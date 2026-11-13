# CLAUDE.md

This repository builds Ordpar (<https://ordpar.no>), a static Norwegian–English dictionary site:
every article of Bokmålsordboka, with English added to the translated ones. It holds the site's code
and every file the build reads. This file is for an AI coding assistant working in a clone. It
routes into the docs written for people rather than repeating them; read the doc a task needs
before changing what it describes.

Start with [`README.md`](README.md) (build, tests, licences, hosting a copy) and
[`docs/overview.md`](docs/overview.md) (how the pieces fit, and what to replace for another
language or another dictionary).

## The folders

| Path | What it is | Its doc |
|---|---|---|
| `ordpar/` | the site: `build_site.py` (article pages), `build_index.py` (search index), `build_offline.py` (offline copy), `sitegen/` (the page generator), `site/` (browser scripts and styles), `root/` (service worker, app manifest), `receiver/` and `audio-worker/` (Cloudflare Workers), `tests/` | [`ordpar/README.md`](ordpar/README.md) |
| `ordpar/docs/` | the technical docs: one per build, plus the tests' index | listed in [`ordpar/README.md`](ordpar/README.md) |
| `ordbok_gen.py`, `scripts/` | the article renderer and the pipeline modules the site imports; imported, not run | [`docs/overview.md`](docs/overview.md) |
| `data/` | everything the build reads: the library, Bokmålsordboka's data (raw and corrected), word counts, corrections | [`data/README.md`](data/README.md) |
| `handover/checks/` | scripts that find errors in Bokmålsordboka's data; `agent-review/` sorts one check's findings with AI agents | [`handover/checks/README.md`](handover/checks/README.md) |
| `docs/` | the overview, the decision log, the divergences from ordbokene.no, the plan, the ideas; [`docs/where-in-the-code.md`](docs/where-in-the-code.md) answers "where does feature X live" for each divergence, and [`docs/glossary.md`](docs/glossary.md) explains the project's own words and the shorthand in the code's comments | — |
| `tests/` | the test of the check scripts | — |

## Commands

From the repository's root folder:

```bash
python ordpar/data_parts.py join data/bokmalsordboka     # once after a clone or a pull
export ORDBOK_DATA_DIR=data
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --ids 7663 62174   # a few articles
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --all
python ordpar/build_index.py --mirror data/bokmalsordboka/bm-articles.jsonl \
       --freq data/frequency/nb-2026-books-nob-1990_freq.frk
python ordpar/build_offline.py
for f in ordpar/tests/test_*.py tests/test_*.py; do python "$f" || echo "FAILED: $f"; done
python handover/checks/agent-review/test_agent_review.py
```

Every script has a `--help`; trust it over memory. The tests are standard-library `unittest`, one
file at a time; a test that needs something absent (a build, bun, Microsoft Edge, the whole data,
a private module) is skipped with its reason printed. [`ordpar/docs/tests.md`](ordpar/docs/tests.md)
says what each file checks.

## Rules that keep the build right

- **Run the tests near what you changed, and all of them before calling a change done.** A change
  that adds a test file adds its row to `ordpar/docs/tests.md`.
- **Never edit a generated file by hand.** The joined articles files are made by
  `ordpar/data_parts.py join`: `data/bokmalsordboka/bm-articles.jsonl` by the join in the commands
  above, and the corrected copy's, in `data/bokmalsordboka/corrected/`, only if you join that
  folder too ([`data/bokmalsordboka/README.md`](data/bokmalsordboka/README.md)); everything under ordpar/out/ and ordpar/.build/ (both git-ignored) is made by the builds. Change the
  source or the code and build again.
- **Keep the data's bytes.** The files under `data/` are compared byte for byte (the parts with the
  joined file, the library with its gate marker, the corrected copy with the raw one). Never
  reformat, re-encode or re-sort them, or change their line endings (`.gitattributes` keeps git from
  doing so). If you change `data/articles.jsonl` on purpose, write a new marker with
  `gate.write_marker` (`ordpar/sitegen/gate.py`; the command is in `data/README.md`), or the build
  refuses it.
- **The data keeps its licences and credits.** The code and docs are MIT-0, but Bokmålsordboka's
  text is CC BY 4.0 (© Språkrådet and the University of Bergen), and so are Ordpar's added example
  sentences and corrections (credited to Ordpar); whatever rights exist in Ordpar's English, which
  is written with AI, are given on the same terms (credited to Ordpar). Never remove a credit from the pages or
  the data's READMEs; anything built from the data must keep crediting its sources. The README's
  "Licences" section has the exact terms.
- **Two scripts are not for a clone as it stands.** `ordpar/export_public.py` runs only in Ordpar's
  private repository. `ordpar/deploy.py` publishes to ordpar.no's own GitHub Pages; a copy must be
  changed first (the README's "If you host a copy").
- **Some code is written twice and must agree**: the search's folding, sharding and spelling rules
  in `ordpar/build_index.py` and `ordpar/site/lookup.js` (each says so where it applies).
- **"decisions N" in a comment** is entry N of [`docs/decisions.md`](docs/decisions.md): read it
  before changing what it explains.

## Adapting it to another language or dictionary

[Using it for another language or another dictionary](docs/overview.md#using-it-for-another-language-or-another-dictionary)
in the overview lists every part tied to Bokmålsordboka, to Norwegian, to English or to Ordpar's
own data, with where it lives and what to replace, and a worked case for French. Read it before
planning such work. The English in the library was written by a private pipeline that is not in
this repository yet (a later release is planned, sooner on request: the README's "Contact"); the
row format the site expects is in [`data/README.md`](data/README.md).

## An agent you can reuse

`handover/checks/agent-review/check7-reader.md` is the agent definition the review of one check's
findings ran with. Copy it into the `agents` folder of a project's `.claude` folder to use it;
[`handover/checks/agent-review/README.md`](handover/checks/agent-review/README.md) explains the loop,
how to run it, and what it does not do.
