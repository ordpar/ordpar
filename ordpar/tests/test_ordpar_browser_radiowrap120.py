"""Site-review decisions 120 (Robin, 2026-10-24): on a phone a setting's long choice wraps beside its radio button (headless Edge).

Robin's shot from his phone: Settings → Article → Language, "Norwegian, with the English hidden
until revealed" on the line below its button. Each choice was a wrapping flex row
(`shell.css` `.ordpar-radio`: `flex-wrap: wrap; align-items: center`), so a label too long for the
line dropped whole onto the next. Now the button keeps its own size and the label takes the rest of
the line, wrapping inside it, its first line level with the button (`align-items: baseline`).

Through `browser/radiowrap120.js`, on the settings page at 390 px (a phone's width) and at 1280,
every choice (`.ordpar-radio`; a hidden setting's fieldset shown for the measuring):

* the label starts on the button's line: its first line's box overlaps the button's vertically and
  the label starts right of the button, never below it;
* the button's middle is level with the first line's middle (within 3 px) — beside the first line,
  not the middle of two;
* at 390 px at least one label (the Language choice above) takes two lines or more, so the case is
  met, and nothing is wider than the window;
* the swatch choices (the colour setting) and the hidden choice notes (`.ordpar-choice-note`, the
  radios' descriptions since decisions 99) stay as they were: a note hidden and not laid out;
* the drop-down setting (`.ordpar-select`, decisions 112) is still on its own line under its
  title, inside the window.

`ORDPAR_TEST_BASE` points it at another copy (the live site before the fix, snapshot be80aae5188:
fails — at 390 px the long labels start below their buttons). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

LONG = "Norwegian, with the English hidden until revealed"
SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_radiowrap120: skipped —", SKIP)
        return
    SITE = harness.Site()
    for w in (390, 1280):
        RESULT[w] = SITE.check("radiowrap120.js", {"w": w})


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class RadioWrap(unittest.TestCase):

    def _rows(self, w):
        rows = RESULT[w]["rows"]
        self.assertGreater(len(rows), 10, "too few choices measured on %s" % RESULT[w]["base"])
        return rows

    def _where(self, w, r):
        return "at %d px on %s: %s=%s %r, radio %s, first line %s, %d line(s)" % (
            w, RESULT[w]["base"], r["key"], r["value"], r["text"], r["radio"], r["first"], r["lines"])

    def test_a_the_first_line_beside_the_button(self):
        for w in RESULT:
            for r in self._rows(w):
                where = self._where(w, r)
                self.assertTrue(r["first"], where)
                self.assertLess(r["first"]["t"], r["radio"]["b"], where)
                self.assertGreater(r["first"]["b"], r["radio"]["t"], where)
                self.assertGreaterEqual(r["label"]["l"], r["radio"]["r"], where)

    def test_b_level_with_the_first_line(self):
        for w in RESULT:
            for r in self._rows(w):
                mid_radio = (r["radio"]["t"] + r["radio"]["b"]) / 2
                mid_line = (r["first"]["t"] + r["first"]["b"]) / 2
                self.assertLessEqual(abs(mid_radio - mid_line), 3, self._where(w, r))

    def test_c_a_long_choice_wraps_at_a_phones_width(self):
        rows = self._rows(390)
        longs = [r for r in rows if r["lines"] > 1]
        self.assertTrue(longs, "no label takes two lines at 390 px")
        lang = [r for r in rows if r["text"] == LONG]
        self.assertTrue(lang, "no choice %r" % LONG)
        self.assertGreater(lang[0]["lines"], 1, self._where(390, lang[0]))
        self.assertLessEqual(RESULT[390]["docWidth"], RESULT[390]["vw"])

    def test_d_swatches_and_notes(self):
        for w in RESULT:
            rows = self._rows(w)
            self.assertTrue([r for r in rows if r["swatch"]], "no swatch choice at %d px" % w)
            for r in rows:
                if r["note"]:
                    self.assertTrue(r["note"]["hidden"] and not r["note"]["shown"], self._where(w, r))

    def test_e_the_drop_down(self):
        for w in RESULT:
            s = RESULT[w]["select"]
            self.assertTrue(s["found"], "no drop-down at %d px" % w)
            self.assertGreaterEqual(s["top"], s["legendBottom"] - 1, s)
            self.assertLessEqual(s["right"], RESULT[w]["vw"], s)


if __name__ == "__main__":
    unittest.main()
