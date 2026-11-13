# Detection scripts for Bokmålsordboka

Seven small scripts that each look for one kind of mistake in the *artikler* of
Bokmålsordboka, reading the JSON that the public API publishes
(`https://ord.uib.no/bm/article/<id>.json`). Each one writes its findings as a TSV file,
one finding per line, giving the *artikkel* id, a place inside the *artikkel* that a
reader can find, and the text at fault.

All the examples below come from a run over the whole dictionary on 2026-10-03 (a copy of
the API data taken on 2026-10-02: 91,618 published *artikler*). The output of that run is
not in this repository. To see the findings, run the scripts: `run_all.py` over the joined
articles file in `data/bokmalsordboka/` takes about two minutes.

The same scripts read Nynorskordboka (`https://ord.uib.no/nn/article/<id>.json`) when
given `--dictionary nn`; see [Nynorskordboka](#nynorskordboka) below.

## How to run them

You need Python 3, and nothing else: the scripts use only the standard library and never
go online. Keep the folder together, because every script imports `common.py` from it.

The commands in this README are run from inside this folder, `handover/checks/`. From the
repository's root folder, write the script's path instead, for example
`python handover/checks/run_all.py data/bokmalsordboka/bm-articles.jsonl OUTDIR` (join the
articles file first: [`data/bokmalsordboka/README.md`](../../data/bokmalsordboka/README.md)).

```
python dangling_sense_refs.py ARTICLES -o findings.tsv
python run_all.py ARTICLES OUTDIR          # all seven at once, plus OUTDIR/summary.txt
```

`ARTICLES` is either a directory of `<id>.json` files, saved exactly as the API returns
them, or a JSONL file with one *artikkel* per line. Each script has a `--help` that says
what it finds and what each column means. By default the scripts skip any *artikkel*
whose `status` is not 8; `--include-unpublished` reads every *artikkel*. A one-line
summary goes to the screen: *artikler* read, *artikler* skipped, findings and the time
taken.

**How a place is written.** `betydning 3 (definisjon id 7), forklaring 1` means the first
explanation in the third *betydning*, whose definition node has `id` 7 in the JSON.
`betydning 2.1` is the first sub-*betydning* under *betydning* 2. The other places are
`eksempel N`, `etymologi, ledd N` and `oppslagsord N`. The *betydning* number follows
ordbokene's own numbering, the number its own *henvisninger* carry, and the `id` is exact.
That includes one case where the number is not simply a count: when an *artikkel* has only
one *betydning* at the top and that one has sub-*betydninger* (a fixed expression's "Se:
…" over its senses, or a definition with "brukt som adjektiv" under it), ordbokene.no
numbers the sub-*betydninger* 1, 2, 3, and so do the scripts. The top *betydning* itself
has no number on the page; its text is written `overordnet betydning (definisjon id 2),
forklaring 1`, the text shown above the numbered ones.

**Fixed expressions.** A fixed expression is an *artikkel* of its own, and each
*artikkel* that lists it holds a copy of it (`sub_article`). The copies do not always
match the expression's own *artikkel*. The expression is checked in its own *artikkel*.
From a copy, the checks that read text or *henvisninger* (1, 3, 4, 5 and 7) read only the *forklaringer*
and *eksempler* that the expression's own *artikkel* does not have, word for word and
with the same *henvisninger*; if the expression has no *artikkel* of its own in the
input, they read all of the copy. So each mistake is still reported once, and a copy
that has gone its own way is read too. A finding in a copy carries the id and
*oppslagsord* of the *artikkel* that holds the copy, and its place begins with that
*artikkel* and the expression: `artikkel 48613, uttrykk "ringe inn" (133353), betydning
3 (definisjon id 4), forklaring 1`. The *betydning* number is the copy's own. Checks 2
and 6 look at the structure of each *artikkel*'s own *betydninger* and do not read the
copies. `--no-embedded` turns the copies off, for the output as it was before.

## Nynorskordboka

Every script takes `--dictionary nn` for an input of Nynorskordboka *artikler* (the default
is `bm`, Bokmålsordboka). This repository carries Bokmålsordboka's data only, so a run over
Nynorskordboka needs its *artikler* file from elsewhere. `run_all.py` passes the option to all
seven:

```
python run_all.py NN_ARTICLES OUTDIR --dictionary nn --bokmal BM_ARTICLES     --nynorsk-forms fullformer_2012.txt --bokmal-forms fullformsliste.txt
```

What changes with it:
- links point at Nynorskordboka's page, `https://ordbokene.no/nno/nn/<id>` (check 6);
- check 6 allows Nynorskordboka's linking words beside the *henvisninger*: "sjå", "og",
  "eller", "òg" and "også" (it writes "sjå" where Bokmålsordboka writes "se");
- check 7 turns round: it reads Nynorsk text against Nynorsk forms, and labels a word that
  is a Bokmål form and not a Nynorsk one `bokmal_form` (below). `--bokmal` gives the
  Bokmål *artikler* as the other dictionary, as `--nynorsk` does in the default mode.

Checks 1 to 5 read the two dictionaries the same way. A place is written with the same
words in both modes (`betydning`, `eksempel`, `uttrykk`, `hele artikkelen`), so that one
reading of the output fits both.

A run over Nynorskordboka on 2026-11-13 (the API data of that morning, 96,928 published
*artikler*; Norsk ordbank's lists for both languages) found: 402 findings of check 1 (219
`missing_definition_id`, 162 `target_not_published`, 13 `target_missing`, 8
`anchor_without_text`), 2 duplicate ids (check 2), 506 doubled spaces and 82 doubled
words (check 3), 227 quotation marks without a partner (check 4), 90 empty
*artikler* that others refer to (check 5), 4 loops (check 6: two `mutual` `bare` and two
`mutual` `own-examples`), and 9,761 word-form candidates (check 7: 2,709 `bokmal_form`
and 7,052 `unknown_form`; 7,265 of them marked `compound`).

## 1. References to a *betydning* that does not exist: `dangling_sense_refs.py`

**What it finds.** A *henvisning* (`article_ref`) carries a `definition_id`, but no
*definisjon* in the target *artikkel* has that id. The link cannot land on the intended
*betydning*.

The output also has three smaller finding types, kept separate: `anchor_without_text`
(the id exists, but its node has no explanation or *eksempel* of its own, because it only
holds sub-*betydninger* or fixed expressions); `target_not_published` (the target's
`status` is not 8); and `target_missing` (the target is not in the input at all).

**What it cannot find.** A *henvisning* that points at a *betydning* that exists but is
the wrong one. Those are in our separate list of mis-anchored *henvisninger*.

**Examples** (124 `missing_definition_id` in all):
- [pupp](https://ordbokene.no/nob/bm/46911), *betydning* 1: the *henvisning* "bryst"
  points at *bryst* (7850) with `definition_id` 5, but 7850 has no *definisjon* with id 5.
  Three more *artikler* make the same *henvisning*: brystmelk (70802), brystfager (109254)
  and kvinnebryst (120923).
- [etanol](https://ordbokene.no/nob/bm/13196), *betydning* 1: "vanlig alkohol, for eksempel
  brukt i rusdrikker" points at *alkohol* (808) with `definition_id` 4. The *definisjoner*
  in 808 have ids 3, 5 and 6.
- [isning, ising](https://ordbokene.no/nob/bm/27277): the *henvisning* "ising" points at
  *ising* (27240) with `definition_id` 4. 27240 has a single *definisjon*, with id 2.

## 2. Two *definisjoner* with the same id: `duplicate_definition_ids.py`

**What it finds.** Two *definisjon* nodes in one *artikkel* carry the same `id`. A
*henvisning* to that id cannot tell which *betydning* it means. There is one line per node,
so both copies can be found.

**What it cannot find.** An id that is unique but wrong.

**Examples** (two *artikler*, four lines):
- [gå](https://ordbokene.no/nob/bm/21740): id 5 is used by *betydning* 4 ("med særlig vekt
  på utgangspunktet el målet") and by *betydning* 15 ("utvikle seg i en viss retning").
- [uhørt](https://ordbokene.no/nob/bm/63992): id 4 is used by *betydning* 1 ("som ikke er
  hørt") and by *betydning* 2 ("helt uvanlig").

## 3. Doubled spaces and doubled words: `doubled_spaces_words.py`

**What it finds.** Two or more spaces in a row (`double_space`), and the same word twice in
a row (`doubled_word`), in *definisjon*, *eksempel* and *etymologi* text. Doubled spaces are
also looked for in the *oppslagsord*. A doubled space does not show on the web page, but
it is in the data.

**What it cannot find.** A word that is missing, or a doubled word with punctuation
between the two copies. Many doubled words are correct Norwegian ("ja ja", "det det
gjelder", "for for eksempel"), so every `doubled_word` finding needs a human reader. In this
run, 26 of the 55 were real mistakes. Latin names such as "Crex crex" are skipped.

**Examples** (538 doubled spaces, 55 doubled words; 4 of the spaces and 1 of the words
are in copies of fixed expressions, such as *kjøpe katta i sekken* in
[katte](https://ordbokene.no/nob/bm/29024): "bli␣␣lurt", where the expression's own
*artikkel* now reads "bli snytt"):
- [tårn](https://ordbokene.no/nob/bm/63550), *betydning* 1: "høy og smal (øvre) del av av
  byggverk".
- [panservernrakettkaster](https://ordbokene.no/nob/bm/44028), *betydning* 1: "bærbart
  våpen til bruk mot mot pansrede kjøretøyer".
- [være på post](https://ordbokene.no/nob/bm/126022), *eksempel* 1: "de har␣␣vært
  kontinuerlig på post helt siden ulykken" (two spaces after "har").

## 4. Quotation marks without a partner: `unmatched_quotes.py`

**What it finds.** In one text element (one explanation, one *eksempel*, or one part of an
*etymologi*), an opening ‘ “ or « with no closing mark (`unclosed_opening`), or a closing
mark with no opening mark (`unopened_closing`). It also finds two mismatched pairs, each
reported as its own type: a curly opening mark closed by a straight one, ‘…'
(`straight_close`), and the reverse, '…’ (`straight_open`).

**What it cannot find.** A quotation mark that is missing at both ends. A ’ written
directly after a letter is read as an apostrophe (as in "Johannes’ åpenbaring"), so a
closing mark that stands just after a word, with no opening mark at all, is not reported.

**Examples** (191 `straight_close`, 14 `unclosed_opening`, 2 `straight_open`,
1 `unopened_closing`):
- [grut](https://ordbokene.no/nob/bm/21259), *etymologi*: "besl med grus og grjót ‘stein"
  (the closing ’ is missing).
- [yen](https://ordbokene.no/nob/bm/69557), *etymologi*: "fra kinesisk ’rund ting, dollar’"
  (the opening mark is written as ’).
- [abscisse](https://ordbokene.no/nob/bm/67), *etymologi*: "av lat. abscissa (linea)
  ‘avskåret (linje)'" (the closing mark is straight). In 187 of the 191 `straight_close`
  findings the mark is in an *etymologi*, and in most of them it comes straight after a
  ")" or a "-".

## 5. Empty *artikler* that other *artikler* refer to: `empty_cited_articles.py`

**What it finds.** An *artikkel* with no *definisjon* text, no *eksempel* and no fixed
expression, which at least one other published *artikkel* refers to. A reader who follows
the *henvisning* finds only the *oppslagsord*. The output gives the number of citing
*artikler* and up to five of them.

A *henvisning* in a copy of a fixed expression counts as made by the *artikkel* that
holds the copy, when the expression's own *artikkel* does not make it.

**What it cannot find.** An empty *artikkel* that nothing refers to. Those are left out on
purpose: of the 722 empty *artikler* in this run, 69 are referred to.

**Examples:**
- [trostefamilie](https://ordbokene.no/nob/bm/123200): empty, and referred to by five
  *artikler*: måltrost, nattergal, svarttrost, trost and trostefugl.
- [alkoholmisbruk](https://ordbokene.no/nob/bm/827): empty, and referred to by drukkenskap
  and misbruk.

## 6. *Henvisninger* that lead back to where the reader started: `sense_ref_cycles.py`

**What it finds.** Chains of *betydninger* whose explanations contain nothing but
*henvisninger*, which send the reader back to the *artikkel* they started in.
Abbreviations such as "jf" and the words "se", "og", "eller" and "også" are allowed
alongside the *henvisninger*, and so are *eksempler*. Each loop is reported once, on one
line, which names every step: the *oppslagsord*, the *artikkel* id, the *betydning* number,
the definition id and the link. There are three types:
- `mutual`: two *betydninger* that refer only to each other. A reader sent from either
  one is sent straight back.
- `returns-other-sense`: a chain through one other *artikkel* that comes back to a
  different *betydning* of the starting *artikkel*. The reader is sent away and then back
  home, and the visit adds nothing.
- `longer-loop`: the same through two or more other *artikler*, coming back either to the
  starting *betydning* or to another one.

A chain is followed only while the reader has nowhere else to go. Every *betydning* on it
before the return must be made only of *henvisninger*, and all of them must point at one
*artikkel*. A *henvisning* to a whole *artikkel* is followed only if no *betydning* in
that *artikkel* has text of its own. The chain stops, and nothing is reported, as soon as
it reaches a *betydning* with its own *definisjon* text. The *betydning* it returns to
may have text, and in the *blunke* case it does. For `mutual` the old rule is kept: a
*henvisning* to a whole *artikkel* counts as reaching each of its *betydninger*.

**Split by *eksempler*.** Every finding is also marked `bare` or `own-examples`.
- `bare`: no *betydning* on the loop that is only *henvisninger* has an *eksempel* of
  its own.
- `own-examples`: at least one does. The reader then finds some lexicographic
  information there, though no *definisjon*.

The *betydning* the loop returns to is not counted. The last column names each
*betydning* that has *eksempler* and how many. The output lists `bare` before
`own-examples` within each type.

**What it cannot find.**
- Loops where one step also refers somewhere else, as synonym lists do: "*kontroll*:
  tilsyn, oppsyn, overvåking", and "*tilsyn*: overvåking, kontroll, inspeksjon". If those
  steps were followed too, 122 more loops would be found (8 of them through two other
  *artikler*). Most are ordinary synonym definitions; the reader is given other words at
  every step. 13 of them start from a *betydning* that also names another word, but every
  other step leads only back. One example is *anstendighet* ("sømmelighet,
  skamfølelse") and *sømmelighet* ("anstendighet").
- A *henvisning* to a whole *artikkel* that has a *betydning* with text, even when
  another *betydning* there points back. There are two such cases.
  *[uforskyldt](https://ordbokene.no/nob/bm/63842)* 2 is "ufortjent", and
  *[ufortjent](https://ordbokene.no/nob/bm/63854)* 2 is "uforskyldt" (pointing at
  *uforskyldt* 1). But *ufortjent* 1 has its own text. The other case is
  *[vinterdrakt](https://ordbokene.no/nob/bm/68589)* 1 and
  *[vinterham](https://ordbokene.no/nob/bm/68604)* 2. If the *henvisning* meant the
  *betydning* that points back, it should name it.
- A *betydning* with any words of its own ("det samme som …") is not counted as
  *henvisninger* only.

`--max-articles` limits a chain to that many other *artikler* (10 by default). In this run,
no chain got past one other *artikkel*, and a limit of 50 found nothing more.

**Examples.** The run found two `mutual`, one `returns-other-sense` and no
`longer-loop`, the same three whether or not unpublished *artikler* are read. All three
are `own-examples`, so no loop is `bare`.
- `mutual`, `own-examples`: [allerede](https://ordbokene.no/nob/bm/868) is defined only
  as "alt", and *betydning* 3 of [alt](https://ordbokene.no/nob/bm/1372) only as
  "allerede". *allerede* has 4 *eksempler* ("jeg er allerede ferdig med halvparten"), and
  *alt* 3 has 1 ("han er alt reist").
- `mutual`, `own-examples`: [fotball](https://ordbokene.no/nob/bm/17346), *betydning* 2,
  is defined only as "fotballspill", and
  [fotballspill](https://ordbokene.no/nob/bm/116499) only as "fotball". *fotball* 2 has 3
  *eksempler*, and *fotballspill* has none.
- `returns-other-sense`, `own-examples`: [blunke](https://ordbokene.no/nob/bm/6606),
  *betydning* 2 (definition id 4), is only "blinke", which points at *betydning* 2 (id 4)
  of [blinke II](https://ordbokene.no/nob/bm/6446). That *betydning* is only "blunke",
  which points at *blunke* *betydning* 1 (id 2). So the reader who looks up *blunke* 2
  ends at *blunke* 1. *blunke* 2 has 1 *eksempel* ("blunke med lyset"), and *blinke* II 2
  has none.
- `bare`: none under the rule above. Of the 122 synonym-list loops the rule passes over,
  20 are bare. One is [magiker](https://ordbokene.no/nob/bm/36539) ("tryllekunstner,
  illusjonist") and [illusjonist](https://ordbokene.no/nob/bm/25839) ("tryllekunstner,
  magiker"). The only bare one among the 13 one-sided cases is
  [faen I](https://ordbokene.no/nob/bm/13773) ("djevelen / fanden, fan") and
  [fan II](https://ordbokene.no/nob/bm/13766) ("faen").
- `longer-loop`: none under the rule above. The nearest is a synonym ring that the rule
  passes over. [dyktig](https://ordbokene.no/nob/bm/11317) is "dugende / flink",
  [dugende](https://ordbokene.no/nob/bm/111811) is "dyktig / dugelig", and
  [dugelig](https://ordbokene.no/nob/bm/11102) is "dyktig / skikket".

## 7. Word forms that are not Bokmål: `word_forms.py`

(With `--dictionary nn`, word forms that are not Nynorsk: everything below holds with the
two languages swapped. The script collects Nynorskordboka's forms, and Norsk ordbank's
Nynorsk list with `--nynorsk-forms`; `--bokmal` and `--bokmal-forms` give the other
dictionary; the finding types are `bokmal_form` and `unknown_form`.)

**This script finds candidates for a human to read, not mistakes.** Most of what it
reports is correct: compounds and derivations with no *artikkel* of their own, foreign
words in *eksempler*, and Nynorsk in a quotation. Read it from the top.

**What it finds.** It collects every Bokmål word form the dictionary lists, from the
*oppslagsord* and the inflection tables. With `--nynorsk`, it collects every Nynorsk form
from Nynorskordboka as well. Norsk ordbank's full-form lists can be added with
`--bokmal-forms` and `--nynorsk-forms`. Norsk ordbank is the source of the dictionaries'
inflection tables, and Språkbanken at the National Library publishes it under CC BY. It
covers far more words than the dictionaries' *oppslagsord*, so it removes most of the
false findings. The lists the options name are Norsk ordbank's `fullformsliste.txt`
(Bokmål) and `fullformer_2012.txt` (Nynorsk), from Språkbanken. Neither list is in this
repository, and the figures under **Examples** below were made with Norsk ordbank.
The script then reads every word in *definisjon* and *eksempel* text,
never in *etymologi*:
- `nynorsk_form`: the word is a Nynorsk form and not a Bokmål form;
- `unknown_form`: the word is neither.

In a copy of a fixed expression, a word that occurs anywhere in the expression's own
*artikkel* is left to that *artikkel*, even when the copy's *forklaring* as a whole
differs, so the word is reported once.

The output is sorted so that the rarest words come first. It skips numbers, words with a
capital letter, words of one or two letters, abbreviations, and the words of a Latin name
after the genus.

**Latin names.** The API marks a scientific name as a `usage` item. When such an item has
the shape of a Latin name (a capitalised genus, then one to three lowercase words, with
"x", "×", "subsp." or "var." allowed between them), its words are skipped if the item
stands alone in its *forklaring* or if none of its lowercase words is a Bokmål form. So
"Sylvia atricapilla" and "Brassica oleracea var. botrytis" are skipped, even though
"sylvia" is a Bokmål form, while a Norwegian name of the same shape, such as "Det kaspiske
hav", is still read. In text without that markup, it skips the word after a capitalised
word that is not a Bokmål form ("Uria aalge"), a word after "x" or a rank abbreviation
inside such a name, and the third word of a name ("Fagus sylvatica atropunicea"). A
capitalised word that is a Bokmål form, such as the first word of a sentence, never starts
a Latin name, so the word after it is read. A misspelt epithet is skipped too: *hodekål*
has "Brassica olracea", where every other *artikkel* writes *oleracea*.

**The `mark` column.** It is empty or `compound`. `compound` means that the word splits
into two or three Bokmål forms of at least three letters each, with an optional *-s-* or
*-e-* between them ("saltvann-s-området"), and that no Bokmål form is one edit away from
it (one letter deleted, added or changed, or two letters next to each other swapped). The
second condition keeps the mark off misspellings that happen to split: "lasestråle" splits
into "lase" and "stråle", but it is one edit away from "laserstråle". A marked word is
probably a correct compound with no *artikkel* of its own. The row is never dropped. A
missing space can still hide behind the mark: "metalliskgrunnstoff" is marked.

**What it cannot find.** A misspelling that is itself a real word ("hvis" for "vis",
"stor" for "stort"), and anything in an *etymologi*.

**Examples.** These figures come from a run over every *artikkel* the API serves, 94,241
in all, unpublished ones included (`--include-unpublished`), with Norsk ordbank. It found
5,814 findings: 193 `nynorsk_form` and 5,621 `unknown_form`. They cover 4,858 different
words in 5,249 *artikler*, and 4,438 of the findings are marked `compound`. Seven of them
are in copies of fixed expressions, read since 2026-10-04: for example "beveglesen" in an
*eksempel* of *i utgangspunktet* as [utgangspunkt](https://ordbokene.no/nob/bm/65338)
holds it. In a reading of
20 findings from the earlier output, before the Latin-name rule and the mark, 6 were real
mistakes.
- [atomkjerne](https://ordbokene.no/nob/bm/3084), *betydning* 1: "sammensatt av protoner og
  nøytronar". "nøytronar" is Nynorsk, and the Bokmål form is "nøytroner".
- [nyregrus](https://ordbokene.no/nob/bm/41387), *betydning* 1: "små, harde partiklar i
  nyre og urinleder". "partiklar" is a Nynorsk form.
- [strafferettslig](https://ordbokene.no/nob/bm/57518), *eksempel* 2: "strafferettslig
  rekasjon" ("reaksjon").

## Licence

The scripts are under MIT-0, like the rest of the code in this repository: [`LICENSE`](../../LICENSE).
