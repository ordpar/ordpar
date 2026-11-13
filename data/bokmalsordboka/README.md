# Bokmålsordboka's data

Every article of Bokmålsordboka, the Bokmål dictionary from Språkrådet (the Language Council of
Norway) and the University of Bergen, exactly as the University of Bergen's API at
`ord.uib.no` serves it, including the articles ordbokene.no no longer lists but the API still
serves. Nothing in the files at this
folder's top level has been changed by us, and nothing has been removed: the `author` field,
which names the editor of each article, is kept as the API gives it. Beside them, in
`corrected/`, is a copy of the same data with our fixes applied (below).

The site build reads this folder as its *mirror*: every article on ordpar.no is built from it,
and an article we have translated also from the library, `../articles.jsonl`
([`../README.md`](../README.md)).

## Where it comes from

The copy was first taken from [ordbokapi](https://ordbokapi.org/)'s public dump of the
dictionaries' database. Thank you to ordbokapi for publishing it: it spares everyone nearly
100,000 calls to the API. Since then it has been kept current from the API itself. Each night
the University of Bergen's index of Bokmålsordboka (one `[id, lemma, revision, updated_at]` row
per article) is compared with the copy, and only the articles that changed or are new are
fetched again from `ord.uib.no`. The tool that does this is in Ordpar's private repository, not here. Each weekly update
of this repository carries the copy as it stood that week.

`manifest.json` is the manifest of the last dump downloaded from ordbokapi, as ordbokapi wrote
it: when it was made (`created_at`), its size and its SHA-256. It does not date the
articles fetched since; each article's `revision` and `updated_at` do.

## The files

| File | What it is |
|---|---|
| `bm-articles.<first id>.jsonl` | The articles, in parts (below). One JSON object per line, in id order: `{"id", "revision", "updated_at", "data"}`. `data` is the article exactly as `ord.uib.no/bm/article/<id>.json` returns it; `revision` and `updated_at` come from the API's index. |
| `bm-listed.jsonl` | The API's index of the articles ordbokene.no lists: one `[id, lemma, revision, updated_at]` array per line. |
| `bm-unlisted.json` | Every article that has left the index, keyed by id: its last `revision` and `updated_at`; `left_index`, the date it left (null for one that had already left when the copy was first made); and `since_404`, the date the API began answering 404 for it (null while it still serves it, and then it is in the articles file). |
| `bm/404/<id>.json` | A stored copy of each unlisted article the API now answers 404 for. An article that leaves later keeps its last text here. Today all the files are empty (`{}`): the dump the copy was first made from held no text for these articles. |
| `bm-concepts.json` | The dictionary's table of abbreviations and labels (`adj` → *adjektiv*), from the API, fetched with the articles. |
| `manifest.json` | The dump's manifest (above). |
| `corrected/` | The corrected copy (below). |

The site gives an unlisted article a page while the API still serves it, but no place in
search. It is in search, and keeps its page after the API answers 404, only when we have
translated it and no listed article with the same headword is translated too
([46](../../docs/decisions.md#d46)).

## The parts, and the join step

The articles file is about 205 MB, too large for one file on GitHub, so it is stored in parts
of 20,000 article ids each: `bm-articles.000000.jsonl` holds ids 0 to 19,999, and so on. Each
part is under 50 MB and uncompressed, so that git stores a week's changes as differences. A
part's range never moves, so an article stays in the same part from one week to the next.

Before a build, put the file back together once:

```
python ordpar/data_parts.py join data/bokmalsordboka
python ordpar/data_parts.py join data/bokmalsordboka/corrected    # the corrected copy, if you want it
```

Each writes `bm-articles.jsonl` in its folder, byte for byte the file the parts were cut from.
Git ignores the joined file. The join checks that every line is an article whose id belongs to
its part, in ascending order. `split` is the other direction, used by the export
(`ordpar/data_parts.py`).

## The corrected copy

`corrected/` holds the same articles in the same parts, with every fix of ours that can be made
exactly, applied to the data. An article we did not change is the original line, byte for byte.
The copy at the top level stays, so that a build reproduces ordpar.no and every fix can be
checked against the original ([184](../../docs/decisions.md#d184)).

Two sets of fixes go in, both through the one piece of code the site build uses for them
(`ordpar/sitegen/overlay.py`):

1. **Our corrections to the dictionary's text**, `../review/mirror-corrections.jsonl`: patches
   already, each naming an `article`, a `path` from the article's `data` to one field, and the
   field's value `before` and `after`. The site applies these only to articles with no library
   row ([182](../../docs/decisions.md#d182)); the corrected copy applies them everywhere.
2. **Our log of corrections to the article files the translation works from**,
   `../review/source-normalizations.jsonl`.
   The log is written in prose, and the corrected text lives in the article files under
   `../sources/articles/`, which may be older than this copy. So `ordpar/corrected_copy.py`
   turns the log into patches mechanically: for each article the log names, it compares that
   file with this copy's article and makes a patch only when the log explains the whole
   difference. The patch's `before` is this copy's value and its `after` that value with only
   the logged change made, so no older text comes in with it.

**The rule for applying a patch:** a field is changed only where its value at `path` is exactly
`before`. For an object (a cross-reference, a definition), only the keys `before` names are
compared and changed. A patch changes only the article's `body`, never its headwords or
inflections. A set phrase's text also sits, as a copy, in every article that prints it; a patch
on the set phrase is applied to each copy whose value is `before`.

The copy is made again at every export from the current data. A fix that ordbokene has since
made itself drops out; a fix whose text ordbokene has changed is no longer applied. Neither is
ever guessed again. To make it yourself, from this repository:

```
ORDBOK_DATA_DIR=data python ordpar/corrected_copy.py write --mirror data/bokmalsordboka/bm-articles.jsonl data/bokmalsordboka/corrected
```

### `normalization-patches.jsonl`

The patches made from the log, one per line, in article and path order:
`{"article", "lemma", "kind", "path", "before", "after", "how", "log"}`. `how` is `text` (a
change in a text string) or `reference` (the ids in a cross-reference or a definition); `log` is
the log's line numbers the patch comes from.

### `fixes.jsonl`

Every row of `../review/mirror-corrections.jsonl` and of `normalization-patches.jsonl`, and
every line of the log that made no patch, with what became of it:
`{"source", "line" or "log_lines", "article", "lemma", "kind", "path", "how", "verdict", "why",
"copies"}`. `source` is `mirror-corrections` or `source-normalizations`; `line` and `log_lines`
are line numbers in that file; `copies` lists, for a set phrase, the verdict in each article that
prints it. The verdicts:

| Verdict | Meaning |
|---|---|
| `applied` | The value was `before`; it is now `after`. |
| `upstream` | The value is already `after`: ordbokene has made the fix itself. |
| `stale` | The value is something else, or the field or the article is gone: ordbokene has changed it. |
| `duplicate` | An earlier row already corrects the same field. |
| `malformed` | The row cannot be read as a patch. |
| `not_located` | The log does not explain the whole difference between the corrected file and this copy; `why` says more (for example, that ordbokene's text already carries the fix). |
| `element_added_or_removed` | The fix adds or removes an element, which no path can name. |
| `headword` | The fix is in the headwords or inflections, which the copy does not change. |
| `display_order` | The log row sets the order of an article's spellings, which the site shows but which is not a change to the text. |
| `not_a_text_fix` | The log row records something other than an edit to the text. |
| `no_article`, `no_capture`, `not_in_mirror` | The row names no article, or its article file or its article in this copy is missing. |

Some of our fixes are therefore not in the corrected copy; `fixes.jsonl` lists each one and why.

## Licence and credit

Bokmålsordboka is © Språkrådet (the Language Council of Norway) and the University of Bergen,
published at [ordbokene.no](https://ordbokene.no/) under the
[Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
If you use these files, credit Bokmålsordboka as that licence asks.

The corrected copy is Bokmålsordboka with our fixes in it, under the same licence: credit
Bokmålsordboka, and Ordpar (ordpar.no) for the corrections. `corrected/fixes.jsonl` says what
was changed.
Any mistakes our changes introduce are ours.

Ordpar is an independent project. It is not made, endorsed or checked by Språkrådet, the
University of Bergen or ordbokene.no.
