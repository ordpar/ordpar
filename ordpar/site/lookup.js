/*! Ordpar — the client-side lookup index and the search view.
 *
 * Two namespaces in one file, because the search page AND the 404 shell need both:
 *
 *   window.ordparLookup  the DATA layer over out/index/ — fold, shard, lookup, suggest,
 *                        similar, randomHeadword, shownOrder, firstShown. No DOM; usable under node (see
 *                        `setLoader`), which is how the build smoke-tests it.
 *   window.ordparSearch  the VIEW — render(root, query): every hit's article in full (or,
 *                        with the setting `listview` = on, one row per hit that opens the
 *                        article in place — site decisions 59), the inflected-form panel,
 *                        similar headwords, the live region. The articles are taken from
 *                        their own static pages (`extractArticle`, `scopeArticle`).
 *
 * The index format, the shard rule and the algorithms are documented in
 * ordpar/docs/lookup-index.md. Forms are stored as spelled and folded at query time; the
 * shard key is the first character of the folded form (and for b f k s t the second too),
 * so `fold`, `bare`, `accentMatch`, `letterKey`, `shardKey` and `suggestKey` here must stay in
 * step with ordpar/build_index.py (`fold`, `bare`, `accent_match`, `letter_key`, `shard_key`,
 * `suggest_key`, `SPLIT_LETTERS`) — and, for decisions 55, `tailKey`, `remainderKey`,
 * `RULES`, `DOUBLING`, `rewrites` (`tail_key`, `remainder_key`, `RULES`, `DOUBLING`,
 * `rewrites`). Accents fold one way (decisions 41 (a)): what is typed
 * without an accent matches a form with one (en -> én), never the reverse.
 *
 * No request leaves the origin from this file: a search the reader made is handed to
 * `events.js` (`window.ordparEvents`: a hit, or a miss held until a similar word is chosen —
 * site decisions 62), which alone decides whether anything is sent. Nothing is stored by this
 * file.
 */
(function (global) {
  'use strict';

  var SPECIAL = { 'æ': 'ae', 'ø': 'oe', 'å': 'aa' };
  var KEEP = { 'æ': 1, 'ø': 1, 'å': 1 };          // letters of Norwegian: never folded
  var PLAIN = /[^\x00-\x7fæøå]/;
  var MARKS = /^[\u0300-\u036f]+$/;
  var MISC = 'misc';
  var SPLIT = { b: 1, f: 1, k: 1, s: 1, t: 1 };   // split again by the second character
  var MAX_QUERY = 200;      // the search box's own cap
  var MAX_WORDS = 20;       // query guard: more than this is prose, not a lookup
  var MAX_WORD_LEN = 40;    // query guard: no Bokmål headword is this long

  var config = {
    base: (global.ORDPAR_BASE || '/'),   // site root; index lives at <base>index/
    maxSuggestions: 20,
    similarCount: 5,
    similarPer: 3          // one edit per this many characters (build_index.SIMILAR_PER)
  };

  var shards = {};        // key -> prepared shard
  var pending = {};       // key -> Promise
  var headwords = {};     // letter key -> {list: [...], buckets: {c: [{w, f, b, n}]}}
  var headwordsPending = {};
  var tails = {};         // tails key -> [{w, f, b, n}] (decisions 55)
  var tailsPending = {};
  var translated = null;  // Set of ids
  var translatedList = null;
  var translatedPending = null;
  var randomList = null;  // the Random word's pool (random.json, decisions 67)
  var randomPending = null;

  /* ---------------------------------------------------------------- loading */

  function defaultLoader(name) {
    return fetch(config.base + 'index/' + name, { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }
  var loader = defaultLoader;

  function setLoader(fn) { loader = fn || defaultLoader; }

  function configure(opts) {
    for (var k in (opts || {})) { config[k] = opts[k]; }
    return config;
  }

  /* --------------------------------------------------------------- folding */

  function fold(s) {
    return (s == null ? '' : String(s)).normalize('NFC').toLowerCase();
  }

  /**
   * One FOLDED character without its accent (build_index.py `bare_char`): a character that
   * decomposes (NFD) into an ASCII letter plus combining marks U+0300-U+036F folds to the
   * letter — é -> e, ü -> u; æ ø å never fold.
   */
  function bareChar(c) {
    if (c < '\x80' || KEEP[c]) { return c; }
    var d = c.normalize('NFD');
    if (d.length > 1 && d.charAt(0) >= 'a' && d.charAt(0) <= 'z' && MARKS.test(d.slice(1))) {
      return d.charAt(0);
    }
    return c;
  }

  /** `fold(s)` with the accents folded away: what forms are matched, sharded and compared on. */
  function bare(s) {
    var f = fold(s);
    if (!PLAIN.test(f)) { return f; }
    var out = '';
    for (var i = 0; i < f.length; i++) { out += bareChar(f.charAt(i)); }
    return out;
  }

  /**
   * Does folded query `q` match folded form `w` over q's length, ONE way: each character of
   * `q` equals w's or is its bare letter (en matches én; én does not match en).
   */
  function accentMatch(q, w) {
    if (w.length < q.length) { return false; }
    for (var i = 0; i < q.length; i++) {
      var a = q.charAt(i), b = w.charAt(i);
      if (a !== b && a !== bareChar(b)) { return false; }
    }
    return true;
  }

  function charKey(c) {
    if (!c) { return MISC; }
    if (c >= 'a' && c <= 'z') { return c; }
    if (SPECIAL[c]) { return SPECIAL[c]; }
    return MISC;
  }

  /** The first-letter bucket of the BARE form: a-z, ae/oe/aa, misc (én is filed with e). */
  function letterKey(s) { return charKey(bare(s).charAt(0)); }

  /** The shard a form lives in: its letter key, and for a split letter `s-k`, `s-misc`. */
  function shardKey(s) {
    var f = bare(s), key = charKey(f.charAt(0));
    if (!SPLIT[key]) { return key; }
    return key + '-' + charKey(f.charAt(1));
  }

  /**
   * The file an autocomplete prefix reads: its shard, except a ONE-character prefix on a
   * split letter, which reads `<letter>-top` (the letter's first 50 headwords in suggestion
   * order) rather than every sub-shard.
   */
  function suggestKey(s) {
    var f = fold(s);
    if (f.length === 1 && SPLIT[letterKey(f)]) { return letterKey(f) + '-top'; }
    return shardKey(f);
  }

  /**
   * Decisions 55 (2): the `tails/` file a headword lives in — the keys of its second and third
   * bare characters (build_index.py `tail_key`: hus -> u-s); `remainderKey(s)` is the file
   * whose headwords' remainder starts with s's first two characters.
   */
  function tailKey(s) { var b = bare(s); return charKey(b.charAt(1)) + '-' + charKey(b.charAt(2)); }
  function remainderKey(s) { return charKey(s.charAt(0)) + '-' + charKey(s.charAt(1)); }
  /** The `snip/` file of a headword or a query (site decisions 59): its first three bare
   *  characters' keys — `hus` -> `h-u-s`. build_index.py `snippet_key`. */
  function snipKey(s) {
    var b = bare(s);
    return charKey(b.charAt(0)) + '-' + charKey(b.charAt(1)) + '-' + charKey(b.charAt(2));
  }

  /*
   * Decisions 55 (1), 56: Norwegian spelling-variation rules, applied to the BARE query (on a
   * hit and a miss alike) — build_index.py `RULES`, `DOUBLING`, `MAX_REWRITES`, `rewrites`; the
   * table with an example per rule is lookup-index.md § 4 (3). [from, to, where, notAfter]:
   * where is 'start' (of a word), 'end', 'inner' (each occurrence not at a word's end), 'any'
   * (each occurrence, one rewrite each) or 'all' (every occurrence at once).
   */
  var RULES = [
    ['hv', 'k', 'start', ''], ['hv', 'v', 'start', ''], ['k', 'hv', 'start', ''], ['v', 'hv', 'start', ''],
    ['kv', 'hv', 'start', ''], ['hv', 'kv', 'start', ''],
    ['kj', 'sj', 'any', 's'], ['kj', 'skj', 'any', 's'], ['sj', 'kj', 'any', ''],
    ['sj', 'skj', 'any', ''], ['skj', 'kj', 'any', ''], ['skj', 'sj', 'any', ''],
    ['tj', 'kj', 'start', ''], ['kj', 'tj', 'start', ''],
    ['gj', 'hj', 'start', ''], ['gj', 'j', 'start', ''], ['hj', 'gj', 'start', ''],
    ['hj', 'j', 'start', ''], ['j', 'gj', 'start', ''], ['j', 'hj', 'start', ''],
    ['aa', 'å', 'all', ''], ['å', 'aa', 'all', ''], ['ae', 'æ', 'all', ''],
    ['æ', 'ae', 'all', ''], ['oe', 'ø', 'all', ''], ['ø', 'oe', 'all', ''],
    ['æ', 'eg', 'end', ''], ['eg', 'æ', 'end', ''],
    ['æ', 'e', 'inner', ''], ['e', 'æ', 'inner', ''],
    ['c', 'k', 'any', ''], ['c', 's', 'any', ''], ['ph', 'f', 'any', ''],
    ['th', 't', 'any', ''], ['x', 'ks', 'any', ''], ['qu', 'kv', 'any', '']
  ];
  var DOUBLING = 'bdfgklmnprstv';
  var MAX_REWRITES = 40;
  var WORD_EDGE = ' -';

  function overlaps(i, j, spans) {
    for (var k = 0; k < spans.length; k++) {
      if (i < spans[k][1] && spans[k][0] < j) { return true; }
    }
    return false;
  }

  /**
   * Every single-rule rewrite of q as [rewrite, spans] — build_index.py `_rewrite_once`: spans
   * are the [start, end) stretches the rule wrote; a match touching a stretch of `avoid` (what an
   * earlier rule wrote) is skipped, so a chained rule never rewrites what the first one wrote.
   */
  function rewriteOnce(q, avoid) {
    var out = [], n = q.length, i, j, p;
    avoid = avoid || [];
    for (var k = 0; k < RULES.length; k++) {
      var frm = RULES[k][0], to = RULES[k][1], where = RULES[k][2], notAfter = RULES[k][3];
      var L = frm.length, T = to.length;
      if (where === 'all') {
        var pos = [];
        i = q.indexOf(frm);
        while (i !== -1) { pos.push(i); i = q.indexOf(frm, i + L); }
        if (!pos.length) { continue; }
        var clash = false;
        for (p = 0; p < pos.length; p++) { if (overlaps(pos[p], pos[p] + L, avoid)) { clash = true; } }
        if (!clash) {
          var spans = [];
          for (p = 0; p < pos.length; p++) { spans.push([pos[p] + p * (T - L), pos[p] + p * (T - L) + T]); }
          out.push([q.split(frm).join(to), spans]);
        }
        continue;
      }
      i = q.indexOf(frm);
      while (i !== -1) {
        var ok = !(notAfter && i > 0 && q.charAt(i - 1) === notAfter);
        if (where === 'start' && i > 0 && WORD_EDGE.indexOf(q.charAt(i - 1)) === -1) { ok = false; }
        if (where === 'end' && i + L < n && WORD_EDGE.indexOf(q.charAt(i + L)) === -1) { ok = false; }
        if (where === 'inner' && (i + L >= n || WORD_EDGE.indexOf(q.charAt(i + L)) !== -1)) { ok = false; }
        if (ok && avoid.length && overlaps(i, i + L, avoid)) { ok = false; }
        if (ok) { out.push([q.slice(0, i) + to + q.slice(i + L), [[i, i + T]]]); }
        i = q.indexOf(frm, i + 1);
      }
    }
    i = 0;
    while (i < n) {
      var c = q.charAt(i);
      j = i;
      while (j < n && q.charAt(j) === c) { j++; }
      if (DOUBLING.indexOf(c) !== -1 && !(avoid.length && overlaps(i, j, avoid))) {
        if (j - i === 1) { out.push([q.slice(0, i) + c + q.slice(i), [[i, i + 2]]]); }
        else if (j - i === 2) { out.push([q.slice(0, i) + q.slice(i + 1), [[i, i + 1]]]); }
      }
      i = j;
    }
    return out;
  }

  /**
   * The spelling-variation rewrites of a bare query, in build_index.py `rewrites` order: the
   * single rewrites, then (decisions 56, capped at two rules) a second rule on each of them,
   * never over what the first wrote; deduplicated, never q, at most MAX_REWRITES.
   */
  function rewrites(q) {
    var seen = Object.create(null), res = [], singles = [], i, k, r;
    seen[q] = 1;
    var once = rewriteOnce(q, null);
    for (i = 0; i < once.length; i++) {
      r = once[i][0];
      if (r && !seen[r]) { seen[r] = 1; res.push(r); singles.push(once[i]); }
    }
    for (i = 0; i < singles.length && res.length < MAX_REWRITES; i++) {
      var two = rewriteOnce(singles[i][0], singles[i][1]);
      for (k = 0; k < two.length; k++) {
        r = two[k][0];
        if (r && !seen[r]) { seen[r] = 1; res.push(r); }
      }
    }
    return res.slice(0, MAX_REWRITES);
  }

  /**
   * Capitalisation as a small distance (decisions 55, Robin 2026-10-19; build_index.py
   * `case_distance`): the query AS TYPED against a form as written, position by position over
   * the shorter — each pair of cased characters whose case differs counts 1. A tie-breaker only.
   */
  function caseDistance(q, w) {
    q = String(q).normalize('NFC'); w = String(w).normalize('NFC');
    var n = 0, m = Math.min(q.length, w.length);
    for (var i = 0; i < m; i++) {
      var a = q.charAt(i), b = w.charAt(i);
      if (a.toLowerCase() !== a.toUpperCase() && b.toLowerCase() !== b.toUpperCase() &&
          (a !== a.toLowerCase()) !== (b !== b.toLowerCase())) { n++; }
    }
    return n;
  }

  /** The query guards (plan § 1.1): junk is not sent to the index. */
  function guard(q) {
    var s = (q == null ? '' : String(q)).trim();
    if (!s) { return { ok: false, reason: 'empty' }; }
    if (s.length > MAX_QUERY) { s = s.slice(0, MAX_QUERY); }
    var words = s.split(/\s+/);
    if (words.length > MAX_WORDS) { return { ok: false, reason: 'tooManyWords' }; }
    for (var i = 0; i < words.length; i++) {
      if (words[i].length > MAX_WORD_LEN) { return { ok: false, reason: 'wordTooLong' }; }
    }
    return { ok: true, query: s };
  }

  function prepare(key, raw) {
    var shard = raw || { k: key, heads: {}, forms: {}, words: {} };
    shard.foldedHeads = foldMap(shard.heads);
    shard.foldedForms = foldMap(shard.forms);
    // brief 59b item 14: the frequency band of each headword, one hex digit per headword
    // aligned with the headwords sorted (build_index.py `shard_bands`)
    var hex = shard.n || '', band = Object.create(null);
    Object.keys(shard.heads).sort().forEach(function (w, i) {
      band[w] = i < hex.length ? parseInt(hex.charAt(i), 16) : 0;
    });
    shard.headList = Object.keys(shard.heads).map(function (w) {
      return { w: w, f: fold(w), b: bare(w), n: band[w] };
    }).sort(function (a, b) { return a.f < b.f ? -1 : (a.f > b.f ? 1 : 0); });
    // site decisions 117: the searches of this shard that have a page of their own — `p`, one
    // digit per headword aligned with the headwords sorted (as `n`), and `pf`, the inflected
    // forms with a form page (build_index.py `write_index`, from `page_plan`): the build's
    // answer, read here, never worked out again
    var pflags = shard.p || '';
    shard.pages = Object.create(null);
    if (pflags) {
      Object.keys(shard.heads).sort().forEach(function (w, i) {
        if (pflags.charAt(i) === '1') { shard.pages[fold(w)] = 1; }
      });
    }
    (shard.pf || []).forEach(function (w) { shard.pages[fold(w)] = 1; });
    return shard;
  }

  /** bare form -> the stored forms with it (`group` then keeps the accent matches). */
  function foldMap(map) {
    var out = Object.create(null);
    for (var form in map) {
      var f = bare(form);
      (out[f] || (out[f] = [])).push(form);
    }
    return out;
  }

  function loadShard(key) {
    if (shards[key]) { return Promise.resolve(shards[key]); }
    if (pending[key]) { return pending[key]; }
    pending[key] = Promise.resolve(loader(key + '.json')).then(function (raw) {
      shards[key] = prepare(key, raw);
      delete pending[key];
      return shards[key];
    });
    return pending[key];
  }

  /**
   * A similar-words file as entries {w, f, b, n}: `{"w": [forms], "f": "<one hex band per
   * form>"}` since decisions 55 (n = the frequency band), a plain list of forms before (n = 0).
   * Since site decisions 144 also what the form's row after a miss needs, with no shard
   * (build_index.py `similar_file`): `c` the number of articles it heads (`a`, one hex digit),
   * `x` whether any is translated (`x`), `k` a one-article form's word class (`k`, its place in
   * `kc`; '' for none) — `c` null in a file built before 144, whose row then asks the search.
   */
  var ROW_CODES = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
  function similarEntries(data) {
    if (!data) { return []; }
    var list = Array.isArray(data) ? data : (data.w || []);
    var bands = Array.isArray(data) ? '' : (data.f || '');
    var pages = Array.isArray(data) ? '' : (data.p || '');     // site decisions 117
    var arts = Array.isArray(data) ? '' : (data.a || '');      // site decisions 144
    var trs = Array.isArray(data) ? '' : (data.x || '');
    var kinds = Array.isArray(data) ? '' : (data.k || '');
    var kc = (!Array.isArray(data) && data.kc) || [];
    var out = new Array(list.length);
    for (var i = 0; i < list.length; i++) {
      var code = ROW_CODES.indexOf(kinds.charAt(i));
      out[i] = { w: list[i], f: fold(list[i]), b: bare(list[i]),
                 n: i < bands.length ? parseInt(bands.charAt(i), 16) : 0,
                 p: pages.charAt(i) === '1',
                 c: i < arts.length ? parseInt(arts.charAt(i), 16) : null,
                 x: trs.charAt(i) === '1',
                 k: code >= 0 && code < kc.length ? kc[code] : '' };
    }
    return out;
  }

  /** One letter's headwords (`headwords/<letter>.json`), bucketed by first bare char. */
  function loadHeadwords(letter) {
    if (headwords[letter]) { return Promise.resolve(headwords[letter]); }
    if (headwordsPending[letter]) { return headwordsPending[letter]; }
    headwordsPending[letter] = Promise.resolve(loader('headwords/' + letter + '.json')).then(function (data) {
      var entries = similarEntries(data);
      var buckets = Object.create(null);
      for (var i = 0; i < entries.length; i++) {
        var c = entries[i].b.charAt(0);
        (buckets[c] || (buckets[c] = [])).push(entries[i]);
      }
      headwords[letter] = { list: entries.map(function (e) { return e.w; }), buckets: buckets,
                            byBare: Object.create(null) };
      delete headwordsPending[letter];
      return headwords[letter];
    });
    return headwordsPending[letter];
  }

  /** One `tails/<key>.json` file (decisions 55 (2)), as entries. */
  function loadTails(key) {
    if (tails[key]) { return Promise.resolve(tails[key]); }
    if (tailsPending[key]) { return tailsPending[key]; }
    tailsPending[key] = Promise.resolve(loader('tails/' + key + '.json')).then(function (data) {
      tails[key] = similarEntries(data);
      delete tailsPending[key];
      return tails[key];
    });
    return tailsPending[key];
  }

  /**
   * The list view's snippets (site decisions 59): `snip/<snipKey>.json`, `{"<id>": "one
   * line"}` for every article with a headword under that key — what a list row shows under
   * its headword. Files of their own, so the default view (full articles) never downloads
   * one. A missing file reads as no snippets.
   */
  var snippets = {};
  var snippetsPending = {};
  function loadSnippets(key) {
    if (snippets[key]) { return Promise.resolve(snippets[key]); }
    if (snippetsPending[key]) { return snippetsPending[key]; }
    snippetsPending[key] = Promise.resolve(loader('snip/' + key + '.json')).then(function (data) {
      snippets[key] = data || {};
      delete snippetsPending[key];
      return snippets[key];
    });
    return snippetsPending[key];
  }
  /** The `snip/` file `key` if this page has it already (loaded by a search, a list or a hover),
   *  else null; never fetches (site decisions 185: the hover under "When its link is clicked"). */
  function loadedSnippets(key) { return snippets[key] || null; }

  /**
   * Whether the snippet of `id` in a `snip/` file is the article's SUMMARY GLOSS (decisions 42),
   * not its first English sense (site decisions 116, Robin 2026-10-24: "semibold for *English
   * equivalents* only"; "English definition lines also stays regular text (when there are no
   * summary glosses for the article)"): the file's `"_g"` list (build_index.py
   * `snippet_files`). A file without one (built before 116) marks none, so its rows stay as
   * they were.
   */
  function isGloss(snips, id) {
    var g = snips && snips._g;
    if (!g || !g.length) { return false; }
    if (!snips.__gset) {
      var set = Object.create(null);
      for (var i = 0; i < g.length; i++) { set[String(g[i])] = 1; }
      try { Object.defineProperty(snips, '__gset', { value: set }); } catch (e) { snips.__gset = set; }
    }
    return !!snips.__gset[String(id)];
  }

  /*
   * Site decisions 152 (Robin, 2026-10-30/31): THE FIRST NORWEGIAN DEFINITION of an article, for
   * the rows' right side and the hovers under Norwegian only with the English equivalents hidden.
   * A `snip/` file carries it for its translated articles in `"_n"` (`{"<id>": text}`, "" where the
   * article has none; build_index.py `snippet_files`); an untranslated article's own line is its
   * Norwegian definition already. A file without `"_n"` (built before 152) gives none, so no row
   * ever shows a translated article's English in its place. -> the text, or ''.
   */
  function nbDef(snips, id) {
    if (!snips || !snips._n) { return ''; }
    id = String(id);
    if (Object.prototype.hasOwnProperty.call(snips._n, id)) { return snips._n[id] || ''; }
    return snips[id] || '';
  }
  /** Whether the rows show the Norwegian definition (Norwegian only on, the English equivalents
   *  hidden, the rows on "Norwegian definition": `ordparShell.layer`). */
  function nbRows() {
    var S = global.ordparShell, L = S && S.layer ? S.layer() : null;
    return !!(L && L.hidden && L.rows === 'nbdef');
  }
  /**
   * A `snip/` file as the ROWS read it (`nbRows`): every article's line its first Norwegian
   * definition (`nbDef`), none where it has none, no summary glosses (`"_g"`) and no set-phrase
   * boxes (`"_d"`); `"_h"` kept. Otherwise the file itself. The rows' readers take it (the
   * suggestions, Recent and History, the list view and the inflected-form rows, the similar rows,
   * Favourites); what is STORED (a History entry's text, `recordSearch`) always reads the file.
   */
  function rowView(snips) {
    if (!snips || !nbRows()) { return snips; }
    if (snips.__nbview) { return snips.__nbview; }
    var v = {}, k;
    for (k in snips) {
      if (Object.prototype.hasOwnProperty.call(snips, k) && /^\d+$/.test(k)) {
        var text = nbDef(snips, k);
        if (text) { v[k] = text; }
      }
    }
    if (snips._h) { v._h = snips._h; }
    v._n = snips._n || {};
    try { Object.defineProperty(snips, '__nbview', { value: v }); } catch (e) { snips.__nbview = v; }
    return v;
  }

  /** The class of a summary gloss's text (semibold, shell.css) and of the faded " · "
   *  between glosses (the muted grey, the gloss's weight) — site decisions 116. */
  var GLOSS_CLASS = 'ordpar-sgloss';
  var SEP_CLASS = 'ordpar-gsep';

  /** Append `text` to `node`, each " · " in it a separator span (`SEP_CLASS`). */
  function appendGlossText(node, text) {
    var doc = node.ownerDocument;
    String(text).split(' · ').forEach(function (part, i) {
      if (i) {
        var sep = node.appendChild(doc.createElement('span'));
        sep.className = SEP_CLASS;
        sep.textContent = ' · ';
      }
      if (part) { node.appendChild(doc.createTextNode(part)); }
    });
  }

  /**
   * Write a row's gloss or snippet text into `node` (site decisions 116): a summary gloss
   * (`gloss` true) marked `GLOSS_CLASS`, its " · " separators faded (`appendGlossText`);
   * anything else — an English definition line, a Norwegian one, a set-phrase box — as plain
   * text, the class removed.
   */
  function writeGloss(node, text, gloss) {
    node.textContent = '';
    if (gloss) {
      node.classList.add(GLOSS_CLASS);
      appendGlossText(node, text);
    } else {
      node.classList.remove(GLOSS_CLASS);
      node.textContent = text;
    }
  }

  function loadTranslated() {
    if (translated) { return Promise.resolve(translated); }
    if (translatedPending) { return translatedPending; }
    translatedPending = Promise.resolve(loader('translated.json')).then(function (list) {
      translatedList = list || [];
      translated = new Set(translatedList);
      translatedPending = null;
      return translated;
    });
    return translatedPending;
  }

  /* --------------------------------------------------------------- queries */

  /**
   * One article as a search answers it. `words[id]` is `[display, hg, pos(, 1)]`, its `hg` one
   * number every shown spelling carries (0 none) or, where they differ, a list of one per
   * spelling (site decisions 93; build_index.py `hg_field`): the list rides along as `hgs`, and
   * `hg` is the number of the spelling the search matched (`form`, `formHg`) — what the results'
   * order and a suggestion's or a history row's numbered glosses use, as ordbokene numbers
   * *lysning* I before *lysing* I, *lysning* II.
   */
  function article(shard, id, form) {
    var w = shard.words[String(id)] || ['', 0, ''];
    var a = {
      id: id,
      word: w[0],
      hg: formHg(w, form),
      pos: w[2] || '',
      translated: translated ? translated.has(id) : null
    };
    if (Array.isArray(w[1])) { a.hgs = w[1].slice(); }
    return a;
  }

  /** The SEPARATOR between an article's spellings in the index's text (build_index.py `SEP`):
   *  data only — every place that shows the text draws ", " (`headParts`, decisions 93). */
  var SEP = ' / ';

  /** The homograph number of the spelling `form` in the article `w` (a `words` entry); a form
   *  not among the shown spellings takes the first non-zero number. build_index.py `form_hg`. */
  function formHg(w, form) {
    var hg = w[1];
    if (!Array.isArray(hg)) { return hg || 0; }
    var forms = String(w[0] || '').replace(/ …$/, '').split(SEP);
    var i = form == null ? -1 : forms.indexOf(form);
    if (i >= 0 && i < hg.length) { return hg[i] || 0; }
    for (var k = 0; k < hg.length; k++) { if (hg[k]) { return hg[k]; } }
    return 0;
  }

  /**
   * An article's headword line as the article page prints it (site decisions 93, Robin
   * 2026-10-22, read off ordbokene's rendered pages): each spelling with its OWN homograph
   * number — *lysing* I, *lysning* II; *avrustning*, *avrusting* II; *tore* II, *tørre* II —
   * and the spellings separated by ", ", never the index's " / " (Robin: "the lemmas are
   * seperated by `,` not `/`"). `word` is the index's text (`words[id][0]`) or one stored with a
   * favourite or a history entry, old or new (the same " / "); `hgs` the per-spelling numbers
   * where they differ, else `hg` is every spelling's. -> {parts: [{w, hg}], cut} — `cut` where
   * the text ends " …" (more than three spellings).
   */
  function headParts(word, hg, hgs) {
    var text = String(word == null ? '' : word), cut = / …$/.test(text);
    var forms = text.replace(/ …$/, '').split(SEP);
    var list = Array.isArray(hgs) && hgs.length ? hgs : null;
    return {
      parts: forms.map(function (f, i) { return { w: f, hg: list ? (list[i] || 0) : (hg || 0) }; }),
      cut: cut
    };
  }

  /** The headword line as plain text — "lysing I, lysning II" — for a title, a label or the
   *  share sheet. */
  function headText(word, hg, hgs) {
    var h = headParts(word, hg, hgs);
    return h.parts.map(function (p) { return p.w + (p.hg ? ' ' + roman(p.hg) : ''); }).join(', ')
      + (h.cut ? ' …' : '');
  }

  /**
   * The order of the articles under one form, as ordbokene's results (site decisions 59 (1),
   * measured 2026-10-19): the verbs first, in homograph-number order among themselves, then
   * every other article in homograph-number order whatever its word class — fange III (verb),
   * I, II; stille IV, V (verbs), I, II, III. An unnumbered article keeps its place before the
   * numbered ones; the id breaks a tie. build_index.py `homograph_order`.
   */
  function homographRank(a) { return !a.hg ? 0 : (a.pos === 'VERB' ? 1 : 2); }
  function homographOrder(a, b) {
    return (homographRank(a) - homographRank(b)) || (a.hg - b.hg) || (a.id - b.id);
  }

  /**
   * The order of the articles listed for one form in the results (brief 59b item 12, Robin
   * 2026-10-19 — a deliberate divergence from ordbokene, which has no such split): the
   * translated articles first, then the untranslated, each group in `homographOrder` — fly V
   * (verb) and III, the translated, before I, II, IV. build_index.py `result_order`.
   */
  function resultOrder(a, b) {
    return ((b.translated ? 1 : 0) - (a.translated ? 1 : 0)) || homographOrder(a, b);
  }

  function group(shard, foldedMap, sourceMap, folded, matched) {
    var forms = (foldedMap[bare(folded)] || []).filter(function (form) {
      return accentMatch(folded, fold(form));      // one way: én never finds en
    }).sort();
    return forms.map(function (form) {
      var articles = (sourceMap[form] || []).map(function (id) {
        // a headword hit is numbered by the spelling it matched (decisions 93)
        var a = article(shard, id, matched ? form : null);
        // an expression written in alternation notation shows the variant that matched
        var w = shard.words[String(id)];
        if (matched && w && w[3]) { a.word = form; delete a.hgs; }
        return a;
      });
      // a headword group in `resultOrder`; an inflected form's articles keep the order the
      // index stores them in, the most common headword first (site decisions 143,
      // build_index.py `form_order`)
      if (matched) { articles.sort(resultOrder); }
      return { form: form, articles: articles };
    });
  }

  /**
   * Answer one query.
   * -> {query, folded, heads: [{form, articles}], forms: [{form, articles}], count}
   * `heads` are the articles the string is the HEADWORD of (all homographs, decisions 18);
   * `forms` the articles it is an inflected form of. Both may be non-empty.
   */
  function lookup(q) {
    var g = guard(q);
    if (!g.ok) { return Promise.resolve({ query: q, folded: '', heads: [], forms: [], count: 0, guard: g.reason }); }
    var folded = fold(g.query);
    return Promise.all([loadShard(shardKey(folded)), loadTranslated()]).then(function (r) {
      var shard = r[0];
      var heads = group(shard, shard.foldedHeads, shard.heads, folded, true);
      var forms = group(shard, shard.foldedForms, shard.forms, folded, false);
      // An article is listed once (build_index.py `dedupe_accent_groups`): a group reached only
      // through accent folding (én for en) keeps the articles no earlier group lists.
      var seen = Object.create(null);
      heads.concat(forms).forEach(function (grp) {
        if (fold(grp.form) === folded) { grp.articles.forEach(function (a) { seen[a.id] = 1; }); }
      });
      var dedupe = function (groups) {
        return groups.filter(function (grp) {
          if (fold(grp.form) === folded) { return true; }
          grp.articles = grp.articles.filter(function (a) { return !seen[a.id]; });
          grp.articles.forEach(function (a) { seen[a.id] = 1; });
          return grp.articles.length > 0;
        });
      };
      heads = dedupe(heads);
      forms = dedupe(forms);
      var count = 0;
      heads.concat(forms).forEach(function (grp) { count += grp.articles.length; });
      var res = { query: g.query, folded: folded, heads: heads, forms: forms, count: count };
      if (!forms.length || !shard.t) { return res; }
      // site decisions 117: each inflected-form row's label ("plural indefinite"), its code
      // from the shard's `t`, its words from `labels.json`
      return loadLabels().then(function (table) {
        forms.forEach(function (grp) {
          grp.articles.forEach(function (a) {
            var c = labelCode(shard, grp.form, a.id);
            a.label = (c && table && table[c]) || '';
            // site decisions 152: its Norwegian words (`labels.json` "_nb"), for Norwegian only
            // and the labels setting
            a.labelNb = (c && table && table._nb && table._nb[c]) || '';
          });
        });
        return res;
      });
    });
  }

  /**
   * The headwords of `shard` that continue `typed` (folded `p`), in the autocomplete order: the
   * continuations reached only through the accent fold (their own first letters differ from the
   * typed ones) after every other match, as ordbokene: its `e` never reaches `én`; each group by
   * length, then capitalisation against the prefix as typed (decisions 55), then folded, then as
   * spelled — `suggest_order` in build_index.py. Each hit keeps its shard.
   */
  function completions(shard, p, typed) {
    var bp = bare(p), hits = [];
    for (var i = 0; i < shard.headList.length; i++) {
      var h = shard.headList[i];
      if (h.b.lastIndexOf(bp, 0) === 0 && accentMatch(p, h.f)) {
        hits.push({ w: h.w, f: h.f, b: h.b, n: h.n, shard: shard });
      }
    }
    hits.forEach(function (h) {
      h.later = h.b.length > p.length && h.f.slice(0, p.length) !== p ? 1 : 0;
      h.cd = caseDistance(typed, h.w);
    });
    hits.sort(function (a, b) {
      return (a.later - b.later) || (a.w.length - b.w.length) || (a.cd - b.cd) ||
        (a.f < b.f ? -1 : a.f > b.f ? 1 : 0) || (a.w < b.w ? -1 : a.w > b.w ? 1 : 0);
    });
    hits.forEach(function (h, i) { h.at = i; });     // the present order, the tie-breaker
    return hits;
  }

  /**
   * The autocomplete's ranks (brief 59b items 13 and 14, Robin 2026-10-19 — deliberate
   * divergences: ordbokene ranks by length, then alphabet): 0 the exact match (`b`, the bare
   * query), whatever its status; 1 the one-word headwords that are translated (a word standing
   * for several articles is translated if any of them is); 2 the Norwegian-only ones; 3 the set
   * phrases (a headword with a space: a reader typing a word usually wants a headword, and a
   * trailing space brings up the phrases); 4 the continuations reached only through the accent
   * fold, last as before (decisions 41/46: `e` never reaches `én`). Ranks 1 and 2 go by the
   * frequency band, highest first (decisions 55's `headword_bands`, carried in the shard as
   * `n`); everything else, and a tie, keeps the present order (`completions`). Hits carry
   * `translated`. build_index.py `suggest_rank`.
   */
  function suggestRank(h, b) {
    if (h.b === b) { return 0; }
    if (h.later) { return 4; }
    if (h.w.indexOf(' ') !== -1) { return 3; }
    return h.translated ? 1 : 2;
  }
  function rankSuggestions(hits, b) {
    hits.forEach(function (h) { h.rank = suggestRank(h, b); });
    return hits.sort(function (x, y) {
      return (x.rank - y.rank) ||
        ((x.rank === 1 || x.rank === 2) ? (y.n - x.n) : 0) || (x.at - y.at);
    });
  }

  /**
   * The text the autocomplete answers for: leading spaces dropped and every run of spaces one
   * space, a TRAILING space kept (brief 59b item 10, Robin 2026-10-19). -> {query, trailing}
   * or null when the guard refuses it.
   */
  function suggestQuery(prefix) {
    var raw = prefix == null ? '' : String(prefix);
    var g = guard(raw);
    if (!g.ok) { return null; }
    return { query: g.query.replace(/\s+/g, ' '), trailing: /\s$/.test(raw) };
  }

  /**
   * Autocomplete: headword-prefix matches in the prefix's own shard (`completions`), each
   * tagged translated / Norwegian only, up to `maxSuggestions` (a one-character prefix on a
   * split letter reads `<letter>-top`: at most 50).
   *
   * A trailing space is honoured (brief 59b item 10, Robin 2026-10-19 — a deliberate
   * divergence: ordbokene's suggest API honours it, its site trims it): "fy " offers the word
   * itself first (if a headword), then the set phrases beginning "fy " in the same order
   * (fy faen, fy flate, fy søren, fy til katta …; alternation variants are stored expanded),
   * then the ordinary completions of "fy" filling the rest. The search itself still trims.
   * build_index.py `Index.suggest`.
   */
  function suggest(prefix, limit) {
    var sq = suggestQuery(prefix);
    if (!sq) { return Promise.resolve([]); }
    var p = fold(sq.query);
    limit = limit || config.maxSuggestions;
    var loads = [loadShard(suggestKey(p)), loadTranslated()];
    // the set phrases "<word> " live in the shard of "<word> " (for a one-letter word on a
    // split letter that is `<letter>-misc`, not the `-top` file the word itself reads)
    if (sq.trailing) { loads.push(loadShard(shardKey(p + ' '))); }
    var mark = function (h) {
      h.ids = h.shard.heads[h.w] || [];
      h.translated = h.ids.some(function (id) { return translated.has(id); });
      return h;
    };
    return Promise.all(loads).then(function (r) {
      var bp = bare(p);
      // items 13, 14: the order is set over every match, and only then cut to `limit`
      var hits = rankSuggestions(completions(r[0], p, sq.query).map(mark), bp);
      if (sq.trailing) {
        var seen = Object.create(null), merged = [];
        var add = function (h) { if (!seen[h.w]) { seen[h.w] = 1; merged.push(h); } };
        hits.forEach(function (h) { if (h.b === bp) { add(h); } });         // the word itself
        completions(r[2], p + ' ', sq.query + ' ').map(mark).forEach(add);  // its set phrases
        hits.forEach(add);                     // then the rest, ranked as without the space
        hits = merged;
      }
      // brief 59b item 11: one article's word class rides along (`pos`, '' for several)
      return mergeArticles(hits).slice(0, limit).map(function (h) {
        var one = h.ids.length === 1 ? h.shard.words[String(h.ids[0])] : null;
        var item = { word: h.w, ids: h.ids, translated: h.translated, pos: (one && one[2]) || '' };
        if (one) {
          item.line = typedLine(one, h.forms, p);
        } else {
          // each numbered by the form the row stands for (decisions 93)
          item.articles = h.ids.map(function (id) { return article(h.shard, id, h.w); }).sort(resultOrder);
        }
        return item;
      });
    });
  }

  /**
   * One suggestion per article (site decisions 82, Robin 2026-10-21 — a deliberate divergence:
   * ordbokene suggests per form). The rows are built per form as before and ranked; then a row
   * leading to ONE article takes in every later row leading to that same article, keeping the
   * place of its best-ranked form (`w`, what choosing it searches) and listing the forms that
   * merged (`forms`). A form several articles share keeps its own "N articles" row and never
   * merges into an article's row, so the search showing them all stays on offer; the article may
   * then also have its own row, by a form of its own. build_index.py `merge_articles`.
   */
  function mergeArticles(hits) {
    var byId = Object.create(null), out = [];
    hits.forEach(function (h) {
      if (h.ids.length !== 1) { out.push(h); return; }
      var id = h.ids[0], row = byId[id];
      if (row) { row.forms.push(h.w); return; }
      byId[id] = h;
      h.forms = [h.w];
      out.push(h);
    });
    return out;
  }

  /**
   * The dropdown's sections (site decisions 86, Robin 2026-10-22: the style lab's frame D2-136L).
   * `items` are `suggest`'s rows, already ranked and cut to 20; `typed` the box's text as typed.
   * The rows stay in their ranked order, and the run of one-word *Norwegian only* headwords
   * (rank 2: after the translated ones, rank 1) is the section the dropdown draws under its
   * "Norwegian only" label; the exact match (rank 0) is never in it, whatever its status
   * (decisions 59: the exact match first, always), nor are the set phrases (rank 3), which stay
   * below the headwords where the ranking puts them, nor what comes after them. **After a
   * trailing space** (decisions 59's rule: the query asks for set phrases) the set phrases are
   * grouped as the headwords are: the exact match first, then every translated row, then every
   * untranslated row — the section — each group in its ranked order. A row is untranslated when
   * none of its articles is (`translated`, as `suggest` marks it), so an "N articles" row whose
   * articles are all untranslated falls in the section too. Presentation only: what `suggest`
   * returns, and its Python twin, are unchanged, and the rows are not copied or marked.
   * -> {rows, start, end}: the rows in the order to draw them, the section `rows[start..end)`
   * (`start` -1, and `end` -1, when there is none).
   */
  function suggestSections(items, typed) {
    var raw = typed == null ? '' : String(typed);
    var sq = suggestQuery(raw);
    var bq = sq ? bare(fold(sq.query)) : null;
    var exact = function (it) { return bq !== null && bare(fold(it.word)) === bq; };
    var rows = (items || []).slice();
    var trailing = !!(sq && sq.trailing);
    if (trailing) {
      var ex = [], tr = [], no = [];
      rows.forEach(function (it) { (exact(it) ? ex : it.translated ? tr : no).push(it); });
      rows = ex.concat(tr, no);
    }
    var start = -1, end = -1;
    for (var i = 0; i < rows.length; i++) {
      var it = rows[i];
      var nb = !it.translated && !exact(it) && (trailing || it.word.indexOf(' ') === -1);
      if (start < 0) { if (nb) { start = i; } }
      else if (!nb) { end = i; break; }
    }
    if (start >= 0 && end < 0) { end = rows.length; }
    return { rows: rows, start: start, end: end };
  }

  /**
   * A one-article suggestion's headword line (decisions 82): the article's own forms in its order
   * (`words[id][0]`, "dannet / danna"), each marked `match` where it continues what was typed
   * (folded `p`, as `completions` tests it) — drawn bold. An expression stored as its alternation
   * variants (`words[id][3]`) shows the variants that matched instead, as the result list does; a
   * merged form the stored line leaves out (it keeps three forms, then "…") is added after them.
   * -> [{w, match}], with a final {w: '…'} when the stored line was cut.
   */
  function headLine(one, forms, p) {
    var bp = bare(p);
    var matches = function (w) { return bare(w).lastIndexOf(bp, 0) === 0 && accentMatch(p, fold(w)); };
    var text = one[0] || '', cut = / …$/.test(text);
    var shown = one[3] ? forms.slice() : text.replace(/ …$/, '').split(SEP);
    forms.forEach(function (w) { if (shown.indexOf(w) === -1) { shown.push(w); } });
    var line = shown.filter(Boolean).map(function (w) { return { w: w, match: matches(w) }; });
    if (cut && !one[3]) { line.push({ w: '\u2026', match: false }); }
    return line;
  }

  /**
   * A one-article suggestion's line since site decisions 150 (Robin, 2026-10-29: "writing "selv"
   * the suggestions only show the "selv..." forms of the compunds, not the "sjøl...""): the ONE
   * spelling of the article that continues what was typed — "selv" -> *selvsagt*, "sjøl" ->
   * *sjølsagt*, as ordbokene's suggestions show each spelling apart — the first in our lemma
   * order where several do (`headLine`'s order: the article's own). The part carries that spelling's
   * `hg` (`formHg`, decisions 93), but the row draws no numeral (`shell.js` `drawLine`; 148's follow-up,
   * Robin 2026-10-29: a numeral only where a row shows more than one word of one form). One row per word, as before; the article and the list view keep the
   * whole headword line. -> [{w, match: true, hg}]. The row searches that spelling (shell.js).
   */
  function typedLine(one, forms, p) {
    var line = headLine(one, forms, p), pick = null;
    for (var i = 0; i < line.length; i++) { if (line[i].match) { pick = line[i].w; break; } }
    if (pick == null) { pick = forms[0]; }
    return [{ w: pick, match: true, hg: formHg(one, pick) }];
  }

  /**
   * Optimal string alignment (Damerau–Levenshtein without repeated edits), with a cutoff:
   * a row whose cheapest cell already exceeds `cutoff` ends the comparison.
   */
  function distance(a, b, cutoff) {
    var la = a.length, lb = b.length;
    if (Math.abs(la - lb) > cutoff) { return cutoff + 1; }
    var prev2 = null, prev = new Array(lb + 1), cur = new Array(lb + 1), i, j;
    for (j = 0; j <= lb; j++) { prev[j] = j; }
    for (i = 1; i <= la; i++) {
      cur[0] = i;
      var rowMin = i;
      for (j = 1; j <= lb; j++) {
        var cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
        var v = Math.min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
        if (i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1)) {
          v = Math.min(v, prev2[j - 2] + 1);
        }
        cur[j] = v;
        if (v < rowMin) { rowMin = v; }
      }
      if (rowMin > cutoff) { return cutoff + 1; }
      prev2 = prev; prev = cur; cur = prev2.slice();
    }
    return prev[lb];
  }

  /**
   * Bag distance (build_index.py `bag_distance`, decisions 56): the larger of the letters only
   * one string has and only the other has, as multisets — a lower bound of `distance` and a
   * metric, so the similar pass can skip the OSA table for a candidate that cannot qualify.
   * Never changes an answer. `counts` is charCounts(a), `n` its length.
   */
  function charCounts(s) {
    var out = Object.create(null);
    for (var i = 0; i < s.length; i++) { var ch = s.charAt(i); out[ch] = (out[ch] || 0) + 1; }
    return out;
  }
  function bagDistance(counts, n, w) {
    var seen = Object.create(null), extra = 0;
    for (var i = 0; i < w.length; i++) {
      var ch = w.charAt(i), k = (seen[ch] || 0) + 1;
      seen[ch] = k;
      if (k > (counts[ch] || 0)) { extra++; }
    }
    return Math.max(extra, n - (w.length - extra));
  }

  /* The similar-headwords limits — build_index.py `letter_limit`, `word_limit`, `words_limit`. */
  function letterLimit(n) { return Math.max(1, Math.floor(n / config.similarPer)); }
  function wordLimit(n) { return Math.floor(n / config.similarPer); }
  function wordsLimit(m) { return Math.max(1, Math.floor(m / config.similarPer)); }

  function sameWord(a, b) {
    if (a === b) { return true; }
    var lim = wordLimit(a.length);
    return lim > 0 && distance(a, b, lim) <= lim;
  }

  /** The most words `qw` and `cw` share IN ORDER (an LCS with `sameWord` as equality). */
  function sharedWords(qw, cw) {
    var k = cw.length, prev = new Array(k + 1), cur, i, j;
    for (j = 0; j <= k; j++) { prev[j] = 0; }
    for (i = 0; i < qw.length; i++) {
      cur = new Array(k + 1); cur[0] = 0;
      for (j = 1; j <= k; j++) {
        cur[j] = sameWord(qw[i], cw[j - 1]) ? prev[j - 1] + 1 : Math.max(prev[j], cur[j - 1]);
      }
      prev = cur;
    }
    return prev[k];
  }

  function cmpStr(a, b) { return a < b ? -1 : (a > b ? 1 : 0); }

  /**
   * The five nearest headwords (lookup-index.md § 4 (3)) — build_index.py `Index.similar`.
   * Candidates: the query's own first-character bucket. A candidate qualifies by LETTERS — OSA
   * distance at most letterLimit(query length) — or, for a query of two words or more, by
   * WORDS: at least two words in common in order (a typo inside a word tolerated, wordLimit
   * per word), and at most wordsLimit(m) words differing.
   *
   * `wide` (decisions 55; on a hit and a miss alike since decisions 56 — the default; `false`
   * is kept only to measure against): (2) the `tails/` files reach a wrong first letter
   * (vus -> hus) and a missing one (us -> hus), the second letter's bucket an extra letter in
   * front (ohus -> hus); (1) each spelling-variation rewrite is searched in its own first
   * letter's bucket: a rewrite that lands on a headword costs nothing (kordan -> hvordan at 0),
   * a candidate near a rewrite costs 1 + its distance from it, within the same limit; and a
   * rewrite that is an inflected form in the query's own shard is offered itself, at 0. A
   * chained rewrite (two rules, kæm -> kem -> hvem) costs the same; under a limit of 1 only an
   * exact landing qualifies, so a rewrite is looked up by bare form (`bucketByBare`).
   *
   * Ranked (Robin, 2026-10-19): words differing (a word match first), letter distance,
   * capitalisation against the query as typed (caseDistance), the higher frequency band, the query's first letter before another, length difference, folded
   * form, form. Another
   * variant of the query's own article is listed like any other headword, as ordbokene lists
   * it (en vond sirkel -> en ond sirkel). Accents are folded before comparing, so an accent is
   * never an edit; a form the lookup itself finds is not listed, the other direction is, at 0
   * (à la carte -> a la carte).
   */
  /** One bucket of a loaded headwords file keyed by bare form (build_index.py `by_bare`). */
  function bucketByBare(file, c) {
    var m = file.byBare[c];
    if (!m) {
      m = file.byBare[c] = Object.create(null);
      var b = file.buckets[c] || [];
      for (var i = 0; i < b.length; i++) { (m[b[i].b] || (m[b[i].b] = [])).push(b[i]); }
    }
    return m;
  }

  function similar(q, n, wide) {
    wide = wide !== false;      // a hit's list is built as a miss's (decisions 56)
    var g = guard(q);
    if (!g.ok) { return Promise.resolve([]); }
    var fq = fold(g.query), f = bare(fq);
    n = n || config.similarCount;
    var lim = letterLimit(f.length);
    var qw = f.split(/\s+/), m = qw.length;
    var wlim = m > 1 ? wordsLimit(m) : -1;
    var rw = wide ? rewrites(f) : [];
    var own = shardKey(f);
    var widen = !!wide && f.length > 1;
    var loads = [loadHeadwords(letterKey(f))];
    if (widen) {
      loads.push(loadTails(remainderKey(f.slice(1))), loadTails(remainderKey(f)),
        loadHeadwords(letterKey(f.slice(1))));
    }
    var needShard = false;
    rw.forEach(function (r) {
      loads.push(loadHeadwords(letterKey(r)));
      if (shardKey(r) === own) { needShard = true; }
    });
    var shardP = needShard ? loadShard(own) : Promise.resolve(null);
    return Promise.all([Promise.all(loads), shardP]).then(function (res) {
      var files = res[0], shard = res[1];
      var cands = Object.create(null), list = [];
      var keep = function (e, wd, d) {
        var c = cands[e.w];
        if (!c) {
          c = cands[e.w] = { wd: wd, dist: d, cd: caseDistance(g.query, e.w),
            first: e.b.charAt(0) === f.charAt(0) ? 0 : 1,
            band: e.n, gap: Math.abs(e.b.length - f.length), f: e.f, word: e.w, page: !!e.p,
            count: e.c == null ? null : e.c, tr: !!e.x, pos: e.k || '' };
          list.push(c);
        } else {
          if (wd < c.wd) { c.wd = wd; }
          if (d < c.dist) { c.dist = d; }
        }
      };
      var pool = (files[0].buckets[f.charAt(0)] || []);
      if (widen) {
        pool = pool.concat(files[1], files[2], files[3].buckets[f.charAt(1)] || []);
      }
      var qc = charCounts(f), qn = f.length, bags = Object.create(null);
      var bagOf = function (bw) {
        var b = bags[bw];
        if (b === undefined) { b = bags[bw] = bagDistance(qc, qn, bw); }
        return b;
      };
      var seen = Object.create(null);
      for (var i = 0; i < pool.length; i++) {
        var cand = pool[i];
        if (seen[cand.w]) { continue; }
        seen[cand.w] = 1;
        if (cand.b === f && accentMatch(fq, cand.f)) { continue; }   // the query, or a hit
        var gap = Math.abs(cand.b.length - f.length);
        // the bag distance is a lower bound of OSA: past the limit, no table is needed
        var d = gap <= lim && bagOf(cand.b) <= lim ? distance(f, cand.b, lim) : lim + 1;
        var wd = wlim + 1;
        if (wlim > 0 && cand.b.indexOf(' ') !== -1) {
          var cw = cand.ws || (cand.ws = cand.b.split(/\s+/));
          if (Math.abs(cw.length - m) <= wlim) {
            var c = sharedWords(qw, cw), diff = Math.max(m, cw.length) - c;
            if (c >= 2 && diff <= wlim) { wd = diff; }
          }
        }
        if (d > lim && wd > wlim) { continue; }
        if (d > lim) { d = distance(f, cand.b, f.length + cand.b.length); }
        keep(cand, wd, d);
      }
      var base = widen ? 4 : 1, near = lim - 1;     // 1 + a distance within the limit
      rw.forEach(function (r, k) {
        var bucket = near < 1 ? (bucketByBare(files[base + k], r.charAt(0))[r] || [])   // exact only
          : (files[base + k].buckets[r.charAt(0)] || []);
        var rb = bagDistance(qc, qn, r);
        for (var i = 0; i < bucket.length; i++) {
          var e = bucket[i];
          if (e.b === f && accentMatch(fq, e.f)) { continue; }
          // bag(r, b) >= bag(q, b) - bag(q, r): a candidate that cannot come within `near` of
          // the rewrite is skipped without its OSA table (decisions 56)
          if (Math.abs(e.b.length - r.length) <= near && bagOf(e.b) - rb <= near) {
            // a rewrite costs nothing only where it lands exactly; a candidate near it costs
            // 1 + its distance from it (Robin, 2026-10-19)
            var d = distance(r, e.b, near);
            if (d <= near) { keep(e, wlim + 1, d ? d + 1 : 0); }
          }
        }
        if (shard && shardKey(r) === own) {        // a rewrite that is an inflected form
          var hit = (shard.foldedForms[r] || []).slice().sort();
          if (hit.length && !shard.foldedHeads[r]) {
            // c 0: a form, not a headword (site decisions 144: its row says whose form it is)
            keep({ w: hit[0], f: fold(hit[0]), b: r, n: 0, p: !!shard.pages[fold(hit[0])], c: 0 }, wlim + 1, 0);
          }
        }
      });
      list.sort(function (a, b) {
        return (a.wd - b.wd) || (a.dist - b.dist) || (a.cd - b.cd) || (b.band - a.band) || (a.first - b.first) ||
          (a.gap - b.gap) || cmpStr(a.f, b.f) || cmpStr(a.word, b.word);
      });
      // site decisions 117: `page`, the address of the word's own page where it has one;
      // site decisions 144: what its row after a miss needs — `count` the articles it heads (0:
      // an inflected form only; null: a file built before 144), `translated`, `pos` (one article)
      return list.slice(0, n).map(function (s) {
        return { word: s.word, dist: s.dist, page: s.page ? pagePath(s.f) : null,
                 count: s.count, translated: s.tr, pos: s.pos };
      });
    });
  }

  function loadRandom() {
    if (randomList) { return Promise.resolve(randomList); }
    if (randomPending) { return randomPending; }
    randomPending = Promise.resolve(loader('random.json')).then(function (list) {
      randomList = list || [];
      randomPending = null;
      return randomList;
    });
    return randomPending;
  }

  /** A random headword for the Random word button (plan § 1.1), opened as its search, as
   * ordbokene's (decisions 115, Robin 2026-10-24): drawn from `random.json`, the headwords whose
   * search shows first an article that is translated, not a set phrase and has a summary gloss
   * (decisions 67's bar; build_index.py `random_headwords`). Until decisions 115 the file held
   * article ids, and an id still drawn (an old copy of the file) is returned as it is. */
  function randomHeadword() {
    return loadRandom().then(function (list) {
      if (!list || !list.length) { return null; }
      return list[Math.floor(Math.random() * list.length)];
    });
  }

  /* ------------------------------------- Random word in English (site decisions 155) */

  var randomEnData = null;
  var randomEnPending = null;
  function loadRandomEnglish() {
    if (randomEnData) { return Promise.resolve(randomEnData); }
    if (randomEnPending) { return randomEnPending; }
    randomEnPending = Promise.resolve(loader('random-en.json')).then(function (data) {
      randomEnData = data && data.n ? data : { n: {} };
      randomEnPending = null;
      return randomEnData;
    });
    return randomEnPending;
  }

  /** The words of one English file that Random word draws from (site decisions 155): the keys
   *  filed under that file's own letter (`enLetter`; a phrase or an irregular pair a file also
   *  carries for another letter's sake is drawn from that letter's file only, so each word is in
   *  one file) that the suggestions can offer — the key its own display reaches when typed
   *  (`enNorm`), which leaves out a key like "the point", whose "the" the search drops.
   *  build_index.py `english_random` counts the same keys. Sorted, as `loadEnglish` sorts. */
  function enPool(shard, letter) {
    if (!shard.pool) {
      shard.pool = shard.keys.filter(function (k) {
        return enLetter(k) === letter && enNorm((shard.d && shard.d[k]) || k) === k;
      });
    }
    return shard.pool;
  }

  /**
   * An English word for Random word with "Search English words" on (site decisions 155, Robin
   * 2026-10-31: "it chooses a random English word (instead of a Norwegian one)"; the pool his
   * pick, "Yes, every word"): every English word the English suggestions can offer, each equally
   * likely, as it is displayed (what a picked suggestion searches, shell.js `submit`). No list of
   * its own: `random-en.json` holds only how many words each English file holds
   * (build_index.py `english_random`, `{n: {letter: count}}`), so ONE draw over the total picks
   * the file and the place in it — a file weighted by its count, the word uniform inside it, each
   * word 1 / total — and that file is the one the word's search reads anyway. Should a file
   * disagree with its count (an older copy of one of them), the word is drawn uniformly from the
   * file as it is. -> a promise of the word, or null.
   */
  function randomEnglish() {
    return loadRandomEnglish().then(function (data) {
      var letters = Object.keys(data.n).sort(), total = 0, i;
      for (i = 0; i < letters.length; i++) { total += data.n[letters[i]] || 0; }
      if (!total) { return null; }
      var r = Math.min(Math.floor(Math.random() * total), total - 1);
      for (i = 0; i < letters.length; i++) {
        var n = data.n[letters[i]] || 0;
        if (r < n) { break; }
        r -= n;
      }
      var letter = letters[i];
      return loadEnglish(letter).then(function (shard) {
        var pool = enPool(shard, letter);
        if (!pool.length) { return null; }
        var k = pool.length === data.n[letter] ? pool[r] : pool[Math.floor(Math.random() * pool.length)];
        return (shard.d && shard.d[k]) || k;
      });
    });
  }

  /**
   * The articles a search shows, in the order it shows them (`render`): every headword group's
   * articles in turn (each group in `resultOrder`), then the translated ones before the
   * untranslated across the groups (brief 59b item 12) — the full results and the list view
   * alike. The inflected-form rows are not among them. -> {all, done, todo}.
   * build_index.py `first_shown`, which builds Random word's pool from the first (decisions 115).
   */
  function shownOrder(res) {
    var all = [];
    ((res && res.heads) || []).forEach(function (grp) { all = all.concat(grp.articles); });
    return {
      all: all,
      done: all.filter(function (a) { return a.translated; }),
      todo: all.filter(function (a) { return !a.translated; })
    };
  }
  /** The id of the article a search shows first, or null (decisions 115). */
  function firstShown(res) {
    var o = shownOrder(res), a = o.done[0] || o.todo[0];
    return a ? a.id : null;
  }

  function articleUrl(id) { return config.base + 'bm-en/' + id + '/'; }
  /** A search's address: the query in the FRAGMENT (`/bm-en/#q=hus`), which a browser never
   *  sends to a server, so the search does not reach the host in a request line or a Referer
   *  (site decisions 104, R2; until 2026-10-23 it was `/bm-en/?q=hus`, still read). */
  function searchUrl(q) { return config.base + 'bm-en/#q=' + encodeURIComponent(q); }

  /* ------------------------------------------- word pages (site decisions 117) */

  /** The address of the page for the folded search `fq` — `/bm-en/s%C3%A5/`: every character
   *  outside A-Z a-z 0-9 _ . - ~ percent-encoded, the same string the build writes
   *  (`wordpages.word_path`, Python's `quote(fq, safe="")`; `encodeURIComponent` keeps
   *  ! ' ( ) * as they are, so those are encoded here too). */
  function pagePath(fq) {
    return config.base + 'bm-en/' + encodeURIComponent(fq).replace(/[!'()*]/g, function (c) {
      return '%' + c.charCodeAt(0).toString(16).toUpperCase();
    }) + '/';
  }

  /** Whether the search `q` has a page of its own — a word page (a headword search whose first
   *  article is translated) or a form page (a common irregular form): the build's answer,
   *  carried in the query's own shard (`p`, `pf`; `prepare`), which the search loads anyway.
   *  -> a promise of the page's address, or null (the search stays `#q=`). */
  function pageFor(q) {
    var g = guard(q);
    if (!g.ok) { return Promise.resolve(null); }
    var fq = fold(g.query);
    return Promise.resolve(loadShard(shardKey(fq))).then(function (shard) {
      return shard && shard.pages && shard.pages[fq] ? pagePath(fq) : null;
    }, function () { return null; });
  }

  /** Where a search made on a page that answers searches in place goes in the address bar: its
   *  page, else `/bm-en/#q=<q>` (decisions 104). -> a promise of the address. */
  function address(q) {
    return pageFor(q).then(function (url) { return url || searchUrl(q); });
  }

  /** Where a search made on any other page opens (the box's submit, Random word): its page with
   *  the search after `#` — `/bm-en/så/#q=Så`, the mark a word page reads as a search the reader
   *  made (`ordparSearch.wordPage`: recorded in History as the search page records one, the
   *  address then cleaned to `/bm-en/så/`), `&random` after it for a draw — else
   *  `/bm-en/#q=<q>` as before. -> a promise of the address. */
  function searchAddress(q, drawn) {
    var mark = drawn ? DRAWN_MARK : '';
    return pageFor(q).then(function (url) {
      return (url ? url + '#q=' + encodeURIComponent(String(q).trim()) : searchUrl(String(q).trim())) + mark;
    });
  }

  /**
   * The built title of the page the address names, for the search `res` answered on it (site
   * decisions 131: 117's one style — a search answered in place titles the tab as the page it
   * stands on is built). -> a promise of null when the address is not this search's own word or
   * form page (`/bm-en/#q=…`, a search page, a mistyped word with no page: the caller's
   * "q — Ordpar" stays); `{one: id}` for a word page of one article, whose title is that
   * article's own (`wordpages.article_meta`); else `{title}`, "så — Norwegian–English dictionary"
   * (`wordpages.several_title`): the page's word as `build_index.page_plan` picks it — of the
   * headword spellings that fold to the search, sorted, the first that holds the article shown
   * first, else the first; for a form page (no such headword) the first inflected-form row's
   * form — and the dictionary's name, `strings["dictionary_name"]` (the shell pages carry it in
   * their inline strings, `build_index.copy_shell`; never a fixed copy).
   */
  function pageTitle(res) {
    var here = pathWord(global.location && global.location.pathname);
    if (!res || !here || here !== res.folded) { return Promise.resolve(null); }
    return pageFor(res.query).then(function (url) {
      if (!url) { return null; }
      var heads = [], ids = Object.create(null), n = 0;
      res.heads.forEach(function (grp) {
        if (fold(grp.form) === res.folded && heads.indexOf(grp.form) === -1) { heads.push(grp.form); }
        grp.articles.forEach(function (a) { if (!ids[a.id]) { ids[a.id] = 1; n++; } });
      });
      heads.sort();
      var word = null;
      if (heads.length) {
        if (n === 1) { return { one: firstShown(res) }; }
        var first = firstShown(res);
        var holds = res.heads.filter(function (grp) {
          return grp.articles.some(function (a) { return a.id === first; });
        }).map(function (grp) { return grp.form; });
        word = heads.filter(function (f) { return holds.indexOf(f) !== -1; })[0] || heads[0];
      } else {
        var rows = res.forms.filter(function (grp) { return grp.articles.length; });
        word = rows.length ? rows[0].form : null;
      }
      return word ? { title: word + ' — ' + t('dictionary_name') } : null;
    }, function () { return null; });
  }

  /** The folded search a page path names (`/bm-en/s%C3%A5/` -> `så`), or null (an article's
   *  `/bm-en/<id>/`, `/bm-en/`, anything else). `wordpages.path_word`. */
  function pathWord(path) {
    var b = config.base;
    if (!path || path.indexOf(b) !== 0) { return null; }
    var m = /^bm-en\/([^\/]+)\/?(?:index\.html)?$/.exec(path.slice(b.length));
    if (!m) { return null; }
    var w;
    try { w = decodeURIComponent(m[1]); } catch (e) { return null; }
    return /^\d+$/.test(w) ? null : fold(w);
  }

  /* The form labels (site decisions 117): the words of each code in the shards' `t`, carried
   * once (`labels.json`), fetched with the first search that shows an inflected-form row. */
  var labelTable = null;
  var labelPending = null;
  function loadLabels() {
    if (labelTable) { return Promise.resolve(labelTable); }
    if (labelPending) { return labelPending; }
    labelPending = Promise.resolve(loader('labels.json')).then(function (data) {
      labelTable = data || {};
      labelPending = null;
      return labelTable;
    }, function () { labelPending = null; return {}; });
    return labelPending;
  }

  /** The code of (form, id) in a shard's `t`: one character per (form, article), the forms
   *  sorted and each form's ids in their stored order (most common first, decisions 143) — as `n` aligns with the
   *  headwords (build_index.py `write_index`). */
  function labelCode(shard, form, id) {
    var t = shard.t || '';
    if (!t) { return ''; }
    if (!shard.labelAt) {
      var at = Object.create(null), k = 0;
      Object.keys(shard.forms).sort().forEach(function (f) {
        at[f] = k;
        k += shard.forms[f].length;
      });
      shard.labelAt = at;
    }
    var start = shard.labelAt[form];
    if (start === undefined) { return ''; }
    var i = shard.forms[form].indexOf(id);
    return i < 0 ? '' : t.charAt(start + i);
  }

  /* ---------------------------------------- the English search (site decisions 148) */

  /*
   * Robin, 2026-10-29: "a kind of "switch" underneath the search, where switching it on makes you
   * search for the English equivalents instead of the Norwegian headword". The index is the summary
   * glosses (build_index.py `english_index`, `english_files`; lookup-index.md § 3b): one file per
   * first letter of the key, `en/<letter>.json`, so a search, its suggestions and its similar words
   * read ONE file — `e` {key: [[id, unit, place, start, end], …]}, `a` {id: [headword text, hg, pos,
   * band, rank, units]}, `d` {key: display}, `sp` {american: british}, `ir` {irregular form: base},
   * `c` the articles indexed and `p` their share of the dictionary (the miss line's numbers).
   * Every article in it is translated (only translated rows are indexed).
   */
  var EN_DIR = 'en/';
  var enShards = {};
  var enPending = {};
  var EN_EDGE = /^[\s.,;:!?'"‘’“”\-–—\/]+|[\s.,;:!?'"‘’“”\-–—\/]+$/g;

  /** A query as the English index compares it: lower case, spaces collapsed, the edges trimmed,
   *  one leading "to ", "a ", "an ", "the " dropped (build_index.py `en_norm`). */
  function enNorm(s) {
    s = String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').replace(EN_EDGE, '');
    var m = /^(to|a|an|the) (.+)$/.exec(s);
    return m ? m[2].replace(EN_EDGE, '') : s;
  }

  /** The English shard of a key: its first bare character, a to z, else `misc`
   *  (build_index.py `en_letter`). */
  function enLetter(k) {
    var c = bare(String(k || '')).charAt(0);
    return c >= 'a' && c <= 'z' ? c : MISC;
  }

  function loadEnglish(letter) {
    if (enShards[letter]) { return Promise.resolve(enShards[letter]); }
    if (enPending[letter]) { return enPending[letter]; }
    enPending[letter] = Promise.resolve(loader(EN_DIR + letter + '.json')).then(function (raw) {
      var shard = raw || { k: letter, e: {}, a: {}, d: {}, sp: {}, ir: {}, missing: true };
      shard.keys = Object.keys(shard.e || {}).sort();
      enShards[letter] = shard;
      delete enPending[letter];
      return shard;
    });
    return enPending[letter];
  }

  /** One English tails file (`en/tails/<k2>-<k3>.json`, site decisions 148's follow-up): the
   *  one-word keys filed by their second and third characters, with what a similar row needs —
   *  `e` {key: [[id, unit, place], …]}, `a` {id: [first spelling, its numeral, pos, band, rank]},
   *  `d` — read by the similar words only, after the results are painted. A missing file reads
   *  as empty. build_index.py `english_tails`. */
  var enTails = {};
  var enTailsPending = {};
  function loadEnglishTails(key) {
    if (enTails[key]) { return Promise.resolve(enTails[key]); }
    if (enTailsPending[key]) { return enTailsPending[key]; }
    enTailsPending[key] = Promise.resolve(loader(EN_DIR + 'tails/' + key + '.json')).then(function (raw) {
      var file = raw || { t: key, e: {}, a: {}, d: {}, missing: true };
      enTails[key] = file;
      delete enTailsPending[key];
      return file;
    });
    return enTailsPending[key];
  }

  /** The query and, where the spelling map changes it, its British form (word by word). */
  function enVariants(q, shard) {
    var sp = (shard && shard.sp) || {};
    var t = q.split(' ').map(function (w) { return Object.prototype.hasOwnProperty.call(sp, w) ? sp[w] : w; }).join(' ');
    return t !== q ? [q, t] : [q];
  }

  /** One article of an English shard as the rows draw it: `word` the headword text (" / "
   *  between spellings, as `article`), `hg` / `hgs` as `article`, `first` its first spelling and
   *  `firstHg` that spelling's numeral (Robin, 2026-10-29: "enough to show the Norwegian
   *  main-lemma"), `band`, `rank`, `units` its summary gloss as the site draws it. */
  function enArticle(shard, id) {
    var x = shard.a[String(id)] || ['', 0, '', 0, 0, []];
    var a = { id: Number(id), word: x[0], pos: x[2] || '', translated: true,
              band: x[3] || 0, rank: x[4] || 0, units: x[5] || [] };
    if (Array.isArray(x[1])) {
      a.hgs = x[1].slice();
      a.hg = formHg(x, null);
    } else { a.hg = x[1] || 0; }
    a.first = String(x[0] || '').replace(/ …$/, '').split(SEP)[0];
    a.firstHg = a.hgs ? (a.hgs[0] || 0) : a.hg;
    return a;
  }

  /** Order (c) (Robin, 2026-10-29: "C seems like a good compromise"): the equivalents in the
   *  gloss's units 1 and 2 as one tier, then those in unit 3 on; inside a tier the Norwegian
   *  word's band, highest first; then the earlier unit, the place in the unit, the article's rank
   *  (the suggestions' own tie-break). build_index.py `EnglishIndex.order`. */
  function enOrder(shard) {
    return function (x, y) {
      var ax = shard.a[String(x.id)], ay = shard.a[String(y.id)];
      return ((x.unit <= 2 ? 0 : 1) - (y.unit <= 2 ? 0 : 1)) || (ay[3] - ax[3]) ||
        (x.unit - y.unit) || (x.pos - y.pos) || (ax[4] - ay[4]);
    };
  }

  /** The articles of one key, each once at its best place, in order (c). */
  function enArticlesOf(shard, key) {
    var seen = Object.create(null), list = [];
    (shard.e[key] || []).forEach(function (e) {
      if (!seen[e[0]]) { seen[e[0]] = 1; list.push({ id: e[0], unit: e[1], pos: e[2] }); }
    });
    return list.sort(enOrder(shard));
  }

  /** An English word as a row shows it: {key, word (its display, "AIDS"), arts: [enArticle]}. */
  function englishItem(shard, key) {
    return { key: key, word: (shard.d && shard.d[key]) || key,
             arts: enArticlesOf(shard, key).map(function (m) { return enArticle(shard, m.id); }) };
  }

  /**
   * Answer one English search: the articles whose summary gloss has the query as an equivalent,
   * exact equivalents only (Robin's pick in the lab), the British form of an American spelling
   * too, in order (c). -> {query, key, shard, matches: [{id, unit, pos, spans, article}], count}
   * — `spans` every matched equivalent's [unit, start, end] (the list view's bold).
   */
  function englishLookup(q) {
    var g = guard(q);
    if (!g.ok) { return Promise.resolve({ query: q, key: '', matches: [], count: 0, guard: g.reason }); }
    var p = enNorm(g.query);
    return loadEnglish(enLetter(p)).then(function (shard) {
      var by = Object.create(null), list = [];
      if (p) {
        enVariants(p, shard).forEach(function (v) {
          (shard.e[v] || []).forEach(function (e) {
            var m = by[e[0]];
            if (!m) { m = by[e[0]] = { id: e[0], unit: e[1], pos: e[2], spans: [] }; list.push(m); }
            else if (e[1] < m.unit || (e[1] === m.unit && e[2] < m.pos)) { m.unit = e[1]; m.pos = e[2]; }
            m.spans.push([e[1], e[3], e[4]]);
          });
        });
      }
      list.sort(enOrder(shard));
      list.forEach(function (m) { m.article = enArticle(shard, m.id); });
      return { query: g.query, key: p, shard: shard, matches: list, count: list.length };
    });
  }

  /**
   * The English suggestions (site decisions 148 item 4): one item per English word continuing
   * what was typed — the exact word, then the one-word continuations by the top band of their
   * Norwegian words, then the phrases by length (Robin's pick: the Norwegian suggestions' own
   * order), up to `maxSuggestions`. -> [englishItem]. build_index.py `EnglishIndex.suggest`.
   */
  function englishSuggest(prefix, limit) {
    var sq = suggestQuery(prefix);
    if (!sq) { return Promise.resolve([]); }
    var p = enNorm(sq.query);
    if (!p) { return Promise.resolve([]); }
    limit = limit || config.maxSuggestions;
    return loadEnglish(enLetter(p)).then(function (shard) {
      var vs = enVariants(p, shard), items = [];
      shard.keys.forEach(function (k) {
        var rank = -1;
        for (var i = 0; i < vs.length; i++) {
          if (k === vs[i]) { rank = 0; break; }
          if (k.lastIndexOf(vs[i], 0) === 0) {
            var r = k.indexOf(' ') < 0 ? 1 : 2;
            rank = rank < 0 ? r : Math.min(rank, r);
          }
        }
        if (rank < 0) { return; }
        var top = 0;
        shard.e[k].forEach(function (e) { top = Math.max(top, shard.a[String(e[0])][3]); });
        items.push({ k: k, rank: rank, top: top });
      });
      items.sort(function (x, y) {
        return (x.rank - y.rank) || (x.rank === 1 ? y.top - x.top : 0) ||
          (x.k.length - y.k.length) || cmpStr(x.k, y.k);
      });
      return items.slice(0, limit).map(function (x) { return englishItem(shard, x.k); });
    });
  }

  /** A word's possible stems for the similar English words (build_index.py `en_stems`): the
   *  lab's rough English without -er (swimming -> swim, houses -> house, tries -> try), then the
   *  base of an irregular form (`ir`: swam -> swim). Not a lemmatizer. */
  function enStems(w, ir) {
    var out = [w];
    var add = function (s) { if (s.length >= 3 && out.indexOf(s) < 0) { out.push(s); } };
    var cut = function (suf) {
      if (w.length < suf.length + 3 || w.slice(-suf.length) !== suf) { return; }
      var b = w.slice(0, -suf.length);
      add(b); add(b + 'e');
      if (b.length > 3 && b.charAt(b.length - 1) === b.charAt(b.length - 2)) { add(b.slice(0, -1)); }
    };
    cut('ing'); cut('ed'); cut('es'); cut('s');
    if (w.length > 4 && /ie[sd]$/.test(w)) { add(w.slice(0, -3) + 'y'); }
    var base = ir && Object.prototype.hasOwnProperty.call(ir, w) ? ir[w] : null;
    if (base && out.indexOf(base) < 0) { out.push(base); }
    return out;
  }

  function enTokens(k) { return k.split(/[\s\-]+/).filter(Boolean); }

  /**
   * The similar English words (site decisions 148 item 7, Robin 2026-10-29: "same way as the
   * Norwegian-English search does it"): five, first the word matches — a longer equivalent
   * holding the searched word as a whole word ("go swimming" for *swimming*) and a word sharing
   * its stem (*swim*) — then the one-word keys of the query's letter spelled alike, within
   * `letterLimit` edits (`distance`); ranked word match first, the distance, the top band of
   * their Norwegian words, the length, the key. Site decisions 149's rule: a word whose articles
   * are all among `shown` (ids on the page) is left out, the next taking its place.
   * Past the first letter (site decisions 148's follow-up, Robin 2026-10-29: "the English similar
   * words reach other first letters as the Norwegian ones do"), as `similar` reaches them: a
   * wrong first letter through the tails file of the query without its first character (*hoose*
   * -> *loose*, `en/tails/o-o`), a missing one through the query's own (*hoose* -> *choose*,
   * `en/tails/h-o`), an extra one through the second letter's English file, its one-word keys
   * starting with that letter (*xhouse* -> *house*, `en/h`); spelled alike only, ranked with the
   * rest. The caller fetches it after the results are painted (`renderEnglish`), so the search's
   * results keep their one request. -> [englishItem]. build_index.py `EnglishIndex.similar`.
   */
  function englishSimilar(q, n, shown) {
    var g = guard(q);
    if (!g.ok) { return Promise.resolve([]); }
    var p = enNorm(g.query);
    n = n || config.similarCount;
    if (p.length < 3) { return Promise.resolve([]); }
    var lim = letterLimit(p.length), on = shown || {}, b = bare(p);
    return Promise.all([loadEnglish(enLetter(p)), loadEnglishTails(remainderKey(b.slice(1))),
      loadEnglishTails(remainderKey(b)), loadEnglish(enLetter(b.slice(1)))]).then(function (got) {
      var shard = got[0];
      var ir = shard.ir || {}, vs = enVariants(p, shard), L = enLetter(p);
      var mine = enStems(p, ir).concat(vs), out = [];
      shard.keys.forEach(function (k) {
        if (vs.indexOf(k) !== -1) { return; }
        var ids = [], seen = Object.create(null);
        shard.e[k].forEach(function (e) { if (!seen[e[0]]) { seen[e[0]] = 1; ids.push(e[0]); } });
        if (ids.length && ids.every(function (i) { return on[i]; })) { return; }
        var w, d;
        if (k.indexOf(' ') !== -1 || k.indexOf('-') !== -1) {
          if (enTokens(k).indexOf(p) === -1) { return; }
          w = 0; d = 0;
        } else if (enStems(k, ir).some(function (s) { return mine.indexOf(s) !== -1; })) {
          w = 0; d = 0;
        } else {
          if (enLetter(k) !== L) { return; }
          d = distance(p, k, lim);
          if (d > lim) { return; }
          w = 1;
        }
        var top = 0;
        ids.forEach(function (i) { top = Math.max(top, shard.a[String(i)][3]); });
        out.push({ k: k, w: w, d: d, top: top, from: shard });
      });
      // past the first letter: the two tails files, then the second letter's keys starting with it
      var seen = Object.create(null);
      out.forEach(function (x) { seen[x.k] = 1; });
      vs.forEach(function (v) { seen[v] = 1; });
      var second = got[3], c2 = b.charAt(1);
      var pools = [got[1], got[2], { e: second.e, a: second.a, d: second.d || {}, only: function (k) {
        return k.indexOf(' ') === -1 && k.indexOf('-') === -1 && bare(k).charAt(0) === c2;
      } }];
      pools.forEach(function (pool) {
        Object.keys(pool.e || {}).sort().forEach(function (k) {
          if (seen[k] || (pool.only && !pool.only(k))) { return; }
          seen[k] = 1;
          var ids = [], had = Object.create(null);
          pool.e[k].forEach(function (e) { if (!had[e[0]]) { had[e[0]] = 1; ids.push(e[0]); } });
          if (ids.length && ids.every(function (i) { return on[i]; })) { return; }
          var d = distance(p, k, lim);
          if (d > lim) { return; }
          var top = 0;
          ids.forEach(function (i) { top = Math.max(top, pool.a[String(i)][3]); });
          out.push({ k: k, w: 1, d: d, top: top, from: pool });
        });
      });
      out.sort(function (x, y) {
        return (x.w - y.w) || (x.d - y.d) || (y.top - x.top) || (x.k.length - y.k.length) || cmpStr(x.k, y.k);
      });
      return out.slice(0, n).map(function (x) { return englishItem(x.from, x.k); });
    });
  }

  /** The English search's numbers for the miss line (site decisions 148 item 8): the articles
   *  indexed and their share of the dictionary, a whole percent, from the build (`c`, `p` in
   *  every English file). -> a promise of {n, p} (nulls where no file answers). */
  function englishNumbers(shard) {
    if (shard && shard.c != null) { return Promise.resolve({ n: shard.c, p: shard.p }); }
    return loadEnglish('a').then(function (s) { return { n: s.c == null ? null : s.c, p: s.p }; });
  }

  /** The address of an English search (site decisions 148 item 3): `/bm-en/#en=<word>`. */
  function englishUrl(q) { return config.base + 'bm-en/#en=' + encodeURIComponent(q); }

  var ordparLookup = {
    englishLookup: englishLookup, englishSuggest: englishSuggest, englishSimilar: englishSimilar,
    englishItem: englishItem, enArticle: enArticle, enNorm: enNorm, enLetter: enLetter, enStems: enStems,
    loadEnglish: loadEnglish, englishNumbers: englishNumbers, englishUrl: englishUrl,
    config: config, configure: configure, setLoader: setLoader,
    fold: fold, bare: bare, accentMatch: accentMatch,
    letterKey: letterKey, shardKey: shardKey, suggestKey: suggestKey,
    tailKey: tailKey, remainderKey: remainderKey, snipKey: snipKey, rewrites: rewrites, RULES: RULES, useList: useList, formHits: formHits,
    caseDistance: caseDistance, bagDistance: bagDistance, charCounts: charCounts,
    guard: guard, suggestQuery: suggestQuery, distance: distance, letterLimit: letterLimit, sharedWords: sharedWords,
    loadShard: loadShard, loadHeadwords: loadHeadwords, loadTails: loadTails,
    loadTranslated: loadTranslated, loadRandom: loadRandom, loadSnippets: loadSnippets,
    loadedSnippets: loadedSnippets,                                 // site decisions 185
    nbDef: nbDef, nbRows: nbRows, rowView: rowView,                 // site decisions 152
    isGloss: isGloss, writeGloss: writeGloss, appendGlossText: appendGlossText,
    GLOSS_CLASS: GLOSS_CLASS, SEP_CLASS: SEP_CLASS,
    lookup: lookup, suggest: suggest, similar: similar, formHg: formHg, headParts: headParts, headText: headText, homographOrder: homographOrder, resultOrder: resultOrder, rankSuggestions: rankSuggestions, mergeArticles: mergeArticles, suggestSections: suggestSections, headLine: headLine, typedLine: typedLine,
    randomHeadword: randomHeadword, randomEnglish: randomEnglish, enPool: enPool,
    shownOrder: shownOrder, firstShown: firstShown,
    articleUrl: articleUrl, searchUrl: searchUrl,
    pagePath: pagePath, pageFor: pageFor, address: address, searchAddress: searchAddress,
    pathWord: pathWord, loadLabels: loadLabels,
    MAX_QUERY: MAX_QUERY
  };

  /* ================================================================= view == */

  /** Where a search that found nothing can go next (site decisions 171, Robin 2026-11-06: as
   *  ordbokene's own page for a missing word, ordbokene.no/nob/about/missing-word): the line
   *  `results.noneWhy`, its {naob} and {norskOrdbok} each a link to that dictionary's search for
   *  the reader's word (NAOB `/søk/<word>`, Norsk Ordbok `/nno/no/<word>`, Robin's look), in a
   *  new tab; `nofollow`, since NAOB keeps crawlers off its search pages. Nothing is sent to
   *  either site unless the reader presses a link. -> the <p>. */
  var MISS_LINKS = {
    naob: ['results.naob', 'https://naob.no/s%C3%B8k/'],
    norskOrdbok: ['results.norskOrdbok', 'https://norsk-ordbok.no/nno/no/']
  };
  function missWhy(q) {
    var p = el('p', 'ordpar-note');
    var word = encodeURIComponent(String(q || '').trim());
    t('results.noneWhy').split(/(\{naob\}|\{norskOrdbok\})/).forEach(function (part) {
      var m = /^\{(naob|norskOrdbok)\}$/.exec(part);
      if (!m) { if (part) { p.appendChild(global.document.createTextNode(part)); } return; }
      var a = el('a', 'ordpar-miss-link', t(MISS_LINKS[m[1]][0]));
      a.href = MISS_LINKS[m[1]][1] + word;
      a.target = '_blank';
      a.rel = 'noopener nofollow';
      p.appendChild(a);
    });
    return p;
  }

  function t(key, vars) {
    var shell = global.ordparShell;
    var s = shell ? shell.t(key) : key;
    if (vars) {
      for (var k in vars) { s = s.split('{' + k + '}').join(String(vars[k])); }
    }
    return s;
  }

  function el(tag, cls, text) {
    var node = global.document.createElement(tag);
    if (cls) { node.className = cls; }
    if (text != null) { node.textContent = text; }
    return node;
  }

  /** A screen readers' label (`ordpar-visually-hidden`), made with `data-nosnippet` (site
   *  decisions 154, Robin 2026-10-31: Google's snippet read "være III homograph 3"): Google reads
   *  the attribute only on an element that carries it when it is first put into the page, never
   *  one a script adds to it later, so it is set here, at the making. */
  function srOnly(text) {
    var node = el('span', 'ordpar-visually-hidden', text);
    node.setAttribute('data-nosnippet', '');
    return node;
  }

  /** A newline between each two element children of `node` that meet with nothing between them
   *  (site decisions 154): the separate pieces of a row, a heading, a list or the results —
   *  separate on the page, one run of words to a text extraction without it ("verbto scent").
   *  Used only where the children are laid out as flex or grid items or blocks, where a newline
   *  between them draws nothing. Run after the children are in; running it again adds none. */
  function spaced(node) {
    var kids = node && node.childNodes, doc = global.document;
    if (!kids || !node.insertBefore || !doc || !doc.createTextNode) { return node; }   // a stand-in
    for (var i = kids.length - 1; i > 0; i--) {
      if (kids[i].nodeType === 1 && kids[i - 1].nodeType === 1) {
        node.insertBefore(global.document.createTextNode('\n'), kids[i]);
      }
    }
    return node;
  }

  // A set phrase (EXPR) has no label: `pos.EXPR` is deliberately absent from the strings, as
  // ordbokene's results show no word class for one (site decisions 22 as amended, 2026-10-19).
  function posLabel(pos) {
    if (!pos) { return ''; }
    // site decisions 152: in Norwegian under Norwegian only or the labels setting (shell.js)
    var S = global.ordparShell;
    if (S && S.posWords) { return S.posWords(pos); }
    var label = t('pos.' + pos);
    return label === 'pos.' + pos ? '' : label;
  }
  /** The word class as a row's span, its `lang` its words' (site decisions 152); null for none. */
  function posSpan(pos) {
    var S = global.ordparShell;
    if (S && S.posSpan) { return S.posSpan(pos); }
    var label = posLabel(pos);
    return label ? el('span', 'ordpar-pos', label) : null;
  }

  var ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];
  /** The homograph number as the article page prints it (Roman, `article.py` `_ROMAN`). */
  function roman(n) { return ROMAN[n] || String(n); }

  /** The homograph mark: the Roman numeral, hidden from assistive technology, with a visually
   *  hidden reading beside it — as the article page's head (site decisions 33 (1)). */
  function homograph(node, hg) {
    if (!hg) { return; }
    var mark = el('span', 'ordbok-homograph ordpar-hg', roman(hg));   // the article's look (decisions 93 (1))
    mark.setAttribute('aria-hidden', 'true');
    node.appendChild(mark);
    node.appendChild(srOnly(' ' + t('results.homograph', { n: hg })));
  }

  /**
   * An article's headword line drawn into `node` (site decisions 93): each spelling, a space
   * and its own numeral (`homograph`), ", " between spellings, " …" where the index cut the
   * list — `headParts` over the article's text, `a.hgs` or every spelling's `a.hg`. The
   * article's id stands in for a missing text.
   */
  function headwordInto(node, a) {
    if (!a.word) { node.appendChild(global.document.createTextNode('#' + a.id)); return; }
    var h = headParts(a.word, a.hg, a.hgs);
    h.parts.forEach(function (p, i) {
      if (i) { node.appendChild(global.document.createTextNode(', ')); }
      node.appendChild(global.document.createTextNode(p.w));
      if (p.hg) { node.appendChild(global.document.createTextNode(' ')); homograph(node, p.hg); }
    });
    if (h.cut) { node.appendChild(global.document.createTextNode(' …')); }
  }

  /**
   * A favourite is drawn as stored, then checked against the index once its shard answers:
   * where the index lists the same spellings in another order (our lemma order, site decisions
   * 93 (2): *tørre, tore* stored as "tore / tørre" before 2026-10-23) or, for one stored before
   * decisions 93 with one number for all its spellings, different numbers per spelling, the
   * line is drawn again from the index (`redrawFrom`). The entry itself is left as stored (a
   * heart pressed again stores the new shape).
   */
  function renumber(node, a) {
    var first = String(a.word).split(SEP)[0].replace(/ …$/, '');
    Promise.resolve(loadShard(shardKey(fold(first)))).then(function (shard) {
      var w = shard && shard.words && shard.words[String(a.id)];
      var now = redrawFrom(a, w);
      if (!now) { return; }
      node.textContent = '';
      headwordInto(node, now);
    }).catch(function () { /* drawn as stored */ });
  }

  /** What `renumber` draws for the stored entry `a` from the index's `words` entry `w`, or
   *  null to keep it as stored: the index's order and numbers where its text holds the same
   *  spellings as the stored one and either the order or a number differs (pure; the tests). */
  function redrawFrom(a, w) {
    if (!w || typeof w[0] !== 'string') { return null; }
    var mine = String(a.word).split(SEP), theirs = w[0].split(SEP);
    if (mine.length !== theirs.length ||
        mine.slice().sort().join(SEP) !== theirs.slice().sort().join(SEP)) { return null; }
    var hg = Array.isArray(w[1]) ? 0 : (w[1] || 0), hgs = Array.isArray(w[1]) ? w[1] : null;
    if (w[0] === a.word && headText(w[0], hg, hgs) === headText(a.word, a.hg, a.hgs)) {
      return null;
    }
    return { id: a.id, word: w[0], hg: hg, hgs: hgs };
  }

  /** A plain link row — the inflected-form lines ("husene is an inflected form of: hus"),
   *  as they were before decisions 59, and the fallback when an article cannot be fetched.
   *  The link holds the whole headword line, each spelling's numeral with it (decisions 93). */
  function articleItem(a) {
    var li = el('li', 'ordpar-hit');
    var link = el('a', 'ordpar-hit-link');
    headwordInto(link, a);
    link.href = articleUrl(a.id);
    link.lang = 'nb';
    li.appendChild(link);
    var pos = posSpan(a.pos);
    if (pos) { li.appendChild(pos); }
    // site decisions 117 (Robin's shape: *tå* *noun* (plural indefinite)): which form of this
    // word the search was, after the word class, in brackets — on every inflected-form row
    if (a.label) {
      // site decisions 152: in Norwegian under Norwegian only or the labels setting
      var S = global.ordparShell, nbl = a.labelNb && S && S.nbWords && S.nbWords();
      var fl = li.appendChild(el('span', 'ordpar-form-label', '(' + (nbl ? a.labelNb : a.label) + ')'));
      if (nbl) { fl.lang = 'nb'; }
    }
    // site decisions 137 (Robin, 2026-10-26): only an untranslated article is tagged, "Norwegian only"
    if (!a.translated) { li.appendChild(el('span', 'ordpar-tag', t('tag.norwegianOnly'))); }
    return spaced(li);                          // a flex row (site decisions 154)
  }

  function section(cls, heading) {
    var sec = el('section', cls);
    var h = el('h2', 'ordpar-section-title');
    h.textContent = heading;
    sec.appendChild(h);
    return sec;
  }

  /** The inflected-form rows: each a link row with, under it, the article's one-line
   *  snippet — held empty until its `snip/` file fills it (`fillSnippets`; brief 59b item 9,
   *  Robin 2026-10-19), in both views. Opening one records its headword in the history (site
   *  decisions 88 as amended: `recordOnOpen`). */
  function articleList(articles) {
    var ul = el('ul', 'ordpar-hits-list');
    articles.forEach(function (a) {
      var li = articleItem(a);
      recordOnOpen(li.firstChild, a);
      if (lemmaOf(a)) {
        var snip = el('span', 'ordpar-hit-snippet is-pending', '\u00a0');
        snip.setAttribute('data-snip', String(a.id));
        snip.lang = a.translated && !nbRows() ? 'en' : 'nb';      // site decisions 152
        li.appendChild(snip);
        spaced(li);
      }
      ul.appendChild(li);
    });
    return spaced(ul);
  }

  /** The headword an article's snippet is filed under: the first of its shown forms
   *  (`words[id][0]`, "fôr / for" -> "fôr"), which is one of its headwords, so its `snip/`
   *  file exists (build_index.py `snippet_files`). '' when the index shows none. */
  function lemmaOf(a) {
    var w = (a.word || '').split(SEP)[0].replace(/ …$/, '');
    return w;
  }

  function announce(root, text) {
    var live = root.querySelector('[data-ordpar-live]');
    if (live) { live.textContent = text; }
  }

  /* ------------------------------------------- full articles (decisions 59) */

  /**
   * The article as its own page shows it, taken from the page itself (site decisions 59: the
   * static page `/bm-en/<id>/` is the one copy; no second file per article). Pure string work
   * over the build's own output (`sitegen/page.py` `render`): the fragment is everything from
   * `<div class="ordbok` to the foot of the article's card (`<footer class="ordpar-card-foot">`,
   * decisions 63; a page built before it ends at the credit footer, `ordpar-attr`), and an
   * untranslated page's status caption comes with it (the long note under it does not — it
   * would repeat on every untranslated hit). Since decisions 106 the card's foot may carry the
   * change notice (`<p class="ordpar-change">`, built into the page by `sitegen/corrections.py`):
   * it comes as `notice`, which `mountArticle` puts after the result's controls, so the notice
   * shows wherever the article's foot does ('' for none). The mini script cuts at the foot and
   * never gets it.
   * Since site decisions 128 (2026-10-25) it also returns the page's own `<title>` as `title`
   * ("abstrakt (adjective) — Norwegian–English dictionary"), which a one-article search sets as
   * the search page's title (`render`), so the two never differ ('' when the page has none).
   * -> {caption, fragment, notice, meta, title} or null when the page does not have that shape.
   */
  function extractArticle(page) {
    var start = page.indexOf('<div class="ordbok');
    var end = page.indexOf('<footer class="ordpar-card-foot">', start);
    if (end < 0) { end = page.indexOf('<footer class="ordpar-attr">', start); }
    if (start < 0 || end < 0) { return null; }
    var cap = /<p class="ordpar-caption">[\s\S]*?<\/p>/.exec(page.slice(0, start));
    var fe = page.indexOf('</footer>', end);
    var foot = page.slice(end, fe < 0 ? page.length : fe);
    var notice = /<p class="ordpar-change">[\s\S]*?<\/p>/.exec(foot);
    var ttl = /<title>([\s\S]*?)<\/title>/.exec(page.slice(0, start));
    return { caption: cap ? cap[0] : '', fragment: page.slice(start, end).replace(/\s+$/, ''),
      notice: notice ? notice[0] : '', meta: pageMeta(page),
      title: ttl ? unescapeAttr(ttl[1]) : '' };
  }

  /** What a history or favourites row needs from the page and the index does not carry (site
   *  decisions 60): the `<html>` tag's `data-snip` (the snippet line) and `data-drop` (the
   *  dropdown's own text for a translated set phrase without a gloss) — `sitegen/page.py`
   *  `personal_attrs`. -> {snip, drop} (drop null when the page has none). Where the snippet
   *  equals the meta description the page leaves `data-snip` out (2026-10-20, the size
   *  report's item 7), so a page without it has the description's text. */
  function pageMeta(page) {
    var tag = /<html\b[^>]*>/.exec(page);
    var attr = function (name) {
      var m = tag && new RegExp('\\s' + name + '="([^"]*)"').exec(tag[0]);
      return m ? unescapeAttr(m[1]) : null;
    };
    var snip = attr('data-snip');
    if (snip == null) {
      var d = /<meta name="description" content="([^"]*)">/.exec(page);
      snip = d ? unescapeAttr(d[1]) : '';
    }
    return { snip: snip, drop: attr('data-drop') };
  }

  function unescapeAttr(v) {
    return v.replace(/&(quot|#x27|#39|lt|gt|amp);/g, function (m, e) {
      return { quot: '"', '#x27': "'", '#39': "'", lt: '<', gt: '>', amp: '&' }[e];
    });
  }

  /** The hit `a` with its page's snippet line and dropdown text (`pageMeta`). */
  function withMeta(a, got) {
    if (!got || !got.meta) { return a; }
    var b = {};
    for (var k in a) { b[k] = a[k]; }
    b.snip = got.meta.snip;
    b.drop = got.meta.drop;
    return b;
  }

  /** A favourites entry's fields for the hit `a` (`ordparPersonal.heartButton`): with the
   *  per-spelling numbers where they differ (`hgs`, decisions 93), else `hg` every spelling's. */
  function personalFields(a) {
    var f = { id: a.id, word: a.word || String(a.id), hg: a.hg || 0, pos: a.pos || '',
      translated: !!a.translated, snip: a.snip || '' };
    if (a.hgs) { f.hgs = a.hgs.slice(); f.hg = formHg([a.word, a.hgs], null); }
    if (a.drop != null) { f.drop = a.drop; }
    return f;
  }

  /**
   * Make one article's fragment safe to sit beside others on the results page (site decisions
   * 59). Every id inside it is prefixed `r<id>-` — `def3` → `r24627-def3`, an embedded
   * expression's `x102921-def4` → `r24627-x102921-def4`, `ordpar-paradigm` →
   * `r24627-ordpar-paradigm`, a control's `xra24627-1` → `r24627-xra24627-1` — and so is every
   * attribute that names one (`for`, `data-for`, `data-paradigm`); a link to the article's
   * own sense (`/bm-en/<id>/#def3`) becomes the in-page `#r<id>-def3`; every other link is
   * left as it is. The `<h1>` headword becomes an `<h3>` (`level`) holding a link to the
   * article's page — the canonical URL — with the id `r<id>-hw`, and the section headings go
   * one level below it (`aria-level`).
   */
  function scopeArticle(html, id, level) {
    level = level || 3;
    var p = 'r' + id + '-';
    var self = '/bm-en/' + id + '/#';
    html = html.replace(/<[a-zA-Z][^>]*>/g, function (tag) {
      return tag
        .replace(/(\s)(id|for|data-for|data-paradigm)="([^"]*)"/g, function (m, s, a, v) {
          return s + a + '="' + p + v + '"';
        })
        .replace(/(\s)href="([^"]*)"/g, function (m, s, v) {
          return v.indexOf(self) === 0 ? s + 'href="#' + p + v.slice(self.length) + '"' : m;
        });
    });
    // the headword is no link, as on ordbokene's results: a link beside each spelling's sound
    // icon made a press a little short of the icon leave the page (site decisions 160, Robin
    // 2026-11-02). Copy link and Share under the article carry its page's address; the "Article
    // page" link that went there is gone (site decisions 168, re-ruled 2026-11-06 (everywhere))
    html = html.replace(/<h1 class="ordpar-hw"([^>]*)>([\s\S]*?)<\/h1>/, function (m, attrs, inner) {
      return '<h3 class="ordpar-hw"' + attrs + ' id="' + p + 'hw"'
        + (level !== 3 ? ' aria-level="' + level + '"' : '') + '>' + inner + '</h3>';
    });
    return html.replace(/<h3 lang="en">/g, '<h3 lang="en" aria-level="' + (level + 1) + '">');
  }

  var articleCache = Object.create(null);   // id -> Promise<{caption, fragment} | null>

  /** Fetch an article's page once per page view and take its fragment (`extractArticle`). */
  function fetchArticle(id) {
    if (articleCache[id]) { return articleCache[id]; }
    var p = (global.fetch ? global.fetch(articleUrl(id), { credentials: 'omit' })
      : Promise.reject(new Error('no fetch')))
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (text) { return text ? extractArticle(text) : null; })
      .catch(function () { return null; })
      .then(function (got) {
        if (!got) { delete articleCache[id]; }     // a failure is retried next time
        return got;
      });
    articleCache[id] = p;
    return p;
  }

  /** The article's own page as an absolute URL — what Copy link copies and Share shares. */
  function absoluteUrl(id) {
    var loc = global.location;
    return (loc && loc.origin && loc.origin !== 'null' ? loc.origin : '') + articleUrl(id);
  }

  /**
   * The controls under an article shown whole — a word page, the results, an opened list
   * row, History and Favourites (site decisions 59 (2)): Copy link, Share, "Suggest a
   * correction" (166) and the heart (60), in that order — no Cite (site decisions 21e), and no
   * "Article page" link, which ordbokene's results carry (site decisions 168, re-ruled
   * 2026-11-06 (everywhere): Robin, "it doesn't really serve any purpose"). Copy link copies
   * the article's own page URL (`<origin>/bm-en/<id>/`), not the search's; Share shares it
   * with the headword (and its homograph numeral) as the title. As on the article page, a
   * button is shown only where the browser supports it. No ids: nothing refers to them, so a
   * page of many results gains none.
   */
  function resultControls(a) {
    var nav = global.navigator || {};
    var url = absoluteUrl(a.id);
    var title = a.word ? headText(a.word, a.hg, a.hgs) : String(a.id);
    var p = el('p', 'ordpar-result-controls');
    if (nav.clipboard && nav.clipboard.writeText) {
      var copy = el('button', 'ordpar-result-btn ordpar-result-copy', t('results.copyLink'));
      copy.type = 'button';
      var done = el('span', 'ordpar-result-copied');
      done.setAttribute('role', 'status');
      var timer = null;
      copy.addEventListener('click', function () {
        nav.clipboard.writeText(url).then(function () {
          done.textContent = t('results.copied');
          if (timer) { clearTimeout(timer); }
          timer = setTimeout(function () { done.textContent = ''; }, 2500);
        }, function () { /* refused: nothing to say */ });
      });
      p.appendChild(copy);
      p.appendChild(done);
    }
    if (nav.share) {
      var share = el('button', 'ordpar-result-btn ordpar-result-share', t('results.share'));
      share.type = 'button';
      share.addEventListener('click', function () {
        nav.share({ title: title, url: url }).catch(function () { /* cancelled */ });
      });
      p.appendChild(share);
    }
    // site decisions 166: "Report a mistake" after them, as at the article page's foot
    // (`report.js`; nothing while its receiver address is empty)
    if (global.ordparReport && global.ordparReport.mount) { global.ordparReport.mount(p, a.id); }
    // the heart beside them (site decisions 60 item 4), as on the article page
    if (global.ordparPersonal) {
      p.appendChild(global.ordparPersonal.heartButton(personalFields(a), 'ordpar-result-heart'));
    }
    return spaced(p);                           // a flex row (site decisions 154)
  }

  /** Put a fetched article into `host`, its controls after it (`resultControls`), and wake
   *  what the article page would: the inflection island (`inflection.js`), the definitions
   *  settings and `infl` (`article.js`). The Inflection toggle follows `infl` as on an
   *  article page, in both views — an opened list row too (site decisions 83, reversing
   *  59 (3)'s always-open row, which was ordbokene's). */
  function mountArticle(host, a, got, level) {
    a = withMeta(a, got);
    // a newline between the pieces (site decisions 154): blocks, where it draws nothing
    host.innerHTML = (got.caption ? got.caption + '\n' : '') + scopeArticle(got.fragment, a.id, level) + '\n';
    host.appendChild(resultControls(a));
    // decisions 106: the change notice, under the controls as at the article page's foot
    if (got.notice) { host.insertAdjacentHTML('beforeend', '\n' + got.notice); }
    if (global.ordparInflection && global.ordparInflection.mountAll) {
      try { global.ordparInflection.mountAll(host); } catch (e) { /* the module's own bug */ }
    }
    if (typeof global.ordparDefs === 'function') {
      try { global.ordparDefs(); } catch (e) { /* the page script's own bug */ }
    }
    // the wide table gives way to the narrow one when it does not fit the card, measured
    // (Robin 2026-10-19, brief 60 item 7(a) as ruled; everywhere since decisions 102, where
    // `mountAll` fits each mount itself and this call only measures again, after ordparDefs)
    if (global.ordparInflection && global.ordparInflection.fit) {
      try { global.ordparInflection.fit(host); } catch (e) { /* the module's own bug */ }
    }
  }

  /** Default view: every hit's article in full, one after another, in the hit order. */
  function fullArticles(articles, seen) {
    var wrap = el('div', 'ordpar-results-full');
    var shown = [];
    articles.forEach(function (a) {
      if (seen[a.id]) { return; }
      seen[a.id] = 1;
      var art = el('article', 'ordpar-result');
      art.setAttribute('data-id', String(a.id));
      art.setAttribute('aria-labelledby', 'r' + a.id + '-hw');
      art.setAttribute('aria-busy', 'true');
      art.appendChild(el('p', 'ordpar-empty', a.word || ('#' + a.id)));
      wrap.appendChild(art);
      shown.push(fetchArticle(a.id).then(function (got) {
        art.removeAttribute('aria-busy');
        // site decisions 128: the page's own title, for a one-article search (`render`)
        if (got) { art.ordparTitle = got.title || ''; mountArticle(art, a, got, 3); return withMeta(a, got); }
        art.removeAttribute('aria-labelledby');
        art.textContent = '';
        var ul = el('ul', 'ordpar-hits-list');
        ul.appendChild(articleItem(a));
        art.appendChild(ul);
        return null;
      }));
    });
    // the articles shown in full, in their order, once every fetch has answered (null where a
    // page could not be fetched) — a one-article search's history entry takes its display
    // fields from them (brief 60b item 2)
    wrap.shown = Promise.all(shown);
    return spaced(wrap);
  }

  /**
   * The list view (the setting `listview` = on): one row per hit — headword, homograph, word
   * class, the translated tag and a one-line snippet — each a disclosure button (`aria-expanded`,
   * `aria-controls`) inside a heading; the article opens in full in a region below the row,
   * labelled by it, its inflection table shown or behind its button as the setting `infl` says
   * (decisions 83; ordbokene's always shows it), and closes again; any number may be open
   * (ordbokene's own list view). The snippets arrive after the rows (`fillSnippets`): each row
   * holds its line until then, so nothing moves when they come.
   * `opts` (the favourites page, site decisions 89): `level` the rows' heading level (3, under
   * the results' heading; the article opened in a row one below it), `mark` false to leave out
   * the saved article's small heart (every favourite is one), `renumber` true to correct the
   * numerals of a favourite stored before decisions 93 from the index (`renumber`).
   * Loading ahead (decisions 92, `ahead.js`): a row's article is fetched when the pointer rests
   * on it or a finger touches it (`minifetch = point`), or with the page (`page`, below).
   */
  function listRows(articles, seen, opts) {
    var level = (opts && opts.level) || 3;
    var mark = !(opts && opts.mark === false);
    var wrap = el('div', 'ordpar-rows');
    var drawn = [];
    articles.forEach(function (a) {
      if (seen[a.id]) { return; }
      seen[a.id] = 1;
      drawn.push(a.id);
      var row = el('div', 'ordpar-row');
      row.setAttribute('data-id', String(a.id));
      var head = el('h' + level, 'ordpar-row-head');
      var btn = el('button', 'ordpar-row-button');
      btn.type = 'button';
      btn.id = 'r' + a.id + '-row';
      btn.setAttribute('aria-expanded', 'false');
      btn.setAttribute('aria-controls', 'r' + a.id + '-panel');
      var line = el('span', 'ordpar-row-line');
      // the headword line, each spelling with its own numeral, ", " between (decisions 93)
      var word = el('span', 'ordpar-row-word');
      headwordInto(word, a);
      word.lang = 'nb';
      line.appendChild(word);
      if (a.word && a.word.indexOf(SEP) !== -1 && opts && opts.renumber) {
        renumber(word, a);      // a favourite stored before decisions 93, or before our order
      }
      // a saved article's row carries a small filled heart beside the headword (decisions 60)
      if (mark && global.ordparPersonal) { line.appendChild(global.ordparPersonal.favMark(a.id)); }
      var pos = posSpan(a.pos);
      if (pos) { line.appendChild(pos); }
      // site decisions 137: only an untranslated article is tagged, "Norwegian only"
      if (!a.translated) { line.appendChild(el('span', 'ordpar-tag', t('tag.norwegianOnly'))); }
      btn.appendChild(el('span', 'ordpar-row-chevron'));
      btn.lastChild.setAttribute('aria-hidden', 'true');
      btn.appendChild(line);
      var snip = el('span', 'ordpar-row-snippet is-pending', '\u00a0');
      snip.setAttribute('data-snip', String(a.id));
      snip.lang = a.translated && !nbRows() ? 'en' : 'nb';      // site decisions 152
      btn.appendChild(snip);
      spaced(line);                             // the word, its numeral's label, its class: a flex row
      spaced(btn);                              // the line over the snippet: a grid (site decisions 154)
      head.appendChild(btn);
      row.appendChild(head);
      var panel = el('div', 'ordpar-row-panel');
      panel.id = 'r' + a.id + '-panel';
      panel.setAttribute('role', 'region');
      panel.setAttribute('aria-labelledby', btn.id);
      panel.hidden = true;
      row.appendChild(panel);
      spaced(row);
      var loaded = false;
      btn.addEventListener('click', function () {
        var open = btn.getAttribute('aria-expanded') !== 'true';
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        row.classList.toggle('is-open', open);
        panel.hidden = !open;
        // an opened row records nothing: its article is one the search found as a headword, so
        // the search is the entry (brief 60b item 1; decisions 88 as amended)
        if (!open || loaded) { return; }
        loaded = true;
        panel.setAttribute('aria-busy', 'true');
        panel.textContent = '';
        panel.appendChild(el('p', 'ordpar-empty', t('results.loading')));
        fetchArticle(a.id).then(function (got) {
          panel.removeAttribute('aria-busy');
          if (got) {
            mountArticle(panel, a, got, level + 1);
            return;
          }
          loaded = false;                       // try again on the next open
          panel.textContent = '';
          var ul = el('ul', 'ordpar-hits-list');
          ul.appendChild(articleItem(a));
          panel.appendChild(ul);
        });
      });
      wrap.appendChild(row);
    });
    // decisions 92: `minifetch = page` fetches the list's articles with the page, one at a time in
    // idle time (ahead.js `queue`, shared with the minis' targets); `point` on a resting pointer
    // or a touch is ahead.js's own listener on the row's button
    var ahead = global.ordparAhead;
    if (ahead && ahead.mode && ahead.mode() === 'page') {
      drawn.forEach(function (id) { ahead.queue('a' + id, function () { return fetchArticle(id); }); });
    }
    return spaced(wrap);
  }

  /** The right-hand text of a one-article history row, by the dropdown's rule (`shell.js`
   *  `glossText`): the set-phrase box where the article has one (`"_d"`, or a page's
   *  `data-drop`), else (an override of '' too: a set phrase with no box, site decisions 82,
   *  A13 point 3, Robin 2026-10-21) the first unit of its snippet line. */
  function dropRule(drop, snip) {
    return drop ? drop : (snip ? String(snip).split(' · ')[0] : '');
  }

  /**
   * Record a search that found something in the history (brief 60b items 1–2): the query as
   * typed, trimmed (`g.query`), the number of distinct articles whose OWN headword it matched
   * (the headword hits, an accent-folded group's included) and, when that is one, its display
   * fields. The inflected-form rows are not counted, and a search that found only those records
   * nothing (site decisions 88 as amended, Robin 2026-10-22: "a search with only inflected-form
   * results records nothing until one is opened" — opening one records its headword,
   * `recordOpened`). Several articles: written at once. One untranslated article: at once too.
   * One translated article: written at once without its right-hand text, so a page left before
   * the article arrives still has its entry (site decisions 129, 2026-10-25: a reader on a slow
   * connection who opened another page right after the results heading lost the entry; as
   * `recordOpened`'s stand-in), then written again, the same entry (the same query, the same
   * time: `ordparPersonal.addSearch` replaces it), once the text is on hand — in the full view
   * from the page the result already fetched (`shown`, the page's `data-snip` / `data-drop`),
   * else (the list view, a page that could not be fetched) from the `snip/` file of its
   * headword, the file the rows' own snippets come from. An entry left without its text is
   * drawn from the index all the same (shell.js `needsFill`). The time is the search's (`t`,
   * else now), so the entry keeps its place by time. A miss is never recorded. -> a promise,
   * resolved once the entry is complete (or nothing is written).
   */
  function recordSearch(q, res, shownP, t) {
    var P = global.ordparPersonal;
    if (!P || !P.recordSearch || !res || !res.count) { return Promise.resolve(); }
    if (t == null) { t = Date.now(); }
    var ids = Object.create(null), n = 0, one = null;
    res.heads.forEach(function (grp) {
      grp.articles.forEach(function (a) { if (!ids[a.id]) { ids[a.id] = 1; n++; one = a; } });
    });
    if (!n) { return Promise.resolve(); }
    if (n > 1) { P.recordSearch({ q: q, n: n }, t); return Promise.resolve(); }
    var write = function (text) {
      P.recordSearch({ q: q, n: 1, word: one.word || String(one.id), hg: one.hg || 0,
        pos: one.pos || '', translated: !!one.translated, text: text || '' }, t);
    };
    write('');                                 // at once (decisions 129); the text fills it below
    if (!one.translated) { return Promise.resolve(); }
    var fromSnip = function () {
      var w = lemmaOf(one);
      if (!w) { return; }                      // the entry stays as written
      return loadSnippets(snipKey(fold(w))).then(function (snips) {
        var id = String(one.id);
        var drop = snips && snips._d && Object.prototype.hasOwnProperty.call(snips._d, id)
          ? snips._d[id] : null;
        var text = dropRule(drop, snips && snips[id]);
        if (text) { write(text); }
      }, function () { /* the entry stays as written */ });
    };
    if (!shownP) { return Promise.resolve(fromSnip()); }
    return shownP.then(function (lists) {
      var hit = null;
      [].concat.apply([], lists || []).forEach(function (b) { if (b && b.id === one.id) { hit = b; } });
      if (hit) { var text = dropRule(hit.drop, hit.snip); if (text) { write(text); } return; }
      return fromSnip();
    }, fromSnip);
  }

  /**
   * An article a search reached through an inflected form, opened (site decisions 88 as
   * amended, Robin 2026-10-22: "if you actually click on an inflected form to open it, then it
   * gets added to the history"): its headword (`lemmaOf`) goes into the history as its own
   * entry, as a search for it would — the headword is looked up and recorded by
   * `recordSearch`, so *danne* opened from *dann* stores what a search for *danne* stores. A
   * stand-in is written at once, the one article as an entry for its headword, so a page left
   * before the lookup answers still has its entry; the lookup's entry replaces it (the same
   * query, the same time). Where the headword's own search does not find it as a headword, the
   * stand-in stays. -> a promise, resolved once the entry is written.
   */
  function recordOpened(a) {
    var P = global.ordparPersonal;
    var w = lemmaOf(a);
    if (!P || !P.recordSearch || !w) { return Promise.resolve(); }
    var t = Date.now();
    P.recordSearch({ q: w, n: 1, word: a.word || String(a.id), hg: a.hg || 0, pos: a.pos || '',
      translated: !!a.translated, text: '' }, t);
    return lookup(w).then(function (res) {
      var found = res && res.heads.some(function (grp) {
        return grp.articles.some(function (b) { return b.id === a.id; });
      });
      if (!found) { res = { count: 1, heads: [{ form: w, articles: [a] }], forms: [] }; }
      return recordSearch(w, res, null, t);
    }).catch(function () { /* the stand-in stays */ });
  }

  /** Wire an inflected-form row's link to record its article when opened (`recordOpened`): a
   *  plain click waits for the entry (at most `OPEN_WAIT` ms) before it follows the link; a
   *  click that opens another tab or window, and a middle click, record without waiting. */
  var OPEN_WAIT = 1200;
  function recordOnOpen(link, a) {
    link.addEventListener('click', function (ev) {
      var done = recordOpened(a);
      if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey
          || ev.altKey || !global.location) { return; }
      ev.preventDefault();
      var gone = false;
      var go = function () { if (!gone) { gone = true; global.location.href = link.href; } };
      done.then(go, go);
      setTimeout(go, OPEN_WAIT);
    });
    link.addEventListener('auxclick', function (ev) { if (ev.button === 1) { recordOpened(a); } });
  }

  /** Put the snippets of one file (`{"<id>": text}`, or null) into the rows' held lines — the
   *  list rows' and the inflected-form rows'. With `last`, once every file has come, a line
   *  still held loses its place (its article has no snippet). */
  function fillSnippets(wrap, snips, last) {
    var spans = wrap.querySelectorAll('[data-snip].is-pending');
    var nb = nbRows();
    if (nb) { snips = rowView(snips); }                      // site decisions 152
    for (var i = 0; i < spans.length; i++) {
      var id = spans[i].getAttribute('data-snip');
      var text = snips && snips[id];
      if (text) {
        writeGloss(spans[i], text, isGloss(snips, id));     // site decisions 116
        if (nb) { spans[i].lang = 'nb'; }
        spans[i].classList.remove('is-pending');
      } else if (last) {
        spans[i].parentNode.removeChild(spans[i]);
      }
    }
  }

  /** The results' heading on a hit (site decisions 59, Robin 2026-10-19), after ordbokene's
   *  "Bokmål dictionary" with its count badge: the dictionary's name ("Norwegian–English
   *  dictionary", site decisions 164: one dictionary here) and the number of
   *  articles — the number shown, the whole "5 articles" read by a screen reader. */
  function resultsHeading(count) {
    var h = el('h2', 'ordpar-section-title ordpar-dict-title');
    h.appendChild(el('span', 'ordpar-dict-name', t('results.dictionary')));
    var badge = el('span', 'ordpar-count');
    var n = el('span', null, String(count));
    n.setAttribute('aria-hidden', 'true');
    badge.appendChild(n);
    badge.appendChild(srOnly(' ' + t(count === 1 ? 'results.countOne' : 'results.count', { n: count })));
    h.appendChild(badge);
    return spaced(h);                           // a flex row (site decisions 154)
  }

  /** The setting `listview`: 'forms' (the list when the query finds several articles as
   *  headword hits, or any article through an inflected form — site decisions 158, Robin
   *  2026-11-01, the default since), 'multi' (the list only for several headword hits — brief
   *  59b item 16; the default from decisions 71 to 158), 'on' (the list always) or 'off' (full
   *  articles; the default until 71), here as in shell.js `SETTINGS`. */
  function listMode() {
    var shell = global.ordparShell;
    var v = shell && shell.getSetting ? shell.getSetting('listview') : 'forms';
    return v === 'on' || v === 'off' || v === 'multi' ? v : 'forms';
  }

  /** Does `mode` show `n` headword hits as the list, the query also finding `f` articles through
   *  an inflected form (the "is an inflected form of" rows, `formHits`)? 'multi' counts the
   *  headword hits alone (homographs, set phrases matched directly); 'forms' (site decisions 158)
   *  counts the form hits too, so the article opens straight away only for exactly one headword
   *  hit and no form hit. With no headword hit there is nothing to list: as 'multi'. The form
   *  rows themselves are rows in every mode. */
  function useList(mode, n, f) {
    if (mode === 'on') { return true; }
    if (mode === 'multi') { return n > 1; }
    if (mode === 'forms') { return n > 1 || (n === 1 && (f || 0) > 0); }
    return false;
  }

  /** The articles a lookup result finds through an inflected form (its `forms` groups' rows):
   *  what 'forms' counts (site decisions 158). */
  function formHits(res) {
    var f = 0;
    ((res && res.forms) || []).forEach(function (grp) { f += (grp.articles || []).length; });
    return f;
  }

  var last = null;          // {root, query, mode}: what a change of the list-view setting re-renders
  var watching = false;
  function watchSetting() {
    var shell = global.ordparShell;
    if (watching || !shell || !shell.onChange) { return; }
    watching = true;
    // the setting changed (or was reset, or its stored data deleted): re-render as the other
    // view, once — `setSetting` notifies both 'render' and the key
    shell.onChange(function (key) {
      // an English search is always the list (site decisions 148 item 5): not re-rendered
      // site decisions 152: nor a change of Norwegian only, its settings or the labels, which
      // the rows, drawn by script in the language in force, must follow
      var layer = ['nbonly', 'nbequiv', 'nbrows', 'nbhover', 'labels'].indexOf(key) !== -1;
      if (last && !last.en && (layer || listMode() !== last.mode)) { render(last.root, last.query); }
    });
  }

  /** The line a search shows while it runs: the search page's "Searching…" (`results.searching`)
   *  in a `p.ordpar-empty`, one element for `render` and `searching` (site decisions 138). */
  function searchingLine() { return el('p', 'ordpar-empty', t('results.searching')); }

  /**
   * A search made in place has started, before its index file is loaded (site decisions 138):
   * the results area of `root` cleared at once and the "Searching…" line shown in it — the line
   * `render` draws when it starts, so the reader sees one line throughout — instead of the
   * previous answer staying until the new one comes. `last` moves to the new search, so no later
   * step of the previous answer (its similar words, its title) draws into it. A query `guard`
   * refuses is left to `render`, which says why at once. No-op without a results area.
   */
  function searching(root, query) {
    if (!root || !guard(query).ok) { return; }
    var results = root.querySelector('[data-ordpar-results]') || root;
    last = { root: root, query: query, mode: listMode() };
    watchSetting();
    results.textContent = '';
    results.appendChild(searchingLine());
    idle(root, false);
  }

  /** Site decisions 142: `ordpar-idle` on `root` while it shows no search (an empty query), which
   *  is when `shell.css` shows the home page's line to "More ways to use Ordpar". */
  function idle(root, on) {
    if (root && root.classList) { root.classList.toggle('ordpar-idle', !!on); }
  }

  /**
   * Render one query into `root` (the search page's results container, also used by the
   * 404 shell). Returns a promise resolving to the lookup result.
   */
  function render(root, query, opts) {
    if (opts && opts.en) { return renderEnglish(root, query, opts); }     // site decisions 148
    var record = !!(opts && opts.record);     // a search the reader made: it goes into the history
    var results = root.querySelector('[data-ordpar-results]') || root;
    var mode = listMode();
    var list = false;          // set once the lookup has said how many headword hits there are
    last = { root: root, query: query, mode: mode };
    watchSetting();
    var mine = last;
    results.textContent = '';
    var g = guard(query);
    // site decisions 142 (Robin, 2026-10-27: "It can be dropped everywhere"): an empty query
    // draws nothing — the line "Type a Norwegian word to search the dictionary." is gone — and
    // marks the page idle, for the home page's line
    idle(root, !g.ok && g.reason === 'empty');
    if (!g.ok) {
      if (g.reason !== 'empty') {
        results.appendChild(el('p', 'ordpar-empty', t('search.' + g.reason)));
        announce(root, t('search.' + g.reason));
      }
      return Promise.resolve(null);
    }
    results.appendChild(searchingLine());
    return lookup(g.query).then(function (res) {
      if (mine !== last) { return res; }          // a newer search has started
      results.textContent = '';
      var seen = Object.create(null);
      var shown = null;          // the full view's fetched articles (`fullArticles` `shown`)
      if (res.count) {
        // one heading over every hit, as ordbokene's; the articles of every headword group
        // (en, én) in one run, each group in its homograph order (`homographOrder`)
        var hits = el('section', 'ordpar-hits');
        hits.appendChild(resultsHeading(res.count));
        // translated first across the groups too (item 12; each group is in `resultOrder`):
        // `shownOrder`, the order Random word's pool is built from (decisions 115)
        var order = shownOrder(res), all = order.all, done = order.done, todo = order.todo;
        var ids = Object.create(null), n = 0;
        all.forEach(function (a) { if (!ids[a.id]) { ids[a.id] = 1; n++; } });
        list = useList(mode, n, formHits(res));     // site decisions 158: the form rows count under 'forms'
        if (list) {
          if (all.length) { hits.appendChild(listRows(done.concat(todo), seen)); }
        } else {
          var full = [];
          if (done.length) { full.push(hits.appendChild(fullArticles(done, seen))); }
          if (todo.length) {
            // both groups: the untranslated under decisions 58's sub-heading, its words and look
            if (done.length) { hits.appendChild(el('p', 'ordpar-untr-head', t('results.untranslated'))); }
            full.push(hits.appendChild(fullArticles(todo, seen)));
          }
          shown = Promise.all(full.map(function (w) { return w.shown; }));
          // site decisions 128 (one style for every page title): a search that lifts ONE
          // article in full takes that article page's own <title> ("abstrakt (adjective) —
          // Norwegian–English dictionary") once it has come; a search showing several keeps the
          // page's own title for the query (search.html, 404.html)
          if (n === 1) {
            shown.then(function () {
              var art = hits.querySelector('.ordpar-result');
              if (mine === last && art && art.ordparTitle) { global.document.title = art.ordparTitle; }
            });
          }
        }
        results.appendChild(spaced(hits));
      }
      res.forms.forEach(function (grp) {
        var sec = section('ordpar-inflected', t('results.inflected', { q: grp.form }));
        sec.appendChild(articleList(grp.articles));
        results.appendChild(spaced(sec));
      });
      spaced(results);                          // the sections, blocks (site decisions 154)
      // The snippets, after the results have painted: the list rows' file is the query's key,
      // asked for on a headword hit only, and each inflected-form row's is its headword's key
      // (in both views) — every headword's key has its file (build_index.py `snippet_files`),
      // so no search asks for a file that is not there, and a miss asks for none. Each held
      // line is filled when its file comes; a file already loaded fills before the next paint.
      var keys = [];
      var addKey = function (k) { if (keys.indexOf(k) === -1) { keys.push(k); } };
      if (list && res.heads.some(function (grp) { return grp.articles.length; })) {
        addKey(snipKey(fold(g.query)));
      }
      res.forms.forEach(function (grp) {
        grp.articles.forEach(function (a) { var w = lemmaOf(a); if (w) { addKey(snipKey(fold(w))); } });
      });
      Promise.all(keys.map(function (k) {
        return loadSnippets(k).then(function (snips) {
          if (mine === last) { fillSnippets(results, snips, false); }
        });
      })).then(function () {
        if (mine === last) { fillSnippets(results, null, true); }
      });
      // site decisions 131 (117's one style for the tab's title): a search whose address is its
      // own word or form page takes that page's built title (`pageTitle`) — several entries or a
      // form: "så — Norwegian–English dictionary"; one article: the article's own title, which the
      // full view sets above (128) and a list row fetches here; a `#q=` search keeps "q — Ordpar"
      pageTitle(res).then(function (pt) {
        if (mine !== last || !pt) { return; }
        if (pt.title) { global.document.title = pt.title; return; }
        if (list) {
          fetchArticle(pt.one).then(function (got) {
            if (mine === last && got && got.title) { global.document.title = got.title; }
          });
        }
      });
      // the search into the history (brief 60b) — only one the reader made: not a re-render on
      // a setting, not back / forward, not the 404 page's search of a mistyped address
      if (record) { recordSearch(g.query, res, shown); }
      // decisions 62: one event per search the reader made — a hit, or a miss held until a
      // similar word is chosen below or the page is left (events.js)
      var E = global.ordparEvents;
      if (record && E) {
        try { if (res.count) { E.hit(g.query); } else { E.missStart(g.query); } } catch (e) { /* not ours to break */ }
      }
      if (!res.count) {
        var miss = el('section', 'ordpar-miss');
        miss.appendChild(el('h2', 'ordpar-section-title', t('results.none', { q: g.query })));
        miss.appendChild(missWhy(g.query));
        results.appendChild(spaced(miss));
        spaced(results);
        announce(root, t('results.liveNone', { q: g.query }));
      } else {
        announce(root, t(res.count === 1 ? 'results.liveHitsOne' : 'results.liveHits',
          { n: res.count, q: g.query }));
      }
      // the similar words, past the first letter and through the spelling rules (decisions
      // 55), on a hit as on a miss (decisions 56); fetched after the results are painted.
      // Site decisions 144 (Robin, 2026-10-27): after a search that finds NOTHING (no headword,
      // no inflected form) each is a row, as the suggestions draw theirs (`similarRow`); a hit
      // keeps the bare list of words ("for pages that actually has a search hit, it becomes a
      // bit information overload")
      // site decisions 149 (Robin, 2026-10-29: "a "similar headword" suggestion is only shown if
      // it would actually lead you to articles that are not currently on the search page"): on a
      // page that shows articles, a similar headword whose own search would show only those is
      // left out (`dropRepeats`) and the next takes its place — so the pass is asked for more
      var showing = res.count || res.forms.some(function (grp) { return grp.articles.length; });
      // the full view's articles come with ALL their spellings (the index's text keeps three:
      // *selvlaget*'s fourth, *sjøllaget*, is only on its page), so the pass waits for them
      var whole = showing && shown ? shown.then(null, function () { return null; }) : null;
      return Promise.all([similar(g.query, showing ? SIMILAR_POOL : null), whole]).then(function (both) {
        var words = both[0];
        if (mine !== last) { return res; }
        if (showing) { words = dropRepeats(words, res, pageSpellings(results)).slice(0, config.similarCount); }
        if (words.length) {
          var sec = section('ordpar-similar', t('results.similar'));
          var rows = !res.count && canDrawRows();
          var ul = el('ul', 'ordpar-similar-list' + (rows ? ' ordpar-similar-rows' : ''));
          words.forEach(function (s, i) {
            var li = el('li');
            var a = rows ? similarRow(s) : el('a', null, s.word);
            // site decisions 117: the word's own page where it has one, the search after `#`
            // (the mark of a search the reader made, as the `#q=` link was), else its search
            a.href = s.page ? s.page + '#q=' + encodeURIComponent(s.word) : searchUrl(s.word);
            if (!rows) { a.lang = 'nb'; }       // a row marks its word, its English is not
            // decisions 62 (1): the similar word chosen after a miss, and its position
            if (record && !res.count && E) {
              var choose = function () { try { E.missChoose(g.query, s.word, i + 1); } catch (e) { /* lost */ } };
              a.addEventListener('click', choose);
              a.addEventListener('auxclick', function (ev) { if (ev.button === 1) { choose(); } });
            }
            ul.appendChild(li).appendChild(a);
          });
          sec.appendChild(spaced(ul));
          results.appendChild(spaced(sec));
          spaced(results);
        }
        return res;
      });
    });
  }

  /** How many similar headwords a page that shows articles asks the pass for, so that five
   *  remain once `dropRepeats` has left out the ones that would only repeat the page. */
  var SIMILAR_POOL = 30;

  /**
   * Site decisions 149: the similar headwords `words` (`similar`'s answer, its `count` the
   * articles each heads — the headwords file's `a`) without those whose own search would show no
   * article not already on the page `res` shows — neither among the results (full or list view)
   * nor among the "is an inflected form of" rows. No request: a candidate's articles are known
   * exactly where its shard is loaded (the query's own: `heads`), and otherwise by its spellings
   * among the articles on the page — their headword text in the index (up to three spellings)
   * and, for an article shown in full, every spelling its head shows (`spell`, `pageSpellings`):
   * dropped when the articles on the page carrying it as a spelling are as many as it heads.
   * *selvlaget* no longer lists *selvlagd*, *selvlaga* or *sjøllaget* (spellings of the one
   * article shown); *rett* still lists *rette*, which heads two articles, one of them (*rette* I,
   * the noun) not on the page.
   */
  function dropRepeats(words, res, spell) {
    var on = Object.create(null), arts = [];
    (res.heads || []).concat(res.forms || []).forEach(function (grp) {
      grp.articles.forEach(function (a) { if (!on[a.id]) { on[a.id] = 1; arts.push(a); } });
    });
    if (!arts.length) { return words; }
    return words.filter(function (s) {
      var sh = shards[shardKey(fold(s.word))];
      var ids = sh && sh.heads && sh.heads[s.word];
      if (ids && ids.length) { return !ids.every(function (id) { return on[id]; }); }
      if (!s.count) { return true; }          // an inflected form only, or a file before 144
      var carriers = 0;
      arts.forEach(function (a) {
        var forms = String(a.word || '').replace(/ …$/, '').split(SEP);
        if (spell && spell[a.id]) { forms = forms.concat(spell[a.id]); }
        if (forms.indexOf(s.word) !== -1) { carriers++; }
      });
      return carriers < s.count;
    });
  }

  /** The spellings each article shown IN FULL under `root` carries in its head (`.ordbok-lemma`,
   *  the article page's own headword line): {id: [spelling, …]} (site decisions 149). */
  function pageSpellings(root) {
    var out = Object.create(null);
    Array.prototype.forEach.call(root.querySelectorAll('.ordpar-result[data-id]'), function (art) {
      var list = [];
      Array.prototype.forEach.call(art.querySelectorAll('.ordpar-hw .ordbok-lemma'), function (l) {
        var w = l.textContent.replace(/^[\s,]+|[\s,]+$/g, '');
        if (w) { list.push(w); }
      });
      out[art.getAttribute('data-id')] = list;
    });
    return out;
  }

  /* ---------------------------------------- the English search's view (site decisions 148) */

  /**
   * Render one ENGLISH search into `root` (`render` with `opts.en`): Robin, 2026-10-29, as picked
   * in the lab. A hit is always the list view (59's rows, whatever the reader's `listview`),
   * except one matching article, which opens in full and gives the tab its own title (128); the
   * heading as for a Norwegian search ("Norwegian–English dictionary" and the count; site decisions 164). Each row is the
   * site's own (`listRows`: the Norwegian headword line with all its spellings and its word
   * class), its snippet line the article's WHOLE summary gloss, wrapping, in normal text, the
   * searched equivalent bold (700) every place it matches (`englishGloss`; a deliberate exception
   * to site decisions 116, Robin's). A miss says the word is not among our English equivalents
   * yet, with the build's numbers (`englishNumbers`). Then the similar English words
   * (`englishSimilar`): the suggestion rows after a miss (`ordparShell.englishRow`), the bare
   * list after a hit, each a link to its English search (`#en=`). A hit the reader made goes into
   * History, marked English (`recordEnglish`); a miss never. The search's event (decisions 62, as
   * the Norwegian search sends it; 148's follow-up, Robin 2026-10-29: "Yes, count them"): a
   * search the reader made sends a hit, or a miss held until a similar English word is chosen (its
   * place from 1) or the page is left, each marked English (`events.js`, `lang` 'en'); a re-render
   * sends none. -> the lookup's answer.
   */
  function renderEnglish(root, query, opts) {
    var record = !!(opts && opts.record);
    var results = root.querySelector('[data-ordpar-results]') || root;
    last = { root: root, query: query, mode: listMode(), en: true };
    watchSetting();
    var mine = last;
    results.textContent = '';
    var g = guard(query);
    idle(root, !g.ok && g.reason === 'empty');
    if (!g.ok) {
      if (g.reason !== 'empty') {
        results.appendChild(el('p', 'ordpar-empty', t('search.' + g.reason)));
        announce(root, t('search.' + g.reason));
      }
      return Promise.resolve(null);
    }
    results.appendChild(searchingLine());
    return englishLookup(g.query).then(function (res) {
      if (mine !== last) { return res; }
      results.textContent = '';
      var on = Object.create(null);
      var arts = res.matches.map(function (m) { on[m.id] = 1; return m.article; });
      var done = Promise.resolve();
      // decisions 62, for the English search too (148's follow-up): one event per search the
      // reader made, marked English
      var E = global.ordparEvents;
      if (record && E) {
        try { if (res.count) { E.hit(g.query, true); } else { E.missStart(g.query, true); } } catch (e) { /* not ours to break */ }
      }
      if (res.count) {
        var hits = el('section', 'ordpar-hits ordpar-hits-en');
        hits.appendChild(resultsHeading(res.count));
        if (res.count === 1) {
          // Robin, 2026-10-29: "if there is only one matching Norwegian headword to the English
          // equivalent, it can probably go straight to the article" — with the page's own title
          var full = hits.appendChild(fullArticles(arts, Object.create(null)));
          full.shown.then(function () {
            var art = hits.querySelector('.ordpar-result');
            if (mine === last && art && art.ordparTitle) { global.document.title = art.ordparTitle; }
          });
        } else {
          var wrap = hits.appendChild(listRows(arts, Object.create(null)));
          wrap.classList.add('ordpar-rows-en');
          res.matches.forEach(function (m) {
            var snip = wrap.querySelector('[data-snip="' + m.id + '"]');
            if (!snip) { return; }
            snip.textContent = '';
            snip.lang = 'en';
            snip.classList.remove('is-pending');
            englishGloss(snip, m.article.units, m.spans);
          });
        }
        results.appendChild(spaced(hits));
        announce(root, t(res.count === 1 ? 'results.liveHitsOne' : 'results.liveHits',
          { n: res.count, q: g.query }));
        if (record) { recordEnglish(g.query, res); }
      } else {
        var miss = results.appendChild(el('section', 'ordpar-miss ordpar-miss-en'));
        miss.appendChild(el('h2', 'ordpar-section-title', t('results.noneEn', { q: g.query })));
        var why = miss.appendChild(el('p', 'ordpar-note'));
        spaced(miss);
        announce(root, t('results.liveNone', { q: g.query }));
        done = englishNumbers(res.shard).then(function (num) {
          if (mine !== last) { return; }
          why.textContent = t('results.noneEnWhy', {
            n: num.n == null ? '' : Number(num.n).toLocaleString('en-GB'),
            p: num.p == null ? '' : String(num.p) });
        });
      }
      return done.then(function () { return englishSimilar(g.query, null, on); }).then(function (items) {
        if (mine !== last) { return res; }
        if (items.length) {
          var S = global.ordparShell;
          var rows = !res.count && !!(S && S.englishRow);
          var sec = section('ordpar-similar ordpar-similar-en', t('results.similarEn'));
          var ul = el('ul', 'ordpar-similar-list' + (rows ? ' ordpar-similar-rows' : ''));
          var drawn = [];
          items.forEach(function (it, i) {
            var li = el('li');
            var a = rows ? S.englishRow('a', it, 'ordpar-similar-row') : el('a', null, it.word);
            if (!rows) { a.lang = 'en'; }
            a.href = englishUrl(it.word);
            // decisions 62 (1), English: the similar word chosen after a miss, and its place
            if (record && !res.count && E) {
              var choose = function () { try { E.missChoose(g.query, it.word, i + 1, true); } catch (e) { /* lost */ } };
              a.addEventListener('click', choose);
              a.addEventListener('auxclick', function (ev) { if (ev.button === 1) { choose(); } });
            }
            ul.appendChild(li).appendChild(a);
            if (rows) { drawn.push(a); }
          });
          sec.appendChild(spaced(ul));
          results.appendChild(spaced(sec));
          spaced(results);
          drawn.forEach(function (a) { if (a.ordparFit) { a.ordparFit(); } });
        }
        return res;
      });
    });
  }

  /** A summary gloss into `node` as an English result row shows it (site decisions 148 item 5):
   *  the units as the site draws them, the faded " · " between them (`SEP_CLASS`), in normal
   *  text, and every matched equivalent (`spans`: [unit, start, end]) in `ordpar-en-hit` (700). */
  function englishGloss(node, units, spans) {
    var doc = node.ownerDocument;
    (units || []).forEach(function (u, i) {
      if (i) { node.appendChild(el('span', SEP_CLASS, ' \u00b7 ')); }
      var hs = (spans || []).filter(function (s) { return s[0] === i + 1; })
        .sort(function (a, b) { return a[1] - b[1]; });
      var at = 0;
      hs.forEach(function (s) {
        if (s[1] < at) { return; }
        if (s[1] > at) { node.appendChild(doc.createTextNode(u.slice(at, s[1]))); }
        node.appendChild(el('span', 'ordpar-en-hit', u.slice(s[1], s[2])));
        at = s[2];
      });
      if (at < u.length) { node.appendChild(doc.createTextNode(u.slice(at))); }
    });
  }

  /** An English search that found something into the history (site decisions 148 item 9): the
   *  query as typed and the number of articles, marked `en` — drawn in the English manner by
   *  shell.js (`englishEntryRow`), its link `#en=`. A miss is never recorded. */
  function recordEnglish(q, res) {
    var P = global.ordparPersonal;
    if (!P || !P.recordSearch || !res || !res.count) { return; }
    P.recordSearch({ q: q, n: res.count, en: true }, Date.now());
  }

  /** Whether the shell's row code is on the page (`ordparShell.searchRowMain` …), which the
   *  similar rows after a miss are drawn by (site decisions 144); without it, the bare list. */
  function canDrawRows() {
    var S = global.ordparShell;
    return !!(S && S.searchRowMain && S.searchRowSide && S.fillSearchRow && S.similarArticles);
  }

  /**
   * One similar headword after a miss as a row (site decisions 144, Robin 2026-10-27: "set up
   * the 'Similar headwords' section similar to how the deck shows the 'Also on ordpar.no:' list
   * … I would style it similar to the search suggestions list"): an `<a>` drawn by the shell's
   * own row code, the code of the suggestions and History — the word (`lang="nb"`), in the
   * accent where an article it heads is translated, its word class where it heads one article
   * (`searchRowMain`); then its side (`searchRowSide`, `fillSearchRow`): one article's summary
   * gloss semibold or its English definition, an untranslated one's Norwegian definition; for
   * several, the translated homographs' numbered glosses and "+ N more", or with none
   * translated each homograph's Norwegian definition (`sideGlosses`). Shell.css sets the side
   * after the word, after a muted em dash, and a thin line between the rows. What the row needs
   * comes with the similar pass's own files (`similar`'s `count`, `translated`, `pos`) and the
   * word's `snip/` file (`similarArticles`: its `"_h"`), so no shard is loaded for it. A word
   * that is only an inflected form (`count` 0, reached through a spelling rule) says whose form
   * it is (`formRow`); a similar-words file from before 144 (`count` null) draws the row from
   * the word's search, as History does. The caller sets `href`.
   */
  function similarRow(s) {
    var S = global.ordparShell;
    var a = el('a', 'ordpar-option ordpar-similar-row');
    if (s.count === 0) { return formRow(a, s.word); }
    if (s.count == null) {
      var held = a.appendChild(S.searchRowMain({ q: s.word, n: 0 }));
      lookup(s.word).then(function (res) {
        var ids = Object.create(null), n = 0, one = null;
        ((res && res.heads) || []).forEach(function (grp) {
          grp.articles.forEach(function (x) { if (!ids[x.id]) { ids[x.id] = 1; n++; one = x; } });
        });
        if (!n) { return; }
        var e = n > 1 ? { q: s.word, n: n } : { q: s.word, n: 1, word: one.word || String(one.id),
          hg: one.hg || 0, pos: one.pos || '', translated: !!one.translated, text: '' };
        a.replaceChild(S.searchRowMain(e), held);
        if (n === 1 && e.translated) { a.classList.add('is-translated'); }
        spaced(a);                                // site decisions 154: a flex row
        S.fillSearchRow(a.appendChild(S.searchRowSide(e)), e);
        spaced(a);
      });
      return a;
    }
    var e = s.count > 1 ? { q: s.word, n: s.count }
      : { q: s.word, n: 1, word: s.word, hg: 0, pos: s.pos || '', translated: !!s.translated, text: '' };
    if (s.translated) { a.classList.add('is-translated'); }
    a.appendChild(S.searchRowMain(e));
    S.fillSearchRow(a.appendChild(S.searchRowSide(e)), e, null, S.similarArticles);
    spaced(a);                                  // site decisions 154: a flex row
    return a;
  }

  /**
   * The row of a similar word that is only an INFLECTED form (site decisions 144; `similar`
   * offers one only where a spelling rule lands on it in the query's own shard, already loaded):
   * the form, then what its search would answer — "inflected form of" and the headwords it is a
   * form of, in the rows' stored order (site decisions 143), each word once, at most
   * `FORM_ROW_MAX`; the form in the accent where one of those articles is translated.
   */
  var FORM_ROW_MAX = 3;
  function formRow(a, word) {
    var S = global.ordparShell;
    a.classList.add('ordpar-similar-form');
    a.appendChild(S.searchRowMain({ q: word, n: 0 }));
    var side = a.appendChild(el('span', 'ordpar-option-side'));
    spaced(a);                                  // site decisions 154: a flex row
    var text = side.appendChild(el('span', 'ordpar-option-gloss is-pending', '\u00a0'));
    lookup(word).then(function (res) {
      var arts = [];
      ((res && res.forms) || []).forEach(function (grp) { arts = arts.concat(grp.articles); });
      var seen = Object.create(null), heads = [];
      arts.forEach(function (x) {
        var w = lemmaOf(x);
        if (w && !seen[w]) { seen[w] = 1; heads.push(w); }
      });
      if (!heads.length) { side.removeChild(text); return; }
      if (arts.some(function (x) { return x.translated; })) { a.classList.add('is-translated'); }
      text.textContent = '';
      text.appendChild(el('span', 'ordpar-option-formof', t('similar.formOf') + ' '));
      heads.slice(0, FORM_ROW_MAX).forEach(function (w, i) {
        if (i) { text.appendChild(global.document.createTextNode(', ')); }
        var span = text.appendChild(el('span', 'ordpar-option-formhead', w));
        span.lang = 'nb';
      });
      if (heads.length > FORM_ROW_MAX) { text.appendChild(global.document.createTextNode(', \u2026')); }
      text.classList.remove('is-pending');
    }, function () { side.removeChild(text); });
    return a;
  }

  /** Wire the random-word buttons on the page: a random headword's SEARCH (decisions 115, as
   *  ordbokene's "Tilfeldig ord"), `/bm-en/#q=<headword>` — answered in place on a page that
   *  answers searches itself (the search page, the 404 shell: `ordparShell.search`, as the box's
   *  own submit), else opened as that address. An id from an old pool file opens its article.
   *  With "Search English words" on (site decisions 155, Robin 2026-10-31), a random English word
   *  instead (`randomEnglish`), opened exactly as if it had been typed and picked (148: its
   *  English search, the list, or the article itself where the word has one match) — answered in
   *  place as an English search, else `/bm-en/#en=<word>&random` — and not a search either
   *  (115): not in History, not sent. The switch's state is the reader's stored one
   *  (`ordparShell.direction`), so a page that does not show the switch follows it too; the box
   *  stays English. This amends 148 item 11, which sent the box back to Norwegian. */
  function wireRandom(root) {
    var buttons = (root || global.document).querySelectorAll('[data-ordpar-random]');
    Array.prototype.forEach.call(buttons, function (btn) {
      btn.addEventListener('click', function () {
        btn.disabled = true;
        var S = global.ordparShell;
        var en = randomEnglishOn();
        // site decisions 180: the word drawn ahead on a rest or a touch (`drawAhead`), if drawn in
        // this direction (awaited if still pending), else a draw now; taken either way, so the
        // next rest draws anew (ahead.js keys a rest by `ordparDrawGen`)
        var pending = btn.ordparDraw;
        btn.ordparDraw = null;
        btn.ordparDrawGen = (btn.ordparDrawGen || 0) + 1;
        var draw = function () { return en ? randomEnglish() : randomHeadword(); };
        (pending && pending.en === en
          ? pending.word.then(function (w) { return w == null ? draw() : w; }, draw)
          : draw()).then(function (w) {
          btn.disabled = false;
          if (w == null) { return; }
          if (en) {
            if (S && S.search && S.search(w, { random: true, en: true })) {
              if (global.scrollTo) { global.scrollTo(0, 0); }
              return;
            }
            global.location.href = englishUrl(w) + DRAWN_MARK;
            return;
          }
          if (typeof w === 'number') { global.location.href = articleUrl(w); return; }
          // a draw is not a search (decisions 115, Robin 2026-10-24: "A random word is not a
          // search, and it does not go into history"): answered as one, but marked as drawn —
          // in place by the history entry's state, from another page by DRAWN_MARK in the
          // fragment, which the search page takes into the state at once (`takeDrawn`)
          if (S && S.search && S.search(w, { random: true })) {
            if (global.scrollTo) { global.scrollTo(0, 0); }
            return;
          }
          // site decisions 117: the word's page where it has one (every word of the pool has one
          // unless its search cannot be a folder name), marked as a draw
          searchAddress(w, true).then(function (href) { global.location.href = href; });
        });
      });
    });
  }

  /** Whether Random word draws an English word now (site decisions 155): the switch's stored
   *  direction, but Norwegian while Norwegian only hides the English equivalents (152: the switch
   *  hidden), even after a shared `#en=` address opened an English search here. */
  function randomEnglishOn() {
    var S = global.ordparShell;
    return !!(S && S.direction && S.direction() === 'en') && !(S.equivHidden && S.equivHidden());
  }

  /** Random word's draw made ahead (site decisions 180, Robin 2026-11-09: "make the "random word"
   *  button also pre-fetch when the mouse pointer is hovering for 150 ms"): on ahead.js's rest or
   *  touch, the word drawn then, in the direction of that moment, and kept on the button
   *  (`btn.ordparDraw = {en, word: promise}`) for its click (`wireRandom`), which takes it; a
   *  second rest before the click keeps the same draw, a rest after the direction changed draws
   *  again. Still a draw, not a search (decisions 115): nothing recorded or sent here.
   *  -> a promise of {w, en} (`w` null when nothing could be drawn: the next rest tries again). */
  function drawAhead(btn) {
    var en = randomEnglishOn(), d = btn.ordparDraw;
    if (!d || d.en !== en) {
      d = btn.ordparDraw = { en: en, word: (en ? randomEnglish() : randomHeadword()) };
    }
    return d.word.then(function (w) {
      if (w == null && btn.ordparDraw === d) { btn.ordparDraw = null; }
      return { w: w, en: en };
    }, function () {
      if (btn.ordparDraw === d) { btn.ordparDraw = null; }
      return { w: null, en: en };
    });
  }

  /** The mark of a drawn word's search in the address it is opened at from another page
   *  (`/bm-en/#q=<word>&random`, decisions 115): only the fragment, never sent to a server
   *  (104), and taken off by the search page before it answers (`takeDrawn`). */
  var DRAWN_MARK = '&random';

  /** The search in a fragment, raw (not decoded), or null: `#q=hus`, or since site decisions 146
   *  after settings (`#defs=en&q=hus`, the address for a pop-up dictionary — the head script
   *  takes the settings off first, `sitegen/head.py`, so this is for a page without it). */
  function hashQuery(hash) {
    var m = /(?:^#|&)q=([^&]*)/.exec(hash || '');
    return m ? m[1] : null;
  }

  /** An English search in a fragment (site decisions 148 item 3: `/bm-en/#en=house`), raw, or
   *  null. */
  function hashEnglish(hash) {
    var m = /(?:^#|&)en=([^&]*)/.exec(hash || '');
    return m ? m[1] : null;
  }

  function decodeRaw(raw) {
    raw = raw.replace(/\+/g, ' ');
    try { return decodeURIComponent(raw); } catch (e) { return raw; }
  }

  var wiredLinks = false;
  var ordparSearch = {
    render: render,
    searching: searching,
    extractArticle: extractArticle, scopeArticle: scopeArticle, roman: roman, pageMeta: pageMeta,
    fetchArticle: fetchArticle,   // the mini script's fetch too (decisions 80): one cache for both
    withMeta: withMeta, personalFields: personalFields, headwordInto: headwordInto, redrawFrom: redrawFrom,
    listRows: listRows,           // the favourites page's rows (site decisions 89)
    recordSearch: recordSearch, recordOpened: recordOpened, recordOnOpen: recordOnOpen,
    wireRandom: wireRandom,
    drawAhead: drawAhead, randomEnglishOn: randomEnglishOn,     // site decisions 180 (ahead.js)
    /** The search in the page's address: the fragment's `#q=` (decisions 104), else an old
     *  address's `?q=` (a link or bookmark from before; `fragmentAddress` rewrites it). */
    queryFromLocation: function () {
      var loc = global.location;
      if (!loc) { return ''; }
      var raw = hashQuery(loc.hash);
      if (raw == null) {
        var m = /[?&]q=([^&#]*)/.exec(loc.search || '');
        if (!m) { return ''; }
        raw = m[1];
      }
      raw = raw.replace(/\+/g, ' ');
      try { return decodeURIComponent(raw); } catch (e) { return raw; }
    },
    /** The English search in the page's address (`#en=<word>`, site decisions 148), decoded, or
     *  '' — a search page opened from it is switched to English and runs the search. */
    englishFromLocation: function () {
      var loc = global.location;
      var raw = loc ? hashEnglish(loc.hash) : null;
      return raw == null ? '' : decodeRaw(raw);
    },
    /** Whether the search the address stands for (`addressQuery`) is an English one: the
     *  entry's state (`{q, en: true}`, what an English search answered in place pushed), else a
     *  `#en=` fragment. */
    addressEnglish: function () {
      var st = null;
      try { st = global.history && global.history.state; } catch (e) { st = null; }
      if (st && typeof st.q === 'string') { return !!st.en; }
      return !!(global.location && hashEnglish(global.location.hash) != null);
    },
    englishUrl: englishUrl,
    DRAWN_MARK: DRAWN_MARK,
    hashQuery: hashQuery, hashEnglish: hashEnglish,
    /** Whether the search in the address is a Random word draw, not a search the reader made
     *  (decisions 115: not recorded in History, no search event). A draw from another page
     *  arrives with DRAWN_MARK after the query: taken off the address here with
     *  `history.replaceState`, no new entry, the mark moved into the entry's state
     *  (`{q, random: true}`), where a draw answered in place puts it too (the search page's
     *  `run`). The state is kept with the entry by the browser — across a reload, Back and
     *  Forward — so a reload of the drawn address stays a draw; an address typed or followed
     *  afresh has no such state. Called by the search page (and the 404 shell) before their
     *  first search. -> true for a draw. */
    takeDrawn: function () {
      var loc = global.location, h = global.history;
      if (!loc) { return false; }
      var hash = loc.hash || '';
      var at = hash.indexOf(DRAWN_MARK);
      // site decisions 155: an English draw arrives as `#en=<word>&random`, its entry `{q, random:
      // true, en: true}`
      var en = hashQuery(hash) == null && hashEnglish(hash) != null;
      if ((hashQuery(hash) != null || en) && at > 0
          && (at + DRAWN_MARK.length === hash.length || hash.charAt(at + DRAWN_MARK.length) === '&')) {
        var q = en ? ordparSearch.englishFromLocation() : ordparSearch.queryFromLocation();
        var rest = hash.slice(0, at) + hash.slice(at + DRAWN_MARK.length);
        try {
          if (h && h.replaceState) {
            h.replaceState(en ? { q: q, random: true, en: true } : { q: q, random: true }, '', loc.pathname + loc.search + rest);
          }
        } catch (e) { /* the address keeps its mark; the page still treats it as a draw */ }
        return true;
      }
      try { return !!(h && h.state && h.state.random); } catch (e) { return false; }
    },
    /** Clicks on a link to a search on THIS page (`<this path>#q=<word>`: a "Similar headwords"
     *  link while the address is `/bm-en/`) answered by `onSearch(query)` instead: the browser
     *  would only move the fragment and load nothing (decisions 104). A click for a new tab or
     *  window, or one another handler took, is left alone. Wired once per page. */
    wireFragmentLinks: function (onSearch) {
      var doc = global.document, loc = global.location;
      if (!doc || !loc || wiredLinks) { return; }
      wiredLinks = true;
      doc.addEventListener('click', function (e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) { return; }
        var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
        if (!a || a.target || a.hasAttribute('download')) { return; }
        var url;
        try { url = new global.URL(a.href, loc.href); } catch (err) { return; }
        // site decisions 148: an English search's link (`#en=`, a similar English word) too,
        // handed on with `{en: true}`
        var raw = url.search ? null : hashQuery(url.hash), en = false;
        if (raw == null && !url.search) { raw = hashEnglish(url.hash); en = raw != null; }
        if (url.origin !== loc.origin || raw == null) { return; }
        // this page's own path, the search page's, or a word page's (site decisions 117: a
        // similar headword's link is its page with the search after `#`) — all answered here
        if (url.pathname !== loc.pathname && url.pathname !== config.base + 'bm-en/'
            && !pathWord(url.pathname)) { return; }
        e.preventDefault();
        var q = decodeRaw(raw);
        onSearch(q.trim(), en ? { en: true } : undefined);
      });
    },
    /** An old address with the search in its query (`/bm-en/?q=hus`) rewritten in place to the
     *  fragment form (`/bm-en/#q=hus`, decisions 104): `history.replaceState`, so no reload and no
     *  new history entry, the entry's state kept. -> true when it rewrote. Called by the search
     *  page (and the 404 shell) before their first search. */
    fragmentAddress: function () {
      var loc = global.location, h = global.history;
      if (!loc || !h || !h.replaceState || !/[?&]q=/.test(loc.search || '')) { return false; }
      var q = ordparSearch.queryFromLocation();
      var rest = (loc.search || '').slice(1).split('&').filter(function (kv) {
        return kv && kv.split('=')[0] !== 'q';
      }).join('&');
      try {
        h.replaceState(h.state, '', loc.pathname + (rest ? '?' + rest : '')
          + (q ? '#q=' + encodeURIComponent(q) : ''));
        return true;
      } catch (e) { return false; }
    },
    /** The search the page's address stands for (site decisions 117): the entry's state (`{q}`,
     *  what a search answered in place pushed), else the fragment's `#q=`, else a word page's own
     *  word (`pathWord`). What Back and Forward re-answer. */
    addressQuery: function () {
      var st = null;
      try { st = global.history && global.history.state; } catch (e) { st = null; }
      if (st && typeof st.q === 'string') { return st.q; }
      return ordparSearch.queryFromLocation() || ordparSearch.englishFromLocation()
        || pathWord(global.location && global.location.pathname) || '';
    },
    /** Whether this page was reached by Back or Forward from another page (the browser kept no
     *  copy of it): not a search the reader made. */
    cameByHistory: cameByHistory,
    answerInPlace: answerInPlace,
    wordPage: wordPage
  };

  function cameByHistory() {
    try {
      var nav = global.performance.getEntriesByType('navigation')[0];
      return !!nav && nav.type === 'back_forward';
    } catch (e) { return false; }
  }

  /**
   * A page that answers searches in place (site decisions 117: a word page; the 404 shell):
   * the box's searches (and Random word, through `ordparShell.search`), a similar headword's
   * link and Back / Forward are answered here, with no reload, and the address becomes the
   * search's page where it has one (`address`: `/bm-en/så/`), else its `#q=` — the entry's
   * state `{q, search: true}` (a draw `{q, random: true}`), so a reload or a return finds the
   * search as typed. The title is the search page's for a search (`q — Ordpar`) until the answer
   * comes; then, for a search whose address is its own page, that page's built title (`render`,
   * `pageTitle`, site decisions 131). -> `go(q, how)`.
   */
  function answerInPlace(main) {
    var d = global.document, h = global.history;
    var start = { path: global.location.pathname, title: d.title };
    // `en`: an English search (site decisions 148), its address `/bm-en/#en=<q>`, its entry's
    // state `{q, search: true, en: true}`; the switch follows it
    var show = function (q, record, en) {
      d.title = q + ' — ' + t('site.name');
      var box = d.getElementById('ordpar-q');
      if (box && box.value !== q) { box.value = q; }      // back / forward keeps the box in step
      var S = global.ordparShell;
      if (S && S.setDirection) { S.setDirection(en ? 'en' : 'nb', { quiet: true }); }
      return render(main, q, { record: record, en: !!en });
    };
    // site decisions 138: a later search always wins — each search takes the next number, and
    // drops its answer (no address pushed, nothing drawn) when a newer search, or Back /
    // Forward, has started while its index file was loading, as `render` does with `mine !== last`
    var seq = 0, loading = 0;                         // `loading`: the number of a search not yet answered
    var go = function (q, how) {
      // site decisions 155: a draw may be English (Random word with the switch on)
      var drawn = !!(how && how.random), en = !!(how && how.en), mine = ++seq;
      loading = mine;
      // shown at once (decisions 138): the title and the box the new search's, the results the
      // "Searching…" line, until the answer comes
      d.title = q + ' — ' + t('site.name');
      var box = d.getElementById('ordpar-q');
      if (box && box.value !== q) { box.value = q; }
      searching(main, q);
      return (en ? Promise.resolve(englishUrl(q)) : address(q)).then(function (url) {
        if (mine !== seq) { return null; }            // a newer search (or Back / Forward) since
        loading = 0;
        var state = drawn ? (en ? { q: q, random: true, en: true } : { q: q, random: true })
          : en ? { q: q, search: true, en: true } : { q: q, search: true };
        try { h.pushState(state, '', url); } catch (e) { /* the address stays */ }
        return show(q, !drawn, en);
      });
    };
    var S = global.ordparShell;
    if (S && S.setSearchHandler) { S.setSearchHandler(go); }
    ordparSearch.wireFragmentLinks(function (q, how) { if (global.scrollTo) { global.scrollTo(0, 0); } go(q, how); });
    global.addEventListener('popstate', function () {
      var cut = !!loading;
      seq++; loading = 0;                             // a search still loading is dropped (138)
      var q = ordparSearch.addressQuery();
      if (!q) {
        if (cut) { render(main, q, { record: false }); }   // not its "Searching…" left standing
        return;
      }
      var st = null;
      try { st = h.state; } catch (e) { st = null; }
      if (global.location.pathname === start.path && !(st && (st.search || st.en))) {
        render(main, q, { record: false });
        d.title = start.title;
        return;
      }
      show(q, false, ordparSearch.addressEnglish());
    });
    return go;
  }

  /**
   * A word page or a form page opened (site decisions 117): the search for its word, rendered as
   * a search renders it — under the reader's settings (the list view's setting: by default one
   * article whole, several, or one that is also an inflected form, as the list — site decisions
   * 158), the inflected-form rows with their labels, the similar
   * headwords — in place of the rows the build wrote. Then the page answers searches in place
   * (`answerInPlace`).
   * * Reached from a search box, Random word or a similar headword on another page, the address
   *   carries the search after `#` (`searchAddress`: `/bm-en/så/#q=Så`, a draw `&random`): it is
   *   a search the reader made, recorded in History and counted (`render`'s `record`) exactly as
   *   the search page records `/bm-en/#q=Så` today — not a draw, not one reached by Back or
   *   Forward — and the address is cleaned to the page's own (`history.replaceState`, the search
   *   kept in the entry's state, so a reload records again as the search page's does).
   * * Opened directly (a link, a bookmark, a search engine): what the 404 shell did for the same
   *   address until 117 — the search for the word, not recorded.
   * The page's own title stays (the build's: the article's for one article). `word` (the 404
   * shell's) the folded word, else the page's `data-ordpar-word`. -> the render's promise.
   */
  function wordPage(main, word) {
    var d = global.document;
    main = main || d.getElementById('ordpar-main');
    if (!main) { return Promise.resolve(null); }
    word = word || main.getAttribute('data-ordpar-word') || pathWord(global.location.pathname) || '';
    var S = global.ordparShell;
    return Promise.resolve(S && S.ready).then(function () {
      var h = global.history, loc = global.location, q = word, record = false;
      var hash = loc.hash || '';
      var drawn = ordparSearch.takeDrawn();
      var asked = ordparSearch.queryFromLocation();
      if (hashQuery(hash) != null) {
        if (asked && fold(asked) === fold(word)) {
          q = asked;
          record = !drawn && !cameByHistory();
        }
        try {
          h.replaceState(drawn ? { q: q, random: true } : (record ? { q: q, search: true } : null),
            '', loc.pathname + loc.search);
        } catch (e) { /* the address keeps its search */ }
      } else {
        var st = null;
        try { st = h.state; } catch (e) { st = null; }
        if (st && typeof st.q === 'string' && fold(st.q) === fold(word)) {
          q = st.q;
          record = !!st.search && !st.random && !cameByHistory();
        }
      }
      // the box shows the word, as the search page's shows its search
      var box = d.getElementById('ordpar-q');
      if (box && !box.value) { box.value = q; }
      answerInPlace(main);
      return render(main, q, { record: record });
    });
  }

  // a word page starts itself (site decisions 117): `/site/ordpar.js` is deferred, so the rest of
  // the bundle (shell.js) has run by DOMContentLoaded
  (function () {
    var d = global.document;
    if (!d || !d.addEventListener) { return; }
    var go = function () {
      var m = d.querySelector('main[data-ordpar-word]');
      if (m) { wordPage(m); }
    };
    if (d.readyState === 'complete') { setTimeout(go, 0); } else { d.addEventListener('DOMContentLoaded', go); }
  }());

  global.ordparLookup = ordparLookup;
  global.ordparSearch = ordparSearch;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ordparLookup: ordparLookup, ordparSearch: ordparSearch };
  }
}(typeof globalThis !== 'undefined' ? globalThis : this));
