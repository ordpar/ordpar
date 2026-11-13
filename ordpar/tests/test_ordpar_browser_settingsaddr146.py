"""Site-review decisions 146 (Robin, 2026-10-27/28): the reader's settings in the address, for a
pop-up dictionary such as Definer, in a browser (headless Edge, `browser/settingsaddr146.js`), at
1,280 px and at 390 px (a phone: touch, a phone's user agent), the saved theme light and dark.
The source side: `test_ordpar_settingsaddr146.py`.

* **The visit**: `/bm-en/#defs=en&theme=<the other>&mini=en&q=hus` goes on to the word's page
  `/bm-en/hus/` and shows those settings — the other theme, the definitions' Norwegian hidden (the
  English alone), the mini's English-only rule — with the settings part gone from the address and
  kept in `sessionStorage`; `localStorage`'s settings unchanged; History's entry the plain search.
* **Onward**: the article's own page (a page load in the same tab, by its address: the result row
  has no "Article page" link since site decisions 168, re-ruled 2026-11-06 (everywhere)), and a
  click on a small article's headword (another), keep them; `localStorage` still unchanged.
* **A fresh tab** in the same browser, opened without them: the saved settings.
* **`/settings/`** opened with settings in its address (in the visit's tab): the saved ones,
  drawn and applied (the session's call, 2026-10-28). **`/more/`** opened so: its step-4 line
  still the saved settings' address (the session's second call).
* **`/more/`**: the step-4 line the saved settings' address (`theme=…&defs=no&exlimit=2&listview=multi`,
  `{{str}}` last; `listview` saved as `multi` since site decisions 158, so that *hus* opens its
  article), the CSS line as written; a Copy button beside each, alike; each click copies
  its line (read back from the clipboard) and says "Copied", "Copy" again a few seconds later;
  one click on a line still selects it whole.
* **Settings**: "Copy the address for a pop-up dictionary" at the bottom, after "Reset settings"'s
  line, in its look; its line under it, the link "More ways to use Ordpar" to `/more/#popup`, in
  the reset line's style; a click copies the same address as `/more/` and says "Address copied.".
* **The clipboard refused** (and the browser's copy command): `/more/`'s button selects its line
  and keeps saying "Copy"; Settings shows the address as a line, selected, and says nothing.

`ORDPAR_TEST_SHOTS=<folder>` saves /more/'s Definer section and Settings' bottom, before and after
a click (and refused), and for the light views one article with `defs=en&theme=dark` beside the
same without. Skipped without Edge, bun or a build.
"""
import json
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
# site decisions 152: a second rule, the headword's Norwegian-only icon in the pop-up
CSS = (".ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; } "
       ".ordpar-nbhw { display: inline-flex !important; }")
NOTE = ("An address that opens Ordpar with your current settings, for a pop-up dictionary such as "
        "Definer. How to set one up: More ways to use Ordpar.")


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_settingsaddr146: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_TEST_SHOTS")
    if shots:
        os.makedirs(shots, exist_ok=True)
    for name, view in VIEWS.items():
        args = dict(view)
        args["pair"] = not view["dark"]
        if shots:
            args["shots"] = {"dir": shots.replace("\\", "/"), "prefix": name}
        R[name] = SITE.check("settingsaddr146.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class SettingsAddress(unittest.TestCase):

    def test_a_the_visit(self):
        for name, r in R.items():
            with self.subTest(view=name):
                dark = VIEWS[name]["dark"]
                v = r["visit"]
                self.assertEqual(v["path"], "/bm-en/hus/", v)
                self.assertEqual(v["hash"], "", v)
                self.assertNotIn("defs=", v["href"])
                self.assertEqual(v["night"], not dark, v)            # the address's theme, not the saved
                self.assertTrue(v["defsEn"] and v["miniEn"], v)
                self.assertFalse(v["defsNo"], v)
                self.assertTrue(v["exlimit2"], v)                    # a saved setting it does not name
                self.assertGreater(v["pairs"], 0, v)
                self.assertEqual(v["nbShown"], 0, v)                 # the English alone
                self.assertGreater(v["enShown"], 0, v)
                self.assertEqual(v["miniNb"], "none", v)
                self.assertEqual(json.loads(v["visit"]), {"defs": "en", "theme": "light" if dark else "dark",
                                                          "mini": "en"})
                self.assertEqual(json.loads(v["stored"]), json.loads(r["before"]), "localStorage's settings unchanged")
                hist = json.loads(v["history"] or "[]")
                self.assertTrue(hist and hist[0]["q"] == "hus", hist)
                self.assertNotIn("defs", v["history"] or "")
                self.assertNotIn("theme", v["history"] or "")

    def test_b_onward(self):
        for name, r in R.items():
            with self.subTest(view=name):
                dark = VIEWS[name]["dark"]
                o = r["onward"]
                self.assertIn("article", o, o)
                self.assertRegex(o["article"]["path"], r"^/bm-en/\d+/$")
                self.assertIn("headword", o, o)
                self.assertRegex(o["headword"]["path"], r"^/bm-en/\d+/$")
                self.assertNotEqual(o["headword"]["path"], o["article"]["path"])
                self.assertEqual(o["mini"]["look"]["nbShown"], 0, o["mini"])
                for page in (o["article"], o["headword"]):
                    self.assertEqual(page["night"], not dark, page)
                    self.assertTrue(page["defsEn"] and page["miniEn"], page)
                    self.assertEqual(page["nbShown"], 0, page)
                self.assertEqual(json.loads(o["stored"]), json.loads(r["before"]))
                self.assertEqual(json.loads(r["final"]), json.loads(r["before"]))

    def test_c_a_fresh_tab(self):
        for name, r in R.items():
            with self.subTest(view=name):
                f = r["fresh"]
                self.assertEqual(f["path"], "/bm-en/hus/")
                self.assertIsNone(f["visit"])
                self.assertEqual(f["night"], VIEWS[name]["dark"], f)
                self.assertTrue(f["defsNo"], f)
                self.assertFalse(f["defsEn"] or f["miniEn"], f)

    def test_d_settings_and_more_inside_a_visit(self):
        for name, r in R.items():
            with self.subTest(view=name):
                s = r["settingsVisit"]
                self.assertEqual(s["night"], VIEWS[name]["dark"], s)
                self.assertEqual(s["defs"], "no", s)
                self.assertEqual(s["theme"], "dark" if VIEWS[name]["dark"] else "light", s)
                self.assertFalse(s["defsClass"], s)
                self.assertIsNone(s["visitApplied"], s)
                m = r["moreVisit"]
                self.assertEqual(m["night"], not VIEWS[name]["dark"], m)   # the page follows the visit ...
                self.assertEqual(m["line"], r["expect"], m)                # ... its copy the saved settings
                self.assertEqual(m["hash"], "", m)

    def test_e_more(self):
        for name, r in R.items():
            with self.subTest(view=name):
                m = r["more"]
                self.assertEqual(m["lines"], [r["expect"], CSS])
                self.assertTrue(m["popupMarked"])
                self.assertEqual(m["buttons"], ["Copy", "Copy"])
                self.assertEqual(m["looks"][0], m["looks"][1])             # one style
                self.assertEqual(m["beside"], [True, True], m)
                self.assertEqual(m["night"], VIEWS[name]["dark"])
                for i, c in enumerate(m["clicks"]):
                    self.assertEqual(c["label"], "Copied", c)
                    self.assertEqual(c["clip"], m["lines"][i], c)
                    self.assertEqual(c["later"], "Copy", c)
                self.assertEqual([x.strip() for x in m["select"]], m["lines"])

    def test_f_settings(self):
        for name, r in R.items():
            with self.subTest(view=name):
                s = r["settings"]
                self.assertEqual(s["button"], "Copy the address for a pop-up dictionary")
                self.assertEqual(s["note"], NOTE)
                self.assertEqual(s["link"], ["More ways to use Ordpar", "/more/#popup"])
                self.assertTrue(s["inStored"])
                self.assertEqual(s["look"], s["resetLook"])
                self.assertEqual(s["noteFont"], s["resetNoteFont"])
                self.assertEqual(s["order"], sorted(s["order"]), s)          # Reset's line, the button, its line
                self.assertTrue(s["lineHidden"])
                self.assertEqual(s["night"], VIEWS[name]["dark"])
                a = s["after"]
                self.assertEqual(a["clip"], r["expect"], a)
                self.assertEqual(a["clip"], r["more"]["lines"][0])          # the same address as /more/
                self.assertEqual(a["status"], "Address copied.", a)
                self.assertTrue(a["lineHidden"], a)

    def test_g_the_clipboard_refused(self):
        for name, r in R.items():
            with self.subTest(view=name):
                f = r["fallback"]
                self.assertEqual(f["settings"]["status"], "", f)
                self.assertFalse(f["settings"]["lineHidden"], f)
                self.assertEqual(f["settings"]["line"], r["expect"])
                self.assertEqual(f["settings"]["selected"].strip(), r["expect"], f)
                self.assertEqual(f["more"]["label"], "Copy", f)
                self.assertEqual(f["more"]["selected"].strip(), f["more"]["line"], f)

    def test_h_the_pair(self):
        for name, r in R.items():
            if VIEWS[name]["dark"]:
                continue
            with self.subTest(view=name):
                p = r["pair"]
                self.assertFalse(p["without"]["night"])
                self.assertTrue(p["without"]["defsNo"])
                self.assertTrue(p["with"]["night"])
                self.assertTrue(p["with"]["defsEn"])
                self.assertEqual(p["with"]["nbShown"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
