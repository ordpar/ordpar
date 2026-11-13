# -*- coding: utf-8 -*-
"""Pins history and favourites, kept on the device (site decisions 60, Robin 2026-10-19; briefs
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-history-60-2026-10-19.md` and, for
the history as a list of searches, `brief-history-60b-2026-10-19.md`). What can be pinned
outside a browser:

* **The storage format** (`ordpar/site/personal.js`): two localStorage keys. `favourites`, a
  JSON array of articles `{id, word, hg, pos, translated, snip, drop?, t}`: a missing or corrupt
  value reads as empty, a malformed entry is dropped, a repeated id keeps its first place.
  `history`, a JSON array of searches `{q, n, t}` plus, for one article found, `{word, hg, pos,
  translated, text}`: the query stored trimmed, the same checks, a repeated query keeps its first
  place.
* **The history's rules** (60b items 1, 2): newest first, a repeat — the same query trimmed and
  lower-cased — moved to the top with the spelling typed last, capped at 100 (the oldest
  dropped); an entry written late takes its place by time; no query or no article, no entry.
* **The old entries** (60b item 4): the build before 60b's per-article entries read as searches
  for their word, merged per word at the newest time, counting the distinct ids; converted at
  read time, the new shape written at the next write.
* **Export and import**: the file's format name and version (2); import reads version 1 too, its
  history converted; it refuses a file that does not parse, has another format, a newer version
  (3) or one malformed entry — and then writes nothing; the merge adds new favourites without
  duplicates, combines the history by query and time under the cap and takes the settings from
  the file; a storage failure mid-write puts everything back.
* **The page's fields** (`sitegen/page.py` `personal_attrs`, `build_site.personal_fields`): the
  `<html>` attributes a favourites row is drawn from, the article page loading `personal.js`
  before its script, and the script drawing the heart with the strings' words — one name,
  "Favourite", in both states (60b item 6).
* **The dropdown's set-phrase text** (brief item 7(b) as amended, Robin 2026-10-19):
  `article.dropdown_text` — a translated set phrase with no summary gloss shows its first
  set-phrase box (`idiom`), else `""`; `build_index.snippet_files` files it under `"_d"`,
  which only the dropdown and the history and favourites rows read; the list view's snippet is
  unchanged. Every reader (`shell.js` `glossText`, `lookup.js` `dropRule`, `personal.js`
  `dropText`) takes a `""` as no box and shows the snippet's first unit — its English line
  (site decisions 82, A13 point 3, Robin 2026-10-21; until then `""` meant nothing).
* **The table fit** (brief item 7(a) as ruled): `inflection.js` exports `fit`, the search view
  calls it; since decisions 102 (2026-10-23) `mountAll` fits every mount itself, the article
  page's included, and the mount is capped at the card everywhere (`article.css`), so
  `shell.css`'s results-only cap is gone (the pin moved, not dropped).
* **The pages**: `/favourites/` and `/history/` are written by `build_index.copy_shell` from
  `site/favourites.html` and `site/history.html`; the header links the favourites page.

The JavaScript tests run under `bun` (or `node`) and are skipped when neither is on PATH.
Synthetic data only: no mirror, library or built site is read."""

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
sys.path.insert(0, ROOT)

import build_index as B  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _runner():
    return shutil.which("bun") or shutil.which("node")


#: A localStorage stand-in for bun/node; `failAfter` makes setItem throw after N writes.
FAKE_STORAGE = r"""
const store = {}; let writes = 0; globalThis.failAfter = Infinity;
globalThis.localStorage = {
  getItem: k => Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null,
  setItem: (k, v) => { if (++writes > globalThis.failAfter) { throw new Error('QuotaExceededError'); } store[k] = String(v); },
  removeItem: k => { delete store[k]; },
  clear: () => { for (const k in store) delete store[k]; }
};
globalThis.STORE = store;
"""


def _run_js(body):
    """Run `body` with `P` (ordparPersonal) loaded over a fake localStorage; it must print
    JSON. Skips the test when no runner is on PATH."""
    runner = _runner()
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(FAKE_STORAGE + "const P = require(%s);\n%s\n"
                     % (json.dumps(os.path.join(SITE, "personal.js")), body))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def E(i, t, **kw):
    e = {"id": i, "word": "w%d" % i, "hg": 0, "pos": "NOUN", "translated": True,
         "snip": "a · b", "t": t}
    e.update(kw)
    return e


class StorageFormat(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _run_js(r"""
const out = {};
out.keys = [P.HISTORY_KEY, P.FAV_KEY, P.CAP, P.RECENT, P.VERSION];
out.missing = P.parseList(null);
out.empty = P.parseList('');
out.corrupt = P.parseList('{not json');
out.object = P.parseList('{"id": 1}');
out.mixed = P.parseList(JSON.stringify([%s, {"id": "x"}, null, %s, %s]));
out.hMissing = P.parseHistory(null);
out.hCorrupt = P.parseHistory('{not json');
out.hObject = P.parseHistory('{"q": "hus"}');
out.hMixed = P.parseHistory(JSON.stringify([
  {q: ' fly ', n: 5, t: 9}, {q: 'x', n: 0, t: 1}, {q: '', n: 1, t: 1}, {q: 'hus', n: 1, t: 8},
  {q: 'Fly', n: 2, t: 7}, null, {q: 'bok', n: 1, t: 6, word: 'bok', translated: true, text: 'book'}]));
localStorage.setItem('history', '][');
out.storedCorrupt = P.history();
out.record = P.recordSearch({q: '  husene ', n: 1, word: 'hus', hg: 0, pos: 'NOUN', translated: true, text: 'house'});
out.afterRecord = JSON.parse(STORE.history);
process.stdout.write(JSON.stringify(out));
""" % (json.dumps(E(1, 3)), json.dumps(E(2, 2, drop="")), json.dumps(E(1, 1))))

    def test_the_two_keys_the_caps_and_the_version(self):
        self.assertEqual(self.out["keys"], ["history", "favourites", 100, 8, 2])

    def test_missing_or_corrupt_reads_as_empty(self):
        for k in ("missing", "empty", "corrupt", "object", "storedCorrupt",
                  "hMissing", "hCorrupt", "hObject"):
            self.assertEqual(self.out[k], [], k)

    def test_favourites_malformed_entries_dropped_and_ids_unique(self):
        self.assertEqual([e["id"] for e in self.out["mixed"]], [1, 2])
        self.assertEqual(self.out["mixed"][1]["drop"], "")      # '' is kept: "show nothing"
        self.assertNotIn("drop", self.out["mixed"][0])

    def test_history_entries_checked_and_queries_unique(self):
        # n 0, an empty query, a one-article entry without its word: dropped; "Fly" repeats
        # " fly " (trimmed, lower-cased) and keeps the first place; queries stored trimmed
        self.assertEqual(self.out["hMixed"], [
            {"q": "fly", "n": 5, "t": 9},
            {"q": "bok", "n": 1, "t": 6, "word": "bok", "hg": 0, "pos": "", "translated": True,
             "text": "book"}])

    def test_a_search_is_stored_as_typed_trimmed(self):
        self.assertTrue(self.out["record"])
        [e] = self.out["afterRecord"]
        self.assertEqual({k: v for k, v in e.items() if k != "t"},
                         {"q": "husene", "n": 1, "word": "hus", "hg": 0, "pos": "NOUN",
                          "translated": True, "text": "house"})
        self.assertIsInstance(e["t"], (int, float))


class HistoryRules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _run_js(r"""
const out = {};
let h = [];
for (let i = 1; i <= 105; i++) h = P.addSearch(h, {q: 'w' + i, n: 2, t: i}, 100);
out.len = h.length; out.top = h[0].q; out.bottom = h[h.length - 1].q;
h = P.addSearch(h, {q: 'W50', n: 3, t: 999}, 100);
out.moved = [h[0].q, h[0].n, h.filter(e => P.searchKey(e.q) === 'w50').length, h.length];
// an entry written late (its display fields arrived after a later search) keeps its time's place
h = P.addSearch(h, {q: 'late', n: 2, t: 990}, 100);
out.late = h.slice(0, 2).map(e => e.q);
P.recordSearch({q: 'fly', n: 5}, 100);
P.recordSearch({q: 'husene', n: 1, word: 'hus', pos: 'NOUN', translated: true, text: 'house'}, 200);
P.recordSearch({q: 'Fly', n: 5}, 300);
out.repeat = P.history().map(e => [e.q, e.n]);
out.refused = [P.recordSearch({q: '  ', n: 1}), P.recordSearch({q: 'x', n: 0}),
               P.recordSearch({q: 'x', n: 1})];        // one article but no word
out.after = P.history().length;
out.fav = [P.isFavourite(3), P.toggleFavourite({id: 3, word: 'c', translated: true}), P.isFavourite(3)];
P.setFavourite({id: 4, word: 'd', translated: true}, true);
P.setFavourite({id: 3, word: 'c', translated: true}, true);    // already saved: no duplicate
out.favs = P.favourites().map(e => e.id);
out.off = P.toggleFavourite({id: 3}); out.favsAfter = P.favourites().map(e => e.id);
P.clearHistory(); out.cleared = [P.history(), localStorage.getItem('history')];
process.stdout.write(JSON.stringify(out));
""")

    def test_capped_at_100_oldest_dropped(self):
        self.assertEqual((self.out["len"], self.out["top"], self.out["bottom"]), (100, "w105", "w6"))

    def test_a_repeat_moves_to_the_top_with_the_spelling_typed_last(self):
        self.assertEqual(self.out["moved"], ["W50", 3, 1, 100])
        self.assertEqual(self.out["repeat"], [["Fly", 5], ["husene", 1]])

    def test_an_entry_takes_its_place_by_time(self):
        self.assertEqual(self.out["late"], ["W50", "late"])

    def test_no_query_or_no_article_is_not_recorded(self):
        self.assertEqual(self.out["refused"], [False, False, False])
        self.assertEqual(self.out["after"], 2)

    def test_favourites_toggle_without_duplicates(self):
        self.assertEqual(self.out["fav"], [False, True, True])
        self.assertEqual(self.out["favs"], [4, 3])
        self.assertEqual((self.out["off"], self.out["favsAfter"]), (False, [4]))

    def test_clear_history(self):
        self.assertEqual(self.out["cleared"], [[], None])


class OldEntries(unittest.TestCase):
    """60b item 4: history entries stored by the build before 60b (one per article) are read as
    searches for their headword."""

    @classmethod
    def setUpClass(cls):
        old = [E(101, 1000, word="fly", hg=5, pos="VERB"),
               E(102, 999, word="fly", hg=3), E(103, 998, word="fly", hg=1, translated=False),
               E(104, 997, word="Fly", hg=2), E(105, 996, word="fly", hg=4),
               E(7, 500, word="hus", snip="house · home"),
               E(8, 400, word="fy faen", pos="EXPR", snip="used to express", drop="bloody hell"),
               E(9, 300, word="fôr / for …", pos="EXPR", translated=False, snip="x")]
        cls.out = _run_js(r"""
const out = {};
localStorage.setItem('history', JSON.stringify(%s));
out.read = P.history();
out.stored = localStorage.getItem('history') === JSON.stringify(%s);   // read time only
P.recordSearch({q: 'bok', n: 2}, 2000);
out.written = JSON.parse(STORE.history).map(e => Object.keys(e).sort().join(','));
// old and new entries in one stored list: one per query, the later kept
localStorage.setItem('history', JSON.stringify([{q: 'HUS', n: 1, t: 50, word: 'hus', translated: false}].concat(%s)));
out.mixed = P.history().map(e => [e.q, e.t]).slice(0, 3);
process.stdout.write(JSON.stringify(out));
""" % (json.dumps(old), json.dumps(old), json.dumps(old)))

    def test_the_five_fly_articles_and_hus_read_as_words(self):
        r = self.out["read"]
        self.assertEqual([(e["q"], e["n"], e["t"]) for e in r],
                         [("fly", 5, 1000), ("hus", 1, 500), ("fy faen", 1, 400), ("fôr", 1, 300)])
        self.assertNotIn("word", r[0])                         # several articles: no display fields

    def test_one_id_keeps_its_display_fields_and_the_dropdown_rule(self):
        hus, fy, fo = self.out["read"][1:]
        self.assertEqual((hus["word"], hus["pos"], hus["translated"], hus["text"]),
                         ("hus", "NOUN", True, "house"))
        self.assertEqual(fy["text"], "bloody hell")            # the set-phrase text
        self.assertEqual((fo["word"], fo["translated"], fo["text"]), ("fôr / for …", False, ""))

    def test_converted_at_read_time_written_at_the_next_write(self):
        self.assertTrue(self.out["stored"])
        self.assertEqual(set(self.out["written"]), {"n,q,t", "hg,n,pos,q,t,text,translated,word"})

    def test_old_and_new_together(self):
        self.assertEqual(self.out["mixed"], [["fly", 1000], ["hus", 500], ["fy faen", 400]])


def S(q, t, n=2, **kw):
    e = {"q": q, "n": n, "t": t}
    e.update(kw)
    return e


class ExportImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        dev_h = [S("hus", 5000, 1, word="hus", hg=0, pos="NOUN", translated=True, text="house"),
                 S("fly", 100)]
        dev_f = [E(11, 100)]
        file_h = [S("Fly", 3000), S("bok", 2000)] + [S("w%d" % i, 1000 - i) for i in range(120)]
        file_f = [E(11, 100), E(12, 400)]
        v1_h = [E(201, 900, word="fly"), E(202, 800, word="fly"), E(7, 700, word="hus", snip="house")]
        cls.out = _run_js(r"""
const out = {};
const devH = %s, devF = %s, fileH = %s, fileF = %s, v1H = %s;
const file = P.makeExport({theme: 'dark', listview: 'multi', bogus: 'x', defs: 7}, fileH, fileF, Date.UTC(2026, 9, 19));
out.head = [file.format, file.version, file.exported, Object.keys(file)];
out.settings = file.settings;
out.name = P.exportName(new Date(2026, 9, 9));
const text = JSON.stringify(file);
out.read = P.readImport(text).ok;
const v1 = JSON.stringify({format: 'ordpar-personal', version: 1, exported: 'x', settings: {theme: 'light'},
                           history: v1H, favourites: fileF});
const r1 = P.readImport(v1);
out.v1 = [r1.ok, r1.ok && r1.data.history.map(e => [e.q, e.n, e.t]), r1.ok && r1.data.favourites.length];
out.refuse = {
  parse: P.readImport('not json').error,
  format: P.readImport(JSON.stringify({format: 'other', version: 1})).error,
  array: P.readImport('[]').error,
  noVersion: P.readImport(JSON.stringify({format: 'ordpar-personal'})).error,
  newer: P.readImport(JSON.stringify(Object.assign({}, file, {version: 3}))).error,
  entry: P.readImport(JSON.stringify(Object.assign({}, file, {favourites: fileF.concat([{id: 'x'}])}))).error,
  search: P.readImport(JSON.stringify(Object.assign({}, file, {history: fileH.concat([{q: 'x', n: 0, t: 1}])}))).error,
  oldShapeInV2: P.readImport(JSON.stringify(Object.assign({}, file, {history: v1H}))).error,
  newShapeInV1: P.readImport(JSON.stringify(Object.assign({}, file, {version: 1}))).error,
  setting: P.readImport(JSON.stringify(Object.assign({}, file, {settings: {theme: 3}}))).error,
  list: P.readImport(JSON.stringify(Object.assign({}, file, {history: {}}))).error,
};
const m = P.mergeImport({history: devH, favourites: devF}, P.readImport(text).data);
out.merge = {fav: m.favourites.map(e => e.id), hist: m.history.slice(0, 4).map(e => [e.q, e.t]),
             histLen: m.history.length, added: m.added, settings: m.settings};
// importText: a refusal writes nothing; a good file writes all three
localStorage.setItem('history', JSON.stringify(devH)); localStorage.setItem('favourites', JSON.stringify(devF));
localStorage.setItem('theme', 'light');
const before = JSON.stringify(STORE);
out.bad = [P.importText('{"format":"ordpar-personal","version":2,"history":[{"q":1}]}').error, JSON.stringify(STORE) === before];
out.v3 = [P.importText(JSON.stringify(Object.assign({}, file, {version: 3}))).error, JSON.stringify(STORE) === before];
// storage fails on the third write: everything is put back
globalThis.failAfter = 2;
out.full = [P.importText(text).error];
globalThis.failAfter = Infinity;
out.full.push(JSON.stringify(STORE) === before);
const ok = P.importText(text);
out.good = [ok.ok, ok.added, localStorage.getItem('theme'), localStorage.getItem('listview'),
            P.favourites().map(e => e.id), P.history().length];
// a version-1 file imported: its history arrives as searches
localStorage.setItem('history', JSON.stringify(devH));
const ok1 = P.importText(v1);
out.good1 = [ok1.ok, ok1.added, P.history().map(e => [e.q, e.n])];
out.exportData = [Object.keys(P.exportData(k => ({theme: 'dark'})[k] || null).settings),
                  P.exportData(null).version, P.exportData(null).history[0]];
process.stdout.write(JSON.stringify(out));
""" % tuple(json.dumps(x) for x in (dev_h, dev_f, file_h, file_f, v1_h)))

    def test_the_file_names_its_format_and_version(self):
        fmt, ver, when, keys = self.out["head"]
        self.assertEqual((fmt, ver, when), ("ordpar-personal", 2, "2026-10-19T00:00:00.000Z"))
        self.assertEqual(keys, ["format", "version", "exported", "settings", "history", "favourites"])
        self.assertEqual(self.out["name"], "ordpar-2026-10-09.txt")      # a .txt since 2026-10-20

    def test_only_known_string_settings_are_exported(self):
        self.assertEqual(self.out["settings"], {"theme": "dark", "listview": "multi"})
        self.assertEqual(self.out["exportData"][0], ["theme"])

    def test_the_export_carries_searches(self):
        _keys, ver, first = self.out["exportData"]
        self.assertEqual(ver, 2)
        self.assertEqual((first["q"], first["n"]), ("hus", 1))

    def test_refusals(self):
        self.assertTrue(self.out["read"])
        self.assertEqual(self.out["refuse"], {
            "parse": "parse", "format": "format", "array": "format", "noVersion": "format",
            "newer": "version", "entry": "content", "search": "content",
            "oldShapeInV2": "content", "newShapeInV1": "content", "setting": "content",
            "list": "content"})

    def test_a_version_1_file_is_read_its_history_converted(self):
        ok, hist, nfav = self.out["v1"]
        self.assertTrue(ok)
        self.assertEqual(hist, [["fly", 2, 900], ["hus", 1, 700]])
        self.assertEqual(nfav, 2)

    def test_the_merge(self):
        m = self.out["merge"]
        # favourites: 11 kept once, 12 added; newest first
        self.assertEqual(m["fav"], [12, 11])
        # history: one entry per query (fly / Fly one), the later search's, by time, under the cap
        self.assertEqual(m["hist"], [["hus", 5000], ["Fly", 3000], ["bok", 2000], ["w0", 1000]])
        self.assertEqual(m["histLen"], 100)
        self.assertEqual(m["added"], {"favourites": 1, "history": 98})
        self.assertEqual(m["settings"], {"theme": "dark", "listview": "multi"})

    def test_a_refused_file_or_a_failed_write_changes_nothing(self):
        self.assertEqual(self.out["bad"], ["content", True])
        self.assertEqual(self.out["v3"], ["version", True])
        self.assertEqual(self.out["full"], ["storage", True])

    def test_a_good_file_writes_all_three(self):
        self.assertEqual(self.out["good"], [True, {"favourites": 1, "history": 98}, "dark",
                                            "multi", [12, 11], 100])

    def test_importing_a_version_1_file(self):
        ok, added, hist = self.out["good1"]
        self.assertTrue(ok)
        self.assertEqual(added["history"], 0)          # fly and hus are already searches here
        self.assertEqual(hist[:2], [["hus", 1], ["fly", 2]])


class Display(unittest.TestCase):

    def test_units_and_the_dropdown_text(self):
        out = _run_js(r"""
process.stdout.write(JSON.stringify([
  P.unit({snip: 'to catch · to capture'}), P.unit({snip: ''}),
  P.dropText({snip: 'used to express', drop: 'bloody hell'}), P.dropText({snip: 'x', drop: ''}),
  P.dropText({snip: 'a · b'})]));
""")
        # an override of '' is a set phrase with no box: its English line (decisions 82, A13 point 3)
        self.assertEqual(out, ["to catch", "", "bloody hell", "x", "a"])


class DropdownText(unittest.TestCase):
    """`article.dropdown_text` and its path through the index (item 7(b) as amended)."""

    @classmethod
    def setUpClass(cls):
        try:
            from ordpar.sitegen import article
        except Exception as e:                      # the deck's renderer not importable
            raise unittest.SkipTest("sitegen.article not importable: %s" % e)
        cls.article = article

    def row(self, pos="fixed expression", gloss=None, idioms=((None, ()),)):
        senses = [{"defn": 1, "ordinal": 1, "no": ["n"], "en": ["first sense"], "idiom": i,
                   "subs": [{"defn": 2, "no": ["s"], "en": ["s"], "idiom": s} for s in subs],
                   "ex": [], "comp": []} for i, subs in idioms]
        r = {"id": 1, "pos_en": pos, "senses": senses}
        if gloss:
            r["summary"] = {"gloss": gloss}
        return r

    def test_set_phrase_without_gloss_takes_its_idiom(self):
        r = self.row(idioms=((None, ()), ("to be on one's guard", ())))
        self.assertEqual(self.article.dropdown_text(r, r), "to be on one's guard")

    def test_sense_before_its_subs_in_sense_order(self):
        r = self.row(idioms=((None, (None, "from a sub")), ("from sense 2", ())))
        self.assertEqual(self.article.dropdown_text(r, r), "from a sub")
        r = self.row(idioms=(("sense 1", ("sub",)),))
        self.assertEqual(self.article.dropdown_text(r, r), "sense 1")

    def test_set_phrase_without_gloss_or_idiom_gives_an_empty_override(self):
        # '' is filed as such; the readers show the English line for it (test below)
        r = self.row()
        self.assertEqual(self.article.dropdown_text(r, r), "")

    def test_everything_else_takes_the_snippet(self):
        r = self.row(gloss=["all in all"], idioms=(("all in all", ()),))
        self.assertIsNone(self.article.dropdown_text(r, r))
        r = self.row(pos="noun")
        self.assertIsNone(self.article.dropdown_text(r, r))
        r = self.row()
        self.assertIsNone(self.article.dropdown_text(r, None))          # untranslated
        # the list view's snippet is not touched
        self.assertEqual(self.article.snippet(r, r), ("first sense", "en"))

    def test_the_index_files_it_under_d_for_the_dropdown_only(self):
        heads = {"f": {"fy faen": [1], "fy flate": [2], "fy søren": [3]}}
        snippets = {1: ("used to express admiration", "en", "bloody hell"),
                    2: ("used to express", "en", ""),
                    3: ("brukt som mild ed", "nb", "never shown")}
        out, missing, _mm = B.snippet_files(heads, snippets, [1, 2])
        f = out[B.snippet_key("fy faen")]
        self.assertEqual(f["1"], "used to express admiration")      # the list view's line
        self.assertEqual(f["_d"], {"1": "bloody hell", "2": ""})     # 3 is untranslated
        self.assertEqual(missing, 0)

    def test_read_snippets_takes_two_or_three(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "s.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"1": ["a", "en"], "2": ["b", "en", "c"]}, fh)
            self.assertEqual(B.read_snippets(p), {1: ("a", "en"), 2: ("b", "en", "c")})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_shell_reads_d_before_the_first_unit(self):
        js = _read(SITE, "shell.js")
        self.assertIn("snips._d[id]", js)       # `glossText` since decisions 82
        self.assertLess(js.index("snips._d[id]"), js.index("snips[id].split("))

    def test_readers_take_an_empty_override_as_no_box(self):
        # site decisions 82, A13 point 3 (Robin 2026-10-21): the dropdown (`glossText`) and the
        # history rows' stored text (`dropRule`) agree with `personal.js` `dropText` (Display)
        runner = _runner()
        if not runner:
            self.skipTest("no bun/node on PATH")
        def fn(src, name):            # the function's text: one return, then its closing brace
            i = src.index("function %s(" % name)
            return src[i:src.index("}", src.index("return ", i)) + 1]
        body = fn(_read(SITE, "shell.js"), "glossText") + ";" + fn(_read(SITE, "lookup.js"), "dropRule")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "readers.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(body + r"""
const snips = {'1': 'used to express admiration \u00b7 or disgust', '2': 'to stand up \u00b7 to rise',
  '3': 'to be still', _d: {'1': 'bloody hell', '2': ''}};
process.stdout.write(JSON.stringify([glossText(snips, '1'), glossText(snips, '2'),
  glossText(snips, '3'), glossText(snips, '4'),
  dropRule('bloody hell', 'x'), dropRule('', 'to stand up \u00b7 to rise'), dropRule(null, 'a'),
  dropRule('', '')]));
""")
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode != 0:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            out = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(out, ["bloody hell", "to stand up", "to be still", "",
                               "bloody hell", "to stand up", "a", ""])


class PageFields(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from ordpar.sitegen import page
            from ordpar.sitegen.strings import EN
            import build_site
        except Exception as e:
            raise unittest.SkipTest("sitegen not importable: %s" % e)
        cls.page, cls.EN, cls.build_site = page, EN, build_site

    def test_attributes(self):
        a = self.page.personal_attrs({"hg": 3, "pos": "VERB", "word": "fange", "snip": 'to "catch"',
                                      "drop": None}, "fange")
        self.assertEqual(a, ' data-hg="3" data-pos="VERB" data-snip="to &quot;catch&quot;"')
        a = self.page.personal_attrs({"hg": 0, "pos": "EXPR", "word": "fôr / for", "snip": "x",
                                      "drop": ""}, "fôr")
        self.assertEqual(a, ' data-pos="EXPR" data-word="fôr / for" data-snip="x" data-drop=""')

    def test_fields_as_the_index_computes_them(self):
        data = {"lemmas": [{"lemma": "fange", "hgno": 3, "paradigm_info": [{"tags": ["VERB"]}]}]}
        f = self.build_site.personal_fields(13791, data, {"lemmas": [{"form": "fange"}]},
                                            "to catch · to capture " * 10, None)
        self.assertEqual((f["hg"], f["pos"], f["word"], f["drop"]), (3, "VERB", "fange", None))
        self.assertLessEqual(len(f["snip"]), B.SNIPPET_MAX)
        f = self.build_site.personal_fields(5, None, {"pos_en": "fixed expression",
                                                      "lemmas": [{"form": "fy faen"}]}, "x", "y")
        self.assertEqual((f["pos"], f["word"], f["drop"]), ("EXPR", "fy faen", "y"))

    def test_the_page_loads_personal_js_before_its_script(self):
        html = self.page.render(aid=1, lemmas=[{"form": "hus"}], article="<div class=\"ordbok\"></div>",
                                translated=True, other_entries=0, strings=self.EN, stamp="s",
                                description="d", mk=None,
                                personal={"hg": 0, "pos": "NOUN", "word": "hus", "snip": "a house"})
        self.assertIn('data-pos="NOUN" data-snip="a house">', html)
        # one script since 2026-10-20 (`/site/ordpar.js`): personal.js still before article.js
        parts = self.page.ARTICLE_JS_PARTS
        self.assertLess(parts.index("/site/personal.js"), parts.index("/site/article.js"))
        self.assertIn('<script src="/site/ordpar.js?v=', html)

    def test_the_script_draws_the_heart_with_the_strings(self):
        js = self.page.PAGE_JS
        self.assertIn("P.mountPage(", js)
        # decisions 63: the header's "Favourites" link is the shared header's (chrome.py), so the
        # page script carries only the heart's two words
        for k in ("fav_label", "fav_saved"):
            self.assertIn(json.dumps(self.EN[k]), js)
        self.assertNotIn("fit(", js)            # the fit is inflection.js `mountAll`'s own (102)

    def test_the_heart_has_one_name(self):
        # 60b item 6: "Favourite" in both states, `aria-pressed` alone carries the state
        self.assertEqual(self.EN["fav_label"], "Favourite")
        for k in ("fav_save", "fav_remove"):
            self.assertNotIn(k, self.EN)
        js = _read(SITE, "personal.js")
        self.assertIn("btn.setAttribute('aria-label', labels.label);", js)
        self.assertIn("btn.title = labels.label;", js)
        self.assertIn("btn.setAttribute('aria-pressed', on ? 'true' : 'false');", js)

    def test_the_article_page_records_nothing(self):
        js = _read(SITE, "personal.js")
        body = js[js.index("function mountPage("):js.index("global.addEventListener('storage'")]
        self.assertNotIn("record", body.replace("not recorded", ""))

    def test_the_shell_strings_agree(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["fav.label"], self.EN["fav_label"])
        self.assertNotIn("fav.save", s)
        self.assertNotIn("fav.remove", s)
        self.assertEqual(s["fav.saved"], self.EN["fav_saved"])
        self.assertEqual(s["nav.favourites"], self.EN["fav_link"])
        for k in ("recent.title", "recent.all", "recent.label", "personal.device",
                  "favourites.empty", "history.empty", "history.clear", "history.confirm",
                  "transfer.export", "transfer.import", "transfer.parse", "transfer.format",
                  "transfer.version", "transfer.content", "transfer.storage", "transfer.done"):
            self.assertIn(k, s)


class Wiring(unittest.TestCase):

    def test_the_results_fit_their_tables(self):
        self.assertIn("fit: fit,", _read(SITE, "inflection.js"))
        self.assertIn("global.ordparInflection.fit(host)", _read(SITE, "lookup.js"))
        # decisions 102: every mount fitted by `mountAll`, and capped at its card in article.css
        self.assertIn("fitHost(host);", _read(SITE, "inflection.js"))
        self.assertNotIn(".ordpar-row-panel .ordpar-inflection { max-width: 100%; }", _read(SITE, "shell.css"))

    def test_the_results_record_the_search_and_draw_hearts(self):
        js = _read(SITE, "lookup.js")
        self.assertIn("function render(root, query, opts)", js)
        self.assertIn("if (record) { recordSearch(g.query, res, shown); }", js)
        self.assertNotIn("recordAll", js)                         # no article is recorded
        self.assertNotIn("remember(", js)                         # nor a list row opened
        self.assertIn("global.ordparPersonal.heartButton(personalFields(a), 'ordpar-result-heart')", js)
        self.assertIn("global.ordparPersonal.favMark(a.id)", js)
        search = _read(SITE, "search.html")
        # back / forward: not recorded (since site decisions 148 in the entry's direction)
        self.assertIn("run(q, false, false, false, ordparSearch.addressEnglish());", search)
        # a Random word draw (and a reload of one) is not recorded either (decisions 115)
        # site decisions 117: the first load's search, recorded unless drawn or reached by Back /
        # Forward — on this page, or on the word's own page it is sent to (`ordparSearch.wordPage`)
        self.assertIn("if (!q || back) { run(q, false, !drawn && !back); return; }", search)
        self.assertIn("run(q, false, !drawn);", search)
        self.assertIn("ordparSearch.render(main, q, { record: !!record, en: en });", search)
        notfound = _read(SITE, "404.html")
        # a mistyped address (/bm-en/<word>): its page, or its search, not recorded (lookup.js
        # `wordPage`: recorded only with a search's mark after `#`)
        self.assertIn("if (rest.length === 1) { word(rest[0]); return; }", notfound)
        self.assertIn("ordparSearch.wordPage(main, w);", notfound)
        self.assertIn("ordparSearch.render(main, q, { record: !drawn });", notfound)   # 115: a draw is not

    def test_recent_and_history_rows_run_the_search(self):
        shell_js = _read(SITE, "shell.js")
        # since site decisions 148 each in its own direction: a Norwegian entry's search
        # Norwegian, an English entry's English (its link `#en=`)
        self.assertIn("submit(e.q, false);", shell_js)
        self.assertIn("submit(e.q, true);", shell_js)
        self.assertNotIn("openEntry", shell_js)
        page = _read(SITE, "personal-page.js")
        self.assertIn("a.href = base() + 'bm-en/#q=' + encodeURIComponent(e.q);", page)
        self.assertIn("en.href = base() + 'bm-en/#en=' + encodeURIComponent(e.q);", page)
        self.assertNotIn("kind === 'history') { line.appendChild(P.favMark", page)

    def test_pages_load_personal_js(self):
        # since 2026-10-20 inside the shell pages' one blocking script, still before shell.js
        from ordpar.sitegen import page
        parts = page.SHELL_JS_PARTS
        self.assertLess(parts.index("/site/personal.js"), parts.index("/site/shell.js"))
        for name in ("search.html", "404.html", "favourites.html", "history.html"):
            html = _read(SITE, name)
            self.assertIn('<script src="/site/shell-pages.js"></script>', html, name)
        self.assertIn('data-ordpar-personal="favourites"', _read(SITE, "favourites.html"))
        self.assertIn('data-ordpar-personal="history"', _read(SITE, "history.html"))

    def test_the_header_links_the_favourites_page(self):
        # decisions 63: the header is chrome.py's static markup on every page; shell.js draws the
        # dropdown's "History" link — and since 2026-10-20 the header's Favourites link too
        # (`addChrome`), which needs script as it always did
        js = _read(SITE, "shell.js")
        self.assertIn("fav.setAttribute('href', base() + 'favourites/');", js)
        self.assertIn("historyLink.href = base() + 'history/';", js)

    def test_copy_shell_writes_the_two_pages(self):
        tmp = tempfile.mkdtemp()
        try:
            written = B.copy_shell(tmp)
            for dest in (os.path.join("favourites", "index.html"), os.path.join("history", "index.html")):
                self.assertIn(dest, written)
                html = _read(tmp, dest)
                self.assertIn("window.ORDPAR_STRINGS=", html)
                # decisions 92 (D): inside the shell pages' one script, no tag of its own
                self.assertIn("/site/shell-pages.js?v=", html)
                self.assertNotIn("/site/personal-page.js", html)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_nothing_is_sent(self):
        for name in ("personal.js", "personal-page.js"):
            js = _read(SITE, name)
            for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "document.cookie"):
                self.assertNotIn(word, js, (name, word))


if __name__ == "__main__":
    unittest.main()
