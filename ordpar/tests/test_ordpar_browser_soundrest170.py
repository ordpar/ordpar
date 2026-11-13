"""Site decisions 170 (Robin, 2026-11-06): the sound icon's early load follows the setting "When a
linked article or page is loaded" (`minifetch`), as `ahead.js` reads it (`ordparAhead.mode`), in
headless Edge on a computer (`browser/soundrest170.js`), on *hus* (24627):

* `click` ("When its link is clicked"): the pointer resting on an example's sound icon well past
  `REST_MS` asks the audio Worker for nothing; the press then asks for the clip (a press plays as
  before);
* `point` (the default) and `page`: the rest asks for that one clip, as since 159.

The second part (Robin, 2026-11-06, "Yes, marks now"; brief
`evidence/brief-table-marks-170-2026-11-06.md`): the sound list `/audio/<k>.json` is fetched only
when a recording is wanted —

* under every value, opening the article asks for no list, and the table still shows its icons at
  open, drawn from the page's mark (`data-a-cells`): *hus*'s five, `et hus`, `hus`, `husa`,
  `husene`, `huset`, in each of the two tables drawn (wide and narrow), as the list drew them;
* under `click`, nothing is asked before a press (no list at the rest) and no `preconnect` to the
  Worker is made; the press asks for its block's list once and the clip; a second icon of the
  same block pressed asks for no list again;
* under `point` and `page`, the rest asks for the list once and that clip, and the `preconnect` is
  made as before; the press and a second press ask for no list again;
* a small article opened on *hus* (hjem, 23742, `mount`) draws its icons and asks for no list.

The Worker is never reached: the check intercepts every request to its address (the DevTools
`Fetch` domain), answers it with a stand-in of a few bytes and counts it, so a run costs none of
the Worker's daily requests (`test_ordpar_browser_audio159.py` plays the real clips). The lists on
our own host are intercepted and counted too, and checked against the page's resource timing.
The first part fails on the build deployed as 9b50a8b8d9c3375d (`click`: one request on the rest);
the second part on the same build (a list asked for at every open, a `preconnect` under `click`,
the small article's list). Before the full build, `ORDPAR_TEST_OVERLAY=<folder>` holding
`site/ordpar.js` and `site/shell-pages.js` shipped from the working tree (`sitegen.page.shipped`)
and *hus*'s page with the tables' mark (a `build_site.py --ids` render into a scratch folder).
Skipped without Edge, bun or a build.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SITE = None
RESULT = {}
SKIP = harness.skip_reason()
CLIP = re.compile(r"^https://ordpar-audio\.ordpar\.workers\.dev/ordpar-[0-9a-f]{16}\.mp3$")
#: hus's table forms with a clip, as the names list drew them before the marks (the deployed build;
#: each twice: the wide table and the narrow one are both drawn, one shown)
HUS_CELLS = ["et hus", "et hus", "hus", "hus", "husa", "husa", "husene", "husene", "huset", "huset"]


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_soundrest170: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("soundrest170.js", {}, timeout=240)["cases"])


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class SoundRest(unittest.TestCase):

    def test_a_the_page_reads_each_value(self):
        for v in ("click", "point", "page"):
            with self.subTest(v):
                c = RESULT[v]
                self.assertEqual(c["mode"], v, c)
                self.assertGreaterEqual(c["icons"], 3, c)

    def test_b_click_loads_no_clip_before_a_press(self):
        c = RESULT["click"]
        self.assertEqual(c["rested"], 0, c)
        self.assertGreaterEqual(c["pressed"], 1, c)       # the press still asks for it

    def test_c_point_and_page_load_the_rested_clip(self):
        for v in ("point", "page"):
            with self.subTest(v):
                c = RESULT[v]
                self.assertEqual(c["rested"], 1, c)
                self.assertRegex(c["restedUrl"], CLIP)
                self.assertEqual(c["pressed"], 1, c)      # the press plays it: nothing more asked

    def test_d_no_list_when_an_article_opens(self):
        for v in ("click", "point", "page"):
            with self.subTest(v):
                c = RESULT[v]
                self.assertEqual(c["listsOpen"], 0, c)
                self.assertEqual(c["cells"], HUS_CELLS, c)      # the table's icons, with no list

    def test_e_the_list_once_when_a_recording_is_wanted(self):
        c = RESULT["click"]
        self.assertEqual(c["listsRest"], 0, c)                   # under click: nothing before a press
        self.assertEqual((c["listsPress"], c["listsSecond"]), (1, 1), c)
        for v in ("point", "page"):
            with self.subTest(v):
                c = RESULT[v]
                self.assertEqual((c["listsRest"], c["listsPress"], c["listsSecond"]), (1, 1, 1), c)

    def test_f_no_preconnect_under_click(self):
        self.assertIs(RESULT["click"]["preconnect"], False, RESULT["click"])
        for v in ("point", "page"):
            with self.subTest(v):
                self.assertIs(RESULT[v]["preconnect"], True, RESULT[v])

    def test_g_a_small_article_asks_for_no_list(self):
        m = RESULT["mini"]
        self.assertTrue(m["opened"], m)
        self.assertGreaterEqual(m["icons"], 1, m)
        self.assertEqual((m["listsBefore"], m["listsAfter"]), (0, 0), m)


if __name__ == "__main__":
    unittest.main()
