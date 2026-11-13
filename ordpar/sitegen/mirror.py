# -*- coding: utf-8 -*-
"""The mirror, read-only: `bm-articles.jsonl`, one JSON row per Bokmål article.

The file lives in the MAIN worktree and is 205 MB, so it is never loaded whole. One index
pass parses every line (3.4 s for 94,238 rows, measured) and keeps two things: the byte
offset of each article id, and a lemma form -> ids map for the "other entries for this word"
count (decisions 24, refinement 2). Rows are then read back by `seek`.

Row shape: `{"id", "revision", "updated_at", "data"}`; `data` is the verbatim UiB article.
Nothing here writes to the mirror or anywhere near it.

`Listing` reads the mirror's two listing files beside it — `bm-listed.jsonl` (ordbokene's index)
and `bm-unlisted.json` (articles that left it; `since_404` null while ordbokene still serves
them) — and holds decisions 46: which unlisted articles the site KEEPS (in search, and a page
even once ordbokene answers 404) because they are translated library rows.
"""
import json
import os
import re
import unicodedata

from . import slim
from . import lemma_order


class Mirror(object):
    def __init__(self, path):
        self.path = path
        self.offsets = {}
        self.forms = {}
        self._fh = None
        self._cache = {}
        self._cache_order = []
        self.stored = {}          # id -> data (or None) for a kept article ordbokene 404s
        self.headless = set()     # ids of the jsonl with no headword (site decisions 163)
        self.overlay = None       # site decisions 182: the corrections `data` applies

    # --- the one pass --------------------------------------------------------

    def index(self):
        """Read the file once: offsets + the lemma-form map + the paradigm shapes of every
        article (`shapes`, the compact islands' site-wide table — `slim.compact_paradigm`,
        2026-10-20). Returns the row count."""
        self.offsets, self.forms, self.shapes = {}, {}, {}
        self.headless = set()
        with open(self.path, "rb") as f:
            while True:
                off = f.tell()
                line = f.readline()
                if not line:
                    break
                if not line.strip():
                    continue
                row = json.loads(line)
                aid = row["id"]
                self.offsets[aid] = off
                head = False
                for lem in (row.get("data") or {}).get("lemmas") or []:
                    form = lem.get("lemma")
                    if form:
                        self.forms.setdefault(form, []).append(aid)
                    if isinstance(form, str) and form.strip():
                        head = True
                if not head:
                    self.headless.add(aid)
                slim.compact_paradigm(row.get("data"), self.shapes)
        return len(self.offsets)

    def has_headword(self, aid):
        """Site decisions 163 (Robin, 2026-11-04): False for an article of the jsonl whose
        `lemmas` give no headword (`[]`: 134445, 136424, 136509 in the mirror of 2026-11-03),
        which gets no page, as ordbokene shows none ("500: Error"). True for any other id,
        a kept 404 included (its page has the stored copy's or the library row's spellings)."""
        return aid not in self.headless

    # --- random access -------------------------------------------------------

    def __contains__(self, aid):
        return aid in self.offsets

    def ids(self):
        return list(self.offsets)

    def row(self, aid):
        """The raw mirror row for `aid`, or None. Small LRU — a cross-reference target is
        read once per citing page, and a page's targets overlap heavily."""
        if aid in self._cache:
            return self._cache[aid]
        off = self.offsets.get(aid)
        if off is None:
            return None
        if self._fh is None:
            self._fh = open(self.path, "rb")
        self._fh.seek(off)
        row = json.loads(self._fh.readline())
        self._cache[aid] = row
        self._cache_order.append(aid)
        if len(self._cache_order) > 4096:
            self._cache.pop(self._cache_order.pop(0), None)
        return row

    def data(self, aid):
        """The article's `data`: the jsonl row's, or — for a kept article the jsonl no longer
        carries (decisions 46) — its stored copy, which may be None (the page then builds
        from the library row alone). Its `lemmas` in OUR order where the normalization log
        rules one (`lemma_order`, site decisions 93 (2)): every reader of the article's spellings
        on the site goes through here. With an overlay set (`set_overlay`, site decisions 182),
        the handover's corrections made in a copy: every reader of the article's text sees them."""
        if aid not in self.offsets and aid in self.stored:
            return lemma_order.reorder(aid, self.stored[aid])
        row = self.row(aid)
        if row is None:
            return None
        data = row.get("data")
        if self.overlay is not None:
            data = self.overlay.apply(aid, data)
        return lemma_order.reorder(aid, data)

    def raw_data(self, aid):
        """`data` without the overlay — ordbokene's text as of the snapshot, for the change
        notice's checker (`corrections.Checker`), which must compare the page with it."""
        if aid not in self.offsets and aid in self.stored:
            return lemma_order.reorder(aid, self.stored[aid])
        row = self.row(aid)
        return None if row is None else lemma_order.reorder(aid, row.get("data"))

    def set_overlay(self, overlay):
        """Site decisions 182: decide `overlay`'s rows against this mirror's raw rows (one extra
        pass over the file for the parents embedding a corrected expression) and apply them from
        now on in `data`. An empty overlay (no file, or no row) changes nothing and reads
        nothing."""
        if not overlay:
            self.overlay = None
            return overlay
        overlay.resolve(lambda aid: (self.row(aid) or {}).get("data"),
                        lambda ids: {k: v[0] for k, v in embedding_parents(self.path, ids).items()})
        self.overlay = overlay
        return overlay

    def touched(self, aid):
        """True when the overlay changes this article's data (its own text or an embedded copy)."""
        return self.overlay is not None and self.overlay.touches(aid)

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    # --- "other entries for this word" ---------------------------------------

    def other_entries(self, aid, forms=()):
        """How many OTHER mirror articles carry any of this article's lemma forms
        (decisions 24, refinement 2: the count is known at build time and rides on the page
        as one attribute; the chrome renders the line). `forms` stands in for the lemmas when
        the mirror has no data for the article (a kept 404, decisions 46)."""
        data = self.data(aid) or {}
        lemmas = [lem.get("lemma") for lem in data.get("lemmas") or []] or list(forms)
        others = set()
        for form in lemmas:
            for other in self.forms.get(form, ()):
                if other != aid:
                    others.add(other)
        return len(others)


def snapshot_stamp(mirror_path):
    """The snapshot's date from the mirror folder's `manifest.json` (its `created_at`), or
    None when the manifest is missing — the build stamps every page with it."""
    man = os.path.join(os.path.dirname(os.path.abspath(mirror_path)), "manifest.json")
    try:
        with open(man, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return None
    return m.get("created_at")


# --- listed, unlisted, kept (decisions 46) -----------------------------------

class Listing(object):
    """ordbokene's index as the mirror records it, and the site's rule over it (decisions 46,
    Robin 2026-10-18): search covers the LISTED articles plus the KEPT unlisted ones — an
    unlisted article that is a translated library row, unless a listed article sharing one of
    its headword strings is translated too (that one carries the English). A kept article
    keeps its page even once ordbokene answers 404; any other unlisted article has a page
    only while ordbokene serves it, and is never in search.

    When the listing files are missing (a synthetic mirror in a test), every article counts
    as listed and nothing is unlisted — the behaviour before decisions 46."""

    def __init__(self, mirror_path):
        self.folder = os.path.dirname(os.path.abspath(mirror_path))
        self.prefix = os.path.basename(mirror_path).split("-", 1)[0]       # "bm"
        self.listed = None
        path = os.path.join(self.folder, self.prefix + "-listed.jsonl")
        if os.path.exists(path):
            self.listed = set()
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.listed.add(json.loads(line)[0])
        self.unlisted = {}                    # id -> the date it began to 404, or None
        path = os.path.join(self.folder, self.prefix + "-unlisted.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    self.unlisted[int(k)] = (v or {}).get("since_404")
        self.kept = set()
        self.displaced = {}                   # unlisted translated id -> the listed ids

    def is_listed(self, aid):
        return self.listed is None or aid in self.listed

    def gone(self, aid):
        """Unlisted AND answering 404 at ordbokene (the jsonl no longer carries it)."""
        return self.unlisted.get(aid) is not None

    def in_search(self, aid):
        return self.is_listed(aid) or aid in self.kept

    def has_page(self, aid):
        """Every article ordbokene serves has a page; of the ones it 404s, only the kept."""
        return not self.gone(aid) or aid in self.kept

    def kept_404(self):
        return sorted(i for i in self.kept if self.gone(i))

    def resolve(self, translated, forms_of, listed_by_form):
        """Decide the kept set and return it. `translated`: the translated ids (the site's
        own test, `coverage.complete_strict`); `forms_of(aid)`: the headword strings of an
        unlisted article; `listed_by_form`: headword string -> article ids (only the LISTED
        ones among them count)."""
        self.kept, self.displaced = set(), {}
        for aid in sorted(self.unlisted):
            if aid not in translated:
                continue
            rivals = sorted({j for f in forms_of(aid) for j in listed_by_form.get(f, ())
                             if j != aid and j in translated and j not in self.unlisted
                             and self.is_listed(j)})
            if rivals:
                self.displaced[aid] = rivals
            else:
                self.kept.add(aid)
        return self.kept

    def stored_copy(self, aid):
        """The mirror's stored copy of an unlisted article (`bm/404/<id>.json`, else
        `bm/unlisted/<id>.json`) as a `data` dict, or None when there is none or it carries
        no lemmas — the mirror's seed wrote `{}` for every 404 copy (2026-09-25), so on
        2026-10-18 it is None for all of them."""
        for sub in ("404", "unlisted"):
            path = os.path.join(self.folder, self.prefix, sub, "%d.json" % aid)
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                except ValueError:
                    return None
                return data if isinstance(data, dict) and data.get("lemmas") else None
        return None

    def counts(self):
        """The decisions-46 counts `build.json` and the index manifest record."""
        served = [i for i, d in self.unlisted.items() if d is None]
        return {"listed": len(self.listed) if self.listed is not None else None,
                "unlisted_served": len(served),
                "unlisted_404": len(self.unlisted) - len(served),
                "kept": len(self.kept),
                "kept_served": sum(1 for i in self.kept if not self.gone(i)),
                "kept_404": sum(1 for i in self.kept if self.gone(i)),
                "left_out_of_search": len(self.unlisted) - len(self.kept),
                "left_out_of_search_served": sum(1 for i in served if i not in self.kept),
                "unlisted_translated_displaced": len(self.displaced)}


def decide_kept(listing, mirror_path, library, translated, listed_by_form, served_lemmas):
    """The one decisions-46 decision both builds make, so they cannot disagree.

    `library` id -> row; `translated` the set of translated ids; `listed_by_form` headword
    string -> ids over the mirror's rows; `served_lemmas(aid)` the lemma strings of an
    article the jsonl carries ([] otherwise). An unlisted article's headword strings are its
    library row's forms, its mirror lemmas and — for one ordbokene 404s — the lemmas of the
    copy its first parent embeds (raw, so `[ha|få] papir på` meets its listed namesake),
    each also NFC-normalised. Returns `embedding_parents` for the 404'd translated ones: the
    credit link's parent and the index entry's lemmas."""
    gone = [i for i in listing.unlisted if listing.gone(i) and i in translated]
    embedded = embedding_parents(mirror_path, gone)

    def forms_of(aid):
        fs = [l.get("form") for l in (library.get(aid) or {}).get("lemmas") or []]
        fs += list(served_lemmas(aid))
        art = (embedded.get(aid) or (None, None))[1] or {}
        fs += [l.get("lemma") for l in art.get("lemmas") or []]
        fs = [f for f in fs if f]
        return list(dict.fromkeys(fs + [unicodedata.normalize("NFC", f.strip()) for f in fs]))

    listing.resolve(translated, forms_of, listed_by_form)
    return embedded


_ARTICLE_ID = re.compile(r'"article_id": ?(\d+)')


def embedding_parents(mirror_path, targets):
    """The mirror articles that embed each target as a `sub_article`, in the mirror's order,
    and the FIRST one's embedded copy of it: `{id: ([parent ids], embedded article)}`; a
    target nothing embeds is absent. One pass; a line is parsed only when it carries a
    sub-article and names a target."""
    targets = set(targets)
    out = {}
    if not targets:
        return out

    def walk(node, parent):
        if isinstance(node, dict):
            if node.get("type_") == "sub_article" and node.get("article_id") in targets:
                par, _art = out.setdefault(node["article_id"], ([], node.get("article")))
                if parent not in par:
                    par.append(parent)
            for v in node.values():
                walk(v, parent)
        elif isinstance(node, list):
            for v in node:
                walk(v, parent)

    with open(mirror_path, encoding="utf-8") as f:
        for line in f:
            if '"sub_article"' not in line:
                continue
            if not targets.intersection(int(m) for m in _ARTICLE_ID.findall(line)):
                continue
            row = json.loads(line)
            walk((row.get("data") or {}).get("body"), row["id"])
    return out
