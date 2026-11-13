"""Site-review decisions 105 (Robin, 2026-10-23): the homograph numeral in his chosen style (headless Edge).

His pick from the style lab: the numeral at 0.60 of the headword beside it, in the muted text
colour (#757070; at night #b9b6b6, `--ordpar-muted`), weight 600, raised 0.14 em; in the gloss
lists (the suggestions, Recent, History) its own size, 0.80 em of the gloss text, not coloured.
One rule in every place (`standing.md`, one style). Measured in each place, light and dark
(`browser/homograph105.js`):

* the article's headword line (*fange* III) and a full search result (*lysning*, list view off) —
  the numeral beside the 1.9 em `.ordbok-lemma`;
* the inflected-form rows (*lysingen*), the list view's rows (*lysning*) and the favourites' rows
  — the numeral inside the headword's span;
* the gloss lists: the suggestions for *fange*, Recent and History's — against the gloss text.
  (A History row shows the query, never a numeral after it: its numerals are its gloss list's.)

Each: the size ratio 0.60 ±0.02 (0.80 ±0.02 in a gloss list), the colour, weight 600, and raised
(its baseline above the baseline of what it follows; 0.14 em of its own size, ±1 px). The
suggestions' headwords keep no numeral (105). `ORDPAR_TEST_BASE=https://ordpar.no` runs it
against the live site (before the build: fails). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

COLOUR = {False: "rgb(117, 112, 112)", True: "rgb(185, 182, 182)"}
HEAD_PLACES = ("article", "full", "inflected", "list", "favourites")
GLOSS_PLACES = ("suggest", "recent", "historyGloss")
RATIO = {"head": 0.60, "gloss": 0.80}
TOL = 0.02
RAISE_EM = 0.14

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_homograph105: skipped —", SKIP)
        return
    SITE = harness.Site()
    for dark in (False, True):
        RESULT[dark] = SITE.check("homograph105.js", dict(dark=dark))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class NumeralInEveryPlace(unittest.TestCase):

    def _check(self, dark, place, want_ratio):
        got = RESULT[dark]["places"][place]
        self.assertTrue(got, "%s (%s): no numeral found on %s" % (place, "dark" if dark else "light",
                                                                 RESULT[dark]["base"]))
        for n in got:
            where = "%s %r (%s) on %s: %s" % (place, n["text"], "dark" if dark else "light",
                                              RESULT[dark]["base"], n)
            self.assertAlmostEqual(n["ratio"], want_ratio, delta=TOL, msg="size: " + where)
            self.assertEqual(n["color"], COLOUR[dark], "colour: " + where)
            self.assertEqual(n["weight"], "600", "weight: " + where)
            self.assertGreater(n["raise"], 0, "not raised: " + where)
            self.assertAlmostEqual(n["raise"], RAISE_EM * n["fs"], delta=1.0, msg="raise: " + where)

    def test_after_a_headword(self):
        for dark in (False, True):
            for place in HEAD_PLACES:
                with self.subTest(dark=dark, place=place):
                    self._check(dark, place, RATIO["head"])

    def test_in_a_gloss_list(self):
        for dark in (False, True):
            for place in GLOSS_PLACES:
                with self.subTest(dark=dark, place=place):
                    self._check(dark, place, RATIO["gloss"])

    def test_the_cases(self):
        for dark in (False, True):
            self.assertEqual(RESULT[dark]["dark"], dark, "the theme was not applied")
            self.assertEqual(RESULT[dark]["places"]["historyHead"], 0, "a History row's query shows a numeral")
            self.assertEqual(RESULT[dark]["places"]["suggestHead"], 0,
                             "a suggestion's headword shows a numeral (105: only in its gloss list)")
            kinds = {n["kind"] for n in RESULT[dark]["places"]["article"]}
            self.assertEqual(kinds, {"lemma"}, "the article's numeral no longer beside its lemma")


if __name__ == "__main__":
    unittest.main(verbosity=2)
