# -*- coding: utf-8 -*-
"""Which face an article gets, and where its row comes from.

The rule (site decisions 27 (1), 2): a library row that passes `coverage.complete_strict`
is TRANSLATED — the page shows the authored English beside the Norwegian. Every other
article is the Norwegian page: no library row at all (72k of the 94,238), or a row whose
English is unfinished, which ships as its own derived Norwegian and never as a half.

`Store` is the one place that decides, and the one place that derives. Deriving is
`derive.derive_row(aid, concepts, advisories, art=fetch.prune_article(data))` — 0.64 ms per
row, writing nothing — memoized here because a page's cross-reference targets overlap.
"""
import collections
import json
import os
import re
import time

from . import deck

derive = deck.derive
coverage = deck.coverage
fetch = deck.fetch
markup = deck.markup


#: where the public repository keeps the mirror's files, `bm-concepts.json` among them, under
#: its data folder (`ORDBOK_DATA_DIR`; `export_public.py` `MIRROR_OUT`)
PUBLIC_MIRROR_DIR = "bokmalsordboka"


def _read_concepts(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: (v.get("expansion") or k) for k, v in (raw.get("concepts") or {}).items()}


def mirror_concepts(mirror_path):
    """The abbreviation table a mirror article is derived against (site decisions 29, ruled
    (3), 2026-09-25): the mirror's own `bm-concepts.json`, fetched with the articles and so
    dated with them (`scripts/mirror.py`, `main` 1487b7c1), beside `bm-articles.jsonl`; the
    deck's committed `sources/concepts.json` (`derive.concepts_map()`) only when the mirror
    has none. Same shape either way. Returns `(table, source path)`.

    Decisions 184 (the outsider test of the public repository, finding 2): a mirror with no
    table of its own (a test's synthetic one) and no `sources/concepts.json` (the public
    repository has none) took `derive.concepts_map()`, which fetched the table from ord.uib.no
    and wrote it under the data folder. Such a mirror now gets the public repository's copy of
    the mirror's table, `<data folder>/bokmalsordboka/bm-concepts.json`; `derive.concepts_map()`
    is reached only when neither file is there."""
    path = os.path.join(os.path.dirname(os.path.abspath(mirror_path)), "bm-concepts.json")
    if os.path.exists(path):
        return _read_concepts(path), path
    if not os.path.exists(fetch.CONCEPTS_PATH):
        public = os.path.join(fetch.DATA_ROOT, PUBLIC_MIRROR_DIR, "bm-concepts.json")
        if os.path.exists(public):
            return _read_concepts(public), public
    return derive.concepts_map(), fetch.CONCEPTS_PATH


class Store(object):
    def __init__(self, mirror, library_rows, cache_size=8192):
        self.mirror = mirror
        self.library = {r["id"]: r for r in library_rows}
        self.concepts, self.concepts_source = mirror_concepts(mirror.path)
        self.advisories = []                       # (tag, message) — collected, never written
        self.errors = collections.Counter()        # DeriveError by message head
        self.error_ids = []
        self.missing = set()                       # cited ids in neither library nor mirror
        # expressions with no row of their own, derived from the copy their parent embeds
        # (`embedded_expr`): id -> row or None. They get no page and no search entry, so
        # the face never draws a link to one (`SiteFace.resolvable`).
        self.embedded = {}
        self._cache = collections.OrderedDict()
        self._cache_size = cache_size
        # site decisions 182: the raw derivations of the articles the overlay corrects, for the
        # change notice's checker (`raw_derived`, `raw_embedded_expr`)
        self._raw = {}
        self._raw_embedded = {}
        self.derived_count = 0
        self.derive_seconds = 0.0

    # --- rows ----------------------------------------------------------------

    def derived(self, aid):
        """The Norwegian row derived from the mirror, or None (no mirror row, or the
        deriver refused the article's POS tag set)."""
        if aid in self._cache:
            self._cache.move_to_end(aid)
            return self._cache[aid]
        data = self.mirror.data(aid)
        row = None
        if data is not None:
            t0 = time.perf_counter()
            try:
                row = derive.derive_row(aid, self.concepts, self.advisories,
                                        art=fetch.prune_article(data))
                self.derived_count += 1
            except derive.DeriveError as e:
                self.errors[str(e).split(":", 1)[-1].strip()[:80]] += 1
                self.error_ids.append(aid)
                row = None
            self.derive_seconds += time.perf_counter() - t0
        self._cache[aid] = row
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return row

    def _derive(self, aid, art):
        t0 = time.perf_counter()
        try:
            row = derive.derive_row(aid, self.concepts, [], art=fetch.prune_article(art))
        except derive.DeriveError:
            row = None
        self.derive_seconds += time.perf_counter() - t0
        return row

    def raw_derived(self, aid):
        """`derived` from the RAW mirror (site decisions 182): ordbokene's text as of the
        snapshot, without the overlay's corrections — what the change notice's checker compares
        the page with. The same row as `derived` for every article the overlay leaves alone.
        Its advisories and errors are not collected (the page's own derivation reports them)."""
        if not getattr(self.mirror, "touched", None) or not self.mirror.touched(aid):
            return self.derived(aid)
        if aid not in self._raw:
            data = self.mirror.raw_data(aid)
            self._raw[aid] = None if data is None else self._derive(aid, data)
        return self._raw[aid]

    def raw_embedded_expr(self, parent_id, eid):
        """`embedded_expr` from the parent's RAW copy (site decisions 182), as `raw_derived`."""
        if not getattr(self.mirror, "touched", None) or not self.mirror.touched(parent_id):
            return self.embedded_expr(parent_id, eid)
        if eid not in self._raw_embedded:
            copy = _embedded_copy(self.mirror.raw_data(parent_id), eid)
            self._raw_embedded[eid] = None if copy is None else self._derive(eid, copy)
        return self._raw_embedded[eid]

    def status(self, aid):
        """`("en" | "no", row)` for an article id, or None when it cannot be rendered at all.

        `"en"` means the translated face (a complete library row); `"no"` the Norwegian one —
        the library row's own derived Norwegian where a row exists, else the mirror's.
        """
        row = self.library.get(aid)
        if row is not None:
            return ("en" if coverage.complete_strict(row) else "no"), row
        row = self.derived(aid)
        if row is None:
            self.missing.add(aid)
            return None
        return "no", row

    def row(self, aid):
        st = self.status(aid)
        return None if st is None else st[1]

    def embedded_expr(self, parent_id, eid):
        """An expression the parent `parent_id` cites but neither the library nor the mirror's
        jsonl carries (404'd at ordbokene, or never mirrored), derived from the whole copy the
        parent's own mirror data embeds — the `sub_article` node's `article`, which is the
        `{article_id, lemmas, body}` shape the deck materializes from the same copy
        (`fetch.materialize_source`). None when the parent carries no such copy or the
        deriver refuses it. Memoized by expression id: one expression has one copy per
        parent, and the first parent's is used."""
        if eid in self.embedded:
            return self.embedded[eid]
        row, copy = None, _embedded_copy(self.mirror.data(parent_id), eid)
        if copy is not None:
            t0 = time.perf_counter()
            try:
                row = derive.derive_row(eid, self.concepts, self.advisories,
                                        art=fetch.prune_article(copy))
                self.derived_count += 1
            except derive.DeriveError as e:
                self.errors[str(e).split(":", 1)[-1].strip()[:80]] += 1
                self.error_ids.append(eid)
            self.derive_seconds += time.perf_counter() - t0
        self.embedded[eid] = row
        return row

    def expr_row(self, parent_id, eid):
        """The row for one of `parent_id`'s expressions: its own (library or mirror), else
        the one derived from the parent's embedded copy (`embedded_expr`)."""
        r = self.row(eid)
        return r if r is not None else self.embedded_expr(parent_id, eid)

    def is_embedded_only(self, aid):
        """True for an expression whose only row is the one derived from a parent's copy."""
        return self.embedded.get(aid) is not None

    # --- the closure a page's markup layer must resolve against ---------------

    def page_library(self, aid):
        """Every row `markup` needs to render the page for `aid`:

        the article and its expression rows (both rendered in full), every id they cite (each
        is a link — `face.SiteFace.resolvable` asks for its row), and those targets' own
        expression rows (a senseless target's inlined mini rendered them until decisions 80;
        no longer read, still loaded). Depth stops there.
        """
        lib = {}

        def add(i):
            if i in lib:
                return None
            r = self.row(i)
            if r is not None:
                lib[i] = r
            return r

        def add_expr(parent, eid):
            if eid in lib:
                return None
            r = self.expr_row(parent, eid)
            if r is not None:
                lib[eid] = r
            return r

        root = add(aid)
        if root is None:
            return None, lib
        level1 = [root]
        for eid in root.get("exprs") or []:
            r = add_expr(aid, eid)
            if r is not None:
                level1.append(r)
        cited = set()
        for r in level1:
            cited |= cited_ids(r)
        # decisions 153: the root's own "Se:" lines are links on its page (an embedded
        # expression's never show, so theirs are not loaded)
        cited |= see_ids(root)
        for tid in sorted(cited):
            if self.is_embedded_only(tid):
                continue        # one of the page's own expressions, already in; no mini
            t = add(tid)
            if t is not None:
                for eid in t.get("exprs") or []:
                    add_expr(tid, eid)
        return root, lib


def _embedded_copy(data, eid):
    """The `article` of the `sub_article` node for `eid` inside a raw article, or None."""
    stack = [(data or {}).get("body")]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            if n.get("type_") == "sub_article" and n.get("article_id") == eid:
                art = n.get("article")
                if isinstance(art, dict) and art.get("body"):
                    return dict(art, article_id=eid)
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
    return None


# --- what a row cites -------------------------------------------------------

_HREF = re.compile(r"^/nob/bm/(\d+)")


def iter_strings(row):
    """Every marker-bearing string in a row — BOTH faces. `derive.referenced_ids` reads the
    derived Norwegian only, and authored English cites hrefs of its own (a `compare {…}`
    collapse the Norwegian has no counterpart for), so a page built from it alone would meet
    a cross-reference whose target is not in the library."""
    ety = row.get("etymology") or {}
    for seg in (ety.get("no") or []) + (ety.get("en") or []):
        yield seg
    for s in row.get("senses") or []:
        for u in [s] + (s.get("subs") or []):
            for seg in (u.get("no") or []) + (u.get("en") or []):
                yield seg
            for ex in u.get("ex") or []:
                for part in ex:
                    if isinstance(part, str):
                        yield part
            for e in u.get("ex_added") or []:
                yield e.get("no")
                yield e.get("en")


def see_ids(row):
    """The article ids a fixed expression's "Se:" lines cite (the units' `see` field, site
    decisions 153) — drawn on its own page only, so read for a page's root alone."""
    ids = set()
    for s in row.get("senses") or []:
        for u in [s] + (s.get("subs") or []):
            for seg in u.get("see") or []:
                for href in markup.hrefs(seg or ""):
                    m = _HREF.match(href)
                    if m:
                        ids.add(int(m.group(1)))
    return ids


def cited_ids(row):
    """The article ids a row cites, from both faces, plus its compound links and its own
    expression refs."""
    ids = set(row.get("exprs") or [])
    for seg in iter_strings(row):
        for href in markup.hrefs(seg or ""):
            m = _HREF.match(href)
            if m:
                ids.add(int(m.group(1)))
    for s in row.get("senses") or []:
        for u in [s] + (s.get("subs") or []):
            for b in u.get("comp") or []:
                for it in b.get("items") or []:
                    m = _HREF.match(it.get("href") or "")
                    if m:
                        ids.add(int(m.group(1)))
    return ids
