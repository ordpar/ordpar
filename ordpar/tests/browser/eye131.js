// Site-review decisions 131 (Robin, 2026-10-25): the deck's eye "as an optional setting you can
// turn on if you want (off by default)". The setting `exeye` (Off | On), under Examples.
//
// For one viewport (args.mobile: a phone, pressed by touch; else a computer, by the mouse), in a
// fresh context with the storage cleared:
//   settings  the settings page draws the setting right after Examples, Off first and checked;
//   off       no eye anywhere (article page, word page, full results, a list row's article), no
//             button by its name in the accessibility tree;
//   on        set in place, then after a reload: the eye beside the headword of the article page
//             (in its `.ordbok-head`, on the headword's line, at the right); a real <button> with
//             `aria-pressed` and its name; pressed by pointer it hides every example's English of
//             the article (each then revealed one at a time by its "Show English" cue), pressed
//             again it shows them all; Enter and Space press it from the keyboard; the tap area
//             is at least 44 x 44 px;
//   examples = no   the article opens with the English hidden and the eye pressed; a press shows
//             every example, a second hides them again;
//   whole     a word page of one article, a one-article search answered in place, every full result
//             (each its own eye, a press touching only its own article), an article opened in a
//             list row (none on the row's button);
//   mini      a mini opened in the article (hjem I on hus) has no eye, and the article's eye leaves its English;
//   colours   light and night: the outline, and the pressed fill (the accent).
// With args.shots ({dir, prefix}) it also saves pictures of the article's head, pressed and not, in
// light and night, for the review.
//
// args: { mobile, shots? }   Result: { base, cases: {...} }
import { writeFileSync } from 'node:fs';
import { open, base, args, run, done, sleep } from './cdp.js';

const NAME = "Hide the examples' English";

async function until(p, expr, ms = 15000) {
  // a word page's built rows go before the script's answer is read (site decisions 117)
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// the state of the article `sel` names (the first match): its eye and its examples (never a mini's)
const ART = (sel) => `(() => {
  const a = document.querySelector(${JSON.stringify(sel)});
  if (!a) return null;
  const vis = e => !!e && e.getClientRects().length > 0;
  const lis = [...a.querySelectorAll('.ordbok-ex-list > li')].filter(li => !li.closest('.ordbok-xmini') && li.querySelector(':scope > .ordpar-en'));
  const shownLis = lis.filter(li => vis(li));
  const head = a.querySelector(':scope > .ordbok-head');
  const w = head && head.querySelector(':scope > .ordpar-exeye');
  const b = w && w.querySelector('button');
  let eye = null;
  if (b) {
    const r = b.getBoundingClientRect(), hw = head.querySelector('.ordpar-hw, h1, h2, h3, h4');
    const hr = hw ? hw.getBoundingClientRect() : null;
    const cs = getComputedStyle(b);
    eye = { tag: b.tagName, type: b.type, pressed: b.getAttribute('aria-pressed'), label: b.getAttribute('aria-label'),
      title: b.title, visible: vis(b), first: head.firstElementChild === w, w: r.width, h: r.height,
      right: Math.round(a.getBoundingClientRect().right - r.right),
      sameLine: hr ? r.top < hr.bottom && r.bottom > hr.top : null,
      border: cs.borderTopColor, bg: cs.backgroundColor, colour: cs.color,
      accent: getComputedStyle(document.documentElement).getPropertyValue('--ordpar-accent').trim() };
  }
  return { eye, eyes: a.querySelectorAll('.ordpar-exeye').length,
    withEn: shownLis.length,
    enShown: shownLis.filter(li => vis(li.querySelector(':scope > .ordpar-en'))).length,
    cuesShown: shownLis.filter(li => vis(li.querySelector(':scope > .ordpar-excue'))).length };
})()`;

const COUNT = `({ eyes: document.querySelectorAll('.ordpar-exeye').length,
  buttons: [...document.querySelectorAll('button')].filter(b => b.getAttribute('aria-label') === ${JSON.stringify(NAME)}).length,
  cls: document.documentElement.classList.contains('ordpar-exeye-on') })`;

async function press(p, sel) {
  const c = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(sel)});
    if (!b) return null; b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!c) return false;
  await p.frames();
  const c2 = await p.eval(`(() => { const r = document.querySelector(${JSON.stringify(sel)}).getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (args.mobile) await p.tap(c2.x, c2.y); else await p.click(c2.x, c2.y);
  await sleep(200);
  return true;
}

async function key(p, k) {
  const ev = k === 'Enter' ? { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' }
    : { key: ' ', code: 'Space', windowsVirtualKeyCode: 32, text: ' ' };
  await p.send('Input.dispatchKeyEvent', { type: 'keyDown', ...ev });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: ev.key, code: ev.code, windowsVirtualKeyCode: ev.windowsVirtualKeyCode });
  await sleep(200);
}

// the tap area: points 21 px from the button's centre, each way, hit the button
const AREA = (sel) => `(() => { const b = document.querySelector(${JSON.stringify(sel)}); if (!b) return null;
  b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  return [[0, -21], [0, 21], [-21, 0], [21, 0]].map(([dx, dy]) => { const e = document.elementFromPoint(x + dx, y + dy);
    return !!e && !!e.closest && e.closest('button') === b; }); })()`;

async function shot(p, name) {
  if (!args.shots) return null;
  // no focus ring in the pictures (the keyboard's steps leave the eye focused)
  const box = await p.eval(`(() => { const a = document.querySelector('main .ordpar-article'); if (!a) return null;
    if (document.activeElement) document.activeElement.blur(); window.scrollTo(0, 0); const h = a.querySelector('.ordbok-head').getBoundingClientRect(), r = a.getBoundingClientRect();
    const ex = a.querySelector('.ordbok-ex-list'); const bottom = ex ? ex.getBoundingClientRect().bottom : h.bottom + 200;
    return { x: Math.max(0, r.left - 16), y: Math.max(0, h.top + scrollY - 16), w: Math.min(r.width + 32, innerWidth), h: Math.min(bottom - h.top + 40, 900) }; })()`);
  if (!box) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 } });
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  const ARTICLE = 24627;          // hus: four senses with examples
  await p.goto(base + '/bm-en/', 400);
  // the light theme stated (headless Edge may prefer the dark scheme, which `system` follows)
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);

  // the settings page: right after Examples, Off first and checked
  await p.goto(base + '/settings/', 400);
  await until(p, `document.querySelectorAll('fieldset[data-setting]').length > 5`);
  cases.settings = await p.eval(`(() => { const fs = [...document.querySelectorAll('fieldset[data-setting]')];
    const keys = fs.map(f => f.getAttribute('data-setting')), i = keys.indexOf('examples');
    const f = fs.find(x => x.getAttribute('data-setting') === 'exeye');
    const radios = f ? [...f.querySelectorAll('input[type=radio]')] : [];
    return { after: keys[i + 1], title: f ? f.querySelector('.ordpar-field-title').textContent : null,
      shown: !!f && f.getClientRects().length > 0, hint: !!f && !!f.querySelector('.ordpar-hint-button'),
      choices: radios.map(r => document.querySelector('label[for="' + r.id + '"]').textContent.trim()),
      checked: radios.filter(r => r.checked).map(r => r.value) }; })()`);

  // off: nothing anywhere
  await p.goto(base + '/bm-en/' + ARTICLE + '/', 600);
  cases.offArticle = await p.eval(COUNT);
  cases.offAx = (await p.axNodes()).filter(n => n.name && n.name.value === NAME).length;
  await p.goto(base + '/bm-en/vindu/', 400);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-result .ordbok-head')`);
  cases.offWord = await p.eval(COUNT);
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/fange/', 400);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok-head').length > 1`);
  cases.offFull = await p.eval(COUNT);
  await p.eval(`localStorage.removeItem('listview'); true`);

  // on, in place, then after a reload
  await p.goto(base + '/bm-en/' + ARTICLE + '/', 600);
  await p.eval(`ordparShell.setSetting('exeye', 'on'); true`);
  await p.frames();
  cases.onInPlace = await p.eval(ART('main .ordpar-article'));
  await p.reload(600);
  cases.stored = await p.eval(`localStorage.getItem('exeye')`);
  cases.on = await p.eval(ART('main .ordpar-article'));
  cases.ax = (await p.axNodes()).filter(n => n.name && n.name.value === NAME)
    .map(n => ({ role: n.role && n.role.value, pressed: (n.properties || []).filter(x => x.name === 'pressed').map(x => x.value.value)[0] }));
  cases.area = await p.eval(AREA('main .ordpar-exeye-btn'));
  cases.shotLight = await shot(p, 'light');
  await press(p, 'main .ordpar-exeye-btn');
  cases.pressed = await p.eval(ART('main .ordpar-article'));
  cases.axPressed = (await p.axNodes()).filter(n => n.name && n.name.value === NAME)
    .map(n => (n.properties || []).filter(x => x.name === 'pressed').map(x => x.value.value)[0]);
  cases.shotLightPressed = await shot(p, 'light-pressed');
  // one example revealed by its cue
  await press(p, 'main .ordpar-article .ordbok-ex-list > li > .ordpar-excue');
  cases.oneRevealed = await p.eval(ART('main .ordpar-article'));
  await press(p, 'main .ordpar-exeye-btn');
  cases.again = await p.eval(ART('main .ordpar-article'));
  // the keyboard
  await p.eval(`document.querySelector('main .ordpar-exeye-btn')?.focus(); true`);
  await key(p, 'Enter');
  cases.enter = await p.eval(ART('main .ordpar-article'));
  await key(p, 'Space');
  cases.space = await p.eval(ART('main .ordpar-article'));

  // night
  await p.eval(`ordparShell.setSetting('theme', 'dark'); true`);
  await p.frames();
  cases.night = await p.eval(ART('main .ordpar-article'));
  cases.shotNight = await shot(p, 'night');
  await press(p, 'main .ordpar-exeye-btn');
  cases.nightPressed = await p.eval(ART('main .ordpar-article'));
  cases.shotNightPressed = await shot(p, 'night-pressed');
  await p.eval(`ordparShell.setSetting('theme', 'light'); true`);
  await p.frames();
  cases.lightAfter = await p.eval(ART('main .ordpar-article'));

  // examples = no: opens hidden, the eye pressed; a press shows them all
  await p.eval(`ordparShell.setSetting('examples', 'no'); true`);
  await p.frames();
  cases.noStart = await p.eval(ART('main .ordpar-article'));
  await press(p, 'main .ordpar-exeye-btn');
  cases.noShown = await p.eval(ART('main .ordpar-article'));
  await press(p, 'main .ordpar-exeye-btn');
  cases.noHidden = await p.eval(ART('main .ordpar-article'));
  await p.eval(`ordparShell.setSetting('examples', 'both'); true`);
  await p.frames();
  cases.bothAgain = await p.eval(ART('main .ordpar-article'));

  // a word page of one article
  await p.goto(base + '/bm-en/vindu/', 400);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-result .ordbok-head .ordpar-exeye')`);
  cases.word = await p.eval(ART('[data-ordpar-results] .ordpar-result .ordpar-article'));
  await press(p, '[data-ordpar-results] .ordpar-exeye-btn');
  cases.wordPressed = await p.eval(ART('[data-ordpar-results] .ordpar-result .ordpar-article'));

  // a one-article search answered in place on the search page
  await p.goto(base + '/bm-en/', 600);
  await p.eval(`ordparShell.search('vindu'); true`);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-result .ordbok-head .ordpar-exeye')`);
  cases.search = await p.eval(ART('[data-ordpar-results] .ordpar-result .ordpar-article'));
  cases.searchPath = await p.eval('location.pathname');

  // every full result its own eye; a press touches only its own article
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/fange/', 400);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok-head').length > 1
    && !document.querySelector('.ordpar-result[aria-busy]')`);
  await sleep(300);
  cases.full = await p.eval(`[...document.querySelectorAll('[data-ordpar-results] .ordpar-result')].map(r => {
    const a = r.querySelector('.ordpar-article'); if (!a) return null;
    return { eyes: a.querySelectorAll('.ordpar-exeye').length,
      withEn: [...a.querySelectorAll('.ordbok-ex-list > li > .ordpar-en')].filter(e => !e.closest('.ordbok-xmini')).length }; })`);
  await p.eval(`document.querySelectorAll('[data-ordpar-results] .ordpar-result').forEach((r, i) => r.setAttribute('data-t131', i)); true`);
  const firstWithEye = await p.eval(`[...document.querySelectorAll('[data-ordpar-results] .ordpar-result')].findIndex(r => r.querySelector('.ordpar-exeye'))`);
  const otherWithEye = await p.eval(`[...document.querySelectorAll('[data-ordpar-results] .ordpar-result')].findIndex((r, i) => i > ${firstWithEye} && r.querySelector('.ordpar-exeye'))`);
  await press(p, `[data-t131="${firstWithEye}"] .ordpar-exeye-btn`);
  cases.fullFirst = await p.eval(ART(`[data-t131="${firstWithEye}"] .ordpar-article`));
  cases.fullOther = otherWithEye >= 0 ? await p.eval(ART(`[data-t131="${otherWithEye}"] .ordpar-article`)) : null;

  // an article opened in a list row
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  await p.goto(base + '/bm-en/fange/', 400);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 1`);
  cases.rowButtons = await p.eval(`document.querySelectorAll('.ordpar-row-button .ordpar-exeye').length`);
  await p.eval(`document.querySelector('.ordpar-row-button').click(); true`);
  await until(p, `!!document.querySelector('.ordpar-row-panel:not([hidden]) .ordbok-head .ordpar-exeye')`);
  cases.row = await p.eval(ART('.ordpar-row-panel:not([hidden]) .ordpar-article'));
  await press(p, '.ordpar-row-panel:not([hidden]) .ordpar-exeye-btn');
  cases.rowPressed = await p.eval(ART('.ordpar-row-panel:not([hidden]) .ordpar-article'));
  await p.eval(`localStorage.removeItem('listview'); true`);

  // a mini: hjem I (23742, five examples in English), opened on hus
  await p.goto(base + '/bm-en/' + ARTICLE + '/', 800);
  cases.miniOpened = await p.eval(`(async () => {
    const a = document.querySelector('main .ordpar-article a.ordbok-xword[href^="/bm-en/23742/"]'); if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 60; t++) { if (document.querySelector('.ordbok-xmini .ordbok-ex-list > li')) break;
      await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 300));
    return !!document.querySelector('.ordbok-xmini .ordbok-ex-list > li'); })()`);
  const MINI = `(() => { const m = document.querySelector('.ordbok-xmini'); if (!m) return null;
    const vis = e => !!e && e.getClientRects().length > 0;
    const en = [...m.querySelectorAll('.ordbok-ex-list > li > .ordpar-en, .mini-exen')];
    return { eyes: m.querySelectorAll('.ordpar-exeye, .ordpar-exeye-btn').length, en: en.length, enShown: en.filter(vis).length }; })()`;
  cases.mini = await p.eval(MINI);
  // the article's eye, pressed by script so the mini stays open (a click outside would close it)
  await p.eval(`document.querySelector('main .ordpar-exeye-btn')?.click(); true`);
  await sleep(200);
  cases.miniAfter = await p.eval(MINI);
  cases.miniArticle = await p.eval(ART('main .ordpar-article'));

  // off again in place: every eye goes, the article back to the Examples setting
  await p.eval(`ordparShell.setSetting('exeye', 'off'); true`);
  await p.frames();
  cases.offAgain = await p.eval(COUNT);
  cases.offAgainArticle = await p.eval(ART('main .ordpar-article'));
  await done({ base, cases });
});
