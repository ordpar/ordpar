# -*- coding: utf-8 -*-
"""Pins the search results of site decisions 59 (Robin, 2026-10-19): every hit's article in
full by default, and the setting "List view in search" — one row per hit with a one-line
snippet, each opening its article in place. What can be pinned outside a browser:

* **The snippet** (`sitegen/article.py` `snippet`): the summary gloss on a translated article,
  else its first English sense; the first Norwegian sense on an untranslated one; nothing for
  an article with no senses (as ordbokene's row). `build_index.snippet_text` cuts it to one
  line at a word boundary with "…".
* **The snippet in the index**: `snippet_key` files a headword's snippet under its first three
  bare characters (`snip/h-u-s.json`), holding only the articles that are a HEADWORD under that
  key; `write_index` writes them and records them in the manifest; lookup.js `snipKey` agrees.
* **The id scheme** (lookup.js `scopeArticle`, `extractArticle`): every id of a fragment
  prefixed `r<id>-` and every reference to one following, a link to the article's own sense
  made in-page, the `<h1>` headword an `<h3>` linking to the canonical page — so two articles
  with the same `def1` sit on one page with no duplicate id.
* **The setting's key**: `listview` = off | on | multi (59b item 16), default multi from decisions 71
  (2026-10-20; off until then) to site decisions 158 (2026-11-01: a fourth value, `forms`, the
  default since — `test_ordpar_listview158.py`), in shell.js and its strings, a stored value kept;
  the search view reads it.
* The pages' wiring: `article.css` holds the fragment's rules and no page chrome (`page.css`);
  the search page and the 404 shell link the article sheets before the shell's and load
  `inflection.js` and `article.js`; `article.js`'s `ordparDefs` applies `infl` to toggles
  added later; the shell no longer styles `.ordpar-article` (the fragment's root class).

The second round (brief 59b, 2026-10-19):

* **Homograph order** (`build_index.homograph_order`, lookup.js `homographOrder`): verbs
  first in number order, then every other article in number order — *fange*, *stille*,
  *analog*, *for*, *fly* as ordbokene lists them, through both lookups over a built index.
* **The snippets file** lives outside `out/`: both scripts default to
  `ordpar/.build/build-snippets.json`, which `.gitignore` covers; every headword key has its
  `snip/` file (`{}` when none of its articles has a snippet), and the view asks for one only
  on a headword hit.
* **The summary gloss** is joined with " · " (`markup.HEADLINE_SEP`) in the snippet and the
  meta description, and a cut never leaves a dangling " ·"; `.ordpar-gloss` is semibold, 1.1x.
* **The view's strings and wiring**: the results heading "Norwegian–English dictionary" (site decisions 164; "Bokmål–English" until 2026-11-04) with the
  count, `results.headword` gone; Copy link / Share (no Cite), the button words the article
  page's own, and no "Article page" link in the row (site decisions 168, re-ruled 2026-11-06
  (everywhere); the string `results.articlePage` stays, for the static list rows' panel); an opened list row's inflection table follows the setting `infl`
  as an article page's does (decisions 83, 2026-10-21; until then it was always open, 59b (3)),
  in both views — no forced opening is left in `mountArticle`; the inflected-form
  rows take their headword's snippet (item 9).
* **Translated first** (item 12, `result_order` / `resultOrder`): the translated articles of a
  form before the untranslated, each group in the homograph order — *fly* V, III, then I, II,
  IV; the full view's "Not yet translated" sub-heading has decisions 58's words.
* **The dropdown's sides** (item 11): a suggestion carries its one article's word class; the
  shell shows "N articles", "Norwegian only" or the first gloss unit from `snip/`.
* **The autocomplete's translated first** (item 13): the exact match, then the one-word
  headwords translated before Norwegian-only, then the set phrases; the cut comes after.
* **The autocomplete by frequency** (item 14): inside the translated and the Norwegian-only
  headwords, the frequency band highest first, carried in the shards as `n` (one hex digit per
  sorted headword) and read alike by lookup.js and `shard_bands`; `-top` chosen in that order.
* **The autocomplete honours a trailing space** (item 10): "fy " offers *fy*, then the set
  phrases "fy …", then the ordinary completions — lookup.js `suggest` and its Python twin
  `Index.suggest` alike, over a built synthetic index; runs of spaces collapse.

The JavaScript tests run under `bun` (or `node`) and are skipped when neither is on PATH.
Synthetic rows and fragments only: no mirror, library or built site is read."""

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
sys.path.insert(0, ORDPAR)

import build_index as B  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run_js(body):
    """Run `body` with `L` (ordparLookup) and `S` (ordparSearch) loaded; it must print JSON.
    Skips the test when no runner is on PATH."""
    runner = _runner()
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("const M = require(%s); const L = M.ordparLookup, S = M.ordparSearch;\n%s\n"
                     % (json.dumps(os.path.join(SITE, "lookup.js")), body))
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tables(rows, tmp):
    """`build_tables` over a synthetic mirror file of `rows`."""
    mirror = os.path.join(tmp, "mirror.jsonl")
    with open(mirror, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return B.build_tables(mirror, None, {})


def _row(aid, lemma, pos="NOUN", forms=()):
    return {"id": aid, "data": {"lemmas": [{
        "lemma": lemma, "hgno": 0,
        "paradigm_info": [{"tags": [pos],
                           "inflection": [{"word_form": f} for f in forms]}]}]}}


class SnippetText(unittest.TestCase):

    def test_short_text_is_kept_on_one_line(self):
        self.assertEqual(B.snippet_text("a house;\n  a building"), "a house; a building")

    def test_long_text_is_cut_at_a_word_with_an_ellipsis(self):
        text = ("person som er tatt av fienden, særlig i krig og konflikt, og som holdes "
                "fanget i lang tid")
        cut = B.snippet_text(text, 60)
        self.assertTrue(cut.endswith("…"))
        self.assertLessEqual(len(cut), 60)
        self.assertTrue(text.startswith(cut[:-1]))
        self.assertNotEqual(cut[-2], " ")
        self.assertEqual(cut, "person som er tatt av fienden, særlig i krig og konflikt…")

    def test_one_long_word_is_cut_inside_it(self):
        self.assertEqual(B.snippet_text("x" * 100, 10), "x" * 9 + "…")

    def test_zero_limit_is_uncut(self):
        self.assertEqual(B.snippet_text("y " * 100, 0), " ".join(["y"] * 100))

    def test_default_limit(self):
        self.assertEqual(B.SNIPPET_MAX, 80)
        self.assertLessEqual(len(B.snippet_text("ord " * 60)), 80)


class SnippetSource(unittest.TestCase):
    """`article.snippet`: what the article build writes for the index."""

    @classmethod
    def setUpClass(cls):
        try:
            from sitegen import article
        except Exception as e:                       # the deck's renderer is not importable
            raise unittest.SkipTest("sitegen.article not importable: %s" % e)
        cls.article = article

    def test_translated_with_a_gloss(self):
        no = {"senses": [{"no": ["et byggverk"]}]}
        en = {"summary": {"gloss": ["a house", "a building"]}, "senses": [{"en": ["a building"]}]}
        self.assertEqual(self.article.snippet(no, en), ("a house · a building", "en"))

    def test_translated_without_a_gloss_takes_the_first_english_sense(self):
        no = {"senses": [{"no": ["et byggverk"]}]}
        en = {"senses": [{"en": [""], "subs": [{"en": ["a small house"]}]}]}
        self.assertEqual(self.article.snippet(no, en), ("a small house", "en"))

    def test_untranslated_takes_the_first_norwegian_sense(self):
        no = {"senses": [{"no": ["cirka, om lag"]}, {"no": ["noe annet"]}]}
        self.assertEqual(self.article.snippet(no, None), ("cirka, om lag", "nb"))

    def test_no_senses_gives_nothing(self):
        self.assertEqual(self.article.snippet({"senses": []}, None), ("", "nb"))

    def test_meta_description_joins_the_gloss_with_the_headline_separator(self):
        no = {"senses": [{"no": ["et byggverk"]}]}
        en = {"summary": {"gloss": ["a house", "a building"]}}
        self.assertEqual(self.article.meta_description(no, en, None), "a house · a building")


class SnippetCutAtTheSeparator(unittest.TestCase):
    """A " · "-joined gloss cut at 80 characters ends on a word, never on " ·"."""

    def test_no_dangling_separator(self):
        items = ["to catch", "to capture", "to seize", "to take prisoner", "to trap",
                 "to grasp", "to apprehend", "to net"]
        text = " · ".join(items)
        for limit in range(20, len(text)):
            cut = B.snippet_text(text, limit)
            self.assertLessEqual(len(cut), limit)
            self.assertTrue(cut.endswith("…"), cut)
            body = cut[:-1]
            self.assertFalse(body.endswith((" ", "·")), (limit, cut))


class SnippetIndex(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        rows = [_row(1, "hus", forms=["huset", "husene"]), _row(2, "huse", "VERB"),
                _row(3, "en", "DET"), _row(4, "én", "DET"), _row(5, "ta seg i akt", "EXPR"),
                _row(6, "ære", forms=["æren"]), _row(7, "ha", "VERB", forms=["hus"])]
        stats = {}
        heads, forms, words = _tables(rows, cls.tmp)
        snippets = {1: ("a house; a building", "en"), 2: ("gi husly til " * 12, "nb"),
                    3: ("one", "en"), 4: ("", "nb"), 5: ("passe seg", "nb"),
                    6: ("heder", "nb"), 7: ("eie", "nb")}
        cls.manifest = B.write_index(cls.tmp, heads, forms, words, [1, 3], stats,
                                     snippets=snippets)
        cls.stats = stats
        cls.dir = os.path.join(cls.tmp, "index", "snip")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def snip(self, key, rows=False):
        """A `snip/` file; its `"_h"` (site decisions 144: each headword's articles, for the similar
        rows) and its `"_n"` (site decisions 152: the translated articles' Norwegian definitions,
        `test_ordpar_nbonly152.py`) left out unless `rows`."""
        with open(os.path.join(self.dir, key + ".json"), encoding="utf-8") as fh:
            got = json.load(fh)
        if not rows:
            got.pop("_h", None)
            got.pop("_n", None)
        return got

    def test_keys(self):
        self.assertEqual(B.snippet_key("hus"), "h-u-s")
        self.assertEqual(B.snippet_key("Hus"), "h-u-s")
        self.assertEqual(B.snippet_key("en"), "e-n-misc")
        self.assertEqual(B.snippet_key("én"), "e-n-misc")          # with its bare letter
        self.assertEqual(B.snippet_key("ta seg i akt"), "t-a-misc")
        self.assertEqual(B.snippet_key("ære"), "ae-r-e")

    def test_files_hold_the_headword_articles_cut(self):
        hus = self.snip("h-u-s")
        self.assertEqual(hus["1"], "a house; a building")
        # site decisions 185: an untranslated article's Norwegian line is kept whole (the hover reads it)
        self.assertEqual(hus["2"], "gi husly til " * 12)
        self.assertGreater(len(hus["2"]), B.SNIPPET_MAX)
        self.assertNotIn("7", hus)          # *hus* is only an inflected form of 7 (ha)
        self.assertEqual(self.snip("h-a-misc"), {"7": "eie"})
        self.assertEqual(self.snip("h-a-misc", rows=True)["_h"], {"ha": 7})     # 144
        self.assertEqual(self.snip("e-n-misc"), {"3": "one"})       # 4 has none
        self.assertEqual(self.snip("t-a-misc"), {"5": "passe seg"})

    def test_manifest_and_counts(self):
        m = self.manifest["snip"]
        self.assertEqual(m["max"], B.SNIPPET_MAX)
        self.assertEqual(m["count"], 6)
        self.assertEqual(self.stats["snippets_missing"], 1)
        # 3 is translated with an English snippet, 1 too; 2 is not translated and Norwegian
        self.assertEqual(self.stats["snippet_lang_mismatch"], 0)
        self.assertEqual(sorted(f["k"] for f in m["files"]),
                         sorted(os.path.basename(p)[:-5] for p in os.listdir(self.dir)))

    def test_an_inflected_rows_headword_key_has_its_file(self):
        # item 9: *hus* is an inflected form of 7 (ha); the row's key is its shown headword's
        idx = B.Index(os.path.join(self.tmp, "index"))
        rows = [a for grp in idx.lookup("hus")["forms"] for a in grp["articles"]]
        self.assertEqual([a["id"] for a in rows], [7])
        for a in rows:
            key = B.snippet_key(a["word"].split(" / ")[0])
            self.assertTrue(os.path.exists(os.path.join(self.dir, key + ".json")), key)
            self.assertEqual(self.snip(key)[str(a["id"])], "eie")

    def test_no_snippets_still_writes_the_files_empty(self):
        tmp = tempfile.mkdtemp()
        try:
            stats = {}
            heads, forms, words = _tables([_row(1, "hus")], tmp)
            m = B.write_index(tmp, heads, forms, words, [], stats)
            self.assertEqual(m["snip"]["count"], 0)
            self.assertEqual(stats["snippets_missing"], 1)
            # every headword key has its file, so a hit never asks for a missing one (59b)
            with open(os.path.join(tmp, "index", "snip", "h-u-s.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh), {})
            self.assertEqual([f["k"] for f in m["snip"]["files"]], ["h-u-s"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_js_snip_key_matches_python(self):
        words = ["hus", "Hus", "en", "én", "ta seg i akt", "ære", "øl", "å", "s", "-aktig",
                 "à la carte", "kafé", "1", "x"]
        js = _run_js("process.stdout.write(JSON.stringify(%s.map(w => L.snipKey(L.fold(w)))));"
                     % json.dumps(words, ensure_ascii=False))
        self.assertEqual(js, [B.snippet_key(w) for w in words])


# a fragment shaped as `sitegen/page.py` `render` writes it (ids and references as on 24627)
PAGE = """<!doctype html><html><head><title>t</title></head><body>
<article class="ordpar-entry">
  <p class="ordpar-caption">Norwegian only · not yet translated</p>
  <p class="ordpar-note">This article has not been translated yet.</p>
<div class="ordbok ordpar-article">
  <div class="ordbok-head">
    <h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma">hus</span><span class="ordbok-homograph" aria-hidden="true">II</span><span class="sr-only"> homograph 2</span></h1>
    <p class="ordpar-gloss" lang="en">a house<sup><a href="/bm-en/@ID@/#def1">1</a></sup></p>
  </div>
  <script type="application/json" id="ordpar-paradigm">{"lemmas":[]}</script>
  <details class="ordpar-infl-toggle" hidden><summary>Inflection</summary>
  <div class="ordpar-inflection" data-paradigm="ordpar-paradigm"></div></details>
  <section class="ordbok-sec"><h3 lang="en">Senses and Example Sentences</h3>
  <ol><li id="def1"><span class="ordbok-xref"><input type="checkbox" id="xra@ID@-1" class="ordbok-xtoggle"><label for="xra@ID@-1" class="ordbok-xword" data-href="/bm-en/999/">bygning</label></span>
  <span class="ordpar-xen" data-for="xra@ID@-1"><label>building</label></span>
  se <a href="/bm-en/@ID@/#def2">2</a> and <a href="/bm-en/999/#def1">bygning</a></li>
  <li id="def2">to</li></ol></section>
  <section class="ordbok-sec"><h3 lang="en">Set phrases</h3>
  <ol><li id="x102921-def4">på huset</li></ol></section>
</div>
<footer class="ordpar-attr"><p id="ordpar-copy">credit</p></footer>
</article></body></html>"""


class IdScheme(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pages = {"24627": PAGE.replace("@ID@", "24627"), "24650": PAGE.replace("@ID@", "24650")}
        cls.out = _run_js("""
const pages = %s, out = {};
for (const id in pages) {
  const got = S.extractArticle(pages[id]);
  out[id] = {caption: got.caption, full: S.scopeArticle(got.fragment, Number(id), 3),
             list: S.scopeArticle(got.fragment, Number(id), 4)};
}
out.none = S.extractArticle('<html><body>no fragment</body></html>');
out.roman = [1, 2, 4, 9, 12].map(S.roman);
process.stdout.write(JSON.stringify(out));
""" % json.dumps(pages, ensure_ascii=False))

    def test_extract_takes_caption_and_fragment_not_note_or_footer(self):
        got = self.out["24627"]
        self.assertEqual(got["caption"], '<p class="ordpar-caption">Norwegian only · not yet translated</p>')
        self.assertTrue(got["full"].startswith('<div class="ordbok ordpar-article">'))
        self.assertNotIn("ordpar-note", got["full"])
        self.assertNotIn("ordpar-attr", got["full"])
        self.assertNotIn("ordpar-copy", got["full"])
        self.assertIsNone(self.out["none"])

    def test_every_id_is_prefixed(self):
        html = self.out["24627"]["full"]
        ids = re.findall(r' id="([^"]*)"', html)
        self.assertEqual(sorted(ids), sorted(["r24627-hw", "r24627-ordpar-paradigm", "r24627-def1",
                                              "r24627-def2", "r24627-x102921-def4",
                                              "r24627-xra24627-1"]))

    def test_references_follow(self):
        html = self.out["24627"]["full"]
        self.assertIn('for="r24627-xra24627-1"', html)
        self.assertIn('data-for="r24627-xra24627-1"', html)
        self.assertIn('data-paradigm="r24627-ordpar-paradigm"', html)
        for ref in re.findall(r' (?:for|data-for|data-paradigm)="([^"]*)"', html):
            self.assertIn(' id="%s"' % ref, html)

    def test_links(self):
        html = self.out["24627"]["full"]
        self.assertIn('href="#r24627-def1"', html)               # the gloss's sense mark
        self.assertIn('href="#r24627-def2"', html)               # a link to its own sense
        self.assertIn('href="/bm-en/999/#def1"', html)           # another article: untouched
        self.assertIn('data-href="/bm-en/999/"', html)
        for ref in re.findall(r'href="#([^"]*)"', html):
            self.assertIn(' id="%s"' % ref, html)

    def test_headword_and_heading_levels(self):
        full, lst = self.out["24627"]["full"], self.out["24627"]["list"]
        self.assertNotIn("<h1", full)
        # the headword no link, as ordbokene's results (decisions 160); Copy link and Share carry
        # the article page's address (no "Article page" link since 168 was re-ruled, 2026-11-06)
        self.assertIn('<h3 class="ordpar-hw" lang="nb" id="r24627-hw"><span class="ordbok-lemma">hus</span>', full)
        self.assertNotIn('ordpar-hw-link', full + lst)
        self.assertEqual(full.count('<h3 lang="en" aria-level="4">'), 2)
        self.assertIn('id="r24627-hw" aria-level="4"><span class="ordbok-lemma">hus</span>', lst)
        self.assertEqual(lst.count('<h3 lang="en" aria-level="5">'), 2)

    def test_two_articles_on_one_page_share_no_id(self):
        both = self.out["24627"]["full"] + self.out["24650"]["full"]
        ids = re.findall(r' id="([^"]*)"', both)
        self.assertEqual(len(ids), len(set(ids)))
        # the unscoped fragments collide on def1, def2, the paradigm and the expression
        raw = PAGE.replace("@ID@", "1") + PAGE.replace("@ID@", "1")
        self.assertGreater(len(re.findall(r' id="def1"', raw)), 1)

    def test_roman(self):
        self.assertEqual(self.out["roman"], ["I", "II", "IV", "IX", "12"])


class Setting(unittest.TestCase):

    def test_shell_key_values_default(self):
        # decisions 63: one table of settings (shell.js SETTINGS), which the settings page draws
        js = _read(SITE, "shell.js")
        # site decisions 158: `forms` first and the default (test_ordpar_listview158.py)
        self.assertIn("{ key: 'listview', values: ['forms', 'multi', 'on', 'off'], def: 'forms', section: 'search' }", js)
        self.assertIn("var KEYS = SETTINGS.map(function (sp) { return sp.key; });", js)
        self.assertIn("sp.values.indexOf(v) !== -1 ? v : sp.def", js)
        self.assertIn("sh.SETTINGS.forEach(function (sp) {", _read(SITE, "settings.js"))

    def test_shell_getsetting_under_js(self):
        body = """
const store = {};
globalThis.localStorage = {getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }, clear: () => {}};
const cl = {toggle() {}, add() {}, contains() { return false; }};
globalThis.document = {readyState: 'loading', documentElement: {classList: cl, setAttribute() {}, removeAttribute() {}},
  addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; }};
globalThis.matchMedia = () => ({matches: false, addEventListener() {}});
globalThis.navigator = {languages: ['en']};
require(%s);
const S = globalThis.ordparShell, out = [S.getSetting('listview')];
store.listview = 'on'; out.push(S.getSetting('listview'));
store.listview = 'yes'; out.push(S.getSetting('listview'));
store.listview = 'multi'; out.push(S.getSetting('listview'));
store.listview = 'off'; out.push(S.getSetting('listview'));
S.setSetting('listview', 'on'); out.push(store.listview);
process.stdout.write(JSON.stringify(out));
""" % json.dumps(os.path.join(SITE, "shell.js"))
        runner = _runner()
        if not runner:
            self.skipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "shell.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(body)
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
            # the default and an unknown value: `forms` since site decisions 158 (`multi` from 71)
            self.assertEqual(json.loads(res.stdout.decode("utf-8")), ["forms", "on", "forms", "multi", "off", "on"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_strings(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["settings.listview"], "List view in search")
        self.assertEqual((s["settings.listview.off"], s["settings.listview.on"]), ("Off", "On"))
        self.assertEqual(s["settings.listview.multi"], "Only when there are several articles")
        for key in ("results.homograph", "results.loading"):
            self.assertIn(key, s)

    def test_the_view_reads_it(self):
        js = _read(SITE, "lookup.js")
        # site decisions 158: `forms` the fallback, and the form rows passed to the rule
        self.assertIn("return v === 'on' || v === 'off' || v === 'multi' ? v : 'forms';", js)
        self.assertIn("list = useList(mode, n, formHits(res));", js)
        self.assertIn("values: ['forms', 'multi', 'on', 'off']", _read(SITE, "shell.js"))

    def test_use_list(self):
        # 59b item 16: `multi` lists only several headword hits; the inflected-form rows are
        # not counted (the view counts `res.heads` alone)
        got = _run_js("process.stdout.write(JSON.stringify([['off',3],['on',1],['on',0],"
                      "['multi',1],['multi',2],['multi',0],['multi',5]].map(c => L.useList(c[0], c[1]))));")
        self.assertEqual(got, [False, True, True, False, True, False, True])
        js = _read(SITE, "lookup.js")
        self.assertIn("addKey(snipKey(fold(g.query)))", js)
        self.assertIn("setAttribute('aria-expanded', 'false')", js)
        self.assertIn("setAttribute('aria-controls', 'r' + a.id + '-panel')", js)
        self.assertIn("panel.setAttribute('aria-labelledby', btn.id)", js)


def _hrow(aid, lemma, hg, pos):
    return {"id": aid, "data": {"lemmas": [{"lemma": lemma, "hgno": hg,
                                            "paradigm_info": [{"tags": [pos], "inflection": []}]}]}}


#: Homograph groups with ordbokene's order (measured 2026-10-19, decisions 59; *fly* read on
#: the live page 2026-10-19): the mirror's ids, numbers and first paradigm tags.
GROUPS = {
    "fange": ([(13787, 2, "NOUN"), (13789, 1, "NOUN"), (13791, 3, "VERB")],
              [13791, 13789, 13787]),                                   # III, I, II
    "stille": ([(57184, 1, "NOUN"), (57185, 2, "ADJ"), (57186, 4, "VERB"), (57187, 5, "VERB"),
                (99031, 3, "NOUN")],
               [57186, 57187, 57184, 57185, 99031]),                    # IV, V, I, II, III
    "analog": ([(1606, 1, "ADJ"), (107406, 2, "NOUN")], [1606, 107406]),
    "for": ([(15906, 1, "NOUN"), (15907, 2, "NOUN"), (15908, 5, "ADP"), (15909, 3, "CCONJ"),
             (15910, 4, "ADV")],
            [15906, 15907, 15909, 15910, 15908]),                       # I–V
    "fly": ([(15540, 1, "NOUN"), (15541, 2, "NOUN"), (15542, 3, "NOUN"), (15543, 4, "ADV"),
             (15544, 5, "VERB")],
            [15544, 15540, 15541, 15542, 15543]),                       # V, I–IV
}


class HomographOrder(unittest.TestCase):
    """Brief 59b item 1: verbs first in number order, then the rest in number order."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        rows = [_hrow(i, w, hg, pos) for w, (arts, _) in GROUPS.items() for i, hg, pos in arts]
        rows.append(_hrow(900001, "rapp", 0, "NOUN"))          # an unnumbered article ...
        rows.append(_hrow(900002, "rapp", 1, "VERB"))          # ... before the numbered verb
        rows.append(_hrow(900003, "rapp", 2, "NOUN"))
        heads, forms, words = _tables(rows, cls.tmp)
        B.write_index(cls.tmp, heads, forms, words, [], {})
        cls.index = os.path.join(cls.tmp, "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_sort_key(self):
        for word, (arts, want) in GROUPS.items():
            got = sorted(({"id": i, "hg": hg, "pos": pos} for i, hg, pos in arts),
                         key=B.homograph_order)
            self.assertEqual([a["id"] for a in got], want, word)

    def test_python_lookup(self):
        idx = B.Index(self.index)
        for word, (_arts, want) in GROUPS.items():
            res = idx.lookup(word)
            self.assertEqual([a["id"] for a in res["heads"][0]["articles"]], want, word)
        self.assertEqual([a["id"] for a in idx.lookup("rapp")["heads"][0]["articles"]],
                         [900001, 900002, 900003])

    def test_js_lookup(self):
        words = list(GROUPS) + ["rapp"]
        js = _run_js("""
const fs = require('fs'), path = require('path');
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
Promise.all(%s.map(w => L.lookup(w))).then(rs => process.stdout.write(JSON.stringify(
  rs.map(r => r.heads[0].articles.map(a => a.id)))));
""" % (json.dumps(self.index), json.dumps(words)))
        self.assertEqual(js, [GROUPS[w][1] for w in GROUPS] + [[900001, 900002, 900003]])


class TrailingSpace(unittest.TestCase):
    """Brief 59b item 10: ordbokene's suggest API answers for "fy" and "fy " (2026-10-19)."""

    WORDS = ["fy", "fyk", "fyr", "fyke", "fyll", "fy faen", "fy flate", "fy søren",
             "fy til katta", "fy til grisen", "fyrstikk"]
    WANT = {
        # item 13: the set phrases after every headword (all untranslated here)
        "fy": ["fy", "fyk", "fyr", "fyke", "fyll", "fyrstikk", "fy faen", "fy flate", "fy søren",
               "fy til katta", "fy til grisen"],
        "fy ": ["fy", "fy faen", "fy flate", "fy søren", "fy til katta", "fy til grisen",
                "fyk", "fyr", "fyke", "fyll", "fyrstikk"],
        "  fy   ": ["fy", "fy faen", "fy flate", "fy søren", "fy til katta", "fy til grisen",
                    "fyk", "fyr", "fyke", "fyll", "fyrstikk"],
        "fy f": ["fy faen", "fy flate"],
        "fy  til ": ["fy til katta", "fy til grisen"],
    }

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        rows = [_hrow(800000 + n, w, 0, "EXPR" if " " in w else "NOUN")
                for n, w in enumerate(cls.WORDS)]
        heads, forms, words = _tables(rows, cls.tmp)
        B.write_index(cls.tmp, heads, forms, words, [], {})
        cls.index = os.path.join(cls.tmp, "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_python(self):
        idx = B.Index(self.index)
        for q, want in self.WANT.items():
            self.assertEqual([x["word"] for x in idx.suggest(q)], want, repr(q))

    def test_js(self):
        qs = list(self.WANT)
        js = _run_js("""
const fs = require('fs'), path = require('path');
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
Promise.all(%s.map(q => L.suggest(q))).then(rs => process.stdout.write(JSON.stringify(
  rs.map(r => r.map(x => x.word)))));
""" % (json.dumps(self.index), json.dumps(qs, ensure_ascii=False)))
        self.assertEqual(js, [self.WANT[q] for q in qs])

    def test_submit_still_trims(self):
        self.assertIn("var query = (value != null ? value : input.value).trim();",
                      _read(SITE, "shell.js"))


class TranslatedFirst(unittest.TestCase):
    """Brief 59b item 12: translated first, then the item-1 order inside each group."""

    # fly in the build of 2026-10-19: V (verb) and III translated
    FLY = [(15540, 1, "NOUN", False), (15541, 2, "NOUN", False), (15542, 3, "NOUN", True),
           (15543, 4, "ADV", False), (15544, 5, "VERB", True)]
    WANT = [15544, 15542, 15540, 15541, 15543]
    # a translated noun before an untranslated verb; verbs first inside each group
    MIXED = [(1, 1, "NOUN", False), (2, 2, "VERB", False), (3, 3, "NOUN", True), (4, 4, "VERB", True)]
    MIXED_WANT = [4, 3, 2, 1]

    def _arts(self, rows):
        return [{"id": i, "hg": hg, "pos": pos, "translated": tr} for i, hg, pos, tr in rows]

    def test_python(self):
        for rows, want in ((self.FLY, self.WANT), (self.MIXED, self.MIXED_WANT)):
            self.assertEqual([a["id"] for a in sorted(self._arts(rows), key=B.result_order)], want)

    def test_js(self):
        js = _run_js("process.stdout.write(JSON.stringify([%s, %s].map(r => r.sort(L.resultOrder)"
                     ".map(a => a.id))));" % (json.dumps(self._arts(self.FLY)),
                                               json.dumps(self._arts(self.MIXED))))
        self.assertEqual(js, [self.WANT, self.MIXED_WANT])

    def test_python_lookup_puts_translated_first(self):
        tmp = tempfile.mkdtemp()
        try:
            rows = [_hrow(i, "fly", hg, pos) for i, hg, pos, _tr in self.FLY]
            heads, forms, words = _tables(rows, tmp)
            B.write_index(tmp, heads, forms, words, [15542, 15544], {})
            res = B.Index(os.path.join(tmp, "index")).lookup("fly")
            self.assertEqual([a["id"] for a in res["heads"][0]["articles"]], self.WANT)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_sub_heading_words(self):
        try:
            from sitegen import article
        except Exception as e:
            self.skipTest("sitegen.article not importable: %s" % e)
        strings = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(strings["results.untranslated"], article.UNTRANSLATED_HEAD)
        self.assertIn("el('p', 'ordpar-untr-head', t('results.untranslated'))", _read(SITE, "lookup.js"))


class DropdownSides(unittest.TestCase):
    """Brief 59b item 11, what can be pinned outside a browser."""

    def test_suggestion_carries_one_articles_word_class(self):
        tmp = tempfile.mkdtemp()
        try:
            rows = [_hrow(1, "fly", 1, "NOUN"), _hrow(2, "fly", 2, "VERB"), _hrow(3, "flyte", 0, "VERB"),
                    _hrow(4, "fly av", 0, "EXPR")]
            heads, forms, words = _tables(rows, tmp)
            B.write_index(tmp, heads, forms, words, [3], {})
            js = _run_js("""
const fs = require('fs'), path = require('path');
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
L.suggest('fly').then(r => process.stdout.write(JSON.stringify(
  r.map(x => [x.word, x.ids.length, x.pos, x.translated]))));
""" % json.dumps(os.path.join(tmp, "index")))
            self.assertEqual(js, [["fly", 2, "", False], ["flyte", 1, "VERB", True],
                                  ["fly av", 1, "EXPR", False]])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_shell_draws_the_sides(self):
        js = _read(SITE, "shell.js")
        self.assertIn("t('results.count', { n: g.n })", js)    # decisions 82: none to list
        self.assertIn("t('tag.norwegianOnly')", js)
        self.assertNotIn("t(item.translated ? 'tag.translated' : 'tag.norwegianOnly')", js)
        self.assertIn("lookup.loadSnippets(k)", js)
        # the first unit of the snippet, unless the file's "_d" map overrides it (a translated
        # set phrase with no gloss: its set-phrase box — brief 60 item 7(b); with no box, the
        # first unit after all, site decisions 82, A13 point 3)
        self.assertIn("snips[id].split(' \\u00b7 ')[0]", js)
        self.assertIn("snips._d[id]", js)
        # the word class on the left, after the word, for one article only
        self.assertIn("var pos = (item.ids || []).length === 1 ? posSpan(item.pos) : null;", js)
        self.assertIn("if (pos) { main.appendChild(pos); }", js)            # 152: `posSpan`, its language's words


class SuggestTranslatedFirst(unittest.TestCase):
    """Brief 59b item 13 as amended: exact match, translated headwords, Norwegian-only
    headwords, set phrases — each in the present order — and only then the cut."""

    ROWS = [(1, "kjøre", False), (2, "kjøretøy", True), (3, "kjøre inn", True), (4, "kjørel", False),
            (5, "kjører", False), (6, "kjørebane", True), (7, "kjøre opp", False)]
    WANT = {
        ("kjøre", None): ["kjøre", "kjøretøy", "kjørebane", "kjørel", "kjører", "kjøre inn", "kjøre opp"],
        ("kjøre", 3): ["kjøre", "kjøretøy", "kjørebane"],      # kjørebane was 6th before the order
        ("kjøre ", None): ["kjøre", "kjøre inn", "kjøre opp", "kjøretøy", "kjørebane", "kjørel", "kjører"],
        ("kjør", None): ["kjøretøy", "kjørebane", "kjøre", "kjørel", "kjører", "kjøre inn", "kjøre opp"],
    }

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        rows = [_hrow(i, w, 0, "EXPR" if " " in w else "VERB") for i, w, _tr in cls.ROWS]
        heads, forms, words = _tables(rows, cls.tmp)
        B.write_index(cls.tmp, heads, forms, words, [i for i, _w, tr in cls.ROWS if tr], {})
        cls.index = os.path.join(cls.tmp, "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_python(self):
        idx = B.Index(self.index)
        for (q, limit), want in self.WANT.items():
            got = idx.suggest(q, limit or 20)
            self.assertEqual([x["word"] for x in got], want, (q, limit))

    def test_js(self):
        cases = list(self.WANT)
        js = _run_js("""
const fs = require('fs'), path = require('path');
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
Promise.all(%s.map(c => L.suggest(c[0], c[1] || undefined))).then(rs => process.stdout.write(
  JSON.stringify(rs.map(r => r.map(x => x.word)))));
""" % (json.dumps(self.index), json.dumps([list(c) for c in cases], ensure_ascii=False)))
        self.assertEqual(js, [self.WANT[c] for c in cases])


class SuggestByFrequency(unittest.TestCase):
    """Brief 59b item 14: exact match; translated headwords by band, highest first; then the
    Norwegian-only by band; then the set phrases; then the accent-only continuations; the
    present order inside one band. Python and lookup.js alike, over a built index."""

    # (id, headword, translated, count) — the count becomes the band (`band`)
    ROWS = [(1, "kjøre", False, 50), (2, "kjøretøy", True, 100), (3, "kjørebane", True, 10000),
            (4, "kjører", False, 1000), (5, "kjørel", False, 0), (6, "kjøre inn", True, 99999),
            (7, "Kjørevei", True, 100), (8, "kjøretur", False, 1000), (9, "kjøreplan", True, 100)]
    WANT = {
        "kjøre": ["kjøre", "kjørebane", "kjøretøy", "Kjørevei", "kjøreplan", "kjører", "kjøretur",
                  "kjørel", "kjøre inn"],
        "kjøre ": ["kjøre", "kjøre inn", "kjørebane", "kjøretøy", "Kjørevei", "kjøreplan", "kjører",
                   "kjøretur", "kjørel"],
    }

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        rows = [_hrow(i, w, 0, "EXPR" if " " in w else "NOUN") for i, w, _t, _c in cls.ROWS]
        heads, forms, words = _tables(rows, cls.tmp)
        freq = {i: c for i, _w, _t, c in cls.ROWS}
        B.write_index(cls.tmp, heads, forms, words, [i for i, _w, t, _c in cls.ROWS if t], {}, freq)
        cls.index = os.path.join(cls.tmp, "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_bands_in_the_shard(self):
        shard = _load_json(os.path.join(self.index, "k-j.json"))
        self.assertEqual(len(shard["n"]), len(shard["heads"]))
        got = B.shard_bands(shard)
        self.assertEqual(got["kjørebane"], B.band(10000))
        self.assertEqual(got["kjørel"], 0)

    def test_python(self):
        idx = B.Index(self.index)
        for q, want in self.WANT.items():
            self.assertEqual([x["word"] for x in idx.suggest(q)], want, repr(q))

    def test_js(self):
        qs = list(self.WANT)
        js = _run_js("""
const fs = require('fs'), path = require('path');
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
Promise.all(%s.map(q => L.suggest(q))).then(rs => process.stdout.write(JSON.stringify(
  rs.map(r => r.map(x => x.word)))));
""" % (json.dumps(self.index), json.dumps(qs, ensure_ascii=False)))
        self.assertEqual(js, [self.WANT[q] for q in qs])

    def test_no_freq_writes_no_bands(self):
        tmp = tempfile.mkdtemp()
        try:
            heads, forms, words = _tables([_hrow(1, "kjøre", 0, "VERB")], tmp)
            B.write_index(tmp, heads, forms, words, [], {})
            self.assertNotIn("n", _load_json(os.path.join(tmp, "index", "k-j.json")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class SnippetsPath(unittest.TestCase):
    """Brief 59b item 4: the snippets file is out of `out/`, at one default both scripts share."""

    def test_default_path(self):
        want = os.path.join(ORDPAR, ".build", "build-snippets.json")
        self.assertEqual(os.path.normcase(B.SNIPPETS_PATH), os.path.normcase(want))
        out = os.path.normcase(os.path.join(ORDPAR, "out")) + os.sep
        self.assertFalse(os.path.normcase(B.SNIPPETS_PATH).startswith(out))
        try:
            sys.path.insert(0, ROOT)
            import ordpar.build_site as S
        except Exception as e:
            self.skipTest("build_site not importable: %s" % e)
        self.assertEqual(os.path.normcase(os.path.abspath(S.SNIPPETS_PATH)),
                         os.path.normcase(want))

    def test_gitignored(self):
        lines = [l.strip() for l in _read(ROOT, ".gitignore").splitlines()]
        self.assertIn("ordpar/.build/", lines)


class View59b(unittest.TestCase):
    """What the view's source must say (the rest is checked in the browser)."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(SITE, "lookup.js")
        cls.strings = json.loads(_read(SITE, "strings", "en.json"))

    def test_heading_strings(self):
        self.assertEqual(self.strings["results.dictionary"], "Norwegian–English dictionary")   # site decisions 164
        self.assertNotIn("results.headword", self.strings)
        self.assertNotIn("results.headword", self.js)
        self.assertIn("resultsHeading(res.count)", self.js)
        for key in ("results.count", "results.countOne"):
            self.assertIn(key, self.strings)

    def test_controls_words_are_the_pages(self):
        try:
            from sitegen.strings import EN
        except Exception as e:
            self.skipTest("sitegen.strings not importable: %s" % e)
        self.assertEqual(self.strings["results.copyLink"], EN["copy_link"])
        self.assertEqual(self.strings["results.copied"], EN["copy_done"])
        self.assertEqual(self.strings["results.share"], EN["share"])
        self.assertEqual(self.strings["results.articlePage"], "Article page")   # wordpages.py's
        # site decisions 168, re-ruled 2026-11-06 (everywhere): the row makes no "Article page"
        self.assertNotIn("ordpar-result-page", self.js)
        self.assertNotIn("results.articlePage", self.js)
        self.assertNotIn("Cite", self.strings.values())            # site decisions 21e
        self.assertFalse([k for k in self.strings if "cite" in k.lower()])
        self.assertIn("host.appendChild(resultControls(a));", self.js)

    def test_opened_row_follows_the_infl_setting(self):
        # decisions 83: both views mount the article the same way, and the toggle is left to
        # article.js `infl` (via `ordparDefs`), which opens it only where `infl` = open
        # the row's article one level under the row's heading (3 in the results; the favourites
        # page's rows are level 2, decisions 89)
        self.assertIn("mountArticle(panel, a, got, level + 1);", self.js)
        self.assertIn("var level = (opts && opts.level) || 3;", self.js)
        self.assertIn("mountArticle(art, a, got, 3);", self.js)
        self.assertNotIn("openTable", self.js)
        self.assertNotIn("mountArticle(panel, a, got, level + 1, true)", self.js)
        self.assertIn("function mountArticle(host, a, got, level) {", self.js)
        body = self.js.split("function mountArticle(host, a, got, level) {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("global.ordparDefs()", body)
        self.assertNotIn(".open = true", body)
        try:
            from sitegen import page
        except Exception as e:
            self.skipTest("sitegen.page not importable: %s" % e)
        # the article page's rule, which the opened row now shares: open only on `infl` = open,
        # once per toggle
        # site decisions 146: read through the visit (`ordparRead`), the saved setting without it
        self.assertIn("o=(window.ordparRead?window.ordparRead('infl'):localStorage.getItem('infl'))==='open'",
                      page.PAGE_JS)
        self.assertIn("if(ts[i]._i)continue;ts[i]._i=1;if(o)ts[i].open=true;", page.PAGE_JS)

    def test_snippets_only_on_a_headword_hit(self):
        self.assertNotIn("Promise.all([lookup(g.query), snipsP])", self.js)
        self.assertIn("if (list && res.heads.some(function (grp) { return grp.articles.length; })) {\n"
                      "        addKey(snipKey(fold(g.query)));", self.js)

    def test_inflected_rows_take_their_headwords_snippet(self):
        # item 9: each inflected-form row asks for its headword's key, in both views
        self.assertIn("grp.articles.forEach(function (a) { var w = lemmaOf(a); if (w) "
                      "{ addKey(snipKey(fold(w))); } });", self.js)
        self.assertIn("var snip = el('span', 'ordpar-hit-snippet is-pending'", self.js)

    def test_gloss_style(self):
        try:
            from sitegen import page
        except Exception as e:
            self.skipTest("sitegen.page not importable: %s" % e)
        self.assertIn(".ordpar-gloss{margin:.4em 0 0;font-size:1.1em;font-weight:600;", page.SITE_CSS)


class Wiring(unittest.TestCase):

    def test_sheets_split(self):
        try:
            from sitegen import page
        except Exception as e:
            self.skipTest("sitegen.page not importable: %s" % e)
        css = page.article_css()
        # decisions 63: the header, the footer and the card are shell.css's, on every page; the
        # article page's own sheet keeps only its "Article view" line, the table's room, About
        shell = _read(SITE, "shell.css")
        for chrome in (".ordpar-header {", ".ordpar-footer {", "body.ordpar {", ".ordpar-card {"):
            self.assertFalse(chrome in css, chrome)
            self.assertIn(chrome.split(" {")[0], shell)
        for gone in ("\n.ordpar-shell{", "\n.ordpar-head{", "\n.ordpar-attr{", "\nbody{", "\nhtml{"):
            self.assertFalse(gone in page.PAGE_CSS, gone)
        self.assertIn("\n.ordpar-viewline{", page.PAGE_CSS)
        for frag in ("\n.sr-only{", "\n.ordpar-caption{", "\n.ordpar-pair{", "\n.ordpar-infl-toggle{"):
            self.assertTrue(frag in css, frag)
        self.assertIn("infl();eyes();nbhw();};", page.PAGE_JS)   # 152: the headword's icon   # decisions 131: the eye last   # decisions 123: no pronunciation "?" since 2026-11-02
        self.assertNotIn("localStorage.getItem('infl')==='open'){", page.PAGE_JS)
        self.assertTrue(page.asset(page.PAGE_CSS_HREF).startswith("/site/page.css?v="))

    def test_search_pages_load_the_article_parts(self):
        for name in ("search.html", "404.html"):
            html = _read(SITE, name)
            from sitegen import page
            # one sheet since 2026-10-20, the shell pages' own: the article page's parts, then
            # the shell's
            self.assertIn('<link rel="stylesheet" href="/site/shell-pages.css">', html)
            parts = page.SHELL_CSS_PARTS
            self.assertLess(parts.index("/site/article.css"), parts.index("/site/shell.css"))
            self.assertLess(parts.index("/site/inflection.css"), parts.index("/site/shell.css"))
            self.assertIn('<script src="/site/inflection.js" defer></script>', html)
            self.assertIn('<script src="/site/article.js" defer></script>', html)
            # decisions 63: the head script is head.py's one copy, put in by the index build
            self.assertIn("<!--ORDPAR_HEADJS-->", html)
        from sitegen import head
        self.assertIn("ordpar-pframes-off", head.THEME_JS)

    def test_shell_css_leaves_the_fragment_root_alone(self):
        css = _read(SITE, "shell.css")
        self.assertNotRegex(css, r"\.ordpar-article\b")


if __name__ == "__main__":
    unittest.main()
