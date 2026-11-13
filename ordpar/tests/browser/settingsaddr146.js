// Site-review decisions 146 (Robin, 2026-10-27/28): the reader's settings in the address, for a
// pop-up dictionary such as Definer, and the Copy of that address on /more/ and in Settings.
//
// For one viewport (args.w × args.h, args.mobile; args.dark: the SAVED theme dark, else light), in a
// fresh context whose saved settings are SAVED below plus that theme:
//   visit    — `/bm-en/#defs=en&theme=<the other>&mini=en&q=hus` opened: the search goes on to the
//              word's page and shows the address's settings (the other theme, the English
//              definitions alone, the mini's class), the settings part gone from the address,
//              `localStorage`'s settings unchanged, History's entry the plain search;
//   onward   — from there a click on the article's own page link (a page load), then on a
//              cross-reference and the small article's headword (another page load): each page
//              with the visit's settings, `localStorage` still unchanged;
//   fresh    — a new tab in the same browser (the same saved settings, no visit): the saved ones;
//   moreVisit— `/more/` opened in the visit's tab with other settings in its address: its step-4
//              line still the SAVED settings' address;
//   settingsVisit — `/settings/#theme=…&defs=en` in the visit's tab: the page shows the saved ones;
//   more     — `/more/` in the new tab: the step-4 line the saved settings' address, a Copy button
//              beside each code line, each click copies its line (read back from the clipboard)
//              and says "Copied", back to "Copy" after a few seconds; one click still selects a line;
//   settings — `/settings/` in the new tab: the button, its line and link at the bottom after
//              Reset's line; a click copies the same address as /more/ and says "Address copied.";
//   fallback — the clipboard refused (and the copy command): /more/'s button selects its line and
//              says nothing; Settings shows the address as a line, selected, and says nothing.
// With args.shots = {dir, prefix}: /more/'s Definer section and Settings' bottom, before and after
// a click; with args.pair, one article opened with `defs=en&theme=dark` and the same without.
//
// args: { w, h, mobile, dark, shots, pair }
import { writeFileSync } from 'node:fs';
import { open, base, args, run, done, sleep } from './cdp.js';

// `listview` = multi saved (site decisions 158): *hus*, also an inflected form of *huse*, then
// opens its article, whose look and links this test reads (the default shows the list); so the
// addresses carry it too, after the article settings, in the table's order
const SAVED = { defs: 'no', exlimit: '2', listview: 'multi' };
const THEME = args.dark ? 'dark' : 'light';
const OTHER = args.dark ? 'light' : 'dark';
const EXPECT = `https://ordpar.no/bm-en/#theme=${THEME}&defs=no&exlimit=2&listview=multi&q={{str}}`;
const CSS = '.ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; }';
const KEYS_NOT_SETTINGS = ['history', 'favourites', 'offline', 'offline-update', 'install-offer'];

async function until(s, expr, ms = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await s.eval(`!!(${expr})`)) return true;
    await sleep(100);
  }
  return false;
}

/** A page-like handle on another target (a second tab), over the same connection. */
function tab(p, sessionId) {
  return {
    async eval(expr) {
      const r = await p.raw('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }, sessionId);
      if (r.exceptionDetails) throw new Error(expr.slice(0, 100) + ' :: ' + JSON.stringify(r.exceptionDetails).slice(0, 500));
      return r.result.value;
    },
    send: (m, prm) => p.raw(m, prm, sessionId),
  };
}

async function goto(s, url, settle = 500) {
  // a navigation in the page itself, so it works on either handle; the same page with another
  // fragment is reloaded, so its head script runs again (a fragment alone loads nothing)
  await s.eval(`(() => { window.__old = 1; const u = new URL(${JSON.stringify(url)}, location.href);
    const same = u.pathname === location.pathname && u.search === location.search;
    location.href = u.href; if (same) location.reload(); return true; })()`);
  await sleep(300);
  await until(s, `!window.__old && document.readyState === 'complete'`);
  await sleep(settle);
}

async function shot(s, name, selector, to) {
  if (!args.shots) return null;
  await s.eval('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(true))))');
  const opts = { format: 'png' };
  if (selector) {
    // from the element's top to the bottom of `to` (else its own), at most 1,600 px
    const box = await s.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)});
      const z = ${JSON.stringify(to || '')} ? document.querySelector(${JSON.stringify(to || '')}) : e;
      if (!e || !z) return null; e.scrollIntoView({ block: 'start' }); const r = e.getBoundingClientRect();
      const b = z.getBoundingClientRect().bottom;
      return { y: r.top + scrollY, h: Math.min(Math.max(r.height, b - r.top), 1600) }; })()`);
    if (box) {
      await sleep(150);
      opts.captureBeyondViewport = true;
      opts.clip = { x: 0, y: Math.max(0, box.y - 8), width: args.w, height: box.h + 16, scale: 1 };
    }
  }
  const { data } = await s.send('Page.captureScreenshot', opts);
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

async function press(p, s, selector) {
  const r = await s.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)});
    if (!e) return null; e.scrollIntoView({ block: 'center' }); const b = e.getBoundingClientRect();
    return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; })()`);
  if (!r) return false;
  await sleep(120);
  const send = s.send;
  if (args.mobile) {
    await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: r.x, y: r.y }] });
    await sleep(60);
    await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  } else {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: r.x, y: r.y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: r.x, y: r.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: r.x, y: r.y, button: 'left', clickCount: 1 });
  }
  return true;
}

/** What the page shows of the settings this test changes. */
const LOOK = `(() => {
  const E = document.documentElement, cl = E.classList;
  const nb = [...document.querySelectorAll('#ordpar-main .ordpar-pair>span[lang=nb]')];
  const en = [...document.querySelectorAll('#ordpar-main .ordpar-pair>span[lang=en]')];
  const shown = l => l.filter(e => getComputedStyle(e).display !== 'none' && e.getClientRects().length).length;
  // the mini's rule, on a stand-in pair (the class alone says little): its Norwegian hidden?
  const t = document.createElement('span'); t.className = 'mini-pair';
  t.innerHTML = '<span lang="nb">x</span><span lang="en">y</span>'; document.body.appendChild(t);
  const miniNb = getComputedStyle(t.firstChild).display; t.remove();
  return { path: location.pathname, hash: location.hash, night: cl.contains('nightMode'),
    bg: getComputedStyle(document.body).backgroundColor,
    defsEn: cl.contains('ordpar-defs-en'), defsNo: cl.contains('ordpar-defs-no'), miniEn: cl.contains('ordpar-mini-en'),
    exlimit2: cl.contains('ordpar-exlimit-2'),
    pairs: nb.length, nbShown: shown(nb), enShown: shown(en), miniNb,
    visit: sessionStorage.getItem('ordpar-visit') };
})()`;

const STORED = `(() => { const o = {}; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i);
  if (!${JSON.stringify(KEYS_NOT_SETTINGS)}.includes(k)) o[k] = localStorage.getItem(k); } return JSON.stringify(o); })()`;

run(async () => {
  const p = await open({ w: args.w, h: args.h, mobile: !!args.mobile });
  await p.send('Emulation.setFocusEmulationEnabled', { enabled: true });
  const res = {};
  await p.goto(base + '/', 300);
  await p.eval(`(() => { localStorage.setItem('theme', ${JSON.stringify(THEME)});
    const s = ${JSON.stringify(SAVED)}; for (const k in s) localStorage.setItem(k, s[k]); return true; })()`);
  // the clipboard may be read back: grant it to this context
  const { targetInfos } = await p.raw('Target.getTargets', {});
  const href = await p.eval('location.href');
  const me = targetInfos.find(t => t.type === 'page' && t.url === href);
  const ctx = me && me.browserContextId;
  try {
    await p.raw('Browser.grantPermissions', { origin: base || (await p.eval('location.origin')), browserContextId: ctx,
      permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'] });
  } catch (e) { res.grantError = e.message; }
  const before = await p.eval(STORED);
  res.saved = JSON.parse(before);

  // ---- the visit: a search with settings in its address goes on to its word page
  await p.goto(base + `/bm-en/#defs=en&theme=${OTHER}&mini=en&q=hus`, 300);
  await until(p, `location.pathname === '/bm-en/hus/' && document.querySelector('#ordpar-main .ordpar-pair')`);
  await sleep(600);
  res.visit = await p.eval(LOOK);
  res.visit.stored = await p.eval(STORED);
  res.visit.history = await p.eval(`localStorage.getItem('history')`);
  res.visit.href = await p.eval('location.href');

  // ---- onward: the article's own page (a page load), then a small article's headword
  res.onward = {};
  // the result row has no "Article page" link since site decisions 168 (phones 2026-11-05,
  // everywhere since its re-ruling 2026-11-06): the page load goes to the article's own address
  // in the same tab (what the check is about: the tab's visit carried onward)
  const shownRow = `#ordpar-main article.ordpar-result[data-id] .ordpar-result-controls`;
  const hasRow = await until(p, `!!document.querySelector(${JSON.stringify(shownRow)})`, 8000);
  if (hasRow) {
    const loaded = p.waitEvent('Page.loadEventFired');
    await p.eval(`location.assign('/bm-en/' + document.querySelector('#ordpar-main article.ordpar-result[data-id]')
      .getAttribute('data-id') + '/'); true`);
    await loaded; await sleep(600);
    res.onward.article = await p.eval(LOOK);
  }
  // a cross-reference's small article, then its headword
  const xref = `#ordpar-main .ordbok-xref a.ordbok-xword`;
  if (await p.eval(`!!document.querySelector(${JSON.stringify(xref)})`)) {
    await press(p, p, xref);
    const opened = await until(p, `document.querySelector('.ordbok-xmini .mini-hw a')`, 8000);
    res.onward.mini = { opened };
    if (opened) {
      res.onward.mini.look = await p.eval(`(() => { const m = document.querySelector('.ordbok-xmini');
        const nb = [...m.querySelectorAll('.mini-pair>span[lang=nb]')];
        return { pairs: nb.length, nbShown: nb.filter(e => getComputedStyle(e).display !== 'none').length }; })()`);
      const loaded = p.waitEvent('Page.loadEventFired');
      await press(p, p, '.ordbok-xmini .mini-hw a');
      await loaded; await sleep(600);
      res.onward.headword = await p.eval(LOOK);
    }
  }
  res.onward.stored = await p.eval(STORED);

  // ---- /more/ and /settings/ opened in the visit's tab with other settings in their address
  await p.goto(base + `/more/#theme=${OTHER}&defs=en&mini=en`, 300);
  await until(p, `document.querySelector('.ordpar-code-copy')`, 8000);
  res.moreVisit = await p.eval(`({ night: document.documentElement.classList.contains('nightMode'),
    line: document.querySelector('.ordpar-code code').textContent, hash: location.hash })`);
  await p.goto(base + `/settings/#theme=${OTHER}&defs=en`, 300);
  await until(p, `document.querySelector('.ordpar-settings-popup')`, 8000);
  res.settingsVisit = await p.eval(`({ night: document.documentElement.classList.contains('nightMode'),
    defs: (document.querySelector('input[data-key="defs"]:checked') || {}).value || null,
    theme: (document.querySelector('input[data-key="theme"]:checked') || {}).value || null,
    defsClass: document.documentElement.classList.contains('ordpar-defs-en'),
    visitApplied: window.ordparVisit && window.ordparVisit.settings })`);

  // ---- a new tab in the same browser: the saved settings, no visit
  const { targetId } = await p.raw('Target.createTarget', { url: base + '/bm-en/hus/', browserContextId: ctx });
  const { sessionId } = await p.raw('Target.attachToTarget', { targetId, flatten: true });
  const t2 = tab(p, sessionId);
  await t2.send('Page.enable', {}); await t2.send('Runtime.enable', {});
  await t2.send('Emulation.setDeviceMetricsOverride', { width: args.w, height: args.h, deviceScaleFactor: args.mobile ? 3 : 1, mobile: !!args.mobile });
  if (args.mobile) await t2.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await t2.send('Emulation.setFocusEmulationEnabled', { enabled: true });
  await until(t2, `document.readyState === 'complete' && document.querySelector('#ordpar-main .ordpar-pair')`);
  await sleep(500);
  res.fresh = await t2.eval(LOOK);

  // ---- /more/ in the new tab
  await goto(t2, base + '/more/#popup');
  await until(t2, `document.querySelectorAll('.ordpar-code-copy').length === 2`, 8000);
  res.more = await t2.eval(`(() => { const boxes = [...document.querySelectorAll('.ordpar-about .ordpar-code')];
    return { lines: boxes.map(b => b.querySelector('code').textContent),
      buttons: boxes.map(b => { const x = b.querySelector('.ordpar-code-copy'); return x ? x.textContent : null; }),
      looks: boxes.map(b => { const x = b.querySelector('.ordpar-code-copy'), c = getComputedStyle(x);
        return [x.className, c.color, c.backgroundColor, c.borderTopColor, c.fontSize, Math.round(x.getBoundingClientRect().height)]; }),
      beside: boxes.map(b => { const c = b.querySelector('code').getBoundingClientRect(), x = b.querySelector('.ordpar-code-copy').getBoundingClientRect();
        return x.left >= c.right - 1 && Math.abs(x.top - c.top) < 4 && x.right <= innerWidth; }),
      popupMarked: !!document.querySelector('.ordpar-code code[data-ordpar-popup]'),
      night: document.documentElement.classList.contains('nightMode') }; })()`);
  res.more.shotBefore = await shot(t2, 'more-popup', '#popup', '#popup ~ ol + p + p');
  // each button in turn (`data-next` marks the one to press), the clipboard emptied first
  res.more.clicks = [];
  for (let i = 0; i < 2; i++) {
    await t2.eval(`(async () => { try { await navigator.clipboard.writeText('-'); } catch (e) {} return true; })()`);
    await t2.eval(`(document.querySelectorAll('.ordpar-about .ordpar-code-copy').forEach((b, j) => b.toggleAttribute('data-next', j === ${i})), true)`);
    await press(p, t2, '.ordpar-about .ordpar-code-copy[data-next]');
    await sleep(300);
    const after = await t2.eval(`(async () => { const b = document.querySelectorAll('.ordpar-about .ordpar-code-copy')[${i}];
      let clip = null; try { clip = await navigator.clipboard.readText(); } catch (e) { clip = 'ERR ' + e.message; }
      return { label: b.textContent, clip }; })()`);
    if (i === 0) after.shot = await shot(t2, 'more-popup-copied', '#popup', '#popup ~ ol + p + p');
    await sleep(2800);
    after.later = await t2.eval(`document.querySelectorAll('.ordpar-about .ordpar-code-copy')[${i}].textContent`);
    res.more.clicks.push(after);
  }
  // one click on a line still selects it whole
  res.more.select = [];
  for (let i = 0; i < 2; i++) {
    await t2.eval(`(getSelection().removeAllRanges(), document.querySelectorAll('.ordpar-about .ordpar-code code').forEach((c, j) => c.toggleAttribute('data-next', j === ${i})), true)`);
    await press(p, t2, '.ordpar-about .ordpar-code code[data-next]');
    await sleep(150);
    res.more.select.push(await t2.eval(`getSelection().toString()`));
  }

  // ---- Settings in the new tab
  await goto(t2, base + '/settings/');
  await until(t2, `document.querySelector('.ordpar-settings-popup')`, 8000);
  res.settings = await t2.eval(`(() => { const b = document.querySelector('.ordpar-settings-popup');
    const reset = document.querySelector('.ordpar-settings-reset'), note = document.querySelector('.ordpar-popup-note');
    const rn = document.querySelector('.ordpar-reset-note:not(.ordpar-popup-note)');
    const cs = e => { const c = getComputedStyle(e); return [c.color, c.backgroundColor, c.borderTopColor, c.fontSize, c.paddingTop, c.borderRadius]; };
    const a = note.querySelector('a');
    return { button: b.textContent, note: note.textContent, link: a ? [a.textContent, a.getAttribute('href')] : null,
      noteClass: note.className, noteFont: [getComputedStyle(note).fontSize, getComputedStyle(note).color, getComputedStyle(note).fontStyle],
      resetNoteFont: [getComputedStyle(rn).fontSize, getComputedStyle(rn).color, getComputedStyle(rn).fontStyle],
      look: cs(b), resetLook: cs(reset),
      order: [rn, b, note].map(e => Math.round(e.getBoundingClientRect().top)),
      inStored: !!b.closest('.ordpar-stored'), lineHidden: document.querySelector('.ordpar-popup-line').hidden,
      night: document.documentElement.classList.contains('nightMode') }; })()`);
  res.settings.shotBefore = await shot(t2, 'settings-bottom', '.ordpar-stored', '.ordpar-settings-status');
  await t2.eval(`(async () => { try { await navigator.clipboard.writeText('-'); } catch (e) {} return true; })()`);
  await press(p, t2, '.ordpar-settings-popup');
  await sleep(400);
  res.settings.after = await t2.eval(`(async () => { let clip = null; try { clip = await navigator.clipboard.readText(); } catch (e) { clip = 'ERR ' + e.message; }
    return { clip, status: document.querySelector('.ordpar-settings-status').textContent,
      lineHidden: document.querySelector('.ordpar-popup-line').hidden }; })()`);
  res.settings.shotAfter = await shot(t2, 'settings-bottom-copied', '.ordpar-stored', '.ordpar-settings-status');

  // ---- the clipboard refused (and the copy command): select, say nothing
  const refuse = `(navigator.clipboard.writeText = () => Promise.reject(new Error('refused')), document.execCommand = () => false, true)`;
  await t2.eval(refuse);
  await t2.eval(`(getSelection().removeAllRanges(), document.querySelector('.ordpar-settings-status').textContent = '', true)`);
  await press(p, t2, '.ordpar-settings-popup');
  await sleep(400);
  res.fallback = { settings: await t2.eval(`({ status: document.querySelector('.ordpar-settings-status').textContent,
    lineHidden: document.querySelector('.ordpar-popup-line').hidden, line: document.querySelector('.ordpar-popup-line code').textContent,
    selected: getSelection().toString() })`) };
  res.fallback.settings.shot = await shot(t2, 'settings-refused', '.ordpar-stored', '.ordpar-settings-status');
  await goto(t2, base + '/more/#popup');
  await until(t2, `document.querySelectorAll('.ordpar-code-copy').length === 2`, 8000);
  await t2.eval(refuse);
  await t2.eval(`(getSelection().removeAllRanges(), true)`);
  await press(p, t2, '.ordpar-about .ordpar-code-copy');
  await sleep(400);
  res.fallback.more = await t2.eval(`({ label: document.querySelector('.ordpar-code-copy').textContent,
    selected: getSelection().toString(), line: document.querySelector('.ordpar-code code').textContent })`);

  // ---- an article opened with `defs=en&theme=dark` beside the same without (shots)
  if (args.pair) {
    await goto(t2, base + '/bm-en/hus/');
    await until(t2, `document.querySelector('#ordpar-main .ordpar-pair')`);
    await sleep(400);
    res.pair = { without: await t2.eval(LOOK) };
    res.pair.without.shot = await shot(t2, 'article-saved');
    await goto(t2, base + '/bm-en/hus/#defs=en&theme=dark');
    await until(t2, `document.querySelector('#ordpar-main .ordpar-pair')`);
    await sleep(400);
    res.pair.with = await t2.eval(LOOK);
    res.pair.with.shot = await shot(t2, 'article-defs-en-dark');
  }
  res.final = await t2.eval(STORED);
  try { await p.raw('Target.closeTarget', { targetId }); } catch (e) { /* closed with the context */ }
  await done({ base, expect: EXPECT, css: CSS, before, ...res });
});
