"""Deploy the built site to GitHub Pages (decisions 61 step 2), guarded (decisions 103): `ordpar/out/`
as ONE snapshot commit in a clone kept outside the repo, force-pushed, so the published repository
never grows a history.

    python ordpar/deploy.py prepare     # check the change lists, run every test, then copy out/ into the clone and commit (no network)
    python ordpar/deploy.py push        # force-push the snapshot, then `verify` (asks for GitHub sign-in the first time)
    python ordpar/deploy.py verify      # wait until ordpar.no serves the pushed build; run the browser tests on it
    python ordpar/deploy.py rollback    # the previous good snapshot, as it was, in a new snapshot commit (no network); then `push`
    python ordpar/deploy.py status      # what the clone holds, what is live, what a rollback would restore
    python ordpar/deploy.py readme --out FILE   # write the README prepare would publish, nothing else
    python ordpar/deploy.py test        # the gate alone: every test file against out/, nothing copied (for builds)

**The change lists (decisions 95, 109).** `prepare` first checks, in seconds, that this deploy's
entries were written and committed (on the repository's current branch, HEAD) since the last
published snapshot (the newest push in the clone's deploy log, at its time `at`; for a clone from
before the log, the commit of `origin/main`, at its commit time):
  * `ordpar/changes.md`, every deploy: its last commit must be newer than that snapshot;
  * `ordpar/library-changes.md`: it must exist in HEAD, and when the library changed, its last
    commit must be newer than that snapshot. "Changed": a fingerprint of `out/build.json`'s
    `site_stats` and `change_notice` counts (`library_fingerprint`), recorded in the deploy log with
    every published snapshot, differs from the last snapshot's, or that snapshot has none (every
    push before decisions 109).
A failing check refuses, naming the step (write the entry, commit it, run prepare again), before
the gate. `--skip-changes "<reason>"` (a reason required) lets through a re-deploy with nothing
reader-visible to say: the checks still run, and when one fails the override is appended, with the
build and the checks it skipped, to OVERRIDE_LOG and printed. `rollback` does not run `prepare`, so
it never needs a list entry (the rollback is recorded afterwards as a deploy).

**The gate (decisions 103).** `prepare` then runs every test file, `tests/test_*.py` and
`ordpar/tests/test_*.py` (the browser tests against the build being deployed: `ORDPAR_TEST_OUT`), in
parallel (`--jobs`, at most BROWSER_JOBS of them browser files), and refuses on any failure, naming the failing
files, before it touches the clone. `--skip-tests "<reason>"` (a reason required) lets an urgent fix
through: the tests still run, and the override is appended, with the build and the failing files, to
OVERRIDE_LOG (`ordpar/deploy-overrides.jsonl`, in the repo) and printed. The gate adds about a
minute and a half to a deploy (111 files: 86 s at 8 at once, 123 s at 4, 313 s one by one; 2026-10-23);
by 2026-10-27, 175 files, 1,017 s with the browser files one at a time, 436 s and 426 s with three (site
decisions 145). `test` runs the gate alone, nothing copied: the full suite for a build's brief.

**The reports' receiver (site decisions 166).** Before anything else, `prepare` refuses a build
whose reports receiver — `out/build.json`'s `reports_166` and the address written into the shipped
`report.js`, `ordpar.js` and `shell-pages.js` — is anything but empty (reports off) or `https://` on
a public host name (`report_address_problem`: not http, not an IP address, not localhost or a local
name), or that has reports on but no `/privacy/` page with its section on reports (the form links
it; 2026-11-05), and says why. A look build (`ORDPAR_REPORT_RECEIVER`, the receiver's stand-in on the home
network, `ordpar/receiver/README.md` § A look build) can so never be published by mistake. The
README's `[if reports]` follows the same record.

**The check after the push.** `push` then waits (up to `--wait` seconds, default 900) until
`<site>/offline/version.json` names the build just pushed, and runs the browser tests
(`ordpar/tests/test_ordpar_browser_*.py`) against the site with `ORDPAR_TEST_BASE`. A failure undoes
nothing: it prints the failing files and the rollback commands. `verify` runs this check alone
(for the snapshot last pushed); `push --no-verify` skips it.

**The rollback.** `rollback` takes the previous good published snapshot (the deploy log, or the
remote-tracking branch's reflog; never one a rollback left, never one whose check failed; `--to REV`
names one) and commits its files unchanged, build id included, as a new snapshot: an installed
offline copy updates whenever `version.json` names a build different from its own, so a copy that
took the bad build goes back, and one that never took it sees its own build and does nothing
(`docs/offline-app.md` § 6; the session's change of 2026-10-23, after the build found a new id
needless). Like `prepare`, it never pushes; `push` publishes it.

What is published: every file of `out/` except EXCLUDE (prototypes and the build's own report,
which names local paths), plus `.nojekyll` (GitHub must not run Jekyll over the files) and `CNAME`
(`ordpar.no`; the docs are silent on a force-pushed branch without it, so every snapshot carries it —
`docs/sessions/2026-09-19-ordpar-site-review/evidence/reports/github-pages-deploy-2026-10-20-lookup-web.md`),
and `README.md`, the published repository's front page on GitHub: the About page's own source,
`ordpar/about.md`, with its README-only note on the repository's files and the numbers of the build
being published, read from `out/build.json` (`site_stats`), rendered by `sitegen/about.py` (one text
for both, site decisions 63, Robin 2026-10-22; until then a copy of `ordpar/deploy-README.md`, now
retired). `out/` has no README of its own, so nothing is overwritten. `readme --out FILE` renders it
alone, for a check without touching the clone.
The clone lives on E: (C: is nearly full) and is kept between deploys: the old snapshot's objects
stay in it, so a push sends only what changed, and `push` keeps a ref to each of the last KEEP
snapshots it published (`refs/ordpar/pushed/*`) and a line for each in the clone's deploy log
(`.git/ordpar-deploys.jsonl`), so a rollback finds them. GitHub Pages limits a site to 1 GB;
`prepare` refuses above LIMIT.

For tests: `--clone DIR` (an existing scratch clone with its own `origin`; `prepare` initialises
only the real one), `--out DIR`, `--log FILE` (the override log), `--test-dir DIR` (repeatable;
replaces the two test folders, and says so), `--site URL`, `--repo DIR` (the repository whose change
lists are checked).
"""
import argparse, concurrent.futures, datetime, glob, hashlib, io, ipaddress, json, os, re, shutil, subprocess, sys, time
import urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ordpar", "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_paths  # noqa: E402  -- one machine's paths

# the real clone is this machine's, named in ordpar/local-paths.json ("deploy_clone"); unset, a
# step needs --clone (no private path in the code)
CLONE = local_paths.get("deploy_clone")
REAL_CLONE = CLONE
REMOTE = "https://github.com/ordpar/ordpar.github.io.git"
DOMAIN = "ordpar.no"
SITE = "https://" + DOMAIN
BUILD_JSON = os.path.join(OUT, "build.json")   # the build's report: the README's numbers
BRANCH = "main"
LIMIT = 1_000_000_000          # GitHub Pages: "no larger than 1 GB", counted strictly
#: Top-level entries of out/ never published: the prototypes (decisions 53, 54; the demo pages) and
#: the build's report (local paths).
EXCLUDE = {"compare-53", "t54", "demo.html", "demo-full.html", "build.json"}
#: The gate's test folders (decisions 101, 103).
TEST_DIRS = [os.path.join(ROOT, "tests"), os.path.join(ROOT, "ordpar", "tests")]
#: The two change lists (decisions 95), relative to the repository; `prepare` checks them (decisions 109).
CHANGES = "ordpar/changes.md"
LIBRARY_CHANGES = "ordpar/library-changes.md"
REPO = ROOT                           # the repository whose lists are checked (`--repo`, for tests)
#: Every `--skip-tests` and `--skip-changes` override, one JSON line each (in the repo, committed with the session's work).
OVERRIDE_LOG = os.path.join(ROOT, "ordpar", "deploy-overrides.jsonl")
DEPLOY_LOG = "ordpar-deploys.jsonl"   # in the clone's .git: every push, check and rollback
PENDING = "ordpar-pending.json"       # in the clone's .git: what the unpushed snapshot is
KEEP = 3                              # published snapshots kept by a ref (refs/ordpar/pushed/*)
TEST_TIMEOUT = 1800                   # seconds, per test file
JOBS = min(8, os.cpu_count() or 4)    # the gate's test files run at once
#: the browser files run at once, within JOBS (site decisions 145, Robin 2026-10-27: one at a time
#: until then; each file serves the build on its own free port and starts its own Edge profile)
BROWSER_JOBS = 3
POLL = 15                             # seconds between two looks at the site's version.json


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def git(*args, check=True, capture=False):
    r = subprocess.run(["git", "-C", CLONE] + list(args), text=True, encoding="utf-8",
                       errors="replace", capture_output=capture)
    if check and r.returncode != 0:
        sys.exit("git %s failed (%d)%s" % (" ".join(args), r.returncode,
                                           (": " + r.stderr) if capture else ""))
    return r


def git_out(*args):
    """stdout of a git command, stripped; None if it failed."""
    r = git(*args, check=False, capture=True)
    return r.stdout.strip() if r.returncode == 0 else None


def tree_bytes(path):
    n = files = 0
    for dp, dn, fn in os.walk(path):
        if ".git" in dn:
            dn.remove(".git")
        for f in fn:
            n += os.path.getsize(os.path.join(dp, f))
            files += 1
    return n, files


def readme_text(build_json=None):
    """The README.md the clone gets: `ordpar/about.md` with its README lines, the numbers the
    build recorded (`site_stats`). Exits if the build recorded none."""
    build_json = build_json or BUILD_JSON
    sys.path.insert(0, ROOT)
    from ordpar.sitegen import about
    try:
        with io.open(build_json, encoding="utf-8") as f:
            stats = json.load(f).get("site_stats")
    except (OSError, ValueError) as e:
        sys.exit("cannot read %s: %s" % (build_json, e))
    if not stats:
        sys.exit("%s has no site_stats: rebuild with build_site.py" % build_json)
    # site decisions 166: the About text's `[if reports]` as this build's pages have it (its
    # `reports_166` record; a build from before it, the committed switch)
    rec = (read_json(build_json) or {}).get("reports_166")
    return about.readme(stats, reports=bool(rec.get("receiver")) if isinstance(rec, dict) else None)


#: The shipped scripts that carry the reports' switch (site decisions 166: `report.js`, written into
#: both bundles by the article build, `sitegen/page.py` `report_js`)
REPORT_SCRIPTS = ("site/report.js", "site/ordpar.js", "site/shell-pages.js")
_REPORT_ASSIGN = re.compile(r"""\bREPORT_RECEIVER\s*=\s*(["'])(.*?)\1""")
#: Host names that never reach the public: this computer, the home network's own names
_LOCAL_NAMES = ("localhost",)
_LOCAL_SUFFIXES = (".localhost", ".local", ".lan", ".home", ".internal", ".intranet",
                   ".localdomain", ".home.arpa", ".test", ".invalid", ".example")


def report_address_problem(address):
    """Why the reports' receiver `address` may not be published (site decisions 166), or None: it
    must be empty (reports off) or `https://` on a public host name — not http, not an IP address
    (a home network's 192.168.…, this computer's 127.0.0.1), not localhost or a local name. A look
    build for :8098 (ORDPAR_REPORT_RECEIVER) points at the receiver's stand-in on the home network,
    so it can never pass."""
    if not address:
        return None
    try:
        u = urllib.parse.urlsplit(address)
        host = (u.hostname or "").rstrip(".").lower()
    except ValueError:
        return "%r is not an address" % address
    if u.scheme != "https":
        return "%s is not https" % address
    if not host:
        return "%s has no host" % address
    try:
        ipaddress.ip_address(host)
        return "%s is an IP address, not the receiver's public name (a local or home-network address)" % address
    except ValueError:
        pass
    if host in _LOCAL_NAMES or host.endswith(_LOCAL_SUFFIXES) or "." not in host:
        return "%s is a local name, not reachable from the internet" % address
    return None


def report_addresses(out):
    """Every reports receiver address the build in `out` names: [(where, address)] — `build.json`'s
    record (`reports_166.receiver`) and each assignment in the shipped scripts (REPORT_SCRIPTS);
    empty ones included, so a mismatch shows."""
    found = []
    bj = read_json(os.path.join(out, "build.json")) or {}
    rec = bj.get("reports_166")
    if isinstance(rec, dict) and "receiver" in rec:
        found.append(("build.json reports_166 (from %s)" % rec.get("source", "?"), rec.get("receiver") or ""))
    for rel in REPORT_SCRIPTS:
        try:
            with io.open(os.path.join(out, rel), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for m in _REPORT_ASSIGN.finditer(text):
            found.append(("out/" + rel, m.group(2)))
    return found


#: The privacy page's section the report form links (site decisions 166: `report.js` PRIVACY_HREF)
PRIVACY_PAGE = os.path.join("privacy", "index.html")
PRIVACY_REPORTS_ID = 'id="reporting-a-mistake"'


def check_reports(out):
    """`prepare`'s guard (site decisions 166): a line for each reports address in the build that may
    not be published (`report_address_problem`), one when the build's record and its shipped
    scripts disagree, and one when reports are on but the build has no `/privacy/` page with its
    section on reports (the form links `/privacy/#reporting-a-mistake`; 2026-11-05); [] when all is
    well (reports off, or on with a public https receiver and the page)."""
    found = report_addresses(out)
    problems = ["%s: %s" % (where, why) for where, addr in found
                for why in [report_address_problem(addr)] if why]
    if len({addr for _w, addr in found}) > 1:
        problems.append("the build names different addresses: %s"
                        % "; ".join("%s %r" % (w, a) for w, a in found))
    if any(addr for _w, addr in found):
        try:
            with io.open(os.path.join(out, PRIVACY_PAGE), encoding="utf-8") as f:
                page = f.read()
        except OSError:
            page = None
        if page is None:
            problems.append("reports are on but the build has no /privacy/ page: the report form links "
                            "/privacy/#reporting-a-mistake (turn chrome.PRIVACY on, or reports off)")
        elif PRIVACY_REPORTS_ID not in page:
            problems.append("reports are on but /privacy/ has no section on reports (%s), which the "
                            "report form links" % PRIVACY_REPORTS_ID)
    return problems


def write_readme(path, build_json=None):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme_text(build_json))


def read_json(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def build_of(out):
    """What the build in `out` is: its stamp, its time, and the offline build id the app sees."""
    bj = read_json(os.path.join(out, "build.json")) or {}
    vj = read_json(os.path.join(out, "offline", "version.json")) or {}
    return {"built_at": bj.get("built_at"), "stamp": bj.get("stamp"), "offline_build": vj.get("build")}


# ------------------------------------------------------------------------------------- the gate

def test_files(dirs):
    files = []
    for d in dirs:
        files += sorted(glob.glob(os.path.join(d, "test_*.py")))
    return files


def _summary(text):
    """unittest's last verdict line ("OK", "OK (skipped=2)", "FAILED (failures=1)"), or ''."""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("OK") or line.startswith("FAILED"):
            return line
    return ""


def run_tests(files, env_extra, jobs=JOBS, browser_jobs=BROWSER_JOBS):
    """Run each file as `python <file>` from the repo root, `jobs` at a time, at most `browser_jobs`
    of them browser files (each starts its own Edge; site decisions 145). Returns
    ([{file, rc, seconds, summary, tail}], seconds)."""
    env = dict(os.environ)
    env.pop("ORDPAR_TEST_BASE", None)
    env.update(env_extra)
    env["PYTHONIOENCODING"] = "utf-8"
    import threading
    browser_lock = threading.BoundedSemaphore(max(1, browser_jobs))

    def one(f):
        lock = browser_lock if "browser" in os.path.basename(f) else None
        if lock:
            lock.acquire()
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, f], cwd=ROOT, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=TEST_TIMEOUT)
            rc, text = p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            rc, text = -1, "timed out after %d s" % TEST_TIMEOUT
        finally:
            if lock:
                lock.release()
        return {"file": shown(f), "rc": rc,
                "seconds": round(time.time() - t0, 1), "summary": _summary(text),
                "tail": "\n".join(text.strip().splitlines()[-25:])}

    t0 = time.time()
    # the browser files first, so their lanes overlap the rest
    order = sorted(files, key=lambda f: "browser" not in os.path.basename(f))
    with concurrent.futures.ThreadPoolExecutor(max(1, jobs)) as ex:
        results = list(ex.map(one, order))
    results.sort(key=lambda r: r["file"])
    return results, round(time.time() - t0, 1)


def report_tests(results, seconds, label):
    failed = [r for r in results if r["rc"] != 0]
    skipped = [r for r in results if "skipped" in r["summary"]]
    for r in failed:
        print("---- FAILED: %s (exit %s, %.0f s)\n%s" % (r["file"], r["rc"], r["seconds"], r["tail"]))
    print("%s: %d test files in %.0f s; %d failed%s" % (
        label, len(results), seconds, len(failed),
        "" if not skipped else "; with skips: " + ", ".join(
            "%s (%s)" % (r["file"], r["summary"]) for r in skipped)))
    return [r["file"] for r in failed]


def gate(out, dirs, jobs, browser_jobs=BROWSER_JOBS):
    files = test_files(dirs)
    if not files:
        sys.exit("refused: no test files in %s" % ", ".join(dirs))
    if dirs != TEST_DIRS:
        print("gate: NOT the full gate, only %s" % ", ".join(dirs))
    print("gate: running %d test files against %s ..." % (len(files), out))
    results, seconds = run_tests(files, {"ORDPAR_TEST_OUT": os.path.abspath(out)}, jobs, browser_jobs)
    return report_tests(results, seconds, "gate"), seconds


def log_override(path, out, reason, failing, seconds):
    entry = {"at": now_iso(), "build": build_of(out), "reason": reason, "failing": failing,
             "gate_seconds": seconds}
    if is_scratch():
        entry["clone"] = CLONE
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("OVERRIDE logged in %s:\n%s" % (path, json.dumps(entry)))


# ----------------------------------------------------------------------------- the change lists

def repo_git(*args):
    """stdout of a git command in REPO, stripped; None if it failed."""
    r = subprocess.run(["git", "-C", REPO] + list(args), text=True, encoding="utf-8", errors="replace",
                       capture_output=True)
    return r.stdout.strip() if r.returncode == 0 else None


def committed_at(rel):
    """Unix time of the last commit on REPO's HEAD touching `rel`, or None if HEAD does not hold it."""
    if repo_git("cat-file", "-e", "HEAD:" + rel) is None:
        return None
    t = repo_git("log", "-1", "--format=%ct", "HEAD", "--", rel)
    return int(t) if t else None


def library_counts(build):
    """The dictionary's content as a library entry reports it: `site_stats` whole (its counts and
    the source snapshot's date) and `change_notice`'s counts (its numbers, its per-kind tables, and
    the length of each list and of the per-article notice map)."""
    cn = {}
    for k, v in (build.get("change_notice") or {}).items():
        if isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()):
            cn[k] = v                                  # groups, about: {kind: {articles, corrections}}
        elif isinstance(v, (dict, list)):
            cn[k] = len(v)                             # the lists, the notice map
        else:
            cn[k] = v
    return {"site_stats": build.get("site_stats") or {}, "change_notice": cn}


def library_fingerprint(build_json=None):
    """(fingerprint, totals): a 16-hex hash of `library_counts`, and `site_stats.articles` (shown in
    a refusal). Exits if the build report cannot be read."""
    build = read_json(build_json or BUILD_JSON)
    if build is None:
        sys.exit("cannot read %s" % (build_json or BUILD_JSON))
    text = json.dumps(library_counts(build), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            (build.get("site_stats") or {}).get("articles"))


def last_published():
    """The last published snapshot, {commit, at (unix), entry (its deploy-log line, or {})}, or None
    when nothing was pushed: the deploy log's newest push at its time `at`; for a clone from before
    the log, the newest commit of the remote-tracking branch at its commit time (`pushed_history`)."""
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        return None
    hist = pushed_history()
    if not hist:
        return None
    c, e = hist[0]
    if e.get("at"):
        at = int(datetime.datetime.fromisoformat(e["at"]).timestamp())
    else:
        at = int(git_out("log", "-1", "--format=%ct", c) or 0)
    return {"commit": c, "at": at, "entry": e}


def _iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat()


def check_changes(fingerprint, totals):
    """The change-list checks (decisions 109): [(check, message)] for each that fails; [] if both pass."""
    if repo_git("rev-parse", "--verify", "-q", "HEAD") is None:
        sys.exit("refused: %s is not a git repository with a commit; the change lists cannot be checked"
                 % REPO)
    last = last_published()
    since = last["at"] if last else None
    what = ("the last published snapshot (%s, published %s)" % (last["commit"][:11], _iso(since))
            if last else "the first deploy (nothing published yet)")
    fails = []

    def edited(rel):
        return " (the file has uncommitted edits: commit them)" if repo_git(
            "status", "--porcelain", "--", rel) else ""

    t = committed_at(CHANGES)
    if t is None or (since is not None and t <= since):
        fails.append(("changes", "%s has no commit since %s%s%s.\n  Write this deploy's entry in it "
                      "(decisions 95), commit it, and run prepare again." % (
                          CHANGES, what, "" if t is None else "; its last commit is " + _iso(t),
                          edited(CHANGES))))
    t = committed_at(LIBRARY_CHANGES)
    before = ((last or {}).get("entry") or {}).get("library")
    changed = before != fingerprint                    # no fingerprint recorded counts as changed
    if t is None:
        fails.append(("library-changes", "%s is not in the repository%s.\n  Create it with a baseline "
                      "entry (this build's totals from out/build.json site_stats, no changes listed; "
                      "decisions 109), commit it, and run prepare again." % (
                          LIBRARY_CHANGES, " (it exists but is not committed)"
                          if os.path.exists(os.path.join(REPO, LIBRARY_CHANGES)) else "")))
    elif changed and since is not None and t <= since:
        fails.append(("library-changes", "the library changed since %s (%s), and %s has no commit "
                      "since; its last commit is %s%s.\n  Write this deploy's entry in it (the new "
                      "totals and what changed), commit it, and run prepare again." % (
                          what, ("article totals %s -> %s" % (
                              json.dumps(last["entry"].get("library_totals")), json.dumps(totals)))
                          if before else "no fingerprint recorded for it",
                          LIBRARY_CHANGES, _iso(t), edited(LIBRARY_CHANGES))))
    if not fails:
        print("change lists: since %s, %s committed; %s" % (
            what, CHANGES, ("%s committed" % LIBRARY_CHANGES) if changed
            else "the library unchanged (fingerprint %s), so no %s entry needed" % (fingerprint,
                                                                                    LIBRARY_CHANGES)))
    return fails


def log_skip_changes(path, out, reason, fails):
    entry = {"at": now_iso(), "build": build_of(out), "override": "--skip-changes", "reason": reason,
             "skipped": [k for k, _m in fails]}
    if is_scratch():
        entry["clone"] = CLONE
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("OVERRIDE logged in %s:\n%s" % (path, json.dumps(entry)))


def shown(path):
    """A path relative to the repository where it can be, else absolute: `relpath` raises across
    drives (a test folder on C: while the checkout is on E:, the public export's run, 2026-11-12)."""
    try:
        return os.path.relpath(path, ROOT).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path).replace(os.sep, "/")


def is_scratch():
    """True when CLONE is not the machine's real clone (a test's, given by --clone)."""
    return REAL_CLONE is None or os.path.abspath(CLONE) != os.path.abspath(REAL_CLONE)


# ---------------------------------------------------------------------------------- the snapshot

def init_clone():
    os.makedirs(CLONE, exist_ok=True)
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        if is_scratch():
            sys.exit("refused: %s is not a clone; a scratch clone must exist with its own origin" % CLONE)
        subprocess.run(["git", "init", "-q", "-b", BRANCH, CLONE], check=True)
        git("remote", "add", "origin", REMOTE)
        git("config", "core.autocrlf", "false")       # publish the bytes as built


def commit_snapshot(message):
    """Commit the clone's working tree as the one commit of BRANCH (an orphan replaces the old)."""
    if git_out("rev-parse", "--abbrev-ref", "HEAD") != "snapshot" and \
            git_out("rev-parse", "--verify", "-q", "refs/heads/snapshot"):
        git("branch", "-D", "snapshot")                # a leftover of a run that stopped half-way
    git("checkout", "-q", "--orphan", "snapshot")
    git("add", "-A")
    git("-c", "user.name=Ordpar build", "-c", "user.email=post@ordpar.no",
        "commit", "-q", "-m", message)
    if git("rev-parse", "--verify", "-q", BRANCH, check=False, capture=True).returncode == 0:
        git("branch", "-D", BRANCH)
    git("branch", "-m", BRANCH)
    print("snapshot:", git("log", "--oneline", "-1", capture=True).stdout.strip())


def pending_path():
    return os.path.join(CLONE, ".git", PENDING)


def prepare(skip_reason=None, dirs=None, jobs=JOBS, override_log=None, skip_changes=None):
    if not os.path.isfile(os.path.join(OUT, "index.html")):
        sys.exit("no built site at %s" % OUT)
    problems = check_reports(OUT)                      # site decisions 166: no look build published
    if problems:
        sys.exit("refused: this build's reports receiver cannot be published:\n%s\nA look build "
                 "(ORDPAR_REPORT_RECEIVER, ordpar/receiver/README.md § A look build) is for :8098 "
                 "only: rebuild without it, or with the Worker's https address, and run prepare "
                 "again." % "\n".join("- " + p for p in problems))
    readme = readme_text()                             # before the clone is touched
    fingerprint, totals = library_fingerprint()
    fails = check_changes(fingerprint, totals)         # decisions 109: seconds, before the gate
    if fails and not skip_changes:
        sys.exit("refused: %s for this deploy:\n%s\nFor a re-deploy with nothing reader-visible to say: "
                 "--skip-changes \"<reason>\" (logged)." % (
                     "the change lists are not written" if len(fails) > 1
                     else "a change list is not written", "\n".join("- " + m for _k, m in fails)))
    if fails:
        for _k, m in fails:
            print("skipped (--skip-changes): " + m.splitlines()[0])
        log_skip_changes(override_log or OVERRIDE_LOG, OUT, skip_changes, fails)
    elif skip_changes:
        print("--skip-changes: nothing to skip, both checks pass; not logged")
    failing, seconds = gate(OUT, dirs or TEST_DIRS, jobs)
    if failing and not skip_reason:
        sys.exit("refused: %d test file(s) failed: %s\nFix them, or let an urgent fix through with "
                 "--skip-tests \"<reason>\" (logged)." % (len(failing), ", ".join(failing)))
    if skip_reason:
        log_override(override_log or OVERRIDE_LOG, OUT, skip_reason, failing, seconds)
    init_clone()
    for name in os.listdir(CLONE):                     # the old snapshot's files, not .git
        if name == ".git":
            continue
        p = os.path.join(CLONE, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    t0 = time.time()
    for name in os.listdir(OUT):
        if name in EXCLUDE:
            continue
        src, dst = os.path.join(OUT, name), os.path.join(CLONE, name)
        shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
    open(os.path.join(CLONE, ".nojekyll"), "w").close()
    with open(os.path.join(CLONE, "CNAME"), "w", newline="\n") as fh:
        fh.write(DOMAIN + "\n")
    with io.open(os.path.join(CLONE, "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme)                               # the repository's front page
    size, files = tree_bytes(CLONE)
    print("copied %d files, %.1f MB, in %.0f s" % (files, size / 1e6, time.time() - t0))
    if size > LIMIT:
        sys.exit("refused: %d bytes is over GitHub Pages' limit (%d)" % (size, LIMIT))
    stamp = build_of(OUT)["built_at"] or "unknown"
    # one commit, no history: an orphan branch replaces the old one
    commit_snapshot("ordpar.no, built %s (%d files, %.0f MB)" % (stamp, files, size / 1e6))
    pend = {"kind": "snapshot", "commit": git_out("rev-parse", "HEAD"), "at": now_iso(),
            "library": fingerprint, "library_totals": totals}
    if skip_reason:
        pend["override"] = skip_reason
    if fails:
        pend["skip_changes"] = skip_changes
    with io.open(pending_path(), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pend, fh)


# ----------------------------------------------------------------------------- the deploy log

def log_path():
    return os.path.join(CLONE, ".git", DEPLOY_LOG)


def read_log():
    out = []
    try:
        with io.open(log_path(), encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


def append_log(entry):
    with io.open(log_path(), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def version_at(rev):
    """offline/version.json at `rev` in the clone (a dict), or None."""
    t = git_out("show", "%s:offline/version.json" % rev)
    try:
        return json.loads(t) if t else None
    except ValueError:
        return None


def live_commit():
    return git_out("rev-parse", "--verify", "-q", "refs/remotes/origin/%s" % BRANCH)


# ------------------------------------------------------------------------------- push and verify

def push(verify_after=True, site=None, wait=900, dirs=None):
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        sys.exit("no clone at %s: run prepare first" % CLONE)
    head = git_out("rev-parse", BRANCH)
    before = live_commit()
    print("pushing %s to %s" % (git("log", "--oneline", "-1", BRANCH, capture=True).stdout.strip(),
                                git_out("remote", "get-url", "origin")))
    git("push", "--force", "origin", BRANCH)
    pend = read_json(pending_path()) or {}
    if pend.get("commit") != head:
        pend = {"kind": "snapshot"}
    entry = {"at": now_iso(), "pushed": head, "kind": pend.get("kind", "snapshot"),
             "build": (version_at(head) or {}).get("build"), "replaced": before}
    for k in ("restored", "left", "override", "skip_changes", "library", "library_totals"):
        if k in pend:
            entry[k] = pend[k]
    append_log(entry)
    try:
        os.remove(pending_path())
    except OSError:
        pass
    keep_refs(head)
    print("pushed %s (build %s)" % (head[:11], entry["build"]))
    if verify_after:
        return verify(site, wait, dirs)
    print("not checked (--no-verify); later: python ordpar/deploy.py verify")
    return 0


def keep_refs(head):
    """A ref to each of the last KEEP published snapshots, so their objects outlive the reflog."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    git("update-ref", "refs/ordpar/pushed/%s-%s" % (stamp, head[:11]), head)
    refs = (git_out("for-each-ref", "--format=%(refname)", "refs/ordpar/pushed/") or "").split()
    for r in sorted(refs)[:-KEEP]:
        git("update-ref", "-d", r)


def fetch_build(site):
    url = "%s/offline/version.json?t=%d" % (site.rstrip("/"), int(time.time() * 1000))
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "ordpar-deploy"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8")).get("build")


def wait_for_build(site, want, wait, every=None):
    """Poll `<site>/offline/version.json` until it names `want`; True when it does in `wait` s."""
    every = every or POLL
    t0 = time.time()
    seen, last_print = None, -60
    while True:
        try:
            seen = fetch_build(site)
        except Exception as e:                         # not up yet, a network blip: keep polling
            seen = "unreachable (%s)" % e
        if seen == want:
            print("%s serves build %s (after %.0f s)" % (site, want, time.time() - t0))
            return True
        if time.time() - t0 >= wait:
            print("%s still serves %s after %.0f s, not %s" % (site, seen, time.time() - t0, want))
            return False
        if time.time() - t0 - last_print >= 60:
            print("waiting for %s to serve build %s (it serves %s) ..." % (site, want, seen))
            last_print = time.time() - t0
        time.sleep(every)


def verify(site=None, wait=900, dirs=None):
    site = (site or SITE).rstrip("/")
    live = live_commit()
    if not live:
        sys.exit("nothing pushed from %s yet" % CLONE)
    want = (version_at(live) or {}).get("build")
    if not want:
        sys.exit("the pushed snapshot %s has no offline/version.json" % live[:11])
    entry = {"at": now_iso(), "verified": live, "build": want, "site": site}
    if not wait_for_build(site, want, wait):
        entry.update(verify="not served")
        append_log(entry)
        print("NOT CHECKED: GitHub has not served the build yet; run `python ordpar/deploy.py verify` later.")
        return 1
    files = [f for f in test_files(dirs or [TEST_DIRS[1]]) if "browser" in os.path.basename(f)]
    print("verify: running %d browser test files against %s ..." % (len(files), site))
    results, seconds = run_tests(files, {"ORDPAR_TEST_BASE": site}, jobs=BROWSER_JOBS)
    failing = report_tests(results, seconds, "verify")
    entry.update(verify="failed" if failing else "passed", failing=failing, seconds=seconds)
    append_log(entry)
    if failing:
        print("THE LIVE SITE FAILS %d browser test file(s): %s\nNothing has been undone. To put the "
              "previous good snapshot back:\n    python ordpar/deploy.py rollback\n"
              "    python ordpar/deploy.py push" % (len(failing), ", ".join(failing)))
        return 1
    print("verify: the live site passes every browser test (build %s)" % want)
    return 0


# ------------------------------------------------------------------------------------- rollback

def pushed_history():
    """The published snapshots, newest first: [(commit, log entry or {})]. The deploy log first;
    the remote-tracking branch's reflog for what was pushed before the log existed."""
    seen, out = set(), []
    for e in reversed(read_log()):
        c = e.get("pushed")
        if c and c not in seen:
            seen.add(c)
            out.append((c, e))
    refl = git_out("reflog", "show", "--format=%H", "refs/remotes/origin/%s" % BRANCH) or ""
    for c in refl.split():
        if c not in seen:
            seen.add(c)
            out.append((c, {}))
    return out


def rollback_target(to=None):
    """(commit, why) — the snapshot a rollback restores. Skips the live one, any that a rollback
    left, any whose check failed, and any whose objects are gone."""
    live = live_commit()
    if not live:
        sys.exit("nothing pushed from %s yet: nothing to roll back" % CLONE)
    if to:
        c = git_out("rev-parse", "--verify", "-q", to + "^{commit}")
        if not c:
            sys.exit("no commit %s in %s" % (to, CLONE))
        return c, "named by --to"
    log = read_log()
    left = {e.get("left") for e in log if e.get("kind") == "rollback"}
    failed = {e.get("verified") for e in log if e.get("verify") == "failed"}
    live_tree = git_out("rev-parse", live + "^{tree}")
    for c, e in pushed_history():
        if c == live or c in left or c in failed:
            continue
        if git("cat-file", "-e", c + "^{commit}", check=False, capture=True).returncode != 0:
            continue
        if git_out("rev-parse", c + "^{tree}") == live_tree:
            continue
        return c, "the newest published snapshot before the live one" + (
            "" if e else " (from the reflog of origin/%s)" % BRANCH)
    sys.exit("no earlier published snapshot to roll back to (the deploy log and the reflog of "
             "origin/%s hold none); name one with --to" % BRANCH)


def rollback(to=None):
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        sys.exit("no clone at %s" % CLONE)
    live = live_commit()
    target, why = rollback_target(to)
    old = (version_at(target) or {}).get("build")
    live_build = (version_at(live) or {}).get("build")
    if not old:
        sys.exit("refused: %s has no offline/version.json" % target[:11])
    print("rolling back: live %s (build %s)\n         to: %s (build %s), %s" % (
        git("log", "--format=%h %s", "-1", live, capture=True).stdout.strip(), live_build,
        git("log", "--format=%h %s", "-1", target, capture=True).stdout.strip(), old, why))
    t0 = time.time()
    git("checkout", "-q", "-f", target + "^0")         # the old snapshot's files, detached
    git("clean", "-q", "-f", "-d", "-x")
    subject = git_out("log", "--format=%s", "-1", target)
    commit_snapshot("ordpar.no, rollback to %s [%s], build %s (live was %s)"
                    % (subject.replace("ordpar.no, ", ""), target[:11], old, live_build))
    pend = {"kind": "rollback", "commit": git_out("rev-parse", "HEAD"), "at": now_iso(),
            "restored": target, "left": live, "build": old}
    for e in reversed(read_log()):                     # the restored snapshot's library fingerprint
        if e.get("pushed") == target:
            pend.update({k: e[k] for k in ("library", "library_totals") if k in e})
            break
    with io.open(pending_path(), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pend, fh)
    print("rollback snapshot ready in %.0f s: the files of %s, build id %s (unchanged). Nothing is published "
          "until: python ordpar/deploy.py push" % (time.time() - t0, target[:11], old))


def status():
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        print("no clone at", CLONE)
        return
    print("clone: ", git("log", "--oneline", "-1", capture=True).stdout.strip(),
          "(build %s)" % (version_at("HEAD") or {}).get("build"))
    live = live_commit()
    if live:
        print("pushed:", git("log", "--format=%h %s", "-1", live, capture=True).stdout.strip(),
              "(build %s)" % (version_at(live) or {}).get("build"))
    pend = read_json(pending_path())
    if pend and pend.get("commit") == git_out("rev-parse", "HEAD"):
        print("unpushed:", pend.get("kind"))
    for e in read_log()[-5:]:
        print("log:", json.dumps(e))
    size, files = tree_bytes(CLONE)
    print("%d files, %.1f MB in the working tree" % (files, size / 1e6))


def main(argv=None):
    global CLONE, OUT, BUILD_JSON, REPO
    # a test's tail may hold any character; under Windows' cp1252 a pipe or file refused one (2026-10-27)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("prepare", "push", "verify", "rollback", "status", "readme", "test"))
    ap.add_argument("--skip-tests", metavar="REASON",
                    help="prepare: publish even if tests fail; the reason is required and logged")
    ap.add_argument("--skip-changes", metavar="REASON",
                    help="prepare: publish without this deploy's change-list entries (a re-deploy with "
                    "nothing reader-visible to say); the reason is required and logged. rollback never "
                    "needs it")
    ap.add_argument("--jobs", type=int, default=JOBS, help="prepare, test: test files run at once (default %d)" % JOBS)
    ap.add_argument("--no-verify", action="store_true", help="push: skip the check after the push")
    ap.add_argument("--wait", type=int, default=900, metavar="S",
                    help="push, verify: how long to wait for the site to serve the build (default 900)")
    ap.add_argument("--site", metavar="URL", help="push, verify: the site checked (default %s)" % SITE)
    ap.add_argument("--to", metavar="REV", help="rollback: the snapshot to restore (default: the "
                    "previous good one)")
    ap.add_argument("--out", metavar="FILE", help="readme: where to write it (required); with any other "
                    "step, the built folder (default ordpar/out)")
    ap.add_argument("--build-json", default=None, metavar="FILE",
                    help="readme: the build report to read the numbers from (default out/build.json)")
    ap.add_argument("--clone", metavar="DIR", help="for tests: an existing scratch clone instead of the real one")
    ap.add_argument("--log", metavar="FILE", help="for tests: the override log (default %s)"
                    % os.path.relpath(OVERRIDE_LOG, ROOT))
    ap.add_argument("--repo", metavar="DIR", help="for tests: the repository whose %s and %s are "
                    "checked (default this one)" % (CHANGES, LIBRARY_CHANGES))
    ap.add_argument("--test-dir", action="append", metavar="DIR",
                    help="for tests: the test folder(s) instead of tests/ and ordpar/tests/")
    args = ap.parse_args(argv)
    if args.clone:
        CLONE = args.clone.replace("\\", "/")
    if CLONE is None and args.step != "readme":
        local_paths.require("deploy_clone", "--clone DIR")
    if args.step == "readme":
        if not args.out:
            ap.error("readme needs --out FILE")
        write_readme(args.out, args.build_json)
        print("wrote", args.out)
        return 0
    if args.out:
        OUT = os.path.abspath(args.out)
        BUILD_JSON = os.path.join(OUT, "build.json")
    if args.skip_tests is not None and not args.skip_tests.strip():
        ap.error("--skip-tests needs a reason")
    if args.skip_tests and args.step != "prepare":
        ap.error("--skip-tests is for prepare")
    if args.skip_changes is not None and not args.skip_changes.strip():
        ap.error("--skip-changes needs a reason")
    if args.skip_changes and args.step != "prepare":
        ap.error("--skip-changes is for prepare (rollback never needs it)")
    if args.repo:
        REPO = os.path.abspath(args.repo)
    dirs = [os.path.abspath(d) for d in args.test_dir] if args.test_dir else None
    if args.step == "test":
        failing, _seconds = gate(OUT, dirs or TEST_DIRS, args.jobs)
        return 1 if failing else 0
    if args.step == "prepare":
        prepare(args.skip_tests and args.skip_tests.strip(), dirs, args.jobs, args.log,
                args.skip_changes and args.skip_changes.strip())
    elif args.step == "push":
        return push(not args.no_verify, args.site, args.wait, dirs)
    elif args.step == "verify":
        return verify(args.site, args.wait, dirs)
    elif args.step == "rollback":
        rollback(args.to)
    else:
        status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
