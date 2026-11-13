# -*- coding: utf-8 -*-
"""Site 159 (2026-11-01): the audio Worker, `ordpar/audio-worker/` — a Cloudflare Worker serving the
pronunciation clips from the private R2 bucket `ordpar-audio` (audio decisions 12, 15, 24).
Brief: `docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-audio-worker-159-2026-11-01.md`.
Its tests are `ordpar/audio-worker/test/worker.test.js`, run here under `bun test` with no network
(R2 stood in for by an in-memory bucket with the binding's `get` / `head`); skipped, with the reason
printed, without bun. Wrangler (`ordpar/audio-worker/node_modules`) is not used.

What they pin:

* **the name**: exactly `ordpar-` + 16 lower-case hex + `.mp3` (`scripts/audio/clips.py`
  `name_for_sent`); upper-case hex, 15 or 17 digits, other extensions, paths with `/`, `..` or
  `%2F`, the root and a listing query refused with a 404 and no bucket call;
* **the methods**: GET and HEAD; anything else a 405 with `Allow: GET, HEAD`, no bucket call;
* **the whole file**: 200, every byte, `Content-Type: audio/mpeg`, the year-long immutable
  `Cache-Control`, `Content-Length`, `Accept-Ranges: bytes`, an `ETag`; the object's own headers
  passed on, the two fallbacks when it has none; HEAD with no body;
* **ranges**: `bytes=a-b`, `bytes=a-`, `bytes=-n` a 206 with `Content-Range` and exactly those bytes
  (an end past the file clamped, a suffix longer than the file all of it); out of range and
  `bytes=-0` a 416 with `Content-Range: bytes */<size>`; several ranges, an inverted one, another
  unit or garbage ignored (200, the whole file); `If-Range` honoured;
* **304** for a matching `If-None-Match` (strong, weak, in a list, `*`), before any Range;
* **a missing clip**: 404 cached a minute; `Access-Control-Allow-Origin: https://ordpar.no` on
  every answer, never `*`; no cookie read or set;
* **the configuration** (`wrangler.jsonc`, in the bun tests and again here): Workers Logs, traces and
  Logpush off; `workers_dev` on, preview addresses off; the one R2 binding `AUDIO` to the bucket
  `ordpar-audio`; no `console`, `list`, `put` or `delete` call in the Worker.
"""
import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKER = os.path.join(ROOT, "ordpar", "audio-worker")


def _config():
    with open(os.path.join(WORKER, "wrangler.jsonc"), encoding="utf-8") as f:
        text = f.read()
    return json.loads(re.sub(r"(?m)^\s*//.*$", "", text))


class AudioWorkerConfig(unittest.TestCase):

    def test_wrangler_jsonc(self):
        cfg = _config()
        self.assertEqual(cfg["name"], "ordpar-audio")
        self.assertEqual(cfg["main"], "src/worker.js")
        self.assertIs(cfg["workers_dev"], True)
        self.assertIs(cfg["preview_urls"], False)
        self.assertEqual(cfg["r2_buckets"], [{"binding": "AUDIO", "bucket_name": "ordpar-audio"}])
        obs = cfg["observability"]
        self.assertIs(obs["enabled"], False)
        self.assertIs(obs["logs"]["enabled"], False)
        self.assertIs(obs["logs"]["invocation_logs"], False)
        self.assertIs(obs["traces"]["enabled"], False)
        self.assertIs(cfg["logpush"], False)

    def test_wrangler_pinned(self):
        with open(os.path.join(WORKER, "package.json"), encoding="utf-8") as f:
            pkg = json.load(f)
        self.assertRegex(pkg["devDependencies"]["wrangler"], r"^\d+\.\d+\.\d+$")


@unittest.skipUnless(shutil.which("bun"), "bun is not on PATH (the audio Worker's tests run under bun test)")
class AudioWorkerTests(unittest.TestCase):

    def test_bun_test(self):
        res = subprocess.run([shutil.which("bun"), "test", "./test/"], cwd=WORKER,
                             capture_output=True, timeout=180)
        out = (res.stdout + res.stderr).decode("utf-8", "replace")
        self.assertEqual(res.returncode, 0, out)
        self.assertIn(" 0 fail", out)
        self.assertNotIn(" 0 pass", out)


if __name__ == "__main__":
    unittest.main()
