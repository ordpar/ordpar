// Decisions 102: the article card in ordbokene's widths, and no inflection table past its card.
//
// Part 1, the widths (args.widths): for each window width, a computer viewport (w × 900, no
// touch), the card's rendered width on the article page (`article.ordpar-card`, *fange* III), a
// full result (`.ordpar-result`, the search "fange" with `listview` = off) and the list view's box
// (`.ordpar-rows`, the same search with `listview` = on, in a 360 px tall window so that its short
// page scrolls). Each a fresh load at that width, the page's clientWidth recorded with each.
//
// Part 2, the tables (args.tables): for each { id, q } and window width, with `infl` = open, the
// article page and the article's row opened in the list view of the search q. For every
// inflection mount in the card: the layout shown, whether the wide tables FIT the mount's box
// (since decisions 108 their fully STACKED width — min-content, no cell held whole — read with the wide layout shown for
// the moment; their unwrapped width, max-content, and the width each is drawn at beside it),
// and how far the right edge of every visible table and strip lies
// past the card's content box and past the card itself. Also the page's sideways overflow.
//
// Part 3, a resize (args.resize): the article page loaded at `from` px, the window then set to
// `to` px without a reload; the layout after the resize (ours re-decides; ordbokene does not).
//
// args: { widths: [w…], widthWord, widthId, tables: [{ id, q }], tableWidths: [w…], resize: { id, from, to } }
// Result: { widths: [{ w, cw, art, result, list }], tables: [{ id, w, view, ... }], resize: {...} }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

const WIDTH = sel => `(() => { const e = document.querySelector(${JSON.stringify(sel)});
  return e && e.getClientRects().length ? Math.round(e.getBoundingClientRect().width * 10) / 10 : null; })()`;

// the card's tables, measured: `card` the card element's selector
const TABLES = sel => `(() => {
  const card = document.querySelector(${JSON.stringify(sel)}); if (!card) return { err: 'no card ' + ${JSON.stringify(sel)} };
  const cs = getComputedStyle(card), cr = card.getBoundingClientRect();
  const contentRight = cr.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
  const round = x => Math.round(x * 10) / 10;
  const groups = [...card.querySelectorAll('.ordpar-inflection-tables')].filter(g => g.getClientRects().length).map(g => {
    const shown = [...g.querySelectorAll('.ordpar-infl-wrap')].filter(w => w.getClientRects().length);
    const layout = [...new Set(shown.map(w => /--narrow/.test(w.className) ? 'narrow' : 'wide'))].join('+');
    const right = Math.max(...shown.map(w => w.getBoundingClientRect().right),
      ...shown.map(w => { const t = w.querySelector('table'); return t ? Math.min(t.getBoundingClientRect().right, w.getBoundingClientRect().right) : -1e9; }));
    // the wide tables' unwrapped (max-content) and stacked (min-content) widths, and the width
    // each is drawn at, read with the wide layout shown for the moment
    const had = g.className;
    g.classList.remove('ordpar-force-narrow'); g.classList.add('ordpar-force-wide');
    const read = (t, width) => { const w = t.style.width, mw = t.style.maxWidth; t.style.width = width; t.style.maxWidth = 'none';
      const x = t.getBoundingClientRect().width; t.style.width = w; t.style.maxWidth = mw; return round(x); };
    const ts = [...g.querySelectorAll('.ordpar-infl-wrap--wide table')];
    const wide = ts.map(t => read(t, 'max-content'));
    // fully stacked: min-content with no cell held whole (ordpar-col-whole, decisions 108)
    const held = [...g.querySelectorAll('.ordpar-col-whole')]; held.forEach(x => x.classList.remove('ordpar-col-whole'));
    const stacked = ts.map(t => read(t, 'min-content'));
    held.forEach(x => x.classList.add('ordpar-col-whole'));
    const drawn = ts.map(t => round(t.getBoundingClientRect().width));
    g.className = had;
    const box = round(g.getBoundingClientRect().width);
    return { layout, box, wide, stacked, drawn, fits: stacked.every(x => x <= box + 0.5),
      unwrappedFits: wide.map(x => x <= box + 0.5), right: round(right),
      pastContent: round(right - contentRight), pastCard: round(right - cr.right) };
  });
  const E = document.documentElement;
  return { card: round(cr.width), groups, sideways: E.scrollWidth - E.clientWidth };
})()`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const out = { widths: [], tables: [] };
  const setting = async (kv) => {
    await p.goto(base + '/', 200);
    await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); ${Object.entries(kv)
      .map(([k, v]) => `localStorage.setItem(${JSON.stringify(k)}, ${JSON.stringify(v)});`).join(' ')} true`);
  };

  // part 1
  if (args.widths) {
    const rec = {};
    for (const w of args.widths) rec[w] = { w };
    await setting({});
    for (const w of args.widths) {
      await p.size(w, 900);
      await p.goto(base + '/bm-en/' + args.widthId + '/', 200);
      await until(p, `!!document.querySelector('article.ordpar-card')`);
      rec[w].cw = await p.eval('document.documentElement.clientWidth');
      rec[w].art = await p.eval(WIDTH('article.ordpar-card'));
    }
    await setting({ listview: 'off' });
    for (const w of args.widths) {
      await p.size(w, 900);
      await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.widthWord), 200);
      // the result painted AND the page grown past the window, so the scrollbar the widths assume is
      // there (read too early under parallel load, it was not: site decisions 145, 2026-10-27)
      await until(p, `!!document.querySelector('.ordpar-result') && document.documentElement.scrollHeight > innerHeight`);
      rec[w].result = await p.eval(WIDTH('.ordpar-result'));
      rec[w].resultCw = await p.eval('document.documentElement.clientWidth');
    }
    await setting({ listview: 'on' });
    for (const w of args.widths) {
      // a short window, so the three rows' page scrolls and shows the scrollbar the widths assume
      await p.size(w, 360);
      await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.widthWord), 200);
      await until(p, `!!document.querySelector('.ordpar-rows')`);
      rec[w].list = await p.eval(WIDTH('.ordpar-rows'));
      rec[w].listCw = await p.eval('document.documentElement.clientWidth');
    }
    out.widths = args.widths.map(w => rec[w]);
  }

  // part 2
  if (args.tables) {
    await setting({ infl: 'open' });
    for (const c of args.tables) for (const w of args.tableWidths) {
      await p.size(w, 900);
      await p.goto(base + '/bm-en/' + c.id + '/', 200);
      await until(p, `!!document.querySelector('article.ordpar-card .ordpar-inflection-tables table')`);
      await p.frames();
      out.tables.push({ id: c.id, w, view: 'article', ...(await p.eval(TABLES('article.ordpar-card'))) });
    }
    await setting({ infl: 'open', listview: 'on' });
    for (const c of args.tables) for (const w of args.tableWidths) {
      await p.size(w, 900);
      await p.goto(base + '/bm-en/?q=' + encodeURIComponent(c.q), 200);
      const sel = `.ordpar-row[data-id="${c.id}"]`;
      if (!await until(p, `!!document.querySelector(${JSON.stringify(sel + ' .ordpar-row-button')})`)) {
        out.tables.push({ id: c.id, w, view: 'list', err: 'no row ' + c.id + ' for ' + c.q }); continue;
      }
      await p.eval(`document.querySelector(${JSON.stringify(sel + ' .ordpar-row-button')}).click(); true`);
      await until(p, `!!document.querySelector(${JSON.stringify(sel + ' .ordpar-inflection-tables table')})`);
      await p.frames();
      out.tables.push({ id: c.id, w, view: 'list', ...(await p.eval(TABLES('.ordpar-rows'))) });
    }
  }

  // part 3
  if (args.resize) {
    const r = args.resize;
    await setting({ infl: 'open' });
    await p.size(r.from, 900);
    await p.goto(base + '/bm-en/' + r.id + '/', 200);
    await until(p, `!!document.querySelector('article.ordpar-card .ordpar-inflection-tables table')`);
    await p.frames();
    const before = await p.eval(TABLES('article.ordpar-card'));
    await p.size(r.to, 900);
    await sleep(300); await p.frames();
    const after = await p.eval(TABLES('article.ordpar-card'));
    out.resize = { ...r, before, after };
  }
  await done({ base, ...out });
});
