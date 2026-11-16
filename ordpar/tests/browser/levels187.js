// Site decisions 187 (2026-11-15): the CEFR level box, the style lab's "Quiet box", after the
// headword and on each embedded set phrase's line, behind the setting `levels` (Off | On).
//
// For one viewport (args.mobile: a phone, pressed by touch; else a computer), in a fresh context
// with the storage cleared, on pages rendered with the levels (the test's overlay):
//   settings  the setting right after "What the eye at the headword hides", its title, Off then On,
//             Off checked, its "?" whose box links to Help's #cefr-levels; On stores `levels`;
//   presets   For learners turns it on, Default off;
//   off       no box drawn on the article page, none in the accessibility tree;
//   on        hus (24627): the box the last thing in the h1, after the sound icon where there is one,
//             on the headword's line; its letters, tooltip and the heading's name ", level A1"
//             (the letters themselves not read); the Quiet box's computed look, light and night;
//             each set phrase's term with its own box last, after its icon, on the term's line;
//             bein, ben (5026) after the second spelling; omkjøring (42134, Norwegian only) and
//             uteområde (128786, no definition) theirs;
//   paint     the class on <html> before the first box is parsed, so nothing moves on load;
//   address   `#levels=on` shows it for the visit, nothing stored;
//   whole     a word page (vindu), each full result of fisk (list view off), an article opened in a
//             list row (none on the rows);
//   mini      a small article (hjem I on hus) carries none.
// args: { mobile, levels: {id: level}, shots? }   Result: { base, cases }
import { writeFileSync } from 'node:fs';
import { open, base, args, run, done, sleep } from './cdp.js';

const LV = args.levels || {};

async function until(p, expr, ms = 15000) {
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// the boxes of the article `sel` names: the headword's and each set phrase's
const BOXES = (sel) => `(() => {
  const a = document.querySelector(${JSON.stringify(sel)});
  if (!a) return null;
  const vis = e => !!e && e.getClientRects().length > 0;
  const one = (b, line) => {
    if (!b) return null;
    const r = b.getBoundingClientRect(), cs = getComputedStyle(b), t = b.querySelector('.ordpar-level-txt');
    const prev = b.previousElementSibling, lr = line ? line.getBoundingClientRect() : null;
    const words = line ? [...line.querySelectorAll('.ordbok-lemma')].pop() : null;
    const wr = words ? words.getBoundingClientRect() : null;
    return { level: b.getAttribute('data-level'), text: t && t.textContent, title: t && t.title,
      hidden: t && t.getAttribute('aria-hidden'), sr: (b.querySelector('.sr-only') || {}).textContent,
      shown: vis(b), last: b.parentNode.lastElementChild === b, prev: prev ? prev.className : null,
      afterPrev: prev && vis(prev) ? r.left >= prev.getBoundingClientRect().right - 0.5 : null,
      sameLine: wr ? r.top < wr.bottom && r.bottom > wr.top : null,
      fontSize: cs.fontSize, weight: cs.fontWeight, border: cs.borderTopWidth + ' ' + cs.borderTopStyle,
      borderColour: cs.borderTopColor, colour: cs.color, radius: cs.borderTopLeftRadius,
      padding: cs.paddingTop + ' ' + cs.paddingLeft, marginLeft: cs.marginLeft, select: cs.userSelect,
      w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 };
  };
  const hw = a.querySelector('.ordbok-head > .ordpar-hw');
  const head = hw ? one(hw.querySelector(':scope > .ordpar-level'), hw) : null;
  const terms = [...a.querySelectorAll('.ordbok-expr-term')].map(t => {
    const b = t.querySelector(':scope > .ordpar-level');
    const o = one(b, null);
    if (o && vis(b)) {
      // the term's words: a range over its first text node
      const n = [...t.childNodes].find(x => x.nodeType === 3 && x.data.trim());
      if (n) { const rg = document.createRange(); rg.selectNodeContents(n); const wr = rg.getBoundingClientRect(), r = b.getBoundingClientRect();
        o.sameLine = r.top < wr.bottom && r.bottom > wr.top; o.dy = Math.round(((r.top + r.bottom) - (wr.top + wr.bottom)) / 2 * 10) / 10; }
    }
    return o;
  });
  return { head, terms, boxes: a.querySelectorAll('.ordpar-level').length,
    shown: [...a.querySelectorAll('.ordpar-level')].filter(vis).length,
    muted: getComputedStyle(document.documentElement).getPropertyValue('--ordpar-muted').trim(),
    cls: document.documentElement.classList.contains('ordpar-levels-on') };
})()`;

async function headingName(p) {
  const nodes = await p.axNodes();
  const h = nodes.find(n => n.role && n.role.value === 'heading' && !n.ignored
    && (n.properties || []).some(x => x.name === 'level' && x.value.value === 1));
  return h && h.name ? h.name.value : null;
}

async function shot(p, name, sel) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const a = document.querySelector(${JSON.stringify(sel)}); if (!a) return null;
    a.scrollIntoView({ block: 'start' }); const r = a.getBoundingClientRect();
    return { x: Math.max(0, r.left - 8), y: r.top + scrollY - 8, w: Math.min(r.width + 16, innerWidth), h: Math.min(r.height + 16, 700) }; })()`);
  if (!box) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 } });
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

async function press(p, sel) {
  const c = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(sel)});
    if (!b) return null; b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!c) return false;
  if (args.mobile) await p.tap(c.x, c.y); else await p.click(c.x, c.y);
  await sleep(250);
  return true;
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  await p.goto(base + '/bm-en/', 400);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);

  // the settings page
  await p.goto(base + '/settings/', 400);
  await until(p, `document.querySelectorAll('fieldset[data-setting]').length > 5`);
  cases.settings = await p.eval(`(() => { const fs = [...document.querySelectorAll('fieldset[data-setting]')];
    const keys = fs.map(f => f.getAttribute('data-setting')), i = keys.indexOf('levels');
    const f = fs[i]; const radios = f ? [...f.querySelectorAll('input[type=radio]')] : [];
    return { before: keys[i - 1], title: f ? f.querySelector('.ordpar-field-title').textContent : null,
      sub: f ? (f.closest('.ordpar-settings-sub') || {}).querySelector('h3').textContent : null,
      shown: !!f && f.getClientRects().length > 0, hint: !!f && !!f.querySelector('.ordpar-hint-button'),
      choices: radios.map(r => document.querySelector('label[for="' + r.id + '"]').textContent.trim()),
      checked: radios.filter(r => r.checked).map(r => r.value) }; })()`);
  await press(p, 'fieldset[data-setting="levels"] .ordpar-hint-button');
  cases.hintBox = await p.eval(`(() => { const b = document.querySelector('fieldset[data-setting="levels"] .ordpar-hint-box');
    const a = b && b.querySelector('a'); return b ? { text: b.textContent, href: a && a.getAttribute('href'), link: a && a.textContent } : null; })()`);
  await p.eval(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true`);
  await sleep(150);
  await p.eval(`(() => { const r = document.querySelector('fieldset[data-setting="levels"] input[value="on"]'); r.click(); return true; })()`);
  await sleep(150);
  cases.storedOn = await p.eval(`localStorage.getItem('levels')`);
  // the presets: Default (off), then For learners (on)
  await p.eval(`document.querySelector('button[data-preset="default"]').click(); true`);
  await sleep(200);
  cases.presetDefault = await p.eval(`localStorage.getItem('levels') || 'off'`);
  await p.eval(`document.querySelector('button[data-preset="learners"]').click(); true`);
  await sleep(200);
  cases.presetLearners = await p.eval(`localStorage.getItem('levels')`);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);

  // off: nothing drawn, nothing read
  await p.goto(base + '/bm-en/24627/', 800);
  cases.off = await p.eval(BOXES('main .ordpar-article'));
  cases.offName = await headingName(p);

  // on, stored; the class before the first box (a watcher installed before the page's scripts)
  await p.eval(`localStorage.setItem('levels', 'on'); true`);
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: `(() => { window.__l187 = null;
    new MutationObserver((ms, o) => { if (document.querySelector('.ordpar-level')) {
      window.__l187 = document.documentElement.classList.contains('ordpar-levels-on'); o.disconnect(); } })
      .observe(document, { childList: true, subtree: true }); })();` });
  await p.goto(base + '/bm-en/24627/', 1200);
  await until(p, `document.querySelectorAll('.ordbok-expr-term .ordpar-play').length > 0 || true`, 3000);
  await sleep(400);
  cases.paint = await p.eval(`window.__l187`);
  cases.hus = await p.eval(BOXES('main .ordpar-article'));
  cases.husName = await headingName(p);
  cases.shotHus = await shot(p, 'hus-head-light', 'main .ordpar-article .ordbok-head');
  cases.shotExpr = await shot(p, 'hus-setphrases-light', 'main .ordpar-article .ordbok-expr');
  await p.eval(`ordparShell.setSetting('theme', 'dark'); true`);
  await p.frames();
  cases.husNight = await p.eval(BOXES('main .ordpar-article'));
  cases.shotHusNight = await shot(p, 'hus-head-night', 'main .ordpar-article .ordbok-head');
  cases.shotExprNight = await shot(p, 'hus-setphrases-night', 'main .ordpar-article .ordbok-expr');
  await p.eval(`ordparShell.setSetting('theme', 'light'); true`);
  // off again in place
  await p.eval(`ordparShell.setSetting('levels', 'off'); true`);
  await p.frames();
  cases.offInPlace = await p.eval(BOXES('main .ordpar-article'));
  await p.eval(`ordparShell.setSetting('levels', 'on'); true`);

  for (const id of [5026, 42134, 128786]) {
    await p.goto(base + '/bm-en/' + id + '/', 900);
    cases['a' + id] = await p.eval(BOXES('main .ordpar-article'));
  }
  cases.shotBein = await (async () => { await p.goto(base + '/bm-en/5026/', 900); return shot(p, 'bein-head-light', 'main .ordpar-article .ordbok-head'); })();

  // a word page of one article (vindu, 68472)
  await p.goto(base + '/bm-en/vindu/', 400);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-result .ordbok-head .ordpar-level')`);
  cases.word = await p.eval(BOXES('[data-ordpar-results] .ordpar-result .ordpar-article'));

  // each full result of fisk (list view off)
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/fisk/', 400);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok-head').length > 1
    && !document.querySelector('.ordpar-result[aria-busy]')`);
  await sleep(300);
  cases.full = await p.eval(`[...document.querySelectorAll('[data-ordpar-results] .ordpar-result')].map(r => {
    const a = r.querySelector('.ordpar-article'); if (!a) return null;
    const b = a.querySelector('.ordbok-head > .ordpar-hw > .ordpar-level');
    return { id: r.getAttribute('data-id'),
      level: b ? b.getAttribute('data-level') : null, shown: !!b && b.getClientRects().length > 0 }; })`);

  // an article opened in a list row; none on the rows
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  await p.goto(base + '/bm-en/fisk/', 400);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 1`);
  cases.rowBoxes = await p.eval(`document.querySelectorAll('.ordpar-row-button .ordpar-level').length`);
  await p.eval(`document.querySelector('.ordpar-row-button').click(); true`);
  await until(p, `!!document.querySelector('.ordpar-row-panel:not([hidden]) .ordbok-head .ordpar-level')`);
  cases.row = await p.eval(BOXES('.ordpar-row-panel:not([hidden]) .ordpar-article'));
  await p.eval(`localStorage.removeItem('listview'); true`);

  // a small article: hjem I (23742) opened on hus
  await p.goto(base + '/bm-en/24627/', 800);
  cases.miniOpened = await p.eval(`(async () => {
    const a = document.querySelector('main .ordpar-article a.ordbok-xword[href^="/bm-en/23742/"]'); if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 60; t++) { if (document.querySelector('.ordbok-xmini .ordpar-mbody')) break;
      await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 300));
    return !!document.querySelector('.ordbok-xmini .ordpar-mbody'); })()`);
  cases.miniBoxes = await p.eval(`document.querySelectorAll('.ordbok-xmini .ordpar-level').length`);

  // the address: shown for the visit, nothing stored
  await p.goto(base + '/bm-en/', 400);       // a page load, not a jump within the article's page
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); sessionStorage.clear(); true`);
  await p.goto(base + '/bm-en/24627/#levels=on', 900);
  cases.address = await p.eval(BOXES('main .ordpar-article'));
  cases.addressStored = await p.eval(`localStorage.getItem('levels')`);
  cases.addressHash = await p.eval(`location.hash`);
  await p.eval(`sessionStorage.clear(); true`);
  await done({ base, levels: LV, cases });
});
