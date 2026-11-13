"""Site-review decisions 126 (Robin, 2026-10-25): the settings' words on the page (headless Edge).

Through `browser/settingswords126.js`, on the settings page at 390 px (a phone's width) and at 1280,
with the default settings:

* **the line under "Small articles"** — right under the heading, the approved words, in the page's
  explanatory style (the same font size and colour as "Changes apply at once …", `settings.applied`),
  inside the window; the subsection a group named "Small articles" and described by the line, in
  Chrome's accessibility tree as a screen reader gets it;
* **the "?" texts the settings gained** — emphasis, formula lines, list view, accent colour, and
  "How much of the article it shows": each has its "?", a real click opens a box holding the new text,
  inside the window; the accent colour's button is named "About this setting: Accent colour";
* **the new notes** — the small article's Language ("Same as the article", "English") and the list
  view's "Only when there are several articles": in their setting's box, and kept as their radio's
  description.

`ORDPAR_TEST_BASE` points it at another copy (ordpar.no before 126, snapshot 980a10198513: fails — no
line under the heading, no "?" on the list view, the new texts and notes in none of the boxes). `ORDPAR_TEST_SHOTS` names a folder for the pictures of the
subsection and of an open "?". Skipped without Edge, bun or a build. The words themselves are pinned in
`test_ordpar_settingswords126.py`.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(ROOT, "ordpar", "site", "strings", "en.json"), encoding="utf-8") as f:
    S = json.load(f)

#: the settings that gained a "?" (126) and the text each box must hold
GAINED = {
    "emph": S["settings.emph.hint"],
    "formulas": S["settings.formulas.hint"],
    "listview": S["settings.listview.hint"],
    "colour": S["settings.colour.hint"],
    "minicontent": S["settings.minicontent.hint"],
}
#: the new notes: their setting and the radio's note id
NOTES = {
    "settings.mini.article.note": ("mini", "ordpar-mini-article-note"),
    "settings.mini.en.note": ("mini", "ordpar-mini-en-note"),
    "settings.listview.multi.note": ("listview", "ordpar-listview-multi-note"),
}
INTRO = ("The box that opens on the page when you click a word linked to another article. It shows the "
         "word's senses only; click its headword for the whole article.")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_settingswords126: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_TEST_SHOTS")
    keys = list(GAINED) + ["mini"]
    for w in (390, 1280):
        a = {"w": w, "keys": keys}
        if shots:
            a["shots"] = {"dir": shots.replace("\\", "/"), "prefix": "settings126-%d" % w}
        RESULT[w] = SITE.check("settingswords126.js", a)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class SettingsWords(unittest.TestCase):

    def test_a_the_line_under_small_articles(self):
        for w, r in RESULT.items():
            where = "at %d px on %s" % (w, r["base"])
            self.assertEqual(r["heading"], "Small articles", where)
            i = r["intro"]
            self.assertTrue(i, "no line under Small articles " + where)
            self.assertEqual(i["text"], INTRO, where)
            self.assertIn("ordpar-note", i["cls"].split(), where)
            self.assertEqual((i["size"], i["colour"]), (r["applied"]["size"], r["applied"]["colour"]),
                             "not in the page's note style " + where)
            self.assertGreater(i["h"], 0, where)
            self.assertGreaterEqual(i["l"], 0, where)
            self.assertLessEqual(i["r"], r["vw"], where)
            self.assertLessEqual(r["docWidth"], r["vw"], where)

    def test_b_a_group_described_by_the_line(self):
        for w, r in RESULT.items():
            where = "at %d px on %s" % (w, r["base"])
            self.assertTrue(r["intro"], where)
            self.assertEqual((r["intro"]["role"], r["intro"]["labelledby"], r["intro"]["describedby"]),
                             ("group", "article-mini-title", r["intro"]["id"]), where)
            self.assertEqual(r["ax"], {"role": "group", "name": "Small articles", "description": INTRO}, where)

    def test_c_the_new_question_marks(self):
        for w, r in RESULT.items():
            for key, text in GAINED.items():
                h = r["hints"][key]
                where = "%s at %d px on %s" % (key, w, r["base"])
                self.assertTrue(h["button"], "no \"?\" on " + where)
                self.assertTrue(h["open"], "the box did not open: " + where)
                self.assertIn(text, h["text"], where)
                self.assertTrue(h["inside"], "the box leaves the window: " + where)
            self.assertEqual(r["hints"]["colour"]["label"], "About this setting: Accent colour")
            self.assertEqual(r["hints"]["minicontent"]["label"],
                             "About this setting: Small articles, How much of the article it shows")

    def test_d_the_new_notes(self):
        for w, r in RESULT.items():
            for skey, (setting, nid) in NOTES.items():
                where = "%s at %d px on %s" % (skey, w, r["base"])
                self.assertIn(S[skey], r["hints"][setting].get("text", ""), where)
                self.assertEqual(r["notes"][nid], S[skey], where)


if __name__ == "__main__":
    unittest.main()
