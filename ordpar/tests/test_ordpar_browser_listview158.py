"""Site decisions 158 (Robin, 2026-11-01): the list view also when a search finds an inflected form,
the new default (headless Edge, computer and phone).

Robin: "only if there are just 1 search match, and no inflected forms hits, does the search open
straight to the article. Reason: this makes it easier to find the inflected hits, instead of having
to scroll down to the bottom of the page to find them. I'd also like to make this the default
setting." Through `browser/listview158.js`, each step in a fresh context:

* **The default** (nothing stored): *hus* — one article, and an inflected form of *huse* — shows
  the list (one row, no article in full), its "is an inflected form of" section starting within
  the first screen; in every place a search opens: a shared address (`/bm-en/#q=hus`), its word
  page opened directly, typed in the search page's box, Random word (the draw made to fall on
  *hus*), a History row and a Recent row.
* **A one-article word with no form hit** (*vindu*: one row on its built word page, no
  inflected-form section): the article in full, as before 158 — by address, page, box and
  Random word.
* **`listview` = `multi`** (stored, the default until 158): *hus* opens the article in full again,
  the inflected-form section below it — in the same places, so a reader who chose it keeps it.
* **A form page** (*huset*, found only as an inflected form): the inflected-form rows, no article
  in full, under the default — as before 158.

The rule itself, the setting and its words: `test_ordpar_listview158.py`. `ORDPAR_TEST_BASE` points
it at another copy (the site before 158 fails: *hus* opens the article); `ORDPAR_TEST_OVERLAY` lays
a scratch render over the build. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

VIEWPORTS = ("computer", "phone")
EVERY = ["address", "page", "typed", "random", "history", "recent"]
CASES = [
    {"name": "hus", "q": "hus", "steps": EVERY},
    {"name": "vindu", "q": "vindu", "steps": ["address", "page", "typed", "random"]},
    {"name": "hus-multi", "q": "hus", "listview": "multi", "steps": EVERY},
]
FORM = "huset"
SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_listview158: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("listview158.js", dict(mobile=vp == "phone", cases=CASES, form=FORM),
                                timeout=900)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class ListViewWithForms(unittest.TestCase):
    def got(self, vp, case):
        r = RESULT[vp]
        self.assertNotIn("error", r, "%s: %s" % (vp, r))
        return r["got"][case]

    def each(self, case):
        for vp in VIEWPORTS:
            for step, st in self.got(vp, case).items():
                where = "%s, %s, %s: %s" % (vp, case, step, st)
                self.assertNotIn("error", st, where)
                self.assertTrue(st["settled"], "the results never settled: " + where)
                yield where, st

    def test_a_default_hus_shows_the_list_its_form_row_near_the_top(self):
        for where, st in self.each("hus"):
            self.assertEqual((st["rows"], st["full"]), (1, 0), "not the list: " + where)
            self.assertGreaterEqual(st["inflected"], 1, "no inflected-form row: " + where)
            self.assertLess(st["inflTop"], st["height"], "the inflected-form row below the first screen: " + where)

    def test_b_default_one_article_no_form_opens_it(self):
        for where, st in self.each("vindu"):
            self.assertEqual((st["rows"], st["full"], st["inflected"]), (0, 1, 0), "not the article: " + where)

    def test_c_multi_keeps_the_article(self):
        for where, st in self.each("hus-multi"):
            self.assertEqual((st["rows"], st["full"]), (0, 1), "not the article: " + where)
            self.assertGreaterEqual(st["inflected"], 1, where)

    def test_d_every_place_was_tried(self):
        for vp in VIEWPORTS:
            self.assertEqual(sorted(self.got(vp, "hus")), sorted(EVERY), vp)

    def test_e_a_form_page_as_before(self):
        for where, st in self.each("form"):
            self.assertEqual(st["full"], 0, where)
            self.assertGreaterEqual(st["inflected"], 1, where)


if __name__ == "__main__":
    unittest.main()
