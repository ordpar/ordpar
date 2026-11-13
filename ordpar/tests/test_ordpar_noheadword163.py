# -*- coding: utf-8 -*-
"""Pins site decisions 163 (Robin, 2026-11-04: "Yes, as recommended"): an article whose data gives
no headword (`lemmas: []` — 134445, 136424 and 136509 in the mirror of 2026-11-03) gets no page,
as ordbokene has none (its own pages for them answer "500: Error").

* `sitegen.mirror.Mirror.has_headword`: False for a jsonl row with no lemma, or only empty or
  blank ones; True for any other row and for an id the jsonl does not carry (a kept 404 is built
  from its stored copy or its library row, which have spellings).
* The build (`build_site.py --ids`, run on a synthetic mirror and an empty library, into a
  temporary folder): no page for the headword-less article, and a page an earlier build wrote
  for it is removed; `build.json` counts one page and records the article under
  `no_headword_163` (not as a failure); no snippet for it; the front page lists only the other;
  the offline copy, which packs every page in `out/bm-en/` (`build_offline.article_ids`), finds
  only the other.
* The search index has no entry for it (`build_index.build_tables` skips an article with neither
  a headword nor an inflected form — unchanged by 163, pinned here).

Synthetic data only: the real mirror is not read. The build runs in a subprocess (a few seconds).
Fails on the code before 163 (`has_headword` missing; the page written).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)

import build_index as B  # noqa: E402
import build_offline as O  # noqa: E402
from ordpar.sitegen import mirror as M  # noqa: E402


def _art(aid, lemmas, text):
    return {"id": aid, "revision": "1", "updated_at": "",
            "data": {"article_id": aid, "lemmas": lemmas, "status": 8,
                     "body": {"definitions": [{"type_": "definition", "id": 1, "elements": [
                         {"type_": "explanation", "content": text, "items": []}]}]}}}


ROWS = [
    _art(1, [{"lemma": "hus", "hgno": 0, "id": 11, "paradigm_info": []}], "bygning"),
    _art(2, [], "forkortelse for noe"),                                   # 134445's shape
    _art(3, [{"lemma": " ", "hgno": 0, "id": 13, "paradigm_info": []}], "tom"),
]


def _write_mirror(folder):
    path = os.path.join(folder, "bm-articles.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in ROWS:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


class HasHeadword(unittest.TestCase):

    def test_mirror_index(self):
        tmp = tempfile.mkdtemp()
        try:
            m = M.Mirror(_write_mirror(tmp))
            m.index()
            self.assertTrue(m.has_headword(1))
            self.assertFalse(m.has_headword(2))
            self.assertFalse(m.has_headword(3))
            self.assertTrue(m.has_headword(99))         # not in the jsonl: a kept 404's case
            m.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_index_has_no_entry(self):
        _heads, _forms, words = B.build_tables([B.entry(1, ROWS[0]["data"]), B.entry(2, ROWS[1]["data"])],
                                               None, {})
        self.assertEqual(sorted(words), [1])


class BuildMakesNoPage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        mirror = _write_mirror(cls.tmp)
        library = os.path.join(cls.tmp, "articles.jsonl")
        open(library, "w").close()
        # marked as gated, so the public repository's build (no scripts/triage.py) takes it too
        # (decisions 184, `sitegen/gate.py`); the private side gates it with triage as before
        from ordpar.sitegen import gate
        gate.write_marker(library, 0, 0)
        cls.out = os.path.join(cls.tmp, "out")
        cls.snippets = os.path.join(cls.tmp, "snippets.json")
        # a page an earlier build wrote for the headword-less article
        os.makedirs(os.path.join(cls.out, "bm-en", "2"))
        with open(os.path.join(cls.out, "bm-en", "2", "index.html"), "w") as f:
            f.write("<!doctype html>\n<title>2</title>\n")
        cls.proc = subprocess.run(
            [sys.executable, os.path.join(ORDPAR, "build_site.py"), "--mirror", mirror,
             "--articles", library, "--ids", "1", "2", "3", "--out", cls.out,
             "--snippets", cls.snippets],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=300)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr.decode("utf-8", "replace")[-2000:])

    def page(self, aid):
        return os.path.join(self.out, "bm-en", str(aid), "index.html")

    def test_pages(self):
        self.assertTrue(os.path.isfile(self.page(1)))
        self.assertFalse(os.path.exists(self.page(2)))           # the earlier build's page removed
        self.assertFalse(os.path.exists(os.path.dirname(self.page(2))))
        self.assertFalse(os.path.exists(self.page(3)))

    def test_build_json(self):
        with open(os.path.join(self.out, "build.json"), encoding="utf-8") as f:
            b = json.load(f)
        self.assertEqual(b["pages"], 1)
        self.assertEqual(b["untranslated"], 1)
        self.assertEqual(b["no_headword_163"], {"ids": [2, 3], "pages_removed": [2]})
        self.assertEqual(b["failure_count"], 0)
        self.assertEqual(b["search_128"]["noindex_articles"], 1)

    def test_snippets_and_front_page(self):
        with open(self.snippets, encoding="utf-8") as f:
            self.assertEqual(sorted(json.load(f)), ["1"])
        with open(os.path.join(self.out, "index.html"), encoding="utf-8") as f:
            front = f.read()
        self.assertIn("/bm-en/1/", front)
        self.assertNotIn("/bm-en/2/", front)
        self.assertNotIn("/bm-en/3/", front)

    def test_offline_copy_finds_only_the_page(self):
        self.assertEqual(O.article_ids(self.out), [1])


class SiteStatsCountsOnlyShown(unittest.TestCase):
    # the About page's totals (`site_stats.measure`) count the articles shown: an article with no
    # headword has no page here and none at ordbokene, so it is not counted (the session, 2026-11-04)
    def test_not_counted(self):
        import site_stats
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "bm-articles.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for r in ROWS:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            got = site_stats.measure(path, rows=[])
            self.assertEqual(got["articles"]["all"], 1, got["articles"])
            # `lemmas: []` in the data but a library row (*på tide* 131994): it has a page, so it
            # counts, translated (the session, 2026-11-04: the build's first skip took these too)
            got = site_stats.measure(path, rows=[{"id": 2, "lemmas": [{"form": "på tide"}]}])
            self.assertEqual((got["articles"]["all"], got["articles"]["translated"]), (2, 1), got["articles"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TheBuiltSite(unittest.TestCase):
    # over the real build (`ordpar/out/`, skipped without one): the three with no headword
    # anywhere have no page; the three set phrases whose data has `lemmas: []` but whose
    # translated library rows give the line keep theirs (the session, 2026-11-04)
    def test_pages(self):
        out = os.path.join(ORDPAR, "out", "bm-en")
        if not os.path.isfile(os.path.join(out, "1", "index.html")):
            self.skipTest("no built site")
        for aid in (134445, 136424, 136509):
            self.assertFalse(os.path.exists(os.path.join(out, str(aid), "index.html")), aid)
        for aid, word in ((131994, "på tide"), (132570, "til topps"), (135850, "til vanns")):
            with open(os.path.join(out, str(aid), "index.html"), encoding="utf-8") as f:
                self.assertIn("<title>%s — " % word, f.read(), aid)


if __name__ == "__main__":
    unittest.main()
