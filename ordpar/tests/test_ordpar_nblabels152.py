"""Site decisions 152, the follow-up (Robin, 2026-10-31 and 2026-11-01): Norwegian only turns EVERY
label inside the article, and the Norwegian grammatical labels in the wording he approved — the
static half (the browser half: `test_ordpar_browser_nbonly152.py`, `test_l_the_layer_turns_every_label`).

* **The sheet** (`page.SITE_CSS`): under `ordpar-nbo` the labels' English copies (`.ordpar-l-en`) are
  hidden and their Norwegian copies (`.ordpar-l-nb`) shown, exactly as under `ordpar-labels-no`, so
  the layer turns them wherever the sheet and the layer's class are — before the first paint (the
  head script draws `ordpar-nbo`), with the stored `labels` never written.
* **The form labels' Norwegian** (`wordpages.FormLabels.label_nb`, `labels.json`'s `"_nb"`):
  definiteness, the word "form", then number, as Bokmålsordboka's own definitions write it ("i
  bestemt form entall"): "ubestemt form flertall", "bestemt form entall", "bestemt form flertall",
  "ubestemt og bestemt form flertall", "bestemt form entall og flertall" — every code of the index's
  table of 2026-10-31 checked, its English unchanged; the degrees, the participles and the gender-led
  labels as before.
* **ordbokene's three words**: "gradbøying" / "Gradbøying" (`inflection.js` `NB_STRINGS`),
  "forkorting" (`article.NB_POS_WORDS`, `strings/en.json` `pos.nb.ABBR`), "i sammensetning"
  (`pos.nb.COMPPFX`); the old words nowhere in the site's code; the compound lists' "som forledd i ord
  som" (ordbokene's own intro, 151) kept.
* **The words for Robin**: the labels setting's hint, and Help's two paragraphs, true about the layer.

Shown failing on the code before the follow-up and passing on it (the build's report). Stdlib unittest.
"""
import glob
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)

from sitegen import article, page, wordpages  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


STRINGS = json.loads(_read(SITE, "strings", "en.json"))


def _rules(css):
    """`{selector: declarations}` for every plain rule of a sheet (comments and at-rule heads
    dropped; a selector list split at its commas)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        for sel in m.group(1).split(","):
            sel = re.sub(r"\s+", " ", sel.strip())
            if sel and not sel.startswith("@"):
                out.setdefault(sel, []).append(m.group(2).replace(" ", ""))
    return out


class TheSheet(unittest.TestCase):

    def test_a_the_layer_turns_the_labels(self):
        rules = _rules(page.SITE_CSS)
        self.assertIn("display:none", rules.get("html.ordpar-nbo .ordpar-l-en", []))
        self.assertIn("display:inline", rules.get("html.ordpar-nbo .ordpar-l-nb", []))
        # the same as the labels setting's own rules, so the two can never draw them differently
        self.assertIn("display:none", rules.get("html.ordpar-labels-no .ordpar-l-en", []))
        self.assertIn("display:inline", rules.get("html.ordpar-labels-no .ordpar-l-nb", []))
        self.assertIn("display:none", rules.get(".ordpar-l-nb", []))      # hidden by default

    def test_b_the_stored_labels_never_written(self):
        # the layer's turn is the sheet's: neither the shell nor the head script writes `labels`
        shell = _read(SITE, "shell.js")
        self.assertNotRegex(shell, r"setItem\(\s*'labels'")
        self.assertNotRegex(shell, r"setSetting\(\s*'labels'")
        from sitegen import head
        self.assertNotIn("setItem('labels'", head.THEME_JS)


#: Every code of the index's `labels.json` as built on 2026-10-31: its cell keys (`wordpages.CELLS`,
#: `PASSIVES`), the English (unchanged) and the Norwegian as approved (Robin, 2026-11-01)
CODES = {
    "A": ({"Plur+Def"}, "plural definite", "bestemt form flertall"),
    "B": ({"Sing+Def"}, "singular definite", "bestemt form entall"),
    "C": ({"Plur+Ind"}, "plural indefinite", "ubestemt form flertall"),
    "D": ({"Pos+Def+Sing", "Pos+Plur"}, "singular definite, plural", "bestemt form entall og flertall"),
    "E": ({"Adj+<PerfPart>+Def+Sing", "Adj+<PerfPart>+Plur"}, "perfect participle definite and plural",
          "perfektum partisipp bestemt og flertall"),
    "F": ({"Inf+Pass", "Pres+Pass"}, "passive infinitive, passive present", "passiv infinitiv, passiv presens"),
    "G": ({"Adj+<PresPart>"}, "present participle", "presens partisipp"),
    "H": ({"Pres"}, "present", "presens"),
    "I": ({"Imp"}, "imperative", "imperativ"),
    "J": ({"Neuter+Ind+Sing"}, "singular neuter", "entall intetkjønn"),
    "K": ({"Adj+<PerfPart>+Masc/Fem+Ind+Sing", "Adj+<PerfPart>+Neuter+Ind+Sing"},
          "perfect participle masculine / feminine and neuter",
          "perfektum partisipp hankjønn / hunkjønn og intetkjønn"),
    "L": ({"Past", "Adj+<PerfPart>+Masc/Fem+Ind+Sing", "Adj+<PerfPart>+Neuter+Ind+Sing"},
          "past, perfect participle masculine / feminine and neuter",
          "preteritum, perfektum partisipp hankjønn / hunkjønn og intetkjønn"),
    "M": ({"Past", "Adj+<PerfPart>+Masc/Fem+Ind+Sing", "Adj+<PerfPart>+Neuter+Ind+Sing",
           "Adj+<PerfPart>+Def+Sing", "Adj+<PerfPart>+Plur"},
          "past, perfect participle masculine / feminine, neuter, definite and plural",
          "preteritum, perfektum partisipp hankjønn / hunkjønn, intetkjønn, bestemt og flertall"),
    "N": ({"Past", "Adj+<PerfPart>+Def+Sing", "Adj+<PerfPart>+Plur"},
          "past, perfect participle definite and plural", "preteritum, perfektum partisipp bestemt og flertall"),
    "O": ({"Sup+Def"}, "superlative definite", "superlativ bestemt"),
    "P": ({"Sup+Ind"}, "superlative indefinite", "superlativ ubestemt"),
    "Q": ({"Cmp"}, "comparative", "komparativ"),
    "R": ({"Past"}, "past", "preteritum"),
    "S": ({"Adj+<PerfPart>+Masc/Fem+Ind+Sing"}, "perfect participle masculine / feminine",
          "perfektum partisipp hankjønn / hunkjønn"),
    "T": ({"Sing+Def", "Plur+Def"}, "singular definite, plural definite", "bestemt form entall og flertall"),
    "U": ({"Pres", "Imp"}, "present, imperative", "presens, imperativ"),
    "V": ({"Past", "Imp"}, "past, imperative", "preteritum, imperativ"),
    "W": ({"Past", "<PerfPart>"}, "past, perfect participle", "preteritum, perfektum partisipp"),
    "X": ({"Fem+Ind+Sing"}, "singular feminine", "entall hunkjønn"),
    "Y": ({"Plur"}, "plural", "flertall"),
    "Z": ({"<PerfPart>"}, "perfect participle", "perfektum partisipp"),
    "a": ({"Sup"}, "superlative", "superlativ"),
    "b": ({"Acc"}, "object form", "objektsform"),
    "c": ({"Adj+<PerfPart>+Neuter+Ind+Sing"}, "perfect participle neuter", "perfektum partisipp intetkjønn"),
    "d": ({"Sing+Def", "Plur+Ind", "Plur+Def"}, "singular definite, plural indefinite and definite",
          "bestemt form entall, ubestemt og bestemt form flertall"),
    "e": ({"<PerfPart>", "Adj+<PerfPart>+Masc/Fem+Ind+Sing", "Adj+<PerfPart>+Neuter+Ind+Sing", "Imp"},
          "perfect participle masculine / feminine and neuter, imperative",
          "perfektum partisipp hankjønn / hunkjønn og intetkjønn, imperativ"),
    "f": ({"Adj+<PerfPart>+Masc/Fem+Ind+Sing", "Adj+<PerfPart>+Neuter+Ind+Sing", "Adj+<PerfPart>+Def+Sing",
           "Adj+<PerfPart>+Plur"},
          "perfect participle masculine / feminine, neuter, definite and plural",
          "perfektum partisipp hankjønn / hunkjønn, intetkjønn, bestemt og flertall"),
    "g": ({"Plur+Ind", "Plur+Def"}, "plural indefinite and definite", "ubestemt og bestemt form flertall"),
    "h": ({"Fem+Ind+Sing", "Neuter+Ind+Sing"}, "singular feminine and neuter", "entall hunkjønn og intetkjønn"),
}


class TheFormLabels(unittest.TestCase):

    def test_a_the_approved_five(self):
        L = wordpages.FormLabels()
        self.assertEqual(L.label_nb({"Plur+Ind"}), "ubestemt form flertall")
        self.assertEqual(L.label_nb({"Sing+Def"}), "bestemt form entall")
        self.assertEqual(L.label_nb({"Plur+Def"}), "bestemt form flertall")
        self.assertEqual(L.label_nb({"Plur+Ind", "Plur+Def"}), "ubestemt og bestemt form flertall")
        self.assertEqual(L.label_nb({"Pos+Def+Sing", "Pos+Plur"}), "bestemt form entall og flertall")
        self.assertEqual(L.label_nb({"Def+Sing", "Plur"}), "bestemt form entall og flertall")

    def test_b_every_code_of_the_index(self):
        L = wordpages.FormLabels()
        for code, (keys, en, nb) in CODES.items():
            self.assertEqual(L.label(keys), en, code)           # the English unchanged
            self.assertEqual(L.label_nb(keys), nb, code)

    def test_c_the_index_table(self):
        # `labels.json`: the codes handed out over the analyses, `"_nb"` each code's Norwegian
        L = wordpages.FormLabels()
        keysets = []
        for i, (keys, _en, _nb) in enumerate(CODES.values()):
            keysets += [keys] * (len(CODES) - i)                # the table's order: A most frequent
        L.assign(keysets)
        table, nb = L.table(), L.table_nb()
        self.assertEqual(sorted(nb), sorted(table))
        want = {en: n for _k, en, n in CODES.values()}
        for c, en in table.items():
            self.assertEqual(nb[c], want[en], (c, en))

    def test_d_unchanged_by_ruling(self):
        L = wordpages.FormLabels()
        self.assertEqual(L.label_nb({"Sup+Ind"}), "superlativ ubestemt")      # ordbokene's heads
        self.assertEqual(L.label_nb({"Adj+<PerfPart>+Def+Sing"}), "perfektum partisipp bestemt")
        self.assertEqual(L.label_nb({"Pos+Neuter+Ind+Sing"}), "entall intetkjønn")
        self.assertEqual(L.label_nb({"Inf+Pass"}), "passiv infinitiv")
        self.assertEqual(L.label_nb({"Sing+Ind"}), "ubestemt form entall")    # the same rule

    def test_e_the_built_row_and_the_script(self):
        h = wordpages.form_label_html("plural indefinite", wordpages.FormLabels().label_nb({"Plur+Ind"}))
        self.assertIn('<span class="ordpar-w-nb" lang="nb" data-nosnippet>(ubestemt form flertall)</span>', h)
        # `lookup.js` draws the index's words as they are: no composing of its own
        js = _read(SITE, "lookup.js")
        self.assertIn("a.labelNb = (c && table && table._nb && table._nb[c]) || '';", js)
        self.assertNotIn("flertall", js)


class TheThreeWords(unittest.TestCase):

    def test_a_where_they_are_written(self):
        nb = wordpages.table_strings(name="NB_STRINGS")
        self.assertEqual((nb["captionComparison"], nb["degreesOfComparison"]), ("Gradbøying", "gradbøying"))
        self.assertEqual(article.NB_POS_WORDS["abbreviation"], "forkorting")
        self.assertEqual(article.nb_pos("abbreviation"), "forkorting")
        self.assertEqual(STRINGS["pos.nb.ABBR"], "forkorting")
        self.assertEqual(STRINGS["pos.nb.COMPPFX"], "i sammensetning")

    def test_b_the_old_words_nowhere_in_the_code(self):
        files = (glob.glob(os.path.join(SITE, "*.js")) + glob.glob(os.path.join(SITE, "*.css"))
                 + glob.glob(os.path.join(SITE, "*.html")) + glob.glob(os.path.join(SITE, "strings", "*.json"))
                 + glob.glob(os.path.join(ORDPAR, "sitegen", "*.py")) + glob.glob(os.path.join(ORDPAR, "*.py")))
        self.assertTrue(files)
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            for old in ("gradbøyning", "forkortelse"):
                self.assertNotIn(old, text.lower(), (path, old))
            # "forledd" only in the compound lists' intro, ordbokene's own text (151)
            self.assertEqual(re.findall(r"forledd(?! i ord som)", text), [], path)

    def test_c_the_compound_intro_kept(self):
        self.assertIn('"som forledd i ord som"', _read(ORDPAR, "sitegen", "article.py"))

    def test_d_a_compound_prefix_one_word_everywhere(self):
        # Robin, 2026-11-01: "yes, it should be one word" — *kjempe-* (COMPPFX) was "prefix" /
        # "prefiks" on its article page and "compound prefix" / "i sammensetning" in the rows
        pos = article.site_pos(frozenset({"COMPPFX"}), ())
        self.assertEqual(pos, STRINGS["pos.COMPPFX"])
        self.assertEqual(article.nb_pos(pos), STRINGS["pos.nb.COMPPFX"])
        self.assertEqual(article.site_pos(frozenset({"PFX"}), ()), "prefix")   # *eks-* unchanged
        built = os.path.join(ORDPAR, "out", "bm-en", "29505", "index.html")
        if not os.path.exists(built):
            self.skipTest("no built page for kjempe- (29505)")
        self.assertIn('<span class="ordbok-pos"><span class="ordpar-w-en">compound prefix</span>'
                      '<span class="ordpar-w-nb" lang="nb" data-nosnippet>i sammensetning</span></span>',
                      _read(built))


class TheWords(unittest.TestCase):

    def test_a_the_hint(self):
        hint = STRINGS["settings.labels.hint"]
        self.assertIn('With "Norwegian only" on, they are all in Norwegian whatever this says.', hint)
        self.assertNotIn("the word class and the inflection tables are in Norwegian whatever", hint)
        self.assertTrue(hint.startswith('The headings and buttons inside an article, such as "Etymology"'))
        # Robin, 2026-11-03: the card foot's buttons are the interface's, so the example is a button
        # that turns ("Inflection"), and the foot is named among what stays English
        self.assertIn('such as "Etymology" and "Inflection",', hint)
        self.assertNotIn('"Copy link", its word class', hint)
        self.assertTrue(hint.endswith('The rest of the site stays in English, such as the header, the menus, '
                                      'Settings and the buttons at the foot of an article ("Copy link", "Share").'))

    def test_b_help(self):
        help_md = _read(ORDPAR, "help.md")
        para = re.search(r"\*\*Norwegian only\.\*\*[^\n]*", help_md).group(0)
        self.assertIn("puts the labels inside the article in Norwegian", para)
        labels = re.search(r"\*\*Labels in Norwegian\.\*\*[^\n]*", help_md).group(0)
        self.assertIn('With "Norwegian only" on, they are all in Norwegian whatever this setting says.', labels)


if __name__ == "__main__":
    unittest.main()
