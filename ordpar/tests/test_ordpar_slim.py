# -*- coding: utf-8 -*-
"""Pins the page slimming of 2026-10-20 (the size report's stages 1 and 2,
`docs/sessions/2026-09-19-ordpar-site-review/evidence/reports/site-size-2026-10-20-contractor.md`;
`ordpar/sitegen/slim.py`), what can be pinned outside a browser. The browser comparisons, before
against after, are `docs/sessions/2026-09-19-ordpar-site-review/evidence/site-slim-2026-10-20/`.

* **The comment stripper** (decisions 61: the published scripts and stylesheets ship without
  comments, a small step of our own): comments go, a `/*!` header too; strings, template literals
  (with `${…}` inside), regular expressions and `//` in URLs stay; a comment that spanned lines
  between code stays a line break (ASI). Every script the site serves, stripped, is the same
  program as its source — compared by bun's own transpiler, an independent reader — and no
  shipped script or sheet has a comment left.
* **The island codec**: `slim.compact_paradigm` and `inflection.js` `decode` give back what the
  renderer reads, so every fixture paradigm (ordbokene's captured tables and decisions 40's)
  renders the same tree from the compact island as from the verbatim lemmas; nothing renders ->
  no island; the shape ids are stable and a clash is refused.
* **The inserted chrome**: the header's and footer's script-only links and Random word are not in
  the markup, `shell.js` `addChrome` makes them with the same classes, keys and hrefs, and the
  relabel map (`chrome.RELABEL`, `shell.js` `STATIC_STRINGS`) is one map whose selectors find the
  static elements and whose keys are strings (the shell's, or for the About link the article
  build's `about_link`, in the table the article pages inline); the card foot ships empty and the page script
  makes its controls.
* **The page**: no stamp comment (it is `build.json`'s, and the offline manifest's through
  `build_offline.majority_stamp`), `data-other-entries` only when not 0, `data-snip` only where
  it is not the description, `data-href` only where the mini's headword link is not the target,
  the four unused class tokens gone, one head script / one sheet / one script.
* **Redundant `lang`**: dropped where inherited, kept on `<html>`, the fragment root (which now
  always has one), mini spans and a pair's lines — the only elements the site's sheets and
  scripts select by the attribute (any other `[lang` selector fails here).

Stdlib unittest; the JS parts under bun (or node) when one is on PATH, else skipped."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ordpar.sitegen import article, chrome, face, page, slim  # noqa: E402
from ordpar.sitegen.strings import EN  # noqa: E402
from ordpar import build_offline as BO  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _runner():
    for exe in ("bun", "node"):
        if shutil.which(exe):
            return exe
    return None


def _run_js(body, *args):
    runner = _runner()
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "x.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(body)
        res = subprocess.run([runner, script] + list(args), capture_output=True, timeout=120)
        if res.returncode:
            raise AssertionError(res.stderr.decode("utf-8", "replace")[:2000])
        return res.stdout.decode("utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class StripComments(unittest.TestCase):

    def test_js_cases(self):
        src = r"""/*! a header that goes too */
// a line comment
var url = 'http://example.org/a//b';   // after code
var s = "/* not a comment */ // nor this";
var re = /\/\/x[/*]+\//g, half = a / b / c;   /* inline */ var k = 1;
var t = `x ${ y /* in code */ + `inner // ${z}` } // kept, in the template`;
function f() {
  return /* a comment
  that spans lines */ 42;
}
x = i++ / 2; // division after ++
if (a) /re/.test(b);
"""
        out = slim.strip_js(src)
        self.assertNotIn("header", out)
        self.assertNotIn("a line comment", out)
        self.assertNotIn("after code", out)
        self.assertNotIn("inline", out)
        self.assertNotIn("in code", out)
        self.assertIn("var url = 'http://example.org/a//b';\n", out)
        self.assertIn('var s = "/* not a comment */ // nor this";', out)
        self.assertIn(r"var re = /\/\/x[/*]+\//g, half = a / b / c;", out)
        self.assertNotIn("c;var k", out.replace(" ", "x"))       # the comment's place: whitespace
        self.assertIn(" var k = 1;\n", out)
        self.assertIn("`inner // ${z}` } // kept, in the template`;", out)
        self.assertIn("  return\n42;", out)                 # the line break stays: ASI as before
        self.assertIn("x = i++ / 2;\n", out)
        self.assertIn("if (a) /re/.test(b);", out)
        self.assertFalse(out.startswith("\n"))

    def test_css_cases(self):
        src = '/*! head */\n.a{content:"/* kept */";background:url(http://x/y.png)} /* gone */\n' \
              '.b{margin:0/**/auto}\n/* a\n   block */\n.c{x:1}\n'
        out = slim.strip_css(src)
        self.assertEqual(out, '.a{content:"/* kept */";background:url(http://x/y.png)}\n'
                              '.b{margin:0 auto}\n.c{x:1}\n')

    def test_refuses_its_own_stand_ins(self):
        with self.assertRaises(slim.StripError):
            slim.strip_js("var a = '';")

    def test_every_served_script_is_the_same_program(self):
        # bun's transpiler reads JavaScript on its own; with whitespace minified (which drops
        # comments) the source and the stripped file must give the same text
        files = [os.path.join(SITE, n) for n in sorted(os.listdir(SITE)) if n.endswith(".js")]
        files.append(os.path.join(ORDPAR, "root", "sw.js"))
        pairs = []
        tmp = tempfile.mkdtemp()
        try:
            for k, p in enumerate(files):
                out = os.path.join(tmp, "%d.js" % k)
                with open(out, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(slim.strip_js(_read(p)))
                pairs.append([p, out])
            if _runner() != "bun":
                self.skipTest("needs bun's transpiler")
            got = json.loads(_run_js(r"""
const fs = require('fs');
const t = new Bun.Transpiler({ loader: 'js', minifyWhitespace: true });
const legal = s => s.replace(/\/\*![\s\S]*?\*\//g, '');
const pairs = JSON.parse(process.argv[2]);
console.log(JSON.stringify(pairs.map(([a, b]) => [a,
  legal(t.transformSync(fs.readFileSync(a, 'utf8'))) === legal(t.transformSync(fs.readFileSync(b, 'utf8')))])));
""", json.dumps(pairs)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for name, same in got:
            self.assertTrue(same, name)
        self.assertGreaterEqual(len(got), 8)

    def test_nothing_shipped_keeps_a_comment(self):
        for url in sorted(set(page.GENERATED) | {"/site/" + n for n in os.listdir(SITE)
                                                  if n.endswith((".js", ".css"))}):
            text = page.shipped(url)
            marked = (slim._js_marks if url.endswith(".js") else slim._css_marks)(text)
            self.assertNotIn(slim._GONE, marked, url)
            self.assertNotIn(slim._GONE_NL, marked, url)


class IslandCodec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cases = {}
        for a in json.loads(_read(ORDPAR, "test", "paradigms.json"))["articles"]:
            cases["%s %s" % (a["id"], a["heading"])] = a["lemmas"]
        import test_ordpar_inflection40 as T40
        for k, v in T40.EXTRA.items():
            cases["extra " + k] = v
        cls.cases = cases

    def test_round_trip_renders_the_same(self):
        shapes, compact = {}, {}
        for name, lemmas in self.cases.items():
            compact[name] = json.loads(slim.compact_paradigm({"lemmas": lemmas}, shapes) or "null")
        tmp = tempfile.mkdtemp()
        try:
            data = os.path.join(tmp, "cases.json")
            with open(data, "w", encoding="utf-8") as fh:
                json.dump({"verbatim": self.cases, "compact": compact, "shapes": shapes}, fh)
            out = _run_js(r"""
const fs = require('fs');
function Node(tag) { this.tag = tag; this.attrs = {}; this.children = []; }
Node.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
Node.prototype.getAttribute = function (k) { return this.attrs[k] === undefined ? null : this.attrs[k]; };
Node.prototype.appendChild = function (c) { this.children.push(c); return c; };
function Text(t) { this.text = t; }
const document = { createElement: (t) => new Node(t), createTextNode: (t) => new Text(t),
                   readyState: 'complete', querySelectorAll: () => [] };
const win = { document };
new Function('window', fs.readFileSync(process.argv[2], 'utf8'))(win);
const R = win.ordparInflection;
const ser = (n) => n instanceof Text ? JSON.stringify(n.text)
  : '<' + n.tag + JSON.stringify(n.attrs) + n.children.map(ser).join('') + '>';
const d = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const res = {};
for (const name in d.verbatim) {
  const a = ser(R.render(d.verbatim[name]));
  const c = d.compact[name];
  const b = c === null ? null : ser(R.render(R.decode(c, d.shapes).lemmas));
  res[name] = { same: a === b, tables: (a.match(/<table/g) || []).length, none: c === null };
}
process.stdout.write(JSON.stringify(res));
""", os.path.join(SITE, "inflection.js"), data)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        res = json.loads(out)
        self.assertEqual(len(res), len(self.cases))
        for name, r in res.items():
            if r["none"]:
                self.assertEqual(r["tables"], 0, name)       # no island only where nothing renders
            else:
                self.assertTrue(r["same"], name)
                self.assertGreater(r["tables"], 0, name)

    def test_what_the_island_keeps(self):
        shapes = {}
        data = {"lemmas": [
            {"lemma": "a<b", "hgno": 1, "paradigm_info": [
                {"from": "1996", "to": None, "paradigm_id": 3, "standardisation": "STANDARD",
                 "inflection_group": "NOUN_regular", "tags": ["NOUN", "Masc"],
                 "inflection": [{"tags": [], "word_form": None}, {"tags": ["Sing", "Ind"], "word_form": "a<b"},
                                {"tags": ["Sing", "Def"], "word_form": None}]},
                {"to": "2000", "inflection_group": "X", "tags": [],
                 "inflection": [{"tags": ["Sing"], "word_form": "gone"}]}]},
            {"lemma": "uninflected", "paradigm_info": [
                {"tags": ["ADV"], "inflection_group": "ADV", "inflection": [{"tags": [], "word_form": "u"}]}]}]}
        text = slim.compact_paradigm(data, shapes)
        sid = slim.shape_id([["NOUN", "Masc"], "NOUN_regular", ["Sing+Ind"]])
        self.assertEqual(text, '[["a\\u003cb",["%s","a\\u003cb"]]]' % sid)
        self.assertEqual(shapes, {sid: [["NOUN", "Masc"], "NOUN_regular", ["Sing+Ind"]]})
        self.assertIsNone(slim.compact_paradigm({"lemmas": [data["lemmas"][1]]}, shapes))
        self.assertIsNone(slim.compact_paradigm(None, shapes))
        self.assertEqual(len(sid), slim.SHAPE_ID_LEN)
        self.assertEqual(sid, slim.shape_id([["NOUN", "Masc"], "NOUN_regular", ["Sing+Ind"]]))
        clash = {sid: ["something", "else", []]}
        with self.assertRaises(slim.ShapeClash):
            slim.compact_paradigm(data, clash)

    def test_no_island_and_no_toggle_where_nothing_renders(self):
        self.assertEqual(article.paradigm_block({"lemmas": [{"lemma": "ikke", "paradigm_info": [
            {"tags": ["ADV"], "inflection": [{"tags": [], "word_form": "ikke"}]}]}]}, EN), "")
        block = article.paradigm_block({"lemmas": [{"lemma": "hus", "paradigm_info": [
            {"tags": ["NOUN", "Neuter"], "inflection_group": "NOUN_regular",
             "inflection": [{"tags": ["Sing", "Ind"], "word_form": "hus"}]}]}]}, EN)
        self.assertTrue(block.startswith('  <script type="application/json" id="ordpar-paradigm">[["hus",["'))
        self.assertIn('<details class="ordpar-infl-toggle" hidden><summary>Inflection</summary>', block)

    def test_the_table_goes_into_inflection_js(self):
        saved = dict(article.SHAPES)
        try:
            page.set_shapes({"abcd": [["NOUN"], "G", ["Sing+Ind"]]})
            js = page.source(page.INFLECTION_JS_HREF)
            self.assertIn('var SHAPES = {"abcd":[["NOUN"],"G",["Sing+Ind"]]};', js)
            self.assertIn('"abcd"', page.shipped(page.JS_ALL_HREF))
            self.assertEqual(_read(SITE, "inflection.js").count(page.SHAPES_SLOT), 1)
        finally:
            page.set_shapes(saved)


class InsertedChrome(unittest.TestCase):

    def test_one_relabel_map(self):
        js = _read(SITE, "shell.js")
        block = js.split("var STATIC_STRINGS = [")[1].split("];")[0]
        sels = re.findall(r"\['([^']+)'", block)
        self.assertEqual(sels, [s for s, _k in chrome.RELABEL])
        keys = re.findall(r"\['[^']+', '([^']+)'\]", block)
        self.assertEqual(keys, [k for _s, k in chrome.RELABEL if isinstance(k, str)])
        self.assertIn("'nav.skipArticle' : 'nav.skip'", block)
        strings = json.loads(_read(SITE, "strings", "en.json"))
        merged = chrome.strings()          # what the article pages inline (`page._strings_part`)
        for _s, k in chrome.RELABEL:
            for key in (k if isinstance(k, tuple) else (k,)):
                if key == "about_link":    # the article build's (`strings.py`), not the shell's
                    self.assertNotIn(key, strings)
                    self.assertIn(key, merged)
                else:
                    self.assertIn(key, strings)
        # each selector finds exactly one element of the static chrome
        s = chrome.strings()
        markup = chrome.header(s) + chrome.footer(s)
        for sel, _k in chrome.RELABEL:
            if sel.startswith("."):
                cls = sel[1:].split(" ")[0]
                self.assertEqual(len(re.findall(r'class="%s"' % re.escape(cls), markup)), 1, sel)
        self.assertEqual(markup.count('<label class="ordpar-visually-hidden" for="ordpar-q">'), 1)
        self.assertEqual(markup.count('<nav class="ordpar-footer-nav" aria-label="Site links"><a href="/">'), 1)
        self.assertNotIn("data-ordpar-string", markup)

    def test_add_chrome_makes_what_the_markup_had(self):
        js = _read(SITE, "shell.js")
        body = js.split("function addChrome() {")[1].split("\n  }\n")[0]
        for needle in ("labelled('button', 'ordpar-button is-quiet ordpar-random ordpar-needs-js', 'search.random')",
                       "random.setAttribute('data-ordpar-random', '')",
                       "el('nav', 'ordpar-header-nav ordpar-needs-js')",
                       "nav.setAttribute('aria-label', t('nav.header'))",
                       "labelled('a', 'ordpar-settings-button ordpar-fav-link', 'nav.favourites')",
                       "labelled('a', 'ordpar-settings-button ordpar-settings-link', 'settings.open')",
                       "['settings/', 'footer.settings'], ['favourites/', 'footer.favourites']",
                       "['history/', 'footer.history']", "labelled('a', 'ordpar-needs-js', l[1])",
                       "root.classList.add('ordpar-chrome')"):
            self.assertIn(needle, body)
        # made at once, before the strings' relabel and Random word's wiring
        self.assertLess(js.index("  addChrome();\n"), js.index("function start()"))
        # its words: inline on every page — ordpar.js opens with the strings
        self.assertTrue(page.shipped(page.JS_ALL_HREF).startswith(
            "try{\nwindow.ORDPAR_STRINGS=window.ORDPAR_STRINGS||{};window.ORDPAR_STRINGS.en="))
        self.assertIn('"search.random":"Random word"', page.shipped(page.JS_ALL_HREF))

    def test_room_held_until_it_comes(self):
        css = _read(SITE, "shell.css")
        self.assertIn("html.ordpar-js:not(.ordpar-chrome) .ordpar-header-inner::after {", css)
        self.assertIn("html.ordpar-js .ordpar-card-foot:empty::before,", css)
        # decisions 106: a foot holding only the change notice holds the controls' room too
        self.assertIn("html.ordpar-js .ordpar-card-foot:not(:has(> .ordpar-result-controls))"
                      "::before {", css)
        # the footer's three, between Home and About (2026-10-22): a stand-in placed by `order`
        self.assertIn("html.ordpar-js:not(.ordpar-chrome) .ordpar-footer-nav::before {", css)
        self.assertIn('html.ordpar-js:not(.ordpar-chrome) .ordpar-footer-nav a[href="/about/"] { order: 2; }', css)

    def test_card_foot_made_by_the_page_script(self):
        js = page.PAGE_JS
        # English only: the foot is the interface's (site decisions 152, Robin 2026-11-03)
        self.assertIn("el('button','ordpar-result-btn','ordpar-copy',FOOT.copy);", js)
        self.assertIn("el('span','ordpar-result-copied','ordpar-copied',FOOT.done).setAttribute('role','status');", js)
        self.assertIn("el('button','ordpar-result-btn','ordpar-share',FOOT.share);", js)
        self.assertNotIn("NB.copy", js)
        self.assertIn('FOOT={"copy": "Copy link", "done": "Link copied", "share": "Share"}', js)
        self.assertLess(js.index("foot();"), js.index("var c=d.getElementById('ordpar-copy');"))
        self.assertLess(js.index("foot();"), js.index("P.mountPage("))


def _page(**kw):
    args = dict(aid=13791, lemmas=[{"form": "fange"}],
                article='<div class="ordbok ordpar-article" lang="en"><h1 class="ordpar-hw" lang="nb">'
                        'fange</h1><p lang="en">x</p></div>',
                translated=True, other_entries=0, strings=EN, stamp="ordpar build: t",
                description="to catch", mk=None, personal={"pos": "VERB", "snip": "to catch"})
    args.update(kw)
    return page.render(**args)


class ThePage(unittest.TestCase):

    def test_frame(self):
        html = _page()
        self.assertTrue(html.startswith('<!doctype html>\n<html lang="en" data-article-id="13791" '))
        self.assertNotIn("ordpar build", html)
        self.assertNotIn("data-other-entries", html)
        self.assertIn(' data-other-entries="2"', _page(other_entries=2))
        self.assertNotIn("data-snip", html)                     # = the description
        self.assertIn(' data-snip="a catch"', _page(personal={"snip": "a catch"}))
        self.assertIn(' data-snip=""', _page(personal={"pos": "VERB"}))   # empty, description not
        self.assertNotIn("data-snip", _page(personal={"pos": "VERB"}, description=""))
        self.assertEqual(re.findall(r'<script src="([^"?]+)', html), ["/site/theme.js", "/site/ordpar.js"])
        self.assertEqual(re.findall(r'<link rel="stylesheet" href="([^"?]+)', html), ["/site/ordpar.css"])
        self.assertLess(html.index("/site/theme.js"), html.index("/site/ordpar.css"))
        self.assertIn('<script src="/site/theme.js?v=', html)
        self.assertIn('<script src="/site/ordpar.js?v=', html)
        self.assertNotIn("<script>", html)                     # nothing inline any more
        self.assertIn('<footer class="ordpar-card-foot"></footer>', html)
        self.assertNotIn("\n ", html)                          # no indentation
        for gone in ("ordpar-home", "ordpar-other", "ordpar-mono", "ordbok-xref-hover",
                     "data-ordpar-string", "ordpar-needs-js"):
            self.assertNotIn(gone, html)
        # the About page keeps the stamp, one copy of it on the site
        about = page.about_page("ordpar build: t", EN, page.about_mod.SAMPLE)
        self.assertIn("<!-- ordpar build: t -->", about)
        self.assertEqual(re.findall(r'<script src="([^"?]+)', about), ["/site/theme.js", "/site/ordpar.js"])

    def test_readers_fall_back_to_the_description(self):
        self.assertIn("node.ownerDocument.querySelector('meta[name=\"description\"]')",
                      _read(SITE, "personal.js"))
        out = _run_js("const S = require(%s).ordparSearch;"
                      "process.stdout.write(JSON.stringify([S.extractArticle(%s).meta, S.extractArticle(%s).meta]));"
                      % (json.dumps(os.path.join(SITE, "lookup.js")),
                         json.dumps(_page(description='to "catch"', personal={"snip": 'to "catch"'})),
                         json.dumps(_page(personal={"pos": "VERB"}))))
        a, b = json.loads(out)
        self.assertEqual(a["snip"], 'to "catch"')
        self.assertEqual(b["snip"], "")

    def test_redundant_lang(self):
        html = _page()
        self.assertIn('<html lang="en"', html)
        self.assertIn('<div class="ordbok ordpar-article" lang="en">', html)    # the root keeps it
        self.assertIn('<h1 class="ordpar-hw" lang="nb">', html)
        self.assertIn("<p>x</p>", html)                                          # inherited: gone
        src = ('<html lang="en"><body><div class="ordbok" lang="en"><span class="ordpar-pair">'
               '<span lang="nb">a</span><span lang="en">b</span></span><span lang="en">c</span>'
               '<span class="ordbok-xmini" lang="en"><span lang="en">d</span></span></div></body></html>')
        out, n = slim.drop_redundant_lang(src)
        self.assertEqual(n, 2)
        self.assertIn('<span lang="en">b</span>', out)                       # a pair's line
        self.assertIn('<span class="ordbok-xmini" lang="en"><span>d</span>', out)
        self.assertIn("</span><span>c</span>", out)
        bad = '<html lang="en"><p lang="en"><div lang="en">x</div></p></html>'
        self.assertEqual(slim.drop_redundant_lang(bad), (bad, -1))         # not as the parser reads it

    def test_lang_selectors_are_only_the_pairs(self):
        # the sheets and scripts select by `[lang` only a pair's lines; were there another, the
        # lang pass would need to keep that attribute too (`slim.LANG_SELECTED_CHILDREN_OF`)
        texts = [page.shipped(u) for u in page.GENERATED]
        texts += [page.shipped("/site/" + n) for n in os.listdir(SITE) if n.endswith((".js", ".css"))]
        for text in texts:
            for m in re.finditer(r"([^{}\s,;'\"]+)\[lang=", text):
                # decisions 87, 90 (2026-10-22): a pair's Norwegian line told apart by its class
                # (`span.ordbok-def` / `span.ordbok-body`) and a formula pair excluded — still a
                # pair's child, so still a `lang` the pass keeps
                self.assertRegex(m.group(1), r"\.(ordpar|mini)-pair(:not\(\.ordpar-(open|fml)\))?"
                                             r">span(\.ordbok-(def|body))?$|"
                                             r"\.ordpar-open>span$", m.group(0))

    def test_xref_is_a_plain_link(self):
        # decisions 80 (2026-10-21): no inlined mini, so no `data-href` and no label — the link
        # carries the target's URL itself, and the mini script reads it from `href`
        f = face.SiteFace.__new__(face.SiteFace)
        f.mode, f.minis, f.mini_bytes, f.omit_minis = None, 0, 0, False
        f.current_target_url = "/bm-en/45949/#def2"
        out = f.xref("a1", "<em>x</em>", "p", "")
        self.assertEqual(out, '<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/45949/#def2" '
                              'lang="nb"><em>x</em></a><span class="ordbok-xpeek" lang="en" data-nosnippet>p</span></span>')
        self.assertNotIn("data-href", out)
        self.assertNotIn("xref-hover", f.xref_hover("<em>y</em>", "q", "/bm-en/1/"))
        js = page.PAGE_JS
        self.assertNotIn("label.ordbok-xword", js)
        self.assertNotIn(".mini-hw a", js)


class OfflineStamp(unittest.TestCase):

    def test_stamp_from_build_json(self):
        tmp = tempfile.mkdtemp()
        try:
            d = os.path.join(tmp, "bm-en", "5")
            os.makedirs(d)
            with open(os.path.join(d, "index.html"), "wb") as fh:
                fh.write(b'<!doctype html>\n<html lang="en">\n')
            self.assertIsNone(BO.majority_stamp(tmp, [5]))
            with open(os.path.join(tmp, "build.json"), "w", encoding="utf-8") as fh:
                json.dump({"stamp": "ordpar build: mirror snapshot X · library abc"}, fh)
            self.assertEqual(BO.majority_stamp(tmp, [5]),
                             "ordpar build: mirror snapshot X · library abc".encode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
