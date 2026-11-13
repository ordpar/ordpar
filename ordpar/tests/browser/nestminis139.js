// Decisions 139 (Robin, 2026-10-26): a small article inside a small article, as a setting —
// `nestminis` inplace (the box swaps to the new word, "← word" steps back, no limit) | stacked (a
// second box below its word) | off (depth one). Since decisions 147 (2026-10-29) the default is
// `second` (`nestminis147.js`), so the in-place groups name `inplace`; stacked has no limit (the
// setting `nestlimit` went); and nothing in a box scrolls the page.
//
// For one viewport (args.w x args.h; args.mobile a phone with touch), in a fresh context, the
// groups args.groups names, with real mouse clicks (`Input.dispatchMouseEvent`, so the sheet's
// pointer-events count) and real keys. The articles (args.ids): bat (båt) -> skip (skip (II)) ->
// two (slagskip) -> three (krigsskip) -> four (orlogsskip), all translated; lang -> sid -> fotsid,
// the last Norwegian-only.
//
//   inplace   open, two steps, the back line (its words, its name, the focus), back by the line
//             (the first word's scroll position kept), Escape steps back then closes, the focus
//             and aria-expanded at each point
//   stacked1  a second box; a click inside the first closes only it; the same word again closes
//             it; Escape closes it and the focus is back on its word; a link in the second box
//             opens a third (147: no limit); a click outside every box closes all
//   stacked2  three boxes, then a fourth (147: no limit); Escape one at a time
//   off       a link in a box opens its page (today's depth one)
//   nbonly    a Norwegian-only target nested, in place and stacked
//   keyboard  Tab reaches a link in a box, Enter opens it; the focus moves into the new box
//   search    the search page's lifted article, a word page's, an opened list-view row, under the
//             default (147: `second`): a second box, then a step in it
//   scroll    in place, back (the line, twice; Escape) puts the box's own scroll back as it was at
//             each step in, and leaves the page where it is (147: Robin's rule, nothing in a box
//             scrolls the page; args.scrollSettings: e.g. miniscroll off)
//   settings  the settings page's Small articles block: the field, its choices (147: four), no
//             limit field whichever is chosen
//
// Result: { base, groups: { <group>: {...} } }; args.shots (a folder) also writes PNGs.
import { open, base, args, run, done, sleep } from './cdp.js';

const I = args.ids;
const HELP = `window.H = {
  vis: a => !!a && a.getClientRects().length > 0 && getComputedStyle(a).pointerEvents !== 'none',
  link(root, id) { if (!root) return null;
    return [...root.querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && H.vis(a))[0] || null; },
  page(id) { return [...document.querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => !a.closest('.ordbok-xmini') && (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && H.vis(a))[0] || null; },
  minis() { return [...document.querySelectorAll('.ordbok-xmini')].filter(m => m.getClientRects().length); },
  box(n) { return H.minis()[n] || null; },
  newest() { const ms = H.minis(); return ms[ms.length - 1] || null; },
  head(m) { const h = m && m.querySelector(':scope > .mini > .mini-head .mini-hw'); return h ? h.textContent.replace(/\\s+/g, ' ').trim() : null; },
  back() { const b = document.querySelector('.ordpar-mback'); return b ? { text: b.textContent, label: b.getAttribute('aria-label') } : null; },
  active() { const a = document.activeElement; if (!a || a === document.body) return null;
    return { tag: a.tagName.toLowerCase(), cls: a.className || '', href: a.getAttribute('href'), inBox: !!a.closest('.ordbok-xmini'),
      inNest: !!a.closest('.ordpar-mnest'), hw: !!a.closest('.mini-hw') }; },
  boxes() { return H.minis().map(m => { const r = m.querySelector(':scope > .mini').getBoundingClientRect();
    return { nest: m.classList.contains('ordpar-mnest'), head: H.head(m), lang: m.getAttribute('lang'),
      l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), w: Math.round(r.width), vis: m.style.visibility !== 'hidden',
      busy: !!m.querySelector(':scope > .mini[aria-busy=true]') }; }); },
  point(a) { a.scrollIntoView({ block: 'center' }); const r = a.getClientRects()[0]; return { x: r.left + Math.min(r.width / 2, 12), y: r.top + r.height / 2 }; },
};
true`;

let p;
const E = s => p.eval(s);
async function mouse(x, y) {
  await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await p.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await p.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
}
/** A real click on the element `expr` names (scrolled into view first); false if there is none. */
async function click(expr) {
  const pt = await E(`(() => { const a = ${expr}; return a ? H.point(a) : null; })()`);
  if (!pt) return false;
  await sleep(120); await mouse(pt.x, pt.y);
  return true;
}
async function key(k, code, vk, shift = false) {
  const mod = shift ? 8 : 0;
  await p.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: k, code, windowsVirtualKeyCode: vk, modifiers: mod });
  if (k === 'Enter') await p.send('Input.dispatchKeyEvent', { type: 'char', key: k, code, text: '\r', windowsVirtualKeyCode: vk });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk, modifiers: mod });
}
const esc = async () => { await key('Escape', 'Escape', 27); await sleep(250); };
/** Wait until `n` boxes show and none is loading. */
async function settle(n) {
  for (let t = 0; t < 80; t++) {
    const b = await E(`H.boxes()`);
    if (b.length === n && !b.some(x => x.busy) && (await E(`!!H.newest() && !!H.newest().querySelector('.ordpar-mbody')`))) break;
    await sleep(100);
  }
  await sleep(250);
}
async function go(id, settings = {}) {
  await E(`localStorage.clear(); localStorage.setItem('theme', '${args.theme || 'light'}');
    ${Object.entries(settings).map(([k, v]) => `localStorage.setItem('${k}', '${v}');`).join(' ')} true`);
  await p.goto(base + '/bm-en/' + id + '/', 700);
  await E(HELP);
}
const here = () => E(`location.pathname`);
const alive = () => E(`typeof window.H !== 'undefined'`);
async function shot(name) {
  if (!args.shots) return;
  await sleep(300);
  const { data } = await p.send('Page.captureScreenshot', { format: 'png' });
  await Bun.write(args.shots + '/' + name + '.png', Buffer.from(data, 'base64'));
}

/** A real click on `expr` where it stands: no scrollIntoView (that would move the scroll positions
 *  the scroll group measures) — the box first scrolled so the element is in it, then the page only
 *  where the element is outside the window. Returns the positions just before the press. */
async function clickHere(expr, boxN = 0) {
  const pt = await E(`(() => { const a = ${expr}; if (!a) return null;
    const m = H.box(${boxN}), b = m && m.querySelector(':scope > .mini');
    if (b && b.contains(a) && b.scrollHeight > b.clientHeight + 1) {
      const r = a.getClientRects()[0], br = b.getBoundingClientRect();
      if (r.top < br.top + 4 || r.bottom > br.bottom - 4) b.scrollTop += r.top - br.top - 40;
    }
    let r = a.getClientRects()[0];
    if (r.top < 4 || r.bottom > innerHeight - 4) { window.scrollBy(0, r.top - innerHeight / 2); r = a.getClientRects()[0]; }
    return { x: r.left + Math.min(r.width / 2, 12), y: r.top + r.height / 2,
      s: b ? b.scrollTop : null, y0: window.scrollY }; })()`);
  if (!pt) return null;
  await sleep(120); await mouse(pt.x, pt.y);
  return { s: pt.s, y: pt.y0 };
}
const POS = `(() => { const b = H.box(0) && H.box(0).querySelector(':scope > .mini');
  return { s: b ? b.scrollTop : null, y: window.scrollY, head: H.head(H.box(0)), back: H.back(),
    scrolls: !!b && b.scrollHeight > b.clientHeight + 1, overflow: b ? getComputedStyle(b).overflowY : null }; })()`;
/** Leave the positions somewhere else on purpose: the box at its top (where the back line is) and
 *  the page moved so the back line sits near the window's top. */
const ELSEWHERE = `(() => { const b = H.box(0).querySelector(':scope > .mini'); b.scrollTop = 0;
  const l = document.querySelector('.ordpar-mback'); if (l) window.scrollBy(0, l.getBoundingClientRect().top - 12); return true; })()`;

const GROUPS = {
  // Robin, 2026-10-27 (to the build): in place, back returns the reader to exactly where they had
  // scrolled — the box's own scroll where it scrolls inside, the page's where it does not; each
  // level its own; by the back line and by Escape alike
  async scroll() {
    const g = {};
    await go(I.bat, Object.assign({ nestminis: 'inplace' }, args.scrollSettings || {}));
    await E(`document.body.style.paddingBottom = '150vh'; true`);     // room for the page to scroll
    await click(`H.page(${I.skip})`); await settle(1);
    // the first box scrolled down a little where it scrolls, the page down a little where it does not
    await E(`(() => { const b = H.box(0).querySelector(':scope > .mini');
      if (b.scrollHeight > b.clientHeight + 1) b.scrollTop = Math.min(60, b.scrollHeight - b.clientHeight); else window.scrollBy(0, 37);
      return true; })()`);
    g.first = await E(POS);
    g.in1 = await clickHere(`H.link(H.box(0), ${I.two})`); await settle(1);
    g.at1 = await E(POS);
    await E(`(() => { const b = H.box(0).querySelector(':scope > .mini');
      if (b.scrollHeight > b.clientHeight + 1) b.scrollTop = Math.min(30, b.scrollHeight - b.clientHeight); else window.scrollBy(0, 23);
      return true; })()`);
    g.in2 = await clickHere(`H.link(H.box(0), ${I.three})`); await settle(1);
    g.at2 = await E(POS);
    await E(ELSEWHERE);
    g.moved1 = await clickHere(`document.querySelector('.ordpar-mback')`); await sleep(350);
    g.back1 = await E(POS);
    await E(ELSEWHERE);
    g.moved2 = await clickHere(`document.querySelector('.ordpar-mback')`); await sleep(350);
    g.back2 = await E(POS);
    // Escape's step back
    g.in3 = await clickHere(`H.link(H.box(0), ${I.two})`); await settle(1);
    await E(ELSEWHERE);
    g.moved3 = await E(POS);
    await esc(); await sleep(150);
    g.esc = await E(POS);
    return g;
  },

  async inplace() {
    const g = {};
    await go(I.bat, { nestminis: 'inplace' });
    await click(`H.page(${I.skip})`); await settle(1);
    g.open = { boxes: await E(`H.boxes()`), expanded: await E(`H.page(${I.skip}).getAttribute('aria-expanded')`) };
    const head0 = g.open.boxes[0] && g.open.boxes[0].head;
    // the first word scrolled a little inside its box, where it scrolls
    g.scroll0 = await E(`(() => { const b = H.box(0).querySelector('.ordpar-fmini'); b.scrollTop = 24; return b.scrollTop; })()`);
    g.in1 = await clickHere(`H.link(H.box(0), ${I.two})`); g.clicked1 = !!g.in1; await settle(1);
    g.step1 = { boxes: await E(`H.boxes()`), back: await E(`H.back()`), active: await E(`H.active()`),
      scrollTop: await E(`H.box(0).querySelector('.ordpar-fmini').scrollTop`) };
    const head1 = g.step1.boxes[0] && g.step1.boxes[0].head;
    g.clicked2 = await click(`H.link(H.box(0), ${I.three})`); await settle(1);
    g.step2 = { boxes: await E(`H.boxes()`), back: await E(`H.back()`), active: await E(`H.active()`), path: await here() };
    await shot((args.shotPrefix || '') + 'inplace-two-steps');
    await click(`document.querySelector('.ordpar-mback')`); await sleep(300);
    g.backByLine = { boxes: await E(`H.boxes()`), back: await E(`H.back()`), active: await E(`H.active()`) };
    await click(`document.querySelector('.ordpar-mback')`); await sleep(300);
    g.backToFirst = { boxes: await E(`H.boxes()`), back: await E(`H.back()`),
      scrollTop: await E(`H.box(0) && H.box(0).querySelector('.ordpar-fmini').scrollTop`),
      twoExpanded: await E(`H.link(H.box(0), ${I.two}) && H.link(H.box(0), ${I.two}).getAttribute('aria-expanded')`) };
    // Escape: one step back, then the box closes
    await click(`H.link(H.box(0), ${I.two})`); await settle(1);
    await esc();
    g.esc1 = { boxes: await E(`H.boxes()`), back: await E(`H.back()`), active: await E(`H.active()`) };
    await esc();
    g.esc2 = { boxes: await E(`H.boxes()`), active: await E(`H.active()`),
      expanded: await E(`H.page(${I.skip}).getAttribute('aria-expanded')`) };
    g.heads = [head0, head1];
    return g;
  },

  async stacked1() {
    const g = {};
    await go(I.bat, { nestminis: 'stacked' });
    await click(`H.page(${I.skip})`); await settle(1);
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    g.two = { boxes: await E(`H.boxes()`), expanded: await E(`H.link(H.box(0), ${I.two}).getAttribute('aria-expanded')`),
      win: await E(`document.documentElement.clientWidth`) };
    await shot((args.shotPrefix || '') + 'stacked-limit1');
    // a click inside the first box (its header's gloss, not a link) closes only the second
    await click(`H.box(0).querySelector(':scope > .mini > .mini-head .mini-gloss') || H.box(0).querySelector('.ordpar-mbody .ordbok-def')`);
    await sleep(300);
    g.insideFirst = { boxes: await E(`H.boxes()`), expanded: await E(`H.link(H.box(0), ${I.two}).getAttribute('aria-expanded')`) };
    // the same word again closes its own box
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    await click(`H.link(H.box(0), ${I.two})`); await sleep(300);
    g.sameAgain = { boxes: await E(`H.boxes()`) };
    // Escape closes the second, the focus back on its word
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    await esc();
    g.esc = { boxes: await E(`H.boxes()`), active: await E(`H.active()`) };
    // a click outside every box closes all
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    const W = await E(`document.documentElement.clientWidth`), Hh = await E(`document.documentElement.clientHeight`);
    await mouse(W - 4, Hh - 4); await sleep(300);
    g.outside = { boxes: await E(`H.boxes()`), expanded: await E(`H.page(${I.skip}).getAttribute('aria-expanded')`) };
    // no limit (147): a link inside the second box opens a third
    await click(`H.page(${I.skip})`); await settle(1);
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    g.limitClicked = await click(`H.link(H.box(1), ${I.three})`); await settle(3);
    g.limit = { path: await here(), left: !(await alive()), boxes: (await E(`H.boxes()`)).length };
    return g;
  },

  async stacked2() {
    const g = {};
    await go(I.bat, { nestminis: 'stacked' });
    await click(`H.page(${I.skip})`); await settle(1);
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    await click(`H.link(H.box(1), ${I.three})`); await settle(3);
    g.three = { boxes: await E(`H.boxes()`) };
    await shot((args.shotPrefix || '') + 'stacked-limit2');
    await esc(); g.esc1 = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`) };
    await esc(); g.esc2 = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`) };
    await esc(); g.esc3 = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`) };
    // a click inside the first box closes the second and the third
    await click(`H.page(${I.skip})`); await settle(1);
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    await click(`H.link(H.box(1), ${I.three})`); await settle(3);
    await click(`H.box(0).querySelector(':scope > .mini > .mini-head .mini-gloss')`); await sleep(300);
    g.insideFirst = { boxes: (await E(`H.boxes()`)).length };
    // a click inside the second closes only the third
    await click(`H.link(H.box(0), ${I.two})`); await settle(2);
    await click(`H.link(H.box(1), ${I.three})`); await settle(3);
    await click(`H.box(1).querySelector(':scope > .mini > .mini-head .mini-gloss')`); await sleep(300);
    g.insideSecond = { boxes: (await E(`H.boxes()`)).length };
    // no limit (147): a link in the third box opens a fourth
    await click(`H.link(H.box(1), ${I.three})`); await settle(3);
    g.limitClicked = await click(`H.link(H.box(2), ${I.four})`); await settle(4);
    g.limit = { path: await here(), left: !(await alive()), boxes: (await E(`H.boxes()`)).length };
    return g;
  },

  async off() {
    const g = {};
    await go(I.bat, { nestminis: 'off' });
    await click(`H.page(${I.skip})`); await settle(1);
    g.boxes = (await E(`H.boxes()`)).length;
    g.clicked = await click(`H.link(H.box(0), ${I.two})`); await sleep(1500);
    g.path = await here(); g.left = !(await alive());
    return g;
  },

  async nbonly() {
    const g = {};
    await go(I.lang, { nestminis: 'inplace' });
    await click(`H.page(${I.sid})`); await settle(1);
    g.clicked = await click(`H.link(H.box(0), ${I.fotsid})`); await settle(1);
    g.inplace = { boxes: await E(`H.boxes()`), back: await E(`H.back()`) };
    await go(I.lang, { nestminis: 'stacked' });
    await click(`H.page(${I.sid})`); await settle(1);
    await click(`H.link(H.box(0), ${I.fotsid})`); await settle(2);
    g.stacked = { boxes: await E(`H.boxes()`) };
    return g;
  },

  async keyboard() {
    const g = {};
    for (const mode of ['stacked', 'inplace']) {
      const r = g[mode] = {};
      await go(I.bat, { nestminis: mode });
      await click(`H.page(${I.skip})`); await settle(1);
      // Tab from the opening word into the box, until its link to `two` has the focus
      await E(`H.page(${I.skip}).focus(); true`);
      r.tabs = 0;
      for (let i = 0; i < 25; i++) {
        await key('Tab', 'Tab', 9); r.tabs++;
        if (await E(`document.activeElement === H.link(H.box(0), ${I.two})`)) { r.reached = true; break; }
      }
      await key('Enter', 'Enter', 13); await settle(mode === 'stacked' ? 2 : 1);
      r.opened = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`), back: await E(`H.back()`) };
      await esc();
      r.esc = { boxes: (await E(`H.boxes()`)).length, active: await E(`H.active()`),
        onTwo: await E(`document.activeElement === H.link(H.box(0), ${I.two})`) };
    }
    return g;
  },

  async search() {
    // the search page proper (args.searchUrl: an inflected form, answered on /bm-en/ itself), a
    // word page (117, args.wordUrl), each with båt lifted whole; and an opened list-view row
    // (args.rowsUrl: skip's two homographs), with skip (II)'s article in its panel
    const g = {};
    for (const [name, url] of [['search', args.searchUrl], ['word', args.wordUrl]]) {
      const r = g[name] = {};
      await E(`localStorage.clear(); localStorage.setItem('theme', '${args.theme || 'light'}'); true`);
      if (name === 'search') {
        // the search page itself, then the search in its address: answered in place there (a page
        // loaded at `/bm-en/#q=<word>` goes on to the word's own page, 117)
        await p.goto(base + '/bm-en/', 900);
        await E(`location.hash = ${JSON.stringify(url.slice(url.indexOf('#')))}; true`);
        await sleep(1500);
      } else {
        await p.goto(base + url, 1500);
      }
      await E(HELP);
      for (let t = 0; t < 60 && !(await E(`!!H.page(${I.skip})`)); t++) await sleep(100);
      r.path = await here();
      r.found = await E(`!!H.page(${I.skip})`);
      r.rendered = await E(`!!(H.page(${I.skip}) && H.page(${I.skip}).closest('[data-ordpar-results], .ordpar-results, main'))`);
      // the default (147): a second box, then a step inside it
      await click(`H.page(${I.skip})`); await settle(1);
      await click(`H.link(H.box(0), ${I.two})`); await settle(2);
      r.second = { boxes: await E(`H.boxes()`) };
      await click(`H.link(H.box(1), ${I.three})`); await settle(2);
      r.step = { boxes: await E(`H.boxes()`), back: await E(`H.back()`), inSecond: await E(`!!H.box(1) && !!H.box(1).querySelector('.ordpar-mback')`),
        path: await here() };
    }
    const r = g.row = {};
    await E(`localStorage.clear(); localStorage.setItem('theme', '${args.theme || 'light'}'); true`);
    await p.goto(base + args.rowsUrl, 1500);
    await E(HELP);
    r.rows = await E(`document.querySelectorAll('.ordpar-row-button').length`);
    for (let k = 0; k < r.rows && !(await E(`!!H.page(${I.two})`)); k++) {
      await click(`document.querySelectorAll('.ordpar-row-button')[${k}]`); await sleep(800);
    }
    r.found = await E(`!!(H.page(${I.two}) && H.page(${I.two}).closest('.ordpar-row-panel'))`);
    await click(`H.page(${I.two})`); await settle(1);
    await click(`H.link(H.box(0), ${I.three})`); await settle(2);
    r.second = { boxes: await E(`H.boxes()`) };
    await click(`H.link(H.box(1), ${I.four})`); await settle(2);
    r.step = { boxes: await E(`H.boxes()`), back: await E(`H.back()`), inSecond: await E(`!!H.box(1) && !!H.box(1).querySelector('.ordpar-mback')`),
      path: await here() };
    return g;
  },

  async settings() {
    const g = {};
    await E(`localStorage.clear(); localStorage.setItem('theme', '${args.theme || 'light'}'); true`);
    await p.goto(base + '/settings/', 900);
    await E(HELP);
    const read = () => E(`(() => {
      const f = k => document.querySelector('fieldset[data-setting="' + k + '"]');
      const order = [...document.querySelectorAll('fieldset[data-setting]')].map(x => x.getAttribute('data-setting'));
      const n = f('nestminis'), l = f('nestlimit');
      return { order, sub: n && n.closest('.ordpar-settings-sub') ? n.closest('.ordpar-settings-sub').querySelector('h3').textContent : null,
        title: n ? n.querySelector('.ordpar-field-title').textContent : null,
        choices: n ? [...n.querySelectorAll('input[type=radio]')].map(r => [r.value, r.checked, r.labels[0].textContent]) : null,
        hint: !!(n && n.querySelector('.ordpar-hint-button')),
        limitTitle: l ? l.querySelector('.ordpar-field-title').textContent : null,
        limitHidden: l ? l.hidden : null, limitShown: l ? l.getClientRects().length > 0 : null,
        limitOptions: l ? [...l.querySelectorAll('option')].map(o => [o.value, o.selected]) : null,
        limitHint: !!(l && l.querySelector('.ordpar-hint-button')) }; })()`);
    const shotBlock = async name => {
      if (!args.shots) return;
      await E(`document.querySelector('fieldset[data-setting="nestminis"]').scrollIntoView({ block: 'center' }); true`);
      await shot(name);
    };
    g.start = await read();
    await shotBlock((args.shotPrefix || '') + 'settings-default');
    await click(`document.querySelector('label[for=ordpar-nestminis-stacked]')`); await sleep(300);
    g.stacked = await read();
    g.stored = await E(`localStorage.getItem('nestminis')`);
    await shotBlock((args.shotPrefix || '') + 'settings-stacked');
    await click(`document.querySelector('label[for=ordpar-nestminis-off]')`); await sleep(300);
    g.off = await read();
    await shotBlock((args.shotPrefix || '') + 'settings-off');
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
