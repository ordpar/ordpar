# -*- coding: utf-8 -*-
"""Site decisions 166, the reports' ONE switch (2026-11-05): until reports go live, the site says
nothing about them that is not yet true (standing.md, "state only true things"). Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-report-switch-166-2026-11-05.md`.

* **One place**: `sitegen/chrome.py` `REPORT_RECEIVER` — empty as committed until 2026-11-05; since
  166's go-live that day the live receiver's https `/report` address, which `deploy.py prepare`'s
  check accepts (`OnePlace.test_the_committed_switch_the_live_receiver`, amended from
  `test_the_default_stays_off`).
  The build writes it into `report.js`'s one line `var REPORT_RECEIVER = '';` (`page.REPORT_SLOT`,
  `page.report_js`), so the shipped `report.js` and both bundles (`ordpar.js`, `shell-pages.js`)
  carry it; an address typed into `report.js` itself fails the build. Its form: empty, or an http(s)
  address ending in `/report` (`chrome.check_report_receiver`).
* **The build-time override**: `ORDPAR_REPORT_RECEIVER`, read by `build_site.py` for one build
  (`report_receiver_override`), checked the same way; unset or empty, the committed switch decides.
  `build_site.py` sets it before anything renders and records it in `build.json` (`reports_166`).
* **Off** (the default): no `/thanks/` (`build_site.write_thanks` writes none and removes one an
  earlier build left), not in the sitemap (`build_site.indexed_other()`; the index build's
  `wordpages.indexed_other(out)`, from the page's presence), not among the offline copy's required
  shell pages (`build_offline.OPTIONAL_PAGES`, so its absence is no warning), and no paragraph on
  reports in the About page or the README (`about.md` `[if reports]`).
* **On**: all of them there.
* **The privacy page** obeys `[if reports]` (`about.privacy_page`), so its section "Reporting a
  mistake" follows this switch; the page itself is `chrome.PRIVACY` (decisions 104), on since
  2026-11-05 (its words approved; it pinned the page off until then).
  Amended by the privacy build of 2026-11-05: until then this pinned the page as having
  no `[if]` mechanism, so that the change would be a deliberate one; the page's cases are
  `test_ordpar_privacy166.py`'s.
* **The receiver's stand-in on the local network** (`receiver/tools/local.mjs --lan`, for a
  look on :8098 from this computer and a phone): a report from `http://127.0.0.1:8098` or
  `http://192.168.0.100:8098` is taken and answered with that origin, any other origin refused
  (400); without `--lan` neither LAN origin is taken; `--stay` keeps it running once its standard
  input closes. Bound to 127.0.0.1 here (`--host`), so the test never opens a port to the network.
  Skipped without bun.

Fails on 61ca860b4's code (no switch: `/thanks/` and the About paragraph always built). Stdlib
unittest, no network.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
sys.path.insert(0, ROOT)
from ordpar.sitegen import chrome, page, about, wordpages  # noqa: E402
from ordpar import build_site, build_offline  # noqa: E402

LOOK = "http://192.168.0.100:8787/report"
THANKS_LINE = "Thank you to the readers who tell us about mistakes"
RECEIVER = os.path.join(ORDPAR, "receiver")
BUN = shutil.which("bun")


def _read(*p):
    with io.open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


@contextlib.contextmanager
def reports(address):
    """The switch set for the block, as `build_site.py` sets it, and put back after."""
    before = getattr(chrome, "REPORT_RECEIVER", "")
    setter = getattr(page, "set_report_receiver", None)
    if setter:
        setter(address)
    else:                                   # the code before the switch: nothing reads it
        chrome.REPORT_RECEIVER = address
    try:
        yield
    finally:
        if setter:
            setter(before)
        else:
            chrome.REPORT_RECEIVER = before


class OnePlace(unittest.TestCase):

    def test_the_committed_switch_the_live_receiver(self):
        # amended 2026-11-05 (166's go-live; was `test_the_default_stays_off`, which pinned it empty):
        # the one place holds the live receiver's address, set as a literal on its own line, which
        # the switch's form and deploy.py prepare's check both accept
        live = "https://ordpar-receiver.ordpar.workers.dev/report"
        self.assertEqual(chrome.REPORT_RECEIVER, live)
        self.assertIn('\nREPORT_RECEIVER = "%s"\n' % live, _read(ORDPAR, "sitegen", "chrome.py"))
        self.assertEqual(chrome.check_report_receiver(chrome.REPORT_RECEIVER), live)
        from ordpar import deploy
        self.assertIsNone(deploy.report_address_problem(chrome.REPORT_RECEIVER))

    def test_report_js_carries_the_slot_only(self):
        src = _read(ORDPAR, "site", "report.js")
        self.assertEqual(page.REPORT_SLOT, "var REPORT_RECEIVER = '';")
        self.assertEqual(src.count(page.REPORT_SLOT), 1)
        self.assertEqual(src.count("var REPORT_RECEIVER"), 1)

    def test_off_shipped_empty(self):
        with reports(""):
            for url in (page.REPORT_JS_HREF, page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF):
                self.assertIn(page.REPORT_SLOT, page.shipped(url), url)

    def test_on_written_into_report_js_and_both_bundles(self):
        with reports(LOOK):
            for url in (page.REPORT_JS_HREF, page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF):
                text = page.shipped(url)
                self.assertIn('var REPORT_RECEIVER = "%s";' % LOOK, text, url)
                self.assertNotIn(page.REPORT_SLOT, text, url)
            hashes = {u: page.asset(u) for u in (page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF)}
        for u, h in hashes.items():                         # the ?v= follows the switch
            self.assertNotEqual(page.asset(u), h, u)

    def test_an_address_in_report_js_itself_fails_the_build(self):
        src = _read(ORDPAR, "site", "report.js").replace(page.REPORT_SLOT, "var REPORT_RECEIVER = 'x';")
        with self.assertRaises(ValueError):
            page.report_js(src)

    def test_its_form(self):
        for ok in ("", LOOK, "https://ordpar-receiver.ordpar.workers.dev/report", "http://127.0.0.1:8787/report"):
            self.assertEqual(chrome.check_report_receiver(ok), ok)
        for bad in ("ftp://x.no/report", "https://x.no/", "https://x.no/reports", "x.no/report",
                    "https://x.no/report'", 'https://x.no/"report', "javascript:alert(1)//report",
                    "https://x.no/report?a=1"):
            with self.assertRaises(ValueError, msg=bad):
                chrome.check_report_receiver(bad)


class Override(unittest.TestCase):

    def test_read_from_the_environment(self):
        env = build_site.REPORT_RECEIVER_ENV
        self.assertEqual(env, "ORDPAR_REPORT_RECEIVER")
        self.assertIsNone(build_site.report_receiver_override({}))
        self.assertIsNone(build_site.report_receiver_override({env: ""}))
        self.assertIsNone(build_site.report_receiver_override({env: "  "}))
        self.assertEqual(build_site.report_receiver_override({env: LOOK}), LOOK)
        with self.assertRaises(ValueError):
            build_site.report_receiver_override({env: "http://192.168.0.100:8787/"})

    def test_set_before_anything_renders_and_recorded(self):
        src = _read(ORDPAR, "build_site.py")
        main = src[src.index("    a = ap.parse_args()"):]
        self.assertLess(main.index("page_mod.set_report_receiver("), main.index("deck.store.read_jsonl"))
        self.assertIn('"reports_166": {"receiver": chrome_mod.REPORT_RECEIVER', src)
        self.assertIn("thanks_state = write_thanks(a.out, stamp, mirror)", src)


class _Mirror:
    def data(self, aid):
        return {1000: {"lemmas": [{"lemma": "lek", "hgno": 3}]}}.get(aid)


class ThanksPage(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="ordpar-switch166-")
        self.path = os.path.join(self.out, "thanks", "index.html")

    def tearDown(self):
        shutil.rmtree(self.out)

    def test_off_not_built_and_an_earlier_one_removed(self):
        with reports(""):
            self.assertEqual(build_site.write_thanks(self.out, "ordpar build: test", _Mirror(), []), "absent")
            self.assertFalse(os.path.exists(self.path))
            os.makedirs(os.path.dirname(self.path))
            with open(self.path, "w") as f:
                f.write("<p>an earlier build's</p>")
            self.assertEqual(build_site.write_thanks(self.out, "ordpar build: test", _Mirror(), []), "removed")
            self.assertFalse(os.path.exists(self.path))

    def test_on_built(self):
        fixes = [{"fix": 1, "date": "2026-11-05", "article": 1000, "reports": [4], "names": []}]
        with reports(LOOK):
            self.assertEqual(build_site.write_thanks(self.out, "ordpar build: test", _Mirror(), fixes), "written")
        html = _read(self.path)
        self.assertIn("<h1>Thanks to our readers</h1>", html)
        self.assertIn("Thanks to 1 report that led to 1 fix.", html)

    def test_the_sitemap(self):
        self.assertNotIn("/thanks/", build_site.INDEXED_OTHER)
        self.assertNotIn("/thanks/", wordpages.INDEXED_OTHER)
        with reports(""):
            self.assertNotIn("/thanks/", build_site.indexed_other())
        with reports(LOOK):
            self.assertEqual(build_site.indexed_other()[-1], "/thanks/")
        # the index build (a process of its own) lists it where the article build wrote it
        self.assertEqual(wordpages.indexed_other(self.out), wordpages.INDEXED_OTHER)
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("<p>thanks</p>")
        self.assertEqual(wordpages.indexed_other(self.out), wordpages.INDEXED_OTHER + ("/thanks/",))
        self.assertIn("W.indexed_other(out)", _read(ORDPAR, "build_index.py"))
        self.assertNotIn("W.INDEXED_OTHER", _read(ORDPAR, "build_index.py"))

    def test_the_offline_copy(self):
        self.assertNotIn("/thanks/", build_offline.SHELL_PAGES)
        self.assertEqual(build_offline.OPTIONAL_PAGES["/thanks/"], "thanks/index.html")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            files = build_offline.other_files(self.out)
        self.assertNotIn("/thanks/", buf.getvalue())         # its absence is no warning
        self.assertNotIn("/thanks/", files)
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("<p>thanks</p>")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIn("/thanks/", build_offline.other_files(self.out))


class AboutAndReadme(unittest.TestCase):

    def test_the_source(self):
        text = _read(ORDPAR, "about.md")
        sect = text[text.index("## Thanks"):text.index("## Not affiliated")]
        self.assertIn("[if reports]" + THANKS_LINE, sect)
        self.assertIn("have led to and the ideas we have taken up or plan to.\n\n[/if]", sect)  # 183

    def test_off(self):
        with reports(""):
            _t, body = about.page(about.SAMPLE)
            md = about.readme(about.SAMPLE)
        for text in (body, md):
            self.assertNotIn(THANKS_LINE, text)
            self.assertNotIn("/thanks/", text)
            self.assertNotIn("[if", text)
        self.assertIn("## Not affiliated", md)

    def test_on(self):
        with reports(LOOK):
            _t, body = about.page(about.SAMPLE)
            md = about.readme(about.SAMPLE)
        self.assertIn('<a href="https://ordpar.no/thanks/">Thanks to our readers</a>', body)
        self.assertIn(THANKS_LINE, md)
        self.assertIn("(https://ordpar.no/thanks/)", md)

    def test_the_readme_follows_the_published_build(self):
        # deploy.py passes the build's own record (`reports_166`), whatever the switch says now
        with reports(""):
            self.assertIn(THANKS_LINE, about.readme(about.SAMPLE, reports=True))
        with reports(LOOK):
            self.assertNotIn(THANKS_LINE, about.readme(about.SAMPLE, reports=False))


class PrivacyPage(unittest.TestCase):

    def test_the_if_mechanism_there(self):
        # amended 2026-11-05 (the privacy build): privacy.md's [if reports] is obeyed — it pinned
        # the opposite until then ("rendered as it stands"), so that a change would be deliberate
        for on in (False, True):
            _t, body = about.privacy_page(source="# P\n\n[if reports]A.[/if]\n", draft=True,
                                          counting=False, reports=on)
            self.assertNotIn("[if", body)
            self.assertEqual("<p>A.</p>" in body, on)
        self.assertIn("[if reports]## Reporting a mistake", _read(ORDPAR, "privacy.md"))
        # the page on since 2026-11-05 (approved; it pinned PRIVACY off until
        # then), with its section on reports, as the committed switches make it
        self.assertIs(chrome.PRIVACY, True)
        self.assertIn('id="reporting-a-mistake"', about.privacy_page()[1])


def _post(url, origin, method="POST"):
    req = urllib.request.Request(url, method=method, headers={"Origin": origin, "Content-Type": "text/plain"},
                                 data=(b'{"id":1000,"text":"A look.","category":null,"reply":null,"build":null}'
                                       if method == "POST" else None))
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.headers.get("Access-Control-Allow-Origin")
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.headers.get("Access-Control-Allow-Origin")


@unittest.skipUnless(BUN, "bun is not on PATH")
class StandInOnTheHomeNetwork(unittest.TestCase):

    def start(self, *extra):
        proc = subprocess.Popen([BUN, "tools/local.mjs", "--port", "0"] + list(extra), cwd=RECEIVER,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.addCleanup(self.stop, proc)
        line = proc.stdout.readline().decode("utf-8", "replace").strip()
        self.assertTrue(line.startswith("listening http://127.0.0.1:"), line)
        return proc, "http://127.0.0.1:" + line.rsplit(":", 1)[1]

    @staticmethod
    def stop(proc):
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        for s in (proc.stdin, proc.stdout):
            try:
                s.close()
            except Exception:
                pass

    def test_lan_takes_the_two_look_origins_only(self):
        _p, url = self.start("--lan", "--host", "127.0.0.1")
        for origin in ("http://127.0.0.1:8098", "http://192.168.0.100:8098"):
            self.assertEqual(_post(url + "/report", origin), (204, origin), origin)
            self.assertEqual(_post(url + "/report", origin, "OPTIONS"), (204, origin), origin)
        for origin in ("http://127.0.0.1:1", "http://192.168.0.100:8099", "https://ordpar.no",
                       "http://localhost:8098"):
            self.assertEqual(_post(url + "/report", origin)[0], 400, origin)
        req = urllib.request.Request(url + "/reports", headers={"Authorization": "Bearer local-reports-token-0000"})
        with urllib.request.urlopen(req, timeout=10) as res:          # this computer: allowed
            self.assertIn(b'"text":"A look."', res.read())

    def test_without_lan_neither_look_origin_is_taken(self):
        _p, url = self.start()
        self.assertEqual(_post(url + "/report", "http://192.168.0.100:8098")[0], 400)
        self.assertEqual(_post(url + "/report", "http://127.0.0.1:1")[0], 204)

    def test_stay_outlives_its_standard_input(self):
        proc, url = self.start("--stay")
        proc.stdin.close()
        time.sleep(1.5)
        self.assertIsNone(proc.poll())
        self.assertEqual(_post(url + "/report", "http://127.0.0.1:1")[0], 204)
        plain, _u = self.start()
        plain.stdin.close()
        plain.wait(timeout=10)                                        # without it, it stops


class TheLookBuildsCommands(unittest.TestCase):

    def test_the_readme_gives_them(self):
        text = _read(RECEIVER, "README.md")
        # the public README's section on the stand-in, trying the form before a deploy (the
        # private look build from a phone, with its addresses, is in README-rationale.md)
        sect = text[text.index("## The local stand-in"):text.index("## Deploying, with the counting off")]
        for want in ("bun tools/local.mjs --port 8787",
                     "ORDPAR_REPORT_RECEIVER=http://127.0.0.1:8787/report",
                     "python ordpar/build_site.py",
                     "python -m http.server 8098 --directory ordpar/out",
                     "--lan", "LAN_ORIGINS",
                     "build again without `ORDPAR_REPORT_RECEIVER`"):
            self.assertIn(want, sect)


if __name__ == "__main__":
    unittest.main()
