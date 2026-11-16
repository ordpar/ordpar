# -*- coding: utf-8 -*-
"""Site-review decisions 123 (Robin, 2026-10-24): Bokmålsordboka's pronunciation field — the page
HTML's side, and the Help page that holds the note on its marks.

Until this build no page showed `body.pronunciation`. Now (`sitegen/pronunciation.py`):

1. **placed and labelled as ordbokene's page** (its English interface, rendered 2026-10-24): a
   section "Pronunciation" after the inflection toggle and before the etymology — *abstrakt*
   (98, translated; 97, Norwegian-only) "abstrakˊt", verbatim, `lang="nb"`;
2. **the words around the respellings**: on a translated page both halves, `ordpar-pg-en` (the
   default, and under `formulas = both`) and `ordpar-pg-nb` (`formulas = no`) — *doktor* (10539)
   "in the plural" / "i flertall", "or" / "eller"; on a Norwegian-only page Norwegian alone, no
   pair — *lektor* (34785) "lekˊtor, *i flertall* lekˊtorer eller lektoˊrer";
3. **the note on the marks** is the Help page's § Pronunciation (`/help/#pronunciation`, from
   `ordpar/help.md`), linked from every page's footer ("Help", before "About and licence"), in the
   offline copy as About is. No note text in any page, and since 2026-11-02 no "?" beside the
   label either (decisions 123's amendment: it took space and attention for nothing once
   the sound icons were in; on the site and the deck alike): no `ordpar-pron-key` class, no `pronq`
   in the page script, no `pron_note` / `pron_button` strings — also on *abstrakt*, whose field
   uses a mark.

Two parts: the renderer over the mirror's own entries as fixtures (always runs), and the built
pages — from `ordpar/out/` (or `ORDPAR_TEST_OUT`), or fetched from `ORDPAR_TEST_BASE` (the live
site before the build, snapshot 98be9479dbc: fails — no section, no Help page, no footer link).
A page missing from the copy skips its test. The browser's side, with the setting:
`test_ordpar_browser_pron123.py`.
"""
import os
import re
import sys
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

from ordpar.sitegen import pronunciation as P  # noqa: E402
from ordpar.sitegen import about, chrome, strings  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
BASE = (os.environ.get("ORDPAR_TEST_BASE") or "").rstrip("/")
NOTE_START = "Written in ordinary Norwegian spelling"

#: The mirror's entries (2026-09-25 snapshot), copied as they are
DOKTOR = {"body": {"pronunciation": [
    {"type_": "pronunciation", "content": "dokˊtor, $ dokˊtorer",
     "items": [{"type_": "pronunciation_guide", "content": "i $", "items": [{"type_": "grammar", "id": "fl"}]}]},
    {"type_": "pronunciation", "content": "doktoˊrer", "items": []}]}}
DOCTOR = {"body": {"pronunciation": [
    {"type_": "pronunciation", "content": "dokˊtor, i $ form $ dåktoˋres",
     "items": [{"type_": "grammar", "id": "ub"}, {"type_": "grammar", "id": "fl"}]}]}}
KOMPAKTOR = {"body": {"pronunciation": [
    {"type_": "pronunciation", "content": "$, i $ $ eller $",
     "items": [{"type_": "pronunciation_guide", "content": "kompakˊtor", "items": []},
               {"type_": "grammar", "id": "fl"},
               {"type_": "pronunciation_guide", "content": "kompakˊtorer", "items": []},
               {"type_": "pronunciation_guide", "content": "kompaktoˊrer", "items": []}]}]}}
AKKUMULATOR = {"body": {"pronunciation": [
    {"type_": "pronunciation", "content": "akumulaˊtor", "items": []},
    {"type_": "pronunciation", "content": "$ akumulaˊtorer",
     "items": [{"type_": "pronunciation_guide", "content": "i fleirtal", "items": []}]},
    {"type_": "pronunciation", "content": "akumulatoˊrer", "items": []}]}}
SCHAEFER = {"body": {"pronunciation": [
    {"type_": "pronunciation", "content": "av $ ‘Schäferhund’, ‘Schäfer’ ‘gjeter’ av $ ‘sau’",
     "items": [{"type_": "entity", "id": "ty."},
               {"type_": "pronunciation_guide", "content": "Schaf", "items": []}]}]}}
CONCEPTS = {"fl": "flertall", "ub": "ubestemt", "el": "eller", "ty.": "tysk"}


def visible(markup, formulas="en"):
    """The words a reader sees under a `formulas` choice: the other language's half dropped."""
    drop = "ordpar-pg-nb" if formulas != "no" else "ordpar-pg-en"
    markup = re.sub(r'<span class="%s"[^>]*>(?:<em>)?[^<]*(?:</em>)?</span>' % drop, "", markup)
    return re.sub(r"<[^>]+>", "", markup)


class Renderer(unittest.TestCase):

    def setUp(self):
        self.saved, P.CONCEPTS = P.CONCEPTS, CONCEPTS

    def tearDown(self):
        P.CONCEPTS = self.saved

    def test_a_translated_words_in_english_and_norwegian(self):
        out = P.body_html(DOKTOR, True)
        self.assertEqual(visible(out), "dokˊtor, in the plural dokˊtorer or doktoˊrer")
        self.assertEqual(visible(out, "no"), "dokˊtor, i flertall dokˊtorer eller doktoˊrer")
        self.assertIn('<span class="ordpar-pg-en" lang="en"><em>in the plural</em></span>'
                      '<span class="ordpar-pg-nb"><em>i flertall</em></span>', out)

    def test_b_norwegian_only_words_stay_norwegian(self):
        out = P.body_html(DOKTOR, False)
        self.assertNotIn("ordpar-pg", out)
        self.assertEqual(out, "dokˊtor, <em>i flertall</em> dokˊtorer <em>eller</em> doktoˊrer")

    def test_c_a_run_across_literal_words(self):
        self.assertEqual(visible(P.body_html(DOCTOR, True)), "dokˊtor, in the indefinite plural dåktoˋres")
        self.assertEqual(P.body_html(DOCTOR, False), "dokˊtor, i ubestemt form flertall dåktoˋres")

    def test_d_respellings_as_items_stay_verbatim_in_italics(self):
        out = P.body_html(KOMPAKTOR, True)
        self.assertTrue(out.startswith("<em>kompakˊtor</em>, "), out)
        self.assertEqual(visible(out), "kompakˊtor, in the plural kompakˊtorer or kompaktoˊrer")

    def test_e_entries_joined_as_ordbokene(self):
        # ", " before an entry that opens with a template item, else an italic "eller"
        self.assertEqual(P.body_html(AKKUMULATOR, False),
                         "akumulaˊtor, <em>i fleirtal</em> akumulaˊtorer <em>eller</em> akumulatoˊrer")

    def test_f_an_unknown_run_leaves_the_entry_norwegian(self):
        out = P.body_html(SCHAEFER, True)
        self.assertNotIn("ordpar-pg", out)
        self.assertEqual(out, "av tysk ‘Schäferhund’, ‘Schäfer’ ‘gjeter’ av <em>Schaf</em> ‘sau’")

    def test_g_the_section_and_no_note(self):
        sec = P.section_html({"body": {"pronunciation": [
            {"type_": "pronunciation", "content": "abstrakˊt", "items": []}]}}, True)
        self.assertIn('<h3 lang="en">Pronunciation</h3>', sec)
        self.assertIn('<span class="ordbok-body" lang="nb">abstrakˊt</span>', sec)
        self.assertIn('<section class="ordbok-sec ordbok-inline ordpar-pron">', sec)   # no key (123, 2026-11-02)
        self.assertNotIn("ordpar-hint", sec)
        self.assertEqual(P.section_html({"body": {}}, True), "")

    def test_g2_no_question_mark_anywhere(self):
        # decisions 123's amendment (Robin, 2026-11-02): the "?" beside the label is gone, on the
        # site and the deck (which carries the same page script); the note is Help's alone
        def d(*cs):
            return {"body": {"pronunciation": [{"type_": "pronunciation", "content": c, "items": []}
                                               for c in cs]}}
        for marked in (d("abstrakˊt"), d("kesadi`ja"), d("båˊrding-"), KOMPAKTOR):
            self.assertNotIn("ordpar-pron-key", P.section_html(marked, True))
        self.assertFalse(hasattr(P, "needs_key"))
        from ordpar.sitegen import page
        for gone in ("pronq", "ordpar-pron-key", "PRON"):
            self.assertNotIn(gone, page.PAGE_JS, gone)
        self.assertNotIn("pron_note", strings.EN)
        self.assertNotIn("pron_button", strings.EN)

    def test_h_the_help_page_and_the_footer_link(self):
        title, body = about.help_page()
        self.assertEqual(title, "Help")
        self.assertIn('<h2 id="pronunciation">Pronunciation</h2>', body)
        self.assertIn(NOTE_START, body)
        s = chrome.strings("en")
        nav = re.search(r'<nav class="ordpar-footer-nav".*?</nav>', chrome.footer(s, noindex=False,
                                                                                  privacy=False), re.S).group(0)
        self.assertIn('<a href="/help/">Help</a>\n<a href="/more/">', nav)   # a newline between (154)   # More after Help since decisions 142

    def test_i_the_mini_leaves_it_out(self):
        with open(os.path.join(ROOT, "ordpar", "site", "mini.js"), encoding="utf-8") as fh:
            self.assertIn("!has(sec, 'ordpar-pron')", fh.read())


def fetch(path):
    """A page of the copy under test, by its path (`/bm-en/98/`, `/help/`), or None."""
    if BASE:
        try:
            with urllib.request.urlopen(BASE + path, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception:
            return None
    f = os.path.join(OUT, path.strip("/").replace("/", os.sep), "index.html") if path != "/" \
        else os.path.join(OUT, "index.html")
    if not os.path.exists(f):
        return None
    with open(f, encoding="utf-8") as fh:
        return fh.read()


# site decisions 152: on a site page the heading is a label pair, "Pronunciation" and its hidden
# Norwegian copy "Uttale" (`article.label_pair`, the labels setting)
SEC_RE = re.compile(r'<section class="ordbok-sec ordbok-inline ordpar-pron( ordpar-pron-key)?">\s*<h3[^>]*>'
                    r'<span class="ordpar-l-en">Pronunciation</span><span class="ordpar-l-nb" lang="nb" '
                    r'data-nosnippet>Uttale</span></h3>'
                    r'\s*<span class="ordbok-body"(?: lang="nb")?>(.*?)</span>\s*</section>', re.S)
# (the slimming drops `lang="nb"` where the page's root is Norwegian already, `page.finish`)


class Pages(unittest.TestCase):

    def page(self, path):
        html = fetch(path)
        if html is None and not BASE:
            self.skipTest("no page %s in %s" % (path, OUT))
        return html or ""

    def test_a_abstrakt_after_the_inflection_before_the_etymology(self):
        for aid in (98, 97):
            html = self.page("/bm-en/%d/" % aid)
            m = SEC_RE.search(html)
            self.assertTrue(m, "no Pronunciation section on %d (%s)" % (aid, BASE or OUT))
            self.assertEqual(m.group(2), "abstrakˊt")
            self.assertFalse(m.group(1), "a key on %d (123: no \"?\" since 2026-11-02)" % aid)
            # site decisions 152: the etymology's heading is a label pair
            infl, ety = html.find("ordpar-infl-toggle"), html.find('<span class="ordpar-l-en">Etymology</span>')
            self.assertTrue(0 < infl < m.start() < ety, (aid, infl, m.start(), ety))

    def test_b_a_template_on_a_translated_page(self):
        m = SEC_RE.search(self.page("/bm-en/10539/"))
        self.assertTrue(m, "no Pronunciation on doktor 10539 (%s)" % (BASE or OUT))
        self.assertEqual(visible(m.group(2)), "dokˊtor, in the plural dokˊtorer or doktoˊrer")
        self.assertEqual(visible(m.group(2), "no"), "dokˊtor, i flertall dokˊtorer eller doktoˊrer")

    def test_c_a_template_on_a_norwegian_only_page(self):
        m = SEC_RE.search(self.page("/bm-en/34785/"))
        self.assertTrue(m, "no Pronunciation on lektor 34785 (%s)" % (BASE or OUT))
        self.assertNotIn("ordpar-pg", m.group(2))
        self.assertEqual(visible(m.group(2)), "lekˊtor, i flertall lekˊtorer eller lektoˊrer")

    def test_d_no_note_text_and_no_key_in_a_page(self):
        for aid in (98, 10539, 34785, 4005, 8651):
            html = self.page("/bm-en/%d/" % aid)
            art = html[html.find('<article class="ordpar-card'):html.find("</article>")]
            self.assertNotIn(NOTE_START, art, aid)
            self.assertNotIn("ordpar-hint", art, aid)
            self.assertNotIn("ordpar-pron-key", html, aid)
        for aid in (4005, 8651):
            m = SEC_RE.search(self.page("/bm-en/%d/" % aid))
            self.assertTrue(m, "no Pronunciation on %d (%s)" % (aid, BASE or OUT))
            self.assertFalse(m.group(1), "a key on %d, which uses no mark" % aid)

    def test_e_the_help_page(self):
        html = fetch("/help/")
        if not html and not BASE and not os.path.isdir(OUT):
            self.skipTest("no built site in %s" % OUT)       # as the other pages (a fresh checkout)
        self.assertTrue(html, "no /help/ in %s" % (BASE or OUT))
        self.assertIn('<h2 id="pronunciation">Pronunciation</h2>', html)
        self.assertIn(NOTE_START, html)
        # indexed since site decisions 128 (2026-10-25): Help is one of the pages search engines list
        self.assertNotIn('content="noindex"', html)

    def test_f_the_footer_links_help_on_an_article_and_the_home_page(self):
        for path in ("/bm-en/98/", "/"):
            html = self.page(path)
            nav = re.search(r'<nav class="ordpar-footer-nav".*?</nav>', html, re.S)
            self.assertTrue(nav, path)
            # "More ways to use Ordpar" after Help since site decisions 142
            # \s*: site decisions 154 puts a newline between the footer's links
            self.assertRegex(nav.group(0), r'<a href="/help/">Help</a>\s*<a href="/more/">', path)

    def test_g_in_the_offline_copy(self):
        if BASE:
            self.skipTest("the offline list is the build's")
        sys.path.insert(0, os.path.join(ROOT, "ordpar"))
        import build_offline
        self.assertEqual(build_offline.SHELL_PAGES.get("/help/"), "help/index.html")


if __name__ == "__main__":
    unittest.main()
