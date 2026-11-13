"""Site decisions 173 (Robin, 2026-11-07): the readers' survey, "Ordpar — your first impressions", in
a browser (headless Edge, `browser/survey173.js`), sending to the receiver's own code run locally.

The receiver is `ordpar/receiver/tools/local.mjs` — the Worker's `handle` under bun, D1 stood in for by
bun:sqlite — started here on a free port; what arrived is read back through its `GET /surveys` with
the token, as Robin's page reads it. The page's switch (`survey.js` `SURVEY_RECEIVER`) is set to the
stand-in's address before the page's scripts run, so nothing is ever sent elsewhere.

**What is served.** The survey is off as committed (`chrome.SURVEY`), so a build has no `/survey/`
until it is turned on. When the site served (`ordpar/out/`, `ORDPAR_TEST_OUT`, or an overlay) has no
`/survey/`, this test lays its own overlay over `ordpar/out/` for its run: the page and the four
scripts that carry the switch (`survey.js`, `shell.js`, `ordpar.js`, `shell-pages.js`), rendered here
with the survey on (`page.set_survey`), in a temporary folder, deleted after.

* **The page**: its title, the intro (its "Privacy" linking `/privacy/#the-survey`), every question
  in order with its label, hint and limit (the follow-up 254, the texts within 2,000), radio buttons
  for the level and check boxes for the ideas and the devices, the trap out of sight and out of the
  tab order, one Send; the names in the accessibility tree; no "needs JavaScript" line with script on.
* **The skipped question**: "What is your first language?" shown, hidden while "Norwegian is my first
  language" is chosen, shown again for another level; never sent while hidden, whatever was typed.
* **Sending**: nothing answered — the status says so, nothing sent; answers sent — "Thank you, your
  answers have been sent." (a status line, focused), the form gone; a dead address — the failure said,
  the answers kept; offline — said, nothing sent, kept; the total cap reached with reports from here —
  the cap's words, the answers kept (reports and answers counted together).
* **What arrived**: exactly the answers sent, under their keys, the choices as they read, the
  follow-up apart; each request a POST of exactly `answers` and `follow`, no Referer, no Cookie,
  `no-referrer`.
* **The footer's "Tell us what you think →"**: as built, present exactly when the build wrote
  `SURVEY_HREF`; with the survey on, after the "under development" note, linking `/survey/` in the
  same tab; with the note gone (launch), in a line of its own, last in the footer.
* **A phone's width** (360 px): nothing on the page wider than the screen.

Against the live site (`ORDPAR_TEST_BASE` not local), the checks that need a send to ARRIVE are
skipped, as in `test_ordpar_browser_report166.py`, and without `/survey/` there the whole file is.
Skipped without Edge, bun or a build.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ORDPAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ORDPAR)
RECEIVER = os.path.join(ORDPAR, "receiver")
TOKEN = "browser-test-token-0123456789"
NATIVE = "Norwegian is my first language"
SITE = None
STAND_IN = None
OWN_OVERLAY = None
R = {}
ARRIVED = []
SKIP = harness.skip_reason() or (None if shutil.which("bun") else "bun is not on PATH")
_BASE = harness.base_override() or ""
LIVE = None if not _BASE or "127.0.0.1" in _BASE or "localhost" in _BASE else (
    "against %s: the local stand-in takes nothing from that origin, and the live receiver gets no "
    "test answers" % _BASE)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _served_has_survey():
    for folder in (harness.OVERLAY, harness.OUT):
        if folder and os.path.exists(os.path.join(folder, "survey", "index.html")):
            return True
    return False


def make_overlay():
    """A temporary overlay with the survey on: /survey/ and the scripts that carry the switch."""
    sys.path.insert(0, ROOT)
    from ordpar.sitegen import chrome, page
    from ordpar.sitegen.strings import EN
    d = tempfile.mkdtemp(prefix="ordpar-survey173-")
    old = chrome.SURVEY
    page.set_survey(True)
    try:
        files = {os.path.join("survey", "index.html"): page.survey_page("survey173 overlay", EN)}
        for url in (page.SURVEY_JS_HREF, page.SHELL_JS_HREF, page.JS_ALL_HREF, page.SHELL_PAGES_JS_HREF):
            files[url.lstrip("/")] = page.shipped(url)
    finally:
        page.set_survey(old)
    for rel, text in files.items():
        path = os.path.join(d, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return d


def start_stand_in():
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
        proc.stdin.close()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    proc.stdout.close()


def read_surveys(url):
    req = urllib.request.Request(url + "/surveys", headers={"Authorization": "Bearer " + TOKEN})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))["surveys"]


def setUpModule():
    global SITE, STAND_IN, OWN_OVERLAY, SKIP
    if SKIP:
        print("test_ordpar_browser_survey173: skipped —", SKIP)
        return
    if not _BASE and not _served_has_survey():
        OWN_OVERLAY = make_overlay()
        if harness.OVERLAY:
            print("test_ordpar_browser_survey173: the overlay %s has no /survey/; using its own" % harness.OVERLAY)
        harness.OVERLAY = OWN_OVERLAY
        print("test_ordpar_browser_survey173: the build has no /survey/ (the survey is off as committed); "
              "an overlay with it on:", OWN_OVERLAY)
    STAND_IN, url = start_stand_in()
    try:
        SITE = harness.Site()
        R.update(SITE.check("survey173.js", {"receiver": url + "/survey", "report": url + "/report",
                                             "dead": "http://127.0.0.1:%d/survey" % _free_port()},
                            timeout=300))
        ARRIVED.extend(read_surveys(url))
    finally:
        stop_stand_in(STAND_IN)
    if R.get("page") is None and _BASE:
        SKIP = "against %s: no /survey/ there" % _BASE


def tearDownModule():
    if SITE:
        SITE.close()
    if OWN_OVERLAY:
        shutil.rmtree(OWN_OVERLAY, ignore_errors=True)


def _skip():
    return SKIP


@unittest.skipIf(SKIP, SKIP or "")
class Survey(unittest.TestCase):

    def setUp(self):
        if _skip():
            self.skipTest(_skip())

    def test_a_the_page(self):
        pg = R["page"]
        self.assertEqual(pg["title"], "Ordpar — your first impressions")
        # the note first under the title, in bold (Robin, 2026-11-07)
        self.assertEqual(pg["note"], {"text": "Every question is optional.", "bold": True, "first": True})
        self.assertEqual(len(pg["intro"]), 2)
        self.assertTrue(pg["intro"][1].startswith("Your answers are stored by Ordpar (see Privacy) and read by Robin"))
        self.assertEqual(pg["privacy"], "/privacy/#the-survey")
        ids = [q["id"] for q in pg["qs"]]
        self.assertEqual(ids, ["level", "first_language", "looked_up", "confusing", "missed", "ideas",
                               "ideas_comments", "other_language", "devices", "browser", "again",
                               "anything_else", "follow"])
        by = {q["id"]: q for q in pg["qs"]}
        self.assertEqual(by["level"]["label"], "How well do you know Norwegian?")
        self.assertEqual([c[0] for c in by["level"]["choices"]], ["radio"] * 5)
        self.assertEqual(by["level"]["choices"][-1][1:], [NATIVE, NATIVE])
        self.assertEqual([c[0] for c in by["ideas"]["choices"]], ["checkbox"] * 7)
        self.assertEqual([c[1] for c in by["devices"]["choices"]], ["Phone", "Tablet", "Computer"])
        self.assertEqual(by["looked_up"]["hint"], "A few words you searched for, and whether the result helped.")
        self.assertEqual((by["follow"]["tag"], by["follow"]["max"]), ("input", 254))
        self.assertEqual(by["follow"]["label"], "If it's all right to ask you a follow-up question, leave an email "
                                                "address or name.")
        self.assertEqual(by["anything_else"]["label"], "Anything else you'd like to tell us?")
        for q in pg["qs"]:
            if q["max"] is not None:
                self.assertLessEqual(q["max"], 2000, q)
            self.assertTrue(q["shown"], q)
        self.assertEqual(pg["trap"], {"tab": -1, "hidden": True, "offscreen": True})
        self.assertEqual(pg["buttons"], ["Send"])
        self.assertFalse(pg["noscriptShown"])
        ax = [tuple(x) for x in R["ax"]]
        for want in (("radio", NATIVE), ("checkbox", "Phone"), ("button", "Send"),
                     ("textbox", "Anything else you'd like to tell us?"),
                     ("group", "How well do you know Norwegian?")):
            self.assertIn(want, ax, ax)

    def test_b_the_skipped_question(self):
        self.assertEqual(R["skip"], {"before": True, "native": False, "fluent": True})

    def test_c_nothing_answered(self):
        e = R["empty"]
        self.assertEqual(e["status"], "Please answer at least one question before you send.")
        self.assertTrue(e["failed"] and e["formShown"], e)
        self.assertEqual(R["emptySent"], 0)

    @unittest.skipIf(LIVE, LIVE or "")
    def test_d_sent(self):
        for s in (R["answers"], R["native"]):
            self.assertEqual(s["done"], "Thank you, your answers have been sent.", s)
            self.assertEqual((s["doneRole"], s["focus"], s["formShown"]), ("status", "done", False), s)

    @unittest.skipIf(LIVE, LIVE or "")
    def test_e_failed_offline_and_the_cap_keep_the_answers(self):
        f = R["failed"]
        self.assertEqual(f["status"], "Your answers could not be sent. They are kept here; please try again.")
        self.assertEqual((f["kept"], f["formShown"], f["done"]), ("FAILED: kept.", True, None), f)
        o = R["offline"]
        self.assertTrue(o["status"].startswith("You are offline. Sending your answers needs a connection"), o)
        self.assertEqual(o["kept"], "OFFLINE: kept.")
        self.assertEqual(R["offlineSent"], 0)
        self.assertTrue(R["fillRefused"], R.get("fill"))
        c = R["capped"]
        self.assertEqual(c["status"], "We have received a great many messages in the last hour. Your answers are "
                                      "kept here; please try again in an hour.")
        self.assertEqual(c["kept"], "CAP: refused, kept.")
        self.assertEqual(R["fill"] + 2, 30)             # the cap is 30: the two answers sent and the reports

    @unittest.skipIf(LIVE, LIVE or "")
    def test_f_what_arrived(self):
        self.assertEqual(len(ARRIVED), 2, ARRIVED)
        by = {s["answers"].get("anything_else"): s for s in ARRIVED}
        a = by["First answers."]
        self.assertEqual(a["answers"], {
            "level": "I can read simple texts", "first_language": "Polish", "looked_up": "SENT: hus, and it helped.",
            "ideas": ["Example sentences for the words and meanings that don't have any yet",
                      "Use Ordpar as the dictionary on your e-reader (Kindle, Kobo) when reading Norwegian books"],
            "devices": ["Phone"], "anything_else": "First answers."})
        self.assertEqual(a["follow"], "reader@example.org")
        n = by["NATIVE: second answers."]
        self.assertEqual(n["answers"], {"level": NATIVE, "anything_else": "NATIVE: second answers."})
        self.assertIsNone(n["follow"])
        self.assertNotIn("NEVER SENT", json.dumps(ARRIVED))

    @unittest.skipIf(LIVE, LIVE or "")
    def test_g_what_was_sent(self):
        posts = [s for s in R["sent"] if s["method"] == "POST"]
        self.assertEqual(len(posts), 4, R["sent"])       # 2 stored, the dead one, the one the cap refused
        for s in posts:
            body = json.loads(s["body"])
            self.assertEqual(sorted(body), ["answers", "follow"], s)
            heads = {k.lower(): v for k, v in s["headers"].items()}
            self.assertEqual(heads.get("referer", ""), "", s)
            self.assertNotIn("cookie", heads, s)
            self.assertEqual(s["referrerPolicy"], "no-referrer")
        self.assertNotIn("NEVER SENT", json.dumps(posts))

    def test_h_the_footer_link(self):
        built = R["builtFoot"]
        self.assertEqual(built["link"], bool(R["builtHref"]), (built, R["builtHref"]))
        f = R["foot"]
        self.assertTrue(f["link"] and f["shown"], f)
        self.assertEqual((f["text"], f["href"], f["target"]), ("Tell us what you think →", "/survey/", None))
        self.assertEqual(f["inNote"], f["noteThere"], f)      # after the note while there is one
        lf = R["launchFoot"]
        self.assertFalse(lf["noteThere"], lf)
        self.assertTrue(lf["link"] and lf["inLine"] and lf["lineLast"] and lf["shown"], lf)
        self.assertEqual(lf["href"], "/survey/")

    def test_i_a_phones_width(self):
        ph = R["phone"]
        self.assertLessEqual(ph["scroll"], ph["width"], ph)
        self.assertEqual(ph["wide"], 0, ph)


if __name__ == "__main__":
    unittest.main(verbosity=2)
