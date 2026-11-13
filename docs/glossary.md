# Glossary

The words this repository uses in its own sense, and the shorthand in the code's comments. Each
entry points to where the thing lives; the [overview](overview.md) says how the parts fit.

## The project's words

- **Band.** A headword's frequency band, 0 to 15, written into the search index as one hex digit:
  how common the word is in the National Library of Norway's word counts, scaled to that corpus
  (`headword_bands` and `FREQ_SCALE` in `ordpar/build_index.py`). Suggestions and similar words
  rank higher bands first. Without `--freq` every band is 0.
- **Capture.** One of the article files in `data/sources/articles/`: Bokmålsordboka's article,
  pruned to the fields the translation work reads, with our hand corrections in it. The library's
  Norwegian was derived from these (`CAPTURES` in `ordpar/export_public.py`).
- **Corrected copy.** Bokmålsordboka's data with our fixes applied, in
  `data/bokmalsordboka/corrected/` ([its README](../data/bokmalsordboka/README.md)).
- **The deck.** Ordpar's Anki flashcard decks, which the private repository builds from the same
  library. The article renderer, `ordbok_gen.py`, was written for the cards and is shared with the
  site, which is why the code calls it "the deck's renderer".
- **Derived.** The Norwegian side of a row, made mechanically from Bokmålsordboka's JSON by
  `scripts/derive.py` (`derive_row`). An article with no library row is derived from the mirror
  as the build runs (`Store` in `ordpar/sitegen/library.py`).
- **Gate.** Two things. *The example gate*: an added example sentence is published only once a
  native speaker has written or approved it; the library here has been through it already.
  *The deploy's gate*: `ordpar/deploy.py prepare` runs every test file before it publishes, and
  stops on a failure.
- **Gate marker.** `data/articles.jsonl.gate.json`: the record that the library went through the
  example gate, with the library's SHA-256. The build refuses a library without a matching one;
  `gate.write_marker` in `ordpar/sitegen/gate.py` writes a new one
  ([`data/README.md`](../data/README.md)).
- **Handover.** What we sent to ordbokene.no's editors: the errors that the scripts in
  `handover/checks/` found, and our corrections to Bokmålsordboka's text
  (`data/review/mirror-corrections.jsonl`).
- **Homograph.** One of several headwords spelled the same, which Bokmålsordboka numbers with a
  Roman numeral (*bank* I to IV).
- **Library.** `data/articles.jsonl`: one row per article we have begun to translate, and per
  article their cross-references lead to, with the Norwegian and the English side by side
  ([`data/README.md`](../data/README.md)).
- **Listed, unlisted.** A *listed* article is one in the index of articles ordbokene.no lists,
  `data/bokmalsordboka/bm-listed.jsonl`. An *unlisted* one has left that index; the API may still
  serve it, or answer 404. The site gives an unlisted article a page while the API serves it, but
  no place in search, unless we have translated it and no listed article with the same headword is
  translated (`Listing` in `ordpar/sitegen/mirror.py`).
- **Mirror.** Our copy of Bokmålsordboka's data, every article as the University of Bergen's API
  serves it, one per line: `data/bokmalsordboka/bm-articles.jsonl` once joined, the file the
  builds' `--mirror` names.
- **Norwegian only.** The page of an article that is not translated: the whole article in
  Norwegian, marked *Norwegian only*. Also a setting that shows every article that way.
- **Overlay.** Our corrections to the mirror, applied in memory as the build reads an article
  (`ordpar/sitegen/overlay.py`); the data files are never written.
- **Pair.** The dictionary pair, `bm-en` (Bokmålsordboka to English): the first part of every
  article's address, `/bm-en/<id>/`, never the interface language (`PAIR` in
  `ordpar/sitegen/face.py`).
- **Peek.** The short preview shown when the pointer rests on a cross-reference: the target's
  English, or its first Norwegian definition if the reader's settings ask for that. The build
  writes it into the page beside the link (`_link` in `ordpar/sitegen/face.py`); the style sheet
  shows it.
- **Row.** One line of the library: one Bokmålsordboka article, by its id.
- **Set phrase.** A fixed expression, which Bokmålsordboka keeps as an article of its own and
  prints in the articles of its words. Its row's `pos_en` is `"fixed expression"`.
- **Shard.** One of the small files the search index is split into, one per initial letter, with
  the five largest letters (b f k s t) split again by the second, so that a search loads only what
  it needs ([`ordpar/docs/lookup-index.md`](../ordpar/docs/lookup-index.md)).
- **Small article, mini.** What a click on a cross-reference opens in place: the target's senses,
  cut from the target's own page (`ordpar/site/mini.js`).
- **Snippet.** The one-line text of an article in the search's list view, written by the article
  build and filed in the index by `ordpar/build_index.py`.
- **Summary gloss.** The short list of English equivalents shown under a translated article's
  headword (`summary` in a row).
- **Translated.** An article whose row has English for every line (`complete_strict` in
  `scripts/coverage.py`). Only a translated article is shown in English; no page is half English.
- **Word page.** A page at `/bm-en/<word>/` for a word whose first article is translated, and for
  common irregular inflected forms (`ordpar/sitegen/wordpages.py`).

## The shorthand in the code's comments

- **"decisions N"** (also "site decisions N" and "site-review decisions N") is entry N of
  [`decisions.md`](decisions.md). The numbers have gaps where an entry is about the project
  rather than the code.
- **"audio decisions N", "context-cost decisions N"** and the like, with another word before
  "decisions", name entries in other logs of the project, which are not published.
- **"Robin, <date>"** is a ruling of Robin Fauskanger's on that date.
- **"brief N"** (such as "brief 59b"), **"build A", "build B"** and the like name the project's
  private working papers: the briefs a piece of work was done from, and two early pieces of work
  (build A the article pages, build B the inflection tables). They are not published; a reader can
  pass over them.
