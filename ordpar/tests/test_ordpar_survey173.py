# -*- coding: utf-8 -*-
"""Site decisions 173 (Robin, 2026-11-07): the readers' survey, "Ordpar — your first impressions",
as Ordpar's own page in place of the Google form, kept after launch. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-survey-173-2026-11-07.md`. The receiver's
own tests are `ordpar/receiver/test/survey.test.js` (`test_ordpar_receiver104.py` runs them); the
page in a browser, `test_ordpar_browser_survey173.py`.

* **The data file** (`ordpar/site/survey.json`, `sitegen/survey.py` `read`/`check`): the approved
  words exactly — the title, the two intro paragraphs (the second as changed, its "Privacy" linking
  `/privacy/#the-survey`, the section's own id), every question, hint and choice in Robin's order,
  the new free-form question last before the follow-up; "What is your first language?" skipped for
  "Norwegian is my first language"; every question optional; a data file the page or the receiver
  could not take is refused.
* **The page** (`page.survey_page`): the intro and one form, each question with its label, hint and
  `maxlength`; radio buttons for one choice, check boxes for several; the trap, the status, Send;
  `noindex`; its own script after the page's; nothing of Google.
* **The switch** (`chrome.SURVEY`, `chrome.survey_receiver()`): the reports' receiver with
  `/survey`, on only with reports on; written into `survey.js` and, as `/survey/`, into `shell.js`
  for the footer's "Tell us what you think →" (same tab, after the note or in a line of its own
  after launch); `build_site.write_survey` writes or removes `/survey/`; `ORDPAR_SURVEY` for one
  build. Google's form gone from every script.
* **What is sent** (`survey.js` under bun): exactly `answers` and `follow` (and the trap only when
  filled); one `fetch`, in the submit handler; no cookies, no referrer, no storage.
* **The privacy page**: the opening's companies (no Google; Anthropic for "a report or survey
  answers"; the list reads right with each switch off), "Questions" without Google, and "The survey"
  after "Reporting a mistake", word for word, only with the survey on; each of its claims held to
  the code.
* **Robin's page** (`scripts/reports_page.py`, `/reports` through `scripts/serve.py`), against the
  receiver's stand-in: the open answers under their questions in the survey's order, Done deleting
  the follow-up address or name and keeping the answers, Copy never carrying it, a receiver without
  `/surveys` said plainly.

Skipped in part without bun. Shown failing on the code before it (a `git archive` of HEAD 6208c6f09
with this file copied in) and passing after.
"""
import io
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
SITE = os.path.join(ORDPAR, "site")
RECEIVER = os.path.join(ORDPAR, "receiver")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ORDPAR)          # build_site
from ordpar.sitegen import about, chrome, page  # noqa: E402

#: the reports' reading page is the private repository's (scripts/reports_page.py; decisions 184:
#: not in the public export), so what reads through it skips where it is not
HAVE_READER = importlib.util.find_spec("reports_page") is not None

BUN = shutil.which("bun")
TOKEN = "unit-test-token-0123456789abcdef"
NATIVE = "Norwegian is my first language"


def _read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def _survey():
    from ordpar.sitegen import survey
    return survey


class SurveyOn(object):
    """The survey's switch on (and reports on) for one test; restored after."""

    def setUp(self):
        self._old = (chrome.SURVEY, chrome.REPORT_RECEIVER)
        page.set_report_receiver("https://ordpar-receiver.ordpar.workers.dev/report")
        page.set_survey(True)

    def tearDown(self):
        page.set_survey(self._old[0])
        page.set_report_receiver(self._old[1])


# --- the approved words (site decisions 173, Robin's form pasted 2026-11-07; the brief's text) ------

TITLE = "Ordpar — your first impressions"
# Robin, 2026-11-07, at his look at the build: "Include a note on the top of the survey that each
# field is optional" — the privacy page's own words for it ("The survey": "Every question is optional.")
NOTE = "Every question is optional."
INTRO = [
    "Ordpar is a Norwegian–English dictionary in development, built on Bokmålsordboka. Thank you for "
    "trying it! These questions take five to ten minutes. Answer as much or as little as you like — "
    "specific examples help most (\"I searched for X and …\").",
    "Your answers are stored by Ordpar (see Privacy) and read by Robin (the creator of Ordpar), who also "
    "uses an AI assistant (Claude, made by Anthropic) to help go through them. Leave the last question "
    "blank if you'd rather stay anonymous.",
]
QUESTIONS = [
    ("How well do you know Norwegian?", None,
     ["Just starting", "I can read simple texts", "I get by in daily life", "Fluent", NATIVE]),
    ("What is your first language?", None, None),
    ("What did you look up, and did you find what you were looking for?",
     "A few words you searched for, and whether the result helped.", None),
    ("Was anything confusing, wrong or broken?",
     "Which word or page? A wrong translation, a strange suggestion, a button that did nothing — anything.", None),
    ("What did you miss, or wish it could do?",
     "A feature, a setting, the look or the layout, a word or a meaning that was missing, how it works on "
     "your phone — anything.", None),
    ("Some ideas we have. Which would you use?",
     "Anki, mentioned below, is a free flashcard app that uses spaced repetition: it shows each word again "
     "just before you're likely to forget it.",
     ["Make Anki flashcards from words you've saved — one by one or all at once, kept up to date as the "
      "dictionary improves",
      "A short description of how a word's meanings fit together, for words with many meanings (on the "
      "flashcards, and optional on the site)",
      "Common pitfalls for English speakers: false friends, tricky grammar, words that don't translate the "
      "way you'd expect (on the flashcards, and optional on the site)",
      "Example sentences for the words and meanings that don't have any yet",
      "Ask a question about a word, answered later (not straight away) by other readers, or by an AI with "
      "the answer checked before it is shown",
      "Use Ordpar as the dictionary on your e-reader (Kindle, Kobo) when reading Norwegian books",
      "Synthetic voice audio for the English translations, similar to the Norwegian audio that is already "
      "in the dictionary"]),
    ("Any comments on these ideas, or an idea of your own?", "Say which idea you mean.", None),
    ("Would you like a dictionary like this one between Norwegian and a language other than English? If "
     "so, which?", "Your own first language, or any other.", None),
    ("What did you use it on?", None, ["Phone", "Tablet", "Computer"]),
    ("Which browser, if you know it?", "Chrome, Safari, Firefox …", None),
    ("Would you use it again? For what?", None, None),
    ("Anything else you'd like to tell us?", "About Ordpar, this survey, or anything else.", None),
    ("If it's all right to ask you a follow-up question, leave an email address or name.",
     "Only Robin will see this. It's removed before the answers are shared with the AI assistant, and it's "
     "never passed on to anyone else.", None),
]
#: The privacy page's new section, approved ("Approve all", 2026-11-07), as the brief gives it
SECTION = [
    "## The survey",
    "The page \"Ordpar — your first impressions\", linked at the foot of every page, asks what you think of "
    "Ordpar. Every question is optional. If you fill it in, your browser sends our receiver one message when "
    "you press Send, and only then: your answers, and an email address or name if you gave one so that we "
    "can ask you a follow-up question. Nothing else goes with it: no cookie, no identifier, and not the "
    "address of the page you were on. As for a report, the receiver does not use or store your IP address "
    "or your browser's name, though Cloudflare keeps records of requests to it (see \"Audio\" above), and "
    "the limit of 30 an hour counts reports and answers together. The answers are kept in Cloudflare's "
    "database service, in the EU, as reports are (see \"Where it is kept\" above).",   # Robin, 2026-11-07
    "Robin reads the answers, to improve Ordpar, and may go through them with the help of an AI assistant, "
    "as for reports (see \"Reporting a mistake\"); your email address or name is never shared with it. We "
    "use them only to ask you a follow-up question, and delete them once we have, or once we have decided "
    "not to; like any deletion in that database, they can still be restored by us for 7 days after that. "
    "The rest of your answers is kept with no end date, as our record of what readers have asked for. "
    "Please do not write anything you would not want us to keep.",
    "The legal basis is our legitimate interest in improving the dictionary (GDPR Article 6(1)(f)); for "
    "your email address or name, your choice to give it so that we can ask you a follow-up question (GDPR "
    "Article 6(1)(a)). You can ask us to see, correct or delete your answers, or to delete your email "
    "address or name before we use it, by writing to post@ordpar.no; tell us roughly when you sent them "
    "and what they said.",
]
ANTHROPIC = "Anthropic, whose AI assistant may help us read a report or survey answers you send."
GOOGLE_GONE = ("Google, which holds our feedback form",
               "the feedback form linked at the foot of every page is a Google form")


class Data(unittest.TestCase):
    """ordpar/site/survey.json: the approved words, read and checked."""

    def test_the_approved_words(self):
        d = _survey().read()
        self.assertEqual(d["title"], TITLE)
        self.assertEqual(d.get("note"), NOTE)
        self.assertEqual(len(d["intro"]), 2)
        self.assertEqual(d["intro"][0], INTRO[0])
        self.assertEqual(d["intro"][1].replace("[Privacy](/privacy/#the-survey)", "Privacy"), INTRO[1])
        self.assertIn("(see [Privacy](%s))" % chrome.PRIVACY_SURVEY_HREF, d["intro"][1])
        got = [(q["label"], q.get("hint"), q.get("choices")) for q in d["questions"]]
        self.assertEqual(got, QUESTIONS)

    def test_kinds_skip_and_follow(self):
        qs = _survey().read()["questions"]
        kinds = {q["id"]: q["kind"] for q in qs}
        self.assertEqual(kinds["level"], "one")
        self.assertEqual(kinds["first_language"], "short")
        self.assertEqual((kinds["ideas"], kinds["devices"]), ("many", "many"))
        self.assertEqual(qs[-1]["kind"], "follow")
        self.assertEqual(qs[-2]["id"], "anything_else")                      # NEW, last before the follow-up
        self.assertEqual([q["id"] for q in qs if q.get("skip_if")], ["first_language"])
        self.assertEqual(qs[1]["skip_if"], {"level": NATIVE})
        for q in qs:
            self.assertNotIn("required", q)                                  # every question optional

    def test_the_section_id(self):
        self.assertEqual(chrome.PRIVACY_SURVEY_HREF, "/privacy/#" + about.slug("The survey"))
        self.assertEqual(chrome.PRIVACY_SURVEY_HREF, "/privacy/#the-survey")

    def test_check_refuses(self):
        s = _survey()
        good = s.read()

        def broken(f):
            d = json.loads(json.dumps(good))
            f(d)
            return d
        cases = [
            lambda d: d["questions"][0].update(id="Level"),
            lambda d: d["questions"][2].update(id="level"),
            lambda d: d["questions"][0].update(kind="dropdown"),
            lambda d: d["questions"][2].update(max=2001),
            lambda d: d["questions"][-1].update(max=200),
            lambda d: d["questions"][0]["choices"].append("x" * 301),
            lambda d: d["questions"][1].update(skip_if={"level": "Fluently"}),
            lambda d: d["questions"][1].update(skip_if={"looked_up": "x"}),
            lambda d: d["questions"].append(dict(d["questions"][2], id="late")),
            lambda d: d["words"].pop("sent"),
        ]
        for i, f in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ValueError):
                    s.check(broken(f))


class Page(SurveyOn, unittest.TestCase):
    """/survey/ as the build writes it."""

    def test_the_page(self):
        html = page.survey_page("STAMP", page.EN)
        self.assertIn("<h1>%s</h1>" % TITLE, html)
        # the note: the first thing under the title, in bold, before the intro
        note = '<p class="ordpar-survey-note"><strong>%s</strong></p>' % NOTE
        self.assertRegex(html, r"<h1>%s</h1>\s*%s" % (re.escape(TITLE), re.escape(note)))
        self.assertLess(html.index(note), html.index("Ordpar is a Norwegian–English dictionary"))
        self.assertIn('<a href="/privacy/#the-survey">Privacy</a>', html)
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertRegex(html, r'<script src="/site/survey\.js(\?v=[0-9a-f]+)?" defer></script>')
        self.assertLess(html.index("/site/ordpar.js"), html.index("/site/survey.js"))
        for words in ("Part 1 of 3", "Part 2", "forms.gle", "google"):
            self.assertNotIn(words, html)
        self.assertEqual(html.count('<form class="ordpar-survey"'), 1)
        self.assertEqual(len(re.findall(r'data-q="', html)), len(QUESTIONS))
        self.assertEqual(len(re.findall(r'type="radio"', html)), 5)
        self.assertEqual(len(re.findall(r'type="checkbox"', html)), 7 + 3)
        self.assertIn('data-q="first_language" data-kind="short" data-skip-q="level" '
                      'data-skip-v="%s"' % NATIVE, html)
        self.assertIn('id="ordpar-survey-hp" name="website" tabindex="-1"', html)
        self.assertIn('class="ordpar-report-trap" aria-hidden="true"', html)
        self.assertRegex(html, r'<p class="[^"]*ordpar-survey-status" role="status">')
        self.assertIn(">Send</button>", html)
        self.assertNotIn(" required", html)
        for m in re.finditer(r'<(textarea|input) class="ordpar-report-(?:text|reply)"[^>]*maxlength="(\d+)"', html):
            self.assertLessEqual(int(m.group(2)), 2000)
        self.assertIn('id="ordpar-survey-follow" name="follow" maxlength="254" autocomplete="email"', html)
        island = re.search(r'<script type="application/json" id="ordpar-survey-words">(.*?)</script>', html, re.S)
        self.assertEqual(json.loads(island.group(1))["sent"], "Thank you, your answers have been sent.")
        # every label and hint on the page, escaped as HTML
        import html as _h
        for label, hint, choices in QUESTIONS:
            self.assertIn(_h.escape(label, quote=False), html)
            if hint:
                self.assertIn(_h.escape(hint, quote=False), html)
            for c in choices or ():
                self.assertIn('value="%s"' % _h.escape(c, quote=True), html)

    def test_written_and_removed_by_the_build(self):
        import build_site
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(build_site.write_survey(out, "STAMP"), "written")
            self.assertTrue(os.path.exists(os.path.join(out, "survey", "index.html")))
            page.set_survey(False)
            self.assertEqual(build_site.write_survey(out, "STAMP"), "removed")
            self.assertEqual(build_site.write_survey(out, "STAMP"), "absent")




class Switch(unittest.TestCase):
    """chrome.SURVEY and the addresses the build writes."""

    def tearDown(self):
        page.set_survey(False)
        page.set_report_receiver(chrome.REPORT_RECEIVER)

    def test_on_as_committed(self):
        # ON since 2026-11-07 (the receiver migrated and redeployed on Robin's go, the privacy
        # page's two sentences applied). Read from the file, not from chrome.SURVEY, which the other
        # tests' tearDown sets: until then this test read the module and passed with the switch on.
        with io.open(os.path.join(os.path.dirname(chrome.__file__), "chrome.py"), encoding="utf-8") as f:
            self.assertEqual(re.findall(r"(?m)^SURVEY = (\w+)$", f.read()), ["True"])

    def test_off_writes_no_address(self):
        page.set_survey(False)
        self.assertEqual(chrome.survey_receiver(), "")
        self.assertIn("var SURVEY_RECEIVER = '';", page.source("/site/survey.js"))
        self.assertIn("var SURVEY_HREF = '';", page.source("/site/shell.js"))

    def test_on_writes_both_addresses(self):
        old = chrome.REPORT_RECEIVER
        page.set_survey(True)
        self.assertEqual(chrome.survey_receiver(), "https://ordpar-receiver.ordpar.workers.dev/survey")
        self.assertIn('var SURVEY_RECEIVER = "https://ordpar-receiver.ordpar.workers.dev/survey";',
                      page.source("/site/survey.js"))
        self.assertIn('var SURVEY_HREF = "/survey/";', page.source("/site/shell.js"))
        for bundle in (page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF):
            self.assertIn('SURVEY_HREF="/survey/"', page.shipped(bundle).replace(" ", ""))
        # a look build's receiver: the stand-in's address with /survey
        page.set_report_receiver("http://127.0.0.1:8787/report")
        self.assertEqual(chrome.survey_receiver(), "http://127.0.0.1:8787/survey")
        # reports off: the survey off too, whatever SURVEY says
        page.set_report_receiver("")
        self.assertEqual(chrome.survey_receiver(), "")
        self.assertIn("var SURVEY_HREF = '';", page.source("/site/shell.js"))
        page.set_report_receiver(old)

    def test_the_slots_once(self):
        with self.assertRaises(ValueError):
            page.survey_js("var SURVEY_RECEIVER = 'https://x/survey';")
        with self.assertRaises(ValueError):
            page.survey_link_js("var SURVEY_HREF = ''; var SURVEY_HREF = '';")

    def test_one_build_by_the_environment(self):
        import build_site
        self.assertIsNone(build_site.survey_override({}))
        self.assertIs(build_site.survey_override({"ORDPAR_SURVEY": "1"}), True)
        self.assertIs(build_site.survey_override({"ORDPAR_SURVEY": "0"}), False)
        with self.assertRaises(ValueError):
            build_site.survey_override({"ORDPAR_SURVEY": "yes"})

    def test_google_gone(self):
        for name in sorted(os.listdir(SITE)):
            if name.endswith((".js", ".json", ".html", ".css")) and os.path.isfile(os.path.join(SITE, name)):
                self.assertNotIn("forms.gle", _read(SITE, name), name)
        self.assertNotIn("FEEDBACK_URL", _read(SITE, "shell.js"))
        for words in GOOGLE_GONE:
            self.assertNotIn(words, _read(ORDPAR, "privacy.md"))

    def test_the_footer_link(self):
        src = _read(SITE, "shell.js")
        body = src[src.index("var foot = doc.querySelector('.ordpar-footer-inner');"):src.index("addMoreLine();")]
        self.assertIn("labelled('a', 'ordpar-feedback ordpar-needs-js', 'footer.feedback')", body)
        self.assertIn("fb.setAttribute('href', SURVEY_HREF);", body)
        self.assertNotIn("_blank", body)                         # our own page: the same tab
        self.assertIn(".ordpar-devnote", body)                   # after the note while it is there
        self.assertIn("'ordpar-feedback-line'", body)            # else a line of its own (after launch)
        self.assertEqual(json.loads(_read(SITE, "strings", "en.json"))["footer.feedback"],
                         "Tell us what you think →")


@unittest.skipUnless(BUN, "bun is not on PATH")
class Script(unittest.TestCase):
    """survey.js on its own under bun, with no document: the API and the message."""

    PROG = r"""
const g = {};
const src = require('fs').readFileSync(%s, 'utf8');
new Function('globalThis', src.replace(/typeof globalThis !== 'undefined' \? globalThis : this/, 'globalThis'))(g);
const S = g.ordparSurvey;
console.log(JSON.stringify({
  receiver: S.SURVEY_RECEIVER,
  full: S.message({ level: 'Fluent', ideas: ['a', 'b'] }, 'x@example.org', ''),
  none: S.message({}, '', ''),
  trap: S.message({}, null, 'http://spam'),
  max: [S.MAX_ANSWER, S.MAX_CHOICE, S.MAX_FOLLOW],
}));
"""

    def test_api_and_message(self):
        with tempfile.TemporaryDirectory() as d:
            prog = os.path.join(d, "t.js")
            with open(prog, "w", encoding="utf-8") as f:
                f.write(self.PROG % json.dumps(os.path.join(SITE, "survey.js")))
            res = subprocess.run([BUN, prog], capture_output=True, timeout=60)
        out = json.loads(res.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertEqual(out["receiver"], "")
        self.assertEqual(out["full"], {"answers": {"level": "Fluent", "ideas": ["a", "b"]}, "follow": "x@example.org"})
        self.assertEqual(out["none"], {"answers": {}, "follow": None})
        self.assertEqual(out["trap"], {"answers": {}, "follow": None, "hp": "http://spam"})
        self.assertEqual(out["max"], [2000, 300, 254])

    def test_one_send_no_cookie_no_referrer_no_storage(self):
        src = _read(SITE, "survey.js")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        self.assertEqual(code.count("fetch("), 1)                         # one message, at Send
        at = code.index("fetch(")
        self.assertGreater(at, code.index("form.addEventListener('submit'"))
        self.assertIn("credentials: 'omit'", code)
        self.assertIn("referrerPolicy: 'no-referrer'", code)
        for word in ("localStorage", "sessionStorage", "indexedDB", "document.cookie", "location",
                     "navigator.userAgent", "sendBeacon", "XMLHttpRequest", "ORDPAR_BASE", "build"):
            self.assertNotIn(word, code, word)
        self.assertIn("body: JSON.stringify(message(got.answers, got.follow, got.trap))", code)


class Privacy(unittest.TestCase):
    """ordpar/privacy.md: the three approved changes, and the new section held to the code."""

    CASES = [(c, r, s) for c in (True, False) for r in (True, False) for s in (True, False)]

    def text(self, c, r, s):
        return " ".join(about.privacy_text(counting=c, reports=r, survey=s).split())

    def test_every_case_renders_whole(self):
        for c, r, s in self.CASES:
            with self.subTest(counting=c, reports=r, survey=s):
                _title, body = about.privacy_page(counting=c, reports=r, survey=s)
                for left in ("[[", "[if", "[/if]", "<!--"):
                    self.assertNotIn(left, body)
                self.assertNotRegex(body, r" [,.;:]")
                self.assertNotIn("  ", body)
                self.assertNotIn("google", body.lower())
                self.assertEqual('<h2 id="the-survey">The survey</h2>' in body, r and s)

    def test_the_opening(self):
        want = {
            (True, True): "They are GitHub, which serves the site's pages; Cloudflare, which runs our receiver "
                          "and our audio server; and " + ANTHROPIC,
            (True, False): "They are GitHub, which serves the site's pages; Cloudflare, which runs our receiver "
                           "and our audio server; and Anthropic, whose AI assistant may help us read a report "
                           "you send.",
            (False, False): "They are GitHub, which serves the site's pages; and Cloudflare, which runs our "
                            "audio server.",
        }
        for (r, s), sentence in want.items():
            t = self.text(False, r, s)
            self.assertIn(sentence, t)
        self.assertIn("They are GitHub, which serves the site's pages; and Cloudflare, which runs our receiver "
                      "and our audio server.", self.text(True, False, False))

    def test_what_your_browser_sends(self):
        """Robin's approval of 2026-11-07 ("Approve all three"): the survey named in "What your browser sends
        us" whenever it is on, the sentences unchanged while it is off."""
        on = self.text(False, True, True)
        self.assertIn('Apart from a request for a recording when you play one (see "Audio" below), a report of a '
                      'mistake if you send one (see "Reporting a mistake" below) and your answers to the survey if '
                      'you send them (see "The survey" below), your browser sends us nothing:', on)
        off = self.text(False, True, False)
        self.assertIn('Apart from a request for a recording when you play one (see "Audio" below) and a report of a '
                      'mistake if you send one (see "Reporting a mistake" below), your browser sends us nothing:', off)
        self.assertNotIn("survey", off.split("## What stays")[0] + off.split("## What your browser sends us")[1]
                         .split("##")[0])
        counting = self.text(True, True, True)
        self.assertIn('and nothing else apart from a report of a mistake, if you send one (see "Reporting a '
                      'mistake" below), or your answers to the survey, if you send them (see "The survey" '
                      'below):', counting)

    def test_where_answers_are_kept(self):
        t = self.text(False, True, True)
        self.assertIn("The answers are kept in Cloudflare's database service, in the EU, as reports are (see "
                      '"Where it is kept" above).', t)

    def test_questions_without_google(self):
        for c, r, s in self.CASES:
            t = self.text(c, r, s)
            q = t[t.index("## Questions"):]
            self.assertTrue(q.startswith("## Questions To ask about this page or to use any of these rights, "
                                         "write to post@ordpar.no. If what we collect changes"), q[:200])

    def test_the_section_word_for_word_after_reporting(self):
        for c in (True, False):
            raw = about.privacy_text(counting=c, reports=True, survey=True)
            blocks = [b.strip() for b in raw.split("\n\n")]
            at = blocks.index("## The survey")
            self.assertEqual(blocks[at:at + 4], SECTION)
            heads = [b for b in blocks if b.startswith("## ")]
            self.assertEqual(heads[heads.index("## The survey") - 1], "## Reporting a mistake")
            self.assertNotIn("The survey", about.privacy_text(counting=c, reports=True, survey=False))
            self.assertNotIn("survey", about.privacy_text(counting=c, reports=False, survey=True).lower())

    def test_the_claims_against_the_code(self):
        rec = _read(RECEIVER, "src", "reports.js")
        cap = int(re.search(r"export const REPORTS_PER_HOUR = (\d+);", rec).group(1))
        self.assertIn("the limit of %d an hour counts reports and answers together" % cap, SECTION[1])
        worker = _read(RECEIVER, "src", "worker.js")
        part = worker[worker.index("async function takeMessage("):worker.index("/** POST /report (site")]
        self.assertIn("withinCap(env, now)", part)                          # one cap, both kinds
        survey_part = worker[worker.index("export async function handleSurvey("):]
        survey_part = survey_part[:survey_part.index("\n}\n")]
        self.assertIn("takeMessage(", survey_part)
        self.assertIn("SQL.INSERT_SURVEY", survey_part)
        sql = _read(RECEIVER, "src", "sql.js")
        self.assertIn("UPDATE surveys SET done = ?2, follow = NULL", sql)    # deleted at done
        mig = _read(RECEIVER, "migrations", "0003_surveys.sql")
        cols = re.search(r"CREATE TABLE IF NOT EXISTS surveys \((.*?)\);", mig, re.S).group(1)
        self.assertEqual([c.strip().split()[0] for c in cols.strip().split(",\n")],
                         ["id", "day", "answers", "follow", "done"])     # no address, no browser name
        # the address or name never in Copy (reports_page.survey_copy_text)
        if not HAVE_READER:
            self.skipTest("scripts/reports_page.py is not here (the private repository's)")
        import reports_page
        t = reports_page.survey_copy_text({"id": 3, "day": "2026-11-07", "answers": {"level": "Fluent"},
                                            "follow": "secret-reader@example.org"})
        self.assertNotIn("secret-reader", t)
        self.assertIn("> Fluent", t)


def _post(url, body, origin="http://127.0.0.1:1"):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Origin": origin, "Content-Type": "text/plain;charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.status


@unittest.skipUnless(BUN, "bun is not on PATH")
@unittest.skipUnless(HAVE_READER, "scripts/reports_page.py is not here (the private repository's)")
class ReadingPage(unittest.TestCase):
    """scripts/reports_page.py's survey part and serve.py's /reports, against the receiver's stand-in."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, REPORTS_TOKEN=TOKEN)
        cls.proc = subprocess.Popen([BUN, "tools/local.mjs", "--port", "0"], cwd=RECEIVER, env=env,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        line = cls.proc.stdout.readline().decode("utf-8", "replace").strip()
        if not line.startswith("listening "):
            cls.proc.kill()
            raise RuntimeError("the stand-in did not start: %r" % line)
        cls.url = line.split(" ", 1)[1]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.access = os.path.join(cls.tmp.name, "ordpar-reports.json")
        cls.old = os.environ.get("ORDPAR_REPORTS_FILE")
        os.environ["ORDPAR_REPORTS_FILE"] = cls.access
        with open(cls.access, "w", encoding="utf-8") as f:
            json.dump({"url": cls.url, "token": TOKEN}, f)
        _post(cls.url + "/survey", {"answers": {"anything_else": "Great <b>&", "level": "Fluent",
                                                "ideas": ["Example sentences for the words and meanings that don't have any yet"],
                                                "retired_key": "old"},
                                    "follow": "reader@example.org"})
        _post(cls.url + "/survey", {"answers": {"devices": ["Phone", "Computer"]}, "follow": None})
        import reports_page
        cls.rp = reports_page

    @classmethod
    def tearDownClass(cls):
        try:
            cls.proc.stdin.close()
            cls.proc.wait(timeout=10)
        except Exception:
            cls.proc.kill()
        cls.proc.stdout.close()
        if cls.old is None:
            os.environ.pop("ORDPAR_REPORTS_FILE", None)
        else:
            os.environ["ORDPAR_REPORTS_FILE"] = cls.old
        cls.tmp.cleanup()

    def test_a_listed_under_their_questions(self):
        got = self.rp.queue_json()
        self.assertTrue(got["ok"], got)
        self.assertIsNone(got["surveys_message"])
        first = [s for s in got["surveys"] if s["follow"]][0]
        self.assertEqual([i[0] for i in first["items"]], [
            "How well do you know Norwegian?", "Some ideas we have. Which would you use?",
            "Anything else you'd like to tell us?", "retired_key"])           # the survey's order, then the rest
        self.assertEqual(first["items"][1][1], "- Example sentences for the words and meanings that don't have any yet")
        self.assertEqual(first["follow"], "reader@example.org")
        self.assertNotIn("reader@example.org", first["copy"])
        self.assertIn("## Anything else you'd like to tell us?\n\n> Great <b>&", first["copy"])
        self.assertEqual([s["id"] for s in got["surveys"]], sorted([s["id"] for s in got["surveys"]], reverse=True))

    def test_b_done_deletes_the_follow_up_and_keeps_the_answers(self):
        sid = [s for s in self.rp.queue_json()["surveys"] if s["follow"]][0]["id"]
        msg, ok = self.rp.mark_survey_done({"id": sid})
        self.assertTrue(ok, msg)
        self.assertNotIn(sid, [s["id"] for s in self.rp.queue_json()["surveys"]])
        msg, ok = self.rp.mark_survey_done({"id": sid})
        self.assertFalse(ok)
        self.assertIn("not open", msg)
        self.assertEqual(self.rp.mark_survey_done({"id": "x"}), ("not an answers id", False))

    def test_c_a_receiver_without_surveys_said_plainly(self):
        import unittest.mock as mock
        with mock.patch.object(self.rp, "_call", return_value=(404, b"")):
            surveys, msg = self.rp.surveys_json()
        self.assertIsNone(surveys)
        self.assertIn("does not take survey answers yet (404)", msg)

    def test_d_through_serve(self):
        import serve
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            base = "http://127.0.0.1:%d" % httpd.server_address[1]
            with urllib.request.urlopen(base + "/reports", timeout=10) as res:
                html = res.read().decode("utf-8")
            self.assertIn("Survey answers", html)
            self.assertIn("/reports/survey-done", html)
            self.assertNotIn("innerHTML", html)
            _post(self.url + "/survey", {"answers": {"again": "via serve"}, "follow": "z@example.org"})
            with urllib.request.urlopen(base + "/reports/data.json", timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
            sv = [s for s in data["surveys"] if s["items"] == [["Would you use it again? For what?", "via serve"]]][0]
            self.assertNotIn("z@example.org", sv["copy"])
            req = urllib.request.Request(base + "/reports/survey-done", data=json.dumps({"id": sv["id"]}).encode("utf-8"),
                                         method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as res:
                out = json.loads(res.read().decode("utf-8"))
            self.assertTrue(out["ok"], out)
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
