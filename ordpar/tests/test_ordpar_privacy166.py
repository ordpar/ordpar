# -*- coding: utf-8 -*-
"""Site decisions 166's go-live, step 2 (2026-11-05): the privacy page publishable with the counting
off. Brief: `docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-privacy-page-166-2026-11-05.md`.
Stdlib unittest, pure Python (one subprocess of `build_site.py` that stops at its guard).

What it pins:

* **Two switches where there was one.** `chrome.PRIVACY` decides the page (written, its footer and
  About links); the COUNTING is `chrome.counting()`, read from `events.js`'s `var RECEIVER` (the
  line that decides whether anything is sent), and it alone draws "Send usage statistics": the
  settings page built with the page ON and the counting OFF carries no `window.ORDPAR_COUNTING`
  (nor the old `ORDPAR_PRIVACY`), so the setting is not drawn. As committed since 2026-11-05 (166's
  go-live, Robin: "Approve all four"): the page on, reports on (the live receiver), the counting off;
  until then all three were off.
* **The page's text follows the switches** (`privacy.md` `[if counting]`, `[if reports]`,
  `[if receiver]` and their `no_`, `about.privacy_text`), in all four cases: it renders without
  `draft` (no `[[`), no `[if` or `[/if]` left; with the counting off no passage on the counting (its
  setting, the daily code, robots, page views, searches kept, the right to object …); with reports
  off nothing on reports (nor Anthropic); no section left empty; every `(see "…" above/below)`
  names a section that is there, on the side it says; the companies named in the opening (GitHub,
  Cloudflare; Anthropic only with reports; Google no longer, since site decisions 173). Blocks may nest; an unknown name or an
  unbalanced block is refused.
* **The form's line** linking `/privacy/#reporting-a-mistake`: the anchor is the page's own id for
  "Reporting a mistake" (`report.js` `PRIVACY_HREF` = `chrome.PRIVACY_REPORTS_HREF`), present on
  the page with reports on; its words in `en.json` and `report.js`'s fallback the same; made before
  Send, opened in a new tab.
* **The build's guard** (`build_site.privacy_for_build`): reports on from the committed switch with
  the page off is refused, saying why (also through `build_site.py` itself); a look build
  (`ORDPAR_REPORT_RECEIVER`) gets the page for that build alone, with a line saying so. The two
  build runs set `PRIVACY` off in their own process (the committed switch is on since 2026-11-05),
  `chrome.py` untouched.
  (`deploy.py prepare`'s refusal of reports on with no `/privacy/`: `test_ordpar_deploy166.py`.)

Shown to fail on the code before it (a `git archive` export of a613861de with this file copied in).

**Lookups kept on the device** (site decisions 170, 2026-11-06, `test_lookups_kept_on_device_in_every_build`):
the approved paragraph after the opening, the two sentences in "What GitHub sees" and "Audio"'s new
first sentence, each once and in its place, in all four switch cases; failing on the page of the
deployed build 9b50a8b8d9c3375d (`privacy.md` at dfb57c1a4).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
ORDPAR = os.path.join(ROOT, "ordpar")

from ordpar.sitegen import about, chrome, page  # noqa: E402

CASES = [(c, r) for c in (True, False) for r in (True, False)]
LIVE = "https://ordpar-receiver.ordpar.workers.dev/report"
LOOK = "http://192.168.0.100:8787/report"
#: Words that only the counting's passages use (lower case)
COUNTING_WORDS = ("send usage statistics", "scrambled code", "daily code", "day's secret",
                  "daily secret", "how we count readers", "counting people, not robots",
                  "page views", "a page view", "suggestion chosen", "searches and suggestions",
                  "installs are kept", "global privacy control", "do not track", "your right to object",
                  "offline and the installed app", "count of readers", "after the day they arrived",
                  "40 characters", "data centres and hosting companies", "article 11",
                  "counting the readers")
#: Words that only the reports' passages use (lower case)
REPORT_WORDS = ("reporting a mistake", "report of a mistake", "report you send",
                "suggest a correction", "anthropic", "claude", "name to credit",
                "thanks to our readers", "thanks page", "30 reports")


def _read(*parts):
    with io.open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _plain(body):
    return " ".join(re.sub(r"<[^>]+>", " ", body).split()).lower()


def _sections(body):
    """[(id, words, the HTML up to the next heading)] after the index."""
    parts = re.split(r'(<h2 id="[^"]+">.*?</h2>)', body)
    out = []
    for i in range(1, len(parts), 2):
        m = re.match(r'<h2 id="([^"]+)">(.*?)</h2>', parts[i])
        out.append((m.group(1), m.group(2), parts[i + 1]))
    return out


class PageCases(unittest.TestCase):
    """The page in each case: counting on/off x reports on/off."""

    def render(self, c, r):
        # survey=False: these cases are counting x reports, as HEAD's text; the survey's own
        # clauses ("a report or survey answers you send") and all 8 switch cases are
        # test_ordpar_survey173's. Until 2026-11-07 this followed chrome.SURVEY and failed
        # once the switch went on (site decisions 173).
        return about.privacy_page(counting=c, reports=r, survey=False)   # no draft: refused on a [[

    def test_renders_whole_in_every_case(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                title, body = self.render(c, r)
                self.assertEqual(title, "Privacy")
                for left in ("[[", "]]", "[if", "[/if]", "<!--"):
                    self.assertNotIn(left, body)
                secs = _sections(body)
                self.assertGreaterEqual(len(secs), 6)
                for hid, words, html in secs:                     # no section left empty
                    self.assertRegex(html, r"<(p|ul)>\s*\S", "%s is empty" % hid)
                self.assertNotIn("<p></p>", body)
                self.assertNotIn("<p> ", body)
                self.assertNotRegex(body, r" [,.;:]")             # no hole left by a dropped clause
                self.assertNotIn("  ", body)

    def test_no_counting_passage_with_the_counting_off(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                t = _plain(self.render(c, r)[1])
                for w in COUNTING_WORDS:
                    self.assertEqual(w in t, c, w)

    def test_no_report_passage_with_reports_off(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                t = _plain(self.render(c, r)[1])
                for w in REPORT_WORDS:
                    self.assertEqual(w in t, r, w)
                self.assertEqual(bool(re.search(r"\breport\b", t)), r)

    def test_the_receiver_only_while_used(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                t = _plain(self.render(c, r)[1])
                self.assertEqual("receiver" in t, c or r)
                self.assertEqual("https://ordpar-receiver.ordpar.workers.dev" in t, c or r)
                self.assertEqual("where it is kept, and for how long" in t, c or r)

    def test_the_companies_named_in_the_opening(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                body = self.render(c, r)[1]
                lead = _plain(body[:body.index('<nav class="ordpar-toc"')])
                self.assertIn("which companies handle it", lead)
                for name in ("github", "cloudflare"):
                    self.assertIn(name, lead)
                # site decisions 173 (2026-11-07): Google's form replaced by our own survey, so Google
                # is no longer named (amended; it pinned "google" in the opening until then)
                self.assertNotIn("google", lead)
                self.assertEqual("anthropic" in lead, r)
                self.assertEqual("our receiver and our audio server" in lead, c or r)

    def test_every_see_names_a_section_that_is_there(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                body = self.render(c, r)[1]
                order = [w for _h, w, _x in _sections(body)]
                pos = {w: body.index('">%s</h2>' % w) for w in order}
                refs = re.findall(r'\(see (?:&quot;|")([^"&]+)(?:&quot;|") (above|below)\)', body)
                for words, side in refs:
                    heads = [w for w in order if w.startswith(words)]
                    self.assertTrue(heads, "see %r: no such section" % words)
                    for m in re.finditer(re.escape(words) + r'(?:&quot;|") ' + side, body):
                        self.assertEqual(m.start() < pos[heads[0]], side == "below", words)
                for m in re.finditer(r"\(see (above|below)\)", body):
                    self.assertTrue(c or r, m.group(0))      # "our receiver (see below)" is the counting's

    def test_the_section_the_form_links(self):
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                body = self.render(c, r)[1]
                self.assertEqual('<h2 id="reporting-a-mistake">' in body, r)
        self.assertEqual(chrome.PRIVACY_REPORTS_HREF,
                         "/privacy/#" + about.slug("Reporting a mistake"))

    def test_the_counting_off_words(self):
        # the passages written for the counting off (site decisions 166, Robin's to approve)
        t = " ".join(about.privacy_text(counting=False, reports=True).split())
        self.assertIn("Ordpar does not count its readers or record what they look up.", t)
        self.assertIn("in a database created in Cloudflare's EU jurisdiction", t)
        self.assertIn("The reports are kept in Cloudflare's database service, in the EU", t)
        self.assertIn("## Who is responsible\n", about.privacy_text(counting=False, reports=True))
        self.assertIn("or object to our use of it.", t)
        self.assertNotIn("or object to our use of it",
                         " ".join(about.privacy_text(counting=False, reports=False).split()))

    def test_what_cloudflare_keeps_in_every_build(self):
        # site decisions 169 (a), Robin's approval 2026-11-06: the full statement of what Cloudflare
        # itself keeps lives in "Audio", which every build shows, so it stays with the receiver off;
        # the receiver's section points to it, and says it only once
        full = ('Cloudflare itself keeps log data about the traffic on its network, which can include IP '
                'addresses, in its data centres in the US and Europe "for a limited period of time"; it does '
                'not say how long.')
        records = ('Cloudflare also keeps records of requests to our audio server, which we can see in our '
                   'Cloudflare account for 32 days: each with the IP address, its country, the time, and which '
                   'recording was asked for, and so which word. We do not copy or keep them.')
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                t = " ".join(about.privacy_text(counting=c, reports=r).split())
                audio = t[t.index("## Audio"):]
                audio = audio[:audio.index("##", 3)] if "##" in audio[3:] else audio
                self.assertIn(full, audio)
                self.assertIn(records, audio)
                self.assertEqual(t.count(full), 1)
                self.assertEqual('as described under "Audio" below.' in t, c or r)

    def test_lookups_kept_on_device_in_every_build(self):
        # site decisions 170, Robin's approval 2026-11-06 ("Approve all four"): the way to look words
        # up unseen, near the top (after the opening, before "What stays on your device"); the
        # offline copy and fetching ahead in "What GitHub sees", after "…roughly what was looked
        # up." and before the JavaScript and version-check sentences; "Audio"'s first sentence
        top = ('**To look words up without anyone seeing which:** download the offline copy, in Settings '
               'under "Loading, offline and your data". Your searches and the articles you open are then '
               'answered from your device, so neither GitHub nor anyone else sees which words you look up; '
               'only a recording you play, and the list of recordings it is found in, is still fetched (see "Audio"). Setting "When a linked article or '
               'page is loaded" to "When its link is clicked" also stops the site fetching anything before '
               'you open it.')
        github = ('If you keep the offline copy, your searches and the articles you open are answered from '
                  'your device instead, so GitHub does not see them; a recording you play is still fetched '
                  'from our audio server, and the list of recordings it is found in from GitHub (see "Audio" below). By default the site also fetches an article, '
                  'page or search when your pointer rests on its link, on a suggestion under the search box '
                  'or on Random word, before you open it, and a recording when it rests '   # 180, 2026-11-09
                  'on a sound icon; under Settings, "When a linked article or page is loaded" set to "When its '
                  'link is clicked" fetches nothing before you click. '
                  # 185, 2026-11-12: the Norwegian hover's fetch (the session's call at Robin's delegation)
                  "If you have chosen to see a linked word's first Norwegian definition when the pointer "
                  'rests on it, the site fetches the part of the index that holds it as soon as your pointer '
                  'reaches the link, unless you have chosen "When its link is clicked".')
        audio = ('When you press a sound icon, or rest the pointer on one (unless you have chosen to load '
                 'nothing before you click, see "What GitHub sees" above), your browser fetches the recording '
                 "from Ordpar's audio server, a small program on Cloudflare's network.")
        for c, r in CASES:
            with self.subTest(counting=c, reports=r):
                raw = about.privacy_text(counting=c, reports=r)
                paras = [" ".join(p.split()) for p in raw.split("\n\n") if p.strip()]
                t = " ".join(raw.split())
                for words in (github, audio):
                    self.assertEqual(t.count(words), 1, words[:40])
                # the top paragraph only while the counting is off (170's second part, 2026-11-06):
                # with it live, searches go to the receiver, so "nor anyone else" would be untrue;
                # with it off its own paragraph, the second after the title, before the first section
                self.assertTrue(paras[0].startswith("# Privacy"), paras[0])
                self.assertNotIn("without anyone seeing which", t if c else "")
                if c:
                    self.assertEqual(paras[2], "## What stays on your device", paras[:4])
                else:
                    self.assertEqual(t.count(top), 1, top[:40])
                    at = paras.index(top)
                    self.assertEqual(at, 2, paras[:4])
                    self.assertEqual(paras[at + 1], "## What stays on your device")
                gh = t[t.index("## What GitHub sees"):]
                gh = gh[:gh.index("##", 3)]
                # site decisions 170, Robin "Approve all" 2026-11-06: the "#" sentence gone, what GitHub can tell said plainly
                self.assertNotIn("after \"#\", which your browser never sends", t)
                self.assertIn("So unless you keep the offline copy, GitHub can tell which words and articles you look up. " + github
                              + " With JavaScript turned off", gh)
                self.assertIn(" If you keep the offline copy, your browser asks GitHub whether there is a "
                              "newer version", gh)
                au = t[t.index("## Audio"):]
                self.assertTrue(au.startswith("## Audio " + audio), au[:200])
                # bold in the page's Markdown subset
                html = about.privacy_page(counting=c, reports=r)[1]
                self.assertEqual("<strong>To look words up without anyone seeing which:</strong>" in html, not c)

    def test_by_default_the_switches(self):
        # as committed since 2026-11-05 (166's go-live): the page on, reports on (the live
        # receiver), the counting off (events.js RECEIVER empty); before that all three were off
        self.assertIs(chrome.counting(), False)
        self.assertEqual(chrome.REPORT_RECEIVER, LIVE)
        self.assertIs(chrome.PRIVACY, True)
        self.assertEqual(about.privacy_page(), about.privacy_page(counting=False, reports=True))
        # the page still follows each switch, by default
        with mock.patch.object(chrome, "REPORT_RECEIVER", ""):
            self.assertEqual(about.privacy_page(), about.privacy_page(counting=False, reports=False))
        with mock.patch.object(chrome, "counting", lambda path=None: True):
            self.assertEqual(about.privacy_page(), about.privacy_page(counting=True, reports=True))


class Conditions(unittest.TestCase):

    def test_nested_and_opposites(self):
        src = "# P\n\nA[if counting] B[if reports] C[/if][/if][if no_counting] D[/if].\n"
        got = {(c, r): about.privacy_text(src, counting=c, reports=r).split("\n\n")[1].strip()
               for c, r in CASES}
        self.assertEqual(got, {(True, True): "A B C.", (True, False): "A B.",
                               (False, True): "A D.", (False, False): "A D."})
        src = "# P\n\n[if receiver]R[/if][if no_receiver]N[/if]\n"
        self.assertIn("R", about.privacy_text(src, counting=False, reports=True))
        self.assertIn("N", about.privacy_text(src, counting=False, reports=False))

    def test_refused(self):
        with self.assertRaises(KeyError):
            about.privacy_text("# P\n\n[if privacy]x[/if]\n", counting=True, reports=True)
        with self.assertRaises(ValueError):
            about.privacy_text("# P\n\n[if counting]x\n", counting=True, reports=True)
        with self.assertRaises(ValueError):
            about.privacy_text("# P\n\nx[/if]\n", counting=True, reports=True)


class Counting(unittest.TestCase):
    """`chrome.counting()`: events.js's RECEIVER line decides."""

    def test_read_from_events_js(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "events.js")
            for line, on in (("  var RECEIVER = '';", False),
                             ("  var RECEIVER = 'https://ordpar-receiver.ordpar.workers.dev/e';", True)):
                with io.open(p, "w", encoding="utf-8") as f:
                    f.write("(function () {\n%s\n  var api = { RECEIVER: RECEIVER };\n})();\n" % line)
                self.assertIs(chrome.counting(p), on)
            with io.open(p, "w", encoding="utf-8") as f:
                f.write("(function () {})();\n")
            with self.assertRaises(ValueError):
                chrome.counting(p)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIn("\n  var RECEIVER = '';\n", _read(ORDPAR, "site", "events.js"))

    def test_settings_with_the_page_on_and_the_counting_off(self):
        # the brief's case: Settings must show no statistics setting. Until 2026-11-05 PRIVACY on
        # wrote window.ORDPAR_PRIVACY, which drew it.
        from ordpar import build_index as B
        tmp = tempfile.mkdtemp()
        try:
            with mock.patch.object(chrome, "PRIVACY", True), \
                    mock.patch.object(chrome, "counting", lambda path=None: False):
                B.copy_shell(tmp)
            built = _read(tmp, "settings", "index.html")
            self.assertNotIn("ORDPAR_PRIVACY", built)
            self.assertNotIn("ORDPAR_COUNTING", built)
            self.assertIn('<a href="/privacy/">Privacy</a>', built)     # the page's link is there
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIn("gate: 'counting' }", _read(ORDPAR, "site", "shell.js"))
        self.assertNotIn("gate: 'privacy'", _read(ORDPAR, "site", "shell.js"))
        self.assertIn("<!--ORDPAR_COUNTING-->", _read(ORDPAR, "site", "settings.html"))


class FormLine(unittest.TestCase):

    def setUp(self):
        self.js = _read(ORDPAR, "site", "report.js")

    def test_the_link(self):
        m = re.search(r"var PRIVACY_HREF = '([^']+)';", self.js)
        self.assertTrue(m)
        self.assertEqual(m.group(1), chrome.PRIVACY_REPORTS_HREF)
        anchor = m.group(1).split("#")[1]
        _t, body = about.privacy_page(counting=False, reports=True)
        self.assertEqual(body.count('id="%s"' % anchor), 1)
        built = page.privacy_page("ordpar build: t", page.EN, counting=False, reports=True)
        self.assertIn('<h2 id="%s">Reporting a mistake</h2>' % anchor, built)
        self.assertIn("pl.href = PRIVACY_HREF;", self.js)
        self.assertIn("pl.target = '_blank';", self.js)
        self.assertIn("pl.rel = 'noopener';", self.js)

    def test_the_words(self):
        strings = json.loads(_read(ORDPAR, "site", "strings", "en.json"))
        for key in ("report.privacy", "report.privacyLink"):
            m = re.search(r"'%s': '([^']*)'," % re.escape(key), self.js)
            self.assertTrue(m, key)
            self.assertEqual(m.group(1), strings[key], key)
        self.assertEqual(strings["report.privacy"].count("{link}"), 1)

    def test_before_send(self):
        i = self.js.index("form.appendChild(pv);")
        self.assertLess(self.js.index("form.appendChild(lc); form.appendChild(credit); form.appendChild(ch);"), i)
        self.assertLess(i, self.js.index("form.appendChild(status);"))
        self.assertLess(i, self.js.index("form.appendChild(actions);"))


class BuildGuard(unittest.TestCase):

    def test_privacy_for_build(self):
        from ordpar import build_site as BS
        self.assertEqual(BS.privacy_for_build(True, "", False), (True, None))
        self.assertEqual(BS.privacy_for_build(True, LIVE, False), (True, None))
        self.assertEqual(BS.privacy_for_build(False, "", False), (False, None))
        self.assertEqual(BS.privacy_for_build(False, "", True), (False, None))
        with self.assertRaises(ValueError) as e:
            BS.privacy_for_build(False, LIVE, False)
        self.assertIn("while the privacy page is off", str(e.exception))
        self.assertIn("/privacy/#reporting-a-mistake", str(e.exception))
        write, note = BS.privacy_for_build(False, LOOK, True)
        self.assertTrue(write)
        self.assertIn("written for this build alone", note)

    def _run(self, receiver, env_receiver=None, privacy=False):
        # the switches set in the build's own process: since 2026-11-05 the committed PRIVACY is
        # on, and these cases are the page OFF (chrome.py itself untouched)
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "run.py")
            with io.open(script, "w", encoding="utf-8") as f:
                f.write("import sys\nsys.path.insert(0, %r)\n"
                        "from ordpar.sitegen import chrome\nchrome.REPORT_RECEIVER = %r\n"
                        "chrome.PRIVACY = %r\n"
                        "from ordpar import build_site\n"
                        "sys.argv = ['build_site.py', '--mirror', %r, '--articles', %r, '--ids', '1000', "
                        "'--out', %r]\nbuild_site.main()\n"
                        % (ROOT, receiver, privacy, os.path.join(tmp, "no-mirror.jsonl"),
                           os.path.join(tmp, "no-articles.jsonl"), os.path.join(tmp, "out")))
            env = dict(os.environ, PYTHONUTF8="1")
            env.pop("ORDPAR_REPORT_RECEIVER", None)
            if env_receiver:
                env["ORDPAR_REPORT_RECEIVER"] = env_receiver
            return subprocess.run([sys.executable, script], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=env, timeout=600,
                                  stdin=subprocess.DEVNULL)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_build_refuses_reports_without_the_page(self):
        r = self._run(LIVE)
        self.assertEqual(r.returncode, 2, r.stdout[-500:] + r.stderr[-500:])
        self.assertIn("while the privacy page is off", r.stderr)

    def test_a_look_build_gets_the_page(self):
        r = self._run("", LOOK)
        self.assertIn("written for this build alone", r.stdout)
        self.assertNotIn("while the privacy page is off", r.stderr)


if __name__ == "__main__":
    unittest.main()
