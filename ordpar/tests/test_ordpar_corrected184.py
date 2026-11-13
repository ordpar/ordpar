"""Pins the corrected copy of Bokmålsordboka the public export ships (decisions 184, Robin
2026-11-12: "Yes, corrected copy"; `ordpar/corrected_copy.py`).

1. **The normalization log made into patches** (`derive_patches`): a capture's text fix that its
   log row explains becomes a patch whose `before` is the raw value and whose `after` is that value
   with only the row's replacement made; a reference fix becomes a patch on the item's ids; a
   difference no row explains, a capture's older text, a headword difference, a lemma-order row and
   a registry pointer make none, and are listed with their reason.
2. **The copy** (`write`): both sets through the overlay — a fix applied where the raw value is
   exactly `before`; a mirror correction whose value changed listed `stale`, one ordbokene made
   itself `upstream`; an expression's fix reaching a parent's embedded copy; every row and log
   line in `fixes.jsonl` with its verdict; an untouched article byte for byte the raw line; the
   raw mirror file never written; a second run byte-identical.
3. **The export's side**: the copy lives under the mirror's folder (Bokmålsordboka's data for the
   guard), its joined file is git-ignored, and the projected log keeps `path`.

The site build is untouched by all this (it still loads `overlay.Overlay` with the library's ids
and only the mirror corrections): `test_ordpar_overlay182` and `test_ordpar_export184` pin it.
Pure Python, synthetic files in a temporary folder.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)

import corrected_copy as C  # noqa: E402
import data_parts  # noqa: E402
import export_public as X  # noqa: E402
from ordpar.sitegen.deck import fetch  # noqa: E402


def art(aid, defs, lemma="ord", extra=None):
    d = {"article_id": aid, "lemmas": [{"lemma": lemma, "hgno": 0}], "author": "someone",
         "body": {"definitions": [{"type_": "definition", "id": 1, "elements": defs}]}}
    d.update(extra or {})
    return d


def expl(text, items=()):
    return {"type_": "explanation", "content": text, "items": list(items)}


def example(text):
    return {"type_": "example", "quote": {"content": text, "items": []}}


def ref(target, defn, order):
    return {"type_": "article_ref", "article_id": target, "definition_id": defn,
            "definition_order": order, "lemmas": [{"lemma": "mål"}]}


def sub(eid, body_text):
    return {"type_": "sub_article", "article_id": eid, "lemmas": [{"lemma": "uttrykk"}],
            "article": {"article_id": eid, "lemmas": [{"lemma": "uttrykk"}], "referenced_by": [1],
                        "body": {"definitions": [{"type_": "definition", "id": 1,
                                                  "elements": [expl(body_text)]}]}}}


class Fixture(object):
    """A mirror, captures, a normalization log and a mirror-corrections file in a temp folder."""

    def __init__(self, test):
        self.dir = tempfile.mkdtemp()
        test.addCleanup(shutil.rmtree, self.dir, True)
        self.mirror = os.path.join(self.dir, "bm-articles.jsonl")
        self.captures = os.path.join(self.dir, "articles")
        os.makedirs(self.captures)
        self.log = os.path.join(self.dir, "source-normalizations.jsonl")
        self.corr = os.path.join(self.dir, "mirror-corrections.jsonl")
        self.out = os.path.join(self.dir, "corrected")
        self.rows = {}
        self.log_rows = []
        self.corr_rows = []

    def article(self, aid, data, capture=None):
        """`data` in the mirror; `capture(pruned copy)` edits the capture (None: no capture)."""
        self.rows[aid] = data
        if capture is not None:
            cap = json.loads(json.dumps(fetch.prune_article(data)))
            capture(cap)
            with open(os.path.join(self.captures, "%d.json" % aid), "w", encoding="utf-8") as fh:
                json.dump(cap, fh, ensure_ascii=False)

    def norm(self, **row):
        self.log_rows.append(row)

    def correction(self, **row):
        self.corr_rows.append(row)

    def flush(self):
        with open(self.mirror, "w", encoding="utf-8", newline="\n") as fh:
            for aid in sorted(self.rows):
                fh.write(json.dumps({"id": aid, "revision": "1", "updated_at": "x",
                                     "data": self.rows[aid]}, ensure_ascii=False) + "\n")
        for path, rows in ((self.log, self.log_rows), (self.corr, self.corr_rows)):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    def write(self):
        self.flush()
        return C.write(self.mirror, self.out, log_path=self.log, corrections_path=self.corr,
                       captures=self.captures)

    def patches(self):
        self.flush()
        m = C.MirrorFile(self.mirror)
        try:
            return C.derive_patches(m, C.read_log(self.log), self.captures)
        finally:
            m.close()

    def corrected(self):
        out = {}
        for name in data_parts.parts(self.out):
            with open(os.path.join(self.out, name), encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    out[r["id"]] = r["data"]
        return out

    def fixes(self):
        with open(os.path.join(self.out, C.FIXES_NAME), encoding="utf-8") as fh:
            return [json.loads(l) for l in fh]


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def set_path(root, path, value):
    node = root
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value


CONTENT = ["body", "definitions", 0, "elements", 0, "content"]
QUOTE = ["body", "definitions", 0, "elements", 1, "quote", "content"]


class Patches(unittest.TestCase):

    def test_text_fix_explained_by_its_row(self):
        f = Fixture(self)
        f.article(10, art(10, [expl("en fornem restaturant"), example("hum kommer")]),
                  lambda c: set_path(c, CONTENT, "en fornem restaurant"))
        f.norm(article=10, lemma="ord", kind="typo", where="def", before="'en fornem restaturant'",
               after="'en fornem restaurant'")
        patches, status = f.patches()
        self.assertEqual(len(patches), 1)
        p = patches[0]
        self.assertEqual((p["article"], p["path"], p["before"], p["after"], p["how"], p["log"]),
                         (10, CONTENT, "en fornem restaturant", "en fornem restaurant", "text", [1]))
        self.assertEqual(status, {})

    def test_word_level_row_and_two_rows_one_string(self):
        f = Fixture(self)
        f.article(11, art(11, [expl("i det fleste landene foran landnummeret")]),
                  lambda c: set_path(c, CONTENT, "i de fleste landene foran landsnummeret"))
        f.norm(article=11, kind="typo", before="i det fleste landene", after="i de fleste landene")
        f.norm(article=11, kind="typo", before="landnummeret", after="landsnummeret")
        patches, status = f.patches()
        self.assertEqual([(p["after"], p["log"]) for p in patches],
                         [("i de fleste landene foran landsnummeret", [1, 2])])

    def test_older_capture_text_never_leaks(self):
        # ordbokene rewrote the sentence since the capture: the capture's text holds the fix and
        # the OLD wording, so the log no longer explains the difference: no patch, listed
        f = Fixture(self)
        f.article(12, art(12, [expl("en ny og fin restaturant")]),
                  lambda c: set_path(c, CONTENT, "en fornem restaurant"))
        f.norm(article=12, kind="typo", before="en fornem restaturant", after="en fornem restaurant")
        patches, status = f.patches()
        self.assertEqual(patches, [])
        self.assertEqual(status[1][0], C.NOT_LOCATED)

    def test_unlogged_difference_and_other_fields_untouched(self):
        # the capture also differs where no row speaks (an older example): only the logged fix
        f = Fixture(self)
        f.article(13, art(13, [expl("kraktertrekk"), example("ny tekst")]),
                  lambda c: (set_path(c, CONTENT, "karaktertrekk"), set_path(c, QUOTE, "gammel tekst")))
        f.norm(article=13, kind="typo", before="kraktertrekk", after="karaktertrekk")
        patches, _s = f.patches()
        self.assertEqual([p["path"] for p in patches], [CONTENT])

    def test_upstream_fixed_row(self):
        f = Fixture(self)
        f.article(14, art(14, [expl("en fornem restaurant")]), lambda c: None)
        f.norm(article=14, kind="typo", before="restaturant", after="restaurant")
        patches, status = f.patches()
        self.assertEqual(patches, [])
        self.assertEqual(status[1], (C.NOT_LOCATED, "ordbokene's text carries the fix (upstream)"))

    def test_reference_fix(self):
        f = Fixture(self)
        f.article(15, art(15, [expl("se $", [ref(40, 13, 4)])]),
                  lambda c: c["body"]["definitions"][0]["elements"][0]["items"][0].update(
                      definition_id=7, definition_order=1))
        f.norm(article=15, kind="ref-anchor", before='#def13 ("om noe")', after='#def7 ("om lys")')
        patches, _s = f.patches()
        self.assertEqual(len(patches), 1)
        p = patches[0]
        self.assertEqual(p["path"], ["body", "definitions", 0, "elements", 0, "items", 0])
        self.assertEqual((p["before"], p["after"], p["how"]),
                         ({"definition_id": 13, "definition_order": 4},
                          {"definition_id": 7, "definition_order": 1}, "reference"))

    def test_reference_numbers_must_match(self):
        f = Fixture(self)
        f.article(16, art(16, [expl("se $", [ref(40, 13, 4)])]),
                  lambda c: c["body"]["definitions"][0]["elements"][0]["items"][0].update(definition_id=9))
        f.norm(article=16, kind="ref-anchor", before="#def13", after="#def7")
        patches, status = f.patches()
        self.assertEqual(patches, [])

    def test_headword_lemma_order_and_pointer_make_no_patch(self):
        f = Fixture(self)
        f.article(17, art(17, [expl("x")], lemma="gåsa  vann"),
                  lambda c: c["lemmas"][0].update(lemma="gåsa vann"))
        f.norm(article=17, kind="typo", where="lemma", before="'gåsa  vann' (double space)",
               after="single space")
        f.norm(article=17, kind="lemma-order", where="top-level lemmas order", before="a, b", after="b, a")
        f.norm(article=None, kind="registry-pointer:dangling-ref", before="x", after="NOT corrected")
        f.norm(article=None, lemma="gi ut", kind="typo", before="a", after="b")
        patches, status = f.patches()
        self.assertEqual(patches, [])
        self.assertEqual({k: v[0] for k, v in status.items()},
                         {1: C.HEADWORD, 2: C.DISPLAY, 3: C.NOT_FIX, 4: C.NO_ARTICLE})


class Copy(unittest.TestCase):

    def fixture(self):
        f = Fixture(self)
        # 1: a normalisation applied; 2: an expression with a mirror correction, embedded in 3;
        # 4: a correction ordbokene made itself; 5: a correction whose text changed; 6: untouched
        f.article(1, art(1, [expl("en fornem restaturant")]),
                  lambda c: set_path(c, CONTENT, "en fornem restaurant"))
        f.norm(article=1, lemma="ord", kind="typo", before="restaturant", after="restaurant")
        f.article(2, art(2, [expl("sitte inn med noe")], lemma="uttrykk"))
        f.article(3, {"article_id": 3, "lemmas": [{"lemma": "sitte"}],
                      "body": {"definitions": [{"type_": "definition", "id": 1,
                                                "elements": [sub(2, "sitte inn med noe")]}]}})
        f.correction(article=2, lemma="uttrykk", kind="typo", path=CONTENT,
                     before="sitte inn med noe", after="sitte inne med noe")
        f.article(4, art(4, [expl("riktig")]))
        f.correction(article=4, kind="typo", path=CONTENT, before="rikitg", after="riktig")
        f.article(5, art(5, [expl("helt annen tekst")]))
        f.correction(article=5, kind="typo", path=CONTENT, before="feil", after="rett")
        f.article(6, art(6, [expl("urørt æøå")]), lambda c: None)
        return f

    def test_the_copy(self):
        f = self.fixture()
        raw_before = read(f.mirror) if os.path.exists(f.mirror) else None
        counts = f.write()
        got = f.corrected()
        self.assertEqual(got[1]["body"]["definitions"][0]["elements"][0]["content"], "en fornem restaurant")
        self.assertEqual(got[2]["body"]["definitions"][0]["elements"][0]["content"], "sitte inne med noe")
        copy = got[3]["body"]["definitions"][0]["elements"][0]["article"]
        self.assertEqual(copy["body"]["definitions"][0]["elements"][0]["content"], "sitte inne med noe")
        self.assertEqual(got[4], f.rows[4])
        self.assertEqual(got[5], f.rows[5])
        self.assertEqual(counts["mirror_corrections"], {"applied": 1, "upstream": 1, "stale": 1})
        self.assertEqual(counts["patch_verdicts"], {"applied": 1})
        self.assertEqual(counts["articles_changed"], 3)
        self.assertEqual(counts["copies_applied"], 1)
        self.assertIsNone(raw_before)

    def test_fixes_list(self):
        f = self.fixture()
        f.norm(article=6, kind="typo", before="urort", after="urørt")
        f.write()
        fixes = f.fixes()
        by = {(x["source"], x["article"]): x for x in fixes}
        self.assertEqual(by[("mirror-corrections", 2)]["verdict"], "applied")
        self.assertEqual(by[("mirror-corrections", 2)]["copies"], {"3": ["applied"]})
        self.assertEqual(by[("mirror-corrections", 2)]["line"], 1)
        self.assertEqual(by[("mirror-corrections", 4)]["verdict"], "upstream")
        self.assertEqual(by[("mirror-corrections", 5)]["verdict"], "stale")
        self.assertEqual(by[("source-normalizations", 1)]["verdict"], "applied")
        self.assertEqual(by[("source-normalizations", 1)]["log_lines"], [1])
        self.assertEqual(by[("source-normalizations", 6)]["verdict"], C.NOT_LOCATED)
        self.assertEqual(len(fixes), 3 + 2)

    def test_raw_untouched_and_untouched_lines_identical(self):
        f = self.fixture()
        f.flush()
        raw = read(f.mirror)
        f.write()
        self.assertEqual(read(f.mirror), raw)
        joined, n = data_parts.join(f.out, os.path.join(f.dir, "joined.jsonl"))
        a, b = raw.splitlines(), read(joined).splitlines()
        self.assertEqual(n, 6)
        self.assertEqual([i for i, (x, y) in enumerate(zip(a, b)) if x != y], [0, 1, 2])

    def test_rerun_byte_identical(self):
        f = self.fixture()
        f.write()
        first = {n: read(os.path.join(f.out, n)) for n in sorted(os.listdir(f.out))}
        f.write()
        second = {n: read(os.path.join(f.out, n)) for n in sorted(os.listdir(f.out))}
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), ["bm-articles.000000.jsonl", C.FIXES_NAME, C.PATCHES_NAME])

    def test_a_patch_on_a_corrected_field_is_duplicate(self):
        f = Fixture(self)
        f.article(7, art(7, [expl("restaturant")]), lambda c: set_path(c, CONTENT, "restaurant"))
        f.norm(article=7, kind="typo", before="restaturant", after="restaurant")
        f.correction(article=7, kind="typo", path=CONTENT, before="restaturant", after="restaurant")
        counts = f.write()
        self.assertEqual(counts["mirror_corrections"], {"applied": 1})
        self.assertEqual(counts["patch_verdicts"], {"duplicate": 1})
        self.assertEqual(f.corrected()[7]["body"]["definitions"][0]["elements"][0]["content"], "restaurant")


class ExportSide(unittest.TestCase):

    def test_layout(self):
        self.assertTrue(X.CORRECTED_OUT.startswith(X.MIRROR_OUT + "/"))
        self.assertTrue((X.CORRECTED_OUT + "/x").startswith(X.THEIR_DATA))
        self.assertIn(X.CORRECTED_OUT + "/bm-articles.jsonl", X.GITIGNORE.splitlines())
        self.assertIn("path", X.NORMALIZATION_FIELDS)

    def test_projected_log_remakes_the_same_patches(self):
        f = Fixture(self)
        f.article(1, art(1, [expl("en fornem restaturant")]),
                  lambda c: set_path(c, CONTENT, "en fornem restaurant"))
        f.norm(article=1, lemma="ord", kind="typo", before="restaturant", after="restaurant",
               why="w", reporter="someone", path=CONTENT)
        full = f.patches()
        data = X.normalizations(f.log)
        self.assertNotIn(b"someone", data)
        with open(f.log, "wb") as fh:
            fh.write(data)
        m = C.MirrorFile(f.mirror)
        try:
            projected = C.derive_patches(m, C.read_log(f.log), f.captures)
        finally:
            m.close()
        self.assertEqual(full, projected)
        self.assertEqual(len(full[0]), 1)


if __name__ == "__main__":
    unittest.main()
