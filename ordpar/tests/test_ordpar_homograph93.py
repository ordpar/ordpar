# -*- coding: utf-8 -*-
"""Pins site decisions 93 (Robin, 2026-10-22; brief
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-homograph-93-2026-10-22.md`): a
homograph numeral per SPELLING, as ordbokene prints it, and the spellings separated by ", "
wherever the site shows them.

ordbokene's rule, read off its rendered pages on 2026-10-22
(`…/evidence/homograph-93-2026-10-22/`): every spelling carries its own lemma's number after it,
a spelling numbered 0 none — *lysing* I, *lysning* II; *avrustning*, *avrusting* II;
*akterskott* I, *akterskut*; *av* I, *AV* — and where the numbers match, the numeral on each —
*tore* II, *tørre* II; *antakelig* I, *antagelig* I. Spellings in different paradigm groups
keep their own (*brems* II over *bremse* I; *bod* over *bu* II). Its results list each article
with that whole line, ordered by the number of the spelling the search matched (*lysning* I
before *lysing* I, *lysning* II).

* **The article's headword line** (`article.lemma_groups`, `head_html`), each numeral hidden
  from screen readers with its own "homograph N" (decisions 33).
* **The index** (`build_index.entry`, `hg_field`, `form_hg`): `words[id][1]` one number every
  shown spelling carries, or a list of one per spelling where they differ; a search numbers and
  orders an article by the spelling it matched — in the Python twin and in `lookup.js`.
* **The readers** (`lookup.js` `headParts`, `headText`, `listRows`; `personal.js`): ", "
  between spellings, never the index's " / " (a data separator, kept in the index and in stored
  entries, old and new); a favourite carries `hgs` where the numbers differ, one stored before
  93 is renumbered from the index when drawn; the article page writes `data-hgs`.
* **The numbered glosses** (suggestions, history rows): each article numbered by the row's own
  spelling — *lysning*: "I … · II …".

The JS runs under bun (or node) against the real `lookup.js`, `personal.js` and `shell.js` over
a synthetic index built by `build_index.write_index`. Skipped when neither runner is on PATH."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_index as B  # noqa: E402
from ordpar.sitegen import article, page  # noqa: E402
import test_ordpar_favourites89 as F89  # noqa: E402  (its stand-in DOM)
import test_ordpar_history88 as H88  # noqa: E402  (its shell.js harness)


def _lem(lemma, hg, *tags):
    return {"lemma": lemma, "hgno": hg, "paradigm_info": [{"tags": list(tags) or ["NOUN", "Masc"]}]}


def _row(aid, *lemmas):
    return {"id": aid, "data": {"lemmas": list(lemmas)}}


# the mirror's own cases (ids and numbers as in bm-articles.jsonl, 2026-10-22)
ROWS = [
    _row(36349, _lem("lysing", 1, "NOUN", "Masc", "Fem"), _lem("lysning", 2, "NOUN", "Masc", "Fem")),
    _row(36371, _lem("lysning", 1)),
    _row(36350, _lem("lysing", 2)),
    _row(61543, _lem("tore", 2, "VERB"), _lem("tørre", 2, "VERB")),
    _row(61542, _lem("tore", 1, "NOUN", "Masc")),
    _row(3739, _lem("avrustning", 0), _lem("avrusting", 2)),
    _row(3738, _lem("avrusting", 1)),
    _row(592, _lem("akterskott", 1, "NOUN", "Neuter"), _lem("akterskut", 0, "NOUN", "Neuter")),
    _row(2164, _lem("antakelig", 1, "ADJ"), _lem("antagelig", 1, "ADJ")),
    _row(9657, _lem("deltakelse", 1, "NOUN", "Masc"), _lem("deltagelse", 1, "NOUN", "Masc"),
         _lem("deltaking", 0, "NOUN", "Fem", "Masc"), _lem("deltaing", 0, "NOUN", "Fem", "Masc")),
]
TRANSLATED = [36349, 36371, 61543, 61542]
SNIPPETS = {36349: ("a public announcement", "en"), 36371: ("a clearing", "en"),
            61543: ("to dare", "en"), 61542: ("Thor", "en")}


def _data(aid):
    return next(r["data"] for r in ROWS if r["id"] == aid)


def head_lines(h):
    """The headword lines of `head_html`'s block as text, each numeral as written ("II") and
    its hidden reading checked and dropped."""
    out = []
    for m in re.finditer(r'<(h1|p) class="ordpar-hw"[^>]*>(.*?)</\1>', h):
        inner = m.group(2)
        for num, said in re.findall(r'<span class="ordbok-homograph" aria-hidden="true">([^<]+)</span>'
                                    r'<span class="sr-only" data-nosnippet> homograph (\d+)</span>', inner):
            assert {"I": "1", "II": "2", "III": "3"}[num] == said, (num, said)
        inner = re.sub(r'<span class="sr-only"[^>]*>[^<]*</span>', "", inner)
        out.append(re.sub(r"<[^>]+>", "", inner))
    return out


class HeadwordLine(unittest.TestCase):
    """The article's headword line, each spelling its own numeral (`head_html`)."""

    def line(self, aid, pos="noun"):
        return head_lines(article.head_html({"lemmas": [], "pos_en": pos}, page.EN, data=_data(aid)))

    def test_differing_numbers(self):
        self.assertEqual(self.line(36349), ["lysing I, lysning II"])        # was "lysing, lysning I"
        self.assertEqual(self.line(3739), ["avrustning, avrusting II"])     # unchanged (the index had 0)
        self.assertEqual(self.line(592), ["akterskott I, akterskut"])

    def test_the_same_number_on_each(self):
        self.assertEqual(self.line(61543, "verb"), ["tore II, tørre II"])
        self.assertEqual(self.line(2164, "adjective"), ["antakelig I, antagelig I"])

    def test_paradigm_groups_keep_their_own(self):
        self.assertEqual(self.line(9657), ["deltakelse I, deltagelse I", "deltaking, deltaing"])
        bod = {"lemmas": [_lem("bod", 0, "NOUN", "Fem"), _lem("bu", 2, "NOUN", "Masc")]}
        h = article.head_html({"lemmas": [], "pos_en": "noun"}, page.EN, data=bod)
        self.assertEqual(head_lines(h), ["bod", "bu II"])

    def test_one_reading_per_numeral(self):
        h = article.head_html({"lemmas": [], "pos_en": "noun"}, page.EN, data=_data(36349))
        self.assertEqual(re.findall(r'<span class="sr-only" data-nosnippet> ([^<]+)</span>', h),
                         ["homograph 1", "homograph 2"])

    def test_without_a_mirror_row_the_library_lemmas(self):
        row = {"lemmas": [{"form": "lysing", "homograph": "I"}, {"form": "lysning", "homograph": "II"}],
               "pos_en": "noun"}
        self.assertEqual(head_lines(article.head_html(row, page.EN)), ["lysing I, lysning II"])
        self.assertEqual(article.lemma_groups(row)[0][0], [("lysing", "I"), ("lysning", "II")])


class IndexNumbers(unittest.TestCase):
    """The index's `words[id][1]` and the Python twin's answers."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx93-")
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        heads, forms, cls.words = B.build_tables(mirror, None, {})
        B.write_index(cls.tmp, heads, forms, cls.words, TRANSLATED, {}, snippets=SNIPPETS)
        cls.dir = os.path.join(cls.tmp, "index")
        cls.idx = B.Index(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_entry_carries_a_number_per_headword(self):
        self.assertEqual(B.entry(36349, _data(36349))[2], [1, 2])
        self.assertEqual(B.entry(61543, _data(61543))[2], [2, 2])

    def test_words_one_number_or_a_list(self):
        w = self.words
        self.assertEqual(w[36349], ["lysing / lysning", [1, 2], "NOUN"])
        self.assertEqual(w[3739], ["avrustning / avrusting", [0, 2], "NOUN"])
        self.assertEqual(w[592], ["akterskott / akterskut", [1, 0], "NOUN"])
        # the same on each: one int. Moved 2026-10-23 (decisions 93 (2)): 61543 is one of the
        # normalization log's lemma-order rulings, so the index reads it in our order
        self.assertEqual(w[61543], ["tørre / tore", 2, "VERB"])
        self.assertEqual(w[2164][1], 1)
        self.assertEqual(w[36371], ["lysning", 1, "NOUN"])           # one spelling: as before
        # more than three spellings: the numbers of the three shown decide
        self.assertEqual(w[9657], ["deltakelse / deltagelse / deltaking …", [1, 1, 0], "NOUN"])

    def test_form_hg(self):
        w = self.words
        self.assertEqual(B.form_hg(w[36349], "lysning"), 2)
        self.assertEqual(B.form_hg(w[36349], "lysing"), 1)
        self.assertEqual(B.form_hg(w[3739], "avrustning"), 0)
        self.assertEqual(B.form_hg(w[3739], "x"), 2)               # not shown: the first non-zero
        self.assertEqual(B.form_hg(w[61543], "tørre"), 2)
        self.assertEqual(B.form_hg(w[9657], "deltaing"), 1)        # a fourth spelling

    def test_results_numbered_and_ordered_by_the_matched_spelling(self):
        heads = self.idx.lookup("lysning")["heads"]
        self.assertEqual([(a["id"], a["hg"]) for a in heads[0]["articles"]], [(36371, 1), (36349, 2)])
        heads = self.idx.lookup("lysing")["heads"]
        self.assertEqual([(a["id"], a["hg"]) for a in heads[0]["articles"]], [(36349, 1), (36350, 2)])
        heads = self.idx.lookup("avrusting")["heads"]
        self.assertEqual([(a["id"], a["hg"]) for a in heads[0]["articles"]], [(3738, 1), (3739, 2)])
        # verbs first, as ordbokene's *tore*: tore II (verb) before tore I
        heads = self.idx.lookup("tore")["heads"]
        self.assertEqual([(a["id"], a["hg"]) for a in heads[0]["articles"]], [(61543, 2), (61542, 1)])

    def test_the_page_attributes(self):
        attrs = page.personal_attrs({"hg": 1, "hgs": [1, 2], "pos": "NOUN", "word": "lysing / lysning",
                                     "snip": "", "drop": None}, "lysing")
        self.assertIn(' data-hg="1" data-hgs="1 2"', attrs)
        self.assertNotIn("data-hgs", page.personal_attrs({"hg": 2, "hgs": None, "pos": "VERB",
                                                          "word": "tore / tørre", "snip": ""}, "tore"))

    # ------------------------------------------------------------ lookup.js

    JS = F89.FAKE_DOM + r"""
const fs = require('fs'), path = require('path');
const STR = JSON.parse(fs.readFileSync(%(strings)s, 'utf8'));
globalThis.ordparShell = { t: k => (k in STR ? STR[k] : k), ready: Promise.resolve(),
  onChange: () => {}, getSetting: () => 'multi' };
const store = {};
globalThis.localStorage = { getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
const P = require(%(personal)s);
const M = require(%(lookup)s), L = M.ordparLookup, S = M.ordparSearch;
L.setLoader(name => { const p = path.join(%(index)s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
const tick = () => new Promise(r => setTimeout(r, 20));
function out(v) { process.stdout.write(JSON.stringify(v)); }
"""

    def js(self, body):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        script = os.path.join(self.tmp, "run93.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(self.JS % {
                "strings": json.dumps(os.path.join(SITE, "strings", "en.json")),
                "personal": json.dumps(os.path.join(SITE, "personal.js")),
                "lookup": json.dumps(os.path.join(SITE, "lookup.js")),
                "index": json.dumps(self.dir),
            })
            fh.write("(async () => { " + body + " })().catch(e => { console.error(e); process.exit(1); });\n")
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))

    def test_js_lookup_matches_the_twin(self):
        got = self.js("""const r = [];
for (const q of ['lysning', 'lysing', 'avrusting', 'tore']) {
  const res = await L.lookup(q);
  r.push(res.heads[0].articles.map(a => [a.id, a.hg, a.hgs || null]));
}
out(r);""")
        self.assertEqual(got, [[[36371, 1, None], [36349, 2, [1, 2]]],
                               [[36349, 1, [1, 2]], [36350, 2, None]],
                               [[3738, 1, None], [3739, 2, [0, 2]]],
                               [[61543, 2, None], [61542, 1, None]]])

    def test_js_head_parts_and_text(self):
        got = self.js("""out([
  L.headText('lysing / lysning', 1, [1, 2]), L.headText('tore / tørre', 2),
  L.headText('avrustning / avrusting', 2, [0, 2]), L.headText('hus', 0),
  L.headText('deltakelse / deltagelse / deltaking …', 1, [1, 1, 0]),
  L.headParts('snipp, snapp, snute', 0).parts.length,
  L.formHg(['lysing / lysning', [1, 2], 'NOUN'], 'lysning')]);""")
        self.assertEqual(got, ["lysing I, lysning II", "tore II, tørre II", "avrustning, avrusting II",
                               "hus", "deltakelse I, deltagelse I, deltaking …", 1, 2])

    def test_list_view_rows_draw_the_line_with_commas(self):
        got = self.js("""const res = await L.lookup('lysning');
const wrap = S.listRows(res.heads[0].articles, Object.create(null));
out([].map.call(wrap.querySelectorAll('.ordpar-row-word'), w => w.textContent));""")
        self.assertEqual(got, ["lysning I homograph 1", "lysing I homograph 1, lysning II homograph 2"])

    def test_an_old_favourite_is_renumbered_from_the_index(self):
        # stored before 93: the " / " text and one number (its first lemma's) — read as stored,
        # drawn with ", ", its numerals corrected once the index answers
        got = self.js("""const e = { id: 36349, word: 'lysing / lysning', hg: 1, pos: 'NOUN', translated: true, snip: '', t: 1 };
const wrap = S.listRows([e], Object.create(null), { level: 2, mark: false, renumber: true });
const w = wrap.querySelector('.ordpar-row-word');
const first = w.textContent;
await tick();
const old = S.listRows([{ id: 61543, word: 'tore / tørre', hg: 2, pos: 'VERB', translated: true, t: 1 }],
  Object.create(null), { renumber: true }).querySelector('.ordpar-row-word');
await tick();
out([first, w.textContent, old.textContent]);""")
        # moved 2026-10-23 (decisions 93 (2)): the index now lists 61543 in our order, so a
        # favourite stored as "tore / tørre" is redrawn "tørre II, tore II" (`redrawFrom`)
        self.assertEqual(got, ["lysing I homograph 1, lysning I homograph 1",
                               "lysing I homograph 1, lysning II homograph 2",
                               "tørre II homograph 2, tore II homograph 2"])

    def test_favourites_store_the_numbers_per_spelling(self):
        got = self.js("""const res = await L.lookup('lysning');
const f = S.personalFields(res.heads[0].articles[1]);
P.setFavourite(f, true);
P.setFavourite({ id: 61543, word: 'tore / tørre', hg: 2, pos: 'VERB', translated: true }, true);
out([f, P.favourites().map(e => [e.id, e.word, e.hg, e.hgs || null])]);""")
        self.assertEqual(got[0]["hgs"], [1, 2])
        self.assertEqual(got[0]["hg"], 1)
        self.assertEqual(got[0]["word"], "lysing / lysning")
        self.assertEqual(sorted(got[1]), sorted([[36349, "lysing / lysning", 1, [1, 2]],
                                                 [61543, "tore / tørre", 2, None]]))

    def test_a_malformed_hgs_is_refused(self):
        got = self.js("""const raw = JSON.stringify([
  { id: 1, word: 'a / b', hg: 0, hgs: [1, 'x'], pos: '', translated: false, snip: '', t: 1 },
  { id: 2, word: 'a / b', hg: 0, hgs: [1], pos: '', translated: false, snip: '', t: 1 },
  { id: 3, word: 'c / d', hg: 1, hgs: [1, 2], pos: '', translated: false, snip: '', t: 1 },
  { id: 4, word: 'e / f', hg: 1, pos: '', translated: false, snip: '', t: 1 }]);
out(P.parseList(raw).map(e => [e.id, e.hgs || null]));""")
        self.assertEqual(got, [[3, [1, 2]], [4, None]])

    def test_old_history_entries_with_the_slash_still_read(self):
        # a pre-60b per-article entry, stored with the " / " text: its query is the first spelling
        got = self.js("""out(P.parseHistory(JSON.stringify([{ id: 36349, word: 'lysing / lysning', hg: 1,
  pos: 'NOUN', translated: true, snip: 'a public announcement', t: 5 }])));""")
        self.assertEqual(got[0]["q"], "lysing")
        self.assertEqual(got[0]["word"], "lysing / lysning")

    def test_suggestion_glosses_numbered_by_the_row_spelling(self):
        got = self.js("""const rows = await L.suggest('lysning');
const r = rows.find(x => x.word === 'lysning');
out(r.articles.map(a => [a.id, a.hg]));""")
        self.assertEqual(got, [[36371, 1], [36349, 2]])

    def test_the_page_heart_reads_data_hgs(self):
        got = self.js("""const h = doc.createElement('html');
h.hasAttribute = n => n in h.attrs;
h.ownerDocument = doc;
h.setAttribute('data-article-id', '36349'); h.setAttribute('data-lemma', 'lysing');
h.setAttribute('data-word', 'lysing / lysning'); h.setAttribute('data-hg', '1');
h.setAttribute('data-hgs', '1 2'); h.setAttribute('data-translated', '1'); h.setAttribute('data-snip', '');
out(P.fieldsFrom(h));""")
        self.assertEqual(got["hgs"], [1, 2])


class HistoryRowNumbers(unittest.TestCase):
    """A history row's numbered glosses: each article numbered by the row's own spelling."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="hist93-")
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        heads, forms, words = B.build_tables(mirror, None, {})
        B.write_index(cls.tmp, heads, forms, words, TRANSLATED, {}, snippets=SNIPPETS)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def h88(self):
        inst = H88.HistoryGlosses88("row")     # its harness: shell.js's history functions
        inst.tmp = self.tmp
        return inst

    def test_lysning(self):
        got = self.h88().js("out(await row({q: 'lysning', n: 2, t: 1}));")
        items = got["side"][0]["items"]
        self.assertEqual([i["hg"] for i in items], ["I", "II"])
        self.assertTrue(items[0]["text"].endswith(" a clearing"))
        self.assertTrue(items[1]["text"].endswith(" a public announcement"))

    def test_the_headword_colour_follows_the_articles(self):
        # 88's second amendment: the row's colour class set from what the search finds
        got = self.h88().js("""const holder = el('a');
const e = {q: 'lysning', n: 2, t: 1};
const side = F.searchRowSide(e); holder.appendChild(side);
await F.fillSearchRow(side, e);
const e2 = {q: 'avrusting', n: 2, t: 1};
const holder2 = el('a');
const side2 = F.searchRowSide(e2); holder2.appendChild(side2);
await F.fillSearchRow(side2, e2);
out([holder.className, holder2.className, dump(side2)]);""")
        self.assertEqual(got[0], "is-translated")
        self.assertEqual(got[1], "")                      # neither avrusting is translated
        self.assertEqual(got[2], [{"cls": "ordpar-option-count", "text": "2 articles"}])


if __name__ == "__main__":
    unittest.main()
