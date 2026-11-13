// Decisions 147 (Robin, 2026-10-29): nested small articles — four choices, the new default `second`
// (a link in the first box opens a second box; a link inside the second box changes that box, with
// the "← word" line back), no limit; and Robin's rule: nothing done inside a box scrolls the page.
//
// For one viewport (args.w x args.h; args.mobile a phone with touch), in a fresh context, the groups
// args.groups names, with real mouse clicks (`Input.dispatchMouseEvent`) and real keys. The articles
// (args.ids): bat (båt) -> skip (skip (II)) -> two (slagskip) -> three (krigsskip) -> four (orlogsskip).
//
//   def       nothing saved (the default): the first box, a second box, two steps in the second, the
//             back line (its box, its words, the focus), Escape stepping back then closing the second,
//             then the first; a click inside the first closes the second; a click outside closes all;
//             aria-expanded at each point
//   keyboard  the default from the keyboard: Enter on a link in the first box opens the second, the
//             focus on its headword; Enter on a link in the second steps, the focus on the back line
//   stacked   `stacked`, no limit: four boxes (three after the first); Escape closes one at a time
//   rule3     for each mode in args.modes (and args.scrollSettings, e.g. miniscroll off): the page
//             padded and scrolled down first; each action — opening from the article, a link in a box,
//             the back line, Escape, a click inside the first box, a click outside — with the page's
//             scroll just before the press and after the box has settled; the reader scrolls the page
//             (and the box, where it scrolls) between actions; the box's own scroll at each step in
//             and after each step back
//   settings  the settings page's Small articles block: the four choices, their words and order, the
//             default checked, no limit field, the hint's words
//
// Result: { base, groups: { <group>: {...} } }; args.shots (a folder) also writes PNGs.
import { open, base, args, run, done, sleep } from './cdp.js';

const I = args.ids;
const HELP = `window.H = {
  vis: a => !!a && a.getClientRects().length > 0 && getComputedStyle(a).pointerEvents !== 'none',
  link(root, id) { if (!root) return null;
    return [...root.querySelectorAll(':scope > .mini .ordbok-xref > a.ordbok-xword')]
      .filter(a => (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && H.vis(a))[0] || null; },
  page(id) { return [...document.querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => !a.closest('.ordbok-xmini') && (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && H.vis(a))[0] || null; },
  minis() { return [...document.querySelectorAll('.ordbok-xmini')].filter(m => m.getClientRects().length); },
  box(n) { return H.minis()[n] || null; },
  newest() { const ms = H.minis(); return ms[ms.length - 1] || null; },
  inner(m) { return m ? m.querySelector(':scope > .mini') : null; },
  head(m) { const h = m && m.querySelector(':scope > .mini > .mini-head .mini-hw'); return h ? h.textContent.replace(/\\s+/g, ' ').trim() : null; },
  back(m) { const b = m && m.querySelector(':scope > .mini > .ordpar-mback'); return b ? { text: b.textContent, label: b.getAttribute('aria-label') } : null; },
  backs() { return H.minis().map(m => !!H.back(m)); },
  active() { const a = document.activeElement; if (!a || a === document.body) return null;
    const m = a.closest('.ordbok-xmini');
    return { tag: a.tagName.toLowerCase(), cls: a.className || '', href: a.getAttribute('href'), box: m ? H.minis().indexOf(m) : -1,
      hw: !!a.closest('.mini-hw') }; },
  boxes() { return H.minis().map(m => { const r = H.inner(m).getBoundingClientRect();
    return { nest: m.classList.contains('ordpar-mnest'), head: H.head(m), back: !!H.back(m),
      l: Math.round(r.left), r: Math.round(r.right), vis: m.style.visibility !== 'hidden',
      busy: !!m.querySelector(':scope > .mini[aria-busy=true]') }; }); },
  pos() { return { x: Math.round(scrollX * 10) / 10, y: Math.round(scrollY * 10) / 10 }; },
  scrolls(m) { const b = H.inner(m); return !!b && b.scrollHeight > b.clientHeight + 1 && getComputedStyle(b).overflowY !== 'visible'; },
};
true`;

let p;
const E = s => p.eval(s);
async function mouse(x, y) {
  await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await p.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await p.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
}
async function key(k, code, vk, shift = false) {
  const mod = shift ? 8 : 0;
  await p.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: k, code, windowsVirtualKeyCode: vk, modifiers: mod });
  if (k === 'Enter') await p.send('Input.dispatchKeyEvent', { type: 'char', key: k, code, text: '\r', windowsVirtualKeyCode: vk });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk, modifiers: mod });
}
const esc = async () => { await key('Escape', 'Escape', 27); await sleep(300); };
/** Wait until `n` boxes show and none is loading. */
async function settle(n) {
  for (let t = 0; t < 80; t++) {
    const b = await E(`H.boxes()`);
    if (b.length === n && !b.some(x => x.busy) && (n === 0 || await E(`!!H.newest() && !!H.newest().querySelector('.ordpar-mbody')`))) break;
    await sleep(100);
  }
  await sleep(300);
}
async function go(id, settings = {}) {
  await E(`localStorage.clear(); localStorage.setItem('theme', '${args.theme || 'light'}');
    ${Object.entries(settings).map(([k, v]) => `localStorage.setItem('${k}', '${v}');`).join(' ')} true`);
  await p.goto(base + '/bm-en/' + id + '/', 700);
  await E(HELP);
}
async function shot(name) {
  if (!args.shots) return;
  await sleep(300);
  const { data } = await p.send('Page.captureScreenshot', { format: 'png' });
  await Bun.write(args.shots + '/' + name + '.png', Buffer.from(data, 'base64'));
}

/** A real click on `expr` where it stands, never `scrollIntoView` (that would be a page move of the
 *  test's own): the box the element is in first scrolled so the element shows in it, then the page
 *  only where the element is outside the window — both before the press, as a reader would. Returns
 *  the page's scroll and the box's own scroll just before the press, or null. */
async function clickHere(expr, soft = false) {
  const found = await E(`(() => { const a = ${expr}; if (!a) return false;
    const b = a.closest('.mini');
    if (b && b.scrollHeight > b.clientHeight + 1) {
      const r = a.getClientRects()[0], br = b.getBoundingClientRect();
      if (r.top < br.top + 4 || r.bottom > br.bottom - 4) b.scrollTop += r.top - br.top - 40;
    }
    const r = a.getClientRects()[0];
    if (r.top < 60 || r.bottom > innerHeight - 4) window.scrollBy(0, r.top - innerHeight / 2);
    return true; })()`);
  if (!found) { if (soft) return null; throw new Error('nothing to click: ' + expr); }
  // the point read once the scroll events have run: a nested box follows its word (`placeNested`)
  await sleep(200);
  const pt = await E(`(() => { const a = ${expr}, b = a && a.closest('.mini'); if (!a) return null;
    const r = a.getClientRects()[0];
    return { x: r.left + Math.min(r.width / 2, 12), y: r.top + r.height / 2, s: b ? b.scrollTop : null }; })()`);
  if (!pt) { if (soft) return null; throw new Error('gone before the click: ' + expr); }
  const before = await E(`H.pos()`);
  await mouse(pt.x, pt.y);
  return { s: pt.s, before };
}

const GROUPS = {
  async def() {
    const g = {};
    await go(I.bat);
    g.mode = await E(`window.ordparMinis.nestMode()`);
    await clickHere(`H.page(${I.skip})`); await settle(1);
    g.first = { boxes: await E(`H.boxes()`), expanded: await E(`H.page(${I.skip}).getAttribute('aria-expanded')`) };
    await clickHere(`H.link(H.box(0), ${I.two})`); await settle(2);
    g.second = { boxes: await E(`H.boxes()`), expanded: await E(`H.link(H.box(0), ${I.two}).getAttribute('aria-expanded')`) };
    // two steps in the second box
    g.clicked3 = !!(await clickHere(`H.link(H.box(1), ${I.three})`, true)); await settle(2);
    g.step1 = { boxes: await E(`H.boxes()`), back: await E(`H.back(H.box(1))`), backs: await E(`H.backs()`),
      active: await E(`H.active()`) };
    g.clicked4 = !!(await clickHere(`H.link(H.box(1), ${I.four})`, true)); await settle(2);
    g.step2 = { boxes: await E(`H.boxes()`), back: await E(`H.back(H.box(1))`), backs: await E(`H.backs()`),
      active: await E(`H.active()`), path: await E(`location.pathname`) };
    await shot((args.shotPrefix || '') + 'default-two-steps');
    // the back line: one word back, the focus on the link stepped from
    await clickHere(`H.box(1).querySelector(':scope > .mini > .ordpar-mback')`); await sleep(350);
    g.back1 = { boxes: await E(`H.boxes()`), back: await E(`H.back(H.box(1))`), active: await E(`H.active()`),
      fourExpanded: await E(`H.link(H.box(1), ${I.four}) && H.link(H.box(1), ${I.four}).getAttribute('aria-expanded')`) };
    // Escape: one more step back, then the second box closes, then the first
    await esc();
    g.esc1 = { boxes: await E(`H.boxes()`), back: await E(`H.back(H.box(1))`), active: await E(`H.active()`) };
    await esc();
    g.esc2 = { boxes: await E(`H.boxes()`), active: await E(`H.active()`),
      twoExpanded: await E(`H.link(H.box(0), ${I.two}).getAttribute('aria-expanded')`) };
    await esc();
    g.esc3 = { boxes: await E(`H.boxes()`), active: await E(`H.active()`),
      expanded: await E(`H.page(${I.skip}).getAttribute('aria-expanded')`) };
    // a click inside the first box closes the second (and its steps)
    await clickHere(`H.page(${I.skip})`); await settle(1);
    await clickHere(`H.link(H.box(0), ${I.two})`); await settle(2);
    await clickHere(`H.link(H.box(1), ${I.three})`); await settle(2);
    await clickHere(`H.box(0).querySelector(':scope > .mini > .mini-head .mini-gloss') || H.box(0).querySelector('.ordpar-mbody .ordbok-def')`);
    await sleep(350);
    g.insideFirst = { boxes: await E(`H.boxes()`), expanded: await E(`H.link(H.box(0), ${I.two}).getAttribute('aria-expanded')`) };
    // the same word again closes its own box
    await clickHere(`H.link(H.box(0), ${I.two})`); await settle(2);
    await clickHere(`H.link(H.box(0), ${I.two})`); await sleep(350);
    g.sameAgain = { boxes: (await E(`H.boxes()`)).length };
    // a click outside every box closes all
    await clickHere(`H.link(H.box(0), ${I.two})`); await settle(2);
    await clickHere(`H.link(H.box(1), ${I.three})`); await settle(2);
    const W = await E(`document.documentElement.clientWidth`), Hh = await E(`document.documentElement.clientHeight`);
    await mouse(W - 4, Hh - 4); await sleep(350);
    g.outside = { boxes: (await E(`H.boxes()`)).length, expanded: await E(`H.page(${I.skip}).getAttribute('aria-expanded')`) };
    return g;
  },

  async keyboard() {
    const g = {};
    await go(I.bat);
    await clickHere(`H.page(${I.skip})`); await settle(1);
    await E(`H.page(${I.skip}).focus({ preventScroll: true }); true`);
    g.tabs1 = 0;
    for (let i = 0; i < 30; i++) {
      await key('Tab', 'Tab', 9); g.tabs1++;
      if (await E(`document.activeElement === H.link(H.box(0), ${I.two})`)) { g.reached1 = true; break; }
    }
    await key('Enter', 'Enter', 13); await settle(2);
    g.opened = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`) };
    g.tabs2 = 0;
    for (let i = 0; i < 30; i++) {
      await key('Tab', 'Tab', 9); g.tabs2++;
      if (await E(`document.activeElement === H.link(H.box(1), ${I.three})`)) { g.reached2 = true; break; }
    }
    await key('Enter', 'Enter', 13); await settle(2);
    g.stepped = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`), back: await E(`H.back(H.box(1))`) };
    await esc();
    g.esc1 = { boxes: (await E(`H.boxes()`)).length, onThree: await E(`document.activeElement === H.link(H.box(1), ${I.three})`) };
    await esc();
    g.esc2 = { boxes: (await E(`H.boxes()`)).length, onTwo: await E(`document.activeElement === H.link(H.box(0), ${I.two})`) };
    return g;
  },

  async stacked() {
    const g = {};
    await go(I.bat, { nestminis: 'stacked' });
    await clickHere(`H.page(${I.skip})`); await settle(1);
    await clickHere(`H.link(H.box(0), ${I.two})`); await settle(2);
    await clickHere(`H.link(H.box(1), ${I.three})`); await settle(3);
    await shot((args.shotPrefix || '') + 'stacked-three-deep');
    g.clicked4 = !!(await clickHere(`H.link(H.box(2), ${I.four})`, true)); await settle(4);
    g.four = { boxes: await E(`H.boxes()`), path: await E(`location.pathname`), win: await E(`document.documentElement.clientWidth`) };
    g.esc = [];
    for (let k = 0; k < 4; k++) { await esc(); g.esc.push((await E(`H.boxes()`)).length); }
    return g;
  },

  async rule3() {
    const out = {};
    for (const mode of args.modes) {
      const g = out[mode] = { actions: [], box: [] };
      await go(I.bat, Object.assign({}, args.scrollSettings || {}, { nestminis: mode }));
      // room above and below, so the page can be scrolled down first and further on
      await E(`document.body.style.paddingTop = '60vh'; document.body.style.paddingBottom = '150vh'; true`);
      await E(`(() => { const r = H.page(${I.skip}).getBoundingClientRect(); window.scrollBy(0, r.top - innerHeight * 0.35); return true; })()`);
      await sleep(200);
      g.start = await E(`H.pos()`);
      const nest = mode !== 'off', steps = mode === 'inplace' || mode === 'second';
      const deepest = () => mode === 'inplace' ? 0 : 1;
      /** One action: the page's scroll just before the press and once the boxes have settled. */
      const act = async (name, before, n) => {
        await settle(n);
        g.actions.push({ name, before, after: await E(`H.pos()`), boxes: (await E(`H.boxes()`)).length });
      };
      const readerScrolls = async (dy, ds) => {
        await E(`(() => { const m = H.newest(), b = H.inner(m);
          if (b && H.scrolls(m)) b.scrollTop = Math.min(${ds}, b.scrollHeight - b.clientHeight);
          window.scrollBy(0, ${dy}); return true; })()`);
        await sleep(200);
      };
      let c = await clickHere(`H.page(${I.skip})`);
      await act('open', c.before, 1);
      if (!nest) {
        await readerScrolls(19, 40);
        const b = await E(`H.pos()`); await esc(); await act('escape', b, 0);
        c = await clickHere(`H.page(${I.skip})`); await act('open again', c.before, 1);
        const W = await E(`document.documentElement.clientWidth`), Hh = await E(`document.documentElement.clientHeight`);
        const b2 = await E(`H.pos()`); await mouse(W - 4, Hh - 4); await act('click outside', b2, 0);
        continue;
      }
      await readerScrolls(23, 40);
      c = await clickHere(`H.link(H.box(0), ${I.two})`);
      await act('link in the first box', c.before, mode === 'inplace' ? 1 : 2);
      g.box.push({ at: 'in two', s: c.s });
      await readerScrolls(17, 30);
      const n2 = mode === 'stacked' ? 3 : mode === 'inplace' ? 1 : 2;
      c = await clickHere(`H.link(H.box(${deepest()}), ${I.three})`);
      await act('link in the deepest box', c.before, n2);
      const s2 = c.s;
      await readerScrolls(13, 25);
      const n3 = mode === 'stacked' ? 4 : n2;
      c = await clickHere(`H.link(H.box(${mode === 'stacked' ? 2 : deepest()}), ${I.four})`);
      await act('another link in the deepest box', c.before, n3);
      const s3 = c.s;
      if (steps) {
        // the reader moves the page and the box; the back line puts back only the box's own scroll
        await readerScrolls(11, 0);
        c = await clickHere(`H.box(${deepest()}).querySelector(':scope > .mini > .ordpar-mback')`);
        await act('back line', c.before, n3);
        g.box.push({ at: 'back 1', want: s3, got: await E(`H.inner(H.box(${deepest()})).scrollTop`), max: await E(`(b => b.scrollHeight - b.clientHeight)(H.inner(H.box(${deepest()})))`),
          scrolls: await E(`H.scrolls(H.box(${deepest()}))`) });
        await E(`H.inner(H.box(${deepest()})).scrollTop = 0; true`);
        await readerScrolls(9, 0);
        c = await clickHere(`H.box(${deepest()}).querySelector(':scope > .mini > .ordpar-mback')`);
        await act('back line again', c.before, n3);
        g.box.push({ at: 'back 2', want: s2, got: await E(`H.inner(H.box(${deepest()})).scrollTop`), max: await E(`(b => b.scrollHeight - b.clientHeight)(H.inner(H.box(${deepest()})))`),
          scrolls: await E(`H.scrolls(H.box(${deepest()}))`) });
        // Escape's step back
        c = await clickHere(`H.link(H.box(${deepest()}), ${I.three})`);
        await act('link again', c.before, n3);
        const sEsc = c.s;
        await readerScrolls(7, 0);
        let b = await E(`H.pos()`); await esc(); await act('escape (a step back)', b, n3);
        g.box.push({ at: 'escape', want: sEsc, got: await E(`H.inner(H.box(${deepest()})).scrollTop`), max: await E(`(b => b.scrollHeight - b.clientHeight)(H.inner(H.box(${deepest()})))`),
          scrolls: await E(`H.scrolls(H.box(${deepest()}))`) });
      }
      // Escape until every box is closed
      for (let k = 0, n = (await E(`H.boxes()`)).length; n > 0 && k < 6; k++) {
        await readerScrolls(5, 0);
        const b = await E(`H.pos()`); await esc();
        const left = (await E(`H.boxes()`)).length;
        g.actions.push({ name: 'escape ' + (k + 1), before: b, after: await E(`H.pos()`), boxes: left });
        n = left;
      }
      // a click inside the first box closes the nested ones
      await clickHere(`H.page(${I.skip})`); await settle(1);
      await clickHere(`H.link(H.box(0), ${I.two})`); await settle(mode === 'inplace' ? 1 : 2);
      if (mode !== 'inplace') {
        await clickHere(`H.link(H.box(1), ${I.three})`); await settle(mode === 'stacked' ? 3 : 2);
        c = await clickHere(`H.box(0).querySelector(':scope > .mini > .mini-head .mini-gloss') || H.box(0).querySelector('.ordpar-mbody .ordbok-def')`);
        await sleep(350);
        g.actions.push({ name: 'click inside the first box', before: c.before, after: await E(`H.pos()`), boxes: (await E(`H.boxes()`)).length });
        await clickHere(`H.link(H.box(0), ${I.two})`); await settle(2);
      }
      // a click outside every box closes all
      await readerScrolls(21, 0);
      const W = await E(`document.documentElement.clientWidth`), Hh = await E(`document.documentElement.clientHeight`);
      const b = await E(`H.pos()`); await mouse(W - 4, Hh - 4); await sleep(350);
      g.actions.push({ name: 'click outside', before: b, after: await E(`H.pos()`), boxes: (await E(`H.boxes()`)).length });
    }
    return out;
  },

  async settings() {
    const g = {};
    await E(`localStorage.clear(); localStorage.setItem('theme', '${args.theme || 'light'}'); true`);
    await p.goto(base + '/settings/', 900);
    await E(HELP);
    g.start = await E(`(() => {
      const f = k => document.querySelector('fieldset[data-setting="' + k + '"]');
      const order = [...document.querySelectorAll('fieldset[data-setting]')].map(x => x.getAttribute('data-setting'));
      const n = f('nestminis');
      return { order, limit: !!f('nestlimit'),
        sub: n && n.closest('.ordpar-settings-sub') ? n.closest('.ordpar-settings-sub').querySelector('h3').textContent : null,
        title: n ? n.querySelector('.ordpar-field-title').textContent : null,
        choices: n ? [...n.querySelectorAll('input[type=radio]')].map(r => [r.value, r.checked, r.labels[0].textContent]) : null }; })()`);
    // the hint, opened by a real click on its "?"
    const pt = await E(`(() => { const f = document.querySelector('fieldset[data-setting="nestminis"]');
      f.scrollIntoView({ block: 'center' }); const b = f.querySelector('legend .ordpar-hint-button');
      if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
    await shot((args.shotPrefix || '') + 'settings-choices');   // the four choices, before the hint covers them
    if (pt) { await sleep(150); await mouse(pt.x, pt.y); await sleep(250); }
    g.hint = await E(`(() => { const b = document.querySelector('fieldset[data-setting="nestminis"] .ordpar-hint-box');
      return b ? b.textContent : null; })()`);
    await shot((args.shotPrefix || '') + 'settings-block');
    return g;
  },
};

run(async () => {
  p = await open({ w: args.w || 1280, h: args.h || 900, mobile: !!args.mobile });
  await p.goto(base + '/bm-en/', 300);
  const groups = {};
  for (const name of args.groups) groups[name] = await GROUPS[name]();
  done({ base, groups });
});
