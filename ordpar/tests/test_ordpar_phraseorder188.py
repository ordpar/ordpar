# -*- coding: utf-8 -*-
"""Site decisions 188 (2026-11-16): the set phrases ordered by CEFR level, the static half and the
rendered pages.

* **The setting** `phraseorder` = alpha (the default) | level, in the Article section's Language
  subsection right after the level box's setting (`levels`); its words (the label, the two choices,
  a hint that says what each does, that a level keeps its phrases alphabetical and that in a
  translated article the untranslated phrases still come last); shown only while `levels` is on
  (`settings.js` `shown`); stored, exported, read from the address and reset like the rest
  (`CLASS_KEYS`, `personal.js`, `head.settings_table`); the head script's and the shell's class
  `ordpar-phraseorder-level`.
* **The presets**: For learners names `phraseorder` level; no other preset names it, so each gives
  the default, alpha; For learners' "?" line names the order.
* **The renderer** (`article._expr_html`, `fragment`): each embedded set phrase with a level carries
  it on its block (`<div class="ordbok-expr" data-level="B1">`), and a set-phrase section with any
  levelled block carries `ordpar-exprs`; with no levels (the deck's call), or none of its phrases
  levelled, the markup is exactly as before.
* **The sheet**: every rule of the order sits under `html.ordpar-levels-on.ordpar-phraseorder-level`
  (`:where`, so the sheet's own hiding rules still win): the section and its untranslated group a
  flex column, its own blocks and its group's (never a small article's inside one), A1 to C ordered 1 to 5, a block with no level 6, the untranslated group 7, so a
  level keeps the page's alphabetical order and the translated phrases stay first; the spacing
  rules that keep the gaps as in the block layout; no rule outside that prefix names `ordpar-exprs`.
* **The page's own order** (the keyboard): the page script's `phord`, run from `ordparDefs`, puts
  the blocks in the page in the drawn order while both classes are on and back in the built order
  (each block's place recorded once) when either goes, a section's own blocks and its untranslated
  group's apart, the focus given back without scrolling; no file in `ordpar/site/` names
  `ordpar-exprs`. Its behaviour is pinned in the browser test.
* **The sound icons**: the build still marks a set phrase's term in a block that carries a level
  (`audio.mark`).
* **Help**: a sentence on the order in "Practising your Norwegian: For learners" and in "CEFR
  levels"; both marked in the file's opening comment as drafts (site decisions 188).
* **Rendered pages** (through `build_site.Builder` on the real mirror; skipped without it): *hus*
  (24627) and *ete* (13208, with untranslated set phrases), each block's level the level of its
  term's box and of `ordpar/levels.tsv`; the same pages built without levels as before.

`ORDPAR_TEST_ROOT` names another copy of the repository (`git archive HEAD ordpar` unpacked over a
checkout) to show it failing on the version before the change. Stdlib unittest.
"""
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("ORDPAR_TEST_ROOT") or REPO
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ordpar.sitegen import article, face as face_mod, head, page  # noqa: E402
from ordpar.sitegen.strings import EN  # noqa: E402

import test_ordpar_levels187 as L  # noqa: E402

ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
PREFIX = ":where(html.ordpar-levels-on.ordpar-phraseorder-level)"
#: a section's own blocks and its untranslated group's, never a block deeper down (a small article's)
BLOCK = ":is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr"
WORDS = {"settings.phraseorder": "Order of the set phrases",
         "settings.phraseorder.alpha": "Alphabetical, as in Bokmålsordboka",
         "settings.phraseorder.level": "By CEFR level, A1 first"}


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _strings():
    return json.loads(_read(SITE, "strings", "en.json"))


class TheSetting(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_a_right_below_the_level_box_alpha_first(self):
        self.assertIn("{ key: 'phraseorder', values: ['alpha', 'level'], def: 'alpha', section: 'article', "
                      "sub: 'language' }", self.js)
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        self.assertEqual(order[order.index("levels") + 1], "phraseorder")

    def test_b_the_words(self):
        s = _strings()
        for k, v in WORDS.items():
            self.assertEqual(s.get(k), v, k)
        hint = s.get("settings.phraseorder.hint") or ""
        for w in ("Alphabetical", "By CEFR level", "A1", "within", "alphabetical", "untranslated",
                  "CEFR level after the headword"):
            self.assertIn(w, hint)

    def test_c_shown_only_while_the_boxes_are_on(self):
        self.assertIn("if (sp.key === 'phraseorder') { return sh.getSetting('levels') === 'on'; }",
                      _read(SITE, "settings.js"))

    def test_d_stored_exported_reset_and_in_the_address(self):
        self.assertIn("'phraseorder'", re.search(r"var CLASS_KEYS = \[([^\]]*)\]", self.js).group(1))
        self.assertIn("cl.toggle('ordpar-phraseorder-level', getSetting('phraseorder') === 'level');", self.js)
        self.assertIn("'phraseorder'", re.search(r"var SETTING_KEYS = \[([^\]]*)\]",
                                                 _read(SITE, "personal.js")).group(1))
        self.assertIn(("phraseorder", ["alpha", "level"]), head.settings_table())
        self.assertIn("s.getItem('phraseorder')==='level'&&c.add('ordpar-phraseorder-level');", head.THEME_JS)
        # before the first paint: in the head script, after the level box's class
        self.assertLess(head.THEME_JS.index("ordpar-levels-on"), head.THEME_JS.index("ordpar-phraseorder-level"))


class ThePresets(unittest.TestCase):

    def test_a_for_learners_orders_by_level(self):
        p = {x["id"]: x["values"] for x in L._presets()}
        self.assertEqual(p["learners"].get("phraseorder"), "level")
        self.assertEqual(p["learners"].get("levels"), "on")
        for pid in ("default", "english", "concise"):
            self.assertNotIn("phraseorder", p[pid], pid)     # each gives the default, alpha

    def test_b_its_line_names_the_order(self):
        note = _strings()["settings.presets.learners.note"]
        self.assertIn("CEFR level", note)
        self.assertIn("set phrases ordered by level", note)


EX = {1: {"id": 1, "lemmas": [{"form": "ha det"}], "pos_en": "fixed expression",
          "senses": [{"defn": 3, "no": ["farvel"], "en": ["bye"]}]},
      2: {"id": 2, "lemmas": [{"form": "ha seg"}], "pos_en": "fixed expression",
          "senses": [{"defn": 4, "no": ["vel"], "en": ["well"]}]},
      9: {"id": 9, "lemmas": [{"form": "ha"}], "pos_en": "verb", "exprs": [1, 2],
          "senses": [{"defn": 1, "no": ["eie"], "en": ["to have"]}]}}


class TheRenderer(unittest.TestCase):

    def setUp(self):
        self.face = face_mod.SiteFace(L.StubStore())
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library(EX)
        self.face.set_page(9)

    def tearDown(self):
        face_mod.restore(self.saved)

    def frag(self, row_en=True, **kw):
        no = self.mk.pair_view(EX[9], "no")
        en = self.mk.pair_view(EX[9], "en") if row_en else None
        return article.fragment(no, en, EX, self.mk, EN, paradigm=False, site=True, **kw)

    def test_a_each_block_carries_its_level(self):
        out = self.frag(levels={9: "A1", 1: "C", 2: "A2"})
        self.assertEqual(re.findall(r'<div class="ordbok-expr"[^>]*>', out),
                         ['<div class="ordbok-expr" data-level="C">', '<div class="ordbok-expr" data-level="A2">'])
        self.assertIn('<section class="ordbok-sec ordpar-exprs">\n    <h3 lang="en"><span class="ordpar-l-en">Set phrases</span>', out)

    def test_b_a_block_with_no_level_carries_none(self):
        out = self.frag(levels={2: "B1"})
        self.assertEqual(re.findall(r'<div class="ordbok-expr"[^>]*>', out),
                         ['<div class="ordbok-expr">', '<div class="ordbok-expr" data-level="B1">'])
        self.assertIn("ordpar-exprs", out)

    def test_c_untranslated_and_norwegian_only(self):
        out = self.frag(levels={1: "B2"}, untranslated_exprs={1, 2})
        self.assertIn('<section class="ordbok-sec ordpar-untr-only ordpar-exprs">', out)
        self.assertIn('<div class="ordbok-expr" data-level="B2">', out)
        nb = self.frag(row_en=False, levels={1: "B2", 2: "A1"})
        self.assertIn('<section class="ordbok-sec ordpar-exprs">', nb)
        self.assertIn('<div class="ordbok-expr" data-level="A1">', nb)

    def test_d_no_levels_the_markup_as_before(self):
        plain = self.frag()
        self.assertNotIn("data-level", plain)
        self.assertNotIn("ordpar-exprs", plain)
        self.assertEqual(self.frag(levels=None), plain)
        self.assertEqual(self.frag(levels={}), plain)
        # only the headword levelled: no block levelled, the section as before
        only_head = self.frag(levels={9: "A1"})
        self.assertNotIn("ordpar-exprs", only_head)
        self.assertEqual(re.sub(r'<span class="ordpar-level".*?</span></span>', "", only_head), plain)


def _parts(sel):
    """A selector list split at its top-level commas (not those inside `:is(…)`)."""
    out, depth, cur = [], 0, ""
    for ch in sel:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and not depth:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return out + [cur.strip()]


def _rules(css):
    """(selector, body) for each rule of the sheet, comments dropped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(s.strip(), b.strip()) for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


class TheSheet(unittest.TestCase):
    css = page.SITE_CSS

    def mine(self):
        return [(s, b) for s, b in _rules(self.css) if "ordpar-exprs" in s]

    def test_a_every_rule_under_the_two_classes(self):
        rules = self.mine()
        self.assertGreater(len(rules), 5)
        for sel, _b in rules:
            for part in _parts(sel):
                # the two classes first (the Norwegian-only rule adds a third)
                self.assertTrue(part.strip().startswith(PREFIX[:-1]), part)

    def test_b_the_order(self):
        got = {}
        for sel, body in self.mine():
            m = re.search(r"(?:^|;)order:(\d+)", body)
            if m:
                for part in _parts(sel):
                    got[part.strip()[len(PREFIX):].strip()] = int(m.group(1))
        want = {BLOCK: 6, ".ordpar-exprs>.ordpar-untr": 7}
        for i, lv in enumerate(("A1", "A2", "B1", "B2", "C"), 1):
            want[BLOCK + '[data-level="%s"]' % lv] = i
        self.assertEqual(got, want)

    def test_c_a_flex_column_with_the_block_gaps(self):
        body = dict((s, b) for s, b in self.mine())
        flex = PREFIX + " .ordbok-sec.ordpar-exprs," + PREFIX + " .ordpar-exprs>.ordpar-untr"
        self.assertEqual(body.get(flex), "display:flex;flex-direction:column;row-gap:.6em")
        # the margins that the flex items would otherwise add to the gap: none on a block or the
        # headings, a trailing margin inside a block cancelled, the untranslated heading's .81em kept
        self.assertEqual(body.get(PREFIX + " " + BLOCK), "margin:0;order:6")
        self.assertEqual(body.get(PREFIX + " .ordpar-exprs.ordbok-sec>h3"), "margin-bottom:0")
        self.assertEqual(body.get(PREFIX + " " + BLOCK + "::after"),
                         'content:"";display:block;margin:.6em 0 -.6em')
        self.assertEqual(body.get(PREFIX + " .ordpar-exprs>.ordpar-untr"), "margin-top:.21em;order:7")
        self.assertEqual(body.get(PREFIX + " .ordpar-exprs>.ordpar-untr>.ordpar-untr-head"), "margin:0")

    def test_c2_only_a_sections_own_blocks(self):
        # a small article opened inside a block copies set-phrase blocks into it: no rule reaches them
        for sel, _b in self.mine():
            self.assertNotRegex(sel, r"\.ordpar-exprs\s+\.ordbok-expr", sel)
            self.assertNotRegex(sel, r"\.ordpar-untr\s+\.ordbok-expr", sel)

    def test_d_nothing_else_names_the_class(self):
        # the order is drawn by the sheet; of the scripts only the page script's `phord` (below)
        # names the section, to put the page's own order in line with it
        for name in os.listdir(SITE):
            if name.endswith(".js"):
                self.assertNotIn("ordpar-exprs", _read(SITE, name), name)
        self.assertEqual(page.PAGE_JS.count("ordpar-exprs"), 1)
        self.assertIn("d.querySelectorAll('.ordpar-exprs')", page.PAGE_JS)


class ThePageOrder(unittest.TestCase):
    """Site decisions 188, the keyboard: the page script (`page.PAGE_JS` `phord`) puts each
    set-phrase section's own blocks, and its untranslated group's apart, in the order the sheet
    draws, and back in the built order (recorded once per block, `_po`) when either class goes;
    run from `ordparDefs`, which the shell calls at a change of a setting and the search page after
    it puts an article on screen. Its behaviour is the browser test's."""
    js = page.PAGE_JS

    def test_a_run_from_ordpar_defs(self):
        i = self.js.index("window.ordparDefs=function(){")
        body = self.js[i:self.js.index("};", i)]
        self.assertIn("phord();", body)

    def test_b_both_classes_decide(self):
        self.assertIn("C.contains('ordpar-levels-on')&&C.contains('ordpar-phraseorder-level')", self.js)

    def test_c_the_levels_in_the_sheets_order(self):
        self.assertIn("var LVO={A1:1,A2:2,B1:3,B2:4,C:5};", self.js)
        self.assertIn("(LVO[a.getAttribute('data-level')]||6)", self.js)     # no level after C

    def test_d_the_built_order_recorded_once_never_re_sorted_text(self):
        self.assertIn("if(bs[0]._po==null)for(i=0;i<bs.length;i++)bs[i]._po=i;", self.js)
        self.assertIn("a._po-b._po", self.js)
        i = self.js.index("function phgrp(")
        self.assertNotIn("textContent", self.js[i:self.js.index("function phord(", i)])

    def test_e_a_sections_own_blocks_and_its_groups_apart(self):
        i = self.js.index("function phord(")
        body = self.js[i:self.js.index("window.ordparDefs=", i)]
        self.assertIn("phgrp(s,lv);var u=kid(s,'ordpar-untr');if(u)phgrp(u,lv);", body)
        self.assertIn("if(s.closest('.ordbok-xmini'))continue;", body)

    def test_f_the_focus_given_back_without_scrolling(self):
        self.assertIn("f.focus({preventScroll:true})", self.js[self.js.index("function phgrp("):])


class TheSoundIcons(unittest.TestCase):

    def test_a_a_levelled_block_is_still_its_own_articles(self):
        # a set phrase's texts are named as its own article's (`audio.mark` reads the blocks): a
        # clip scoped to the phrase's article 1 is found for its term in a block carrying a level
        from ordpar.sitegen import audio
        names = audio.Names(scoped={("-", "ha det", 1): "0123456789abcdef"}, source="x", header=audio.HEADER)
        pg = ('<div class="ordbok ordpar-article" lang="nb"><div class="ordbok-expr" data-level="A2">'
              '<span class="ordbok-expr-term" lang="nb">ha det%s</span></div></div>' % L.box("A2"))
        out, entry, counts = audio.mark(pg, 9, names, expr_ids={"ha det": 1})
        self.assertIn('<span class="ordbok-expr-term" lang="nb" data-a>', out)
        self.assertEqual(counts["expr"], 1)
        self.assertEqual(list(entry.values()), ["0123456789abcdef"])


class Help(unittest.TestCase):

    def test_the_two_sentences(self):
        from ordpar.sitegen import about
        _t, body = about.help_page()
        learners = re.search(r"<strong>Practising your Norwegian: For learners\.</strong>(.*?)</p>", body, re.S)
        self.assertIsNotNone(learners)
        self.assertIn("<em>Order of the set phrases</em>", learners.group(1))
        cefr = re.search(r'<h2 id="cefr-levels">CEFR levels</h2>(.*?)(?:<h2|$)', body, re.S).group(1)
        self.assertIn("<em>Order of the set phrases</em>", cefr)
        self.assertIn("A1 first", cefr)
        comment = _read(ORDPAR, "help.md").split("-->", 1)[0]
        self.assertIn("site decisions 188", comment)
        self.assertRegex(comment, r"DRAFTS? for Robin[^.]*\(site decisions 188")


# ---- rendered pages --------------------------------------------------------------------------

@unittest.skipUnless(L.mirror_path(), "no mirror (ordpar/local-paths.json `mirror`)")
class RenderedPages(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        b = L.builder(True)
        cls.lv = b.levels
        cls.pages = {aid: b.page(aid)["html"] for aid in (24627, 13208)}
        bare = L.builder(False)
        cls.bare = {aid: bare.page(aid)["html"] for aid in (24627, 13208)}

    def test_a_each_block_its_terms_level(self):
        for aid, html in self.pages.items():
            blocks = re.findall(r'<div class="ordbok-expr"(?: data-level="(\w+)")?>\s*'
                                r'<span class="ordbok-expr-term"[^>]*>[^<]*'
                                r'(?:<span class="ordpar-level" data-level="(\w+)")?', html)
            self.assertGreater(len(blocks), 5, aid)
            for on_block, on_box in blocks:
                self.assertEqual(on_block, on_box, aid)
            self.assertIn('class="ordbok-sec ordpar-exprs"', html)

    def test_b_the_order_the_sheet_will_draw(self):
        # the page's order is alphabetical within each group; what level order makes of it
        b = L.builder(True)
        root, lib = b.store.page_library(13208)
        order = [e for e in article.g._expr_order(root["exprs"], lib) if lib.get(e) is not None]
        untr = set(b.untranslated_on_translated.get(13208) or [])
        self.assertTrue(untr and len(untr) < len(order))
        shown = re.findall(r'<div class="ordbok-expr" data-level="(\w+)">', self.pages[13208])
        want = [self.lv[e] for e in order if e not in untr] + [self.lv[e] for e in order if e in untr]
        self.assertEqual(shown, want)

    def test_c_without_levels_as_before(self):
        for aid, html in self.bare.items():
            self.assertNotIn("data-level", html, aid)
            self.assertNotIn("ordpar-exprs", html, aid)
            stripped = re.sub(r'<span class="ordpar-level".*?</span></span>', "", self.pages[aid])
            stripped = re.sub(r' data-level="\w+"(?=>)', "", stripped.replace(" ordpar-exprs\"", "\""))
            self.assertEqual(stripped, html, aid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
