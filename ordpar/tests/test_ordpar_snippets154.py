# -*- coding: utf-8 -*-
"""Site decisions 154 (Robin, 2026-10-31): what Google reads — the producers' side.

Google built its snippets for *kanskje* and *være* from the page text and the text came out glued
and doubled ("kan hendeperhaps, maybeused to express a possibility"; "være III homograph 3
verbto scent"). Pinned here, in the code that writes the markup (the browser's view, on built
pages: `test_ordpar_browser_snippets154.py`):

1. **`data-nosnippet` on every hidden label, in the markup itself.** Every hover label
   (`ordbok-xpeek`) and screen-reader-only label (`ordpar-visually-hidden`, `sr-only`) that a
   Python producer writes carries it in the same tag (`face._link`, `face.SiteFace.xref_hover`,
   `article.head_html`, `wordpages`); the live regions are `div`s carrying it (a `p` cannot: Google
   reads the attribute on `span`, `div` and `section` only). The one exception is the search box's
   `<label>` in the header (outside the dictionary's content; a label cannot carry it). Every
   script that makes one makes it with the attribute (`lookup.js` and `shell.js` `srOnly`,
   `inflection.js` `hiddenLabel`, `install.js`, the page script's pronunciation "?"): Google never
   reads the attribute added by a script to an element already in the page.
2. **Whitespace between separate pieces**: the definition pair, an example and its translation,
   the "Article view" line, the header's name and tagline, the footer's links, a built row's word,
   word class, tag and snippet, the results' heading and its count.
3. **The headword first in the description** (`describe.description` with `word`,
   `wordpages.several_description`, `form_description`), `describe.CAP` the whole length; without
   a word every shape as before.

Fails on the code before 154 (no attribute, no newlines, no `word`). Stdlib unittest.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ROOT)

from ordpar.sitegen import article, chrome, describe, face as face_mod, wordpages  # noqa: E402
EN = chrome.strings("en")     # the site's strings with the shell's (`build_index` uses the same)

HIDDEN = ("ordbok-xpeek", "ordpar-visually-hidden", "sr-only")


def _read(*parts):
    with open(os.path.join(ORDPAR, *parts), encoding="utf-8") as f:
        return f.read()


def _tags(html, cls):
    return re.findall(r'<[a-z]+ [^>]*class="[^"]*\b%s\b[^"]*"[^>]*>' % re.escape(cls), html)


class HiddenLabelsInPython(unittest.TestCase):
    def test_every_python_producer_writes_the_attribute(self):
        """Every literal tag in ordpar/sitegen/*.py with a hidden label's class carries
        data-nosnippet — but the header's search <label>."""
        missing = []
        for name in sorted(os.listdir(os.path.join(ORDPAR, "sitegen"))):
            if not name.endswith(".py"):
                continue
            src = _read("sitegen", name)
            for cls in HIDDEN:
                pat = r'<(\w+) class="(?:[^"%]*\s)?' + re.escape(cls) + r'(?:%s)?(?:\s[^"]*)?"[^>]*>'
                for m in re.finditer(pat, src):
                    tag = m.group(0)
                    if m.group(1) == "label" and 'for="ordpar-q"' in tag:
                        continue
                    if "data-nosnippet" not in tag:
                        missing.append("%s: %s" % (name, tag))
        self.assertEqual(missing, [])

    def test_the_peeks(self):
        out = face_mod._link("/bm-en/116950/", "<em>kan hende</em>", "perhaps, maybe", "en")
        self.assertIn('<span class="ordbok-xpeek" lang="en" data-nosnippet>perhaps, maybe</span>', out)

    def test_the_head_numeral_reading(self):
        line = '<span class="sr-only" data-nosnippet> homograph 3</span>'
        src = _read("sitegen", "article.py")
        self.assertIn("'<span class=\"sr-only\" data-nosnippet> %s</span>'", src)
        self.assertTrue(line)

    def test_word_page_markup(self):
        a = {"id": 69212, "word": "være", "hg": 3, "pos": "VERB", "translated": True}
        b = {"id": 69210, "word": "være", "hg": 1, "pos": "NOUN", "translated": False}
        snip = lambda x: ("to scent · to sense", True) if x["translated"] else ("det å være", False)
        rows = wordpages.list_rows([a, b], EN, snip)
        for t in _tags(rows, "ordpar-visually-hidden"):
            self.assertIn("data-nosnippet", t)
        # the pieces of a row apart: the word, its class, its tag, its snippet; the rows apart
        self.assertNotRegex(rows, r'</span><span class="ordpar-(pos|tag|row-snippet)')
        self.assertNotIn("</span><span class=\"ordpar-row-line\"", rows)
        self.assertNotIn("</div><div class=\"ordpar-row\"", rows)
        self.assertIn('</span>\n<span class="ordpar-pos">', rows)
        self.assertIn('</span>\n<span class="ordpar-row-snippet ordpar-sgloss" lang="en">', rows)
        forms = wordpages.form_rows([dict(a, label="present")], EN, snip)
        self.assertNotRegex(forms, r'</(a|span)><span class="ordpar-(pos|form-label|tag|hit-snippet)')
        head = wordpages.results_heading(3, EN)
        self.assertIn('</span>\n<span class="ordpar-count">', head)
        self.assertIn('class="ordpar-visually-hidden" data-nosnippet> 3 articles', head)
        page = wordpages.render(fq="være", word="være", page={"count": 2, "arts": [a, b], "forms": []},
                                title="t", description="d", canonical="/bm-en/v%C3%A6re/", s=EN,
                                assets={"/site/theme.js": "/site/theme.js", "/site/ordpar.css": "/site/ordpar.css",
                                        "/site/ordpar.js": "/site/ordpar.js"}, snip=snip)
        self.assertIn('<div class="ordpar-visually-hidden" data-ordpar-live data-nosnippet role="status"', page)
        self.assertNotIn('<p class="ordpar-visually-hidden"', page)

    def test_the_shell_pages_live_regions(self):
        for name in ("search.html", "404.html"):
            src = _read("site", name)
            self.assertIn('<div class="ordpar-visually-hidden" data-ordpar-live data-nosnippet', src, name)
            self.assertNotIn('<p class="ordpar-visually-hidden"', src, name)


class HiddenLabelsInScript(unittest.TestCase):
    def test_lookup_and_shell_make_them_with_the_attribute(self):
        src = _read("site", "lookup.js")
        self.assertIn("function srOnly(text) {", src)
        self.assertIn("node.setAttribute('data-nosnippet', '');", src)
        # no other maker of the class
        self.assertEqual(len(re.findall(r"[^A-Za-z]el\('span', 'ordpar-visually-hidden'", src)), 1)
        # shell.js makes its two inline (the tests lift its functions one by one), each given the
        # attribute on the next line
        src = _read("site", "shell.js")
        made = re.findall(r"var (\w+) = el\('span', 'ordpar-visually-hidden'[^\n]*\n\s*(\w+)\.setAttribute\('data-nosnippet', ''\);", src)
        self.assertEqual(len(made), 2)
        self.assertTrue(all(a == b for a, b in made))
        self.assertEqual(src.count("'ordpar-visually-hidden'"), 2)

    def test_inflection_tables(self):
        src = _read("site", "inflection.js")
        self.assertNotRegex(src, r"[^A-Za-z]el\('(span|caption)', 'ordpar-vh'")
        self.assertEqual(len(re.findall(r"hiddenLabel\('(span|caption)', 'ordpar-vh'", src)), 4)
        self.assertIn("span.setAttribute('data-nosnippet', '');", src)
        self.assertEqual(src.count("return spaceTable(table);"), 2)

    def test_install_live_region(self):
        # (the pronunciation "?" pinned here too until site decisions 123's amendment removed it,
        # 2026-11-02)
        src = _read("site", "install.js")
        self.assertRegex(src, r"live = el\('div', 'ordpar-visually-hidden'\);\s*live.setAttribute\('data-nosnippet', ''\);")
        self.assertNotIn("w.className='ordpar-hint'", _read("sitegen", "page.py"))


class Whitespace(unittest.TestCase):
    def test_the_definition_pair(self):
        self.assertEqual(article.line_pair("brukt for å uttrykke en mulighet", "used to express a possibility"),
                         '<span class="ordpar-pair"><span class="ordbok-def" lang="nb">brukt for å uttrykke en '
                         'mulighet</span>\n<span class="ordbok-def" lang="en">used to express a possibility</span></span>')

    def test_an_example_and_its_translation(self):
        src = _read("sitegen", "article.py")
        self.assertIn('en = ("\\n" + _en_span(en_html)) if en_html else ""', src)

    def test_the_header_and_footer(self):
        h = chrome.header(chrome.strings("en"))
        self.assertIn('<span class="ordpar-brand-name">Ordpar</span>\n<span class="ordpar-brand-tagline">', h)
        f = chrome.footer(chrome.strings("en"), noindex=False, privacy=True)
        nav = re.search(r'<nav class="ordpar-footer-nav"[^>]*>(.*?)</nav>', f, re.S).group(1)
        self.assertNotIn("</a><a", nav)
        self.assertEqual(nav.count("</a>\n<a"), nav.count("<a ") - 1)

    def test_the_article_view_line(self):
        src = _read("sitegen", "page.py")
        self.assertIn('ordpar-dict-title">%(view)s</span>\n<a href="/">', src)
        self.assertIn("other = ('\\n<a href=\"%s\">%s</a>'", src)

    def test_scripts_space_their_rows(self):
        js = _read("site", "lookup.js")
        for call in ("spaced(line);", "spaced(btn);", "spaced(row);", "return spaced(wrap);",
                     "return spaced(h);", "return spaced(p);", "return spaced(li);",
                     "results.appendChild(spaced(hits));"):
            self.assertIn(call, js)


class TheHeadwordFirst(unittest.TestCase):
    def test_translated(self):
        d = describe.description(["perhaps", "maybe"], ["used to express a possibility; maybe",
                                                        "used to confirm a statement"], True, word="kanskje")
        self.assertEqual(d, "kanskje: perhaps · maybe. Definition: 1. used to express a possibility; maybe; "
                            "2. used to confirm a statement")

    def test_no_gloss_untranslated_fallback(self):
        self.assertEqual(describe.description([], ["a building"], True, word="hus"), "hus: a building")
        self.assertEqual(describe.description([], ["retning innenfor filosofi"], False, word="absurdisme"),
                         "absurdisme (not yet in English): retning innenfor filosofi")
        self.assertEqual(describe.description([], [], True, fallback="to shoulder", word="aksle"),
                         "aksle: to shoulder")
        self.assertEqual(describe.description([], [], True, fallback="", word="aksle"), "")

    def test_without_a_word_as_before(self):
        self.assertEqual(describe.description(["perhaps"], ["x"], True), "perhaps. Definition: x")
        self.assertEqual(describe.description([], ["x"], False), "Not yet in English: x")
        self.assertEqual(describe.description([], ["x"], True), "Definition: x")

    def test_the_cap_is_the_whole_length(self):
        long = ["used to express a possibility, a likelihood or a guess about what will happen next week",
                "used to confirm a statement that somebody else has just made in the conversation"]
        d = describe.description(["perhaps", "maybe"], long, True, word="kanskje")
        self.assertTrue(d.startswith("kanskje: perhaps · maybe. Definition: "), d)
        self.assertLessEqual(len(d), describe.CAP)

    def test_word_and_form_pages(self):
        arts = [{"id": 1, "hg": 2, "translated": True}, {"id": 2, "hg": 3, "translated": True},
                {"id": 3, "hg": 1, "translated": False}]
        gl = {1: "to be", 2: "to scent", 3: ""}
        d = wordpages.several_description(arts, lambda a: gl[a["id"]], EN, "være")
        self.assertEqual(d, "være: 3 entries in the Norwegian–English dictionary. II to be · III to scent · "
                            "I Norwegian only")
        self.assertEqual(wordpages.several_description(arts, lambda a: gl[a["id"]], EN),
                         "3 entries in the Norwegian–English dictionary: II to be · III to scent · I Norwegian only")
        rows = [{"id": 5, "word": "tå", "pos": "NOUN", "label": "plural indefinite", "translated": True}]
        f = wordpages.form_description("tær", rows, lambda a: "toe", EN, word=True)
        self.assertEqual(f, "tær: an inflected form of tå, noun (plural indefinite): toe.")


if __name__ == "__main__":
    unittest.main()
