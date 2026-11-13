"""Site decisions 130 (2026-10-25): the mini's header carries its own language tags, loading and loaded (headless Edge).

Found by the rowgloss116 flake: `mini.js` `header()` drew the header with no `lang` of its own, so
it took whatever surrounded it. While the target's article was loading it sat in the line the link
was on, and the English gloss of a Norwegian line's link was tagged `nb`. Once the body was in it
took the mini's `lang` (the target article's), and a Norwegian headword in an English mini was
tagged `en`. Nothing on screen changed, but a screen reader reads each word in the tagged language.
The fix (Robin's go): the headword is tagged `nb` when it is the Norwegian face (the link's own
word, or the peek after a partner word's swap), and `en` only for an English word with no peek.
Every gloss is tagged `en`.

Through `browser/minilang130.js`, every request delayed 400 ms through CDP, the header read in the
click's own task (`aria-busy` set) and again once the body is in:

* *hus* (24627), *bosted* on the Norwegian line: headword `nb`, gloss " — place of residence · dwelling
  place" `en` (both pieces);
* *hus*, "place of residence" on the English line (a partner word; swapped): headword *bosted* `nb`,
  gloss `en`;
* *hus*, the same partner link with its peek removed in the page (no built page has an English link
  with no peek): headword "place of residence" `en`, no gloss;
* *stø* II (58037, untranslated): *lene* (II) (a bare link, its target's English glosses): headword
  `nb`, gloss `en`; *stø* (IV, 1) (one sense, `ordpar-nbdef`: the header the headword alone) and
  *skorde* (I, 1) (no peek): headword `nb`, no gloss.

The header's headword may carry its sound icon (decisions 159, 2026-11-02): the header's text is
read without it (its hidden "Play" / "Spill av" is no word of the header), and the icon is checked
to sit beside the headword, outside its `lang` part, with its English label `en` and its Norwegian
`nb`.

`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before 130's deploy it fails:
the loading reading on the gloss, `nb`, and the loaded one on the headword, `en`). Skipped without
Edge, bun or a build.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

LATENCY = 400
HUS, STO = 24627, 58037


def _find(href, xen=None):
    """A JS expression: the first article link to `href` outside any mini; `xen` True for the
    English line's partner word, False for anything else (the Norwegian line's link)."""
    cond = "" if xen is None else (" && %sa.parentNode.classList.contains('ordpar-xen')"
                                   % ("" if xen else "!"))
    return ("[...document.querySelectorAll('a.ordbok-xword')].find(a => a.getAttribute('href') === %r"
            " && !a.closest('.ordbok-xmini')%s)" % (href, cond))


CASES = [
    {"name": "nb-line", "page": HUS, "find": _find("/bm-en/7136/", xen=False)},
    {"name": "en-partner", "page": HUS, "find": _find("/bm-en/7136/", xen=True)},
    {"name": "en-nopeek", "page": HUS, "find": _find("/bm-en/7136/", xen=True), "unpeek": True},
    {"name": "untr-bare", "page": STO, "find": _find("/bm-en/34820/")},
    {"name": "untr-sense", "page": STO, "find": _find("/bm-en/58039/#def2")},
    {"name": "untr-nopeek", "page": STO, "find": _find("/bm-en/53420/#def2")},
]
# name -> (headword text, its lang, the header's whole text)
WANT = {
    "nb-line": ("bosted", "nb", "bosted — place of residence · dwelling place"),
    "en-partner": ("bosted", "nb", "bosted — place of residence"),
    "en-nopeek": ("place of residence", "en", "place of residence"),
    "untr-bare": ("lene (II)", "nb", "lene (II) — to lean · to rest, to prop (something) against"),
    "untr-sense": ("stø (IV, 1)", "nb", "stø (IV, 1)"),
    "untr-nopeek": ("skorde (I, 1)", "nb", "skorde (I, 1)"),
}

SITE = None
RESULT = {}
SKIP = harness.skip_reason()


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_minilang130: skipped —", SKIP)
        return
    SITE = harness.Site()
    RESULT.update(SITE.check("minilang130.js", dict(latency=LATENCY, cases=CASES,
                                                    shot=os.environ.get("ORDPAR_MINILANG_SHOT", ""))))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class HeaderLanguages(unittest.TestCase):

    def check(self, name):
        c = [c for c in RESULT["cases"] if c["name"] == name][0]
        where = "%s on %s (page %s)" % (name, RESULT["base"], c["page"])
        self.assertTrue(c["found"], "no link for " + where)
        hw, hw_lang, text = WANT[name]
        self.assertTrue(c["busy"]["busy"], "the first reading was not while loading: %s %r" % (where, c["busy"]))
        self.assertIsNotNone(c["loaded"], "the mini's body never came: " + where)
        wrong = []          # every wrong tag in both readings, so a failure names them all
        for when in ("busy", "loaded"):
            r = c[when]
            self.assertEqual(r["text"], text, "%s, %s" % (where, when))
            self.assertEqual(r["hw"]["text"], hw, "%s, %s" % (where, when))
            if text != hw:
                self.assertTrue(r["gloss"], "%s, %s: no gloss" % (where, when))
            if r["hw"]["lang"] != hw_lang:
                wrong.append("%s: headword %r tagged %r, not %r" % (when, hw, r["hw"]["lang"], hw_lang))
            wrong += ["%s: gloss piece %r tagged %r, not 'en'" % (when, g["t"], g["lang"])
                      for g in r["gloss"] if g["lang"] != "en"]
            # the headword's sound icon (decisions 159): beside the headword, not in its tagged
            # part, and each label in its own language
            for b in r.get("play", []):
                if b["inHw"] or b["en"] != "en" or b["nb"] != "nb":
                    wrong.append("%s: the header's icon %r (want outside the headword, labels 'en' and 'nb')"
                                 % (when, b))
        self.assertEqual(wrong, [], where)

    def test_a_norwegian_line(self):
        self.check("nb-line")

    def test_b_english_partner_swapped(self):
        self.check("en-partner")

    def test_c_english_link_without_peek(self):
        self.check("en-nopeek")

    def test_d_untranslated_bare_link(self):
        self.check("untr-bare")

    def test_e_untranslated_sense_link(self):
        self.check("untr-sense")

    def test_f_untranslated_link_without_peek(self):
        self.check("untr-nopeek")


if __name__ == "__main__":
    unittest.main()
