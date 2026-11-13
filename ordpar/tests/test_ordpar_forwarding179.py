# -*- coding: utf-8 -*-
"""Site decisions 179 (2026-11-08): the audio Worker forwards superseded clip names. This file pins
the sync step, `ordpar/audio-worker/sync_forwarding.py`, which copies the audio store's
`forwarding.json` (written by `scripts/audio/forwarding.py`) into the Worker's bundled
`ordpar/audio-worker/src/forwarding.json`. The Worker's side (the 302, its headers, no bucket call)
is pinned by `ordpar/audio-worker/test/worker.test.js`, run by `test_ordpar_audioworker159.py`.
Brief: `docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-forwarding-179-2026-11-08.md`.

What it pins, on synthetic tables in a temporary folder (the store on E: is never read):

* **flattening**: `a -> b`, `b -> c` give `a -> c`, `b -> c`; a longer chain ends at its last name;
  the count of moved targets printed;
* **refusals**, each with exit status 1 and nothing written: a cycle (named in the message), a pair
  forwarding a name to itself, a name that is not 16 lower-case hex (upper case, 15 digits, a full
  file name), a table without `pairs`;
* **writes only on change**: the same input twice writes once (the file's time untouched the second
  time), a changed input writes again; the output keeps the source's `written` and `shipped`;
* the script run as `python -I` with an explicit path and `--out`;
* the committed `src/forwarding.json`: valid JSON with `pairs`, every name 16 lower-case hex, no
  chain left and no self-pair.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKER = os.path.join(ROOT, "ordpar", "audio-worker")
SCRIPT = os.path.join(WORKER, "sync_forwarding.py")

_spec = importlib.util.spec_from_file_location("sync_forwarding", SCRIPT)
sync_forwarding = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_forwarding)

A, B, C, D = ("a" * 16, "b" * 16, "c" * 16, "d" * 16)
HEX16 = re.compile(r"^[0-9a-f]{16}$")


class Flatten(unittest.TestCase):

    def test_chain_flattened(self):
        flat, changed = sync_forwarding.flatten({A: B, B: C})
        self.assertEqual(flat, {A: C, B: C})
        self.assertEqual(changed, 1)

    def test_long_chain(self):
        flat, changed = sync_forwarding.flatten({A: B, B: C, C: D})
        self.assertEqual(flat, {A: D, B: D, C: D})
        self.assertEqual(changed, 2)

    def test_plain_pairs_unchanged(self):
        self.assertEqual(sync_forwarding.flatten({A: B, C: D}), ({A: B, C: D}, 0))
        self.assertEqual(sync_forwarding.flatten({}), ({}, 0))

    def test_cycle_refused(self):
        with self.assertRaisesRegex(sync_forwarding.Refused, "cycle"):
            sync_forwarding.flatten({A: B, B: A})
        with self.assertRaisesRegex(sync_forwarding.Refused, "cycle"):
            sync_forwarding.flatten({D: A, A: B, B: C, C: A})

    def test_self_pair_refused(self):
        with self.assertRaisesRegex(sync_forwarding.Refused, "itself"):
            sync_forwarding.flatten({A: A})

    def test_bad_names_refused(self):
        for bad in ({A.upper(): B}, {A: B.upper()}, {"a" * 15: B}, {A: "b" * 17},
                    {"ordpar-%s.mp3" % A: B}, {A: None}, {A: 7}):
            with self.assertRaisesRegex(sync_forwarding.Refused, "16 lower-case hex", msg=repr(bad)):
                sync_forwarding.flatten(bad)

    def test_not_an_object(self):
        with self.assertRaises(sync_forwarding.Refused):
            sync_forwarding.flatten([[A, B]])


class Script(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "forwarding.json")
        self.out = os.path.join(self.tmp.name, "out.json")

    def tearDown(self):
        self.tmp.cleanup()

    def table(self, pairs, **extra):
        doc = {"written": "2026-11-08T12:00:00", "shipped": ["deck-2026-11-07.tsv"],
               "current": "x", "pairs": pairs, "held": 0}
        doc.update(extra)
        with open(self.src, "w", encoding="utf-8") as f:
            json.dump(doc, f)

    def run_script(self):
        return subprocess.run([sys.executable, "-I", SCRIPT, self.src, "--out", self.out],
                              capture_output=True, text=True, encoding="utf-8", timeout=60)

    def test_writes_flattened(self):
        self.table({A: B, B: C})
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("read: 2 pairs", r.stdout)
        self.assertIn("flattened: 1", r.stdout)
        self.assertIn("written:", r.stdout)
        with open(self.out, encoding="utf-8") as f:
            doc = json.load(f)
        self.assertEqual(doc["pairs"], {A: C, B: C})
        self.assertEqual(doc["written"], "2026-11-08T12:00:00")
        self.assertEqual(doc["shipped"], ["deck-2026-11-07.tsv"])

    def test_unchanged_writes_nothing(self):
        self.table({A: B})
        self.assertEqual(self.run_script().returncode, 0)
        past = 1_000_000_000
        os.utime(self.out, (past, past))
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unchanged:", r.stdout)
        self.assertEqual(os.stat(self.out).st_mtime, past)
        # a re-run upstream: a new `written`, the same pairs and decks — not a change (2026-11-08)
        self.table({A: B}, written="2026-11-09T08:00:00")
        r = self.run_script()
        self.assertIn("unchanged:", r.stdout)
        self.assertEqual(os.stat(self.out).st_mtime, past)
        self.table({A: C})
        r = self.run_script()
        self.assertIn("written:", r.stdout)
        self.assertNotEqual(os.stat(self.out).st_mtime, past)

    def test_refusals_write_nothing(self):
        for pairs in ({A: B, B: A}, {A: A}, {A.upper(): B}):
            self.table(pairs)
            r = self.run_script()
            self.assertEqual(r.returncode, 1, (pairs, r.stdout))
            self.assertIn("refused, nothing written", r.stderr)
            self.assertFalse(os.path.exists(self.out), pairs)
        self.table({A: B, B: A})
        self.assertIn("%s -> %s -> %s" % (A, B, A), self.run_script().stderr)

    def test_refusal_keeps_the_old_file(self):
        self.table({A: B})
        self.run_script()
        with open(self.out, encoding="utf-8") as f:
            before = f.read()
        self.table({A: B, B: A})
        self.assertEqual(self.run_script().returncode, 1)
        with open(self.out, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)

    def test_no_pairs_refused(self):
        with open(self.src, "w", encoding="utf-8") as f:
            json.dump({"written": "x"}, f)
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("no 'pairs'", r.stderr)

    def test_default_path_is_the_store(self):
        # the store is this machine's, named in ordpar/local-paths.json
        self.assertEqual(sync_forwarding.STORE_TABLE,
                         sync_forwarding.local_paths.get("clip_store_forwarding"))
        self.assertEqual(sync_forwarding.OUT, os.path.join(WORKER, "src", "forwarding.json"))


class Committed(unittest.TestCase):

    def test_bundled_table(self):
        with open(os.path.join(WORKER, "src", "forwarding.json"), encoding="utf-8") as f:
            doc = json.load(f)
        pairs = doc["pairs"]
        self.assertIsInstance(pairs, dict)
        for old, new in pairs.items():
            self.assertRegex(old, HEX16)
            self.assertRegex(new, HEX16)
            self.assertNotEqual(old, new)
            self.assertNotIn(new, pairs)

    def test_worker_imports_it(self):
        with open(os.path.join(WORKER, "src", "worker.js"), encoding="utf-8") as f:
            self.assertIn("import FORWARDING from './forwarding.json';", f.read())


if __name__ == "__main__":
    unittest.main()
