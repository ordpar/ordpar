# -*- coding: utf-8 -*-
"""Site decisions 80 and 81 (Robin, 2026-10-21): minis made from the target's own page, and
formula lines. Stdlib unittest; the mini script's example budget runs under bun (or node),
skipped when neither is on PATH. Synthetic rows only: no mirror and no library file are read.

What it pins:

* **80 — the plain link** (`sitegen/face.py`): a cross-reference is `<a class="ordbok-xword"
  href="/bm-en/<id>/[#def<N>]">` and its peek inside `<span class="ordbok-xref">` — no
  checkbox, no backdrop, no mini in the page (`MiniShim.render` draws nothing); a partner word
  is the same link inside `ordbok-xref ordpar-xen`, which the sheet keeps a plain word unless
  the English stands alone.
* **80 — the mini script** (`ordpar/site/mini.js`): shipped in `/site/ordpar.js` after
  `article.js` (whose `place` it uses, `window.ordparPlace`), linked by the search page and the
  404 shell; `lookup.js` lends it its fetch; the deck's example budget (`allocate`).
* **80 — the mini's width on a computer** (Robin, 2026-10-22, the style lab's row 7; row 6's
  32rem until the same day): the sheet's shrink-to-fit rule (12rem floor, the ceiling min(36rem, max(19rem, 50vw), 100vw − 1rem)) under
  the fine-pointer query, after the deck's 19rem; `mini.js` `narrowest` (bun/node) and where
  `fit` runs. The layout itself is measured in a browser, not here.
* **80, 81 — the settings**: `minicontent`, `minispacing`, `miniscroll`, `minifetch` and
  `formulas` in `shell.js`'s table (section *Article*, with their defaults), their words in
  `strings/en.json`, the export's keys (`personal.js`), the head script's and the shell's
  classes on `<html>`, and the sheet's rules for each (variant 5's compact values, the
  scrolling only on a fine pointer that hovers).
* **81 — formula lines** (`sitegen/article.py`): `FORMULA_RE` matches the whole Norwegian
  definition, with or without the colon, and nothing longer; a matching pair carries
  `ordpar-fml`; a compound list's label carries both languages on a translated page, the
  Norwegian one the mirror's intro (or ordbokene's commonest intro by the English label); the
  label upright in every setting (Robin, 2026-10-21, from the style lab); an untranslated page's
  one label Norwegian and its compounds linked since decisions 118 (2026-10-24).
* **84 — the etymology line** (Robin, 2026-10-21): the setting `ety` (en | no | both, default en)
  beside `formulas`, its class on `<html>`, its words, and the sheet's rules over the markup as
  built (`.ordbok-inline>.ordpar-pair`, in a mini `.ordpar-mbody>.mini-pair`) — no page changes.
* **80 — the mini's header on either line** (2026-10-22): a Norwegian word MENTIONED on an English
  line (an etymology's "developed from *hus*") is tagged a Norwegian word with an English peek
  (`face.py` `_partner`, as `xref`); `mini.js` `header` reads the Norwegian face, then the English,
  from a Norwegian line's link, a partner word, a mention and a compound list alike, on a page
  built before the tag fix too (`norwegian`: the `<em>`, not the `lang`; bun/node, a stub DOM).
* **80's findings** (Robin, 2026-10-22): an opened mini always hides its link's peek (the sheet's
  `!important`, finding 1); `ety = both` and `formulas = both` show both lines under `defs = en`
  and `mini = en` too, the link on the Norwegian line (finding 2, amending 84 and 81); the
  Norwegian line's bare links hover the target's headline set (`face.headline_view`, finding 4),
  the deck's `markup.pair_view` untouched.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
#: decisions 91: the scope that keeps an article line's link rules out of a mini opened from the line
NM = ":where(:not(.ordbok-xmini *))"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import ordbok_gen  # noqa: E402,F401  -- first: mini imports it back for STYLE
from ordpar.sitegen import article, face as face_mod, head, page  # noqa: E402
from ordpar.sitegen.strings import EN  # noqa: E402

SITE = os.path.join(ROOT, "ordpar", "site")
markup = face_mod.markup


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _row(rid, no, en, subs=()):
    return {"id": rid, "lemmas": [{"form": "ord%d" % rid}],
            "senses": [{"defn": 1, "ordinal": 1, "no": no, "en": en, "ex": [],
                        "subs": list(subs)}]}


class _Store(object):
    def __init__(self, rows):
        self.library = {r["id"]: r for r in rows}
        self.mirror = {}

    def status(self, aid):
        row = self.library.get(aid)
        return ("en", row) if row else None


class PlainLink(unittest.TestCase):
    T1 = 900001

    def setUp(self):
        targets = [_row(self.T1, ["norsk en"], ["english one"])]
        self.face = face_mod.SiteFace(_Store(targets))
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library({r["id"]: r for r in targets})
        self.face.set_page(7)

    def tearDown(self):
        face_mod.restore(self.saved)

    def test_a_reference_is_a_link_and_its_peek(self):
        out = self.mk.expand('se [ord](/nob/bm/%d#def1 "word")' % self.T1, norwegian=True)
        self.assertIn('<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/%d/#def1" '
                      'lang="nb"><em>ord</em></a><span class="ordbok-xpeek" lang="en" data-nosnippet>word</span>'
                      '</span>' % self.T1, out)
        for gone in ("ordbok-xtog", "ordbok-xback", "ordbok-xmini", 'class="mini', "<label",
                     "data-href"):
            self.assertNotIn(gone, out)
        self.assertEqual((self.face.minis, self.face.mini_bytes), (1, 0))

    def test_the_mini_shim_draws_nothing(self):
        shim = face_mod.MiniShim(self.face)
        self.assertEqual(shim.render({"id": 42}, "gloss", defn=3), "")
        self.assertEqual(self.face.current_target_url, "/bm-en/42/#def3")

    def test_a_partner_is_the_same_link(self):
        row_no = markup.pair_view(_row(7, ['[ord](/nob/bm/%d)' % self.T1],
                                       ['[word](/nob/bm/%d)' % self.T1]), "no")["senses"][0]
        row_en = markup.pair_view(_row(7, ['[ord](/nob/bm/%d)' % self.T1],
                                       ['[word](/nob/bm/%d)' % self.T1]), "en")["senses"][0]
        out = "\n".join(article._unit_inner(row_no, row_en, self.mk, True, EN))
        self.assertIn('<span class="ordbok-xref ordpar-xen"><a class="ordbok-xword" '
                      'href="/bm-en/%d/" lang="en">word</a><span class="ordbok-xpeek" lang="nb" data-nosnippet>'
                      % self.T1, out)

    def test_the_sheet_keeps_a_partner_plain_unless_the_english_leads(self):
        # moved 2026-10-22 (decisions 87): the English leads by default now, so a partner is a
        # plain word only where the Norwegian leads — `emph = no` with both lines shown, or
        # `defs = no` (ordpar/tests/test_ordpar_emphasis87.py pins the rest)
        css = page.article_css()
        # moved 2026-10-22 (decisions 91): each article-line selector stops at a mini opened from
        # the line, `:where(:not(.ordbok-xmini *))` (ordpar/tests/test_ordpar_fixes91.py)
        self.assertIn("html.ordpar-emph-no:not(.ordpar-defs-en) .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword%(nm)s,\n"
                      "html.ordpar-defs-no .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword%(nm)s"
                      "{color:inherit;\n  text-decoration-line:none;pointer-events:none" % {"nm": NM}, css)
        self.assertIn("html.ordpar-defs-no .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xpeek" + NM +
                      "{display:none}", css)
        self.assertNotIn("html:not(.ordpar-defs-en) .ordpar-pair>span[lang=en] .ordpar-xen", css)


class MiniScript(unittest.TestCase):
    def test_shipped_after_the_page_script(self):
        parts = page.ARTICLE_JS_PARTS
        self.assertEqual(parts.index(page.MINI_JS_HREF), parts.index(page.JS_HREF) + 1)
        self.assertIn("window.ordparMinis", page.shipped(page.JS_ALL_HREF))
        self.assertIn("window.ordparPlace=place;", page.PAGE_JS)
        self.assertIn("var M=window.ordparMinis;if(M&&M.scan)M.scan();", page.PAGE_JS)
        for name in ("search.html", "404.html"):
            html = _read(SITE, name)
            self.assertLess(html.index('<script src="/site/article.js" defer></script>'),
                            html.index('<script src="/site/mini.js" defer></script>'), name)

    def test_the_page_script_no_longer_moves_controls(self):
        for gone in ("ordbok-xtog", "data-for", "label.ordbok-xword", "function arm("):
            self.assertNotIn(gone, page.PAGE_JS)

    def test_lookup_lends_its_fetch(self):
        self.assertIn("fetchArticle: fetchArticle,", _read(SITE, "lookup.js"))
        js = _read(SITE, "mini.js")
        self.assertIn("S.fetchArticle(id)", js)
        self.assertIn("parseFromString(html, 'text/html').querySelector('.ordpar-article')", js)

    def test_rules_named_in_the_script(self):
        js = _read(SITE, "mini.js")
        self.assertIn("var EX_BUDGET = 6;", js)
        self.assertIn("var REST_MS = 150;", js)
        self.assertIn("m === 'page' && c && c.saveData ? 'click' : m", js)
        self.assertIn("n.classList.add('mini-pair')", js)          # `mini`, not `defs`, decides
        # depth one until decisions 139 (2026-10-27): a link inside a mini is refused only as the
        # setting `nestminis` says — off; since decisions 147 no limit — `test_ordpar_nestminis147.py`
        self.assertNotIn("if (a.closest('.ordbok-xmini')) { return null; }", js)
        self.assertIn("if (nestMode() === 'off') { return null; }", js)


ALLOCATE = r"""
eval(MINI_JS);
const A = globalThis.ordparMinis.allocate;
process.stdout.write(JSON.stringify({
  one: A([9]), three: A([4, 4, 4]), seven: A([3, 3, 3, 3, 3, 3, 3]), none: A([0, 2, 0]),
  uneven: A([1, 5, 2])}));
"""


class Allocate(unittest.TestCase):
    """`scripts/mini.py` `_allocate_examples`, as the mini script ports it."""

    @classmethod
    def setUpClass(cls):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            raise unittest.SkipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "alloc.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("const MINI_JS = %s;\n%s" % (json.dumps(_read(SITE, "mini.js")), ALLOCATE))
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            cls.out = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_one_unit_takes_the_budget(self):
        self.assertEqual(self.out["one"], [6])

    def test_round_robin(self):
        self.assertEqual(self.out["three"], [2, 2, 2])
        self.assertEqual(self.out["uneven"], [1, 3, 2])

    def test_the_floor_is_never_starved(self):
        self.assertEqual(self.out["seven"], [1] * 7)
        self.assertEqual(self.out["none"], [0, 2, 0])


NARROWEST = r"""
eval(MINI_JS);
const N = globalThis.ordparMinis.narrowest;
// a synthetic layout: lines of `lens` px of text, each wrapping at `w`, 20 px a line
function at(lens) { const seen = []; return [seen, function (w) { seen.push(w);
  return lens.reduce(function (h, n) { return h + 20 * Math.ceil(n / w); }, 0); }]; }
const out = {};
let [s1, f1] = at([150, 100]); out.floor = N(192, 512, f1); out.floorTrials = s1.length;
let [s2, f2] = at([700, 300]); out.mid = N(192, 512, f2);      // 2 + 1 lines at 512; 350 is the narrowest
let [s3, f3] = at([1100]); out.ceil = N(192, 512, f3);         // 3 lines at 512 (367..), 367 the narrowest
let [s4, f4] = at([100]); out.equal = N(304, 304, f4); out.equalTrials = s4.length;
out.tol = N(192, 512, function (w) { return w < 400 ? 101 : 100; });   // within 1 px: the floor
process.stdout.write(JSON.stringify(out));
"""


class MiniWidth(unittest.TestCase):
    """Decisions 80, the style lab's row 7 ("Fit-to-height <=36rem"): the sheet's floor and
    ceiling on a computer, and `mini.js` `narrowest` — the narrowest width with the ceiling's
    height. The layout itself (`fit`) needs a browser: the build's CDP run measures it."""

    @classmethod
    def setUpClass(cls):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            raise unittest.SkipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "narrow.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("const MINI_JS = %s;\n%s" % (json.dumps(_read(SITE, "mini.js")), NARROWEST))
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            cls.out = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_floor_where_it_holds(self):
        self.assertEqual(self.out["floor"], 192)
        self.assertEqual(self.out["floorTrials"], 2)

    def test_the_narrowest_with_the_same_height(self):
        self.assertEqual(self.out["mid"], 350)
        self.assertEqual(self.out["ceil"], 367)

    def test_no_room_no_search(self):
        self.assertEqual(self.out["equal"], 304)
        self.assertEqual(self.out["equalTrials"], 0)

    def test_one_px_of_tolerance(self):
        self.assertEqual(self.out["tol"], 192)

    def test_the_sheet(self):
        css = page.article_css()
        rule = (".ordpar-fmini{width:max-content;min-width:12rem;"
                "max-width:min(36rem,max(19rem,50vw),calc(100vw - 1rem))}")
        self.assertIn("@media (hover:hover) and (pointer:fine){\n  " + rule, css)
        self.assertLess(css.index("width:19rem"), css.index(rule))   # after the deck's, so it wins
        self.assertEqual(css.count("min-width:12rem"), 1)             # a phone keeps the deck's 19rem

    def test_the_script_fits_before_placing(self):
        js = _read(SITE, "mini.js")
        self.assertIn("var FINE = '(hover:hover) and (pointer:fine)';", js)
        self.assertIn("fit(m);                                                  // before placing", js)
        after = js[js.index("box.removeAttribute('aria-busy');"):].splitlines()
        self.assertEqual(after[1].split("//")[0].strip(), "fit(m);")
        # since decisions 139 the fitting is in `fill`, shared by every level: each caller places after
        # it (since 147 through `put`: the first box `place`, a nested one `placeNested`)
        self.assertIn("fill(m, box, art, t);\n      put(c);", js)
        self.assertIn("fill(c.m, box, art, t);\n      put(c);", js)
        self.assertIn("if (chain[0] === c) { place(c.m); } else { placeNested(c); }", js)
        self.assertIn("box.style.width = '';", js)                    # cleared before each run
        self.assertIn("global.addEventListener('resize', refit);", js)
        self.assertIn("attributeFilter: ['class']", js)


SETTINGS = [("formulas", ["both", "en", "no"], "both", "language"),   # site decisions 174: was en | no | both, en
            ("ety", ["en", "no", "both"], "en", "language"),        # decisions 84
            ("minicontent", ["full", "slim"], "full", "mini"),
            # decisions 97 (2026-10-23): the article's spacing the default, `compact` kept
            ("minispacing", ["article", "compact"], "article", "mini"),
            # decisions 114 (2026-10-24): the mini's text sizes, the article's the default
            ("minitext", ["article", "smaller"], "article", "mini"),
            ("miniscroll", ["on", "off"], "on", "mini"),
            # decisions 92 (2026-10-22): moved to "Loading, offline and your data" -> Loading
            ("minifetch", ["point", "click", "page"], "point", "data/loading")]


class Settings(unittest.TestCase):
    js = _read(SITE, "shell.js")
    strings = json.loads(_read(SITE, "strings", "en.json"))

    def test_the_table(self):
        for key, values, default, sub in SETTINGS:
            section, sub = sub.split("/") if "/" in sub else ("article", sub)
            self.assertIn("{ key: '%s', values: [%s], def: '%s', section: '%s', sub: '%s' }"
                          % (key, ", ".join("'%s'" % v for v in values), default, section, sub), self.js)
        # beside "Small articles opened from a cross-reference" (under Small articles since 85);
        # `minifetch` left them for Loading in decisions 92, the last entry of the table
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        i = order.index("mini")
        self.assertEqual(order[i:i + 7], ["mini", "minicontent", "nestminis", "minispacing",
                                          "minitext", "miniscroll", "minihw"])   # 139: nestminis; 147: nestlimit went
        # the last of the table but for the opt-out of decisions 104 (`stats`, data, drawn only with
        # the privacy switch on)
        self.assertEqual(order[-2:], ["minifetch", "stats"])
        # the etymology beside the formula lines (decisions 84)
        i = order.index("formulas")
        self.assertEqual(order[i:i + 2], ["formulas", "ety"])

    def test_the_words(self):
        for key, values, _d, _s in SETTINGS:
            self.assertIn("settings." + key, self.strings)
            for v in values:
                self.assertIn("settings.%s.%s" % (key, v), self.strings)
        self.assertIn("data saver", self.strings["settings.minifetch.page.note"])

    def test_the_export_carries_them(self):
        keys = _read(SITE, "personal.js").split("SETTING_KEYS = ")[1].split(";")[0]
        for key, _v, _d, _s in SETTINGS:
            self.assertIn("'%s'" % key, keys)

    def test_the_classes(self):
        js, shell = head.THEME_JS, self.js
        for needle in ("s.getItem('minicontent')==='slim'&&c.add('ordpar-minicontent-slim')",
                       "s.getItem('minispacing')==='compact'&&c.add('ordpar-minispacing-compact')",   # 97
                       "s.getItem('miniscroll')==='off'&&c.add('ordpar-miniscroll-off')",
                       "(f==='click'||f==='page')&&c.add('ordpar-minifetch-'+f)",
                       # site decisions 174: `both` the default, so its class unless en or no is stored
                       "f=L?'no':s.getItem('formulas');f!=='en'&&c.add('ordpar-formulas-'+(f==='no'?'no':'both'))",
                       # site decisions 152: Norwegian only (`L`) answers for the setting
                       "f=L?'no':s.getItem('ety');(f==='no'||f==='both')&&c.add('ordpar-ety-'+f)"):
            self.assertIn(needle, js)
        for cls in ("ordpar-minicontent-slim", "ordpar-minispacing-compact", "ordpar-miniscroll-off",
                    "ordpar-minifetch-click", "ordpar-minifetch-page", "ordpar-formulas-no",
                    "ordpar-formulas-both", "ordpar-ety-no", "ordpar-ety-both"):
            self.assertIn("cl.toggle('%s'" % cls, shell)
        self.assertIn("if (CLASS_KEYS.indexOf(key) !== -1) { applyClassKeys(); }", shell)

    def test_the_sheet(self):
        css = page.article_css()
        # compact: the style lab's minifit variant 5, a class of its own since decisions 97
        self.assertNotIn("ordpar-minispacing-article", css)
        for rule in ("html.ordpar-minispacing-compact .ordpar-fmini{line-height:1.3;padding:.6rem .75rem}",
                     "html.ordpar-minispacing-compact .ordpar-mbody{margin-top:.35rem}",
                     "html.ordpar-minispacing-compact .ordpar-mbody .ordbok-senses>li{margin-bottom:.3rem}",
                     "gap:.12rem;margin-top:.12rem}",
                     "html.ordpar-minispacing-compact .ordpar-mbody .ordbok-ex-list>li{margin:.05em 0}",
                     ".ordbok-subsenses{margin-top:.35rem;margin-bottom:.2rem}",
                     ".ordpar-mbody{margin-top:.55rem;font-size:1rem}",   # decisions 114: the article's size
                     "html.ordpar-minitext-smaller .ordpar-mbody{font-size:.92rem}"):
            self.assertIn(rule, css)
        scroll = css[css.index("@media (hover:hover) and (pointer:fine){"):]
        self.assertIn("html:not(.ordpar-miniscroll-off) .ordpar-fmini{max-height:min(70vh,30rem);overflow-y:auto;",
                      scroll)
        self.assertIn("overscroll-behavior:contain", scroll)
        self.assertIn(".ordbok-xref.ordpar-mopen>.ordbok-xmini,.ordbok-xref.ordpar-mopen>.ordbok-xback{display:block}",
                      css)


class Formulas(unittest.TestCase):
    MATCH = ["brukt som adverb:", "brukt som adverb", "brukt som adjektiv:", "brukt som substantiv",
             "som adverb:", "som substantiv", "brukt som forsterkende adverb:", "brukt som preposisjon",
             "som subjunksjon:", "brukt som interjeksjon", "brukt i nøytrum:", "brukt i nøytrum",
             "brukt i ikke-tellelig betydning:", "brukt i ikke-tellelig betydning"]
    NOT = ["brukt som forsterkende adverb: svært", "som adjektiv i presens partisipp:",
           "brukt som påpekende pronomen:", "brukt som skjellsord", "i overført betydning:",
           "brukt som forsterkende forledd", "Brukt som adverb:", "brukt som adverb::",
           "brukt  som adverb", "brukt som [adverb](/nob/bm/1)", "som adverb: veldig",
           "brukt som adjektivisk", "brukt i nøytrum flertall"]

    def test_the_pattern(self):
        for s in self.MATCH:
            self.assertTrue(article.FORMULA_RE.match(s), s)
        for s in self.NOT:
            self.assertFalse(article.FORMULA_RE.match(s), s)

    def test_a_unit_is_a_formula_only_whole(self):
        self.assertTrue(article.is_formula({"no": ["brukt som adverb:"]}))
        self.assertFalse(article.is_formula({"no": ["brukt som adverb:", "noe mer"]}))
        self.assertFalse(article.is_formula({"no": []}))

    def test_the_pair_is_marked(self):
        self.assertEqual(article.line_pair("brukt som adverb:", "used as an adverb:", formula=True),
                         '<span class="ordpar-pair ordpar-fml"><span class="ordbok-def" lang="nb">'
                         'brukt som adverb:</span>\n<span class="ordbok-def" lang="en">used as an '
                         'adverb:</span></span>')
        self.assertNotIn("ordpar-fml", article.line_pair("x", "y"))

    def test_the_sheet_decides_per_setting(self):
        css = page.article_css()
        for rule in (
                "html:not(.ordpar-formulas-no):not(.ordpar-formulas-both) .ordpar-fml.ordpar-pair>span[lang=nb]",
                "html.ordpar-formulas-no .ordpar-fml.ordpar-pair>span[lang=en]",
                "html.ordpar-formulas-no .ordpar-fml.mini-pair>span[lang=nb]{display:block}",
                "html.ordpar-defs-no:not(.ordpar-formulas-both) .ordpar-fml.ordpar-pair>.ordpar-encue{display:none}",
                ".ordpar-cl-nb{display:none}", "html.ordpar-formulas-no .ordpar-cl-en{display:none}"):
            self.assertIn(rule, css)


class CompoundLabels(unittest.TestCase):
    BLK = {"label": "as a suffix in words such as:", "intro": "som etterledd i ord som",
           "items": [{"word": "hundehus", "href": "/nob/bm/1", "en": None}]}

    def test_both_labels_on_a_translated_page(self):
        out = article.comp_html(dict(self.BLK, items=[]), markup, True, "en", "som etterledd i ord som")
        self.assertIn('<div class="ordbok-sub ordpar-comp">', out)
        self.assertIn('<span class="ordbok-def"><em><span class="ordpar-cl-en">as a suffix in words such as:</span>'
                      '<span class="ordpar-cl-nb" lang="nb">som etterledd i ord som</span></em>', out)

    def test_one_label_on_an_untranslated_page(self):
        # since decisions 118 (2026-10-24) that one label is the Norwegian one and the compound a
        # link (`comp_html_nb`; until then "<em>used as a suffix in:</em> <em>hundehus</em>");
        # the site face draws the link, stood in for here (`test_ordpar_nbcomp118.py` has the rest)
        class Mk:
            def expand(self, text, norwegian=False, hover_only=False, strict=True):
                return "<a>%s</a>" % text
        out = article.comp_html(self.BLK, Mk(), True, "no")
        self.assertIn("<em>som etterledd i ord som</em> <a>[hundehus](/nob/bm/1)</a>", out)
        self.assertNotIn("used as", out)
        self.assertNotIn("ordpar-cl", out)

    def test_the_norwegian_label(self):
        # since decisions 151 (2026-10-30) the block's own `intro`, verbatim; until then the
        # mirror's intro by alignment (`comp_intros`, gone), else `COMP_NB`
        blk2 = {"label": "for example:", "intro": "for eksempel", "items": []}
        unit = {"defn": 5, "comp": [self.BLK, blk2]}
        self.assertEqual(article.comp_nb_label(unit, 0, self.BLK), "som etterledd i ord som")
        self.assertEqual(article.comp_nb_label(unit, 1, blk2), "for eksempel")
        self.assertEqual(article.comp_nb_label(unit, 0, dict(self.BLK, intro=" som etterledd i ")),
                         "som etterledd i")
        self.assertEqual(article.comp_nb_label(unit, 0, dict(self.BLK, intro="")), "")   # no intro, no label
        # a block derived before 151 (no `intro`): COMP_NB by its old English label
        self.assertEqual(article.comp_nb_label(unit, 0, {"label": "Used as a suffix in:", "items": []}),
                         "som etterledd i ord som")
        self.assertEqual(article.comp_nb_label(unit, 0, {"label": "Also found in compounds:", "items": []}),
                         "i ord som")

    def test_the_intro_from_the_capture(self):
        # the deriver stores the intro as it read it, filled (`f_eks` -> "for eksempel")
        node = {"type_": "compound_list", "intro": {"content": "$", "items": [{"id": "f_eks", "type_": "entity"}]},
                "elements": []}
        blk = article.deck.derive._comp_block(node, {"f_eks": "for eksempel"})
        self.assertEqual((blk["label"], blk["intro"], blk["items"]), ("for example:", "for eksempel", []))

    def test_the_label_is_upright(self):
        # Robin, 2026-10-21 (decisions 81, from the style lab): upright for both languages, in
        # every Formula lines setting; the label is the line's first <em>, the compounds after it
        # (an untranslated page's <em>hundehus</em>) keep the deck's italic
        css = page.article_css()
        rule = ".ordbok .ordpar-comp>.ordbok-def>em:first-child{font-style:normal}"
        self.assertIn(rule, css)
        self.assertGreater(css.index(rule), css.index(".ordbok em{font-style:italic}"))
        self.assertNotIn("ordpar-cl-nb{font-style", css)


class Etymology84(unittest.TestCase):
    """Decisions 84 (Robin, 2026-10-21): the etymology line in one language, as 81's formula
    lines — `ety` = en (default) | no | both, a class on <html>, the sheet alone deciding."""

    def test_the_hook_is_the_markup_as_built(self):
        # no page changes for it: the etymology is the one inline section holding a line pair
        src = _read(ROOT, "ordpar", "sitegen", "article.py")
        self.assertIn("body = ['    ' + line_pair(no_ety, en_ety, cls=\"ordbok-body\")]", src)
        self.assertEqual(src.count("'  <section class=\"ordbok-sec ordbok-inline\">'"), 2)
        self.assertIn("ordbok-nodef", src.split("ordbok-inline", 2)[2][:200])   # the other: no pair
        self.assertEqual(article.line_pair("av norrønt", "from Old Norse", cls="ordbok-body"),
                         '<span class="ordpar-pair"><span class="ordbok-body" lang="nb">av norrønt</span>\n'
                         '<span class="ordbok-body" lang="en">from Old Norse</span></span>')
        # a senseless page's mini: the section's children copied to the body's top level
        mjs = _read(SITE, "mini.js")
        self.assertIn("if (k.tagName !== 'H3') { body.appendChild(k.cloneNode(true)); }", mjs)

    def test_the_sheet_decides_per_setting(self):
        css = page.article_css()
        E = "html:not(.ordpar-ety-no):not(.ordpar-ety-both)"
        for rule in (E + " .ordbok-inline>.ordpar-pair>span[lang=nb],",
                     E + " .ordpar-mbody>.mini-pair>span[lang=nb]{display:none}",
                     E + " .ordpar-mbody>.mini-pair>span[lang=en]{display:block;",
                     "html.ordpar-ety-no .ordbok-inline>.ordpar-pair>span[lang=en],",
                     "html.ordpar-ety-no .ordpar-mbody>.mini-pair>span[lang=nb]{display:block}",
                     "html.ordpar-defs-no:not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>.ordpar-encue{display:none}",
                     E + " .ordbok-inline>.ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword" + NM + ","):  # NM: decisions 91
            self.assertIn(rule, css)
        # after the `defs` and `mini` rules it overrides
        self.assertGreater(css.index(E + " .ordbok-inline"),
                           css.index("html.ordpar-defs-no .ordpar-pair:not(.ordpar-open)>span[lang=en]{display:none}"))
        self.assertGreater(css.index(E + " .ordbok-inline"),
                           css.index("html.ordpar-mini-en .mini-pair>span[lang=nb]{display:none}"))

    def test_the_words(self):
        strings = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual([strings["settings.ety" + k] for k in ("", ".en", ".no", ".both")],
                         ["Etymology", "In English", "In Norwegian", "In Norwegian and English"])


class MentionPartner(unittest.TestCase):
    """A Norwegian word mentioned on the English line of a pair (`{[ord](…)}`, as an English
    etymology's "developed from *hus*") is the Norwegian word with its English peek — tagged so,
    as on the Norwegian line (2026-10-22; it was tagged an English word with a Norwegian peek)."""
    T1 = 900001

    def setUp(self):
        targets = [_row(self.T1, ["norsk en"], ["english one"])]
        self.face = face_mod.SiteFace(_Store(targets))
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library({r["id"]: r for r in targets})
        self.face.set_page(7)

    def tearDown(self):
        face_mod.restore(self.saved)

    def test_the_mention_is_tagged_norwegian(self):
        row = _row(7, ['fra [ord](/nob/bm/%d "word")' % self.T1],
                   ['from {[ord](/nob/bm/%d "word")}' % self.T1])
        no, en = (markup.pair_view(row, side)["senses"][0] for side in ("no", "en"))
        out = "\n".join(article._unit_inner(no, en, self.mk, True, EN))
        self.assertIn('from <span class="ordbok-xref ordpar-xen"><a class="ordbok-xword" '
                      'href="/bm-en/%d/" lang="nb"><em>ord</em></a><span class="ordbok-xpeek" '
                      'lang="en" data-nosnippet>word</span></span>' % self.T1, out)
        self.assertEqual(self.face.matched, 1)


class PeekWithMiniOpen(unittest.TestCase):
    """Decisions 80's finding 1 (Robin, 2026-10-22): an opened mini always hides its link's own
    hover peek. The hiding rule is `!important`, so no showing rule outranks it — the etymology
    line's (84) did, under its default, by specificity — and no rule shows a peek with
    `!important` that could tie it."""

    def test_the_rule_wins_whatever_shows(self):
        css = page.article_css()
        self.assertIn(".ordbok-xref.ordpar-mopen>.ordbok-xpeek{display:none!important}", css)
        shows = re.findall(r"([^{}]*xpeek[^{}]*)\{[^}]*display:\s*block\s*!important", css)
        self.assertEqual(shows, [])

    def test_the_84_rule_is_still_there(self):
        # the rule that outranked the old one: it still shows the English line's peek on hover
        # when the mini is shut, so the fix is the `!important`, not its removal
        self.assertIn(".ordpar-xen:hover>.ordbok-xpeek" + NM + ",", page.article_css())   # NM: decisions 91
        self.assertIn(".mini-pair>span[lang=en] .ordbok-xref:hover>.ordbok-xpeek{display:block}", page.article_css())


class BothInEveryDefs(unittest.TestCase):
    """Decisions 80's finding 2 (Robin, 2026-10-22; amends 84 and 81): `ety = both` and
    `formulas = both` show both lines under `defs = en` too (in a mini, `mini = en`), styled as
    the line pair under `defs = both`, the link on the Norwegian line (54): the English line's
    partner words plain. Under `defs = no` nothing changes (the English behind its reveal)."""

    SHOW = ("html.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=nb]",
            "html.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=nb]",
            "html.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=nb]",
            "html.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=nb]{display:block}")

    def test_the_norwegian_line_shows(self):
        css = page.article_css()
        for rule in self.SHOW:
            self.assertIn(rule, css)
        # after the rules that hide it under `defs = en` / `mini = en` (the more specific
        # selector wins anyway; the order keeps it so if one is ever loosened)
        for hide in ("html.ordpar-defs-en .ordpar-pair>span[lang=nb]{display:none}",
                     "html.ordpar-mini-en .mini-pair>span[lang=nb]{display:none}"):
            self.assertGreater(css.index(self.SHOW[0]), css.index(hide))

    # moved 2026-10-22 (decisions 87): these cells follow the emphasis — the English the muted
    # second line and the link on the Norwegian line only where the Norwegian leads (`emph = no`;
    # in a mini `defs = no` too); under the default the emphasized line's rules
    # (ordpar/tests/test_ordpar_emphasis87.py)
    def test_the_english_line_is_the_muted_second_line(self):
        css = page.article_css()
        self.assertIn("html.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en]"
                      "{margin-top:.1em}", css)
        self.assertIn("html.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en]"
                      "{color:#757070;\n  font-size:.95em}", css)
        self.assertIn("html.nightMode.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>"
                      "span[lang=en]{color:#b9b6b6}", css)
        self.assertIn("html.ordpar-emph-no.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=en],", css)

    def test_the_link_lives_on_the_norwegian_line(self):
        css = page.article_css()
        self.assertIn("html.ordpar-emph-no.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en] "
                      ".ordpar-xen>.ordbok-xword" + NM + ",", css)   # NM: decisions 91
        self.assertIn("html.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en] "
                      ".ordbok-xword{color:inherit;\n  border-bottom:0;text-decoration-line:none;"
                      "pointer-events:none;cursor:auto}", css)
        self.assertIn("html.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en] "
                      ".ordbok-xpeek{display:none}", css)
        self.assertNotIn("html.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en] "
                         ".ordpar-xen>.ordbok-xword", css)

    def test_defs_no_unchanged(self):
        css = page.article_css()
        self.assertIn("html.ordpar-defs-no .ordpar-pair:not(.ordpar-open)>span[lang=en]{display:none}", css)
        self.assertNotIn("ordpar-defs-no.ordpar-ety-both", css)
        self.assertNotIn("ordpar-defs-no.ordpar-formulas-both", css)


class HeadlineSet(unittest.TestCase):
    """Decisions 80's finding 4 (Robin, 2026-10-22): the deck's headline rule (2026-07-22,
    `docs/rendering.md` § Norwegian-visible hovers) extended to the site's Norwegian lines — a
    bare link in a derived-Norwegian definition, subsense or etymology to a target with a
    `summary` hovers the target's whole `summary.gloss`, joined " · "; a `#defN` link, a target
    with no summary and an untitled link keep what they had. Site-side: `MarkupShim.pair_view`
    on the Norwegian side; the deck's `markup.pair_view` is unchanged."""
    T1, T2, T3 = 900001, 900002, 900003

    def setUp(self):
        t1 = _row(self.T1, ["norsk en"], ["english one"])
        t1["summary"] = {"gloss": ["a house", "a building"]}
        t3 = _row(self.T3, ["norsk tre"], ["english three"])
        t3["summary"] = {"gloss": ["three"]}
        targets = [t1, _row(self.T2, ["norsk to"], ["english two"]), t3]
        self.face = face_mod.SiteFace(_Store(targets))
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library({r["id"]: r for r in targets})
        self.face.set_page(7)

    def tearDown(self):
        face_mod.restore(self.saved)

    def _cite(self):
        T1, T2, T3 = self.T1, self.T2, self.T3
        sub = {"defn": 2, "no": ["se [hus](/nob/bm/%d)" % T1], "en": ["see [house](/nob/bm/%d)" % T1]}
        row = _row(7, ["[hus](/nob/bm/%d) og [hus](/nob/bm/%d#def1) og [ord](/nob/bm/%d) og "
                       "[x](/nob/bm/%d)" % (T1, T1, T2, T3)],
                   ["[house](/nob/bm/%d) and [home](/nob/bm/%d#def1) and [word](/nob/bm/%d)"
                    % (T1, T1, T2)], subs=[sub])
        row["etymology"] = {"no": ["av [hus](/nob/bm/%d)" % T1],
                            "en": ["from {[hus](/nob/bm/%d \"house\")}" % T1]}
        return row

    def test_the_rule_and_its_exclusions(self):
        HL = "a house · a building"
        r = self.mk.pair_view(self._cite(), "no")
        sense = markup.links(r["senses"][0]["no"][0])
        self.assertEqual([t for _l, _h, t in sense], [HL, "home", "word", None])  # defN, no summary, untitled (no partner)
        self.assertEqual(markup.links(r["senses"][0]["subs"][0]["no"][0])[0][2], HL)
        self.assertEqual(markup.links(r["etymology"]["no"][0])[0][2], HL)

    def test_the_deck_is_untouched(self):
        row = self._cite()
        self.assertEqual(markup.links(markup.pair_view(row, "no")["etymology"]["no"][0])[0][2], "house")
        self.assertEqual(self.mk.pair_view(row, "en"), markup.pair_view(row, "en"))

    def test_the_peek_on_the_page(self):
        no = self.mk.pair_view(self._cite(), "no")["senses"][0]
        en = markup.pair_view(self._cite(), "en")["senses"][0]
        out = "\n".join(article._unit_inner(no, en, self.mk, True, EN))
        self.assertIn('href="/bm-en/%d/" lang="nb"><em>hus</em></a><span class="ordbok-xpeek" '
                      'lang="en" data-nosnippet>a house · a building</span>' % self.T1, out)

    def test_the_build_takes_the_face(self):
        src = _read(ROOT, "ordpar", "build_site.py")
        self.assertIn('row_no = self.mk.pair_view(root, "no")', src)
        self.assertEqual(_read(ROOT, "ordpar", "sitegen", "article.py").count('mk.pair_view(erow, "no")'), 2)


HEADER = r"""
// a stub DOM: just what `header`, `norwegian` and `kid` touch
function N(tag, cls, kids) {
  const n = { tagName: tag, className: cls || '', childNodes: [], _text: null, href: '' };
  n.classList = { contains: function (c) { return n.className.split(' ').indexOf(c) >= 0; } };
  n.appendChild = function (k) { k.parentNode = n; n.childNodes.push(k); return k; };
  Object.defineProperty(n, 'textContent', {
    get: function () { return n._text !== null ? n._text : n.childNodes.map(function (k) { return k.textContent; }).join(''); },
    set: function (v) { n._text = v; n.childNodes = []; } });
  Object.defineProperty(n, 'firstChild', { get: function () { return n.childNodes[0] || null; } });
  Object.defineProperty(n, 'firstElementChild', { get: function () {
    return n.childNodes.filter(function (k) { return k.tagName; })[0] || null; } });
  Object.defineProperty(n, 'nextSibling', { get: function () {
    const s = n.parentNode ? n.parentNode.childNodes : []; return s[s.indexOf(n) + 1] || null; } });
  Object.defineProperty(n, 'nextElementSibling', { get: function () {
    const s = n.parentNode ? n.parentNode.childNodes.filter(function (k) { return k.tagName; }) : [];
    return s[s.indexOf(n) + 1] || null; } });
  (kids || []).forEach(function (k) { n.appendChild(typeof k === 'string' ? T(k) : k); });
  return n;
}
function T(t) {
  const n = { textContent: t, childNodes: [] };
  Object.defineProperty(n, 'nextSibling', { get: function () {
    const s = n.parentNode.childNodes; return s[s.indexOf(n) + 1] || null; } });
  return n;
}
// createTextNode: the header's text around a faded " · " (site decisions 116)
globalThis.document = { createElement: function (t) { return N(t.toUpperCase()); }, createTextNode: T };
eval(MINI_JS);
const M = globalThis.ordparMinis;
// one cross-reference: <span class="ordbok-xref"><a class="ordbok-xword">WORD</a><span class="ordbok-xpeek">PEEK</span></span>
function xref(word, peek, em) {
  const a = N('A', 'ordbok-xword', [em ? N('EM', '', [word]) : word]);
  N('SPAN', 'ordbok-xref', peek ? [a, N('SPAN', 'ordbok-xpeek', [peek])] : [a]);
  return a;
}
function text(a) { const h = M.header(a, '/bm-en/1/'); return [h.className, h.textContent]; }
const out = {
  norwegianLine: text(xref('bosted', 'place of residence', true)),
  partner: text(xref('place of residence', 'bosted', false)),
  mention: text(xref('hus', 'a house · a building', true)),
  compound: text(xref('hundehus', 'a kennel, a doghouse', true)),
  noPeek: text(xref('hus', '', true)),
  noPeekEnglish: text(xref('home', '', false)),
  mixed: M.norwegian(N('A', 'ordbok-xword', [N('EM', '', ['hus']), ' (I)'])),
};
process.stdout.write(JSON.stringify(out));
"""


class MiniHeader(unittest.TestCase):
    """`mini.js` `header` (2026-10-22): the Norwegian face, an em dash, the English, whichever
    line the link sits on — read from the link's `<em>` (`norwegian`), not from the peek's
    `lang`, which a page built before the tag fix had wrong on an English line's mention."""

    @classmethod
    def setUpClass(cls):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            raise unittest.SkipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "header.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("const MINI_JS = %s;\n%s" % (json.dumps(_read(SITE, "mini.js")), HEADER))
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            cls.out = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_norwegian_line_link(self):
        self.assertEqual(self.out["norwegianLine"], ["mini-head", "bosted — place of residence"])
        self.assertEqual(self.out["compound"], ["mini-head", "hundehus — a kennel, a doghouse"])

    def test_a_partner_word_is_swapped(self):
        self.assertEqual(self.out["partner"], ["mini-head", "bosted — place of residence"])

    def test_a_mention_on_an_english_line_is_not(self):
        self.assertEqual(self.out["mention"], ["mini-head", "hus — a house · a building"])

    def test_no_peek_no_gloss(self):
        self.assertEqual(self.out["noPeek"], ["mini-head", "hus"])
        self.assertEqual(self.out["noPeekEnglish"], ["mini-head", "home"])

    def test_only_a_whole_em_is_norwegian(self):
        self.assertFalse(self.out["mixed"])

    def test_the_dash_is_escaped(self):
        src = _read(SITE, "mini.js")
        self.assertIn("textContent = ' \\u2014 ' + gloss", src)
        code = [ln for ln in src.splitlines() if not ln.lstrip().startswith(("*", "/*", "//"))]
        self.assertEqual([ln for ln in code if "—" in ln], [])


if __name__ == "__main__":
    unittest.main()
