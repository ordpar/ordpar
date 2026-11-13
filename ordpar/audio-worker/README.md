# The Ordpar audio Worker

A Cloudflare Worker that serves the site's pronunciation recordings (Amazon Polly's Norwegian voice
Ida, 400,704 MP3 clips) from a private R2 bucket, `ordpar-audio`, on its free `workers.dev`
address, `https://ordpar-audio.ordpar.workers.dev`. The site plays
`https://ordpar-audio.ordpar.workers.dev/<clip name>` ([159](../../docs/decisions.md#d159)),
and puts a play button only where the clip has been uploaded. A Worker is used because it is the
one free way Cloudflare supports for real traffic while ordpar.no's nameservers stay with its
registrar, outside Cloudflare. The receiver, `ordpar/receiver/`, was its model.

The clips are made and uploaded by the private audio pipeline, which is not in this repository. A
clip's name is `ordpar-` and 16 lower-case hex digits, a fingerprint of the text that was sent to
the voice, so a clip's bytes never change under its name.

## Files

| Path | What |
|---|---|
| `src/worker.js` | the Worker: `handle` (GET and HEAD of one clip) and the default export |
| `src/rules.js` | the pure rules: the name pattern, the range parser, the ETag check, the headers, the constants, the forwarding lookup and its redirect |
| `src/forwarding.json` | the bundled forwarding table, superseded name to new name (§ Forwarding superseded names); written by `sync_forwarding.py`, never by hand |
| `sync_forwarding.py` | the sync step: the clip store's `forwarding.json` into `src/forwarding.json`, validated and flattened |
| `test/worker.test.js` | the tests, `bun test` (R2 stood in for by an in-memory bucket with `get` and `head`) |
| `wrangler.jsonc` | the configuration: the R2 binding `AUDIO`, `workers_dev`, Workers Logs off |
| `package.json` | Wrangler pinned (`bun install` puts it in `node_modules/`, git-ignored) |

The constants live in `rules.js`, not in the main module, because workerd treats every export of
the main module as an entry point and refuses to start if one is a string.

## What it answers, and why

| Request | Answer | Why |
|---|---|---|
| `GET` or `HEAD` of a superseded name (in `src/forwarding.json`), with or without `Range` | **302** to `/ordpar-<new>.mp3`, `Cache-Control: public, max-age=86400`, **no bucket call** | the clip was fixed, and a shared Anki deck still names the old one (§ Forwarding superseded names) |
| `GET /ordpar-<16 lower-case hex>.mp3`, no `Range` | **200**, the whole clip | one bucket read |
| the same with `Range: bytes=a-b`, `bytes=a-` or `bytes=-n` | **206**, `Content-Range` and that part | Safari on iPhone and Mac asks for media in ranges and may refuse a file served whole; Edge and Chrome ask `bytes=0-` |
| a range past the end, or `bytes=-0` | **416**, `Content-Range: bytes */<size>` | RFC 9110 § 15.5.17 |
| several ranges (`bytes=0-9,20-29`), an inverted one, another unit, garbage | **200**, the whole clip | RFC 9110 lets a server ignore `Range`; a clip is about 10 KB, so a multipart answer buys nothing |
| `If-None-Match` with the clip's ETag | **304**, no body | simple to do right (a `head`, then a weak compare); it saves bytes, not requests |
| `HEAD` | the same status and headers, no body | |
| a well-formed name not in the bucket | **404**, `Cache-Control: public, max-age=60` | a clip may be uploaded later under that name, so the miss is cached a minute at most |
| any other path (`/`, a listing query, a key with `/`, `%2F`, `..`, upper-case hex, 15 or 17 digits, another extension) | **404**, no body, **no bucket call** | the raw path is checked against the pattern before R2 is touched; the bucket is never listed |
| any other method | **405**, `Allow: GET, HEAD`, no bucket call | |

**Headers on every clip found:** `Content-Type` and `Cache-Control` passed on from the object
(`audio/mpeg` and `public, max-age=31536000, immutable`, set at upload; the same two values if an
object lacks them), `Content-Length`, `ETag` (R2's `httpEtag`, the clip's MD5 in quotes) and
`Accept-Ranges: bytes`. The year-long `immutable` cache is what keeps the account inside its daily
limit: a clip's bytes never change under its name, so a reader's browser fetches each clip once.

**Privacy.** Workers Logs, traces and Logpush are off in `wrangler.jsonc`, as for the receiver;
there is no `console` call. The Worker stores nothing and reads no cookie.

**CORS: `Access-Control-Allow-Origin: https://ordpar.no` on every answer, never `*`.** A plain
`<audio>` element needs no CORS header; the header is there so the site can later read a clip with
`fetch` (a fetch ahead of play) or through `<audio crossorigin>` and the Web Audio API. It costs
nothing in requests: CORS only decides whether a page may *read* the answer, and by then the
request has reached the Worker and been counted. Nothing here stops another site from hotlinking a
clip with its own `<audio>`: a media request carries no `Origin`, and refusing on `Referer` would
still count each request against the daily limit, so neither is attempted. If hotlinking ever eats
the limit, the remedy is outside the Worker (a WAF rule on a custom domain, or the paid plan).

**No Cache API in front of R2.** Every request to a Worker counts against the daily limit whether
or not it is answered from a cache, so `caches.default` would save R2 reads (free up to 10 million
a month) and none of the 100,000 Worker requests a day. Cloudflare's docs also promise working
Cache API operations only to Workers on custom domains
(<https://developers.cloudflare.com/workers/runtime-apis/cache/>, read 1 November 2026). The
browser's own cache, under the year-long header, is the cache that matters.

**Range requests cost two bucket reads** (a `head` for the size and ETag, then a `get` of exactly
that part), so the Worker computes `Content-Range` itself instead of relying on how R2 clamps an
over-long range or fails an out-of-range one. A whole-file GET is one read. Both are R2 Class B
operations, free up to 10 million a month; the Worker's limit (100,000 a day, at most about
3 million a month) is reached first.

## Forwarding superseded names

**Why** ([179](../../docs/decisions.md#d179)). A clip's name is the fingerprint of
what was sent, so a fixed clip gets a **new name**, and the old clip stays in R2 for good. The
site's next build picks up the new names by itself, but an Anki deck already shared cannot be
rebuilt, and it names clips. Without forwarding, its readers would hear the unfixed clip for ever.
So the Worker answers an old name with a redirect to the clip that replaced it.

**The table.** The private audio pipeline compares the clip names that shipped decks were built
from with the current ones and writes the clip store's `forwarding.json`,
`{"pairs": {"<old 16 hex>": "<new 16 hex>"}, …}`. It never forwards a name some line still uses,
and forwards only to an uploaded clip. The Worker carries a copy, `src/forwarding.json`, which
Wrangler bundles into the script: no KV, no D1, no fetch, and nothing read at request time but the
object in memory. The table may be empty.

**The sync step**, from the repository root, after the clip store's table has changed:

```bash
python -I ordpar/audio-worker/sync_forwarding.py <the store's forwarding.json>
```

Without a path it reads `clip_store_forwarding` from the machine's `local-paths.json` (made from
`ordpar/local-paths.example.json`, read by `ordpar/local_paths.py`); `--out` writes
elsewhere than `src/forwarding.json`. It checks every name (16 lower-case hex, the hex of `NAME` in
`rules.js`), refuses a pair that forwards a name to itself, **flattens chains** (`a -> b` and
`b -> c` give `a -> c` and `b -> c`, so a reader gets one redirect, never two), refuses a cycle and
names it, writes `src/forwarding.json` only when its text changes, and prints the pairs read, how
many it flattened, and whether it wrote. A refusal exits 1 and leaves the old file as it was. The
new file is committed with the Worker and reaches readers at the next deploy.

**The redirect.** For GET or HEAD of a valid name in the table, the Worker answers **302** with
`Location: /ordpar-<new>.mp3` (relative, so the same Worker answers it), before R2 is touched, so a
superseded name costs no bucket operation. It carries `Cache-Control: public, max-age=86400` and
the headers every answer carries (`Access-Control-Allow-Origin: https://ordpar.no`, the exposed
headers, `nosniff`); a `Range` or `If-None-Match` on the old name changes nothing, since the new
name answers those. The table is followed once: a target that is not a clip name, is the old name
itself, or is itself in the table is ignored, and the old clip is served as before, so even a
hand-made table cannot make a loop. A name not in the table is served exactly as before.

**Why 302, not 307.** Only GET and HEAD are ever redirected, and every client keeps those methods
across either status, so 307's guarantee to keep the method buys nothing here; 302 is the oldest
temporary redirect and the one every media stack, WebView and download tool has followed longest.
Both are temporary, which is the point: **never 301 or 308**, which browsers keep for good, so a
later fix of the same text (the new clip itself superseded) could never move a reader on. A day's
cache is the compromise: a deck playing the same clip again within the day may not ask again, and a
later fix reaches it within a day of its deploy. Whether a given media stack honours the redirect's
cache has not been tested.

**The cost in requests.** A superseded clip played the first time costs two Worker requests (the
redirect, then the new clip) against the shared 100,000 a day; after that the new clip is in the
browser's year-long cache.

**What it cannot reach.**

* A device that already fetched the old clip keeps it in its cache for up to a year
  (`max-age=31536000, immutable`, set at upload) and never asks the Worker, so it never sees the
  redirect. Nothing on the server can change that.
* A clip packaged inside an Anki deck is played from the Anki collection's own media by its file
  name and never asks the Worker either; only the clips a deck plays from the Worker can be
  forwarded.
* The site needs none of this: its next build names the new clips.

**Size.** The table is bundled into the script. Measured with `npx wrangler deploy --dry-run` on
synthetic tables of random names: no pairs 5.11 KiB (gzip 1.94 KiB), 5,000 pairs 216.34 KiB (gzip
100.59 KiB), 20,000 pairs 849.98 KiB (gzip 387.82 KiB); the Worker without forwarding was 4.04 KiB
(gzip 1.53 KiB). Check against Cloudflare's script size limit for the plan before a large table
ships.

## The daily limit is shared

The Workers free plan allows **100,000 requests a day for the whole account**, so this Worker and
the receiver share it; past it, both fail with Cloudflare's Error 1027 until midnight UTC (no bill;
<https://developers.cloudflare.com/workers/platform/limits/#daily-requests>). Each clip played is
at least one request (an inflection-table row of five forms is five), and Safari may make two or
three range requests for one clip. To see the count, open **Workers & Pages** in the Cloudflare
dashboard and select each Worker in **Overview**
(<https://developers.cloudflare.com/workers/observability/metrics-and-analytics/>).

## Tests

`bun test` here, or `python ordpar/tests/test_ordpar_audioworker159.py` from the repository root
(part of every test run; it also checks `wrangler.jsonc`, and skips the bun part, saying why, when
bun is missing). No network and nothing installed. The sync step's own tests are
`python ordpar/tests/test_ordpar_forwarding179.py` (synthetic tables in a temporary folder; no
clip store is read).

## A local run

`bun x wrangler dev` cannot answer under bun (see `ordpar/receiver/README.md`, on Wrangler), so the
local run uses Node, first on `PATH` for the command only, with the Cloudflare variables removed
and the state outside the repository. From this folder, after `bun install`:

```bash
NODE=<a Node folder>
SCRATCH=<a scratch folder>
# seed the local bucket with a clip, with its two headers as at upload
env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID PATH="$NODE:$PATH" npx wrangler r2 object put \
  ordpar-audio/ordpar-ac06dc7ae33bbab9.mp3 --file <a clip> --content-type audio/mpeg \
  --cache-control "public, max-age=31536000, immutable" --local --persist-to "$SCRATCH"
# serve it on http://127.0.0.1:8787
env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID PATH="$NODE:$PATH" npx wrangler dev --local \
  --port 8787 --ip 127.0.0.1 --persist-to "$SCRATCH"
curl -s -D - -o /dev/null -H "Range: bytes=0-99" http://127.0.0.1:8787/ordpar-ac06dc7ae33bbab9.mp3
```

`wrangler dev` writes a `.wrangler/` folder here (git-ignored); delete it afterwards.

## Deploying

1. **The token.** A Cloudflare Account API token with **Workers Scripts · Write** and **Account
   Settings · Read** on the account, and **Workers R2 Storage Bucket Item Read** on the bucket
   alone. Keep it in an environment variable, never in a file here, and pass it for the one
   command: `CLOUDFLARE_API_TOKEN="$<your variable>" …`. With only Bucket Item Read, `deploy` warns
   that it cannot check the bucket exists ("Skipping automatic provisioning") and goes on; the
   binding works.
2. **The forwarding table**, if the clip store's table changed: run the sync step (above) and
   commit `src/forwarding.json` if it says `written`. An `unchanged` line means the deploy changes
   nothing in the table.
3. **Run Wrangler under Node, not `bun x`**: under bun, `whoami` and `deploy` exit silently with
   nothing done. With Node first on `PATH` and `CLOUDFLARE_ACCOUNT_ID` dropped from the
   environment: `npx wrangler whoami` (check the account), then `npx wrangler deploy`.
4. **The address.** An account with no workers.dev subdomain gets one at its first deploy, named
   after the Worker; it can be changed on the dashboard's "Change account subdomain" page. Every
   Worker on the account is then `<worker>.<subdomain>.workers.dev`; Ordpar's subdomain is
   `ordpar`. Renaming the *Worker* in its own settings is a different thing: it changes the Worker's
   name, and `wrangler.jsonc`'s `"name"` would then make a second Worker at the next deploy.
5. In the dashboard, open the Worker under **Workers & Pages** and check that Workers Logs
   (Observability) are off; `wrangler.jsonc` deploys them off.
6. **Check one clip:**
   ```bash
   curl -s -D - -o /dev/null -H "Range: bytes=0-99" https://ordpar-audio.ordpar.workers.dev/ordpar-ac06dc7ae33bbab9.mp3
   ```
   Expect `206`, `content-range: bytes 0-99/9980`, `content-type: audio/mpeg` and
   `cache-control: public, max-age=31536000, immutable`. Without the `-H` line, `200` and
   `content-length: 9980`. A made-up name (`ordpar-0000000000000000.mp3`) gives `404`. Once the
   table holds pairs, an old name from it gives `302`, `location: /ordpar-<new>.mp3` and
   `cache-control: public, max-age=86400`.
