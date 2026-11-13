"""Pins the About page and the published README as ONE source text (site decisions 63, Robin
2026-10-22: "making the README and the about page identical"), `ordpar/about.md`, rendered by
`ordpar/sitegen/about.py`:

* the source's Markdown subset on the page: the `# ` title, `## ` headings, paragraphs, links
  (the CC BY 4.0 deed with `rel="license"`), bold;
* the numbers the build fills: the article total to the nearest hundred, the others exact with a
  thousands comma, the text share a whole percent ("36 %"); an unknown name raises;
* the summary clause is there while some translated article lacks its summary, and at zero it
  goes, the sentence ending "…translated so far.";
* the README is the page's text plus its one `[readme]` section, the repository note in the
  approved README's words; `deploy.py readme --out` writes it from `build.json`'s `site_stats`
  and refuses a report without them;
* the added example's mark on the site says "added by Ordpar"; the deck's own is unchanged.
* the recordings offered under CC BY 4.0 and the data on request (decisions 172).

Stdlib unittest."""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, ROOT)

from ordpar.sitegen import about, article, page  # noqa: E402
from ordpar import deploy  # noqa: E402
import ordbok_gen  # noqa: E402

S = about.SAMPLE
APPROVED = os.path.join(ROOT, "docs", "sessions", "2026-09-19-ordpar-site-review", "walk-through",
                        "about-page-final-2026-10-22.md")
REPO_NOTE = ("This is the built site that GitHub Pages serves at ordpar.no: generated pages, styles, "
             "scripts and search files. It is replaced in full each time the site is updated and "
             "keeps no history, so changes made here would be lost. The code that builds the site "
             "will be published in a repository of its own, with its own licence; until then, no "
             "licence is given for the scripts and styles here.")

#: site decisions 172 (Robin, 2026-11-07), the approved words
AUDIO_172 = ("You may reuse the recordings on the same terms as the text, CC BY 4.0: credit the recordings "
             "to Ordpar (ordpar.no), and the words they read as you would the text itself.")
DATA_172 = ("If you would like the dictionary's data as files, the articles or the recordings, write to us "
            "there too.")
#: site decisions 184 (Robin, 2026-11-13): the English's licence in the code's wording
ENGLISH_184 = ("The English is written with AI (Claude, by Anthropic) under Robin Fauskanger's direction and "
               "review. Whatever rights exist in it are given on the same terms as the Norwegian, CC BY 4.0: "
               "credit the English to Ordpar (ordpar.no), and the Norwegian to Bokmålsordboka.")


def _stats(**art):
    s = json.loads(json.dumps(S))
    s["articles"].update(art)
    return s


class Source(unittest.TestCase):

    def test_page_markup(self):
        title, body = about.page(S)
        self.assertEqual(title, "About Ordpar")
        self.assertTrue(body.startswith("<p>Ordpar is a Norwegian–English dictionary on the web."))
        # every heading with its id since site decisions 131 (2026-10-26: "Contact" -> #contact)
        self.assertIn('<h2 id="how-far-it-has-come">How far it has come</h2>', body)
        self.assertIn('<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">Creative '
                      'Commons Attribution 4.0 International licence (CC BY 4.0)</a>', body)
        self.assertIn('<a href="https://creativecommons.org/licenses/by/4.0/legalcode.en#s5">'
                      'disclaimer of warranties (section 5)</a>', body)
        self.assertNotIn("[", body)
        self.assertNotIn("{", body)
        self.assertNotIn("<!--", body)
        self.assertNotIn("This repository", body)
        self.assertEqual(about._inline("a **b** c"), "a <strong>b</strong> c")
        # `*italic*` since site decisions 131 (the deck's name under "Thanks")
        self.assertEqual(about._inline("a *b c* d **e** f"), "a <em>b c</em> d <strong>e</strong> f")
        self.assertEqual(about._inline("2 * 3 * 4"), "2 * 3 * 4")
        self.assertEqual(about.plain("a <em>b</em> *c* **d**"), "a b c d")

    def test_whole_page(self):
        html = page.about_page("ordpar build: t", page.EN, S)
        self.assertIn("<title>About Ordpar — Ordpar</title>", html)
        # site decisions 176: the about pages' tabs between the title and the first paragraph
        self.assertRegex(html, r'(?s)<article class="ordpar-about">\n<h1>About Ordpar</h1>\n'
                               r'<nav class="ordpar-tabs" aria-label="About Ordpar">\n.*?</nav>\n<p>Ordpar is')

    def test_numbers(self):
        n = about.numbers(S)
        self.assertEqual(n["articles"][1], "94,200")
        self.assertEqual(n["translated"][1], "21,873")
        self.assertEqual(n["complete"][1], "10,132")
        self.assertEqual(n["words_share"][1], "36 %")
        self.assertEqual(about.numbers(_stats(all=94149))["articles"][1], "94,100")
        self.assertEqual(about.numbers(_stats(all=94150))["articles"][1], "94,200")
        _t, body = about.page(S)
        self.assertIn("Bokmålsordboka has about 94,200 articles, and 21,873 of them", body)
        self.assertIn("about 36 % of it", body)
        self.assertIn("added where a sense had no example: 450 in 271 articles", body)

    def test_unknown_number_raises(self):
        with self.assertRaises(KeyError):
            about.fill("# T\n\n{nonesuch}\n", S)
        with self.assertRaises(KeyError):
            about.fill("# T\n\n[if nonesuch]x[/if]\n", S)

    def test_summary_clause(self):
        _t, body = about.page(S)
        self.assertIn("translated so far: 10,132 complete, with the short summary at the top, and "
                      "the rest with every definition and example in English, their summary still "
                      "to come. The translated articles", body)
        _t, body = about.page(_stats(complete=21873, no_summary=0))
        self.assertIn("21,873 of them have been translated so far. The translated articles", body)
        self.assertNotIn("summary still to come", body)
        self.assertNotIn("complete", body)

    def test_same_words_as_approved(self):
        """The page with today's numbers is the approved box word for word, but for "Our changes to
        the Norwegian" ("What Ordpar has changed" until 2026-10-24; decisions 121 put it
        after "The English") — the headings bold there, `##` here. That section was the box's prose until
        2026-10-23, then decisions 93 (3)'s added sentence, and since decisions 106 (Robin
        2026-10-23: "a concise bulleted list of every type of change + the count") the list
        pinned in `test_ordpar_changenotice106.py`; it is cut from both sides here. Also cut, two
        paragraphs not in the approved box, both shown since 2026-11-05 because the switches are on
        (166's go-live: `chrome.REPORT_RECEIVER` set, `chrome.PRIVACY` on):
        * the line under "Thanks" that links `/thanks/` ("Thank you to the readers who tell us
          about mistakes …", `[if reports]`): APPROVED by Robin with 166's words (site decisions
          166's follow-up, 2026-11-05), not yet copied into the box; `test_ordpar_thanks166.py`
          and `test_ordpar_reportswitch166.py` pin it;
        * the section "Privacy" ("What the site sends, what it keeps and for how long, and what
          stays on your device: Privacy.", `[if privacy]`): APPROVED by Robin, 2026-11-05 ("Keep
          it", site decisions 166), not yet copied into the box.
        Each is cut only where the page has it, so with a switch off the comparison is as before.
        Also cut, the data sentence under "Contact" (decisions 172, Robin 2026-11-07, "yes"),
        pinned by `AudioLicenceAndData172` below; the recordings' licence sentence sits inside the
        span already cut (under "Hear the words")."""
        if not os.path.exists(APPROVED):
            # the approved draft is the private record's (decisions 184: not in the public export)
            self.skipTest("the approved draft is not here: %s" % os.path.relpath(APPROVED, ROOT))
        with io.open(APPROVED, encoding="utf-8") as f:
            box = f.read().split('<Info title="About Ordpar">', 1)[1].split("</Info>", 1)[0]
        title, body = about.page(S)

        def cut(text):
            i = text.index("Our changes to the Norwegian")
            j = text.index("Search ", i)
            text = text[:i] + text[j:]
            k = text.find(" Thank you to the readers who tell us about mistakes")
            if k >= 0:
                text = text[:k] + text[text.index("plan to.", k) + len("plan to."):]  # 183: the line ends with the ideas
            p = text.find(" Privacy What the site sends, what it keeps")
            if p >= 0:
                end = "what stays on your device: Privacy."
                text = text[:p] + text[text.index(end, p) + len(end):]
            text = text.replace(" " + DATA_172, "")
            # the English's licence, reworded by site decisions 184 (Robin, 2026-11-13: the code's
            # wording); the box has the older sentence; pinned by
            # test_the_englishs_licence_in_the_codes_wording below
            text = text.replace("Whatever rights exist in it are given on the same terms",
                                "You may reuse it on the same terms")
            # the deck sentence under "Thanks", reworded by site decisions 178 (Robin, 2026-11-08,
            # "Yes, as drafted": both decks, the blended order); pinned by test_ordpar_site131.py
            s = text.find(" The same list")
            if s >= 0:
                end = "the dictionary itself stays under CC BY 4.0."
                text = text[:s] + text[text.index(end, s) + len(end):]
            return text
        self.assertEqual(cut(about.plain(body)), cut(about.plain(box)))


class AudioLicenceAndData172(unittest.TestCase):
    """Site decisions 172 (Robin, 2026-11-07): the recordings offered under CC BY 4.0 with no
    ownership claimed, as the English is ("You may reuse …"), the words they read credited as the
    text itself (they include our added examples, so not simply to Bokmålsordboka); and a way to ask
    for the data as files, in "Contact". Both on the page and so in the README."""

    def test_recordings_licence(self):
        _t, body = about.page(S)
        hear = about.plain(body).split("Hear the words", 1)[1].split("Search", 1)[0]
        self.assertIn(AUDIO_172, hear)

    def test_the_englishs_licence_in_the_codes_wording(self):
        _t, body = about.page(S)
        self.assertIn(ENGLISH_184, about.plain(body))
        self.assertNotIn("You may reuse it", about.plain(body))

    def test_data_on_request(self):
        _t, body = about.page(S)
        contact = about.plain(body).split("Contact", 1)[1]
        self.assertIn(DATA_172, contact)
        self.assertIn("post@ordpar.no", contact)


class Readme(unittest.TestCase):

    def test_readme_is_page_plus_note(self):
        md = about.readme(S)
        self.assertTrue(md.startswith("# About Ordpar\n\nOrdpar is a Norwegian"))
        self.assertIn("## This repository\n\n" + REPO_NOTE + "\n\n## How far it has come", md)
        self.assertNotIn("[readme]", md)
        self.assertNotIn("<!--", md)
        title, body = about.page(S)
        page_words = about.plain("<h1>%s</h1>%s" % (title, body))
        readme_words = about.plain(md).replace("This repository " + REPO_NOTE + " ", "")
        self.assertEqual(readme_words, page_words)
        # its links as Markdown, as the source has them
        self.assertIn("[ordbokene.no](https://ordbokene.no/)", md)

    def test_readme_summary_clause_follows(self):
        self.assertNotIn("summary still to come", about.readme(_stats(no_summary=0)))

    def test_deploy_readme_out(self):
        tmp = tempfile.mkdtemp()
        bj = os.path.join(tmp, "build.json")
        with io.open(bj, "w", encoding="utf-8") as f:
            json.dump({"site_stats": S}, f)
        out = os.path.join(tmp, "README.md")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "ordpar", "deploy.py"), "readme",
                            "--out", out, "--build-json", bj],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        with io.open(out, encoding="utf-8", newline="") as f:
            got = f.read()
        self.assertEqual(got, about.readme(S))
        self.assertNotIn("\r", got)
        with io.open(bj, "w", encoding="utf-8") as f:
            json.dump({"pages": 1}, f)
        with self.assertRaises(SystemExit):
            deploy.readme_text(bj)

    def test_deploy_readme_is_retired(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "ordpar", "deploy-README.md")))
        self.assertFalse(hasattr(deploy, "README"))


class AddedMark(unittest.TestCase):

    class _Mk:
        def expand(self, text, norwegian=False, strict=False):
            return text

    def test_site_says_ordpar(self):
        self.assertEqual(article.ADDED_MARKER, ordbok_gen._ADDED_MARKER.replace(
            "Example added by this deck", "Example added by Ordpar"))
        self.assertIn('title="Example added by Ordpar (not from Bokmålsordboka)"',
                      article.ADDED_MARKER)
        # the deck's own is untouched
        self.assertIn("Example added by this deck (not from Bokmålsordboka)",
                      ordbok_gen._ADDED_MARKER)

    def test_rendered_example(self):
        html = article._ex_list({"ex_added": [{"no": "ei setning"}]},
                                {"ex_added": [{"en": "a sentence"}]}, self._Mk(), False)
        self.assertIn("Example added by Ordpar (not from Bokmålsordboka)", html)
        self.assertNotIn("this deck", html)
        self.assertEqual(len(re.findall(r'class="ordbok-added"', html)), 1)


if __name__ == "__main__":
    unittest.main()
