# -*- coding: utf-8 -*-
"""Pins the follow-up build of 2026-10-23 (site decisions 93's follow-up, 86, 97, 98; brief
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-followup-93-97-98-2026-10-23.md`).

1. **One numeral look (93 (1)).** A homograph numeral in a row — the list view, favourites,
   inflected-form rows, the suggestions' and history's numbered glosses — carries the article's
   own class, `.ordbok-homograph`, beside `.ordpar-hg`, whose only rule left is `line-height: 0`
   so no row grows. The look itself since decisions 105 (2026-10-23): 0.60 of the headword, the
   muted grey (`--ordpar-muted`, light and night), weight 600, raised 0.14 em; 0.80 em of the
   gloss text in a gloss list. (Raised, maroon, bold and 0.7 em until then.)
2. **Our lemma order (93 (2)).** The normalization log's header lemma-order rulings
   (`review/source-normalizations.jsonl`) put the mirror's lemmas in our order
   (`sitegen.lemma_order`) wherever the site reads them — `Mirror.data` (the headword line, the
   inflection table) and `build_index.entry` (the index's display text and numbers); the page
   `<title>`, `data-lemma` and the "N more entries" link follow the headword line
   (`build_site.head_lemmas`); a favourite stored in the old order is redrawn from the index
   (`lookup.js` `redrawFrom`).
3. **The About sentence (93 (3)).**
4. **The Recent rows capped above a phone's keyboard (86)**, as the suggestions are.
5. **The mini's defaults (97):** `minispacing` defaults to `article` (`compact` a class of its
   own, so a stored "compact" keeps its look and nothing stored gets the article's spacing); the
   header's gloss in the text colour.
6. **The sense numbers (98):** a bulleted subsense (`display: list-item`) no longer advances the
   senses list's `list-item` counter.

The JS runs under bun (or node) against the real `lookup.js` over a synthetic index, with the
harness of `test_ordpar_homograph93.py`. Skipped when neither runner is on PATH."""

import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_index as B  # noqa: E402
from ordpar import build_site  # noqa: E402
from ordpar.sitegen import about, article, head, lemma_order, mirror, page  # noqa: E402
import test_ordpar_homograph93 as H93  # noqa: E402  (its rows, its lookup.js harness)


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _lem(lemma, hg, *tags):
    return {"lemma": lemma, "hgno": hg, "paradigm_info": [{"tags": list(tags) or ["VERB"]}]}


TORE = {"lemmas": [_lem("tore", 2), _lem("tørre", 2)]}


# --- 1. one numeral look -------------------------------------------------------------------

class NumeralLook(unittest.TestCase):
    css = page.article_css()
    shell_css = _read(SITE, "shell.css")

    def test_rows_take_the_articles_class(self):
        self.assertIn("el('span', 'ordbok-homograph ordpar-hg', roman(hg))", _read(SITE, "lookup.js"))
        self.assertIn("el('span', 'ordbok-homograph ordpar-hg', ROMAN[s.hg] || String(s.hg))",
                      _read(SITE, "shell.js"))
        for f in ("lookup.js", "shell.js", "personal-page.js", "mini.js"):
            self.assertNotIn("'ordpar-hg'", _read(SITE, f), f)

    def test_the_articles_look_is_unscoped(self):
        rule = re.search(r"(^|[}\n])\.ordbok-homograph\{([^}]*)\}", self.css)
        self.assertTrue(rule)
        for d in ("font-weight:600", "vertical-align:.14em", "font-size:.6em",
                  "color:var(--ordpar-muted,#757070)"):
            self.assertIn(d, rule.group(2))
        for d in ("700", "super", "maroon"):
            self.assertNotIn(d, rule.group(2))
        # the article's headword line: beside the 1.9 em lemma, so scaled to it (decisions 105)
        self.assertIn(".ordbok-head .ordbok-homograph{font-size:calc(.6*1.9em)}", self.css)
        night = re.search(r"\.nightMode \.ordbok-homograph\{([^}]*)\}", self.css)
        self.assertTrue(night)
        self.assertEqual(night.group(1), "color:var(--ordpar-muted,#b9b6b6)")
        self.assertNotRegex(self.css, r"\.nightMode \.ordbok-homograph,")   # out of the near-white group

    def test_the_gloss_lists_own_size(self):
        self.assertIn(".ordpar-option-gl .ordbok-homograph { font-size: 0.8em; }", self.shell_css)

    def test_ordpar_hg_keeps_only_the_line_height(self):
        bodies = re.findall(r"([^{}]*\.ordpar-hg[^{}]*)\{([^}]*)\}", self.shell_css)
        self.assertEqual([b.strip() for _s, b in bodies], ["line-height: 0;"])
        self.assertNotIn("font-weight: 400", "".join(b for _s, b in bodies))


# --- 2. our lemma order --------------------------------------------------------------------

class LogReading(unittest.TestCase):

    def test_the_four_header_rulings(self):
        got = lemma_order.read_log()
        self.assertEqual(got.get(61543), "tørre, tore")
        self.assertEqual(got.get(554), "aksjemegler, aksjemekler")
        self.assertEqual(got.get(11828), "eiendomsmegler, eiendomsmekler")
        self.assertEqual(got.get(18893), "gæren, galen")
        self.assertNotIn(37693, got)            # a compound list's faces, not a header

    def test_a_missing_log_is_no_rulings(self):
        self.assertEqual(lemma_order.read_log(os.path.join(tempfile.gettempdir(), "no-such.jsonl")), {})

    def test_the_last_line_wins_and_other_kinds_are_skipped(self):
        tmp = tempfile.mkdtemp(prefix="lo93-")
        try:
            p = os.path.join(tmp, "log.jsonl")
            with open(p, "w", encoding="utf-8") as fh:
                for e in ({"article": 1, "kind": "lemma-order", "where": "top-level lemmas order (the article header)", "after": "a, b"},
                          {"article": 1, "kind": "lemma-order", "where": "top-level lemmas order (the article header)", "after": "b, a"},
                          {"article": 2, "kind": "lemma-order", "where": "sense 2 compound list", "after": "x, y"},
                          {"article": 3, "kind": "spelling", "where": "top-level lemmas", "after": "q"}):
                    fh.write(json.dumps(e) + "\n")
            self.assertEqual(lemma_order.read_log(p), {1: "b, a"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Reorder(unittest.TestCase):

    def test_each_spelling_keeps_its_lemma(self):
        data = {"lemmas": [_lem("lysing", 1, "NOUN"), _lem("lysning", 2, "NOUN")], "other": 1}
        got = lemma_order.reorder(5, data, after="lysning, lysing")
        self.assertEqual([(l["lemma"], l["hgno"]) for l in got["lemmas"]], [("lysning", 2), ("lysing", 1)])
        self.assertEqual(got["other"], 1)
        self.assertEqual(data["lemmas"][0]["lemma"], "lysing")       # never in place

    def test_no_ruling_is_the_same_object(self):
        self.assertIs(lemma_order.reorder(0, TORE), TORE)            # no article 0 in the log

    def test_a_ruling_that_matches_no_order_is_not_applied(self):
        lemma_order.unmatched.discard(7)
        self.assertIs(lemma_order.reorder(7, TORE, after="tørre, tore, toere"), TORE)
        self.assertIn(7, lemma_order.unmatched)

    def test_a_spelling_listed_twice_keeps_its_lemmas_together_in_order(self):
        data = {"lemmas": [_lem("a", 1), _lem("b", 1), _lem("a", 2)]}
        got = lemma_order.reorder(8, data, after="b, a")
        self.assertEqual([(l["lemma"], l["hgno"]) for l in got["lemmas"]], [("b", 1), ("a", 1), ("a", 2)])

    def test_a_form_with_a_comma_is_matched_whole(self):
        data = {"lemmas": [_lem("snipp, snapp, snute", 0), _lem("x", 0)]}
        got = lemma_order.reorder(9, data, after="x, snipp, snapp, snute")
        self.assertEqual([l["lemma"] for l in got["lemmas"]], ["x", "snipp, snapp, snute"])


class EveryReader(unittest.TestCase):
    """The real log's 61543 through every reader of the mirror's lemmas."""

    def test_the_headword_line_through_the_mirror(self):
        tmp = tempfile.mkdtemp(prefix="m93-")
        try:
            p = os.path.join(tmp, "bm-articles.jsonl")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": 61543, "data": copy.deepcopy(TORE)}, ensure_ascii=False) + "\n")
                fh.write(json.dumps({"id": 61542, "data": {"lemmas": [_lem("tore", 1, "NOUN")]}},
                                    ensure_ascii=False) + "\n")
            m = mirror.Mirror(p)
            m.index()
            data = m.data(61543)
            self.assertEqual([l["lemma"] for l in data["lemmas"]], ["tørre", "tore"])
            self.assertEqual([l["lemma"] for l in m.row(61543)["data"]["lemmas"]], ["tore", "tørre"])
            h = article.head_html({"lemmas": [], "pos_en": "verb"}, page.EN, data=data)
            self.assertEqual(H93.head_lines(h), ["tørre II, tore II"])
            self.assertEqual(m.data(61542)["lemmas"][0]["lemma"], "tore")    # no ruling: untouched
            m.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_index_entry(self):
        aid, heads, hgnos, _pos, _infl, _n = B.entry(61543, copy.deepcopy(TORE))
        self.assertEqual((heads, hgnos), (["tørre", "tore"], [2, 2]))
        self.assertEqual(B.display(heads), "tørre / tore")

    def test_title_lemma_and_more_link_follow_the_line(self):
        data = lemma_order.reorder(61543, copy.deepcopy(TORE))
        root = {"lemmas": [{"form": "tørre", "homograph": "II"}, {"form": "tore", "homograph": "II"}]}
        head_l = build_site.head_lemmas(root, data)
        self.assertEqual(head_l, [{"form": "tørre", "homograph": "II"}, {"form": "tore", "homograph": "II"}])
        h = page.render(aid=61543, lemmas=head_l, article="<div></div>", translated=True, other_entries=2,
                        strings=page.EN, stamp="x", description="d", mk=None,
                        pos_class="verb", numerals=True)
        # site decisions 128: "word (class) — <dictionary name>", the numerals kept here as where
        # another page shares a spelling and the class (`describe.page_title`)
        self.assertIn("<title>tørre II, tore II (verb) — Norwegian–English dictionary</title>", h)
        self.assertIn('data-lemma="tørre"', h)
        # site decisions 117: the article build links the word's search (`face.lemma_url`); the
        # index build sends it to the word's page where it has one (`wordpages.patch_article`)
        # site decisions 152: the line's words in both languages (the labels setting)
        self.assertIn('<a href="/bm-en/#q=t%C3%B8rre"><span class="ordpar-l-en">2 more entries for tørre</span>', h)

    def test_a_stale_library_row_title_takes_the_mirrors_number(self):
        # 15909 *for*: the library row says IV, the mirror (ordbokene renumbered) III
        root = {"lemmas": [{"form": "for", "homograph": "IV"}]}
        data = {"lemmas": [{"lemma": "for", "hgno": 3, "paradigm_info": [{"tags": ["ADP"]}]}]}
        self.assertEqual(build_site.head_lemmas(root, data), [{"form": "for", "homograph": "III"}])

    def test_a_double_space_is_one_in_the_title(self):
        data = {"lemmas": [{"lemma": "sprenge  grenser", "hgno": 0, "paradigm_info": []}]}
        self.assertEqual(build_site.head_lemmas({"lemmas": [], "pos_en": "fixed expression"}, data),
                         [{"form": "sprenge grenser", "homograph": None}])

    def test_the_page_build_passes_the_line(self):
        src = _read(ORDPAR, "build_site.py")
        self.assertIn("head = head_lemmas(root, data)", src)
        self.assertIn("aid=aid, lemmas=head, article=frag,", src)
        self.assertIn("other_entries=self.mirror.other_entries(aid, [l[\"form\"] for l in head]),", src)


class Index(unittest.TestCase):
    """The JS side over a synthetic index of H93's rows, built with the real log (61543 in
    our order)."""
    JS = H93.IndexNumbers.JS
    js = H93.IndexNumbers.js

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idx93f-")
        p = os.path.join(cls.tmp, "mirror.jsonl")
        with open(p, "w", encoding="utf-8") as fh:
            for r in H93.ROWS:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        heads, forms, cls.words = B.build_tables(p, None, {})
        B.write_index(cls.tmp, heads, forms, cls.words, H93.TRANSLATED, {}, snippets=H93.SNIPPETS)
        cls.dir = os.path.join(cls.tmp, "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_row_draws_the_classes(self):
        got = self.js("""const w = doc.createElement('span');
S.headwordInto(w, { id: 36349, word: 'lysing / lysning', hg: 1, hgs: [1, 2] });
out([].map.call(w.querySelectorAll('.ordpar-hg'), m => [m.className, m.textContent]));""")
        self.assertEqual(got, [["ordbok-homograph ordpar-hg", "I"], ["ordbok-homograph ordpar-hg", "II"]])

    def test_words_in_our_order(self):
        self.assertEqual(self.words[61543], ["tørre / tore", 2, "VERB"])

    def test_redraw_from(self):
        got = self.js("""out([
  S.redrawFrom({ id: 61543, word: 'tore / tørre', hg: 2 }, ['tørre / tore', 2, 'VERB']),
  S.redrawFrom({ id: 61543, word: 'tørre / tore', hg: 2 }, ['tørre / tore', 2, 'VERB']),
  S.redrawFrom({ id: 36349, word: 'lysing / lysning', hg: 1 }, ['lysing / lysning', [1, 2], 'NOUN']),
  S.redrawFrom({ id: 36349, word: 'lysing / lysning', hg: 1, hgs: [1, 2] }, ['lysing / lysning', [1, 2], 'NOUN']),
  S.redrawFrom({ id: 5, word: 'a / b', hg: 0 }, ['a / c', 0, 'NOUN']),
  S.redrawFrom({ id: 5, word: 'a / b', hg: 0 }, null)]);""")
        self.assertEqual(got, [{"id": 61543, "word": "tørre / tore", "hg": 2, "hgs": None}, None,
                               {"id": 36349, "word": "lysing / lysning", "hg": 0, "hgs": [1, 2]}, None, None, None])

    def test_a_favourite_in_the_old_order_is_redrawn(self):
        got = self.js("""const w = S.listRows([{ id: 61543, word: 'tore / tørre', hg: 2, pos: 'VERB', translated: true, t: 1 }],
  Object.create(null), { level: 2, mark: false, renumber: true }).querySelector('.ordpar-row-word');
const first = w.textContent;
await tick(); await tick();
out([first, w.textContent]);""")
        self.assertEqual(got, ["tore II homograph 2, tørre II homograph 2",
                               "tørre II homograph 2, tore II homograph 2"])

    def test_a_search_lists_it_in_our_order(self):
        got = self.js("""const res = await L.lookup('tore');
out(res.heads[0].articles.map(a => [a.id, a.word]));""")
        self.assertIn([61543, "tørre / tore"], got)


# --- 3. the About sentence -----------------------------------------------------------------

#: Since decisions 106 (Robin 2026-10-23: "a concise bulleted list of every type of change + the
#: count") 93 (3)'s sentence is a line of the About page's list, with the count the build makes
LINE = ("The more common spelling of the headword put first, where Bokmålsordboka lists it "
        "second: 4 articles")


class AboutSentence(unittest.TestCase):

    def test_in_the_list_of_changes(self):
        src = _read(ORDPAR, "about.md")
        self.assertIn("[if corr_headorder]- The more common spelling of the headword put first, "
                      "where Bokmålsordboka lists it second: {corr_headorder}", src)
        _t, body = about.page(about.SAMPLE)
        self.assertIn(LINE, about.plain(body))
        self.assertIn(LINE, about.plain(about.readme(about.SAMPLE)))


# --- 4. the Recent rows above the keyboard -------------------------------------------------

class RecentCap(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_capped_when_drawn(self):
        recent = self.js[self.js.index("    function openRecent("):self.js.index("    function emptyBox(")]
        self.assertIn("fitHeight(popup);", recent)
        self.assertNotIn("popup.style.maxHeight = '';", recent)
        self.assertLess(recent.index("popup.hidden = false;"), recent.index("fitHeight(popup);"))

    def test_capped_again_on_a_resize(self):
        resize = self.js[self.js.index("viewport.addEventListener('resize'"):]
        resize = resize[:resize.index("});") + 3]
        self.assertIn("if (!recentHead.hidden) { fitHeight(popup); return; }", resize)

    def test_one_cap_for_both(self):
        self.assertEqual(self.js.count("function fitHeight("), 1)


# --- 5. the mini's defaults ----------------------------------------------------------------

class MiniDefaults(unittest.TestCase):
    css = page.article_css()
    js = _read(SITE, "shell.js")

    def test_article_the_default(self):
        self.assertIn("{ key: 'minispacing', values: ['article', 'compact'], def: 'article', section: 'article', sub: 'mini' }",
                      self.js)
        self.assertIn("cl.toggle('ordpar-minispacing-compact', getSetting('minispacing') === 'compact');", self.js)

    def test_the_head_script_sets_compact_only_when_stored(self):
        self.assertIn("s.getItem('minispacing')==='compact'&&c.add('ordpar-minispacing-compact');", head.THEME_JS)
        self.assertNotIn("minispacing-article", head.THEME_JS)

    def test_the_compact_rules_ride_on_their_class(self):
        self.assertNotIn("ordpar-minispacing-article", self.css)
        self.assertEqual(self.css.count("html.ordpar-minispacing-compact "), 10)
        self.assertIn("html.ordpar-minispacing-compact .ordpar-fmini{line-height:1.3;padding:.6rem .75rem}", self.css)

    def test_the_labels_unchanged(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        self.assertEqual((s["settings.minispacing"], s["settings.minispacing.compact"],
                          s["settings.minispacing.article"]), ("Spacing", "Compact", "As the article"))

    def test_the_header_gloss_in_the_text_colour(self):
        ours = ".mini-head .mini-gloss,html.nightMode .mini-head .mini-gloss{color:inherit}"
        self.assertIn(ours, self.css)
        # after the deck's rule, and more specific; since decisions 114 the deck's rule has no
        # colour of its own (the text colour, light and night) and is 1rem semibold
        self.assertGreater(self.css.index(ours), self.css.index(".mini-gloss{font-size:1rem;font-weight:600}"))
        self.assertNotIn(".mini-gloss{color:#8b7f84", self.css)
        self.assertNotIn(".nightMode .mini-gloss", self.css)


# --- 6. the sense numbers ------------------------------------------------------------------

class SenseNumbers(unittest.TestCase):
    css = page.article_css()

    def test_the_bullet_does_not_advance_the_counter(self):
        rule = re.search(r"\.ordbok-sub:not\(\.ordpar-comp\)\{([^}]*)\}", self.css).group(1)
        self.assertIn("display:list-item", rule)
        self.assertIn("list-style:disc outside", rule)
        self.assertIn("counter-increment:list-item 0", rule)

    def test_no_other_list_item_without_it(self):
        for name, css in (("article css", self.css), ("shell.css", _read(SITE, "shell.css")),
                          ("inflection.css", _read(SITE, "inflection.css"))):
            for m in re.finditer(r"([^{}]*)\{([^}]*display:\s*list-item[^}]*)\}", css):
                self.assertIn("counter-increment:list-item0", m.group(2).replace(" ", ""), (name, m.group(1)))


if __name__ == "__main__":
    unittest.main()
