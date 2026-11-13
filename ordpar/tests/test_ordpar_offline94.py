# -*- coding: utf-8 -*-
"""Pins the offline copy's update check as ruled in site-review decisions 94 (Robin, 2026-10-22;
brief `docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-offline-update-94-2026-10-22.md`;
spec `ordpar/docs/offline-app.md` § 6):

* **The 15 minutes** (`offline.js` `due`): a check is due unless the last check that REACHED the
  site (`offline-update`'s `checked`, localStorage) is under 15 minutes old; a check that did not
  reach it writes `tried`, not `checked`; a `checked` in the future counts as due; no
  `sessionStorage` flag blocks a check any more.
* **The triggers**: the page's load, `visibilitychange` to visible and `pageshow` from the
  back-forward cache, each after the delay, one pending at a time, none while hidden; offline or
  without a copy, nothing is fetched.
* **An update's switch** writes the note's mark; the note shows once, with Reload and a close x,
  its words from `strings/en.json`; since site decisions 175 (2026-11-07) a link "What's new" to
  `/changes/` after the sentence, before the buttons; stacked above the install offer's bands (`install.js` `room`)
  and hidden while the suggestions are open (`shell.css`).
* **The article pages** (`page.PAGE_JS`): `offline.js` loaded only where the manifest in use is in
  Cache Storage (`caches.has` first), its `?v=` the shipped file's; nothing where offline.js is
  already loaded, nothing without a copy.

The JavaScript runs under `bun` (or node) with stand-ins for the storage, the DOM, Cache Storage
and fetch; skipped when neither is on PATH. No built site is read.
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
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")

from ordpar.sitegen import page  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run(js):
    runner = _runner()
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "t.js")
        with open(script, "w", encoding="utf-8") as f:
            f.write(js)
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
    out = res.stdout.decode("utf-8", "replace")
    if res.returncode != 0:
        raise AssertionError("JS failed: %s\n%s" % (res.stderr.decode("utf-8", "replace"), out))
    return json.loads(out.strip().splitlines()[-1])


#: Stand-ins enough for offline.js to load, check, update and show its note. `world` steers them:
#: `copy` (the manifest in use, or null), `version` (what version.json says, or 'fail'),
#: `manifest` (what manifest.json says), `online`.
HARNESS = r"""
const OFFLINE_SRC = %(src)s;
function storage() {
  const s = {};
  return { getItem: k => (k in s ? s[k] : null), setItem: (k, v) => { s[k] = String(v); },
           removeItem: k => { delete s[k]; }, clear: () => { for (const k in s) delete s[k]; },
           _s: s };
}
const world = { copy: { build: 'A', bundles: [], packs: [], total: 10 }, version: 'A',
                manifest: null, online: true, fetched: [], timers: [], opened: 0 };
function reset() {
  globalThis.localStorage = storage();
  globalThis.sessionStorage = storage();
  world.fetched = []; world.timers = []; world.opened = 0;
}
reset();
const winH = {}, docH = {};
globalThis.addEventListener = (t, f) => { (winH[t] = winH[t] || []).push(f); };
globalThis.setTimeout = (f, ms) => { world.timers.push(f); return world.timers.length; };
globalThis.clearTimeout = () => {};
function runTimers() { const ts = world.timers; world.timers = []; ts.forEach(f => f()); }
function fire(h, t, e) { (h[t] || []).forEach(f => f(e || {})); }
function node(tag) {
  return { tag, className: '', textContent: '', children: [], attrs: {}, style: {}, parentNode: null,
    offsetHeight: 40, isConnected: true,
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentNode = null; },
    setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(t, f) { (this.h = this.h || {})[t] = f; } };
}
const body = node('body');
globalThis.document = { readyState: 'loading', visibilityState: 'visible', body,
  documentElement: node('html'), createElement: node,
  addEventListener: (t, f) => { (docH[t] = docH[t] || []).push(f); },
  querySelector: sel => { const cls = sel.replace(/^\./, ''); return find(body, cls); } };
function find(n, cls) {
  for (const c of n.children) { if ((' ' + c.className + ' ').includes(' ' + cls + ' ')) return c;
    const f = find(c, cls); if (f) return f; }
  return null;
}
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: {
  get onLine() { return world.online; },
  serviceWorker: { register: () => Promise.resolve(), ready: Promise.resolve({ active: null }) } } });
const store = new Map();
function key(u) { return typeof u === 'string' ? u : u.url; }
const cache = {
  match: async u => { const p = new URL(key(u), 'https://x').pathname;
    if (p === '/offline/__current.json') return world.copy ? new Response(JSON.stringify(world.copy)) : undefined;
    return store.get(p); },
  put: async (u, r) => { const p = new URL(key(u), 'https://x').pathname;
    if (p === '/offline/__current.json') { world.copy = JSON.parse(await r.text()); } else store.set(p, r); },
  keys: async () => [...store.keys()].map(p => ({ url: 'https://x' + p })),
  delete: async k => store.delete(new URL(k.url).pathname),
};
globalThis.caches = { has: async () => !!world.copy, open: async () => { world.opened++; return cache; },
                      delete: async () => true };
globalThis.fetch = async (u) => {
  world.fetched.push(u);
  if (u.endsWith('version.json')) {
    if (world.version === 'fail') throw new TypeError('Failed to fetch');
    return new Response(JSON.stringify({ build: world.version, total: 10 }));
  }
  if (u.endsWith('manifest.json')) return new Response(JSON.stringify(world.manifest));
  return new Response('', { status: 404 });
};
globalThis.ordparShell = { t: k => STRINGS[k] || k };
const STRINGS = %(strings)s;
(0, eval)(OFFLINE_SRC);
const O = globalThis.ordparOffline;
const settle = () => new Promise(r => setTimeout === globalThis.setTimeout ? queueMicrotask(r) : r());
async function flush() { for (let i = 0; i < 30; i++) await Promise.resolve(); await new Promise(r => setImmediate ? setImmediate(r) : r()); for (let i = 0; i < 30; i++) await Promise.resolve(); }
const rec = () => JSON.parse(localStorage.getItem('offline-update') || 'null');
const versionFetches = () => world.fetched.filter(u => u.endsWith('version.json')).length;
const res = {};
"""


class TheRule(unittest.TestCase):
    """`due` and the record, under bun."""

    @classmethod
    def setUpClass(cls):
        if not _runner():
            raise unittest.SkipTest("neither bun nor node on PATH")
        strings = json.loads(_read(SITE, "strings", "en.json"))
        cls.head = HARNESS % {"src": json.dumps(_read(SITE, "offline.js")),
                              "strings": json.dumps(strings, ensure_ascii=False)}

    def run_js(self, body):
        return _run(self.head + "(async () => {\n" + body
                    + "\nconsole.log(JSON.stringify(res));})().catch(e => { console.error(e); process.exit(1); });")

    def test_due_counts_15_minutes_from_the_last_check_that_reached_the_site(self):
        r = self.run_js(r"""
const now = Date.parse('2026-10-22T12:00:00Z'), iso = m => new Date(now - m * 60000).toISOString();
res.none = O.due(null, now);
res.noChecked = O.due({ tried: iso(1) }, now);
res.m1 = O.due({ checked: iso(1) }, now);
res.m14 = O.due({ checked: iso(14.9) }, now);
res.m15 = O.due({ checked: iso(15) }, now);
res.m16 = O.due({ checked: iso(16) }, now);
res.future = O.due({ checked: iso(-60) }, now);
res.junk = O.due({ checked: 'x' }, now);
res.every = O.EVERY;
""")
        self.assertEqual(r, {"none": True, "noChecked": True, "m1": False, "m14": False,
                             "m15": True, "m16": True, "future": True, "junk": True,
                             "every": 900000})

    def test_triggers_and_the_15_minutes(self):
        r = self.run_js(r"""
// an old once-per-opening flag, as Android Chrome kept it: blocks nothing any more
sessionStorage.setItem('ordpar-offline-checked', '1');
fire(winH, 'load');
res.beforeTimer = versionFetches();
runTimers(); await flush();
res.afterLoad = versionFetches();
res.checked = !!(rec() && rec().checked);
// back to the screen within 15 minutes: no check
fire(docH, 'visibilitychange'); runTimers(); await flush();
res.within = versionFetches();
// a bfcache return within 15 minutes: none either
fire(winH, 'pageshow', { persisted: true }); runTimers(); await flush();
res.withinPageshow = versionFetches();
// the clock moved on 16 minutes (the record's checked put back): the return checks
const r0 = rec(); r0.checked = new Date(Date.now() - 16 * 60000).toISOString();
localStorage.setItem('offline-update', JSON.stringify(r0));
fire(docH, 'visibilitychange'); runTimers(); await flush();
res.after16 = versionFetches();
// pageshow from the bfcache after 16 minutes checks; a plain pageshow does not
r0.checked = new Date(Date.now() - 16 * 60000).toISOString();
localStorage.setItem('offline-update', JSON.stringify(r0));
fire(winH, 'pageshow', { persisted: false }); res.plainPageshowTimers = world.timers.length;
fire(winH, 'pageshow', { persisted: true }); runTimers(); await flush();
res.afterPageshow = versionFetches();
// several triggers at once: one pending, one check
r0.checked = new Date(Date.now() - 16 * 60000).toISOString();
localStorage.setItem('offline-update', JSON.stringify(r0));
fire(docH, 'visibilitychange'); fire(docH, 'visibilitychange'); fire(winH, 'pageshow', { persisted: true });
res.pendingTimers = world.timers.length;
runTimers(); await flush();
res.afterBurst = versionFetches();
// hidden when the delay ends: no check
r0.checked = new Date(Date.now() - 16 * 60000).toISOString();
localStorage.setItem('offline-update', JSON.stringify(r0));
fire(docH, 'visibilitychange'); document.visibilityState = 'hidden'; runTimers(); await flush();
res.hidden = versionFetches();
document.visibilityState = 'visible';
""")
        self.assertEqual(r["beforeTimer"], 0)
        self.assertEqual(r["afterLoad"], 1)
        self.assertTrue(r["checked"])
        self.assertEqual(r["within"], 1)
        self.assertEqual(r["withinPageshow"], 1)
        self.assertEqual(r["after16"], 2)
        self.assertEqual(r["plainPageshowTimers"], 0)
        self.assertEqual(r["afterPageshow"], 3)
        self.assertEqual(r["pendingTimers"], 1)
        self.assertEqual(r["afterBurst"], 4)
        self.assertEqual(r["hidden"], 4)

    def test_a_check_that_did_not_reach_the_site_does_not_start_the_15_minutes(self):
        r = self.run_js(r"""
world.version = 'fail';
res.first = await O.checkUpdate(false);
res.rec = rec();
world.version = 'A';
res.second = await O.checkUpdate(false);
res.reached = !!rec().checked;
res.third = await O.checkUpdate(false);
res.fetches = versionFetches();
""")
        self.assertEqual(r["first"], "unreachable")
        self.assertNotIn("checked", r["rec"])
        self.assertIn("tried", r["rec"])
        self.assertIn("checkError", r["rec"])
        self.assertEqual(r["second"], "current")
        self.assertTrue(r["reached"])
        self.assertIsNone(r["third"])         # within the 15 minutes
        self.assertEqual(r["fetches"], 2)

    def test_offline_or_without_a_copy_nothing_is_fetched(self):
        r = self.run_js(r"""
world.online = false;
res.offline = await O.checkUpdate(false);
world.online = true;
world.copy = null;
res.noCopy = await O.checkUpdate(false);
res.fetched = world.fetched.length;
res.rec = rec();
""")
        self.assertIsNone(r["offline"])
        self.assertIsNone(r["noCopy"])
        self.assertEqual(r["fetched"], 0)
        self.assertIsNone(r["rec"])

    def test_an_update_switches_and_the_note_shows_once(self):
        r = self.run_js(r"""
world.version = 'B';
world.manifest = { build: 'B', bundles: [], packs: [], total: 20 };
res.result = await O.checkUpdate(true);
res.copy = world.copy.build;
res.rec = rec();
const note = find(body, 'ordpar-update-note');
res.shown = !!note;
res.role = note && note.attrs.role;
const words = [], walk = n => { if (n.textContent) words.push(n.textContent); n.children.forEach(walk); };
if (note) walk(note);
res.words = words;
const x = note && find(note, 'ordpar-update-close');
res.xLabel = x && x.attrs['aria-label'];
// site decisions 175: "What's new", a link to /changes/ after the sentence, before the buttons
const link = note && find(note, 'ordpar-update-link');
res.link = link && { tag: link.tag, href: link.attrs.href, text: link.textContent, target: link.attrs.target || null };
res.padding = document.documentElement.style.paddingBottom;
// the next page: no second note for the same switch
O.showNote();
res.count = body.children.filter(c => c.className === 'ordpar-update-note').length;
x.h.click();
res.afterClose = !!find(body, 'ordpar-update-note');
res.paddingAfter = document.documentElement.style.paddingBottom;
// a switch whose page went before the note: the next page that loads offline.js shows it
localStorage.setItem('offline-update', JSON.stringify(Object.assign(rec(), { note: 'C' })));
O.showNote();
res.nextPage = !!find(body, 'ordpar-update-note');
res.cleared = !('note' in rec());
""")
        self.assertEqual(r["result"], "updated")
        self.assertEqual(r["copy"], "B")
        self.assertEqual(r["rec"]["result"], "updated")
        self.assertNotIn("note", r["rec"])      # cleared by the showing
        self.assertTrue(r["shown"])
        self.assertEqual(r["role"], "status")
        self.assertEqual(r["words"], ["Ordpar has been updated — reload to see it",
                                      "What's new", "Reload", "×"])
        # site decisions 175 (Robin, 2026-11-07): the link to the site's change list, same tab
        self.assertEqual(r["link"], {"tag": "a", "href": "/changes/", "text": "What's new", "target": None})
        self.assertEqual(r["xLabel"], "Close")
        self.assertEqual(r["padding"], "40px")
        self.assertEqual(r["count"], 1)
        self.assertFalse(r["afterClose"])
        self.assertEqual(r["paddingAfter"], "")
        self.assertTrue(r["nextPage"])
        self.assertTrue(r["cleared"])

    def test_a_check_already_current_keeps_the_record(self):
        r = self.run_js(r"""
localStorage.setItem('offline-update', JSON.stringify({ at: 'x', result: 'updated', bytes: 5, packs: 2 }));
res.result = await O.checkUpdate(false);
res.rec = rec();
""")
        self.assertEqual(r["result"], "current")
        self.assertEqual(r["rec"]["packs"], 2)          # kept (was dropped before decisions 94)
        self.assertEqual(r["rec"]["result"], "updated")
        self.assertIn("checked", r["rec"])


class TheArticlePage(unittest.TestCase):
    """`page.PAGE_JS`'s loader."""

    def loader(self):
        js = page.shipped(page.JS_HREF)
        a = js.index("var K='ordpar-offline-1'")
        return js[a:js.rindex("})();")]

    def test_the_loader_names_the_shipped_offline_js(self):
        js = page.shipped(page.JS_HREF)
        self.assertIn('o.src="%s"' % page.asset(page.OFFLINE_JS_HREF), js)
        self.assertEqual(page._offline_href(), page.asset(page.OFFLINE_JS_HREF))
        # inside the one combined script of the article and About pages
        self.assertIn(page.asset(page.OFFLINE_JS_HREF), page.shipped(page.JS_ALL_HREF))
        # no page grows: offline.js is not a part of ordpar.js
        self.assertNotIn(page.OFFLINE_JS_HREF, page.ARTICLE_JS_PARTS)

    def test_the_loader_asks_cache_storage_first(self):
        src = self.loader()
        self.assertLess(src.index("caches.has(K)"), src.index("caches.open(K)"))
        self.assertIn("'/offline/__current.json'", src)
        self.assertIn("!window.ordparOffline", src)

    def run_loader(self, copy, already=False):
        if not _runner():
            self.skipTest("neither bun nor node on PATH")
        js = r"""
const out = { opened: 0, added: [], fetched: 0 };
globalThis.fetch = () => { out.fetched++; return Promise.reject(new Error('no')); };
globalThis.caches = { has: async () => %(has)s, open: async () => { out.opened++; return {
  match: async u => (%(cur)s && u === '/offline/__current.json') ? { ok: true } : undefined }; } };
globalThis.window = globalThis;
%(already)s
const d = { createElement: t => ({ tag: t }), head: { appendChild: n => out.added.push(n.src) } };
%(src)s
setTimeout(() => console.log(JSON.stringify(out)), 50);
""" % {"has": "true" if copy in ("cache", "full") else "false",
       "cur": "true" if copy == "full" else "false",
       "already": "globalThis.ordparOffline = {};" if already else "",
       "src": self.loader()}
        return _run(js)

    def test_with_a_copy_offline_js_is_added(self):
        r = self.run_loader("full")
        self.assertEqual(r["added"], [page.asset(page.OFFLINE_JS_HREF)])
        self.assertEqual(r["fetched"], 0)

    def test_without_a_copy_nothing(self):
        r = self.run_loader(None)
        self.assertEqual(r, {"opened": 0, "added": [], "fetched": 0})

    def test_a_cache_without_the_manifest_in_use_nothing(self):
        r = self.run_loader("cache")      # a download stopped half-way
        self.assertEqual(r["added"], [])

    def test_where_offline_js_is_loaded_already_nothing(self):
        r = self.run_loader("full", already=True)
        self.assertEqual(r, {"opened": 0, "added": [], "fetched": 0})


class TheWiring(unittest.TestCase):

    def test_no_session_flag_left(self):
        src = _read(SITE, "offline.js")
        self.assertNotIn("sessionStorage", src)
        self.assertNotIn("ordpar-offline-checked", src)

    def test_the_triggers_are_wired(self):
        src = _read(SITE, "offline.js")
        self.assertIn("addEventListener('visibilitychange'", src)
        self.assertRegex(src, r"addEventListener\('pageshow', function \(e\) \{ if \(e\.persisted\)")
        self.assertIn("var EVERY = 15 * 60 * 1000;", src)

    def test_the_words(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["offline.noteUpdated"], "Ordpar has been updated — reload to see it")
        self.assertEqual(s["offline.noteReload"], "Reload")
        self.assertEqual(s["offline.noteClose"], "Close")
        self.assertEqual(s["offline.noteWhatsNew"], "What's new")       # site decisions 175
        # in the combined scripts' string table too
        self.assertIn('"offline.noteReload":"Reload"', page.shipped(page.JS_ALL_HREF))

    def test_the_bands_stack_and_the_suggestions_win(self):
        inst = _read(SITE, "install.js")
        self.assertIn("var BANDS = ['.ordpar-install-bar', '.ordpar-install-note', "
                      "'.ordpar-update-note'];", inst)
        self.assertIn("    room: room,\n", inst)
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-install-bar, .ordpar-install-note, .ordpar-update-note {\n"
                      "  position: fixed;", css)
        # decisions 92 (G): the install offer's bar and note hidden with the note
        self.assertIn("html:has(.ordpar-popup:not([hidden])) .ordpar-update-note,\n"
                      "html:has(.ordpar-popup:not([hidden])) .ordpar-install-bar,\n"
                      "html:has(.ordpar-popup:not([hidden])) .ordpar-install-note { visibility: hidden; }", css)

    def test_room_stacks_under_bun(self):
        if not _runner():
            self.skipTest("neither bun nor node on PATH")
        js = r"""
const els = {};
function n(h) { return { offsetHeight: h, style: {} }; }
globalThis.document = { documentElement: { style: {} }, body: {},
  querySelector: s => els[s] || null, addEventListener() {} };
globalThis.addEventListener = () => {};
globalThis.localStorage = { getItem: () => null, setItem() {} };
globalThis.sessionStorage = globalThis.localStorage;
globalThis.navigator = {};
%s
const I = globalThis.ordparInstall, out = {};
els['.ordpar-install-bar'] = n(70); els['.ordpar-update-note'] = n(50);
I.room();
out.bar = els['.ordpar-install-bar'].style.bottom; out.note = els['.ordpar-update-note'].style.bottom;
out.pad = document.documentElement.style.paddingBottom;
delete els['.ordpar-install-bar']; I.room();
out.note2 = els['.ordpar-update-note'].style.bottom; out.pad2 = document.documentElement.style.paddingBottom;
console.log(JSON.stringify(out));
""" % _read(SITE, "install.js")
        r = _run(js)
        self.assertEqual(r, {"bar": "", "note": "70px", "pad": "120px", "note2": "", "pad2": "50px"})


if __name__ == "__main__":
    unittest.main()
