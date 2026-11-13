"""Site-review decisions 123 (Robin, 2026-10-24): Bokmålsordboka's pronunciation field and the Help page, as the browser shows them (headless Edge).

Through `browser/pron123.js`, at 1280×900, under each `formulas` choice (the default, `en`, `no`,
`both`):

* *abstrakt* (98, translated): "Pronunciation abstrakˊt", after the inflection toggle and before
  the etymology, as ordbokene's page (its English interface, rendered 2026-10-24);
* *doktor* (10539, translated): the field's words in English — "dokˊtor, in the plural dokˊtorer
  or doktoˊrer" — under the default, `en` and `both` (as the compound labels), in Norwegian under
  `no` ("i flertall", "eller"), decisions 81's one setting;
* *lektor* (34785, Norwegian-only): Norwegian under every choice, "lekˊtor, i flertall lekˊtorer
  eller lektoˊrer";
* no "?" beside the label on any of them, also where the field uses a mark the note explains
  (decisions 123's amendment, Robin 2026-11-02: the "?" "taking unecessary space and attention"
  once the sound icons were in; it had been there since 2026-10-24); the note is Help's alone;
* `/help/`'s § Pronunciation (`#pronunciation`) holds the same note, and every page's footer links
  "Help" just before "About" ("About and licence" until site decisions 176) — on an article page and on the home page.

`ORDPAR_TEST_BASE` points it at another copy (the live site before the build, snapshot
98be9479dbc: fails — no section, no Help page, no Help link). Skipped without Edge, bun or a build.
The page HTML's side: `test_ordpar_pron123.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ABSTRAKT, DOKTOR, LEKTOR, BACK, CAMP = 98, 10539, 34785, 4005, 8651
CHOICES = ("default", "en", "no", "both")
EXPECT = {
    ABSTRAKT: {c: "Pronunciation abstrakˊt" for c in CHOICES},
    DOKTOR: {c: ("Pronunciation dokˊtor, i flertall dokˊtorer eller doktoˊrer" if c == "no"
                 else "Pronunciation dokˊtor, in the plural dokˊtorer or doktoˊrer") for c in CHOICES},
    LEKTOR: {c: "Pronunciation lekˊtor, i flertall lekˊtorer eller lektoˊrer" for c in CHOICES},
    BACK: {c: "Pronunciation bekk eller bækk" for c in CHOICES},
    CAMP: {c: "Pronunciation kæmp" for c in CHOICES},
}
KEYED = (ABSTRAKT, DOKTOR, LEKTOR)
NOTE_START = "Written in ordinary Norwegian spelling"
FOOTER = ("/bm-en/%d/" % ABSTRAKT, "/")

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_pron123: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("pron123.js", {"pages": list(EXPECT), "keyed": list(KEYED),
                                            "footer": list(FOOTER)}))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Pronunciation(unittest.TestCase):

    def test_a_the_field_in_each_setting(self):
        for choice in CHOICES:
            for aid, want in EXPECT.items():
                got = RESULT["cases"][choice][str(aid)]
                where = "formulas=%s, page %d on %s: %s" % (choice, aid, RESULT.get("base"), got)
                self.assertTrue(got, where)
                self.assertEqual(got["text"], want[choice], where)
                self.assertTrue(got["order"], where)

    def test_b_no_question_mark(self):
        for choice in CHOICES:
            for aid in EXPECT:
                got = RESULT["cases"][choice][str(aid)] or {}
                self.assertEqual(got.get("hints"), 0,
                                 "formulas=%s, page %d: %s" % (choice, aid, got))

    def test_b2_none_where_a_mark_is_used(self):
        for aid in KEYED:
            k = RESULT["key"][str(aid)]
            self.assertIsNone(k["before"], "page %d on %s: %s" % (aid, RESULT.get("base"), k))

    def test_c_the_help_page(self):
        h = RESULT.get("help")
        self.assertTrue(h, "no #pronunciation on /help/ at %s" % RESULT.get("base"))
        self.assertEqual(h["head"], "Pronunciation")
        self.assertTrue((h["note"] or "").startswith(NOTE_START), h)

    def test_d_the_footer_links_help_before_about(self):
        for path in FOOTER:
            links = RESULT["footer"][path]
            where = "%s on %s: %s" % (path, RESULT.get("base"), links)
            self.assertIn("Help /help/", links, where)
            i = links.index("Help /help/")
            # since site decisions 142 (2026-10-27) "More ways to use Ordpar" between them
            self.assertTrue(links[i + 1].endswith(" /more/"), where)
            self.assertTrue(links[i + 2].endswith(" /about/"), where)


if __name__ == "__main__":
    unittest.main()
