"""Site-review decisions 104 (Robin, 2026-10-23/24): the opt-out "Send usage statistics" on the
settings page (headless Edge).

Robin, 2026-10-24: "the privacy page and the opt out does not need to be deployed before we actually
start the receiver". The setting `stats` (On, the default and first / Off) is drawn only while the
COUNTING is live (`chrome.counting()`: `events.js` `RECEIVER` set), which the build writes into the
settings page as `window.ORDPAR_COUNTING` (`build_index.copy_shell`; the Python side:
`test_ordpar_privacy104.py`, `test_ordpar_privacy166.py`). Until 2026-11-05 the privacy page's
switch drew it (`window.ORDPAR_PRIVACY`); site decisions 166's privacy build split the two, so the
page can be published with the counting off. Checked through `browser/optout104.js`, on a computer
and a phone:

* **As built** (the counting off, as shipped): no trace of the setting on the page — over an
  overlay whose settings page was built with `chrome.PRIVACY` on, the brief's case (the page on,
  the counting off: its footer carries "Privacy", and still no setting).
* **The page's old flag alone** (`window.ORDPAR_PRIVACY`, what a privacy-on build wrote until
  2026-11-05): no setting drawn (on the code before the split it was: this fails there).
* **With the counting's flag** (set before the page's scripts, as a build with the counting live
  writes it): the
  field "Send usage statistics" in "Loading, offline and your data", after the offline copy and the
  transfer and before the stored data; On first and chosen; a "?" with its hint; Off is stored and
  kept on reload; "Delete stored data" turns it back on. (`events.js` reading the stored Off:
  `test_ordpar_events104.py`.)

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build: fails). Skipped
without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

VIEWPORTS = ("computer", "phone")
SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_optout104: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("optout104.js", dict(mobile=vp == "phone"))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class OptOut(unittest.TestCase):

    def test_no_trace_as_built(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                b = RESULT[vp]["built"]
                self.assertEqual((b["field"], b["text"], b["flag"]), (False, False, False), b)

    def test_not_drawn_with_the_page_on_and_the_counting_off(self):
        # site decisions 166 (2026-11-05): the privacy page's switch no longer draws the setting
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s = RESULT[vp]["pageOnly"]
                self.assertTrue(s["oldFlag"], s)
                self.assertEqual((s["field"], s["text"], s["flag"]), (False, False, False), s)
                b = RESULT[vp]["built"]
                if b["privacyLink"]:                # an overlay built with chrome.PRIVACY on
                    self.assertEqual((b["field"], b["text"], b["oldFlag"]), (False, False, False), b)

    def test_drawn_with_the_switch(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                s = RESULT[vp]["on"]
                where = "%s on %s: %s" % (vp, RESULT[vp]["base"], s)
                self.assertTrue(s["flag"] and s["field"], "no field with the flag: " + where)
                self.assertEqual(s["title"], "Send usage statistics", where)
                self.assertEqual(s["choices"], [["on", "On", True], ["off", "Off", False]], where)
                self.assertTrue(s["hint"], where)
                o = s["order"]
                self.assertLess(o.index("transfer"), o.index("stats"), where)
                self.assertEqual(o[o.index("stats") + 1], "stored", where)
                if "offline" in o:
                    self.assertLess(o.index("offline"), o.index("stats"), where)

    def test_off_stored_kept_and_deleted(self):
        for vp in VIEWPORTS:
            with self.subTest(vp=vp):
                r = RESULT[vp]
                self.assertEqual(r["off"]["stored"], "off")
                self.assertEqual(r["off"]["choices"], [["on", "On", False], ["off", "Off", True]])
                self.assertEqual(r["reload"]["choices"], [["on", "On", False], ["off", "Off", True]])
                self.assertIsNone(r["deleted"]["stored"])
                self.assertEqual(r["deleted"]["choices"], [["on", "On", True], ["off", "Off", False]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
