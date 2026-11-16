# -*- coding: utf-8 -*-
"""Site decisions 166, Copy: a 'copy' button on each row, to paste it into a session chat to
discuss it with Claude, holding the article ID, the article body and the report. Brief: `docs/sessions/2026-09-19-ordpar-site-review/evidence/
brief-report-copy-166-2026-11-05.md`. Stdlib unittest, no bun, no browser, no network.

* **The four parts, in order** (`reports_page.copy_text`): the heading line (the report's number,
  its day, the site build it names), the article (id, headword, the live and the :8098 address),
  the report (its category, its text whole in a quote block), the article's text as built.
* **Never the reply address or the name to credit**, even when the report has them.
* **The article's text** (`article_text`, from `<out>/bm-en/<id>/index.html`): the headword line,
  the word class, the senses numbered with their English, the examples with theirs, the set
  phrases; not what the page hides — the label copy not shown (`ordpar-l-nb`, `ordpar-w-nb`,
  `ordpar-cl-nb`, `ordpar-pg-nb`), the hover peeks (`ordbok-xpeek`), the screen-reader text
  (`sr-only`), a `hidden` element; the inflection table as plain rows (`inflection_rows`, the
  shapes read from the built `site/inflection.js`), or "(inflection table not included)".
* **A missing page** said so in the text.
* **The page** (`page_html`): a Copy button per report, its tooltip and a note saying the
  address and the name are not copied, the clipboard with a selected text box as the fallback;
  `queue_json` gives each report its `copy`.
* **The real build** (when `ordpar/out/` has it): *hus* (24627), its senses and peeks.

The report reader is private: in the public repository every test here skips, naming the module.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import reports_page  # noqa: E402
except ModuleNotFoundError as e:
    if e.name != "reports_page":
        raise
    reports_page = None
#: the report reader is private: in the public repository every test here skips with this reason
NO_READER = "needs reports_page (scripts/reports_page.py), which the public repository does not have"

SHAPES = {"b24z": [["NOUN", "Neuter"], "NOUN_regular", ["Sing+Ind", "Sing+Def", "Plur+Ind", "Plur+Def"]]}

PAGE = """<!doctype html>
<html lang="en" data-article-id="98" data-lemma="hus" data-translated="1">
<head><title>hus</title><script src="/site/theme.js"></script></head>
<body class="ordpar">
<a class="ordpar-skip" href="#ordpar-main">Skip to the article</a>
<header class="ordpar-header"><form><label class="ordpar-visually-hidden">Search a Norwegian word</label>
<button>Search</button></form></header>
<main id="ordpar-main">
<article class="ordpar-card ordpar-entry">
<div class="ordbok ordpar-article" lang="en">
<div class="ordbok-head">
<h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma">hus</span> <span class="ordbok-homograph" aria-hidden="true">II</span><span class="sr-only" data-nosnippet> homograph 2</span></h1>
<span class="ordbok-pos"><span class="ordpar-w-en">noun <i>neuter</i></span><span class="ordpar-w-nb" lang="nb" data-nosnippet>substantiv <i>intetkjønn</i></span></span>
<p class="ordpar-gloss">a house<span class="ordpar-gsep"> · </span>a building</p>
</div>
<script type="application/json" id="ordpar-paradigm">%(island)s</script>
<details class="ordpar-infl-toggle" hidden><summary><span class="ordpar-l-en">Inflection</span><span class="ordpar-l-nb" lang="nb" data-nosnippet>Vis bøyning</span></summary>
<div class="ordpar-inflection" data-paradigm="ordpar-paradigm"></div></details>
<section class="ordbok-sec ordbok-inline ordpar-pron">
<h3><span class="ordpar-l-en">Pronunciation</span><span class="ordpar-l-nb" lang="nb" data-nosnippet>Uttale</span></h3>
<span class="ordbok-body" lang="nb">huːs <span class="ordpar-pg-en" lang="en"><em>or</em></span><span class="ordpar-pg-nb"><em>eller</em></span> hʉːs</span>
</section>
<section class="ordbok-sec">
<h3><span class="ordpar-l-en">Senses and Example Sentences</span><span class="ordpar-l-nb" lang="nb" data-nosnippet>Betydning og bruk</span></h3>
<ol class="ordbok-senses">
<li id="def2">
<span class="ordpar-pair"><span class="ordbok-def" lang="nb">bygning brukt til bosted</span>
<span class="ordbok-def" lang="en">a building used as a dwelling</span></span>
<ul class="ordbok-ex-list">
<li><span lang="nb"><em>bygge hus</em></span>
<span class="ordbok-tr ordpar-en">to build a house</span></li>
</ul>
<div class="ordbok-sub ordpar-comp">
<span class="ordbok-def"><em><span class="ordpar-cl-en">as a suffix in words such as:</span><span class="ordpar-cl-nb" lang="nb" data-nosnippet>som etterledd i ord som</span></em> <span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/24530/" lang="nb"><em>hundehus</em></a><span class="ordbok-xpeek" data-nosnippet>a kennel, a doghouse</span></span></span>
</div>
</li>
<li id="def8">
<span class="ordpar-pair"><span class="ordbok-def" lang="nb">personer i et hus;<br>husstand</span>
<span class="ordbok-def" lang="en">the people in a house;<br>household</span></span>
</li>
</ol>
</section>
<section class="ordbok-sec">
<h3><span class="ordpar-l-en">Set phrases</span><span class="ordpar-l-nb" lang="nb" data-nosnippet>Faste uttrykk</span></h3>
<div class="ordbok-expr">
<span class="ordbok-expr-term" lang="nb">holde åpent hus</span>
<span class="ordpar-pair"><span class="ordbok-def" lang="nb">ta imot gjester</span>
<span class="ordbok-def" lang="en">to receive guests</span></span>
<span class="ordbok-idiom"><span class="ordbok-idiom-tag">Eng. phrase</span><span class="ordbok-idiom-eng">to keep open house</span></span>
</div>
</section>
</div>
<footer class="ordpar-card-foot"></footer>
</article>
</main>
<footer class="ordpar-footer"><p class="ordpar-credit">Based on Bokmålsordboka</p></footer>
</body>
</html>
"""

REPORT = {"id": 12, "day": "2026-11-05", "article": 98, "build": "2026-11-05-1508",
          "category": "translation", "text": "Sense 1 should say \"home\".\n\nSecond paragraph.",
          "reply": "kari.reader@example.org", "credit": "Kari Nordmann"}


@unittest.skipUnless(reports_page, NO_READER)
class CopyText(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="copy166-")
        island = json.dumps([["hus", ["b24z", "hus", "huset", "hus", "husa"],
                              ["b24z", "hus", "huset", "hus", "husene"]]], ensure_ascii=False)
        self.write(98, PAGE % {"island": island})
        self.write(99, PAGE % {"island": json.dumps([["hus", ["zzzz", "hus"]]])})
        os.makedirs(os.path.join(self.out, "site"))
        with open(os.path.join(self.out, "site", "inflection.js"), "w", encoding="utf-8") as f:
            f.write("(function(){var SHAPES = %s;\nvar X = 1;}());\n" % json.dumps(SHAPES))

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def write(self, article, text):
        d = os.path.join(self.out, "bm-en", str(article))
        os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(text)

    def copy(self, **over):
        return reports_page.copy_text(dict(REPORT, **over), self.out)

    def test_four_parts_in_order(self):
        text = self.copy()
        first = text.split("\n", 1)[0]
        self.assertEqual(first, "Ordpar reader report #12, arrived 2026-11-05, site build 2026-11-05-1508")
        marks = ["## The article", "- id: 98", "- headword: hus",
                 "- live: https://ordpar.no/bm-en/98/", "- local build: http://127.0.0.1:8098/bm-en/98/",
                 "## The report", "Category: Translation",
                 '> Sense 1 should say "home".\n>\n> Second paragraph.',
                 "## The article's text, as built", "Headword: hus II"]
        at = [text.find(m) for m in marks]
        self.assertNotIn(-1, at, [m for m, a in zip(marks, at) if a < 0])
        self.assertEqual(at, sorted(at))
        self.assertIn("site build (none named)", self.copy(build=None).split("\n", 1)[0])
        self.assertIn("Category: none chosen", self.copy(category=None))

    def test_no_reply_address_and_no_name(self):
        text = self.copy()
        for gone in ("kari.reader@example.org", "Kari Nordmann", "Nordmann", "@", "credit", "Reply"):
            self.assertNotIn(gone, text)
        self.assertNotIn("Kari", self.copy(text="x"))

    def test_article_text_visible_only(self):
        hw, body = reports_page.article_text(98, self.out)
        self.assertEqual(hw, "hus")
        for shown in ("Headword: hus II", "Word class: noun neuter", "Gloss: a house · a building",
                      "### Pronunciation", "huːs or hʉːs", "### Senses and Example Sentences",
                      "1. nb: bygning brukt til bosted", "   en: a building used as a dwelling",
                      "   - nb: bygge hus", "     en: to build a house",
                      "as a suffix in words such as: hundehus",
                      "2. nb: personer i et hus;\n       husstand",
                      "### Set phrases", "**holde åpent hus**", "  en: to receive guests",
                      "Eng. phrase: to keep open house"):
            self.assertIn(shown, body)
        # the label copy not shown, the peeks, the screen-reader text, the hidden toggle
        for hidden in ("Betydning og bruk", "Faste uttrykk", "Uttale", "substantiv", "intetkjønn",
                       "eller", "som etterledd", "a kennel", "doghouse", "homograph 2",
                       "Vis bøyning", "Search", "Skip to", "Based on"):
            self.assertNotIn(hidden, body)

    def test_inflection_rows(self):
        _, body = reports_page.article_text(98, self.out)
        self.assertIn("- hus: singular indefinite hus; singular definite huset; plural indefinite hus; "
                      "plural definite husa", body)
        self.assertIn("plural definite husene", body)
        self.assertNotIn(reports_page.NO_TABLE, body)
        _, other = reports_page.article_text(99, self.out)     # a shape the table does not have
        self.assertIn(reports_page.NO_TABLE, other)
        os.remove(os.path.join(self.out, "site", "inflection.js"))   # no shape table at all
        _, bare = reports_page.article_text(98, self.out)
        self.assertIn(reports_page.NO_TABLE, bare)

    def test_missing_page(self):
        self.assertEqual(reports_page.article_text(4242, self.out), (None, None))
        text = self.copy(article=4242)
        self.assertIn("- id: 4242", text)
        self.assertIn("No page at ordpar/out/bm-en/4242/index.html: the article is not in this build.",
                      text)
        self.assertLess(text.find("## The report"), text.find("No page at"))


@unittest.skipUnless(reports_page, NO_READER)
class ThePage(unittest.TestCase):
    def test_button_note_and_fallback(self):
        html = reports_page.page_html()
        self.assertIn("el('button', 'copy', 'Copy')", html)
        self.assertIn("The reply address and the name to credit are not copied.", html)
        self.assertIn("Copy leaves out the reply address and the name to credit.", html)
        self.assertIn("navigator.clipboard.writeText(r.copy)", html)
        self.assertIn("copyBox.select()", html)
        self.assertNotIn("r.reply + ", html.split("// Copy (166)")[1].split("copy.addEventListener")[0])

    def test_queue_json_gives_each_report_its_copy(self):
        saved = reports_page._call, reports_page.access, reports_page.read_fixes
        rec = dict(REPORT)
        try:
            reports_page._call = lambda m, p: (200, json.dumps({"reports": [rec]}).encode())
            reports_page.access = lambda: ("http://127.0.0.1:1", "t")
            reports_page.read_fixes = lambda: []
            got = reports_page.queue_json()
        finally:
            reports_page._call, reports_page.access, reports_page.read_fixes = saved
        r = got["reports"][0]
        self.assertTrue(r["copy"].startswith("Ordpar reader report #12"))
        self.assertNotIn("kari.reader@example.org", r["copy"])
        self.assertNotIn("Kari Nordmann", r["copy"])


@unittest.skipUnless(reports_page, NO_READER)
@unittest.skipUnless(os.path.exists(os.path.join(ORDPAR, "out", "bm-en", "24627", "index.html")),
                     "no build of hus (24627) in ordpar/out/")
class TheBuild(unittest.TestCase):
    def test_hus(self):
        hw, body = reports_page.article_text(24627)
        self.assertEqual(hw, "hus")
        self.assertTrue(body.startswith("Headword: hus\nWord class: noun neuter"), body[:80])
        for shown in ("1. nb: bygning (med tak og vegger)", "     en: to build a house",
                      "plural definite husene", "**gå hus forbi**"):
            self.assertIn(shown, body)
        for hidden in ("Betydning og bruk", "Opphav", "intetkjønn", "a kennel", "Vis bøyning"):
            self.assertNotIn(hidden, body)


if __name__ == "__main__":
    unittest.main()
