# -*- coding: utf-8 -*-
"""Site decisions 175, 176 and 177 (Robin, 2026-11-07): the three change lists as public pages, the
tabs over the about pages, the footer's "About", and "What's new" in the update note. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-changes-tabs-175-177-2026-11-07.md`.

* **The three pages** (175, 177): `/changes/` from `ordpar/changes.md`, `/dictionary-changes/` from
  `ordpar/library-changes.md`, `/deck-changes/` from `ordpar/deck-changes.md` (`about.changes_page`,
  `library_changes_page`, `deck_changes_page`; `page.changes_page` …), built as `/coming/` is from
  `coming.md`: the leading comment dropped, the About page's Markdown subset — with a list item's
  wrapped lines (indented two spaces) joined into the item, which the three files need — no build
  numbers. Each page's title is its file's `# ` line, its opening the file's first paragraph; every
  word of the file (its comment and title aside) on the page, every `- ` item one `<li>`; every
  dated `## ` heading with its id from its words (`about.slug`), so an entry can be linked; every
  link on the page resolving to a page the build writes (its `#…` to an id on it), but the deck
  list's two AnkiWeb links.
* **Indexing as `/coming/`**: indexed (no `noindex`), its canonical; in both sitemap writers'
  `INDEXED_OTHER` after `/more/`; in the offline copy's shell pages (`build_offline.SHELL_PAGES`).
* **The tabs** (176): About · Coming to Ordpar · Changes · Privacy · Thanks, those labels in that
  order (`chrome.ABOUT_TABS`), a `<nav class="ordpar-tabs">` labelled "About Ordpar" directly under
  the page's `<h1>`, links (no script) in Settings' pill list (`<ul class="ordpar-jump">`), the
  current one `aria-current="page"` — Changes on all three change pages — on exactly the seven
  pages About, Coming, the three change pages, Privacy and Thanks; none on Help, More ways, the
  survey or an article. Privacy's tab only while its page is built (`chrome.PRIVACY`), Thanks' only
  while reports are on (`chrome.REPORT_RECEIVER`, the page's own switch). Never in the README.
  The pressed look in `shell.css`.
* **The footer's "About"** (176): `strings.py` `about_link` "About"; "About and licence" nowhere in
  the site's code or strings.
* **"What's new"** (175): the update note's link to `/changes/` (`offline.js` `showNote`, the words
  `offline.noteWhatsNew`); its behaviour in a stand-in: `test_ordpar_offline94.py`.

`ORDPAR_TEST_ROOT` names another copy of the repository's `ordpar/` parent (`git archive HEAD
ordpar` unpacked) to show the source half failing on the version before the change; the built half
reads `ordpar/out/` (`ORDPAR_TEST_OUT` another). In a browser: `test_ordpar_browser_tabs176.py`.

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

from ordpar.sitegen import about, chrome, page  # noqa: E402
from ordpar.sitegen import strings as strings_mod  # noqa: E402

ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
S = about.SAMPLE
STAMP = "ordpar build: t"

#: path -> (source file, title, the opening's first words)
PAGES = {
    "/changes/": ("changes.md", "Changes to the Ordpar site",
                  "What has changed on ordpar.no, newest first."),
    "/dictionary-changes/": ("library-changes.md", "Changes to the Ordpar dictionary",
                             "What has changed in the dictionary's content, newest first:"),
    "/deck-changes/": ("deck-changes.md", "Changes to the Ordpar Anki decks",
                       "What has changed in Ordpar's Anki decks, newest first."),
}
#: path -> the `about` function giving (title, body), and the `page` one giving the whole page
FUNCS = {"/changes/": "changes_page", "/dictionary-changes/": "library_changes_page",
         "/deck-changes/": "deck_changes_page"}
#: The links the deck list carries outside the site (its AnkiWeb pages; not checked here): the two
#: parts, and the one-deck edition added with the November release (2026-11-08).
EXTERNAL = {"https://ankiweb.net/shared/info/1989661164", "https://ankiweb.net/shared/info/879167685",
            "https://ankiweb.net/shared/info/1906319472"}
TABS = [("/about/", "About"), ("/coming/", "Coming to Ordpar"), ("/changes/", "Changes"),
        ("/privacy/", "Privacy"), ("/thanks/", "Thanks")]
#: the page -> the tab shown pressed
TAB_PAGES = {"/about/": "/about/", "/coming/": "/coming/", "/changes/": "/changes/",
             "/dictionary-changes/": "/changes/", "/deck-changes/": "/changes/",
             "/privacy/": "/privacy/", "/thanks/": "/thanks/"}
INDEXED = ("/", "/about/", "/help/", "/coming/", "/more/", "/changes/", "/dictionary-changes/",
           "/deck-changes/")
_COMMENT = re.compile(r"\A\s*<!--.*?-->\s*", re.S)
_NAV = re.compile(r'<nav class="ordpar-tabs" aria-label="([^"]*)">\n<ul class="ordpar-jump">\n(.*?)\n</ul>\n</nav>',
                  re.S)
_TAB = re.compile(r'<li><a href="([^"]+)"( aria-current="page")?>([^<]*)</a></li>')


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _source(path):
    return _read(ORDPAR, PAGES[path][0])


def _parts(path):
    return getattr(about, FUNCS[path])()


def _whole(path):
    """The page as the build writes it."""
    if path in FUNCS:
        return getattr(page, FUNCS[path])(STAMP, page.EN)
    if path == "/about/":
        return page.about_page(STAMP, page.EN, S)
    if path == "/privacy/":
        return page.privacy_page(STAMP, page.EN)
    if path == "/thanks/":
        return page.thanks_page(STAMP, page.EN, [], lambda _aid: None)
    if path == "/survey/":
        return page.survey_page(STAMP, page.EN)
    return getattr(page, path.strip("/") + "_page")(STAMP, page.EN)


def _tabs(markup):
    """[(href, current, label)] of the page's tab row, its label, and whether it is right under the
    `<h1>`; None without one."""
    m = _NAV.search(markup)
    if not m:
        return None
    under = bool(re.search(r"</h1>\n" + re.escape(m.group(0)), markup))
    return [(h, bool(c), html.unescape(t)) for h, c, t in _TAB.findall(m.group(2))], m.group(1), under


class ThePages(unittest.TestCase):

    def test_title_and_opening(self):
        for path, (src, title, opening) in PAGES.items():
            t, body = _parts(path)
            self.assertEqual(t, title, path)
            self.assertTrue(body.startswith("<p>" + html.escape(opening, quote=False)), (path, body[:200]))
            first = _COMMENT.sub("", _source(path)).split("\n\n")[1]
            self.assertEqual(body.split("\n")[0], "<p>%s</p>" % about._inline(" ".join(first.split("\n"))), path)

    def test_every_word_of_the_file(self):
        for path in PAGES:
            text = _COMMENT.sub("", _source(path), count=1)
            text = re.sub(r"\A# [^\n]*\n", "", text)
            _t, body = _parts(path)
            self.assertEqual(about.plain(body), about.plain(text), path)

    def test_every_item_one_li(self):
        for path in PAGES:
            n = len(re.findall(r"(?m)^- ", _COMMENT.sub("", _source(path), count=1)))
            _t, body = _parts(path)
            self.assertEqual(body.count("<li>"), n, path)
            self.assertNotIn("<p>- ", body, path)
            # a wrapped line is the item's own words, never a paragraph of its own
            self.assertNotIn("<p>  ", body, path)

    def test_the_dated_headings_have_ids(self):
        for path in PAGES:
            src = _COMMENT.sub("", _source(path), count=1)
            words = re.findall(r"(?m)^## (.+)$", src)
            self.assertTrue(words, path)
            _t, body = _parts(path)
            heads = re.findall(r'<h2 id="([^"]+)">([^<]+)</h2>', body)
            self.assertEqual([w for _i, w in heads], [html.escape(w, quote=False) for w in words], path)
            taken = []
            for hid, w in heads:
                self.assertEqual(hid, about.slug(html.unescape(w), taken), path)
                self.assertRegex(hid, r"^\d{4}-\d{2}-\d{2}", path)        # dated
                taken.append(hid)
            self.assertEqual(len(set(taken)), len(taken), path)
        _t, body = about.changes_page()
        self.assertIn('<h2 id="2026-11-07-second-update">2026-11-07, second update</h2>', body)
        _t, body = about.library_changes_page()
        self.assertIn('<h2 id="2026-10-23-the-starting-point">2026-10-23 — the starting point</h2>', body)

    def test_every_link_resolves(self):
        built = {chrome.ABOUT_HREF, chrome.HELP_HREF, chrome.MORE_HREF, chrome.COMING_HREF,
                 chrome.THANKS_HREF, chrome.PRIVACY_HREF, "/changes/", "/dictionary-changes/",
                 "/deck-changes/", "/"}
        seen_external = set()
        for path in PAGES:
            _t, body = _parts(path)
            hrefs = re.findall(r'<a href="([^"]+)"', body)
            self.assertTrue(hrefs, path)
            for h in hrefs:
                if h in EXTERNAL:
                    seen_external.add(h)
                    continue
                self.assertTrue(h.startswith("https://ordpar.no/"), (path, h))
                where, _hash, frag = h[len("https://ordpar.no"):].partition("#")
                self.assertIn(where, built, (path, h))
                if frag:
                    target = _whole(where)
                    self.assertIn('id="%s"' % frag, target, (path, h))
        self.assertEqual(seen_external, EXTERNAL)
        # the openings' links (the brief): the site's and the deck's lists to the dictionary's
        for path in ("/changes/", "/deck-changes/"):
            self.assertIn('<a href="https://ordpar.no/dictionary-changes/">', _parts(path)[1], path)

    def test_no_build_numbers_and_no_comment(self):
        for path in PAGES:
            _t, body = _parts(path)
            self.assertNotIn("<!--", body, path)
            self.assertNotIn("site decisions", body, path)
            self.assertNotRegex(body, r"\{\w+\}", path)

    def test_the_whole_pages(self):
        for path, (_src, title, opening) in PAGES.items():
            t = _whole(path)
            self.assertIn("<title>%s — Ordpar</title>" % html.escape(title, quote=False), t)
            self.assertIn('<link rel="canonical" href="https://ordpar.no%s">' % path, t)
            self.assertNotIn("noindex", t, path)
            self.assertIn('<article class="ordpar-about">\n<h1>%s</h1>\n' % html.escape(title, quote=False), t)


class Indexing(unittest.TestCase):

    def test_both_sitemap_writers(self):
        from ordpar import build_site
        from ordpar.sitegen import wordpages
        self.assertEqual(build_site.INDEXED_OTHER, INDEXED)
        self.assertEqual(wordpages.INDEXED_OTHER, INDEXED)

    def test_the_offline_copy(self):
        from ordpar import build_offline
        for path in PAGES:
            self.assertEqual(build_offline.SHELL_PAGES.get(path), path.strip("/") + "/index.html", path)

    def test_the_build_writes_them(self):
        src = _read(ORDPAR, "build_site.py")
        for path, name in FUNCS.items():
            self.assertIn('write(os.path.join(a.out, "%s", "index.html"), page_mod.%s(stamp, EN))'
                          % (path.strip("/"), name), src)


class Tabs(unittest.TestCase):

    def test_the_seven_pages(self):
        for path, current in TAB_PAGES.items():
            got = _tabs(_whole(path))
            self.assertIsNotNone(got, path)
            tabs, label, under = got
            self.assertEqual(label, "About Ordpar", path)
            self.assertTrue(under, path)                     # directly under the title
            self.assertEqual([(h, t) for h, _c, t in tabs], TABS, path)
            self.assertEqual([h for h, c, _t in tabs if c], [current], path)

    def test_the_first_paragraph_after_them(self):
        for path in PAGES:
            t = _whole(path)
            self.assertRegex(t, r"</h1>\n<nav class=\"ordpar-tabs\"[^>]*>\n<ul class=\"ordpar-jump\">\n"
                                r"(?:<li>.*?</li>\n)+</ul>\n</nav>\n<p>", path)

    def test_none_elsewhere(self):
        for path in ("/help/", "/more/", "/survey/"):
            self.assertIsNone(_tabs(_whole(path)), path)
            self.assertNotIn("ordpar-tabs", _whole(path), path)
        for name in ("settings.html", "search.html", "404.html", "favourites.html", "history.html"):
            self.assertNotIn("ordpar-tabs", _read(SITE, name), name)
        self.assertNotIn("ordpar-tabs", _read(SITE, "shell.js"))

    def test_the_switches(self):
        s = chrome.strings("en")
        on = re.findall(r'href="([^"]+)"', chrome.about_tabs(s, "/about/", privacy=True, thanks=True))
        self.assertEqual(on, [h for h, _t in TABS])
        off = re.findall(r'href="([^"]+)"', chrome.about_tabs(s, "/about/", privacy=False, thanks=False))
        self.assertEqual(off, ["/about/", "/coming/", "/changes/"])
        self.assertEqual(chrome.about_tabs(s, "/help/"), "")
        # by default they follow the pages' own switches
        saved = chrome.PRIVACY, chrome.REPORT_RECEIVER
        try:
            chrome.PRIVACY, chrome.REPORT_RECEIVER = False, ""
            hrefs = [h for h, _c, _t in _tabs(_whole("/changes/"))[0]]
            self.assertEqual(hrefs, ["/about/", "/coming/", "/changes/"])
        finally:
            chrome.PRIVACY, chrome.REPORT_RECEIVER = saved

    def test_the_labels_are_the_strings(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["about.tabs"], "About Ordpar")
        self.assertEqual([s["about.tab." + k] for k in ("about", "coming", "changes", "privacy", "thanks")],
                         [t for _h, t in TABS])

    def test_the_look_is_the_settings_pills(self):
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-jump {\n  display: flex;\n  flex-wrap: wrap;", css)
        rule = re.search(r'\.ordpar-jump a\[aria-current="page"\] \{([^}]*)\}', css)
        self.assertIsNotNone(rule)
        self.assertIn("background: var(--ordpar-accent);", rule.group(1))
        self.assertIn("el('ul', 'ordpar-jump')", _read(SITE, "settings.js"))     # Settings' own row

    def test_never_in_the_readme(self):
        md = about.readme(S)
        self.assertNotIn("ordpar-tabs", md)
        self.assertNotIn("Coming to Ordpar · Changes", md)
        for _h, label in TABS[2:]:
            self.assertNotIn("\n%s\n" % label, md)
        _t, body = about.page(S)
        self.assertNotIn("ordpar-tabs", body)       # the tabs are the page frame's, not about.md's


class Footer(unittest.TestCase):

    def test_about(self):
        self.assertEqual(strings_mod.EN["about_link"], "About")
        f = chrome.footer(chrome.strings("en"))
        self.assertIn('<a href="/about/">About</a>', f)
        self.assertNotIn("About and licence", f)

    def test_the_old_label_nowhere(self):
        for parts in (("sitegen", "chrome.py"), ("sitegen", "strings.py"), ("sitegen", "page.py"),
                      ("site", "shell.js"), ("site", "strings", "en.json")):
            self.assertNotIn("About and licence", _read(ORDPAR, *parts), parts)


class WhatsNew(unittest.TestCase):

    def test_the_words_and_the_link(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual(s["offline.noteWhatsNew"], "What's new")
        js = _read(SITE, "offline.js")
        self.assertIn("tr('offline.noteWhatsNew')", js)
        self.assertIn("setAttribute('href', '/changes/')", js)
        self.assertIn('"offline.noteWhatsNew":"What\'s new"', page.shipped(page.JS_ALL_HREF))


BUILT = os.path.exists(os.path.join(OUT, "build.json"))


@unittest.skipUnless(BUILT, "no built site in %s" % OUT)
class Built(unittest.TestCase):

    def page(self, path):
        return _read(OUT, path.strip("/"), "index.html")

    def test_the_pages(self):
        for path, (_src, title, opening) in PAGES.items():
            t = self.page(path)
            self.assertIn("<title>%s — Ordpar</title>" % html.escape(title, quote=False), t)
            self.assertNotIn('content="noindex"', t, path)
            self.assertIn("<p>" + html.escape(opening, quote=False), t)

    def test_every_link_on_them_is_built(self):
        for path in PAGES:
            t = self.page(path)
            body = t.split('<article class="ordpar-about">', 1)[1].split("</article>", 1)[0]
            for h in re.findall(r'<a href="([^"]+)"', body):
                if h in EXTERNAL:
                    continue
                if h.startswith("https://ordpar.no"):
                    h = h[len("https://ordpar.no"):]
                where, _x, frag = h.partition("#")
                target = os.path.join(OUT, where.strip("/"), "index.html") if where != "/" else \
                    os.path.join(OUT, "index.html")
                self.assertTrue(os.path.isfile(target), (path, h))
                if frag:
                    self.assertIn('id="%s"' % frag, _read(target), (path, h))

    def test_the_sitemap(self):
        locs = re.findall(r"<loc>([^<]+)</loc>", _read(OUT, "sitemap.xml"))
        self.assertEqual(locs[:len(INDEXED)], ["https://ordpar.no" + p for p in INDEXED])

    def test_the_offline_manifest(self):
        m = json.loads(_read(OUT, "offline", "manifest.json"))
        flat = json.dumps(m)
        for path in PAGES:
            self.assertIn('"%s"' % path, flat, path)

    def test_the_tabs(self):
        for path, current in TAB_PAGES.items():
            got = _tabs(self.page(path))
            self.assertIsNotNone(got, path)
            self.assertEqual([h for h, c, _t in got[0] if c], [current], path)
            self.assertTrue(got[2], path)
        for path in ("/help/", "/more/", "/settings/"):
            self.assertNotIn("ordpar-tabs", self.page(path), path)

    def test_the_footer(self):
        for path in ("/about/", "/changes/", "/help/", "/settings/", "/bm-en/"):
            t = self.page(path)
            self.assertNotIn("About and licence", t, path)
            self.assertIn('<a href="/about/">About</a>', t, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
