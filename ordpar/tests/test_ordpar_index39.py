# -*- coding: utf-8 -*-
"""Pins the lookup index's decisions-39 build (`ordpar/build_index.py`, `ordpar/site/lookup.js`,
Robin 2026-10-18):

* `variants()` expands ordbokene's alternation notation — `[a|b]` groups (every combination),
  a `/` inside brackets, a `|` between whole bracketed alternatives — in source order, and
  leaves a bare `/` (`km/h`) and unbalanced brackets alone.
* The key rules: `letter_key` (a-z, ae/oe/aa, misc; accented initials with their letter since 41 (a)), `shard_key` (b f k s t split by the second
  folded character: `s-k`, `s-oe`, `s-misc`), `suggest_key` (a one-character prefix on a split
  letter reads `<letter>-top`).
* A synthetic index built through `build_tables` + `write_index`: the bracket notation is never
  a key, every variant reaches the same article, the panel shows the variant that matched,
  `<letter>-top` answers a one-character prefix exactly as the whole letter would, and the
  similar pass reads only `headwords/<letter>.json`.
* The similar-words ranking (2026-10-18): the letter limit scales with the query's length
  (`letter_limit`), a multi-word query also matches word by word (`shared_words`), nonsense
  gets nothing, and an expression's sibling variants stay separate suggestions.
* The live region's singular line (`results.liveHitsOne`).
* When `bun` (or `node`) is on PATH, `lookup.js` answers the same as the Python twin over the
  same synthetic index; otherwise that test is skipped.
* The Random word's bar (decisions 67, 2026-10-20): `random_pool` keeps the translated ids that
  are not set phrases (entry `EXPR`, or a library `fixed expression`) and carry a summary gloss;
  since decisions 115 `random.json` holds the HEADWORDS whose search shows one of them first
  (`test_ordpar_random115.py` pins that rule); `translated.json` keeps every translated id;
  `library_pass` reports the gloss; `lookup.js randomHeadword` draws from `random.json` only
  (under bun/node).

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


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _row(aid, lemma, pos="NOUN", forms=()):
    return {"id": aid, "data": {"lemmas": [{
        "lemma": lemma, "hgno": 0,
        "paradigm_info": [{"tags": [pos],
                           "inflection": [{"word_form": f} for f in forms]}]}]}}


ROWS = [
    _row(1, "[få|sette] ræva i gir", "EXPR"),
    _row(2, "en [ond|vond] sirkel", "EXPR"),
    _row(3, "[i alt vesentlig] | [i det vesentlige]", "EXPR"),
    _row(4, "pipa får en annen [låt/lyd]", "EXPR"),
    _row(5, "pipa får en annen lyd", "EXPR"),
    _row(6, "km/h", "SYM"),
    _row(7, "skole", forms=["skolen", "skolene"]),
    _row(8, "sko", forms=["skoen"]),
    _row(9, "s", "SYM"),
    _row(10, "sø"),
    _row(11, "sånn", "ADJ"),
    _row(12, "fare", forms=["faren"]),
    _row(13, "hus", forms=["huset", "husene"]),
    _row(14, "[a|b] [c|d] e", "EXPR"),
    # the similar-words ranking (length-scaled limit, word by word; 2026-10-18)
    _row(15, "ta rotta på", "EXPR"),
    _row(16, "ta fatt på", "EXPR"),
    _row(17, "ta hull på", "EXPR"),
    _row(18, "tamrotte"),
    _row(19, "hos", "ADP"),
    _row(20, "hav"),
    _row(21, "fotballkamp"),
    _row(22, "fotballbane"),
    _row(23, "ta av", "EXPR"),
] + [_row(100 + i, "s" + "x" * (i % 7) + chr(97 + i % 26)) for i in range(80)]


class TestVariants(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(B.variants("[få|sette] ræva i gir"), ["få ræva i gir", "sette ræva i gir"])
        self.assertEqual(B.variants("blande seg [bort i|borti]"),
                         ["blande seg bort i", "blande seg borti"])
        self.assertEqual(B.variants("[berge|stryke|reve] seil"),
                         ["berge seil", "stryke seil", "reve seil"])
        self.assertEqual(B.variants("[a|b] [c|d] e"), ["a c e", "a d e", "b c e", "b d e"])

    def test_other_spellings(self):
        self.assertEqual(B.variants("[i alt vesentlig] | [i det vesentlige]"),
                         ["i alt vesentlig", "i det vesentlige"])
        self.assertEqual(B.variants("pipa får en annen [låt/lyd]"),
                         ["pipa får en annen låt", "pipa får en annen lyd"])

    def test_left_alone(self):
        for w in ("hus", "km/h", "ha en trumf i ermet/bakhånd", "... og ... , fru Blom",
                  "a [b|c", "a ]b|c["):
            self.assertEqual(B.variants(w), [w])


class TestKeys(unittest.TestCase):
    def test_letter_key(self):
        for w, k in (("hus", "h"), ("Skole", "s"), ("ære", "ae"), ("øl", "oe"), ("ål", "aa"),
                     ("éclair", "e"), ("-aktig", "misc"), ("1814", "misc"), ("", "misc")):
            self.assertEqual(B.letter_key(w), k, w)

    def test_shard_key(self):
        for w, k in (("hus", "h"), ("skole", "s-k"), ("Skole", "s-k"), ("sø", "s-oe"),
                     ("sånn", "s-aa"), ("s", "s-misc"), ("s-", "s-misc"), ("sé", "s-e"),
                     ("bok", "b-o"), ("fare", "f-a"), ("kjær", "k-j"), ("tog", "t-o"),
                     ("hjem", "h"), ("éclair", "e")):
            self.assertEqual(B.shard_key(w), k, w)

    def test_suggest_key(self):
        self.assertEqual(B.suggest_key("s"), "s-top")
        self.assertEqual(B.suggest_key("S"), "s-top")
        self.assertEqual(B.suggest_key("sk"), "s-k")
        self.assertEqual(B.suggest_key("h"), "h")
        self.assertEqual(B.suggest_key("é"), "e")      # accents fold (decisions 41 (a))


class TestSyntheticIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx39-")
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        stats = {}
        heads, forms, words = B.build_tables(mirror, None, stats)
        cls.stats = stats
        cls.manifest = B.write_index(cls.tmp, heads, forms, words, [1, 7], stats)
        cls.dir = os.path.join(cls.tmp, "index")
        cls.idx = B.Index(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_counts(self):
        self.assertEqual(self.stats["expanded_headwords"], 5)
        self.assertEqual(self.stats["expanded_variants"], 12)

    def test_no_bracket_key_anywhere(self):
        for root, _, files in os.walk(self.dir):
            for f in files:
                if f in ("index.json", "translated.json", "random.json"):
                    continue
                data = _load(os.path.join(root, f))
                # a similar-words file is {"w": forms, "f": bands} since decisions 55
                keys = (data if isinstance(data, list) else
                        data["w"] if "w" in data else list(data.get("heads", {})))
                self.assertFalse([k for k in keys if "[" in k or "|" in k], f)

    def test_every_variant_hits_the_same_article(self):
        for q in ("få ræva i gir", "sette ræva i gir", "Få ræva i gir"):
            r = self.idx.lookup(q)
            self.assertEqual([a["id"] for a in r["heads"][0]["articles"]], [1])
            # the panel shows the variant that matched, never the notation
            self.assertEqual(r["heads"][0]["articles"][0]["word"], B.fold(q) if q[0] == "F"
                             else q)
        r = self.idx.lookup("pipa får en annen lyd")    # a variant that is also its own article
        self.assertEqual([a["id"] for a in r["heads"][0]["articles"]], [4, 5])
        self.assertEqual({a["word"] for a in r["heads"][0]["articles"]}, {"pipa får en annen lyd"})

    def test_display_is_first_variant(self):
        s = _load(os.path.join(self.dir, "e.json"))
        self.assertEqual(s["words"]["2"], ["en ond sirkel", 0, "EXPR", 1])
        s = _load(os.path.join(self.dir, "h.json"))
        self.assertEqual(s["words"]["13"], ["hus", 0, "NOUN"])

    def test_files(self):
        names = set(os.listdir(self.dir))
        self.assertIn("s-k.json", names)
        self.assertIn("s-top.json", names)
        self.assertNotIn("s.json", names)
        self.assertNotIn("headwords.json", names)
        self.assertIn("s.json", os.listdir(os.path.join(self.dir, "headwords")))
        self.assertIn("k-o.json", os.listdir(os.path.join(self.dir, "tails")))   # sko, skole

    def test_one_char_prefix_equals_whole_letter(self):
        shards = [_load(os.path.join(self.dir, k)) for k in os.listdir(self.dir)
                  if k.startswith("s-") and k != "s-top.json"]
        pool = {f: ids for sh in shards for f, ids in sh["heads"].items()}
        bands = {f: b for sh in shards for f, b in B.shard_bands(sh).items()}
        # in the autocomplete's own order since brief 59b items 13-14 (`suggest_rank`)
        def rank(w, typed):
            return B.suggest_rank(w, typed, any(i in self.idx.translated for i in pool[w]),
                                  bands.get(w, 0))
        want = sorted(pool, key=lambda w: rank(w, "s"))[:20]
        self.assertEqual([s["word"] for s in self.idx.suggest("s")], want)
        # typed in capitals too: the -top file holds both orders' first 50 (decisions 55)
        want = sorted(pool, key=lambda w: rank(w, "S"))[:20]
        self.assertEqual([s["word"] for s in self.idx.suggest("S")], want)
        # skole is translated in this fixture, sko is not: translated first (brief 59b item 13)
        self.assertEqual([s["word"] for s in self.idx.suggest("sk")], ["skole", "sko"])

    def test_suggest_and_similar_reach_variants(self):
        self.assertEqual([s["word"] for s in self.idx.suggest("få ræ")], ["få ræva i gir"])
        self.assertEqual([s["word"] for s in self.idx.similar("få rompa i gir")], ["få ræva i gir"])
        # a sibling variant is a suggestion on a hit and on a miss, as on ordbokene
        self.assertEqual([s["word"] for s in self.idx.similar("en ond sirkel")], ["en vond sirkel"])
        self.assertEqual([s["word"] for s in self.idx.similar("en god sirkel")],
                         ["en ond sirkel", "en vond sirkel"])

    def test_similar_limit_scales_with_length(self):
        sim = lambda q: [s["word"] for s in self.idx.similar(q)]
        self.assertEqual([B.letter_limit(n) for n in (1, 3, 5, 6, 8, 9, 20)], [1, 1, 1, 2, 2, 3, 6])
        self.assertEqual(sim("hus"), ["hos"])                  # hav is 2 edits: too far for 3 letters
        self.assertEqual(sim("fotbalkapm"), ["fotballkamp"])   # 2 edits in 10 letters
        self.assertEqual(sim("fotballkamp"), ["fotballbane"])  # 3 edits in 11 letters
        self.assertEqual(sim("xyzzy"), [])                     # nonsense gets nothing

    def test_similar_word_by_word(self):
        sim = lambda q: [s["word"] for s in self.idx.similar(q)]
        # one word swapped: ta X på shares ta, på; the word matches come before tamrotte
        self.assertEqual(sim("ta musa på"), ["ta hull på", "ta fatt på", "ta rotta på"])
        # a word missing, and a typo inside a word
        self.assertEqual(sim("ta rotta"), ["ta rotta på", "tamrotte"])
        self.assertEqual(sim("ta rote på")[:1], ["ta rotta på"])
        # two words need both to match: ta av is not offered for ta xyzzy
        self.assertEqual(sim("ta xyzzy"), [])
        self.assertTrue(B.same_word("rotte", "rotta"))
        self.assertFalse(B.same_word("i", "å"))                # 1-2 letter words match exactly
        self.assertEqual(B.shared_words(["få", "rompa", "i", "gir"], ["få", "ræva", "i", "gir"]), 3)

    def test_live_region_singular(self):
        strings = _load(os.path.join(ROOT, "ordpar", "site", "strings", "en.json"))
        self.assertEqual(strings["results.liveHitsOne"], "1 article for “{q}”.")
        with open(os.path.join(ROOT, "ordpar", "site", "lookup.js"), encoding="utf-8") as fh:
            self.assertIn("res.count === 1 ? 'results.liveHitsOne'", fh.read())

    def test_js_matches_python(self):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        queries = ["få ræva i gir", "sette ræva i gir", "pipa får en annen lyd", "en vond sirkel",
                   "s", "S", "sk", "sko", "skolene", "hus", "husene", "huse", "få rompa i gir",
                   "i alt vesentlig", "a d e", "km/h", "sø", "sånn", "fa", "f", "xyz",
                   "en ond sirkel", "en god sirkel", "fotbalkapm", "fotballkamp", "ta musa på",
                   "ta rotta", "ta rote på", "ta xyzzy", "ta rotta på", "hav", "xyzzy"]
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
              (await L.similar(q)).map(s => [s.word, s.dist])]; }
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
                  [[s["word"], s["dist"]] for s in self.idx.similar(q)]]
            self.assertEqual(js[q], py, q)


class TestRandomPool(unittest.TestCase):
    """Decisions 67: Random word draws only from translated, glossed, non-set-phrase articles."""
    TRANSLATED = [1, 7, 8, 12, 13]
    LIBRARY = {1: {"pos_en": "fixed expression", "gloss": True},   # EXPR entry: out
               7: {"pos_en": "noun", "gloss": True},                # in
               8: {"pos_en": "noun", "gloss": False},               # no summary gloss: out
               12: {"pos_en": "fixed expression", "gloss": True},   # library set phrase: out
               13: {"pos_en": "noun", "gloss": True}}               # in

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx67-")
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        stats = {}
        heads, forms, words = B.build_tables(mirror, None, stats)
        cls.words = words
        cls.manifest = B.write_index(cls.tmp, heads, forms, words, cls.TRANSLATED, stats,
                                     library=cls.LIBRARY)
        cls.dir = os.path.join(cls.tmp, "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pool(self):
        self.assertEqual(B.random_pool(self.TRANSLATED, self.words, self.LIBRARY), [7, 13])
        # without a library only the set-phrase test applies
        self.assertEqual(B.random_pool(self.TRANSLATED, self.words), [7, 8, 12, 13])

    def test_files(self):
        # decisions 115: the headwords of 7 (skole) and 13 (hus), each its search's first article
        self.assertEqual(_load(os.path.join(self.dir, "random.json")), ["hus", "skole"])
        self.assertEqual(_load(os.path.join(self.dir, "translated.json")), self.TRANSLATED)
        self.assertEqual(self.manifest["random"]["file"], "random.json")
        self.assertEqual(self.manifest["random"]["count"], 2)
        self.assertEqual(self.manifest["random"]["articles"], 2)
        self.assertEqual(self.manifest["counts"]["random_pool"], 2)
        self.assertEqual(self.manifest["counts"]["random_headwords"], 2)

    def test_library_pass_gloss(self):
        lib = os.path.join(self.tmp, "lib.jsonl")
        rows = [{"id": 1, "lemmas": [], "senses": [], "pos_en": "noun", "summary": {"gloss": ["boat deck"]}},
                {"id": 2, "lemmas": [], "senses": [], "pos_en": "noun"},
                {"id": 3, "lemmas": [], "senses": [], "pos_en": "noun", "summary": {"gloss": []}}]
        with open(lib, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        _tr, lite = B.library_pass(lib)
        self.assertEqual({i: lite[i]["gloss"] for i in lite}, {1: True, 2: False, 3: False})

    def test_js_random_reads_pool(self):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        script = os.path.join(self.tmp, "rand.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""
const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const dir = %s, asked = [];
L.setLoader(n => { asked.push(n); const p = path.join(dir, n);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
(async () => { const seen = new Set();
  for (let k = 0; k < 200; k++) { seen.add(await L.randomHeadword()); }
  process.stdout.write(JSON.stringify({seen: [...seen].sort(), asked})); })();
""" % (json.dumps(os.path.join(ROOT, "ordpar", "site", "lookup.js")), json.dumps(self.dir)))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        out = json.loads(res.stdout.decode("utf-8"))
        self.assertEqual(out["seen"], ["hus", "skole"])
        self.assertEqual(out["asked"], ["random.json"])     # loaded once, never translated.json


if __name__ == "__main__":
    unittest.main()
