#!/usr/bin/env python3
"""Site decisions 148, 149 and 150 (Robin, 2026-10-29): the English search, the similar headwords
that would only repeat the page, the spelling typed in the Norwegian suggestions — the source side.

Pins, in `build_index.py` (`en_split_unit`, `en_key_of`, `en_norm`, `en_spelling_map`, `en_stems`,
`english_index`, `english_files`, `EnglishIndex`) and its twin `lookup.js` (`englishLookup`,
`englishSuggest`, `englishSimilar`, `typedLine`, `dropRepeats`):

* **the split and the keys** — a unit cut at "," and ";" outside brackets; the key lower case,
  bracketed text and `{…}` mentions dropped, one leading "to", "a", "an", "the" dropped; an
  explanation unit (all brackets) not indexed; each entry its article, unit, place and the span
  the list view marks bold;
* **the map** — American -> British from the glosses' -ise/-our words and the named pairs;
* **the stems** — the lab's rule without -er (*running* no longer pairs with *runner*), and the
  irregular verb table (*swam* -> *swim*);
* **the shards** — one file per first letter; a phrase also in the file of each of its words'
  letters ("go swimming" in `s`); an irregular pair across letters in both (*went* / *go*); every
  article a file names once, with what the rows need; the miss line's numbers;
* **the tails files** (148's follow-up, Robin 2026-10-29: "the English similar words reach other
  first letters as the Norwegian ones do") — the one-word keys again, filed by their second and
  third characters, each with only what a similar row needs (no spans, no gloss);
* **over the build** (skipped without `ordpar/out/index/en/`): the sizes in the manifest; order
  (c) — *go*: *gå* first; *house*: *hus*, *house*, *bosette*; *candle* one article; the similar
  words of *swimming* (*swim*, *go swimming* …) and of *house* after a hit (none of its own
  articles); *hoose* past the first letter: *house*, *choose*, *horse*, *loose*, *hose*; the
  requests — a search's results ONE file cold and none warm, the similar words then the two tails
  files and the second letter's; and lookup.js agreeing with the Python twin, under bun, on the
  searches, the suggestions and the similar words;
* **149** — `dropRepeats` (under bun): *selvlagd* and *selvlaga* left out on *selvlaget*'s page,
  *rette* kept on *rett*'s (it heads two articles, one not on the page);
* **150** — `typedLine` (under bun, over the build): "selv" shows *selvsagt* alone, "sjøl"
  *sjølsagt* alone (the line carries the spelling's numeral as data; the dropdown draws none
  after a headword, Robin 2026-10-23);
* **History and the switch** (`personal.js`, under bun): an English entry kept with its mark, the
  English and the Norwegian *house* two entries, the direction saved and read back, Norwegian by
  default;
* **the offline copy** — the English shards in packs of their own, the English tails files in
  one pack per first key (`build_offline.file_group`);
* **the words** — the DRAFT words as Robin approved them (strings/en.json).

The look and the behaviour in a browser: `test_ordpar_browser_english148.py`.
Stdlib unittest; the JavaScript runs under bun (or node), skipped when neither is on PATH.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
INDEX = os.path.join(ORDPAR, "out", "index")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)

from ordpar import build_index as B  # noqa: E402
from ordpar import build_offline as O  # noqa: E402

BUILT = os.path.exists(os.path.join(INDEX, "en", "h.json"))
RUNNER = shutil.which("bun") or shutil.which("node")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _js(body, en_dir=None, tmp=None):
    """Run `body` under bun with lookup.js (and personal.js) loaded, the loader reading the built
    index (the English files from `en_dir` when given); -> the JSON it prints."""
    if not RUNNER:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tmp or tempfile.mkdtemp()
    script = os.path.join(tmp, "run148.js")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write("""const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const S = require(%s).ordparSearch;
const IDX = %s, EN = %s;
L.setLoader(name => { const p = name.startsWith('en/') && EN ? path.join(EN, name.slice(3)) : path.join(IDX, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
const out = x => process.stdout.write(JSON.stringify(x));
(async () => { %s })().catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
""" % (json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(os.path.join(SITE, "lookup.js")),
       json.dumps(INDEX), json.dumps(en_dir), body))
    res = subprocess.run([RUNNER, script], capture_output=True, timeout=120)
    if res.returncode != 0:
        raise AssertionError(res.stderr.decode("utf-8", "replace"))
    return json.loads(res.stdout.decode("utf-8"))


# --------------------------------------------------------------------------- the rules

class TheKeys(unittest.TestCase):

    def test_split_outside_brackets(self):
        self.assertEqual(B.en_split_unit("to go, to travel"), [("to go", ", "), ("to travel", "")])
        self.assertEqual(B.en_split_unit("at (a price of, each)"), [("at (a price of, each)", "")])
        self.assertEqual(B.en_split_unit("a; b"), [("a", "; "), ("b", "")])

    def test_the_key(self):
        self.assertEqual(B.en_key_of("to house (someone)"), ("house", "eq"))
        self.assertEqual(B.en_key_of("the Bible"), ("bible", "eq"))
        self.assertEqual(B.en_key_of("an apple"), ("apple", "eq"))
        self.assertEqual(B.en_key_of("to go"), ("go", "eq"))
        self.assertEqual(B.en_key_of("to"), ("to", "eq"))                 # never emptied
        self.assertEqual(B.en_key_of("sinful (in {den gamle adam})"), ("sinful", "eq"))
        self.assertEqual(B.en_key_of("Swimming pool."), ("swimming pool", "eq"))
        # an explanation (all brackets) is not indexed (site decisions 148 item 1)
        self.assertEqual(B.en_key_of("(particle used only in exclamations)"), ("", "x"))
        self.assertEqual(B.en_key_of("{uff}"), ("", "m"))

    def test_norm_is_the_query_rule_too(self):
        self.assertEqual(B.en_norm("  To   Go "), "go")
        self.assertEqual(B.en_norm("the"), "the")
        self.assertEqual(B.en_letter("house"), "h")
        self.assertEqual(B.en_letter("Épée"), "e")
        self.assertEqual(B.en_letter("1st"), B.MISC_SHARD)

    def test_the_map(self):
        sp = B.en_spelling_map(["organise", "colour film", "centre"])
        self.assertEqual(sp["organize"], "organise")
        self.assertEqual(sp["color"], "colour")
        self.assertEqual(sp["center"], "centre")
        self.assertNotIn("advize", sp)                                   # -ise in American too
        self.assertNotIn("hor", sp)                                      # hour is not humour

    def test_the_stems(self):
        self.assertIn("swim", B.en_stems("swimming"))
        self.assertIn("house", B.en_stems("houses"))
        self.assertIn("try", B.en_stems("tries"))
        self.assertIn("swim", B.en_stems("swam"))
        self.assertIn("go", B.en_stems("went"))
        # without -er (the lab's rule gave *runner* for *running*)
        self.assertFalse(set(B.en_stems("runner")) & set(B.en_stems("running")))
        for form, base in B.EN_FORM_BASE.items():
            self.assertNotEqual(form, base)
            self.assertIn(base, B.EN_IRREGULAR)


def _library():
    return {
        1: {"en": ["to go, to travel"]},
        2: {"en": ["to walk", "to go"]},
        3: {"en": ["to go swimming"]},
        4: {"en": ["to swim"]},
        5: {"en": ["to house (someone)", "(an explanation only)"]},
        6: {"en": ["house"]},
        7: {"en": ["went"]},                   # an irregular form, filed under w
        9: {"en": ["untranslated"]},           # not on the site
    }


WORDS = {1: ["dra", 0, "VERB"], 2: ["gå", 0, "VERB"], 3: ["bade", 0, "VERB"], 4: ["svømme", 0, "VERB"],
         5: ["bosette / busette", 0, "VERB"], 6: ["hus", 0, "NOUN"], 7: ["dro", 0, "VERB"],
         9: ["x", 0, "NOUN"]}
BANDS = {"dra": 11, "gå": 12, "bade": 8, "svømme": 9, "bosette": 8, "busette": 3, "hus": 11, "dro": 5}


class TheShards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.idx = B.english_index(_library(), WORDS, BANDS, [1, 2, 3, 4, 5, 6, 7])
        cls.files = B.english_files(cls.idx, 100)
        cls.tmp = tempfile.mkdtemp()
        for L, sh in cls.files.items():
            p = os.path.join(cls.tmp, "en", L + ".json")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(B.dump(sh))
        cls.E = B.EnglishIndex(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_only_the_site_translated(self):
        self.assertNotIn(9, self.idx["a"])
        self.assertEqual(self.idx["stats"]["glossed_not_on_site"], 1)
        self.assertEqual(self.idx["stats"]["explanations_not_indexed"], 1)
        self.assertNotIn("an explanation only", self.idx["k"])

    def test_entries_carry_the_span(self):
        # "to go, to travel": go at place 1 of unit 1, its span the whole "to go"
        self.assertEqual(self.idx["k"]["go"][0], [1, 1, 1, 0, 5])
        self.assertEqual(self.idx["k"]["travel"][0], [1, 1, 2, 7, 16])
        self.assertEqual(self.idx["a"][1][5], ["to go, to travel"])
        # the article: its headword text, hg, pos, band (its spellings' highest), rank, units
        a5 = self.idx["a"][5]
        self.assertEqual(a5[:4], ["bosette / busette", 0, "VERB", 8])
        self.assertEqual(a5[5], ["to house (someone)", "(an explanation only)"])

    def test_one_file_per_letter_and_the_phrases(self):
        self.assertIn("go swimming", self.files["g"]["e"])
        self.assertIn("go swimming", self.files["s"]["e"])     # the similar words' phrase rule
        self.assertNotIn("house", self.files["g"]["e"])
        # an irregular pair across letters, in both files
        self.assertIn("went", self.files["g"]["e"])
        self.assertIn("go", self.files["w"]["e"])
        self.assertEqual(self.files["w"]["ir"]["went"], "go")
        # each article a file names, once, with the rows' fields
        self.assertEqual(sorted(self.files["h"]["a"]), ["5", "6"])
        self.assertEqual((self.files["h"]["c"], self.files["h"]["p"]), (7, 7))

    def test_order_c(self):
        # units 1 and 2 one tier, by band: gå (unit 2, band 12) before dra (unit 1, band 11)
        self.assertEqual([m["id"] for m in self.E.matches("go")], [2, 1])
        self.assertEqual([m["id"] for m in self.E.matches("To Go")], [2, 1])

    def test_suggest_and_similar(self):
        self.assertEqual([i["word"] for i in self.E.suggest("go")], ["go", "go swimming"])
        # both word matches; then the higher band first (svømme 9, bade 8)
        sim = [i["word"] for i in self.E.similar("swimming")]
        self.assertEqual(sim[:2], ["swim", "go swimming"])
        # site decisions 149's rule: a word whose articles are all on the page is left out
        self.assertEqual([i["word"] for i in self.E.similar("swimming", shown=[3])], ["swim"])

    def test_the_tails_files(self):
        tails = B.english_tails(self.idx)
        # one-word keys only, by their 2nd and 3rd characters (the Norwegian tails/ rule)
        self.assertIn("house", tails["o-u"]["e"])
        self.assertIn("swim", tails["w-i"]["e"])
        self.assertIn("go", tails["o-misc"]["e"])
        self.assertFalse(any("go swimming" in t["e"] for t in tails.values()))
        self.assertEqual(B.en_tail_key("choose"), "h-o")
        self.assertEqual(B.remainder_key("hoose"), "h-o")          # a missing first letter
        self.assertEqual(B.remainder_key("oose"), "o-o")           # a wrong one: loose
        # a row's needs only: [id, unit, place]; [first spelling, its numeral, pos, band, rank]
        self.assertEqual(tails["o-u"]["e"]["house"], [[5, 1, 1], [6, 1, 1]])
        self.assertEqual(tails["o-u"]["a"]["5"][:4], ["bosette", 0, "VERB", 8])
        self.assertEqual(len(tails["o-u"]["a"]["5"]), 5)


# --------------------------------------------------------------------------- over the build

@unittest.skipUnless(BUILT, "no build with the English index (ordpar/out/index/en/)")
class OverTheBuild(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.E = B.EnglishIndex(INDEX)
        cls.manifest = json.loads(_read(INDEX, "index.json"))

    def words(self, q):
        sh = self.E.shard(B.en_letter(B.en_norm(q)))
        return [sh["a"][str(m["id"])][0].split(" / ")[0] for m in self.E.matches(q)]

    def test_the_manifest(self):
        en = self.manifest["english"]
        self.assertGreater(en["articles"], 9000)
        self.assertEqual(en["explanations_not_indexed"], 3)
        files = {f["k"]: f for f in en["files"]}
        self.assertIn("h", files)
        for f in en["files"]:
            self.assertTrue(os.path.exists(os.path.join(INDEX, f["file"])), f["file"])
        self.assertEqual(en["gzip"], sum(f["gzip"] for f in en["files"]))
        self.assertEqual(en["largest_gzip"], max(f["gzip"] for f in en["files"]))

    def test_order_c_on_real_searches(self):
        self.assertEqual(self.words("go")[0], "gå")               # Robin's case for (c)
        self.assertEqual(self.words("house")[:3], ["hus", "house", "bosette"])
        self.assertEqual(self.words("run")[0], "løpe")
        self.assertEqual(len(self.words("candle")), 1)
        self.assertEqual(self.words("color"), self.words("colour"))   # the map

    def test_similar_words(self):
        sim = [i["word"] for i in self.E.similar("swimming")]
        self.assertIn("swim", sim)
        self.assertIn("go swimming", sim)
        hits = [m["id"] for m in self.E.matches("house")]
        sh = self.E.shard("h")
        for i in self.E.similar("house", shown=hits):
            self.assertFalse(set(i["ids"]) <= set(hits), i["word"])
        self.assertNotIn("runner", [i["word"] for i in self.E.similar("running")])

    def test_the_tails_in_the_manifest(self):
        t = self.manifest["english"]["tails"]
        self.assertGreater(t["count"], 300)
        self.assertEqual(t["gzip"], sum(f["gzip"] for f in t["files"]))
        for f in t["files"]:
            self.assertTrue(os.path.exists(os.path.join(INDEX, "en", "tails", f["k"] + ".json")), f["k"])

    def test_past_the_first_letter(self):
        # Robin, 2026-10-29 ("Yes, before deploy"): hoose -> choose (a missing first letter) and
        # loose (a wrong one), as the lab listed them, beside its own letter's house, horse, hose
        self.assertEqual([i["word"] for i in self.E.similar("hoose")],
                         ["house", "choose", "horse", "loose", "hose"])
        self.assertIn("house", [i["word"] for i in self.E.similar("xhouse")])    # an extra one
        self.assertIn("house", [i["word"] for i in self.E.similar("ouse")])
        self.assertIn("swim", [i["word"] for i in self.E.similar("wsim")])

    def test_the_requests(self):
        # the results keep their ONE request; the similar words, after them, read the two tails
        # files and the second letter's file; warm, nothing
        got = _js("""const asked = [];
L.setLoader(name => { asked.push(name); const p = path.join(IDX, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
const r = {};
await L.englishLookup('hoose'); r.results = asked.splice(0);
await L.englishSimilar('hoose', null, {}); r.similar = asked.splice(0).sort();
await L.englishLookup('hoose'); await L.englishSimilar('hoose', null, {}); r.warm = asked.splice(0);
await L.englishLookup('house'); r.hit = asked.splice(0);
await L.englishSimilar('house', null, {}); r.hitSimilar = asked.splice(0).sort();
out(r);""")
        self.assertEqual(got["results"], ["en/h.json"])
        self.assertEqual(got["similar"], ["en/o.json", "en/tails/h-o.json", "en/tails/o-o.json"])
        self.assertEqual(got["warm"], [])
        self.assertEqual(got["hit"], [])                                      # h is loaded
        self.assertEqual(got["hitSimilar"], ["en/tails/o-u.json"])   # h-o and o loaded

    def test_js_agrees_with_python(self):
        qs = ["go", "house", "run", "light", "colour", "color", "drive", "dye", "candle", "smartphone"]
        got = _js("""const r = []; for (const q of %s) { const x = await L.englishLookup(q);
  r.push(x.matches.map(m => m.id)); } out(r);""" % json.dumps(qs))
        self.assertEqual(got, [[m["id"] for m in self.E.matches(q)] for q in qs])
        ps = ["hou", "run", "phone", "colo", "swim"]
        got = _js("""const r = []; for (const q of %s) { const x = await L.englishSuggest(q);
  r.push(x.map(i => [i.word, i.arts.map(a => a.id)])); } out(r);""" % json.dumps(ps))
        self.assertEqual(got, [[[i["word"], i["ids"]] for i in self.E.suggest(p)] for p in ps])
        ss = ["swimming", "hoose", "running", "colours", "swam", "ouse", "xhouse", "nife", "frend", "wsim"]
        got = _js("""const r = []; for (const q of %s) { const x = await L.englishSimilar(q, null, {});
  r.push(x.map(i => i.word)); } out(r);""" % json.dumps(ss))
        self.assertEqual(got, [[i["word"] for i in self.E.similar(s)] for s in ss])

    def test_150_the_spelling_typed(self):
        got = _js("""const a = await L.suggest('selv'), b = await L.suggest('sjøl');
  const line = (rs, w) => { const x = rs.find(i => i.line && i.line[0].w === w); return x ? x.line : null; };
  out({ selv: line(a, 'selvsagt'), sjol: line(b, 'sjølsagt'),
        mixed: a.concat(b).filter(i => i.line && i.line.length !== 1).length });""")
        self.assertEqual(got["selv"], [{"w": "selvsagt", "match": True, "hg": 0}])
        self.assertEqual(got["sjol"], [{"w": "sjølsagt", "match": True, "hg": 0}])
        self.assertEqual(got["mixed"], 0)


# --------------------------------------------------------------------------- 149

class DropRepeats149(unittest.TestCase):
    """`dropRepeats` over stand-in pages: no shard loaded for the candidates, so the rule by the
    spellings on the page and the headwords file's count."""

    def run_drop(self, words, res, spell=None):
        tmp = tempfile.mkdtemp()
        try:
            src = _read(SITE, "lookup.js")
            body = src.split("  function dropRepeats(words, res, spell) {")[1].split("\n  }\n")[0]
            script = """const SEP = ' / '; const shards = {}; const shardKey = x => x; const fold = x => x;
function dropRepeats(words, res, spell) {%s
}
process.stdout.write(JSON.stringify(dropRepeats(%s, %s, %s).map(s => s.word)));""" % (
                body, json.dumps(words), json.dumps(res), json.dumps(spell))
            p = os.path.join(tmp, "drop.js")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(script)
            if not RUNNER:
                self.skipTest("no bun/node on PATH")
            r = subprocess.run([RUNNER, p], capture_output=True, timeout=60)
            if r.returncode:
                raise AssertionError(r.stderr.decode("utf-8", "replace"))
            return json.loads(r.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_selvlaget(self):
        res = {"heads": [{"form": "selvlaget", "articles": [
            {"id": 47000, "word": "selvlaget / selvlagd / selvlaga …"}]}], "forms": []}
        words = [{"word": "selvlagd", "count": 1}, {"word": "selvlaga", "count": 1},
                 {"word": "selvlagt", "count": 1}, {"word": "sjøllaget", "count": 1}]
        # the index's text keeps three spellings: the fourth is known from the article in full
        self.assertEqual(self.run_drop(words, res), ["selvlagt", "sjøllaget"])
        spell = {"47000": ["selvlaget", "selvlagd", "selvlaga", "sjøllaget", "sjøllagd", "sjøllaga"]}
        self.assertEqual(self.run_drop(words, res, spell), ["selvlagt"])

    def test_rett_keeps_rette(self):
        res = {"heads": [{"form": "rett", "articles": [{"id": 1, "word": "rett"}, {"id": 2, "word": "rett"},
                                                        {"id": 3, "word": "rett"}]}],
               "forms": [{"form": "rett", "articles": [{"id": 50, "word": "rette"}]}]}
        words = [{"word": "rette", "count": 2}, {"word": "rest", "count": 1}]
        self.assertEqual(self.run_drop(words, res), ["rette", "rest"])
        # had rette headed one article only, the page would already show it
        self.assertEqual(self.run_drop([{"word": "rette", "count": 1}], res), [])

    def test_wired_into_render(self):
        js = _read(SITE, "lookup.js")
        self.assertIn("if (showing) { words = dropRepeats(words, res, pageSpellings(results)).slice(0, config.similarCount); }", js)
        self.assertIn("var whole = showing && shown ? shown.then(null, function () { return null; }) : null;", js)


# --------------------------------------------------------------------------- History, the switch

class PersonalEnglish(unittest.TestCase):

    def run_personal(self, body):
        if not RUNNER:
            self.skipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "personal.js")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("""const store = {}; globalThis.localStorage = { getItem: k => k in store ? store[k] : null,
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }, clear: () => {} };
const P = require(%s);
const out = x => process.stdout.write(JSON.stringify(x));
%s""" % (json.dumps(os.path.join(SITE, "personal.js")), body))
            r = subprocess.run([RUNNER, p], capture_output=True, timeout=60)
            if r.returncode:
                raise AssertionError(r.stderr.decode("utf-8", "replace"))
            return json.loads(r.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_english_entries(self):
        got = self.run_personal("""P.recordSearch({ q: 'house', n: 3, en: true }, 10);
P.recordSearch({ q: 'house', n: 1, word: 'house', hg: 0, pos: 'NOUN', translated: true, text: 'house music' }, 20);
P.recordSearch({ q: 'House', n: 3, en: true }, 30);
out(P.history());""")
        self.assertEqual([(e["q"], e.get("en", False)) for e in got], [("House", True), ("house", False)])
        self.assertEqual(got[0], {"q": "House", "n": 3, "t": 30, "en": True})

    def test_the_direction(self):
        got = self.run_personal("""const a = P.direction(); P.setDirection('en'); const b = P.direction();
const raw = localStorage.getItem(P.DIRECTION_KEY); P.setDirection('nb'); out([a, b, raw, P.direction()]);""")
        self.assertEqual(got, ["nb", "en", "en", "nb"])


# --------------------------------------------------------------------------- the rest

class TheRest(unittest.TestCase):

    def test_offline_packs(self):
        self.assertEqual(O.file_group("/index/en/h.json"), "en-h")
        self.assertEqual(O.file_group("/index/en/misc.json"), "en-misc")
        self.assertEqual(O.file_group("/index/en/tails/o-o.json"), "en-tails-o")
        self.assertEqual(O.file_group("/index/en/tails/misc-misc.json"), "en-tails-misc")
        self.assertEqual(O.file_group("/index/tails/o-o.json"), "tails-o")
        self.assertEqual(O.file_group("/index/h.json"), "index-h")

    def test_the_words(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["search.english"], "Search English words")
        self.assertEqual(s["search.placeholderEn"], "Search an English word")
        self.assertEqual(s["search.labelEn"], "Search an English word")
        self.assertEqual(s["results.similarEn"], "Similar English words")
        self.assertEqual(s["results.noneEn"], "“{q}” is not among our English equivalents yet.")
        self.assertEqual(s["results.noneEnWhy"],
                         "The English search looks through the English equivalents of the {n} articles "
                         "that have them so far, {p} % of the dictionary. A word missing here may still have a "
                         "Norwegian equivalent.")

    def test_the_switch_is_drawn_by_script(self):
        js = _read(SITE, "shell.js")
        self.assertIn("function addSwitch(inner) {", js)
        self.assertIn("cb.setAttribute('role', 'switch');", js)
        chrome = _read(ORDPAR, "sitegen", "chrome.py")
        self.assertNotIn("ordpar-direction", chrome)        # not written into the pages
        self.assertIn('lang="nb"', chrome)

    def test_random_word_stays_english(self):
        # site decisions 155 (Robin, 2026-10-31) amends 148 item 11: with the switch on, Random
        # word draws an English word and the box stays English (`test_ordpar_random155.py`)
        js = _read(SITE, "lookup.js")
        self.assertNotIn("if (S && S.setDirection) { S.setDirection('nb'); }", js)
        self.assertIn("(en ? randomEnglish() : randomHeadword())", js)


if __name__ == "__main__":
    unittest.main()
