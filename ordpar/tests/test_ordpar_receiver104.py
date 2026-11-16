# -*- coding: utf-8 -*-
"""Site decisions 26, 62, 104 (2026-10-23): the receiver, `ordpar/receiver/` — a Cloudflare Worker.
Brief: `docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-receiver-26-62-104-2026-10-23.md`
§ 1, § 4. Its tests are `ordpar/receiver/test/receiver.test.js`, run here under `bun test` with no
network (they need bun itself, for `bun:sqlite`; skipped, with the reason printed, without it). They
need nothing installed: Wrangler (`ordpar/receiver/node_modules`) is not used.

What they pin (the file's own `describe` blocks):

* **validation** (`src/rules.js` `parseEvent`): the five event types, each with exactly its
  fields, any other dropped; 62's rule — a query with a digit (any script's) or over 40
  characters drops the event (204, nothing stored); anything not an event is a 400; a view's path
  one of the site's own, anything else stored as `/other`; the query and the word chosen stored
  lower-cased (decisions 104, 2026-10-23); the origins (ordpar.no; 127.0.0.1 only with `ALLOW_LOCAL`);
  the UTC day and minute;
* **the bot lists** (layers 2 and 5): ordinary browsers pass, crawlers, headless browsers and an
  empty browser name do not; the big clouds are data centres, Norwegian home and mobile networks
  and the privacy relays (Cloudflare, Akamai, Fastly) are not; each list names its source and
  commit; the crawler check stays well inside the 10 ms CPU budget;
* **the daily code** (104): one code per address and browser a day, another the next day; the
  HMAC-SHA-256 vector; the secret made once, expiring five minutes after its day, yesterday's
  deleted and tomorrow's made by the daily run;
* **the endpoint**: 204 with no body and CORS for ordpar.no; a view stored as day, minute, path and
  code, the address and browser name nowhere in the database; search events and installs with no
  code (and no secret read); search lines in no order of arrival — no rowid, a random 32-hex key,
  the table in the key's order (decisions 104); a request with `Sec-GPC: 1` answered 204 and nothing
  stored (decisions 104); bots and dropped events stored nowhere; anything else a 400 with no body; a
  body over 512 bytes refused in bytes, chunked included;
* **the daily run** (in SQL, as on D1): totals for every finished day not yet totalled and never
  doubled; layer 6 — a code with 100 views inside 10 minutes (a sliding window) left out of the
  totals, its lines kept; view lines past 7 days deleted (`VIEW_DAYS`, 104 as revised
  2026-10-23), their totals made first and kept; search lines past 90 days kept as counts only for
  strings seen at least 3 times;
* **the configuration** (`wrangler.jsonc`): Workers Logs, traces and Logpush off; one daily Cron
  Trigger; local origins off; the two bindings; no `console` call in the Worker.

Since site decisions 166 (2026-11-05) the same run takes `test/report.test.js` too: `POST /report`
accepted and refused (origin, method, size, the trap, the rate), the stored fields with no address
or browser name, Robin's `GET /reports` and `POST /reports/<id>/done` with and without the token,
Done deleting the reply address; and the counting's own switch `COUNTING` ("0" as configured: `/e`
not served, no totals). `test/receiver.test.js` runs with the counting on.
"""
import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECEIVER = os.path.join(ROOT, "ordpar", "receiver")


@unittest.skipUnless(shutil.which("bun"), "bun is not on PATH (the receiver's tests use bun:sqlite)")
class ReceiverTests(unittest.TestCase):

    def test_bun_test(self):
        res = subprocess.run([shutil.which("bun"), "test", "./test/"], cwd=RECEIVER,
                             capture_output=True, timeout=180)
        out = (res.stdout + res.stderr).decode("utf-8", "replace")
        self.assertEqual(res.returncode, 0, out)
        self.assertIn(" 0 fail", out)
        self.assertNotIn(" 0 pass", out)


if __name__ == "__main__":
    unittest.main()
