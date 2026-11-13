"""Site decisions 141 (Robin, 2026-10-26): a hover peek inside a small article shows in full (headless Edge).

The fault: the mini's box scrolls (`overflow-y:auto` on a computer), and a link's peek inside it was
placed by the sheet from its word (`position:absolute`), so a long peek was cut off at the box's
edge — Robin's shot, the peek of *fiske (I, 1)* inside the mini of *fiskefartøy*. Ruled: the mini
keeps its size, and the peek shows in full, extending beyond the box's edge, inside the window.

Through `browser/peek141.js`, with real mouse clicks and a real hover, on *fiskebåt* (14925): its
link to *fiskefartøy* (14930) opened, then the pointer rested on the mini's link to *fiske* (14909),
whose peek is that sense's three-line English definition. And nested, from *båt* (8608): *fiskebåt*
in the first box, *fiskefartøy* in it, in place, in a second box (the default since decisions 147) and
stacked (decisions 139). Asserted per case:

* the peek shows, and all nine of its sample points are painted as the peek
  (`document.elementFromPoint`) — nothing clips or covers it — and its box lies inside the window;
* the mini's box has the same size before and after the hover;
* on a computer (1280 x 900) light and dark, and at a phone's width on a computer (390 x 844, a
  fine pointer: the peeks show); with the box's top near the window's top the peek goes below its
  word (`ordpar-pbelow`), still whole;
* a peek a setting hides stays hidden (`peek` = off); on a phone (touch) a mini's peeks are hidden,
  as before.

`ORDPAR_TEST_BASE=https://ordpar.no` points it at the live site: before the fix the first-level case
fails (the peek's top lines cut off by the box: three of nine points not the peek) and the nested
cases cannot open (no nesting there). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

BAT, FISKEBAT, FISKEFARTOY, FISKE = 8608, 14925, 14930, 14909
FIRST = dict(page=FISKEBAT, path=[FISKEFARTOY], hover=FISKE)
NESTED = dict(page=BAT, path=[FISKEBAT, FISKEFARTOY], hover=FISKE)
RUNS = {
    "computer": dict(w=1280, h=900, cases=[
        dict(name="first", **FIRST),
        dict(name="first-dark", theme="dark", **FIRST),
        dict(name="first-top", toTop=True, **FIRST),
        dict(name="inplace", nest="inplace", **NESTED),
        dict(name="second", nest="second", **NESTED),        # decisions 147: the new default
        dict(name="stacked", nest="stacked", **NESTED),
        dict(name="stacked-dark", nest="stacked", theme="dark", **NESTED),
        dict(name="peek-off", settings={"peek": "off"}, **FIRST),
    ]),
    "narrow": dict(w=390, h=844, cases=[
        dict(name="first", **FIRST),
        dict(name="inplace", nest="inplace", **NESTED),
        dict(name="second", nest="second", **NESTED),
        dict(name="stacked", nest="stacked", **NESTED),
    ]),
    "phone": dict(w=390, h=844, mobile=True, cases=[dict(name="first", **FIRST)]),
}
SHOWN = {"computer": ["first", "first-dark", "first-top", "inplace", "second", "stacked", "stacked-dark"],
         "narrow": ["first", "inplace", "second", "stacked"]}

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_peek141: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_SHOTS")
    for name, a in RUNS.items():
        a = dict(a)
        if shots:
            a["shots"] = shots
            a["cases"] = [dict(c, shot="peek141-%s-%s" % (name, c["name"])) for c in a["cases"]]
        RESULT[name] = SITE.check("peek141.js", a)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Peek(unittest.TestCase):

    def _c(self, run, name):
        c = RESULT[run]["cases"][name]
        where = "%s, %s on %s: %s" % (run, name, RESULT[run]["base"], {k: c.get(k) for k in (
            "error", "opened", "boxes", "shown", "position", "below", "hits", "peek", "win", "boxBefore", "boxAfter")})
        self.assertTrue(c.get("opened"), "no mini opened — " + where)
        return c, where

    def test_a_shown_in_full_inside_the_window(self):
        for run, names in SHOWN.items():
            for name in names:
                c, where = self._c(run, name)
                self.assertTrue(c["shown"], "the peek does not show — " + where)
                self.assertTrue(all(c["hits"]), "the peek is cut off or covered — " + where)
                self.assertTrue(c["inWindow"], "the peek leaves the window — " + where)

    def test_b_the_mini_keeps_its_size(self):
        for run, names in SHOWN.items():
            for name in names:
                c, where = self._c(run, name)
                for k in ("w", "h", "l", "t"):
                    self.assertAlmostEqual(c["boxBefore"][k], c["boxAfter"][k], delta=0.5, msg=k + " — " + where)

    def test_c_nested_boxes(self):
        for run in ("computer", "narrow"):
            self.assertEqual(self._c(run, "inplace")[0]["boxes"], 1)
            self.assertEqual(self._c(run, "second")[0]["boxes"], 2)     # decisions 147
            self.assertEqual(self._c(run, "stacked")[0]["boxes"], 2)

    def test_d_below_the_word_near_the_top(self):
        c, where = self._c("computer", "first-top")
        self.assertTrue(c["below"], where)
        self.assertGreaterEqual(c["peek"]["t"], c["word"]["b"] - 0.5, where)

    def test_e_a_hidden_peek_stays_hidden(self):
        c, where = self._c("computer", "peek-off")
        self.assertFalse(c["shown"], where)
        c, where = self._c("phone", "first")
        self.assertFalse(c["shown"], "a phone shows no peek in a mini — " + where)


if __name__ == "__main__":
    unittest.main()
