# -*- coding: utf-8 -*-
"""Decisions 184, the outsider test's finding 2: no test fetches the abbreviation table or
writes it into the data folder.

In a clone of the public repository a test run went online: the table of abbreviations
(`concepts.json`) was asked of `derive.concepts_map()`, which, with no `sources/concepts.json` in
the data folder, calls `fetch.ensure_concepts`; that fetched `https://ord.uib.no/bm/concepts.json`
and wrote it to `data/sources/concepts.json`. The same table is in the public repository beside
the mirror, `data/bokmalsordboka/bm-concepts.json`. Three test files reached that path (found by
running every file outside the browser tests with `fetch.ensure_concepts` traced, 2026-11-13):
`test_ordpar_complabels151.py` called `derive.concepts_map()` itself, and
`test_ordpar_overlay182.py` and `test_ordpar_selines153.py` build a `library.Store` over a
synthetic mirror with no table of its own, as the builds those and other tests run in a
subprocess do. Now `library.mirror_concepts` takes the data folder's
`bokmalsordboka/bm-concepts.json` when the mirror has no table and there is no
`sources/concepts.json`, and the compound-label test takes its table through it.

Pinned here, in a child process set up as a clone is (the data folder `ORDBOK_DATA_DIR` holds
`bokmalsordboka/bm-concepts.json` and no `sources/concepts.json`, no `.glossary_cache/`), with
`fetch._get` replaced by a function that records the address and raises:

1. `library.mirror_concepts` over a mirror with no table returns the data folder's table, and
   nothing is fetched or written;
2. the three tests above run and pass, and nothing is fetched or written;
3. no test file calls `derive.concepts_map()` or `fetch.ensure_concepts` itself (a static check:
   the table comes through `library.mirror_concepts`).

Stdlib unittest; the child process takes a few seconds.
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
TESTS = os.path.dirname(os.path.abspath(__file__))

#: the tests that reached `fetch.ensure_concepts` before the fix
REACHED = ("test_ordpar_complabels151.EveryIntro.test_every_capture_intro_has_its_label",
           "test_ordpar_overlay182.MirrorAndChecker.test_checker_reads_the_raw_mirror",
           "test_ordpar_selines153.ThePageLibrary.test_b_the_root_only")

#: the child: fetch's network call replaced, then the code path or the tests
CHILD = r'''
import json, os, sys
root, tests, log, what = sys.argv[1:5]
sys.path[:0] = [os.path.join(root, "scripts"), root, os.path.join(root, "ordpar"), tests]
import fetch

def _get(url, *a, **k):
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(url + "\n")
    raise OSError("network blocked by test_ordpar_concepts184: " + url)

fetch._get = _get
fetch.BOOTSTRAP = os.path.join(os.path.dirname(log), "no-glossary-cache")
if what == "library":
    from ordpar.sitegen import library
    table, source = library.mirror_concepts(sys.argv[5])
    print(json.dumps({"table": table, "source": source}))
else:
    import unittest
    prog = unittest.main(module=None, argv=["x"] + sys.argv[5:], exit=False, verbosity=0)
    r = prog.result
    sys.exit(0 if r.wasSuccessful() and r.testsRun == len(sys.argv[5:]) and not r.skipped else 1)
'''

TABLE = {"concepts": {"f_eks": {"expansion": "for eksempel"}, "norr.": {"expansion": "norrønt"}}}


class NoFetchNoWrite(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ordpar-concepts184-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data = os.path.join(self.tmp, "data")
        os.makedirs(os.path.join(self.data, "bokmalsordboka"))
        with open(os.path.join(self.data, "bokmalsordboka", "bm-concepts.json"), "w",
                  encoding="utf-8", newline="\n") as fh:
            json.dump(TABLE, fh, ensure_ascii=False)
        self.log = os.path.join(self.tmp, "fetched.txt")
        self.child = os.path.join(self.tmp, "child.py")
        with open(self.child, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(CHILD)

    def run_child(self, *args):
        env = dict(os.environ, ORDBOK_DATA_DIR=self.data, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, self.child, ROOT, TESTS, self.log] + list(args),
                              cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL, timeout=600)

    def fetched(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as fh:
            return fh.read().split()

    def written(self):
        """Every file under the data folder but the table this test put there."""
        out = []
        for dp, _dn, fn in os.walk(self.data):
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), self.data).replace("\\", "/")
                if rel != "bokmalsordboka/bm-concepts.json":
                    out.append(rel)
        return sorted(out)

    def test_mirror_concepts_takes_the_data_folders_table(self):
        mirror = os.path.join(self.tmp, "synthetic-mirror", "bm-articles.jsonl")
        r = self.run_child("library", mirror)
        self.assertEqual(self.fetched(), [], "fetched over the network: %s" % r.stderr[-1500:])
        self.assertEqual(self.written(), [], "written under the data folder")
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["table"], {"f_eks": "for eksempel", "norr.": "norrønt"})
        self.assertEqual(os.path.normcase(os.path.abspath(got["source"])),
                         os.path.normcase(os.path.join(self.data, "bokmalsordboka", "bm-concepts.json")))

    def test_the_tests_that_reached_it(self):
        r = self.run_child("tests", *REACHED)
        self.assertEqual(self.fetched(), [], "fetched over the network: %s" % r.stderr[-1500:])
        self.assertEqual(self.written(), [], "written under the data folder")
        self.assertEqual(r.returncode, 0, "the tests did not all run and pass: " + r.stderr[-2000:])


class NoDirectCall(unittest.TestCase):

    CALL = re.compile(r"\b(?:concepts_map|ensure_concepts)\s*\(")

    def test_no_test_calls_it_itself(self):
        me = os.path.basename(__file__)
        bad = []
        for name in sorted(os.listdir(TESTS)):
            if not name.endswith(".py") or name == me:
                continue
            with open(os.path.join(TESTS, name), encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    code = re.sub(r"`[^`]*`", "", line)          # a mention in a docstring
                    if self.CALL.search(code) and not line.lstrip().startswith("#"):
                        bad.append("%s:%d: %s" % (name, n, line.strip()))
        self.assertEqual(bad, [], "take the table through library.mirror_concepts: " + "; ".join(bad))


if __name__ == "__main__":
    unittest.main()
