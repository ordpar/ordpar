# Ordpar: the site

Ordpar, at <https://ordpar.no>, is a free Norwegian–English dictionary built on Bokmålsordboka,
which the University of Bergen and the Language Council of Norway publish at ordbokene.no under
CC BY 4.0. Every article of Bokmålsordboka that ordbokene.no serves has a page; the translated ones carry English beside the
Norwegian, and the rest are shown whole in Norwegian, marked *Norwegian only*.

This folder, `ordpar/`, is the site: the code that builds it from the dictionary's data, the
scripts and style sheets that run in the browser, the two small Cloudflare Workers it talks to, its
tests and its technical docs. The site is static: plain files on GitHub Pages, with search, the
offline copy and every setting running in the reader's browser.

**State.** The site is live and still being built (before version 1.0.0, every page's footer says
so). Translated article pages, the home page, About and Help are open to search engines; the rest
carry `noindex`. The site installs as an app and can keep the whole dictionary on the device for
use offline. Bokmålsordboka's pronunciations are shown, and recordings of headwords, definitions,
examples and inflected forms play from the audio Worker. Readers can suggest a correction on any
article and answer a survey; both go to Ordpar's own receiver. Usage counting is built but off.

## Building the site

Python 3, and nothing else, for the build: it uses only the standard library. Only
`build_icons.py`, which draws the app's icons (they are committed, so a build does not run it),
needs Pillow. The tests of the browser scripts need [bun](https://bun.sh) or Node.js; the Workers'
own tests and the browser tests need bun (the browser tests also Microsoft Edge). From the
repository root, with the data under `data/` (see [`../data/README.md`](../data/README.md)):

```bash
python ordpar/data_parts.py join data/bokmalsordboka     # Bokmålsordboka's articles, put back together once
export ORDBOK_DATA_DIR=data                              # the library, sources/ and review/ under data/
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --all
python ordpar/build_index.py --mirror data/bokmalsordboka/bm-articles.jsonl \
       --freq data/frequency/nb-2026-books-nob-1990_freq.frk
python ordpar/build_offline.py
python -m http.server 8098 --directory ordpar/out        # then http://127.0.0.1:8098/
```

The site lands in `ordpar/out`. One machine's paths outside the repository (the mirror, the
frequency file, a deploy clone) can instead go in `local-paths.json` beside this README, made from
`local-paths.example.json` and read by `local_paths.py`. The build applies the example gate to the
library (`sitegen/gate.py`): in this repository it accepts only the library the export gated and
marked. Recordings get play buttons only when the build is given the clip names
(`--audio-names`), which the private audio pipeline writes; without them no page has a play
button. Each step's flags are in its `--help` and its doc (below).

Tests (stdlib unittest), one file at a time; from the repository root, every file:

```bash
for f in ordpar/tests/test_*.py tests/test_*.py; do python "$f" || echo "FAILED: $f"; done
python handover/checks/agent-review/test_agent_review.py
```

They are indexed in [`docs/tests.md`](docs/tests.md), which also says how to run the browser tests.

## What is here

| Path | What |
|---|---|
| `build_site.py`, `sitegen/` | the article pages: the build from the library and Bokmålsordboka's data to one static page per article, the word pages, and the text pages (About, Help, privacy and the others) |
| `build_index.py` | the search index, split by letter, and the shell pages (search, History, Favourites, Settings, 404) |
| `build_offline.py`, `root/` | the offline copy's bundles and manifest; the service worker, the app manifest and `robots.txt` served at the site's root |
| `build_icons.py` | draws the app's icons (run once; the PNGs are committed) |
| `site/` | what runs in the browser: search (`lookup.js`, `shell.js`), the inflection tables (`inflection.js`), small articles (`mini.js`), loading ahead, audio, settings, the offline copy, the install offer, reports, the survey, the counting; the strings in `site/strings/en.json` |
| `deploy.py` | publishes `out/` to GitHub Pages as one snapshot, guarded by the tests, with a rollback |
| `receiver/` | the Cloudflare Worker for reports, the survey and the (off) counting |
| `audio-worker/` | the Cloudflare Worker that serves the recordings |
| `tests/`, `test/` | the site's tests; `test/` holds the inflection-table test page and its data |
| `export_public.py`, `data_parts.py`, `corrected_copy.py` | how this public repository is made from the private one, the articles file in parts and back, and the corrected copy of Bokmålsordboka's data |
| `site_stats.py` | how much of Bokmålsordboka is translated: articles, and the share of the dictionary's text by lines and running words; the About page's statistics |
| `divergences_print.py` | prints the record of where Ordpar deliberately differs from ordbokene.no; its public edition is [`../docs/divergences.md`](../docs/divergences.md) |
| `local_paths.py`, `local-paths.example.json` | one machine's paths outside the repository |
| `about.md`, `help.md`, `privacy.md`, `more.md`, `coming.md`, `thanks.md` | the sources of the site's text pages |
| `changes.md`, `library-changes.md`, `deck-changes.md` | the change lists of the site, the dictionary and the Anki decks, published as pages |
| `freq-overrides.tsv`, `form-order-overrides.tsv` | hand-kept exceptions to the frequency bands and to the order of inflected forms in search |
| `reader-fixes.jsonl`, `reader-ideas.jsonl` | fixes made from readers' reports, and readers' ideas, shown on the Thanks page |
| `deploy-overrides.jsonl` | the record of deploys that skipped a guard, with the reason |

The article itself is rendered by the deck's renderer, `ordbok_gen.py`, with a few modules of the
translation pipeline under `scripts/` (`sitegen/deck.py` imports them), at the repository root.

## The docs

| Doc | What it covers |
|---|---|
| [`docs/build-site.md`](docs/build-site.md) | `build_site.py`: which articles get a page, the page's anatomy, the output folder, the deploy |
| [`docs/lookup-index.md`](docs/lookup-index.md) | `build_index.py`, `site/lookup.js`, `site/shell.js`: the split index, the search algorithms, the search page, the 404 shell, the settings |
| [`docs/inflection-table.md`](docs/inflection-table.md) | `site/inflection.js`: the inflection tables, their wide and narrow layouts |
| [`docs/offline-app.md`](docs/offline-app.md) | the offline copy: bundles, manifest, service worker, download, updates, the icon, the install offer |
| [`docs/receiver.md`](docs/receiver.md) | the receiver: what the counting would collect, reports, the survey, retention |
| [`docs/tests.md`](docs/tests.md) | every test file, what it checks, how to run them |
| [`../docs/where-in-the-code.md`](../docs/where-in-the-code.md) | where each divergence from ordbokene.no lives in the code: it answers "where does feature X live" |
| [`../docs/glossary.md`](../docs/glossary.md) | the project's own words, and the shorthand in the code's comments |
| [`../docs/plan.md`](../docs/plan.md) | the plan for the site |
| [`../docs/decisions.md`](../docs/decisions.md) | the decision log: every decision by number, with its reason; the code cites it as "decisions N" |
| [`../docs/divergences.md`](../docs/divergences.md) | where Ordpar differs from ordbokene.no on purpose, and why |
| [`../docs/ideas.md`](../docs/ideas.md) | ideas not yet decided |

## What is not here

The English is written by a private translation pipeline, which is not in this repository; the
site reads its result, the library (`data/articles.jsonl` here). The private repository also holds
the audio pipeline that makes and uploads the recordings, the Anki deck, and the working records
behind the decisions.

## Principles

- **ordbokene.no is the baseline** for presentation and lexicography. Where Ordpar differs, it
  differs deliberately, and the difference is recorded with its reason in
  [`../docs/divergences.md`](../docs/divergences.md).
- **Ordpar's code is its own.** It is written from descriptions of what ordbokene.no shows and
  does. Ordbokene's code may be read to learn how something works, but whoever writes Ordpar's
  code works from the description, never from ordbokene's code ([12](../docs/decisions.md#d12)).
  How the code was made is told in full in the repository's [README](../README.md).
- **Every decision is recorded** in the decision log under a number, with its reason, and the
  code cites that number.
