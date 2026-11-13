# -*- coding: utf-8 -*-
"""Site decisions 92 (Robin, 2026-10-22): loading ahead beyond the minis, the setting moved, the
favourites and history pages' script in the shell bundle, smaller offline bundles, and two
faults the 94 build found. Stdlib unittest; `ahead.js` runs under bun (or node) against a stub
DOM, skipped when neither is on PATH. No mirror, library or built file is read.

What it pins:

* **A — loading ahead** (`ordpar/site/ahead.js`): what resting on a node fetches (`aim`): a
  list-view row's article through `ordparSearch.fetchArticle` (key `a<id>`, the key mini.js
  queues its targets under, so one fetch serves both), a link to `/bm-en/<id>/`, `/bm-en/#q=…`
  (the search in the fragment since decisions 104: the page fetched without it, the query only
  looked up in the index — never sent; an old `/bm-en/?q=` link is not fetched ahead at all),
  `/history/`, `/favourites/` or `/settings/` (the page warmed) — since site decisions 180 also
  the front page and About (the rest of 180: `test_ordpar_ahead180.py`) — and nothing for a link
  that leaves the site, opens elsewhere, points at this very page, or is a cross-reference
  mini.js opens a mini for (unless `xref = page`); `mode` (the setting through
  `ordparShell.getSetting`, `page` as `click` under the data saver); `queue` once per key, in
  order; `assetsOf` (the scripts and sheets of a fetched page this page lacks). The wiring:
  mini.js takes the mode and the idle queue from ahead.js, lookup.js `listRows` queues a list's
  articles under `page`, both bundles carry `ahead.js`.
* **B — the setting's place and words**: `minifetch` under section `data`, subsection
  `loading`, its key and values unchanged; the section's new title, the subsection's word, the
  widened labels, the data-saver sentence kept.
* **C** — no code change (the test found the cause elsewhere; the report): the fetches keep
  `credentials: 'omit'`.
* **D** — `personal-page.js` the shell bundle's last part; no page links it on its own.
* **E** — 500 pages to a bundle (`build_offline.PER`); the worker's memory cap 20 MB (`sw.js`
  `KEEP_BYTES`, 40 MB until then).
* **G** — `shell.js` `countOnly` replaces a gloss list once only; the install offer's bar and
  note hidden while the suggestions are open (`shell.css`).
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
sys.path.insert(0, ROOT)

from ordpar import build_offline  # noqa: E402
from ordpar.sitegen import page  # noqa: E402

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


#: A stub DOM: enough of Element for `aim` (closest, classList, getAttribute, parentNode, href,
#: target, hasAttribute), a location, localStorage and navigator.connection.
STUB = r"""
function El(tag, cls, attrs, parent) {
  this.tagName = tag.toUpperCase(); this.cls = (cls || '').split(' ').filter(Boolean);
  this.attrs = attrs || {}; this.parentNode = parent || null; this.target = this.attrs.target || '';
  var me = this;
  this.classList = { contains: function (c) { return me.cls.indexOf(c) !== -1; } };
  if (this.attrs.href != null) { this.href = new URL(this.attrs.href, 'https://ordpar.no/bm-en/#q=hus').href; }
}
El.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
El.prototype.hasAttribute = function (k) { return k in this.attrs; };
El.prototype.matches = function (sel) {
  var me = this;
  return sel.split(',').some(function (one) {
    one = one.trim();
    var m = /^([a-z]*)((?:\.[\w-]+)*)(\[href\])?$/.exec(one);
    if (!m) { return false; }
    if (m[1] && me.tagName !== m[1].toUpperCase()) { return false; }
    if (m[3] && me.attrs.href == null) { return false; }
    return (m[2].match(/\.[\w-]+/g) || []).every(function (c) { return me.classList.contains(c.slice(1)); });
  });
};
El.prototype.closest = function (sel) {
  for (var n = this; n; n = n.parentNode) { if (n.matches && n.matches(sel)) { return n; } }
  return null;
};
var store = {};
globalThis.localStorage = { getItem: function (k) { return k in store ? store[k] : null; } };
globalThis.location = new URL('https://ordpar.no/bm-en/#q=hus');
// defined, not assigned: Node.js (21 and later) has a `navigator` of its own that an assignment
// does not replace, so `navigator.connection` stayed undefined there (found by the run on GitHub)
Object.defineProperty(globalThis, 'navigator', { value: { connection: { saveData: false } },
  configurable: true, writable: true });
var fetched = [];
globalThis.fetch = function (u) { fetched.push(u); return Promise.resolve({ ok: true, text: function () { return Promise.resolve(''); } }); };
globalThis.ordparSearch = { fetchArticle: function (id) { fetched.push('article ' + id); return Promise.resolve({}); } };
"""


class Ahead(unittest.TestCase):
    js = _read(SITE, "ahead.js")

    def setUp(self):
        if not _runner():
            self.skipTest("neither bun nor node on PATH")

    def run_js(self, body):
        return _run(STUB + "\n" + self.js + "\nvar A = globalThis.ordparAhead, res = {};\n"
                    + "(async () => {\n" + body
                    + "\nconsole.log(JSON.stringify(res));})().catch(e => { console.error(e); process.exit(1); });")

    def test_aim(self):
        r = self.run_js(r"""
var key = function (n) { var t = A.aim(n); return t ? t.key : null; };
var row = new El('div', 'ordpar-row', { 'data-id': '24627' });
var head = new El('h3', 'ordpar-row-head', {}, row);
var btn = new El('button', 'ordpar-row-button', {}, head);
res.row = key(new El('span', 'ordpar-row-word', {}, btn));
// an article's own page: the inflected-form row's link (`lookup.js` `articleItem`); the results'
// "Article page" link it stood for until site decisions 168's re-ruling (2026-11-06) is gone
res.article = key(new El('a', 'ordpar-hit-link', { href: '/bm-en/21740/' }));
res.search = key(new El('a', '', { href: '/bm-en/#q=g%C3%A5' }));
res.oldSearch = key(new El('a', '', { href: '/bm-en/?q=g%C3%A5' }));
res.history = key(new El('a', '', { href: '/history/' }));
res.favourites = key(new El('a', '', { href: '/favourites/' }));
res.settings = key(new El('a', '', { href: '/settings/#data' }));
res.about = key(new El('a', '', { href: '/about/' }));
res.front = key(new El('a', '', { href: '/' }));
res.away = key(new El('a', '', { href: 'https://ordbokene.no/' }));
res.blank = key(new El('a', '', { href: '/history/', target: '_blank' }));
res.here = key(new El('a', '', { href: '/bm-en/#q=hus' }));
res.hash = key(new El('a', '', { href: '#def2' }));
var x = new El('span', 'ordbok-xref', {});
var xa = new El('a', 'ordbok-xword', { href: '/bm-en/123/' }, x);
res.noMinis = key(xa);
globalThis.ordparMinis = {};
res.mini = key(xa);
globalThis.ordparShell = { getSetting: function (k) { return k === 'xref' ? 'page' : null; } };
res.xrefPage = key(xa);
var t = A.aim(new El('span', '', {}, btn));
await t.run();
res.fetched = fetched.slice();
// 104: a search warmed from another page fetches the search page without its fragment, and
// looks the query up in the index; from the search page itself, the lookup only
globalThis.ordparLookup = { lookup: function (q) { fetched.push('lookup ' + q); return Promise.resolve(null); } };
fetched.length = 0;
await A.aim(new El('a', '', { href: '/bm-en/#q=g%C3%A5' })).run();
res.warmHere = fetched.slice();
globalThis.location = new URL('https://ordpar.no/history/');
fetched.length = 0;
await A.aim(new El('a', '', { href: '/bm-en/#q=hytte' })).run();
res.warmThere = fetched.slice();
""")
        self.assertEqual(r["row"], "a24627")
        self.assertEqual(r["article"], "/bm-en/21740/")
        self.assertEqual(r["search"], "/bm-en/#q=g%C3%A5")
        self.assertIsNone(r["oldSearch"])                  # its fetch would send the query (104)
        self.assertEqual(r["warmHere"], ["lookup gå"])
        self.assertEqual(r["warmThere"], ["/bm-en/", "lookup hytte"])
        self.assertEqual((r["history"], r["favourites"], r["settings"]),
                         ("/history/", "/favourites/", "/settings/"))
        # site decisions 180 (2026-11-09): the front page and the about-type pages loaded ahead too
        # (their cases: test_ordpar_ahead180.py)
        self.assertEqual((r["about"], r["front"]), ("/about/", "/"))
        for k in ("away", "blank", "here", "hash", "mini"):
            self.assertIsNone(r[k], k)
        self.assertEqual(r["noMinis"], "/bm-en/123/")     # no mini.js on the page: a plain link
        self.assertEqual(r["xrefPage"], "/bm-en/123/")    # `xref = page`: a plain link
        self.assertEqual(r["fetched"], ["article 24627"])

    def test_mode(self):
        r = self.run_js(r"""
res.none = A.mode();
store.minifetch = 'click'; res.stored = A.mode();
store.minifetch = 'junk'; res.junk = A.mode();
store.minifetch = 'page'; res.page = A.mode();
navigator.connection.saveData = true; res.saver = A.mode();
store.minifetch = 'point'; res.saverPoint = A.mode();
navigator.connection.saveData = false;
globalThis.ordparShell = { getSetting: function () { return 'page'; } };
res.shell = A.mode();
""")
        self.assertEqual(r, {"none": "point", "stored": "click", "junk": "point", "page": "page",
                             "saver": "click", "saverPoint": "point", "shell": "page"})

    def test_queue_once_per_key_in_order(self):
        r = self.run_js(r"""
globalThis.requestIdleCallback = function (f) { setTimeout(f, 0); };
var ran = [];
['a1', 'a2', 'a1', 'a3'].forEach(function (k) { A.queue(k, function () { ran.push(k); return Promise.resolve(); }); });
for (var i = 0; i < 200 && ran.length < 3; i++) { await new Promise(function (ok) { setTimeout(ok, 10); }); }
res.ran = ran;
""")
        self.assertEqual(r["ran"], ["a1", "a2", "a3"])

    def test_assets_of_a_page(self):
        r = self.run_js(r"""
globalThis.document = { addEventListener: function () {}, querySelectorAll: function () {
  return [{ getAttribute: function (k) { return k === 'src' ? '/site/shell-pages.js?v=abc1234567' : null; } }]; } };
res.list = A.assetsOf('<link rel="stylesheet" href="/site/shell-pages.css?v=0123456789">'
  + '<script src="/site/shell-pages.js?v=abc1234567"></script><script src="/site/mini.js?v=1111111111" defer></script>'
  + '<link rel="manifest" href="/manifest.webmanifest"><a href="/site/x.js">');
""")
        self.assertEqual(r["list"], ["/site/shell-pages.css?v=0123456789", "/site/mini.js?v=1111111111"])

    def test_one_listener_set_and_the_rest(self):
        self.assertIn("var REST_MS = 150;", self.js)
        self.assertIn("doc.addEventListener('mousemove'", self.js)
        self.assertIn("doc.addEventListener('touchstart'", self.js)
        self.assertIn("{ passive: true }", self.js)
        self.assertIn("credentials: 'omit'", self.js)        # C: unchanged, as the other fetches


class Wiring(unittest.TestCase):
    def test_both_bundles_carry_ahead_js(self):
        self.assertIn(page.AHEAD_JS_HREF, page.ARTICLE_JS_PARTS)
        self.assertIn(page.AHEAD_JS_HREF, page.SHELL_JS_PARTS)
        self.assertLess(page.ARTICLE_JS_PARTS.index(page.AHEAD_JS_HREF),
                        page.ARTICLE_JS_PARTS.index(page.MINI_JS_HREF))

    def test_mini_js_takes_the_mode_and_the_queue(self):
        mini = _read(SITE, "mini.js")
        self.assertIn("if (global.ordparAhead && global.ordparAhead.mode) { return global.ordparAhead.mode(); }", mini)
        self.assertIn("shared('a' + t.id, load.bind(null, t.id))", mini)

    def test_the_list_queues_its_articles_under_page(self):
        lookup = _read(SITE, "lookup.js")
        self.assertIn("if (ahead && ahead.mode && ahead.mode() === 'page') {", lookup)
        self.assertIn("ahead.queue('a' + id, function () { return fetchArticle(id); });", lookup)
        self.assertIn("{ credentials: 'omit' }", lookup)       # C: unchanged

    def test_d_personal_page_js_in_the_shell_bundle(self):
        self.assertEqual(page.SHELL_JS_PARTS[-1], page.PERSONAL_PAGE_JS_HREF)
        self.assertEqual(page.PERSONAL_PAGE_JS_HREF, "/site/personal-page.js")
        for name in ("history.html", "favourites.html"):
            html = _read(SITE, name)
            self.assertNotIn('<script src="/site/personal-page.js">', html, name)
            self.assertIn('<script src="/site/shell-pages.js"></script>', html, name)
        # it does nothing on a page without its marker
        self.assertIn("var main = doc.querySelector('[data-ordpar-personal]');\n    if (!main) { return; }",
                      _read(SITE, "personal-page.js"))


class Setting(unittest.TestCase):
    js = _read(SITE, "shell.js")
    strings = json.loads(_read(SITE, "strings", "en.json"))

    def test_b_moved_with_its_key_and_values(self):
        self.assertIn("{ key: 'minifetch', values: ['point', 'click', 'page'], def: 'point', "
                      "section: 'data', sub: 'loading' }", self.js)
        self.assertEqual(len(re.findall(r"key: 'minifetch'", self.js)), 1)

    def test_b_the_words(self):
        s = self.strings
        self.assertEqual(s["settings.section.data"], "Loading, offline and your data")
        self.assertEqual(s["settings.sub.loading"], "Loading")
        self.assertEqual(s["settings.minifetch"], "When a linked article or page is loaded")
        self.assertEqual(s["settings.minifetch.point"], "When the pointer rests on its link")
        self.assertEqual(s["settings.minifetch.click"], "When its link is clicked")
        self.assertEqual(s["settings.minifetch.page"], "With the page")
        self.assertIn("touch screen", s["settings.minifetch.point.note"])
        self.assertTrue(s["settings.minifetch.page.note"].endswith(
            "With the browser's data saver on, only when the link is clicked."))
        self.assertEqual(s["settings.sub.mini"], "Small articles")    # the others stay


class Bundles(unittest.TestCase):
    def test_e_500_a_bundle(self):
        self.assertEqual(build_offline.PER, 500)
        groups = build_offline.chunk(list(range(1, 1300)), build_offline.PER)
        self.assertEqual([len(g) for _f, g in groups], [500, 500, 299])

    def test_e_the_memory_cap(self):
        sw = _read(ROOT, "ordpar", "root", "sw.js")
        self.assertIn("var KEEP_BYTES = 20e6;", sw)          # 40e6 until decisions 92


class Faults(unittest.TestCase):
    def test_g_count_only_once(self):
        js = _read(SITE, "shell.js")
        body = js.split("function countOnly(g) {")[1].split("\n  }")[0]
        self.assertIn("if (!g.list || g.list.parentNode !== g.side) { return; }", body)
        self.assertIn("g.list.classList.remove('is-pending');", body)

    def test_g_the_install_offer_gives_way_to_the_suggestions(self):
        css = _read(SITE, "shell.css")
        for band in (".ordpar-update-note", ".ordpar-install-bar", ".ordpar-install-note"):
            self.assertIn("html:has(.ordpar-popup:not([hidden])) " + band, css)


if __name__ == "__main__":
    unittest.main()
