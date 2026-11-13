"""Site decisions 102: the article card in ordbokene's widths, and no inflection table past its card (headless Edge).

**The widths.** Ordbokene's card — its article page and its search results alike — was measured on
2026-10-23 (rendered geometry only, headless Edge, a computer viewport, the 15 px scrollbar showing):
fluid at 16 px from each edge below a 784 px window, then 736, 992, 1,248 and 1,504 px, each step
opening with a short fluid run where the page is narrower than the step plus 32 px
(`docs/sessions/2026-09-19-ordpar-site-review/evidence/reports/card-width-102-measure-2026-10-23-contractor.md`,
its data `evidence/card-width-102-2026-10-23/data/obk-*.jsonl`). Those numbers are pinned below,
window by window, as ORDBOKENE_CARD, and our card is held to them, ±1 px: the article page
(`article.ordpar-card`, *fange* III 13791), a full result (`.ordpar-result`, the search "fange" with
`listview` = off) and — our own rule, one style everywhere (`standing.md`), since ordbokene's list
view was not measured — the list view's box (`.ordpar-rows`, `listview` = on). The widths include
each step's edges.

**The tables.** On *fange* III (13791), *trøtte, trette* III (62174) and *vitenskapsmann* (68839),
at 800, 1,024, 1,280 and 1,600 px, on the article page and in the article's opened list row
(`infl` = open): no table or table strip passes the card's content box; the wide table shows
exactly where it fits the box with its cells stacked, the narrow one exactly where even that does
not (decisions 108, which replaced 102's unwrapped test: until then the wide table showed only
where its UNWRAPPED width fitted); a wide table whose unwrapped width does not fit is stacked, column by
column, until it fits its box — never wider than the box, never narrower than fully stacked (his
shot 5; the first, all-or-nothing 108 build pinned it at its fully stacked width); the page never scrolls sideways. Where ordbokene's own
choice is known and ours must agree (every view from 1,024 px wide), that is pinned too
(EXPECTED_LAYOUT). At 800 px every table here is the deliberate difference — it fits our card
stacked (until 108: *vitenskapsmann*'s unwrapped), so ours is wide where ordbokene's, deciding by
the window, is narrow (`divergences.md`); until 108 *fange*'s and *trøtte*'s were pinned narrow
there. And ours decides again on a resize: *fange* III loaded at 1,600 px and narrowed to 500 px
(800 px until 108, where it now fits stacked) shows the narrow table. The stacked step itself, on
*møte* II at Robin's widths: `test_ordpar_browser_tablestack.py`.

The live site before the 102 build fails it: a 704 px card at every width from ~752 px, and
*fange*'s and *trøtte*'s participle tables 16–55 px past the card.

`ORDPAR_TEST_BASE` points it at another copy. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

# Ordbokene's card, measured 2026-10-23 (the article page /eng/bm/13791; its results page the same
# at every width measured): window width -> (card width, the page's clientWidth at that window).
# A fluid width is the clientWidth less 32; it holds only where the page shows the same 15 px
# scrollbar, which the test checks first.
ORDBOKENE_CARD = {
    320: (273, 305), 360: (313, 345), 600: (553, 585), 760: (713, 745), 780: (733, 765),
    782: (735, 767), 784: (736, 769), 786: (736, 771), 800: (736, 785), 900: (736, 885),
    1000: (736, 985), 1022: (736, 1007), 1024: (977, 1009), 1038: (991, 1023), 1040: (992, 1025),
    1100: (992, 1085), 1278: (992, 1263), 1280: (1233, 1265), 1294: (1247, 1279),
    1296: (1248, 1281), 1400: (1248, 1385), 1534: (1248, 1519), 1536: (1489, 1521),
    1550: (1503, 1535), 1552: (1504, 1537), 1600: (1504, 1585), 1920: (1504, 1905),
    2560: (1504, 2545),
}
TOLERANCE = 1.0

WIDTH_ID, WIDTH_WORD = 13791, "fange"
TABLES = [{"id": 13791, "q": "fange"}, {"id": 62174, "q": "trøtte"}, {"id": 68839, "q": "vitenskapsmann"}]
TABLE_WIDTHS = [800, 1024, 1280, 1600]
RESIZE = {"id": 13791, "from": 1600, "to": 500}

# Where ours must show what ordbokene shows (its layout measured at these windows, 2026-10-23).
EXPECTED_LAYOUT = {}
for _id in (13791, 62174, 68839):
    for _w in (1024, 1280, 1600):
        for _v in ("article", "list"):
            EXPECTED_LAYOUT[(_id, _w, _v)] = "wide"

SITE = None
RESULT = None
SKIP = harness.skip_reason()


def setUpModule():
    global SITE, RESULT
    if SKIP:
        print("test_ordpar_browser_cardwidth: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT = SITE.check("cardwidth.js", dict(
        widths=sorted(ORDBOKENE_CARD), widthId=WIDTH_ID, widthWord=WIDTH_WORD,
        tables=TABLES, tableWidths=TABLE_WIDTHS, resize=RESIZE), timeout=900)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class CardInOrdbokenesWidths(unittest.TestCase):

    def test_same_scrollbar_as_measured(self):
        off = ["%s at %d: %s (ordbokene %d)" % (view, r["w"], r[key], ORDBOKENE_CARD[r["w"]][1])
               for r in RESULT["widths"] for view, key in (("article", "cw"), ("result", "resultCw"), ("list", "listCw"))
               if r[key] != ORDBOKENE_CARD[r["w"]][1]]
        self.assertFalse(off, "the page's clientWidth differs from the measurement's, so the fluid "
                              "widths cannot be compared: " + "; ".join(off))

    def _held(self, key, label):
        off = []
        for r in RESULT["widths"]:
            want = ORDBOKENE_CARD[r["w"]][0]
            if r[key] is None or abs(r[key] - want) > TOLERANCE:
                off.append("window %d: %s px, ordbokene %d" % (r["w"], r[key], want))
        if off:
            self.fail("%s on %s not ordbokene's card width ±%g px: %s"
                      % (label, RESULT["base"], TOLERANCE, "; ".join(off)))

    def test_article_card(self):
        self._held("art", "the article page's card")

    def test_result_card(self):
        self._held("result", "a full result's card")

    def test_list_view_box(self):
        self._held("list", "the list view's box")


@unittest.skipIf(SKIP, SKIP or "")
class NoTablePastItsCard(unittest.TestCase):

    def _cases(self):
        self.assertEqual(len(RESULT["tables"]), len(TABLES) * len(TABLE_WIDTHS) * 2)
        for c in RESULT["tables"]:
            self.assertNotIn("err", c, c)
            self.assertTrue(c["groups"], "no inflection table drawn: %s" % c)
            yield c

    def test_no_table_past_the_card(self):
        off = []
        for c in self._cases():
            for g in c["groups"]:
                if g["pastContent"] > 0.5:
                    off.append("%s %s at %d: a %s table %.1f px past the card's content box (%.1f past its edge)"
                               % (c["id"], c["view"], c["w"], g["layout"], g["pastContent"], g["pastCard"]))
            if c["sideways"] > 0:
                off.append("%s %s at %d: the page scrolls sideways by %d px" % (c["id"], c["view"], c["w"], c["sideways"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_the_wide_table_wherever_it_fits(self):
        # decisions 108: wherever it fits STACKED (until then: wherever its unwrapped width fitted)
        off = []
        for c in self._cases():
            for g in c["groups"]:
                want = "wide" if g["fits"] else "narrow"
                if g["layout"] != want:
                    off.append("%s %s at %d: %s shown, the wide tables %s unwrapped, %s stacked, in a %.1f px box"
                               % (c["id"], c["view"], c["w"], g["layout"], g["wide"], g["stacked"], g["box"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_a_squeezed_table_is_drawn_stacked(self):
        # decisions 108 (2): a wide table whose unwrapped width does not fit is stacked, column by
        # column, to fit its box — never squeezed past it, never narrower than fully stacked. (The
        # first, all-or-nothing 108 build pinned it at its fully stacked width; column-by-column
        # stacking, Robin 2026-10-23, stops as soon as it fits. Its spare width and how many
        # columns stack: test_ordpar_browser_tablestack.py.)
        off = []
        for c in self._cases():
            for g in c["groups"]:
                if g["layout"] != "wide":
                    continue
                for x, mn, mx, fits in zip(g["drawn"], g["stacked"], g["wide"], g["unwrappedFits"]):
                    ok = abs(x - mx) <= 0.5 if fits else (mn - 0.5 <= x <= g["box"] + 0.5)
                    if not ok:
                        off.append("%s %s at %d: a table drawn %.1f px wide (unwrapped %.1f, fully stacked %.1f, box %.1f)"
                                   % (c["id"], c["view"], c["w"], x, mx, mn, g["box"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_as_ordbokene_where_it_agrees(self):
        off = []
        for c in self._cases():
            want = EXPECTED_LAYOUT.get((c["id"], c["w"], c["view"]))
            got = "+".join(sorted({g["layout"] for g in c["groups"]}))
            if want and got != want:
                off.append("%s %s at %d: %s, ordbokene %s" % (c["id"], c["view"], c["w"], got, want))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_decided_again_on_a_resize(self):
        r = RESULT["resize"]
        before = {g["layout"] for g in r["before"]["groups"]}
        after = r["after"]["groups"]
        self.assertEqual(before, {"wide"}, "loaded at %d px: %s" % (r["from"], r["before"]))
        for g in after:
            self.assertEqual(g["layout"], "wide" if g["fits"] else "narrow", "after the resize to %d px: %s" % (r["to"], g))
            self.assertLessEqual(g["pastContent"], 0.5, "after the resize to %d px: %s" % (r["to"], g))
        self.assertIn("narrow", {g["layout"] for g in after}, "fange's participle table should not fit at %d px" % r["to"])


if __name__ == "__main__":
    unittest.main()
