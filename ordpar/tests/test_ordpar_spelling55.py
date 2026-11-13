# -*- coding: utf-8 -*-
"""Pins decisions 55 in the lookup index (`ordpar/build_index.py`, `ordpar/site/lookup.js`; Robin
2026-10-18/19): spelling suggestions past the first letter, common words first.

* (C) The spelling-variation rules (`rewrites`): hv ↔ k/v word-initially, kj ↔ sj ↔ skj (never
  the `kj` inside `skj`), tj ↔ kj, gj ↔ hj ↔ j, the keyboard rules aa/ae/oe (-a ↔ -en dropped 2026-10-19), the
  loanword respellings, single ↔ double consonants; never the query itself, at most
  `MAX_REWRITES`.
* (A) Frequency: `band` (0 unseen, log scale, at most 15); `read_freq` folds case and sums;
  `article_freq` counts each distinct form once per article, and the shared-form switch —
  `own` (the default, Robin 2026-10-19) counts an article's own headwords plus only its unshared
  forms, `each` counts a shared form for every article; a headword string takes its highest
  article's band. The similar-words files carry one hex band per form (`{"w", "f"}`), and the
  reader still accepts the old plain list.
* (B) `tail_key` / `remainder_key` and the `tails/` files; on a miss (`wide`) a wrong first
  letter (vus -> hus), a missing one (us -> hus) and an extra one in front (ohus -> hus) are
  reached; ``wide=False`` reads only the query's own letter (until decisions 56 what a hit got;
  since then a hit's list is a miss's, `ordpar/tests/test_ordpar_dialect56.py`, and ``wide=False`` is
  kept only to measure against).
* (D) The ranking (Robin, 2026-10-19): distance, then the higher band, then the query's first
  letter; a rule rewrite costs nothing only where it lands exactly (kordan -> hvordan at 0), a
  candidate near a rewrite costs 1 + its distance from it; a rewrite that is an inflected form
  in the query's own shard is offered.
* Capitalisation as a small distance (Robin, 2026-10-19; `case_distance`): in similar words
  right after the letter distance (us -> ut before UT, US -> UT first), in autocomplete a
  tie-break within one length (u -> u, U; U -> U, u).
* The About page credits the National Library's 2026 n-grams (Språkbanken).
* (E) The switch to NB's 2026 books alone (decisions 55, 2026-10-20): the scale (``FREQ_SCALE``,
  ``scaled_band``); a headword string's rules in order (``form_band``: the registry, a single
  character, an abbreviation between the floor and the ceiling, a sunk symbol, the scaled count);
  the overrides registry's reading and refusals (``read_overrides``) and the committed file; the
  manifest's note (``freq_note``); the fixes to ``own``: a plain spelling beside an accented
  headword (``accent_twins``), the agent noun's present form for its verb (``agent_forms``), a
  symbol spelled like a word (``symbol_shared``). Synthetic rows and counts, not NB's list.
* When `bun` (or `node`) is on PATH, `lookup.js` gives the same rewrites and the same answers as
  the Python twin over the same synthetic index.

Synthetic rows and a synthetic frequency file only: no mirror, no library, no real list."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))
sys.path.insert(0, ROOT)

import build_index as B  # noqa: E402


def _row(aid, lemma, pos="NOUN", forms=()):
    return {"id": aid, "data": {"lemmas": [{
        "lemma": lemma, "hgno": 0,
        "paradigm_info": [{"tags": [pos],
                           "inflection": [{"word_form": f} for f in [lemma] + list(forms)]}]}]}}


ROWS = [
    _row(1, "hus", forms=["huset", "hus", "husa", "husene"]),
    _row(2, "bus"),
    _row(3, "dus"),
    _row(4, "VVS", "SYM"),
    _row(5, "vis", "ADJ"),
    _row(6, "hvordan", "ADV"),
    _row(7, "koran"),
    _row(8, "hvem", "PRON"),
    _row(9, "skjære", "VERB", forms=["skjærer", "skar"]),
    _row(10, "gjerne", "ADV"),
    _row(11, "hjerne"),
    _row(12, "vennskap"),
    _row(13, "bil", forms=["bilen", "biler", "bilene"]),
    _row(14, "to", "NUM"),
    _row(15, "toe", "VERB", forms=["to", "toer", "toet"]),
    _row(16, "på", "ADP"),
    _row(17, "opus"),
    _row(18, "ut", "ADV"),
    _row(19, "tak", forms=["taket"]),
    _row(20, "kafe"),
    # capitalisation as a small distance (Robin, 2026-10-19)
    _row(21, "UT", "SYM"),
    _row(22, "av", "ADP"),
    _row(23, "AV", "SYM"),
    _row(24, "u", "INTJ"),
    _row(25, "U", "SYM"),
]

# a synthetic 1-gram file in the list's own shape: "<count> <form>", ISO-8859-1, case-sensitive
FREQ = {"hus": 160000, "Hus": 18000, "huset": 138000, "husene": 20000, "bus": 98, "dus": 1199,
        "VVS": 383, "vis": 5000, "hvordan": 545000, "koran": 50, "hvem": 300000, "to": 900000,
        "toer": 3, "toet": 2, "på": 20000000, "bil": 40000, "bilen": 30000, "opus": 40,
        "ut": 2000000, "tak": 9000, "kafe": 700}


CASE_PAIRS = [["us", "UT"], ["us", "ut"], ["US", "hus"], ["Ærlig", "ærlig"], ["1-a", "1-A"],
              ["kafé", "KAFÉ"], ["", "X"], ["ab", "AV"]]


class TestRewrites(unittest.TestCase):
    def test_rules(self):
        cases = {"kordan": "hvordan", "kem": "hvem", "vem": "hvem", "hvalp": "valp", "kvilken": "hvilken",
                 "sjære": "skjære", "kjorte": "skjorte", "forsjell": "forskjell",
                 "tjole": "kjole", "kjære": "tjære", "jerne": "gjerne", "jem": "hjem",
                 "gjul": "jul", "paa": "på", "aere": "ære", "oel": "øl",
                 "cafe": "kafe", "cigar": "sigar", "photograf": "fotograf",
                 "thema": "tema", "taxi": "taksi", "quality": "kvality", "venskap": "vennskap",
                 "takk": "tak"}
        for q, want in cases.items():
            self.assertIn(want, B.rewrites(q), q)

    def test_limits(self):
        self.assertNotIn("ssjære", B.rewrites("skjære"))      # kj inside skj is skj's
        self.assertNotIn("hvhus", B.rewrites("hus"))
        self.assertNotIn("ahvem", B.rewrites("avem"))          # hv is word-initial only
        self.assertIn("ta hvem", B.rewrites("ta vem"))          # … of any word
        self.assertNotIn("skjære", B.rewrites("skjære"))       # never the query itself
        self.assertEqual(B.rewrites("paaaa")[:1], ["påå"])      # all occurrences at once
        self.assertLessEqual(len(B.rewrites("abcdefghijklmnopqrstuvwxyz" * 2)), B.MAX_REWRITES)


class TestFrequency(unittest.TestCase):
    def test_band(self):
        self.assertEqual([B.band(n) for n in (0, 1, 100, 10000, 10 ** 6, 42 * 10 ** 6, 10 ** 12)],
                         [0, 1, 4, 8, 12, 15, 15])

    def test_freq_and_switch(self):
        tmp = tempfile.mkdtemp(prefix="freq55-")
        try:
            path = os.path.join(tmp, "1gram.frk")
            with open(path, "w", encoding="latin-1") as fh:
                for w, n in FREQ.items():
                    fh.write("%8d %s\n" % (n, w))
            counts = B.read_freq(path, {"hus", "på"})
            self.assertEqual(counts, {"hus": 178000, "på": 20000000})   # Hus + hus, filtered
            entries = [B.entry(r["id"], r["data"]) for r in ROWS]
            each = B.article_freq(entries, path, {}, "each")
            own = B.article_freq(entries, path, {})
            # hus fills several cells and counts once: hus + Hus + huset + husene
            self.assertEqual(each[1], 160000 + 18000 + 138000 + 20000)
            self.assertEqual(own[1], each[1])
            # toe's imperative "to" is the numeral's headword: each counts it, own does not
            self.assertEqual(each[15], 900000 + 3 + 2)
            self.assertEqual(own[15], 3 + 2)
            self.assertEqual(own[14], 900000)                # its own headword, as written
            with self.assertRaises(ValueError):
                B.article_freq(entries, path, {}, "sum")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSynthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx55-")
        freq_path = os.path.join(cls.tmp, "1gram.frk")
        with open(freq_path, "w", encoding="latin-1") as fh:
            for w, n in FREQ.items():
                fh.write("%8d %s\n" % (n, w))
        entries = [B.entry(r["id"], r["data"]) for r in ROWS]
        stats = {}
        heads, forms, words = B.build_tables(entries, None, stats)
        cls.freq = B.article_freq(entries, freq_path, stats)
        B.write_index(cls.tmp, heads, forms, words, [1], stats, cls.freq)
        cls.dir = os.path.join(cls.tmp, "index")
        cls.idx = B.Index(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def sim(self, q, wide=True):
        return [s["word"] for s in self.idx.similar(q, wide=wide)]

    def test_keys(self):
        self.assertEqual(B.tail_key("hus"), "u-s")
        self.assertEqual(B.tail_key("bus"), "u-s")
        self.assertEqual(B.tail_key("ål"), "l-misc")
        self.assertEqual(B.tail_key("i"), "misc-misc")
        self.assertEqual(B.tail_key("Øre"), "r-e")
        self.assertEqual(B.remainder_key("us"), B.tail_key("hus"))

    def test_files(self):
        with open(os.path.join(self.dir, "headwords", "h.json"), encoding="utf-8") as fh:
            h = json.load(fh)
        self.assertLessEqual({"w", "f"}, set(h))
        # `p`: the word pages (site decisions 117); `a`, `x`, `k`, `kc`: a similar row's data (144)
        self.assertLessEqual(set(h), {"w", "f", "p", "a", "x", "k", "kc"})
        self.assertEqual(len(h["w"]), len(h["f"]))
        self.assertEqual(h["f"][h["w"].index("hus")], B.HEX[B.band(self.freq[1])])
        with open(os.path.join(self.dir, "tails", "u-s.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["w"], ["bus", "dus", "hus"])
        # the reader still takes the old plain list (every band 0)
        os.makedirs(os.path.join(self.tmp, "old", "headwords"), exist_ok=True)
        with open(os.path.join(self.tmp, "old", "headwords", "h.json"), "w", encoding="utf-8") as fh:
            json.dump(["hus", "hvem"], fh)
        old = B.Index(os.path.join(self.tmp, "old"))
        self.assertEqual(old._similar_file("headwords", "h")[0], ("hus", "hus", "hus", 0))

    def test_first_letter(self):
        # a wrong first letter, ranked by band before the first letter (Robin, 2026-10-19):
        # hus (11) above vis, dus, bus; VVS last, its capitals two case steps from vus
        self.assertEqual(self.sim("vus"), ["hus", "vis", "dus", "bus", "VVS"])
        self.assertEqual(self.sim("vus", wide=False), ["vis", "VVS"])
        self.assertEqual(self.sim("us"), ["ut", "hus", "dus", "bus", "u"])  # a missing one
        self.assertIn("hus", self.sim("ohus"))                            # an extra one
        self.assertEqual(self.sim("ohus", wide=False), ["opus"])
        # wide=False (a hit's list until decisions 56) reads only the query's own letter
        self.assertEqual(self.sim("hus", wide=False), [])
        self.assertEqual(self.sim("bus", wide=False), [])

    def test_case_distance(self):
        # capitalisation as a small distance, after the letter distance (Robin, 2026-10-19)
        self.assertEqual([B.case_distance("us", w) for w in ("UT", "ut", "AS", "As", "hus")],
                         [2, 0, 2, 1, 0])
        self.assertEqual(B.case_distance("US", "UT"), 0)
        self.assertEqual(B.case_distance("1-a", "1-A"), 1)      # only cased characters count
        self.assertEqual(self.sim("us")[0], "ut")
        self.assertEqual(self.sim("US")[:2], ["UT", "U"])
        self.assertEqual(self.sim("ab"), ["av", "AV"])
        self.assertEqual(self.sim("AB"), ["AV", "av"])
        # autocomplete: a tie-break within one length (u before U; U before u when capital)
        self.assertEqual([s["word"] for s in self.idx.suggest("u")], ["u", "U", "ut", "UT"])
        self.assertEqual([s["word"] for s in self.idx.suggest("U")], ["U", "u", "UT", "ut"])
        self.assertEqual([s["word"] for s in self.idx.suggest("A")], ["AV", "av"])

    def test_rules_cost_nothing(self):
        for q, want in (("kordan", "hvordan"), ("kem", "hvem"), ("vem", "hvem"),
                        ("sjære", "skjære"), ("jerne", "gjerne"), ("venskap", "vennskap"),
                        ("paa", "på")):
            res = self.idx.similar(q, wide=True)
            self.assertEqual((res[0]["word"], res[0]["dist"]), (want, 0), q)
        self.assertEqual(self.sim("kordan")[:2], ["hvordan", "koran"])
        # jerne reaches both gjerne and hjerne at 0; the more common first
        self.assertEqual(self.sim("jerne")[:2], ["gjerne", "hjerne"])
        # a rewrite is free only where it lands exactly (Robin, 2026-10-19): sjæra -> skjæra is
        # one edit from skjære, so skjære costs 2, past sjæra's limit of 1
        self.assertNotIn("skjære", self.sim("sjæra"))
        self.assertEqual(self.idx.similar("sjære", wide=True)[0]["dist"], 0)
        # the -a <-> -en rule is gone (Robin, 2026-10-19: suggestions are lemmatized headwords):
        # bila no longer offers bilen, and en (a hit) no longer offers a, à, A at 0
        self.assertNotIn("bilen", B.rewrites("bila"))
        self.assertNotIn("a", B.rewrites("en"))
        self.assertTrue(all(d > 0 for w, d in
                            [(s["word"], s["dist"]) for s in self.idx.similar("en")]
                            if w.lower() in ("a", "à")))

    def test_about_credit(self):
        from ordpar.sitegen import page, strings
        html = page.about_page("stamp", strings.EN, page.about_mod.SAMPLE)
        self.assertIn('Språkbanken</a>, National Library of Norway (<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>)', html)
        self.assertIn("N-grams from the National Library of Norway 2026, <a", html)

    def test_js_matches_python(self):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        queries = ["vus", "us", "US", "Us", "ab", "AB", "u", "U", "A", "ohus", "hus", "kordan", "kem", "vem", "sjære", "jerne",
                   "venskap", "paa", "bila", "takk", "kafe", "cafe", "toe", "to", "xyzzy",
                   "h", "u", "ta vem"]
        words = ["kordan", "skjære", "forsjell", "paaaa", "ta vem", "bila", "kuen", "taxi",
                 "quality", "vennskap", "abcdefghijklmnopqrstuvwxyz"]
        script = os.path.join(self.tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""
const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const dir = %s;
L.setLoader(n => { const p = path.join(dir, n); return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
(async () => { const out = {sim: {}, rw: {}};
  for (const q of %s) { const r = await L.lookup(q);
    out.sim[q] = [(await L.similar(q, null, true)).map(s => [s.word, s.dist]),
                  (await L.similar(q)).map(s => [s.word, s.dist]),
                  (await L.suggest(q)).map(s => s.word)]; }
  out.cd = %s.map(p => L.caseDistance(p[0], p[1]));
  for (const w of %s) { out.rw[w] = L.rewrites(w); }
  process.stdout.write(JSON.stringify(out)); })();
""" % (json.dumps(os.path.join(ROOT, "ordpar", "site", "lookup.js")), json.dumps(self.dir),
                json.dumps(queries, ensure_ascii=False), json.dumps(CASE_PAIRS, ensure_ascii=False),
                json.dumps(words, ensure_ascii=False)))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        js = json.loads(res.stdout.decode("utf-8"))
        for q in queries:
            py = [[[s["word"], s["dist"]] for s in self.idx.similar(q, wide=True)],
                  [[s["word"], s["dist"]] for s in self.idx.similar(q)],
                  [s["word"] for s in self.idx.suggest(q)]]
            self.assertEqual(js["sim"][q], py, q)
        for w in words:
            self.assertEqual(js["rw"][w], B.rewrites(w), w)
        self.assertEqual(js["cd"], [B.case_distance(a, b) for a, b in CASE_PAIRS])
        # the rule tables themselves are the same
        with open(os.path.join(ROOT, "ordpar", "site", "lookup.js"), encoding="utf-8") as fh:
            src = fh.read()
        for frm, to, where, na in B.RULES:
            self.assertIn("['%s', '%s', '%s', '%s']" % (frm, to, where, na), src)
        self.assertIn("var DOUBLING = '%s';" % "".join(sorted(B.DOUBLING)), src)
        self.assertIn("var MAX_REWRITES = %d;" % B.MAX_REWRITES, src)



def _para(pos, cells, extra=()):
    return {"tags": [pos] + list(extra),
            "inflection": [{"tags": list(t), "word_form": w} for t, w in cells]}


def _arow(aid, lemmas, paras):
    """A mirror row with several lemmas (``lemmas``: spellings) and full paradigms."""
    ls = [{"lemma": w, "hgno": 0, "paradigm_info": paras if i == 0 else []}
          for i, w in enumerate(lemmas)]
    return {"id": aid, "data": {"lemmas": ls}}


# decisions 55's switch (2026-10-20): the mapping artefacts and the symbol rule, synthetic
NB_ROWS = [
    # 3.1: fôr lists the plain spelling for, the preposition's headword
    _arow(101, ["fôr", "for"], [_para("NOUN", [(("Sing", "Ind"), "fôr"), (("Sing", "Def"), "fôret")],
                                      ("Neuter",))]),
    _arow(102, ["for"], [_para("ADP", [((), "for")])]),
    # 3.1: homographs sharing both spellings keep them (provençalsk noun and adjective)
    _arow(103, ["provencalsk", "provençalsk"], [_para("NOUN", [(("Sing", "Ind"), "provencalsk")],
                                                      ("Masc",))]),
    _arow(104, ["provencalsk", "provençalsk"], [_para("ADJ", [((), "provencalsk")])]),
    # 3.2: the agent noun and its verb; the guard keeps sukker (a neuter) off sukke
    _arow(105, ["skrive"], [_para("VERB", [(("Inf",), "skrive"), (("Pres",), "skriver"),
                                           (("Pres", "Pass"), "skrives"), (("Past",), "skrev")])]),
    _arow(106, ["skriver"], [_para("NOUN", [(("Sing", "Ind"), "skriver"), (("Sing", "Def"), "skriveren"),
                                            (("Plur", "Ind"), "skrivere")], ("Masc",))]),
    _arow(107, ["sukke"], [_para("VERB", [(("Inf",), "sukke"), (("Pres",), "sukker")])]),
    _arow(108, ["sukker"], [_para("NOUN", [(("Sing", "Ind"), "sukker"), (("Plur", "Ind"), "sukkere")],
                                  ("Neuter",))]),
    # 3.3: a symbol spelled like a word sinks; one that shares only a capitalised noun does not
    _arow(109, ["Og"], [_para("SYM", [((), "Og")])]),
    _arow(110, ["og"], [_para("CCONJ", [((), "og")])]),
    _arow(111, ["km"], [_para("SYM", [((), "km")])]),
    _arow(112, ["KM"], [_para("NOUN", [(("Sing", "Ind"), "KM"), (("Sing", "Def"), "KM-et")], ("Neuter",))]),
]
NB_FREQ = {"fôr": 4000, "fôret": 1000, "for": 16_000_000, "provencalsk": 300, "provençalsk": 200,
           "skrive": 100_000, "skriver": 460_000, "skrev": 90_000, "skrives": 20_000,
           "skriveren": 3_000, "skrivere": 2_000, "sukke": 500, "sukker": 50_000, "sukkere": 10,
           "og": 30_000_000, "km": 80_000}

REGISTRY = ("# a comment\nform\tband\twhy\nå\tnb\ta word\n\n# another\nkr\t8\tcurrency\n")


class TestNBSwitch(unittest.TestCase):
    """Decisions 55's switch to NB's 2026 books (2026-10-20): the scale, the rules for a headword
    string, the overrides registry, and the three fixes to the ``own`` rule."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="nb55-")
        cls.freq_path = os.path.join(cls.tmp, "nb.frk")
        with open(cls.freq_path, "w", encoding="latin-1") as fh:
            for w, n in NB_FREQ.items():
                fh.write("%d %s\n" % (n, w))
        cls.entries = [B.entry(r["id"], r["data"]) for r in NB_ROWS]
        cls.facts = {r["id"]: B.article_facts(r["data"]) for r in NB_ROWS}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def freq(self, fixes=B.FREQ_FIXES):
        return B.article_freq(self.entries, self.freq_path, {}, facts=self.facts, fixes=fixes)

    def test_scale(self):
        self.assertAlmostEqual(B.FREQ_SCALE, 18_873_584_692 / 1_306_199_192)
        self.assertAlmostEqual(B.FREQ_SCALE, 14.449, places=3)
        k = B.FREQ_SCALE
        self.assertEqual(B.scaled_band(0), 0)
        self.assertEqual(B.scaled_band(1), 1)                       # counted at all: band 1
        self.assertEqual(B.scaled_band(round(100 * k)), B.band(100))
        self.assertEqual(B.scaled_band(round(10 ** 6 * k)), 12)
        self.assertEqual(B.scaled_band(100, scale=1), B.band(100))

    def test_rules(self):
        k = B.FREQ_SCALE
        rules = B.freq_rules({"å": "nb", "kr": 8, "f.o.r.": 3}, symbol_ids={9}, ceiling=5)
        big, mid = round(10 ** 7 * k), round(2000 * k)              # bands 14 and 7 once scaled
        band = lambda f, n, ids=(1,): B.form_band(f, ids, n, rules)
        self.assertEqual(band("a", big), B.SINGLE_BAND)             # 1. a single character
        self.assertEqual(band("7", big), B.SINGLE_BAND)
        self.assertEqual(band("å", big), 14)                        # ... unless the registry spares it
        self.assertEqual(band("fl.", big), 5)                       # 2. an abbreviation, at the ceiling
        self.assertEqual(band("bl.a.", 0), B.ABBR_FLOOR)            # ... and the floor, uncounted
        self.assertEqual(band("f.eks.", round(5 * k)), B.ABBR_FLOOR)
        self.assertEqual(band("pr.", round(30 * k)), 3)             # ... its own count in between
        for spared in ("17. mai", "ph.d.-kandidat", "n.-rot", "o…"):
            self.assertFalse(B.is_abbr(spared), spared)
            self.assertEqual(band(spared, mid), 7, spared)
        self.assertEqual(band("kr", big), 8)                        # 3. the registry
        self.assertEqual(band("f.o.r.", big), 3)                    # ... ahead of the rules
        self.assertEqual(band("du", big), 14)                       # 4. the scaled count
        self.assertEqual(band("Og", big, ids=(9,)), 5)              # a sunk symbol: the abbreviation band
        self.assertEqual(band("Og", 0, ids=(9,)), B.ABBR_FLOOR)
        self.assertEqual(band("og", big, ids=(9, 10)), 14)          # ... not where a word shares the form
        # headword_bands applies them; without rules it keeps the raw count's band
        heads = {"a": {"a": [1], "fl.": [2]}, "o": {"og": [3]}}
        freq = {1: big, 2: big, 3: big}
        self.assertEqual(B.headword_bands(heads, freq, rules), {"a": 1, "fl.": 5, "og": 14})
        self.assertEqual(B.headword_bands(heads, freq), {f: B.band(big) for f in ("a", "fl.", "og")})

    def test_registry_reads(self):
        path = os.path.join(self.tmp, "reg.tsv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(REGISTRY)
        self.assertEqual(B.read_overrides(path), {"å": "nb", "kr": 8})
        # the committed registry: round 3's seven, word for word, and Robin's three agent-noun
        # false friends (2026-10-20)
        got = B.read_overrides(B.OVERRIDES_PATH)
        self.assertEqual(got, {"å": "nb", "i": "nb", "fl": 2, "ff": 2, "ss": 2, "kr": 8, "kg": 8,
                               "gange": 8, "helle": 8, "midle": 7})
        with open(B.OVERRIDES_PATH, encoding="utf-8") as fh:
            first = fh.readline()
        self.assertTrue(first.startswith("#"))
        self.assertIn("Robin", open(B.OVERRIDES_PATH, encoding="utf-8").read().split("form\tband")[0])
        note = B.freq_note("E:/x/nb-2026-books-nob-1990_freq.frk", "own", B.OVERRIDES_PATH, got,
                           B.freq_rules(got))
        self.assertEqual(note["freq"], "nb-2026-books-nob-1990_freq.frk")
        self.assertEqual(note["overrides"], {"file": "freq-overrides.tsv", "entries": 10})
        self.assertEqual(note["abbr_band"], [B.ABBR_FLOOR, B.ABBR_CEILING])
        self.assertEqual(B.freq_note(None, "own"), {"freq": None, "freq_shared": None})

    def test_registry_refuses(self):
        bad = {
            "form\tband\n": ":1:",                               # the header
            "form\tband\twhy\nå\tnb\n": ":2:",                    # two fields
            "form\tband\twhy\n# c\nå\t16\tx\n": ":3:",            # out of range
            "form\tband\twhy\nå\thigh\tx\n": ":2:",               # not a band
            "form\tband\twhy\nå\t3\t \n": ":2:",                  # no reason
            "form\tband\twhy\nå\t3\tx\nå\t4\ty\n": ":3:",         # listed twice
            "form\tband\twhy\n å\t3\tx\n": ":2:",                 # padded form
            "# only a comment\n": "no header",
        }
        for text, where in bad.items():
            path = os.path.join(self.tmp, "bad.tsv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            with self.assertRaises(ValueError) as cm:
                B.read_overrides(path)
            self.assertIn(where, str(cm.exception), text)

    def test_accent_twin(self):
        # 3.1: fôr no longer inherits the preposition's count through its plain spelling
        self.assertEqual(B.accent_twins(self.entries), {101: {"for"}})
        before, after = self.freq(()), self.freq(("accent",))
        self.assertEqual(before[101], 4000 + 1000 + 16_000_000)
        self.assertEqual(after[101], 4000 + 1000)
        self.assertEqual(after[102], 16_000_000)
        # homographs that share both spellings keep both
        self.assertEqual(after[103], before[103])
        self.assertEqual(after[103], 300 + 200)

    def test_agent_noun(self):
        # 3.2: skriver (Pres of skrive, and a masculine noun with plural skrivere) counts for the
        # verb as well; the noun keeps it; sukker (a neuter) stays off sukke
        self.assertEqual(B.agent_forms(self.entries, self.facts), {105: {"skriver"}})
        self.assertEqual(self.facts[105][1], frozenset({"skriver"}))   # no passive form
        before, after = self.freq(()), self.freq(("agent",))
        self.assertEqual(before[105], 100_000 + 20_000 + 90_000)        # skriver is the noun's
        self.assertEqual(after[105], before[105] + 460_000)
        self.assertEqual(after[106], before[106])
        self.assertEqual(after[107], before[107])
        self.assertGreater(after[105], after[106])
        # nothing without facts
        self.assertEqual(B.article_freq(self.entries, self.freq_path, {}, fixes=("agent",)), before)

    def test_symbol(self):
        # 3.3: Og shares og with the conjunction and sinks; km shares only a capitalised noun
        self.assertEqual(B.symbol_shared(self.entries, self.facts), {109: {"og"}})
        before, after = self.freq(()), self.freq(("symbol",))
        self.assertEqual(before[109], 30_000_000)
        self.assertEqual(after[109], 0)
        self.assertEqual(after[110], 30_000_000)
        self.assertEqual(after[111], before[111])
        heads, _forms, _words = B.build_tables(self.entries, None, {})
        rules = B.freq_rules({}, B.symbol_shared(self.entries, self.facts))
        bands = B.headword_bands(heads, after, rules)
        self.assertEqual(bands["Og"], B.ABBR_FLOOR)
        self.assertEqual(bands["og"], B.scaled_band(30_000_000))
        self.assertEqual(bands["km"], B.scaled_band(80_000))


if __name__ == "__main__":
    unittest.main()
