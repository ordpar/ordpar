"""Site decisions 185 (Robin, 2026-11-12): the linked word's first Norwegian definition as a hover
choice everywhere, in the browser (headless Edge, a computer; `browser/hovernb185.js`):

* **The fault: the Norwegian hover follows the Loading setting.** Under "When its link is clicked"
  (`minifetch` = click), resting on a link asks for no `snip/` file before a press — in the
  Norwegian-only view with `nbhover` = nbdef, and under `peek` = nb; no Norwegian peek is shown
  then. A file the page already has (loaded as a search would) still gives the peek. Fails on the
  build before 185 (`ORDPAR_TEST_OVERLAY` unset, `ordpar/out/` as deployed: one `snip/` request on
  the rest).
* **`peek` = nb** ("Its first Norwegian definition"): a rest on a translated link and on a link to an
  untranslated word (which has no English peek) shows the first Norwegian definition (`ordpar-nbpk`,
  `lang="nb"`) and no English peek, in an article, in a small article and in the search page's
  article; on an English partner word too (Definitions on English), and on a word page.
* **One style**: each of those Norwegian peeks has the computed look (font, size, weight, wrapping,
  width cap, colours, border, shadow) of the Norwegian-only view's own.
* **`peek` = off** ("Nothing"): no peek; **the default** ("Its translation"): the English peek, no
  Norwegian one.
* **The address** (146): `#peek=nb` gives the class and the Norwegian peek, for the visit, nothing
  saved.
* **The settings page**: the title "When the pointer rests on a linked word", the three choices in
  order with their words, "Nothing" keeping its note; choosing the second stores `nb` and sets the
  class.

The static half (the table, the strings, the head script, the presets): `test_ordpar_hovernb185.py`.
`ORDPAR_TEST_OVERLAY` lays the working tree's scripts and shell pages over the build. Skipped
without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

#: hus; elastisk with its link to the untranslated tøyelig and to the translated smidig; elastikk,
#: whose link to elastisk opens it as a small article; the search for elastisk
ARGS = dict(hus=24627, untr=dict(page=12237, href="/bm-en/63472/", tr="/bm-en/54808/"),
            mini=dict(page=12236, id=12237), search="elastisk", word="hus")
SITE = None
R = {}
SKIP = harness.skip_reason()
WORDS = [["on", "Its translation"], ["nb", "Its first Norwegian definition"], ["off", "Nothing"]]


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_hovernb185: skipped —", SKIP)
        return
    SITE = harness.Site()
    R.update(SITE.check("hovernb185.js", ARGS, timeout=240)["R"])


def tearDownModule():
    if SITE:
        SITE.close()


def nb_only(case):
    """The link's peeks shown: exactly one, the Norwegian definition."""
    peeks = case.get("peeks") or []
    return len(peeks) == 1 and "ordpar-nbpk" in peeks[0][0] and peeks[0][1] == "nb" and bool(peeks[0][2])


@unittest.skipIf(SKIP, SKIP or "")
class HoverNb(unittest.TestCase):

    def test_a_click_fetches_no_snip_before_a_press(self):
        for name in ("fault", "faultpeek"):
            with self.subTest(name):
                c = R[name]
                self.assertIn("ordpar-nbo-hovnb", c["cls"].split(), c["cls"])
                self.assertEqual(c["atLoad"], [], c)
                self.assertTrue(c["rest"]["found"], c)
                self.assertEqual(c["rest"]["snips"], [], c["rest"])          # nothing before a press
                self.assertEqual(c["rest"]["peeks"], [], c["rest"])

    def test_b_a_file_already_loaded_gives_the_peek(self):
        for name in ("fault", "faultpeek"):
            with self.subTest(name):
                c = R[name]
                self.assertTrue(c["loadedKey"], c)
                self.assertTrue(nb_only(c["loaded"]), c["loaded"])

    def test_c_nb_in_an_article(self):
        nb = R["nb"]
        self.assertIn("ordpar-nbo-hovnb", nb["cls"].split())
        self.assertNotIn("ordpar-peek-off", nb["cls"].split())
        for name in ("hus", "untr", "tr", "partner"):
            with self.subTest(name):
                self.assertTrue(nb[name]["found"], nb[name])
                self.assertTrue(nb_only(nb[name]), nb[name])
        self.assertFalse(nb["untrHadPeek"])             # the untranslated word has no English peek
        self.assertTrue(nb["partner"]["xen"], nb["partner"])

    def test_d_nb_in_a_small_article(self):
        m = R["nb"]["mini"]
        self.assertTrue(m["opened"], m)
        for name in ("untr", "tr"):
            with self.subTest(name):
                self.assertTrue(m[name]["found"], m[name])
                self.assertTrue(nb_only(m[name]), m[name])

    def test_e_nb_on_the_search_page(self):
        s = R["nb"]["search"]
        for name in ("untr", "tr"):
            with self.subTest(name):
                self.assertTrue(s[name]["found"], s[name])
                self.assertTrue(nb_only(s[name]), s[name])

    def test_e2_nb_on_a_word_page(self):
        w = R["nb"]["word"]
        self.assertTrue(w["found"], w)
        self.assertTrue(nb_only(w), w)

    def test_e3_one_style_everywhere(self):
        """Every Norwegian peek looks as the Norwegian-only view's own (its computed font, size,
        weight, wrapping, width cap, colours, border and shadow)."""
        ref = R["nbo"]
        self.assertTrue(nb_only(ref), ref)
        nb = R["nb"]
        places = {"article": nb["hus"], "untranslated": nb["untr"], "translated": nb["tr"],
                  "partner": nb["partner"], "word page": nb["word"], "small article": nb["mini"]["untr"],
                  "small article, translated": nb["mini"]["tr"], "search": nb["search"]["untr"],
                  "search, translated": nb["search"]["tr"], "address": R["address"],
                  "click, a file loaded": R["faultpeek"]["loaded"]}
        for name, case in places.items():
            with self.subTest(name):
                self.assertEqual(case.get("look"), ref["look"])

    def test_f_nothing_and_the_default(self):
        off = R["off"]
        self.assertTrue(off["found"], off)
        self.assertEqual((off["peeks"], off["shown"]), ([], 0), off)
        d = R["def"]
        self.assertTrue(d["found"], d)
        self.assertEqual(len(d["peeks"]), 1, d)
        self.assertNotIn("ordpar-nbpk", d["peeks"][0][0], d)
        self.assertEqual(d["peeks"][0][1], "en", d)
        self.assertFalse({"ordpar-nbo-hovnb", "ordpar-peek-off"} & set(d["cls"].split()), d["cls"])

    def test_g_the_address(self):
        a = R["address"]
        self.assertIn("ordpar-nbo-hovnb", a["cls"].split())
        self.assertEqual(a["visit"], {"peek": "nb"})
        self.assertIsNone(a["saved"])
        self.assertTrue(nb_only(a), a)

    def test_h_the_settings_page(self):
        s = R["settings"]
        self.assertEqual(s["title"], "When the pointer rests on a linked word")
        self.assertEqual([c[:2] for c in s["choices"]], WORDS)
        self.assertEqual([c[2] for c in s["choices"]], [True, False, False])   # the default first
        self.assertEqual(s["notes"][2], "Fewer pop-ups while you read. A click still opens the link.")
        self.assertEqual(s["stored"], "nb")
        self.assertIn("ordpar-nbo-hovnb", s["cls"].split())
        self.assertEqual(s["pressed"], [])              # no preset chooses it


if __name__ == "__main__":
    unittest.main()
