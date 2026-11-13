/*! Ordpar — loading ahead (site decisions 92, Robin 2026-10-22; widened by 180, Robin
 * 2026-11-09): an article, a page or a search fetched before the reader opens it, so the open
 * is instant. Spec: ordpar/docs/build-site.md § Loading ahead; the setting:
 * ordpar/docs/lookup-index.md § 7.
 *
 * The setting `minifetch` (its key and values from decisions 80, when it governed the minis
 * alone; since 92 under Settings → Loading, offline and your data → Loading) governs every
 * control that opens an article, a page or a search of this site (since 180; links alone until
 * then):
 *
 *   point   (the default) when the pointer has rested on it for `REST_MS` without moving (a
 *           pointer crossing the page fetches nothing), and on a touch (`touchstart`: a tap's
 *           own 50–100 ms, the only head start a touch screen gives — a phone has no resting
 *           pointer, so there `point` is a fetch at the touch, as the minis' has been since 80)
 *   click   nothing ahead: the fetch starts on the click
 *   page    what the page shows is fetched with it, one at a time in idle time (`queue`): the
 *           list view's articles (lookup.js `listRows`, the favourites page's rows too) and the
 *           minis' targets (mini.js `scan`); everything else as `point` (nothing 180 added is
 *           queued). With the browser's data saver on (`navigator.connection.saveData`), `page`
 *           is `click`.
 *
 * What is fetched ahead, for which control (`aim`):
 *
 *   a list-view row (`.ordpar-row[data-id]`'s button: the search page, the favourites page) —
 *           its article through `ordparSearch.fetchArticle`, the one in-memory cache the row's
 *           own open and the minis already share within the page view
 *   a cross-reference's mini — mini.js, as before (`xref = page` makes it a link like any
 *           other); since 180 a link inside an open small article that mini.js opens as a
 *           nested one too (`ordparMinis.target`; until then fetched here as well, twice in
 *           all) — under `page`, which mini.js does not rest on, through its `load`
 *   a link to a page of this site — `/` (180), `/bm-en/<id>/` (the inflected-form rows,
 *           a mini's own links, a cross-reference under `xref = page`), a word or form page
 *           `/bm-en/<word>/` with its search after `#` or none (180: the similar headwords, an
 *           article's "more entries"), `/bm-en/#q=…` (the history page's rows, the similar
 *           words; the query in the fragment, never sent — decisions 104), `/bm-en/#en=…` (180:
 *           an English search), `/history/`, `/favourites/`, `/settings/` (the header's and the
 *           footer's links), and the about-type pages by their list (180: `about`, `coming`,
 *           `changes`, `dictionary-changes`, `deck-changes`, `thanks`, `privacy`, `help`,
 *           `more`, `survey` — not any path: `out/` holds lab folders): the page (`warm`), read
 *           whole so the browser's HTTP cache keeps it for the navigation (the host's
 *           `max-age=600`; with an offline copy the worker answers it from the copy), and the
 *           scripts and sheets it links that this page has not loaded; for a search, the index
 *           files its query reads (`ordparLookup.lookup`; an English one's, `englishLookup`)
 *           and, where the search will show its articles in full, those (at most `FULL_MAX`).
 *           On a page that answers searches in place (`ordparShell.answersInPlace`: the search
 *           page, the front page, a word page, the 404 shell) a link whose search is in the
 *           fragment is answered here, so only the search is fetched, its articles through
 *           `fetchArticle`, never the page it names
 *   a suggestion or Recent row under the box (180; shell.js puts its search on the row,
 *           `data-q`, `data-en`) — its search as its press opens it (`warmQuery`: in place, or
 *           its word page by lookup.js `searchAddress`, or `/bm-en/#en=`); a row selected by the
 *           keyboard (`select`, from shell.js `choose`) once the selection has stayed on it for
 *           `REST_MS`
 *   Random word (180) — the word drawn at the rest (lookup.js `drawAhead`, kept on the button
 *           for its click, `wireRandom`; one draw per click) and its search as the click opens
 *           it, without the drawn mark; a draw is still not a search (decisions 115)
 *
 * Never fetched ahead (the exceptions ruled in 180): a link that leaves the site, opens
 * elsewhere (`target`, `download`) or only moves on this page; actions (a report, the survey's
 * Submit, Clear history, removing a favourite, Copy link, Share, the heart, the offline copy's
 * and install's buttons, the settings' export / import / reset / delete / presets — none a link
 * or a row `aim` knows); the English/Norwegian switch. Each URL once per page view. Nothing here
 * stores anything.
 *
 *   window.ordparAhead = { mode, queue, warm, aim, select, assetsOf, REST_MS, FULL_MAX }
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var REST_MS = 150;          // decisions 80: "the mouse actually has to stand still"
  var FULL_MAX = 3;           // a search shown in full: its first pages fetched ahead
  var VALUES = ['point', 'click', 'page'];

  /* --------------------------------------------------------------- the mode */

  function stored() {
    // site decisions 146: the visit's value where it has one (the head script's `ordparRead`)
    if (typeof global.ordparRead === 'function') { return global.ordparRead('minifetch'); }
    try { return global.localStorage.getItem('minifetch'); } catch (e) { return null; }
  }

  /** The setting as read (shell.js `getSetting`, which knows the default), then the data saver:
   *  'point' | 'click' | 'page'. */
  function mode() {
    var sh = global.ordparShell, m = null;
    if (sh && sh.getSetting) { m = sh.getSetting('minifetch'); }
    if (VALUES.indexOf(m) === -1) { m = stored(); }
    if (VALUES.indexOf(m) === -1) { m = 'point'; }
    var c = global.navigator && global.navigator.connection;
    return m === 'page' && c && c.saveData ? 'click' : m;
  }

  /* ------------------------------------------------------- the idle queue */

  var queued = Object.create(null), list = [], pumping = false;
  function idle(f) {
    if (global.requestIdleCallback) { global.requestIdleCallback(f, { timeout: 3000 }); } else { setTimeout(f, 200); }
  }
  function pump() {
    if (pumping) { return; }
    var job = list.shift();
    if (!job) { return; }
    pumping = true;
    idle(function () {
      var p;
      try { p = Promise.resolve(job()); } catch (e) { p = Promise.resolve(); }
      p.then(next, next);
    });
  }
  function next() { pumping = false; pump(); }

  /** `fn` (returning a promise) run once per `key` per page view, one job at a time in idle
   *  time — the minis' targets (mini.js) and the list view's articles share it. */
  function queue(key, fn) {
    if (queued[key]) { return; }
    queued[key] = 1;
    list.push(fn);
    pump();
  }

  /* --------------------------------------------------------- the fetches */

  var warmed = Object.create(null);

  function origin() { return global.location ? global.location.origin : ''; }

  function get(url) {
    if (!global.fetch) { return Promise.resolve(null); }
    return global.fetch(url, { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .catch(function () { return null; });
  }

  /** The scripts and sheets a page links (`/site/…`) that this page has not loaded itself. */
  function assetsOf(html) {
    var have = Object.create(null), out = [], d = global.document;
    if (d && d.querySelectorAll) {
      Array.prototype.forEach.call(d.querySelectorAll('script[src], link[rel="stylesheet"][href]'), function (n) {
        have[n.getAttribute('src') || n.getAttribute('href')] = 1;
      });
    }
    var re = /<(?:script[^>]*\ssrc|link[^>]*\shref)="(\/site\/[\w.\/-]+\.(?:js|css)(?:\?v=[0-9a-f]+)?)"/g, m;
    while ((m = re.exec(html))) {
      if (!have[m[1]] && out.indexOf(m[1]) === -1) { out.push(m[1]); }
    }
    return out;
  }

  /** Whether this page answers a search in place (the search page, the front page, a word page,
   *  the 404 shell: a search handler set, shell.js `answersInPlace`) — a search-shaped link or
   *  row is answered here, so the page it names is never fetched (site decisions 180). */
  function answersInPlace() {
    var sh = global.ordparShell;
    return !!(sh && sh.answersInPlace && sh.answersInPlace());
  }

  /** An article a search will show in full: through `ordparSearch.fetchArticle` where the search
   *  is answered on this page (the in-memory cache its render reads, as a list row's), else its
   *  page into the HTTP cache for the navigation. */
  function warmArticle(id, here) {
    var S = global.ordparSearch;
    if (here && S && S.fetchArticle) { return Promise.resolve(S.fetchArticle(id)); }
    return warm('/bm-en/' + id + '/');
  }

  /** A search's index files, and its articles' pages where it will show them in full (the
   *  list-view setting's rule, lookup.js `useList`, which counts the inflected-form rows under
   *  the default 'forms' — site decisions 158). `here`: answered on this page. */
  function warmSearch(q, here) {
    var L = global.ordparLookup;
    if (!L || !L.lookup || !q) { return Promise.resolve(); }
    return Promise.resolve(L.lookup(q)).then(function (res) {
      if (!res) { return; }
      var ids = [];
      (res.heads || []).forEach(function (g) { g.articles.forEach(function (a) { ids.push(a.id); }); });
      var sh = global.ordparShell;
      var lv = sh && sh.getSetting ? sh.getSetting('listview') : 'forms';
      var full = L.useList ? !L.useList(lv, ids.length, L.formHits ? L.formHits(res) : 0)
        : lv === 'off' || (lv !== 'on' && ids.length === 1);
      if (!full) { return; }
      return Promise.all(ids.slice(0, FULL_MAX).map(function (id) { return warmArticle(id, here); }));
    }).catch(function () { /* nothing ahead */ });
  }

  /** An English search's file (`ordparLookup.englishLookup`, site decisions 148), and where it
   *  opens its one match in full whatever the list view says (lookup.js, Robin 2026-10-29), that
   *  article (site decisions 180). */
  function warmEnglish(q, here) {
    var L = global.ordparLookup;
    if (!L || !L.englishLookup || !q) { return Promise.resolve(); }
    return Promise.resolve(L.englishLookup(q)).then(function (res) {
      if (res && res.count === 1 && res.matches && res.matches[0]) { return warmArticle(res.matches[0].id, here); }
    }).catch(function () { /* nothing ahead */ });
  }

  /** A script or sheet a fetched page links, once per page view (site decisions 180: two pages
   *  warmed from one row — a word page and its article — link the same bundle). */
  var gotAsset = Object.create(null);
  function asset(url) {
    if (!gotAsset[url]) {
      gotAsset[url] = get(url).then(function (t) { if (t == null) { delete gotAsset[url]; } return t; });
    }
    return gotAsset[url];
  }

  /** A page of this site fetched ahead, with the scripts and sheets it links, once per page view. */
  function warmPage(page) {
    if (warmed[page]) { return warmed[page]; }
    var p = get(page).then(function (html) {
      if (!html) { delete warmed[page]; return; }
      return Promise.all(assetsOf(html).map(asset));
    });
    warmed[page] = p;
    return p;
  }

  /** The search a path stands for -> {q, en, hashed} or null: `#q=` (decisions 104; after settings
   *  too, site decisions 146; a drawn mark `&random` after it does not stop it, 180), `#en=` (an
   *  English search, 148), else a word or form page's own word (`/bm-en/så/`, 117: it runs that
   *  word's search when opened). `hashed`: the search is in the fragment, so a page that answers
   *  searches in place answers it there (lookup.js `wireFragmentLinks`). */
  function searchOf(path) {
    var cut = path.indexOf('#');
    var page = cut < 0 ? path : path.slice(0, cut), hash = cut < 0 ? '' : path.slice(cut);
    var m = /(?:^#|&)q=([^&#]*)/.exec(hash), en = false;
    if (!m) { m = /(?:^#|&)en=([^&#]*)/.exec(hash); en = !!m; }
    var raw = m ? m[1] : null, hashed = !!m;
    if (raw == null) {
      var w = WORD.exec(page);
      if (!w || /^\d+$/.test(w[1])) { return null; }
      raw = w[1];
    }
    var q = '';
    try { q = decodeURIComponent(raw.replace(/\+/g, ' ')); } catch (e) { q = ''; }
    q = q.trim();
    return q ? { q: q, en: en, hashed: hashed } : null;
  }

  /** What a link to a page of this site fetches ahead (see the head comment): the page, unless
   *  it is this one or a search this page answers in place, and for a search (`/bm-en/#q=…`,
   *  decisions 104; a word page's, 117; an English one, 148) its index files — the query is
   *  never sent: the page is fetched without its fragment. */
  function warm(path) {
    var cut = path.indexOf('#');
    var page = cut < 0 ? path : path.slice(0, cut);
    var s = searchOf(path);
    var loc = global.location;
    var self = !!(loc && page === loc.pathname + loc.search);
    var inPlace = !!(s && s.hashed && answersInPlace());
    var jobs = [];
    if (!self && !inPlace) { jobs.push(warmPage(page)); }
    // answered on this page (this very page, or a search it answers in place): its articles
    // through the page's own cache
    if (s) { jobs.push(s.en ? warmEnglish(s.q, self || inPlace) : warmSearch(s.q, self || inPlace)); }
    return Promise.all(jobs);
  }

  /** A path of the address a search opens at (lookup.js `searchAddress`, `englishUrl`: the
   *  configured base before it), as `warm` takes it; null for another origin. */
  function local(href) {
    try {
      var u = new global.URL(href, global.location.href);
      return u.origin === origin() ? u.pathname + u.search + u.hash : null;
    } catch (e) { return null; }
  }

  /** What a search made from the box opens (shell.js `submit`: a suggestion, a Recent row; Random
   *  word's draw, lookup.js `wireRandom`), fetched ahead: answered in place where this page
   *  answers searches, else at its address — the word's page where it has one (`searchAddress`,
   *  117), else `/bm-en/#q=`; an English search at `/bm-en/#en=`. Never with the drawn mark. */
  function warmQuery(q, en) {
    q = String(q == null ? '' : q).trim();
    if (!q) { return Promise.resolve(null); }
    var L = global.ordparLookup;
    if (en) {
      var enPath = '/bm-en/#en=' + encodeURIComponent(q);
      return warm((L && L.englishUrl && local(L.englishUrl(q))) || enPath);
    }
    var plain = '/bm-en/#q=' + encodeURIComponent(q);
    if (answersInPlace() || !L || !L.searchAddress) { return warm(plain); }
    return Promise.resolve(L.searchAddress(q)).then(function (href) { return warm(local(href) || plain); },
      function () { return warm(plain); });
  }

  /* ------------------------------------------------------------ the links */

  // a search is `/bm-en/#q=…` (decisions 104); an old `?q=` address is never fetched ahead, as
  // that would send its query
  // (site decisions 146: settings may stand before the search, `#defs=en&q=…`)
  // site decisions 180: the front page; a word or form page `/bm-en/<word>/` (percent-encoded, as
  // lookup.js `pagePath` writes it; its search after `#`, or none); an English search
  // `/bm-en/#en=…`; the about-type pages by their list — not any path, as `out/` holds lab
  // folders (`/compare-53/`, `/t54/`)
  var PAGE = /^\/(?:|bm-en\/[^\/#?]+\/(?:#(?:[a-z]+=[a-z0-9-]*&)*q=[^#]+)?|bm-en\/#(?:[a-z]+=[a-z0-9-]*&)*q=[^#]+|bm-en\/#en=[^#&]+|(?:history|favourites|settings|about|coming|changes|dictionary-changes|deck-changes|thanks|privacy|help|more|survey)\/)$/;
  var WORD = /^\/bm-en\/([^\/#?]+)\/$/;

  /** A cross-reference mini.js opens a small article for (its `target`, with its rules for a link
   *  inside an open one: nesting, depth — decisions 139, 147) -> that target, or null: left to
   *  mini.js, unless `xref = page` makes it a plain link. Site decisions 180 (the inventory's
   *  Doubt (a)): until then a link inside an open small article counted as a page link here too,
   *  so mini.js and this file both fetched it. */
  function miniOf(a) {
    var M = global.ordparMinis;
    if (!M || !a.classList.contains('ordbok-xword')) { return null; }
    if (!a.parentNode || !a.parentNode.classList || !a.parentNode.classList.contains('ordbok-xref')) { return null; }
    var sh = global.ordparShell;
    if (sh && sh.getSetting && sh.getSetting('xref') === 'page') { return null; }
    if (M.target) { return M.target(a) || null; }
    return a.closest('.ordbok-xmini') ? null : { depth: 0 };        // a mini.js without `target`
  }

  /** What resting on `n` would fetch -> {key, run} or null. */
  function aim(n) {
    if (!n || !n.closest) { return null; }
    var btn = n.closest('.ordpar-row-button');
    if (btn) {
      var row = btn.closest('.ordpar-row');
      var id = row && +row.getAttribute('data-id');
      var S = global.ordparSearch;
      if (!id || !S || !S.fetchArticle) { return null; }
      return { key: 'a' + id, run: function () { return S.fetchArticle(id); } };
    }
    // site decisions 180: a suggestion or Recent row under the box (shell.js puts its search on
    // it, `data-q`, and `data-en` on an English one) — its search as its press opens it
    var opt = n.closest('.ordpar-option');
    if (opt) {
      var oq = opt.getAttribute('data-q'), oen = opt.hasAttribute('data-en');
      if (!oq) { return null; }
      return { key: 'opt:' + (oen ? 'en:' : 'nb:') + oq, run: function () { return warmQuery(oq, oen); } };
    }
    // site decisions 180: Random word — the word drawn at the rest (lookup.js `drawAhead`, which
    // its click then takes) and what the click opens; one draw per click (the key carries the
    // button's count of clicks, `ordparDrawGen`), in the direction of that moment
    var rb = n.closest('[data-ordpar-random]');
    if (rb) {
      var R = global.ordparSearch;
      if (rb.disabled || !R || !R.drawAhead) { return null; }
      var ren = !!(R.randomEnglishOn && R.randomEnglishOn());
      return { key: 'random:' + (rb.ordparDrawGen || 0) + (ren ? ':en' : ''), fresh: true, run: function () {
        return Promise.resolve(R.drawAhead(rb)).then(function (d) {
          if (!d || d.w == null) { return null; }
          return typeof d.w === 'number' ? warm('/bm-en/' + d.w + '/') : warmQuery(d.w, d.en);
        });
      } };
    }
    var a = n.closest('a[href]');
    if (!a || a.target || a.hasAttribute('download')) { return null; }
    var mt = miniOf(a);
    if (mt) {
      // mini.js loads it on the rest under `point`; under `page` it queued the page's own links
      // with the page (`scan`), not those inside a small article opened since — those load here,
      // through mini.js's own `load`, under its key
      var M = global.ordparMinis;
      if (mt.depth && mt.id && M.load && mode() === 'page') {
        return { key: 'a' + mt.id, run: function () { return M.load(mt.id); } };
      }
      return null;
    }
    var url;
    try { url = new global.URL(a.href, global.location.href); } catch (e) { return null; }
    if (url.origin !== origin()) { return null; }
    // a search's key is its fragment (`/bm-en/#q=hus`, a word page's `/bm-en/hus/#q=hus`, an
    // English one's `/bm-en/#en=house`); any other fragment is a place on the page
    var search = !url.search && (url.pathname === '/bm-en/' ? /(?:^#|&)(?:q|en)=/.test(url.hash)
      : WORD.test(url.pathname) && /(?:^#|&)q=/.test(url.hash));
    var path = url.pathname + url.search + (search ? url.hash : '');
    if (!PAGE.test(path)) { return null; }
    var loc = global.location;
    if (loc && path === loc.pathname + loc.search + (search ? loc.hash : '')) { return null; }
    return { key: path, run: function () { return warm(path); } };
  }

  var done = Object.create(null);
  function go(t) {
    if (done[t.key]) { return; }
    done[t.key] = 1;
    Promise.resolve(t.run()).then(function (got) { if (got === null) { delete done[t.key]; } },
      function () { delete done[t.key]; });
  }

  var restKey = null, restNode = null, restTimer = null;
  function unrest() {
    if (restTimer) { clearTimeout(restTimer); }
    restKey = restNode = restTimer = null;
  }

  /** Keyboard selection in the box's suggestions (site decisions 180; shell.js `choose`, and
   *  `close` with null): the selected row's search once the selection has stayed on it for
   *  `REST_MS`, as the pointer's rest; arrowing on sooner loads nothing. */
  var selTimer = null;
  function select(node) {
    if (selTimer) { clearTimeout(selTimer); selTimer = null; }
    if (!node || mode() === 'click') { return; }
    var t = aim(node);
    if (!t || done[t.key]) { return; }
    selTimer = setTimeout(function () { selTimer = null; go(t); }, REST_MS);
  }

  var CONTROL = '.ordpar-row-button, .ordpar-option, [data-ordpar-random], a[href]';

  if (doc && doc.addEventListener) {
    // `point` (and `page`, for what the page did not fetch with it): a fetch once the pointer
    // has rested on the control (each move restarts the wait)
    var lastNode = null, lastAim = null;
    doc.addEventListener('mousemove', function (e) {
      if (mode() === 'click') { return; }
      // Random word's key changes with each click while the pointer stays on it (`fresh`)
      if (e.target !== lastNode || (lastAim && lastAim.fresh)) { lastNode = e.target; lastAim = aim(e.target); }
      var t = lastAim;
      if (!t) { if (restKey) { unrest(); } return; }
      if (done[t.key]) { return; }
      if (restTimer) { clearTimeout(restTimer); }
      restKey = t.key;
      restNode = e.target.closest(CONTROL);
      restTimer = setTimeout(function () { restTimer = null; restKey = null; go(t); }, REST_MS);
    });
    doc.addEventListener('mouseout', function (e) {
      if (restNode && !(e.relatedTarget && restNode.contains(e.relatedTarget))) { unrest(); }
    });
    doc.addEventListener('touchstart', function (e) {
      if (mode() === 'click') { return; }
      var t = aim(e.target);
      if (t) { go(t); }
    }, { passive: true });
  }

  global.ordparAhead = { mode: mode, queue: queue, warm: warm, aim: aim, select: select, assetsOf: assetsOf,
    REST_MS: REST_MS, FULL_MAX: FULL_MAX };
}(typeof globalThis !== 'undefined' ? globalThis : this));
