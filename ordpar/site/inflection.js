/* ordpar — inflection-table renderer.
 *
 * Renders ordbokene-style inflection tables from an article's paradigm data
 * (data.lemmas[] of the ordbokene article JSON; the page embeds it in the compact
 * schema of § 3, `decode`, since 2026-10-20 — the verbatim lemmas are still read).
 *
 * Dependency-free, ES2018 or lower, one file. The stylesheet is separate:
 * <link rel="stylesheet" href="/site/inflection.css">
 *
 * Page contract (build A):
 *   <script type="application/json" id="ordpar-paradigm">[[lemma, [shape, form, ...], ...], ...]</script>
 *   <div class="ordpar-inflection" data-paradigm="ordpar-paradigm"></div>
 *   (the script deferred: /site/ordpar.js on an article page, which carries this file;
 *    /site/inflection.js on the search page)
 *
 * API: window.ordparInflection = {
 *   render(lemmas, strings?) -> HTMLElement,   // <div class="ordpar-inflection-tables">
 *   decode(island, shapes?) -> {lemmas},       // a compact island read back (section 3)
 *   SHAPES: { <id>: [tags, group, [cell tags]] },  // the site's shape table
 *   mountAll(root?),                           // what DOMContentLoaded calls
 *   TAGS: { <cell tag>: {...} },               // the closed tag -> header/frame table
 *   STRINGS: { ... },                          // the default (English) strings
 *   FAMILIES: [ ... ], LEMMA_SORT: 'alphabetical'
 * }
 *
 * Doc of record: ordpar/docs/inflection-table.md.
 */
(function (global) {
  'use strict';

  /* ------------------------------------------------------------------ *
   * 1. Strings. Every header and frame string lives here; an interface
   *    language costs one object (decisions 24 (1)).
   * ------------------------------------------------------------------ */

  var DEFAULT_STRINGS = {
    /* captions (visually hidden, one per table) */
    captionInflection: 'Inflection',
    captionParticiples: 'Participles',
    captionComparison: 'Degrees of comparison',
    /* column and row headers */
    indefiniteForm: 'indefinite form',
    definiteForm: 'definite form',
    singular: 'singular',
    plural: 'plural',
    masculine: 'masculine',
    feminine: 'feminine',
    neuter: 'neuter',
    mascFem: 'masculine / feminine',   /* no break before the slash: the wide header wraps it as "masculine /" over "feminine" */
    /* the narrow layout's shorter row headers, as ordbokene's narrow tables print
       them (live DOM at 500 px, 2026-10-19: geranium "indefinite" / "definite",
       mange "superlative indefinite", trøtte "masculine/ feminine" — no space
       before the slash, a break after it); see NARROW_STRINGS */
    indefiniteNarrow: 'indefinite',
    definiteNarrow: 'definite',
    mascFemNarrow: 'masculine/ feminine',
    gender: 'gender',
    infinitive: 'infinitive',
    present: 'present',
    past: 'past',
    presentPerfect: 'present perfect',
    imperative: 'imperative',
    perfectParticiple: 'perfect participle',
    presentParticiple: 'present participle',
    degreesOfComparison: 'degrees of comparison',
    positive: 'positive',
    comparative: 'comparative',
    superlative: 'superlative',
    subjectForm: 'subject form',
    objectForm: 'object form',
    /* frames (grey italic beside the form, never part of it) */
    frameMasc: 'en',
    frameFem: 'ei/en',
    frameNeuter: 'et',
    frameInfinitive: 'å',
    framePerfect: 'har',
    frameImperative: '!',
    frameAdjNoun: '+ noun',
    frameDefiniteParticiple: 'den/det',
    /* the unknown-tag marker (an unlisted cell tag is shown, never dropped) */
    unknownTag: 'unknown tag'
  };

  /* Site decisions 152 (Robin, 2026-10-30/31): the tables' words in NORWEGIAN, ordbokene's where
     its rendered pages show them (the lookup of 2026-10-30: entall, flertall, ubestemt / bestemt
     form, hankjønn, hunkjønn, intetkjønn, "hankjønn/ hunkjønn", infinitiv, presens, preteritum,
     presens perfektum, imperativ, perfektum partisipp, presens partisipp, "+ substantiv"); the rest
     are drafts. Every word below is drawn in both languages (`str` -> a pair, `el` -> two spans:
     `ordpar-w-en`, and `ordpar-w-nb` with `lang="nb"` and `data-nosnippet`, the copy the default
     hides, 154), the sheet showing the Norwegian under Norwegian only or the labels setting
     (`page.SITE_CSS`), so the table needs no redraw and nothing flashes. A key absent here, or the
     same in both, is drawn once (the frames en, ei/en, et, å, har, ! are Norwegian already). */
  var NB_STRINGS = {
    captionInflection: 'Bøyning',
    captionParticiples: 'Partisipper',
    captionComparison: 'Gradbøying',         /* ordbokene's word (*stor* 57372; 152's follow-up) */
    indefiniteForm: 'ubestemt form',
    definiteForm: 'bestemt form',
    singular: 'entall',
    plural: 'flertall',
    masculine: 'hankjønn',
    feminine: 'hunkjønn',
    neuter: 'intetkjønn',
    mascFem: 'hankjønn / hunkjønn',      /* the no-break space before the slash, as the English */
    indefiniteNarrow: 'ubestemt',
    definiteNarrow: 'bestemt',
    mascFemNarrow: 'hankjønn/ hunkjønn',
    gender: 'kjønn',
    infinitive: 'infinitiv',
    present: 'presens',
    past: 'preteritum',
    presentPerfect: 'presens perfektum',
    imperative: 'imperativ',
    perfectParticiple: 'perfektum partisipp',
    presentParticiple: 'presens partisipp',
    degreesOfComparison: 'gradbøying',       /* ordbokene's head (*stor* 57372) */
    positive: 'positiv',
    comparative: 'komparativ',
    superlative: 'superlativ',
    subjectForm: 'subjektsform',
    objectForm: 'objektsform',
    frameAdjNoun: '+ substantiv',
    unknownTag: 'ukjent merke'
  };

  /* ------------------------------------------------------------------ *
   * 2. The closed tag table: every cell tag the mirror contains, with the
   *    table it belongs to, its header and its frames. Computed over all
   *    94,238 mirror articles on 2026-09-20; the counts are in the doc.
   *
   *    family   which paradigm shape the tag belongs to
   *    table    'main' | 'participle' | 'comparison' | null (deliberate drop)
   *    order    column order inside that table
   *    top      a header spanning the whole table (level 1, bold)
   *    group    a header spanning the columns that share it (level 2, bold)
   *    label    the column's own bold header
   *    qual     the column's italic qualifier
   *    before / after   frame: {str: <strings key>, tight: <no space>}
   *                     {str: '@gender'} takes the row's gender (en/ei/et)
   * ------------------------------------------------------------------ */

  var TAGS = {
    /* --- nouns (NOUN_regular: 120,602 paradigms) --------------------- */
    'Sing+Ind': { family: 'noun', table: 'main', order: 1, group: 'singular', qual: 'indefiniteForm', before: { str: '@gender' } },
    'Sing+Def': { family: 'noun', table: 'main', order: 2, group: 'singular', qual: 'definiteForm' },
    'Plur+Ind': { family: 'noun', table: 'main', order: 3, group: 'plural', qual: 'indefiniteForm' },
    'Plur+Def': { family: 'noun', table: 'main', order: 4, group: 'plural', qual: 'definiteForm' },

    /* --- verbs (VERB_regular: 19,044; VERB_sPass: 114) --------------- */
    'Inf': { family: 'verb', table: 'main', order: 1, label: 'infinitive', before: { str: 'frameInfinitive' } },
    'Pres': { family: 'verb', table: 'main', order: 2, label: 'present' },
    'Past': { family: 'verb', table: 'main', order: 3, label: 'past' },
    '<PerfPart>': { family: 'verb', table: 'main', order: 4, label: 'presentPerfect', before: { str: 'framePerfect' } },
    'Imp': { family: 'verb', table: 'main', order: 5, label: 'imperative', after: { str: 'frameImperative', tight: true } },
    /* the s-passive-only verbs (finnes, synes, …) share those columns */
    'Inf+<SPass>': { family: 'verb', table: 'main', order: 1, label: 'infinitive', before: { str: 'frameInfinitive' } },
    'Pres+<SPass>': { family: 'verb', table: 'main', order: 2, label: 'present' },
    'Past+<SPass>': { family: 'verb', table: 'main', order: 3, label: 'past' },
    '<PerfPart>+<SPass>': { family: 'verb', table: 'main', order: 4, label: 'presentPerfect', before: { str: 'framePerfect' } },
    'Imp+<SPass>': { family: 'verb', table: 'main', order: 5, label: 'imperative', after: { str: 'frameImperative', tight: true } },
    /* the adjectival participles */
    'Adj+<PerfPart>+Masc/Fem+Ind+Sing': { family: 'verb', table: 'participle', order: 1, group: 'perfectParticiple', qual: 'mascFem', after: { str: 'frameAdjNoun' } },
    'Adj+<PerfPart>+Neuter+Ind+Sing': { family: 'verb', table: 'participle', order: 2, group: 'perfectParticiple', qual: 'neuter', after: { str: 'frameAdjNoun' } },
    'Adj+<PerfPart>+Def+Sing': { family: 'verb', table: 'participle', order: 3, group: 'perfectParticiple', qual: 'definiteForm', before: { str: 'frameDefiniteParticiple' }, after: { str: 'frameAdjNoun' } },
    'Adj+<PerfPart>+Plur': { family: 'verb', table: 'participle', order: 4, group: 'perfectParticiple', qual: 'plural', after: { str: 'frameAdjNoun' } },
    'Adj+<PresPart>': { family: 'verb', table: 'participle', order: 5, group: 'presentParticiple' },
    /* the bare perfect participle rides in the present-perfect column; the
       two periphrastic passives are dropped, as ordbokene drops them */
    'Inf+Pass': { family: 'verb', table: null, drop: 'ordbokene shows no passive column' },
    'Pres+Pass': { family: 'verb', table: null, drop: 'ordbokene shows no passive column' },

    /* --- adjectives (ADJ_regular 17,248; ADJ_masc/fem_fem 24) -------- */
    'Pos+Masc/Fem+Ind+Sing': { family: 'adj', table: 'main', order: 1, group: 'singular', qual: 'mascFem', qualIfFem: 'masculine' },
    'Pos+Fem+Ind+Sing': { family: 'adj', table: 'main', order: 2, group: 'singular', qual: 'feminine' },
    'Pos+Neuter+Ind+Sing': { family: 'adj', table: 'main', order: 3, group: 'singular', qual: 'neuter' },
    'Pos+Def+Sing': { family: 'adj', table: 'main', order: 4, group: 'singular', qual: 'definiteForm' },
    'Pos+Plur': { family: 'adj', table: 'main', order: 5, group: 'plural' },
    'Cmp': { family: 'adj', table: 'comparison', order: 1, top: 'degreesOfComparison', label: 'comparative' },
    'Sup+Ind': { family: 'adj', table: 'comparison', order: 2, top: 'degreesOfComparison', label: 'superlative', qual: 'indefiniteForm' },
    'Sup+Def': { family: 'adj', table: 'comparison', order: 3, top: 'degreesOfComparison', label: 'superlative', qual: 'definiteForm' },

    /* --- comparable adverbs (ADV_adj: 11) ---------------------------- */
    /* No "degrees of comparison" header over the three: ordbokene's ofte is
       positive | comparative | superlative, wide and narrow (decisions 40 (b),
       live DOM 2026-10-18). */
    'Pos': { family: 'advdeg', table: 'comparison', order: 1, label: 'positive' },
    'Sup': { family: 'advdeg', table: 'comparison', order: 3, label: 'superlative' },
    /* 'Cmp' is shared with the adjective family (FAMILY_EXTRA); the adverb
       drops its top header (FAMILY_NO_TOP) */

    /* --- determiners, adjectival (DET_adj: 9) ------------------------ */
    'Masc+Ind+Sing': { family: 'detadj', table: 'main', order: 1, group: 'singular', qual: 'masculine' },
    'Fem+Ind+Sing': { family: 'detadj', table: 'main', order: 2, group: 'singular', qual: 'feminine' },
    'Neuter+Ind+Sing': { family: 'detadj', table: 'main', order: 3, group: 'singular', qual: 'neuter' },
    'Def+Sing': { family: 'detadj', table: 'main', order: 4, group: 'singular', qual: 'definiteForm' },
    'Plur': { family: 'detadj', table: 'main', order: 5, group: 'plural' },

    /* --- determiners, regular (DET_regular: 76) ---------------------- */
    'Masc+Sing': { family: 'det', table: 'main', order: 1, group: 'singular', qual: 'masculine' },
    'Fem+Sing': { family: 'det', table: 'main', order: 2, group: 'singular', qual: 'feminine' },
    'Neuter+Sing': { family: 'det', table: 'main', order: 3, group: 'singular', qual: 'neuter' },
    /* 'Plur' is shared with the detadj family; see FAMILY_EXTRA */

    /* --- pronouns (PRON_regular: 10) --------------------------------- */
    'Nom': { family: 'pron', table: 'main', order: 1, qual: 'subjectForm' },
    'Acc': { family: 'pron', table: 'main', order: 2, qual: 'objectForm' }
  };

  /* Which tables each family renders, in order. resolveFamily() tries the
   * families in this order and takes the first whose tag set covers every
   * tag of the paradigm. */
  var FAMILIES = [
    { name: 'verb', tables: ['main', 'participle'] },
    { name: 'noun', tables: ['main'] },
    { name: 'adj', tables: ['main', 'comparison'] },
    { name: 'advdeg', tables: ['comparison'] },
    { name: 'detadj', tables: ['main'] },
    { name: 'det', tables: ['main'] },
    { name: 'pron', tables: ['main'] }
  ];

  var CAPTIONS = { main: 'captionInflection', participle: 'captionParticiples', comparison: 'captionComparison' };

  /* Tags a family accepts although TAGS files them under another family. */
  var FAMILY_EXTRA = { advdeg: ['Cmp'], det: ['Plur'] };

  /* Families whose columns carry no top header, whatever TAGS says (the
     shared Cmp keeps "degrees of comparison" for adjectives only). */
  var FAMILY_NO_TOP = { advdeg: true };

  /* The cells in which two paradigms of one lemma may differ and still share a row (section 4),
     each found on ordbokene's rendered tables (headless Edge, 2026-11-02; the lemmas and the
     reasons are in the blind-rewrite note, `merge-rule-derived.md`). Two paradigms that differ in
     ONE of these cells and in nothing else are one row, the two forms side by side in that cell:
     hus (Plur+Def husa, husene), vite (Pres veit, vet), angi (Past anga, angav), avvæpne (Imp),
     angripe (the participle's masculine/feminine), avkle (the present participle), liten
     (feminine, neuter, definite), annen, en (Fem+Sing ei, en), han (Acc ham, han). A difference in
     any other cell keeps them apart: geranium (Sing+Def), mange (Cmp), lykkes (the perfect
     participle), sjøl (the determiner's plural), anse (the hidden passive); so does a difference
     in two cells, joinable or not: bartre (bartre / bartrea against bartrær / bartrærne), finnes
     (the present and the hidden imperative). A cell never seen differing alone on ordbokene is
     left out (the infinitive, the participle's other forms, the superlatives, ...). */
  var JOINABLE = {
    'Plur+Ind': 1, 'Plur+Def': 1,                                        /* nouns */
    'Pres': 1, 'Pres+<SPass>': 1, 'Past': 1, 'Past+<SPass>': 1, 'Imp': 1,  /* verbs */
    'Adj+<PerfPart>+Masc/Fem+Ind+Sing': 1, 'Adj+<PresPart>': 1,
    'Pos+Fem+Ind+Sing': 1, 'Pos+Neuter+Ind+Sing': 1, 'Pos+Def+Sing': 1,  /* adjectives */
    'Fem+Ind+Sing': 1, 'Neuter+Ind+Sing': 1, 'Fem+Sing': 1,              /* determiners */
    'Acc': 1                                                             /* pronouns */
  };

  /* Inflection groups whose table shows no imperative, though the data gives one: the
     s-passive-only verbs (finnes, lykkes, synes). The form still counts when two paradigms are
     compared (section 4). */
  var NO_IMPERATIVE = { VERB_sPass: true };

  /* Norwegian collation, for the forms inside a joined cell (decisions 40
     (d)). */
  function collate(x, y) {
    return x.localeCompare ? x.localeCompare(y, 'nb') : (x < y ? -1 : (x > y ? 1 : 0));
  }

  /* The ROW order's collation, for lemmas and for the rows inside a lemma: ordbokene's, in
     which ae, oe and aa are not letters after z — æ sorts as "ae", ø as o and å as a, the
     accent breaking a tie only (bartrær before bartre, tilbød before tilbydde, trå before
     trø). That is the English collation (`localeCompare(…, 'en')`). Robin, 2026-11-02, code
     provenance decisions 9: "follow ordbokene" — it amends site decisions 45, whose rows were
     in Norwegian collation (ø, å after z); 45's ruling, ordbokene's order, stands. Checked against ordbokene's live tables on
     the 184 articles of the shared-row comparison and 20 more (the doc, § 4 rule 8). */
  function orderCollate(x, y) {
    return x.localeCompare ? x.localeCompare(y, 'en') : (x < y ? -1 : (x > y ? 1 : 0));
  }

  /* Row order when a row has several lemma forms. 'alphabetical' reproduces
   * ordbokene's own tables (bru/bro, tore/tørre, en/én, trå/trø — whose table
   * order is not the lemma order of the data), in `orderCollate`; 'data' keeps
   * the article's lemma order. See the doc, § Open questions. */
  var LEMMA_SORT = 'alphabetical';

  var GENDER_FRAME = { Masc: 'frameMasc', Fem: 'frameFem', Neuter: 'frameNeuter' };
  var GENDER_LABEL = { Masc: 'masculine', Fem: 'feminine', Neuter: 'neuter' };
  var GENDER_ORDER = ['Masc', 'Fem', 'Neuter'];

  /* ------------------------------------------------------------------ *
   * 3. Reading the paradigm data into rows.
   * ------------------------------------------------------------------ */

  /* The compact island (2026-10-20, the size report's item 9c; the doc, § 1): the page
     carries each paradigm as a SHAPE id and its forms, `[[lemma, [id, form, …], …], …]`,
     and the shapes — [paradigm tags, inflection group, [cell tags joined by "+", …]] — are
     this site-wide table, written in by the article build (`build_site.py`, from every
     paradigm in the mirror; `sitegen/slim.py` `compact_paradigm`). The source file carries
     an empty table: the test page and the tests pass their own, or the verbatim lemmas. */
  var SHAPES = {};

  /* A compact island -> the `data.lemmas` that `readRows` reads (only the fields it reads:
     lemma, paradigm_info[].tags / inflection_group / inflection[].tags / word_form). A
     paradigm whose shape the table lacks is skipped. Anything else (`{"lemmas": […]}`, or a
     plain list of lemma objects) is returned as it is. */
  function decode(data, shapes) {
    if (!(data instanceof Array) || !data.length || !(data[0] instanceof Array)) return data;
    var table = shapes || SHAPES, lemmas = [], i, j, k;
    for (i = 0; i < data.length; i++) {
      var lem = data[i], pars = [];
      for (j = 1; j < lem.length; j++) {
        var p = lem[j], shape = table[p[0]];
        if (!shape) continue;
        var cells = [], seq = shape[2];
        for (k = 0; k < seq.length; k++) cells.push({ tags: seq[k].split('+'), word_form: p[k + 1] });
        pars.push({ tags: shape[0], inflection_group: shape[1], inflection: cells });
      }
      lemmas.push({ lemma: lem[0], paradigm_info: pars });
    }
    return { lemmas: lemmas };
  }

  function familyTags(name) {
    var out = [], tag;
    for (tag in TAGS) {
      if (Object.prototype.hasOwnProperty.call(TAGS, tag) && TAGS[tag].family === name) out.push(tag);
    }
    return out.concat(FAMILY_EXTRA[name] || []);
  }

  function resolveFamily(tags) {
    var best = null, bestScore = 0;
    for (var i = 0; i < FAMILIES.length; i++) {
      var own = familyTags(FAMILIES[i].name), score = 0;
      for (var j = 0; j < tags.length; j++) if (own.indexOf(tags[j]) !== -1) score++;
      if (score === tags.length) return FAMILIES[i].name;
      if (score > bestScore) { bestScore = score; best = FAMILIES[i].name; }
    }
    /* No family covers every tag: the best-fitting one renders its columns and
       the tags left over become marked columns of their own (buildColumns) —
       an unknown tag is never silently dropped. */
    return best;
  }

  function columnFor(family, tag) {
    var col = TAGS[tag];
    if (!col) return null;
    if (col.family === family) return col;
    /* a tag shared between families (Cmp, Plur) keeps its spec */
    if (FAMILY_EXTRA[family] && FAMILY_EXTRA[family].indexOf(tag) !== -1) return col;
    return null;
  }

  /* One row = one paradigm of one lemma. cells: tag -> [word forms]. */
  function readRows(lemmas) {
    var rows = [], i, j, k;
    var list = (lemmas || []).slice();
    if (LEMMA_SORT === 'alphabetical') {
      list = list.map(function (lem, idx) { return { lem: lem, idx: idx }; });
      list.sort(function (a, b) {
        var x = String((a.lem && a.lem.lemma) || ''), y = String((b.lem && b.lem.lemma) || '');
        var c = orderCollate(x, y);
        return c !== 0 ? c : a.idx - b.idx;
      });
      list = list.map(function (w) { return w.lem; });
    }
    for (i = 0; i < list.length; i++) {
      var lemma = list[i] || {};
      var paradigms = lemma.paradigm_info || [];
      for (j = 0; j < paradigms.length; j++) {
        var par = paradigms[j] || {};
        /* rule 9: a paradigm withdrawn from the standard (to != null) is not
           rendered. No mirror paradigm has one as of 2026-09-20. */
        if (par.to) continue;
        var cells = {}, tags = [], gender = null, ptags = par.tags || [], hide = {};
        /* the forms this paradigm hides: an s-passive verb's imperative (NO_IMPERATIVE) */
        if (NO_IMPERATIVE[par.inflection_group]) { hide['Imp'] = true; hide['Imp+<SPass>'] = true; }
        for (k = 0; k < ptags.length; k++) {
          if (GENDER_FRAME[ptags[k]]) gender = ptags[k];
        }
        var infl = par.inflection || [];
        for (k = 0; k < infl.length; k++) {
          var cell = infl[k] || {};
          var ct = cell.tags || [];
          /* a cell with no tags is either a grid hole (word_form null, 13.6 %
             of all cells) or the single untagged cell of an uninflected
             paradigm — neither is a form this table renders */
          if (!ct.length || cell.word_form === null || cell.word_form === undefined) continue;
          var tag = ct.join('+');
          if (!cells[tag]) { cells[tag] = []; tags.push(tag); }
          if (cells[tag].indexOf(cell.word_form) === -1) cells[tag].push(cell.word_form);
        }
        if (!tags.length) continue; /* uninflected: render nothing (rule 8) */
        /* `cells` keeps every tagged form, the hidden ones too (the passives,
           an s-passive's imperative): rule 4 compares them all, as ordbokene
           does (anse: two rows that differ only in the passive anses /
           ansees). What a column shows is `shown(row, tag)`. */
        rows.push({
          lemma: lemma.lemma || '',
          lemmaIndex: i,
          gender: gender,
          family: resolveFamily(tags),
          tags: tags,
          cells: cells,
          hide: hide
        });
      }
    }
    return rows;
  }

  /* ------------------------------------------------------------------ *
   * 4. Merging alternative paradigms of one lemma into shared rows.
   *
   *    Two rows of the same lemma, gender and family become one when they
   *    differ in exactly one cell and that cell is JOINABLE. Every tagged
   *    cell is compared, the hidden ones too (an s-passive's imperative, the
   *    dropped passives: anse's anses / ansees keeps two rows), as sets of
   *    forms, a cell one row lacks counting as a difference. The joined cell
   *    holds both rows' forms in Norwegian collation (decisions 40 (d)). The
   *    test is repeated on the joined rows until no pair is left, so a lemma
   *    whose variants combine freely collapses to one row: liten's eight
   *    paradigms (feminine x neuter x definite), angripe's four (past x
   *    participle). Two identical paradigms are one row. Which pair is
   *    joined first: `pickPair`; the earlier row takes the later.
   * ------------------------------------------------------------------ */

  function sameForms(a, b) {
    a = a || []; b = b || [];
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) if (b.indexOf(a[i]) === -1) return false;
    return true;
  }

  /* The one cell two rows may share a row through: its tag; '' when the rows are
     identical (a paradigm listed twice: vannfilter); null when they stay apart. */
  function joinTag(a, b) {
    if (a.lemmaIndex !== b.lemmaIndex || a.gender !== b.gender || a.family !== b.family) return null;
    var seen = {}, all = a.tags.concat(b.tags), diff = null, i;
    for (i = 0; i < all.length; i++) {
      if (seen[all[i]]) continue;
      seen[all[i]] = true;
      if (sameForms(a.cells[all[i]], b.cells[all[i]])) continue;
      if (diff !== null) return null;   /* a second difference */
      diff = all[i];
    }
    if (diff === null) return '';
    return JOINABLE[diff] ? diff : null;
  }

  /* Where a row could be joined to two others through different cells, the outcome depends on
     which pair goes first (24 lemmas in the mirror, 2026-11-02). ordbokene joins through the
     cell furthest along the tables first: the participle table after the main one, and within a
     table the later column. halsbord (bord / border, borda / bordene in three paradigms) shares
     its definite plural and keeps "halsbord | halsborda" a row of its own; klype joins its
     participle's kløpen / kløpet before its past kløp / kløyp. Identical paradigms go first of
     all; ties in the data's order. */
  function joinRank(tag) {
    if (!tag) return Infinity;
    var spec = TAGS[tag];
    return spec ? (spec.table === 'main' ? 0 : 100) + (spec.order || 0) : 0;
  }

  function pickPair(cands) {
    var best = cands[0], q;
    for (q = 1; q < cands.length; q++) if (joinRank(cands[q].tag) > joinRank(best.tag)) best = cands[q];
    return best;
  }

  function mergeRows(rows) {
    var out = rows.map(function (r) {
      var hide = {}, h;
      for (h in r.hide) if (Object.prototype.hasOwnProperty.call(r.hide, h)) hide[h] = true;
      return { lemma: r.lemma, lemmaIndex: r.lemmaIndex, gender: r.gender, family: r.family,
               tags: r.tags.slice(), cells: copyCells(r.cells), hide: hide };
    });
    var i, j, k, tag, h, cands, pick, a, b;
    for (;;) {
      cands = [];
      for (i = 0; i < out.length; i++) {
        for (j = i + 1; j < out.length; j++) {
          tag = joinTag(out[i], out[j]);
          if (tag !== null) cands.push({ i: i, j: j, tag: tag });
        }
      }
      if (!cands.length) return out;
      pick = pickPair(cands);
      a = out[pick.i]; b = out[pick.j]; tag = pick.tag;
      if (tag) {
        if (!a.cells[tag]) { a.cells[tag] = []; a.tags.push(tag); }
        for (k = 0; k < (b.cells[tag] || []).length; k++) {
          if (a.cells[tag].indexOf(b.cells[tag][k]) === -1) a.cells[tag].push(b.cells[tag][k]);
        }
        a.cells[tag].sort(collate);
      }
      /* a form stays hidden only where both rows hide it */
      for (h in a.hide) if (Object.prototype.hasOwnProperty.call(a.hide, h) && !b.hide[h]) delete a.hide[h];
      out.splice(pick.j, 1);
    }
  }

  /* The forms a row shows in a column: none where its paradigm hides the tag
     (an s-passive's imperative). */
  function shown(row, tag) {
    return row.hide[tag] ? [] : (row.cells[tag] || []);
  }

  /* ------------------------------------------------------------------ *
   * 5. DOM helpers.
   * ------------------------------------------------------------------ */

  function el(name, cls, text) {
    var node = global.document.createElement(name);
    if (cls) node.setAttribute('class', cls);
    if (text !== undefined && text !== null && text !== '') put(node, text);
    return node;
  }

  /* Text into `node`: a string as it is, a pair (`str`, site decisions 152) as its two copies, the
     English and the Norwegian, nothing between (a space would show; the hidden one is never read). */
  function put(node, text) {
    var doc = global.document;
    if (typeof text === 'string') { node.appendChild(doc.createTextNode(text)); return; }
    var en = node.appendChild(doc.createElement('span'));
    en.setAttribute('class', 'ordpar-w-en');
    en.appendChild(doc.createTextNode(text.en));
    var nb = node.appendChild(doc.createElement('span'));
    nb.setAttribute('class', 'ordpar-w-nb');
    nb.setAttribute('lang', 'nb');
    nb.setAttribute('data-nosnippet', '');
    nb.appendChild(doc.createTextNode(text.nb));
  }
  /* A string's text, a pair's English (an attribute's text, a test's) */
  function plain(text) { return typeof text === 'string' ? text : text.en; }

  /* Site decisions 154 (Robin, 2026-10-31): what a search engine reads from the tables. A
     screen readers' label (`ordpar-vh`: the caption, a bare row's name) carries `data-nosnippet`
     from its making — Google reads the attribute only on a span, div or section, and never one
     a script adds to an element already in the page — so a caption's words sit in such a span.
     And a newline between the parts of a table (its row groups, rows, cells, a header cell's
     stacked label and qualifier, the tables' wrappers): separate on the page, one run of words to
     a text extraction without it ("infinitivepresent"); between table parts, and between blocks,
     a newline draws nothing. */
  function hiddenLabel(name, cls, text) {
    var node = el(name, cls);
    var span = name === 'span' ? node : node.appendChild(el('span'));
    span.setAttribute('data-nosnippet', '');
    if (text) put(span, text);
    return node;
  }

  function spaced(node) {
    var kids = node && node.childNodes, doc = global.document, i;
    if (!kids || !node.insertBefore || !doc || !doc.createTextNode) return node;   /* a stand-in */
    for (i = kids.length - 1; i > 0; i--) {
      if (kids[i].nodeType === 1 && kids[i - 1].nodeType === 1) {
        node.insertBefore(global.document.createTextNode('\n'), kids[i]);
      }
    }
    return node;
  }

  function spaceTable(t) {
    spaced(t);
    if (!t.querySelectorAll) return t;
    var parts = t.querySelectorAll('thead, tbody, tr, th');
    for (var i = 0; i < parts.length; i++) {
      /* a header cell only where it stacks a label over a qualifier (both blocks) */
      if (parts[i].tagName === 'TH' && !parts[i].querySelector('.ordpar-th-qual')) continue;
      spaced(parts[i]);
    }
    return t;
  }

  function str(strings, key) {
    if (!key) return '';
    var en = Object.prototype.hasOwnProperty.call(strings, key) ? strings[key] : key;
    /* site decisions 152: with the Norwegian on hand (`render`'s `__nb`), a word that differs in
       Norwegian is a pair, drawn as two copies (`put`) */
    var nb = strings.__nb && Object.prototype.hasOwnProperty.call(strings.__nb, key) ? strings.__nb[key] : null;
    return nb && nb !== en ? { en: en, nb: nb } : en;
  }

  function copyCells(cells) {
    var out = {}, k;
    for (k in cells) if (Object.prototype.hasOwnProperty.call(cells, k)) out[k] = cells[k].slice();
    return out;
  }

  /* ------------------------------------------------------------------ *
   * 6. Building one table.
   * ------------------------------------------------------------------ */

  function buildColumns(family, tableName, rows) {
    var seen = {}, cols = [], unknown = [], i, t;
    for (i = 0; i < rows.length; i++) {
      for (t = 0; t < rows[i].tags.length; t++) {
        var tag = rows[i].tags[t];
        if (seen[tag]) continue;
        seen[tag] = true;
        var spec = columnFor(family, tag);
        if (!spec) {
          /* never silently dropped: an unlisted tag becomes its own column,
             headed by the tag itself and marked */
          if (tableName === 'main') {
            unknown.push({ tag: tag, unknown: true, order: 1000 + unknown.length });
          }
          continue;
        }
        if (spec.table !== tableName) continue; /* another table, or a drop */
        cols.push({
          tag: tag, top: FAMILY_NO_TOP[family] ? null : spec.top, group: spec.group, label: spec.label, qual: spec.qual,
          qualIfFem: spec.qualIfFem, before: spec.before, after: spec.after, order: spec.order || 0
        });
      }
    }
    cols.sort(function (a, b) { return a.order - b.order; });
    cols = cols.concat(unknown);
    /* rule 3: a column with no form anywhere is dropped, not left empty */
    cols = cols.filter(function (col) {
      for (var r = 0; r < rows.length; r++) {
        if (shown(rows[r], col.tag).length) return true;
      }
      return false;
    });
    /* "masculine / feminine" becomes "masculine" when the table also has a
       feminine column of its own (liten: liten / lita / lite / lille) */
    var hasFem = false;
    cols.forEach(function (c) { if (c.tag === 'Pos+Fem+Ind+Sing') hasFem = true; });
    if (hasFem) cols.forEach(function (c) { if (c.qualIfFem) c.qual = c.qualIfFem; });
    return cols;
  }

  function cellKey(row, col) {
    var v = shown(row, col.tag);
    if (!v.length) return null;
    /* The gender only separates two cells when the column's frame depends on
       it (en jente / ei/en jente never merge). Everywhere else a cell equal
       across adjacent gender rows is one cell: jente's plural spans both
       genders, while bru/bro's is repeated because its equal plurals are not
       adjacent. */
    var byGender = col.before && col.before.str === '@gender';
    return (byGender ? (row.gender || '') : '') + '\x00' + v.join('\x01');
  }

  /* The participle frames ("+ noun", "den/det") carry a class of their own, so the
     device setting `pframes = off` (ordbokene's "Show context for participle forms
     in the inflection tables", on by default — decisions 31) hides them with one class
     on <html>, `ordpar-pframes-off`; the other frames always show, as on ordbokene. */
  var PARTICIPLE_FRAMES = { frameAdjNoun: 1, frameDefiniteParticiple: 1 };
  function frameClass(key) {
    return PARTICIPLE_FRAMES[key] ? 'ordpar-frame ordpar-frame--participle' : 'ordpar-frame';
  }

  /* `plain`: the form alone, no frames — the narrow participle table (ordbokene
     drops "den/det" and "+ noun" there to fit a phone; Robin, 2026-09-24).
     Otherwise EVERY variant of a joined cell carries its own frames, as
     ordbokene prints them: "avvæpn!, avvæpne!", "angrepen + noun, angrepet +
     noun" (live DOM, wide and narrow, 2026-10-18; decisions 40, question 9).
     `keep` (the wide tables, decisions 108): each variant — its frame before, the form, its
     frame after — in one `ordpar-form` span, which inflection.css keeps unbroken in a wide
     table except at a space inside its frame AFTER (`ordpar-frame-after`), so a stacked cell breaks only where ordbokene's
     does: "møtt +" over "noun", "den/det møtte +" over "noun", and after the comma between
     variants; never inside a form, nor between a form and its å, har, den/det or en. */
  function fillCell(td, row, col, strings, plain, keep) {
    var v = shown(row, col.tag);
    if (!v.length) return;
    var span, key, i, doc = global.document, at;
    if (plain) {
      td.appendChild(doc.createTextNode(v.join(', ')));
      return;
    }
    var before = col.before ? (col.before.str === '@gender' ? GENDER_FRAME[row.gender] : col.before.str) : null;
    for (i = 0; i < v.length; i++) {
      if (i) td.appendChild(doc.createTextNode(', '));
      at = keep ? td.appendChild(el('span', 'ordpar-form')) : td;
      if (before) {
        at.appendChild(el('span', frameClass(before), str(strings, before)));
        at.appendChild(doc.createTextNode(' '));
      }
      at.appendChild(doc.createTextNode(v[i]));
      if (col.after) {
        if (!col.after.tight) at.appendChild(doc.createTextNode(' '));
        key = col.after.str;
        /* `ordpar-frame-after`: the one frame a wide cell may break inside (inflection.css) */
        span = el('span', frameClass(key) + (keep ? ' ordpar-frame-after' : ''), str(strings, key));
        /* "+ noun" is English furniture inside a Norwegian cell */
        if (key === 'frameAdjNoun') span.setAttribute('lang', 'en');
        at.appendChild(span);
      }
    }
  }

  /* Header keys the narrow layout swaps for its own shorter term (decisions 40
     follow-up, 2026-10-19; the wide layout keeps "indefinite form", as
     ordbokene's wide tables do). */
  var NARROW_STRINGS = { indefiniteForm: 'indefiniteNarrow', definiteForm: 'definiteNarrow', mascFem: 'mascFemNarrow' };

  function headerCell(col, strings, scope, narrow) {
    var nk = function (key) { return narrow && NARROW_STRINGS[key] ? NARROW_STRINGS[key] : key; };
    var th = el('th');
    th.setAttribute('scope', scope || 'col');
    if (col.unknown) {
      th.setAttribute('class', 'ordpar-unknown');
      th.setAttribute('title', plain(str(strings, 'unknownTag')) + ': ' + col.tag);
      th.appendChild(el('span', 'ordpar-th-label', col.tag));
      th.appendChild(el('span', 'ordpar-th-qual', str(strings, 'unknownTag')));
      return th;
    }
    if (col.label) th.appendChild(el('span', 'ordpar-th-label', str(strings, nk(col.label))));
    if (col.qual) th.appendChild(el('span', 'ordpar-th-qual', str(strings, nk(col.qual))));
    return th;
  }

  /* The column sections of a table: the consecutive runs of columns that
     share a top or a group header. Wide, a section is a header cell spanning
     its columns; narrow, it is a full-width heading row above its rows. */
  function sections(cols) {
    var out = [], i = 0, n;
    while (i < cols.length) {
      var key = cols[i].top || cols[i].group || null;
      n = 1;
      while (i + n < cols.length && ((cols[i + n].top || cols[i + n].group || null) === key)) n++;
      /* a lone column with no header of its own takes the section's name */
      var bare = n === 1 && !cols[i].label && !cols[i].qual && !cols[i].unknown;
      out.push({ key: key, at: i, n: n, bare: bare });
      i += n;
    }
    return out;
  }

  /* The narrow (transposed) table: the genders become column headers, the
     number/definiteness (or tense, or degree) become row groups. Measured off
     ordbokene's own DOM at 500 px (jente) and ~670 px (selvfordypelse),
     2026-09-20 — see the doc, § 4a. Every span is the same run length as the
     wide table's, read along the other axis.
     ONE narrow table per family: the wide tables' sections are stacked in it
     (the tenses, then the perfect participle, then the present participle),
     so the label column is shared, as ordbokene's narrow table is (live DOM
     at 500 px, trøtte and mange, 2026-10-18; decisions 40, question 10). All
     the models share one body, so the column count is the same throughout. */
  function renderNarrow(models, strings) {
    var model = models[0], body = model.body;
    var width = 1 + body.length, i, c, tr, th, m;
    var cls = 'ordpar-infl ordpar-infl--narrow';
    for (m = 0; m < models.length; m++) cls += ' ordpar-infl--' + models[m].tableName;
    var table = el('table', cls);
    table.appendChild(hiddenLabel('caption', 'ordpar-vh', str(strings, models.length > 1 ? 'captionInflection' : (CAPTIONS[model.tableName] || 'captionInflection'))));

    if (model.genderAxis) {
      var thead = el('thead');
      tr = el('tr');
      /* ordbokene leaves this corner empty at narrow width; the axis name is
         kept for a screen reader */
      var corner = el('th', 'ordpar-corner');
      corner.setAttribute('scope', 'col');
      corner.appendChild(hiddenLabel('span', 'ordpar-vh', str(strings, 'gender')));
      tr.appendChild(corner);
      for (i = 0; i < model.genderGroups.length; i++) {
        var gg = model.genderGroups[i];
        th = el('th', 'ordpar-th-row', str(strings, GENDER_LABEL[gg.gender] || gg.gender));
        th.setAttribute('scope', gg.n > 1 ? 'colgroup' : 'col');
        if (gg.n > 1) th.setAttribute('colspan', String(gg.n));
        tr.appendChild(th);
      }
      thead.appendChild(tr);
      table.appendChild(thead);
    }

    for (m = 0; m < models.length; m++) {
      var cols = models[m].cols, spans = models[m].spans, empty = models[m].empty || [];
      /* ordbokene's narrow participle cells carry no frames (live DOM at 552 px,
         trøtte, 2026-09-24); the verb table keeps its å / har / ! */
      var plain = models[m].tableName === 'participle';
      var secs = sections(cols);
      for (var s = 0; s < secs.length; s++) {
        var sec = secs[s], tbody = el('tbody');
        /* a bare section (present participle) is a heading row too, as ordbokene
           has it narrow, over a row whose header cell is empty to the eye */
        if (sec.key) {
          tr = el('tr');
          th = el('th', 'ordpar-th-group', str(strings, sec.key));
          th.setAttribute('scope', 'rowgroup');
          th.setAttribute('colspan', String(width));
          tr.appendChild(th);
          tbody.appendChild(tr);
        }
        for (c = sec.at; c < sec.at + sec.n; c++) {
          tr = el('tr');
          if (sec.bare) {
            th = el('th', 'ordpar-th-row');
            th.setAttribute('scope', 'row');
            th.appendChild(hiddenLabel('span', 'ordpar-vh', str(strings, sec.key)));
          } else {
            th = headerCell(cols[c], strings, 'row', true);
          }
          tr.appendChild(th);
          for (i = 0; i < body.length; i++) {
            if (spans[c][i] === 0 || empty[i]) continue;   /* 162 (1): a row with no comparison form */
            var td = el('td', cols[c].unknown ? 'ordpar-unknown' : null);
            td.setAttribute('lang', 'nb');
            if (spans[c][i] > 1) td.setAttribute('colspan', String(spans[c][i]));
            fillCell(td, body[i], cols[c], strings, plain);
            tr.appendChild(td);
          }
          tbody.appendChild(tr);
        }
        table.appendChild(tbody);
      }
    }
    return spaceTable(table);
  }

  /* One family's rows, ready for its tables: merged once over the whole
     lemma (rule 4) and sorted once, so every table of the family has the same
     rows in the same order — a split in the comparison table is a split in
     the positive table too, with the equal cells spanning (mange). */
  function prepareFamily(family, rows) {
    var tables = familyTables(family), i, k;
    var body = mergeRows(rows);
    var tables_ = [];
    for (i = 0; i < tables.length; i++) {
      var cols = buildColumns(family, tables[i], body);
      tables_.push({ name: tables[i], cols: cols });
    }
    /* rule 6: a gender row axis only when the nouns have several genders */
    var genders = [];
    if (family === 'noun') {
      body.forEach(function (r) { if (r.gender && genders.indexOf(r.gender) === -1) genders.push(r.gender); });
    }
    var genderAxis = genders.length > 1;
    /* Row order: gender (on a gender axis), then lemma, then — inside one lemma
       — alphabetical by the row's forms, cell by cell. That last key is
       ordbokene's, not the data's paradigm order: trøtte's paradigms come as
       trøttet/trøttete, trøttet/trøttede, trøtta, and ordbokene shows trøtta,
       then trøttede, then trøttete (live DOM, 2026-09-24; Robin: "Ours should
       follow the same ordering as theirs"). The cells are read in the order
       the paradigm lists them, the hidden passives included, not the
       columns' order: rådgi's rådgav / rådgivende row (passive rådgies) comes
       before its rådga, rådgav / rådgiende row (rådgis) on ordbokene, though
       its past sorts after (live DOM, 2026-10-18; the one mirror article where
       the two readings differ). Each cell is compared by its FIRST form, in
       `orderCollate` (Robin, 2026-11-02, code provenance decisions 9: follow
       ordbokene; until then the joined cell in Norwegian collation, decisions
       45): gyve's gjøv, gøyv / gjøvet row comes before its gjøv / gyvd row, as
       on ordbokene, where the joined string would put the shorter gjøv first
       (the one mirror article where the two readings differ); bartre's
       bartrær row before its bartre row, klype's kløyp / kløpet before kløyp /
       klypt. */
    body.sort(function (a, b) {
      if (genderAxis) {
        var g = GENDER_ORDER.indexOf(a.gender) - GENDER_ORDER.indexOf(b.gender);
        if (g !== 0) return g;
      }
      if (a.lemmaIndex !== b.lemmaIndex) return a.lemmaIndex - b.lemmaIndex;
      var seq = a.tags.concat(b.tags.filter(function (t) { return a.tags.indexOf(t) === -1; }));
      for (k = 0; k < seq.length; k++) {
        var c = orderCollate(String((a.cells[seq[k]] || [])[0] || ''), String((b.cells[seq[k]] || [])[0] || ''));
        if (c !== 0) return c;
      }
      /* first forms equal throughout: the whole cells decide (never reached in the
         mirror, 2026-11-02, so not seen on ordbokene) */
      for (k = 0; k < seq.length; k++) {
        c = orderCollate((a.cells[seq[k]] || []).join(', '), (b.cells[seq[k]] || []).join(', '));
        if (c !== 0) return c;
      }
      return 0;
    });
    return { body: body, genderAxis: genderAxis, tables: tables_ };
  }

  function familyTables(name) {
    for (var i = 0; i < FAMILIES.length; i++) if (FAMILIES[i].name === name) return FAMILIES[i].tables;
    return ['main'];
  }

  function buildTable(prep, t, strings, mode) {
    var tableName = prep.tables[t].name, cols = prep.tables[t].cols;
    if (!cols.length) return null;
    var body = prep.body, genderAxis = prep.genderAxis;

    /* --- the spans, shared by both layouts -------------------------- */
    /* A run of adjacent rows with the same content in one column is one cell
       (jente: the plural; tore: the present tør). The wide table reads the
       run as a rowspan, the narrow one as a colspan — same numbers, so the
       two layouts can never disagree. */
    var spans = [], r, run, s, i, c;
    for (i = 0; i < cols.length; i++) {
      spans[i] = [];
      r = 0;
      while (r < body.length) {
        var key = cellKey(body[r], cols[i]);
        run = 1;
        if (key !== null) {
          while (r + run < body.length && cellKey(body[r + run], cols[i]) === key) run++;
        }
        spans[i][r] = run;
        for (s = 1; s < run; s++) spans[i][r + s] = 0;
        r += run;
      }
    }
    var genderSpan = {}, genderGroups = [];
    if (genderAxis) {
      for (i = 0; i < body.length; i++) {
        var g0 = body[i].gender;
        if (genderSpan[g0] === undefined) {
          genderSpan[g0] = { at: i, n: 0 };
          genderGroups.push({ gender: g0, at: i, n: 0 });
        }
        genderSpan[g0].n++;
        genderGroups[genderGroups.length - 1].n = genderSpan[g0].n;
      }
    }
    /* Site decisions 162 (1) (Robin, 2026-11-04): a comparison row with no form in any of its
       cells is not drawn — a paradigm with no comparison forms beside one that has them
       (avsindig 3768, kjærlighetslaus 119179). Wide, its row is left out; narrow, its cell in
       each comparison row, the others not widened to fill, as ordbokene's rendered narrow table
       has it (live DOM at 500 px, 2026-11-04). An empty cell is never in a span (`cellKey`), so
       the spans stand. The positive table keeps the row. */
    var empty = [];
    for (r = 0; r < body.length; r++) {
      empty[r] = false;
      if (tableName !== 'comparison') continue;
      empty[r] = true;
      for (i = 0; i < cols.length; i++) if (shown(body[r], cols[i].tag).length) { empty[r] = false; break; }
    }
    var model = {
      tableName: tableName, cols: cols, body: body, spans: spans, empty: empty,
      genderAxis: genderAxis, genderSpan: genderSpan, genderGroups: genderGroups
    };
    if (mode === 'narrow') return model; /* rendered with its siblings: renderNarrow */

    var table = el('table', 'ordpar-infl ordpar-infl--wide ordpar-infl--' + tableName);
    table.appendChild(hiddenLabel('caption', 'ordpar-vh', str(strings, CAPTIONS[tableName] || 'captionInflection')));

    /* --- header rows ------------------------------------------------ */
    var hasTop = false, hasGroup = false, hasCell = false;
    cols.forEach(function (c) {
      if (c.top) hasTop = true;
      if (c.group) hasGroup = true;
      if (c.label || c.qual || c.unknown) hasCell = true;
    });
    var headRows = (hasTop ? 1 : 0) + (hasGroup ? 1 : 0) + (hasCell ? 1 : 0);
    var thead = el('thead'), tr = el('tr'), n, q, p;

    if (genderAxis) {
      var corner = el('th', 'ordpar-corner');
      corner.setAttribute('scope', 'col');
      if (headRows > 1) corner.setAttribute('rowspan', String(headRows));
      corner.appendChild(el('span', 'ordpar-th-qual', str(strings, 'gender')));
      tr.appendChild(corner);
    }

    if (hasTop) {
      i = 0;
      while (i < cols.length) {
        var topKey = cols[i].top || null;
        n = 1;
        while (i + n < cols.length && (cols[i + n].top || null) === topKey) n++;
        var thTop = el('th', 'ordpar-th-group', topKey ? str(strings, topKey) : '');
        thTop.setAttribute('scope', n > 1 ? 'colgroup' : 'col');
        if (n > 1) thTop.setAttribute('colspan', String(n));
        tr.appendChild(thTop);
        i += n;
      }
      thead.appendChild(tr);
      tr = el('tr');
    }

    if (hasGroup) {
      i = 0;
      while (i < cols.length) {
        var groupKey = cols[i].group || null;
        n = 1;
        while (i + n < cols.length && (cols[i + n].group || null) === groupKey) n++;
        var thGroup = el('th', 'ordpar-th-group', groupKey ? str(strings, groupKey) : '');
        thGroup.setAttribute('scope', n > 1 ? 'colgroup' : 'col');
        if (n > 1) thGroup.setAttribute('colspan', String(n));
        /* a group whose columns carry no header of their own reaches down
           into the column row (bra: plural; spise: present participle) */
        var bare = true;
        for (q = i; q < i + n; q++) if (cols[q].label || cols[q].qual || cols[q].unknown) bare = false;
        if (bare && hasCell) thGroup.setAttribute('rowspan', '2');
        tr.appendChild(thGroup);
        for (p = i; p < i + n; p++) cols[p]._bare = bare;
        i += n;
      }
      thead.appendChild(tr);
      tr = el('tr');
    }

    if (hasCell) {
      for (i = 0; i < cols.length; i++) {
        if (hasGroup && cols[i]._bare) continue; /* covered by the group rowspan */
        tr.appendChild(headerCell(cols[i], strings));
      }
      thead.appendChild(tr);
    }
    table.appendChild(thead);

    /* --- body: the runs above, read as rowspans --------------------- */
    var tbody = el('tbody');
    for (i = 0; i < body.length; i++) {
      if (empty[i]) continue;   /* 162 (1): see `empty` above */
      tr = el('tr');
      if (genderAxis) {
        var gi = genderSpan[body[i].gender];
        if (gi && gi.at === i) {
          var thRow = el('th', 'ordpar-th-row', str(strings, GENDER_LABEL[body[i].gender] || body[i].gender));
          thRow.setAttribute('scope', gi.n > 1 ? 'rowgroup' : 'row');
          if (gi.n > 1) thRow.setAttribute('rowspan', String(gi.n));
          tr.appendChild(thRow);
        }
      }
      for (c = 0; c < cols.length; c++) {
        if (spans[c][i] === 0) continue;
        var td = el('td', cols[c].unknown ? 'ordpar-unknown' : null);
        td.setAttribute('lang', 'nb');
        if (spans[c][i] > 1) td.setAttribute('rowspan', String(spans[c][i]));
        fillCell(td, body[i], cols[c], strings, false, true);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return spaceTable(table);
  }

  /* ------------------------------------------------------------------ *
   * 7. render()
   * ------------------------------------------------------------------ */

  function render(lemmas, strings) {
    var s = {}, k;
    for (k in DEFAULT_STRINGS) if (Object.prototype.hasOwnProperty.call(DEFAULT_STRINGS, k)) s[k] = DEFAULT_STRINGS[k];
    if (strings) for (k in strings) if (Object.prototype.hasOwnProperty.call(strings, k)) s[k] = strings[k];
    /* site decisions 152: every word in both languages, unless the caller gives strings of its own
       (another interface language) and no Norwegian */
    if (!Object.prototype.hasOwnProperty.call(s, '__nb')) s.__nb = strings ? null : NB_STRINGS;

    var wrap = el('div', 'ordpar-inflection-tables');
    var rows = readRows(lemmas);
    if (!rows.length) return wrap; /* uninflected, or no paradigm: no table */

    /* one block per paradigm family, in the order the families first occur */
    var order = [], byFamily = {};
    rows.forEach(function (r) {
      var name = r.family || '\x00unknown';
      if (!byFamily[name]) { byFamily[name] = []; order.push(name); }
      byFamily[name].push(r);
    });
    order.forEach(function (name) {
      var prep = prepareFamily(name, byFamily[name]), models = [];
      for (var i = 0; i < prep.tables.length; i++) {
        /* Both layouts are rendered from the same model and the same spans;
           inflection.css shows one and hides the other (§ 4a of the doc).
           Each sits in a wrapper that scrolls sideways rather than clip: one
           wrapper per wide table, one for the family's single narrow table. */
        var wide = buildTable(prep, i, s);
        if (!wide) continue;
        models.push(buildTable(prep, i, s, 'narrow'));
        var boxW = el('div', 'ordpar-infl-wrap ordpar-infl-wrap--wide');
        boxW.appendChild(wide);
        wrap.appendChild(boxW);
      }
      if (models.length) {
        var boxN = el('div', 'ordpar-infl-wrap ordpar-infl-wrap--narrow');
        boxN.appendChild(renderNarrow(models, s));
        wrap.appendChild(boxN);
      }
    });
    return spaced(wrap);
  }

  /* ------------------------------------------------------------------ *
   * 8. Mounting on the article page.
   * ------------------------------------------------------------------ */

  function mountAll(root) {
    var doc = global.document;
    var nodes = (root || doc).querySelectorAll('.ordpar-inflection');
    for (var i = 0; i < nodes.length; i++) {
      var host = nodes[i];
      if (host.getAttribute('data-ordpar-mounted')) continue;
      var id = host.getAttribute('data-paradigm');
      var script = id ? doc.getElementById(id) : null;
      if (!script) continue;
      var data;
      try {
        data = decode(JSON.parse(script.textContent || script.innerHTML || '{}'));
      } catch (e) {
        continue;
      }
      var lemmas = (data && data.lemmas) ? data.lemmas : (data instanceof Array ? data : []);
      host.appendChild(render(lemmas));
      host.setAttribute('data-ordpar-mounted', '1');
      /* the article page wraps the mount in a hidden "Inflection" toggle (Robin,
         2026-09-24); it is shown only when a table was rendered — an uninflected
         word gets no button */
      var toggle = host.closest ? host.closest('.ordpar-infl-toggle') : null;
      if (toggle && host.querySelector('table')) toggle.hidden = false;
      /* the wide table where it fits the card, the narrow one where it does not
         (decisions 102; section 9) */
      fitHost(host);
    }
  }

  /* ------------------------------------------------------------------ *
   * 9. The fit, everywhere (decisions 102, Robin 2026-10-23: "go ahead", generalising 59's
   *    measured switch in a result card, Robin 2026-10-19; the stacked step, decisions 108):
   *    the wide table is shown wherever it fits the box it sits in (the card's content box,
   *    the mount being capped there: article.css `.ordpar-inflection`), unwrapped where that
   *    fits, else with its columns stacked one by one until it fits (below), and the narrow
   *    one where even the fully stacked one does not, so no table ever passes its card's edge; a narrow table still too wide scrolls
   *    inside its own strip, as ordbokene's does on a phone. On the article page (`mountAll`
   *    calls it), in a full result and an opened list or favourites row (lookup.js
   *    `mountArticle` calls it too; once per mount, the second call a no-op). Decided at load
   *    and again whenever the box changes width (a ResizeObserver on the mount, which also
   *    fires, before the paint, when a closed Inflection toggle opens: a closed one has no
   *    width to measure) — ordbokene decides once, by the WINDOW (wide from 1,024 px), and
   *    keeps that until a reload: a deliberate difference (`divergences.md`). The choice is
   *    the class `ordpar-fit-wide` or `ordpar-fit-narrow` on the tables; the 48rem media
   *    rule in inflection.css is only the layout before the first measurement, and a page
   *    that forces one layout on an ancestor (`.ordpar-force-wide` / `-narrow`: the test
   *    page's Layout button) still wins, its rules coming later in the sheet.
   * ------------------------------------------------------------------ */

  /* The stacked step (decisions 108, Robin 2026-10-23): between the unwrapped wide table and
     the narrow one, the wide table with some of its columns STACKED — their cells broken only
     where ordbokene's rendered tables break (`fillCell`'s `keep`: "møtt +" over "noun", headings
     at their spaces, never inside a form). Column by column (Robin, on the all-or-nothing first
     build: "Stack column by column, widest first, until the table fits"; the order then
     changed to space saved, decisions 108, the session's call at his delegation: "I didn't know
     the ramifications when I 'ruled' widest first. You can overrule it"): where the unwrapped
     table (max-content) does not fit the box, its columns are stacked one at a time, until it
     fits — at each step the column whose stacking frees the most width, each column still whole
     stacked on trial in the table as it stands and the table re-measured (ties: the wider
     unwrapped column, then the leftmost). Widest first could stack a column wide for one long
     form that frees little, and then need another. A column is the cells of one grid column with colspan 1 (a rowspan header such as
     "present participle" belongs to its column); a header spanning several columns ("perfect
     participle") is no column of its own and is never held whole — it wraps only if the
     columns under it are together narrower than it. The table is drawn at its min-content
     width (`ordpar-infl--stacked`), the cells of the columns not stacked held whole
     (`ordpar-col-whole`, white-space: nowrap), so an unstacked column keeps its unwrapped width,
     a stacked one takes its stacked width, and no column carries spare width (his shot 5: a
     table a hair too wide squeezed to its box, every cell wrapping its last word in a column as
     wide as before). No tolerance (the old +1 px let a table 1 px too wide through). The narrow
     layout only when some table does not fit even with every column stacked. */
  function measured(t, width) {
    var w = t.style.width, mw = t.style.maxWidth;
    t.style.width = width;
    t.style.maxWidth = 'none';
    var x = t.getBoundingClientRect().width;
    t.style.width = w;
    t.style.maxWidth = mw;
    return x;
  }

  /* the table's columns: for each grid column, its cells with colspan 1 */
  function gridColumns(t) {
    var cols = [], taken = [], rows = t.rows, r, i, j, c, cell, cs, rs;
    for (r = 0; r < rows.length; r++) {
      c = 0;
      for (i = 0; i < rows[r].cells.length; i++) {
        cell = rows[r].cells[i];
        while (taken[r] && taken[r][c]) c++;
        cs = cell.colSpan || 1;
        rs = cell.rowSpan || 1;
        for (j = 0; j < rs * cs; j++) {
          (taken[r + Math.floor(j / cs)] = taken[r + Math.floor(j / cs)] || [])[c + j % cs] = 1;
        }
        if (cs === 1) (cols[c] = cols[c] || []).push(cell);
        c += cs;
      }
    }
    return cols.filter(function (x) { return x && x.length; });
  }

  function whole(cells, on) {
    for (var i = 0; i < cells.length; i++) cells[i].classList[on ? 'add' : 'remove']('ordpar-col-whole');
  }

  function stackColumns(t, avail) {
    var cols = gridColumns(t), widths = [], left = [], k, mw = t.style.maxWidth;
    for (k = 0; k < cols.length; k++) whole(cols[k], true);
    t.classList.add('ordpar-infl--stacked');
    t.style.maxWidth = 'none';                    /* the columns' unwrapped widths, read free */
    for (k = 0; k < cols.length; k++) { widths.push(cols[k][0].getBoundingClientRect().width); left.push(k); }
    t.style.maxWidth = mw;
    var now = measured(t, 'min-content');
    while (now > avail && left.length) {
      /* each column still whole, stacked on trial in the table as it stands: the width it frees */
      var best = -1, bestFree = 0, bestNow = now;
      for (var j = 0; j < left.length; j++) {
        whole(cols[left[j]], false);
        var x = measured(t, 'min-content'), free = now - x;
        whole(cols[left[j]], true);
        if (best < 0 || free > bestFree + 0.01 ||
            (Math.abs(free - bestFree) <= 0.01 && widths[left[j]] > widths[left[best]] + 0.01)) {
          best = j; bestFree = free; bestNow = x;            /* ties: the wider, then the leftmost */
        }
      }
      whole(cols[left[best]], false);
      left.splice(best, 1);
      now = bestNow;
    }
  }

  function fitTables(tables) {
    if (!tables.clientWidth) return;            /* hidden: measured when shown */
    var avail = tables.getBoundingClientRect().width;
    tables.classList.remove('ordpar-fit-narrow');
    tables.classList.add('ordpar-fit-wide');
    var wraps = tables.querySelectorAll('.ordpar-infl-wrap--wide');
    var tooWide = false;
    for (var i = 0; i < wraps.length; i++) {
      var t = wraps[i].querySelector('table');
      if (!t) continue;
      t.classList.remove('ordpar-infl--stacked');
      whole(t.querySelectorAll('.ordpar-col-whole'), false);
      if (tooWide || measured(t, 'max-content') <= avail) continue;
      /* every column stacked: the table's min-content width with no cell held whole */
      if (measured(t, 'min-content') <= avail) stackColumns(t, avail);
      else tooWide = true;
    }
    if (tooWide) {
      tables.classList.remove('ordpar-fit-wide');
      tables.classList.add('ordpar-fit-narrow');
    }
  }

  function fitHost(host) {
    var all = host.querySelectorAll('.ordpar-inflection-tables');
    if (!all.length) return;
    var run = function () { for (var i = 0; i < all.length; i++) fitTables(all[i]); };
    run();
    if (host._ordparFit) return;                  /* wired once per mount */
    host._ordparFit = true;
    var toggle = host.closest ? host.closest('details.ordpar-infl-toggle') : null;
    if (toggle) toggle.addEventListener('toggle', run);
    if (typeof global.ResizeObserver === 'function') {
      var lastW = -1;
      new global.ResizeObserver(function () {
        var w = host.clientWidth;
        if (w !== lastW) { lastW = w; run(); }
      }).observe(host);
    } else if (global.addEventListener) {
      global.addEventListener('resize', run);
    }
  }

  /** Fit every inflection mount in `root` (or `root` itself, if it is one). */
  function fit(root) {
    if (!root || !root.querySelectorAll) return;
    var hosts = (root.matches && root.matches('.ordpar-inflection'))
      ? [root] : root.querySelectorAll('.ordpar-inflection');
    for (var i = 0; i < hosts.length; i++) fitHost(hosts[i]);
  }

  global.ordparInflection = {
    render: render,
    decode: decode,
    SHAPES: SHAPES,
    mountAll: mountAll,
    fit: fit,
    TAGS: TAGS,
    STRINGS: DEFAULT_STRINGS,
    NB_STRINGS: NB_STRINGS,                    // site decisions 152
    FAMILIES: FAMILIES,
    LEMMA_SORT: LEMMA_SORT
  };

  if (global.document && global.document.addEventListener) {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', function () { mountAll(); });
    } else {
      mountAll();
    }
  }
})(typeof window !== 'undefined' ? window : this);
