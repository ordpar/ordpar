/*! Ordpar — a cross-reference's mini, made from the target's own page (site decisions 80).
 * Spec: ordpar/docs/build-site.md § Cross-references and the small article.
 *
 * Every cross-reference on a page is a plain link to its target's page (`/bm-en/<id>/`, with
 * `#def<N>` for one sense) and its hover peek (`sitegen/face.py` `_link`); without script the
 * link navigates. This script upgrades every such link — on an article page, in the search
 * page's lifted articles and in an opened list-view row alike (one listener on the document) —
 * into the mini control:
 *
 *   click   fetches the target's page (the browser's HTTP cache online, the service worker's
 *           bundles offline; `ordparSearch.fetchArticle` where the page has it, so the search
 *           page's results and the minis share one fetch), parses it (DOMParser), takes the
 *           article (`.ordpar-article`) and CUTS the mini from its senses (`cut`), then places
 *           it below the word inside the window (`window.ordparPlace`, decisions 69). A failed
 *           fetch navigates to the page instead. A second click, the backdrop or Escape closes.
 *   header  the link's visible words as the headword link (decisions 78's look), " — " and the
 *           peek's gloss; for an English partner word the two are swapped, so the header is
 *           always the Norwegian face, then the English (as the inlined minis had it).
 *   cache   every parsed page is kept for the page's life.
 *
 * What the mini keeps (`cut`): a `#def<N>` link its sense, with its subsenses (a subsense's
 * anchor: its parent sense, the subsenses with it, as the deck's mini does — or the subsense
 * alone where the parent has no definition of its own and no other subsense); an anchor the
 * page lacks, or a link to the whole article, every sense. Everything outside the senses goes.
 * `minicontent` = full (default): each kept sense whole, every subsense and compound list;
 * slim: the deck's mini rules (`scripts/mini.py`) — subsenses in a whole-article mini of several
 * senses only under a sense with no definition of its own, compound lists only on a unit with
 * no example. Both: at most `EX_BUDGET` examples in all, at least one a unit (`allocate`).
 * A page with no senses: its etymology and set phrases (one example each), or its "not
 * defined" note. Each kept line pair becomes a `mini-pair`, so the setting `mini` (not `defs`)
 * decides its languages, as it did for the inlined minis (`page.SITE_CSS`); ids are dropped.
 * Under `layout = ordbokene` (decisions 87) the page script's `ordparExHeads` then puts the
 * "Example" heading before each kept sense's own examples, as on the article; and under
 * `examples = no` (decisions 111) its `ordparExCues` puts the "Show English" cue before each kept
 * example's English, which the sheet hides until the cue is clicked, as on the article. The
 * kept texts' sound icons (site decisions 159) come along as the target page's marks (`data-a`);
 * `ordparAudio.mount` (`audio.js`) makes them buttons, named with the target's own names, before
 * the box is fitted, and a click on one plays it and does nothing else (no box closed).
 *
 * When to fetch (`minifetch`): point (default) — when the pointer has rested on a link for
 * `REST_MS` without moving (a pointer crossing the page fetches nothing), and on a touch; click
 * — on the click; page — every target, one at a time in idle time after the page has loaded
 * (and after the search page inserts articles: `scan`, called from `ordparDefs`), except with
 * the browser's data saver on, where it is `click`. `xref` = page: nothing is upgraded, a click
 * navigates (decisions 34's setting). Since decisions 92 the setting governs all loading ahead
 * (`ahead.js`): the mode is `ordparAhead.mode()` (its default included) and `page`'s queue is
 * `ordparAhead.queue`, shared with the list view's articles, where ahead.js is loaded (every
 * page's bundle); this file's own reading and queue stay for a page without it. The hover's
 * first Norwegian definition (`nbPeek`) follows it too: under `click` it fetches no `snip/` file
 * (site decisions 185).
 *
 * The width on a computer (`(hover:hover) and (pointer:fine)`; decisions 80, Robin 2026-10-22: the
 * style lab's row 7, "Fit-to-height <=36rem"; row 6's 32rem until the same day): the sheet lets
 * the box shrink to its content between a floor of 12rem and a ceiling of
 * min(36rem, max(19rem, 50vw), 100vw - 1rem) (`page.SITE_CSS`), which holds without script; `fit` then takes the NARROWEST width with the same content height as
 * at the ceiling (`narrowest`: a binary search over whole pixels, 1 px of tolerance), all in one
 * task before paint, and again on a window resize and when a class on <html> changes (a setting:
 * the languages, the spacing, the scrolling, the formula and etymology lines). The floor and the
 * ceiling are read from the sheet itself (the box at width 0 and at a huge width), so the numbers
 * live in one place. On a phone the box keeps the deck's 19rem and `fit` sets nothing.
 *
 * A small article inside a small article (site decisions 139, Robin 2026-10-26, built from the
 * nested-mini lab; four choices since site decisions 147, Robin 2026-10-29: "A top link inside a
 * small article should open its small article in a second box. But a link inside the second box
 * should open in-place. This will be the new default"): a link inside an open mini is upgraded
 * too, as the setting `nestminis` says (`target`, `depthOf`). Two ways a link can open, and the
 * choice says from which box on a link changes the box it is in (`inPlaceAt`):
 *   a box    a new box (`.ordpar-mnest`) below its word inside the box it is in. It hangs in that
 *            box, beside its `.mini`, `position:fixed` (`placeNested`: below its word, or above it
 *            where the room below is short (165), kept in the window as decisions 69 keeps the
 *            first, following its word on every scroll, hidden
 *            while its word is scrolled out of its box) — not in its word's line, where the line's
 *            rules (`.mini-pair>span[lang=nb] .ordbok-xword`: no underline, no pointer) would reach
 *            every link in it. Opened from the keyboard, the focus moves to its headword (it is not
 *            next to its word in the page's order).
 *   a step   the box's content swaps to the new word (`step`), with a line at its top, "← word"
 *            (`backLine`: a button, "Back to word"; the word as the header draws its headword),
 *            that steps back one word at a time (`stepBack`; the word stepped from comes back at
 *            the box's own scroll position). Each box keeps its own steps (`c.steps`), so the same
 *            code serves the first box and a second one.
 *   inplace  every link inside a box is a step in the first box.
 *   second   (default) a link in the first box opens a second box; a link inside the second box
 *            is a step in it.
 *   stacked  every link opens one more box, over the one before.
 *   off      depth one: a link in a mini keeps its peek, and a click opens its page.
 * No limit in any (decisions 147: the second boxes' limit went). The open boxes are a
 * chain (`chain`, from the page's own word inward): Escape steps back in the deepest box where it
 * has steps, else closes it, the focus back on its word; a click inside a box closes the boxes
 * nested in it (`insideClick`); the backdrop closes all; the same word clicked again closes its own
 * box. Every level loads through `load`, so the search page's shared fetch and the offline copy
 * serve them as they serve the first. On the Anki deck (`window.ordparDeck`,
 * `deck/static/deck-pre.js`) a link in a mini is upgraded only where the card carries its target's
 * `<template id="ordpar-t-<id>">`, so a link whose target the note does not carry keeps today's
 * behaviour.
 *
 * Nothing done inside a box scrolls the page (decisions 147, Robin 2026-10-29: "interacting inside
 * the small article boxes should never scroll the main window"): opening, a step, a step back, the
 * back line, Escape, a click that closes, a box's content arriving. A step back puts back only the
 * box's own `scrollTop` (on a phone and with `miniscroll` off the box has no scroll of its own, so
 * the page stays where the reader left it). Every focus is `preventScroll`; the boxes are kept out
 * of the browser's scroll anchoring (`overflow-anchor: none` on each); and before a change that can
 * make the page shorter (a box's content swapped, a box closed) `hold` keeps the page at least as
 * tall as the bottom of what the window shows, so the browser never pulls it up — lowered again as
 * the reader scrolls up, so it never adds room below what was on screen.
 *
 * A peek inside a mini (site decisions 141, Robin 2026-10-26: "the mini stays the same size, but
 * the hover is still displayed in full while extending beyond its edge"): the mini's box scrolls,
 * so a peek placed in it by the sheet (`position:absolute` from its word) was cut off at the box's
 * edge. On hover (`peekFix`) it is drawn against the window instead (`.ordpar-pfix`:
 * `position:fixed`, so no scrolling box clips it), above its word as the sheet draws it, moved
 * left to stay 8 px inside the window (its arrow kept on the word, `--ordpar-peek-dx`, as the page
 * script does for the article's peeks), below the word where above would leave the window. Only
 * its place changes: whether it shows is still the sheet's (`peek`, `defs`, `emph`, `mini`).
 *
 *   window.ordparMinis = { scan, cut, allocate, header, norwegian, close, narrowest, fit,
 *     nestMode, inPlaceAt, depthOf, peekFix,    (the pure parts for the tests)
 *     load, target }   (ahead.js: a link this script opens a small article for, nested ones too, is
 *                       left to it — site decisions 180 — and under `page` loaded through `load`)
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var HREF = /^\/bm-en\/(\d+)\/(?:#(def\d+))?$/;
  var EX_BUDGET = 6;           // `scripts/mini.py` EX_BUDGET: examples in a mini, in all
  var REST_MS = 150;           // decisions 80: "the mouse actually has to stand still"
  // decisions 153: a set phrase's "Se:" line (`.ordpar-see`) in its small article — open for
  // Robin (entry 153); `false` (the default) leaves it out, as before. THE switch: one line
  var SEE_IN_MINI = false;

  /* --------------------------------------------------------------- settings */

  function setting(key, values, def) {
    var v = null;
    // site decisions 146: the visit's value where it has one (the head script's `ordparRead`)
    if (typeof global.ordparRead === 'function') { v = global.ordparRead(key); }
    else { try { v = global.localStorage.getItem(key); } catch (e) { /* private mode */ } }
    return values.indexOf(v) !== -1 ? v : def;
  }
  function navigates() { return setting('xref', ['mini', 'page'], 'mini') === 'page'; }
  function fetchMode() {
    // decisions 92: the setting governs all loading ahead now; ahead.js reads it (and its default)
    if (global.ordparAhead && global.ordparAhead.mode) { return global.ordparAhead.mode(); }
    var m = setting('minifetch', ['point', 'click', 'page'], 'point');
    var c = global.navigator && global.navigator.connection;
    return m === 'page' && c && c.saveData ? 'click' : m;
  }
  function slim() { return setting('minicontent', ['full', 'slim'], 'full') === 'slim'; }
  // decisions 139, 147: a link inside a mini — its mini in the same box, a second box then that box
  // (the default), a box of its own each time, or its page; no limit
  function nestMode() { return setting('nestminis', ['second', 'inplace', 'stacked', 'off'], 'second'); }
  /** From which depth a link inside a box changes the box it is in (a step) rather than opening a
   *  box (decisions 147): in place from the first box, `second` from the second, stacked never. */
  function inPlaceAt(mode) { return mode === 'inplace' ? 1 : mode === 'second' ? 2 : 0; }

  /* ------------------------------------------------------------------ links */

  function kid(n, c) {
    for (var k = n.firstChild; k; k = k.nextSibling) {
      if (k.classList && k.classList.contains(c)) { return k; }
    }
    return null;
  }

  /** How many minis a node sits inside (0 on the page itself; decisions 139). */
  function depthOf(n) {
    var d = 0;
    for (var p = n && n.parentNode; p && p.classList; p = p.parentNode) {
      if (p.classList.contains('ordbok-xmini')) { d++; }
    }
    return d;
  }

  /** The link this script opens a mini for -> {id, def, href, depth}, or null: a cross-reference
   *  (`.ordbok-xref > a.ordbok-xword`) to an article page; inside a mini only as `nestminis`
   *  allows (decisions 139, 147): always, with no limit, except off (depth one, as until 139).
   *  On the deck, inside a mini only where the card carries the target's template (the module
   *  comment). */
  function target(a) {
    if (!a || !a.classList || !a.classList.contains('ordbok-xword') || !a.closest) { return null; }
    var x = a.parentNode;
    if (!x || !x.classList || !x.classList.contains('ordbok-xref')) { return null; }
    var m = HREF.exec(a.getAttribute('href') || '');
    if (!m) { return null; }
    var d = a.closest('.ordbok-xmini') ? depthOf(a) : 0;
    if (d) {
      if (nestMode() === 'off') { return null; }
      if (d > chain.length) { return null; }                 // a mini this script did not open
      if (global.ordparDeck && !doc.getElementById('ordpar-t-' + m[1])) { return null; }
    }
    return { id: +m[1], def: m[2] || null, href: m[0], depth: d };
  }

  function linkOf(n) { return n && n.closest ? n.closest('a.ordbok-xword') : null; }

  /* ------------------------------------------------------------ fetch, cache */

  var pages = Object.create(null);     // id -> Promise<Element (.ordpar-article) | null>

  function fragmentOf(text) {
    var s = text.indexOf('<div class="ordbok'), e = text.indexOf('<footer class="ordpar-card-foot">', s);
    return s < 0 || e < 0 ? null : text.slice(s, e);
  }

  function fetchFragment(id) {
    var S = global.ordparSearch;
    if (S && S.fetchArticle) {
      return S.fetchArticle(id).then(function (got) { return got ? got.fragment : null; });
    }
    if (!global.fetch) { return Promise.resolve(null); }
    return global.fetch('/bm-en/' + id + '/', { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (text) { return text ? fragmentOf(text) : null; });
  }

  function parse(html) {
    if (!html || !global.DOMParser) { return null; }
    return new global.DOMParser().parseFromString(html, 'text/html').querySelector('.ordpar-article');
  }

  /** The target's article, fetched and parsed once per page view (a failure is retried). */
  function load(id) {
    if (pages[id]) { return pages[id]; }
    var p = fetchFragment(id).then(parse).catch(function () { return null; })
      .then(function (art) {
        if (!art) { delete pages[id]; }
        return art;
      });
    pages[id] = p;
    return p;
  }

  /* -------------------------------------------------------------------- cut */

  function el(tag, cls) {
    var n = doc.createElement(tag);
    if (cls) { n.className = cls; }
    return n;
  }
  function has(n, c) { return !!(n && n.classList && n.classList.contains(c)); }
  function kids(n) {
    var out = [];
    for (var k = n.firstElementChild; k; k = k.nextElementSibling) { out.push(k); }
    return out;
  }
  function isComp(n) { return has(n, 'ordpar-comp') || (has(n, 'ordbok-sub') && !n.id); }
  function isDefLine(n) { return has(n, 'ordpar-pair') || (has(n, 'ordbok-def') && n.tagName === 'SPAN'); }

  /** The senses section of an article: the `<section>` holding `ol.ordbok-senses` or a solo
   *  sense's `div#def<N>` (`sitegen/article.py` `fragment`). */
  function sensesOf(art) {
    var secs = kids(art);
    for (var i = 0; i < secs.length; i++) {
      if (secs[i].tagName !== 'SECTION') { continue; }
      var ks = kids(secs[i]);
      for (var j = 0; j < ks.length; j++) {
        if ((ks[j].tagName === 'OL' && has(ks[j], 'ordbok-senses'))
            || (ks[j].tagName === 'DIV' && /^def\d/.test(ks[j].id))) { return ks[j]; }
      }
    }
    return null;
  }

  /** A sense's subsenses: its `div.ordbok-sub` that are not compound lists, and the items of a
   *  numbered `ol.ordbok-subsenses`. */
  function subsOf(sense) {
    var out = [];
    kids(sense).forEach(function (k) {
      if (has(k, 'ordbok-sub') && !isComp(k)) { out.push(k); }
      if (k.tagName === 'OL' && has(k, 'ordbok-subsenses')) { out = out.concat(kids(k)); }
    });
    return out;
  }
  function ownDef(unit) { return kids(unit).some(isDefLine); }
  function examples(unit) {
    var out = [];
    kids(unit).forEach(function (k) {
      if (k.tagName === 'UL' && has(k, 'ordbok-ex-list')) { out = out.concat(kids(k)); }
    });
    return out;
  }

  /** How many examples each unit shows (`scripts/mini.py` `_allocate_examples`): one each
   *  where it has any — never starved — then everyone's second, third… round-robin while the
   *  mini's total is under `EX_BUDGET`. `avail` is each unit's number of examples. (The deck
   *  grants extras only to examples with authored English; a page shows each example whole in
   *  its own languages, so here every example counts.) */
  function allocate(avail) {
    var counts = avail.map(function (n) { return n ? 1 : 0; });
    var total = counts.reduce(function (a, b) { return a + b; }, 0);
    for (var rank = 1; total < EX_BUDGET; rank++) {
      var granted = false;
      for (var i = 0; i < avail.length && total < EX_BUDGET; i++) {
        if (avail[i] > rank && counts[i] === rank) { counts[i]++; total++; granted = true; }
      }
      if (!granted) { break; }
    }
    return counts;
  }

  /** A sense's (or a subsense's) content, flush: its children in a plain `div`, so no list
   *  number and no subsense rule stand before it. */
  function flush(unit) {
    var d = el('div', 'ordpar-msense');
    for (var k = unit.firstChild; k; k = k.nextSibling) { d.appendChild(k.cloneNode(true)); }
    return d;
  }

  function trim(unit, n) {
    var exs = examples(unit);
    for (var i = n; i < exs.length; i++) { exs[i].parentNode.removeChild(exs[i]); }
    kids(unit).forEach(function (k) {
      if (k.tagName === 'UL' && has(k, 'ordbok-ex-list') && !k.firstElementChild) { unit.removeChild(k); }
    });
  }

  /** Line pairs become the mini's (`mini-pair`: the setting `mini` decides, `page.SITE_CSS`), any
   *  reveal cue goes, any opened example closes (its cue comes back, `ordparExCues`, decisions 111),
   *  and every id goes (they are the target page's, and would clash here). A set phrase's "Se:"
   *  line goes unless `SEE_IN_MINI` (decisions 153). */
  function finish(root) {
    if (!SEE_IN_MINI) {   // decisions 153: the "Se:" line stays on the page (`SEE_IN_MINI`)
      Array.prototype.forEach.call(root.querySelectorAll('.ordpar-see'), function (n) { n.parentNode.removeChild(n); });
    }
    var all = [root].concat(Array.prototype.slice.call(root.querySelectorAll('*')));
    all.forEach(function (n) {
      if (n.removeAttribute) { n.removeAttribute('id'); }
      if (has(n, 'ordpar-pair')) { n.classList.remove('ordpar-pair', 'ordpar-open'); n.classList.add('mini-pair'); }
      if (has(n, 'ordpar-open')) { n.classList.remove('ordpar-open'); }
    });
    Array.prototype.forEach.call(root.querySelectorAll('.ordpar-encue'), function (b) { b.parentNode.removeChild(b); });
    return root;
  }

  /** A page with no senses: its etymology, its set phrases with one example each (the deck's
   *  mini for a senseless row), or its "not defined" note. */
  function senseless(art, body) {
    kids(art).forEach(function (sec) {
      if (sec.tagName !== 'SECTION') { return; }
      // the pronunciation (decisions 123) is not a mini's: a mini is the senses, or this
      if (has(sec, 'ordbok-inline') && !has(sec, 'ordpar-pron') && !sec.querySelector('.ordbok-nodef')) {
        kids(sec).forEach(function (k) { if (k.tagName !== 'H3') { body.appendChild(k.cloneNode(true)); } });
      }
    });
    Array.prototype.forEach.call(art.querySelectorAll('.ordbok-expr'), function (x) {
      var c = x.cloneNode(true);
      Array.prototype.forEach.call(c.querySelectorAll('ul.ordbok-ex-list'), function (ul) {
        while (ul.children.length > 1) { ul.removeChild(ul.lastElementChild); }
      });
      body.appendChild(c);
    });
    if (!body.firstChild) {
      var nd = art.querySelector('.ordbok-nodef');
      if (nd) { body.appendChild(nd.cloneNode(true)); }
    }
    return body;
  }

  /**
   * The mini's body, cut from `art` (a parsed page's `.ordpar-article`) for the anchor `def`
   * (`'def3'`, or null for the whole article). `isSlim`: the slim rules. -> `div.ordpar-mbody`.
   */
  function cut(art, def, isSlim) {
    var body = el('div', 'ordpar-mbody');
    var top = sensesOf(art);
    if (!top) { return finish(senseless(art, body)); }
    var hit = def ? top.querySelector('#' + def) : null;
    if (!hit && def && top.id === def) { hit = top; }
    var root, senses, whole = !hit;
    if (hit) {
      // the sense the anchor is in: an item of the senses list, or the solo sense itself
      var sense = top;
      if (top.tagName === 'OL') {
        sense = hit;
        while (sense.parentNode !== top) { sense = sense.parentNode; }
      }
      // a subsense's anchor: its sense, unless that is only a frame for this one subsense
      if (sense !== hit && !ownDef(sense) && subsOf(sense).length === 1) { sense = hit; }
      root = flush(sense);
      senses = [root];
    } else if (top.tagName === 'OL') {
      root = top.cloneNode(true);
      senses = kids(root);
    } else {
      root = flush(top);
      senses = [root];
    }
    var units = [];
    senses.forEach(function (s) {
      if (isSlim && whole && senses.length > 1 && ownDef(s)) {
        // the card-80 rule: a whole-article mini of several senses keeps a sense's subsenses
        // only where the sense has no definition of its own
        kids(s).forEach(function (k) {
          if ((has(k, 'ordbok-sub') && !isComp(k)) || has(k, 'ordbok-subsenses')) { s.removeChild(k); }
        });
      }
      units.push(s);
      units = units.concat(subsOf(s));
    });
    if (isSlim) {
      // a compound list only where its unit has no example (`scripts/mini.py` `_comp_line`)
      units.forEach(function (u) {
        if (examples(u).length) { kids(u).forEach(function (k) { if (isComp(k)) { u.removeChild(k); } }); }
      });
    }
    var counts = allocate(units.map(function (u) { return examples(u).length; }));
    units.forEach(function (u, i) { trim(u, counts[i]); });
    body.appendChild(root);
    return finish(body);
  }

  /** Is the link's own word the Norwegian face? `markup._render_link` makes the visible word
   *  `<em>…</em>` exactly when the Norwegian side is visible, on either line of a pair: a
   *  Norwegian line's reference, a compound list's, and a Norwegian word MENTIONED on an English
   *  line (an etymology's "developed from *hus*") alike; an English partner word is never
   *  wrapped. The `lang` tags are not asked: a page built before 2026-10-22 tagged a mention's
   *  peek `nb` (`face.py` `_partner`), and `slim.drop_redundant_lang` drops an inherited one. */
  function norwegian(a) {
    var e = a.firstElementChild;
    return !!(e && e.tagName === 'EM' && !e.nextElementSibling &&
              e.textContent.trim() === a.textContent.trim());
  }

  /** The header line: the headword link (the link's own words) and " — " the gloss (its
   *  peek's). An English word (its peek the Norwegian face: a partner word) is swapped, so the
   *  header reads Norwegian, then English, whichever line the link was on — as from a
   *  Norwegian line's link.
   *
   *  Each half carries its own `lang` (site decisions 130, 2026-10-25), so neither depends on
   *  where the header is drawn (inside a Norwegian or an English line) nor on whether the
   *  mini's body, which tags the mini with the article's language, has arrived: the headword
   *  `nb` when it is the Norwegian face (the link's own word, or the peek after a swap), `en`
   *  only for an English word with no peek; the gloss always `en` (a Norwegian word's peek is
   *  its English, `face.py` `_link`; after a swap it is the English link's own word). */
  function header(a, href) {
    var peek = kid(a.parentNode, 'ordbok-xpeek');
    // a Norwegian-only page's link to one sense: its peek is the sense's English definition line,
    // which the mini's body shows, so the header is the headword alone (decisions 119, Robin
    // 2026-10-24: "the mini header has no English glosses")
    if (peek && peek.classList.contains('ordpar-nbdef')) { peek = null; }
    var word = a.textContent.replace(/\s+/g, ' ').trim();
    var gloss = peek ? peek.textContent.replace(/\s+/g, ' ').trim() : '';
    var nb = norwegian(a);
    if (gloss && !nb) { var w = word; word = gloss; gloss = w; nb = true; }
    var head = el('div', 'mini-head'), hw = el('span', 'mini-hw'), link = el('a');
    hw.lang = nb ? 'nb' : 'en';
    link.href = href;
    link.textContent = word;
    hw.appendChild(link);
    head.appendChild(hw);
    if (gloss && gloss.indexOf(' \u00b7 ') < 0) {
      var one = head.appendChild(el('span', 'mini-gloss'));
      one.lang = 'en';
      one.textContent = ' \u2014 ' + gloss;
    } else if (gloss) {
      // the " \u00b7 " between glosses faded, in the gloss's weight (site decisions 116)
      var g = head.appendChild(el('span', 'mini-gloss'));
      g.lang = 'en';
      gloss.split(' \u00b7 ').forEach(function (part, i) {
        if (i) { g.appendChild(el('span', 'ordpar-gsep')).textContent = ' \u00b7 '; }
        g.appendChild(doc.createTextNode((i ? '' : ' \u2014 ') + part));
      });
    }
    return head;
  }

  /* ------------------------------------------------------------ open, close */

  var openX = null;

  function place(m) {
    if (typeof global.ordparPlace === 'function') {
      try { global.ordparPlace(m); } catch (e) { /* the page script's own bug */ }
    }
  }

  /* ------------------------------------------------------------------ width */

  var FINE = '(hover:hover) and (pointer:fine)';   // the sheet's query (the scrolling rule's too)

  function fine() {
    try { return !!(global.matchMedia && global.matchMedia(FINE).matches); } catch (e) { return false; }
  }

  /** The narrowest whole-pixel width in [lo, hi] whose height is within 1 px of the height at
   *  `hi` (decisions 80): `heightAt(w)` lays the box out at `w` and returns its content
   *  height. The floor itself where it already holds; else a binary search. Pure. */
  function narrowest(lo, hi, heightAt) {
    if (!(hi > lo)) { return hi; }
    var h = heightAt(hi);
    if (heightAt(lo) <= h + 1) { return lo; }
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (heightAt(mid) <= h + 1) { hi = mid; } else { lo = mid; }
    }
    return hi;
  }

  /** Fit an opened mini's width (`m`: its `.ordbok-xmini`) to its content, on a computer and once
   *  the content is in: the inline width cleared first, the sheet's floor and ceiling read as the
   *  box at width 0 and at a huge width (its `min-width` / `max-width` clamp them), then the
   *  narrowest width with the ceiling's `scrollHeight` (the full content, a scrolling box too).
   *  Every trial is a synchronous layout in this task, so no trial width is ever painted. */
  function fit(m) {
    var box = m ? kid(m, 'ordpar-fmini') : null;
    if (!box) { return; }
    box.style.width = '';
    if (!fine() || box.getAttribute('aria-busy') === 'true') { return; }
    box.style.width = '100000px';
    var hi = Math.floor(box.getBoundingClientRect().width);
    box.style.width = '0px';
    var lo = Math.ceil(box.getBoundingClientRect().width);
    if (!hi) { box.style.width = ''; return; }
    box.style.width = narrowest(Math.min(lo, hi), hi, function (w) {
      box.style.width = w + 'px';
      return box.scrollHeight;
    }) + 'px';
  }

  /** The open minis fitted again and placed (a resize, a setting's class on <html>): the first,
   *  then every nested one (decisions 139). */
  function refit() {
    if (!openX) { return; }
    var m = kid(openX, 'ordbok-xmini');
    if (m) { fit(m); place(m); }
    for (var i = 1; i < chain.length; i++) { fit(chain[i].m); placeNested(chain[i]); }
  }

  /* The open boxes (decisions 139), from the page's own word (0) inward: [{x, a, m, steps, tok}].
   * A box's `steps` (decisions 147: each box its own, the first under in place, the second under
   * `second`) hold the words stepped from in it: {nodes, lang, from, scroll} — the box's own
   * scrollTop as it was, put back by `stepBack` (the back line and Escape alike); never the page's
   * (decisions 147). `tok` counts the box's steps, so a late fetch for a step left is dropped. */
  var chain = [];

  function boxOf(n) {
    var m = n && n.closest ? n.closest('.ordbok-xmini') : null;
    for (var i = 0; i < chain.length; i++) { if (chain[i].m === m) { return chain[i]; } }
    return null;
  }

  /* Rule 3 (decisions 147): the page never moves for a box. A box hangs outside the page's flow,
   * but its height still counts in how far the page scrolls; swapped for a shorter content, or
   * closed, it would leave the window below the page's new end, and the browser would pull the
   * page up. So before such a change the page is held at least as tall as the bottom of what the
   * window shows (`min-height` on <html>: below the page's own height it does nothing), and the
   * scroll listener lowers the hold as the reader scrolls up, so it never adds room below what was
   * on screen. */
  var held = 0;
  function bottom() { return Math.ceil((global.pageYOffset || 0) + (global.innerHeight || 0)); }
  function hold() {
    var e = doc.documentElement;
    if (!e || !e.style) { return; }
    held = bottom();
    e.style.minHeight = held + 'px';
  }
  function unhold() {
    if (!held) { return; }
    var b = bottom();
    if (b < held) { held = b; doc.documentElement.style.minHeight = b + 'px'; }
  }

  /** Close the boxes from level `i` inward (0: every one). */
  function closeFrom(i) {
    if (chain.length > i) { hold(); }
    while (chain.length > i) {
      var c = chain.pop();
      c.tok++;
      if (c.ro) { c.ro.disconnect(); c.ro = null; }
      c.x.classList.remove('ordpar-mopen');
      c.a.setAttribute('aria-expanded', 'false');
      c.steps.forEach(function (s) { if (s.from) { s.from.setAttribute('aria-expanded', 'false'); } });
      c.steps = [];
      if (c.m.parentNode) { c.m.parentNode.removeChild(c.m); }     // a nested box: in its parent box
      var back = kid(c.x, 'ordbok-xback');
      if (back) { c.x.removeChild(back); }
    }
    if (!chain.length) { openX = null; }
  }
  function close() { closeFrom(0); }

  /** Place a box after a change: the first as the page script places it, a nested one below its word. */
  function put(c) {
    if (chain[0] === c) { place(c.m); } else { placeNested(c); }
  }

  /** A nested box (decisions 139, stacked) set below its word as the first is below its own (the
   *  sheet's `.ordbok-xmini{top:1.7em}` from the word's `.ordbok-xref`), kept inside the window as
   *  decisions 69 keeps the first (8 px from either edge); hidden while its word is scrolled out
   *  of the box it sits in. A fixed box adds nothing to the page's height, so the page cannot be
   *  scrolled to it: it is kept inside the window, top and bottom (site decisions 165, Robin
   *  2026-11-04: "Yes, open it above"). Below its word when it fits there (its content's height,
   *  under a computer's `min(70vh, 30rem)`); else, where there is more room above, ABOVE its word,
   *  its bottom the same gap above the word as its top is below it; else below. Its height is
   *  capped at the room on the side it takes (8 px from the window's edge), where it scrolls inside
   *  itself — no floor (until 165 it was never under 160 px, which ran it past the window's
   *  bottom). Its natural height is read from the box's `scrollHeight`, never by lifting the cap,
   *  which would reset the box's own scroll (this runs on every scroll). */
  function placeNested(c, keep) {
    var m = c.m, rs = c.a.getClientRects(), r = rs.length ? rs[0] : c.a.getBoundingClientRect();
    var em = parseFloat(global.getComputedStyle(c.x).fontSize) || 16;
    var top = Math.round(c.x.getBoundingClientRect().top + 1.7 * em);
    var W = doc.documentElement.clientWidth, H = global.innerHeight, G = 8;
    m.style.top = top + 'px';
    m.style.left = Math.round(r.left) + 'px';
    var w = m.getBoundingClientRect().width, left = Math.min(r.left, W - G - w);
    if (left < G) { left = G; }
    m.style.left = Math.round(left) + 'px';
    var host = c.x.closest('.ordpar-fmini'), hr = host ? host.getBoundingClientRect() : null;
    m.style.visibility = hr && (r.bottom < hr.top || r.top > hr.bottom) ? 'hidden' : '';
    var box = kid(m, 'ordpar-fmini');
    if (!box) { return; }
    // the box's frame: what its rendered height adds to its max-height (padding and border on a
    // content-box sheet) and what the `.ordbok-xmini` around it adds to that
    var cs = global.getComputedStyle(box), px = function (k) { return parseFloat(cs[k]) || 0; };
    var border = px('borderTopWidth') + px('borderBottomWidth');
    var frame = cs.boxSizing === 'border-box' ? 0 : border + px('paddingTop') + px('paddingBottom');
    var outer = Math.max(0, m.getBoundingClientRect().height - box.getBoundingClientRect().height);
    var need = box.scrollHeight + border;                    // the whole content, padding and border
    if (fine()) {
      var rem = parseFloat(global.getComputedStyle(doc.documentElement).fontSize) || 16;
      need = Math.min(need, Math.min(0.7 * H, 30 * rem) + frame);
    }
    need += outer;
    frame += outer;
    var gap = Math.max(0, top - r.bottom);
    var below = H - G - top, above = Math.floor(r.top - gap) - G;
    // the side is chosen when the box is placed on opening, on its content's arrival, on a step or
    // a resize, and KEPT while the page or a box scrolls (`keep`; Robin, 2026-11-04: "if they
    // opened above to begin with, they stay above"), the height capped at that side's room
    var up = keep && typeof c.up === 'boolean' ? c.up : need > below && above > below;
    c.up = up;
    var room = Math.max(0, Math.floor((up ? above : below) - frame));
    box.style.maxHeight = fine() ? 'min(70vh, 30rem, ' + room + 'px)' : room + 'px';
    if (up) { m.style.top = Math.round(r.top - gap - m.getBoundingClientRect().height) + 'px'; }
    m.classList.toggle('ordpar-mabove', up);
  }

  /** A nested box placed again whenever its height changes after it was placed (site decisions
   *  165): content arriving, a step in it, an example's English shown — so a box above its word
   *  keeps its bottom there; its side is kept (Robin, 2026-11-04: it does not turn on a scroll). */
  function watch(c) {
    if (typeof global.ResizeObserver !== 'function') { return; }
    var box = kid(c.m, 'ordpar-fmini');
    if (!box) { return; }
    // in the next frame: a placing inside the observer's own callback that changes the height again
    // would be the browser's "ResizeObserver loop" error
    var due = false, later = function (f) {
      return global.requestAnimationFrame ? global.requestAnimationFrame(f) : global.setTimeout(f, 16);
    };
    c.ro = new global.ResizeObserver(function () {
      if (due) { return; }
      due = true;
      // its side kept: a scroll that changes the cap changes the height, which must not turn it
      later(function () { due = false; if (chain.indexOf(c) > 0) { placeNested(c, true); } });
    });
    c.ro.observe(box);
  }

  /** The fetched page cut into a box (the first, a nested one, or a step in place). */
  function fill(m, box, art, t) {
    m.setAttribute('lang', art.getAttribute('lang') || 'en');
    box.appendChild(cut(art, t.def, slim()));
    // the layout closer to ordbokene.no (decisions 87): the "Example" headings, as the article's
    if (typeof global.ordparExHeads === 'function') {
      try { global.ordparExHeads(box); } catch (e) { /* the page script's own bug */ }
    }
    // the examples' English behind its cue (decisions 111), as the article's
    if (typeof global.ordparExCues === 'function') {
      try { global.ordparExCues(box); } catch (e) { /* the page script's own bug */ }
    }
    // the sound icons (site decisions 159, `audio.js`): its marks made buttons, named with the
    // target's names, before the width is fitted
    if (global.ordparAudio && global.ordparAudio.mount) {
      try { global.ordparAudio.mount(box, t.id, art); } catch (e) { /* the audio script's own bug */ }
    }
    box.removeAttribute('aria-busy');
    fit(m);                                                  // before placing: the width decides
  }

  /** The focus moved without moving the page (decisions 147): never a plain `focus()`, which
   *  scrolls the element into view; a browser that cannot keep the page leaves the focus where it is. */
  function focusOn(n) {
    if (!n || !n.focus) { return; }
    try { n.focus({ preventScroll: true }); } catch (e) { /* no focus rather than a moved page */ }
  }

  /** Open the mini for `a` (its target `t`); `keyboard`: opened by Enter, not a pointer. A link
   *  inside a mini (decisions 139, 147): a step in the box it is in from the depth `inPlaceAt`
   *  gives, else a box nested in the one it is in. */
  function open(a, t, keyboard) {
    var d = t.depth || 0, from = inPlaceAt(nestMode());
    if (d && from && d >= from && chain[d - 1]) { step(chain[d - 1], a, t); return; }
    closeFrom(d);                                            // 0: every box, as before 139
    var x = a.parentNode;
    var m = el('span', 'ordbok-xmini');
    m.style.overflowAnchor = 'none';                         // decisions 147: no anchor in a box
    if (d) { m.classList.add('ordpar-mnest'); }
    var box = el('div', 'mini ordpar-fmini');
    box.setAttribute('aria-busy', 'true');
    box.appendChild(header(a, t.href));
    m.appendChild(box);
    if (!d) {                                                // one backdrop: the first box's
      var back = el('span', 'ordbok-xback');
      back.setAttribute('aria-hidden', 'true');
      x.appendChild(back);
    }
    // a nested box goes into the box it opens from, beside that box's `.mini` (the module comment)
    if (d) { chain[d - 1].m.appendChild(m); } else { x.appendChild(m); }
    x.classList.add('ordpar-mopen');
    a.setAttribute('aria-expanded', 'true');
    var c = { x: x, a: a, m: m, steps: [], tok: 0 };
    chain.push(c);
    if (!d) { openX = x; }
    put(c);
    if (d) { watch(c); }                                     // decisions 165: placed again on a new height
    if (d && keyboard) { focusOn(box.querySelector('.mini-hw a')); }
    load(t.id).then(function (art) {
      if (chain.indexOf(c) < 0 || !m.parentNode) { return; }           // closed, or another opened
      if (!art) { closeFrom(d); global.location.href = t.href; return; }
      fill(m, box, art, t);
      put(c);
    });
  }

  /* A step (decisions 139, 147): a box's content swapped for the new word, "← word" above it —
   * the first box under in place, the second under `second`; the steps are the box's own. */

  /** The line back to the word stepped from: a button, "Back to <word>", the word drawn as the
   *  header draws its headword (`.mini-hw`: its weight, its colour under `minihw`, its homograph
   *  numeral as it stands in the header) — `hw` the header's `.mini-hw`. */
  function backLine(hw) {
    var word = hw ? hw.textContent.replace(/\s+/g, ' ').trim() : '';
    var b = doc.createElement('button');
    b.className = 'ordpar-mback';                          // so `deck/assets.py` finds the class
    b.type = 'button';
    b.setAttribute('aria-label', 'Back to ' + word);
    var arrow = b.appendChild(el('span', 'ordpar-mback-arrow'));
    arrow.setAttribute('aria-hidden', 'true');
    arrow.textContent = '← ';
    var w = b.appendChild(el('span', 'mini-hw'));
    w.lang = hw && hw.lang ? hw.lang : 'nb';
    w.textContent = word;
    return b;
  }
  /** A step in the open box `c` to the target `t` of its link `a`. */
  function step(c, a, t) {
    closeFrom(chain.indexOf(c) + 1);                         // the boxes opened from it, if any
    var box = kid(c.m, 'ordpar-fmini');
    var hw = box.querySelector('.mini-head .mini-hw'), head = header(a, t.href);
    var nodes = doc.createDocumentFragment();
    a.setAttribute('aria-expanded', 'true');
    // where the reader was in the box: its own scroll (a computer's box scrolls inside); the
    // page's is never touched (decisions 147) — each step its own
    c.steps.push({ nodes: nodes, lang: c.m.getAttribute('lang'), from: a, scroll: box.scrollTop });
    var b = backLine(hw);
    hold();                                                  // the new content may be shorter
    while (box.firstChild) { nodes.appendChild(box.firstChild); }
    box.appendChild(b);
    box.appendChild(head);
    box.setAttribute('aria-busy', 'true');
    box.scrollTop = 0;
    fit(c.m); put(c);
    focusOn(b);
    var tok = ++c.tok;
    load(t.id).then(function (art) {
      if (tok !== c.tok || chain.indexOf(c) < 0) { return; }
      if (!art) { stepBack(c, false); global.location.href = t.href; return; }
      fill(c.m, box, art, t);
      put(c);
    });
  }
  /** One step back in the box `c`: the word stepped from, at the box's own scroll position; the
   *  page stays where it is (decisions 147). `focus`: the focus back on the link stepped from. */
  function stepBack(c, focus) {
    var s = c && c.steps.pop();
    if (!s) { return; }
    c.tok++;
    closeFrom(chain.indexOf(c) + 1);
    var box = kid(c.m, 'ordpar-fmini');
    hold();
    while (box.firstChild) { box.removeChild(box.firstChild); }
    box.appendChild(s.nodes);
    box.removeAttribute('aria-busy');
    if (s.lang) { c.m.setAttribute('lang', s.lang); }
    if (s.from) { s.from.setAttribute('aria-expanded', 'false'); }
    fit(c.m); put(c);
    box.scrollTop = s.scroll;
    if (focus) { focusOn(s.from); }
  }

  /** Nested boxes (decisions 139, 147): a click inside an open box, not on a word that opens one,
   *  closes the boxes opened from it — so a click in the first box closes only the nested ones. */
  function insideClick(n) {
    if (chain.length < 2) { return; }
    var m = n.closest('.ordbok-xmini');
    for (var i = 0; i < chain.length; i++) {
      if (chain[i].m === m) { if (chain.length > i + 1) { closeFrom(i + 1); } return; }
    }
  }

  /* ------------------------------------------------- a peek inside a mini (141) */

  var peekX = null;                    // the `.ordbok-xref` in a mini whose peek was last placed

  /** Draw the peek of `x` (an `.ordbok-xref` inside a mini) against the window: above its word as
   *  the sheet draws it (its bottom 1.6em of its own size above the bottom of the word's first
   *  line), moved left to stay 8 px inside the window with its arrow kept on the word, below the
   *  word where above would leave the window (`ordpar-pbelow`, the arrow turned). A peek the
   *  sheet hides (no box) is left where it is. */
  function peekFix(x) {
    var p = x ? peekOf(x) : null;
    if (!p) { return; }
    peekX = x;
    p.classList.add('ordpar-pfix');
    p.classList.remove('ordpar-pbelow');
    p.style.removeProperty('--ordpar-peek-dx');
    p.style.left = '0px';
    p.style.top = '0px';
    var pr = p.getBoundingClientRect();
    if (!pr.width) { return; }
    var rs = x.getClientRects(), r = rs.length ? rs[0] : x.getBoundingClientRect();
    var em = parseFloat(global.getComputedStyle(p).fontSize) || 13;
    var W = doc.documentElement.clientWidth, H = doc.documentElement.clientHeight, G = 8;
    var gap = Math.max(0, 1.6 * em - r.height);              // the sheet's gap between word and peek
    var top = r.top - gap - pr.height;
    if (top < G && r.bottom + gap + pr.height <= H - G) {
      top = r.bottom + gap;
      p.classList.add('ordpar-pbelow');
    }
    var left = Math.min(r.left, W - G - pr.width);
    if (left < G) { left = G; }
    p.style.left = Math.round(left) + 'px';
    p.style.top = Math.round(top) + 'px';
    var dx = Math.round(r.left - left);
    if (dx) { p.style.setProperty('--ordpar-peek-dx', dx + 'px'); }
  }

  /* ------------------------------------------------------------- prefetch */

  var restA = null, restTimer = null;
  function unrest() {
    if (restTimer) { clearTimeout(restTimer); }
    restA = restTimer = null;
  }
  function rest(a, t) {
    if (restTimer) { clearTimeout(restTimer); }
    restA = a;
    restTimer = setTimeout(function () { restTimer = null; load(t.id); }, REST_MS);
  }

  var queue = [], pumping = false;
  function idle(f) {
    if (global.requestIdleCallback) { global.requestIdleCallback(f, { timeout: 3000 }); } else { setTimeout(f, 200); }
  }
  function pump() {
    if (pumping) { return; }
    var id = queue.shift();
    if (id == null) { return; }
    pumping = true;
    idle(function () {
      load(id).then(function () { pumping = false; pump(); });
    });
  }

  /* ---------------------------- the hover's Norwegian definition (site decisions 152) */

  /*
   * Norwegian only with the English equivalents hidden and the hovers on "Norwegian definition"
   * (`ordpar-nbo-hovnb` on <html>; Robin 2026-10-30, "the hovers showing the Norwegian definition
   * vs nothing"): EVERY link whose target has a first Norwegian definition shows it, translated or
   * not (one style). Read at hover time from the target's `snip/` file (the list rows' own file,
   * lookup-index.md § 3: an untranslated article's line is its Norwegian definition, a translated
   * one's is in `"_n"`), whose key the page carries on the link (`data-s`, `face._link`), so a page
   * carries no second peek (the measurement: lookup-index.md § 5, 152). The peek is made once per
   * link, on the first hover or focus, with `data-nosnippet` from its making (154), and placed as
   * the page places a peek; the sheet shows it only under that class and hides the English one.
   */
  function hovNb() { return !!(doc && doc.documentElement.classList.contains('ordpar-nbo-hovnb')); }
  /** The peek a link shows: its Norwegian one under `ordpar-nbo-hovnb`, else its own. */
  function peekOf(x) {
    if (hovNb()) {
      for (var k = x.firstChild; k; k = k.nextSibling) {
        if (k.classList && k.classList.contains('ordpar-nbpk')) { return k; }
      }
      return null;
    }
    return kid(x, 'ordbok-xpeek');
  }
  /** Place the Norwegian peek of `x` as the page places a peek (`article.js` `place`; a mini's
   *  against the window, `peekFix`). */
  function placeNb(x) {
    var p = peekOf(x);
    if (!p || !p.classList.contains('ordpar-nbpk')) { return; }
    if (x.closest('.ordbok-xmini')) { peekFix(x); return; }
    var place = global.ordparPlace;
    if (!place) { return; }
    p.style.removeProperty('--ordpar-peek-dx');
    place(p);
    var dx = parseFloat(p.style.left) || 0;
    if (dx) { p.style.setProperty('--ordpar-peek-dx', (-dx) + 'px'); }
  }
  /** The first Norwegian definition of article `id` in its `snip/` file `snips` (lookup.js
   *  `nbDef`), or ''. */
  function nbText(snips, id) {
    var L = global.ordparLookup;
    return L && L.nbDef ? L.nbDef(snips, id) || '' : '';
  }
  /** The `snip/` key of link `a`: its own `data-s`, or for an English partner word (decisions 54,
   *  `ordpar-xen`, which carries none) that of the Norwegian link to the same target in its pair. */
  function snipKeyOf(a) {
    var key = a.getAttribute('data-s');
    if (key) { return key; }
    var pair = a.closest && a.closest('.ordpar-pair, .mini-pair'), href = a.getAttribute('href') || '';
    if (!pair || !href) { return null; }
    var as = pair.querySelectorAll('a.ordbok-xword[data-s]');
    for (var i = 0; i < as.length; i++) {
      if (as[i].getAttribute('href') === href) { return as[i].getAttribute('data-s'); }
    }
    return null;
  }
  /*
   * Site decisions 185: the same peek under the setting `peek` = nb (the class `shell.js` `hoverNb`
   * toggles), wherever a peek shows. It follows the setting "When a linked article or page is
   * loaded" (`minifetch`, as `fetchMode` reads it): under `click` nothing is fetched before a press,
   * so the peek is made only from a `snip/` file the page has already (`lookup.js`
   * `loadedSnippets`, a search's, say), else none — and the link is left unmade, so a later hover
   * after such a file has come makes it.
   */
  function nbPeek(x) {
    if (!x || !hovNb()) { return; }
    if (x._nbpk) { if (x._nbpk === 2) { placeNb(x); } return; }
    var a = kid(x, 'ordbok-xword'), L = global.ordparLookup;
    var key = a && snipKeyOf(a), m = a && HREF.exec(a.getAttribute('href') || '');
    if (!key || !m || !L || !L.loadSnippets) { return; }
    var have = null;
    if (fetchMode() === 'click') {
      have = L.loadedSnippets ? L.loadedSnippets(key) : null;
      if (!have) { return; }
    }
    x._nbpk = 1;
    Promise.resolve(have || L.loadSnippets(key)).then(function (snips) {
      var text = nbText(snips, m[1]);
      if (!text) { return; }
      var p = el('span', 'ordbok-xpeek ordpar-nbpk ordpar-nbdef');
      p.setAttribute('lang', 'nb');
      p.setAttribute('data-nosnippet', '');          // site decisions 154: at the making
      p.textContent = text;
      x.appendChild(p);
      x._nbpk = 2;
      if (x.matches && x.matches(':hover')) { placeNb(x); }
    }, function () { x._nbpk = 0; });
  }

  /** `minifetch = page`: every target on the page not fetched yet, queued (also after the
   *  search page inserts articles — `ordparDefs` calls this). */
  function scan() {
    if (!doc || navigates() || fetchMode() !== 'page') { return; }
    var as = doc.querySelectorAll('.ordbok-xref > a.ordbok-xword');
    var shared = global.ordparAhead && global.ordparAhead.queue;
    for (var i = 0; i < as.length; i++) {
      var t = target(as[i]);
      if (!t || pages[t.id]) { continue; }
      // decisions 92: one idle queue with the list view's articles (ahead.js), so the page's
      // fetches ahead go one at a time whoever asked for them
      if (shared) { shared('a' + t.id, load.bind(null, t.id)); } else if (queue.indexOf(t.id) === -1) { queue.push(t.id); }
    }
    if (!shared) { pump(); }
  }

  /* --------------------------------------------------------------- wiring */

  if (doc && doc.addEventListener) {
    doc.addEventListener('click', function (e) {
      var n = e.target;
      if (e.defaultPrevented || !n || !n.closest) { return; }
      if (openX && n.closest('.ordbok-xback')) { e.preventDefault(); close(); return; }
      var bl = openX ? n.closest('.ordpar-mback') : null, bc = bl ? boxOf(bl) : null;
      if (bc && bc.steps.length) { e.preventDefault(); stepBack(bc, true); return; }   // its own box
      var a = linkOf(n), t = target(a);
      if (!t || navigates()) { if (openX) { insideClick(n); } return; }
      if (e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) { return; }   // a new tab
      e.preventDefault();
      for (var i = 0; i < chain.length; i++) {               // the same word again closes its box
        if (chain[i].x === a.parentNode) { closeFrom(i); return; }
      }
      open(a, t, e.detail === 0);                            // detail 0: Enter, not a pointer
    });
    doc.addEventListener('keydown', function (e) {
      if (openX && (e.key === 'Escape' || e.key === 'Esc')) {
        // decisions 139, 147: the deepest box — one step back where it has steps, else it closes
        var c = chain[chain.length - 1];
        if (c.steps.length) { stepBack(c, true); return; }
        closeFrom(chain.length - 1);
        focusOn(c.a);
      }
    });
    // decisions 139: a nested box follows its word when the page or a box scrolls; 141: so does
    // a peek drawn against the window, while its word is still under the pointer
    global.addEventListener('scroll', function () {
      unhold();                                              // decisions 147: the hold follows the reader up
      for (var i = 1; i < chain.length; i++) { placeNested(chain[i], true); }   // 165: its side kept
      if (peekX && peekX.isConnected && peekX.matches && peekX.matches(':hover')) { peekFix(peekX); }
    }, true);
    // 141: a peek inside a mini drawn against the window — on the window, so after the page
    // script's own placing on the document (`article.js`), which assumes the sheet's place
    global.addEventListener('mouseover', function (e) {
      var n = e.target, x = n && n.closest ? n.closest('.ordbok-xref') : null;
      if (x && x.closest('.ordbok-xmini') && peekOf(x)) { peekFix(x); }
      // site decisions 152: the link's Norwegian peek, made on the first hover, placed on each
      if (x) { nbPeek(x); }
    });
    doc.addEventListener('focusin', function (e) {
      var n = e.target, x = n && n.closest ? n.closest('.ordbok-xref') : null;
      if (x) { nbPeek(x); }
    });
    // `point`: a fetch once the pointer has rested on a link (each move restarts the wait)
    doc.addEventListener('mousemove', function (e) {
      if (fetchMode() !== 'point' || navigates()) { return; }
      var a = linkOf(e.target), t = target(a);
      if (!t) { if (restA) { unrest(); } return; }
      if (pages[t.id]) { return; }
      rest(a, t);
    });
    doc.addEventListener('mouseout', function (e) {
      if (restA && !(e.relatedTarget && restA.contains(e.relatedTarget))) { unrest(); }
    });
    doc.addEventListener('touchstart', function (e) {
      if (fetchMode() !== 'point' || navigates()) { return; }
      var t = target(linkOf(e.target));
      if (t) { load(t.id); }
    }, { passive: true });
    if (doc.readyState === 'complete') { scan(); } else { global.addEventListener('load', scan); }
    // the width again (decisions 80): the ceiling follows the window, and a setting's class
    // on <html> can change the open mini's lines (languages, spacing, scrolling, formulas, etymology)
    global.addEventListener('resize', refit);
    if (global.MutationObserver && doc.documentElement) {
      new global.MutationObserver(refit).observe(doc.documentElement, { attributes: true, attributeFilter: ['class'] });
    }
  }

  global.ordparMinis = { scan: scan, cut: cut, allocate: allocate, header: header,
    norwegian: norwegian, close: close, load: load, narrowest: narrowest, fit: fit,
    nestMode: nestMode, inPlaceAt: inPlaceAt, depthOf: depthOf, peekFix: peekFix,
    nbPeek: nbPeek, peekOf: peekOf,                          // site decisions 152
    target: target,                                          // site decisions 180: ahead.js leaves these to this file
    EX_BUDGET: EX_BUDGET, REST_MS: REST_MS };
}(typeof globalThis !== 'undefined' ? globalThis : this));
