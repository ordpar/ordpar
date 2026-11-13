#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared, crash-safe storage primitives for every writer in the pipeline.

Two file shapes live here so no tool hand-rolls a write:

1. **Canonical JSON** (``sources/articles/{id}.json``, ``sources/concepts.json``): a
   deterministic ``sort_keys``/``indent=1`` serialization, so a re-fetch is byte-identical
   whenever the upstream content is unchanged and a diff is always meaningful
   (``docs/schemas.md`` § sources).
2. **JSONL** (``articles.jsonl``, ``cards.jsonl``, ``review/pos-variants.jsonl``): one
   object per line, ``ensure_ascii=False``, LF, sorted by the file's key.

Every write is atomic (temp file in the destination dir + ``os.replace``), cleaned up on
exception, so a crash mid-write can never leave a half-written file. Upsert is **insert-
only by default**: an existing row is kept untouched, never regenerated — the merge, never
overwrite rule of ``docs/library.md``.
"""
import os
import sys
import json
import time
import threading
import tempfile
import contextlib

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


LOCK_TIMEOUT = 120.0   # seconds to wait for a held lock before giving up
LOCK_POLL = 0.05
REPLACE_TIMEOUT = 20.0  # seconds to keep retrying os.replace against a concurrent READER
REPLACE_POLL = 0.05
READ_TIMEOUT = 20.0     # seconds to keep retrying an open() against a concurrent WRITER
READ_POLL = 0.05


class LibraryUnreadable(OSError):
    """A read of a library file lost its race with a concurrent writer for the whole retry
    window. Its own class so a caller can say *"could not read the library"* rather than
    reporting the failure of whatever check it was in the middle of (Robin, 2026-08-09 — the
    per-card gates that printed ``GUARDRAILS FAILED`` on a ``PermissionError``)."""


def _retry_open(path, mode="r", **kw):
    """``open`` with the same bounded retry ``_atomic_write_chunks`` gives the writer.

    The two sides of this race were asymmetric until now. A writer whose ``os.replace`` hits a
    reader retries for ``REPLACE_TIMEOUT``; a reader whose ``open`` hits a writer mid-replace
    got the ``PermissionError`` straight out. That is the same window seen from the other end,
    and at 25 parallel slots it fired twice in one wave (cards 1575 and 1677, 2026-08-09) —
    both times inside ``check_library``, which then printed the words ``GUARDRAILS FAILED``
    for a card whose guardrails it had never managed to run.

    Past the window the error is real and is raised as ``LibraryUnreadable``, which callers
    catch to report the read failure honestly instead of attributing it to their own check."""
    deadline = time.time() + READ_TIMEOUT
    while True:
        try:
            return open(path, mode, **kw)
        except PermissionError as exc:
            if time.time() >= deadline:
                raise LibraryUnreadable(
                    "could not read %s — a concurrent writer held it for the whole %.0fs "
                    "retry window (this is a LOCK failure, not a content failure)"
                    % (path, READ_TIMEOUT)) from exc
            time.sleep(READ_POLL)

# Byte 0 of the lockfile IS the lock; everything from byte 1 is a human-readable "pid time"
# note for the timeout message. Split that way on purpose: on Windows `msvcrt.locking` is
# MANDATORY, so a waiter reading byte 0 would itself fail — reading from byte 1 never touches
# the locked region on either platform.
_LOCK_BYTE = 1
_NOTE_AT = 1

if os.name == "nt":
    import msvcrt

    def _try_acquire(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, _LOCK_BYTE)
            return True
        except OSError:
            return False        # held by someone else — LK_NBLCK never blocks

    def _unlock(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, _LOCK_BYTE)
else:
    import fcntl

    def _try_acquire(fd):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def _unlock(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def lock(path, timeout=LOCK_TIMEOUT):
    """Hold an exclusive lock on ``path`` for the duration of the block.

    Atomic writes make a *single* write crash-safe; they do nothing for a **read-modify-
    write**, which is what every merge in this pipeline is (`author_kit.author` reads all
    10,000 rows, mutates one, writes them all back). Two of those interleaving is a lost
    update: the second writer's snapshot predates the first writer's merge, so `os.replace`
    silently discards it. That is invisible — the file stays well-formed, one card's English
    simply is not there — which is exactly the failure class the guardrails cannot see.
    Serial stints never raced; parallel stints (2026-07-26) do.

    **The lock is the kernel's, not ours** (Robin, 2026-08-09). The first version was a
    lockfile created with ``O_CREAT|O_EXCL`` and *deleted* on release, with the holder's pid
    and birth time inside so an abandoned one could be broken by hand. Every hard part of that
    design came from the delete: a killed holder left the file behind, so `_stale`/`_pid_alive`
    had to guess whether a pid was alive (and lost to pid reuse); a failed remove leaked the
    lock outright; and on Windows the remove itself raced a waiter that had the file open to
    read that pid. The first 25-wide wave lost two merges anyway (2026-08-09), which is where
    guessing gets you.

    So: acquire ``msvcrt.locking`` / ``fcntl.flock`` on byte 0 of the lockfile, and **never
    delete the file**. The kernel drops the lock when the holder exits or crashes — including
    a `kill -9`, which no user-space scheme can survive — so there is no staleness to judge,
    nothing to break by hand, and no release that can fail. A leftover ``.lock`` file on disk
    now means nothing at all; it is an empty handle, not a claim.

    The cost is a per-platform branch, which the old docstring named as the reason not to do
    this. Two four-line functions, both stdlib, is the whole of it.

    Re-entrant per THREAD, so a locked helper may call another; a second thread genuinely
    contends, because both platforms' locks conflict across handles within one process too."""
    lockfile = path + ".lock"
    state = getattr(_held, "state", None)
    if state is None:
        state = _held.state = {}
    entry = state.get(lockfile)
    if entry:
        entry[0] += 1                                   # already ours — nest, don't deadlock
        try:
            yield
        finally:
            entry[0] -= 1
        return
    os.makedirs(os.path.dirname(os.path.abspath(lockfile)) or ".", exist_ok=True)
    fd = os.open(lockfile, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        deadline = time.time() + timeout
        while not _try_acquire(fd):
            if time.time() >= deadline:
                raise RuntimeError(
                    "timed out after %.0fs waiting for %s — %s is holding it. The lock is "
                    "the kernel's: it is released the moment that process exits, so there is "
                    "nothing to delete and nothing to clean up."
                    % (timeout, lockfile, _holder(lockfile)))
            time.sleep(LOCK_POLL)
        try:
            os.lseek(fd, _NOTE_AT, os.SEEK_SET)
            os.write(fd, ("pid %d since %f\n" % (os.getpid(), time.time())).encode("ascii"))
            os.ftruncate(fd, _NOTE_AT + 64)
        except OSError:
            pass                                        # diagnostics only; never fail on them
        state[lockfile] = [1, fd]
        try:
            yield
        finally:
            del state[lockfile]
            _unlock(fd)
    finally:
        os.close(fd)


def _holder(lockfile):
    """Who holds this lock, for the timeout message only. Read from byte 1 — see ``_LOCK_BYTE``."""
    try:
        with open(lockfile, "rb") as f:
            f.seek(_NOTE_AT)
            note = f.read(64).split(b"\n")[0].decode("ascii", "replace").strip("\0 ")
        return note or "another process"
    except Exception:
        return "another process"


# Thread-local, not process-global: the re-entrancy shortcut must only fire for the thread
# that actually holds the lock. Process-global, a second thread sees the first thread's entry,
# takes the nested path and skips locking entirely — which is worse than no lock at all,
# because it looks locked.
_held = threading.local()


def _atomic_write_chunks(path, chunks):
    """Write an ITERABLE of text chunks to ``path`` via a temp file + ``os.replace``.

    Streaming, so the whole file never exists as one string in memory. ``write_jsonl`` used to
    ``"".join`` every serialized row before writing — at 6,703 rows that is a ~5.6 MB string
    built on *every* merge, and with four parallel stint agents merging at once one of them
    died with ``MemoryError`` inside the join (2026-07-31). Nothing was corrupted, because the
    join happens before the temp file is opened, but the peak is pure waste and grows with the
    deck. Chunks are written one at a time instead.

    The replace is **retried** on ``PermissionError`` (Robin's parallel stints, 2026-07-26).
    On Windows a rename onto a destination another process merely has *open* fails, and the
    readers here never take the write lock — every slot's packet generation reads
    ``articles.jsonl`` freely, which is exactly what makes concurrent authoring cheap. So the
    lock serialises writers correctly and the write still lost a race with a reader: a
    grouped packet merges row by row, and slot 4's packet 18 died after two of its eight rows
    had landed, leaving the agent to hand-drop the merged rows and resubmit the rest. A short
    bounded retry covers the window a reader holds the file; past it the error is real and is
    raised as before."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            for chunk in chunks:
                f.write(chunk)
        deadline = time.time() + REPLACE_TIMEOUT
        while True:
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if time.time() >= deadline:
                    raise
                time.sleep(REPLACE_POLL)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _atomic_write(path, text):
    """Atomic write of one whole string — ``_atomic_write_chunks`` with a single chunk."""
    _atomic_write_chunks(path, (text,))


def write_json(path, obj):
    """Canonical atomic JSON write: ``sort_keys``, ``indent=1``, ``ensure_ascii=False``,
    LF, trailing newline. A re-write with the same content produces identical bytes."""
    text = json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
    _atomic_write(path, text)


def read_json(path, missing_ok=False):
    """Read a JSON file, or ``None`` when missing and ``missing_ok``."""
    if not os.path.exists(path):
        if missing_ok:
            return None
        raise FileNotFoundError(path)
    with _retry_open(path, encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path, missing_ok=True):
    """Read a JSONL file into a list of dicts (blank lines skipped).

    The open is retried against a concurrent writer (``_retry_open``) — readers deliberately
    take no lock, so this is the only thing standing between a parallel wave and a spurious
    failure in whatever the caller was doing."""
    if not os.path.exists(path):
        if missing_ok:
            return []
        raise FileNotFoundError(path)
    out = []
    with _retry_open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(path, rows, key):
    """Atomically write ``rows`` as JSONL, sorted by ``key`` (a row -> sort-value fn).

    ``key=None`` preserves the given order — the append-ordered registries
    (`review/ex-terminal.jsonl`) rewrite minus a row without imposing a sort.
    Before 2026-08-17 ``key=None`` was passed straight to ``sorted``, which
    compares the dicts themselves and raises TypeError on any list of two or
    more — the triage Restore of a drop-terminal crashed mid-flight on exactly
    that, after its library write and before its log write."""
    rows = sorted(rows, key=key) if key is not None else list(rows)
    _atomic_write_chunks(path, (json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def upsert_jsonl(path, new_rows, key, replace=False):
    """Merge ``new_rows`` into the JSONL at ``path`` keyed by ``key(row)``.

    Insert-only by default: a row whose key already exists is left as it was on disk and
    the incoming one is dropped (manual compositions survive re-seeds). With
    ``replace=True`` an existing row is overwritten — the single-card repair path.

    Returns ``(added, replaced, skipped)``.
    """
    existing = {key(r): r for r in read_jsonl(path, missing_ok=True)}
    added = replaced = skipped = 0
    for r in new_rows:
        k = key(r)
        if k in existing:
            if replace:
                existing[k] = r
                replaced += 1
            else:
                skipped += 1
        else:
            existing[k] = r
            added += 1
    write_jsonl(path, list(existing.values()), key)
    return added, replaced, skipped
