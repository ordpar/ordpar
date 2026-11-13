# -*- coding: utf-8 -*-
"""Site decisions 68 (Robin, 2026-10-20): the install offer once per device, the line in
Settings → Offline, the phone-only footer hint. Spec: `ordpar/docs/offline-app.md` § 11; the
proposal (its wording, Robin's answers (a), (a), (a), "as written"):
`docs/sessions/2026-09-19-ordpar-site-review/walk-through/install-offer-68-proposal-2026-10-20.md`.
Stdlib unittest; the script's rules run under bun (or node), skipped when neither is on PATH.

What it pins:

* **The record's rules** (`ordpar/site/install.js` `mayOffer`, `afterShown`, `afterAnswer`):
  the bar may show only outside the installed app, never once answered ("Install", Chrome's
  dialog accepted or cancelled, "No thanks", or the app installed by any route), never after its
  second showing, and never twice in one browsing session — so an unanswered offer shows on a
  first visit, not on the next page, once more on a later visit, then never.
* **The same rules through the event** (a stand-in DOM and storage): every install event is
  cancelled (`preventDefault`) whether or not the bar shows; the bar's buttons record their
  answer; standalone shows nothing and writes nothing.
* **The Settings line's six cases** (`settingsCase`) in their order, and where the hint is made
  (`hintWanted`).
* **The wiring and the words**: `install.js` in both combined scripts, before `shell.js`;
  `offline.js` draws the line, `shell.js` `addChrome` asks for the hint; the proposal's texts in
  `strings/en.json` verbatim; the sheet's phone query; the manifest's `related_applications`
  entry for the site's own web app; the shipped script without comments.
"""
import json
import os
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


#: Storage, a window and a stand-in DOM, enough for install.js to show its bar and answer.
HARNESS = r"""
function storage() {
  const s = {};
  return { getItem: k => (k in s ? s[k] : null), setItem: (k, v) => { s[k] = String(v); },
           removeItem: k => { delete s[k]; }, clear: () => { for (const k in s) delete s[k]; } };
}
globalThis.localStorage = storage();
globalThis.sessionStorage = storage();
const handlers = {};
globalThis.addEventListener = (t, f) => { (handlers[t] = handlers[t] || []).push(f); };
globalThis.MEDIA = {};
globalThis.matchMedia = q => ({ matches: !!MEDIA[q] });
globalThis.BeforeInstallPromptEvent = function () {};
globalThis.setTimeout = (f) => { f(); return 0; };
globalThis.clearTimeout = () => {};
function node(tag) {
  return { tag, children: [], style: {}, attrs: {}, className: '', textContent: '', parentNode: null,
    offsetHeight: 90, listeners: {},
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentNode = null; return c; },
    setAttribute(k, v) { this.attrs[k] = String(v); }, getAttribute(k) { return this.attrs[k]; },
    addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
    click() { (this.listeners.click || []).forEach(f => f()); } };
}
const body = node('body');
function all(n, out) { out.push(n); n.children.forEach(c => all(c, out)); return out; }
globalThis.document = {
  body, documentElement: node('html'),
  createElement: node, createTextNode: t => ({ tag: '#text', textContent: t, children: [] }),
  addEventListener() {},
  querySelector(sel) {
    const cls = sel.split(',')[0].trim().replace(/^\./, '');
    return all(body, []).find(n => (' ' + n.className + ' ').includes(' ' + cls + ' ')) || null;
  }
};
globalThis.navigator = { userAgent: 'Mozilla/5.0 (Linux; Android 14) Chrome/140 Mobile' };
globalThis.ordparShell = { t: k => k };
let I = require(INSTALL);
// a new page: a fresh document body and a fresh copy of the script, as a navigation gives
function newPage() {
  for (const k in handlers) delete handlers[k];
  body.children = [];
  delete require.cache[require.resolve(INSTALL)];
  I = require(INSTALL);
}
function fire(outcome) {
  let prevented = false, prompted = 0;
  const e = { preventDefault() { prevented = true; }, prompt() { prompted++; },
              userChoice: Promise.resolve({ outcome: outcome || 'accepted' }) };
  handlers.beforeinstallprompt.forEach(f => f(e));
  return { prevented, get prompted() { return prompted; } };
}
function bar() { return document.querySelector('.ordpar-install-bar'); }
function buttons() { return all(bar(), []).filter(n => n.tag === 'button'); }
function rec() { return JSON.parse(localStorage.getItem('install-offer') || 'null'); }
function newSession() { sessionStorage.clear(); }
"""


def _run_js(body):
    """Run `body` after the harness; it must print JSON. Skips without bun/node."""
    runner = _runner()
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("const INSTALL = %s;\n" % json.dumps(os.path.join(SITE, "install.js"))
                     + HARNESS + "\n(async () => {\n" + body + "\n})();\n")
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8").strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class RecordRules(unittest.TestCase):
    """`mayOffer`, `afterShown`, `afterAnswer` — the device's record."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_js(r"""
const M = (r, s, a) => I.mayOffer(r, s, a);
const res = {
  fresh: M(null, false, false),
  shownOnce: M({ shown: 1 }, false, false),
  shownTwice: M({ shown: 2 }, false, false),
  sameSession: M({ shown: 1 }, true, false),
  standalone: M(null, false, true),
  answers: ['install', 'installed', 'dismissed', 'no'].map(a => M(I.afterAnswer({ shown: 1 }, a, 1), false, false)),
  installedOnly: M({ installed: true }, false, false),
  afterShown: I.afterShown({ shown: 1, answer: null }, 5),
  afterInstalled: I.afterAnswer({ shown: 1 }, 'installed', 7),
  afterNo: I.afterAnswer({ shown: 2 }, 'no', 8),
  untouched: (() => { const r = { shown: 1 }; I.afterShown(r, 1); I.afterAnswer(r, 'no', 1); return r; })(),
  max: I.MAX_SHOWN, key: I.REC, session: I.SESSION
};
// the visits of an offer never answered: [session, pages] -> did the bar show on each page
let r = null; const visits = [];
for (const pages of [3, 2, 2]) {
  let sessionShown = false; const seen = [];
  for (let i = 0; i < pages; i++) {
    const may = M(r, sessionShown, false);
    if (may) { r = I.afterShown(r, i); sessionShown = true; }
    seen.push(may);
  }
  visits.push(seen);
}
res.visits = visits;
console.log(JSON.stringify(res));
""")

    def test_first_visit_offers(self):
        self.assertTrue(self.out["fresh"])
        self.assertTrue(self.out["shownOnce"])

    def test_shown_twice_never_again(self):
        self.assertEqual(self.out["max"], 2)
        self.assertFalse(self.out["shownTwice"])

    def test_not_twice_in_one_session(self):
        self.assertFalse(self.out["sameSession"])

    def test_never_in_the_app(self):
        self.assertFalse(self.out["standalone"])

    def test_any_answer_ends_it(self):
        self.assertEqual(self.out["answers"], [False, False, False, False])
        self.assertFalse(self.out["installedOnly"])

    def test_records(self):
        self.assertEqual(self.out["afterShown"], {"shown": 2, "answer": None, "at": 5})
        self.assertEqual(self.out["afterInstalled"], {"shown": 1, "answer": "installed", "installed": True, "at": 7})
        self.assertEqual(self.out["afterNo"], {"shown": 2, "answer": "no", "at": 8})
        self.assertEqual(self.out["untouched"], {"shown": 1})
        self.assertEqual(self.out["key"], "install-offer")
        self.assertEqual(self.out["session"], "ordpar-install-shown")

    def test_unanswered_visits(self):
        # first visit: on its first page only; a later visit: once more; a third: nothing
        self.assertEqual(self.out["visits"], [[True, False, False], [True, False], [False, False]])


class ThroughTheEvent(unittest.TestCase):
    """The same rules driven by the install event in a stand-in page."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_js(r"""
const res = {};
// a first visit: the bar; the next page of the visit (the bar gone with the page): none
let f = fire();
res.first = { prevented: f.prevented, bar: !!bar(), rec: rec(), session: sessionStorage.getItem('ordpar-install-shown') };
newPage();
f = fire();
res.nextPage = { prevented: f.prevented, bar: !!bar() };
// a later visit: once more; a third: none, and the event is still cancelled
newPage(); newSession(); f = fire(); res.second = { bar: !!bar(), shown: rec().shown };
newPage();
newSession(); f = fire(); res.third = { prevented: f.prevented, bar: !!bar(), shown: rec().shown };
// No thanks
newPage(); localStorage.clear(); newSession(); fire();
buttons()[1].click();
res.no = { bar: !!bar(), rec: rec() };
newPage(); newSession(); fire(); res.afterNo = !!bar();
// Install, accepted
newPage(); localStorage.clear(); newSession(); f = fire('accepted');
buttons()[0].click();
await new Promise(r => Promise.resolve().then(r)); await null; await null; await null;
res.accepted = { prompted: f.prompted, bar: !!bar(), rec: rec() };
// Install, dismissed in Chrome's dialog
newPage(); localStorage.clear(); newSession(); f = fire('dismissed');
buttons()[0].click();
await null; await null; await null; await null;
res.dismissed = { prompted: f.prompted, rec: rec() };
newPage(); newSession(); fire(); res.afterDismissed = !!bar();
// in the app: nothing shown, nothing written, still cancelled
newPage(); localStorage.clear(); newSession(); MEDIA['(display-mode: standalone)'] = true;
f = fire(); res.app = { prevented: f.prevented, bar: !!bar(), rec: rec() };
console.log(JSON.stringify(res));
""")

    def test_first_and_next_page(self):
        self.assertTrue(self.out["first"]["prevented"])
        self.assertTrue(self.out["first"]["bar"])
        self.assertEqual(self.out["first"]["rec"]["shown"], 1)
        self.assertEqual(self.out["first"]["session"], "1")
        self.assertEqual(self.out["nextPage"], {"prevented": True, "bar": False})

    def test_second_and_third_visit(self):
        self.assertEqual(self.out["second"], {"bar": True, "shown": 2})
        self.assertEqual(self.out["third"], {"prevented": True, "bar": False, "shown": 2})

    def test_no_thanks(self):
        self.assertFalse(self.out["no"]["bar"])
        self.assertEqual(self.out["no"]["rec"]["answer"], "no")
        self.assertFalse(self.out["afterNo"])

    def test_install_accepted(self):
        a = self.out["accepted"]
        self.assertEqual(a["prompted"], 1)
        self.assertFalse(a["bar"])
        self.assertEqual(a["rec"]["answer"], "installed")
        self.assertTrue(a["rec"]["installed"])

    def test_install_dismissed(self):
        self.assertEqual(self.out["dismissed"]["prompted"], 1)
        self.assertEqual(self.out["dismissed"]["rec"]["answer"], "dismissed")
        self.assertFalse(self.out["afterDismissed"])

    def test_standalone(self):
        self.assertEqual(self.out["app"], {"prevented": True, "bar": False, "rec": None})


class SettingsCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _run_js(r"""
const C = e => I.settingsCase(e);
console.log(JSON.stringify({
  app: C({ standalone: true, event: true, chromium: true }),
  related: C({ relatedInstalled: true, event: true, chromium: true }),
  here: C({ installedHere: true, chromium: true }),
  offer: C({ event: true, chromium: true, recordInstalled: true }),
  record: C({ recordInstalled: true, chromium: true }),
  ios: C({ ios: true }),
  iosChromium: C({ ios: true, chromium: true }),
  menu: C({ chromium: true }),
  none: C({}),
  hintPhone: I.hintWanted({ touch: true, chromium: true }),
  hintIos: I.hintWanted({ touch: true, ios: true }),
  hintDesktop: I.hintWanted({ touch: false, chromium: true }),
  hintApp: I.hintWanted({ touch: true, chromium: true, standalone: true }),
  hintInstalled: I.hintWanted({ touch: true, chromium: true, relatedInstalled: true }),
  hintFirefox: I.hintWanted({ touch: true })
}));
""")

    def test_order(self):
        o = self.out
        self.assertEqual((o["app"], o["related"], o["here"]), ("app", "installed", "installed"))
        # an event means the app is not installed here, whatever an old record says
        self.assertEqual(o["offer"], "offer")
        self.assertEqual(o["record"], "installed")
        self.assertEqual((o["ios"], o["iosChromium"]), ("ios", "ios"))
        self.assertEqual(o["menu"], "menu")
        self.assertIsNone(o["none"])

    def test_hint(self):
        o = self.out
        self.assertTrue(o["hintPhone"])
        self.assertTrue(o["hintIos"])
        for k in ("hintDesktop", "hintApp", "hintInstalled", "hintFirefox"):
            self.assertFalse(o[k], k)


class Wiring(unittest.TestCase):

    def test_in_both_combined_scripts_before_shell(self):
        for parts in (page.ARTICLE_JS_PARTS, page.SHELL_JS_PARTS):
            self.assertIn("/site/install.js", parts)
            self.assertEqual(parts.index("/site/install.js") + 1, parts.index("/site/shell.js"))

    def test_hooks(self):
        self.assertIn("global.ordparInstall.line(t)", _read(SITE, "offline.js"))
        self.assertIn("global.ordparInstall.hint(links)", _read(SITE, "shell.js"))

    def test_shipped_without_comments(self):
        js = page.shipped("/site/install.js")
        self.assertNotIn("/*", js)
        self.assertNotIn("decisions 68", js)
        self.assertIn("beforeinstallprompt", page.shipped("/site/ordpar.js"))
        self.assertIn("beforeinstallprompt", page.shipped("/site/shell-pages.js"))

    def test_phone_query(self):
        css = _read(SITE, "shell.css")
        self.assertIn("@media (pointer: coarse) and (hover: none) and (max-width: 40rem),\n"
                      "       (pointer: coarse) and (hover: none) and (max-height: 40rem)", css)
        self.assertIn("@media (display-mode: standalone), (display-mode: fullscreen), "
                      "(display-mode: minimal-ui)", css)

    def test_manifest(self):
        with open(os.path.join(ORDPAR, "root", "manifest.webmanifest"), encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(m["related_applications"],
                         [{"platform": "webapp", "url": "https://ordpar.no/manifest.webmanifest"}])
        self.assertNotIn("prefer_related_applications", m)
        self.assertEqual((m["id"], m["scope"], m["start_url"]), ("/", "/", "/"))

    def test_words_verbatim(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        want = {
            "install.title": "Install Ordpar as an app",
            "install.text": "It opens from your home screen in its own window, and can keep the "
                            "whole dictionary for use offline.",
            "install.install": "Install",
            "install.no": "No thanks",
            "install.noteInstalled": "Installed. To use it offline, keep the whole dictionary in {link}.",
            "install.noteLater": "You can install it any time in {link}.",
            "install.link": "Settings → Offline",
            "install.can": "Ordpar can be installed as an app: it opens from your home screen or "
                           "desktop in its own window.",
            "install.button": "Install app",
            "install.inApp": "You're using the installed app.",
            "install.installed": "Ordpar is installed on this device.",
            "install.menu": "To install Ordpar, use your browser's menu: Install app (or Add to Home screen).",
            "install.ios": "To install Ordpar, tap Share in Safari, then Add to Home Screen.",
            "install.hint": "Install Ordpar as an app",
        }
        for k, v in want.items():
            self.assertEqual(s.get(k), v, k)


if __name__ == "__main__":
    unittest.main()
