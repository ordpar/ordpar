"""Site-review decisions 131 (2026-10-25/26): what the deck's release asks of the site — the
source side and the built pages. The words are the proposal's
(`docs/sessions/2026-09-19-ordpar-site-review/walk-through/proposal-131-site-items-2026-10-25.md`),
the session's call at Robin's delegation, the fifth `/coming/` item his ruling; the e-mail address
the proposal writes as "[Ordpar's post address]" is the privacy page's own, post@ordpar.no.

* **The deck under "Thanks"** (`about.md`): the second paragraph word for word, the deck's name in
  italics (`<em>`, `*…*` in the README), both AnkiWeb links; in the page and in the README.
* **"Contact"**: the last section, after "No warranty", its heading's id `contact` (the deck's
  AnkiWeb page links `https://ordpar.no/about/#contact`), the one sentence, the address a `mailto:`
  link; every About heading has its id now, as Help's; no footer link.
* **`/coming/`** (`coming.md`, `about.coming_page`, `page.coming_page`): the title, the intro and the
  six items with their *Waiting for:* lines, in order; About links it at the end of "How far it has
  come"; built, indexed (no `noindex`), its canonical, in the sitemap after Help (both sitemap
  writers' `INDEXED_OTHER`); no footer link.
* **The eye's setting** (`exeye`): right under Examples, Off first and the default; its words in
  `strings/en.json` exactly; the head script's class `ordpar-exeye-on`; `shell.js` toggling it; the
  export carrying it; the page script's button (`eyes`, `eye`) with its name from `strings.py`, and
  the sheet's rules (hidden unless the class is on; the hidden English never reaching a mini).
* **The tab title** (117's one style): `lookup.js` `pageTitle` reads `dictionary_name`, and the
  shell pages' inline strings carry it from `strings.py` (never a fixed copy).

`ORDPAR_TEST_ROOT` names another copy of the repository's `ordpar/` parent (`git archive HEAD
ordpar` unpacked) to show the source half failing on the version before the change; the built
half reads `ordpar/out/` (`ORDPAR_TEST_OUT` another). In a browser: `test_ordpar_browser_eye131.py`,
`test_ordpar_browser_tabtitle131.py`, `test_ordpar_browser_pages131.py`.

Stdlib unittest.
"""
import html
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("ORDPAR_TEST_ROOT") or REPO
sys.path.insert(0, REPO)
sys.path.insert(0, ROOT)
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(REPO, "ordpar", "out")

from ordpar.sitegen import about, chrome, head, page  # noqa: E402
from ordpar.sitegen import strings as strings_mod  # noqa: E402

SITE = os.path.join(ROOT, "ordpar", "site")
S = about.SAMPLE

#: decisions 131's paragraph, as decisions 178 (Robin, 2026-11-08) reworded it: both decks, the blended order
DECK = ("The same list, blended with how often each word is used in film and TV subtitles "
        "([Hermit Dave's FrequencyWords](https://github.com/hermitdave/FrequencyWords), CC BY-SA 4.0), sets the "
        "order of Ordpar's Anki decks, [*Ordpar: Norwegian Core Vocabulary*](https://ankiweb.net/shared/info/1906319472) "
        "and *6000 Most Frequent Norwegian Words* ([Part 1](https://ankiweb.net/shared/info/1989661164), "
        "[Part 2](https://ankiweb.net/shared/info/879167685)), whose cards show each word's Ordpar article. Because "
        "their word order comes from these two lists, the decks are licensed CC BY-SA 4.0, as the lists are; the "
        "dictionary itself stays under CC BY 4.0.")
DECK_HTML = ("<p>The same list, blended with how often each word is used in film and TV subtitles "
             "(<a href=\"https://github.com/hermitdave/FrequencyWords\">Hermit Dave's FrequencyWords</a>, CC BY-SA "
             "4.0), sets the order of Ordpar's Anki decks, <a href=\"https://ankiweb.net/shared/info/1906319472\">"
             "<em>Ordpar: Norwegian Core Vocabulary</em></a> and <em>6000 Most Frequent Norwegian Words</em> "
             "(<a href=\"https://ankiweb.net/shared/info/1989661164\">Part 1</a>, "
             "<a href=\"https://ankiweb.net/shared/info/879167685\">Part 2</a>), whose cards show each word's Ordpar "
             "article. Because their word order comes from these two lists, the decks are licensed CC BY-SA 4.0, as "
             "the lists are; the dictionary itself stays under CC BY 4.0.</p>")
CONTACT = ("Write to us at [post@ordpar.no](mailto:post@ordpar.no) about a mistake in an article, the "
           "Anki deck, or anything else about Ordpar. If you would like the dictionary's data as files, "
           "the articles or the recordings, write to us there too.")  # the last sentence: decisions 172
CONTACT_HTML = ('<h2 id="contact">Contact</h2>\n<p>Write to us at <a href="mailto:post@ordpar.no">'
                "post@ordpar.no</a> about a mistake in an article, the Anki deck, or anything else "
                "about Ordpar. If you would like the dictionary's data as files, the articles or the "
                "recordings, write to us there too.</p>")
COMING_LINK = "What we have decided to build next: [Coming to Ordpar](https://ordpar.no/coming/)."
COMING_TITLE = "Coming to Ordpar"
COMING_INTRO = ("What we have decided to build, and what each is waiting for. There are no dates: each "
                "comes when what it waits for is in place.")
COMING_ITEMS = [
    # "English to Norwegian search." went with its build (site decisions 148, 2026-10-29)
    # "Norwegian you can listen to." went with the audio (site decisions 159, live 2026-11-02),
    # moved to Built 2026-11-07
    ("Ordpar in Norwegian.", "The menus, the settings and the articles' labels in Norwegian, as a "
     "choice.", "the site's first full version (1.0), when its building stage ends."),
    ("More languages.", "Bokmålsordboka's articles in other languages than English.",
     "the English to be complete."),
    ("More example sentences.", "New examples for the articles and senses that have none yet, each "
     "one checked by hand before it is added.", "time to check them."),
    # Robin's sixth item, 2026-10-26 (decisions 131), the words the session's
    ("Better English equivalents.", "Every English equivalent under a headword reviewed, and each "
     "linked to the sense of the article it translates; pointing at one, or pressing it, will show its "
     "senses in the article.", "the revision of the lexicographical principles our work builds on, then "
     "time to do the work."),
]
EYE_WORDS = {
    "settings.exeye": "An eye button for the examples' English",
    "settings.exeye.off": "Off",
    "settings.exeye.on": "On",
    "settings.exeye.hint": ("On: an eye beside the headword hides the English of every example in the "
                            "article, or shows it again, so you can switch between reading the "
                            "Norwegian and checking yourself without opening Settings. While the "
                            "English is hidden, \"Show English\" under an example reveals that one. "
                            "The Examples setting above decides how an article opens."),
}


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class PollyLink(unittest.TestCase):
    """Robin, 2026-11-09: the About page's audio sentence links Amazon Polly
    ("[Amazon Polly's](https://aws.amazon.com/polly/) synthetic Norwegian voice")."""
    LINK = "[Amazon Polly's](https://aws.amazon.com/polly/) synthetic Norwegian voice"

    def test_the_source_and_the_readme(self):
        self.assertIn("read by Ida, " + self.LINK + ".", _read(ROOT, "ordpar", "about.md"))
        self.assertIn(self.LINK, about.readme(S))

    def test_the_page(self):
        _t, body = about.page(S)
        self.assertRegex(body, r'<a href="https://aws\.amazon\.com/polly/"[^>]*>Amazon Polly(?:&#x27;|&#39;|\'|’)s</a>')

    def test_help_and_coming(self):
        # "Yes, both" (Robin, 2026-11-09): the same link wherever the site names Polly (one style)
        self.assertIn("read by Ida, [Amazon Polly's](https://aws.amazon.com/polly/) synthetic Norwegian Bokmål voice",
                      _read(ROOT, "ordpar", "help.md"))
        self.assertIn("reads it aloud in Ida, " + self.LINK + ".", _read(ROOT, "ordpar", "coming.md"))
        for name in ("help.md", "coming.md", "about.md"):
            src = _read(ROOT, "ordpar", name)
            self.assertEqual(src.count("Amazon Polly"), src.count("[Amazon Polly's](https://aws.amazon.com/polly/)"), name)


class Thanks(unittest.TestCase):

    def test_the_paragraph_in_the_source_after_the_kelly_one(self):
        src = _read(ROOT, "ordpar", "about.md")
        sec = src.split("## Thanks\n\n", 1)[1].split("\n\n## ", 1)[0]
        paras = sec.strip("\n").split("\n\n")
        self.assertTrue(paras[0].startswith("The articles we translated first were chosen from"))
        self.assertEqual(paras[1].split("\n\n")[0], DECK)

    def test_the_page(self):
        _t, body = about.page(S)
        self.assertIn(DECK_HTML, body)
        self.assertLess(body.index("Thank you to the Text Laboratory"), body.index(DECK_HTML))

    def test_the_readme(self):
        md = about.readme(S)
        self.assertIn("\n\n" + DECK + "\n\n", md)


class Contact(unittest.TestCase):

    def test_last_section_with_its_id(self):
        _t, body = about.page(S)
        self.assertTrue(body.endswith(CONTACT_HTML), body[-400:])
        self.assertLess(body.index('<h2 id="no-warranty">No warranty</h2>'), body.index(CONTACT_HTML))

    def test_every_about_heading_has_an_id(self):
        _t, body = about.page(S)
        heads = re.findall(r"<h2[^>]*>", body)
        self.assertTrue(heads)
        self.assertEqual([h for h in heads if " id=" not in h], [])

    def test_the_readme_ends_with_it(self):
        self.assertTrue(about.readme(S).endswith("## Contact\n\n" + CONTACT + "\n"))

    def test_no_footer_link(self):
        f = chrome.footer(chrome.strings("en"))
        self.assertNotIn("#contact", f)
        self.assertNotIn("/coming/", f)


class Coming(unittest.TestCase):

    def test_the_link_on_about(self):
        src = _read(ROOT, "ordpar", "about.md")
        sec = src.split("## How far it has come\n\n", 1)[1].split("\n\n", 1)[0]
        self.assertTrue(sec.endswith("and then to add other languages. " + COMING_LINK), sec[-200:])
        _t, body = about.page(S)
        self.assertIn('What we have decided to build next: <a href="https://ordpar.no/coming/">Coming '
                      'to Ordpar</a>.</p>', body)

    def test_the_page_text(self):
        title, body = about.coming_page()
        self.assertEqual(title, COMING_TITLE)
        want = "<p>%s</p>\n<ul>\n%s\n</ul>" % (COMING_INTRO, "\n".join(
            "<li><strong>%s</strong> %s <em>Waiting for:</em> %s</li>" % (
                html.escape(a, quote=False),
                re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html.escape(b, quote=False)), c)
            for a, b, c in COMING_ITEMS))
        # site decisions 148 (Robin, 2026-10-29): a "Built" section where items move as they land
        want += ('\n<h2 id="built">Built</h2>\n<p>What we have built from this list, newest first.</p>\n<ul>\n'
                 '<li><strong>Norwegian you can listen to.</strong> A sound icon after every headword, example '
                 'sentence and Norwegian definition line, and on the forms in the inflection tables of the core '
                 'vocabulary, of every irregular word and of every adjective, reads it aloud in Ida, '
                 '<a href="https://aws.amazon.com/polly/">Amazon Polly\'s</a> '   # linked, 181 (2026-11-09)
                 "synthetic Norwegian voice. <em>Built:</em> 2 November 2026.</li>\n"
                 '<li><strong>English to Norwegian search.</strong> Switch on "Search English words" under '
                 'the search box to find the Norwegian articles whose English equivalents contain an English '
                 'word. <em>Built:</em> 30 October 2026.</li>\n</ul>')
        self.assertEqual(body, want)

    def test_the_whole_page(self):
        t = page.coming_page("ordpar build: t", page.EN)
        self.assertIn("<title>Coming to Ordpar — Ordpar</title>", t)
        self.assertIn('<link rel="canonical" href="https://ordpar.no/coming/">', t)
        self.assertNotIn("noindex", t)
        # site decisions 176: the about pages' tabs between the title and the first paragraph
        self.assertRegex(t, r'(?s)<article class="ordpar-about">\n<h1>Coming to Ordpar</h1>\n'
                            r'<nav class="ordpar-tabs" aria-label="About Ordpar">\n.*?</nav>\n<p>What we have')

    def test_both_sitemap_writers_list_it_after_help(self):
        from ordpar import build_site
        from ordpar.sitegen import wordpages
        for other in (build_site.INDEXED_OTHER, wordpages.INDEXED_OTHER):
            self.assertEqual(other[:4], ("/", "/about/", "/help/", "/coming/"))   # /more/ after, decisions 142


class TheEyeSetting(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_right_under_examples_off_first(self):
        self.assertIn("{ key: 'exeye', values: ['off', 'on'], def: 'off', section: 'article', "
                      "sub: 'language' }", self.js)
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        self.assertEqual(order[order.index("examples") + 1], "exeye")

    def test_the_words(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        for k, v in EYE_WORDS.items():
            self.assertEqual(s.get(k), v, k)

    def test_the_class(self):
        self.assertIn("s.getItem('exeye')==='on'&&c.add('ordpar-exeye-on');", head.THEME_JS)
        self.assertIn("cl.toggle('ordpar-exeye-on', getSetting('exeye') === 'on');", self.js)
        keys = self.js.split("var CLASS_KEYS = [")[1].split("];")[0]
        self.assertIn("'exeye'", keys)
        exp = re.search(r"var SETTING_KEYS = \[([^\]]*)\]", _read(SITE, "personal.js")).group(1)
        self.assertIn("'exeye'", exp)

    def test_the_page_script(self):
        js = page.PAGE_JS
        self.assertIn("EYE=" + json.dumps(strings_mod.EN["exeye_button"]), js)
        self.assertEqual(strings_mod.EN["exeye_button"], "Hide the examples' English")
        self.assertIn("eyes();nbhw();phord();};", js)        # run by every ordparDefs (152: nbhw; 188: phord)
        self.assertIn("var y=t.closest('.ordpar-exeye-btn');if(y){eye(y);return;}", js)
        self.assertIn("b.type='button';b.className='ordpar-exeye-btn';b.setAttribute('aria-label',EYE)", js)
        self.assertIn("setAttribute('aria-pressed'", js)
        # nothing at all while the setting is off: the buttons removed, none made
        self.assertIn("if(!on){var ws=d.querySelectorAll('.ordpar-exeye');", js)
        self.assertIn("a.closest('.ordbok-xmini,.ordpar-row-button')", js)

    def test_the_sheet(self):
        css = page.article_css()
        self.assertIn("html:not(.ordpar-exeye-on) .ordpar-exeye{display:none}", css)
        self.assertIn(".ordpar-exhide .ordbok-ex-list:not(.ordbok-xmini *)>li:not(.ordpar-open)>"
                      ".ordpar-en{display:none}", css)
        self.assertIn(".ordpar-exeye>button[aria-pressed=true]{background:var(--ordpar-accent)", css)
        # styled through its span, never by the button's own class: the deck shares this sheet and
        # its asset build refuses a styled button class outside its BUTTON_CLASSES
        self.assertNotIn(".ordpar-exeye-btn", css)


class TabTitle(unittest.TestCase):

    def test_lookup_reads_the_dictionary_name(self):
        js = _read(SITE, "lookup.js")
        self.assertIn("function pageTitle(res)", js)
        self.assertIn("word + ' — ' + t('dictionary_name')", js)
        code = re.sub(r"(?m)^\s*//.*$", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))
        self.assertNotIn("Norwegian–English dictionary", code)     # never a fixed copy


BUILT = os.path.exists(os.path.join(OUT, "build.json"))


@unittest.skipUnless(BUILT, "no built site in %s" % OUT)
class Built(unittest.TestCase):

    def test_about(self):
        t = _read(OUT, "about", "index.html")
        self.assertIn(DECK_HTML, t)
        self.assertIn(CONTACT_HTML, t)
        self.assertIn('<a href="https://ordpar.no/coming/">Coming to Ordpar</a>', t)

    def test_coming(self):
        t = _read(OUT, "coming", "index.html")
        self.assertIn("<title>Coming to Ordpar — Ordpar</title>", t)
        self.assertNotIn(head.ROBOTS_NOINDEX, t)
        self.assertEqual(t.count("<em>Waiting for:</em>"), len(COMING_ITEMS))

    def test_sitemap(self):
        locs = re.findall(r"<loc>([^<]+)</loc>", _read(OUT, "sitemap.xml"))
        self.assertEqual(locs[:4], ["https://ordpar.no/", "https://ordpar.no/about/",
                                    "https://ordpar.no/help/", "https://ordpar.no/coming/"])

    def test_shell_pages_carry_the_dictionary_name(self):
        want = strings_mod.EN["dictionary_name"]
        for name in ("404.html", os.path.join("bm-en", "index.html"), "index.html"):
            t = _read(OUT, name)
            m = re.search(r"window\.ORDPAR_STRINGS=(\{.*?\});</script>", t, re.S)
            self.assertIsNotNone(m, name)
            self.assertEqual(json.loads(m.group(1))["en"]["dictionary_name"], want, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
