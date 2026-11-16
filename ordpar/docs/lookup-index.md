# The lookup index and the search shell

This is the reference for `ordpar/build_index.py` and the search code in the browser:
`ordpar/site/lookup.js`, `ordpar/site/shell.js` and `ordpar/site/shell.css`, with
`ordpar/site/personal.js` (history and favourites) and `ordpar/site/settings.js` (the settings
page). It describes the index files, the rule that splits them into shards, the query
algorithms, their sizes, and the pages the build writes.

Everything here runs **on the device**. There is no server and no API: a search reads static
JSON files from the site's own origin and answers in the browser.

The rules it implements are in the decision log, chiefly
[17](../../docs/decisions.md#d17), [18](../../docs/decisions.md#d18),
[19](../../docs/decisions.md#d19), [21a](../../docs/decisions.md#d21),
[24](../../docs/decisions.md#d24), [25](../../docs/decisions.md#d25),
[39](../../docs/decisions.md#d39), [41](../../docs/decisions.md#d41),
[46](../../docs/decisions.md#d46), [55](../../docs/decisions.md#d55),
[56](../../docs/decisions.md#d56), [59](../../docs/decisions.md#d59),
[60](../../docs/decisions.md#d60), [63](../../docs/decisions.md#d63),
[117](../../docs/decisions.md#d117), [143](../../docs/decisions.md#d143),
[144](../../docs/decisions.md#d144), [148](../../docs/decisions.md#d148) and
[152](../../docs/decisions.md#d152). Where the site deliberately differs from ordbokene.no,
the public record of differences, `docs/divergences.md`, has a row for it. What this doc says
ordbokene.no shows or does was seen on its live site in the autumn of 2026; it may have changed
since.

In this doc `<out>` is the site's output folder, the build's `--out` (by default `ordpar/out`).

## Building the index

The index is built **after** the article pages (`ordpar/build_site.py`, see
[build-site.md](build-site.md)). The article build leaves three things this build reads:
`build.json` in `<out>` (the About page's figures; without it this build stops), the snippets
file `build-snippets.json` and the list of article pages for the sitemap,
`sitemap-articles.json`, both in the git-ignored folder `.build` under `ordpar`. After this build, run
the offline packer (`ordpar/build_offline.py`, see [offline-app.md](offline-app.md)). So the
order is fixed: articles, then the index, then the offline bundles.

In the public repository, with the data under `data/`:

```
python ordpar/data_parts.py join data/bokmalsordboka          # once: the articles file from its parts
export ORDBOK_DATA_DIR=data
python ordpar/build_site.py ...                               # the article pages first (build-site.md)
python ordpar/build_index.py --mirror data/bokmalsordboka/bm-articles.jsonl --out ordpar/out \
    --freq data/frequency/nb-2026-books-nob-1990_freq.frk
python ordpar/build_index.py --out ordpar/out --verify        # query an existing index, no rebuild
```

On a machine with its own copies of the data, the paths can come from `local-paths.json`
instead (`ordpar/local_paths.py`; its shape is `ordpar/local-paths.example.json`):
`--mirror "$(python ordpar/local_paths.py mirror)" --freq "$(python ordpar/local_paths.py freq)"`.
A flag on the command line always wins.

| Flag | What it does |
|---|---|
| `--mirror` | the Bokmålsordboka articles file, one raw article per line. Without it, nothing is built and `--verify` queries the existing index |
| `--library` | the library `articles.jsonl` (default: under `ORDBOK_DATA_DIR`, else the repository root) |
| `--out` | the site output folder (default `ordpar/out`); the build writes **only** under it |
| `--freq` | the National Library of Norway's 1-gram counts (books, Bokmål, 1990 on; CC0). Optional: without it every frequency band is 0, the similar words and the suggestions are not ranked by how common a word is, and no form pages are written (§ 9). Only the bands enter the index, never the list |
| `--freq-overrides` | the overrides registry for the bands, default `ordpar/freq-overrides.tsv` (§ 4 (3)); read only with `--freq`; a malformed line stops the build with its line number |
| `--form-overrides` | the exceptions to the order of an inflected form's articles, default `ordpar/form-order-overrides.tsv` (§ 3); read with or without `--freq`; a malformed line stops the build |
| `--freq-shared own\|each` | how a form shared by several articles counts towards their frequency (§ 4 (3)); `own` is the default |
| `--snippets PATH` | the snippets file (default: `build-snippets.json` in the folder `.build` under `ordpar`). Give both builds the same path. Without the file the build warns and writes the `snip/` files empty |
| `--snippet-max N` | the English snippets' cut, default 80 characters; 0 = uncut (a Norwegian snippet is always whole) |
| `--limit N` | read only the first N articles: a quick partial build for a smoke test |
| `--verify`, `--query Q` | answer the standard test queries (and any extra `--query`) against the built index |
| `--time-similar N` | time the similar-headwords pass over N random headwords |

The frequency file is the 1-gram list for books from "N-grams from the National Library of Norway
2026", as `count form`
lines in ISO-8859-1. The public repository carries the counts only for the forms the index asks
for; the full list is 386 MB.

`<out>/index/` is a build artefact: the build clears the folder and writes it whole on every run.
It does **not** write `<out>/site/`: the article build copies `ordpar/site/` there, and both builds
reference those copies (`/site/lookup.js`, `/site/shell.js`, `/site/shell.css`,
`/site/strings/en.json`, `/site/inflection.js`, and the article build's generated
`/site/article.css` and `/site/article.js`, whose `?v=` hash this build reads from `<out>/site/`).
After editing a file in `ordpar/site/`, re-run the article build.

## 1. What is written

Paths under `<out>/index/` unless shown otherwise. Sizes are in § 5.

| File | What it holds |
|---|---|
| `<shard>.json` | the search index proper: one shard per first letter of the bare form (§ 2), except the five big letters `b f k s t`, which are split again by the second character (`s-k.json`, `s-oe.json`, `s-misc.json`, …). 135 files |
| `<letter>-top.json` | for each split letter, its first headwords in the suggestions' order: what a ONE-character prefix reads (§ 4 (2)) |
| `headwords/<letter>.json` | every distinct headword form of one letter key, sorted, with its frequency band and what its row needs after a miss (article count, translated, word class): the similar-headwords pass (§ 4 (3)). 30 files |
| `tails/<k2>-<k3>.json` | every headword again, filed by the keys of its 2nd and 3rd bare characters (`hus` in `u-s.json`, `i` in `misc-misc.json`): the similar words past the first letter. 585 files |
| `snip/<k1>-<k2>-<k3>.json` | the one-line snippets, filed by the keys of a headword's first three bare characters (`hus` in `h-u-s.json`, `en` in `e-n-misc.json`, *ta seg i akt* in `t-a-misc.json`), with the maps `"_d"`, `"_g"`, `"_h"` and `"_n"` (§ 3). One file for **every** key a headword has, `{}` where none of its articles has a snippet |
| `en/<letter>.json` | the English search's index: one file per first letter of the English key, `a`–`z` and `misc` (§ 3b) |
| `en/tails/<k2>-<k3>.json` | the one-word English keys again, filed by their 2nd and 3rd characters, for the similar English words (§ 3b) |
| `translated.json` | the sorted ids of the translated articles: what puts the translated first, colours a translated word and tags an untranslated row *Norwegian only* (§ 6) |
| `random.json` | Random word's pool: the headwords whose search shows first an article that is translated, not a set phrase, and has a summary gloss (§ 3) |
| `random-en.json` | Random word in English: `{"v":1,"n":{letter: count}}`, each `en/<letter>.json` file's number of own-letter keys the suggestions can offer. `lookup.js` `randomEnglish` draws one number below the total, which picks the file by its count and the word inside it, so every word is equally likely (`build_index.py` `english_pool`, `english_random`) |
| `labels.json` | the inflected-form labels: `{code: "plural indefinite", …}`, one character per label, and `"_nb"`, the same labels in Norwegian (§ 3) |
| `index.json` | the manifest: counts, every file's raw and gzip size, the frequency settings, the form order's method and exceptions, the English index's figures, the word pages' and the sitemap's counts |

Pages and other files the build writes:

| File | What it is |
|---|---|
| `<out>/bm-en/index.html` | the search page (`ordpar/site/search.html`, the strings inlined) |
| `<out>/404.html` | the same shell, for the host's 404 handler (`ordpar/site/404.html`; § 6) |
| `<out>/favourites/index.html`, `<out>/history/index.html` | the favourites and history pages (`ordpar/site/favourites.html`, `ordpar/site/history.html`): static shells drawn from the browser's storage (§ 6) |
| `<out>/settings/index.html` | the settings page (`ordpar/site/settings.html`, the strings and colour schemes inlined), drawn by `settings.js` (§ 7) |
| `<out>/index.html` | the front page, the search shell. Written only over a page that carries this build's own marker (`<!-- ordpar: placeholder front page, written by build_index.py -->`) or the article build's prototype marker (`<!-- ordpar: prototype front page, written by build_site.py -->`); a file with neither marker is never overwritten. The app's `start_url` is `/`, so this is the page an installed copy opens |
| `<out>/bm-en/<word>/index.html` | a **word page** or **form page** (§ 9), its folder named by the search's fold in NFC (`på kryss og tvers/`) |
| `<out>/sitemap.xml` | rewritten here: the article build writes it first, and this build replaces it with the word pages, the form pages and the article pages that are still their own canonical (§ 9) |

**Which articles search covers** (decisions [46](../../docs/decisions.md#d46);
`build_index.py` `search_scope` over `ordpar/sitegen/mirror.py` `Listing`, the same rule the
article build applies, see [build-site.md](build-site.md)). Every index file is built from
ordbokene's **listed** articles (`bm-listed.jsonl`) plus the **kept** unlisted ones: an unlisted
article (`bm-unlisted.json`) that is translated, unless a listed article sharing one of its
headword strings is translated too. Every other unlisted article is left out of search, as
ordbokene leaves it out of its own search. Its page stays, reachable by a link.

A kept article that ordbokene no longer serves is not in the articles file. Its index entry
comes from the mirror's stored copy (`bm/404/<id>.json`), else from the copy its first parent
embeds as a `sub_article` (raw lemmas, so its alternation notation is expanded like any other;
its embedded `word_class` can read `"false"`, so the word class then comes from the library row,
where a fixed expression is `EXPR`), else from the library row's forms. Library rows for fixed
expressions the mirror has never carried, listed or unlisted, have no page and are not in
search. The manifest's `counts` records all of this under `unlisted46_*`.

## 2. The shard rule

A **form** is a `lemmas[].lemma` of a mirror article (a *headword* form) or a non-null
`paradigm_info[].inflection[].word_form` (an *inflected* form). A form maps to the article's id.
Empty cells (`word_form: null`) are skipped.

**Folding** is NFC then `lower()` in Python, `.normalize('NFC').toLowerCase()` in JavaScript.
It is `lower()`, not `casefold()`, so that the builder and the browser always agree on which
file to open. The **bare** form (`bare` in both files) is the folded form with each accented
letter replaced by its letter, one character for one: a character is replaced when it
decomposes (NFD) into an ASCII letter followed only by combining marks U+0300–U+036F.
**`æ`, `ø` and `å` are never replaced**: they are letters of Norwegian, not accented letters
(`å` decomposes, so it is excluded by name).

The accented letters that occur in Bokmålsordboka's headwords and inflected forms, and what they
fold to: `à ä` → a, `ç` → c, `è é ê` → e, `î` → i, `ò ô` → o, `ü` → u (*à la carte*, *salongfähig*,
*curaçao*, *crème fraîche*, *kafé*, *crêpe*, *òg*, *entrecôte*, *gründer*). `é` is by far the
most common (about 250 headwords). The other non-ASCII characters in forms, `–`, `’` and `…`,
are not letters and never fold.

**The shard key is the first character of the bare form:**

| First bare character | Shard file |
|---|---|
| `a`–`z` (so `à`, `é`, `ò` too) | `a.json` … `z.json` |
| `æ` / `ø` / `å` | `ae.json` / `oe.json` / `aa.json` |
| anything else: digits, `-`, `…` | `misc.json` |

That gives 30 letter keys. `misc.json` holds affixes (`-aktig`, `-arki`), digits and the
expressions that begin with `…`.

**The five big letters are split again.** For `b`, `f`, `k`, `s` and `t` (`SPLIT_LETTERS` in
`build_index.py`, `SPLIT` in `lookup.js`) the shard key is `<letter>-<second>`, where `<second>`
is the second bare character by the same table: `s-a` … `s-z`, `s-ae` / `s-oe` / `s-aa`, and
`s-misc` for anything else **or no second character at all** (the one-letter word *s* lives in
`s-misc.json`). The hyphen keeps these keys apart from the single-letter ones (`aa` is *å*, never
*a* + *a*). That makes 110 sub-shards. A two-letter pair with no forms has no file, and a missing
file reads as an empty shard. `h` is now the largest unsplit shard; splitting it too would be one
more entry in each of the two lists.

**Which file a query reads:**

| Operation | File |
|---|---|
| lookup | `shard_key(q)`: `h.json`, `s-k.json` |
| suggestions, prefix of 2+ characters | `shard_key(prefix)`: a prefix and its continuations share their first two characters |
| suggestions, ONE character of a split letter | `<letter>-top.json` (`suggest_key`), not the 27 sub-shards |
| similar headwords | `headwords/<letter_key(q)>.json`, the whole first-letter bucket (an edit can change the second character), plus the files of § 4 (3) |

`letter_key` (`letterKey`), `shard_key` (`shardKey`) and `suggest_key` (`suggestKey`) must stay
in step between `build_index.py` and `lookup.js`. `ordpar/tests/test_ordpar_index39.py` pins
them and checks the JavaScript against its Python twin when `bun` or `node` is on the PATH.

**Forms are stored as they are spelled and folded at query time**
(decisions [25](../../docs/decisions.md#d25)). The distinctions *PR* / *pr* and *Be* / *be*
are real, and only 0.19 % of forms collide when folded. The lookup folds both sides: on load each
shard gets a bare → original map, so a query for `Be` answers with both `Be` (symbol) and `be`
(verb), each as its own group.

**Accents match one way**, as on ordbokene.no (decisions [41](../../docs/decisions.md#d41)
(a)). A query matches a form when their bare forms agree and, position by position, each
character of the folded query equals the form's or is that character's bare letter
(`accent_match` / `accentMatch`). So *en* matches *én*, but *én* does not match *en*; *a la carte*
matches *à la carte*, but not the reverse. The display keeps the accents.

## 3. The shard format

```json
{"k":"h",
 "heads":{"hus":[24627],"huse":[24650]},
 "forms":{"husene":[24627],"husa":[24627]},
 "words":{"24627":["hus",0,"NOUN"],"24650":["huse",0,"VERB"]}}
```

* `heads`: form → sorted ids of the articles that form is **the headword of** (all homographs).
* `forms`: form → ids of the articles that form is **an inflected form of**, leaving out the
  article's own headword forms. A hit here fills the inflected-form rows. A string can be in both
  maps (*trøtte* is a headword verb *and* an inflected adjective); the two maps are disjoint per
  article, never per form.
* `words`: id → `[display, hg, pos]` for **every id the shard mentions**, so the rows need no
  second request.

**The order of a form's articles in `forms`** (decisions [143](../../docs/decisions.md#d143))
is the order the rows show them: the most common word first. The method, **E2**: each
case-folded spelling's count in the frequency list is shared out among **every** article that has
it, as a headword or an inflected form, in proportion to each article's number of example
sentences + 1 (read from the mirror's `body.definitions`; expressions embedded as `sub_article`
not counted; an article missing from the mirror is read from its stored copy). An article's
figure is the sum of its shares, rounded (`build_index.form_share`, `article_examples`). None of
the frequency fixes of § 4 (3) applies here. **The figures order words, not articles**: the
articles are grouped by their word (`form_word`, the first spelling of the headword line, so
*en, én* II and *en* III are one word), a word's figure is the sum of its articles', and within a
word, as in a tie between words, `result_order` decides (`build_index.form_order`). For *varer*:
*vare* III, IV, I, then *var* I; for *bomber*: the translated noun *bombe* I before the
untranslated verb II.

Then the **exceptions file**, `ordpar/form-order-overrides.tsv` (`read_form_overrides`): a header
`form<TAB>first<TAB>why`, then one line per form as spelled, the id or comma-separated ids that go
first, in that order, and the reason. Each id's whole word leads the form's rows, in its own order
(within one word the list view's order wins), and the rest keep E2's order. An exception never
puts one homograph above another of the same word. The manifest's `form_order` names the method,
the file, its entry count, and any line that names no inflected form with two or more articles or
an id not among them (`unmatched`); a full build refuses such a line. Without `--freq` the order is
`result_order` alone, then the exceptions. Every reader keeps the stored order.

**`display`** is the article's lemma forms joined by ` / `, at most three, then `…`, in the
mirror's order, or in the project's own order where the normalization log sets a header's lemma
order (`build_index.entry` reads the lemmas through `ordpar/sitegen/lemma_order.py`, as the
article's headword line does: *tørre / tore*, *gæren / galen*). The ` / ` is a **data separator,
never shown** (`build_index.SEP`): every reader draws the spellings with ", " between them, each
with its own numeral (`lookup.js` `headParts`, `headwordInto`). It stays in the data because 48
headwords contain ", " (*snipp, snapp, snute*) and none contains " / ", and because history and
favourites already stored in readers' browsers carry it.

**`hg`** is the homograph number (`0` = none), **per spelling**: one integer where every shown
spelling has the same number, else a list of one per shown spelling (*lysing, lysning* `[1,2]`;
*avrustning, avrusting* `[0,2]`; `build_index.hg_field`). A search numbers and orders an article
by the spelling it matched (`form_hg` / `formHg`; a spelling not among the three shown takes the
first non-zero number): *lysning* lists *lysning* I before *lysing* I, *lysning* II, as
ordbokene's results do. **`pos`** is the first paradigm tag as the mirror spells it (`NOUN`,
`VERB`, `ADJ`, `EXPR`, `ADP`, `SYM`, …), shown through the strings' key `pos.<TAG>`.

The `words` table is a deliberate extension of decision 25's "form → article ids only": it is
**per article, not per form**, carries no grammatical tag of the form, and is what lets the rows
name their headwords without a second request. It costs about 30 % of the shards' gzip bytes.
An id repeats across shards only when an article's inflected forms start with another letter
(*bok* in `b-o`, *bøker* in `b-oe`), for about 1 % of articles.

**Alternation notation is expanded** (decisions [39](../../docs/decisions.md#d39)). About 325
expression headwords are written in ordbokene's notation: `[få|sette] ræva i gir`,
`en [ond|vond] sirkel`, `blande seg [bort i|borti]`. The build stores each as its **variants**
(`variants()` in `build_index.py`): each bracketed group is one of its `|`-separated alternatives,
every combination where there are several groups, in source order. Two rarer spellings of the
notation are read the same way: a `/` inside the brackets (`pipa får en annen [låt/lyd]`) and a
`|` between whole bracketed alternatives (`[i alt vesentlig] | [i det vesentlige]`). The bracket
notation is never a key in `heads`, never in a headwords file, and never shown:

* every variant is its own `heads` key, pointing at the same article id (where a variant is also
  another article's headword, *poppe opp*, *tur-retur*, the key lists both ids);
* the article's `words` entry carries a fourth element `1` (`["få ræva i gir",0,"EXPR",1]`), and
  its `display` is built from the **first** variant, which is what a row shows where nothing was
  typed to match against;
* in a **headword** group, an article flagged `1` is shown as **the variant that matched**: a
  search for *sette ræva i gir* lists "sette ræva i gir", not "få ræva i gir".

Not expanded: a bare `/` (`km/h`, `c/o`, `m/s`, `av/på-knapp`, and the one expression
`ha en trumf i ermet/bakhånd`, whose slash is not bracketed and so cannot be told apart from
`km/h`), and `...` placeholders (`... og ... , fru Blom`). No headword contains parentheses.
Inflected forms carry no notation.

**`<letter>-top.json`** has the shard format with `forms` and `words` empty. Its `heads` holds the
letter's first 50 headwords in the suggestions' ranked order (§ 4 (2)) for the letter typed in
lower case and in capitals (the union, so up to 100), each with its full id list.

**`n`**, in a shard and a `-top` file: the frequency band of each headword (`headword_bands`, the
highest band of the articles the form heads, § 4 (3)), as ONE HEX DIGIT PER HEADWORD, aligned with
the file's headwords sorted (`shard_bands`; `lookup.js` sorts the same keys the same way). Omitted
when every band is 0 (a build without `--freq`). A `{headword: band}` map would be 5.3 times the
bytes.

**`p`, `pf` and `t`** (decisions [117](../../docs/decisions.md#d117)), written by
`write_index` from the page plan (§ 9) and the mirror's cell tags:

* `p`: one digit per headword, aligned with the headwords sorted (as `n`): `1` where that
  headword's search has a word page. Omitted where none has.
* `pf`: the inflected forms (as stored) whose search has a form page.
* `t`: one character per (form, article) pair, the forms sorted and each form's ids in their
  stored order: the code of the pair's form label in `labels.json` ("A" `plural indefinite`; "-"
  for an analysis with no label).

The shard and the similar-words files are the browser's ONLY source for "does this search have a
page": `lookup.js` never works it out itself (`pageFor`, `similar`).

### The snippet files, `snip/`

`snip/<key>.json` is `{"<id>": "one line"}`: `{"24627":"a house; a building", "24650":"gi husly til", …}`.
The key is `snippet_key` (`snipKey` in `lookup.js`): the `char_key` of the 1st, 2nd and 3rd bare
characters joined by `-`, `misc` for a missing one. A query and every headword it can match share
the key (the key is of the bare form, and an accent match needs equal bare forms). A file holds
every article that has a HEADWORD under its key; an article that is only an inflected form there
is not in it (*hus* is an inflected form of *ha*; *ha*'s snippet is in `h-a-misc`). Every key that
has a headword has its file, `{}` where none of its articles has a snippet, so a headword hit can
ask for its file without first checking that it exists.

**The snippet** (`ordpar/sitegen/article.py` `snippet`): a translated article's summary gloss, its
items joined by ` · ` (`markup.HEADLINE_SEP`, as in the article head), else its first sense's
English; an untranslated article's first sense's Norwegian. Markers are reduced to the words a
reader sees, and **on a Norwegian line each cross-reference's homograph numeral and sense number
are dropped**: `article.drop_ref_numbers` takes the ` (III)`, ` (1)` or ` (II, 2)` off the end of
a link marker's label before the markers are reduced, so *evne til å huske (III)* becomes *evne
til å huske*, while a parenthesis of the definition's own words stays (*dag nummer to (2) i en
høytid*). The article page keeps the numbers. An English snippet is cut by `snippet_text` to at
most 80 characters (`SNIPPET_MAX`) at the last space past half the limit, trailing punctuation
and a dangling ` ·` dropped, with `…`; a Norwegian one is kept whole, since the hover over a link
can show it ([185](../../docs/decisions.md#d185)) and the rows cut every line to their width
anyway. The longest Norwegian first definition is 273 characters; keeping them whole adds about
0.13 MB to the `snip/` files (measured 12 November 2026). The browser marks it `lang="en"` when the article is translated,
else `nb`; the build counts snippets whose language would be marked wrong
(`snippet_lang_mismatch`, expected 0). An article with no sense line (only set phrases, or only
an etymology: *ditt*, *disfavør*) has no snippet, as ordbokene's row shows none. Every row that
shows a one-line definition reads this snippet: the list view, the suggestions, Recent and
History, favourites, the similar rows, a word page's built rows and a page's `data-snip`.

The article build writes the snippets to `build-snippets.json` as
`{"<id>": [text, lang, drop|null, 0|1, nb]}`: the last three elements only where needed.
`read_snippets` accepts two to five elements. Beside the snippets, each `snip/` file carries:

* **`"_d"`**: `{"<id>": text}` for every TRANSLATED set phrase (`pos_en` "fixed expression")
  with no summary gloss: its first authored set-phrase box (`idiom`, the first non-null in sense
  order, a sense before its subsenses; `article.dropdown_text`), cut as the snippet, or `""` where
  it has none. Only the suggestions and the history and favourites rows read it, in place of the
  snippet's first unit. A `""` is read as no box, so such a set phrase shows the snippet's first
  unit like any other article (`shell.js` `glossText`, `lookup.js` `dropRule`, `personal.js`
  `dropText`; a page's `data-drop=""` is read the same way). Example, `f-y-misc.json`:
  `{"112657": "used to express admiration, disgust or some other reaction", …, "_d": {"112657": "bloody hell", …}}`.
* **`"_g"`**: the ids, as integers, of the file's translated articles whose snippet is the summary
  gloss (`article.snippet_is_gloss`); absent where there is none. Rows that show a snippet or its
  first unit set those in semibold and fade their ` · ` (`lookup.js` `isGloss` / `writeGloss`;
  `shell.js` `glossIs`, which also leaves a `"_d"` box regular). An English definition line, a
  Norwegian one and a set-phrase box stay at weight 400. A file without `"_g"` marks none.
* **`"_h"`**: `{form: ids}` for every headword under the file's key with at least one snippet in
  the file: the articles the form heads, in the results' order (`result_order`, translated
  first); a single id as an integer, several as `[[id, hg], …]` with the spelling's homograph
  number (`form_hg`): `"husk": [[24680, 1], [24681, 2]]`, `"hus": 24627`. A similar word's row
  reads its articles' snippets from this one file (`shell.js` `similarArticles`), with
  `translated.json`. A form with no `"_h"` entry is drawn as History draws a row with nothing on
  hand ("Norwegian only", "N articles").
* **`"_n"`** (decisions [152](../../docs/decisions.md#d152)): `{"<id>": text}` for every
  TRANSLATED article of the file, its first sense's (else first subsense's) Norwegian line, made
  as an untranslated article's snippet is (`article.snippet_nb`), kept whole; `""`
  where it has none. It is what the rows and the hovers show under *Norwegian only* with the
  English equivalents hidden (see [build-site.md](build-site.md), Norwegian only). Every file that
  holds an article carries `"_n"`, `{}` where none of its articles is translated, so a reader can
  tell a file built without it: there it gives no Norwegian definition for any article
  (`lookup.js` `nbDef`), never a translated article's English in its place. The rows read a file
  through `lookup.js` `rowView`; what is STORED (a History entry's text) always reads the file
  itself.

Readers that do not know a field ignore it, so an older cached or offline file still draws.

**The hovers read the same files.** Each leading link on an article page carries its target's
file key (`data-s="h-u-s"` on the `<a class="ordbok-xword">`; `face._link`,
`build_site.Builder.snip_key`: the `snippet_key` of the target's first headword), and `mini.js`
`nbPeek` reads `nbDef` from that file on the first hover. Of the ways measured, this one costs the
offline download least (§ 5). An English partner word carries no key; it takes the Norwegian link's
in its pair. Under `minifetch` = `click` the hover fetches no file: it reads one only if the page
already has it (`lookup.js` `loadedSnippets`).

### The similar-words files, `headwords/` and `tails/`

`headwords/<letter>.json` and `tails/<key>.json` are `{"w": [sorted forms], "f": "<one hex digit
per form>"}`, the digit the form's frequency band, 0–15 (§ 4 (3)): `{"w":["hus","husk"],"f":"b9"}`.
Both readers also accept a plain sorted array of strings (every band 0). Aligned with `w`, they
also carry:

* `p`: the forms whose search has a word page (as in a shard), for the similar headwords' links;
* `a`: one hex digit per form, the number of articles the form heads (as a suggestion row counts
  them), at most `f`;
* `x`: one digit per form, `1` where any of them is translated;
* `k` and `kc`: one character per form, the word class of a one-article form as its place in the
  file's own sorted list `kc` (`ROW_CODES`: `0`–`9`, `a`–`z`, `A`–`Z`), `.` for several articles
  or no tag. In the `h` headwords file, *hus* and *hus under hver busk* read `"a":"…11…"`,
  `"x":"…11…"`, `"k":"…97…"` with `"kc":["ABBR","ADJ",…,"EXPR",…,"NOUN",…]`.

These let a similar word's row be drawn with no shard loaded (`build_index.row_fields`,
`similar_file`). A `headwords/` file without `a` makes `lookup.js` draw the row from the word's
own search instead.

### `translated.json`, `random.json`, `labels.json`

**`translated.json`** is a sorted array of the ids for which `coverage.complete_strict(row)`
holds (`scripts/coverage.py`, decision [27](../../docs/decisions.md#d27)'s translated gate),
within the articles search covers (§ 1). Today every library row passes the gate, so "in the
library" and "translated" coincide; the flag is still carried per id because rows that do not
pass can land.

**`random.json`** is Random word's pool (decisions [115](../../docs/decisions.md#d115)): the
sorted HEADWORDS whose search shows first an article that meets the bar of decisions
[67](../../docs/decisions.md#d67) (`build_index.random_headwords`). The bar
(`build_index.random_pool`): the article is translated, is **not a set phrase** (its part of
speech in the index is `EXPR`; for a kept article whose entry carries no tag, its library row's
`pos_en` is `fixed expression`), **and** its library row has a non-empty `summary.gloss`. Each
headword of an article meeting the bar is searched through `Index` (the Python twin of
`lookup.js`) over the index just written, and kept when `first_shown` (the first article of the
results as `render` draws them: `lookup.js` `shownOrder` / `firstShown`, the headword groups in
turn, translated before untranslated) meets it. Spellings that fold to one search are one entry
(*Mars* / *mars*). The other articles of that search may be untranslated or unglossed. The
manifest's `random` carries `count` (headwords) and `articles` (the bar's). Offline, the file
travels in the `index-meta` pack with `index.json` and `translated.json`
([offline-app.md](offline-app.md)).

**`labels.json`**: the words of the inflected-form labels, `{code: "plural indefinite", …}`, the
codes each shard's `t` carries, and `"_nb"`, the same codes in Norwegian
(`FormLabels.table_nb`: the inflection tables' Norwegian words, `inflection.js` `NB_STRINGS`):
`{"A": "ubestemt form flertall", …}`. A number's definiteness reads in the Norwegian order:
definiteness, "form", then number. `lookup.js` reads `"_nb"` for a row's label under Norwegian
only or the labels setting (`labelNb`); a built row carries both copies
(`wordpages.form_label_html`). Ordbokene's rows show no such label.

## 3b. The English search's files

This is the format for `en/<letter>.json` (`build_index.py` `english_index`, `english_files`,
`write_english`; read by `lookup.js` `loadEnglish`), behind the switch under the search box that
makes the search look for English equivalents instead of Norwegian headwords
(decisions [148](../../docs/decisions.md#d148)).

**What is indexed.** The library rows that carry `summary.gloss`, are translated and are in search
(`translated`, `words`). Each gloss unit is cut at "," and ";" outside ( ), [ ] and { }
(`en_split_unit`). Each piece is an **equivalent** with a **key** (`en_key_of`, `en_norm`): lower
case, bracketed text dropped, a `{…}` mention dropped with its contents, punctuation at the edges
trimmed, and one leading "to ", "a ", "an " or "the " dropped. A piece that is all brackets is an
**explanation** ("(particle used only in exclamations …)") and is not indexed; a piece that is
only a mention gives no key. A unit is drawn as the site draws a gloss
(`sitegen.article._plain`), and each equivalent keeps its span in that text: what the list view
marks bold.

**One file per first letter of the key** (`en_letter`: the first character of `bare(key)`, a–z,
else `misc`), so a search, its suggestions and an English History row each read ONE file. A file
holds every key of its letter and, besides them, every key of two or more words (spaces, hyphens)
with a word of its letter ("go swimming" in `g` and `s`, for the similar words' phrase rule), and
the keys of an irregular verb pair or a spelling pair whose halves start with different letters
(*went* / *go*, in both files). Fields (`dump`: compact, keys sorted):

| Field | What |
|---|---|
| `v`, `k` | the format version (1) and the letter |
| `e` | `{key: [[id, unit, place, start, end], …]}`: every equivalent with that key: the article, the unit's number in the gloss (1, 2, …), the place in the unit (1, 2, …), its span in the unit's drawn text |
| `a` | `{id: [headword text, hg, pos, band, rank, units]}`: each article the file names, once: the shard's `words[id]` text and numbers (§ 3), its word class, its **band** (the highest band among the spellings it shows), its **rank** (its place in `en_rank`'s order over every indexed article: the first spelling's length, folded, as spelled, then `homograph_order`, then the id), and its gloss's units as drawn |
| `d` | `{key: display}`: a key's display where every occurrence is written otherwise (*AIDS*, *House of Lords*) |
| `sp` | `{american: british}`: the spelling map's entries of this letter (`en_spelling_map`: the glosses' -ise/-isation/-our words with their inflections, and the named pairs `EN_PAIRS`), applied to a query word by word. The glosses hold no American spelling, so it runs one way. Words ending in *-anise*, *-mise*, *-rise*, *-arise* are not blocked by it (`EN_ISE_WHOLE`) |
| `ir` | `{form: base}`: the irregular verb forms (`EN_IRREGULAR`) of this letter or of a base of this letter, for the similar words' stem rule |
| `c`, `p` | the number of articles indexed, and their share of the dictionary (the About page's article count, `site_stats` `articles.all`) as a whole percent: the figures in the line shown when nothing is found |

The manifest carries `english`: the counts, `spelling_map`, `irregular_forms`, every file's keys,
articles, raw and gzip size, the totals and the largest.

**The search** (`lookup.js` `englishLookup`; Python twin `EnglishIndex.matches`): the query
normalised as a key, with its British form where the map changes it; **exact equivalents only**;
each article once, at its best place, with every matched span; in **order (c)** (`enOrder`): the
equivalents in the gloss's units 1 and 2 as one tier, then those in unit 3 and later; within a
tier the band, highest first; then the earlier unit, the place in the unit, the rank. *go*: *gå*
(unit 2, band 12), *dra*, *fare* II, *kjøre*, *fart*, *lyde*, *ryke*.

**The suggestions** (`englishSuggest`, twin `EnglishIndex.suggest`): one item per key continuing
what was typed: the exact word (rank 0), the one-word continuations by the top band of their
Norwegian words (1), then the phrases (2) by length, then the key; up to 20. Each item's articles
in order (c).

**The similar English words** (`englishSimilar`, twin `EnglishIndex.similar`): five, for a query
of three letters or more. First the word matches, from the query's own file: a key of two or more
words holding the query as a whole word, and a one-word key sharing a stem with it (`enStems`,
`build_index.en_stems`: *-ing*, *-ed*, *-es*, *-s* cut, with and without a final *e*, a doubled
consonant undone, *-ies*/*-ied* to *-y*, and the irregular base from `ir`). Then the one-word keys
spelled alike, within `letterLimit` edits (`distance`, as in the Norwegian search): those of the
query's letter, from its own file, and those **past the first letter**, as the Norwegian
`similar` reaches them (§ 4 (3)): a **wrong** first letter from the English tails file of the
query without its first character (`en/tails/<remainder_key(b[1:])>`: *hoose* → *loose* in
`o-o`), a **missing** one from the query's own (`en/tails/<remainder_key(b)>`: *hoose* → *choose*
in `h-o`), an **extra** one from the second letter's English file, its one-word keys starting
with that letter (`en/<en_letter(b[1:])>`: *xhouse* → *house*), where `b` is the bare query.
Ranked: word match first, then distance, top band, length, key. The searched word itself, and a
key whose articles are all on the page already (decisions [149](../../docs/decisions.md#d149)),
are left out. The page asks for them after the results are painted (`renderEnglish`), so the
results keep their one request; on a cold miss the similar words add at most three files.

**The English tails files** (`build_index.english_tails`, `en_tail_key`; read by `lookup.js`
`loadEnglishTails`): every one-word key (no space, no hyphen) again, filed by the keys of its
second and third bare characters (`tail_key`, the Norwegian `tails/` rule: *house* `o-u`, *loose*
`o-o`, *choose* `h-o`). Each file carries only what a similar row needs, so a row needs no other
letter's file: `v`, `t` (its key), `e` `{key: [[id, unit, place], …]}` (for order (c) of the
row's headwords and for rule 149; no spans), `a` `{id: [first spelling, its numeral, pos, band,
rank]}` (a row draws the first spelling alone; no gloss units), and `d`, the keys' display. The
manifest's `english.tails` carries each file's figures. Tails files with the keys alone would be a
third of the size, but a miss whose rows come from other letters would then load one whole letter
file per letter, so the rows' data ships in the tails files.

## 4. The query algorithms (`lookup.js`)

The query functions are pure functions over the loaded files. `ordparLookup` has no DOM
dependency and takes an injectable loader (`setLoader`), which is how the build tests it.
`build_index.py`'s `Index` is the Python twin of the same algorithms.

### (1) Lookup

`lookup(q)` folds the query, loads its shard (and `translated.json`) and returns
`{heads: [{form, articles}], forms: [{form, articles}], count}`.

A form found only through accent folding (*én* for *en*, *gründer* for *grunder*) is its own
group, but **an article is listed once**: such a group keeps only the articles that no exact group
(and no accent group before it) lists, and is dropped if none is left (`dedupe_accent_groups`).
So *en* lists *en / én* once, under "en"; *kafe* lists *kafé / kafe* once; *grunder* lists
*gründer* beside "is an inflected form of *grunde*".

**The order within a group** is ordbokene's: **the verbs first, in homograph-number order, then
every other article in number order, whatever its word class**: *fange* III (verb), I, II;
*stille* IV, V (verbs), I, II, III; *fly* V (verb), I–IV. An unnumbered article keeps its place
before the numbered ones; the id breaks a tie (`homographOrder`, `build_index.py`
`homograph_order`). A verb is told by the index's own word class, the article's first paradigm
tag (`VERB`; `words` in § 3).

**Translated first**, a deliberate difference from ordbokene: before that order, the translated
articles come first and the untranslated after, each part in the order above (`resultOrder`,
`result_order`): *fly* V (verb) and III, the translated, then I, II, IV. This holds in both views,
but **not in the inflected-form rows**: there the most common word comes first, translated or
not, by the stored order of § 3 (`forms`), and `result_order` orders the homographs of one word
and breaks a tie between words.

How the results are drawn (full articles, the list view, the inflected-form rows) is § 6.

**The grammatical description of the form itself is not looked up here.** The index carries no
per-form grammatical tags; the label after the word class on an inflected-form row ("*hus* noun
(plural definite)") comes from the shard's `t` codes and `labels.json` (§ 3, § 9).

### (2) Suggestions

`suggest(prefix, limit=20)` gives the headwords that continue the prefix, **within the prefix's
own shard**, ranked as below and cut to 20, each tagged translated or Norwegian only. A prefix
never spans shards: a prefix and its continuations share the first letter, and the first two for a
split letter. A **one-character** prefix on a split letter reads `<letter>-top.json` instead: its
headwords are by construction the first ones the whole letter would give, so the answer is the
same, for `limit` up to 50, at about 0.5 KB gzip instead of 27 sub-shards. Typing *s*, *sk*
therefore loads `s-top.json`, then `s-k.json`. A variant of an expanded expression is a headword
like any other: *få ræ* offers "få ræva i gir". A prefix typed without an accent matches headwords
with one (*en* offers *en*, *én*, …; *a la carte* offers *à la carte*); a prefix typed with one
offers only headwords that have it.

**A trailing space is honoured**, a deliberate difference from ordbokene.no's site (its suggest
API honours it; checked 19 October 2026). Leading spaces are dropped and every run of spaces is one
(`suggestQuery`), but "fy " offers the word itself first (if it is a headword), then the set
phrases beginning "fy ", in their ranked order, then the ordinary continuations of "fy" filling
the rest: *fy*, *fy faen*, *fy flate*, *fy søren*, *fy til katta*, … *fyk*, *fyr* …. The phrases
are read from the shard of "fy " (for a one-letter word on a split letter, `<letter>-misc`, beside
the `-top` file). Submitting a search still trims. `Index.suggest` in `build_index.py` is the same.

**Ranking: translated first, then by frequency**, a deliberate difference from ordbokene, which
ranks by length, then alphabet. Over EVERY match, and only then cut to `limit` (a one-character
prefix on a split letter ranks its `-top` file's headwords, which were chosen in this order), the
ranks are:

0. the exact match (the bare query), whatever its status;
1. the one-word headwords that are translated (a word standing for several articles counts as
   translated if any of them is), **by frequency band, highest first**;
2. the *Norwegian only* ones, by band;
3. the set phrases (a headword with a space), translated or not, in length order: a reader typing
   a word usually wants a headword, the trailing space brings up the phrases, and a phrase has no
   1-gram count;
4. the continuations reached only through the accent fold, last (below).

Inside one band, and in ranks 0, 3 and 4, the tie is broken by length, then capitalisation
(below), then the folded form, then the form as spelled (`rankSuggestions`, `suggest_rank`). The
band is the shard's `n` (§ 3). With a trailing space: the word, then ITS phrases in their order,
then the rest ranked as above. For example, *kjøre* offers kjøre, kjøretøy, kjørebane, kjørefelt,
kjøretime, kjøreskole, …; *hus* offers hus, huske, husholdning, husdyr, husmor, …; *s* offers s,
S, som, si, så, seg, stor, ….

**The continuations reached only through the accent fold come last** (`suggest_order`): a
headword longer than the prefix whose own first letters differ from the typed ones
(`fold(w)[:len(p)] != p`) is ranked after every other match. So *e* never reaches *én*, and
*kafe* lists *kafe*, *kafé*, *kafeliv* … *kafeteriadisk*, then *kaféliv* …. But a form equal to the
prefix keeps its place (*en* offers *en*, *én*, *ene*: *én* second, as ordbokene), and so does a
continuation whose typed letters match as spelled (*kaf* offers *kafe*, *kafé*, *kaffe*, …
*kafkask*, *kaféliv*). Ordbokene's own suggestions also include matches inside a headword (*brun
kafé*, *i og med*) and hyphen-folded ones (*A-lag*), which ours do not make.

**Capitalisation is a tie-break within one length** (`case_distance` / `caseDistance`). The
prefix AS TYPED is compared with each form as written, position by position over the shorter of
the two; each pair of cased characters whose case differs counts 1. The sort key is
`(later, length, case distance, folded, form)`. So *u* offers *u*, *U*, then *u-*, *ul*, *ur*,
*ut* … before *U-*, *UT*; *U* offers *U*, *u*, *U-*, *UT*, *UV* …; *og* offers *og*, *òg*, *Og*.
Because the order depends on the case typed, each `<letter>-top.json` holds the union of the
first 50 for the letter typed in lower case and in capitals.

**One suggestion per article**, a deliberate difference from ordbokene, which suggests per form
(*dann* there lists *danna* and *dannet*, one article, as two rows with the same gloss). The rows
are built and ranked per form as above; then a row leading to ONE article takes in every later
row leading to that same article (`mergeArticles`, `merge_articles`), in the place of its
best-ranked form, which is what choosing it searches. **A form several articles share keeps its
own "N articles" row and never merges** into an article's row, so the search showing them all
stays on offer; such an article may also keep a row of its own, by a form of its own (*br*: *bro*,
2 articles, and *bru, bro*).

**What a suggestion row shows.** Ordbokene's suggestion list shows the word alone; ours shows
more:

* **On the left**, the word and, when ONE article is under it, its word class in faded italic as in
  the result rows (none for a set phrase). A one-article row shows the article's headword line
  (`words[id][0]`, its forms in the article's order, comma-separated: "dannet, danna"), the forms
  continuing what was typed in bold and the rest regular (`headLine`; an expression stored as
  variants shows the variants that matched; a line cut at three forms ends "…"). It shows no
  numeral.
* **On the right**, for one translated article: the first unit of its summary gloss, else of its
  first English sense, cut by CSS with an ellipsis (`shell.js` `optionSide`, `fillGlosses`). A
  translated set phrase with no summary gloss shows its first set-phrase box instead (the `"_d"`
  map, § 3: *fy faen* "bloody hell", *fy flate* "flipping heck"); one with no box either shows its
  English line, like any other article (`glossText`). For one untranslated article: the *Norwegian
  only* tag, or inside the "Norwegian only" section (below) its Norwegian definition.
* **An "N articles" row** lists its translated articles' glosses in the results' order with their
  homograph numerals, "I it · III the" for *den*, as many as fit, then "+ N more" (`shell.js`
  `glossList`, `listedGlosses`, `fitGlosses`; the string `suggest.more`). An untranslated article,
  or a translated one with no gloss text, is not listed, only counted in the "+ N more". With none
  of its articles translated, the row shows each homograph's numeral and first Norwegian definition
  instead (*husk* "I evne til å huske · II huskende, gyngende bevegelse"), fitted and cut the same
  way. English and Norwegian are never mixed in one row (`sideGlosses`, one rule shared with
  History and the similar rows). Each numeral is the number of the row's own spelling (under
  *lysning*, *lysing, lysning* is II, not its first spelling's I). With nothing to list, the row
  keeps a plain "N articles".

The glosses come from the `snip/` files: the article's line up to the first " · ", from the file
of the word's own key (a headword's key always has its file, § 3), fetched after the dropdown has
painted; the reserved space fills in, and is dropped if the file has no line. Storing the first
unit in the shards instead was measured: it would add about 13 % to the index and 17.8 KB to every
*hus* search, typed or not, where the `snip/` files cost 1.6–3.6 KB and 1–4 requests per prefix,
only while typing, cached afterwards and shared with the list view and the inflected-form rows. The
cost of the choice: the gloss arrives one round trip after the dropdown on a key not yet loaded.

Every homograph numeral in a row (these gloss lists, History, the list view, favourites, the
inflected-form rows) is drawn in **the article's own look**: the span carries the article's class
`.ordbok-homograph` beside `.ordpar-hg`, whose one remaining rule, `line-height: 0`, keeps the
raised numeral from making a row taller. That look is 0.6 of the headword it follows, the muted
grey, weight 600, raised 0.14 em; in the gloss lists 0.8 em of the gloss text.

**A row that overflows gives up its left side in a fixed order.** A row overflows when its right
side cannot show what it must: "Norwegian only" or a count in full, or a gloss at least the smaller
of its own width and 8rem. It then drops, stopping at the first step that fits: (1) the forms not
continuing what was typed, and the "…"; (2) every form but the best-matching one, the one the row
searches; (3) the word class; and last (4) it cuts the word with an ellipsis. A row that fits is
drawn in full. An "N articles" row has no line or word class, so only step 4, and its gloss list
then fits itself in what is left; a "Recent" row takes steps 3–4. Measured in the browser
(`shell.js` `fitRow`, `sideNeed`), always from the full row: once when the dropdown is drawn, a
pending gloss counting as 8rem, and again when its gloss arrives, so a short gloss gives back what
the first fit took.

**All 20 rows, in a list that scrolls**, as on ordbokene.no. The dropdown draws every row
`suggest` returns, up to 20, at 35.2 px a row. The popup's height is its own (`max-height: 60vh`)
or, if less, what is left between its top and the bottom of the **visual** viewport, less 8 px
(`shell.js` `fitHeight`), and never less than three rows. A phone's on-screen keyboard shrinks the
visual viewport but not `vh` (nor `dvh` / `svh`), so this keeps the list above the keyboard,
scrolling inside, instead of running under it. The height is measured after the rows are drawn and
again when the visual viewport is resized with the list open (the keyboard coming up, the phone
turned), keeping the list and the reader's place in it. The arrow keys bring the chosen row into
view. The "Recent" rows (§ 6) take the same cap: `openRecent` calls `fitHeight` once the popup
shows, and the "Recent" heading is inside the measured popup and scrolls with the rows.

**The rows' spacing** is a setting, `suggestrows` (§ 7): `standard` (the default, a 35.2 px row)
or `roomy`, 0.625rem above and below the 24 px line instead of 0.35rem, a 44 px row, on any
device and for the Recent rows too (`html.ordpar-suggestrows-roomy`). 44 px follows Apple's touch
target guidance (Material's is 48 dp; the WCAG 2.2 minimum is 24 px).

**The "Norwegian only" section.** The rows keep their ranked order, and the run of one-word
*Norwegian only* headwords (rank 2, after the translated ones) is drawn under a label box
"Norwegian only": the tag's grey look, its text at the gloss's size and tied to it (`shell.css`
`--ordpar-gloss-size`, one value for the right-hand text and the label), with a thin rule above it
(not where it would open the list) and one after it where rows follow. Each one-article row in it
shows its **first Norwegian definition** on the right (the whole `snip/` line), with no tag, and
nothing where the article has no snippet; the row fit treats it as a gloss. An "N articles" row
whose articles are all untranslated is in the section too and keeps its "N articles". **The exact
match is always first**, and never in the section: a Norwegian-only exact match (*dann*, *ø*,
*Ba*) keeps its tag at the top. **Set phrases stay below the headwords** where the ranking puts
them (rank 3), not grouped, a Norwegian-only one with its tag, **except after a trailing space**:
then the exact match comes first, every translated row next and every untranslated one after,
under the label, each group in its ranked order. **Colours**: a translated row's word is in the
accent (`var(--ordpar-accent)`), an untranslated row's in the text colour, everywhere in the
dropdown. This is a presentation step after `suggest` (`lookup.js` `suggestSections`, with no
Python twin), so the 20 rows are the same 20. For a screen reader the section is a `role="group"`
named by its label (`aria-labelledby`; the label itself `aria-hidden`, read once as the name), and
the rules are `role="none"` / `aria-hidden`: none is an option, and the arrow keys, Home / End
and `aria-activedescendant` move over the options only. The "Recent" rows are a history list, not
suggestions, so they have no section, but use the same colours.

### (3) Similar headwords

`similar(q, n=5, wide)` reads `headwords/<letter>.json` (the query's own letter key; `misc.json`
holds several first characters and is filtered to the query's) and the further files below. It is
shown **on a miss and under a hit**, and **built the same way for both**: the same pools, limits
and ranking, and the query never lists itself. So *kor*, a hit (*kor*, choir), offers *hvor*,
*for*, *fôr*, *kort*, *bor*. The page paints a hit's results first and fetches the list afterwards
(`render`), so a hit never waits for it.

**The limits scale with what is compared.** The one constant is `SIMILAR_PER = 3` (JS
`config.similarPer`): **one edit per three characters**. A candidate qualifies in either of two
ways:

- **by letters**: its **optimal string alignment distance** to the query (Damerau–Levenshtein
  without repeated edits: insert, delete, substitute, transpose adjacent) is at most
  `letter_limit(len(q)) = max(1, len(q) // 3)`: 1 for *bro*, *ikke*, *skole*; 2 for *venskap*; 3
  for *datamaskn*; 6 for a 20-letter compound. The length window is the same number (a length
  difference is itself that many edits), and the distance computation stops a row of the table as
  soon as its cheapest cell exceeds the limit, which keeps the pass cheap;
- **by words**, for a query of two words or more: the candidate shares **at least two words** with
  the query **in order** (a longest common subsequence of words), and no more than
  `words_limit(m) = max(1, m // 3)` words differ (`max(m, k) − shared`, for an m-word query and a
  k-word candidate). Two words count as the same if they are equal or within
  `word_limit(len(word)) = len(word) // 3` edits, so a typo inside *rotte* is forgiven, but a one-
  or two-letter word (*i*, *en*, *på*) must match exactly. *få rompa i gir* shares *få*, *i*, *gir*
  with *få ræva i gir*; *ta rotta* finds *ta rotta på* (one word missing); *ta xyzzy* finds nothing
  (one shared word is not enough).

**Accents are folded before comparing**: the distances are between bare forms and the bucket is
the bare first character, so an accent is never an edit. A form the lookup itself finds is never
listed; the other direction is, at distance 0: *à la carte* → *a la carte* first, *kafé* →
*kafe*, *òg* → *og*, as in ordbokene's similar list. The candidates include the fixed expressions
and their variants (*få rompa i gir* → "Similar words: få ræva i gir"); a query lists its own
expression's other variants, on a hit and on a miss, as ordbokene does (*en vond sirkel* → *en ond
sirkel*).

**Ranked** by: words differing (a word match first, 0, then 1 …; a letters-only match after every
word match); then letter distance (a word match's true distance; a rewrite's candidate as below);
then **capitalisation**, the query as typed against the candidate as written, the same
`case_distance` as the suggestions', a step smaller than any edit (*us* gives *ut, hus, as, is,
s*; *US* gives *UT, AS, S, U, KS*); then **the higher frequency band** (below); then **the query's
own first letter before another**; then length difference, the folded form, and the form as
spelled. The band comes before the first letter, which puts *hus* first for *vus*. Up to five. A
candidate that qualifies neither way is never shown, so nonsense (*xyzzy*, *bbbbbb*) gets nothing.

**Drawn as rows after a miss** (decisions [144](../../docs/decisions.md#d144)): when the
search finds nothing (no headword and no inflected form, `res.count` 0), each similar word is a
row drawn by the shell's own row code, the code the suggestions and History use (`lookup.js`
`similarRow`; `shell.js` `searchRowMain`, `searchRowSide`, `fillSearchRow` with
`similarArticles`): the word (`lang="nb"`) in the accent where it heads a translated article, its
word class where it heads one, then its English after a muted em dash, with a thin line between
the rows (§ 6). **A hit keeps the plain list of links**: under results, rows would be too much.
`similar` returns with each word what the row needs from the `headwords/` and `tails/` files it
read (`count`, `translated`, `pos`; § 3), and the row's English comes from the word's own `snip/`
file (`"_h"`), so a row loads no shard. A word that is only an inflected form (`count` 0, offered by
a spelling rule landing on a form in the query's shard, which is loaded) reads "inflected form of"
and its headwords (`formRow`; *kjøppte* → *kjøpte*, inflected form of *kjøpe*). The listener for a
similar word chosen after a miss (decisions [62](../../docs/decisions.md#d62)) is on every row.

`similar(q, n, wide)` widens by default (`Index.similar(q)`); `wide = false` is kept only to
measure against. The candidates widen in two ways:

- **Past the first letter.** Three more pools, compared with the query under the same limits (an
  edit to the first letter is one edit like any other):
  - a **wrong** first letter (*vus* → *hus*): `tails/<remainder_key(q[1:])>`, the headwords whose
    2nd and 3rd characters are the query's 2nd and 3rd (`u-s`);
  - a **missing** first letter (*us* → *hus*): `tails/<remainder_key(q)>`, the headwords whose
    2nd and 3rd characters are the query's 1st and 2nd (`u-s` again);
  - an **extra** letter in front (*ohus* → *hus*): `headwords/<letter_key(q[1:])>`, the bucket of
    the query's second character.

  Not reached: an error in the first letter together with an error in the 2nd or 3rd character
  (the tails file is chosen by them), and none of this for a one-character query. A one-letter
  typo on a single word changes the first character in about 17 % of cases under a uniform model
  of position (23 % for the 1,000 most common words, which are short); real typing likely errs
  less at the first letter, so read that as an upper estimate.
- **Through spelling-variation rules**: the project's own table of Norwegian spelling variation
  (below), applied to the bare query (`rewrites` in both files). Each rule applies once per
  rewrite; every rewrite is searched like a query in its own first letter's bucket
  (`headwords/<letter_key(r)>`). **Two rules may chain**: after the single rewrites, a second rule
  is applied to each of them (*kæm* → *kem* (*æ → e*) → *hvem* (*k → hv*)), never a third, and
  never over what the first rule wrote (`_rewrite_once` / `rewriteOnce` skip a match that touches
  it: so no undoing, and no *k → hv → v*, which would be a rule *k → v* the table does not have).
  **A rewrite is free only where it lands exactly**: a rewrite that is a headword is that candidate
  at distance 0 (*kordan* reaches *hvordan* at 0 through *k → hv*); **a candidate near a rewrite
  costs 1 + its distance from it**, within the query's own limit, so a rewrite never buys a free
  second edit. A rewrite that is an **inflected form** in the query's own shard (the one the lookup
  has just loaded) is offered itself, at 0. A chained rewrite costs exactly as a single one. At
  most `MAX_REWRITES` = 40 rewrites: the single ones in table order, then the chained ones in the
  order of the single rewrite they extend.

| Rule | Where | Example (a miss → its first suggestion) |
|---|---|---|
| *hv → k*, *hv → v* | word-initial | *hvalp* → *valp* |
| *k → hv*, *v → hv* | word-initial | *kordan* → *hvordan*, *kem* → *hvem*, *vem* → *hvem* |
| *kv ↔ hv* (Nynorsk and dialect spelling) | word-initial | *kvilken* → *hvilken*; *kva* → *hva*, *kven* |
| *kj ↔ sj ↔ skj* (never the *kj* inside *skj*) | anywhere | *sjære* → *skjære*, *kjorte* → *skjorte*, *forsjell* → *forskjell* |
| *tj ↔ kj* | word-initial | *tjole* → *kjole* |
| *gj ↔ hj ↔ j* | word-initial | *jerne* → *gjerne*, *hjerne*; *jem* → *hjem*; *gjul* → *jul* |
| *aa ↔ å* (every occurrence at once) | anywhere | *paa* → *på* |
| *æ ↔ eg* (the dialect pronouns) | word-final | *dæ* → *deg*, *mæ* → *meg*, *sæ* → *seg*, *jæ* → *jeg* |
| *æ ↔ e* (each occurrence) | anywhere in a word but its last letter (a word-final *æ* is *æ ↔ eg*'s) | *kæm* → *kem*, chained with *k → hv* → *hvem*; *æple* → *eple* |
| *ae ↔ æ*, *oe ↔ ø* (keyboards without the letters) | anywhere, all at once | *aere* → *ære*, *oel* → *øl* |
| single ↔ double consonant (*b d f g k l m n p r s t v*; a run of one is doubled, of two made single) | each run | *venskap* → *vennskap* |
| loanword respellings, one way: *c → k*, *c → s*, *ph → f*, *th → t*, *x → ks*, *qu → kv* | anywhere | *cafe* → *kafe*, *cigar* → *sigar*, *photograf* → *fotograf*, *thema* → *tema* |

"Word-initial" and "word-final" apply per word of a multi-word query (a space or a hyphen is an
edge). A rewrite's candidates match by letters only, never word by word. The rules describe the
orthography; they are not a list of words. There is no rule for a definite ending (*-a ↔ -en*):
suggestions are headwords, so no definite ending is ever one, and *hesta* still reaches *hest* by
one edit. Not reached: *hvertfall* (→ *i hvert fall*, a word split).

**How the count stays bounded.** A single word gets at most 24 single rewrites, so the cap of 40
never cuts one. Chaining multiplies them (uncapped, about 6–10 for a word of up to five letters,
17–32 for six to nine, 33–56 for ten to thirteen, 63–101 and at most 297 for longer ones), so the
cap binds on many words of ten letters or more; it keeps every single rewrite and as many chains
as fit, in table order. What keeps the TIME bounded is not the count but the pass each rewrite
makes over its bucket. Under a limit of 1 (a query under six letters) only an exact landing can
qualify, so the rewrite is looked up by its bare form (`by_bare` / `bucketByBare`). Above it, a
candidate's **bag distance** from the query (the letters only one of the two has, as multisets:
`bag_distance` / `bagDistance`, a lower bound of the alignment distance and a metric) rules out,
without computing the full distance, every candidate that cannot come within `limit − 1` of the
rewrite (`bag(r, w) ≥ bag(q, w) − bag(q, r)`), and the main pool skips the computation the same
way. Neither shortcut changes an answer: over 1,446 test queries the lists are identical with and
without them.

**Frequency.** The order prefers common words to rare ones. The source is "N-grams from the National
Library of Norway 2026" (Språkbanken, National Library of Norway; CC0), its list for books in
Bokmål from 1990 on, given to the build as `--freq`. An
**article's** count is the sum of the counts of the SET of its case-folded forms, headwords and
inflected forms, each distinct form once (*hus* fills two cells in each of two paradigms and counts
once; *Hus* and *hus* in the list are summed). **A form several articles share**
(`--freq-shared`): by default (`own`) an article counts its own headword(s) as written plus only
the forms no other article has, so *toe* does not inherit *to*'s count through its imperative
*to*. `each` counts a shared form for every article that has it, which lifts several thousand
articles by one to nine bands (*frukte*, *restere*, *ete*, *toe* …). A **headword string's** band
is the highest of its articles' (a suggestion is a string to search for, so homographs do not add
up). The **band** is `0` for unseen, else `1 + ⌊log2(count) / 1.75⌋`, at most 15: one band per
factor of about 3.4 (1 → 1, 100 → 4, 10,000 → 8, a million → 12; *hus* 11, *dus* 7, *bus* 6, *VVS*
5). A multi-word expression is never in a 1-gram list and is 0.

**The scale.** The band formula was set on a smaller corpus (Språkbanken's sbr-12, 1,306,199,192
tokens); the National Library's books hold 14.45 times as many (18,873,584,692). So a count is
divided by `FREQ_SCALE` before banding, `band(max(1, round(count / 14.449)))` above 0, and a band
keeps its meaning (`build_index.py` `FREQ_SCALE`, `form_band`, `article_freq`).

**A headword string's rules**, in order:

1. **the overrides registry**, where it names the string: a band, or `nb` for the scaled count.
   An entry is a ruling, so it comes before every rule.
2. a **single letter or digit** (length 1, alphanumeric) → band 1, so a letter never outranks a
   counted word (the books count the alphabet as page apparatus);
3. an **abbreviation**, a string made only of letter groups each closed by a full stop
   (`^(?:[^\W\d_]+\.)+$`: *fl.*, *bl.a.*, *f.eks.*; a digit, space, hyphen or "…" spares it, so
   *17. mai* and *ph.d.-kandidat* keep their count) → its scaled count held between `ABBR_FLOOR`
   and `ABBR_CEILING`, both 2, so band 2. The fixed bands apply whether or not the list counts the
   string;
4. a string whose every article is a **symbol sunk by the third fix** below → the abbreviation
   band;
5. everything else, two-character strings included: the scaled count.

**The registry**, `ordpar/freq-overrides.tsv`, has a header `form<TAB>band<TAB>why` and one line
per headword string as spelled, its band (0–15, or `nb`) and the reason. Entries are added only
where a visible suggestion or similar-words list goes wrong: *å* and *i* `nb` (words, not
letters), *fl*, *ff*, *ss* 2 (page apparatus), *kr*, *kg* 8 (prices and weights), and a few verbs
that the agent-noun fix (below) lifts too high.

**Three fixes to `own`:**

* *a plain spelling beside its accented headword* that is also another article's headword does
  not count for the article: *fôr* does not take the preposition *for*'s count, nor *òg* *og*'s,
  nor *én* *en*'s. Homographs that share both spellings (*fôring* I and II) are untouched.
* *the agent noun's present form counts for its verb too*: for *skriver*, *løper*, *vasker* the
  verb is what is usually meant, and ordbokene lists verbs first. It applies to a verb's present
  form (`Pres`, not passive) that is the headword of a masculine noun whose indefinite plural is
  that form + *e* (the noun keeps its count too): about 690 forms for about 740 verbs. The paradigm
  test keeps it off *sukker* ← *sukke*, *lager* ← *lage*, *liter* ← *lite*.
* *a symbol or abbreviation spelled like a word*: an article whose every word class is `SYM` or
  `ABBR` takes no count from a form it shares, case-folded, with a form that an article of another
  class spells in lower case (*Og* / *og*, *Be* / *be*, *At*, *Er*, *UT*, *NOK*; about 125
  articles), and falls to the abbreviation band.

The manifest's `freq` names the file, the `freq_shared` rule, the scale, the fixed bands, the
fixes and the overrides file with its entry count. About 93,000 of some 103,000 headword strings
have a band above 0.

### (4) Random word

`randomHeadword()` makes a uniform pick from `random.json`'s headwords (§ 3), loaded once by
`loadRandom`, and opens it as its search, `/bm-en/#q=<headword>` (in place on the search page,
`ordparShell.search`), or as its word page where it has one (§ 9). So it never draws a word that
search leaves out. An id drawn from an older file of article ids opens `/bm-en/<id>/`. A Random
word draw is answered but not recorded in History (§ 6).

### Query guards

Applied before any request: an empty query → nothing; more than 20 whitespace-separated words →
`tooManyWords`; any word longer than 40 characters → `wordTooLong`; the search box itself caps
input at 200 characters. A guarded query is never sent to the index, and the reason is shown.

### Measured cost on the device

Measured with Bun on a desktop computer, warm, on the full index:

| Operation | Time |
|---|---|
| `suggest()` on a loaded shard | about 0.3–0.8 ms per keystroke |
| `loadShard` for a very large shard (`s`, before the big letters were split): parse, then build the folded maps and bare forms | about 75–80 ms (*e*, a middling shard: about 20 ms) |
| `similar()` on a hit or a miss, short words (3–5 letters) | about 3–6 ms mean |
| `similar()`, an error in the first letter | about 25–32 ms mean |
| `similar()`, long words (14+ letters) with a typo | about 34–40 ms mean (95th percentile 78–89 ms, worst 98–326 ms) |
| `similar()`, expressions of 3+ words | about 31 ms mean (95th percentile about 68 ms) |
| the same pass in the Python twin (`build_index.Index.similar`) | about 100–140 ms per query |

Without the bag-distance shortcut, long single hits (*representere*, *arbeidsmiljøloven*, *få ræva
i gir*) took 87–204 ms. A phone is perhaps 3–5 times slower (an assumption, not measured): a long
query would then take roughly 60–150 ms, after the results are already painted: a few frames, not
a stall. **The one-off parse of a big shard is still the larger cost.**

## 5. Sizes

Raw is the file on disk; gzip is level 9, which is what a static host serves. The index's own
manifest, `index.json`, records every file's figures on each build; the figures below are from the
build of 11 November 2026 (Bokmålsordboka's 94,244 articles, 94,188 in search, 22,281 translated).

| Files | Count | Raw | gzip | Largest (gzip) |
|---|---:|---:|---:|---|
| shards | 135 | 12.9 MB | 2.80 MB | `h.json` 160 KB |
| `<letter>-top.json` | 5 | 5.2 KB | 2.4 KB | about 0.5 KB each |
| `headwords/` | 30 | 1.88 MB | 524 KB | |
| `tails/` | 585 | 1.92 MB | 599 KB | |
| `snip/` | 3,849 | 7.93 MB | 3.46 MB | |
| `en/` | 27 | 3.21 MB | 1.17 MB | `s` 119 KB |
| `en/tails/<k2>-<k3>.json` | 359 | 873 KB | 346 KB | `o-n` 7.6 KB |
| `translated.json` | 1 | 139 KB | 52 KB | |
| `random.json`, `random-en.json`, `labels.json` | 3 | 112 KB | 35 KB | |

Of a shard's bytes, `forms` is the largest part (about 45 %), then `words` and `heads`.

**What a search downloads.** A first search reads its shard, `translated.json` and, for the
similar words, its letter's `headwords/` file: *hus* about 243 KB gzip, *skole* about 204 KB
(before the headwords file was split by letter and the big letters by their second character, an
*s* word cost 847 KB). The similar pass then reads, after the results are painted, the two
`tails/` files, the second letter's `headwords/` file and each rewrite's letter file: 6–55 KB more
on a hit and 20–75 KB on a miss, most of it whole `headwords/` files of other letters, not the
small `tails/` files. Splitting the `headwords/` files by two letters, as the tails are, would cut
that. A miss's rows then cost only their `snip/` files (*husx* one file, 4.1 KB; *spisee* two,
18.4 KB). `translated.json` is a large share of every first search and is the next thing to cut,
if one is wanted. A search that is typed rather than followed from a link adds the
`<letter>-top.json` (about 0.5 KB) on the first keystroke of a split letter.

**Full articles in the results.** In the default view, each headword hit's page is fetched in
parallel (*hus*: one page, 7.5 KB gzip; *en*: four pages, 13.8 KB; *være*: three, 14.6 KB). A
separate fragment file per article would save the page frame, 15–35 % of what a search fetches
(68 % for a one-line set phrase), at the cost of 94,000 more files and over 300 MB raw beside the
pages; the page fetched for a result is also the page a click on its headword opens, already
cached. The articles start once the shard has answered, so on a network the full view costs one
more round trip than the list view's first paint.

**The `snip/` key.** Filing the snippets by three characters was chosen over the alternatives,
measured gzip-9 for one *hus* search: by shard (135 files) 95 KB; by two characters (548 files)
9.5 KB; **by three characters (built) 3.1 KB**; inline in each `words` entry, +85 KB on the shard,
paid by every reader, list view or not. Most snippets are short (median 30 characters, 90 % under
73), so the cut at 80 changes little. The `"_d"` map adds about 3 % to the files; a second file
family for the dropdown would add a request per prefix instead.

**The Norwegian definitions for the hovers** (§ 3, `"_n"` and `data-s`). Measured over the whole
site, the ways of giving each translated article's first Norwegian line to the rows and the hovers
cost the offline download: (a) a second peek in each page's markup, about +2.4 MB in all; (b) a
file family by id, about +1.9 MB; **(c) the file key on each link and the `snip/` file read
(built), about +0.8 MB**, the hover reading the `snip/` file the rows already share (median 2.8 KB
gzipped). The limit set was 2 MB.

**The English search.** One file per letter costs 2.5 times the gzip of a single file, because a
file holds each article once per file that names it and each phrase once per letter of its words;
that is the price of one request per search. A search reads ONE file cold (0.2–119 KB gzip), which
also answers the suggestions, the similar words' word matches and the miss line; the similar
words past the first letter add two tails files (0–7.6 KB) and the second letter's file where it
is another letter, 42–83 KB in all, after the results. Filing the one-word keys by their FIRST two
characters would carry the extra-letter case for 0.1–12 KB instead of a whole letter file; it was
measured, not built.

## 6. The pages

**The search page** is the static file `<out>/bm-en/index.html`, taking `#q=<word>`. The search is
in the address's FRAGMENT (decisions [104](../../docs/decisions.md#d104)), so it is never sent
to a server, neither in the request line nor in a `Referer`. It answers from the index **in
place**: the query is pushed with `history.pushState`, focus returns to the search box, and the
hit count goes to a polite live region. While its index file loads the results show "Searching…",
and a search overtaken by a newer one is dropped (§ 9). Back and Forward answer again from the same
shard, already cached. Every search address is made by `lookup.js` `searchUrl` and read by
`ordparSearch.queryFromLocation`. An old `?q=<word>` address is still read, and rewritten to `#q=`
in place by `ordparSearch.fragmentAddress` (`history.replaceState`: no reload, no new entry). A
link to a search on the page itself (a "Similar headwords" link) would only move the fragment, so
`ordparSearch.wireFragmentLinks` answers it as a new search by the reader (recorded, the page
scrolled to the top); a click for a new tab is left to the browser. The header's form never
submits its own GET on a page with script: `shell.js` takes it, and before `shell.js` has loaded,
the head script (`head.THEME_JS`) sends it to `#q=`; only with JavaScript off does the form's GET
to `/bm-en/?q=` run (the privacy page says so). What a search does fetch: the index files named by
the query's first letters (`shardKey`, `tailKey`, `snipKey`) and the pages of the articles shown in
full.

**The results** follow ordbokene's own default. A hit opens with one heading (`<h2>`),
"Norwegian–English dictionary" (`results.dictionary`), and the number of articles in a badge, read
as "5 articles" by a screen reader (`results.count` / `results.countOne`), the same in both views.
The translated articles come first (§ 4 (1)); when untranslated ones follow them, the full view
sets them under a small "Not yet translated" heading (`results.untranslated`, equal to
`article.UNTRANSLATED_HEAD`; its look `.ordpar-untr-head` from `article.css`). The list view has no
such heading: an untranslated row carries the *Norwegian only* tag instead. The headword groups'
articles are shown **in full**, one after another, each on its own card (`<article
class="ordpar-result" aria-labelledby="r<id>-hw">`), exactly as its page `/bm-en/<id>/` shows it.
Then come the inflected-form groups ("*husene* is an inflected form of: hus, …", each row a link to
`/bm-en/<id>/`, an untranslated one tagged *Norwegian only*, with its article's snippet beneath)
and the similar words: plain links under a hit, rows after a miss (§ 4 (3)).

**Only an untranslated row is tagged** (decisions [137](../../docs/decisions.md#d137)). Every
row that tags an article, a list-view row and an inflected-form row (`lookup.js` `listRows`,
`articleItem`), the rows of History and Favourites (the same code) and a word page's built rows
(`ordpar/sitegen/wordpages.py` `_tag`), carries the tag *Norwegian only* (`tag.norwegianOnly`,
`.ordpar-tag`) when the article is untranslated and no tag when it is translated. There is no
"translated" tag; a translated word is told apart by its colour where the rows colour words.
`ordpar/tests/test_ordpar_tag137.py` pins it, in the code and in a built word page.

**Where to look when a word is missing** (decisions [171](../../docs/decisions.md#d171)). A
search that finds nothing, no headword and no inflected form, shows "Could not find “*word*”."
(`results.none`) and under it one line (`lookup.js` `missWhy`, the words `results.noneWhy`): "It may
be a misspelling or a compound. Try the larger dictionaries NAOB (for Bokmål) and Norsk Ordbok (for
dialect words and Nynorsk), both in Norwegian." Each name is a link to that dictionary's search for
the reader's word (`MISS_LINKS`: NAOB `https://naob.no/s%C3%B8k/<word>`, Norsk Ordbok
`https://norsk-ordbok.no/nno/no/<word>`, the word through `encodeURIComponent`), opening in a new
tab with `rel="noopener nofollow"`. Nothing is sent to either site unless the reader follows a link.
The similar rows follow the line (§ 4 (3)). A search by English word that finds nothing shows its
own message instead (`results.noneEn`, `results.noneEnWhy`), with no links.
`ordpar/tests/test_ordpar_missline171.py` pins the words and the links. A similar row shows the word, its word class for one article, and after a muted em dash
what a suggestion row shows on its right (`shell.js` `sideGlosses`), with a thin line between rows,
the suggestions' row spacing (it follows the "Suggestion rows" setting) and the results column's
width (`shell.css` `.ordpar-similar-rows`). The search page, a word page's in-place search, the 404
shell and the installed copy all draw through `render`, so all show the same.

**Where an article comes from: its own static page.** `fetchArticle` fetches `/bm-en/<id>/` (all of
a search's hits at once, each once per page view), and `extractArticle` takes the fragment (from
`<div class="ordbok` to the credit footer) plus an untranslated page's status caption; the long
untranslated note is left out, since it would repeat under every untranslated hit. No second copy
of any article is written. If a page cannot be fetched, the hit falls back to a link row.

**Unique ids** (`scopeArticle`). Several articles on one page would repeat `def1`, `def2`,
`ordpar-paradigm` (the inflection island) and an embedded expression's `x<id>-defN` (see
[build-site.md](build-site.md), the page's anchors). Every id inside a result is prefixed `r<id>-`
(`def3` → `r24627-def3`, `x102921-def4` → `r24627-x102921-def4`, `ordpar-paradigm` →
`r24627-ordpar-paradigm`, a control's `xra24627-1` → `r24627-xra24627-1`), and so is every
attribute that names one: `for`, `data-for` and `data-paradigm` (`inflection.js`). A link to the
article's own sense (`/bm-en/<id>/#def3`, the gloss's sense marks and internal references) becomes
the in-page `#r<id>-def3`; every other link, to another article, a sense of another article or a
mini's target, is left as it is and opens that page. An article listed twice on one page (two
exact groups sharing it) is shown in full once. The invariant to keep: no duplicate ids, and no `#`
link or `for` / `aria-*` reference without a target.

**The controls under each result**, after ordbokene's own: **Copy link** copies the article's own
page URL, `<origin>/bm-en/<id>/`, not the search's; **Share** shares that URL with the headword (and
its homograph numeral) as the title; then "Suggest a correction" and the heart (below). They sit
right-aligned after each full article and each opened row's article (`lookup.js`
`resultControls`). There is no Cite button (decisions [21](../../docs/decisions.md#d21)) and
no "Article page" link (decisions [168](../../docs/decisions.md#d168)). As on the article page,
each button is drawn only where the browser has `navigator.clipboard` / `navigator.share`. The
words are the page's own ("Copy link", "Link copied", "Share": `results.copyLink` / `copied` /
`share`, equal to `strings.py`'s `copy_link` / `copy_done` / `share`). The string
`results.articlePage` ("Article page") is still used by the built word pages' list rows for their
panel's fallback link (§ 9). The controls carry no ids; "Link copied" shows for 2.5 s in a
`role="status"` span.

### History and favourites

`ordpar/site/personal.js` keeps both in the browser's storage, beside the settings, under the keys
`history` and `favourites` (§ 7). Nothing leaves the browser: no cookie, no request. **The history
is a list of searches, the favourites a list of articles.**

A **favourite** is `{id, word, hg, hgs?, pos, translated, snip, drop?, t}`: the headword as the
index shows it (its spellings joined by the data separator " / ", drawn with ", "), the homograph
number (where the spellings' numbers differ, `hgs` holds one per spelling and `hg` the first
non-zero; `hgs` is optional, so the export format stays at version 2), the index's word-class code,
translated or not, the list view's snippet line, the dropdown's set-phrase text where there is one
(§ 3), and a timestamp.

A **history entry** is `{q, n, t}`: the query as typed (trimmed), the number of DISTINCT articles
whose own headword the search matched (the headword hits, an accent-folded group's included; not
the inflected-form rows), and a timestamp. When `n` is 1 it also carries
`{word, hg, pos, translated, text}`, where `text` is the right-hand text by the dropdown's rule
(§ 4 (2): the gloss unit; for a translated set phrase with no summary gloss, its set-phrase box, or
'' for nothing; '' for an untranslated article). A missing or corrupt value reads as an empty list,
a malformed entry is dropped, and storage that is full or blocked fails silently.

* **What the history records: a search that found something** (`lookup.js` `recordSearch`,
  called by `render(root, query, {record: true})` once the lookup has answered): the search box
  submitted on the search page or the 404 shell; a suggestion chosen (choosing one runs a search
  for its word); a "Recent" entry chosen; the search page's first load from `#q=` (or an old
  `?q=`), which is how the article page's search box, a "Similar headwords" link from another page
  and a `/history/` row arrive; a "Similar headwords" link on the search page itself
  (`wireFragmentLinks`). A miss is not recorded, **nor is a search that found only inflected
  forms** (*gikk* → *gå*) until one of them is opened.
* **An inflected-form result opened is recorded as a search for its headword** (`lookup.js`
  `recordOpened`, wired to each "is an inflected form of" row's link by `recordOnOpen`, in both
  views): the headword (`lemmaOf`: *danne*, opened from *dann*) is looked up and recorded by
  `recordSearch` exactly as a search for it would be. A placeholder entry (the one article, as an
  entry for its headword) is written at once and replaced when the lookup answers (the same query
  and time), so leaving the page early still leaves the entry. A plain click waits for the entry,
  at most 1.2 s, before following the link; a click that opens a new tab or window, or a middle
  click, records without waiting. Opening from the 404 shell records too.
* **Not recorded:** an article page loading; an article opened by any other link; a mini; the
  favourites (an article opened on `/favourites/` included); a Random word draw (its search is
  answered but is not the reader's search, also on a reload of it: the history entry's state
  `{random: true}`, `ordparSearch.takeDrawn`); a list row opened (its article is a headword hit,
  already the search's entry); Back / Forward (`popstate`, and a search page reloaded by Back from
  another page: `performance` navigation type `back_forward`); a re-render after a setting changes;
  the 404 shell's automatic search of a mistyped address (its search box does record). The
  browser's own history keeps page visits.
* **Newest first, a repeat moved to the top, at most 100.** A repeat is the same query trimmed and
  lower-cased (*Hus* and *hus* are one entry, `searchKey`); the spelling typed last is kept.
  **When it is written**: several articles, or one untranslated article, at once; one translated
  article at once too, without its right-hand text, and then again, as the same entry (the same
  query and time), once the text is on hand, so a reader who leaves before the article arrives on a
  slow connection still keeps the entry. The text comes in the full view from the page the result
  already fetched (its `data-snip` / `data-drop`, `extractArticle` → `meta`; a page without
  `data-snip`, which is left out where it equals the meta description, gives the description),
  else (the list view, an opened inflected-form result, a page that could not be fetched) from the
  `snip/` file of its headword (`"_d"` first where it is not `""`, else the line's first unit). The
  entry carries the time of the search, so the filled entry keeps its place (`addSearch`). An entry
  left without its text is drawn all the same: a History or Recent row with no stored text reads
  its gloss from the index when shown (`shell.js` `needsFill`, `fillSearchRow`).
* **Older per-article entries** (one per article, the favourites' shape) are read as searches for
  their word (`fromArticles`, at read time; the new shape is written at the next write): the word is
  the first variant of a display with alternatives (`fôr / for` → `fôr`); entries sharing a word
  become one, at the newest time; the count is the number of distinct ids merged; one id keeps its
  display fields and its text by the dropdown's rule.
* **The heart** (`ordparPersonal.heartButton`): a toggle button beside Copy link and Share under
  every full result and every opened row (and on the article page, at its card's foot), last in
  the row; `aria-pressed`, an outline heart when not saved and a filled one when saved, named
  "Favourite" in both states (`fav.label`; `aria-pressed` alone carries the state, so a screen
  reader says "Favourite, toggle button, pressed"). A closed list row shows a small filled heart
  beside its headword when the article is saved (`favMark`, `role="img"`, "In favourites"). A
  change repaints every heart and mark on the page at once (`refresh`), and a change in another tab
  too (the `storage` event).
* **The recent searches in the dropdown** (`shell.js` `openRecent`): with the box focused and empty
  (or holding only spaces), the last 8 history entries under a "Recent" heading with a "History"
  link to `/history/`. The heading sits above the listbox, outside it (a listbox holds options
  only), in one popup (`.ordpar-popup`); the listbox is then labelled "Recent searches". The rows
  are suggestion rows (`ordparShell.searchRowMain` / `searchRowSide`, shared with `/history/`): the
  query, and for one article its word class in faded italic (none for a set phrase); no homograph
  numeral beside the query, the row being a word, not an article. **On the right, as the
  suggestions**: for several articles, the homograph-numbered glosses of the articles whose own
  headword the search matched, translated first, as many as fit, then "+ N more"
  (`paintGlossList`, `fitGlosses`; *fly* "V to fly · III plane, aircraft + 3 more"); untranslated
  articles, and translated ones with no gloss text, are only counted in the "+ N more"; with none
  translated, each homograph's numeral and its first Norwegian definition (`sideGlosses`), and "N
  articles" only where none has a line. Each numeral is the number of the spelling the search
  matched. For one untranslated article: its Norwegian definition ("Norwegian only" where it has no
  snippet). For one translated article: its stored gloss text, with no fetch. **The query's
  colour** is a suggestion row's: the accent where a translated article is behind the row, else the
  text colour (`markTranslated`, set at once for one article, when the side fills for several).
* **Drawn from the dictionary when shown** (`fillSearchRow`), not from text stored with the entry:
  an entry keeps no ids, so the search is run again (`lookup`, its shard and `translated.json`) and
  the headword hits' `snip/` file read (the query's key). The rows paint at once from storage with
  the right-hand side held (`is-pending`, as a suggestion's gloss) and fill in, each row fitted
  again as it fills; the installed copy answers the same files offline. Where nothing answers, or
  the search now finds no headword, the row is drawn as stored: one translated article with its
  text, that gloss (*gikk* "to go"); one untranslated article, "Norwegian only"; one translated
  article stored without text, nothing on the right; several, "N articles". The stored shape, and
  the export's version 2, are unchanged by this. Arrow keys, Home / End, Escape, Tab and Enter work
  as in the suggestions; **choosing one runs the search again** (`submit`), which moves it to the
  top. Typing replaces the rows with the suggestions; clearing the box with × brings them back.
  Every page has the dropdown: the article page loads `lookup.js` and `shell.js`, deferred, and
  reads `/site/strings/en.json` by fetch, cached, since its strings are not inlined.
* **The two pages** are static shells (`ordpar/site/favourites.html`, `ordpar/site/history.html`,
  written by this build like the search page) drawn from storage by
  `ordpar/site/personal-page.js`, newest first.
  `/favourites/` shows **the list view's rows** (`lookup.js` `listRows`, exported on `ordparSearch`
  with `{level: 2, mark: false, renumber: true}`): headword line, word class, the translated /
  Norwegian-only tag, and under them the snippet line stored with the favourite. The headword line
  is drawn as everywhere, each spelling with its own numeral, ", " between (`headwordInto`). Every
  favourite with several spellings is checked against the index's `words` entry once its shard
  answers (`renumber`, `redrawFrom`): one stored without `hgs` has its numerals corrected, and one
  stored in another spelling order is redrawn in the index's order, only where the index holds the
  same spellings; the entry itself is left as stored. Each row is a disclosure button in an `<h2>`
  that opens the article in place below it (`mountArticle`: the page fetched as the list view
  fetches it, so the installed copy answers it offline; the Inflection toggle per `infl`; Copy
  link, Share, "Suggest a correction" and the heart under it, as for a list-view result); there is
  no small heart beside the headword (every row is a favourite); each row has a "Remove" button
  beside it (focus moves to the next row's). The page loads the search page's deferred article
  scripts (`inflection.js`, `article.js`, `mini.js`). A row is made once per page view and kept: a
  removal here or in another tab, or a favourite added elsewhere, adds and drops rows in place, so
  an opened article stays open; the heart pressed inside an opened favourite removes its row, the
  focus going to the row now in its place (else the heading). A change of language draws the rows
  again. Opening a favourite records nothing.
  `/history/` shows one row per search, drawn as the dropdown's "Recent" rows, the whole row a link
  to `/bm-en/#q=<query>` that runs the search again (no heart mark: an entry is a word, not an
  article). Each row's right-hand side is filled as the row comes within 400 px of the screen
  (`IntersectionObserver`; all at once without it), so a full history of 100 does not run 100
  searches on load. **Clear history** asks once, in place ("Clear all 6 entries from the history?
  This cannot be undone.", with Clear and Cancel, Cancel focused). Each page says plainly when it
  is empty, and that the lists are kept only in this browser, on this device. **Reached from**: a
  "Favourites" link beside Settings in the header of every page; the history page from the footer,
  the favourites page, the dropdown's "Recent" heading and each page's link to the other. Both
  pages are `noindex`: they are empty to a crawler.
* **Export and import** are on the settings page, section "Loading, offline and your data", under
  "Move to another device"; the favourites page links to `/settings/#data`. Export downloads
  `ordpar-<local date>.txt` (`text/plain`, a file every phone and mail program opens and sends),
  its content JSON:
  `{"format": "ordpar-personal", "version": 2, "exported": "<ISO time>", "settings": {…}, "history": […], "favourites": […]}`,
  with every setting's value in force (`getSetting`). Where the browser can share a file
  (`navigator.canShare({files})`, as on Android's Chrome) a "Send the file" button offers the share
  sheet too: the `.txt` first, and a `.json` copy only where the `.txt` cannot be shared. A refusal
  other than the reader closing the sheet (`AbortError`) tries the next file at once, and when none
  is left the file is downloaded and the status line names the error (`transfer.shareFailed`,
  "err.name: err.message"). Import reads a chosen file (`.json` or `.txt`) and MERGES: the
  favourites added to those present, no duplicates, newest first; the history combined, one entry
  per query (the later search), ordered by time under the cap; the settings taken from the file and
  applied at once (`ordparShell.applyAll`). A version-1 file is read too, its per-article history
  converted as the stored old entries are; each version's history must be in its own shape. A file
  that does not parse, has another format or a newer version (3 and up), or holds one malformed
  entry is refused with a plain message and nothing changes; if the browser refuses a write half
  way, what was there is put back.

### The rest of the results page

**The table in a result card.** In a full result and an opened row, the inflection table's mount
is capped at the card's width (`shell.css`), and `inflection.js` `fit` (called by `mountArticle`,
never by the article page) measures each wide table's unwrapped width (max-content) against it:
if wider, the narrow layout is forced (`ordpar-force-narrow`). It measures again when the card
changes width (`ResizeObserver`) and when the Inflection toggle opens. At 48rem and below the media
rule decides, as before; a table too wide even when narrow still scrolls inside its wrapper, the
last resort. There is no sideways scroll otherwise, and the article page is unchanged. A container
query was rejected: a fixed threshold would have made every results table narrow on a desktop,
small ones included.

**Headings.** The results' heading is an `<h2>`; each article's `<h1>` headword becomes an
`<h3 id="r<id>-hw">` holding a link to the article's page (the canonical URL), and its section
headings ("Etymology", …) take `aria-level="4"` (the tags stay `h3`, so the article CSS still
applies). In the list view, one level lower (`aria-level` 4 and 5).

**What runs on a result**, as on the article page: `inflection.js` `mountAll(<the result>)` draws
the inflection island (the toggle shows only when a table was drawn); `article.js`
`window.ordparDefs()` adds the "Show English" cues under `defs = no`, opens the toggles under
`infl = open` (per toggle, once, so a result added later follows the setting and a toggle the
reader closed stays closed) and, under `minifetch = page`, has the mini script queue the new
targets (`ordparMinis.scan`). The hover peek is CSS. The small articles are `/site/mini.js`'s (see
[build-site.md](build-site.md), cross-references and the small article); its clicks, like the
reveal's, are delegated on the document, so a lifted article and an opened list-view row get them
with nothing to wire. The mini script fetches a target through `ordparSearch.fetchArticle`
(exported for it), so a result and a small article of the same article share one request and one
cache entry. The page's sheets (`article.css`, `inflection.css`) are linked before `shell.css`,
which wins where they meet; the article page's own rules are a separate sheet, `page.css`, that
the search page does not load. The article page links `shell.css` too: the header, the footer and
the card are the same on both.

**The list view** (`listview` = `on`; with `forms`, the default, when there are several headword
hits or any inflected-form row; with `multi`, when there are several headword hits; § 7). Each
headword hit is one row, as in ordbokene's "List view in simple search": headword (`lang="nb"`),
homograph as a Roman numeral (hidden from assistive technology, with a visually hidden "homograph
2" beside it, as in the page head), word class (none for a set phrase), the *Norwegian only* tag
on an untranslated article (a translated one has none; § 6), and under them the snippet (§ 3) on one line, cut again by CSS with an
ellipsis to the row's width. **The snippet file for the query (`snip/<snipKey(q)>.json`) is asked
for only on a headword hit**, once the shard has answered; every headword key has its file (§ 3),
so no search asks for a file that is not there. The rows paint as soon as the lookup answers, each
with an empty snippet line; the file fills the lines (`fillSnippets`), and a row with no snippet
loses its line. On a cold search the snippets therefore appear one round trip after the rows. No
article is fetched until a row is opened.

**A row is a disclosure**: a `<button>` inside an `<h3>`, `aria-expanded`, `aria-controls` naming
the region below it (`r<id>-panel`, `role="region"`, `aria-labelledby` the button). A click, Enter
or Space opens the article in full in the region (fetched the first time) and closes it again; any
number may be open at once. **An opened row's inflection table follows `infl`**, as the full view
and the article page do (ordbokene always opens it; see `docs/divergences.md`). An open row is
shaded and its chevron turns. Changing the setting draws the current results again in the other
view without a reload (`lookup.js` listens to `ordparShell.onChange`).

**The inflected-form rows' snippets** (both views). Each row under "“*tær*” is an inflected form
of:" stays a link to the article's page, and carries beneath it the same one-line snippet a list
row shows. Its file is the key of the article's headword as the index shows it (`words[id][0]`, the
first form of "fôr / for"; `lemmaOf`), which has a file because it is a headword, so the default
view reads `snip/` files only when there are inflected-form rows, only the keys their headwords
need, after the results have painted, and never a file that is not there. The rows hold their
snippet line until it fills.

### The 404 shell, indexing and the strings

**`404.html` is the shell too.** A static host has no file at `/bm-en/<word>`, so the host's 404
handler shows it:

| Path | What happens |
|---|---|
| `/bm-en/<word>` | where the word's fold has a word or form page, the shell sends it there (`/bm-en/Norge` → `/bm-en/norge/`, § 9); otherwise the search for `<word>` is drawn in place, and **the URL stays as typed** |
| `/bm-en/<id>/<slug>` (an id followed by anything) | `location.replace('/bm-en/<id>/')`: the slug is decoration |
| `/bm-en/<id>/` that has no page | the not-found page; the shell never bounces to itself |
| anything else | the not-found page: "Could not find …", a link home, and the header's search box |

**`noindex` by page** (decisions [128](../../docs/decisions.md#d128)). `copy_shell` drops the
templates' own robots lines and writes each page's from `SHELL_PAGES`: the home page `/` is indexed
(no robots line); the search page `/bm-en/` (the home page's twin), 404, favourites, history and
settings are `noindex`. Each shell page also carries the link-preview tags (`head.social_tags`)
from its own title and description. The home page's description (the search page's too, one
template) is `describe.home_description`, its number the About page's figure of translated
articles, read from `<out>/build.json`. `robots.txt` ships from `ordpar/root/`, not from this build
(see [offline-app.md](offline-app.md)).

**What a crawler sees.** GitHub Pages serves the root `404.html` for every missing path **with HTTP
status 404**; it has no rewrite rules. So a search address such as `/bm-en/#q=hus` is not indexed.
The indexable addresses of a word are its article page `/bm-en/<id>/` and, for the searches the
plan names, its word page `/bm-en/<word>/` (§ 9): both real files. To make other search addresses
indexable, the host has to change (a Worker, or Cloudflare Pages' `_redirects`), not the shell.

**The strings are inlined** into every built page as `window.ORDPAR_STRINGS` (replacing the
`<!--ORDPAR_STRINGS-->` marker), so the frame paints with no second request. The same file also
ships as `/site/strings/en.json` (`ordpar/site/strings/en.json`), which a switch to a language the
page was not built with would fetch. `en` is the only language that exists (decisions
[21a](../../docs/decisions.md#d21)): the switcher lists it alone, and the mechanism, not the
choice, is what is built.

## 7. What `shell.js` offers the article pages

`shell.js` is loaded by every page, the article and About pages included. It applies the theme and
the colour on load and **enhances the static header** that `ordpar/sitegen/chrome.py` writes on
every page: the box becomes a combobox (`role`, `aria-expanded`, `aria-controls`,
`aria-autocomplete`) with the × button and the dropdown inside `.ordpar-combobox`. The form's
Search button is drawn by `shell.css` as a magnifier inside the box's right end, beside the × (CSS
only: its text "Search" is moved out of sight and remains its accessible name; the input is padded
past both). It **makes the parts of the frame that need script** (`addChrome`: Random word,
Favourites and Settings in the header, and Settings, Favourites and History after the footer's
Home; then, on a phone, the install hint, `install.js` `hint`, see
[offline-app.md](offline-app.md)), and sets `ordpar-chrome` on `<html>`, which releases the room
`shell.css` held for them from the first paint. It wires Random word (beside the box; hidden where
`lookup.js` is not loaded), relabels the frame from the strings in force (every
`data-ordpar-string` element, and the static ones found by selector, `STATIC_STRINGS`, the same map
as `chrome.RELABEL`; only keys the strings have, so a page whose strings did not load keeps its
built words), marks `aria-current` on the header's and footer's links, and exposes
`window.ordparShell`. Its main members:

```js
window.ordparShell = {
  t(key), has(key),        // a string for the current language (the key itself if missing); is it there
  getSetting(key),         // any key of SETTINGS, with its default; 'colour': the id, else the default scheme's
  savedSetting(key),       // the stored value, as against one set for this visit only
  setSetting(key, value),  // stores, applies, relabels the frame in place
  applyAll(),              // re-applies every stored setting at once (after an import)
  resetSettings(), deleteStoredData(),
  SETTINGS,                // the settings' table: {key, values, def, section, sub?, ...}
  KEYS,                    // the setting keys, the ones an export carries
  colours(),               // the colour schemes where the page carries them (/settings/)
  lang,                    // the interface language in force
  onChange(fn),            // (key, value) after any change, ('render', lang), ('reset'|'import', null)
  setSearchHandler(fn),    // a page that answers searches itself (the search page) registers here
  search(q, how),          // a search answered in place by that handler; false where there is none
  searchRowMain(e), searchRowSide(e), fillSearchRow(...),  // a history entry drawn as a suggestion row
  sideGlosses(...), similarArticles(...),                  // the right-hand side of the rows
  direction, setDirection,                                 // the English / Norwegian search switch
  hintGuard(...),          // the "?" boxes' outside-click guard (below)
  event(name, data),       // hands an event to events.js (below)
  ready                    // a promise resolved once the language is loaded and the frame drawn
}
```

The object has a few more members for Norwegian only, the English rows and copying; the comment at
the head of `shell.js` and the object literal near its end are the complete list.

**The head script** applies the theme, the colour scheme and the article settings before the first
paint, and puts `ordpar-js` on `<html>` (so the room for the frame `shell.js` makes is held). It has
ONE copy, `ordpar/sitegen/head.py` `THEME_JS`, written by the article build as the file
`/site/theme.js`, which every page loads with a parser-blocking `<script src>` before its sheet
(this build puts the tag into the shell pages at `<!--ORDPAR_HEADJS-->`). The shell pages load one
sheet, `/site/shell-pages.css` (`article.css`, `inflection.css`, `shell.css`, in that order), and
one blocking script, `/site/shell-pages.js` (`personal.js`, `lookup.js`, `offline.js`,
`install.js`, `shell.js`); the search page and 404 add their deferred `inflection.js`, `article.js`
and `mini.js`, `/settings/` its `settings.js`, `/favourites/` and `/history/` `personal-page.js`.
The article build writes all the combined files (`page.COMBINED`), without comments.

**The settings live on the device only** (decisions [19](../../docs/decisions.md#d19)):
`localStorage`, one key per setting, no cookies, no third party. **One table**, `shell.js`
`SETTINGS` (decisions [63](../../docs/decisions.md#d63)): a new setting is one entry
`{key, values, def, section}`, and under *Article* or *Loading* also `sub`, its subsection
(decisions [85](../../docs/decisions.md#d85)). The settings page draws them in the table's
order, with the words `settings.<key>` and `settings.<key>.<value>`. `values` lists the valid
stored values (any other reads as `def`); neither `section` nor `sub` is stored, so a setting can
move without losing a reader's choice. An entry with `layer: true` belongs to the Norwegian-only
layer and is kept out of the presets; one with `gate` is drawn only while its feature is live. The
table as it stands (the code is the authority if they differ):

| Key | Values | Default | Section / `sub` | What it does |
|---|---|---|---|---|
| `theme` | `system` \| `light` \| `dark` | `system` (follows `prefers-color-scheme`) | Style | class `nightMode` on `<html>` |
| `colour` | a colour scheme's id (`ordpar/sitegen/colours.py`) | the default scheme | Style | `data-accent="<id>"` on `<html>`; `colours.css()` styles each scheme, so an unknown value reads as the default |
| `lang` | `en` | the browser's language if the site has it, else `en` | Style | the interface language |
| `layout` | `ordpar` \| `ordbokene` | `ordpar` | Style | "Article layout": `ordbokene` ("Closer to ordbokene.no") puts an "Example" heading before each sense's own examples (the page script's `exheads`, and in a small article the mini script), the examples level with the sense's text, no quote bars; `ordpar-layout-ordbokene` (see [build-site.md](build-site.md)) |
| `nbonly`, `nbequiv`, `nbrows`, `nbhover`, `nbicon` | `off`\|`on`; `hidden`\|`shown`; `nbdef`\|`none`; `none`\|`nbdef`; `on`\|`off` | `off`, `hidden`, `nbdef`, `none`, `on` | Article / `nbonly` (layer) | *Norwegian only* (decisions [152](../../docs/decisions.md#d152)): the articles in Norwegian only; the English equivalents hidden or shown; what the rows' right side and the hovers show with them hidden; the header icon (see [build-site.md](build-site.md), Norwegian only) |
| `defs` | `both` \| `en` \| `no` | `both` | Article / `language` | a translated article's definition pairs: the Norwegian and English (Norwegian first), the English alone, or the Norwegian with the English behind a "Show English" cue; `ordpar-defs-en` / `ordpar-defs-no` |
| `examples` | `both` \| `no` | `both` | Article / `language` | the examples' English shown, or behind a reveal (decisions [111](../../docs/decisions.md#d111)) |
| `exeye` | `off` \| `on` | `off` | Article / `language` | the eye beside the headword (decisions [131](../../docs/decisions.md#d131)) |
| `exeyewhat` | `examples` \| `all` | `examples` | Article / `language` | what the eye hides: the examples' English, or every English line of its article but the etymology, each behind its own "Show English"; drawn only while `exeye` is on (decisions [186](../../docs/decisions.md#d186)) |
| `levels` | `off` \| `on` | `off` | Article / `language` | the CEFR level box after the headword and on each embedded set phrase, `ordpar-levels-on` on `<html>` (decisions [187](../../docs/decisions.md#d187)); For learners turns it on |
| `phraseorder` | `alpha` \| `level` | `alpha` | Article / `language` | the order of an article's embedded set phrases: alphabetical, as Bokmålsordboka has them, or by CEFR level, A1 first, each level alphabetical and a translated article's untranslated phrases still last; `ordpar-phraseorder-level` on `<html>`, which orders them only beside `ordpar-levels-on`, and drawn only while `levels` is on (decisions [188](../../docs/decisions.md#d188)); For learners chooses `level` |
| `exlimit`, `exmore` | `all` \| `1`…`10`; `on` \| `off` | `all`, `on` | Article / `language` | how many examples show under each sense (a drop-down), and whether a "Show N more examples" line opens the rest (decisions [112](../../docs/decisions.md#d112)) |
| `emph` | `no` \| `en` | `no` | Article / `language` | the emphasised line of a pair where both show ("Norwegian emphasized" / "English emphasized"): the main style and the links, the other line faded and plain; never under `defs = no`; `ordpar-emph-no` |
| `subsenses` | `defs` \| `en` | `defs` | Article / `language` | "In English only": under `defs = both` a real subsense shows its English alone with the links; `ordpar-subsen-en` |
| `formulas` | `both` \| `en` \| `no` | `both` | Article / `language` | the language of a formula line ("used as an adverb:") whatever `defs` says, and with `no` the compound lists' labels; `ordpar-formulas-no` / `-both` |
| `ety` | `en` \| `no` \| `both` | `en` | Article / `language` | the etymology line's language in every `defs` and `mini` setting; `ordpar-ety-no` / `-both` |
| `labels` | `en` \| `no` | `en` | Article / `language` (layer) | the labels inside the article frame (headings, buttons, word class, the tables' words) in English or Norwegian |
| `infl` | `button` \| `open` | `button` | Article / `inflection` | ordbokene's "Always show inflection tables" |
| `pframes` | `on` \| `off` | `on` | Article / `inflection` | the participle frames; `ordpar-pframes-off` |
| `xref` | `mini` \| `page` | `mini` | Article / `xref` | `page`: a cross-reference click opens the target's page |
| `peek` | `on` \| `nb` \| `off` | `on` | Article / `xref` | the hover peek: the translation, the first Norwegian definition (`ordpar-nbo-hovnb`, read from the target's `snip/` file), or none (`ordpar-peek-off`) |
| `mini` | `article` \| `both` \| `en` | `article` | Article / `mini` | what a translated target's small article shows; `article` resolves to `en` when `defs` is `en`, else `both`; `ordpar-mini-en` when the RESOLVED value is `en` |
| `minicontent` | `full` \| `slim` | `full` | Article / `mini` | how much a small article keeps of its target's senses (`mini.js` `cut`); `ordpar-minicontent-slim` |
| `nestminis` | `second` \| `inplace` \| `stacked` \| `off` | `second` | Article / `mini` | a link inside a small article: its small article in a second box, in the same box, in a box of its own each time, or its whole article (`mini.js` reads it) |
| `minispacing` | `article` \| `compact` | `article` | Article / `mini` | the small article's spacing; `ordpar-minispacing-compact`. A stored value stays as stored |
| `minitext` | `article` \| `smaller` | `article` | Article / `mini` | the small article's text sizes |
| `miniscroll` | `on` \| `off` | `on` | Article / `mini` | a tall small article scrolls inside its box on a computer; `ordpar-miniscroll-off` |
| `minihw` | `link` \| `article` | `link` | Article / `mini` | the small article's headword: the body's underlined link look, or the article headword's; `ordpar-minihw-article` |
| `audiospeed` | `recorded` \| `90` | `recorded` | Article / `audio` | the speed of the sound icons' clips, the recordings' own or 90 % with the pitch kept (`audio.js`) |
| `listview` | `forms` \| `multi` \| `on` \| `off` | `forms` | Search | the results: `forms`, the list when the search finds several articles as headwords or any article through an inflected form; `multi`, only for several headword hits; `on` always; `off` never (§ 6). `lookup.js` `useList(mode, n, f)` with `f` = `formHits(res)`, which `ahead.js` asks too; `listMode` falls back to `forms` |
| `suggestrows` | `standard` \| `roomy` | `standard` | Search | the dropdown's row spacing, 35.2 px or 44 px; `ordpar-suggestrows-roomy` (§ 4 (2)) |
| `minifetch` | `point` \| `click` \| `page` | `point` | Loading, offline and your data / `loading` | when a linked article or page is loaded ahead (`ahead.js`, see [build-site.md](build-site.md), loading ahead): `point` after the pointer rests `REST_MS` (150 ms) on the link, or at a touch; `click` on the click alone; `page` what the page shows (the small articles' targets, the list view's and the favourites page's articles), idle-queued, every other link as `point`; `page` acts as `click` under the browser's data saver. It covers every control that opens an article, a page or a search of the site (the front page, word and form pages, the about pages, English searches, the suggestion and Recent rows, a row selected by keyboard once the selection has rested `REST_MS`, Random word), never a link to another site, an action, a link with `target` or `download` or to a place on the same page, or the English / Norwegian switch; and the sound icon's clip (`audio.js` `preload`, through `ordparAhead.mode`; under `click` none before a press), and the `snip/` file of the hover's first Norwegian definition (`mini.js` `nbPeek`; under `click` none, only a file the page already has). Words: "When a linked article or page is loaded": "When the pointer rests on its link" / "When its link is clicked" / "With the page", with a hint and a note per choice behind the "?" (`settings.minifetch.hint`, `settings.minifetch.<value>.note`); `ordpar-minifetch-click` / `-page` |
| `stats` | `on` \| `off` | `on` | Loading, offline and your data (gated) | the opt-out of the events (`events.js` reads it); drawn only while counting is live (`window.ORDPAR_COUNTING`, which the build writes into the settings page only while `events.js` `RECEIVER` is set) |
| `history`, `favourites` | a JSON array of entries (§ 6) | absent = empty | | `ordpar/site/personal.js`, the only writer. Not settings: "reset settings" leaves them, "delete stored data" clears them |

The shell stores each setting and mirrors it as a class or attribute on `<html>` exactly as the head
script does, on load and on change, then calls `window.ordparDefs()` when the page has it, so an
article already on screen updates in place without a reload.

**The settings page**, `/settings/` (decisions [63](../../docs/decisions.md#d63)), is a static
shell (`ordpar/site/settings.html`, written by this build, `noindex`, in the offline shell pack)
drawn by `ordpar/site/settings.js`: "← Back" (the browser's history when the reader came from this
site, else the front page), the heading, a row of jump links, and four sections: **Style** (theme,
colour, interface language, article layout); **Article**, in subsections (*Norwegian only*,
*Language*, *Inflection*, *Cross-references*, *Small articles*, *Audio*); **Search** (the list view,
the row spacing); and **Loading, offline and your data** (first its subsection *Loading*,
`minifetch`, then the offline copy, `offline.js` `section()`, see
[offline-app.md](offline-app.md); export and import, § 6; reset settings; delete stored data). Each
section is an `h2`; a subsection is an `h3` under it, drawn from the table's `sub` key
(`settings.sub.<sub>` its words), which also begins each of its fieldsets' accessible names
(`aria-labelledby`: "Small articles, Language"), so a short legend under its heading still reads
clearly on its own. A subsection whose strings have `settings.sub.<sub>.intro` gets that line under
its heading (`settings.js` `intro`: the page's grey `ordpar-note`, the subsection then a
`role="group"` named by its heading and described by the line). The controls are plain fieldsets of
radio buttons (or a drop-down where the entry has `control: 'select'`), no dialog. A change applies
at once and is stored; the controls are kept in step after a reset or an import without a redraw,
so the focus stays. The header's and the footer's Settings link here. The colour choices come from
`window.ORDPAR_COLOURS` (`colours.settings_json()`, put into the page by this build at
`<!--ORDPAR_COLOURS-->`), each with a swatch of its day and night accents and, for ordbokene's
maroon, a note ("The colour ordbokene.no uses. Ordpar is independent of ordbokene.no.").

**The hints, behind a "?"**, so the page does not grow long. A setting with anything to say gets
one "?" on its title line (in the legend, after the title's own span, which alone names the
fieldset): a real `<button>` named "About this setting: <subsection>, <title>"
(`settings.hintButton`), with `aria-expanded` and `aria-controls`. It opens a small box holding the
setting's own hint (`settings.<key>.hint`), then one line per choice that has a note
(`settings.<key>.<value>.note`, or a colour's own `note`), led by the choice's label in bold. The
box is an **overlay** inside the fieldset (placed by `settings.js` `hintPlace` under the title,
left-aligned with the "?" where it fits, never wider than the fieldset), so opening it moves nothing
on the page, and it stays inside a 360 px window. On a computer it shows while the mouse rests on
the "?" or the box, and a click keeps it open (a second click closes it); on a touch screen a tap
opens and closes it; a click or tap elsewhere, or Escape, closes it; one box at a time. **Once a
click or tap has opened the box, the click or tap outside that closes it does nothing else** (no
choice picked, no drop-down opened, no link followed, no small article opened; the next one acts as
usual). One mechanism serves every "?" box, `shell.js` `hintGuard`, which the settings' hints and
the articles' pronunciation "?" (the page script in `ordpar/sitegen/page.py`) use to pin their open
box. On the window, in the capture phase, a mouse press outside closes the box at once and its
mousedown, mouseup and click are swallowed; a finger closes it on lifting, the lift's touchend
cancelled and any click swallowed, while a finger that scrolls (`pointercancel`) leaves it open. A
press on another "?" only closes the open box. A box the mouse merely rests on is not pinned: a
click elsewhere closes it and acts as usual. The box is written into an always-present
`role="status"` region when it opens and emptied when it closes, so a screen reader reads it on
opening. The notes are also kept as hidden copies (`.ordpar-choice-note`), each radio's
`aria-describedby`. Tests: `ordpar/tests/test_ordpar_hints99.py`,
`ordpar/tests/test_ordpar_browser_outside124.py`.

**Colours.** The accent is the colour scheme's: `--ordpar-accent` is `var(--ordpar-maroon)` by day
and `var(--ordpar-tint)` under `.nightMode`, both set by `colours.css()` in `article.css`, which
every page links. The default scheme is Wine (`#6b0f2e` by day); the default's night colour is
always the tint `#e3b7c9`, whichever scheme is the default. The other schemes: Burnt orange
(`#b13a0b`, its own computed tint by night) and "ordbokene.no's maroon" (`#560027`, the only place
that colour appears, with ordbokene's black-and-white night and `#880e4f` link underlines). Every
other colour has a `.nightMode` partner from the project's night-mode palette. Apart from the
article, the frame is **the site's own** (decisions [12](../../docs/decisions.md#d12)): it
borrows nothing of ordbokene's look; only the article keeps ordbokene's anatomy. The footer is a
quiet band of its own (a light neutral ground, a hairline above, muted small text, the links in the
accent), with no logos.

**Accessibility baseline**: a skip link; a real combobox (`role="combobox"` + `aria-expanded` +
`aria-controls` + `aria-activedescendant`, a `role="listbox"` of `role="option"`, Arrow keys,
Home/End, Escape, Tab, Enter); a polite live region for the hit count; focus returned to the search
box after an in-place search; `lang="nb"` on every Norwegian string (the box, the suggestions, the
headword links); `aria-current="page"` on a header link that points at the current path.

**The receiver's events** (decisions [26](../../docs/decisions.md#d26),
[62](../../docs/decisions.md#d62), [104](../../docs/decisions.md#d104)):
`ordparShell.event(name, data)` hands a suggestion chosen (`pick`) to `events.js`, and `lookup.js`
`render` hands it a search the reader made (a hit, or a miss held until a similar word is chosen).
`events.js` alone decides whether anything is sent: nothing while its receiver address is empty, as
shipped (see [build-site.md](build-site.md) and [receiver.md](receiver.md)). Nothing else on any page
makes an external request.

## 8. Not built here, on purpose

* the page-view and failed-search events themselves: `events.js` and the receiver
  ([receiver.md](receiver.md)), § 7;
* wildcards, advanced search, full-text search, paging;
* the offline copy: `ordpar/build_offline.py` packs every file under `<out>/index/` into gzip packs by
  letter key, and the service worker answers the index's requests from them
  ([offline-app.md](offline-app.md)).

## 9. Word pages and form pages

Decisions [117](../../docs/decisions.md#d117). The code: `build_index.py` `page_plan` (which
searches get a page, and the canonicals), `write_index` (the browser's copy of the plan, § 3),
`write_word_pages` (the pages, the article pages' canonical, the sitemap);
`ordpar/sitegen/wordpages.py` (the address, the labels, the page's markup, title and description);
`lookup.js` `pagePath`, `pageFor`, `address`, `searchAddress`, `ordparSearch.wordPage`,
`answerInPlace`.

**Which searches get a page** (`page_plan`, over the shards in memory before they are written,
through the Python twin of `lookup.js`):

* **a word page** for every distinct search (the search's own `fold`: *Mars* / *mars* is one
  search) that matches a headword and whose FIRST SHOWN article (`first_shown`: translated before
  untranslated) is translated: about 23,300 pages, most with one article;
* **a form page** for every search that matches no headword, is an inflected form of at least one
  translated word, is IRREGULAR against at least one of those translated words (it begins neither
  with one of that word's spellings nor with one of them less a final *-e*, the stem at least two
  letters, tested against each word's own spellings: *tær* against *tå*, *bøker* against *bok* but
  not against *bøk*, of which it is a regular form), is seen at least 100 times in the frequency
  list (`read_freq`, `wordpages.MIN_FORM_COUNT`; without `--freq`, no form pages), and is not only a
  passive: about 2,350 pages;
* **no page** for a search that cannot be a folder name (`wordpages.unrepresentable`): a slash, a
  question mark, a full stop at the end, and, to fail safe, a full stop at the start, digits only
  (an article's own folder), a character Windows forbids, `#` or `%`, a space at either end, a
  reserved device name, or over 200 bytes. A dozen searches whose first article is translated fall
  here. Two searches a Windows file system would treat as one folder cannot arise (the fold is lower
  case), and the plan refuses a second one all the same.

**The address** is `/bm-en/<fold, percent-encoded>/`: lower case, NFC, every byte outside
`A-Z a-z 0-9 _ . - ~` encoded (`wordpages.word_path`, Python's `quote(…, safe="")`; `lookup.js`
`pagePath` encodes `! ' ( ) *` as well, so the two write the same string): `/bm-en/s%C3%A5/`,
`/bm-en/p%C3%A5%20kryss%20og%20tvers/`. GitHub Pages is case-sensitive: `/bm-en/Norge` answers 404,
and the 404 shell sends it on to `/bm-en/norge/`.

**What a page holds as built** (`wordpages.render`): the article page's frame (the head lines, the
canonical, `theme.js`, `/site/ordpar.css`, the header and footer, `/site/ordpar.js` deferred; not
the shell pages' larger frame), `<main data-ordpar-word="<fold>">`, and in its results the word as
the headline (`h1.ordpar-word-title`, in the word's own capitals: the stored spelling whose group
holds the first article), the results' heading with the count, the headword rows as the list view
draws them (headword with its numerals, word class, the *Norwegian only* tag on an untranslated
article (`_tag`), the snippet; the panel
holding the "Article page" link), and each "is an inflected form of" section with its rows and
labels, the rows in the index's stored order (§ 3; `Index.lookup` keeps it, as `lookup.js` does
when it redraws). The similar headwords are not built in; the script draws them. About 4 KB a page.

**In a browser** (`ordparSearch.wordPage`, started by `lookup.js` itself on any page whose `<main>`
carries `data-ordpar-word`, and by the 404 shell for `/bm-en/<word>`): the search for the word is
drawn as the search page draws it under the reader's settings, in place of the built rows (by
default one article whole, several as the list; then the inflected-form rows; then the similar
headwords). The page's own title stays (for one article, the article page's). Then the page answers
searches in place (`answerInPlace`: the box, Random word, a similar headword's link, Back and
Forward; `pushState` to the search's page, else to `/bm-en/#q=`).

**A later search always wins, and "Searching…" shows at once** (decisions
[138](../../docs/decisions.md#d138)). A search answered in place loads its query's index file
before it pushes its address and draws. Each such search (`answerInPlace` `go`, the search page's
`run`) takes the next number and drops its answer (no address pushed, nothing drawn) when a newer
search, or Back / Forward, has started meanwhile, as `render` drops its own stale answers
(`mine !== last`). Meanwhile, from the moment the search is made, the title and the box show the
new search and the results area holds only the "Searching…" line (`ordparSearch.searching`:
`results.searching` in a `p.ordpar-empty`, the element `render` draws, so one line throughout), on a
word page, the search page and the 404 shell alike. The previous answer is cleared then, not when
the new answer comes. Test: `ordpar/tests/test_ordpar_browser_race138.py`.

* **Opened from a search** (the box on another page, Random word, a similar headword's link,
  `/bm-en/#q=<word>` itself): the address carries the search after `#` (`/bm-en/så/#q=S%C3%A5`; a
  draw `…&random`, `searchAddress`), which `wordPage` reads as a search the reader made: recorded in
  History and counted (`render`'s `record`) exactly as the search page records one, unless it is a
  draw or reached by Back or Forward. The address is then cleaned to `/bm-en/så/`
  (`replaceState`), with the search kept in the entry's state (`{q, search: true}`), so a reload
  records again, as a reload of `/bm-en/#q=så` does.
* **Opened directly** (a link, a bookmark, a search engine): the search for the word, NOT recorded.

**The search goes to the page** (one rule, one source): `lookup.js` `pageFor(q)` folds the query
and reads its own shard's `p` / `pf` (the shard a search loads anyway); `address(q)` is the page or
`/bm-en/#q=<q>`. It is used by: `shell.js` `submit` on a page with no handler of its own (an article
page: `searchAddress`, a navigation); the search page's `run` (in place, `pushState`); the search
page's first load from `#q=<q>` when `q` has a page (`location.replace` to the page with the search
after `#`, a draw marked; a load by Back or Forward is answered in place); a word page's and the 404
shell's own searches (`answerInPlace`); Random word (`wireRandom`); the similar headwords' links
(`similar` returns each word's `page` from the `headwords/` or `tails/` file's `p`, or the shard's
`pf` for a rewrite that is an inflected form). `ordparSearch.wireFragmentLinks` answers a click on
such a link in place on a page that answers searches in place. Tests:
`ordpar/tests/test_ordpar_wordpages117.py` runs `pageFor` over every search (every headword's and
every inflected form's fold) against the folders the build wrote;
`ordpar/tests/test_ordpar_browser_wordpages117.py` checks the pages in a browser.

**Title, description, canonical:**

| The page | `<title>` | description | canonical | sitemap |
|---|---|---|---|---|
| one article (*hus*) | the article page's own ("hus (noun) — Norwegian–English dictionary"), read from its built page | the article page's own | itself; the ARTICLE page's canonical and `og:url` point to it (`patch_article`) | the word page; the article drops out |
| one article reached by several searches (*bru* / *bro*) | as above | as above | for every such page and the article: the page of the article's first spelling (the one its title begins with), else of its first spelling that has a page | only that page |
| several entries (*så*) | "så — Norwegian–English dictionary" (`strings["dictionary_name"]`) | "6 entries in the Norwegian–English dictionary: VI to sow · I the husk … · III so · IV so that · V then · II Norwegian only": each entry's numeral and what the suggestions show for it (the set-phrase box, else the snippet's first unit), "Norwegian only" for an untranslated one, in the suggestions' order (`result_order`) | itself; each article keeps its own | the word page and each translated article |
| a form (*tær*) | "tær — Norwegian–English dictionary" | "“tær” is an inflected form of: tå, noun (plural indefinite): toe · tære, verb (imperative): Norwegian only." | itself | yes |

Every word and form page is indexed (no `noindex`: each has a translated first article or a
translated word) and carries the link-preview tags (`head.social_tags`) with its own title and
description. The article build writes each article page with its own canonical and its "N more
entries for …" link to the word's SEARCH (`face.lemma_url`, `/bm-en/#q=<form>`); this build then
sets the canonical and that link where the plan says (`wordpages.patch_article`), on every article
page whose headword has a word page, in search or not. So **the order is fixed**: the article
build, then this build, then the offline bundles. An article build run alone (`--ids`) leaves its
pages self-canonical until this build runs again.

**The sitemap** (`write_word_pages`): home, About, Help, every word page that is its own canonical,
every form page, and every translated article page that kept its canonical (the article build's
list, `sitemap-articles.json` in the folder `.build` under `ordpar`): about 26,000 addresses, 1.6 MB. Past 50,000 the
build stops: a sitemap index would then be needed.

**Stale pages**: a word page an earlier build wrote that the plan no longer names (its first
article no longer translated, say) is removed: a folder under `bm-en/` that is not an id and whose
page carries `data-ordpar-word`.

**The form labels** (`wordpages.FormLabels`; the shape *tå* *noun* (plural indefinite)): the words
are `inflection.js`'s own `DEFAULT_STRINGS`, read from that file: the group, then the narrow
layout's qualifier ("indefinite", "definite"), "masculine / feminine" with its no-break space as the
wide header writes it; "passive infinitive" / "passive present" for the two passives the table does
not show; a bare participle that fills the "present perfect" column is labelled "perfect
participle"; several analyses within one word go in one label, each group once, in table order
("past, perfect participle masculine / feminine and neuter"). There are 34 distinct labels, and
every cell key has one. The rows show the label after the word class, in brackets
(`.ordpar-form-label`, the word class's size and grey, upright): `lookup.js` `articleItem` on the
search page, the 404 shell, the word and form pages and offline; `wordpages.form_rows` in the built
pages. `lookup` fetches `labels.json` with the first search that shows such a row.

**Offline**: word pages are not in the offline bundles. Offline, the service worker answers a
navigation to `/bm-en/<word>/` that the network cannot answer with the stored 404 shell
(`ordpar/root/sw.js` `route`: any `/bm-en/<…>` but an id's page), and the shell does what the page
does (`ordparSearch.wordPage`, the mark after `#` included); `labels.json` is in the `index-meta`
pack.
