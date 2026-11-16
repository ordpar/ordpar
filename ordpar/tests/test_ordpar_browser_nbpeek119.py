"""Site-review decisions 119 (Robin, 2026-10-24): a Norwegian-only article's links carry their target's English, as the browser shows it (headless Edge).

The style lab's pick (breaking as the article): on a Norwegian-only
article, a bare link to a translated target with summary glosses shows the glosses in its hover
peek and in the mini's header; a link to one sense of a translated target shows that sense's whole
English definition line in the peek, broken where the article breaks it (after each ";"), in
regular weight (400), wrapping at 22rem for a single long clause, and the mini's header stays the
headword alone; nothing for an untranslated target. Through `browser/nbpeek119.js`, the site's
defaults, with a mouse, at 1280 × 900 and at 390 (a phone's width):

* *stø* II (58037) → *lene* II (34820), bare: the peek shown, "to lean · to rest, to prop
  (something) against", at the gloss peeks' weight (600); the mini's header "lene (II) — to lean ·
  to rest, to prop (something) against";
* *stø* II → *stø* IV 1 (58039 #def2): the peek "to hold up, upright or in place;" and "to support,
  to help" on two lines, weight 400, no wider than 22rem and inside the window; the mini's header
  "stø (IV, 1)" alone;
* *stø* II → *skorde* I 1 (53420 #def2), Norwegian only: no peek; the header the headword alone;
* *kuriøs* (32852) → *rar* 2 (47485 #def2), an 88-character line in three clauses: three lines,
  none wider than 22rem;
* the minis follow (cut from their pages): the mini of *merkverdig* (38021) opened on *kuriøs*
  carries its *underlig* (64348) link's peek, "strange · odd", the glosses of that translated word.

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build, snapshot
be80aae5188: fails — no peek on any of *stø* II's links, every header the headword alone).
Skipped without Edge, bun or a build. The page HTML's side: `test_ordpar_nbpeek119.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

STO, KURIOS = 58037, 32852
LENE, STO_IV, SKORDE, RAR = "/bm-en/34820/", "/bm-en/58039/#def2", "/bm-en/53420/#def2", "/bm-en/47485/#def2"
MERKVERDIG = "/bm-en/38021/#def2"
GLOSSES = "to lean · to rest, to prop (something) against"
CASES = [{"page": STO, "href": LENE}, {"page": STO, "href": STO_IV}, {"page": STO, "href": SKORDE},
         {"page": KURIOS, "href": RAR}]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_nbpeek119: skipped —", SKIP)
        return
    SITE = harness.Site()
    for w in (1280, 390):
        RESULT[w] = SITE.check("nbpeek119.js", {"w": w, "cases": CASES, "inMini": [
            {"page": KURIOS, "href": MERKVERDIG, "inner": "/bm-en/64348/"}] if w == 1280 else []})


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class NbPeeks(unittest.TestCase):

    def case(self, w, href):
        c = [c for c in RESULT[w]["cases"] if c["href"] == href][0]
        self.assertTrue(c["found"], "no link %s at %d px on %s" % (href, w, RESULT[w]["base"]))
        return c, "at %d px on %s: %s" % (w, RESULT[w]["base"], c)

    def test_a_a_bare_link_the_glosses(self):
        for w in RESULT:
            c, where = self.case(w, LENE)
            self.assertTrue(c["peek"] and c["peek"]["shown"], where)
            self.assertEqual(c["peek"]["text"], GLOSSES, where)
            self.assertEqual(c["peek"]["weight"], "600", where)
            self.assertEqual(c["head"], "lene (II) — " + GLOSSES, where)

    def test_b_one_sense_the_line_broken_in_regular_weight(self):
        for w in RESULT:
            c, where = self.case(w, STO_IV)
            p = c["peek"]
            self.assertTrue(p and p["shown"], where)
            self.assertEqual(p["text"], "to hold up, upright or in place;\nto support, to help", where)
            self.assertEqual(p["weight"], "400", where)
            self.assertEqual(p["lines"], 2, where)
            self.assertLessEqual(p["width"], 22 * p["rem"] + 0.5, where)
            self.assertGreaterEqual(p["left"], 0, where)
            self.assertLessEqual(p["right"], p["vw"], where)
            self.assertEqual(c["head"], "stø (IV, 1)", where)

    def test_c_an_untranslated_target_nothing(self):
        for w in RESULT:
            c, where = self.case(w, SKORDE)
            self.assertIsNone(c["peek"], where)
            self.assertEqual(c["head"], "skorde (I, 1)", where)

    def test_d_a_long_line_wraps_at_22rem(self):
        for w in RESULT:
            c, where = self.case(w, RAR)
            p = c["peek"]
            self.assertTrue(p and p["shown"], where)
            self.assertEqual(p["text"].count("\n"), 2, where)
            self.assertGreaterEqual(p["lines"], 3, where)
            self.assertLessEqual(p["width"], 22 * p["rem"] + 0.5, where)
            self.assertLessEqual(p["right"], p["vw"], where)

    def test_e_a_norwegian_only_mini_follows(self):
        m = RESULT[1280]["inMini"][0]
        where = "on %s: %s" % (RESULT[1280]["base"], m)
        self.assertTrue(m["opened"] and m["found"], where)
        self.assertEqual(m["peek"], "strange · odd", where)


if __name__ == "__main__":
    unittest.main()
