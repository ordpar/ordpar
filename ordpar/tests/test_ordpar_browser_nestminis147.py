"""Site decisions 147 (Robin, 2026-10-29): nested small articles, the new default and rule 3 (headless Edge).

The setting `nestminis` gets four choices — in place, **second** (the new default: a link in the
first box opens a second box, a link inside the second box changes that box, with the "← word" line
back), stacked, off — and no limit. And the rule that nothing done inside the small article boxes
ever scrolls the main window. Through `browser/nestminis147.js`, with real mouse clicks and
real keys, on *båt* (8608) -> *skip (II)* (52833) -> *slagskip* (54202) -> *krigsskip* (32118) ->
*orlogsskip* (43359), all translated:

* the default with nothing saved: the first box, a second box, two steps in the second box (the
  back line in the second box only, "← <word>", the focus on it), the back line one word back (the
  focus on the link stepped from), Escape stepping back then closing the second (the focus on the
  word that opened it), then the first; a click inside the first box closes the second; the same
  word again closes its box; a click outside closes all; aria-expanded — computer, 390 px, light and
  dark;
* the default from the keyboard: Enter in the first box opens the second, the focus on its
  headword; Enter in the second steps, the focus on the back line; Escape back, then closed;
* `stacked`: four boxes (three after the first: no limit); Escape closes one at a time;
* **rule 3**: in place, second, stacked and off, at 1,280 and 390 px, with `miniscroll` on and off,
  the page first scrolled down (and moved again by the "reader" between actions, the box too where
  it scrolls): the page's scroll (x and y) is the same just after each action as just before it —
  opening from the article, each link in a box, the back line, Escape (a step back and each close),
  a click inside the first box, a click outside; and each step back puts back the box's own scroll
  where the box scrolls (since decisions 165, when a nested box opens above its word where the room
  below is short, the 390 x 844 boxes no longer have to scroll: so rule 3 runs also in a short
  window, 1,280 x 240, and a phone on its side, 760 x 280, where they still do);
* the settings page: the four choices, the default first (107), in Robin's words, the default checked, no limit
  field, the hint's words.

Rule 3 was shown failing on https://ordpar.no before the build (`ORDPAR_TEST_BASE`; the report of
2026-10-29). Each run and group is its own check, so one that cannot run (the live site's old
choices) fails alone. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

IDS = dict(bat=8608, skip=52833, two=54202, three=32118, four=43359)
MODES = ["inplace", "second", "stacked", "off"]
RUNS = {
    "computer": dict(w=1280, h=900, groups=["rule3", "def", "keyboard", "stacked", "settings"], modes=MODES),
    "noscroll": dict(w=1280, h=900, scrollSettings={"miniscroll": "off"}, groups=["rule3"], modes=MODES[:3]),
    "dark": dict(w=1280, h=900, theme="dark", groups=["def", "stacked", "settings"]),
    "phone": dict(w=390, h=844, mobile=True, groups=["rule3", "def", "stacked", "settings"], modes=MODES),
    "phone-noscroll": dict(w=390, h=844, mobile=True, scrollSettings={"miniscroll": "off"}, groups=["rule3"],
                           modes=["second"]),
    "phone-dark": dict(w=390, h=844, mobile=True, theme="dark", groups=["def", "stacked", "settings"]),
    # short windows (decisions 165): since a nested box opens above its word where the room below is
    # short, at 390 x 844 it no longer has to scroll; here the boxes are taller than the window allows,
    # so a step back from a box scrolled inside is still checked (`test_e`); 240 and 280 tall since a box
    # keeps its side on a scroll (Robin, 2026-11-04): at 320 and 360 it stayed on its roomier side, unscrolled
    "computer-short": dict(w=1280, h=240, groups=["rule3"], modes=["inplace", "second"]),
    "phone-landscape": dict(w=760, h=280, mobile=True, groups=["rule3"], modes=["second"]),
}
#: what WORDS in `test_ordpar_nestminis147.py` pins, as the page draws it
CHOICES = [["second", True, "Opens its small article in a second box; a link there changes that box"],
           ["inplace", False, "Opens its small article in the same box"],
           ["stacked", False, "Opens each small article in a box of its own"],
           ["off", False, "Opens its whole article"]]
HINT = ("In the same box: the box changes to the new word, and a line at its top, such as \"← skip\", goes "
        "back one word at a time. In a second box: the new small article opens below its word, over the first; "
        "a link inside the second box changes that box, with the same line back. In a box of its own: every "
        "link opens one more box, over the one before. There is no limit. A click outside every box closes "
        "them all.")

#: `ORDPAR_147_GROUPS=rule3` runs only those groups (the fault shown on the live site)
ONLY = [g for g in os.environ.get("ORDPAR_147_GROUPS", "").split(",") if g]

SITE = None
RESULT = {}          # (run, group[, mode]) -> the check's dict, or {"error": text}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_nestminis147: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_SHOTS")
    for name, a in RUNS.items():
        for group in [g for g in a["groups"] if not ONLY or g in ONLY]:
            for mode in (a["modes"] if group == "rule3" else [None]):
                args = dict(a, ids=IDS, groups=[group], modes=[mode] if mode else [])
                if shots:
                    args.update(shots=shots, shotPrefix="nest147-%s-" % name)
                key = (name, group, mode) if mode else (name, group)
                try:
                    res = SITE.check("nestminis147.js", args, timeout=600)
                    g = res["groups"][group]
                    RESULT[key] = dict(g[mode], base=res["base"]) if mode else dict(g, base=res["base"])
                except Exception as e:      # noqa: BLE001 — reported by the test that reads it
                    RESULT[key] = {"error": str(e)[:1500]}


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Nest147(unittest.TestCase):

    def _g(self, *key):
        if key not in RESULT:
            self.skipTest("not run (ORDPAR_147_GROUPS)")
        g = RESULT[key]
        where = "%s on %s" % ("/".join(key), g.get("base"))
        self.assertNotIn("error", g, "%s: %s" % ("/".join(key), g.get("error")))
        return g, where

    def test_a_the_default(self):
        for run in [r for r in RUNS if "def" in RUNS[r]["groups"]]:
            g, where = self._g(run, "def")
            self.assertEqual(g["mode"], "second", where)
            self.assertEqual([b["nest"] for b in g["first"]["boxes"]], [False], where)
            self.assertEqual(g["first"]["expanded"], "true", where)
            self.assertEqual([b["nest"] for b in g["second"]["boxes"]], [False, True], where)
            self.assertEqual(g["second"]["expanded"], "true", where)
            self.assertTrue(all(b["vis"] for b in g["second"]["boxes"]), where)
            head1 = g["second"]["boxes"][1]["head"]
            # two steps in the second box: still two boxes, the back line in the second only
            self.assertTrue(g["clicked3"] and g["clicked4"], where)
            for st in ("step1", "step2"):
                self.assertEqual([b["nest"] for b in g[st]["boxes"]], [False, True], st + ": " + where)
                self.assertEqual(g[st]["backs"], [False, True], st + ": " + where)
                self.assertEqual(g[st]["active"]["cls"], "ordpar-mback", st + ": " + where)
                self.assertEqual(g[st]["active"]["box"], 1, st + ": " + where)
            self.assertEqual(g["step1"]["back"], {"text": "← " + head1, "label": "Back to " + head1}, where)
            head2 = g["step1"]["boxes"][1]["head"]
            self.assertEqual(g["step2"]["back"]["text"], "← " + head2, where)
            self.assertEqual(g["step2"]["path"], "/bm-en/%d/" % IDS["bat"], where)
            # the back line: one word back, the focus on the link stepped from
            self.assertEqual(g["back1"]["boxes"][1]["head"], head2, where)
            self.assertEqual(g["back1"]["back"]["text"], "← " + head1, where)
            self.assertIn("/bm-en/%d/" % IDS["four"], g["back1"]["active"]["href"], where)
            self.assertEqual(g["back1"]["active"]["box"], 1, where)
            self.assertEqual(g["back1"]["fourExpanded"], "false", where)
            # Escape: a step back, then the second closes (the focus on its word), then the first
            self.assertEqual(len(g["esc1"]["boxes"]), 2, where)
            self.assertEqual(g["esc1"]["boxes"][1]["head"], head1, where)
            self.assertIsNone(g["esc1"]["back"], where)
            self.assertIn("/bm-en/%d/" % IDS["three"], g["esc1"]["active"]["href"], where)
            self.assertEqual(len(g["esc2"]["boxes"]), 1, where)
            self.assertIn("/bm-en/%d/" % IDS["two"], g["esc2"]["active"]["href"], where)
            self.assertEqual(g["esc2"]["active"]["box"], 0, where)
            self.assertEqual(g["esc2"]["twoExpanded"], "false", where)
            self.assertEqual(g["esc3"]["boxes"], [], where)
            self.assertIn("/bm-en/%d/" % IDS["skip"], g["esc3"]["active"]["href"], where)
            self.assertEqual(g["esc3"]["active"]["box"], -1, where)
            self.assertEqual(g["esc3"]["expanded"], "false", where)
            # clicks: inside the first closes the second; the same word again; outside closes all
            self.assertEqual(len(g["insideFirst"]["boxes"]), 1, where)
            self.assertEqual(g["insideFirst"]["expanded"], "false", where)
            self.assertEqual(g["sameAgain"]["boxes"], 1, where)
            self.assertEqual(g["outside"]["boxes"], 0, where)
            self.assertEqual(g["outside"]["expanded"], "false", where)

    def test_b_the_default_from_the_keyboard(self):
        g, where = self._g("computer", "keyboard")
        self.assertTrue(g.get("reached1") and g.get("reached2"), where)
        self.assertEqual(g["opened"]["boxes"], 2, where)
        self.assertTrue(g["opened"]["active"]["hw"] and g["opened"]["active"]["box"] == 1, where)
        self.assertEqual(g["stepped"]["boxes"], 2, where)
        self.assertEqual(g["stepped"]["active"]["cls"], "ordpar-mback", where)
        self.assertEqual(g["stepped"]["active"]["box"], 1, where)
        self.assertIsNotNone(g["stepped"]["back"], where)
        self.assertEqual(g["esc1"]["boxes"], 2, where)
        self.assertTrue(g["esc1"]["onThree"], where)
        self.assertEqual(g["esc2"]["boxes"], 1, where)
        self.assertTrue(g["esc2"]["onTwo"], where)

    def test_c_stacked_without_a_limit(self):
        for run in [r for r in RUNS if "stacked" in RUNS[r]["groups"]]:
            g, where = self._g(run, "stacked")
            self.assertTrue(g["clicked4"], where)
            self.assertEqual([b["nest"] for b in g["four"]["boxes"]], [False, True, True, True], where)
            self.assertEqual(g["four"]["path"], "/bm-en/%d/" % IDS["bat"], where)
            for b in g["four"]["boxes"]:
                self.assertGreaterEqual(b["l"], 0, where)
                self.assertLessEqual(b["r"], g["four"]["win"], where)
            self.assertEqual(g["esc"], [3, 2, 1, 0], where)

    def test_d_rule_three_the_page_never_moves(self):
        # decisions 147: nothing done inside the small article boxes ever scrolls the main window
        moved, broken = [], []         # every move in every run and mode, listed at once
        for run, a in RUNS.items():
            if "rule3" not in a["groups"]:
                continue
            for mode in a["modes"]:
                if (run, "rule3", mode) not in RESULT:
                    self.skipTest("not run (ORDPAR_147_GROUPS)")
                g = RESULT[(run, "rule3", mode)]
                where = "%s/%s" % (run, mode)
                if "error" in g:
                    broken.append("%s: %s" % (where, g["error"][:200]))
                    continue
                if not g["start"]["y"] > 0:
                    broken.append("%s: the page was not scrolled down first" % where)
                names = [x["name"] for x in g["actions"]]
                want = ["open", "click outside"]
                if mode in ("inplace", "second"):
                    want += ["back line", "back line again", "escape (a step back)"]
                if mode in ("second", "stacked"):
                    want += ["click inside the first box"]
                broken += ["%s: no action %r" % (where, n) for n in want if n not in names]
                for x in g["actions"]:
                    if abs(x["after"]["y"] - x["before"]["y"]) > 1 or abs(x["after"]["x"] - x["before"]["x"]) > 1:
                        moved.append("%s: %s moved the page from %s to %s"
                                     % (where, x["name"], x["before"], x["after"]))
                if g["actions"][-1]["boxes"] != 0:
                    broken.append("%s: boxes left open at the end" % where)
        self.assertEqual(moved, [], "\n".join(moved))
        self.assertEqual(broken, [], "\n".join(broken))

    def test_e_a_step_back_restores_the_boxs_own_scroll(self):
        seen = 0
        for run, a in RUNS.items():
            if "rule3" not in a["groups"]:
                continue
            for mode in [m for m in a["modes"] if m in ("inplace", "second")]:
                g, where = self._g(run, "rule3", mode)
                for b in g["box"]:
                    if "want" not in b or not b["scrolls"] or b["want"] is None:
                        continue
                    # as far as the box now scrolls: a nested box's height follows its word's place in the window
                    # (`placeNested`), so after the reader moved the page it can be taller, with less to scroll
                    self.assertAlmostEqual(b["got"], min(b["want"], b["max"]), delta=1, msg="%s: %s" % (b["at"], where))
                    seen += bool(b["want"])
        self.assertGreater(seen, 0, "no step back from a box scrolled inside was checked")

    def test_f_the_settings_page(self):
        for run in [r for r in RUNS if "settings" in RUNS[r]["groups"]]:
            g, where = self._g(run, "settings")
            st = g["start"]
            i = st["order"].index("minicontent")
            self.assertEqual(st["order"][i + 1], "nestminis", where)
            self.assertFalse(st["limit"], where)
            self.assertNotIn("nestlimit", st["order"], where)
            self.assertEqual(st["sub"], "Small articles", where)
            self.assertEqual(st["title"], "A link inside a small article", where)
            self.assertEqual(st["choices"], CHOICES, where)
            self.assertEqual(g["hint"], HINT, where)


if __name__ == "__main__":
    unittest.main()
