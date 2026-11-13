"""Site decisions 148 (Robin, 2026-10-29): the English search in a browser (headless Edge).

Through `browser/english148.js`, at 1,280 px and at 390 px (a phone), light and dark, against the
built site:

* **the switch** — drawn under the search box (a computer: below it; a phone: on Random word's
  row), a `role="switch"` checkbox labelled "Search English words", off at first; turned on by a
  real click (a tap on a phone), the box's placeholder and label "Search an English word", the box
  `lang="en"`, the direction stored on the device; a reload keeps it on (remembered);
* **the suggestions** typed with it on — *hou*, *run*, *phone*: one row per English word, the
  word semibold in the text colour, `lang="en"`; on the right the Norwegian headwords semibold in
  the accent, `lang="nb"`, each ONE spelling (no ", "); *run*'s headwords cut with "+ N more" and
  their word classes gone; a row picked runs the English search (`#en=`);
* **the results**, opened from `/bm-en/#en=<word>` — the switch on; *go*: the list view, *gå*
  first (order (c)), each row's snippet the whole gloss, wrapping, normal text (400, not the
  semibold gloss class), the searched equivalent bold (700); *house*: *hus*, *house*, *bosette*,
  the list keeping the full headword line ("bosette, busette"); *candle*: one article in full,
  the article's own title; the heading "Norwegian–English dictionary" (164); the tab title "go — Ordpar";
* **the similar English words** — *swimming* (a miss): rows, among them *swim* and *go swimming*;
  *house* (a hit): the bare list, without *house*; *hoose*: rows, *house*, *choose*, *horse*,
  *loose*, *hose* (148's follow-up: past the first letter), the page asking for its letter's
  English file, the two English tails files and the second letter's file;
* **the miss** — *smartphone*: the heading and the line with the build's numbers;
* **switched off** with a word in the box: the word searched in Norwegian; **Random word** with
  the switch on: since site decisions 155 an English word's search, the switch still on (148 item
  11's "the switch off" amended, Robin 2026-10-31);
* **History and Recent** — English searches recorded marked English (a miss not), drawn as English
  rows (the word left, first spellings right), History's links `#en=`;
* no sideways scroll anywhere.

The similar words are drawn last, after the results settle; the script waits for the list of each
search in `SIMILAR` (up to 15 s) before reading it, so a slow index file no longer reads as an empty
list, and a list that never comes still fails (2026-11-07: twice read empty on the live site).

A new feature, not a fault: run against ordpar.no before the deploy, it fails at the switch.
`ORDPAR_148_SHOTS=<dir>` saves the shots (the build's report). Skipped without Edge, bun or a
build.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SUGGEST = ["hou", "run", "phone"]
RESULTS = ["go", "house", "candle", "swimming", "hoose", "smartphone"]
#: The searches whose similar English words the checks read: the script waits for their list's first
#: word before reading the page (it comes after the results settle), and still reads an empty list,
#: failing the check, if they never come (the flaky read of 2026-11-07)
SIMILAR = ["swimming", "house", "hoose"]
RUNS = [("computer", False, False), ("computer-dark", False, True),
        ("phone", True, False), ("phone-dark", True, True)]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()

MISS_LINE = re.compile(r"^The English search looks through the English equivalents of the [\d,]+ articles "
                       r"that have them so far, \d+ % of the dictionary\. A word missing here may still have a "
                       r"Norwegian equivalent\.$")


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_english148: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_148_SHOTS")
    for tag, phone, dark in RUNS:
        args = dict(phone=phone, dark=dark, suggest=SUGGEST, results=RESULTS, similar=SIMILAR)
        if shots:
            os.makedirs(shots, exist_ok=True)
            args["shots"] = {"dir": shots.replace("\\", "/"), "tag": tag}
        RESULT[tag] = SITE.check("english148.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class English148(unittest.TestCase):

    def each(self):
        for tag, _phone, _dark in RUNS:
            yield tag, RESULT[tag]

    def test_the_switch(self):
        for tag, r in self.each():
            b, a, m = r["switch"]["before"], r["switch"]["after"], r["remembered"]
            self.assertEqual((b["role"], b["checked"], b["text"]), ("switch", False, "Search English words"), tag)
            self.assertEqual((b["placeholder"], b["lang"]), ("Search a Norwegian word", "nb"), tag)
            if r["phone"]:
                self.assertTrue(b["sameRowAsRandom"], tag)       # it fits beside Random word
            else:
                self.assertGreaterEqual(b["belowBox"], 0, tag)  # under the box
            self.assertTrue(a["checked"], tag)
            self.assertEqual((a["placeholder"], a["label"], a["lang"]),
                             ("Search an English word", "Search an English word", "en"), tag)
            self.assertEqual(r["stored"], "en", tag)
            self.assertTrue(m["checked"], tag)                  # remembered across a reload
            self.assertTrue(b["wide"] and a["wide"], tag)

    def test_the_suggestions(self):
        for tag, r in self.each():
            for q in SUGGEST:
                s = r["suggest"][q]
                self.assertTrue(s["wide"], (tag, q))
                for row in s["rows"]:
                    self.assertTrue(row["en"], (tag, q, row))
                    self.assertEqual((row["wordLang"], row["wordColour"], row["wordWeight"]),
                                     ("en", r["text"], "600"), (tag, q, row["word"]))
                    self.assertEqual((row["nbLang"], row["nbColour"], row["nbWeight"]),
                                     ("nb", r["accent"], "600"), (tag, q, row["word"]))
                    for w in row["nb"]:
                        self.assertNotIn(", ", w, (tag, q, row["word"]))     # one spelling each
                    self.assertFalse(row["overflow"], (tag, q, row["word"]))
            hou = [x["word"] for x in r["suggest"]["hou"]["rows"]]
            self.assertIn("house", hou[:3], tag)
            run = r["suggest"]["run"]["rows"][0]
            self.assertEqual(run["word"], "run", tag)
            self.assertRegex(run["more"], r"^\+ \d+ more$", tag)              # the list cut
            self.assertEqual(run["pos"], [], tag)                              # the word classes went first
            self.assertEqual(r["suggest"]["phone"]["rows"][0]["word"], "phone", tag)
            self.assertTrue(r["picked"]["hash"].startswith("#en="), (tag, r["picked"]))

    def test_the_results(self):
        for tag, r in self.each():
            go = r["results"]["go"]
            self.assertTrue(go["switchOn"], tag)
            self.assertEqual(go["heading"], "Norwegian–English dictionary", tag)   # site decisions 164
            self.assertEqual(go["title"], "go — Ordpar", tag)
            self.assertTrue(go["rows"][0]["word"].startswith("gå"), (tag, go["rows"][0]))
            for row in go["rows"]:
                # the whole equivalent bold, its brackets with it: "go", "to go", "to go (be lost)"
                self.assertTrue(any(re.sub(r"\s*\(.*?\)", "", h) in ("go", "to go") for h in row["hits"]), (tag, row))
                self.assertEqual((row["hitWeight"], row["weight"], row["white"], row["sgloss"], row["lang"]),
                                 ("700", "400", "normal", False, "en"), (tag, row["word"]))
                self.assertFalse(row["pending"], tag)
            house = [x["word"] for x in r["results"]["house"]["rows"]]
            self.assertEqual(house[:3], ["hus", "house", "bosette, busette"], tag)
            candle = r["results"]["candle"]
            self.assertEqual((candle["full"], candle["rows"]), (1, []), tag)
            self.assertNotEqual(candle["title"], "candle — Ordpar", tag)    # the article's own title
            self.assertIn("lys", candle["title"], tag)
            for q in RESULTS:
                self.assertTrue(r["results"][q]["wide"], (tag, q))

    def test_the_similar_words_and_the_miss(self):
        for tag, r in self.each():
            sw = r["results"]["swimming"]
            self.assertEqual(sw["miss"], "“swimming” is not among our English equivalents yet.", tag)
            self.assertRegex(sw["missLine"], MISS_LINE, tag)
            self.assertEqual(sw["similarHead"], "Similar English words", tag)
            self.assertTrue(sw["similarRows"], tag)
            words = [x["word"] for x in sw["similar"]]
            self.assertIn("swim", words, tag)
            self.assertIn("go swimming", words, tag)
            for row in sw["similar"]:
                self.assertTrue(row["href"].endswith("/bm-en/#en=" + row["word"].replace(" ", "%20")), (tag, row))
                self.assertFalse(row["pending"], tag)
            house = r["results"]["house"]
            self.assertFalse(house["similarRows"], tag)                  # a hit: the bare list
            self.assertTrue(house["similar"], tag)
            self.assertNotIn("house", [x["word"] for x in house["similar"]], tag)
            for x in house["similar"]:
                self.assertEqual(x["lang"], "en", tag)
            hoose = r["results"]["hoose"]
            self.assertTrue(hoose["similarRows"], tag)
            # past the first letter (148's follow-up): choose (a missing first letter, tails h-o),
            # loose (a wrong one, tails o-o), beside house, horse, hose of its own letter
            self.assertEqual([x["word"] for x in hoose["similar"]],
                             ["house", "choose", "horse", "loose", "hose"], tag)
            # the files asked for: its letter's, then (after the results) the two tails files and
            # the second letter's
            self.assertEqual(sorted(hoose["enFiles"]), ["h.json", "o.json", "tails/h-o.json", "tails/o-o.json"], tag)
            sm = r["results"]["smartphone"]
            self.assertEqual(sm["miss"], "“smartphone” is not among our English equivalents yet.", tag)

    def test_switched_off_and_random_word(self):
        for tag, r in self.each():
            off = r["off"]
            self.assertEqual((off["switchOn"], off["box"], off["english"], off["stored"]),
                             (False, "house", False, None), tag)
            self.assertEqual(off["placeholder"], "Search a Norwegian word", tag)
            self.assertNotIn("en=", off["hash"], tag)
            # site decisions 155 (amending 148 item 11): with the switch on, Random word draws an
            # English word and opens its English search; the switch stays on
            self.assertTrue(r["random"]["switchOn"], (tag, r["random"]))
            self.assertTrue(r["random"]["hash"].startswith("#en="), (tag, r["random"]))

    def test_history_and_recent(self):
        for tag, r in self.each():
            stored = r["stored_history"]
            self.assertEqual([(e["q"], e["en"]) for e in stored][:3],
                             [("hus", False), ("swim", True), ("house", True)], tag)
            self.assertNotIn("smartphone", [e["q"] for e in stored], tag)     # a miss is not recorded
            hist = {x["word"]: x for x in r["history"]["rows"]}
            self.assertTrue(hist["house"]["en"], tag)
            self.assertEqual(hist["house"]["nb"][:3], ["hus", "house", "bosette"], tag)
            self.assertEqual(hist["house"]["wordColour"], r["text"], tag)
            self.assertTrue(hist["house"]["href"].endswith("/bm-en/#en=house"), tag)
            self.assertFalse(hist["hus"]["en"], tag)
            self.assertTrue(r["history"]["wide"], tag)
            recent = {x["word"]: x for x in r["recent"]["rows"]}
            self.assertTrue(recent["swim"]["en"], tag)
            self.assertTrue(recent["swim"]["nb"], tag)
            self.assertFalse(recent["hus"]["en"], tag)


if __name__ == "__main__":
    unittest.main()
