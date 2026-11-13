"""Site-review decisions 111 (Robin, 2026-10-23): the examples' English behind a reveal (headless Edge).

The setting `examples` (Settings -> Article -> Language, beside Definitions): `both` (the default)
shows every example's English; `no` shows the Norwegian with the English hidden behind the same
"Show English" cue as `defs = no`'s (`page.SITE_CSS`, `_PAGE_JS` `excues`), on every example with
an English line — the article page, an added ("+") example, a set phrase's, a full search result,
a list-view row's article and a mini — and on none without one. Checked on a computer (the cue
clicked, then Enter on a focused cue) and on a phone (tapped), through `browser/examples111.js`:

* set in place (`ordparShell.setSetting`), the article hides its examples' English at once; after
  a reload the head script applies it from storage;
* a click on the cue shows that example's English and hides its cue; a click on the opened English
  hides it again; Enter on a focused cue opens it;
* `both` again: every English line shows and no cue, in an open mini too;
* the four pairs of `defs` × `examples` on one article: `examples` decides the examples alone,
  `defs` the definitions alone.

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build: fails). Skipped
without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

EXPR = 10214            # direkte: set phrases with translated examples
UNTRANSLATED = 41441    # an untranslated article with examples (none has English)
VIEWPORTS = ("computer", "phone")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_examples111: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("examples111.js", dict(mobile=vp == "phone", expr=EXPR, untranslated=UNTRANSLATED))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class ExamplesBehindTheCue(unittest.TestCase):

    def _hidden(self, vp, name):
        s = RESULT[vp]["cases"][name]
        where = "%s, %s on %s: %s" % (vp, name, RESULT[vp]["base"], s)
        self.assertTrue(s and s["withEn"] > 0, "no example with English: " + where)
        self.assertTrue(s["cls"], "the class ordpar-examples-no is not on <html>: " + where)
        self.assertEqual(s["enShown"], 0, "an example's English shows: " + where)
        self.assertEqual(s["cuesShown"], s["withEn"], "not one cue per example with English: " + where)
        self.assertEqual(s["cueWithoutEn"], 0, "a cue on an example with no English: " + where)

    def _shown(self, vp, name):
        s = RESULT[vp]["cases"][name]
        where = "%s, %s on %s: %s" % (vp, name, RESULT[vp]["base"], s)
        self.assertTrue(s and s["withEn"] > 0, "no example with English: " + where)
        self.assertEqual(s["enShown"], s["withEn"], "an example's English is hidden: " + where)
        self.assertEqual(s["cuesShown"], 0, "a cue shows: " + where)

    def _cycle(self, vp, name):
        c = RESULT[vp]["cases"][name]
        where = "%s, %s on %s: %s" % (vp, name, RESULT[vp]["base"], c)
        self.assertTrue(c["found"], "no cue to press: " + where)
        self.assertEqual(c["text"], "Show English", where)
        self.assertEqual((c["before"]["en"], c["before"]["cue"]), (False, True), "before: " + where)
        self.assertEqual((c["opened"]["en"], c["opened"]["cue"]), (True, False), "the press did not open it: " + where)
        self.assertEqual((c["closed"]["en"], c["closed"]["cue"]), (False, True), "a press on the English did not close it: " + where)
        self.assertEqual((c["key"]["en"], c["key"]["cue"]), (True, False), "Enter on the cue did not open it: " + where)

    def test_the_default_shows_the_english(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                self._shown(vp, "articleBoth")
                self.assertIsNone(RESULT[vp]["cases"]["articleBoth"]["stored"])

    def test_no_in_place_and_after_a_reload(self):
        for vp in VIEWPORTS:
            for name in ("articleNoInPlace", "articleNo"):
                with self.subTest(vp=vp, case=name):
                    self._hidden(vp, name)
                    self.assertEqual(RESULT[vp]["cases"][name]["stored"], "no")

    def test_every_place_hides_and_reveals(self):
        for vp in VIEWPORTS:
            for name in ("article", "added", "expr", "full", "list", "mini"):
                with self.subTest(vp=vp, place=name):
                    if name == "mini":
                        self.assertTrue(RESULT[vp]["cases"]["miniOpened"], "the mini did not open")
                    self._hidden(vp, "articleNo" if name == "article" else name)
                    self._cycle(vp, name + "Cycle")
                if name == "mini":
                    self.assertTrue(RESULT[vp]["cases"]["miniStillOpen"], "pressing in the mini closed it")

    def test_the_cases_cover_what_they_claim(self):
        for vp in VIEWPORTS:
            c = RESULT[vp]["cases"]
            self.assertGreater(c["added"]["added"], 0, "no added (+) example on the added case's page")
            self.assertGreater(c["expr"]["inExpr"], 0, "no set-phrase example on %s" % EXPR)

    def test_no_english_no_cue(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s = RESULT[vp]["cases"]["untranslated"]
                self.assertGreater(s["examples"], 0, s)
                self.assertEqual((s["withEn"], s["cuesShown"], s["cueWithoutEn"]), (0, 0, 0), s)
                self.assertTrue(s["cls"], s)

    def test_both_again_in_a_mini(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                self._shown(vp, "miniBoth")

    def test_defs_and_examples_combine(self):
        for vp in VIEWPORTS:
            c = RESULT[vp]["cases"]
            for defs in ("both", "en", "no"):
                for ex in ("both", "no"):
                    name = "defs-%s-ex-%s" % (defs, ex)
                    with self.subTest(vp=vp, case=name):
                        (self._hidden if ex == "no" else self._shown)(vp, name)
                        s = c[name]
                        self.assertGreater(s["pairs"], 0, name)
                        if defs == "no":
                            self.assertEqual(s["pairsEn"], 0, "defs=no shows a definition's English: %s" % s)
                            self.assertEqual(s["pairCues"], s["pairs"], "defs=no: a pair without its cue: %s" % s)
                        else:
                            self.assertEqual(s["pairsEn"], s["pairs"], "a definition's English hidden: %s" % s)
                            self.assertEqual(s["pairCues"], 0, "a definition cue under defs=%s: %s" % (defs, s))


if __name__ == "__main__":
    unittest.main(verbosity=2)
