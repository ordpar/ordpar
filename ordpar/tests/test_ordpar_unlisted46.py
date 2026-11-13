# -*- coding: utf-8 -*-
"""Pins decisions 46 (Robin, 2026-10-18): unlisted articles on the site — what we translated stays.
`ordpar/sitegen/mirror.py` `Listing` / `decide_kept` / `embedding_parents`, `ordpar/build_index.py`
`search_scope`, `ordpar/sitegen/page.py` `credit_line`:

* The kept rule: an UNLISTED article is kept when it is translated, unless a LISTED article that
  shares one of its headword strings is translated too (*vaffel*, *det aller helligste*: the
  listed namesake carries the English). An untranslated unlisted article is never kept.
* Search covers the listed articles plus the kept ones; every other unlisted article is out of
  the lookup index and `translated.json` (*krone* 32274's case: served, not ours, not in search).
* Pages: every served article has one; of the 404'd, only the kept.
* A 404'd kept article's index entry comes from the copy its first parent embeds (raw, so
  `[ha|få] papir på` is expanded into its variants), else from its library row.
* The credit line no longer links each article (decisions 63, Robin 2026-10-19: no per-article
  source link): it sits in every page's footer and links ordbokene.no in general; until then a
  404'd kept article linked its first parent, else ordbokene's search for its headword.

Synthetic mirror and library only: the real ones are not read."""

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

import build_index as B  # noqa: E402
from ordpar.sitegen import mirror as M  # noqa: E402


def _data(aid, lemma, pos="NOUN", body=None):
    return {"article_id": aid, "body": body or {"definitions": []},
            "lemmas": [{"lemma": lemma, "hgno": 0,
                        "paradigm_info": [{"tags": [pos], "inflection": [{"word_form": lemma}]}]}]}


def _sub(aid, lemma):
    return {"type_": "sub_article", "article_id": aid, "lemmas": [{"lemma": lemma}],
            "article": {"article_id": aid, "word_class": "EXPR",
                        "lemmas": [{"hgno": 0, "lemma": lemma}], "body": {}}}


# id -> (headword, in the jsonl?) ; listed / unlisted below
SERVED = {
    1: _data(1, "krone"),                 # listed, translated
    2: _data(2, "krone"),                 # unlisted, served, not a library row
    3: _data(3, "vaffel"),                # listed, translated
    4: _data(4, "vaffel"),                # unlisted, served, translated: displaced by 3
    5: _data(5, "heilnorsk", "ADJ"),      # unlisted, served, translated: KEPT
    7: _data(7, "det aller helligste", "EXPR"),   # listed, translated
    9: _data(9, "mer", "ADV", {"definitions": [_sub(8, "med mer")]}),
    10: _data(10, "med", "ADP", {"definitions": [_sub(8, "med mer")]}),
    12: _data(12, "papir", "NOUN", {"definitions": [_sub(11, "[ha|få] papir på")]}),
    14: _data(14, "uoversatt"),           # unlisted, served, an untranslated library row
}
LISTED = [1, 3, 7, 9, 10, 12]
UNLISTED = {2: None, 4: None, 5: None, 14: None,
            6: "2026-09-25",     # det aller helligste, 404: displaced by 7, no page
            8: "2026-09-25",     # med mer, 404, embedded in 9 and 10: KEPT
            11: "2026-09-25",    # [ha|få] papir på, 404, embedded in 12: KEPT
            13: "2026-09-25"}    # gammelt ord, 404, embedded nowhere: KEPT, credit = search
LIBRARY = {
    1: "krone", 3: "vaffel", 4: "vaffel", 5: "heilnorsk", 6: "det aller helligste",
    7: "det aller helligste", 8: "med mer", 11: "ha/få papir på", 13: "gammelt ord",
    14: "uoversatt",
}
TRANSLATED = [1, 3, 4, 5, 6, 7, 8, 11, 13]


class Unlisted46(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="unl46-")
        cls.mirror = os.path.join(cls.tmp, "bm-articles.jsonl")
        with open(cls.mirror, "w", encoding="utf-8") as fh:
            for aid in sorted(SERVED):
                fh.write(json.dumps({"id": aid, "revision": "1", "updated_at": "",
                                     "data": SERVED[aid]}, ensure_ascii=False) + "\n")
        with open(os.path.join(cls.tmp, "bm-listed.jsonl"), "w", encoding="utf-8") as fh:
            for aid in LISTED:
                fh.write(json.dumps([aid, SERVED[aid]["lemmas"][0]["lemma"], "1", ""],
                                    ensure_ascii=False) + "\n")
        with open(os.path.join(cls.tmp, "bm-unlisted.json"), "w", encoding="utf-8") as fh:
            json.dump({str(k): {"since_404": v, "revision": "0"} for k, v in UNLISTED.items()},
                      fh)
        os.makedirs(os.path.join(cls.tmp, "bm", "404"))
        for aid, since in UNLISTED.items():
            if since:   # the mirror's seed wrote `{}` for every 404 copy
                with open(os.path.join(cls.tmp, "bm", "404", "%d.json" % aid), "w") as fh:
                    fh.write("{}")
        cls.library = {i: {"lemmas": [{"form": f, "homograph": None}],
                           "pos_en": "fixed expression" if " " in f else "noun"}
                       for i, f in LIBRARY.items()}
        cls.listing = M.Listing(cls.mirror)
        mir = M.Mirror(cls.mirror)
        mir.index()
        cls.embedded = M.decide_kept(
            cls.listing, cls.mirror, cls.library, set(TRANSLATED), mir.forms,
            lambda i: [l["lemma"] for l in (mir.data(i) or {}).get("lemmas") or []])
        mir.close()
        stats = {}
        entries = list(B.read_mirror(cls.mirror))
        cls.entries, cls.translated, _ = B.search_scope(cls.mirror, entries, cls.library,
                                                        TRANSLATED, stats)
        cls.stats = stats
        heads, forms, words = B.build_tables(cls.entries, None, stats)
        B.write_index(cls.tmp, heads, forms, words, cls.translated, stats)
        cls.idx = B.Index(os.path.join(cls.tmp, "index"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def ids(self, q):
        return sorted(a["id"] for g in self.idx.lookup(q)["heads"] for a in g["articles"])

    def test_kept_rule(self):
        self.assertEqual(self.listing.kept, {5, 8, 11, 13})
        self.assertEqual(self.listing.displaced, {4: [3], 6: [7]})
        self.assertEqual(self.listing.kept_404(), [8, 11, 13])

    def test_pages(self):
        for aid in (1, 2, 4, 5, 14, 8, 11, 13):
            self.assertTrue(self.listing.has_page(aid), aid)
        self.assertFalse(self.listing.has_page(6))

    def test_search_scope(self):
        self.assertEqual([e[0] for e in self.entries], [1, 3, 5, 7, 8, 9, 10, 11, 12, 13])
        self.assertEqual(self.translated, [1, 3, 5, 7, 8, 11, 13])
        self.assertEqual(self.ids("krone"), [1])           # 2: served, not ours: out
        self.assertEqual(self.ids("vaffel"), [3])          # 4: displaced by its namesake
        self.assertEqual(self.ids("det aller helligste"), [7])
        self.assertEqual(self.ids("heilnorsk"), [5])
        self.assertEqual(self.ids("med mer"), [8])
        self.assertEqual(self.ids("gammelt ord"), [13])
        self.assertEqual(self.ids("uoversatt"), [])
        # from the parent's embedded copy, raw, so the alternation is expanded
        self.assertEqual(self.ids("ha papir på"), [11])
        self.assertEqual(self.ids("få papir på"), [11])
        self.assertEqual([s["word"] for s in self.idx.suggest("kro")], ["krone"])
        self.assertEqual(self.stats["unlisted46_kept_404_index_from_parent_embedded_copy"], 2)
        self.assertEqual(self.stats["unlisted46_kept_404_index_from_library_row"], 1)

    def test_parents_in_mirror_order(self):
        self.assertEqual(self.embedded[8][0], [9, 10])
        self.assertEqual(self.embedded[11][0], [12])
        self.assertNotIn(13, self.embedded)

    def test_counts(self):
        c = self.listing.counts()
        self.assertEqual((c["listed"], c["unlisted_served"], c["unlisted_404"], c["kept"],
                          c["kept_served"], c["kept_404"], c["left_out_of_search"]),
                         (6, 4, 4, 4, 1, 3, 4))

    def test_stored_copy_and_mirror_fallback(self):
        self.assertIsNone(self.listing.stored_copy(8))      # `{}` is no copy
        mir = M.Mirror(self.mirror)
        mir.index()
        mir.stored[8] = None
        self.assertIsNone(mir.data(8))
        self.assertEqual(mir.other_entries(13, ["krone"]), 2)
        self.assertEqual(mir.other_entries(1), 1)
        mir.close()

    def test_credit_links_ordbokene_in_general(self):
        # decisions 63 replaced the per-article source link and its decisions-46 fallbacks
        from ordpar.sitegen import page
        self.assertFalse(hasattr(page, "credit_source"))
        for k in ("source_link", "source_link_parent", "source_link_search"):
            self.assertNotIn(k, page.EN)
        line = page.credit_line(page.EN)
        self.assertIn('href="https://ordbokene.no/"', line)
        self.assertNotIn("ordbokene.no/nob/bm/", line)

    def test_no_listing_files_means_all_listed(self):
        bare = os.path.join(self.tmp, "solo")
        os.makedirs(bare)
        path = os.path.join(bare, "bm-articles.jsonl")
        open(path, "w").close()
        L = M.Listing(path)
        self.assertTrue(L.is_listed(12345) and L.in_search(12345) and L.has_page(12345))


if __name__ == "__main__":
    unittest.main()
