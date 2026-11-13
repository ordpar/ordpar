# -*- coding: utf-8 -*-
"""Site decisions 166, Copy (Robin, 2026-11-05): the Copy button on Robin's `/reports` page in a
browser (headless Edge, `browser/copy166.js`). Brief: `docs/sessions/2026-09-19-ordpar-site-review/
evidence/brief-report-copy-166-2026-11-05.md`; the text itself: `test_ordpar_copy166.py`.

The page is served by `scripts/serve.py`'s own `Handler` on a free loopback port, with
`reports_page.queue_json` stood in for (one open report, with a reply address and a name to
credit, its `copy` made by `copy_text`), so no receiver is needed. The clipboard is stood in for in
the page (`navigator.clipboard.writeText` recording, or refusing, or absent).

* **The row**: Done, Fixed …, Copy; Copy's tooltip and the note under the row say the reply address
  and the name to credit are not copied (the row still shows them to Robin).
* **Copied**: exactly the server's text, once; the status says so; no text box.
* **The clipboard refused, or none**: a read-only text box with exactly that text, focused and
  selected whole; the status says to press Ctrl+C.

Skipped without Edge or bun, and in the public repository, which has no report reader.
"""
import os
import shutil
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "browser"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import harness  # noqa: E402
try:
    import reports_page  # noqa: E402
except ModuleNotFoundError as e:
    if e.name != "reports_page":
        raise
    reports_page = None

REPORT = {"id": 31, "day": "2026-11-05", "article": 24627, "build": "2026-11-05-1508",
          "category": "translation", "text": "Sense 2 reads oddly.", "reply": "reader@example.org",
          "credit": "Kari Nordmann"}
SKIP = ("needs reports_page (scripts/reports_page.py), which the public repository does not have"
        if reports_page is None else
        None if harness.edge_path() and shutil.which("bun") else "no Edge or no bun")
SITE = None
HTTPD = None
RESULT = {}
COPY = None


def setUpModule():
    global SITE, HTTPD, COPY
    if SKIP:
        print("test_ordpar_browser_copy166: skipped —", SKIP)
        return
    import serve
    rep = dict(REPORT)
    rep["live"] = reports_page.LIVE % rep["article"]
    rep["local_path"] = "/bm-en/%d/" % rep["article"]
    COPY = rep["copy"] = reports_page.copy_text(rep)
    saved = reports_page.queue_json
    reports_page.queue_json = lambda: {"ok": True, "reports": [rep], "receiver": "stand-in",
                                       "fixes": [], "fixes_file": "ordpar/reader-fixes.jsonl"}
    unittest.addModuleCleanup(lambda: setattr(reports_page, "queue_json", saved))
    HTTPD = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
    threading.Thread(target=HTTPD.serve_forever, daemon=True).start()
    old = os.environ.get("ORDPAR_TEST_BASE")
    os.environ["ORDPAR_TEST_BASE"] = "http://127.0.0.1:%d" % HTTPD.server_address[1]
    try:
        SITE = harness.Site()
    finally:
        if old is None:
            os.environ.pop("ORDPAR_TEST_BASE", None)
        else:
            os.environ["ORDPAR_TEST_BASE"] = old
    RESULT.update(SITE.check("copy166.js", {"copy": COPY})["out"])


def tearDownModule():
    if SITE:
        SITE.close()
    if HTTPD:
        HTTPD.shutdown()
        HTTPD.server_close()


@unittest.skipIf(SKIP, SKIP or "")
class CopyButton(unittest.TestCase):
    def test_the_row(self):
        b = RESULT["ok"]["before"]
        self.assertEqual(b["buttons"], ["Done", "Fixed …", "Copy"])
        self.assertIn("The reply address and the name to credit are not copied.", b["title"])
        self.assertEqual(b["note"], "Copy leaves out the reply address and the name to credit.")
        self.assertIn("reader@example.org", b["rowText"])      # still shown to Robin
        self.assertIsNone(b["box"])
        self.assertEqual(b["copied"], [])

    def test_copied(self):
        a = RESULT["ok"]["after"]
        self.assertEqual(a["copied"], [COPY])
        self.assertNotIn("reader@example.org", COPY)
        self.assertNotIn("Kari Nordmann", COPY)
        self.assertTrue(a["status"].startswith("Copied report #31"), a["status"])
        self.assertIsNone(a["box"])

    def test_refused_or_none(self):
        for mode in ("refuse", "none"):
            with self.subTest(mode=mode):
                a = RESULT[mode]["after"]
                self.assertEqual(a["box"], {"value": COPY, "readOnly": True, "focused": True,
                                            "selected": True})
                self.assertIn("press Ctrl+C", a["status"])
        self.assertEqual(RESULT["refuse"]["after"]["copied"], [COPY])
        self.assertEqual(RESULT["none"]["after"]["copied"], [])


if __name__ == "__main__":
    unittest.main()
