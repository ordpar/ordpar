"""Site-review decisions 118 (Robin, 2026-10-24): a Norwegian-only article's compound lists, as the browser shows them (headless Edge).

On a Norwegian-only page every compound in a compound list is a link to its article, and the
list's label is Norwegian whatever the `formulas` setting — the mirror's own intro, as ordbokene's
page prints it ("som etterledd i ord som", lower case, no colon; read on ordbokene.no's rendered
*krukke* and *stø* II, 2026-10-24). Until then the page drew the deck's source view: plain italics
under "used as a suffix in:". Through `browser/nbcomp118.js`, at 1280×900, under each `formulas`
choice (the default, `en`, `no`, `both`):

* *krukke* (32341): "som etterledd i ord som", *blomsterkrukke* -> 109847, *honningkrukke* -> 117653;
  *stø* II (58037): the same label, *ryggstø* -> 49253; each link with no peek (as the page's other
  Norwegian-only references: these targets are untranslated, so no English under 119 either);
* the same in the mini of each, opened on a page that links it (*honningkrukke* 117653 -> *krukke*,
  *ryggstø* 49253 -> *stø* II): the minis are cut from the target's page (decisions 80);
* a translated page unchanged (*hus*, 24627): its label English under the default, `en` and
  `both`, "som etterledd i ord som" under `no` (decisions 81), and every compound a link with its
  peek, *hundehus* -> 24530 first.

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build, snapshot
be80aae5188: fails — *krukke*'s and *stø*'s compounds plain text under "used as a suffix in:").
Skipped without Edge, bun or a build. The page HTML's side: `test_ordpar_nbcomp118.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

KRUKKE, STO, HUS = 32341, 58037, 24627
# *hus*'s English label since decisions 151 (2026-10-30; "used as a suffix in:" before the re-derive)
LABEL_NB, LABEL_EN = "som etterledd i ord som", "as a suffix in words such as:"
NB_ONLY = {KRUKKE: [("blomsterkrukke", 109847), ("honningkrukke", 117653)],
           STO: [("ryggstø", 49253)]}
MINIS = [(117653, KRUKKE), (49253, STO)]
CHOICES = ("default", "en", "no", "both")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_nbcomp118: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("nbcomp118.js", {"pages": [KRUKKE, STO, HUS], "minis": MINIS}))


def tearDownModule():
    if SITE:
        SITE.close()


def expected(aid):
    return [{"label": LABEL_NB,
             "items": [{"word": w, "href": "/bm-en/%d/" % t, "peek": False} for w, t in NB_ONLY[aid]]}]


@unittest.skipIf(SKIP, SKIP or "")
class NbOnlyCompounds(unittest.TestCase):

    def _where(self, choice, what):
        return "formulas=%s, %s on %s" % (choice, what, RESULT.get("base"))

    def test_a_the_pages_linked_under_the_norwegian_label(self):
        for choice in CHOICES:
            for aid in NB_ONLY:
                got = RESULT["cases"][choice]["pages"][str(aid)]
                self.assertEqual(got, expected(aid), self._where(choice, "page %d" % aid))

    def test_b_the_minis_follow(self):
        for choice in CHOICES:
            for frm, to in MINIS:
                m = RESULT["cases"][choice]["minis"]["%d-%d" % (frm, to)]
                where = self._where(choice, "the mini of %d on %d: %s" % (to, frm, m))
                self.assertTrue(m["opened"], where)
                self.assertEqual(m["lists"], expected(to), where)

    def test_c_a_translated_page_unchanged(self):
        for choice in CHOICES:
            got = RESULT["cases"][choice]["pages"][str(HUS)]
            where = self._where(choice, "page %d: %s" % (HUS, got))
            self.assertTrue(got, where)
            self.assertEqual(got[0]["label"], LABEL_NB if choice == "no" else LABEL_EN, where)
            self.assertEqual(got[0]["items"][0], {"word": "hundehus", "href": "/bm-en/24530/", "peek": True}, where)
            for lst in got:
                for it in lst["items"]:
                    self.assertTrue(it["href"] and it["peek"], where)


if __name__ == "__main__":
    unittest.main()
