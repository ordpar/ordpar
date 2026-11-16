"""Site decisions 180 (Robin, 2026-11-09): everything that opens something of the site loads ahead (headless Edge).

The ruling: the Random word button fetches ahead once the pointer has rested on it for 150 ms,
and so does everything else, with the exceptions where fetching ahead makes no sense. Through `browser/ahead180.js`, on a
computer, each case in a fresh context, every request the page makes recorded (CDP; the harness's
server sends `no-store`, so a request repeated is a fetch made again):

* **Random word** on the search page (the draw made to fall on *vindu*, one article shown in
  full): resting on the button fetches the word's search files before the click — the random
  list, the word's index files, its article; the click opens the same word, and nothing of its
  search or its article is fetched again after it;
* **a similar headword** whose link is its word page (`/bm-en/<w>/#q=<w>`), rested on where the
  search page answers it in place: its search looked up before a click (`ordparLookup.lookup`
  wrapped: its index files are often in memory already, read by the search shown), the word
  page's HTML not fetched (the page will not navigate there);
* **an article's link to a word page** (`/bm-en/a/` on article 1): the word page fetched during
  the rest;
* **a suggestion row** on the History page: its word page fetched during the rest;
* **under `minifetch = click`**: nothing fetched before the click;
* **inside an open small article** (båt → skip, its link to slagskip): the nested link's article
  fetched once, not twice (mini.js and ahead.js both fetched it before 180 — the inventory's
  Doubt (a)).

The pointer's rest is not a fixed time (2026-11-11: the live check's parallel load once left
Random word's article unrequested at 700 ms): the script waits until what a case expects has been
requested and answered, 15 s at most (`rested`; `rest`, `ceiling` and `latency` in the args).

`ORDPAR_TEST_BASE` / `ORDPAR_TEST_OUT` point it at another copy (the build before 180 fails every
case but `click`). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

WORD = "vindu"
ARGS = dict(word=WORD, similarFrom="hus", moreFrom=1,
            nest={"from": 8608, "mid": 52833, "inner": 54202})   # båt -> skip -> slagskip

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_ahead180: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("ahead180.js", ARGS, timeout=400)["cases"])


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class LoadedAhead(unittest.TestCase):

    def case(self, name):
        c = RESULT[name]
        self.assertNotIn("error", c, "%s: %s" % (name, c))
        return c

    def test_a_random_word_rested_on(self):
        c = self.case("random")
        self.assertEqual(c["pending"], WORD, c)
        self.assertIn("/index/random.json", c["before"], c)
        self.assertTrue([u for u in c["beforeIndex"] if u != "/index/random.json"],
                        "no index file of the word's search before the click: %s" % c["before"])
        self.assertTrue(c["beforePages"], "its article not fetched before the click: %s" % c["before"])
        self.assertEqual(c["landed"], WORD, c)
        self.assertGreaterEqual(c["full"], 1, c)
        again = [u for u in c["after"] if u in c["before"]]
        self.assertEqual(again, [], "fetched again after the click: %s (all after: %s)" % (again, c["after"]))
        self.assertEqual(c["afterPages"], [], c)

    def test_b_a_similar_headword_with_a_word_page(self):
        c = self.case("similar")
        word_page, word = c["link"].split("#")[0], c["link"].split("#q=")[1]
        self.assertIn(word, c["looked"], "its search not looked up during the rest on %s: %s" % (c["link"], c))
        self.assertNotIn(word_page, c["before"], "the page answers in place; its word page was fetched")

    def test_c_an_articles_link_to_a_word_page(self):
        c = self.case("more")
        self.assertIn(c["link"], c["before"], c)

    def test_d_a_suggestion_row(self):
        c = self.case("suggestion")
        self.assertTrue(c["beforePages"] or c["beforeIndex"], "nothing fetched during the rest on %r" % c["row"])
        self.assertIn("/bm-en/%s/" % WORD, c["before"], c)

    def test_e_nothing_ahead_under_click(self):
        c = self.case("click")
        self.assertEqual(c["before"], [], c)
        self.assertEqual(c["landed"], WORD, c)

    def test_f_a_nested_link_fetched_once(self):
        c = self.case("nested")
        self.assertEqual(c["count"], 1, c)


if __name__ == "__main__":
    unittest.main()
