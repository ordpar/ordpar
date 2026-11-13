#!/usr/bin/env python3
"""Site decisions 155 (Robin, 2026-10-31): Random word in English when "Search English words" is on.

Robin: "when "Search English words" is switched on, it chooses a random English word (instead of a
Norwegian one)"; the pool his pick, "Yes, every word" — every English word the English suggestions
can offer, each equally likely, opened exactly as if typed and picked. Pinned here (the click in a
browser: `test_ordpar_browser_random155.py`):

* **the pool** (`build_index.english_pool`, `english_random`; `lookup.js` `enPool`) — every key of
  the English index, once, under its own file's letter; a phrase a file carries for another
  letter's sake (*go swimming* in `s`) counted in `g` only; a key the suggestions can never offer
  left out (one whose display, typed, does not reach it: *the point*, from "to the point", whose
  "the" the search drops); `random-en.json` holds the counts alone;
* **the draw** (`lookup.js` `randomEnglish`, under bun) — with `Math.random` stubbed to each of
  the total's slots in turn, every pool word comes out exactly once (every word reachable, each
  equally likely), as displayed ("AIDS"), never a word outside the pool; a file whose words no
  longer match its count is drawn from uniformly as it is; no `random-en.json`, no draw;
* **over the build** (skipped without `ordpar/out/index/random-en.json`, or pointed at another
  index by `ORDPAR_TEST_INDEX`): the counts the Python wrote equal the words `enPool` takes from
  each file; every pool word is offered by the suggestions when typed and finds its articles;
* **the click** — `wireRandom` draws English with the switch on (`ordparShell.direction`) and
  opens it as an English search marked a draw (`{random: true, en: true}`, `#en=<word>&random`
  from another page, `takeDrawn`), no longer sending the box back to Norwegian (148 item 11,
  amended); the search page keeps a drawn English search English and unrecorded;
* **the offline copy** — `random-en.json` in the `index-meta` pack, as `random.json`.

Fails on the code before 155 (no `english_random`, no `randomEnglish`). Stdlib unittest; the
JavaScript runs under bun (or node), skipped when neither is on PATH.
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
INDEX = os.environ.get("ORDPAR_TEST_INDEX") or os.path.join(ORDPAR, "out", "index")
sys.path.insert(0, ROOT)

from ordpar import build_index as B  # noqa: E402
from ordpar import build_offline as O  # noqa: E402

RUNNER = shutil.which("bun") or shutil.which("node")
BUILT = os.path.exists(os.path.join(INDEX, "random-en.json"))


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _js(body, index):
    """Run `body` under bun with lookup.js loaded, its loader reading `index`; -> the JSON printed."""
    if not RUNNER:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run155.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const IDX = %s;
L.setLoader(name => { const p = path.join(IDX, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
const out = x => process.stdout.write(JSON.stringify(x));
(async () => { %s })().catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
""" % (json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(index), body))
        res = subprocess.run([RUNNER, script], capture_output=True, timeout=300)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _library():
    return {
        1: {"en": ["to go, to travel"]},
        2: {"en": ["to walk", "to go"]},
        3: {"en": ["to go swimming"]},          # a phrase, also carried in s's file
        4: {"en": ["to swim"]},
        5: {"en": ["to the point"]},            # its key "the point": never offered
        6: {"en": ["house", "AIDS"]},           # "AIDS": displayed in capitals
        7: {"en": ["went"]},                    # an irregular form, filed under w
        8: {"en": ["2nd"]},                     # misc
    }


WORDS = {1: ["dra", 0, "VERB"], 2: ["gå", 0, "VERB"], 3: ["bade", 0, "VERB"], 4: ["svømme", 0, "VERB"],
         5: ["presis", 0, "ADJ"], 6: ["hus", 0, "NOUN"], 7: ["dro", 0, "VERB"], 8: ["annen", 0, "ADJ"]}
BANDS = {"dra": 11, "gå": 12, "bade": 8, "svømme": 9, "presis": 9, "hus": 11, "dro": 5, "annen": 10}


class ThePool(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.idx = B.english_index(_library(), WORDS, BANDS, list(WORDS))
        cls.tmp = tempfile.mkdtemp()
        for L, sh in B.english_files(cls.idx, 100).items():
            p = os.path.join(cls.tmp, "en", L + ".json")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(B.dump(sh))
        cls.rnd = B.english_random(cls.idx)
        with open(os.path.join(cls.tmp, "random-en.json"), "wb") as fh:
            fh.write(B.dump(cls.rnd))
        cls.pool = sorted(k for ks in B.english_pool(cls.idx).values() for k in ks)
        cls.shown = sorted(cls.idx["d"].get(k, k) for k in cls.pool)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_every_offered_key_once(self):
        self.assertIn("the point", self.idx["k"])
        self.assertEqual(self.pool, sorted(k for k in self.idx["k"] if k != "the point"))
        self.assertEqual(B.english_pool(self.idx)["g"], ["go", "go swimming"])
        self.assertNotIn("go swimming", B.english_pool(self.idx).get("s", []))
        self.assertEqual(B.english_pool(self.idx)["misc"], ["2nd"])

    def test_b_the_file_holds_the_counts_alone(self):
        self.assertEqual(set(self.rnd), {"v", "n"})
        self.assertEqual(sum(self.rnd["n"].values()), len(self.pool))
        self.assertEqual(self.rnd["n"]["t"], 1)               # "travel"; not "the point"

    def test_c_the_draw_is_uniform_and_reaches_every_word(self):
        n = len(self.pool)
        got = _js("""const N = %d, words = [];
for (let i = 0; i < N; i++) { Math.random = () => (i + 0.5) / N; words.push(await L.randomEnglish()); }
out(words);""" % n, self.tmp)
        self.assertEqual(sorted(got), self.shown)            # each word exactly once
        self.assertIn("AIDS", got)
        self.assertNotIn("the point", got)

    def test_d_the_js_pool_is_the_python_pool(self):
        got = _js("""const counts = JSON.parse(fs.readFileSync(path.join(IDX, 'random-en.json'), 'utf8')).n, r = {};
for (const letter of Object.keys(counts)) { r[letter] = L.enPool(await L.loadEnglish(letter), letter); }
out(r);""", self.tmp)
        self.assertEqual(got, B.english_pool(self.idx))

    def test_e_a_file_out_of_step_with_its_count(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(self.tmp, "en"), os.path.join(tmp, "en"))
            with open(os.path.join(tmp, "random-en.json"), "w", encoding="utf-8") as fh:
                json.dump({"v": 1, "n": {"h": 99}}, fh)             # h's file holds 1 word, not 99
            got = _js("""Math.random = () => 0.999; out(await L.randomEnglish());""", tmp)
            self.assertEqual(got, "house")
            os.remove(os.path.join(tmp, "random-en.json"))
            self.assertIsNone(_js("out(await L.randomEnglish());", tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(BUILT, "no random-en.json in %s (build the index first)" % INDEX)
class OverTheBuild(unittest.TestCase):
    def test_counts_match_the_files_and_every_word_opens(self):
        got = _js("""const counts = JSON.parse(require('fs').readFileSync(require('path').join(IDX, 'random-en.json'), 'utf8')).n;
const r = { mismatch: [], notOffered: [], noMatch: [], total: 0 };
for (const letter of Object.keys(counts)) {
  const shard = await L.loadEnglish(letter), pool = L.enPool(shard, letter);
  if (pool.length !== counts[letter]) r.mismatch.push([letter, pool.length, counts[letter]]);
  for (const k of pool) {
    r.total++;
    const w = (shard.d && shard.d[k]) || k;
    const s = await L.englishSuggest(w);
    if (!s.some(x => x.key === k)) r.notOffered.push(w);
    const m = await L.englishLookup(w);
    if (!m.count) r.noMatch.push(w);
  }
}
out(r);""", INDEX)
        self.assertEqual(got["mismatch"], [])
        self.assertEqual(got["notOffered"], [])
        self.assertEqual(got["noMatch"], [])
        self.assertGreater(got["total"], 10000)


class TheClick(unittest.TestCase):
    def test_wire_random(self):
        js = _read(SITE, "lookup.js")
        # site decisions 152: Norwegian while Norwegian only hides the English equivalents (since
        # site decisions 180 read in `randomEnglishOn`, shared by the click and the draw ahead)
        self.assertIn("return !!(S && S.direction && S.direction() === 'en') && "
                      "!(S.equivHidden && S.equivHidden());", js)
        self.assertIn("var en = randomEnglishOn();", js)
        self.assertIn("(en ? randomEnglish() : randomHeadword())", js)
        self.assertIn("S.search(w, { random: true, en: true })", js)
        self.assertIn("global.location.href = englishUrl(w) + DRAWN_MARK;", js)
        self.assertNotIn("S.setDirection('nb');", js)             # 148 item 11, amended

    def test_drawn_english_stays_english_and_unrecorded(self):
        js = _read(SITE, "lookup.js")
        self.assertIn("var drawn = !!(how && how.random), en = !!(how && how.en), mine = ++seq;", js)
        self.assertIn("en ? { q: q, random: true, en: true } : { q: q, random: true }", js)
        html = _read(SITE, "search.html")
        self.assertIn("    en = !!en;\n", html)
        self.assertIn("var drawnEn = ordparSearch.takeDrawn();", html)
        self.assertIn("run(english, false, !drawnEn && !ordparSearch.cameByHistory(), drawnEn, true);", html)

    def test_take_drawn_reads_an_english_mark(self):
        if not RUNNER:
            self.skipTest("no bun/node on PATH")
        got = _js("""const S = require(%s).ordparSearch;
let state = null; let url = null;
globalThis.location = { hash: '#en=go%%20swimming&random', pathname: '/bm-en/', search: '' };
globalThis.history = { state: null, replaceState: (s, t, u) => { state = s; url = u; } };
const drawn = S.takeDrawn();
out({ drawn, state, url });""" % json.dumps(os.path.join(SITE, "lookup.js")), INDEX)
        self.assertEqual(got, {"drawn": True, "state": {"q": "go swimming", "random": True, "en": True},
                               "url": "/bm-en/#en=go%20swimming"})


class TheOfflineCopy(unittest.TestCase):
    def test_in_the_meta_pack(self):
        self.assertEqual(O.file_group("/index/random-en.json"), "index-meta")
        self.assertEqual(O.file_group("/index/random.json"), "index-meta")


if __name__ == "__main__":
    unittest.main()
