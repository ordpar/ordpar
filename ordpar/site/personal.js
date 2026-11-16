/*! Ordpar — history and favourites, kept on the device (site decisions 60, Robin 2026-10-19;
 * history amended to a list of searches the same day — brief 60b).
 *
 * Two lists in localStorage, beside the settings, each under one key:
 *
 *   history      the SEARCHES that found something, by the query as typed (trimmed), newest
 *                first; a repeat — the same query trimmed and lower-cased — moved to the top
 *                with the spelling typed last; at most 100
 *   favourites   the ARTICLES saved with the heart, newest first
 *
 * A history entry is the search and what its row needs beyond what the dictionary gives:
 *
 *   {q, n, t}                                          several articles found
 *   {q, n: 1, t, word, hg, pos, translated, text}      one article found
 *
 * — the query, the number of distinct articles whose own headword the search matched (site
 * decisions 88 as amended, Robin 2026-10-22: the inflected-form rows are not counted, a search
 * that found only those is not recorded, and an article opened from one is recorded as a search
 * for its headword — lookup.js `recordSearch`, `recordOpened`; entries stored before count
 * them, and draw by what their search finds now — shell.js `fillSearchRow`), the time it was
 * stored (ms since 1970), and for one article its headword as the
 * index shows it, homograph number (0 for none), the index's word-class code (NOUN, VERB, EXPR …;
 * '' for none), translated or not, and its right-hand text by the dropdown's rule (the gloss unit;
 * a translated set phrase with no summary gloss: its set-phrase box, or '' for nothing; '' for an
 * untranslated article). Only one translated article with its text stored is drawn from the
 * entry alone; every other row's right-hand side — one untranslated article's Norwegian
 * definition, several articles' numbered glosses, a stored text that is empty — is drawn from
 * the dictionary when the row is shown (site decisions 88, Robin 2026-10-22: `shell.js`
 * `fillSearchRow`), so the entries' shape is unchanged and an old entry draws as a new one.
 *
 * A favourites entry is one article: {id, word, hg, hgs?, pos, translated, snip, drop?, t} —
 * the article id, the headword, homograph, word class, translated or not, the list view's
 * snippet line (cut as in `snip/`), the dropdown's own text where it is not the snippet's first
 * unit (brief 60 item 7(b) as amended), and the time it was saved. `word` is the index's text,
 * the spellings joined by " / " (a data separator: every row draws them with ", ", lookup.js
 * `headParts`); `hgs`, since site decisions 93 (2026-10-22), one homograph number per spelling
 * where they differ (*lysing* 1, *lysning* 2), `hg` then the first non-zero; without `hgs`,
 * `hg` is every spelling's. An entry stored before 93 has no `hgs` and its first lemma's `hg`;
 * the favourites page corrects its numerals from the index when it draws it (lookup.js
 * `renumber`). The format's version is unchanged: `hgs` is optional.
 *
 * The build before 60b stored history entries in the favourites' shape, one per article opened.
 * They are read as searches for their headword (`fromArticles`): entries sharing a word become
 * one, at the newest time, counting the distinct ids merged; the new shape is written at the next
 * write.
 *
 * Nothing leaves the browser: no cookie, no request. A missing or corrupt value reads as an empty
 * list, a malformed entry inside one is dropped; storage that is full or blocked (private mode)
 * fails silently and the page carries on.
 *
 * Export / import (brief 60 item 6, 60b item 5; decisions 60, 61): one small JSON file holding
 * the settings, the history and the favourites, with a format name and a version (2; a version-1
 * file's history is converted as above). Import MERGES — favourites added to those present (no
 * duplicates), history entries combined by query and ordered by time under the cap, the settings
 * taken from the file — and refuses a file that does not parse, has another format or a newer
 * version, or carries one malformed entry, before anything is written: never half-read.
 *
 * Loaded by the article page (deferred, before /site/article.js, which draws the heart —
 * `sitegen/page.py` PAGE_JS) and by the shell's pages (before shell.js and lookup.js's view,
 * which draw the dropdown's recent searches, record a search and draw the results' hearts and
 * the favourites and history pages). The pure parts run under bun for the tests
 * (`ordpar/tests/test_ordpar_history60.py`).
 */
(function (global) {
  'use strict';

  var HISTORY_KEY = 'history';
  var FAV_KEY = 'favourites';
  var CAP = 100;                 // the history's cap (decisions 60: "about 100")
  var FAV_CAP = 5000;            // a guard against a runaway list, not a design limit
  var RECENT = 8;                // the dropdown's recent searches
  var FORMAT = 'ordpar-personal';
  var VERSION = 2;               // 2: history entries are searches (brief 60b)
  // the settings an export carries — shell.js KEYS
  var SETTING_KEYS = ['lang', 'theme', 'colour', 'xref', 'defs', 'mini', 'peek', 'infl', 'pframes', 'minihw', 'listview',
    'minicontent', 'nestminis', 'minispacing', 'minitext', 'miniscroll', 'minifetch', 'formulas', 'ety', 'suggestrows',
    'emph', 'subsenses', 'layout', 'examples', 'exeye', 'exeyewhat', 'exlimit', 'exmore', 'stats',
    // site decisions 152: the labels setting, and Norwegian only with its settings
    'labels', 'nbonly', 'nbequiv', 'nbrows', 'nbhover', 'nbicon',
    // site decisions 159: the sound icons' speed
    'audiospeed',
    // site decisions 187: the CEFR level box; 188: the set phrases' order
    'levels', 'phraseorder'];

  /* ------------------------------------------------------------ the entries */

  function isInt(n) { return typeof n === 'number' && isFinite(n) && Math.floor(n) === n; }
  function isStr(s, max) { return typeof s === 'string' && s.length <= max; }

  /** A stored or imported entry checked and normalized; null when it is not one. */
  function cleanEntry(e) {
    if (!e || typeof e !== 'object' || Array.isArray(e)) { return null; }
    if (!isInt(e.id) || e.id <= 0) { return null; }
    if (!isStr(e.word, 300) || !e.word) { return null; }
    var hg = e.hg == null ? 0 : e.hg;
    if (!isInt(hg) || hg < 0 || hg > 99) { return null; }
    var pos = e.pos == null ? '' : e.pos;
    if (!isStr(pos, 20)) { return null; }
    if (typeof e.translated !== 'boolean') { return null; }
    var snip = e.snip == null ? '' : e.snip;
    if (!isStr(snip, 400)) { return null; }
    if (e.drop != null && !isStr(e.drop, 400)) { return null; }
    if (typeof e.t !== 'number' || !isFinite(e.t) || e.t < 0) { return null; }
    var hgs = null;
    if (e.hgs != null) {             // decisions 93: one number per spelling, 2 to 3 of them
      if (!Array.isArray(e.hgs) || e.hgs.length < 2 || e.hgs.length > 3) { return null; }
      for (var i = 0; i < e.hgs.length; i++) {
        if (!isInt(e.hgs[i]) || e.hgs[i] < 0 || e.hgs[i] > 99) { return null; }
      }
      hgs = e.hgs.slice();
    }
    var out = { id: e.id, word: e.word, hg: hg, pos: pos, translated: e.translated, snip: snip, t: e.t };
    if (hgs) { out.hgs = hgs; }
    if (e.drop != null) { out.drop = e.drop; }
    return out;
  }

  /** A stored list read leniently: anything that is not a JSON array reads as empty, an entry
   *  that is not one is dropped, a repeated id keeps its first (newest) place. */
  function parseList(raw) {
    var data;
    if (raw == null || raw === '') { return []; }
    try { data = JSON.parse(raw); } catch (e) { return []; }
    if (!Array.isArray(data)) { return []; }
    var out = [], seen = {};
    data.forEach(function (e) {
      var c = cleanEntry(e);
      if (c && !seen[c.id]) { seen[c.id] = 1; out.push(c); }
    });
    return out;
  }

  /* ------------------------------------------------- the history's entries */

  /** What makes two searches one entry: the query trimmed and lower-cased (brief 60b item 1 —
   *  *Hus* and *hus* are one; the session's call, easy to change here). */
  function searchKey(q) { return String(q == null ? '' : q).trim().toLowerCase(); }
  /** What makes two history entries one: the query (`searchKey`) in one direction — an English
   *  search (`en`, site decisions 148) is never the Norwegian search of the same word. */
  function entryKey(e) { return (e && e.en ? 'en\u0000' : '') + searchKey(e && e.q); }

  /** A stored or imported history entry checked and normalized; null when it is not one. */
  function cleanSearch(e) {
    if (!e || typeof e !== 'object' || Array.isArray(e)) { return null; }
    if (!isStr(e.q, 300)) { return null; }
    var q = e.q.trim();
    if (!q) { return null; }
    if (!isInt(e.n) || e.n < 1) { return null; }
    if (typeof e.t !== 'number' || !isFinite(e.t) || e.t < 0) { return null; }
    var out = { q: q, n: e.n, t: e.t };
    // site decisions 148 item 9: an English search, marked as English (`en`), its query and
    // count alone — drawn from its English file when shown (shell.js `englishEntryRow`)
    if (e.en === true) { out.en = true; return out; }
    if (e.n === 1) {
      if (!isStr(e.word, 300) || !e.word) { return null; }
      var hg = e.hg == null ? 0 : e.hg;
      if (!isInt(hg) || hg < 0 || hg > 99) { return null; }
      var pos = e.pos == null ? '' : e.pos;
      if (!isStr(pos, 20)) { return null; }
      if (typeof e.translated !== 'boolean') { return null; }
      var text = e.text == null ? '' : e.text;
      if (!isStr(text, 400)) { return null; }
      out.word = e.word; out.hg = hg; out.pos = pos; out.translated = e.translated; out.text = text;
    }
    return out;
  }

  /** The query an old (per-article) entry stands for: its headword, the first variant of an
   *  expression shown in alternation ("fôr / for" -> "fôr"), without a trailing " …". The
   *  " / " is the index's data separator (build_index.py `SEP`), in entries old and new alike;
   *  it is never shown (decisions 93). */
  function wordQuery(word) { return String(word).split(' / ')[0].replace(/ …$/, '').trim(); }

  /**
   * History entries stored by the build before 60b — one per article, `{id, word, hg, pos,
   * translated, snip, drop?, t}`, already checked by `cleanEntry` — read as searches for their
   * word (60b item 4): entries sharing a word (`searchKey`) become one, at the newest `t`, with
   * the spelling of the newest; the count is the number of distinct ids merged; one id keeps its
   * display fields, its text by the dropdown's rule. Newest first.
   */
  function fromArticles(list) {
    var groups = Object.create(null), order = [];
    list.forEach(function (e) {
      var q = wordQuery(e.word);
      if (!q) { return; }
      var k = searchKey(q), g = groups[k];
      if (!g) { g = groups[k] = { ids: Object.create(null), n: 0, top: e }; order.push(k); }
      if (!g.ids[e.id]) { g.ids[e.id] = 1; g.n++; }
      if (e.t > g.top.t) { g.top = e; }
    });
    return order.map(function (k) {
      var g = groups[k], e = g.top;
      var s = { q: wordQuery(e.word), n: g.n, t: e.t };
      if (g.n === 1) {
        s.word = e.word; s.hg = e.hg; s.pos = e.pos; s.translated = e.translated;
        s.text = e.translated ? dropText(e) : '';
      }
      return s;
    }).sort(byTime);
  }

  /** Several history lists as one: one entry per query (`searchKey`), the later kept, newest
   *  first, under the cap. */
  function combineHistory(lists, cap) {
    var byKey = Object.create(null);
    lists.forEach(function (list) {
      list.forEach(function (e) {
        var k = entryKey(e);
        if (!byKey[k] || byKey[k].t < e.t) { byKey[k] = e; }
      });
    });
    return Object.keys(byKey).map(function (k) { return byKey[k]; }).sort(byTime)
      .slice(0, cap == null ? CAP : cap);
  }

  /**
   * The stored history read leniently: anything that is not a JSON array reads as empty, an
   * entry that is neither shape is dropped, a repeated query keeps its first (newest) place;
   * entries of the old per-article shape are converted (`fromArticles`) and the whole then
   * ordered by time.
   */
  function parseHistory(raw) {
    var data;
    if (raw == null || raw === '') { return []; }
    try { data = JSON.parse(raw); } catch (e) { return []; }
    if (!Array.isArray(data)) { return []; }
    var searches = [], old = [], seenId = {};
    data.forEach(function (e) {
      if (e && typeof e === 'object' && !Array.isArray(e) && Object.prototype.hasOwnProperty.call(e, 'q')) {
        var s = cleanSearch(e);
        if (s) { searches.push(s); }
        return;
      }
      var c = cleanEntry(e);
      if (c && !seenId[c.id]) { seenId[c.id] = 1; old.push(c); }
    });
    if (!old.length) {
      var out = [], seen = {};
      searches.forEach(function (s) {
        var k = entryKey(s);
        if (!seen[k]) { seen[k] = 1; out.push(s); }
      });
      return out.slice(0, CAP);
    }
    return combineHistory([searches, fromArticles(old)], CAP);
  }

  /** `entry` into the history `list` (a copy): the same query (`searchKey`) taken out, the
   *  entry put in its place by time — the top, for a search just made — and the oldest past
   *  `cap` dropped. */
  function addSearch(list, entry, cap) {
    // an English search and a Norwegian one of the same word are two entries (site decisions
    // 148: *house*, the English word, and *house*, the Norwegian music genre)
    var k = entryKey(entry);
    var out = list.filter(function (e) { return entryKey(e) !== k; });
    var at = 0;
    while (at < out.length && out[at].t > entry.t) { at++; }
    out.splice(at, 0, entry);
    return out.slice(0, cap == null ? CAP : cap);
  }

  function indexOf(list, id) {
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) { return i; } }
    return -1;
  }

  /** `entry` at the top of `list` (a copy): an entry already listed moves up, the oldest past
   *  `cap` drop off. */
  function addTo(list, entry, cap) {
    var out = list.filter(function (e) { return e.id !== entry.id; });
    out.unshift(entry);
    return out.slice(0, cap == null ? CAP : cap);
  }

  function removeFrom(list, id) { return list.filter(function (e) { return e.id !== id; }); }

  function byTime(a, b) { return b.t - a.t; }

  /* ------------------------------------------------------------- the storage */

  var listeners = [];

  function storage() { try { return global.localStorage || null; } catch (e) { return null; } }
  function readRaw(key) { try { var s = storage(); return s ? s.getItem(key) : null; } catch (e) { return null; } }
  function writeRaw(key, value) {
    try { var s = storage(); if (!s) { return false; } s.setItem(key, value); return true; }
    catch (e) { return false; }                 // full, or blocked: degrade silently
  }
  function dropRaw(key) { try { var s = storage(); if (s) { s.removeItem(key); } } catch (e) { /* blocked */ } }

  function load(key) { return key === HISTORY_KEY ? parseHistory(readRaw(key)) : parseList(readRaw(key)); }
  function save(key, list) {
    return list.length ? writeRaw(key, JSON.stringify(list)) : (dropRaw(key), true);
  }

  function notify(what) {
    listeners.slice().forEach(function (fn) { try { fn(what); } catch (e) { /* a page's own bug */ } });
    refresh();
  }

  function now() { return Date.now(); }

  /** A row's fields as given by a caller (the page's attributes, a search result), stamped. */
  function stamp(fields, t) {
    var e = {
      id: Number(fields.id), word: String(fields.word || ''), hg: Number(fields.hg) || 0,
      pos: String(fields.pos || ''), translated: !!fields.translated,
      snip: String(fields.snip || ''), t: t == null ? now() : t
    };
    if (fields.drop != null) { e.drop = String(fields.drop); }
    if (Array.isArray(fields.hgs)) { e.hgs = fields.hgs.map(Number); }
    return cleanEntry(e);
  }

  /**
   * Record a search that found something (brief 60b item 1): `fields` = {q, n} and, when n is 1,
   * {word, hg, pos, translated, text}; `t` the time the search was made (the caller's, so an
   * entry whose display fields arrived late still takes its place by time — `addSearch`).
   * A repeat (`searchKey`) moves to the top with the spelling typed last; the cap holds.
   */
  function recordSearch(fields, t) {
    var f = fields || {};
    var e = { q: String(f.q == null ? '' : f.q).trim(), n: Number(f.n), t: t == null ? now() : t };
    if (f.en) { e.en = true; }                 // site decisions 148: an English search
    else if (e.n === 1) {
      e.word = String(f.word || ''); e.hg = Number(f.hg) || 0; e.pos = String(f.pos || '');
      e.translated = !!f.translated; e.text = String(f.text == null ? '' : f.text);
    }
    e = cleanSearch(e);
    if (!e) { return false; }
    var ok = save(HISTORY_KEY, addSearch(load(HISTORY_KEY), e, CAP));
    notify('history');
    return ok;
  }

  function isFavourite(id) { return indexOf(load(FAV_KEY), Number(id)) !== -1; }

  /** Save or remove (`on`) an article; returns the state now stored. */
  function setFavourite(fields, on) {
    var list = load(FAV_KEY), id = Number(fields.id);
    if (on) {
      var e = stamp(fields);
      if (!e) { return false; }
      if (indexOf(list, id) === -1) { list = addTo(list, e, FAV_CAP); }
    } else {
      list = removeFrom(list, id);
    }
    save(FAV_KEY, list);
    notify('favourites');
    return isFavourite(id);
  }

  function toggleFavourite(fields) { return setFavourite(fields, !isFavourite(fields.id)); }

  function clearHistory() { dropRaw(HISTORY_KEY); notify('history'); }

  /* ------------------------------------------------------- export and import */

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  /** `ordpar-<date>.txt`, the local date — a `.txt` holding the export's JSON (Robin,
   *  decisions 60: a file every phone and mail program opens and sends); the import reads a
   *  `.txt` and a `.json` alike. */
  function exportName(date) {
    date = date || new Date();
    return 'ordpar-' + date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) + '.txt';
  }

  /** The export file's object: the format and version first, then the three lists. */
  function makeExport(settings, history, favourites, when) {
    var s = {};
    SETTING_KEYS.forEach(function (k) {
      if (settings && typeof settings[k] === 'string') { s[k] = settings[k]; }
    });
    return {
      format: FORMAT, version: VERSION,
      exported: new Date(when == null ? now() : when).toISOString(),
      settings: s, history: history.slice(0, CAP), favourites: favourites.slice()
    };
  }

  /**
   * Read an export file's text, strictly. -> {ok: true, data: {settings, history, favourites}}
   * or {ok: false, error: 'parse' | 'format' | 'version' | 'content'}. Nothing is written.
   * A newer version is refused (a later build's file may mean something this one cannot read);
   * an unknown setting is ignored, a known one must be a string; every entry must be whole, in
   * its version's shape. Version 1's history (one entry per article) comes back converted to
   * searches (`fromArticles`, brief 60b item 5); version 2's is searches already.
   */
  function readImport(text) {
    var data;
    try { data = JSON.parse(text); } catch (e) { return { ok: false, error: 'parse' }; }
    if (!data || typeof data !== 'object' || Array.isArray(data) || data.format !== FORMAT) {
      return { ok: false, error: 'format' };
    }
    if (!isInt(data.version) || data.version < 1) { return { ok: false, error: 'format' }; }
    if (data.version > VERSION) { return { ok: false, error: 'version' }; }
    var settings = data.settings == null ? {} : data.settings;
    if (typeof settings !== 'object' || Array.isArray(settings)) { return { ok: false, error: 'content' }; }
    var s = {};
    for (var i = 0; i < SETTING_KEYS.length; i++) {
      var k = SETTING_KEYS[i];
      if (Object.prototype.hasOwnProperty.call(settings, k)) {
        if (!isStr(settings[k], 40)) { return { ok: false, error: 'content' }; }
        s[k] = settings[k];
      }
    }
    var lists = {};
    var names = ['history', 'favourites'];
    for (var n = 0; n < names.length; n++) {
      var raw = data[names[n]] == null ? [] : data[names[n]];
      if (!Array.isArray(raw)) { return { ok: false, error: 'content' }; }
      var searches = names[n] === 'history' && data.version >= 2;
      var out = [];
      for (var j = 0; j < raw.length; j++) {
        var c = searches ? cleanSearch(raw[j]) : cleanEntry(raw[j]);
        if (!c) { return { ok: false, error: 'content' }; }
        out.push(c);
      }
      lists[names[n]] = out;
    }
    var history = data.version >= 2 ? combineHistory([lists.history], CAP) : fromArticles(lists.history).slice(0, CAP);
    return { ok: true, data: { settings: s, history: history, favourites: lists.favourites } };
  }

  /**
   * The merge (decisions 60 item 7): favourites — those present kept, the file's added where
   * their id is new, newest first; history — both combined, one entry per query (`searchKey`,
   * the later search kept), ordered by time, newest first, under the cap; settings — the file's.
   */
  function mergeImport(current, data) {
    var fav = current.favourites.slice(), added = 0;
    data.favourites.forEach(function (e) {
      if (indexOf(fav, e.id) === -1) { fav.push(e); added++; }
    });
    fav.sort(byTime);
    var hist = combineHistory([current.history, data.history], CAP);
    var had = {};
    current.history.forEach(function (e) { had[searchKey(e.q)] = 1; });
    var newHist = hist.filter(function (e) { return !had[searchKey(e.q)]; }).length;
    return {
      settings: data.settings, history: hist, favourites: fav.slice(0, FAV_CAP),
      added: { favourites: added, history: newHist }
    };
  }

  /** The device's export, `getSetting` reading each setting (the shell's). */
  function exportData(getSetting, when) {
    var s = {};
    SETTING_KEYS.forEach(function (k) {
      var v = getSetting ? getSetting(k) : readRaw(k);
      if (typeof v === 'string') { s[k] = v; }
    });
    return makeExport(s, load(HISTORY_KEY), load(FAV_KEY), when);
  }

  /**
   * Import a file's text into this device: read strictly, merge, then write all three — and
   * if a write fails (storage full or blocked), put back what was there, so the device is
   * never left half-imported. -> {ok, error?, added?}
   */
  function importText(text) {
    var got = readImport(text);
    if (!got.ok) { return got; }
    if (!storage()) { return { ok: false, error: 'storage' }; }
    var before = {};
    [HISTORY_KEY, FAV_KEY].concat(SETTING_KEYS).forEach(function (k) { before[k] = readRaw(k); });
    var merged = mergeImport({ history: load(HISTORY_KEY), favourites: load(FAV_KEY) }, got.data);
    var ok = save(HISTORY_KEY, merged.history) && save(FAV_KEY, merged.favourites);
    Object.keys(merged.settings).forEach(function (k) { ok = ok && writeRaw(k, merged.settings[k]); });
    if (!ok) {
      Object.keys(before).forEach(function (k) {
        if (before[k] == null) { dropRaw(k); } else { writeRaw(k, before[k]); }
      });
      return { ok: false, error: 'storage' };
    }
    notify('import');
    return { ok: true, added: merged.added, settings: Object.keys(merged.settings).length };
  }

  /* ---------------------------------------------------------- the display */

  /** The row's one gloss unit: the snippet up to its first " · ". */
  function unit(e) { return (e.snip || '').split(' · ')[0]; }

  /** The dropdown's right-hand text for a translated entry, as the suggestions show it: the
   *  set-phrase box where there is one, else (an override of '' too: a set phrase with no box,
   *  site decisions 82, Robin 2026-10-21) the first gloss unit. */
  function dropText(e) { return e.drop ? e.drop : unit(e); }

  var HEART = 'M12 20.5s-7.2-4.4-9.4-8.6C1 8.8 2.6 5.2 6.1 5c2.3-.1 4.2 1.3 5.9 3.4C13.7 6.3 15.6 4.9 17.9 5c3.5.2 5.1 3.8 3.5 6.9-2.2 4.2-9.4 8.6-9.4 8.6z';

  function svgHeart(cls) {
    var doc = global.document;
    var ns = 'http://www.w3.org/2000/svg';
    var svg = doc.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('class', cls);
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    var path = doc.createElementNS(ns, 'path');
    path.setAttribute('d', HEART);
    svg.appendChild(path);
    return svg;
  }

  // the heart's one name in both states (brief 60b item 6: `aria-pressed` alone carries the
  // state), and the closed row's mark
  var labels = { label: 'Favourite', saved: 'In favourites' };
  /** The interface's words for the heart (the shell's strings, or the article page's). */
  function setLabels(l) { for (var k in l) { if (l[k]) { labels[k] = l[k]; } } }

  function paintHeart(btn, on) {
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.setAttribute('aria-label', labels.label);
    btn.title = labels.label;
  }

  /**
   * The heart (decisions 60 item 4): a toggle button, `aria-pressed`, an outline heart when the
   * article is not saved and a filled one when it is, labelled "Favourite" in both states (brief
   * 60b item 6 — the pressed state is the toggle's, not the name's). Every heart and mark for the same article on the page follows a click at
   * once (`refresh`), and another tab's change too (the `storage` event).
   */
  function heartButton(fields, cls) {
    var doc = global.document;
    var btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = 'ordpar-heart' + (cls ? ' ' + cls : '');
    btn.setAttribute('data-fav-id', String(fields.id));
    btn.appendChild(svgHeart('ordpar-heart-icon'));
    paintHeart(btn, isFavourite(fields.id));
    btn.addEventListener('click', function () { toggleFavourite(fields); });
    return btn;
  }

  /** The small filled heart beside a saved article's headword in a closed list row. */
  function favMark(id) {
    var doc = global.document;
    var span = doc.createElement('span');
    span.className = 'ordpar-fav-mark';
    span.setAttribute('data-fav-mark', String(id));
    span.setAttribute('role', 'img');
    span.setAttribute('aria-label', labels.saved);
    span.appendChild(svgHeart('ordpar-heart-icon'));
    span.hidden = !isFavourite(id);
    return span;
  }

  /** Bring every heart and mark on the page in step with the stored favourites. */
  function refresh(root) {
    var doc = global.document;
    if (!doc || !doc.querySelectorAll) { return; }
    var fav = {};
    load(FAV_KEY).forEach(function (e) { fav[e.id] = 1; });
    var scope = root || doc;
    Array.prototype.forEach.call(scope.querySelectorAll('[data-fav-id]'), function (b) {
      paintHeart(b, !!fav[b.getAttribute('data-fav-id')]);
    });
    Array.prototype.forEach.call(scope.querySelectorAll('[data-fav-mark]'), function (m) {
      m.hidden = !fav[m.getAttribute('data-fav-mark')];
    });
  }

  /** An entry's fields from an element's data attributes — the article page's `<html>`
   *  (`sitegen/page.py` `personal_attrs`). A page leaves `data-snip` out where the snippet is its
   *  meta description (2026-10-20, the size report's item 7): the description is read then. */
  function fieldsFrom(node) {
    var g = function (k) { return node.getAttribute(k); };
    var snip = g('data-snip');
    if (snip == null) {
      var meta = node.ownerDocument && node.ownerDocument.querySelector('meta[name="description"]');
      snip = meta ? meta.getAttribute('content') : '';
    }
    var f = {
      id: Number(g('data-article-id')), word: g('data-word') || g('data-lemma') || '',
      hg: Number(g('data-hg')) || 0, pos: g('data-pos') || '',
      translated: g('data-translated') === '1', snip: snip || ''
    };
    if (node.hasAttribute('data-drop')) { f.drop = g('data-drop'); }
    // decisions 93: the spellings' own numbers where they differ ("1 2"; page.py personal_attrs)
    if (node.hasAttribute('data-hgs')) { f.hgs = g('data-hgs').split(' ').map(Number); }
    return f;
  }

  /**
   * The article page's part (called by `/site/article.js`): the heart put beside Copy link and
   * Share at the foot of the article's card (decisions 63). The visit is not recorded: the
   * history is a list of searches (brief 60b item 1; the browser's own history keeps page
   * visits). `l`: the page's words ({label, saved}).
   */
  function mountPage(l) {
    var doc = global.document, root = doc.documentElement;
    if (!root.getAttribute('data-article-id')) { return; }
    setLabels(l || {});
    var f = fieldsFrom(root);
    // decisions 63: the article's card carries Copy link, Share and the heart at its foot, as a
    // full search result does; the header's "Favourites" link is the shared header's own
    var ctl = doc.querySelector('.ordpar-card-foot .ordpar-result-controls');
    if (ctl && !ctl.querySelector('.ordpar-heart')) { ctl.appendChild(heartButton(f, 'ordpar-result-heart')); }
  }

  try {
    global.addEventListener('storage', function (ev) {
      if (!ev || ev.key == null || ev.key === HISTORY_KEY || ev.key === FAV_KEY) { notify('storage'); }
    });
  } catch (e) { /* no window */ }

  /*
   * The search's direction (site decisions 148: the switch is remembered):
   * 'en' while the English switch is on, saved on the device under DIRECTION_KEY beside the
   * settings (not a row on the Settings page, not in an export), so a new visit opens in the
   * direction last used; Norwegian ('nb') until the reader first switches. "Delete stored data"
   * (`localStorage.clear`) takes it with the rest. `setDirection` -> false where storage is
   * blocked (shell.js then keeps it for the page alone).
   */
  var DIRECTION_KEY = 'direction';
  function direction() { return readRaw(DIRECTION_KEY) === 'en' ? 'en' : 'nb'; }
  function setDirection(d) {
    try {
      var s = storage();
      if (!s) { return false; }
      if (d === 'en') { s.setItem(DIRECTION_KEY, 'en'); } else { s.removeItem(DIRECTION_KEY); }
      return (s.getItem(DIRECTION_KEY) === 'en') === (d === 'en');
    } catch (e) { return false; }
  }

  var api = {
    DIRECTION_KEY: DIRECTION_KEY, direction: direction, setDirection: setDirection, entryKey: entryKey,
    HISTORY_KEY: HISTORY_KEY, FAV_KEY: FAV_KEY, CAP: CAP, RECENT: RECENT,
    FORMAT: FORMAT, VERSION: VERSION, SETTING_KEYS: SETTING_KEYS,
    cleanEntry: cleanEntry, parseList: parseList, addTo: addTo, removeFrom: removeFrom,
    searchKey: searchKey, cleanSearch: cleanSearch, parseHistory: parseHistory,
    fromArticles: fromArticles, addSearch: addSearch, combineHistory: combineHistory,
    makeExport: makeExport, exportName: exportName, readImport: readImport, mergeImport: mergeImport,
    history: function () { return load(HISTORY_KEY); },
    favourites: function () { return load(FAV_KEY); },
    recordSearch: recordSearch, isFavourite: isFavourite, setFavourite: setFavourite,
    toggleFavourite: toggleFavourite, clearHistory: clearHistory,
    exportData: exportData, importText: importText,
    onChange: function (fn) { listeners.push(fn); },
    unit: unit, dropText: dropText, setLabels: setLabels,
    heartButton: heartButton, favMark: favMark, refresh: refresh, fieldsFrom: fieldsFrom,
    mountPage: mountPage
  };
  global.ordparPersonal = api;
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
}(typeof globalThis !== 'undefined' ? globalThis : this));
