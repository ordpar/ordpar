# -*- coding: utf-8 -*-
"""Site decisions 104's box, item 5 (2026-10-23): the privacy page, `/privacy/`, its own page linked
from every footer and from About — built from `ordpar/privacy.md` (`sitegen/about.py`
`privacy_page`, the About page's Markdown subset) behind one switch, `sitegen/chrome.py` `PRIVACY`,
off until Robin has approved the words. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-receiver-26-62-104-2026-10-23.md` § 3.
Stdlib unittest, pure Python.

What it pins:

* **The draft renders** (title, the brief's sections) and is **refused while a `[[…]]`
  placeholder is left** — the build cannot publish an unfilled legal sentence; filled, it renders.
  Since site decisions 166 (2026-11-05) the page's text follows the switches (`[if counting]`,
  `[if reports]`, `about.privacy_text`): the classes here read it with BOTH ON (`ALL_ON`), the page
  the decisions-104 review saw; the other cases are `test_ordpar_privacy166.py`'s. No placeholder is
  left since the receiver's address was filled (2026-11-05), so the refusal is shown on a copy
  with one put back.
* **Its numbers are the code's**: 40 characters (the receiver's and the page script's
  `MAX_QUERY`), two seconds (`VISIBLE_MS`), one day for page views (`VIEW_DAYS`, 104 as revised
  2026-11-08, from 7) and 30 for searches (`RETAIN_DAYS`, from 90), three times (`KEEP_MIN`), 100 pages within 10
  minutes (`PACE_MAX`, `PACE_MINUTES`), five minutes after the day (`GRACE`), 15 minutes between
  the offline copy's update checks (`offline.js` `EVERY`); and the Settings buttons it names are
  the strings the settings page shows.
* **The redraft of 2026-10-23** (the independent review, decisions 104): no placeholder is left
  (Robin's name and contact filled 2026-10-23, the receiver's address 2026-11-05), no `[[CHECK` or
  `[[LEGAL`; the
  sentences that rest on a code change stand on it — the search in the fragment (`lookup.js`
  `searchUrl`), the mistyped address sent as /other (`events.js` `cleanPath`), the searches in
  small letters (`rules.js`), in a random order (`searches` WITHOUT ROWID), nothing kept under
  Global Privacy Control (`worker.js` `optedOut`); the page claims no exemption from consent; and
  the Settings and personal pages' lines say the stored items are not sent, not "nothing sent".
* **The switch** (off as shipped): off — no footer link, no About section, no README line; on — the
  link after About in every footer, the About section and the README line (absolute link); the
  build writes `/privacy/` only while it is on, and the offline copy takes it only where it was
  written; the relabel tables carry the link's key.
* **The index of sections** (decisions 104, Robin 2026-10-23, built 2026-10-24): every `## `
  heading has an id from its words, stable; an index under the page's lead lists each once, in
  order, every link resolving; its label the interface's `privacy.contents`; the About page (also
  the README) has none.
* **The opt-out it names** (built 2026-10-24): the right to object names "Send usage statistics",
  the setting's label in `en.json` — the test fails if either changes alone; the built settings
  page carries `window.ORDPAR_COUNTING` (and so draws the setting) only while the COUNTING is live
  (`chrome.counting()`, `events.js` `RECEIVER`) — no longer the privacy page's switch (site
  decisions 166, 2026-11-05; that split's own tests: `test_ordpar_privacy166.py`).
* **The Settings names it uses** (site decisions 170, 2026-11-06): "Loading, offline and your data"
  (the section holding the offline copy), "When a linked article or page is loaded" and "When its
  link is clicked" are the settings page's strings.
"""
import json
import os
import re
import sys
import tempfile
import shutil
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
ORDPAR = os.path.join(ROOT, "ordpar")

from ordpar.sitegen import about, chrome, page  # noqa: E402
from ordpar import build_offline as BO  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _js_const(path, name):
    m = re.search(r"(?:export const|var) %s = (\d+);" % name, _read(path))
    if not m:
        raise AssertionError("%s not found in %s" % (name, path))
    return int(m.group(1))


RULES = os.path.join(ORDPAR, "receiver", "src", "rules.js")
SECRET = os.path.join(ORDPAR, "receiver", "src", "secret.js")
EVENTS = os.path.join(ORDPAR, "site", "events.js")
WORDS = {1: "one", 2: "two", 3: "three", 5: "five", 10: "10"}
#: The page as the decisions-104 review saw it: the counting and reports both on (site decisions 166)
ALL_ON = dict(counting=True, reports=True)


class Draft(unittest.TestCase):

    def setUp(self):
        self.raw = _read(ORDPAR, "privacy.md")
        self.text = about.privacy_text(**ALL_ON)
        self.title, self.body = about.privacy_page(draft=True, **ALL_ON)

    def test_renders_with_the_briefs_sections(self):
        self.assertEqual(self.title, "Privacy")
        for h in ("What stays on your device", "What your browser sends us", "How we count readers",
                  "Counting people, not robots", "Where it is kept, and for how long",
                  "What GitHub sees", "Offline and the installed app",
                  "Who is responsible, and the legal basis", "Your right to object",
                  "Your other rights", "Questions"):
            self.assertIn('<h2 id="%s">%s</h2>' % (about.slug(h), h), self.body)
        self.assertIn("<ul>", self.body)
        self.assertNotIn("<!--", self.body)

    def test_refused_while_a_placeholder_is_left(self):
        # site decisions 166 (2026-11-05): the receiver's address filled, so the page renders; a
        # placeholder put back is refused, by the page builder too
        address = "https://ordpar-receiver.ordpar.workers.dev"
        self.assertIn("at %s." % address, self.text)
        title, body = about.privacy_page(**ALL_ON)
        self.assertEqual(title, "Privacy")
        self.assertNotIn("[[", body)
        unfilled = self.raw.replace(address, "[[ADDRESS: the receiver's address]]")
        with self.assertRaises(ValueError):
            about.privacy_page(source=unfilled, **ALL_ON)
        with mock.patch.object(about, "read_source", lambda path=None: unfilled):
            with self.assertRaises(ValueError):
                page.privacy_page("ordpar build: t", page.EN, **ALL_ON)

    def test_its_numbers_are_the_codes(self):
        t = " ".join(self.text.split())
        self.assertEqual(_js_const(RULES, "MAX_QUERY"), _js_const(EVENTS, "MAX_QUERY"))
        self.assertIn("longer than %d characters" % _js_const(RULES, "MAX_QUERY"), t)
        self.assertIn("on screen for %s seconds" % WORDS[_js_const(EVENTS, "VISIBLE_MS") // 1000], t)
        self.assertEqual(_js_const(RULES, "VIEW_DAYS"), 1)
        n = _js_const(RULES, "VIEW_DAYS")
        self.assertIn("**Page views** are kept as they arrived (the page's address, the day and minute, "
                      "the day's code) for %s %s after the day they arrived"
                      % (WORDS[n], "day" if n == 1 else "days"), t)
        self.assertIn("**Searches and suggestions chosen** are kept as they arrived", t)
        self.assertIn("for %d days after the day they arrived. After that, a search is kept only"
                      % _js_const(RULES, "RETAIN_DAYS"), t)
        self.assertIn("after %d days, the count kept" % _js_const(RULES, "RETAIN_DAYS"), t)
        n = _js_const(RULES, "RETAIN_DAYS")
        rest = t.replace("for %d days after" % n, "").replace("after %d days, the" % n, "")
        rest = rest.replace("keeps the conversation for 30 days", "")    # Anthropic's, not ours
        self.assertNotIn("%d days" % n, rest)
        m = re.search(r"var EVERY = (\d+) \* 60 \* 1000;", _read(ORDPAR, "site", "offline.js"))
        self.assertIn("at most once every %s minutes" % m.group(1), t)
        self.assertIn("at least %s times" % WORDS[_js_const(RULES, "KEEP_MIN")], t)
        self.assertIn("viewed %d pages or more within %d minutes"
                      % (_js_const(RULES, "PACE_MAX"), _js_const(RULES, "PACE_MINUTES")), t)
        self.assertIn("deleted %s minutes after its day ends" % WORDS[_js_const(SECRET, "GRACE") // 60], t)

    def test_only_robins_placeholders_left(self):
        # Robin's name and contact filled in (2026-10-23: "Robin Fauskanger", post@ordpar.no); the
        # receiver's address comes with its deploy
        body = re.sub(r"<!--.*?-->", "", self.raw, count=1, flags=re.S)
        names = re.findall(r"\[\[([A-Z]+):", body)
        self.assertEqual(sorted(names), [])                     # ADDRESS filled 2026-11-05 (166)
        self.assertNotIn("[[", body)
        self.assertIn("Robin Fauskanger is responsible for this data", body)
        self.assertIn("write to post@ordpar.no", body)

    def test_the_claims_that_rest_on_the_code(self):
        t = " ".join(self.text.split())
        lookup = _read(ORDPAR, "site", "lookup.js")
        rules = _read(ORDPAR, "receiver", "src", "rules.js")
        worker = _read(ORDPAR, "receiver", "src", "worker.js")
        sql = _read(ORDPAR, "receiver", "migrations", "0001_init.sql")
        # the search in the fragment (R2): the page no longer says it "never" reaches a server, since the
        # word's own page and the shown articles do (site decisions 170, Robin 2026-11-06, "Approve all")
        self.assertIn("GitHub can tell which words and articles you look up", t)
        self.assertIn("function searchUrl(q) { return config.base + 'bm-en/#q=' + encodeURIComponent(q); }", lookup)
        # a mistyped address sent as /other (R12)
        self.assertIn("an address the site does not have is sent as /other", t)
        self.assertIn("return { type: 'view', path: cleanPath(f.path) };", _read(EVENTS))
        # in small letters (R11), in a random order (R4)
        self.assertIn("its words in small letters", t)
        self.assertEqual(rules.count("return s.toLowerCase();"), 2)
        self.assertIn("no time of day and in a random order", t)
        self.assertIn(") WITHOUT ROWID;", sql)
        # Global Privacy Control refused on the receiver too (R12)
        self.assertIn("the receiver keeps nothing from a browser that sends Global Privacy Control", t)
        self.assertIn("&& !optedOut(request)", worker)
        self.assertIn("request.headers.get('Sec-GPC') === '1'", worker)

    def test_it_claims_no_exemption(self):
        t = " ".join(self.body.split()).lower()                 # the page as rendered: no comment
        # site decisions 166's follow-up (2026-11-05): the name to credit's legal basis is consent,
        # GDPR 6(1)(a) (the brief: "consent, GDPR 6(1)(a)") — the one use of the word, in
        # "Reporting a mistake", about the name and nothing else; it says nothing about the counting
        name = "for a name to credit, your consent, which you give by writing it in the field"
        self.assertEqual(t.count("consent"), 1)
        self.assertIn(name, t)
        t = t.replace(name, "")
        for word in ("consent", "exempt", "strictly necessary", "3-15", "not needed", "not required"):
            self.assertFalse(word in t, word)

    def test_the_sites_own_lines_about_sending(self):
        strings = json.loads(_read(ORDPAR, "site", "strings", "en.json"))
        # R5: true once the receiver is live — the stored items are never sent; page views and
        # searches are, so "nothing sent anywhere" would not be
        for key, says in (("settings.stored", "none of it is sent anywhere"),
                          ("personal.device", "are not sent anywhere")):
            self.assertNotIn("nothing sent", strings[key].lower(), key)
            self.assertNotIn("nothing is sent", strings[key].lower(), key)
            self.assertIn(says, strings[key], key)

    def test_the_settings_buttons_it_names(self):
        strings = json.loads(_read(ORDPAR, "site", "strings", "en.json"))
        for key in ("settings.delete", "offline.remove"):
            self.assertIn('"%s"' % strings[key], self.text, key)
        # site decisions 170: the section, the setting and its choice the page names are the
        # settings page's own words (the section's heading holds the offline copy: settings.js);
        # the top paragraph that names the section is the counting-off page's only (170's second
        # part, 2026-11-06: `[if no_counting]`), so it is read there
        t = " ".join(self.text.split())
        off = " ".join(about.privacy_text(counting=False, reports=True).split())
        for key in ("settings.minifetch", "settings.minifetch.click"):
            self.assertIn('"%s"' % strings[key], t, key)
        self.assertIn('in Settings under "%s"' % strings["settings.section.data"], off)
        self.assertIn('"%s" set to "%s"' % (strings["settings.minifetch"], strings["settings.minifetch.click"]), t)
        self.assertIn('Setting "%s" to "%s"' % (strings["settings.minifetch"], strings["settings.minifetch.click"]), off)
        self.assertIn("var SECTIONS = ['style', 'article', 'search', 'data'];", _read(ORDPAR, "site", "settings.js"))
        self.assertIn("// decisions 61: the offline copy (offline.js draws and redraws its own section)",
                      _read(ORDPAR, "site", "settings.js"))

    def test_the_opt_outs_label_as_ruled(self):
        # Robin's words (decisions 104): "Send usage statistics", On (the default, first) / Off
        strings = json.loads(_read(ORDPAR, "site", "strings", "en.json"))
        self.assertEqual((strings["settings.stats"], strings["settings.stats.on"], strings["settings.stats.off"]),
                         ("Send usage statistics", "On", "Off"))

    def test_the_opt_out_it_names_is_the_settings_label(self):
        # decisions 104 (built 2026-10-24): the right to object names the setting by its label, so
        # the page and the setting change together or this fails
        strings = json.loads(_read(ORDPAR, "site", "strings", "en.json"))
        label = strings["settings.stats"]
        t = " ".join(self.text.split())
        self.assertIn('turn off "%s" in Settings' % label, t)
        self.assertIn('"%s" turns it back on' % strings["settings.delete"], t)
        # the setting the label names: on | off, On first, the events' key
        js = _read(ORDPAR, "site", "shell.js")
        self.assertIn("{ key: 'stats', values: ['on', 'off'], def: 'on', section: 'data', gate: 'counting' }", js)
        self.assertIn("var STATS_KEY = 'stats';", _read(EVENTS))
        self.assertIn("return global.localStorage.getItem(STATS_KEY) === 'off';", _read(EVENTS))

    def test_the_page_in_the_sites_frame(self):
        html = page.privacy_page("ordpar build: t", page.EN, draft=True, **ALL_ON)
        self.assertIn('<link rel="canonical" href="https://ordpar.no/privacy/">', html)
        self.assertIn("<h1>Privacy</h1>", html)
        self.assertEqual(html.count('<footer class="ordpar-footer">'), 1)


class Index(unittest.TestCase):
    """The page's index of its sections (decisions 104, Robin 2026-10-23: "an index on the top,
    where you can click on each header to bring you that section")."""

    def setUp(self):
        self.text = about.privacy_text(**ALL_ON)                 # the [if]s resolved (166)
        self.title, self.body = about.privacy_page(draft=True, **ALL_ON)

    def test_every_heading_has_an_id_and_the_index_lists_each_once_in_order(self):
        heads = re.findall(r"(?m)^## (.+)$", self.text)
        self.assertGreater(len(heads), 5)
        ids = re.findall(r'<h2 id="([^"]+)">', self.body)
        self.assertEqual(len(ids), len(heads))
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(re.findall(r"<h2[ >]", self.body)), len(ids), "a heading without an id")
        nav = re.search(r'<nav class="ordpar-toc" aria-labelledby="ordpar-toc-title">(.*?)</nav>', self.body, re.S)
        self.assertTrue(nav, self.body[:400])
        links = re.findall(r'<li><a href="#([^"]+)">([^<]+)</a></li>', nav.group(1))
        self.assertEqual([h for h, _w in links], ids)                    # each once, in order
        self.assertEqual([w for _h, w in links], [h.strip() for h in heads])
        for hid in ids:                                                  # every link resolves
            self.assertEqual(self.body.count('id="%s"' % hid), 1, hid)
        self.assertIn('<p class="ordpar-toc-title" id="ordpar-toc-title">On this page</p>', nav.group(0))
        self.assertEqual(json.loads(_read(ORDPAR, "site", "strings", "en.json"))["privacy.contents"], "On this page")

    def test_under_the_lead_before_the_first_section(self):
        nav = self.body.index('<nav class="ordpar-toc"')
        self.assertLess(nav, self.body.index("<h2 "))
        self.assertTrue(self.body.startswith("<p>"), "the page's lead first")
        self.assertNotIn("<h2", self.body[:nav])

    def test_stable_ids(self):
        self.assertEqual(about.slug("Your right to object"), "your-right-to-object")
        self.assertEqual(about.slug("Who is responsible, and the legal basis"),
                         "who-is-responsible-and-the-legal-basis")
        self.assertEqual(about.slug("Hva så?"), "hva-sa")
        self.assertEqual(about.slug("Questions", ["questions"]), "questions-2")

    def test_the_about_page_has_none(self):
        art = page.about_page("ordpar build: t", page.EN, about.SAMPLE)
        self.assertNotIn("ordpar-toc", art)
        # no index; its headings have their ids since site decisions 131 (2026-10-26: `#contact`,
        # which the deck's AnkiWeb page links), as the Help page's
        self.assertIn('<h2 id="contact">Contact</h2>', art)
        self.assertNotIn("ordpar-toc", about.readme(about.SAMPLE))

    def test_in_the_built_page(self):
        html = page.privacy_page("ordpar build: t", page.EN, draft=True, **ALL_ON)
        self.assertIn('<nav class="ordpar-toc"', html)
        self.assertIn('<a href="#your-right-to-object">Your right to object</a>', html)
        self.assertIn('<h2 id="your-right-to-object">Your right to object</h2>', html)
        self.assertIn(".ordpar-toc{", page.PAGE_CSS)


class Switch(unittest.TestCase):

    def test_off(self):
        s = chrome.strings()
        with mock.patch.object(chrome, "PRIVACY", False):
            self.assertNotIn("/privacy/", chrome.footer(s))
            self.assertNotIn("privacy", page.about_page("ordpar build: t", page.EN, about.SAMPLE).lower()
                             .split("<article")[1].split("</article>")[0])
            self.assertNotIn("privacy", about.readme(about.SAMPLE).lower())

    def test_on(self):
        s = chrome.strings()
        self.assertIn('<a href="/about/">About</a>\n<a href="/privacy/">Privacy</a></nav>',   # "About": 176
                      chrome.footer(s, privacy=True))   # a newline between the links (154)
        with mock.patch.object(chrome, "PRIVACY", True):
            self.assertIn('<a href="/privacy/">Privacy</a></nav>', chrome.footer(s))
            art = page.about_page("ordpar build: t", page.EN, about.SAMPLE)
            self.assertIn('<h2 id="privacy">Privacy</h2>', art)     # its id since decisions 131
            self.assertIn('<a href="https://ordpar.no/privacy/">Privacy</a>', art)
            self.assertIn("(https://ordpar.no/privacy/)", about.readme(about.SAMPLE))

    def test_the_build_writes_it_only_while_on(self):
        src = _read(ORDPAR, "build_site.py")
        # site decisions 166: `privacy_build` is the switch, or a look build with reports on
        # (`build_site.privacy_for_build`, pinned in test_ordpar_privacy166.py)
        self.assertIn("if privacy_build:\n        write(privacy_out, page_mod.privacy_page(stamp, EN))", src)
        self.assertIn("elif os.path.exists(privacy_out):\n        os.remove(privacy_out)", src)

    def test_the_offline_copy_takes_it_only_where_written(self):
        tmp = tempfile.mkdtemp()
        try:
            for rel in BO.SHELL_PAGES.values():
                p = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(p) or tmp, exist_ok=True)
                open(p, "w").close()
            self.assertNotIn("/privacy/", BO.other_files(tmp))
            os.makedirs(os.path.join(tmp, "privacy"))
            open(os.path.join(tmp, "privacy", "index.html"), "w").close()
            self.assertIn("/privacy/", BO.other_files(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_settings_page_draws_the_opt_out_only_while_on(self):
        # decisions 104 (Robin, 2026-10-24: not deployed before the receiver): the built settings
        # page tells settings.js the counting's state (`window.ORDPAR_COUNTING`), and carries no
        # trace of it while it is off; settings.js draws the setting only with it. Since site
        # decisions 166 (2026-11-05) the COUNTING decides (`chrome.counting()`), not `PRIVACY`
        from ordpar import build_index as B
        for on in (False, True):
            tmp = tempfile.mkdtemp()
            try:
                with mock.patch.object(chrome, "counting", lambda path=None, on=on: on):
                    B.copy_shell(tmp)
                built = _read(tmp, "settings", "index.html")
                self.assertNotIn("<!--ORDPAR_COUNTING-->", built)
                self.assertEqual("window.ORDPAR_COUNTING=true" in built, on)
                self.assertEqual("ORDPAR_COUNTING" in built, on)
                self.assertNotIn("ORDPAR_PRIVACY", built)
                for other in ("bm-en/index.html", "404.html", "favourites/index.html"):
                    self.assertNotIn("ORDPAR_COUNTING", _read(tmp, other), other)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        js = _read(ORDPAR, "site", "settings.js")
        self.assertIn("if (sp.gate === 'counting') { return global.ORDPAR_COUNTING === true; }", js)
        self.assertIn("if (sp.section !== id || !drawn(sp)) { return; }", js)

    def test_the_relabel_tables(self):
        self.assertIn(('.ordpar-footer-nav a[href="/privacy/"]', "footer.privacy"), chrome.RELABEL)
        self.assertIn("['.ordpar-footer-nav a[href=\"/privacy/\"]', 'footer.privacy']",
                      _read(ORDPAR, "site", "shell.js"))
        self.assertEqual(json.loads(_read(ORDPAR, "site", "strings", "en.json"))["footer.privacy"], "Privacy")
        self.assertIn('html.ordpar-js:not(.ordpar-chrome) .ordpar-footer-nav a[href="/privacy/"] { order: 2; }',
                      _read(ORDPAR, "site", "shell.css"))


if __name__ == "__main__":
    unittest.main()
