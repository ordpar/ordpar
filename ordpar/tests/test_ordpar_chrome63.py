# -*- coding: utf-8 -*-
"""Pins site-review decisions 63 (Robin, 2026-10-19): one header and one footer on every page,
the article in a card, the credit in the footer with no per-article source link, the colour
schemes, the settings on a page of their own. What can be pinned outside a browser; the browser
checks are `docs/sessions/2026-09-19-ordpar-site-review/evidence/chrome-63-2026-10-19/`.

* ONE header source and ONE footer source (`ordpar/sitegen/chrome.py`): the article page, the
  About page and every shell page the index build writes carry the same markup, byte for byte;
  the shell HTML files hold only markers, and `shell.js` draws no header of its own.
* The footer, with the credit, on every page type; the credit links ordbokene.no in general —
  `page.credit_source`, its decisions-46 fallbacks and their strings are gone.
* What needs script is not in the markup (since 2026-10-20 `shell.js` makes it; until then it was
  marked `ordpar-needs-js`, hidden until the head script ran).
* The article page: "Article view" + Home + the "N more entries" line, the article in a card
  whose foot (`ordpar-card-foot`) is where the search page's `extractArticle` stops.
* The colour schemes: one table (`colours.py`), the default one value, the head script and the
  shell pages' copy of it, the deck's sheets rewritten through the variables, the icon's and the
  manifest's colour the default's; the cross-references in ordbokene's style; the headword at 600.
* `/settings/`: written by the index build with the colour table, in the offline shell pack.
* The three frame items of 2026-10-20 (decisions 60 and 63): "About and licence" (since site decisions 176, 2026-11-07, "About") once in the
  footer (since 2026-10-22 the links row's last link, Home · Settings · Favourites · History ·
  About, no longer the credit's); the export a `.txt` (`text/plain`, the
  share sheet's second try a `.json`); the "under development" note in every page's footer
  exactly while `head.NOINDEX` is on.

Stdlib unittest; the JS part under bun or node when one is on PATH."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)

from ordpar.sitegen import chrome, colours, head, page  # noqa: E402
from ordpar import build_index as B  # noqa: E402
from ordpar import build_offline as BO  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _runner():
    for exe in ("bun", "node"):
        if shutil.which(exe):
            return exe
    return None


def _article(**kw):
    args = dict(aid=13791, lemmas=[{"form": "fange", "homograph": "III"}],
                article='<div class="ordbok ordpar-article"><h1 class="ordpar-hw">fange</h1></div>',
                translated=True, other_entries=2, strings=page.EN, stamp="ordpar build: t",
                description="d", mk=None, personal={"pos": "VERB"})
    args.update(kw)
    return page.render(**args)


class Chrome(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = chrome.strings()
        cls.header = chrome.header(cls.s)
        cls.footer = chrome.footer(cls.s)
        cls.tmp = tempfile.mkdtemp()
        cls.written = B.copy_shell(cls.tmp)
        cls.shells = {}
        for rel in ("bm-en/index.html", "404.html", "favourites/index.html", "history/index.html",
                    "settings/index.html", "index.html"):
            cls.shells[rel] = _read(cls.tmp, rel)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_one_header_source(self):
        art = _article()
        body = self.header.split("</a>\n", 1)[1]           # past the skip link (its words differ)
        self.assertIn(body, art)
        self.assertIn(body, page.about_page("ordpar build: t", page.EN, page.about_mod.SAMPLE))
        for rel, html in self.shells.items():
            self.assertIn(body, html, rel)
            self.assertEqual(html.count('<header class="ordpar-header">'), 1, rel)
        # the shell sources hold the marker only; shell.js enhances, never draws, the header
        for name in ("search.html", "404.html", "favourites.html", "history.html", "settings.html"):
            src = _read(SITE, name)
            self.assertIn("<!--ORDPAR_HEADER-->", src, name)
            self.assertIn("<!--ORDPAR_FOOTER-->", src, name)
            self.assertNotIn("<header", src, name)
            self.assertNotIn("data-ordpar-random", src, name)   # Random word is the header's
        js = _read(SITE, "shell.js")
        self.assertNotIn("el('form'", js)
        self.assertNotIn("el('a', 'ordpar-brand", js)        # it finds the brand, never draws it
        self.assertNotIn("renderSettingsPanel", js)

    def test_header_works_without_script(self):
        h = self.header
        self.assertIn('<form class="ordpar-search" role="search" action="/bm-en/" method="get">', h)
        self.assertIn('<input id="ordpar-q" type="text"', h)
        self.assertNotIn('name="q"', h)   # decisions 104: no field name, so a search never goes into an address
        self.assertNotIn('role="combobox"', h)               # drawn by shell.js
        # since 2026-10-20 what needs script is not in the markup at all: shell.js makes it
        # (`ordpar/tests/test_ordpar_slim.py` pins `addChrome`)
        for gone in ('data-ordpar-random', 'ordpar-needs-js', 'data-ordpar-string', '/favourites/',
                     '/settings/'):
            self.assertNotIn(gone, h)
        f = self.footer
        # site decisions 104: "Privacy" after About while its switch is on (`chrome.PRIVACY`)
        priv = '<a href="/privacy/">Privacy</a>' if chrome.PRIVACY else ''
        # decisions 123 (Robin, 2026-10-24): "Help" before About; decisions 142 (2026-10-27): "More
        # ways to use Ordpar" after Help
        # a newline between the links (site decisions 154)
        self.assertIn('<nav class="ordpar-footer-nav" aria-label="Site links"><a href="/">Home</a>\n'
                      '<a href="/help/">Help</a>\n<a href="/more/">More ways to use Ordpar</a>\n'
                      '<a href="/about/">About</a>' + ('\n' + priv if priv else '')
                      + '</nav>', f)
        self.assertNotIn('ordpar-needs-js', f)
        js = _read(SITE, "shell.js")
        for made in ("'search.random'", "'nav.favourites'", "'settings.open'", "'footer.settings'",
                     "'footer.favourites'", "'footer.history'"):
            self.assertIn(made, js.split("function addChrome()")[1].split("\n  }\n")[0])
        self.assertIn("html:not(.ordpar-js) .ordpar-needs-js { display: none !important; }",
                      _read(SITE, "shell.css"))
        self.assertTrue(head.THEME_JS.startswith(
            "(function(){var E=document.documentElement,c=E.classList;c.add('ordpar-js');try{"))

    def test_footer_and_credit_on_every_page(self):
        pages = {"article": _article(), "untranslated": _article(translated=False),
                 "about": page.about_page("ordpar build: t", page.EN, page.about_mod.SAMPLE)}
        pages.update(self.shells)
        for name, html in pages.items():
            self.assertEqual(html.count('<footer class="ordpar-footer">'), 1, name)
            self.assertIn(self.footer.rstrip(), html, name)
            self.assertIn('<a href="https://ordbokene.no/" rel="noopener">Bokmålsordboka</a>', html, name)
            self.assertNotIn("ordbokene.no/nob/bm/", html, name)
        self.assertNotIn("<img", self.footer)                 # no logos

    def test_about_and_licence_once_in_the_footer(self):
        # Robin, 2026-10-20: "should only be shown once in the footer"; 2026-10-22: "on the same
        # line as the other page-links" — the links row's last, no longer the credit's
        pages = {"article": _article(), "about": page.about_page("ordpar build: t", page.EN, page.about_mod.SAMPLE)}
        pages.update(self.shells)
        for name, html in pages.items():
            at = html.index('<footer class="ordpar-footer">')
            foot = html[at:html.index("</footer>", at)]
            self.assertEqual(foot.count('href="/about/"'), 1, name)
            self.assertEqual(foot.count('>About</a>'), 1, name)   # "About" since site decisions 176
            self.assertNotIn("About and licence", foot, name)
            nav = foot[foot.index('<nav class="ordpar-footer-nav"'):foot.index("</nav>")]
            credit = foot[foot.index('<p class="ordpar-credit">'):foot.index("</p>")]
            self.assertNotIn('href="/about/"', credit, name)
            self.assertTrue(credit.endswith("Ordpar is independent of both"), name)
            # Home first, then Help (decisions 123), More ways to use Ordpar (decisions 142), About
            # last; the rest are shell.js's (`addChrome`), inserted before Help
            priv = '<a href="/privacy/">Privacy</a>' if chrome.PRIVACY else ''   # decisions 104
            self.assertTrue(nav.endswith('<a href="/">Home</a>\n<a href="/help/">Help</a>\n'
                                         '<a href="/more/">More ways to use Ordpar</a>\n'
                                         '<a href="/about/">About</a>' + ('\n' + priv if priv else '')),
                            name)   # a newline between the links (site decisions 154)
        js = _read(SITE, "shell.js")
        body = js.split("function addChrome() {")[1].split("\n  }\n")[0]
        self.assertIn("var about = links.querySelector('a[href=\"/help/\"]') || "
                      "links.querySelector('a[href=\"/about/\"]');", body)
        self.assertIn("links.insertBefore(a, about);", body)
        self.assertNotIn("links.appendChild(a);", body)

    def test_development_note_follows_the_launch_switch(self):
        note = '<p class="ordpar-devnote">%s</p>' % page.EN["dev_note"]
        self.assertEqual(page.EN["dev_note"], "Under development: Ordpar is still being built, "
                                              "and its pages may change.")   # decisions 132
        self.assertIn(note, chrome.footer(self.s, noindex=True))
        self.assertNotIn("ordpar-devnote", chrome.footer(self.s, noindex=False))
        self.assertTrue(head.NOINDEX)                 # until launch: the note is on every page
        pages = {"article": _article(), "untranslated": _article(translated=False),
                 "about": page.about_page("ordpar build: t", page.EN, page.about_mod.SAMPLE)}
        pages.update(self.shells)                      # 404, /settings/, /favourites/, /history/ …
        for name, html in pages.items():
            self.assertEqual(html.count(note), 1, name)
            at = html.index('<footer class="ordpar-footer">')
            self.assertLess(at, html.index(note), name)
            self.assertLess(html.index(note), html.index("</footer>", at), name)
        # the switch turns the note off; since site decisions 128 (2026-10-25) it no longer
        # touches the robots line, which is each page's own (`head_tags(indexed=…)`)
        old = head.NOINDEX
        try:
            head.NOINDEX = False
            self.assertNotIn("ordpar-devnote", chrome.footer(self.s))
            self.assertIn("noindex", head.head_tags())
            self.assertNotIn("noindex", head.head_tags(indexed=True))
        finally:
            head.NOINDEX = old
        self.assertIn(".ordpar-devnote {", _read(SITE, "shell.css"))

    def test_export_is_a_txt(self):
        # Robin, decisions 60: the export downloads ordpar-<date>.txt as text/plain; the share
        # sheet keeps its order (the .txt, then a .json copy); the import takes both
        js = _read(SITE, "settings.js")
        self.assertIn("var blob = new global.Blob([text], { type: 'text/plain' });", js)
        self.assertNotIn("type: 'application/json' });", js)
        self.assertIn("input.accept = '.json,.txt,application/json,text/plain';", js)
        self.assertIn("pad(date.getDate()) + '.txt';", _read(SITE, "personal.js"))

    def test_no_per_article_source_link(self):
        self.assertFalse(hasattr(page, "credit_source"))
        self.assertFalse(hasattr(page, "ORDBOKENE"))
        for k in ("source_link", "source_link_parent", "source_link_search"):
            self.assertNotIn(k, page.EN)
        self.assertNotIn("Every article page links to the same article", page.about_mod.read_source())
        self.assertEqual(page.credit_line(page.EN), chrome.credit(page.chrome_strings(page.EN)))


class ArticlePage(unittest.TestCase):

    def test_view_line_card_and_controls(self):
        html = _article()
        self.assertIn('<span class="ordpar-section-title ordpar-dict-title">Article view</span>', html)
        self.assertIn('<a href="/"><span aria-hidden="true">← </span>Home</a>', html)
        # site decisions 152: the line in both languages (the labels setting), the Norwegian a draft
        self.assertIn('<span class="ordpar-l-en">2 more entries for fange</span>'
                      '<span class="ordpar-l-nb" lang="nb" data-nosnippet>2 artikler til for fange</span></a></p>', html)
        self.assertIn('<article class="ordpar-card ordpar-entry">', html)
        # the card's foot ships empty since 2026-10-20: the page script makes Copy link, its
        # status and Share (`PAGE_JS` `foot`), personal.js the heart
        self.assertIn('<footer class="ordpar-card-foot"></footer>\n</article>', html)
        for idn in ("'ordpar-copy'", "'ordpar-copied'", "'ordpar-share'"):
            self.assertIn(idn, page.PAGE_JS)
        self.assertLess(html.index("</main>"), html.index('<footer class="ordpar-footer">'))
        self.assertIn('<a class="ordpar-skip" href="#ordpar-main">Skip to the article</a>', html)
        # the header's scripts ride on every article page, in its one script
        self.assertIn('<script src="/site/ordpar.js?v=', html)
        for part in ("/site/lookup.js", "/site/shell.js", "/site/personal.js"):
            self.assertIn(part, page.ARTICLE_JS_PARTS)
        self.assertIn('/site/ordpar.css?v=', html)
        self.assertIn("/site/shell.css", page.ARTICLE_CSS_PARTS)
        # decisions 102 (replacing 43's growth towards the window): the table keeps to its card
        # on the page too, the mount capped in article.css and fitted by inflection.js itself
        self.assertNotIn(".ordpar-entry .ordpar-inflection{max-width:", page.PAGE_CSS)
        self.assertIn(".ordpar-inflection{margin:.2em 0 0;max-width:100%}", page.SITE_CSS)
        self.assertNotIn("fit(", page.PAGE_JS)

    def test_heart_goes_to_the_card_foot(self):
        js = _read(SITE, "personal.js")
        self.assertIn("doc.querySelector('.ordpar-card-foot .ordpar-result-controls')", js)
        self.assertNotIn("a.className = 'ordpar-btn ordpar-fav-link'", js)

    def test_extract_stops_at_the_card_foot(self):
        runner = _runner()
        if not runner:
            self.skipTest("no bun/node on PATH")
        html = _article(translated=False)
        body = ("const S = require(%s).ordparSearch; const got = S.extractArticle(%s);"
                "process.stdout.write(JSON.stringify(got));"
                % (json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(html)))
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "x.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(body)
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            got = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertTrue(got["fragment"].startswith('<div class="ordbok'))
        self.assertTrue(got["fragment"].endswith("</div>"))
        self.assertNotIn("ordpar-copy", got["fragment"])
        self.assertNotIn("ordpar-footer", got["fragment"])
        self.assertIn("ordpar-caption", got["caption"])


class Colours(unittest.TestCase):

    def test_one_table_and_the_default(self):
        ids = [c["id"] for c in colours.COLOURS]
        self.assertEqual(ids, ["wine", "burnt-orange", "ordbokene"])   # 167: Oxblood out
        # Wine is the default (Robin, 2026-10-20); the default's night is today's tint, whichever
        # scheme is the default; `#560027` only under ordbokene's own scheme
        self.assertEqual(colours.DEFAULT, "wine")
        self.assertEqual(colours.effective(colours.default())["night"], "#e3b7c9")
        o = colours.by_id("ordbokene")
        self.assertEqual((o["day"], o["night"], o["night_line"]), ("#560027", "#ffffff", "#880e4f"))
        self.assertEqual(o["name"], "ordbokene.no's maroon")
        self.assertIn("Ordpar is independent of ordbokene.no", o["note"])
        self.assertEqual(colours.by_id("wine")["day"], "#6b0f2e")
        self.assertEqual(colours.by_id("burnt-orange")["day"], "#b13a0b")
        self.assertNotIn("oxblood", ids)                            # 167: removed (Robin)
        for c in ("wine", "burnt-orange"):                       # our own: the hue at today's tint
            self.assertEqual(colours.by_id(c)["night"], colours.tint(colours.by_id(c)["day"]))
        css = colours.css()
        self.assertIn(":root{--ordpar-maroon:#6b0f2e;--ordpar-maroon-rgb:107,15,46;"
                      "--ordpar-tint:#e3b7c9;--ordpar-tint-rgb:227,183,201}", css)
        for c in ids:
            self.assertIn('html[data-accent="%s"]{' % c, css)
        self.assertIn('html[data-accent="burnt-orange"]{--ordpar-maroon:#b13a0b;--ordpar-maroon-rgb:177,58,11;'
                      '--ordpar-tint:%s;' % colours.tint("#b13a0b"), css)
        self.assertIn("--ordpar-night-line:initial", css)    # our own schemes: no ordbokene line
        self.assertEqual(css.count("#560027"), 1)              # ordbokene's scheme only
        saved = colours.DEFAULT
        try:
            colours.DEFAULT = "burnt-orange"
            self.assertIn(":root{--ordpar-maroon:#b13a0b;--ordpar-maroon-rgb:177,58,11;"
                          "--ordpar-tint:#e3b7c9;", colours.css())
            self.assertIn('html[data-accent="wine"]{--ordpar-maroon:#6b0f2e;--ordpar-maroon-rgb:107,15,46;'
                          '--ordpar-tint:%s;' % colours.tint("#6b0f2e"), colours.css())
            colours.DEFAULT = "ordbokene"
            self.assertNotIn("--ordpar-night-line:#880e4f", colours.css())
        finally:
            colours.DEFAULT = saved
        js = json.loads(colours.settings_json())
        self.assertEqual([e["id"] for e in js if e.get("default")], ["wine"])

    def test_the_default_drives_head_manifest_icon(self):
        self.assertEqual(head.THEME_COLOR, colours.default()["day"])
        self.assertIn('<meta name="theme-color" content="%s">' % colours.default()["day"],
                      head.head_tags())
        man = json.loads(_read(ORDPAR, "root", "manifest.webmanifest"))
        self.assertEqual(man["theme_color"], colours.default()["day"])
        self.assertIn('MAROON = tuple(int(colours.default()["day"]', _read(ORDPAR, "build_icons.py"))
        from ordpar import build_site
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "m.webmanifest")
            shutil.copy(os.path.join(ORDPAR, "root", "manifest.webmanifest"), p)
            before = open(p, "rb").read()
            build_site.write_manifest_colours(p)
            self.assertEqual(open(p, "rb").read(), before)     # the default unchanged: the same file
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_head_script_and_its_one_copy(self):
        self.assertIn("var a=s.getItem('colour');if(a&&/^[a-z][a-z0-9-]*$/.test(a))"
                      "E.setAttribute('data-accent',a);", head.THEME_JS)
        self.assertIs(page.THEME_JS, head.THEME_JS)
        # one copy, a file since 2026-10-20: /site/theme.js, the same script
        self.assertEqual(page.source(head.THEME_JS_HREF), head.THEME_JS + "\n")
        self.assertIn('<script src="/site/theme.js?v=', _article())
        tmp = tempfile.mkdtemp()
        try:
            B.copy_shell(tmp)
            for rel in ("bm-en/index.html", "404.html", "favourites/index.html",
                        "history/index.html", "settings/index.html"):
                html = _read(tmp, rel)
                self.assertIn('<script src="/site/theme.js', html, rel)
                self.assertNotIn(head.THEME_JS, html, rel)
                self.assertNotIn("try{var t=localStorage", html, rel)
                # the colour schemes: article.css, inside the shell pages' one sheet
                self.assertIn('href="/site/shell-pages.css', html, rel)
                self.assertEqual(page.SHELL_CSS_PARTS[0], page.CSS_HREF)
            self.assertIn("window.ORDPAR_COLOURS=%s;" % colours.settings_json(),
                          _read(tmp, "settings/index.html"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_every_maroon_through_the_variables(self):
        css = page.article_css().replace(colours.css(), "")   # the schemes define the values
        self.assertEqual(page.article_css().count("#560027"), 1)   # only ordbokene's own scheme
        bare = re.sub(r"var\(--ordpar-[a-z-]+,[^)]*\)", "", css)
        for c in ("#560027", "#e3b7c9", "rgba(86,0,39,", "rgba(227,183,201,", "#7a5566"):
            self.assertNotIn(c, bare, c)
        for name in ("shell.css", "inflection.css"):
            src = re.sub(r"var\(--ordpar-[a-z-]+, *[^)]*\)", "", _read(SITE, name))
            self.assertNotIn("#560027", src, name)
            self.assertNotIn("#e3b7c9", src, name)
        self.assertNotIn("#560027", re.sub(r"var\(--ordpar-[a-z-]+,[^)]*\)", "", page.PAGE_CSS))

    def test_xref_style_and_headword_weight(self):
        css = page.article_css()
        self.assertIn(".ordbok-xword{color:inherit;font-style:normal;border-bottom:0;"
                      "text-decoration:underline;", css)
        self.assertIn(".ordbok .ordbok-xword em{font-style:normal}", css)
        self.assertIn("var(--ordpar-night-line,var(--ordpar-tint,#e3b7c9))", css)
        # later in the sheet than the deck's rules, so it wins at the same specificity
        self.assertGreater(css.index(".ordbok-lemma{font-weight:600}"), css.index(".ordbok-lemma{font-size"))
        self.assertGreater(css.index(".ordbok-xword{color:inherit"), css.index(".ordbok-xword{cursor"))


class SettingsPage(unittest.TestCase):

    def test_page_and_pack(self):
        self.assertEqual(BO.SHELL_PAGES["/settings/"], "settings/index.html")
        src = _read(SITE, "settings.html")
        self.assertIn('<meta name="robots" content="noindex">', src)
        self.assertIn("<!--ORDPAR_COLOURS-->", src)
        self.assertIn('<script src="/site/settings.js"></script>', src)
        js = _read(SITE, "settings.js")
        self.assertIn("var SECTIONS = ['style', 'article', 'search', 'data'];", js)
        self.assertIn("global.history.back()", js)
        self.assertNotIn("role', 'dialog'", js + _read(SITE, "shell.js"))
        # export / import moved here; the favourites page keeps a link
        self.assertIn("function transfer()", js)
        pp = _read(SITE, "personal-page.js")
        self.assertNotIn("function transfer()", pp)
        self.assertIn("base() + 'settings/#data'", pp)
        # the share sheet (Robin's phone, 2026-10-19: a JSON file did nothing): the .txt first,
        # a refusal other than the reader's cancel tries the next, then downloads, naming the error
        self.assertIn(r"[[name, 'text/plain'], [name.replace(/\.txt$/, '.json'), 'application/json']]", js)
        self.assertIn("if (err && err.name === 'AbortError') { return; }", js)
        self.assertIn("say(t('transfer.shareFailed', { error: errorText(err), name: name }));", js)

    def test_the_subsections(self):
        # decisions 85 (Robin, 2026-10-21): an h3 per `sub`, one level under the section's h2;
        # each fieldset's accessible name leads with its subsection heading
        js = _read(SITE, "settings.js")
        self.assertIn("var h3 = el('h3', null, t('settings.sub.' + sub));", js)
        # since decisions 99 the name is the title's own span, not the legend, which also holds
        # the "?" (test_ordpar_hints99.py pins the rest)
        self.assertIn("group.setAttribute('aria-labelledby', (subId ? subId + ' ' : '') + title.id);", js)
        self.assertIn("box.appendChild(field(sp, sub ? id + '-' + sub + '-title' : null));", js)
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-settings-sub > h3 {", css)
        self.assertIn(".ordpar-settings-sub > h3 + .ordpar-field { border-top: 0; padding-top: 0; }", css)
        strings = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual([strings["settings.sub." + k] for k in ("language", "inflection", "xref", "mini")],
                         ["Language", "Inflection", "Cross-references", "Small articles"])
        self.assertEqual(strings["settings.mini"], "Language")   # the brief's example

    def test_every_setting_has_a_section_and_words(self):
        js = _read(SITE, "shell.js")
        strings = json.loads(_read(SITE, "strings", "en.json"))
        specs = re.findall(r"\{ key: '(\w+)', values: (\[[^\]]*\]|null|LANGS), def: [^,]+, "
                           r"section: '(\w+)'(?:, sub: '(\w+)')?(?:, control: '\w+')?(?:, gate: '\w+')?"
                           r"(?:, layer: true)? \}", js)
        # decisions 85 (2026-10-21): Article in four subsections, `minihw` moved there from Style
        self.assertEqual([(k, s, sub) for k, _v, s, sub in specs],
                         [("theme", "style", ""), ("colour", "style", ""), ("lang", "style", ""),
                          ("layout", "style", ""),                         # decisions 87
                          ("nbonly", "article", "nbonly"), ("nbequiv", "article", "nbonly"),   # 152
                          ("nbrows", "article", "nbonly"), ("nbhover", "article", "nbonly"),
                          ("nbicon", "article", "nbonly"),
                          ("defs", "article", "language"),
                          ("examples", "article", "language"),            # decisions 111
                          ("exeye", "article", "language"),               # decisions 131
                          ("exlimit", "article", "language"), ("exmore", "article", "language"),  # 112
                          ("emph", "article", "language"), ("subsenses", "article", "language"),  # 87, 90
                          ("formulas", "article", "language"),
                          ("ety", "article", "language"),
                          ("labels", "article", "language"),   # site decisions 152 (Style until 2026-11-03)
                          ("infl", "article", "inflection"), ("pframes", "article", "inflection"),
                          ("xref", "article", "xref"), ("peek", "article", "xref"),
                          ("mini", "article", "mini"), ("minicontent", "article", "mini"),
                          ("nestminis", "article", "mini"),   # 139; nestlimit went in 147
                          ("minispacing", "article", "mini"), ("minitext", "article", "mini"),   # 114
                          ("miniscroll", "article", "mini"),
                          ("minihw", "article", "mini"),
                          ("audiospeed", "article", "audio"),   # site decisions 159
                          ("listview", "search", ""),
                          ("suggestrows", "search", ""),    # decisions 86 (2026-10-22)
                          # decisions 92 (2026-10-22): moved from Small articles to Loading
                          ("minifetch", "data", "loading"),
                          # decisions 104 (2026-10-24): the opt-out, drawn only with the counting
                          # live (166, 2026-11-05), after the offline copy and the transfer (no subsection)
                          ("stats", "data", "")])
        for key, values, section, sub in specs:
            self.assertIn(section, ("style", "article", "search", "data"))
            self.assertEqual(bool(sub), section in ("article", "data") and key != "stats")
            if sub:
                self.assertIn("settings.sub." + sub, strings)
            self.assertIn("settings.%s" % key, strings)
            if values.startswith("["):
                for v in re.findall(r"'(\w+)'", values):
                    if v.isdigit():          # a number is its own label (decisions 112, settings.js)
                        continue
                    self.assertIn("settings.%s.%s" % (key, v), strings)
        for sec in ("style", "article", "search", "data"):
            self.assertIn("settings.section." + sec, strings)
        self.assertIn("'colour'", _read(SITE, "personal.js").split("SETTING_KEYS = ")[1].split(";")[0])


if __name__ == "__main__":
    unittest.main()
