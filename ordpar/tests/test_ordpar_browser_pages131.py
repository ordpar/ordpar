"""Site-review decisions 131 (2026-10-25/26): the About page's new parts and the "Coming to Ordpar"
page in a browser (headless Edge, `browser/pages131.js`) — the check `deploy.py verify` runs on
the live site after a push, as for every page.

* `/about/#contact` lands on the section "Contact" (`h2#contact`, the address the deck's AnkiWeb
  page links), scrolled to it (to the page's end, the section being the last), the last section, its sentence with the `mailto:post@ordpar.no`
  link; the deck's paragraph under "Thanks", *6000 Most Frequent Norwegian Words* in italics and
  its two AnkiWeb links; "How far it has come" ending with the link to Coming to Ordpar.
* `/coming/` answers 200: its title "Coming to Ordpar — Ordpar", its heading, its intro, the six
  items in order, each with its *Waiting for:* line; no `noindex`; its canonical.
* No footer link to either.

The words themselves are pinned in `test_ordpar_site131.py`. `ORDPAR_TEST_BASE=https://ordpar.no`
runs it against the live site (before 131's deploy: fails — no `#contact`, `/coming/` a 404).
Skipped without Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SITE = None
R = {}
SKIP = harness.skip_reason()
# "English to Norwegian search." went with its build (site decisions 148, 2026-10-29)
# "Norwegian you can listen to." went with the audio (site decisions 159, live 2026-11-02)
ITEMS = ["Ordpar in Norwegian.",
         "More languages.", "More example sentences.", "Better English equivalents."]


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_pages131: skipped —", SKIP)
        return
    SITE = harness.Site()
    R.update(SITE.check("pages131.js", {}))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class Pages(unittest.TestCase):

    def test_a_contact(self):
        a = R["about"]
        self.assertEqual(a["contact"], "Contact", a)
        self.assertTrue(a["last"], a)
        self.assertIsNotNone(a["top"])
        # scrolled to: its top in the window's first third, or (the last section, on a short page)
        # the page scrolled to its end with the heading in view
        self.assertTrue(0 <= a["top"] < a["vh"] / 3 or (a["y"] > 0 and a["y"] >= a["ymax"] - 1
                                                        and 0 <= a["top"] < a["vh"]), a)
        self.assertEqual(a["mail"], {"href": "mailto:post@ordpar.no", "text": "post@ordpar.no"})
        self.assertEqual(a["contactText"], "Write to us at post@ordpar.no about a mistake in an article, "
                                           "the Anki deck, or anything else about Ordpar. If you would like "
                                           "the dictionary's data as files, the articles or the "
                                           "recordings, write to us there too.")  # decisions 172

    def test_b_the_deck_under_thanks(self):
        a = R["about"]
        # decisions 178 (2026-11-08): both decks, the new one first and linked, the subtitle list credited
        self.assertEqual(a["deckEm"], "Ordpar: Norwegian Core Vocabulary")
        self.assertEqual(a["deckLinks"], [["Hermit Dave's FrequencyWords", "https://github.com/hermitdave/FrequencyWords"],
                                          ["Ordpar: Norwegian Core Vocabulary", "https://ankiweb.net/shared/info/1906319472"],
                                          ["Part 1", "https://ankiweb.net/shared/info/1989661164"],
                                          ["Part 2", "https://ankiweb.net/shared/info/879167685"]])
        self.assertTrue(a["deck"].endswith("the dictionary itself stays under CC BY 4.0."), a["deck"])

    def test_c_the_link_to_coming(self):
        a = R["about"]
        self.assertEqual(a["coming"], "Coming to Ordpar")
        self.assertTrue(a["farEnds"].endswith("What we have decided to build next: Coming to Ordpar."), a)

    def test_d_coming(self):
        c = R["coming"]
        self.assertEqual(c["status"], 200)
        self.assertEqual(c["title"], "Coming to Ordpar — Ordpar")
        self.assertEqual(c["h1"], "Coming to Ordpar")
        self.assertTrue(c["intro"].startswith("What we have decided to build, and what each is waiting for."))
        self.assertEqual([i["name"] for i in c["items"]], ITEMS)
        self.assertEqual([i["waiting"] for i in c["items"]], ["Waiting for:"] * len(ITEMS))
        # site decisions 148 (Robin, 2026-10-29): what has landed moves to "Built", a list of its own
        self.assertEqual(c["built"], ["Norwegian you can listen to.", "English to Norwegian search."])
        self.assertFalse(c["noindex"])
        self.assertEqual(c["canonical"], "https://ordpar.no/coming/")

    def test_e_no_footer_link(self):
        self.assertFalse(R["about"]["footContact"])
        self.assertFalse(R["about"]["footComing"])
        self.assertFalse(R["coming"]["footComing"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
