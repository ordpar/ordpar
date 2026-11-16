"""Site-review decisions 113 (Robin, 2026-10-24): the search on a phone (headless Edge).

The finding: on a phone, a search made with the Enter key, or by tapping a suggestion, left the
keyboard up, and the box started writing with a capital letter. Checked through `browser/search113.js`:

* **The focus.** On a phone (touch emulation: `(pointer: coarse)`), after a search by Enter, by a
  tapped suggestion and by Enter on a highlighted suggestion, on the search page (answered in place)
  and from an article page (which goes to the search page), `document.activeElement` is not the
  search field — a phone's keyboard closes when its field loses the focus. On a computer the field
  keeps the focus after a search on the search page (`shell.js` `submit`, as before and as
  ordbokene.no's, observed 2026-10-24).
* **The capital.** Every search field on the article, search, 404, settings and favourites pages
  carries `autocapitalize="none"` (as ordbokene.no's).

A real phone's keyboard is not something a test can see: these read the focus and the attribute the
keyboard follows; Robin's phone is the last check. `ORDPAR_TEST_BASE` points it at another copy (the
live site before the build: fails). Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

VIEWPORTS = ("computer", "phone")
PAGES = ("article", "search", "404", "settings", "favourites")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_search113: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("search113.js", dict(mobile=vp == "phone", word="hus", prefix="hyt", id=21740))


def tearDownModule():
    if SITE:
        SITE.close()


def _searched(path):
    """A search's address: `/bm-en/#q=…`, or since site decisions 117 (2026-10-25) the word's own
    page, `/bm-en/<word>/` (every word searched here has one)."""
    import re
    return "#q=" in path or bool(re.match(r"^/bm-en/[^/0-9#][^/#]*/$", path))


@unittest.skipIf(SKIP, SKIP or "")
class PhoneSearch(unittest.TestCase):

    def test_the_emulation_is_a_touch_screen(self):
        self.assertTrue(RESULT["phone"]["coarse"])
        self.assertFalse(RESULT["computer"]["coarse"])

    def test_a_phone_lets_go_of_the_field_after_a_search(self):
        r = RESULT["phone"]
        for name in ("enter", "pick", "pickKey", "fromArticle"):
            with self.subTest(case=name):
                s = r["cases"][name]
                self.assertTrue(s["value"], "nothing was searched: %s on %s: %s" % (name, r["base"], s))
                self.assertTrue(_searched(s["path"]), "no search made: %s: %s" % (name, s))
                self.assertNotEqual(s["active"], "search",
                                    "the search field keeps the focus (the keyboard stays up): %s on %s: %s"
                                    % (name, r["base"], s))

    def test_a_computer_keeps_it_on_the_search_page(self):
        r = RESULT["computer"]
        for name in ("enter", "pick", "pickKey"):
            with self.subTest(case=name):
                s = r["cases"][name]
                self.assertTrue(_searched(s["path"]), s)
                self.assertEqual(s["active"], "search", "%s on %s: %s" % (name, r["base"], s))

    def test_every_search_field_starts_in_small_letters(self):
        for vp in VIEWPORTS:
            for page in PAGES:
                with self.subTest(vp=vp, page=page):
                    f = RESULT[vp]["fields"][page]
                    self.assertTrue(f, "no search field on %s" % page)
                    for field in f:
                        self.assertEqual(field["autocapitalize"], "none",
                                         "%s on %s (%s): %s" % (page, RESULT[vp]["base"], vp, field))


if __name__ == "__main__":
    unittest.main(verbosity=2)
