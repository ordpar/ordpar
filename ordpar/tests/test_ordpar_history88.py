# -*- coding: utf-8 -*-
"""Pins site decisions 88 (Robin, 2026-10-22; brief
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-history-glosses-88-2026-10-22.md`):
a history row — the dropdown's "Recent" rows and the /history/ page — draws its right-hand side
as the suggestions since decisions 82 do, not as "Norwegian only" or "N articles":

* **Several articles:** their homograph-numbered glosses in the results' order (the headword
  hits, translated first) — since 88's second amendment (it had mixed
  English and Norwegian, instead of the "... + N more" convention) the TRANSLATED
  ones only, as the suggestions list them; an untranslated article, and one with no text at
  all, counted in "+ N more"; none translated: since site decisions 144 each homograph's
  Norwegian definition (until then "N articles"); none to list: "N articles". (Until then an untranslated article
  was listed with its Norwegian definition; those pins moved 2026-10-22.) **Only the articles whose own headword the search
  matched** (88 as amended, Robin 2026-10-22): the inflected-form rows are not listed, and the
  first build's bold headword before them is gone; an entry stored for a search that found only
  inflected forms draws as stored. (The recording side of the amendment:
  `test_ordpar_history88b.py`.)
* **One untranslated article:** its Norwegian definition in place of the "Norwegian only" tag;
  with no snippet, the tag.
* **One translated article:** its stored gloss, no fetch; an entry stored with an empty text
  (before decisions 82 made an empty one mean the snippet's first unit) is filled from the snippet.
* **Painted at once, filled after** (`is-pending`, as the suggestions); where the search finds
  nothing now or nothing answers, the row as stored ("N articles", "Norwegian only").
* **The wiring:** `searchRowSide` / `fillSearchRow` exported by the shell, the Recent rows filled
  and refitted, the history page filling its rows as they near the screen; the entries' stored
  shape (and so `personal.js` format version 2) unchanged.

`shell.js`'s own functions (`needsFill` .. `countOnly`, cut out of the file) run under bun (or
node) against a stand-in DOM and the real `lookup.js` over a synthetic index built by
`build_index.write_index`. Skipped when neither runner is on PATH. The layout (the fit, the
"+ N more" cut) is checked in a browser, not here."""

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
    _art(30, "fly", "NOUN", 1), _art(31, "fly", "NOUN", 2), _art(32, "fly", "VERB", 3),
    _art(40, "hus", "NOUN"), _art(50, "stille", "NOUN"), _art(60, "kjapp", "ADJ"),
    _art(70, "stillhet", "NOUN", 1), _art(71, "stillhet", "NOUN", 2),
]
TRANSLATED = [20, 22, 2, 32, 40]
SNIPPETS = {
    20: ("it · he", "en"), 21: ("brukt foran substantiv", "nb"), 22: ("the", "en"),
    4: ("kultivert, dannet", "nb"), 2: ("to form · to found", "en"),
    30: ("", "nb"), 31: ("lite insekt", "nb"), 32: ("to fly · to rush", "en"),
    40: ("a house · a building", "en"), 50: ("ro, taushet", "nb"),
    70: ("det å være stille", "nb"), 71: ("ro", "nb"),
}

HARNESS = r"""const fs = require('fs'), path = require('path');
const L = require(%(lookup)s).ordparLookup;
L.setLoader(name => { const p = path.join(%(index)s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
const STR = JSON.parse(fs.readFileSync(%(strings)s, 'utf8'));
const src = fs.readFileSync(%(shell)s, 'utf8');
const from = src.indexOf('  function needsFill('), to = src.indexOf('  function wireSearch(', from);
if (from < 0 || to < 0) { throw new Error('shell.js: needsFill .. wireSearch not found'); }
class N {
  constructor(tag, cls, text) {
    this.tag = tag; this.className = cls || ''; this.children = []; this.parentNode = null;
    this.text = text == null ? '' : String(text); this.lang = ''; this.attrs = {}; this.hidden = false;
    this.clientWidth = 0;
    const me = this;
    this.classList = {
      contains: c => me.className.split(' ').indexOf(c) >= 0,
      add: c => { if (!me.classList.contains(c)) { me.className = (me.className + ' ' + c).trim(); } },
      remove: c => { me.className = me.className.split(' ').filter(x => x && x !== c).join(' '); }
    };
  }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  set textContent(v) { this.children.forEach(c => { c.parentNode = null; }); this.children = []; this.text = String(v); }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter(k => k !== c); c.parentNode = null; return c; }
  replaceChild(a, b) { const i = this.children.indexOf(b); this.children[i] = a; a.parentNode = this; b.parentNode = null; return b; }
  querySelectorAll(sel) {
    const out = [], c = sel.slice(1);
    const walk = n => n.children.forEach(k => { if (k.classList.contains(c)) { out.push(k); } walk(k); });
    walk(this); return out;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  setAttribute(n, v) { this.attrs[n] = String(v); }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
}
const doc = { createElement: t => new N(t), createTextNode: t => new N('#text', '', t) };
const el = (tag, cls, text) => new N(tag, cls, text);
const t = (key, vars) => { let s = STR[key] || key;
  for (const k in (vars || {})) { s = s.split('{' + k + '}').join(String(vars[k])); } return s; };
const ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];
const global = { ordparLookup: L };
const F = new Function('global', 'doc', 'el', 't', 'ROMAN', src.slice(from, to)
  + '; return { searchRowSide: searchRowSide, fillSearchRow: fillSearchRow, historyArticles: historyArticles };')(
  global, doc, el, t, ROMAN);
function dump(side) {
  return side.children.map(c => {
    const o = { cls: c.className, text: c.textContent };
    if (c.lang) { o.lang = c.lang; }
    if (c.hidden) { o.hidden = true; }
    const items = c.children.filter(k => k.classList.contains('ordpar-option-gl'));
    if (items.length) {
      o.items = items.map(k => {
        const hg = k.querySelector('.ordpar-hg');
        return { text: k.textContent.replace(/^ · /, ''), lang: k.lang || '',
          hg: hg ? hg.textContent : null };
      });
    }
    return o;
  });
}
async function row(e, opts) {
  const side = F.searchRowSide(e);
  const first = dump(side);
  let refits = 0;
  await F.fillSearchRow(side, e, () => { refits++; });
  return { first: first, side: dump(side), refits: refits };
}
function out(v) { process.stdout.write(JSON.stringify(v)); }
"""


class HistoryGlosses88(unittest.TestCase):

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

    def js(self, body, no_lookup=False):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        script = os.path.join(self.tmp, "run88.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(HARNESS % {
                "lookup": json.dumps(os.path.join(SITE, "lookup.js")),
                "index": json.dumps(os.path.join(self.tmp, "index")),
                "strings": json.dumps(os.path.join(SITE, "strings", "en.json")),
                "shell": json.dumps(os.path.join(SITE, "shell.js")),
            })
            if no_lookup:
                fh.write("global.ordparLookup = null;\n")
            fh.write("(async () => { " + body + " })().catch(e => { console.error(e); process.exit(1); });\n")
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))

    def row(self, entry):
        return self.js("out(await row(%s));" % json.dumps(entry))

    # ------------------------------------------------------------ several articles

    def test_several_list_the_translated_and_count_the_rest(self):
        got = self.row({"q": "den", "n": 3, "t": 1})
        # painted at once, held
        self.assertEqual(got["first"], [{"cls": "ordpar-option-glosses is-pending", "text": "\u00a0",
                                         "lang": "en"}])
        side = got["side"]
        self.assertEqual(side[0]["cls"], "ordpar-option-glosses")
        # 88's second amendment: the translated (I, III) by their glosses, II (untranslated)
        # counted in "+ 1 more", as the suggestion row for *den* draws it — no Norwegian
        self.assertEqual([(i["hg"], i["text"].split("homograph")[0], i["lang"]) for i in side[0]["items"]],
                         [("I", "I", ""), ("III", "III", "")])
        self.assertTrue(side[0]["items"][0]["text"].endswith(" it"))
        self.assertNotIn("brukt foran substantiv", json.dumps(side))
        self.assertNotIn("Norwegian only", json.dumps(side))
        self.assertEqual(side[1]["cls"], "ordpar-option-count ordpar-option-more")
        self.assertEqual(side[1]["text"], "+ 1 more")
        self.assertFalse(side[1].get("hidden", False))
        self.assertEqual(got["refits"], 1)

    def test_several_all_untranslated_list_their_norwegian(self):
        # site decisions 144 (Robin, 2026-10-27; until then 88's second amendment: "N articles"):
        # with none translated, each homograph's numeral and its Norwegian definition, as the
        # suggestion row now draws it — the list Norwegian as a whole, nothing more to count
        side = self.row({"q": "stillhet", "n": 2, "t": 1})["side"]
        self.assertEqual(side[0]["cls"], "ordpar-option-glosses ordpar-option-nblist")
        self.assertEqual(side[0]["lang"], "nb")
        self.assertEqual([(i["hg"], i["text"].split("homograph")[-1].split(" ", 2)[-1])
                          for i in side[0]["items"]], [("I", "det å være stille"), ("II", "ro")])
        self.assertNotIn("articles", json.dumps(side))
        self.assertEqual(side[1]["cls"], "ordpar-option-count ordpar-option-more")
        self.assertTrue(side[1].get("hidden", False))

    def test_inflected_form_articles_are_not_listed(self):
        # 88 as amended: *dann* is a headword (untranslated) and an inflected form of *danne*; an
        # entry stored before the amendment counted both (n 2) — only the headword is found now,
        # so the row draws as one untranslated article: its Norwegian definition (amended again)
        side = self.row({"q": "dann", "n": 2, "t": 1})["side"]
        self.assertEqual(side, [{"cls": "ordpar-option-gloss", "text": "kultivert, dannet", "lang": "nb"}])
        self.assertNotIn("to form", json.dumps(side))          # danne's gloss
        got = self.js("out((await F.historyArticles('dann')));")
        self.assertEqual(got["n"], 1)
        self.assertEqual([a["id"] for a in got["list"]], [4])
        self.assertNotIn("word", got["list"][0])

    def test_an_old_inflected_only_entry_draws_as_stored(self):
        # *danna* is only an inflected form (of *danne*): the search finds no headword now, so an
        # entry stored before the amendment is drawn from what it stored
        self.assertIsNone(self.js("out(await F.historyArticles('danna'));"))
        one = {"q": "danna", "n": 1, "t": 1, "word": "danne", "hg": 0, "pos": "VERB",
               "translated": True}
        got = self.row(dict(one, text="to form"))
        self.assertEqual(got["side"], [{"cls": "ordpar-option-gloss", "text": "to form", "lang": "en"}])
        self.assertEqual(got["refits"], 0)                        # not fetched
        self.assertEqual(self.row(dict(one, text=""))["side"], [])
        self.assertEqual(self.row(dict(one, translated=False, text=""))["side"],
                         [{"cls": "ordpar-tag", "text": "Norwegian only"}])
        self.assertEqual(self.row({"q": "danna", "n": 2, "t": 1})["side"],
                         [{"cls": "ordpar-option-count", "text": "2 articles"}])

    def test_an_article_with_no_text_goes_under_more(self):
        side = self.row({"q": "fly", "n": 3, "t": 1})["side"]
        # fly I (no snippet) and II (untranslated) both go under "+ N more" (88 amended again)
        self.assertEqual([i["hg"] for i in side[0]["items"]], ["III"])
        self.assertEqual(side[1]["text"], "+ 2 more")
        self.assertFalse(side[1].get("hidden", False))

    def test_a_search_that_finds_nothing_now_keeps_the_count(self):
        side = self.row({"q": "borte", "n": 4, "t": 1})["side"]
        self.assertEqual(side, [{"cls": "ordpar-option-count", "text": "4 articles"}])

    # ------------------------------------------------------------ one article

    def test_one_untranslated_shows_its_definition(self):
        got = self.row({"q": "stille", "n": 1, "t": 1, "word": "stille", "hg": 0, "pos": "NOUN",
                        "translated": False, "text": ""})
        self.assertEqual(got["first"], [{"cls": "ordpar-option-gloss is-pending", "text": "\u00a0",
                                         "lang": "nb"}])
        self.assertEqual(got["side"], [{"cls": "ordpar-option-gloss", "text": "ro, taushet", "lang": "nb"}])

    def test_one_untranslated_with_no_snippet_keeps_the_tag(self):
        side = self.row({"q": "kjapp", "n": 1, "t": 1, "word": "kjapp", "hg": 0, "pos": "ADJ",
                         "translated": False, "text": ""})["side"]
        self.assertEqual(side, [{"cls": "ordpar-tag", "text": "Norwegian only"}])

    def test_one_translated_with_its_text_is_drawn_at_once(self):
        # drawn from its stored text at once; since site decisions 116 (2026-10-24) its search
        # is run once more to learn whether the text is a summary gloss (`checkStored`) — here
        # the file has no "_g", so the text stays as stored and regular, and the row is not refitted
        got = self.row({"q": "hus", "n": 1, "t": 1, "word": "hus", "hg": 0, "pos": "NOUN",
                        "translated": True, "text": "a house"})
        self.assertEqual(got["first"], [{"cls": "ordpar-option-gloss is-check", "text": "a house", "lang": "en"}])
        self.assertEqual(got["side"], [{"cls": "ordpar-option-gloss", "text": "a house", "lang": "en"}])
        self.assertEqual(got["refits"], 0)

    def test_an_entry_stored_with_an_empty_text_is_filled(self):
        side = self.row({"q": "hus", "n": 1, "t": 1, "word": "hus", "hg": 0, "pos": "NOUN",
                         "translated": True, "text": ""})["side"]
        self.assertEqual(side, [{"cls": "ordpar-option-gloss", "text": "a house", "lang": "en"}])

    def test_without_the_lookup_the_row_is_drawn_as_stored(self):
        got = self.js("""out([F.searchRowSide({q: 'den', n: 3, t: 1}),
  F.searchRowSide({q: 'stille', n: 1, t: 1, word: 'stille', hg: 0, pos: '', translated: false, text: ''})
].map(dump));""", no_lookup=True)
        self.assertEqual(got, [[{"cls": "ordpar-option-count", "text": "3 articles"}],
                               [{"cls": "ordpar-tag", "text": "Norwegian only"}]])

    # ------------------------------------------------------------ the old entries

    def test_an_old_per_article_entry_draws_as_a_new_one(self):
        # personal.js reads a pre-60b entry as a search (`fromArticles`): its shape is unchanged,
        # and the row is drawn from the dictionary like any other
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            self.skipTest("no bun/node on PATH")
        got = self.js("""const P = require(%s);
const h = P.parseHistory(JSON.stringify([{id: 50, word: 'stille', hg: 0, pos: 'NOUN',
  translated: false, snip: 'ro, taushet', t: 5}]));
out([h, (await row(h[0])).side]);""" % json.dumps(os.path.join(SITE, "personal.js")))
        self.assertEqual(got[0], [{"q": "stille", "n": 1, "t": 5, "word": "stille", "hg": 0,
                                   "pos": "NOUN", "translated": False, "text": ""}])
        self.assertEqual(got[1], [{"cls": "ordpar-option-gloss", "text": "ro, taushet", "lang": "nb"}])

    # ------------------------------------------------------------ the wiring

    def test_wiring(self):
        js = _read(SITE, "shell.js")
        self.assertIn("searchRowSide: searchRowSide, fillSearchRow: fillSearchRow,", js)
        recent = js[js.index("    function openRecent("):js.index("    function emptyBox(")]
        self.assertIn("fillSearchRow(li.querySelector('.ordpar-option-side'), item.recent", recent)
        self.assertIn("if (mine === seq && li.parentNode === listbox) { fitRow(li, item); }", recent)
        page = _read(SITE, "personal-page.js")
        self.assertIn("sh.fillSearchRow(r.side, r.e);", page)
        self.assertIn("new global.IntersectionObserver(", page)
        # the stored shape is unchanged: no new field, the format still version 2
        personal = _read(SITE, "personal.js")
        self.assertIn("var VERSION = 2;", personal)
        # 88 as amended: the bold headword before an inflected-form article is gone
        self.assertNotIn("ordpar-option-gl-word", _read(SITE, "shell.css"))
        self.assertNotIn("ordpar-option-gl-word", js)


if __name__ == "__main__":
    unittest.main()
