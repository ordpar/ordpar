"""Site decisions 166 (Robin, 2026-11-05): "Report a mistake" at an article's foot, in a browser
(headless Edge, `browser/report166.js`), sending to the receiver's own code run locally. Since the
follow-up of the same day: Robin's pick in the lab ("Suggest a correction", the drop-down, the
confirmation under the row), the name to credit, the receiver's total cap per hour, and the phone
row.

The receiver is `ordpar/receiver/tools/local.mjs` — the Worker's `handle` under bun, D1 stood in for
by bun:sqlite — started here on a free port; what arrived is read back through its `GET /reports`
with the token, as Robin's page reads it. The page's switch (`report.js` `REPORT_RECEIVER`) is
empty as built, so the check reads the page as built first (no button), then sets the stand-in's
address before the page's scripts run.

* **As built**: the button exactly when the build wrote an address into `REPORT_RECEIVER` —
  none while it is empty (as committed until 2026-11-05), shown after Copy link since 166's go-live
  (the live receiver's address; amended that day, it pinned the switch empty until then).
* **An article page** (`/bm-en/1000/`): the button after Copy link and Share; opened by Enter, the
  form under the foot's row, `aria-expanded`, focus in the text box (4 lines); the labels (the text,
  its 2,000-character hint, "Where is the mistake? (optional)" over a drop-down of "Choose …" and
  the four categories, the optional address and its hint, the name to credit, 60 characters, and
  its hint), the trap out of sight and out of the tab order, Send and Cancel; their names in the
  accessibility tree. Send with nothing written: the status says so, nothing is sent. Escape
  closes, focus back on the button. A link as the name to credit: the status says so, nothing
  sent. A report sent: "Thank you, your report has been sent." under the row (a status), the form
  closed, focus back. A dead address: "could not be sent", the text kept, the form open. Offline:
  the form says it needs a connection, nothing is sent, the text kept, the note shown again on
  reopening; online again, the same text sent.
* **A word page** (`/bm-en/norge/`, its one article shown whole by `lookup.js`): the button in the
  result's row after Copy link, a report sent; then the receiver filled to its total cap for the
  hour from the test itself (any sender), and one more from the page: the cap's message, which
  does not blame the reader, the text kept.
* **Under "Norwegian only"** with the labels in Norwegian: the button and the form stay English (152).
* **What arrived**: exactly the reports sent, with the article's id, the build the site is on (or
  none), the category, the text, the address and the name to credit (cleaned); each request a POST
  of exactly the six fields, no Referer and no Cookie header.
* **The phone row** (Robin, 2026-11-05, as ordbokene): at 320, 360 and 390 px with Share (the
  browser's own, or one put in for the check), Copy link is not shown and Share, "Suggest a
  correction" and the heart sit on one line, on the article page and on the word page's row,
  nothing wider than the screen; without Share, Copy link stays; on a computer's width it stays.
  The word page's row (`lookup.js` `resultControls`) has no "Article page" link, at the three
  widths with Share and without and on a computer (site decisions 168, re-ruled 2026-11-06
  (everywhere); until then hidden on a phone only), and on a phone keeps every item on one line.
  With the form open, the row is still one line and the form's privacy line inside the screen.
* **The form's line on privacy** (the privacy build, 2026-11-05): "How we handle your report is
  explained on our Privacy page.", the link `/privacy/#reporting-a-mistake` in a new tab
  (`noopener`), before Send; where the site served has `/privacy/` (an overlay with the page), that
  page carries the section's id (the Python side, always: `test_ordpar_privacy166.py`).

Needs `ordpar/out/` (or `ORDPAR_TEST_OUT`) with the article page and `/bm-en/norge/`; to test a
scratch render over the full build, `ORDPAR_TEST_OVERLAY`. Skipped without Edge, bun or a build.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ORDPAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIVER = os.path.join(ORDPAR, "receiver")
TOKEN = "browser-test-token-0123456789"
BUTTON = "Suggest a correction"
with open(os.path.join(RECEIVER, "src", "reports.js"), encoding="utf-8") as _f:
    CAP = int(re.search(r"export const REPORTS_PER_HOUR = (\d+);", _f.read()).group(1))
ARTICLE, WORD = 1000, "norge"
SITE = None
STAND_IN = None
R = {}
ARRIVED = []
SKIP = harness.skip_reason() or (None if shutil.which("bun") else "bun is not on PATH")
# Against the live site (`deploy.py verify`, ORDPAR_TEST_BASE=https://ordpar.no) the page's origin is
# ordpar.no, which the local stand-in refuses (it takes only this computer's origins), and the real
# receiver must never get a test report: so the checks that need a send to ARRIVE are skipped there
# (2026-11-05, the first live check after 166 went live: they failed by design; nothing was stored).
# The form, the button, the phone row and what the page sends are still checked live.
_BASE = harness.base_override() or ""
LIVE = None if not _BASE or "127.0.0.1" in _BASE or "localhost" in _BASE else (
    "against %s: the local stand-in takes no report from that origin, and the live receiver gets "
    "no test report" % _BASE)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_stand_in():
    """The receiver's code on a free port: (process, "http://127.0.0.1:<port>")."""
    env = dict(os.environ, REPORTS_TOKEN=TOKEN)
    proc = subprocess.Popen([shutil.which("bun"), "tools/local.mjs", "--port", "0"], cwd=RECEIVER, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    line = proc.stdout.readline().decode("utf-8", "replace").strip()
    if not line.startswith("listening "):
        proc.kill()
        raise RuntimeError("the receiver's stand-in did not start: %r" % line)
    return proc, line.split(" ", 1)[1]


def stop_stand_in(proc):
    try:
        proc.stdin.close()          # local.mjs ends when its standard input closes
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    proc.stdout.close()


def read_reports(url):
    req = urllib.request.Request(url + "/reports", headers={"Authorization": "Bearer " + TOKEN})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))["reports"]


def setUpModule():
    global SITE, STAND_IN
    if SKIP:
        print("test_ordpar_browser_report166: skipped —", SKIP)
        return
    STAND_IN, url = start_stand_in()
    try:
        SITE = harness.Site()
        R.update(SITE.check("report166.js", {"id": ARTICLE, "word": WORD, "receiver": url + "/report",
                                             "dead": "http://127.0.0.1:%d/report" % _free_port()},
                            timeout=300))
        ARRIVED.extend(read_reports(url))
        # the phone row's Share: the browser's own, or put in for the check (report166.js `SHARE_ON`)
        print("test_ordpar_browser_report166: navigator.share in this Edge:", R.get("nativeShare"))
    finally:
        stop_stand_in(STAND_IN)


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Report(unittest.TestCase):

    def test_a_the_button_as_built(self):
        # amended 2026-11-05 (166's go-live; was `test_a_no_button_as_built`, which pinned the switch
        # empty): the button exactly when the build wrote an address, whichever the build is
        api, row = R["built"]["api"], R["built"]["row"] or []
        self.assertIsInstance(api, str)
        self.assertEqual(BUTTON in row, bool(api), (api, row))
        if api:
            self.assertLess(row.index("Copy link"), row.index(BUTTON), row)

    def test_b_the_button_after_copy_link(self):
        for where in ("article", "word"):
            with self.subTest(where=where):
                row = R[where]["row"]
                self.assertIn(BUTTON, row, row)
                self.assertNotIn("Report a mistake", row)
                self.assertLess(row.index("Copy link"), row.index(BUTTON), row)
                if "Share" in row:
                    self.assertLess(row.index("Share"), row.index(BUTTON), row)
        c = R["article"]["closed"]
        self.assertEqual((c["expanded"], c["form"]), ("false", False), c)

    def test_c_the_form_by_keyboard(self):
        s = R["article"]["opened"]
        self.assertTrue(s["open"] and s["afterRow"], s)
        self.assertEqual(s["expanded"], "true")
        self.assertEqual(s["focus"], "text")
        self.assertEqual(s["formLabel"], "Suggest a correction to this article")
        self.assertEqual(s["textLabel"], "What is wrong?")
        self.assertEqual((s["textMax"], s["textRequired"]), (2000, True))
        self.assertEqual(s["textHint"], "Up to 2,000 characters.")
        self.assertEqual(s["whereLabel"], "Where is the mistake? (optional)")
        self.assertEqual(s["choices"], [["", "Choose …"], ["translation", "Translation"], ["audio", "Audio"],
                                        ["norwegian", "Norwegian text"], ["other", "Other"]])
        self.assertEqual(s["radios"], 0)                                   # a drop-down, Robin's pick
        self.assertEqual(s["textRows"], 4)
        self.assertEqual(s["replyLabel"], "Your email address (optional)")
        self.assertIn("delete it once we have dealt with your report", s["replyHint"])
        self.assertEqual((s["creditLabel"], s["creditMax"]), ("Name to credit (optional)", 60))
        self.assertIn("Thanks page", s["creditHint"])
        self.assertEqual(s["trap"], {"tab": -1, "hidden": True, "offscreen": True})
        self.assertEqual(s["buttons"], ["Send", "Cancel"])
        self.assertEqual(s["statusRole"], "status")
        # the privacy build (2026-11-05): the line linking the privacy page's section, before Send
        pv = s["privacy"]
        self.assertTrue(pv, s)
        self.assertEqual(pv["text"], "How we handle your report is explained on our Privacy page.")
        self.assertEqual((pv["link"], pv["href"], pv["target"], pv["rel"]),
                         ("Privacy page", "/privacy/#reporting-a-mistake", "_blank", "noopener"))
        self.assertTrue(pv["shown"] and pv["beforeSend"] and pv["inside"], pv)
        if R["privacyPage"] is not None:                 # the site served has /privacy/
            self.assertTrue(R["privacyPage"], "/privacy/ without id=\"reporting-a-mistake\"")
        self.assertEqual(s["lang"], "en")
        ax = [tuple(x) for x in R["article"]["ax"]]
        for want in (("textbox", "What is wrong?"), ("textbox", "Your email address (optional)"),
                     ("combobox", "Where is the mistake? (optional)"), ("textbox", "Name to credit (optional)"),
                     ("button", "Send"), ("button", "Cancel")):
            self.assertIn(want, ax, ax)

    def test_d_empty_and_escape(self):
        e = R["article"]["empty"]
        self.assertEqual(e["status"], "Please write what is wrong before you send.")
        self.assertEqual(e["focus"], "text")
        self.assertEqual(R["article"]["emptySent"], 0)
        x = R["article"]["escaped"]
        self.assertEqual((x["open"], x["expanded"], x["focus"]), (False, "false", "button"), x)

    def test_d2_a_link_as_the_name(self):
        b = R["article"]["badCredit"]
        self.assertEqual(b["status"], "A name to credit cannot be a link. Write a name or nickname, "
                                      "or leave the field empty.")
        self.assertEqual((b["open"], b["text"]), (True, "LINK: never sent."), b)
        self.assertEqual(R["article"]["badCreditSent"], 0)

    @unittest.skipIf(LIVE, LIVE or "")
    def test_e_sent(self):
        for s in (R["article"]["sent"], R["word"]["sent"], R["article"]["online"]):
            self.assertEqual(s["done"], "Thank you, your report has been sent.", s)
            self.assertEqual(s["doneRole"], "status")
            self.assertTrue(s["doneUnderRow"], s)               # under the row, not in it
            self.assertEqual((s["open"], s["expanded"], s["focus"], s["text"]), (False, "false", "button", ""), s)

    @unittest.skipIf(LIVE, LIVE or "")
    def test_f_failed_keeps_the_text(self):
        f = R["article"]["failed"]
        self.assertEqual(f["status"], "The report could not be sent. Your text is kept here; please try again.")
        self.assertEqual((f["open"], f["text"], f["done"]), (True, "FAILED: kept after a failure.", ""), f)

    @unittest.skipIf(LIVE, LIVE or "")
    def test_g_offline(self):
        a = R["article"]
        self.assertIs(a["offlineOnline"], False)
        o = a["offline"]
        self.assertTrue(o["status"].startswith("You are offline. Sending a report needs a connection"), o)
        self.assertEqual((o["open"], o["text"]), (True, "OFFLINE: sent once back online."), o)
        self.assertEqual(a["offlineSent"], 0)
        self.assertTrue(a["offlineReopened"]["status"].startswith("You are offline."), a["offlineReopened"])
        self.assertEqual(a["offlineReopened"]["text"], "OFFLINE: sent once back online.")

    @unittest.skipIf(LIVE, LIVE or "")
    def test_h_total_cap(self):
        self.assertTrue(R["fillRefused"], R.get("fill"))
        self.assertEqual(R["rate"], ["We have received a great many reports in the last hour. Your text is kept "
                                     "here; please try again in an hour."])
        self.assertEqual(R["rateKept"], "CAP: refused, kept.")
        self.assertTrue(R["rateFailedClass"])

    def test_h2_english_under_norwegian_only(self):
        n = R["nbonly"]
        self.assertTrue(n["layer"], n)
        self.assertIn(BUTTON, n["row"])
        self.assertTrue(n["form"]["open"], n)
        self.assertEqual((n["form"]["textLabel"], n["form"]["buttons"]), ("What is wrong?", ["Send", "Cancel"]))

    @unittest.skipIf(LIVE, LIVE or "")
    def test_i_what_arrived(self):
        texts = [r["text"] for r in ARRIVED]
        fill = [t for t in texts if t.startswith("FILL ")]
        self.assertEqual(sorted(t for t in texts if not t.startswith("FILL ")), sorted([
            "ARTICLE: the audio of the headword says the wrong word.", "OFFLINE: sent once back online.",
            "WORD: sense 1 is mistranslated."]))
        self.assertEqual(len(ARRIVED), CAP)        # the total cap: CAP an hour from everyone together
        self.assertEqual(len(fill), R["fill"])
        by = {r["text"]: r for r in ARRIVED}
        build = R["build"]
        a = by["ARTICLE: the audio of the headword says the wrong word."]
        self.assertEqual({k: a[k] for k in ("article", "build", "category", "reply", "credit")},
                         {"article": ARTICLE, "build": build, "category": "audio", "reply": "reader@example.org",
                          "credit": "Kari N."})
        self.assertEqual(by["OFFLINE: sent once back online."]["category"], "other")
        w = by["WORD: sense 1 is mistranslated."]
        self.assertEqual((w["category"], w["reply"], w["credit"]), ("translation", None, None))
        self.assertIsInstance(w["article"], int)

    def test_j_what_was_sent(self):
        sent = R["sent"]
        posts = [s for s in sent if s["method"] == "POST"]
        self.assertEqual(len(posts), 5, sent)        # 3 stored, the dead one, the one the cap refused
        for s in posts:
            body = json.loads(s["body"])
            self.assertEqual(sorted(body), ["build", "category", "credit", "id", "reply", "text"], s)
            heads = {k.lower(): v for k, v in s["headers"].items()}
            self.assertEqual(heads.get("referer", ""), "", s)        # CDP shows none sent as ""
            self.assertNotIn("cookie", heads, s)
            self.assertEqual(s["referrerPolicy"], "no-referrer")
        self.assertEqual(json.loads(posts[0]["body"])["id"], ARTICLE)

    def test_k_the_phone_row(self):
        for w in (320, 360, 390):
            for where in ("article", "word"):
                with self.subTest(width=w, where=where):
                    o = R["phone"]["share%d" % w][where]
                    self.assertEqual(o["width"], w)
                    self.assertTrue(o["shown"]["share"] and o["shown"]["report"] and o["shown"]["heart"], o)
                    self.assertFalse(o["shown"]["copy"], o)            # Copy link not shown: Share is
                    self.assertTrue(o["oneLine"], o)                   # Share, the button, the heart: one line
                    self.assertTrue(o["inside"], o)
                    self.assertFalse(o["overflow"], o)
                    if where == "article":           # the form open: the row unmoved, the line inside
                        op = R["phone"]["share%d" % w]["open"]
                        self.assertTrue(op["form"]["open"], op)
                        self.assertTrue(op["row"]["oneLine"] and op["row"]["inside"], op)
                        self.assertFalse(op["row"]["overflow"], op)
                        self.assertTrue(op["form"]["privacy"]["shown"] and op["form"]["privacy"]["inside"], op)
                    n = R["phone"]["noshare%d" % w][where]
                    self.assertFalse(n["shown"]["share"], n)
                    self.assertTrue(n["shown"]["copy"], n)             # no Share: Copy link stays
                    if where == "word":     # 168 (re-ruled 2026-11-06): no "Article page" in the row,
                        self.assertFalse(o["pagePresent"], o)      # not made at all,
                        self.assertFalse(n["pagePresent"], n)
                        self.assertTrue(o["allOneLine"], o)        # and nothing wraps
        wide = R["wide"]
        self.assertTrue(wide["shown"]["copy"] and wide["shown"]["share"], wide)   # a computer: both
        ww = R["wideWord"]                  # 168 re-ruled 2026-11-06 (everywhere): not on a computer either
        self.assertTrue(ww["shown"]["share"] and ww["shown"]["report"] and ww["shown"]["heart"], ww)
        self.assertFalse(ww["pagePresent"], ww)


if __name__ == "__main__":
    unittest.main(verbosity=2)
