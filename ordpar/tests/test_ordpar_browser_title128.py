"""Site decisions 128 (2026-10-25): the search page's lifted article sets the new title (headless Edge).

One style for every page title (standing.md; the brief's § 3): an article page's `<title>` is "word
(class) — Norwegian–English dictionary", and a search that lifts ONE article in full now takes that
page's own title (`lookup.js` `render`, from `extractArticle`'s `title`), where it used to say
"<query> — Ordpar". A search that shows several articles keeps "<query> — Ordpar" (left for Robin).

Through `browser/title128.js`: the search page opened at `/bm-en/#q=vindu` (one translated
article) and at `/bm-en/#q=abstrakt` (three). Asserted:

* *vindu*: one article lifted; the page's title equals that article page's own `<title>` and has
  the new form ("vindu (noun) — Norwegian–English dictionary");
* *abstrakt*: several articles (list rows, the default view of several hits); the title stayed
  "abstrakt — Ordpar" until site decisions 117 (2026-10-25), since when the search is answered on
  the word's own page, `/bm-en/abstrakt/`, whose title is "abstrakt — Norwegian–English
  dictionary" (117's several-entry title).

`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before 128's deploy: fails,
the title "vindu — Ordpar"). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

DICT = " — Norwegian–English dictionary"
SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_title128: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("title128.js", dict(cases=[{"q": "vindu"}, {"q": "abstrakt"}])))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class LiftedTitle(unittest.TestCase):

    def row(self, q):
        return next(r for r in RESULT["rows"] if r["q"] == q)

    def test_a_one_article_takes_its_page_title(self):
        r = self.row("vindu")
        self.assertEqual(r["articles"], 1, r)
        self.assertEqual(r["title"], r["pageTitle"], r)
        self.assertEqual(r["title"], "vindu (noun)" + DICT, r)

    def test_b_several_keep_the_query_title(self):
        r = self.row("abstrakt")
        # several hits: the list view by default (setting `listview` multi), so no article lifted
        self.assertGreater(r["articles"] + r["rows"], 1, r)
        # since site decisions 117 (2026-10-25) the search is answered on the word's own page,
        # whose title is the several-entry word page's: "abstrakt — Norwegian–English dictionary"
        # (until then the search page kept "abstrakt — Ordpar")
        self.assertEqual(r["title"], "abstrakt — Norwegian–English dictionary", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
