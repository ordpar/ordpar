"""Site decisions 187 (2026-11-15): the CEFR level box in headless Edge (`browser/levels187.js`), on a
computer (clicked) and a phone (tapped), over pages this test renders with the levels.

* **Settings**: "CEFR level after the headword" right after "What the eye at the headword hides",
  under Article's Language, Off then On, Off checked with nothing stored; its "?" box links to Help's
  `#cefr-levels`; On stores `levels` = on; the preset Default leaves it off, For learners turns it on.
* **Off** (the default): no box drawn on *hus*, and the heading's accessible name without a level.
* **On**: the head script's class on <html> before the first box is parsed (nothing moves on load);
  on *hus* the box the last thing in the `h1`, after the sound icon where the page has one, on the
  headword's line, its letters the level of `ordpar/levels.tsv`, the tooltip the level's, the
  letters `aria-hidden`, the heading's name carrying ", level A1" and the letters once; the Quiet
  box's look (12 px, weight 600, a 1 px solid outline in the muted grey of `--ordpar-muted`,
  radius 3 px, not selectable), day and night; every set phrase's term with its own box last,
  after its icon, on the term's line; off again in place, none drawn. *bein, ben* (5026): after the
  second spelling; *omkjøring* (42134, Norwegian only) and *uteområde* (128786, no definition):
  theirs.
* **The address**: `#levels=on` shows the box, nothing stored, the pair taken off the address.
* **Every article shown whole**: the word page *vindu* (68472), each full result of *fisk* (list view off;
  fisk I A1, fisk II C), an article opened in a list row (none on the rows).
* **A small article** (*hjem* I on *hus*): no box.

The overlay (`ORDPAR_TEST_OVERLAY`, laid over `ordpar/out/` by the harness): the pages above rendered
through `build_site.Builder` with `ordpar/levels.tsv` (and the clip names in
`.cache/ordpar-audio-names.tsv` where that file is here, so the sound icons show), the working tree's
`/site/` files written as the build writes them (`build_site.write_assets`, `write_strings`) and the
shell pages (`build_index.copy_shell`). `ORDPAR_TEST_SHOTS=<folder>` saves the head and the set
phrases of *hus* (light and night) and the head of *bein, ben*. Skipped without Edge, bun, a build or
the mirror.
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

IDS = (24627, 5026, 42134, 128786, 14903, 14904, 23742, 68472)
NAMES = os.path.join(L.REPO, ".cache", "ordpar-audio-names.tsv")
SITE = None
RESULTS = {}
OWN = None
SKIP = harness.skip_reason() or (None if L.mirror_path() else "no mirror (ordpar/local-paths.json `mirror`)")


def make_overlay():
    from ordpar import build_site, build_index
    from ordpar.sitegen import audio, page
    d = tempfile.mkdtemp(prefix="ordpar-levels187-")
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
    return d, {str(aid): b.levels[aid] for aid in IDS}


def setUpModule():
    global SITE, OWN
    if SKIP:
        print("test_ordpar_browser_levels187: skipped —", SKIP)
        return
    OWN, levels = make_overlay()
    if harness.OVERLAY:
        print("test_ordpar_browser_levels187: its own overlay %s, not %s" % (OWN, harness.OVERLAY))
    harness.OVERLAY = OWN
    SITE = harness.Site()
    shots = os.environ.get("ORDPAR_TEST_SHOTS")
    for mobile in (False, True):
        a = {"mobile": mobile, "levels": levels}
        if shots:
            a["shots"] = {"dir": shots.replace("\\", "/"), "prefix": "phone-390" if mobile else "computer-1280"}
        RESULTS["phone" if mobile else "computer"] = SITE.check("levels187.js", a)


def tearDownModule():
    if SITE:
        SITE.close()
    if OWN:
        shutil.rmtree(OWN, ignore_errors=True)


@unittest.skipIf(SKIP, SKIP or "")
class Levels(unittest.TestCase):

    def each(self):
        for n, r in RESULTS.items():
            yield n, r["cases"], r["levels"]

    def test_a_the_setting(self):
        for n, c, _lv in self.each():
            with self.subTest(n):
                s = c["settings"]
                self.assertEqual((s["before"], s["title"], s["sub"], s["choices"], s["checked"]),
                                 ("exeyewhat", "CEFR level after the headword", "Language", ["Off", "On"], ["off"]), s)
                self.assertTrue(s["shown"] and s["hint"], s)
                self.assertEqual((c["hintBox"]["href"], c["hintBox"]["link"]),
                                 ("/help/#cefr-levels", "More about the levels in Help"), c["hintBox"])
                self.assertIn("C covers both C1 and C2", c["hintBox"]["text"])
                self.assertEqual(c["storedOn"], "on")
                self.assertEqual((c["presetDefault"], c["presetLearners"]), ("off", "on"))

    def test_b_off_nothing_drawn_nothing_read(self):
        for n, c, _lv in self.each():
            with self.subTest(n):
                self.assertGreater(c["off"]["boxes"], 1)            # the page carries them
                self.assertEqual((c["off"]["shown"], c["off"]["cls"]), (0, False))
                self.assertNotIn("level", c["offName"] or "")
                self.assertEqual((c["offInPlace"]["shown"], c["offInPlace"]["cls"]), (0, False))

    def test_c_on_the_headword(self):
        for n, c, lv in self.each():
            with self.subTest(n):
                self.assertIs(c["paint"], True)
                h = c["hus"]["head"]
                want = lv["24627"]
                self.assertEqual((h["level"], h["text"], h["hidden"], h["sr"]), (want, want, "true", ", level " + want))
                self.assertEqual(h["title"], L.TIPS[want])
                self.assertTrue(h["shown"] and h["last"] and h["sameLine"], h)
                if h["prev"] and "ordpar-play" in h["prev"]:
                    self.assertTrue(h["afterPrev"], h)
                name = c["husName"] or ""
                self.assertIn(", level " + want, name)
                self.assertEqual(name.count(want), 1, name)

    def test_d_the_quiet_box_day_and_night(self):
        for n, c, _lv in self.each():
            with self.subTest(n):
                for k, colour in (("hus", "rgb(117, 112, 112)"), ("husNight", "rgb(185, 182, 182)")):
                    h = c[k]["head"]
                    self.assertEqual((h["fontSize"], h["weight"], h["border"], h["radius"], h["select"]),
                                     ("12px", "600", "1px solid", "3px", "none"), (k, h))
                    self.assertEqual((h["colour"], h["borderColour"]), (colour, colour), (k, h))
                    self.assertEqual(h["padding"], "2.4px 4.56px", (k, h))
                self.assertEqual(c["hus"]["muted"].lower(), "#757070")
                self.assertEqual(c["husNight"]["muted"].lower(), "#b9b6b6")

    def test_e_each_set_phrase(self):
        for n, c, _lv in self.each():
            with self.subTest(n):
                terms = c["hus"]["terms"]
                self.assertGreater(len(terms), 5)
                for t in terms:
                    self.assertIsNotNone(t)
                    self.assertTrue(t["shown"] and t["last"] and t["sameLine"], t)
                    self.assertEqual(t["sr"], ", level " + t["level"])
                    self.assertEqual(t["fontSize"], "12px")
                    if t["prev"] and "ordpar-play" in t["prev"]:
                        self.assertTrue(t["afterPrev"], t)

    def test_f_two_spellings_norwegian_only_no_definition(self):
        for n, c, lv in self.each():
            with self.subTest(n):
                for aid in ("5026", "42134", "128786"):
                    h = c["a" + aid]["head"]
                    self.assertEqual(h["level"], lv[aid], aid)
                    self.assertTrue(h["shown"] and h["last"] and h["sameLine"], (aid, h))

    def test_g_the_address(self):
        for n, c, lv in self.each():
            with self.subTest(n):
                self.assertEqual(c["address"]["head"]["level"], lv["24627"])
                self.assertTrue(c["address"]["head"]["shown"])
                self.assertIsNone(c["addressStored"])
                self.assertEqual(c["addressHash"], "")

    def test_h_every_article_shown_whole(self):
        for n, c, lv in self.each():
            with self.subTest(n):
                self.assertEqual(c["word"]["head"]["level"], lv["68472"])
                self.assertTrue(c["word"]["head"]["shown"])
                full = {r["id"]: r for r in c["full"] if r}
                for aid in ("14903", "14904"):
                    self.assertEqual((full[aid]["level"], full[aid]["shown"]), (lv[aid], True), full)
                self.assertEqual(c["rowBoxes"], 0)
                self.assertTrue(c["row"]["head"]["shown"])

    def test_i_never_in_a_small_article(self):
        for n, c, _lv in self.each():
            with self.subTest(n):
                self.assertTrue(c["miniOpened"])
                self.assertEqual(c["miniBoxes"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
