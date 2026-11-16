# -*- coding: utf-8 -*-
"""Pins Random word's pool as headwords (site-review decisions 115: as on ordbokene.no,
Random word opens a random headword's search, not a random article, and the first article is
enough; a stricter rule would leave out words such as "fly"):

* `random.json` holds HEADWORDS (`build_index.random_headwords`), and a headword is in it when the
  FIRST article its search shows meets decisions 67's bar (`random_pool`: translated, not a set
  phrase, a summary gloss); the other articles of that search may be untranslated or unglossed —
  *fly*-like: V (a verb, translated, glossed) first, I and II untranslated -> in;
* a headword whose first article does not meet the bar is out, even when a later homograph does —
  *akutt*-like: I translated but with no summary gloss first, II glossed -> out;
* no set phrase is ever drawn (an `EXPR` entry, glossed and translated);
* two spellings that fold to one search (*Mars*, *mars*) are one entry;
* "the first article shown" is the site's own order: `first_shown` in Python and lookup.js
  `firstShown` (the order `render` draws, `shownOrder`) agree on every headword of the synthetic
  index (under bun/node), and `randomHeadword` draws only from the file.

Synthetic rows only: no mirror and no library file are read. The browser side (the button lands
on a `#q=` search whose first article qualifies) is `test_ordpar_browser_random115.py`."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

import build_index as B  # noqa: E402


def _row(aid, lemma, hg=0, pos="NOUN"):
    return {"id": aid, "data": {"lemmas": [{"lemma": lemma, "hgno": hg,
                                            "paradigm_info": [{"tags": [pos], "inflection": []}]}]}}


ROWS = [
    # fly: I, II untranslated; III a noun, translated and glossed; V a verb, translated, glossed
    _row(1, "fly", 1), _row(2, "fly", 2), _row(3, "fly", 3), _row(5, "fly", 5, "VERB"),
    # akutt: I translated with no summary gloss (first), II translated and glossed
    _row(10, "akutt", 1, "ADJ"), _row(11, "akutt", 2, "ADJ"),
    # a set phrase, translated and glossed: never drawn
    _row(20, "alt i alt", 0, "EXPR"),
    # one article, in the bar
    _row(30, "bosted"),
    # two spellings, one search
    _row(40, "Mars", 1), _row(41, "mars", 2),
    # untranslated alone
    _row(50, "hus"),
]
TRANSLATED = [3, 5, 10, 11, 20, 30, 40, 41]
LIBRARY = {3: {"pos_en": "noun", "gloss": True}, 5: {"pos_en": "verb", "gloss": True},
           10: {"pos_en": "adjective", "gloss": False}, 11: {"pos_en": "adjective", "gloss": True},
           20: {"pos_en": "fixed expression", "gloss": True}, 30: {"pos_en": "noun", "gloss": True},
           40: {"pos_en": "noun", "gloss": True}, 41: {"pos_en": "noun", "gloss": True}}


class RandomHeadwords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="rand115-")
        mirror = os.path.join(cls.tmp, "mirror.jsonl")
        with open(mirror, "w", encoding="utf-8") as fh:
            for r in ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        stats = {}
        heads, forms, words = B.build_tables(mirror, None, stats)
        cls.heads, cls.words = heads, words
        cls.manifest = B.write_index(cls.tmp, heads, forms, words, TRANSLATED, stats, library=LIBRARY)
        cls.dir = os.path.join(cls.tmp, "index")
        cls.idx = B.Index(cls.dir)
        with open(os.path.join(cls.dir, "random.json"), encoding="utf-8") as fh:
            cls.file = json.load(fh)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_bar_is_67s(self):
        self.assertEqual(B.random_pool(TRANSLATED, self.words, LIBRARY), [3, 5, 11, 30, 40, 41])

    def test_first_shown_is_the_sites_order(self):
        # translated first, verbs first among the numbered: fly V, then III, then I, II
        self.assertEqual(B.first_shown(self.idx.lookup("fly")), 5)
        self.assertEqual(B.first_shown(self.idx.lookup("akutt")), 10)
        self.assertEqual(B.first_shown(self.idx.lookup("hus")), 50)   # untranslated alone: itself
        self.assertIsNone(B.first_shown(self.idx.lookup("finnesikke")))

    def test_first_qualifies_in_though_later_ones_do_not(self):
        self.assertIn("fly", self.file)          # I and II untranslated: still in
        self.assertIn("bosted", self.file)

    def test_first_does_not_qualify_out(self):
        self.assertNotIn("akutt", self.file)     # II qualifies, but I is shown first

    def test_no_set_phrase(self):
        self.assertNotIn("alt i alt", self.file)
        for w in self.file:
            for g in self.idx.lookup(w)["heads"]:
                for a in g["articles"]:
                    if a["id"] == B.first_shown(self.idx.lookup(w)):
                        self.assertNotEqual(self.words[a["id"]][2], "EXPR", w)

    def test_untranslated_never(self):
        self.assertNotIn("hus", self.file)

    def test_one_entry_per_search(self):
        self.assertEqual([w for w in self.file if B.fold(w) == "mars"], ["Mars"])

    def test_the_file(self):
        self.assertEqual(self.file, sorted(self.file))
        self.assertEqual(self.file, ["Mars", "bosted", "fly"])
        self.assertEqual(self.manifest["random"]["count"], 3)
        self.assertEqual(self.manifest["random"]["articles"], 6)
        self.assertTrue(all(isinstance(w, str) for w in self.file))

    def test_js_agrees(self):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        forms = sorted({f for k in self.heads for f in self.heads[k]})
        script = os.path.join(self.tmp, "first.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("""
const fs = require('fs'), path = require('path');
const L = require(%s).ordparLookup;
const dir = %s;
L.setLoader(n => { const p = path.join(dir, n);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
(async () => { const first = {};
  for (const w of %s) { first[w] = L.firstShown(await L.lookup(w)); }
  const seen = new Set(); for (let k = 0; k < 200; k++) { seen.add(await L.randomHeadword()); }
  process.stdout.write(JSON.stringify({ first, seen: [...seen].sort() })); })();
""" % (json.dumps(os.path.join(ROOT, "ordpar", "site", "lookup.js")), json.dumps(self.dir),
       json.dumps(forms, ensure_ascii=False)))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        out = json.loads(res.stdout.decode("utf-8"))
        self.assertEqual(out["first"], {w: B.first_shown(self.idx.lookup(w)) for w in forms})
        self.assertEqual(out["seen"], ["Mars", "bosted", "fly"])


if __name__ == "__main__":
    unittest.main()
