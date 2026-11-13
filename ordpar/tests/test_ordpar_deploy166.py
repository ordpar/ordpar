"""Pins `deploy.py prepare`'s guard on the reports' receiver (site decisions 166, 2026-11-05): a look
build — the site built with `ORDPAR_REPORT_RECEIVER` pointing at the receiver's local stand-in on
the local network, for a look on :8098 — can never be published by mistake. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-report-switch-166-2026-11-05.md`.

* **Refused**, before the change lists, the gate and the clone, saying why: a build whose reports
  address — `out/build.json` `reports_166.receiver`, or the address written into the shipped
  `site/report.js`, `site/ordpar.js` or `site/shell-pages.js` — is not `https://` on a public host
  name: `http://`, an IP address (the home network's 192.168.…, this computer's 127.0.0.1, ::1),
  localhost, a local name (`.local`, `.lan`, `.home.arpa` …), a name without a dot; and a build
  whose record and shipped scripts name different addresses.
* **Refused** too (the privacy build, 2026-11-05): reports on with the Worker's https address but
  no `/privacy/` page, or a `/privacy/` without its section on reports
  (`id="reporting-a-mistake"`), which the report form links.
* **Passed**: reports off (empty everywhere, or no record at all — every build before 166's switch
  and the scratch builds of the other deploy tests), and reports on with the Worker's https address
  and the privacy page with its section (amended 2026-11-05: the page written in).
* **The README** (`readme_text`) says what the published build's pages say: its paragraph on
  reports (`about.md` `[if reports]`) only when that build had reports on (`reports_166`).

On the scratch clone, bare repository and change lists of `test_ordpar_deploy103.py` — never the
real clone, never the network. Shown to fail on 61ca860b4's `deploy.py` (a `git archive` export with
this file copied in). Stdlib unittest; needs git.
"""

import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ordpar_deploy103 as t103  # noqa: E402  (the scratch clone, repository and site)

deploy = t103.deploy
LOOK = "http://192.168.0.100:8787/report"
LIVE = "https://ordpar-receiver.ordpar.workers.dev/report"
#: the shipped scripts that carry the switch (`deploy.REPORT_SCRIPTS`; here too, so the file runs on the code before it)
SCRIPTS = ("site/report.js", "site/ordpar.js", "site/shell-pages.js")
THANKS_LINE = "Thank you to the readers who tell us about mistakes"


class Base(t103.Scratch):

    def record(self, receiver, source="chrome.REPORT_RECEIVER"):
        """The build's record of its reports' switch, as `build_site.py` writes it."""
        bj = os.path.join(self.out, "build.json")
        with io.open(bj, encoding="utf-8") as fh:
            b = json.load(fh)
        b["reports_166"] = {"receiver": receiver, "source": source,
                            "thanks": "written" if receiver else "absent"}
        with io.open(bj, "w", encoding="utf-8") as fh:
            json.dump(b, fh)

    def ship(self, receiver, files=SCRIPTS):
        """The shipped scripts with the switch written in, minified as the build ships them."""
        for rel in files:
            t103.write(os.path.join(self.out, rel),
                       "(function(g){'use strict';var REPORT_RECEIVER=%s;var MAX_TEXT=2000;})(this);\n"
                       % json.dumps(receiver))

    def privacy(self, section=True):
        """The privacy page as the build writes it, with or without its section on reports."""
        t103.write(os.path.join(self.out, "privacy", "index.html"),
                   "<!doctype html><h1>Privacy</h1>%s\n"
                   % ('<h2 id="reporting-a-mistake">Reporting a mistake</h2>' if section else ""))

    def assertGuarded(self, r, *why):
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("refused: this build's reports receiver cannot be published", r.stderr)
        for w in why:
            self.assertIn(w, r.stderr)
        self.assertIn("rebuild without it", r.stderr)
        self.assertNotIn("gate:", r.stdout)                                  # before the gate
        self.assertEqual(self.git("rev-parse", "--verify", "-q", "HEAD"), "")  # no snapshot
        self.assertFalse(os.path.exists(os.path.join(self.clone, "index.html")))


class Refused(Base):

    def test_a_look_build(self):
        self.record(LOOK, "ORDPAR_REPORT_RECEIVER")
        self.ship(LOOK)
        r = self.run_deploy("prepare")
        self.assertGuarded(r, LOOK + " is not https", "ORDPAR_REPORT_RECEIVER",
                           "out/site/report.js", "out/site/ordpar.js", "out/site/shell-pages.js")

    def test_a_shipped_script_alone(self):
        # no record in build.json (a build.json from elsewhere): the shipped bundle still tells
        self.ship("https://127.0.0.1:8787/report", ("site/ordpar.js",))
        r = self.run_deploy("prepare")
        self.assertGuarded(r, "out/site/ordpar.js", "is an IP address")

    def test_record_and_scripts_disagree(self):
        self.record("")
        self.ship(LIVE)
        r = self.run_deploy("prepare")
        self.assertGuarded(r, "the build names different addresses")

    def test_reports_on_without_the_privacy_page(self):
        # the privacy build (2026-11-05): the form links /privacy/#reporting-a-mistake
        self.record(LIVE)
        self.ship(LIVE)
        r = self.run_deploy("prepare")
        self.assertGuarded(r, "reports are on but the build has no /privacy/ page")

    def test_reports_on_with_a_privacy_page_without_its_section(self):
        self.record(LIVE)
        self.ship(LIVE)
        self.privacy(section=False)
        r = self.run_deploy("prepare")
        self.assertGuarded(r, "/privacy/ has no section on reports")


class Passed(Base):

    def test_reports_off(self):
        self.record("")
        self.ship("")
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(THANKS_LINE, self.show("HEAD", "README.md"))

    def test_no_record_at_all(self):
        r = self.run_deploy("prepare")                     # t103's scratch site: no report.js, no record
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_reports_on_with_the_workers_https_address(self):
        self.record(LIVE)
        self.ship(LIVE)
        self.privacy()                    # amended 2026-11-05: reports need the page (the guard)
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        readme = self.show("HEAD", "README.md")
        self.assertIn(THANKS_LINE, readme)
        self.assertIn("(https://ordpar.no/thanks/)", readme)


class Address(unittest.TestCase):

    def test_the_scripts_read(self):
        self.assertEqual(tuple(deploy.REPORT_SCRIPTS), SCRIPTS)

    def test_what_may_be_published(self):
        for ok in ("", None, LIVE, "https://reports.ordpar.no/report"):
            self.assertIsNone(deploy.report_address_problem(ok), ok)
        for bad, why in ((LOOK, "not https"),
                         ("http://127.0.0.1:8787/report", "not https"),
                         ("http://ordpar-receiver.ordpar.workers.dev/report", "not https"),
                         ("https://192.168.0.100:8787/report", "IP address"),
                         ("https://10.0.0.2/report", "IP address"),
                         ("https://127.0.0.1/report", "IP address"),
                         ("https://[::1]/report", "IP address"),
                         ("https://8.8.8.8/report", "IP address"),
                         ("https://localhost:8787/report", "local name"),
                         ("https://robin-pc.local/report", "local name"),
                         ("https://router.lan/report", "local name"),
                         ("https://box.home.arpa/report", "local name"),
                         ("https://intranet/report", "local name"),
                         ("ftp://ordpar.no/report", "not https")):
            with self.subTest(address=bad):
                self.assertIn(why, deploy.report_address_problem(bad) or "")


if __name__ == "__main__":
    unittest.main()
