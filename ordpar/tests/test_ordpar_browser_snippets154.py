"""Site decisions 154 (Robin, 2026-10-31): what Google reads from our pages (headless Edge).

Google built its snippets for *kanskje* and *være* from the page text, not from our meta
description, and the text came out glued and doubled: "kan hendeperhaps, maybeused to express a
possibility" (a link, its hover label, the next line with no space between), "være III homograph 3
verbto scent" (the screen readers' label beside the numeral, the word class run into the
gloss). Through `browser/snippets154.js`, on a computer and a phone, over *kanskje* 28561 and its
word page `/bm-en/kanskje/`, *være*'s word page, *være* III 69212 (a homograph numeral in the
head), *absurdisme* 100 (untranslated), the form page *tær* and an English search with result
rows (`#en=house`):

* (a) every hover label (`.ordbok-xpeek`) and screen-reader-only label (`.ordpar-visually-hidden`,
  `.sr-only`) inside a `data-nosnippet` `span`, `div` or `section` — on the drawn page and in the
  markup as served (the header's search `<label>` excepted); no `data-nosnippet` on any other
  element (Google reads it on those three only);
* (b) no glued text: no two consecutive drawn text nodes outside `data-nosnippet` that meet with
  no whitespace while the page shows them apart (innerText's space or line break, another line,
  or a gap of more than 2 px);
* (c) each page's description begins with its headword ("kanskje: perhaps · maybe …", Robin's
  approved shape), and `og:description` is the same.

`ORDPAR_TEST_BASE=https://ordpar.no` shows all three failing on the site before 154. Skipped
without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

PAGES = [
    {"path": "/bm-en/28561/", "word": "kanskje"},
    {"path": "/bm-en/kanskje/", "word": "kanskje"},
    {"path": "/bm-en/v%C3%A6re/", "word": "være"},
    {"path": "/bm-en/69212/", "word": "være"},
    {"path": "/bm-en/100/", "word": "absurdisme"},
    {"path": "/bm-en/t%C3%A6r/", "word": "tær"},
    {"path": "/bm-en/#en=house"},
]
VIEWPORTS = ("computer", "phone")
SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_snippets154: skipped —", SKIP)
        return
    SITE = harness.Site()
    for vp in VIEWPORTS:
        RESULT[vp] = SITE.check("snippets154.js", dict(mobile=vp == "phone", pages=PAGES))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class WhatGoogleReads(unittest.TestCase):
    def pages(self, vp):
        r = RESULT[vp]
        self.assertNotIn("error", r, "%s: %s" % (vp, r))
        self.assertEqual([p["path"] for p in r["pages"]], [p["path"] for p in PAGES])
        return r["pages"]

    def test_0_the_pages_drew(self):
        for vp in VIEWPORTS:
            for p in self.pages(vp):
                self.assertGreater(p["rows"], 0, "%s %s: nothing drawn" % (vp, p["path"]))

    def test_a_hidden_labels_carry_data_nosnippet(self):
        for vp in VIEWPORTS:
            for p in self.pages(vp):
                where = "%s %s" % (vp, p["path"])
                self.assertEqual(p["hidden"], [], "%s: a hidden label outside data-nosnippet (drawn page)" % where)
                self.assertEqual(p["hiddenRaw"], [], "%s: a hidden label outside data-nosnippet (served markup)" % where)
                self.assertEqual(p["badHolders"], [], "%s: data-nosnippet on an element Google ignores it on" % where)

    def test_b_no_glued_text(self):
        for vp in VIEWPORTS:
            for p in self.pages(vp):
                self.assertEqual(p["glued"], [], "%s %s: text a snippet would glue together" % (vp, p["path"]))

    def test_c_the_description_begins_with_the_headword(self):
        for p in self.pages("computer"):
            if not p.get("word"):
                continue
            self.assertTrue(p["descOk"], "%s: description %r, og:description %r, headword %r"
                            % (p["path"], p["description"], p["og"], p["word"]))


if __name__ == "__main__":
    unittest.main()
