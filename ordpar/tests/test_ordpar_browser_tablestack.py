"""Site decisions 108: the wide inflection table stacks its columns, one by one, before going narrow (headless Edge).

**What it holds.** *møte* II (39910), whose participle table Robin sent from ordbokene wide and
stacked and from ours wide, squeezed and narrow (2026-10-23, `docs/sessions/2026-09-19-ordpar-site-review/
evidence/table-stack-108-2026-10-23/robin-*.png`), with `infl` = open, at the widths of his shots
and on a phone in landscape:

- his list view (`?q=møte`, `listview` = on, the row opened) at windows of 1,337 and 1,242 px —
  the pixel widths of his shots 3 and 4 — and at 1,070 and 994 px, the CSS widths those shots
  show (his screen is scaled 125 %: our card measures 920 px in shot 4, 736 CSS px);
- his article (`/bm-en/39910/`) at 1,244 and 940 px (shots 5 and 6) and at 995 and 752 px;
- a phone in landscape, 844 × 390, the article and the list view;
- his shot 5 made exact: the article at 1,244 px with the mount narrowed to 0.8 px less than the
  participle table's unwrapped width — where his screen's fonts put his 995 px window, and
  headless Edge's never do at his widths (its unwrapped table is 1.8 px wider than the box there);
- column by column (Robin, 2026-10-23: "Stack column by column, widest first, until the table
  fits"): the article at 600 px (four of the five columns stacked), at 574 px (only the fully
  stacked table fits: all five) and at 540 px (not even that: narrow);
- the order by space saved (decisions 108, the session's call at Robin's delegation, 2026-10-23:
  at each step the column whose stacking frees the most width; ties the wider, then the
  leftmost): *brenne* I (7433), a verb whose participle table the two orders stack differently,
  at 745 px (box 660.8 px; the table 711.5 px unwrapped): space saved stacks *masculine /
  feminine* alone (650 px), where widest first stacks *definite form* (673.6 px, still too wide)
  and then *masculine / feminine* too (612.1 px) — one column more than needed; and at 995 px
  (box 698.8), where both stack one column but widest first the one that frees less (*definite
  form*, 37.9 px, against 61.5).

At each: the layout and the columns stacked as pinned (EXPECTED: "unwrapped", "narrow", or the
set of stacked columns — on *møte* II at 995 px and in the shot-5 box only *masculine / feminine*,
the column that frees the most, 61.5 px; widest first stacked *definite form*, 37.9 px); the
wide layout wherever the fully stacked table fits its box; no more columns stacked than needed
(un-stacking any one stacked column, back to its unwrapped width, would not fit); no column
carrying spare width beside its widest line (his shot 5), every wide table no wider than its
unwrapped width or its box; no cell broken inside a form (a form over two lines, or its å / har /
den/det parted from it); on *møte* II, a stacked column's cells broken where ordbokene's stacked
table breaks them and an unstacked column's on one line (COLUMN_LINES: ordbokene's *møte* II
measured 2026-10-23 in a 736 px card, rendered geometry and text only —
`evidence/reports/table-stack-108-2026-10-23-contractor.md`); no table past its card; no sideways
scroll.

The live site before the 108 build fails it (the narrow table at 994, 995, 940 and 752 px and on
the phone; the shot-5 box squeezed with spare width), and so does the first, all-or-nothing 108
build (5444cb7fc): every column stacked at 995 px and in the shot-5 box, the table two thirds of
its box. The widest-first build (29e8f86e4) fails the columns and the not-more-than-needed tests:
*definite form* stacked on *møte* II and *brenne* I wherever one column is enough, and on
*brenne* I at 745 px *definite form* and *masculine / feminine* where *masculine / feminine*
alone fits (`evidence/reports/stack-order-harness-108-100-2026-10-23-contractor.md`).

The sound icons (decisions 159, 2026-11-02): an icon after each voiced form, inside the form's
unit ("møt!" and then its icon). The check reads no icon's hidden "Play" as a cell's text, and
counts the icon's box on its line, so a column's widest line runs to its icon (the first audio
build's gate failed three tests on those readings alone: the hidden word taken for a second line,
a form after the "!", and the icon's width for spare room). Its own test: no icon parted from its
form, as drawn and with every shown table squeezed to its narrowest — which the first audio build
fails in the narrow tables (the icon after "møte" alone on the next line; fixed by `audio.js`
`bind`).

`ORDPAR_TEST_BASE` points it at another copy. Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ID, Q = 39910, "møte"
CASES = [
    {"view": "list", "w": 1337, "h": 900}, {"view": "list", "w": 1242, "h": 900},
    {"view": "list", "w": 1070, "h": 900}, {"view": "list", "w": 994, "h": 900},
    {"view": "article", "w": 1244, "h": 900}, {"view": "article", "w": 940, "h": 900},
    {"view": "article", "w": 995, "h": 900}, {"view": "article", "w": 752, "h": 900},
    {"view": "article", "w": 600, "h": 900}, {"view": "article", "w": 574, "h": 900},
    {"view": "article", "w": 540, "h": 900},
    {"view": "article", "w": 844, "h": 390, "mobile": True},
    {"view": "list", "w": 844, "h": 390, "mobile": True},
    {"view": "article", "w": 1244, "h": 900, "squeeze": 0.8},
    # the space-saved order (decisions 108): brenne I, where the two orders differ
    {"view": "article", "w": 745, "h": 900, "id": 7433}, {"view": "article", "w": 995, "h": 900, "id": 7433},
]
MF, NT, DF, PL, PP = "masculine / feminine", "neuter", "definite form", "plural", "present participle"
ALL = frozenset([MF, NT, DF, PL, PP])
# the participle table (the second wide table): unwrapped, narrow, or the columns stacked. Møte
# II's participle table: 700.6 px unwrapped; by space saved masculine / feminine first (to
# 639.1), then present participle (581.3), definite form (543.4), plural (505.5), neuter (467.7)
EXPECTED = {
    ("list", 1337, ID): "unwrapped", ("list", 1242, ID): "unwrapped", ("list", 1070, ID): "unwrapped",
    ("list", 994, ID): frozenset([MF]), ("article", 1244, ID): "unwrapped", ("article", 940, ID): frozenset([MF]),
    ("article", 995, ID): frozenset([MF]), ("article", 752, ID): frozenset([MF]),
    ("article", 600, ID): frozenset([DF, MF, PP, PL]), ("article", 574, ID): ALL, ("article", 540, ID): "narrow",
    ("article", 844, ID): frozenset([MF]), ("list", 844, ID): frozenset([MF]),
    ("squeezed", 1244, ID): frozenset([MF]),
    # brenne I: 711.5 px unwrapped; masculine / feminine alone 650 px (widest first: definite form
    # 673.6, then masculine / feminine too, 612.1)
    ("article", 745, 7433): frozenset([MF]), ("article", 995, 7433): frozenset([MF]),
}
# ordbokene's stacked participle table of møte II, column by column (its card 736 px,
# 2026-10-23): the header's lines, then each cell's
COLUMN_LINES = {
    MF: (["masculine /", "feminine"], [["møtt +", "noun"]]),
    NT: (["neuter"], [["møtt +", "noun"]]),
    DF: (["definite form"], [["den/det møtte +", "noun"]]),
    PL: (["plural"], [["møtte +", "noun"]]),
    PP: (["present", "participle"], [["møtende"]]),
}

SITE = None
RESULT = None
SKIP = harness.skip_reason()


def setUpModule():
    global SITE, RESULT
    if SKIP:
        print("test_ordpar_browser_tablestack: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT = SITE.check("tablestack.js", dict(id=ID, q=Q, cases=CASES), timeout=600)


def tearDownModule():
    if SITE:
        SITE.close()


def _key(c):
    return ("squeezed" if c.get("squeeze") else c["view"], c["w"], c.get("id", ID))


def _tag(c):
    return "%s%s at %d%s%s" % ("" if c.get("id", ID) == ID else "%d, " % c["id"], c["view"], c["w"],
                               " (phone)" if c.get("mobile") else "",
                             " in a box %g px narrower than the unwrapped table" % c["squeeze"] if c.get("squeeze") else "")


def _state(g):
    """The participle table's state as drawn: 'narrow', 'unwrapped' or the set of stacked columns."""
    if g["layout"] != "wide":
        return g["layout"]
    if len(g["cols"]) < 2:
        return "no participle table"
    stacked = frozenset(c["name"] for c in g["cols"][1] if c["stacked"])
    return stacked or "unwrapped"


def _show(s):
    return s if isinstance(s, str) else "stacked: " + ", ".join(sorted(s))


@unittest.skipIf(SKIP, SKIP or "")
class TheStackedStep(unittest.TestCase):

    def _cases(self):
        self.assertEqual(len(RESULT["cases"]), len(CASES))
        for c in RESULT["cases"]:
            self.assertNotIn("err", c, c)
            self.assertTrue(c["groups"], "no inflection table drawn: %s" % _tag(c))
            yield c

    def test_wide_wherever_the_stacked_table_fits(self):
        off = []
        for c in self._cases():
            for g in c["groups"]:
                fits = all(x <= g["box"] + 0.5 for x in g["stacked"])
                if g["layout"] != ("wide" if fits else "narrow"):
                    off.append("%s: %s shown, the wide tables %s unwrapped and %s fully stacked in a %.1f px box"
                               % (_tag(c), g["layout"], g["wide"], g["stacked"], g["box"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_columns_stacked_as_expected(self):
        off = []
        for c in self._cases():
            got, want = _state(c["groups"][0]), EXPECTED[_key(c)]
            if got != want:
                g = c["groups"][0]
                off.append("%s: %s, want %s (drawn %s, box %.1f)" % (_tag(c), _show(got), _show(want), g["drawn"], g["box"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_no_more_columns_stacked_than_needed(self):
        # the most width freed first, until it fits: un-stacking ANY one stacked column (back to
        # its unwrapped width) would not fit the box — widest first fails this where it stacked a
        # column that frees little and then needed another (brenne I at 745 px)
        off = []
        for c in self._cases():
            for g in c["groups"]:
                if g["layout"] != "wide":
                    continue
                for x, cols, wide in zip(g["drawn"], g["cols"], g["colWide"]):
                    for w, col in zip(wide, cols):
                        if col["stacked"] and x - col["width"] + w <= g["box"] + 0.5:
                            off.append("%s: %r stacked (%.1f px; %.1f unwrapped), but the table would fit "
                                       "without it: %.1f px in a %.1f px box" % (
                                           _tag(c), col["name"], col["width"], w, x - col["width"] + w, g["box"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_no_spare_width(self):
        # no column wider than its widest line needs, and no table wider than its unwrapped width or its box
        off = []
        for c in self._cases():
            for g in c["groups"]:
                if g["layout"] != "wide":
                    continue
                for x, mx, cols in zip(g["drawn"], g["wide"], g["cols"]):
                    if x > mx + 0.5 or x > g["box"] + 0.5:
                        off.append("%s: a table drawn %.1f px, unwrapped %.1f, box %.1f" % (_tag(c), x, mx, g["box"]))
                    for col in cols:
                        if col["spare"] > 1.5:
                            off.append("%s: column %r %.1f px wide with %.1f px spare beside its widest line"
                                       % (_tag(c), col["name"], col["width"], col["spare"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_no_cell_broken_inside_a_form(self):
        off = ["%s: %s" % (_tag(c), b) for c in self._cases() for g in c["groups"] for b in g["breaks"]]
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_no_icon_parted_from_its_form(self):
        # decisions 159: an icon after each voiced form, the form, its frames and its icon one unit
        # ("møt!" then its icon), as drawn and in every table squeezed to its narrowest
        off, seen = [], 0
        for c in self._cases():
            for g in c["groups"]:
                seen += g["icons"]
                off += ["%s: %s" % (_tag(c), b) for b in g["iconParts"]]
        if not seen:
            off.append("no sound icon drawn in any table (the names file not read?)")
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_breaks_where_ordbokenes_do(self):
        # a stacked column breaks as ordbokene's stacked table does; an unstacked one stays on one line
        off = []
        for c in self._cases():
            g = c["groups"][0]
            want = EXPECTED[_key(c)]
            if c.get("id", ID) != ID or isinstance(want, str) or g["layout"] != "wide" or len(g["cells"]) < 2:
                continue
            heads = {" ".join(x["lines"]): x["lines"] for x in g["cells"][1] if x["tag"] == "th"}
            tds = [x["lines"] for x in g["cells"][1] if x["tag"] == "td"]
            for k, name in enumerate([MF, NT, DF, PL, PP]):
                head, cells = COLUMN_LINES[name]
                if name not in want:
                    head, cells = [" ".join(head)], [[" ".join(l) for l in cells]]
                got = (heads.get(name), tds[k:k + 1])
                if got != (head, cells):
                    off.append("%s: %r drawn %s, want %s" % (_tag(c), name, got, (head, cells)))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))

    def test_no_table_past_the_card(self):
        off = []
        for c in self._cases():
            for g in c["groups"]:
                if g["pastContent"] > 0.5:
                    off.append("%s: a %s table %.1f px past the card's content box" % (_tag(c), g["layout"], g["pastContent"]))
            if c["sideways"] > 0:
                off.append("%s: the page scrolls sideways by %d px" % (_tag(c), c["sideways"]))
        if off:
            self.fail("on %s: %s" % (RESULT["base"], "; ".join(off)))


if __name__ == "__main__":
    unittest.main()
