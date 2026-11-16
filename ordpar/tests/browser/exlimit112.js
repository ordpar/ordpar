// Decisions 112 (Robin, 2026-10-23): how many examples show under each sense, as a setting.
//
// For one viewport (args.mobile: a phone, the line tapped; else a computer, the line clicked), in a
// fresh context, on *gå* (args.id; its first sense has 15 examples): the setting `exlimit`
// (all | 1 … 10) cuts every example list outside a mini to its first n items, and, while `exmore`
// is on (the default), a line "Show N more examples" under a cut list opens the rest in place. Read
// in the article (set in place, then after a reload; args.sub's subsenses), a full search result, a list-view row and a
// favourites row; with `exmore` off; with the examples' English hidden (111) on the opened ones; a
// mini (args.miniFrom, args.miniTo) keeps its own cap; the settings page draws the drop-down.
//
// Result: { base, cases: { <name>: LISTS or {...} } }; LISTS = { lists: [{ n, shown, line, lineShown,
//   inExpr }], first: {...}, cls, stored } — `n` a list's examples, `shown` how many show, `line`
//   its "Show N more" line's text (null when none), `lineShown` whether it shows.
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

const LISTS = (rootSel = 'main') => `(() => {
  const root = document.querySelector(${JSON.stringify(rootSel)});
  if (!root) return null;
  const vis = e => !!e && e.getClientRects().length > 0;
  // site decisions 152: a line's words as drawn (its Norwegian copy ships hidden beside them); a
  // line the sheet hides, its English copy, the one the default settings draw
  const drawn = e => vis(e) ? e.innerText
    : ([...e.querySelectorAll('.ordpar-l-en')].map(x => x.textContent).join('') || e.textContent);
  const read = u => {
    const items = [...u.children].filter(li => !li.classList.contains('ordpar-exmore'));
    const line = u.querySelector(':scope > li.ordpar-exmore');
    return { n: items.length, shown: items.filter(vis).length,
      line: line ? drawn(line) : null, lineShown: vis(line),
      inExpr: !!u.closest('.ordbok-expr'), sub: !!u.closest('.ordbok-sub, .ordbok-subsenses'), en: items.filter(li => vis(li.querySelector(':scope > .ordpar-en'))).length,
      cues: items.filter(li => vis(li.querySelector(':scope > .ordpar-excue'))).length };
  };
  const lists = [...root.querySelectorAll('ul.ordbok-ex-list')].filter(u => !u.closest('.ordbok-xmini')).map(read);
  const f = root.querySelector('.ordbok-senses > li > ul.ordbok-ex-list, .ordbok-sec > div[id] > ul.ordbok-ex-list');
  return { lists, first: f ? read(f) : null,
    cls: [...document.documentElement.classList].filter(c => c.startsWith('ordpar-ex')),
    stored: localStorage.getItem('exlimit'), more: localStorage.getItem('exmore') };
})()`;

async function press(p, x, y) { if (args.mobile) await p.tap(x, y); else await p.click(x, y); await sleep(200); }

/** Press the first list's "Show N more" line under `rootSel`; return the list as it is after. */
async function openFirst(p, rootSel = 'main') {
  const at = await p.eval(`(() => {
    const root = document.querySelector(${JSON.stringify(rootSel)});
    const b = root && [...root.querySelectorAll('ul.ordbok-ex-list > li.ordpar-exmore > button')]
      .find(x => !x.closest('.ordbok-xmini') && x.getClientRects().length);
    if (!b) return null;
    document.querySelectorAll('[data-t112]').forEach(n => n.removeAttribute('data-t112'));
    b.closest('ul').setAttribute('data-t112', '1');
    b.scrollIntoView({ block: 'center' });
    const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, text: b.innerText, tag: b.tagName };   // 152: as drawn
  })()`);
  if (!at) return { found: false };
  await press(p, at.x, at.y);
  const after = await p.eval(`(() => { const u = document.querySelector('[data-t112]');
    const vis = e => !!e && e.getClientRects().length > 0;
    const items = [...u.children].filter(li => !li.classList.contains('ordpar-exmore'));
    return { n: items.length, shown: items.filter(vis).length, line: !!u.querySelector(':scope > .ordpar-exmore'),
      en: items.filter(li => vis(li.querySelector(':scope > .ordpar-en'))).length,
      cues: items.filter(li => vis(li.querySelector(':scope > .ordpar-excue'))).length }; })()`);
  return { found: true, text: at.text, tag: at.tag, after };
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  const art = base + '/bm-en/' + args.id + '/';
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); true`);

  // All (the default), then 3 set in place, then after a reload
  await p.goto(art, 800);
  cases.all = await p.eval(LISTS());
  await p.eval(`ordparShell.setSetting('exlimit', '3'); true`);
  await p.frames();
  cases.inPlace = await p.eval(LISTS());
  await p.reload(800);
  cases.three = await p.eval(LISTS());
  cases.threeOpen = await openFirst(p);
  // subsenses (args.sub: an article whose subsenses have more examples than 3, and fewer)
  await p.goto(base + '/bm-en/' + args.sub + '/', 600);
  cases.sub = await p.eval(LISTS());
  await p.goto(art, 600);
  // 14: one left over, the line in the singular
  await p.eval(`localStorage.setItem('exlimit', '14'); true`);   // not a choice: read as All
  await p.reload(600);
  cases.fourteenInvalid = await p.eval(LISTS());
  await p.eval(`localStorage.setItem('exlimit', '10'); true`);
  await p.reload(600);
  cases.ten = await p.eval(LISTS());
  // 1: the set phrases' lists of two and three are cut too, in the singular where one is left
  await p.eval(`localStorage.setItem('exlimit', '1'); true`);
  await p.reload(600);
  cases.one = await p.eval(LISTS());
  // the line off
  await p.eval(`localStorage.setItem('exlimit', '3'); localStorage.setItem('exmore', 'off'); true`);
  await p.reload(600);
  cases.off = await p.eval(LISTS());
  await p.eval(`localStorage.removeItem('exmore'); true`);
  // with the examples' English hidden (111): the opened ones hide theirs too
  await p.eval(`localStorage.setItem('examples', 'no'); true`);
  await p.reload(800);
  cases.hidden = await p.eval(LISTS());
  cases.hiddenOpen = await openFirst(p);
  await p.eval(`localStorage.removeItem('examples'); true`);

  // a full search result (list view off)
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.word), 500);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordbok-ex-list > li').length > 0`);
  await sleep(500);
  cases.full = await p.eval(LISTS('[data-ordpar-results]'));
  cases.fullOpen = await openFirst(p, '[data-ordpar-results]');

  // a list-view row's article
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  await p.goto(art, 300);
  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.word), 500);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 0`);
  await p.eval(`(() => { const b = [...document.querySelectorAll('.ordpar-row-button')]
    .find(x => (x.closest('[data-id]') || x).getAttribute('data-id') === '${args.id}') || document.querySelector('.ordpar-row-button');
    b.click(); return true; })()`);
  await until(p, `!!document.querySelector('.ordpar-row-panel:not([hidden]) .ordbok-ex-list > li')`);
  await sleep(500);
  cases.list = await p.eval(LISTS('.ordpar-row-panel:not([hidden])'));
  cases.listOpen = await openFirst(p, '.ordpar-row-panel:not([hidden])');
  await p.eval(`localStorage.removeItem('listview'); true`);

  // a favourites row: the heart on the article page, then the row opened on /favourites/
  await p.goto(art, 800);
  await p.eval(`(() => { const h = document.querySelector('.ordpar-heart'); if (h) h.click(); return !!h; })()`);
  await sleep(300);
  await p.goto(base + '/favourites/', 800);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 0`, 5000);
  await p.eval(`(() => { const b = document.querySelector('.ordpar-row-button'); if (b) b.click(); return !!b; })()`);
  await until(p, `!!document.querySelector('.ordpar-row-panel:not([hidden]) .ordbok-ex-list > li')`, 8000);
  await sleep(500);
  cases.fav = await p.eval(LISTS('.ordpar-row-panel:not([hidden])'));

  // a mini keeps its own cap: limit 1, a mini opened from args.miniFrom to args.miniTo
  await p.eval(`localStorage.setItem('exlimit', '1'); true`);
  await p.goto(base + '/bm-en/' + args.miniFrom + '/', 800);
  cases.miniOpened = await p.eval(`(async () => {
    const a = document.querySelector('a.ordbok-xword[href^="/bm-en/${args.miniTo}/"]'); if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 60; t++) { if (document.querySelector('.ordbok-xmini .ordbok-ex-list > li')) break;
      await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 300));
    return !!document.querySelector('.ordbok-xmini .ordbok-ex-list > li'); })()`);
  cases.mini = await p.eval(`(() => {
    const vis = e => !!e && e.getClientRects().length > 0;
    const ls = [...document.querySelectorAll('.ordbok-xmini ul.ordbok-ex-list')];
    return { lists: ls.map(u => ({ n: u.children.length, shown: [...u.children].filter(vis).length,
      line: !!u.querySelector('.ordpar-exmore') })) }; })()`);

  // the settings page: the drop-down and the line's setting, shown only with a number
  await p.eval(`localStorage.clear(); true`);
  await p.goto(base + '/settings/', 800);
  const SET = `(() => {
    const s = document.querySelector('select[data-key="exlimit"]');
    const f = k => document.querySelector('fieldset[data-setting="' + k + '"]');
    const vis = e => !!e && e.getClientRects().length > 0;
    const order = [...document.querySelectorAll('fieldset[data-setting]')].map(x => x.getAttribute('data-setting'));
    return { select: !!s, options: s ? [...s.options].map(o => [o.value, o.textContent]) : null,
      value: s ? s.value : null, label: s ? s.getAttribute('aria-labelledby') : null,
      title: f('exlimit') ? f('exlimit').querySelector('.ordpar-field-title').textContent : null,
      moreShown: vis(f('exmore')), moreTitle: f('exmore') ? f('exmore').querySelector('.ordpar-field-title').textContent : null,
      after: order.slice(order.indexOf('examples'), order.indexOf('examples') + 4),
      hints: ['exlimit', 'exmore'].map(k => !!(f(k) && f(k).querySelector('.ordpar-hint-button'))),
      stats: !!f('stats'), statsText: document.body.textContent.includes('Send usage statistics'),
      stored: localStorage.getItem('exlimit'), cls: [...document.documentElement.classList].filter(c => c.startsWith('ordpar-ex')) };
  })()`;
  cases.settings = await p.eval(SET);
  await p.eval(`(() => { const s = document.querySelector('select[data-key="exlimit"]'); if (!s) return false; s.value = '3';
    s.dispatchEvent(new Event('change', { bubbles: true })); return true; })()`);
  await p.frames();
  cases.settingsThree = await p.eval(SET);
  await p.reload(600);
  cases.settingsReload = await p.eval(SET);
  // "Delete stored data" puts it back to All
  await p.eval(`(() => { document.querySelector('.ordpar-settings-delete').click(); return true; })()`);
  await p.frames();
  cases.settingsDeleted = await p.eval(SET);
  await done({ base, cases });
});
