"""Site decisions 150 (Robin, 2026-10-29): the Norwegian suggestions show the spelling typed
(headless Edge).

Through `browser/suggest150.js`, at 1,280 px and 390 px, light and dark, against the built site:
typed "selv", the row of *selvsagt* reads *selvsagt* alone (one spelling drawn, not "selvsagt,
sjølsagt"); typed "sjøl", the row reads *sjølsagt* alone; no row among the first twelve draws
more than one spelling; a row picked searches the spelling it shows; History and Recent show the
word as searched (*sjølsagt*). No sideways scroll.

**A fault against ordbokene's own suggestions, so it is shown failing first** (standing.md): run
against ordpar.no before the deploy (`ORDPAR_TEST_BASE=https://ordpar.no`), the rows fail — the
live dropdown draws "selvsagt, sjølsagt". `ORDPAR_150_SHOTS=<dir>` saves the shots. Skipped
without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

RUNS = [("computer", False, False), ("computer-dark", False, True),
        ("phone", True, False), ("phone-dark", True, True)]

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_suggest150: skipped —", SKIP)
        return
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_150_SHOTS")
    for tag, phone, dark in RUNS:
        args = dict(phone=phone, dark=dark, typed=["selv", "sjøl"], searched="sjølsagt")
        if shots:
            os.makedirs(shots, exist_ok=True)
            args["shots"] = {"dir": shots.replace("\\", "/"), "tag": tag}
        RESULT[tag] = SITE.check("suggest150.js", args)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Suggest150(unittest.TestCase):

    def test_the_spelling_typed(self):
        for tag, r in RESULT.items():
            selv = [x["word"] for x in r["typed"]["selv"]["rows"]]
            sjol = [x["word"] for x in r["typed"]["sjøl"]["rows"]]
            self.assertIn("selvsagt", selv, (tag, selv))
            self.assertIn("sjølsagt", sjol, (tag, sjol))
            for t in ("selv", "sjøl"):
                for row in r["typed"][t]["rows"]:
                    self.assertNotIn(", ", row["word"], (tag, t, row))
                    self.assertLessEqual(row["parts"], 1, (tag, t, row))
                    self.assertTrue(row["word"].startswith(t), (tag, t, row))
                self.assertTrue(r["typed"][t]["wide"], tag)

    def test_picked_history_and_recent(self):
        for tag, r in RESULT.items():
            self.assertEqual(r["picked"]["history"][:1], ["sjølsagt"], (tag, r["picked"]))
            self.assertIn("sjølsagt", r["history"], tag)
            self.assertIn("sjølsagt", r["recent"], tag)


if __name__ == "__main__":
    unittest.main()
