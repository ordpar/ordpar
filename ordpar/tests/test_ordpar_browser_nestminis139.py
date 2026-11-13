"""Site decisions 139 (Robin, 2026-10-26): a small article inside a small article (headless Edge).

The setting `nestminis` (Settings -> Article -> Small articles): *inplace* — the box's content
swaps to the new word, with a line "← word" at its top that steps back, no limit; *stacked* — a
second box below its word inside the first; *off* — depth one (a click opens the page). Since site
decisions 147 (2026-10-29) the default is *second* (a second box, then steps in it; its own test,
`test_ordpar_browser_nestminis147.py`), so the in-place cases here name *inplace*; *stacked* has no
limit (`nestlimit` went); and nothing in a box scrolls the page (Robin's rule). Through
`browser/nestminis139.js`, with real mouse clicks and real keys, on *båt* (8608) -> *skip (II)*
(52833) -> *slagskip* (54202) -> *krigsskip* (32118) -> *orlogsskip* (43359), all translated, and *lang* (33770) -> *sid* (51277)
-> *fotsid* (17409), Norwegian-only:

* in place, where the reader was (Robin, 2026-10-27, amended by his rule of 2026-10-29, decisions
  147): back (the line, two levels; Escape) restores the box's own scroll on a computer, each level
  its own, and leaves the page where it is — also at 390 px and with `miniscroll` off, where the box
  does not scroll (until 147 the page was put back there);
* in place: one box throughout; the back line reads "← <the word stepped from>" and is named "Back
  to <word>"; the focus moves to it; it steps back one word at a time, the first word at its scroll
  position; Escape steps back, then closes, the focus on the word each time; aria-expanded;
* stacked: two boxes, the second `.ordpar-mnest` inside the window; a click inside the first closes
  only the second; the same word again closes it; Escape closes it, the focus back on its word; a
  click outside every box closes all; a link in the second opens a third (147: no limit);
* stacked, three boxes: Escape closes one at a time; a click inside the first closes both nested,
  inside the second only the third; a link in the third opens a fourth (147: no limit);
* off: a link in a box opens its page;
* a Norwegian-only target nested (`lang="nb"`), in place and stacked;
* the keyboard: Tab reaches a link inside the box, Enter opens it; the focus moves into the new box
  (stacked: its headword; in place: the back line), and Escape brings it back to the word;
* under the default (147: a second box, then a step in it) on the search page's lifted *båt*
  (`/bm-en/#q=båt`), on the word page `/bm-en/båt/` (117), and in an opened list-view row
  (`/bm-en/skip/`, *slagskip*'s panel);
* at 390 px (a phone, touch): in place and stacked, every box inside the window;
* the settings page: the field under Small articles after *How much of the article it shows*, its
  four choices (147), the default checked, no limit field whichever is chosen.

`ORDPAR_TEST_BASE` points it at another copy (not run against the live site: before this build a
click inside a mini opens the page there, and its settings page has no such fields). Skipped without
Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

IDS = dict(bat=8608, skip=52833, two=54202, three=32118, four=43359, lang=33770, sid=51277, fotsid=17409)
URLS = dict(searchUrl="/bm-en/#q=b%C3%A5t", wordUrl="/bm-en/b%C3%A5t/", rowsUrl="/bm-en/skip/")
RUNS = {
    "computer": dict(w=1280, h=900, groups=["inplace", "scroll", "stacked1", "stacked2", "off", "nbonly",
                                            "keyboard", "search", "settings"]),
    "noscroll": dict(w=1280, h=900, scrollSettings={"miniscroll": "off"}, groups=["scroll"]),
    "dark": dict(w=1280, h=900, theme="dark", groups=["inplace", "stacked2", "settings"]),
    "phone": dict(w=390, h=844, mobile=True, groups=["inplace", "scroll", "stacked1", "settings"]),
    "phone-dark": dict(w=390, h=844, mobile=True, theme="dark", groups=["inplace", "stacked2"]),
}

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_nestminis139: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_SHOTS")
    for name, a in RUNS.items():
        a = dict(a, ids=IDS, **URLS)
        if shots:
            a.update(shots=shots, shotPrefix="nest139-%s-" % name)
        RESULT[name] = SITE.check("nestminis139.js", a, timeout=600)


def tearDownModule():
    if SITE:
        SITE.close()


def _hw(box):
    return box["head"]


@unittest.skipIf(SKIP, SKIP or "")
class Nest(unittest.TestCase):

    def _g(self, run, group):
        g = RESULT[run]["groups"][group]
        return g, "%s, %s on %s: %s" % (run, group, RESULT[run]["base"], g)

    def test_a_in_place(self):
        for run in [r for r in RUNS if "inplace" in RUNS[r]["groups"]]:
            g, where = self._g(run, "inplace")
            self.assertEqual(len(g["open"]["boxes"]), 1, where)
            self.assertEqual(g["open"]["expanded"], "true", where)
            head0, head1 = g["heads"]
            self.assertTrue(head0 and head1 and head0 != head1, where)
            # first step: one box, the back line to the first word, the focus on it
            self.assertEqual([b["nest"] for b in g["step1"]["boxes"]], [False], where)
            self.assertEqual(g["step1"]["back"], {"text": "← " + head0, "label": "Back to " + head0}, where)
            self.assertEqual(g["step1"]["active"]["cls"], "ordpar-mback", where)
            self.assertEqual(g["step1"]["scrollTop"], 0, where)
            # second step: still one box, the back line to the second word (no limit)
            self.assertTrue(g["clicked2"], where)
            self.assertEqual(len(g["step2"]["boxes"]), 1, where)
            self.assertEqual(g["step2"]["back"]["text"], "← " + head1, where)
            self.assertEqual(g["step2"]["path"], "/bm-en/%d/" % IDS["bat"], where)
            # the back line steps back one word at a time; the first word at its scroll position
            self.assertEqual(_hw(g["backByLine"]["boxes"][0]), head1, where)
            self.assertEqual(g["backByLine"]["back"]["text"], "← " + head0, where)
            self.assertEqual(_hw(g["backToFirst"]["boxes"][0]), head0, where)
            self.assertIsNone(g["backToFirst"]["back"], where)
            self.assertTrue(g["clicked1"], where)
            self.assertEqual(g["backToFirst"]["scrollTop"], g["in1"]["s"], where)
            self.assertEqual(g["backToFirst"]["twoExpanded"], "false", where)
            # Escape: a step back (the focus on the word stepped from), then the box closes
            self.assertEqual(_hw(g["esc1"]["boxes"][0]), head0, where)
            self.assertIsNone(g["esc1"]["back"], where)
            self.assertTrue(g["esc1"]["active"]["inBox"], where)
            self.assertIn("/bm-en/%d/" % IDS["two"], g["esc1"]["active"]["href"], where)
            self.assertEqual(g["esc2"]["boxes"], [], where)
            self.assertIn("/bm-en/%d/" % IDS["skip"], g["esc2"]["active"]["href"], where)
            self.assertFalse(g["esc2"]["active"]["inBox"], where)
            self.assertEqual(g["esc2"]["expanded"], "false", where)

    def test_a2_back_where_the_reader_was(self):
        # Robin, 2026-10-27: back returns exactly where the reader had scrolled in the box — two
        # steps in and two back, each level its own; Escape's step back too. Amended 2026-10-29
        # (decisions 147, "interacting inside the small article boxes should never scroll the main
        # window"): the page is never put back; it stays where it was just before the back
        for run, inside in (("computer", True), ("noscroll", False), ("phone", False)):
            g, where = self._g(run, "scroll")
            self.assertEqual(g["first"]["scrolls"], inside, where)
            if inside:
                self.assertGreater(g["in1"]["s"], 0, where)          # the first box was scrolled
            else:
                self.assertGreater(g["in1"]["y"], 0, where)          # the page was scrolled
            self.assertEqual(g["at2"]["back"]["text"], "← " + g["at1"]["head"], where)
            # the box was moved to its top before each back, so a pass is the script putting it back
            if inside:
                for moved, was in (("moved1", "in2"), ("moved2", "in1"), ("moved3", "in3")):
                    if g[was]["s"]:
                        self.assertNotAlmostEqual(g[moved]["s"], g[was]["s"], delta=1, msg=moved + ": " + where)
            for got, moved, was in (("back1", "moved1", "in2"), ("back2", "moved2", "in1"), ("esc", "moved3", "in3")):
                self.assertAlmostEqual(g[got]["y"], g[moved]["y"], delta=1, msg=got + " page stays: " + where)
                if inside:
                    self.assertAlmostEqual(g[got]["s"], g[was]["s"], delta=1, msg=got + " box: " + where)
            self.assertEqual(g["back1"]["head"], g["at1"]["head"], where)
            self.assertEqual(g["back2"]["head"], g["first"]["head"], where)
            self.assertIsNone(g["back2"]["back"], where)
            self.assertEqual(g["esc"]["head"], g["first"]["head"], where)

    def _inside(self, boxes, win, where):
        for b in boxes:
            self.assertGreaterEqual(b["l"], 0, where)
            self.assertLessEqual(b["r"], win, where)

    def test_b_stacked(self):
        for run in ("computer", "phone"):
            g, where = self._g(run, "stacked1")
            self.assertEqual([b["nest"] for b in g["two"]["boxes"]], [False, True], where)
            self.assertEqual(g["two"]["expanded"], "true", where)
            self.assertTrue(all(b["vis"] for b in g["two"]["boxes"]), where)
            self._inside(g["two"]["boxes"], g["two"]["win"], where)
            self.assertEqual(len(g["insideFirst"]["boxes"]), 1, where)
            self.assertEqual(g["insideFirst"]["expanded"], "false", where)
            self.assertEqual(len(g["sameAgain"]["boxes"]), 1, where)
            self.assertEqual(len(g["esc"]["boxes"]), 1, where)
            self.assertIn("/bm-en/%d/" % IDS["two"], g["esc"]["active"]["href"], where)
            self.assertEqual(g["outside"]["boxes"], [], where)
            self.assertEqual(g["outside"]["expanded"], "false", where)
            # no limit (147): a link in the second box opens a third, on the same page
            self.assertTrue(g["limitClicked"], where)
            self.assertFalse(g["limit"]["left"], where)
            self.assertEqual(g["limit"]["boxes"], 3, where)
            self.assertEqual(g["limit"]["path"], "/bm-en/%d/" % IDS["bat"], where)

    def test_c_stacked_three_and_four(self):
        for run in ("computer", "dark", "phone-dark"):
            g, where = self._g(run, "stacked2")
            self.assertEqual([b["nest"] for b in g["three"]["boxes"]], [False, True, True], where)
            self.assertEqual([g["esc1"]["boxes"], g["esc2"]["boxes"], g["esc3"]["boxes"]], [2, 1, 0], where)
            self.assertIn("/bm-en/%d/" % IDS["three"], g["esc1"]["active"]["href"], where)
            self.assertIn("/bm-en/%d/" % IDS["two"], g["esc2"]["active"]["href"], where)
            self.assertIn("/bm-en/%d/" % IDS["skip"], g["esc3"]["active"]["href"], where)
            self.assertEqual(g["insideFirst"]["boxes"], 1, where)
            self.assertEqual(g["insideSecond"]["boxes"], 2, where)
            # no limit (147): a link in the third box opens a fourth
            self.assertTrue(g["limitClicked"], where)
            self.assertFalse(g["limit"]["left"], where)
            self.assertEqual(g["limit"]["boxes"], 4, where)
            self.assertEqual(g["limit"]["path"], "/bm-en/%d/" % IDS["bat"], where)

    def test_d_off_is_depth_one(self):
        g, where = self._g("computer", "off")
        self.assertEqual(g["boxes"], 1, where)
        self.assertTrue(g["clicked"], where)
        self.assertTrue(g["left"], where)
        self.assertEqual(g["path"], "/bm-en/%d/" % IDS["two"], where)

    def test_e_norwegian_only_target(self):
        g, where = self._g("computer", "nbonly")
        self.assertTrue(g["clicked"], where)
        self.assertEqual(len(g["inplace"]["boxes"]), 1, where)
        self.assertEqual(g["inplace"]["boxes"][0]["lang"], "nb", where)
        self.assertIsNotNone(g["inplace"]["back"], where)
        self.assertEqual([b["nest"] for b in g["stacked"]["boxes"]], [False, True], where)
        self.assertEqual(g["stacked"]["boxes"][1]["lang"], "nb", where)

    def test_f_keyboard(self):
        g, where = self._g("computer", "keyboard")
        s, i = g["stacked"], g["inplace"]
        self.assertTrue(s.get("reached"), where)
        self.assertEqual(s["opened"]["boxes"], 2, where)
        self.assertTrue(s["opened"]["active"]["inNest"] and s["opened"]["active"]["hw"], where)
        self.assertEqual(s["esc"]["boxes"], 1, where)
        self.assertTrue(s["esc"]["onTwo"], where)
        self.assertTrue(i.get("reached"), where)
        self.assertEqual(i["opened"]["boxes"], 1, where)
        self.assertEqual(i["opened"]["active"]["cls"], "ordpar-mback", where)
        self.assertEqual(i["esc"]["boxes"], 1, where)
        self.assertTrue(i["esc"]["onTwo"], where)

    def test_g_search_page_word_page_list_row(self):
        g, where = self._g("computer", "search")
        self.assertEqual(g["search"]["path"], "/bm-en/", where)       # answered on the search page
        self.assertEqual(g["row"]["rows"], 2, where)
        for case in ("search", "word", "row"):
            self.assertTrue(g[case]["found"], case + ": " + where)
            # the default (147): a second box, then a step inside it, the back line there
            self.assertEqual([b["nest"] for b in g[case]["second"]["boxes"]], [False, True], case + ": " + where)
            self.assertEqual([b["nest"] for b in g[case]["step"]["boxes"]], [False, True], case + ": " + where)
            self.assertIsNotNone(g[case]["step"]["back"], case + ": " + where)
            self.assertTrue(g[case]["step"]["inSecond"], case + ": " + where)

    def test_h_settings_page(self):
        for run in ("computer", "dark", "phone"):
            g, where = self._g(run, "settings")
            st = g["start"]
            i = st["order"].index("minicontent")
            self.assertEqual(st["order"][i + 1], "nestminis", where)
            self.assertNotIn("nestlimit", st["order"], where)      # 147: the limit went
            self.assertEqual(st["sub"], "Small articles", where)
            self.assertEqual(st["title"], "A link inside a small article", where)
            # 147: four choices, `second` the default (their words: test_ordpar_nestminis147.py)
            self.assertEqual([[v, c] for v, c, _w in st["choices"]],
                             [["second", True], ["inplace", False], ["stacked", False], ["off", False]], where)
            self.assertEqual(st["choices"][1][2], "Opens its small article in the same box", where)
            self.assertEqual(st["choices"][3][2], "Opens its whole article", where)
            self.assertTrue(st["hint"], where)
            self.assertEqual(g["stored"], "stacked", where)
            for state in ("start", "stacked", "off"):              # no limit field, whatever is chosen
                self.assertIsNone(g[state]["limitHidden"], state + ": " + where)


if __name__ == "__main__":
    unittest.main()
