# -*- coding: utf-8 -*-
"""Pins site decisions 89 (Robin, 2026-10-22; brief
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-history-favourites-88b-89-2026-10-22.md`
part B): the favourites page as the list view's rows that open in place.

* **The rows are the list view's** (`lookup.js` `listRows`, exported on `ordparSearch`): a
  disclosure button in a heading, `aria-expanded` / `aria-controls`, the article fetched and
  mounted in the region below (`mountArticle`, with its controls) — on the favourites page with
  `{level: 2, mark: false}`: `<h2>` rows, the article's headword an `<h3>`, no small heart.
  The controls under it have no "Article page" link (site decisions 168, re-ruled 2026-11-06
  (everywhere); until then the test asserted one, as the list view's).
* **The page** (`personal-page.js`): one row per favourite, newest first, the tag kept, the
  stored snippet line shown, a Remove button in each row; a change to the list adds and drops
  rows in place, so an opened article stays open; Remove moves the focus to the next row's.
* **The wiring**: `favourites.html` loads the search page's deferred article scripts; the built
  page stamps them; the history page is unchanged.

`lookup.js`, `personal.js` and `personal-page.js` run under bun (or node) against a small
stand-in DOM (`FakeDom` below) and a stubbed `fetch`. Skipped when neither runner is on PATH.
The layout is checked in a browser, not here."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


FAKE_DOM = r"""
class N {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase(); this.children = []; this.parentNode = null;
    this.attrs = {}; this.text = ''; this.html = null; this.hidden = false; this.listeners = {};
    const me = this;
    this.classList = {
      contains: c => me.className.split(' ').indexOf(c) >= 0,
      add: c => { if (!me.classList.contains(c)) { me.className = (me.className + ' ' + c).trim(); } },
      remove: c => { me.className = me.className.split(' ').filter(x => x && x !== c).join(' '); },
      toggle: (c, on) => { if (on === undefined) { on = !me.classList.contains(c); }
        if (on) { me.classList.add(c); } else { me.classList.remove(c); } return on; }
    };
  }
  get className() { return this.attrs['class'] || ''; }
  set className(v) { this.attrs['class'] = String(v); }
  get id() { return this.attrs.id || ''; }
  set id(v) { this.attrs.id = String(v); }
  get firstChild() { return this.children[0] || null; }
  get lastChild() { return this.children[this.children.length - 1] || null; }
  get nextElementSibling() { const p = this.parentNode; if (!p) { return null; }
    return p.children[p.children.indexOf(this) + 1] || null; }
  get previousElementSibling() { const p = this.parentNode; if (!p) { return null; }
    return p.children[p.children.indexOf(this) - 1] || null; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  set textContent(v) { this.children.forEach(c => { c.parentNode = null; }); this.children = []; this.text = String(v); this.html = null; }
  get innerHTML() { return this.html || ''; }
  set innerHTML(v) { this.textContent = ''; this.html = String(v); }
  appendChild(c) { if (c.parentNode) { c.parentNode.removeChild(c); } c.parentNode = this; this.children.push(c); return c; }
  insertBefore(c, ref) {
    if (!ref) { return this.appendChild(c); }
    if (c.parentNode) { c.parentNode.removeChild(c); }
    const i = this.children.indexOf(ref); this.children.splice(i, 0, c); c.parentNode = this; return c;
  }
  removeChild(c) { this.children = this.children.filter(k => k !== c); c.parentNode = null; return c; }
  contains(n) { while (n) { if (n === this) { return true; } n = n.parentNode; } return false; }
  setAttribute(n, v) { this.attrs[n] = String(v); }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  removeAttribute(n) { delete this.attrs[n]; }
  addEventListener(k, fn) { (this.listeners[k] = this.listeners[k] || []).push(fn); }
  click() { (this.listeners.click || []).forEach(fn => fn({ button: 0, preventDefault() {} })); }
  focus() { doc.activeElement = this; }
  matches1(part) {
    const re = /([a-zA-Z0-9]+)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g; let m, ok = true;
    while ((m = re.exec(part))) {
      if (m[1] && this.tagName !== m[1].toUpperCase()) { ok = false; }
      if (m[2] && !this.classList.contains(m[2])) { ok = false; }
      if (m[3] && (m[4] === undefined ? this.getAttribute(m[3]) === null : this.getAttribute(m[3]) !== m[4])) { ok = false; }
    }
    return ok;
  }
  matches(sel) {
    const parts = sel.trim().split(/\s+/); let node = this;
    if (!node.matches1(parts[parts.length - 1])) { return false; }
    for (let i = parts.length - 2; i >= 0; i--) {
      node = node.parentNode;
      while (node && !(node.matches1 && node.matches1(parts[i]))) { node = node.parentNode; }
      if (!node) { return false; }
    }
    return true;
  }
  querySelectorAll(sel) {
    const out = [];
    const walk = n => n.children.forEach(k => { if (k.matches(sel)) { out.push(k); } walk(k); });
    walk(this); return out;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
const doc = new N('#document');
doc.createElement = t => new N(t);
doc.createElementNS = (ns, t) => new N(t);
doc.createTextNode = t => { const n = new N('#text'); n.text = String(t); return n; };
doc.readyState = 'complete';
doc.activeElement = null;
doc.addEventListener = () => {};
doc.documentElement = new N('html');
doc.body = doc.appendChild(new N('body'));
globalThis.document = doc;
"""

HARNESS = FAKE_DOM + r"""
const fs = require('fs');
const store = {};
globalThis.localStorage = { getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
const STR = JSON.parse(fs.readFileSync(%(strings)s, 'utf8'));
const shellFns = [];
globalThis.ordparShell = { t: k => (k in STR ? STR[k] : k), ready: Promise.resolve(),
  onChange: fn => { shellFns.push(fn); }, getSetting: () => 'multi' };
const fetched = [];
const PAGE = id => '<!doctype html><html lang="nb" data-snip="snippet ' + id + '"><body>'
  + '<main><div class="ordbok"><h1 class="ordpar-hw">word ' + id + '</h1>'
  + '<h3 lang="en">Meaning</h3></div><footer class="ordpar-card-foot"></footer></main></body></html>';
globalThis.fetch = url => { fetched.push(url); const id = /\/(\d+)\/$/.exec(url)[1];
  return Promise.resolve({ ok: true, text: () => Promise.resolve(PAGE(id)) }); };
const P = require(%(personal)s);
globalThis.ordparPersonal = P;
const M = require(%(lookup)s), S = M.ordparSearch;
const tick = () => new Promise(r => setTimeout(r, 20));
function rowInfo(r) {
  const head = r.children[0], btn = head.children[0];
  const snip = r.querySelector('.ordpar-row-snippet');
  const panel = r.querySelector('.ordpar-row-panel');
  return { cls: r.className, id: r.getAttribute('data-id'), head: head.tagName,
    expanded: btn.getAttribute('aria-expanded'), controls: btn.getAttribute('aria-controls'),
    word: r.querySelector('.ordpar-row-word').textContent,
    tag: (r.querySelector('.ordpar-tag') || {}).textContent || '',   // decisions 137: a translated row has none
    mark: !!r.querySelector('.ordpar-fav-mark'),
    snip: snip ? snip.textContent : null, pending: snip ? snip.classList.contains('is-pending') : null,
    remove: r.querySelector('.ordpar-fav-remove') ? r.querySelector('.ordpar-fav-remove').getAttribute('aria-label') : null,
    open: panel ? !panel.hidden : null, html: panel ? panel.innerHTML : null,
    region: panel ? panel.getAttribute('role') + ':' + panel.getAttribute('aria-labelledby') : null };
}
function out(v) { process.stdout.write(JSON.stringify(v)); }
"""

FAVS = [
    {"id": 7, "word": "hus", "hg": 0, "pos": "NOUN", "translated": True,
     "snip": "a house · a building", "t": 3},
    {"id": 8, "word": "stille", "hg": 2, "pos": "NOUN", "translated": False,
     "snip": "ro, taushet", "t": 2},
    {"id": 9, "word": "kjapp", "hg": 0, "pos": "ADJ", "translated": False, "snip": "", "t": 1},
]


class Favourites89(unittest.TestCase):

    def js(self, body):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "run89.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(HARNESS % {
                    "lookup": json.dumps(os.path.join(SITE, "lookup.js")),
                    "personal": json.dumps(os.path.join(SITE, "personal.js")),
                    "strings": json.dumps(os.path.join(SITE, "strings", "en.json")),
                })
                fh.write("(async () => { " + body + " })().catch(e => { console.error(e); process.exit(1); });\n")
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode != 0:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            return json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ------------------------------------------------------------ listRows' options

    def test_list_rows_levels_and_mark(self):
        got = self.js("""
P.setFavourite(%s, true);
const a = { id: 7, word: 'hus', hg: 0, pos: 'NOUN', translated: true };
const plain = S.listRows([a], {}).firstChild;
const fav = S.listRows([a], {}, { level: 2, mark: false }).firstChild;
plain.children[0].children[0].click(); fav.children[0].children[0].click();
await tick();
out([rowInfo(plain), rowInfo(fav)]);""" % json.dumps(FAVS[0]))
        plain, fav = got
        self.assertEqual((plain["head"], plain["mark"]), ("H3", True))
        self.assertEqual((fav["head"], fav["mark"]), ("H2", False))
        # the article one level under the row: an h3 under the favourites' h2 (no aria-level),
        # aria-level 4 under the results' h3; its section headings one below that
        self.assertIn('<h3 class="ordpar-hw" id="r7-hw">word 7</h3>', fav["html"])   # no link (decisions 160)
        self.assertIn('<h3 lang="en" aria-level="4">', fav["html"])
        self.assertIn('<h3 class="ordpar-hw" id="r7-hw" aria-level="4">', plain["html"])
        self.assertIn('<h3 lang="en" aria-level="5">', plain["html"])
        for r in got:
            self.assertEqual(r["expanded"], "true")
            self.assertEqual(r["controls"], "r7-panel")
            self.assertEqual(r["region"], "region:r7-row")

    # ------------------------------------------------------------ the page

    PAGE_SETUP = """
localStorage.setItem('favourites', JSON.stringify(%s));
const main = doc.body.appendChild(doc.createElement('main'));
main.setAttribute('data-ordpar-personal', 'favourites');
require(%s);
await tick();
const box = () => main.querySelector('.ordpar-fav-rows');
const rows = () => box().children;
"""

    def page(self, body):
        return self.js(self.PAGE_SETUP % (json.dumps(FAVS), json.dumps(os.path.join(SITE, "personal-page.js")))
                       + body)

    def test_the_page_draws_list_view_rows(self):
        got = self.page("""out({ rows: Array.from(rows()).map(rowInfo), fetched: fetched,
  h1: main.querySelector('h1').textContent, empty: main.querySelector('.ordpar-personal-empty').hidden,
  transfer: !!main.querySelector('.ordpar-transfer-link'), title: doc.title });""")
        rows = got["rows"]
        # newest first; since decisions 93 the headword span holds each spelling's numeral (the
        # Roman numeral and its hidden reading), where it sat beside the span before
        self.assertEqual([r["word"] for r in rows], ["hus", "stille II homograph 2", "kjapp"])
        self.assertEqual([r["head"] for r in rows], ["H2"] * 3)
        self.assertEqual([r["tag"] for r in rows], ["", "Norwegian only", "Norwegian only"])   # decisions 137
        self.assertEqual([r["mark"] for r in rows], [False] * 3)
        # the stored snippet line, whole, at once; none stored: no line
        self.assertEqual([(r["snip"], r["pending"]) for r in rows],
                         [("a house · a building", False), ("ro, taushet", False), (None, None)])
        self.assertEqual(rows[0]["remove"], "Remove hus from favourites")
        self.assertTrue(all("ordpar-fav-row" in r["cls"] for r in rows))
        self.assertEqual([r["open"] for r in rows], [False] * 3)
        # no article fetched until opened; since site decisions 116 the translated row's
        # headword `snip/` file is read, to learn whether its stored line is a summary gloss
        self.assertEqual([u for u in got["fetched"] if "/index/snip/" not in u], [])
        self.assertEqual([u for u in got["fetched"] if "/index/snip/" in u], ["/index/snip/h-u-s.json"])
        self.assertEqual(got["h1"], "Favourites")
        self.assertTrue(got["empty"])
        self.assertTrue(got["transfer"])

    def test_a_row_opens_in_place_and_stays_open_across_a_removal(self):
        got = self.page("""
const hus = rows()[0];
hus.querySelector('.ordpar-row-button').click();
await tick();
const opened = rowInfo(hus);
// another favourite removed (here, or in another tab: the same notify)
P.setFavourite({ id: 8 }, false);
const after = Array.from(rows());
out({ opened: opened, fetched: fetched, same: after[0] === hus, words: after.map(r => rowInfo(r).word),
      still: rowInfo(after[0]).open, controls: !!hus.querySelector('.ordpar-result-controls'),
      page: !!hus.querySelector('.ordpar-result-page') });""")
        self.assertTrue(got["opened"]["open"])
        self.assertEqual(got["opened"]["expanded"], "true")
        self.assertIn('id="r7-hw"', got["opened"]["html"])
        self.assertEqual([u for u in got["fetched"] if "/index/snip/" not in u], ["/bm-en/7/"])
        self.assertTrue(got["same"])
        self.assertEqual(got["words"], ["hus", "kjapp"])
        self.assertTrue(got["still"])
        self.assertTrue(got["controls"])
        self.assertFalse(got["page"])                              # no "Article page" (168 re-ruled)

    def test_remove_moves_the_focus_to_the_next_row(self):
        got = self.page("""
rows()[0].querySelector('.ordpar-fav-remove').click();
const a = doc.activeElement;
const first = [a.className, a.parentNode.getAttribute('data-id')];
// the heart pressed inside an opened favourite: its row goes, the focus to the row in its place
const kj = rows()[1];
kj.querySelector('.ordpar-row-button').click();
await tick();
kj.querySelector('.ordpar-heart').focus();
kj.querySelector('.ordpar-heart').click();
const b = doc.activeElement;
out({ first: first, words: Array.from(rows()).map(r => rowInfo(r).word), stored: P.favourites().map(e => e.id),
      second: [b.className, b.parentNode.parentNode.getAttribute('data-id')] });""")
        self.assertEqual(got["first"], ["ordpar-result-btn ordpar-fav-remove", "8"])
        self.assertEqual(got["words"], ["stille II homograph 2"])     # decisions 93: see above
        self.assertEqual(got["stored"], [8])
        self.assertEqual(got["second"], ["ordpar-row-button", "8"])

    def test_the_last_removal_shows_the_empty_line(self):
        got = self.page("""
[7, 8, 9].forEach(id => P.setFavourite({ id: id }, false));
out([rows().length, main.querySelector('.ordpar-personal-empty').hidden]);""")
        self.assertEqual(got, [0, False])

    # ------------------------------------------------------------ the wiring

    def test_wiring(self):
        html = _read(SITE, "favourites.html")
        for src in ("/site/inflection.js", "/site/article.js", "/site/mini.js"):
            self.assertIn('<script src="%s" defer></script>' % src, html)
            self.assertLess(html.index(src), html.index('<script src="/site/shell-pages.js">'))
        self.assertNotIn("article.js", _read(SITE, "history.html"))
        page = _read(SITE, "personal-page.js")
        self.assertIn("global.ordparSearch.listRows([e], Object.create(null),"
                      + chr(10) + "      { level: 2, mark: false, renumber: true });", page)  # 93
        # the history page is unchanged: its rows are searches
        self.assertIn("a.href = base() + 'bm-en/#q=' + encodeURIComponent(e.q);", page)
        js = _read(SITE, "lookup.js")
        self.assertIn("listRows: listRows,", js)
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-fav-row > .ordpar-row-panel { grid-column: 1 / -1; }", css)

    def test_the_built_page_stamps_the_article_scripts(self):
        import sys
        sys.path.insert(0, ORDPAR)
        import build_index as B
        tmp = tempfile.mkdtemp()
        try:
            B.copy_shell(tmp)
            html = _read(tmp, "favourites", "index.html")
            for src in ("/site/inflection.js?v=", "/site/article.js?v=", "/site/mini.js?v="):
                self.assertIn(src, html)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
