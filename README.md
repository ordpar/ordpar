# Ordpar

Ordpar, at <https://ordpar.no>, is a free Norwegian–English dictionary on the web. It is built on
Bokmålsordboka, the Bokmål dictionary from Språkrådet (the Language Council of Norway) and the
University of Bergen, and adds an English translation to each article: the definitions, the examples
and the set phrases. Every article has a page; those we have not translated yet are shown in
Norwegian. Its aim is to help people learn Norwegian: a learner can read a Norwegian word's whole
dictionary entry in a language they already know. It is free to use, with no advertisements and no
account.

This repository holds the code that builds the site and the data the build reads, so that anyone
can build the whole site from it. It is meant for applying the work elsewhere, not only for copying
it:

- **The same kind of dictionary for another language.** Say, French words with English
  translations, from sources of your own, taking over the method, the layout and the tools. Start
  with [Using it for another language or another dictionary](docs/overview.md#using-it-for-another-language-or-another-dictionary)
  in the overview. The tools that write the translations are not here yet (below).
- **Features for another dictionary site.** Each place where Ordpar deliberately differs from
  ordbokene.no is described, with its reason, in [`docs/divergences.md`](docs/divergences.md); see
  also [For ordbokene.no's editors and developers](#for-ordbokenenos-editors-and-developers) below.
- **The Norwegian–English dictionary inside your own app or course.** The library's format is in
  [`data/README.md`](data/README.md), how to build pages and search from it in
  [Using the dictionary in another app](docs/overview.md#using-the-dictionary-in-another-app), and
  what a reuse must credit under [Licences](#licences) below.

How the pieces fit together, from Bokmålsordboka's data to a page in the browser:
[`docs/overview.md`](docs/overview.md). The project's own words, and the shorthand in the code's
comments: [`docs/glossary.md`](docs/glossary.md).

## What is here, and what is not

**Here:**

- `ordpar/`: the site. The build scripts, the page generator (`ordpar/sitegen/`), the scripts and
  style sheets that run in the browser (`ordpar/site/`), the offline app's files (`ordpar/root/`),
  the two Cloudflare Workers (`ordpar/receiver/` for reports and the survey, `ordpar/audio-worker/`
  for the recordings), the sources of the text pages, the tests and the technical docs
  (`ordpar/docs/`). Its own README is [`ordpar/README.md`](ordpar/README.md).
- `ordbok_gen.py` and eight modules under `scripts/`: the article renderer and the parts of the
  private pipeline that the site build imports (deriving the Norwegian from Bokmålsordboka's data,
  the text markers, the word classes).
- `handover/checks/`: the scripts that found the errors in Bokmålsordboka we reported to its
  editors, with their README, and `tests/test_handover_checks.py`, their test.
  `handover/checks/agent-review/` shows how AI agents sorted the findings of one of those checks,
  with the agents' prompt and a script that runs the same loop.
- `data/`: everything the build reads. The library (`data/articles.jsonl`), the articles we have
  translated or begun, with their English,
  Bokmålsordboka's data exactly as its API serves it and a corrected copy with our fixes applied
  (`data/bokmalsordboka/`), an extract of the National Library of Norway's word counts
  (`data/frequency/`), and the small files of corrections and checks. What each file is:
  [`data/README.md`](data/README.md).
- `docs/`: the overview of how it all works, a glossary, the decision log, the divergences from
  ordbokene.no, the site's plan and the ideas not yet decided.

**Not here:**

- **The pipeline that writes the English**: the translation loop, its assessments, and the
  pipeline that writes and checks the added example sentences. The site reads only their result,
  the library. We plan to publish these tools, workflows and docs in a later release, in a form
  someone can repurpose for another language. If you would like them sooner, write to us
  ([Contact](#contact)).
- **A description of the article format the build expects, and a guide to which tests a version
  for another language keeps, rewrites or drops.** Neither is written yet. If you would like to
  use this repository for another dictionary, write to us at
  [post@ordpar.no](mailto:post@ordpar.no) and we will add them.
- **The recordings.** A build from this repository has no play buttons, since the list of
  recordings is not here. The recordings themselves are available on request (below).
- **The added example sentences' check records**, our working notes on each sentence, which the
  site never shows.
- **The tools that laid out the checks' findings as a spreadsheet** for ordbokene's editors. They
  arranged the findings; the checks themselves are here.
- **Nynorsk.** Ordpar covers Bokmålsordboka only.
- **The code of Ordpar's Anki decks.**

This repository is made from Ordpar's private one by `ordpar/export_public.py`, which is included
as the record of how it was made; it runs only in the private repository. `EXPORT.json` is the
export's own record: for each part (the site's code, the checks, the library, Bokmålsordboka's
copy), the last commit in Ordpar's own repositories that changed it; whether the export was made
as a release or a draft; and, for a draft, the number of files that had changes not yet
committed. The repository is updated once a week when something has changed.

## Building the site

You need Python 3, and nothing else: the build uses only the standard library. The code is
developed and tested with Python 3.14.

From the repository's root folder:

```bash
python ordpar/data_parts.py join data/bokmalsordboka     # once after a clone or a pull
export ORDBOK_DATA_DIR=data                              # in PowerShell: $env:ORDBOK_DATA_DIR = "data"
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --ids 7663 62174   # a few articles
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --all
python ordpar/build_index.py --mirror data/bokmalsordboka/bm-articles.jsonl \
       --freq data/frequency/nb-2026-books-nob-1990_freq.frk
python ordpar/build_offline.py
python -m http.server 8098 --directory ordpar/out        # then open http://127.0.0.1:8098/
```

1. **Join the articles.** Bokmålsordboka's articles are stored in parts under 50 MB each, because
   GitHub refuses larger files. The join writes them back into one file,
   data/bokmalsordboka/bm-articles.jsonl, byte for byte as they were cut.
2. **Point the build at the data.** `ORDBOK_DATA_DIR` tells the build, and the modules it
   imports, to read the library and the small data files from `data/`.
3. **Build the article pages.** One static page per article, in the folder ordpar/out/. `--ids` builds a
   few articles instead of all of them (7663 is *bru*, 62174 *trøtte*); `--limit N` stops after N.
   An article's id is the first number on its line in `data/bokmalsordboka/bm-listed.jsonl`, so
   `grep '"bru"' data/bokmalsordboka/bm-listed.jsonl` finds *bru*'s.
4. **Build the search index** and the search, Settings, History and Favourites pages. It reads the
   list view's snippets that step 3 wrote, so it comes after it. `--limit N` reads only the first
   N articles, for a quick index.
5. **Pack the offline copy**, which the installed app can keep on the device. It reads what steps 3
   and 4 wrote.
6. **Look at it** with any static file server. Python's own does not answer a missing address with
   the site's `404.html` the way GitHub Pages does, so the few addresses that page handles (a word
   typed in another case, such as `/bm-en/Norge`) do not work there.

Each script's `--help` lists its options. The details are in
[`ordpar/docs/build-site.md`](ordpar/docs/build-site.md) (the pages),
[`ordpar/docs/lookup-index.md`](ordpar/docs/lookup-index.md) (the search) and
[`ordpar/docs/offline-app.md`](ordpar/docs/offline-app.md) (the offline copy).

## Running the tests

The tests use Python's own `unittest`. From the root folder, with the articles joined and
`ORDBOK_DATA_DIR=data` set as above:

```bash
for f in ordpar/tests/test_*.py tests/test_*.py; do python "$f" || echo "FAILED: $f"; done
python handover/checks/agent-review/test_agent_review.py
```

- Many tests also check the built site in ordpar/out/: build it first, or they are skipped. They
  check the whole site, so build it with `--all`. After a build of a few articles (`--ids`) they
  run and fail, since the pages they look for are not there, and a browser test may print nothing
  for several minutes. To run the tests without a whole build, move
  ordpar/out/ aside (rename it) first, and they are skipped. (`ORDPAR_TEST_OUT`, which names
  another built folder, is read by only some of them.)
- The tests of the browser scripts need [bun](https://bun.sh) or Node.js; the Workers' own tests
  need bun. Without them those tests are skipped.
- The browser tests (`ordpar/tests/test_ordpar_browser_*.py`, and the browser part of
  `ordpar/tests/test_ordpar_changenotice106.py`) need Microsoft Edge, bun and a built site.
- Tests that read the whole of Bokmålsordboka's data find it through the `mirror` key of
  ordpar/local-paths.json, a file you make from `ordpar/local-paths.example.json` with the full
  path to data/bokmalsordboka/bm-articles.jsonl. Without it they are skipped.
- Four test files test tools that only the private repository has. Here, the tests in them that need
  such a tool are skipped, each naming the missing module: `test_ordpar_copy166.py`,
  `test_ordpar_browser_copy166.py` and `test_ordpar_thanks166.py` (the page where we read readers'
  reports, and its server) and `test_ordpar_complabels151.py` (the translation pipeline's
  assessment tool).

GitHub runs the same loop on its own machine at every push, before any build, and then builds two
articles, the search index and the offline copy: `.github/workflows/tests.yml`.

As a guide: in a fresh copy of this repository on Windows, before any build and without the
browser tests, 96 test files ran 1,585 tests, of which 157 were skipped and none failed.

A skipped test prints its reason. What each file checks: [`ordpar/docs/tests.md`](ordpar/docs/tests.md).

## The decision log

[`docs/decisions.md`](docs/decisions.md) records the site's decisions by number, each with the rule
as built and its reason. A comment in the code that cites "decisions 126" means entry 126 there.
Decisions about the project rather than the code are left out, so the numbers have gaps.

## How the code was made

Ordpar mirrors what ordbokene.no shows, never how it is built: none of ordbokene's code is in Ordpar. In
November 2026 we audited the whole history of Ordpar's code. In three places, an agent writing our code had
seen the part of ordbokene's code that does the same job. Two of them, the rule for which forms of a word
share a row in the inflection table and one sentence of interface text, were rewritten by agents that had
never seen ordbokene's code, working only from its published pages. The third, the punctuation between the
parts of an etymology, shares nothing with ordbokene's code beyond a one-line rule (theirs is a stylesheet,
ours a Python loop) and was kept. Everything else was compared with ordbokene's public source code, and checked
against the history of who had seen it, and shares nothing with it beyond what the task itself dictates. The same holds for Ordbok API, whose code (AGPL) was
read for two ideas about keeping a copy up to date, and none of whose code is in Ordpar.

The code, like the English, is written with AI (Claude, by Anthropic, run as Claude Code) under
Robin Fauskanger's direction and review. Whatever rights exist in it are given under MIT-0.

## Licences

- **The code and the docs**: MIT-0, in [`LICENSE`](LICENSE). It asks nothing of you.
- **Bokmålsordboka** (`data/bokmalsordboka/`, `data/sources/articles/`, the Norwegian in
  `data/articles.jsonl`, and its text in the tests and their fixtures): © Språkrådet (the Language
  Council of Norway) and the University of Bergen, published at [ordbokene.no](https://ordbokene.no/)
  under the [Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
  The inflection tables are built from Norsk ordbank, under the same licence. Our copy was first
  taken from [ordbokapi](https://ordbokapi.org/)'s public dump of the dictionaries' database: thank
  you to ordbokapi for publishing it. The corrected copy is Bokmålsordboka with our fixes in it,
  under the same licence: credit Bokmålsordboka, and Ordpar (ordpar.no) for the corrections.
- **Ordpar's English** (the English in `data/articles.jsonl`): written with AI (Claude, by
  Anthropic) under Robin Fauskanger's direction and review. Whatever rights exist in it are given
  on the same terms as the Norwegian, CC BY 4.0: credit the English to Ordpar (ordpar.no), and the
  Norwegian to Bokmålsordboka.
- **Ordpar's added example sentences and corrections** (the `ex_added` sentences, the files in
  `data/review/`, and our fixes in `data/sources/articles/` and `data/bokmalsordboka/corrected/`):
  CC BY 4.0, like the rest of what Ordpar adds, credited to Ordpar (ordpar.no).
- **Ordpar's recordings** (not in this repository, available on request): you may reuse them on the
  same terms as the text, CC BY 4.0: credit the recordings to Ordpar (ordpar.no), and the words they
  read as you would the text itself.
- **The word counts** in `data/frequency/`: N-grams from the National Library of Norway 2026,
  [Språkbanken](https://www.nb.no/sprakbanken/), National Library of Norway
  ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)).
- **Two lists in the receiver** (`ordpar/receiver/data/`), of crawlers and of data-centre networks:
  MIT, each with its licence file beside it.

What in `data/` is under which licence, with the credits each asks for:
[`data/LICENSE.md`](data/LICENSE.md).

The app icons (`ordpar/site/icons/`) and the picture shown with a shared link
(`ordpar/site/og/ordpar.png`) are images whose letters were drawn in Segoe UI, a Microsoft font, by
`ordpar/build_icons.py`. The font itself is not in this repository.

Ordpar is an independent project. It is not made, endorsed or checked by Språkrådet, the University
of Bergen or ordbokene.no.

## Credit and a link back

MIT-0 asks for nothing, and we mean that. But if you use this work, we would be glad of a mention of
Ordpar and a link to <https://ordpar.no>. For us the only point of a credit is that it helps more
people learning Norwegian find the dictionary.

## If you host a copy

A copy built as it stands presents itself as Ordpar and is set up for ordpar.no. Before you put it
online, change these:

- **The privacy page**, `ordpar/privacy.md`, names Robin Fauskanger as the one responsible for the
  data it describes. Write your own, or leave the page out (`PRIVACY` in `ordpar/sitegen/chrome.py`;
  the build refuses reports without it).
- **Reports and the survey** are sent to Ordpar's receiver: `REPORT_RECEIVER` and `SURVEY` in
  `ordpar/sitegen/chrome.py`. That receiver accepts them only from ordpar.no, so on another address
  they fail. Set `REPORT_RECEIVER` to `""` to turn off the "Suggest a correction" button, the survey
  and the Thanks page, or to the address of a receiver of your own (`ordpar/receiver/`).
- **The counting** (page views, searches and app installs, sent to the receiver) is off: the
  address in `ordpar/site/events.js` (`var RECEIVER = '';`) is empty. Keep it empty, or point it at your own receiver and say so on
  your privacy page.
- **The recordings** are played from Ordpar's audio Worker (`WORKER` in `ordpar/site/audio.js`). A
  build without the list of recordings has no play buttons, so nothing is asked of it; if you add
  recordings of your own, point it at your own server.
- **The pages that speak for Ordpar**: About (`ordpar/about.md`), Help, Coming, More, Thanks and
  the change lists (`ordpar/*.md`), and the readers' fixes and ideas
  (`ordpar/reader-fixes.jsonl`, `ordpar/reader-ideas.jsonl`).
- **The name and the look**: `site.name` in `ordpar/site/strings/en.json`, `site_name` in
  `ordpar/sitegen/strings.py`, `ordpar/root/manifest.webmanifest`, the icons and the link picture.
- **The address**: `https://ordpar.no` is written into the canonical links, the sitemap, the app
  manifest, `robots.txt` and the deploy script (`ordpar/deploy.py`); search the code for
  `ordpar.no`. `ordpar/root/google1a7a4e06bc7a50c5.html` is ordpar.no's own verification file for
  Google; remove it.

We ask, without requiring it, that a copy does not present itself as Ordpar, so that readers know
whom to write to about it.

## For ordbokene.no's editors and developers

Everything here is yours to take, under the licences above. Where to find what may interest you:

- **The checks** that found the errors we reported: `handover/checks/`, with a README on each check,
  and `handover/checks/agent-review/` on how agents sorted one check's findings.
- **Our corrections to Bokmålsordboka's text**: `data/bokmalsordboka/corrected/`, the whole data
  with every fix applied, and `data/bokmalsordboka/corrected/fixes.jsonl`, each fix with what became
  of it; the fixes themselves in `data/review/`. Described in
  [`data/bokmalsordboka/README.md`](data/bokmalsordboka/README.md).
- **The added example sentences**: in `data/articles.jsonl`, each sense's `ex_added` list
  ([`data/README.md`](data/README.md)).
- **The divergences**: [`docs/divergences.md`](docs/divergences.md), every place Ordpar differs
  from ordbokene.no, with the reason and whether we think it could be of use to you.

Where the code is for each divergence marked **Yes** or **Maybe**:
[`docs/where-in-the-code.md`](docs/where-in-the-code.md).

## Contact

Write to [post@ordpar.no](mailto:post@ordpar.no). To report a mistake in the dictionary, use the
"Suggest a correction" button at the foot of every article on ordpar.no. For a mistake in the code
or the docs, open an issue on this repository. If you would like the recordings as files, write to
us.
