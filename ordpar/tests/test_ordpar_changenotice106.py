"""Site decisions 106 (Robin, 2026-10-23): a one-line change notice at the card's foot of every
article whose Norwegian we corrected, naming the kinds of change only and linking to the article
on ordbokene.no; and the About page's list of changes, counted by the same reader.

* **The live rows** (`sitegen/corrections.py` `live_rows`, synthetic rows): an integer `article`;
  no `resolved_upstream`; a `revert` recipe or a `supersedes` pointer keeps the row; a
  `reapplied_from` row replaces the row it names; a class row (`ids`) and a null-article row are
  not an article's correction; the same edit logged twice counts once.
* **The check against the mirror** (`check_row`, synthetic views): a typo, a cross-reference and
  the headword's order shown when the page differs from the mirror's derivation in the logged way;
  `UPSTREAM` — no notice — when the mirror already carries the fix (Robin's rider, 2026-10-23); not
  shown when the page has no library row, or still carries the defect; invisible for a run of
  spaces; unconfirmed where no difference is found and the row cannot settle why. `Checker` over a
  stand-in store makes notices from `SHOWN` rows only, and its counts are the About page's.
* **The words** (`ordpar/site/strings/en.json` `change.*`): every kind the log carries maps to a
  group or is on the list of non-corrections; each group's phrase singular and plural; the groups
  in the ruled order (cross-references, the headword's order, typos, the rest); joined with commas
  and "and"; the link's words and its one URL form (`chrome.ORDBOKENE_ARTICLE`).
* **The page** (`page.render`): the notice inside `<footer class="ordpar-card-foot">`, static; no
  notice, an empty foot; the page script puts its controls BEFORE the notice and still makes them
  when the foot is not empty; the search page's `extractArticle` returns the notice apart from the
  fragment, `mountArticle` puts it after the result's controls, and the mini cuts before the foot
  (JS stand-in).
* **The About page** (`about.md` through `sitegen/about.py`): one bullet per type with its count,
  from `stats["corrections"]`, dated by the snapshot ("as of Bokmålsordboka's data of 25 September
  2026"); a type with no count drops its line.
* **The built pages** (`ordpar/out/`, or the folder `ORDPAR_TEST_OUT` names): the notice on
  exactly the articles the build's checker names — and that list is the live log's articles less
  those none of whose corrections reach the page — on no other page, word for word, with its link.
  The verdicts come from the folder's own `build.json`, or the local build's where the folder has
  none (the published clone): **on the live snapshot this fails**, as no page has a notice.
* **The browser** (`browser/changenotice.js`, headless Edge, a computer, a phone and dark): the
  foot's controls then the notice, the heart among them, the muted colour, inside the card, no
  sideways scroll; a full search result and an opened list row carry it after their controls; an
  article without corrections none.

Stdlib unittest. Skips its built-page part without a build, and its browser part without Edge,
bun or a build.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))

from ordpar.sitegen import about, chrome, corrections as C, page  # noqa: E402
import harness  # noqa: E402

ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ORDPAR, "out")
LOCAL_BUILD_JSON = os.path.join(ORDPAR, "out", "build.json")
STRINGS = chrome.strings("en")

#: Kinds in the log that record no correction of an article's text (a content refresh, a class
#: of defects deliberately left alone, pointers to other registries).
NOT_CORRECTIONS = {"refresh", "whitespace-class", "registry-pointer:dangling-ref",
                   "registry-pointer:dangling-def", "registry-pointer:embedded-vs-standalone"}


def _runner():
    for exe in ("bun", "node"):
        if shutil.which(exe):
            return exe
    return None


def _row(**kw):
    r = {"article": 1, "lemma": "x", "kind": "typo", "where": "def 1", "before": "hum kommer",
         "after": "hun kommer", "why": "w", "date": "2026-08-01"}
    r.update(kw)
    return r


def _view(text, hrefs=(), defn=(1,), pos="noun", exprs=()):
    """A `View` over a one-sense row with `text` as its definition and `hrefs` as links."""
    segs = [text] + ["[t](%s)" % h for h in hrefs]
    row = {"lemmas": [{"form": "x"}], "pos_en": pos, "exprs": list(exprs),
           "senses": [{"defn": d, "no": segs if i == 0 else ["s"], "subs": [], "ex": [], "comp": []}
                      for i, d in enumerate(defn)]}
    return C.View(row)


# --- 1. the live rows -------------------------------------------------------------------------

class LiveRows(unittest.TestCase):

    def test_the_rule(self):
        rows = [
            _row(article=1),
            _row(article=2, resolved_upstream="2026-09-02 fixed by ordbokene"),
            _row(article=3, kind="wrong-form", revert="git checkout …", supersedes="declined …"),
            _row(article=None, lemma="gi ut"),
            _row(article=None, lemma="(class)", ids=[5, 6]),
            _row(article=4, kind="refresh"),
            _row(article=7, kind="registry-pointer:dangling-ref"),
            _row(article=8, kind="notation", date="2026-08-27", before="$ $, $", after="$, $, $"),
            _row(article=8, kind="notation", date="2026-09-03", reapplied_from="2026-08-27",
                 before="$ $, $", after="$, $, $"),
            _row(article=9, before="'hum kommer stadig opp i problemer'",
                 after="'hun kommer stadig opp i problemer'", date="2026-07-16"),
            _row(article=9, before="hum kommer", after="hun kommer", date="2026-09-02"),
            _row(article=9, kind="ref-anchor", before="#def4", after="#def3"),
        ]
        live = C.live_rows(rows)
        got = [(r["article"], r["kind"], r["date"]) for r in live]
        self.assertEqual(got, [(1, "typo", "2026-08-01"), (3, "wrong-form", "2026-08-01"),
                               (8, "notation", "2026-09-03"), (9, "typo", "2026-07-16"),
                               (9, "ref-anchor", "2026-08-01")])

    def test_every_logged_kind_is_known(self):
        kinds = {r.get("kind") for r in C.read_log()}
        self.assertTrue(kinds, "the normalization log is empty or missing")
        unknown = kinds - set(C.KIND_GROUP) - NOT_CORRECTIONS
        self.assertFalse(unknown, "kinds in the log with no notice group: %s — give each a group "
                                  "(and its phrase in en.json) or list it as no correction"
                         % sorted(unknown))
        self.assertEqual(set(C.KIND_GROUP.values()), set(C.GROUPS))


# --- 2. the check against the mirror ---------------------------------------------------------

class Check(unittest.TestCase):

    def test_typo(self):
        row = _row(before="'hum kommer stadig'", after="'hun kommer stadig'")
        fixed, broken = _view("hun kommer stadig opp"), _view("hum kommer stadig opp")
        self.assertEqual(C.check_row(row, fixed, broken, True), C.SHOWN)
        # ordbokene fixed it before our next refresh: the mirror reads as the page does
        self.assertEqual(C.check_row(row, fixed, _view("hun kommer stadig opp"), True), C.UPSTREAM)
        # the page still carries the defect, as the mirror does
        self.assertEqual(C.check_row(row, broken, broken, True), C.NOT_SHOWN)
        # no library row: the page is the mirror's
        self.assertEqual(C.check_row(row, broken, broken, False), C.NOT_SHOWN)
        self.assertEqual(C.check_row(row, fixed, fixed, False), C.UPSTREAM)

    def test_typo_counts_words_not_strings(self):
        row = _row(before="del av av byggverk", after="del av byggverk")
        self.assertEqual(C.check_row(row, _view("del av byggverk"), _view("del av av byggverk"),
                                     True), C.SHOWN)
        sup = _row(before="lik 2,83 m<sup>2</sup>", after="lik 2,83 m<sup>3</sup>")
        self.assertEqual(C.check_row(sup, _view("lik 2,83 m³"), _view("lik 2,83 m²"), True),
                         C.SHOWN)

    def test_compound_intro(self):
        """A typo in a compound list's intro (151's nine, 2026-10-30) is a correction the page
        shows: the intro is part of the article's text since the row stores it."""
        def view(intro):
            return C.View({"lemmas": [{"form": "x"}], "pos_en": "noun", "exprs": [],
                           "senses": [{"defn": 1, "no": ["d"], "subs": [], "ex": [],
                                       "comp": [{"label": "as a suffix in words such as:", "intro": intro,
                                                 "items": [{"word": "hjemskriv", "href": "/nob/bm/1"}]}]}]})
        row = _row(before="som etteredd i ord som", after="som etterledd i ord som")
        self.assertEqual(C.check_row(row, view("som etterledd i ord som"), view("som etteredd i ord som"),
                                     True), C.SHOWN)

    def test_spaces_are_invisible(self):
        row = _row(kind="notation", before="med  hunder", after="med hunder")
        self.assertEqual(C.check_row(row, _view("med hunder"), _view("med  hunder"), True),
                         C.INVISIBLE)
        row = _row(before="double space", after="single space")
        self.assertEqual(C.check_row(row, _view("a b"), _view("a  b"), True), C.INVISIBLE)

    def test_cross_reference(self):
        row = _row(kind="ref-anchor", before="#def2", after="#def3")
        ours = _view("t", hrefs=["/nob/bm/5#def3"])
        theirs = _view("t", hrefs=["/nob/bm/5#def2"])
        self.assertEqual(C.check_row(row, ours, theirs, True), C.SHOWN)
        self.assertEqual(C.check_row(row, ours, ours, True), C.UPSTREAM)
        self.assertEqual(C.check_row(row, theirs, theirs, False), C.NOT_SHOWN)

    def test_headword_order(self):
        row = _row(kind="lemma-order", where="top-level lemmas order (the article header)",
                   before="tore, tørre", after="tørre, tore")
        self.assertEqual(C.check_row(row, None, None, True, ["tore", "tørre"]), C.SHOWN)
        self.assertEqual(C.check_row(row, None, None, True, ["tørre", "tore"]), C.UPSTREAM)
        self.assertEqual(C.check_row(row, None, None, True, ["tora", "tørre"]), C.NOT_SHOWN)

    def test_other_kinds(self):
        row = _row(kind="segment-drop", before="…, jf", after="…")
        self.assertEqual(C.check_row(row, _view("felt"), _view("felt, jf"), True), C.SHOWN)
        self.assertEqual(C.check_row(row, _view("felt"), _view("felt"), True), C.UNCONFIRMED)
        dup = _row(kind="duplicate-def-id", before="5, 5", after="5, 8")
        self.assertEqual(C.check_row(dup, _view("t", defn=(5, 8)), _view("t", defn=(5, 5)), True),
                         C.SHOWN)

    def test_checker_notices_and_counts(self):
        class Mirror(object):
            stored = {}

            def row(self, aid):
                return {"data": {"lemmas": [{"lemma": "tore"}, {"lemma": "tørre"}]}} \
                    if aid == 4 else {"data": {"lemmas": [{"lemma": "x"}]}}

        def lib(text, hrefs=()):
            v = {"id": 0, "lemmas": [{"form": "x"}], "pos_en": "noun", "exprs": [],
                 "senses": [{"defn": 1, "no": [text] + ["[t](%s)" % h for h in hrefs],
                             "subs": [], "ex": [], "comp": []}]}
            return v

        class Store(object):
            mirror = Mirror()
            library = {1: lib("hun kommer", ["/nob/bm/5#def3"]), 2: lib("hun kommer"),
                       4: lib("x")}
            derived_rows = {1: lib("hum kommer", ["/nob/bm/5#def2"]), 2: lib("hun kommer"),
                            3: lib("hum kommer"), 4: lib("x")}

            def derived(self, aid):
                return self.derived_rows.get(aid)

            def embedded_expr(self, parent, eid):
                return None

            def expr_row(self, parent, eid):
                return None

        rows = [_row(article=1), _row(article=1, kind="ref-anchor", before="#def2", after="#def3"),
                _row(article=2),                    # fixed upstream: no notice, no count
                _row(article=3),                    # no library row: no notice
                _row(article=4, kind="lemma-order", where="top-level lemmas order",
                     before="tore, tørre", after="tørre, tore"),
                _row(article=5)]                    # no page: no notice
        ch = C.Checker(Store(), rows=rows, has_page=lambda aid: aid != 5)
        self.assertEqual(ch.notice, {1: [("xref", 1), ("typo", 1)], 4: [("headorder", 1)]})
        s = ch.summary()
        self.assertEqual(s["articles"], 2)
        self.assertEqual(s["about"]["xref"], {"corrections": 1, "articles": 1})
        self.assertEqual(s["about"]["spelling"], {"corrections": 1, "articles": 1})
        self.assertEqual(s["about"]["headorder"], {"corrections": 1, "articles": 1})
        self.assertEqual([x["article"] for x in s["upstream"]], [2])
        self.assertEqual(sorted(x["article"] for x in s["not_shown"]), [3, 5])
        # the About page counts what the checker counted (decisions 106: one source)
        stats = json.loads(json.dumps(about.SAMPLE))
        stats["corrections"] = {"about": s["about"], "other": s["other_groups"],
                                "articles": s["articles"]}
        text = about.plain(about.page(stats)[1])
        self.assertIn("homograph or article, corrected: 1 in 1 article", text)
        self.assertIn("Typos, punctuation and formatting corrected: 1 in 1 article", text)
        self.assertIn("where Bokmålsordboka lists it second: 1 article", text)
        self.assertNotIn("Other corrections", text)


# --- 3. the words ------------------------------------------------------------------------------

class Words(unittest.TestCase):

    def test_every_group_has_both_phrases(self):
        for g in C.GROUPS:
            if g == "headorder":            # a sentence of its own (decisions 106, Robin 2026-10-23)
                continue
            for n in ("one", "many"):
                self.assertTrue(STRINGS.get("change.%s.%s" % (g, n)), "change.%s.%s" % (g, n))

    def test_the_mapping(self):
        want = {"ref-anchor": "a cross-reference", "ref-retarget": "a cross-reference",
                "ref-unlink": "a cross-reference",
                "typo": "a typo", "wording": "a typo", "wrong-form": "a word form",
                "notation": "a punctuation or formatting error",
                "alternation-notation": "a punctuation or formatting error",
                "inflectional-collapse": "a punctuation or formatting error",
                "marker": "a punctuation or formatting error",
                "comp-membership": "a list of compounds", "segment-drop": "a stray fragment of text",
                "misplaced-element": "a misplaced passage",
                "duplicate-expression-article": "a duplicated set phrase",
                "pos-tag": "the word class", "duplicate-def-id": "a duplicated link target",
                "capture-repair": "a damaged passage"}
        for kind, phrase in want.items():
            self.assertEqual(C.phrases([(C.KIND_GROUP[kind], 1)], STRINGS), [phrase], kind)
        self.assertEqual(set(want) | {"lemma-order"}, set(C.KIND_GROUP))   # lemma-order: its own sentence
        # an anchor fix never says the words were changed
        self.assertNotIn("word", STRINGS["change.xref.one"] + STRINGS["change.xref.many"])

    def test_sentence(self):
        self.assertEqual(C.sentence([("typo", 1)], STRINGS), "We corrected a typo in this article.")
        self.assertEqual(C.sentence([("xref", 2), ("typo", 1)], STRINGS),
                         "We corrected cross-references and a typo in this article.")
        # the headword's order: a sentence of its own (Robin, 2026-10-23)
        self.assertEqual(C.KIND_GROUP["lemma-order"], "headorder")
        self.assertEqual(C.sentence([("headorder", 1)], STRINGS),
                         "We put the more common spelling of the headword first.")
        self.assertEqual(C.sentence([("xref", 1), ("headorder", 1), ("typo", 3)], STRINGS),
                         "We put the more common spelling of the headword first and corrected "
                         "a cross-reference and typos in this article.")
        # the order is the ruled one, whatever order the groups come in from a row
        self.assertEqual(C.GROUPS[:3], ["xref", "headorder", "typo"])

    def test_notice_markup(self):
        h = C.notice_html(17238, [("xref", 1), ("typo", 1)], STRINGS)
        # site decisions 152: the sentence and the link's words in both languages (the labels
        # setting), the Norwegian copies DRAFTS with `data-nosnippet`
        self.assertEqual(h, '<p class="ordpar-change"><span class="ordpar-l-en">We corrected a '
                            'cross-reference and a typo in this article.</span><span '
                            'class="ordpar-l-nb" lang="nb" data-nosnippet>Vi har rettet feil i denne '
                            'artikkelen.</span> <a class="ordpar-l-en" href="https://ordbokene.no/nob/bm/17238" '
                            'rel="noopener">Bokmålsordboka\'s article on ordbokene.no<span aria-hidden="true"> '
                            '↗</span></a><span class="ordpar-l-nb" lang="nb" data-nosnippet><a '
                            'href="https://ordbokene.no/nob/bm/17238" rel="noopener">Bokmålsordbokas artikkel '
                            'på ordbokene.no<span aria-hidden="true"> ↗</span></a></span></p>')
        self.assertEqual(C.notice_html(1, [], STRINGS), "")
        self.assertEqual(chrome.ORDBOKENE_ARTICLE % 5, "https://ordbokene.no/nob/bm/5")


# --- 4. the page and its scripts ---------------------------------------------------------------

def _article(**kw):
    args = dict(aid=17238, lemmas=[{"form": "forvaltningsorgan", "homograph": None}],
                article='<div class="ordbok ordpar-article"><h1 class="ordpar-hw">x</h1></div>',
                translated=True, other_entries=0, strings=page.EN, stamp="t", description="d",
                mk=None, personal={"pos": "NOUN"})
    args.update(kw)
    return page.render(**args)


class Page(unittest.TestCase):

    def test_static_in_the_foot(self):
        html = _article(change=[("xref", 1), ("typo", 1)])
        foot = re.search(r'<footer class="ordpar-card-foot">(.*?)</footer>', html, re.S).group(1)
        self.assertEqual(foot, C.notice_html(17238, [("xref", 1), ("typo", 1)], STRINGS))
        self.assertIn('<footer class="ordpar-card-foot"></footer>', _article())

    def test_page_script_keeps_its_controls(self):
        js = page.PAGE_JS
        self.assertIn("f.querySelector('.ordpar-result-controls'))return;", js)
        self.assertNotIn("f.firstElementChild)return;", js)
        self.assertIn("f.insertBefore(p,f.firstChild);", js)

    def _js(self, body):
        runner = _runner()
        if not runner:
            self.skipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "x.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(body)
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            return json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_takes_it_and_mini_does_not(self):
        html = _article(change=[("typo", 1)])
        got = self._js("const S = require(%s).ordparSearch; process.stdout.write(JSON.stringify("
                       "[S.extractArticle(%s), S.extractArticle(%s)]));"
                       % (json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(html),
                          json.dumps(_article())))
        self.assertEqual(got[0]["notice"], C.notice_html(17238, [("typo", 1)], STRINGS))
        self.assertNotIn("ordpar-change", got[0]["fragment"])
        self.assertEqual(got[1]["notice"], "")
        with open(os.path.join(SITE, "lookup.js"), encoding="utf-8") as f:
            lookup = f.read()
        mount = lookup[lookup.index("function mountArticle("):]
        mount = mount[:mount.index("\n  }\n")]
        self.assertLess(mount.index("host.appendChild(resultControls(a));"),
                        mount.index("host.insertAdjacentHTML('beforeend', '\\n' + got.notice);"))
        # the mini is cut from the page's first `<div class="ordbok` to the card's foot
        with open(os.path.join(SITE, "mini.js"), encoding="utf-8") as f:
            mini = f.read()
        self.assertIn("e = text.indexOf('<footer class=\"ordpar-card-foot\">', s);", mini)

    def test_look(self):
        with open(os.path.join(SITE, "shell.css"), encoding="utf-8") as f:
            css = f.read()
        rule = css[css.index(".ordpar-change {"):]
        rule = rule[:rule.index("}")]
        self.assertIn("color: var(--ordpar-muted);", rule)
        self.assertIn("font-size: 0.85rem;", rule)


# --- 5. the About page ---------------------------------------------------------------------------

class About(unittest.TestCase):

    def test_list_from_the_counts(self):
        text = about.plain(about.page(about.SAMPLE)[1])
        self.assertIn("We show Bokmålsordboka's articles in a layout close to ordbokene.no's, with "
                      "these changes of ours, as of its data of 25 September 2026: "   # decisions 121
                      "Cross-references that pointed to the wrong sense, homograph or article, "
                      "corrected: 82 in 80 articles Typos, punctuation and formatting corrected: 99 "
                      "in 97 articles The more common spelling of the headword put first, where "
                      "Bokmålsordboka lists it second: 4 articles Other corrections (a word form, a "
                      "list of compounds, a misplaced passage, a duplicated set phrase and a "
                      "duplicated link target): 5 in 5 articles Example sentences of our own, added "
                      "where a sense had no example: 450 in 271 articles.", text)
        self.assertIn("Each corrected article says so at its foot, with a link to Bokmålsordboka's "
                      "article on ordbokene.no.", text)
        body = about.page(about.SAMPLE)[1]
        self.assertIn("<ul>\n<li>Cross-references that pointed", body)
        readme = about.readme(about.SAMPLE)
        self.assertIn("\n- Typos, punctuation and formatting corrected: 99 in 97 articles\n", readme)

    def test_a_type_without_a_count_drops(self):
        stats = json.loads(json.dumps(about.SAMPLE))
        stats["corrections"]["about"]["other"] = {"corrections": 0, "articles": 0}
        stats["corrections"]["other"] = []
        stats["snapshot"] = None
        text = about.plain(about.page(stats)[1])
        self.assertNotIn("Other corrections", text)
        self.assertIn("with these changes of ours: Cross-references", text)   # decisions 121's words
        # a build record from before decisions 106 (no counts): only the added sentences remain
        old = {k: v for k, v in about.SAMPLE.items() if k not in ("corrections", "snapshot")}
        text = about.plain(about.page(old)[1])
        self.assertNotIn("corrected:", text)
        self.assertIn("Example sentences of our own", text)

    def test_date(self):
        self.assertEqual(about.snapshot_date("2026-09-25T01:15:52.93+00:00"), "25 September 2026")
        self.assertEqual(about.snapshot_date("unknown"), "")


# --- 6. the built pages ------------------------------------------------------------------------

def _verdicts():
    """The build's `change_notice` record, from the tested folder's build.json, else the local
    build's (a published clone carries none); None without either."""
    for path in (os.path.join(OUT, "build.json"), LOCAL_BUILD_JSON):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rec = json.load(f).get("change_notice")
            if rec:
                return rec, path
    return None, None


REC, REC_PATH = _verdicts()
PAGES = os.path.join(OUT, "bm-en")
BUILT_SKIP = (None if REC and os.path.isdir(PAGES)
              else "no built site with a change_notice record (%s)" % OUT)


@unittest.skipIf(BUILT_SKIP, BUILT_SKIP or "")
class Built(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.found = {}
        for name in os.listdir(PAGES):
            path = os.path.join(PAGES, name, "index.html")
            if not name.isdigit() or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                data = f.read()
            if b"ordpar-change" in data:
                cls.found[int(name)] = data.decode("utf-8")
        cls.built = {int(n) for n in os.listdir(PAGES) if n.isdigit()}

    def test_the_record_is_the_live_log(self):
        """The notice's articles are the live log's, less those none of whose corrections reach
        the page (each listed by verdict)."""
        import collections
        live = collections.Counter(r["article"] for r in C.live_rows(C.read_log()))
        # site decisions 182: the applied rows of review/mirror-corrections.jsonl are live too
        overlay = collections.Counter(x["article"] for x in REC.get("overlay_rows") or [])
        live_log = sum(live.values())
        live += overlay
        off = collections.Counter(x["article"] for v in (C.UPSTREAM, C.NOT_SHOWN, C.INVISIBLE,
                                                         C.UNCONFIRMED) for x in REC[v])
        self.assertEqual({int(a) for a in REC["notice"]}, {a for a in live if live[a] > off[a]},
                         "the record's notices are not the live log's articles less those none "
                         "of whose corrections reach the page")
        self.assertEqual(REC["live_rows"], live_log)

    def test_exactly_those_pages(self):
        want = {int(a) for a in REC["notice"]} & self.built
        self.assertTrue(want, "the record names no built page")
        missing = sorted(want - set(self.found))
        extra = sorted(set(self.found) - want)
        self.assertFalse(missing, "%d page(s) in %s lack the change notice the build names "
                                  "(verdicts from %s), e.g. %s"
                         % (len(missing), OUT, REC_PATH, missing[:10]))
        self.assertFalse(extra, "%d page(s) carry a notice the build does not name: %s"
                         % (len(extra), extra[:10]))

    def test_words_and_link(self):
        for aid, html in sorted(self.found.items()):
            groups = [tuple(g) for g in REC["notice"][str(aid)]]
            foot = re.search(r'<footer class="ordpar-card-foot">(.*?)</footer>', html, re.S)
            self.assertIsNotNone(foot, aid)
            self.assertEqual(foot.group(1), C.notice_html(aid, groups, STRINGS), aid)
            self.assertEqual(html.count("ordpar-change"), 1, aid)
            self.assertIn('href="https://ordbokene.no/nob/bm/%d"' % aid, foot.group(1))

    def test_about_page_counts(self):
        path = os.path.join(OUT, "about", "index.html")
        with open(path, encoding="utf-8") as f:
            text = about.plain(f.read())
        xref = REC["about"]["xref"]
        self.assertIn("homograph or article, corrected: %s in %s articles"
                      % ("{:,}".format(xref["corrections"]), "{:,}".format(xref["articles"])), text)
        self.assertIn("Each corrected article says so at its foot", text)


# --- 7. the browser ------------------------------------------------------------------------------

BROWSER_SKIP = harness.skip_reason() or BUILT_SKIP
CASES = {"computer": dict(w=1280, h=900, mobile=False, dark=False),
         "phone": dict(w=390, h=844, mobile=True, dark=False),
         "dark": dict(w=1280, h=900, mobile=False, dark=True)}
#: the articles the browser reads: one with two kinds (*rot I*: since Bokmålsordboka's data of 14
#: November 2026 the only article with two, the cross-reference of *forvaltningsorgan* now corrected
#: upstream); a query finding one article (*forvaltningsorgan*); a list row (*tørre* under "tore");
#: one without corrections
ARGS = dict(article=48919, several=48919, plain=7663, single="forvaltningsorgan", single_id=17238,
            list="tore", list_id=61543)
SHOTS = os.environ.get("ORDPAR_CHANGENOTICE_SHOTS")    # a folder: the review's screenshots
SITE_ = None
RESULT = {}


def setUpModule():
    global SITE_
    if BROWSER_SKIP:
        print("test_ordpar_changenotice106 (browser): skipped —", BROWSER_SKIP)
        return
    SITE_ = harness.Site()
    for name, vp in CASES.items():
        args = dict(vp, **ARGS)
        if SHOTS:
            args["shots"] = {"dir": SHOTS.replace("\\", "/"), "prefix": name}
        RESULT[name] = SITE_.check("changenotice.js", args)


def tearDownModule():
    if SITE_:
        SITE_.close()


@unittest.skipIf(BROWSER_SKIP, BROWSER_SKIP or "")
class Browser(unittest.TestCase):

    def test_article_foot(self):
        for name, r in RESULT.items():
            with self.subTest(case=name):
                a = r["article"]
                self.assertEqual(a.get("notices"), 1, "%s: no notice on %s" % (name, r["base"]))
                self.assertEqual(a["order"], ["ordpar-result-controls", "ordpar-change"])
                self.assertTrue(a["heart"], "the heart is missing from the controls")
                self.assertTrue(a["afterControls"])
                self.assertEqual(a["text"], C.sentence([("typo", 1), ("punct", 1)], STRINGS) + " "
                                 + STRINGS["change.link"] + " ↗")
                self.assertEqual(a["href"], "https://ordbokene.no/nob/bm/48919")
                self.assertEqual(a["colour"], a["muted"])
                self.assertEqual(a["linkColour"], a["muted"])
                self.assertTrue(a["inside"])
                self.assertFalse(a["overflow"])
                self.assertFalse(a["scrollX"])
                self.assertEqual(a["night"], CASES[name]["dark"])
                self.assertEqual(r["several"].get("notices"), 1)
                self.assertEqual(r["plain"]["notices"], 0)
                self.assertTrue(r["plain"]["controls"])

    def test_search_result_and_list_row(self):
        for name, r in RESULT.items():
            with self.subTest(case=name):
                for where in ("single", "list"):
                    x = r[where]
                    self.assertEqual(x.get("notices"), 1, "%s, %s: %s" % (name, where, x))
                    self.assertTrue(x["afterControls"], where)
                    self.assertEqual(x["colour"], x["muted"], where)
                    self.assertTrue(x["inside"], where)
                self.assertEqual(r["list"]["href"], "https://ordbokene.no/nob/bm/61543")


if __name__ == "__main__":
    unittest.main(verbosity=2)
