// Decisions 111 (Robin, 2026-10-23): the examples' English behind a reveal, as a setting.
//
// For one viewport (args.mobile: a phone, the cue tapped; else a computer, the cue clicked), in a
// fresh context: the setting `examples` (both | no) is set in place through `ordparShell`, then
// read back after a reload; with `no`, an example's English is hidden behind the "Show English"
// cue, a click (or tap, or Enter) opens it and a click on the opened English closes it, in the
// article page, a full search result, a list-view row's article, a mini, a set phrase and an
// added ("+") example; with `both`, every English line shows and no cue does. The four pairs of
// `defs` (both | en | no) × `examples` are read on one article.
//
// args: { mobile: bool, expr: <id with set-phrase examples>, untranslated: <id whose examples have no English> }
// Result: { base, cases: { <name>: STATE or {...} } }; STATE = { examples, withEn, enShown,
//   cuesShown, cueWithoutEn, cls, pairsEn, pairCues }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

const STATE = (rootSel = null) => `(() => {
  const root = ${rootSel ? `document.querySelector(${JSON.stringify(rootSel)})` : 'document'};
  if (!root) return null;
  const vis = e => !!e && e.getClientRects().length > 0;
  const lis = [...root.querySelectorAll('.ordbok-ex-list > li')].filter(vis);
  const en = li => li.querySelector(':scope > .ordpar-en');
  const cue = li => li.querySelector(':scope > .ordpar-excue');
  const withEn = lis.filter(en);
  const pairs = [...root.querySelectorAll('.ordpar-pair:not(.ordpar-fml)')].filter(p => vis(p) && !p.closest('.ordbok-inline'));
  return { examples: lis.length, withEn: withEn.length,
    enShown: withEn.filter(li => vis(en(li))).length,
    cuesShown: lis.filter(li => vis(cue(li))).length,
    cueWithoutEn: lis.filter(li => !en(li) && cue(li)).length,
    added: withEn.filter(li => li.querySelector(':scope > .ordbok-added')).length,
    inExpr: withEn.filter(li => li.closest('.ordbok-expr')).length,
    cls: document.documentElement.classList.contains('ordpar-examples-no'),
    stored: localStorage.getItem('examples'),
    pairsEn: pairs.filter(p => vis(p.querySelector(':scope > span[lang=en]'))).length,
    pairCues: pairs.filter(p => vis(p.querySelector(':scope > .ordpar-encue'))).length, pairs: pairs.length };
})()`;

// the first example under `rootSel` whose cue shows: mark it, return the cue's centre
const MARK = (rootSel) => `(() => {
  const root = document.querySelector(${JSON.stringify(rootSel)}) || document;
  document.querySelectorAll('[data-t111]').forEach(n => n.removeAttribute('data-t111'));
  const c = [...root.querySelectorAll('.ordbok-ex-list > li > .ordpar-excue')].find(b => b.getClientRects().length);
  if (!c) return null;
  c.parentNode.setAttribute('data-t111', '1');
  c.scrollIntoView({ block: 'center' });
  const r = c.getBoundingClientRect();
  // site decisions 152: the cue's words as drawn (its Norwegian copy ships hidden beside them)
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, text: c.innerText };
})()`;
const ONE = `(() => { const li = document.querySelector('[data-t111]'); if (!li) return null;
  const vis = e => !!e && e.getClientRects().length > 0;
  const en = li.querySelector(':scope > .ordpar-en'), r = en.getBoundingClientRect();
  return { en: vis(en), cue: vis(li.querySelector(':scope > .ordpar-excue')),
           x: r.left + Math.min(20, r.width / 2), y: r.top + r.height / 2 }; })()`;

async function press(p, x, y) { if (args.mobile) await p.tap(x, y); else await p.click(x, y); await sleep(150); }

/** Open and close one example under `rootSel` with the pointer; then open one with the keyboard. */
async function cycle(p, rootSel) {
  const c = await p.eval(MARK(rootSel));
  if (!c) return { found: false };
  const before = await p.eval(ONE);
  await press(p, c.x, c.y);
  const opened = await p.eval(ONE);
  await press(p, opened.x, opened.y);
  const closed = await p.eval(ONE);
  // the keyboard: the cue focused, Enter
  await p.eval(MARK(rootSel));
  await p.eval(`document.querySelector('[data-t111] > .ordpar-excue').focus(); true`);
  await p.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await sleep(150);
  const key = await p.eval(ONE);
  return { found: true, text: c.text, before, opened, closed, key };
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); true`);

  // the default, then `no` set in place, then after a reload
  await p.goto(base + '/bm-en/13791/', 800);
  cases.articleBoth = await p.eval(STATE());
  await p.eval(`ordparShell.setSetting('examples', 'no'); true`);
  await p.frames();
  cases.articleNoInPlace = await p.eval(STATE());
  await p.reload(800);
  cases.articleNo = await p.eval(STATE());
  cases.articleCycle = await cycle(p, 'main');

  // an added example ("+"), and a set phrase's examples
  await p.goto(base + '/bm-en/42618/', 800);
  cases.added = await p.eval(STATE());
  cases.addedCycle = await cycle(p, 'main');
  await p.goto(base + '/bm-en/' + args.expr + '/', 800);
  cases.expr = await p.eval(STATE('.ordbok-expr'));
  cases.exprCycle = await cycle(p, '.ordbok-expr');

  // an untranslated article: its examples have no English, so no cue
  await p.goto(base + '/bm-en/' + args.untranslated + '/', 800);
  cases.untranslated = await p.eval(STATE('main'));

  // a full search result (list view off)
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/?q=fange', 500);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordbok-ex-list > li').length > 0`);
  await sleep(500);
  cases.full = await p.eval(STATE('[data-ordpar-results]'));
  cases.fullCycle = await cycle(p, '[data-ordpar-results]');

  // a list-view row's article
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  await p.goto(base + '/bm-en/?q=fange', 500);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 0`);
  await p.eval(`document.querySelector('.ordpar-row-button').click(); true`);
  await until(p, `!!document.querySelector('.ordpar-row-panel:not([hidden]) .ordbok-ex-list > li')`);
  await sleep(500);
  cases.list = await p.eval(STATE('.ordpar-row-panel:not([hidden])'));
  cases.listCycle = await cycle(p, '.ordpar-row-panel:not([hidden])');
  await p.eval(`localStorage.removeItem('listview'); true`);

  // a mini: lysing I (36349), opened from 31178
  await p.goto(base + '/bm-en/31178/', 800);
  const opened = await p.eval(`(async () => {
    const a = document.querySelector('a.ordbok-xword[href^="/bm-en/36349/"]'); if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 60; t++) { if (document.querySelector('.ordbok-xmini .ordbok-ex-list > li')) break;
      await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 300));
    return !!document.querySelector('.ordbok-xmini .ordbok-ex-list > li'); })()`);
  cases.miniOpened = opened;
  cases.mini = await p.eval(STATE('.ordbok-xmini'));
  cases.miniCycle = await cycle(p, '.ordbok-xmini');
  cases.miniStillOpen = await p.eval(`!!document.querySelector('.ordbok-xmini .ordbok-ex-list > li')`);

  // back to both: in place, then the mini and the article
  await p.eval(`ordparShell.setSetting('examples', 'both'); true`);
  await p.frames();
  cases.miniBoth = await p.eval(STATE('.ordbok-xmini'));

  // defs × examples on one article
  for (const defs of ['both', 'en', 'no']) {
    for (const ex of ['both', 'no']) {
      await p.eval(`localStorage.setItem('defs', '${defs}'); localStorage.setItem('examples', '${ex}'); true`);
      await p.goto(base + '/bm-en/13791/', 800);
      cases['defs-' + defs + '-ex-' + ex] = await p.eval(STATE('main'));
    }
  }
  await done({ base, cases });
});
