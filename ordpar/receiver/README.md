# The Ordpar receiver

A Cloudflare Worker, on its free `workers.dev` address, that receives three things from the site:
the counting's events (page views, offline-app installs and search events), readers' reports of
mistakes (`POST /report`) and the readers' survey answers (`POST /survey`). What it collects, the
daily code, the bot layers, retention and how to read the numbers are in
[`../docs/receiver.md`](../docs/receiver.md). The page's side is `ordpar/site/events.js` (the
counting), `ordpar/site/report.js` and `ordpar/site/survey.js`; the words for readers are in
`ordpar/privacy.md`.

## Files

| Path | What |
|---|---|
| `src/worker.js` | the Worker: `POST /e` (`handle`, `store`), `POST /report` (`handleReport`), `POST /survey` (`handleSurvey`), the operator's `GET /reports`, `POST /reports/<id>/done` (`handleReports`), `GET /surveys` and `POST /surveys/<id>/done` (`handleSurveys`), and the daily run (`daily`, a Cron Trigger); the counting's switch `COUNTING` |
| `src/reports.js` | what a report may carry (`parseReport`; the name to credit, `cleanCredit`), its limits, the total cap per hour (`REPORTS_PER_HOUR`), the token check (`authorised`) |
| `src/survey.js` | what a set of survey answers may carry (`parseSurvey`, `cleanFollow`) and its limits; the answers share the reports' total cap |
| `src/rules.js` | pure rules: what an event may carry, what is dropped, the day and minute, the origins, the constants (retention, thresholds) |
| `src/code.js` | the daily code: HMAC-SHA-256 of the IP address and browser name under the day's secret |
| `src/secret.js` | the daily secret in Workers KV: made, expired, rotated |
| `src/bots.js` | bot layers 2 and 5: the crawler list and the data-centre list |
| `src/sql.js` | every statement, including the daily totals (layer 6) and the retention |
| `migrations/0001_init.sql` | the counting's tables |
| `migrations/0002_reports.sql` | the reports and the total cap's counts per hour |
| `migrations/0003_surveys.sql` | the survey's answers, a table of their own (the total cap is the reports' `report_hours`) |
| `data/crawlers.json`, `data/datacentre-asns.json` | the two kept lists, each with its source, the upstream commit it was taken from, and its MIT licence beside it |
| `tools/refresh-lists.mjs` | remakes the two lists from their upstream files |
| `tools/local.mjs` | a local stand-in (below) |
| `test/receiver.test.js` | the counting's tests, run with `COUNTING` on |
| `test/report.test.js` | the reports' tests: accepted, refused (origin, method, size), the trap, the total cap, the name to credit, the stored fields, reading with and without the token, closing deleting the address and the name; with the counting off, `/e` not served and no totals |
| `test/survey.test.js` | the survey's tests: what a set of answers may carry, accepted and refused, the trap, the same total cap as reports (both kinds counted together), nothing about the sender read or stored, `GET /surveys`, and Done deleting the follow-up address or name; the page's limits (`ordpar/site/survey.json`) held to the receiver's |
| `wrangler.jsonc` | the configuration: Workers Logs off, the Cron Trigger, the bindings, `COUNTING` `"0"` |
| `package.json` | Wrangler pinned |

**A schema change is a new numbered migration.** D1 records the migrations it has applied, so a
file already applied to a database must not be edited.

## Tests

`bun test` here, or `python ordpar/tests/test_ordpar_receiver104.py` from the repository root
(part of every test run). No network and nothing installed: the tests import the Worker's own
modules and run its SQL under `bun:sqlite`, with D1 stood in for by `bun:sqlite` and KV by a map.

## The two switches

**The counting** is off unless both are set:

- on the Worker, `COUNTING` in `wrangler.jsonc` `vars`. With `"0"` (as configured), `POST /e` is
  not served (it answers 400 like any unknown path and stores nothing), and the daily run makes no
  totals and makes or reads no secret; it only deletes the total cap's counts of past hours. The
  KV binding `SECRETS` is left out of `wrangler.jsonc` while the counting is off (the commented
  block at the file's end);
- on the site, `events.js`'s `var RECEIVER`: empty, and the page sends nothing.

**Reports** are on when `ordpar/sitegen/chrome.py` `REPORT_RECEIVER` holds the Worker's address
plus `/report`. It is the one place the address is set. Empty: no "Suggest a correction" button
anywhere, no `/thanks/` page (nor its sitemap and offline entries), and no paragraph on reports in
About or the published README. The build writes it into `report.js`'s `var REPORT_RECEIVER = ''`
(never edited by hand; the build refuses a changed line). It is separate from `events.js`'s
`RECEIVER` and from `chrome.PRIVACY`. For one build only, the environment variable
`ORDPAR_REPORT_RECEIVER` overrides it (below); `python ordpar/deploy.py prepare` refuses to publish
any build whose address is not `https://` on a public name.

**The survey** is on with `SURVEY = True` in `ordpar/sitegen/chrome.py`; its address is the
reports' with `/survey` (`chrome.survey_receiver()`). For one build, `ORDPAR_SURVEY=1` turns it on.

What reports and survey answers keep is in [`../docs/receiver.md`](../docs/receiver.md). In
short: nothing about the sender is read, not the IP address and not the browser's name; junk is
kept out by the trap field and a total cap of 30 an hour from everyone together (one count per
hour, deleted when the hour is over). **Reports and the survey need no KV**: D1 only.

## Wrangler: use Node, not bun

`package.json` pins Wrangler; `bun install` puts it and its runtime, about 170 MB, in
`node_modules/` (git-ignored). Under bun (tried with bun 1.3.14 and Wrangler 4.152.0):

- `bun x wrangler --version` and `bun x wrangler d1 migrations apply ordpar-events --local` work;
- `bun --bun …` fails at once ("Wrangler does not support the Bun runtime");
- **`bun x wrangler dev` starts but cannot answer**: every request gets a 503, because Bun's
  `fetch()` ignores the undici `dispatcher` that Miniflare routes requests through
  (oven-sh/bun#39247);
- `whoami` and `deploy` exit silently with nothing done.

So run Wrangler under Node (a portable Node first on `PATH` for the command is enough). Keep the
Cloudflare variables out of a local run's environment and its state outside the repository:

```bash
env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID npx wrangler d1 migrations apply ordpar-events --local --persist-to <scratch>
env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID npx wrangler dev --local --var ALLOW_LOCAL:1 --test-scheduled --persist-to <scratch>
# then POST events to http://127.0.0.1:8787/e with Origin: http://127.0.0.1:<port>,
# and GET http://127.0.0.1:8787/__scheduled to run the daily work
```

`ALLOW_LOCAL` `"1"` lets pages on `http://127.0.0.1:<port>` send; it is only for local tests. A
headless browser's own User-Agent says `HeadlessChrome`, which is on the crawler list: its events
are answered 204 and dropped. Give it a normal one (`--user-agent=…`) to see them stored.

## The local stand-in

`tools/local.mjs` serves the Worker's own `handle` with bun on `127.0.0.1`, with D1 stood in for by
`bun:sqlite` (every migration applied) and KV by a map. It is not Cloudflare: no workerd, no
`request.cf`, no `CF-Connecting-IP`. It is for the browser tests of the report button and the
survey, and for trying a reading page before a deploy.

```bash
cd ordpar/receiver && bun tools/local.mjs --port 8787 --db <file.sqlite>
# a report by hand (the stand-in allows a local origin):
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8787/report -H "Origin: http://127.0.0.1:1" \
  --data '{"id":1000,"text":"A test report.","category":"other","reply":null,"build":null}'
```

Its options: `--port` (default 8787), `--db` (a SQLite file; in memory without it), `--counting`
(serve `/e`), `--stay` (keep running when standard input closes, for a run in the background), and
`--lan` with `--host` (answer on the local network, taking reports only from the origins listed in
`LAN_ORIGINS` in the script: change them to your own machine's address). The token for `GET /reports` is the
environment's `REPORTS_TOKEN`, or `local-reports-token-0000` when that is unset; the reading
endpoints answer the local machine only.

**Trying the form before a deploy.** Build the site once with the stand-in's address, without
changing any committed file:

```bash
ORDPAR_REPORT_RECEIVER=http://127.0.0.1:8787/report ORDPAR_SURVEY=1 python ordpar/build_site.py --mirror <bm-articles.jsonl> --all
python ordpar/build_index.py --mirror <bm-articles.jsonl> --freq <1-gram file>
python ordpar/build_offline.py
python -m http.server 8098 --directory ordpar/out
```

`build_site.py` prints `reports: ON for this build only, receiver …`, and `reports_166` in the build's
`build.json` records it. Open the site as `127.0.0.1`, not `localhost` (another origin gets 400),
and press "Suggest a correction" at an article's foot. A browser that installed the offline copy
from the same address may show the build before; removing that copy shows this one. Afterwards,
**build again without `ORDPAR_REPORT_RECEIVER`** before any deploy; `deploy.py prepare` refuses
such a build in any case, since its address is `http://`.

## Deploying, with the counting off

From this folder, Wrangler under Node, `CLOUDFLARE_ACCOUNT_ID` dropped from the environment and a
Cloudflare API token in `CLOUDFLARE_API_TOKEN` (never printed). For a run with no terminal, set
`CI=1` (else `migrations apply` asks before applying).

1. `npx wrangler whoami`: check it is the right account.
2. `npx wrangler d1 create ordpar-events --jurisdiction=eu`, and copy the printed `database_id`
   into `wrangler.jsonc`. `--jurisdiction=eu` keeps the data in the EU, as the privacy page says;
   it can be set only at creation.
3. No KV namespace: reports and the survey use none.
4. `npx wrangler d1 migrations apply ordpar-events --remote`: all three migrations. The counting's
   tables stay empty while `COUNTING` is `"0"`.
5. Check that `wrangler.jsonc` has `"COUNTING": "0"`, then `npx wrangler deploy`. It prints the
   address, `https://ordpar-receiver.<subdomain>.workers.dev`. Check in the dashboard that the
   Worker's Observability (Workers Logs) is off; `wrangler.jsonc` deploys it off.
6. **The token for reading:** a long random value (32 characters or more; the Worker refuses one
   under 16), then `npx wrangler secret put REPORTS_TOKEN`, pasting it when asked. Put the secret
   after the first deploy. Never write it into the repository.
7. Checks that store nothing:
   - `curl -s -o /dev/null -w "%{http_code}\n" -X POST <address>/e -H "Origin: https://ordpar.no" --data '{"type":"view","path":"/"}'`
     answers `400` (the counting is off);
   - `curl -s -o /dev/null -w "%{http_code}\n" <address>/reports` and `…/surveys` answer `401` (no
     token);
   - `curl -s -o /dev/null -w "%{http_code}\n" -X POST <address>/survey -H "Origin: https://ordpar.no" --data '{"answers":{}}'`
     answers `400` (nothing answered).
8. The site: `<address>/report` into `ordpar/sitegen/chrome.py` `REPORT_RECEIVER`, and
   `SURVEY = True`; then the site's full build and deploy. A first report through the form, then
   closing it, checks the whole way.

**A later migration** (as `0003_surveys.sql` was): `npx wrangler d1 migrations list ordpar-events
--remote` should list only the new file as not yet applied; then
`CI=1 npx wrangler d1 migrations apply ordpar-events --remote` (trying it with `--local` first does
no harm), then `npx wrangler deploy`. Apply a migration before deploying the Worker that uses it.

## Turning the counting on

1. `npx wrangler kv namespace create ordpar-secrets --jurisdiction=eu`, and put the binding
   `SECRETS` back into `wrangler.jsonc` (the commented block at its end) with the printed `id`.
2. `"COUNTING": "1"` in `wrangler.jsonc`, then `npx wrangler deploy`.
3. A check that stores nothing:
   `curl -s -o /dev/null -w "%{http_code}\n" -X POST <address>/e -H "Origin: https://ordpar.no" --data '{"type":"view"}'`
   answers `400`; the same with `--data '{"type":"hit","query":"x1"}'` answers `204`
   (dropped by the digit rule).
4. The site: the address plus `/e` into `ordpar/site/events.js` (`var RECEIVER = '…'`), with the
   privacy page's section on the counting ready (`chrome.PRIVACY`); then the site's full build and
   deploy.
5. After the first 00:05 UTC: the first row of `daily_views` (see
   [`../docs/receiver.md`](../docs/receiver.md), on reading the numbers), and
   `npx wrangler kv key list --binding SECRETS --remote` showing today's and tomorrow's secrets only.
