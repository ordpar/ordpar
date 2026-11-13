# -*- coding: utf-8 -*-
"""Site-review decisions 119 (Robin, 2026-10-24): a Norwegian-only article's links carry their
TARGET's English — the page HTML's side.

Until this build a Norwegian-only unit's cross-reference was a plain link with no peek (an
untitled link: `face.SENTINEL` dropped it), so neither a hover peek nor a gloss in the mini's
header. Now, inside a Norwegian-only unit (an untranslated page, a translated page's untranslated
set phrases: `article.norwegian_only`), an untitled link to a translated target takes, from the
target's library row at build time (`face.SiteFace.target_english`):

1. a **bare** link to a target with summary glosses: the glosses joined " · " in the link's peek,
   `<span class="ordbok-xpeek" lang="en" data-nosnippet>`, exactly as a translated page's Norwegian line has it
   (the mini script takes the header gloss from it, as there);
2. a **`#def<N>`** link: that sense's whole English definition line, as the target's page shows it
   (its segments in the page's order, links reduced to their words, broken at the page's `;<br>`),
   in `<span class="ordbok-xpeek ordpar-nbdef" lang="en" data-nosnippet>` (regular weight, wrapped at 22rem; left
   out of the mini's header);
3. nothing where the target is untranslated, a bare link's target has no summary glosses, or the
   targeted sense has no English; and nothing outside a Norwegian-only unit (a translated page).

Two parts: the face over stub rows (always runs), and the built pages — *stø* II (58037): *lene* II
bare, *stø* IV 1 one sense, *skorde* I 1 Norwegian only; *krukke* (32341), its compounds Norwegian
only; *stø* IV (58039), translated, its sense link keeping its own citing gloss — from `ordpar/out/`
(or `ORDPAR_TEST_OUT`), or fetched from `ORDPAR_TEST_BASE` (the live site before the build, snapshot
be80aae5188: fails on *stø* II; *krukke* fails there too, its compounds not yet links, 118); and the
offline copy's pack holding *stø* II, its peeks the page's (`build_offline.read_pack`; a build
folder only). A page missing from the build skips its test. The browser's side
(the hover, the mini's header, the weight): `test_ordpar_browser_nbpeek119.py`.
"""
import os
import re
import sys
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ordpar"))

from ordpar.sitegen import article, face as face_mod  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
BASE = (os.environ.get("ORDPAR_TEST_BASE") or "").rstrip("/")

# stub rows: 1 translated with summary glosses; 2 translated, no summary; 3 untranslated
ROWS = {
    1: {"id": 1, "summary": {"gloss": ["to lean", "to rest, to prop (something) against"]},
        "senses": [{"defn": 2, "en": ["to hold up, upright or in place",
                                      "[to support](/nob/bm/2#def9), [to help](/nob/bm/3)"],
                    "subs": [{"defn": 5, "en": ["a {kind} of [x · y](/nob/bm/2)"]},
                             {"defn": 6, "en": []}]}]},
    2: {"id": 2, "senses": [{"defn": 9, "en": ["to back"]}]},
    3: {"id": 3, "senses": [{"defn": 4, "no": ["noe"], "en": None}]},
}


class StubStore:
    library = ROWS
    mirror = {}

    def is_embedded_only(self, aid):
        return False


class StubFace(face_mod.SiteFace):
    def translated_row(self, aid):
        return ROWS[aid] if aid in (1, 2) else None


class Face(unittest.TestCase):

    def setUp(self):
        self.face = StubFace(StubStore())
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library(ROWS)
        self.face.set_page(99)

    def tearDown(self):
        face_mod.restore(self.saved)

    def nb(self, text):
        with article.norwegian_only(self.mk):
            return self.mk.expand(text, norwegian=True)

    def test_a_bare_the_summary_glosses(self):
        self.assertEqual(self.nb("[lene (II)](/nob/bm/1)"),
                         '<span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/1/" lang="nb">'
                         '<em>lene (II)</em></a><span class="ordbok-xpeek" lang="en" data-nosnippet>'
                         'to lean · to rest, to prop (something) against</span></span>')
        self.assertEqual(self.face.nb_counts, {"bare": 1, "sense": 0})

    def test_b_one_sense_the_definition_line(self):
        out = self.nb("[stø (IV, 1)](/nob/bm/1#def2)")
        self.assertIn('<span class="ordbok-xpeek ordpar-nbdef" lang="en" data-nosnippet>to hold up, upright or in '
                      'place;<br>to support, to help</span>', out)
        # a subsense, its mention's braces and its link's " · " as the page prints them
        self.assertIn('ordpar-nbdef" lang="en" data-nosnippet>a kind of x; y</span>', self.nb("[a](/nob/bm/1#def5)"))
        self.assertEqual(self.face.nb_counts, {"bare": 0, "sense": 2})

    def test_c_nothing(self):
        for text in ("[a](/nob/bm/2)",          # translated, no summary glosses
                     "[a](/nob/bm/3)",          # untranslated
                     "[a](/nob/bm/3#def4)",     # untranslated sense
                     "[a](/nob/bm/1#def6)",     # a sense with no English
                     "[a](/nob/bm/1#def77)"):   # no such sense
            self.assertNotIn("xpeek", self.nb(text), text)
        self.assertEqual(self.face.nb_counts, {"bare": 0, "sense": 0})

    def test_d_not_outside_a_norwegian_only_unit(self):
        self.assertNotIn("xpeek", self.mk.expand("[a](/nob/bm/1)", norwegian=True))
        self.assertNotIn("xpeek", self.mk.expand("[a](/nob/bm/1#def2)", norwegian=True))
        # a titled link keeps its own title inside one too
        self.assertIn('lang="en" data-nosnippet>own</span>', self.nb('[a](/nob/bm/1#def2 "own")'))

    def test_e_the_fragment_scopes(self):
        row = {"id": 99, "lemmas": [{"form": "stø", "homograph": "II"}], "pos_en": "noun",
               "senses": [{"defn": 1, "no": ["[lene (II)](/nob/bm/1)"]}]}
        lib = dict(ROWS)
        lib[99] = row
        self.face.set_library(lib)
        out = article.fragment(row, None, lib, self.mk, {"homograph": "homograph {n}",
                                                          "inflection": "Inflection"},
                               paradigm=False)
        self.assertIn('<span class="ordbok-xpeek" lang="en" data-nosnippet>to lean · to rest', out)
        self.assertEqual(self.face.nb_only, 0)


def page(aid):
    """The built article page's HTML, or None when this copy has no such page."""
    if BASE:
        try:
            with urllib.request.urlopen("%s/bm-en/%d/" % (BASE, aid), timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception:
            return None
    path = os.path.join(OUT, "bm-en", str(aid), "index.html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def xref(html, href):
    """The `<span class="ordbok-xref">` around the first link to `href` in the article."""
    m = re.search(r'<span class="ordbok-xref"><a class="ordbok-xword" href="%s"[^>]*>.*?</a>'
                  r'(?:<span class="ordbok-xpeek[^"]*" lang="en"(?: data-nosnippet)?>.*?</span>)?</span>' % re.escape(href),
                  html)
    return m.group(0) if m else None


class BuiltPages(unittest.TestCase):

    def get(self, aid):
        html = page(aid)
        if html is None:
            self.skipTest("no page %d in %s" % (aid, BASE or OUT))
        return html

    def test_a_sto_ii_lene_bare(self):
        x = xref(self.get(58037), "/bm-en/34820/")
        self.assertTrue(x and x.replace(" data-nosnippet", "").endswith('</a><span class="ordbok-xpeek" lang="en">to lean · to rest, '
                                         'to prop (something) against</span></span>'), x)

    def test_b_sto_ii_sto_iv_one_sense(self):
        x = xref(self.get(58037), "/bm-en/58039/#def2")
        self.assertTrue(x and x.replace(" data-nosnippet", "").endswith('</a><span class="ordbok-xpeek ordpar-nbdef" lang="en">to hold '
                                         'up, upright or in place;<br>to support, to help</span></span>'), x)

    def test_c_sto_ii_skorde_norwegian_only(self):
        x = xref(self.get(58037), "/bm-en/53420/#def2")
        self.assertTrue(x, "no skorde link")
        self.assertNotIn("xpeek", x)

    def test_d_krukke_compounds_untranslated_targets(self):
        html = self.get(32341)
        for href in ("/bm-en/109847/", "/bm-en/117653/"):
            x = xref(html, href)
            self.assertTrue(x, href)
            self.assertNotIn("xpeek", x, href)

    def test_e_a_translated_page_keeps_its_own_glosses(self):
        html = self.get(58039)
        self.assertNotIn("ordpar-nbdef", html)
        # its sense link keeps the citing article's gloss, not the target's line
        x = xref(html, "/bm-en/58083/#def2")
        self.assertTrue(x and x.replace(" data-nosnippet", "").endswith('<span class="ordbok-xpeek" lang="en">to support</span></span>'), x)
        self.assertNotIn("ordpar-nbdef", self.get(24627))

    def test_f_the_offline_copy_follows(self):
        # the offline copy packs the built pages (`build_offline.py`, decisions 61): *stø* II's there
        # with its peeks
        if BASE:
            self.skipTest("the offline packs are read from a build folder")
        import glob
        import build_offline
        found = None
        for path in glob.glob(os.path.join(OUT, "offline", "bm-en-*.bin")):
            with open(path, "rb") as fh:
                items = build_offline.read_pack(fh.read())
            if 58037 in items:                      # the pack's keys are the article ids
                found = items[58037].decode("utf-8")
                break
        if found is None:
            self.skipTest("no offline pack holds 58037 in %s" % OUT)
        self.assertEqual(xref(found, "/bm-en/58039/#def2"), xref(self.get(58037), "/bm-en/58039/#def2"))
        self.assertIn("ordpar-nbdef", found)
        # the attribute since site decisions 154 (either build)
        self.assertRegex(found, r'<span class="ordbok-xpeek" lang="en"(?: data-nosnippet)?>to lean · to rest')


if __name__ == "__main__":
    unittest.main()
