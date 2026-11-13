/*! Ordpar — the install offer (site-review decisions 68). Spec: ordpar/docs/offline-app.md § 11.
 *
 * Loaded by EVERY page, in the combined script before shell.js (`page.ARTICLE_JS_PARTS`,
 * `page.SHELL_JS_PARTS`). It
 *   - catches Chrome's install event (`beforeinstallprompt`, Chromium only), always cancels
 *     Chrome's own install bar, and keeps the event for this page (an event lives only in its
 *     own document, and `prompt()` works once per event);
 *   - shows the ONCE-ONLY OFFER, a bar along the bottom of the window, when the event fires and
 *     the device's record allows: never inside the installed app, never once answered
 *     ("Install" or "No thanks"), never after its second showing, and never twice in one
 *     browsing session — so an offer left unanswered shows once more on a later visit, then
 *     never again; after either answer a short note points to Settings → Offline;
 *   - draws the line at the top of Settings → Offline (`line(t)`, called by offline.js), in its
 *     six cases, with the "Install app" button where this page holds an event;
 *   - makes the footer's phone-only hint (`hint(links)`, called by shell.js `addChrome`).
 *
 * The record is localStorage `install-offer`, beside offline.js's `offline` and
 * `offline-update`: not a setting, so "Reset settings" leaves it; "Delete stored data" clears
 * it, and the offer may then show again. Nothing leaves the device.
 */
(function (global) {
  'use strict';

  var REC = 'install-offer';          // localStorage: {shown, answer, installed, at}
  var SESSION = 'ordpar-install-shown'; // sessionStorage: the bar has shown in this visit
  var MAX_SHOWN = 2;
  var NOTE_MS = 8000;
  var SETTINGS_HASH = 'settings/#data';

  /* -------------------------------------------------------- the pure rules */

  /** May the bar show now? `rec` the device's record (or null), `sessionShown` whether it
   *  has already shown in this browsing session, `standalone` whether this is the app. */
  function mayOffer(rec, sessionShown, standalone) {
    if (standalone || sessionShown) { return false; }
    rec = rec || {};
    if (rec.answer || rec.installed) { return false; }
    return (rec.shown | 0) < MAX_SHOWN;
  }

  /** The record after the bar has shown once more. */
  function afterShown(rec, now) {
    var r = copy(rec);
    r.shown = (r.shown | 0) + 1;
    r.at = now;
    return r;
  }

  /** The record after an answer: `install` (the button pressed), `installed` (Chrome's dialog
   *  accepted, or the app installed by any route), `dismissed` (Chrome's dialog cancelled),
   *  `no` (No thanks). Any of them ends the offer for good. */
  function afterAnswer(rec, answer, now) {
    var r = copy(rec);
    r.answer = answer;
    if (answer === 'installed') { r.installed = true; }
    r.at = now;
    return r;
  }

  /**
   * The Settings line's case (the proposal's step 3), from what this page knows:
   *   app        inside the installed app
   *   installed  in a tab, the app known installed (`getInstalledRelatedApps`, or installed
   *              from this page), or installed earlier on this browser by the record and no
   *              install event since
   *   offer      this page holds an install event: the text and the Install app button
   *   ios        iPhone or iPad: Share → Add to Home Screen
   *   menu       a browser with the install event that has not fired it (yet)
   *   null       every other browser: nothing
   */
  function settingsCase(env) {
    if (env.standalone) { return 'app'; }
    if (env.relatedInstalled || env.installedHere) { return 'installed'; }
    if (env.event) { return 'offer'; }
    if (env.recordInstalled) { return 'installed'; }
    if (env.ios) { return 'ios'; }
    if (env.chromium) { return 'menu'; }
    return null;
  }

  var CASE_KEYS = { app: 'install.inApp', installed: 'install.installed', offer: 'install.can',
                    ios: 'install.ios', menu: 'install.menu' };

  /** Should the footer's hint be made? On a touch screen (its width is the sheet's rule, so a
   *  turned phone follows), never in the app, and only where Settings has a line to lead to. */
  function hintWanted(env) {
    return !!(env.touch && !env.standalone && !env.relatedInstalled && !env.installedHere
              && (env.chromium || env.ios));
  }

  function copy(rec) {
    var r = {};
    if (rec) { for (var k in rec) { if (Object.prototype.hasOwnProperty.call(rec, k)) { r[k] = rec[k]; } } }
    return r;
  }

  /* ------------------------------------------------------------ the device */

  var doc = global.document;
  var nav = global.navigator || {};

  function readRec() {
    try { return JSON.parse(global.localStorage.getItem(REC) || 'null'); } catch (e) { return null; }
  }
  function writeRec(r) {
    try { global.localStorage.setItem(REC, JSON.stringify(r)); } catch (e) { /* full / blocked */ }
  }
  function sessionShown() {
    try { return !!global.sessionStorage.getItem(SESSION); } catch (e) { return false; }
  }
  function markSession() {
    try { global.sessionStorage.setItem(SESSION, '1'); } catch (e) { /* blocked */ }
  }
  function media(q) {
    try { return !!(global.matchMedia && global.matchMedia(q).matches); } catch (e) { return false; }
  }
  function standalone() {
    return nav.standalone === true || media('(display-mode: standalone)')
      || media('(display-mode: fullscreen)') || media('(display-mode: minimal-ui)');
  }
  function ios() {
    var ua = String(nav.userAgent || '');
    return /iPhone|iPad|iPod/.test(ua) || (nav.platform === 'MacIntel' && (nav.maxTouchPoints | 0) > 1);
  }
  function chromium() {
    return 'BeforeInstallPromptEvent' in global || 'onbeforeinstallprompt' in global;
  }
  function touch() { return media('(pointer: coarse) and (hover: none)'); }

  var deferred = null;            // this page's install event, until prompt() is called
  var installedHere = false;      // the app was installed from this page (or appinstalled fired)
  var related = null;             // true / false once getInstalledRelatedApps has answered
  var relatedAsked = null;
  var listeners = [];

  function env() {
    var rec = readRec() || {};
    return { standalone: standalone(), relatedInstalled: related === true, installedHere: installedHere,
             event: !!deferred, recordInstalled: !!rec.installed, ios: ios(), chromium: chromium(),
             touch: touch() };
  }

  /** `getInstalledRelatedApps()` once per page (the manifest's `related_applications` entry
   *  for the site's own web app; Android Chrome 84+, desktop Chrome and Edge 140+). */
  function askRelated() {
    if (relatedAsked) { return relatedAsked; }
    if (typeof nav.getInstalledRelatedApps !== 'function') {
      related = false;
      relatedAsked = Promise.resolve(false);
      return relatedAsked;
    }
    relatedAsked = Promise.resolve().then(function () { return nav.getInstalledRelatedApps(); })
      .then(function (list) { related = !!(list && list.length); return related; })
      .catch(function () { related = false; return false; })
      .then(function (v) { emit(); return v; });
    return relatedAsked;
  }

  function emit() {
    listeners = listeners.filter(function (fn) {
      try { return fn() !== false; } catch (e) { return false; }
    });
  }

  function t(key, vars) {
    var sh = global.ordparShell;
    return sh ? sh.t(key, vars) : key;
  }
  function base() { return global.ORDPAR_BASE || '/'; }
  function el(tag, cls, text) {
    var n = doc.createElement(tag);
    if (cls) { n.className = cls; }
    if (text != null) { n.textContent = text; }
    return n;
  }

  /* ------------------------------------------------------------ the prompt */

  /** Chrome's own dialog, from a press of Install (the bar) or Install app (Settings). The note
   *  after a dialog cancelled only under the bar: on the Settings page it would point to itself. */
  function prompt(fromBar) {
    var ev = deferred;
    deferred = null;              // prompt() works once per event
    writeRec(afterAnswer(readRec(), 'install', Date.now()));
    hideBar();
    emit();
    if (!ev) { return Promise.resolve(null); }
    var choice;
    try {
      ev.prompt();
      choice = Promise.resolve(ev.userChoice);
    } catch (e) { choice = Promise.resolve(null); }
    return choice.catch(function () { return null; }).then(function (c) {
      var outcome = c && c.outcome;
      if (outcome === 'accepted') { installed(); }
      else {
        writeRec(afterAnswer(readRec(), outcome === 'dismissed' ? 'dismissed' : 'install', Date.now()));
        if (fromBar) { note('install.noteLater'); }
      }
      emit();
      return outcome || null;
    });
  }

  var noted = false;
  function installed() {
    installedHere = true;
    deferred = null;
    var rec = readRec() || {};
    writeRec(afterAnswer(rec, 'installed', Date.now()));
    hideBar();
    if (!standalone()) { note('install.noteInstalled'); }
    var hintEl = doc && doc.querySelector('.ordpar-install-hint');
    if (hintEl && hintEl.parentNode) { hintEl.parentNode.removeChild(hintEl); }
    emit();
  }

  /* --------------------------------------------------------------- the bar */

  var bar = null;

  function showBar() {
    if (bar || !doc.body) { return; }
    bar = el('div', 'ordpar-install-bar');
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-labelledby', 'ordpar-install-title');
    var inner = el('div', 'ordpar-install-inner');
    var words = el('div', 'ordpar-install-words');
    var title = el('p', 'ordpar-install-title', t('install.title'));
    title.id = 'ordpar-install-title';
    words.appendChild(title);
    words.appendChild(el('p', 'ordpar-install-text', t('install.text')));
    inner.appendChild(words);
    var actions = el('div', 'ordpar-install-actions');
    var yes = el('button', 'ordpar-button', t('install.install'));
    yes.type = 'button';
    yes.addEventListener('click', function () { prompt(true); });
    var no = el('button', 'ordpar-button is-quiet', t('install.no'));
    no.type = 'button';
    no.addEventListener('click', function () {
      writeRec(afterAnswer(readRec(), 'no', Date.now()));
      hideBar();
      note('install.noteLater');
      emit();
    });
    actions.appendChild(yes);
    actions.appendChild(no);
    inner.appendChild(actions);
    bar.appendChild(inner);
    doc.body.appendChild(bar);
    room(bar);
    announce(t('install.title'));
  }

  function hideBar() {
    if (!bar) { return; }
    if (bar.parentNode) { bar.parentNode.removeChild(bar); }
    bar = null;
    room(null);
  }

  /** The bands along the bottom of the window, lowest first: this file's bar or note, then the
   *  update note (`offline.js`, decisions 94), which stacks above them so neither covers the
   *  other. */
  var BANDS = ['.ordpar-install-bar', '.ordpar-install-note', '.ordpar-update-note'];

  /** Room below the page for the bands, on <html>, so the footer can be scrolled clear of them,
   *  and nothing on the page moves (the body's own height is untouched); each band set above
   *  the ones below it. Called whenever a band comes or goes (`offline.js` too). */
  function room() {
    var root = doc.documentElement, h = 0;
    for (var i = 0; i < BANDS.length; i++) {
      var n = doc.querySelector(BANDS[i]);
      if (!n) { continue; }
      n.style.bottom = h ? h + 'px' : '';
      h += n.offsetHeight;
    }
    root.style.paddingBottom = h ? h + 'px' : '';
  }

  var live = null;
  function announce(text) {
    if (!live) {
      live = el('div', 'ordpar-visually-hidden');
      live.setAttribute('data-nosnippet', '');   // site decisions 154: set at the making
      live.setAttribute('role', 'status');
      doc.body.appendChild(live);
    }
    live.textContent = '';
    global.setTimeout(function () { live.textContent = text; }, 100);
  }

  /** The short note after an answer, with its link to Settings → Offline, for a few seconds
   *  (held while the pointer or the focus is on it). */
  function note(key) {
    if (noted || !doc.body) { return; }
    noted = true;
    var box = el('div', 'ordpar-install-note');
    box.setAttribute('role', 'status');
    var p = el('p');
    box.appendChild(p);
    doc.body.appendChild(box);
    global.setTimeout(function () {
      var parts = String(t(key, { link: '\u0000' })).split('\u0000');
      p.appendChild(doc.createTextNode(parts[0]));
      if (parts.length > 1) {
        var a = el('a', null, t('install.link'));
        a.href = base() + SETTINGS_HASH;
        p.appendChild(a);
        p.appendChild(doc.createTextNode(parts.slice(1).join('')));
      }
      room(box);
    }, 50);
    var timer = null;
    function go() {
      if (box.parentNode) { box.parentNode.removeChild(box); }
      room(null);
    }
    function arm() { global.clearTimeout(timer); timer = global.setTimeout(go, NOTE_MS); }
    function hold() { global.clearTimeout(timer); }
    box.addEventListener('mouseenter', hold);
    box.addEventListener('focusin', hold);
    box.addEventListener('mouseleave', arm);
    box.addEventListener('focusout', arm);
    arm();
  }

  function offer() {
    if (bar) { return; }
    if (!mayOffer(readRec(), sessionShown(), standalone())) { return; }
    writeRec(afterShown(readRec(), Date.now()));
    markSession();
    showBar();
  }

  /* ------------------------------------------------- the Settings line */

  /** The line at the top of Settings → Offline (offline.js `section`): one of the six cases,
   *  redrawn when the install event arrives, after an install, and when
   *  `getInstalledRelatedApps` answers. `tr(key, vars)` the settings page's strings. */
  function line(tr) {
    tr = tr || t;
    var box = el('div', 'ordpar-install-line');
    var drawn = false;
    function draw() {
      if (drawn && !box.isConnected) { return false; }
      drawn = true;
      box.textContent = '';
      var c = settingsCase(env());
      box.hidden = !c;
      box.setAttribute('data-case', c || 'none');
      if (!c) { return; }
      box.appendChild(el('p', null, tr(CASE_KEYS[c])));
      if (c === 'offer') {
        var b = el('button', 'ordpar-button', tr('install.button'));
        b.type = 'button';
        b.addEventListener('click', function () { prompt(false); });
        box.appendChild(b);
      }
    }
    listeners.push(draw);
    draw();
    askRelated();
    return box;
  }

  /* --------------------------------------------------- the footer hint */

  /** The footer's hint (decisions 68: phones only, Robin): made by shell.js `addChrome` into
   *  the footer's links. Its text is relabelled with the rest of the chrome. Where Chrome can
   *  say whether the app is installed here, the hint keeps its room but stays invisible until
   *  it has answered, and goes if it is. */
  function hint(links) {
    var e0 = env();
    if (!links || !hintWanted(e0) || links.querySelector('.ordpar-install-hint')) { return null; }
    var a = el('a', 'ordpar-install-hint', t('install.hint'));
    a.setAttribute('data-ordpar-string', 'install.hint');
    a.setAttribute('href', base() + SETTINGS_HASH);
    links.appendChild(doc.createTextNode('\n'));   // the footer's links: a flex row (site decisions 154)
    links.appendChild(a);
    if (typeof nav.getInstalledRelatedApps === 'function' && related !== false) {
      a.style.visibility = 'hidden';
      askRelated().then(function (yes) {
        if (yes) { if (a.parentNode) { a.parentNode.removeChild(a); } }
        else { a.style.visibility = ''; }
      });
    }
    return a;
  }

  /* ---------------------------------------------------------------- wiring */

  if (global.addEventListener && doc) {
    global.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();         // Chrome's own install bar never shows: ours replaces it
      deferred = e;
      installedHere = false;
      if (doc.body && global.ordparShell) { offer(); }
      else { doc.addEventListener('DOMContentLoaded', function () { if (deferred) { offer(); } }); }
      emit();
    });
    global.addEventListener('appinstalled', function () {
      installed();
      // site decisions 104: an install counted, with nothing identifying (events.js decides
      // whether it is sent at all)
      if (global.ordparEvents) { try { global.ordparEvents.install(); } catch (e) { /* lost */ } }
    });
  }

  var api = {
    line: line,
    hint: hint,
    prompt: prompt,
    has: function () { return !!deferred; },
    state: function () { return { rec: readRec(), session: sessionShown(), env: env(), bar: !!bar }; },
    onChange: function (fn) { listeners.push(fn); },
    room: room,
    mayOffer: mayOffer,
    afterShown: afterShown,
    afterAnswer: afterAnswer,
    settingsCase: settingsCase,
    hintWanted: hintWanted,
    REC: REC,
    SESSION: SESSION,
    MAX_SHOWN: MAX_SHOWN
  };
  global.ordparInstall = api;
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
}(typeof globalThis !== 'undefined' ? globalThis : this));
