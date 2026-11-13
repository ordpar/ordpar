# How Ordpar works

This overview is for a developer who wants to understand the work, change it, or build something of
their own from it. It says how the pieces fit, which of them are general and which are tied to
Bokmålsordboka, Norwegian, English or our own data, and how to use the dictionary inside another app.
Each section points to the doc with the details. How to build the site and run the tests is in the
[README](../README.md).

## Contents

- [How the pieces fit](#how-the-pieces-fit)
- [Using it for another language or another dictionary](#using-it-for-another-language-or-another-dictionary)
- [Using the dictionary in another app](#using-the-dictionary-in-another-app)
- [The docs](#the-docs)

## How the pieces fit

Ordpar is a static site: plain files on GitHub Pages, with no server of its own. Search, the
settings, the history and the offline copy all run in the reader's browser. Only two small
Cloudflare Workers answer requests: one takes readers' reports, the other serves the recordings.

```
Bokmålsordboka's data        data/bokmalsordboka/          one article per line, as the API serves it
  + our corrections          data/review/                  applied in memory by the build (the overlay)
        |
        v
the library                  data/articles.jsonl           Norwegian derived from the data, English written by us
        |
        v
build_site.py  ------------> ordpar/out/bm-en/<id>/        one page per article, and the text pages
build_index.py ------------> ordpar/out/index/             the search index in small files, the search pages
build_offline.py ----------> ordpar/out/offline/           the whole site packed for the offline app
        |
        v
GitHub Pages (ordpar.no)  <----- the reader's browser ----->  receiver Worker (reports, survey)
                                                          -->  audio Worker (recordings)
```

### Bokmålsordboka's data and our corrections

The build's source for the Norwegian is the **mirror**: every Bokmål article, exactly as the
University of Bergen's API at `ord.uib.no` serves it, one JSON object per line
(`data/bokmalsordboka/`, joined from its parts first). Beside it are the API's listing files,
which tell which articles ordbokene.no lists, and its table of abbreviations.
`ordpar/sitegen/mirror.py` indexes the file once and reads articles back by their position, so
the 205 MB file is never held in memory.

Our corrections to Bokmålsordboka's text are patches in `data/review/mirror-corrections.jsonl`.
The build applies them in memory, to the articles with no library row, before anything reads
those articles (`ordpar/sitegen/overlay.py`); the data files are never written. The same patches,
and those made from our log of corrections, give the corrected copy in
`data/bokmalsordboka/corrected/` (`ordpar/corrected_copy.py`). The site reads the raw copy and the
patches and applies them itself, so that every fix can be checked against the original. Details:
[`data/bokmalsordboka/README.md`](../data/bokmalsordboka/README.md).

### The derivation of the Norwegian

An article's Norwegian is turned from the API's JSON into a library row by `scripts/derive.py`
(`derive_row`), after `scripts/fetch.py` (`prune_article`) has kept only the fields it reads. The
row holds the headwords, the word class in English (`scripts/postags.py`), the senses, the
examples, the etymology and the set phrases, as lists of text segments with markers for
cross-references and mentioned words (`scripts/markup.py`). For the articles in the library this
was done by our private pipeline, from the article files in `data/sources/articles/`. For every
other article the build does it on the fly from the mirror (`ordpar/sitegen/library.py`, `Store`).

### The library of English

`data/articles.jsonl` holds one row per article we have worked on: the derived Norwegian and,
segment by segment, our English. An article is shown as **translated** only when every line of it
has English (`complete_strict` in `scripts/coverage.py`); otherwise its page is the Norwegian
article, marked *Norwegian only*. No page is ever half English. Example sentences we added are in
the row too, and the build accepts the library only with the marker that says it was checked by
our example gate (`ordpar/sitegen/gate.py`). The row format: [`data/README.md`](../data/README.md).

The English is written by a private pipeline, which is not in this repository.

### The page build and its renderer

`ordpar/build_site.py` writes one page per article, at `/bm-en/<id>/`. The article itself, the part
inside the card, is drawn by the same renderer that makes our Anki cards, `ordbok_gen.py`, with
`scripts/mini.py` and `scripts/markup.py`; `ordpar/sitegen/deck.py` imports them, and
`ordpar/sitegen/article.py` adapts their output to the site. `ordpar/sitegen/page.py` puts the
header, the footer, the settings script and the styles around it. Some of the work is left to the
browser:

- a cross-reference is a plain link with a short preview of the target (the *peek*) beside it, which
  the build writes into the page (`_link` in `ordpar/sitegen/face.py`) and the style sheet shows when
  the pointer rests on the link (the rule `.ordbok-xref:hover>.ordbok-xpeek`, in `ordbok_gen.py`).
  A click opens the target as a small article in place, cut from the target's own page
  (`ordpar/site/mini.js`); the same script makes the peek from the target's first Norwegian
  definition instead when the reader's settings ask for that (`nbPeek`);
- the inflection table travels as compact data inside the page and is drawn by
  `ordpar/site/inflection.js`, wide or stacked to fit the card.

The same build writes the text pages (About, Help, Privacy and others, from `ordpar/*.md`) and
`build.json`, a record of the build. Details:
[`ordpar/docs/build-site.md`](../ordpar/docs/build-site.md) and
[`ordpar/docs/inflection-table.md`](../ordpar/docs/inflection-table.md).

### The search index

`ordpar/build_index.py` reads the mirror and the library and writes the search index as many small
JSON files under ordpar/out/index/, one per initial letter (the five largest letters split again),
so a search loads only the files it needs. Every headword and every inflected form points at its
articles, so *husene* finds *hus*. The browser's side is `ordpar/site/lookup.js` (lookup,
suggestions, similar words for a misspelling, Random word) and `ordpar/site/shell.js` (the search
page, the results, the settings). The suggestions are ranked partly by the National Library of
Norway's word counts, from which the build writes only a frequency band per headword. An English
search, from the translated articles' summary glosses, is in ordpar/out/index/en/. The same build
writes a page at `/bm-en/<word>/` for a word whose first article is translated, and for common
irregular inflected forms (`ordpar/sitegen/wordpages.py`). Details:
[`ordpar/docs/lookup-index.md`](../ordpar/docs/lookup-index.md).

### The offline copy

The site installs as an app. `ordpar/build_offline.py` packs the built pages and the index into
bundles (in ordpar/out/offline/); `ordpar/site/offline.js` downloads them when the reader asks to keep
the dictionary on the device, and the service worker, `ordpar/root/sw.js`, answers from them when the
device is offline, byte for byte the page the host serves. Details:
[`ordpar/docs/offline-app.md`](../ordpar/docs/offline-app.md).

### The two Workers

- **The receiver** (`ordpar/receiver/`): takes the "Suggest a correction" reports and the survey's
  answers, and could take the counting of page views and searches, which is built but off. It stores
  them in a Cloudflare database in the EU. Details: [`ordpar/docs/receiver.md`](../ordpar/docs/receiver.md)
  and [`ordpar/receiver/README.md`](../ordpar/receiver/README.md).
- **The audio Worker** (`ordpar/audio-worker/`): serves the recordings from Cloudflare's storage. A
  page has play buttons only when the build is given the list of recordings (`--audio-names`), which
  is not in this repository. Details: [`ordpar/audio-worker/README.md`](../ordpar/audio-worker/README.md).

### The deploy

`ordpar/deploy.py` publishes ordpar/out/ to GitHub Pages as one snapshot, after running the tests,
and can roll back. It is set up for ordpar.no; see the README's
[If you host a copy](../README.md#if-you-host-a-copy).

## Using it for another language or another dictionary

Most of Ordpar is not tied to Norwegian: a static site with one page per article, search that runs
in the browser from small files, an offline copy, settings and history kept on the device, a
reports form, and a build that keeps a source dictionary and a translation apart and never shows a
half-translated article. The parts that are tied to something are below, with what you would
replace.

**Tied to Bokmålsordboka's data.** The build reads articles in the shape the University of Bergen's
API serves them: `{"id", "revision", "updated_at", "data"}` per line, `data` the API's article
(`ordpar/sitegen/mirror.py`; the listing files in `Listing` there). The readers of that shape are
`scripts/derive.py` (`derive_row`), `scripts/fetch.py` (`prune_article`), `scripts/headwords.py`,
`scripts/postags.py` (the word-class tags), `ordpar/sitegen/pronunciation.py`, and the index build's
`read_mirror` in `ordpar/build_index.py`. You can either convert your own source
into that shape, which leaves the build untouched, or replace those readers. The first is less work
if your source is a dictionary with senses, examples and inflections; look at a few lines of
`data/bokmalsordboka/bm-articles.*.jsonl` to see the shape. The credit in every page's footer and on
the About page names Bokmålsordboka (`ordpar/sitegen/strings.py`, `ordpar/about.md`).

**Tied to Norwegian.**

- *The inflection tables*: `ordpar/site/inflection.js` knows Norsk ordbank's tags and lays out
  Norwegian nouns, verbs and adjectives as ordbokene.no does
  ([`ordpar/docs/inflection-table.md`](../ordpar/docs/inflection-table.md) § 3 is the tag table).
  Another language needs its own table of tags and layouts. The labels of inflected forms in search
  ("plural definite") come from the same words (`ordpar/sitegen/wordpages.py`, `FormLabels`).
- *Search*: the folding of accents keeps *æ ø å* as letters (`KEEP` in `ordpar/build_index.py`),
  the index files are split by Norwegian letters, and the spelling rules for misspellings (`RULES`,
  `DOUBLING`) are Norwegian ones. Each of these is written twice, in `ordpar/build_index.py` and in
  `ordpar/site/lookup.js`, and the two must agree.
- *Alphabetical order* inside a table cell uses Norwegian collation (`'nb'` in
  `ordpar/site/inflection.js`).
- *The order of a headword's spellings* (`ordpar/sitegen/lemma_order.py`) and the key to the
  pronunciation marks in `ordpar/help.md` are about Norwegian.

**Tied to English.** The interface's words are in `ordpar/sitegen/strings.py` and
`ordpar/site/strings/en.json`. They are kept out of the article itself, so a second interface
language needs these strings translated, not a second set of article pages. The section labels inside an article ("Etymology", "Set phrases") are in
`ordpar/sitegen/article.py`. Word classes are given in English (`pos_en`, from
`scripts/postags.py`). The English search (ordpar/out/index/en/) is built from the library's
English summary glosses. The address of every article starts with the pair `bm-en`. It is a
constant, `PAIR`, in `ordpar/sitegen/face.py`, `ordpar/sitegen/chrome.py`,
`ordpar/sitegen/wordpages.py` and `ordpar/build_offline.py`, but it is also written out in 22 code
files outside the tests, most often in `ordpar/site/lookup.js`, `ordpar/site/ahead.js` and
`ordpar/root/sw.js`: search the code for `bm-en`.

The pages also carry a second set of interface labels, in Norwegian, which the reader's settings
can show instead of the English ones ("Vis bøyning" for "Inflection"): `NB_LABELS` in
`ordpar/sitegen/article.py` and `NB_STRINGS` in `ordpar/site/inflection.js`. A version for another
language replaces them with labels in its own source language.

**Tied to our own data.**

- *The library*: the site needs rows in the format of [`data/README.md`](../data/README.md): the
  Norwegian segments, an English segment for each (or `null`), the examples as pairs, the markers in
  the text. The English in it is written by our private pipeline, which is not in this release; for
  your own language you need your own way of writing those rows. The build accepts a library only
  with its gate marker; `gate.write_marker` in `ordpar/sitegen/gate.py` writes one (the command:
  [`data/README.md`](../data/README.md)).
- *The frequency source*: the National Library of Norway's word counts, read by `read_freq` in
  `ordpar/build_index.py` as `count form` lines in ISO-8859-1. The bands are scaled to that corpus's
  size (`FREQ_SCALE`). Another corpus needs its own scale, and a language with letters outside
  ISO-8859-1 a change to the reader. Without `--freq` every band is 0 and suggestions are ranked by
  length and alphabet.
- *The audio*: optional. The build marks a text with its recording only when given a list of clip
  names (`--audio-names`, `ordpar/sitegen/audio.py`); the player is `ordpar/site/audio.js`, and the
  Worker that serves the files is `ordpar/audio-worker/`. How the recordings are made is not in this
  repository.
- *The site's name, address and pages*: see [If you host a copy](../README.md#if-you-host-a-copy).

**A worked case: French words with English translations.** Say you have a French dictionary you may
use, and want what Ordpar is for Norwegian. You would:

1. convert its articles into the mirror's shape, each with a stable id, its headwords, its senses
   and examples, and its inflection data, or write your own reader in place of `derive.py`;
2. write the library: for each article, the derived French and your English, in the row format of
   `data/README.md`, with its gate marker. The tools Ordpar writes its English with are not in this
   release; we plan to publish them later, in a form you can repurpose for another language, and
   sooner if you ask ([Contact](../README.md#contact));
3. give `ordpar/site/inflection.js` a table of French tags and layouts (conjugation tables, not
   Norwegian noun tables), and replace the search's spelling rules with French ones (dropped accents
   are already folded: *e* finds *é*);
4. supply French word counts for the suggestions, or leave `--freq` out;
5. change the pair in the addresses (`bm-en`), the credits, the name and the text pages.

Two things such a version needs are not written yet: a description of the article format the build
expects, and a guide to which tests it keeps, rewrites or drops. If you would like to use this
repository for another dictionary, write to us at [post@ordpar.no](mailto:post@ordpar.no) and we
will add them.

The parts not tied to the language stay as they are: the page build's loop, the search's file
layout, the offline copy, the settings and the receiver. The check scripts in `handover/checks/` read Bokmålsordboka's JSON, but the kinds of mistake
they look for (links to a sense that does not exist, doubled spaces, unmatched quotes, words not
found among the dictionary's own forms) are worth looking for in any dictionary; the account in
`handover/checks/agent-review/` of how agents sorted one check's findings is not tied to a language.

## Using the dictionary in another app

For a course, a reading app or any other learning resource that wants the Norwegian–English
dictionary inside it, there are three ways in, from the least work to the most control.

**The built pages.** Build the site (README) and take what you need from ordpar/out/: each
article's page is `bm-en/<id>/index.html`. The search page's script lifts the article out of such a
page (`extractArticle` in `ordpar/site/lookup.js`), which shows where it starts and ends. You can
also link to the live pages, `https://ordpar.no/bm-en/<id>/`.

**The library and Bokmålsordboka's data.** `data/articles.jsonl` has, for every translated article,
the Norwegian and the English side by side, as data: the senses, the examples, the summary gloss
under the headword (a short list of English equivalents), the set phrases. That is the smallest
useful set if you draw articles your own way. A translated article is one whose row passes
`complete_strict` (`scripts/coverage.py`); the rest of the rows are not finished. An article with no
row is in `data/bokmalsordboka/` in Norwegian only.

**The renderer as a module.** `ordpar/build_site.py` shows the sequence in its `main`: read the
library and apply the gate (`ordpar/sitegen/gate.py`), index the mirror
(`ordpar/sitegen/mirror.py`, `Mirror`), make the `Store` (`ordpar/sitegen/library.py`) that decides
each article's face, apply the overlay, then `Builder(store, mirror, stamp).page(id)` gives one
article's page. The tests render a handful of pages this way into a scratch folder (see
`ORDPAR_TEST_OVERLAY` in [`ordpar/docs/tests.md`](../ordpar/docs/tests.md)).

**Looking a word up.** The search index finds an article from a headword or from any of its
inflected forms. In the browser, `ordpar/site/lookup.js` does it over the built `index/` files; in
Python, the class `Index` in `ordpar/build_index.py` gives the same answers over the same files
(`Index(index_dir).lookup(word)`, and `suggest`, `similar`). `python ordpar/build_index.py --verify
--query <word>` asks it from the command line. The file format is
[`ordpar/docs/lookup-index.md`](../ordpar/docs/lookup-index.md) § 3.

**What the licences ask.** The code asks nothing (MIT-0). The dictionary's text does. The
Norwegian is Bokmålsordboka's, © Språkrådet (the Language Council of Norway) and the University of
Bergen, under CC BY 4.0: credit Bokmålsordboka as that licence asks. Our English is written with
AI, and whatever rights exist in it are given under CC BY 4.0 too; our added example sentences and
corrections are under CC BY 4.0. Credit all three to Ordpar (ordpar.no). The README's
[Licences](../README.md#licences) gives each part's terms, and
[`data/LICENSE.md`](../data/LICENSE.md) lists them file by file.

## The docs

- [README](../README.md): building, testing, licences, hosting a copy.
- [`data/README.md`](../data/README.md): every data file, and the library's row format.
- [`data/bokmalsordboka/README.md`](../data/bokmalsordboka/README.md): Bokmålsordboka's data, its parts
  and the corrected copy.
- [`ordpar/README.md`](../ordpar/README.md): the site's folder, file by file.
- [`ordpar/docs/build-site.md`](../ordpar/docs/build-site.md): the article pages.
- [`ordpar/docs/lookup-index.md`](../ordpar/docs/lookup-index.md): the search index and the search
  pages.
- [`ordpar/docs/inflection-table.md`](../ordpar/docs/inflection-table.md): the inflection tables.
- [`ordpar/docs/offline-app.md`](../ordpar/docs/offline-app.md): the offline copy.
- [`ordpar/docs/receiver.md`](../ordpar/docs/receiver.md): the receiver.
- [`ordpar/docs/tests.md`](../ordpar/docs/tests.md): every test file.
- [`docs/where-in-the-code.md`](where-in-the-code.md): where a feature lives in the code, for each
  divergence from ordbokene.no; it answers "where does feature X live".
- [`docs/glossary.md`](glossary.md): the project's own words, and the shorthand in the code's
  comments.
- [`docs/decisions.md`](decisions.md): the decision log; comments in the code cite its entries by
  number.
- [`docs/divergences.md`](divergences.md): where Ordpar differs from ordbokene.no, and why.
- [`docs/plan.md`](plan.md) and [`docs/ideas.md`](ideas.md): the plan for the site, and the ideas
  not yet decided.
- [`handover/checks/README.md`](../handover/checks/README.md) and
  [`handover/checks/agent-review/README.md`](../handover/checks/agent-review/README.md): the checks
  of Bokmålsordboka's data and the agent review.
