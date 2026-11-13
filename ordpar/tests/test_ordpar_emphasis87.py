# -*- coding: utf-8 -*-
"""Decisions 87 and 90 (Robin, 2026-10-22), as built on the site: the sheet, the settings and
the page script. Stdlib unittest; no browser (the browser checks are the build's evidence,
`docs/sessions/2026-09-19-ordpar-site-review/evidence/build-87-90-2026-10-22/`).

* **87 A — the emphasized line.** The setting `emph` = en | no, under Article -> Language, a class
  `ordpar-emph-no` only for `no`; under `en` the English line of a pair is in the main style and its
  partner words are the links, the Norwegian faded and plain — definitions, formula lines and the
  etymology alike, minis too; never under `defs = no`. The default was `en` until site decisions 174
  (Robin, 2026-11-07), `no` since, listed first: the head script now draws `ordpar-emph-no` unless
  `en` is stored, so the state with no class (a page with JavaScript off) is still the English
  emphasized look (`test_ordpar_defaults174.py`).
* **87 B — the examples' look.** Example lists as quote blocks; real subsenses as bullets 1.1em
  in, the bullet in the numerals' colour; compound lists a plain line. Pure CSS, the default.
* **87 C — the layout closer to ordbokene.no.** The setting `layout` = ordpar (default) |
  ordbokene, under Style; an "Example" heading the page script inserts (a real element, its words
  from the strings), the sense's examples flush.
* **90 D — subsenses in English only.** The setting `subsenses` = defs (default) | en, under
  Article -> Language; only under `defs = both` (the mini: unless it shows English alone or
  `defs = no`), never on a formula line or a compound list.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import ordbok_gen  # noqa: E402,F401  -- first: mini imports it back for STYLE
from ordpar.sitegen import article, head, page  # noqa: E402
from ordpar.sitegen.strings import EN  # noqa: E402

SITE = os.path.join(ROOT, "ordpar", "site")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _rules(css):
    """The sheet as (selector list, body) pairs, comments stripped, at-rules' insides included."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@media[^{]*\{", "", css)
    return [(sel.strip(), body.strip()) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


def _bodies_for(css, selector):
    """Every declaration block whose selector list names `selector` exactly."""
    out = []
    for sel, body in _rules(css):
        if selector in [s.strip() for s in sel.split(",")]:
            out.append(body)
    return out


E = "html:not(.ordpar-emph-no):not(.ordpar-defs-no)"
#: decisions 91: every rule reaching a link or peek inside an ARTICLE line pair stops at a mini opened
#: from the line (`page.SITE_CSS`, the 54 block's comment); the mini-pair rules need no such scope
NM = ":where(:not(.ordbok-xmini *))"


class Settings(unittest.TestCase):
    js = _read(SITE, "shell.js")
    strings = json.loads(_read(SITE, "strings", "en.json"))

    TABLE = (("emph", ["no", "en"], "no", "article", "language"),     # site decisions 174: was en | no, en
             ("subsenses", ["defs", "en"], "defs", "article", "language"),
             ("layout", ["ordpar", "ordbokene"], "ordpar", "style", None))

    def test_the_table(self):
        for key, values, default, section, sub in self.TABLE:
            entry = "{ key: '%s', values: [%s], def: '%s', section: '%s'%s }" % (
                key, ", ".join("'%s'" % v for v in values), default, section,
                ", sub: '%s'" % sub if sub else "")
            self.assertIn(entry, self.js)
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        # beside the definitions (after the examples' settings, decisions 111 and 112), before the
        # formula lines and the etymology; the eye's setting under Examples since decisions 131
        self.assertEqual(order[order.index("defs"):order.index("defs") + 9],
                         ["defs", "examples", "exeye", "exlimit", "exmore", "emph", "subsenses", "formulas",
                          "ety"])
        self.assertEqual(order[order.index("lang") + 1], "layout")       # last in Style

    def test_the_words(self):
        for key, values, _d, _s, _sub in self.TABLE:
            self.assertIn("settings." + key, self.strings)
            for v in values:
                self.assertIn("settings.%s.%s" % (key, v), self.strings)
        s = self.strings
        self.assertEqual((s["settings.emph.en"], s["settings.emph.no"]),
                         ("English emphasized", "Norwegian emphasized"))
        self.assertEqual(s["settings.layout.ordbokene"], "Closer to ordbokene.no")
        self.assertEqual(s["settings.subsenses.en"], "In English only")

    def test_the_export_carries_them(self):
        keys = _read(SITE, "personal.js").split("SETTING_KEYS = ")[1].split(";")[0]
        for key, _v, _d, _s, _sub in self.TABLE:
            self.assertIn("'%s'" % key, keys)

    def test_a_class_only_for_the_other_value(self):
        # the default is the state with no class: what a page shows with JavaScript off — but for
        # `emph` since site decisions 174, whose default `no` keeps the class `ordpar-emph-no`, drawn
        # unless the reader stored `en` (the no-class look stays English emphasized)
        for needle in ("s.getItem('emph')!=='en'&&c.add('ordpar-emph-no')",
                       "s.getItem('subsenses')==='en'&&c.add('ordpar-subsen-en')",
                       "s.getItem('layout')==='ordbokene'&&c.add('ordpar-layout-ordbokene')"):
            self.assertIn(needle, head.THEME_JS)
        for needle in ("cl.toggle('ordpar-emph-no', getSetting('emph') === 'no');",
                       "cl.toggle('ordpar-subsen-en', eff('subsenses') === 'en');",
                       "cl.toggle('ordpar-layout-ordbokene', getSetting('layout') === 'ordbokene');"):
            self.assertIn(needle, self.js)
        class_keys = self.js.split("var CLASS_KEYS = ")[1].split(";")[0]
        for key in ("emph", "subsenses", "layout"):
            self.assertIn("'%s'" % key, class_keys)
        # the class keys ask the page to catch up (the headings are inserted only once chosen)
        body = self.js.split("function applyClassKeys() {")[1].split("\n  }\n")[0]
        self.assertIn("global.ordparDefs();", body)


class EmphasizedLine(unittest.TestCase):
    css = page.article_css()

    def test_the_norwegian_emphasized_rules_are_the_base(self):
        self.assertIn(".ordpar-pair>span[lang=en]{color:#757070;font-size:.95em;margin-top:.1em}", self.css)
        self.assertIn(".mini-pair>span[lang=en]{color:#757070;font-size:.95em}", self.css)

    def test_the_english_leads_by_default(self):
        for sel in (E + " .ordpar-pair>span[lang=en]", E + " .mini-pair>span[lang=en]"):
            self.assertIn("color:inherit;font-size:1em", _bodies_for(self.css, sel))
        faded = (E + " .ordpar-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb]",
                 "html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no)"
                 " .ordpar-fml.ordpar-pair>span[lang=nb]",
                 "html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no)"
                 " .ordpar-pair>span.ordbok-body[lang=nb]",
                 E + " .mini-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb]",
                 "html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no)"
                 " .ordpar-fml.mini-pair>span[lang=nb]",
                 "html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no)"
                 " .mini-pair>span.ordbok-body[lang=nb]")
        for sel in faded:
            self.assertIn("color:var(--ordpar-muted,#757070);font-size:.95em", _bodies_for(self.css, sel), sel)
            # its links plain, their peek hidden
            nm = NM if ".ordpar-pair" in sel else ""
            self.assertTrue(any("pointer-events:none" in b for b in _bodies_for(self.css, sel + " .ordbok-xword" + nm)), sel)
            self.assertIn("display:none", _bodies_for(self.css, sel + " .ordbok-xpeek" + nm), sel)

    def test_after_the_base(self):
        i = self.css.index(E + " .ordpar-pair>span[lang=en]")
        self.assertGreater(i, self.css.index(".ordpar-pair>span[lang=en]{color:#757070"))
        self.assertGreater(i, self.css.index(".mini-pair>span[lang=en]{color:#757070"))

    def test_the_english_partner_is_plain_only_where_the_norwegian_leads(self):
        for sel in ("html.ordpar-emph-no:not(.ordpar-defs-en) .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword" + NM,
                    "html.ordpar-defs-no .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword" + NM,
                    "html.ordpar-emph-no:not(.ordpar-mini-en) .mini-pair>span[lang=en] .ordbok-xword",
                    "html.ordpar-defs-no:not(.ordpar-mini-en) .mini-pair>span[lang=en] .ordbok-xword"):
            self.assertTrue(any("pointer-events:none" in b for b in _bodies_for(self.css, sel)), sel)
        # no rule left that makes a partner plain whatever the emphasis
        for sel, _b in _rules(self.css):
            for one in sel.split(","):
                one = one.strip()
                if "span[lang=en]" in one and ("ordbok-xword" in one or "ordbok-xpeek" in one) \
                        and "pointer" not in one:
                    self.assertFalse(one.startswith("html:not(.ordpar-defs-en) ")
                                     or one.startswith("html:not(.ordpar-mini-en) "), one)

    def test_plain_words_keep_the_underline_colour(self):
        # the new and moved plain rules use `text-decoration-line`, so a rule that makes a link
        # live again (84's etymology line, 90's subsenses) keeps the accent's underline colour
        for sel, body in _rules(self.css):
            if "pointer-events:none" in body and "ordbok-xword" in sel and (
                    "emph" in sel or "defs-no" in sel):
                self.assertNotIn("text-decoration:none", body, sel)

    def test_examples_are_never_pairs(self):
        # the swap selects pairs only; an example's lines are `li>span[lang=nb]` + `.ordbok-tr`
        for sel, _b in _rules(self.css):
            if "ordpar-emph" in sel:
                self.assertNotIn("ordbok-ex-list", sel)
                self.assertNotIn("ordbok-tr", sel)


class ExamplesLook(unittest.TestCase):
    css = page.article_css()

    def test_quote_blocks(self):
        self.assertIn(".ordbok-ex-list{margin:.3em 0 .2em 1em;padding-left:.6em;border-left:2px solid #e0d8d9}", self.css)
        self.assertIn(".nightMode .ordbok-ex-list{border-left-color:#656161}", self.css)
        # the subsense bar's own colours (the deck's `.ordbok-sub`)
        self.assertIn("border-left:2px solid #e0d8d9", "".join(_bodies_for(self.css, ".ordbok-sub")))
        self.assertIn(".nightMode .ordbok-sub{border-color:#656161}", self.css)

    def test_bullets_in_the_numerals_colour(self):
        self.assertIn(".ordbok-sub:not(.ordpar-comp){display:list-item;list-style:disc outside;border-left:0;\n"
                      "  padding-left:0;margin-left:1.1em;counter-increment:list-item 0}", self.css)
        # moved 2026-10-23 (decisions 98): the bullet no longer advances the senses' numbers
        numeral = _bodies_for(self.css, ".ordbok-senses>li::marker")
        colour = re.search(r"color:([^;}]+)", numeral[0]).group(1)
        self.assertEqual(_bodies_for(self.css, ".ordbok-sub:not(.ordpar-comp)::marker"), ["color:%s" % colour])
        self.assertIn(".nightMode .ordbok-senses>li::marker", self.css)
        self.assertIn(".nightMode .ordbok-sub:not(.ordpar-comp)::marker{color:#b9b6b6}", self.css)

    def test_compound_list_a_plain_line(self):
        self.assertIn(".ordbok-sub.ordpar-comp{border-left:0;padding-left:0;margin-left:0}", self.css)

    def test_after_the_decks_rules(self):
        self.assertGreater(self.css.index(".ordbok-ex-list{margin:.3em"), self.css.index(".ordbok-ex-list{list-style:none"))
        self.assertGreater(self.css.index(".ordbok-sub:not(.ordpar-comp){display:list-item"),
                           self.css.index(".ordbok-sub{margin:.3em 0 .2em 1em"))


class OrdbokeneLayout(unittest.TestCase):
    css = page.article_css()
    js = page.PAGE_JS

    def test_the_heading_is_hidden_but_under_the_setting(self):
        self.assertIn(".ordpar-exhead{display:none}", self.css)
        body = _bodies_for(self.css, "html.ordpar-layout-ordbokene .ordpar-exhead")[0]
        for decl in ("display:block", "font-size:1em", "font-weight:600", "color:var(--ordpar-accent"):
            self.assertIn(decl, body)

    def test_the_script_inserts_a_real_heading_from_the_strings(self):
        self.assertEqual(EN["example_heading"], "Example")
        self.assertIn('EXH="Example"', self.js)
        self.assertIn("if(!C.contains('ordpar-layout-ordbokene'))return;", self.js)
        self.assertIn("d.createElement(m?'div':'h4')", self.js)
        self.assertIn("window.ordparExHeads=exheads;", self.js)
        self.assertIn("cues();excues();exheads();exmore();infl();", self.js)   # 111, 112 between
        mini = _read(SITE, "mini.js")
        self.assertIn("global.ordparExHeads(box);", mini)
        self.assertLess(mini.index("box.appendChild(cut(art, t.def, slim()));"),
                        mini.index("global.ordparExHeads(box);"))

    def test_the_lists_it_heads_are_the_lists_set_flush(self):
        xl = re.search(r"var XL='([^']*)'\+\s*'([^']*)';", self.js)
        heads = [s.replace("ul.", ".") for s in (xl.group(1) + xl.group(2)).split(",")]
        flush = [s.strip() for s in self.css.split(
            "html.ordpar-layout-ordbokene .ordbok-ex-list{border-left:0;padding-left:0}")[1]
            .split("{margin-left:0}")[0].split(",")]
        self.assertEqual([("html.ordpar-layout-ordbokene " + h) for h in heads], flush[:4])
        self.assertEqual(flush[4], "html.ordpar-layout-ordbokene .ordbok-sub>.ordbok-ex-list")
        # never a set phrase's or a subsense's list: every one starts at a top sense
        for h in heads:
            self.assertNotIn("ordbok-expr", h)
            self.assertNotIn("ordbok-sub", h)

    def test_no_page_ships_it(self):
        self.assertNotIn("ordpar-exhead", _read(ROOT, "ordpar", "sitegen", "article.py"))


class SubsensesInEnglish(unittest.TestCase):
    css = page.article_css()
    A = ("html.ordpar-subsen-en:not(.ordpar-defs-en):not(.ordpar-defs-no) "
         ".ordbok-sub:not(.ordpar-comp)>.ordpar-pair:not(.ordpar-fml)")
    M = ("html.ordpar-subsen-en:not(.ordpar-mini-en):not(.ordpar-defs-no) "
         ".ordbok-sub:not(.ordpar-comp)>.mini-pair:not(.ordpar-fml)")

    def test_the_english_alone_in_the_main_style(self):
        for x in (self.A, self.M):
            self.assertEqual(_bodies_for(self.css, x + ">span[lang=nb]"), ["display:none"])
            self.assertEqual(_bodies_for(self.css, x + ">span[lang=en]"), ["color:inherit;font-size:1em;margin-top:0"])

    def test_its_links_live(self):
        for sel in (self.A + ">span[lang=en] .ordpar-xen>.ordbok-xword" + NM, self.M + ">span[lang=en] .ordbok-xword"):
            self.assertEqual(_bodies_for(self.css, sel),
                             ["text-decoration-line:underline;pointer-events:auto;cursor:pointer"])
        self.assertIn(self.A + ">span[lang=en] .ordpar-xen:hover>.ordbok-xpeek" + NM, self.css)

    def test_a_set_phrases_numbered_senses_are_not_subsenses(self):
        # they are `ol.ordbok-subsenses>li`, never `div.ordbok-sub`
        src = _read(ROOT, "ordpar", "sitegen", "article.py")
        self.assertIn('<ol class="ordbok-senses ordbok-subsenses">', src)
        for sel, _b in _rules(self.css):
            if "ordpar-subsen-en" in sel:
                self.assertNotIn("ordbok-subsenses", sel)


if __name__ == "__main__":
    unittest.main()
