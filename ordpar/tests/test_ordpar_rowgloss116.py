"""Site-review decisions 116 (Robin, 2026-10-24): only the summary glosses semibold, the "·" faded.

The pick from the row-gloss lab: semibold for English equivalents only, and the `·`
faded; English definition lines stay regular text, also where the article has no summary
glosses; the separator semibold still. The parts that need no browser (the browser
side: `test_ordpar_browser_rowgloss116.py`):

* **The data**: `article.snippet_is_gloss` is true only where the snippet is the summary gloss
  (42), never for a first English sense or a Norwegian line; `build_index.snippet_files` lists
  those ids under `"_g"` (integers, each once, translated articles only), and nothing where there
  is none; `read_snippets` takes the fourth element.
* **The article head**: `head_html` writes each " · " between the glosses as
  `<span class="ordpar-gsep"> · </span>`, the words and the stored separator unchanged.
* **The stylesheet**: `.ordpar-sgloss` 600 and `.ordpar-gsep` in `--ordpar-muted`, in
  `shell.css`; no rule sets a whole row snippet's weight.
* **The scripts**: `lookup.js` `isGloss` / `writeGloss` (a gloss marked and its " · " in spans; any
  other text plain, the mark removed), under bun.
* **The deck** (105, "the deck follows"): `mini.py` `render`'s header puts each " · " of its gloss in
  `.mini-gsep`, #757070 by day and #b9b6b6 at night; nothing else in the mini changes.
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
sys.path.insert(0, ORDPAR)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_index as B  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _row(gloss=None, en="first sense"):
    r = {"id": 1, "pos_en": "noun", "lemmas": [{"form": "hus"}],
         "senses": [{"defn": 1, "no": ["bygning"], "en": [en], "subs": [], "ex": [], "comp": []}]}
    if gloss:
        r["summary"] = {"gloss": gloss}
    return r


class TheData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from ordpar.sitegen import article
        except Exception as e:                      # the deck's renderer not importable
            raise unittest.SkipTest("sitegen.article not importable: %s" % e)
        cls.article = article

    def test_snippet_is_gloss_only_for_the_summary_gloss(self):
        a = self.article
        g = _row(gloss=["a house", "a building"])
        self.assertTrue(a.snippet_is_gloss(g, g))
        self.assertEqual(a.snippet(g, g), ("a house · a building", "en"))
        e = _row()                                   # translated, no summary gloss
        self.assertFalse(a.snippet_is_gloss(e, e))
        self.assertEqual(a.snippet(e, e), ("first sense", "en"))
        self.assertFalse(a.snippet_is_gloss(g, None))  # untranslated: its Norwegian

    def test_snippet_files_list_the_glosses_under_g(self):
        heads = {"h": {"hus": [1, 2, 3], "huse": [1]}}
        snippets = {1: ("a house · a building", "en", None, 1),
                    2: ("first sense", "en"),
                    3: ("bygning", "nb", None, 1)}           # untranslated: never listed
        out, missing, mismatched = B.snippet_files(heads, snippets, [1, 2])
        f = out[B.snippet_key("hus")]
        self.assertEqual(f["_g"], [1])
        self.assertEqual(f["1"], "a house · a building")
        self.assertNotIn("_d", f)
        self.assertEqual((missing, mismatched), (0, 0))
        out, _m, _mm = B.snippet_files({"h": {"hus": [2]}}, snippets, [1, 2])
        self.assertNotIn("_g", out[B.snippet_key("hus")])     # none: no list

    def test_read_snippets_takes_up_to_four(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "s.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"1": ["a", "en"], "2": ["b", "en", "c"], "3": ["d", "en", None, 1]}, fh)
            self.assertEqual(B.read_snippets(p), {1: ("a", "en"), 2: ("b", "en", "c"),
                                                  3: ("d", "en", None, 1)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_article_head_fades_its_separator(self):
        from ordpar.sitegen import page
        h = self.article.head_html({"lemmas": [], "pos_en": "noun"}, page.EN,
                                   gloss=["a house", "a building"])
        self.assertIn('<p class="ordpar-gloss" lang="en">a house<span class="ordpar-gsep"> · </span>'
                      'a building</p>', h)


class TheStylesheetAndScripts(unittest.TestCase):

    def test_shell_css_rules(self):
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-sgloss { font-weight: 600; }", css)
        self.assertIn(".ordpar-gsep { color: var(--ordpar-muted); }", css)
        # the whole-row selectors carry no weight (the lab's misreading: fjellslette semibold)
        for sel in (".ordpar-row-snippet {", ".ordpar-hit-snippet {",
                    ".ordpar-option-gloss, .ordpar-option-count, .ordpar-option-glosses {"):
            rule = css[css.index(sel):css.index("}", css.index(sel))]
            self.assertNotIn("font-weight", rule, sel)

    def test_the_scripts_write_the_separator_span(self):
        for name in ("shell.js", "mini.js"):
            self.assertIn("'ordpar-gsep'", _read(SITE, name), name)
        self.assertIn("SEP_CLASS = 'ordpar-gsep'", _read(SITE, "lookup.js"))
        self.assertIn("markGloss(snip, e)", _read(SITE, "personal-page.js"))

    def test_lookup_isgloss_and_writegloss_under_bun(self):
        run = shutil.which("bun") or shutil.which("node")
        if not run:
            self.skipTest("no bun or node")
        js = r"""
const L = require(%s).ordparLookup;
class N { constructor(t, x) { this.tag = t; this.kids = []; this.className = ''; this.ownerDocument = doc;
    if (x != null) this.data = x;
    const me = this; this.classList = { add: c => { if (!me.className.split(' ').includes(c)) me.className = (me.className + ' ' + c).trim(); },
      remove: c => { me.className = me.className.split(' ').filter(k => k && k !== c).join(' '); } }; }
  set textContent(v) { this.kids = []; if (v) this.kids.push(new N('#text', String(v))); }
  get textContent() { return this.data != null ? this.data : this.kids.map(k => k.textContent).join(''); }
  appendChild(k) { this.kids.push(k); return k; } }
const doc = { createElement: t => new N(t), createTextNode: t => new N('#text', t) };
const snips = { '1': 'a house · a building', '2': 'first sense', _g: [1] };
const a = new N('span'); L.writeGloss(a, snips['1'], L.isGloss(snips, '1'));
const b = new N('span'); b.className = 'x ordpar-sgloss'; L.writeGloss(b, snips['2'], L.isGloss(snips, '2'));
console.log(JSON.stringify({ g1: L.isGloss(snips, '1'), g2: L.isGloss(snips, 2), none: L.isGloss({ '1': 'x' }, '1'),
  a: { cls: a.className, text: a.textContent, kids: a.kids.map(k => [k.tag, k.className, k.textContent]) },
  b: { cls: b.className, text: b.textContent, kids: b.kids.length } }));
""" % json.dumps(os.path.join(SITE, "lookup.js"))
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "t.js")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(js)
            out = subprocess.run([run, p], capture_output=True, text=True, encoding="utf-8", timeout=60)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        got = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual((got["g1"], got["g2"], got["none"]), (True, False, False))
        self.assertEqual(got["a"]["cls"], "ordpar-sgloss")
        self.assertEqual(got["a"]["text"], "a house · a building")
        self.assertEqual(got["a"]["kids"], [["#text", "", "a house"], ["span", "ordpar-gsep", " · "],
                                            ["#text", "", "a building"]])
        self.assertEqual(got["b"], {"cls": "x", "text": "first sense", "kids": 1})


class TheDeck(unittest.TestCase):

    def test_the_mini_header_fades_its_separator(self):
        try:
            import mini
        except Exception as e:
            self.skipTest("scripts/mini.py not importable: %s" % e)
        row = {"id": 7136, "lemmas": [{"form": "bosted"}], "senses": []}
        out = mini.render(row, "place of residence · dwelling place")
        self.assertIn('<span class="mini-gloss"> — place of residence<span class="mini-gsep"> · </span>'
                      'dwelling place</span>', out)
        one = mini.render(row, "a house")
        self.assertIn('<span class="mini-gloss"> — a house</span>', one)
        self.assertIn(".mini-gsep{color:#757070}", mini.STYLE)
        self.assertIn(".nightMode .mini-gsep{color:#b9b6b6}", mini.STYLE)


if __name__ == "__main__":
    unittest.main()
