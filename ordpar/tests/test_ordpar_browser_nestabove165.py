"""Site decisions 165 (Robin, 2026-11-04: "Yes, open it above"): a nested small article stays inside the window (headless Edge).

A nested box (`nestminis` `second`, the default, and `stacked`) is `position: fixed`, so the page
cannot be scrolled to it. Until 165 `mini.js` `placeNested` always set it below its word, at least
160 px tall, so from a word near the window's bottom it ran past the window (Robin's screenshot,
*stusslig* -> *stakkarslig (1)*, about 70 px of room). Through `browser/nestabove165.js`, with real
clicks, on *båt* (8608) -> *skip (II)* (52833) -> *slagskip* (54202):

* **low**: the link to *slagskip* in the first box 70 px above the window's bottom: the nested box
  opens ABOVE its word (its bottom at or above the word's top), wholly inside the window (top >= 0,
  bottom <= the window's height), and is still so 600 ms later — under the default and `stacked`
  on a computer (1,280 x 900), under the default on a phone (390 x 844);
* **high**: the same link 120 px from the window's top: the box opens BELOW its word, inside the
  window, as before 165;
* where the box scrolls inside itself, a placing (a page-scroll event) keeps its own scroll.

Shown failing on the `mini.js` before 165 and passing on 165's (the contractor's report,
2026-11-04). Skipped without Edge, bun or a build. `ORDPAR_TEST_OUT` / `ORDPAR_TEST_OVERLAY` point
it at a build of a few pages (`harness.py`).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

IDS = dict(bat=8608, skip=52833, two=54202)
RUNS = {
    "computer": dict(w=1280, h=900, cases=[dict(name="low", at="low", mode=None),
                                           dict(name="low-stacked", at="low", mode="stacked"),
                                           dict(name="high", at="high", mode=None)]),
    "phone": dict(w=390, h=844, mobile=True, cases=[dict(name="low", at="low", mode=None),
                                                    dict(name="high", at="high", mode=None)]),
}

SITE = None
RESULT = {}          # run -> the check's dict, or {"error": text}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_nestabove165: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_SHOTS")
    for name, a in RUNS.items():
        args = dict(a, ids=IDS)
        if shots:
            args.update(shots=shots, shotPrefix="nest165-%s-" % name)
        try:
            RESULT[name] = SITE.check("nestabove165.js", args, timeout=300)
        except Exception as e:      # noqa: BLE001 — reported by the test that reads it
            RESULT[name] = {"error": str(e)[:1500]}


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class NestAbove165(unittest.TestCase):

    def _case(self, run, case):
        res = RESULT[run]
        self.assertNotIn("error", res, "%s: %s" % (run, res.get("error")))
        c = res["cases"][case]
        return c, "%s/%s on %s: %r" % (run, case, res["base"], c)

    def _inside(self, c, where):
        for k in ("first", "later"):
            g = c[k]
            self.assertTrue(g["nest"], where)
            self.assertFalse(g["hidden"], where)
            self.assertGreaterEqual(g["box"]["top"], 0, k + ": " + where)
            self.assertLessEqual(g["box"]["bottom"], g["vh"], k + ": " + where)
            self.assertTrue(g["inside"], k + ": " + where)
        if "kept" in c:
            self.assertEqual(c["kept"], 30, where)

    def test_a_from_a_word_near_the_bottom_it_opens_above_inside_the_window(self):
        for run, case in (("computer", "low"), ("computer", "low-stacked"), ("phone", "low")):
            c, where = self._case(run, case)
            self.assertLessEqual(c["before"]["roomBelow"], 80, where)     # the word did stand near the bottom
            self._inside(c, where)
            self.assertTrue(c["first"]["above"], where)
            self.assertTrue(c["later"]["above"], where)

    def test_d_its_side_kept_while_the_page_scrolls(self):
        # Robin, 2026-11-04: "the minis should not change position when you scroll the main window
        # (i.e., if they opened above to begin with, they stay above)": the page scrolled until
        # the word has more room below than above, and the box is still above it, inside the window
        for run, case in (("computer", "low"), ("computer", "low-stacked"), ("phone", "low")):
            c, where = self._case(run, case)
            s = c.get("scrolled")
            self.assertTrue(s, where)
            self.assertGreater(s["roomBelow"], s["roomAbove"], (where, s))   # a fresh placing would go below
            self.assertTrue(s["above"], (where, s))
            self.assertFalse(s["hidden"], (where, s))
            self.assertTrue(s["box"]["top"] >= -0.5, (where, s))

    def test_b_with_room_below_it_opens_below(self):
        for run in RUNS:
            c, where = self._case(run, "high")
            self._inside(c, where)
            self.assertTrue(c["first"]["below"], where)
            self.assertTrue(c["later"]["below"], where)

    def test_c_the_modes(self):
        self.assertEqual(self._case("computer", "low")[0]["mode"], "second")
        self.assertEqual(self._case("computer", "low-stacked")[0]["mode"], "stacked")


if __name__ == "__main__":
    unittest.main()
