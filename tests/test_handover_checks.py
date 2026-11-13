#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the ordbokene handover detection scripts (``handover/checks/``).

Run:  python tests/test_handover_checks.py

Each of the seven checks gets at least one hand-built article that must be reported and
one that must not, in the public API's article shape, read from a temporary directory
of <id>.json files (and once from a JSONL file with the mirror's {"id", "data"} wrapper).
Also pinned: unpublished articles are skipped; an embedded fixed expression (sub_article)
never lends its definition ids to its host, and its copy is read only for what the
expression's own article lacks (all of it when there is no such article); the straight-apostrophe closing quote is its
own finding type, not "unmatched"; Latin binomials are not doubled words. Check 7's
Latin-name skip, one test per shape (rank abbreviation, trinomial, hybrid sign, a genus
that is a Bokmål form) and the Norwegian it must still read; its compound mark, which
never drops a row and stays off a slip one edit from a known form. The sense numbers
follow ordbokene's own, including an article whose one top sense holds the numbered ones.
The intro line of a compound list is read as text (place, kind, items, numbering).
Nynorsk mode (--dictionary nn, 2026-11-13): check 7 labels a Bokmål form in Nynorsk text
bokmal_form and leaves a form of Norsk ordbank's Nynorsk list alone, and refuses the other
mode's flag; links point at Nynorskordboka; check 6 reads "sjå" as a linking word there only.

Nothing here reads the mirror, the library or the network.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = os.path.join(os.path.dirname(HERE), "handover", "checks")
sys.path.insert(0, CHECKS)

import common  # noqa: E402
import dangling_sense_refs  # noqa: E402
import doubled_spaces_words  # noqa: E402
import duplicate_definition_ids  # noqa: E402
import empty_cited_articles  # noqa: E402
import sense_ref_cycles  # noqa: E402
import unmatched_quotes  # noqa: E402
import word_forms  # noqa: E402


# --- builders ----------------------------------------------------------------

def expl(content, items=()):
    return {"type_": "explanation", "content": content, "items": list(items)}


def example(content, items=()):
    return {"type_": "example", "quote": {"content": content, "items": list(items)},
            "explanation": {"content": "", "items": []}}


def ref(aid, did=None, lemma="x", word_form=None):
    r = {"type_": "article_ref", "article_id": aid, "definition_id": did,
         "lemmas": [{"lemma": lemma, "hgno": 0}]}
    if word_form:
        r["word_form"] = word_form
    return r


def defn(did, *elements):
    return {"type_": "definition", "id": did, "elements": list(elements)}


def article(aid, lemma, senses, etymology=None, status=8, forms=None):
    body = {"definitions": [defn(1, *senses)]}
    if etymology is not None:
        body["etymology"] = etymology
    lem = {"lemma": lemma, "hgno": 0, "paradigm_info": [
        {"inflection": [{"word_form": f} for f in (forms or [lemma])]}]}
    return {"article_id": aid, "status": status, "lemmas": [lem], "body": body}


def sub_article(aid, *senses):
    return {"type_": "sub_article", "article_id": aid, "lemmas": ["uttrykk"],
            "article": {"article_id": aid, "body": {"definitions": list(senses)}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.arts = os.path.join(self.dir, "arts")
        os.mkdir(self.arts)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, *arts, where=None):
        where = where or self.arts
        os.makedirs(where, exist_ok=True)
        for a in arts:
            with io.open(os.path.join(where, "%s.json" % a["article_id"]), "w",
                         encoding="utf-8") as f:
                json.dump(a, f, ensure_ascii=False)
        return where

    def run_check(self, module, extra=()):
        out = os.path.join(self.dir, "out.tsv")
        devnull = io.StringIO()
        old, sys.stderr = sys.stderr, devnull
        try:
            code = module.main([self.arts, "-o", out] + list(extra))
        finally:
            sys.stderr = old
        self.assertEqual(code, 0, devnull.getvalue())
        with io.open(out, encoding="utf-8") as f:
            lines = f.read().splitlines()
        head = lines[0].split("\t")
        return [dict(zip(head, ln.split("\t"))) for ln in lines[1:]]


# --- check 1 -------------------------------------------------------------------

class DanglingRefs(Base):
    def test_missing_definition_id(self):
        target = article(7850, "bryst", [defn(2, expl("kroppsdel")), defn(6, expl("kjøtt"))])
        citer = article(46911, "pupp", [defn(2, expl("$", [ref(7850, 5, "bryst")]))])
        ok = article(46912, "god", [defn(2, expl("$", [ref(7850, 6, "bryst")]))])
        self.write(target, citer, ok)
        rows = self.run_check(dangling_sense_refs)
        self.assertEqual([(r["article_id"], r["type"], r["definition_id"]) for r in rows],
                         [("46911", "missing_definition_id", "5")])

    def test_sub_article_ids_do_not_count_for_the_host(self):
        host = article(40430, "ne", [defn(4, expl("ned")),
                                     defn(9, sub_article(1, defn(2, expl("av og til"))))])
        citer = article(500, "fallende", [defn(2, expl("$", [ref(40430, 2, "ne")]))])
        self.write(host, citer)
        rows = self.run_check(dangling_sense_refs)
        self.assertEqual([r["type"] for r in rows], ["missing_definition_id"])

    def test_anchor_without_text_and_missing_target(self):
        host = article(14219, "felt", [defn(2, expl("jorde")),
                                       defn(7, sub_article(2, defn(2, expl("ute"))))])
        citer = article(14222, "feltarbeid", [defn(2, expl("$ og $", [
            ref(14219, 7, "felt"), ref(99999, 3, "borte")]))])
        draft = article(99999, "borte", [defn(3, expl("vekk"))], status=5)
        self.write(host, citer, draft)
        types = sorted(r["type"] for r in self.run_check(dangling_sense_refs))
        self.assertEqual(types, ["anchor_without_text", "target_not_published"])

    def test_jsonl_with_wrapper(self):
        path = os.path.join(self.dir, "arts.jsonl")
        target = article(1, "a", [defn(2, expl("x"))])
        citer = article(2, "b", [defn(2, expl("$", [ref(1, 3)]))])
        with io.open(path, "w", encoding="utf-8") as f:
            for a in (target, citer):
                f.write(json.dumps({"id": a["article_id"], "data": a}) + "\n")
        self.arts = path
        rows = self.run_check(dangling_sense_refs)
        self.assertEqual(len(rows), 1)


# --- check 2 -------------------------------------------------------------------

class DuplicateIds(Base):
    def test_duplicate(self):
        self.write(article(21740, "gå", [defn(5, expl("en")), defn(6, expl("to")),
                                         defn(5, expl("tre"))]))
        rows = self.run_check(duplicate_definition_ids)
        self.assertEqual([r["definition_id"] for r in rows], ["5", "5"])
        self.assertEqual(rows[1]["first_text"], "tre")

    def test_unique_and_sub_article_clash(self):
        # the embedded expression's own id 2 is not the host's id 2
        self.write(article(1, "a", [defn(2, expl("x")),
                                    defn(3, sub_article(9, defn(2, expl("y"))))]))
        self.assertEqual(self.run_check(duplicate_definition_ids), [])


# --- check 3 -------------------------------------------------------------------

class Doubled(Base):
    def test_positive(self):
        self.write(article(63550, "tårn", [defn(2, expl("del av av byggverk"),
                                                example("han  kom"))],
                           etymology=[{"type_": "etymology_language",
                                       "content": "kausativ $ $", "items": [
                                           {"type_": "usage", "text": "av"},
                                           {"type_": "usage", "text": "av"}]}]))
        rows = self.run_check(doubled_spaces_words)
        got = sorted((r["type"], r["word"], r["location"].split(",")[-1].strip())
                     for r in rows)
        self.assertEqual(got, [("double_space", "", "eksempel 1"),
                               ("doubled_word", "av", "forklaring 1"),
                               ("doubled_word", "av", "ledd 1")])

    def test_negative(self):
        self.write(article(942, "åkerrikse", [
            defn(2, expl("fugl"), expl("Crex crex"), expl("av $", [{"type_": "entity", "id": "av"}]),
                 example("han kom og gikk"))]))
        self.assertEqual(self.run_check(doubled_spaces_words), [])

    def test_headword_double_space(self):
        self.write(article(102534, "som å skvette  vann på gåsa", [defn(2, expl("nytteløst"))]))
        rows = self.run_check(doubled_spaces_words)
        self.assertEqual([r["location"] for r in rows], ["oppslagsord 1"])


# --- check 4 -------------------------------------------------------------------

class Quotes(Base):
    def test_scan(self):
        s = unmatched_quotes.scan
        self.assertEqual(s("av ‘far, munk’"), [])
        self.assertEqual(s("rock’n’roll"), [])
        self.assertEqual([t for t, m, p in s("og {grjót} ‘stein")], ["unclosed_opening"])
        self.assertEqual([t for t, m, p in s("sidestille (med) ’")], ["unopened_closing"])
        self.assertEqual([t for t, m, p in s("‘avskåret (linje)'")], ["straight_close"])
        self.assertEqual([t for t, m, p in s("«du Guds Lam")], ["unclosed_opening"])
        self.assertEqual(s("'i går' og 'til Paris'"), [])
        self.assertEqual(s("Johannes’ åpenbaring og Sant’ Elmo"), [])
        self.assertEqual([t for t, m, p in s("og helios 'sol’")], ["straight_open"])
        self.assertEqual([t for t, m, p in s("kinesisk ’rund ting, dollar’")],
                         ["unopened_closing"])
        self.assertEqual([t for t, m, p in s("‘Sankt Johannes’ dag’")], [])

    def test_article(self):
        self.write(article(21259, "grut", [defn(2, expl("grums"))], etymology=[
            {"type_": "etymology_reference", "content": "beslektet med $ ‘stein",
             "items": [{"type_": "usage", "text": "grjót"}]},
            {"type_": "etymology_reference", "content": "av $ ‘sidestille (med)'",
             "items": [{"type_": "usage", "text": "comparare"}]}]),
            article(2, "ok", [defn(2, expl("tegn («…» eller “…”) brukt ved sitat"))]))
        rows = self.run_check(unmatched_quotes)
        self.assertEqual([(r["article_id"], r["type"]) for r in rows],
                         [("21259", "unclosed_opening"), ("21259", "straight_close")])


# --- check 5 -------------------------------------------------------------------

class EmptyCited(Base):
    def test_positive_and_negative(self):
        empty_cited = article(686, "alarmklokke", [])
        empty_alone = article(687, "alarmlampe", [])
        host_only = article(1120, "årsbasis", [defn(2, sub_article(5, defn(2, expl("årlig"))))])
        citer = article(30187, "klokke", [defn(2, expl("$, $ og $", [
            ref(686), ref(1120), ref(30188)]))])
        self_cite = article(30188, "tomt", [defn(2, expl("$", [ref(30188)]))])
        self.write(empty_cited, empty_alone, host_only, citer, self_cite)
        rows = self.run_check(empty_cited_articles)
        # 687 is empty but uncited; 1120 holds a fixed expression; 30188 has text
        self.assertEqual([(r["article_id"], r["citing_articles"]) for r in rows],
                         [("686", "1")])
        self.assertTrue(empty_cited_articles.is_empty(empty_cited))
        self.assertFalse(empty_cited_articles.is_empty(host_only))

    def test_counted(self):
        self.write(article(686, "alarmklokke", []),
                   article(1, "klokke", [defn(2, expl("$", [ref(686)]))]),
                   article(2, "ur", [defn(2, expl("jf. $", [ref(686, 2)]))]),
                   article(3, "uten", []))
        rows = self.run_check(empty_cited_articles)
        self.assertEqual([(r["article_id"], r["citing_articles"]) for r in rows],
                         [("686", "2")])


# --- check 6 -------------------------------------------------------------------

class Cycles(Base):
    def found(self):
        return [(r["article_id"], r["type"], r["other_articles"],
                 [st.split(" https:")[0] for st in r["loop"].split(" -> ")])
                for r in self.run_check(sense_ref_cycles)]

    # mutual

    def test_mutual(self):
        self.write(article(868, "allerede", [defn(2, expl("$", [ref(1372, None, "alt")]))]),
                   article(1372, "alt", [defn(2, expl("hele mengden")),
                                         defn(5, expl("$", [ref(868, None, "allerede")]))]))
        self.assertEqual(self.found(), [("868", "mutual", "1", [
            "allerede [868] betydning 1 (definisjon id 2)",
            "alt [1372] betydning 2 (definisjon id 5)",
            "allerede [868] betydning 1 (definisjon id 2)"])])

    def test_no_mutual(self):
        # A also points elsewhere; C points back but has real text
        self.write(article(1, "a", [defn(2, expl("$, $", [ref(2), ref(3)]))]),
                   article(2, "b", [defn(2, expl("$", [ref(1)]))]),
                   article(4, "c", [defn(2, expl("$", [ref(5)]))]),
                   article(5, "d", [defn(2, expl("det samme som $", [ref(4)]))]))
        self.assertEqual(self.found(), [])

    # returns-other-sense

    def blunke(self, blinke_text=None):
        blinke = article(6446, "blinke", [defn(2, expl("lyse i blink")),
                                          defn(4, expl(blinke_text or "$",
                                                       [] if blinke_text else
                                                       [ref(6606, 2, "blunke")]))])
        blinke["lemmas"][0]["hgno"] = 2
        self.write(article(6606, "blunke", [defn(2, expl("lukke og åpne øynene raskt")),
                                            defn(4, expl("$", [ref(6446, 4, "blinke")]),
                                                 example("blunke med lyset"))]),
                   blinke)

    def test_returns_other_sense(self):
        self.blunke()
        self.assertEqual(self.found(), [("6606", "returns-other-sense", "1", [
            "blunke [6606] betydning 2 (definisjon id 4)",
            "blinke II [6446] betydning 2 (definisjon id 4)",
            "blunke [6606] betydning 1 (definisjon id 2)"])])

    def test_examples_split(self):
        # blunke 2 carries an example of its own; allerede and alt 3 carry none
        self.blunke()
        self.write(article(868, "allerede", [defn(2, expl("$", [ref(1372)]))]),
                   article(1372, "alt", [defn(5, expl("$", [ref(868)]))]))
        rows = self.run_check(sense_ref_cycles)
        self.assertEqual([(r["article_id"], r["type"], r["examples"]) for r in rows],
                         [("868", "mutual", "bare"),
                          ("6606", "returns-other-sense", "own-examples")])
        self.assertEqual(rows[0]["senses_with_examples"], "")
        self.assertEqual(rows[1]["senses_with_examples"],
                         "blunke [6606] betydning 2 (definisjon id 4): 1 eksempel")

    def test_examples_sort_bare_first(self):
        self.write(article(1, "a", [defn(2, expl("$", [ref(2, 2)]), example("a nå")),
                                    defn(3, expl("tekst"))]),
                   article(2, "b", [defn(2, expl("$", [ref(1, 3)]))]),
                   article(3, "c", [defn(2, expl("$", [ref(4, 2)])), defn(3, expl("tekst"))]),
                   article(4, "d", [defn(2, expl("$", [ref(3, 3)]))]))
        rows = self.run_check(sense_ref_cycles)
        self.assertEqual([(r["article_id"], r["examples"]) for r in rows],
                         [("3", "bare"), ("1", "own-examples")])

    def test_chain_ends_in_text(self):
        # blinke II sense 2 has a definition of its own: the reader is not sent back
        self.blunke(blinke_text="lyse kort")
        self.assertEqual(self.found(), [])

    def test_whole_article_step_into_text(self):
        # vinterdrakt 1 = "vinterham" (the whole article); vinterham 1 has its own text,
        # so the reader finds a definition there even though vinterham 2 points back
        self.write(article(68589, "vinterdrakt", [defn(2, expl("$", [ref(68604)])),
                                                  defn(3, expl("dekke av snø"))]),
                   article(68604, "vinterham", [defn(2, expl("ham om vinteren")),
                                                defn(3, expl("$", [ref(68589, 3)]))]))
        self.assertEqual(self.found(), [])

    def test_whole_article_step_into_references(self):
        # the same with no text in the middle article: a finding
        self.write(article(68589, "vinterdrakt", [defn(2, expl("$", [ref(68604)])),
                                                  defn(3, expl("dekke av snø"))]),
                   article(68604, "vinterham", [defn(3, expl("$", [ref(68589, 3)]))]))
        self.assertEqual([(a, t) for a, t, n, s in self.found()],
                         [("68589", "returns-other-sense")])

    # longer-loop

    def test_longer_cycle_reported_once(self):
        # 10#2 -> 20#2 -> 30 (whole, one reference-only sense) -> 10#2
        self.write(article(10, "a", [defn(2, expl("$", [ref(20, 2)]))]),
                   article(20, "b", [defn(2, expl("$ $", [{"type_": "relation", "id": "jf"},
                                                          ref(30)]))]),
                   article(30, "c", [defn(2, expl("se $", [ref(10, 2)]))]))
        self.assertEqual(self.found(), [("10", "longer-loop", "2", [
            "a [10] betydning 1 (definisjon id 2)", "b [20] betydning 1 (definisjon id 2)",
            "c [30] betydning 1 (definisjon id 2)", "a [10] betydning 1 (definisjon id 2)"])])

    def test_longer_loop_to_whole_article(self):
        self.write(article(10, "a", [defn(2, expl("tekst")), defn(3, expl("$", [ref(20, 2)]))]),
                   article(20, "b", [defn(2, expl("$", [ref(30, 2)]))]),
                   article(30, "c", [defn(2, expl("$", [ref(10)]))]))
        rows = self.found()
        self.assertEqual([(a, t, n) for a, t, n, s in rows], [("10", "longer-loop", "2")])
        self.assertEqual(rows[0][3][-1], "a [10] hele artikkelen")

    def test_no_longer_loop(self):
        # c has text of its own; d also refers elsewhere
        self.write(article(10, "a", [defn(2, expl("$", [ref(20, 2)]))]),
                   article(20, "b", [defn(2, expl("$", [ref(30, 2)]))]),
                   article(30, "c", [defn(2, expl("tekst og $", [ref(10, 2)]))]),
                   article(40, "d", [defn(2, expl("$", [ref(50, 2)]))]),
                   article(50, "e", [defn(2, expl("$", [ref(60, 2)]))]),
                   article(60, "f", [defn(2, expl("$ eller $", [ref(40, 2), ref(70)]))]),
                   article(70, "g", [defn(2, expl("tekst"))]))
        self.assertEqual(self.found(), [])

    def test_max_articles(self):
        self.write(article(10, "a", [defn(2, expl("$", [ref(20, 2)]))]),
                   article(20, "b", [defn(2, expl("$", [ref(30, 2)]))]),
                   article(30, "c", [defn(2, expl("$", [ref(10, 2)]))]))
        self.assertEqual(self.run_check(sense_ref_cycles, ["--max-articles", "1"]), [])


# --- check 7 -------------------------------------------------------------------

class WordForms(Base):
    def test_candidates(self):
        nn = self.write(article(41671, "nøytron", [defn(2, expl("partikkel"))],
                                forms=["nøytron", "nøytronar"]),
                        where=os.path.join(self.dir, "nn"))
        self.write(
            article(41671, "nøytron", [defn(2, expl("partikkel"))],
                    forms=["nøytron", "nøytroner"]),
            article(3084, "atomkjerne", [
                defn(2, expl("kjerne av protoner og $", [ref(41671, None, "nøytron",
                                                             "nøytronar")]),
                     example("en lasestråle traff kjernen"))],
                etymology=[{"type_": "etymology_language", "content": "norr. hleypa",
                            "items": []}]),
            article(1, "kjerne", [defn(2, expl("midte"))], forms=["kjerne", "kjernen"]),
            article(2, "protoner", [defn(2, expl("partikkel"))]),
            article(3, "traff", [defn(2, expl("treffe"))]),
            article(4, "partikkel", [defn(2, expl("liten del, f.eks. Uria aalge"))]),
            article(5, "midte", [defn(2, expl("partikkel"))]),
            article(6, "treffe", [defn(2, expl("partikkel"))]),
            article(7, "liten", [defn(2, expl("partikkel"))]),
            article(8, "del", [defn(2, expl("partikkel"))]),
            article(9, "en", [defn(2, expl("partikkel"))]),
            article(10, "og", [defn(2, expl("partikkel"))]),
            article(11, "av", [defn(2, expl("partikkel"))]))
        rows = self.run_check(word_forms, ["--nynorsk", nn])
        got = sorted((r["article_id"], r["type"], r["word"]) for r in rows)
        self.assertEqual(got, [("3084", "nynorsk_form", "nøytronar"),
                               ("3084", "unknown_form", "lasestråle")])


class WordFormsNynorsk(Base):
    """Nynorsk mode (--dictionary nn, 2026-11-13): the input is Nynorskordboka, the other
    dictionary Bokmål; a Bokmål form is labelled bokmal_form, and a Nynorsk form that only
    Norsk ordbank's Nynorsk list knows is not flagged."""

    def fixture(self):
        bm = self.write(article(5001, "begrense", [defn(2, expl("sette grense for"))],
                                forms=["begrense", "begrensa", "begrenset"]),
                        where=os.path.join(self.dir, "bm"))
        nnlist = os.path.join(self.dir, "nno.txt")
        with io.open(nnlist, "w", encoding="utf-8") as f:
            f.write("muren\nmur\n")
        self.write(
            article(1, "avgrense", [defn(2, expl("setje grense for"),
                                         example("dei har begrensa tilgangen til muren"),
                                         example("eit uuttalt krav"))],
                    forms=["avgrense", "avgrensa"]),
            article(2, "setje", [defn(2, expl("plassere"))], forms=["setje", "sette"]),
            article(3, "grense", [defn(2, expl("skilje"))]),
            article(4, "for", [defn(2, expl("skilje"))]),
            article(5, "dei", [defn(2, expl("skilje"))]),
            article(6, "har", [defn(2, expl("skilje"))]),
            article(7, "tilgang", [defn(2, expl("skilje"))], forms=["tilgang", "tilgangen"]),
            article(8, "til", [defn(2, expl("skilje"))]),
            article(9, "eit", [defn(2, expl("skilje"))]),
            article(10, "krav", [defn(2, expl("skilje"))]),
            article(11, "plassere", [defn(2, expl("skilje"))]),
            article(12, "skilje", [defn(2, expl("plassere"))]))
        return bm, nnlist

    def test_bokmal_form_found_and_ordbank_form_not_flagged(self):
        bm, nnlist = self.fixture()
        rows = self.run_check(word_forms, ["--dictionary", "nn", "--bokmal", bm,
                                           "--nynorsk-forms", nnlist])
        got = sorted((r["article_id"], r["type"], r["word"]) for r in rows)
        self.assertEqual(got, [("1", "bokmal_form", "begrensa"),
                               ("1", "unknown_form", "uuttalt")])

    def test_without_the_list_the_ordbank_form_is_unknown(self):
        bm, _ = self.fixture()
        rows = self.run_check(word_forms, ["--dictionary", "nn", "--bokmal", bm])
        self.assertIn(("unknown_form", "muren"), [(r["type"], r["word"]) for r in rows])

    def test_other_dictionary_flag_must_match_the_mode(self):
        bm, _ = self.fixture()
        err = io.StringIO()
        old, sys.stderr = sys.stderr, err
        try:
            with self.assertRaises(SystemExit):
                word_forms.main([self.arts, "--dictionary", "nn", "--nynorsk", bm])
            with self.assertRaises(SystemExit):
                word_forms.main([self.arts, "--bokmal", bm])
        finally:
            sys.stderr = old


class NynorskLinks(Base):
    def test_link_by_dictionary(self):
        self.assertEqual(common.link(7435), "https://ordbokene.no/nob/bm/7435")
        self.assertEqual(common.link(7435, "nn"), "https://ordbokene.no/nno/nn/7435")

    def mutual_sja(self):
        self.write(article(1, "allereie", [defn(2, expl("sjå $", [ref(2, None, "alt")]))]),
                   article(2, "alt", [defn(2, expl("sjå $", [ref(1, None, "allereie")]))]))

    def test_sense_ref_cycles_in_nynorsk_mode(self):
        self.mutual_sja()
        rows = self.run_check(sense_ref_cycles, ["--dictionary", "nn"])
        self.assertEqual([r["type"] for r in rows], ["mutual"])
        self.assertIn("https://ordbokene.no/nno/nn/1", rows[0]["loop"])
        self.assertNotIn("/nob/bm/", rows[0]["loop"])

    def test_sja_is_not_a_bokmal_linking_word(self):
        self.mutual_sja()
        self.assertEqual(self.run_check(sense_ref_cycles), [])


def usage(text):
    return {"type_": "usage", "text": text}


class WordFormsLatin(Base):
    """The Latin-name skip, one shape per test. Every word that is not Latin is a
    Bokmål form of the dictionary written here, so a row means an epithet leaked."""

    WORDS = ["plante", "fugl", "sylvia", "beta", "piper", "det", "den", "far", "huset",
             "kaspiske", "hav", "av", "frukter", "treet", "gikk", "var", "og", "som", "etter"]

    def flagged(self, *elements):
        arts = [article(1000 + i, w, [defn(2, expl("x"))]) for i, w in enumerate(self.WORDS)]
        arts.append(article(1, "testord", [defn(2, *elements)]))
        self.write(*arts)
        return sorted(r["word"] for r in self.run_check(word_forms))

    def test_rank_abbreviation_in_markup(self):
        self.assertEqual(self.flagged(expl("$ subsp. $", [usage("Ranunculus acris"),
                                                         usage("acris")]),
                                      expl("$ var. $", [usage("Brassica oleracea"),
                                                        usage("botrytis")]),
                                      expl("$ subsp. $", [usage("Brassica"),
                                                          usage("pekinensis")])), [])

    def test_rank_abbreviation_in_text(self):
        self.assertEqual(self.flagged(expl("plante Ranunculus acris subsp. acris")), [])

    def test_trinomial(self):
        self.assertEqual(self.flagged(expl("$", [usage("Fagus sylvatica atropunicea")]),
                                      expl("plante Fagus sylvatica atropunicea")), [])

    def test_hybrid_sign(self):
        self.assertEqual(self.flagged(expl("$", [usage("Fragaria x ananassa")]),
                                      expl("plante Fragaria x ananassa"),
                                      expl("plante Fragaria × ananassa")), [])

    def test_genus_that_is_a_bokmal_form(self):
        self.assertEqual(self.flagged(expl("$", [usage("Sylvia atricapilla")]),
                                      expl("$", [usage("Beta vulgaris altissima")]),
                                      expl("frukter av $", [usage("Piper nigrum")])), [])

    def test_norwegian_after_a_capital_is_still_read(self):
        # a sentence-initial capital that is a Bokmål form starts no Latin name, in
        # running text or in a usage item that is not a Latin name
        self.assertEqual(self.flagged(example("Sylvia gikk hjme"),
                                      expl("(etter $)", [usage("Den sjunede far i huset")]),
                                      expl("$ og $", [usage("Det kaspiske hva"),
                                                      usage("Piper nigrum")]),
                                      expl("$", [usage("aurora borealis")])),
                         ["aurora", "borealis", "hjme", "hva", "sjunede"])

    def test_one_epithet_only_after_an_unmarked_genus_in_text(self):
        # "Uria aalge" in running text: the epithet is skipped; a third word is skipped
        # only when the second was no Bokmål form, so a slip after "Uria var" is read
        self.assertEqual(self.flagged(expl("plante Uria aalge"),
                                      expl("plante Uria var hjme")), ["hjme"])


class WordFormsMark(Base):
    def test_compound_mark(self):
        words = ["laser", "stråle", "laserstråle", "kjøtt", "gryte", "salt", "vann", "område",
                 "med", "lase"]
        arts = [article(1000 + i, w, [defn(2, expl("x"))]) for i, w in enumerate(words)]
        arts.append(article(1, "testord", [defn(2, expl(
            "med kjøttgryte og saltvannsområde og lasestråle og qwxyzk"))]))
        self.write(*arts)
        rows = self.run_check(word_forms)
        got = sorted((r["word"], r["mark"]) for r in rows)
        # every row is kept; a slip that splits ("lase" + "stråle") is one edit from a
        # known form and stays unmarked
        self.assertEqual(got, [("kjøttgryte", "compound"), ("lasestråle", ""),
                               ("qwxyzk", ""), ("saltvannsområde", "compound")])

    def test_compound_split(self):
        forms = {"salt", "vann", "område", "suge", "skiver", "sug", "esk", "iver"}
        self.assertEqual(word_forms.compound_split("saltvannsområde", forms),
                         ["salt", "vann+s", "område"])
        self.assertEqual(word_forms.compound_split("sugeskiver", forms), ["suge", "skiver"])
        self.assertIsNone(word_forms.compound_split("saltvan", forms))


# --- embedded copies of fixed expressions ------------------------------------------

class EmbeddedCopies(Base):
    """A copy is read only for what its expression's own article lacks (common.py)."""

    def expr(self, *elements):
        # the expression's own article, with the closing "Se: $" back-reference
        return article(133353, "ringe inn", [defn(2, *elements),
                                             expl("Se: $", [ref(48613, None, "ringe")])])

    def parent(self, *elements, aid=48613):
        return article(aid, "ringe", [defn(2, expl("lage en ring")),
                                      defn(5, sub_article(133353, defn(2, *elements)))])

    def visited(self, *arts):
        self.write(*arts)
        emb = common.Embedded(self.arts)
        out = []
        for a in arts:
            out += [(common.article_id(a), loc, common.render(c, i))
                    for loc, k, c, i in common.iter_embedded_text(a, emb)]
        return out

    def test_identical_copy_yields_nothing(self):
        self.assertEqual(self.visited(self.expr(expl("del av av byggverk")),
                                      self.parent(expl("del av av byggverk"))), [])

    def test_extra_example_yields_that_example_only(self):
        got = self.visited(self.expr(expl("tegne ring rundt")),
                           self.parent(expl("tegne ring rundt"),
                                       example("ringen inn feilen med raudt")))
        self.assertEqual(got, [(48613, 'artikkel 48613, uttrykk "uttrykk" (133353), '
                                       'betydning 1 (definisjon id 2), eksempel 1',
                                'ringen inn feilen med raudt')])

    def test_copy_without_its_article_yields_everything(self):
        got = self.visited(self.parent(expl("tegne ring rundt"), example("ring inn")))
        self.assertEqual([t for _, _, t in got], ["tegne ring rundt", "ring inn"])

    def test_place_string(self):
        sub = sub_article(133353, defn(2, expl("x")))
        sub["article"]["lemmas"] = [{"lemma": "ringe inn"}]
        self.assertEqual(common.copy_place({"article_id": 48613}, sub),
                         'artikkel 48613, uttrykk "ringe inn" (133353)')

    def test_concept_type_is_not_a_difference(self):
        a = common.element_key("truer $ ødelegger", [{"type_": "entity", "id": "el"}])
        b = common.element_key("truer $ ødelegger", [{"type_": "relation", "id": "el"}])
        self.assertEqual(a, b)
        self.assertNotEqual(common.element_key("$", [ref(1, 2)]),
                            common.element_key("$", [ref(1, 3)]))

    def test_check_reports_against_the_parent_and_switches_off(self):
        self.write(self.expr(expl("tegne ring rundt")),
                   self.parent(expl("tegne  ring rundt")))
        rows = self.run_check(doubled_spaces_words)
        self.assertEqual([(r["article_id"], r["lemma"], r["location"]) for r in rows],
                         [("48613", "ringe", 'artikkel 48613, uttrykk "uttrykk" (133353), '
                                             'betydning 1 (definisjon id 2), forklaring 1')])
        self.assertEqual(self.run_check(doubled_spaces_words, ["--no-embedded"]), [])

    def test_dangling_reference_in_a_copy(self):
        self.write(article(7850, "bryst", [defn(2, expl("kroppsdel"))]),
                   self.expr(expl("$", [ref(7850, 2, "bryst")])),
                   self.parent(expl("$", [ref(7850, 5, "bryst")])))
        rows = self.run_check(dangling_sense_refs)
        self.assertEqual([(r["article_id"], r["definition_id"]) for r in rows],
                         [("48613", "5")])

    def test_word_forms_leaves_the_articles_words_to_it(self):
        # the copy's element differs, but "partiklar" is in the article: reported once
        self.write(self.expr(expl("små partiklar")),
                   self.parent(expl("små partiklar i nyre")),
                   article(1, "små", [defn(2, expl("små"))]),
                   article(2, "nyre", [defn(2, expl("nyre"))]),
                   article(3, "lage", [defn(2, expl("nyre"))]),
                   article(4, "ring", [defn(2, expl("nyre"))]))
        rows = self.run_check(word_forms)
        self.assertEqual(sorted((r["article_id"], r["word"]) for r in rows),
                         [("133353", "partiklar")])


class Reading(Base):
    def test_unpublished_skipped(self):
        self.write(article(1, "a", [defn(2, expl("del av av byggverk"))], status=3),
                   article(2, "b", [defn(2, expl("x"))], status=None))
        self.assertEqual(self.run_check(doubled_spaces_words), [])
        rows = self.run_check(doubled_spaces_words, ["--include-unpublished"])
        self.assertEqual(len(rows), 1)

    def test_sense_labels(self):
        a = article(1, "a", [defn(2, expl("x"), defn(3, expl("y")), defn(4, expl("z"))),
                             defn(5, expl("w"))])
        labels = common.sense_labels(a)
        got = sorted(labels[id(n)] for n in common.own_definition_nodes(a) if id(n) in labels)
        self.assertEqual(got, ["1", "1.1", "1.2", "2"])


class LoneTopSense(Base):
    """One top-level sense with sub-senses: ordbokene numbers the sub-senses 1, 2, 3 and
    gives the top sense no number (its references carry definition_order 0 there)."""

    def places(self, a):
        labels = common.sense_labels(a)
        return [common.node_place(n, labels) for n in common.own_definition_nodes(a)]

    def lone(self, *top_elements):
        return article(1, "a", [defn(2, *(top_elements + (
            defn(3, expl("x"), defn(6, expl("x2"))), defn(4, expl("y")), defn(5, expl("z")))))])

    def test_see_wrapper(self):
        self.assertEqual(self.places(self.lone(expl("Se: $", [ref(9)]))),
                         ["definisjon id 1", "overordnet betydning (definisjon id 2)",
                          "betydning 1 (definisjon id 3)", "betydning 1.1 (definisjon id 6)",
                          "betydning 2 (definisjon id 4)", "betydning 3 (definisjon id 5)"])

    def test_empty_wrapper(self):
        self.assertEqual(self.places(self.lone(expl(""))),
                         ["definisjon id 1", "overordnet betydning (definisjon id 2)",
                          "betydning 1 (definisjon id 3)", "betydning 1.1 (definisjon id 6)",
                          "betydning 2 (definisjon id 4)", "betydning 3 (definisjon id 5)"])

    def test_top_sense_with_text(self):
        a = self.lone(expl("som kommer fra hjertet"), example("takk"))
        self.assertEqual(self.places(a)[1:3], ["overordnet betydning (definisjon id 2)",
                                               "betydning 1 (definisjon id 3)"])
        locs = [loc for loc, _, _, _ in common.iter_text(a)]
        self.assertEqual(locs[:3], ["overordnet betydning (definisjon id 2), forklaring 1",
                                    "overordnet betydning (definisjon id 2), eksempel 1",
                                    "betydning 1 (definisjon id 3), forklaring 1"])

    def test_lone_sense_without_sub_senses(self):
        a = article(1, "a", [defn(2, expl("x"))])
        self.assertEqual(self.places(a), ["definisjon id 1", "betydning 1 (definisjon id 2)"])

    def test_several_top_senses_unchanged(self):
        a = article(1, "a", [defn(2, expl("x"), defn(3, expl("y")), defn(4, expl("z"))),
                             defn(5, expl("w"))])
        self.assertEqual(self.places(a), ["definisjon id 1", "betydning 1 (definisjon id 2)",
                                          "betydning 1.1 (definisjon id 3)",
                                          "betydning 1.2 (definisjon id 4)",
                                          "betydning 2 (definisjon id 5)"])

    def test_embedded_copy(self):
        expr_senses = (defn(2, expl("Se: $", [ref(48613)]), defn(3, expl("lage en ring")),
                       defn(4, expl("ringe til"))),)
        parent = article(48613, "ringe", [defn(2, expl("lage en ring")),
                                          defn(5, sub_article(133353, *expr_senses))])
        self.write(parent)
        emb = common.Embedded(self.arts)
        locs = [loc for loc, _, _, _ in common.iter_embedded_text(parent, emb)]
        head = 'artikkel 48613, uttrykk "uttrykk" (133353), '
        self.assertEqual(locs, [head + "overordnet betydning (definisjon id 2), forklaring 1",
                                head + "betydning 1 (definisjon id 3), forklaring 1",
                                head + "betydning 2 (definisjon id 4), forklaring 1"])


# --- the intro line of a compound list -------------------------------------------

def compound_list(intro, *refs, items=()):
    return {"type_": "compound_list", "intro": {"content": intro, "items": list(items)},
            "elements": list(refs)}


class CompoundIntro(Base):
    """iter_text yields a compound list's intro (klinikk 30122: "som etterldd i ord som"),
    so every text check reads it."""

    def klinikk(self, intro="som etterldd i ord som", items=()):
        return article(30122, "klinikk", [defn(2, expl("sykehus"),
                                               compound_list(intro, ref(18636, None, "fødselsklinikk"),
                                                             items=items))])

    def test_yielded_with_place_and_kind(self):
        got = [(loc, kind, common.render(c, i)) for loc, kind, c, i in
               common.iter_text(self.klinikk())]
        self.assertEqual(got[-1], ("betydning 1 (definisjon id 2), sammensetninger, innledning",
                                   "sammensetningsinnledning", "som etterldd i ord som"))

    def test_items_render_and_definitions_flag(self):
        a = self.klinikk("som etterledd i $", items=[{"type_": "entity", "id": "f_eks"}])
        intro = [x for x in common.iter_text(a) if x[1] == "sammensetningsinnledning"]
        self.assertEqual(common.render(intro[0][2], intro[0][3]), "som etterledd i f_eks")
        self.assertEqual(common.render(intro[0][2], intro[0][3], words=True),
                         "som etterledd i " + common.SEP)
        self.assertFalse([x for x in common.iter_text(a, definitions=False)
                          if x[1] == "sammensetningsinnledning"])

    def test_empty_intro_not_yielded(self):
        self.assertFalse([x for x in common.iter_text(self.klinikk(""))
                          if x[1] == "sammensetningsinnledning"])

    def test_several_lists_in_one_sense_are_numbered(self):
        a = article(6739, "x", [defn(2, expl("y"), compound_list("i ord som"),
                                     compound_list("som etterledd i"))])
        locs = [loc for loc, kind, c, i in common.iter_text(a)
                if kind == "sammensetningsinnledning"]
        self.assertEqual([l.split(", ", 1)[1] for l in locs],
                         ["sammensetninger 1, innledning", "sammensetninger 2, innledning"])

    def test_list_references_still_yielded_once(self):
        refs = [loc for loc, it, ctx in common.iter_refs(self.klinikk())]
        self.assertEqual(refs, ["betydning 1 (definisjon id 2), sammensetninger"])

    def test_word_forms_reads_the_intro(self):
        self.write(self.klinikk(),
                   *[article(i, w, [defn(2, expl("sykehus"))]) for i, w in
                     enumerate(["som", "i", "ord", "etterledd", "sykehus"], 1)])
        rows = self.run_check(word_forms)
        self.assertEqual([(r["word"], r["location"].split(", ", 1)[1]) for r in rows],
                         [("etterldd", "sammensetninger, innledning")])

    def test_doubled_space_in_the_intro(self):
        self.write(self.klinikk("etterledd  ord som"))
        rows = self.run_check(doubled_spaces_words)
        self.assertEqual([(r["type"], r["location"].split(", ", 1)[1]) for r in rows],
                         [("double_space", "sammensetninger, innledning")])


if __name__ == "__main__":
    unittest.main()
