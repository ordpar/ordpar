#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Make the folder of Ordpar's public repository from the private one (decisions 184).

Ordpar's site (https://ordpar.no) is built in a private repository that also holds the pipeline
that writes the English. Its public repository, github.com/ordpar/ordpar, carries the part that
builds the site and the data the build reads, so that anyone can build the whole site from it.
This script makes that folder. It runs in the private repository, which has things the public one
has not (the example gate's rule, the private paths in ordpar/local-paths.json); in the public
repository it is kept as the record of how the folder was made.

    python ordpar/export_public.py --draft                 # make it; missing texts only warn
    python ordpar/export_public.py                         # release: anything missing refuses
    python ordpar/export_public.py --target DIR --draft    # somewhere else
    python ordpar/export_public.py --guard DIR             # run the guard alone over a folder
    python ordpar/export_public.py --stamp docs/decisions.md   # a public text is up to date

What goes in (the MANIFEST below, nothing else):

* **code and tests**: every file git tracks under ordpar/ except the three working docs (the site
  plan, its decision log, the ideas list; they go out later as rewritten texts), the divergences
  record (it goes out as its public edition, below) and ordpar/out/;
  `ordbok_gen.py` and the nine pipeline modules the site imports (`PIPELINE`; the export refuses
  when the site imports another at module level); and, read from branch `main` by `git show`,
  `handover/checks/` (the checks behind the corrections sent to ordbokene) with its test. The
  private layout is kept, so no import changes;
* **data/** (`ORDBOK_DATA_DIR=data` points the build at it): the library `articles.jsonl` with the
  example gate applied and the added sentences' `verification` and `claim_check.note` left out,
  and its gate marker (`ordpar/sitegen/gate.py`); Bokmålsordboka's data as UiB's API serves it,
  in `data/bokmalsordboka/`, its articles file in parts under 50 MB cut by article id, which
  `python ordpar/data_parts.py join` puts back together, and beside it, in
  `data/bokmalsordboka/corrected/`, **the corrected copy**: the same articles in the same parts
  with every fix of ours applied (decisions 184, "Yes, corrected copy"; `ordpar/corrected_copy.py`:
  the handover's mirror corrections and the normalization log made into patches, both through
  `sitegen/overlay.py`), its `normalization-patches.jsonl` and `fixes.jsonl`, every row of both
  files with its verdict per article, the ones not applied included; the National Library's word counts
  (CC0) for the forms the search index asks for; the deck's committed article captures, which
  the build reads for cross-references; and the small files the build reads, projected to the
  fields it reads;
* **public texts**: those listed in `ordpar/public/texts.json`, each with the hashes of the
  private sources it was written from (`--stamp` records them; a text's `from` names its file
  when that differs from where it goes, as the assistant guide `CLAUDE.public.md` goes out as
  `CLAUDE.md`; a source written `main:<path>` is read from branch `main`, and a text written at
  a path the export also reads from `main` replaces that file, as the checks' public README
  replaces theirs), and `docs/divergences.md`,
  made from ordpar/docs/divergences.md by `ordpar/divergences_print.py --public`.

**The guard** reads every file before anything is written to the target and refuses, naming the
file and the line, on a mail address outside the allow-list (`ALLOWED_MAIL`; in Bokmålsordboka's
data an address is counted, not refused), a private path, a key- or token-shaped string, or a
working doc or session file in the export. In release mode it also refuses a "decisions N" cited
in the exported code with no entry in the public log, a relative link or a backticked repository
path in an exported Markdown file that does not resolve inside the export (except the few paths
a reader has but the repository does not carry, `LOCAL_BY_DESIGN`: the build's output, the
reader's paths file, the joined articles file, the reader's Claude Code agents), a missing public text,
and one whose sources changed since it was written; with `--draft` these warn.

**Byte-stable**: the same input gives the same bytes, nothing carries a date, and a file is
written only when its bytes change; files the manifest no longer names are removed (never
`.git/`). `EXPORT.json` records what was read: for each source repository the last commit that
touched what was exported, so a week with no change gives the same file.

Then the tests run inside a copy of it, with `ORDBOK_DATA_DIR` set to its data/, all but the
browser tests: a test file that imports a module the export leaves out runs too, its tests that
need the module skipped with a reason naming it, and is listed with its counts. The counts run,
skipped and excluded are printed, by reason (`--no-tests` skips them).

Paths: the target, the mirror and the 1-gram file come from the flags, else from
ordpar/local-paths.json (`ordpar/local_paths.py`). Standard library only.
"""
import argparse
import ast
import concurrent.futures
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import local_paths  # noqa: E402
import data_parts   # noqa: E402

# --------------------------------------------------------------------------------- the manifest

#: the working docs: private now, published later as rewritten texts (decisions 184); the
#: divergences record goes out only as its public edition, docs/divergences.md (Robin, 2026-11-12)
WORKING_DOCS = ("ordpar/docs/dictionary-site.md", "ordpar/docs/dictionary-site-decisions.md",
                "ordpar/docs/ideas.md", "ordpar/docs/divergences.md")
#: never exported, whatever else says so
NEVER = ("ordpar/out/", "ordpar/.build/", "ordpar/local-paths.json", "ordpar/public/")
#: the deck renderer and the pipeline modules the site imports (decisions 184: nine modules)
PIPELINE = ("ordbok_gen.py", "scripts/markup.py", "scripts/mini.py", "scripts/derive.py",
            "scripts/fetch.py", "scripts/coverage.py", "scripts/postags.py", "scripts/store.py",
            "scripts/headwords.py")
#: read from branch `main`: the check scripts and their test
MAIN_BRANCH = "main"
MAIN_PATHS = ("handover/checks/", "tests/test_handover_checks.py")
#: taken from this branch beside ordpar/: check 7's agent review, written for the public repository
#: (decisions 184), which joins the check scripts read from `main`
LOCAL_PATHS = ("handover/checks/agent-review",)
#: the mirror's files the build opens (traced 2026-11-12: build_site.py --all, build_index.py);
#: `bm-articles.jsonl` goes in parts, the folders' files whole
MIRROR_FILES = ("bm-listed.jsonl", "bm-unlisted.json", "bm-concepts.json", "manifest.json")
MIRROR_DIRS = ("bm/404",)
FREQ_NAME = "nb-2026-books-nob-1990_freq.frk"
#: where each part of the data goes in the public folder
DATA = "data"
LIBRARY = DATA + "/articles.jsonl"
MIRROR_OUT = DATA + "/bokmalsordboka"
#: the corrected copy (decisions 184): the articles with our fixes applied, the derived patches and
#: the list of fixes with their verdicts (`ordpar/corrected_copy.py`)
CORRECTED_OUT = MIRROR_OUT + "/corrected"
FREQ_OUT = DATA + "/frequency/" + FREQ_NAME
#: the small files: source -> (destination, how). "copy" as it is; a projection keeps only the
#: fields the build reads (the rest is working matter: who reported, who approved, notes)
SMALL = {
    "review/mirror-corrections.jsonl": (DATA + "/review/mirror-corrections.jsonl", "copy"),
    "review/source-normalizations.jsonl": (DATA + "/review/source-normalizations.jsonl",
                                           "normalizations"),
    "review/dangling-def-assessed.jsonl": (DATA + "/review/dangling-def-assessed.jsonl",
                                           "dangling_def"),
    "sources/dangling.json": (DATA + "/sources/dangling.json", "dangling"),
}
#: the deck's committed captures: the build reads them for the targets of cross-references
CAPTURES = "sources/articles/"
CAPTURES_OUT = DATA + "/sources/articles/"
#: the fields of a normalization-log row the site reads (`sitegen/lemma_order.py`,
#: `sitegen/corrections.py`) and the corrected copy's patches are made from (`corrected_copy.py`:
#: `path`, so the public repository can remake them)
NORMALIZATION_FIELDS = ("article", "lemma", "kind", "where", "before", "after", "date", "defect",
                        "ids", "resolved_upstream", "reapplied_from", "path")
TEXTS = os.path.join(HERE, "public", "texts.json")
PUBLIC_DIR = os.path.join(HERE, "public")
#: the public repository's .gitignore: the joined articles file, the build's output, local paths
GITIGNORE = """__pycache__/
*.pyc
data/bokmalsordboka/bm-articles.jsonl
data/bokmalsordboka/corrected/bm-articles.jsonl
ordpar/out/
ordpar/.build/
ordpar/local-paths.json
"""
DIVERGENCES_SRC = "ordpar/docs/divergences.md"
DIVERGENCES_OUT = "docs/divergences.md"
PUBLIC_LOG = "docs/decisions.md"
#: backticked paths a reader of the public repository has but the repository does not carry; the
#: release guard lets a Markdown file name them. An entry ending in "/" is a folder and covers what
#: is under it; any other is one file
LOCAL_BY_DESIGN = (
    # the build's output, made by the reader's own build (.gitignore)
    "ordpar/out/",
    # the reader's own paths file (.gitignore; its example goes out)
    "ordpar/local-paths.json",
    # the articles file the reader joins from its parts, `data_parts.py join` (.gitignore)
    "data/bokmalsordboka/bm-articles.jsonl",
    # a folder of the reader's own Claude Code setup, where check 7's review agent is installed
    ".claude/agents/",
)


def local_by_design(p):
    """Is the backticked path ``p`` one of ``LOCAL_BY_DESIGN``, or under one of its folders?"""
    p = p[2:] if p.startswith("./") else p
    for entry in LOCAL_BY_DESIGN:
        if p == entry or (entry.endswith("/") and (p.rstrip("/") + "/").startswith(entry)):
            return True
    return False

# ------------------------------------------------------------------------------------ the guard

ALLOWED_MAIL = re.compile(r"^(post@ordpar\.no|[^@\s]+@example\.(org|com))$", re.I)
MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
#: a machine's own paths: this project's folders on a drive (the projects' folder, the storage
#: folder), a user folder in any of its spellings (a drive's Users folder, the shell's /c/ form, /home/, /Users/),
#: an AppData path. A drive path elsewhere (`C:/Windows/Fonts`, a test's `E:/x/`) is not private.
#: (Written so that this file does not match its own pattern.)
_SEP = r"(?:\\\\|\\|/)+"
PRIVATE_PATH = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:" + _SEP + r"(?:Claude[ ]Code|Users|Documents and Settings)\b"
    r"|Claude[ ]Code[ ]Storage|(?<![A-Za-z0-9])/[a-z]/(?:Users|Claude[ ]Code)/|/home/[a-z][a-z0-9_-]*/"
    r"|/Users/[A-Z][A-Za-z]+/|AppData" + _SEP, re.I)
#: key- or token-shaped: the shapes services give their keys, and any long run of letters and
#: digits that mixes upper case, lower case and digits (a hash or an id in hex has no upper case)
TOKEN_PREFIX = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
TOKEN_RUN = re.compile(r"(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_-]{32,}(?![A-Za-z0-9+/_-])")
TOKEN_ASSIGN = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|password|passwd|auth[_-]?token|access[_-]?token)\b\s*[:=]\s*[\"']([^\"'\s]{12,})[\"']")
#: values the token check lets through: the local stand-in's dummy token (receiver/tools/local.mjs)
ALLOWED_TOKENS = ("local-reports-token-0000",)
#: "decisions N" in code; other sessions' logs ("audio decisions 26") are not the public log
DECISION_CITE = re.compile(
    r"(?<![\w-])(?<!audio )(?<!provenance )(?<!context-cost )(?:site |site-review )?decisions?"
    r"(?: entry| entries)? (\d+)\b", re.I)
MD_LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK_PATH = re.compile(r"`((?:\.{1,2}/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.*<>-]+)+/?)`")
TEXT_EXT = (".py", ".js", ".mjs", ".css", ".html", ".md", ".json", ".jsonl", ".jsonc", ".tsv",
            ".txt", ".sql", ".sh", ".webmanifest", ".frk", ".gitignore", ".yml", "")
#: Bokmålsordboka's data: an address in it is counted, never refused (it is theirs, as served)
THEIR_DATA = (MIRROR_OUT + "/", CAPTURES_OUT, FREQ_OUT)


class Refused(SystemExit):
    pass


def is_text(rel):
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1].lower()
    return ext in TEXT_EXT or base.startswith(".")


#: an alphabet written out (a base-62 digit table, a test's characters) is not a key
ALPHABETS = ("0123456789", "abcdefghij", "ABCDEFGHIJ")


def mixed(run):
    return (re.search(r"[A-Z]", run) and re.search(r"[a-z]", run) and re.search(r"[0-9]", run)
            and not re.fullmatch(r"[A-Za-z]+[0-9]{0,3}", run)
            and not any(a in run for a in ALPHABETS))


class Guard(object):
    """Collects findings over every exported file; `refusals` stop the export, `warnings` don't."""

    def __init__(self, release):
        self.release = release
        self.refusals, self.warnings = [], []
        self.their_mail = {}
        self.cites = []          # (file, line, number)

    def add(self, hard, rel, line, kind, text):
        (self.refusals if hard else self.warnings).append((rel, line, kind, text.strip()[:140]))

    def path(self, rel):
        if (rel in WORKING_DOCS or is_rationale(rel) or rel.startswith("docs/sessions/")
                or "/docs/sessions/" in rel):
            self.add(True, rel, 0, "working doc", "a working doc or session file is in the export")

    def text(self, rel, data):
        if not is_text(rel):
            return
        try:
            s = data.decode("utf-8")
        except UnicodeDecodeError:
            s = data.decode("latin-1")
        theirs = rel.startswith(THEIR_DATA)
        code = rel.endswith((".py", ".js", ".mjs", ".css", ".html", ".jsonc", ".sql", ".sh"))
        for n, line in enumerate(s.split("\n"), 1):
            if "@" in line:
                for m in MAIL.finditer(line):
                    addr = m.group(0)
                    if ALLOWED_MAIL.match(addr):
                        continue
                    if theirs:
                        self.their_mail[addr.lower()] = self.their_mail.get(addr.lower(), 0) + 1
                    else:
                        self.add(True, rel, n, "mail address", addr)
            if PRIVATE_PATH.search(line):
                self.add(True, rel, n, "private path", PRIVATE_PATH.search(line).group(0) + " … " + line)
            for m in TOKEN_PREFIX.finditer(line):
                self.add(True, rel, n, "key-shaped", m.group(0)[:12] + "…")
            for m in TOKEN_ASSIGN.finditer(line):
                if m.group(1) not in ALLOWED_TOKENS:
                    self.add(True, rel, n, "token-shaped", m.group(0)[:40] + "…")
            if not theirs and len(line) < 20000:
                for m in TOKEN_RUN.finditer(line):
                    run = m.group(0)
                    if mixed(run) and run not in ALLOWED_TOKENS and not run.startswith(("data/", "./")) \
                            and "/" not in run.strip("/"):
                        self.add(True, rel, n, "token-shaped", run[:12] + "… (%d characters)" % len(run))
            if code and "ecision" in line:
                for m in DECISION_CITE.finditer(line):
                    self.cites.append((rel, n, int(m.group(1))))

    def links(self, rel, data, exists):
        """A Markdown file's relative links and backticked repository paths, each checked to
        resolve inside the export (``exists(rel_path)``)."""
        s = data.decode("utf-8", "replace")
        base = os.path.dirname(rel)
        fence = False
        for n, line in enumerate(s.split("\n"), 1):
            if line.lstrip().startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            for m in MD_LINK.finditer(line):
                target = m.group(1)
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith(("#", "<")):
                    continue
                path = target.split("#")[0]
                if path and not exists(os.path.normpath(os.path.join(base, path)).replace("\\", "/")):
                    self.add(self.release, rel, n, "link", target)
            for m in BACKTICK_PATH.finditer(line):
                p = m.group(1)
                if any(c in p for c in "<>*") or p.startswith(("http", "www.")) or "//" in p:
                    continue
                if not re.search(r"\.[A-Za-z0-9]{1,6}/?$|/$", p):
                    continue          # a phrase with slashes ("and/or"), not a path
                if local_by_design(p):
                    continue          # the reader has it; the repository does not carry it
                cand = [p.rstrip("/"), os.path.normpath(os.path.join(base, p)).replace("\\", "/").rstrip("/")]
                if not any(exists(c) for c in cand):
                    self.add(self.release, rel, n, "path", p)

    def decision_log(self, entries):
        """Every "decisions N" cited in the exported code against the public log's entries."""
        if entries is None:
            if self.cites:
                self.add(self.release, PUBLIC_LOG, 0, "decision log",
                         "the public log is not there: %d citations of %d decisions unchecked"
                         % (len(self.cites), len({c[2] for c in self.cites})))
            return
        for rel, n, num in self.cites:
            if num not in entries:
                self.add(self.release, rel, n, "decision", "decisions %d has no entry in %s" % (num, PUBLIC_LOG))


def log_entries(data):
    """The entry numbers of the public log: its headings "## N." / "### N" or anchors id="dN"."""
    s = data.decode("utf-8", "replace")
    out = {int(m.group(1)) for m in re.finditer(r"(?m)^#{2,4}\s+(\d+)\b", s)}
    out |= {int(m.group(1)) for m in re.finditer(r"id=\"d(\d+)\"", s)}
    return out


# --------------------------------------------------------------------------------- the sources

def git(*args, cwd=ROOT, binary=False):
    r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True)
    if r.returncode != 0:
        raise SystemExit("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout if binary else r.stdout.decode("utf-8")


def is_rationale(rel):
    """A doc's private history (decisions 184, question 4: the rewritten technical docs replace the
    working ones, and their history and decision trail move to a `<doc>-rationale.md` beside each,
    which never leaves the private repository)."""
    return rel.endswith("-rationale.md")


#: a link into the private decision log, in any of the forms the docs under ordpar/ write it
PRIVATE_LOG_LINK = re.compile(r"(?:[\w.-]+/)*dictionary-site-decisions\.md#d")
PUBLIC_LOG = "docs/decisions.md"


def public_md(rel, data):
    """An exported Markdown file under ordpar/ with its links into the private decision log pointed at
    the public one, `docs/decisions.md`, whose entries carry the same numbers and anchors (decisions
    184). Other files, and Markdown with no such link, come back unchanged."""
    if not (rel.startswith("ordpar/") and rel.endswith(".md")):
        return data
    text = data.decode("utf-8")
    target = posixpath.relpath(PUBLIC_LOG, posixpath.dirname(rel)) + "#d"
    new = PRIVATE_LOG_LINK.sub(lambda m: target, text)
    return data if new == text else new.encode("utf-8")


def ordpar_files():
    """``(tracked, untracked)`` under ordpar/ (and ``LOCAL_PATHS``) that the manifest takes, as
    repository paths."""
    tracked = [p for p in git("ls-files", "-z", "ordpar", *LOCAL_PATHS).split("\0") if p]
    others = [p for p in git("ls-files", "-z", "--others", "--exclude-standard", "ordpar", *LOCAL_PATHS).split("\0")
              if p]
    def keep(p):
        return (p not in WORKING_DOCS and not is_rationale(p) and not p.startswith(NEVER)
                and "__pycache__" not in p)
    return sorted(p for p in tracked if keep(p) and os.path.exists(os.path.join(ROOT, p))), \
        sorted(p for p in others if keep(p))


def main_files():
    names = [p for p in git("ls-tree", "-r", "--name-only", "-z", MAIN_BRANCH, "--", *MAIN_PATHS).split("\0") if p]
    return sorted(names)


def last_commit(paths, rev="HEAD", cwd=ROOT):
    out = git("log", "-1", "--format=%H", rev, "--", *paths, cwd=cwd).strip()
    return out or None


def dirty(paths):
    """Exported paths with uncommitted changes (modified, added, deleted or untracked)."""
    out = git("status", "--porcelain", "-z", "--untracked-files=all", "--", *paths)
    return sorted({e[3:] for e in out.split("\0") if len(e) > 3 and e[2] == " "})


def module_level_imports(path):
    """The names a Python file imports at module level (not inside a function)."""
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (SyntaxError, UnicodeDecodeError):
        return set(), set()
    top, lazy = set(), set()

    def visit(node, inside):
        for child in ast.iter_child_nodes(node):
            fn = isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
            if isinstance(child, ast.Import):
                for a in child.names:
                    (lazy if inside else top).add(a.name)
            elif isinstance(child, ast.ImportFrom) and child.module and not child.level:
                (lazy if inside else top).add(child.module)
                for a in child.names:
                    (lazy if inside else top).add(child.module + "." + a.name)
            visit(child, inside or fn)
    visit(tree, False)
    return top, lazy


def resolve(name, importer, stage=None):
    """A module name as a repository path, or None when it is not one of the repository's."""
    parts = name.split(".")
    cands = []
    rel = "/".join(parts)
    cands += [rel + ".py", rel + "/__init__.py"]
    if len(parts) == 1:
        cands += ["scripts/%s.py" % name, "ordpar/%s.py" % name,
                  os.path.join(os.path.dirname(importer), name + ".py").replace("\\", "/"),
                  "handover/checks/%s.py" % name]
    for c in cands:
        if os.path.exists(os.path.join(ROOT, c)) or (stage and os.path.exists(os.path.join(stage, c))):
            return c
    return None


def closure_check(code_files, exported, stage):
    """``(missing, lazy, tests_private)``: module-level imports of exported code that resolve to
    an unexported repository module (the export refuses), the same inside functions (reported),
    and the tests that import an unexported module at module level ({test: [modules]})."""
    missing, lazy, tests_private = [], [], {}
    for rel in code_files:
        if not rel.endswith(".py"):
            continue
        top, inner = module_level_imports(os.path.join(stage, rel))
        for names, bucket in ((top, "top"), (inner, "lazy")):
            for name in sorted(names):
                hit = resolve(name, rel, stage)
                if hit is None or hit in exported:
                    continue
                if re.search(r"(^|/)tests/test_[^/]+\.py$", rel) and bucket == "top":
                    tests_private.setdefault(rel, []).append(hit)
                elif bucket == "top" and "/tests/" not in rel:
                    missing.append((rel, name, hit))
                else:
                    lazy.append((rel, name, hit))
    return missing, lazy, tests_private


# ------------------------------------------------------------------------------- the producers

def jsonl_rows(path):
    with io.open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def dumps_jsonl(rows):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def strip_added(row):
    """The added sentences without their check records: `verification`, `claim_check.note`."""
    n = 0
    for sense in row.get("senses") or []:
        for unit in [sense] + list(sense.get("subs") or []):
            for ex in unit.get("ex_added") or []:
                if ex.pop("verification", None) is not None:
                    n += 1
                cc = ex.get("claim_check")
                if isinstance(cc, dict):
                    cc.pop("note", None)
    return n


#: what of a row's `summary` goes out: the summary gloss the site shows, and the senses each
#: entry renders. The learner notes (`note`, `trap`) and the flashcards' `cue` and `ex` stay
#: private (decisions 184, Robin 2026-11-13: not of the quality to offer others; the site never
#: reads them)
SUMMARY_KEYS = ("gloss", "gloss_senses")


def strip_summary(row):
    """A row's `summary` cut to `SUMMARY_KEYS`. Returns the number of keys removed."""
    s = row.get("summary")
    if not isinstance(s, dict):
        return 0
    gone = [k for k in s if k not in SUMMARY_KEYS]
    for k in gone:
        del s[k]
    return len(gone)


def library(stage, src):
    """The gated, stripped library, rows in id order, and its gate marker."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from ordpar.sitegen import gate
    triage = gate.triage_module()
    if triage is None:
        raise Refused("the example gate needs scripts/triage.py: export from the private repository")
    rows = jsonl_rows(src)
    rows, held = triage.publishable(rows)
    stripped = 0
    import copy
    rows = [copy.deepcopy(r) for r in rows]
    summary_keys = 0
    for r in rows:
        stripped += strip_added(r)
        summary_keys += strip_summary(r)
    rows.sort(key=lambda r: r["id"])
    out = os.path.join(stage, LIBRARY)
    write(out, dumps_jsonl(rows))
    gate.write_marker(out, len(rows), held)
    return {"rows": len(rows), "held": held, "verification_removed": stripped,
            "summary_keys_removed": summary_keys}


def normalizations(src):
    rows = jsonl_rows(src)
    return dumps_jsonl([{k: r[k] for k in NORMALIZATION_FIELDS if k in r} for r in rows])


def dangling_def(src):
    rows = jsonl_rows(src)
    return dumps_jsonl([{k: r[k] for k in ("citer", "target", "defn")} for r in rows])


def dangling(src):
    with io.open(src, encoding="utf-8") as fh:
        rows = json.load(fh)
    # `fetch.load_dangling` reads the id, `load_dangling_assessed` whether `assessed` is set
    out = [dict({"id": r["id"]}, **({"assessed": True} if r.get("assessed") else {})) for r in rows]
    return (json.dumps(out, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def freq_extract(stage, freq, mirror_jsonl):
    """The 1-gram file's lines for the folded forms the index build asks for (`read_freq`'s
    `wanted`, over the whole mirror and the kept articles), in the file's order and bytes."""
    sys.path.insert(0, ROOT)
    from ordpar import build_index as bi
    entries = list(bi.read_mirror(mirror_jsonl))
    translated, lib = bi.library_pass(os.path.join(stage, LIBRARY))
    scoped, _t, _l = bi.search_scope(mirror_jsonl, list(entries), lib, translated, {})
    wanted = set()
    for e in entries + list(scoped):
        wanted |= {bi.fold(f) for f in list(e[1]) + list(e[4])}
    out_path = os.path.join(stage, FREQ_OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    kept = 0
    with open(freq, "rb") as src, open(out_path, "wb") as dst:
        for raw in src:
            line = raw.decode("latin-1").strip()
            sp = line.find(" ")
            if sp <= 0:
                continue
            if bi.fold(line[sp + 1:].strip()) in wanted:
                dst.write(raw)
                kept += 1
    return {"forms_wanted": len(wanted), "lines": kept}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def file_hash(path):
    """SHA-256 of a text file with its line endings as LF (a checkout's CRLF is no change)."""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def source_hash(source):
    """A public text's source's SHA-256 (LF line endings), or None when it is gone. A source
    written ``main:<path>`` is that file on branch `main`, read by `git show` as the export reads
    it (decisions 184: the checks' README, whose public version replaces `main`'s, the outsider
    test's findings 4, 5 and 16); any other is a file of this checkout."""
    if source.startswith(MAIN_BRANCH + ":"):
        try:
            data = git("show", source, binary=True)
        except SystemExit:
            return None
        return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    p = os.path.join(ROOT, source)
    return file_hash(p) if os.path.exists(p) else None


# ------------------------------------------------------------------------------- public texts

def read_texts():
    if not os.path.exists(TEXTS):
        return []
    with io.open(TEXTS, encoding="utf-8") as fh:
        return json.load(fh)["texts"]


def text_source(t):
    """A public text's file under ordpar/public/: its ``"from"`` when it has one, else its
    ``"path"``. The assistant guide is stored as ``CLAUDE.public.md`` and exported as
    ``CLAUDE.md``, since Claude Code may load a ``CLAUDE.md`` it finds in a folder of the private
    repository (decisions 184)."""
    return os.path.join(PUBLIC_DIR, t.get("from") or t["path"])


def public_texts(stage, texts):
    """Write each public text that exists at its ``"path"`` under ``stage``; returns
    ``check_texts(texts)``."""
    states = check_texts(texts)
    for t, (path, state, _d) in zip(texts, states):
        if state != "missing":
            with open(text_source(t), "rb") as fh:
                write(os.path.join(stage, path), fh.read())
    return states


def shown(path):
    """``path`` relative to the repository for a message; as it is when it lies on another drive."""
    try:
        return os.path.relpath(path, ROOT).replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


def check_texts(texts):
    """``[(public path, state, detail)]``: state "ok", "missing" (no public text yet) or "stale"
    (a source changed since the text was stamped, or was never stamped)."""
    out = []
    for t in texts:
        src = text_source(t)
        if not os.path.exists(src):
            out.append((t["path"], "missing", "no %s yet" % shown(src)))
            continue
        stale = []
        for s, h in sorted((t.get("sources") or {}).items()):
            now = source_hash(s)
            if now is None:
                stale.append("%s is gone" % s)
            elif h != now:
                stale.append("%s %s" % (s, "never stamped" if h is None else "changed"))
        out.append((t["path"], "stale" if stale else "ok", "; ".join(stale)))
    return out


def stamp(public_path):
    """Record the current hashes of a public text's sources: it has been brought up to date."""
    with io.open(TEXTS, encoding="utf-8") as fh:
        doc = json.load(fh)
    hit = [t for t in doc["texts"] if t["path"] == public_path]
    if not hit:
        raise SystemExit("%s is not in %s" % (public_path, os.path.relpath(TEXTS, ROOT)))
    if not os.path.exists(text_source(hit[0])):
        raise SystemExit("no public text at ordpar/public/%s to stamp" % (hit[0].get("from") or public_path))
    for s in hit[0].get("sources") or {}:
        h = source_hash(s)
        if h is None:
            raise SystemExit("the source %s of %s is gone: nothing stamped" % (s, public_path))
        hit[0]["sources"][s] = h
    with io.open(TEXTS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print("stamped %s: %d source(s)" % (public_path, len(hit[0].get("sources") or {})))


# --------------------------------------------------------------------------------- the export

def build_stage(stage, a, report):
    """Everything the export holds, under ``stage``; returns {repository-relative path: source}
    for the report."""
    tracked, untracked = ordpar_files()
    code = tracked + untracked + list(PIPELINE)
    for rel in code:
        src = os.path.join(ROOT, rel)
        dst = os.path.join(stage, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if rel.endswith(".md"):
            with open(src, "rb") as fh:
                write(dst, public_md(rel, fh.read()))
        else:
            shutil.copyfile(src, dst)
    main = main_files()
    for rel in main:
        write(os.path.join(stage, rel), git("show", "%s:%s" % (MAIN_BRANCH, rel), binary=True))
    report["code"] = {"ordpar_tracked": len(tracked), "ordpar_untracked": len(untracked),
                      "pipeline": len(PIPELINE), "from_main": len(main)}
    report["_untracked"] = untracked
    report["_code"] = code + main

    # the data
    report["library"] = library(stage, os.path.join(ROOT, "articles.jsonl"))
    for src, (dst, how) in sorted(SMALL.items()):
        p = os.path.join(ROOT, src)
        data = open(p, "rb").read() if how == "copy" else \
            {"normalizations": normalizations, "dangling_def": dangling_def, "dangling": dangling}[how](p)
        write(os.path.join(stage, dst), data)
    caps = [p for p in git("ls-files", "-z", CAPTURES).split("\0") if p]
    for rel in caps:
        dst = os.path.join(stage, CAPTURES_OUT + rel[len(CAPTURES):])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), dst)
    report["captures"] = len(caps)
    mirror_dir = os.path.dirname(a.mirror)
    parts = data_parts.split(a.mirror, os.path.join(stage, MIRROR_OUT))
    report["mirror_parts"] = parts
    for name in MIRROR_FILES:
        shutil.copyfile(os.path.join(mirror_dir, name), os.path.join(stage, MIRROR_OUT, name))
    n = 0
    for d in MIRROR_DIRS:
        for name in sorted(os.listdir(os.path.join(mirror_dir, d))):
            dst = os.path.join(stage, MIRROR_OUT, d, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(mirror_dir, d, name), dst)
            n += 1
    report["mirror_stored"] = n
    # the corrected copy, from the same mirror and the private review files and captures (the
    # projected log keeps every field the derivation reads, so the public repository remakes it)
    import corrected_copy
    report["corrected"] = corrected_copy.write(
        a.mirror, os.path.join(stage, CORRECTED_OUT),
        log_path=os.path.join(ROOT, "review", "source-normalizations.jsonl"),
        corrections_path=os.path.join(ROOT, "review", "mirror-corrections.jsonl"),
        captures=os.path.join(ROOT, CAPTURES))
    report["freq"] = freq_extract(stage, a.freq, a.mirror)

    # the public texts
    states = public_texts(stage, read_texts())
    write(os.path.join(stage, ".gitignore"), GITIGNORE.encode("utf-8"))
    report["texts"] = states
    import divergences_print
    with io.open(os.path.join(ROOT, DIVERGENCES_SRC), encoding="utf-8") as fh:
        div = divergences_print.edition(fh.read(), public=True)
    write(os.path.join(stage, DIVERGENCES_OUT), div.encode("utf-8"))

    # what was read
    mirror_commit = None
    if os.path.isdir(os.path.join(mirror_dir, ".git")):
        mirror_commit = git("rev-parse", "HEAD", cwd=mirror_dir).strip()
    info = {"made_by": "ordpar/export_public.py",
            "mode": "draft" if a.draft else "release",
            "read_from": {
                "ordpar": last_commit([p for p in code if p not in untracked] or ["ordpar"]),
                MAIN_BRANCH: last_commit(list(MAIN_PATHS), rev=MAIN_BRANCH),
                "library": last_commit(["articles.jsonl"] + list(SMALL) + [CAPTURES]),
                "bokmalsordboka_mirror": mirror_commit,
            }}
    if a.draft:
        info["uncommitted"] = len(report["_dirty"])
    write(os.path.join(stage, "EXPORT.json"), (json.dumps(info, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    report["read_from"] = info["read_from"]


def walk(folder):
    out = []
    for dp, dn, fn in os.walk(folder):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            out.append(os.path.relpath(os.path.join(dp, f), folder).replace("\\", "/"))
    return sorted(out)


def run_guard(folder, release, code_files=None):
    """The guard over every file of ``folder``."""
    g = Guard(release)
    files = walk(folder)
    present = set(files)
    dirs = {os.path.dirname(f) for f in files}
    while True:
        more = {os.path.dirname(d) for d in dirs} - dirs
        if not more:
            break
        dirs |= more

    def exists(p):
        p = p.strip("/")
        return p in present or p in dirs or p == "."
    for rel in files:
        g.path(rel)
        with open(os.path.join(folder, rel), "rb") as fh:
            data = fh.read()
        g.text(rel, data)
        if rel.endswith(".md") and not rel.startswith(THEIR_DATA):
            g.links(rel, data, exists)
    log = os.path.join(folder, PUBLIC_LOG)
    g.decision_log(log_entries(open(log, "rb").read()) if os.path.exists(log) else None)
    return g, files


def sync(stage, target):
    """Write into ``target`` every file of ``stage`` whose bytes differ; remove what ``stage``
    does not have (never `.git/`). Returns (written, unchanged, removed)."""
    os.makedirs(target, exist_ok=True)
    have = set(walk(target))
    want = walk(stage)
    written = unchanged = 0
    for rel in want:
        src, dst = os.path.join(stage, rel), os.path.join(target, rel)
        with open(src, "rb") as fh:
            data = fh.read()
        if rel in have:
            with open(dst, "rb") as fh:
                if fh.read() == data:
                    unchanged += 1
                    continue
        write(dst, data)
        written += 1
    removed = sorted(have - set(want))
    for rel in removed:
        os.remove(os.path.join(target, rel))
    for dp, dn, fn in sorted(os.walk(target, topdown=False), key=lambda t: -len(t[0])):
        if ".git" not in dp.replace("\\", "/").split("/") and dp != target and not os.listdir(dp):
            os.rmdir(dp)
    return written, unchanged, len(removed)


# ------------------------------------------------------------------------------------ the tests

BROWSER = re.compile(r"test_ordpar_browser_")
#: tests that cannot run from the export, each with its reason (decisions 184; the review's § 14).
#: A test that imports an unexported module is not one of them: it skips what needs the module,
#: naming it, and runs (the closure check finds it, `run_tests` runs it, the summary lists it).
EXCLUDED = {
}


def run_tests(folder, tests_private, jobs=8):
    """Run the export's tests in ``folder``: ``(results, excluded)``. The files in
    ``tests_private`` (they import a module the export leaves out) run like the rest; their
    tests that need the module skip, so a failure there is a test that does not skip as it
    should."""
    tests = [f for f in walk(folder) if re.search(r"(^|/)tests/test_[^/]+\.py$", f)
             or re.match(r"handover/checks/agent-review/test_[^/]+\.py$", f)]
    excluded, runnable = {}, []
    for t in tests:
        if BROWSER.search(t):
            excluded[t] = "browser test: needs Microsoft Edge and a built site"
        elif t in EXCLUDED:
            excluded[t] = EXCLUDED[t]
        else:
            runnable.append(t)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               ORDBOK_DATA_DIR=os.path.join(folder, DATA))
    for k in ("ORDPAR_TEST_OUT", "ORDPAR_TEST_BASE", "ORDPAR_MIRROR_DIR", "ORDPAR_TEST_AUDIO_NAMES",
              "ORDPAR_TEST_OVERLAY", "ORDPAR_REPORT_RECEIVER", "ORDPAR_SURVEY"):
        env.pop(k, None)

    def one(t):
        r = subprocess.run([sys.executable, os.path.join(folder, t)], cwd=folder, env=env,
                           capture_output=True, timeout=900)
        err = r.stderr.decode("utf-8", "replace")
        ran = re.findall(r"Ran (\d+) tests?", err)
        skipped = re.findall(r"skipped=(\d+)", err)
        return t, r.returncode, int(ran[-1]) if ran else 0, int(skipped[-1]) if skipped else 0, err[-1500:]
    results = []
    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        for res in ex.map(one, runnable):
            results.append(res)
    return results, excluded


# ------------------------------------------------------------------------------------ the main

#: the findings that refuse in any mode come first in a listing
FIRST = ("mail address", "private path", "key-shaped", "token-shaped", "working doc")


def show(findings, limit):
    findings = sorted(findings, key=lambda f: (f[2] not in FIRST, FIRST.index(f[2]) if f[2] in FIRST else 0))
    for rel, line, kind, text in findings[:limit]:
        print("  %s:%s: %s: %s" % (rel, line, kind, text))
    if len(findings) > limit:
        print("  … and %d more" % (len(findings) - limit))


def _counts(d):
    return ", ".join("%d %s" % (n, k) for k, n in sorted(d.items(), key=lambda kv: (-kv[1], kv[0])))


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", help="the public repository's folder (default: public_export in "
                                     "ordpar/local-paths.json)")
    ap.add_argument("--draft", action="store_true",
                    help="warn, rather than refuse, on what only a release must have: the public "
                         "texts, their sources unchanged, the decision log's entries, resolving links, "
                         "a committed export set")
    ap.add_argument("--mirror", help="the mirror's bm-articles.jsonl (default: mirror in "
                                     "ordpar/local-paths.json)")
    ap.add_argument("--freq", help="the National Library's 1-gram file (default: freq in "
                                   "ordpar/local-paths.json)")
    ap.add_argument("--no-tests", action="store_true", help="do not run the tests in the export")
    ap.add_argument("--jobs", type=int, default=8, help="test files run at once (default 8)")
    ap.add_argument("--guard", metavar="DIR", help="run the guard alone over DIR, write nothing")
    ap.add_argument("--stamp", metavar="PUBLIC_PATH",
                    help="record the hashes of a public text's sources (ordpar/public/texts.json)")
    ap.add_argument("--report", metavar="FILE", help="also write the findings and counts as JSON")
    a = ap.parse_args(argv)
    release = not a.draft

    if a.stamp:
        stamp(a.stamp)
        return 0
    if a.guard:
        g, files = run_guard(a.guard, release)
        print("guard over %d files (%s): %d refusal(s), %d warning(s); addresses in Bokmålsordboka's "
              "data: %d" % (len(files), "release" if release else "draft", len(g.refusals),
                            len(g.warnings), sum(g.their_mail.values())))
        show(g.refusals, 40)
        return 1 if g.refusals else 0

    a.target = a.target or local_paths.require("public_export", "--target DIR")
    a.mirror = a.mirror or local_paths.require("mirror", "--mirror FILE")
    a.freq = a.freq or local_paths.require("freq", "--freq FILE")
    report = {}
    tracked, untracked = ordpar_files()
    export_paths = tracked + untracked + list(PIPELINE) + ["articles.jsonl"] + list(SMALL) + [CAPTURES]
    report["_dirty"] = dirty(export_paths)
    if report["_dirty"]:
        msg = "%d exported file(s) have uncommitted changes (first: %s)" % (
            len(report["_dirty"]), ", ".join(report["_dirty"][:5]))
        if release:
            raise Refused("refused: " + msg + "; commit them, or run with --draft")
        print("warning: " + msg)

    parent = os.path.dirname(os.path.abspath(a.target))
    os.makedirs(parent, exist_ok=True)
    stage = tempfile.mkdtemp(prefix="ordpar-export-", dir=parent)
    try:
        print("staging in %s" % stage)
        build_stage(stage, a, report)

        # the closure: every module the exported code imports at module level is exported
        exported = set(report["_code"])
        missing, lazy, tests_private = closure_check(report["_code"], exported, stage)
        if missing:
            for rel, name, hit in missing:
                print("  %s imports %s (%s), which is not exported" % (rel, name, hit))
            raise Refused("refused: the exported code imports %d unexported module(s)" % len(missing))
        report["lazy_unexported"] = sorted({(hit) for _r, _n, hit in lazy})

        for path, state, detail in report["texts"]:
            if state != "ok":
                print(("warning" if a.draft else "refused") + ": public text %s %s: %s" % (path, state, detail))
        bad_texts = [t for t in report["texts"] if t[1] != "ok"]

        g, files = run_guard(stage, release)
        report["files"] = len(files)
        report["bytes"] = sum(os.path.getsize(os.path.join(stage, f)) for f in files)
        print("guard over %d files (%.1f MB): %d refusal(s), %d warning(s); addresses in "
              "Bokmålsordboka's data, counted: %d (%d distinct)"
              % (len(files), report["bytes"] / 1e6, len(g.refusals), len(g.warnings),
                 sum(g.their_mail.values()), len(g.their_mail)))
        if g.warnings:
            kinds = {}
            for w in g.warnings:
                kinds[w[2]] = kinds.get(w[2], 0) + 1
            print("warnings by kind: " + ", ".join("%s %d" % kv for kv in sorted(kinds.items())))
        if g.refusals:
            show(g.refusals, 60)
            raise Refused("refused by the guard: %d finding(s); nothing written to %s"
                          % (len(g.refusals), a.target))
        if release and bad_texts:
            raise Refused("refused: %d public text(s) missing or stale; nothing written" % len(bad_texts))

        written, unchanged, removed = sync(stage, a.target)
        print("target %s: %d written, %d unchanged, %d removed" % (a.target, written, unchanged, removed))
        report["sync"] = {"written": written, "unchanged": unchanged, "removed": removed}
        lib = report["library"]
        print("library: %d rows, %d added sentence(s) held by the gate, %d verification block(s) "
              "left out; captures %d; mirror parts %s; stored copies %d; frequency extract %d lines "
              "for %d forms" % (lib["rows"], lib["held"], lib["verification_removed"], report["captures"],
                                ", ".join("%s %.1f MB" % (os.path.basename(p), b / 1e6)
                                          for p, b in report["mirror_parts"]),
                                report["mirror_stored"], report["freq"]["lines"],
                                report["freq"]["forms_wanted"]))
        cc = report["corrected"]
        print("corrected copy: %d article(s) changed; mirror corrections %s; normalization patches "
              "%d (%s) from %d of %d log line(s), %s; log lines with no patch: %s" % (
                  cc["articles_changed"], _counts(cc["mirror_corrections"]), cc["patches"],
                  _counts(cc["patches_by_how"]), cc["log_lines_patched"], cc["log_lines"],
                  _counts(cc["patch_verdicts"]), _counts(cc["log_lines_not_patched"])))
        if report["lazy_unexported"]:
            print("imported inside functions only, not exported (no build path reaches them): "
                  + ", ".join(report["lazy_unexported"]))

        if not a.no_tests:
            results, excluded = run_tests(stage, tests_private, a.jobs)
            ran = sum(r[2] for r in results)
            skipped = sum(r[3] for r in results)
            failed = [r for r in results if r[1] != 0]
            print("tests in the export: %d file(s), %d test(s) run, %d skipped; %d file(s) failed"
                  % (len(results), ran, skipped, len(failed)))
            reasons = {}
            for t, why in excluded.items():
                key = why.split(":")[0]
                reasons.setdefault(key, []).append(t)
            for key, ts in sorted(reasons.items()):
                print("  excluded, %s: %d file(s)" % (key, len(ts)))
                if not key.startswith("browser"):
                    for t in sorted(ts):
                        print("    %s (%s)" % (t, excluded[t]))
            private = [r for r in results if r[0] in tests_private]
            if private:
                print("  importing a private module, run with those tests skipped: %d file(s)" % len(private))
                for t, code, n, k, err in sorted(private):
                    print("    %s (%s): %d run, %d skipped" % (t, ", ".join(
                        os.path.splitext(os.path.basename(m))[0] for m in sorted(set(tests_private[t]))), n, k))
            for t, code, n, k, err in failed:
                print("  FAILED %s (exit %s):\n    %s" % (t, code, err.strip().replace("\n", "\n    ")[-1200:]))
            report["tests"] = {"files": len(results), "run": ran, "skipped": skipped,
                               "failed": [r[0] for r in failed], "excluded": excluded,
                               "private_imports": {t: sorted(set(m)) for t, m in tests_private.items()},
                               "per_file": {r[0]: [r[1], r[2], r[3]] for r in results}}
        if a.report:
            out = {k: v for k, v in report.items() if not k.startswith("_")}
            out["refusals"] = g.refusals
            out["warnings"] = g.warnings
            out["their_mail"] = g.their_mail
            with io.open(a.report, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True, default=list) + "\n")
        return 1 if report.get("tests", {}).get("failed") else 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
