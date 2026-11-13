# -*- coding: utf-8 -*-
"""Pins site decisions 88 as amended (Robin, 2026-10-22; brief
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-history-favourites-88b-89-2026-10-22.md`
part A) — the recording side; the drawing side is `test_ordpar_history88.py`:

* **A search records the articles whose own headword it matched** (`lookup.js` `recordSearch`):
  the inflected-form rows are not counted, and a search that found only inflected forms records
  nothing ("a search with only inflected-form results records nothing until one is opened").
* **One translated article is written at once, then filled** (site decisions 129, 2026-10-25):
  the entry without its text the moment the search answers, so a page left before the article
  arrives keeps it, then the same entry (the same query, the same time) with the text; the
  history ends with ONE entry. Before 129 the entry waited for the text, and a reader who left
  early on a slow connection lost it (`test_ordpar_browser_history129.py` is the browser check).
* **Opening an inflected-form result records its headword** (`recordOpened`): a stand-in entry
  at once, replaced by what a search for the headword records (the same query, the same time);
  the history ends with ONE entry for it.
* **The link's click** (`recordOnOpen`, wired to every "is an inflected form of" row): a plain
  click waits for the entry, then follows the link; a click for a new tab or window, or a middle
  click, records without holding the link.

`lookup.js` runs under bun (or node) over a synthetic index built by `build_index.write_index`,
with a stand-in `ordparPersonal` that logs its calls, or the real `personal.js` over an
in-memory localStorage. Skipped when neither runner is on PATH."""

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


def _art(aid, lemma, pos, hg=0, forms=()):
    return {"id": aid, "data": {"lemmas": [{
        "lemma": lemma, "hgno": hg,
        "paradigm_info": [{"tags": [pos], "inflection": [{"word_form": f} for f in forms]}]}]}}


ROWS = [
    _art(20, "den", "PRON", 1), _art(21, "den", "DET", 2), _art(22, "den", "DET", 3),
    _art(4, "dann", "ADV"), _art(2, "danne", "VERB", forms=["dann", "danna"]),
    _art(30, "fly", "NOUN", 1), _art(31, "fly", "NOUN", 2), _art(32, "fly", "VERB", 3,
                                                               forms=["flyr"]),
]
TRANSLATED = [20, 22, 2, 32]
SNIPPETS = {
    20: ("it · he", "en"), 21: ("brukt foran substantiv", "nb"), 22: ("the", "en"),
    4: ("kultivert, dannet", "nb"), 2: ("to form · to found", "en"),
    31: ("lite insekt", "nb"), 32: ("to fly · to rush", "en"),
}

HARNESS = r"""const fs = require('fs'), path = require('path');
const store = {};
globalThis.localStorage = { getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
const calls = [];
const STUB = { recordSearch: (f, t) => { calls.push([f, t]); return true; } };
globalThis.ordparPersonal = STUB;
const M = require(%(lookup)s), L = M.ordparLookup, S = M.ordparSearch;
L.setLoader(name => { const p = path.join(%(index)s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
function realPersonal() {
  globalThis.ordparPersonal = require(%(personal)s);
  return globalThis.ordparPersonal;
}
async function formArticle(q) {
  const res = await L.lookup(q);
  return res.forms[0].articles[0];
}
function out(v) { process.stdout.write(JSON.stringify(v)); }
"""


class Recording88b(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        heads, forms, words = B.build_tables(mirror, None, {})
        B.write_index(cls.tmp, heads, forms, words, TRANSLATED, {}, snippets=SNIPPETS)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def js(self, body):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        script = os.path.join(self.tmp, "run88b.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(HARNESS % {
                "lookup": json.dumps(os.path.join(SITE, "lookup.js")),
                "personal": json.dumps(os.path.join(SITE, "personal.js")),
                "index": json.dumps(os.path.join(self.tmp, "index")),
            })
            fh.write("(async () => { " + body + " })().catch(e => { console.error(e); process.exit(1); });\n")
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))

    # ------------------------------------------------------------ a search

    def test_a_search_counts_its_headword_hits_only(self):
        # *dann*: a headword (dann, untranslated) and an inflected form of *danne*
        got = self.js("await S.recordSearch('dann', await L.lookup('dann'), null, 5); out(calls);")
        self.assertEqual(got, [[{"q": "dann", "n": 1, "word": "dann", "hg": 0, "pos": "ADV",
                                 "translated": False, "text": ""}, 5]])

    def test_several_headword_hits(self):
        got = self.js("await S.recordSearch('den', await L.lookup('den'), null, 5); out(calls);")
        self.assertEqual(got, [[{"q": "den", "n": 3}, 5]])

    def test_one_translated_article_is_written_at_once_then_filled(self):
        # decisions 129: the first write comes before the promise is awaited (a page left at once
        # still has it), the text after, the same query and time
        got = self.js("""const p = S.recordSearch('danne', await L.lookup('danne'), null, 7);
const early = calls.map(c => c[0]);
await p; out([early, calls]);""")
        early, calls = got
        bare = {"q": "danne", "n": 1, "word": "danne", "hg": 0, "pos": "VERB",
                "translated": True, "text": ""}
        self.assertEqual(early, [bare])
        self.assertEqual(calls, [[bare, 7], [dict(bare, text="to form"), 7]])

    def test_one_translated_article_leaves_one_entry(self):
        got = self.js("""const P = realPersonal();
const p = S.recordSearch('danne', await L.lookup('danne'), null, 7);
const early = P.history().map(e => [e.q, e.text, e.t]);
await p; out([early, P.history().map(e => [e.q, e.text, e.t])]);""")
        self.assertEqual(got, [[["danne", "", 7]], [["danne", "to form", 7]]])

    def test_a_search_with_only_inflected_forms_records_nothing(self):
        got = self.js("""const res = await L.lookup('danna');
const p = S.recordSearch('danna', res, null);
out([res.count, res.heads.length, typeof p.then, await p, calls]);""")
        self.assertEqual(got[0], 1)               # it found something: danne, as an inflected form
        self.assertEqual(got[1], 0)
        self.assertEqual(got[2], "function")
        self.assertEqual(got[4], [])

    # ------------------------------------------------------------ an opened inflected form

    def test_opening_records_the_headword_as_its_own_search(self):
        got = self.js("""const a = await formArticle('danna');
await S.recordOpened(a); out([a.id, calls]);""")
        self.assertEqual(got[0], 2)
        first, last = got[1][0], got[1][-1]
        # the stand-in at once (no text yet), then the search's own entry, at the same time
        self.assertEqual(first[0], {"q": "danne", "n": 1, "word": "danne", "hg": 0, "pos": "VERB",
                                    "translated": True, "text": ""})
        self.assertEqual(last[0], {"q": "danne", "n": 1, "word": "danne", "hg": 0, "pos": "VERB",
                                   "translated": True, "text": "to form"})
        self.assertEqual(first[1], last[1])
        # three writes since decisions 129 (two before): the stand-in, `recordSearch`'s own
        # at-once write (the same, unfilled entry again — it no longer waits for the text), then
        # the text; all the same entry (the same query and time)
        self.assertEqual(len(got[1]), 3)
        self.assertEqual(got[1][1], first)

    def test_opening_records_what_a_search_for_the_headword_records(self):
        # fly III opened from *flyr*: a search for *fly* finds three articles
        got = self.js("""const a = await formArticle('flyr');
await S.recordOpened(a);
const opened = calls.slice(-1)[0][0];
calls.length = 0;
await S.recordSearch('fly', await L.lookup('fly'), null);
out([a.id, opened, calls[0][0]]);""")
        self.assertEqual(got[0], 32)
        self.assertEqual(got[1], {"q": "fly", "n": 3})
        self.assertEqual(got[1], got[2])

    def test_a_headword_the_index_does_not_find_keeps_its_article(self):
        got = self.js("""await S.recordOpened({id: 99, word: 'zzz', hg: 0, pos: 'NOUN', translated: false});
out(calls.map(c => c[0]));""")
        self.assertEqual(got[-1], {"q": "zzz", "n": 1, "word": "zzz", "hg": 0, "pos": "NOUN",
                                   "translated": False, "text": ""})

    def test_the_history_holds_one_entry_for_it(self):
        got = self.js("""const P = realPersonal();
P.recordSearch({q: 'danna', n: 1, word: 'danne', translated: true, text: 'to form'}, 1);
await S.recordOpened(await formArticle('danna'));
out(P.history().map(e => [e.q, e.n, e.text]));""")
        # the opened headword on top, one entry; the older entry (stored before) untouched
        self.assertEqual(got, [["danne", 1, "to form"], ["danna", 1, "to form"]])

    # ------------------------------------------------------------ the link

    def test_the_link_records_and_then_follows(self):
        got = self.js("""globalThis.location = { href: '/bm-en/#q=danna' };
const handlers = {};
const link = { href: '/bm-en/2/', addEventListener: (k, fn) => { handlers[k] = fn; } };
S.recordOnOpen(link, await formArticle('danna'));
const ev = (o) => Object.assign({ button: 0, prevented: false, defaultPrevented: false,
  preventDefault() { this.prevented = true; } }, o);
const plain = ev({});
handlers.click(plain);
const before = location.href;
await new Promise(r => setTimeout(r, 50));
const after = location.href;
const n1 = calls.length;
location.href = 'here';
const ctrl = ev({ ctrlKey: true });
handlers.click(ctrl);
await new Promise(r => setTimeout(r, 50));
const n2 = calls.length;
handlers.auxclick(ev({ button: 1 }));
await new Promise(r => setTimeout(r, 50));
out([plain.prevented, before, after, n1, ctrl.prevented, location.href, n2, calls.length,
     Object.keys(handlers).sort()]);""")
        prevented, before, after, n1, ctrl_prevented, href, n2, n3, keys = got
        self.assertTrue(prevented)
        self.assertEqual(before, "/bm-en/#q=danna")       # held until the entry is written
        self.assertEqual(after, "/bm-en/2/")
        # three writes per opening since decisions 129 (two before; see
        # test_opening_records_the_headword_as_its_own_search)
        self.assertEqual(n1, 3)
        self.assertFalse(ctrl_prevented)                  # a new tab: the browser opens it
        self.assertEqual(href, "here")
        self.assertEqual(n2, 6)
        self.assertEqual(n3, 9)                           # a middle click records too
        self.assertEqual(keys, ["auxclick", "click"])

    # ------------------------------------------------------------ the wiring

    def test_wiring(self):
        js = _read(SITE, "lookup.js")
        body = js[js.index("  function articleList("):js.index("  function lemmaOf(")]
        self.assertIn("recordOnOpen(li.firstChild, a);", body)
        rec = js[js.index("  function recordSearch("):js.index("  function recordOpened(")]
        self.assertIn("res.heads.forEach(function (grp) {", rec)
        self.assertNotIn("res.forms", rec)
        self.assertIn("if (record) { recordSearch(g.query, res, shown); }", js)
        # a list row opened (a headword hit) still records nothing
        rows = js[js.index("  function listRows("):js.index("  function dropRule(")]
        self.assertNotIn("record", rows.replace("records nothing", ""))


if __name__ == "__main__":
    unittest.main()
