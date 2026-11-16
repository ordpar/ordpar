// Site decisions 188 (2026-11-16): the set phrases ordered by CEFR level, the setting `phraseorder`
// (alpha | level) right below the level box's (`levels`), shown and applied only while the boxes
// are on.
//
// For one viewport (args.mobile: a phone, pressed by touch; else a computer), in a fresh context
// with the storage cleared, on pages rendered with the levels (the test's overlay). Each article
// check (`SECS`) returns, for each set-phrase section, its blocks in the page's order (term, level,
// group: the translated phrases or the untranslated ones) and the terms in the order they are drawn
// (by their place on the screen), with the section's height; the Python side works out the order
// level gives and compares.
//   settings  the setting right after "CEFR level after the headword", hidden while it is off and
//             shown once it is on, its title, choices and "?", alpha checked; level stored; Default
//             gives alpha, For learners level;
//   alpha     hus (24627) with nothing stored: drawn in the page's order;
//   boxesOff  phraseorder level stored, levels off: still the page's order;
//   on        both on: the classes on <html> before the first block is parsed (nothing moves on
//             load), hus drawn by level, the section the height it has alphabetically; set back to
//             alpha in place, then level again; a small article's blocks inside a block (stand-in
//             markup) left as they are;
//   anchor    `#x102921-def2` (på huset, B1, last alphabetically, first by level): scrolled to;
//   features  the sound icons (as many in each order), the eye's whole-article mode (186), "Show N
//             more examples" (exlimit 1, a line pressed in a block that moved), Norwegian only (152),
//             print: each by level, each the same height in both orders;
//   groups    5516 (one translated phrase, the rest untranslated): each group by level, the
//             untranslated heading and its group after the translated one; under Norwegian only too;
//   nbonly    46031, a Norwegian-only article;
//   address   `#levels=on&phraseorder=level`: by level for the visit, nothing stored;
//   whole     the word page hus (list view off), each full result of fisk (list view off), an article opened in a
//             list row.
// args: { mobile }   Result: { base, cases }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// a block's term (its first text, without the sound icon's or the level box's)
const TERM = `(x => { const t = x.querySelector('.ordbok-expr-term'); const n = t && [...t.childNodes].find(c => c.nodeType === 3 && c.data.trim());
    return n ? n.data.trim() : null; })`;
// a section's own blocks and its untranslated group's, in the page's order
const OWN = `(s => [...s.querySelectorAll(':scope > .ordbok-expr, :scope > .ordpar-untr > .ordbok-expr')])`;
// the order the page was built in, read from the article's own page as served (fetched and
// parsed, never from the page script's record): for each set-phrase section, [term, level, group]
const BUILT = `(async (a) => {
  const term = ${TERM};
  const host = a.closest('[data-id]');
  const id = host ? host.getAttribute('data-id') : document.documentElement.getAttribute('data-article-id');
  const doc = new DOMParser().parseFromString(await (await fetch('/bm-en/' + id + '/')).text(), 'text/html');
  return [...doc.querySelectorAll('.ordpar-article section.ordbok-sec')].filter(s => s.querySelector('.ordbok-expr'))
    .map(s => [...s.querySelectorAll('.ordbok-expr')].map(x => [term(x), x.getAttribute('data-level'), x.closest('.ordpar-untr') ? 'untr' : 'tr']));
})`;
// each set-phrase section of the article `a` (an element): `page` the order it was built in (above),
// `dom` the order of its blocks in the page now (what screen readers and the Tab key follow),
// `drawn` the order on the screen
const SECS_FN = `async (a) => {
  if (!a) return null;
  const term = ${TERM}, own = ${OWN}, built = await (${BUILT})(a);
  const secs = [...a.querySelectorAll('section.ordbok-sec')].filter(s => s.querySelector('.ordbok-expr'));
  return secs.map((s, i) => {
    const blocks = own(s).map(x => ({ term: term(x), level: x.getAttribute('data-level'),
      group: x.closest('.ordpar-untr') ? 'untr' : 'tr', top: x.getBoundingClientRect().top, h: x.getBoundingClientRect().height }));
    const head = s.querySelector('.ordpar-untr-head'), hv = head && head.getClientRects().length > 0;
    const drawn = blocks.filter(b => b.h > 0).slice().sort((x, y) => x.top - y.top).map(b => b.term);
    const lastTr = Math.max(-1e9, ...blocks.filter(b => b.group === 'tr' && b.h > 0).map(b => b.top));
    const firstUntr = Math.min(1e9, ...blocks.filter(b => b.group === 'untr' && b.h > 0).map(b => b.top));
    return { cls: s.className, page: built[i] || [], dom: blocks.map(b => b.term), drawn,
      height: Math.round(s.getBoundingClientRect().height * 10) / 10,
      headAfterTr: hv ? head.getBoundingClientRect().top > lastTr : null,
      headBeforeUntr: hv ? head.getBoundingClientRect().bottom <= firstUntr + 0.5 : null,
      icons: s.querySelectorAll('.ordbok-expr-term .ordpar-play').length };
  });
}`;
// the same for the article `sel` names
const SECS = (sel) => `(${SECS_FN})(document.querySelector(${JSON.stringify(sel)}))`;

const CLS = `(() => { const c = document.documentElement.classList; return { levels: c.contains('ordpar-levels-on'), order: c.contains('ordpar-phraseorder-level') }; })()`;

async function key(p, k, code, vk) {
  await p.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: k, code, windowsVirtualKeyCode: vk });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk });
}

// The Tab key through the first set-phrase section of the article `sel` names, from its heading
// (made focusable for the test) until the focus leaves the section: the section's own blocks the
// focus passed through, in turn (each once in a row), and the drawn order of the blocks
async function tabs(p, sel) {
  const ok = await p.eval(`(() => { const a = document.querySelector(${JSON.stringify(sel)});
    const s = a && [...a.querySelectorAll('section.ordbok-sec')].find(x => x.querySelector('.ordbok-expr'));
    if (!s) return false; const h = s.querySelector('h3'); h.tabIndex = -1; h.scrollIntoView({ block: 'start' });
    h.focus({ preventScroll: true }); window.__tabSec = s; return document.activeElement === h; })()`);
  if (!ok) return null;
  const seen = [];
  let n = 0;
  for (; n < 1500; n++) {
    await key(p, 'Tab', 'Tab', 9);
    const t = await p.eval(`(() => { const s = window.__tabSec, f = document.activeElement, own = ${OWN};
      if (!f || !s.contains(f)) return null; const x = own(s).find(b => b.contains(f)); return x ? (${TERM})(x) : '(outside a block)'; })()`);
    if (t === null) break;
    if (seen[seen.length - 1] !== t) seen.push(t);
  }
  const drawn = await p.eval(`(() => { const s = window.__tabSec, own = ${OWN}, term = ${TERM};
    s.querySelector('h3').removeAttribute('tabindex');
    return own(s).filter(b => b.getClientRects().length).sort((x, y) => x.getBoundingClientRect().top - y.getBoundingClientRect().top).map(term); })()`);
  return { seen, drawn, presses: n };
}

// Every block's place on the screen before and after the page script (`ordparDefs`) runs, on the
// article page with both classes on: at load (the page's blocks first put back in the order they
// were built in, as before the script), then at each change of the two classes as the shell makes
// it (`step`, `together`). Each step: the page's order before and after, and the largest shift of
// any block's top, left or height, in CSS pixels
const STILL = `(async () => {
  const a = document.querySelector('main .ordpar-article'), term = ${TERM}, own = ${OWN}, C = document.documentElement.classList;
  const s = [...a.querySelectorAll('section.ordbok-sec')].find(x => x.querySelector('.ordbok-expr'));
  const built = (await (${BUILT})(a))[0].map(b => b[0]);
  const pos = () => { const m = new Map(); own(s).forEach(x => { const r = x.getBoundingClientRect();
    m.set(x, [r.top + scrollY, r.left + scrollX, r.height]); }); return m; };
  const shift = (m1, m2) => { let d = 0; m1.forEach((v, k) => { const w = m2.get(k);
    for (let i = 0; i < 3; i++) d = Math.max(d, Math.abs(v[i] - w[i])); }); return Math.round(d * 100) / 100; };
  const dom = () => own(s).map(term);
  const putBuilt = () => { [s, s.querySelector(':scope > .ordpar-untr')].forEach(g => { if (!g) return;
    const bs = [...g.children].filter(x => x.classList.contains('ordbok-expr')); if (!bs.length) return;
    const ref = bs[bs.length - 1].nextSibling;
    bs.sort((x, y) => built.indexOf(term(x)) - built.indexOf(term(y))).forEach(x => g.insertBefore(x, ref)); }); };
  // the class added, then the script: compared with the places drawn between the two
  const step = (change) => { change(); const m1 = pos(), before = dom(); ordparDefs(); return { before, after: dom(), shift: shift(m1, pos()) }; };
  // the class taken off and the script in one go, as the shell does them (the sheet then draws the
  // page's order, so the moment between is never drawn): compared with the places the page as built
  // has with the class off, measured first
  const together = (change, ref) => { const before = dom(); change(); ordparDefs(); return { before, after: dom(), shift: shift(ref, pos()) }; };
  const L = 'ordpar-phraseorder-level', B = 'ordpar-levels-on', out = { built };
  putBuilt();                                  // the page as built, as before the script ran
  C.remove(L); const refAlpha = pos(); C.add(L);
  C.remove(B); const refOff = pos(); C.add(B);
  out.load = step(() => {});
  out.levelOff = together(() => C.remove(L), refAlpha);
  out.levelOn = step(() => C.add(L));
  out.boxesOff = together(() => C.remove(B), refOff);
  out.boxesOn = step(() => C.add(B));
  return out; })()`;

async function press(p, sel) {
  const c = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(sel)});
    if (!b) return null; b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!c) return false;
  if (args.mobile) await p.tap(c.x, c.y); else await p.click(c.x, c.y);
  await sleep(250);
  return true;
}

async function set(p, kv) {
  await p.eval(`(() => { const kv = ${JSON.stringify(kv)}; for (const k in kv) { if (kv[k] === null) localStorage.removeItem(k); else localStorage.setItem(k, kv[k]); } return true; })()`);
}

async function both(p, url, sel, extra) {
  // the same page alphabetically and by level, with the settings `extra` (both orders with the boxes on)
  await set(p, Object.assign({ levels: 'on', phraseorder: 'alpha' }, extra || {}));
  await p.goto(base + url, 900);
  await sleep(300);
  const alpha = await p.eval(SECS(sel));
  await set(p, { phraseorder: 'level' });
  await p.goto(base + url, 900);
  await sleep(300);
  const level = await p.eval(SECS(sel));
  return { alpha, level };
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  const ART = 'main .ordpar-article';
  await p.goto(base + '/bm-en/', 400);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);

  // the settings page
  await p.goto(base + '/settings/', 400);
  await until(p, `document.querySelectorAll('fieldset[data-setting]').length > 5`);
  const FIELD = `(() => { const fs = [...document.querySelectorAll('fieldset[data-setting]')];
    const keys = fs.map(f => f.getAttribute('data-setting')), i = keys.indexOf('phraseorder');
    const f = fs[i]; const radios = f ? [...f.querySelectorAll('input[type=radio]')] : [];
    return { before: keys[i - 1], after: keys[i + 1], title: f ? f.querySelector('.ordpar-field-title').textContent : null,
      sub: f ? (f.closest('.ordpar-settings-sub') || {}).querySelector('h3').textContent : null,
      shown: !!f && f.getClientRects().length > 0, hint: !!f && !!f.querySelector('.ordpar-hint-button'),
      choices: radios.map(r => document.querySelector('label[for="' + r.id + '"]').textContent.trim()),
      checked: radios.filter(r => r.checked).map(r => r.value) }; })()`;
  cases.fieldOff = await p.eval(FIELD);
  await p.eval(`document.querySelector('fieldset[data-setting="levels"] input[value="on"]').click(); true`);
  await sleep(200);
  cases.fieldOn = await p.eval(FIELD);
  await press(p, 'fieldset[data-setting="phraseorder"] .ordpar-hint-button');
  cases.hintBox = await p.eval(`(() => { const b = document.querySelector('fieldset[data-setting="phraseorder"] .ordpar-hint-box');
    return b ? b.textContent : null; })()`);
  await p.eval(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true`);
  await sleep(150);
  await p.eval(`document.querySelector('fieldset[data-setting="phraseorder"] input[value="level"]').click(); true`);
  await sleep(150);
  cases.stored = await p.eval(`localStorage.getItem('phraseorder')`);
  await p.eval(`document.querySelector('button[data-preset="default"]').click(); true`);
  await sleep(200);
  cases.presetDefault = await p.eval(`({ order: localStorage.getItem('phraseorder') || 'alpha', levels: localStorage.getItem('levels') || 'off' })`);
  cases.fieldAfterDefault = await p.eval(FIELD);
  await p.eval(`document.querySelector('button[data-preset="learners"]').click(); true`);
  await sleep(200);
  cases.presetLearners = await p.eval(`({ order: localStorage.getItem('phraseorder'), levels: localStorage.getItem('levels') })`);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);

  // alphabetical, nothing stored
  await p.goto(base + '/bm-en/24627/', 900);
  cases.alpha = await p.eval(SECS(ART));
  // the level order stored with the boxes off: not applied
  await set(p, { phraseorder: 'level' });
  await p.goto(base + '/bm-en/24627/', 900);
  cases.boxesOff = { secs: await p.eval(SECS(ART)), cls: await p.eval(CLS) };

  // both on: the classes before the first block is parsed
  await set(p, { levels: 'on', phraseorder: 'alpha' });
  await p.goto(base + '/bm-en/24627/', 900);
  cases.onAlpha = await p.eval(SECS(ART));
  await set(p, { phraseorder: 'level' });
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: `(() => { window.__p188 = null;
    new MutationObserver((ms, o) => { if (document.querySelector('.ordbok-expr')) { const c = document.documentElement.classList;
      window.__p188 = c.contains('ordpar-levels-on') && c.contains('ordpar-phraseorder-level'); o.disconnect(); } })
      .observe(document, { childList: true, subtree: true }); })();` });
  await p.goto(base + '/bm-en/24627/', 1200);
  await sleep(300);
  cases.paint = await p.eval(`window.__p188`);
  cases.on = await p.eval(SECS(ART));
  // a small article's copied blocks inside a block (as mini.js puts a senseless article's set
  // phrases into its box): stand-in markup, the order and the spacing the sheet gives them
  cases.miniInside = await p.eval(`(() => {
    const x = document.querySelector('main .ordpar-article .ordpar-exprs > .ordbok-expr'); if (!x) return null;
    const m = document.createElement('div'); m.className = 'ordpar-mbody';
    m.innerHTML = '<div class="ordbok-expr" data-level="C"><span class="ordbok-expr-term">c</span></div>'
      + '<div class="ordbok-expr" data-level="A1"><span class="ordbok-expr-term">a</span></div>';
    x.appendChild(m);
    const [c, a] = m.children, out = { cFirst: c.getBoundingClientRect().top < a.getBoundingClientRect().top,
      margin: getComputedStyle(c).marginBottom, order: getComputedStyle(a).order,
      after: getComputedStyle(c, '::after').content };
    m.remove(); return out; })()`);
  await p.eval(`ordparShell.setSetting('phraseorder', 'alpha'); true`);
  await p.frames();
  cases.inPlaceAlpha = await p.eval(SECS(ART));
  await p.eval(`ordparShell.setSetting('phraseorder', 'level'); true`);
  await p.frames();
  cases.inPlaceLevel = await p.eval(SECS(ART));
  await p.eval(`ordparShell.setSetting('levels', 'off'); true`);
  await p.frames();
  cases.inPlaceBoxesOff = await p.eval(SECS(ART));
  await p.eval(`ordparShell.setSetting('levels', 'on'); true`);

  // the page script moves nothing on the screen: at load and at each change of the two classes
  await set(p, { levels: 'on', phraseorder: 'level' });
  await p.goto(base + '/bm-en/24627/', 900);
  cases.still = await p.eval(STILL);
  // the Tab key through hus's set phrases: by level with both on; alphabetical with the order
  // alpha, and with the boxes off
  await p.goto(base + '/bm-en/24627/', 900);
  cases.tabLevel = await tabs(p, ART);
  await set(p, { phraseorder: 'alpha' });
  await p.goto(base + '/bm-en/24627/', 900);
  cases.tabAlpha = await tabs(p, ART);
  await set(p, { levels: 'off', phraseorder: 'level' });
  await p.goto(base + '/bm-en/24627/', 900);
  cases.tabBoxesOff = await tabs(p, ART);
  // the focus on a link in a block that moves (46031, presens partisipp: B2, the fourth as built and
  // the third by level), kept through a change of the order in place both ways
  await set(p, { levels: 'on', phraseorder: 'level' });
  await p.goto(base + '/bm-en/46031/', 900);
  cases.focusKept = await p.eval(`(async () => {
    const a = document.querySelector('main .ordpar-article'), s = a.querySelector('.ordpar-exprs'), own = ${OWN}, term = ${TERM};
    const built = (await (${BUILT})(a))[0].map(b => b[0]), bs = own(s);
    // a block whose place in the page differs by level and as built
    const x = bs.find((b, i) => built.indexOf(term(b)) !== i && b.querySelector('a[href]'));
    if (!x) return null;
    const l = x.querySelector('a[href]'); l.focus({ preventScroll: true });
    const at0 = own(s).indexOf(x), y0 = scrollY;
    ordparShell.setSetting('phraseorder', 'alpha');
    const k1 = document.activeElement === l, at1 = own(s).indexOf(x);
    ordparShell.setSetting('phraseorder', 'level');
    return { kept: [k1, document.activeElement === l], moved: at1 !== at0, back: own(s).indexOf(x) === at0,
      scrolled: scrollY !== y0 }; })()`);
  // a small article open inside a block that moves (46031 again): still open, and in place against
  // its link, through a change of the order in place both ways
  await p.goto(base + '/bm-en/46031/', 900);
  cases.mini = await (async () => {
    const found = await p.eval(`(async () => {
      const a = document.querySelector('main .ordpar-article'), s = a.querySelector('.ordpar-exprs'), own = ${OWN}, term = ${TERM};
      const built = (await (${BUILT})(a))[0].map(b => b[0]), bs = own(s), drawn = bs.slice().sort((x, y) => x.getBoundingClientRect().top - y.getBoundingClientRect().top);
      // a block drawn in another place by level than as built
      const x = drawn.find((b, i) => built.indexOf(term(b)) !== i && b.querySelector('.ordbok-xref > a[href]'));
      if (!x) return false;
      x.querySelector('.ordbok-xref > a[href]').setAttribute('data-p188mini', ''); return true; })()`);
    if (!found) return null;
    await press(p, 'a[data-p188mini]');
    await until(p, `!!document.querySelector('.ordbok-xmini .mini:not([aria-busy])')`);
    await sleep(300);
    const PLACE = `(() => { const l = document.querySelector('a[data-p188mini]'), m = document.querySelector('.ordbok-xmini');
      if (!l || !m) return null; const own = ${OWN}, s = l.closest('.ordpar-exprs'), x = own(s).find(b => b.contains(l));
      const bl = l.getBoundingClientRect(), bm = m.querySelector('.mini').getBoundingClientRect();
      return { open: m.isConnected && !!l.closest('.ordpar-mopen') && x.contains(m), at: own(s).indexOf(x),
        dx: Math.round((bm.left - bl.left) * 10) / 10, dy: Math.round((bm.top - bl.top) * 10) / 10,
        top: Math.round((bm.top + scrollY) * 10) / 10, w: Math.round(bm.width * 10) / 10 }; })()`;
    const first = await p.eval(PLACE);
    await p.eval(`ordparShell.setSetting('phraseorder', 'alpha'); true`);
    await p.frames();
    const alpha = await p.eval(PLACE);
    await p.eval(`ordparShell.setSetting('phraseorder', 'level'); true`);
    await p.frames();
    const level = await p.eval(PLACE);
    return { first, alpha, level };
  })();

  // a link to a set phrase that moves
  await p.goto(base + '/bm-en/', 400);
  await p.goto(base + '/bm-en/24627/#x102921-def2', 1200);
  await sleep(500);
  cases.anchor = await p.eval(`(() => { const e = document.getElementById('x102921-def2'); if (!e) return null;
    const r = e.getBoundingClientRect(); const x = e.closest('.ordbok-expr');
    const all = [...x.parentNode.querySelectorAll(':scope > .ordbok-expr')].sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    return { top: Math.round(r.top), inView: r.top >= -2 && r.top < innerHeight, first: all[0] === x }; })()`);

  // the features that touch the blocks
  cases.icons = await both(p, '/bm-en/24627/', ART);
  cases.eyeAll = await both(p, '/bm-en/24627/', ART, { exeye: 'on', exeyewhat: 'all' });
  cases.eyeAllPressed = await (async () => {
    // the eye pressed: every English line hidden, the order kept
    const ok = await press(p, `${ART} .ordpar-exeye-btn`);
    await sleep(300);
    return { pressed: ok, secs: await p.eval(SECS(ART)) };
  })();
  await set(p, { exeye: null, exeyewhat: null });
  cases.exlimit = await both(p, '/bm-en/24627/', ART, { exlimit: '1' });
  cases.exmore = await p.eval(`(async () => {
    // a "Show N more examples" line (decisions 112) in the first block drawn that has one
    const blocks = [...document.querySelectorAll('main .ordpar-article .ordbok-expr')];
    const drawn = () => blocks.slice().sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    const vis = e => !!e && e.getClientRects().length > 0;
    const order = drawn();
    const x = order.find(b => vis(b.querySelector('li.ordpar-exmore button')));
    if (!x) return { found: false };
    const h = x.getBoundingClientRect().height;
    x.querySelector('li.ordpar-exmore button').click();
    await new Promise(r => setTimeout(r, 300));
    return { found: true, pageIndex: blocks.indexOf(x), drawnIndex: order.indexOf(x),
      grew: x.getBoundingClientRect().height > h, sameOrder: drawn().every((b, i) => b === order[i]) }; })()`);
  await set(p, { exlimit: null });
  cases.nbo = await both(p, '/bm-en/24627/', ART, { nbonly: 'on' });
  cases.nboGroups = await both(p, '/bm-en/5516/', ART, { nbonly: 'on' });
  await set(p, { nbonly: null });
  cases.print = await (async () => {
    await set(p, { levels: 'on', phraseorder: 'level' });
    await p.goto(base + '/bm-en/24627/', 900);
    await p.send('Emulation.setEmulatedMedia', { media: 'print' });
    await sleep(200);
    const level = await p.eval(SECS(ART));
    await p.send('Emulation.setEmulatedMedia', { media: '' });
    return { level };
  })();

  // the two groups, and a Norwegian-only article
  cases.groups = await both(p, '/bm-en/5516/', ART);
  cases.nbArticle = await both(p, '/bm-en/46031/', ART);

  // the address: by level for the visit, nothing stored
  await p.goto(base + '/bm-en/', 400);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); sessionStorage.clear(); true`);
  await p.goto(base + '/bm-en/24627/#levels=on&phraseorder=level', 900);
  cases.address = { secs: await p.eval(SECS(ART)), stored: await p.eval(`localStorage.getItem('phraseorder')`),
    hash: await p.eval(`location.hash`) };
  await p.eval(`sessionStorage.clear(); true`);

  // every article shown whole: the word page hus, the full results of fisk, a list row's article
  // (list view off: with it on, the word page hus lists hus beside the inflected forms it finds)
  await set(p, { levels: 'on', phraseorder: 'level', listview: 'off' });
  await p.goto(base + '/bm-en/hus/', 400);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-result .ordbok-expr')`);
  await sleep(300);
  cases.word = await p.eval(SECS('[data-ordpar-results] .ordpar-result .ordpar-article'));
  await p.goto(base + '/bm-en/fisk/', 400);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok-head').length > 1
    && !document.querySelector('.ordpar-result[aria-busy]')`);
  await sleep(300);
  cases.full = await p.eval(`Promise.all([...document.querySelectorAll('[data-ordpar-results] .ordpar-result')].map(async r => ({
    id: r.getAttribute('data-id'), secs: await (${SECS_FN})(r.querySelector('.ordpar-article')) })))`);
  await set(p, { listview: 'on' });
  await p.goto(base + '/bm-en/fisk/', 400);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 1`);
  await p.eval(`document.querySelector('.ordpar-row-button').click(); true`);
  await until(p, `!!document.querySelector('.ordpar-row-panel:not([hidden]) .ordbok-expr')`);
  await sleep(300);
  cases.row = await p.eval(SECS('.ordpar-row-panel:not([hidden]) .ordpar-article'));
  await done({ base, cases });
});
