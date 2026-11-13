"""Site decisions 136 (Robin, 2026-10-26): the presets on the settings page, in the browser (headless
Edge).

Through `browser/presets136.js`, at 1280 px (clicked) and 390 px (a phone, tapped), in a fresh
browser context:

* **the box** — "Presets" above the first section, its line in the page's intro style, four buttons
  (Default, English emphasized, Concise, For learners; the second since site decisions 174,
  2026-11-07) of the page's own button class, inside the window; the line
  under "Reset settings", right under its two buttons;
* **what each does** (site decisions 161) — one "?" after the heading, named "About the presets"
  (the section named by the title alone): pressed, a line per preset in the ruled words and "More
  about the presets in Help" to `/help/#settings`, inside the window; a second press closes it;
* **a reader on the defaults before 174** (`emph` en and `formulas` en stored, nothing else): English
  emphasized pressed, and nothing stored a fresh Default (174);
* **each preset pressed** (Concise, Default, English emphasized, For learners, Concise, after a dark
  theme was chosen) —
  every Article setting stored as the preset's full set (`test_ordpar_presets136.full`), that preset
  alone pressed, the status line "Article settings set to <name>.", the theme still dark, every radio
  and the drop-down in step; Default after Concise brings every Article setting back to its default;
* **the pressed look** — filled with the accent as the page's primary button, the others not;
* **not locked** — one Article setting changed afterwards (Definitions back to both, by its radio): no
  preset pressed, the rest of Concise kept; **a reload** keeps For learners pressed; **another tab** (a
  same-origin frame changing `emph`) leaves none pressed;
* **an article after Concise** — *gå* (21740, translated, 15 examples under its first sense): no
  Norwegian definition line shows, and no example list shows more than two;
* **`/help/#settings`** — the section's heading, inside the window; and the section's link
  `/settings/#article` lands on the Article section (drawn by the script, then scrolled to).

`ORDPAR_TEST_SHOTS` names a folder for the pictures (the page's top with each preset pressed, light and
dark; the Help section). `ORDPAR_TEST_BASE` points it at another copy; a new feature, so ordpar.no before
136 simply has no presets. Skipped without Edge, bun or a build. The table and the words are pinned in
`test_ordpar_presets136.py`.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "browser"))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import test_ordpar_presets136 as P  # noqa: E402

GA = 21740                      # gå: 15 examples under its first sense
FULL = {p["id"]: P.full(p["values"]) for p in P.presets_table()}
DEFAULTS = FULL["default"]
KEYS = sorted(DEFAULTS)
NAMES = {"default": "Default", "english": "English emphasized", "concise": "Concise", "learners": "For learners"}

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_presets136: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_TEST_SHOTS")
    for w in (1280, 390):
        a = {"w": w, "mobile": w == 390, "keys": KEYS, "id": GA}
        if shots:
            a["shots"] = {"dir": shots.replace("\\", "/"), "prefix": "presets136-%d" % w}
        RESULT[w] = SITE.check("presets136.js", a)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Presets(unittest.TestCase):

    def test_a_the_box(self):
        for w, r in RESULT.items():
            where = "at %d px on %s" % (w, r["base"])
            L = r["layout"]
            self.assertTrue(L["present"], where)
            self.assertTrue(L["beforeSections"], where)
            self.assertEqual(L["heading"], "Presets", where)
            self.assertEqual(L["intro"], P.WORDS["settings.presets.intro"], where)
            self.assertIn("ordpar-settings-intro", L["introCls"].split(), where)
            self.assertIn("ordpar-note", L["introCls"].split(), where)
            self.assertEqual(L["labels"], ["Default", "English emphasized", "Concise", "For learners"], where)   # 174
            for c in L["cls"]:
                self.assertIn("ordpar-button", c.split(), where)
            self.assertEqual(L["named"], "presets-title", where)       # the title, not the "?"
            self.assertTrue(L["hint"], where)                           # decisions 161
            h = r["hint"]
            self.assertTrue(h["open"], (where, h))
            self.assertEqual((h["expanded"], h["label"]), ("true", "About the presets"), where)
            self.assertEqual([x["name"] for x in h["lines"]],
                             ["Default:", "English emphasized:", "Concise:", "For learners:"], where)   # 174
            for x, pid in zip(h["lines"], ("default", "english", "concise", "learners")):
                self.assertIn(P.STRINGS["settings.presets.%s.note" % pid], x["text"], where)
            self.assertEqual(h["link"], {"text": "More about the presets in Help", "href": "/help/#settings"}, where)
            self.assertTrue(h["inside"], where)
            self.assertLessEqual(h["docWidth"], L["vw"], where)
            self.assertTrue(h["closed"], where)
            self.assertTrue(L["inside"], where)
            self.assertLessEqual(L["docWidth"], L["vw"], where)
            n = L["resetNote"]
            self.assertTrue(n, "no line under Reset " + where)
            self.assertEqual(n["text"], P.WORDS["settings.resetNote"], where)
            self.assertIn("ordpar-note", n["cls"].split(), where)
            self.assertTrue(n["afterButtons"], where)

    def test_b_fresh_is_default(self):
        for w, r in RESULT.items():
            self.assertEqual(r["fresh"]["pressed"], ["default"], w)
            self.assertEqual(r["fresh"]["effective"], DEFAULTS, w)
            # site decisions 174: the new defaults; the old ones, stored, are English emphasized
            self.assertEqual((DEFAULTS["emph"], DEFAULTS["formulas"]), ("no", "both"))
            self.assertEqual(r["oldDefaults"]["pressed"], ["english"], w)
            self.assertEqual(r["oldDefaults"]["effective"], FULL["english"], w)
            self.assertTrue(r["oldDefaults"]["radiosInStep"], w)

    def test_c_each_preset_pressed(self):
        for w, r in RESULT.items():
            self.assertEqual(r["darkChosen"]["theme"], "dark")
            self.assertEqual([s["preset"] for s in r["steps"]], ["concise", "default", "english", "learners", "concise"])
            for s in r["steps"]:
                where = "%s at %d px" % (s["preset"], w)
                self.assertEqual(s["stored"], FULL[s["preset"]], where)
                self.assertEqual(s["effective"], FULL[s["preset"]], where)
                self.assertEqual(s["pressed"], [s["preset"]], where)
                self.assertEqual(s["status"], "Article settings set to %s." % NAMES[s["preset"]], where)
                self.assertEqual(s["theme"], "dark", where)
                self.assertTrue(s["night"], where)
                self.assertTrue(s["radiosInStep"], where)
            # Default after Concise: every Article setting back to its default
            self.assertEqual(r["steps"][1]["effective"], DEFAULTS)

    def test_d_the_pressed_look(self):
        for w, r in RESULT.items():
            L = r["look"]
            self.assertEqual(L["pressed"]["bg"], L["primary"]["bg"], w)
            self.assertEqual(L["pressed"]["fg"], L["primary"]["fg"], w)
            self.assertNotEqual(L["other"]["bg"], L["primary"]["bg"], w)

    def test_e_nothing_locked(self):
        for w, r in RESULT.items():
            c = r["changed"]
            self.assertEqual(c["pressed"], [], w)
            want = dict(FULL["concise"], defs="both")
            self.assertEqual(c["effective"], want, w)
            self.assertEqual(r["learners"]["pressed"], ["learners"], w)
            self.assertEqual(r["reloaded"]["pressed"], ["learners"], w)
            self.assertEqual(r["reloaded"]["effective"], FULL["learners"], w)
            self.assertEqual(r["otherTab"]["pressed"], [], w)
            self.assertEqual(r["otherTab"]["effective"]["emph"], "en", w)
            self.assertTrue(r["otherTab"]["radiosInStep"], w)

    def test_f_an_article_after_concise(self):
        for w, r in RESULT.items():
            self.assertEqual(r["beforeArticle"]["pressed"], ["concise"], w)
            a = r["article"]
            where = "gå at %d px: %s" % (w, json.dumps(a))
            self.assertGreater(a["pairs"], 5, where)
            self.assertEqual(a["nbShown"], 0, where)
            self.assertGreater(a["lists"], 3, where)
            self.assertGreater(a["maxItems"], 2, where)
            self.assertLessEqual(a["maxShown"], 2, where)
            self.assertEqual(a["maxShown"], 2, where)

    def test_g_help(self):
        for w, r in RESULT.items():
            a = r["articleLink"]
            self.assertTrue(a, "no #article on /settings/ at %d px" % w)
            self.assertEqual(a["tag"], "SECTION", w)
            self.assertGreater(a["scrollY"], 0, w)
            self.assertLess(abs(a["top"]), 40, (w, a))
            h = r["help"]
            self.assertTrue(h, w)
            self.assertEqual((h["tag"], h["text"]), ("H2", "Settings"), w)
            self.assertLessEqual(h["docWidth"], h["vw"], w)


if __name__ == "__main__":
    unittest.main()
