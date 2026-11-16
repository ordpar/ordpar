# -*- coding: utf-8 -*-
"""Site decisions 26, 62, 104 (2026-10-23): the page's side of the receiver — `ordpar/site/events.js`
and the calls into it from `shell.js` (a suggestion chosen), `lookup.js` (a search's hit or miss, a
similar word chosen) and `install.js` (an install). Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-receiver-26-62-104-2026-10-23.md` § 2.
Stdlib unittest; the scripts run under bun (or node) against a stand-in page, skipped when neither
is on PATH.

What it pins:

* **Nothing is sent** with the receiver's address empty (the default, as shipped), under
  `navigator.webdriver` (our own browser tests, layer 3), offline (62: the offline app logs
  nothing), or with Global Privacy Control or Do Not Track (104's box, item 2).
* **The page view** (26; layer 4): the path only — never the search page's `#q=` — sent once, after
  the page has been visible VISIBLE_MS, or at the first scroll, tap or key; nothing while hidden.
  **The path cleaned before sending** (decisions 104, 2026-10-23): one of the site's own, else `/other`
  (a mistyped address can hold a word), by the receiver's own pattern (`rules.js` `PATH`, the same
  text in both files).
* **The message**: exactly its fields, sent by `fetch` with `keepalive`, `credentials: 'omit'` and
  `referrerPolicy: 'no-referrer'`; events.js writes no storage and touches no cookie, and reads one
  key, the reader's own choice; no field anywhere holds an identifier.
* **The opt-out** (decisions 104, Robin 2026-10-23, built 2026-10-24): with "Send usage statistics"
  off (the stored setting `stats` = 'off') nothing is sent — no page view, search, suggestion
  chosen, miss or install — and turned off on an open page, from the next event on.
* **The searches** (62): a query with a digit or over 40 characters is never sent; a miss is held
  until a similar word is chosen (sent with it and its position) or the page is hidden (sent with
  none), and a new search ends it.
* **One event per choice, none per keystroke**, through the real `shell.js` and `lookup.js` over a
  small real index: typing sends nothing; a suggestion chosen by Enter or by a press sends one `pick`
  (typed text, word, position from 1); a Recent row sends none; a search the reader made sends one
  `hit` or one `miss`, a re-render (not the reader's) none; a similar word chosen after a miss sends
  the miss with it.
* **The search's language** (site decisions 148's follow-up, English searches counted
  too): every search and suggestion message carries `lang`, 'nb' for the Norwegian search and
  'en' for the English one — an English hit, an English miss held until a similar English word is
  chosen (its place from 1) or the page is left, an English suggestion chosen, under the same rules
  (no digit, at most 40 characters, one per choice); through the real shell and lookup.js too.
* **The wiring**: `events.js` in both combined scripts, before `install.js` and `shell.js`; the
  receiver's address in one place, empty; `install.js` reports `appinstalled`.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
SITE = os.path.join(ROOT, "ordpar", "site")

from ordpar import build_index as B  # noqa: E402
from ordpar.sitegen import page  # noqa: E402

RECEIVER = "https://receiver.test/e"


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run(script):
    runner = _runner()
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "t.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(script)
        res = subprocess.run([runner, path], capture_output=True, timeout=120)
        out = res.stdout.decode("utf-8", "replace")
        if res.returncode != 0:
            raise AssertionError("JS failed:\n" + out + res.stderr.decode("utf-8", "replace"))
        return json.loads(out.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


#: events.js on its own, in a fresh global per case: a stand-in navigator, document, location,
#: fetch, timers — and storage and a cookie that record any touch.
EVENTS_ALONE = r"""
const fs = require('fs');
const SRC = fs.readFileSync(%(events)s, 'utf8');
const TAIL = "(typeof globalThis !== 'undefined' ? globalThis : this)";
if (SRC.split(TAIL).length !== 2) throw new Error('events.js: its IIFE tail moved');
function load(o) {
  o = o || {};
  const touched = [];
  const trap = (name) => new Proxy({}, { get(t, k) { touched.push(name + '.' + String(k)); return () => null; } });
  // the one read events.js may make (decisions 104: the opt-out, "Send usage statistics"): recorded
  // with its key; any other touch of storage is recorded as the trap's
  const stored = o.stored || {};
  const local = new Proxy({}, { get(t, k) {
    if (k === 'getItem') return (key) => { touched.push('localStorage.getItem:' + key); return key in stored ? stored[key] : null; };
    touched.push('localStorage.' + String(k)); return () => null; } });
  const listeners = {}, docListeners = {};
  const timers = [];
  const sent = [];
  const doc = {
    visibilityState: o.hidden ? 'hidden' : 'visible',
    addEventListener(t, f) { (docListeners[t] = docListeners[t] || []).push(f); },
    removeEventListener(t, f) { docListeners[t] = (docListeners[t] || []).filter(g => g !== f); },
  };
  Object.defineProperty(doc, 'cookie', { get() { touched.push('cookie'); return ''; }, set() { touched.push('cookie='); } });
  const G = {
    navigator: Object.assign({ onLine: true }, o.nav || {}),
    document: doc,
    location: { pathname: o.path || '/bm-en/', search: '', hash: '#q=hus', href: 'https://ordpar.no' + (o.path || '/bm-en/') + '#q=hus' },
    localStorage: local, sessionStorage: trap('sessionStorage'), indexedDB: trap('indexedDB'),
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    removeEventListener(t, f) { listeners[t] = (listeners[t] || []).filter(g => g !== f); },
    setTimeout(f, ms) { timers.push({ f, ms, live: true }); return timers.length - 1; },
    clearTimeout(i) { if (timers[i]) timers[i].live = false; },
    fetch(url, opts) { sent.push({ url, opts }); return Promise.resolve({ ok: true }); },
  };
  if (o.dnt) G.doNotTrack = o.dnt;
  const src = SRC.replace(TAIL, '(G)').replace("var RECEIVER = '';", "var RECEIVER = " + JSON.stringify(o.receiver === undefined ? %(receiver)s : o.receiver) + ";");
  new Function('G', 'module', src)(G, undefined);
  const fire = (t) => (listeners[t] || []).slice().forEach(f => f({ type: t }));
  const fireDoc = (t) => (docListeners[t] || []).slice().forEach(f => f({ type: t }));
  const run = () => timers.forEach(t => { if (t.live) { t.live = false; t.f(); } });
  return { G, E: G.ordparEvents, sent, touched, timers, fire, fireDoc, run, doc };
}
const msgs = (c) => c.sent.map(s => JSON.parse(s.opts.body));
const out = {};

// the default as shipped: no address
let c = load({ receiver: '' });
c.run(); c.fire('scroll'); c.E.hit('hus'); c.E.pick('hu', 'hus', 1); c.E.install(); c.E.missStart('vus'); c.fireDoc('visibilitychange');
out.empty = { sent: c.sent.length, quiet: c.E.quiet(), timers: c.timers.length };
// the four signals
for (const [name, o] of [['webdriver', { nav: { webdriver: true } }], ['offline', { nav: { onLine: false } }],
                         ['gpc', { nav: { globalPrivacyControl: true } }], ['dnt', { nav: { doNotTrack: '1' } }],
                         ['dntWindow', { dnt: '1' }], ['optout', { stored: { stats: 'off' } }]]) {
  c = load(o);
  c.run(); c.fire('pointerdown'); c.E.hit('hus'); c.E.pick('hu', 'hus', 1); c.E.install();
  c.E.missStart('vus'); c.doc.visibilityState = 'hidden'; c.fireDoc('visibilitychange');
  out[name] = { sent: c.sent.length, quiet: c.E.quiet() };
}
// the page view after the timer: once, the path only
c = load();
out.viewTimer = { ms: c.timers.map(t => t.ms), before: c.sent.length };
c.run(); c.fire('scroll'); c.run();
out.viewTimer.msgs = msgs(c); out.viewTimer.url = c.sent.map(s => s.url);
out.viewTimer.opts = c.sent.map(s => { const x = Object.assign({}, s.opts); delete x.body; return x; });
// ... or at the first scroll, tap or key, before the timer
for (const t of ['scroll', 'pointerdown', 'keydown']) {
  c = load(); c.fire(t); c.fire(t); c.run();
  out['view_' + t] = msgs(c);
}
// hidden: no timer, no view at a scroll; once visible, the timer
c = load({ hidden: true });
c.run(); c.fire('scroll');
out.hidden = { sent: c.sent.length, live: c.timers.filter(t => t.live).length };
c.doc.visibilityState = 'visible'; c.fireDoc('visibilitychange');
out.hidden.liveAfter = c.timers.filter(t => t.live).length; c.run();
out.hidden.after = msgs(c);
// hidden before the 2 seconds: the timer stopped
c = load();
c.doc.visibilityState = 'hidden'; c.fireDoc('visibilitychange');
out.hiddenEarly = { live: c.timers.filter(t => t.live).length };
// the searches
c = load(); c.fire('scroll');                         // the view first, out of the way
c.E.hit('hus'); c.E.hit(' hus  hytte '); c.E.hit('hus2'); c.E.hit('a'.repeat(41)); c.E.hit('a'.repeat(40)); c.E.hit('٣');
c.E.pick('hu', 'hus', 1); c.E.pick('h2', 'hus', 1);
c.E.missStart('vus'); c.E.missChoose('vus', 'hus', 2); c.E.missChoose('vus', 'hus', 2);   // once
c.E.missStart('kvs'); c.doc.visibilityState = 'hidden'; c.fireDoc('visibilitychange'); c.fire('pagehide');
c.doc.visibilityState = 'visible';
c.E.missStart('vvs'); c.E.hit('hus');                 // a new search ends the held miss
c.E.missStart('xxs'); c.E.missChoose('yys', 'hus', 1); // another query's choice: nothing
c.E.missStart('ola 12');                              // a digit: nothing held
c.fire('pagehide');
c.E.install();
out.searches = msgs(c);
out.touched = c.touched;
// 148's follow-up: the English search, marked 'en'; the same rules
c = load(); c.fire('scroll');
c.E.hit('house', true); c.E.hit('house 2', true); c.E.hit('a'.repeat(41), true);
c.E.pick('hou', 'house', 1, true);
c.E.missStart('hoose', true); c.E.missChoose('hoose', 'choose', 2);        // a Norwegian choice: not this miss
c.E.missChoose('hoose', 'choose', 2, true); c.E.missChoose('hoose', 'choose', 2, true);   // once
c.E.missStart('hoose', true); c.fire('pagehide');                          // left: sent with none
c.E.missStart('hoose', true); c.E.hit('hus');                              // a new search ends it
out.english = msgs(c);
// decisions 104: a view's path as SENT — one of the site's own, else /other (a mistyped address)
for (const [name, path] of [['typo', '/bm-en/hus'], ['typo2', '/bm-en/hus/'], ['article', '/bm-en/12345/'],
                            ['tooLong', '/bm-en/12345678/'], ['privacy', '/privacy/'], ['front', '/'],
                            ['other', '/finnes/ikke'], ['huge', '/' + 'a'.repeat(300)]]) {
  const v = load({ path }); v.fire('scroll');
  out['path_' + name] = msgs(v);
}
out.keys = [...new Set(msgs(c).flatMap(m => Object.keys(m)))].sort();
// decisions 104: "Send usage statistics" On (stored 'on', or anything but 'off') sends as before;
// turned off on the page, the next event is not sent
for (const [name, v] of [['statsOn', 'on'], ['statsOther', 'yes']]) {
  const v1 = load({ stored: { stats: v } }); v1.fire('scroll'); v1.E.hit('hus');
  out[name] = { sent: v1.sent.length, quiet: v1.E.quiet() };
}
const lateStore = {};
const late = load({ stored: lateStore }); late.fire('scroll'); late.E.hit('hus');
lateStore.stats = 'off';                              // turned off in Settings, the page still open
late.E.hit('hytte'); late.E.pick('hy', 'hytte', 1); late.E.install(); late.E.missStart('vus'); late.fire('pagehide');
out.late = { msgs: msgs(late), quiet: late.E.quiet() };
out.lateTouched = [...new Set(late.touched)];

process.stdout.write(JSON.stringify(out));
"""


#: A stand-in DOM, enough for shell.js's header and lookup.js's results to run in it.
FAKE_DOM = r"""
const fs = require('fs'), path = require('path');
class Ev { constructor(type, o) { this.type = type; this.bubbles = !!(o && o.bubbles); this.defaultPrevented = false; Object.assign(this, o || {}); }
  preventDefault() { this.defaultPrevented = true; } stopPropagation() {} }
globalThis.Event = Ev;
function parseSel(sel) {
  return sel.split(',').map(s => s.trim()).filter(Boolean).map(s => {
    const parts = []; let rel = ' ';
    for (const tok of s.match(/(?:[^\s>"]|"[^"]*")+|>/g)) {
      if (tok === '>') { rel = '>'; continue; }
      const c = { rel, tag: null, id: null, cls: [], attrs: [] };
      const t = tok.match(/^[a-zA-Z][\w-]*/);
      if (t) c.tag = t[0].toUpperCase();
      const re = /#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:([$^*]?=)"([^"]*)")?\]/g;
      let k;
      while ((k = re.exec(tok))) { if (k[1]) c.id = k[1]; if (k[2]) c.cls.push(k[2]); if (k[3]) c.attrs.push([k[3], k[4], k[5]]); }
      parts.push(c); rel = ' ';
    }
    return parts;
  });
}
function one(n, c) {
  if (!n || n.nodeType !== 1) return false;
  if (c.tag && n.tagName !== c.tag) return false;
  if (c.id && n.getAttribute('id') !== c.id) return false;
  for (const k of c.cls) if (!n.classList.contains(k)) return false;
  for (const [a, op, v] of c.attrs) {
    const got = n.getAttribute(a); if (got === null) return false;
    if (op === '=' && got !== v) return false; if (op === '$=' && !got.endsWith(v)) return false;
    if (op === '^=' && !got.startsWith(v)) return false; if (op === '*=' && got.indexOf(v) < 0) return false;
  }
  return true;
}
function chain(n, parts, i) {
  if (!one(n, parts[i])) return false;
  if (i === 0) return true;
  if (parts[i].rel === '>') return chain(n.parentNode, parts, i - 1);
  for (let p = n.parentNode; p; p = p.parentNode) if (chain(p, parts, i - 1)) return true;
  return false;
}
function matches(n, sel) { return parseSel(sel).some(parts => chain(n, parts, parts.length - 1)); }
class N {
  constructor(tag, text) {
    this.nodeType = tag === '#text' ? 3 : 1; this.tagName = tag.toUpperCase(); this.nodeName = this.tagName;
    this.childNodes = []; this.parentNode = null; this.attrs = {}; this.listeners = {}; this._text = text || '';
    this.style = { setProperty() {}, removeProperty() {} }; this.hidden = false; this.value = ''; this.dataset = {};
    const self = this, set = new Set();
    this.classList = { add(...c) { c.forEach(x => set.add(x)); }, remove(...c) { c.forEach(x => set.delete(x)); },
      toggle(c, f) { const on = f === undefined ? !set.has(c) : !!f; on ? set.add(c) : set.delete(c); return on; },
      contains(c) { return set.has(c); }, _set: set };
    this.offsetHeight = 0; this.clientWidth = 0; this.scrollWidth = 0; this.scrollTop = 0;
  }
  get children() { return this.childNodes.filter(c => c.nodeType === 1); }
  get className() { return [...this.classList._set].join(' '); }
  set className(v) { this.classList._set.clear(); String(v).split(/\s+/).filter(Boolean).forEach(x => this.classList._set.add(x)); }
  get id() { return this.attrs.id || ''; } set id(v) { this.attrs.id = String(v); }
  get href() { return this.attrs.href || ''; } set href(v) { this.attrs.href = String(v); }
  get lang() { return this.attrs.lang || ''; } set lang(v) { this.attrs.lang = String(v); }
  get textContent() { return this.nodeType === 3 ? this._text : this.childNodes.map(c => c.textContent).join(''); }
  set textContent(v) { if (this.nodeType === 3) { this._text = String(v); return; } this.childNodes.forEach(c => { c.parentNode = null; }); this.childNodes = []; if (v !== '' && v != null) this.appendChild(new N('#text', String(v))); }
  get innerHTML() { return ''; } set innerHTML(v) { this.textContent = ''; }
  get firstChild() { return this.childNodes[0] || null; } get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
  get firstElementChild() { return this.children[0] || null; } get lastElementChild() { const k = this.children; return k[k.length - 1] || null; }
  sib(d, el) { if (!this.parentNode) return null; const l = el ? this.parentNode.children : this.parentNode.childNodes; return l[l.indexOf(this) + d] || null; }
  get nextSibling() { return this.sib(1); } get previousSibling() { return this.sib(-1); }
  get nextElementSibling() { return this.sib(1, 1); } get previousElementSibling() { return this.sib(-1, 1); }
  get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n === document.documentElement; }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.childNodes.push(c); return c; }
  insertBefore(c, ref) { if (!ref) return this.appendChild(c); if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.childNodes.splice(this.childNodes.indexOf(ref), 0, c); return c; }
  removeChild(c) { const i = this.childNodes.indexOf(c); if (i >= 0) this.childNodes.splice(i, 1); c.parentNode = null; return c; }
  replaceChild(n, o) { this.insertBefore(n, o); return this.removeChild(o); }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  setAttribute(k, v) { if (k === 'class') this.className = v; else this.attrs[k] = String(v); }
  getAttribute(k) { if (k === 'class') return this.classList._set.size ? this.className : null; return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return this.getAttribute(k) !== null; } removeAttribute(k) { if (k === 'class') this.classList._set.clear(); delete this.attrs[k]; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  removeEventListener(t, f) { this.listeners[t] = (this.listeners[t] || []).filter(g => g !== f); }
  dispatchEvent(e) { if (!e.target) e.target = this; for (let n = this; n; n = n.parentNode) { (n.listeners[e.type] || []).slice().forEach(f => f.call(n, e)); if (!e.bubbles) break; } return !e.defaultPrevented; }
  click() { this.dispatchEvent(new Ev('click', { bubbles: true, button: 0 })); }
  focus() { document.activeElement = this; this.dispatchEvent(new Ev('focus')); } blur() {}
  getBoundingClientRect() { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  scrollIntoView() {}
  all() { const out = []; const walk = (n) => n.children.forEach(c => { out.push(c); walk(c); }); walk(this); return out; }
  querySelectorAll(sel) { return this.all().filter(n => matches(n, sel)); }
  querySelector(sel) { return this.all().find(n => matches(n, sel)) || null; }
  matches(sel) { return matches(this, sel); }
  closest(sel) { for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (matches(n, sel)) return n; return null; }
}
const html = new N('html'), head = new N('head'), body = new N('body');
html.appendChild(head); html.appendChild(body);
globalThis.window = globalThis;
globalThis.document = {
  documentElement: html, head, body, readyState: 'complete', visibilityState: 'visible', activeElement: null,
  createElement: (t) => new N(t), createTextNode: (t) => new N('#text', t),
  querySelector: (s) => html.matches(s) ? html : html.querySelector(s), querySelectorAll: (s) => html.querySelectorAll(s),
  getElementById: (id) => html.querySelector('#' + id), addEventListener() {}, removeEventListener() {},
};
globalThis.location = { pathname: '/bm-en/', search: '', href: 'https://ordpar.no/bm-en/', origin: 'https://ordpar.no' };
const winL = {};
globalThis.addEventListener = (t, f) => { (winL[t] = winL[t] || []).push(f); };
globalThis.removeEventListener = (t, f) => { winL[t] = (winL[t] || []).filter(g => g !== f); };
globalThis.fireWindow = (t) => (winL[t] || []).slice().forEach(f => f({ type: t }));
globalThis.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
globalThis.getComputedStyle = () => ({ columnGap: '0', left: '0', getPropertyValue: () => '' });
globalThis.requestAnimationFrame = (f) => { f(); return 0; };
function storage() { const s = {}; return { getItem: k => (k in s ? s[k] : null), setItem: (k, v) => { s[k] = String(v); },
  removeItem: k => { delete s[k]; }, clear: () => { for (const k in s) delete s[k]; }, key: i => Object.keys(s)[i] || null,
  get length() { return Object.keys(s).length; } }; }
globalThis.localStorage = storage(); globalThis.sessionStorage = storage();
const realSetTimeout = setTimeout;
globalThis.SENT = []; globalThis.ALL = [];
globalThis.fetch = (url, opts) => {
  if (url === %(receiver)s) { SENT.push(JSON.parse(opts.body)); ALL.push(JSON.parse(opts.body)); return Promise.resolve({ ok: true }); }
  return Promise.resolve({ ok: false, status: 404, text: () => Promise.resolve(''), json: () => Promise.resolve(null) });
};
Object.defineProperty(globalThis, 'navigator', { value: { onLine: true, userAgent: 'test' }, configurable: true });
"""

#: shell.js + lookup.js + events.js together, over a small real index: the keystrokes and choices.
INTEGRATION = FAKE_DOM + r"""
const INDEX = %(index)s;
globalThis.ORDPAR_STRINGS = { en: JSON.parse(fs.readFileSync(%(strings)s, 'utf8')) };
function load(file, receiver) {
  let src = fs.readFileSync(file, 'utf8');
  if (receiver) src = src.replace("var RECEIVER = '';", "var RECEIVER = " + JSON.stringify(receiver) + ";");
  (0, eval)(src);
}
// the header, as chrome.py writes it
const hdr = document.createElement('header'); hdr.className = 'ordpar-header';
const inner = document.createElement('div'); inner.className = 'ordpar-header-inner'; hdr.appendChild(inner);
const form = document.createElement('form'); form.className = 'ordpar-search'; inner.appendChild(form);
const box = document.createElement('div'); box.className = 'ordpar-combobox'; form.appendChild(box);
const input = document.createElement('input'); input.id = 'ordpar-q'; box.appendChild(input);
document.body.appendChild(hdr);
const main = document.createElement('main'); main.id = 'ordpar-main'; document.body.appendChild(main);
const results = document.createElement('div'); results.setAttribute('data-ordpar-results', ''); main.appendChild(results);
globalThis.ordparPersonal = { history: () => [{ q: 'katt', t: 1 }], RECENT: 8, recordSearch() {}, setLabels() {} };
load(%(events)s, %(receiver)s);
load(%(lookup)s);
ordparLookup.setLoader(name => { const p = path.join(INDEX, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
load(%(shell)s);
const tick = () => new Promise(r => realSetTimeout(r, 30));
const key = (k) => input.dispatchEvent(new Ev('keydown', { key: k }));
const type = async (v) => { input.value = v; document.activeElement = input; input.dispatchEvent(new Ev('input')); await tick(); };
const searches = () => SENT.filter(m => m.type !== 'view');
(async () => {
  await ordparShell.ready; await tick();
  const out = {};
  // typing: one keystroke at a time, the suggestions open — nothing sent
  await type('h'); await type('hu'); await type('hus');
  out.rows = input.parentNode.querySelectorAll('.ordpar-option').map(li => li.textContent).slice(0, 4);
  out.afterTyping = searches().length;
  // Enter on the second suggestion
  key('ArrowDown'); key('ArrowDown'); key('Enter');
  out.enter = searches().slice();
  // a press on the first, after typing again
  await type('hu');
  const li = input.parentNode.querySelectorAll('.ordpar-option')[0];
  li.dispatchEvent(new Ev('mousedown'));
  out.press = searches().slice(out.enter.length);
  // a Recent row: the box empty and focused
  input.value = ''; input.dispatchEvent(new Ev('focus')); await tick();
  const recent = input.parentNode.querySelectorAll('.ordpar-option-recent');
  out.recentRows = recent.length;
  if (recent[0]) recent[0].dispatchEvent(new Ev('mousedown'));
  out.afterRecent = searches().length;
  // searches the reader made, and a re-render that is not
  SENT.length = 0;
  await ordparSearch.render(main, 'hus', { record: true }); await tick();
  out.hit = searches().slice();
  SENT.length = 0;
  await ordparSearch.render(main, 'hus', { record: false }); await tick();
  out.rerender = searches().length;
  await ordparSearch.render(main, 'hux', { record: true }); await tick();
  out.missHeld = searches().length;
  const links = main.querySelectorAll('.ordpar-similar-list a');
  out.similar = links.map(a => (a.querySelector('.ordpar-option-word') || a).textContent);   // 144: a miss's rows
  if (links[1]) links[1].click(); else if (links[0]) links[0].click();
  out.miss = searches().slice();
  SENT.length = 0;
  await ordparSearch.render(main, 'qqqqq', { record: true }); await tick();
  await ordparSearch.render(main, 'hus', { record: true }); await tick();   // the new search ends the miss
  out.missThenHit = searches().slice();
  // 148's follow-up: the English search, the same events marked 'en'
  SENT.length = 0;
  await ordparSearch.render(main, 'house', { record: true, en: true }); await tick();
  out.enHit = searches().slice();
  SENT.length = 0;
  await ordparSearch.render(main, 'house', { record: false, en: true }); await tick();
  out.enRerender = searches().length;
  await ordparSearch.render(main, 'hoose', { record: true, en: true }); await tick();
  out.enMissHeld = searches().length;
  const enLinks = main.querySelectorAll('.ordpar-similar-list a');
  out.enSimilar = enLinks.map(a => (a.querySelector('.ordpar-option-word') || a).textContent);
  if (enLinks[0]) enLinks[0].click();
  out.enMiss = searches().slice();
  // an English suggestion chosen, by a press and by Enter
  SENT.length = 0;
  ordparShell.setDirection('en', { quiet: true });
  await type('hou');
  out.enRows = input.parentNode.querySelectorAll('.ordpar-option').map(li => li.textContent);
  const enLi = input.parentNode.querySelectorAll('.ordpar-option')[0];
  if (enLi) enLi.dispatchEvent(new Ev('mousedown'));
  await tick();
  out.enPress = searches().filter(m => m.type === 'pick');
  SENT.length = 0;
  await type('rem');
  key('ArrowDown'); key('Enter'); await tick();
  out.enEnter = searches().filter(m => m.type === 'pick');
  ordparShell.setDirection('nb', { quiet: true });
  out.keys = [...new Set(SENT.flatMap(m => Object.keys(m)))].sort();
  out.allKeys = [...new Set(ALL.filter(m => m.type !== 'view').flatMap(m => Object.keys(m)))].sort();
  process.stdout.write('\n' + JSON.stringify(out));
  process.exit(0);
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
"""


def _rows():
    def row(aid, lemma, pos="NOUN", forms=()):
        return {"id": aid, "data": {"lemmas": [{
            "lemma": lemma, "hgno": 0,
            "paradigm_info": [{"tags": [pos], "inflection": [{"word_form": f} for f in forms]}]}]}}
    return [row(1, "hus", forms=["huset"]), row(2, "huske", "VERB"), row(3, "hut", "VERB"),
            row(4, "hund"), row(5, "hue"), row(6, "hul", "ADJ")]


@unittest.skipUnless(_runner(), "neither bun nor node on PATH")
class EventsAlone(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _run(EVENTS_ALONE % {"events": json.dumps(os.path.join(SITE, "events.js")),
                                       "receiver": json.dumps(RECEIVER)})

    def test_nothing_without_the_address_as_shipped(self):
        self.assertEqual(self.out["empty"], {"sent": 0, "quiet": "off", "timers": 0})

    def test_nothing_under_automation_offline_gpc_or_dnt(self):
        for name, why in (("webdriver", "webdriver"), ("offline", "offline"), ("gpc", "gpc"),
                          ("dnt", "dnt"), ("dntWindow", "dnt")):
            self.assertEqual(self.out[name], {"sent": 0, "quiet": why}, name)

    def test_nothing_with_send_usage_statistics_off(self):
        # decisions 104 (Robin, 2026-10-23): the opt-out — no page view, search, suggestion
        # chosen, miss or install while the stored setting `stats` is 'off'
        self.assertEqual(self.out["optout"], {"sent": 0, "quiet": "optout"})
        for name in ("statsOn", "statsOther"):
            self.assertEqual(self.out[name], {"sent": 2, "quiet": ""}, name)

    def test_turned_off_on_an_open_page(self):
        self.assertEqual(self.out["late"]["msgs"], [{"type": "view", "path": "/bm-en/"},
                                                    {"type": "hit", "query": "hus", "lang": "nb"}])
        self.assertEqual(self.out["late"]["quiet"], "optout")
        self.assertEqual(self.out["lateTouched"], ["localStorage.getItem:stats"])

    def test_the_view_after_two_seconds_the_path_only_once(self):
        v = self.out["viewTimer"]
        self.assertEqual(v["ms"], [2000])
        self.assertEqual(v["before"], 0)
        self.assertEqual(v["msgs"], [{"type": "view", "path": "/bm-en/"}])     # never #q=hus
        self.assertEqual(v["url"], [RECEIVER])
        self.assertEqual(v["opts"], [{"method": "POST", "keepalive": True, "credentials": "omit",
                                      "referrerPolicy": "no-referrer", "cache": "no-store"}])

    def test_the_view_at_the_first_scroll_tap_or_key(self):
        for t in ("scroll", "pointerdown", "keydown"):
            self.assertEqual(self.out["view_" + t], [{"type": "view", "path": "/bm-en/"}], t)

    def test_the_path_cleaned_before_sending(self):
        # decisions 104: a mistyped address can hold a word the reader typed; it is sent as /other
        want = {"typo": "/other", "typo2": "/other", "article": "/bm-en/12345/", "tooLong": "/other",
                "privacy": "/privacy/", "front": "/", "other": "/other", "huge": "/other"}
        for name, path in want.items():
            self.assertEqual(self.out["path_" + name], [{"type": "view", "path": path}], name)

    def test_the_path_rule_is_the_receivers(self):
        rules = _read(ROOT, "ordpar", "receiver", "src", "rules.js")
        events = _read(SITE, "events.js")
        r = re.search(r"^const PATH = (/.+/);$", rules, re.M)
        e = re.search(r"^  var PATH = (/.+/);$", events, re.M)
        self.assertTrue(r and e, "PATH not found in rules.js or events.js")
        self.assertEqual(e.group(1), r.group(1))
        self.assertIn("export const OTHER_PATH = '/other';", rules)
        self.assertIn("var OTHER_PATH = '/other';", events)

    def test_no_view_while_hidden(self):
        h = self.out["hidden"]
        self.assertEqual((h["sent"], h["live"]), (0, 0))
        self.assertEqual(h["liveAfter"], 1)
        self.assertEqual(h["after"], [{"type": "view", "path": "/bm-en/"}])
        self.assertEqual(self.out["hiddenEarly"], {"live": 0})

    def test_the_searches(self):
        self.assertEqual(self.out["searches"], [
            {"type": "view", "path": "/bm-en/"},
            {"type": "hit", "query": "hus", "lang": "nb"},
            {"type": "hit", "query": "hus hytte", "lang": "nb"},
            {"type": "hit", "query": "a" * 40, "lang": "nb"},
            {"type": "pick", "query": "hu", "word": "hus", "position": 1, "lang": "nb"},
            {"type": "miss", "query": "vus", "word": "hus", "position": 2, "lang": "nb"},
            {"type": "miss", "query": "kvs", "word": None, "position": None, "lang": "nb"},
            {"type": "miss", "query": "vvs", "word": None, "position": None, "lang": "nb"},
            {"type": "hit", "query": "hus", "lang": "nb"},
            {"type": "miss", "query": "xxs", "word": None, "position": None, "lang": "nb"},
            {"type": "install"},
        ])

    def test_the_english_searches(self):
        # 148's follow-up (English searches counted too): as the Norwegian ones, marked 'en'
        self.assertEqual(self.out["english"], [
            {"type": "view", "path": "/bm-en/"},
            {"type": "hit", "query": "house", "lang": "en"},
            {"type": "pick", "query": "hou", "word": "house", "position": 1, "lang": "en"},
            {"type": "miss", "query": "hoose", "word": "choose", "position": 2, "lang": "en"},
            {"type": "miss", "query": "hoose", "word": None, "position": None, "lang": "en"},
            {"type": "miss", "query": "hoose", "word": None, "position": None, "lang": "en"},
            {"type": "hit", "query": "hus", "lang": "nb"},
        ])

    def test_no_storage_no_cookie_no_identifier(self):
        # one read, the reader's own choice (decisions 104: "Send usage statistics"); nothing written,
        # no other key, no cookie
        self.assertEqual(sorted(set(self.out["touched"])), ["localStorage.getItem:stats"])
        self.assertEqual(self.out["keys"], ["lang", "path", "position", "query", "type", "word"])


@unittest.skipUnless(_runner(), "neither bun nor node on PATH")
class ThroughTheShell(unittest.TestCase):
    """The real shell.js and lookup.js, in a stand-in page, over a small real index."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in _rows():
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        heads, forms, words = B.build_tables(mirror, None, {})
        # 148's follow-up: two glossed rows, so the English search has an index to answer from
        library = {1: {"lemmas": [], "pos_en": "noun", "gloss": True, "en": ["house, home"]},
                   2: {"lemmas": [], "pos_en": "verb", "gloss": True, "en": ["to remember"]}}
        B.write_index(cls.tmp, heads, forms, words, [1, 2], {}, library=library)
        cls.out = _run(INTEGRATION % {
            "index": json.dumps(os.path.join(cls.tmp, "index")),
            "strings": json.dumps(os.path.join(SITE, "strings", "en.json")),
            "events": json.dumps(os.path.join(SITE, "events.js")),
            "lookup": json.dumps(os.path.join(SITE, "lookup.js")),
            "shell": json.dumps(os.path.join(SITE, "shell.js")),
            "receiver": json.dumps(RECEIVER)})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_typing_sends_nothing(self):
        self.assertTrue(self.out["rows"], "the suggestions opened")
        self.assertEqual(self.out["afterTyping"], 0)

    def test_a_suggestion_chosen_sends_one_pick(self):
        self.assertEqual(len(self.out["enter"]), 1)
        e = self.out["enter"][0]
        self.assertEqual((e["type"], e["query"], e["position"], e["lang"]), ("pick", "hus", 2, "nb"))
        self.assertTrue(e["word"])
        self.assertEqual(len(self.out["press"]), 1)
        p = self.out["press"][0]
        self.assertEqual((p["type"], p["query"], p["position"], p["lang"]), ("pick", "hu", 1, "nb"))

    def test_a_recent_row_sends_no_pick(self):
        self.assertEqual(self.out["recentRows"], 1)
        self.assertEqual(self.out["afterRecent"], 2)

    def test_a_search_the_reader_made(self):
        self.assertEqual(self.out["hit"], [{"type": "hit", "query": "hus", "lang": "nb"}])
        self.assertEqual(self.out["rerender"], 0)
        self.assertEqual(self.out["missHeld"], 0)
        self.assertTrue(self.out["similar"], "similar words offered for the miss")
        pos = 2 if len(self.out["similar"]) > 1 else 1
        self.assertEqual(self.out["miss"], [{"type": "miss", "query": "hux",
                                             "word": self.out["similar"][pos - 1], "position": pos,
                                             "lang": "nb"}])
        self.assertEqual(self.out["missThenHit"], [
            {"type": "miss", "query": "qqqqq", "word": None, "position": None, "lang": "nb"},
            {"type": "hit", "query": "hus", "lang": "nb"}])

    def test_an_english_search_the_reader_made(self):
        # 148's follow-up: a hit marked English; a re-render none; a miss held until a similar
        # English word is chosen, then sent with it and its place
        self.assertEqual(self.out["enHit"], [{"type": "hit", "query": "house", "lang": "en"}])
        self.assertEqual(self.out["enRerender"], 0)
        self.assertEqual(self.out["enMissHeld"], 0)
        self.assertEqual(self.out["enSimilar"][:1], ["house"])
        self.assertEqual(self.out["enMiss"], [{"type": "miss", "query": "hoose", "word": "house",
                                               "position": 1, "lang": "en"}])

    def test_an_english_suggestion_chosen(self):
        self.assertTrue(self.out["enRows"], "the English suggestions opened")
        self.assertEqual(self.out["enPress"], [{"type": "pick", "query": "hou", "word": "house",
                                                "position": 1, "lang": "en"}])
        self.assertEqual(self.out["enEnter"], [{"type": "pick", "query": "rem", "word": "remember",
                                                "position": 1, "lang": "en"}])

    def test_no_identifier_in_any_message(self):
        self.assertEqual(self.out["keys"], ["lang", "position", "query", "type", "word"])
        self.assertEqual(self.out["allKeys"], ["lang", "position", "query", "type", "word"])


class Wiring(unittest.TestCase):

    def test_in_both_combined_scripts_before_install_and_shell(self):
        for parts in (page.ARTICLE_JS_PARTS, page.SHELL_JS_PARTS):
            self.assertIn(page.EVENTS_JS_HREF, parts)
            self.assertLess(parts.index(page.EVENTS_JS_HREF), parts.index(page.INSTALL_JS_HREF))
            self.assertLess(parts.index(page.EVENTS_JS_HREF), parts.index(page.SHELL_JS_HREF))

    def test_the_address_in_one_place_and_empty(self):
        src = _read(SITE, "events.js")
        self.assertEqual(src.count("var RECEIVER = '';"), 1)
        for name in os.listdir(SITE):
            if name.endswith((".js", ".html")) and name != "events.js":
                text = _read(SITE, name)
                if name == "audio.js":     # site decisions 159: the audio Worker's address, not the receiver's
                    text = text.replace("https://ordpar-audio.ordpar.workers.dev/", "")
                self.assertNotIn("workers.dev", text, name)
        self.assertIn("var RECEIVER = '';", page.shipped(page.JS_ALL_HREF))
        self.assertIn("var RECEIVER = '';", page.shipped(page.SHELL_PAGES_JS_HREF))

    def test_install_reports_appinstalled(self):
        src = _read(SITE, "install.js")
        at = src.index("global.addEventListener('appinstalled'")
        self.assertIn("global.ordparEvents.install()", src[at:at + 400])

    def test_the_calls_into_events(self):
        shell = _read(SITE, "shell.js")
        handler = shell.split("input.addEventListener('input', function () {")[1].split("\n    });")[0]
        self.assertNotIn("event(", handler)
        self.assertNotIn("picked(", handler)
        self.assertEqual(shell.count("picked("), 4)          # its definition, Enter, a press, an English press
        self.assertIn("li.addEventListener('mousedown', function (e) { e.preventDefault(); picked(i); submit(it.word, true); });", shell)
        look = _read(SITE, "lookup.js")
        self.assertIn("if (record && E) {", look)
        self.assertIn("E.missChoose(g.query, s.word, i + 1)", look)
        # 148's follow-up: the English search's events, marked English
        self.assertIn("if (res.count) { E.hit(g.query, true); } else { E.missStart(g.query, true); }", look)
        self.assertIn("E.missChoose(g.query, it.word, i + 1, true)", look)


if __name__ == "__main__":
    unittest.main()
