# -*- coding: utf-8 -*-
"""Site-review decisions 118 (Robin, 2026-10-24): a Norwegian-only article's compound lists — the
page HTML's side.

Until this build a Norwegian-only unit drew its compound lists through the deck's source view
(`ordbok_gen._comp_html`, `side='no'`): plain italics, no links, under the deriver's English
label — *krukke* (32341): `<em>used as a suffix in:</em> <em>blomsterkrukke</em>, …`. Now
(`sitegen.article.comp_html_nb`):

1. **every compound is a link** to its article, drawn as the page's other Norwegian-only
   references (`<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/<id>/">`, no
   peek); a compound with no target stays plain italics;
2. **the label is Norwegian**, one label, whatever the `formulas` setting: the capture's own
   intro, stored in the block since decisions 151 (`intro`, read by `comp_nb_label`; until then
   the mirror's by alignment), `COMP_NB` by the old English label only for a block derived
   before 151 — "som etterledd i ord som" on *krukke* and *stø* II, as ordbokene's rendered
   pages print it (lower case, no colon; read 2026-10-24); no intro, no label (151);
3. a translated unit's list is unchanged: both labels (`ordpar-cl-en`, `ordpar-cl-nb`), the
   compounds with their peeks; its English label 151's ("as a suffix in words such as:" on *hus*;
   "used as a suffix in:" before the re-derive of 2026-10-30, so `test_d_hus_unchanged` fails on
   a build older than that).

Two parts: the renderer over synthetic blocks (always runs), and the built pages of *krukke*,
*stø* II (58037) and *hus* (24627) — from `ordpar/out/` (or `ORDPAR_TEST_OUT`), or fetched from
`ORDPAR_TEST_BASE` (the live site before the build, snapshot be80aae5188: fails on *krukke* and
*stø*). A page missing from the build skips its test. The browser's side, with the minis and the
`formulas` setting: `test_ordpar_browser_nbcomp118.py`.
"""
import os
import re
import sys
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

from ordpar.sitegen import article  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
BASE = (os.environ.get("ORDPAR_TEST_BASE") or "").rstrip("/")
LABEL_NB = "som etterledd i ord som"


class StubMk:
    """Records what `expand` is asked for and returns it marked, so the renderer's choices show."""

    def __init__(self):
        self.calls = []

    def expand(self, text, norwegian=False, hover_only=False, strict=True):
        self.calls.append((text, norwegian))
        return "<X %s>" % text


BLOCK = {"label": "as a suffix in words such as:", "intro": "som etterledd i ord som",
         "items": [{"word": "blomsterkrukke", "href": "/nob/bm/109847", "en": None},
                   {"word": "honningkrukke", "href": "/nob/bm/117653", "en": "a honey jar"},
                   {"word": "a<b", "href": None}]}


class Renderer(unittest.TestCase):

    def test_a_nb_only_links_every_compound_untitled(self):
        mk = StubMk()
        out = article.comp_html(BLOCK, mk, False, "no", LABEL_NB)
        self.assertEqual(mk.calls, [("[blomsterkrukke](/nob/bm/109847)", True),
                                    ("[honningkrukke](/nob/bm/117653)", True)])
        self.assertIn('<span class="ordbok-def"><em>%s</em> <X [blomsterkrukke](/nob/bm/109847)>, '
                      '<X [honningkrukke](/nob/bm/117653)>, <em>a&lt;b</em></span>' % LABEL_NB, out)
        self.assertIn('<div class="ordbok-sub ordpar-comp">', out)
        self.assertNotIn("used as", out.lower())
        self.assertNotIn("ordpar-cl-", out)

    def test_b_the_label_is_the_blocks_intro(self):
        # 151: the block's own intro, verbatim (a typo normalized in the capture shows corrected)
        for intro in ("som etterledd i ord som", "i ord som", "etterledd i fuglenavn som",
                      "også i sammensetninger som"):
            out = article.comp_html(dict(BLOCK, label="X:", intro=intro), StubMk(), False, "no")
            self.assertIn("<em>%s</em> " % intro, out, intro)
            self.assertNotIn("X:", out)
        # a block derived before 151 has no `intro`: COMP_NB by its old English label
        for en, nb in (("Used as a suffix in:", "som etterledd i ord som"),
                       ("Used as a prefix in:", "som forledd i ord som"),
                       ("Also found in compounds:", "i ord som"), (None, "i ord som")):
            blk = {"label": en, "items": BLOCK["items"]} if en else {"items": BLOCK["items"]}
            out = article.comp_html(blk, StubMk(), False, "no")
            self.assertIn("<em>%s</em> " % nb, out, en)

    def test_b2_no_intro_no_label(self):
        # 151: a list with no intro has no label line on a Norwegian-only unit either
        out = article.comp_html(dict(BLOCK, label="", intro=""), StubMk(), False, "no")
        self.assertIn('<span class="ordbok-def"><X [blomsterkrukke](/nob/bm/109847)>, ', out)
        self.assertNotIn("<em></em>", out)
        self.assertNotIn("i ord som", out)
        self.assertEqual(article.comp_html({"label": "", "intro": "", "items": []}, StubMk(), False, "no"), "")

    def test_c_the_unit_passes_the_blocks_intro(self):
        mk = StubMk()
        blk = dict(BLOCK, intro="som etterledd i ord som")
        out = "\n".join(article._unit_inner({"defn": 7, "comp": [blk]}, None, mk, False, None))
        self.assertIn("<em>som etterledd i ord som</em> <X [blomsterkrukke]", out)
        out = "\n".join(article._unit_inner({"defn": 7, "comp": [dict(blk, label="", intro="", items=[])]},
                                             None, mk, False, None))
        self.assertNotIn("ordpar-comp", out)     # an empty list without an intro: nothing drawn

    def test_d_a_translated_unit_unchanged(self):
        blk = {"label": "as a suffix in words such as:", "intro": LABEL_NB,
               "items": [{"word": "hundehus", "href": "/nob/bm/24530", "en": "a kennel"}]}
        mk = StubMk()
        out = article.comp_html(blk, mk, True, "en", LABEL_NB)
        self.assertEqual(mk.calls, [('[hundehus](/nob/bm/24530 "a kennel")', True)])
        self.assertIn('<em><span class="ordpar-cl-en">as a suffix in words such as:</span>'
                      '<span class="ordpar-cl-nb" lang="nb">%s</span></em> ' % LABEL_NB, out)

    def test_e_a_translated_unit_without_an_intro(self):
        # 151: no label line in either language, no ordpar-cl pair
        blk = {"label": "", "intro": "",
               "items": [{"word": "hundehus", "href": "/nob/bm/24530", "en": "a kennel"}]}
        out = article.comp_html(blk, StubMk(), True, "en", article.comp_nb_label({}, 0, blk))
        self.assertIn('<span class="ordbok-def"><X [hundehus](/nob/bm/24530 "a kennel")></span>', out)
        self.assertNotIn("ordpar-cl-", out)
        self.assertNotIn("<em></em>", out)


def page(aid):
    """The built article page's HTML, or None when this copy has no such page."""
    if BASE:
        try:
            with urllib.request.urlopen("%s/bm-en/%d/" % (BASE, aid), timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception:
            return None
    path = os.path.join(OUT, "bm-en", str(aid), "index.html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


COMP_RE = re.compile(r'<div class="ordbok-sub ordpar-comp">\s*(<span class="ordbok-def">.*?</span>)\s*</div>', re.S)


def comps(aid, test):
    html = page(aid)
    if html is None:
        test.skipTest("no page %d in %s" % (aid, BASE or OUT))
    return COMP_RE.findall(html)


def link(word, aid, key):
    """A compound's link; since site decisions 152 it carries its target's `snip/` key (`data-s`, the
    hover's first Norwegian definition)."""
    return ('<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/%d/" data-s="%s"><em>%s</em></a></span>'
            % (aid, key, word))


class BuiltPages(unittest.TestCase):

    def test_a_krukke(self):
        self.assertEqual(comps(32341, self), [
            '<span class="ordbok-def"><em>%s</em> %s, %s</span>'
            % (LABEL_NB, link("blomsterkrukke", 109847, "b-l-o"), link("honningkrukke", 117653, "h-o-n"))])

    def test_b_sto_ii(self):
        self.assertEqual(comps(58037, self), [
            '<span class="ordbok-def"><em>%s</em> %s</span>' % (LABEL_NB, link("ryggstø", 49253, "r-y-g"))])

    def test_c_the_links_as_the_pages_other_references(self):
        # *stø* II's own definition references: the same markup, so the compounds match them
        # (since decisions 119 *lene* II, a translated target, has its glosses' peek after the link;
        # `test_ordpar_nbpeek119.py`)
        html = page(58037)
        if html is None:
            self.skipTest("no page 58037")
        self.assertIn('<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/34820/" data-s="l-e-n"><em>lene (II)</em></a>',
                      html)
        self.assertIn('<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/53420/#def2" data-s="s-k-o">'
                      '<em>skorde (I, 1)</em></a></span>',
                      html)

    def test_d_hus_unchanged(self):
        got = comps(24627, self)
        self.assertTrue(got)
        self.assertTrue(got[0].startswith(
            '<span class="ordbok-def"><em><span class="ordpar-cl-en">as a suffix in words such as:</span>'
            # site decisions 152: `data-nosnippet` on the copy the default hides; the target's
            # `snip/` key on the link (`data-s`, read by the hover's Norwegian definition)
            '<span class="ordpar-cl-nb" lang="nb" data-nosnippet>som etterledd i ord som</span></em> '
            '<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/24530/" lang="nb" data-s="h-u-n">'
            '<em>hundehus</em></a>'
            '<span class="ordbok-xpeek" data-nosnippet>'), got[0][:400])   # data-nosnippet: site decisions 154
        for c in got:
            self.assertIn('class="ordpar-cl-en"', c)
            self.assertEqual(c.count('class="ordbok-xword"'), c.count('class="ordbok-xpeek"'), c[:300])


if __name__ == "__main__":
    unittest.main()
