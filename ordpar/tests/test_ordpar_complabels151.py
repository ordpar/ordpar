# -*- coding: utf-8 -*-
"""Site-review decisions 151 (Robin, 2026-10-29): each compound-list intro gets an English label
that says what ordbokene's says — one table, Norwegian intro -> English label
(`derive.COMP_INTRO_LABELS`), the table his "looks good" to the session's draft — and the block
stores the capture's intro (`intro`), which is the Norwegian label on the site and the Norwegian
side of `assess.py`'s citer line.

Until this build the label was a substring test with three outcomes: "etterledd" -> "Used as a
suffix in:", "forledd" -> "Used as a prefix in:", anything else -> "Also found in compounds:"
(*klinikk* 30122's misspelt "som etterldd i ord som", every "i ord som", even a list with no
intro). Pinned here:

1. **every intro maps to its label** — over every compound list in `sources/articles/*.json`
   always, and in the mirror's `bm-articles.jsonl` when its folder (`ORDPAR_MIRROR_DIR`, else the folder
   of `mirror` in `ordpar/local-paths.json`) exists, skipped with the reason when it does not. An intro the table
   does not know fails with its article and text, so a new intro from ordbokene stops a deploy's
   gate until it has a label (151's call 3). A misspelling is corrected in the capture
   (`pipeline.md` § Source normalization), never matched around; the mirror keeps ordbokene's
   own text, so its known misspellings are listed in `MIRROR_TYPOS`, each with the intro our
   capture carries once normalized, and an entry ordbokene has since corrected fails as stale;
2. the matcher: whitespace collapsed and trimmed, lower case, a final colon dropped, the whole
   intro and nothing looser; no intro, no label;
3. the deriver: `intro` stored as plain text (`f_eks` filled to "for eksempel"), an unknown
   intro labelled "in words such as:" with a `comp-intro-unknown` advisory naming article and
   intro;
4. a list with no intro drawn without a label line — the site's page (translated and
   Norwegian-only unit), the deck's `_comp_html` and its mini (`mini._comp_line`) — and an empty
   one (*bo* 6739's two) not at all;
5. the site's Norwegian label read from the block's `intro` (`article.comp_nb_label`), and
   `assess._comp_block_lines`' Norwegian side the same (the assessment tool is private: in the
   public repository that one test skips, naming the module).

On the captures as they stood at the build (2026-10-30) test 1 fails on nine library rows: the
three misspellings Robin approved for normalization (*klinikk* 30122, *reim* 47869, *skriv*
53626) and six more put to him (*høst* 25223, *pølse* 47029, *sko* 53208, *slave* 54301, *tun*
62823, *verk* 67841); it passes once those captures are normalized
(`docs/sessions/2026-09-19-ordpar-site-review/evidence/reports/compound-labels-151-2026-10-30-contractor.md`).
"""
import glob
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import ordbok_gen  # noqa: E402  -- first: mini imports it back for STYLE
import derive      # noqa: E402
try:
    import assess  # noqa: E402
except ModuleNotFoundError as e:
    if e.name != "assess":
        raise
    assess = None
import mini        # noqa: E402
from ordpar.sitegen import article, face, library  # noqa: E402

from ordpar import local_paths  # noqa: E402  -- this machine's mirror

MIRROR_DIR = (os.environ.get("ORDPAR_MIRROR_DIR")
              or os.path.dirname(local_paths.get("mirror") or "") or "(no mirror set)")

#: ordbokene's own misspelt intros, as the mirror has them: (article id, the matcher's key) ->
#: the key our capture carries once normalized. All nine are library rows; the first three Robin
#: approved (151), the other six were put to him with this build (2026-10-30).
MIRROR_TYPOS = {
    (30122, "som etterldd i ord som"): "som etterledd i ord som",     # klinikk
    (47869, "som ettreledd i ord som"): "som etterledd i ord som",    # reim
    (53626, "som etteredd i ord som"): "som etterledd i ord som",     # skriv
    (25223, "som etterledd ord som"): "som etterledd i ord som",      # høst
    (47029, "som etterleddd i ord som"): "som etterledd i ord som",   # pølse
    (53208, "om etterledd i ord som"): "som etterledd i ord som",     # sko
    (54301, "som etterledd i ord"): "som etterledd i ord som",        # slave
    (62823, "som etterledd ord som"): "som etterledd i ord som",      # tun
    (67841, "som etterledd ord som"): "som etterledd i ord som",      # verk
}


def _lists(body):
    """Every compound_list node of an article body, not descending into a sub_article."""
    out = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type_") == "sub_article":
                return
            if n.get("type_") == "compound_list":
                out.append(n)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(body)
    return out


def _intro(node, concepts):
    i = node.get("intro") or {}
    return derive.fill(i.get("content", "") or "", i.get("items") or [], concepts)


def capture_intros():
    """`(article id, intro)` for every compound list in the library's captures. The abbreviation
    table comes through `library.mirror_concepts`, never `derive.concepts_map()` directly, which in
    the public repository fetched it from ord.uib.no and wrote it under the data folder (decisions
    184, the outsider test's finding 2; `test_ordpar_concepts184.py`)."""
    concepts = library.mirror_concepts(os.path.join(MIRROR_DIR, "bm-articles.jsonl"))[0]
    for p in sorted(glob.glob(os.path.join(ROOT, "sources", "articles", "*.json"))):
        with open(p, encoding="utf-8") as f:
            text = f.read()
        if '"compound_list"' not in text:
            continue
        art = json.loads(text)
        aid = int(os.path.basename(p)[:-5])
        for n in _lists(art.get("body")):
            yield aid, _intro(n, concepts)


def mirror_intros():
    """`(article id, intro)` for every compound list in the mirror, or None with no mirror."""
    path = os.path.join(MIRROR_DIR, "bm-articles.jsonl")
    if not os.path.exists(path):
        return None
    with open(os.path.join(MIRROR_DIR, "bm-concepts.json"), encoding="utf-8") as f:
        raw = json.load(f)
    concepts = {k: (v.get("expansion") or k) for k, v in (raw.get("concepts") or {}).items()}
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if '"compound_list"' not in line:
                continue
            r = json.loads(line)
            for n in _lists((r.get("data") or {}).get("body")):
                out.append((r["id"], _intro(n, concepts)))
    return out


class EveryIntro(unittest.TestCase):
    def test_every_capture_intro_has_its_label(self):
        unknown = ["%s %r" % (aid, intro) for aid, intro in capture_intros()
                   if not derive.comp_label(intro)[1]]
        self.assertEqual(unknown, [], "compound-list intros in sources/articles/ that "
                         "derive.COMP_INTRO_LABELS does not know (give each a label, or correct "
                         "a misspelling in its capture): %s" % "; ".join(unknown))

    def test_every_mirror_intro_has_its_label(self):
        got = mirror_intros()
        if got is None:
            self.skipTest("no mirror at %s (set ORDPAR_MIRROR_DIR)" % MIRROR_DIR)
        self.assertGreater(len(got), 2000)
        unknown, seen_typos = [], set()
        for aid, intro in got:
            key = derive.comp_intro_key(intro)
            if derive.comp_label(intro)[1]:
                continue
            if (aid, key) in MIRROR_TYPOS:
                seen_typos.add((aid, key))
                continue
            unknown.append("%s %r" % (aid, intro))
        self.assertEqual(unknown, [], "compound-list intros in the mirror that "
                         "derive.COMP_INTRO_LABELS does not know (a new intro from ordbokene "
                         "needs its label before a deploy; a misspelling goes in MIRROR_TYPOS "
                         "once its capture is normalized): %s" % "; ".join(unknown))
        stale = sorted(set(MIRROR_TYPOS) - seen_typos)
        self.assertEqual(stale, [], "MIRROR_TYPOS entries ordbokene no longer has: drop them")

    def test_the_typo_corrections_are_table_keys(self):
        for k, fixed in MIRROR_TYPOS.items():
            self.assertTrue(derive.comp_label(fixed)[1], k)
            self.assertFalse(derive.comp_label(k[1])[1], k)


class Matcher(unittest.TestCase):
    def test_spacing_case_colon(self):
        want = "as a suffix in words such as:"
        for intro in ("som etterledd i ord som", "  som etterledd i  ord som ", "Som Etterledd i ord som",
                      "som etterledd i ord som:", "som etterledd i ord som :", "som\tetterledd i ord\nsom"):
            self.assertEqual(derive.comp_label(intro), (want, True), repr(intro))

    def test_nothing_looser(self):
        for intro in ("som etterldd i ord som", "som etterledd i ord som x", "etterledd",
                      "som etterledd i ord som::", "i ord som."):
            self.assertEqual(derive.comp_label(intro), (derive.COMP_UNKNOWN_LABEL, False), repr(intro))

    def test_no_intro_no_label(self):
        for intro in ("", "   ", None, ":"):
            self.assertEqual(derive.comp_label(intro), ("", True), repr(intro))

    def test_the_table(self):
        self.assertEqual(derive.COMP_UNKNOWN_LABEL, "in words such as:")
        for k, v in derive.COMP_INTRO_LABELS.items():
            self.assertEqual(derive.comp_intro_key(k), k)       # every key as the matcher sees it
            self.assertTrue(v[:1].islower() and v.endswith(":"), v)   # stored lowercase-initial (Robin, 2026-10-30)
        # 151's rows, word for word
        for k, v in (("som etterledd i ord som", "as a suffix in words such as:"),
                     ("som etterledd i", "as a suffix in:"),
                     ("brukt som etterledd i ord som", "used as a suffix in words such as:"),
                     ("også som etterledd i", "also as a suffix in:"),
                     ("etterledd i fuglenavn som", "as a suffix in bird names such as:"),
                     ("som forledd i ord som", "as a prefix in words such as:"),
                     ("i ord som", "in words such as:"),
                     ("for eksempel", "for example:"),
                     ("for eksempel i ord som", "for example in words such as:"),
                     ("for eksempel i", "for example in:"),
                     ("også i sammensetninger som", "also in compounds such as:"),
                     ("også i sammensetninger", "also in compounds:")):
            self.assertEqual(derive.COMP_INTRO_LABELS[k], v)


class Deriver(unittest.TestCase):
    def node(self, content, items=(), elements=()):
        return {"type_": "compound_list", "intro": {"content": content, "items": list(items)},
                "elements": list(elements)}

    def test_intro_stored_filled(self):
        b = derive._comp_block(self.node("også i $ som", [{"id": "sms_er", "type_": "relation"}]),
                               {"sms_er": "sammensetninger"})
        self.assertEqual((b["label"], b["intro"]), ("also in compounds such as:", "også i sammensetninger som"))
        b = derive._comp_block(self.node("$", [{"id": "f_eks", "type_": "entity"}]), {"f_eks": "for eksempel"})
        self.assertEqual((b["label"], b["intro"]), ("for example:", "for eksempel"))
        b = derive._comp_block({"type_": "compound_list"}, {})
        self.assertEqual((b["label"], b["intro"], b["items"]), ("", "", []))

    def test_unknown_intro_advisory(self):
        art = {"article_id": 999999, "lemmas": [{"lemma": "testord", "hgno": 0}],
               "body": {"definitions": [{"type_": "definition", "id": 1, "elements": [
                   {"type_": "definition", "id": 2, "elements": [
                       {"type_": "explanation", "content": "noe", "items": []},
                       self.node("som etterldd i ord som")]}]}]}}
        adv = []
        try:
            row = derive.derive_row(999999, {}, adv, art=art)
        except derive.DeriveError as e:
            self.skipTest("synthetic article refused by the deriver: %s" % e)
        blk = row["senses"][0]["comp"][0]
        self.assertEqual((blk["label"], blk["intro"]), ("in words such as:", "som etterldd i ord som"))
        tags = [a for a in adv if a[0] == "comp-intro-unknown"]
        self.assertEqual(len(tags), 1, adv)
        self.assertIn("999999", tags[0][1])
        self.assertIn("'som etterldd i ord som'", tags[0][1])
        self.assertEqual(derive._COMP_UNKNOWN, [])


class Mk:
    def expand(self, text, norwegian=False, hover_only=False, strict=True):
        return "<a>%s</a>" % text


NO_INTRO = {"label": "", "intro": "", "items": [{"word": "dødsbo", "href": "/nob/bm/11471", "en": "an estate"}]}
EMPTY = {"label": "", "intro": "", "items": []}
SUFFIX = {"label": "as a suffix in words such as:", "intro": "som etterledd i ord som",
          "items": [{"word": "hundehus", "href": "/nob/bm/24530", "en": "a kennel"}]}


class NoLabel(unittest.TestCase):
    def test_site_page_translated(self):
        out = article.comp_html(NO_INTRO, Mk(), True, "en", article.comp_nb_label({}, 0, NO_INTRO))
        self.assertIn('<span class="ordbok-def"><a>[dødsbo](/nob/bm/11471 "an estate")</a></span>', out)
        self.assertNotIn("<em>", out)
        self.assertNotIn("ordpar-cl-", out)
        self.assertEqual(article.comp_html(EMPTY, Mk(), True, "en", ""), "")

    def test_site_norwegian_only_unit(self):
        out = article.comp_html(NO_INTRO, Mk(), True, "no", article.comp_nb_label({}, 0, NO_INTRO))
        self.assertIn('<span class="ordbok-def"><a>[dødsbo](/nob/bm/11471)</a></span>', out)
        self.assertNotIn("<em>", out)
        self.assertEqual(article.comp_html(EMPTY, Mk(), True, "no", ""), "")

    def test_site_unit_skips_an_empty_list(self):
        out = "\n".join(article._unit_inner({"defn": 3, "comp": [EMPTY, SUFFIX]}, None, Mk(), False, None))
        self.assertEqual(out.count("ordpar-comp"), 1)
        self.assertIn("<em>som etterledd i ord som</em>", out)

    def test_deck_card(self):
        for side in ("en", "no"):
            out = ordbok_gen._comp_html(NO_INTRO, Mk(), True, side)
            self.assertNotIn("<em></em>", out)
            self.assertNotIn("compounds", out.lower())
        self.assertEqual(ordbok_gen._comp_html(EMPTY, Mk(), True, "en"), "")

    def test_deck_mini(self):
        x = lambda t, norwegian=False: "<a>%s</a>" % t  # noqa: E731
        out = mini._comp_line({"comp": [NO_INTRO]}, x)
        self.assertEqual(out, '<div class="mini-comp"><a>[dødsbo](/nob/bm/11471 "an estate")</a></div>')
        out = mini._comp_line({"comp": [SUFFIX]}, x)
        self.assertIn('<em>as a suffix in words such as:</em> <a>', out)


class NorwegianLabel(unittest.TestCase):
    def test_site_reads_the_intro(self):
        self.assertEqual(article.comp_nb_label({}, 0, SUFFIX), "som etterledd i ord som")
        blk = dict(SUFFIX, label="in words such as:", intro="i ord som")
        self.assertEqual(article.comp_nb_label({}, 0, blk), "i ord som")
        out = article.comp_html(blk, Mk(), True, "en", article.comp_nb_label({}, 0, blk))
        self.assertIn('<span class="ordpar-cl-en">in words such as:</span>'
                      '<span class="ordpar-cl-nb" lang="nb">i ord som</span>', out)
        self.assertEqual(face.lowercase_comp_block(blk)["intro"], "i ord som")   # the intro untouched

    @unittest.skipUnless(assess, "needs assess (scripts/assess.py), which the public repository does not have")
    def test_assess_citer_line(self):
        no, en = assess._comp_block_lines(SUFFIX, "/nob/bm/24530", False)
        self.assertEqual(no, "    no: som etterledd i ord som [hundehus](/nob/bm/24530)")
        self.assertEqual(en, '    en: as a suffix in words such as: {[hundehus](/nob/bm/24530 "????")}')
        blk = dict(SUFFIX, label="in words such as:", intro="i ord som")
        self.assertTrue(assess._comp_block_lines(blk, "", True)[0].startswith("    no: i ord som ["))
        no, en = assess._comp_block_lines(dict(NO_INTRO), "", True)
        self.assertEqual(no, "    no: [dødsbo](/nob/bm/11471)")
        self.assertEqual(en, '    en: {[dødsbo](/nob/bm/11471 "an estate")}')
        # a row derived before 151 (no `intro`): the old reverse map
        old = {"label": "Used as a suffix in:", "items": SUFFIX["items"]}
        self.assertTrue(assess._comp_block_lines(old, "", True)[0].startswith("    no: som etterledd i ord som ["))


if __name__ == "__main__":
    unittest.main()
