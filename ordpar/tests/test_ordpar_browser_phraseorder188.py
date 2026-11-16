"""Site decisions 188 (2026-11-16): the set phrases ordered by CEFR level, in headless Edge
(`browser/phraseorder188.js`), on a computer (clicked) and a phone (tapped), over pages this test
renders with the levels.

* **Settings**: "Order of the set phrases" right after "CEFR level after the headword", under
  Article's Language, hidden while the boxes are off and shown once they are on; Alphabetical then
  By CEFR level, Alphabetical checked with nothing stored; its "?" says a level stays alphabetical;
  By CEFR level stores `phraseorder` = level; the preset Default gives alpha (and the boxes off, the
  setting hidden again), For learners level with the boxes on.
* **The order**: what level gives is worked out here from the page's own order (each block's
  `data-level`, its group): the translated phrases A1, A2, B1, B2, C, then any with no level, each
  level in the page's order, then the untranslated ones the same way. Alphabetical, or level with
  the boxes off: drawn in the page's order. Both on: drawn by level, the classes on <html> before the
  first block is parsed (nothing moves on load), the section exactly the height it has
  alphabetically; changed in place both ways, and back to the page's order when the boxes go off.
* **The features that touch the blocks**: a link to a set phrase that moves (`#x102921-def2`, *på
  huset*: last alphabetically, first by level) lands on it; the sound icons, as many in each order;
  the eye's whole-article mode (186), the eye pressed too; "Show N more examples" (exlimit 1), a
  line pressed, the block grown and the order kept; Norwegian only (152); print. Each by level and
  the same height in both orders.
* **The groups**: 5516 (one translated phrase, the rest untranslated): each group by level, the
  untranslated heading after the translated phrase and before its group; under Norwegian only too
  (no heading there). A Norwegian-only article, 46031.
* **The address**: `#levels=on&phraseorder=level` orders by level for the visit, nothing stored.
* **Every article shown whole**: the word page *hus* and each full result of *fisk* (list view off),
  an article opened in a list row.
* **The page's own order** (the keyboard, decisions 188): in every check above, the order of the
  blocks in the page (what screen readers and the Tab key follow) is the drawn one, the order as
  built read from the article's own page as served, never from the page script's record. On *hus*:
  every block's place on the screen the same before and after the page script runs (`ordparDefs`),
  at load (the blocks first put back as built) and at each change of the two classes on `<html>`
  as the shell makes it, the page's order changed by the script each time; the Tab key, pressed
  from the section's heading, meets the blocks in the drawn order (by level; alphabetically with
  the order alpha and with the boxes off), each once; the focus on a link in a block that moves kept
  through a change of the order in place both ways, the page not scrolled; a small article open in
  such a block still open, beside its link, after the order changes in place both ways.

Small articles keep their order: the sheet's rules reach only a section's own blocks and its
untranslated group's (child combinators), so the blocks a small article copies into its box, even
when the box opens inside a block, keep the block layout; checked on stand-in markup appended to a
block of *hus*, not on a real small article.

The overlay (`ORDPAR_TEST_OVERLAY`, laid over `ordpar/out/` by the harness): the pages above
rendered through `build_site.Builder` with `ordpar/levels.tsv` (and the clip names in
`.cache/ordpar-audio-names.tsv` where that file is here, so the sound icons show), the working tree's
`/site/` files written as the build writes them and the shell pages, as `test_ordpar_browser_levels187`
makes its own. Skipped without Edge, bun, a build or the mirror.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "browser"))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import test_ordpar_levels187 as L  # noqa: E402

IDS = (24627, 5516, 46031, 14903, 14904)
NAMES = os.path.join(L.REPO, ".cache", "ordpar-audio-names.tsv")
RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C": 5}
SITE = None
RESULTS = {}
OWN = None
SKIP = harness.skip_reason() or (None if L.mirror_path() else "no mirror (ordpar/local-paths.json `mirror`)")


def make_overlay():
    from ordpar import build_site, build_index
    from ordpar.sitegen import audio, page
    d = tempfile.mkdtemp(prefix="ordpar-phraseorder188-")
    b = L.builder(True)
    if os.path.exists(NAMES):
        b.audio = audio.Names.read(NAMES)
    for aid in IDS:
        html = page.finish(b.page(aid)["html"])
        path = os.path.join(d, "bm-en", str(aid), "index.html")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
    shutil.copytree(os.path.join(L.ORDPAR, "site"), os.path.join(d, "site"))
    build_site.write_assets(d)
    build_site.write_strings(os.path.join(d, "site", "strings", "en.json"))
    build_index.copy_shell(d, stats=build_index.site_stats(harness.OUT))
    front = os.path.join(d, "index.html")      # the build's own front page stays
    if os.path.exists(front):
        os.remove(front)
    return d


def setUpModule():
    global SITE, OWN
    if SKIP:
        print("test_ordpar_browser_phraseorder188: skipped —", SKIP)
        return
    OWN = make_overlay()
    if harness.OVERLAY:
        print("test_ordpar_browser_phraseorder188: its own overlay %s, not %s" % (OWN, harness.OVERLAY))
    harness.OVERLAY = OWN
    SITE = harness.Site()
    for mobile in (False, True):
        RESULTS["phone" if mobile else "computer"] = SITE.check("phraseorder188.js", {"mobile": mobile})


def tearDownModule():
    if SITE:
        SITE.close()
    if OWN:
        shutil.rmtree(OWN, ignore_errors=True)


def page_order(sec):
    return [t for t, _lv, _g in sec["page"]]


def by_level(sec):
    """The order level gives: each group by level, a level in the page's order (a stable sort)."""
    out = []
    for group in ("tr", "untr"):
        blocks = [(t, lv) for t, lv, g in sec["page"] if g == group]
        out += [t for t, _lv in sorted(blocks, key=lambda b: RANK.get(b[1], 6))]
    return out


@unittest.skipIf(SKIP, SKIP or "")
class PhraseOrder(unittest.TestCase):

    def each(self):
        for n, r in RESULTS.items():
            yield n, r["cases"]

    def assertPage(self, secs, what):
        # drawn in the order the page was built in, and the page's own blocks in it
        self.assertTrue(secs, what)
        for sec in secs:
            self.assertEqual(sec["drawn"], page_order(sec), what)
            self.assertEqual(sec["dom"], page_order(sec), what + " (the page's order)")

    def assertLevel(self, secs, what):
        # drawn by level, and the page's own blocks in the same order (decisions 188, the keyboard)
        self.assertTrue(secs, what)
        for sec in secs:
            self.assertEqual(sec["drawn"], by_level(sec), what)
            self.assertEqual(sec["dom"], by_level(sec), what + " (the page's order)")

    def assertBoth(self, pair, what):
        # alphabetical in the page's order, level by level, the sections the same height
        self.assertPage(pair["alpha"], what + " alpha")
        self.assertLevel(pair["level"], what + " level")
        for a, b in zip(pair["alpha"], pair["level"]):
            self.assertAlmostEqual(a["height"], b["height"], delta=0.5, msg=what)

    def test_a_the_setting(self):
        for n, c in self.each():
            with self.subTest(n):
                off, on = c["fieldOff"], c["fieldOn"]
                self.assertEqual((off["before"], off["shown"]), ("levels", False), off)
                self.assertEqual((on["before"], on["after"], on["title"], on["sub"], on["choices"], on["checked"]),
                                 ("levels", "exlimit", "Order of the set phrases", "Language",
                                  ["Alphabetical, as in Bokmålsordboka", "By CEFR level, A1 first"], ["alpha"]), on)
                self.assertTrue(on["shown"] and on["hint"], on)
                self.assertIn("within a level they stay alphabetical", c["hintBox"] or "")
                self.assertEqual(c["stored"], "level")
                self.assertEqual(c["presetDefault"], {"order": "alpha", "levels": "off"})
                self.assertFalse(c["fieldAfterDefault"]["shown"])
                self.assertEqual(c["presetLearners"], {"order": "level", "levels": "on"})

    def test_b_alphabetical_and_with_the_boxes_off(self):
        for n, c in self.each():
            with self.subTest(n):
                self.assertPage(c["alpha"], "alpha")
                self.assertNotEqual(by_level(c["alpha"][0]), page_order(c["alpha"][0]))   # hus does move
                self.assertEqual(c["boxesOff"]["cls"], {"levels": False, "order": True})
                self.assertPage(c["boxesOff"]["secs"], "boxes off")

    def test_c_by_level_from_the_first_paint(self):
        for n, c in self.each():
            with self.subTest(n):
                self.assertIs(c["paint"], True)
                self.assertPage(c["onAlpha"], "on, alpha")
                self.assertLevel(c["on"], "on, level")
                self.assertEqual(c["on"][0]["drawn"][0], "på huset")
                self.assertEqual(c["on"][0]["cls"], "ordbok-sec ordpar-exprs")
                self.assertAlmostEqual(c["on"][0]["height"], c["onAlpha"][0]["height"], delta=0.5)

    def test_c2_a_small_articles_blocks_inside_a_block_left_alone(self):
        for n, c in self.each():
            with self.subTest(n):
                m = c["miniInside"]
                self.assertIsNotNone(m)
                self.assertTrue(m["cFirst"], m)                     # the page's order
                self.assertEqual((m["order"], m["after"]), ("0", "none"), m)
                self.assertNotEqual(m["margin"], "0px", m)         # the block layout's own margin

    def test_d_changed_in_place(self):
        for n, c in self.each():
            with self.subTest(n):
                self.assertPage(c["inPlaceAlpha"], "in place, alpha")
                self.assertLevel(c["inPlaceLevel"], "in place, level")
                self.assertPage(c["inPlaceBoxesOff"], "in place, boxes off")

    def test_e_a_link_to_a_set_phrase_that_moves(self):
        for n, c in self.each():
            with self.subTest(n):
                a = c["anchor"]
                self.assertIsNotNone(a)
                self.assertTrue(a["inView"] and a["first"], a)

    def test_f_the_features_that_touch_the_blocks(self):
        for n, c in self.each():
            with self.subTest(n):
                self.assertBoth(c["icons"], "icons")
                self.assertEqual(c["icons"]["alpha"][0]["icons"], c["icons"]["level"][0]["icons"])
                if os.path.exists(NAMES):
                    self.assertGreater(c["icons"]["level"][0]["icons"], 0)
                self.assertBoth(c["eyeAll"], "eye, all the English")
                self.assertTrue(c["eyeAllPressed"]["pressed"])
                self.assertLevel(c["eyeAllPressed"]["secs"], "eye pressed")
                self.assertBoth(c["exlimit"], "exlimit 1")
                m = c["exmore"]
                self.assertTrue(m["found"] and m["grew"] and m["sameOrder"], m)
                self.assertBoth(c["nbo"], "Norwegian only")
                self.assertLevel(c["print"]["level"], "print")

    def test_g_the_two_groups(self):
        for n, c in self.each():
            with self.subTest(n):
                g = c["groups"]
                self.assertBoth(g, "groups")
                sec = g["level"][0]
                self.assertIn("ordpar-exprs", sec["cls"])
                self.assertNotEqual(by_level(sec), page_order(sec))
                self.assertEqual({x[2] for x in sec["page"]}, {"tr", "untr"})
                self.assertTrue(sec["headAfterTr"] and sec["headBeforeUntr"], sec)
                self.assertBoth(c["nboGroups"], "groups, Norwegian only")
                self.assertIsNone(c["nboGroups"]["level"][0]["headAfterTr"])     # no heading there
                self.assertBoth(c["nbArticle"], "a Norwegian-only article")
                self.assertNotEqual(by_level(c["nbArticle"]["level"][0]), page_order(c["nbArticle"]["level"][0]))

    def test_h_the_address(self):
        for n, c in self.each():
            with self.subTest(n):
                self.assertLevel(c["address"]["secs"], "address")
                self.assertIsNone(c["address"]["stored"])
                self.assertEqual(c["address"]["hash"], "")

    def test_i_every_article_shown_whole(self):
        for n, c in self.each():
            with self.subTest(n):
                self.assertLevel(c["word"], "word page")
                full = [r for r in c["full"] if r["secs"]]
                self.assertTrue(full, c["full"])
                for r in full:
                    self.assertLevel(r["secs"], "full result %s" % r["id"])
                self.assertTrue(any(by_level(s) != page_order(s) for r in full for s in r["secs"]))
                self.assertLevel(c["row"], "list row")

    def test_j_the_page_script_moves_nothing_on_screen(self):
        for n, c in self.each():
            with self.subTest(n):
                st = c["still"]
                lv = by_level(c["on"][0])
                built = st["built"]
                self.assertEqual(built, page_order(c["on"][0]))
                self.assertNotEqual(lv, built)
                # (before, after) the script: at load from the built order; each class off and on
                want = {"load": (built, lv), "levelOff": (lv, built), "levelOn": (built, lv),
                        "boxesOff": (lv, built), "boxesOn": (built, lv)}
                for k, (b, a) in want.items():
                    self.assertEqual((st[k]["before"], st[k]["after"]), (b, a), k)
                    self.assertLessEqual(st[k]["shift"], 0.05, k)

    def assertTabs(self, t, want, what):
        self.assertIsNotNone(t, what)
        seen = t["seen"]
        self.assertGreaterEqual(len(seen), 3, what)
        self.assertNotIn("(outside a block)", seen, what)
        self.assertEqual(len(seen), len(set(seen)), what + ": a block met twice")
        # every block the focus reached, in the order drawn; the drawn order the expected one
        self.assertEqual(t["drawn"], want, what)
        self.assertEqual(seen, [x for x in t["drawn"] if x in set(seen)], what)

    def test_k_the_tab_key_follows_the_drawn_order(self):
        for n, c in self.each():
            with self.subTest(n):
                sec = c["on"][0]
                self.assertTabs(c["tabLevel"], by_level(sec), "level")
                self.assertTabs(c["tabAlpha"], page_order(sec), "alpha")
                self.assertTabs(c["tabBoxesOff"], page_order(sec), "boxes off")
                # the Tab order differs between the two, so the check above can tell them apart
                self.assertNotEqual(c["tabLevel"]["seen"], c["tabAlpha"]["seen"])

    def test_l_the_focus_kept_through_a_change_in_place(self):
        for n, c in self.each():
            with self.subTest(n):
                f = c["focusKept"]
                self.assertIsNotNone(f, "no block that moves in the page")
                self.assertEqual(f["kept"], [True, True], f)
                self.assertTrue(f["moved"] and f["back"], f)
                self.assertFalse(f["scrolled"], f)

    def test_m_a_small_article_open_inside_a_block_kept(self):
        for n, c in self.each():
            with self.subTest(n):
                m = c["mini"]
                self.assertIsNotNone(m, "no link in a block that moves")
                first, alpha, level = m["first"], m["alpha"], m["level"]
                for x in (first, alpha, level):
                    self.assertIsNotNone(x, m)
                    self.assertTrue(x["open"], m)
                self.assertNotEqual(first["at"], alpha["at"], m)      # its block moved in the page
                self.assertEqual(first["at"], level["at"], m)
                for x in (alpha, level):                             # beside its link, as it was
                    self.assertAlmostEqual(x["dx"], first["dx"], delta=1, msg=m)
                    self.assertAlmostEqual(x["dy"], first["dy"], delta=1, msg=m)
                    self.assertAlmostEqual(x["w"], first["w"], delta=1, msg=m)
                self.assertAlmostEqual(level["top"], first["top"], delta=1, msg=m)


if __name__ == "__main__":
    unittest.main(verbosity=2)
