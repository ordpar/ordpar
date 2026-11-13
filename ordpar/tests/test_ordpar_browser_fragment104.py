"""Site decisions 104 (2026-10-23): the search out of the address (headless Edge).

The independent review found that a search reached by navigation went to `/bm-en/?q=<query>`, so
the reader's search reached GitHub's servers in the request line (and, in a same-site `Referer`,
with the next file fetched). The session's call at Robin's delegation: the search lives in the
fragment, `/bm-en/#q=<query>`, which a browser never sends to a server; an old `?q=` address still
answers and is rewritten to `#q=` in place.

In one fresh context, with every request the page makes recorded (`browser/fragment104.js`): a
search submitted in an article page's header before the page's own script has taken the form (the
script blocked: the head script's guard, `head.THEME_JS`, sends it to `#q=`); a search typed into
an article page's header and submitted; a search that finds nothing, made in the box of
the word page that search landed on (answered in place, since site decisions 117), and the first
of its similar words clicked (recorded in History; Back and Forward between the two); a History
row clicked. **No request carries the search in its query
string or its Referer's query.** Each of those searches is answered with the address `/bm-en/#q=…`
and no query string — or, since site decisions 117 (2026-10-25), a search for a word with a page
of its own with that page's address, `/bm-en/<word>/` (the page is requested, as an article page
is: the word reaches GitHub in the path by design; the privacy page's sentence is to be
reworded). Then `/bm-en/?q=…` answers too, rewritten to `#q=…` with no new history entry (and, its
word having a page, sent there).

What still reaches GitHub by design is not tested here (and is stated on the privacy page): the
index files a search fetches are named by the query's first few letters (`shardKey`, `tailKey`,
`snipKey`: at most three), and an article shown in full is fetched by its id. `ORDPAR_TEST_BASE=https://ordpar.no` runs it
against the live site (before this build: fails, 64 requests carrying the search; the local build
before it, without step 0: 74). With JavaScript off the form still GETs `/bm-en/?q=` (no script can stop it): not
tested, and said on the privacy page. Skipped without Edge, bun or a build.

The similar word's History entry is waited for (up to 15 s), not read after a fixed pause (2026-10-25):
a one-article search then wrote its entry only once that article had been fetched (`lookup.js` `recordSearch`),
so over the network the entry could come later than the results heading — the check after the deploy of
2026-10-25 read History 400 ms after the heading and failed once ("'hus' not found in ['lys', 'dyp']").
Since decisions 129 the entry is written at once (`test_ordpar_browser_history129.py`); the wait stays.

A search answered in place is read once its own history entry is pushed, never by the box alone
(2026-10-26): such a search first loads its query's index file and only then pushes its address and
draws, so for that time the box holds the new word over the previous answer. The miss's step passed
on *lys*'s answer and its similar words, and after a fixed 400 ms the click on "the first similar
word" met none (*husx* drawn, its similar words still loading: "Cannot read properties of null
(reading 'click')", the failures on ordpar.no after the three deploys of 2026-10-26) or *lys*'s.
Every read now waits for its state, the miss's similar words up to 20 s; the History row's search is
taken from its link. Trace: the session's `evidence/reports/fragment104-flake-2026-10-26-contractor.md`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ARGS = dict(article=39910, early="dyp", typed="lys", miss="husx", old="hytte")
#: the searches here that have a word page (site decisions 117): every word but the miss
PAGED = {"dyp", "lys", "hytte", "hus"}

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_fragment104: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("fragment104.js", ARGS))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class SearchInTheFragment(unittest.TestCase):

    def test_the_searches_were_made(self):
        s = RESULT["steps"]
        self.assertFalse(s["earlyShell"], "the article page's script was not blocked")
        for name in ("earlyFound", "typedFound", "missFound", "wordFound", "backFound", "forwardFound", "historyFound"):
            self.assertTrue(s[name], "%s: not answered on %s (%r)" % (name, RESULT["base"], s))
        self.assertGreater(RESULT["requests"], 10)

    def test_no_request_carries_the_search(self):
        self.assertEqual(RESULT["leakCount"], 0, "requests with the search in their query string or "
                         "Referer on %s: %r" % (RESULT["base"], RESULT["leaks"]))

    def test_the_address_holds_it_in_the_fragment(self):
        """A search with no page of its own (the miss) in the fragment; since site decisions 117
        (2026-10-25) a search for a word with a page (*dyp*, *lys*, *hytte*, the similar word *hus*,
        the History row's word) in its page's address, `/bm-en/<word>/`, with nothing after it —
        never in a query string either way."""
        s = RESULT["steps"]
        want = {"early": ARGS["early"], "typed": ARGS["typed"], "miss": ARGS["miss"], "similar": s["word"], "back": ARGS["miss"],
                "forward": s["word"], "old": ARGS["old"]}
        for name, q in want.items():
            with self.subTest(step=name):
                st = s[name]
                self.assertEqual(st["search"], "", st)
                if q in PAGED:
                    self.assertEqual(st["path"], "/bm-en/%s/" % _enc(q), st)
                    self.assertEqual(st["hash"], "", st)
                else:
                    self.assertEqual(st["path"], "/bm-en/", st)
                    self.assertEqual(st["hash"].replace("%20", " "), "#q=" + _enc(q), st)
                self.assertEqual(st["shown"]["box"], q, st)
        self.assertEqual(s["history"]["search"], "", s["history"])
        self.assertEqual(s["history"]["hash"], "", s["history"])
        self.assertRegex(s["history"]["path"], r"^/bm-en/[^/]+/$", s["history"])

    def test_the_history_row_and_the_similar_word(self):
        s = RESULT["steps"]
        self.assertTrue(s["historyRow"]["href"].startswith("/bm-en/#q="), s["historyRow"])
        self.assertIn(s["word"], s["historyAfterSimilar"], "the similar word chosen was not recorded")

    def test_an_old_address_is_rewritten_in_place(self):
        s = RESULT["steps"]
        self.assertTrue(s["oldFound"], s["old"])
        self.assertEqual(s["oldAddedEntries"], 1, "the rewrite added a history entry")


def _enc(q):
    from urllib.parse import quote
    return quote(q, safe="")


if __name__ == "__main__":
    unittest.main()
