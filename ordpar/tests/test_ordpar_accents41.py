# -*- coding: utf-8 -*-
"""Pins accent folding in the lookup index (decisions 41 (a), Robin 2026-10-18; `ordpar/build_index.py`
`bare` / `accent_match` / `dedupe_accent_groups`, and their twins in `ordpar/site/lookup.js`):

* The fold table: à ä ç è é ê î ò ô ü fold to their letter; æ ø å (either case) never fold, and
  nor does anything that is not a letter plus combining marks (– ’ …).
* Shard placement: an accented initial lives with its letter (`én` in `e.json` and
  `headwords/e.json`, `à la mode` with `a`), never in `misc`; a split letter's second character
  folds too (`salongfähig` in `s-a`).
* Autocomplete, both directions: typed without the accent it offers the accented headword
  (`a la` -> `à la mode`, `og` -> `òg`); typed with it, only accented headwords (`òg` never
  offers `og`, `kafé` never offers `kafe`). The order, as ordbokene's (decisions 46 brief,
  2026-10-18): the continuations reached only through the accent fold come last (`kafe` ->
  kafe, kafé, kafeliv, kaféliv; `e` -> en, ende, én); a form equal to the prefix, or one whose
  typed letters match as spelled, keeps its length place (`kaf` -> kafe, kafé, kafeliv …).
* Lookup: one way, the same; an article is listed once (`en` lists `en / én` once, under "en").
* Similar words: an accent is never an edit; a lookup hit is never listed, the other direction
  is, at 0 (`òg` -> `og`).
* æ ø å untouched: `are` never finds `ære`, `al` never `ål`, `o` never offers `øl`.
* When `bun` (or `node`) is on PATH, `lookup.js` answers the same as the Python twin.

Synthetic rows only: no mirror and no library file are read."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

import build_index as B  # noqa: E402


def _row(aid, lemmas, pos="NOUN", forms=()):
    if isinstance(lemmas, str):
        lemmas = [lemmas]
    return {"id": aid, "data": {"lemmas": [{
        "lemma": w, "hgno": 0,
        "paradigm_info": [{"tags": [pos],
                           "inflection": [{"word_form": f} for f in forms]}]} for w in lemmas]}}


ROWS = [
    _row(30, ["en", "én"], "DET"),
    _row(31, "en", "PRON"),
    _row(40, ["kafé", "kafe"], forms=["kaféen", "kafeen"]),
    _row(41, "à la mode", "EXPR"),
    _row(42, "òg", "ADV"),
    _row(43, "og", "CCONJ"),
    _row(44, "salongfähig", "ADJ", forms=["salongfähige"]),
    _row(45, "ære"),
    _row(46, "are"),
    _row(47, "øl"),
    _row(48, "ol"),
    _row(49, "ål"),
    _row(50, "al"),
    _row(52, "crème fraîche", "EXPR"),
    _row(53, "-aktig", "SUFF"),
    _row(54, "kaféliv"),
    _row(55, "kafeliv"),
    _row(56, "ende", "VERB"),
]


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TestFoldTable(unittest.TestCase):
    def test_folds(self):
        for c, base in zip("àäçèéêîòôü", "aaceeeioou"):
            self.assertEqual(B.bare_char(c), base, c)
            self.assertEqual(B.bare(c.upper()), base, c)

    def test_never_folds(self):
        for c in "æøåÆØÅ–’…-1":
            self.assertEqual(B.bare(c), B.fold(c), c)
        self.assertEqual(B.bare("Ærlig blåbær på øya"), "ærlig blåbær på øya")
        self.assertEqual(B.bare("À la carte"), "a la carte")
        self.assertEqual(len(B.bare("crème fraîche")), len("crème fraîche"))

    def test_accent_match_is_one_way(self):
        self.assertTrue(B.accent_match("en", "én"))
        self.assertTrue(B.accent_match("a la", "à la mode"))
        self.assertFalse(B.accent_match("én", "en"))
        self.assertFalse(B.accent_match("à la", "a la mode"))
        self.assertFalse(B.accent_match("ae", "æ"))
        self.assertFalse(B.accent_match("a", "å"))

    def test_keys(self):
        for w, k in (("én", "e"), ("à la carte", "a"), ("òg", "o"), ("Écu", "e"),
                     ("ære", "ae"), ("øl", "oe"), ("ål", "aa"), ("-aktig", "misc")):
            self.assertEqual(B.letter_key(w), k, w)
        self.assertEqual(B.shard_key("salongfähig"), "s-a")
        self.assertEqual(B.shard_key("så"), "s-aa")
        self.assertEqual(B.suggest_key("é"), "e")


class TestAccentIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx41-")
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        stats = {}
        heads, forms, words = B.build_tables(mirror, None, stats)
        B.write_index(cls.tmp, heads, forms, words, [30, 40], stats)
        cls.dir = os.path.join(cls.tmp, "index")
        cls.idx = B.Index(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def sug(self, q):
        return [s["word"] for s in self.idx.suggest(q)]

    def heads(self, q):
        return [(g["form"], [a["id"] for a in g["articles"]]) for g in self.idx.lookup(q)["heads"]]

    def forms(self, q):
        return [(g["form"], [a["id"] for a in g["articles"]]) for g in self.idx.lookup(q)["forms"]]

    def sim(self, q):
        return [(s["word"], s["dist"]) for s in self.idx.similar(q)]

    def test_shard_placement(self):
        self.assertIn("én", _load(os.path.join(self.dir, "e.json"))["heads"])
        self.assertIn("à la mode", _load(os.path.join(self.dir, "a.json"))["heads"])
        self.assertIn("òg", _load(os.path.join(self.dir, "o.json"))["heads"])
        self.assertIn("salongfähig", _load(os.path.join(self.dir, "s-a.json"))["heads"])
        self.assertEqual(list(_load(os.path.join(self.dir, "misc.json"))["heads"]), ["-aktig"])
        # the headwords files are {"w": forms, "f": bands} since decisions 55
        self.assertIn("én", _load(os.path.join(self.dir, "headwords", "e.json"))["w"])
        self.assertEqual(_load(os.path.join(self.dir, "headwords", "misc.json"))["w"], ["-aktig"])
        # æ ø å keep their own shards
        self.assertIn("ære", _load(os.path.join(self.dir, "ae.json"))["heads"])
        self.assertIn("øl", _load(os.path.join(self.dir, "oe.json"))["heads"])
        self.assertIn("ål", _load(os.path.join(self.dir, "aa.json"))["heads"])

    def test_suggest_without_accent_offers_accented(self):
        self.assertEqual(self.sug("en"), ["en", "én", "ende"])
        self.assertEqual(self.sug("a la"), ["à la mode"])
        self.assertEqual(self.sug("og"), ["og", "òg"])
        # kafe and kafé are one article: one row since site decisions 82 (its forms both)
        self.assertEqual(self.sug("kafe"), ["kafe", "kafeliv", "kaféliv"])
        self.assertEqual(self.idx.suggest("kafe")[0]["forms"], ["kafe", "kafé"])
        self.assertEqual(self.sug("salongfa"), ["salongfähig"])
        self.assertEqual(self.sug("creme"), ["crème fraîche"])

    def test_suggest_accented_continuations_last(self):
        # as ordbokene (suggest API, 2026-10-18): its `e` never reaches `én`, its `en` offers
        # `én` second, its `kafe` lists every kafe- word before kaféliv
        self.assertEqual(self.sug("e"), ["en", "ende", "én"])
        self.assertEqual(self.sug("en"), ["en", "én", "ende"])
        # but a continuation whose typed letters match as spelled keeps its length place,
        # as ordbokene's `kaf` (kafe, kafé, kaffe … kafkask, kaféliv); kafé merges into the
        # row of kafe, its own article's best form (site decisions 82)
        self.assertEqual(self.sug("kaf"), ["kafe", "kafeliv", "kaféliv"])
        self.assertEqual(B.suggest_order("én", "e")[0], True)
        self.assertEqual(B.suggest_order("én", "en")[0], False)

    def test_suggest_with_accent_offers_only_accented(self):
        self.assertEqual(self.sug("én"), ["én"])
        self.assertEqual(self.sug("à la"), ["à la mode"])
        self.assertEqual(self.sug("òg"), ["òg"])
        self.assertEqual(self.sug("kafé"), ["kafé", "kaféliv"])
        self.assertEqual(self.sug("crè"), ["crème fraîche"])

    def test_lookup_one_way(self):
        self.assertEqual(self.heads("og"), [("og", [43]), ("òg", [42])])
        self.assertEqual(self.heads("òg"), [("òg", [42])])
        self.assertEqual(self.heads("a la mode"), [("à la mode", [41])])
        self.assertEqual(self.heads("à la mode"), [("à la mode", [41])])
        self.assertEqual(self.heads("creme fraiche"), [("crème fraîche", [52])])
        self.assertEqual(self.forms("salongfahige"), [("salongfähige", [44])])
        self.assertEqual(self.heads("én"), [("én", [30])])

    def test_lookup_lists_an_article_once(self):
        # en / én is one article: listed under "en", not again under "én"
        self.assertEqual(self.heads("en"), [("en", [30, 31])])
        self.assertEqual(self.heads("kafe"), [("kafe", [40])])
        self.assertEqual(self.forms("kafeen"), [("kafeen", [40])])
        self.assertEqual(self.forms("kaféen"), [("kaféen", [40])])

    def test_similar_accent_is_not_an_edit(self):
        self.assertEqual(self.sim("òg")[:1], [("og", 0)])          # the other direction, at 0
        self.assertNotIn("òg", [w for w, _ in self.sim("og")])     # a hit is never listed
        self.assertEqual(self.sim("salongfahih"), [("salongfähig", 1)])
        self.assertEqual(self.sim("kafé")[:1], [("kafe", 0)])      # as ordbokene: kafé -> kafe

    def test_norwegian_letters_untouched(self):
        self.assertEqual(self.heads("are"), [("are", [46])])
        self.assertEqual(self.heads("al"), [("al", [50])])
        self.assertEqual(self.heads("ol"), [("ol", [48])])
        self.assertNotIn("øl", self.sug("o"))
        self.assertNotIn("ål", self.sug("a"))
        self.assertNotIn("ære", self.sug("a"))
        self.assertEqual(self.sug("æ"), ["ære"])
        # æ for a is an edit, never folded: ære is one edit from are, reached only past the
        # first letter (a hit's list is built as a miss's since decisions 56), never at 0
        self.assertEqual(B.osa(B.bare("are"), B.bare("ære")), 1)
        self.assertEqual(self.sim("are"), [("ære", 1)])
        self.assertEqual([(s["word"], s["dist"]) for s in self.idx.similar("are", wide=False)], [])

    def test_js_matches_python(self):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        queries = ["en", "én", "a la", "à la", "a la mode", "à la mode", "og", "òg", "o", "kafe",
                   "kafé", "kafeen", "kaféen", "salongfa", "salongfahig", "salongfahige",
                   "salongfahih", "creme", "crè", "creme fraiche", "are", "al", "ol", "a", "æ",
                   "ae", "e", "é", "-akt", "kaf", "kafel", "end"]
        script = os.path.join(self.tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""
const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const dir = %s;
L.setLoader(n => { const p = path.join(dir, n); return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
(async () => { const out = {};
  for (const q of %s) { const r = await L.lookup(q);
    out[q] = [r.heads, r.forms, (await L.suggest(q)).map(s => [s.word, s.translated]),
              (await L.similar(q)).map(s => [s.word, s.dist]), L.shardKey(q), L.letterKey(q),
              L.suggestKey(q), L.bare(q)]; }
  process.stdout.write(JSON.stringify(out)); })();
""" % (json.dumps(os.path.join(ROOT, "ordpar", "site", "lookup.js")), json.dumps(self.dir),
                json.dumps(queries, ensure_ascii=False)))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        js = json.loads(res.stdout.decode("utf-8"))
        for q in queries:
            r = self.idx.lookup(q)
            py = [r["heads"], r["forms"],
                  [[s["word"], s["translated"]] for s in self.idx.suggest(q)],
                  [[s["word"], s["dist"]] for s in self.idx.similar(q)],
                  B.shard_key(q), B.letter_key(q), B.suggest_key(q), B.bare(q)]
            self.assertEqual(js[q], py, q)


if __name__ == "__main__":
    unittest.main()
