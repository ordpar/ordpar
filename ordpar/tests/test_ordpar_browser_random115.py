"""Site-review decisions 115 (Robin, 2026-10-24): Random word opens a random headword's search (headless Edge).

Robin: "ordbokenes "random word" doesn't actually open to a random article, it opens to a random
headword search. I suggest we do it the same way (but still limited to searches were we can
actually offer complete articles …)"; of the limit: "Just the first one is enough". Through
`browser/random115.js`, on a computer (clicked) and a phone (tapped), four presses on the search
page (answered in place) and two from an article page (*fly* V, 15544):

* each lands on the headword's own page, `/bm-en/<headword>/` (site decisions 117, 2026-10-25;
  `/bm-en/#q=<headword>` until then, and still for a word whose search cannot be a folder name),
  and the box shows the headword;
* the search shows at least one article, and its first article (a full result or a list row) is
  the first that the same address opened afresh shows — the search as a typed one gives it;
* that first article meets decisions 67's bar, read from the site's own files: in
  `/index/translated.json`, its page has a summary gloss (`p.ordpar-gloss`), and its word class
  is not "fixed expression".

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build: fails — the button
opens `/bm-en/<id>/`). Skipped without Edge, bun or a build. The pool's rule itself is
`test_ordpar_random115.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

FLY_V = 15544
VIEWPORTS = ("computer", "phone")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_random115: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("random115.js", dict(mobile=vp == "phone", draws=4, fromArticle=2,
                                                     article=FLY_V))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class RandomWord(unittest.TestCase):

    def _draws(self, vp):
        d = RESULT[vp]["draws"]
        self.assertEqual(len(d), 6, "%s: %s" % (vp, d))
        for x in d:
            self.assertNotIn("error", x, "%s: %s" % (vp, x))
        return d

    def test_a_lands_on_a_search(self):
        for vp in VIEWPORTS:
            for d in self._draws(vp):
                where = "%s, from the %s page on %s: %s" % (vp, d["from"], RESULT[vp]["base"], d["url"])
                self.assertTrue(d["landed"], "did not land on the word's page or a #q= search: " + where)
                # site decisions 117: the word's own page, the address clean (every word of the
                # pool has one unless its search cannot be a folder name: then `/bm-en/#q=`)
                if d["hash"]:
                    self.assertEqual(d["path"], "/bm-en/", where)
                    self.assertTrue(d["hash"].startswith("#q="), where)
                    self.assertEqual(d["box"], d["q"], where)
                else:
                    self.assertRegex(d["path"], r"^/bm-en/[^/0-9][^/]*/$", where)
                    self.assertEqual((d["box"] or "").lower(), d["q"], where)
                self.assertTrue(d["q"], where)

    def test_b_as_a_typed_search_shows_it(self):
        for vp in VIEWPORTS:
            for d in self._draws(vp):
                where = "%s, %s: %s" % (vp, d["from"], d["url"])
                self.assertGreaterEqual(d["n"], 1, where)
                self.assertIsNotNone(d["first"], where)
                self.assertEqual(d.get("fresh"), d["first"], "the same address afresh shows another first article: " + where)

    def test_c_the_first_article_qualifies(self):
        for vp in VIEWPORTS:
            for d in self._draws(vp):
                where = "%s, %s: %s, first %s" % (vp, d["from"], d["url"], d["first"])
                self.assertTrue(d.get("translated"), "first article untranslated: " + where)
                self.assertTrue(d.get("gloss"), "first article has no summary gloss: " + where)
                self.assertNotEqual(d.get("pos"), "fixed expression", where)


if __name__ == "__main__":
    unittest.main()
