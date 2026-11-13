"""Site decisions 144 (Robin, 2026-10-27): the similar headwords as rows after a miss (headless Edge).

Through `browser/similar144.js`, at 1,280 px and at 390 px (a phone), light and dark, against the
built site:

* **the misses** *husx*, *flyy*, *spisee* and *kjøppte* (the inflected-form case): the "Similar
  headwords" list is the rows' list (`ordpar-similar-rows`, no pills); each row a link
  (`a.ordpar-option`) with the word in `lang="nb"` (the link itself unmarked, its English is not
  Norwegian), in the accent where it has a translated article and in the text colour where not;
  its word class where it heads one article; the side straight after the word (not at the right
  edge), after a muted em dash; a thin line above every row but the first; no row left pending; no
  sideways scroll. *hus*: noun, a semibold gloss; *husk* (two articles, none translated): each
  homograph's numeral and its Norwegian definition, all `nb`, no "2 articles"; *huse*: verb, its
  Norwegian definition; *fly*: no word class, numbered glosses and "+ N more", all English;
  *spisse*: its Norwegian definition; *kjøpte*: "inflected form of kjøpe". No row mixes English and
  Norwegian.
* **the hit** *katt* (its word page): the bare list, unchanged — each link the word alone,
  `lang="nb"`, a pill.
* **every place**: the 404 shell's search of a mistyped address (`/bm-en/husx`) and a miss typed
  into a word page's box (*katt*'s page, *flyy*) draw the same rows;
* **the miss-choice listener**: with `ordparEvents` stubbed, the miss is started, a click on the
  second row reports position 2 and its word, a middle click on the first position 1.
* **the suggestions** for *husk* and **History** after searching it: the Norwegian homograph list
  (numerals I and II, Norwegian text), not "2 articles".

A new feature, not a fault: a run against ordpar.no before 144's deploy fails on the rows, which
says nothing more. `ORDPAR_144_SHOTS=<dir>` saves the shots (the build's report). Skipped without
Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

MISSES = ["husx", "flyy", "spisee", "kjøppte"]
HIT = "katt"
SUGGEST = "husk"
RUNS = [("computer", False, False), ("computer-dark", False, True),
        ("phone", True, False), ("phone-dark", True, True)]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_similar144: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_144_SHOTS")
    for tag, phone, dark in RUNS:
        args = dict(phone=phone, dark=dark, misses=MISSES, hit=HIT, suggest=SUGGEST)
        if shots:
            os.makedirs(shots, exist_ok=True)
            args["shots"] = {"dir": shots.replace("\\", "/"), "tag": tag}
        RESULT[tag] = SITE.check("similar144.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


def _texts(side, **flags):
    return [p["t"] for p in side if all(p.get(k) == v for k, v in flags.items())]


def _homographs(side):
    """Both of *husk*'s homographs accounted for: I and II listed, or (where the row is too narrow,
    a phone) I listed and "+ 1 more"."""
    hg, more = _texts(side, hg=True), _texts(side, more=True)
    return hg[:2] == ["I", "II"] or (hg == ["I"] and more == ["+ 1 more"])


def _langs(side):
    """The languages of a side's words (not its numerals, not "+ N more", not a tag)."""
    return {p["lang"] for p in side if not p["hg"] and not p["more"] and not p["tag"]}


@unittest.skipIf(SKIP, SKIP or "")
class Misses(unittest.TestCase):

    def rows(self, tag, q):
        got = RESULT[tag]["misses"][q]
        self.assertIsNotNone(got, "no similar section for %r (%s)" % (q, tag))
        return got, {r["word"]: r for r in got["rows"]}

    def test_a_the_rows_list(self):
        for tag in RESULT:
            r = RESULT[tag]
            for q in MISSES:
                got, _rows = self.rows(tag, q)
                self.assertIn("ordpar-similar-rows", got["cls"].split(), (tag, q))
                self.assertEqual(got["display"], "block", (tag, q))
                self.assertLessEqual(got["scroll"], got["inner"], "sideways scroll: %s %s" % (tag, q))
                for i, row in enumerate(got["rows"]):
                    where = (tag, q, row["word"])
                    self.assertTrue(row["row"], where)
                    self.assertFalse(row["pending"], where)
                    self.assertEqual(row["aLang"], "", where)
                    self.assertEqual(row["wordLang"], "nb", where)
                    self.assertTrue(row["href"].startswith("/bm-en/"), where)
                    self.assertEqual(row["colour"], r["accent"] if row["translated"] else r["text"], where)
                    if row["side"]:
                        self.assertEqual(row["dash"], '"—"', where)
                        self.assertNotEqual(row["dashColour"], r["text"], where)     # muted
                        self.assertGreaterEqual(row["gap"], 0, where)
                        self.assertLess(row["gap"], 40, "the side is not after the word: %r" % (where,))
                    self.assertEqual(row["line"], "solid 1px" if i else "", where)
                    if not row["form"]:     # an inflected form's row: the label, then the headword
                        self.assertLessEqual(len(_langs(row["side"])), 1, "English and Norwegian in one row: %r" % (where,))

    def test_b_husx(self):
        for tag in RESULT:
            _got, rows = self.rows(tag, "husx")
            hus, husk, huse = rows["hus"], rows["husk"], rows["huse"]
            self.assertEqual((hus["pos"], hus["translated"]), ("noun", True), tag)
            self.assertTrue(_texts(hus["side"], sgloss=True), (tag, hus))
            self.assertEqual(_langs(hus["side"]), {"en"}, tag)
            # Robin, 2026-10-27: each homograph with its first Norwegian definition, not "2 articles"
            self.assertEqual(husk["pos"], "", tag)
            self.assertFalse(husk["translated"], tag)
            self.assertTrue(_homographs(husk["side"]), (tag, husk["side"]))
            self.assertEqual(_langs(husk["side"]), {"nb"}, (tag, husk["side"]))
            self.assertNotIn("articles", " ".join(_texts(husk["side"])), tag)
            self.assertEqual((huse["pos"], huse["translated"], _langs(huse["side"])), ("verb", False, {"nb"}), tag)

    def test_c_flyy(self):
        for tag in RESULT:
            _got, rows = self.rows(tag, "flyy")
            fly = rows["fly"]
            self.assertEqual(fly["pos"], "", tag)
            self.assertTrue(fly["translated"], tag)
            self.assertTrue(_texts(fly["side"], hg=True), (tag, fly["side"]))
            self.assertTrue(any(t.startswith("+ ") for t in _texts(fly["side"], more=True)), (tag, fly["side"]))
            self.assertEqual(_langs(fly["side"]), {"en"}, (tag, fly["side"]))

    def test_d_spisee(self):
        for tag in RESULT:
            _got, rows = self.rows(tag, "spisee")
            self.assertEqual(_langs(rows["spisse"]["side"]), {"nb"}, (tag, rows["spisse"]))
            self.assertFalse(rows["spisse"]["translated"], tag)

    def test_e_an_inflected_form(self):
        for tag in RESULT:
            _got, rows = self.rows(tag, "kjøppte")
            row = rows["kjøpte"]
            self.assertTrue(row["form"], (tag, row))
            self.assertEqual(row["pos"], "", tag)
            joined = "".join(p["t"] for p in row["side"])
            self.assertIn("inflected form of", joined, (tag, row["side"]))
            self.assertIn("kjøpe", joined, (tag, row["side"]))


@unittest.skipIf(SKIP, SKIP or "")
class TheHitKeepsItsList(unittest.TestCase):

    def test_katt(self):
        for tag in RESULT:
            got = RESULT[tag]["hit"]
            self.assertIsNotNone(got, tag)
            self.assertNotIn("ordpar-similar-rows", got["cls"].split(), tag)
            self.assertEqual(got["display"], "flex", tag)
            self.assertTrue(got["rows"], tag)
            for row in got["rows"]:
                self.assertFalse(row["row"], (tag, row))
                self.assertEqual(row["text"], row["word"], (tag, row))
                self.assertEqual(row["aLang"], "nb", (tag, row))
                self.assertNotIn(row["bg"], ("rgba(0, 0, 0, 0)", "transparent"), (tag, row))
                self.assertNotEqual(row["radius"], "0px", (tag, row))


@unittest.skipIf(SKIP, SKIP or "")
class EveryPlace(unittest.TestCase):
    """The 404 shell (a mistyped address searched there) and a word page's box (a miss answered in
    place) draw the same rows."""

    def test_the_404_shell_and_a_word_page(self):
        for tag in RESULT:
            for place, got in RESULT[tag]["places"].items():
                self.assertIn("ordpar-similar-rows", got["cls"].split(), (tag, place, got))
                self.assertGreater(got["rows"], 0, (tag, place, got))


@unittest.skipIf(SKIP, SKIP or "")
class TheListener(unittest.TestCase):

    def test_the_choice_and_its_position(self):
        for tag in RESULT:
            L = RESULT[tag]["listener"]
            words = L["words"]
            self.assertGreater(len(words), 1, tag)
            self.assertIn(["missStart", MISSES[0]], L["calls"], tag)
            self.assertIn(["missChoose", MISSES[0], words[1], 2], L["calls"], (tag, L))
            self.assertIn(["missChoose", MISSES[0], words[0], 1], L["calls"], (tag, L))
            self.assertEqual(L["path"], "/bm-en/", tag)              # the navigation held off


@unittest.skipIf(SKIP, SKIP or "")
class SuggestionsAndHistory(unittest.TestCase):

    def check(self, got, where):
        self.assertIsNotNone(got, where)
        self.assertFalse(got["translated"], where)
        self.assertTrue(_homographs(got["side"]), (where, got["side"]))
        self.assertEqual(_langs(got["side"]), {"nb"}, (where, got["side"]))
        self.assertNotIn("articles", " ".join(_texts(got["side"])), where)

    def test_the_suggestions_for_husk(self):
        for tag in RESULT:
            self.check(RESULT[tag]["suggest"], (tag, "suggestions"))

    def test_history_with_husk(self):
        for tag in RESULT:
            self.check(RESULT[tag]["history"], (tag, "history"))


if __name__ == "__main__":
    unittest.main()
