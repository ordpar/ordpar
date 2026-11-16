# -*- coding: utf-8 -*-
"""Site decisions 166 (Robin, 2026-11-05): "Report a mistake" — the page's side, its switch, and
Robin's reading page. Brief: `docs/sessions/2026-09-19-ordpar-site-review/evidence/
brief-report-button-166-2026-11-05.md`. The receiver's own tests are `ordpar/receiver/test/
report.test.js` (`test_ordpar_receiver104.py` runs them); the button and form in a browser,
`test_ordpar_browser_report166.py`.

* **The wiring**: `report.js` in both combined scripts, before `lookup.js` (whose `resultControls`
  calls it) and the page script (`page.PAGE_JS` `foot`, which calls it after Share); the deck's
  cards have no foot and never load it.
* **The switch** is the report's own: `var REPORT_RECEIVER = '';` once in the source, the address
  written in by the build alone; since 2026-11-05 (166's go-live) both shipped bundles carry the
  live receiver's address (`chrome.REPORT_RECEIVER`), before that they shipped empty. The counting
  untouched (`events.js` `RECEIVER` empty; `chrome.PRIVACY` is the page's switch, not the
  counting's, since the privacy build). Under bun with the switch empty, `mount` draws nothing.
* **What is sent** (`message`): exactly the article's id, the build, the category or null, the
  text, the reply address or null, the name to credit or null (166's follow-up: `credit`, the
  sixth field; `creditOk` refuses a link or more than 60 characters, as the receiver does); the
  trap field only when filled; never cookies or a referrer; not held back by the stats setting,
  GPC, DNT or `navigator.webdriver` (the counting's rules, not a report's: the reader pressed Send).
* **The words**: English (152), the same in `report.js`'s fallback and `strings/en.json`; the
  pick, "Suggest a correction" and "Thank you, your report has been sent."; the 429's message the
  total cap's, never "you have sent several".
* **The privacy section** against the code: the total cap's number, no scrambled code, the name to
  credit and its consent.
* **Robin's page** (`scripts/reports_page.py`, `/reports` in `scripts/serve.py`), against the
  receiver's stand-in (`ordpar/receiver/tools/local.mjs`, the Worker's code under bun): the open
  reports newest first with their links and the name to credit; Done deletes the reply address and
  the name; Fixed writes the list of fixes (a new fix, a join, other articles, the name only when
  published) and then deletes them too; taking a name off; a wrong token, a missing access file
  and a receiver that does not answer each said plainly; the token never in the page; served
  through serve.py on this computer. The pure parts (the list's plan, the thanks page, the 403 to
  another address): `test_ordpar_thanks166.py`.

Skipped in part without bun.
"""
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
SITE = os.path.join(ORDPAR, "site")
RECEIVER = os.path.join(ORDPAR, "receiver")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from ordpar.sitegen import about, page, chrome  # noqa: E402
from ordpar.sitegen import strings as strings_mod  # noqa: E402

#: the reports' reading page is the private repository's (scripts/reports_page.py; decisions 184:
#: not in the public export), so what reads through it skips where it is not
HAVE_READER = importlib.util.find_spec("reports_page") is not None

BUN = shutil.which("bun")
TOKEN = "unit-test-token-0123456789abcdef"


def _read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Wiring(unittest.TestCase):

    def test_in_both_bundles_before_its_callers(self):
        a = page.ARTICLE_JS_PARTS
        self.assertIn(page.REPORT_JS_HREF, a)
        self.assertLess(a.index(page.REPORT_JS_HREF), a.index(page.LOOKUP_JS_HREF))
        self.assertLess(a.index(page.REPORT_JS_HREF), a.index(page.JS_HREF))
        s = page.SHELL_JS_PARTS
        self.assertIn(page.REPORT_JS_HREF, s)
        self.assertLess(s.index(page.REPORT_JS_HREF), s.index(page.LOOKUP_JS_HREF))
        for url in (page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF):
            self.assertIn("global.ordparReport = api;", page.shipped(url))

    def test_the_article_page_foot(self):
        js = page.PAGE_JS
        foot = js[js.index("function foot(){"):js.index("foot();")]
        share, mount, insert = (foot.index("FOOT.share"), foot.index("R.mount(p,E.getAttribute('data-article-id'))"),
                                foot.index("f.insertBefore(p,f.firstChild)"))
        self.assertLess(share, mount)
        self.assertLess(mount, insert)

    def test_result_controls(self):
        look = _read(SITE, "lookup.js")
        rc = look[look.index("function resultControls(a) {"):look.index("function mountArticle(")]
        self.assertIn("global.ordparReport.mount(p, a.id)", rc)
        self.assertLess(rc.index("p.appendChild(share)"), rc.index("ordparReport.mount"))
        self.assertLess(rc.index("ordparReport.mount"), rc.index("heartButton"))

    def test_no_other_maker_of_an_article_foot(self):
        # every place an article's foot row is made calls the report's mount: the page script and
        # resultControls; the minis (cut at the foot) and the deck's cards (no foot) have none
        makers = []
        for name in sorted(os.listdir(SITE)):
            if name.endswith(".js") and re.search(r"['\"]ordpar-result-controls['\"]", _read(SITE, name)):
                makers.append(name)
        self.assertEqual(makers, ["lookup.js"])
        self.assertIn("p.className='ordpar-result-controls'", page.PAGE_JS)


class Switch(unittest.TestCase):

    def test_its_own_address_empty(self):
        # the source line stays empty: the address is written in by the build alone
        src = _read(SITE, "report.js")
        self.assertEqual(src.count("var REPORT_RECEIVER = '';"), 1)
        self.assertNotIn("workers.dev", src)
        self.assertNotIn("var RECEIVER", src)
        # since 2026-11-05 (166's go-live) the shipped scripts carry the live receiver's address,
        # once each (until then they shipped the empty line)
        live = "https://ordpar-receiver.ordpar.workers.dev/report"
        self.assertEqual(chrome.REPORT_RECEIVER, live)
        for url in (page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF):
            shipped = page.shipped(url)
            self.assertEqual(shipped.count("var REPORT_RECEIVER = %s;" % json.dumps(live)), 1, url)
            self.assertNotIn("var REPORT_RECEIVER = '';", shipped)

    def test_the_counting_untouched(self):
        # the counting's line stays empty (chrome.PRIVACY is the privacy page's switch since the
        # privacy build of 2026-11-05, no longer the counting's; on since 166's go-live)
        self.assertEqual(_read(SITE, "events.js").count("var RECEIVER = '';"), 1)
        self.assertIs(chrome.counting(), False)
        self.assertNotIn("ordparEvents", _read(SITE, "report.js"))

    def test_not_held_back_by_the_countings_rules(self):
        src = _read(SITE, "report.js")
        code = re.sub(r"(?m)^\s*(//|\*).*$", "", re.sub(r"/\*.*?\*/", "", src, flags=re.S))
        for word in ("webdriver", "globalPrivacyControl", "doNotTrack", "'stats'", "localStorage", "cookie"):
            self.assertNotIn(word, code, word)
        self.assertIn("credentials: 'omit'", code)
        self.assertIn("referrerPolicy: 'no-referrer'", code)


@unittest.skipUnless(BUN, "bun is not on PATH")
class Script(unittest.TestCase):
    """report.js on its own under bun, with no document: the API and the message."""

    PROG = r"""
const g = {};
const src = require('fs').readFileSync(%s, 'utf8');
new Function('globalThis', src.replace(/typeof globalThis !== 'undefined' \? globalThis : this/, 'globalThis'))(g);
const R = g.ordparReport;
const out = {
  receiver: R.REPORT_RECEIVER,
  mountOff: R.mount({ appendChild() { throw new Error('drawn'); } }, 5),
  full: R.message(1000, '3be273e42565c3a6', 'audio', 'x', 'a@example.org', 'Kari N.', ''),
  none: R.message(7, null, 'spelling', 'y', '', '', ''),
  trap: R.message(7, null, null, 'y', null, null, 'http://spam'),
  max: [R.MAX_TEXT, R.MAX_REPLY, R.MAX_CREDIT, R.CATEGORIES],
  credit: ['', 'Kari', '@kari_n', 'x'.repeat(60), 'x'.repeat(61), 'https://a.b', 'www.spam', 'spam.com', 'Kari (kari.no)']
    .map((n) => R.creditOk(n)),
};
console.log(JSON.stringify(out));
"""

    def test_api_and_message(self):
        with tempfile.TemporaryDirectory() as d:
            prog = os.path.join(d, "t.js")
            with open(prog, "w", encoding="utf-8") as f:
                f.write(self.PROG % json.dumps(os.path.join(SITE, "report.js")))
            res = subprocess.run([BUN, prog], capture_output=True, timeout=60)
        out = json.loads(res.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertEqual(out["receiver"], "")
        self.assertIsNone(out["mountOff"])
        self.assertEqual(out["full"], {"id": 1000, "build": "3be273e42565c3a6", "category": "audio",
                                       "text": "x", "reply": "a@example.org", "credit": "Kari N."})
        self.assertEqual(out["none"], {"id": 7, "build": None, "category": None, "text": "y", "reply": None,
                                       "credit": None})
        self.assertEqual(out["trap"]["hp"], "http://spam")
        self.assertEqual(out["max"], [2000, 254, 60, ["translation", "audio", "norwegian", "other"]])
        self.assertEqual(out["credit"], [True, True, True, True, False, False, False, False, False])


class Words(unittest.TestCase):

    def test_fallback_equals_the_strings_file(self):
        src = _read(SITE, "report.js")
        block = src[src.index("var WORDS = {"):src.index("};", src.index("var WORDS = {"))]
        fallback = dict(re.findall(r"'(report\.[\w.]+)': '((?:[^'\\]|\\.)*)'", block))
        en = json.loads(_read(SITE, "strings", "en.json"))
        mine = {k: v for k, v in en.items() if k.startswith("report.")}
        self.assertEqual(fallback, mine)
        for k in mine:
            self.assertNotIn(k, strings_mod.NB)        # the interface's English (152)

    def test_robins_pick_and_the_caps_message(self):
        en = json.loads(_read(SITE, "strings", "en.json"))
        # decisions 166: "Suggest a correction" + the lab's defaults (the confirmation c1)
        self.assertEqual(en["report.button"], "Suggest a correction")
        self.assertEqual(en["report.sent"], "Thank you, your report has been sent.")
        # the cap is everyone's: the 429's words do not blame the reader
        self.assertNotIn("you have sent", en["report.tooMany"].lower())
        self.assertIn("in the last hour", en["report.tooMany"])
        self.assertIn("Your text is kept here", en["report.tooMany"])
        # the name to credit's field
        self.assertEqual(en["report.credit"], "Name to credit (optional)")
        self.assertIn("no links", en["report.creditHint"])
        self.assertIn("Thanks page", en["report.creditHint"])

    def test_the_form_is_the_labs_pick(self):
        src = _read(SITE, "report.js")
        self.assertIn("el('select', 'ordpar-report-select')", src)          # a drop-down
        self.assertNotIn("r.type = 'radio'", src)
        self.assertIn("text.rows = 4;", src)                                 # 4 lines high
        self.assertIn("el('input', 'ordpar-report-credit')", src)
        self.assertIn("credit.maxLength = MAX_CREDIT;", src)



class Privacy(unittest.TestCase):
    """The privacy page's draft section (`ordpar/privacy.md` "Reporting a mistake") against the code."""

    def test_the_section_and_its_numbers(self):
        # the page with the counting and reports on, its [if]s resolved (site decisions 166's
        # privacy build, 2026-11-05: the text follows the switches; the other cases are
        # test_ordpar_privacy166.py's)
        text = " ".join(about.privacy_text(counting=True, reports=True).split())
        self.assertIn("## Reporting a mistake", text)
        per_hour = int(re.search(r"export const REPORTS_PER_HOUR = (\d+);",
                                 _read(RECEIVER, "src", "reports.js")).group(1))
        self.assertIn("it accepts at most %d reports an hour from everyone together" % per_hour, text)
        self.assertIn("delete it once we have dealt with the report", text)
        self.assertIn("We delete it once we have dealt with your report.",
                      json.loads(_read(SITE, "strings", "en.json"))["report.replyHint"])
        # what a report holds, as report.js `message` sends it and reports.js keeps it
        self.assertIn("what you wrote, where you said the mistake is (if you chose), your email address "
                      "(if you gave one), a name to credit (if you gave one), the article's number, and which "
                      "version of the site", text)
        self.assertIn("nothing else apart from a report of a mistake, if you send one", text)
        # no placeholder of its own: the page's only one stays the receiver's address
        sect = text[text.index("## Reporting a mistake"):text.index("## Offline and the installed app")]
        self.assertNotIn("[[", sect)
        # 166's follow-up: no per-sender limit, so no scrambled code and no daily secret for reports
        for gone in ("scrambled code", "from one sender", "day's secret", "rate"):
            self.assertNotIn(gone, sect, gone)
        # 169 (a), Robin's approval 2026-11-06: what Cloudflare itself keeps of the request, said with it
        self.assertIn("It does not use or store your IP address or your browser's name for a report, though "
                      "Cloudflare keeps records of requests to the receiver too, with their IP address and time, "
                      "which we can see for 32 days, as for the audio server (see \"Audio\" above).", sect)
        self.assertIn('"Suggest a correction"', sect)
        # the name to credit: optional, published only with a fix, deleted at closing, consent, taken off on request
        self.assertIn("The name to credit is optional", sect)
        self.assertIn("[Thanks to our readers](https://ordpar.no/thanks/)", sect)
        self.assertIn("the name is deleted from the receiver as your email address is", sect)
        self.assertIn("your consent, which you give by writing it in the field and can withdraw at any time "
                      "(GDPR Article 6(1)(a))", sect)
        self.assertIn("If you want your name taken off the page, write to post@ordpar.no", sect)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _post(url, body, origin="http://127.0.0.1:1"):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Origin": origin, "Content-Type": "text/plain;charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.status


@unittest.skipUnless(BUN, "bun is not on PATH")
@unittest.skipUnless(HAVE_READER, "scripts/reports_page.py is not here (the private repository's)")
class ReadingPage(unittest.TestCase):
    """scripts/reports_page.py and serve.py's /reports, against the receiver's stand-in."""

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
        cls.fixes = os.path.join(cls.tmp.name, "reader-fixes.jsonl")
        cls.old_env = os.environ.get("ORDPAR_REPORTS_FILE")
        cls.old_fixes = os.environ.get("ORDPAR_FIXES_FILE")
        os.environ["ORDPAR_REPORTS_FILE"] = cls.access
        os.environ["ORDPAR_FIXES_FILE"] = cls.fixes
        cls.write_access(cls.url, TOKEN)
        _post(cls.url + "/report", {"id": 1000, "build": None, "category": "audio", "text": "first <b>&",
                                     "reply": "reader@example.org", "credit": "Kari N."})
        _post(cls.url + "/report", {"id": 98, "build": "3be273e42565c3a6", "category": None,
                                     "text": "second", "reply": None})
        import reports_page
        cls.rp = reports_page

    @classmethod
    def write_access(cls, url, token):
        with open(cls.access, "w", encoding="utf-8") as f:
            json.dump({"url": url, "token": token}, f)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.proc.stdin.close()
            cls.proc.wait(timeout=10)
        except Exception:
            cls.proc.kill()
        cls.proc.stdout.close()
        for name, old in (("ORDPAR_REPORTS_FILE", cls.old_env), ("ORDPAR_FIXES_FILE", cls.old_fixes)):
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        cls.tmp.cleanup()

    def tearDown(self):
        self.write_access(self.url, TOKEN)

    def test_a_list_newest_first_with_links(self):
        got = self.rp.queue_json()
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["receiver"], self.url)
        texts = [r["text"] for r in got["reports"]]
        self.assertEqual(texts[:2], ["second", "first <b>&"])
        first = got["reports"][1]
        self.assertEqual(first["live"], "https://ordpar.no/bm-en/1000/")
        self.assertEqual(first["local_path"], "/bm-en/1000/")
        self.assertEqual((first["category"], first["reply"], first["credit"]),
                         ("audio", "reader@example.org", "Kari N."))
        self.assertIsNone(got["reports"][0]["credit"])
        self.assertEqual(got["fixes"], [])

    def _rid(self, text):
        return [r for r in self.rp.queue_json()["reports"] if r["text"] == text][0]["id"]

    def _stored(self, rid):
        """The report among the OPEN ones (none once it is closed). That closing deletes the address
        and the name in the receiver's table is pinned by `receiver/test/report.test.js` (the
        stand-in's database is not reachable from here); here, that the page's way out closed it."""
        return [r for r in self.rp.queue_json()["reports"] if r["id"] == rid]

    def test_b_done_deletes_the_address_and_the_name(self):
        _post(self.url + "/report", {"id": 5, "text": "to be done", "reply": "x@example.org", "credit": "Ola"})
        rid = self._rid("to be done")
        before = self.rp.read_fixes()
        msg, ok = self.rp.mark_done({"id": rid})
        self.assertTrue(ok, msg)
        self.assertIn("reply address and name deleted", msg)
        self.assertEqual(self._stored(rid), [])
        self.assertEqual(self.rp.read_fixes(), before)       # Done writes no fix
        msg, ok = self.rp.mark_done({"id": rid})
        self.assertFalse(ok)
        self.assertIn("not open", msg)
        self.assertEqual(self.rp.mark_done({"id": "x"}), ("not a report id", False))

    def test_b2_fixed_writes_the_list_then_closes(self):
        before = self.rp.read_fixes()
        _post(self.url + "/report", {"id": 4242, "text": "fixed, named", "reply": "k@example.org", "credit": "Kari N."})
        _post(self.url + "/report", {"id": 4242, "text": "fixed, joined", "credit": "Not Published"})
        _post(self.url + "/report", {"id": 4242, "text": "fixed, two articles"})
        a, b, c = self._rid("fixed, named"), self._rid("fixed, joined"), self._rid("fixed, two articles")
        # a new fix of its article, the name published (trimmed by Robin)
        msg, ok = self.rp.mark_fixed({"id": a, "article": 4242, "fixes": [{"article": 4242}],
                                      "name": "  Kari  N. ", "publish": True})
        self.assertTrue(ok, msg)
        self.assertIn("with the name", msg)
        fixes = self.rp.read_fixes()
        new = [f for f in fixes if f not in before]
        self.assertEqual(len(new), 1)
        n = new[0]["fix"]
        self.assertEqual({k: new[0][k] for k in ("article", "reports", "names")},
                         {"article": 4242, "reports": [a], "names": ["Kari N."]})
        self.assertEqual(new[0]["date"], self.rp.today())
        self.assertEqual(self._stored(a), [])                # closed: address and name gone from the receiver
        # joined to that fix, the name NOT published: the list never sees it
        msg, ok = self.rp.mark_fixed({"id": b, "article": 4242, "fixes": [{"fix": n}],
                                      "name": "Not Published", "publish": False})
        self.assertTrue(ok, msg)
        f = [x for x in self.rp.read_fixes() if x["fix"] == n][0]
        self.assertEqual((f["reports"], f["names"]), ([a, b], ["Kari N."]))
        with open(self.fixes, encoding="utf-8") as fh:
            self.assertNotIn("Not Published", fh.read())
        self.assertEqual(self._stored(b), [])
        # one report, two fixes: a new fix of its article and one of another article
        msg, ok = self.rp.mark_fixed({"id": c, "article": 4242, "fixes": [{"article": 4242}, {"article": 98}],
                                      "name": None, "publish": False})
        self.assertTrue(ok, msg)
        mine = [x for x in self.rp.read_fixes() if c in x["reports"]]
        self.assertEqual(sorted((x["article"], x["names"]) for x in mine), [(98, []), (4242, [])])
        # refused, nothing written: a fix of another article to join, no fix chosen, a link as a name
        _post(self.url + "/report", {"id": 4242, "text": "refused"})
        d = self._rid("refused")
        snapshot = self.rp.read_fixes()
        for bad in ({"fixes": [{"fix": [x for x in mine if x["article"] == 98][0]["fix"]}]}, {"fixes": []},
                    {"fixes": [{"article": 4242}], "name": "spam.com", "publish": True}):
            msg, ok = self.rp.mark_fixed(dict({"id": d, "article": 4242}, **bad))
            self.assertFalse(ok, (bad, msg))
        self.assertEqual(self.rp.read_fixes(), snapshot)
        self.assertEqual(len(self._stored(d)), 1)            # still open on the receiver
        # a name taken off on request: the fix stays
        msg, ok = self.rp.unname({"fix": n, "name": "Kari N."})
        self.assertTrue(ok, msg)
        f = [x for x in self.rp.read_fixes() if x["fix"] == n][0]
        self.assertEqual((f["reports"], f["names"]), ([a, b], []))
        self.assertFalse(self.rp.unname({"fix": n, "name": "Kari N."})[1])

    def test_b3_fixed_twice_when_the_receiver_failed(self):
        _post(self.url + "/report", {"id": 777, "text": "receiver down"})
        rid = self._rid("receiver down")
        self.write_access("http://127.0.0.1:%d" % _free_port(), TOKEN)
        msg, ok = self.rp.mark_fixed({"id": rid, "article": 777, "fixes": [{"article": 777}], "publish": False})
        self.assertFalse(ok)
        self.assertIn("press Fixed again", msg)
        self.write_access(self.url, TOKEN)
        msg, ok = self.rp.mark_fixed({"id": rid, "article": 777, "fixes": [{"article": 777}], "publish": False})
        self.assertTrue(ok, msg)
        self.assertEqual(len([f for f in self.rp.read_fixes() if rid in f["reports"]]), 1)   # not twice

    def test_c_failures_said_plainly(self):
        self.write_access(self.url, "wrong-token-0123456789abcdef")
        got = self.rp.queue_json()
        self.assertFalse(got["ok"])
        self.assertIn("401", got["message"])
        os.remove(self.access)
        got = self.rp.queue_json()
        self.assertIn("No access file", got["message"])
        self.write_access("http://127.0.0.1:%d" % _free_port(), TOKEN)
        got = self.rp.queue_json()
        self.assertIn("did not answer", got["message"])

    def test_d_through_serve(self):
        import serve
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            base = "http://127.0.0.1:%d" % httpd.server_address[1]
            with urllib.request.urlopen(base + "/reports", timeout=10) as res:
                html = res.read().decode("utf-8")
            self.assertIn("Reports from readers", html)
            self.assertIn("textContent", html)          # the readers' text never as markup
            self.assertNotIn("innerHTML", html)
            self.assertNotIn(TOKEN, html)
            with urllib.request.urlopen(base + "/reports/data.json", timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["ok"], data)
            self.assertNotIn(TOKEN, json.dumps(data))
            _post(self.url + "/report", {"id": 6, "text": "via serve", "reply": "y@example.org"})
            rid = [r for r in self.rp.queue_json()["reports"] if r["text"] == "via serve"][0]["id"]
            req = urllib.request.Request(base + "/reports/done", data=json.dumps({"id": rid}).encode("utf-8"),
                                         method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as res:
                out = json.loads(res.read().decode("utf-8"))
            self.assertTrue(out["ok"], out)
            _post(self.url + "/report", {"id": 6, "text": "via serve, fixed", "credit": "Per"})
            rid = [r for r in self.rp.queue_json()["reports"] if r["text"] == "via serve, fixed"][0]["id"]
            for path, body in (("/reports/fixed", {"id": rid, "article": 6, "fixes": [{"article": 6}],
                                                   "name": "Per", "publish": True}),):
                req = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"),
                                             method="POST", headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as res:
                    out = json.loads(res.read().decode("utf-8"))
                self.assertTrue(out["ok"], out)
            fix = [f for f in self.rp.read_fixes() if rid in f["reports"]][0]
            req = urllib.request.Request(base + "/reports/unname", method="POST",
                                         data=json.dumps({"fix": fix["fix"], "name": "Per"}).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as res:
                self.assertTrue(json.loads(res.read().decode("utf-8"))["ok"])
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
