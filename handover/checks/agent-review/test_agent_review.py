#!/usr/bin/env python3
"""Tests for agent_review.py (standard-library unittest): python test_agent_review.py

They pin the packets (one per article and word, every place kept), the batches (cut,
numbered, each packet once, the mark hidden from readers), the refusals of a malformed
verdict file, the second pass's selection, the merge, and a whole run with a stand-in
agent: a function that returns fixed verdicts. The tests of --articles need common.py and
word_forms.py in the folder above; they are skipped when those are missing.
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import agent_review as ar  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "word", "occurrences", "context", "mark"]
ROWS = [
    ["101", "tårn", "betydning 1 (definisjon id 2), forklaring 1", "unknown_form", "byggverkk",
     "1", "høy del av byggverkk", ""],
    ["101", "tårn", "betydning 1 (definisjon id 2), eksempel 2", "unknown_form", "byggverkk",
     "1", "et høyt byggverkk", ""],
    ["102", "atomkjerne", "betydning 1 (definisjon id 2), forklaring 1", "nynorsk_form",
     "nøytronar", "1", "protoner og nøytronar", ""],
    ["103", "salt", "betydning 2 (definisjon id 4), eksempel 1", "unknown_form",
     "saltvannsområdet", "2", "i saltvannsområdet", "compound"],
    ["104", "hav", "betydning 1 (definisjon id 2), eksempel 1", "unknown_form",
     "saltvannsområdet", "2", "hele saltvannsområdet", "compound"],
]


def write_tsv(path, rows=ROWS, header=HEADER):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in [header] + rows:
            f.write("\t".join(r) + "\n")


def many_rows(n, marked=0):
    out = []
    for i in range(n):
        out.append(["%d" % (1000 + i), "ord%d" % i, "betydning 1 (definisjon id 2), forklaring 1",
                    "unknown_form", "feilord%d" % i, "1", "tekst med feilord%d" % i,
                    "compound" if i < marked else ""])
    return out


def verdict(key, v="valid", **kw):
    r = {"key": key, "verdict": v, "kind": None, "confidence": "high", "correction": None,
         "reason": "a correct compound"}
    if v == "slip":
        r.update(kind="misspelling", correction="rett", reason="a typo")
    r.update(kw)
    return r


def write_verdicts(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write((r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)) + "\n")


def stand_in(fixed, default="valid"):
    """A stand-in reader: fixed verdicts by word, the default for everything else."""
    def judge(packet):
        v = fixed.get(packet["word"], default)
        return verdict(packet["key"], v)
    return judge


def run_reader(st, tag, judge, n=None, limit=99):
    """The reader's loop, as the agent runs it: take, judge, write, submit."""
    done = 0
    while done < limit:
        got = ar.take(st, tag, n)
        if got is None:
            break
        write_verdicts(got["out"], [judge(p) for p in got["packets"]])
        ar.submit(st, got["batch"], got["out"])
        done += 1
    return done


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tsv = os.path.join(self.tmp, "word_forms.tsv")
        self.st = ar.State(os.path.join(self.tmp, "state"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, rows=ROWS):
        write_tsv(self.tsv, rows)
        pks, lex = ar.build_packets(self.tsv)
        ar.save_packets(self.st, pks, lex)
        return pks


class Packets(Base):
    def test_one_packet_per_article_and_word(self):
        pks = self.make()
        self.assertEqual([p["key"] for p in pks],
                         ["101-byggverkk", "102-nøytronar", "103-saltvannsområdet",
                          "104-saltvannsområdet"])
        p = pks[0]
        self.assertEqual(p["article_id"], 101)
        self.assertEqual(p["headwords"], ["tårn"])
        self.assertEqual(len(p["places"]), 2)
        self.assertEqual(p["texts"], ["høy del av byggverkk", "et høyt byggverkk"])
        self.assertEqual(pks[2]["mark"], "compound")

    def test_refuses_other_tsv(self):
        write_tsv(self.tsv, [["1", "x"]], header=["article_id", "lemma"])
        with self.assertRaises(ar.Refused):
            ar.build_packets(self.tsv)

    def test_no_rebuild_under_a_queued_pass(self):
        pks = self.make()
        ar.queue(self.st, 1)
        with self.assertRaises(ar.Refused):
            ar.save_packets(self.st, pks, None)


class Batches(Base):
    def test_cut_and_numbered(self):
        self.make(many_rows(60))
        new, _ = ar.queue(self.st, 1, batch=25)
        self.assertEqual([b["id"] for b in new], ["p1-001", "p1-002", "p1-003"])
        self.assertEqual([len(b["keys"]) for b in new], [25, 25, 10])
        keys = [k for b in new for k in b["keys"]]
        self.assertEqual(sorted(keys), sorted(self.st.packets()))
        with self.assertRaises(ar.Refused):
            ar.queue(self.st, 1)

    def test_seeded_and_sampled(self):
        self.make(many_rows(40, marked=30))
        new, line = ar.queue(self.st, 1, batch=10, seed=7, sample=5)
        keys = [k for b in new for k in b["keys"]]
        self.assertEqual(len(keys), 15)
        self.assertIn("10 unmarked + 5 of 30 marked", line)
        other = ar.State(os.path.join(self.tmp, "other"))
        ar.save_packets(other, list(self.st.packets().values()), None)
        new2, _ = ar.queue(other, 1, batch=10, seed=7, sample=5)
        self.assertEqual(new, new2)

    def test_take_claims_in_turn_and_hides_the_mark(self):
        self.make(many_rows(30, marked=30))
        ar.queue(self.st, 1, batch=25)
        a = ar.take(self.st, "r01")
        b = ar.take(self.st, "r02")
        self.assertEqual((a["batch"], b["batch"]), ("p1-001", "p1-002"))
        self.assertIsNone(ar.take(self.st, "r03"))
        self.assertTrue(all("mark" not in p for p in a["packets"]))
        with open(self.st.claim("p1-001")) as f:
            self.assertEqual(f.read(), "r01")

    def test_release(self):
        self.make()
        ar.queue(self.st, 1)
        got = ar.take(self.st, "r01")
        self.assertEqual(ar.release(self.st, got["batch"]), "released p1-001")
        self.assertEqual(ar.take(self.st, "r02")["batch"], "p1-001")


class Verdicts(Base):
    def setUp(self):
        Base.setUp(self)
        self.make()
        ar.queue(self.st, 1, seed=3)
        self.got = ar.take(self.st, "r01")
        self.keys = [p["key"] for p in self.got["packets"]]
        self.path = self.got["out"]

    def problems(self, rows):
        write_verdicts(self.path, rows)
        _rows, probs, _adv = ar.validate(self.st, "p1-001", self.path)
        return probs

    def test_clean_file_recorded(self):
        write_verdicts(self.path, [verdict(k) for k in self.keys])
        line = ar.submit(self.st, "p1-001", self.path)
        self.assertTrue(line.startswith("ACCEPTED p1-001: 4 verdicts"))
        self.assertFalse(os.path.exists(self.st.claim("p1-001")))
        done = ar.read_jsonl(self.st.done("p1-001"))
        self.assertEqual([r["key"] for r in done], self.keys)
        self.assertEqual(done[0]["tag"], "r01")
        with self.assertRaises(ar.Refused):
            ar.submit(self.st, "p1-001", self.path)

    def test_every_malformation_refused(self):
        k = self.keys
        good = [verdict(x) for x in k]
        cases = {
            "not valid JSON": good[:3] + ["{broken"],
            "no line for this packet": good[:3],
            "more than once": good + [good[0]],
            "not in batch": good + [verdict("999-x")],
            "verdict": good[:3] + [verdict(k[3], v="maybe")],
            "a slip's kind": good[:3] + [verdict(k[3], v="slip", kind=None)],
            "a slip needs a correction": good[:3] + [verdict(k[3], v="slip", correction="")],
            "kind must be null for valid": good[:3] + [verdict(k[3], kind="other")],
            "correction must be null for valid": good[:3] + [verdict(k[3], correction="x")],
            "joint_variant row needs": good[:3] + [verdict(k[3], v="unsure", kind="joint_variant")],
            "confidence": good[:3] + [verdict(k[3], confidence="sure")],
            "reason must be": good[:3] + [verdict(k[3], reason=" ")],
            "unknown field": good[:3] + [verdict(k[3], note="x")],
            "missing field": good[:3] + [{"key": k[3], "verdict": "valid"}],
            "also, when given": good[:3] + [verdict(k[3], also=[{"text": "a"}])],
        }
        for want, rows in cases.items():
            probs = self.problems(rows)
            self.assertTrue(any(want in p for p in probs), "%s: %s" % (want, probs))
        write_verdicts(self.path, cases["verdict"])
        with self.assertRaises(ar.Refused) as cm:
            ar.submit(self.st, "p1-001", self.path)
        self.assertIn("REFUSED", str(cm.exception))
        self.assertFalse(os.path.exists(self.st.done("p1-001")))
        self.assertTrue(os.path.exists(self.st.claim("p1-001")))

    def test_unsure_and_also_accepted(self):
        k = self.keys
        rows = [verdict(x) for x in k[:2]]
        rows.append(verdict(k[2], v="unsure", kind="joint_variant", correction="saltvannområdet",
                            confidence="low"))
        rows.append(verdict(k[3], v="slip", also=[{"text": "av av", "correction": "av",
                                                   "reason": "a doubled word"}]))
        self.assertEqual(self.problems(rows), [])

    def test_unclaimed_refused(self):
        write_verdicts(self.path, [verdict(k) for k in self.keys])
        ar.release(self.st, "p1-001")
        with self.assertRaises(ar.Refused):
            ar.submit(self.st, "p1-001", self.path)


class SecondPassAndMerge(Base):
    def setUp(self):
        Base.setUp(self)
        self.make(many_rows(30))
        ar.queue(self.st, 1, batch=10, seed=5)

    def test_selection(self):
        with self.assertRaises(ar.Refused):
            ar.queue(self.st, 2)            # no pass-1 batch is done
        got = ar.take(self.st, "r01")
        keys = [p["key"] for p in got["packets"]]
        write_verdicts(got["out"], [verdict(keys[0], "slip"), verdict(keys[1], "unsure")]
                       + [verdict(k) for k in keys[2:]])
        ar.submit(self.st, got["batch"], got["out"])
        new, line = ar.queue(self.st, 2, dry_run=True)
        self.assertEqual(new[0]["keys"], [keys[0]])
        self.assertIsNone(self.st.queue(2))
        new, _ = ar.queue(self.st, 2, include_unsure=True, dry_run=True)
        self.assertEqual(set(new[0]["keys"]), set(keys[:2]))
        new, line = ar.queue(self.st, 2)
        self.assertIn("2 pass-1 batches not done yet", line)
        self.assertEqual([(b["id"], b["keys"]) for b in new], [("p2-001", [keys[0]])])
        with self.assertRaises(ar.Refused):
            ar.queue(self.st, 2)            # nothing new waits

    def test_second_wave_numbers_on_and_shows_the_same_packet(self):
        judge = stand_in({}, default="slip")
        run_reader(self.st, "r01", judge, limit=1)
        ar.queue(self.st, 2, batch=100)
        run_reader(self.st, "r02", judge, n=1)   # pass 1's other batches
        new, _ = ar.queue(self.st, 2, batch=100)
        self.assertEqual(new[0]["id"], "p2-002")
        self.assertEqual(len(new[0]["keys"]), 20)
        p2 = ar.take(self.st, "r03", 2)
        for p in p2["packets"]:
            self.assertEqual(p, ar.reader_view(self.st.packets()[p["key"]]))
            self.assertNotIn("verdict", json.dumps(p))

    def test_merge_outcomes(self):
        def judged(tag, pass_, pick):
            got = ar.take(self.st, tag, pass_)
            keys = [p["key"] for p in got["packets"]]
            write_verdicts(got["out"], [verdict(k, pick(i, k)) for i, k in enumerate(keys)])
            ar.submit(self.st, got["batch"], got["out"])
            return keys
        a = judged("r01", 1, lambda i, k: {0: "slip", 1: "slip", 2: "unsure"}.get(i, "valid"))
        judged("r01", 1, lambda i, k: "valid")
        ar.queue(self.st, 2, batch=100)
        # pass 2 confirms a[0] and calls a[1] valid
        second = judged("r02", 2, lambda i, k: "slip" if k == a[0] else "valid")
        self.assertEqual(set(second), set(a[:2]))
        c = judged("r01", 1, lambda i, k: "slip" if i == 0 else "valid")
        rows = {r["word"]: r for r in ar.outcomes(self.st)}
        word = lambda k: self.st.packets()[k]["word"]
        self.assertEqual(rows[word(a[0])]["outcome"], "slip")
        self.assertEqual(rows[word(a[1])]["outcome"], "disputed")
        self.assertEqual(rows[word(a[2])]["outcome"], "unsure")
        self.assertEqual(rows[word(c[0])]["outcome"], "slip (one pass)")
        self.assertEqual(rows[word(a[3])]["outcome"], "valid")
        self.assertEqual(rows[word(a[0])]["pass2_verdict"], "slip")
        order = [r["outcome"] for r in ar.outcomes(self.st)]
        self.assertEqual(order, sorted(order, key=ar.OUTCOMES.index))
        out = os.path.join(self.tmp, "merged.csv")
        ar.merge(self.st, out)
        with io.open(out, encoding="utf-8-sig") as f:
            got_rows = list(csv.DictReader(f))
        self.assertEqual(len(got_rows), 30)
        self.assertEqual(got_rows[0]["outcome"], "slip")
        md = os.path.join(self.tmp, "merged.md")
        ar.merge(self.st, md, fmt="md")
        with io.open(md, encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 32)
        self.assertTrue(lines[0].startswith("| outcome |"))
        self.assertEqual({r["outcome"] for r in ar.disputed(self.st)} - {"unsure", "disputed"},
                         set())


class EndToEnd(Base):
    def test_whole_run_with_stand_in_agents(self):
        self.make(many_rows(53, marked=20))
        ar.queue(self.st, 1, batch=10, seed=11, sample=8)
        slips = {"feilord30", "feilord31", "feilord40", "feilord2"}
        judge = stand_in({w: "slip" for w in slips})
        n = run_reader(self.st, "r01", judge, limit=2) + run_reader(self.st, "r02", judge)
        self.assertEqual(n, 5)                                  # 33 + 8 = 41 packets
        read1 = set(self.st.verdicts(1))
        self.assertEqual(len(read1), 41)
        ar.queue(self.st, 2, batch=10)
        # pass 2 agrees except on feilord31
        run_reader(self.st, "r03", stand_in({w: "slip" for w in slips - {"feilord31"}}), n=2)
        rows = {r["word"]: r["outcome"] for r in ar.outcomes(self.st)}
        for w in slips:
            if any(k.endswith("-" + w) for k in read1):
                self.assertEqual(rows[w], "disputed" if w == "feilord31" else "slip")
        self.assertIn("pass 2: 1 batches (0 open, 0 claimed, 1 done)", ar.status(self.st))
        self.assertEqual(len(ar.outcomes(self.st, everything=True)), 53)

    def test_command_line(self):
        write_tsv(self.tsv)
        state = os.path.join(self.tmp, "cli")

        def run(*args):
            p = subprocess.run([sys.executable, os.path.join(HERE, "agent_review.py"),
                                "--state", state] + list(args),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return p.returncode, p.stdout.decode("utf-8")
        self.assertEqual(run("packets", self.tsv)[0], 0)
        self.assertEqual(run("queue", "--pass", "1")[0], 0)
        code, out = run("take", "--as", "r01")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("batch p1-001 (pass 1, 4 packets)"))
        packets = [json.loads(x) for x in lines[4:]]
        self.assertEqual(len(packets), 4)
        path = lines[1].split(": ", 1)[1]
        write_verdicts(path, [verdict(p["key"]) for p in packets][:3])
        code, out = run("submit", "p1-001", path)
        self.assertEqual(code, 1)
        self.assertIn("no line for this packet", out)
        code, out = run("take", "--as", "r02")
        self.assertIn("nothing left", out)
        self.assertIn("help", subprocess.run([sys.executable, os.path.join(HERE, "agent_review.py"),
                                              "--help"], stdout=subprocess.PIPE).stdout.decode())


CHECKS = os.path.dirname(HERE)
HAVE_CHECKS = all(os.path.exists(os.path.join(CHECKS, f)) for f in ("common.py", "word_forms.py"))


def article(aid, lemma, forms, definitions, status=8):
    return {"article_id": aid, "status": status,
            "lemmas": [{"lemma": lemma, "paradigm_info": [{"tags": ["NOUN"], "inflection": [
                {"tags": ["Sing"], "word_form": f} for f in forms]}]}],
            "body": {"definitions": [{"type_": "definition", "id": 1, "elements": definitions}]}}


def sense(did, expl, quotes=()):
    els = [{"type_": "explanation", "content": expl, "items": []}]
    els += [{"type_": "example", "quote": {"content": q, "items": []}} for q in quotes]
    return {"type_": "definition", "id": did, "elements": els}


@unittest.skipUnless(HAVE_CHECKS, "needs common.py and word_forms.py in %s" % CHECKS)
class WithArticles(Base):
    def setUp(self):
        Base.setUp(self)
        arts = [
            article(1, "hus", ["hus", "huset"],
                    [sense(2, "bygning til å bo i", ["et stort huus"]), sense(3, "familie")]),
            article(2, "bygning", ["bygning", "bygningen"], [sense(2, "noe som er bygd")]),
            article(3, "stor", ["stor", "stort", "store"], [sense(2, "av stort omfang")]),
            article(4, "stue", ["stue", "stua"], [sense(2, "rom i et hus")]),
        ]
        self.articles = os.path.join(self.tmp, "articles.jsonl")
        with io.open(self.articles, "w", encoding="utf-8") as f:
            for a in arts:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        write_tsv(self.tsv, [["1", "hus", "betydning 1 (definisjon id 2), eksempel 1",
                              "unknown_form", "huus", "1", "et stort huus", ""]])
        pks, lex = ar.build_packets(self.tsv, articles=self.articles)
        ar.save_packets(self.st, pks, lex)
        self.p = pks[0]

    def test_whole_sense_other_senses_and_nearest(self):
        p = self.p
        self.assertEqual(p["senses"][0]["sense"], "1")
        self.assertEqual(p["senses"][0]["definitions"], ["bygning til å bo i"])
        self.assertEqual(p["senses"][0]["examples"], [{"quote": "et stort huus"}])
        self.assertEqual(p["other_senses"], ["2: familie"])
        self.assertEqual(p["nearest"][0]["form"], "hus")
        self.assertEqual(p["nearest"][0]["count"], 1)           # "rom i et hus"
        self.assertEqual(p["nearest"][0]["lemmas"][0]["headwords"], ["hus"])
        self.assertNotIn("texts", p)

    def test_forms_lookup(self):
        lex = self.st.lexicon()
        self.assertTrue(lex.lookup("stort")["known"])
        self.assertEqual(lex.lookup("stort")["lemmas"][0]["article_id"], "3")
        self.assertEqual(lex.lookup("bygnign")["nearest"][0]["form"], "bygning")

    def test_correction_must_be_known(self):
        ar.queue(self.st, 1)
        got = ar.take(self.st, "r01")
        key = got["packets"][0]["key"]
        write_verdicts(got["out"], [verdict(key, "slip", correction="et stort hhus")])
        with self.assertRaises(ar.Refused) as cm:
            ar.submit(self.st, "p1-001", got["out"])
        self.assertIn("ADVISORY", str(cm.exception))
        with self.assertRaises(ar.Refused):
            ar.submit(self.st, "p1-001", got["out"], override=True)   # no override_reason
        write_verdicts(got["out"], [verdict(key, "slip", correction="et stort hhus",
                                            override_reason="a known older spelling")])
        self.assertIn("1 flagged", ar.submit(self.st, "p1-001", got["out"], override=True))
        self.assertEqual(ar.read_jsonl(self.st.done("p1-001"))[0]["unknown_words"], ["hhus"])

    def test_known_correction_accepted(self):
        ar.queue(self.st, 1)
        got = ar.take(self.st, "r01")
        write_verdicts(got["out"], [verdict(got["packets"][0]["key"], "slip",
                                            correction="et stort hus")])
        self.assertIn("ACCEPTED", ar.submit(self.st, "p1-001", got["out"]))


if __name__ == "__main__":
    unittest.main()
