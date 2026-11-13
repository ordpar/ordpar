/*! Ordpar — the favourites and history pages (site decisions 60, Robin 2026-10-19).
 *
 * Static shells (`site/favourites.html`, `site/history.html`, written to `/favourites/` and
 * `/history/` by build_index.py) that render from the device's storage (`personal.js`). The
 * favourites page lists the saved articles, newest first, as the list view's rows (site
 * decisions 89, Robin 2026-10-22: `ordparSearch.listRows`) — headword, homograph, word class,
 * the translated / Norwegian-only tag and the stored snippet line, each a disclosure that opens
 * the article in place (fetching its page, as the list view does) — with a remove button, and a
 * link to Export and Import, which live on the settings page since decisions 63 (`settings.js`;
 * brief 60 item 6 put them here). The history page lists the searches, newest
 * first, each drawn as a suggestion row (`ordparShell.searchRowMain` / `searchRowSide`, brief
 * 60b item 3) and linking to the search it runs again, with "Clear history", which asks once;
 * a row's right-hand side is filled from the dictionary as it nears the screen (site decisions
 * 88, `ordparShell.fillSearchRow` — the history page's one fetch).
 * Each says plainly when it is
 * empty, and that the lists live only in this browser on this device. Either page follows a
 * change made in another tab (the `storage` event, through `ordparPersonal.onChange`).
 *
 * The page picks its kind from `<main data-ordpar-personal="favourites|history">`.
 */
(function (global) {
  'use strict';

  var doc = global.document;

  function shell() { return global.ordparShell; }
  function t(key, vars) {
    var s = shell() ? shell().t(key) : key;
    if (vars) { for (var k in vars) { s = s.split('{' + k + '}').join(String(vars[k])); } }
    return s;
  }
  function el(tag, cls, text) {
    var node = doc.createElement(tag);
    if (cls) { node.className = cls; }
    if (text != null) { node.textContent = text; }
    return node;
  }
  function base() { return global.ORDPAR_BASE || '/'; }

  // the page's status line: kept across re-renders (an import or a change in another tab
  // re-draws the page), so a message is never lost to the redraw it caused
  var message = '';
  function say(text) {
    message = text;
    var st = doc.querySelector('.ordpar-personal-status');
    if (st) { st.textContent = text; }
  }

  /** One history row: the search as a suggestion row, the whole row a link that runs it again
   *  (the search page's first load from #q= records it, so it moves to the top). The search in
   *  the address's fragment, never sent to a server (decisions 104). */
  function searchRow(e) {
    var sh = shell();
    var li = el('li', 'ordpar-personal-row ordpar-history-row');
    // site decisions 148 item 9: an English search, drawn unmarked in the English manner (the
    // English word left, the Norwegian headwords' first spellings right), its link `#en=`
    if (e.en && sh.englishEntryRow) {
      var en = sh.englishEntryRow('a', e, '', 'ordpar-history-link');
      en.href = base() + 'bm-en/#en=' + encodeURIComponent(e.q);
      li.appendChild(en);
      return li;
    }
    var a = el('a', 'ordpar-history-link');
    a.href = base() + 'bm-en/#q=' + encodeURIComponent(e.q);
    // the accent only where a translated article is behind the row (88's second amendment);
    // known at once for one article, else set when the side fills (shell.js `fillSearchRow`)
    if (e.n === 1 && e.translated) { a.classList.add('is-translated'); }
    a.appendChild(sh.searchRowMain(e));
    var side = a.appendChild(sh.searchRowSide(e));
    li.appendChild(a);
    // held: a side to fill, or a stored gloss to check (site decisions 116, `is-check`)
    if (side.querySelector('.is-pending, .is-check')) { held.push({ li: li, side: side, e: e }); }
    return li;
  }

  /*
   * The held right-hand sides filled from the dictionary (site decisions 88, `ordparShell.
   * fillSearchRow`), each when its row comes near the screen — a list of up to 100 searches
   * would otherwise run up to 100 searches at once; where the browser has no
   * IntersectionObserver, all at once. A redraw of the page drops the old rows' watch.
   */
  var held = [];
  var watch = null;
  function fillHeld() {
    var sh = shell(), rows = held;
    held = [];
    if (watch) { watch.disconnect(); watch = null; }
    if (!rows.length || !sh || !sh.fillSearchRow) { return; }
    if (!global.IntersectionObserver) {
      rows.forEach(function (r) { sh.fillSearchRow(r.side, r.e); });
      return;
    }
    watch = new global.IntersectionObserver(function (seen, obs) {
      seen.forEach(function (s) {
        if (!s.isIntersecting) { return; }
        obs.unobserve(s.target);
        var r = rows[Number(s.target.getAttribute('data-held'))];
        if (r) { sh.fillSearchRow(r.side, r.e); }
      });
    }, { rootMargin: '400px 0px' });
    rows.forEach(function (r, i) { r.li.setAttribute('data-held', String(i)); watch.observe(r.li); });
  }

  /*
   * The favourites (site decisions 89, Robin 2026-10-22): the list view's rows
   * (`ordparSearch.listRows`), so a favourite opens in place as a list-view result does — a
   * disclosure button in a heading (`aria-expanded`), the article fetched into the region below
   * it, the inflection tables as the setting `infl` says (83), Copy link / Share / "Suggest a
   * correction" / the heart under it (`resultControls`; no "Article page" since site decisions
   * 168, re-ruled 2026-11-06), the installed copy answering it offline. Each row
   * keeps its headword, homograph, word class and the translated / Norwegian-only tag (A18:
   * they keep the tag), its snippet line the one stored with the favourite, and the Remove
   * button beside it. The rows are headings one level under the page's title (`level` 2); the
   * small heart the list view puts beside a saved word is left out, since every row is one.
   *
   * A row is made once per page view and kept (`favRows`, by id): a change to the list — a
   * favourite removed here or in another tab, one added elsewhere — adds and drops rows in
   * place (`syncFavs`), so an opened article stays open; a change of language draws them anew.
   */
  var favRows = Object.create(null);

  /* A favourite's stored snippet written as a summary gloss — semibold, its " · " faded —
   * where its headword's `snip/` file names it one and still has that same text (site
   * decisions 116, Robin 2026-10-24: only the summary glosses semibold); an English definition
   * line, a text that has changed since, or no file (offline without the copy) stays regular.
   * The entry's own shape is unchanged, so a favourite saved before 116 follows too. */
  function markGloss(snip, e) {
    var L = global.ordparLookup;
    if (!L || !L.loadSnippets || !L.isGloss || !L.writeGloss) { return; }
    var word = String(e.word || '').split(' / ')[0];
    if (!word) { return; }
    var got;
    try { got = L.loadSnippets(L.snipKey(L.fold(word))); } catch (err) { return; }
    Promise.resolve(got).then(function (snips) {
      var id = String(e.id);
      if (snips && snips[id] === e.snip && L.isGloss(snips, id)) { L.writeGloss(snip, e.snip, true); }
    }).catch(function () {});
  }

  /* A favourite's line as its first Norwegian definition (site decisions 152), held until its
   * headword's `snip/` file answers (`ordparLookup.nbDef`); gone where it has none. */
  function nbSnip(snip, e) {
    var L = global.ordparLookup;
    var word = String(e.word || '').split(' / ')[0];
    var drop = function () { if (snip.parentNode) { snip.parentNode.removeChild(snip); } };
    if (!word) { drop(); return; }
    snip.lang = 'nb';
    Promise.resolve(L.loadSnippets(L.snipKey(L.fold(word)))).then(function (snips) {
      var text = L.nbDef(snips, e.id);
      if (!text) { drop(); return; }
      snip.textContent = text;
      snip.classList.remove('is-pending');
    }).catch(drop);
  }

  function favRow(e, P) {
    if (favRows[e.id]) { return favRows[e.id]; }
    var wrap = global.ordparSearch.listRows([e], Object.create(null),
      { level: 2, mark: false, renumber: true });
    var row = wrap.firstChild;
    row.classList.add('ordpar-fav-row');
    var snip = row.querySelector('.ordpar-row-snippet');
    var L0 = global.ordparLookup;
    if (snip && e.translated && L0 && L0.nbRows && L0.nbRows()) {
      // site decisions 152: Norwegian only's rows on "Norwegian definition" — the article's first
      // Norwegian definition from its headword's `snip/` file (the stored line is its English)
      nbSnip(snip, e);
    } else if (snip && e.snip) {
      snip.textContent = e.snip;
      snip.classList.remove('is-pending');
      if (e.translated) { markGloss(snip, e); }
    } else if (snip) {
      snip.parentNode.removeChild(snip);
    }
    var rm = el('button', 'ordpar-result-btn ordpar-fav-remove', t('favourites.remove'));
    rm.type = 'button';
    // the spellings as the row shows them, ", " between, never the stored " / " (decisions
    // 93); no numeral, as before: a label read out has no use for a Roman numeral (33)
    var L = global.ordparLookup;
    var said = L && L.headParts
      ? L.headParts(e.word).parts.map(function (p) { return p.w; }).join(', ') : e.word;
    rm.setAttribute('aria-label', t('favourites.removeLabel', { word: said }));
    rm.addEventListener('click', function () {
      var next = row.nextElementSibling || row.previousElementSibling;
      var nextId = next ? next.getAttribute('data-id') : null;
      P.setFavourite(e, false);                   // the rows follow through onChange
      // focus stays on the list: the next row's button, else the heading
      var target = nextId && doc.querySelector('.ordpar-fav-row[data-id="' + nextId + '"] .ordpar-fav-remove');
      var h = doc.querySelector('.ordpar-personal h1');
      if (target) { target.focus(); } else if (h) { h.focus(); }
    });
    row.insertBefore(rm, row.querySelector('.ordpar-row-panel'));
    favRows[e.id] = row;
    return row;
  }

  /** Bring the rows in `box` to `list`, in its order, keeping the rows already there. A row
   *  that goes while it holds the focus (its article's heart pressed) hands it to the row now
   *  in its place, else to the page's heading. */
  function syncFavs(box, list, P) {
    var want = list.map(function (e) { return favRow(e, P); });
    var active = doc.activeElement, lost = -1;
    Array.prototype.slice.call(box.children).forEach(function (r, i) {
      if (want.indexOf(r) !== -1) { return; }
      if (active && r.contains(active)) { lost = i; }
      box.removeChild(r);
      delete favRows[r.getAttribute('data-id')];
    });
    want.forEach(function (r, i) {
      if (box.children[i] !== r) { box.insertBefore(r, box.children[i] || null); }
    });
    if (lost !== -1) {
      var to = box.children[Math.min(lost, box.children.length - 1)];
      var target = to ? to.querySelector('.ordpar-row-button') : doc.querySelector('.ordpar-personal h1');
      if (target) { target.focus(); }
    }
  }

  /** The favourites page drawn once (its heading, the rows' box, the links); a later change
   *  only updates the rows and the empty line (`syncFavs`). `fresh`: draw it all anew. */
  var favPage = null;
  function renderFavourites(main, fresh) {
    var P = global.ordparPersonal;
    var list = P ? P.favourites() : [];
    if (favPage && !fresh && main.contains(favPage.wrap)) {
      favPage.empty.hidden = list.length > 0;
      syncFavs(favPage.box, list, P);
      return;
    }
    favRows = Object.create(null);
    main.textContent = '';
    var wrap = el('div', 'ordpar-personal');
    var h1 = el('h1', null, t('favourites.title'));
    h1.tabIndex = -1;
    wrap.appendChild(h1);
    var nav = el('p', 'ordpar-personal-nav');
    var link = el('a', null, t('favourites.toHistory'));
    link.href = base() + 'history/';
    nav.appendChild(link);
    wrap.appendChild(nav);
    wrap.appendChild(el('p', 'ordpar-note', t('personal.device')));
    var empty = wrap.appendChild(el('p', 'ordpar-empty ordpar-personal-empty', t('favourites.empty')));
    empty.hidden = list.length > 0;
    var box = wrap.appendChild(el('div', 'ordpar-rows ordpar-fav-rows'));
    syncFavs(box, list, P);
    // decisions 63: export and import moved to /settings/ ("Loading, offline and your data" since decisions 92); a link stays
    var tp = el('p', 'ordpar-transfer ordpar-transfer-link');
    var ta = el('a', null, t('transfer.link'));
    ta.href = base() + 'settings/#data';
    tp.appendChild(ta);
    wrap.appendChild(tp);
    var st = el('p', 'ordpar-personal-status');
    st.setAttribute('role', 'status');
    st.textContent = message;
    wrap.appendChild(st);
    main.appendChild(wrap);
    favPage = { wrap: wrap, box: box, empty: empty };
  }

  function render(main, kind, fresh) {
    if (kind === 'favourites') { renderFavourites(main, fresh); return; }
    var P = global.ordparPersonal;
    main.textContent = '';
    var wrap = el('div', 'ordpar-personal');
    var h1 = el('h1', null, t(kind + '.title'));
    h1.tabIndex = -1;
    wrap.appendChild(h1);
    var nav = el('p', 'ordpar-personal-nav');
    var link = el('a', null, t('history.toFavourites'));
    link.href = base() + 'favourites/';
    nav.appendChild(link);
    wrap.appendChild(nav);
    wrap.appendChild(el('p', 'ordpar-note', t('personal.device')));

    var list = P ? P.history() : [];
    if (!list.length) {
      wrap.appendChild(el('p', 'ordpar-empty ordpar-personal-empty', t('history.empty')));
    }
    var ul = el('ul', 'ordpar-personal-list');
    held = [];
    list.forEach(function (e) { ul.appendChild(searchRow(e)); });
    wrap.appendChild(ul);

    var st = el('p', 'ordpar-personal-status');
    st.setAttribute('role', 'status');
    st.textContent = message;

    if (list.length) {
      var actions = el('div', 'ordpar-personal-actions');
      var clear = el('button', 'ordpar-button is-quiet ordpar-history-clear', t('history.clear'));
      clear.type = 'button';
      clear.addEventListener('click', function () { confirmClear(actions, clear, list.length); });
      actions.appendChild(clear);
      wrap.appendChild(actions);
    }
    wrap.appendChild(st);
    main.appendChild(wrap);
    fillHeld();                                   // laid out now: the rows can be watched
  }

  /** "Clear history" asks once, in place: the question and two buttons, Cancel focused. */
  function confirmClear(actions, clear, n) {
    if (actions.querySelector('.ordpar-confirm')) { return; }
    clear.hidden = true;
    var box = el('div', 'ordpar-confirm');
    box.setAttribute('role', 'group');
    var q = el('span', 'ordpar-confirm-text', t('history.confirm', { n: n }));
    q.id = 'ordpar-confirm-text';
    box.setAttribute('aria-labelledby', q.id);
    box.appendChild(q);
    var yes = el('button', 'ordpar-button ordpar-confirm-yes', t('history.confirmYes'));
    yes.type = 'button';
    var no = el('button', 'ordpar-button is-quiet ordpar-confirm-no', t('history.cancel'));
    no.type = 'button';
    yes.addEventListener('click', function () {
      say(t('history.cleared'));
      global.ordparPersonal.clearHistory();       // re-renders through onChange
      var h = doc.querySelector('.ordpar-personal h1');
      if (h) { h.focus(); }
    });
    no.addEventListener('click', function () {
      actions.removeChild(box);
      clear.hidden = false;
      clear.focus();
    });
    box.appendChild(yes);
    box.appendChild(no);
    actions.appendChild(box);
    no.focus();
  }

  function start() {
    var main = doc.querySelector('[data-ordpar-personal]');
    if (!main) { return; }
    var kind = main.getAttribute('data-ordpar-personal') === 'history' ? 'history' : 'favourites';
    var draw = function (fresh) {
      doc.title = t(kind + '.title') + ' — ' + t('site.name');
      render(main, kind, fresh);
    };
    draw(true);
    if (global.ordparPersonal) { global.ordparPersonal.onChange(function () { draw(false); }); }
    if (shell() && shell().onChange) {
      // a change of language draws the favourites anew (their words); any other setting keeps
      // their rows, the opened articles following it as the list view's do
      // site decisions 152: Norwegian only, its settings and the labels draw them anew too (their
      // lines and word classes are drawn in the language in force)
      var fresh = ['lang', 'nbonly', 'nbequiv', 'nbrows', 'labels'];
      shell().onChange(function (key) {
        if (key === 'render' || fresh.indexOf(key) !== -1) { draw(fresh.indexOf(key) !== -1); }
      });
    }
  }

  function whenReady() { ((shell() && shell().ready) || Promise.resolve()).then(start); }
  if (doc.readyState === 'loading') { doc.addEventListener('DOMContentLoaded', whenReady); }
  else { whenReady(); }
}(typeof globalThis !== 'undefined' ? globalThis : this));
