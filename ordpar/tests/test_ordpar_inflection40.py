# -*- coding: utf-8 -*-
"""Pins the inflection table's decisions-40 rules (`ordpar/site/inflection.js`, as recommended:
ordbokene's own behaviour, checked on its live tables on 2026-10-18):

* (g) Two paradigms of one lemma share a row or stay apart as ordbokene's live tables show,
  compared over the lemma's whole paradigm (hidden passives
  included), with the equal cells spanning in every table of the lemma — *geranium* (definite
  singular: two rows), *mange* (comparative: two rows in both tables), *lykkes* (an s-passive's
  perfect participle), *anse* (only the hidden passive differs: two rows, all cells spanning),
  *liten* (eight paradigms, one row), *hus* (one row, a joined cell).
* (d) The forms inside a joined cell are alphabetical in Norwegian collation (*lita, liten*;
  *anga, angav*), never the data's order.
* Row order inside a lemma: alphabetical by the forms, read in the paradigm's own cell order —
  *rådgi*'s rådgav row (passive rådgies) before its rådga, rådgav row (rådgis). The collation of
  rows and lemmas is ordbokene's (æ as "ae", ø as o, å as a), each cell compared by its first
  form (Robin, 2026-11-02, code provenance decisions 9: follow ordbokene; class `RowOrder`).
* (c) No imperative for a `VERB_sPass` paradigm (*finnes*), though the form still keeps
  finnes's two paradigms apart.
* (b) The comparable adverb (*ofte*) has positive / comparative / superlative with no "degrees of
  comparison" header, wide and narrow; the adjective's comparison table keeps its header.
* Question 9 (as ordbokene does it): every variant of a joined cell carries its
  own frame — *avvæpne* "avvæpn!, avvæpne!" wide and narrow, *angripe* "angrepen + noun, angrepet
  + noun" — while the narrow participle cells stay bare.
* The narrow layout's shorter headers (2026-10-19, "follow ordbokene"): "indefinite" /
  "definite" and "masculine/ feminine" narrow, "indefinite form" and "masculine / feminine" wide.
* Question 10 (same ruling): the narrow layout is ONE table per paradigm family, the wide tables'
  sections stacked inside it (*mange*: plural, then degrees of comparison; *angripe*: the tenses,
  perfect participle, present participle).

Every expected table was compared with ordbokene's live table (headless Edge, 2026-10-18,
`docs/sessions/2026-09-19-ordpar-site-review/evidence/inflection-40-2026-10-18/`). The data is
`ordpar/test/paradigms.json` (verbatim mirror extracts, in the repo) plus a few paradigms
written out below from the mirror; no mirror file is read. The renderer runs in `bun` (or
`node`) under a minimal stand-in for `document`; without either the tests are skipped.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
JS = os.path.join(ROOT, "ordpar", "site", "inflection.js")
FIXTURE = os.path.join(ROOT, "ordpar", "test", "paradigms.json")

HARNESS = r"""
const fs = require('fs');
function Node(tag) { this.tag = tag; this.attrs = {}; this.children = []; }
Node.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
Node.prototype.getAttribute = function (k) { return this.attrs[k] === undefined ? null : this.attrs[k]; };
Node.prototype.appendChild = function (c) { this.children.push(c); return c; };
function Text(t) { this.text = t; }
const document = { createElement: (t) => new Node(t), createTextNode: (t) => new Text(t),
                   readyState: 'complete', querySelectorAll: () => [] };
const win = { document };
new Function('window', fs.readFileSync(process.argv[2], 'utf8'))(win);
const R = win.ordparInflection;
const text = (n) => n instanceof Text ? n.text : n.children.map(text).join('');
function find(n, tag, out) {
  if (n instanceof Text) return out;
  if (n.tag === tag) out.push(n);
  n.children.forEach((c) => find(c, tag, out));
  return out;
}
function grid(lemmas, layout) {
  const out = [];
  R.render(lemmas, {}).children.filter((w) => w.attrs.class.includes('--' + layout)).forEach((w) => {
    find(w, 'table', []).forEach((t) => {
      const rows = [];
      find(t, 'tr', []).forEach((tr) => {
        const cells = tr.children.filter((c) => c.tag === 'th' || c.tag === 'td').map((c) => {
          let span = '';
          ['rowspan', 'colspan'].forEach((k) => { if (c.attrs[k]) span += ' ' + k + '=' + c.attrs[k]; });
          return c.tag + span + ':' + text(c).replace(/\s+/g, ' ').trim();
        });
        if (cells.length) rows.push(cells.join(' | '));
      });
      out.push(rows);
    });
  });
  return out;
}
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const res = {};
for (const name in cases) res[name] = { wide: grid(cases[name], 'wide'), narrow: grid(cases[name], 'narrow') };
process.stdout.write(JSON.stringify(res));
"""


def par(group, cells, tags=("VERB",)):
    return {"inflection_group": group, "standardisation": "STANDARD", "tags": list(tags), "to": None,
            "inflection": [{"tags": t.split("+"), "word_form": f} for t, f in cells]}


def verb(inf, pres, past, perf, imp, pass_, mf, nt, df, pl, prp):
    return par("VERB_regular", [
        ("Inf", inf), ("Pres", pres), ("Inf+Pass", pass_), ("Pres+Pass", pass_), ("Past", past),
        ("<PerfPart>", perf), ("Adj+<PerfPart>+Neuter+Ind+Sing", nt),
        ("Adj+<PerfPart>+Masc/Fem+Ind+Sing", mf), ("Adj+<PerfPart>+Def+Sing", df),
        ("Adj+<PerfPart>+Plur", pl), ("Adj+<PresPart>", prp), ("Imp", imp)])


def noun(gender, si, sd, pi, pd):
    return par("NOUN_regular", [("Sing+Ind", si), ("Sing+Def", sd), ("Plur+Ind", pi), ("Plur+Def", pd)],
               tags=("NOUN", gender))


# Written out from the mirror (bm-articles.jsonl, 2026-10-18), in the data's paradigm order.
EXTRA = {
    "geranium": [{"lemma": "geranium", "paradigm_info": [
        noun("Masc", "geranium", "geraniumen", "geranier", "geraniene"),
        noun("Masc", "geranium", "geranien", "geranier", "geraniene")]}],
    "angi": [{"lemma": "angi", "paradigm_info": [
        verb("angi", "angir", "angav", "angitt", "angi", "angis", "angitt", "angitt", "angitte", "angitte", "angiende"),
        verb("angi", "angir", "anga", "angitt", "angi", "angis", "angitt", "angitt", "angitte", "angitte", "angiende")]}],
    "lykkes": [{"lemma": "lykkes", "paradigm_info": [
        par("VERB_sPass", [("Inf+<SPass>", "lykkes"), ("Pres+<SPass>", "lykkes"), ("Past+<SPass>", "lyktes"),
                           ("<PerfPart>+<SPass>", "lykkes"), ("Imp+<SPass>", "lykkes")]),
        par("VERB_sPass", [("Inf+<SPass>", "lykkes"), ("Pres+<SPass>", "lykkes"), ("Past+<SPass>", "lyktes"),
                           ("<PerfPart>+<SPass>", "lyktes"), ("Imp+<SPass>", "lykkes")])]}],
    "anse": [{"lemma": "anse", "paradigm_info": [
        verb("anse", "anser", "anså", "ansett", "anse", "anses", "ansett", "ansett", "ansette", "ansette", "anseende"),
        verb("anse", "anser", "anså", "ansett", "anse", "ansees", "ansett", "ansett", "ansette", "ansette", "anseende")]}],
    "rådgi": [{"lemma": "rådgi", "paradigm_info": [
        verb("rådgi", "rådgir", "rådgav", "rådgitt", "rådgi", "rådgis", "rådgitt", "rådgitt", "rådgitte", "rådgitte", "rådgiende"),
        verb("rådgi", "rådgir", "rådgav", "rådgitt", "rådgi", "rådgies", "rådgitt", "rådgitt", "rådgitte", "rådgitte", "rådgivende"),
        verb("rådgi", "rådgir", "rådga", "rådgitt", "rådgi", "rådgis", "rådgitt", "rådgitt", "rådgitte", "rådgitte", "rådgiende")]}],
}

def _avvaepne(past, df, imp):
    t = "avvæpnet" if past == "avvæpnet" else "avvæpna"
    return verb("avvæpne", "avvæpner", past, past, imp, "avvæpnes", t, t, df, df, "avvæpnende")


def _angripe(past, mf):
    return verb("angripe", "angriper", past, "angrepet", "angrip", "angripes", mf, "angrepet",
                "angrepne", "angrepne", "angripende")


# avvæpne 3978 (six paradigms) and angripe 1830 (four), from the mirror, in the data's order
EXTRA["avvæpne"] = [{"lemma": "avvæpne", "paradigm_info": [
    _avvaepne("avvæpna", "avvæpna", "avvæpn"), _avvaepne("avvæpnet", "avvæpnete", "avvæpn"),
    _avvaepne("avvæpna", "avvæpna", "avvæpne"), _avvaepne("avvæpnet", "avvæpnete", "avvæpne"),
    _avvaepne("avvæpnet", "avvæpnede", "avvæpne"), _avvaepne("avvæpnet", "avvæpnede", "avvæpn")]}]
EXTRA["angripe"] = [{"lemma": "angripe", "paradigm_info": [
    _angripe("angrep", "angrepet"), _angripe("angreip", "angrepet"),
    _angripe("angrep", "angrepen"), _angripe("angreip", "angrepen")]}]

# The shared-row rule as found on ordbokene's rendered tables (2026-11-02, the blind rewrite:
# docs/sessions/2026-11-02-code-provenance/evidence/blind-rewrite/merge-rule-derived.md),
# written out from the mirror in the data's paradigm order.
def _adj(cells):
    return par("ADJ_regular", cells, tags=("ADJ",))


def _detadj(lemma, m, f, n, d, pl):
    return par("DET_adj", [("Masc+Ind+Sing", m), ("Fem+Ind+Sing", f), ("Neuter+Ind+Sing", n),
                           ("Def+Sing", d), ("Plur", pl)], tags=("DET", "Intens", "<ADJ>"))


def _spass(pres):
    return par("VERB_sPass", [("Inf+<SPass>", "trives"), ("Pres+<SPass>", pres), ("Past+<SPass>", "trivdes"),
                              ("<PerfPart>+<SPass>", "trivdes"), ("Imp+<SPass>", "trives")])


EXTRA.update({
    # bartre 4669: the indefinite and definite plural differ together: two cells, two rows
    "bartre": [{"lemma": "bartre", "paradigm_info": [
        noun("Neuter", "bartre", "bartreet", "bartre", "bartrea"),
        noun("Neuter", "bartre", "bartreet", "bartrær", "bartrærne")]}],
    # årsbudsjett 136014: the same two cells varying freely (2 x 2): one row
    "årsbudsjett": [{"lemma": "årsbudsjett", "paradigm_info": [
        noun("Neuter", "årsbudsjett", "årsbudsjettet", "årsbudsjett", "årsbudsjetta"),
        noun("Neuter", "årsbudsjett", "årsbudsjettet", "årsbudsjett", "årsbudsjettene"),
        noun("Neuter", "årsbudsjett", "årsbudsjettet", "årsbudsjetter", "årsbudsjetta"),
        noun("Neuter", "årsbudsjett", "årsbudsjettet", "årsbudsjetter", "årsbudsjettene")]}],
    # vite 68826 (present), avkle 3585 (present participle)
    "vite": [{"lemma": "vite", "paradigm_info": [
        verb("vite", "veit", "visste", "visst", "vit", "vites", "visst", "visst", "visste", "visste", "vitende"),
        verb("vite", "vet", "visste", "visst", "vit", "vites", "visst", "visst", "visste", "visste", "vitende")]}],
    "avkle": [{"lemma": "avkle", "paradigm_info": [
        verb("avkle", "avkler", "avkledde", "avkledd", "avkle", "avkles", "avkledd", "avkledd", "avkledde", "avkledde", "avkleende"),
        verb("avkle", "avkler", "avkledde", "avkledd", "avkle", "avkles", "avkledd", "avkledd", "avkledde", "avkledde", "avkledende")]}],
    # trives 62329: an s-passive's present alone differs: one row, still no imperative
    "trives": [{"lemma": "trives", "paradigm_info": [_spass("trives"), _spass("trivs")]}],
    # skjelv 53019 (an adjective's neuter); hjerteformet 23864 (definite and plural together: two rows)
    "skjelv": [{"lemma": "skjelv", "paradigm_info": [
        _adj([("Pos+Masc/Fem+Ind+Sing", "skjelv"), ("Pos+Plur", "skjelve"), ("Pos+Def+Sing", "skjelve"), ("Pos+Neuter+Ind+Sing", "skjelv")]),
        _adj([("Pos+Masc/Fem+Ind+Sing", "skjelv"), ("Pos+Plur", "skjelve"), ("Pos+Def+Sing", "skjelve"), ("Pos+Neuter+Ind+Sing", "skjelvt")])]}],
    "hjerteformet": [{"lemma": "hjerteformet", "paradigm_info": [
        _adj([("Pos+Masc/Fem+Ind+Sing", "hjerteformet"), ("Pos+Plur", "hjerteformete"), ("Pos+Def+Sing", "hjerteformete"), ("Pos+Neuter+Ind+Sing", "hjerteformet")]),
        _adj([("Pos+Masc/Fem+Ind+Sing", "hjerteformet"), ("Pos+Plur", "hjerteformede"), ("Pos+Def+Sing", "hjerteformede"), ("Pos+Neuter+Ind+Sing", "hjerteformet")])]}],
    # selv / sjøl 50629: the determiner's plural alone differs, yet two rows
    "sjøl": [{"lemma": "selv", "paradigm_info": [_detadj("selv", "selv", "selv", "selv", "selve", "selv")]},
             {"lemma": "sjøl", "paradigm_info": [_detadj("sjøl", "sjøl", "sjøl", "sjøl", "sjølve", "sjøl"),
                                                 _detadj("sjøl", "sjøl", "sjøl", "sjøl", "sjølve", "sjølve")]}],
    # han 22170: the object form
    "han": [{"lemma": "han", "paradigm_info": [
        par("PRON_regular", [("Nom", "han"), ("Acc", "ham")], tags=("PRON", "Prs", "3", "Sing", "Masc", "Hum")),
        par("PRON_regular", [("Nom", "han"), ("Acc", "han")], tags=("PRON", "Prs", "3", "Sing", "Masc", "Hum"))]}],
})

# The row order (Robin, 2026-11-02, code provenance decisions 9: follow ordbokene), written out
# from the mirror in the data's paradigm and lemma order; each expected table is ordbokene's
# rendered one (headless Edge, 2026-11-02: docs/sessions/2026-11-02-code-provenance/evidence/
# blind-rewrite/evidence/obk_fresh.json and obk1-3.json).
def _klype(past, perf, mf, df):
    return verb("klype", "klyper", past, perf, "klyp", "klypes", mf, perf, df, df, "klypende")


def _tra(past, perf, df):
    return verb("trå", "trår", past, perf, "trå", "trås", perf, perf, df, df, "trående")


def _gyve(past, perf, mf, df):
    return verb("gyve", "gyver", past, perf, "gyv", "gyves", mf, perf, df, df, "gyvende")


EXTRA.update({
    # pæretre 47022: the pæretrær row first (ae sorts before e)
    "pæretre": [{"lemma": "pæretre", "paradigm_info": [
        noun("Neuter", "pæretre", "pæretreet", "pæretre", "pæretrea"),
        noun("Neuter", "pæretre", "pæretreet", "pæretrær", "pæretrærne")]}],
    # klype 30323: kløyp / kløpet before kløyp / klypt (ø as o, before y)
    "klype": [{"lemma": "klype", "paradigm_info": [
        _klype("kløyp", "klypt", "klypt", "klypte"), _klype("kløyp", "kløpet", "kløpen", "kløpne"),
        _klype("kløp", "kløpet", "kløpet", "kløpne"), _klype("kløp", "kløpet", "kløpen", "kløpne")]}],
    # trå / trø 62692: two lemmas, trå's rows first (å as a, before ø as o)
    "trå": [{"lemma": "trå", "paradigm_info": [
        _tra("trådde", "trådd", "trådde"), _tra("tro", "trådd", "trådde"), _tra("trådte", "trådt", "trådte")]},
        {"lemma": "trø", "paradigm_info": [
            verb("trø", "trør", "trødde", "trødd", "trø", "trøs", "trødd", "trødd", "trødde", "trødde", "trøende")]}],
    # gyve 21723: each cell compared by its FIRST form — the gjøv, gøyv row before the gjøv row
    "gyve": [{"lemma": "gyve", "paradigm_info": [
        _gyve("gjøv", "gjøvet", "gjøvet", "gjøvne"), _gyve("gjøv", "gjøvet", "gjøven", "gjøvne"),
        _gyve("gjøv", "gyvd", "gyvd", "gyvd"), _gyve("gøyv", "gjøvet", "gjøvet", "gjøvne"),
        _gyve("gøyv", "gjøvet", "gjøven", "gjøvne"), _gyve("gøyv", "gyvd", "gyvd", "gyvde")]}],
})

# Site decisions 162 (1) (Robin, 2026-11-04): an adjective with one paradigm that has comparison
# forms and one that has none, written out from the mirror (2026-11-03) in the data's order —
# the mirror's comparison-less paradigm carries three untagged cells with no form (`_NOCMP`).
_NOCMP = [("", None)] * 3


def _adjpos(m, n, d, pl, cmp=None):
    tail = [("Cmp", cmp[0]), ("Sup+Ind", cmp[1]), ("Sup+Def", cmp[2])] if cmp else _NOCMP
    return _adj([("Pos+Masc/Fem+Ind+Sing", m), ("Pos+Plur", pl), ("Pos+Def+Sing", d),
                 ("Pos+Neuter+Ind+Sing", n)] + tail)


EXTRA.update({
    # avsindig 3768: two paradigms, equal positives, comparison forms in the first only
    "avsindig": [{"lemma": "avsindig", "paradigm_info": [
        _adjpos("avsindig", "avsindig", "avsindige", "avsindige", ("avsindigere", "avsindigst", "avsindigste")),
        _adjpos("avsindig", "avsindig", "avsindige", "avsindige")]}],
    # kjærlighetsløs, kjærlighetslaus 119179: three paradigms, comparison forms in one
    "kjærlighetslaus": [
        {"lemma": "kjærlighetsløs", "paradigm_info": [
            _adjpos("kjærlighetsløs", "kjærlighetsløst", "kjærlighetsløse", "kjærlighetsløse")]},
        {"lemma": "kjærlighetslaus", "paradigm_info": [
            _adjpos("kjærlighetslaus", "kjærlighetslaust", "kjærlighetslause", "kjærlighetslause",
                    ("kjærlighetslausere", "kjærlighetslausest", "kjærlighetslauseste")),
            _adjpos("kjærlighetslaus", "kjærlighetslaust", "kjærlighetslause", "kjærlighetslause")]}],
    # no paradigm with comparison forms (a constructed pair): no comparison table at all, as before
    "nocmp": [{"lemma": "avsindig", "paradigm_info": [
        _adjpos("avsindig", "avsindig", "avsindige", "avsindige"),
        _adjpos("avsindig", "avsindig", "avsindige", "avsindige")]}],
})

FROM_FIXTURE = {"liten": 35408, "mange": 36844, "finnes": 14771, "ofte": 41859, "hus": 24627, "bra": 7217}


class InflectionDecisions40(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runner = shutil.which("bun") or shutil.which("node")
        if not runner:
            raise unittest.SkipTest("no bun/node on PATH")
        with open(FIXTURE, encoding="utf-8") as fh:
            arts = {a["id"]: a["lemmas"] for a in json.load(fh)["articles"]}
        cases = dict(EXTRA)
        for name, aid in FROM_FIXTURE.items():
            cases[name] = arts[aid]
        tmp = tempfile.mkdtemp()
        try:
            h, c = os.path.join(tmp, "h.js"), os.path.join(tmp, "cases.json")
            with open(h, "w", encoding="utf-8") as fh:
                fh.write(HARNESS)
            with open(c, "w", encoding="utf-8") as fh:
                json.dump(cases, fh, ensure_ascii=False)
            res = subprocess.run([runner, h, JS, c], capture_output=True, timeout=60)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        cls.out = json.loads(res.stdout.decode("utf-8"))

    def body(self, name, table=0, layout="wide"):
        return [r for r in self.out[name][layout][table] if r.startswith("td") or " | td" in r]

    # (g) -------------------------------------------------------------------------------------
    def test_definite_singular_is_two_rows(self):
        self.assertEqual(self.body("geranium"), [
            "td rowspan=2:en geranium | td:geranien | td rowspan=2:geranier | td rowspan=2:geraniene",
            "td:geraniumen"])

    def test_comparative_split_shows_in_both_tables(self):
        self.assertEqual(self.body("mange", 0), ["td rowspan=2:mange"])
        self.assertEqual(self.body("mange", 1), ["td:fler | td rowspan=2:flest | td rowspan=2:fleste", "td:flere"])
        # narrow: the same spans, read across, in the one narrow table
        self.assertIn("th:comparative | td:fler | td:flere", self.out["mange"]["narrow"][0])

    def test_spassive_perfect_participle_is_two_rows(self):
        self.assertEqual(self.body("lykkes"), [
            "td rowspan=2:å lykkes | td rowspan=2:lykkes | td rowspan=2:lyktes | td:har lykkes",
            "td:har lyktes"])

    def test_hidden_passive_keeps_rows_apart(self):
        self.assertEqual(self.body("anse"), [
            "td rowspan=2:å anse | td rowspan=2:anser | td rowspan=2:anså | td rowspan=2:har ansett | td rowspan=2:anse!"])

    def test_liten_is_one_row(self):
        self.assertEqual(self.body("liten"), ["td:liten | td:lita, liten | td:lite, smått | td:lille, vesle | td:små"])

    def test_hus_is_one_row(self):
        self.assertEqual(self.body("hus"), ["td:et hus | td:huset | td:hus | td:husa, husene"])

    # (d) and the row order ---------------------------------------------------------------------
    def test_joined_cell_alphabetical(self):
        self.assertEqual(self.body("angi")[0].split(" | ")[2], "td:anga, angav")

    def test_row_order_reads_cells_in_paradigm_order(self):
        self.assertEqual(self.body("rådgi"), [
            "td rowspan=2:å rådgi | td rowspan=2:rådgir | td:rådgav | td rowspan=2:har rådgitt | td rowspan=2:rådgi!",
            "td:rådga, rådgav"])

    # (c) ---------------------------------------------------------------------------------------
    def test_spassive_has_no_imperative(self):
        head = self.out["finnes"]["wide"][0][0]
        self.assertEqual(head, "th:infinitive | th:present | th:past | th:present perfect")
        self.assertEqual(self.body("finnes"), [
            "td rowspan=2:å finnes | td:finnes | td rowspan=2:fantes | td rowspan=2:har funnes", "td:fins"])
        self.assertNotIn("imperative", self.out["lykkes"]["wide"][0][0])
        # an ordinary verb keeps its imperative
        self.assertIn("th:imperative", self.out["angi"]["wide"][0][0])

    # (b) ---------------------------------------------------------------------------------------
    def test_adverb_has_no_degrees_header(self):
        self.assertEqual(self.out["ofte"]["wide"], [[
            "th:positive | th:comparative | th:superlative", "td:ofte | td:oftere | td:oftest"]])
        self.assertEqual(self.out["ofte"]["narrow"], [[
            "th:positive | td:ofte", "th:comparative | td:oftere", "th:superlative | td:oftest"]])

    def test_adjective_keeps_degrees_header(self):
        self.assertEqual(self.out["mange"]["wide"][1][0], "th colspan=3:degrees of comparison")

    # questions 9 and 10 ----------------------------------------------------------------------
    def test_frame_on_every_variant(self):
        self.assertEqual(self.body("avvæpne")[0].split(" | ")[-1], "td rowspan=3:avvæpn!, avvæpne!")
        self.assertEqual(self.body("angripe", 1)[0].split(" | ")[0], "td:angrepen + noun, angrepet + noun")
        self.assertEqual(self.body("angripe")[0].split(" | ")[2], "td:angreip, angrep")
        narrow = self.out["avvæpne"]["narrow"][0]
        self.assertIn("th:imperative | td colspan=3:avvæpn!, avvæpne!", narrow)
        # the narrow participle cells stay bare
        self.assertIn("th:masculine/ feminine | td:angrepen, angrepet", self.out["angripe"]["narrow"][0])

    def test_one_narrow_table_per_family(self):
        self.assertEqual(len(self.out["angripe"]["wide"]), 2)
        self.assertEqual(self.out["angripe"]["narrow"], [[
            "th:infinitive | td:å angripe", "th:present | td:angriper", "th:past | td:angreip, angrep",
            "th:present perfect | td:har angrepet", "th:imperative | td:angrip!",
            "th colspan=2:perfect participle",
            "th:masculine/ feminine | td:angrepen, angrepet", "th:neuter | td:angrepet",
            "th:definite | td:angrepne", "th:plural | td:angrepne",
            "th colspan=2:present participle", "th:present participle | td:angripende"]])
        self.assertEqual(len(self.out["mange"]["narrow"]), 1)
        self.assertEqual(self.out["mange"]["narrow"][0][0], "th colspan=3:plural")

    def test_narrow_short_headers(self):
        # narrow: ordbokene's shorter terms (live DOM at 500 px, 2026-10-19); wide keeps "form"
        # (label and qualifier are two spans; the harness joins their text without a space)
        self.assertIn("th:superlativeindefinite | td colspan=2:flest", self.out["mange"]["narrow"][0])
        self.assertIn("th:definite | td:geranien | td:geraniumen", self.out["geranium"]["narrow"][0])
        self.assertIn("th:indefinite form", self.out["geranium"]["wide"][0][1])
        self.assertIn("superlativeindefinite form", self.out["mange"]["wide"][1][1])
        self.assertIn("th:masculine / feminine", self.out["angripe"]["wide"][1][1])  # the no-break space reads as a space here


class SharedRows(unittest.TestCase):
    """The shared-row rule beyond decisions 40's cases (the blind rewrite, 2026-11-02): each
    expected table is ordbokene's rendered one (headless Edge, 2026-11-02), except where noted."""
    setUpClass = classmethod(InflectionDecisions40.setUpClass.__func__)
    body = InflectionDecisions40.body

    def test_two_differing_cells_stay_apart(self):
        # the bartrær row first: ordbokene's row order (class RowOrder)
        self.assertEqual(self.body("bartre"), [
            "td rowspan=2:et bartre | td rowspan=2:bartreet | td:bartrær | td:bartrærne",
            "td:bartre | td:bartrea"])

    def test_free_variation_is_one_row(self):
        self.assertEqual(self.body("årsbudsjett"), [
            "td:et årsbudsjett | td:årsbudsjettet | td:årsbudsjett, årsbudsjetter | td:årsbudsjetta, årsbudsjettene"])

    def test_present_and_present_participle_join(self):
        self.assertEqual(self.body("vite"), ["td:å vite | td:veit, vet | td:visste | td:har visst | td:vit!"])
        self.assertEqual(self.body("avkle", 1)[0].split(" | ")[-1], "td:avkledende, avkleende")
        self.assertEqual(len(self.body("avkle")), 1)

    def test_spassive_present_joins_without_imperative(self):
        self.assertEqual(self.out["trives"]["wide"][0][0], "th:infinitive | th:present | th:past | th:present perfect")
        self.assertEqual(self.body("trives"), ["td:å trives | td:trives, trivs | td:trivdes | td:har trivdes"])

    def test_adjective_neuter_joins_but_definite_and_plural_do_not(self):
        self.assertEqual(self.body("skjelv"), ["td:skjelv | td:skjelv, skjelvt | td:skjelve | td:skjelve"])
        self.assertEqual(self.body("hjerteformet"), [
            "td rowspan=2:hjerteformet | td rowspan=2:hjerteformet | td:hjerteformede | td:hjerteformede",
            "td:hjerteformete | td:hjerteformete"])

    def test_determiner_plural_keeps_rows_apart(self):
        self.assertEqual(self.body("sjøl"), [
            "td:selv | td:selv | td:selv | td:selve | td:selv",
            "td rowspan=2:sjøl | td rowspan=2:sjøl | td rowspan=2:sjøl | td rowspan=2:sjølve | td:sjøl",
            "td:sjølve"])

    def test_pronoun_object_form_joins(self):
        self.assertEqual(self.body("han"), ["td:han | td:ham, han"])


class RowOrder(unittest.TestCase):
    """The order of rows and of lemmas is ordbokene's (Robin, 2026-11-02, code provenance
    decisions 9: "follow ordbokene"; it reverses site decisions 45's Norwegian collation): a
    collation in which æ sorts as "ae", ø as o and å as a, each cell compared by its first form.
    Every expected table is ordbokene's rendered one (2026-11-02)."""
    setUpClass = classmethod(InflectionDecisions40.setUpClass.__func__)
    body = InflectionDecisions40.body

    def test_tre_noun_plural_traer_first(self):
        self.assertEqual(self.body("pæretre"), [
            "td rowspan=2:et pæretre | td rowspan=2:pæretreet | td:pæretrær | td:pæretrærne",
            "td:pæretre | td:pæretrea"])
        # the narrow layout shares the row model: the same order, as columns
        narrow = self.body("pæretre", layout="narrow")
        self.assertIn("th:indefinite | td:pæretrær | td:pæretre", narrow)
        self.assertIn("th:definite | td:pæretrærne | td:pæretrea", narrow)

    def test_klype_o_slash_sorts_as_o(self):
        self.assertEqual(self.body("klype"), [
            "td rowspan=3:å klype | td rowspan=3:klyper | td:kløp | td rowspan=2:har kløpet | td rowspan=3:klyp!",
            "td rowspan=2:kløyp",
            "td:har klypt"])
        self.assertEqual(self.body("klype", 1), [
            "td:kløpen + noun, kløpet + noun | td rowspan=2:kløpet + noun | td rowspan=2:den/det kløpne + noun"
            " | td rowspan=2:kløpne + noun | td rowspan=3:klypende",
            "td:kløpen + noun",
            "td:klypt + noun | td:klypt + noun | td:den/det klypte + noun | td:klypte + noun"])

    def test_lemmas_tra_before_tro(self):
        self.assertEqual(self.body("trå"), [
            "td rowspan=2:å trå | td rowspan=2:trår | td:trådte | td:har trådt | td rowspan=2:trå!",
            "td:tro, trådde | td:har trådd",
            "td:å trø | td:trør | td:trødde | td:har trødd | td:trø!"])
        self.assertEqual(self.body("trå", layout="narrow")[0], "th:infinitive | td colspan=2:å trå | td:å trø")

    def test_cell_compared_by_first_form(self):
        self.assertEqual(self.body("gyve"), [
            "td rowspan=3:å gyve | td rowspan=3:gyver | td:gjøv, gøyv | td:har gjøvet | td rowspan=3:gyv!",
            "td:gjøv | td rowspan=2:har gyvd",
            "td:gøyv"])


class EmptyComparisonRow(unittest.TestCase):
    """Site decisions 162 (1), as recommended: a comparison row with no
    form in any of its cells is not drawn, wide or narrow, as ordbokene's rendered tables have it
    (headless Edge, 2026-11-04, `/eng/bm/3768` and `/eng/bm/119179` at 1,400 and 500 px): wide, the
    row is left out; narrow, the empty cells are left out of each comparison row and the others
    are not widened. The positive table keeps both rows. Fails on `inflection.js` before 162."""
    setUpClass = classmethod(InflectionDecisions40.setUpClass.__func__)
    body = InflectionDecisions40.body

    def test_avsindig_wide(self):
        self.assertEqual(self.body("avsindig"), [
            "td rowspan=2:avsindig | td rowspan=2:avsindig | td rowspan=2:avsindige | td rowspan=2:avsindige"])
        self.assertEqual(self.body("avsindig", 1), ["td:avsindigere | td:avsindigst | td:avsindigste"])

    def test_avsindig_narrow(self):
        rows = self.body("avsindig", layout="narrow")
        self.assertIn("th:masculine/ feminine | td colspan=2:avsindig", rows)
        self.assertEqual(rows[-3:], ["th:comparative | td:avsindigere",
                                     "th:superlativeindefinite | td:avsindigst",
                                     "th:superlativedefinite | td:avsindigste"])

    def test_kjaerlighetslaus_wide_and_narrow(self):
        self.assertEqual(self.body("kjærlighetslaus"), [
            "td rowspan=2:kjærlighetslaus | td rowspan=2:kjærlighetslaust | td rowspan=2:kjærlighetslause"
            " | td rowspan=2:kjærlighetslause",
            "td:kjærlighetsløs | td:kjærlighetsløst | td:kjærlighetsløse | td:kjærlighetsløse"])
        self.assertEqual(self.body("kjærlighetslaus", 1),
                         ["td:kjærlighetslausere | td:kjærlighetslausest | td:kjærlighetslauseste"])
        rows = self.body("kjærlighetslaus", layout="narrow")
        self.assertIn("th:neuter | td colspan=2:kjærlighetslaust | td:kjærlighetsløst", rows)
        self.assertEqual(rows[-3], "th:comparative | td:kjærlighetslausere")

    def test_no_comparison_forms_anywhere_no_table(self):
        # unchanged by 162: every comparison column is empty, so dropped (rule 3), and no table
        self.assertEqual(len(self.out["nocmp"]["wide"]), 1)
        self.assertFalse(any("comparison" in r for r in self.out["nocmp"]["narrow"][0]))


if __name__ == "__main__":
    unittest.main()
