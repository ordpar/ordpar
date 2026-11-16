#!/usr/bin/env python3
"""Site decisions 82 (Robin, 2026-10-21): one suggestion per article, not per headword form.

Pins, in `build_index.py` (`merge_articles`, `Index.suggest`) and its twin `lookup.js`
(`mergeArticles`, `headLine`, `suggest`): the rows leading to one and the same article merge
into one, in the place of its best-ranked form; a form several articles share keeps its own
"N articles" row and never merges into an article's (that article may also keep a row of its
own); a one-article row carries the article's headword line with the forms continuing what was
typed marked; an "N articles" row carries its articles in the results' order. And, from
`shell.js`, what can be pinned outside a browser: the gloss list's strings and its rule that an
untranslated article is not listed but counted in "+ N more" (decisions 82). And
the row fit (decisions 82, Robin 2026-10-21): shell.js's own `fitRow` run against a
stand-in DOM with fixed widths — the four steps in their order, each taken only as far as the
row needs, a gloss's 8rem floor, the refit giving back what a pending gloss took, an "N articles"
row going straight to the ellipsis — and its wiring (the line fitted before the gloss list,
the refits behind the `seq` check). And the height (site decisions 22, reversed by Robin
2026-10-22: all 20 rows, scrolling; the popup still stopping above a phone's keyboard —
`fitHeight`, `SuggestHeight22`; until then `rowsThatFit` drew only the rows that fit). The real
layout (fonts, how many glosses fit, how many rows) is checked in a browser, not here.

Stdlib unittest; the JavaScript runs under bun (or node), skipped when neither is on PATH.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ORDPAR)

import build_index as B  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _art(aid, lemmas, pos, hg=0):
    """A mirror row with one or more lemmas (`lemmas`: forms in the article's order)."""
    return {"id": aid, "data": {"lemmas": [
        {"lemma": w, "hgno": hg, "paradigm_info": [{"tags": [pos], "inflection": []}]}
        for w in lemmas]}}


ROWS = [
    _art(1, ["dannet", "danna"], "ADJ"),          # one article, two forms (Robin's capture)
    _art(2, ["danne"], "VERB"),
    _art(3, ["dannelse", "danning"], "NOUN"),
    _art(4, ["dann"], "ADV"),
    _art(10, ["bro"], "NOUN", 1),                 # bro: two articles share the form
    _art(11, ["bru", "bro"], "NOUN", 2),          # ... and this one has a form of its own
    _art(20, ["den"], "PRON", 1),
    _art(21, ["den"], "DET", 2),
    _art(22, ["den"], "DET", 3),
]
TRANSLATED = [1, 2, 3, 10, 11, 20, 22]           # dann and den II stay Norwegian only


class Suggest82(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        heads, forms, words = B.build_tables(mirror, None, {})
        B.write_index(cls.tmp, heads, forms, words, TRANSLATED, {})
        cls.idx = B.Index(os.path.join(cls.tmp, "index"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def js(self, body):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        script = os.path.join(self.tmp, "run82.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
%s
""" % (json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(os.path.join(self.tmp, "index")), body))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))

    def sug(self, q):
        return [(s["word"], s["forms"]) for s in self.idx.suggest(q)]

    # ---------------------------------------------------------------- the merge (Python)

    def test_one_row_per_article(self):
        got = self.sug("dann")
        words = [w for w, _ in got]
        self.assertEqual(sorted(words), ["dann", "danna", "danne", "danning"])
        self.assertEqual(dict(got)["danna"], ["danna", "dannet"])
        self.assertEqual(dict(got)["danning"], ["danning", "dannelse"])

    def test_shared_form_keeps_its_row(self):
        got = dict(self.sug("br"))
        self.assertIn("bro", got)                 # the two-article row
        self.assertIn("bru", got)                 # 11's own row, by its own form
        self.assertEqual(got["bru"], ["bru"])     # bro never merged into it
        self.assertEqual(len(got), 2)

    def test_merge_articles_rule(self):
        rows = [{"word": "a", "ids": [1]}, {"word": "b", "ids": [1, 2]}, {"word": "c", "ids": [1]},
                {"word": "d", "ids": [2]}]
        out = B.merge_articles(rows)
        self.assertEqual([(r["word"], r.get("forms")) for r in out],
                         [("a", ["a", "c"]), ("b", None), ("d", ["d"])])

    # ---------------------------------------------------------------- the twin (lookup.js)

    def test_js_matches_python(self):
        qs = ["dann", "danne", "br", "bro", "bru", "de", "den"]
        js = self.js("""Promise.all(%s.map(q => L.suggest(q))).then(rs => process.stdout.write(
  JSON.stringify(rs.map(r => r.map(x => x.word)))));""" % json.dumps(qs))
        self.assertEqual(js, [[s["word"] for s in self.idx.suggest(q)] for q in qs])

    def test_js_head_line_marks_typed_forms(self):
        js = self.js("""Promise.all(['dann', 'dannel', 'bro', 'br'].map(q => L.suggest(q))).then(rs =>
  process.stdout.write(JSON.stringify(rs.map(r => r.map(x => [x.word,
    x.line ? x.line.map(p => (p.match ? '*' : '') + p.w).join(', ') : null])))));""")
        dann, dannel, bro, br = [dict(r) for r in js]
        # site decisions 150 (Robin, 2026-10-29): the row shows the ONE spelling that continues
        # what was typed, the first in the article's own order where several do (until then the
        # whole line, the typed forms marked: "*dannet, *danna")
        self.assertEqual(dann["danna"], "*dannet")
        self.assertEqual(dann["danning"], "*dannelse")
        self.assertEqual(dannel["dannelse"], "*dannelse")
        self.assertIsNone(bro["bro"])             # two articles: no line
        self.assertEqual(br["bru"], "*bru")

    def test_js_shared_row_carries_its_articles(self):
        js = self.js("""L.suggest('den').then(r => process.stdout.write(JSON.stringify(
  r.filter(x => x.word === 'den').map(x => x.articles.map(a => [a.id, a.hg, a.translated])))));""")
        # the results' order: the translated first (I, III), then den II, Norwegian only
        self.assertEqual(js, [[[20, 1, True], [22, 3, True], [21, 2, False]]])

    # ---------------------------------------------------------------- the dropdown (shell.js)

    def test_shell_gloss_list(self):
        js = _read(SITE, "shell.js")
        strings = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(strings["suggest.more"], "+ {n} more")
        self.assertIn("t('suggest.more', { n: rest })", js)
        # an untranslated article is never listed beside a translated one, only counted (Robin,
        # 2026-10-21); since 88's second amendment the rule is shared with the history rows, and
        # since site decisions 144 it is `sideGlosses` (with none translated, the Norwegian
        # definitions), fed by `listedGlosses` (`test_ordpar_similar144.py` runs it)
        self.assertIn("var text = !snips ? '' : a.translated ? glossText(snips, id) : (snips[id] || '');", js)
        self.assertIn("return sideGlosses(articles.map(function (a) {", js)
        self.assertIn("var shown = listedGlosses(g.articles, snips);", js)
        self.assertIn("var rest = g.n - kept;", js)
        # none to list: the plain "N articles"
        self.assertIn("if (!shown.length) { countOnly(g); return; }", js)
        self.assertIn("if (item.line) { drawLine(word, item.line); }", js)
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-option-word .ordpar-option-alt { font-weight: 400; }", css)

    # ---------------------------------------------------------------- the row fit (decisions 82)

    def fit(self, body):
        """Run `body` against shell.js's own `drawLine`, `fitRow` and `sideNeed`, cut out of the
        file and given a stand-in DOM: a character is 8 px, the gaps 8 px, a tag 100 px, 1rem
        16 px (so the floor is 128 px), the row's padding 0."""
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        script = os.path.join(self.tmp, "fit82b.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(FIT_HARNESS % json.dumps(os.path.join(SITE, "shell.js")) + body)
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))

    TWO = "{w: 'dannelsesreise', match: true}, {w: 'danningsreise', match: true}"

    def test_fit_steps_in_order(self):
        # "dannelsesreise, danningsreise" noun + "Norwegian only": 272 + 100 px wanted, the row's
        # room is its width less the gap; each width stops at the first step that fits
        got = self.fit("""out([400, 360, 230, 180].map(W => run(W,
  {word: 'danningsreise', line: [%s], pos: 'noun'}, 'tag')));""" % self.TWO)
        self.assertEqual(got[0], {"fit": None, "word": "dannelsesreise, danningsreise", "pos": True,
                                  "max": "", "cut": False})
        self.assertEqual(got[1], {"fit": "2", "word": "danningsreise", "pos": True, "max": "",
                                  "cut": False})
        self.assertEqual(got[2], {"fit": "3", "word": "danningsreise", "pos": False, "max": "",
                                  "cut": False})
        # step 4: the word cut to what the whole tag leaves (172 - 100)
        self.assertEqual(got[3], {"fit": "4", "word": "danningsreise", "pos": False, "max": "72px",
                                  "cut": True})

    def test_fit_step_one_drops_the_unmatched_and_the_ellipsis(self):
        got = self.fit("""out(run(250, {word: 'brostein', pos: 'noun', line: [{w: 'brustein', match: false},
  {w: 'brostein', match: true}, {w: '\\u2026', match: false}]}, 'tag'));""")
        self.assertEqual(got["fit"], "1")
        self.assertEqual(got["word"], "brostein")
        self.assertTrue(got["pos"])

    def test_fit_gloss_floor(self):
        # a gloss is owed min(its own width, 8rem): 176 px of gloss is owed 128, "it" its 16
        item = "{word: 'kommunestyrerepresentant', pos: 'noun', line: [{w: 'kommunestyrerepresentant', match: true}]}"
        got = self.fit("out([run(380, %s, 'a municipal councillor'), run(360, %s, 'a municipal councillor'),"
                       " run(260, %s, 'it')]);" % (item, item, item))
        self.assertEqual([g["fit"] for g in got], [None, "3", None])

    def test_fit_refit_gives_back(self):
        # pending, the gloss counts as the floor; when it arrives short the full row comes back
        got = self.fit("""var r = row(300, {word: 'kommunestyrerepresentant', pos: 'noun',
  line: [{w: 'kommunestyrerepresentant', match: true}]}, 'pending');
F.fitRow(r.li, r.item); var first = state(r);
r.gloss.textContent = 'it'; r.gloss.classList.remove('is-pending');
F.fitRow(r.li, r.item); out([first, state(r)]);""")
        self.assertEqual(got[0]["fit"], "4")
        self.assertEqual(got[1], {"fit": None, "word": "kommunestyrerepresentant", "pos": True,
                                  "max": "", "cut": False})

    def test_fit_articles_row_only_cuts(self):
        # an "N articles" row has no line and no word class: straight to step 4, against the floor
        got = self.fit("""out([run(150, {word: 'stillestillestille'}, 'list'),
  run(300, {word: 'stille'}, 'list'), run(150, {word: 'stillestillestille'}, 'count')]);""")
        self.assertEqual(got[0], {"fit": "4", "word": "stillestillestille", "pos": None,
                                  "max": "14px", "cut": True})
        self.assertIsNone(got[1]["fit"])
        self.assertEqual(got[2]["max"], "62px")   # a count is kept whole (80 px)

    def test_fit_wiring(self):
        js = _read(SITE, "shell.js")
        # the first fit once the rows are laid out and the popup's height set (site decisions 22,
        # reversed 2026-10-22: every row, scrolling), and only then the glosses asked for; the
        # rows found in the "Norwegian only" group too (decisions 86)
        self.assertIn("""fitHeight(popup);
      Array.prototype.forEach.call(optionRows(), function (li, i) { fitRow(li, items[i]); });
      fillGlosses(glosses);""", js)
        # the line first, against the side's floor, then the gloss list in what it leaves
        self.assertLess(js.index("fitRow(g.row, g.item);                  // the word first"),
                        js.index("fitGlosses(g, shown.length);            // ... then"))
        # the refits happen only inside fillGlosses' answers, after their `seq` check
        # glossText left the closure for the history rows (decisions 88): the body ends at glossList
        body = js[js.index("    function fillGlosses("):js.index("    function glossList(")]
        self.assertEqual(body.count("if (mine !== seq) { return; }"), 2)
        self.assertLess(body.index("if (mine !== seq) { return; }"), body.index("fitRow("))
        self.assertIn("var FIT_FLOOR = 8;", js)
        # the Recent rows take steps 3-4 too
        self.assertIn("fitRow(li, options[i]); });", js)
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-option-main.is-cut .ordpar-option-word {", css)


class SuggestHeight22(unittest.TestCase):
    """Site decisions 22, reversed (Robin, 2026-10-22): the dropdown draws all of `suggest`'s
    rows, up to 20, in a list that scrolls, as ordbokene's — the per-device count of
    2026-10-21 withdrawn. Kept from it ("I agree"): the popup's height stops above a phone's
    on-screen keyboard — shell.js's own `fitHeight` run against a stand-in popup: its height is
    its own (60vh) or, if less, what the VISUAL viewport leaves below its top, less 8 px; never
    under three rows. And the wiring: every row drawn, none cut; the Recent rows uncapped. The
    real layout is checked in a browser, not here."""

    def height(self, body):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "height22.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(HEIGHT_HARNESS % json.dumps(os.path.join(SITE, "shell.js")) + body)
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode != 0:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            return json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_its_own_height_when_there_is_room(self):
        # a 540 px popup (60vh of 900) at 100 px, the visual viewport 900 tall: left as styled
        got = self.height("out([run({h: 540, vv: 900}), run({h: 300, vv: 420})]);")
        self.assertEqual(got, ["", ""])

    def test_stops_above_the_keyboard(self):
        # the visual viewport (a keyboard up) ends 300 px below the popup's top: 292 px; with no
        # visualViewport the window's height is used
        got = self.height("out([run({h: 540, vv: 400}), run({h: 540, vv: null, inner: 400})]);")
        self.assertEqual(got, ["292px", "292px"])

    def test_never_under_three_rows(self):
        # 42 px left: three 35.2 px rows instead (105.6, rounded up)
        got = self.height("out(run({h: 540, vv: 150, row: 35.2}));")
        self.assertEqual(got, "106px")

    def test_an_earlier_cap_is_undone(self):
        got = self.height("out([run({h: 540, vv: 900, was: '120px'}), run({h: 0, vv: 400, was: '120px'}),"
                          " run({h: 540, vv: 400, hidden: true, was: '120px'})]);")
        self.assertEqual(got, ["", "", ""])   # room enough; not laid out; closed

    def test_wiring(self):
        js = _read(SITE, "shell.js")
        self.assertNotIn("rowsThatFit", js)
        self.assertIn("var MIN_ROWS = 3, KEYBOARD_GAP = 8;", js)
        self.assertIn("var vv = global.visualViewport;", js)
        body = js[js.index("    function open(items) {"):js.index("    function openRecent(")]
        # every row drawn: none removed, the options the rows as drawn
        self.assertNotIn("removeChild", body)
        self.assertIn("options = items;", body)
        self.assertLess(body.index("fitHeight(popup);"), body.index("fillGlosses(glosses);"))
        # a resize refits the height and the rows, the list and its place kept
        self.assertIn("var viewport = global.visualViewport || global;", js)
        # moved 2026-10-23 (decisions 86): the Recent rows are capped again on a resize too
        self.assertIn("if (!recentHead.hidden) { fitHeight(popup); return; }", js)
        self.assertIn("if (ranked.length) {", js)
        resize = body[body.index("viewport.addEventListener('resize'"):]
        self.assertNotIn("open(ranked)", resize)
        # the Recent rows: capped above the keyboard as the suggestions are (moved 2026-10-23,
        # decisions 86: "ok (but with a scrolling option here as well)"; until then not capped)
        recent = js[js.index("    function openRecent("):js.index("    function emptyBox(")]
        self.assertIn("fitHeight(popup);", recent)
        self.assertLess(recent.index("popup.hidden = false;"), recent.index("fitHeight(popup);"))
        # `suggest` still returns up to 20, and the popup scrolls at 60vh
        self.assertIn("maxSuggestions: 20,", _read(SITE, "lookup.js"))
        css = _read(SITE, "shell.css")
        pop = css[css.index(".ordpar-popup {"):]
        pop = pop[:pop.index("}")]
        self.assertIn("max-height: 60vh;", pop)
        self.assertIn("overflow-y: auto;", pop)


HEIGHT_HARNESS = r"""const fs = require('fs');
const src = fs.readFileSync(%s, 'utf8');
const from = src.indexOf('    var MIN_ROWS'), to = src.indexOf('    function submit(', from);
if (from < 0 || to < 0) { throw new Error('shell.js: MIN_ROWS .. submit not found'); }
const TOP = 100;
let G = {};
const global = {};
Object.defineProperty(global, 'visualViewport', { get: () => G.vv });
Object.defineProperty(global, 'innerHeight', { get: () => G.inner });
const F = new Function('global', src.slice(from, to) + '; return { fitHeight: fitHeight };')(global);
// a popup at TOP, `h` tall as styled, its first row `row` px
function run(o) {
  G = { vv: o.vv == null ? null : { offsetTop: 0, height: o.vv }, inner: o.inner || 0 };
  const row = { getBoundingClientRect: () => ({ height: o.row || 35.2 }) };
  const popup = { hidden: !!o.hidden, offsetHeight: o.h, style: { maxHeight: o.was || '' },
    getBoundingClientRect: () => ({ top: TOP }), querySelector: () => row };
  F.fitHeight(popup);
  return popup.style.maxHeight;
}
function out(v) { process.stdout.write(JSON.stringify(v)); }
"""


FIT_HARNESS = r"""const fs = require('fs');
const src = fs.readFileSync(%s, 'utf8');
const from = src.indexOf('    function drawLine('), to = src.indexOf('    function submit(', from);
if (from < 0 || to < 0) { throw new Error('shell.js: drawLine .. submit not found'); }
const CH = 8, GAP = 8, REM = 16;
class N {
  constructor(tag, cls, text) {
    this.className = cls || ''; this.children = []; this.text = text == null ? '' : String(text);
    this.hidden = false; this.style = {}; this.attrs = {}; this.clientWidth = 0;
    const me = this;
    this.classList = {
      contains: c => me.className.split(' ').indexOf(c) >= 0,
      add: c => { if (!me.classList.contains(c)) { me.className = (me.className + ' ' + c).trim(); } },
      remove: c => { me.className = me.className.split(' ').filter(x => x && x !== c).join(' '); }
    };
  }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  set textContent(v) { this.children = []; this.text = String(v); }
  appendChild(c) { this.children.push(c); return c; }
  querySelector(sel) {
    for (const k of this.children) {
      if (k.classList.contains(sel.slice(1))) { return k; }
      const r = k.querySelector(sel); if (r) { return r; }
    }
    return null;
  }
  hasAttribute(n) { return n in this.attrs; }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = String(v); }
  removeAttribute(n) { delete this.attrs[n]; }
  width() {
    if (this.hidden) { return 0; }
    if (this.classList.contains('ordpar-option-main')) {
      const vis = this.children.filter(c => !c.hidden);
      const w = vis.reduce((s, c) => s + c.width(), 0) + GAP * Math.max(0, vis.length - 1);
      return this.style.maxWidth ? Math.min(w, parseFloat(this.style.maxWidth)) : w;
    }
    if (this.classList.contains('ordpar-tag')) { return 100; }
    return this.textContent.length * CH;
  }
  getBoundingClientRect() { return { width: this.width() }; }
  get scrollWidth() { return this.width(); }
}
const doc = { createElement: t => new N(t), createTextNode: t => new N('#text', '', t),
  documentElement: {} };
const global = { getComputedStyle: n => n === doc.documentElement ? { fontSize: REM + 'px' }
  : { paddingLeft: '0px', paddingRight: '0px', columnGap: GAP + 'px' } };
const el = (tag, cls, text) => new N(tag, cls, text);
const F = new Function('global', 'doc', 'el', src.slice(from, to)
  + '; return { drawLine: drawLine, fitRow: fitRow };')(global, doc, el);
// a row as `open` draws it; side: 'tag', 'pending', 'list' (a pending gloss list), 'count', or a gloss
function row(W, item, side) {
  const li = el('li', 'ordpar-option'); li.clientWidth = W;
  const main = el('span', 'ordpar-option-main');
  const word = main.appendChild(el('span', 'ordpar-option-word', item.line ? '' : item.word));
  if (item.line) { F.drawLine(word, item.line); }
  const pos = item.pos ? main.appendChild(el('span', 'ordpar-pos', item.pos)) : null;
  const s = el('span', 'ordpar-option-side'); let gloss = null;
  if (side === 'tag') { s.appendChild(el('span', 'ordpar-tag', 'Norwegian only')); }
  else if (side === 'count') { s.appendChild(el('span', 'ordpar-option-count', '2 articles')); }
  else if (side === 'list') { s.appendChild(el('span', 'ordpar-option-glosses is-pending', ' ')); }
  else if (side === 'pending') { gloss = s.appendChild(el('span', 'ordpar-option-gloss is-pending', ' ')); }
  else { gloss = s.appendChild(el('span', 'ordpar-option-gloss', side)); }
  li.appendChild(main); li.appendChild(s);
  return { li: li, item: item, main: main, word: word, pos: pos, gloss: gloss };
}
function state(r) {
  return { fit: r.li.getAttribute('data-fit'), word: r.word.textContent,
    pos: r.pos ? !r.pos.hidden : null, max: r.main.style.maxWidth || '',
    cut: r.main.classList.contains('is-cut') };
}
function run(W, item, side) { const r = row(W, item, side); F.fitRow(r.li, r.item); return state(r); }
function out(v) { process.stdout.write(JSON.stringify(v)); }
"""


if __name__ == "__main__":
    unittest.main()
