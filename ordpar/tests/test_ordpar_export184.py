"""Pins the public repository's export and what it rests on (site decisions 184, 2026-11-12).

1. **The export set passes the guard.** Every code, test and doc file the export takes from the
   private repository (ordpar/ minus the working docs, `ordbok_gen.py` and the nine pipeline
   modules) carries no mail address outside the allow-list, no private path and nothing key- or
   token-shaped. Failed before this build: the deploy commit's author address (`deploy.py`), the
   fetch layer's User-Agent, the receiver's and audio Worker's READMEs, and 16 private paths.
2. **The guard** (`export_public.Guard`) refuses a planted address, a planted private path, a
   token-shaped string, a working doc and a session file, each with its file and line; lets the
   allow-list through; counts, never refuses, an address in Bokmålsordboka's data; in release
   mode refuses a "decisions N" with no entry in the public log and a link or backticked path
   that does not resolve, which a draft only warns about.
3. **One machine's paths** (`local_paths.py`): read from the git-ignored file, None when unset,
   an unknown key refused, and `require` stopping with a message naming the flag and the file.
4. **The example gate** (`sitegen/gate.py`): `triage.publishable` where `triage` imports; else a
   library carrying its export marker is accepted, an unmarked one or one changed since its
   marker refused.
5. **The articles file in parts** (`data_parts.py`): split by id range and joined back byte for
   byte; out-of-order lines, an oversize part and a line in the wrong part refused.
6. **The divergences editions** (`divergences_print.py`): the print edition without the Decision
   column or any decision reference; the public one with the column, each number a link to
   `decisions.md#dN`, the *yes* rows first; a reference that is not such a link refused. Since
   2026-11-13 (`DivergencesDocLinks`) each row's "How it works" link to the technical docs lands
   on a real heading by GitHub's anchor rule; the print edition cuts that column, the public one
   keeps it before Decision with its links resolving from `docs/`, and a bad anchor stops both.
7. **The fetch layer** (`scripts/fetch.py`): certificates verified unless
   `ORDBOK_TLS_NO_VERIFY=1`; `sources/` and `review/` under `ORDBOK_DATA_DIR` when it is set,
   under the repository root (today's paths) when not.
8. **The export's projections**: the added sentences lose `verification` and `claim_check.note`,
   the normalization log keeps only the fields the site reads, the dangling lists only theirs.
9. **A test that imports a private module** (`PrivateImports`): in a folder holding only the
   export set, each such file ends `OK (skipped=N)`, a skip naming every missing module; the
   export's test run runs it rather than leaving it out.
10. **The `.gitattributes`** (`GitAttributes`): a public text with no sources, written at the
   public repository's root, under which git reads every file in data/ as `-text` and the
   code's text files as `text=auto eol=lf`.
11. **`build_offline.py --help`** (`OfflineHelp`) names every page of `SHELL_PAGES` and
   `OPTIONAL_PAGES`.
12. **A public text stored under another name** (`PublicTextFrom`): a text's optional `"from"`
   names its file under `ordpar/public/`, and the export writes it at `"path"`; so the assistant
   guide, stored as `ordpar/public/CLAUDE.public.md` (a `CLAUDE.md` in a folder of the private
   repository could be loaded by Claude Code working there), is written at the public
   repository's root as `CLAUDE.md`, and no `CLAUDE.public.md` goes out.
13. **Paths local by design** (`LocalByDesign`): a backticked path that a reader of the public
   repository has but the repository does not carry (`export_public.LOCAL_BY_DESIGN`) passes the
   release guard, any other that does not resolve still refuses, and the exported Markdown files
   carry no path the guard refuses. Failed before (2026-11-13): 14 paths in five files.
14. **A public text in place of a file from `main`** (`TextFromMain`; the outsider test's findings
   4, 5 and 16): a source written `main:<path>` is hashed from `git show`, so a change on `main`
   makes the text stale; the public text is written over `main`'s file; the checks' README is
   such a text, stamped. Failed before (2026-11-13): no `source_hash`, no such text.
15. **A reader's own files** (finding 19): in the public repository the tests that read the
   export's files read only what git tracks, so a notes file or a renamed build folder of the
   reader's own makes nothing fail.

Pure Python, synthetic files in a temporary folder; nothing outside the repository is read.
"""
import hashlib
import inspect
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)

import export_public as X  # noqa: E402
import local_paths  # noqa: E402
import data_parts  # noqa: E402
import divergences_print as D  # noqa: E402
from ordpar.sitegen import gate  # noqa: E402


#: run in the public repository (or a copy of the export), not in the private one
IN_EXPORT = not os.path.isdir(os.path.join(ORDPAR, "public"))


def tracked_files():
    """Every file git tracks in this checkout, or None without git (the copy of the export the
    export's own test run uses has no `.git/`)."""
    try:
        return {p for p in X.git("ls-files", "-z").split("\0") if p}
    except (SystemExit, OSError):
        return None


def export_set():
    """The files the export takes from this checkout, as repository paths (the private side only:
    without git, the files under ordpar/ on disk). In the public repository only the files git
    tracks: a reader's own file in the clone (a notes file, a build folder renamed aside) is not
    part of the export (decisions 184, the outsider test's finding 19)."""
    try:
        tracked, untracked = X.ordpar_files()
        files = tracked if IN_EXPORT else tracked + untracked
    except SystemExit:
        files = []
        for dp, dn, fn in os.walk(ORDPAR):
            dn[:] = [d for d in dn if d not in ("__pycache__", "out", ".build", "public")]
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/")
                if rel not in X.WORKING_DOCS and rel != "ordpar/local-paths.json":
                    files.append(rel)
    return sorted(files) + [p for p in X.PIPELINE if os.path.exists(os.path.join(ROOT, p))]


class ExportSet(unittest.TestCase):

    def test_export_set_passes_the_guard(self):
        g = X.Guard(release=False)
        files = export_set()
        self.assertGreater(len(files), 100)
        for rel in files:
            g.path(rel)
            with open(os.path.join(ROOT, rel), "rb") as fh:
                g.text(rel, fh.read())
        self.assertEqual(g.refusals, [], "\n".join("%s:%s: %s: %s" % f for f in g.refusals[:20]))


#: the planted values, cut so that this file does not hold them whole (it is exported too)
CC = "Claude" + " Code"
THEIRS = "ola" + "@uib.no"


class GuardTest(unittest.TestCase):

    def run_guard(self, files, release=False):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel, text in files.items():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        g, _ = X.run_guard(tmp, release)
        return g

    def test_planted_address_and_path_refused(self):
        bad = "na" + "me@gm" + "ail.com"
        path = "C:" + "/" + CC + "/ordbok-anki/.mirror/x.jsonl"
        g = self.run_guard({"ordpar/a.py": "x = 1\nAUTHOR = '%s'\n" % bad,
                            "ordpar/b.md": "line one\n\nsee %s\n" % path})
        kinds = sorted((r[0], r[1], r[2]) for r in g.refusals)
        self.assertEqual(kinds, [("ordpar/a.py", 2, "mail address"), ("ordpar/b.md", 3, "private path")])

    def test_allow_list_and_their_data(self):
        g = self.run_guard({"ordpar/a.py": "A = 'post@ordpar.no'\nB = 'x@example.org'\nC = 'k@example.com'\n",
                            "data/bokmalsordboka/bm-articles.000000.jsonl": '{"t": "skriv til %s"}\n' % THEIRS})
        self.assertEqual(g.refusals, [])
        self.assertEqual(g.their_mail, {THEIRS: 1})

    def test_other_private_paths(self):
        for p in ("E:" + "\\" + CC + " Storage\\x", "/c/" + "Users/someone/x", "C:" + "\\Users\\x\\y.txt",
                  "/home/" + "someone/x", "C:" + "/" + CC + "/x"):
            g = self.run_guard({"ordpar/a.md": "at %s\n" % p})
            self.assertEqual([r[2] for r in g.refusals], ["private path"], p)
        g = self.run_guard({"ordpar/a.py": "F = 'C:/Windows/Fonts/seguisb.ttf'\nG = 'E:/x/f.frk'\n"})
        self.assertEqual(g.refusals, [])

    def test_tokens(self):
        g = self.run_guard({"ordpar/a.js": "const k = '%s';\n" % ("Zq8xW2mN4pL7vR1t" + "Y6uK3sD9fG5hJ0aB"),
                            "ordpar/b.py": "API_" + "KEY = 'qwertzuiopasdfgh'\n",
                            "ordpar/c.py": "H = 'ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12'  # a hash\n"
                                           "T = 'local-reports-token-0000'\n"})
        self.assertEqual(sorted((r[0], r[2]) for r in g.refusals),
                         [("ordpar/a.js", "token-shaped"), ("ordpar/b.py", "token-shaped")])

    def test_working_docs_and_sessions(self):
        g = self.run_guard({"ordpar/docs/ideas.md": "x\n", "docs/sessions/s/record.md": "x\n"})
        self.assertEqual(sorted(r[0] for r in g.refusals), ["docs/sessions/s/record.md", "ordpar/docs/ideas.md"])

    def test_release_checks(self):
        files = {"ordpar/a.py": "# site decisions 12 and decisions " "999; audio decisions 7\n",
                 "docs/decisions.md": "# Decisions\n\n## 12. Twelve\n",
                 "README.md": "See [the log](docs/decisions.md), [gone](docs/nope.md), `ordpar/a.py`, "
                              "`ordpar/missing.py` and/or this.\n"}
        draft = self.run_guard(files, release=False)
        self.assertEqual(draft.refusals, [])
        self.assertEqual(sorted(w[2] for w in draft.warnings), ["decision", "link", "path"])
        rel = self.run_guard(files, release=True)
        found = sorted((r[0], r[2], r[3]) for r in rel.refusals)
        self.assertEqual([f[:2] for f in found], [("README.md", "link"), ("README.md", "path"),
                                                  ("ordpar/a.py", "decision")])
        self.assertIn("decisions " "999", found[2][2])     # split, here and above: the guard reads this file too
        no_log = self.run_guard({"ordpar/a.py": "# decisions 3\n"}, release=True)
        self.assertEqual([r[2] for r in no_log.refusals], ["decision log"])


class LocalPaths(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        local_paths._cache.clear()
        self.addCleanup(local_paths._cache.clear)

    def test_unset_and_set(self):
        p = os.path.join(self.tmp, "local-paths.json")
        self.assertIsNone(local_paths.get("mirror", p))
        with self.assertRaises(local_paths.Missing) as cm:
            local_paths.require("mirror", "--mirror FILE", p)
        self.assertIn("--mirror FILE", str(cm.exception))
        self.assertIn("local-paths.json", str(cm.exception))
        local_paths._cache.clear()
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"mirror": "/x/bm-articles.jsonl"}, fh)
        self.assertEqual(local_paths.require("mirror", None, p), "/x/bm-articles.jsonl")
        self.assertIsNone(local_paths.get("freq", p))

    def test_unknown_key_refused(self):
        p = os.path.join(self.tmp, "local-paths.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"mirorr": "/x"}, fh)
        with self.assertRaises(ValueError):
            local_paths.load(p)

    def test_example_names_every_key(self):
        with open(local_paths.EXAMPLE, encoding="utf-8") as fh:
            self.assertEqual(sorted(json.load(fh)), sorted(local_paths.KEYS))


class Gate(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lib = os.path.join(self.tmp, "articles.jsonl")
        with open(self.lib, "w", encoding="utf-8", newline="\n") as fh:
            fh.write('{"id": 1}\n{"id": 2}\n')

    def test_triage_when_importable(self):
        fake = mock.Mock()
        fake.publishable.return_value = ([{"id": 1}], 3)
        with mock.patch.object(gate, "triage_module", return_value=fake):
            rows, held, how = gate.apply([{"id": 1}, {"id": 2}], self.lib)
        self.assertEqual((rows, held, how), ([{"id": 1}], 3, "triage.publishable"))

    def test_marker_without_triage(self):
        rows = [{"id": 1}, {"id": 2}]
        with mock.patch.object(gate, "triage_module", return_value=None):
            with self.assertRaises(gate.Refused) as cm:
                gate.apply(rows, self.lib)
            self.assertIn("no gate marker", str(cm.exception))
            # true for a reader of the public repository too, which has no export_public.py
            # (the outsider test's finding 9): it names the writer and the doc that says how
            self.assertIn("gate.write_marker", str(cm.exception))
            self.assertIn("data/README.md", str(cm.exception))
            self.assertNotIn("export_public", str(cm.exception))
            gate.write_marker(self.lib, 2, 0)
            got, held, how = gate.apply(rows, self.lib)
            self.assertEqual((got, held), (rows, 0))
            self.assertIn("gated at export", how)
            with open(self.lib, "a", encoding="utf-8") as fh:
                fh.write('{"id": 3}\n')
            with self.assertRaises(gate.Refused) as cm:
                gate.apply(rows, self.lib)
            self.assertIn("changed since it was gated", str(cm.exception))
            self.assertIn("gate.write_marker", str(cm.exception))
            self.assertNotIn("re-export", str(cm.exception))

    def test_marker_is_byte_stable(self):
        gate.write_marker(self.lib, 2, 0)
        a = open(gate.marker_path(self.lib), "rb").read()
        gate.write_marker(self.lib, 2, 0)
        self.assertEqual(open(gate.marker_path(self.lib), "rb").read(), a)

    def test_private_side_has_triage(self):
        if not os.path.exists(os.path.join(ROOT, "scripts", "triage.py")):
            self.skipTest("the public repository has no triage (the gate is the export's marker)")
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        self.assertIsNotNone(gate.triage_module())


class Parts(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, "bm-articles.jsonl")
        lines = ['{"id": %d, "revision": "1", "data": {"x": "%s"}}\n' % (i, "å" * (i % 7))
                 for i in (1, 2, 19999, 20000, 45000, 45001, 99999)]
        with open(self.src, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(lines))

    def test_round_trip(self):
        out = os.path.join(self.tmp, "parts")
        got = data_parts.split(self.src, out)
        self.assertEqual([os.path.basename(p) for p, _ in got],
                         ["bm-articles.000000.jsonl", "bm-articles.020000.jsonl",
                          "bm-articles.040000.jsonl", "bm-articles.080000.jsonl"])
        path, n = data_parts.join(out)
        self.assertEqual(n, 7)
        self.assertEqual(open(path, "rb").read(), open(self.src, "rb").read())

    def test_refusals(self):
        with open(self.src, "a", encoding="utf-8") as fh:
            fh.write('{"id": 5}\n')
        with self.assertRaises(data_parts.Refused):
            data_parts.split(self.src, os.path.join(self.tmp, "p1"))
        with self.assertRaises(data_parts.Refused):
            data_parts.split(self.src, os.path.join(self.tmp, "p2"), limit=60)
        out = os.path.join(self.tmp, "p3")
        os.makedirs(out)
        with open(os.path.join(out, "bm-articles.020000.jsonl"), "w") as fh:
            fh.write('{"id": 3}\n')
        with self.assertRaises(data_parts.Refused):
            data_parts.join(out)


SAMPLE = """# Where Ordpar differs

| Column | Holds |
|---|---|
| What | the difference |
| Decision | the project's record: [`dictionary-site-decisions.md`](dictionary-site-decisions.md) |

## The tables

| What | Ordbokene.no today | Ordpar | Why | Of use to ordbokene? | Decision |
|---|---|---|---|---|---|
| A | a | a | a | **No.** ours | [5][d5] (2026-09-01) |
| B | b | b | b | **Yes.** theirs | [12][d12] (2026-09-05); [59][d59] |
| C | c | c | c | **Maybe.** perhaps | [9][d9] |

## For the project's own record

Decisions 5 and 12, [d5]: dictionary-site-decisions.md#d5
"""


class Divergences(unittest.TestCase):

    def test_print_edition(self):
        s = D.edition(SAMPLE)
        self.assertNotIn("Decision", s)
        self.assertNotIn("[d", s)
        rows = [l for l in s.split("\n") if l.startswith("| ") and "**" in l]
        self.assertEqual([r[2] for r in rows], ["B", "C", "A"])

    def test_public_edition(self):
        s = D.edition(SAMPLE, public=True)
        self.assertIn("| Decision |", s)
        self.assertIn("[12](decisions.md#d12) (2026-09-05); [59](decisions.md#d59)", s)
        self.assertNotIn("dictionary-site-decisions", s)
        self.assertNotIn("own record", s)
        rows = [l for l in s.split("\n") if l.startswith("| ") and "**" in l]
        self.assertEqual([r[2] for r in rows], ["B", "C", "A"])
        self.assertEqual({len(D.cells(r)) for r in rows}, {6})

    def test_public_refuses_a_loose_reference(self):
        with self.assertRaises(SystemExit):
            D.edition(SAMPLE.replace("| a | a | a |", "| a (decisions 44) | a | a |"), public=True)

    # 2026-11-12 (decisions 184: that counts as a divergence): a section of what
    # ordbokene.no has and Ordpar lacks, a list after the tables and before the project's record
    ABSENCES = ("\n## What ordbokene.no has that Ordpar lacks\n\n"
                "Features of ordbokene.no that Ordpar does not have.\n\n"
                "- **Advanced search.** Wildcards (`*`, `%`, `_`) and `|` (checked 12 November 2026). "
                "Ordpar: planned, but not a priority.\n"
                "- **A button back to the top.** No decision yet.\n")

    def with_absences(self, extra=""):
        return SAMPLE.replace("\n## For the project's own record", self.ABSENCES + extra
                              + "\n## For the project's own record")

    def test_the_section_of_absences_is_kept_in_both_editions(self):
        for public in (False, True):
            s = D.edition(self.with_absences(), public=public)
            self.assertIn(self.ABSENCES.strip(), s)
            self.assertNotIn("own record", s)
            rows = [l for l in s.split("\n") if l.startswith("| ") and "**" in l]
            self.assertEqual([r[2] for r in rows], ["B", "C", "A"])

    def test_a_reference_in_the_section_stops_both_editions(self):
        text = self.with_absences("- **Codes.** Skipped in decisions 21.\n")
        for public in (False, True):
            with self.assertRaises(SystemExit):
                D.edition(text, public=public)

    @unittest.skipUnless(os.path.exists(os.path.join(ORDPAR, "docs", "divergences.md")),
                         "the divergences record is private; the public repository has its edition only")
    def test_the_record_makes_both(self):
        with io.open(os.path.join(ORDPAR, "docs", "divergences.md"), encoding="utf-8") as fh:
            text = fh.read()
        prn = D.edition(text)
        pub = D.edition(text, public=True)
        self.assertGreater(pub.count("](decisions.md#d"), 50)
        for s in (prn, pub):
            self.assertIn("\n## What ordbokene.no has that Ordpar lacks\n", s)

    def test_the_record_itself_stays_private(self):
        # Robin, 2026-11-12: the public edition only, not the raw record beside it (decisions 184)
        self.assertIn("ordpar/docs/divergences.md", X.WORKING_DOCS)
        self.assertNotIn("ordpar/docs/divergences.md", export_set())


#: the record's links are relative to its own folder, ordpar/docs/
RECORD_DIR = os.path.join(ORDPAR, "docs")
RECORD = os.path.join(RECORD_DIR, "divergences.md")
#: a table of the record with the "How it works" column (decisions 184, Robin 2026-11-13)
SAMPLE_HOW = """# Where Ordpar differs

| Column | Holds |
|---|---|
| What | the difference |
| Decision | the project's record: [`dictionary-site-decisions.md`](dictionary-site-decisions.md) |
| How it works | the section of the technical docs |

## The tables

| What | Ordbokene.no today | Ordpar | Why | Of use to ordbokene? | Decision | How it works |
|---|---|---|---|---|---|---|
| A | a | a | a | **No.** ours | [5][d5] (2026-09-01) | [The search index, § (2) Suggestions](lookup-index.md#2-suggestions) |
| B | b | b | b | **Yes.** theirs | [12][d12] (2026-09-05) | [The receiver's README, § Files](../receiver/README.md#files); [The audio Worker's README, § Files](../audio-worker/README.md#files) |
| C | c | c | c | **Maybe.** perhaps | [9][d9] | |

## For the project's own record

Decisions 5 and 12, [d5]: dictionary-site-decisions.md#d5
"""


def how_links(s):
    """``(target, row What)`` for every Markdown link in the "How it works" cells of ``s``."""
    out, how = [], None
    for line in s.split("\n"):
        if not line.startswith("|"):
            how = None
            continue
        c = [x.strip() for x in D.cells(line)]
        if "How it works" in c and "Decision" in c and len(c) >= 7:
            how = c.index("How it works")
            continue
        if how is not None and len(c) > how and not set(line) <= set("|-: "):
            out += [(t, c[0]) for t in re.findall(r"\]\(([^)\s]+)\)", c[how])]
    return out


def private_path(exported):
    """Where an exported file (a path in the public repository) sits in this checkout, or None
    in the public repository itself."""
    if IN_EXPORT:
        return os.path.join(ROOT, exported)
    if exported.startswith("ordpar/"):
        return os.path.join(ROOT, exported)
    return os.path.join(ORDPAR, "public", exported)


class DivergencesDocLinks(unittest.TestCase):
    """Each row of the divergences record links the section of the technical docs that describes
    the feature as built, in a last column "How it works" (decisions 184: links
    to the relevant sections of the technical docs): every such link lands on a real file and a real
    heading's anchor, made by GitHub's rule (`divergences_print.anchor`); the print edition cuts the
    column; the public one keeps it before the Decision column, its links resolving from `docs/`;
    a planted bad anchor stops either edition."""

    # the rule, on real headings: backticks, parentheses, a full stop, a colon, quotation marks, an
    # arrow, an em dash, an underscore, a non-ASCII letter, a "§" (from the decision log: no
    # technical doc has one in a heading)
    REAL = [
        ("ordpar/docs/lookup-index.md", "## 4. The query algorithms (`lookup.js`)",
         "4-the-query-algorithms-lookupjs"),
        ("ordpar/docs/lookup-index.md", "### `translated.json`, `random.json`, `labels.json`",
         "translatedjson-randomjson-labelsjson"),
        ("ordpar/docs/build-site.md", '### The compound line, the "Se:" line, pronunciation',
         "the-compound-line-the-se-line-pronunciation"),
        ("ordpar/docs/build-site.md", "# `build_site.py` — the article-page build",
         "build_sitepy--the-article-page-build"),
        ("ordpar/docs/build-site.md", "## Report a mistake, the survey and the receiver's events",
         "report-a-mistake-the-survey-and-the-receivers-events"),
        ("ordpar/docs/offline-app.md", "## 4. The service worker (`ordpar/root/sw.js` → `/sw.js`)",
         "4-the-service-worker-ordparrootswjs--swjs"),
        ("ordpar/docs/inflection-table.md", "## 6. Differences from ordbokene.no, and open questions",
         "6-differences-from-ordbokeneno-and-open-questions"),
        ("ordpar/public/data/bokmalsordboka/README.md", "# Bokmålsordboka's data", "bokmålsordbokas-data"),
        ("ordpar/docs/dictionary-site-decisions.md",
         "### 21. Five small inventory calls (plan § 1.1) — RULED 2026-09-19",
         "21-five-small-inventory-calls-plan--11--ruled-2026-09-19"),
    ]

    def test_the_anchor_rule(self):
        for path, heading, anchor in self.REAL:
            self.assertEqual(D.anchor(heading.lstrip("#").strip()), anchor, heading)
            full = os.path.join(ROOT, path)
            if os.path.exists(full):           # a real heading of that file, found by the reader
                with io.open(full, encoding="utf-8") as fh:
                    text = fh.read()
                self.assertIn("\n" + heading + "\n", "\n" + text, path)
                self.assertIn(anchor, D.heading_anchors(text), path)

    def test_the_docs_own_anchor_links_agree(self):
        # the links inside a doc to its own headings (build-site.md's contents list among them,
        # 23 on 2026-11-13) land on anchors the rule makes
        found = 0
        for rel in ("docs/build-site.md", "docs/lookup-index.md", "docs/inflection-table.md",
                    "docs/offline-app.md", "docs/receiver.md", "docs/tests.md", "README.md"):
            with io.open(os.path.join(ORDPAR, rel), encoding="utf-8") as fh:
                text = fh.read()
            anchors = D.heading_anchors(text)
            for frag in re.findall(r"\]\(#([^)\s]+)\)", text):
                found += 1
                self.assertIn(frag, anchors, rel)
        self.assertGreater(found, 15)

    def test_repeats_fences_and_closing_hashes(self):
        text = ("# A\n\n## A ##\n\n```\n# not a heading\n```\n\n### A\n\n#not one either\n"
                "    # indented code\n## Mixed *Case* and [a link](x.md)\n")
        self.assertEqual(D.heading_anchors(text), {"a", "a-1", "a-2", "mixed-case-and-a-link"})

    def test_the_sample_carries_through(self):
        prn = D.edition(SAMPLE_HOW)
        self.assertNotIn("How it works", prn)
        self.assertNotIn(".md#", prn)
        pub = D.edition(SAMPLE_HOW, public=True)
        self.assertIn("| Of use to ordbokene? | How it works | Decision |", pub)
        self.assertIn("[The search index, § (2) Suggestions](../ordpar/docs/lookup-index.md#2-suggestions)", pub)
        self.assertIn("(../ordpar/receiver/README.md#files)", pub)
        key = [l for l in pub.split("\n") if l.startswith(("| How it works |", "| Decision |"))]
        self.assertEqual([k.split("|")[1].strip() for k in key], ["How it works", "Decision"])
        self.assertIn(D.PUBLIC_HOW_KEY, pub)
        rows = [l for l in pub.split("\n") if l.startswith("| ") and "**" in l]
        self.assertEqual([r[2] for r in rows], ["B", "C", "A"])
        self.assertEqual({len(D.cells(r)) for r in rows}, {7})
        self.assertTrue(rows[0].endswith("| [12](decisions.md#d12) (2026-09-05) |"), rows[0])

    def test_a_planted_bad_anchor_stops_both_editions(self):
        for bad in ("lookup-index.md#2-suggestion", "lookup-index.md#", "lookup-index.md",
                    "no-such-doc.md#files", "../receiver/README.md#tests-1"):
            text = SAMPLE_HOW.replace("lookup-index.md#2-suggestions", bad)
            for public in (False, True):
                with self.assertRaises(SystemExit) as cm:
                    D.edition(text, public=public)
                self.assertIn(bad.split("#")[0], str(cm.exception), (bad, public))

    @unittest.skipUnless(os.path.exists(RECORD), "the divergences record is private")
    def test_every_link_in_the_record_resolves(self):
        with io.open(RECORD, encoding="utf-8") as fh:
            text = fh.read()
        links = how_links(text.split("\n## For the project's own record\n")[0])
        self.assertGreater(len({w for _t, w in links}), 60)
        for target, what in links:
            path, _hash, anchor = target.partition("#")
            full = os.path.normpath(os.path.join(RECORD_DIR, path))
            self.assertTrue(os.path.isfile(full), (what, target))
            self.assertTrue(anchor, (what, target))
            with io.open(full, encoding="utf-8") as fh:
                self.assertIn(anchor, D.heading_anchors(fh.read()), (what, target))

    @unittest.skipUnless(os.path.exists(RECORD), "the divergences record is private")
    def test_the_print_edition_has_no_column_and_no_doc_link(self):
        with io.open(RECORD, encoding="utf-8") as fh:
            prn = D.edition(fh.read())
        self.assertNotIn("How it works", prn)
        self.assertNotRegex(prn, r"\]\([^)]*\.md(#[^)]*)?\)")

    @unittest.skipUnless(os.path.exists(RECORD), "the divergences record is private")
    def test_the_public_edition_has_it_before_decision_resolving_from_docs(self):
        with io.open(RECORD, encoding="utf-8") as fh:
            pub = D.edition(fh.read(), public=True)
        heads = [l for l in pub.split("\n") if l.startswith("| What | Ordbokene.no today |")]
        self.assertEqual(len(heads), 7)
        for h in heads:
            self.assertTrue(h.endswith("| Of use to ordbokene? | How it works | Decision |"), h)
        links = how_links(pub)
        self.assertGreater(len(links), 60)
        for target, what in links:
            path, _hash, anchor = target.partition("#")
            exported = posixpath.normpath(posixpath.join("docs", path))
            self.assertFalse(exported.startswith(".."), (what, target))
            full = private_path(exported)
            self.assertTrue(os.path.isfile(full), (what, target, full))
            with io.open(full, encoding="utf-8") as fh:
                self.assertIn(anchor, D.heading_anchors(fh.read()), (what, target))

    # A reference to an entry the public log does not have (an entry cut from it on purpose) would
    # be a dead link on GitHub: the public edition leaves it out of the cell, with its prefix and
    # its parenthesis of dates, says so on stderr, and stops when nothing would be left of the
    # cell. 999 stands for such an entry.
    B_ROW = "| [12][d12] (2026-09-05) |"

    def public_b_row(self, cell):
        """The public edition of SAMPLE_HOW with row B's Decision cell ``cell``: its B row's
        Decision cell and what went to stderr."""
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            pub = D.edition(SAMPLE_HOW.replace(self.B_ROW, "| %s |" % cell), public=True)
        row = [l for l in pub.split("\n") if l.startswith("| B |")][0]
        return D.cells(row)[6].strip(), err.getvalue()

    def test_the_public_log_is_found(self):
        path = D.public_log()
        self.assertTrue(path and os.path.isfile(path), path)
        ids = D.public_ids(path)
        self.assertIn("184", ids)
        self.assertNotIn("999", ids)

    def test_a_reference_the_log_lacks_is_left_out(self):
        for cell, want in (
                # after a "; ", with a prefix of words and its parenthesis (the real cell's shape)
                ("[12][d12] (2026-09-05); the Norwegian interface [999][d999] (2026-10-24)",
                 "[12](decisions.md#d12) (2026-09-05)"),
                # first, its parenthesis holding a "; " of its own
                ('[999][d999] (2026-10-24; the "?" removed 2026-11-02); [12][d12] (2026-09-05)',
                 "[12](decisions.md#d12) (2026-09-05)"),
                # in the middle, with no parenthesis
                ("[12][d12] (2026-09-05); [999][d999]; [59][d59] (2026-10-19)",
                 "[12](decisions.md#d12) (2026-09-05); [59](decisions.md#d59) (2026-10-19)"),
                # one of two sharing a parenthesis: the parenthesis stays with the other
                ("[12][d12], [999][d999] (2026-10-22)", "[12](decisions.md#d12) (2026-10-22)"),
                ("[999][d999], [12][d12] (2026-10-22)", "[12](decisions.md#d12) (2026-10-22)")):
            got, err = self.public_b_row(cell)
            self.assertEqual(got, want, cell)
            self.assertEqual(err, 'left out of the public edition: 999 (row "B")\n', cell)

    def test_a_cell_left_with_no_reference_stops(self):
        for cell in ("[999][d999] (2026-10-24)", "the heading [999][d999]; [998][d998] (2026-10-25)"):
            with self.assertRaises(SystemExit) as cm:
                self.public_b_row(cell)
            self.assertIn('"B"', str(cm.exception), cell)

    def test_the_print_edition_is_unchanged(self):
        # the print edition cuts the column whole: a reference the log lacks changes nothing there
        text = SAMPLE_HOW.replace(self.B_ROW, "| [12][d12] (2026-09-05); [999][d999] (2026-10-24) |")
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            self.assertEqual(D.edition(text), D.edition(SAMPLE_HOW))
        self.assertEqual(err.getvalue(), "")

    @unittest.skipUnless(os.path.exists(RECORD), "the divergences record is private")
    def test_every_decision_link_of_the_record_lands_in_the_public_log(self):
        ids = D.public_ids(D.public_log())
        err = io.StringIO()
        with io.open(RECORD, encoding="utf-8") as fh, mock.patch.object(sys, "stderr", err):
            pub = D.edition(fh.read(), public=True)
        cited = re.findall(r"\]\(decisions\.md#d(\d+[a-z]?)\)", pub)
        self.assertGreater(len(cited), 50)
        self.assertEqual(sorted({n for n in cited if n not in ids}), [])


class Fetch(unittest.TestCase):

    def run_py(self, code, **env):
        e = dict(os.environ, **env)
        for k in ("ORDBOK_DATA_DIR", "ORDBOK_TLS_NO_VERIFY"):
            if k not in env:
                e.pop(k, None)
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    CODE = ("import sys, ssl; sys.path.insert(0, 'scripts'); import fetch; "
            "print(fetch._SSL.verify_mode == ssl.CERT_REQUIRED, fetch._SSL.check_hostname, "
            "fetch.SOURCES, fetch.REVIEW, fetch.LIBRARY_PATH, sep='|')")

    def test_defaults(self):
        verify, host, sources, review, lib = self.run_py(self.CODE).split("|")
        self.assertEqual((verify, host), ("True", "True"))
        self.assertEqual(os.path.normcase(sources), os.path.normcase(os.path.join(ROOT, "sources")))
        self.assertEqual(os.path.normcase(review), os.path.normcase(os.path.join(ROOT, "review")))
        self.assertEqual(os.path.normcase(lib), os.path.normcase(os.path.join(ROOT, "articles.jsonl")))

    def test_overrides(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        verify, host, sources, review, lib = self.run_py(
            self.CODE, ORDBOK_TLS_NO_VERIFY="1", ORDBOK_DATA_DIR=tmp).split("|")
        self.assertEqual((verify, host), ("False", "False"))
        self.assertEqual(os.path.normcase(sources), os.path.normcase(os.path.join(tmp, "sources")))
        self.assertEqual(os.path.normcase(review), os.path.normcase(os.path.join(tmp, "review")))
        self.assertEqual(os.path.normcase(lib), os.path.normcase(os.path.join(tmp, "articles.jsonl")))

    def test_site_readers_follow_the_override(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        code = ("import sys; sys.path.insert(0, '.'); from ordpar.sitegen import lemma_order, overlay; "
                "print(lemma_order.LOG, overlay.PATH, sep='|')")
        log, corr = self.run_py(code, ORDBOK_DATA_DIR=tmp).split("|")
        self.assertEqual(os.path.normcase(log), os.path.normcase(os.path.join(tmp, "review", "source-normalizations.jsonl")))
        self.assertEqual(os.path.normcase(corr), os.path.normcase(os.path.join(tmp, "review", "mirror-corrections.jsonl")))


class DeployAcrossDrives(unittest.TestCase):
    """Found by the export's test run (2026-11-12): with the checkout on E: and the tests' scratch
    folders on C:, `deploy.run_tests` crashed in `os.path.relpath`, failing deploy 103/109/166."""

    def test_shown_falls_back_to_the_absolute_path(self):
        import deploy
        real = os.path.relpath

        def across(path, start=None):
            raise ValueError("path is on mount 'C:', start on mount 'E:'")
        with mock.patch.object(deploy.os.path, "relpath", across):
            got = deploy.shown(os.path.join(tempfile.gettempdir(), "t", "test_x.py"))
        self.assertTrue(os.path.isabs(got), got)
        self.assertNotIn("\\", got)
        self.assertEqual(deploy.shown(os.path.join(ROOT, "ordpar", "x.py")), "ordpar/x.py")
        self.assertIs(os.path.relpath, real)


class Projections(unittest.TestCase):

    def test_strip_summary(self):
        """Decisions 184 (Robin, 2026-11-13): of a row's `summary` only the gloss and its senses go
        out; the learner notes (`note`, `trap`) and the flashcards' `cue` and `ex` stay private."""
        row = {"id": 1, "summary": {"gloss": ["a"], "gloss_senses": [[1]], "note": ["n"], "trap": ["t"],
                                    "cue": None, "ex": {"no": "x"}}}
        self.assertEqual(X.strip_summary(row), 4)
        self.assertEqual(row["summary"], {"gloss": ["a"], "gloss_senses": [[1]]})
        self.assertEqual(X.strip_summary({"id": 2}), 0)
        self.assertEqual(X.strip_summary({"id": 3, "summary": None}), 0)

    def test_the_exported_library_carries_no_learner_note(self):
        """In the public repository (and in a staged export) no row's summary holds a key beyond
        `SUMMARY_KEYS`."""
        lib = os.path.join(ROOT, "data", "articles.jsonl")
        if not (IN_EXPORT and os.path.exists(lib)):
            self.skipTest("the exported library is checked in the export")
        bad = []
        with io.open(lib, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    s = r.get("summary")
                    if isinstance(s, dict) and set(s) - set(X.SUMMARY_KEYS):
                        bad.append(r["id"])
        self.assertEqual(bad[:5], [])

    def test_strip_added(self):
        row = {"id": 1, "senses": [
            {"ex_added": [{"no": "a", "verification": {"x": 1}, "claim_check": {"note": "n", "status": "ok"}}],
             "subs": [{"ex_added": [{"no": "b", "verification": {}}]}]}]}
        self.assertEqual(X.strip_added(row), 2)
        self.assertEqual(row["senses"][0]["ex_added"][0], {"no": "a", "claim_check": {"status": "ok"}})
        self.assertEqual(row["senses"][0]["subs"][0]["ex_added"][0], {"no": "b"})

    def test_small_files(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        norm = os.path.join(tmp, "n.jsonl")
        with open(norm, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"article": 5, "kind": "lemma-order", "where": "top-level lemmas", "after": "x",
                                 "reporter": "someone", "approved_by": "someone", "why": "w"}) + "\n")
        self.assertEqual(json.loads(X.normalizations(norm)),
                         {"article": 5, "kind": "lemma-order", "where": "top-level lemmas", "after": "x"})
        dd = os.path.join(tmp, "d.jsonl")
        with open(dd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"citer": 1, "target": 2, "defn": 3, "note": "n", "date": "d"}) + "\n")
        self.assertEqual(json.loads(X.dangling_def(dd)), {"citer": 1, "target": 2, "defn": 3})
        dg = os.path.join(tmp, "d.json")
        with open(dg, "w", encoding="utf-8") as fh:
            json.dump([{"id": 1, "reason": "r"}, {"id": 2, "reason": "r", "assessed": "a note", "date": "d"}], fh)
        self.assertEqual(json.loads(X.dangling(dg)), [{"id": 1}, {"id": 2, "assessed": True}])


class RewrittenDocs(unittest.TestCase):
    """The technical docs rewritten in place, their history in a private `-rationale.md` beside
    each (decisions 184), and their links into the private log pointed at the public one."""

    def test_a_rationale_file_never_leaves(self):
        self.assertTrue(X.is_rationale("ordpar/docs/build-site-rationale.md"))
        self.assertFalse(X.is_rationale("ordpar/docs/build-site.md"))
        self.assertFalse([p for p in export_set() if p.endswith("-rationale.md")])
        g = X.Guard(release=False)
        g.path("ordpar/docs/build-site-rationale.md")
        self.assertTrue(g.refusals)

    def test_links_into_the_private_log_point_at_the_public_one(self):
        src = ("[126](dictionary-site-decisions.md#d126) and [d63]: dictionary-site-decisions.md#d63; "
               "[x](docs/dictionary-site-decisions.md#d1)").encode("utf-8")
        out = X.public_md("ordpar/docs/build-site.md", src).decode("utf-8")
        self.assertEqual(out, "[126](../../docs/decisions.md#d126) and [d63]: ../../docs/decisions.md#d63; "
                              "[x](../../docs/decisions.md#d1)")
        self.assertIn("](../docs/decisions.md#d1)",
                      X.public_md("ordpar/README.md", b"[1](docs/dictionary-site-decisions.md#d1)").decode())
        self.assertEqual(X.public_md("ordpar/site/x.js", src), src)

    @unittest.skipUnless(os.path.isdir(os.path.join(ROOT, "handover", "checks", "agent-review"))
                         and os.path.isdir(os.path.join(ORDPAR, "public")),
                         "check 7's agent review is not in this checkout, or this is the public "
                         "repository, where the export set is not made")
    def test_check_7s_agent_review_is_taken_from_this_branch(self):
        files = export_set()
        for name in ("README.md", "check7-reader.md", "agent_review.py", "test_agent_review.py"):
            self.assertIn("handover/checks/agent-review/" + name, files)


class ReadmeTestCount(unittest.TestCase):
    """The README's sentence on the tests' result ("… 96 test files ran 1,571 tests, of which 156
    were skipped and none failed.") is checked against the export's own run: a release refuses
    when the three numbers differ, or when the sentence is missing; a draft only warns
    (`export_public.readme_counts`, `readme_count_fault`)."""

    TEXT = ("As a guide: in a fresh copy of this repository on Windows, before any build and without the\n"
            "browser tests, 96 test files ran 1,571 tests, of which 156 were skipped and none failed.\n")

    def test_the_sentence_is_read(self):
        self.assertEqual(X.readme_counts(self.TEXT), (96, 1571, 156))
        self.assertEqual(X.readme_counts("1 test file ran 1 test, of which 0 were skipped"), (1, 1, 0))
        self.assertIsNone(X.readme_counts("The tests ran and none failed."))

    def test_agreeing_numbers_pass(self):
        self.assertIsNone(X.readme_count_fault(self.TEXT, (96, 1571, 156), "ordpar/public/README.md"))

    def test_differing_numbers_are_named_with_the_file(self):
        for run in ((97, 1571, 156), (96, 1580, 156), (96, 1571, 150)):
            fault = X.readme_count_fault(self.TEXT, run, "ordpar/public/README.md")
            self.assertIn("ordpar/public/README.md", fault)
            self.assertIn("96 file(s), 1571 test(s), 156 skipped", fault)
            self.assertIn("%d file(s), %d test(s), %d skipped" % run, fault)

    def test_a_missing_sentence_is_a_fault(self):
        fault = X.readme_count_fault("No such sentence here.\n", (96, 1571, 156), "ordpar/public/README.md")
        self.assertIn("ordpar/public/README.md", fault)
        self.assertIn("test files ran", fault)

    def test_the_public_readme_has_the_sentence(self):
        readme = os.path.join(ROOT, "README.md") if IN_EXPORT else os.path.join(ORDPAR, "public", "README.md")
        with io.open(readme, encoding="utf-8") as fh:
            self.assertIsNotNone(X.readme_counts(fh.read()))

    def test_a_release_refuses_and_a_draft_warns(self):
        bad = (97, 1571, 156)
        with self.assertRaises(X.Refused) as cm:
            X.check_readme_counts(self.TEXT, bad, release=True)
        self.assertIn("refused", str(cm.exception))
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            X.check_readme_counts(self.TEXT, bad, release=False)
            X.check_readme_counts(self.TEXT, (96, 1571, 156), release=True)
        self.assertEqual(out.getvalue().count("warning: "), 1, out.getvalue())
        with self.assertRaises(X.Refused):
            X.check_readme_counts("No such sentence.\n", (96, 1571, 156), release=True)

    def test_the_export_checks_after_its_test_run(self):
        # in main(), after the tests have run; and the help says so
        src = inspect.getsource(X.main)
        self.assertLess(src.index("run_tests(stage"), src.index("check_readme_counts("))
        self.assertIn("README", X.__doc__[X.__doc__.index("Then the tests run"):])


class PrivateImports(unittest.TestCase):
    """A test file that imports a module the export leaves out skips, with a reason naming the
    module, in a folder laid out as the public repository is (the export set, nothing else); and
    the export's own test run runs it rather than leaving it out."""

    def private_tests(self):
        files = export_set()
        tests = [f for f in files if f.startswith("ordpar/tests/test_") and f.endswith(".py")]
        _missing, _lazy, private = X.closure_check(tests, set(files), ROOT)
        return private

    def test_found_here(self):
        if not os.path.exists(os.path.join(ROOT, "scripts", "reports_page.py")):
            self.skipTest("the private modules are not in this checkout: nothing imports one")
        self.assertIn("ordpar/tests/test_ordpar_copy166.py", self.private_tests())

    def test_they_skip_where_the_module_is_absent(self):
        private = self.private_tests()
        if not private:
            self.skipTest("no test here imports a module the export leaves out")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in export_set():
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, rel), dst)
        env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                   ORDBOK_DATA_DIR=os.path.join(tmp, "data"))
        for k in ("ORDPAR_TEST_OUT", "ORDPAR_TEST_BASE", "ORDPAR_MIRROR_DIR"):
            env.pop(k, None)
        for rel, mods in sorted(private.items()):
            r = subprocess.run([sys.executable, os.path.join(tmp, rel), "-v"], cwd=tmp, env=env,
                               capture_output=True, timeout=600)
            err = r.stderr.decode("utf-8", "replace")
            lines = [ln for ln in err.strip().splitlines() if ln.strip()]
            self.assertEqual(r.returncode, 0, "%s:\n%s" % (rel, err[-1500:]))
            self.assertRegex(lines[-1] if lines else "", r"^OK \(skipped=\d+\)$", rel)
            for m in mods:
                name = os.path.splitext(os.path.basename(m))[0]
                self.assertRegex(err, r"skipped '[^'\n]*\b%s\b" % name, "%s: no skip names %s" % (rel, name))

    def test_the_export_runs_them(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "ordpar", "tests"))
        with open(os.path.join(tmp, "ordpar", "tests", "test_p.py"), "w", encoding="utf-8") as fh:
            fh.write("import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n\n\n"
                     "T = unittest.skip('needs private_mod')(T)\nunittest.main()\n")
        results, excluded = X.run_tests(tmp, {"ordpar/tests/test_p.py": ["scripts/private_mod.py"]}, 1)
        self.assertEqual(excluded, {})
        self.assertEqual([(r[0], r[1], r[2], r[3]) for r in results], [("ordpar/tests/test_p.py", 0, 1, 1)])


class GitAttributes(unittest.TestCase):
    """The public repository's root `.gitattributes` marks everything under data/ `-text`, so a
    Windows clone with `core.autocrlf` keeps the data's bytes, and every other text file
    `text=auto eol=lf`, so a clone's scripts and stylesheets hash as ordpar.no's do. Here it is a public text
    (`ordpar/public/.gitattributes`, listed in `texts.json` with no sources), which the export
    writes at the root; in the public repository it is the root's own."""

    def source(self):
        here = os.path.join(ORDPAR, "public", ".gitattributes")
        return here if os.path.isdir(os.path.join(ORDPAR, "public")) else os.path.join(ROOT, ".gitattributes")

    def test_a_public_text_with_no_sources(self):
        if not os.path.isdir(os.path.join(ORDPAR, "public")):
            self.skipTest("the public repository has no ordpar/public/: its .gitattributes is the root's")
        hit = [t for t in X.read_texts() if t["path"] == ".gitattributes"]
        self.assertEqual(hit, [{"path": ".gitattributes", "sources": {}}])
        self.assertIn((".gitattributes", "ok", ""), X.check_texts(hit))

    def test_git_reads_data_as_not_text(self):
        src = self.source()
        self.assertTrue(os.path.exists(src), src)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copyfile(src, os.path.join(tmp, ".gitattributes"))
        subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True)
        paths = ["data/articles.jsonl", "data/bokmalsordboka/bm-articles.part-001.jsonl",
                 "data/bokmalsordboka/corrected/fixes.jsonl", "data/frequency/" + X.FREQ_NAME]
        code = ["ordpar/build_site.py", "ordpar/site/ordpar.css", "ordpar/site/lookup.js"]
        out = subprocess.run(["git", "check-attr", "text", "eol", "--"] + paths + code,
                             cwd=tmp, check=True, capture_output=True, text=True).stdout
        for p in paths:
            self.assertIn("%s: text: unset\n" % p, out)
        for p in code:                     # checked out with LF everywhere, so the `?v=` hashes match
            self.assertIn("%s: text: auto\n" % p, out)
            self.assertIn("%s: eol: lf\n" % p, out)


class OfflineHelp(unittest.TestCase):
    """`build_offline.py --help` names every shell page the code packs (`SHELL_PAGES`) and every
    optional one (`OPTIONAL_PAGES`)."""

    SCRIPT = os.path.join(ORDPAR, "build_offline.py")

    def test_every_shell_page_in_the_help(self):
        from ordpar import build_offline
        r = subprocess.run([sys.executable, self.SCRIPT, "--help"], capture_output=True, timeout=60,
                           env=dict(os.environ, PYTHONUTF8="1"))
        self.assertEqual(r.returncode, 0)
        out = r.stdout.decode("utf-8", "replace")
        for page in list(build_offline.SHELL_PAGES) + list(build_offline.OPTIONAL_PAGES):
            self.assertTrue(re.search(r"(?<![^\s`(,])%s(?![^\s`),])" % re.escape(page), out),
                            "%s is not in build_offline.py --help" % page)


class PublicTextFrom(unittest.TestCase):
    """A public text's optional `"from"`: the file under `ordpar/public/` it is stored as, when
    that differs from where the export writes it (`"path"`). The assistant guide is the case: a
    `CLAUDE.md` in a folder of the private repository could be loaded by Claude Code working
    there, so it is stored as `ordpar/public/CLAUDE.public.md` and exported as `CLAUDE.md`."""

    def test_written_at_its_path_from_its_file(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        public, stage = os.path.join(tmp, "public"), os.path.join(tmp, "stage")
        os.makedirs(os.path.join(public, "docs"))
        for name, body in (("GUIDE.public.md", b"the guide\n"), ("README.md", b"the readme\n")):
            with open(os.path.join(public, name), "wb") as fh:
                fh.write(body)
        texts = [{"path": "GUIDE.md", "from": "GUIDE.public.md", "sources": {}},
                 {"path": "README.md", "sources": {}},
                 {"path": "docs/missing.md", "from": "missing.public.md", "sources": {}}]
        with mock.patch.object(X, "PUBLIC_DIR", public):
            states = X.public_texts(stage, texts)
        self.assertEqual(states, [("GUIDE.md", "ok", ""), ("README.md", "ok", ""),
                                  ("docs/missing.md", "missing", "no %s yet" % X.shown(
                                      os.path.join(public, "missing.public.md")))])
        self.assertEqual(sorted(X.walk(stage)), ["GUIDE.md", "README.md"])
        with open(os.path.join(stage, "GUIDE.md"), "rb") as fh:
            self.assertEqual(fh.read(), b"the guide\n")

    def test_the_assistant_guide_goes_out_as_claude_md(self):
        if not os.path.isdir(os.path.join(ORDPAR, "public")):
            self.skipTest("the public repository has no ordpar/public/: its CLAUDE.md is the root's")
        hit = [t for t in X.read_texts() if t["path"] == "CLAUDE.md"]
        self.assertEqual(hit, [{"path": "CLAUDE.md", "from": "CLAUDE.public.md", "sources": {}}])
        self.assertFalse(os.path.exists(os.path.join(ORDPAR, "public", "CLAUDE.md")))
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.assertEqual(X.public_texts(tmp, hit), [("CLAUDE.md", "ok", "")])
        self.assertEqual(X.walk(tmp), ["CLAUDE.md"])
        with open(os.path.join(tmp, "CLAUDE.md"), "rb") as a, \
                open(os.path.join(ORDPAR, "public", "CLAUDE.public.md"), "rb") as b:
            self.assertEqual(a.read(), b.read())


def exported_markdown():
    """``(present, markdown)``: every path the export holds, and ``{path: bytes}`` for each of its
    Markdown files as exported. In the private repository, from the manifest (the files under
    ordpar/ through `public_md`, `PIPELINE`, `main_files()`, the public texts, the public edition
    of the divergences record, and the names under data/ that the manifest writes); in the public
    repository, the folder itself."""
    if IN_EXPORT:
        present, md = set(), {}
        tracked = tracked_files()      # a reader's own files are not the export's (finding 19)
        for dp, dn, fn in os.walk(ROOT):
            dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/")
                if tracked is not None and rel not in tracked:
                    continue
                present.add(rel)
                if rel.endswith(".md") and not rel.startswith(X.THEIR_DATA):
                    with open(os.path.join(ROOT, rel), "rb") as fh:
                        md[rel] = fh.read()
        return present, md
    md = {}
    for rel in export_set():
        if rel.endswith(".md"):
            with open(os.path.join(ROOT, rel), "rb") as fh:
                md[rel] = X.public_md(rel, fh.read())
    present = set(export_set())
    try:
        main = X.main_files()
    except SystemExit:
        main = []
    for rel in main:
        present.add(rel)
        if rel.endswith(".md"):
            md[rel] = X.git("show", "%s:%s" % (X.MAIN_BRANCH, rel), binary=True)
    for t in X.read_texts():          # a text not yet written is the release's other refusal
        present.add(t["path"])
        if t["path"].endswith(".md") and os.path.exists(X.text_source(t)):
            with open(X.text_source(t), "rb") as fh:
                md[t["path"]] = fh.read()
    with io.open(os.path.join(ROOT, X.DIVERGENCES_SRC), encoding="utf-8") as fh:
        md[X.DIVERGENCES_OUT] = D.edition(fh.read(), public=True).encode("utf-8")
    present |= {X.DIVERGENCES_OUT, ".gitignore", "EXPORT.json"}
    # data/, as the manifest writes it (the parts' names follow the ids, so the folders stand for them)
    present |= {X.LIBRARY, gate.marker_path(X.LIBRARY), X.FREQ_OUT}
    present |= {dst for dst, _how in X.SMALL.values()}
    present |= {X.MIRROR_OUT + "/" + n for n in X.MIRROR_FILES}
    present |= {X.MIRROR_OUT + "/" + d + "/" for d in X.MIRROR_DIRS}
    present |= {X.CORRECTED_OUT + "/normalization-patches.jsonl", X.CORRECTED_OUT + "/fixes.jsonl"}
    try:
        caps = [p for p in X.git("ls-files", "-z", X.CAPTURES).split("\0") if p]
    except SystemExit:
        caps = []
    present |= {X.CAPTURES_OUT + p[len(X.CAPTURES):] for p in caps}
    return present, md


class TextFromMain(unittest.TestCase):
    """A public text may stand in for a file the export reads from branch `main` (decisions 184,
    the outsider test's findings 4, 5 and 16: the checks' README). Its source is written
    `main:<path>` in `texts.json` and hashed from `git show`, so a change on `main` makes the
    text stale, which a release refuses, until it is read again and stamped; and the export
    writes the public text over `main`'s file, since the public texts are written after it."""

    MAIN_FILE = b"# The checks\r\n\r\nThe licence is still to be added.\r\n"

    def fake_git(self, data):
        real = X.git

        def git(*args, **kw):
            if args[:1] == ("show",) and args[1] == "main:handover/checks/README.md":
                return data
            return real(*args, **kw)
        return git

    def texts(self, h):
        return [{"path": "handover/checks/README.md",
                 "sources": {"main:handover/checks/README.md": h}}]

    def test_hashed_from_main(self):
        h = hashlib.sha256(self.MAIN_FILE.replace(b"\r\n", b"\n")).hexdigest()
        with mock.patch.object(X, "git", side_effect=self.fake_git(self.MAIN_FILE)):
            self.assertEqual(X.source_hash("main:handover/checks/README.md"), h)
            states = X.check_texts(self.texts(h))
            self.assertEqual([s[1] for s in states], ["ok"] if os.path.exists(
                os.path.join(X.PUBLIC_DIR, "handover", "checks", "README.md")) else ["missing"])
        changed = self.MAIN_FILE + b"A new line on main.\n"
        with mock.patch.object(X, "git", side_effect=self.fake_git(changed)):
            states = X.check_texts(self.texts(h))
        if states[0][1] != "missing":
            self.assertEqual(states[0][1], "stale")
            self.assertIn("main:handover/checks/README.md changed", states[0][2])

    @unittest.skipUnless(os.path.exists(os.path.join(ORDPAR, "docs", "divergences.md")),
                         "the divergences record is not in the public repository")
    def test_a_local_source_is_hashed_as_before(self):
        self.assertEqual(X.source_hash(X.DIVERGENCES_SRC),
                         X.file_hash(os.path.join(X.ROOT, X.DIVERGENCES_SRC)))
        self.assertIsNone(X.source_hash("ordpar/docs/no-such-file.md"))

    def test_the_public_text_is_written_over_mains_file(self):
        stage = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, stage, True)
        public = os.path.join(stage, "_public")
        os.makedirs(os.path.join(public, "handover", "checks"))
        with open(os.path.join(public, "handover", "checks", "README.md"), "wb") as fh:
            fh.write(b"the public version\n")
        X.write(os.path.join(stage, "out", "handover", "checks", "README.md"), self.MAIN_FILE)
        with mock.patch.object(X, "PUBLIC_DIR", public):
            X.public_texts(os.path.join(stage, "out"), self.texts(None))
        with open(os.path.join(stage, "out", "handover", "checks", "README.md"), "rb") as fh:
            self.assertEqual(fh.read(), b"the public version\n")
        # and build_stage writes the public texts after main's files
        src = inspect.getsource(X.build_stage)
        self.assertLess(src.index("main_files()"), src.index("public_texts("))

    @unittest.skipIf(IN_EXPORT, "the public repository has no ordpar/public/ and no branch main")
    def test_the_checks_readme_is_a_stamped_public_text(self):
        hit = [t for t in X.read_texts() if t["path"] == "handover/checks/README.md"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(list(hit[0]["sources"]), ["main:handover/checks/README.md"])
        state = X.check_texts(hit)[0]
        self.assertEqual(state[1], "ok", state)


class LocalByDesign(unittest.TestCase):
    """A backticked path a reader of the public repository has but the repository does not carry
    (`LOCAL_BY_DESIGN`: the build's output, the reader's paths file, the joined articles file, the
    reader's own Claude Code agents) passes the release guard; any other path that does not
    resolve still refuses; and the real exported Markdown files carry no path the guard refuses
    (2026-11-13: 14 did, in tests.md, build-site.md, inflection-table.md, offline-app.md and check
    7's agent review)."""

    def links(self, text, rel="ordpar/docs/x.md", present=("ordpar/a.py",), release=True):
        g = X.Guard(release)
        dirs = {os.path.dirname(p) for p in present}
        g.links(rel, text.encode("utf-8"), lambda p: p.strip("/") in set(present) | dirs)
        return [r for r in g.refusals if r[2] == "path"]

    def test_each_listed_path_passes(self):
        self.assertTrue(X.LOCAL_BY_DESIGN)
        for p in X.LOCAL_BY_DESIGN:
            self.assertEqual(self.links("see `%s`\n" % p), [], p)
            if p.endswith("/"):
                self.assertEqual(self.links("see `%sdeep/page.html`\n" % p), [], p)

    def test_anything_else_still_refuses(self):
        for p in ("ordpar/missing.py", "ordpar/outline.md", "ordpar/output/x.html", "ordpar/local-paths.jsonl",
                  "data/bokmalsordboka/bm-articles.jsonl.bak", ".claude/settings.json", "ordpar/a.py/x.txt"):
            self.assertEqual([r[3] for r in self.links("see `%s`\n" % p)], [p], p)
        self.assertEqual(self.links("see `ordpar/a.py`\n"), [])

    def test_the_exported_markdown_has_no_unresolved_path(self):
        present, md = exported_markdown()
        self.assertGreater(len(md), 20)
        dirs = {os.path.dirname(p.rstrip("/")) for p in present} | {p.rstrip("/") for p in present if p.endswith("/")}
        while True:
            more = {os.path.dirname(d) for d in dirs} - dirs
            if not more:
                break
            dirs |= more
        files = {p for p in present if not p.endswith("/")}

        def exists(p):
            p = p.strip("/")
            return p in files or p in dirs or p == "."
        g = X.Guard(release=True)
        for rel, data in sorted(md.items()):
            g.links(rel, data, exists)
        found = [r for r in g.refusals if r[2] == "path"]
        self.assertEqual(found, [], "\n".join("%s:%s: %s" % (r[0], r[1], r[3]) for r in found))


if __name__ == "__main__":
    unittest.main()
