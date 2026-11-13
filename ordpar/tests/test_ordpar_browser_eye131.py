"""Site-review decisions 131 (Robin, 2026-10-25): the deck's eye on the site, as a setting off by
default (headless Edge, `browser/eye131.js`), on a computer (clicked) and a phone (tapped):

* **Settings**: the setting "An eye button for the examples' English" drawn right after Examples,
  its choices Off then On, Off checked with nothing stored, with its "?".
* **Off** (the default): no eye anywhere — an article page, a word page, full results — no button by
  its name, nothing in the accessibility tree.
* **On** (in place, then stored and after a reload): on *hus* the eye is the first thing in the
  article's head, on the headword's line at its right; a `<button type="button">` named "Hide the
  examples' English" (its tooltip too) with `aria-pressed="false"`, a button with that name and state
  in the accessibility tree; its tap area at least 44 x 44 px (points 21 px out each way hit it).
  Pressed: `aria-pressed="true"`, every example's English hidden and each one's "Show English" cue
  shown; one cue opens one; pressed again: every English shown, no cue. Enter and Space press it.
* **Night and light**: the outline #c4bcbd by day, #656161 by night; pressed, the fill is the accent
  (`--ordpar-accent`) in both.
* **examples = no**: the article opens with the English hidden and the eye pressed; a press shows
  every example's English, a second hides it again; back to both, the article shows all, unpressed.
* **Every article shown whole**: a word page of one article (*vindu*), a one-article search answered
  in place on the search page, each full result of *fange* (list view off: an eye on every result
  with an example in English; a press hides only its own article's), an article opened in a list
  row (none on the row's button).
* **A mini** (*hjem* I opened on *hus*): no eye in it, and the article's eye pressed leaves the
  mini's English shown while the article's goes.
* **Off again in place**: every eye gone, the article back to the Examples setting.

`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before 131's deploy: fails —
no such setting, no eye). `ORDPAR_TEST_SHOTS=<folder>` also saves the head of *hus* pressed and
not, light and night, at each width. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

NAME = "Hide the examples' English"
SITE = None
RESULTS = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_eye131: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_TEST_SHOTS")
    for mobile in (False, True):
        a = {"mobile": mobile}
        if shots:
            a["shots"] = {"dir": shots.replace("\\", "/"), "prefix": "phone-390" if mobile else "computer-1280"}
        RESULTS["phone" if mobile else "computer"] = SITE.check("eye131.js", a)["cases"]


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Eye(unittest.TestCase):

    def test_a_the_setting_on_the_settings_page(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                s = c["settings"]
                self.assertEqual(s["after"], "exeye", s)
                self.assertEqual(s["title"], "An eye button for the examples' English", s)
                self.assertEqual(s["choices"], ["Off", "On"], s)
                self.assertEqual(s["checked"], ["off"], s)
                self.assertTrue(s["shown"] and s["hint"], s)

    def test_b_off_nothing_anywhere(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                for k in ("offArticle", "offWord", "offFull"):
                    self.assertEqual(c[k], {"eyes": 0, "buttons": 0, "cls": False}, (k, c[k]))
                self.assertEqual(c["offAx"], 0)

    def test_c_on_the_eye_beside_the_headword(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                self.assertEqual(c["stored"], "on")
                for k in ("onInPlace", "on"):
                    a = c[k]
                    e = a["eye"]
                    self.assertIsNotNone(e, (k, a))
                    self.assertEqual((e["tag"], e["type"], e["label"], e["title"], e["pressed"]),
                                     ("BUTTON", "button", NAME, NAME, "false"), (k, e))
                    self.assertTrue(e["visible"] and e["first"] and e["sameLine"], (k, e))
                    self.assertLess(e["right"], 40, (k, e))        # at the article's right
                    self.assertEqual(a["eyes"], 1)
                    self.assertGreater(a["withEn"], 3)
                    self.assertEqual(a["enShown"], a["withEn"], (k, a))
                    self.assertEqual(a["cuesShown"], 0, (k, a))
                self.assertEqual(c["ax"], [{"role": "button", "pressed": "false"}])
                self.assertEqual(c["area"], [True, True, True, True])

    def test_d_pressed_hides_every_example_then_shows_them(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                n = c["on"]["withEn"]
                self.assertEqual((c["pressed"]["eye"]["pressed"], c["pressed"]["enShown"], c["pressed"]["cuesShown"]),
                                 ("true", 0, n), c["pressed"])
                self.assertEqual(c["axPressed"], ["true"])
                self.assertEqual((c["oneRevealed"]["enShown"], c["oneRevealed"]["cuesShown"]), (1, n - 1))
                self.assertEqual((c["again"]["eye"]["pressed"], c["again"]["enShown"], c["again"]["cuesShown"]),
                                 ("false", n, 0))
                self.assertEqual((c["enter"]["eye"]["pressed"], c["enter"]["enShown"]), ("true", 0))
                self.assertEqual((c["space"]["eye"]["pressed"], c["space"]["enShown"]), ("false", n))

    def test_e_light_and_night(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                self.assertEqual(c["on"]["eye"]["border"], "rgb(196, 188, 189)")       # #c4bcbd
                self.assertEqual(c["night"]["eye"]["border"], "rgb(101, 97, 97)")      # #656161
                for k in ("pressed", "nightPressed"):
                    e = c[k]["eye"]
                    self.assertEqual(e["pressed"], "true", k)
                    self.assertNotEqual(e["bg"], "rgba(0, 0, 0, 0)", (k, e))
                    self.assertEqual(e["bg"], e["border"], (k, e))                    # filled with the accent
                self.assertNotEqual(c["pressed"]["eye"]["bg"], c["nightPressed"]["eye"]["bg"])
                self.assertEqual(c["nightPressed"]["enShown"], 0)

    def test_f_examples_no(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                n = c["on"]["withEn"]
                self.assertEqual((c["noStart"]["eye"]["pressed"], c["noStart"]["enShown"], c["noStart"]["cuesShown"]),
                                 ("true", 0, n), c["noStart"])
                self.assertEqual((c["noShown"]["eye"]["pressed"], c["noShown"]["enShown"], c["noShown"]["cuesShown"]),
                                 ("false", n, 0), c["noShown"])
                self.assertEqual((c["noHidden"]["eye"]["pressed"], c["noHidden"]["enShown"]), ("true", 0))
                self.assertEqual((c["bothAgain"]["eye"]["pressed"], c["bothAgain"]["enShown"]), ("false", n))

    def test_g_every_article_shown_whole(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                for k in ("word", "search"):
                    a = c[k]
                    self.assertIsNotNone(a and a["eye"], (k, a))
                    self.assertEqual((a["eye"]["pressed"], a["enShown"]), ("false", a["withEn"]), (k, a))
                self.assertEqual(c["searchPath"], "/bm-en/vindu/")
                self.assertEqual((c["wordPressed"]["eye"]["pressed"], c["wordPressed"]["enShown"]), ("true", 0))
                full = [r for r in c["full"] if r]
                self.assertGreater(len(full), 1)
                for r in full:
                    self.assertEqual(r["eyes"], 1 if r["withEn"] else 0, r)
                self.assertEqual((c["fullFirst"]["eye"]["pressed"], c["fullFirst"]["enShown"]), ("true", 0))
                o = c["fullOther"]
                self.assertIsNotNone(o, "fange: a second result with examples in English")
                self.assertEqual((o["eye"]["pressed"], o["enShown"]), ("false", o["withEn"]), o)
                self.assertEqual(c["rowButtons"], 0)
                self.assertEqual((c["row"]["eye"]["pressed"], c["row"]["enShown"]), ("false", c["row"]["withEn"]))
                self.assertEqual((c["rowPressed"]["eye"]["pressed"], c["rowPressed"]["enShown"]), ("true", 0))

    def test_h_never_in_a_mini(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                self.assertTrue(c["miniOpened"])
                m, after = c["mini"], c["miniAfter"]
                self.assertEqual(m["eyes"], 0, m)
                self.assertGreater(m["en"], 0, m)
                self.assertEqual(after["eyes"], 0)
                self.assertEqual(after["enShown"], m["enShown"], (m, after))
                self.assertEqual((c["miniArticle"]["eye"]["pressed"], c["miniArticle"]["enShown"]), ("true", 0))

    def test_i_off_again_in_place(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                self.assertEqual(c["offAgain"], {"eyes": 0, "buttons": 0, "cls": False})
                a = c["offAgainArticle"]
                self.assertEqual((a["eyes"], a["enShown"], a["cuesShown"]), (0, a["withEn"], 0), a)


if __name__ == "__main__":
    unittest.main(verbosity=2)
