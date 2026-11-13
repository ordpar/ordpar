"""Site decisions 98, 100: the sense numbers a real browser draws run 1, 2, 3, … (headless Edge).

The fault (98): a bulleted subsense (`div.ordbok-sub`, drawn with `display:list-item` for its
bullet) advanced its sense list's implicit `list-item` counter, so *møte* II read 1, 3, 4, 5, 6.
The markup was right and every Python and stand-in test passed; only a browser shows it.

**What is read.** The numbers the browser actually DRAWS, from its accessibility tree (CDP
`Accessibility.getFullAXTree`: each list item's marker is a `ListMarker` node named with its
text, which is also what a screen reader announces). Each marker is mapped through its list
item to its `ol.ordbok-senses`; each visible one with n senses must read "1. " … "n. ". A
second assertion names the cause where the first fails: no element inside a sense list other
than its own `li` children may advance its `list-item` counter (computed `display` a list item,
nearest `ol`/`ul` that list, `counter-increment` not setting `list-item` to 0).

**Where.** *møte* II (39910, Robin's case) and five more translated articles with a bulleted
subsense before a later sense, each under all twelve combinations of the settings that change
the senses' styles (`layout` ordpar / ordbokene × `subsenses` defs / en × `defs` both / en / no,
applied as the classes on `<html>` that `shell.js` sets); *møte* II's mini opened from *møtes*
(39922), and its row opened in the list view of the search "møte".

Runs on the built `ordpar/out/` (a local server); `ORDPAR_TEST_BASE=https://ordpar.no` points it
at the live site. Skipped without Edge, bun or a build (`ordpar/tests/browser/harness.py`).
"""
import itertools
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

# Translated articles with a bulleted subsense (div.ordbok-sub, not a compound list) inside a
# sense that has a later sense — found by scanning ordpar/out/bm-en/ (2026-10-23: 478 such pages).
ARTICLES = {
    39910: "møte II",            # sense 1 of 5 holds one subsense (Robin's case)
    11350: "dyp II",             # senses 1, 2 and 4 of 6
    10465: "dobbelt, dobbel",    # senses 1 and 3 (two) of 4
    1033: "åpen",                # senses 7 and 8 of 12
    110737: "brennende",         # senses 1, 2 and 3 of 4
    10171: "din",                # sense 1 of 2 holds two
}
SETTINGS = [dict(layout=l, subsenses=s, defs=d)
            for l, s, d in itertools.product(("ordpar", "ordbokene"), ("defs", "en"), ("both", "en", "no"))]


def _label(aid, st):
    return "%s %s [layout=%s subsenses=%s defs=%s]" % (aid, ARTICLES.get(aid, ""), st["layout"], st["subsenses"], st["defs"])


def _cases():
    cases = []
    for aid in ARTICLES:
        for st in SETTINGS:
            cases.append(dict(label=_label(aid, st), kind="page", url="/bm-en/%d/" % aid, settings=st))
    for st in (SETTINGS[0], SETTINGS[6 + 4]):   # the defaults, and ordbokene layout + English subsenses + English only
        cases.append(dict(label="mini opened on 39922 møtes: " + _label(39910, st), kind="mini",
                          url="/bm-en/39922/", settings=st, open={"mini": "/bm-en/39910/"}))
    cases.append(dict(label="list-view row in the search 'møte': " + _label(39910, SETTINGS[0]), kind="row",
                      url="/bm-en/?q=m%C3%B8te", settings=SETTINGS[0], open={"row": 39910}))
    return cases


SITE = None
RESULT = None
SKIP = harness.skip_reason()


def setUpModule():
    global SITE, RESULT
    if SKIP:
        print("test_ordpar_browser_senses: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT = SITE.check("senses.js", {"cases": _cases()})


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class SenseNumbers(unittest.TestCase):

    def results(self, kind):
        cases = {c["label"]: c for c in _cases()}
        got = [r for r in RESULT["cases"] if cases[r["label"]]["kind"] == kind]
        self.assertTrue(got, "no %s case ran" % kind)
        return got

    def check_numbers(self, kind):
        bad = []
        for r in self.results(kind):
            for l in r["lists"]:
                want = ["%d. " % i for i in range(1, l["senses"] + 1)]
                if l["drawn"] != want:
                    bad.append("%s — %s: drawn %s for %d senses" % (r["label"], l["where"], l["drawn"], l["senses"]))
        if bad:
            self.fail("%d sense list(s) drawn with numbers that skip or repeat (decisions 98) on %s:\n%s"
                      % (len(bad), RESULT["base"], "\n".join(bad)))

    def check_shape(self, kind, where):
        """The case really exercised the fault's shape: a visible sense list with a bulleted subsense."""
        for r in self.results(kind):
            mine = [l for l in r["lists"] if l["where"] == where]
            self.assertTrue(mine, "%s: no visible sense list in the %s" % (r["label"], where))
            self.assertTrue(any(l["subs"] and l["senses"] >= 2 for l in mine),
                            "%s: no visible bulleted subsense in a list of two or more senses" % r["label"])

    def test_article_pages_number_their_senses_1_to_n(self):
        self.check_shape("page", "page")
        self.check_numbers("page")

    def test_opened_mini_numbers_its_senses_1_to_n(self):
        self.check_shape("mini", "mini")
        self.check_numbers("mini")

    def test_list_view_row_numbers_its_senses_1_to_n(self):
        self.check_shape("row", "row")
        self.check_numbers("row")

    def test_nothing_else_advances_a_sense_lists_counter(self):
        """The cause named: only a sense list's own `li` children may advance its `list-item` counter."""
        bad = ["%s — %s: %s advances the sense list's counter (counter-increment: %s)"
               % (r["label"], o["where"], o["selector"], o["counterIncrement"])
               for r in RESULT["cases"] for o in r["offenders"]]
        if bad:
            self.fail("%d element(s) other than a sense advance the sense numbers (decisions 98) on %s:\n%s"
                      % (len(bad), RESULT["base"],"\n".join(bad[:40] + (["… %d more" % (len(bad) - 40)] if len(bad) > 40 else []))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
