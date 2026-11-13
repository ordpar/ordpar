"""The site's browser tests (decisions 100): the Python side of the harness.

A test file opens ONE `Site` for all its tests (`setUpModule`/`setUpClass`): it serves the
built site and starts headless Edge with a throwaway profile; each test runs a check script
from this folder under `bun` (`Site.check("senses.js", {...})`), which connects to that Edge
through `cdp.js`, works in a fresh browser context, and prints one JSON line — returned here
as a dict. `Site.close()` stops Edge, deletes the profile and stops the server.

**Edge and its profile always end** (decisions 100, the leftover browsers, 2026-10-23). Headless
Edge instances with their `ordpar-test-edge-*` profiles (about 0.5 GB each) had outlived earlier
runs: unittest never calls a test file's `tearDownModule` when its `setUpModule` raises (a
`check()` that throws or times out there, where every browser file runs its checks), and nothing
runs at all when the test process is killed (as `deploy.py prepare`'s gate does on its per-file
timeout). So `Site()`, besides `close()`:
- registers `close()` with unittest's module cleanups (run even when `setUpModule` or `setUpClass`
  raises) and with `atexit` (an uncaught exception, Ctrl-C, `sys.exit`);
- on Windows, starts Edge suspended inside a job object that kills every process in it when its
  last handle closes — which Windows does when this Python process ends, killed or not — and only
  then resumes it, so no Edge child starts outside the job;
- writes `ordpar-harness-owner.json` (this process's id and start time) into the profile, and
  first sweeps the stale ones: an `ordpar-test-edge-*` folder whose owner is no longer running
  (or, with no owner file, one an older harness made over an hour ago) is deleted, after ending
  any Edge whose command line names that folder. Robin's own Edge is never touched: only
  processes started with `--user-data-dir=` one of these folders. A killed run's profile is
  therefore deleted by the next `Site()`.
`test_ordpar_browser_cleanup100.py` forces each way out in a child process and checks.

**What is served.** By default `ordpar/out/` (or the folder `ORDPAR_TEST_OUT` names) on `127.0.0.1` on a free port (a stdlib static
server: `/bm-en/<id>/` serves that folder's `index.html`, a `?v=` stamp is ignored). Set
`ORDPAR_TEST_BASE` to test another copy instead, e.g. the live site:

    ORDPAR_TEST_BASE=https://ordpar.no python ordpar/tests/test_ordpar_browser_senses.py

`ORDPAR_TEST_OVERLAY` names a folder laid OVER the one served (site decisions 154/155's build,
2026-10-31): a path the overlay holds — a file, or a folder with its `index.html` — is served
from it, every other path from the built folder; `404.html` too. So a few pages rendered into a
scratch folder (with that render's `site/` and `index/`) can be tested against the whole built
site without copying it. The overlay's entries are matched case-sensitively, as the rest.

**Skipped, not failed**, with the reason printed, when Edge, `bun` or `ordpar/out/` is missing
(`skip_reason()`; `ORDPAR_EDGE` names another Chromium-family browser). A check script that
throws prints `{"error": ...}` and the harness raises it as an AssertionError.

**Adding a check:** write `ordpar/tests/browser/<name>.js` (import `open`, `base`, `args`, `run`,
`done` from `./cdp.js`; end with `done({...})`), and call it from a `test_ordpar_browser_*.py`
file with `Site.check("<name>.js", args)`; assert on the returned dict in Python, so a failure
message names the page and the case.
"""
from __future__ import annotations

import atexit
import functools
import http.server
import json
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(os.path.dirname(HERE))          # ordpar/
#: The build served. `ORDPAR_TEST_OUT` names another built folder: `deploy.py prepare --out DIR`
#: sets it, so its gate tests the build it is about to publish (decisions 103).
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ORDPAR, "out")
#: A folder served over `OUT` where it holds the path (module doc, "What is served")
OVERLAY = os.environ.get("ORDPAR_TEST_OVERLAY") or None

EDGE_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/microsoft-edge",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


#: The throwaway profiles' folder-name prefix, and the owner file written into each.
PROFILE_PREFIX = "ordpar-test-edge-"
OWNER_FILE = "ordpar-harness-owner.json"
#: A profile with no owner file (an older harness made it) counts as stale after this long.
UNOWNED_STALE_S = 3600

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    _k32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    _k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _k32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _k32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    _k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    _k32.GetCurrentProcess.restype = wintypes.HANDLE
    _ntdll = ctypes.WinDLL("ntdll")
    _ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)

    class _IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class _BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", _IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _JOB_KILL_ON_CLOSE = 0x2000            # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    _EXTENDED_LIMITS = 9                   # JobObjectExtendedLimitInformation
    _CREATE_SUSPENDED = 0x4

    def _kill_on_close_job():
        """A new job object whose processes all end when its last handle closes, or None."""
        job = _k32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _ExtendedLimits()
        info.BasicLimitInformation.LimitFlags = _JOB_KILL_ON_CLOSE
        if not _k32.SetInformationJobObject(job, _EXTENDED_LIMITS, ctypes.byref(info), ctypes.sizeof(info)):
            _k32.CloseHandle(job)
            return None
        return job

    def _started(handle):
        t = [wintypes.FILETIME() for _ in range(4)]
        if not _k32.GetProcessTimes(handle, *[ctypes.byref(x) for x in t]):
            return None
        return (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime

    def _process_start(pid):
        """The start time of the running process `pid`, or None when none is running."""
        h = _k32.OpenProcess(0x1000, False, int(pid))         # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        try:
            code = wintypes.DWORD()
            if not _k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:   # STILL_ACTIVE
                return None
            return _started(h)
        finally:
            _k32.CloseHandle(h)

    def _my_start():
        return _started(_k32.GetCurrentProcess())

else:
    def _process_start(pid):
        try:
            os.kill(int(pid), 0)
        except (OSError, ValueError):
            return None
        try:
            with open("/proc/%d/stat" % int(pid)) as f:
                return int(f.read().rsplit(")", 1)[1].split()[19])
        except (OSError, ValueError, IndexError):
            return 0

    def _my_start():
        return _process_start(os.getpid())


def edge_processes(folder_name):
    """The ids of the Edge processes whose command line names `folder_name` — a profile folder's
    name, so never Robin's own Edge."""
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine "
              "-like '*%s*' } | ForEach-Object { $_.ProcessId }" % folder_name.replace("'", "''"))
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
    else:
        r = subprocess.run(["pgrep", "-f", folder_name], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]


def _kill(pids):
    for pid in pids:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.kill(pid, 9)
            except OSError:
                pass


def _remove(folder, tries=40):
    for _ in range(tries):
        shutil.rmtree(folder, ignore_errors=True)
        if not os.path.exists(folder):
            return True
        time.sleep(0.25)
    return False


def _is_stale(folder):
    try:
        with open(os.path.join(folder, OWNER_FILE), encoding="utf-8") as f:
            owner = json.load(f)
    except (OSError, ValueError):
        try:
            return time.time() - os.stat(folder).st_ctime > UNOWNED_STALE_S
        except OSError:
            return False
    start = _process_start(owner.get("pid", -1))
    return start is None or start != owner.get("start")


def sweep_stale_profiles():
    """Delete every stale `ordpar-test-edge-*` profile (its owner gone), ending any Edge still
    running on it first. Returns the folders deleted."""
    tmp = tempfile.gettempdir()
    gone = []
    try:
        names = [n for n in os.listdir(tmp) if n.startswith(PROFILE_PREFIX)]
    except OSError:
        return gone
    for name in names:
        folder = os.path.join(tmp, name)
        if not os.path.isdir(folder) or not _is_stale(folder):
            continue
        shutil.rmtree(folder, ignore_errors=True)
        if os.path.exists(folder):              # held open: an Edge still runs on it
            try:
                _kill(edge_processes(name))
            except (OSError, subprocess.SubprocessError):
                pass
            _remove(folder)
        if os.path.exists(folder):
            print("harness: could not delete the stale browser profile %s" % folder, file=sys.stderr)
        else:
            gone.append(folder)
    return gone


def edge_path():
    p = os.environ.get("ORDPAR_EDGE")
    if p:
        return p if os.path.exists(p) else None
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("microsoft-edge")


def base_override():
    b = os.environ.get("ORDPAR_TEST_BASE", "").strip()
    return b.rstrip("/") or None


def skip_reason():
    """Why the browser tests cannot run here, or None."""
    if not edge_path():
        return "no Edge found (set ORDPAR_EDGE to a Chromium-family browser)"
    if not shutil.which("bun"):
        return "no bun on PATH"
    if not base_override() and not os.path.exists(os.path.join(OUT, "bm-en", "index.html")):
        return "no built site in ordpar/out/ (and ORDPAR_TEST_BASE not set)"
    return None


@functools.lru_cache(maxsize=4096)
def _names(folder):
    """A folder's entries as a set (cached: `bm-en/` holds some 120,000)."""
    try:
        return frozenset(os.listdir(folder))
    except OSError:
        return frozenset()


@functools.lru_cache(maxsize=4096)
def names_lower(folder):
    return frozenset(n.lower() for n in _names(folder))


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
        ".json": "application/json", ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json",
        ".html": "text/html; charset=utf-8", ".png": "image/png", ".bin": "application/octet-stream",
        ".wasm": "application/wasm",
    }

    def log_message(self, *a):          # quiet
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path):
        """As the standard server's, but case-sensitive, as GitHub Pages is (site decisions 117:
        `/bm-en/Norge` answers 404 there, where Windows' file system would find `norge/`): a path
        whose letters differ in case from the folder's names maps to nowhere."""
        full = super().translate_path(path)
        rel = os.path.relpath(full, self.directory)
        if rel.startswith(".."):
            return full
        if OVERLAY:
            mine = self._in(OVERLAY, rel)
            if mine and (os.path.isfile(mine) or os.path.isfile(os.path.join(mine, "index.html"))):
                return mine
        here = self.directory
        for part in [p for p in rel.split(os.sep) if p and p != "."]:
            names = _names(here)
            if part not in names:
                return (os.path.join(self.directory, "__ordpar_case_mismatch__", part)
                        if part.lower() in names_lower(here) else full)
            here = os.path.join(here, part)
        return full

    @staticmethod
    def _in(folder, rel):
        """`rel` under `folder`, matched case-sensitively part by part, or None."""
        here = folder
        for part in [p for p in rel.split(os.sep) if p and p != "."]:
            if part not in _names(here):
                return None
            here = os.path.join(here, part)
        return here

    def send_error(self, code, message=None, explain=None):
        """A missing path answers with the site's `404.html` and status 404, as GitHub Pages
        does (site decisions 117: `/bm-en/Norge` is the 404 shell's, which sends it to the word
        page `/bm-en/norge/`); any other error as the standard server's."""
        page = os.path.join(self.directory, "404.html")
        if OVERLAY and os.path.exists(os.path.join(OVERLAY, "404.html")):
            page = os.path.join(OVERLAY, "404.html")
        if code != 404 or self.command != "GET" or not os.path.exists(page):
            return super().send_error(code, message, explain)
        with open(page, "rb") as f:
            body = f.read()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    # The listen backlog. Python's default is 5; a page fires about 9 requests at once, and with
    # three browser lanes (site decisions 145) the accept loop lags, the backlog overflows and
    # Windows refuses the rest ("Failed to fetch"). That dropped `tabtitle131` `test_b`'s article
    # fetch, so the tab kept "vindu — Ordpar" (traced 2026-10-29: 4 of 32 runs under load, every
    # one with the article's request refused).
    request_queue_size = 128


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Site:
    """The served site and one headless Edge. Use once per test file."""

    def __init__(self):
        self.server = None
        self.edge = None
        self.job = None
        self.profile = None
        self.port = None
        # registered before anything that can fail: run even when setUpModule/setUpClass raises
        # (unittest then skips tearDownModule/tearDownClass) and at interpreter exit
        unittest.addModuleCleanup(self.close)
        atexit.register(self.close)
        sweep_stale_profiles()
        override = base_override()
        try:
            if override:
                self.base = override
            else:
                self.server = _Server(("127.0.0.1", 0), functools.partial(_Handler, directory=OUT))
                threading.Thread(target=self.server.serve_forever, daemon=True).start()
                self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
            self._start_edge()
        except Exception:
            self.close()
            raise

    def _start_edge(self):
        self.profile = tempfile.mkdtemp(prefix=PROFILE_PREFIX)
        with open(os.path.join(self.profile, OWNER_FILE), "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "start": _my_start()}, f)
        self.port = _free_port()
        cmd = [edge_path(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--disable-extensions", "--disable-sync", "--mute-audio",
               "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=%d" % self.port,
               "--user-data-dir=" + self.profile, "about:blank"]
        if os.name == "nt":
            # suspended until it is in the kill-on-close job, so every process it starts is in it too
            self.job = _kill_on_close_job()
            self.edge = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                         creationflags=_CREATE_SUSPENDED)
            if self.job and not _k32.AssignProcessToJobObject(self.job, int(self.edge._handle)):
                _k32.CloseHandle(self.job)
                self.job = None
            _ntdll.NtResumeProcess(int(self.edge._handle))
        else:
            self.edge = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                         start_new_session=True)
        for _ in range(120):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % self.port, timeout=1):
                    return
            except Exception:
                if self.edge.poll() is not None:
                    break
                time.sleep(0.25)
        raise RuntimeError("headless Edge did not answer on port %d" % self.port)

    def check(self, script, args=None, timeout=300):
        """Run `ordpar/tests/browser/<script>` under bun; return its JSON result (a dict)."""
        env = dict(os.environ, ORDPAR_CDP_PORT=str(self.port), ORDPAR_BASE=self.base,
                   ORDPAR_ARGS=json.dumps(args or {}))
        p = subprocess.run(["bun", os.path.join(HERE, script)], cwd=HERE, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            res = json.loads(lines[-1])
        except (IndexError, ValueError):
            raise AssertionError("%s gave no JSON result (exit %s):\n%s\n%s"
                                 % (script, p.returncode, p.stdout[-2000:], p.stderr[-2000:]))
        if isinstance(res, dict) and res.get("error"):
            raise AssertionError("%s threw: %s" % (script, res["error"]))
        return res

    def close(self):
        """Stop Edge (its whole job, or its process tree), delete the profile, stop the server.
        Safe to call more than once: `__init__` registers it as a module cleanup and at exit."""
        if self.job is not None:          # every process Edge started, at once
            _k32.TerminateJobObject(self.job, 1)
            _k32.CloseHandle(self.job)
            self.job = None
        if self.edge is not None:
            if self.edge.poll() is None:
                if os.name == "nt":       # Edge's child processes hold the profile until they go
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.edge.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    try:
                        os.killpg(self.edge.pid, 15)
                    except OSError:
                        self.edge.terminate()
                try:
                    self.edge.wait(10)
                except subprocess.TimeoutExpired:
                    self.edge.kill()
            self.edge = None
        if self.profile:
            if not _remove(self.profile):
                print("harness: could not delete the browser profile %s" % self.profile, file=sys.stderr)
            self.profile = None
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
