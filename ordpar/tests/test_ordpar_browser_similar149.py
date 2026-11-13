"""Site decisions 149 (Robin, 2026-10-29): similar headwords that would only repeat the page are not
listed (headless Edge).

Through `browser/similar149.js`, at 1,280 px and 390 px, light and dark, against the built site:
*selvlaget* (one article, headed *selvlaget, selvlagd, selvlaga, sjøllaget …*) no longer lists
*selvlagd* or *selvlaga* among its similar headwords; *rett* (three articles, and "is an inflected
form of" *rette* II) still lists *rette*, whose search also shows *rette* I, the noun. No sideways
scroll.

**A fault, so it is shown failing first** (standing.md: "A fault found gets a mechanical test"):
run against ordpar.no before the deploy (`ORDPAR_TEST_BASE=https://ordpar.no`), the *selvlaget*
case fails — the live page lists *selvlaga* and *selvlagd*. `ORDPAR_149_SHOTS=<dir>` saves the
shots. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SEARCHES = ["selvlaget", "rett"]
RUNS = [("computer", False, False), ("computer-dark", False, True),
        ("phone", True, False), ("phone-dark", True, True)]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_similar149: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_149_SHOTS")
    for tag, phone, dark in RUNS:
        args = dict(phone=phone, dark=dark, searches=SEARCHES)
        if shots:
            os.makedirs(shots, exist_ok=True)
            args["shots"] = {"dir": shots.replace("\\", "/"), "tag": tag}
        RESULT[tag] = SITE.check("similar149.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Similar149(unittest.TestCase):

    def test_selvlaget_lists_no_spelling_of_its_own_article(self):
        for tag, r in RESULT.items():
            s = r["searches"]["selvlaget"]
            self.assertEqual(len(s["ids"]), 1, (tag, s))
            for w in ("selvlagd", "selvlaga", "sjøllaget", "sjøllagd", "sjøllaga"):
                self.assertNotIn(w, s["similar"], (tag, s["similar"]))
            self.assertTrue(s["wide"], tag)

    def test_rett_still_lists_rette(self):
        for tag, r in RESULT.items():
            s = r["searches"]["rett"]
            self.assertIn("rette", s["similar"], (tag, s["similar"]))
            self.assertLessEqual(len(s["similar"]), 5, tag)
            self.assertTrue(s["wide"], tag)


if __name__ == "__main__":
    unittest.main()
