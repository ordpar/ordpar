"""Site decisions 129 (2026-10-25): History keeps a one-article search left before its article arrives (headless Edge).

Found by 126's build: a search that finds one translated article wrote its History entry only once
the article's text had been fetched (`lookup.js` `recordSearch`), so a reader on a slow connection
who left the page right after the results heading lost the entry. The fix (Robin's go): the entry
is written at once and the text fills it when it comes, as `recordOpened` already did.

Through `browser/history129.js`, every request delayed by 400 ms: the search page opened at
`/bm-en/#q=vindu` (one translated article), left by a full navigation to `/history/` the moment the
results heading is drawn, from inside the page. Asserted:

* the leave came while the article was still loading (`aria-busy`), so the case is the one at issue;
* History holds one entry for *vindu*, a one-article entry (`n` 1);
* the History page's row for it shows a right-hand text once filled, though the entry may be stored
  without one: a row with no stored text is drawn from the index (shell.js `needsFill`, 116).

`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before 129's deploy: fails,
History empty after the leave). Skipped without Edge, bun or a build. The counted writes behind it
are `test_ordpar_history88b.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

WORD = "vindu"          # one translated article as a headword, no inflected-form rows
LATENCY = 400

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_history129: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("history129.js", dict(word=WORD, latency=LATENCY)))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class LeftEarly(unittest.TestCase):

    def test_a_left_before_the_article_arrived(self):
        self.assertTrue(RESULT["landed"], "the History page was not reached: %r" % RESULT)
        at = RESULT["atLeave"]
        self.assertIsNotNone(at, RESULT)
        self.assertEqual(at["articles"], 1, "not a one-article search on %s: %r" % (RESULT["base"], at))
        self.assertEqual(at["busy"], 1, "the article had already arrived when the page was left: %r" % at)

    def test_b_history_holds_the_entry(self):
        got = [e for e in RESULT["history"] if e["q"] == WORD]
        self.assertEqual(len(got), 1, "History on %s after leaving early: %r" % (RESULT["base"], RESULT["history"]))
        self.assertEqual(got[0]["n"], 1, got)

    def test_c_the_row_shows_its_gloss(self):
        row = RESULT["row"]
        self.assertIsNotNone(row, "no History row for %r on %s" % (WORD, RESULT["base"]))
        self.assertFalse(row["pending"], row)
        self.assertTrue(row["text"], row)


if __name__ == "__main__":
    unittest.main()
