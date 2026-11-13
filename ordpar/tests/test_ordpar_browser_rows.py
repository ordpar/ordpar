"""Site decisions 100 (4): the dropdown's, Recent and list-view rows keep their height (headless Edge).

Rows that change height with their content make a list jump as it fills in (a gloss arriving, a
homograph numeral, a "+ 1 more"); the suggestion rows were fitted to one line for that (82, 86),
and the Recent rows and the list view's rows follow them (86, 88, 93). On a computer (1280×900)
and a phone (390×844, touch), each row of each group must be its group's pinned height, ±1 px:

* the suggestion rows for "hu" (20 rows: an "articles" row, glosses, numerals, "+ N more"),
  standard and roomy (`suggestrows`, 86);
* the Recent rows (six searches made first, each recorded in History), standard and roomy;
* the list view's rows for "la" — with a homograph numeral (*la* I, *lade* II, *la* II) and
  without (*La*).

The heights are today's (after the follow-up build, 2026-10-23), in the one table below, so a
ruled change of a row's look is a one-line edit. `ORDPAR_TEST_BASE` points it at another copy.
Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

# (viewport, group): the height of every row, in CSS px (±1).
EXPECTED = {
    ("computer", "suggest"): 35.19,
    ("computer", "suggest-roomy"): 44.0,
    ("computer", "recent"): 35.19,
    ("computer", "recent-roomy"): 44.0,
    ("computer", "list"): 66.78,
    ("phone", "suggest"): 35.19,
    ("phone", "suggest-roomy"): 44.0,
    ("phone", "recent"): 35.19,
    ("phone", "recent-roomy"): 44.0,
    ("phone", "list"): 66.78,
}
TOLERANCE = 1.0
VIEWPORTS = {"computer": dict(w=1280, h=900, mobile=False), "phone": dict(w=390, h=844, mobile=True)}
HISTORY = ["hus", "lys", "la", "dyp", "møte", "hogg"]   # each search one Recent row
TYPED = "hu"
LIST = "la"                                             # la I, La, lade II / la II, la III

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_rows: skipped —", SKIP)
        return
    SITE = harness.Site()
    for name, vp in VIEWPORTS.items():
        RESULT[name] = SITE.check("rows.js", dict(vp, history=HISTORY, typed=TYPED, list=LIST))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class RowsKeepTheirHeight(unittest.TestCase):

    def test_rows(self):
        for (vp, group), want in EXPECTED.items():
            with self.subTest(viewport=vp, group=group):
                rows = RESULT[vp]["groups"][group]
                self.assertGreaterEqual(len(rows), 3 if group != "list" else 2, "%s %s: too few rows %s" % (vp, group, rows))
                off = ["%r %.2f" % (r["text"], r["h"]) for r in rows if abs(r["h"] - want) > TOLERANCE]
                if off:
                    self.fail("%s, %s rows on %s: not %.2f px ±%g: %s"
                              % (vp, group, RESULT[vp]["base"], want, TOLERANCE, "; ".join(off)))

    def test_cases_cover_what_they_claim(self):
        for vp in VIEWPORTS:
            with self.subTest(viewport=vp):
                self.assertEqual(RESULT[vp]["history"], len(HISTORY), "the searches were not all recorded")
                numerals = {r["numeral"] for r in RESULT[vp]["groups"]["list"]}
                self.assertEqual(numerals, {True, False}, "the list view of %r no longer has rows with AND "
                                 "without a homograph numeral: %s" % (LIST, RESULT[vp]["groups"]["list"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
