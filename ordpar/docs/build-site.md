# `build_site.py` — the article-page build

This doc describes `ordpar/build_site.py` and the `ordpar/sitegen/` package it uses: what the
build does, how to run it, what a page is made of, which files it writes, and the rules a change
must keep. The search index and the search pages are a second build, `ordpar/build_index.py`
([`lookup-index.md`](lookup-index.md)); the offline copy is a third, `ordpar/build_offline.py`
([`offline-app.md`](offline-app.md)); the inflection tables are drawn in the browser
([`inflection-table.md`](inflection-table.md)). The tests are indexed in [`tests.md`](tests.md).
The words used here ("translated", "Norwegian only", "summary gloss", "set phrase", "small
article") are defined in the divergences record, [`docs/divergences.md`](../../docs/divergences.md),
§ How to read the tables.

Decisions are cited by number, linked to the decision log.

## Contents

- [What the build does](#what-the-build-does)
- [Running it](#running-it)
- [Which articles get a page](#which-articles-get-a-page)
- [The output](#the-output)
- [The page](#the-page)
- [The article fragment](#the-article-fragment)
- [Cross-references and the small article](#cross-references-and-the-small-article)
- [Settings](#settings)
- [Loading ahead](#loading-ahead)
- [The search features the pages support](#the-search-features-the-pages-support)
- [What search engines read](#what-search-engines-read)
- [Corrections to the Norwegian](#corrections-to-the-norwegian)
- [The audio](#the-audio)
- [The prose pages](#the-prose-pages)
- [Report a mistake, the survey and the receiver's events](#report-a-mistake-the-survey-and-the-receivers-events)
- [The frame and the colours](#the-frame-and-the-colours)
- [Keeping the pages small](#keeping-the-pages-small)
- [The deploy](#the-deploy)
- [The code](#the-code)

## What the build does

The build joins two sources and writes one static HTML page per Bokmål article:

- the **library**, `articles.jsonl`: one row per article Ordpar has worked on, its Norwegian
  derived from Bokmålsordboka's data and its English written by Ordpar's translation pipeline
  (the row format is described in the README of the `data` folder);
- a **mirror snapshot** of every Bokmål article, as the University of Bergen's dictionary API
  serves it (`bm-articles.jsonl`, one article per line, about 205 MB).

Beside them it reads the CEFR levels the pages draw, `ordpar/levels.tsv` (`--levels`; § The headword
line).

It is **read-only**: it never writes the library, the captures, the review files or the mirror.
Everything it writes goes under `--out` (by default the git-ignored folder ordpar/out/), plus
one snippets file outside it (§ The output).

Which face an article gets is one test, `coverage.complete_strict(row)`:

| the article | the page |
|---|---|
| a library row that passes `complete_strict` | **translated**: every definition line (sense, subsense, set-phrase sense, etymology) shows the English with the Norwegian it translates; examples are bilingual; the summary gloss sits under the headword |
| a library row that does not | **Norwegian only**, from the row's own derived Norwegian; its English stays in the library until it is complete |
| no library row (about 72,000 of 94,238 articles) | **Norwegian only**, derived from the mirror article at build time by `derive.derive_row` |

A Norwegian-only page carries a status caption and a note saying the article is not yet
translated ([32](../../docs/decisions.md#d32)). **No page is ever half English**
([2](../../docs/decisions.md#d2)); the same holds for every set phrase inside a page (§ Set
phrases with no complete English). Our own library's learner notes (a summary's `note` and
`trap`) are not shown on the site ([38](../../docs/decisions.md#d38)), and the library in
the public repository does not carry them.

**The example gate.** An example sentence Ordpar added reaches a reader only once a native
speaker has written or ratified it. The rule lives in the
private translation pipeline. `ordpar/sitegen/gate.py` is the one code path for both
repositories: where the private rule can be imported, the build applies it to the library; where
it cannot (the public repository), the build accepts only a library the export already gated
and marked — a file `<library>.gate.json` beside it, naming the gate and the library's SHA-256 —
and refuses any other, saying why ([184](../../docs/decisions.md#d184)). The public
repository's `data/articles.jsonl` is such a library.

## Running it

In the public repository, put Bokmålsordboka's articles file together once (it is stored in parts
under 50 MB), then build with the data folder named:

```bash
python ordpar/data_parts.py join data/bokmalsordboka     # writes data/bokmalsordboka/bm-articles.jsonl
export ORDBOK_DATA_DIR=data
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --ids 7663 62174 --measure
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --all --limit 2000   # a timed pass
python ordpar/build_site.py --mirror data/bokmalsordboka/bm-articles.jsonl --all                # the whole dictionary
python ordpar/build_index.py …                                                                  # then the search index (lookup-index.md)
python ordpar/build_offline.py …                                                                # then the offline copy (offline-app.md)
```

`ORDBOK_DATA_DIR` points the build, and the pipeline modules it imports, at a folder holding the
library, `sources/` (the deck's article captures, read for cross-references) and `review/` (the
review files the build reads). Unset, every path is the repository root's, which is how the
private repository runs it. One machine's paths outside the repository (the mirror, the
National Library's word-count file, the deploy clone, the public export folder) go in a git-ignored
`local-paths.json` beside `ordpar/local-paths.example.json`; `python ordpar/local_paths.py mirror`
prints one. The flags always win.

| flag | what it does |
|---|---|
| `--mirror PATH` | **required**: the mirror's `bm-articles.jsonl`, opened read-only. The listing files (`bm-listed.jsonl`, `bm-unlisted.json`), the concept table and the stored copies of withdrawn articles (`bm/404/<id>.json`) are read from the same folder |
| `--ids ID …` | build these articles (a withdrawn article that is not kept is refused: § Which articles get a page) |
| `--all` | build every article in the mirror, plus the kept articles ordbokene.no no longer serves |
| `--limit N` | with `--all`: stop after N articles |
| `--out DIR` | the output folder (default ordpar/out/) |
| `--snippets PATH` | where the list view's snippets go for `build_index.py` (default ordpar/.build/build-snippets.json, outside the output, never published); pass the same path to both builds |
| `--articles PATH` | the library (default `articles.jsonl` at the repository root, or in `ORDBOK_DATA_DIR` when that is set) |
| `--audio-names PATH` | the clip names file (§ The audio); read-only. Without it no page has a play button, and a whole build removes the output's `audio/` folder |
| `--levels PATH` | the CEFR levels file (§ The headword line, *The CEFR level box*); default `ordpar/levels.tsv`, read-only; `--levels ""` for none. An article the file lacks gets no box |
| `--mirror-corrections PATH` | the corrections to articles with no library row (§ Corrections to the Norwegian); default `mirror-corrections.jsonl` in the data folder's `review/` (in the public repository `data/review/mirror-corrections.jsonl`); a missing file changes nothing |
| `--measure` | also record each page's size with the paradigm island left out, in `build.json` |

**Speed.** One pass over the mirror indexes it (about 4 s: id to byte offset, lemma form to ids);
rows are then read back by `seek`. A `--all --limit 2000` pass runs at about 430–470 pages a
second end to end (derive, render, write) in one process, so the whole dictionary takes about four
minutes. The listing files add one more pass over the mirror, which parses only the lines that
embed a withdrawn translated article (under a second).

**Testing the build.** The site's tests are in `ordpar/tests/`, indexed in [`tests.md`](tests.md)
with how to run them all. The browser tests (`test_ordpar_browser_*.py`, headless Edge, through
`ordpar/tests/browser/harness.py`) serve the built output on a local port, or the folder
`ORDPAR_TEST_OUT` names, or test another copy given by `ORDPAR_TEST_BASE`
(`ORDPAR_TEST_BASE=https://ordpar.no` for the live site).

## Which articles get a page

**Listed and unlisted** ([46](../../docs/decisions.md#d46)). The mirror records ordbokene's
own index: an article is **listed** when it is in `bm-listed.jsonl`, **unlisted** when it is in
`bm-unlisted.json` (it left the index; `since_404` is null while ordbokene.no still serves it).
`bm-articles.jsonl` carries the listed articles and the unlisted ones still served, and drops the
withdrawn (404) ones. The rule — what has been translated stays — is decided once, for both
builds, by `ordpar/sitegen/mirror.py` (`Listing`, `decide_kept`):

- An unlisted article is **kept** when it is translated (`complete_strict`), unless a **listed**
  article sharing one of its headword strings is translated too; that one carries the English
  (*det aller helligste* 100637 gives way to 114106). The strings compared are the library row's
  forms, the mirror lemmas and, for a withdrawn article, the lemmas of the copy its parent embeds.
  This is a heuristic: an article merged under a different headword is not caught.
- **Pages**: every article `bm-articles.jsonl` carries, and every kept article whether ordbokene.no
  serves it or not. Any other withdrawn article gets **no page**: `--ids` refuses it (a failure
  line in `build.json`), `--all` never lists it. An unlisted article that is not kept but still
  served (*krone* 32274) keeps its page, reachable by its link and never offered by search
  ([`lookup-index.md`](lookup-index.md) § 1).
- A **withdrawn kept** article is built from the mirror's stored copy (`bm/404/<id>.json`) when
  it has one. Where the copy is empty, the page is built from the library row alone: the head
  from the row's forms and English word class, no paradigm island, the "more entries" count from
  the row's forms. `build.json` records how each was sourced (`unlisted_46.kept_404_source`).

On the mirror of 17 October 2026 this meant 94,108 listed articles, 133 unlisted and served,
115 withdrawn; 82 kept (19 served, 63 withdrawn, each embedded in exactly one listed parent), 5
displaced by a listed namesake, and 166 unlisted articles left out of search. `build.json`
records these counts under `unlisted_46`.

**An article with no headword gets no page** ([163](../../docs/decisions.md#d163)). A few
articles in the data have no headword (`lemmas: []`, or only empty or blank lemmas; three in the
mirror of 3 November 2026), and ordbokene.no's own pages for them answered with an error.
`Mirror.index` notes each (`Mirror.has_headword`); the build skips them under `--ids` and `--all`
alike and removes a page an earlier build wrote for one, so neither the offline copy (which packs
whatever article pages the output holds) nor a deploy carries it. They are not failures:
`build.json` lists them under `no_headword_163` (`ids`, and `pages_removed`). They count in no page
figure, get no snippet, are not in the search index (`build_index.build_tables` skips an article
with neither a headword nor an inflected form) or the sitemap, and nothing links to them. The About
page's numbers (`site_stats.measure`) count the mirror's shown articles by `status`, not pages, and
so still include them.

**A set phrase with no row of its own** ([57](../../docs/decisions.md#d57)). A parent's set
phrases block lists every set phrase it cites (`exprs`). Where a set phrase has neither a library
row nor a line in the mirror (withdrawn, or never mirrored), its row is derived from the copy the
parent's own data embeds (the `sub_article` node's `article`; `library.Store.embedded_expr`), and it
shows in the block like any other, as ordbokene.no shows it (*aktmodell* 620: *stå aktmodell*). It
gets **no page** and **no search entry** unless the kept rule above gives it one, so nothing may
link to it: a cross-reference to its id stays plain text (`face.SiteFace.resolvable`).
`build.json` counts these under `cross_references.expressions_from_parent_copy`;
`missing_expression_rows` counts only what is still missing.

**Set phrases with no complete English** ([58](../../docs/decisions.md#d58)). The unit is the
article, embedded or not: a set phrase is either fully translated or shown whole in Norwegian. On a
translated page, the set phrases without complete English of their own come after the translated
ones, in `<div class="ordpar-untr" lang="nb">` under the small label "Not yet translated"; where
none of the article's set phrases is translated, the label is the note "These set phrases have not
been translated yet…" and the section carries `ordpar-untr-only`. The setting "English only"
(`defs` = `en`) hides them (the whole section in the second case); under the other settings they
show in Norwegian with no cue. A listed one also keeps its own Norwegian page and search entry.
`build.json` counts them under `cross_references.untranslated_expressions_in_norwegian`. A small
article whose target has no senses shows them too.

## The output

```
out/bm-en/<id>/index.html   one page per article
out/site/…                  a copy of ordpar/site/ (the shell pages' files, the scripts and sheets)
out/site/article.css        the deck's sheets + the site's rules for the article fragment (page.SITE_CSS);
                            the search page links it too
out/site/page.css           the article page's own rules (page.PAGE_CSS): the "Article view" line,
                            the untranslated note, the table's room, the prose pages
out/site/article.js         the page script (page.PAGE_JS)
out/site/theme.js           the head script (head.THEME_JS)
out/site/ordpar.css         the article and prose pages' one stylesheet (page.COMBINED: article.css,
                            inflection.css, shell.css, page.css, in that order)
out/site/ordpar.js          their one deferred script: the interface strings, then the parts of
                            page.ARTICLE_JS_PARTS, each in its own try
out/site/shell-pages.css    the shell pages' sheet (article.css, inflection.css, shell.css)
out/site/shell-pages.js     the shell pages' script (page.SHELL_JS_PARTS), linked by build_index.copy_shell
out/site/strings/en.json    sitegen/strings.py, merged into the shell's strings
out/index.html              a minimal front page, written only when none is there and marked
                            (page.PROTOTYPE_FRONT) so that the index build replaces it with the search shell
out/about/, help/, coming/, more/, changes/, dictionary-changes/, deck-changes/
                            the prose pages (§ The prose pages), rewritten on every run
out/privacy/, thanks/, survey/
                            written only while their switches are on; removed otherwise
out/sw.js, out/manifest.webmanifest, out/robots.txt
                            ordpar/root/ copied to the site's root: the service worker (scope /) and
                            the app manifest, its theme and background colours rewritten to the
                            default colour scheme's day accent (write_manifest_colours)
out/sitemap.xml             home, About, Help and the other indexed prose pages, and every translated
                            article (write_sitemap); the index build rewrites it with the word pages
out/audio/<k>.json          the clip names, one file per 500 ids (§ The audio)
out/build.json              the stamp and the counts (below); never published
```

and, outside the output, since the output is what gets published:

```
ordpar/.build/build-snippets.json   the list view's snippets, for build_index.py
ordpar/.build/sitemap-articles.json the sitemap's article list, for build_index.py
```

**Not written here:** the word pages and form pages, `/bm-en/<word>/`, and the search shell pages
are the index build's ([`lookup-index.md`](lookup-index.md) § 9); the output's `offline` folder is
`build_offline.py`'s, run after both builds. Entries that `ordpar/root/` once held are removed from
the output on every build (`RETIRED_ROOT`), since copying `ordpar/root/` adds and overwrites but
never deletes, and the deploy publishes every entry of the output but its exclusions. The app
icons are `ordpar/site/icons/icon-192.png` and `icon-512.png`, drawn once by
`ordpar/build_icons.py` and committed.

**Every script and stylesheet is linked with a content hash**, `/site/<file>?v=<hash>`
(`page.asset`; `build_index.py` does the same for its pages), so a browser holding an old copy
fetches the new one as soon as a page changes. The hash is of the file as served
(`page.shipped`: without comments, the combined files joined). So **an edit to any script or
sheet changes every page**; the offline bundles store pages with these hashes blanked and the
service worker puts them back ([`offline-app.md`](offline-app.md) § 2). Every `.js` and `.css`
in the output's `site` folder, and `sw.js`, is written without its comments (`write_assets`;
[61](../../docs/decisions.md#d61)), and the shell pages' HTML sources copied there lose
their comments too (`slim.strip_html`); the sources keep theirs. `inflection.js` is written with
the site's table of paradigm shapes in it (§ Keeping the pages small).

**The snippets file**: `{"<id>": [text, lang]}`, one entry per page built, uncut
(`article.snippet`): the summary gloss on a translated page (its items joined by " · "), else its
first English sense; on a Norwegian-only page its first Norwegian sense, with its
cross-references' homograph and sense numbers dropped (`article.drop_ref_numbers`: *huske (III)*
becomes *huske*; [144](../../docs/decisions.md#d144)). A third element, `[text, lang,
drop]`, is written where the suggestion list's text is not the snippet's first unit (a translated
set phrase with no gloss: `article.dropdown_text`). `build_index.py` reads it from the same default
path (`SNIPPETS_PATH` in both), cuts each to one line and ships it in the index's `snip/` files
([`lookup-index.md`](lookup-index.md) § 3); every row with a one-line definition — the list view,
the suggestions, History, the similar rows after a miss, a word page's rows — shows this line.
`--all` rewrites the file; `--ids` and `--all --limit` update only the entries they built.

**`build.json`** holds the **stamp**, `ordpar build: mirror snapshot <date> · library <commit>`
(the commit is the repository's HEAD; the About page carries it as a comment, and
`build_offline.py` takes it for its manifest), the page counts, the About page's numbers
(`site_stats`), the derive time and errors, the advisories by tag, the concept ids the table
lacks, the cross-reference counts (with the line pairs' matched and unmatched references), the
listing counts (`unlisted_46`), the headword-less articles (`no_headword_163`), the snippets file's
path and counts, the lemma-order rulings not applied (`lemma_order.unmatched`), the change notice
(`change_notice`), the corrections overlay (`mirror_corrections`), the pronunciation runs not
matched, the audio (`audio`), the switches (`privacy_166`, `reports_166`, `survey_173`), the
indexed and `noindex` pages (`search_128`) and, with `--measure`, the sizes.

## The page

`out/bm-en/<id>/index.html`. The language pair `bm-en` is the first URL segment, and the interface
language is never in the URL ([21](../../docs/decisions.md#d21)). Internal links are
`/bm-en/<id>/`; the readable `/bm-en/<id>/<lemma>` form is accepted by the 404 shell's redirect and
never generated. In order:

**`<html>`** carries `lang="en"`, `data-article-id`, `data-lemma`, `data-translated`, and where
they apply `data-other-entries` (only above 0), `data-hg`, `data-hgs`, `data-pos`, `data-word`,
`data-snip` and `data-drop` (§ The favourites attributes).

**The head** (`ordpar/sitegen/head.py`, shared with the index build):

- the charset and viewport;
- **the title**, "word (class) — Norwegian–English dictionary" (`describe.page_title`;
  [128](../../docs/decisions.md#d128)): the headword line's spellings without their
  homograph numerals — the numeral kept where another page shares a spelling and the word class,
  "fange I (noun)" — then the word class without its gender (none for a set phrase), then
  `strings["dictionary_name"]`. The spellings are `build_site.head_lemmas` over
  `article.lemma_groups`, the same as the headword line, so the title never disagrees with the
  page; `data-lemma` and the "N more entries" link read the first of them;
- the canonical, `https://ordpar.no/bm-en/<id>/`;
- **the meta description** (`describe.description`, at most 155 characters): the headword first,
  then the summary glosses joined " · ", ". Definition: " and the page's definition lines,
  numbered when more than one, the glosses never cut (§ What search engines read gives each
  case); `og:description` follows it;
- `<meta name="robots" content="noindex">` on a Norwegian-only page only, the manifest link,
  `<meta name="theme-color">` in the default scheme's day accent
  ([61](../../docs/decisions.md#d61); [`offline-app.md`](offline-app.md) § 7);
- **the head script**, `<script src="/site/theme.js?v=…">` (`head.THEME_JS`), parser-blocking —
  never `defer` or `async` — and before the stylesheet, so the theme, colour scheme and setting
  classes are on `<html>` before the first paint;
- **one stylesheet**, `/site/ordpar.css`.

**The header** (`ordpar/sitegen/chrome.py` `header`, the same on every page;
[63](../../docs/decisions.md#d63)): the skip link ("Skip to the article"), Ordpar and its
tagline, the search box (a GET form to `/bm-en/` that searches on Enter; `shell.js` makes it a
combobox with suggestions while typing and "Recent" when empty), and Search (a magnifier drawn by
`shell.css` at the box's right end; its word "Search" is the accessible name). What needs script
is made by `shell.js` (`addChrome`), not written into the page: Random word, Favourites, Settings,
the "Search English words" switch and the *Norwegian only* icon (§ Settings).

**Random word** opens a random headword's search, `/bm-en/#q=<headword>`, showing every homograph
as a typed search would ([115](../../docs/decisions.md#d115)); on a page that answers searches
in place it is answered there. Its pool, the index's `random.json`, is the headwords whose search shows
first an article that is translated, not a set phrase, and has a summary gloss
(`build_index.random_headwords`; [`lookup-index.md`](lookup-index.md) § 3). **A draw is not a
search**: it is not recorded in History or sent as a search event. Its history entry carries
`{q, random: true}`; from another page the address is `/bm-en/#q=<word>&random`, the mark taken
into the history state and off the address at once (`ordparSearch.takeDrawn`), so a reload, Back or
Forward keeps it a draw. With "Search English words" on it draws an English word (§ The search
features the pages support).

**The "Article view" line**: "Article view", "← Home" (a link to `/`), and "N more entries for
<lemma>" when N > 0, written as the search `/bm-en/#q=<lemma>` (`face.lemma_url`) and pointed by the
index build at the word's own page, `/bm-en/<word>/`, where it has one (`wordpages.patch_article`;
[`lookup-index.md`](lookup-index.md) § 9).

**The card**, `<article class="ordpar-card ordpar-entry">`, the same card as a full search result:
the status caption and note (Norwegian-only pages), the article fragment `<div class="ordbok">`
(§ The article fragment), and the card's foot, `<footer class="ordpar-card-foot"></footer>`,
**empty in the page**. The page script fills it: Copy link and Share (each only where the browser
has the API), "Suggest a correction" while reports are on (§ Report a mistake), and the heart, right-aligned
as under a search result. An article whose Norwegian Ordpar corrected carries the change notice
here as static markup, `<p class="ordpar-change">`, the controls placed before it (§ Corrections
to the Norwegian).

**The footer** (`chrome.footer`, the same on every page): the one-line credit, "Based on
Bokmålsordboka (UiB and Språkrådet) · CC BY 4.0 · Ordpar is independent of both", Bokmålsordboka
linking `https://ordbokene.no/` in general and "CC BY 4.0" linking the licence,
`https://creativecommons.org/licenses/by/4.0/` with `rel="license"` (`chrome.credit`; the words are
`strings.py` `credit`, `credit_source`, `credit_licence`) ([12](../../docs/decisions.md#d12),
[32](../../docs/decisions.md#d32)); then the links Home · Settings · Favourites · History ·
Help · More ways to use Ordpar · About, of which Home, Help, More ways and About are in the markup
and the three after Home are made by `shell.js`; "Privacy" after About while its page is built; on
a phone, on a line of its own, the hint "Install Ordpar as an app"
([68](../../docs/decisions.md#d68); [`offline-app.md`](offline-app.md) § 11). No page links
its own article at ordbokene.no ([63](../../docs/decisions.md#d63)); the change notice is the
one exception. No logos.

**The scripts**: one deferred script, `/site/ordpar.js`, whose parts (`page.ARTICLE_JS_PARTS`, each
in its own `try`, after the interface strings) are, in order: `inflection.js`, `personal.js`
(favourites and history), `report.js`, `lookup.js`, `ahead.js`, `audio.js`, `article.js` (the page
script, written by this build), `mini.js`, `events.js`, `install.js` and `shell.js`. The page
script applies the inflection setting and the moving parts of the definition settings, makes the
card's controls and the heart, and registers the service worker (`/sw.js`, scope `/`;
[`offline-app.md`](offline-app.md) § 4).

**The favourites attributes** ([60](../../docs/decisions.md#d60)). History is a list of
searches, so an article page records nothing; its attributes let a favourites row be drawn without
a fetch, and the search page reads the same attributes from a page it fetches for a result
(`lookup.js` `pageMeta`). Written by `page.personal_attrs` from `build_site.personal_fields`:
`data-hg` (the homograph number, when there is one), `data-hgs` (one number per shown spelling,
"1 2", only where the spellings' numbers differ; `data-hg` is then the first non-zero),
`data-pos` (the index's word-class code: the first paradigm tag, `EXPR` for a set phrase the mirror
does not carry), `data-word` (the headword as the search index shows it, `build_index.display`, only
where it differs from `data-lemma`), `data-snip` (the list view's snippet, cut as in `snip/`; left
out where it equals the meta description, which readers then fall back to; `data-snip=""` when the
snippet is empty and the description is not) and `data-drop` (a translated set phrase with no
summary gloss: its suggestion-list text). The page script calls `ordparPersonal.mountPage`, which
puts the heart (`aria-pressed`, outline or filled, named "Favourite" in both states) after Copy
link and Share. Its look is `.ordpar-heart` in `PAGE_CSS`. The attributes cost about 130 bytes a
page raw, 33 gzipped. With JavaScript off neither the heart nor the header's links show.

**The search page shows these pages' fragments** ([59](../../docs/decisions.md#d59)). It
fetches `/bm-en/<id>/` and takes everything from `<div class="ordbok` to the card's foot,
`<footer class="ordpar-card-foot">`, plus the status caption `<p class="ordpar-caption">`
(`lookup.js` `extractArticle`), then prefixes every id (`scopeArticle`), and takes the change notice
from the foot and puts it after the result's controls. **These markers are a contract with the
search page**: `ordpar/tests/test_ordpar_results59.py` and `test_ordpar_chrome63.py` pin the
shape. The search page draws its own controls under each result (Copy link, Share, "Suggest a
correction", the heart: `lookup.js` `resultControls`). The small article is cut from the same
fragment and never has the notice.

## The article fragment

`<div class="ordbok">`, rendered by `ordpar/sitegen/article.py` over the deck's renderer
(`ordbok_gen.py`) with the site's face (`ordpar/sitegen/face.py`). **The fragment carries no
interface string**: its section labels are fixed in `article.py`, so the same fragment serves
every interface language. Its parts, in order: the headword groups with their word-class lines,
the summary gloss, the paradigm island and the inflection toggle, Pronunciation, Etymology, Senses
and Example Sentences, Set phrases (ordbokene.no's English labels;
[22](../../docs/decisions.md#d22)). A set phrase's own page prints no word class under its
headword, as ordbokene.no's (the row keeps `pos_en` "fixed expression").

**Languages.** Norwegian is `lang="nb"`, English `lang="en"`: on the fragment's root (`en` on a
translated page, `nb` on a Norwegian-only one), and below it only where an element's language
differs from its parent's — except that a line pair's two lines and every small-article span always
carry theirs, since the sheets select them by attribute (§ Keeping the pages small).

### The headword line

**Headword groups** ([36](../../docs/decisions.md#d36)) come from the mirror article's lemmas,
grouped by the union of each lemma's `paradigm_info[].tags` and the order its genders first appear,
in the mirror's order: one line per group, each over its own word-class line, none a link (it is
the page). *bru, bro* is one group, "feminine or masculine"; *anskaffelse* (masculine) and
*anskaffing* (masculine or feminine) are two. The label is `postags.pos_en`, the deriver's table,
with the genders in the data's order, as ordbokene.no prints them.

**Homograph numerals** ([93](../../docs/decisions.md#d93)): a Roman numeral after *each*
spelling, its own lemma's number, none for 0 — "lysing I, lysning II", "tørre II, tore II". Each
numeral is `aria-hidden` with a visually hidden "homograph N" beside it
([33](../../docs/decisions.md#d33)).

**Our spelling order.** Where the deck's normalization log rules an order for an article's
headword spellings (its `kind: "lemma-order"` lines whose `where` starts "top-level lemmas": *tørre,
tore* 61543, *aksjemegler, aksjemekler* 554), `ordpar/sitegen/lemma_order.py` applies it in
`Mirror.data`, so the inflection table and every other reader of the lemmas follow. Each spelling
keeps its own numeral and group. A ruling that no order of the mirror's spellings matches is not
applied and is listed in `build.json` `lemma_order.unmatched`. A new ruling in the log needs no code.

**The word-class line** ([76](../../docs/decisions.md#d76)) is printed as ordbokene.no renders
it: the word class in small capitals, then the gender or subclass in italic lower case, with no
brackets or comma — "NOUN *feminine or masculine*". `article.pos_html` splits the label (`<span
class="ordbok-pos">noun <i>feminine or masculine</i></span>`; "verb" or "proper noun" is the class
alone), and a screen reader hears "noun feminine or masculine". The words are `pos_en`'s (each
checked against ordbokene.no's English pages, with its wording differences "subjunction" and
"uninflectable"). The colour is the deck's muted grey; the size is the body text's
(`.ordbok-pos{font-size:1em}`). The same rule styles the label wherever a fragment shows; a small
article has none. The list view's and inflected-form rows show the class alone in their own rule,
`shell.css` `.ordpar-pos`.

**The lone `false` tag.** A set phrase prints no word class (§ The article fragment; `article.head_html`
writes no `ordbok-pos` line for a "fixed expression"). The lone `false` tag is a data error read the
same way ([57](../../docs/decisions.md#d57); `scripts/postags.py` `pos_en`): an
article whose only paradigm tag is the string `false` is a set phrase, so its page prints no word
class where ordbokene.no prints `tags.false`. In the mirror the build reads (the snapshot of
26 October 2026) five articles carry it: *piggene [ut|ute]* 104373, *poppe [opp|fram|ut]* 125146,
*ikke [det|et] plukk* 125183, *[tett|tjukk] i pappen* 125246 and *legge [på|i] prokrustesseng*
125458.

**The CEFR level box** ([187](../../docs/decisions.md#d187)). With the setting `levels` on
(Article › Language, off by default; the preset *For learners* turns it on), a small box at the end
of the first headword line, after the last spelling's sound icon, shows the article's level in the
Common European Framework of Reference (CEFR): A1, A2, B1, B2, or C, which holds C1 and C2 together.
Each set phrase embedded in the article has the same box, with its own level, at the end of its
term's line, after its sound icon. The look is a thin outline in the muted grey of the homograph
numeral and the word-class line (`--ordpar-muted`), the level as text at 0.75 rem, weight 600,
padding .2em .38em, radius 3 px, .55em after what precedes it (`page.py` `SITE_CSS`, `.ordpar-level`).
The markup (`ordpar/sitegen/levels.py` `box_html`) is always in the page; the sheet draws it only while
`<html>` carries `ordpar-levels-on`, which the head script puts there before the first paint, so
nothing moves on load, and with the setting off the box is neither drawn nor read. The letters are
`aria-hidden` and carry the tooltip ("B1 · intermediate", `strings.py` `level_tip_*`; hover only); a
visually hidden ", level B1" beside them is what a screen reader hears, as part of the heading's
name. The box is `lang="en"` and `data-nosnippet`, and not selectable. The levels come from
`ordpar/levels.tsv` (`article<TAB>shown`, one line per article id, a set phrase by its own id),
which `ordpar/levels_import.py` writes from Ordpar's own judged levels; the build reads it with
`--levels` and records in `build.json` `levels` how many articles and embedded set phrases got a box; it also prints how many have no level, so newer Bokmålsordboka data shows the new articles that lack one.
A caller of `article.fragment` that passes no levels (the Anki deck) gets the markup without boxes.
Not on the search's list rows, in a hover peek or in a small article (`mini.js` removes any it
copies). Tests: `test_ordpar_levels187.py`, `test_ordpar_browser_levels187.py`.

**The set phrases by level** ([188](../../docs/decisions.md#d188)). The setting `phraseorder`
(Article › Language, right below `levels`, shown only while it is on) orders an article's embedded
set phrases alphabetically, as the page has them and as Bokmålsordboka does (`alpha`, the default),
or by level (`level`): A1, A2, B1, B2, C, then any phrase with no level, each level in the
alphabetical order. In a translated article the order applies within each group: the translated
phrases first, then the untranslated ones under their own heading. The preset *For learners*
chooses `level`. The level order applies only while the boxes are on, so it never shows without
them. The pages are built in the alphabetical order; the sheet draws the other. Each levelled block carries
its level (`<div class="ordbok-expr" data-level="B1">`, `article.py` `_expr_html`) and the section,
where any block does, the class `ordpar-exprs`; while `<html>` carries both `ordpar-levels-on` and
`ordpar-phraseorder-level` (the head script's, before the first paint), the section and its
untranslated group are flex columns and each block takes its place by `order` (`page.py`
`SITE_CSS`), so the order is in place at the first paint and nothing moves on screen. In the
flex column the gaps are rebuilt to match the block layout to the pixel (the rule's comment says
how). So that a screen reader and the Tab key follow the drawn order too, the page script
(`page.py` `PAGE_JS` `phord`, run from `ordparDefs`: at load, whenever the search page puts an
article on screen, and at a change of a setting in place) puts each section's own blocks, and its
untranslated group's apart, in the same order in the page itself, and back in the built order when
either class goes. Each block's place as built is recorded once, so the way back never re-sorts
text; only the blocks out of place are moved, each with what it holds (an open small article, the
eye's hidden lines, the examples shown), and the focus, if it was inside one, is given back without
scrolling. The sheet draws the same order before and after, so the script moves nothing on screen;
at a change of a setting the shell sets the class and runs the script in one go, before anything is
drawn. Anchors and links to a set phrase (`x<id>-`), the sound icons, the eye, "Show N more
examples", Norwegian only and print need nothing of their own; the report reader's copy reads the
built page, so it keeps the alphabetical order. The rules reach only a section's own
blocks and its untranslated group's, so a small article, whose box copies the blocks it shows,
keeps the alphabetical order and the block layout's spacing even when it opens inside a block. A caller that passes no levels gets the markup
as before. Tests: `test_ordpar_phraseorder188.py`, `test_ordpar_browser_phraseorder188.py`.

**The summary gloss** sits under the headword groups in its authored order
([42](../../docs/decisions.md#d42)), semibold at 1.1 times the body size in the text colour;
its sense marks stay regular.

**The paradigm island and the Inflection toggle** ([43](../../docs/decisions.md#d43)): the
paradigms as a compact JSON island ([`inflection-table.md`](inflection-table.md) § 1) and a mount
inside a closed "Inflection" toggle, shipped hidden and revealed by `inflection.js` only when a
table rendered. Where no paradigm has a form to show, neither island nor toggle is written. A row of
the degrees-of-comparison table with no form in any cell (a paradigm without comparison beside one
with it, *avsindig* 3768) is not drawn, as on ordbokene.no ([162](../../docs/decisions.md#d162);
`inflection.js` `buildTable`).

### Definition lines and their settings

**The line pair** ([37](../../docs/decisions.md#d37), [53](../../docs/decisions.md#d53),
[54](../../docs/decisions.md#d54)). On a translated page each definition line — sense,
subsense, set-phrase sense, etymology — is a pair in one wrapper (`article.line_pair`,
`.ordpar-pair`): the Norwegian line first, carrying the cross-reference links, then the English
line, whose references are **partner words**. The Norwegian line renders first, recording each link
by its target URL; each English reference then takes the first unclaimed link with the same target
(`#defN` included), in order, and renders as the same link inside `<span class="ordbok-xref
ordpar-xen">`, with its own peek: the Norwegian face, or, for a Norwegian word *mentioned* on the
English line ("developed from *hus*"), the English gloss (`face.SiteFace.record_links`,
`partner_links`). **The link lives on the line that leads**, which is the emphasized one (below):
the sheet makes the other line's links plain words with no peek. An English reference with no
partner is a plain word in every setting; a Norwegian one with no partner keeps its link under
`emph` = `no` and `defs` = `no`. `build.json` counts both kinds (both 0 in practice). A unit with
no Norwegian line renders its English alone, with the links. On a Norwegian-only page the Norwegian
line is the only one and carries the links. Each segment the line joins with ";" breaks onto its
own line.

**`defs`** picks which lines show: `both` (default, and with JavaScript off) — both lines, the
emphasized one in the main style, the other faded; `en` — the English alone, in the main style,
its partner words the links; `no` — the Norwegian in the main style with its links, and under it a
"Show English" cue that opens the English beneath in the translation style, whatever `emph` says.

**`emph`, the emphasized line** ([87](../../docs/decisions.md#d87),
[174](../../docs/decisions.md#d174)): `no` (default; the head script adds `ordpar-emph-no`
unless `en` is stored) or `en` (no class, so this is the look with JavaScript off). Under `en`,
wherever both lines show and `defs` is not `no`: the English line in the text colour at 1em, the
Norwegian above it faded (`--ordpar-muted`, #757070, at night #b9b6b6, at .95em), the English
line's partner words the links. Under `no` the reverse: the Norwegian in the main style with the
links, the English in the muted grey at .95em with its partner words plain. The rule covers
definitions, subsenses, set-phrase senses, formula lines (under `formulas` = `both`) and etymology
(under `ety` = `both`), and the small article's `mini-pair` likewise. **A line shown alone leads
whatever `emph` says** (a formula line under `formulas` = `no`, the etymology under `ety` = `no`),
which is why the sheet's faded rules come in three selectors: definitions (`span.ordbok-def`, not
`.ordpar-fml`), formula lines (`.ordpar-fml`, unless `formulas` = `no`), the etymology
(`span.ordbok-body`, unless `ety` = `no`). Example sentences are not line pairs: the Norwegian leads
there in both values. The sheet alone does this (`page.SITE_CSS`); no markup depends on it.

**`subsenses`** ([90](../../docs/decisions.md#d90)): `defs` (default: as the definitions) or
`en` (`ordpar-subsen-en`). Under `en`, where both lines would show — `defs` = `both`; in a small
article unless it shows English alone or `defs` = `no` — a real subsense's pair
(`div.ordbok-sub:not(.ordpar-comp)>.ordpar-pair`) shows its English line alone, in the main style,
its partner words the links. Under `defs` = `no` it keeps its reveal. A formula line follows its own
setting. A set phrase's numbered senses (`ol.ordbok-subsenses>li`) and a solo sense's numbered
subsenses read as senses and follow the definitions; a `div.ordbok-sub` under a set phrase's sense
follows this setting. Few lines are affected: about 60 prose subsense pairs in the library, beside
about 1,100 formula lines.

**The moving part is the page script's** (`page.PAGE_JS`), since only a script can have set a
non-default value: under `defs` = `no` it inserts the "Show English" cue (`strings.show_english`)
before each line pair's English line; no page ships one, and a small article never gets one. It
runs on load and again from `window.ordparDefs()`, which the shell calls after a setting changes
and the search page after it inserts an article. `ordparDefs` also applies `infl` = `open` once per
Inflection toggle it has not seen (so a toggle added later follows the setting and one the reader
closed stays closed), inserts the "Example" headings and the eye (below), cuts the example lists,
and calls `window.ordparMinis.scan()`, so `minifetch` = `page` loads the targets of links the search
page inserted.

**Formula lines** ([81](../../docs/decisions.md#d81)). A definition line whose whole Norwegian
text is a formula — `article.FORMULA_RE`: "(brukt) som (forsterkende) <word class>", the class one
of adverb, adjektiv, substantiv, preposisjon, pronomen, verb, interjeksjon, konjunksjon,
subjunksjon, determinativ, artikkel; or "brukt i nøytrum", "brukt i ikke-tellelig betydning"; with
or without the final colon, nothing else on the line — is a pair marked `ordpar-fml`
(`article.is_formula`, `line_pair(…, formula=True)`), on senses, subsenses and set-phrase senses.
The setting `formulas` decides it in the sheet, whatever `defs` says: `both` (default,
`ordpar-formulas-both`) — both lines in every `defs` setting, following the emphasis (under `defs`
= `no` the English behind its cue), the compound labels English; `en` (no class) — the English
alone in the main style, shown at once with no cue; `no` (`ordpar-formulas-no`) — the Norwegian
alone, and every compound-list label in Norwegian. In a small article alike (`mini-pair.ordpar-fml`;
under `mini` = `en` both lines too). Over the library there are about 1,150 formula lines (nearly all
on subsenses; "brukt som adverb:" alone 416), over the whole mirror about 1,550. Near misses stay
prose: "brukt som påpekende pronomen:", "som adjektiv i presens partisipp:", "brukt som
forsterkende forledd", "brukt som forsterkende adverb: svært".

**The etymology line** ([84](../../docs/decisions.md#d84)): `ety` = `en` (default) | `no`
(`ordpar-ety-no`) | `both` (`ordpar-ety-both`) decides which line of the etymology's pair shows, in
every `defs` and `mini` setting. `en`: the English alone, in the main style, no reveal cue, its
partner words the links; `no`: the Norwegian alone; `both`: both lines, following the emphasis under
`defs` = `both` and `en`, the English behind the cue under `defs` = `no`, both in a small article
under `mini` = `en`. The sheet alone decides it: the etymology is the one inline section holding a
line pair (`.ordbok-inline>.ordpar-pair`), and in a small article, which shows an etymology only for
a page with no senses, the pair the small-article script copies to the body's top level
(`.ordpar-mbody>.mini-pair`).

**Rules that must not reach into a small article.** A small article opened from a line sits inside
that line's span. So every rule that reaches a link or a peek inside an article's line pair — the
plain partner words, the etymology's relinking, the faded line and its "both" cases, the subsense
English — ends in `:where(:not(.ordbok-xmini *))` ([91](../../docs/decisions.md#d91)), and the
small article's links follow its own rules (`.mini-pair`, `mini`, `emph`). `:where` adds no
specificity, so outside a small article the cascade is unchanged. A new rule of that kind must
carry the same ending.

### Examples

**The default look** ([87](../../docs/decisions.md#d87)), with JavaScript off too: no
"Example" heading; every example list a quote block (`margin:.3em 0 .2em 1em`, `padding-left:.6em`,
a 2px left bar in the deck's `.ordbok-sub` colour, #e0d8d9, at night #656161); a real subsense
(`div.ordbok-sub`, not a compound list) a bullet 1.1em in, without the bar, the bullet in the sense
numerals' colour (`--ordpar-maroon`, the scheme's day accent; #b9b6b6 at night); a compound list
(`.ordbok-sub.ordpar-comp`) a plain line at the end of its sense, as ordbokene.no's. A numbered
subsense keeps its number. **The bullet is a `display: list-item`**, which by itself advances the
enclosing list's implicit `list-item` counter; the rule therefore carries `counter-increment:
list-item 0` (`none` would not do: it is already the computed value, and the automatic step happens
unless the declaration names `list-item`), so the senses run 1, 2, 3 ([98](../../docs/decisions.md#d98)).
Articles, search results and small articles alike; a set phrase's example lists and a Norwegian-only
page's are quote blocks too.

**The layout closer to ordbokene.no** ([87](../../docs/decisions.md#d87)): `layout` = `ordpar`
(default) | `ordbokene` (`ordpar-layout-ordbokene`), under Style. Under it: an "Example" heading
before a sense's own example list (above its subsenses; none on a subsense or a set phrase;
"Example" whatever the count, as ordbokene.no's), in the accent, semibold, at the body's size, the
heading and the list flush with the sense's text, no bar; a subsense's examples under its bullet's
text, no heading; other example lists without their bar, 1em in. The heading is
`.ordpar-exhead`, its words `strings.example_heading`: an `h4` in an article (one level under its
section's `h3`; in a search result `aria-level` one under the section's), a `div` in a small
article. **The page script inserts it** (`PAGE_JS` `exheads`, from `ordparDefs`, before each list
`XL` names), only while the setting is on, once per list; the sheet hides it when the setting goes
off; the small-article script calls `window.ordparExHeads(box)` after it cuts one. Inserting it by
script means no page's markup, and so no offline bundle, changes for an opt-in look; the cost is
that the headings appear when the deferred script runs, after the first paint.

**The examples' English** (`examples` = `both` | `no`; [111](../../docs/decisions.md#d111)):
under `no` (`ordpar-examples-no`) each example's English is behind its own "Show English" cue.

**The eye** (`exeye` = `off` (default) | `on`; [131](../../docs/decisions.md#d131)). With it on,
the page script (`_PAGE_JS` `eyes`, from every `ordparDefs`) puts a `<button>` in a
`span.ordpar-exeye`, first in the `.ordbok-head` of every `.ordpar-article` that has an example with
English — the article page, a word page, a search's article shown whole, an article opened in a
list or favourites row — never in a small article or a row's button. One name in both states,
"Hide the examples' English" (`strings.exeye_button`), with `aria-pressed` (pressed = hidden). A
press switches that article only: under `examples` = `both` the article gets `ordpar-exhide` (its
examples' English hidden as under `examples` = `no`, each revealed by its cue); under `examples` =
`no` it opens every example (`.ordpar-open`); the examples opened one at a time close first. A
change of `examples`, or the eye turned off, puts every article back. The look: floated right on
the headword's line, a round outline in the cue's grey (#c4bcbd, at night #656161), the eye icon,
filled with the accent and struck through while pressed, an unseen 44 × 44 px tap area.

**What the eye hides** (`exeyewhat` = `examples` (default) | `all`;
[186](../../docs/decisions.md#d186)), on the settings page right after the eye and only while it
is on; no preset names it, so every preset puts it at `examples`. Under `examples` the eye is as
above. Under `all` (`ordpar-exeye-all`, from the head script and `shell.js`) the eye goes on every
article shown whole that has an English line (`enOf`), in the same places, and on none while
definitions are in English only (`ordpar-defs-en`: a hidden definition would leave no Norwegian line
above its cue) or under Norwegian only (the sheet hides it, as above). Its name follows its state:
"Hide the English", pressed "Show the English" (`strings.exeye_all_hide`, `exeye_all_show`). A press
(`blank`) blanks that article only (`ordpar-blanked`): the reader's closed pairs and examples are
marked open first (`ordpar-eyeopened`; their own cues hidden by the sheet), the etymology's excepted;
then every English line — the headword's gloss, each line of each definition (a formula's too; a
definition of several lines split at its `<br>`s into `span.ordpar-eyel`), each example's English,
each set phrase's — is hidden (`.ordpar-eyehid`) behind its own "Show English" cue, a `.ordbok-cue`
button marked `data-ordpar-eyecue`, in the line's place. Never the etymology, which stays as the
reader's setting draws it; never a line in a peek, a small article or a row's button; a line the
settings do not draw at all is left alone, while an example cut by the limit is blanked, so "Show N
more" opens it blanked and the examples shown never change at a press. An example's cue is the
examples' cue as it stands; under any other line an empty block (`.ordpar-eyefill`) or a negative
margin makes the cue take the hidden line's height (`fitcue`; a line of several rows as one row), so
a reveal moves nothing below a one-row line. A cue pressed shows its line (`.ordpar-eyeshown`); a
press on that line hides it again, its cue back and focused — taken before the click handler's own
close of an opened pair, so the pair stays open. While blanked, no hover peek shows in the article (a
small article's own excepted), and a list row's glosses are hidden (`ordpar-row-blanked`). The second
press (`unblank`) gives the article back exactly, the reader's own openings and hidings included. A
change of any setting the article depends on (`eyesig`: the eye's two, the definitions, examples,
formula, etymology, subsense, layout, limit, emphasis and label settings, Norwegian only) gives every
blanked article back first, at the start of `ordparDefs`, so none is left half-blanked.

**The examples limit** ([112](../../docs/decisions.md#d112)): `exlimit` = `all` | `1` … `10`
(default `all`), the one setting drawn as a drop-down (`control: 'select'` in `shell.js`
`SETTINGS`). The head script and `shell.js` put `ordpar-exlimit-<n>` on `<html>`, so the sheet
(`page.EXLIMIT_CSS`, one rule per limit) cuts every example list, before the first paint, to its
first n items — each sense's and subsense's list on its own, in articles, full search results,
list and favourites rows' articles and set phrases, in the page's order (Bokmålsordboka's examples,
then Ordpar's added ones, which count). **Never a small article's**: it keeps its own cap
(`mini.js` `EX_BUDGET`, six in all). `exmore` = `on` (default) | `off`: the page script (`exmore`)
puts a line under each cut list, "Show N more examples" / "Show 1 more example"
(`examples_more`, `examples_more_one`), a button in the cue's look (`.ordbok-cue`) that opens the
rest of that list in place (`.ordpar-exopen`); `off` (`ordpar-exmore-off`) hides the lines. The
settings page hides `exmore` while `exlimit` is All. With JavaScript off nothing is cut.

**The added example's mark** reads "Example added by Ordpar (not from Bokmålsordboka)" on hover
(`article.ADDED_MARKER`); the deck keeps its own wording.

### The compound line, the "Se:" line, pronunciation

**The compound line** ("as a suffix in words such as: *gangbru* …"). **Its English label is the
row's** ([151](../../docs/decisions.md#d151)): the deriver gives each Norwegian intro its own
label from one table (`derive.COMP_INTRO_LABELS`: "som etterledd i ord som" → "as a suffix in
words such as:", "i ord som" → "in words such as:", "for eksempel" → "for example:" and the rest),
stores it lowercase-initial, and stores the intro itself in the block (`intro`). The site prints the
label lowercase-initial as every other line ([47](../../docs/decisions.md#d47));
`face.lowercase_comp` lowercases it at render time, which only matters for a row derived before the
deriver did. The block is `div.ordbok-sub.ordpar-comp` (`article.comp_html`; the small-article
script tells it from a subsense by the class). On a translated page its label carries both
languages, `<span class="ordpar-cl-en">as a suffix in words such as:</span><span
class="ordpar-cl-nb" lang="nb">som etterledd i ord som</span>`, the sheet showing the Norwegian only
under `formulas` = `no`. **The Norwegian label is the block's `intro`** (`article.comp_nb_label`):
the capture's own words, so a corrected misspelling shows corrected, printed as ordbokene.no prints
it, lower case, no colon. An article with no library row is derived from the mirror at build time
(`library.Store.derived`) and carries the mirror's intro the same way. `article.COMP_NB` is only for
a block derived before intros were stored. **A Norwegian-only unit** (a Norwegian-only page, and a
translated page's untranslated set phrases; [118](../../docs/decisions.md#d118)) draws its lists
through `article.comp_html_nb`: every compound a link to its article, the one label the Norwegian
intro, whatever the `formulas` setting. **A list with no intro has no label line**; a list with
neither intro nor compounds is not drawn. An intro the table does not know is labelled "in words
such as:" and listed by the deriver (`comp-intro-unknown`), and
`ordpar/tests/test_ordpar_complabels151.py` fails on it, over the captures and the mirror, so a new
intro from ordbokene.no stops a deploy until it has a label. Over the mirror there are about 2,700
lists, "som etterledd i ord som" 2,556 of them. **The label is upright** in every setting, as
ordbokene.no prints it: `.ordbok .ordpar-comp>.ordbok-def>em:first-child{font-style:normal}`
overrides the deck's italic `.ordbok em` on the line's first `<em>`; the compounds keep their look.

**The "Se:" line of a set phrase** ([153](../../docs/decisions.md#d153)). A set phrase's own
page shows ordbokene.no's `Se: …` line, naming the words the phrase is built from (*aksle seg*:
"Se: *aksle*"). Nothing is authored: the deriver keeps it in the unit's `see` field (a
Norwegian-only page's row is derived from the mirror the same way), and `article.see_html` draws it
on a line of its own (`ordpar-see`, a block) after the unit's definition line and before its
examples, where ordbokene.no draws it. Its label is a formula line's: on a translated page "see:"
(`ordpar-cl-en`) and ordbokene's own word, "Se:" or "Sjå:" (`ordpar-cl-nb`), the Norwegian shown
under `formulas` = `no`; on a Norwegian-only page the Norwegian alone. It is upright and not
`ordbok-def`, since the meta description and the small-article script's `isDefLine` read
definitions alone. Its links are drawn inside `norwegian_only`, so each peeks its target's summary
glosses where it has them, else nothing ([119](../../docs/decisions.md#d119)); the page's
library loads the see targets (`library.see_ids`). **Only on the set phrase's own page** — the page
`build_site.Builder.page` builds (`fragment(…, see_lines=True)`) and whatever lifts its fragment
whole (the search page, the offline copy) — never on a set phrase embedded under its headword
(`_expr_html`), and not on the Anki deck's cards (`see_lines` defaults off). The small article
leaves it out; the one-line switch is `mini.js` `SEE_IN_MINI`. About 9,000 of the mirror's 9,054
set phrases carry one. Test: `ordpar/tests/test_ordpar_selines153.py`.

**The pronunciation** ([123](../../docs/decisions.md#d123); `ordpar/sitegen/pronunciation.py`).
The mirror article's `body.pronunciation` (library rows do not carry it), on every page that has it:
`section.ordbok-sec.ordbok-inline.ordpar-pron`, labelled "Pronunciation", after the inflection toggle
and before the etymology, as ordbokene.no's page has it. The respellings verbatim, `lang="nb"`; a
`pronunciation_guide` item in italics, a `grammar` or `entity` item upright (its concept's
expansion); several entries joined by an italic *eller*, or ", " before an entry that opens with a
template item. The words around the respellings are matched as runs (the template's words, the
closed `LITERAL_WORDS`, the connectors "i" and "form") and looked up whole in
`pronunciation.PHRASES`; on a translated page each run is `<span class="ordpar-pg-en"
lang="en">in the plural</span><span class="ordpar-pg-nb">i flertall</span>`, the Norwegian shown only
under `formulas` = `no`; on a Norwegian-only page the Norwegian alone. An entry with a run the table
lacks is Norwegian whole (`build.json` `pronunciation.unmatched`). The note on the marks is the Help
page's § Pronunciation (`/help/#pronunciation`, from `ordpar/help.md`). A small article leaves the
section out.

### Anchors

([57](../../docs/decisions.md#d57)) **Every id on a page is unique.** The article's own senses
and subsenses carry the bare `id="def<N>"`, `<N>` being ordbokene's definition id, and every
cross-reference on the site links to these (`face.site_url`, `/bm-en/<id>/#def<N>`). A set phrase
embedded in the set phrases block numbers its definitions in its own article, so its ids would
collide with the parent's (on 486 pages before the fix); they are prefixed `x<expression
id>-def<N>` (`article.expr_anchor_prefix`). Nothing links to an embedded set phrase's sense: a
reference to a set phrase goes to its own page, and the deriver resolves a `#defN` on the parent
only against the parent's own units (`derive._source_def_ids`). Ordbokene.no's own page repeated the
id (*ikke* 25712, checked 19 October 2026); Ordpar diverges on purpose. Where the data itself gives
two definitions one id (*uhørt* 63992, id 4), the first keeps `def4` and the repeat, which no link
can reach, becomes `def4-2` (`article._unique_sense_ids`).

## Cross-references and the small article

([80](../../docs/decisions.md#d80)) A cross-reference is a plain link to the target's page with
its hover peek:

    <span class="ordbok-xref"><a class="ordbok-xword" href="/bm-en/48112/#def2"><em>renne (II, 1)</em></a><span class="ordbok-xpeek" lang="en">to run</span></span>

(`face._link`; `#def<N>` for one sense; the peek drawn only where a title exists, and never taking
the pointer, [77](../../docs/decisions.md#d77)). No checkbox, backdrop or small article is in
the page: the face's small-article shim draws nothing and only hands the link its URL. Without
JavaScript a click opens the target's page.

**The peeks.**

- **The Norwegian line's peek is the target's headline set**: a bare link (no `#def<N>`) in a
  Norwegian definition, subsense or etymology line to a target with a summary hovers the target's
  whole `summary.gloss`, joined " · " (*hos* → *hus* reads "a house · a building"). `MarkupShim.pair_view`
  applies it to the Norwegian side (`face.headline_view`, through `markup._inject_headlines` and
  `headline_gloss`) for the page's own row and its set phrases. A `#def<N>` link and a target with no
  summary keep the citing gloss; an untitled link with no English partner on a translated line stays
  without a peek; the examples' Norwegian keeps its stored titles.
- **A Norwegian-only unit's link takes its target's English** ([119](../../docs/decisions.md#d119)):
  on a Norwegian-only page and in a translated page's untranslated set phrases
  (`article.norwegian_only`), an untitled link to a translated target gets, from the target's library
  row (`face.SiteFace.target_english`): for a bare link, the target's summary glosses joined " · ";
  for a `#def<N>` link, that sense's whole English definition line, broken at its `;<br>`, in `<span
  class="ordbok-xpeek ordpar-nbdef">` (regular weight, wrapping at 22rem) and left out of the small
  article's header. Nothing where the target is untranslated, has no summary (bare) or the sense has no
  English. `build.json` counts them (`cross_references.nb_target_english`). **So a Norwegian-only page
  depends on its targets' English and changes when one of them is translated.**
- **Placing the peek** (`PAGE_JS` `place`, on `mouseover`; [69](../../docs/decisions.md#d69)):
  a peek that would pass the window's right edge is moved left, its width capped likewise, and its
  arrow moved back by as much (`--ordpar-peek-dx`) so it still points at the word. On a touch
  screen no peek shows. `peek` = `off` hides every peek.
- **The first Norwegian definition as the peek** ([185](../../docs/decisions.md#d185)): with
  `peek` = `nb`, every peek a link would show is its target's first Norwegian definition instead, by
  the code the Norwegian-only view uses (`ordpar-nbo-hovnb`, `mini.js` `nbPeek`; § Norwegian only,
  and the labels in Norwegian, *The hovers*, which also says how it follows the Loading setting): in articles, word pages, the search page's articles, small articles and nested ones,
  and the offline copy. A link to an untranslated word, which has no English peek, gets one too. An
  English partner word, which carries no `data-s`, takes the key of the Norwegian link to the same
  target in its pair (`mini.js` `snipKeyOf`). The Norwegian peek is a child of the link, as the
  English one is, so the sheet's rules that decide which line's peeks show apply to it unchanged.

**The small article** (`ordpar/site/mini.js`, in `ordpar.js` after `article.js`; linked by the search
page and the 404 shell after their `article.js`) upgrades every such link — on the article page, in
the search page's lifted articles and in an opened list row, one listener on the document — unless
`xref` = `page`, where a click opens the page.

- **On a click** it puts `ordpar-mopen` on the link's `.ordbok-xref` (which hides the link's own
  peek while the box is open: `.ordbok-xref.ordpar-mopen>.ordbok-xpeek{display:none!important}`, so no
  showing rule outranks it), appends a backdrop (`.ordbok-xback`) and the box (`.ordbok-xmini` >
  `div.mini.ordpar-fmini`), shows the header at once, fetches the target's page and fills in the
  body: online through the browser's HTTP cache, offline from the service worker's bundles (the
  worker answers a fetch of `/bm-en/<id>/` as it answers a navigation). It shares the search page's
  fetch (`ordparSearch.fetchArticle`), so a result and a small article of the same article are one
  request; every parsed page is kept for the page's life. A failed fetch opens the page. A click on
  the backdrop, Escape, or opening another closes it.
- **Placing the box** (`PAGE_JS` `place`, called when the box opens and fills, and on every
  `resize`): just below the word; if it would pass the window's right edge it is moved left to end
  8 px short of it, never past the left edge; its width is capped at the window less 1rem
  (`.ordbok-xmini`, `SITE_CSS`). **`place` measures the box parked a window-width to the left**
  (`left:-100vw`), never at its natural place: a box overhanging the right edge, even for one forced
  layout, widened a phone browser's layout viewport and made the page jump
  ([91](../../docs/decisions.md#d91)). The base `left` of both boxes is 0.
- **The header** is the link's own words as the headword, linked to its `href` (`.mini-hw a`), then
  " — " and the peek's gloss; for an English partner word (whose peek is Norwegian) the two are
  swapped, so the header always reads the Norwegian, then the English. Which word is Norwegian is read
  from the link's own `<em>` (the markup wraps the visible word exactly when it is the Norwegian side),
  not from a `lang`, so a Norwegian word mentioned on an English line is not swapped. A link with no
  peek gives the headword alone.
- **What is cut** (`cut`): a `#def<N>` link gives that sense (`li#def<N>`, or a solo sense's
  `div#def<N>`) with its subsenses; a subsense's anchor gives its sense with the subsenses (the deck's
  `mini._anchored_sub_block`), or the subsense alone where its sense has no definition of its own and
  no other subsense; an anchor the page lacks, or a link to the whole article, gives every sense.
  Everything outside the senses goes: the word-class line, the summary gloss, the etymology, the
  inflection, pronunciation, the set phrases, the foot. A page with no senses gives its etymology and
  its set phrases (one example each), else its "not defined" note. `minicontent` = `full` (default):
  each kept sense whole; `slim`: the deck's rules (`scripts/mini.py`) — in a whole-article box of
  several senses a sense keeps its subsenses only when it has no definition of its own, and a
  compound list shows only on a unit with no example. In both, the example budget (`allocate`): one
  example a unit where it has any, then each unit's second, third… in turn while the box's total is
  under six; every example counts, so a Norwegian-only target gets extras too.
- **Its languages.** Every kept `.ordpar-pair` becomes a `.mini-pair`, so the setting `mini`, not
  `defs`, decides: both lines (the Norwegian first, the English in the article's grey), or under
  `ordpar-mini-en` the English alone in the main style; on a pair's English line a partner word is a
  plain word unless the box shows English alone. No reveal cue; every id in the cut is dropped (the
  target's `def<N>` would clash with the page's own).
- **Its look** is the article's, since it is the article's markup: quote-block examples, bulleted
  subsenses, the compound line, the "Example" headings under `layout` = `ordbokene`, sense numbers on
  a several-sense box, the emphasized line. Inside it a link is in the text's colour with the accent
  underline, as the article's. The box is the deck's `.mini` (border, shadow, padding, heading, and
  its 19rem width on a phone); the body `.ordpar-mbody` at 1rem; the header (`.mini-head`, shared with
  the deck through `scripts/mini.py`) 1.1rem, its gloss (`.mini-gloss`) 1rem, semibold, upright, in the
  text colour ([114](../../docs/decisions.md#d114)). `minitext` = `smaller`
  (`ordpar-minitext-smaller`) gives the header 1.02rem and the gloss and body .92rem.
  `minispacing` = `article` (default) is the article's spacing (line height 1.5, examples .3em
  apart); `compact` (`ordpar-minispacing-compact`): line height 1.3, padding .6rem .75rem, .35rem
  below the header, senses .3rem apart, .12rem inside a sense, examples .05em with a .12rem flex gap,
  subsenses and compound lists .35rem above and .2rem below. `miniscroll` = `on` (default): on a
  computer only (`@media (hover:hover) and (pointer:fine)`) a tall box scrolls inside, at most
  `min(70vh, 30rem)`, `overscroll-behavior:contain`; `off` (`ordpar-miniscroll-off`) shows it whole.
  `minihw` = `link` (default: the headword upright, in the text colour, with the link underline) or
  `article` (`ordpar-minihw-article`: the article headword's look; [78](../../docs/decisions.md#d78)).
- **Its shadow** ([157](../../docs/decisions.md#d157); `SITE_CSS`, over `scripts/mini.py`'s
  `.mini` by specificity): by day `0 1px 3px rgba(60,20,40,.12), 0 8px 28px rgba(60,20,40,.2)`; at
  night `0 1px 3px rgba(0,0,0,.5), 0 10px 36px 4px rgba(0,0,0,.8)`, the box lifted to #2c2629 with a
  #3e3439 border, so the page's text beside the box visibly darkens under it. Nested boxes take the
  same.
- **Its width on a computer**: under the same fine-pointer query the sheet lets the box shrink to its
  content (`width:max-content`) between a floor of 12rem and a ceiling of `min(36rem, max(19rem,
  50vw), 100vw − 1rem)`; that alone holds without script. Once the content is in and before `place`,
  `mini.js` `fit` clears the inline width, reads the floor and ceiling from the sheet (laying the box
  out at width 0 and at a huge width), notes the content height at the ceiling (`scrollHeight`) and
  sets the narrowest whole-pixel width with that height, within 1 px (`narrowest`: a binary search of
  about ten trial layouts in one task, so no trial is painted). It runs again on `resize` and whenever
  a class on `<html>` changes while a box is open (a `MutationObserver`). Extra width is taken only
  where it saves a line. On a phone the box keeps 19rem and `fit` sets nothing. The box opens at its
  header's width while it waits for the content.
- **When it fetches** (`minifetch`, shared with every in-site link: § Loading ahead): `point`
  (default) — when the pointer has rested on the link for 150 ms without moving, and on `touchstart`;
  `click` — on the click; `page` — every target on the page, one at a time in idle time. The
  small-article script keeps its own rest timer and touch handling.
- **A peek inside a small article** ([141](../../docs/decisions.md#d141)). A computer's box
  scrolls, so a peek placed in it by the sheet would be cut at the box's edge. On `mouseover` of a
  cross-reference inside a box (a listener on the window, so after the page script's own placing),
  `mini.js` `peekFix` draws the peek against the window (`.ordpar-pfix`: `position:fixed`), above its
  word where the sheet puts it, moved left to stay 8 px inside the window with its arrow kept on the
  word, and below the word where above would leave the window (`.ordpar-pbelow`, the arrow turned up);
  again on scroll while the word is hovered. Whether it shows is still the sheet's decision.

**A small article inside a small article** ([139](../../docs/decisions.md#d139),
[147](../../docs/decisions.md#d147)). `mini.js` reads the setting `nestminis` itself: `second`
(default) | `inplace` | `stacked` | `off`. There is no depth limit. A link inside a box either opens
**a box** or is **a step** in the box it is in; the choice says from which box on it is a step
(`inPlaceAt`): *In place* (`inplace`), one box, every link in it a step; *A second box* (`second`), a
link in the first box opens a second, and a link in the second is a step there; *A box of its own*
(`stacked`), every link opens one more box over the one before; *Off*, a click in a box opens the
page. `target` upgrades a link inside a box under every choice but `off`; `xref` = `page` still sends
every click to the page.

- **A step**: the box's content swaps to the new word, with a line at its top "← *word*"
  (`button.ordpar-mback`, `aria-label` "Back to *word*", the word drawn as the header draws its
  headword); the box refits its width and stays under its word; the focus moves to the back line.
  Each box keeps its own steps (`c.steps`). Back (`stepBack`, by the line or by Escape) returns one
  word, restoring the box's own `scrollTop` as it was, the focus on the link stepped from.
- **A nested box** (`.ordbok-xmini.ordpar-mnest`) sits inside the box it opens from, beside that box's
  `.mini`, `position: fixed` — not in its word's line, because the line's rules would reach every
  link inside it; the first box's scrolling does not clip a fixed box. The cost: opened from the
  keyboard, the focus moves to its headword, since the box is not next to its word. `placeNested`
  places it 1.7em below the top of its word's line, moved left to stay 8 px inside the window, with a
  slightly deeper shadow; it follows its word on scroll and hides while its word is scrolled out of
  its box. **Its height is kept inside the window** ([165](../../docs/decisions.md#d165)): below
  its word when its content fits there (under a computer's `min(70vh, 30rem)`), else, where there is
  more room above, above its word (`.ordpar-mabove`), its height capped at the room on that side, 8 px
  from the window's edge, scrolling inside. The side is chosen when the box opens, when its content
  arrives, on a step and on a resize, and **kept while the page or a box scrolls** (`placeNested`'s
  `keep`); a `ResizeObserver` places it again when its height changes.
- **Closing**: Escape acts on the deepest box (a step back where it has steps, else it closes), the
  focus returning to the word that opened it; a click inside a box closes only the boxes nested in it
  (`insideClick`); the backdrop closes all; the same word clicked again closes its own box. The
  opening word carries `aria-expanded`, a loading box `aria-busy`.
- **Nothing done inside a box scrolls the page** ([147](../../docs/decisions.md#d147)): opening a
  box, a link in a box, the back line, Escape, a closing click, content arriving — `scrollX` and
  `scrollY` stay as they were. To keep it so, in `mini.js`: every focus is `focus({preventScroll:
  true})` with no fallback; no `scrollIntoView`, `scrollTo` or `scrollBy`; each box carries
  `overflow-anchor: none`; and before a change that can make the page shorter (a swap for a step, a
  box closed) `hold` sets `min-height` on `<html>` to the bottom of what the window shows, so the
  browser does not pull the page up; the scroll listener lowers it as the reader scrolls up
  (`unhold`). Placement sets only the boxes' own `left` and `top`. A step back restores only the
  box's own `scrollTop`, never the page's.
- Every level loads through `load`, so the shared fetch and the offline copy serve it, and it works
  everywhere small articles show (article pages, word pages, search results, list rows, the 404
  shell, the offline copy). Its rules: `SITE_CSS` `.ordpar-mnest`, `.ordpar-mback`, with their night
  colours.
- **On the Anki deck**, which runs the same `mini.js`, a link inside a box is upgraded only where the
  card carries the target's `<template id="ordpar-t-<id>">` (`window.ordparDeck` set); otherwise the
  link keeps its peek and a click follows it.

Tests: `test_ordpar_nestminis139.py`, `test_ordpar_nestminis147.py`, their browser twins,
`test_ordpar_browser_peek141.py`, `test_ordpar_minishadow157.py`.

## Settings

Settings live on the device, in `localStorage` ([19](../../docs/decisions.md#d19)), and are read
by the head script before the first paint, which puts each non-default value on `<html>` as a class
for the sheet. **The one table is `shell.js` `SETTINGS`** (key, values with the default first, section
and subsection; [107](../../docs/decisions.md#d107)); the head script reads it at build time
(`head.settings_table`), the settings page (`/settings/`, drawn by `settings.js`;
[`lookup-index.md`](lookup-index.md) § 7) writes the same keys through `shell.js`, which toggles the
same classes and calls `window.ordparDefs()`, so a change needs no reload. The export of settings
carries them all (`personal.js` `SETTING_KEYS`). Any other stored value reads as the default. The
labels under a subsection heading are short ("Language", "Its headword"), and each fieldset's
accessible name leads with its subsection heading (`aria-labelledby` = the `h3` and the legend).

| section › subsection | key | values (default first) | effect |
|---|---|---|---|
| Style | `theme` | `system` \| `light` \| `dark` | `nightMode` on `<html>` |
| Style | `colour` | a scheme's id | `data-accent` on `<html>`; an unknown id is the default scheme (§ The frame and the colours) |
| Style | `lang` | the interface languages | the interface language |
| Style | `layout` | `ordpar` \| `ordbokene` | § Examples |
| Article › Norwegian only | `nbonly`, `nbequiv`, `nbrows`, `nbhover`, `nbicon` | § Norwegian only | a layer over the others |
| Article › Language | `defs` | `both` \| `en` \| `no` | § Definition lines |
| Article › Language | `examples` | `both` \| `no` | the examples' English behind a cue |
| Article › Language | `exeye` | `off` \| `on` | the eye |
| Article › Language | `exeyewhat` | `examples` \| `all` | what the eye hides; drawn only while `exeye` is on |
| Article › Language | `levels` | `off` \| `on` | the CEFR level box after the headword and on each set phrase (`ordpar-levels-on`; § The headword line) |
| Article › Language | `phraseorder` | `alpha` \| `level` | the set phrases alphabetically or by CEFR level (`ordpar-phraseorder-level`, applied only beside `ordpar-levels-on`); drawn only while `levels` is on (§ The headword line) |
| Article › Language | `exlimit`, `exmore` | `all` \| `1`…`10`; `on` \| `off` | the examples limit |
| Article › Language | `emph` | `no` \| `en` | the emphasized line |
| Article › Language | `subsenses` | `defs` \| `en` | subsenses in English only |
| Article › Language | `formulas` | `both` \| `en` \| `no` | formula lines |
| Article › Language | `ety` | `en` \| `no` \| `both` | the etymology line |
| Article › Language | `labels` | `en` \| `no` | the labels in Norwegian (a layer) |
| Article › Inflection | `infl` | `button` \| `open` | `open` opens the Inflection toggle on load |
| Article › Inflection | `pframes` | `on` \| `off` | `off` hides the participle frames ([31](../../docs/decisions.md#d31)) |
| Article › Cross-references | `xref` | `mini` \| `page` | `page`: a click opens the target's page |
| Article › Cross-references | `peek` | `on` \| `nb` \| `off` | `on` the translation; `nb` the first Norwegian definition (`ordpar-nbo-hovnb`); `off` (`ordpar-peek-off`) hides every peek |
| Article › Small articles | `mini` | `article` \| `both` \| `en` | `article`: `en` when `defs` is `en`, else `both`; the head script puts `ordpar-mini-en` when the resolved value is `en` |
| Article › Small articles | `minicontent`, `nestminis`, `minispacing`, `minitext`, `miniscroll`, `minihw` | as above | § Cross-references and the small article |
| Article › Audio | `audiospeed` | `recorded` \| `90` | § The audio |
| Search | `listview`, `suggestrows` | see [`lookup-index.md`](lookup-index.md) | |
| Loading, offline and your data › Loading | `minifetch` | `point` \| `click` \| `page` | § Loading ahead |
| Loading, offline and your data | `stats` | `on` \| `off` | drawn only while the counting is live (§ Report a mistake) |

The classes follow one pattern, `ordpar-<key>-<value>` for a non-default value (`ordpar-defs-en`,
`ordpar-formulas-both`), with the exceptions the sections above name.

**Presets** ([136](../../docs/decisions.md#d136), [174](../../docs/decisions.md#d174)).
Above the settings page's sections, after its jump links, a box "Presets" (`settings.js` `presets`; a
"?" after its heading opens a line per preset, `settings.presets.<id>.note`, and a link to
`/help/#settings`) holds four buttons, *Default*, *English emphasized*, *Concise* and *For
learners*. The one table is `settings.js` `PRESETS`: English emphasized is `emph` en, `formulas` en;
Concise is `defs` en, `exlimit` 2, `exmore` on, `minicontent` slim, `minispacing` article, `emph` en,
`formulas` en; For learners is `exeye` on, `emph` no, `examples` both, `subsenses` defs, `formulas`
both, `levels` on ([187](../../docs/decisions.md#d187)), `phraseorder` level
([188](../../docs/decisions.md#d188)); Default names none. Pressing one writes **every** Article setting (`section: 'article'`) through
`setSetting`, the ones it does not name at their default; nothing outside Article changes, and the
layer settings (`layer: true`) are never set or matched. The button whose full set the stored settings
match is `aria-pressed="true"`, filled in the accent; it follows every change, including from another
tab (the page's `storage` listener). The status line says "Article settings set to {name}." Under
"Reset settings" a note (`settings.resetNote`) says it resets every setting, theme and colour too
(`shell.js` `resetSettings` drops every key), and points to *Default* for the Article settings alone.
The Help page (`ordpar/help.md`) opens with `## Settings` (`#settings`). Tests:
`test_ordpar_presets136.py`, `test_ordpar_browser_presets136.py`, `test_ordpar_defaults174.py`.

### Settings in the address

([146](../../docs/decisions.md#d146)) A pop-up dictionary such as Definer shows ordpar.no in a
frame on another site, whose storage the browser keeps apart, so it never sees the reader's saved
settings. The site therefore reads settings from the address, after `#`, beside the search; they hold
for that tab's or pop-up's visit and are never saved.

- **Reading** is the head script's (`head.THEME_JS`), so the pop-up paints in its settings from the
  first frame. Of the fragment's `key=value` pairs it takes those whose key is in the settings table
  with a value that key accepts; anything else is ignored. An address naming any setting starts the
  **visit**: its valid settings go in `sessionStorage` (`ordpar-visit`, `head.VISIT_KEY`), which lasts
  as long as that tab and is not shared; the pairs are then taken off the address
  (`history.replaceState`, the entry's state kept), so `/bm-en/#defs=en&mini=en&q=hus` becomes
  `/bm-en/#q=hus` before any other script reads it. Later pages in the tab take the visit; a new tab
  shows the saved settings. `localStorage` is never written. **Never on `/settings/`**, where the
  reader sees and sets their own saved settings. A setting the reader changes ends the visit's value
  for that key, and "Reset settings" the whole visit (`shell.js` `leaveVisit`). Where the browser
  refuses the storage, the address's settings still apply to the page it opens.
- **Every reader of a setting goes through the visit**: the head script defines
  `window.ordparRead(key)` (the visit's value, else `localStorage`) and `window.ordparVisit` ({table,
  colour: the default scheme's id, settings}); `shell.js` `read`, `mini.js` `setting`, `ahead.js`
  `stored`, `events.js` `optedOut` and the page script's inflection setting all read through it.
  `shell.js` `savedSetting(key)` reads the saved value alone; `setSetting` writes the saved setting.
- **The search's address** takes settings before the search: `lookup.js` `hashQuery` (`#q=hus` or
  `#defs=en&q=hus`) serves every reader of the fragment, and `ahead.js`'s patterns accept it. Every
  writer writes the plain search; History stores the query, Favourites an article, never an address.
- **The address to copy** is `shell.js` `popupAddress()`: `https://ordpar.no/bm-en/#`, every *saved*
  setting that differs from its default, in the table's order, then `q={{str}}` (where Definer puts
  the word). With every setting at its default it is exactly `https://ordpar.no/bm-en/#q={{str}}`; the
  colour travels when it is not the default, the language when it differs from the browser's. A visit
  in force does not change it. It is offered on `/more/` (step 4's line, the code line whose text is
  `about.POPUP_ADDRESS`, marked `data-ordpar-popup` by `about.py` and filled by `shell.js`
  `wireCodeLines`; without script the plain address) and in
  Settings, at the bottom of "Loading, offline and your data" ("Copy the address for a pop-up
  dictionary", `settings.popup`, with a line linking `/more/#popup`, and "Address copied." in the
  status).
- **Copy buttons**: both code lines on `/more/` get a Copy button made by the script (so a page
  without script has none that cannot work): the page's quiet button, `ordpar-code-copy`, with
  `has-copy` putting the line and its button in a row (`page.PAGE_CSS`). A click copies the line and
  the button says "Copied" for 2.5 s (`COPIED_MS`), then "Copy" again (`code.copy`, `code.copied`). Where the clipboard is refused (`shell.js` `copyText`), the line is selected and
  the browser's copy command tried; only if that reports success is "Copied" said. Otherwise the line
  stays selected and nothing is said; in Settings the address first shows as a line of code under the
  button (`.ordpar-popup-line`).

Tests: `test_ordpar_settingsaddr146.py`, `test_ordpar_browser_settingsaddr146.py`.

### Norwegian only, and the labels in Norwegian

([152](../../docs/decisions.md#d152)) For readers who want ordbokene's Norwegian with Ordpar's
features: a **layer** over the reader's own settings, not a preset, changing the language and never the
style.

| key | values (default first) | where |
|---|---|---|
| `labels` | `en` \| `no` | Article › Language, last |
| `nbonly` | `off` \| `on` | Article › *Norwegian only*, at the head of the Article settings |
| `nbequiv` | `hidden` \| `shown` | the same; shown in Settings only while `nbonly` is on |
| `nbrows` | `nbdef` \| `none` | the same; shown only while the equivalents are hidden |
| `nbhover` | `none` \| `nbdef` | the same |
| `nbicon` | `on` \| `off` | the same, always shown |

These carry `layer: true`, so presets leave them alone. They travel in the address and in an export.

- **The layer** (`ordpar-nbo` on `<html>`). While `nbonly` is on, the classes of seven settings are
  drawn from the layer's values, whatever the reader stored, and the stored values are never written:
  `defs` and `examples` `no`, `formulas` and `ety` `no`, small articles as the article, no subsenses in
  English, and with the equivalents hidden the hover by `nbhover` (`shell.js` `LAYER_VALUES`, `eff`; the
  head script draws the same before the first paint). Layout and look settings stay the reader's. The
  sheet then hides what no setting reaches: the "Show English" cues and every English definition,
  formula, etymology and example line however opened, in small articles too; the eye; the "Eng.
  phrase" lines; the "Not yet translated" sub-heading; a Norwegian-only article's caption and note; the
  rows' "Norwegian only" tag. Ordpar's added examples stay, with their "+". With the equivalents
  hidden (`ordpar-nbo-noeq`) it also hides the summary glosses, every row's English (`:lang(en)`) and
  the "Search English words" switch.
- **The search with the switch hidden** is Norwegian (`shell.js` `direction`), the stored direction
  untouched; a shared `#en=` address still opens its English search. Random word stays Norwegian.
- **The rows' right side** (suggestions, Recent, History, Favourites, the list view, inflected-form
  rows, similar rows, a word or form page's rows): with `nbrows` = `nbdef` each article's first
  Norwegian definition (a Norwegian-only article's snippet; for a translated one the `snip/` file's
  `"_n"`, [`lookup-index.md`](lookup-index.md) § 3), drawn through `lookup.js` `rowView`, `lang="nb"`;
  a built row ships its Norwegian line hidden beside its English (`ordpar-nbsnip`). With `none`, no
  right side. The search page, History and Favourites redraw on a change.
- **The hovers**: with `nbhover` = `nbdef` (`ordpar-nbo-hovnb`), every link whose target has a first
  Norwegian definition shows it, in the regular-weight peek (`ordpar-nbdef`), the English peeks hidden.
  It is read at hover time from the target's `snip/` file (`mini.js` `nbPeek`), whose key every leading
  link carries (`data-s`, `face._link`). This costs about 0.5 MB on the offline download, against about
  2 MB for a second peek in every page's markup ([`lookup-index.md`](lookup-index.md) § 5). The same
  hover is the setting `peek` = `nb` outside this view (§ Cross-references and the small article, *The
  first Norwegian definition as the peek*); `nbhover` lies over `peek` while the equivalents are hidden, and with them
  shown `peek` decides (`shell.js` `hoverNb`; the head script draws the same). **It follows the
  Loading setting**: under `minifetch` = `click` no `snip/` file is fetched for it, and a link shows
  its Norwegian peek only when the page already has the file (`lookup.js` `loadedSnippets`, after a
  search, say); under `point` and `page` the file is fetched on the first hover or focus.
- **The word class and the inflection tables' words** are in Norwegian under the layer or under
  `labels` = `no`: both copies ship (`ordpar-w-en`, `ordpar-w-nb`) — the article's `.ordbok-pos`
  (`article.pos_html`, `NB_POS_WORDS`), the tables (`inflection.js` `NB_STRINGS`), a built row's word
  class and form label (`wordpages.pos_html`, `form_label_html`); rows drawn by script draw the language
  in force (`shell.js` `posWords`, `posSpan`; `lookup.js` `labelNb`).
- **The icon** (`shell.js` `nbIcon`): a round button like the eye's, two speech bubbles, filled while
  on; a press is `setSetting('nbonly', …)`, so icon and Settings are one state. On a computer first
  beside Favourites and Settings; on a phone on the switch's row. `nbicon` = `off` hides it
  (`ordpar-nbicon-off`). **Beside the headword** (`page.PAGE_JS` `nbhw`): made on every article shown
  whole (never a small article) and hidden by the sheet unless the page's own CSS shows it; `/more/`'s
  Definer CSS line has the rule `.ordpar-nbhw { display: inline-flex !important; }`, and a press there
  switches the layer for that pop-up only (`shell.js` `visitSetting`: the visit, never `localStorage`).
- **The labels setting** (`ordpar-labels-no`): the labels inside the article frame ship in both
  languages (`ordpar-l-en`, `ordpar-l-nb`), the Norwegian shown with `labels` = `no`; outside the frame
  ("Article view", "Home", header, footer, the results' heading) they stay English. **The layer turns
  them too**: while `nbonly` is on every label inside the article is Norwegian whatever `labels` says,
  by two rules in the sheet (`html.ordpar-nbo .ordpar-l-en` hidden, `html.ordpar-nbo .ordpar-l-nb`
  shown), wherever the sheet and the class are — article pages, word pages, small articles, the full
  search view, the pop-up and the offline copy — before the first paint. The formula lines and compound
  labels keep their own setting. The card foot's Copy link, Share and "Link copied" are the
  interface's and stay English.
- **Search engines**: every paired copy carries `data-nosnippet` on the copy the default settings hide
  (the Norwegian), in the markup or from its making in script, including the compound lists'
  `ordpar-cl-nb` and the "Se:" line's.
- **The deck** is untouched: `article.fragment(site=True)` is the site's alone, and no deck link
  carries `data-s`; the page script, which the cards share, draws its labels in both copies, the
  Norwegian hidden by the shared sheet.

| English | Norwegian | Source |
|---|---|---|
| Pronunciation | Uttale | ordbokene |
| Etymology | Opphav | ordbokene |
| Senses and Example Sentences | Betydning og bruk | ordbokene |
| Set phrases | Faste uttrykk | ordbokene |
| Inflection (the button) | Vis bøyning | ordbokene (its search page's button) |
| Example (ordbokene's layout) | Eksempel | ordbokene |
| Show English | Vis engelsk | ours |
| Show N more examples / Show 1 more example | Vis N eksempler til / Vis 1 eksempel til | ours |
| N more entries for … / 1 more entry for … | N artikler til for … / 1 artikkel til for … | ours |
| Not yet translated (sub-heading) | Ikke oversatt ennå | ours |
| These set phrases have not been translated yet … | Disse faste uttrykkene er ikke oversatt ennå. De står slik Bokmålsordboka har dem. | ours |
| Norwegian only · not yet translated (caption) | Bare på norsk · ikke oversatt ennå | ours |
| This article has not been translated yet … (note) | Denne artikkelen er ikke oversatt ennå. Den står slik Bokmålsordboka har den, på norsk. | ours |
| We corrected … in this article. (and its variants) | Vi har rettet feil i denne artikkelen. / … satt den vanligste skrivemåten av oppslagsordet først (og rettet feil …) | ours (the kind of correction dropped) |
| Bokmålsordboka's article on ordbokene.no | Bokmålsordbokas artikkel på ordbokene.no | ours |
| noun, adjective, verb; masculine, feminine, neuter | substantiv, adjektiv, verb; hankjønn, hunkjønn, intetkjønn | ordbokene |
| adverb, preposition, pronoun, determiner (quantifier, demonstrative, possessive), conjunction, subjunction, interjection, symbol, prefix, proper noun, uninflectable, "or" | adverb, preposisjon, pronomen, determinativ (kvantor, demonstrativ, possessiv), konjunksjon, subjunksjon, interjeksjon, symbol, prefiks, egennavn, ubøyelig, eller | ordbokene |
| abbreviation; compound prefix (`COMPPFX`, in the rows and on the article page: `article.site_pos`) | forkorting; i sammensetning | ordbokene (*dr.* 10696; *kjempe-* 29505) |
| suffix, fixed expression | suffiks, fast uttrykk | ours (ordbokene shows neither) |
| singular, plural, indefinite/definite form, masculine / feminine, infinitive, present, past, present perfect, imperative, perfect participle, present participle, + noun | entall, flertall, ubestemt/bestemt form, hankjønn / hunkjønn, infinitiv, presens, preteritum, presens perfektum, imperativ, perfektum partisipp, presens partisipp, + substantiv | ordbokene |
| degrees of comparison (the table's head and its hidden caption) | gradbøying, Gradbøying | ordbokene (*stor* 57372) |
| comparative, superlative, subject form, object form, the narrow "indefinite"/"definite" | komparativ, superlativ, subjektsform, objektsform, ubestemt/bestemt | ordbokene |
| positive, gender, the hidden captions Bøyning/Partisipper, "unknown tag", the form labels' "passive" and "and" | positiv, kjønn, Bøyning/Partisipper, ukjent merke, passiv, og | ours |

**The form labels' Norwegian order**: a number's definiteness reads as Norwegian writes it —
definiteness, the word "form", then number, as Bokmålsordboka's own definitions write "i bestemt form
entall" (`wordpages.FormLabels.nb`, `form`; `_definite_first`). Ordbokene composes no form label, so
these compositions are Ordpar's. The singular and plural are one phrase where the plural has the same
definiteness or none:

| code | English | Norwegian |
|---|---|---|
| A | plural definite | bestemt form flertall |
| B | singular definite | bestemt form entall |
| C | plural indefinite | ubestemt form flertall |
| D | singular definite, plural | bestemt form entall og flertall |
| T | singular definite, plural definite | bestemt form entall og flertall |
| d | singular definite, plural indefinite and definite | bestemt form entall, ubestemt og bestemt form flertall |
| g | plural indefinite and definite | ubestemt og bestemt form flertall |

Left in their own order: the adjective's degrees ("superlativ ubestemt": ordbokene's own heads), the
participles ("perfektum partisipp" then its qualifier), a number led by a gender ("entall
intetkjønn"), single words, "passiv", "og". They reach the reader as `labels.json`'s `"_nb"`, a row's
`label_nb`, the built rows (`wordpages.form_label_html`) and `lookup.js` `labelNb`.

Tests: `test_ordpar_nbonly152.py`, `test_ordpar_nblabels152.py`, `test_ordpar_browser_nbonly152.py`.

## Loading ahead

([92](../../docs/decisions.md#d92), [180](../../docs/decisions.md#d180)) A list row's or a
favourite's first open takes about 150–600 ms, nearly all of it the fetch of the article's page; loading
it while the pointer rests on the link removes about 95 % of that on a computer.

**`ordpar/site/ahead.js`**, in both bundles, one listener set on the document. The setting `minifetch`
decides (`ordparAhead.mode()` is the one reading of it, including the visit and the data saver):

- `point` (default): the fetch starts once the pointer has rested `REST_MS` (150 ms) on the link without
  moving, and at `touchstart` (on a phone only the tap's own 50–100 ms, in effect nothing);
- `click`: nothing ahead, the hover's first Norwegian definition included (§ Norwegian only, and the
  labels in Norwegian, *The hovers*);
- `page`: what the page shows is fetched with it, one job at a time in idle time
  (`ordparAhead.queue`, keyed `a<id>`): the small articles' targets (`mini.js` `scan`) and the list
  view's articles (`lookup.js` `listRows`); every other link as under `point`. Under the browser's data
  saver (`navigator.connection.saveData`) it is `click`.

**What a rest fetches** (`ordparAhead.aim`), each URL once per page view:

- a list row's button: its article, through `ordparSearch.fetchArticle`, the in-memory cache the row
  and the small articles share;
- a cross-reference the small-article script will open: left to `mini.js` (under `xref` = `page` a
  plain link). A link inside an open box that `mini.js` opens as a nested box (`ordparMinis.target`) is
  left to it too, so the article is not requested twice; under `page` it is loaded through `mini.js`'s
  own `load`, under its key `a<id>`;
- a link to `/bm-en/<id>/`, `/history/`, `/favourites/`, `/settings/`, the front page `/`, a word or
  form page `/bm-en/<word>/` (with or without its search after `#`, the word's search warmed either
  way), or one of the prose pages by an explicit list (`about`, `coming`, `changes`,
  `dictionary-changes`, `deck-changes`, `thanks`, `privacy`, `help`, `more`, `survey`) — not any path,
  since the output can hold other folders: the page, read whole into the HTTP cache (the host's
  `max-age=600`; with an offline copy the worker answers from it), and the scripts and sheets it links
  that this page has not loaded, once per page view;
- a search, `/bm-en/#q=…`: the index files its query reads (the query is only looked up, never sent)
  and, where the search will show its articles in full (`lookup.js` `useList`), their pages, at most
  three. An old `/bm-en/?q=…` link is not fetched ahead. On a page that answers searches in place
  (`ordparShell.answersInPlace()`), only the search is warmed, not the page HTML, and the articles go
  through `ordparSearch.fetchArticle`;
- an English search, `/bm-en/#en=<word>`: the English file (`ordparLookup.englishLookup`) and, where
  the search opens its one match in full, that article;
- a suggestion or Recent row (each carries `data-q`, and `data-en` on an English row): the row's
  search as its press opens it; a row selected by the keyboard (`shell.js` `choose` →
  `ordparAhead.select`) only once the selection has stayed on it `REST_MS`, so arrowing through rows
  loads nothing;
- **Random word**: on the rest or touch the word is drawn (`ordparSearch.drawAhead`, in the direction
  of that moment) and kept on the button, and its search is warmed; the click (`wireRandom`) takes that
  draw if the direction is unchanged, awaiting it if still pending; the next rest draws anew. A draw is
  still not a search.

**Never loaded ahead**: links to other sites (a third party would learn the reader's interest before a
click); actions — "Suggest a correction" and its form, the survey's Send, Clear history, removing a
favourite, Copy link, Share, the heart, the offline copy's buttons, install, the settings' export,
import, reset, delete and presets; links with `target` or `download`; links to a place on the same
page; the English/Norwegian switch.

**The fetches use `credentials: 'omit'`**: in a settled browser profile both credential modes reuse
an open connection, and the HTTP cache is shared between them and the navigation, so the uncredentialed
fetch costs nothing extra.

**`personal-page.js` is in the shell pages' bundle**, its last part, so the first opening of History or
Favourites is one request, not two; on other shell pages it does nothing. About 4 KB gzipped.

**The sound icons follow the setting** ([170](../../docs/decisions.md#d170)): the clip a resting
pointer loads ahead is loaded only where a link would be (`audio.js` `ahead()` asks
`ordparAhead.mode()`); the names file is asked for only when a recording is wanted; the `preconnect`
to the audio server is inserted only under `point` and `page` (§ The audio).

Measured in headless Edge with the network slowed to 150 ms and 1.5 Mbps: a list row rested on, then
clicked, opens in 43 ms against 290 ms clicked at once; History, Favourites and a history row's search,
each rested on first, open with nothing fetched after the click. Tests: `test_ordpar_ahead180.py`,
`test_ordpar_browser_ahead180.py`, `test_ordpar_browser_soundrest170.py`.

## The search features the pages support

The search is drawn by `lookup.js` and `shell.js` from the index ([`lookup-index.md`](lookup-index.md),
§ 3b for the English index's format); this build supplies the rows' one-line text (the snippets file)
and the article fragments. The pieces that live in the article bundle as well:

**The rows the search draws** (the list view, the inflected-form rows, the suggestions, Recent, History,
and the similar headwords after a miss; [144](../../docs/decisions.md#d144)). After a search that
finds nothing, each similar headword is a row as the suggestions draw theirs (the word, its word class,
its English after a muted dash); after a hit, a bare list. A word whose articles are all untranslated
shows each homograph's numeral and Norwegian definition in place of "N articles", without its
cross-references' numbers.

**Similar headwords that would only repeat the page** ([149](../../docs/decisions.md#d149);
`lookup.js` `dropRepeats`, `pageSpellings`): on a page that shows articles, a similar headword is listed
only if its own search would show an article not already on the page (neither among the results nor
the inflected-form rows). No request is made: a candidate's articles are known from its shard where that
is loaded, else by its count (the headwords file's `a`) against the page's articles that carry it as a
spelling. The pass asks for 30 candidates (`SIMILAR_POOL`) so the list keeps its five.

**The suggestions show the spelling typed** ([150](../../docs/decisions.md#d150); `lookup.js`
`typedLine`, `shell.js` `drawLine`, `pickWord`): a one-article row shows the one spelling that continues
what was typed — "selv" → *selvsagt*, "sjøl" → *sjølsagt* — the first in our lemma order where several
do, with no homograph numeral. Picking it searches that spelling.

**The English search** ([148](../../docs/decisions.md#d148)):

- **The switch** "Search English words" under the search box on every page with the box (`shell.js`
  `addSwitch`, `setDirection`, `applyDirection`), drawn by script, so no page's HTML depends on it. On a
  computer a row of its own; on a phone on Random word's row, its room held before the script runs (the
  header's `::before`). On: the placeholder and label "Search an English word", the box `lang="en"`. It
  is **remembered** (`personal.js` `direction`, the key `direction` in `localStorage`; not a setting,
  not exported; "Delete stored data" removes it). Switched with a word in the box, the word is searched
  again the other way. A search run on the search page, or answered in place, sets the switch to its own
  direction.
- **The address** `/bm-en/#en=<word>` (`lookup.js` `englishUrl`, `ordparSearch.englishFromLocation`);
  `#q=` stays Norwegian. An English search answered in place pushes `{q, search: true, en: true}`.
- **The suggestions**: one row per English word (`shell.js` `englishRow`, `openEnglish`; `lookup.js`
  `englishSuggest`): the English word left, semibold, `lang="en"`; right, its Norwegian headwords,
  semibold in the accent (`.ordpar-en-nb`), best ranked first, each in its first spelling with that
  spelling's numeral and word class while all fit; where they do not, the word classes go first, then
  the list is cut with "+ N more" (`ordparFit`, `fitGlosses`). Order: the exact word, then one-word
  continuations by the frequency band of their Norwegian words, then phrases by length.
- **The results** (`lookup.js` `renderEnglish`): always the list view, except one matching article,
  opened in full with its own title. Each row the Norwegian headword line, its snippet line the whole
  summary gloss, wrapping, with the searched equivalent bold (`.ordpar-en-hit`, `englishGloss`) wherever
  it matches. Exact equivalents only.
- **The similar English words** after every English search (`englishSimilar`), five, each a link
  `#en=`: first word matches (a longer equivalent holding the word, a word sharing its stem, with an
  irregular-verb table, `build_index.EN_IRREGULAR`), then words spelled alike within `letterLimit`,
  149's rule applied. Spelled-alike words reach other first letters through the **English tails files**
  (`en/tails/<k2>-<k3>.json`, `build_index.english_tails`: one-word keys filed by their second and third
  characters) and the second letter's English file: a wrong first letter through the tails file of the
  query without its first character (*hoose* → *loose*), a missing one through the query's own (*hoose*
  → *choose*), an extra one through the second letter's file (*xhouse* → *house*). They are **fetched
  after the results are painted**, so a search's results keep their one request.
- **The miss**: "“{q}” is not among our English equivalents yet." and a line giving how many articles
  have English equivalents so far and their share of the dictionary (`results.noneEn`,
  `results.noneEnWhy`; the numbers `c` and `p` from every English file).
- **History and Recent** record an English search that found something as `{q, n, en: true}` (the
  English and the Norwegian *house* are two entries), drawn as an English row; History links `#en=`.
- **Random word in English** ([155](../../docs/decisions.md#d155)): with the switch on (the
  stored direction, `ordparShell.direction`), Random word draws an English word (`lookup.js`
  `randomEnglish`) and opens it as if typed and picked; its entry is `{q, random: true, en: true}`, so
  it is not recorded. **The pool** is every English word the suggestions can offer, each equally likely:
  every key of the English index once, under its file's letter (`build_index.english_pool`), less the
  keys the suggestions can never reach (about 15,000 words). **The file**, the index's `random-en.json`,
  `{"v": 1, "n": {letter: count}}` (`english_random`), is about 0.2 KB; a list of the words would be
  about 63 KB gzipped. **The draw stays uniform**: one number below the total picks the file, weighted
  by its count, and the place in that file's pool, so each word has chance 1/total, and the file loaded
  is the one the word's search reads anyway. The manifest (`index.json`) carries `random_en`; the
  offline copy carries the file. With *Norwegian only* hiding the equivalents, the switch is hidden and
  Random word stays Norwegian.
- **The offline copy** ships the English files and tails files in packs of their own
  (`build_offline.file_group`: `en-<letter>`, `en-tails-<first key>`), about 1.2 MB of the download.
- **Events**: an English search sends `hit`, `miss` and `pick` as a Norwegian one does, with `lang:
  'en'` (§ Report a mistake).

Tests: `test_ordpar_random155.py`, `test_ordpar_browser_random155.py`, and the browser files for
English search and similar words listed in [`tests.md`](tests.md).

### The tab's title

| Where | Title |
|---|---|
| An article page (built) | "word (class) — Norwegian–English dictionary" (`describe.page_title`) |
| A word page of one article (built) | that article's own title |
| A word page of several entries, a form page (built) | "word — Norwegian–English dictionary" (`wordpages.several_title`) |
| About, Help, Coming, More, the change pages, Privacy, Thanks (built) | "*page title* — Ordpar" (`_prose_page`) |
| Home, the search page with no search | "Ordpar — " + `site.tagline` |
| The 404 shell (built) | "Ordpar", until its script sets one of the titles below |
| A search answered in place, at first | "q — Ordpar", set the moment the search is made (the results show "Searching…", and a search overtaken by a newer one is dropped: [138](../../docs/decisions.md#d138)) |
| …whose address is its word or form page (`lookup.js` `render` → `pageTitle`) | the page's built title |
| …with no page of its own (`#q=`), one article in full | the article's title |
| …with no page of its own, anything else | "q — Ordpar" |
| Back to a word page's own first entry | the title the page loaded with |
| The 404 shell, nothing found | "Page not found — Ordpar" (`notfound.title`) |
| History, Favourites, Settings | "*page* — Ordpar" |

The dictionary's name is `strings["dictionary_name"]` (`ordpar/sitegen/strings.py`); the article pages
have it in `ordpar.js`'s strings, and `build_index.copy_shell` adds it to the shell pages' inline
strings. Never a fixed copy.

## What search engines read

([154](../../docs/decisions.md#d154)) A search engine may build its snippet from the page's text
instead of the meta description, and then picks up hidden labels and runs together lines that are
separate on the page. Google's `data-nosnippet` keeps marked text out of snippets: only on `span`,
`div` and `section`, boolean, and **never added to an element already in the page by script** — an
element a script makes must carry it from its making. So:

- **`data-nosnippet` on every hidden label**, written bare. In the markup (so word pages and small
  articles, which lift it, carry it too): the hover peek (`face._link`, `face.SiteFace.xref_hover`), the
  head's numeral reading (`article.head_html`), a built row's numeral reading and the results' count
  reading (`wordpages._headword_html`, `results_heading`), the live regions (`wordpages.render`,
  `search.html`, `404.html`: a `div`, since a `p` cannot carry it). In script, at the making:
  `lookup.js` and `shell.js` `srOnly`, `inflection.js` `hiddenLabel` (a caption's words in a span inside
  the `<caption>`), `install.js`'s live region. The one hidden label without it is the search box's
  `<label>`, which cannot carry it.
- **Whitespace between separate pieces**: a newline in the markup where two elements are separate
  lines or pieces and had nothing between them, only where the layout draws nothing for it (flex or grid
  items, blocks, table parts), so nothing on the page moves — the definition pair, an example and its
  translation, the "Article view" line, the header's name and tagline, the footer's links, a built row's
  parts, the results' heading; in script `lookup.js` `spaced`, `inflection.js` `spaceTable`. A `<br>`
  already separates.
- **The headword first in the description** (`describe.description(…, word=)`; `describe.CAP` is still
  the whole length, and the glosses are never cut). `word` is the headword's first spelling
  (`describe.headword`), not the whole list, which on a many-spelling page left no room for the
  definition:

  | page | description |
  |---|---|
  | translated | "kanskje: perhaps · maybe. Definition: 1. …" |
  | translated, no summary gloss | "hus: 1. …" |
  | Norwegian only | "absurdisme (not yet in English): retning …" |
  | no definition line read | "word: " + the fallback text |
  | word page, several entries | "være: 3 entries in the Norwegian–English dictionary. II to be · …" |
  | form page | "tær: an inflected form of tå, noun (plural indefinite): toe · …" (`strings` `form_page_lead`) |

  A word page of one article takes its article's description. The word and form pages' descriptions
  are not capped.

Tests: `test_ordpar_snippets154.py`, `test_ordpar_browser_snippets154.py` (no hidden label outside
`data-nosnippet`, no glued text, the headword first).

## Corrections to the Norwegian

Ordpar corrects a small number of faults in Bokmålsordboka's data (cross-references, typos, headword
order) and tells the reader so on each article it changed.

### The change notice

([106](../../docs/decisions.md#d106)) Every article whose Norwegian Ordpar corrected gets one line
at its card's foot, naming the kinds of change only and linking to the article on ordbokene.no: "We
corrected a cross-reference and a typo in this article. Bokmålsordboka's article on ordbokene.no ↗".

**`ordpar/sitegen/corrections.py`** is the build's one reader of the normalization log,
`data/review/source-normalizations.jsonl`, for this (its docstring has the rules): which rows are live
corrections of one article, and a check of each against the page's own Norwegian and the same article
derived from the mirror, so that a correction the page does not show — no library row, the page still
carrying the defect, a run of spaces, or one ordbokene.no has made itself by the snapshot — makes no
notice. The checker runs once per build over the whole log, whatever `--ids` builds. `build.json`
records it as `change_notice`: the notice's articles and groups, the counts by group and by the About
page's types, and every live row that makes no notice, by verdict (`upstream`, `not_shown`,
`invisible`, `unconfirmed`).

The words are the shell's strings, `ordpar/site/strings/en.json` `change.*`: one phrase per group,
singular and plural, the groups in a fixed order (cross-references, the headword's order, typos, then
the rest), joined with commas and "and". The link's URL is `chrome.ORDBOKENE_ARTICLE`
(`https://ordbokene.no/nob/bm/<id>`). The look is `shell.css` `.ordpar-change`: the muted colour at the
status text's size, under the controls. The same counts fill the About page's list of changes. Tests:
`ordpar/tests/test_ordpar_changenotice106.py`.

### Corrections to articles with no library row

([182](../../docs/decisions.md#d182)) Articles with no library row are derived from the mirror at
build time, so a correction made in the deck's captures cannot reach them. **`ordpar/sitegen/overlay.py`**
reads `data/review/mirror-corrections.jsonl` (`--mirror-corrections` names another file), and the
build applies each row to the mirror article **in memory**, before anything derives or reads it; the
mirror file is never written. With no file, or an empty one, the build's output is unchanged byte for
byte.

- **The verdict per row**, decided at build time against the raw mirror, never failing the build:
  `applied` (the raw value at the row's `path` is its `before`; for an object, the keys `before` names,
  an absent key reading as null); `upstream` (it already is the row's `after`); `stale` (anything else,
  no such path, or the article not in the mirror); `library_row` (the article has a library row: its
  correction is a capture edit, never applied here); `malformed` (a `path` that does not start at
  `body` — a row may change body text and references only, never the headwords or paradigms that the
  mirror's index and the search index read raw — a `before`/`after` of different shapes, or a kind the
  change notice has no group for); `duplicate` (an earlier row corrects the same field).
- **A set phrase**: the row names the set phrase's own id; the fix is made in its own article and in
  every parent's embedded copy (`sub_article` → `article`), `path` read from the copy's own root, each
  location judged on its own. Most copies carry the same text at the same path as the set phrase's
  article; some are older versions of it. The row's verdict is its own article's (for a set phrase only
  copies carry, `applied` if a copy took it); each copy's verdict is recorded too
  (`mirror_corrections.copies`).
- **The readers**: `Mirror.data` returns the corrected article (`Mirror.set_overlay`), so every reader in
  `build_site.py` sees it, and `site_stats.measure` counts over it. Two read it raw: the change notice's
  checker (`Mirror.raw_data`, `Store.raw_derived`), which must compare the page with ordbokene's text,
  and `build_index.py`, whose passes read only what a row cannot change.
- **The notice**: an applied row is a live correction of its article, checked as a capture edit is, its
  `before_text`/`after_text` standing for the log's `before`/`after`; a shown one makes the notice and
  counts; a row with no page of its own makes none. `change_notice` then also carries `overlay_rows` and
  `overlay_shown`; with no file neither key is written, so the deploy's library fingerprint is unchanged.
- **`build.json` `mirror_corrections`**: the file and whether it was there, the rows, the counts by
  verdict, the embedded copies corrected, the articles touched, and every row not applied with its
  verdict (`not_applied`).

Tests: `ordpar/tests/test_ordpar_overlay182.py`. The public repository also carries a corrected copy of
Bokmålsordboka's articles with these fixes applied (`data/bokmalsordboka/corrected/`, made by
`ordpar/corrected_copy.py` through the same overlay); the build never reads it.

## The audio

([159](../../docs/decisions.md#d159), [160](../../docs/decisions.md#d160),
[170](../../docs/decisions.md#d170)) Spoken Norwegian (Amazon Polly's voice Ida, MP3) on the
Norwegian texts. The clips are stored in a Cloudflare R2 bucket and served by a Worker at
`https://ordpar-audio.ordpar.workers.dev/<name>` ([`ordpar/audio-worker/README.md`](../audio-worker/README.md));
the site plays them with a plain `Audio` element (the Worker allows CORS for ordpar.no only, so never
`fetch`). The recordings and their names are made by a private pipeline; **nothing under `ordpar/`
reads its records**. A build without `--audio-names` simply has no sound icons.

**The icon.** A `<button class="ordpar-play">` after each voiced text whose clip is uploaded: the
headword's main form and each other spelling of the headword line (after its homograph numeral), a set
phrase's term (inside it, at its end), each definition line segment, each example's quote (before its
explanation, which is not voiced), and each form of an inflection table (each form alone; "ei/en"
voiced *ei*, the imperative without its "!"; never the participle table). A speaker with two waves,
1.00 rem; the muted grey faded 50 % toward the card (day #bab8b8, night #6f6b6c); the text colour on
hover; the accent while playing; an unseen 24 px tap area. The night colour is written
`:where(html.nightMode) .ordpar-play`, so it never outweighs hover and playing. The button is not
selectable, so a copied line carries no hidden "Play". The rules are in `page.SITE_CSS`.

**For screen readers** every icon is a real button, reachable by keyboard, named "Play" / "Spill av" by
the label classes (`ordpar-l-en`, `ordpar-l-nb` in a visually hidden span with `data-nosnippet`), so
the labels setting and *Norwegian only* name it; "Stop" / "Stopp" while it plays.

**Playing** (`ordpar/site/audio.js`): one clip at a time; a press on another icon stops the one playing,
a second press on the same icon stops it. A button with several clips plays them in turn, 300 ms apart
(every button has one today). A press does only that: no link followed, no small article or row opened
(the click is taken on the document in its capture phase).

**The speed**, `audiospeed` under Article › Audio: "As recorded" (default) and "90%", applied as
`playbackRate` 0.9 with the pitch kept (`preservesPitch`, `webkitPreservesPitch`). Below 90 % the voice
distorts. The recordings are already 10 % slower than the voice's usual pace.

**The marks: how a page knows which texts have a clip.** The build writes `data-a` on each voiced
element whose text has an uploaded clip (`ordpar/sitegen/audio.py` `mark`, run on each finished page in
`Builder.page`): each headword spelling (`.ordbok-lemma` of the `h1` and of each later group's
`p.ordpar-hw`), a set phrase's `.ordbok-expr-term`, a Norwegian `.ordbok-def` (`data-a="101"` where only
some of its segments have a clip, one digit a segment), an example's first `<span>`. The script turns
the marks into buttons as the article is drawn, synchronously and with no request, so the small
article's width fit and the tables' fit run with the icons in. The marks cost about 25 bytes a page raw,
about 0.4 MB gzipped over the whole site. They exist because deciding from the names file alone would
make every article draw its icons late, a visible shift, and a small article wait for a file before its
width could be fitted.

**The tables' mark.** The tables are drawn by `inflection.js`, so the paradigm island carries the mark:
`data-a-cells` on its `<script>` (`audio.table_code`), one character per form of the island
(`audio.island_forms`, in its order), the character's place in `audio.CELL_CODE` (64 characters) giving
the bits of the frames after which the form's text has a clip — bit 0 bare, then "å ", "har ", "en ",
"ei ", "et " (`audio.FRAMES`) — trailing "0"s dropped, no attribute where no form has one (*hus* 24627
`x111`; *abbed* 13 `1`). It is its own attribute, not `data-a`, which the script turns into a button
wherever it stands. The script reads it back (`tableKeys`) and gives a cell's form its button
synchronously, then fits the tables again (`ordparInflection.fit`); so every icon of an article is drawn
with no request. About 19 bytes a marked page raw, 10 gzipped. The mark keys forms, not cells, so the
build need not draw the tables itself.

**The names, apart from the pages.** The build reads one names file (`--audio-names`) and writes
`out/audio/<k>.json`, one per 500 consecutive ids (`k = (id - 1) // 500`), `{"<id>": {"<text>": "<16
hex>"}}`, a definition line's key led by a TAB (a page's text is stripped, so none starts with one). An
article's entry holds the names of the texts its page marks and of every form its tables can draw (each
paradigm form bare and after å, har, en, ei, et, where the names file has that text). A partial build
updates the entries it built; a whole build writes them all afresh and removes a file no article fills.
About 225 files, 23 MB, 10.6 MB gzipped (the largest 74 KB gzipped); none of it is in the offline copy
(`build_offline.other_files` packs `site/` and `index/` only). `build.json` `audio` records the names
file read, the marks by kind and the files.

**The names file's format**: one line per name, `text TAB d|- TAB *|article id TAB 16 hex|-`: the text
stripped with runs of whitespace collapsed; `d` for a definition line's name where it differs; an
article id where a fix for that article names it otherwise; `-` for not uploaded (no button, no
fallback). The build looks up a definition line in article A as `d A`, `- A`, `d *`, `- *`, any other
text as `- A`, `- *` (`audio.Names.get`). The private pipeline writes it after every upload; a full
build then passes it with `--audio-names`.

**Where icons show**: the article page (`scan` at load and from `ordparDefs`); word and form pages,
search results and an opened list, History or Favourites row (`lookup.js` `mountArticle` →
`ordparDefs` → `scan`, the id from the `r<id>-hw` heading); small articles, nested too (`mini.js`
`fill` → `ordparAudio.mount(box, id, page)` before `fit`, the header word given a button where it is
the target's main form). **Not** on list-view rows, suggestions, History or Favourites rows, Recent, or
hover peeks.

**Loading** (only under `minifetch` = `point` and `page`): a `preconnect` to the Worker as an article
with icons opens (a connection, no request); and when the mouse pointer has rested on an icon for 150 ms
without moving — never for a pointer passing over, never on touch, where a tap plays — the names file
for the article's range (from our own host), then that one clip; the press then plays that very
element. The last eight clips played are kept for a repeat. **The names file is never fetched as an
article opens**: only at the first press in its block, or a rest where the setting allows it, once per
page life (a press while it loads plays once it is in). Under `click` nothing is fetched or connected
before a press. Each rested-on clip that is not played spends one request of the Cloudflare account's
daily allowance, shared with the receiver ([`ordpar/audio-worker/README.md`](../audio-worker/README.md)
§ the daily limit).

**Offline and failure.** The service worker leaves other origins to the network, so the clips are never
offline and the names files are not in the offline copy. An icon still shows offline (it is the page's
mark); a press that cannot play — no connection, a names file that failed (fetched again on the next
press), a text the file lacks, a media error — stops, and the icon is faded (`ordpar-play-failed`) for
1.5 s. A block of ids with no names file has no icon to press, so no request is made.

**Norwegian only**: the icons sit on the Norwegian texts, so they stay under the layer, named in
Norwegian; where a setting hides a Norwegian line, its icon goes with it.

**The Anki deck** ships the site's sheet but not `audio.js`, and its cards carry no marks (the marks are
written by `build_site.py`, not by the fragment renderer), so no card shows the icon.

## The prose pages

About, Help, Coming to Ordpar, More ways to use Ordpar, the three change lists, Privacy, Thanks and the
survey are prose pages written by this build from Markdown under `ordpar/`, rendered by
`ordpar/sitegen/about.py` (its docstring is the Markdown subset) in the About page's frame
(`page._prose_page`): the site's header and footer, the head lines, the stamp, and the article page's
`theme.js`, `ordpar.css` and `ordpar.js` (which registers the service worker). Each is titled "*page
title* — Ordpar" with no meta description.

**The key to the pronunciation marks** ([123](../../docs/decisions.md#d123)) is the Help
page's § Pronunciation (`ordpar/help.md`, `/help/#pronunciation`): the respellings are ordinary
Norwegian spelling; a mark after the stressed syllable of a word not stressed on its first shows the
stress and the word tone, ˊ for tone 1 and ˋ for tone 2, with *bønder* and *bønner* as the pair the
tones tell apart; a hyphen means only part of the word is spelt out. The article itself carries no
key and no link to it (§ The compound line, the "Se:" line, pronunciation): the way there is the
footer's Help link, on every page (`chrome.HELP_HREF`). The Help page is in the offline copy. **The subset**: headings, paragraphs, `*italic*`, links,
bulleted lists (a block of `- ` lines, a wrapped item's indented continuation lines joined into it),
numbered steps (a block of `1. ` lines), a line of code under a step (an indented line wholly in
backticks: `<div class="ordpar-code"><code>`, `user-select: all`), a heading's fixed id after its words
(`## Practise the words in Anki {#anki}`), and conditional blocks `[if name]…[/if]`. Every `## ` heading
gets an id from its words where the page asks for it (`about.slug`: lower case, letters and digits,
hyphens; stable while the words are).

| page | source | notes |
|---|---|---|
| `/about/` | `ordpar/about.md` | with the build's numbers; also the published repository's README |
| `/help/` | `ordpar/help.md` | `#settings`, `#pronunciation` |
| `/coming/` | `ordpar/coming.md` | work that is decided, each with what it waits for, no dates |
| `/more/` | `ordpar/more.md` | `#popup` (Definer), `#anki`, `#offline` |
| `/changes/`, `/dictionary-changes/`, `/deck-changes/` | `ordpar/changes.md`, `ordpar/library-changes.md`, `ordpar/deck-changes.md` | each `## ` a dated entry with its id ("2026-11-07, second update" is `#2026-11-07-second-update`); the leading comment dropped |
| `/privacy/` | `ordpar/privacy.md` | only while `chrome.PRIVACY` is on; `noindex` |
| `/thanks/` | `ordpar/thanks.md`, `ordpar/reader-fixes.jsonl`, `ordpar/reader-ideas.jsonl` | only while reports are on |
| `/survey/` | `ordpar/site/survey.json` | only while the survey is on; `noindex`, not offline |

**Indexed** (no `noindex`, their canonicals, in the sitemap): About, Help, Coming, More, the change
pages and Thanks (`INDEXED_OTHER` in `build_site.py` and `ordpar/sitegen/wordpages.py`, the sitemap's
two writers; `indexed_other()` adds the switched pages by their presence). **In the offline copy**:
`build_offline.SHELL_PAGES` (Help, Coming, More, the change pages) and `OPTIONAL_PAGES` (Privacy,
Thanks, where built).

**The About page and the README are one text** ([63](../../docs/decisions.md#d63)). `about.md` is
rendered into the page by `page.about_page` and written as the deploy clone's `README.md` by
`deploy.py` (`prepare`; `readme --out FILE` alone, for a check). The README keeps the Markdown and adds
the one `[readme]` section. The page's text is not in `strings.py`. **The numbers are the build's**: on
every run `build_site.py` calls `site_stats.measure()` over the rows the pages are built from (after the
gate) and the mirror, puts them in the page and records them in `build.json` as `site_stats`;
`deploy.py` reads them from there, so the README carries the numbers of the build it publishes. Shown:
the articles to the nearest hundred ("about 94,200"), the translated and complete counts exact, the share
of the dictionary's text by running words to a whole percent, and the added example sentences with the
articles holding them. "Our changes to the Norwegian" is a bulleted list, one line per type of change
with its count, filled from the change notice's checker (`stats["corrections"]`) and dated from the
mirror manifest's `created_at`; a type with no count drops its line. The clause about articles still
waiting for their summary is wrapped in `[if no_summary]`. What each count counts: `site_stats.py`'s
docstring. Headings carry ids (`about.render(..., ids=True)`), so `https://ordpar.no/about/#contact`
lands on its section.

**The about pages' tabs** ([176](../../docs/decisions.md#d176)): About · Coming to Ordpar · Changes ·
Privacy · Thanks (`chrome.ABOUT_TABS`, the words `about.tab.*`), a `<nav class="ordpar-tabs">` labelled
"About Ordpar" holding the settings page's pill list (`<ul class="ordpar-jump">`), placed under the
`<h1>` on those pages only (`chrome.ABOUT_TAB_PAGES`). Links, not script-driven tabs; the current page
has `aria-current="page"`, filled in the accent; Changes is current on all three change pages. A tab is
drawn only while its page is built. The tabs are the frame, not `about.md`'s words, so the README never
carries them.

**`/more/`** ([142](../../docs/decisions.md#d142)): the code lines' rules are in `page.PAGE_CSS`
(the step numbers bold in the accent, the code on the pill colour with a border), with the Copy buttons
of § Settings in the address. **The home page's line** "Look words up from any web page, or practise
them in Anki: more ways to use Ordpar", the last five words a link to `/more/` (`home.more`,
`home.moreLink`), is made by `shell.js` `addMoreLine` on the home page only and shown by `shell.css` only
while the main area has `ordpar-idle` (an empty query), so a search hides it. An empty query draws
nothing else.

**The footer's links**: "More ways to use Ordpar" after Help on every page (`chrome.MORE_HREF`), kept in
place by `shell.css` (`order: 2`, as About) so it does not move when the script's links come in, marked
current on `/more/` by `markCurrent`. "About" (`strings.py` `about_link`) is the footer's only link to
`/about/`, the last of the row; the licence stays in the credit's line.

**The change lists' links**: the Changes tab, each other's openings, and the offline copy's update note
("What's new", `offline.js` `showNote`, `offline.noteWhatsNew`, linking `/changes/`). The build never
edits the files.

## Report a mistake, the survey and the receiver's events

Three switches decide what the site sends and which pages exist. They are constants in
`ordpar/sitegen/chrome.py`, read by the build, which writes the addresses into the shipped scripts;
the table's last row is not a switch but the one reading of whether the usage counting is live:

| switch | what it decides |
|---|---|
| `PRIVACY` | the privacy page and nothing else: written or removed, its footer link and tab, `about.md`'s `[if privacy]` |
| `REPORT_RECEIVER` | the address reports go to; empty: no "Suggest a correction" button, no `/thanks/`, no reports text anywhere |
| `SURVEY` | the survey page and its links; its address is the reports' with `/survey`, so it needs reports on |
| `chrome.counting()` | true exactly when `events.js`'s `var RECEIVER` is not empty: the usage counting (read from the script, not mirrored by a second flag) |

**The privacy page** ([104](../../docs/decisions.md#d104), [166](../../docs/decisions.md#d166)):
`ordpar/privacy.md`, rendered by `about.privacy_page` into `page.privacy_page` and written to
`/privacy/` only while `PRIVACY` is on; while off, no page (one an earlier build left is
deleted), no link. With it on, "Privacy" follows "About" in every footer (`footer.privacy`), and the
build stops on a `privacy.md` still holding a `[[…]]` placeholder. **What it says follows the senders**:
`[if counting]`, `[if reports]`, `[if survey]`, `[if receiver]` (either sender) and their reverses `[if
no_counting]`, `[if no_reports]`, `[if no_receiver]`; blocks may nest (`about.privacy_text`, innermost
first; an unknown name or an unbalanced block stops the build). With the counting off the page says
Ordpar does not count its readers, and its sections on counting drop out. It names every company that
handles readers' data. It has a contents list (`about.render(…, index=)`: a `<nav class="ordpar-toc">`
before the first heading, labelled `privacy.contents`, "On this page"); only this page has one. A
paragraph after the opening, outside any `[if …]` block, names the offline copy as the way to look words
up without anyone seeing which, and `minifetch` = `click` as the way to fetch nothing before a click;
this is true because the service worker answers searches, articles and word pages from the copy
([`offline-app.md`](offline-app.md) § 4) and the sound icons follow the setting. **Reports need the
page**: the build refuses `REPORT_RECEIVER` set while `PRIVACY` is off (`privacy_for_build`: the form
links `/privacy/#reporting-a-mistake`), except a look build (below), which writes `/privacy/` for that
build alone with a line saying so and no links. The build prints both switches and records them in
`build.json` `privacy_166`. Tests: `test_ordpar_privacy166.py`, `test_ordpar_privacy104.py`.

**Suggest a correction** ([166](../../docs/decisions.md#d166)). **`ordpar/site/report.js`**, in
both bundles, draws a third button, "Suggest a correction", after Copy link and Share in every article's
foot row: the article page's (`page.PAGE_JS` `foot`) and the row under an article shown whole by
`lookup.js` (`resultControls`). Small articles and the deck's cards have none. Drawn by script, so no
page's markup depends on it.

- **The address**: the build writes `REPORT_RECEIVER` into `report.js`'s one line `var REPORT_RECEIVER
  = ''` (`page.report_js`, `REPORT_SLOT`), and so into both bundles; a source `report.js` whose line
  already holds an address fails the build. For one build, `ORDPAR_REPORT_RECEIVER` in the environment
  overrides it (`build_site.report_receiver_override`): a **look build** against a local stand-in for the
  receiver ([`ordpar/receiver/README.md`](../receiver/README.md) § A look build). `build.json` records it
  (`reports_166`). It is independent of the counting.
- **The form** opens under the foot's row: a text box (required, at most 2,000 characters, four lines),
  "Where is the mistake? (optional)" as a drop-down (Translation, Audio, Norwegian text, Other), an
  optional email address, an optional name to credit (at most 60 characters, no links: `report.js`
  `creditOk`), a line before Send linking the privacy page's section on reports (`report.privacy`,
  `/privacy/#reporting-a-mistake` = `chrome.PRIVACY_REPORTS_HREF`, in a new tab so the text written is
  kept), Send and Cancel, and a hidden trap field. Focus goes into the text box; Cancel and Escape close
  it and return focus to the button (`aria-expanded`, `aria-controls`); the status line and the
  confirmation are `role="status"`. A failure, a 429 (the receiver's hourly cap) or no connection is
  said in the status line and the text kept; a success closes and empties the form and shows "Thank you,
  your report has been sent." on a line of its own. The words are `ordpar/site/strings/en.json` `report.*`. The look:
  the button a pill like Copy link (`ordpar-result-btn`); the form under a rule at the card's width, Send
  in the accent, Cancel the muted pill (`shell.css` § "Suggest a correction").
- **The phone row**: at the phone breakpoint (`max-width: 32rem`) Copy link is not shown where Share is
  (the share sheet has its own copy), so Share, "Suggest a correction" and the heart keep one line; where
  the browser has no Share, Copy link stays. There is no "Article page" link in the row
  ([168](../../docs/decisions.md#d168)); the static word pages' list rows keep a hidden `<a
  href="/bm-en/<id>/">Article page</a>` as the fallback without script and for crawlers, which the
  script replaces.
- **`https://ordpar.no/bm-en/<id>/#report`** opens the article's page with the form open, focus in its
  text box (the Anki deck links each card's article so). The key is `report.js` `ADDRESS_KEY`, the bare
  word `report` as one of the fragment's `&`-separated parts, in any order beside a search or settings
  (`#q=hus&report`, `#theme=dark&defs=en&report`); `report` is not a setting. The page script calls
  `fromAddress` once the foot's row is in the page: it presses the button and takes the key off the
  address (`takeAddress`, `history.replaceState`), so a reload, Back, a bookmark or a shared copy never
  opens it again. Only the exact word; without the button nothing happens and the key stays; the
  article page only (a word page or search may show several articles). Nothing about where the reader
  came from is sent.
- **What is sent**, at Send only: `{id, build, category, text, reply, credit}` (`report.js` `message`;
  `hp` only when the trap is filled) by `fetch` with `credentials: 'omit'`, `referrerPolicy:
  'no-referrer'`, as `text/plain` (no preflight). `build` is `/offline/version.json`'s id, read once at the
  first Send (null if unreadable). Nothing is stored. Not held back by the stats setting, Global Privacy
  Control, Do Not Track or `navigator.webdriver`: a report is the reader's own message. The receiver's
  side: [`receiver.md`](receiver.md) § Reports.

Tests: `test_ordpar_reportaddr166.py`, `test_ordpar_browser_report166.py`,
`test_ordpar_browser_reportaddr166.py`.

**The thanks page, `/thanks/`** ([166](../../docs/decisions.md#d166),
[183](../../docs/decisions.md#d183)), "Thanks to our readers", written by every build while reports
are on (`page.thanks_page`, `ordpar/sitegen/thanks.py`; removed otherwise, `build_site.write_thanks`),
from `ordpar/thanks.md` and two committed files. Under "Corrections": X reports led to Y fixes (X the
distinct report ids, Y the lines), counted at build time from `ordpar/reader-fixes.jsonl` — one line per
fix, `{"fix", "date", "article", "reports", "names"}`, written by the maintainer's reports tool — then
the fixes, newest first: the headword (from the mirror, linked), the date, and the published names or "a
reader" ("readers" for several). With no fixes, "No report has led to a fix yet." Under "Ideas from our
readers": the ideas taken up or planned, from `ordpar/reader-ideas.jsonl` — one line per idea, `{"idea",
"date", "title", "text", "names"}` and an optional `"credit"` (`"reported"` for "Reported by"), kept by
hand; a bad line fails the build (`thanks.read_ideas`, `check_idea`). Each idea: its title in bold with a
colon, the text, then "Suggested by" the names (or "a reader"); newest first; with no ideas the section
goes (`[if ideas]`). Linked from About's "Thanks", not from the footer (`chrome.THANKS_HREF`).

**The readers' survey** ([173](../../docs/decisions.md#d173)). **One data file**,
`ordpar/site/survey.json`, holds the title, the intro, every question (its key, kind, label, hint,
choices, limit, `skip_if`) and the page's other words, so questions can change without touching code.
`ordpar/sitegen/survey.py` checks it (`check` refuses a key the receiver would refuse, a limit beyond the
receiver's, a `skip_if` that names no earlier one-choice question and its choice, a follow-up question
not last) and renders the body: the intro, then one form on one page — a fieldset of radio buttons for
one choice, of check boxes for several, a one-line field or a text box, each with its label, hint
(`aria-describedby`) and `maxlength`; the follow-up field last; the hidden trap; the status line; Send;
the words for the script as a JSON island. The fields use the report form's classes plus a few
`.ordpar-survey*` rules in `shell.css`. **The page** is `/survey/` (`page.survey_page`, `noindex`, not in
the sitemap, not offline since it needs a connection), with **`ordpar/site/survey.js`**: it hides a
question while its `skip_if` answer is chosen (never sending it), and at Send posts one JSON message,
`answers` (each answered question under its key) and `follow` (or null), with `credentials: 'omit'`,
`referrerPolicy: 'no-referrer'`, `hp` only when filled. Nothing answered: said, nothing sent. Without
script the questions show and a line says sending needs JavaScript. **The switch** `SURVEY` (address:
`chrome.survey_receiver()`) decides the page (`build_site.write_survey`), the address written into
`survey.js`'s `var SURVEY_RECEIVER = ''` (`page.survey_js`), the link `/survey/` written into
`shell.js`'s `var SURVEY_HREF = ''` (`page.survey_link_js`), and the privacy page's `[if survey]`. A slot
holding a value in the source fails the build. `ORDPAR_SURVEY` ("1" or "0") overrides it for one build;
`build.json` records `survey_173`. **The footer's "Tell us what you think →"** (`footer.feedback`) is
made by `shell.js` `addChrome` from `SURVEY_HREF`, linking `/survey/` in the same tab: after the "under
development" note while the launch switch is on, and on a line of its own where the note was after
launch (`p.ordpar-feedback-line`). The receiver's side: [`receiver.md`](receiver.md) § The survey. Tests:
`test_ordpar_survey173.py`, `test_ordpar_browser_survey173.py`.

**The receiver's events** ([26](../../docs/decisions.md#d26), [62](../../docs/decisions.md#d62),
[104](../../docs/decisions.md#d104)). **`ordpar/site/events.js`**, in both bundles, is the page's
one sender of usage counts to the receiver (`ordpar/receiver/`, a Cloudflare Worker; what it keeps:
[`receiver.md`](receiver.md)). **Its address is `var RECEIVER = ''`, the one place in the site's code;
empty, nothing is ever sent**, and the site works the same. It sends nothing under
`navigator.webdriver` (the browser tests), offline (`navigator.onLine === false`), or with Global Privacy
Control or Do Not Track. Each event goes by `fetch` with `keepalive`, `credentials: 'omit'` and
`referrerPolicy: 'no-referrer'`, no retry:

- a **view** (the path only), once the page has been visible two seconds or at the first scroll, tap or
  key; a path that is not one of the site's own is sent as `/other` (`cleanPath`);
- an **install** (`install.js`, at `appinstalled`);
- a **hit** and a **miss** from `lookup.js` `render` for a search the reader made, the miss held until a
  similar word is chosen (sent with it and its position) or the page is hidden or a new search starts;
- a **pick** from `shell.js` (`picked`): a suggestion chosen by Enter or a press, with the text typed so
  far, the word and its position from 1; a Recent row is not a pick.

Every hit, miss and pick carries `lang`, `'en'` or `'nb'`; a held miss is chosen only by a choice in its
own language (`missChoose(query, word, position, en)`). Never per keystroke; a query with a digit or over
40 characters is never sent. Nothing is written to storage. **The opt-out**: the setting `stats` = `on`
| `off` ("Send usage statistics") in *Loading, offline and your data* is drawn only while the counting
is live — the index build writes `<script>window.ORDPAR_COUNTING=true;</script>` in place of the
settings page's `<!--ORDPAR_COUNTING-->` then, and nothing otherwise (`shell.js` `SETTINGS` `gate:
'counting'`, `settings.js` `drawn`). `events.js` honours a stored `off` either way, read at every event;
"Delete stored data" and "Reset settings" turn it back on.

## The frame and the colours

([63](../../docs/decisions.md#d63)) As ordbokene.no shows the same header on article and search
pages and a footer on every page:

- **One header, one footer**: `chrome.header` / `chrome.footer`, called by this build (article and prose
  pages) and by `build_index.copy_shell` (the front page, the search page, 404, `/favourites/`,
  `/history/`, `/settings/`, through the markers `<!--ORDPAR_HEADER-->` and `<!--ORDPAR_FOOTER-->`).
  `shell.js` enhances the header ([`lookup-index.md`](lookup-index.md) § 7). Their words are the shell's
  strings; another interface language relabels the static ones in the browser by selector (`shell.js`
  `STATIC_STRINGS`, the same map as `chrome.RELABEL`; a test holds them equal). The About link is
  relabelled with the key `about_link`, which the shell pages' inline strings lack, so there it keeps its
  built words. Without JavaScript the search box is a form that searches on Enter, and nothing that
  needs script is in the markup.
- **The article in a card** (`.ordpar-card`, `shell.css`'s result card) with its controls at its foot.
  The card takes ordbokene.no's widths ([102](../../docs/decisions.md#d102)): the main area of the
  article, search, 404 and favourites pages is `.ordpar-main--cards`, fluid below a 48rem window, then
  736 / 992 / 1,248 / 1,504 px; the text runs at the card's width, and the inflection table keeps to the
  card, wide where it fits and narrow where not (`inflection.js` `fit`, from `mountAll`).
- **The "under development" note**: while the launch switch `head.NOINDEX` is on, the footer closes with
  it (`.ordpar-devnote`: the footer's type, italic; at night the footer's muted grey, by day a step
  darker, `#625d5d`, 5.8:1, since the muted grey is only 4.39:1 on the footer's ground). The same switch
  removes it at launch.
- **The colour schemes** (`ordpar/sitegen/colours.py`; the setting "Accent colour"): Wine `#6b0f2e`, the
  default, its night tint `#e3b7c9`; Burnt orange `#b13a0b` with its own computed tint; and
  "ordbokene.no's maroon" `#560027` with ordbokene.no's black-and-white night (white headings, `#880e4f`
  link underlines, sampled from its rendered dark mode) — the only place `#560027` appears. Whichever
  scheme is the default (`colours.DEFAULT`), its night accent is `#e3b7c9` (`TINT_REF`, applied by
  `colours.effective`); a scheme chosen while it is not the default keeps its own night. The
  browser's theme colour, the manifest and the icon follow the default. **Every use of the deck's maroon
  and its night tint goes through variables**: `--ordpar-maroon` / `--ordpar-tint` (and their `-rgb`),
  `--ordpar-night-line` for a link's night underline. The deck's sheets are rewritten site-side at build
  time (`page.DECK_ACCENT`: 17 × `#560027`, 2 × `rgba(86,0,39,…)`, 9 × `#e3b7c9`, 1 ×
  `rgba(227,183,201,…)`, 1 × `#7a5566`, each with a fallback that is the default scheme's value, so
  `#560027` appears only under its own scheme); `ordbok_gen.py` and `scripts/mini.py` are untouched.
  `SITE_CSS`, `PAGE_CSS`, `shell.css` (`--ordpar-accent`, `--ordpar-focus`) and `inflection.css` use the
  variables. Not routed (the same under every scheme): `#f3e9ed` (the idiom tag, `--ordpar-pill`),
  `#b98ba1` (unused on the site), `#4a2e37` (night pill). The service worker's offline notice, the icon
  and the manifest use the default only.
- **The night page** ([157](../../docs/decisions.md#d157); `shell.css`): `--ordpar-bg` #1b1819 and
  `--ordpar-surface` #242021, shared by the cards, settings panels, menus and dialogs.
- **Cross-references in ordbokene.no's style**: upright, in the text's colour, a solid 1.5px underline
  in the accent (at night the scheme's night line, else its tint), inside small articles too; the deck's
  hover and opened backgrounds kept. **The headword at weight 600.** Both are `SITE_CSS` overrides, later
  in `article.css` than the deck's rules.

The frame costs about 2 KB raw, 0.6 KB gzipped, per article page (the header about 1.2 KB, the footer
about 0.9 KB, the "Article view" line and the script tag), before the savings below.

## Keeping the pages small

With some 94,000 pages, every byte per page counts about 94 KB on the site and in the offline download.
These savings change nothing a reader sees, with or without script; they live in
`ordpar/sitegen/slim.py` and `page.finish`, site-side only (`ordbok_gen.py` and `scripts/mini.py` are
untouched). Keep them when changing the page:

1. **Indentation stripped** at write time (`slim.strip_indent`: `\n[ \t]+` → `\n`; no page has a `<pre>`
   or a `white-space: pre` rule). Newlines between tags stay: dropping them can change the rendering.
2. **No build stamp in the pages**; it is in `build.json`, and the About page shows it.
3. **The head script is a file**, `/site/theme.js` (`head.THEME_JS_HREF`), parser-blocking before the
   sheet, so the classes are on `<html>` before the first paint. It is in the offline shell pack.
4. **One stylesheet and one deferred script** per page (`page.COMBINED`); `ordpar.js` carries the
   merged strings, so an article page does not fetch `/site/strings/en.json`. **Every published script and
   stylesheet ships without comments** (`slim.strip_js`, `strip_css`: a scanner aware of strings,
   template literals, regular-expression literals and `//` inside URLs; names, line breaks and code
   untouched; a `/*!` header goes too). The separate files are still written (the search page reads
   `inflection.js`, `article.js`), stripped likewise.
5. **Chrome that needs script is made by script**: the header's Random word, Favourites and Settings,
   the footer's Settings, Favourites and History, the install hint, the feedback link, and the card
   foot's controls are not in the markup; `shell.js` `addChrome` inserts the header's and footer's (then
   sets `ordpar-chrome` on `<html>`), the page script the foot's. Until then `shell.css` holds their room
   under `html.ordpar-js:not(.ordpar-chrome)` (the header's `::after`, about 119 × 35 px; the empty card
   foot's `::before`), so nothing shifts. The empty `<footer class="ordpar-card-foot"></footer>` stays:
   `lookup.js` `extractArticle` cuts at it.
6. **No `data-ordpar-string`**: relabelling goes by selector (`STATIC_STRINGS` = `chrome.RELABEL`), kept
   in code because it is markup structure, the same for every language; a new interface language still
   costs one strings file ([21](../../docs/decisions.md#d21)).
7. **`data-snip` left out where it equals the meta description** (readers fall back to it: `lookup.js`
   `pageMeta`, `personal.js` `fieldsFrom`).
8. **Redundant `lang` dropped** (`slim.drop_redundant_lang`) where it equals the inherited one — kept on
   `<html>`, the fragment root, every `ordbok-xmini` span and the children of `.ordpar-pair` /
   `.mini-pair`, which the sheets select by attribute (dropping those changes the rendering).
   `data-other-entries` is written only above 0.
9. **The paradigm island in the compact schema** (`slim.compact_paradigm`;
   [`inflection-table.md`](inflection-table.md) § 1): only what `inflection.js` reads, the tag sequences
   moved to one site-wide table of shapes (content-hashed ids, refused on a clash, collected from the
   whole mirror so an `--ids` build agrees; `inflection.js` `SHAPES` / `decode`). No island and no toggle
   where nothing renders (about 11,700 pages).
10. **No `data-href` on the links**: the link's own `href` is the target.
11. **Unused class tokens dropped**: `ordbok-xref-hover`, `ordpar-home`, `ordpar-mono`, `ordpar-other`.

Together these took the published site from 871 MB to 543 MB (article pages 802 to 481 MB) and the
offline download from 48 to 40 MB. The largest items: chrome made by script (100 MB), the inline head
script (61 MB), the paradigm island and toggle (67 MB), the separate script and sheet tags (40 MB). They
were checked with screenshot pairs (light and dark, script on and off, 1280 and 390 px), identical
tables for every paradigm, layout shift no worse, and `build_offline.py --verify`.

## The deploy

`ordpar/deploy.py` publishes the output folder to GitHub Pages as **one snapshot commit** in a clone kept
outside the repository (`deploy_clone` in the local paths), force-pushed, so the published repository
never grows a history. `python ordpar/deploy.py --help` is the reference. It is guarded
([61](../../docs/decisions.md#d61), [103](../../docs/decisions.md#d103),
[109](../../docs/decisions.md#d109)):

```bash
python ordpar/deploy.py prepare     # the change lists, the gate, then the snapshot (no network)
python ordpar/deploy.py push        # publish, then the check after the push
python ordpar/deploy.py verify      # the check after the push alone
python ordpar/deploy.py rollback    # the previous good snapshot, as it was; then push
python ordpar/deploy.py status      # what the clone holds, what is live, what a rollback would restore
python ordpar/deploy.py test        # the gate alone, nothing copied
python ordpar/deploy.py readme --out FILE   # the README prepare would publish
```

- **The reports' address.** First, `prepare` refuses a build whose reports address —
  `build.json` `reports_166`, and the address in the shipped `report.js`, `ordpar.js` and
  `shell-pages.js` — is anything but empty or `https://` on a public host name (not http, an IP address,
  localhost or a local name), or whose record and scripts disagree, or that has reports on but no
  `/privacy/` carrying `id="reporting-a-mistake"` (`deploy.report_address_problem`, `check_reports`). So a
  look build cannot be published by mistake. Test: `test_ordpar_deploy166.py`.
- **The change lists.** Then `prepare` checks that this deploy's entries were written and committed
  since the last published snapshot (the newest push in the clone's deploy log; for an older clone,
  `origin/main`'s commit time): `ordpar/changes.md` needs a newer commit at every deploy;
  `ordpar/library-changes.md` must exist and needs a newer commit when the library changed — when a
  fingerprint of `build.json`'s `site_stats` and `change_notice` counts, recorded in the deploy log with
  each push, differs from the last snapshot's. A refusal names the file and the step. `--skip-changes
  "<reason>"` lets through a re-deploy with nothing reader-visible to say; the override is appended to
  `ordpar/deploy-overrides.jsonl` and printed. `rollback` needs no entry.
- **The gate.** Then `prepare` runs every test file, the browser tests against the build it is about to
  publish (`ORDPAR_TEST_OUT`), in parallel (`--jobs`, at most `BROWSER_JOBS` browser files at once, each
  serving the build on its own port with its own Edge profile), and refuses on any failure, naming the
  files, before the clone is touched. The full suite takes about seven minutes. `--skip-tests
  "<reason>"` lets an urgent fix through: the tests still run, and one JSON line (time, stamp, offline
  build id, reason, failing files) is appended to `ordpar/deploy-overrides.jsonl`.
- **The check after the push.** `push` waits (up to 15 minutes, `--wait`) until
  `https://ordpar.no/offline/version.json` names the build just pushed, then runs the browser tests
  against the live site (`ORDPAR_TEST_BASE`). A failure undoes nothing: it names the failing files and
  prints the rollback commands. A browser test pinning a fix newer than the build fails on it by design,
  so after a rollback the check can fail on the restored snapshot.
- **The rollback** re-publishes the previous good snapshot **as it was**, build id included, as a new
  snapshot commit. An installed offline copy updates whenever `version.json` names a build different
  from its own ([`offline-app.md`](offline-app.md) § 6), so a copy on the bad build goes back (fetching
  only the packs it lacks), and a copy that never took the bad build sees its own build and does nothing.
  "Previous good" is the newest published snapshot that is not live, not one a rollback left, and not one
  whose check failed, from the clone's deploy log (a JSON-lines file in its `.git` folder, one line per
  push, check and rollback) or, for older pushes, the reflog of `origin/main`; `--to REV` names another.
  `push` keeps a ref to each of the last three published snapshots (`refs/ordpar/pushed/*`) so their
  objects outlive the reflog. `rollback`, like `prepare`, never pushes.

## The code

```
ordpar/build_site.py         the build: flags, the page loop, the prose pages, build.json
ordpar/site_stats.py         the About page's numbers
ordpar/sitegen/deck.py       imports the deck's renderer and pipeline modules from the repository root
                             (ordbok_gen.py, scripts/*.py): one renderer, no copy
ordpar/sitegen/gate.py       the example gate
ordpar/sitegen/mirror.py     the mirror index and random access; the "more entries" count; Listing
                             (listed / unlisted / kept); the overlay hook (set_overlay, raw_data)
ordpar/sitegen/overlay.py    the corrections to articles with no library row
ordpar/sitegen/library.py    which face an article gets, derive on demand (memoized), and the rows one
                             page's markup must resolve against
ordpar/sitegen/lemma_order.py  our headword spelling order, from the normalization log
ordpar/sitegen/face.py       the site face over the deck's markup: a plain link and its peek, the
                             small-article shim that draws nothing, the marker shim
ordpar/sitegen/article.py    the article fragment; snippet, dropdown_text; formula lines; compound labels;
                             the "Se:" line
ordpar/sitegen/pronunciation.py  the pronunciation section
ordpar/sitegen/describe.py   the title and meta description
ordpar/sitegen/page.py       the page around the fragment, SITE_CSS and PAGE_CSS, the page script,
                             the favourites attributes, what /site/ serves (source, shipped, asset, COMBINED)
ordpar/sitegen/head.py       the head lines and the head script THEME_JS (shared with the index build)
ordpar/sitegen/chrome.py     the header, the footer, the credit, the switches
ordpar/sitegen/colours.py    the colour schemes and the default
ordpar/sitegen/strings.py    every chrome string
ordpar/sitegen/slim.py       the size savings: comment stripping, indentation, redundant lang, compact island
ordpar/sitegen/corrections.py  the change notice and the About page's counts of corrections
ordpar/sitegen/audio.py      the audio marks and the names files
ordpar/sitegen/about.py      the prose pages' Markdown, the About page and the README
ordpar/sitegen/thanks.py     the thanks page
ordpar/sitegen/survey.py     the survey page
ordpar/sitegen/wordpages.py  word and form pages (used by the index build)
ordpar/site/                 the browser's files: mini.js, ahead.js, audio.js, report.js, survey.js,
                             events.js, shell.js, lookup.js, personal.js, settings.js, inflection.js, …
ordpar/root/                 the files served from the site's root: sw.js, manifest.webmanifest, robots.txt
```

**The deck shares this code.** The Anki deck renders its cards through the same fragment renderer and
the same `mini.js`, and builds its sheet from the site's (`article.css`, `shell.css`); a change to
`SITE_CSS`, `mini.js` or the page script reaches the deck at its next update. The deck's own options
are additive: `mini.render(…, side="no")` renders a small article's Norwegian face and `side="both"` its
line pairs (`scripts/mini.py`), and the deck's output is byte-identical without them.
`article.fragment(site=True)` and the audio marks are the site's alone.

