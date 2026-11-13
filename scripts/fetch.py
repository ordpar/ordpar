#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The shared fetch layer over the ordbokene (UiB) API.

Three jobs, each landing a committed source-of-truth capture:

* **Article fetch** — ``bm/article/{id}.json`` → whitelist-prune (``docs/schemas.md``
  § sources) → canonical atomic write to ``sources/articles/{id}.json``. Re-fetching an
  unchanged article is byte-for-byte a no-op; ``sources/`` is itself the article cache.
  Before the network, the **mirror** answers for any article whose snapshot row is still
  upstream's current version (``mirror_current``, checked against UiB's nightly index).
* **Lemma search** — ``api/articles?w={lemma}&dict=bm&scope=e`` → ``[article ids]``.
  Always ``scope=e`` (exact headword; the default ``ei`` leaks inflected-form matches).
  Responses are cached under the gitignored ``.cache/search/`` so a full seed is resumable
  and re-runnable offline.
* **Concepts snapshot** — ``bm/concepts.json`` → ``sources/concepts.json``, the
  abbreviation-code expansion table.

Bootstrap: the gitignored ``.glossary_cache/`` at the repo root holds ~770 **raw** article
responses plus ``_concepts.json``. When present, a fetch reads and prunes the raw capture
instead of going to the network — the pilot doesn't re-fetch what is already local. A
worktree without that directory simply fetches.

Network: requests verify the server's certificate, send a stable User-Agent, and
``time.sleep(0.4)`` after **every** network hit — never a retry loop without the sleep. A machine
that intercepts TLS with a non-strict CA sets ``ORDBOK_TLS_NO_VERIFY=1``, and only then is the
context unverified (the API is public and read-only); verification was off for every run until
2026-11-12 (decisions 184: on by default in the published code).

Where the data lives: ``sources/`` and ``review/`` sit under the repository root, unless
``ORDBOK_DATA_DIR`` names another folder holding them (and the library, ``articles.jsonl``) —
one optional override, read once at import, for a checkout that keeps its data apart (the public
repository's ``data/``, decisions 184). Unset, every path is as before. The caches (``.cache/``,
``.glossary_cache/``, ``.mirror/``) stay under the root either way.
"""
import os
import re
import sys
import ssl
import time
import json
import datetime
import argparse
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the one override (decisions 184): the folder holding `sources/`, `review/` and the library
DATA_ROOT = os.path.abspath(os.environ.get("ORDBOK_DATA_DIR") or ROOT)
LIBRARY_PATH = os.path.join(DATA_ROOT, "articles.jsonl")
SOURCES = os.path.join(DATA_ROOT, "sources")
ARTICLES_DIR = os.path.join(SOURCES, "articles")
CONCEPTS_PATH = os.path.join(SOURCES, "concepts.json")
SEARCH_CACHE = os.path.join(ROOT, ".cache", "search")
TRANSIENT_CACHE = os.path.join(ROOT, ".cache", "articles")
BOOTSTRAP = os.path.join(ROOT, ".glossary_cache")

ARTICLE_URL = "https://ord.uib.no/bm/article/%s.json"
SEARCH_URL = "https://ord.uib.no/api/articles?w=%s&dict=bm&scope=e"
CONCEPTS_URL = "https://ord.uib.no/bm/concepts.json"

_UA = {"User-Agent": "ordbok-anki fetch (post@ordpar.no)"}
#: set to 1 on a machine whose TLS is intercepted by a non-strict CA; anything else verifies
TLS_NO_VERIFY_ENV = "ORDBOK_TLS_NO_VERIFY"


def ssl_context():
    """The context every request uses: verified, unless ``ORDBOK_TLS_NO_VERIFY=1``."""
    ctx = ssl.create_default_context()
    if os.environ.get(TLS_NO_VERIFY_ENV) == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


_SSL = ssl_context()


def _get(url):
    """Network GET → parsed JSON, throttled. The only place a request is made."""
    req = urllib.request.Request(url, headers=_UA)
    raw = urllib.request.urlopen(req, timeout=30, context=_SSL).read()
    time.sleep(0.4)
    return json.loads(raw)


# --- whitelist prune ---------------------------------------------------------

TOP_KEEP = ("article_id", "lemmas", "body", "suggest", "submitted")
SUBART_KEEP = ("type_", "article_id", "lemmas", "intro", "article")
SUBART_ARTICLE_KEEP = ("article_id", "lemmas", "body")


def _prune_subarticle(node):
    """A ``sub_article`` node keeps only its identity + intro + a stripped ``article``
    (whose volatiles have *different names* than the top level and churn on third-party
    citations — see ``docs/schemas.md`` § sources)."""
    out = {k: node[k] for k in SUBART_KEEP if k in node}
    art = out.get("article")
    if isinstance(art, dict):
        pruned = {k: art[k] for k in SUBART_ARTICLE_KEEP if k in art}
        if isinstance(pruned.get("body"), (dict, list)):
            pruned["body"] = _prune_tree(pruned["body"])
        out["article"] = pruned
    return out


def _prune_tree(node):
    """Walk the body, rewriting every ``sub_article`` subtree; all other content is kept
    verbatim (definition/explanation/example nodes carry no volatiles)."""
    if isinstance(node, dict):
        if node.get("type_") == "sub_article":
            return _prune_subarticle(node)
        return {k: _prune_tree(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_prune_tree(v) for v in node]
    return node


def prune_article(raw):
    """Whitelist-prune a raw article response to its committed shape."""
    out = {k: raw[k] for k in TOP_KEEP if k in raw}
    if "body" in out:
        out["body"] = _prune_tree(out["body"])
    return out


# --- article fetch -----------------------------------------------------------

def source_path(aid):
    return os.path.join(ARTICLES_DIR, "%s.json" % aid)


_SOURCE_CACHE = None


def cache_sources():
    """Enable an in-process cache of pruned captures — for READ-ONLY passes only.

    ``check_library`` re-derives every row in scope, and a cited target's capture is
    loaded once per citer, not once per run: the full gate made ~58k ``read_json``
    calls for ~24k derivations (measured 2026-08-10, 4.5s in ``_io.open`` alone).
    A cache keyed by article id collapses the repeats. **A writer process must not
    enable this**: a capture edit mid-run (a source normalization) would be invisible
    to every later derivation, which is exactly the staleness guardrail 4 exists to
    catch. There is deliberately no "off" switch — enable it only in a process that
    ends when the pass does."""
    global _SOURCE_CACHE
    _SOURCE_CACHE = {}


def source_ids():
    """The ids with a committed capture on disk, as strings — ONE directory listing.

    For existence questions only (guardrail 3's "library row has no source file"): the gate
    used to answer them by opening and parsing every capture — 26,746 ``read_json`` calls,
    6.8 s of a 26 s scoped run (context-cost decisions 9, 2026-09-05). Never a substitute for
    ``load_source`` where the capture's content is wanted."""
    try:
        names = os.listdir(ARTICLES_DIR)
    except OSError:
        return set()
    return {n[:-5] for n in names if n.endswith(".json")}


def load_source(aid):
    """The committed pruned capture for ``aid``, or ``None`` if not fetched."""
    if _SOURCE_CACHE is not None:
        key = str(aid)
        if key in _SOURCE_CACHE:
            return _SOURCE_CACHE[key]
        art = store.read_json(source_path(aid), missing_ok=True)
        if art is not None:
            # A MISS is never cached: derive.py may fetch a new capture mid-run, and a
            # cached None from before the fetch would hide the file it just wrote. A hit
            # is safe — nothing overwrites an existing capture inside one pass.
            _SOURCE_CACHE[key] = art
        return art
    return store.read_json(source_path(aid), missing_ok=True)


LEMMA_INDEX = os.path.join(ROOT, ".cache", "lemma-index.json")
_LEMMA_INDEX = None


MIRROR_ARTICLES = os.path.join(ROOT, ".mirror", "bm-articles.jsonl")
MIRROR_INDEX = os.path.join(ROOT, ".cache", "mirror-index.json")
_MIRROR_INDEX = None
_MIRROR_CACHE = {}


def _mirror_index():
    """{"lemmas": {form: [ids]}, "offsets": {id: byte offset}} over the mirror
    jsonl (`scripts/mirror.py`, decisions entry 58) — built once, cached in
    `.cache/mirror-index.json`, rebuilt when the mirror file's size changes.
    None when no mirror has been extracted: everything then falls back to
    the captures alone, exactly as before the mirror existed."""
    global _MIRROR_INDEX
    if not os.path.exists(MIRROR_ARTICLES):
        return None
    size = os.path.getsize(MIRROR_ARTICLES)
    if _MIRROR_INDEX is not None and _MIRROR_INDEX.get("size") == size:
        return _MIRROR_INDEX
    cached = store.read_json(MIRROR_INDEX, missing_ok=True) or {}
    if cached.get("size") == size:
        _MIRROR_INDEX = cached
        return cached
    lemmas, offsets = {}, {}
    with open(MIRROR_ARTICLES, "rb") as f:
        pos = 0
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                pos += len(line)
                continue
            offsets[str(r["id"])] = pos
            for lem in (r.get("data") or {}).get("lemmas") or []:
                w = (lem.get("lemma") or "").strip().casefold()
                if w:
                    ids = lemmas.setdefault(w, [])
                    if r["id"] not in ids:
                        ids.append(r["id"])
            pos += len(line)
    _MIRROR_INDEX = {"size": size, "lemmas": lemmas, "offsets": offsets}
    os.makedirs(os.path.dirname(MIRROR_INDEX), exist_ok=True)
    store.write_json(MIRROR_INDEX, _MIRROR_INDEX)
    return _MIRROR_INDEX


def articles_by_lemma(lemma):
    """Every article on a written form the pipeline can SEE: the committed
    captures first, then the mirror's — the complete dictionary once
    `mirror.py extract` has run. Ids only; `load_any` reads them."""
    ids = captures_by_lemma(lemma)
    mi = _mirror_index()
    if mi:
        for aid in mi["lemmas"].get((lemma or "").strip().casefold(), []):
            if aid not in ids:
                ids.append(aid)
    return ids


def _mirror_row(aid):
    """The mirror's raw row for ``aid`` — ``{id, revision, updated_at, data}`` — or None.
    One seek, no scan; the offsets come from ``_mirror_index``."""
    mi = _mirror_index()
    key = str(aid)
    if not mi or key not in mi["offsets"]:
        return None
    with open(MIRROR_ARTICLES, "rb") as f:
        f.seek(mi["offsets"][key])
        return json.loads(f.readline())


def load_any(aid):
    """A pruned article from the committed capture if one exists, else from
    the mirror (pruned on the fly, in-memory cached), else None. For PACKET
    CONTEXT only — homograph siblings, an expression's component words. The
    deck's own paths keep using `load_source`: nothing here writes to
    `sources/`, and a mirror-only article is never part of the pinned
    universe by being looked at. **Says nothing about currency** — a row that
    upstream has revised since the snapshot still answers here; pinning a
    capture goes through `mirror_current`."""
    art = load_source(aid)
    if art is not None:
        return art
    key = str(aid)
    if key in _MIRROR_CACHE:
        return _MIRROR_CACHE[key]
    row = _mirror_row(aid)
    if row is None:
        return None
    art = prune_article(row.get("data") or {}) if row.get("data") else None
    _MIRROR_CACHE[key] = art
    return art


# --- the mirror as a PINNING source (currency-checked) -----------------------
# The mirror holds all 94k Bokmålsordboka articles as of its snapshot cursor, and a
# mirrored `data` object is verbatim what the API returns — so a capture pinned from it
# is byte-identical to a fetched one, at a 0.4 s-per-request saving (an `admit 500` pinned
# 877 of 883 closure targets over the API in 2026-09-08's measurement, every one of them
# already local). What the mirror cannot say by itself is whether its row is still
# CURRENT: the snapshot ages from the day it is taken. UiB's nightly index answers that
# for the whole dictionary in one 5 MB download — `revision` + `updated_at` per id — so
# the rule is (Robin, 2026-09-08): pin from the mirror where the index agrees with it,
# from the API where upstream has moved, where the article postdates the snapshot, or
# where the index cannot be reached at all. Never a silently stale pin.

_UIB_INDEX = None
_UIB_INDEX_WARNED = False


def _load_uib_index():
    """Load + parse UiB's nightly index — ``mirror.load_index``, which downloads only when
    ``.mirror/bm-index.json`` is missing or older than ``mirror.INDEX_MAX_AGE`` (12 h).
    Split out so a test can substitute it (and so the network hit is nowhere near import
    time)."""
    import mirror
    return mirror.index_revisions(mirror.load_index())


def uib_index():
    """``{str(id): (revision, updated_at)}`` from UiB's live index, resolved ONCE per
    process and cached in memory — and, across processes, reused from
    ``.mirror/bm-index.json`` while that file is younger than ``mirror.INDEX_MAX_AGE``
    (12 h; the index is rebuilt nightly upstream). A wave's hundreds of short-lived
    processes therefore share one 5 MB download, not one each.

    ``None`` when the index could not be resolved — reported once on stderr, after which
    every currency question answers "not current" and the caller goes to the network
    exactly as before the mirror existed. That covers **both** failure shapes: no usable
    on-disk index, and a failed download over a STALE on-disk index. Neither ever pins
    from an out-of-date snapshot row; a stale copy is not a fallback."""
    global _UIB_INDEX, _UIB_INDEX_WARNED
    if _UIB_INDEX is None:
        try:
            _UIB_INDEX = _load_uib_index() or {}
        except Exception as e:
            _UIB_INDEX = {}
            if not _UIB_INDEX_WARNED:
                _UIB_INDEX_WARNED = True
                print("fetch: UiB index unavailable (%s) — pinning from the network, "
                      "not the mirror" % e, file=sys.stderr)
    return _UIB_INDEX or None


def mirror_current(aid):
    """The pruned mirror article for ``aid`` **iff the mirror row is still upstream's
    current version**, else ``None``.

    Current = the live index carries the id with the same ``revision`` *and* the same
    ``updated_at`` as the mirror row. Any difference — a revised article, an id the
    snapshot predates, an id upstream has deleted, an unreachable index — returns None,
    and the caller falls through to its network step. The pruning is ``prune_article``
    over the row's ``data``, exactly as ``load_any`` and a live fetch do, so a
    mirror-pinned capture is byte-identical to the fetched one.

    **The mirror row is looked up first, the index only after.** ``fetch_article`` is
    reachable from every short-lived process in the pipeline — each ``derive.py`` run, a
    ``stint.py submit`` that needs a target — and a machine with no ``.mirror/`` (or an id
    the snapshot never held) must not pay a 5 MB index download to be told what the
    mirror could not have answered anyway."""
    row = _mirror_row(aid)
    if row is None or not row.get("data"):
        return None                      # no mirror at all, not in the snapshot, or null
    idx = uib_index()
    if not idx:
        return None                      # index unreachable → never a stale pin
    live = idx.get(str(int(aid)))
    if live is None:
        return None                      # deleted upstream
    if (str(row.get("revision")), str(row.get("updated_at"))) != (str(live[0]), str(live[1])):
        return None                      # upstream has moved since the snapshot
    return prune_article(row["data"])


def captures_by_lemma(lemma):
    """Every committed capture carrying ``lemma`` as a written headword form
    (case-folded) — the cross-article lookup the packets need for homograph
    siblings and for an expression's component words (decisions entries 57
    and 60, 2026-09-01). Built once over ``sources/articles`` and cached in
    ``.cache/lemma-index.json``, rebuilt whenever the capture count changes;
    the capture set is the reach, so an article that was never pinned is
    invisible here — entry 58's mirror is what makes it complete."""
    global _LEMMA_INDEX
    adir = os.path.dirname(source_path(0))
    files = [f for f in os.listdir(adir) if f.endswith(".json")]
    if _LEMMA_INDEX is None:
        cached = store.read_json(LEMMA_INDEX, missing_ok=True) or {}
        if cached.get("count") == len(files):
            _LEMMA_INDEX = cached["index"]
    if _LEMMA_INDEX is None:
        index = {}
        for f in files:
            try:
                aid = int(f[:-5])
            except ValueError:
                continue
            art = store.read_json(os.path.join(adir, f), missing_ok=True) or {}
            for lem in art.get("lemmas") or []:
                w = (lem.get("lemma") or "").strip().casefold()
                if w:
                    ids = index.setdefault(w, [])
                    if aid not in ids:
                        ids.append(aid)
        os.makedirs(os.path.dirname(LEMMA_INDEX), exist_ok=True)
        store.write_json(LEMMA_INDEX, {"count": len(files), "index": index})
        _LEMMA_INDEX = index
    return list(_LEMMA_INDEX.get((lemma or "").strip().casefold(), []))


DANGLING_PATH = os.path.join(SOURCES, "dangling.json")
_DANGLING = None
_DANGLING_ASSESSED = None


def load_dangling():
    """Ids confirmed **dangling** (HTTP 404 in ordbokene's own data) — a committed registry
    (`sources/dangling.json`, a list of ``{id, reason}``). The deriver reads it to render a
    reference to such a target as plain definitional Norwegian rather than a broken link; keeping
    it on disk (not a live fetch) is what makes that deterministic for guardrail 4. Distinct from
    a merely *unfetched* target (a depth-two hover peek): those are valid, just not captured."""
    global _DANGLING
    if _DANGLING is None:
        data = store.read_json(DANGLING_PATH, missing_ok=True) or []
        _DANGLING = {int(e["id"]) for e in data}
    return _DANGLING


def mark_dangling(aid, reason=""):
    """Record ``aid`` as dangling (idempotent), updating disk and the in-process cache."""
    aid = int(aid)
    data = store.read_json(DANGLING_PATH, missing_ok=True) or []
    if any(int(e["id"]) == aid for e in data):
        return
    data.append({"id": aid, "reason": reason})
    data.sort(key=lambda e: int(e["id"]))
    store.write_json(DANGLING_PATH, data)
    if _DANGLING is not None:
        _DANGLING.add(aid)


def load_dangling_assessed():
    """Ids whose dangling-404 has been **assessed by a human as a no-issue** — an ``assessed``
    note set on the entry in ``sources/dangling.json``. The deriver mutes its ``dangling-ref``
    advisory for these (the 404 is recorded *and* reviewed), while an un-assessed dangling ref
    keeps firing every derive so a newly surfaced one is never silently lost. Mirrors the A8
    confirm registry; the front door is ``scripts/a8.py dangling``. Distinct from
    ``load_dangling`` (all registered ids, which drives plain-text rendering regardless)."""
    global _DANGLING_ASSESSED
    if _DANGLING_ASSESSED is None:
        data = store.read_json(DANGLING_PATH, missing_ok=True) or []
        _DANGLING_ASSESSED = {int(e["id"]) for e in data if e.get("assessed")}
    return _DANGLING_ASSESSED


def assess_dangling(aid, note):
    """Record a registered dangling id as assessed-and-fine (``assessed`` note + ``date`` on
    its entry). Raises if the id is not registered or is already assessed — assessment is a
    one-time act, like an A8 confirm. Rendering is unaffected (it reads only the id set)."""
    aid = int(aid)
    data = store.read_json(DANGLING_PATH, missing_ok=True) or []
    entry = next((e for e in data if int(e["id"]) == aid), None)
    if entry is None:
        raise KeyError("%d is not a registered dangling id" % aid)
    if entry.get("assessed"):
        raise ValueError("%d already assessed (%s)" % (aid, entry["assessed"]))
    entry["assessed"] = note
    entry["date"] = datetime.date.today().isoformat()
    store.write_json(DANGLING_PATH, data)
    if _DANGLING_ASSESSED is not None:
        _DANGLING_ASSESSED.add(aid)


# --- dangling-*def* registry (a distinct class from the 404 dangling-*ref* above) ----------
# ordbokene sometimes anchors a cross-reference at a ``#defN`` its (existing) target article
# lacks — komme til å → slumpe #def4, slumpe having only one def. The deriver renders these
# safely (bare-href, anchor dropped) regardless; this registry only mutes the ``dangling-def``
# advisory once a human has reviewed the case, mirroring the dangling-ref / A8 confirm pattern.
# Keyed by the whole (citer, target, defn) triple — a different citer to the same bad anchor is
# its own case. Lives in ``review/`` (an advisory assessment, not source data — it drives
# nothing in the rendered card), alongside the a8/a21 confirm registries.
REVIEW = os.path.join(DATA_ROOT, "review")
DANGLING_DEF_PATH = os.path.join(REVIEW, "dangling-def-assessed.jsonl")
_DANGLING_DEF_ASSESSED = None


def load_dangling_def_assessed():
    """The set of ``(citer, target, defn)`` triples whose dangling **definition_id** a human
    has assessed as a no-issue (``review/dangling-def-assessed.jsonl``: ``{citer, target, defn,
    note, date}``). The deriver mutes its ``dangling-def`` advisory for these; an unassessed one
    keeps firing every derive so a newly surfaced case is never silently lost. Front door:
    ``scripts/a8.py dangling-def``."""
    global _DANGLING_DEF_ASSESSED
    if _DANGLING_DEF_ASSESSED is None:
        data = store.read_jsonl(DANGLING_DEF_PATH)
        _DANGLING_DEF_ASSESSED = {(int(e["citer"]), int(e["target"]), int(e["defn"])) for e in data}
    return _DANGLING_DEF_ASSESSED


def assess_dangling_def(citer, target, defn, note):
    """Record a ``(citer, target, defn)`` dangling-def as assessed-and-fine (``note`` + ``date``).
    Raises if the triple is already assessed — a one-time act, like an A8 confirm. Rendering is
    unaffected (the deriver adapts regardless of this registry)."""
    citer, target, defn = int(citer), int(target), int(defn)
    data = store.read_jsonl(DANGLING_DEF_PATH)
    if any((int(e["citer"]), int(e["target"]), int(e["defn"])) == (citer, target, defn) for e in data):
        raise ValueError("%d cites %d#def%d — already assessed" % (citer, target, defn))
    data.append({"citer": citer, "target": target, "defn": defn, "note": note,
                 "date": datetime.date.today().isoformat()})
    store.write_jsonl(DANGLING_DEF_PATH, data, key=lambda e: (e["citer"], e["target"], e["defn"]))
    if _DANGLING_DEF_ASSESSED is not None:
        _DANGLING_DEF_ASSESSED.add((citer, target, defn))


# --- generic advisory acknowledgements --------------------------------------
# The assessed-memory pattern (A8 confirm, dangling mutes) generalised for advisory classes
# that carry no bespoke registry — a **standing, reviewed** advisory (a permanent structural
# fact, or a judgment call the advisory shape can't be taught) is acked once and then stays
# silent, so a normal green run shows zero advisory lines and any advisory that *does* appear
# is news (Robin, as of card 86, 2026-07-18; `docs/guardrails.md` § Acknowledging a standing
# advisory). Keyed ``(check, key)`` — the per-class ``key`` shape is the emitter's own (A10:
# ``article|display-form|gloss``; flattened-subsense: ``article|defn``), documented where the
# check is. Front door: ``scripts/a8.py ack``. Both consumers (``check_library`` at the gate,
# ``derive`` at its own stderr print) mute against this one registry.
ADVISORY_ACKS_PATH = os.path.join(REVIEW, "advisories-acked.jsonl")
_ADVISORY_ACKS = None


def load_advisory_acks():
    """``{(check, key): entry}`` — every advisory a human has acked as reviewed-and-fine."""
    global _ADVISORY_ACKS
    if _ADVISORY_ACKS is None:
        _ADVISORY_ACKS = {(e["check"], e["key"]): e for e in store.read_jsonl(ADVISORY_ACKS_PATH)}
    return _ADVISORY_ACKS


def is_advisory_acked(check, key):
    return (check, key) in load_advisory_acks()


def assess_advisory(check, key, note):
    """Record ``(check, key)`` as acked-and-fine (``note`` + ``date``). Raises if already acked —
    a one-time act. Validation that the advisory *currently fires* is the caller's job
    (``scripts/a8.py ack``), mirroring the confirm/dangling front doors."""
    data = store.read_jsonl(ADVISORY_ACKS_PATH)
    if any(e["check"] == check and e["key"] == key for e in data):
        raise ValueError("%s|%s already acked" % (check, key))
    data.append({"check": check, "key": key, "note": note,
                 "date": datetime.date.today().isoformat()})
    store.write_jsonl(ADVISORY_ACKS_PATH, data, key=lambda e: (e["check"], e["key"]))
    if _ADVISORY_ACKS is not None:
        _ADVISORY_ACKS[(check, key)] = data[-1]


def fetch_article(aid, force=False):
    """Return the pruned article for ``aid``, writing ``sources/articles/{id}.json``.

    Order: committed source (unless ``force``) → raw bootstrap capture (pruned, no network)
    → **the mirror, if its row is still current** (``mirror_current``; unless ``force``) →
    network. A same-content re-fetch rewrites identical bytes, and a mirror-pinned capture
    is byte-identical to the fetched one — the mirror step is a saving, not a variant.

    ``force=True`` means *read upstream*: it skips the committed capture and the mirror
    alike, so the one way to re-pin an article at its live version is unchanged.
    """
    aid = int(aid)
    path = source_path(aid)
    if not force:
        cached = store.read_json(path, missing_ok=True)
        if cached is not None:
            return cached
    boot = os.path.join(BOOTSTRAP, "%s.json" % aid)
    if not force and os.path.exists(boot):
        pruned = prune_article(store.read_json(boot))
    else:
        pruned = None if force else mirror_current(aid)
        if pruned is None:
            pruned = prune_article(_get(ARTICLE_URL % aid))
    store.write_json(path, pruned)
    return pruned


def fetch_article_transient(aid):
    """The pruned article for ``aid`` **without ever writing** ``sources/`` — the read-only
    convenience behind ``author_kit --brief``'s deeper-than-committed lookups. Order:
    committed source → gitignored ``.cache/articles/`` → bootstrap capture → network; a
    fresh result is cached under ``.cache/articles/`` only, so a briefing can never leave
    a stray capture for advisory 14 (Robin, 2026-07-13 — three strays in one day). The
    capture still lands in ``sources/`` via ``fetch_article`` iff the reference is kept
    (the normal derive path)."""
    aid = int(aid)
    cached = store.read_json(source_path(aid), missing_ok=True)
    if cached is not None:
        return cached
    tpath = os.path.join(TRANSIENT_CACHE, "%s.json" % aid)
    cached = store.read_json(tpath, missing_ok=True)
    if cached is not None:
        return cached
    boot = os.path.join(BOOTSTRAP, "%s.json" % aid)
    raw = store.read_json(boot) if os.path.exists(boot) else _get(ARTICLE_URL % aid)
    pruned = prune_article(raw)
    store.write_json(tpath, pruned)
    return pruned


def materialize_source(embedded_article, force=False):
    """Write a source file for an expression that exists **only** as a parent's embedded
    ``sub_article`` (its own id 404s standalone — e.g. ``pådra seg`` 125570 under ``pådra``
    47051). The embedded ``article`` object is already the ``{article_id, lemmas, body}``
    standalone shape; prune-again for canonical form and write it as a first-class source
    (Robin, 2026-07-12). Advisory 11 (embedded-vs-standalone divergence) is a no-op for
    these — there is no separate standalone to diverge from."""
    aid = int(embedded_article["article_id"])
    path = source_path(aid)
    if not force:
        cached = store.read_json(path, missing_ok=True)
        if cached is not None:
            return cached
    # Kept as a faithful capture: the embedded copy carries no paradigm_info, and the
    # deriver maps an empty tag set to "fixed expression" (postags.pos_en) — so a re-fetch
    # stays byte-identical and no synthetic tag is invented.
    pruned = prune_article(embedded_article)
    store.write_json(path, pruned)
    return pruned


def fetch_article_or_embedded(aid, embedded_article):
    """Fetch ``aid`` standalone, falling back to materializing the embedded copy on 404."""
    try:
        return fetch_article(aid)
    except urllib.error.HTTPError as e:
        if e.code == 404 and embedded_article is not None:
            return materialize_source(embedded_article)
        raise


class LemmaMismatch(Exception):
    """A fetched ref target whose lemmas include none the citing ref expected — the
    renumber guard (Robin, 2026-07-14): ordbokene recycling or renumbering an article id
    must be a loud boundary error, never a silently committed wrong capture."""


_LEMMA_ALT = re.compile(r"\[([^\]]*\|[^\]]*)\]")


def _lemma_keys(s):
    """Comparison keys for one lemma string: whitespace-normalized, with ordbokene's
    ``[a|b]`` alternation expanded to each variant plus the ``a/b`` display form — the
    bulk-prefetch triage showed embedded lemmas carry trailing spaces and alternation
    syntax that their standalone articles resolve (2026-07-14)."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    if not s:
        return set()
    keys = {s}
    m = _LEMMA_ALT.search(s)
    if m:
        for part in m.group(1).split("|"):
            keys.add(re.sub(r"\s+", " ", (s[:m.start()] + part + s[m.end():]).strip()))
        keys.add(_LEMMA_ALT.sub(lambda mm: mm.group(1).replace("|", "/"), s))
    return keys


def fetch_article_checked(aid, expected_lemmas, force=False):
    """``fetch_article`` + the renumber guard: the fetched article's lemmas must include at
    least one of ``expected_lemmas`` (the lemma strings the citing ``article_ref`` carries),
    compared on normalized keys (``_lemma_keys``). On a mismatch a *newly written* capture
    is removed and ``LemmaMismatch`` raised — a suspect id is triaged by a human, never
    committed. Empty ``expected_lemmas`` skips the guard (a ref carrying no lemma text has
    nothing to check against). The guard runs on whatever ``fetch_article`` returned —
    mirror-pinned or fetched: a renumbered id is caught on either path."""
    already = load_source(aid) is not None
    art = fetch_article(aid, force=force)
    expected = set()
    for e in (expected_lemmas or ()):
        expected |= _lemma_keys(e)
    if expected:
        got = set()
        for lem in art.get("lemmas", []):
            if isinstance(lem, dict):
                got |= _lemma_keys(lem.get("lemma"))
        if not (got & expected):
            if not already:
                try:
                    os.remove(source_path(aid))
                except OSError:
                    pass
            raise LemmaMismatch("article %d: fetched lemmas %s include none of the expected %s"
                                % (aid, sorted(got), sorted(expected)))
    return art


# --- lemma search ------------------------------------------------------------

def _search_cache_path(lemma):
    return os.path.join(SEARCH_CACHE, urllib.parse.quote(lemma, safe="") + ".json")


def search(lemma, force=False):
    """Exact-headword (``scope=e``) search → list of article ids. Cached (gitignored)."""
    path = _search_cache_path(lemma)
    if not force:
        cached = store.read_json(path, missing_ok=True)
        if cached is not None:
            return list(cached.get("bm", []))
    data = _get(SEARCH_URL % urllib.parse.quote(lemma))
    ids = list((data.get("articles") or {}).get("bm") or [])
    store.write_json(path, {"lemma": lemma, "bm": ids})
    return ids


# --- concepts ----------------------------------------------------------------

def ensure_concepts(force=False):
    """Snapshot ``concepts.json`` to ``sources/`` (bootstrap-aware). Returns the table."""
    if not force:
        cached = store.read_json(CONCEPTS_PATH, missing_ok=True)
        if cached is not None:
            return cached
    boot = os.path.join(BOOTSTRAP, "_concepts.json")
    if not force and os.path.exists(boot):
        raw = store.read_json(boot)
    else:
        raw = _get(CONCEPTS_URL)
    store.write_json(CONCEPTS_PATH, raw)
    return raw


def main():
    ap = argparse.ArgumentParser(description="ordbokene fetch layer (one-off use)")
    ap.add_argument("--article", type=int, metavar="ID", help="fetch one article into sources/")
    ap.add_argument("--search", metavar="LEMMA", help="scope=e search, print ids")
    ap.add_argument("--concepts", action="store_true", help="snapshot concepts.json")
    ap.add_argument("--force", action="store_true", help="ignore caches, hit the network")
    args = ap.parse_args()
    if args.concepts:
        c = ensure_concepts(force=args.force)
        print("concepts: %d codes -> %s" % (len(c.get("concepts", {})), CONCEPTS_PATH))
    if args.search:
        print("%s scope=e -> %s" % (args.search, search(args.search, force=args.force)))
    if args.article:
        a = fetch_article(args.article, force=args.force)
        print("article %s -> %s" % (a.get("article_id"), source_path(args.article)))
    if not (args.concepts or args.search or args.article):
        ap.print_help()


if __name__ == "__main__":
    main()
