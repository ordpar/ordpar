"""Site-review decisions 115, last paragraph (Robin, 2026-10-24): a random word is not a search (headless Edge).

Robin: "I disagree. A random word is not a search, and it does not go into history". Random word
opens the drawn headword's search page (`test_ordpar_browser_random115.py` pins where it lands),
but the draw is not recorded in History and sends no search event. Through
`browser/randomdraw115.js`, on a computer (clicked) and a phone (tapped), with a stand-in receiver
(the events module given a test address before the page's scripts run, `fetch` to it answered in
the page, as `test_ordpar_events104.py`'s stand-in page does; the built files untouched):

* Random word on the search page lands on a `#q=` search — since site decisions 117 the drawn
  word's own page, `/bm-en/<word>/`, where it has one; History stays empty and no `hit`,

  `miss` or `pick` is sent — also after a reload of that address, and after Back and Forward;
* a search typed afterwards on that page (*hus*) is recorded in History and sent as one `hit`,
  as any search;
* Random word from an article page (*fly* V, 15544) lands on a `#q=` search with no marker left
  in the address; History still holds only the typed search and nothing more is sent — also after
  a reload;
* the stand-in is live: the events module is not quiet under it (else "nothing sent" would hold
  vacuously).

`ORDPAR_TEST_BASE` points it at another copy (the build before this fix: fails — the draw goes
into History and is sent as a `hit`). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

FLY_V = 15544
TYPED = "hus"
VIEWPORTS = ("computer", "phone")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_randomdraw115: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("randomdraw115.js", dict(mobile=vp == "phone", article=FLY_V, typed=TYPED))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class ADrawIsNotASearch(unittest.TestCase):

    def _steps(self, vp):
        r = RESULT[vp]
        self.assertNotIn("error", r, "%s: %s" % (vp, r))
        return r["steps"]

    def test_a_the_stand_in_receiver_is_live(self):
        for vp in VIEWPORTS:
            s = self._steps(vp)
            self.assertEqual(s["start"]["quiet"], "", "%s: the events module is quiet: %r" % (vp, s["start"]["quiet"]))

    def test_b_drawn_on_the_search_page(self):
        for vp in VIEWPORTS:
            s = self._steps(vp)
            self.assertTrue(s["drawSearchLanded"], "%s: did not land on a #q= search: %s" % (vp, s["drawSearch"]))
            for name in ("drawSearch", "reload", "backForward"):
                st = s[name]
                where = "%s, %s: %s" % (vp, name, st["url"])
                # the search's address: `#q=`, or since site decisions 117 the word's own page
                self.assertTrue(st["hash"].startswith("#q=") or (not st["hash"] and st["q"]), where)
                self.assertEqual(st["q"], s["drawSearch"]["q"], where)
                self.assertGreaterEqual(st["n"], 1, where)
                self.assertEqual({"history": st["history"], "sent": st["sent"]}, {"history": [], "sent": []},
                                 "the draw went into History or was sent as a search: " + where)

    def test_c_a_typed_search_afterwards_is_ordinary(self):
        for vp in VIEWPORTS:
            st = self._steps(vp)["typed"]
            where = "%s: %s" % (vp, st["url"])
            self.assertEqual(st["q"], TYPED, where)
            self.assertEqual(st["history"], [TYPED], where)
            self.assertEqual(st["sent"], [{"type": "hit", "query": TYPED, "lang": "nb"}], where)

    def test_d_drawn_from_an_article_page(self):
        for vp in VIEWPORTS:
            s = self._steps(vp)
            self.assertTrue(s["drawArticleLanded"], "%s: did not land on a #q= search: %s" % (vp, s["drawArticle"]))
            for name in ("drawArticle", "reload2"):
                st = s[name]
                where = "%s, %s: %s" % (vp, name, st["url"])
                self.assertRegex(st["hash"], r"^(#q=[^&]+)?$", "a marker left in the address: " + where)
                self.assertTrue(st["q"], where)
                self.assertGreaterEqual(st["n"], 1, where)
                self.assertEqual((st["box"] or "").lower(), st["q"].lower(), where)
                self.assertEqual({"history": st["history"], "sent": st["sent"]},
                                 {"history": [TYPED], "sent": [{"type": "hit", "query": TYPED, "lang": "nb"}]},
                                 "the draw went into History or was sent as a search: " + where)


if __name__ == "__main__":
    unittest.main()
