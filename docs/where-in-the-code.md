# Where each divergence lives in the code

These tables are for ordbokene.no's developers, and for anyone taking one of Ordpar's features into
their own dictionary site: for each place where Ordpar differs from ordbokene.no and we think the
difference could be of use to ordbokene, they say where it lives in the code. Each row's reason,
and what ordbokene.no does instead, is in [`divergences.md`](divergences.md), under the same name.
There, **Yes** marks a change ordbokene could adopt, and **Maybe** a judgement call, with the doubt.

The rows are in the order of that document. A name in backticks after a file is a function, a
constant or a setting in it; a doc section is where the rule is described.

## Yes

| Divergence | Where it lives |
|---|---|
| Suggestions ranked by frequency | `ordpar/site/lookup.js` `suggestRank`, `rankSuggestions`; `ordpar/build_index.py` `suggest_rank`, with the frequency bands from `read_freq` and `headword_bands` |
| Set phrases after the headwords | the same ranking: rank 3 in `suggestRank` (`ordpar/site/lookup.js`) and `suggest_rank` (`ordpar/build_index.py`) |
| A trailing space asks for set phrases | `ordpar/site/lookup.js` `suggestQuery` |
| One suggestion per article | `ordpar/site/lookup.js` `mergeArticles`; `ordpar/build_index.py` `merge_articles` |
| Roomier suggestion rows, a setting | the setting `suggestrows` in `SETTINGS`, `ordpar/site/shell.js`; the class `ordpar-suggestrows-roomy` in `ordpar/site/shell.css` |
| Similar words ranked by likelihood | `ordpar/site/lookup.js` `similar`, over the `headwords/` and `tails/` files that `ordpar/build_index.py` writes (`similar_file`); [`lookup-index.md`](../ordpar/docs/lookup-index.md) § (3) Similar headwords |
| Spelling rules and first-letter typos | `RULES`, `DOUBLING` and `rewrites` in `ordpar/build_index.py`, and the same three in `ordpar/site/lookup.js`, kept in step |
| Where to look when a word is missing | `ordpar/site/lookup.js` `missWhy`, `MISS_LINKS` |
| List view when there are several articles | `ordpar/site/lookup.js` `listMode`, `useList`; the setting `listview` in `ordpar/site/shell.js` |
| An opened row follows the inflection setting | `ordpar/site/lookup.js` `mountArticle`, which runs the page script (`window.ordparDefs`, whose `infl` applies the setting `infl`) over the opened row; the page script is `_PAGE_JS` in `ordpar/sitegen/page.py` |
| Which form it is | `ordpar/sitegen/wordpages.py` `FormLabels`, written by `ordpar/build_index.py` to `labels.json`, read by `ordpar/site/lookup.js` `labelCode` and drawn by `articleItem` |
| How many examples show under a sense, as an option | the settings `exlimit` and `exmore` in `ordpar/site/shell.js`; in `ordpar/sitegen/page.py`, the cut (`EXLIMIT_CSS`) and the "Show N more examples" line (`exmore` in `_PAGE_JS`) |
| The homograph number read aloud | `ordpar/sitegen/article.py` `head_html`; its words, `homograph` in `ordpar/sitegen/strings.py` |
| Row names kept for screen readers | `ordpar/site/inflection.js` `hiddenLabel`, used by `renderNarrow`; [`inflection-table.md`](../ordpar/docs/inflection-table.md) § 6 |
| A shared first cell in a later gender group | `ordpar/site/inflection.js` `cellKey`, the key the vertical merge in `buildTable` compares, the same in every gender group; [`inflection-table.md`](../ordpar/docs/inflection-table.md) § 4, rule 5 |
| Unique anchors | `ordpar/sitegen/article.py` `expr_anchor_prefix`, `_unique_sense_ids` |
| Data errors corrected | `scripts/postags.py` `pos_en`, the case of the lone tag `false` |
| The more common spelling first | `ordpar/sitegen/lemma_order.py` (`orders`, `reorder`), from the `lemma-order` rows of `data/review/source-normalizations.jsonl` |
| A key to the pronunciation marks | `ordpar/help.md`, its section "Pronunciation" |
| "Suggest a correction" on every article, and a survey | `ordpar/site/report.js`, `ordpar/site/survey.js`; the receiver, `ordpar/receiver/` ([`receiver.md`](../ordpar/docs/receiver.md)); the Thanks page, `ordpar/sitegen/thanks.py` |
| History and favourites | `ordpar/site/personal.js`, `ordpar/site/personal-page.js`; [`lookup-index.md`](../ordpar/docs/lookup-index.md) § History and favourites |
| Hints and sections on the Settings page | `ordpar/site/settings.js` `SECTIONS`, `hintControl` |

## Maybe

| Divergence | Where it lives |
|---|---|
| What a suggestion row shows | `ordpar/site/shell.js` `optionSide` and `fillGlosses`, inside `wireSearch`; the lines they show come from the `snip/` files, `ordpar/build_index.py` `snippet_files` |
| An "N articles" row lists its articles | `ordpar/site/shell.js` `glossList` (inside `wireSearch`), `listedGlosses` and `sideGlosses` |
| Similar words after a miss say what each word is | `ordpar/site/lookup.js` `similarRow`, called from `render`; the row drawn by `ordpar/site/shell.js` `fillSearchRow`, with `similarArticles` |
| Similar words that would only repeat the page | `ordpar/site/lookup.js` `dropRepeats`, `pageSpellings` |
| A link to the word's other articles | `ordpar/sitegen/page.py` `render`, the line above the article (words `other_entries_one`, `other_entries_many` in `ordpar/sitegen/strings.py`); the count, `ordpar/sitegen/mirror.py` `other_entries`; the link sent to the word's page, `ordpar/sitegen/wordpages.py` `patch_article` |
| Inflected forms, with their articles | `ordpar/site/lookup.js` `articleList`, `articleItem`, `fillSnippets` |
| Inflected-form rows, the commonest word first | `ordpar/build_index.py` `form_order`, `form_share`; the cases set by hand in `ordpar/form-order-overrides.tsv` (`read_form_overrides`) |
| No "Example" label; the examples as quote blocks | `ordpar/sitegen/page.py` `SITE_CSS`, the rule for `.ordbok-ex-list` (the comment "THE EXAMPLES' LOOK") |
| A layout closer to ordbokene.no, as an option | the setting `layout` in `ordpar/site/shell.js`; in `ordpar/sitegen/page.py`, the `ordpar-layout-ordbokene` rules in `SITE_CSS` and `exheads` in `_PAGE_JS`; in a small article, `ordpar/site/mini.js` |
| A CEFR level after the headword, as an option | the box, `ordpar/sitegen/levels.py` `box_html`, drawn by `ordpar/sitegen/article.py` after the headword and each set phrase; the levels, `ordpar/levels.tsv`, made by `ordpar/levels_import.py` and read by `ordpar/build_site.py` (`--levels`); the settings `levels` and `phraseorder` in `ordpar/site/shell.js`; the set phrases' order by level, the `ordpar-exprs` rules in `SITE_CSS` and `phord` in `_PAGE_JS`, `ordpar/sitegen/page.py`; [`build-site.md`](../ordpar/docs/build-site.md) § The headword line |
| Example sentences added by Ordpar, marked | `ordbok_gen.py` `_ex_list`, the `ex_added` sentences after the dictionary's own; the mark, `ADDED_MARKER` in `ordpar/sitegen/article.py` |
| The inflection table by fit | `ordpar/site/inflection.js` `fit`, `fitTables`, `stackColumns`; [`inflection-table.md`](../ordpar/docs/inflection-table.md) § 4a |
| The inflection table on an article page | `ordpar/sitegen/article.py` `paradigm_block`, the table inside the "Inflection" button (`ordpar-infl-toggle`); the setting `infl` in `ordpar/site/shell.js`, applied by `infl` in `_PAGE_JS`, `ordpar/sitegen/page.py` |
| Norwegian you can listen to | `ordpar/site/audio.js` (`button`, `press`; the setting `audiospeed`); `ordpar/sitegen/audio.py` `mark`, which marks what has a recording; the Worker that serves them, `ordpar/audio-worker/`; [`build-site.md`](../ordpar/docs/build-site.md) § The audio |
| A click opens a small article | `ordpar/site/mini.js` (`open`, `cut`, `placeNested`); the settings `xref` and `nestminis` in `ordpar/site/shell.js`; [`build-site.md`](../ordpar/docs/build-site.md) § Cross-references and the small article |
| A hover peek in the other language | `ordpar/sitegen/face.py` `_link` (the peek written into the page with its link, and `data-s`, the target's `snip/` key); `ordpar/site/mini.js` `peekOf`, and `nbPeek` for the first Norwegian definition (read from the target's `snip/` file, never fetched under "When its link is clicked"; `snipKeyOf` for an English partner word); the setting `peek` (`on`, `nb`, `off`) and the Norwegian-only view's `nbhover` in `ordpar/site/shell.js` (`hoverNb`), applied before the first paint by `ordpar/sitegen/head.py` |
| Loading ahead, a setting | `ordpar/site/ahead.js` (`aim`, `warm`, `REST_MS`); the setting `minifetch` in `ordpar/site/shell.js`; [`build-site.md`](../ordpar/docs/build-site.md) § Loading ahead |
| Settings in the address, for a pop-up dictionary | the head script's `ordparRead`, `_visit_js` in `ordpar/sitegen/head.py`; the address the Settings page copies, `popupAddress` in `ordpar/site/shell.js`; [`build-site.md`](../ordpar/docs/build-site.md) § Settings in the address |
| An installable app that works offline | `ordpar/build_offline.py`, the service worker `ordpar/root/sw.js`, the download in `ordpar/site/offline.js` (`download`); [`offline-app.md`](../ordpar/docs/offline-app.md) |
| An offer to install | `ordpar/site/install.js` `offer`, `line` (the button in Settings), `hint` (the footer's line); [`offline-app.md`](../ordpar/docs/offline-app.md) § 11 |
| The about pages' navigation | `ordpar/sitegen/chrome.py` `about_tabs`; their style in `ordpar/site/shell.css` |
| Public change lists | `ordpar/changes.md`, `ordpar/library-changes.md` and `ordpar/deck-changes.md`, built by `ordpar/sitegen/about.py` `changes_page`, `library_changes_page`, `deck_changes_page`; the "What's new" link in the update notice, `ordpar/site/offline.js` `showNote` |
