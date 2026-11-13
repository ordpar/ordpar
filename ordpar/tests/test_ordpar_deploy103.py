"""Pins the guarded deploy (site decisions 103, 2026-10-23), `ordpar/deploy.py`, on a scratch clone
and a local bare repository standing in for GitHub — never the real clone, never the network:

* the gate: `prepare` runs the test files and refuses on a failing one, naming it, before the clone
  is touched; `--skip-tests` needs a non-empty reason; with one, the snapshot is made and the
  override is appended to the log (time, build, reason, the failing files);
* the rollback: after two pushed snapshots, `rollback` makes ONE new parentless commit holding the
  first snapshot's files exactly as they were, build id and packs included (changed 2026-10-23 from a
  new id, which proved needless); nothing is pushed
  until `push`; a second rollback never goes back to the snapshot a rollback left;
* the check after the push: `verify` waits until the site's `version.json` names the pushed build,
  then runs the browser test files against it (`ORDPAR_TEST_BASE`), and on a failure names the file
  and prints the rollback command.

Each prepare checks the change lists (decisions 109, pinned in `test_ordpar_deploy109.py`) in a
scratch repository (`--repo`) whose lists are committed.

Stdlib unittest; needs git."""

import contextlib
import functools
import http.server
import io
import json
import os
import shutil
import socketserver
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
DEPLOY = os.path.join(ROOT, "ordpar", "deploy.py")

from ordpar import deploy  # noqa: E402
from ordpar.sitegen import about  # noqa: E402

PASS = "import unittest\nclass T(unittest.TestCase):\n    def test(self): pass\nunittest.main()\n"
FAIL = ("import unittest\nclass T(unittest.TestCase):\n    def test(self): self.fail('planted')\n"
        "unittest.main()\n")
#: a browser test as verify runs it: passes when ORDPAR_TEST_BASE is set and the site answers
BROWSER_OK = ("import os, unittest, urllib.request\nclass T(unittest.TestCase):\n"
              "    def test(self):\n        b = os.environ['ORDPAR_TEST_BASE']\n"
              "        urllib.request.urlopen(b + '/index.html').read()\nunittest.main()\n")


def _rm(path):
    def onerror(fn, p, exc):
        os.chmod(p, stat.S_IWRITE)
        fn(p)
    shutil.rmtree(path, onerror=onerror)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def make_out(path, build, page="good"):
    """A tiny built site: a page, a script, a pack, the offline manifest and version.json."""
    write(os.path.join(path, "index.html"), "<!doctype html><title>Ordpar</title><p>%s</p>\n" % page)
    write(os.path.join(path, "site", "shell.js"), "/* %s */\n" % page)
    write(os.path.join(path, "offline", "bm-en-1.aaaa.bin"), "pack one\n")
    write(os.path.join(path, "offline", "version.json"),
          json.dumps({"format": "ordpar-offline", "version": 1, "build": build, "total": 9}) + "\n")
    write(os.path.join(path, "offline", "manifest.json"), json.dumps(
        {"format": "ordpar-offline", "version": 1, "build": build, "built_at": "2026-10-23T00:00:00",
         "total": 9, "packs": [{"name": "bm-en-1.aaaa.bin", "size": 9}]}, separators=(",", ":")))
    write(os.path.join(path, "build.json"), json.dumps(
        {"built_at": "2026-10-23T00:00:%02d" % len(page), "stamp": "ordpar build: test " + page,
         "site_stats": about.SAMPLE}))


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ordpar-deploy103-")
        self.clone = os.path.join(self.tmp, "clone").replace("\\", "/")
        self.bare = os.path.join(self.tmp, "github.git")
        self.tests = os.path.join(self.tmp, "tests")
        self.log = os.path.join(self.tmp, "overrides.jsonl")
        self.out = os.path.join(self.tmp, "out")
        if deploy.REAL_CLONE:      # unset on a machine without ordpar/local-paths.json
            self.assertNotEqual(os.path.abspath(self.clone), os.path.abspath(deploy.REAL_CLONE))
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.bare], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", self.clone], check=True)
        subprocess.run(["git", "-C", self.clone, "remote", "add", "origin", self.bare], check=True)
        subprocess.run(["git", "-C", self.clone, "config", "core.autocrlf", "false"], check=True)
        write(os.path.join(self.tests, "test_pass.py"), PASS)
        make_out(self.out, "1111111111111111")
        # the repository whose change lists prepare checks (decisions 109): both lists committed
        # an hour ago, before anything is published
        self.repo = os.path.join(self.tmp, "repo")
        subprocess.run(["git", "init", "-q", "-b", "ordpar", self.repo], check=True)
        subprocess.run(["git", "-C", self.repo, "config", "core.autocrlf", "false"], check=True)
        for name in ("changes.md", "library-changes.md"):
            write(os.path.join(self.repo, "ordpar", name), "# %s\n" % name)
        self.commit_repo("the lists", time.time() - 3600)

    def commit_repo(self, message, when=None):
        """Commit everything in the scratch repository, dated `when` (unix; default now + 5 s, so it is
        newer than a push made just before)."""
        when = int(when if when is not None else time.time() + 5)
        date = "%d +0000" % when
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "-m", message], check=True, env=env)

    def entry(self, name="changes.md", when=None):
        """Write and commit a new entry in ordpar/<name> of the scratch repository."""
        with io.open(os.path.join(self.repo, "ordpar", name), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n## an entry\n")
        self.commit_repo("entry in " + name, when)

    def tearDown(self):
        _rm(self.tmp)

    def run_deploy(self, *args):
        cmd = [sys.executable, DEPLOY] + list(args) + ["--clone", self.clone]
        if args[0] == "prepare":
            cmd += ["--out", self.out, "--log", self.log, "--test-dir", self.tests, "--repo", self.repo]
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=dict(os.environ, PYTHONIOENCODING="utf-8"))

    def git(self, *args):
        return subprocess.run(["git", "-C", self.clone] + list(args), capture_output=True, text=True,
                              encoding="utf-8").stdout.strip()

    def show(self, rev, path, repo=None):
        return subprocess.run(["git", "-C", repo or self.clone, "show", "%s:%s" % (rev, path)],
                              capture_output=True, text=True, encoding="utf-8").stdout


class TestGate(Scratch):
    def test_refuses_on_a_failing_test_naming_it(self):
        write(os.path.join(self.tests, "test_planted_fail.py"), FAIL)
        r = self.run_deploy("prepare")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("refused: 1 test file(s) failed", r.stderr)
        self.assertIn("test_planted_fail.py", r.stderr)
        self.assertNotIn("test_pass.py", r.stderr)
        self.assertEqual(self.git("rev-parse", "--verify", "-q", "HEAD"), "")   # no snapshot
        self.assertFalse(os.path.exists(os.path.join(self.clone, "index.html")))
        self.assertFalse(os.path.exists(self.log))

    def test_passes_without_it(self):
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gate: 1 test files", r.stdout)
        self.assertIn("NOT the full gate", r.stdout)
        self.assertTrue(self.git("log", "--format=%s", "-1").startswith("ordpar.no, built "))
        self.assertFalse(os.path.exists(self.log))

    def test_override_needs_a_reason(self):
        for reason in ("", "   "):
            r = self.run_deploy("prepare", "--skip-tests", reason)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--skip-tests needs a reason", r.stderr)

    def test_override_is_logged(self):
        write(os.path.join(self.tests, "test_planted_fail.py"), FAIL)
        r = self.run_deploy("prepare", "--skip-tests", "urgent fix for a broken search")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OVERRIDE logged", r.stdout)
        with io.open(self.log, encoding="utf-8") as fh:
            lines = [json.loads(l) for l in fh if l.strip()]
        self.assertEqual(len(lines), 1)
        e = lines[0]
        self.assertEqual(e["reason"], "urgent fix for a broken search")
        self.assertEqual(len(e["failing"]), 1)
        self.assertTrue(e["failing"][0].endswith("test_planted_fail.py"))
        self.assertEqual(e["build"]["offline_build"], "1111111111111111")
        self.assertEqual(e["build"]["stamp"], "ordpar build: test good")
        for k in ("at", "gate_seconds"):
            self.assertIn(k, e)
        self.assertIn("ordpar.no, built", self.git("log", "--format=%s", "-1"))


class TestRollback(Scratch):
    def two_pushed(self):
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        good = self.git("rev-parse", "HEAD")
        _rm(self.out)
        make_out(self.out, "2222222222222222", page="bad build")
        self.entry()                                   # this deploy's changes.md entry (decisions 109)
        self.assertEqual(self.run_deploy("prepare").returncode, 0)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        bad = self.git("rev-parse", "HEAD")
        self.assertNotEqual(good, bad)
        return good, bad

    def test_rollback_is_the_old_snapshot_as_it_was(self):
        good, bad = self.two_pushed()
        r = self.run_deploy("rollback")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Nothing is published", r.stdout)
        rb = self.git("rev-parse", "HEAD")
        self.assertNotIn(rb, (good, bad))
        self.assertEqual(self.git("rev-parse", "main"), rb)
        self.assertEqual(self.git("rev-list", "--count", "main"), "1")        # no history
        self.assertEqual(self.git("rev-parse", "refs/remotes/origin/main"), bad)  # not pushed yet
        self.assertIn("rollback to", self.git("log", "--format=%s", "-1"))
        # the files: exactly the good snapshot's, build id included (a copy on the bad build
        # updates because the id differs from its own; one that never took it does nothing)
        self.assertEqual(self.git("diff", "--name-only", good, rb), "")
        new = json.loads(self.show(rb, "offline/version.json"))["build"]
        self.assertEqual(new, "1111111111111111")
        self.assertIn("<p>good</p>", self.show(rb, "index.html"))
        # push publishes it, and the log says what it restored and what it left
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        self.assertEqual(subprocess.run(["git", "-C", self.bare, "rev-parse", "main"], capture_output=True,
                                        text=True).stdout.strip(), rb)
        with io.open(os.path.join(self.clone, ".git", "ordpar-deploys.jsonl"), encoding="utf-8") as fh:
            log = [json.loads(l) for l in fh]
        self.assertEqual([e["kind"] for e in log], ["snapshot", "snapshot", "rollback"])
        self.assertEqual((log[2]["restored"], log[2]["left"], log[2]["build"]), (good, bad, new))
        self.assertEqual(len(self.git("for-each-ref", "refs/ordpar/pushed/").splitlines()), 3)
        # a second rollback never returns to the snapshot a rollback left (bad), and the good one
        # is what is live already (the same files), so with nothing earlier it refuses
        r = self.run_deploy("rollback")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no earlier published snapshot", r.stderr)

    def test_nothing_to_roll_back(self):
        r = self.run_deploy("rollback")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing pushed", r.stderr)
        self.assertEqual(self.run_deploy("prepare").returncode, 0)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        r = self.run_deploy("rollback")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no earlier published snapshot", r.stderr)

    def test_reflog_fallback_and_to(self):
        good, bad = self.two_pushed()
        os.remove(os.path.join(self.clone, ".git", "ordpar-deploys.jsonl"))  # a clone from before 103
        r = self.run_deploy("rollback")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("from the reflog", r.stdout)
        self.assertEqual(self.git("diff", "--name-only", good, "HEAD"), "")      # the good files, as they were
        r = self.run_deploy("rollback", "--to", "nosuchrev")
        self.assertNotEqual(r.returncode, 0)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class TestVerify(Scratch):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.run_deploy("prepare").returncode, 0)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        self.site = os.path.join(self.tmp, "site")              # what "GitHub" serves
        make_out(self.site, "0000000000000000", page="older")   # still the build before
        self.server = _Server(("127.0.0.1", 0), functools.partial(_Quiet, directory=self.site))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.btests = os.path.join(self.tmp, "btests")
        write(os.path.join(self.btests, "test_x_browser_ok.py"), BROWSER_OK)
        write(os.path.join(self.btests, "test_not_run.py"), FAIL)   # not a browser file: not run
        self.poll = deploy.POLL
        deploy.POLL = 0.2

    def tearDown(self):
        deploy.POLL = self.poll
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def verify(self, wait):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = deploy.main(["verify", "--clone", self.clone, "--site", self.base, "--wait", str(wait),
                              "--test-dir", self.btests])
        return rc, buf.getvalue()

    def serve_new_after(self, seconds):
        def later():
            time.sleep(seconds)
            write(os.path.join(self.site, "offline", "version.json"),
                  self.show("HEAD", "offline/version.json"))
        threading.Thread(target=later, daemon=True).start()

    def test_waits_for_the_build_then_runs_the_browser_tests(self):
        self.serve_new_after(1.0)
        rc, out = self.verify(30)
        self.assertEqual(rc, 0, out)
        self.assertIn("serves build 1111111111111111", out)
        self.assertIn("verify: 1 test files", out)
        self.assertIn("passes every browser test", out)

    def test_a_failure_prints_the_rollback(self):
        write(os.path.join(self.btests, "test_y_browser_bad.py"), FAIL)
        self.serve_new_after(0)
        rc, out = self.verify(30)
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: ", out)
        self.assertIn("test_y_browser_bad.py", out)
        self.assertIn("python ordpar/deploy.py rollback", out)
        with io.open(os.path.join(self.clone, ".git", "ordpar-deploys.jsonl"), encoding="utf-8") as fh:
            last = json.loads(fh.readlines()[-1])
        self.assertEqual(last["verify"], "failed")
        # and a rollback skips a snapshot whose check failed: here there is no other
        r = self.run_deploy("rollback")
        self.assertNotEqual(r.returncode, 0)

    def test_gives_up_when_the_build_never_shows(self):
        rc, out = self.verify(1)
        self.assertEqual(rc, 1)
        self.assertIn("NOT CHECKED", out)


if __name__ == "__main__":
    unittest.main()
