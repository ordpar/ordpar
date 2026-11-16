# -*- coding: utf-8 -*-
"""Pins site-review decisions 74 and 76 (Robin, 2026-10-21). What can be pinned outside a browser;
the browser checks and the ordbokene label table are
`docs/sessions/2026-09-19-ordpar-site-review/evidence/search-icon-pos-74-76-2026-10-21/`.

* 76, the part-of-speech line as ordbokene's: `article.pos_html` splits `pos_en` into the word
  class and the gender or subclass — "noun <i>feminine or masculine</i>", "determiner
  <i>quantifier</i>" — with no brackets and no comma, the words unchanged; every label the
  library uses comes out that way; the head block carries it (the data-order genders of
  decisions 36 kept); the site sheet sets the `<i>` italic, upright small capitals off, after
  the deck's `.ordbok-pos` rule, and since 2026-10-21 the label at the body text's size (1em over the
  deck's .8em). The deck (`ordbok_gen.py`) still prints the bracketed label, at .8em.
* 74, the search icon: CSS only — the header's markup is unchanged (the button and its word
  "Search", its accessible name); `shell.css` puts the button inside the box's right end, text
  out of sight, the icon drawn by two pseudo-elements, and pads the input past the × and the
  icon.

Stdlib unittest."""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
SITE = os.path.join(ROOT, "ordpar", "site")
sys.path.insert(0, ROOT)

from ordpar.sitegen import article, chrome, page  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class PosLine(unittest.TestCase):

    def test_split(self):
        cases = {
            "noun (neuter)": "noun <i>neuter</i>",
            "noun (masculine or feminine)": "noun <i>masculine or feminine</i>",
            "noun (feminine or masculine)": "noun <i>feminine or masculine</i>",
            "noun (uninflected)": "noun <i>uninflected</i>",
            "determiner, quantifier": "determiner <i>quantifier</i>",
            "determiner, demonstrative": "determiner <i>demonstrative</i>",
            "determiner, possessive": "determiner <i>possessive</i>",
            "verb": "verb",
            "proper noun": "proper noun",
            "subordinating conjunction": "subordinating conjunction",
            "determiner": "determiner",
            "": "",
            None: "",
        }
        for pos, want in cases.items():
            self.assertEqual(article.pos_html(pos), want, pos)

    def test_every_library_label(self):
        labels = set()
        # the library: the repository root's, or ORDBOK_DATA_DIR's (the public repository's data/)
        lib = os.path.join(os.environ.get("ORDBOK_DATA_DIR") or ROOT, "articles.jsonl")
        if not os.path.exists(lib):
            self.skipTest("no library at %s" % lib)
        with open(lib, encoding="utf-8") as f:
            for line in f:
                labels.add(json.loads(line).get("pos_en") or "")
        self.assertIn("noun (masculine)", labels)
        for pos in labels:
            out = article.pos_html(pos)
            self.assertNotRegex(out, r"[(),]", pos)
            # the words are pos_en's, unchanged: only the brackets and the comma go
            self.assertEqual(re.sub(r"</?i>", "", out), re.sub(r"[(),]", "", pos), pos)
            self.assertLessEqual(out.count("<i>"), 1, pos)

    def test_head_block(self):
        row = {"lemmas": [{"form": "sykehus"}], "pos_en": "noun (neuter)"}
        h = article.head_html(row, page.EN)
        self.assertIn('<span class="ordbok-pos" lang="en">noun <i>neuter</i></span>', h)
        # decisions 36: two genders in the data's order, now in the <i>
        data = {"lemmas": [{"lemma": "bru", "hgno": 0, "paradigm_info": [
            {"tags": ["NOUN", "Fem"]}, {"tags": ["NOUN", "Masc"]}]}]}
        h = article.head_html({"lemmas": [{"form": "bru"}], "pos_en": "noun (masculine or feminine)"},
                              page.EN, data=data)
        self.assertIn('noun <i>feminine or masculine</i></span>', h)
        # a fixed expression still has no POS line
        h = article.head_html({"lemmas": [{"form": "på tide"}], "pos_en": "fixed expression"}, page.EN)
        self.assertNotIn("ordbok-pos", h)

    def test_sheet(self):
        css = page.article_css()
        rule = ".ordbok-pos i{font-style:italic;font-variant:normal;text-transform:lowercase;letter-spacing:normal}"
        self.assertIn(rule, css)
        self.assertGreater(css.index(rule), css.index(".ordbok-pos{display:block"))
        # its size (Robin, 2026-10-21, the style lab's variant 3): the body text's, 1.0, over the
        # deck's .8em, the grey kept (no colour in the site's rule)
        size = ".ordbok-pos{font-size:1em}"
        self.assertIn(size, css)
        self.assertGreater(css.index(size), css.index(".ordbok-pos{display:block;font-size:.8em"))

    def test_deck_untouched(self):
        self.assertIn('<span class="ordbok-pos">%s</span>', _read(ROOT, "ordbok_gen.py"))
        self.assertIn(".ordbok-pos{display:block;font-size:.8em;", _read(ROOT, "ordbok_gen.py"))


class PosWording(unittest.TestCase):
    """76's wording match (ours matching theirs): `article.site_pos` against
    ordbokene's rendered labels for the same tag sets
    (`…/evidence/pos-wording-76-2026-10-21/`)."""

    def test_nouns(self):
        cases = [
            (["NOUN", "Masc"], ["Masc"], "noun (masculine)"),
            (["NOUN", "Fem", "Masc"], ["Fem", "Masc"], "noun (feminine or masculine)"),
            # a neuter beside a masculine is named, in the data's order (agens, åkergull)
            (["NOUN", "Masc", "Neuter"], ["Masc", "Neuter"], "noun (masculine or neuter)"),
            (["NOUN", "Masc", "Neuter"], ["Neuter", "Masc"], "noun (neuter or masculine)"),
            # all three in one fixed order, whatever the data's (nyre: Fem, Neuter, Masc)
            (["NOUN", "Masc", "Fem", "Neuter"], ["Fem", "Neuter", "Masc"],
             "noun (masculine, feminine or neuter)"),
            # Uninfl does not hide the gender (abortus provocatus, råd, afrikaans, mellomnorsk)
            (["NOUN", "Masc", "Uninfl"], ["Masc"], "noun (masculine)"),
            (["NOUN", "Fem", "Masc", "Uninfl"], ["Fem", "Masc"], "noun (feminine or masculine)"),
            (["NOUN", "Masc", "Neuter", "Uninfl"], ["Masc", "Neuter"], "noun (masculine or neuter)"),
            # with no gender, uninflectable (ert); plain noun without Uninfl (folkens)
            (["NOUN", "Uninfl"], [], "noun (uninflectable)"),
            (["NOUN"], [], "noun"),
            (["SCONJ"], [], "subjunction"),
            (["VERB", "Uninfl"], [], "verb"),
            (["PROPN"], [], "proper noun"),
            ([], [], "fixed expression"),
        ]
        for tags, genders, want in cases:
            self.assertEqual(article.site_pos(tags, genders), want, (tags, genders))

    def test_row_label_fallback(self):
        self.assertEqual(article.site_pos_label("subordinating conjunction"), "subjunction")
        self.assertEqual(article.site_pos_label("noun (uninflected)"), "noun (uninflectable)")
        self.assertEqual(article.site_pos_label("noun (neuter)"), "noun (neuter)")

    def test_three_genders_markup(self):
        self.assertEqual(article.pos_html("noun (masculine, feminine or neuter)"),
                         "noun <i>masculine, feminine or neuter</i>")

    def test_head_block(self):
        data = {"lemmas": [{"lemma": "råd", "hgno": 0, "paradigm_info": [
            {"tags": ["NOUN", "Fem", "Uninfl"]}, {"tags": ["NOUN", "Masc", "Uninfl"]}]}]}
        h = article.head_html({"lemmas": [{"form": "råd"}], "pos_en": "noun (uninflected)"},
                              page.EN, data=data)
        self.assertIn('noun <i>feminine or masculine</i></span>', h)
        data = {"lemmas": [{"lemma": "ert", "hgno": 0, "paradigm_info": [
            {"tags": ["NOUN", "Uninfl"]}]}]}
        h = article.head_html({"lemmas": [{"form": "ert"}], "pos_en": "noun (uninflected)"},
                              page.EN, data=data)
        self.assertIn('noun <i>uninflectable</i></span>', h)
        h = article.head_html({"lemmas": [{"form": "fordi"}], "pos_en": "subordinating conjunction"},
                              page.EN)
        self.assertIn('lang="en">subjunction</span>', h)

    def test_search_string(self):
        strings = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(strings["pos.SCONJ"], "subjunction")


class SearchIcon(unittest.TestCase):

    def test_markup_unchanged(self):
        h = chrome.header(chrome.strings())
        self.assertIn('<button class="ordpar-submit" type="submit">Search</button>\n</form>', h)
        self.assertNotIn("<svg", h)
        self.assertNotIn("aria-label", h.split('<form', 1)[1])

    def test_css(self):
        css = _read(SITE, "shell.css")
        block = css.split(".ordpar-search .ordpar-submit {", 1)[1].split("}", 1)[0]
        for decl in ("position: absolute;", "text-indent: 200%;", "overflow: hidden;",
                     "background: transparent;", "color: var(--ordpar-accent);"):
            self.assertIn(decl, block)
        self.assertIn(".ordpar-search .ordpar-submit::before", css)
        self.assertIn(".ordpar-search .ordpar-submit::after", css)
        self.assertIn(".ordpar-search .ordpar-submit:focus-visible { outline-offset: -3px; }", css)
        self.assertIn("padding: 0.5rem 4.6rem 0.5rem 0.6rem;", css)
        clear = css.split(".ordpar-clear {", 1)[1].split("}", 1)[0]
        self.assertIn("right: 2.75rem;", clear)
        search = css.split(".ordpar-search {\n", 1)[1].split("}", 1)[0]
        self.assertIn("position: relative;", search)


if __name__ == "__main__":
    unittest.main()
