/*! Ordpar — the service worker (decisions 61). Spec: ordpar/docs/offline-app.md.
 *
 * Scope `/`. Without the offline copy it changes nothing a visitor sees: every request goes to
 * the network as before, and only a navigation that fails gets the small offline notice below
 * in place of the browser's error page. With the copy downloaded (Settings → Offline,
 * `site/offline.js`), it answers from the copy first:
 *
 *   /bm-en/<id>/            from the article's bundle: the pack read from Cache Storage,
 *                           unpacked with DecompressionStream('gzip'), the page's bytes cut out
 *                           by the pack's offset table, the frame tokens put back (`restore`)
 *   a file in the manifest  (the shell pages, /site/…, /index/…, /manifest.webmanifest) from
 *                           its pack; a `?v=` that is not the held file's hash goes to the
 *                           network first (a page newer than the copy), the held file as fallback
 *   /bm-en/<word>/          a navigation to a word's or a form's own page (`/bm-en/<word>` too;
 *                           never all digits): the held 404 shell, which runs the word's search
 *                           from the copy, online too — so the host never sees the word (site
 *                           decisions 170, Robin 2026-11-06; until then the network first)
 *   anything else           the network; offline, /bm-en/<id> and /bm-en/<id>/<slug> get the
 *                           held 404 shell (it redirects, as the host's 404 does) and any other
 *                           page the notice
 *
 * The pure parts (`parsePack`, `restore`, `prepare`, `route`, `typeOf`, `noticeHtml`) are
 * exported for `ordpar/tests/test_ordpar_offline61.py`, which runs them under bun.
 */
'use strict';

var CACHE = 'ordpar-offline-1';               // the packs and the manifest in use
var CURRENT = '/offline/__current.json';      // the key the manifest in use is stored under
var PACKS = '/offline/';                      // a pack's key: PACKS + its file name
/** Unpacked packs kept in memory, least recently used dropped first, by their unpacked size.
 *  Since decisions 92 an article bundle holds 500 pages and unpacks to about 2 MB (8 MB at
 *  2,000 a bundle until then), so 20 MB (40 MB until then) holds about ten of them besides
 *  the index packs a query reads: more bundles at hand than before, and a bound on what the
 *  setting "With the page" holds on a page whose links reach many bundles (measured: 19). */
var KEEP_BYTES = 20e6;

var TYPES = {
  html: 'text/html; charset=utf-8', js: 'text/javascript; charset=utf-8',
  css: 'text/css; charset=utf-8', json: 'application/json; charset=utf-8',
  webmanifest: 'application/manifest+json', png: 'image/png', svg: 'image/svg+xml',
  txt: 'text/plain; charset=utf-8'
};

/* ---------------------------------------------------------------- pure parts */

function typeOf(path) {
  if (/\/$/.test(path)) { return TYPES.html; }
  var m = /\.([a-z0-9]+)$/i.exec(path);
  return (m && TYPES[m[1].toLowerCase()]) || 'application/octet-stream';
}

/** An unpacked pack (Uint8Array) -> {index: Map key -> [start, end], body, size}. The
 *  format (`build_offline.py` `pack_raw`): "OPK1", uint32 LE header length, the JSON header
 *  {keys, offsets}, the bodies. */
function parsePack(u8) {
  if (u8[0] !== 0x4f || u8[1] !== 0x50 || u8[2] !== 0x4b || u8[3] !== 0x31) {
    throw new Error('not an Ordpar pack');
  }
  var n = new DataView(u8.buffer, u8.byteOffset, u8.byteLength).getUint32(4, true);
  var head = JSON.parse(new TextDecoder().decode(u8.subarray(8, 8 + n)));
  var body = u8.subarray(8 + n);
  var index = new Map();
  for (var i = 0; i < head.keys.length; i++) {
    index.set(head.keys[i], [head.offsets[i], head.offsets[i + 1]]);
  }
  return { index: index, body: body, size: u8.byteLength };
}

/** The frame tokens put back (`build_offline.py` `blank` / `restore`): every
 *  `/site/<file>?v=*` gets the held file's hash, the build stamp its text. */
function restore(text, manifest) {
  var files = manifest.files || {};
  text = text.replace(/(\/site\/[\w.\/-]+\.(?:js|css))\?v=\*/g, function (all, path) {
    return files[path] ? path + '?v=' + files[path].hash.slice(0, 10) : all;
  });
  var token = '<!-- ' + manifest.tokens.stamp + ' -->';
  var at = text.indexOf(token);
  if (at >= 0 && at < 40 && manifest.stamp) {
    text = text.slice(0, at) + '<!-- ' + manifest.stamp + ' -->' + text.slice(at + token.length);
  }
  return text;
}

/** The manifest in use -> what the router needs. */
function prepare(manifest) {
  var byGroup = {};
  (manifest.packs || []).forEach(function (p) { byGroup[p.group] = p; });
  var bundles = (manifest.bundles || []).slice().sort(function (a, b) { return a.first - b.first; });
  return { m: manifest, byGroup: byGroup, bundles: bundles, files: manifest.files || {} };
}

/** The bundle whose range holds `id`: the last whose `first` is at or below it. */
function bundleFor(st, id) {
  var b = st.bundles, lo = 0, hi = b.length - 1, got = null;
  while (lo <= hi) {
    var mid = (lo + hi) >> 1;
    if (b[mid].first <= id) { got = b[mid]; lo = mid + 1; } else { hi = mid - 1; }
  }
  return got;
}

/** A path as the manifest keys it: `/about/index.html` is `/about/`. */
function fileKey(path) {
  return path.replace(/\/index\.html$/, '/');
}

/** A word's or a form's own page (`/bm-en/<word>/`, `/bm-en/<word>`): one path segment after
 *  /bm-en/ that is not all digits (an id's page or its redirect). */
var WORD_PAGE = /^\/bm-en\/(?!\d+\/?$)[^\/]+\/?$/;

/**
 * What to do with a GET to our own origin. `st` is `prepare(manifest)`, or null without the
 * copy. Returns {kind, fallback}:
 *   kind     'article' (+ id, bundle) | 'file' (+ path, stale) | 'shell404' (a navigation to a
 *            word page with the copy kept: the held 404 shell, status 404) | 'network'
 *   fallback what a navigation gets when the network fails too: 'shell404' (the held 404
 *            shell, status 404) or 'notice' (the offline notice); null for any other request
 */
function route(st, url, navigate) {
  var path = url.pathname;
  var fallback = null;
  if (navigate) {
    // /bm-en/<word>, /bm-en/<id> and /bm-en/<id>/<slug> are the 404 shell's (a search, a
    // redirect to the page); the page path /bm-en/<id>/ itself, and anything else, the notice
    fallback = st && /^\/bm-en\/./.test(path) && !/^\/bm-en\/\d+\/(index\.html)?$/.test(path)
      ? 'shell404' : 'notice';
  }
  if (st) {
    var m = /^\/bm-en\/(\d+)\/(?:index\.html)?$/.exec(path);
    if (m) {
      var id = +m[1], b = bundleFor(st, id);
      if (b) { return { kind: 'article', id: id, bundle: b, fallback: fallback }; }
    }
    var key = fileKey(path), f = st.files[key];
    if (f && st.byGroup[f.pack]) {
      var v = url.searchParams.get('v');
      return { kind: 'file', path: key, stale: !!v && v !== f.hash.slice(0, 10),
               fallback: fallback };
    }
    // a word page, online too (decisions 170): the search from the copy, the word never sent
    var shell = st.files['/404.html'];
    if (navigate && WORD_PAGE.test(path) && shell && st.byGroup[shell.pack]) {
      return { kind: 'shell404', fallback: fallback };
    }
  }
  return { kind: 'network', fallback: fallback };
}

/** The offline notice: a page the copy does not hold, or no copy at all, with no network. */
function noticeHtml(path, held) {
  var esc = function (s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };
  var body = held
    ? 'This page (' + esc(path) + ') is not in the offline copy on this device, and there is no connection.'
    : 'There is no connection, and the dictionary is not kept on this device. To use Ordpar without a connection, choose Settings → Offline → “Keep the whole dictionary on this device” while you are online.';
  return '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width, initial-scale=1">'
    + '<meta name="robots" content="noindex"><meta name="theme-color" content="#6b0f2e">'
    + '<title>Offline — Ordpar</title>'
    + '<script>try{var t=localStorage.getItem(\'theme\')||\'system\';if(t===\'dark\'||(t===\'system\'&&matchMedia(\'(prefers-color-scheme: dark)\').matches))document.documentElement.className=\'nightMode\';}catch(e){}</script>'
    + '<style>html{background:#fffdfd;color:#222}html.nightMode{background:#1d1a1b;color:#d9d6d6}'
    + 'body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5}'
    + 'main{max-width:34rem;margin:0 auto;padding:2rem 1rem}'
    + '.brand{font-weight:700;font-size:1.15rem;color:#6b0f2e;text-decoration:none}'
    + '.nightMode .brand,.nightMode a{color:#e3b7c9}a{color:#6b0f2e}'
    + 'h1{font-size:1.4rem;margin:1.2rem 0 .5rem}'
    + 'button{font:inherit;padding:.3em .9em;border:1px solid #c4bcbd;border-radius:6px;background:#f7f3f4;color:#6b0f2e;cursor:pointer}'
    + '.nightMode button{background:#2c2429;color:#e3b7c9;border-color:#656161}</style></head>'
    + '<body><main><a class="brand" href="/">Ordpar</a>'
    + '<h1>You are offline</h1><p>' + body + '</p>'
    + '<p><button type="button" onclick="location.reload()">Try again</button> &nbsp; '
    + '<a href="/">Go to the front page</a></p></main></body></html>\n';
}

/* ------------------------------------------------------------------ the worker */

var statePromise = null;     // Promise<prepared manifest | null>
var known;                   // undefined until read; then true / false: is there a copy?
var packs = new Map();       // pack name -> {promise, size}; Map order = least recently used first

function getState() {
  if (!statePromise) {
    // `caches.has` first: never create the cache for a visitor who has no copy
    statePromise = caches.has(CACHE)
      .then(function (has) { return has ? caches.open(CACHE) : null; })
      .then(function (c) { return c ? c.match(CURRENT) : null; })
      .then(function (r) { return r ? r.json() : null; })
      .then(function (m) { known = !!m; return m ? prepare(m) : null; })
      .catch(function () { known = false; return null; });
  }
  return statePromise;
}

function trim() {
  var total = 0;
  packs.forEach(function (e) { total += e.size; });
  var it = packs.keys(), k;
  while (total > KEEP_BYTES && packs.size > 1 && !(k = it.next()).done) {
    var e = packs.get(k.value);
    if (e.size) { packs.delete(k.value); total -= e.size; }
  }
}

/** The pack `name`, unpacked: from memory, else read from Cache Storage and unpacked.
 *  `info.cold` is set when it had to be unpacked (for the Server-Timing header). */
function getPack(name, info) {
  var e = packs.get(name);
  if (e) { packs.delete(name); packs.set(name, e); return e.promise; }
  if (info) { info.cold = true; }
  e = { size: 0, promise: null };
  e.promise = caches.open(CACHE)
    .then(function (c) { return c.match(PACKS + name); })
    .then(function (res) {
      if (!res) { throw new Error('pack not held: ' + name); }
      return new Response(res.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    })
    .then(function (buf) { return parsePack(new Uint8Array(buf)); });
  packs.set(name, e);
  e.promise.then(function (p) { e.size = p.size; trim(); },
                 function () { if (packs.get(name) === e) { packs.delete(name); } });
  return e.promise;
}

function timing(t0, info, what) {
  return 'ordpar;desc="' + what + (info.cold ? ' (unpacked)' : ' (in memory)') + '";dur='
    + (Date.now() - t0);
}

function articleResponse(st, r, t0) {
  var info = {};
  return getPack(r.bundle.name, info).then(function (p) {
    var span = p.index.get(r.id);
    if (!span) { return null; }
    var text = new TextDecoder().decode(p.body.subarray(span[0], span[1]));
    return new Response(restore(text, st.m), { headers: {
      'Content-Type': TYPES.html, 'X-Ordpar-Offline': r.bundle.name,
      'Server-Timing': timing(t0, info, 'bundle') } });
  });
}

function fileResponse(st, path, status, t0) {
  var f = st.files[path], pk = f && st.byGroup[f.pack], info = {};
  if (!pk) { return Promise.resolve(null); }
  return getPack(pk.name, info).then(function (p) {
    var span = p.index.get(path);
    if (!span) { return null; }
    return new Response(p.body.slice(span[0], span[1]), { status: status || 200, headers: {
      'Content-Type': typeOf(path), 'X-Ordpar-Offline': pk.name,
      'Server-Timing': timing(t0 || Date.now(), info, 'pack') } });
  });
}

function notice(path, held) {
  return new Response(noticeHtml(path, held), { status: 503, headers: {
    'Content-Type': TYPES.html, 'Cache-Control': 'no-store', 'X-Ordpar-Offline': 'notice' } });
}

function handle(req, url, navigate) {
  var t0 = Date.now();
  return getState().then(function (st) {
    var r = route(st, url, navigate);
    var held = Promise.resolve(null);
    if (r.kind === 'article') {
      held = articleResponse(st, r, t0);
    } else if (r.kind === 'file') {
      held = r.stale
        ? fetch(req).then(function (res) { return res.ok ? res : null; }, function () { return null; })
            .then(function (res) { return res || fileResponse(st, r.path, 200, t0); })
        : fileResponse(st, r.path, 200, t0);
    } else if (r.kind === 'shell404') {
      held = fileResponse(st, '/404.html', 404, t0);
    }
    return held.catch(function () { return null; }).then(function (res) {
      if (res) { return res; }
      return fetch(req).catch(function (err) {
        if (!navigate) { throw err; }
        var shell = st && r.fallback === 'shell404'
          ? fileResponse(st, '/404.html', 404, t0).catch(function () { return null; })
          : Promise.resolve(null);
        return shell.then(function (res) { return res || notice(url.pathname, !!st); });
      });
    });
  });
}

if (typeof ServiceWorkerGlobalScope !== 'undefined' && self instanceof ServiceWorkerGlobalScope) {
  // A new sw.js takes over at once: it is a router over the same stored copy, so there is no
  // old page state to protect, and waiting for every tab to close would keep a fix away.
  self.addEventListener('install', function () { self.skipWaiting(); });
  self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });

  // `site/offline.js` posts this after a download, an update's switch or a removal
  self.addEventListener('message', function (e) {
    if (e.data && e.data.type === 'ordpar-offline-changed') {
      statePromise = null;
      known = undefined;
      packs.clear();
      if (e.ports && e.ports[0]) {
        getState().then(function (st) { e.ports[0].postMessage({ held: !!st }); });
      }
    }
  });

  self.addEventListener('fetch', function (e) {
    var req = e.request;
    if (req.method !== 'GET') { return; }
    var url = new URL(req.url);
    if (url.origin !== self.location.origin) { return; }
    // the download's own requests, and the worker itself, always go to the network
    if (url.pathname.indexOf(PACKS) === 0 || url.pathname === '/sw.js') { return; }
    var navigate = req.mode === 'navigate';
    if (known === false && !navigate) { return; }   // no copy: nothing to answer from
    e.respondWith(handle(req, url, navigate));
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { parsePack: parsePack, restore: restore, prepare: prepare, route: route,
                     bundleFor: bundleFor, fileKey: fileKey, typeOf: typeOf, noticeHtml: noticeHtml,
                     WORD_PAGE: WORD_PAGE,
                     CACHE: CACHE, CURRENT: CURRENT, KEEP_BYTES: KEEP_BYTES };
}
