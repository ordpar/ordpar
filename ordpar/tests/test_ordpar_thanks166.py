# -*- coding: utf-8 -*-
"""Site decisions 166's follow-up (Robin, 2026-11-05): the name to credit's other end — the list of
fixes, its one writer, the page `/thanks/` — and Robin's `/reports` on this computer only. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-report-followup-166-2026-11-05.md`.
Stdlib unittest, no bun and no network (the parts that need the receiver's stand-in are in
`test_ordpar_report166.py`).

* **The page's two numbers** (`sitegen/thanks.py`): "Thanks to X reports that led to Y fixes", X
  the DISTINCT report ids, Y the lines, counted from the list at build time; one/many forms;
  with no fix, "No report has led to a fix yet." and no list.
* **The list under them**: newest first; each fix's headword linked to its page, its date, the
  published names ("Kari and Ola"), or "a reader" (one report) / "readers" (several); a name
  escaped, never markup.
* **The list's file** (`ordpar/reader-fixes.jsonl`): committed and valid; a bad line (a fix number
  twice, a link as a name, no report) refused by the reader; the receiver's `LINK` and
  `MAX_CREDIT` the same here.
* **Its one writer**: `scripts/reports_page.py` (`write_fixes`, called by `mark_fixed` and
  `unname` only); nothing else writes the file (the build reads it through `thanks.py`). `plan_fixed`: a new fix, a join to a
  fix of the same article (refused for another article's), new fixes of other articles, the name
  only when published, a second press adding nothing.
* **The page in the site**: `page.thanks_page` (indexed, its canonical `/thanks/`), written by
  `build_site.py`, in the sitemap (both writers' `indexed_other`), in the offline copy, linked
  from About's "Thanks" (and so the README) — since the reports' switch (2026-11-05), all only
  while reports are on (`chrome.REPORT_RECEIVER`; off: `test_ordpar_reportswitch166.py`).
* **This computer only** (`scripts/serve.py`): `/reports`, its data, its three write endpoints and
  the access file answer 403 to another address on the network, GET, HEAD and POST; the rest of the
  server still answers it; 127.0.0.1 gets the page.

The report reader and the browse server are private: in the public repository the tests that need
them skip, naming the module, and the rest run.
"""
import importlib.util
import io
import json
import os
import re
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
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from ordpar.sitegen import thanks, page, chrome, about, wordpages  # noqa: E402
from ordpar import build_site, build_offline  # noqa: E402
try:
    import reports_page  # noqa: E402
except ModuleNotFoundError as e:
    if e.name != "reports_page":
        raise
    reports_page = None
#: the report reader and the browse server are private: in the public repository the tests of
#: the writer, of Remove and of this computer only skip with these reasons
NO_READER = "needs reports_page (scripts/reports_page.py), which the public repository does not have"
HAVE_SERVE = importlib.util.find_spec("serve") is not None
NO_SERVE = "needs serve (scripts/serve.py), which the public repository does not have"

WORDS = {1000: "lek III", 98: "hus", 5: "<b>"}


def _fix(n, date, art, reports, names=()):
    return {"fix": n, "date": date, "article": art, "reports": list(reports), "names": list(names)}


def _read(*p):
    with io.open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Numbers(unittest.TestCase):

    def test_x_distinct_reports_y_lines(self):
        fixes = [_fix(1, "2026-11-05", 1000, [4, 7]), _fix(2, "2026-11-06", 98, [7]),
                 _fix(3, "2026-11-06", 98, [9], ["Kari"])]
        self.assertEqual(thanks.counts(fixes), (3, 3))          # 4, 7, 9 — report 7 counted once
        title, body = thanks.page(fixes, WORDS.get)
        self.assertEqual(title, "Thanks to our readers")
        self.assertIn("<p>Thanks to 3 reports that led to 3 fixes.</p>", body)
        self.assertNotIn("No report has led to a fix yet.", body)

    def test_one_and_many(self):
        _t, body = thanks.page([_fix(1, "2026-11-05", 1000, [4])], WORDS.get)
        self.assertIn("Thanks to 1 report that led to 1 fix.", body)
        _t, body = thanks.page([_fix(1, "2026-11-05", 1000, [4]), _fix(2, "2026-11-05", 98, [4])], WORDS.get)
        self.assertIn("Thanks to 1 report that led to 2 fixes.", body)     # one report, two fixes

    def test_none_yet(self):
        _t, body = thanks.page([], WORDS.get)
        self.assertIn("<p>No report has led to a fix yet.</p>", body)
        self.assertNotIn("Thanks to 0", body)
        self.assertNotIn("<ul", body)
        self.assertNotIn("{list}", body)


class TheList(unittest.TestCase):

    def test_newest_first_word_date_and_who(self):
        fixes = [_fix(1, "2026-11-05", 1000, [4]), _fix(2, "2026-11-07", 98, [5, 6]),
                 _fix(3, "2026-11-07", 98, [8], ["Kari", "Ola"]), _fix(4, "2026-11-06", 5, [9], ["<i>x</i>"]),
                 _fix(5, "2026-11-06", 4321, [10])]
        _t, body = thanks.page(fixes, WORDS.get)
        items = re.findall(r"<li>(.*?)</li>", body)
        self.assertEqual(items, [
            '<a href="/bm-en/98/" lang="nb">hus</a>, 7 November 2026, from Kari and Ola',
            '<a href="/bm-en/98/" lang="nb">hus</a>, 7 November 2026, from readers',
            '<a href="/bm-en/4321/" lang="nb">#4321</a>, 6 November 2026, from a reader',
            '<a href="/bm-en/5/" lang="nb">&lt;b&gt;</a>, 6 November 2026, from &lt;i&gt;x&lt;/i&gt;',
            '<a href="/bm-en/1000/" lang="nb">lek III</a>, 5 November 2026, from a reader'])

    def test_who(self):
        self.assertEqual(thanks.who(_fix(1, "2026-11-05", 1, [1])), "a reader")
        self.assertEqual(thanks.who(_fix(1, "2026-11-05", 1, [1, 2])), "readers")
        self.assertEqual(thanks.who(_fix(1, "2026-11-05", 1, [1, 2, 3], ["A", "B", "C"])), "A, B and C")


class TheFile(unittest.TestCase):

    def test_committed_and_valid(self):
        self.assertEqual(thanks.FIXES_PATH, os.path.join(ORDPAR, "reader-fixes.jsonl"))
        self.assertTrue(os.path.exists(thanks.FIXES_PATH))
        thanks.read_fixes(thanks.FIXES_PATH)                   # raises on a bad line

    def test_bad_lines_refused(self):
        good = thanks.line_text(_fix(1, "2026-11-05", 1000, [4], ["Kari"]))
        self.assertEqual(json.loads(good), _fix(1, "2026-11-05", 1000, [4], ["Kari"]))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.jsonl")
            for bad in (good + "\n" + good,                                         # fix 1 twice
                        good.replace('"Kari"', '"spam.com"'),                       # a link as a name
                        good.replace('"Kari"', '"%s"' % ("x" * 61)),                # too long
                        good.replace("[4]", "[]"), good.replace("[4]", "[4, 4]"),   # no report, one twice
                        good.replace("2026-11-05", "5 Nov"), "not json"):
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write(bad + "\n")
                with self.assertRaises(ValueError, msg=bad):
                    thanks.read_fixes(path)
            self.assertEqual(thanks.read_fixes(os.path.join(d, "missing.jsonl")), [])

    def test_the_receivers_rules(self):
        src = _read(ORDPAR, "receiver", "src", "reports.js")
        js = re.search(r"export const LINK = /(.*)/i;", src).group(1)
        self.assertEqual(js.replace("\\/", "/"), thanks.LINK.pattern)
        self.assertEqual(int(re.search(r"export const MAX_CREDIT = (\d+);", src).group(1)), thanks.MAX_NAME)


@unittest.skipUnless(reports_page, NO_READER)
class OneWriter(unittest.TestCase):

    def test_no_other_code_names_the_file(self):
        named = []
        for top in (os.path.join(ROOT, "scripts"), ORDPAR):
            for dirpath, dirs, files in os.walk(top):
                dirs[:] = [x for x in dirs if x not in ("out", "node_modules", "__pycache__", "tests", ".git")]
                for name in files:
                    if name.endswith((".py", ".js", ".mjs")):
                        text = _read(dirpath, name)
                        if "reader-fixes" in text or "FIXES_PATH" in text or "fixes_path(" in text:
                            named.append(os.path.relpath(os.path.join(dirpath, name), ROOT).replace(os.sep, "/"))
        # the reader (thanks.py), the build that reads it through thanks.py, page.py.s and serve.py.s docstrings,
        # and the writer
        self.assertEqual(sorted(named), ["ordpar/build_site.py", "ordpar/sitegen/page.py",
                                         "ordpar/sitegen/thanks.py", "scripts/reports_page.py",
                                         "scripts/serve.py"])        # the router, in its docstring
        for rel in named:
            if rel != "scripts/reports_page.py":
                text = _read(ROOT, rel)
                self.assertNotIn("write_fixes", text, rel)
                self.assertNotRegex(text[text.find("reader-fixes") - 300:text.find("reader-fixes") + 300],
                                    r"open\([^)]*[\"']w", rel)
        self.assertNotRegex(_read(ORDPAR, "sitegen", "thanks.py"), r"open\([^)]*[\"'][wa]")
        self.assertIn("thanks_mod.read_fixes()", _read(ORDPAR, "build_site.py"))
        # reports_page writes it in one place, called by the two ways that change it
        src = _read(ROOT, "scripts", "reports_page.py")
        self.assertEqual(src.count("def write_fixes("), 1)
        callers = [chunk.split("(", 1)[0] for chunk in src.split("\ndef ")[1:]
                   if "write_fixes(" in chunk and not chunk.startswith("write_fixes(")]
        self.assertEqual(sorted(callers), ["mark_fixed", "remove_fix", "unname"])

    def test_plan_fixed(self):
        day = "2026-11-08"
        fixes = [_fix(1, "2026-11-05", 1000, [4], ["Kari"])]
        # join fix 1, publish a name: the report and the name added, nothing else
        new, touched = reports_page.plan_fixed(fixes, 7, 1000, [{"fix": 1}], "  Ola ", True, day)
        self.assertEqual((new, touched), ([_fix(1, "2026-11-05", 1000, [4, 7], ["Kari", "Ola"])], [1]))
        self.assertEqual(fixes, [_fix(1, "2026-11-05", 1000, [4], ["Kari"])])     # the input untouched
        # a new fix of the article and one of another, no name published: two new lines, "a reader"
        new, touched = reports_page.plan_fixed(fixes, 8, 1000, [{"article": 1000}, {"article": 98}],
                                               "Per", False, day)
        self.assertEqual(new[1:], [_fix(2, day, 1000, [8]), _fix(3, day, 98, [8])])
        self.assertEqual(touched, [2, 3])
        # pressed again (the receiver had not answered): nothing added twice
        again, touched = reports_page.plan_fixed(new, 8, 1000, [{"article": 1000}, {"article": 98}],
                                                 "Per", False, day)
        self.assertEqual((again, touched), (new, [2, 3]))
        # refused
        for targets, name, publish in (([], None, False), ([{"fix": 9}], None, False),
                                       ([{"fix": 3}], None, False),               # fix 3 is article 98's
                                       ([{"article": 0}], None, False),
                                       ([{"article": 1000}], "", True),
                                       ([{"article": 1000}], "https://x.y", True)):
            with self.assertRaises(ValueError, msg=(targets, name)):
                reports_page.plan_fixed(new, 9, 1000, targets, name, publish, day)


class InTheSite(unittest.TestCase):

    def test_the_page(self):
        html = page.thanks_page("ordpar build: test", page.EN, [_fix(1, "2026-11-05", 1000, [4])], WORDS.get)
        self.assertIn('<link rel="canonical" href="https://ordpar.no/thanks/">', html)
        self.assertNotIn("noindex", html)
        self.assertIn("<h1>Thanks to our readers</h1>", html)
        self.assertIn("Thanks to 1 report that led to 1 fix.", html)
        self.assertEqual(chrome.THANKS_HREF, thanks.HREF)
        self.assertEqual(thanks.HREF, "/thanks/")
        self.assertNotIn(chrome.THANKS_HREF, chrome.footer(page.chrome_strings(page.EN)))   # not in the footer

    def test_built_indexed_offline_and_linked(self):
        # Since the reports' switch (166, 2026-11-05: `chrome.REPORT_RECEIVER`): all of this only
        # while reports are on; off, none of it (`test_ordpar_reportswitch166.py`)
        src = _read(ORDPAR, "build_site.py")
        self.assertIn('os.path.join(out, "thanks", "index.html")', src)
        self.assertIn("page_mod.thanks_page(stamp, EN, thanks_mod.read_fixes() if fixes is None else fixes,", src)
        self.assertIn("thanks_mod.mirror_headword(mirror)", src)
        before = chrome.REPORT_RECEIVER
        page.set_report_receiver("https://ordpar-receiver.ordpar.workers.dev/report")
        try:
            self.assertIn("/thanks/", build_site.indexed_other())
            _title, body = about.page(about.SAMPLE)
            readme = about.readme(about.SAMPLE)
        finally:
            page.set_report_receiver(before)
        with tempfile.TemporaryDirectory() as out:
            os.makedirs(os.path.join(out, "thanks"))
            open(os.path.join(out, "thanks", "index.html"), "w").close()
            self.assertIn("/thanks/", wordpages.indexed_other(out))
        self.assertEqual(build_offline.OPTIONAL_PAGES["/thanks/"], "thanks/index.html")
        text = _read(ORDPAR, "about.md")
        sect = text[text.index("## Thanks"):text.index("## Not affiliated")]
        self.assertIn("[Thanks to our readers](https://ordpar.no/thanks/)", sect)
        self.assertIn('<a href="https://ordpar.no/thanks/">Thanks to our readers</a>', body)
        self.assertIn("(https://ordpar.no/thanks/)", readme)

    def test_the_mirror_headword(self):
        class M:
            def data(self, aid):
                return {1: {"lemmas": [{"lemma": "lysing", "hgno": 1}, {"lemma": "lysning", "hgno": 2}]},
                        2: {"lemmas": [{"lemma": "[få|ha] fram", "hgno": 0}]}}.get(aid)
        h = thanks.mirror_headword(M())
        self.assertEqual((h(1), h(2), h(3)), ("lysing I, lysning II", "få/ha fram", None))


class _Elsewhere(ThreadingHTTPServer):
    """A server that sees every request as coming from another computer on the network."""
    ADDRESS = "192.168.1.20"

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, (self.ADDRESS, client_address[1]), self)


@unittest.skipUnless(HAVE_SERVE, NO_SERVE)
class ThisComputerOnly(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import serve
        cls.serve = serve
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old = os.environ.get("ORDPAR_REPORTS_FILE")
        # an access file that does not exist: the page must not reach any receiver from here
        os.environ["ORDPAR_REPORTS_FILE"] = os.path.join(cls.tmp.name, "none.json")

    @classmethod
    def tearDownClass(cls):
        if cls.old is None:
            os.environ.pop("ORDPAR_REPORTS_FILE", None)
        else:
            os.environ["ORDPAR_REPORTS_FILE"] = cls.old
        cls.tmp.cleanup()

    def _with(self, server_class, fn):
        httpd = server_class(("127.0.0.1", 0), self.serve.Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            return fn("http://127.0.0.1:%d" % httpd.server_address[1])
        finally:
            httpd.shutdown()
            httpd.server_close()

    @staticmethod
    def _status(url, method="GET", body=None):
        req = urllib.request.Request(url, method=method, data=body,
                                     headers={"Content-Type": "application/json"} if body else {})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status
        except urllib.error.HTTPError as exc:
            exc.close()
            return exc.code

    def test_the_rule(self):
        self.assertTrue(all(self.serve.is_local(a) for a in ("127.0.0.1", "::1", "::ffff:127.0.0.1")))
        self.assertFalse(any(self.serve.is_local(a) for a in ("192.168.1.20", "10.0.0.2", "", "127.0.0.2x")))
        for p in ("/reports", "/reports/", "/reports/data.json", "/reports/done", "/reports/fixed",
                  "/reports/unname", "/reports/remove", "/reports/anything"):
            self.assertTrue(self.serve.local_only(p), p)
        for p in ("/", "/triage", "/order/data.json", "/reportsx", "/preview.html"):
            self.assertFalse(self.serve.local_only(p), p)

    def test_403_from_another_address(self):
        body = json.dumps({"id": 1}).encode("utf-8")

        def run(base):
            got = {p: self._status(base + p) for p in ("/reports", "/reports/", "/reports/data.json")}
            got["HEAD /reports"] = self._status(base + "/reports", "HEAD")
            for p in ("/reports/done", "/reports/fixed", "/reports/unname", "/reports/remove"):
                got["POST " + p] = self._status(base + p, "POST", body)
            got["/.cache/ordpar-reports.json"] = self._status(base + "/.cache/ordpar-reports.json")
            got["the rest"] = self._status(base + "/ordpar/about.md")
            return got
        # the access file the server guards is the one the page reads (here the default's place)
        os.environ.pop("ORDPAR_REPORTS_FILE", None)
        try:
            got = self._with(_Elsewhere, run)
        finally:
            os.environ["ORDPAR_REPORTS_FILE"] = os.path.join(self.tmp.name, "none.json")
        rest = got.pop("the rest")
        self.assertEqual(set(got.values()), {403}, got)
        self.assertEqual(rest, 200)                           # the rest of the server stays LAN-wide

    def test_this_computer_gets_the_page(self):
        def run(base):
            with urllib.request.urlopen(base + "/reports", timeout=10) as res:
                return res.status, res.read().decode("utf-8")
        status, html = self._with(ThreadingHTTPServer, run)
        self.assertEqual(status, 200)
        self.assertIn("Reports from readers", html)
        self.assertIn("Fixed", html)


@unittest.skipUnless(reports_page, NO_READER)
class RemoveAFix(unittest.TestCase):
    """Site decisions 169 (b), Robin 2026-11-06 ("I tried the fixed one, but I can't remove it
    again"): a fix written by mistake is taken off the list from the page — ``remove_fix`` through
    ``POST /reports/remove`` and a "Remove" beside each fix. The other fixes stay as they were; the
    reports behind it stay closed on the receiver (nothing is sent to it)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "fixes.jsonl")
        self.old = {k: os.environ.get(k) for k in ("ORDPAR_FIXES_FILE", "ORDPAR_REPORTS_FILE")}
        os.environ["ORDPAR_FIXES_FILE"] = self.path
        # no access file: removing must not need the receiver
        os.environ["ORDPAR_REPORTS_FILE"] = os.path.join(self.tmp.name, "none.json")
        reports_page.write_fixes([_fix(1, "2026-11-05", 1000, [4], ["Kari"]),
                                  _fix(2, "2026-11-06", 98, [7, 9])])

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_remove_one_fix(self):
        msg, ok = reports_page.remove_fix({"fix": 1})
        self.assertTrue(ok, msg)
        self.assertIn("fix 1 removed", msg)
        self.assertIn("/thanks/", msg)
        self.assertEqual(thanks.read_fixes(self.path), [_fix(2, "2026-11-06", 98, [7, 9])])

    def test_refused_leaves_the_list(self):
        before = _read(self.path)
        for bad in ({"fix": 3}, {"fix": "1"}, {"fix": True}, {}, {"fix": None}):
            msg, ok = reports_page.remove_fix(bad)
            self.assertFalse(ok, (bad, msg))
        self.assertEqual(_read(self.path), before)

    def test_the_last_fix_leaves_an_empty_file(self):
        reports_page.remove_fix({"fix": 1})
        self.assertTrue(reports_page.remove_fix({"fix": 2})[1])
        self.assertEqual(_read(self.path), "")
        self.assertEqual(thanks.read_fixes(self.path), [])

    def test_the_page_has_the_button(self):
        html = reports_page.page_html()
        self.assertIn("'/reports/remove'", html)
        self.assertIn("'Remove'", html)
        self.assertIn("confirm('Remove fix '", html)          # never without asking

    def test_through_serve(self):
        import serve
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/reports/remove" % httpd.server_address[1], method="POST",
                data=json.dumps({"fix": 2}).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as res:
                out = json.loads(res.read().decode("utf-8"))
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertTrue(out["ok"], out)
        self.assertEqual([f["fix"] for f in thanks.read_fixes(self.path)], [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
