"""Site decisions 100, the leftover browsers: the browser harness's Edge and profile always end.

**What it holds.** Headless Edge instances with their throwaway `ordpar-test-edge-*` profiles
(about 0.5 GB each) outlived earlier test runs (2026-10-23). For each way a browser test file can
end, a child Python process runs a small test module that opens a `harness.Site()` (Edge only, no
server: `ORDPAR_TEST_BASE` points at a dead port) and then:

- **passes** — one passing test, `tearDownModule` closing the site;
- **fails an assertion** — one failing test;
- **raises in `setUpModule`** right after `Site()` — where every browser file runs its checks, and
  unittest then never calls `tearDownModule`;
- **raises in `setUpClass`** right after `Site()` (`tearDownClass` then never called);
- **times out in `check()`** in `setUpModule` (a check script that hangs, `timeout=2`);
- **is killed** while Edge runs (`TerminateProcess`, as `subprocess.run`'s timeout in
  `deploy.py prepare`'s gate does) — then the next `Site()` (a second child that passes) must
  sweep the profile the killed one left.

After each: no Edge process whose command line names that profile is left running, and the
profile folder is gone. The harness at 2026-10-23 HEAD (aabc89b8a) fails the setUpModule,
setUpClass, timeout and killed cases (`ORDPAR_TEST_HARNESS_DIR` points the children at another
copy of `harness.py`, to show that); the fixed one passes all six. Whatever a case leaves behind
is ended and deleted by the test itself, so a failing run cleans up after itself.

Skipped without Edge or bun. Only Edge processes started on these throwaway profiles are ever
looked at or ended.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS_DIR = os.environ.get("ORDPAR_TEST_HARNESS_DIR") or os.path.join(HERE, "browser")
sys.path.insert(0, os.path.join(HERE, "browser"))
import harness  # noqa: E402  (edge_path only: the children import the copy under test)

SKIP = None if harness.edge_path() else "no Edge found"
if not SKIP and not shutil.which("bun"):
    SKIP = "no bun on PATH"

CHILD = textwrap.dedent('''
    import json, os, sys, time, unittest
    sys.path.insert(0, %(harness)r)
    import harness
    MODE = os.environ["CLEANUP_MODE"]
    SITE = None

    def _open():
        site = harness.Site()
        print(json.dumps({"profile": site.profile, "pid": site.edge.pid}), flush=True)
        return site

    def setUpModule():
        global SITE
        if MODE == "setupclass":
            return
        SITE = _open()
        if MODE == "setupmodule":
            raise RuntimeError("forced in setUpModule")
        if MODE == "timeout":
            SITE.check(%(hang)r, timeout=2)
        if MODE == "killed":
            time.sleep(600)

    def tearDownModule():
        if SITE:
            SITE.close()

    class Case(unittest.TestCase):
        site = None

        @classmethod
        def setUpClass(cls):
            if MODE == "setupclass":
                cls.site = _open()
                raise RuntimeError("forced in setUpClass")

        @classmethod
        def tearDownClass(cls):
            if cls.site:
                cls.site.close()

        def test_it(self):
            self.assertNotEqual(MODE, "fail", "forced failure")

    if __name__ == "__main__":
        unittest.main()
''')


def edge_on(folder_name):
    """Ids of the Edge processes whose command line names this profile folder."""
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine "
              "-like '*%s*' } | ForEach-Object { $_.ProcessId }" % folder_name)
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                             capture_output=True, text=True, timeout=60).stdout
    else:
        out = subprocess.run(["pgrep", "-f", folder_name], capture_output=True, text=True).stdout
    return [int(x) for x in out.split() if x.strip().isdigit()]


def end(pids):
    for pid in pids:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.kill(pid, 9)
            except OSError:
                pass


@unittest.skipIf(SKIP, SKIP or "")
class EdgeAlwaysEnds(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ordpar-cleanup-test-")
        cls.hang = os.path.join(cls.tmp, "hang.js")
        with open(cls.hang, "w", encoding="utf-8") as f:
            f.write("await new Promise(r => setTimeout(r, 120000));\n")
        cls.child = os.path.join(cls.tmp, "child_cleanup.py")
        with open(cls.child, "w", encoding="utf-8") as f:
            f.write(CHILD % {"harness": HARNESS_DIR, "hang": cls.hang})
        cls.env = dict(os.environ, ORDPAR_TEST_BASE="http://127.0.0.1:9", PYTHONIOENCODING="utf-8")
        cls.env.pop("ORDPAR_TEST_HARNESS_DIR", None)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.profiles = []

    def tearDown(self):
        # whatever a case left behind, ended here, so a failing run does not leak either
        for p in self.profiles:
            end(edge_on(os.path.basename(p)))
            for _ in range(40):
                shutil.rmtree(p, ignore_errors=True)
                if not os.path.exists(p):
                    break
                time.sleep(0.25)

    def _run(self, mode):
        p = subprocess.run([sys.executable, self.child], env=dict(self.env, CLEANUP_MODE=mode),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        return self._profile(p.stdout, p.stderr)

    def _profile(self, out, err=""):
        for line in out.splitlines():
            if line.startswith("{"):
                prof = json.loads(line)["profile"]
                self.profiles.append(prof)
                return prof
        self.fail("the child printed no profile:\n%s\n%s" % (out[-1500:], err[-1500:]))

    def _assert_gone(self, prof, how):
        left = []
        for _ in range(20):                    # up to ~10 s for Edge to finish going
            left = edge_on(os.path.basename(prof))
            if not left:
                break
            time.sleep(0.5)
        self.assertEqual(left, [], "%s: Edge still running on %s (pids %s)" % (how, prof, left))
        self.assertFalse(os.path.exists(prof), "%s: the profile %s is still there" % (how, prof))

    def test_a_passing_run(self):
        self._assert_gone(self._run("pass"), "a passing run")

    def test_a_failing_assertion(self):
        self._assert_gone(self._run("fail"), "a failing assertion")

    def test_an_exception_in_setUpModule(self):
        self._assert_gone(self._run("setupmodule"), "an exception in setUpModule")

    def test_an_exception_in_setUpClass(self):
        self._assert_gone(self._run("setupclass"), "an exception in setUpClass")

    def test_a_check_timeout(self):
        self._assert_gone(self._run("timeout"), "a check() timeout in setUpModule")

    def test_the_process_killed(self):
        p = subprocess.Popen([sys.executable, self.child], env=dict(self.env, CLEANUP_MODE="killed"),
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                             encoding="utf-8", errors="replace")
        try:
            line = p.stdout.readline()
            prof = self._profile(line)
            time.sleep(1)
        finally:
            p.kill()                           # TerminateProcess: no cleanup of any kind runs
            p.wait(30)
            p.stdout.close()
        left = []
        for _ in range(20):
            left = edge_on(os.path.basename(prof))
            if not left:
                break
            time.sleep(0.5)
        self.assertEqual(left, [], "the test process killed: Edge still running on %s (pids %s)" % (prof, left))
        # the folder outlives a killed process; the next Site() sweeps it
        nxt = self._run("pass")
        self._assert_gone(nxt, "the run after a killed one")
        self.assertFalse(os.path.exists(prof), "the test process killed: its profile %s is still there "
                                               "after the next Site()" % prof)


if __name__ == "__main__":
    unittest.main()
