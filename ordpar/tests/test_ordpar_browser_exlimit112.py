"""Site-review decisions 112 (Robin, 2026-10-23): how many examples show under each sense (headless Edge).

The setting `exlimit` (Settings -> Article -> Language, after Examples): All (the default, first)
or 1 to 10, a drop-down. Every example list outside a mini — a sense's or a subsense's, in the
article, a full search result, a list-view row, a favourites row and a set phrase — shows its first
n examples in the page's order (Bokmålsordboka's, then our added "+" ones, which count); a list
with no more than n shows them all and no line. While `exmore` is on (the default), a line "Show N
more examples" (N the number hidden; "Show 1 more example") under a cut list opens the rest in
place; with it off the rest are simply not shown. Checked on *gå* (21740: its first sense has 15
examples), on a computer (the line clicked) and on a phone (tapped), through `browser/exlimit112.js`:

* All: 15 under the first sense, no line; 3, set in place and after a reload: 3 and "Show 12 more
  examples", which opens the other 12 in place and goes; every list on the page obeys the rule (a
  short list whole, with no line); *aktiv*'s subsenses (602), each its own: 4 cut to 3, 1 whole; 10; 1, where the set phrases' lists are cut too ("Show
  1 more example"); a stored value that is not a choice reads as All;
* the line off: 3 and no line;
* with the examples' English hidden (111): the opened examples hide theirs too, each with its cue;
* the same in a full result, a list-view row and a favourites row;
* a mini (*gå*'s first sense, from 21748) keeps its own cap (`mini.js` EX_BUDGET, 6) under a limit
  of 1: no line, every example it kept shown;
* the settings page: a drop-down of All, 1 … 10 with All chosen, after Examples; the line's setting
  hidden with All and shown with a number; kept on reload; "Delete stored data" puts it back to All;
  no "Send usage statistics" while the privacy switch is off (decisions 104).

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build: fails). Skipped
without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

GA = 21740              # gå: 15 examples under its first sense
AKTIV = 602             # aktiv: subsenses with 4 examples and with 1
VIEWPORTS = ("computer", "phone")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_exlimit112: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("exlimit112.js", dict(mobile=vp == "phone", id=GA, word="gå", sub=AKTIV,
                                                      miniFrom=21748, miniTo=GA))


def tearDownModule():
    if SITE:
        SITE.close()


def _line(h):
    return "Show 1 more example" if h == 1 else "Show %d more examples" % h


@unittest.skipIf(SKIP, SKIP or "")
class ExamplesLimit(unittest.TestCase):

    def _obeys(self, vp, name, limit, line=True, where_min=1):
        """Every list under the case's root: min(n, limit) shown; a line exactly where cut."""
        s = RESULT[vp]["cases"][name]
        where = "%s, %s on %s" % (vp, name, RESULT[vp]["base"])
        self.assertTrue(s and len(s["lists"]) >= where_min, "no example lists: %s: %s" % (where, s))
        cut = 0
        for i, l in enumerate(s["lists"]):
            want = l["n"] if limit is None else min(l["n"], limit)
            self.assertEqual(l["shown"], want, "list %d shows %d of %d, want %d: %s" % (i, l["shown"], l["n"], want, where))
            hidden = 0 if limit is None else max(0, l["n"] - limit)
            if hidden and line:
                cut += 1
                self.assertEqual(l["line"], _line(hidden), "list %d: %s" % (i, where))
                self.assertTrue(l["lineShown"], "list %d: its line is hidden: %s" % (i, where))
            else:
                self.assertFalse(l["lineShown"], "list %d: a line shows (%r): %s" % (i, l["line"], where))
        return s, cut

    def test_all_by_default(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s, _ = self._obeys(vp, "all", None)
                self.assertEqual((s["first"]["n"], s["first"]["shown"]), (15, 15))
                self.assertIsNone(s["stored"])
                self.assertEqual(s["cls"], [])

    def test_three_in_place_and_after_a_reload(self):
        for vp in VIEWPORTS:
            for name in ("inPlace", "three"):
                with self.subTest(vp=vp, case=name):
                    s, cut = self._obeys(vp, name, 3)
                    self.assertEqual((s["first"]["n"], s["first"]["shown"]), (15, 3))
                    self.assertEqual(s["first"]["line"], "Show 12 more examples")
                    self.assertGreater(cut, 1)
                    self.assertEqual(s["stored"], "3")
                    self.assertIn("ordpar-exlimit-3", s["cls"])
                    # a list with no more than the limit: all of it, no line (the rule above, shown to occur)
                    self.assertTrue(any(0 < l["n"] < 3 for l in s["lists"]), "no short list on the page")

    def test_subsenses_each_their_own(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s, _ = self._obeys(vp, "sub", 3)
                subs = [l for l in s["lists"] if l["sub"] and not l["inExpr"]]
                self.assertTrue(any(l["n"] > 3 and l["line"] for l in subs), "no subsense cut: %s" % subs)
                self.assertTrue(any(0 < l["n"] < 3 and not l["line"] for l in subs),
                                "no subsense with fewer examples than the limit: %s" % subs)

    def test_the_line_opens_the_rest_in_place(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                o = RESULT[vp]["cases"]["threeOpen"]
                self.assertTrue(o["found"], o)
                self.assertEqual(o["text"], "Show 12 more examples")
                self.assertEqual(o["tag"], "BUTTON")
                self.assertEqual((o["after"]["n"], o["after"]["shown"], o["after"]["line"]), (15, 15, False), o)

    def test_ten_and_a_value_that_is_no_choice(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s, _ = self._obeys(vp, "ten", 10)
                self.assertEqual(s["first"]["line"], "Show 5 more examples")
                s, _ = self._obeys(vp, "fourteenInvalid", None)
                self.assertEqual(s["cls"], [])

    def test_one_and_the_set_phrases(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s, cut = self._obeys(vp, "one", 1)
                expr = [l for l in s["lists"] if l["inExpr"]]
                self.assertTrue(any(l["n"] > 1 for l in expr), "no set phrase with two examples or more")
                self.assertTrue(any(l["line"] == "Show 1 more example" for l in expr), expr)

    def test_the_line_off(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s, _ = self._obeys(vp, "off", 3, line=False)
                self.assertEqual((s["first"]["shown"], s["first"]["lineShown"]), (3, False))
                self.assertIn("ordpar-exmore-off", s["cls"])

    def test_the_english_hidden_on_the_opened_ones(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s, _ = self._obeys(vp, "hidden", 3)
                self.assertEqual((s["first"]["en"], s["first"]["cues"]), (0, 3))
                o = RESULT[vp]["cases"]["hiddenOpen"]["after"]
                self.assertEqual((o["shown"], o["en"], o["cues"]), (15, 0, 15), o)

    def test_a_full_result_a_list_row_and_a_favourite(self):
        for vp in VIEWPORTS:
            for name in ("full", "list", "fav"):
                with self.subTest(vp=vp, place=name):
                    s, cut = self._obeys(vp, name, 3)
                    self.assertGreater(cut, 0, "nothing was cut: %s" % name)
            for name in ("fullOpen", "listOpen"):
                with self.subTest(vp=vp, place=name):
                    o = RESULT[vp]["cases"][name]
                    self.assertTrue(o["found"], o)
                    self.assertEqual((o["after"]["shown"], o["after"]["line"]), (o["after"]["n"], False), o)

    def test_a_mini_keeps_its_own_cap(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                self.assertTrue(RESULT[vp]["cases"]["miniOpened"], "the mini did not open")
                m = RESULT[vp]["cases"]["mini"]["lists"]
                self.assertTrue(m)
                for l in m:
                    self.assertEqual((l["shown"], l["line"]), (l["n"], False), m)
                self.assertGreater(max(l["n"] for l in m), 1, "every mini list holds one: no proof the limit of 1 is ignored")

    def test_the_settings_page(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                c = RESULT[vp]["cases"]
                s = c["settings"]
                self.assertTrue(s["select"], s)
                self.assertEqual(s["options"], [["all", "All"]] + [[str(n), str(n)] for n in range(1, 11)])
                self.assertEqual(s["value"], "all")
                self.assertEqual(s["title"], "Examples under each sense and set phrase")   # 126
                self.assertEqual(s["label"], "article-language-title ordpar-exlimit-legend")
                # the eye's setting right under Examples since site decisions 131 (2026-10-26), what it
                # hides after it since site decisions 186 (drawn, hidden while the eye is off), the
                # CEFR level box's after them since site decisions 187 (the check reads four keys)
                self.assertEqual(s["after"], ["examples", "exeye", "exeyewhat", "levels"])
                self.assertEqual(s["hints"], [True, True])
                self.assertFalse(s["moreShown"], "the line's setting shows with All")
                self.assertEqual(s["moreTitle"], "A line to show the examples left out")   # 126
                self.assertFalse(s["stats"] or s["statsText"], "the opt-out shows with the privacy switch off")
                t = c["settingsThree"]
                self.assertEqual((t["stored"], t["value"], t["moreShown"]), ("3", "3", True))
                self.assertIn("ordpar-exlimit-3", t["cls"])
                r = c["settingsReload"]
                self.assertEqual((r["value"], r["moreShown"]), ("3", True))
                d = c["settingsDeleted"]
                self.assertEqual((d["stored"], d["value"], d["moreShown"], d["cls"]), (None, "all", False, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
