"""Site decisions 166 (Robin, 2026-11-05, "Yes, as proposed"): the address that opens an article's
"Suggest a correction" form on arrival — `/bm-en/<id>/#report` — for the deck's link on every card,
in a browser (headless Edge, `browser/reportaddr166.js`). Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-report-address-166-2026-11-05.md`.

The key is a bare word among the fragment's `&`-separated parts (`report.js` `ADDRESS_KEY`), beside a
search (`#q=…`) and 146's settings, which the head script takes off the address while keeping every
other part. The article page's script (`page.PAGE_JS` `foot`) calls `report.js` `fromAddress` once
the foot's row is in the page: the form opened as a press of the button would, the key then taken
off the address with `history.replaceState`.

* **Off** (the switch empty): no button, no form, the address left as it came.
* **Opened**: the form under the foot's row, `aria-expanded`, focus in its text box and the box in the
  window; the address without the key (no fragment left), no history entry added.
* **Not again**: a reload, and Back from another page, do not reopen it; the address stays plain.
* **With 146's settings** (`#theme=<the theme the system does not show>&defs=en&report`, and the key
  first, `#report&mini=en`): the
  form open and the settings applied and kept as the tab's visit; neither left in the address.
* **With a search** on the article page (`#q=<word>&report`): the form open, `#q=<word>` kept.
* **Elsewhere**: the search page (`/bm-en/#q=<word>&report`) still answers the search, with no form
  opened; a word page (`/bm-en/<word>/#report`) opens none (the article page only).

The switch is set before the page's scripts run, to a dead local address (or empty), so nothing
can reach a receiver; nothing is sent. Fails on f2c7cc366's code (no `fromAddress`: the form never
opens from the address and the key stays). Needs `ordpar/out/` (or `ORDPAR_TEST_OUT`) with the
article page and `/bm-en/norge/`; a scratch render over it with `ORDPAR_TEST_OVERLAY`. Skipped
without Edge, bun or a build.
"""
import json
import os
import socket
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ARTICLE, WORD = 1000, "norge"
SITE = None
R = {}
SKIP = harness.skip_reason()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_reportaddr166: skipped —", SKIP)
        return
    SITE = harness.Site()
    R.update(SITE.check("reportaddr166.js", {"id": ARTICLE, "word": WORD,
                                             "dead": "http://127.0.0.1:%d/report" % _free_port()},
                        timeout=240))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Address(unittest.TestCase):

    def _open(self, s):
        self.assertTrue(s["button"], s)
        self.assertEqual(s["forms"], 1, s)
        self.assertTrue(s["open"], s)
        self.assertTrue(s["afterRow"], s)
        self.assertEqual(s["expanded"], "true", s)
        self.assertEqual(s["focus"], "text", s)

    def test_a_no_button_nothing_happens(self):
        s = R["off"]
        self.assertTrue(s["footRow"], s)            # the page as normal: Copy link's row is there
        self.assertFalse(s["button"], s)
        self.assertEqual(s["forms"], 0, s)
        self.assertEqual(s["hash"], "#report", s)    # untouched
        self.assertGreater(s["articles"], 0, s)

    def test_b_the_form_opens_from_the_address(self):
        s = R["opened"]
        self._open(s)
        self.assertTrue(s["textInView"], s)
        self.assertEqual(s["path"], "/bm-en/%d/" % ARTICLE)

    def test_c_the_key_taken_off(self):
        s = R["opened"]
        self.assertEqual(s["hash"], "", s)
        self.assertEqual(s["search"], "", s)
        # two loads since the count was taken (another page, then this one): replaceState, no entry
        self.assertEqual(s["history"], s["historyBefore"] + 2, s)

    def test_d_a_reload_does_not_reopen(self):
        s = R["reloaded"]
        self.assertEqual(s["hash"], "", s)
        self.assertTrue(s["button"], s)
        self.assertFalse(s["open"], s)
        self.assertEqual(s["forms"], 0, s)          # never made: the button not pressed
        self.assertEqual(s["expanded"], "false", s)

    def test_e_back_does_not_bring_the_key_back(self):
        s = R["back"]
        self.assertEqual(s["path"], "/bm-en/%d/" % ARTICLE, s)
        self.assertEqual(s["hash"], "", s)

    def test_f_with_the_settings(self):
        s = R["settings"]
        self._open(s)
        self.assertEqual(s["hash"], "", s)
        self.assertEqual(s["night"], R["theme"] == "dark", (R["theme"], s))
        self.assertEqual(s["night"], not R["systemDark"], s)   # the address's theme, not the system's
        self.assertTrue(s["defsEn"], s)
        self.assertEqual(json.loads(s["visit"]), {"theme": R["theme"], "defs": "en"})
        k = R["keyFirst"]
        self._open(k)
        self.assertEqual(k["hash"], "", k)
        self.assertTrue(k["miniEn"], k)
        self.assertEqual(json.loads(k["visit"]), {"mini": "en"})

    def test_g_with_a_search(self):
        s = R["search"]
        self._open(s)
        self.assertEqual(s["hash"], "#q=%s" % WORD, s)

    def test_h_the_search_page_still_answers(self):
        s = R["searchPage"]
        self.assertGreater(s["articles"], 0, s)
        self.assertFalse(s["open"], s)
        self.assertEqual(s["forms"], 0, s)

    def test_i_a_word_page_opens_none(self):
        s = R["wordPage"]
        self.assertEqual(s["path"], "/bm-en/%s/" % WORD, s)
        self.assertGreater(s["articles"], 0, s)
        self.assertTrue(s["button"], s)
        self.assertEqual(s["forms"], 0, s)


if __name__ == "__main__":
    unittest.main()
