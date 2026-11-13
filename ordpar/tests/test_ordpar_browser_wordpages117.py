"""Site decisions 117 (Robin, 2026-10-24/25): the word pages and form pages in a browser
(headless Edge, `browser/wordpages117.js`).

* **Opened directly** (a link, a search engine): `/bm-en/så/` draws the search as the search page
  does under the default settings — six entries, so the list's six rows; `/bm-en/norge/` one
  article, shown whole; the page's own title kept, the address as it was, nothing in History
  (what the 404 shell did for `/bm-en/så` until 117).
* **A form page** (`/bm-en/tær/`): its rows carry their labels, *tå* noun (plural indefinite),
  *tære* verb (imperative); and a regular form searched on the search page (*husene*) too.
* **The search goes to the page**: a word typed and Enter on an article page lands on its page,
  the address `/bm-en/så/` with nothing after it, the search in History; a suggestion chosen
  likewise; on the search page a form typed and Enter moves the address to `/bm-en/tær/` with no
  reload; a word with no page stays `/bm-en/#q=…`; Back after a search on a word page draws the
  first word again; `/bm-en/#q=da` (a Recent row, an old link) goes to `/bm-en/da/`, recorded;
  `/bm-en/Norge` (the 404 shell) to `/bm-en/norge/`; Random word to a word page, not recorded.
* **The similar headwords** link word pages where they exist.

`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before 117's deploy: fails).
Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SITE = None
R = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_wordpages117: skipped —", SKIP)
        return
    SITE = harness.Site()
    R.update(SITE.check("wordpages117.js", {"id": 98}, timeout=600))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class WordPages(unittest.TestCase):

    def test_a_direct_several(self):
        s = R["several"]
        self.assertTrue(s["drawn"], s)
        self.assertEqual(s["path"], "/bm-en/så/")
        self.assertEqual(s["hash"], "")
        self.assertEqual(s["rows"], 6, s)
        self.assertEqual(s["title"], "så — Norwegian–English dictionary")
        self.assertEqual(s["history"], [])

    def test_b_direct_one_article_whole(self):
        s = R["one"]
        self.assertEqual(s["path"], "/bm-en/norge/")
        self.assertEqual(s["full"], 1, s)
        self.assertEqual(s["fullLoaded"], 1, s)
        self.assertEqual(s["rows"], 0)
        self.assertTrue(s["title"].startswith("Norge (proper noun) — "), s["title"])
        self.assertEqual(s["history"], [])

    def test_c_form_page_labels(self):
        s = R["form"]
        self.assertEqual(s["path"], "/bm-en/tær/")
        got = {(r["word"], r["pos"], r["label"]) for r in s["inflected"]}
        self.assertIn(("tå", "noun", "(plural indefinite)"), got)
        self.assertIn(("tære", "verb", "(imperative)"), got)
        self.assertEqual(s["history"], [])
        lab = R["label"]
        self.assertIn(("hus", "noun", "(plural definite)"),
                      {(r["word"], r["pos"], r["label"]) for r in lab["inflected"]}, lab)

    def test_d_typed_on_an_article_page(self):
        s = R["typed"]
        self.assertEqual(s["path"], "/bm-en/så/", s)
        self.assertEqual(s["hash"], "")
        self.assertEqual(s["rows"], 6)
        self.assertEqual(s["history"], ["så"])

    def test_e_suggestion(self):
        s = R["suggestion"]
        self.assertEqual(s["path"], "/bm-en/bru/", s)
        self.assertEqual(s["hash"], "")
        self.assertEqual(s["history"], ["bru"])

    def test_f_in_place_on_the_search_page(self):
        s = R["inplace"]
        self.assertEqual(s["path"], "/bm-en/tær/", s)
        self.assertEqual(s["mark"], "kept", "the page was reloaded")
        self.assertTrue(any(r["label"] == "(plural indefinite)" for r in s["inflected"]), s)
        n = R["nopage"]
        self.assertEqual(n["path"], "/bm-en/")
        self.assertTrue(n["hash"].startswith("#q=xyzzyqq"), n)
        self.assertEqual(n["mark"], "kept")

    def test_g_back(self):
        b = R["back"]
        self.assertEqual(b["there"]["path"], "/bm-en/så/")
        self.assertEqual(b["there"]["mark"], "kept")
        self.assertEqual(b["back"]["path"], "/bm-en/da/")
        self.assertEqual(b["back"]["rows"], 3, b["back"])
        self.assertEqual(b["back"]["mark"], "kept")

    def test_h_redirect_and_capital(self):
        r = R["redirect"]
        self.assertEqual(r["path"], "/bm-en/da/", r)
        self.assertEqual(r["hash"], "")
        self.assertEqual(r["history"], ["da"])
        c = R["capital"]
        self.assertEqual(c["path"], "/bm-en/norge/", c)

    def test_i_similar_links(self):
        sim = R["similar"]
        self.assertTrue(sim, "no similar headwords")
        pages = [s for s in sim if not s["href"].startswith("/bm-en/#q=")]
        self.assertTrue(pages, sim)
        for s in pages:
            self.assertRegex(s["href"], r"^/bm-en/[^/#]+/#q=", s)

    def test_j_random(self):
        r = R["random"]
        self.assertRegex(r["path"], r"^/bm-en/[^/0-9][^/]*/$", r)
        self.assertEqual(r["hash"], "")
        self.assertEqual(r["history"], [])


if __name__ == "__main__":
    unittest.main()
