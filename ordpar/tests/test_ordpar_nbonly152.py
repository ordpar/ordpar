"""Site decisions 152 (Robin, 2026-10-30/31): Norwegian only, its settings, and the labels setting —
the static half (the browser half: `test_ordpar_browser_nbonly152.py`).

* **The settings' table** (`shell.js` `SETTINGS`): `labels` (en | no, Style) and the layer's five —
  `nbonly` (off | on), `nbequiv` (hidden | shown), `nbrows` (nbdef | none), `nbhover` (none | nbdef),
  `nbicon` (on | off) — each with its default listed first (107), the five marked `layer: true`
  under their own subsection at the head of Article; all six in the Definer address's table
  (`head.settings_table`, 146) and in an export (`personal.js` `SETTING_KEYS`); no preset sets or
  matches on the layer's (`settings.js` `articleSettings`), and Settings shows the sub-settings only
  while they act (`shown`).
* **The head script's classes** (run under bun): the layer answers seven settings' classes while on
  (Definitions, Examples, formula lines, etymology Norwegian; the small articles as the article; no
  subsenses in English; the hover by the English equivalents), never writing the stored values;
  `ordpar-nbo`, `-noeq`, `-rows0`, `-hovnb`, `ordpar-nbicon-off`, `ordpar-labels-no`; none of the
  sub-settings act while it is off; the address starts a visit with it (146). `shell.js` draws the
  same classes on a change; its search direction is Norwegian with the equivalents hidden, the stored
  direction untouched; `visitSetting` writes the visit, never `localStorage`.
* **The words**: every new setting's name, choices and hint; the icon's two titles; a Norwegian word
  class for every `pos.<code>`; the labels' Norwegian (`article.NB_LABELS`, `strings.NB`).
* **The `snip/` format**: `"_n"` — a translated article's first Norwegian definition, cut as the
  snippet, "" where it has none, `{}` in a file with none translated; the build's fifth element
  (`build_site.write_snippets`, `build_index.read_snippets`); `lookup.js` `nbDef` and `rowView`.
* **`data-nosnippet` on every new hidden copy** (154): the labels, the word class, the compound lists'
  and "Se:" lines' Norwegian copies, a built row's Norwegian line and word class, the change notice,
  the page script's labels, the inflection tables' words, the hover's Norwegian peek.
* **The deck untouched**: outside a site page, `article.pos_html` and the compound list's label are
  as before, and a link carries no `data-s`.

Stdlib unittest; the JS parts under bun or node (skipped without either).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)
sys.path.insert(0, HERE)

import build_index as BI  # noqa: E402
from sitegen import article, head, page, strings as strings_mod, wordpages, corrections  # noqa: E402
import test_ordpar_settingsaddr146 as T146  # noqa: E402  (its stand-in page and runner)


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SHELL_JS = _read(SITE, "shell.js")
STRINGS = json.loads(_read(SITE, "strings", "en.json"))
LAYER = ["nbonly", "nbequiv", "nbrows", "nbhover", "nbicon"]
RULED = {"labels": ["en", "no"], "nbonly": ["off", "on"], "nbequiv": ["hidden", "shown"],
         "nbrows": ["nbdef", "none"], "nbhover": ["none", "nbdef"], "nbicon": ["on", "off"]}


def _rows():
    body = SHELL_JS[SHELL_JS.index("var SETTINGS = ["):SHELL_JS.index("var SPEC = {}")]
    return {m.group(1): m.group(0) for m in re.finditer(r"\{ key: '(\w+)'[^}]*\}", body)}


def _js(body):
    return T146._run(T146._prelude() + body)


class TheSettings(unittest.TestCase):

    def test_a_the_rows(self):
        rows = _rows()
        for key, values in RULED.items():
            row = rows[key]
            self.assertIn("values: [%s], def: '%s'" % (", ".join("'%s'" % v for v in values), values[0]),
                          row)                                                # the default first (107)
            self.assertIn("layer: true", row, key)                           # never a preset's (136)
            self.assertIn("section: 'article', sub: 'nbonly'" if key in LAYER
                          else "section: 'article', sub: 'language'", row)
        keys = list(rows)
        # the layer's subsection at the head of the Article settings, straight after the Style ones;
        # labels last under Article's Language (Robin, 2026-11-02: "it belongs under "article", not
        # style"; under Style, after the layout, until then)
        self.assertEqual(keys[keys.index("layout") + 1:keys.index("defs")], LAYER)
        self.assertEqual(keys[keys.index("ety") + 1], "labels")
        self.assertEqual(keys[keys.index("labels") + 1], "infl")

    def test_b_in_the_address_and_the_export(self):
        table = dict(head.settings_table())
        for key, values in RULED.items():
            self.assertEqual(table[key], values)
        personal = _read(SITE, "personal.js")
        keys = re.search(r"var SETTING_KEYS = \[(.*?)\];", personal, re.S).group(1)
        for key in RULED:
            self.assertIn("'%s'" % key, keys)

    def test_c_never_a_preset_and_shown_while_acting(self):
        js = _read(SITE, "settings.js")
        self.assertIn("return shell().SETTINGS.filter(function (sp) { return sp.section === 'article' && !sp.layer; });", js)
        self.assertIn("if (sp.key === 'nbequiv') { return sh.getSetting('nbonly') === 'on'; }", js)
        self.assertIn("return sh.getSetting('nbonly') === 'on' && sh.getSetting('nbequiv') === 'hidden';", js)

    def test_d_the_popup_address_carries_them(self):
        got = _js("""
page('', '/settings/', { nbonly: 'on', nbhover: 'nbdef', labels: 'no', nbicon: 'off' });
const sh = shell();
out.addr = sh.popupAddress();
console.log(JSON.stringify(out));""")
        # the table's order: `labels` after the layer's keys since it moved under Article (2026-11-03)
        self.assertEqual(got["addr"], "https://ordpar.no/bm-en/#nbonly=on&nbhover=nbdef&nbicon=off&labels=no&q={{str}}")


class TheHeadScript(unittest.TestCase):
    CASES = {
        "none": {},
        "layer": {"nbonly": "on", "defs": "en", "mini": "en", "subsenses": "en", "formulas": "en",
                  "ety": "both", "examples": "both", "peek": "on", "layout": "ordbokene", "exeye": "on"},
        "shown": {"nbonly": "on", "nbequiv": "shown", "peek": "off"},
        "shownpeek": {"nbonly": "on", "nbequiv": "shown"},
        "hover": {"nbonly": "on", "nbhover": "nbdef", "peek": "off"},
        "rows": {"nbonly": "on", "nbrows": "none"},
        "off": {"nbonly": "off", "nbhover": "nbdef", "nbrows": "none", "nbequiv": "shown"},
        "labels": {"labels": "no", "nbicon": "off"},
    }

    @classmethod
    def setUpClass(cls):
        cls.r = _js("""
const cases = %s;
for (const name in cases) {
  const h = head('', '/bm-en/24627/', cases[name]);
  const sh = shell();
  sh.applyAll();
  const after = [...document.documentElement.classList ? [] : []];
  out[name] = { head: h.classes, writes: h.writes };
}
// the shell's own drawing of the classes, from the same storage (a change made on the page)
for (const name in cases) {
  const p = page('', '/bm-en/24627/', cases[name]);
  const sh = shell();
  sh.applyAll();
  out[name].shell = [...p.cls].filter(c => ['ordpar-js', 'nightMode', 'ordpar-chrome'].indexOf(c) < 0).sort();
}
// the address starts a visit: Norwegian only for this pop-up, nothing saved (146)
const v = head('#nbonly=on&q=hus', '/bm-en/', {});
out.visit = { classes: v.classes, visit: v.visit, writes: v.writes };
console.log(JSON.stringify(out));""" % json.dumps(cls.CASES))

    def cls(self, name):
        return set(self.r[name]["head"])

    def test_a_nothing_by_default(self):
        self.assertFalse({c for c in self.cls("none") if "nbo" in c or "labels" in c or "nbicon" in c})

    def test_b_the_layer_answers_seven_settings(self):
        c = self.cls("layer")
        self.assertTrue({"ordpar-nbo", "ordpar-nbo-noeq", "ordpar-defs-no", "ordpar-examples-no",
                         "ordpar-formulas-no", "ordpar-ety-no", "ordpar-peek-off"} <= c, c)
        self.assertFalse({"ordpar-defs-en", "ordpar-mini-en", "ordpar-subsen-en", "ordpar-ety-both"} & c, c)
        # the style stays the reader's: the layout and the eye's setting kept
        self.assertTrue({"ordpar-layout-ordbokene", "ordpar-exeye-on"} <= c, c)
        self.assertEqual(self.r["layer"]["writes"], [])            # the stored values never written

    def test_c_the_equivalents_and_the_hover(self):
        self.assertIn("ordpar-peek-off", self.cls("shown"))         # shown: the reader's own hover
        self.assertNotIn("ordpar-nbo-noeq", self.cls("shown"))
        self.assertNotIn("ordpar-peek-off", self.cls("shownpeek"))
        c = self.cls("hover")
        self.assertIn("ordpar-nbo-hovnb", c)
        self.assertNotIn("ordpar-peek-off", c)                      # the layer's choice answers
        self.assertIn("ordpar-nbo-rows0", self.cls("rows"))
        self.assertIn("ordpar-peek-off", self.cls("rows"))          # the hovers' default: nothing

    def test_d_nothing_acts_while_off(self):
        self.assertFalse({c for c in self.cls("off") if "nbo" in c}, self.cls("off"))

    def test_e_labels_and_icon(self):
        self.assertTrue({"ordpar-labels-no", "ordpar-nbicon-off"} <= self.cls("labels"))
        self.assertNotIn("ordpar-nbo", self.cls("labels"))

    def test_f_the_shell_draws_the_same(self):
        for name in self.CASES:
            head_set = {c for c in self.r[name]["head"] if c != "ordpar-js" and c != "nightMode"}
            self.assertEqual(set(self.r[name]["shell"]), head_set, (name, self.r[name]))

    def test_g_the_address(self):
        self.assertIn("ordpar-nbo", self.r["visit"]["classes"])
        self.assertEqual(self.r["visit"]["visit"], {"nbonly": "on"})
        self.assertEqual(self.r["visit"]["writes"], [])


class TheShell(unittest.TestCase):

    def test_a_the_search_direction(self):
        got = _js("""
const P_SRC = require('fs').readFileSync(%s, 'utf8');
function personal() { delete globalThis.ordparPersonal; (0, eval)(P_SRC); }
page('', '/bm-en/', { nbonly: 'on', direction: 'en' }); personal();
let sh = shell();
out.hidden = sh.direction();
sh.setDirection('en', { quiet: true });
out.after = sh.direction();
out.stored = localStorage.getItem('direction');
sh.setDirection('nb', { quiet: true });
out.stored2 = localStorage.getItem('direction');
out.random = sh.equivHidden();
page('', '/bm-en/', { nbonly: 'on', nbequiv: 'shown', direction: 'en' }); personal();
sh = shell();
out.shown = sh.direction();
page('', '/bm-en/', { direction: 'en' }); personal();
sh = shell();
out.off = sh.direction();
console.log(JSON.stringify(out));""" % json.dumps(os.path.join(SITE, "personal.js")))
        self.assertEqual(got["hidden"], "nb")          # the switch hidden: the search Norwegian
        self.assertEqual(got["after"], "en")           # a shared #en= address still opens English
        self.assertEqual(got["stored"], "en")          # the stored direction never written
        self.assertEqual(got["stored2"], "en")
        self.assertTrue(got["random"])
        self.assertEqual((got["shown"], got["off"]), ("en", "en"))

    def test_b_the_visit_only(self):
        got = _js("""
const p = page('', '/bm-en/24627/', {});
head('', '/bm-en/24627/', {});
const sh = shell();
sh.visitSetting('nbonly', 'on');
out.visit = JSON.parse(sessionStorage.getItem('ordpar-visit'));
out.saved = localStorage.getItem('nbonly');
out.read = sh.getSetting('nbonly');
console.log(JSON.stringify(out));""")
        self.assertEqual(got["visit"], {"nbonly": "on"})
        self.assertIsNone(got["saved"])
        self.assertEqual(got["read"], "on")

    def test_c_the_rows_word_class(self):
        got = _js("""
const STR = %s;
function shellWith() {
  globalThis.ORDPAR_STRINGS = { en: STR };
  try { Object.defineProperty(globalThis, 'navigator', { value: { languages: ['en'] }, configurable: true, writable: true }); } catch (e) {}
  globalThis.matchMedia = undefined;
  (0, eval)(SHELL_SRC);
  return globalThis.ordparShell;
}
page('', '/bm-en/', { nbonly: 'on' });
out.nb = shellWith().posWords('NOUN');
page('', '/bm-en/', { labels: 'no' });
out.labels = shellWith().posWords('ADJ');
page('', '/bm-en/', {});
out.en = shellWith().posWords('NOUN');
out.expr = shellWith().posWords('EXPR');
console.log(JSON.stringify(out));""" % json.dumps(STRINGS))
        self.assertEqual((got["nb"], got["labels"], got["en"], got["expr"]),
                         ("substantiv", "adjektiv", "noun", ""))


class TheWords(unittest.TestCase):

    def test_a_every_setting_has_its_words(self):
        for key, values in RULED.items():
            self.assertTrue(STRINGS.get("settings." + key), key)
            for v in values:
                self.assertTrue(STRINGS.get("settings.%s.%s" % (key, v)), (key, v))
        for k in ("settings.sub.nbonly", "settings.nbonly.hint", "settings.labels.hint",
                  "settings.nbicon.hint", "nbo.iconOn", "nbo.iconOff"):
            self.assertTrue(STRINGS.get(k), k)
        # true about the text (standing: state only true things): never "identical"
        for k, v in STRINGS.items():
            if k.startswith(("settings.nb", "settings.labels", "settings.sub.nbonly", "nbo.")):
                self.assertNotIn("identical", v.lower(), k)
        self.assertNotIn("only this page switches it", STRINGS["settings.nbicon.hint"])

    def test_b_a_norwegian_word_class_for_every_code(self):
        codes = [k[4:] for k in STRINGS if k.startswith("pos.") and not k.startswith("pos.nb.")]
        for c in codes:
            self.assertTrue(STRINGS.get("pos.nb." + c), c)
        self.assertEqual((STRINGS["pos.nb.NOUN"], STRINGS["pos.nb.ADJ"], STRINGS["pos.nb.VERB"]),
                         ("substantiv", "adjektiv", "verb"))       # ordbokene's own words

    def test_c_the_labels(self):
        self.assertEqual([article.NB_LABELS[k] for k in ("Pronunciation", "Etymology",
                          "Senses and Example Sentences", "Set phrases", "Inflection")],
                         ["Uttale", "Opphav", "Betydning og bruk", "Faste uttrykk", "Vis bøyning"])
        self.assertNotIn("Bøying", json.dumps(article.NB_LABELS, ensure_ascii=False))
        NB = strings_mod.NB
        self.assertEqual(NB["example_heading"], "Eksempel")
        # the card foot's words are the interface's, English until 1.0.0 (Robin, 2026-11-03)
        for k in ("copy_link", "copy_done", "share"):
            self.assertNotIn(k, NB)
        for k in NB:
            self.assertIn(k.split(".")[0] if k.startswith("change") else k,
                          list(strings_mod.EN) + ["change"], k)

    def test_d_the_word_class_in_norwegian(self):
        self.assertEqual(article.nb_pos("noun"), "substantiv")
        self.assertEqual(article.nb_pos("masculine, feminine or neuter"), "hankjønn, hunkjønn eller intetkjønn")
        self.assertEqual(article.nb_pos("proper noun"), "egennavn")
        self.assertIsNone(article.nb_pos("noun of some kind"))


class TheSnipFormat(unittest.TestCase):
    HEADS = {"h": {"hus": [1, 2], "huske": [3]}}
    SNIPS = {1: ("a house · a building", "en", None, 1, "bygning til å bo i"),
             2: ("liten bygning", "nb"),
             3: ("to remember", "en")}

    def test_a_n_in_the_file(self):
        out, _missing, _mis = BI.snippet_files(self.HEADS, self.SNIPS, [1, 3])
        hus = out["h-u-s"]
        self.assertEqual(hus["_n"], {"1": "bygning til å bo i", "3": ""})   # 3: translated, none
        self.assertEqual(hus["2"], "liten bygning")
        out2, _m, _x = BI.snippet_files(self.HEADS, self.SNIPS, [])
        self.assertEqual(out2["h-u-s"]["_n"], {})                            # none translated

    def test_b_norwegian_definitions_kept_whole(self):
        # site decisions 185 (Robin, 2026-11-12: "I can't imagine that there are any definitions
        # that are so long that it makes sense to cut them off"): the hover shows a Norwegian
        # definition whole, so the snip/ files keep every Norwegian line uncut (a translated
        # article's "_n", an untranslated article's own line); an English row line is still cut,
        # since only the one-line rows read it
        long_nb = ("ord " * 40).strip()
        long_en = ("word " * 40).strip()
        out, _m, _x = BI.snippet_files({"h": {"hus": [1, 2]}},
                                       {1: (long_en, "en", None, 0, long_nb), 2: (long_nb, "nb")}, [1])
        self.assertEqual(out["h-u-s"]["_n"]["1"], long_nb)
        self.assertEqual(out["h-u-s"]["2"], long_nb)
        self.assertEqual(out["h-u-s"]["1"], BI.snippet_text(long_en))

    def test_c_the_build_leaves_a_fifth_element(self):
        import build_site as BS
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "s.json")
            pages = [(1, {"snippet": ("a house", "en"), "drop": None, "gloss": True, "nbsnip": "bygning"}, 0),
                     (2, {"snippet": ("a phrase", "en"), "drop": "box", "gloss": False, "nbsnip": "uttrykk"}, 0),
                     (3, {"snippet": ("noe", "nb"), "drop": None, "gloss": False, "nbsnip": ""}, 0),
                     (4, {"snippet": ("a word", "en"), "drop": None, "gloss": False, "nbsnip": "ord"}, 0)]
            BS.write_snippets(path, pages, True)
            got = json.load(open(path, encoding="utf-8"))
            self.assertEqual(got["1"], ["a house", "en", None, 1, "bygning"])
            self.assertEqual(got["2"], ["a phrase", "en", "box", 0, "uttrykk"])
            self.assertEqual(got["3"], ["noe", "nb"])
            self.assertEqual(got["4"], ["a word", "en", None, 0, "ord"])
            self.assertEqual(BI.read_snippets(path)[4], ("a word", "en", None, 0, "ord"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_d_lookup_reads_it(self):
        got = T146._run("""
const L = require(%s).ordparLookup;
const f = { "1": "a house · a building", "2": "liten bygning", "3": "to remember",
            "_n": { "1": "bygning til å bo i", "3": "" }, "_g": [1], "_d": { "3": "x" }, "_h": { "hus": 1 } };
const old = { "1": "a house", "2": "liten bygning" };
const out = { n1: L.nbDef(f, 1), n2: L.nbDef(f, '2'), n3: L.nbDef(f, 3), old1: L.nbDef(old, 1), old2: L.nbDef(old, 2) };
globalThis.ordparShell = { layer: () => ({ on: true, hidden: true, rows: 'nbdef', hover: 'none' }) };
const v = L.rowView(f);
out.view = Object.assign({}, v);
globalThis.ordparShell = { layer: () => ({ on: true, hidden: true, rows: 'none', hover: 'none' }) };
out.same = L.rowView(f) === f;
console.log(JSON.stringify(out));""" % json.dumps(os.path.join(SITE, "lookup.js")))
        self.assertEqual((got["n1"], got["n2"], got["n3"]), ("bygning til å bo i", "liten bygning", ""))
        self.assertEqual((got["old1"], got["old2"]), ("", ""))    # a file before 152: never the English
        self.assertEqual(got["view"], {"1": "bygning til å bo i", "2": "liten bygning",
                                       "_h": {"hus": 1}, "_n": {"1": "bygning til å bo i", "3": ""}})
        self.assertTrue(got["same"])


class NoSnippet(unittest.TestCase):
    """Site decisions 154's rule for every new hidden copy: the copy the default hides carries
    `data-nosnippet` from its making (here: the Norwegian one)."""

    def test_a_python_markup(self):
        self.assertEqual(article.label_pair("Etymology", "Opphav"),
                         '<span class="ordpar-l-en">Etymology</span>'
                         '<span class="ordpar-l-nb" lang="nb" data-nosnippet>Opphav</span>')
        article._SITE[0] = True
        try:
            self.assertEqual(article.pos_html("noun (neuter)"),
                             '<span class="ordpar-w-en">noun <i>neuter</i></span>'
                             '<span class="ordpar-w-nb" lang="nb" data-nosnippet>substantiv <i>intetkjønn</i></span>')
            self.assertEqual(article.site_label("Set phrases"), article.label_pair("Set phrases", "Faste uttrykk"))
        finally:
            article._SITE[0] = False
        s = {"pos.NOUN": "noun", "pos.nb.NOUN": "substantiv"}
        self.assertIn('<span class="ordpar-w-nb" lang="nb" data-nosnippet>substantiv</span>',
                      wordpages.pos_html("NOUN", s))
        row = wordpages._snip_span("ordpar-row-snippet", {"translated": True},
                                   lambda a: ("a house", True, "bygning"))
        self.assertIn('<span class="ordpar-row-snippet ordpar-nbsnip" lang="nb" data-nosnippet>bygning</span>', row)
        notice = corrections.notice_html(5, [("typo", 1)], page.chrome_strings(strings_mod.EN))
        self.assertEqual(notice.count('class="ordpar-l-nb" lang="nb" data-nosnippet'), 2)

    def test_b_scripts(self):
        js = page.PAGE_JS
        self.assertIn("var b=d.createElement('span');b.className='ordpar-l-nb';b.lang='nb';"
                      "b.setAttribute('data-nosnippet','');", js)
        mini = _read(SITE, "mini.js")
        self.assertIn("p.setAttribute('data-nosnippet', '');          // site decisions 154: at the making", mini)
        got = T146._run("""
const fs = require('fs');
class N { constructor(t) { this.tagName = t.toUpperCase(); this.attrs = {}; this.children = []; this.text = ''; }
  setAttribute(k, v) { this.attrs[k] = v; } getAttribute(k) { return this.attrs[k]; }
  appendChild(c) { this.children.push(c); return c; } insertBefore(c) { this.children.push(c); return c; }
  get childNodes() { return this.children; } querySelectorAll() { return []; } querySelector() { return null; } }
globalThis.window = globalThis;
globalThis.document = { createElement: t => new N(t), createTextNode: x => ({ nodeType: 3, text: x }),
  addEventListener() {}, readyState: 'loading' };
(0, eval)(fs.readFileSync(%s, 'utf8'));
const R = window.ordparInflection;
const spans = [];
function walk(n) { if (!n || !n.children) return; if (n.attrs && /ordpar-w-nb/.test(n.attrs.class || '')) spans.push(n.attrs); n.children.forEach(walk); }
walk(R.render([{ lemma: 'hus', paradigm_info: [{ tags: ['NOUN', 'Neuter'], inflection: [
  { tags: ['Sing', 'Ind'], word_form: 'hus' }, { tags: ['Sing', 'Def'], word_form: 'huset' },
  { tags: ['Plur', 'Ind'], word_form: 'hus' }, { tags: ['Plur', 'Def'], word_form: 'husa' }] }] }]));
const english = [];
walk2(R.render([{ lemma: 'hus', paradigm_info: [{ tags: ['NOUN', 'Neuter'], inflection: [
  { tags: ['Sing', 'Ind'], word_form: 'hus' }] }] }], {}));
function walk2(n) { if (!n || !n.children) return; if (n.attrs && /ordpar-w-/.test(n.attrs.class || '')) english.push(1); n.children.forEach(walk2); }
console.log(JSON.stringify({ n: spans.length, all: spans.every(a => a['data-nosnippet'] === '' && a.lang === 'nb'), plain: english.length }));
""" % json.dumps(os.path.join(SITE, "inflection.js")))
        self.assertGreater(got["n"], 0)
        self.assertTrue(got["all"])
        self.assertEqual(got["plain"], 0)          # a caller's own strings: the words once


class TheFormLabels(unittest.TestCase):
    """The inflected-form rows' labels ("plural indefinite") are the tables' words: in Norwegian too
    (`wordpages.FormLabels.label_nb`, `labels.json`'s `"_nb"`, `lookup.js` `labelNb`), a number's
    definiteness first since 152's follow-up ("ubestemt form flertall"; every code:
    `test_ordpar_nblabels152.py`)."""

    def test_a_the_words(self):
        L = wordpages.FormLabels()
        self.assertEqual(L.label_nb({"Plur+Ind"}), "ubestemt form flertall")   # 152 follow-up: the Norwegian order
        self.assertEqual(L.label_nb({"Imp"}), "imperativ")
        self.assertEqual(L.label_nb({"Inf+Pass"}), "passiv infinitiv")
        self.assertEqual(L.label_nb({"Adj+<PerfPart>+Masc/Fem+Ind+Sing", "Adj+<PerfPart>+Neuter+Ind+Sing"}),
                         "perfektum partisipp hankjønn / hunkjønn og intetkjønn"
                         if " " in L.label({"Adj+<PerfPart>+Masc/Fem+Ind+Sing"}) else
                         "perfektum partisipp hankjønn / hunkjønn og intetkjønn")
        L.assign([{"Plur+Ind"}, {"Plur+Ind"}, {"Imp"}])
        self.assertEqual(L.table(), {"A": "plural indefinite", "B": "imperative"})
        self.assertEqual(L.table_nb(), {"A": "ubestemt form flertall", "B": "imperativ"})

    def test_b_the_built_row(self):
        h = wordpages.form_label_html("plural indefinite", "ubestemt form flertall")
        self.assertEqual(h, '<span class="ordpar-form-label"><span class="ordpar-w-en">(plural indefinite)</span>'
                            '<span class="ordpar-w-nb" lang="nb" data-nosnippet>(ubestemt form flertall)</span></span>')
        self.assertEqual(wordpages.form_label_html("x"), '<span class="ordpar-form-label">(x)</span>')

    def test_c_the_script(self):
        js = _read(SITE, "lookup.js")
        self.assertIn("a.labelNb = (c && table && table._nb && table._nb[c]) || '';", js)
        self.assertIn("var fl = li.appendChild(el('span', 'ordpar-form-label', '(' + (nbl ? a.labelNb : a.label) + ')'));", js)


class TheDescription(unittest.TestCase):
    """The gate on the full build (2026-10-31): the description's harvest (`describe.definitions`)
    found the senses' section by its heading's bare text, which is a label pair on a site page; it
    found no definitions, so *abstrakt* 98 lost its "Definition: …" and glossless pages fell back to
    an uncapped text. The harvest reads the pair as the bare heading."""

    BODY = ('\n    <div id="def2"><span class="ordpar-pair"><span class="ordbok-def" lang="nb">uhåndgripelig</span>\n'
            '<span class="ordbok-def" lang="en">which can only be grasped by thought</span></span></div>\n  </section>')

    def test_the_pair_is_the_heading(self):
        from sitegen import describe
        plain = '<section class="ordbok-sec">\n    <h3 lang="en">Senses and Example Sentences</h3>' + self.BODY
        pair = ('<section class="ordbok-sec">\n    <h3 lang="en">%s</h3>'
                % article.label_pair("Senses and Example Sentences", "Betydning og bruk")) + self.BODY
        want = describe.definitions(plain, True)
        self.assertTrue(want)
        self.assertEqual(describe.definitions(pair, True), want)
        article._SITE[0] = True
        try:
            self.assertEqual(article.site_label("Senses and Example Sentences"),
                             article.label_pair("Senses and Example Sentences", "Betydning og bruk"))
        finally:
            article._SITE[0] = False


class TheDeckUntouched(unittest.TestCase):

    def test_outside_a_site_page(self):
        self.assertFalse(article._SITE[0])
        self.assertEqual(article.pos_html("noun (neuter)"), "noun <i>neuter</i>")
        self.assertEqual(article.site_label("Etymology"), "Etymology")
        from sitegen import face
        link = face._link("/bm-en/5/", "hus", "house", "en")
        self.assertNotIn("data-s=", link)
        self.assertIn('data-s="h-u-s"', face._link("/bm-en/5/", "hus", "house", "en", skey="h-u-s"))


class TheSheetAndPages(unittest.TestCase):

    def test_a_the_layer_rules(self):
        css = page.SITE_CSS
        for rule in ("html.ordpar-nbo .ordpar-encue,html.ordpar-nbo .ordpar-exeye,html.ordpar-nbo .ordbok-idiom,",
                     "html.ordpar-nbo .ordpar-pair>span[lang=en],html.ordpar-nbo .mini-pair>span[lang=en],",
                     "html.ordpar-nbo-noeq .ordpar-gloss,html.ordpar-nbo-noeq .mini-gloss,",
                     "html.ordpar-nbo-hovnb .ordbok-xpeek:not(.ordpar-nbpk){display:none!important}",
                     ".ordpar-l-nb,.ordpar-w-nb{display:none}",
                     ".ordpar-nbhw{display:none;float:right;"):
            self.assertIn(rule, css)
        self.assertNotIn(".ordbok-added", css[css.index("SITE DECISIONS 152"):css.index("THE LABELS")])
        shell_css = _read(SITE, "shell.css")
        self.assertIn("html.ordpar-nbo-noeq .ordpar-switch { display: none !important; }", shell_css)
        self.assertIn("html.ordpar-nbicon-off .ordpar-nbo-icon { display: none !important; }", shell_css)

    def test_b_more_and_help(self):
        more = _read(ORDPAR, "more.md")
        self.assertIn("`.ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; } "
                      ".ordpar-nbhw { display: inline-flex !important; }`", more)
        self.assertIn("paste the line again to get the button", more)
        help_md = _read(ORDPAR, "help.md")
        self.assertIn("**Norwegian only.**", help_md)
        self.assertIn("**Labels in Norwegian.**", help_md)
        self.assertIn("Random word are Norwegian", help_md)


if __name__ == "__main__":
    unittest.main()
