"""Site decisions 91, 100 (3): a mini opened by a tap on a phone does not move the page (headless Edge).

The fault (91): on a phone, a mini opened near the right edge was measured by `place()` where
it overhung the page, the page widened for a frame, and the browser scrolled — at a page's end
the page jumped up (*forheng* 177 → 0, *grisunge* 390 → 15, *veltrent* 128 → 0 on the build of
2026-10-22). The fix parks the box at `left:-100vw` before measuring (`sitegen/page.py` `place`).

Each case: a phone (390×844, DPR 3, touch), the article loaded, scrolled to its end (or the link
to mid-screen), the link tapped with a touch; scrollY is recorded on every frame for 1.5 s and
must never leave its value before the tap (±0.5 px), and the mini must have opened. 91's three
right-edge cases at the page's end under `emph` = no (the Norwegian line's links live, as the
diagnosis ran), *grisunge* again under `emph` = en (the default until site decisions 174, 2026-11-07;
set explicitly since, so the case still taps the English line's links), and one mid-page case (*uthus*
on 24627).
Since site decisions 151 (2026-10-30) the *grisunge* cases tap *andunge*, the same list's other
compound on the same page (*unge* 64512): the longer label "as a suffix in words such as:"
wrapped *grisunge* to the line's left (x 87 of 390), and *andunge* took its place at x 285.
A case whose link is no longer in the viewport's right half fails too: it would no longer test
the right edge.

**Shown to fail on the faulty version** (2026-10-23): served from a copy outside the worktree
holding the built `ordpar.js` with the pre-91 `place()` from git (8d745bd06), every right-edge
case at the page's end fails (the report: `.../evidence/reports/browser-tests-2026-10-23-contractor.md`).
`ORDPAR_TEST_BASE` points it at another copy. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

CASES = [
    # label, article id, link text, where, emph, right edge?
    ("forheng 61179, end, emph=no", 61179, "forheng", "end", "no", True),
    ("andunge 64512, end, emph=no", 64512, "andunge", "end", "no", True),
    ("veltrent 132830, end, emph=no", 132830, "veltrent", "end", "no", True),
    ("andunge 64512, end, emph=en", 64512, "andunge", "end", "en", True),   # 174: was the default
    ("uthus 24627, mid-page, emph=no", 24627, "uthus", "mid", "no", False),
]

SITE = None
RESULT = None
SKIP = harness.skip_reason()


def setUpModule():
    global SITE, RESULT
    if SKIP:
        print("test_ordpar_browser_scroll: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT = SITE.check("scroll.js", {"cases": [
        dict(label=l, id=i, text=t, at=w, **({"emph": e} if e else {})) for l, i, t, w, e, _ in CASES]})


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class MiniDoesNotMoveThePage(unittest.TestCase):

    def test_cases(self):
        got = {r["label"]: r for r in RESULT["cases"]}
        W = RESULT["W"]
        for label, _id, text, at, _e, right in CASES:
            with self.subTest(label):
                r = got[label]
                self.assertFalse(r.get("missing"), "%s: no live link %r on the page" % (label, text))
                if at == "end":
                    self.assertGreater(r["maxY"], 0, "%s: the page does not scroll" % label)
                    self.assertAlmostEqual(r["before"], r["maxY"], delta=1, msg="%s: not at the page's end" % label)
                if right:
                    self.assertGreater(r["linkX"], W / 2, "%s: the link is no longer in the right half (x %s)"
                                       % (label, r["linkX"]))
                self.assertIsNotNone(r["mini"], "%s: no mini opened" % label)
                moved = [y for y in r["frames"] + [r["after"]] if abs(y - r["before"]) > 0.5]
                if moved:
                    self.fail("%s on %s: the page moved when the mini opened (decisions 91): scrollY %s → %s, "
                              "frames %s" % (label, RESULT["base"], r["before"], r["after"], r["frames"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
