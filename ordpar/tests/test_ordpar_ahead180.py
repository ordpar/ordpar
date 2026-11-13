# -*- coding: utf-8 -*-
"""Site decisions 180 (Robin, 2026-11-09): everything that opens an article, a page or a search of
this site loads ahead under `minifetch`, as links have since decisions 92, with the ruled
exceptions. Stdlib unittest; `ahead.js` (and for Random word `lookup.js`) run under bun or node
against a stub DOM, skipped when neither is on PATH. No mirror, library or built file is read.

Robin: "I suggest we make the "random word" button also pre-fetch when the mouse pointer is
hovering for 150 ms", then "Same with the "Similar headwords". Same with everything actually
(unless there are some expections where it makes sense to not pre-fetch)", then, to the
exceptions, "Yes, build it".

What it pins (`ahead.js` `aim`, `warm`, `select`; `lookup.js` `drawAhead`, `wireRandom`):

* **A — the new pages aimed**: the front page `/`, a word or form page `/bm-en/<word>/`
  (percent-encoded, as `pagePath` writes it) with and without `#q=`, an English search
  `/bm-en/#en=<word>`, and the about-type pages by their explicit list; a lab folder of `out/`
  (`/compare-53/`, `/t54/`) and anything else not.
* **B — what they warm from a page that navigates** (`/history/`): a word page its page and its
  word's search (the query never sent: the page is fetched without its fragment); an English
  search the search page and the English lookup, plus the article where the English search opens
  its one match in full; `/` and `/about/` their page; a drawn mark (`&random`) does not stop
  the search.
* **C — a page that answers searches in place** (`ordparShell.answersInPlace()`): a
  search-shaped link warms the search only, never the page HTML it will not navigate to, and the
  articles the search shows in full through `ordparSearch.fetchArticle` (the page's own in-memory
  cache, which its render uses); a bare word-page link still navigates, so its page is warmed.
* **D — the suggestions and Recent rows** (`.ordpar-option[data-q]`, `data-en` for an English
  row): the row's search as its press opens it — in place, or the word page by
  `searchAddress`.
* **E — keyboard selection** (`ordparAhead.select`, called by shell.js `choose`): only after the
  selection has stayed on one row for `REST_MS`; arrowing on sooner loads nothing; `select(null)`
  (the list closed) cancels; under `click` nothing.
* **F — Random word**: resting on the button draws through `ordparSearch.drawAhead` (once per
  click: the key carries the button's draw count) and warms what its click opens, without the
  drawn mark; `lookup.js`'s click takes the pending draw when the direction is unchanged, clears
  it, and draws anew otherwise.
* **G — the exceptions stay `null`**: another site, `target`, `download`, a place on this page,
  the report button, the English/Norwegian switch, an old `?q=` address.
* **H — the double fetch inside an open small article** (the inventory's Doubt (a)): a link
  mini.js opens as a nested mini (`ordparMinis.target`) is left to mini.js under `point` — not
  also fetched by `ahead.js`; under `page`, which mini.js does not rest on, ahead.js loads it
  through mini.js's own `load` (key `a<id>`); a link mini.js does not open (nesting off) is a
  plain page link.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, "ordpar", "site")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run(js):
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "t.js")
        with open(script, "w", encoding="utf-8") as f:
            f.write(js)
        res = subprocess.run([_runner(), script], capture_output=True, timeout=60)
    out = res.stdout.decode("utf-8", "replace")
    if res.returncode != 0:
        raise AssertionError(res.stderr.decode("utf-8", "replace") + out)
    return json.loads(out.strip().splitlines()[-1])


#: A stub DOM: Element enough for `aim` (closest over `tag.class[attr]` lists, classList,
#: getAttribute, hasAttribute, parentNode, href, target), a location, localStorage, fetch
#: recorded, and stand-ins for lookup.js's lookups (recorded by name).
STUB = r"""
function El(tag, cls, attrs, parent) {
  this.tagName = tag.toUpperCase(); this.cls = (cls || '').split(' ').filter(Boolean);
  this.attrs = attrs || {}; this.parentNode = parent || null; this.target = this.attrs.target || '';
  var me = this;
  this.classList = { contains: function (c) { return me.cls.indexOf(c) !== -1; } };
  if (this.attrs.href != null) { this.href = new URL(this.attrs.href, String(globalThis.location)).href; }
}
El.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
El.prototype.hasAttribute = function (k) { return k in this.attrs; };
El.prototype.matches = function (sel) {
  var me = this;
  return sel.split(',').some(function (one) {
    one = one.trim();
    var m = /^([a-z]*)((?:\.[\w-]+)*)((?:\[[\w-]+\])*)$/.exec(one);
    if (!m) { return false; }
    if (m[1] && me.tagName !== m[1].toUpperCase()) { return false; }
    var attrs = (m[3].match(/\[[\w-]+\]/g) || []).map(function (a) { return a.slice(1, -1); });
    if (!attrs.every(function (a) { return a in me.attrs; })) { return false; }
    return (m[2].match(/\.[\w-]+/g) || []).every(function (c) { return me.classList.contains(c.slice(1)); });
  });
};
El.prototype.closest = function (sel) {
  for (var n = this; n; n = n.parentNode) { if (n.matches && n.matches(sel)) { return n; } }
  return null;
};
var store = {};
globalThis.localStorage = { getItem: function (k) { return k in store ? store[k] : null; } };
globalThis.location = new URL('https://ordpar.no/history/');
globalThis.navigator = { connection: { saveData: false } };
var fetched = [];
globalThis.fetch = function (u) { fetched.push(u); return Promise.resolve({ ok: true, text: function () { return Promise.resolve(''); } }); };
var RES = {};
globalThis.ordparLookup = {
  lookup: function (q) { fetched.push('lookup ' + q); return Promise.resolve(RES[q] || null); },
  englishLookup: function (q) { fetched.push('en ' + q);
    return Promise.resolve(q === 'house' ? { count: 1, matches: [{ id: 77 }] } : { count: 2, matches: [{ id: 1 }, { id: 2 }] }); },
  searchAddress: function (q) { return Promise.resolve('/bm-en/' + encodeURIComponent(q) + '/#q=' + encodeURIComponent(q)); },
  englishUrl: function (q) { return '/bm-en/#en=' + encodeURIComponent(q); }
};
globalThis.ordparSearch = { fetchArticle: function (id) { fetched.push('article ' + id); return Promise.resolve({}); } };
var inPlace = false, setting = {};
globalThis.ordparShell = { getSetting: function (k) { return setting[k] || null; },
  answersInPlace: function () { return inPlace; } };
var wait = function (ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); };
"""


def _skip():
    return None if _runner() else "neither bun nor node on PATH"


class Ahead(unittest.TestCase):
    js = _read(SITE, "ahead.js")

    def setUp(self):
        if _skip():
            self.skipTest(_skip())

    def run_js(self, body):
        return _run(STUB + "\n" + self.js + "\nvar A = globalThis.ordparAhead, res = {};\n"
                    + "var key = function (n) { var t = A.aim(n); return t ? t.key : null; };\n"
                    + "var runs = async function (n) { var t = A.aim(n); if (!t) { return null; } fetched.length = 0;"
                    + " await t.run(); await wait(0); return fetched.slice(); };\n"
                    + "var link = function (href, attrs) { var a = Object.assign({ href: href }, attrs || {}); return new El('a', '', a); };\n"
                    + "(async () => {\n" + body
                    + "\nconsole.log(JSON.stringify(res));})().catch(e => { console.error(e); process.exit(1); });")

    def test_a_the_new_pages_aimed(self):
        r = self.run_js(r"""
['/', '/about/', '/coming/', '/changes/', '/dictionary-changes/', '/deck-changes/', '/thanks/',
 '/privacy/', '/help/', '/more/', '/survey/', '/bm-en/hus/', '/bm-en/s%C3%A5/', '/bm-en/s%C3%A5/#q=S%C3%A5',
 '/bm-en/hus/#q=hus', '/bm-en/#en=house', '/compare-53/', '/t54/', '/site/ordpar.js', '/index/random.json',
 '/privacy/#the-survey', '/bm-en/', '/bm-en/hus/#def2']
  .forEach(function (h) { res[h] = key(link(h)); });
res.unicode = key(link('/bm-en/så/'));
""")
        for p in ("/", "/about/", "/coming/", "/changes/", "/dictionary-changes/", "/deck-changes/",
                  "/thanks/", "/privacy/", "/help/", "/more/", "/survey/", "/bm-en/hus/", "/bm-en/s%C3%A5/"):
            self.assertEqual(r[p], p, p)
        self.assertEqual(r["unicode"], "/bm-en/s%C3%A5/")
        self.assertEqual(r["/bm-en/s%C3%A5/#q=S%C3%A5"], "/bm-en/s%C3%A5/#q=S%C3%A5")
        self.assertEqual(r["/bm-en/hus/#q=hus"], "/bm-en/hus/#q=hus")
        self.assertEqual(r["/bm-en/#en=house"], "/bm-en/#en=house")
        self.assertEqual(r["/privacy/#the-survey"], "/privacy/")          # a place on another page: the page
        self.assertEqual(r["/bm-en/hus/#def2"], "/bm-en/hus/")
        for p in ("/compare-53/", "/t54/", "/site/ordpar.js", "/index/random.json", "/bm-en/"):
            self.assertIsNone(r[p], p)

    def test_b_what_they_warm_from_a_page_that_navigates(self):
        r = self.run_js(r"""
res.wordHash = await runs(link('/bm-en/hus/#q=hus'));
res.wordBare = await runs(link('/bm-en/s%C3%A5/'));
res.enOne = await runs(link('/bm-en/#en=house'));
res.enMany = await runs(link('/bm-en/#en=big'));
res.front = await runs(link('/'));
res.about = await runs(link('/about/'));
fetched.length = 0;
await A.warm('/bm-en/fly/#q=fly&random');
res.drawn = fetched.slice();
""")
        self.assertEqual(r["wordHash"], ["/bm-en/hus/", "lookup hus"])
        self.assertEqual(r["wordBare"], ["/bm-en/s%C3%A5/", "lookup så"])
        self.assertEqual(r["enOne"], ["/bm-en/", "en house", "/bm-en/77/"])
        self.assertEqual(r["enMany"], ["/bm-en/", "en big"])
        self.assertEqual(r["front"], ["/"])
        self.assertEqual(r["about"], ["/about/"])
        self.assertEqual(r["drawn"], ["/bm-en/fly/", "lookup fly"])

    def test_c_a_page_that_answers_in_place(self):
        r = self.run_js(r"""
globalThis.location = new URL('https://ordpar.no/bm-en/hus/');
inPlace = true;
RES.fly = { heads: [{ form: 'fly', articles: [{ id: 5 }] }], forms: [] };
res.similar = await runs(link('/bm-en/fly/#q=fly'));
res.search = await runs(link('/bm-en/#q=gå'));
res.english = await runs(link('/bm-en/#en=house'));
res.bare = await runs(link('/bm-en/fly/'));
inPlace = false;
fetched.length = 0;
await A.warm('/bm-en/fly/#q=fly');
res.away = fetched.slice();
""")
        self.assertEqual(r["similar"], ["lookup fly", "article 5"])
        self.assertEqual(r["search"], ["lookup gå"])
        self.assertEqual(r["english"], ["en house", "article 77"])
        self.assertEqual(r["bare"], ["/bm-en/fly/", "lookup fly", "/bm-en/5/"])   # it navigates
        self.assertEqual(r["away"], ["/bm-en/fly/", "lookup fly", "/bm-en/5/"])

    def test_d_the_suggestion_and_recent_rows(self):
        r = self.run_js(r"""
var box = new El('ul', '', { id: 'ordpar-listbox' });
var nb = new El('li', 'ordpar-option is-translated', { 'data-q': 'hus' }, box);
var word = new El('span', 'ordpar-option-word', {}, new El('span', 'ordpar-option-main', {}, nb));
var en = new El('li', 'ordpar-option', { 'data-q': 'big', 'data-en': '' }, box);
var recent = new El('li', 'ordpar-option ordpar-option-recent', { 'data-q': 'gå' }, box);
var bare = new El('li', 'ordpar-option', {}, box);
res.keys = [key(word), key(en), key(recent), key(bare)];
res.nb = await runs(word);
res.en = await runs(en);
res.recent = await runs(recent);
inPlace = true;
res.nbHere = await runs(new El('li', 'ordpar-option', { 'data-q': 'vindu' }, box));
res.enHere = await runs(new El('li', 'ordpar-option', { 'data-q': 'house', 'data-en': '' }, box));
""")
        self.assertEqual(r["keys"][:3], ["opt:nb:hus", "opt:en:big", "opt:nb:gå"])
        self.assertIsNone(r["keys"][3])
        self.assertEqual(r["nb"], ["/bm-en/hus/", "lookup hus"])
        self.assertEqual(r["en"], ["/bm-en/", "en big"])
        self.assertEqual(r["recent"], ["/bm-en/g%C3%A5/", "lookup gå"])
        self.assertEqual(r["nbHere"], ["lookup vindu"])
        self.assertEqual(r["enHere"], ["en house", "article 77"])

    def test_e_keyboard_selection_waits_on_one_row(self):
        r = self.run_js(r"""
var box = new El('ul', '', {});
var rows = ['a', 'b', 'c', 'd'].map(function (q) { return new El('li', 'ordpar-option', { 'data-q': q }, box); });
inPlace = true;
fetched.length = 0;
A.select(rows[0]); await wait(40); A.select(rows[1]); await wait(40); A.select(rows[2]);
await wait(A.REST_MS + 80);
res.paused = fetched.slice();
fetched.length = 0;
A.select(rows[3]); await wait(40); A.select(null); await wait(A.REST_MS + 80);
res.closed = fetched.slice();
store.minifetch = 'click';
A.select(rows[0]); await wait(A.REST_MS + 80);
res.click = fetched.slice();
""")
        self.assertEqual(r["paused"], ["lookup c"])
        self.assertEqual(r["closed"], [])
        self.assertEqual(r["click"], [])

    def test_f_random_word_rested_on(self):
        r = self.run_js(r"""
var draws = 0, words = ['fly', 'hus'];
globalThis.ordparSearch.drawAhead = function (btn) {
  if (!btn.ordparDraw) { btn.ordparDraw = { en: false, word: Promise.resolve(words[draws++]) }; }
  return btn.ordparDraw.word.then(function (w) { return { w: w, en: false }; });
};
var btn = new El('button', 'ordpar-button ordpar-random', { 'data-ordpar-random': '', type: 'button' });
var inner = new El('span', '', {}, btn);
res.key1 = key(inner);
res.first = await runs(inner);
res.again = key(inner);
// the click takes the draw and counts it (lookup.js `wireRandom`): the next rest draws anew
btn.ordparDraw = null; btn.ordparDrawGen = 1;
res.key2 = key(inner);
inPlace = true;
res.second = await runs(inner);
res.draws = draws;
""")
        self.assertEqual(r["key1"], "random:0")
        self.assertEqual(r["first"], ["/bm-en/fly/", "lookup fly"])   # no drawn mark, the search warmed
        self.assertEqual(r["again"], "random:0")
        self.assertEqual(r["key2"], "random:1")
        self.assertEqual(r["second"], ["lookup hus"])
        self.assertEqual(r["draws"], 2)

    def test_b2_a_bundle_two_pages_link_fetched_once(self):
        r = self.run_js(r"""
globalThis.fetch = function (u) { fetched.push(u); return Promise.resolve({ ok: true, text: function () {
  return Promise.resolve(/^\/bm-en\//.test(u) ? '<script src="/site/ordpar.js?v=abc1234567" defer></script>' : 'x'); } }); };
RES.vindu = { heads: [{ form: 'vindu', articles: [{ id: 68472 }] }], forms: [] };
res.got = await runs(new El('li', 'ordpar-option', { 'data-q': 'vindu' }, null));
""")
        self.assertEqual(sorted(r["got"]), ["/bm-en/68472/", "/bm-en/vindu/", "/site/ordpar.js?v=abc1234567",
                                            "lookup vindu"])

    def test_g_the_exceptions_stay_null(self):
        r = self.run_js(r"""
res.away = key(link('https://ordbokene.no/'));
res.awayOwnPath = key(link('https://naob.no/bm-en/hus/'));
res.blank = key(link('/about/', { target: '_blank' }));
res.download = key(link('/about/', { download: '' }));
res.here = key(link('#def2'));
res.self = key(link('/history/'));
res.oldSearch = key(link('/bm-en/?q=hus'));
res.report = key(new El('span', '', {}, new El('button', 'ordpar-button ordpar-report', { type: 'button' })));
res.switch = key(new El('input', '', { id: 'ordpar-en-switch', type: 'checkbox' }));
res.heart = key(new El('button', 'ordpar-fav', { type: 'button' }));
""")
        for k, v in r.items():
            self.assertIsNone(v, k)

    def test_h_a_nested_mini_left_to_mini_js(self):
        r = self.run_js(r"""
var nest = 'second';
globalThis.ordparMinis = {
  target: function (a) { var d = a.closest('.ordbok-xmini') ? 1 : 0; return d && nest === 'off' ? null : { id: 123, depth: d }; },
  load: function (id) { fetched.push('mini ' + id); return Promise.resolve({}); }
};
var mini = new El('div', 'ordbok-xmini', {});
var x = new El('span', 'ordbok-xref', {}, new El('div', 'ordbok-mini-body', {}, mini));
var nested = new El('a', 'ordbok-xword', { href: '/bm-en/123/' }, x);
var top = new El('a', 'ordbok-xword', { href: '/bm-en/123/' }, new El('span', 'ordbok-xref', {}));
res.top = key(top);
res.nested = key(nested);
store.minifetch = 'page';
res.nestedPage = await runs(nested);
res.nestedPageKey = key(nested);
store.minifetch = 'point';
nest = 'off';
res.nestOff = key(nested);
setting.xref = 'page'; nest = 'second';
res.xrefPage = key(nested);
""")
        self.assertIsNone(r["top"])
        self.assertIsNone(r["nested"])                    # point: mini.js loads it, ahead.js not again
        self.assertEqual(r["nestedPageKey"], "a123")
        self.assertEqual(r["nestedPage"], ["mini 123"])
        self.assertEqual(r["nestOff"], "/bm-en/123/")
        self.assertEqual(r["xrefPage"], "/bm-en/123/")


#: lookup.js's Random word under node: a document holding one button, the random list from a
#: stand-in loader, `Math.random` scripted, and the shell's direction and in-place search stubbed.
RANDOM = r"""
const listeners = {};
const btn = { disabled: false, addEventListener: (t, f) => { listeners[t] = f; } };
globalThis.document = { readyState: 'loading', addEventListener() {}, querySelector() { return null; },
  querySelectorAll: s => (s === '[data-ordpar-random]' ? [btn] : []) };
globalThis.location = { href: 'https://x.test/history/', origin: 'https://x.test', pathname: '/history/', search: '', hash: '' };
const L = require(%(lookup)s).ordparLookup, S = require(%(lookup)s).ordparSearch;
let loads = 0;
L.setLoader(name => { loads++; return Promise.resolve(name === 'random.json' ? ['fly', 'hus', 'vindu'] : name === 'random-en.json' ? { n: {} } : null); });
let dir = 'nb', searched = [];
globalThis.ordparShell = { direction: () => dir, equivHidden: () => false,
  search: (q, how) => { searched.push([q, !!(how && how.random)]); return true; } };
let r = [0.1];
Math.random = () => r.shift();
const wait = ms => new Promise(ok => setTimeout(ok, ms));
(async () => {
  const out = {};
  S.wireRandom(globalThis.document);
  out.ahead = await S.drawAhead(btn);           // the rest: 0.1 -> 'fly'
  out.again = await S.drawAhead(btn);           // a second rest before the click: the same draw
  r = [0.9];                                     // were the click to draw, it would be 'vindu'
  listeners.click();
  await wait(20);
  out.clicked = searched.slice();
  out.cleared = btn.ordparDraw == null;
  out.gen = btn.ordparDrawGen;
  // a pending draw made Norwegian, the switch then English: the click does not use it
  searched.length = 0;
  r = [0.5];
  await S.drawAhead(btn);                        // 'hus', Norwegian
  dir = 'en';
  listeners.click();
  await wait(20);
  out.switched = searched.slice();
  out.gen2 = btn.ordparDrawGen;
  // no rest at all: the click draws as before
  dir = 'nb'; searched.length = 0; r = [0.5];
  listeners.click();
  await wait(20);
  out.plain = searched.slice();
  process.stdout.write(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


class RandomDraw(unittest.TestCase):

    def setUp(self):
        if _skip():
            self.skipTest(_skip())

    def test_f_the_click_takes_the_pending_draw(self):
        got = _run(RANDOM % {"lookup": json.dumps(os.path.join(SITE, "lookup.js"))})
        self.assertEqual(got["ahead"], {"w": "fly", "en": False})
        self.assertEqual(got["again"], {"w": "fly", "en": False})
        self.assertEqual(got["clicked"], [["fly", True]])          # still a draw, not a search (115)
        self.assertTrue(got["cleared"])
        self.assertEqual(got["gen"], 1)
        self.assertEqual(got["switched"], [])                       # English drawn (none in the stub), not 'hus'
        self.assertEqual(got["gen2"], 2)
        self.assertEqual(got["plain"], [["hus", True]])


class Wiring(unittest.TestCase):
    """What shell.js and mini.js hand ahead.js (their DOM is pinned in the browser test)."""

    def test_the_rows_carry_their_search(self):
        js = _read(SITE, "shell.js")
        self.assertIn("li.setAttribute('data-q', pickWord(item));", js)
        self.assertGreaterEqual(js.count("setAttribute('data-en', '')"), 2)        # English rows, English Recent rows
        self.assertIn("li.setAttribute('data-q', e.q);", js)

    def test_choose_and_close_tell_ahead_js(self):
        js = _read(SITE, "shell.js")
        self.assertEqual(js.count("aheadSelect("), 3)             # defined, in choose, in close

    def test_mini_js_exposes_its_target(self):
        self.assertIn("target: target,", _read(SITE, "mini.js"))


if __name__ == "__main__":
    unittest.main()
