/*! Ordpar — the site chrome: settings on the device, the header's search combobox.
 *
 * Loaded by EVERY page — the shell pages and, since decisions 63, the article and About pages.
 *
 *   window.ordparShell = {
 *     t(key), has(key),           // a string from strings/<lang>.json (the key if absent); is it there
 *     getSetting(key),            // any key of SETTINGS below (the visit, localStorage, defaults)
 *     savedSetting(key), popupAddress(), copyText(text, node), // site decisions 146
 *     setSetting(key, value),     // stores, applies, relabels the chrome in place
 *     SETTINGS, KEYS, colours(),  // the settings' table (the settings page draws from it)
 *     lang, onChange(fn), setSearchHandler(fn), event(name, data), ...
 *   }
 *
 * The header and the footer are NOT drawn here (decisions 63): they are static markup from ONE
 * source, `ordpar/sitegen/chrome.py`, on every page. This file ENHANCES the header — the box
 * becomes a combobox (role, aria-*), with the × button and the dropdown (suggestions while
 * typing, "Recent" when empty) — wires Random word, and relabels the chrome from the strings
 * (another interface language without a rebuild, decisions 24): every `data-ordpar-string`
 * element, and the static ones `chrome.py` writes, found by `STATIC_STRINGS`. Since 2026-10-20
 * (the size report's item 5) it also MAKES the chrome that needs script, which the pages no
 * longer carry hidden: the header's Random word, Favourites and Settings, the footer's
 * Settings, Favourites and History (`addChrome`; `shell.css` holds their room until then), and
 * on a phone the install hint (decisions 68, `install.js` `hint`). The
 * settings are a page of their own, `/settings/`, drawn by `settings.js` from `SETTINGS`.
 *
 * Settings are localStorage, one key per setting, no cookies and no third party
 * (decisions 19). The interface language is never in the URL (decisions 21a) — except in the
 * address for a pop-up dictionary (site decisions 146): settings after `#`, read by the head
 * script and kept for that tab's or pop-up's visit, never saved (`sitegen/head.py`, `read`).
 *
 * Paint order: every page runs the head script `sitegen/head.py` THEME_JS (one copy,
 * `/site/theme.js`, parser-blocking in the head), which applies the theme, the colour scheme
 * (`data-accent`) and the article settings' classes before the first paint, and puts
 * `ordpar-js` on <html> (`shell.css` then holds the room of the chrome made here).
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var LANGS = ['en'];                       // only English exists today (decisions 21a)
  /*
   * THE SETTINGS (decisions 63: a new setting is one entry here, in its section — the settings
   * page draws them in this order; its words are `settings.<key>` and `settings.<key>.<value>`).
   * `values`: the valid stored values (any other reads as `def`); `colour`'s come from the
   * colour table (`sitegen/colours.py`, `window.ORDPAR_COLOURS`), `lang`'s from LANGS.
   * `section`: style | article | search | data (the settings page's sections; "Loading, offline
   * and your data" holds one setting of this kind since decisions 92, `minifetch`, under its
   * subsection *Loading*, before the offline copy and the stored data). `sub` (decisions 85, Robin
   * 2026-10-21): the subsection a setting sits under — *Article*'s language | inflection | xref |
   * mini, *data*'s loading (`settings.sub.<sub>`), in this order; the table keeps each
   * subsection's settings together. Neither key is stored: a setting's key and values never
   * change, so a reader's saved settings survive a regrouping (`minifetch` moved from Article →
   * Small articles in 92 and kept every reader's choice).
   */
  var SETTINGS = [
    { key: 'theme', values: ['system', 'light', 'dark'], def: 'system', section: 'style' },
    { key: 'colour', values: null, def: null, section: 'style' },
    { key: 'lang', values: LANGS, def: null, section: 'style' },
    { key: 'layout', values: ['ordpar', 'ordbokene'], def: 'ordpar', section: 'style' },   // decisions 87: the layout closer to ordbokene.no
    // site decisions 152: NORWEGIAN ONLY, a layer over the reader's own settings (`layer` below):
    // on, the articles in Norwegian only, nothing to reveal; off, the reader's settings as they
    // were. Its own subsection at the head of the Article settings; `layer: true` keeps the five
    // out of the presets (a layer is not a preset). "English equivalents" (the glosses, the rows'
    // and the hovers' English, the search's English switch) and, with them hidden, what the rows'
    // right side and the hovers show; the header icon, optional
    { key: 'nbonly', values: ['off', 'on'], def: 'off', section: 'article', sub: 'nbonly', layer: true },
    { key: 'nbequiv', values: ['hidden', 'shown'], def: 'hidden', section: 'article', sub: 'nbonly', layer: true },
    { key: 'nbrows', values: ['nbdef', 'none'], def: 'nbdef', section: 'article', sub: 'nbonly', layer: true },
    { key: 'nbhover', values: ['none', 'nbdef'], def: 'none', section: 'article', sub: 'nbonly', layer: true },
    { key: 'nbicon', values: ['on', 'off'], def: 'on', section: 'article', sub: 'nbonly', layer: true },
    { key: 'defs', values: ['both', 'en', 'no'], def: 'both', section: 'article', sub: 'language' },
    { key: 'examples', values: ['both', 'no'], def: 'both', section: 'article', sub: 'language' },   // decisions 111: the examples' English behind a reveal
    // decisions 131 (Robin, 2026-10-25): the deck's eye beside the headword, off by default (first)
    { key: 'exeye', values: ['off', 'on'], def: 'off', section: 'article', sub: 'language' },
    // decisions 186: what the eye hides — the examples' English (the default, first, the eye of 131)
    // or every English line of its article but the etymology; shown only while the eye is on
    { key: 'exeyewhat', values: ['examples', 'all'], def: 'examples', section: 'article', sub: 'language' },
    // site decisions 187: the CEFR level box after the headword and on each embedded set phrase,
    // off by default; beside the eye's settings, the other aid for learners at the headword ("For
    // learners" turns both on). The pages carry the box always; the class shows it
    { key: 'levels', values: ['off', 'on'], def: 'off', section: 'article', sub: 'language' },
    // site decisions 188: the order of an article's set phrases, alphabetical as in Bokmålsordboka
    // (the default) or by CEFR level, A1 first; right below the level box's setting and shown only
    // while it is on (`settings.js` `shown`); the sheet orders by level only while the boxes are on
    { key: 'phraseorder', values: ['alpha', 'level'], def: 'alpha', section: 'article', sub: 'language' },
    // decisions 112: how many examples show under each sense and subsense (a drop-down, `control`),
    // and whether a "Show N more examples" line opens the rest (drawn only while a number is set)
    { key: 'exlimit', values: ['all', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], def: 'all', section: 'article', sub: 'language', control: 'select' },
    { key: 'exmore', values: ['on', 'off'], def: 'on', section: 'article', sub: 'language' },
    // site decisions 174 (the default is the "Norwegian emphasized" option, and Short formula
    // lines such as "used as an adverb:" default to "In Norwegian and English"): `emph` no and `formulas` both, each listed first (107); `en` and
    // `en` until then, kept as the preset "English emphasized" (`settings.js` `PRESETS`)
    { key: 'emph', values: ['no', 'en'], def: 'no', section: 'article', sub: 'language' },   // decisions 87: the emphasized line
    { key: 'subsenses', values: ['defs', 'en'], def: 'defs', section: 'article', sub: 'language' },   // decisions 90: subsenses in English only
    { key: 'formulas', values: ['both', 'en', 'no'], def: 'both', section: 'article', sub: 'language' },   // decisions 81: formula lines; 174: both the default
    { key: 'ety', values: ['en', 'no', 'both'], def: 'en', section: 'article', sub: 'language' },   // decisions 84: the etymology line
    // site decisions 152 (Robin, 2026-10-30/31): the labels inside the article frame — its headings
    // and buttons, the word class and the inflection tables' words — in English (first) or
    // Norwegian; apart from the interface language. The Norwegian-only layer turns them all
    // Norwegian whatever this says (152's follow-up: the sheet's `ordpar-nbo` rules), never writing
    // it. Last under Article's Language (152's follow-up: it belongs under Article, not
    // Style; under Style until then); `layer: true` keeps it out of the presets (136), as the
    // Norwegian-only settings
    { key: 'labels', values: ['en', 'no'], def: 'en', section: 'article', sub: 'language', layer: true },
    { key: 'infl', values: ['button', 'open'], def: 'button', section: 'article', sub: 'inflection' },
    { key: 'pframes', values: ['on', 'off'], def: 'on', section: 'article', sub: 'inflection' },
    { key: 'xref', values: ['mini', 'page'], def: 'mini', section: 'article', sub: 'xref' },
    // site decisions 185: what a linked word shows while the pointer rests on it — its translation
    // (`on`, the default), its first Norwegian definition (`nb`) or nothing (`off`); `on` and `off`
    // keep their keys, so a stored value or an address reads as before
    { key: 'peek', values: ['on', 'nb', 'off'], def: 'on', section: 'article', sub: 'xref' },
    { key: 'mini', values: ['article', 'both', 'en'], def: 'article', section: 'article', sub: 'mini' },
    // decisions 80: the mini made from the target's own page
    { key: 'minicontent', values: ['full', 'slim'], def: 'full', section: 'article', sub: 'mini' },
    // decisions 139 (Robin, 2026-10-26), 147 (2026-10-29): a link inside a small article — its small
    // article in the same box, in a second box and then in that box (the default), in a box of its
    // own each time, or its whole article; no limit (147: the second boxes' limit went); `mini.js`
    // reads it itself
    { key: 'nestminis', values: ['second', 'inplace', 'stacked', 'off'], def: 'second', section: 'article', sub: 'mini' },
    // decisions 97: the article's spacing the default (Robin, 2026-10-23); a stored 'compact' stays
    { key: 'minispacing', values: ['article', 'compact'], def: 'article', section: 'article', sub: 'mini' },
    // decisions 114: the mini's text sizes — the article's (the default, first) or today's smaller ones
    { key: 'minitext', values: ['article', 'smaller'], def: 'article', section: 'article', sub: 'mini' },
    { key: 'miniscroll', values: ['on', 'off'], def: 'on', section: 'article', sub: 'mini' },
    { key: 'minihw', values: ['link', 'article'], def: 'link', section: 'article', sub: 'mini' },   // decisions 78: the mini's headword (under Style until decisions 85)
    // site decisions 159 (Robin, 2026-11-02: below 90 % the voice distorts): the speed of the sound
    // icons' clips — the recordings' own (the default, first) or 90 % of it, the pitch kept
    // (`audio.js` reads it at each press); its own subsection, last under Article
    { key: 'audiospeed', values: ['recorded', '90'], def: 'recorded', section: 'article', sub: 'audio' },
    // decisions 158 (Robin, 2026-11-01): the list also when the search finds an inflected form, the
    // new default, listed first (107); `multi` (decisions 71: the list only for several articles,
    // the default until 158), `on` and `off` unchanged, a stored value kept
    { key: 'listview', values: ['forms', 'multi', 'on', 'off'], def: 'forms', section: 'search' },
    { key: 'suggestrows', values: ['standard', 'roomy'], def: 'standard', section: 'search' },   // decisions 86: roomier suggestion rows
    // decisions 80, 92: when an article or a page is loaded ahead (ahead.js) — the minis' setting
    // until 92, which widened it to every in-site link and moved it here, key and values kept
    { key: 'minifetch', values: ['point', 'click', 'page'], def: 'point', section: 'data', sub: 'loading' },
    // decisions 104: the opt-out of the events (`events.js` reads it); drawn only while the counting
    // is live (`gate`: `window.ORDPAR_COUNTING`, which the build writes into the settings page only
    // while `events.js` `RECEIVER` is set, `chrome.counting()`; site decisions 166), after the
    // offline copy and the transfer, before the stored data
    { key: 'stats', values: ['on', 'off'], def: 'on', section: 'data', gate: 'counting' }
  ];
  var SPEC = {};
  SETTINGS.forEach(function (sp) { SPEC[sp.key] = sp; });
  var KEYS = SETTINGS.map(function (sp) { return sp.key; });
  var ARTICLE_KEYS = ['defs', 'mini', 'peek'];   // decisions 54: applied as classes on <html>
  /* the settings that are a class on <html> alone (`applyClassKeys`) */
  var CLASS_KEYS = ['pframes', 'minihw', 'minicontent', 'minispacing', 'minitext', 'miniscroll', 'minifetch',
    'formulas', 'ety', 'suggestrows', 'emph', 'subsenses', 'layout', 'examples', 'exeye', 'exeyewhat', 'exlimit', 'exmore', 'levels',
    'phraseorder'];
  var COLOUR_ID = /^[a-z][a-z0-9-]*$/;
  var strings = {};                          // lang -> {key: string}
  var listeners = [];
  var searchHandler = null;
  var lang = 'en';

  /* --------------------------------------------------------------- storage */

  /* Site decisions 146: a setting as it holds on this page — the visit's (settings in the
   * address, kept for the tab or pop-up: the head script, `sitegen/head.py`, `ordparRead`), else
   * the saved one; `saved` reads the saved one alone (`localStorage`), as the settings page and the
   * Copy of the pop-up address do. Without the head script, the saved one. */
  function read(key) {
    if (typeof global.ordparRead === 'function') { return global.ordparRead(key); }
    return saved(key);
  }
  function saved(key) {
    try { return global.localStorage.getItem(key); } catch (e) { return null; }
  }
  function write(key, value) {
    try { global.localStorage.setItem(key, value); } catch (e) { /* private mode */ }
  }
  function drop(key) {
    try { global.localStorage.removeItem(key); } catch (e) { /* private mode */ }
  }

  /* Site decisions 146 (the session's call, 2026-10-28): a setting the reader changes ends the
   * visit's value for that key, and "Reset settings" (`key` absent) the whole visit, so the change
   * holds on this tab's other pages too and the visit never outvotes the reader's own choice. The
   * visit is `sessionStorage` VISIT_KEY (`sitegen/head.py` VISIT_KEY, the same name) and, on a page
   * the head script gave one, `ordparVisit.settings` (the object `ordparRead` reads). */
  var VISIT_KEY = 'ordpar-visit';
  function leaveVisit(key) {
    var V = global.ordparVisit && global.ordparVisit.settings;
    if (V) { if (key) { delete V[key]; } else { Object.keys(V).forEach(function (k) { delete V[k]; }); } }
    try {
      var S = global.sessionStorage, v = JSON.parse(S.getItem(VISIT_KEY));
      if (!v || typeof v !== 'object') { return; }
      if (key) { delete v[key]; S.setItem(VISIT_KEY, JSON.stringify(v)); } else { S.removeItem(VISIT_KEY); }
    } catch (e) { /* storage blocked: the visit lives in this page alone */ }
  }

  function browserLang() {
    var nav = global.navigator || {};
    var list = (nav.languages && nav.languages.length ? nav.languages : [nav.language || 'en']);
    for (var i = 0; i < list.length; i++) {
      var code = String(list[i] || '').toLowerCase().split('-')[0];
      if (LANGS.indexOf(code) !== -1) { return code; }
    }
    return 'en';
  }

  /** The colour schemes, where the page carries them (`/settings/`; `sitegen/colours.py`). */
  function colours() { return global.ORDPAR_COLOURS || null; }

  function getSetting(key) { return valueOf(key, read(key)); }

  /** The setting as saved on this device, the visit's left aside (site decisions 146). */
  function savedSetting(key) { return valueOf(key, saved(key)); }

  /** The colour schemes' ids and the default's: the settings page's full table, else the head
   *  script's copy (`ordparVisit`, site decisions 146), else none known. */
  function colourIds() {
    var list = colours();
    if (list) {
      var d = list.filter(function (c) { return c.default; })[0];
      return { ids: list.map(function (c) { return c.id; }), def: d ? d.id : null };
    }
    var V = global.ordparVisit;
    return V && V.table && V.table.colour ? { ids: V.table.colour, def: V.colour || null } : null;
  }

  function valueOf(key, v) {
    if (key === 'lang') { return v && LANGS.indexOf(v) !== -1 ? v : browserLang(); }
    if (key === 'colour') {
      var known = colourIds();
      var ok = v && COLOUR_ID.test(v) && (!known || known.ids.indexOf(v) !== -1);
      if (ok) { return v; }
      return known ? known.def : null;
    }
    var sp = SPEC[key];
    if (!sp) { return v; }
    return sp.values.indexOf(v) !== -1 ? v : sp.def;
  }

  /*
   * Site decisions 152 (Robin, 2026-10-30/31): NORWEGIAN ONLY, a LAYER over the reader's own
   * settings, never a preset that rewrites them. While `nbonly` is on, the classes of seven
   * settings are drawn from the layer's values (`LAYER_VALUES`, and the hover by `nbequiv` /
   * `nbhover`) instead of the reader's, which stay stored as they were (`eff`); off, the page is
   * exactly the reader's settings. It changes the language only: the layout and every look
   * setting stay the reader's. The head script (`sitegen/head.py` THEME_JS) draws the same classes
   * before the first paint; this file keeps them in step on a change. `layer()` -> {on, hidden
   * (the English equivalents hidden), rows ('nbdef' | 'none', only while hidden), hover (the same)}.
   */
  var LAYER_VALUES = { defs: 'no', examples: 'no', formulas: 'no', ety: 'no', mini: 'article', subsenses: 'defs' };
  var LAYER_KEYS = ['nbonly', 'nbequiv', 'nbrows', 'nbhover', 'nbicon', 'labels'];
  function layer() {
    var on = getSetting('nbonly') === 'on';
    var hidden = on && getSetting('nbequiv') === 'hidden';
    return { on: on, hidden: hidden, rows: hidden ? getSetting('nbrows') : null,
      hover: hidden ? getSetting('nbhover') : null };
  }
  /** A setting as the page draws it: the layer's value while Norwegian only is on, else the
   *  reader's (`getSetting`). The hover: with the equivalents hidden, on only for the Norwegian
   *  definition (the English peeks then hidden by the sheet, `ordpar-nbo-hovnb`). */
  function eff(key) {
    var L = layer();
    if (L.on && Object.prototype.hasOwnProperty.call(LAYER_VALUES, key)) { return LAYER_VALUES[key]; }
    if (key === 'peek' && L.hidden) { return L.hover === 'nbdef' ? 'on' : 'off'; }
    return getSetting(key);
  }
  /** Whether a linked word's peek is its first Norwegian definition (`ordpar-nbo-hovnb`): with
   *  the English equivalents hidden under Norwegian only, as `nbhover` says (it lies over `peek`
   *  there); otherwise as `peek` says, `nb` (site decisions 185). */
  function hoverNb() {
    var L = layer();
    return L.hidden ? L.hover === 'nbdef' : getSetting('peek') === 'nb';
  }
  /** The word class and the inflection tables' words in Norwegian: under the layer, or with the
   *  labels setting Norwegian (either is enough, Robin 2026-10-31). */
  function nbWords() { return getSetting('labels') === 'no' || layer().on; }

  /*
   * Site decisions 146 (Robin, 2026-10-27/28): THE ADDRESS FOR A POP-UP DICTIONARY, such as
   * Definer — the search address with the reader's SAVED settings in it, `{{str}}` where the
   * word goes, last. Every setting of the table that differs from its default, in the table's
   * order, as `key=value` after `#` (the head script reads them back: `sitegen/head.py`); with
   * every setting at its default exactly `https://ordpar.no/bm-en/#q={{str}}`. `colour` differs
   * when it is a scheme other than the default; `lang` when it is a language other than the
   * browser's (the default). One function for `/more/` and Settings.
   */
  var POPUP_ADDRESS = 'https://ordpar.no/bm-en/#';
  var POPUP_WORD = 'q={{str}}';

  function popupAddress() {
    var pairs = [];
    SETTINGS.forEach(function (sp) {
      var raw = saved(sp.key), v = savedSetting(sp.key);
      if (raw == null || v !== raw) { return; }        // not saved, or not a value it accepts
      var def = sp.key === 'colour' ? (colourIds() || {}).def
        : sp.key === 'lang' ? browserLang() : sp.def;
      if (v !== def) { pairs.push(sp.key + '=' + v); }
    });
    return POPUP_ADDRESS + pairs.concat(POPUP_WORD).join('&');
  }

  /**
   * Copy `text` to the clipboard (site decisions 146) -> a promise of true when it was copied.
   * The clipboard where the browser offers it; where it refuses (no secure context, a blocked
   * permission), the line `node` holding the text is selected and the browser's copy command
   * tried on the selection — true only if that reports success; else the line stays selected, so
   * the reader can copy it, and false (the caller then says nothing). `reveal` (optional) runs
   * first on that path: Settings shows its line, hidden until then.
   */
  function copyText(text, node, reveal) {
    var nav = global.navigator || {};
    var bySelection = function () {
      if (reveal) { try { reveal(); } catch (e) { /* the caller's own bug */ } }
      if (!node || !doc.createRange || !global.getSelection) { return false; }
      try {
        var range = doc.createRange();
        range.selectNodeContents(node);
        var sel = global.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        return !!(doc.execCommand && doc.execCommand('copy'));
      } catch (e) { return false; }
    };
    if (nav.clipboard && nav.clipboard.writeText) {
      return nav.clipboard.writeText(text).then(function () { return true; }, bySelection);
    }
    return Promise.resolve(bySelection());
  }

  /*
   * The lines of code on a page of prose (site decisions 142, 146: `/more/`'s Definer URL and
   * CSS, `about.py` `_steps`): each gets a Copy button beside it, which says "Copied" for a few
   * seconds after a click (COPIED_MS); the line marked `data-ordpar-popup` is filled with the
   * pop-up address from the saved settings (`popupAddress`; the built page carries the plain
   * one). Made here, so a page without script has the lines alone, still selected by one click.
   */
  var COPIED_MS = 2500;

  function wireCodeLines(scope) {
    var lines = scope.querySelectorAll ? scope.querySelectorAll('.ordpar-about .ordpar-code') : [];
    Array.prototype.forEach.call(lines, function (box) {
      var code = box.querySelector('code');
      if (!code || box.querySelector('.ordpar-code-copy')) { return; }
      if (code.hasAttribute('data-ordpar-popup')) { code.textContent = popupAddress(); }
      var btn = labelled('button', 'ordpar-button is-quiet ordpar-code-copy', 'code.copy');
      btn.type = 'button';
      var timer = null;
      btn.addEventListener('click', function () {
        copyText(code.textContent, code).then(function (ok) {
          if (!ok) { return; }
          btn.setAttribute('data-ordpar-string', 'code.copied');
          btn.textContent = t('code.copied');
          if (timer) { clearTimeout(timer); }
          timer = setTimeout(function () {
            btn.setAttribute('data-ordpar-string', 'code.copy');
            btn.textContent = t('code.copy');
          }, COPIED_MS);
        });
      });
      box.appendChild(btn);
      box.classList.add('has-copy');
    });
  }

  function setSetting(key, value) {
    if (KEYS.indexOf(key) === -1) { return; }
    write(key, value);
    leaveVisit(key);
    if (key === 'theme') { applyTheme(); }
    if (key === 'colour') { applyColour(); }
    if (ARTICLE_KEYS.indexOf(key) !== -1) { applyDefs(); }   // an open article page updates in place
    if (CLASS_KEYS.indexOf(key) !== -1) { applyClassKeys(); }   // decisions 31, 78, 80, 81, 84, 86, 87, 90
    if (LAYER_KEYS.indexOf(key) !== -1) { applyLayer(); }        // site decisions 152
    if (key === 'lang') { return useLang(value).then(function () { rerender(); notify(key, value); }); }
    rerender();
    notify(key, value);
    return Promise.resolve();
  }

  /** Site decisions 152: the layer changed — every class it answers for, the search's direction
   *  (the switch hidden with the equivalents) and the icons. */
  function applyLayer() {
    if (!layer().hidden) { dirLayer = null; }
    applyDefs();
    applyClassKeys();
    applyDirection();
  }

  /**
   * A setting for this visit only (site decisions 152, the headword's icon where the header is
   * hidden): written into the visit (146's `sessionStorage`, `ordparVisit.settings`), never
   * saved, so in a pop-up it holds for that pop-up alone, as every setting the address carries.
   * Not on the settings page, which has no visit.
   */
  function visitSetting(key, value) {
    if (KEYS.indexOf(key) === -1) { return Promise.resolve(); }
    var V = global.ordparVisit;
    if (V) {
      if (!V.settings) { V.settings = {}; }
      V.settings[key] = value;
    }
    try {
      var S = global.sessionStorage, v = JSON.parse(S.getItem(VISIT_KEY));
      if (!v || typeof v !== 'object') { v = {}; }
      v[key] = value;
      S.setItem(VISIT_KEY, JSON.stringify(v));
    } catch (e) { /* storage blocked: this page alone */ }
    applyLayer();
    rerender();
    notify(key, value);
    return Promise.resolve();
  }

  function resetSettings() {
    KEYS.forEach(drop);
    leaveVisit();
    applyTheme();
    applyColour();
    applyDefs();
    applyClassKeys();
    return useLang(getSetting('lang')).then(function () { rerender(); notify('reset', null); });
  }

  /** Re-apply every stored setting at once — after an import wrote them (site decisions 60):
   *  the theme, the colour, the article classes, the participle frames, the language, the chrome. */
  function applyAll() {
    applyTheme();
    applyColour();
    applyDefs();
    applyClassKeys();
    return useLang(getSetting('lang')).then(function () { rerender(); notify('import', null); });
  }

  function deleteStoredData() {
    try { global.localStorage.clear(); } catch (e) { /* private mode */ }
    applyTheme();
    applyColour();
    applyDefs();
    applyClassKeys();
    rerender();
    notify('reset', null);
  }

  /** The settings that are a class on <html> alone, as the head script sets them: the
   *  participle frames (`ordpar-pframes-off`, decisions 31), the mini's headword
   *  (`ordpar-minihw-article`, decisions 78), the mini made from the target's page
   *  (`ordpar-minicontent-slim`, `ordpar-minispacing-compact`, `ordpar-miniscroll-off`,
   *  its text sizes `ordpar-minitext-smaller`, decisions 114,
   *  `ordpar-minifetch-click|page`, decisions 80), the formula lines (`ordpar-formulas-no|both`,
   *  decisions 81), the etymology line (`ordpar-ety-no|both`, decisions 84) and the dropdown's
   *  roomier rows (`ordpar-suggestrows-roomy`, decisions 86), the emphasized line
   *  (`ordpar-emph-no`, decisions 87), subsenses in English only (`ordpar-subsen-en`, decisions
   *  90), the layout closer to ordbokene.no (`ordpar-layout-ordbokene`, decisions 87) and the
   *  examples' English behind a reveal (`ordpar-examples-no`, decisions 111), the eye beside the
   *  headword (`ordpar-exeye-on`, decisions 131) and what it hides (`ordpar-exeye-all`,
   *  decisions 186), the CEFR level box (`ordpar-levels-on`, decisions 187) and the set phrases
   *  by level (`ordpar-phraseorder-level`, decisions 188), the examples
   *  limit per sense (`ordpar-exlimit-<n>`, `ordpar-exmore-off`, decisions 112) — then asks an
   *  article on screen to catch up (`ordparDefs`: that layout's "Example" headings, and the
   *  examples' "Show English" cues and the "Show N more examples" lines, are inserted by the
   *  page script, only once chosen). */
  function applyClassKeys() {
    var cl = doc.documentElement.classList;
    cl.toggle('ordpar-pframes-off', getSetting('pframes') === 'off');
    cl.toggle('ordpar-minihw-article', getSetting('minihw') === 'article');
    cl.toggle('ordpar-minicontent-slim', getSetting('minicontent') === 'slim');
    cl.toggle('ordpar-minispacing-compact', getSetting('minispacing') === 'compact');
    cl.toggle('ordpar-minitext-smaller', getSetting('minitext') === 'smaller');
    cl.toggle('ordpar-miniscroll-off', getSetting('miniscroll') === 'off');
    var f = getSetting('minifetch');
    cl.toggle('ordpar-minifetch-click', f === 'click');
    cl.toggle('ordpar-minifetch-page', f === 'page');
    var m = eff('formulas');
    cl.toggle('ordpar-formulas-no', m === 'no');
    cl.toggle('ordpar-formulas-both', m === 'both');
    var e = eff('ety');
    cl.toggle('ordpar-ety-no', e === 'no');
    cl.toggle('ordpar-ety-both', e === 'both');
    cl.toggle('ordpar-suggestrows-roomy', getSetting('suggestrows') === 'roomy');
    cl.toggle('ordpar-emph-no', getSetting('emph') === 'no');
    cl.toggle('ordpar-subsen-en', eff('subsenses') === 'en');
    cl.toggle('ordpar-layout-ordbokene', getSetting('layout') === 'ordbokene');
    cl.toggle('ordpar-examples-no', eff('examples') === 'no');
    // site decisions 152: the layer's own classes, as the head script sets them
    var L = layer();
    cl.toggle('ordpar-nbo', L.on);
    cl.toggle('ordpar-nbo-noeq', L.hidden);
    cl.toggle('ordpar-nbo-rows0', L.rows === 'none');
    cl.toggle('ordpar-nbo-hovnb', hoverNb());
    cl.toggle('ordpar-nbicon-off', getSetting('nbicon') === 'off');
    cl.toggle('ordpar-labels-no', getSetting('labels') === 'no');
    syncIcons();
    // decisions 131: the eye beside the headword (`ordparDefs` below inserts or removes it)
    cl.toggle('ordpar-exeye-on', getSetting('exeye') === 'on');
    // decisions 186: the eye hides all of its article's English instead of the examples'
    cl.toggle('ordpar-exeye-all', getSetting('exeyewhat') === 'all');
    // decisions 187: the CEFR level box after the headword and on each embedded set phrase
    cl.toggle('ordpar-levels-on', getSetting('levels') === 'on');
    // decisions 188: the set phrases by level (the sheet orders them only beside the class above)
    cl.toggle('ordpar-phraseorder-level', getSetting('phraseorder') === 'level');
    // decisions 112: `ordpar-exlimit-<n>` (n 1 to 10; none for All) and `ordpar-exmore-off`
    var lim = getSetting('exlimit');
    SPEC.exlimit.values.forEach(function (v) { if (v !== 'all') { cl.toggle('ordpar-exlimit-' + v, v === lim); } });
    cl.toggle('ordpar-exmore-off', getSetting('exmore') === 'off');
    if (typeof global.ordparDefs === 'function') {
      try { global.ordparDefs(); } catch (e) { /* the page's own bug */ }
    }
  }

  function notify(key, value) {
    listeners.forEach(function (fn) { try { fn(key, value); } catch (e) { /* a page's own bug */ } });
  }

  /* ----------------------------------------------------------------- theme */

  function prefersDark() {
    try { return global.matchMedia('(prefers-color-scheme: dark)').matches; } catch (e) { return false; }
  }

  function applyTheme() {
    var theme = getSetting('theme');
    var dark = theme === 'dark' || (theme === 'system' && prefersDark());
    doc.documentElement.classList.toggle('nightMode', dark);
    doc.documentElement.setAttribute('data-theme', theme);
  }

  /**
   * `defs`, `mini` and `peek` (decisions 54) govern the ARTICLE page. `defs` = en | both | no
   * (default both): the definition line pairs show the English alone, both (the Norwegian
   * first), or the Norwegian with the English behind a "Show English" cue. `mini` = article |
   * en | both (default article: English when `defs` is en, else both — a mini has no reveal,
   * Robin 2026-10-18): what a cross-reference's mini shows. `peek` = on | nb | off (default on): the hover peek — the
   * translation, the first Norwegian definition (site decisions 185) or none. The shell only stores them and
   * mirrors them as classes on <html> — `ordpar-defs-en|no`, `ordpar-mini-en` (the
   * RESOLVED mini value), `ordpar-peek-off`, `ordpar-nbo-hovnb` (`hoverNb`), exactly as the head script does — then asks an
   * article page on screen to re-place its controls (`ordparDefs`, `sitegen/page.py`
   * PAGE_JS), so it updates in place without a reload.
   */
  function applyDefs() {
    var cl = doc.documentElement.classList;
    // site decisions 152: through the layer (`eff`) while Norwegian only is on
    var defs = eff('defs');
    var mini = eff('mini');
    if (mini === 'article') { mini = defs === 'en' ? 'en' : 'both'; }   // a mini has no reveal
    cl.toggle('ordpar-defs-en', defs === 'en');
    cl.toggle('ordpar-defs-no', defs === 'no');
    cl.toggle('ordpar-mini-en', mini === 'en');
    cl.toggle('ordpar-peek-off', eff('peek') === 'off');
    cl.toggle('ordpar-nbo-hovnb', hoverNb());   // site decisions 185: `peek` = nb
    if (typeof global.ordparDefs === 'function') {
      try { global.ordparDefs(); } catch (e) { /* the page's own bug */ }
    }
  }

  /** The colour scheme (decisions 63): the stored `colour` as `data-accent` on <html>, as the
   *  head script does; the CSS (`colours.css()` in article.css) styles each scheme, so a value
   *  no scheme has is the default. */
  function applyColour() {
    var v = read('colour');   // the visit's where it has one (site decisions 146)
    if (v && COLOUR_ID.test(v)) { doc.documentElement.setAttribute('data-accent', v); }
    else { doc.documentElement.removeAttribute('data-accent'); }
  }

  try {
    var mq = global.matchMedia('(prefers-color-scheme: dark)');
    var onScheme = function () { if (getSetting('theme') === 'system') { applyTheme(); } };
    if (mq.addEventListener) { mq.addEventListener('change', onScheme); }
    else if (mq.addListener) { mq.addListener(onScheme); }
  } catch (e) { /* no matchMedia */ }

  /* --------------------------------------------------------------- strings */

  function has(key) {
    return Object.prototype.hasOwnProperty.call(strings[lang] || {}, key);
  }

  function t(key, vars) {
    var table = strings[lang] || {};
    var s = Object.prototype.hasOwnProperty.call(table, key) ? table[key] : key;
    if (vars) { for (var k in vars) { s = s.split('{' + k + '}').join(String(vars[k])); } }
    return s;
  }

  function useLang(code) {
    code = LANGS.indexOf(code) !== -1 ? code : browserLang();
    lang = code;
    shell.lang = code;
    doc.documentElement.setAttribute('lang', code === 'en' ? 'en' : code);
    if (strings[code]) { return Promise.resolve(strings[code]); }
    return fetch(base() + 'site/strings/' + code + '.json', { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; })
      .then(function (table) { strings[code] = table; return table; });
  }

  function base() { return global.ORDPAR_BASE || '/'; }

  /* ---------------------------------------------------------------- header */

  function el(tag, cls, text) {
    var node = doc.createElement(tag);
    if (cls) { node.className = cls; }
    if (text != null) { node.textContent = text; }
    return node;
  }

  /** A newline put into `parent` before `before` (or at its end) (site decisions 154): between two
   *  pieces that are separate on the page — flex items, where it draws nothing — so a text
   *  extraction does not join their words. Nothing where the document cannot make text (a test's
   *  stand-in). */
  function nl(parent, before) {
    if (!doc.createTextNode || !parent || !parent.insertBefore) { return; }
    parent.insertBefore(doc.createTextNode('\n'), before || null);
  }

  /** An element whose text is the string `key`, relabelled with the chrome. */
  function labelled(tag, cls, key) {
    var node = el(tag, cls, t(key));
    node.setAttribute('data-ordpar-string', key);
    return node;
  }

  /**
   * Enhance the static header (`sitegen/chrome.py` `header`) once: the box becomes the combobox
   * (role, aria-expanded, aria-controls, aria-autocomplete), the × button and the dropdown — the
   * listbox, with the "Recent" heading over it — go into `.ordpar-combobox`, and the search is
   * wired. Without this the header is a plain form that searches on Enter.
   */
  function enhanceHeader(header) {
    if (header._ordpar) { return; }
    var form = header.querySelector('form.ordpar-search');
    var input = header.querySelector('#ordpar-q');
    var box = input && input.parentNode;
    if (!form || !input || !box) { return; }
    header._ordpar = true;
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', 'ordpar-listbox');
    input.setAttribute('aria-autocomplete', 'list');

    var clear = el('button', 'ordpar-clear', '×');
    clear.type = 'button';
    clear.setAttribute('aria-label', t('search.clear'));
    box.appendChild(clear);

    // the dropdown: the listbox, and above it a heading shown only over the recent lookups
    // (site decisions 60) — outside the listbox, whose children are options only
    var popup = el('div', 'ordpar-popup');
    popup.hidden = true;
    var recentHead = el('div', 'ordpar-popup-head');
    recentHead.hidden = true;
    recentHead.appendChild(labelled('span', 'ordpar-popup-title', 'recent.title'));
    var historyLink = labelled('a', 'ordpar-popup-link', 'recent.all');
    historyLink.href = base() + 'history/';
    // keep the box's focus on a press, so the dropdown does not close before the click lands
    historyLink.addEventListener('mousedown', function (e) { e.preventDefault(); });
    recentHead.appendChild(historyLink);
    popup.appendChild(recentHead);
    var listbox = el('ul', 'ordpar-listbox');
    listbox.id = 'ordpar-listbox';
    listbox.setAttribute('role', 'listbox');
    listbox.setAttribute('aria-label', t('search.suggestions'));
    popup.appendChild(listbox);
    box.appendChild(popup);

    wireSearch(form, input, listbox, clear, null, popup, recentHead);
  }

  /*
   * The chrome's static elements and their string keys (`sitegen/chrome.py` `RELABEL`, the same
   * pairs; `ordpar/tests/test_ordpar_slim.py` holds the two together): the page carries the words but
   * not the keys (2026-10-20, the size report's item 6 — `data-ordpar-string` on every element
   * was 40 MB over the site), so the keys are put back here, once, on the element found by its
   * selector. A function gives the key from the page: the skip link is "Skip to the article" on
   * an article page. The About link's key is the article build's (`strings.py`): the strings
   * inlined on the shell pages are the shell's alone, so there it keeps its built words. The elements this file makes carry their key themselves (`labelled`).
   */
  var STATIC_STRINGS = [
    ['.ordpar-skip', function () {
      return doc.documentElement.hasAttribute('data-article-id') ? 'nav.skipArticle' : 'nav.skip';
    }],
    ['.ordpar-brand-name', 'site.name'],
    ['.ordpar-brand-tagline', 'site.tagline'],
    ['label[for="ordpar-q"]', 'search.label'],
    ['.ordpar-submit', 'search.submit'],
    ['.ordpar-footer-nav a[href="/"]', 'footer.home'],
    ['.ordpar-footer-nav a[href="/help/"]', 'footer.help'],
    ['.ordpar-footer-nav a[href="/more/"]', 'footer.more'],
    ['.ordpar-footer-nav a[href="/about/"]', 'about_link'],
    ['.ordpar-footer-nav a[href="/privacy/"]', 'footer.privacy']
  ];

  function keyStatic(scope) {
    STATIC_STRINGS.forEach(function (pair) {
      var node = scope.querySelector && scope.querySelector(pair[0]);
      if (node && !node.hasAttribute('data-ordpar-string')) {
        node.setAttribute('data-ordpar-string', typeof pair[1] === 'function' ? pair[1]() : pair[1]);
      }
    });
  }

  /*
   * The chrome that needs script, made here (2026-10-20, the size report's item 5; until then
   * `chrome.py` wrote it into every page, hidden without script): Random word and the links
   * Favourites and Settings in the header, after the search form (their place on screen is
   * `shell.css`'s `order`), and Settings, Favourites and History between Home and About and
   * licence in the footer (Robin, 2026-10-22: About last, in the markup) —
   * the same elements, classes and words as before. Then `ordpar-chrome` on <html>, which
   * releases the room `shell.css` held for them under `html.ordpar-js`, so nothing moves.
   */
  /** The readers' survey, "Ordpar — your first impressions" (site decisions 173: our own page in
   *  place of decisions 72's Google form, kept after launch), linked from every footer. Never set
   *  here: the build writes `chrome.SURVEY_HREF` into this line while the survey is on
   *  (`page.survey_link_js`); empty, no link. */
  var SURVEY_HREF = '';

  function addChrome() {
    var root = doc.documentElement;
    root.classList.add('ordpar-js');            // the head script's, should its file have failed
    var inner = doc.querySelector('.ordpar-header-inner');
    if (inner && !inner.querySelector('.ordpar-random')) {
      var form = inner.querySelector('form.ordpar-search');
      var random = labelled('button', 'ordpar-button is-quiet ordpar-random ordpar-needs-js', 'search.random');
      random.type = 'button';
      random.setAttribute('data-ordpar-random', '');
      var nav = el('nav', 'ordpar-header-nav ordpar-needs-js');
      nav.setAttribute('aria-label', t('nav.header'));
      var fav = labelled('a', 'ordpar-settings-button ordpar-fav-link', 'nav.favourites');
      fav.setAttribute('href', base() + 'favourites/');
      var set = labelled('a', 'ordpar-settings-button ordpar-settings-link', 'settings.open');
      set.setAttribute('href', base() + 'settings/');
      // site decisions 152: Norwegian only's icon, first beside Favourites and Settings on a
      // computer (on a phone its twin on the switch's row, `addSwitch`; shell.css shows one)
      nav.appendChild(nbIcon('nav'));
      nl(nav);
      nav.appendChild(fav);
      nl(nav);
      nav.appendChild(set);
      var after = form ? form.nextSibling : null;
      // a newline before each (site decisions 154): the header is a flex row
      nl(inner, after);
      inner.insertBefore(random, after);
      nl(inner, after);
      inner.insertBefore(nav, after);
    }
    addSwitch(inner);
    var links = doc.querySelector('.ordpar-footer-nav');
    if (links && !links.querySelector('a[href$="/history/"]')) {
      // before Help (decisions 123), else About (last); null appends
      var about = links.querySelector('a[href="/help/"]') || links.querySelector('a[href="/about/"]');
      [['settings/', 'footer.settings'], ['favourites/', 'footer.favourites'],
        ['history/', 'footer.history']].forEach(function (l) {
        var a = labelled('a', 'ordpar-needs-js', l[1]);
        a.setAttribute('href', base() + l[0]);
        links.insertBefore(a, about);
        nl(links, about);          // a flex row (site decisions 154)
      });
    }
    // decisions 68: the phone-only hint "Install Ordpar as an app", leading to Settings →
    // Offline (install.js decides where; shell.css shows it only at a phone's width and holds
    // its line until now)
    if (links && global.ordparInstall) {
      try { global.ordparInstall.hint(links); } catch (e) { /* its own bug */ }
    }
    // decisions 72 (Robin, 2026-10-21), our own survey since site decisions 173 (2026-11-07): "Tell
    // us what you think →" (`footer.feedback`) linking the survey, in the same tab (a page of the
    // site). Made here, so neither adding nor removing it changes a page. Its place: after the
    // "under development" note while the launch switch is on (the note is `chrome.footer`'s); once
    // the note is gone at launch, the link stays, in a line of its own where the note was
    // (`ordpar-feedback-line`, the smallest change of layout). None while SURVEY_HREF is empty.
    var foot = doc.querySelector('.ordpar-footer-inner');
    if (SURVEY_HREF && foot && !foot.querySelector('.ordpar-feedback')) {
      var fb = labelled('a', 'ordpar-feedback ordpar-needs-js', 'footer.feedback');
      fb.setAttribute('href', SURVEY_HREF);
      var dev = foot.querySelector('.ordpar-devnote');
      if (dev) {
        dev.appendChild(doc.createTextNode(' '));
        dev.appendChild(fb);
      } else {
        var line = el('p', 'ordpar-feedback-line');
        line.appendChild(fb);
        foot.appendChild(line);
      }
    }
    addMoreLine();
    root.classList.add('ordpar-chrome');
  }

  /* ------------------------------------- the direction switch (site decisions 148) */

  /*
   * Site decisions 148: a switch under the search box which, turned on, searches the English
   * equivalents instead of the Norwegian headwords. A switch with a label,
   * "Search English words", under the search box wherever the box is — drawn here, not written
   * into the pages (the box is in every page's HTML: a change there would rebuild every page and
   * make every offline copy download again). On a computer a row of its own under the box; on a
   * phone it shares Random word's row where it fits (shell.css `.ordpar-direction`). Switched on:
   * the box's placeholder and label "Search an English word", the box `lang="en"`, the
   * suggestions and the search English (`wireSearch`, lookup.js `renderEnglish`). It stays on
   * after an English search and is REMEMBERED (decisions 148):
   * saved on the device as the reader's own choices are (`ordparPersonal.direction`, beside the
   * settings, not a row on the Settings page), so a new visit opens in the direction last used;
   * Norwegian until the reader first switches; where storage is blocked, for the page only.
   * Switched with a word in the box, that word is searched again in the other direction.
   */
  var dirOnPage = null;                       // the direction where storage is blocked
  // site decisions 152: with Norwegian only on and the English equivalents hidden, the switch is
  // hidden and the search is Norwegian WITHOUT writing the reader's stored direction, which
  // returns when the equivalents are shown or the layer is off; a search opened in English on
  // this page (a shared `#en=` address still opens) holds here alone
  var dirLayer = null;
  function equivHidden() { return layer().hidden; }
  function direction() {
    if (equivHidden()) { return dirLayer === 'en' ? 'en' : 'nb'; }
    var P = global.ordparPersonal;
    var v = dirOnPage || (P && P.direction ? P.direction() : null);
    return v === 'en' ? 'en' : 'nb';
  }
  function englishOn() { return direction() === 'en'; }

  /** Set the direction (`'en'` or `'nb'`), saved on the device; the box, its label and the
   *  switch follow. `opts.rerun`: the switch itself was turned — a word in the box is searched
   *  again in the new direction. `opts.quiet` (a search that already runs in its direction):
   *  nothing else. */
  function setDirection(d, opts) {
    d = d === 'en' ? 'en' : 'nb';
    var was = direction();
    var P = global.ordparPersonal;
    if (equivHidden()) { dirLayer = d; }        // site decisions 152: never written while hidden
    else { dirOnPage = P && P.setDirection && P.setDirection(d) ? null : d; }
    applyDirection();
    if (was !== d) { notify('direction', d); }
    if (!(opts && opts.rerun) || was === d) { return; }
    var box = doc.getElementById('ordpar-q');
    var q = box ? box.value.trim() : '';
    if (!q) { return; }
    if (searchHandler) { searchHandler(q, d === 'en' ? { en: true } : undefined); return; }
    var L = global.ordparLookup;
    if (d === 'en') { global.location.href = L && L.englishUrl ? L.englishUrl(q) : base() + 'bm-en/#en=' + encodeURIComponent(q); }
    else if (L && L.searchAddress) { L.searchAddress(q).then(function (href) { global.location.href = href; }); }
    else { global.location.href = base() + 'bm-en/#q=' + encodeURIComponent(q); }
  }

  /** The box, its label and the switch as the direction says (`relabel` runs it last). */
  function applyDirection() {
    var en = englishOn();
    var input = doc.getElementById ? doc.getElementById('ordpar-q') : null;
    if (input) {
      input.lang = en ? 'en' : 'nb';
      var ph = en ? 'search.placeholderEn' : 'search.placeholder';
      if (has(ph)) { input.placeholder = t(ph); }
    }
    var label = doc.querySelector ? doc.querySelector('label[for="ordpar-q"]') : null;
    var lk = en ? 'search.labelEn' : 'search.label';
    if (label && has(lk)) { label.textContent = t(lk); }
    var sw = doc.getElementById ? doc.getElementById('ordpar-en-switch') : null;
    if (sw) { sw.checked = en; }
  }

  /** Draw the switch into the header's `inner`, before Random word (shell.css orders them). */
  function addSwitch(inner) {
    if (!inner || !inner.querySelector('form.ordpar-search') || inner.querySelector('.ordpar-direction')) { return; }
    var row = el('div', 'ordpar-direction ordpar-needs-js');
    var lab = el('label', 'ordpar-switch');
    var cb = el('input');
    cb.type = 'checkbox';
    cb.id = 'ordpar-en-switch';
    cb.setAttribute('role', 'switch');
    cb.checked = englishOn();
    cb.addEventListener('change', function () { setDirection(cb.checked ? 'en' : 'nb', { rerun: true }); });
    lab.appendChild(cb);
    var track = el('span', 'ordpar-switch-track');
    track.setAttribute('aria-hidden', 'true');
    track.appendChild(el('span', 'ordpar-switch-knob'));
    lab.appendChild(track);
    lab.appendChild(labelled('span', 'ordpar-switch-text', 'search.english'));
    row.appendChild(lab);
    // site decisions 152: on a phone Norwegian only's icon sits on this row (the top row has no
    // room), after the switch; it stays when the switch is hidden with the English equivalents
    row.appendChild(nbIcon('row'));
    var random = inner.querySelector('.ordpar-random');
    inner.insertBefore(row, random);
    if (random) { nl(inner, random); }   // a flex row (site decisions 154)
    applyDirection();
  }

  /*
   * Site decisions 152 (like the night/light switch some sites have in the header, and
   * remembered as that is): NORWEGIAN ONLY'S ICON in the header. It switches
   * the layer for the whole site and is remembered on the device (it is the setting `nbonly`
   * itself: the icon and Settings are one state), filled (`aria-pressed`) while on. Two copies,
   * one per place — beside Favourites and Settings on a computer, on the switch's row on a phone
   * (shell.css shows the one for the width); none while the setting `nbicon` is off (the sheet,
   * `ordpar-nbicon-off`). The look: the lab's "a", two speech bubbles, round as the eye.
   */
  var NB_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h11a2 2 0 0 1 2 2v6a2 2 0 0 1-2 ' +
    '2H9l-4 3.5V15H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/><path d="M17.5 9H20a2 2 0 0 1 2 2v5a2 2 0 0 ' +
    '1-2 2h-1v3l-3.2-3H12" opacity=".55"/></svg>';
  function nbIcon(where) {
    var w = el('span', 'ordpar-nbo-icon ordpar-nbo-' + where + ' ordpar-needs-js');
    var b = el('button', 'ordpar-nbo-btn');
    b.type = 'button';
    b.innerHTML = '<span aria-hidden="true">' + NB_ICON + '</span>';
    b.addEventListener('click', function () {
      setSetting('nbonly', getSetting('nbonly') === 'on' ? 'off' : 'on');
    });
    w.appendChild(b);
    syncIcon(b);
    return w;
  }
  function syncIcon(b) {
    var on = getSetting('nbonly') === 'on';
    var label = t(on ? 'nbo.iconOn' : 'nbo.iconOff');
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.setAttribute('aria-label', label);
    b.title = label;
  }
  function syncIcons() {
    if (!doc.querySelectorAll) { return; }
    Array.prototype.forEach.call(doc.querySelectorAll('.ordpar-nbo-btn,.ordpar-nbhw-btn'), syncIcon);
  }

  /*
   * Site decisions 142 (Robin, 2026-10-27, from the home page lab): on the home page, a line to
   * "More ways to use Ordpar" (`/more/`) under Random word, at the top of the main area, the link
   * on its last words only. `shell.css` shows it only while nothing is searched: lookup.js
   * `render` puts `ordpar-idle` on the main while it shows no search (an empty query), and
   * `searching` and every other answer take it off, so a search or Random word hides it. Made
   * here, as the rest of the chrome that needs script; without script the footer's link stays.
   */
  function addMoreLine() {
    var main = doc.getElementById ? doc.getElementById('ordpar-main') : null;
    var results = main && main.querySelector ? main.querySelector('[data-ordpar-results]') : null;
    if (!results || !global.location || global.location.pathname !== base() ||
        main.querySelector('.ordpar-more-line')) {
      return;
    }
    var parts = t('home.more').split('{link}');
    var line = el('p', 'ordpar-more-line');
    var link = labelled('a', '', 'home.moreLink');
    link.setAttribute('href', base() + 'more/');
    line.appendChild(doc.createTextNode(parts[0]));
    line.appendChild(link);
    if (parts.length > 1 && parts[1]) { line.appendChild(doc.createTextNode(parts[1])); }
    main.insertBefore(line, results);
  }

  /** The chrome's words from the strings in force: every `data-ordpar-string` element, the box's
   *  placeholder, the × button's name. Only a key the strings have: a page whose strings did
   *  not load keeps the words it was built with. */
  function relabel(scope) {
    keyStatic(scope);
    var nodes = scope.querySelectorAll('[data-ordpar-string]');
    Array.prototype.forEach.call(nodes, function (node) {
      var key = node.getAttribute('data-ordpar-string');
      if (has(key)) { node.textContent = t(key); }
    });
    var input = scope.querySelector && scope.querySelector('#ordpar-q');
    if (input && has('search.placeholder')) { input.placeholder = t('search.placeholder'); }
    var clear = scope.querySelector && scope.querySelector('.ordpar-clear');
    if (clear && has('search.clear')) { clear.setAttribute('aria-label', t('search.clear')); }
    applyDirection();          // site decisions 148: the box's words in the switch's direction
  }

  function markCurrent(scope) {
    var links = scope.querySelectorAll('.ordpar-header a[href], .ordpar-footer a[href]');
    Array.prototype.forEach.call(links, function (a) {
      var here = a.pathname === global.location.pathname && a.host === global.location.host;
      if (here) {
        a.setAttribute('aria-current', 'page');
        if (has('nav.current')) { a.title = t('nav.current'); }
      } else { a.removeAttribute('aria-current'); }
    });
  }

  /* -------------------------------------------------------------- combobox */

  /** The homograph numeral, as the article page prints it (lookup.js `roman`). */
  var ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];

  /**
   * A history entry drawn as a suggestion row (brief 60b item 3) — the dropdown's "Recent" and
   * the /history/ page share it: the query (Norwegian), and for a search that found one article
   * its word class faded italic (none for a set phrase, as the suggestions). On the right (site
   * decisions 88, amending 60b's "Norwegian only" and "N articles"): for one
   * translated article its gloss (`text`, stored with the entry, by the dropdown's rule); for
   * one untranslated article its Norwegian definition; for several, their homograph-numbered
   * glosses as in the suggestions, an untranslated article listed too, with its Norwegian
   * definition — the articles whose own headword the search matched, not those it reached as
   * an inflected form (88 as amended, Robin 2026-10-22) — `searchRowSide` paints the side at
   * once, held (`is-pending`), and `fillSearchRow` fills it from the dictionary.
   */
  function searchRowMain(e, tag) {
    var main = el('span', 'ordpar-option-main');
    var word = el(tag || 'span', 'ordpar-option-word', e.q);
    word.lang = 'nb';
    main.appendChild(word);
    var pos = e.n === 1 ? posSpan(e.pos) : null;
    if (pos) { main.appendChild(pos); }
    return main;
  }

  /* ------------------------------------------- the English rows (site decisions 148) */

  /**
   * One English word as a compact row (site decisions 148 item 4, Robin 2026-10-29, as picked in
   * the lab) — the suggestions, Recent, History and the similar English words after a miss, one
   * style: the English word on the left (`lang="en"`), semibold in the text colour; on the right
   * its Norwegian headwords, semibold in the accent, the top ranked first (order (c)), each IN
   * ITS FIRST SPELLING ALONE with that spelling's numeral ("enough to show the Norwegian
   * main-lemma"), each with its word class while every one fits; where they do not, the word
   * classes go first, then the list is cut with "+ N more" (`fitGlosses`). One headword: drawn
   * as a one-article row, the headword and its word class. `item` {key, word, arts: [lookup.js
   * `enArticle`]}; `rowClass` the row's own class (`ordpar-option`, History's
   * `ordpar-history-link`). The element carries `ordparFit(before)`, to run once it is laid out:
   * `before` (the dropdown's `fitRow`) first, then the list's fit.
   */
  function englishRow(tag, item, cls, rowClass) {
    var row = el(tag, (rowClass || 'ordpar-option') + ' ordpar-option-en' + (cls ? ' ' + cls : ''));
    var main = el('span', 'ordpar-option-main');
    var word = el('span', 'ordpar-option-word', item.word);
    word.lang = 'en';
    main.appendChild(word);
    row.appendChild(main);
    nl(row);                      // a flex row (site decisions 154)
    englishSide(row, row.appendChild(el('span', 'ordpar-option-side')), (item && item.arts) || []);
    return row;
  }

  /** A Norwegian headword of an English row: its first spelling, then that spelling's numeral
   *  (the article's look, decisions 93) where `numbered`, in `ordpar-en-nb` (semibold, the accent). */
  function nbFirst(node, a, numbered) {
    var w = el('span', 'ordpar-en-nb');
    w.lang = 'nb';
    w.appendChild(doc.createTextNode(firstOf(a)));
    if (numbered && a.firstHg) {
      w.appendChild(doc.createTextNode(' '));
      var mark = el('span', 'ordbok-homograph ordpar-hg', ROMAN[a.firstHg] || String(a.firstHg));
      mark.setAttribute('aria-hidden', 'true');
      w.appendChild(mark);
      // the screen readers' label made with `data-nosnippet` (site decisions 154: Google's
      // snippets read "homograph 3"; it reads the attribute only on an element that has it when
      // first put into the page)
      var said = el('span', 'ordpar-visually-hidden', t('results.homograph', { n: a.firstHg }));
      said.setAttribute('data-nosnippet', '');
      w.appendChild(said);
    }
    node.appendChild(w);
  }

  function firstOf(a) { return a.first || String(a.word || '').split(' / ')[0]; }

  /** The first spellings an English row would draw twice or more: only those take a numeral
   *  (decisions 148: shown where the row or page shows several words of the same form, as
   *  "light" is an equivalent of both lys I and lys II), as the "N articles" rows number
   *  the homographs of one form; a word alone in its row has none (decisions 93's follow-up). */
  function sharedForms(arts) {
    var n = Object.create(null), out = Object.create(null);
    arts.forEach(function (a) { var f = firstOf(a); n[f] = (n[f] || 0) + 1; if (n[f] > 1) { out[f] = true; } });
    return out;
  }

  /** A word class's words (`pos.<code>`), '' for none — in Norwegian (`pos.nb.<code>`) while the
   *  layer or the labels setting puts the word class in Norwegian (site decisions 152, `nbWords`;
   *  the rows are drawn by script, so each is drawn in the language in force) */
  function posWords(pos) {
    if (!pos) { return ''; }
    var key = (nbWords() && has('pos.nb.' + pos) ? 'pos.nb.' : 'pos.') + pos;
    var label = t(key);
    return label && label !== key ? label : '';
  }
  /** The word class as a row's span (`ordpar-pos`), its `lang` the words' own; null for none. */
  function posSpan(pos) {
    var label = posWords(pos);
    if (!label) { return null; }
    var span = el('span', 'ordpar-pos', label);
    span.lang = nbWords() && has('pos.nb.' + pos) ? 'nb' : 'en';
    return span;
  }

  /** Draw an English row's right-hand side for `arts` and give `row` its `ordparFit`. */
  function englishSide(row, side, arts) {
    side.textContent = '';
    var g = null, shared = sharedForms(arts);
    if (arts.length === 1) {
      var one = el('span', 'ordpar-option-gloss ordpar-option-nbword');
      one.lang = 'nb';
      nbFirst(one, arts[0], false);
      side.appendChild(one);
      var pl = posSpan(arts[0].pos);
      if (pl) { nl(side); side.appendChild(pl); }
    } else if (arts.length) {
      var list = el('span', 'ordpar-option-glosses ordpar-option-nblist');
      list.lang = 'nb';
      side.appendChild(list);
      side.appendChild(el('span', 'ordpar-option-count ordpar-option-more'));
      g = { list: list, side: side, n: arts.length };
      // Decisions 148 (the word class for svømme and bad as well, where there is room):
      // each headword with its word class while every one fits; cut, they go first
      g.fill = function (withPos) {
        list.textContent = '';
        list.removeAttribute('data-cut');
        arts.forEach(function (a, i) {
          var one = el('span', 'ordpar-option-gl');
          if (i) { one.appendChild(el('span', 'ordpar-gsep', ' \u00b7 ')); }
          nbFirst(one, a, !!shared[firstOf(a)]);
          var p = withPos && posSpan(a.pos);
          if (p) { one.appendChild(doc.createTextNode(' ')); one.appendChild(p); }
          list.appendChild(one);
        });
      };
      g.fill(true);
    }
    row.ordparFit = function (before) {
      if (before) { before(); }
      if (!g) { return; }
      g.fill(true);
      fitGlosses(g, arts.length);
      if (g.list.hasAttribute('data-cut')) { g.fill(false); fitGlosses(g, arts.length); }
    };
  }

  /**
   * An English search from the history as a row (site decisions 148 item 9): drawn unmarked, in
   * the English manner — the query on the left, the Norwegian headwords its search finds NOW on
   * the right (`englishLookup`, the query's own English file), as the suggestion row draws them;
   * held until they come; "N articles" where the search no longer answers. `refit` (the
   * dropdown's row fit) runs before the list is fitted. -> the row.
   */
  function englishEntryRow(tag, e, cls, rowClass, refit) {
    var row = englishRow(tag, { key: e.q, word: e.q, arts: [] }, cls, rowClass);
    var side = row.querySelector('.ordpar-option-side');
    var held = el('span', 'ordpar-option-glosses is-pending', '\u00a0');
    side.appendChild(held);
    var L = global.ordparLookup;
    if (!L || !L.englishLookup) { countSide(side, e.n); return row; }
    L.englishLookup(e.q).then(function (res) {
      if (!res || !res.count) { countSide(side, e.n); return; }
      englishSide(row, side, res.matches.map(function (m) { return m.article; }));
      row.ordparFit(refit);
    }, function () { countSide(side, e.n); });
    return row;
  }

  /** The plain count in place of an English row's headwords ("3 articles", "1 article"). */
  function countSide(side, n) {
    side.textContent = '';
    side.appendChild(el('span', 'ordpar-option-count',
      n === 1 ? t('results.countOne') : t('results.count', { n: n || 0 })));
  }

  /*
   * Decisions 88: the right-hand side is drawn from the dictionary when the row is shown, not
   * from text stored with the entry — the entry keeps only the query and the count for several
   * articles, and no id for one, so the search is run again (`ordparLookup.lookup`, its shard
   * and `translated.json`) and the headword hits' `snip/` file read, as the list view reads it
   * (the query's key; the inflected-form rows are not drawn, 88 as amended). That also
   * draws the entries stored before decisions 82's change to the empty override (a translated article with an
   * empty `text`), and a row follows the dictionary as it is now (an article translated since).
   * Nothing is fetched for one translated article with its text stored. The installed copy
   * answers the same files offline; where nothing answers, the row is drawn from the entry as
   * before ("Norwegian only", "N articles").
   */
  // site decisions 152: under Norwegian only's rows on "Norwegian definition" every row is drawn
  // from the dictionary (an entry's stored text is its English)
  function needsFill(e) { return e.n > 1 || !e.translated || !e.text || nbRows(); }
  /** The rows show the first Norwegian definition (site decisions 152: Norwegian only on, the
   *  English equivalents hidden, the rows on "Norwegian definition"); their `snip/` files are then
   *  read through `ordparLookup.rowView`. */
  function nbRows() {
    var L = global.ordparLookup;                 // one reading of the layer: lookup.js `nbRows`
    return !!(L && L.nbRows && L.nbRows());
  }
  function rowView(snips) {
    var L = global.ordparLookup;
    return L && L.rowView ? L.rowView(snips) : snips;
  }
  /** A row text's language: a translated article's is English, unless the rows show Norwegian. */
  function rowLang(translated) { return translated && !nbRows() ? 'en' : 'nb'; }

  function searchRowSide(e) {
    var side = el('span', 'ordpar-option-side');
    var lookup = global.ordparLookup;
    if (lookup && lookup.lookup && lookup.loadSnippets && needsFill(e)) {
      // held until `fillSearchRow` fills it, as a suggestion's gloss is (`optionSide`)
      var held = el('span', (e.n > 1 ? 'ordpar-option-glosses' : 'ordpar-option-gloss') + ' is-pending',
        '\u00a0');
      held.lang = (e.n > 1 || e.translated) && !nbRows() ? 'en' : 'nb';
      side.appendChild(held);
      return side;
    }
    plainSide(side, e);
    // one translated article drawn from its stored text: shown at once, as before, and marked
    // a summary gloss once its file says so (site decisions 116; `fillSearchRow`)
    var stored = lookup && lookup.lookup && lookup.loadSnippets && side.querySelector('.ordpar-option-gloss');
    if (stored) { stored.classList.add('is-check'); }
    return side;
  }

  /** The side as stored (brief 60b): the gloss, "Norwegian only", or "N articles" (`n`). */
  function plainSide(side, e, n) {
    if (e.n > 1) {
      side.appendChild(el('span', 'ordpar-option-count', t('results.count', { n: n || e.n })));
    } else if (e.translated) {
      if (e.text) {
        var gloss = el('span', 'ordpar-option-gloss', e.text);
        gloss.lang = 'en';
        side.appendChild(gloss);
      }
    } else {
      side.appendChild(el('span', 'ordpar-tag', t('tag.norwegianOnly')));
    }
    return side;
  }

  /**
   * The articles a history entry's search finds now as headwords, in the results' order
   * (lookup.js `render`): the headword hits, translated first across their groups, each article
   * once. The inflected-form rows are not listed (site decisions 88 as amended: the
   * inflected-form results dropped from the history page; an article
   * opened from one is an entry of its own, lookup.js `recordOpened`). -> a promise of null (no
   * answer, no headword hit) or {n, list: [{id, hg, translated, head, text, lang}]}: `head` the
   * article's headword as the index has it, `text` the gloss by the dropdown's rule
   * (`glossText`) for a translated article, the snippet line — its Norwegian definition, as the
   * list view shows it — for an untranslated one, '' where its file has neither.
   */
  function historyArticles(q) {
    var L = global.ordparLookup;
    return Promise.resolve(L.lookup(q)).then(function (res) {
      if (!res || !res.count) { return null; }
      var seen = Object.create(null), arts = [];
      var heads = [];
      res.heads.forEach(function (grp) { heads = heads.concat(grp.articles); });
      heads.filter(function (a) { return a.translated; })
        .concat(heads.filter(function (a) { return !a.translated; }))
        .forEach(function (a) { if (!seen[a.id]) { seen[a.id] = 1; arts.push(a); } });
      if (!arts.length) { return null; }
      return Promise.resolve(L.loadSnippets(L.snipKey(L.fold(res.query)))).then(function (snips) {
        snips = rowView(snips || {});                    // site decisions 152
        return { n: arts.length, list: arts.map(function (a) {
          var id = String(a.id);
          var text = a.translated ? glossText(snips, id) : (snips[id] || '');
          return { id: a.id, hg: a.hg || 0, translated: !!a.translated, head: a.word || '',
            text: text, lang: rowLang(a.translated),
            gloss: !!a.translated && glossIs(snips, id) };
        }) };
      });
    }).catch(function () { return null; });
  }

  /**
   * `historyArticles`'s answer for a similar headword's row after a miss (site decisions 144),
   * with no shard: the articles the form `q` heads, in the results' order, from its own `snip/`
   * file's `"_h"` (build_index.py `snippet_files`: a lone id, or [[id, hg], …]) and
   * `translated.json` (loaded by the search that missed). -> a promise of null (the file names
   * no article for `q`: none of them has a snippet) or {n, list}, as `historyArticles`.
   */
  function similarArticles(q) {
    var L = global.ordparLookup;
    return Promise.all([L.loadSnippets(L.snipKey(L.fold(q))), L.loadTranslated()]).then(function (r) {
      var snips = rowView(r[0] || {}), tr = r[1];        // site decisions 152: `rowView`
      var h = snips._h && Object.prototype.hasOwnProperty.call(snips._h, q) ? snips._h[q] : null;
      if (h == null) { return null; }
      var pairs = typeof h === 'number' ? [[h, 0]] : h;
      return { n: pairs.length, list: pairs.map(function (p) {
        var id = String(p[0]), on = !!(tr && tr.has(p[0]));
        return { id: p[0], hg: p[1] || 0, translated: on, head: q,
          text: on ? glossText(snips, id) : (snips[id] || ''), lang: rowLang(on),
          gloss: on && glossIs(snips, id) };
      }) };
    }).catch(function () { return null; });
  }

  /** One article's entry: the one article found, else the one the entry names (its word and
   *  homograph; by its word alone where the stored number no longer matches — an entry stored
   *  before decisions 93 has its article's first number, not the matched spelling's), else
   *  none. */
  function entryArticle(got, e) {
    if (!got) { return null; }
    if (got.list.length === 1) { return got.list[0]; }
    var byWord = [];
    for (var i = 0; i < got.list.length; i++) {
      var a = got.list[i];
      if (a.head !== e.word) { continue; }
      if (a.hg === (e.hg || 0)) { return a; }
      byWord.push(a);
    }
    return byWord.length === 1 ? byWord[0] : null;
  }

  /**
   * What a row lists for several articles — ONE rule for the suggestions (`glossList`), History
   * and Recent (`fillSearchRow`) and the similar rows after a miss (site decisions 144), a pure
   * function. `arts` [{hg, translated, text, gloss}] in the order given (the results' order),
   * `text` a translated article's gloss by the dropdown's rule (`glossText`), an untranslated
   * one's Norwegian definition (its `snip/` line), '' for none. -> [{hg, text, gloss, lang}]:
   * - some article translated: the TRANSLATED ones with a text, each with the homograph number
   *   of the spelling the row stands for (decisions 93) — an untranslated article is not listed
   *   but counted in "+ N more" (82: "It goes under '+ N more'"), as is a translated one with
   *   no text; English and Norwegian never in one row (144: "I do not want one row to mix
   *   English and Norwegian");
   * - none translated (site decisions 144: for a headword whose homographs are all
   *   Norwegian only, their definition lines are shown): each homograph's
   *   number and its first Norwegian definition line, `lang` 'nb', in place of "N articles";
   * - empty where there is none to list (the row then reads "N articles").
   */
  function sideGlosses(arts) {
    // site decisions 152: rows of Norwegian definitions list every article as an untranslated
    // one's (each homograph's number and its Norwegian line), never English
    if (nbRows()) { arts = (arts || []).map(function (a) { return { hg: a.hg, translated: false, text: a.text }; }); }
    var en = (arts || []).filter(function (a) { return a.translated && a.text; })
      .map(function (a) { return { hg: a.hg || 0, text: a.text, gloss: !!a.gloss, lang: 'en' }; });
    if (en.length || (arts || []).some(function (a) { return a.translated; })) { return en; }
    return (arts || []).filter(function (a) { return a.text; })
      .map(function (a) { return { hg: a.hg || 0, text: a.text, gloss: false, lang: 'nb' }; });
  }

  /**
   * The numbered glosses a suggestion row lists for several articles (site decisions 82, and
   * since 88's second amendment the history rows too, Robin 2026-10-22: one style everywhere),
   * by `sideGlosses`'s rule: `articles` [{id, hg, translated}], their texts read from `snips`
   * (a translated article's by `glossText`, an untranslated one's its whole Norwegian line).
   * -> `sideGlosses`'s list; `gloss` true where the text is a summary gloss (`glossIs`).
   */
  function listedGlosses(articles, snips) {
    return sideGlosses(articles.map(function (a) {
      var id = String(a.id);
      var text = !snips ? '' : a.translated ? glossText(snips, id) : (snips[id] || '');
      return { hg: a.hg || 0, translated: !!a.translated, text: text,
               gloss: !!a.translated && !!text && glossIs(snips, id) };
    }));
  }

  /* A history row's headword colour (decisions 86's D2, 88's second amendment): the accent where
   * a translated article is behind the row, else the text colour — as a suggestion row
   * (`is-translated`, shell.css). `row` the element holding the side (the history page's link,
   * the Recent row's option). */
  function markTranslated(row, on) {
    if (row && row.classList) {
      if (on) { row.classList.add('is-translated'); } else { row.classList.remove('is-translated'); }
    }
  }

  /* One translated article's stored text (`searchRowSide`, `is-check`): left as stored, but
   * written as a summary gloss — semibold, its separators faded — where the article the search
   * finds now has that same text as its summary gloss (site decisions 116); an English
   * definition line, a text that has changed since, or no answer (offline without the copy)
   * stays as it is. -> a promise. */
  function checkStored(side, e, refit) {
    var span = side && side.querySelector('.is-check');
    if (!span) { return Promise.resolve(); }
    span.classList.remove('is-check');
    return historyArticles(e.q).then(function (got) {
      var one = entryArticle(got, e);
      if (one && one.gloss && one.text === e.text) {
        writeGloss(span, one.text, true);
        (refit || function () {})();
      }
    });
  }

  /**
   * Fill a history row's held side (`searchRowSide`) from the dictionary — drawn as the
   * suggestion row for the same word is (site decisions 88 as amended again:
   * the suggestions' "+ N more" convention, not English and Norwegian mixed; 82, 86's D2),
   * without the section label. Several articles: the translated ones by their numbered glosses
   * (`listedGlosses`'s rule, `paintGlossList`), in the results' order, as many as fit, then
   * "+ N more", which counts the untranslated and any without a gloss; none to list (all
   * untranslated): "N articles". One article: its gloss, or its Norwegian definition; with
   * neither, "Norwegian only" (untranslated) or nothing (translated) — an entry for several
   * whose search now finds one is drawn as one. The headword in the accent only where a
   * translated article is behind the row (`markTranslated`). `refit` (optional) runs once the
   * side is drawn and before the list is cut — the dropdown's row fit. Since site decisions 144
   * the list for several is `sideGlosses`'s (with none translated, each homograph's Norwegian
   * definition), and `source` (optional, a function of the query -> a promise of
   * `historyArticles`'s answer) names where the articles come from: the similar rows after a
   * miss pass `similarArticles`, which needs no shard. -> a promise.
   */
  function fillSearchRow(side, e, refit, source) {
    var held = side && side.querySelector('.is-pending');
    if (!held) { return checkStored(side, e, refit); }
    var again = refit || function () {};
    return (source || historyArticles)(e.q).then(function (got) {
      if (got) {
        markTranslated(side.parentNode, got.list.some(function (a) { return a.translated; }));
      }
      if (e.n > 1 && (!got || got.n > 1)) {
        var shown = got ? sideGlosses(got.list) : [];
        if (!shown.length) {
          side.textContent = '';
          plainSide(side, e, got ? got.n : e.n);
          again();
          return;
        }
        var g = { list: held, side: side, n: got.n };
        paintGlossList(g, shown);
        again();
        fitGlosses(g, shown.length);
        return;
      }
      if (e.n > 1) {                          // several stored, one found now: drawn as one
        var only = got.list[0];
        held.className = 'ordpar-option-gloss is-pending';
        e = { q: e.q, n: 1, t: e.t, word: only.head, hg: only.hg, translated: only.translated,
          text: '' };
      }
      var one = entryArticle(got, e);
      if (one && one.text) {
        writeGloss(held, one.text, one.gloss);     // site decisions 116
        held.lang = one.lang;
        held.classList.remove('is-pending');
      } else {
        side.textContent = '';
        plainSide(side, e);
      }
      again();
    });
  }

  /* A translated set phrase with no summary gloss: its set-phrase box (build_index.py
   * `snippet_files` "_d"); every other article, and such a set phrase with no box ("_d" ''),
   * the snippet's first unit, its English line (brief 60 item 7(b) as amended, Robin
   * 2026-10-19; its "else nothing" amended by site decisions 82, Robin
   * 2026-10-21). '' only where the article has no snippet either (the span then goes). */
  function glossText(snips, id) {
    var drop = snips._d && Object.prototype.hasOwnProperty.call(snips._d, id) ? snips._d[id] : null;
    return drop ? drop : (snips[id] ? snips[id].split(' \u00b7 ')[0] : '');
  }

  /* Whether `glossText` is a SUMMARY GLOSS (site decisions 116, Robin 2026-10-24: only the
   * summary glosses semibold; an English definition line and a set-phrase box stay regular):
   * no set-phrase box in its place, and the file's `"_g"` names it (lookup.js `isGloss`). */
  function glossIs(snips, id) {
    var L = global.ordparLookup;
    var drop = snips._d && Object.prototype.hasOwnProperty.call(snips._d, id) ? snips._d[id] : null;
    return !drop && !!(L && L.isGloss && L.isGloss(snips, id));
  }

  /* A row's gloss text into `node`, a summary gloss semibold (lookup.js `writeGloss`). */
  function writeGloss(node, text, gloss) {
    var L = global.ordparLookup;
    if (L && L.writeGloss) { L.writeGloss(node, text, gloss); } else { node.textContent = text; }
  }

  /**
   * Draw a gloss list into `g.list` (decisions 82; the history rows' too, decisions 88): each
   * of `shown` its homograph numeral and its text — "I it · II that · III the" — a Norwegian
   * text in `lang="nb"`; then the "+ N more" holder, filled by `fitGlosses`.
   */
  function paintGlossList(g, shown) {
    g.list.textContent = '';
    // site decisions 144: a list of Norwegian definitions is Norwegian as a whole
    var nb = shown.length && shown.every(function (s) { return s.lang === 'nb'; });
    if (nb) { g.list.lang = 'nb'; g.list.classList.add('ordpar-option-nblist'); }
    shown.forEach(function (s, i) {
      var one = el('span', 'ordpar-option-gl' + (s.gloss ? ' ordpar-sgloss' : ''));
      if (s.lang && s.lang !== 'en' && !nb) { one.lang = s.lang; }
      // the separator faded, in the weight of the gloss it opens (site decisions 116)
      if (i) { one.appendChild(el('span', 'ordpar-gsep', ' \u00b7 ')); }
      if (s.hg) {
        var mark = el('span', 'ordbok-homograph ordpar-hg', ROMAN[s.hg] || String(s.hg));   // the article's look (93 (1))
        mark.setAttribute('aria-hidden', 'true');
        one.appendChild(mark);
        var said = el('span', 'ordpar-visually-hidden', t('results.homograph', { n: s.hg }));
        said.setAttribute('data-nosnippet', '');   // site decisions 154, at the making
        one.appendChild(said);
        one.appendChild(doc.createTextNode(' '));
      }
      one.appendChild(doc.createTextNode(s.text));
      g.list.appendChild(one);
    });
    g.list.classList.remove('is-pending');
    var more = el('span', 'ordpar-option-count ordpar-option-more');
    g.side.appendChild(more);
  }

  /* Drop glosses from the end until the list fits its row (the word on the left keeps its
   * width), at least one kept (then cut with an ellipsis); the rest go into "+ N more". */
  function fitGlosses(g, listed) {
    var more = g.side.querySelector('.ordpar-option-more');
    var items = g.list.querySelectorAll('.ordpar-option-gl');
    var kept = items.length;
    var label = function () {
      var rest = g.n - kept;
      more.textContent = rest > 0 ? t('suggest.more', { n: rest }) : '';
      more.hidden = rest <= 0;
    };
    label();
    if (!g.list.clientWidth) { return; }      // not laid out (the popup closed): as listed
    while (kept > 1 && g.list.scrollWidth > g.list.clientWidth + 1) {
      g.list.removeChild(items[--kept]);
      label();
    }
    if (kept < listed) { g.list.setAttribute('data-cut', String(listed - kept)); }
  }

  /* The plain "N articles" in place of a gloss list with nothing to list. Once only: `glossList`
   * calls it when the snippets name no gloss, and `fillGlosses` again for a list still pending
   * once every file has answered — which the replaced list still was (decisions 92 G: "hu"
   * threw a `replaceChild` error; the double call dates from 82, 510fdbd43). */
  function countOnly(g) {
    if (!g.list || g.list.parentNode !== g.side) { return; }
    var count = el('span', 'ordpar-option-count', t('results.count', { n: g.n }));
    g.side.replaceChild(count, g.list);
    g.list.classList.remove('is-pending');
  }

  function wireSearch(form, input, listbox, clear, carried, popup, recentHead) {
    var options = [];
    var active = -1;
    var lookup = global.ordparLookup;
    var seq = 0;

    var q = carried != null ? carried
      : ((global.ordparSearch && global.ordparSearch.queryFromLocation)
        ? global.ordparSearch.queryFromLocation() : '');
    if (q) { input.value = q; }

    function close() {
      popup.hidden = true;
      recentHead.hidden = true;
      listbox.setAttribute('aria-label', t('search.suggestions'));
      listbox.textContent = '';
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      options = [];
      active = -1;
      aheadSelect(null);
    }

    /* Site decisions 180: a row selected by the keyboard loads its search ahead once the
     * selection has stayed on it for ahead.js's REST_MS (`ordparAhead.select`; null cancels). */
    function aheadSelect(row) {
      var A = global.ordparAhead;
      if (A && A.select) { A.select(row || null); }
    }

    /* The option rows, in order: the listbox's own rows and, since decisions 86, those inside
     * its "Norwegian only" group — never the label or the rules, which are not options. */
    function optionRows() { return listbox.querySelectorAll('.ordpar-option'); }

    function choose(i) {
      active = i;
      var rows = optionRows();
      Array.prototype.forEach.call(rows, function (li, n) {
        li.setAttribute('aria-selected', n === i ? 'true' : 'false');
        li.classList.toggle('is-active', n === i);
      });
      if (i >= 0 && rows[i]) {
        input.setAttribute('aria-activedescendant', rows[i].id);
        // the list scrolls (decisions 22 reversed): the chosen row is brought into view, and
        // the first row of the "Norwegian only" group its label with it
        var sub = rows[i].parentNode;
        var head = !rows[i].previousElementSibling && sub !== listbox && sub.parentNode
          ? sub.parentNode.querySelector('.ordpar-option-label') : null;
        if (head && head.scrollIntoView) { head.scrollIntoView({ block: 'nearest' }); }
        if (rows[i].scrollIntoView) { rows[i].scrollIntoView({ block: 'nearest' }); }
      } else { input.removeAttribute('aria-activedescendant'); }
      aheadSelect(i >= 0 ? rows[i] : null);
    }

    /*
     * The suggestions (site decisions 86, Robin 2026-10-22: the style lab's frame D2-136L; 22
     * reversed the same day: all 20 rows, the list scrolling, as ordbokene's). The rows in
     * `lookup.suggestSections`'s order — the ranked order, but after a trailing space the set
     * phrases grouped translated first — and its section, the *Norwegian only* headwords, drawn
     * as a `role="group"` named by its label: a thin rule above it (not where it would open the
     * list), the label box "Norwegian only" (the tag's grey look at the gloss's size, shell.css
     * `--ordpar-gloss-size`), its rows, then a thin rule where rows follow. A translated row's
     * word is in the accent (as the history's rows), an untranslated row's in the text colour —
     * an "N articles" row whose articles are all untranslated too. A one-article row in the
     * section shows its Norwegian definition on the right instead of the tag (`optionSide`); an
     * untranslated row outside it (the exact match, a set phrase) keeps the tag.
     */
    var ranked = [];                          // the last suggestions in full, for a refit
    function open(items) {
      listbox.textContent = '';
      ranked = items;
      var sec = lookup && lookup.suggestSections ? lookup.suggestSections(items, input.value)
        : { rows: items, start: -1, end: -1 };
      items = sec.rows;
      options = items;
      active = -1;
      recentHead.hidden = true;
      listbox.setAttribute('aria-label', t('search.suggestions'));
      var host = listbox;
      items.forEach(function (item, i) {
        if (i === sec.start) {
          var group = el('li', 'ordpar-option-section');
          group.setAttribute('role', 'group');
          group.setAttribute('aria-labelledby', 'ordpar-option-nbhead');
          if (i > 0) {
            var above = el('div', 'ordpar-option-sep');
            above.setAttribute('aria-hidden', 'true');
            group.appendChild(above);
          }
          var head = el('div', 'ordpar-option-label');
          head.id = 'ordpar-option-nbhead';
          head.setAttribute('aria-hidden', 'true');   // read as the group's name, not twice
          head.appendChild(el('span', 'ordpar-tag', t('tag.norwegianOnly')));
          group.appendChild(head);
          host = el('ul', 'ordpar-option-sublist');
          host.setAttribute('role', 'none');
          group.appendChild(host);
          listbox.appendChild(group);
        } else if (i === sec.end) {
          host = listbox;
          var after = el('li', 'ordpar-option-sep');
          after.setAttribute('role', 'none');
          listbox.appendChild(after);
        }
        var li = el('li', 'ordpar-option ' + (item.translated ? 'is-translated' : 'is-nb'));
        li.id = 'ordpar-option-' + i;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', 'false');
        var word = el('span', 'ordpar-option-word', item.line ? '' : item.word);
        word.lang = 'nb';
        if (item.line) { drawLine(word, item.line); }
        // the word class beside the word, faded italic as in the result rows (one article
        // only; none for a set phrase, decisions 22) — Robin's amendment to item 11
        var main = el('span', 'ordpar-option-main');
        main.appendChild(word);
        var pos = (item.ids || []).length === 1 ? posSpan(item.pos) : null;
        if (pos) { main.appendChild(pos); }
        li.appendChild(main);
        li.appendChild(optionSide(item, glosses, li, i >= sec.start && i < sec.end));
        // site decisions 180: its search, for ahead.js (`aim`): what `submit` is handed
        li.setAttribute('data-q', pickWord(item));
        li.addEventListener('mousedown', function (e) { e.preventDefault(); picked(i); submit(pickWord(item), false); });
        host.appendChild(li);
      });
      popup.hidden = items.length === 0;
      input.setAttribute('aria-expanded', items.length ? 'true' : 'false');
      popup.scrollTop = 0;
      fitHeight(popup);
      Array.prototype.forEach.call(optionRows(), function (li, i) { fitRow(li, items[i]); });
      fillGlosses(glosses);
    }

    /* Site decisions 150: what a suggestion row searches — the one spelling it shows (lookup.js
     * `typedLine`), else its word; an English row its English word. */
    function pickWord(item) { return item.line && item.line.length ? item.line[0].w : item.word; }

    /*
     * The English suggestions (site decisions 148 item 4): one row per English word
     * (`englishRow`), in lookup.js `englishSuggest`'s order, up to 20, the list scrolling and
     * capped above a phone's keyboard as the Norwegian ones; each fitted by the row fit (the
     * English word cut last, `fitRow`) and then its headword list (`ordparFit`). Choosing one runs
     * the English search for it. The suggestions' row spacing (`suggestrows`) reaches them too.
     */
    function openEnglish(items) {
      listbox.textContent = '';
      ranked = [];
      options = items.map(function (it) { return { word: it.word, en: true }; });
      active = -1;
      recentHead.hidden = true;
      listbox.setAttribute('aria-label', t('search.suggestions'));
      items.forEach(function (it, i) {
        var li = englishRow('li', it, '');
        li.id = 'ordpar-option-' + i;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', 'false');
        li.setAttribute('data-q', it.word);                  // site decisions 180 (ahead.js)
        li.setAttribute('data-en', '');
        li.addEventListener('mousedown', function (e) { e.preventDefault(); picked(i); submit(it.word, true); });
        listbox.appendChild(li);
      });
      popup.hidden = items.length === 0;
      input.setAttribute('aria-expanded', items.length ? 'true' : 'false');
      popup.scrollTop = 0;
      fitHeight(popup);
      fitEnglish();
    }
    function fitEnglish() {
      Array.prototype.forEach.call(optionRows(), function (li, i) {
        if (li.ordparFit) { li.ordparFit(function () { fitRow(li, options[i]); }); }
      });
    }

    /* The visible height can change with the dropdown open (a phone's keyboard coming up, the
     * phone turned, the window resized): the popup's height is measured again and the rows
     * fitted again to their width, the list and the reader's place in it kept. The Recent rows
     * are capped again too (site decisions 86, Robin 2026-10-22), their widths left as they are. */
    var viewport = global.visualViewport || global;
    viewport.addEventListener('resize', function () {
      if (popup.hidden || doc.activeElement !== input) { return; }
      if (!recentHead.hidden) { fitHeight(popup); return; }
      if (options.length && options[0].en) { fitHeight(popup); fitEnglish(); return; }
      if (ranked.length) {
        fitHeight(popup);
        Array.prototype.forEach.call(optionRows(), function (li, i) { fitRow(li, options[i]); });
      }
    });

    /*
     * The recent searches (site decisions 60 item 3, amended by brief 60b): with the box focused
     * and EMPTY, the last few history entries (`ordparPersonal.RECENT`, 8) under a "Recent"
     * heading that links to the history page, drawn as suggestion rows — the query as typed; for
     * a search that found one article its word class faded italic beside it, and on the right
     * what `searchRowSide` / `fillSearchRow` draw (site decisions 88: the gloss, the Norwegian
     * definition, or several articles' numbered glosses). Painted at once from storage, the
     * right-hand sides held; those not stored are then filled from the dictionary and each row
     * fitted again as its side arrives. Choosing one runs its search again (`submit`), as
     * choosing a suggestion does. Typing replaces them with the suggestions. Capped above a
     * phone's on-screen keyboard as the suggestions are (`fitHeight`, decisions 86): the
     * heading and the rows scroll inside the dropdown when they do not fit.
     */
    function openRecent() {
      var P = global.ordparPersonal;
      var list = P ? P.history().slice(0, P.RECENT) : [];
      if (!list.length) { close(); return; }
      var mine = ++seq;                        // a suggestion answer still in flight is stale
      listbox.textContent = '';
      options = list.map(function (e) { return { word: e.q, recent: e }; });
      active = -1;
      recentHead.hidden = false;
      listbox.setAttribute('aria-label', t('recent.label'));
      list.forEach(function (e, i) {
        // site decisions 148 item 9: an English search drawn unmarked in the English manner,
        // its headwords filled from its English file, the row refitted when they come
        if (e.en) {
          var en = englishEntryRow('li', e, 'ordpar-option-recent', null, function () {
            if (mine === seq && en.parentNode === listbox) { fitRow(en, options[i]); }
          });
          en.id = 'ordpar-option-' + i;
          en.setAttribute('role', 'option');
          en.setAttribute('aria-selected', 'false');
          en.setAttribute('data-q', e.q);                      // site decisions 180 (ahead.js)
          en.setAttribute('data-en', '');
          en.addEventListener('mousedown', function (ev) { ev.preventDefault(); submit(e.q, true); });
          listbox.appendChild(en);
          return;
        }
        // the word in the accent only where a translated article is behind it (88's second
        // amendment, as a suggestion row); for several, set when the side fills
        var li = el('li', 'ordpar-option ordpar-option-recent' +
          (e.n === 1 && e.translated ? ' is-translated' : ''));
        li.id = 'ordpar-option-' + i;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', 'false');
        li.appendChild(searchRowMain(e));
        li.appendChild(searchRowSide(e));
        li.setAttribute('data-q', e.q);                        // site decisions 180 (ahead.js)
        li.addEventListener('mousedown', function (ev) { ev.preventDefault(); submit(e.q, false); });
        listbox.appendChild(li);
      });
      popup.hidden = false;
      popup.scrollTop = 0;
      // above a phone's keyboard, as the suggestions (site decisions 86, with
      // scrolling here as well): the same cap, scrolling inside
      fitHeight(popup);
      input.setAttribute('aria-expanded', 'true');
      // the row fit's steps 3-4 (the word class, then the ellipsis): a recent row has no line
      Array.prototype.forEach.call(listbox.children, function (li, i) { fitRow(li, options[i]); });
      // decisions 88: the held sides filled from the dictionary, each row refitted as it fills
      Array.prototype.slice.call(listbox.children).forEach(function (li, i) {
        var item = options[i];
        if (item.recent.en) { return; }          // an English row fills itself (`englishEntryRow`)
        fillSearchRow(li.querySelector('.ordpar-option-side'), item.recent, function () {
          if (mine === seq && li.parentNode === listbox) { fitRow(li, item); }
        });
      });
    }

    function emptyBox() { return !input.value.replace(/\s+/g, ''); }

    /*
     * The suggestion's right-hand side (brief 59b item 11, Robin 2026-10-19 — a deliberate
     * divergence from ordbokene's dropdown, which shows the word alone): several articles under
     * the word, "N articles"; one untranslated article, "Norwegian only" — or, in the "Norwegian
     * only" section (`nbsec`, site decisions 86, Robin 2026-10-22), its Norwegian definition, the
     * list view's snippet, with no tag (nothing where it has none); one translated article, the
     * first unit of its summary gloss (else of its first English sense) — no tag. (The word class
     * sits on the left, after the word.) The gloss is the article's `snip/` line up to the
     * first " · ", from the file of the word's own key (a headword's key always has its file,
     * lookup-index.md § 3), fetched after the dropdown has painted; the definition the same
     * file's whole line. Both are a gloss to the row fit (`fitRow`): cut at their end.
     */
    var glosses = [];
    function optionSide(item, pending, row, nbsec) {
      var side = el('span', 'ordpar-option-side');
      var ids = item.ids || [];
      if (ids.length > 1) {
        // decisions 82: the glosses of the articles under the form, filled by `fillGlosses`
        var list = el('span', 'ordpar-option-glosses is-pending', '\u00a0');
        list.lang = rowLang(true);                       // site decisions 152
        side.appendChild(list);
        pending.push({ list: list, side: side, word: item.word, n: ids.length,
          articles: item.articles || [], row: row, item: item });
        return side;
      }
      if (item.translated && ids.length === 1) {
        var gloss = el('span', 'ordpar-option-gloss is-pending', '\u00a0');
        gloss.lang = rowLang(true);                      // site decisions 152
        side.appendChild(gloss);
        pending.push({ span: gloss, word: item.word, id: String(ids[0]), row: row, item: item });
      } else if (nbsec && ids.length === 1) {
        var def = el('span', 'ordpar-option-gloss ordpar-option-nb is-pending', '\u00a0');
        def.lang = 'nb';
        side.appendChild(def);
        pending.push({ span: def, word: item.word, id: String(ids[0]), row: row, item: item, nb: true });
      } else {
        side.appendChild(el('span', 'ordpar-tag', t('tag.norwegianOnly')));
      }
      return side;
    }

    function fillGlosses(pending) {
      var mine = seq, todo = pending.splice(0, pending.length);
      if (!todo.length || !lookup || !lookup.loadSnippets) { return; }
      var keys = [];
      todo.forEach(function (g) {
        g.key = lookup.snipKey(lookup.fold(g.word));
        if (keys.indexOf(g.key) === -1) { keys.push(g.key); }
      });
      Promise.all(keys.map(function (k) {
        return lookup.loadSnippets(k).then(function (snips) {
          if (mine !== seq) { return; }
          snips = rowView(snips);                    // site decisions 152
          todo.forEach(function (g) {
            if (g.key !== k || !snips) { return; }
            if (g.list) { glossList(g, snips); return; }
            var text = g.nb ? (snips[g.id] || '') : glossText(snips, g.id);
            if (text) {
              writeGloss(g.span, text, !g.nb && glossIs(snips, g.id));     // site decisions 116
              if (nbRows()) { g.span.lang = 'nb'; }
              g.span.classList.remove('is-pending');
              fitRow(g.row, g.item);          // the gloss's width is known now
            }
          });
        });
      })).then(function () {
        if (mine !== seq) { return; }
        todo.forEach(function (g) {
          if (g.list) {
            if (g.list.classList.contains('is-pending')) { countOnly(g); fitRow(g.row, g.item); }
            return;
          }
          if (g.span.classList.contains('is-pending') && g.span.parentNode) {
            g.span.parentNode.removeChild(g.span);
            fitRow(g.row, g.item);            // nothing on the right after all
          }
        });
      });
    }

    /*
     * The "N articles" row's glosses (site decisions 82, Robin 2026-10-21): the articles under the
     * form in the results' order, each its homograph numeral and its gloss by the dropdown's rule —
     * "I it · II that · III the" — as many as fit the row, then "+ N more". An untranslated
     * article is not listed, only counted in the "+ N more" (decisions 82), as is a
     * translated one with no gloss text; a form with none to list keeps the
     * plain "N articles". The snippets of every article under a form sit in that form's file.
     * The history rows list the same way since 88's second amendment (`fillSearchRow`), each
     * article numbered by the row's own spelling (decisions 93, lookup.js `article`).
     */
    function glossList(g, snips) {
      var shown = listedGlosses(g.articles, snips);
      if (!shown.length) { countOnly(g); return; }
      paintGlossList(g, shown);
      fitRow(g.row, g.item);                  // the word first, against the side's floor ...
      fitGlosses(g, shown.length);            // ... then the glosses, in what it leaves
    }

    /* A one-article suggestion's headword line (decisions 82): its forms in the article's order,
     * comma-separated as the page title has them ("dannet, danna"), the ones continuing what
     * was typed bold, the rest regular (lookup.js `headLine`). */
    function drawLine(node, line) {
      line.forEach(function (part, i) {
        if (i) { node.appendChild(doc.createTextNode(part.w === '\u2026' ? ' ' : ', ')); }
        node.appendChild(el('span', part.match ? 'ordpar-option-match' : 'ordpar-option-alt', part.w));
        // no numeral after a suggestion's headword (decisions 105: the numerals belong inside the
        // gloss list only); 150 shows
        // the spelling typed, nothing more
      });
    }

    /*
     * The row fit (site decisions 82, Robin 2026-10-21): a row whose right-hand side
     * cannot show what it must — "Norwegian only" or a count whole, a gloss at least the smaller
     * of its own width and 8rem (FIT_FLOOR) — gives up, in this order and only as far as it must
     * (decisions 82; the tag is always kept whole): (1) the forms not continuing what was typed, and the
     * "…"; (2) every form but the best-matching (`item.word`); (3) the word class; (4) the word,
     * cut with an ellipsis to what the side leaves. A row with no line (an "N articles" or a
     * recent row) takes only the steps it has. Measured in the browser, always from the full
     * row, so the refit when the glosses arrive can give back what the first fit took; a gloss
     * still pending counts as the floor. The step a row reached is its `data-fit` (none: it fits).
     */
    var FIT_FLOOR = 8;                        // rem
    function fitRow(li, item) {
      if (!li || !item) { return; }
      var main = li.querySelector('.ordpar-option-main');
      var side = li.querySelector('.ordpar-option-side');
      var word = main && main.querySelector('.ordpar-option-word');
      if (!side || !word) { return; }
      var pos = main.querySelector('.ordpar-pos');
      var redraw = function (line) { word.textContent = ''; drawLine(word, line); };
      // back to the full row, as drawn
      if (item.line && li.hasAttribute('data-fit')) { redraw(item.line); }
      if (pos) { pos.hidden = false; }
      main.style.maxWidth = '';
      main.classList.remove('is-cut');
      li.removeAttribute('data-fit');
      if (!li.clientWidth) { return; }        // not laid out (the popup closed)
      var cs = global.getComputedStyle(li);
      var room = li.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)
        - (parseFloat(cs.columnGap) || 0);
      var floor = FIT_FLOOR * parseFloat(global.getComputedStyle(doc.documentElement).fontSize);
      var need = sideNeed(side, floor);
      var steps = [
        item.line && function () { redraw(item.line.filter(function (part) { return part.match; })); },
        item.line && function () { redraw([{ w: item.word, match: true }]); },
        pos && function () { pos.hidden = true; },
        function () {
          main.classList.add('is-cut');
          main.style.maxWidth = Math.max(0, Math.floor(room - need)) + 'px';
        }
      ];
      for (var s = 0; s < steps.length; s++) {
        if (main.getBoundingClientRect().width + need <= room + 0.5) { break; }
        if (steps[s]) { steps[s](); }
        li.setAttribute('data-fit', String(s + 1));
      }
    }

    /* What the right-hand side must show: a tag, a count and "+ N more" whole; a gloss or a gloss
     * list at least the smaller of its own width and the floor (the floor while still pending). */
    function sideNeed(side, floor) {
      var need = 0, n = 0;
      Array.prototype.forEach.call(side.children, function (c) {
        if (c.hidden || !c.textContent) { return; }    // an empty "+ N more"
        var shrinks = c.classList.contains('ordpar-option-gloss')
          || c.classList.contains('ordpar-option-glosses');
        need += !shrinks ? c.getBoundingClientRect().width
          : c.classList.contains('is-pending') ? floor : Math.min(c.scrollWidth, floor);
        n++;
      });
      return need + (n > 1 ? (n - 1) * (parseFloat(global.getComputedStyle(side).columnGap) || 0) : 0);
    }

    /*
     * The popup's height above a phone's keyboard (site decisions 22, Robin 2026-10-21; kept
     * when 22 was reversed, 2026-10-22: "I agree"). The dropdown draws every row `suggest`
     * returns, up to 20, in a list that scrolls, as ordbokene's; its height is its own
     * (`max-height: 60vh`, shell.css) or, if less, what is left between its top and the bottom
     * of the VISUAL viewport, less a small margin (KEYBOARD_GAP) — `visualViewport`, which a
     * phone's on-screen keyboard shrinks while `vh` (and `dvh`, `svh`) do not; the window's
     * height where there is no `visualViewport` — so the list scrolls inside instead of running
     * under the keyboard. Never less than MIN_ROWS rows' height (the first row's, as drawn), so a
     * popup squeezed against the keyboard stays usable. The Recent rows take the same cap
     * (decisions 86, 2026-10-23), their heading inside the measured height. Measured after the rows are drawn, and
     * again when the visual viewport is resized with the suggestions open.
     */
    var MIN_ROWS = 3, KEYBOARD_GAP = 8;
    function fitHeight(popup) {
      popup.style.maxHeight = '';
      if (popup.hidden || !popup.offsetHeight) { return; }      // not laid out: as styled
      var vv = global.visualViewport;
      var bottom = vv ? vv.offsetTop + vv.height : global.innerHeight;
      var room = Math.floor(bottom - popup.getBoundingClientRect().top - KEYBOARD_GAP);
      var first = popup.querySelector('.ordpar-option');
      var floor = first ? Math.ceil(MIN_ROWS * first.getBoundingClientRect().height) : 0;
      if (room < popup.offsetHeight) { popup.style.maxHeight = Math.max(room, floor) + 'px'; }
    }

    /* A suggestion chosen while typing (site decisions 62 (2)): the text typed so far, the word
     * chosen, its position from 1 — one event per choice, never per keystroke (events.js). An
     * English suggestion the same, marked English (and counted, 148's follow-up). A Recent row is not a suggestion: it sends nothing here, its search counts as any
     * other. */
    function picked(i) {
      var item = options[i];
      if (!item || item.recent) { return; }
      event('pick', { typed: input.value, word: item.word, position: i + 1, en: !!item.en });
    }

    /* Decisions 113 (Robin, 2026-10-24): on a touch screen a search made by Enter or by a
     * chosen suggestion lets go of the box, so the phone's keyboard closes and the result shows.
     * With a mouse the box keeps the focus, ready for the next word — as ordbokene.no's, which
     * keeps it after Enter and after a suggestion (observed in its rendered page, 2026-10-24). */
    function touchFirst() {
      try { return !!(global.matchMedia && global.matchMedia('(pointer: coarse)').matches); } catch (e) { return false; }
    }

    /* `en` (site decisions 148): the search's direction — an English row's, a Recent entry's, or
     * (null) the switch's; the switch follows a row of the other direction. */
    function submit(value, en) {
      var query = (value != null ? value : input.value).trim();
      close();
      if (!query) { return; }
      if (en == null) { en = englishOn(); }
      if (en !== englishOn()) { setDirection(en ? 'en' : 'nb', { quiet: true }); }
      input.value = query;
      if (touchFirst()) { input.blur(); }
      if (searchHandler) {
        searchHandler(query, en ? { en: true } : undefined);
        if (!touchFirst()) { input.focus(); }   // with a mouse, focus returns to the box
      } else if (en) {
        global.location.href = lookup && lookup.englishUrl ? lookup.englishUrl(query)
          : base() + 'bm-en/#en=' + encodeURIComponent(query);
      } else if (lookup && lookup.searchAddress) {
        // site decisions 117: the word's own page where it has one, the search after `#` (the
        // page records it as a search the reader made); else the search in the fragment, never
        // sent to a server (decisions 104)
        lookup.searchAddress(query).then(function (href) { global.location.href = href; });
      } else {
        global.location.href = base() + 'bm-en/#q=' + encodeURIComponent(query);
      }
    }

    input.addEventListener('input', function () {
      if (emptyBox()) { openRecent(); return; }
      if (!lookup) { return; }
      var value = input.value;
      var guard = lookup.guard(value);
      if (!guard.ok) { close(); return; }
      var mine = ++seq;
      if (englishOn() && lookup.englishSuggest) {       // site decisions 148
        lookup.englishSuggest(value).then(function (items) {
          if (mine !== seq || doc.activeElement !== input) { return; }
          openEnglish(items);
        });
        return;
      }
      lookup.suggest(value).then(function (items) {
        if (mine !== seq || doc.activeElement !== input) { return; }
        open(items);
      });
    });

    input.addEventListener('focus', function () { if (emptyBox()) { openRecent(); } });

    input.addEventListener('keydown', function (e) {
      if (popup.hidden && (e.key === 'ArrowDown') && (lookup || emptyBox())) {
        input.dispatchEvent(new Event('input'));
        return;
      }
      if (popup.hidden) { return; }
      switch (e.key) {
        case 'ArrowDown': e.preventDefault(); choose((active + 1) % options.length); break;
        case 'ArrowUp': e.preventDefault(); choose(active <= 0 ? options.length - 1 : active - 1); break;
        case 'Home': e.preventDefault(); choose(0); break;
        case 'End': e.preventDefault(); choose(options.length - 1); break;
        case 'Escape': e.preventDefault(); close(); break;
        case 'Tab': close(); break;
        case 'Enter':
          if (active >= 0) {
            e.preventDefault();
            picked(active);
            var o = options[active];
            submit(pickWord(o), o.en ? true : o.recent ? !!o.recent.en : false);
          }
          break;
        default: break;
      }
    });

    input.addEventListener('blur', function () { global.setTimeout(close, 120); });
    clear.addEventListener('click', function () {
      input.value = '';
      close();
      input.focus();
      openRecent();             // the box is empty and focused: the recent lookups
    });

    // never the form's own GET, on any page: it would put the search in the address's query,
    // which goes to the host (decisions 104); `submit` answers in place or goes to `#q=`
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      submit();
    });
  }

  /* ------------------------------------------------------------- rendering */

  function rerender() {
    if (global.ordparPersonal && has('fav.label')) {
      global.ordparPersonal.setLabels({ label: t('fav.label'), saved: t('fav.saved') });
    }
    var header = doc.querySelector('header.ordpar-header');
    if (header) { enhanceHeader(header); }
    relabel(doc);
    markCurrent(doc);
    syncIcons();                     // site decisions 152: the icons' words
    notify('render', lang);
  }

  /**
   * An event for our receiver (site decisions 26, 62, 104), handed to `events.js`
   * (`window.ordparEvents`), which decides whether anything is sent at all: nothing without the
   * receiver's address, under automation, offline, or with Global Privacy Control or Do Not
   * Track. Only 'pick' comes through here (`data.en`: an English suggestion, site decisions 148's
   * follow-up); the page view, the searches and the install are `events.js`'s own, called by it,
   * `lookup.js` and `install.js`.
   */
  function event(name, data) {
    var E = global.ordparEvents;
    if (!E || !data) { return; }
    try {
      if (name === 'pick') { E.pick(data.typed, data.word, data.position, !!data.en); }
    } catch (e) { /* never in the reader's way */ }
  }

  /* ------------------------------------ an open "?" box swallows the outside click (decisions 124) */
  // While a "?" box is open, a click or tap anywhere outside it closes the box
  // and does NOTHING ELSE — no setting picked, no drop-down opened, no link followed, no mini
  // opened; the next click acts as usual. ONE mechanism for every "?" box the site draws (the
  // settings' hints, `settings.js`, decisions 99; the pronunciation "?" of the articles, the page
  // script `sitegen/page.py`, decisions 123): the box's owner calls `pin(wrap, close)` when a click
  // or tap opens it (or keeps a hovered box open), and `unpin(wrap)` whenever it closes. A box a
  // mouse merely rests on is not pinned: it goes when the pointer leaves, and a click elsewhere then
  // acts as usual. Here, on the window in the capture phase, before every listener of the page:
  // * a mouse (or pen) press outside the box closes it at once; that press's mousedown (a
  //   drop-down's opening, the focus, a text selection), mouseup and click are swallowed;
  // * a finger closes it on its LIFT (pointerup), not on touching: a finger that scrolls gets
  //   `pointercancel` instead and leaves the box open. The lift's touchend is cancelled (no mouse
  //   events, no click follow it), and its click, should a browser send one anyway, is swallowed;
  // a press on the box itself or its own "?" (inside `wrap`) is never touched, so the "?" still
  // toggles. A press on ANOTHER "?" is outside: it closes the open box and opens nothing (the
  // ruling's plain reading). The swallowing ends with that click, the next press or key, or 800 ms
  // after a lift. The keyboard is not affected.
  var hintGuard = (function () {
    var pinned = null, touch = null, eat = false, eatTimer = null;
    function stopEating() {
      eat = false;
      if (eatTimer) { clearTimeout(eatTimer); eatTimer = null; }
    }
    function outside(e) {
      if (!pinned) { return false; }
      if (!doc.documentElement.contains(pinned.wrap)) { pinned = null; return false; }   // redrawn
      return !(e.target && e.target.nodeType && pinned.wrap.contains(e.target));
    }
    function shut() {
      var p = pinned;
      pinned = null; touch = null;
      try { p.close(); } catch (er) { /* the box's own bug */ }
    }
    function swallow(e) { e.preventDefault(); e.stopImmediatePropagation(); }
    if (global.addEventListener && doc) {
      global.addEventListener('pointerdown', function (e) {
        stopEating(); touch = null;
        if (!outside(e)) { return; }
        if (e.pointerType === 'touch') { touch = e.pointerId; return; }
        shut(); eat = true;
        e.stopImmediatePropagation();       // not cancelled: its mousedown must come, to be cancelled
      }, true);
      global.addEventListener('pointercancel', function (e) {
        if (touch === e.pointerId) { touch = null; }       // a scroll, not a tap: the box stays
      }, true);
      global.addEventListener('pointerup', function (e) {
        if (touch === null || touch !== e.pointerId) { return; }
        touch = null;
        if (!pinned) { return; }
        shut(); eat = true;
        eatTimer = setTimeout(stopEating, 800);
        swallow(e);
      }, true);
      global.addEventListener('touchend', function (e) {
        if (eat) { swallow(e); }
      }, { capture: true, passive: false });
      ['mousedown', 'mouseup', 'click', 'auxclick', 'contextmenu'].forEach(function (type) {
        global.addEventListener(type, function (e) {
          if (!eat) { return; }
          swallow(e);
          if (type === 'click' || type === 'auxclick') { stopEating(); }
        }, true);
      });
      global.addEventListener('keydown', stopEating, true);
    }
    return {
      /** The box in `wrap` is open by a click or tap: an outside press closes it (`close()`) and
       *  does nothing else. One box at a time: pinning another forgets the first. */
      pin: function (wrap, close) { pinned = { wrap: wrap, close: close }; },
      /** The box in `wrap` has closed (whoever closed it). */
      unpin: function (wrap) { if (pinned && pinned.wrap === wrap) { pinned = null; touch = null; } },
      isPinned: function (wrap) { return !!pinned && (!wrap || pinned.wrap === wrap); }
    };
  }());

  var shell = {
    t: t,
    hintGuard: hintGuard,
    has: has,
    lang: lang,
    getSetting: getSetting,
    savedSetting: savedSetting,                                      // site decisions 146
    popupAddress: popupAddress, copyText: copyText, wireCodeLines: wireCodeLines,
    SETTINGS: SETTINGS,
    colours: colours,
    setSetting: setSetting,
    resetSettings: resetSettings,
    applyAll: applyAll,
    KEYS: KEYS.slice(),
    deleteStoredData: deleteStoredData,
    onChange: function (fn) { listeners.push(fn); },
    searchRowMain: searchRowMain, searchRowSide: searchRowSide, fillSearchRow: fillSearchRow,
    sideGlosses: sideGlosses, similarArticles: similarArticles,     // site decisions 144
    // site decisions 148: the direction switch and the English rows
    direction: direction, setDirection: setDirection,
    // site decisions 152: Norwegian only — the layer as it stands, a setting through it, the word
    // class and the tables' words in Norwegian, the switch hidden, a setting for this visit only
    layer: layer, eff: eff, nbWords: nbWords, equivHidden: equivHidden, visitSetting: visitSetting,
    hoverNb: hoverNb,                                        // site decisions 185
    syncIcons: syncIcons, posWords: posWords, posSpan: posSpan,
    englishRow: englishRow, englishEntryRow: englishEntryRow,
    setSearchHandler: function (fn) { searchHandler = fn; },
    /** Whether this page answers searches in place (a handler set: the search page, the front
     *  page, a word page, the 404 shell) — ahead.js then loads a search ahead without the page it
     *  will not navigate to (site decisions 180). */
    answersInPlace: function () { return !!searchHandler; },
    /** A search answered in place by the page's own handler (the search page, the 404 shell),
     *  as the box's submit does; -> false where the page has none (Random word, decisions 115,
     *  then opens `/bm-en/#q=`). The box shows the word. `how` is handed on: `{random: true}`
     *  for a Random word draw, answered but not recorded or sent as a search (decisions 115). */
    search: function (q, how) {
      if (!searchHandler || !q) { return false; }
      var box = doc.getElementById('ordpar-q');
      if (box) { box.value = q; }
      searchHandler(q, how);
      return true;
    },
    render: rerender,
    event: event,
    ready: null
  };
  global.ordparShell = shell;

  applyTheme();
  applyColour();
  applyDefs();
  var inlined = global.ORDPAR_STRINGS || {};
  for (var code in inlined) { strings[code] = inlined[code]; }
  // the chrome that needs script, at once: on an article page this file runs deferred, after
  // the whole document; on a shell page at the end of <body>, after the header and the footer.
  // Its words are the strings in force — inline on every page (`ORDPAR_STRINGS`: the shell
  // pages' own block, `/site/ordpar.js`'s first part).
  addChrome();

  function start() {
    shell.ready = useLang(getSetting('lang')).then(function () {
      rerender();
      wireCodeLines(doc);       // site decisions 146: the Copy buttons on a page's code lines (`/more/`)
      // Random word, beside the box in the header (decisions 63): lookup.js picks the word; a
      // page without it hides the button rather than show one that does nothing
      if (global.ordparSearch) { global.ordparSearch.wireRandom(doc); }
      else {
        Array.prototype.forEach.call(doc.querySelectorAll('[data-ordpar-random]'),
          function (b) { b.hidden = true; });
      }
      return shell;
    });
  }

  if (doc.readyState === 'loading') { doc.addEventListener('DOMContentLoaded', start); }
  else { start(); }
}(typeof globalThis !== 'undefined' ? globalThis : this));
