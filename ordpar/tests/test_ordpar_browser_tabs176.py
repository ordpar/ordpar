"""Site decisions 176 and 175 (Robin, 2026-11-07): the tabs over the about pages and the three
change pages in a browser (headless Edge, `browser/tabs176.js`), at 360 px (a phone, light and dark)
and 1,280 px.

* **The seven pages** — `/about/`, `/coming/`, `/changes/`, `/dictionary-changes/`,
  `/deck-changes/`, `/privacy/`, `/thanks/` — answer 200, each with ONE tab row labelled "About
  Ordpar" right under its `<h1>` and before its first paragraph: About · Coming to Ordpar · Changes ·
  Privacy · Thanks, links to their pages, the current one `aria-current="page"` and pressed (filled
  in the accent, its text the accent's text colour; the others not filled) — Changes on all three
  change pages; Settings' pill shape (`ordpar-jump`, round ends).
* **At 360 px** the row wraps onto a second line and nothing scrolls sideways: no tab past the
  window's right edge, the row no wider than its box, the page no wider than the window.
* **Not on** Help, More ways to use Ordpar or Settings.
* **A tab is a link**: Changes clicked (tapped on a phone) from About lands on `/changes/`, its tab
  pressed there.
* **The footer's link** reads "About" (decisions 176, the footer's label).

The pages' words, the sitemap and the rest: `test_ordpar_changes175.py`. `ORDPAR_176_SHOTS=<dir>`
saves the shots. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

PAGES = {"/about/": "About", "/coming/": "Coming to Ordpar", "/changes/": "Changes",
         "/dictionary-changes/": "Changes", "/deck-changes/": "Changes", "/privacy/": "Privacy",
         "/thanks/": "Thanks"}
TABS = [("About", "/about/"), ("Coming to Ordpar", "/coming/"), ("Changes", "/changes/"),
        ("Privacy", "/privacy/"), ("Thanks", "/thanks/")]
NONE = ["/help/", "/more/", "/settings/"]
RUNS = [("phone", dict(w=360, h=740, mobile=True, dark=False)),
        ("phone-dark", dict(w=360, h=740, mobile=True, dark=True)),
        ("computer", dict(w=1280, h=900, mobile=False, dark=False))]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_tabs176: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_176_SHOTS")
    for tag, run in RUNS:
        args = dict(run, pages=list(PAGES), none=NONE)
        if shots:
            os.makedirs(shots, exist_ok=True)
            args["shots"] = {"dir": shots.replace("\\", "/"), "tag": tag}
        RESULT[tag] = SITE.check("tabs176.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Tabs176(unittest.TestCase):

    def each(self):
        for tag, run in RUNS:
            for path, current in PAGES.items():
                yield tag, run, path, current, RESULT[tag]["pages"][path], RESULT[tag]

    def test_a_the_row_on_the_seven_pages(self):
        for tag, _run, path, _cur, r, _all in self.each():
            self.assertEqual(r["status"], 200, (tag, path))
            n = r["nav"]
            self.assertIsNotNone(n, (tag, path))
            self.assertEqual(n["label"], "About Ordpar", (tag, path))
            self.assertIn("ordpar-jump", n["cls"].split(), (tag, path))      # Settings' pills
            self.assertEqual((n["after"], n["before"]), ("H1", "P"), (tag, path, n))
            self.assertEqual([(t["text"], t["href"]) for t in n["tabs"]], TABS, (tag, path))

    def test_b_the_current_one_pressed(self):
        for tag, _run, path, current, r, whole in self.each():
            tabs = r["nav"]["tabs"]
            self.assertEqual([t["text"] for t in tabs if t["current"] == "page"], [current], (tag, path))
            for t in tabs:
                if t["current"] == "page":
                    self.assertEqual((t["bg"], t["color"]), (whole["accent"], whole["accentText"]), (tag, path, t))
                else:
                    self.assertNotEqual(t["bg"], whole["accent"], (tag, path, t))
                self.assertNotEqual(t["radius"], "0px", (tag, path, t))       # the pills' round ends

    def test_c_wrapping_and_no_sideways_scroll(self):
        for tag, run, path, _cur, r, _all in self.each():
            n = r["nav"]
            self.assertFalse(r["pageWide"], (tag, path))
            self.assertFalse(n["rowWide"], (tag, path))
            for t in n["tabs"]:
                self.assertLessEqual(t["right"], r["vw"], (tag, path, t))
                self.assertGreaterEqual(t["left"], 0, (tag, path, t))
            if run["w"] == 360:
                self.assertGreaterEqual(n["rows"], 2, (tag, path))          # wrapped, not scrolled
            else:
                self.assertEqual(n["rows"], 1, (tag, path))

    def test_d_none_elsewhere(self):
        for tag, _run in RUNS:
            self.assertEqual(RESULT[tag]["none"], {p: False for p in NONE}, tag)

    def test_e_a_tab_is_a_link(self):
        for tag, _run in RUNS:
            self.assertEqual(RESULT[tag]["clicked"], {"path": "/changes/", "current": "Changes"}, tag)

    def test_f_the_footer_says_about(self):
        for tag, _run, path, _cur, r, _all in self.each():
            self.assertEqual(r["footAbout"], "About", (tag, path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
