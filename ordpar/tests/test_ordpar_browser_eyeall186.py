"""Site decisions 186 (2026-11-14/15): what the eye at the headword hides, in headless Edge
(`browser/eyeall186.js`), on a computer (clicked) and a phone (tapped). The setting `exeyewhat`:
"The examples' English" (the default, the eye of decisions 131) or "All the English of its article
but the etymology, each line behind its own "Show English"".

* **Settings**: "What the eye at the headword hides" right after the eye's own setting, in its
  subsection, hidden while the eye is off and shown once it is on; its two choices in order, the
  first checked; its "?". "For learners" gives the eye on and the examples' value, and puts a
  stored `all` back to it.
* **The examples' value** is the eye of 131: a press hides the examples' English only (the gloss and
  every definition stay); its name "Hide the examples' English" in both states.
* **All** (hus): the eye named "Hide the English", unpressed. A press blanks every English line of
  the article, each behind its own "Show English" cue (as many cues as lines, each covering its
  own, none uncovered), the etymology as it was, no hover peek, the reader's own cues hidden, the
  example lists where they were, an example's cue where the examples' value puts it, a reveal of a
  one-row line moving nothing below it (0.6 px at most), nothing of a hidden line in a select-all;
  then named "Show the English", pressed. The second press gives the article back exactly (its
  markup and its text). Enter presses it. A definition of three lines (slett, 100500): three cues,
  one a line.
* **The reader's own hiding** (`defs` no, `examples` no, `ety` both, one example opened first):
  blanked, nothing of it shows and none of its cues; the etymology as it was; the second press gives
  the article back exactly, the opened example included. A line's cue shows it; a press on the line
  hides it again, its cue back and focused; a second reveal leaves its pair open.
* **The examples' limit** (one a sense): as many examples shown after the press as before; "Show N
  more" opens the rest blanked, each with its cue.
* **Where**: no eye under `defs` en with `all` (one with the examples' value, as today); none under
  Norwegian only with either value; one on an article with English but no example (kid, 100084,
  whose press blanks it whole; none there with the examples' value); none on an untranslated
  article. A word page, a search answered in place, each full result of fange (a press blanks only
  its own article), an article opened in a list row (none on the row's button; the row's glosses
  hidden while its article is blanked).
* **A small article** opened in a blanked article: no cue, nothing hidden, no eye; its English shown.
* **A change while blanked**: the setting back to the examples gives the article back exactly first;
  a change of the Examples setting gives it back too.

Before a full build, `ORDPAR_TEST_OVERLAY=<folder>` with the working tree's `/site/` files and shell
pages over `ordpar/out/` (tests.md). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ALL = "All the English of its article but the etymology, each line behind its own \"Show English\""
SITE = None
RESULTS = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_eyeall186: skipped —", SKIP)
        return
    SITE = harness.Site()
    for mobile in (False, True):
        RESULTS["phone" if mobile else "computer"] = SITE.check("eyeall186.js", {"mobile": mobile})["cases"]


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class EyeAll(unittest.TestCase):

    def test_a_the_setting(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                s = c["settings"]
                self.assertFalse(s["off"]["shown"], s["off"])
                on = s["on"]
                self.assertEqual((on["after"], on["sameSub"], on["shown"], on["hint"]), ("exeyewhat", True, True, True), on)
                self.assertEqual(on["title"], "What the eye at the headword hides")
                self.assertEqual(on["choices"], ["The examples' English", ALL])
                self.assertEqual(on["values"], ["examples", "all"])
                self.assertEqual(on["checked"], ["examples"])
                self.assertEqual(s["learnersValues"], {"exeye": "on", "exeyewhat": "examples"})
                self.assertEqual(s["storedAll"], "all")
                self.assertEqual(s["afterLearners"], {"exeye": "on", "exeyewhat": "examples", "pressed": "true"})

    def test_b_the_examples_value_unchanged(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                b, p, a = c["examples"]["before"], c["examples"]["pressed"], c["examples"]["again"]
                self.assertFalse(b["cls"])
                for x in (b, p, a):
                    self.assertEqual(x["eye"]["label"], "Hide the examples' English", x["eye"])
                self.assertEqual((b["eye"]["pressed"], b["exEnShown"]), ("false", b["exEn"]))
                self.assertGreater(b["exEn"], 3)
                self.assertEqual((p["eye"]["pressed"], p["exEnShown"], p["blanked"], p["cues"]), ("true", 0, False, 0))
                self.assertTrue(p["gloss"])
                self.assertEqual(p["defsShown"], b["defsShown"])
                self.assertEqual((a["eye"]["pressed"], a["exEnShown"]), ("false", b["exEn"]))

    def test_c_all_blanks_the_article(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                b, h, a = c["all"]["before"], c["all"]["hidden"], c["all"]["shownAgain"]
                self.assertTrue(b["cls"])
                self.assertGreater(b["units"], 20)
                self.assertEqual(b["shown"], b["units"])
                self.assertEqual((b["hid"], b["cues"], b["blanked"], b["eyes"]), (0, 0, False, 1))
                self.assertEqual((b["eye"]["label"], b["eye"]["title"], b["eye"]["pressed"]),
                                 ("Hide the English", "Hide the English", "false"))
                self.assertTrue(h["blanked"])
                self.assertEqual(h["shown"], 0, "English left shown")
                self.assertEqual((h["hid"], h["cues"], h["coveredHidden"], h["uncovered"]),
                                 (h["units"], h["units"], h["units"], 0))
                self.assertEqual(h["cuesShown"], h["cues"], h)
                self.assertEqual((h["siteCues"], h["peeksShown"]), (0, 0))
                self.assertGreater(b["peeks"], 0)
                self.assertEqual((h["eye"]["label"], h["eye"]["pressed"]), ("Show the English", "true"))
                # the etymology untouched (`ety` en: its English alone)
                self.assertTrue(b["ety"], "hus has no etymology")
                self.assertEqual(h["ety"], b["ety"])
                self.assertTrue(all(e["en"] and not e["eyeCue"] for e in h["ety"]), h["ety"])
                self.assertGreater(h["selected"]["hidden"], 20)
                self.assertEqual(h["selected"]["found"], [])
                self.assertEqual(h["lists"], b["lists"], "an example list moved at the press")
                one = [r for r in h["reveals"] if r["rows"] == 1]
                self.assertGreater(len(one), 5, h["reveals"])
                self.assertEqual([r for r in one if abs(r["dy"]) > 0.6], [], "a one-row line's reveal moved what is below")
                self.assertEqual(a["same"], {"html": True, "text": True})
                self.assertEqual((a["shown"], a["hid"], a["cues"], a["blanked"]), (b["shown"], 0, 0, False))
                self.assertEqual((a["eye"]["label"], a["eye"]["pressed"]), ("Hide the English", "false"))
                e = c["all"]["enter"]
                self.assertEqual((e["blanked"], e["shown"], e["eye"]["pressed"]), (True, 0, "true"))

    def test_d_three_lines_three_cues(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                self.assertEqual(c["threeLine"], {"lines": 3, "cues": 3, "shown": 3, "own": 3})
                s = c["slett"]
                self.assertEqual((s["shown"], s["uncovered"], s["hid"]), (0, 0, s["units"]))

    def test_e_the_examples_cue_as_the_examples_value_draws_it(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                today = c["readers"]["before"]["exCue"]
                self.assertIsNotNone(today)
                self.assertEqual(today["text"], "Show English")
                for got in (c["all"]["hidden"]["exCue"], c["readers"]["hidden"]["exCue"]):
                    self.assertEqual(got, today)

    def test_f_the_readers_hiding(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                r = c["readers"]
                b, o, h, a = r["before"], r["opened"], r["hidden"], r["shownAgain"]
                self.assertGreater(b["siteCues"], 10)
                self.assertEqual(o["shown"], b["shown"] + 1, "the reader's own cue opened nothing")
                self.assertEqual((h["shown"], h["siteCues"], h["uncovered"]), (0, 0, 0))
                self.assertEqual((h["hid"], h["cues"]), (h["units"], h["units"]))
                self.assertEqual(h["ety"], o["ety"])
                self.assertTrue(o["ety"] and all(e["nb"] and e["cue"] and not e["en"] for e in o["ety"]), o["ety"])
                self.assertEqual(a["same"], {"html": True, "text": True})
                self.assertEqual((a["shown"], a["siteCues"], a["ety"]), (o["shown"], o["siteCues"], o["ety"]))

    def test_g_a_line_revealed_and_hidden_again(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                x = c["readers"]["line"]
                self.assertEqual((x["before"]["shown"], x["before"]["cueShown"]), (False, True))
                self.assertEqual((x["revealed"]["shown"], x["revealed"]["cues"]), (True, 0))
                self.assertEqual((x["hiddenAgain"]["shown"], x["hiddenAgain"]["cues"], x["hiddenAgain"]["cueShown"]),
                                 (False, 1, True))
                self.assertTrue(x["hiddenAgain"]["focused"], "the cue back is not focused")
                self.assertEqual((x["again"]["shown"], x["again"]["cues"]), (True, 0))
                self.assertTrue(x["again"]["pairOpen"], "the page script closed the pair")

    def test_h_the_examples_limit(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                m = c["more"]
                self.assertEqual(m["pressed"], m["before"], "the examples shown changed at the press")
                self.assertGreater(m["after"]["inView"], m["listBefore"], m)
                self.assertEqual(m["after"]["enShown"], 0, m)
                self.assertEqual(m["after"]["withCue"], m["after"]["inView"], m)

    def test_i_where_no_eye(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                w = c["where"]
                self.assertEqual(w["defsEnAll"]["eyes"], 0, "an eye under defs = en with all")
                self.assertEqual(w["defsEnExamples"]["eyes"], 1)
                self.assertTrue(w["defsEnExamples"]["eye"]["shown"])
                for k in ("nbExamples", "nbAll"):
                    self.assertFalse(w[k]["eye"] and w[k]["eye"]["shown"], (k, w[k]["eye"]))
                k = w["kidAll"]
                self.assertEqual((k["eyes"], k["exEn"]), (1, 0), k)
                self.assertGreater(k["units"], 0)
                kp = w["kidPressed"]
                self.assertEqual((kp["blanked"], kp["shown"], kp["cues"], kp["uncovered"]), (True, 0, kp["units"], 0))
                self.assertEqual(w["kidExamples"]["eyes"], 0)
                u = w["untranslated"]
                self.assertIsNotNone(u)
                self.assertEqual((u["units"], u["eyes"]), (0, 0), u)

    def test_j_every_article_shown_whole(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                w = c["where"]
                for k in ("word", "search"):
                    a, p = w[k], w[k + "Pressed"]
                    self.assertIsNotNone(a and a["eye"], k)
                    self.assertEqual((a["eye"]["label"], a["eye"]["pressed"], a["blanked"]), ("Hide the English", "false", False), k)
                    self.assertEqual((p["blanked"], p["shown"], p["uncovered"], p["eye"]["pressed"]), (True, 0, 0, "true"), k)
                full = [r for r in w["full"] if r]
                self.assertGreater(len(full), 1)
                for r in full:
                    self.assertEqual(r["eyes"], 1 if r["units"] else 0, r)
                f = w["fullFirst"]
                self.assertEqual((f["blanked"], f["shown"]), (True, 0))
                o = w["fullOther"]
                self.assertIsNotNone(o, "fange: a second result with an eye")
                self.assertEqual((o["blanked"], o["shown"], o["cues"]), (False, o["units"], 0))
                self.assertEqual(w["rowButtons"], 0)
                self.assertEqual((w["row"]["blanked"], w["row"]["snippet"]), (False, True), w["row"])
                rp = w["rowPressed"]
                self.assertEqual((rp["blanked"], rp["shown"], rp["snippet"]), (True, 0, False))

    def test_k_never_in_a_small_article(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                self.assertTrue(c["all"]["miniOpened"])
                m = c["all"]["mini"]
                self.assertEqual((m["cues"], m["hid"], m["eyes"]), (0, 0, 0), m)
                self.assertGreater(m["en"], 0)
                self.assertEqual(m["enShown"], m["en"], m)

    def test_l_a_change_while_blanked(self):
        for _n, c in RESULTS.items():
            with self.subTest(_n):
                x = c["all"]["changedWhat"]
                self.assertEqual(x["same"], {"html": True, "text": True})
                self.assertEqual((x["blanked"], x["cues"], x["hid"]), (False, 0, 0))
                self.assertEqual(x["eye"]["label"], "Hide the examples' English")
                self.assertEqual(c["all"]["backToAll"]["eye"]["label"], "Hide the English")
                y = c["all"]["changedExamples"]
                self.assertEqual((y["blanked"], y["blankedAny"]), (False, 0), y)


if __name__ == "__main__":
    unittest.main(verbosity=2)
