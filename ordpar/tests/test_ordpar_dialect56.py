# -*- coding: utf-8 -*-
"""Pins decisions 56 in the lookup index (`ordpar/build_index.py`, `ordpar/site/lookup.js`; Robin
2026-10-19): dialect spellings, chained rewrites, and a hit's suggestions built as a miss's.

* Two spelling rules: word-final *æ ↔ eg* (dæ -> deg, mæ -> meg, sæ -> seg, jæ -> jeg) and
  *æ ↔ e* anywhere in a word but its end (kæm -> kem); a word-final æ is never made a plain e.
* Two rules chain (kæm -> kem -> hvem), never three; the second never rewrites what the first
  wrote (no k -> hv -> v, no undo); single rewrites come before chained ones; at most
  `MAX_REWRITES`.
* A chained rewrite costs as a single one: free only where it lands exactly, otherwise 1 + its
  distance, within the query's own limit.
* A hit's similar list is the miss's: `similar(q)` widens by default (past the first letter,
  `tails/`, the rules), a query never lists itself — *kor* (a hit) offers *hvor* — and the page
  calls `similar` without `wide`, after the results are painted.
* `bag_distance`, the prefilter, is a lower bound of `osa` (it never changes an answer).
* When `bun` (or `node`) is on PATH, `lookup.js` gives the same rewrites, bag distances and
  answers as the Python twin over the same synthetic index.

Synthetic rows and a synthetic frequency file only: no mirror, no library, no real list."""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))
sys.path.insert(0, ROOT)

import build_index as B  # noqa: E402

LOOKUP_JS = os.path.join(ROOT, "ordpar", "site", "lookup.js")


def _row(aid, lemma, pos="NOUN", forms=()):
    return {"id": aid, "data": {"lemmas": [{
        "lemma": lemma, "hgno": 0,
        "paradigm_info": [{"tags": [pos],
                           "inflection": [{"word_form": f} for f in [lemma] + list(forms)]}]}]}}


ROWS = [
    _row(1, "deg", "PRON"), _row(2, "meg", "PRON"), _row(3, "seg", "PRON"),
    _row(4, "jeg", "PRON"), _row(5, "de", "PRON"), _row(6, "hvem", "PRON"),
    _row(7, "kor", forms=["koret", "kor", "kora", "korene"]),   # choir: a hit
    _row(8, "hvor", "ADV"), _row(9, "kort"), _row(10, "kam"), _row(11, "kim"),
    _row(12, "bor", "VERB"), _row(13, "hus", forms=["huset"]), _row(14, "bus"),
    _row(15, "dus"), _row(16, "hvordan", "ADV"), _row(17, "vordan"),
    _row(18, "hvemm"),            # one edit from the chained rewrite of kæmm (see below)
    _row(19, "eple"), _row(20, "kæm"),
]

FREQ = {"deg": 900000, "meg": 900000, "seg": 900000, "jeg": 3000000, "de": 2000000,
        "hvem": 300000, "kor": 4000, "hvor": 800000, "kort": 90000, "kam": 3000, "kim": 500,
        "bor": 70000, "hus": 160000, "bus": 98, "dus": 1199, "hvordan": 545000, "eple": 9000}


class TestRules(unittest.TestCase):
    def test_new_rules(self):
        for q, want in (("dæ", "deg"), ("mæ", "meg"), ("sæ", "seg"), ("jæ", "jeg"),
                        ("deg", "dæ"), ("kæm", "kem"), ("kem", "kæm"), ("ta dæ", "ta deg"),
                        ("æple", "eple")):
            self.assertIn(want, B.rewrites(q), q)
        self.assertNotIn("de", B.rewrites("dæ"))           # a word-final æ is æ ↔ eg's, not e's
        self.assertNotIn("kæ", B.rewrites("ke"))
        self.assertIn("kæm ta", B.rewrites("kem ta"))
        self.assertNotIn("ta dæ", B.rewrites("ta de"))       # the end of any word is an end

    def test_chaining(self):
        r = B.rewrites("kæm")
        self.assertIn("hvem", r)                             # k -> hv, then æ -> e
        singles = list(dict.fromkeys(x for x, _ in B._rewrite_once("kæm")))
        self.assertEqual(r[:len(singles)], singles)          # single rewrites first
        self.assertLess(r.index("kem"), r.index("hvem"))
        self.assertNotIn("hvem", B.rewrites("kæmm"))         # three rules: never
        self.assertIn("hvemm", B.rewrites("kæmm"))           # two of them: yes
        # the second rule never rewrites what the first one wrote
        self.assertNotIn("vordan", B.rewrites("kordan"))     # k -> hv -> v would be k -> v
        self.assertNotIn("kordan", B.rewrites("kordan"))     # an undo is the query itself
        self.assertNotIn("dæg", B.rewrites("dæ"))            # æ -> eg, then e -> æ over it
        for w in ("representere", "bestemmelsene", "arbeidsmiljøloven", "elementene" * 3):
            r = B.rewrites(w)
            self.assertLessEqual(len(r), B.MAX_REWRITES)
            self.assertEqual(len(r), len(set(r)))
            self.assertNotIn(w, r)

    def test_bag_distance_is_a_lower_bound(self):
        rng = random.Random(56)
        alphabet = "aeiknorsæ "
        for _ in range(3000):
            a = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9)))
            b = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9)))
            bag = B.bag_distance(B.char_counts(a), len(a), b)
            self.assertLessEqual(bag, B.osa(a, b, 99), (a, b))
            self.assertEqual(bag, B.bag_distance(B.char_counts(b), len(b), a), (a, b))
            # the triangle the rewrite prefilter relies on: bag(r, w) >= bag(q, w) - bag(q, r)
            c = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9)))
            bag_ac = B.bag_distance(B.char_counts(a), len(a), c)
            bag_bc = B.bag_distance(B.char_counts(b), len(b), c)
            self.assertGreaterEqual(bag_bc, bag_ac - bag, (a, b, c))
        self.assertEqual(B.bag_distance(B.char_counts("kæm"), 3, "hvem"), 3)
        self.assertEqual(B.bag_distance(B.char_counts("ab"), 2, "ba"), 0)


class TestSynthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx56-")
        freq_path = os.path.join(cls.tmp, "1gram.frk")
        with open(freq_path, "w", encoding="latin-1", errors="replace") as fh:
            for w, n in FREQ.items():
                fh.write("%8d %s\n" % (n, w))
        entries = [B.entry(r["id"], r["data"]) for r in ROWS]
        stats = {}
        heads, forms, words = B.build_tables(entries, None, stats)
        freq = B.article_freq(entries, freq_path, stats)
        B.write_index(cls.tmp, heads, forms, words, [1], stats, freq)
        cls.dir = os.path.join(cls.tmp, "index")
        cls.idx = B.Index(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def sim(self, q, **kw):
        return [(s["word"], s["dist"]) for s in self.idx.similar(q, **kw)]

    def test_dialect_queries(self):
        for q, want in (("dæ", "deg"), ("mæ", "meg"), ("sæ", "seg"), ("jæ", "jeg")):
            self.assertEqual(self.sim(q)[0], (want, 0), q)
        self.assertIn(("de", 1), self.sim("dæ"))             # still one edit, not free
        self.assertEqual(self.sim("æple")[0], ("eple", 0))

    def test_chained_cost(self):
        # kæm is a headword here (a hit), so its chained rewrite hvem lands at 0 under a hit
        self.assertEqual(self.sim("kæm")[0], ("hvem", 0))
        self.assertNotIn("kæm", [w for w, _ in self.sim("kæm")])   # never itself
        # kæmm: hvemm (two rules) lands exactly; hvem is three rules away, and one edit from
        # the chained rewrite hvemm costs 1 + 1 = 2, past kæmm's limit of 1
        got = self.sim("kæmm")
        self.assertIn(("hvemm", 0), got)
        self.assertNotIn("hvem", [w for w, _ in got])

    def test_hit_as_miss(self):
        self.assertTrue(self.idx.lookup("kor")["heads"])          # kor is a hit (choir)
        self.assertEqual(self.sim("kor")[0], ("hvor", 0))         # k -> hv, as on a miss
        self.assertNotIn("kor", [w for w, _ in self.sim("kor")])
        self.assertEqual(self.sim("kor"), self.sim("kor", wide=True))   # the default is wide
        self.assertNotIn("hvor", [w for w, _ in self.sim("kor", wide=False)])
        # a hit reaches past its first letter too: hus -> bus, dus (tails/u-s)
        self.assertTrue({"bus", "dus"} <= {w for w, _ in self.sim("hus")})
        self.assertEqual(self.sim("hus", wide=False), [])
        # the description of a hit and a miss use the same list
        self.assertIn("hvor(0)", B.describe(self.idx, "kor"))

    def test_page_calls_similar_unwidened_after_the_results(self):
        with open(LOOKUP_JS, encoding="utf-8") as fh:
            src = fh.read()
        render = src[src.index("function render(root, query"):]   # (root, query, opts) since decisions 60
        render = render[:render.index("function wireRandom")]
        # since site decisions 149 the pass is asked for more on a page that shows articles
        # (`SIMILAR_POOL`, then `dropRepeats`), beside the full view's articles — still unwidened
        self.assertIn("return Promise.all([similar(g.query, showing ? SIMILAR_POOL : null), whole]).then(", render)
        self.assertNotIn("!res.count)", render.split("similar(g.query")[1][:40])
        # the hit list is appended before similar is called
        self.assertLess(render.index("results.appendChild(spaced(sec))"), render.index("similar(g.query"))
        self.assertIn("wide = wide !== false;", src)

    def test_js_matches_python(self):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        queries = ["dæ", "mæ", "sæ", "jæ", "kæm", "kæmm", "kor", "hus", "æple", "kordan",
                   "de", "ta dæ", "kem", "vus", "hvem"]
        words = ["kæm", "kæmm", "dæ", "deg", "kordan", "ta dæ", "kem ta", "æple",
                 "representere", "bestemmelsene", "arbeidsmiljøloven", "elementene" * 3,
                 "paaaa", "sjære", "aeoeaa"]
        pairs = [["kæm", "hvem"], ["ab", "ba"], ["representere", "ræpresentere"], ["", "x"],
                 ["elementene", "lmntn"]]
        script = os.path.join(self.tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""
const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const dir = %s;
L.setLoader(n => { const p = path.join(dir, n); return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
(async () => { const out = {sim: {}, rw: {}};
  for (const q of %s) { await L.lookup(q);
    out.sim[q] = [(await L.similar(q)).map(s => [s.word, s.dist]),
                  (await L.similar(q, null, false)).map(s => [s.word, s.dist])]; }
  for (const w of %s) { out.rw[w] = L.rewrites(w); }
  out.bag = %s.map(p => L.bagDistance(L.charCounts(p[0]), p[0].length, p[1]));
  process.stdout.write(JSON.stringify(out)); })();
""" % (json.dumps(LOOKUP_JS), json.dumps(self.dir), json.dumps(queries, ensure_ascii=False),
                json.dumps(words, ensure_ascii=False), json.dumps(pairs, ensure_ascii=False)))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        js = json.loads(res.stdout.decode("utf-8"))
        for q in queries:
            self.assertEqual(js["sim"][q], [[list(x) for x in self.sim(q)],
                                            [list(x) for x in self.sim(q, wide=False)]], q)
        for w in words:
            self.assertEqual(js["rw"][w], B.rewrites(w), w)
        self.assertEqual(js["bag"], [B.bag_distance(B.char_counts(a), len(a), b) for a, b in pairs])


if __name__ == "__main__":
    unittest.main()
