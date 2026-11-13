# The data

The data the site build reads, so that ordpar.no can be built from this repository (all but
the sound recordings, below). Point the build at this folder with `ORDBOK_DATA_DIR=data`, and put Bokmålsordboka's
articles file back together once before the first build:

```
python ordpar/data_parts.py join data/bokmalsordboka
```

How to run the build itself: [`ordpar/docs/build-site.md`](../ordpar/docs/build-site.md).

## What is here

| Path | What it is |
|---|---|
| `articles.jsonl` | **The library**: Ordpar's translated articles, one row per Bokmålsordboka article, Norwegian and English side by side (below). |
| `articles.jsonl.gate.json` | The example gate's marker for the library (below). |
| `bokmalsordboka/` | Bokmålsordboka's own data, every article, as the University of Bergen's API serves it, and beside it a corrected copy with our fixes applied. Its own README: [`bokmalsordboka/README.md`](bokmalsordboka/README.md). |
| `sources/articles/` | One JSON file (`<id>.json`) for each article in the library, for most of the articles its cross-references lead to, and for some more that our translation work fetched: Bokmålsordboka's article, pruned to the fields the translation work reads, with our hand corrections in it. The library's Norwegian is derived from these files. |
| `sources/dangling.json` | Article ids that Bokmålsordboka's own cross-references point to but its API answers 404 for. A reference to one is shown as plain text, not a link. `assessed: true` marks one we have checked and found nothing to fix. |
| `review/source-normalizations.jsonl` | The log of our corrections to the files in `sources/articles/`, one row per edit: `article`, `lemma`, `kind` (`typo`, `ref-anchor`, `lemma-order` and others), `where`, `before`, `after`, `date`, and where they apply `defect` (`theirs` for a fault in Bokmålsordboka's text, `ours` for damage in our copy; older rows have none), `ids`, `resolved_upstream`, `reapplied_from` and `path`. `before` and `after` are often a description, not the exact text. The site reads it for the spelling order in an article's header and for the note at the foot of a corrected article. |
| `review/mirror-corrections.jsonl` | Our corrections to articles that have no library row, as exact patches: `article`, `path` (from the article's `data` to the field, always under `body`), `before`, `after`, with `kind`, `lemma`, `where` and the rendered texts for a reader. The build applies a row only where the article's value at `path` is exactly `before` (`ordpar/sitegen/overlay.py`, [182](../docs/decisions.md#d182)). |
| `review/dangling-def-assessed.jsonl` | Cross-references to a sense that does not exist in the target article, checked by us: `citer`, `target`, `defn`. |
| `frequency/nb-2026-books-nob-1990_freq.frk` | An extract of the National Library of Norway's word counts (below). |

The build writes nothing under `data/`; it writes its output inside `ordpar/`. What does write
here: the join (`bm-articles.jsonl` in `bokmalsordboka/`, and in `bokmalsordboka/corrected/` if you
join the corrected copy), `ordpar/corrected_copy.py write` if you remake the corrected copy
([`bokmalsordboka/README.md`](bokmalsordboka/README.md)), and `gate.write_marker` if you change the
library (below).

## The library, `articles.jsonl`

One JSON object per line, in article id order. Each row is one Bokmålsordboka article: an
ordinary word, or a set phrase (a fixed expression, which Bokmålsordboka keeps as an article of
its own). The rows are the articles we have started to translate, and the articles their
cross-references lead to. The marker file gives the number of rows.

A row has exactly these keys:

| Key | What it holds |
|---|---|
| `id` | Bokmålsordboka's article id. Links between articles are `/nob/bm/<id>`, or `/nob/bm/<id>#def<N>` for one sense. |
| `lemmas` | The headwords: `[{"form", "homograph"}]`, `homograph` a Roman numeral or null. |
| `pos_en` | The part of speech in English, `"fixed expression"` for a set phrase. |
| `headwords` | The header's lines as Bokmålsordboka prints them, one per group of forms: `[{"forms": [{"form", "homograph"}], "pos_en"}]`. |
| `etymology` | `{"no": [segments], "en": [segments] or null}`. |
| `senses` | The senses, in order (below). |
| `exprs` | The ids of the set phrases printed in this article, in order. Their content is in their own rows. |
| `summary` | Optional: the summary gloss, the short list of English equivalents shown under the headword. `gloss` is a list of entries in order of how common each meaning is, one entry per meaning, synonyms inside an entry separated by commas; `gloss_senses`, when present, names for each entry the senses (`defn` ids) it renders. Nothing else is in it here: our own library also holds usage notes for learners on some articles, which are not in this repository, since they have not been reviewed to the standard of the rest. |

A sense has the keys `defn` (Bokmålsordboka's id for the definition, stable when the article
changes), `ordinal` (the number shown), `no` and `en`, `idiom` (an English set phrase, used only
on a set phrase's row), `subs` (the sub-senses, the same shape without `ordinal` and `subs`),
`ex` (the examples), `comp` (lists of compound words) and optionally `ex_added` (below) and `see`
(a set phrase's "Se:" line).

- **Norwegian and English are parallel.** `no` is a list of text segments derived from
  Bokmålsordboka; `en` is the same number of segments in English, or `null` where the English is
  not written yet. The site shows an article in English only when all its English is written;
  otherwise it shows the Norwegian article.
- **Examples** in `ex` are `[norwegian, english]` pairs, or triples
  `[norwegian, english, explanation]` where Bokmålsordboka explains an example. The English may be
  `null`.
- **Markers in the text.** Text segments hold no HTML. `{word}` marks a word mentioned rather
  than used (shown in italics). A cross-reference is a Markdown link to the target article,
  with `#def<N>` for one sense. In Norwegian text the link shows the target's form, with its
  homograph numeral and sense number where it has them. In English text it shows the English, or,
  wrapped in braces, the Norwegian with the English as its title:

  ```
  [ha (II, 13)](/nob/bm/<id>#def<N>)      Norwegian text
  [qualities](/nob/bm/11749#def2)         English text, English shown
  {[den (II)](/nob/bm/9729 "that")}       English text, Norwegian shown, English as title
  ```

  `scripts/markup.py` reads and checks the notation.

### Added example sentences and the example gate

Where a sense had no example, we have written some of our own. They sit in a sense's or
sub-sense's `ex_added` list, each `{"no", "en", "source", "license", "rank"}`, with `kind`,
`claim` and `claim_check` on the few that state a fact. The site marks each with a small raised
"+", so it is never taken for Bokmålsordboka's.

An added sentence is published only once a native speaker has written or approved it. That rule
runs in our private pipeline, so the library here is already gated: sentences not yet approved
are taken out before it is exported. `articles.jsonl.gate.json` records this: `gate`, the name
of the function in our private pipeline that applied the gate (`triage.publishable`); `rows`, the
number of rows in the library; `held`, the number of added sentences the gate held back; and
`sha256`, the library's SHA-256. The build refuses a library with no marker, or one whose bytes no
longer match it (`ordpar/sitegen/gate.py`). It checks only `gate` and `sha256`; `rows` and `held`
are a record.

If you change the library, write a new marker with `gate.write_marker(library, rows, held)`. From
the repository's root folder, this counts the rows and keeps the old marker's `held`:

```
python -c "
import json
from ordpar.sitegen import gate
lib = 'data/articles.jsonl'
held = json.load(open(gate.marker_path(lib)))['held']
rows = sum(1 for line in open(lib, encoding='utf-8') if line.strip())
print(gate.write_marker(lib, rows, held))
"
```

**Left out of the export:** each added sentence's check records, that is its `verification` block
and the `note` inside its `claim_check`. They are our working notes, which the site never shows.

## The frequency extract

`frequency/nb-2026-books-nob-1990_freq.frk` holds lines of the National Library of Norway's
2026 word counts over Bokmål books published since 1990, one `count form` per line in
ISO-8859-1, in the original file's order and bytes. It keeps only the lines for the forms the
search index looks up, so the index is built as it would be from the whole file. The site uses
the counts to put common words first in search suggestions
([55](../docs/decisions.md#d55)); it publishes only a coarse frequency band per headword. Pass the
file to the index build with `--freq`.

## Not here

- Ordpar's private translation pipeline, the records of how each sentence was checked, and the
  list of approved sentences behind the example gate.
- The audio recordings. Write to [post@ordpar.no](mailto:post@ordpar.no) if you would like them
  as files.

## Licences and credits

The code and the docs in this repository are under the licence in [`LICENSE`](../LICENSE). The
data has its own licences, also listed in [`LICENSE.md`](LICENSE.md):

- **Bokmålsordboka** (in `bokmalsordboka/`, `sources/articles/` and the Norwegian of
  `articles.jsonl`): © Språkrådet (the Language Council of Norway) and the University of Bergen,
  published at [ordbokene.no](https://ordbokene.no/) under the
  [Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
  The inflection tables are built from Norsk ordbank, under the same licence.
- **Ordpar's English** (the English of `articles.jsonl`): written with AI (Claude, by
  Anthropic) under Robin Fauskanger's direction and review. Whatever rights exist in it are given
  on the same terms as the Norwegian, CC BY 4.0: credit the English to Ordpar (ordpar.no), and the
  Norwegian to Bokmålsordboka.
- **Ordpar's added example sentences and corrections** (the `ex_added` sentences, the files in
  `review/`, and our fixes in `sources/articles/` and `bokmalsordboka/corrected/`): offered under
  CC BY 4.0 like the rest of what Ordpar adds, credited to Ordpar (ordpar.no).
- **The word counts** in `frequency/`: N-grams from the National Library of Norway 2026,
  [Språkbanken](https://www.nb.no/sprakbanken/), National Library of Norway
  ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)).

Ordpar is an independent project. It is not made, endorsed or checked by Språkrådet, the
University of Bergen or ordbokene.no. The data is offered as it is, without warranties of any
kind; see the licence's
[disclaimer of warranties (section 5)](https://creativecommons.org/licenses/by/4.0/legalcode.en#s5).
