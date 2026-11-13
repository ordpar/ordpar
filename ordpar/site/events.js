/*! Ordpar — the events a page sends to our receiver (site decisions 26, 62, 104).
 *
 *   window.ordparEvents = {
 *     view(),                    // started on load: one page view, the path only (26), sent once
 *                                // the page has been visible VISIBLE_MS, or at the first scroll,
 *                                // tap or key — whichever comes first (104, layer 4)
 *     install(),                 // the offline app installed (install.js, `appinstalled`)
 *     hit(query, en),            // a search the reader made found something (62 (3))
 *     missStart(query, en),      // ... found nothing: held until the reader chooses a similar
 *     missChoose(query, word, position, en),  // word (sent with it) or leaves (sent with none) (62 (1))
 *     pick(typed, word, position, en),        // a suggestion chosen while typing (62 (2))
 *     quiet(), cleanQuery(q), cleanPath(p), message(type, fields), RECEIVER
 *   }
 *
 * SENDS NOTHING when the receiver's address is empty (the default: a build without it sends
 * nothing and works the same), when the browser is driven by automation (`navigator.webdriver`:
 * our own browser tests, 103 — layer 3), when it is offline (62: the offline app logs nothing —
 * read as "nothing without a connection": the installed app online sends as the website does,
 * the session's call at Robin's delegation, 104, and the privacy page says so),
 * when the reader has turned off "Send usage statistics" in Settings (the setting `stats` = off,
 * decisions 104, Robin 2026-10-23: one switch for all), or when the reader asks not to be
 * tracked — Global Privacy Control or Do Not Track (104's box, item 2). A query with a digit or
 * over MAX_QUERY characters is not sent at all (62; the receiver drops it too). No retry and no
 * queue: an event that fails is lost.
 *
 * No identifier of any kind: nothing is written to storage here and one thing is read — the
 * reader's own choice, `stats` (`STATS_KEY`), read at every event so a change applies at once;
 * "Delete stored data" and "Reset settings" remove it, which is On again. The message holds
 * only the fields below, it goes without cookies (`credentials: 'omit'`) and without the page's
 * address (`referrerPolicy: 'no-referrer'`). A view's path is one of the site's own or `/other`
 * (`cleanPath`, the receiver's rule): a mistyped address is never sent as typed (104, R12). The
 * receiver: ordpar/receiver/; what it keeps: ordpar/docs/receiver.md; the words for readers:
 * ordpar/privacy.md.
 *
 * THE SEARCH'S LANGUAGE (site decisions 148's follow-up, Robin 2026-10-29: "Yes, count them"):
 * every search and suggestion message carries `lang`, 'en' for the English search (the switch on,
 * `en` true) and 'nb' for the Norwegian one, so an English search is counted as its Norwegian
 * counterpart is, by the same rules, and told apart from it.
 */
(function (global) {
  'use strict';

  /* THE RECEIVER'S ADDRESS — the one place in the site's code. Empty: nothing is ever sent.
   * On go-live: the Worker's address and its endpoint, "https://ordpar-receiver.<subdomain>.workers.dev/e". */
  var RECEIVER = '';

  var MAX_QUERY = 40;      // 62: "over about 40 characters" — the receiver's MAX_QUERY
  var VISIBLE_MS = 2000;   // 104, layer 4: "visible about 2 seconds"
  // The page paths a view may name, as the receiver's rule (rules.js `PATH`, the same pattern;
  // test_ordpar_events104.py holds the two together): any other path — a mistyped address, which
  // can hold a word the reader typed — is SENT as OTHER_PATH, not only stored so (104, R12).
  var PATH = /^\/(?:bm-en\/(?:\d{1,7}\/)?|about\/|privacy\/|settings\/|favourites\/|history\/)?$/;
  var OTHER_PATH = '/other';
  // any script's digits, as the receiver's /\p{N}/u; built at run time, so an older browser's
  // parser never meets the `u` flag (a syntax error there would stop the whole combined script)
  var DIGIT = /[0-9²³¹¼-¾٠-٩۰-۹०-९０-９]/;
  try { DIGIT = new RegExp('\\p{N}', 'u'); } catch (e) { /* the list above */ }

  var nav = global.navigator || {};
  var doc = global.document;
  // the setting "Send usage statistics" (shell.js SETTINGS `stats`, on | off, default on)
  var STATS_KEY = 'stats';

  /** Whether the reader turned the sending off in Settings. */
  function optedOut() {
    // site decisions 146: an Off carried in a pop-up's address counts too (the head script's
    // `ordparRead`: the visit's value, else the saved one)
    if (typeof global.ordparRead === 'function') { return global.ordparRead(STATS_KEY) === 'off'; }
    try { return global.localStorage.getItem(STATS_KEY) === 'off'; } catch (e) { return false; }
  }

  /** Why nothing may be sent now, or '' when it may. */
  function quiet() {
    if (!api.RECEIVER) { return 'off'; }
    if (nav.webdriver) { return 'webdriver'; }
    if (optedOut()) { return 'optout'; }
    if (nav.onLine === false) { return 'offline'; }
    if (nav.globalPrivacyControl === true) { return 'gpc'; }
    var dnt = nav.doNotTrack || global.doNotTrack || nav.msDoNotTrack;
    if (dnt === '1' || dnt === 'yes') { return 'dnt'; }
    if (typeof global.fetch !== 'function') { return 'nofetch'; }
    return '';
  }

  /** A query as sent: spaces collapsed and trimmed; null when it must not be sent (empty, a
   *  digit, or longer than MAX_QUERY characters). */
  function cleanQuery(q) {
    var s = String(q == null ? '' : q).replace(/\s+/g, ' ').replace(/^ | $/g, '');
    if (!s || DIGIT.test(s)) { return null; }
    var n = 0;
    for (var i = 0; i < s.length; i++) {          // characters, not UTF-16 units
      var c = s.charCodeAt(i);
      if (c < 0xdc00 || c > 0xdfff) { n++; }
    }
    return n > MAX_QUERY ? null : s;
  }

  /** A view's path as sent: one of the site's own, else OTHER_PATH. */
  function cleanPath(p) {
    return typeof p === 'string' && p.length <= 200 && PATH.test(p) ? p : OTHER_PATH;
  }

  /** The language of a search or a suggestion chosen as sent: 'en' or 'nb' (148's follow-up). */
  function langOf(en) { return en ? 'en' : 'nb'; }

  /** The message for one event: exactly these fields, nothing else. */
  function message(type, f) {
    f = f || {};
    if (type === 'view') { return { type: 'view', path: cleanPath(f.path) }; }
    if (type === 'install') { return { type: 'install' }; }
    var m = { type: type, query: f.query, lang: f.lang === 'en' ? 'en' : 'nb' };
    if (type === 'hit') { return m; }
    m.word = f.word == null ? null : String(f.word);
    m.position = f.position == null ? null : f.position;
    return m;
  }

  /** Send one event, or nothing. -> true when it was handed to the browser. */
  function send(type, fields) {
    if (api.quiet()) { return false; }
    try {
      global.fetch(api.RECEIVER, {
        method: 'POST',
        body: JSON.stringify(message(type, fields)),   // text/plain: no preflight
        keepalive: true,
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        cache: 'no-store'
      }).catch(function () { /* lost: no retry */ });
      return true;
    } catch (e) { return false; }
  }

  /* -------------------------------------------------------- the page view */

  var viewed = false;
  function view() {
    if (viewed || api.quiet() || !doc) { return; }
    var timer = null;
    var events = ['scroll', 'pointerdown', 'keydown'];
    function stop() {
      if (timer !== null) { global.clearTimeout(timer); timer = null; }
    }
    function fire() {
      if (viewed) { return; }
      if (doc.visibilityState && doc.visibilityState !== 'visible') { return; }
      viewed = true;
      stop();
      events.forEach(function (t) { global.removeEventListener(t, fire, true); });
      doc.removeEventListener('visibilitychange', watch);
      send('view', { path: (global.location && global.location.pathname) || '/' });
    }
    function watch() {
      stop();
      if (!viewed && (!doc.visibilityState || doc.visibilityState === 'visible') && !doc.prerendering) {
        timer = global.setTimeout(fire, VISIBLE_MS);
      }
    }
    events.forEach(function (t) { global.addEventListener(t, fire, { capture: true, passive: true }); });
    doc.addEventListener('visibilitychange', watch);
    if (doc.addEventListener && 'onprerenderingchange' in doc) { doc.addEventListener('prerenderingchange', watch); }
    watch();
  }

  /* -------------------------------------------------------- the searches */

  var miss = null;          // the miss held: {query, lang}
  function endMiss() {
    if (!miss) { return; }
    var q = miss.query, lang = miss.lang;
    miss = null;
    send('miss', { query: q, word: null, position: null, lang: lang });
  }

  var api = {
    RECEIVER: RECEIVER,
    MAX_QUERY: MAX_QUERY,
    VISIBLE_MS: VISIBLE_MS,
    quiet: quiet,
    cleanQuery: cleanQuery,
    cleanPath: cleanPath,
    message: message,
    view: view,
    install: function () { return send('install'); },
    hit: function (query, en) {
      endMiss();
      var q = cleanQuery(query);
      return q ? send('hit', { query: q, lang: langOf(en) }) : false;
    },
    missStart: function (query, en) {
      endMiss();
      var q = cleanQuery(query);
      if (q && !api.quiet()) { miss = { query: q, lang: langOf(en) }; }
    },
    missChoose: function (query, word, position, en) {
      var q = cleanQuery(query);
      if (!miss || miss.query !== q || miss.lang !== langOf(en)) { return false; }
      miss = null;
      return send('miss', { query: q, word: word, position: position, lang: langOf(en) });
    },
    missEnd: endMiss,
    pick: function (typed, word, position, en) {
      var q = cleanQuery(typed);
      return q ? send('pick', { query: q, word: word, position: position, lang: langOf(en) }) : false;
    }
  };

  // a held miss goes, with no word chosen, when the page is hidden or left
  if (doc && doc.addEventListener) {
    doc.addEventListener('visibilitychange', function () {
      if (doc.visibilityState === 'hidden') { endMiss(); }
    });
  }
  if (global.addEventListener) { global.addEventListener('pagehide', endMiss); }

  global.ordparEvents = api;
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  view();
}(typeof globalThis !== 'undefined' ? globalThis : this));
