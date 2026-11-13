# -*- coding: utf-8 -*-
"""Site-review decisions 146 (Robin, 2026-10-27/28): the reader's settings in the address, for a
pop-up dictionary such as Definer; a Copy on `/more/` and in Settings. The source side; the browser
side is `test_ordpar_browser_settingsaddr146.py`.

* **The parser** (the head script, `sitegen/head.py` `THEME_JS`, run under bun or node against a
  stand-in page): of the fragment's `key=value` pairs it keeps only the settings table's keys with a
  value that key accepts — an unknown key, a bad value, a colour no scheme has, `__proto__` are
  ignored, never an error; an address naming a setting starts the visit (kept in
  `sessionStorage`, never written to `localStorage`) and loses its settings part (`#q=hus` left);
  a page opened without them takes the tab's visit; `/settings/` takes none; the classes before the
  first paint follow the visit; with the storage blocked the address still applies to its page.
  The table is `shell.js` `SETTINGS`, read from that file (`head.settings_table`): the same keys,
  in the same order, as the shell's `KEYS` — no second list.
* **The address the Copy gives** (`shell.js` `popupAddress`, the real file loaded on a stand-in
  page): with every setting at its default — none saved, or each saved at its default — exactly
  `https://ordpar.no/bm-en/#q={{str}}`; from changed settings those and no others, in the table's
  order, `{{str}}` last; from the SAVED settings even while a visit is in force; the colour's
  default scheme and a value a key does not accept left out.
* **The round trip**, for every key and every value other than its default: saved -> address ->
  parsed by the head script -> the same settings; and all keys changed at once.
* **The search's address**: `lookup.js` reads the search after settings (`#defs=en&q=hus` -> hus,
  `hashQuery`), so History stores the plain search (its entries hold the query, never the
  address); Favourites store an article, no address; the history page's links and every writer of
  a search's address write `#q=` alone.
* **Every reader of a stored setting goes through the visit**: `shell.js` `read`, `mini.js`,
  `ahead.js`, `events.js` (the statistics opt-out), the article script's inflection setting.
* **The words**, exactly: `strings/en.json` (Settings' button, its line and link, "Address
  copied.", Copy / Copied) and `more.md` (step 4, the sentence after step 8, the theme sentence,
  the leading comment naming 146); `about.py` marks the step-4 line `data-ordpar-popup`, its text
  the default address.

Stdlib unittest; the JS parts under bun or node (skipped without either).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
SITE = os.path.join(REPO, "ordpar", "site")

from ordpar.sitegen import about, colours, head, page  # noqa: E402

PLAIN = "https://ordpar.no/bm-en/#q={{str}}"


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _run(body):
    runner = shutil.which("bun") or shutil.which("node")
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run146.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(body)
        res = subprocess.run([runner, script], capture_output=True, timeout=120)
        out = res.stdout.decode("utf-8", "replace")
        if res.returncode != 0:
            raise AssertionError("JS failed:\n" + out + res.stderr.decode("utf-8", "replace"))
        return json.loads(out.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


#: The stand-in page both halves run on: a storage of its own each, a fragment, the head script
#: (`head(hash, path)`, -> what it left behind) and the shell (`shell(saved)`, the real file).
PRELUDE = r"""
const fs = require('fs');
const THEME = %(theme)s;
const SHELL_SRC = fs.readFileSync(%(shell)s, 'utf8');
function store(init, log, throws) {
  const m = Object.assign({}, init || {});
  return { getItem(k) { if (throws) throw new Error('blocked'); return Object.prototype.hasOwnProperty.call(m, k) ? m[k] : null; },
           setItem(k, v) { if (throws) throw new Error('blocked'); if (log) log.push([k, String(v)]); m[k] = String(v); },
           removeItem(k) { delete m[k]; }, clear() { for (const k in m) delete m[k]; }, _m: m };
}
function page(hash, path, saved, session, blocked) {
  const cls = new Set(), attrs = {}, writes = [], replaced = [];
  globalThis.window = globalThis;
  globalThis.document = {
    documentElement: { classList: { add: c => cls.add(c), remove: c => cls.delete(c), contains: c => cls.has(c),
                                    toggle: (c, on) => { if (on) cls.add(c); else cls.delete(c); } },
                       setAttribute(n, v) { attrs[n] = v; }, removeAttribute(n) { delete attrs[n]; },
                       hasAttribute(n) { return n in attrs; } },
    querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
    readyState: 'complete', addEventListener() {}
  };
  globalThis.localStorage = store(saved, writes, blocked);
  globalThis.sessionStorage = session || store({}, null, blocked);
  globalThis.location = { hash: hash || '', pathname: path || '/bm-en/', search: '' };
  globalThis.history = { state: { keep: 1 }, replaceState(st, t, url) { replaced.push([st, url]); } };
  delete globalThis.ordparRead; delete globalThis.ordparVisit; delete globalThis.ordparShell;
  return { cls, attrs, writes, replaced };
}
function head(hash, path, saved, session, blocked) {
  const p = page(hash, path, saved, session, blocked);
  (0, eval)(THEME);
  return { visit: window.ordparVisit.settings, classes: [...p.cls].sort(), accent: p.attrs['data-accent'] || null,
           writes: p.writes, replaced: p.replaced, read: k => window.ordparRead(k),
           session: globalThis.sessionStorage };
}
function shell() {
  globalThis.ORDPAR_STRINGS = { en: {} };
  try { Object.defineProperty(globalThis, 'navigator', { value: { languages: ['en'] }, configurable: true, writable: true }); } catch (e) {}
  globalThis.matchMedia = undefined;
  (0, eval)(SHELL_SRC);
  return globalThis.ordparShell;
}
const out = {};
"""


def _prelude():
    return PRELUDE % {"theme": json.dumps(head.THEME_JS), "shell": json.dumps(os.path.join(SITE, "shell.js"))}


class TheTable(unittest.TestCase):

    def test_one_source(self):
        got = _run(_prelude() + r"""
page('', '/');
const S = shell();
out.keys = S.KEYS;
out.table = S.SETTINGS.map(sp => [sp.key, sp.values]);
process.stdout.write(JSON.stringify(out));""")
        table = head.settings_table()
        self.assertEqual([k for k, _v in table], got["keys"])
        ids = [c["id"] for c in colours.COLOURS]
        for (key, values), (k2, v2) in zip(table, got["table"]):
            self.assertEqual(key, k2)
            self.assertEqual(values, ids if key == "colour" else v2, key)
        self.assertEqual(dict(table)["lang"], ["en"])
        # every key and its values in the head script's own copy of the table
        self.assertIn(json.dumps(dict(table), separators=(",", ":")), head.THEME_JS)
        self.assertEqual(head.VISIT_KEY, "ordpar-visit")


class TheParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = _run(_prelude() + r"""
let h = head('#defs=en&theme=dark&mini=en&q=hus', '/bm-en/');
out.basic = { visit: h.visit, classes: h.classes, writes: h.writes, replaced: h.replaced,
              session: h.session._m['ordpar-visit'] || null };
h = head('#foo=bar&defs=xx&colour=pink&exlimit=11&stats=off&colour=burnt-orange&q=hus', '/bm-en/');
out.bad = { visit: h.visit, replaced: h.replaced, accent: h.accent };
h = head('#__proto__=x&constructor=y&hasOwnProperty=z&toString=1&q=a', '/bm-en/');
out.proto = { visit: h.visit, replaced: h.replaced };
h = head('#colour=pink&q=a', '/bm-en/', {}, store({ 'ordpar-visit': '{"defs":"en"}' }));
out.badonly = { visit: h.visit, replaced: h.replaced };
// a page opened without settings takes the tab's visit; the saved settings underneath
const tab = store({ 'ordpar-visit': JSON.stringify({ defs: 'no', theme: 'dark', bogus: 'x', mini: 'nope' }) });
h = head('', '/bm-en/hus/', { theme: 'light', peek: 'off' }, tab);
out.carried = { visit: h.visit, classes: h.classes, theme: h.read('theme'), peek: h.read('peek'),
                replaced: h.replaced };
// the settings page: none of it, though the tab has a visit
h = head('#theme=dark', '/settings/', { theme: 'light' }, store({ 'ordpar-visit': '{"defs":"en"}' }));
out.settings = { visit: h.visit, classes: h.classes, theme: h.read('theme'), replaced: h.replaced,
                 session: h.session._m['ordpar-visit'] };
h = head('', '/settings/index.html', {}, store({ 'ordpar-visit': '{"defs":"en"}' }));
out.settingsIndex = { visit: h.visit };
// storage blocked (a frame whose storage the browser refuses): the address still applies here
h = head('#theme=dark&defs=en&q=hus', '/bm-en/', {}, null, true);
out.blocked = { visit: h.visit, classes: h.classes, replaced: h.replaced };
// no settings in the address and no visit: the saved settings, nothing replaced
h = head('#q=hus', '/bm-en/', { defs: 'en' });
out.none = { visit: h.visit, classes: h.classes, replaced: h.replaced };
h = head('#q=hus&random', '/bm-en/', {});
out.random = { replaced: h.replaced };
h = head('#exlimit=3&q=hus&random', '/bm-en/', {});
out.randomSet = { visit: h.visit, replaced: h.replaced };
process.stdout.write(JSON.stringify(out));""")

    def test_the_address_applied_and_kept_for_the_visit(self):
        b = self.r["basic"]
        self.assertEqual(b["visit"], {"defs": "en", "theme": "dark", "mini": "en"})
        for c in ("nightMode", "ordpar-defs-en", "ordpar-mini-en", "ordpar-js"):
            self.assertIn(c, b["classes"])
        self.assertEqual(b["writes"], [], "nothing written to localStorage")
        self.assertEqual(json.loads(b["session"]), {"defs": "en", "theme": "dark", "mini": "en"})
        # the settings part taken off the address, the entry's state kept
        self.assertEqual(b["replaced"], [[{"keep": 1}, "/bm-en/#q=hus"]])

    def test_unknown_and_bad_ignored(self):
        b = self.r["bad"]
        self.assertEqual(b["visit"], {"stats": "off", "colour": "burnt-orange"})
        self.assertEqual(b["accent"], "burnt-orange")
        # every pair of the table's keys off the address, valid or not; the unknown key stays
        self.assertEqual(b["replaced"][0][1], "/bm-en/#foo=bar&q=hus")
        p = self.r["proto"]
        self.assertIsNone(p["visit"])
        self.assertEqual(p["replaced"], [])
        # an address naming a setting, none valid: a new visit, empty (the tab's old one dropped)
        self.assertEqual(self.r["badonly"]["visit"], {})
        self.assertEqual(self.r["badonly"]["replaced"][0][1], "/bm-en/#q=a")

    def test_the_visit_carried_to_the_next_page(self):
        c = self.r["carried"]
        self.assertEqual(c["visit"], {"defs": "no", "theme": "dark"})   # checked against the table again
        self.assertIn("nightMode", c["classes"])
        self.assertIn("ordpar-defs-no", c["classes"])
        self.assertIn("ordpar-peek-off", c["classes"])     # a saved setting the visit does not name
        self.assertEqual(c["theme"], "dark")
        self.assertEqual(c["peek"], "off")
        self.assertEqual(c["replaced"], [])

    def test_not_on_the_settings_page(self):
        s = self.r["settings"]
        self.assertIsNone(s["visit"])
        self.assertNotIn("nightMode", s["classes"])
        self.assertEqual(s["theme"], "light")
        self.assertIsNone(self.r["settingsIndex"]["visit"])

    def test_storage_blocked(self):
        b = self.r["blocked"]
        self.assertEqual(b["visit"], {"theme": "dark", "defs": "en"})
        self.assertIn("nightMode", b["classes"])
        self.assertIn("ordpar-defs-en", b["classes"])

    def test_no_settings_no_change(self):
        n = self.r["none"]
        self.assertIsNone(n["visit"])
        self.assertIn("ordpar-defs-en", n["classes"])
        self.assertEqual(n["replaced"], [])
        self.assertEqual(self.r["random"]["replaced"], [])
        rs = self.r["randomSet"]
        self.assertEqual(rs["visit"], {"exlimit": "3"})
        self.assertEqual(rs["replaced"][0][1], "/bm-en/#q=hus&random")


#: For the round trip: each key's values other than its default (the colour's other schemes; the
#: language has no other value today, so it is parsed but never written — `popupAddress`)
def _changes():
    out = {}
    js = _read(SITE, "shell.js")
    for key, values in head.settings_table():
        if key == "lang":
            continue
        if key == "colour":
            out[key] = [c for c in values if c != colours.DEFAULT]
            continue
        d = re.search(r"\{ key: '%s', values: \[[^\]]*\], def: '([^']*)'" % key, js).group(1)
        out[key] = [v for v in values if v != d]
    return out


class TheAddress(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.changes = _changes()
        cls.r = _run(_prelude() + r"""
const CHANGES = %s;
function addr(saved, hash, path) {
  head(hash || '', path || '/more/', saved, null);
  return shell().popupAddress();
}
out.none = addr({});
out.defaults = addr({ theme: 'system', colour: 'wine', lang: 'en', defs: 'both', mini: 'article', stats: 'on', exlimit: 'all' });
out.changed = addr({ mini: 'en', defs: 'en', theme: 'dark', colour: 'burnt-orange', stats: 'off', exlimit: '3', bogus: 'x', peek: 'nope' });
// a visit in force on /more/ (opened with settings in its address): the copy still the saved ones
out.visit = addr({ defs: 'en' }, '#theme=dark&mini=en&q=x', '/more/');
out.visitShown = window.ordparShell.getSetting('theme');
out.visitSaved = window.ordparShell.savedSetting('theme');
// the round trip: saved -> address -> parsed -> the same settings
out.trips = [];
for (const key in CHANGES) {
  for (const v of CHANGES[key]) {
    const a = addr({ [key]: v });
    const h = head(a.slice(a.indexOf('#')), '/bm-en/', {});
    out.trips.push({ key, v, address: a, parsed: h.visit, left: h.replaced.length ? h.replaced[0][1] : null });
  }
}
const all = {};
for (const key in CHANGES) all[key] = CHANGES[key][0];
out.all = { saved: all, address: addr(all) };
const back = head(out.all.address.slice(out.all.address.indexOf('#')), '/bm-en/', {});
out.all.parsed = back.visit;
out.all.left = back.replaced[0][1];
process.stdout.write(JSON.stringify(out));""" % json.dumps(cls.changes))

    def test_all_defaults_is_the_plain_address(self):
        self.assertEqual(self.r["none"], PLAIN)
        self.assertEqual(self.r["defaults"], PLAIN)
        self.assertEqual(about.POPUP_ADDRESS, PLAIN)

    def test_changed_settings_only_in_the_tables_order(self):
        self.assertEqual(self.r["changed"], "https://ordpar.no/bm-en/#theme=dark&colour=burnt-orange&defs=en"
                                            "&exlimit=3&mini=en&stats=off&q={{str}}")
        self.assertTrue(self.r["changed"].endswith("&q={{str}}"))

    def test_from_the_saved_settings_during_a_visit(self):
        self.assertEqual(self.r["visit"], "https://ordpar.no/bm-en/#defs=en&q={{str}}")
        self.assertEqual(self.r["visitShown"], "dark")
        self.assertEqual(self.r["visitSaved"], "system")

    def test_the_round_trip_for_every_key(self):
        trips = self.r["trips"]
        want = sum(len(v) for v in self.changes.values())
        self.assertEqual(len(trips), want)
        self.assertEqual({t["key"] for t in trips}, set(self.changes))
        for t in trips:
            with self.subTest(key=t["key"], value=t["v"]):
                self.assertEqual(t["address"], "https://ordpar.no/bm-en/#%s=%s&q={{str}}" % (t["key"], t["v"]))
                self.assertEqual(t["parsed"], {t["key"]: t["v"]})
                self.assertEqual(t["left"], "/bm-en/#q={{str}}")
        a = self.r["all"]
        self.assertEqual(a["parsed"], a["saved"])
        self.assertEqual(a["left"], "/bm-en/#q={{str}}")
        keys = [k for k, _v in head.settings_table() if k in a["saved"]]
        self.assertEqual(a["address"], "https://ordpar.no/bm-en/#" + "&".join(
            "%s=%s" % (k, a["saved"][k]) for k in keys) + "&q={{str}}")


class TheSearchAddress(unittest.TestCase):

    def test_the_search_read_after_settings(self):
        got = _run(r"""
const L = require(%s);
const S = L.ordparSearch;
const out = {};
for (const h of ['#q=hus', '#defs=en&q=hus', '#defs=en&theme=dark&q=b%%C3%%A5t', '#xq=no', '#data', '#q=hus&random']) {
  globalThis.location = { hash: h, search: '', pathname: '/bm-en/' };
  out[h] = [S.hashQuery(h), S.queryFromLocation()];
}
out.url = L.ordparLookup.searchUrl('hus');
process.stdout.write(JSON.stringify(out));""" % json.dumps(os.path.join(SITE, "lookup.js")))
        self.assertEqual(got["#q=hus"], ["hus", "hus"])
        self.assertEqual(got["#defs=en&q=hus"], ["hus", "hus"])
        self.assertEqual(got["#defs=en&theme=dark&q=b%C3%A5t"], ["b%C3%A5t", "båt"])
        self.assertEqual(got["#xq=no"], [None, ""])
        self.assertEqual(got["#data"], [None, ""])
        self.assertEqual(got["#q=hus&random"], ["hus", "hus"])
        self.assertEqual(got["url"], "/bm-en/#q=hus")

    def test_history_and_favourites_store_no_settings(self):
        lk = _read(SITE, "lookup.js")
        # History stores the search as read from the address (the query), never the address
        rec = lk.split("function recordSearch(q, res, shownP, t) {")[1].split("\n  }\n")[0]
        self.assertIn("P.recordSearch({ q: q, n: n }, t)", rec)
        self.assertNotIn("location", rec)
        pp = _read(SITE, "personal-page.js")
        self.assertIn("a.href = base() + 'bm-en/#q=' + encodeURIComponent(e.q);", pp)
        pj = _read(SITE, "personal.js")
        self.assertNotIn("location.hash", pj)
        self.assertNotIn("location.href", pj)
        # the search's writers write `#q=` alone
        self.assertIn("function searchUrl(q) { return config.base + 'bm-en/#q=' + encodeURIComponent(q); }", lk)
        self.assertNotIn("popupAddress", lk)

    def test_the_readers_parse_through_hashquery(self):
        lk = _read(SITE, "lookup.js")
        self.assertNotIn("/^#q=([^&]*)/", lk)
        self.assertNotIn("hash.indexOf('#q=')", lk)
        self.assertNotIn("url.hash.indexOf('#q=')", lk)
        ah = _read(SITE, "ahead.js")
        # site decisions 180: the search read from the fragment wherever it stands (a drawn mark
        # `&random` after it no longer stops it), still after settings
        self.assertIn("var m = /(?:^#|&)q=([^&#]*)/.exec(hash), en = false;", ah)
        self.assertIn("bm-en\\/#(?:[a-z]+=[a-z0-9-]*&)*q=[^#]+", ah)
        self.assertNotIn("url.hash.indexOf('#q=')", ah)


class TheReaders(unittest.TestCase):

    def test_every_reader_through_the_visit(self):
        self.assertIn("if (typeof global.ordparRead === 'function') { return global.ordparRead(key); }",
                      _read(SITE, "shell.js"))
        self.assertIn("global.ordparRead('minifetch')", _read(SITE, "ahead.js"))
        self.assertIn("global.ordparRead(STATS_KEY) === 'off'", _read(SITE, "events.js"))
        self.assertIn("v = global.ordparRead(key);", _read(SITE, "mini.js"))
        self.assertIn("window.ordparRead?window.ordparRead('infl'):localStorage.getItem('infl')", page.PAGE_JS)
        self.assertIn("var s={getItem:W.ordparRead}", head.THEME_JS)
        # the only other reads of localStorage are not settings: the records of the offline copy and
        # the install offer, History and Favourites, the saved read itself, the export's raw read
        for name in ("ahead.js", "events.js", "mini.js"):
            js = _read(SITE, name)
            self.assertEqual(js.count("localStorage.getItem("), 1, name)    # the fallback without the head script


class TheWords(unittest.TestCase):

    def test_settings_strings(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["settings.popup"], "Copy the address for a pop-up dictionary")
        self.assertEqual(s["settings.popupNote"].replace("{link}", s["settings.popupLink"]),
                         "An address that opens Ordpar with your current settings, for a pop-up dictionary "
                         "such as Definer. How to set one up: More ways to use Ordpar.")
        self.assertEqual(s["settings.popupLink"], "More ways to use Ordpar")
        self.assertEqual(s["settings.popupDone"], "Address copied.")
        self.assertEqual(s["code.copy"], "Copy")
        self.assertEqual(s["code.copied"], "Copied")
        js = _read(SITE, "settings.js")
        self.assertIn("a.href = base() + 'more/#popup';", js)
        self.assertIn("say(t('settings.popupDone'))", js)

    def test_more_words(self):
        src = _read(about.MORE_SOURCE)
        lead = src[:src.index("-->")]
        self.assertIn("site decisions 146 (2026-10-28)", lead)
        body = src[src.index("-->") + 3:]
        self.assertIn("4. In the URL field, paste the address below. If you have changed any settings on "
                      "ordpar.no, the address carries them, so the pop-up shows articles the way you see "
                      "them here:\n   `https://ordpar.no/bm-en/#q={{str}}`\n", body)
        self.assertIn("8. Select a word on a page and press Definer's icon.\n\nIf you change your settings "
                      "later, copy the address again, here or at the bottom of Settings, and paste it over "
                      "the old one in Definer's URL field.\n\n", body)
        self.assertIn("\n\nA word with several articles", body)
        self.assertIn("The pop-up follows your browser's light or dark mode, unless you have chosen one in "
                      "Settings.", body)
        self.assertNotIn("light or dark mode. ", body)

    def test_the_page_marks_the_line(self):
        _t, body = about.more_page()
        codes = re.findall(r'<div class="ordpar-code"><code([^>]*)>(.*?)</code></div>', body)
        self.assertEqual(codes[0], (" data-ordpar-popup", PLAIN))
        self.assertEqual(codes[1][0], "")
        js = _read(SITE, "shell.js")
        self.assertIn("if (code.hasAttribute('data-ordpar-popup')) { code.textContent = popupAddress(); }", js)
        self.assertIn("var POPUP_ADDRESS = 'https://ordpar.no/bm-en/#';", js)
        self.assertIn("var POPUP_WORD = 'q={{str}}';", js)
        # both lines alike: a button each (one rule), and the line still selected by one click
        self.assertIn(".ordpar-code.has-copy{display:flex;", page.PAGE_CSS)
        self.assertIn("user-select:all", re.search(r"\.ordpar-code code\{(.*?)\}", page.PAGE_CSS, re.S).group(1))


class TheReadersChoiceEndsTheVisit(unittest.TestCase):
    """The session's call (2026-10-28): a setting the reader changes in a tab with a visit ends the
    visit's value for that key, and "Reset settings" the whole visit, on this page and the tab's
    next ones (`shell.js` `leaveVisit`); the visit's other keys hold."""

    @classmethod
    def setUpClass(cls):
        cls.r = _run(_prelude() + r"""
const S = store({});
const first = head('#theme=dark&defs=en&q=hus', '/bm-en/', {}, S);
out.first = Object.assign({}, first.visit);   // a copy: leaveVisit changes the object itself
const sh = shell();
const tries = [];
try { sh.setSetting('defs', 'no'); } catch (e) { tries.push(String(e)); }
out.afterSet = { here: window.ordparRead('defs'), theme: window.ordparRead('theme'),
                 session: JSON.parse(S.getItem('ordpar-visit')) };
const next = head('#q=hus', '/bm-en/', { defs: 'no' }, S);
out.next = Object.assign({}, next.visit);
shell();
try { window.ordparShell.resetSettings(); } catch (e) { tries.push(String(e)); }
out.afterReset = { here: window.ordparRead('theme'), session: S.getItem('ordpar-visit') };
out.last = head('#q=hus', '/bm-en/', {}, S).visit;
out.errors = tries;
process.stdout.write(JSON.stringify(out));""")

    def test_the_same_key_as_the_head_script(self):
        self.assertIn("var VISIT_KEY = %s;" % json.dumps(head.VISIT_KEY).replace('"', "'"), _read(SITE, "shell.js"))

    def test_a_changed_setting_leaves_the_visit(self):
        self.assertEqual(self.r["errors"], [])
        self.assertEqual(self.r["first"], {"theme": "dark", "defs": "en"})
        self.assertEqual(self.r["afterSet"], {"here": "no", "theme": "dark", "session": {"theme": "dark"}})
        self.assertEqual(self.r["next"], {"theme": "dark"})

    def test_reset_ends_the_visit(self):
        self.assertIsNone(self.r["afterReset"]["session"])
        self.assertIsNone(self.r["afterReset"]["here"])
        self.assertIsNone(self.r["last"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
