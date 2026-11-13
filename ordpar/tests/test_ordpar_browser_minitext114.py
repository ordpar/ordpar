"""Site-review decisions 114 (Robin, 2026-10-24): the mini's text sizes, and their setting (headless Edge).

Robin's pick from the style lab: the mini's header line 1.1rem (the bracket at the headword's size),
its gloss 1rem, semibold (600), upright, in the text colour; the body 1rem, the article's own size,
its parts' proportions unchanged. The setting `minitext` (Settings -> Article -> Small articles):
the new sizes, the default and first (107), or the sizes until then — the header 1.02rem, its
gloss and the body .92rem; the gloss semibold in both (the session's reading). Through
`browser/minitext114.js`, on a computer and a phone, light and dark, a real mini (*bosted*, 7136,
opened on *hus*, 24627), measured with the computed styles:

* the header line 17.6 px (16.32 with `smaller`), the gloss 16 px (14.72), weight 600 and upright
  in both, its colour the mini's text colour and the article's (#222 light, #d9d6d6 dark);
* the English line of the mini's first definition the size of the article's own (x 1), or .92 of
  it with `smaller`; the default (nothing stored) is `article`;
* a change made in place applies at once;
* the settings page: "Text size" under Small articles, after Spacing; "As the article" first and
  chosen, then "Smaller"; a "?" (the choice's line).

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build: fails — the header
16.32 px, the gloss 14.72 px regular, the body .92). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

HUS, BOSTED = 24627, 7136
VIEWPORTS = ("computer", "phone")
TEXT = {"light": "rgb(34, 34, 34)", "dark": "rgb(217, 214, 214)"}
SIZES = {"article": (17.6, 16.0, 1.0), "smaller": (16.32, 14.72, 0.92)}   # head, gloss, body x article

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_minitext114: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("minitext114.js", dict(mobile=vp == "phone", **{"from": HUS, "to": BOSTED}))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class MiniText(unittest.TestCase):

    def _case(self, vp, name):
        c = RESULT[vp]["cases"][name]
        self.assertTrue(c.get("opened"), "%s, %s: no mini opened on %s" % (vp, name, RESULT[vp]["base"]))
        return c

    def _sizes(self, vp, name, choice):
        c = self._case(vp, name)
        head, gloss, ratio = SIZES[choice]
        where = "%s, %s on %s: %s" % (vp, name, RESULT[vp]["base"], c)
        self.assertAlmostEqual(c["head"], head, delta=0.05, msg="header line: " + where)
        self.assertAlmostEqual(c["gloss"], gloss, delta=0.05, msg="gloss size: " + where)
        self.assertIsNotNone(c["def"], where)
        self.assertIsNotNone(c["articleDef"], where)
        self.assertAlmostEqual(c["def"] / c["articleDef"], ratio, delta=0.005, msg="body against the article: " + where)

    def test_a_the_sizes_each_choice(self):
        for vp in VIEWPORTS:
            for theme in ("light", "dark"):
                self._sizes(vp, theme + "-default", "article")
                self._sizes(vp, theme + "-article", "article")
                self._sizes(vp, theme + "-smaller", "smaller")

    def test_b_the_gloss_semibold_upright_text_colour(self):
        for vp in VIEWPORTS:
            for theme in ("light", "dark"):
                for choice in ("default", "article", "smaller"):
                    c = self._case(vp, theme + "-" + choice)
                    where = "%s, %s-%s on %s: %s" % (vp, theme, choice, RESULT[vp]["base"], c)
                    self.assertEqual(c["weight"], "600", where)
                    self.assertEqual(c["italic"], "normal", where)
                    self.assertEqual(c["colour"], TEXT[theme], where)
                    self.assertEqual(c["colour"], c["miniColour"], where)
                    self.assertEqual(c["colour"], c["articleColour"], where)
                    self.assertEqual("nightMode" in c["cls"], theme == "dark", where)

    def test_c_in_place(self):
        for vp in VIEWPORTS:
            self._sizes(vp, "inPlace", "smaller")

    def test_d_the_settings_page(self):
        for vp in VIEWPORTS:
            s = RESULT[vp]["settings"]
            where = "%s on %s: %s" % (vp, RESULT[vp]["base"], s)
            self.assertTrue(s["field"], where)
            self.assertEqual(s["title"], "Text size", where)
            self.assertEqual(s["sub"], "Small articles", where)
            self.assertEqual(s["after"][:2], ["minispacing", "minitext"], where)
            self.assertEqual(s["choices"], [["article", True, "As the article"], ["smaller", False, "Smaller"]], where)
            self.assertTrue(s["hint"], where)


if __name__ == "__main__":
    unittest.main()
