#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bokmålsordboka with our fixes in it: the corrected copy the public export ships beside the raw
one (decisions 184, Robin 2026-11-12: "Yes, corrected copy").

Two sets of fixes reach Bokmålsordboka's text on its way to ordpar.no, and the copy carries both,
through **one code path, the overlay's** (`sitegen/overlay.py`: a row changes a value only where
the raw value at its `path` is exactly its `before`):

1. `review/mirror-corrections.jsonl` — machine patches already (`article`, `path`, `before`,
   `after`). The site build applies them only to articles with no library row (`library_row`); the
   copy applies them everywhere, as it has no library rows to defer to.
2. `review/source-normalizations.jsonl` — a log in prose, whose text lives only in the deck's
   captures `sources/articles/<id>.json`. `derive_patches` turns it into patches of the same shape,
   mechanically, from the captures, the log and the mirror: for each article a log row names, the
   capture is compared with the mirror's article pruned the same way (`fetch.prune_article`), and a
   differing value becomes a patch **only when the log explains the whole difference**:

   * text (`how: "text"`): the row's `before` → `after` (its literal strings, or the words that
     differ between them) turn the mirror's value into exactly the capture's. The patch's `before`
     is the raw value and its `after` is that value with only those replacements made, so nothing
     else of the capture — an older text ordbokene has since changed — can come in;
   * a reference (`how: "reference"`, kinds `ref-anchor`, `ref-retarget`, `duplicate-def-id`): a
     cross-reference item or a definition whose ids differ, where the row's `before` names the old
     number and its `after` the new one; the patch names only the keys that differ.

   Not patched, and listed with the reason: a difference in the headwords or paradigms (`lemmas`;
   the overlay refuses a path outside `body`, as the mirror's index and the search index read them
   raw), an element added or removed (no path can name it), a difference the log does not explain,
   a row whose article ordbokene has changed or fixed, and the rows that are not text fixes at all
   (the registry pointers, the content refresh, the derive-time whitespace rule).

   **Remade at every export**, from the current mirror: a row ordbokene fixes drops out (`upstream`),
   one whose text ordbokene changed stops being explained (`not_located`), never re-guessed.

Out of the copy, as display rather than data: `sitegen/lemma_order.py` (the order of an article's
spellings in its header) and `sitegen/corrections.py` (the change notice and the About page's
counts); the reconciler's picks between ordbokene's own embedded and standalone texts.

    python ordpar/corrected_copy.py patches [--mirror FILE] [--out FILE]   # the derived patches
    python ordpar/corrected_copy.py write [--mirror FILE] FOLDER           # the copy, in parts

`write` puts into FOLDER the corrected articles in parts (`data_parts.py`, the raw copy's ranges),
`normalization-patches.jsonl` (the derived patches) and `fixes.jsonl` (every row of both files and
every log row, with its verdict per article). Standard library and the site's own modules only.
"""
import argparse
import collections
import difflib
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ordpar.sitegen import overlay  # noqa: E402
from ordpar.sitegen.deck import fetch  # noqa: E402
import data_parts  # noqa: E402

LOG = os.path.join(fetch.REVIEW, "source-normalizations.jsonl")
CORRECTIONS = overlay.PATH
CAPTURES = fetch.ARTICLES_DIR
PATCHES_NAME = "normalization-patches.jsonl"
FIXES_NAME = "fixes.jsonl"

#: kinds that record something other than a fix in a capture's text
NOT_A_FIX = {"registry-pointer:dangling-ref", "registry-pointer:dangling-def",
             "registry-pointer:embedded-vs-standalone", "whitespace-class", "refresh"}
#: kinds whose fix is a cross-reference's or a definition's ids
REF_KINDS = {"ref-anchor", "ref-retarget", "duplicate-def-id"}
REF_KEYS = {"article_id", "definition_id", "definition_order", "id", "hgno", "lemmas"}
#: the doubled space the log's class row collapsed (between two word characters only)
DOUBLE_SPACE = re.compile(r"(?<=\w)  +(?=\w)")
QUOTES = "'\"‘’“”«»`"
_ABSENT = object()

# verdicts of a log row that makes no patch (the overlay's own are `overlay.VERDICTS`)
NOT_LOCATED, HEADWORD, SHAPE, NOT_FIX, DISPLAY, NO_ARTICLE, NO_CAPTURE, NOT_IN_MIRROR = (
    "not_located", "headword", "element_added_or_removed", "not_a_text_fix", "display_order",
    "no_article", "no_capture", "not_in_mirror")


# ------------------------------------------------------------------------------- reading

def read_log(path=LOG):
    """`[(line number, row)]` of the normalization log."""
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                out.append((n, json.loads(line)))
    return out


def index_mirror(path):
    """`{id: byte offset}` over the mirror's `bm-articles.jsonl` (one pass, ids read from the line
    start as `data_parts` does)."""
    out = {}
    with open(path, "rb") as f:
        while True:
            off = f.tell()
            line = f.readline()
            if not line:
                break
            if line.strip():
                out[data_parts.line_id(line)] = off
    return out


class MirrorFile(object):
    """Random access to the mirror's rows by id; the raw `data`, nothing reordered."""

    def __init__(self, path):
        self.path = path
        self.offsets = index_mirror(path)
        self._fh = open(path, "rb")

    def row(self, aid):
        off = self.offsets.get(aid)
        if off is None:
            return None
        self._fh.seek(off)
        return json.loads(self._fh.readline())

    def data(self, aid):
        r = self.row(aid)
        return None if r is None else r.get("data")

    def close(self):
        self._fh.close()


# ------------------------------------------------------------------------------- the diff

def _shape(i):
    return "<element %d>" % i


def diff(a, b, path=(), out=None):
    """The differing values of `a` (the mirror's) and `b` (the capture's): `[(path, a, b)]`, an
    absent key as `_ABSENT`. Lists of different lengths are aligned element by element; an
    element added or removed is one entry whose path ends in a `<element N>` marker."""
    out = [] if out is None else out
    path = list(path)
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            diff(a.get(k, _ABSENT), b.get(k, _ABSENT), path + [k], out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) == len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, path + [i], out)
        else:
            ka = [json.dumps(x, sort_keys=True) for x in a]
            kb = [json.dumps(x, sort_keys=True) for x in b]
            for t, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ka, b=kb, autojunk=False).get_opcodes():
                if t == "equal":
                    continue
                if t == "replace" and i2 - i1 == j2 - j1:
                    for k in range(i2 - i1):
                        diff(a[i1 + k], b[j1 + k], path + [i1 + k], out)
                else:
                    out.append((path + [_shape(i1)], a[i1:i2], b[j1:j2]))
    elif type(a) is not type(b) or a != b:
        out.append((path, a, b))
    return out


def _get(root, path):
    node = root
    for k in path:
        if isinstance(node, dict) and k in node:
            node = node[k]
        elif isinstance(node, list) and isinstance(k, int) and 0 <= k < len(node):
            node = node[k]
        else:
            return _ABSENT
    return node


# ------------------------------------------------------------------------------- explaining

def _variants(s):
    """The literal text in a log row's `before` or `after`: split where the row lists several
    (" / ", " + "), quotes and a trailing parenthetical note or ellipsis taken off."""
    if not isinstance(s, str):
        return []
    out = []
    for part in re.split(r"\s+/\s+|\s+\+\s+", s):
        p = re.sub(r"\s{2,}\([^)]*\)\s*$", "", part)
        p = re.sub(r"\s+\((?:bare join|parenthesized|two segments)\)\s*$", "", p).strip()
        p = p.strip(QUOTES).strip()
        p = re.sub(r"^(?:\.\.\.|…)\s*|\s*(?:\.\.\.|…)$", "", p).strip()
        if p:
            out.append(p)
    return out


def replacements(row):
    """`[(old, new)]` a row stands for: its whole before/after strings, and each run of words
    that differs between them, with one, none or two words of context, also without the
    punctuation at its ends."""
    out = []
    for b, a in zip(_variants(row.get("before")), _variants(row.get("after"))):
        if b == a:
            continue
        out.append((b, a))
        bw, aw = b.split(" "), a.split(" ")
        for t, i1, i2, j1, j2 in difflib.SequenceMatcher(a=bw, b=aw, autojunk=False).get_opcodes():
            if t == "equal":
                continue
            for ctx in (1, 0, 2):
                o = " ".join(bw[max(0, i1 - ctx):min(len(bw), i2 + ctx)])
                n = " ".join(aw[max(0, j1 - ctx):min(len(aw), j2 + ctx)])
                if o and o != n:
                    out.append((o, n))
                    po, pn = o.strip(".,;:!?()"), n.strip(".,;:!?()")
                    if po and po != pn and (po, pn) != (o, n):
                        out.append((po, pn))
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def _rewrite(s, row, class_row):
    """`s` with the first of `row`'s replacements that changes it made (every occurrence), or with
    the doubled spaces collapsed for the class row; `s` itself when none applies."""
    if class_row:
        return DOUBLE_SPACE.sub(" ", s)
    for o, n in replacements(row):
        if o in s:
            t = s.replace(o, n)
            if t != s:
                return t
    return s


def _map_strings(value, fn):
    if isinstance(value, dict):
        return {k: _map_strings(v, fn) for k, v in value.items()}
    if isinstance(value, list):
        return [_map_strings(v, fn) for v in value]
    if isinstance(value, str):
        return fn(value)
    return value


def explain(m, c, rows):
    """The log rows (`[(line, row, class_row)]`) whose replacements turn `m` (the mirror's value:
    a string, or a list or object of them) into exactly `c` (the capture's), as
    `(sorted lines, transform)`; `transform(raw)` makes the same replacements in a raw value.
    None when no order of the rows does it."""
    for order in (rows, rows[::-1]):
        used = []

        def step(s, order=order, used=used):
            for line, row, cls in order:
                t = _rewrite(s, row, cls)
                if t != s:
                    used.append(line)
                    s = t
            return s
        if _map_strings(m, step) == c and used:
            def transform(raw, order=order):
                return _map_strings(raw, lambda s: _apply_all(s, order))
            # every row whose own replacement is visible here, so a row logged twice is credited
            fm, fc = json.dumps(m, ensure_ascii=False), json.dumps(c, ensure_ascii=False)
            lines = set(used) | {line for line, row, cls in rows if not cls and any(
                o in fm and n in fc and o not in fc for o, n in replacements(row))}
            return sorted(lines), transform
    return None


def _apply_all(s, order):
    for _line, row, cls in order:
        s = _rewrite(s, row, cls)
    return s


def _numbers(s):
    return set(re.findall(r"\d+", s if isinstance(s, str) else json.dumps(s)))


# ------------------------------------------------------------------------------- deriving

def _row_ids(row):
    ids = set()
    if isinstance(row.get("article"), int) and not isinstance(row.get("article"), bool):
        ids.add(row["article"])
    if row.get("kind") != "refresh":
        ids.update(x for x in row.get("ids") or [] if isinstance(x, int))
    return ids


def _ref_owner(path, data):
    """The longest prefix of `path` naming a cross-reference item or a definition (an object with
    `type_` `article_ref` or `definition`, or one holding `definition_id`) in `data`."""
    for k in range(len(path) - 1, 0, -1):
        node = _get(data, path[:k])
        if isinstance(node, dict) and (node.get("type_") in ("article_ref", "definition")
                                       or "definition_id" in node):
            return path[:k]
    return None


def derive_patches(mirror, log_rows, captures=CAPTURES):
    """The normalization log as patches in the mirror-corrections row shape.

    `mirror`: a `MirrorFile` (or anything with `data(aid)`); `log_rows`: `read_log`'s list.
    Returns `(patches, status)`: the patches in article and path order, each
    `{article, lemma, kind, path, before, after, how, log}` (`log`: the log's line numbers), and
    `{line: (verdict, why)}` for every log line that made no patch."""
    status, by_article = {}, collections.defaultdict(list)
    for line, row in log_rows:
        kind = row.get("kind")
        if kind in NOT_A_FIX:
            status[line] = (NOT_FIX, "the row records no edit of a capture's text (%s)" % kind)
            continue
        if kind == "lemma-order":
            status[line] = (DISPLAY, "an order of spellings: shown by sitegen/lemma_order.py, "
                                     "not a fix of the text")
            continue
        ids = _row_ids(row)
        if not ids:
            status[line] = (NO_ARTICLE, "the row names no article id")
            continue
        # the doubled-space class row, and any row that says "double space" rather than quoting it
        class_row = (row.get("article") is None and bool(row.get("ids"))) or "double space" in (
            "%s %s" % (row.get("before"), row.get("after"))).lower()
        for aid in ids:
            by_article[aid].append((line, row, class_row))

    patches, located, why_not = [], collections.defaultdict(set), collections.defaultdict(set)
    for aid in sorted(by_article):
        rows = by_article[aid]
        cap_path = os.path.join(captures, "%d.json" % aid)
        if not os.path.exists(cap_path):
            for line, _r, _c in rows:
                why_not[line].add((NO_CAPTURE, "no capture of article %d" % aid))
            continue
        with io.open(cap_path, encoding="utf-8") as fh:
            cap = json.load(fh)
        raw = mirror.data(aid)
        if raw is None:
            for line, _r, _c in rows:
                why_not[line].add((NOT_IN_MIRROR, "article %d is not in the mirror" % aid))
            continue
        pm = fetch.prune_article(raw)
        diffs = diff(pm, cap)
        ref_groups = collections.OrderedDict()
        for path, m, c in diffs:
            last = path[-1] if path else None
            shape = isinstance(last, str) and last.startswith("<element ")
            near = [(l, r, cls) for l, r, cls in rows
                    if r.get("path") is None or list(r["path"][:len(path)]) == list(path[:len(r["path"])])]
            if not near:
                continue
            if shape or m is _ABSENT or c is _ABSENT:
                if any(r.get("kind") in REF_KINDS for _l, r, _c in near) and not shape and \
                        path[0] == "body":
                    owner = _ref_owner(path, pm)
                    if owner is not None:
                        ref_groups.setdefault(tuple(owner), []).append((path, m, c))
                        continue
                if shape:
                    for line, r, cls in near:
                        if _touches(r, m, c):
                            why_not[line].add((SHAPE, "an element added or removed at %s" % _p(path)))
                continue
            got = None
            if isinstance(m, (str, list, dict)) and type(m) is type(c):
                got = explain(m, c, near)
            if got is None and isinstance(m, (int, type(None))) and path[0] == "body" and \
                    any(r.get("kind") in REF_KINDS for _l, r, _c in near):
                owner = _ref_owner(path, pm)
                if owner is not None:
                    ref_groups.setdefault(tuple(owner), []).append((path, m, c))
                continue
            if got is None:
                continue
            lines, transform = got
            if path[0] != "body":
                for line in lines:
                    why_not[line].add((HEADWORD, "the headwords or paradigms (%s)" % _p(path)))
                continue
            raw_v = _get(raw, path)
            if raw_v is _ABSENT:
                continue
            after = transform(raw_v)
            if after == raw_v:
                continue
            first = _first(rows, lines)
            patches.append({"article": aid, "lemma": first.get("lemma"), "kind": first.get("kind"),
                            "path": list(path), "before": raw_v, "after": after, "how": "text",
                            "log": lines})
            for line in lines:
                located[line].add(aid)
        for owner, items in ref_groups.items():
            owner = list(owner)
            keys = sorted({p[len(owner)] for p, _m, _c in items}, key=str)
            keys = [k for k in keys if k in REF_KEYS]
            raw_node, cap_node = _get(raw, owner), _get(cap, owner)
            if not keys or not isinstance(raw_node, dict) or not isinstance(cap_node, dict):
                continue
            before = {k: raw_node.get(k) for k in keys}
            after = {k: cap_node.get(k) for k in keys}
            if before == after:
                continue
            # the id that says where the reference points (or which definition it is): the row
            # must name its old value in `before` and its new one in `after`
            key = next((k for k in ("article_id", "definition_id", "id")
                        if k in keys and before.get(k) != after.get(k)), None)
            if key is None:
                continue
            old, new = str(before[key]), str(after[key])
            lines = sorted(l for l, r, _c in rows if r.get("kind") in REF_KINDS and
                           old in _numbers(r.get("before")) and new in _numbers(r.get("after")))
            if not lines:
                continue
            first = _first(rows, lines)
            patches.append({"article": aid, "lemma": first.get("lemma"), "kind": first.get("kind"),
                            "path": owner, "before": before, "after": after, "how": "reference",
                            "log": lines})
            for line in lines:
                located[line].add(aid)

    patches.sort(key=lambda p: (p["article"], json.dumps(p["path"])))
    for line, row in log_rows:
        if line in status or line in located:
            continue
        reasons = sorted(why_not.get(line) or [])
        if reasons:
            status[line] = reasons[0]
        else:
            status[line] = (NOT_LOCATED, _not_located_why(row, mirror))
    return patches, status


def _touches(row, m, c):
    fm, fc = json.dumps(m, ensure_ascii=False), json.dumps(c, ensure_ascii=False)
    return any(o in fm or n in fc for o, n in replacements(row))


def _first(rows, lines):
    for line, row, _c in rows:
        if line == lines[0]:
            return row
    return {}


def _p(path):
    return "/".join(str(k) for k in path)


def _texts(node, out):
    if isinstance(node, dict):
        for v in node.values():
            _texts(v, out)
    elif isinstance(node, list):
        for v in node:
            _texts(v, out)
    elif isinstance(node, str):
        out.append(node)
    return out


def _not_located_why(row, mirror):
    """Why a row with an article made no patch: ordbokene's text already carries its `after`
    (fixed upstream), still carries its `before` (the capture does not differ there in a way the
    log explains), or neither (ordbokene changed the text)."""
    text = " | ".join(t for aid in sorted(_row_ids(row)) for t in _texts(mirror.data(aid), []))
    reps = replacements(row)
    has_b = any(o in text for o, _n in reps)
    has_a = any(n in text and o not in text for o, n in reps)
    if row.get("resolved_upstream"):
        return "logged as resolved upstream"
    if has_a and not has_b:
        return "ordbokene's text carries the fix (upstream)"
    if has_b:
        return "ordbokene's text still has the defect, but no difference the log explains"
    if not reps:
        return "the row's before and after are descriptions, not text"
    return ("neither the row's before nor its after is in ordbokene's article (changed upstream, "
            "or the row describes rather than quotes)")


# ------------------------------------------------------------------------------- the copy

def make_overlay(mirror, corrections, patches):
    """One overlay over both sets, resolved against the raw mirror: the mirror corrections first,
    then the derived patches, so a patch on a field a correction already fixes is `duplicate`.
    No library row defers (the copy has none) and every kind is allowed."""
    from ordpar.sitegen import mirror as mirror_mod
    rows = list(corrections) + [dict(p) for p in patches]
    ov = overlay.Overlay(rows, path=None, library_ids=(), kinds=None)
    ov.resolve(mirror.data,
               lambda ids: {k: v[0] for k, v in mirror_mod.embedding_parents(mirror.path, ids).items()})
    return ov


def fixes_list(ov, mc_lines, log_rows, status):
    """Every row of both files and every log line, with its verdict: the overlay's for a row it
    resolved (with each embedding parent's copies' verdicts under `copies`), and the reason for a
    log line that made no patch. `mc_lines`: the mirror corrections' line numbers in their file."""
    out, n_mc = [], len(mc_lines)
    for i, (row, v) in enumerate(zip(ov.rows, ov.verdicts)):
        e = collections.OrderedDict()
        if i < n_mc:
            e["source"], e["line"] = "mirror-corrections", mc_lines[i]
        else:
            e["source"], e["log_lines"] = "source-normalizations", row.get("log")
        for k in ("article", "lemma", "kind", "path"):
            e[k] = row.get(k)
        if i >= n_mc:
            e["how"] = row.get("how")
        e["verdict"] = v
        if ov.details[i]:
            e["why"] = ov.details[i]
        if ov.copies[i]:
            e["copies"] = {str(p): vs for p, vs in sorted(ov.copies[i].items())}
        out.append(e)
    rows = dict(log_rows)
    for line in sorted(status):
        v, why = status[line]
        r = rows[line]
        out.append(collections.OrderedDict([
            ("source", "source-normalizations"), ("log_lines", [line]), ("article", r.get("article")),
            ("lemma", r.get("lemma")), ("kind", r.get("kind")), ("path", None), ("verdict", v),
            ("why", why)]))
    return out


def read_corrections(path=CORRECTIONS):
    """The mirror corrections (`overlay.read`) and the line number of each in the file."""
    lines = []
    if path and os.path.exists(path):
        with io.open(path, encoding="utf-8") as fh:
            lines = [n for n, line in enumerate(fh, 1) if line.strip()]
    return overlay.read(path), lines


def dumps_jsonl(rows):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def write(mirror_path, folder, log_path=LOG, corrections_path=CORRECTIONS, captures=CAPTURES):
    """The corrected copy into `folder`: its articles in parts, the derived patches, the list of
    fixes. A row the overlay leaves untouched is the raw line, byte for byte; a corrected one is
    the raw row with its `data` corrected, written as the mirror writes its lines. Returns the
    counts."""
    mirror = MirrorFile(mirror_path)
    try:
        log_rows = read_log(log_path)
        patches, status = derive_patches(mirror, log_rows, captures)
        corrections, mc_lines = read_corrections(corrections_path)
        ov = make_overlay(mirror, corrections, patches)
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="corrected-", suffix=".jsonl", dir=folder)
        changed = 0
        try:
            with os.fdopen(fd, "wb") as dst, open(mirror_path, "rb") as src:
                for line in src:
                    if not line.strip():
                        continue
                    aid = data_parts.line_id(line)
                    if ov.touches(aid):
                        row = json.loads(line)
                        fixed = ov.apply(aid, row.get("data"))
                        if fixed is not row.get("data") and fixed != row.get("data"):
                            row["data"] = fixed
                            line = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
                            changed += 1
                    dst.write(line)
            parts = data_parts.split(tmp, folder)
        finally:
            os.remove(tmp)
        _write(os.path.join(folder, PATCHES_NAME), dumps_jsonl(patches))
        fixes = fixes_list(ov, mc_lines, log_rows, status)
        _write(os.path.join(folder, FIXES_NAME), dumps_jsonl(fixes))
        n_mc = len(corrections)
        counts = {
            "articles_changed": changed,
            "parts": [(os.path.basename(p), b) for p, b in parts],
            "mirror_corrections": dict(collections.Counter(ov.verdicts[:n_mc])),
            "patches": len(patches),
            "patches_by_how": dict(collections.Counter(p["how"] for p in patches)),
            "patch_verdicts": dict(collections.Counter(ov.verdicts[n_mc:])),
            "copies_applied": sum(vs.count(overlay.APPLIED) for c in ov.copies for vs in c.values()),
            "log_lines": len(log_rows),
            "log_lines_patched": len({l for p in patches for l in p["log"]}),
            "log_lines_not_patched": dict(collections.Counter(v for v, _w in status.values())),
        }
        return counts
    finally:
        mirror.close()


def _write(path, data):
    """Write `data` only when the file's bytes differ (a re-run writes nothing)."""
    if os.path.exists(path):
        with open(path, "rb") as fh:
            if fh.read() == data:
                return False
    with open(path, "wb") as fh:
        fh.write(data)
    return True


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("patches", "write"))
    ap.add_argument("folder", nargs="?", help="write: the folder for the copy")
    ap.add_argument("--mirror", help="the mirror's bm-articles.jsonl (default: mirror in "
                                     "ordpar/local-paths.json)")
    ap.add_argument("--out", help="patches: the file to write (default: standard output)")
    a = ap.parse_args(argv)
    if not a.mirror:
        import local_paths
        a.mirror = local_paths.require("mirror", "--mirror FILE")
    if a.what == "patches":
        mirror = MirrorFile(a.mirror)
        try:
            patches, status = derive_patches(mirror, read_log())
        finally:
            mirror.close()
        data = dumps_jsonl(patches)
        if a.out:
            _write(a.out, data)
        else:
            sys.stdout.write(data.decode("utf-8"))
        print("%d patch(es) from %d log line(s); not patched: %s" % (
            len(patches), len({l for p in patches for l in p["log"]}),
            ", ".join("%s %d" % kv for kv in sorted(collections.Counter(
                v for v, _w in status.values()).items()))), file=sys.stderr)
        return 0
    if not a.folder:
        ap.error("write needs FOLDER")
    counts = write(a.mirror, a.folder)
    print(json.dumps(counts, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
