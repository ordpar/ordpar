/*! Ordpar — the sound icons: Ida's voice on the Norwegian texts (site decisions 159).
 * Spec: ordpar/docs/build-site.md § The audio (159).
 *
 * The build marks each voiced text whose clip is uploaded (`data-a`, `sitegen/audio.py`): the
 * headword's main form and each other spelling (160), a set phrase's term, a Norwegian definition line (`data-a="101"`: which
 * of its segments, the parts joined by ";" and a line break, have a clip), an example's quote.
 * This script turns every mark into a play button — a real <button class="ordpar-play"> after the
 * text, the speaker with two waves (our own drawing), named "Play" / "Spill av" by the site's
 * label classes (the English one `lang="en"`) — as the article is drawn: on the article page, in a
 * looked-up article (the word and form pages, the search's results, an opened list, History or
 * Favourites row: `scan`, from the page script's `ordparDefs`), and in a small article, nested or
 * not (`mount`, from `mini.js` `fill`, before its width is fitted). The inflection tables are
 * drawn in the browser, so their cells carry no mark; the paradigm island does (`data-a-cells`,
 * `sitegen/audio.py` `table_code`, site decisions 170): one character a form of the island, its
 * bits after which frames ("", "å ", "har ", "en ", "ei ", "et ") the form's text has a clip. A
 * cell's form gets a button where those keys hold its ruled text (`cells`; each form alone, "ei/en"
 * voiced "ei", the imperative without its "!"; never the participle table), as the article is
 * scanned, and the tables are fitted again (`ordparInflection.fit`). So every icon is drawn with
 * no request.
 *
 * The names: `/audio/<k>.json`, one file per 500 article ids (k = (id - 1) / 500, rounded down),
 * `{"<id>": {"<text>": "<16 hex>"}}`, a definition line's key led by a TAB; fetched from our own
 * host only when a recording is wanted (site decisions 170, Robin 2026-11-06): at a press, or when
 * the pointer rests on an icon where the Loading setting allows it (below) — never as an article
 * or a small article opens. Once per page life a file (`files`): a press while it is loading
 * plays once it is in; a file that fails is asked for again at the next press. A clip is
 * `https://ordpar-audio.ordpar.workers.dev/ordpar-<hex>.mp3` (the Worker, `ordpar/audio-worker/`),
 * played by a plain `Audio` element (no `fetch`: the Worker allows CORS for ordpar.no only).
 *
 * Loading early follows the setting "When a linked article or page is loaded" (`minifetch`, read
 * through `ordparAhead.mode`; site decisions 170, Robin 2026-11-06). Under `point` and `page`
 * (Robin, 2026-11-02): a `preconnect` to the Worker as an article with an icon opens (no request),
 * and when the mouse pointer has RESTED on an icon for `REST_MS` (mini.js's links' rule) without
 * moving — never for a pointer passing over, never on touch (a tap plays) — the block's names
 * file, then the one clip under the pointer: one request of the account's 100,000 a day each,
 * shared with the receiver. The press then plays that element, so it asks for nothing more. Under
 * `click` nothing is loaded and nothing connected before a press: no `preconnect`, no names file,
 * no clip. Nothing else here asks the Worker for a clip before a press (an element with
 * `preload = 'auto'` is made only by the press, `take`).
 *
 * Playing: one clip at a time; a press on another icon stops the one playing; a second press on
 * the same icon stops it (its name says "Stop" / "Stopp" while it plays). A button with several
 * clips plays them in turn, 300 ms apart (the audio session's decisions 23). The speed is the
 * setting `audiospeed` — "As recorded" (1) or "90%" (0.9) — as `playbackRate`, the pitch kept
 * (`preservesPitch`). A clip that cannot play — offline (the service worker leaves other origins
 * to the network), a failed names file, a name the file lacks, an error — stops, and the icon
 * shows `ordpar-play-failed` (faded) for 1.5 s; nothing else happens.
 *
 *   window.ordparAudio = { scan, mount, stop, names, norm, ruled, tableKeys, last, REST_MS, WORKER }
 */
(function (global) {
  'use strict';

  var doc = global.document;
  if (!doc) { return; }
  var WORKER = 'https://ordpar-audio.ordpar.workers.dev/';
  var NAMES = '/audio/';
  var PER = 500;               // article ids to a names file (`sitegen/audio.py` PER)
  var DEF = '\t';              // a definition line's key in a names file
  var GAP = 300;               // between the clips of one button (the audio session's decisions 23)
  var REST_MS = 150;           // mini.js REST_MS: the pointer has to stand still this long
  var FAIL_MS = 1500;
  var SPEEDS = { recorded: 1, '90': 0.9 };
  // the tables' mark (`sitegen/audio.py` FRAMES and CELL_CODE): a form's character, its frame bits
  var FRAMES = ['', '\u00e5 ', 'har ', 'en ', 'ei ', 'et '];
  var CODE = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_';
  // the speaker with two waves (the style lab's shape a; our own drawing)
  var SVG = '<svg class="ordpar-play-i" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path d="M3 9h4l5-4v14l-5-4H3z" fill="currentColor"/>' +
    '<path d="M15.5 8.5a5 5 0 0 1 0 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>' +
    '<path d="M18.5 5.5a9.2 9.2 0 0 1 0 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  // the button's name in both label languages (site decisions 152), the sheet showing one
  var WORDS = { play: ['Play', 'Spill av'], stop: ['Stop', 'Stopp'] };

  function norm(t) { return String(t == null ? '' : t).replace(/\s+/g, ' ').trim(); }
  /** A table form's text as voiced: "ei/en tå" -> "ei tå", "vær!" -> "vær" (decisions 17). */
  function ruled(t) { return norm(t).replace(/^ei\/en /, 'ei ').replace(/!$/, ''); }

  function setting(key, def) {
    var S = global.ordparShell, v = null;
    if (S && S.getSetting) { try { return S.getSetting(key); } catch (e) { /* fall through */ } }
    try { v = typeof global.ordparRead === 'function' ? global.ordparRead(key) : global.localStorage.getItem(key); } catch (e) { v = null; }
    return v == null ? def : v;
  }
  function rate() { return SPEEDS[setting('audiospeed', 'recorded')] || 1; }

  /* ------------------------------------------------------------- the names */

  var files = Object.create(null);     // k -> Promise<object|null>

  function fileOf(id) { return Math.floor((id - 1) / PER); }
  function namesFile(k) {
    if (!files[k]) {
      var p = global.fetch ? global.fetch(NAMES + k + '.json', { credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) { throw new Error(String(r.status)); } return r.json(); })
        : Promise.reject(new Error('no fetch'));
      files[k] = p.catch(function () { delete files[k]; return null; });   // retried next time
    }
    return files[k];
  }
  /** The article's names: `{key: hex}`, `{}` for an article with none, null when the file failed. */
  function names(id) {
    return namesFile(fileOf(id)).then(function (f) { return f ? (f[String(id)] || {}) : null; });
  }
  function urlOf(entry, key) { var h = entry && entry[key]; return h ? WORKER + 'ordpar-' + h + '.mp3' : null; }

  var connected = false;
  function preconnect() {
    if (connected || !doc.head) { return; }
    connected = true;
    var l = doc.createElement('link');
    l.rel = 'preconnect';
    l.href = WORKER.replace(/\/$/, '');      // no crossorigin: an <audio> request is a plain one
    doc.head.appendChild(l);
  }

  /* ------------------------------------------------------------- the buttons */

  function button(keys, id) {
    var b = doc.createElement('button');
    b.type = 'button';
    b.className = 'ordpar-play';
    b.innerHTML = SVG + '<span class="ordpar-visually-hidden" data-nosnippet>' +
      '<span class="ordpar-l-en" lang="en">' + WORDS.play[0] + '</span>' +
      '<span class="ordpar-l-nb" lang="nb">' + WORDS.play[1] + '</span></span>';
    b._keys = keys;
    b._id = id;
    return b;
  }
  function after(node, b) { node.parentNode.insertBefore(b, node.nextSibling); }

  var HIDE = '.ordbok-xpeek, .sr-only, .ordpar-visually-hidden, .ordpar-play';
  /** The words a reader sees in `nodes` (peeks, hidden readings and our buttons out), as the build reads them. */
  function textOf(nodes, drop) {
    var box = doc.createElement('div');
    for (var i = 0; i < nodes.length; i++) { box.appendChild(nodes[i].cloneNode(true)); }
    var q = box.querySelectorAll(HIDE + (drop ? ', ' + drop : ''));
    for (var j = 0; j < q.length; j++) { if (q[j].parentNode) { q[j].parentNode.removeChild(q[j]); } }
    return norm(box.textContent);
  }

  /** One marked element's buttons. -> the number added. */
  function place(el, id) {
    var cls = el.classList, b, n;
    if (cls.contains('ordbok-lemma')) {
      // the headword's main form: after its homograph numeral and the screen readers' reading
      // ("være II"), outside the looked-up article's headword link
      var at = el;
      for (n = el.nextSibling; n; n = n.nextSibling) {
        if (n.nodeType === 3 && !n.data.trim()) { continue; }
        if (n.nodeType === 1 && (n.classList.contains('ordbok-homograph') || n.classList.contains('sr-only'))) { at = n; continue; }
        break;
      }
      var link = at.parentNode && at.parentNode.closest ? at.parentNode.closest('a') : null;
      // no headword is a link on the site (a looked-up article's neither, `lookup.js`, site
      // decisions 160); should one ever hold several spellings, an icon cannot sit inside it,
      // so only the first spelling's goes after it
      if (link && link.querySelector('.ordbok-lemma') !== el) { return 0; }
      b = button([textOf([el])], id);
      after(link || at, b);
      return 1;
    }
    if (cls.contains('ordbok-expr-term')) {
      // inside the term, a block (`ordbok_gen.py`): beside it the icon fell to the next line
      el.appendChild(button([textOf([el])], id));
      return 1;
    }
    if (cls.contains('ordbok-def')) {
      // each segment the page joins with ";" and a line break, its own clip and its own icon
      var bits = el.getAttribute('data-a') || '', segs = [], cur = [], added = 0;
      Array.prototype.forEach.call(el.childNodes, function (k) {
        var prev = cur.length ? cur[cur.length - 1] : null;
        if (k.nodeName === 'BR' && prev && prev.nodeType === 3 && /;\s*$/.test(prev.data)) { segs.push({ nodes: cur, br: k }); cur = []; } else { cur.push(k); }
      });
      segs.push({ nodes: cur, br: null });
      segs.forEach(function (s, i) {
        if (bits && bits.charAt(i) !== '1') { return; }
        var t = norm(textOf(s.nodes).replace(/;\s*$/, ''));
        if (!t) { return; }
        var bb = button([DEF + t], id);
        if (s.br) { el.insertBefore(bb, s.br); } else { el.appendChild(bb); }
        added++;
      });
      return added;
    }
    // an example's quote: the button before its explanation ("– …"), which is not voiced
    var expl = null;
    for (n = el.firstChild; n; n = n.nextSibling) { if (n.classList && n.classList.contains('ordbok-exexpl')) { expl = n; } }
    b = button([textOf([el], '.ordbok-exexpl')], id);
    if (expl) { el.insertBefore(b, expl); } else { el.appendChild(b); }
    return 1;
  }

  /** The marks in `root` (an article, or a small article's box) turned into buttons, named with
   *  article `id`'s names; a mark inside a small article opened in `root` is that box's. */
  function marks(root, id) {
    var home = root.closest ? root.closest('.ordbok-xmini') : null, n = 0;
    var all = root.querySelectorAll('[data-a]');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (el._a || el.closest('.ordbok-xmini') !== home) { continue; }
      el._a = 1;
      n += place(el, id);
    }
    return n;
  }

  /* ------------------------------------------------------------- the tables */

  var PART = null;
  function participleHeads() {
    if (PART) { return PART; }
    PART = [];
    var I = global.ordparInflection || {};
    [I.STRINGS, I.NB_STRINGS].forEach(function (s) {
      if (!s) { return; }
      ['perfectParticiple', 'presentParticiple'].forEach(function (k) { if (s[k]) { PART.push(norm(s[k]).toLowerCase()); } });
    });
    return PART;
  }
  /** A cell of a voiced table: not the participle table (wide), nor its sections (narrow). */
  function voicedCell(td) {
    var t = td.closest('table');
    if (!t || td.classList.contains('ordpar-unknown')) { return false; }
    if (t.classList.contains('ordpar-infl--wide')) { return !t.classList.contains('ordpar-infl--participle'); }
    var body = td.closest('tbody'), g = body && body.querySelector('th.ordpar-th-group');
    if (!g) { return true; }
    var gt = norm(g.textContent).toLowerCase();
    return !participleHeads().some(function (k) { return gt.indexOf(k) >= 0; });
  }
  /** The icon after `last`, a narrow table's variant's last node, held to it: the form's last word
   *  (or its "!") and the icon in one unbroken `ordpar-play-unit` span, so a squeezed narrow cell
   *  never puts the icon on a line of its own (the wide table's `ordpar-form` span does this there).
   *  The text is split, never changed: the cell reads the same. */
  function bind(last, b) {
    var tail = last, m = last.nodeType === 3 ? /\S+\s*$/.exec(last.data) : null;
    if (m && m.index > 0) { tail = last.splitText(m.index); }
    var u = doc.createElement('span');
    u.className = 'ordpar-play-unit';
    tail.parentNode.insertBefore(u, tail);
    u.appendChild(tail);
    u.appendChild(b);
  }
  /** Every word form of a compact paradigm island, in order, once (`sitegen/audio.py` `island_forms`). */
  function islandForms(data) {
    var seen = Object.create(null), out = [];
    (Array.isArray(data) ? data : []).forEach(function (lem) {
      (Array.isArray(lem) ? lem.slice(1) : []).forEach(function (par) {
        (Array.isArray(par) ? par.slice(1) : []).forEach(function (f) {
          if (typeof f === 'string' && f.trim() && !seen[f]) { seen[f] = 1; out.push(f); }
        });
      });
    });
    return out;
  }
  /** The texts the tables in `root` (not a small article's inside it) have a clip for, read from
   *  their islands' `data-a-cells` (`sitegen/audio.py` `table_keys`): `{text: 1}`, null for none. */
  function tableKeys(root) {
    var home = root.closest ? root.closest('.ordbok-xmini') : null, keys = null;
    var isl = root.querySelectorAll('script[data-a-cells]');
    for (var i = 0; i < isl.length; i++) {
      var s = isl[i], data;
      if (s.closest('.ordbok-xmini') !== home) { continue; }
      try { data = JSON.parse(s.textContent || ''); } catch (e) { continue; }
      var forms = islandForms(data), code = s.getAttribute('data-a-cells') || '';
      for (var j = 0; j < forms.length && j < code.length; j++) {
        var v = CODE.indexOf(code.charAt(j));
        for (var k = 0; v > 0 && k < FRAMES.length; k++) {
          if (v >> k & 1) { (keys = keys || Object.create(null))[norm(FRAMES[k] + forms[j])] = 1; }
        }
      }
    }
    return keys;
  }
  /** Each table form in `root` whose text `keys` hold (`tableKeys`) gets its button. */
  function cells(root, id, keys) {
    var home = root.closest ? root.closest('.ordbok-xmini') : null, added = 0;
    var tds = root.querySelectorAll('.ordpar-inflection td');
    for (var i = 0; i < tds.length; i++) {
      var td = tds[i];
      if (td._a || td.closest('.ordbok-xmini') !== home) { continue; }
      td._a = 1;
      if (!voicedCell(td)) { continue; }
      var vars = [], cur = [];
      Array.prototype.forEach.call(td.childNodes, function (k) {
        if (k.nodeType === 3 && /^\s*,\s*$/.test(k.data)) { if (cur.length) { vars.push(cur); } cur = []; } else { cur.push(k); }
      });
      if (cur.length) { vars.push(cur); }
      vars.forEach(function (v) {
        var t = ruled(textOf(v));
        if (!t || !keys[t]) { return; }
        var b = button([t], id);
        // inside the wide table's unbroken `ordpar-form` span, so the icon never parts from its form
        var host = v.length === 1 && v[0].nodeType === 1 && v[0].classList.contains('ordpar-form') ? v[0] : null;
        if (host) { host.appendChild(b); } else { bind(v[v.length - 1], b); }
        added++;
      });
    }
    if (added && global.ordparInflection && global.ordparInflection.fit) {
      try { global.ordparInflection.fit(root); } catch (e) { /* the module's own bug */ }
    }
    return added;
  }

  /* ------------------------------------------------------------- where an article shows */

  function idOf(art) {
    var h = art.querySelector('.ordpar-hw[id]'), m = h && /^r(\d+)-hw$/.exec(h.id);
    if (m) { return +m[1]; }
    var host = art.closest('[data-id]'), v = host && host.getAttribute('data-id');
    if (v && /^\d+$/.test(v)) { return +v; }
    v = doc.documentElement.getAttribute('data-article-id');
    return v && /^\d+$/.test(v) ? +v : null;
  }
  /** Every article in `scope` (default the document), not a small article's: its marks and its
   *  tables' forms (`tableKeys`) turned into buttons, with no request; the Worker preconnected
   *  unless the setting says nothing before a press (`ahead`). The names wait for a press. */
  function scan(scope) {
    var arts = (scope || doc).querySelectorAll('.ordpar-article');
    for (var i = 0; i < arts.length; i++) {
      var art = arts[i];
      if (art.closest('.ordbok-xmini')) { continue; }
      var id = idOf(art);
      if (!id) { continue; }
      var n = marks(art, id), keys = tableKeys(art);
      if (keys) { n += cells(art, id, keys); }
      if ((n || art.querySelector('[data-a], .ordpar-play, .ordpar-inflection')) && ahead()) { preconnect(); }
    }
  }
  /** A small article's box (`mini.js` `fill`): its marks, named with its target `id`'s names,
   *  and its header word's button where the word is the target's main form (`art`, the target's
   *  parsed page: its headword's mark); the Worker preconnected as in `scan`, the names waiting
   *  for a press. Before the box is fitted. */
  function mount(box, id, art) {
    if (!box || !id) { return 0; }
    var n = marks(box, id);
    var hw = box.querySelector('.mini-head .mini-hw'), lem = art && art.querySelector('.ordpar-hw .ordbok-lemma[data-a]');
    if (hw && lem && !hw._a) {
      hw._a = 1;
      var main = textOf([lem]), word = norm(hw.textContent).replace(/\s*\([IVX]+(?:,\s*\d+)?\)$/, '');
      if (word === main) { after(hw, button([main], id)); n++; }
    }
    if (n && ahead()) { preconnect(); }
    return n;
  }

  /* ------------------------------------------------------------- playing */

  var cur = null;                      // {btn, urls, i, el, t}
  var pre = null;                      // the rested-on clip: {url, el}
  var kept = [];                       // the last clips played: [{url, el}], newest last
  var info = null;                     // the last clip asked for, for the tests (`last`)

  function label(b, words) {
    var en = b.querySelector('.ordpar-l-en'), nb = b.querySelector('.ordpar-l-nb');
    if (en) { en.textContent = words[0]; }
    if (nb) { nb.textContent = words[1]; }
  }
  function state(b, on) {
    b.classList.toggle('ordpar-playing', on);
    label(b, on ? WORDS.stop : WORDS.play);
  }
  function stop() {
    var c = cur;
    cur = null;
    if (!c) { return; }
    clearTimeout(c.t);
    if (c.el) { try { c.el.pause(); } catch (e) { /* gone */ } c.el.onended = c.el.onerror = null; }
    state(c.btn, false);
  }
  function fail(b) {
    if (cur && cur.btn === b) { stop(); }
    b.classList.add('ordpar-play-failed');
    setTimeout(function () { b.classList.remove('ordpar-play-failed'); }, FAIL_MS);
  }
  /** The element for `url`: the rested-on one, a recently played one, or a new one. */
  function take(url) {
    if (pre && pre.url === url) { var p = pre.el; pre = null; keep(url, p); return p; }
    for (var i = 0; i < kept.length; i++) { if (kept[i].url === url) { return kept[i].el; } }
    var a = new global.Audio();
    a.preload = 'auto';
    a.src = url;
    keep(url, a);
    return a;
  }
  function keep(url, el) {
    kept = kept.filter(function (k) { return k.url !== url; });
    kept.push({ url: url, el: el });
    if (kept.length > 8) { kept.shift(); }
  }
  function speed(a) {
    var r = rate();
    a.defaultPlaybackRate = r;
    a.playbackRate = r;
    a.preservesPitch = true;
    a.webkitPreservesPitch = true;
    a.mozPreservesPitch = true;
  }
  function next(c) {
    if (cur !== c) { return; }
    if (c.i >= c.urls.length) { stop(); return; }
    var url = c.urls[c.i++], a = take(url);
    c.el = a;
    info = { src: url, el: a };
    speed(a);
    a.onended = function () {
      if (cur !== c) { return; }
      if (c.i < c.urls.length) { c.t = setTimeout(function () { next(c); }, GAP); } else { stop(); }
    };
    a.onerror = function () { if (cur === c) { fail(c.btn); } };
    try { a.currentTime = 0; } catch (e) { /* not loaded yet */ }
    var p = a.play();
    if (p && p.catch) { p.catch(function (err) { if (cur === c && !(err && err.name === 'AbortError')) { fail(c.btn); } }); }
  }
  function press(b) {
    if (cur && cur.btn === b) { stop(); return; }          // a second press stops it
    stop();
    var c = cur = { btn: b, i: 0 };
    state(b, true);
    names(b._id).then(function (entry) {
      if (cur !== c) { return; }
      var urls = (b._keys || []).map(function (k) { return urlOf(entry, k); });
      if (!entry || !urls.length || urls.indexOf(null) >= 0) { fail(b); return; }
      c.urls = urls;
      next(c);
    });
  }
  /** May a clip be loaded before a press? The setting "When a linked article or page is loaded"
   *  (`minifetch`) as `ahead.js` reads it (`ordparAhead.mode`, the one reading: the visit's value,
   *  the default, the data saver): under `click` nothing is loaded before a press (site decisions
   *  170). Without ahead.js (both bundles carry it), the setting read here, `point` its default. */
  function ahead() {
    var A = global.ordparAhead, m = null;
    if (A && typeof A.mode === 'function') { try { m = A.mode(); } catch (e) { m = null; } }
    if (m == null) { m = setting('minifetch', 'point'); }
    return m !== 'click';
  }

  /** The clip of the button the pointer rests on, loaded ahead (only that one), unless the
   *  setting says nothing before a press (`ahead`). */
  function preload(b) {
    if (!b.isConnected || (cur && cur.btn === b) || !ahead()) { return; }
    names(b._id).then(function (entry) {
      var url = urlOf(entry, (b._keys || [])[0]);
      if (!url || (pre && pre.url === url)) { return; }
      for (var i = 0; i < kept.length; i++) { if (kept[i].url === url) { return; } }
      if (pre) { try { pre.el.removeAttribute('src'); pre.el.load(); } catch (e) { /* gone */ } }
      var a = new global.Audio();
      a.preload = 'auto';
      a.src = url;
      try { a.load(); } catch (e) { /* the browser loads it on play */ }
      pre = { url: url, el: a };
    });
  }

  doc.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('button.ordpar-play') : null;
    if (!b) { return; }
    // the press is the button's alone: no link followed, no small article opened or closed,
    // no row of a list opened (every other listener sits below this one, or after it)
    e.preventDefault();
    e.stopPropagation();
    press(b);
  }, true);

  var restB = null, restT = null;
  function unrest() { clearTimeout(restT); restT = restB = null; }
  doc.addEventListener('pointermove', function (e) {
    if (e.pointerType !== 'mouse') { return; }
    var b = e.target && e.target.closest ? e.target.closest('button.ordpar-play') : null;
    if (!b) { if (restB) { unrest(); } return; }
    clearTimeout(restT);                    // each move restarts the wait
    restB = b;
    restT = setTimeout(function () { restT = null; preload(b); }, REST_MS);
  }, { passive: true });
  doc.addEventListener('pointerout', function (e) {
    if (restB && !(e.relatedTarget && restB.contains(e.relatedTarget))) { unrest(); }
  });

  global.ordparAudio = {
    scan: scan, mount: mount, stop: stop, names: names, norm: norm, ruled: ruled, rate: rate,
    tableKeys: tableKeys,
    playing: function () { return cur ? cur.btn : null; },
    /** The last clip asked for: its address and the element's state (for the tests). */
    last: function () {
      if (!info) { return null; }
      var a = info.el;
      return { src: info.src, readyState: a.readyState, duration: a.duration, paused: a.paused,
        currentTime: a.currentTime, playbackRate: a.playbackRate, preservesPitch: a.preservesPitch,
        error: a.error ? a.error.code : null };
    },
    REST_MS: REST_MS, WORKER: WORKER, PER: PER
  };

  if (doc.readyState === 'loading') { doc.addEventListener('DOMContentLoaded', function () { scan(); }); } else { scan(); }
}(typeof globalThis !== 'undefined' ? globalThis : this));
