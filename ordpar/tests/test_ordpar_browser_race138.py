"""Site decisions 138 (2026-10-26): a later search always wins, and "Searching…" at once (headless Edge).

The fault (found by the `fragment104` trace, the session's
`evidence/reports/fragment104-flake-2026-10-26-contractor.md` § (b)): a search answered in place — on
a word page (`lookup.js` `answerInPlace` `go`, also the 404 shell) or the search page (`search.html`
`run`) — first loads its query's index file and only then pushes its address and draws, and nothing
checked that no newer search had started meanwhile. A reader who searched again, or clicked a link in
the old answer, before the first search was answered ended on the EARLIER search: box, address, title
and answer jumped back to it. Meanwhile the old answer stayed on screen with nothing showing a search
was under way. The fix: each search takes a sequence number and drops its answer when a newer search
(or Back / Forward) has started; and the moment a search is made, the results area shows the search
page's "Searching…" line (`ordparSearch.searching`, the element `render` draws).

`browser/race138.js`, with 400 ms added to every request (CDP), two searches 50 ms apart, the first
(*husx*, its index file not yet loaded) before the second (its file already in), in three cases:
- the word page `/bm-en/lys/`: *husx* typed, then *lyse* typed;
- there: *husx* typed, then *lys*'s first similar headword clicked (since 138 the list is cleared at
  the first submit, so an identical link is clicked if it is gone: the same handler answers it);
- the search page `/bm-en/#q=lysx`: *husx* typed, then *lyse* typed.
Each is read once the second search is drawn and 1.5 s more has passed for a late answer: the box,
the address, `history.state.q`, the title and the drawn headwords are all the second search's, and no
miss is drawn. From the first submit until the second is drawn, every sample of the results area is
the "Searching…" line alone — no row, similar word or article of the previous answer.

On ordpar.no before 138's deploy every case fails (it ends on *husx*, and the old answer stays during
the wait). `ORDPAR_TEST_BASE=https://ordpar.no` runs it there. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

FIRST = "husx"
CASES = {
    "word-page-two-typed": dict(start="/bm-en/lys/", first=FIRST, second="lyse", how="box"),
    "word-page-similar-click": dict(start="/bm-en/lys/", first=FIRST, how="similar"),
    "search-page-two-typed": dict(start="/bm-en/#q=lysx", first=FIRST, second="lyse", how="box"),
}
COMMON = dict(gap=50, latency=400, late=1500)

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_race138: skipped —", SKIP)
        return
    SITE = harness.Site()
    for name, c in CASES.items():
        RESULT[name] = SITE.check("race138.js", dict(COMMON, **c), timeout=120)


def tearDownModule():
    if SITE:
        SITE.close()


def _fold(s):
    return (s or "").strip().lower()


@unittest.skipIf(SKIP, SKIP or "")
class LaterSearchWins(unittest.TestCase):

    def test_the_later_search_is_drawn(self):
        for name, r in RESULT.items():
            with self.subTest(case=name):
                self.assertIsNotNone(r["drawnAfter"], "%s on %s: the second search (%r) was never drawn; "
                                     "it ended on %r" % (name, r["base"], r["second"], r["end"]))

    def test_it_stays_the_later_search(self):
        for name, r in RESULT.items():
            second, e = r["second"], r["end"]
            with self.subTest(case=name):
                msg = "%s on %s: %r" % (name, r["base"], e)
                self.assertEqual(e["box"], second, msg)
                self.assertEqual(e["stq"], second, msg)
                # its own page where it has one (lyse, the similar word), never the first's #q=
                self.assertEqual(e["path"], "/bm-en/%s/" % second, msg)
                self.assertNotIn(FIRST, e["hash"], msg)
                self.assertIn(_fold(second), _fold(e["title"]), msg)
                self.assertNotIn(FIRST, _fold(e["title"]), msg)
                self.assertFalse(e["miss"], msg)
                self.assertIn(_fold(second), [_fold(w) for w in e["words"]], msg)
                self.assertNotIn(FIRST, _fold(e["text"]), msg)

    def test_searching_is_shown_during_the_wait(self):
        for name, r in RESULT.items():
            d = r["during"]
            with self.subTest(case=name):
                self.assertGreaterEqual(d["n"], 1)
                self.assertEqual(d["badCount"], 0, "%s on %s: %d of %d samples between the submit and the "
                                 "answer were not the \"Searching…\" line alone: %r"
                                 % (name, r["base"], d["badCount"], d["n"], d["bad"]))


if __name__ == "__main__":
    unittest.main()
