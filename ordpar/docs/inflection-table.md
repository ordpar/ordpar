# The inflection table

This doc describes `ordpar/site/inflection.js` and `ordpar/site/inflection.css`, the renderer that
turns an article's paradigm data from Bokmålsordboka into inflection tables on the site, laid out
as ordbokene.no lays out its own. It holds the **closed table from cell tag to header and frame**,
the layout rules, and where the tables differ from ordbokene.no's.

The baseline is ordbokene.no's English-interface tables, as rendered: where no rule here decides,
the table does what ordbokene.no's does. The markup and the stylesheet are our own, written from
what ordbokene.no's tables show. The rules the renderer implements are site decisions
[21](../../docs/decisions.md#d21) (b–d), [22](../../docs/decisions.md#d22),
[24](../../docs/decisions.md#d24), [31](../../docs/decisions.md#d31),
[40](../../docs/decisions.md#d40), [102](../../docs/decisions.md#d102) and
[108](../../docs/decisions.md#d108).

## 1. The contract with the article page

```html
<link rel="stylesheet" href="/site/inflection.css">        <!-- inside /site/ordpar.css on an article page -->
<script type="application/json" id="ordpar-paradigm">[["bru",["0s2q","bru","brua","bruer","bruene"],…],…]</script>
<details class="ordpar-infl-toggle" hidden><summary>Inflection</summary>
<div class="ordpar-inflection" data-paradigm="ordpar-paradigm"></div>
</details>
<script src="/site/inflection.js" defer></script>          <!-- inside /site/ordpar.js on an article page -->
```

When the document is ready (`DOMContentLoaded`, or at once if it already is) the module renders
into every `.ordpar-inflection` whose `data-paradigm` names an embedded JSON block, and marks it
`data-ordpar-mounted`. It reads the block's `textContent`, falling back to `innerHTML`, so an
island inside a `<template>` (as in the Anki deck, whose editor deletes scripts) still renders. The
article page wraps the mount in a hidden "Inflection" toggle; the module shows the toggle only when
a table was rendered, so an uninflected word, or a reader without JavaScript, never sees an empty
button. The module also exposes

```js
window.ordparInflection = { render(lemmas, strings?) -> HTMLElement, mountAll(root?), fit(root?),
                            decode(island, shapes?), SHAPES,
                            TAGS, STRINGS, NB_STRINGS, FAMILIES, LEMMA_SORT }
```

**The island, in the compact schema.** The page carries only what `readRows` (§ 3) reads: per
lemma that has a paradigm with a form to show, `[lemma, paradigm, paradigm, …]`, and per paradigm
`[shape id, form, form, …]`, the forms of the cells that have both tags and a form, in the data's
cell order. A **shape** is the paradigm's tags, its `inflection_group` and its cells' tag lists
(each joined by `+`), `[tags, group, ["Sing+Ind", …]]`; its id is four base-36 characters of a
SHA-1 of the shape (`ordpar/sitegen/slim.py` `shape_id`), so it depends on the shape alone and a
page's bytes change only when its own paradigm does. The shapes live once, in the table `SHAPES` in
`inflection.js`, which the article build writes into the shipped file (`page.source`: the source's
`var SHAPES = {};` replaced) from every paradigm in Bokmålsordboka's data and the stored copies
(55 shapes, 4.8 KB, on the data of 25 September 2026). Two shapes on one id stop the build.

`decode(island, shapes?)` turns a compact island back into `{lemmas}` with exactly the fields
`readRows` reads (lemma, `paradigm_info[].tags`, `inflection_group`, `inflection[].tags`,
`word_form`); anything else (the full `{"lemmas": …}` or a list of lemma objects, as the test page
uses) passes through unchanged. Left out of the island: `from`, `standardisation`, `paradigm_id`,
`hgno`, the paradigms with `to` set (rule 7: none in the data), the untagged cells and the holes
(`word_form: null`), and a lemma with nothing left. **Where nothing would render** (no paradigm
with a tagged form, about 12 % of the pages, such as *ikke*) the page has neither the island nor
the Inflection toggle. `ordpar/tests/test_ordpar_slim.py` renders every fixture of the test page
(§ 8) both from the full data and from the island, and checks the two give the same tables.

`render` returns `<div class="ordpar-inflection-tables">` holding, per paradigm family, 0–2
*logical* tables, each in a `<div class="ordpar-infl-wrap ordpar-infl-wrap--wide">`, followed by
one `<div class="ordpar-infl-wrap ordpar-infl-wrap--narrow">` holding the family's single narrow
table with all its sections stacked (§ 4a point 6); the stylesheet shows one layout. **The page
must link `inflection.css` itself**: the module never injects a stylesheet, and without it both
layouts would show. No framework, no build step, ES2018 or lower, one file. The homograph,
part-of-speech and gender lines are the article page's, not the module's.

**Strings.** Everything the reader sees comes from one strings object (`ordparInflection.STRINGS`),
which a call can override: an interface language costs one object (decisions
[24](../../docs/decisions.md#d24) (1)). The terms are ordbokene.no's own English (decisions
[22](../../docs/decisions.md#d22)), plus **positive** (§ 3, comparable adverbs). Every word is
drawn in both languages: `NB_STRINGS` holds ordbokene.no's Norwegian terms (*entall*, *flertall*,
*ubestemt form*, *infinitiv*, *Gradbøying* …), each word written as two spans, `ordpar-w-en` and
`ordpar-w-nb` (with `lang="nb"` and `data-nosnippet`), and the site's stylesheet shows the Norwegian
under the *Norwegian only* layer or the labels setting, so switching needs no redraw (decisions
[152](../../docs/decisions.md#d152)). A key absent from `NB_STRINGS`, or the same in both, is
drawn once (the frames *en*, *ei/en*, *et*, *å*, *har*, *!* are Norwegian already). A caller that
passes strings of its own (another interface language) gets no Norwegian copy.

## 2. The data, measured

Counted over the whole of Bokmålsordboka's data (`data/bokmalsordboka/bm-articles.jsonl`, 94,238
articles, as of 20 September 2026):

| | |
|---|---:|
| paradigms (`data.lemmas[].paradigm_info[]`) | 169,471 |
| inflection cells | 921,368 |
| cells with `word_form: null` (grid holes, always untagged) | 125,177 (13.59 %) |
| cells with a form but no tags (the single cell of an uninflected paradigm) | 12,329 |
| distinct cell tags (non-empty) | **41** |
| distinct paradigm tag sets | 60 |
| distinct `inflection_group` values | 24 |
| distinct (paradigm tags → cell tag) pairs | 101 |
| distinct (paradigm tags → rendered cell tag set) combinations | **95**: 55 render a table, 40 render nothing (12,333 uninflected paradigms) |
| paradigms with `to` set (withdrawn from the standard) | **0** |
| paradigms with `standardisation: "REGISTERED"` | 9,035, every one an `EXPR`, so uninflected |

All 41 tags are in `TAGS`, and all 95 combinations render (checked by rendering each one through
the module). Nothing is dropped but the two passives of § 3 and the imperative of a `VERB_sPass`
paradigm.

A cell with **no tags** is either a grid hole keeping the shape of a paradigm's fixed slot count
(16 for `VERB_regular`, 7 for `ADJ_regular`, 4 for `NOUN_regular`) or the lone cell of an
uninflected paradigm. Neither is a form: the renderer keeps neither, and a paradigm left with no
tagged cell renders nothing at all (the article page then shows no table). **Cell order inside a
paradigm is not display order** (*spise* lists `Inf, Pres, Inf+Pass, Pres+Pass, Past, …`); the
column order below is.

## 3. The closed tag table

`family` decides which table a row's forms go to; a paradigm is assigned to the first family whose
tag set covers every tag it has (verb, noun, adj, advdeg, detadj, det, pron). The header is written
`group › qualifier` where the table has a group header, `label` where the column has a bold header
of its own. Frames (§ 5) are shown in *italics*. The cell counts are those of § 2's data.

### Nouns: family `noun`, one table, `NOUN_regular` (120,602 paradigms)

| cell tag | header | frame | cells |
|---|---|---|---:|
| `Sing+Ind` | singular › indefinite form | *en* / *ei/en* / *et* before, by the row's gender | 120,408 |
| `Sing+Def` | singular › definite form | — | 120,416 |
| `Plur+Ind` | plural › indefinite form | — | 120,558 |
| `Plur+Def` | plural › definite form | — | 120,548 |

Paradigm tag sets that reach it: `NOUN+Masc`, `NOUN+Fem`, `NOUN+Neuter`, `NOUN`, `ABBR+Masc`
(12 paradigms: abbreviations inflected as nouns), and one article tagged only `Masc`
(*jern- og metallindustri*, id 124989, a tagging slip in the data; it renders as a noun).

### Verbs: family `verb`, two tables, `VERB_regular` (19,044) + `VERB_sPass` (114)

Table (i), `Inflection`:

| cell tag | header | frame | cells |
|---|---|---|---:|
| `Inf` | infinitive | *å* before | 19,044 |
| `Pres` | present | — | 19,044 |
| `Past` | past | — | 19,044 |
| `<PerfPart>` | present perfect | *har* before | 19,042 |
| `Imp` | imperative | *!* after, tight | 19,032 |
| `Inf+<SPass>` | infinitive | *å* before | 114 |
| `Pres+<SPass>` | present | — | 114 |
| `Past+<SPass>` | past | — | 114 |
| `<PerfPart>+<SPass>` | present perfect | *har* before | 114 |
| `Imp+<SPass>` | imperative: **not shown** for a `VERB_sPass` paradigm | *!* after, tight | 110 |

The s-passive-only verbs (*finnes*, *synes*, …) have no other forms, so their tags share the verb
columns: one verb table, same headers. **A `VERB_sPass` paradigm shows no imperative**, though the
data has one (`NO_IMPERATIVE`), as on ordbokene.no, whose *finnes* 14771 and *aldres* 743 have no
imperative column (checked 18 October 2026); the form still counts in rule 4's comparison.

Table (ii), `Participles`:

| cell tag | header | frame | cells |
|---|---|---|---:|
| `Adj+<PerfPart>+Masc/Fem+Ind+Sing` | perfect participle › masculine / feminine | *+ noun* after | 19,030 |
| `Adj+<PerfPart>+Neuter+Ind+Sing` | perfect participle › neuter | *+ noun* after | 19,032 |
| `Adj+<PerfPart>+Def+Sing` | perfect participle › definite form | *den/det* before, *+ noun* after | 19,030 |
| `Adj+<PerfPart>+Plur` | perfect participle › plural | *+ noun* after | 19,030 |
| `Adj+<PresPart>` | present participle | none | 19,036 |

**Dropped, deliberately:** `Inf+Pass` (19,033 cells) and `Pres+Pass` (19,033), the periphrastic
passive infinitive and present (*spises*). ordbokene.no's table does not show them, and neither
does ours; the data is there should that change (§ 6).

### Adjectives: family `adj`, two tables, `ADJ_regular` (17,248) + `ADJ_masc/fem_fem` (24)

| cell tag | header | table | cells |
|---|---|---|---:|
| `Pos+Masc/Fem+Ind+Sing` | singular › masculine / feminine; *masculine* when the table also has a feminine column | (i) | 17,258 |
| `Pos+Fem+Ind+Sing` | singular › feminine | (i) | 24 |
| `Pos+Neuter+Ind+Sing` | singular › neuter | (i) | 17,258 |
| `Pos+Def+Sing` | singular › definite form | (i) | 17,257 |
| `Pos+Plur` | plural | (i) | 17,259 |
| `Cmp` | degrees of comparison › comparative | (ii) | 1,224 |
| `Sup+Ind` | degrees of comparison › superlative / indefinite form | (ii) | 1,213 |
| `Sup+Def` | degrees of comparison › superlative / definite form | (ii) | 1,213 |

No adjective cell takes a frame. Paradigm tag sets: `ADJ`, `ADJ+Ord` (ordinals), and one lemma
tagged `NOUN` carrying adjective cells (*løsningsorientert*, id 124935, another tagging slip; the
cells decide, so it renders as an adjective).

### Comparable adverbs: family `advdeg`, one table, `ADV_adj` (11 paradigms)

| cell tag | header | cells |
|---|---|---:|
| `Pos` | positive | 11 |
| `Cmp` | comparative | (shared with `adj`; no top header here) |
| `Sup` | superlative | 11 |

**No "degrees of comparison" header** over the three, wide or narrow, as on ordbokene.no: its *ofte*
(41859) is one header row positive | comparative | superlative at 1,500 px, and three rows
(positive, comparative, superlative) with no heading row at 500 px (checked 18 October 2026). The
adjective's comparison table keeps its header; `FAMILY_NO_TOP` drops it for `advdeg` only. The term
**positive** is ordbokene.no's own, read off the same table.

### Determiners: families `det` (`DET_regular`, 76) and `detadj` (`DET_adj`, 9)

| cell tag | header | family | cells |
|---|---|---|---:|
| `Masc+Sing` | singular › masculine | det | 27 |
| `Fem+Sing` | singular › feminine | det | 27 |
| `Neuter+Sing` | singular › neuter | det | 28 |
| `Plur` | plural | det / detadj | 71 |
| `Masc+Ind+Sing` | singular › masculine | detadj | 9 |
| `Fem+Ind+Sing` | singular › feminine | detadj | 9 |
| `Neuter+Ind+Sing` | singular › neuter | detadj | 9 |
| `Def+Sing` | singular › definite form | detadj | 9 |

`Plur` belongs to both; `detadj` is tried first, so a `Masc+Sing` paradigm lands in `det` and an
*egen*-shaped one in `detadj`. Both render the same table shape.

### Pronouns: family `pron`, one table, `PRON_regular` (10 paradigms)

| cell tag | header | cells |
|---|---|---:|
| `Nom` | subject form | 9 |
| `Acc` | object form | 10 |

### Everything else: no table

The remaining 40 combinations (`EXPR` (fixed expressions), `ADV`, `ABBR`, `ADP`, `SYM`, `INTJ`,
`PFX`, `COMPPFX`, `SCONJ`, `CCONJ`, `PROPN`, `VERB_uninfl`, `NOUN_uninfl`, `DET_simple`,
`PRON_simple`, and the handful of paradigms with an empty or nonsense tag list, `(none)` and
`false`) have a single untagged cell holding the lemma itself, or no cell at all. They are
uninflected: **the renderer emits no table**, and the page shows none.

### An unknown tag

A cell tag not in the table above (a future addition to the data) is **never silently dropped**:
the best-fitting family still renders its own columns, and each unrecognised tag becomes a column
of its own headed by the literal tag, marked `class="ordpar-unknown"` (dotted red outline,
`title="unknown tag: …"`). No such tag exists in the data today.

## 4. Layout rules

1. **Columns come from the table above**, in its order, and **a column with no form in any row is
   dropped**, not left empty (*være* has no masc/fem, definite or plural participle column;
   *tore/tørre* no imperative). A table left with no column is not rendered at all (*øvre*: no
   positive forms, so only the degrees-of-comparison table). Likewise **a row of the comparison
   table with no form in any cell is not drawn**: a paradigm with no comparison forms beside one
   that has them (*avsindig* 3768, *kjærlighetslaus* 119179; 15 articles in the data of 3 November
   2026). In the narrow layout its cell is left out of each comparison row and the others are not
   widened, as in ordbokene.no's rendered tables (decisions [162](../../docs/decisions.md#d162)
   (1)). The positive table keeps the row.
2. **Header rows.** A column may carry a *top* (spanning the whole table), a *group* (spanning the
   columns that share it, bold) and its own *label* (bold) and/or *qualifier* (italic, stacked under
   the label). The renderer emits only the levels in use: verbs get one bold row, pronouns one
   italic row, nouns a group row and a qualifier row, adjectives' table (ii) a top row and a
   label/qualifier row. A group whose columns have no header of their own reaches down into the
   column row with `rowspan="2"` (*bra*: plural; *spise*: present participle).
3. **One row per (lemma form × paradigm)**, in that order; several lemma forms give one row each,
   unlabelled (*en* / *én*) or labelled by gender when both axes apply (*bru/bro*).
4. **Alternative paradigms of one lemma.** This rule was derived from ordbokene.no's rendered
   tables alone. The paradigms of one lemma, gender and family are compared over **all** their
   cells, in all the family's tables, the hidden ones included (the passives, an s-passive's
   imperative), each cell as a set of forms. **An absent form is a difference.** Two rows become one
   when they differ in **exactly one cell and that cell is joinable**, the two rows' forms side by
   side in it. The joinable cells (`JOINABLE` in the module), each seen joining on ordbokene.no:
   the noun's indefinite and definite plural (*hus*: husa, husene); the verb's present and past,
   s-passive ones too, and its imperative (*vite*: veit, vet; *angi*: anga, angav; *avvæpne*); the
   perfect participle's masculine/feminine and the present participle (*angripe*, *avkle*); the
   adjective's feminine, neuter and definite form (*liten*); the determiner's feminine and neuter
   (*annen*, *en*); the pronoun's object form (*han*: ham, han). Identical paradigms are one row.
   The test is repeated on the joined rows until no pair is left, so *liten*'s eight paradigms end
   as one row. Where the outcome depends on which pair is joined first, the pair whose cell lies
   furthest along the tables goes first: the participle table after the main table, then the later
   column (*halsbord*, *korpus*, *klype*); ties in the data's order. Rows that differ in any other
   cell, or in two cells, **stay separate rows**, and the cells they share span them by rule 5:
   *geranium* (definite singular), *mange* (comparative), *lykkes* (the perfect participle), *sjøl*
   (the determiner's plural), *anse* (only the hidden passive differs: two rows, every cell spanning
   both), *bartre*, *finnes* (the present and the hidden imperative). A cell never seen differing
   alone on ordbokene.no (the infinitive, the participle's other forms, the superlatives, …) is
   treated as not joinable. Because the comparison is over the whole lemma, a split shows in
   **every** table of the lemma: *mange*'s plural *mange* spans two rows in the positive table, as
   on ordbokene.no. Checked against ordbokene.no's wide tables on 184 articles (2 November 2026):
   the shared rows identical in all 184, whole tables in 178; the other six differ in how a cell is
   drawn.

   **Inside a joined cell the forms are alphabetical** in Norwegian collation
   (`localeCompare(…, 'nb')`, `collate`; the rows' own order is rule 8's): *liten* lita, liten;
   *angi* anga, angav; *barnesko* barneskoa, barneskoene, never the data's paradigm order.
   **Each variant carries its own frames** (§ 5): *avvæpn!, avvæpne!*, *angrepen + noun, angrepet
   + noun*, as ordbokene.no prints them.
5. **Vertical merging.** After that, a run of adjacent rows with identical content in one column
   becomes one cell with `rowspan`. That is what makes *jente*'s plural span both genders, *tore*'s
   present *tør* span all four rows (across the lemma forms), and *bru/bro*'s plural repeat per row
   (the equal cells are not adjacent there). Frames are part of the comparison, and the row's
   **gender separates two cells only in the column whose frame depends on it**: *en jente* and
   *ei/en jente* stay apart, the plural beside them does not. An empty cell never merges.
6. **The gender row axis** (nouns only) appears when the rows have more than one gender: a corner
   header cell "gender" (italic), one bold row header per gender in the fixed order masculine,
   feminine, neuter (not the data's order), each spanning its rows. A one-gender noun has no axis.
   A three-gender noun (*snørr*) is the same axis with a neuter row; its two neuter paradigms differ
   in one cell only, so rule 4 joins them (snørra, snørrene), and its masculine and feminine plurals
   are equal, so rule 5 spans them.
7. **Historical paradigms**: a paradigm whose `to` is a date was withdrawn from the standard and is
   not rendered. Implemented and unexercised: no paradigm in the data has one.
8. **Row order, in ordbokene.no's collation**: æ sorts as "ae", ø as o and å as a, the accent
   breaking a tie only. That is the English collation, `localeCompare(…, 'en')` (`orderCollate` in
   `inflection.js`). It orders both the lemma forms and the rows inside a lemma. So *bartre*'s
   bartrær row comes before its bartre row, *tilby*'s tilbød before tilbydde, *klype*'s kløyp /
   kløpet before kløyp / klypt, and *trå*'s rows before *trø*'s, where Norwegian collation (æ, ø, å
   after z) would put them the other way. Checked on ordbokene.no's wide tables (2 November 2026)
   over the 184 articles of rule 4 and 20 more chosen for it: the row order matches in all.
   **Several lemma forms** are ordered alphabetically by lemma in that collation, as ordbokene.no's
   tables show: its *selvfordypelse* (50675) at 1,400 px is one table with the gender axis,
   masculine spanning 10 rows then feminine spanning 8, the ten lemma forms alphabetical inside each
   gender (selvfordjuping, selvfordjupning, selvfordypelse, …), not the article's own lemma order
   and not the headword line's; the article headed "bru, bro" orders its table bro, bru (checked 20
   September 2026). `LEMMA_SORT` at the top of the module (`'alphabetical'`) is the switch should
   this ever change.
   **Inside one lemma** (and gender), the rows of its alternative paradigms are alphabetical by
   their forms, not in the data's paradigm order: *trøtte*'s paradigms come in the data as
   trøttet/trøttete, trøttet/trøttede, trøtta, and the table (as ordbokene.no's, wide and narrow)
   shows trøtta, then trøttede, then trøttete; *tore* keeps torde before turte. The forms are
   compared **cell by cell in the order the paradigm lists its cells**, hidden passives included,
   not in the columns' order: on *rådgi* (110196), the one article where the two readings differ,
   the rådgav / rådgivende row (passive *rådgies*) comes before the rådga, rådgav / rådgiende row
   (*rådgis*), though its past sorts after, as on ordbokene.no (checked 18 October 2026). **Each
   cell is compared by its first form**: *gyve*'s gjøv, gøyv / gjøvet row comes before its gjøv /
   gyvd row, as on ordbokene.no, where comparing the cells' joined forms would put the shorter gjøv
   first (*gyve*, 21723, is the one article where those two readings differ). Should every first
   form tie, the joined cells decide; no article reaches that step. The order is computed once per
   lemma, so every table of it has the same rows in the same order.

## 4a. The narrow (transposed) layout

Where the wide table does not fit (see **The switch** below), the table is **transposed**, as
ordbokene.no's is on narrow screens: the row axis becomes the column axis. *jente* at 500 px, row by
row, as ordbokene.no shows it and as the renderer emits it:

```
[ (empty) ] [ masculine ] [ feminine ]
[ singular                      colspan 3 ]
[ indefinite form ] [ en jente ] [ ei/en jente ]
[ definite form   ] [ jenten   ] [ jenta       ]
[ plural                        colspan 3 ]
[ indefinite form ] [ jenter           colspan 2 ]
[ definite form   ] [ jentene          colspan 2 ]
```

The shape, in general:

1. **The genders become column headers**, one per gender, each spanning its lemma rows
   (*selvfordypelse*: masculine colspan 10, feminine colspan 8, 19 columns in all). The corner cell
   is empty on ordbokene.no; ours carries the word "gender" visually hidden, for a screen reader.
   With no gender axis there is no header row at all: the body columns are the unlabelled
   lemma/paradigm rows (*en/én*, *tore/tørre*).
2. **Each column group becomes a row group**: a full-width heading row (`singular`, `plural`,
   `perfect participle`, `degrees of comparison`), then one row per column under it, headed by that
   column's own qualifier. A group with a single column that has no header of its own is a heading
   row too, over a row whose header cell is empty to the eye (its name kept visually hidden for a
   screen reader): `plural` for *bra* and *noen*, `present participle` for *spise* and *trøtte*.
3. **Verbs and pronouns transpose the same way**: the tense names run down the first column as bold
   row headers, the lemma × paradigm alternatives across. For *tore, tørre*: infinitive *å tore* /
   *å tørre* each spanning 2 columns, present *tør* spanning all 4, past and present perfect one
   cell per column, and no imperative row because there is no form. The **participle table's**
   narrow layout follows the same rule, **without frames**: ordbokene.no's narrow participle cells
   are the bare forms (*tretta*, not *den/det tretta + noun*), while its narrow verb rows keep *å*,
   *har* and *!* (checked 24 September 2026; decisions [44](../../docs/decisions.md#d44)).
   `fillCell(…, plain)`. The narrow row headers may wrap at a space (*masculine /* over *feminine*,
   a no-break space before the slash). A verb with many participle variants is still wider than a
   phone (*trøtte*: 515 px in a 468 px box at a 500 px window; ordbokene.no's is likewise wider than
   its box) and scrolls.
4. **The spans are the same numbers**, read along the other axis: a run of adjacent rows with equal
   content is a `rowspan` wide and a `colspan` narrow, computed once, so the two layouts cannot
   disagree. *jente*'s plural merges across the two gender columns; *selvfordypelse*'s plurals do
   not, because the equal cells (masculine and feminine *selvfordjupinger*) are ten columns apart.
5. **The narrow row headers use ordbokene.no's shorter terms**: `indefinite` / `definite` where the
   wide layout says `indefinite form` / `definite form` (*geranium*; *mange* "superlative
   indefinite"), and `masculine/ feminine` (no space before the slash, an ordinary space after it,
   so the header can wrap after the slash) where the wide header is `masculine` + no-break space +
   `/ feminine` (*trøtte*). ordbokene.no's wide tables keep the long terms (checked 19 October
   2026), and so do ours. Three keys in the strings object, `indefiniteNarrow`, `definiteNarrow`,
   `mascFemNarrow`, are swapped in by `NARROW_STRINGS` for the narrow row headers only; an interface
   language translates them like any other key.
6. **Rule 4's split rows transpose like any other**: *mange*'s comparative is two columns, *fler* |
   *flere*, with the superlatives spanning both; *geranium*'s definite singular two columns,
   *geranien* | *geraniumen*, the rest spanning; *trøtte, trette* 3 + 3 columns; *ofte* three rows,
   positive / comparative / superlative, no heading row (§ 3). Cells, spans and header terms match
   ordbokene.no's narrow tables (checked at 500 px, 18 and 19 October 2026); the one difference is
   the visually hidden name in a bare section's row header (point 2, § 6).

   **One narrow table per paradigm family.** ordbokene.no's narrow layout is a single `<table>`, its
   sections stacked inside it (*mange*: plural, then degrees of comparison; *trøtte, trette* and
   *avvæpne*: the tenses, then perfect participle, then present participle), so the label column
   and the column widths are shared across the sections (checked at 500 px, 18 October 2026). The
   module does the same: the wide tables stay one per logical table, and the narrow table holds
   every section of the family, in the wide tables' order, under one gender header row when there
   is an axis. Every logical table of a family has the same rows (rule 4), so the column count is
   the same throughout. The caption is "Inflection" when it holds more than one logical table,
   otherwise that table's own; the participle sections stay frameless (point 3).

**The switch is measured fit** (decisions [102](../../docs/decisions.md#d102)). Both layouts are
rendered into the page; `inflection.js` `fit` shows the **wide** one wherever it fits the box it
sits in (the card's content box: the mount is capped there by `.ordpar-inflection{max-width:100%}`
in the site's stylesheet, `page.SITE_CSS`) and the **narrow** one where it does not, by the class `ordpar-fit-wide` or
`ordpar-fit-narrow` on `.ordpar-inflection-tables`.

**The stacked step** (decisions [108](../../docs/decisions.md#d108)). Each wide table in turn
is shown **unwrapped** (its max-content width) where that fits the box, with no tolerance. Otherwise
its columns are **stacked one at a time until it fits, at each step the column whose stacking frees
the most width** (each column still whole stacked on trial in the table as it stands, the table
re-measured; ties go to the wider unwrapped column, then the leftmost). Space saved beats widest
first: a column that is wide for one long form can free little, and stacking it can then need
another. A column is the cells of one grid column with colspan 1: a rowspan header such as *present
participle* belongs to its column; a header spanning several columns (*perfect participle* over
four) is no column of its own, is never held whole, and wraps only if the columns under it are
together narrower than it. The table is drawn at its min-content width (`ordpar-infl--stacked`,
`width: min-content`) with the cells of the unstacked columns held whole (`ordpar-col-whole`,
`white-space: nowrap`), so an unstacked column keeps its unwrapped width, a stacked one takes its
stacked width, the table never passes its box and no column carries spare width.

Two measured cases (23 October 2026). *møte* II at a 995 px window (box 698.8 px, the table 700.6
px unwrapped) stacks only *masculine / feminine* (159.8 → 98.4 px), the table 639.1 px; with every
column stacked it is 467.7 px (widest first would stack *definite form*, 169.9 → 132 px, freeing
37.9 px against 61.5). On *brenne* I at a 745 px window (box 660.8 px, the table 711.5 px unwrapped)
space saved stacks *masculine / feminine* alone (650 px), where widest first would stack *definite
form* (673.6 px, still too wide) and then *masculine / feminine* as well (612.1 px). In a sample of
517 verbs, adjectives and nouns, 117 of 705 wide tables have some box width where widest first
stacks more columns.

The narrow layout comes only where some table does not fit with every column stacked. A stacked
cell breaks only where ordbokene.no's rendered tables break (measured on *møte* II, *angripe*,
*skrive*, *overraske*, *gammel*, *liten*, *vitenskapelig* and *vitenskapsmann*): between a form and
the words of its frame after it ("møtt +" over "noun", "den/det møtte +" over "noun"), after the
comma between variants, and at the spaces of a heading ("present" over "participle"; "masculine /"
over "feminine" by its no-break space); **never inside a form**, nor between a form and its frame
before it (*å*, *har*, *den/det*, *en*). In the wide table each variant is one `ordpar-form` span,
kept unbroken by `white-space: nowrap` except inside its `ordpar-frame-after` ("+ noun"); the narrow
table is untouched. ordbokene.no's own wide table, squeezed by a resize, fills its card instead, its
columns sharing the spare width, and breaks inside a word ("vitenskapsm" / "ann") rather than
overflow; ours does not follow it there.

The fit applies everywhere a table is drawn: the article page (`mountAll` fits each mount it
fills), a full search result, an opened list or favourites row; small articles carry no table. So
**no table ever passes its card**: a narrow table still too wide (*trøtte*'s on a 360 px phone)
scrolls sideways inside `.ordpar-infl-wrap`, as ordbokene.no's does. The choice is made at load and
**again whenever the box changes width** (a `ResizeObserver` on the mount, which also catches a
closed Inflection toggle opening: a closed one has no width to measure). The hidden table
(`display: none`) is out of the accessibility tree. The 48rem media rule in `inflection.css` is only
the layout before the first measurement. A page (or the test page's toggle) can still force one
layout with `.ordpar-force-wide` / `.ordpar-force-narrow` on an ancestor; those rules come after the
measured ones and win.

**What ordbokene.no does** (its rendered geometry, measured 23 October 2026): on a computer its wide
table loads **when the window is at least 1,024 px wide, whatever the table's or the card's width**.
*fange* III, *trøtte* and *vitenskapsmann* are all narrow at 1,022 px and wide at 1,024, and
*vitenskapsmann*'s 636 px wide table loads narrow in a 736 px card that would hold it. It keeps the
layout it loaded with through a resize, until a reload (or, on its results page, until the
Inflection toggle is closed and reopened). **In Android emulation** (a phone's viewport, touch and
user agent; 360, 390, 412, 430, 500, 670, 740 and 915 px, the same three articles) every table is
narrow, its card the window less 32 px (736 px at 915), and the narrow table runs past the card and
scrolls inside it where it is wider (*trøtte*'s 536 px table in a 328 px card at 360 px). Ours
deciding by fit is a deliberate difference (`docs/divergences.md`, The article page).

## 5. Frames

Frames are **on by default; the participle frames can be turned off** (decisions
[21](../../docs/decisions.md#d21) d, [31](../../docs/decisions.md#d31)): the device
setting `pframes`, ordbokene.no's "Show context for participle forms", on by default;
`ordpar-pframes-off` on `<html>` hides `.ordpar-frame--participle`, that is *+ noun* and *den/det*;
the others always show. A frame is grey italic beside the form, never part of it, in
`<span class="ordpar-frame">`. Frames are **not** `aria-hidden` (a screen reader should hear "å
spise") and are marked by class only. *+ noun* carries `lang="en"` inside the otherwise Norwegian
cell. The full list is in the tables of § 3: *en* / *ei/en* / *et*, *å*, *har*, *!*, *+ noun*,
*den/det*. The present participle takes none. The one exception is the **narrow participle table**,
which carries no frames at all, as ordbokene.no's does (§ 4a point 3).

**In a joined cell, every variant carries its own frames**: *avvæpn!, avvæpne!* wide and narrow,
*angrepen + noun, angrepet + noun* wide, as ordbokene.no prints them (checked 18 October 2026). Only
the imperative's *!* and the participles' *+ noun* ever meet a joined cell in the data: the cells
framed by *å*, *har*, *en* / *ei/en* / *et* and *den/det* are never joined (none is among rule 4's
joinable cells, and the infinitive's difference always brings a passive difference with it), so
ordbokene.no shows no case of them. The module frames every variant whatever the frame, the reading
that agrees with the two cases there are.

## 6. Differences from ordbokene.no, and open questions

**Where our tables differ from ordbokene.no's**

- `Pos+Masc/Fem+Ind+Sing` is headed "masculine" instead of "masculine / feminine" when the same
  table has a feminine column of its own (*liten*: liten / lita). No observation of ordbokene.no
  covers it; the alternative is two columns both headed "masculine / feminine".
- **A bare section's narrow row header carries its name, visually hidden** (*plural* for *mange* and
  *bra*, *present participle* for *trøtte*), where ordbokene.no's header cell is empty. A screen
  reader announces the row header with each cell, and an empty one leaves the form with no name; on
  screen the two are identical (§ 4a, point 2).
- The layout switches by measured fit, the wide table wherever it fits its card, stacked if need be;
  ordbokene.no's by the window, wide from 1,024 px at load (§ 4a). A table that does not fit
  unwrapped stacks its columns one by one, the one that frees the most width first, until it fits;
  ordbokene.no's, squeezed, fills its card and wraps every cell.

Not a difference, but a choice worth knowing: the periphrastic passives `Inf+Pass` / `Pres+Pass`
are dropped, as ordbokene.no drops them, though the data has them and a dictionary reader might
want *spises*.

**Open questions**

1. Should the dropped passive forms come back, as a sixth verb column or a note?
2. Each table's caption is visually hidden ("Inflection", "Participles", "Degrees of comparison").
   ordbokene.no shows no caption but does show a collapsible "Inflection" control, as ours does;
   whether the site wants a visible heading is the article page's call, not this module's.

## 7. Accessibility and palette

A real `<table>` per table with a `<caption>` (visually hidden, `.ordpar-vh`), `scope` on every
`<th>` (`col`, `colgroup`, `row`, `rowgroup`), `lang="nb"` on every form cell, and no `aria-hidden`
anywhere. Nothing is a layout table.

Palette (light / `.nightMode`, the site's night palette): header text inherits the page's colour,
on ordbokene.no's neutral `#f1f1f1` / `rgba(255,255,255,.06)` (decisions
[43](../../docs/decisions.md#d43)); muted (the frames and the "gender" corner) `#757070` /
`#b9b6b6`; borders `#d6d6d6` / `#656161`; form cells inherit the page's text colour, `#d9d6d6` at
night. Dark mode is `.nightMode` on an ancestor (`<html>`). The font is inherited:
`inflection.css` sets no family, except a monospace one for an unknown tag's header (§ 3).

## 8. The test page

`ordpar/test/inflection.html` renders every hard case one under the other, with a source label
printed under each table (wide and, where one exists, narrow), a **Layout** button cycling auto →
forced wide → forced narrow, and a "Toggle night mode" button. Serve `ordpar/` as a static root and
open `/test/inflection.html` (`fetch()` of `paradigms.json` does not work from `file://`). In
"auto" the page flips at 48rem (768 px): it draws with `render`, not `mountAll`, so nothing
measures, unlike the site, which decides by fit (§ 4a). The Layout button forces the wide or the
narrow tables at any width. Check both colour schemes after a change to the sheet.

The data is `ordpar/test/paradigms.json`, each article's `data.lemmas` copied unchanged from
Bokmålsordboka's data:

```
python ordpar/test/extract_paradigms.py --mirror data/bokmalsordboka/bm-articles.jsonl
```

23 articles: ten shapes observed on ordbokene.no, then *trøtte/trette*, *snørr*, *gå* and
*selvfordypelse*, then nine shapes that a survey of the whole data turned up (*finnes*, *liten*,
*egen*, *ofte*, *øvre*, *mange*, *løsningsorientert*, *vannkopper*, *spørre nytt*).
