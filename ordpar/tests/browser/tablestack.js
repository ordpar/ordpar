// Decisions 108: the wide inflection table stacks its cells before going narrow.
//
// For each case (args.cases: { view: 'article' | 'list', w, h, mobile, squeeze }), *møte* II (args.id)
// with `infl` = open: the article page, or its row opened in the list view of the search
// args.q. For every inflection mount in the card: the layout shown; each wide table's unwrapped
// (max-content) and fully stacked (min-content, no cell held whole) width, read with the wide layout shown for the moment,
// and the width it is drawn at; the box; how far the shown tables run past the card's content
// box; the lines each cell of the shown wide tables is drawn in (its text, line by line); each
// column of those tables (decisions 108, column by column: its name, whether it is stacked, its
// width, its spare width beside its widest line) and each column's unwrapped width (`colWide`);
// and every place a cell is broken INSIDE a form — a form's own text over two lines, or a frame
// before a form (å, har, den/det, en) on another line than the form. The form check reads the
// DOM only by its text nodes and the `ordpar-frame` class, so it reads the older markup too.
// The forms' sound icons (decisions 159, a `button.ordpar-play` with a visually hidden "Play"):
// their hidden words are no text of the cell, and an icon's box counts on its line like a word
// (so a column's widest line runs to its icon's right edge); `iconParts` lists each icon parted
// from the form before it, as drawn and with every shown table squeezed to its narrowest, in any
// layout; `icons` how many icons the tables carry.
// `squeeze` (an article case): the mount then narrowed to that many px less than the participle
// table's unwrapped width — the state of Robin's shot 5, which his screen's fonts reach at his
// window but headless Edge's do not.
//
// A case's own `id` (an article case) opens that article instead of args.id (decisions 108, the
// space-saved order: *brenne* I, where the two orders differ).
//
// args: { id, q, cases: [{ view, w, h, mobile, squeeze, id }] }
// Result: { base, cases: [{ view, w, h, mobile, card, groups: [...], sideways }] }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  for (let t = 0; t < ms; t += 100) { try { if (await p.eval(expr)) return true; } catch (e) {} await sleep(100); }
  return false;
}

// runs in the page: `sel` the card
function measure(sel) {
  const card = document.querySelector(sel); if (!card) return { err: 'no card ' + sel };
  const round = x => Math.round(x * 10) / 10;
  const cs = getComputedStyle(card), cr = card.getBoundingClientRect();
  const contentRight = cr.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
  const SP = /[\s ]+/g;
  const tops = (node, from, to) => {
    if (to <= from) return [];
    const r = document.createRange(); r.setStart(node, from); r.setEnd(node, to);
    return [...r.getClientRects()].filter(b => b.width > 0.5).map(b => b.top);
  };
  const distinct = ts => ts.reduce((a, t) => a.some(x => Math.abs(x - t) < 3) ? a : a.concat([t]), []);
  // the sound icon (decisions 159): its hidden "Play" is no text of the cell; the icon itself is
  // drawn on its line like a word (`rows` places its box, so it counts in its line's width)
  const inIcon = n => !!(n.parentElement && n.parentElement.closest('.ordpar-play'));
  const icons = cell => [...cell.querySelectorAll('.ordpar-play')].map(b => b.getBoundingClientRect()).filter(b => b.width > 0.5);
  const rowsOf = cell => {
    const rows = []; const w = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) {
      if (inIcon(n) || !n.parentElement.getClientRects().length) continue;
      for (let i = 0; i < n.data.length; i++) {
        const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1);
        const b = [...r.getClientRects()].filter(x => x.width > 0.5)[0]; const top = b ? b.top : null;
        if (top === null) { if (rows.length) rows[rows.length - 1].s += n.data[i]; continue; }
        let row = rows.find(x => Math.abs(x.top - top) < 3);
        if (!row) { row = { top, h: b.height, s: '', l: b.left, r: b.right }; rows.push(row); }
        row.s += n.data[i];
        if (n.data[i].trim()) { row.l = Math.min(row.l, b.left); row.r = Math.max(row.r, b.right); }
      }
    }
    // an icon on the line whose middle it sits in (its box is a little taller than the text's)
    icons(cell).forEach(b => {
      const mid = (b.top + b.bottom) / 2;
      let row = rows.find(x => mid >= x.top - 1 && mid <= x.top + x.h + 1);
      if (!row) { row = { top: b.top, h: b.height, s: '', l: b.left, r: b.right }; rows.push(row); }
      row.icon = true; row.l = Math.min(row.l, b.left); row.r = Math.max(row.r, b.right);
    });
    rows.sort((a, b) => a.top - b.top);
    return rows.filter(x => x.s.trim() || x.icon);
  };
  const lines = (cell, widths) => {
    const rows = rowsOf(cell);
    if (widths) return rows.map(x => x.r - x.l);
    return rows.map(x => x.s.replace(SP, ' ').trim()).filter(Boolean);
  };
  // the table's grid columns: for each, its cells with colspan 1 (a spanning header is no column)
  const gridColumns = t => {
    const cols = [], taken = [];
    [...t.rows].forEach((row, r) => { let c = 0;
      [...row.cells].forEach(cell => {
        while (taken[r] && taken[r][c]) c++;
        const cs = cell.colSpan || 1, rs = cell.rowSpan || 1;
        for (let i = 0; i < rs; i++) for (let j = 0; j < cs; j++) (taken[r + i] = taken[r + i] || [])[c + j] = 1;
        if (cs === 1) (cols[c] = cols[c] || []).push(cell);
        c += cs;
      });
    });
    return cols.filter(x => x && x.length);
  };
  // each column as drawn: its name (its header's text), whether it is stacked (a cell over more
  // than one line), its width, and its spare width — the least room any of its cells leaves
  // beside its widest line, inside the cell's padding
  const columns = t => gridColumns(t).map(cells => {
    const th = cells.find(x => x.tagName === 'TH');
    const spare = Math.min(...cells.map(x => { const cs = getComputedStyle(x);
      const inner = x.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const ws = lines(x, true); return ws.length ? inner - Math.max(...ws) : inner; }));
    return { name: th ? lines(th).join(' ') : '', stacked: cells.some(x => rowsOf(x).length > 1),
      width: round(cells[0].getBoundingClientRect().width), spare: round(spare) };
  });
  // a form's text node: outside every frame, more than spaces and commas
  const isFrame = n => !!(n.parentElement && n.parentElement.closest('.ordpar-frame'));
  const blank = n => n.data.replace(SP, '').replace(/,/g, '') === '';
  const isForm = n => !isFrame(n) && !blank(n);
  const formBreaks = td => {
    const out = []; const all = []; const w = document.createTreeWalker(td, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) if (!inIcon(n) && n.parentElement.getClientRects().length) all.push(n);
    all.forEach((n, k) => {
      if (isForm(n)) {
        const lead = n.data.length - n.data.replace(/^[\s ,]+/, '').length;
        const end = n.data.replace(/[\s ,]+$/, '').length;
        if (distinct(tops(n, lead, end)).length > 1) out.push('a form over two lines: ' + n.data.trim());
      } else if (isFrame(n) && !blank(n)) {
        // a frame BEFORE a form: the next text node that is not spaces is a form
        let j = k + 1; while (j < all.length && !isFrame(all[j]) && blank(all[j]) && !/,/.test(all[j].data)) j++;
        if (j < all.length && isForm(all[j])) {
          const f = tops(n, 0, n.data.length), g = tops(all[j], 0, all[j].data.length);
          if (f.length && g.length && Math.abs(f[f.length - 1] - g[0]) >= 3)
            out.push('a frame parted from its form: ' + n.data.trim() + ' | ' + all[j].data.trim());
        }
      }
    });
    return out;
  };
  // the sound icon parted from its form (decisions 159: the form, its frames and its icon one
  // unit, the icon after the whole of it): an icon whose middle is not on the line of the last
  // character before it — in any layout, wide or narrow
  const iconBreaks = td => [...td.querySelectorAll('.ordpar-play')].filter(b => b.getClientRects().length).map(b => {
    const w = document.createTreeWalker(td, NodeFilter.SHOW_TEXT); let n, last = null;
    while ((n = w.nextNode())) {
      if (b.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING) break;
      if (!inIcon(n) && n.data.trim() && n.parentElement.getClientRects().length) last = n;
    }
    if (!last) return 'an icon with no form before it: ' + td.textContent.trim();
    const end = last.data.replace(/\s+$/, '').length;
    const r = document.createRange(); r.setStart(last, end - 1); r.setEnd(last, end);
    const t = [...r.getClientRects()].filter(x => x.width > 0.5).pop(), bb = b.getBoundingClientRect(), mid = (bb.top + bb.bottom) / 2;
    return t && mid >= t.top && mid <= t.bottom ? null : 'an icon parted from its form: ' + last.data.trim();
  }).filter(Boolean);
  // ... as drawn, and with every shown table squeezed to its narrowest (min-content, no column held
  // whole), where a break before the icon would show
  const iconCheck = g => {
    const tds = () => [...g.querySelectorAll('.ordpar-infl-wrap td')].filter(x => x.getClientRects().length);
    const out = [].concat(...tds().map(iconBreaks));
    const tables = [...g.querySelectorAll('.ordpar-infl-wrap table')].filter(t => t.getClientRects().length);
    const held = [...g.querySelectorAll('.ordpar-col-whole')]; held.forEach(x => x.classList.remove('ordpar-col-whole'));
    const was = tables.map(t => [t.style.width, t.style.minWidth, t.style.maxWidth]);
    tables.forEach(t => { t.style.width = '0px'; t.style.minWidth = '0px'; t.style.maxWidth = 'none'; });
    const squeezed = [].concat(...tds().map(iconBreaks)).map(x => x + ' (squeezed)');
    tables.forEach((t, i) => { [t.style.width, t.style.minWidth, t.style.maxWidth] = was[i]; });
    held.forEach(x => x.classList.add('ordpar-col-whole'));
    return out.concat(squeezed);
  };
  const groups = [...card.querySelectorAll('.ordpar-inflection-tables')].filter(g => g.getClientRects().length).map(g => {
    const iconParts = iconCheck(g), icons = g.querySelectorAll('td .ordpar-play').length;
    const shown = [...g.querySelectorAll('.ordpar-infl-wrap')].filter(w => w.getClientRects().length);
    const layout = [...new Set(shown.map(w => /--narrow/.test(w.className) ? 'narrow' : 'wide'))].join('+');
    const right = Math.max(...shown.map(w => w.getBoundingClientRect().right),
      ...shown.map(w => { const t = w.querySelector('table'); return t ? Math.min(t.getBoundingClientRect().right, w.getBoundingClientRect().right) : -1e9; }));
    const box = round(g.getBoundingClientRect().width);
    // the cells as drawn, before anything is forced
    const wideTables = [...g.querySelectorAll('.ordpar-infl-wrap--wide table')];
    const cells = layout === 'wide' ? wideTables.map(t =>
      [...t.querySelectorAll('th,td')].filter(x => x.getClientRects().length).map(x => ({ tag: x.tagName.toLowerCase(), lines: lines(x) }))) : [];
    const breaks = layout === 'wide' ? [].concat(...[...g.querySelectorAll('.ordpar-infl-wrap--wide td')].map(formBreaks)) : [];
    const drawn = wideTables.map(t => round(t.getBoundingClientRect().width));
    const cols = layout === 'wide' ? wideTables.map(columns) : [];
    const had = g.className;
    g.classList.remove('ordpar-force-narrow'); g.classList.add('ordpar-force-wide');
    const read = (t, width) => { const w = t.style.width, mw = t.style.maxWidth; t.style.width = width; t.style.maxWidth = 'none';
      const x = t.getBoundingClientRect().width; t.style.width = w; t.style.maxWidth = mw; return round(x); };
    const wide = wideTables.map(t => read(t, 'max-content'));
    // the columns' unwrapped widths, read with the table at max-content
    const colWide = wideTables.map(t => { const w = t.style.width, mw = t.style.maxWidth;
      t.style.width = 'max-content'; t.style.maxWidth = 'none';
      const x = gridColumns(t).map(cells => round(cells[0].getBoundingClientRect().width));
      t.style.width = w; t.style.maxWidth = mw; return x; });
    // fully stacked: min-content with no cell held whole (`ordpar-col-whole`, decisions 108)
    const held = [...g.querySelectorAll('.ordpar-col-whole')]; held.forEach(x => x.classList.remove('ordpar-col-whole'));
    const stacked = wideTables.map(t => read(t, 'min-content'));
    held.forEach(x => x.classList.add('ordpar-col-whole'));
    g.className = had;
    return { layout, box, wide, stacked, drawn, cells, cols, colWide, breaks, iconParts, icons,
      pastContent: round(right - contentRight), pastCard: round(right - cr.right) };
  });
  const E = document.documentElement;
  return { card: round(cr.width), groups, sideways: E.scrollWidth - E.clientWidth };
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const out = [];
  let mode = null;
  const M = sel => `(${measure.toString()})(${JSON.stringify(sel)})`;
  const setting = async (kv) => {
    await p.size(1280, 900);
    await p.goto(base + '/', 200);
    await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); ${Object.entries(kv)
      .map(([k, v]) => `localStorage.setItem(${JSON.stringify(k)}, ${JSON.stringify(v)});`).join(' ')} true`);
  };
  for (const c of args.cases) {
    if (mode !== c.view) {
      await setting(c.view === 'list' ? { infl: 'open', listview: 'on' } : { infl: 'open' });
      mode = c.view;
    }
    await p.size(c.w, c.h, !!c.mobile);
    if (c.view === 'article') {
      await p.goto(base + '/bm-en/' + (c.id || args.id) + '/', 300);
      await until(p, `!!document.querySelector('article.ordpar-card .ordpar-inflection-tables table')`);
      // the forms' sound icons (decisions 159) go in once the article's names file is read
      await until(p, `!!document.querySelector('article.ordpar-card .ordpar-inflection td .ordpar-play')`, 3000);
      await p.frames();
      if (c.squeeze) {
        // his shot 5 made exact: the mount narrowed to `squeeze` px less than the participle
        // table's unwrapped width (where his screen's fonts put it); the fit re-decides on the resize
        await p.eval(`(() => { const h = document.querySelector('article.ordpar-card .ordpar-inflection');
          const g = h.querySelector('.ordpar-inflection-tables'), had = g.className;
          g.classList.remove('ordpar-force-narrow'); g.classList.add('ordpar-force-wide');
          const t = g.querySelectorAll('.ordpar-infl-wrap--wide table')[1];
          const w = t.style.width, mw = t.style.maxWidth; t.style.width = 'max-content'; t.style.maxWidth = 'none';
          const x = t.getBoundingClientRect().width; t.style.width = w; t.style.maxWidth = mw; g.className = had;
          h.style.width = (x - ${+c.squeeze}) + 'px'; return x; })()`);
        await sleep(300); await p.frames();
      }
      out.push({ ...c, ...(await p.eval(M('article.ordpar-card'))) });
    } else {
      await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.q), 300);
      const sel = `.ordpar-row[data-id="${args.id}"]`;
      // site decisions 117: the search for a word with a page is answered on that page, whose
      // built rows (under its headline) the script replaces — wait for the script's rows
      if (!await until(p, `!document.querySelector('.ordpar-word-title')
          && !!document.querySelector(${JSON.stringify(sel + ' .ordpar-row-button')})`)) {
        out.push({ ...c, err: 'no row ' + args.id + ' for ' + args.q }); continue;
      }
      await p.eval(`document.querySelector(${JSON.stringify(sel + ' .ordpar-row-button')}).click(); true`);
      await until(p, `!!document.querySelector(${JSON.stringify(sel + ' .ordpar-inflection-tables table')})`);
      await until(p, `!!document.querySelector(${JSON.stringify(sel + ' .ordpar-inflection td .ordpar-play')})`, 3000);
      await p.frames();
      out.push({ ...c, ...(await p.eval(M('.ordpar-rows'))) });
    }
  }
  await done({ base, cases: out });
});
