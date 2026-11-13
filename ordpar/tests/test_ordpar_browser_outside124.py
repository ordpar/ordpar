"""Site-review decisions 124 (Robin, 2026-10-24): a click or tap outside an open "?" box closes it and does nothing else (headless Edge).

Through `browser/outside124.js`, with real input events (so the browser's own default actions are
measured: a label's click checking its radio, a link's navigation, a drop-down taking the focus),
at 390 and 1,280 px, each with a mouse and with touch (touch emulation, a phone's user agent):

* **Settings** (the hints, decisions 99): the "?" of Definitions pressed — its box open; then a
  press on an unchecked choice of ANOTHER setting, outside the box: the box closes, and the setting
  is unchanged both in storage (`localStorage`) and on screen (the choice not checked); a second
  press on the same choice then picks it (stored and checked).
* **The drop-down**: with the box open, a press on the examples drop-down (`exlimit`) closes the box,
  and the drop-down neither takes the focus (its mousedown's default) nor changes.
* **Another "?"** (the brief's open point, decided by the build: the ruling's plain reading): with
  one box open, a press on another setting's "?" closes the first and opens nothing.
* **A finger scroll** (touch only): scrolling the page with a finger while a box is open is not a
  tap — the page moves, the box stays open, nothing is stored.
* (The pronunciation "?" on an article and in a list row had their cases here until decisions
  123's amendment removed that "?", 2026-11-02.)

`ORDPAR_TEST_BASE` points it at another copy: on ordpar.no before the build (snapshot
442cae9333f) it fails — the outside press both closes the box and picks the setting, focuses the
drop-down and opens the second "?"; under touch the scroll
closes the box. Skipped
without Edge, bun or a build. The mechanism: `ordpar/site/shell.js` `hintGuard`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ABSTRAKT = 98
RUNS = [(w, ptr) for w in (390, 1280) for ptr in ("touch", "mouse")]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_outside124: skipped —", SKIP)
        return
    SITE = harness.Site()
    for w, ptr in RUNS:
        RESULT[(w, ptr)] = SITE.check("outside124.js", {"w": w, "pointer": ptr, "article": ABSTRAKT})


def tearDownModule():
    if SITE:
        SITE.close()


OPEN = {"expanded": "true", "box": True}
CLOSED = {"expanded": "false", "box": False}


@unittest.skipIf(SKIP, SKIP or "")
class OutsideClick(unittest.TestCase):

    def where(self, run, case):
        r = RESULT[run]
        return "%d px, %s, on %s: %s" % (run[0], run[1], r.get("base"), r.get(case))

    def test_a_settings_choice_not_picked(self):
        for run in RUNS:
            s, where = RESULT[run]["settings"], self.where(run, "settings")
            self.assertEqual(s.get("opened"), OPEN, where)
            self.assertTrue(s.get("target"), where)
            self.assertEqual(s["before"], {"stored": None, "checked": False}, where)
            first = s["afterFirst"]
            self.assertEqual(first["box"], CLOSED, where)
            self.assertIsNone(first["stored"], "the setting was stored: " + where)
            self.assertFalse(first["checked"], "the choice was checked: " + where)

    def test_b_the_next_press_picks_it(self):
        for run in RUNS:
            s, where = RESULT[run]["settings"], self.where(run, "settings")
            second = s.get("afterSecond") or {}
            self.assertEqual(second.get("stored"), s["target"]["value"], where)
            self.assertTrue(second.get("checked"), where)
            self.assertEqual(second.get("box"), CLOSED, where)

    def test_c_the_drop_down_untouched(self):
        for run in RUNS:
            s, where = RESULT[run]["select"], self.where(run, "select")
            self.assertEqual(s.get("opened"), OPEN, where)
            self.assertTrue(s.get("visible"), where)
            after = s["after"]
            self.assertEqual(after["box"], CLOSED, where)
            self.assertFalse(after["focused"], "the drop-down took the focus: " + where)
            self.assertEqual(after["value"], "all", where)
            self.assertIsNone(after["stored"], where)

    def test_d_another_question_mark_only_closes(self):
        for run in RUNS:
            s, where = RESULT[run]["other"], self.where(run, "other")
            self.assertEqual(s.get("opened"), OPEN, where)
            self.assertTrue(s.get("second"), where)
            self.assertEqual(s["after"]["first"], CLOSED, where)
            self.assertEqual(s["after"]["second"], CLOSED, where)

    def test_e_a_finger_scroll_is_not_a_tap(self):
        for run in RUNS:
            if run[1] != "touch":
                continue
            s, where = RESULT[run]["scroll"], self.where(run, "scroll")
            self.assertEqual(s.get("opened"), OPEN, where)
            self.assertGreater(s["moved"], 50, "the page did not scroll: " + where)
            self.assertEqual(s["after"], OPEN, where)
            self.assertEqual(s["stored"], 0, where)


if __name__ == "__main__":
    unittest.main()
