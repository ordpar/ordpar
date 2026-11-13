# -*- coding: utf-8 -*-
"""Site-review decisions 153 (Robin, 2026-10-30): a fixed expression's "Se:" line back on its
standalone article — the page HTML's side.

The deriver keeps the line in the unit's own `see` field (`tests/test_see_lines153.py`); the site
draws it (`article.see_html`) on the expression's **own page** only:

1. **Where**: after the unit's definition line, before its examples — where ordbokene draws it
   (its *holde i age* 100606, *aksle seg* 100615, `S/evidence/se-lines-153-2026-10-30/`); on a
   see-only unit (*aksle seg*) above its subsenses. A line of its own (`ordpar-see`,
   `display:block` in `page.SITE_CSS`), not `ordbok-def` (the meta description's harvest and the
   mini script's `isDefLine` read that class).
2. **The label**: a formula line's, as a compound list's (decisions 81): on a translated page
   "see:" (`ordpar-cl-en`) and ordbokene's own word, "Se:" or "Sjå:" (`ordpar-cl-nb`), the sheet
   showing the Norwegian under `formulas = no`; on an untranslated page the Norwegian alone.
3. **The links**: Norwegian-visible, untitled, their peek the target's English as on any
   Norwegian-only unit (decisions 119, `face.SiteFace.target_english`): a target with summary
   glosses shows them; one without, none — on a translated page too.
4. **Not**: an expression embedded under its headword (`_expr_html`); a fragment rendered without
   `see_lines` (the default — the Anki deck's `deck/render.py`); the deck's own card
   (`ordbok_gen.render_card`); the small article (`mini.js` `SEE_IN_MINI`, false: Robin's open
   question in entry 153, default not shown).
5. **The page's library** takes the root's see-line targets (`library.see_ids`), so the links
   resolve; an embedded expression's are not loaded.

Two parts: stub rows through the face (always runs; fails on the code before this build — no
`see_lines`, no `see_html`), and the built pages — *absolutt flertall* (100586, translated),
*aksle seg* (100615, untranslated), *aksle* (569, embedding *aksle seg*) — from `ordpar/out/` (or
`ORDPAR_TEST_OUT`), or fetched from `ORDPAR_TEST_BASE` (the live site before the build fails
100586 and 100615). A page missing from the build skips its test. The built-page tests wait on
the library's re-derive (100586's row gains its `see`) and the site build.
"""
import os
import re
import sys
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

from ordpar.sitegen import article, face as face_mod, library, page as page_mod  # noqa: E402
from ordpar.sitegen import deck  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
BASE = (os.environ.get("ORDPAR_TEST_BASE") or "").rstrip("/")
STRINGS = {"homograph": "homograph {n}", "inflection": "Inflection"}

SEE_ONE = "Se: [lene](/nob/bm/1), [bære](/nob/bm/2), [noe](/nob/bm/3)"


def _expr(aid, form, senses):
    return {"id": aid, "lemmas": [{"form": form, "homograph": None}], "pos_en": "fixed expression",
            "etymology": {"no": [], "en": None}, "senses": senses, "exprs": []}


# targets: 1 translated with summary glosses, 2 translated without, 3 untranslated
ROWS = {
    1: {"id": 1, "summary": {"gloss": ["to lean", "to rest"]},
        "senses": [{"defn": 2, "no": ["lene"], "en": ["to lean"], "subs": []}]},
    2: {"id": 2, "senses": [{"defn": 9, "no": ["bære"], "en": ["to carry"], "subs": []}]},
    3: {"id": 3, "senses": [{"defn": 4, "no": ["noe"], "en": None, "subs": []}]},
    # a unit shared with a definition, one example (*holde i age*'s shape)
    10: _expr(10, "lene seg", [{"defn": 2, "ordinal": 1, "no": ["støtte seg"],
                                "en": ["to lean on"], "idiom": None,
                                "see": [SEE_ONE], "ex": [["lene seg mot", "lean on"]],
                                "comp": [], "subs": []}]),
    # a see-only unit with subsenses (*aksle seg*'s shape), the nynorsk label
    11: _expr(11, "bære seg", [{"defn": 2, "ordinal": 1, "no": [], "en": [], "idiom": None,
                                "see": ["Sjå: [bære](/nob/bm/2)"], "ex": [], "comp": [],
                                "subs": [{"defn": 3, "no": ["klage"], "en": ["to complain"],
                                          "idiom": None, "ex": [], "comp": []},
                                         {"defn": 4, "no": ["oppføre seg"], "en": ["to behave"],
                                          "idiom": None, "ex": [], "comp": []}]}]),
    # a headword embedding 10
    20: {"id": 20, "lemmas": [{"form": "lene", "homograph": None}], "pos_en": "verb",
         "etymology": {"no": [], "en": None},
         "senses": [{"defn": 1, "ordinal": 1, "no": ["helle"], "en": ["to lean"], "idiom": None,
                     "ex": [], "comp": [], "subs": []}],
         "exprs": [10]},
}


class StubStore:
    library = ROWS
    mirror = {}

    def is_embedded_only(self, aid):
        return False


class StubFace(face_mod.SiteFace):
    def translated_row(self, aid):
        return ROWS[aid] if aid in (1, 2) else None


class Rendered(unittest.TestCase):

    def setUp(self):
        self.face = StubFace(StubStore())
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library(ROWS)
        self.face.set_page(99)

    def tearDown(self):
        face_mod.restore(self.saved)

    def frag(self, aid, translated, see_lines=True):
        row = ROWS[aid]
        row_no = self.mk.pair_view(row, "no")
        row_en = deck.markup.pair_view(row, "en") if translated else None
        return article.fragment(row_no, row_en, ROWS, self.mk, STRINGS, paradigm=False,
                                see_lines=see_lines)

    def see_lines(self, html):
        return re.findall(r'<span class="ordpar-see"[^>]*>.*?</span></span>(?=\n)', html)

    def test_a_translated_label_both_languages(self):
        lines = self.see_lines(self.frag(10, True))
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith(
            '<span class="ordpar-see"><span class="ordpar-cl-en" lang="en">see:</span>'
            # site decisions 152: `data-nosnippet` on the copy the default hides (154's rule)
            '<span class="ordpar-cl-nb" lang="nb" data-nosnippet>Se:</span> <span class="ordbok-xref">'),
            lines[0])

    def test_b_untranslated_label_norwegian_alone(self):
        lines = self.see_lines(self.frag(10, False))
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith('<span class="ordpar-see" lang="nb">Se: <span class='),
                        lines[0])
        self.assertNotIn("see:", lines[0])
        self.assertNotIn("ordpar-cl-", lines[0])

    def test_c_the_links_and_their_peeks(self):
        for translated in (True, False):
            line = self.see_lines(self.frag(10, translated))[0]
            # Norwegian-visible, italic in the markup
            for href, word in (("/bm-en/1/", "lene"), ("/bm-en/2/", "bære"), ("/bm-en/3/", "noe")):
                self.assertIn('href="%s" lang="nb"><em>%s</em></a>' % (href, word), line)
            # 1: its summary glosses; 2 (no summary) and 3 (untranslated): no peek
            self.assertIn('<em>lene</em></a><span class="ordbok-xpeek" lang="en" data-nosnippet>to lean · to rest'
                          '</span></span>', line)
            self.assertIn('<em>bære</em></a></span>', line)
            self.assertIn('<em>noe</em></a></span>', line)
        self.assertEqual(self.face.nb_only, 0)

    def test_d_after_the_definition_before_the_examples(self):
        html = self.frag(10, True)
        pair, see, ex = (html.index('class="ordpar-pair"'), html.index('class="ordpar-see"'),
                         html.index('class="ordbok-ex-list"'))
        self.assertLess(pair, see)
        self.assertLess(see, ex)
        html = self.frag(10, False)
        self.assertLess(html.index('class="ordbok-def"'), html.index('class="ordpar-see"'))
        self.assertLess(html.index('class="ordpar-see"'), html.index('class="ordbok-ex-list"'))

    def test_e_a_see_only_unit_above_its_subsenses(self):
        for translated in (True, False):
            html = self.frag(11, translated)
            lines = self.see_lines(html)
            self.assertEqual(len(lines), 1, lines)
            self.assertIn("Sjå:", lines[0])
            self.assertLess(html.index('class="ordpar-see"'), html.index('id="def3"'))

    def test_f_not_when_embedded(self):
        for translated in (True, False):
            html = self.frag(20, translated)
            self.assertIn("ordbok-expr", html)            # *lene seg* is there, embedded
            self.assertIn("støtte seg", html)
            self.assertNotIn("ordpar-see", html)
            self.assertNotIn("Se:", html)

    def test_g_not_without_see_lines(self):
        # the default: the Anki deck's fragments (`deck/render.py`) stay as they were
        for aid in (10, 11):
            for translated in (True, False):
                html = self.frag(aid, translated, see_lines=False)
                self.assertNotIn("ordpar-see", html)
                self.assertNotIn("Se:", html)
                self.assertNotIn("Sjå:", html)

    def test_h_not_a_definition_line(self):
        # the meta description reads `ordbok-def` lines (`describe.definitions`), the mini
        # script's `isDefLine` too: the see line is neither
        for translated in (True, False):
            for line in self.see_lines(self.frag(10, translated)):
                self.assertNotIn("ordbok-def", line.split(">", 1)[0])
        from ordpar.sitegen import describe
        defs = describe.definitions(self.frag(11, False), False)
        self.assertFalse(any("Sjå" in d or "bære" == d for d in defs), defs)


class TheDeck(unittest.TestCase):

    def test_the_cards_have_no_see_line(self):
        g = deck.ordbok_gen
        for aid in (10, 11):
            card = g.render_card(ROWS[aid], dict(ROWS), strict=False)
            self.assertNotIn("Se:", card)
            self.assertNotIn("Sjå:", card)
            self.assertNotIn("see:", card)
            self.assertNotIn("/nob/bm/3", card)


class TheSheetAndTheMini(unittest.TestCase):

    def test_a_the_line_is_a_block_and_its_label_follows_formulas(self):
        css = page_mod.SITE_CSS
        self.assertIn(".ordpar-see{display:block}", css)
        self.assertIn(".ordpar-cl-nb{display:none}", css)
        self.assertIn("html.ordpar-formulas-no .ordpar-cl-en{display:none}", css)
        self.assertIn("html.ordpar-formulas-no .ordpar-cl-nb{display:inline}", css)

    def test_b_the_small_article_leaves_it_out_by_default(self):
        with open(os.path.join(ROOT, "ordpar", "site", "mini.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertEqual(len(re.findall(r"^\s*var SEE_IN_MINI = false;", js, re.M)), 1)
        m = re.search(r"function finish\(root\) \{\n(.*?)\n  \}\n", js, re.S)
        self.assertTrue(m)
        self.assertIn("if (!SEE_IN_MINI)", m.group(1))
        self.assertIn("querySelectorAll('.ordpar-see')", m.group(1))


class ThePageLibrary(unittest.TestCase):

    def test_a_see_ids(self):
        self.assertEqual(library.see_ids(ROWS[10]), {1, 2, 3})
        self.assertEqual(library.see_ids(ROWS[11]), {2})
        self.assertEqual(library.see_ids(ROWS[20]), set())
        # `cited_ids` (every level-one row's links) does not read `see`
        self.assertFalse(library.cited_ids(ROWS[10]) & {1, 2, 3})

    def test_b_the_root_only(self):
        class Mirror(object):
            path = os.path.join(ROOT, "no-such-mirror", "bm-articles.jsonl")

            def data(self, aid):
                return None

            def __contains__(self, aid):
                return False
        rows = [r for r in ROWS.values() if "lemmas" in r] + [
            dict(ROWS[i], lemmas=[{"form": "x", "homograph": None}], pos_en="verb",
                 etymology={"no": [], "en": None}, exprs=[]) for i in (1, 2, 3)]
        store = library.Store(Mirror(), rows)
        _root, lib = store.page_library(10)
        self.assertTrue({1, 2, 3} <= set(lib))
        _root, lib = store.page_library(20)          # embeds 10: its see targets not loaded
        self.assertFalse({1, 2, 3} & set(lib))


# --- the built pages -------------------------------------------------------------

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


class BuiltPages(unittest.TestCase):

    def get(self, aid):
        html = page(aid)
        if html is None:
            self.skipTest("no page %d in %s" % (aid, BASE or OUT))
        return html

    def test_a_absolutt_flertall_translated(self):
        html = self.get(100586)
        m = re.search(r'<span class="ordpar-see"><span class="ordpar-cl-en"( lang="en")?>see:</span>'
                      # site decisions 152: `data-nosnippet` on the copy the default hides (154)
                      r'<span class="ordpar-cl-nb" lang="nb" data-nosnippet>Se:</span> (.*?)</span>\n', html)
        self.assertTrue(m, "no see line on 100586")
        for href in ("/bm-en/77/", "/bm-en/15359/"):
            self.assertRegex(m.group(2), r'href="%s"[^>]*><em>[^<]+</em></a><span class="ordbok-xpeek"'
                             % re.escape(href))
        # after the definition line, before the set-phrase box
        self.assertLess(html.index('class="ordpar-pair"'), html.index('class="ordpar-see"'))

    def test_b_aksle_seg_untranslated(self):
        html = self.get(100615)
        self.assertTrue(re.search(r'<span class="ordpar-see"( lang="nb")?>Se: <span class="ordbok-xref">'
                                  r'<a class="ordbok-xword" href="/bm-en/569/"[^>]*><em>aksle</em></a>',
                                  html), "no see line on 100615")
        self.assertLess(html.index('class="ordpar-see"'), html.index('id="def3"'))
        # the meta description still reads the definitions alone
        desc = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        self.assertNotIn("Se:", desc)

    def test_c_aksle_embeds_it_without(self):
        html = self.get(569)
        # the set phrase's term embedded, by its class and its text; the sound mark (decisions 159,
        # `data-a`) or any other attribute allowed
        self.assertRegex(html, r'class="ordbok-expr-term"[^>]*>aksle seg<')
        self.assertNotIn('class="ordpar-see"', html)


if __name__ == "__main__":
    unittest.main()
