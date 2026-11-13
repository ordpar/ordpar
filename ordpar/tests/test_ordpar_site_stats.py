"""Pins `ordpar/site_stats.py`'s counting rules on a tiny fixture (Robin, 2026-10-22: the About
page's statistics, kept as a script so the numbers can be updated as the library grows):

* every article ordbokene shows counts — any `status` but none and 1 (2026-10-22: statuses 2–6 are
  shown, not only 8); a translated article is one with a library row;
* a line is one etymology segment, explanation, example or compound-list item; a fixed
  expression's "Se: …" line is not one;
* running words are whitespace-separated pieces with a letter, digit or `$`; an example's quote
  and explanation both count; a compound item is one word;
* the unit walk agrees with the parent repo's `scripts/coverage.py` `count_units`;
* the translated split into complete (a summary gloss) and without a summary;
* `--json` writes the same counts;
* the added example sentences (`ex_added`, senses and subsenses) count over the shown articles
  only, as sentences, articles and senses; `measure(rows=…)` takes the rows the build holds
  (2026-10-22, the About page's "N sentences in M articles").

Stdlib unittest."""

import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from ordpar import site_stats as S  # noqa: E402
import coverage as C  # noqa: E402  (scripts/coverage.py)


def _expl(text):
    return {"type_": "explanation", "content": text, "items": []}


def _ex(quote, expl=""):
    return {"type_": "example", "quote": {"content": quote, "items": []},
            "explanation": {"content": expl, "items": []}}


def _article(aid, status=8, expr=False, body=None):
    tags = ["EXPR"] if expr else ["NOUN"]
    return {"id": aid, "data": {"article_id": aid, "status": status, "body": body or {},
                                "lemmas": [{"lemma": "ord%d" % aid, "paradigm_info": [{"tags": tags}]}]}}   # a headword: 163


# 1: etymology (2 words), a sense (3 words + `$`), two examples (2 + 3 words, "-" not a word),
#    a subsense (2 words), a compound list of two items
A1 = _article(1, body={
    "etymology": [{"type_": "etymology_reference", "content": "av $", "items": []}],
    "definitions": [{"type_": "definition", "elements": [
        _expl("holdning , politisk $ retning"),
        _ex("religiøs aktivisme"),
        _ex("ta det - rolig", ""),
        {"type_": "definition", "elements": [_expl("en undersans")]},
        {"type_": "compound_list", "elements": [{"type_": "article_ref"}, {"type_": "article_ref"}]},
    ]}]})
# 2: a fixed expression whose "Se:" line is left out; one example with quote and explanation
A2 = _article(2, expr=True, body={"definitions": [{"type_": "definition", "elements": [
    _expl("Se: noe annet"), _expl("gjøre noe"), _ex("gjøre det", "altså nå")]}]})
# 3: status 1, which ordbokene's search does not show — never counted
A3 = _article(3, status=1, body={"definitions": [{"type_": "definition",
                                                  "elements": [_expl("utkast her")]}]})


class SiteStats(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.mirror = os.path.join(cls.tmp, "m.jsonl")
        cls.lib = os.path.join(cls.tmp, "a.jsonl")
        with io.open(cls.mirror, "w", encoding="utf-8") as f:
            for a in (A1, A2, A3):
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        with io.open(cls.lib, "w", encoding="utf-8") as f:
            f.write(json.dumps({"id": 2, "summary": {"gloss": ["do something"]}}) + "\n")
            f.write(json.dumps({"id": 1, "summary": None}) + "\n")
            f.write(json.dumps({"id": 3}) + "\n")      # a draft's row: still not counted

    def test_text_of(self):
        self.assertEqual(S.text_of(A1["data"]), (7, 2 + 4 + 2 + 3 + 2 + 2))
        self.assertEqual(S.text_of(A2["data"]), (2, 2 + 2 + 2))

    def test_words(self):
        self.assertEqual(S.words("ta det - rolig"), 3)
        self.assertEqual(S.words("av $ , 1)"), 3)
        self.assertEqual(S.words(""), 0)

    def test_agrees_with_coverage(self):
        for a in (A1, A2):
            c = C.count_units(a["data"])
            see = C._see_lines(a["data"]) if C.is_expr_source(a["data"]) else 0
            self.assertEqual(S.text_of(a["data"])[0], sum(c.values()) - see)

    def test_measure(self):
        m = S.measure(self.mirror, self.lib)
        self.assertEqual(m["articles"], {"all": 2, "translated": 2, "share": 1.0,
                                         "complete": 1, "no_summary": 1})
        self.assertEqual((m["lines"]["all"], m["lines"]["translated"]), (9, 9))
        self.assertEqual((m["words"]["all"], m["words"]["translated"]), (21, 21))

    def test_shown_statuses(self):
        # statuses 2-6 are shown by ordbokene and count; none and 1 do not (sampled 2026-10-22)
        m = os.path.join(self.tmp, "st.jsonl")
        body = {"definitions": [{"type_": "definition", "elements": [_expl("noe her")]}]}
        with io.open(m, "w", encoding="utf-8") as f:
            for i, st in enumerate((8, 5, 2, 6, 1, None), 10):
                f.write(json.dumps(_article(i, status=st, body=body)) + chr(10))
        lib = os.path.join(self.tmp, "st-lib.jsonl")
        with io.open(lib, "w", encoding="utf-8") as f:
            f.write("")
        self.assertEqual(S.measure(m, lib)["articles"]["all"], 4)

    def test_measure_part(self):
        lib = os.path.join(self.tmp, "b.jsonl")
        with io.open(lib, "w", encoding="utf-8") as f:
            f.write(json.dumps({"id": 2}) + "\n")
        m = S.measure(self.mirror, lib)
        self.assertEqual(m["articles"], {"all": 2, "translated": 1, "share": 0.5,
                                         "complete": 0, "no_summary": 1})
        self.assertEqual((m["lines"]["translated"], m["words"]["translated"]), (2, 6))

    def test_added(self):
        rows = [{"id": 1, "senses": [
                    {"ex_added": [{"no": "a"}, {"no": "b"}],
                     "subs": [{"ex_added": [{"no": "c"}]}, {"ex": [["d", "e"]]}]},
                    {"ex_added": []}]},
                {"id": 2, "summary": {"gloss": ["x"]}, "senses": [{"subs": []}]},
                {"id": 3, "senses": [{"ex_added": [{"no": "hidden"}]}]},     # status 1
                {"id": 99, "senses": [{"ex_added": [{"no": "no page"}]}]}]   # not in the mirror
        m = S.measure(self.mirror, rows=rows)
        self.assertEqual(m["added"], {"sentences": 3, "articles": 1, "senses": 2})
        self.assertEqual((m["articles"]["translated"], m["articles"]["complete"]), (2, 1))
        self.assertEqual(S.measure(self.mirror, self.lib)["added"],
                         {"sentences": 0, "articles": 0, "senses": 0})

    def test_json(self):
        out = os.path.join(self.tmp, "s.json")
        with open(os.devnull, "w") as null:
            saved, sys.stdout = sys.stdout, null
            try:
                S.main(["--mirror", self.mirror, "--articles", self.lib, "--build-json", "",
                        "--json", out])
            finally:
                sys.stdout = saved
        with io.open(out, encoding="utf-8") as f:
            got = json.load(f)
        self.assertEqual(got["words"]["translated"], 21)
        self.assertNotIn("site_pages", got)


if __name__ == "__main__":
    unittest.main()
