"""Site decisions 182 (Robin, 2026-11-10: "Build the overlay"): the handover's corrections to
articles with no library row, `review/mirror-corrections.jsonl`, applied by the site build to the
mirror article in memory before anything derives it (`sitegen/overlay.py`; the row format is
`docs/sessions/2026-09-19-ordpar-site-review/evidence/mirror-corrections-format-182-2026-11-10.md`).

* **The verdicts** (`Overlay.resolve`, synthetic articles): a text fix and a reference fix
  `applied`; `upstream` when the raw value is already `after`; `stale` when it is neither, when
  the path is missing, and when the article is not in the mirror; `library_row` for an article
  with a library row; `malformed` for a path outside `body`; a second row on the same field
  `duplicate`. The mirror's data is never changed in place.
* **An expression** (a row naming the expression's own id): the fix reaches its own article and
  the copy each parent embeds (`sub_article` -> `article`, read at the same path from the copy's
  root), and a copy whose value is not `before` is left alone; a row `upstream` in its own article
  and applied in a copy is reported as both. The writer's shapes: an absent key written `null`,
  a usage item's `text`, a definition node's `id`.
* **The mirror reader** (`Mirror.data` with `set_overlay`): corrected; `Mirror.raw_data` raw; no
  file, the same object as before.
* **The checker** (`corrections.Checker` over a `library.Store`): it reads the RAW mirror, so an
  applied row is `SHOWN` and makes the notice, and the About page's counts include it.
* **The build** (`build_site.py` over a synthetic mirror, with and without the file): the corrected
  text and the notice on the corrected page; the reference retargeted; an expression's fix on the
  parent page that shows its embedded copy; the pages of articles the file does not touch
  byte-identical to a build without it; `build.json`'s `mirror_corrections`; the About page's
  count. No file: the build is as before.
* **The real build** (`build_site.py --ids` over the real mirror, skipped without it): one real fix
  from the handover workbook (Skrivefeil row 29, *badehette* 4022, "vanttett" -> "vanntett")
  shows on its page with the notice; a page the file does not touch is byte-identical.

Stdlib unittest.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ROOT)

from ordpar.sitegen import overlay as O, mirror as M, library as L, corrections as C  # noqa: E402

from ordpar import local_paths  # noqa: E402  -- this machine's mirror

REAL_MIRROR = local_paths.get("mirror") or "(no mirror set in ordpar/local-paths.json)"


def _lem(form, lid):
    return [{"lemma": form, "hgno": 0, "id": lid, "paradigm_info": []}]


def _defn(elements, did=1):
    return {"type_": "definition", "id": did, "sub_definition": False, "elements": elements}


def _expl(text, items=()):
    return {"type_": "explanation", "content": text, "items": list(items)}


def _ex(text):
    return {"type_": "example", "quote": {"content": text, "items": []},
            "explanation": {"content": "", "items": []}}


def _art(aid, form, definitions):
    return {"id": aid, "revision": "1", "updated_at": "",
            "data": {"article_id": aid, "lemmas": _lem(form, 1000 + aid), "status": 8,
                     "body": {"definitions": definitions}}}


def _ref(target, did):
    return {"type_": "article_ref", "article_id": target, "definition_id": did,
            "lemmas": [{"lemma": "x"}]}


def _expr_copy(eid, form, text):
    """A parent's embedded copy of an expression (the mirror's `sub_article` shape)."""
    return {"type_": "sub_article", "article_id": eid, "intro": "", "lemmas": [{"lemma": form}],
            "article": {"article_id": eid, "lemmas": [{"lemma": form, "hgno": 0, "id": 1}],
                        "body": {"definitions": [_defn([_expl("melde seg"), _ex(text)])]},
                        "word_class": "EXPR"}}


ROWS = [
    _art(1, "badehette", [_defn([_expl("vanttett hodeplagg til bading")])]),
    _art(2, "hus", [_defn([_expl("bygning; jf. $", [_ref(4, 1)])])]),
    _art(3, "mann", [_defn([_expl("voksen person av hankjønn")])]),
    _art(4, "bil", [_defn([_expl("kjøretøy med motor")])]),
    _art(5, "båt", [_defn([_expl("farkost på vann")])]),
    _art(9, "skip", [_defn([_expl("stor båt")])]),
    # 6 embeds the expression 7 (which has its own article) and 8 (which has none: 404'd)
    _art(6, "melde", [_defn([_expl("gi beskjed"),
                            _expr_copy(7, "melde på", "tretti filmar er melde på"),
                            _expr_copy(8, "melde av", "hun meldte seg av kurset igår")])]),
    _art(7, "melde på", [_defn([_expl("melde seg"), _ex("tretti filmar er melde på")])]),
]
ROWS[-1]["data"]["word_class"] = "EXPR"

TEXT_PATH = ["body", "definitions", 0, "elements", 0, "content"]
EX_PATH = ["body", "definitions", 0, "elements", 1, "quote", "content"]
REF_PATH = ["body", "definitions", 0, "elements", 0, "items", 0]


def _row(article, path, before, after, kind="typo", **kw):
    r = {"article": article, "lemma": "x", "kind": kind, "sheet": "Skrivefeil", "where": "",
         "path": path, "before": before, "after": after, "before_text": before,
         "after_text": after, "defect": "theirs", "verified_live": "2026-11-10",
         "date": "2026-11-10", "handover": "2026-11-09 Skrivefeil row %d" % article}
    if isinstance(before, dict):
        r["before_text"], r["after_text"] = "bygning; jf. bil", "bygning; jf. båt"
    r.update(kw)
    return r


CORRECTIONS = [
    _row(1, TEXT_PATH, "vanttett hodeplagg til bading", "vanntett hodeplagg til bading"),
    _row(2, REF_PATH, {"article_id": 4, "definition_id": 1}, {"article_id": 5, "definition_id": 1},
         kind="ref-retarget"),
    _row(3, TEXT_PATH, "voksen persson av hankjønn", "voksen person av hankjønn"),   # upstream
    _row(4, TEXT_PATH, "kjøretøy med motorr", "kjøretøy med motor x"),              # stale
    _row(4, ["body", "definitions", 3, "content"], "a", "b"),                       # no path
    _row(5, TEXT_PATH, "farkost på vann", "farkost på vannet"),                     # library row
    _row(7, EX_PATH, "tretti filmar er melde på", "tretti filmar er meldt på"),     # expression
    _row(8, EX_PATH, "hun meldte seg av kurset igår", "hun meldte seg av kurset i går"),
    _row(77, TEXT_PATH, "x", "y"),                                                  # not in mirror
]

KINDS = set(C.KIND_GROUP)


def _write(folder, rows=ROWS, corrections=CORRECTIONS):
    mirror = os.path.join(folder, "bm-articles.jsonl")
    with open(mirror, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    corr = os.path.join(folder, "mirror-corrections.jsonl")
    with open(corr, "w", encoding="utf-8", newline="\n") as f:
        for r in corrections:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return mirror, corr


def _resolved(corrections=CORRECTIONS, library_ids=(5,)):
    data = {r["id"]: r["data"] for r in ROWS}
    parents = {7: [6], 8: [6]}
    ov = O.Overlay(copy.deepcopy(corrections), library_ids=library_ids, kinds=KINDS)
    return ov.resolve(lambda a: data.get(a), lambda ids: {i: parents[i] for i in ids if i in parents}), data


class Verdicts(unittest.TestCase):

    def test_each_verdict(self):
        ov, _data = _resolved()
        self.assertEqual(ov.verdicts, [O.APPLIED, O.APPLIED, O.UPSTREAM, O.STALE, O.STALE,
                                       O.LIBRARY_ROW, O.APPLIED, O.APPLIED, O.STALE])
        self.assertEqual(ov.details[4], "no such path")
        self.assertEqual(ov.details[8], "not in the mirror")
        s = ov.summary()
        self.assertEqual(s["counts"][O.APPLIED], 4)
        self.assertEqual([x["article"] for x in s["not_applied"]], [3, 4, 4, 5, 77])
        self.assertEqual(s["copies_applied"], 2)        # 7's and 8's copies in 6

    def test_malformed_and_duplicate(self):
        rows = [_row(1, ["lemmas", 0, "lemma"], "badehette", "badehatt"),
                _row(1, TEXT_PATH, "vanttett hodeplagg til bading", "vanntett hodeplagg til bading"),
                _row(1, TEXT_PATH, "vanttett hodeplagg til bading", "vanntett hodeplagg for bading"),
                _row(1, TEXT_PATH, "vanttett", "vanntett", kind="nonsense")]
        ov, _data = _resolved(rows)
        self.assertEqual(ov.verdicts, [O.MALFORMED, O.APPLIED, O.DUPLICATE, O.MALFORMED])

    def test_apply_text_and_reference(self):
        ov, data = _resolved()
        raw = copy.deepcopy(data)
        one = ov.apply(1, data[1])
        self.assertEqual(O._get(one, TEXT_PATH), "vanntett hodeplagg til bading")
        two = ov.apply(2, data[2])
        self.assertEqual(O._get(two, REF_PATH)["article_id"], 5)
        self.assertEqual(O._get(two, REF_PATH)["lemmas"], [{"lemma": "x"}])
        self.assertIs(ov.apply(3, data[3]), data[3])            # upstream: untouched
        self.assertIs(ov.apply(4, data[4]), data[4])            # stale: untouched
        self.assertIs(ov.apply(5, data[5]), data[5])            # library row: untouched
        self.assertEqual(data, raw, "the mirror's data was changed in place")

    def test_absent_key_is_null_and_any_object(self):
        """The writer's shapes (2026-11-10): a key the object lacks is `null` in `before` and
        `after` adds it (*underprivilegert*'s `word_form`); a reference's `definition_id: null`
        retargeted (*ratt* II); a usage item's `text`; a DEFINITION node's `id`
        (`duplicate-def-id`, *uhørt*)."""
        data = {1: {"body": {"definitions": [
            {"type_": "definition", "id": 4, "elements": [
                {"type_": "explanation", "content": "$ og $", "items": [
                    {"type_": "article_ref", "article_id": 9, "lemmas": [{"lemma": "x"}]},
                    {"type_": "usage", "text": "Brassica olracea"},
                    {"type_": "article_ref", "article_id": 23105, "definition_id": None}]}]}]}}}
        item = ["body", "definitions", 0, "elements", 0, "items"]
        rows = [_row(1, item + [0], {"word_form": None}, {"word_form": "privilegier"}),
                _row(1, item + [1], {"text": "Brassica olracea"}, {"text": "Brassica oleracea"}),
                _row(1, item + [2], {"article_id": 23105, "definition_id": None},
                     {"article_id": 22945, "definition_id": 10}, kind="ref-retarget"),
                _row(1, ["body", "definitions", 0], {"id": 4}, {"id": 1}, kind="duplicate-def-id"),
                _row(1, item + [0], {"definition_id": 3}, {"definition_id": 1}, kind="ref-anchor")]
        ov = O.Overlay(rows, kinds=KINDS).resolve(lambda a: data.get(a), lambda ids: {})
        self.assertEqual(ov.verdicts, [O.APPLIED] * 4 + [O.STALE])
        got = ov.apply(1, data[1])
        its = O._get(got, item)
        self.assertEqual(its[0]["word_form"], "privilegier")
        self.assertEqual(its[1]["text"], "Brassica oleracea")
        self.assertEqual((its[2]["article_id"], its[2]["definition_id"]), (22945, 10))
        self.assertEqual(got["body"]["definitions"][0]["id"], 1)
        self.assertNotIn("word_form", O._get(data[1], item)[0])      # the raw data untouched
        # the fixed text again: upstream (an absent key and null alike)
        again = O.Overlay(rows[:1], kinds=KINDS).resolve(lambda a: got, lambda ids: {})
        self.assertEqual(again.verdicts, [O.UPSTREAM])

    def test_upstream_in_its_article_applied_in_a_copy(self):
        """*på alle bauger og kanter* 115367: ordbokene fixed its own article, not the copy
        *baug* embeds — the row is `upstream`, its copy applied, and the summary says both."""
        rows = copy.deepcopy(ROWS)
        rows[7]["data"]["body"]["definitions"][0]["elements"][1]["quote"]["content"] =             "tretti filmar er meldt på"
        data = {r["id"]: r["data"] for r in rows}
        ov = O.Overlay([CORRECTIONS[6]], kinds=KINDS).resolve(
            lambda a: data.get(a), lambda ids: {7: [6]})
        self.assertEqual(ov.verdicts, [O.UPSTREAM])
        s = ov.summary()
        self.assertEqual(s["copies"], [{"article": 7, "lemma": "x", "verdict": O.UPSTREAM,
                                        "copies": {"6": [O.APPLIED]}}])
        self.assertEqual(s["not_applied"][0]["copies"], {"6": [O.APPLIED]})
        self.assertIn("tretti filmar er meldt på",
                      json.dumps(ov.apply(6, data[6]), ensure_ascii=False))

    def test_expression_reaches_every_copy(self):
        ov, data = _resolved()
        own = ov.apply(7, data[7])
        self.assertEqual(O._get(own, EX_PATH), "tretti filmar er meldt på")
        parent = ov.apply(6, data[6])
        copies = {c["article_id"]: c for c in (O._copies(parent, 7) + O._copies(parent, 8))}
        self.assertEqual(O._get(copies[7], EX_PATH), "tretti filmar er meldt på")
        self.assertEqual(O._get(copies[8], EX_PATH), "hun meldte seg av kurset i går")
        self.assertEqual(ov.copies[6], {6: [O.APPLIED]})

    def test_a_copy_that_differs_is_left_alone(self):
        rows = copy.deepcopy(ROWS)
        sub = rows[6]["data"]["body"]["definitions"][0]["elements"][1]
        sub["article"]["body"]["definitions"][0]["elements"][1]["quote"]["content"] = "annen tekst"
        data = {r["id"]: r["data"] for r in rows}
        ov = O.Overlay([CORRECTIONS[6]], kinds=KINDS).resolve(
            lambda a: data.get(a), lambda ids: {7: [6]})
        self.assertEqual(ov.verdicts, [O.APPLIED])              # its own article took it
        self.assertEqual(ov.copies[0], {6: [O.STALE]})
        self.assertIs(ov.apply(6, data[6]), data[6])

    def test_no_file(self):
        ov = O.Overlay.load(os.path.join(tempfile.gettempdir(), "no-such-overlay-182.jsonl"))
        self.assertFalse(ov)
        self.assertEqual(ov.summary()["rows"], 0)


class MirrorAndChecker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.mirror_path, cls.corr = _write(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _mirror(self, with_overlay=True):
        m = M.Mirror(self.mirror_path)
        m.index()
        if with_overlay:
            m.set_overlay(O.Overlay.load(self.corr, library_ids=(5,), kinds=KINDS))
        return m

    def test_data_and_raw_data(self):
        m = self._mirror()
        self.assertEqual(O._get(m.data(1), TEXT_PATH), "vanntett hodeplagg til bading")
        self.assertEqual(O._get(m.raw_data(1), TEXT_PATH), "vanttett hodeplagg til bading")
        self.assertEqual(O._get(m.row(1)["data"], TEXT_PATH), "vanttett hodeplagg til bading")
        self.assertTrue(m.touched(6))
        self.assertFalse(m.touched(9))
        m.close()

    def test_no_file_changes_nothing(self):
        m = self._mirror(with_overlay=False)
        self.assertIsNone(m.set_overlay(O.Overlay.load(self.corr + ".absent")) or None)
        self.assertIsNone(m.overlay)
        self.assertIs(m.data(1), m.row(1)["data"])
        m.close()

    def test_checker_reads_the_raw_mirror(self):
        m = self._mirror()
        store = L.Store(m, [])
        self.assertIn("vanntett", json.dumps(store.derived(1), ensure_ascii=False))
        self.assertIn("vanttett", json.dumps(store.raw_derived(1), ensure_ascii=False))
        ch = C.Checker(store, rows=[], has_page=lambda a: a in m,
                       overlay_rows=m.overlay.applied_rows())
        got = {r["article"]: v for r, v in ch.verdicts}
        self.assertEqual(got[1], C.SHOWN)
        self.assertEqual(got[2], C.SHOWN)
        self.assertEqual(got[7], C.SHOWN)
        self.assertEqual(got[8], C.NOT_SHOWN)       # no page of its own; its parent shows it
        self.assertEqual(ch.notice[1], [("typo", 1)])
        self.assertEqual(ch.notice[2], [("xref", 1)])
        s = ch.summary()
        self.assertEqual(s["about"]["spelling"], {"corrections": 2, "articles": 2})
        self.assertEqual(s["about"]["xref"], {"corrections": 1, "articles": 1})
        self.assertEqual(s["overlay_shown"], 3)
        self.assertEqual([x.get("overlay") for x in s["not_shown"]], [True])
        m.close()


def _build(args, timeout=900):
    return subprocess.run([sys.executable, os.path.join(ORDPAR, "build_site.py")] + args,
                          cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                          timeout=timeout, env=dict(os.environ, PYTHONUTF8="1"))


def _read(path):
    with open(path, "rb") as f:
        return f.read()


class Build(unittest.TestCase):
    """Two synthetic builds, with the file and with none."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        mirror, corr = _write(cls.tmp)
        library = os.path.join(cls.tmp, "articles.jsonl")
        open(library, "w").close()
        # marked as gated, so the public repository's build (no scripts/triage.py) takes it too
        # (decisions 184, `sitegen/gate.py`); the private side gates it with triage as before
        from ordpar.sitegen import gate
        gate.write_marker(library, 0, 0)
        cls.runs = {}
        for name, path in (("with", corr), ("without", corr + ".absent")):
            out = os.path.join(cls.tmp, "out-" + name)
            proc = _build(["--mirror", mirror, "--articles", library, "--out", out,
                           "--snippets", os.path.join(cls.tmp, "snip-%s.json" % name),
                           "--mirror-corrections", path,
                           "--ids", "1", "2", "3", "4", "5", "6", "7", "9"])
            cls.runs[name] = (proc, out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def out(self, name):
        proc, out = self.runs[name]
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace")[-3000:])
        return out

    def page(self, name, aid):
        return _read(os.path.join(self.out(name), "bm-en", str(aid), "index.html")).decode("utf-8")

    def build_json(self, name):
        with open(os.path.join(self.out(name), "build.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_text_fix_and_notice(self):
        p = self.page("with", 1)
        self.assertIn("vanntett", p)
        self.assertNotIn("vanttett", p)
        self.assertIn('class="ordpar-change"', p)
        q = self.page("without", 1)
        self.assertIn("vanttett", q)
        self.assertNotIn('class="ordpar-change"', q)

    def test_reference_fix(self):
        p, q = self.page("with", 2), self.page("without", 2)
        self.assertIn("/bm-en/5", p)
        self.assertNotIn("/bm-en/4", p)
        self.assertIn("/bm-en/4", q)
        self.assertIn('class="ordpar-change"', p)

    def test_expression_on_its_parent(self):
        p = self.page("with", 6)
        self.assertIn("i går", p)                     # 8: only the parent's copy carries it
        self.assertIn("meldt på", p)                   # 7: its own article, corrected
        self.assertIn("meldt på", self.page("with", 7))

    def test_untouched_pages_identical(self):
        for aid in (3, 4, 9):
            self.assertEqual(self.page("with", aid), self.page("without", aid), aid)

    def test_build_json(self):
        rec = self.build_json("with")["mirror_corrections"]
        self.assertTrue(rec["present"])
        # the build's library is empty, so 5 is no library row here: its row is applied
        self.assertEqual(rec["counts"]["applied"], 5)
        self.assertEqual(rec["counts"]["upstream"], 1)
        self.assertEqual(rec["counts"]["stale"], 3)
        self.assertEqual(rec["counts"]["library_row"], 0)
        self.assertEqual(sorted(x["article"] for x in rec["not_applied"]), [3, 4, 4, 77])
        none = self.build_json("without")["mirror_corrections"]
        self.assertFalse(none["present"])
        self.assertEqual(none["rows"], 0)
        self.assertNotIn("1", self.build_json("without")["change_notice"]["notice"])
        self.assertIn("1", self.build_json("with")["change_notice"]["notice"])

    def test_about_counts(self):
        a = self.build_json("with")["site_stats"]["corrections"]["about"]
        b = self.build_json("without")["site_stats"]["corrections"]["about"]
        self.assertEqual(a["spelling"]["corrections"] - b["spelling"]["corrections"], 3)
        self.assertEqual(a["xref"]["corrections"] - b["xref"]["corrections"], 1)


REAL_FIX = {"article": 4022, "lemma": "badehette", "kind": "typo", "sheet": "Skrivefeil",
            "where": "betydning 1 (definisjon id 2), forklaring 1",
            "path": ["body", "definitions", 0, "elements", 0, "content"],
            "before": "vanttett hodeplagg som holder håret tørt under bading",
            "after": "vanntett hodeplagg som holder håret tørt under bading",
            "before_text": "vanttett hodeplagg som holder håret tørt under bading",
            "after_text": "vanntett hodeplagg som holder håret tørt under bading",
            "defect": "theirs", "verified_live": "2026-11-10", "date": "2026-11-10",
            "handover": "2026-11-09 Skrivefeil row 29"}


@unittest.skipUnless(os.path.exists(REAL_MIRROR), "no mirror at %s" % REAL_MIRROR)
class RealBuild(unittest.TestCase):
    """`build_site.py --ids` over the real mirror and library, with one real fix."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        corr = os.path.join(cls.tmp, "mirror-corrections.jsonl")
        with open(corr, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(REAL_FIX, ensure_ascii=False) + "\n")
        cls.runs = {}
        for name, path in (("with", corr), ("without", corr + ".absent")):
            out = os.path.join(cls.tmp, "out-" + name)
            cls.runs[name] = (_build(["--mirror", REAL_MIRROR, "--out", out,
                                      "--snippets", os.path.join(cls.tmp, "snip-%s.json" % name),
                                      "--mirror-corrections", path, "--ids", "4022", "2802"]),
                              out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def page(self, name, aid):
        proc, out = self.runs[name]
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace")[-3000:])
        return _read(os.path.join(out, "bm-en", str(aid), "index.html")).decode("utf-8")

    def test_the_fix_shows_with_its_notice(self):
        p = self.page("with", 4022)
        self.assertIn("vanntett hodeplagg", p)
        self.assertNotIn("vanttett", p)
        self.assertIn('class="ordpar-change"', p)
        self.assertIn('href="https://ordbokene.no/nob/bm/4022"', p)

    def test_other_page_identical(self):
        self.assertEqual(self.page("with", 2802), self.page("without", 2802))


if __name__ == "__main__":
    unittest.main()
