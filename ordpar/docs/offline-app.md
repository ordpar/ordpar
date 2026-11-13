# The offline copy: bundles, manifest, service worker, download and updates

This doc describes how Ordpar works as an installable web app that can keep the whole dictionary
on a device. The code it covers:

| File | What it does |
|---|---|
| `ordpar/build_offline.py` | packs the built site into the offline copy's files, `out/offline` |
| `ordpar/root/sw.js` | the service worker, served as `/sw.js`: routes requests to the stored copy |
| `ordpar/site/offline.js` | the download, the updates and the update note, drawn in Settings |
| `ordpar/site/install.js` | the offer to install the app (§ 11) |
| `ordpar/root/manifest.webmanifest` | the app manifest |
| `ordpar/build_icons.py` | draws the app's icons |
| `ordpar/sitegen/head.py` | the head lines every page carries, the robots line and the launch switch (§ 7) |

The decision behind it is [61](../../docs/decisions.md#d61); the install offer is
[68](../../docs/decisions.md#d68), the bundle size [92](../../docs/decisions.md#d92), the
update rules [94](../../docs/decisions.md#d94).

**The app is the site.** It serves the same pages at the same addresses, plus a service worker and
an app manifest, so Chrome offers *Install* and the home-screen icon opens the site in its own
window. A visitor who never presses "Keep the whole dictionary on this device" downloads nothing
extra and sees no change; offline, they get a small notice in place of the browser's error page.

## 1. The build

```
python ordpar/build_site.py --mirror <bm-articles.jsonl> --all       # the pages, out/sw.js, out/manifest.webmanifest
python ordpar/build_index.py --mirror <bm-articles.jsonl> --freq <1-gram file>   # the index and the shell pages
python ordpar/build_offline.py                                        # out/offline/
python ordpar/build_offline.py --verify                               # every bundle read back against out/
```

In the public repository the mirror is `data/bokmalsordboka/bm-articles.jsonl` (joined first with
`python ordpar/data_parts.py join data/bokmalsordboka`) and the 1-gram file is under
`data/frequency/`, with `ORDBOK_DATA_DIR=data` set; see `ordpar/docs/build-site.md`.

`build_offline.py` is a step of its own, not a stage of `build_index.py`. It reads what both builds
wrote (the pages, `out/site`, `out/index`, the shell pages) and nothing else: no mirror and no
library. So it can be re-run alone after a hand edit or a partial rebuild.

| Flag | What it does |
|---|---|
| `--out DIR` | the built site (default `ordpar/out`) |
| `--per N` | pages to a bundle (default 500) |
| `--rechunk` | ignore the previous manifest's bundle boundaries (§ 2) |
| `--verify` | write nothing; read every bundle back against `out/` |
| `--json PATH` | also write the counts to this file |

**`--verify`** checks every page: each is in exactly one bundle, equals its built file with the
tokens blanked (§ 2) byte for byte, and restores to the built file itself. Every other file must
equal its file and its hash. Over 94,304 pages it takes about 24 s.

**Sizes.** As built on 31 October 2026: 189 article bundles of 500 pages, and 115 index and shell
packs; the download (bundles, packs and manifest) was **34.1 MB** (34,125,004 B). The manifest
itself is about 490 KB raw and about 95 KB gzipped on the wire. A build from scratch takes about
45 s; when only the shell pack changes, the unchanged packs are not recompressed. The English
search's files ([148](../../docs/decisions.md#d148)) add about 1.45 MB to the download: 27
packs of 1.15 MB and 26 packs of their tails files, 295 KB.

## 2. The bundles and packs

`out/offline` holds:

    bm-en-<first>.<hash>.bin   the article pages, whole, in numeric id order, 500 to a bundle
    index-<key>.<hash>.bin     out/index/: the shard files, their -top files, the snip/ files and
                               the headwords/ file of one letter key (`h`, `aa`, `misc` …): what a
                               query for a word in that letter reads together
    tails-<key>.<hash>.bin     out/index/tails/, by the first key of the file name
    en-<letter>.<hash>.bin     out/index/en/<letter>.json, the English search's file of one letter
                               (a–z and misc, 27 packs), so a change to the English glosses never
                               touches a Norwegian pack, nor the reverse
    en-tails-<key>.<hash>.bin  out/index/en/tails/, the English tails files (the similar English
                               words past the first letter), by the first key of the file name
    index-meta.<hash>.bin      index.json, translated.json, random.json (Random word's pool),
                               random-en.json (the English draw's pool), labels.json (the form
                               labels' words)
    shell.<hash>.bin           the shell pages, /manifest.webmanifest and everything under
                               out/site/ (the scripts and style sheets among them, so the worker
                               serves them offline like any other file)
    manifest.json, version.json

The shell pages are those `SHELL_PAGES` in `ordpar/build_offline.py` names: `/`, `/bm-en/`,
`/about/`, `/help/`, `/coming/`, `/more/`, `/changes/`, `/dictionary-changes/`, `/deck-changes/`,
`/favourites/`, `/history/`, `/settings/` and `/404.html`; and, only where the build wrote them,
`/privacy/` and `/thanks/` (`OPTIONAL_PAGES`). The link-preview picture under `out/site/og` is left
out: no page shows it.

**Word pages and form pages are not in the copy**
([117](../../docs/decisions.md#d117)). There are about 25,000 of them, some 4 KB each, about
100 MB together, and each is only a frame around a search the copy can already answer. When a copy
is kept, a navigation to `/bm-en/<word>/` gets the held 404 shell, online too (§ 4), and the shell
does what the word page does: it runs the word's search under the reader's settings, recorded in
History when the address carries a search's mark (`ordpar/site/lookup.js`
`ordparSearch.wordPage`). Its status is 404, which a reader does not see. The result is the same
articles in the same order, with the same text, title, address and History entry as the word page.
Answering from the copy online as well means the host never sees the word in the address
([170](../../docs/decisions.md#d170)).

**The bundle size, 500 pages** ([92](../../docs/decisions.md#d92)). The worker's unpack of
one article (read from Cache Storage, gunzipped, the header read, the page cut out) was measured
in headless Edge, the median of five bundles, on a desktop computer and with the page's CPU slowed
4× as a stand-in for a phone:

| pages a bundle | bundles | the bundles' download | largest, unpacked | unpack, computer | unpack, CPU ×4 |
|---|---|---|---|---|---|
| 250 | 378 | 20.01 MB | 1.1 MB | 4–6 ms | 12–17 ms |
| **500** | **189** | **19.69 MB** | **2.1 MB** | **6–9 ms** | **23–26 ms** |
| 1,000 | 95 | 19.53 MB | 4.2 MB | 10–15 ms | 48–49 ms |
| 2,000 | 48 | 19.43 MB | 8.2 MB | 24–27 ms | 89–94 ms |

The unpack time follows the size. The download grows by only 1.3 % at 500, because gzip's window
is 32 KB, so a small bundle compresses as well as a large one; at 250 it grows by 3 %, and the
fixed costs (a request, a Cache Storage entry, a manifest line each) start to cost more than the
unpack saves. 500 quarters the cold first open of an article and the memory a bundle holds, for
0.26 MB and 141 more files than 2,000.

**A pack** is gzip (level 9, mtime 0, so the same content gives the same bytes) of: the ASCII
`OPK1`, a little-endian uint32 header length, the JSON header `{"keys": [...], "offsets": [...]}`
(n keys, article ids as numbers and file paths as strings, and n + 1 offsets into the body), then
the bodies back to back. **One page is found from the header** after the unpack, never by a scan.
The files are named `.bin` so that no server labels them `Content-Encoding: gzip` (the browser
would then hand the worker the unpacked bytes). The worker and the download treat them as opaque
bytes, checked against their SHA-256.

**A name carries its hash** (the first 16 hex digits of the file's SHA-256), so an unchanged
bundle keeps its name from build to build and an update fetches exactly the names it lacks. A pack
whose unpacked content is unchanged keeps its file without being recompressed.

**Boundaries.** A bundle's range runs from its `first` up to the next bundle's `first`. A new build
keeps the previous manifest's boundaries, so an article added or removed changes only its own
bundle (counting 500 from the lowest id would shift every later bundle by one page). A bundle that
grows past 1.5 × `--per` is split; an emptied one is dropped. `--rechunk` starts afresh. Without a
previous manifest (a clean `out/`) the chunking is the same as `--rechunk`, which is
deterministic.

**The frame tokens.** Every article page links its scripts and style sheets with a `?v=<hash>`
(`page.asset`), so editing any of them would change every page, and every bundle with it: a whole
new download for every installed copy. So a page is stored with those tokens **blanked**:
`/site/<file>?v=<hash>` becomes `/site/<file>?v=*` where the hash is the shipped file's current
one. A page today links three such files: `/site/theme.js`, `/site/ordpar.css` and
`/site/ordpar.js`. The worker puts the hash back from the manifest (`files[path].hash[:10]`) when
it serves the page, so a page served offline is **byte for byte** the file the host serves. A
token that does not match (a page left over from an older partial build) is kept as it is, so the
restore is always exact.

Pages once carried a build stamp comment, `<!-- ordpar build: … -->`, holding the repository's
commit; the bundles blanked it too (to `<!-- ordpar build: * -->`, where it was the build's
majority stamp). Article pages no longer carry one. The mechanism is kept: the manifest's `stamp`
is the majority stamp of the pages, or the `stamp` in `out`'s `build.json` when no page has one
(`majority_stamp`); the build id covers it; and the worker still restores a stamp into an older
page that has the token and leaves every other page alone. The About page, in the shell pack,
keeps its comment.

**What still touches every bundle**: a change to the frame of the article page, that is
`page.py`'s `render` and its post-passes (`page.finish`, `ordpar/sitegen/slim.py`);
`ordpar/sitegen/chrome.py` (every page's header and footer, with their strings from
`ordpar/site/strings/en.json` and the credit); the default colour scheme (`ordpar/sitegen/colours.py`,
the theme-color line); the inline head script; the list of `<link>` and `<script>` tags (adding or
removing a file); the chrome strings an article page carries (`search_placeholder`, `credit`,
`copy_link`, `share`, the untranslated caption and note, the title suffix); the meaning of the
`<html>` attributes; the head lines of § 7; turning the launch switch off (§ 7); and any change to
how the article itself is rendered (`ordpar/sitegen/article.py`, the deck's renderer `ordbok_gen.py`,
the small article). Of these, the article's rendering and the strings change most often. Each such
change costs an installed copy one full download of the bundles, fetched in the background at the
next opening. A content update touches only the bundles holding the changed articles. A change to
a script or style sheet behind its `?v=` touches the shell pack only.

## 3. The manifest

`manifest.json` in `out/offline`:

```json
{"format": "ordpar-offline", "version": 1, "build": "<16 hex>", "built_at": "…", "total": <bytes>,
 "per": 500, "stamp": "ordpar build: …", "tokens": {"asset": "?v=*", "stamp": "ordpar build: *"},
 "pages": 94304,
 "bundles": [{"name", "first", "last", "count", "size", "sha256", "raw", "raw_size"}, …],
 "packs":   [{"name", "group", "count", "size", "sha256", "raw", "raw_size"}, …],
 "files":   {"/site/shell.js": {"size", "hash", "pack": "<group>"}, "/": {…}, "/index/h.json": {…}, …}}
```

- `build` is the SHA-256 of everything but `build` and `built_at`, so an unchanged rebuild has the
  same id and the app sees no update.
- `total` is the bundles' and packs' bytes.
- `files` lists every file the app needs offline besides the article pages, by the URL path it is
  requested at (`/` for `index.html`, `/bm-en/` for the search page), with its size, the first 16
  hex digits of its SHA-1 (the `?v=` is its first 10) and the group of its pack.
- `raw` is the SHA-256 of a pack unpacked: what the build reuses a file by.

`version.json` is `{"build", "total"}` alone: what the app polls on opening, a few bytes instead of
the manifest.

## 4. The service worker (`ordpar/root/sw.js` → `/sw.js`)

Scope `/`, registered by every page: by the page script (`page.PAGE_JS`, in `/site/ordpar.js`) on
the article pages and the About page, and by `offline.js` on the shell pages. It intercepts GET
requests to its own origin, except `/offline/…` (the download's own requests) and `/sw.js`.

**Without a copy** it answers nothing: a request goes to the network untouched. Once the worker
knows there is no copy, it does not even call `respondWith` for anything but a navigation. A
navigation that fails gets the **offline notice** (status 503): "You are offline", what to do, Try
again, and a link to the front page, styled after the shell, light or dark by the stored theme. Its
words are English and live in `sw.js` (`noticeHtml`), not in the strings file.

**With a copy** (the manifest in use stored in Cache Storage), the routes are:

| Request | Answer |
|---|---|
| `/bm-en/<id>/` (a navigation, the search page's fetch of a result, or the small-article script's fetch of a cross-reference's target) | from the bundle whose range holds the id: the pack read from Cache Storage, unpacked with `DecompressionStream('gzip')`, the page's bytes cut out by the header, the tokens put back; `text/html; charset=utf-8` |
| a path in `files` (`/`, `/bm-en/`, `/about/`, `/settings/`, `/404.html`, `/site/…`, `/index/…`, `/manifest.webmanifest` and the other shell pages) | from its pack, storage first. A `?v=` that is not the held file's hash means a page newer than the copy asked for a newer script: the network first, the held file as a fallback |
| a navigation to a word's or a form's own page, `/bm-en/<word>/` or `/bm-en/<word>` (one segment, not all digits: `WORD_PAGE`) | the held `404.html`, status 404, at once, online too; the shell runs the word's search from the copy. A copy without the shell: the network |
| an id not in its bundle, any other path | the network |
| … and the network fails, for a navigation to `/bm-en/<id>` or `/bm-en/<id>/<slug>` | the held `404.html`, status 404: the shell runs the redirect, as the host's 404 does |
| … and the network fails, for any other navigation (`/bm-en/<id>/` the copy lacks, `/x/`) | the offline notice |

A search's `#q=…` never reaches the worker: it stays in the address after the `#`
([104](../../docs/decisions.md#d104)).

**Small articles offline.** A small article is cut in the browser from its target's own page
(`ordpar/site/mini.js`; [80](../../docs/decisions.md#d80)), which the page script fetches as
`/bm-en/<id>/`: the first route above. So an installed copy opens every small article with the
network off, and the small-article script ships in the shell pack with the other scripts.

**Timing headers.** Every answer from the copy carries `X-Ordpar-Offline: <pack>` and a
`Server-Timing` entry (`bundle (unpacked)` or `bundle (in memory)`, with the worker's
milliseconds), visible in the navigation timing. Measured in headless Edge on a desktop computer:
an article whose bundle was not yet unpacked took 41–59 ms from request to response (the worker's
part 32–49 ms, nearly all of it the unpack); one whose bundle was in memory, 11 ms.

**In memory**, the worker keeps unpacked packs, least recently used dropped first, up to **20 MB**
unpacked (`KEEP_BYTES`). An article bundle of 500 unpacks to about 2 MB, so that is about ten
bundles (a search's articles usually sit in one to three) plus the index packs a query reads (a
few hundred KB each). The cap also bounds what the loading setting "With the page" holds (below).
The browser stops an idle worker after about 30 s, which frees it all; the next request unpacks
again. Two requests for one pack share one unpack.

**"With the page" while a copy is in use.** The setting "When a linked article or page is loaded"
(`minifetch`: `point`, the default, `click` or `page`) decides when linked articles are fetched.
Measured with the copy installed, in phone emulation with the page's CPU 4× slower and every case
from a stopped worker: a list row's first open took 80–98 ms under `click` and 42–47 ms under
`page`; a small article on *hus*, 51–66 ms against 21–34 ms. What `page` costs: on *gå* (21740),
21 targets in 19 bundles were all unpacked in idle time within 0.65–0.8 s of the load, the page's
main thread was busy 105–235 ms more (parsing each fetched page for its small article), and the
worker held 39 MB of ArrayBuffers afterwards (7 MB under `click`). The median page links one
target, and 99 % link at most six, so most pages cost nothing. The default stays `point`: with
500 pages a bundle a first open under `click` is already under 100 ms, so `page` saves 30–50 ms
per first open at the cost of up to half a second of a phone's processor and 35–40 MB held for the
worker's life on a link-heavy page.

**Its own updates.** The browser fetches `/sw.js` on navigations (bypassing the HTTP cache for the
worker script, at most once a day by default) and installs a changed one. Ours calls
`skipWaiting()` and `clients.claim()`, so the new worker takes over at once instead of waiting for
every tab and app window to close. That is safe because the worker holds no state of its own: it is
a router over the stored copy, whose format is versioned by the cache's name
(`ordpar-offline-1`). **A future format change must read or migrate the old one.** So a route
changed in `sw.js` reaches an installed copy without a new download. Until the new worker has taken
over, the old one routes: the navigation that fetches the new `sw.js` is still the old worker's.

## 5. The download (`ordpar/site/offline.js`)

The shell pages load `offline.js` before `shell.js`. Its section (`ordparOffline.section`) is drawn
by the settings page, `/settings/` (`ordpar/site/settings.js`), in the section "Loading, offline and
your data", after the subsection *Loading* (`minifetch`; `ordpar/docs/lookup-index.md`). The first
line of the Offline part, above the download, is the install line (§ 11). Every page's header and
footer link to the settings page.

* **No copy**: a line on what the copy is, and the button **"Keep the whole dictionary on this
  device (about N MB)"**, N being the `total` of `version.json`, fetched when the section is first
  drawn. Offline, a note instead.
* **Pressed**: `manifest.json` is fetched (`cache: 'no-store'`), then every pack it names that is
  not stored yet, three at a time, each with `cache: 'no-store'` (so the download is not also
  written to the HTTP cache), checked against its SHA-256 and stored **as fetched, compressed**, in
  Cache Storage (`ordpar-offline-1`, key `/offline/<name>`). The progress shows as a bar and
  "Downloading: 12.3 of 34.1 MB". A pack that fails is tried three times; then the download stops
  with the reason and **"Try again"**, which continues: what is stored is kept and skipped, and the
  progress starts at what is already in.
* **All in**: the manifest is stored as the one in use (`/offline/__current.json`); the worker is
  told (`postMessage`, answered when it has re-read it); stored packs the manifest does not name are
  deleted; then `navigator.storage.persist()` is called. The section shows the date, the size,
  whether the browser granted persistent storage (or that it may clear the copy when the device
  runs short), and `navigator.storage.estimate()`'s usage and quota; and **"Remove the offline
  copy"**, which deletes the cache and the records.
* The download takes the Web Lock `ordpar-offline` where the browser has Web Locks, so two tabs
  never download at once.

**The records** in `localStorage` are not settings: "Reset settings" leaves them; "Delete stored
data" clears them, but not the copy itself, which only "Remove the offline copy" removes.

| Key | Holds |
|---|---|
| `offline` | `{build, at, size, persisted}` |
| `offline-update` | `{at, result: "updated"\|"failed", bytes, packs, error, checked, tried, checkError, note}`: `checked` is the last check that reached the site (the one the 15 minutes count from, and the Offline section's "Last checked"); `tried` and `checkError` the last that did not; `note` the build of a switch whose note has not shown yet (§ 6) |
| `install-offer` | the install offer's record (§ 11) |

## 6. Updates

**When.** With a copy in use and the browser online, `offline.js` checks 1.5 s after the page has
loaded, and 1.5 s after the page comes back to the screen (`visibilitychange` to visible, or
`pageshow` from the back-forward cache), one check pending at a time and none while the page is
hidden. It checks **at most once every 15 minutes** from the last check that reached the site
(`offline-update`'s `checked`, in `localStorage`, so shared by every tab and app window). A check
that did not reach the site (no network after all, a captive portal, an HTTP error) writes `tried`
and `checkError`, not `checked`, so the next opening or return checks again. A `checked` in the
future (a clock put back) counts as due. The check is not tied to a browser session, because on
Android closing the installed app's window does not end Chrome's session.

**Every page checks, not only the shell pages.** The shell pages load `offline.js` in their
combined script. The article pages and the About page load it **only where a copy is in use**: a
few lines in `/site/ordpar.js` (its `article.js` part, `page.PAGE_JS`) ask Cache Storage
(`caches.has` first, so no cache is created; then the manifest in use) and, if it is there, add
`offline.js` with its `?v=` as a script, which the worker then answers from the shell pack, so
nothing goes over the network for it. Without a copy an article page fetches nothing new. Where
`offline.js` is already loaded (the search page and 404, which also load `article.js`), the lines
do nothing. The cost is about 360 B in `article.js` (140 B gzipped); no page's HTML grows. The
alternatives were worse: a small shared piece of the check would still need the download's own
sync, switch and lock, most of the file; and the worker cannot do it, since it is stopped after
about 30 s idle and cannot show the note.

**What a check does.** It fetches `version.json` with `cache: 'no-store'`. GitHub Pages sends
`Cache-Control: max-age=600` and allows no headers of our own, so the browser's cache must be
bypassed to see a new build within ten minutes. If the build differs, it fetches `manifest.json`
(no-store; refused if its build is not the one `version.json` named, which means a deployment
half-way), then only the packs whose names the copy lacks, as the download does, under the
download's Web Lock. If another tab or window holds the lock, it is updating, and this one leaves
the record as it was. **The switch to the new manifest happens only when every pack is in**; until
then the old copy serves every request. The Offline section then shows "Updated <date> (N MB
fetched)", or "The last update failed (…); the copy you have still works." A failed update leaves
its fetched packs stored, so the next try continues. The shell pages are served from the copy, so
the new build shows from the next page loaded after the switch.

**The note.** Once the switch is done, a bar along the bottom of the window, in the install offer's
look (§ 11), says **"Ordpar has been updated — reload to see it"** in the accent, with a link
**What's new** to the site's change list (`/changes/`), **Reload** (reloads the page) and a **×**
("Close"). The words are in `ordpar/site/strings/en.json` (`offline.noteUpdated`,
`offline.noteWhatsNew`, `offline.noteReload`, `offline.noteClose`); the bar is a polite status. It
shows once per switch: the switch writes the new build into the record's `note`, and the first page
to show the note clears it (the page that made the switch or, if that page went before it could,
the next page that loads `offline.js`). It takes no focus and stays until Reload or ×.

- **Beside the install offer**, the bands stack: the offer's bar or note lowest, the update note
  above it, and `<html>`'s bottom padding their sum (`install.js` `room`, which both files call).
- **Beside the suggestions**, it is hidden (`visibility`) while the header's dropdown is open
  (`html:has(.ordpar-popup:not([hidden]))`), which reaches 60vh and would run under it on a phone.

## 7. The head lines, the robots line and the launch switch (`ordpar/sitegen/head.py`)

Every article page, the About, Help and privacy pages and every shell page carries:

    <meta name="robots" content="noindex">                        on the pages left out (below)
    <link rel="manifest" href="/manifest.webmanifest">
    <meta name="theme-color" content="#6b0f2e">
    <meta property="og:…"> … <meta name="twitter:card" …>         the link-preview tags
    <script src="/site/theme.js?v=…"></script>                    the head script

The theme colour is the default colour scheme's day accent, `colours.default()["day"]`
([63](../../docs/decisions.md#d63)); a reader's own colour setting does not change it.

**The robots line is each page's own** ([128](../../docs/decisions.md#d128)): `noindex` on
every untranslated article page, the search page `/bm-en/`, History, Favourites, Settings, the 404
page and the privacy page; none on a translated article page, the home page, About and Help.
`head_tags(indexed=…)` writes it: the article build passes the page's translated state, so a page
loses its `noindex` in the build where its article becomes translated, and the index build's
`SHELL_PAGES` names the shell pages' state, replacing the robots lines in their sources.
`ordpar/root/robots.txt` allows everything and names `/sitemap.xml`, which a whole article build
writes (`build_site.write_sitemap`: the indexed pages' addresses). A crawler that may not fetch a
page never sees its `noindex`, which is why `robots.txt` blocks nothing. Neither is access control.

**The link-preview tags** ([127](../../docs/decisions.md#d127), `head.social_tags`):
`og:type` website, `og:site_name`, `og:url` (the canonical address), `og:title` (the `<title>`),
`og:description` (the meta description, left out where the page has none), `og:image`
`https://ordpar.no/site/og/ordpar.png` (`ordpar/site/og/ordpar.png`, 1200 × 630, kept out of the
offline copy by `build_offline.other_files`) with its width, height and alt text, and
`twitter:card` `summary_large_image`.

**The launch switch**, `NOINDEX = True` in `head.py`, is to be set to `False` at version 1.0.0
([110](../../docs/decisions.md#d110)). While it is on, every page's footer band shows the
"under development" note (`chrome.footer`, the string `dev_note` in `ordpar/sitegen/strings.py`:
"Under development: Ordpar is still being built, and its pages may change."). Despite its name it
no longer touches the robots line. Turning it off changes every page, so it costs an installed copy
one full download (§ 2).

**Sizes.** The link-preview tags, descriptions and History texts add about 740 bytes to each
article page: 71.1 MB raw over the article pages, and 2.9 MB on the offline download.

## 8. The app manifest and the icon

`ordpar/root/manifest.webmanifest` is served as `/manifest.webmanifest`:

- `id` and `start_url` `/`, `scope` `/`, `display` `standalone`; name and short name "Ordpar";
  icons of 192 and 512 px, each for `any` and `maskable`.
- `related_applications`: one entry for the site's own web app,
  `{"platform": "webapp", "url": "https://ordpar.no/manifest.webmanifest"}`
  ([68](../../docs/decisions.md#d68) (3)), so that a page in a browser tab can ask
  `navigator.getInstalledRelatedApps()` whether the app is installed on this device (Android
  Chrome 84+, desktop Chrome and Edge 140+, from a page in the app's scope on the same origin).
  `prefer_related_applications` stays absent, as installability requires.
- `theme_color` and `background_color`: the default colour scheme's day accent (the splash screen
  is the icon's own ground). The committed file names `#6b0f2e` (Wine); `build_site.py`
  `write_manifest_colours` rewrites the copied manifest to the current default.

**The icon**: "cow patches" on the default scheme's ground (Wine, `#6b0f2e`): a white patch with a
maroon "Ord" behind, a pink (`#e3b7c9`) patch with a maroon "Par" in front, and three small stray
patches, in Segoe UI Semibold. `ordpar/build_icons.py` draws it at 768 px, takes its ground from
the default colour scheme, and writes `ordpar/site/icons/icon-192.png` and
`ordpar/site/icons/icon-512.png` (resampled, opaque). The art sits inside the maskable safe zone
(the centred circle of 80 %) on a full-bleed ground, so **one drawing serves `any` and
`maskable`**: a launcher's mask cuts only ground. **The PNGs are generated once and committed**:
the script draws with a Windows font (Segoe UI Semibold, from the Windows fonts folder), so a build
elsewhere could not draw them. Re-run it, and commit the PNGs, only when the design or the default
colour scheme changes. The icon is meant to stay unmistakable from ordbokene.no's, a white serif
"O" on a maroon circle.

**Installability** (Chrome and Edge) needs a manifest with a name, icons of 192 and 512 px,
`start_url` and `display` standalone, served over https (or from `localhost`), and a service worker
with a fetch handler. `Page.getInstallabilityErrors` (Chrome DevTools Protocol) returns none on
`localhost`, in desktop and phone emulation. On `localhost` the `related_applications` entry's URL
is not the page's origin, so there `getInstalledRelatedApps()` always answers `[]`; only
`https://ordpar.no` can answer yes.

## 9. What hosting needs

* The whole of `out/` published as it is: `sw.js` and `manifest.webmanifest` at the root,
  `out/offline` beside the pages, over https (a service worker needs a secure origin).
* **Publish `out/offline` in the same deployment as the pages**, and never a `version.json` newer
  than the bundles it names: the app refuses a manifest whose build is not `version.json`'s, and a
  pack that 404s fails the update (the copy keeps serving). If deployments can be partial, keep the
  previous deployment's bundle files for a while; names are content hashes, so old and new
  coexist.
* Keep the previous manifest available to the next `build_offline.py` run: it reads
  `manifest.json` in `out/offline` for the bundle boundaries. A fresh `out/` re-chunks, which is still
  deterministic but may shift boundaries after articles were added or removed.
* GitHub Pages serves `.bin` as `application/octet-stream`, and its `max-age=600` is why every poll
  is `no-store`; nothing else needs configuring. Mind its 1 GB site limit: as built on 11 November 2026, the
  published site was about 730 MB, the offline files 35 MB of it.
* At 1.0.0, `NOINDEX = False` and a rebuild: one full re-download for an installed copy (§ 2).
* A rollback (`python ordpar/deploy.py rollback`; [103](../../docs/decisions.md#d103),
  `ordpar/docs/build-site.md`) re-publishes an older snapshot with a new `build` in `version.json`
  and the manifest and every pack unchanged. A copy on the bad build updates back to it under § 6's
  rules, fetching only the packs it lacks. The new id is not the manifest's content hash; nothing
  reads it as one.

## 10. Tests

All in `ordpar/tests/`, indexed in `ordpar/docs/tests.md`:

- `test_ordpar_offline61.py` (stdlib unittest; the worker's pure parts run under bun): the pack
  format read back to identical bytes in Python and in `sw.js`; the tokens blanked and restored
  exactly; the manifest's contents and hashes; a script edit and a new stamp leaving every bundle's
  name and bytes unchanged; one page changing one bundle; boundaries kept; the worker's routes; the
  robots line by page, whatever the launch switch; the app manifest and the icons' sizes.
- `test_ordpar_offline94.py`: the 15-minute rule (`due`) and the record under bun, the triggers,
  the article page's loader (only with a copy, its `?v=` the shipped file's), the note's words and
  stacking.
- `test_ordpar_offline125.py`: the Offline section's opening line.
- `test_ordpar_install68.py`: the install offer's record rules, the same rules through the event in
  a stand-in page, the Settings line's cases and the hint's conditions, the wiring, the words and
  the manifest entry (§ 11).
- `test_ordpar_slim.py`: among others, the stamp taken from `build.json` when the pages carry none.

What only a browser can check (the download, an update between two builds, the routes offline,
the install offer's paths) was checked by hand in headless Edge over the DevTools Protocol, with
`out/` served the way GitHub Pages serves it. Not checkable without a real phone: whether Chrome's
own install bar really stays away, the real event's timing on Android, an install from the bar (a
WebAPK), `appinstalled` and the note there, and the iPhone's Share wording.

## 11. The install offer (`ordpar/site/install.js`)

Decision [68](../../docs/decisions.md#d68): the install is offered **once per device**, with
an **Install app** button in Settings → Offline for any time after, and a one-line hint in the
footer **on phones only**. The offer shows wherever Chrome allows it, computers included; there is
no bar on iPhones. The texts are in `ordpar/site/strings/en.json` under `install.*`.

**Where the code is.** `install.js` is a part of both combined scripts, just before `shell.js`
(`page.ARTICLE_JS_PARTS`, `page.SHELL_JS_PARTS`), so every page has it and no page needs another
tag. `offline.js` `section` asks it for the Settings line, and `shell.js` `addChrome` for the
footer's hint; the styles are in `shell.css`. Like every script, it ships without comments.

**The event.** Every page listens for `beforeinstallprompt` (Chromium only: Chrome, Edge, Opera,
Samsung Internet) and **always** calls `preventDefault()` on it, so Chrome's own install bar does
not show; our offer replaces it. Each page keeps its own event, because an event lives only in its
own document and `prompt()` works once per event. Chrome fires it on each load while the app is
installable and not installed, at the first moment it allows (after about 30 s and a click on the
site, at any time); headless Edge on `localhost` fires it at once. `appinstalled` marks the app
installed, whatever installed it (our button or the browser's menu).

**The record** is `localStorage` `install-offer` = `{shown, answer, installed, at}`, beside
`offline` and `offline-update` (§ 5), and the session's mark, `sessionStorage`
`ordpar-install-shown`. It is not a setting: "Reset settings" leaves it; "Delete stored data"
clears it with the rest of `localStorage`, and the offer may then show again, as it may after the
browser's own "clear site data". When the event fires, the bar shows only if:

* the page is not the installed app (`display-mode` standalone, fullscreen or minimal-ui, or iOS's
  `navigator.standalone`);
* no `answer` is recorded and `installed` is not set. **Install** (pressed: `install`; then Chrome's
  dialog accepted: `installed`, cancelled: `dismissed`) and **No thanks** (`no`) each end the offer
  for good, as does an install by any other route (`appinstalled`);
* `shown` is under 2 (each showing adds one);
* it has not shown in this browsing session (the mark). So an offer **left unanswered** (the page
  left or closed with the bar showing) does not come back on the next page of the same visit; on a
  later visit (a new session, whose `sessionStorage` is empty) it shows **once more**, then never
  again, answered or not.

**The bar** (`.ordpar-install-bar`) is fixed along the bottom of the window: the page's surface
colour under a 2 px rule in the scheme's accent, so it follows every scheme by day and night; its
title in the accent, a line of text, **Install** (the accent button) and **No thanks** (the quiet
one). Being fixed, it moves nothing on the page; while it shows, `<html>` gets a bottom padding of
its height, so the footer can be scrolled clear of it (the body's own height is untouched, so a
short page's footer stays where it was). It is a region labelled by its title, at the end of the
body (after the footer in the Tab order); the title is also announced once through a polite status.
It takes no focus.

**The notes** after an answer (`.ordpar-install-note`, a status, in the bar's place), shown for
8 s, held while the pointer or the focus is on them:

- after an accepted install, or `appinstalled` outside the app: *"Installed. To use it offline,
  keep the whole dictionary in Settings → Offline."*;
- after **No thanks**, or Chrome's dialog cancelled from the bar: *"You can install it any time in
  Settings → Offline."*

"Settings → Offline" links to `/settings/#data`, the section "Loading, offline and your data".
A dialog cancelled from the Settings button shows no note (it would point to the page it is on).

**The Settings line** (`.ordpar-install-line`, the Offline part's first item, above the download;
`data-case` names the case) is redrawn when the event arrives after the section is drawn, after an
install, and when `getInstalledRelatedApps` answers:

| Case | Detected by | Shows |
|---|---|---|
| `app` | `display-mode` standalone / fullscreen / minimal-ui, or `navigator.standalone` | *"You're using the installed app."* |
| `installed` | `getInstalledRelatedApps()` lists the app, or it was installed from this page (`appinstalled`, or the dialog accepted), or the record says installed and no event has come (a browser without that API: desktop Chrome before 140) | *"Ordpar is installed on this device."* |
| `offer` | this page holds an install event | *"Ordpar can be installed as an app: it opens from your home screen or desktop in its own window."* and **Install app** (`prompt()`; the same record as the bar's Install) |
| `ios` | iPhone, iPad or iPod in the user agent, or an iPad in desktop mode (`navigator.platform` `MacIntel` with `maxTouchPoints` > 1) | *"To install Ordpar, tap Share in Safari, then Add to Home Screen."* |
| `menu` | a browser that has the install event (`BeforeInstallPromptEvent` or `onbeforeinstallprompt` exists) but has not fired it (yet) | *"To install Ordpar, use your browser's menu: Install app (or Add to Home screen)."* |
| none | every other browser (Firefox, desktop Safari) | nothing: the line is hidden |

The order matters: an event means the app is not installed here, so it outranks the record's
`installed` (left over after an uninstall); `getInstalledRelatedApps` and this page's own install
outrank the event.

**The footer hint**, *"Install Ordpar as an app"* (`.ordpar-install-hint`, linking to
`/settings/#data`), is made by `shell.js` `addChrome` among the footer's links, on a line of its
own, and relabelled with the chrome (`data-ordpar-string`). It is made only:

- on a touch screen: the primary pointer coarse and no hover, `(pointer: coarse) and (hover: none)`,
  so a laptop with a touch screen and a mouse does not count;
- outside the app, and not where the app is known to be installed;
- only where the Settings line has something to say (a browser with the install event, or an
  iPhone or iPad; on Firefox the link would lead to nothing).

`shell.css` shows it only at **a phone's size**: that media query and either side under 40rem
(640 px), so a phone upright (360–430 px wide) or turned (under 500 px high), never a tablet
(744 px or more both ways), and a phone turned while reading follows; and never under
`display-mode` standalone. Until `addChrome` has run, the sheet holds its line
(`.ordpar-footer-nav::after`, 1.275rem, under the same query and not in the app), so nothing moves;
where no hint comes (Firefox on a phone) the held line closes once. Where `getInstalledRelatedApps`
exists, the hint keeps its room but stays invisible until it answers, and is removed if the app is
installed. The hint stays after the offer has been seen.

**Cost.** No page's bytes change beyond the `?v=` of the combined scripts, which the bundles blank
(§ 2), so an installed copy's update is the shell pack alone. `install.js` is about 11 KB, in each
combined script.
