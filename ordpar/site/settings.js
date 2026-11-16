/*! Ordpar — the settings page, `/settings/` (site-review decisions 63, Robin 2026-10-19).
 *
 * A static page in place of the header's old settings dialog, in sections with a row of jump
 * links at the top (decisions 63): **Style** (theme, colour, interface language, the article
 * layout — decisions 87), **Article**
 * in four subsections since decisions 85 (Robin, 2026-10-21) — *Language* (definitions, the
 * emphasized line and subsenses in English — decisions 87, 90 — formula lines, etymology), *Inflection* (the tables, participle context), *Cross-references* (what a
 * click opens, the hover peek), *Small articles* (their language, content, spacing, scrolling
 * and headword) — each an `h3` under the section's `h2`, named by the table's `sub` key,
 * **Search** (the list view), **Loading, offline and your data** (since decisions 92 its first
 * subsection *Loading*: when a linked article or page is loaded, `minifetch`, moved there from
 * Small articles with its key and values; then the offline copy — `offline.js`;
 * export and import — moved here from the favourites page, which keeps a link; reset settings;
 * delete stored data). Plain form controls — fieldsets of radio buttons — no dialog.
 *
 * Built from the settings' table, `ordparShell.SETTINGS` (shell.js): a new setting is ONE entry
 * there, carrying its section; this file draws every entry of a section in the table's order,
 * with the words `settings.<key>` (legend) and `settings.<key>.<value>` (each choice). The colour
 * choices come from the colour table (`sitegen/colours.py`, inlined as `window.ORDPAR_COLOURS`).
 * A change applies at once and is stored (`ordparShell.setSetting`); "← Back" goes back in the
 * browser's history when the reader came from this site, else to the front page.
 *
 * Since 2026-10-24: a setting with `control: 'select'` (the examples limit, decisions 112) is a
 * drop-down in its fieldset instead of radios; `exmore` is hidden while that limit is All
 * (`shown`); a setting with `gate: 'counting'` ("Send usage statistics", decisions 104) is drawn
 * only while the build says the counting is live (`window.ORDPAR_COUNTING`, `drawn`), after the
 * offline copy and the transfer, before the stored data. (Until 2026-11-05, site decisions 166,
 * the privacy page's switch drew it, `window.ORDPAR_PRIVACY`: the page can now be published while
 * the counting is off, so the setting follows the counting alone.)
 *
 * Since 2026-10-25 (decisions 126): a subsection whose strings have `settings.sub.<sub>.intro`
 * gets that line under its heading (`intro`); only Small articles has one.
 *
 * Since 2026-10-26 (decisions 136): PRESETS above the sections — Default, English emphasized (since
 * 2026-11-07, decisions 174), Concise, For learners — each setting every Article setting at once (`PRESETS` below, the one table); the
 * one the settings match shows pressed (`aria-pressed`), none when they match none; and a line
 * under "Reset settings" saying it resets everything, the style too (`settings.resetNote`).
 *
 * Since 2026-10-28 (decisions 146): under it, "Copy the address for a pop-up dictionary" (`popup`).
 * This page always draws, changes and copies the SAVED settings: the head script applies no
 * visit here (settings in the address, `sitegen/head.py`).
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var SECTIONS = ['style', 'article', 'search', 'data'];

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

  // the page's status line, kept across a redraw
  var message = '';
  function say(text) {
    message = text;
    var st = doc.querySelector('.ordpar-settings-status');
    if (st) { st.textContent = text; }
  }

  /* ------------------------------------------- the presets (site decisions 136) */
  // THE PRESETS (Robin, 2026-10-26): each sets EVERY Article setting (`section: 'article'` in
  // `ordparShell.SETTINGS`) — the values it names, and every other one its default — and nothing
  // else: not Style (theme, colour, layout, language), Search or Loading. Nothing is locked: a
  // setting changed afterwards is simply the reader's. Every value a preset was ruled to have is
  // named here even where it is the default today, so a later change of a default does not
  // silently change a preset; Default names none (it is the defaults, whatever they become).
  // Kept as strict JSON between the brackets: `tests/test_ordpar_presets136.py` reads it.
  // Decisions 139's setting `nestminis` is named in Concise and For learners: since decisions 147
  // at its new default, a second box then that box,
  // so a preset changes only what it is about; the limit's setting went with the limit.
  // Site decisions 174 (a new preset with the old defaults): "English emphasized", second, names `emph` en and `formulas` en, the
  // defaults until 174 (now no and both); Concise names the same two, so the change of default
  // leaves it as it was; For learners already named no and both.
  // Site decisions 187: For learners turns the CEFR level box on (`levels`); the others leave it at
  // its default, off. Site decisions 188: For learners orders the set phrases by level
  // (`phraseorder`); the others give the default, alphabetical.
  var PRESETS = [
    { "id": "default", "values": {} },
    { "id": "english", "values": { "emph": "en", "formulas": "en" } },
    { "id": "concise", "values": { "defs": "en", "exlimit": "2", "exmore": "on", "minicontent": "slim", "minispacing": "article", "nestminis": "second", "emph": "en", "formulas": "en" } },
    { "id": "learners", "values": { "exeye": "on", "emph": "no", "examples": "both", "subsenses": "defs", "formulas": "both", "nestminis": "second", "levels": "on", "phraseorder": "level" } }
  ];

  function articleSettings() {
    // site decisions 152: Norwegian only and its settings are a LAYER over the reader's settings,
    // never a preset's (`layer: true` in the table): no preset sets them, none matches on them
    return shell().SETTINGS.filter(function (sp) { return sp.section === 'article' && !sp.layer; });
  }

  /** A preset's full set: {key: value} for every Article setting. */
  function presetValues(pr) {
    var out = {};
    articleSettings().forEach(function (sp) {
      out[sp.key] = Object.prototype.hasOwnProperty.call(pr.values, sp.key) ? pr.values[sp.key] : sp.def;
    });
    return out;
  }

  /** The id of the preset the stored settings match, or null. */
  function matching() {
    var sh = shell();
    for (var i = 0; i < PRESETS.length; i++) {
      var want = presetValues(PRESETS[i]), same = true;
      for (var k in want) { if (sh.getSetting(k) !== want[k]) { same = false; break; } }
      if (same) { return PRESETS[i].id; }
    }
    return null;
  }

  /** Each preset button pressed or not, as the settings stand. */
  function syncPresets() {
    var on = matching();
    Array.prototype.forEach.call(doc.querySelectorAll('button[data-preset]'), function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-preset') === on ? 'true' : 'false');
    });
  }

  /** Set every Article setting to the preset's value, as a radio does (`setSetting`: stored, the
   *  classes on <html>, the page's redraw), then say so in the status line. */
  function applyPreset(pr) {
    var sh = shell(), want = presetValues(pr), waits = [];
    for (var k in want) { waits.push(sh.setSetting(k, want[k])); }
    return Promise.all(waits).then(function () {
      sync();
      say(t('settings.presets.done', { name: t('settings.presets.' + pr.id) }));
    });
  }

  /** The presets' box: a heading, the line under it, a button per preset (four since 174). */
  function presets() {
    var sec = el('section', 'ordpar-settings-section ordpar-presets');
    sec.id = 'presets';
    var h2 = el('h2');
    // the section named by the title's own span, as a field by its title: the heading also
    // holds the "?" and its box (below)
    var title = h2.appendChild(el('span', null, t('settings.presets.title')));
    title.id = 'presets-title';
    sec.setAttribute('aria-labelledby', title.id);
    sec.appendChild(h2);
    // what each preset does, behind one "?" after the heading (site decisions 161):
    // a line per preset, then Help's Settings section
    var data = { hint: '', lines: PRESETS.map(function (pr) {
      return { label: t('settings.presets.' + pr.id), text: t('settings.presets.' + pr.id + '.note') };
    }), link: { href: '/help/#settings', text: t('settings.presets.helpLink') } };
    var hc = hintControl({ key: 'presets' }, data, sec, h2, t('settings.presets.title'));
    hc.button.setAttribute('aria-label', t('settings.presets.hintButton'));
    var p = el('p', 'ordpar-note ordpar-settings-intro', t('settings.presets.intro'));
    p.id = 'presets-intro';
    sec.setAttribute('aria-describedby', p.id);
    sec.appendChild(p);
    var row = el('div', 'ordpar-presets-row');
    var on = matching();
    PRESETS.forEach(function (pr) {
      var b = el('button', 'ordpar-button is-quiet ordpar-preset', t('settings.presets.' + pr.id));
      b.type = 'button';
      b.setAttribute('data-preset', pr.id);
      b.setAttribute('aria-pressed', pr.id === on ? 'true' : 'false');
      b.addEventListener('click', function () { applyPreset(pr); });
      row.appendChild(b);
    });
    sec.appendChild(row);
    return sec;
  }

  /* ------------------------------------------------------------- the choices */

  function choices(sp) {
    if (sp.key === 'colour') {
      return (shell().colours() || []).map(function (c) {
        return { value: c.id, label: c.name, colour: c };
      });
    }
    return sp.values.map(function (v) {
      var key = 'settings.' + sp.key + '.' + v;
      // a number is its own label (the examples limit's 1 to 10, decisions 112)
      var label = sp.key === 'lang' ? t('lang.name') : (/^\d+$/.test(v) && t(key) === key ? v : t(key));
      return { value: v, label: label };
    });
  }

  /* -------------------------------------------- when a setting is drawn or shown */

  /** Whether the setting is drawn at all. `gate: 'counting'` (decisions 104, the opt-out of the
   *  events): only while the counting is live (`chrome.counting()`: `events.js` `RECEIVER` set;
   *  site decisions 166), which the build tells this page by `window.ORDPAR_COUNTING`
   *  (`build_index.copy_shell`); with it off the page has no trace of the setting, though
   *  `events.js` still honours a stored Off. */
  function drawn(sp) {
    if (sp.gate === 'counting') { return global.ORDPAR_COUNTING === true; }
    return true;
  }

  /** Whether a drawn setting shows now: the "Show N more examples" line's setting only while a
   *  limit is set (decisions 112: with All it would do nothing, so it is hidden, not greyed). */
  function shown(sp) {
    var sh = shell();
    if (sp.key === 'exmore') { return sh.getSetting('exlimit') !== 'all'; }
    // decisions 186: what the eye hides, only while the eye is on
    if (sp.key === 'exeyewhat') { return sh.getSetting('exeye') === 'on'; }
    // site decisions 188: the set phrases' order, only while the level boxes are on
    if (sp.key === 'phraseorder') { return sh.getSetting('levels') === 'on'; }
    // site decisions 152: "English equivalents" acts only while Norwegian only is on, and what the
    // rows and the hovers show with them hidden only while they are hidden (hidden, not greyed)
    if (sp.key === 'nbequiv') { return sh.getSetting('nbonly') === 'on'; }
    if (sp.key === 'nbrows' || sp.key === 'nbhover') {
      return sh.getSetting('nbonly') === 'on' && sh.getSetting('nbequiv') === 'hidden';
    }
    return true;
  }

  function swatch(c) {
    var sw = el('span', 'ordpar-swatch');
    sw.setAttribute('aria-hidden', 'true');
    [c.day, c.night].forEach(function (col) {
      var s = el('span');
      s.style.background = col;
      sw.appendChild(s);
    });
    return sw;
  }

  /** A choice's line: a colour's own (decisions 63, ordbokene's maroon), or the strings'
   *  `settings.<key>.<value>.note` (decisions 78, 99); '' when it has none. */
  function noteOf(sp, ch) {
    if (ch.colour) { return ch.colour.note || ''; }
    var nkey = 'settings.' + sp.key + '.' + ch.value + '.note';
    return t(nkey) !== nkey ? t(nkey) : '';
  }

  /** A setting's way on to Help from its "?" box (site decisions 187: the CEFR levels' section),
   *  its words `settings.<key>.helpLink`. */
  var HELP_LINKS = { levels: '/help/#cefr-levels' };

  /** What a setting's "?" box holds (decisions 99, Robin 2026-10-23): the setting's own hint
   *  (`settings.<key>.hint`), then one line per choice that has a note, led by the choice's
   *  label, then its link to Help where `HELP_LINKS` has one. null when there is nothing to say —
   *  then the setting gets no "?". */
  function hintOf(sp, list) {
    var hkey = 'settings.' + sp.key + '.hint';
    var hint = t(hkey) !== hkey ? t(hkey) : '';
    var lines = [];
    (list || choices(sp)).forEach(function (ch) {
      var n = noteOf(sp, ch);
      if (n) { lines.push({ label: ch.label, text: n }); }
    });
    if (!hint && !lines.length) { return null; }
    var out = { hint: hint, lines: lines };
    if (HELP_LINKS[sp.key]) { out.link = { href: HELP_LINKS[sp.key], text: t('settings.' + sp.key + '.helpLink') }; }
    return out;
  }

  /* ---------------------------------------------- the "?" per setting (decisions 99) */
  // The hints sit behind one "?" per setting, on its title line, so the page shows only titles
  // and choices (decisions 99: the page is already long). The box is an OVERLAY placed under
  // the title inside the setting's fieldset: opening it never moves the page (a hover that
  // reflowed the choices under the pointer would make them jump), and the fieldset's width
  // keeps it inside the window. As the cross-reference's peek and mini: on a computer it shows
  // while the pointer rests on the "?" (or on the box itself), a click keeps it open and a
  // second click closes it; a touch screen's tap opens and closes it (only a `mouse` pointer
  // "hovers"); a click or tap elsewhere, or Escape, closes it — and once a click or tap has
  // opened it, that outside click does nothing else (decisions 124); one box open at a time.
  // The box is written into an always-present live region (`role="status"`) when it opens and
  // emptied when it closes, so a screen reader reads its text on opening; the button carries
  // `aria-expanded` and `aria-controls` (that region). Each radio keeps `aria-describedby` to
  // a hidden copy of its own line, so its note is still heard on the choice.

  var openHint = null;          // the open box's record: {wrap, button, live, field, data, pinned, quiet}
  var leaveTimer = null;

  function hintShow(h, pinned) {
    if (leaveTimer) { clearTimeout(leaveTimer); leaveTimer = null; }
    if (openHint === h) { h.pinned = h.pinned || pinned; if (h.pinned) { guardPin(h); } return; }
    if (openHint) { hintHide(openHint); }
    var box = el('span', 'ordpar-hint-box');
    if (h.data.hint) { box.appendChild(el('span', 'ordpar-hint-line', h.data.hint)); }
    h.data.lines.forEach(function (ln) {
      var row = el('span', 'ordpar-hint-line');
      row.appendChild(el('strong', null, ln.label + ':'));
      row.appendChild(doc.createTextNode(' ' + ln.text));
      box.appendChild(row);
    });
    if (h.data.link) {
      // a box's way on (the presets' to Help, decisions 161)
      var more = el('a', null, h.data.link.text);
      more.href = h.data.link.href;
      box.appendChild(el('span', 'ordpar-hint-line')).appendChild(more);
    }
    h.live.appendChild(box);
    h.button.setAttribute('aria-expanded', 'true');
    h.pinned = pinned;
    openHint = h;
    if (pinned) { guardPin(h); }
    hintPlace(h, box);
  }

  // decisions 124: a box opened by a click or tap is pinned with the shell's guard
  // (`shell.js` `hintGuard`), so a click or tap outside it closes it and does nothing else
  function guard() { return shell() && shell().hintGuard; }
  function guardPin(h) {
    var g = guard();
    if (g) { g.pin(h.wrap, function () { hintHide(h); }); }
  }

  function hintHide(h) {
    if (!h) { return; }
    h.live.textContent = '';
    h.button.setAttribute('aria-expanded', 'false');
    h.pinned = false;
    if (guard()) { guard().unpin(h.wrap); }
    if (openHint === h) { openHint = null; }
  }

  /** Under the title line, left-aligned with the "?" where the box fits, else moved left so its
   *  right edge meets the fieldset's (the sheet keeps the box no wider than the fieldset). */
  function hintPlace(h, box) {
    if (!box.getBoundingClientRect) { return; }
    var f = h.field.getBoundingClientRect(), b = h.button.getBoundingClientRect();
    box.style.top = Math.round(b.bottom - f.top + 4) + 'px';
    var w = box.getBoundingClientRect().width;
    box.style.left = Math.round(Math.max(0, Math.min(b.left - f.left, f.width - w))) + 'px';
  }

  function hovered(node) {
    try { return node.matches(':hover'); } catch (e) { return false; }
  }

  /** The "?" and its live region, appended to `legend`; `name` is the setting's title as the
   *  button's accessible name gives it ("About this setting: <title>"). */
  function hintControl(sp, data, group, legend, name) {
    var wrap = el('span', 'ordpar-hint');
    var button = el('button', 'ordpar-hint-button', '?');
    button.type = 'button';
    button.setAttribute('aria-label', t('settings.hintButton', { title: name }));
    button.setAttribute('aria-expanded', 'false');
    var live = el('span', 'ordpar-hint-live');
    live.id = 'ordpar-' + sp.key + '-hint';
    live.setAttribute('role', 'status');
    button.setAttribute('aria-controls', live.id);
    wrap.appendChild(button);
    wrap.appendChild(live);
    legend.appendChild(doc.createTextNode(' '));
    legend.appendChild(wrap);
    var h = { wrap: wrap, button: button, live: live, field: group, data: data, pinned: false, quiet: false };
    button.addEventListener('click', function () {
      if (openHint === h && h.pinned) { hintHide(h); h.quiet = hovered(wrap); } else { hintShow(h, true); }
    });
    // the pointer resting on the "?" or its box: a mouse only (a touch's tap is the click above);
    // `quiet` after a click closed it, until the pointer leaves, so it does not reopen at once
    wrap.addEventListener('pointerenter', function (e) {
      if (e.pointerType !== 'mouse') { return; }
      if (openHint === h) { if (leaveTimer) { clearTimeout(leaveTimer); leaveTimer = null; } return; }
      if (h.quiet || (openHint && openHint.pinned)) { return; }
      hintShow(h, false);
    });
    wrap.addEventListener('pointerleave', function (e) {
      if (e.pointerType !== 'mouse') { return; }
      h.quiet = false;
      if (openHint !== h || h.pinned) { return; }
      // a short grace, so the pointer can cross the gap between the "?" and the box
      leaveTimer = setTimeout(function () {
        leaveTimer = null;
        if (openHint === h && !h.pinned) { hintHide(h); }
      }, 200);
    });
    return h;
  }

  /** One setting's fieldset. `subId`: the id of the subsection heading it sits under
   *  (decisions 85), which then leads its accessible name — "Small articles, Language" — so a
   *  label shortened under its heading is still clear read alone; the title stays its visible
   *  name. The name is the title's own span, not the whole legend, which since decisions 99
   *  also holds the "?" and its box. */
  function field(sp, subId) {
    var group = el('fieldset', 'ordpar-field');
    var legend = el('legend');
    var title = el('span', 'ordpar-field-title', t('settings.' + sp.key));
    title.id = 'ordpar-' + sp.key + '-legend';
    legend.appendChild(title);
    group.appendChild(legend);
    group.setAttribute('aria-labelledby', (subId ? subId + ' ' : '') + title.id);
    var list = choices(sp);
    var data = hintOf(sp, list);
    if (data) {
      var name = (subId && sp.sub ? t('settings.sub.' + sp.sub) + ', ' : '') + t('settings.' + sp.key);
      hintControl(sp, data, group, legend, name);
    }
    group.setAttribute('data-setting', sp.key);
    group.hidden = !shown(sp);
    var current = shell().getSetting(sp.key);
    if (sp.control === 'select') {
      // a drop-down (decisions 112: a number box or a drop-down menu):
      // on a phone the phone's own picker, nothing to type; the same fieldset, title and "?"
      // as every other setting, the choices as its options, the default first (107)
      var box = el('div', 'ordpar-select');
      var select = el('select');
      select.id = 'ordpar-' + sp.key;
      select.setAttribute('data-key', sp.key);
      select.setAttribute('aria-labelledby', (subId ? subId + ' ' : '') + title.id);
      list.forEach(function (ch) {
        var opt = el('option', null, ch.label);
        opt.value = ch.value;
        opt.selected = current === ch.value;
        select.appendChild(opt);
      });
      select.addEventListener('change', function () { shell().setSetting(sp.key, select.value); });
      box.appendChild(select);
      group.appendChild(box);
      return group;
    }
    list.forEach(function (ch) {
      var id = 'ordpar-' + sp.key + '-' + ch.value;
      var wrap = el('div', 'ordpar-radio');
      var input = el('input');
      input.type = 'radio';
      input.name = 'ordpar-' + sp.key;
      input.value = ch.value;
      input.id = id;
      input.checked = current === ch.value;
      input.setAttribute('data-key', sp.key);
      input.addEventListener('change', function () {
        if (input.checked) { shell().setSetting(sp.key, ch.value); }
      });
      var label = el('label');
      label.htmlFor = id;
      if (ch.colour) { label.appendChild(swatch(ch.colour)); label.appendChild(doc.createTextNode(' ')); }
      label.appendChild(doc.createTextNode(ch.label));
      wrap.appendChild(input);
      wrap.appendChild(label);
      // the choice's line: shown in the setting's "?" box since decisions 99; a hidden copy here
      // keeps it the radio's description (an element referenced by `aria-describedby` gives its
      // text even when hidden)
      var noteText = noteOf(sp, ch);
      if (noteText) {
        var note = el('span', 'ordpar-choice-note', noteText);
        note.id = id + '-note';
        note.hidden = true;
        input.setAttribute('aria-describedby', note.id);
        wrap.appendChild(note);
      }
      group.appendChild(wrap);
    });
    return group;
  }

  /** Every radio in step with the stored settings — after a change elsewhere (another radio,
   *  a reset, an import) without redrawing, so the focus stays where it is. */
  function sync() {
    var sh = shell();
    Array.prototype.forEach.call(doc.querySelectorAll('input[data-key]'), function (input) {
      input.checked = sh.getSetting(input.getAttribute('data-key')) === input.value;
    });
    Array.prototype.forEach.call(doc.querySelectorAll('select[data-key]'), function (select) {
      select.value = sh.getSetting(select.getAttribute('data-key'));
    });
    sh.SETTINGS.forEach(function (sp) {
      var group = doc.querySelector('fieldset[data-setting="' + sp.key + '"]');
      if (group) { group.hidden = !shown(sp); }
    });
    syncPresets();
  }

  /* ------------------------------------------------------- export / import */
  // (decisions 60, brief 60 item 6; on the favourites page until decisions 63)

  function exportText(P) {
    var sh = shell();
    return JSON.stringify(P.exportData(sh ? sh.getSetting : null), null, 1) + '\n';
  }

  /** The files the share sheet may take, in the order to offer them (Android's Chrome).
   *  Chrome shares only an allow-list of file types; on Robin's phone (2026-10-19) a JSON file
   *  passed `canShare` yet "Send the file" did nothing, while a link share worked — so the
   *  `.txt` (`text/plain`, the export's own name since decisions 60) is offered FIRST and a
   *  `.json` copy only after it (decisions 63 fix). [] when the browser cannot share files. */
  function shareables(text, name) {
    var nav = global.navigator || {};
    if (!nav.share || !nav.canShare || typeof global.File !== 'function') { return []; }
    var tries = [[name, 'text/plain'], [name.replace(/\.txt$/, '.json'), 'application/json']];
    var out = [];
    for (var i = 0; i < tries.length; i++) {
      try {
        var f = new global.File([text], tries[i][0], { type: tries[i][1] });
        if (nav.canShare({ files: [f] })) { out.push(f); }
      } catch (e) { /* not this one */ }
    }
    return out;
  }

  function errorText(err) {
    return err ? (err.name || 'Error') + ': ' + (err.message || String(err)) : 'unknown';
  }

  /** Share `files[0]`, called straight from the click (the share sheet needs the user's
   *  activation). The reader closing the sheet (`AbortError`) does nothing; any other refusal
   *  tries the next file at once, and when none is left the file is downloaded instead and the
   *  status line names the error, so the next phone test shows what happened. */
  function shareFile(files, text, name) {
    var file = files[0];
    global.navigator.share({ files: [file], title: name }).catch(function (err) {
      if (err && err.name === 'AbortError') { return; }
      if (files.length > 1) { shareFile(files.slice(1), text, name); return; }
      download(text, name);
      say(t('transfer.shareFailed', { error: errorText(err), name: name }));
    });
  }

  /** Download `text` as the file `name` — `text/plain`, the export being a `.txt` (decisions 60). */
  function download(text, name) {
    var blob = new global.Blob([text], { type: 'text/plain' });
    var url = global.URL.createObjectURL(blob);
    var a = el('a');
    a.href = url;
    a.download = name;
    a.hidden = true;
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
    global.setTimeout(function () { global.URL.revokeObjectURL(url); }, 2000);
  }

  function readFile(file) {
    if (file.text) { return file.text(); }
    return new Promise(function (resolve, reject) {
      var r = new global.FileReader();
      r.onload = function () { resolve(String(r.result)); };
      r.onerror = reject;
      r.readAsText(file);
    });
  }

  function transfer() {
    var P = global.ordparPersonal;
    var box = el('fieldset', 'ordpar-field ordpar-transfer');
    box.appendChild(el('legend', null, t('transfer.title')));
    if (!P) { return box; }
    box.appendChild(el('p', 'ordpar-note', t('transfer.intro')));
    var actions = el('div', 'ordpar-settings-actions');

    var exp = el('button', 'ordpar-button is-quiet ordpar-export', t('transfer.export'));
    exp.type = 'button';
    exp.addEventListener('click', function () {
      var name = P.exportName(new Date());
      download(exportText(P), name);
      say(t('transfer.exported', { name: name }));
    });
    actions.appendChild(exp);

    // the share sheet, only where the browser can share a file (decisions 60 item 6)
    var probe = shareables('{}', P.exportName(new Date()));
    if (probe.length) {
      var send = el('button', 'ordpar-button is-quiet ordpar-share-file', t('transfer.share'));
      send.type = 'button';
      send.addEventListener('click', function () {
        var name = P.exportName(new Date());
        var text = exportText(P);
        var files = shareables(text, name);
        if (!files.length) { download(text, name); say(t('transfer.exported', { name: name })); return; }
        shareFile(files, text, name);
      });
      actions.appendChild(send);
    }

    var input = el('input', 'ordpar-import-input');
    input.type = 'file';
    input.accept = '.json,.txt,application/json,text/plain';
    input.hidden = true;
    input.id = 'ordpar-import-file';
    var imp = el('button', 'ordpar-button is-quiet ordpar-import', t('transfer.import'));
    imp.type = 'button';
    imp.addEventListener('click', function () { input.click(); });
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      input.value = '';
      if (!file) { return; }
      readFile(file).then(function (text) {
        var res = P.importText(text);
        if (!res.ok) { say(t('transfer.' + res.error)); return; }
        say(t('transfer.done', { f: res.added.favourites, h: res.added.history }));
        var sh = shell();
        if (sh && sh.applyAll) { sh.applyAll(); }
      }, function () { say(t('transfer.parse')); });
    });
    actions.appendChild(imp);
    actions.appendChild(input);
    box.appendChild(actions);
    return box;
  }

  /** Reset settings and delete stored data (as the old dialog had them). */
  function stored() {
    var box = el('fieldset', 'ordpar-field ordpar-stored');
    box.appendChild(el('legend', null, t('settings.storedTitle')));
    box.appendChild(el('p', 'ordpar-note', t('settings.stored')));
    var row = el('div', 'ordpar-settings-actions');
    var reset = el('button', 'ordpar-button ordpar-settings-reset', t('settings.reset'));
    reset.type = 'button';
    reset.addEventListener('click', function () {
      Promise.resolve(shell().resetSettings()).then(function () { sync(); say(t('settings.resetDone')); });
    });
    var wipe = el('button', 'ordpar-button ordpar-settings-delete', t('settings.delete'));
    wipe.type = 'button';
    wipe.addEventListener('click', function () {
      shell().deleteStoredData();
      sync();
      say(t('settings.deleted'));
    });
    row.appendChild(reset);
    row.appendChild(wipe);
    box.appendChild(row);
    // decisions 136: what Reset resets (every key of `ordparShell.KEYS`, the style too), beside
    // the Presets' Default, which resets the Article settings only
    box.appendChild(el('p', 'ordpar-note ordpar-reset-note', t('settings.resetNote')));
    popup(box);
    return box;
  }

  /*
   * Site decisions 146 (Robin, 2026-10-27/28): "Copy the address for a pop-up dictionary", after
   * "Reset settings" and its line, in the same look — the search address with the SAVED settings
   * (`ordparShell.popupAddress`, the one code `/more/` uses too), its line under it with the link
   * to `/more/#popup`, and "Address copied." in the page's status after a click, as "Settings
   * reset.". Where the clipboard is refused, the address shows as a line of code, selected, and
   * nothing is said (`copyText`).
   */
  function popup(box) {
    var row = el('div', 'ordpar-settings-actions ordpar-popup-actions');
    var btn = el('button', 'ordpar-button ordpar-settings-popup', t('settings.popup'));
    btn.type = 'button';
    row.appendChild(btn);
    box.appendChild(row);
    var parts = t('settings.popupNote').split('{link}');
    var note = el('p', 'ordpar-note ordpar-reset-note ordpar-popup-note');
    note.appendChild(doc.createTextNode(parts[0]));
    var a = el('a', null, t('settings.popupLink'));
    a.href = base() + 'more/#popup';
    note.appendChild(a);
    if (parts.length > 1 && parts[1]) { note.appendChild(doc.createTextNode(parts[1])); }
    box.appendChild(note);
    var line = el('div', 'ordpar-code ordpar-popup-line');
    var code = el('code');
    line.appendChild(code);
    line.hidden = true;
    box.appendChild(line);
    btn.addEventListener('click', function () {
      var sh = shell(), text = sh.popupAddress();
      code.textContent = text;
      sh.copyText(text, code, function () { line.hidden = false; }).then(function (ok) {
        if (ok) { say(t('settings.popupDone')); }
      });
    });
  }

  /* ---------------------------------------------------------------- the page */

  /** "← Back": the browser's history when the reader came here from this site, else home. */
  function backLink() {
    var p = el('p', 'ordpar-back-row');
    var a = el('a', 'ordpar-back');
    a.href = base();
    var arrow = el('span', null, '← ');
    arrow.setAttribute('aria-hidden', 'true');
    a.appendChild(arrow);
    a.appendChild(doc.createTextNode(t('settings.back')));
    a.addEventListener('click', function (e) {
      var ref = doc.referrer;
      var same = false;
      try { same = !!ref && new URL(ref).origin === global.location.origin; } catch (x) { /* none */ }
      if (same && global.history.length > 1) { e.preventDefault(); global.history.back(); }
    });
    p.appendChild(a);
    return p;
  }

  /** A subsection's line under its heading (decisions 126, Robin 2026-10-25): drawn when the
   *  strings have `settings.sub.<sub>.intro`, in the page's explanatory style (`ordpar-note`).
   *  The subsection then becomes a group named by its heading and described by the line, so a
   *  screen reader moving from field to field still hears it once, on entering. Only Small
   *  articles has one. */
  function intro(box, h3, sub) {
    var key = 'settings.sub.' + sub + '.intro';
    if (t(key) === key) { return null; }
    var p = el('p', 'ordpar-note ordpar-settings-intro', t(key));
    p.id = h3.id.replace(/-title$/, '-intro');
    box.appendChild(p);
    box.setAttribute('role', 'group');
    box.setAttribute('aria-labelledby', h3.id);
    box.setAttribute('aria-describedby', p.id);
    return p;
  }

  function render(main) {
    var sh = shell();
    openHint = null;
    main.textContent = '';
    var wrap = el('div', 'ordpar-settings-page');
    wrap.appendChild(backLink());
    var h1 = el('h1', null, t('settings.title'));
    h1.tabIndex = -1;
    wrap.appendChild(h1);
    wrap.appendChild(el('p', 'ordpar-note', t('settings.applied')));

    var jump = el('nav');
    jump.setAttribute('aria-label', t('settings.jump'));
    var ul = el('ul', 'ordpar-jump');
    SECTIONS.forEach(function (id) {
      var a = el('a', null, t('settings.section.' + id));
      a.href = '#' + id;
      ul.appendChild(el('li')).appendChild(a);
    });
    jump.appendChild(ul);
    wrap.appendChild(jump);
    wrap.appendChild(presets());   // decisions 136: above the sections

    SECTIONS.forEach(function (id) {
      var sec = el('section', 'ordpar-settings-section');
      sec.id = id;
      var h2 = el('h2', null, t('settings.section.' + id));
      h2.id = id + '-title';
      sec.setAttribute('aria-labelledby', h2.id);
      sec.appendChild(h2);
      // the subsections (decisions 85, Robin 2026-10-21): a setting with a `sub` goes under
      // that subsection's heading, one level below the section's, in the table's order
      // "Loading, offline and your data": a setting there with no subsection (decisions 104,
      // "Send usage statistics") is drawn after the offline copy and the transfer, just before
      // the stored data, whose "Delete stored data" turns it back on
      var sub = null, box = sec, late = [];
      sh.SETTINGS.forEach(function (sp) {
        if (sp.section !== id || !drawn(sp)) { return; }
        if (sp.key === 'colour' && !(sh.colours() || []).length) { return; }
        if (id === 'data' && !sp.sub) { late.push(sp); return; }
        if ((sp.sub || null) !== sub) {
          sub = sp.sub || null;
          box = sec;
          if (sub) {
            box = el('div', 'ordpar-settings-sub');
            var h3 = el('h3', null, t('settings.sub.' + sub));
            h3.id = id + '-' + sub + '-title';
            box.appendChild(h3);
            intro(box, h3, sub);
            sec.appendChild(box);
          }
        }
        box.appendChild(field(sp, sub ? id + '-' + sub + '-title' : null));
      });
      if (id === 'data') {
        // decisions 61: the offline copy (offline.js draws and redraws its own section)
        if (global.ordparOffline) {
          try { sec.appendChild(global.ordparOffline.section(t, sh.lang)); } catch (e) { /* its own bug */ }
        }
        sec.appendChild(transfer());
        late.forEach(function (sp) { sec.appendChild(field(sp, null)); });
        sec.appendChild(stored());
      }
      wrap.appendChild(sec);
    });

    var st = el('p', 'ordpar-settings-status');
    st.setAttribute('role', 'status');
    st.textContent = message;
    wrap.appendChild(st);
    main.appendChild(wrap);
  }

  function start() {
    var main = doc.querySelector('[data-ordpar-settings]');
    if (!main || !shell()) { return; }
    var draw = function () {
      doc.title = t('settings.title') + ' — ' + t('site.name');
      render(main);
    };
    draw();
    // a jump link's target, when the page was opened at one (/settings/#data)
    if (global.location.hash) {
      var target = doc.getElementById(global.location.hash.slice(1));
      if (target) { target.scrollIntoView(); }
    }
    shell().onChange(function (key) {
      if (key === 'lang') { draw(); } else { sync(); }
    });
    // a setting changed in another tab (decisions 136: the pressed preset follows it; the radios
    // with it). `key` null: that tab cleared the storage ("Delete stored data")
    global.addEventListener('storage', function (e) {
      if (!e || e.key == null || shell().KEYS.indexOf(e.key) !== -1) { sync(); }
    });
    // decisions 99: a click outside a box the mouse only rests on closes it and acts as usual.
    // A box opened by a click or tap is the shell's guard's (decisions 124: an outside click or
    // tap closes it and does nothing else; `shell.js` `hintGuard`). Escape closes either (the
    // focus goes back to its "?" when it was inside the box)
    doc.addEventListener('pointerdown', function (e) {
      if (openHint && !openHint.pinned && !(e.target && openHint.wrap.contains(e.target))) { hintHide(openHint); }
    });
    doc.addEventListener('keydown', function (e) {
      if (openHint && (e.key === 'Escape' || e.key === 'Esc')) {
        var h = openHint;
        hintHide(h);
        h.quiet = hovered(h.wrap);
        if (h.wrap.contains(doc.activeElement) && doc.activeElement !== h.button) { h.button.focus(); }
      }
    });
  }

  // the pure parts, for the tests (decisions 99)
  global.ordparSettings = { noteOf: noteOf, hintOf: hintOf, field: field, intro: intro, drawn: drawn, shown: shown,
    PRESETS: PRESETS, presetValues: presetValues, matching: matching };

  function whenReady() { ((shell() && shell().ready) || Promise.resolve()).then(start); }
  if (doc.readyState === 'loading') { doc.addEventListener('DOMContentLoaded', whenReady); }
  else { whenReady(); }
}(typeof globalThis !== 'undefined' ? globalThis : this));
