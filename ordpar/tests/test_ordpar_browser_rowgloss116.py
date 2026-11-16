"""Site-review decisions 116 (Robin, 2026-10-24): only the summary glosses semibold, the "·" faded (headless Edge).

The ruling: semibold for English equivalents only, and the `·` faded — the summary
glosses (42) at weight 600, at their sizes and colour, wherever a row shows them; English
definition lines stay regular text, also where the article has no summary glosses,
and every Norwegian line too; the " · " between glosses in the muted grey (`--ordpar-muted`,
#757070, night #b9b6b6) "(but still semibold)" — in the weight of the gloss it opens. Read piece
by piece in each place (`browser/rowgloss116.js`), light and dark:

* the suggestions for *fange* (a gloss list with *fange* II's English definition in it, one-article
  rows, the "Norwegian only" rows' definitions), *fly* and *båtdekk* (translated, no summary gloss);
* Recent and History after searching *fly*, *båtdekk*, *fanger*, *hus*, *fange*;
* the list view for *fly* (*fjellslette*, Norwegian, among the glosses) and *båtdekk*; the
  inflected-form rows under *fanger*; favourites (*fly* V, *fly* I, *båtdekk*);
* the article head of *hus* (already 600, decisions 42) and the mini's header for *bosted* on *hus*
  (114's 600): their separators. The header is read once the mini's body is in (`aria-busy` gone,
  the mini tagged with the article's `lang`): drawn at the click, it inherits the Norwegian line's
  `lang` until then, which a fixed 300 ms read caught on a slow answer (2026-10-25).

For each place: the named summary glosses 600, the named definition lines 400, every Norwegian
piece 400; every separator in the muted colour and the weight of the piece after it; a separator
present where a summary gloss of several items is shown. Which text is a summary gloss is the
data's (`summary.gloss`; the texts below as the build of 2026-10-24 has them).
`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before the build: fails — every
gloss 400, the separator in the text colour). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

MUTED = {False: "rgb(117, 112, 112)", True: "rgb(185, 182, 182)"}

#: place -> ([summary glosses: 600], [definition lines: 400], a separator expected)
CASES = {
    "suggestFange": (["to catch", "prisoner", "captivity"],
                     ["as much as one can hold in one's arms",
                      "person eller gjenstand som fanger (opp) noe"], True),
    "suggestFly": (["to fly", "plane, aircraft"], ["someone who flies an aeroplane"], True),
    "suggestBatdekk": ([], ["a deck on a ship where the lifeboats are stowed"], False),
    "recent": (["to fly", "plane, aircraft", "a house"],
               ["a deck on a ship where the lifeboats are stowed"], True),
    "history": (["to fly", "plane, aircraft", "a house", "to catch", "prisoner"],
                ["a deck on a ship where the lifeboats are stowed"], True),
    "listFly": (["to fly", "to rush about", "plane, aircraft"], ["fjellslette", "lite insekt"], True),
    "listBatdekk": ([], ["a deck on a ship where the lifeboats are stowed"], False),
    "inflected": (["to catch", "to capture", "prisoner", "captive", "inmate"],
                  ["as much as one can hold in one's arms"], True),
    "favourites": (["to fly", "to rush about"],
                   ["fjellslette", "a deck on a ship where the lifeboats are stowed"], True),
    "articleHead": (["a house", "a building"], [], True),
    "miniHead": (["place of residence", "dwelling place"], [], True),
}

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_rowgloss116: skipped —", SKIP)
        return
    SITE = harness.Site()
    for dark in (False, True):
        RESULT[dark] = SITE.check("rowgloss116.js", dict(dark=dark))


def tearDownModule():
    if SITE:
        SITE.close()


def _theme(dark):
    return "dark" if dark else "light"


@unittest.skipIf(SKIP, SKIP or "")
class RowGlosses(unittest.TestCase):

    def _pieces(self, dark, place):
        got = RESULT[dark]["places"].get(place)
        self.assertTrue(got, "%s (%s): nothing found on %s" % (place, _theme(dark), RESULT[dark]["base"]))
        return got

    def _find(self, pieces, text):
        for p in pieces:
            if p["t"].strip().lstrip("—").strip() == text:
                return p
        return None

    def test_a_the_theme_took(self):
        for dark in (False, True):
            self.assertEqual(RESULT[dark]["dark"], dark, _theme(dark))

    def test_b_summary_glosses_semibold(self):
        for dark in (False, True):
            for place, (glosses, _defs, _sep) in CASES.items():
                pieces = self._pieces(dark, place)
                for g in glosses:
                    p = self._find(pieces, g)
                    self.assertIsNotNone(p, "%s (%s): no %r in %s" % (place, _theme(dark), g, pieces))
                    self.assertEqual(p["w"], "600", "%s (%s): the summary gloss %r: %s on %s"
                                     % (place, _theme(dark), g, p, RESULT[dark]["base"]))

    def test_c_definition_lines_regular(self):
        for dark in (False, True):
            for place, (_glosses, defs, _sep) in CASES.items():
                pieces = self._pieces(dark, place)
                for d in defs:
                    p = self._find(pieces, d)
                    self.assertIsNotNone(p, "%s (%s): no %r in %s" % (place, _theme(dark), d, pieces))
                    self.assertEqual(p["w"], "400", "%s (%s): the definition line %r: %s"
                                     % (place, _theme(dark), d, p))
                for p in pieces:
                    if p["lang"] == "nb":
                        self.assertEqual(p["w"], "400", "%s (%s): a Norwegian line: %s" % (place, _theme(dark), p))

    def test_d_separators_faded_in_the_glosss_weight(self):
        for dark in (False, True):
            for place, (_glosses, _defs, want_sep) in CASES.items():
                pieces = self._pieces(dark, place)
                seps = [i for i, p in enumerate(pieces) if p["sep"]]
                if want_sep:
                    self.assertTrue(seps, "%s (%s): no separator in %s" % (place, _theme(dark), pieces))
                for i in seps:
                    p = pieces[i]
                    self.assertEqual(p["c"], MUTED[dark], "%s (%s): the separator's colour: %s on %s"
                                     % (place, _theme(dark), p, RESULT[dark]["base"]))
                    nxt = pieces[i + 1] if i + 1 < len(pieces) else None
                    self.assertIsNotNone(nxt, "%s: a separator with nothing after it" % place)
                    self.assertEqual(p["w"], nxt["w"], "%s (%s): the separator's weight %s, the gloss after it %s"
                                     % (place, _theme(dark), p, nxt))


if __name__ == "__main__":
    unittest.main()
