# -*- coding: utf-8 -*-
"""Site decisions 158 (Robin, 2026-11-01): the list view also when a search finds inflected forms,
the new default.

The ruling: one more option for the search's list view: when there are any inflected-form hits,
the search page uses the list view, so a search opens straight to the article only when it has one
match and no inflected-form hits; and this is the default setting.

What can be pinned outside a browser:

* **The setting**: `listview` gains a fourth value, `forms`, listed first and the default (107:
  the default first); `multi`, `on` and `off` unchanged; a stored value kept, an unknown one read
  as `forms` (shell.js `getSetting`, under bun); the view's own fallback (`lookup.js` `listMode`)
  `forms` too.
* **The words**: the choice "When there are several articles, or inflected forms", its note
  "Counts the articles found as headwords, and any word found as an inflected form."; the
  `multi` choice and its note unchanged.
* **The rule** (`lookup.js` `useList(mode, n, f)`, `n` the articles found as headwords, `f` the
  articles found through an inflected form): the four cases under each of the four values — one
  headword hit and no form hit (the article, except under `on`), one hit and a form hit (the list
  under `forms` and `on`, the article under `multi` and `off`), several (the list under `forms`,
  `multi`, `on`), no headword hit and a form hit (as before 158: only `on` says list, and with no
  headword hit there is nothing to list either way). `render` passes the form hits (`formHits`).
* **Loading ahead** (`ahead.js` `warmSearch`): a search link's article page is fetched ahead only
  where the search will open it in full — by the same rule (`ordparLookup.useList`): *hus*-shaped
  (one headword, a form hit) fetches nothing under the default, its article under `multi`.
* **The address for a pop-up dictionary** (146): the head script's table carries `forms`, so
  `#listview=forms&q=…` parses (`sitegen/head.py` `settings_table`).

The browser side (computer and phone): `test_ordpar_browser_listview158.py`. Runs under bun (or
node) where noted; skipped without either.
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
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ORDPAR)

VALUES = ["forms", "multi", "on", "off"]


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _has(case, needle, hay, where):
    """assertIn without printing a whole script on failure."""
    case.assertTrue(needle in hay, "not in %s: %s" % (where, needle))


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run(body):
    runner = _runner()
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(body)
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


SHELL_STUB = """
const store = {};
globalThis.localStorage = {getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }, clear: () => {}};
const cl = {toggle() {}, add() {}, remove() {}, contains() { return false; }};
globalThis.document = {readyState: 'loading', documentElement: {classList: cl, setAttribute() {}, removeAttribute() {}},
  addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; }};
globalThis.matchMedia = () => ({matches: false, addEventListener() {}});
globalThis.navigator = {languages: ['en']};
"""


class TheSetting(unittest.TestCase):

    def test_a_fourth_value_first_and_the_default(self):
        js = _read(SITE, "shell.js")
        m = re.search(r"\{ key: 'listview', values: (\[[^\]]*\]), def: '(\w+)', section: 'search' \}", js)
        self.assertTrue(m, "no listview row in shell.js SETTINGS")
        self.assertEqual(json.loads(m.group(1).replace("'", '"')), VALUES)
        self.assertEqual(m.group(2), "forms")

    def test_b_stored_values_kept_the_unknown_read_as_the_default(self):
        body = SHELL_STUB + """
require(%s);
const S = globalThis.ordparShell, out = [S.getSetting('listview')];
for (const v of ['multi', 'on', 'off', 'forms', 'yes', '']) { store.listview = v; out.push(S.getSetting('listview')); }
delete store.listview; out.push(S.getSetting('listview'));
process.stdout.write(JSON.stringify(out));
""" % json.dumps(os.path.join(SITE, "shell.js"))
        self.assertEqual(_run(body), ["forms", "multi", "on", "off", "forms", "forms", "forms", "forms"])

    def test_c_the_view_falls_back_to_it_too(self):
        js = _read(SITE, "lookup.js")
        _has(self, "var v = shell && shell.getSetting ? shell.getSetting('listview') : 'forms';", js, "lookup.js")
        _has(self, "return v === 'on' || v === 'off' || v === 'multi' ? v : 'forms';", js, "lookup.js")

    def test_d_the_address_for_a_pop_up_carries_it(self):
        from sitegen import head
        table = dict(head.settings_table())
        self.assertEqual(table["listview"], VALUES)

    def test_e_the_export_carries_the_setting(self):
        self.assertIn("'listview'", _read(SITE, "personal.js").split("var SETTING_KEYS = [", 1)[1].split("];", 1)[0])


class TheWords(unittest.TestCase):

    def test_the_choice_and_its_note(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["settings.listview.forms"], "When there are several articles, or inflected forms")
        self.assertEqual(s["settings.listview.forms.note"],
                         "Counts the articles found as headwords, and any word found as an inflected form.")
        self.assertEqual(s["settings.listview.multi"], "Only when there are several articles")
        self.assertEqual(s["settings.listview.multi.note"],
                         "Counts the articles found as headwords; words found as an inflected form don't count.")
        self.assertEqual((s["settings.listview.on"], s["settings.listview.off"]), ("On", "Off"))


# (n headword articles, f inflected-form articles) -> the four cases of the brief
CASES = [(1, 0), (1, 2), (3, 0), (0, 1)]
WANT = {
    "forms": [False, True, True, False],
    "multi": [False, False, True, False],
    "on":    [False, True, True, True],
    "off":   [False, False, False, False],
}
WANT["on"][0] = True        # `on`: the list always, one hit included


class TheRule(unittest.TestCase):

    def test_a_use_list_four_cases_under_each_value(self):
        body = ("const L = require(%s).ordparLookup;\nconst cases = %s, values = %s, out = {};\n"
                "values.forEach(v => { out[v] = cases.map(c => L.useList(v, c[0], c[1])); });\n"
                "process.stdout.write(JSON.stringify(out));\n"
                % (json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(CASES), json.dumps(VALUES)))
        self.assertEqual(_run(body), WANT)

    def test_b_form_hits_counted_from_the_result(self):
        body = ("const L = require(%s).ordparLookup;\n"
                "process.stdout.write(JSON.stringify([L.formHits({forms: []}), L.formHits({}),"
                " L.formHits({forms: [{form: 'hus', articles: [{id: 1}]}, {form: 'hus', articles: [{id: 2}, {id: 3}]}]}),"
                " L.formHits({forms: [{form: 'x', articles: []}]})]));\n"
                % json.dumps(os.path.join(SITE, "lookup.js")))
        self.assertEqual(_run(body), [0, 0, 3, 0])

    def test_c_render_passes_them(self):
        js = _read(SITE, "lookup.js")
        _has(self, "list = useList(mode, n, formHits(res));", js, "lookup.js")


AHEAD = SHELL_STUB + """
const fetched = [];
globalThis.location = {origin: 'https://x.test', pathname: '/bm-en/', search: '', hash: ''};
globalThis.fetch = url => { fetched.push(url); return Promise.resolve({ok: true, text: () => Promise.resolve('')}); };
require(%(lookup)s);
const L = globalThis.ordparLookup;
const RES = {
  hus: {heads: [{form: 'hus', articles: [{id: 101}]}], forms: [{form: 'hus', articles: [{id: 202}]}], count: 2},
  vindu: {heads: [{form: 'vindu', articles: [{id: 303}]}], forms: [], count: 1},
};
L.lookup = q => Promise.resolve(RES[q]);
globalThis.ordparShell = {getSetting: k => (k === 'listview' ? store.listview || 'forms' : null)};
const AHEAD_JS = %(ahead)s;
(async () => {
  const out = {};
  for (const v of ['forms', 'multi', 'on', 'off']) {
    store.listview = v;
    for (const q of ['hus', 'vindu']) {
      // a fresh copy each time: ahead.js fetches each page once per page view
      delete require.cache[require.resolve(AHEAD_JS)];
      require(AHEAD_JS);
      const A = globalThis.ordparAhead;
      fetched.length = 0;
      await A.warm('/bm-en/#q=' + q);
      out[v + ':' + q] = fetched.filter(u => /^\\/bm-en\\/\\d+\\/$/.test(u));
    }
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


class LoadingAhead(unittest.TestCase):

    def test_the_article_fetched_ahead_only_where_it_opens(self):
        got = _run(AHEAD % {"lookup": json.dumps(os.path.join(SITE, "lookup.js")),
                            "ahead": json.dumps(os.path.join(SITE, "ahead.js"))})
        self.assertEqual(got, {
            "forms:hus": [], "forms:vindu": ["/bm-en/303/"],
            "multi:hus": ["/bm-en/101/"], "multi:vindu": ["/bm-en/303/"],
            "on:hus": [], "on:vindu": [],
            "off:hus": ["/bm-en/101/"], "off:vindu": ["/bm-en/303/"],
        })

    def test_ahead_asks_the_view_s_rule(self):
        _has(self, "L.useList(lv, ids.length, L.formHits ? L.formHits(res) : 0)", _read(SITE, "ahead.js"), "ahead.js")


if __name__ == "__main__":
    unittest.main()
