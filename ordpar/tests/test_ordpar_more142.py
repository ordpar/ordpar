"""Site-review decisions 142 (Robin, 2026-10-26/27): the page "More ways to use Ordpar" at `/more/`,
the home page's line to it under Random word, its footer link on every page, and the line "Type a
Norwegian word to search the dictionary." dropped everywhere — the source side and the built pages.

* **The words** (`ordpar/more.md`): the approved draft's, compared with the draft's box
  (`docs/sessions/2026-09-19-ordpar-site-review/walk-through/more-ways-page-draft-2026-10-26.md`,
  § The draft, as it would read, the `<Info>` box) read at test time, both normalized for markup
  (headings, bold, italics, links, backticks and step numbers dropped) — not a copy here. The
  differences allowed: the draft's "Microsoft Edge Add-ons (link to come)" is, on the page, the
  store's name linked (the address the session supplied, 2026-10-27); and site decisions 146's
  approved words (Robin, 2026-10-28) — step 4, the sentence after step 8, the theme sentence
  (`AMENDED_146`, pinned exactly in `test_ordpar_settingsaddr146.py`); site decisions 152's (`AMENDED_152`);
  and site decisions 178's (Robin, 2026-11-08): the Anki section first, its words `ANKI_178`.
* **The page** (`about.more_page`, `page.more_page`, built `out/more/index.html`): the title "More
  ways to use Ordpar — Ordpar", the sections `#anki`, `#popup`, `#offline` in order (178: Anki first), 8 Definer steps
  and 3 Anki steps, the Definer URL and CSS each a line of code under its step, exactly; the step
  and code rules in the About page's sheet (`page.PAGE_CSS`, the code `user-select: all`; since
  site decisions 146 a Copy button beside each line, made by `shell.js`, so none in the built
  markup, and the URL's line marked `data-ordpar-popup`); indexed (no `noindex`, its canonical) and in the sitemap (both writers' `INDEXED_OTHER`).
* **The home page's line**: its words in `strings/en.json` (`home.more`, `home.moreLink`), inlined in
  the built home page; `shell.js` `addMoreLine` makes it on the home page only, before the results,
  the link on "more ways to use Ordpar" to `/more/`; `shell.css` shows it only with `ordpar-idle`,
  which `lookup.js` `render` sets for an empty query and `searching` clears.
* **The footer link**, after Help (`chrome.MORE_HREF`, `footer.more`), on one built page of each
  kind; relabelled with the chrome (`chrome.RELABEL` and `shell.js` `STATIC_STRINGS`).
* **The dropped line**: `results.empty` gone from the strings and `lookup.js`, and its words from
  every built page and script.

In a browser: `test_ordpar_browser_more142.py`. The built half reads `ordpar/out/`
(`ORDPAR_TEST_OUT` another) and is skipped without a build. Stdlib unittest.
"""
import html
import json
import os
import re
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(REPO, "ordpar", "out")
SITE = os.path.join(REPO, "ordpar", "site")
DRAFT = os.path.join(REPO, "docs", "sessions", "2026-09-19-ordpar-site-review", "walk-through",
                     "more-ways-page-draft-2026-10-26.md")

from ordpar.sitegen import about, chrome, page  # noqa: E402

TITLE = "More ways to use Ordpar"
URL = "https://ordpar.no/bm-en/#q={{str}}"
# site decisions 152: a second rule, the headword's Norwegian-only icon in the pop-up
CSS = (".ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; } "
       ".ordpar-nbhw { display: inline-flex !important; }")
EDGE = "https://microsoftedge.microsoft.com/addons/detail/definer-word-translator/bmjggedeimdncfelfdcphnmbknkmfffp"
DROPPED = "Type a Norwegian word to search the dictionary."
LINE = "Look words up from any web page, or practise them in Anki: more ways to use Ordpar"
#: Site decisions 146 (Robin, 2026-10-28): the approved draft's words that 146 replaced, and
#: the sentence it added after the eight steps — (before, after), applied to the draft's words
AMENDED_146 = (
    ("In the URL field, paste: https://",
     "In the URL field, paste the address below. If you have changed any settings on ordpar.no, the "
     "address carries them, so the pop-up shows articles the way you see them here: https://"),
    ("press Definer's icon. A word with several articles",
     "press Definer's icon. If you change your settings later, copy the address again, here or at "
     "the bottom of Settings, and paste it over the old one in Definer's URL field. A word with "
     "several articles"),
    ("The pop-up follows your browser's light or dark mode.",
     "The pop-up follows your browser's light or dark mode, unless you have chosen one in Settings."),
)
#: Site decisions 152 (2026-10-31): step 7's line with the headword icon's rule, and a sentence after
#: the settings paragraph (a DRAFT for Robin)
AMENDED_152 = (
    ("{ display: none !important; } Select a word",
     "{ display: none !important; } .ordpar-nbhw { display: inline-flex !important; } Select a word"),
    ("in Definer's URL field. A word with several articles",
     "in Definer's URL field. The CSS line also shows a button beside the headword in the pop-up "
     "that switches Norwegian only on or off, for that pop-up only. If your CSS field holds the line "
     "without its .ordpar-nbhw part, paste the line again to get the button. A word with several "
     "articles"),
)


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _norm(markdown):
    """Markdown's visible words: comments, `{#id}`, heading marks, bold and italic stars, link
    targets, backticks and step numbers dropped; whitespace collapsed."""
    t = re.sub(r"<!--.*?-->", " ", markdown, flags=re.S)
    t = re.sub(r"\s*\{#[a-z0-9-]+\}", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)\s]+\)", r"\1", t)
    t = re.sub(r"(?m)^#+ ", "", t)
    t = re.sub(r"(?m)^\s*\d+\. ", "", t)
    t = t.replace("**", "").replace("`", "")
    t = re.sub(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])", r"\1", t)
    return " ".join(t.split())


def _draft_box():
    if not os.path.exists(DRAFT):
        # the draft is the private record's (decisions 184: not in the public export)
        raise unittest.SkipTest("the approved draft is not here: %s" % os.path.relpath(DRAFT, REPO))
    text = _read(DRAFT)
    m = re.search(r'<Info title="More ways to use Ordpar[^"]*">\s*(.*?)\s*</Info>', text, re.S)
    assert m, "the draft's box not found in " + DRAFT
    return m.group(1)


#: Site decisions 178 (Robin, 2026-11-08: the draft "looks ok", A36): the opening's list reordered,
#: and the Anki section first, rewritten for the one-deck edition — its words pinned here, exactly
OPENING_178 = ("as a pop-up on any web page, as flashcards in Anki, and on your own device",
               "as flashcards in Anki, as a pop-up on any web page, and on your own device")
ANKI_178 = """## Practise the words in Anki {#anki}

Anki is a free flashcard program that shows you the cards you find hard more often than the ones you already know. Ordpar's Anki deck, [*Ordpar: Norwegian Core Vocabulary*](https://ankiweb.net/shared/info/1906319472), has about 6,000 core Norwegian words, sorted into levels from A1 to C2, the most frequent first. The back of each card is the word's Ordpar article, with the Norwegian read aloud and small articles for linked words that open with no network needed. If you're stuck, a Hint button on the front shows a Norwegian example. Every word also has a card from English to Norwegian. To start:

1. Install Anki on your computer from [apps.ankiweb.net](https://apps.ankiweb.net/). It is free for Windows, Mac and Linux.
2. Open the deck on AnkiWeb and press Download.
3. Double-click the downloaded file to add it to Anki, or use File → Import.

On a phone, AnkiDroid for Android is free, and AnkiMobile for iPhone and iPad is paid. In AnkiDroid you can add the deck directly: open its Shared Decks, search for "Ordpar", and choose *Ordpar: Norwegian Core Vocabulary*. On an iPhone or iPad, add the deck on your computer and sync both through a free AnkiWeb account. The deck's page on AnkiWeb says how to practise with it, and [Changes to the Ordpar Anki decks](https://ordpar.no/deck-changes/) lists what each update changed.

The same cards also come as *6000 Most Frequent Norwegian Words*, in two parts ([Part 1](https://ankiweb.net/shared/info/1989661164), [Part 2](https://ankiweb.net/shared/info/879167685)), which carry more of the audio in the download, for studying offline. If you already study the two parts, the new deck's page says how to switch and keep your progress."""


def _amend_178(draft):
    """The draft's words with 178's change: the old Anki section out, the new one before the pop-up's."""
    before, after = OPENING_178
    assert draft.count(before) == 1, before
    draft = draft.replace(before, after)
    i, j = draft.index("Practise the words in Anki "), draft.index("Use it without a connection ")
    draft = draft[:i] + draft[j:]
    k = draft.index("Look up words on any web page ")
    return draft[:k] + _norm(ANKI_178) + " " + draft[k:]


class Words(unittest.TestCase):

    def test_the_words_are_the_drafts(self):
        draft = _norm(_draft_box()).replace("Microsoft Edge Add-ons (link to come)",
                                            "Microsoft Edge Add-ons")
        for before, after in AMENDED_146 + AMENDED_152:
            self.assertEqual(draft.count(before), 1, before)
            draft = draft.replace(before, after)
        draft = _amend_178(draft)
        source = _read(about.MORE_SOURCE)
        self.assertTrue(source.lstrip().startswith("<!--"))
        lead = source[:source.index("-->")]
        self.assertIn("site decisions 142", lead)
        self.assertIn("more-ways-page-draft-2026-10-26.md", lead)
        mine = _norm(source[source.index("-->") + 3:])
        self.assertEqual(mine, draft)

    def test_the_links(self):
        src = _read(about.MORE_SOURCE)
        self.assertIn("[Microsoft Edge Add-ons](%s)" % EDGE, src)
        self.assertNotIn("EDGE:", src)
        for href in ("https://chromewebstore.google.com/detail/definer-word-translator-a/noagjioaihamoljcbelhdlldnmlgnkon",
                     "https://addons.mozilla.org/en-US/firefox/addon/lumetrium-definer",
                     "https://ankiweb.net/shared/info/1989661164", "https://ankiweb.net/shared/info/879167685",
                     "https://apps.ankiweb.net/", "https://ordpar.no/settings/#data",
                     "https://ankiweb.net/shared/info/1906319472", "https://ordpar.no/deck-changes/"):
            self.assertIn("](%s)" % href, src)


def _sections(body):
    """{id: the section's HTML up to the next h2}."""
    parts = re.split(r'(?=<h2 id=")', body)
    return {re.match(r'<h2 id="([^"]+)"', p).group(1): p for p in parts if p.startswith("<h2 id=")}


class ThePage(unittest.TestCase):

    def setUp(self):
        self.title, self.body = about.more_page()

    def test_title_ids_steps_code(self):
        self.assertEqual(self.title, TITLE)
        self.assertEqual(re.findall(r'<h2 id="([^"]+)"', self.body), ["anki", "popup", "offline"])
        sec = _sections(self.body)
        self.assertEqual(sec["popup"].count("<li>"), 8)
        self.assertEqual(sec["anki"].count("<li>"), 3)
        self.assertEqual(sec["offline"].count("<li>"), 0)
        codes = re.findall(r'<div class="ordpar-code"><code[^>]*>(.*?)</code></div>', self.body)
        self.assertEqual([html.unescape(c) for c in codes], [URL, CSS])
        self.assertIn('the way you see them here:<div class="ordpar-code"><code data-ordpar-popup>',
                      sec["popup"])
        self.assertIn('<li>In the CSS field, paste:<div class="ordpar-code"><code>', sec["popup"])
        self.assertIn('<a href="%s">Microsoft Edge Add-ons</a>' % EDGE, sec["popup"])
        self.assertIn("<em>husene</em>", sec["popup"])
        # site decisions 146: the Copy buttons are made by the page's script, not built
        self.assertNotIn("<button", self.body)

    def test_the_sheet(self):
        css = page.PAGE_CSS
        self.assertIn(".ordpar-about ol>li::marker{font-weight:700;color:var(--ordpar-accent)}", css)
        rule = re.search(r"\.ordpar-code code\{(.*?)\}", css, re.S).group(1)
        self.assertIn("user-select:all", rule)
        self.assertIn("background:var(--ordpar-pill)", rule)

    def test_wired_as_help(self):
        from ordpar import build_site
        from ordpar.sitegen import wordpages
        self.assertEqual(chrome.MORE_HREF, "/more/")
        for other in (build_site.INDEXED_OTHER, wordpages.INDEXED_OTHER):
            self.assertIn("/more/", other)
        self.assertIn('page_mod.more_page(stamp, EN)', _read(REPO, "ordpar", "build_site.py"))
        built = page.more_page("ordpar build: t", page.EN)
        self.assertIn("<title>More ways to use Ordpar — Ordpar</title>", built)
        self.assertIn('<link rel="canonical" href="https://ordpar.no/more/">', built)
        self.assertNotIn("noindex", built)

    def test_in_the_offline_copy(self):
        # found after the build: /more/ was missing from the offline shell pages, so offline its links led nowhere
        from ordpar import build_offline
        self.assertEqual(build_offline.SHELL_PAGES.get("/more/"), "more/index.html")


class TheChrome(unittest.TestCase):

    def test_strings(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertNotIn("results.empty", s)
        self.assertEqual(s["footer.more"], "More ways to use Ordpar")
        self.assertEqual(s["home.more"].replace("{link}", s["home.moreLink"]), LINE)
        self.assertTrue(s["home.more"].endswith(": {link}"))
        self.assertEqual(s["home.moreLink"], "more ways to use Ordpar")

    def test_footer_after_help(self):
        f = chrome.footer(chrome.strings("en"), noindex=False, privacy=False)
        self.assertIn('<a href="/help/">Help</a>\n<a href="/more/">More ways to use Ordpar</a>\n'
                      '<a href="/about/">', f)          # a newline between the links (154)
        self.assertIn(('.ordpar-footer-nav a[href="/more/"]', "footer.more"), chrome.RELABEL)
        self.assertIn("""['.ordpar-footer-nav a[href="/more/"]', 'footer.more']""", _read(SITE, "shell.js"))

    def test_the_home_line_scripts(self):
        js = _read(SITE, "shell.js")
        body = js.split("function addMoreLine() {")[1].split("\n  }\n")[0]
        self.assertIn("global.location.pathname !== base()", body)
        self.assertIn("'home.more'", body)
        self.assertIn("labelled('a', '', 'home.moreLink')", body)
        self.assertIn("base() + 'more/'", body)
        self.assertIn("main.insertBefore(line, results)", body)
        self.assertIn("addMoreLine();", js.split("function addChrome() {")[1].split("\n  }\n")[0])
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-more-line {\n  display: none;", css)
        self.assertIn(".ordpar-main.ordpar-idle > .ordpar-more-line { display: block; }", css)
        lk = _read(SITE, "lookup.js")
        self.assertIn("idle(root, !g.ok && g.reason === 'empty');", lk)
        searching = lk.split("function searching(root, query) {")[1].split("\n  }\n")[0]
        self.assertIn("idle(root, false);", searching)
        self.assertNotIn("results.empty", lk)


#: one built page of each kind the footer shows on
KINDS = {"article": ("bm-en", "98", "index.html"), "word page": ("bm-en", "hus", "index.html"),
         "form page": ("bm-en", "tær", "index.html"), "about": ("about", "index.html"),
         "help": ("help", "index.html"), "coming": ("coming", "index.html"),
         "more": ("more", "index.html"), "home": ("index.html",), "search": ("bm-en", "index.html"),
         "404": ("404.html",), "settings": ("settings", "index.html"),
         "history": ("history", "index.html"), "favourites": ("favourites", "index.html")}


@unittest.skipUnless(os.path.exists(os.path.join(OUT, "more", "index.html")), "no build with /more/ in " + OUT)
class Built(unittest.TestCase):

    def test_the_page(self):
        t = _read(OUT, "more", "index.html")
        self.assertIn("<title>More ways to use Ordpar — Ordpar</title>", t)
        self.assertIn('<link rel="canonical" href="https://ordpar.no/more/">', t)
        self.assertNotIn("noindex", t)
        self.assertEqual(re.findall(r'<h2 id="([^"]+)"', t), ["anki", "popup", "offline"])
        sec = _sections(t[t.index('<article class="ordpar-about">'):t.index("</article>")])
        self.assertEqual(sec["popup"].count("<li>"), 8)
        self.assertEqual(sec["anki"].count("<li>"), 3)
        codes = re.findall(r'<div class="ordpar-code"><code[^>]*>(.*?)</code></div>', t)
        self.assertEqual([html.unescape(c) for c in codes], [URL, CSS])

    def test_in_the_sitemap(self):
        self.assertIn("<loc>https://ordpar.no/more/</loc>", _read(OUT, "sitemap.xml"))

    def test_the_home_page_carries_the_line(self):
        t = _read(OUT, "index.html")
        self.assertIn('"home.more":"Look words up from any web page, or practise them in Anki: {link}"',
                      t.replace('": "', '":"'))
        self.assertIn('"home.moreLink":"more ways to use Ordpar"', t.replace('": "', '":"'))
        self.assertIn("addMoreLine", _read(OUT, "site", "shell-pages.js"))

    def test_footer_on_each_kind(self):
        for kind, parts in KINDS.items():
            path = os.path.join(OUT, *parts)
            if not os.path.exists(path):
                self.fail("%s: %s not built" % (kind, path))
            t = _read(path)
            nav = re.search(r'<nav class="ordpar-footer-nav".*?</nav>', t, re.S)
            self.assertTrue(nav, kind)
            # the order; the newline between the links since site decisions 154 (either build)
            self.assertRegex(nav.group(0), r'<a href="/help/">Help</a>\n?<a href="/more/">More ways to use '
                             r'Ordpar</a>\n?<a href="/about/">', kind)

    def test_the_dropped_line_on_no_built_page(self):
        files = []
        for d, _sub, names in os.walk(OUT):
            files.extend(os.path.join(d, n) for n in names if n.endswith((".html", ".js", ".json")))
        needle, key = DROPPED.encode("utf-8"), b"results.empty"

        def has(p):
            with open(p, "rb") as f:
                b = f.read()
            return p if (needle in b or key in b) else None
        with ThreadPoolExecutor(16) as ex:
            found = [p for p in ex.map(has, files) if p]
        self.assertGreater(len(files), 1000)
        # site decisions 175: the site's change list, a public page since, quotes the line it says is
        # gone ("A quieter home page. The line "Type a Norwegian word …" is gone.") — history, not
        # the line shown
        changes = os.path.join(OUT, "changes", "index.html")
        if changes in found:
            with open(changes, encoding="utf-8") as f:
                text = f.read()
            quoted = 'The line "%s" is gone.' % DROPPED
            self.assertEqual(text.count(DROPPED), text.count(quoted))   # only ever as that quotation
            self.assertGreater(text.count(quoted), 0)
            self.assertNotIn("results.empty", text)
            found.remove(changes)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
