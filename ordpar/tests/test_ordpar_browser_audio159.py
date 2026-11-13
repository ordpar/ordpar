"""Site decisions 159 (Robin's pick from the style lab, 2026-11-02): the sound icons in the browser
(headless Edge, `browser/audio159.js`), on a computer (the mouse) and a phone (touch), by day and at
night, playing Ida's clips from the live Worker (`https://ordpar-audio.ordpar.workers.dev/`):

* *hus* (24627) shows icons on its headword (beside the word), its definition lines, its examples
  and, the Inflection toggle opened, its table forms (*et hus*, *huset* …); each a real `<button>`,
  focusable, named "Play" in the accessibility tree ("Spill av" with the labels in Norwegian); every
  icon's text is in the article's names file; at rest day #bab8b8, night #6f6b6c;
* a press plays the clip through the Worker (the request's address `…/ordpar-<16 hex>.mp3`,
  `readyState`, `duration`), the icon in the accent colour and named "Stop" while it plays; a second
  press stops it;
* on a computer the pointer crossing four icons asks the Worker for nothing, resting on one asks for
  its clip once, and the press then plays it with no second request; the hover colour is the text
  colour (darker by day, lighter at night);
* the speed set to 90 %: `playbackRate` 0.9, the pitch kept;
* a small article (*hjem*, opened on *hus*) carries its icons, and one plays inside the box, which
  stays open;
* *være* (69211): the set phrase *være eller ikke være*'s icon inside its term, at its end, on the
  term's line;
* *smuldre* (54865, a run-6 table, not voiced): only a form whose text has a clip gets an icon (the
  bare *smuldre*, the headword's clip); the other forms none.
* *bru, bro* (7663, site decisions 160): each spelling of the headword line its own icon, beside
  it, in order; on the word page `/bm-en/bru/` the same, the headword no link (as ordbokene's
  results; Robin, 2026-11-02), and no "Article page" link under the article (site decisions 168,
  re-ruled 2026-11-06 (everywhere); until then it was asserted there).

The clips cost a few of the Worker's 100,000 requests a day per run (about ten). `ORDPAR_TEST_BASE=
https://ordpar.no` runs it on the live site (before 159's deploy: fails, no icons); before the full
build, `ORDPAR_TEST_OVERLAY=<folder>` with those pages rendered through the build (with
`--audio-names`) and their `audio/` and `site/`. Skipped without Edge, bun or a build.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SITE = None
RESULTS = {}
SKIP = harness.skip_reason()
CLIP = re.compile(r"^https://ordpar-audio\.ordpar\.workers\.dev/ordpar-[0-9a-f]{16}\.mp3$")
DAY, NIGHT = "rgb(186, 184, 184)", "rgb(111, 107, 108)"


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_audio159: skipped —", SKIP)
        return
    SITE = harness.Site()
    for mobile in (False, True):
        for night in (False, True):
            RESULTS[("phone" if mobile else "computer") + ("-night" if night else "-day")] = \
                SITE.check("audio159.js", {"mobile": mobile, "night": night}, timeout=240)["cases"]


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Audio(unittest.TestCase):

    def test_a_hus_shows_icons(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                h = c["hus"]
                self.assertEqual(h["head"], 1, h)
                self.assertTrue(h["headBeside"], h)
                self.assertGreater(h["def"], 10, h)
                self.assertGreater(h["ex"], 10, h)
                self.assertGreater(h["cell"], 2, h)
                self.assertEqual(h["other"], 0, h)
                self.assertEqual(h["type"], "submit" if False else "button")
                self.assertIn("et hus", c["cellText"])
                self.assertEqual(c["keys"]["miss"], [], c["keys"])
                self.assertEqual(c["hus"]["night"], n.endswith("night"))
                self.assertEqual(h["colour"], NIGHT if n.endswith("night") else DAY, h)
                # 1.00 rem: the icon's box is the root's font size
                self.assertEqual(h["size"][0], round(h["fontPx"]), h)

    def test_b_named_for_screen_readers(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                self.assertGreater(c["ax"]["play"], 20, c["ax"])
                self.assertEqual(c["ax"]["spill"], 0, c["ax"])
                self.assertTrue(c["focusable"])
                self.assertGreater(c["labels"]["spill"], 20, c["labels"])
                self.assertEqual(c["labels"]["play"], 0, c["labels"])

    def test_c_a_press_plays_through_the_worker(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                pr = c["press"]
                self.assertTrue(pr["played"], pr)
                self.assertRegex(pr["last"]["src"], CLIP)
                self.assertGreaterEqual(pr["last"]["readyState"], 2, pr)
                self.assertGreater(pr["last"]["duration"], 0.2, pr)
                self.assertIsNone(pr["last"]["error"], pr)
                self.assertTrue(pr["during"]["cls"], pr)
                self.assertEqual(pr["during"]["label"], "Stop", pr)
                self.assertEqual(pr["during"]["colour"], _rgb(c["accent"]), (pr, c["accent"]))
                for u in pr["requests"]:
                    self.assertRegex(u, CLIP)

    def test_d_a_second_press_stops(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                s = c["stop"]
                self.assertEqual((s["paused"], s["cls"], s["playing"], s["label"]), (True, False, False, "Play"), s)
                self.assertTrue(s["cut"], s)       # stopped by the press, not run to its end (2026-11-04)
                # since 2026-11-06 on an example's clip, long enough that only the press can stop it
                # in time (the headword's 0.7 s ran out first against the live site, twice)
                self.assertGreaterEqual(s["duration"], 1.5, s)

    def test_e_loading_on_rest(self):
        for n, c in RESULTS.items():
            if n.startswith("phone"):
                continue
            with self.subTest(n):
                r = c["rest"]
                # a true crossing (every icon left within 150 ms, as the page measured it) in one
                # of three passes; a pass the machine's load stretched to a rest is made again
                self.assertLess(r["dwell"], 150, r)
                self.assertEqual(r["crossed"], 0, r)
                self.assertEqual(r["rested"], 1, r)
                self.assertRegex(r["restedUrl"], CLIP)
                self.assertTrue(r["playing"], r)
                self.assertEqual(r["afterPress"], 1, r)            # the press asked for nothing more
                self.assertEqual(r["last"]["src"], r["restedUrl"], r)
                self.assertEqual(r["hover"], _rgb(c["text"]), (r, c["text"]))

    def test_f_ninety_percent_pitch_kept(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                s = c["speed"]
                self.assertEqual(s["rate"], 0.9, s)
                self.assertAlmostEqual(s["last"]["playbackRate"], 0.9, places=3)
                self.assertTrue(s["last"]["preservesPitch"], s)

    def test_g_a_small_article_plays(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                m = c["mini"]
                self.assertTrue(m["opened"], m)
                self.assertGreater(m["icons"], 0, m)
                self.assertTrue(m["played"], m)
                self.assertTrue(m["still"] and m["inBox"], m)
                self.assertRegex(m["last"]["src"], CLIP)

    def test_h_a_set_phrase_on_its_line(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                ph = c["phrase"]
                self.assertTrue(ph and ph["inside"], ph)
                self.assertTrue(ph["last"] and ph["sameLine"] and ph["afterWords"], ph)

    def test_i_run6_forms_without_a_clip_have_no_icon(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                r = c["run6"]
                self.assertGreater(r["forms"], 4, r)
                self.assertLessEqual(len(r["icons"]), 1, r)
                self.assertTrue(set(r["icons"]) <= {"smuldre"}, r)

    def test_j_every_spelling_of_the_headword(self):
        for n, c in RESULTS.items():
            with self.subTest(n):
                s = c["spellings"]["page"]
                self.assertEqual(s["words"], ["bru", "bro"], s)
                self.assertEqual(s["icons"], ["bru", "bro"], s)          # in order, one each
                self.assertEqual(s["beside"], [True, True], s)
                self.assertFalse(s["inLink"], s)
                lu = c["spellings"]["lookedUp"]                          # the word page: no link
                self.assertTrue(lu, c["spellings"])
                self.assertEqual(lu["words"], ["bru", "bro"], lu)
                self.assertEqual(lu["links"], 0, lu)
                self.assertEqual(lu["icons"], ["bru", "bro"], lu)
                self.assertEqual(lu["beside"], [True, True], lu)
                self.assertFalse(lu["articlePage"], lu)                  # 168 re-ruled: no "Article page"


def _rgb(css):
    """`#rrggbb` (or an `rgb(...)` already) as getComputedStyle writes it."""
    css = css.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", css)
    if not m:
        return css
    h = m.group(1)
    return "rgb(%d, %d, %d)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


if __name__ == "__main__":
    unittest.main()
