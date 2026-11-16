"""Site decisions 152 (Robin, 2026-10-30/31): Norwegian only, in the browser (headless Edge).

Through `browser/nbonly152.js`, on a computer (clicked) and a phone (tapped), storage cleared first:

* **Off, as before**: *hus* 24627 with the eye on shows its English, the eye and the header icon
  (beside Favourites and Settings on a computer, on the switch's row on a phone), not pressed.
* **The icon pressed**: the layer's classes, `nbonly` stored "on"; the ENGLISH SCAN of `<main>` finds
  no English from the dictionary's content on *hus*, *gå* 21740, *direkte* 10214, *heise* 22892 and
  *elastisk* 12237, in a small article opened from *hus*, on the search for *lys* (its rows and their
  form labels Norwegian), in the suggestions for *hus*, in History and in Favourites (an entry each);
  the word class and the inflection table's words Norwegian, the headings Norwegian too (152's
  follow-up); the eye hidden; remembered across a reload and a new page, the classes there when
  `<body>` is first made (before the first paint).
* **The English equivalents hidden**: the "Search English words" switch gone, the box Norwegian,
  Random word Norwegian, the stored direction ("en") untouched, and on a phone the icon still on the
  switch's row; shown again, the switch is back and on.
* **The rows' and hovers' choices**: rows on "nothing", no row line shown; hovers on "Norwegian
  definition" (a computer), a link's Norwegian peek and no English one; on "nothing" (the default),
  no peek.
* **The icon's setting off**: no icon.
* **Definer**: `#nbonly=on&q=hus` with `/more/`'s CSS line — the header hidden, the headword's icon
  shown and pressed; pressed again, the layer off for that pop-up, nothing saved, the visit "off".
* **The labels setting**: Norwegian with the layer off — the headings (Opphav, Betydning og bruk,
  Faste uttrykk) and the word class, the English definitions still shown.
* **The layer turns every label** (152's follow-up: the labels too become
  Norwegian with the Norwegian only setting turned on): `labels` stored "en" and the layer on, the
  headings ("Opphav", "Betydning og bruk"), "Vis bøyning" and every other label copy shown in
  Norwegian, no English copy shown, on *hus*, *gå* 21740, the word page *hus* and in a small article
  (in ordbokene's layout, its "Eksempel" heading);
  the layer off by the icon, English again and `labels` still "en" in storage. Fails on the live
  site before the follow-up (`ORDPAR_TEST_BASE=https://ordpar.no`: the headings English).
* **Back off by the icon**: the reader's own settings again, the English and the eye back.

The static half: `test_ordpar_nbonly152.py`. `ORDPAR_TEST_BASE` points it at another copy (the
site before 152: fails — no icon, no layer); `ORDPAR_TEST_OVERLAY` lays a scratch render over the
build. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

CSS = (".ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; } "
       ".ordpar-nbhw { display: inline-flex !important; }")
ARGS = dict(hus=24627, pages=[21740, 10214, 22892, 12237], search="lys", suggest="hus", css=CSS,
            go=21740, word="hus")
VIEWPORTS = ("computer", "phone")
SITE = None
RESULT = {}
SKIP = harness.skip_reason()
LAYER = {"ordpar-nbo", "ordpar-nbo-noeq", "ordpar-defs-no", "ordpar-examples-no", "ordpar-formulas-no",
         "ordpar-ety-no", "ordpar-peek-off"}


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_nbonly152: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("nbonly152.js", dict(ARGS, mobile=vp == "phone"))["R"]


def tearDownModule():
    if SITE:
        SITE.close()


def cls(state):
    return set((state.get("cls") or "").split())


def _first_english(vp, foot):
    """The foot's first English button: Copy link, but Share on a phone that has Share — site
    decisions 166's follow-up (Robin, 2026-11-05, as ordbokene): Copy link is not shown on a narrow
    screen where Share is."""
    return "Share" if vp == "phone" and "Share" in foot else "Copy link"


@unittest.skipIf(SKIP, SKIP or "")
class NorwegianOnly(unittest.TestCase):

    def each(self):
        for vp in VIEWPORTS:
            yield vp, RESULT[vp]

    def place(self, vp):
        return "ordpar-nbo-row" if vp == "phone" else "ordpar-nbo-nav"

    def test_a_off_as_before(self):
        for vp, R in self.each():
            off = R["off"]
            self.assertFalse({c for c in cls(off) if "nbo" in c}, vp)
            self.assertTrue(off["gloss"] and off["enDefs"] and off["eye"], (vp, off))
            self.assertEqual(len(off["icon"]), 1, (vp, off["icon"]))
            self.assertIn(self.place(vp), off["icon"][0][0], vp)
            self.assertEqual(off["icon"][0][1], "false", vp)

    def test_b_the_icon_switches_the_site(self):
        for vp, R in self.each():
            on = R["on"]
            self.assertTrue(R["pressed"], vp)
            self.assertTrue(LAYER <= cls(on), (vp, on["cls"]))
            self.assertEqual(on["stored"], "on", vp)
            self.assertEqual(on["icon"][0][1], "true", vp)
            self.assertEqual(on["scan"]["content"], [], (vp, on["scan"]))
            self.assertEqual((on["gloss"], on["enDefs"], on["eye"]), ([], 0, 0), vp)
            self.assertEqual(on["pos"], ["substantiv intetkjønn"], vp)
            self.assertIn("entall", on["table"], vp)
            self.assertNotIn("singular", on["table"], vp)
            self.assertIn("Opphav", on["h3"], vp)             # 152's follow-up: the layer turns them
            self.assertNotIn("Etymology", on["h3"], vp)

    def test_c_remembered_and_before_the_first_paint(self):
        for vp, R in self.each():
            self.assertTrue(LAYER <= set(R["reload"]["first"].split()), (vp, R["reload"]))
            for pid, page in R["pages"].items():
                self.assertTrue(LAYER <= cls(page), (vp, pid))
                self.assertEqual(page["scan"]["content"], [], (vp, pid, page["scan"]))

    def test_d_small_article_search_suggestions(self):
        for vp, R in self.each():
            self.assertTrue(R["mini"]["opened"], vp)
            self.assertEqual(R["mini"]["scan"]["content"], [], (vp, R["mini"]))
            s = R["search"]
            self.assertEqual(s["scan"]["content"], [], (vp, s["scan"]))
            self.assertTrue(s["rows"] and all(lang == "nb" and text for lang, text in s["rows"]), (vp, s["rows"]))
            self.assertTrue(all(not l.startswith("(") or "imperative" not in l for l in s["labels"]), (vp, s["labels"]))
            self.assertEqual(R["suggest"]["scan"]["content"], [], (vp, R["suggest"]["scan"]))
            self.assertTrue(R["suggest"]["sides"], vp)
            self.assertTrue(all(lang == "nb" for lang, _t in R["suggest"]["sides"] if not _t.startswith("+")),
                            (vp, R["suggest"]["sides"]))

    def test_e_history_and_favourites(self):
        for vp, R in self.each():
            self.assertTrue(R["faved"], vp)
            for page in ("history", "favourites"):
                got = R["personal"][page]
                self.assertEqual(got["scan"]["content"], [], (vp, page, got["scan"]))
                lines = [t for lang, t in got["sides"] if lang == "nb"]
                self.assertTrue(lines, (vp, page, got["sides"]))

    def test_f_the_switch_hidden_the_direction_kept(self):
        for vp, R in self.each():
            sw = R["sw"]
            self.assertEqual((sw["switchShown"], sw["boxLang"]), (0, "nb"), vp)
            self.assertNotIn("#en=", sw["random"], vp)            # Random word Norwegian (155)
            self.assertEqual(sw["stored"], "en", vp)              # the stored direction untouched
            self.assertTrue(any(self.place(vp) in c for c in sw["icon"]), (vp, sw["icon"]))
            self.assertEqual((sw["shown"]["switchShown"], sw["shown"]["checked"]), (1, True), vp)

    def test_g_rows_and_hovers(self):
        for vp, R in self.each():
            self.assertIn("ordpar-nbo-rows0", cls(R["rows0"]), vp)
            self.assertGreater(R["rows0"]["rows"], 0, vp)
            self.assertEqual(R["rows0"]["snippets"], 0, (vp, R["rows0"]))
        R = RESULT["computer"]
        self.assertTrue(R["hoverNb"], R["hoverNb"])
        self.assertTrue(all("ordpar-nbpk" in c and lang == "nb" and text for c, lang, text in R["hoverNb"]),
                        R["hoverNb"])
        self.assertEqual(R["hoverNone"], [])

    def test_h_the_icon_setting(self):
        for vp, R in self.each():
            self.assertEqual(R["iconoff"]["icons"], 0, vp)
            self.assertIn("ordpar-nbo", cls(R["iconoff"]), vp)

    def test_i_definer(self):
        for vp, R in self.each():
            d = R["definer"]
            self.assertEqual(d["header"], 0, vp)
            self.assertIn("ordpar-nbo", cls(d), vp)
            self.assertEqual((d["hw"], d["stored"]), (["true"], None), (vp, d))
            a = d["after"]
            self.assertNotIn("ordpar-nbo", cls(a), (vp, a))
            self.assertEqual((a["hw"], a["stored"]), (["false"], None), (vp, a))
            self.assertEqual(a["visit"].get("nbonly"), "off", (vp, a))

    def test_j_the_labels_setting(self):
        for vp, R in self.each():
            lab = R["labels"]
            self.assertNotIn("ordpar-nbo", cls(lab), vp)
            self.assertEqual(lab["h3"], ["Opphav", "Betydning og bruk", "Faste uttrykk"], vp)
            self.assertEqual(lab["pos"], ["substantiv intetkjønn"], vp)
            self.assertTrue(lab["enDefs"] and lab["gloss"], vp)
            self.assertEqual(lab["lab"]["labels"], "no", vp)
            # the card foot stays English (the interface's; Robin, 2026-11-03)
            foot = lab["lab"]["foot"]
            # (166's follow-up, Robin 2026-11-05: on a phone with Share, Copy link is not shown)
            self.assertIn(_first_english(vp, foot), foot, (vp, foot))
            # since 166 is on (2026-11-05) "Suggest a correction" too, English as the rest of the foot
            self.assertTrue(set(foot) <= {"Copy link", "Share", "Suggest a correction"}, (vp, foot))
            # 152's follow-up: with the layer on and the labels English, the headings Norwegian too
            both = R["layerLabels"]
            self.assertEqual(both["h3"], ["Opphav", "Betydning og bruk", "Faste uttrykk"], vp)
            self.assertEqual(both["pos"], ["substantiv intetkjønn"], vp)

    def test_l_the_layer_turns_every_label(self):
        for vp, R in self.each():
            n = R["nbl"]
            for name in ("hus", "go", "word"):
                got = n[name]
                self.assertIn("ordpar-nbo", got["cls"].split(), (vp, name))
                self.assertEqual(got["labels"], "en", (vp, name))        # never written
                self.assertEqual(got["en"], [], (vp, name, got))         # no English label shown
                self.assertTrue(got["nb"], (vp, name, got))
                self.assertIn("Betydning og bruk", got["h3"], (vp, name, got))
                self.assertEqual(got["infl"], ["Vis bøyning"], (vp, name, got))
                self.assertIn(_first_english(vp, got["foot"]), got["foot"], (vp, name, got))   # the foot English
                self.assertTrue(set(got["foot"]) <= {"Copy link", "Share", "Suggest a correction"}, (vp, name, got))
            self.assertIn("Opphav", n["hus"]["h3"], vp)
            self.assertIn("Opphav", n["go"]["h3"], vp)
            mini = n["mini"]
            self.assertTrue(mini["opened"], vp)
            self.assertEqual(mini["en"], [], (vp, mini))
            self.assertIn("Eksempel", mini["nb"], (vp, mini))       # ordbokene's layout's heading
            off = n["off"]
            self.assertNotIn("ordpar-nbo", off["cls"].split(), vp)
            self.assertEqual(off["labels"], "en", vp)
            self.assertEqual(off["nb"], [], (vp, off))
            self.assertIn("Etymology", off["h3"], (vp, off))
            self.assertIn("Senses and Example Sentences", off["h3"], (vp, off))
            self.assertEqual(off["infl"], ["Inflection"], (vp, off))

    def test_k_back_off(self):
        for vp, R in self.each():
            b = R["back"]
            self.assertFalse({c for c in cls(b) if "nbo" in c}, (vp, b["cls"]))
            self.assertEqual(b["stored"], "off", vp)
            self.assertTrue(b["gloss"] and b["enDefs"] and b["eye"], (vp, b))
            self.assertEqual(b["pos"], ["noun neuter"], vp)


if __name__ == "__main__":
    unittest.main()
