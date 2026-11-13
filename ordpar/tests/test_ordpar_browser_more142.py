"""Site-review decisions 142 (Robin, 2026-10-26/27): "More ways to use Ordpar" in a browser (headless
Edge, `browser/more142.js`), at 1,280 px and at 390 px (a phone: touch, a phone's user agent), each
light and dark.

* **The home page's line**: under Random word, the main's first thing shown, below the header (not
  in it), its words "Look words up from any web page, or practise them in Anki: more ways to use
  Ordpar", the link only on "more ways to use Ordpar", to `/more/`, underlined, the line in the muted
  colour; the results area empty (no "Type a Norwegian word…", no box, no height); the search box
  and Random word exactly where they are without the line. A search from the box hides it, and so
  does Random word; the link (clicked, or tapped on a phone) opens `/more/`.
* **`/more/`**: the footer's links Home · Settings · Favourites · History · Help · More ways to use
  Ordpar · About ("About and licence" until site decisions 176), the new link marked the current page (and only it); the sections
  `anki`, `popup`, `offline` (site decisions 178: Anki first), 3 and 8 steps; `/more/#anki` scrolls to its section; a click on each
  code line selects the whole line (`user-select: all`). Since site decisions 146 the URL's line
  carries the saved settings: this check saves only the theme, so it reads
  `https://ordpar.no/bm-en/#theme=light&q={{str}}` (or `dark`); the Copy buttons are
  `test_ordpar_browser_settingsaddr146.py`'s.
* **The dropped line**: not on `/bm-en/` with no search, nor on a missing page (the 404 shell); no
  `.ordpar-empty` there, and no home line.

`ORDPAR_TEST_SHOTS=<folder>` saves the home page, `/more/`'s top, its Anki section and its footer
for each viewport and theme. `ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site
(before 142's deploy: fails — no line, `/more/` a 404). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SITE = None
R = {}
SKIP = harness.skip_reason()
VIEWS = {"computer-light": {"w": 1280, "h": 800, "mobile": False, "dark": False},
         "computer-dark": {"w": 1280, "h": 800, "mobile": False, "dark": True},
         "phone-light": {"w": 390, "h": 844, "mobile": True, "dark": False},
         "phone-dark": {"w": 390, "h": 844, "mobile": True, "dark": True}}
LINE = "Look words up from any web page, or practise them in Anki: more ways to use Ordpar"
LINK = "more ways to use Ordpar"
FOOTER = ["Home", "Settings", "Favourites", "History", "Help", "More ways to use Ordpar",
          "About"]   # "About and licence" until site decisions 176
URL = "https://ordpar.no/bm-en/#q={{str}}"
# site decisions 152: a second rule, the headword's Norwegian-only icon in the pop-up
CSS = (".ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; } "
       ".ordpar-nbhw { display: inline-flex !important; }")


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_more142: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_TEST_SHOTS")
    if shots:
        os.makedirs(shots, exist_ok=True)
    for name, view in VIEWS.items():
        args = dict(view)
        if shots:
            args["shots"] = {"dir": shots.replace("\\", "/"), "prefix": name}
        R[name] = SITE.check("more142.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class More(unittest.TestCase):

    def test_a_the_home_line(self):
        for name, r in R.items():
            with self.subTest(view=name):
                h = r["home"]
                self.assertEqual(h["night"], VIEWS[name]["dark"], h)
                self.assertTrue(h["shown"], h)
                self.assertEqual(h["text"], LINE)
                self.assertEqual(h["link"]["text"], LINK)
                self.assertEqual(h["link"]["href"], "/more/")
                self.assertEqual(h["linkOnly"], LINE[:-len(LINK)])
                self.assertIn("underline", h["link"]["underline"])
                self.assertEqual(h["firstShown"], "ordpar-more-line", h)
                self.assertFalse(h["inHeader"])
                self.assertTrue(h["belowHeader"], h)
                self.assertTrue(h["belowRandom"], h)
                # lined up with the header's column, not the window's edge (Robin, 2026-10-27)
                self.assertLessEqual(abs(h["lineLeft"] - h["columnLeft"]), 1, h)
                self.assertTrue(h["resultsEmpty"], h)
                self.assertEqual(h["resultsHeight"], 0, h)
                self.assertFalse(h["dropped"])
                # the header does not move for the line
                self.assertEqual(h["boxRect"], h["without"]["boxRect"])
                self.assertEqual(h["randomRect"], h["without"]["randomRect"])

    def test_b_a_search_and_random_word_hide_it(self):
        for name, r in R.items():
            with self.subTest(view=name):
                self.assertTrue(r["search"]["answered"], r["search"])
                self.assertFalse(r["search"]["shown"], r["search"])
                self.assertTrue(r["random"]["before"], r["random"])
                self.assertTrue(r["random"]["drawn"], r["random"])
                self.assertFalse(r["random"]["shown"], r["random"])

    def test_c_the_link_opens_more(self):
        for name, r in R.items():
            with self.subTest(view=name):
                self.assertEqual(r["follow"]["path"], "/more/")
                self.assertEqual(r["follow"]["title"], "More ways to use Ordpar — Ordpar")

    def test_d_the_footer_on_more(self):
        for name, r in R.items():
            with self.subTest(view=name):
                m = r["more"]
                # the phone's install hint is only on a real phone's touch screen; leave it out
                links = [x for x in m["links"] if x in FOOTER]
                self.assertEqual(links, FOOTER, m)
                self.assertEqual(m["current"], "page")
                self.assertEqual(m["currentAll"], ["More ways to use Ordpar"])
                self.assertEqual(m["ids"], ["anki", "popup", "offline"])
                self.assertEqual(m["steps"], [3, 8])     # Anki's three, then Definer's eight (178)

    def test_e_anki_scrolled_to(self):
        for name, r in R.items():
            with self.subTest(view=name):
                a = r["anki"]
                self.assertEqual(a["text"], "Practise the words in Anki")
                self.assertTrue(0 <= a["top"] < a["vh"] / 3 or (a["y"] > 0 and a["y"] >= a["ymax"] - 1
                                                                and 0 <= a["top"] < a["vh"]), a)

    def test_f_a_click_selects_the_code_line(self):
        for name, r in R.items():
            with self.subTest(view=name):
                # site decisions 146: the URL's line carries the saved theme, the one setting saved here
                theme = "dark" if VIEWS[name]["dark"] else "light"
                url = URL.replace("#q=", "#theme=%s&q=" % theme)
                self.assertEqual([c["text"] for c in r["code"]], [url, CSS])
                for c in r["code"]:
                    self.assertEqual(c["selected"].strip(), c["text"], c)
                    self.assertEqual(c["userSelect"], "all", c)

    def test_g_the_dropped_line_nowhere(self):
        for name, r in R.items():
            with self.subTest(view=name):
                for where, e in r["empty"].items():
                    self.assertFalse(e["dropped"], (where, e))
                    self.assertEqual(e["empties"], 0, (where, e))
                    self.assertFalse(e["line"], (where, e))


if __name__ == "__main__":
    unittest.main(verbosity=2)
