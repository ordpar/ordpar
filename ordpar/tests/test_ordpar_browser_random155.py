"""Site decisions 155 (Robin, 2026-10-31): Random word in English when the switch is on (headless Edge).

Robin: "when "Search English words" is switched on, it chooses a random English word (instead of a
Norwegian one)"; the pool his pick: every English word the English suggestions can offer, each
equally likely, opened exactly as if typed and picked. Through `browser/random155.js`, on a
computer (clicked) and a phone (tapped), storage cleared first:

* the switch turned on by a real click or tap on the search page, then Random word: an English
  search `#en=<word>` (no mark left in the address) of a word in the English pool (`enPool` over
  the word's own file), its results shown (the list, or the one article in full), the switch
  still on, the box holding the word with `lang="en"`, History empty (a draw is not a search,
  115) — also after a reload of that address;
* Random word on an article page (*fly* V, 15544), the switch on as stored: the same, the page
  left for the search;
* the switch turned off, then Random word: Norwegian, as before 155 — no `#en=`, the box `nb`,
  the switch off, History still empty.

The pool, the uniform draw and the counts: `test_ordpar_random155.py`. `ORDPAR_TEST_BASE` points
it at another copy (the site before 155: fails — the switch goes off and a Norwegian word is
drawn); `ORDPAR_TEST_OVERLAY` lays a scratch render over the build. Skipped without Edge, bun or a
build.
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
        print("test_ordpar_browser_random155: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("random155.js", dict(mobile=vp == "phone", article=FLY_V))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class RandomWordInEnglish(unittest.TestCase):
    def steps(self, vp):
        r = RESULT[vp]
        self.assertNotIn("error", r, "%s: %s" % (vp, r))
        return r["steps"]

    def english(self, vp, name):
        st = self.steps(vp)[name]
        where = "%s, %s: %s" % (vp, name, st["url"])
        self.assertTrue(st["hash"].startswith("#en="), "not an English search: " + where)
        self.assertNotIn("random", st["hash"], "the draw's mark left in the address: " + where)
        self.assertTrue(st["word"], where)
        self.assertTrue(st["inPool"], "a word outside the English pool: " + where)
        self.assertTrue(st["english"] and st["shown"] >= 1, "no English results shown: " + where)
        self.assertEqual((st["switchOn"], st["boxLang"]), (True, "en"), "the box left English: " + where)
        self.assertEqual(st["box"], st["word"], where)
        self.assertEqual(st["history"], [], "the draw went into History: " + where)

    def test_a_drawn_on_the_search_page(self):
        for vp in VIEWPORTS:
            self.assertTrue(self.steps(vp)["onSearchLanded"], "%s: %s" % (vp, self.steps(vp)["onSearch"]))
            self.english(vp, "onSearch")
            self.english(vp, "reload")
            self.assertEqual(self.steps(vp)["reload"]["word"], self.steps(vp)["onSearch"]["word"])

    def test_b_drawn_from_an_article_page(self):
        for vp in VIEWPORTS:
            self.assertTrue(self.steps(vp)["onArticleLanded"], "%s: %s" % (vp, self.steps(vp)["onArticle"]))
            self.english(vp, "onArticle")

    def test_c_switch_off_norwegian_as_before(self):
        for vp in VIEWPORTS:
            s = self.steps(vp)
            st = s["off"]
            where = "%s: %s" % (vp, st["url"])
            self.assertTrue(s["offLanded"], where)
            self.assertNotIn("#en=", st["hash"], where)
            self.assertEqual((st["switchOn"], st["boxLang"]), (False, "nb"), where)
            self.assertTrue(st["box"], where)
            self.assertGreaterEqual(st["shown"], 1, where)
            self.assertEqual(st["history"], [], where)


if __name__ == "__main__":
    unittest.main()
