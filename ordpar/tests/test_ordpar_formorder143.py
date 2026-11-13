# -*- coding: utf-8 -*-
"""Pins site decisions 143 (Robin, 2026-10-26: "purely sort it based on frequency"; 2026-10-27:
"E2 sounds good", with a short list of ruled exceptions; and "within one word the list view's
order wins"): the rows under "is an inflected form of" group each form's articles by their word
(`form_word`: the headword line's first spelling) and list the words most common first by **E2**
— each spelling's count in NB's 2026
books shared out among every article that has it (headword or inflected form), in proportion to
each one's example sentences + 1, an article's figure the sum of its shares, rounded, a word's
the sum of its articles' (`build_index.form_share`, as the measurement
`form-order-measure-143-2026-10-26/collect.py` defined it); within a word, and in a tie, the
results' order (`result_order` / `resultOrder`: translated first, then `homograph_order`, verbs
in number order, then the rest in number order); then the exceptions file
`ordpar/form-order-overrides.tsv` lifts the word of each id it names first
(`read_form_overrides`). A query's own headword rows are unchanged.

* **The build** (`form_order`, `form_share`, `article_examples`, used by `write_index`): each
  form's ids are stored in that order in the shard's `forms`; without figures the order is
  `result_order`'s; the exceptions file is applied after E2, and a line naming no form with two
  or more articles, or an id not among them, is reported in the manifest (`form_order`). The
  manifest's per-shard `heads`/`forms` counts are each shard's own (the first 143 build wrote
  the last shard's into every entry).
* **Every reader keeps the stored order**: `Index.lookup` (the read-side twin, from which the
  word pages and form pages are built: `page_plan`, `wordpages.form_rows`) and lookup.js
  `group` (the search page, the list view and the full view, the 404 shell, the offline copy —
  all draw `res.forms` through `render`'s `articleList`).
* **The built site** (`ordpar/out/`, skipped when absent or built without `--freq`): *var*
  starts with *være* II; the six faults the first build's spelling count made are right
  (`KNOWN`: *helt* → *hel*, *varer* → not *var* I, *satte* → *sette*, *mener* → *mene*,
  *varen* → *vare* I through the exceptions file); *bomber* → the noun *bombe* I, its word's
  list order (translated first; the verb *bombe* II is not); *varer* → *vare* III, IV, I, then *var*
  I (Robin, 2026-10-27); *været* → *vær* II, III (its word lifted), then *være* III; the agent-noun
  loan is gone (*heller* → *gjerne*, *timer* → *time* I); a tie keeps the results' order
  (*forer*: *fôre* II and III, one figure, II first); *etterspurte* lists the untranslated verb
  before the translated adjective; every line of the exceptions file names a real inflected
  form and articles under it, and those ids' words lead the built rows; the word page `/bm-en/var/`
  draws *var*'s rows in the index's order.

`ORDPAR_TEST_INDEX` and `ORDPAR_TEST_PAGES` point the built-site checks at another copy of
`out/index/` and `out/bm-en/` (how the test was shown to fail on the first 143 build).
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
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ORDPAR)

import build_index as B  # noqa: E402

INDEX = os.environ.get("ORDPAR_TEST_INDEX") or os.path.join(ORDPAR, "out", "index")
PAGES = os.environ.get("ORDPAR_TEST_PAGES") or os.path.join(ORDPAR, "out", "bm-en")

VAERE, VADE = 69211, 66098
#: The first 143 build's faults (decisions 143, the session's check of 2026-10-26): form ->
#: (the id that must lead, the id that led wrongly). *varen* is right through the exceptions file.
KNOWN = {"helt": (22945, 22968),      # hel, heil II, not hele VI
         "satte": (51169, 50239),     # sette, not satt
         "mener": (37860, 37856),     # mene, meine, not men II
         "bomber": (6920, 6921),      # the noun bombe I: one word, the list view's order (translated first)
         "varen": (66635, 66620)}     # vare I, not var I (the exceptions file)
#: *varer*: the fault was *var* I first; the word *vare* now leads in the list view's order,
#: III, IV, I, then *var* I (Robin, 2026-10-27: "That would put the order like this")
VARER_NOT_FIRST, VARER_VARE = 66620, {66635, 66637, 66638}
VARER = [66637, 66638, 66635, 66620]
#: *været*: the exception names *vær* III; its word is lifted whole, *vær* II first
VAERET = [69202, 69203, 69212]
#: the agent-noun loan of `article_freq` (the measurement's doubt 3), not read by E2
AGENT = {"heller": (19935, 23013),    # gjerne, not helle II
         "timer": (61018, 61019)}     # time I, not time, taime II
#: a tie in the build: *fôre, fore* II and III have the same E2 figure, so the results' order
TIE = ("forer", [16106, 16107])
#: an untranslated headword more common than a translated one, listed first
UNTRANSLATED_FIRST = {"etterspurte": (125888, 13350)}


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run_js(body):
    runner = _runner()
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("const M = require(%s); const L = M.ordparLookup;\n%s\n"
                     % (json.dumps(os.path.join(SITE, "lookup.js")), body))
        res = subprocess.run([runner, script], capture_output=True, timeout=120)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _js_forms(index_dir, q):
    """lookup.js's inflected-form groups for `q` over the index at `index_dir`: [[form, [ids]]]."""
    return _run_js("""
const fs = require('fs'), path = require('path');
L.setLoader(name => { const p = path.join(%s, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
L.lookup(%s).then(r => process.stdout.write(JSON.stringify(
  r.forms.map(g => [g.form, g.articles.map(a => a.id)]))));
""" % (json.dumps(index_dir), json.dumps(q)))


def _row(aid, lemma, hg, pos, forms=(), examples=0):
    defs = [{"type_": "definition", "elements": [{"type_": "example"}] * examples}]
    return {"id": aid, "data": {"lemmas": [{
        "lemma": lemma, "hgno": hg,
        "paradigm_info": [{"tags": [pos], "inflection": [{"word_form": f} for f in forms]}]}],
        "body": {"definitions": defs}}}


def _tables(rows, tmp):
    mirror = os.path.join(tmp, "mirror.jsonl")
    with open(mirror, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return B.build_tables(mirror, None, {}), mirror


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class FormOrder(unittest.TestCase):
    """`build_index.form_order` on its own."""

    WORDS = {1: ["vade / va", 0, "VERB"], 2: ["være", 2, "VERB"], 3: ["vare", 3, "VERB"],
             4: ["vare", 4, "VERB"]}

    def test_most_common_first_whatever_is_translated(self):
        got = B.form_order([1, 2, 3, 4], self.WORDS, {1, 3, 4}, {1: 10, 2: 1000, 3: 50, 4: 50})
        self.assertEqual(got, [2, 3, 4, 1])      # 2 untranslated, but the most common

    def test_a_tie_keeps_the_results_order(self):
        # the same count: translated first, then the homograph order (verbs III before IV)
        self.assertEqual(B.form_order([4, 3, 2], self.WORDS, {3, 4}, {2: 7, 3: 7, 4: 7}), [3, 4, 2])

    def test_without_frequencies_the_order_is_the_results_order(self):
        want = [a["id"] for a in sorted(
            ({"id": i, "hg": w[1], "pos": w[2], "translated": i in {1, 3, 4}}
             for i, w in self.WORDS.items()), key=B.result_order)]
        self.assertEqual(want, [1, 3, 4, 2])
        self.assertEqual(B.form_order([4, 3, 2, 1], self.WORDS, {1, 3, 4}), want)
        self.assertEqual(B.form_order([4, 3, 2, 1], self.WORDS, {1, 3, 4}, {}), want)

    def test_a_words_homographs_keep_the_list_order_and_the_word_its_summed_place(self):
        # vare IV more common than vare III: still III first (verbs in number order); the word
        # vare (60) above vade (40) though each of its articles alone is below it
        words = dict(self.WORDS)
        words[5] = ["vare", 1, "NOUN"]
        freq = {1: 40, 2: 1000, 3: 5, 4: 30, 5: 25}
        self.assertEqual(B.form_order([1, 2, 3, 4, 5], words, {1, 2, 3, 4, 5}, freq), [2, 3, 4, 5, 1])
        # within the word, translated first, as the list view
        self.assertEqual(B.form_order([3, 4, 5], words, {5}, {3: 1, 4: 1, 5: 1}), [5, 3, 4])
        # the word is the first spelling shown: "en / én" and "en" are one
        self.assertEqual(B.form_word(["en / én", 2, "DET"]), B.form_word(["en", 3, "DET"]))

    def test_the_exceptions_lift_their_word_in_their_order_the_rest_by_frequency(self):
        freq = {1: 10, 2: 1000, 3: 50, 4: 40}
        # 4 names the word vare, lifted whole in its own order (III before IV)
        self.assertEqual(B.form_order([1, 2, 3, 4], self.WORDS, set(), freq, [4]), [3, 4, 2, 1])
        self.assertEqual(B.form_order([1, 2, 3, 4], self.WORDS, set(), freq, [1, 3]), [1, 3, 4, 2])
        # an id not under the form is ignored
        self.assertEqual(B.form_order([1, 2], self.WORDS, set(), freq, [9, 1]), [1, 2])


class FormShare(unittest.TestCase):
    """E2's figure (`form_share`) and the example count it weighs by (`article_examples`)."""

    def test_examples_skip_expressions(self):
        data = {"body": {"definitions": [
            {"type_": "definition", "elements": [
                {"type_": "explanation", "content": "x"}, {"type_": "example"},
                {"type_": "definition", "elements": [{"type_": "example"}, {"type_": "example"}]},
                {"type_": "sub_article", "elements": [{"type_": "example"}]}]}]}}
        self.assertEqual(B.article_examples(data), 3)
        self.assertEqual(B.article_examples({}), 0)

    def test_a_spelling_is_shared_by_examples_plus_one(self):
        # entry: (id, headwords, _, pos, inflected forms)
        entries = [(1, ["vare"], None, "NOUN", ["varen", "var"]),
                   (2, ["være"], None, "VERB", ["var", "er"]),
                   (3, ["var"], None, "NOUN", [])]
        counts = {"var": 1000, "varen": 10, "er": 500, "være": 100}
        # weights: 1 -> 4, 2 -> 1, 3 -> 0 + 1 = 1: var's 1000 split 4:1:1
        got = B.form_share(entries, counts, {1: 3, 2: 0})
        self.assertEqual(got, {1: round(1000 * 4 / 6 + 10), 2: round(1000 / 6 + 500 + 100),
                               3: round(1000 / 6)})

    def test_no_agent_noun_loan(self):
        # the noun *heller* has its own spelling; the verb's present *heller* is shared by both,
        # never added whole to the verb (`article_freq`'s agent fix is not read)
        entries = [(1, ["helle"], None, "VERB", ["heller"]), (2, ["heller"], None, "ADV", [])]
        got = B.form_share(entries, {"heller": 900, "helle": 0}, {1: 0, 2: 2})
        self.assertEqual(got, {1: 225, 2: 675})      # weights 1 and 2 + 1


class OverridesFile(unittest.TestCase):
    """`read_form_overrides`, and the committed file in its format."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read(self, text):
        p = os.path.join(self.tmp, "o.tsv")
        _write(p, text)
        return B.read_form_overrides(p)

    def test_reads_one_or_several_ids(self):
        got = self._read("# c\n\nform\tfirst\twhy\net\t12571\tthe article\nx\t3, 1\ttwo\n")
        self.assertEqual(got, {"et": [12571], "x": [3, 1]})

    def test_refuses_a_bad_line(self):
        for bad in ("form\tband\twhy\n", "form\tfirst\twhy\net\t12571\n",
                    "form\tfirst\twhy\net\tabc\twhy\n", "form\tfirst\twhy\net\t1\t \n",
                    "form\tfirst\twhy\net\t1\ta\net\t2\tb\n", "et\t1\ta\n"):
            with self.assertRaises(ValueError, msg=bad):
                self._read(bad)

    def test_the_committed_file_reads(self):
        got = B.read_form_overrides(B.FORM_OVERRIDES_PATH)
        self.assertGreater(len(got), 0)
        self.assertEqual(got["varen"], [66635])


class SyntheticIndex(unittest.TestCase):
    """A small index written by `write_index`, read back by both lookups and the page plan."""

    FREQ = {1: 10, 2: 1000, 3: 50, 4: 50, 5: 5}
    WANT = [2, 3, 4, 1]

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        rows = [_row(1, "vade", 0, "VERB", ["var", "vadet"]), _row(2, "være", 2, "VERB", ["var", "er"]),
                _row(3, "vare", 3, "VERB", ["var"]), _row(4, "vare", 4, "VERB", ["var"]),
                _row(5, "var", 0, "NOUN"), _row(6, "ete", 0, "VERB", ["et", "eter"]),
                _row(7, "en", 3, "DET", ["et"])]
        (heads, forms, words), cls.mirror = _tables(rows, cls.tmp)
        cls.heads = heads
        cls.stats = {}
        cls.overrides = {"et": [7], "nosuch": [1], "vadet": [2]}
        cls.manifest = B.write_index(os.path.join(cls.tmp, "freq"), heads, forms, words,
                                     [1, 3, 4, 5], cls.stats, cls.FREQ, order_freq=cls.FREQ,
                                     order_overrides=cls.overrides)
        cls.plain = B.write_index(os.path.join(cls.tmp, "plain"), heads, forms, words,
                                  [1, 3, 4, 5], {})
        cls.index = os.path.join(cls.tmp, "freq", "index")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _shard(self, sub, form="var"):
        with open(os.path.join(self.tmp, sub, "index", B.shard_key(form) + ".json"),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def test_the_shard_stores_the_frequency_order(self):
        self.assertEqual(self._shard("freq")["forms"]["var"], self.WANT)
        self.assertEqual(self.stats["form_order_changed_143"], 2)    # var, and et (exception)

    def test_without_freq_the_shard_stores_the_results_order(self):
        self.assertEqual(self._shard("plain")["forms"]["var"], [1, 3, 4, 2])

    def test_the_exception_goes_first(self):
        self.assertEqual(self._shard("freq", "et")["forms"]["et"], [7, 6])

    def test_an_unmatched_exception_is_reported(self):
        # nosuch is no form; vadet has one article, which is not 2
        note = self.manifest["form_order"]
        self.assertEqual(note["method"], "E2")
        self.assertEqual(note["overrides"]["entries"], 3)
        self.assertEqual(note["overrides"]["unmatched"], ["nosuch", "vadet"])
        self.assertEqual(self.stats["form_overrides_unmatched"], 2)

    def test_the_manifest_counts_each_shards_own_heads_and_forms(self):
        self.assertGreater(len(self.manifest["shards"]), 1)
        for sh in self.manifest["shards"]:
            with open(os.path.join(self.index, sh["file"]), encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual((sh["heads"], sh["forms"]),
                             (len(data["heads"]), len(data["forms"])), sh["k"])

    def test_the_python_lookup_keeps_it(self):
        res = B.Index(self.index).lookup("var")
        self.assertEqual([a["id"] for a in res["forms"][0]["articles"]], self.WANT)

    def test_the_script_keeps_it(self):
        self.assertEqual(_js_forms(self.index, "var"), [["var", self.WANT]])

    def test_the_word_page_rows_keep_it(self):
        page = self.manifest["_plan"]["words"]["var"]
        self.assertEqual([[a["id"] for a in arts] for _f, arts in page["rows"]], [self.WANT])

    def test_headword_rows_are_unchanged(self):
        # a query's own headword rows keep result_order: the two *vare* (both translated)
        res = B.Index(self.index).lookup("vare")
        self.assertEqual([a["id"] for a in res["heads"][0]["articles"]], [3, 4])

    def test_the_script_does_not_resort_inflected_rows(self):
        with open(os.path.join(SITE, "lookup.js"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("if (matched) { articles.sort(resultOrder); }", src)
        self.assertNotRegex(src, r"\n\s+articles\.sort\(resultOrder\);")


def _built():
    mf = os.path.join(INDEX, "index.json")
    if not os.path.exists(mf):
        return None, "no built index at %s" % INDEX
    with open(mf, encoding="utf-8") as fh:
        m = json.load(fh)
    if not (m.get("freq") or {}).get("freq"):
        return None, "the built index has no frequencies (built without --freq)"
    return m, None


class BuiltSite(unittest.TestCase):
    """The site as built (`ordpar/out/`, or the copy the environment names)."""

    @classmethod
    def setUpClass(cls):
        cls.manifest, why = _built()
        if why:
            raise unittest.SkipTest(why)
        cls.idx = B.Index(INDEX)

    def _ids(self, q):
        res = self.idx.lookup(q)
        for g in res["forms"]:
            for a in g["articles"]:
                self._words[a["id"]] = a["word"]
        return {g["form"]: [a["id"] for a in g["articles"]] for g in res["forms"]}

    _words = {}

    def idx_word(self, i):
        # the word as `form_word` reads it: the first spelling shown
        return B.form_word([self._words[i]])

    def test_built_by_e2(self):
        self.assertEqual((self.manifest.get("form_order") or {}).get("method"), "E2")

    def test_var_starts_with_vaere(self):
        ids = self._ids("var")["var"]
        self.assertEqual(ids[0], VAERE, ids)
        self.assertLess(ids.index(VAERE), ids.index(VADE), ids)

    def test_the_known_faults_are_right(self):
        for form, (first, wrong) in KNOWN.items():
            ids = self._ids(form)[form]
            self.assertEqual(ids[0], first, (form, ids))
            self.assertIn(wrong, ids)
        ids = self._ids("varer")["varer"]
        self.assertNotEqual(ids[0], VARER_NOT_FIRST, ids)
        self.assertIn(ids[0], VARER_VARE, ids)
        self.assertEqual(ids, VARER)
        self.assertEqual(self._ids("været")["været"], VAERET)

    def test_the_agent_noun_loan_is_not_read(self):
        for form, (first, verb) in AGENT.items():
            ids = self._ids(form)[form]
            self.assertEqual(ids[0], first, (form, ids))
            self.assertIn(verb, ids)

    def test_a_tie_keeps_the_results_order(self):
        form, want = TIE
        ids = self._ids(form)[form]
        self.assertEqual(ids[:2], want, ids)

    def test_an_untranslated_more_common_headword_comes_first(self):
        tr = self.idx.translated
        for form, (untr, trans) in UNTRANSLATED_FIRST.items():
            ids = self._ids(form)[form]
            self.assertNotIn(untr, tr)
            self.assertIn(trans, tr)
            self.assertLess(ids.index(untr), ids.index(trans), (form, ids))

    def test_every_exception_names_a_real_form_and_its_word_leads_it(self):
        ovr = B.read_form_overrides(B.FORM_OVERRIDES_PATH)
        note = (self.manifest.get("form_order") or {}).get("overrides") or {}
        self.assertEqual(note.get("entries"), len(ovr))
        self.assertEqual(note.get("unmatched"), [])
        for form, first in ovr.items():
            ids = self._ids(form).get(form)
            self.assertIsNotNone(ids, form)
            self.assertGreater(len(ids), 1, form)
            words = {}
            for i in ids:
                words.setdefault(self.idx_word(i), []).append(i)
            lead = []
            for i in first:
                lead.extend(j for j in words[self.idx_word(i)] if j not in lead)
            self.assertEqual(ids[:len(lead)], lead, (form, ids))

    def test_the_script_draws_var_in_the_same_order(self):
        self.assertEqual(dict((f, i) for f, i in _js_forms(INDEX, "var")), self._ids("var"))

    def test_the_word_page_draws_var_in_the_same_order(self):
        path = os.path.join(PAGES, "var", "index.html")
        if not os.path.exists(path):
            self.skipTest("no word page %s" % path)
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        secs = re.findall(r'<section class="ordpar-inflected">(.*?)</section>', html, re.S)
        self.assertEqual(len(secs), 1)
        got = [int(x) for x in re.findall(r'href="/bm-en/(\d+)/"', secs[0])]
        self.assertEqual(got, self._ids("var")["var"])
        self.assertEqual(got[0], VAERE)


if __name__ == "__main__":
    unittest.main()
