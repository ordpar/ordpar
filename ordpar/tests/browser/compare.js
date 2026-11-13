// Decisions 102: ordbokene.no's live layout beside ours, for `compare_ordbokene.py` (NOT a test).
//
// Rendered geometry only on ordbokene's side: bounding boxes and the text shown, never a script,
// stylesheet or computed style of theirs (CLAUDE.md, "its code is never ours"). Its card is the
// 6th ancestor of the article's heading (an h3 starting with the headword), the box the
// 2026-10-23 measurement verified against the white card in its screenshots at 113 widths; its
// table layout is read from where two header cells sit (side by side: wide; one under the other:
// narrow). Each width is a fresh load, one page at a time, with a pause between ordbokene's.
//
// args: { obk: 'https://ordbokene.no', cards: { id, word, widths: [w…], phone: [w…] },
//         tables: [{ id, word }], tableWidths: [w…] }
// Result: { cards: [{ w, phone, obk: {card, cw} | {err}, ours: {card, cw} }], tables: [{ id, w, obk, ours }] }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 150) { try { if (await p.eval(expr)) return true; } catch (e) {} await sleep(150); }
  return false;
}

const OBK_HEAD = word => `[...document.querySelectorAll('h3')].filter(e => e.offsetParent && e.innerText.trim().indexOf(${JSON.stringify(word)}) === 0)[0]`;
const OBK = word => `(() => {
  const h = ${OBK_HEAD(word)}; if (!h) return { err: 'no heading' };
  let c = h; for (let i = 0; i < 6; i++) c = c.parentElement;
  const r = c.getBoundingClientRect();
  const cells = [...c.querySelectorAll('th,td')].filter(e => e.offsetParent);
  const find = t => cells.find(x => x.innerText.trim() === t);
  let layout = null;
  for (const [a, b] of [['infinitive', 'present'], ['singular', 'plural']]) {
    const x = find(a), y = find(b);
    if (x && y) { layout = Math.abs(x.getBoundingClientRect().top - y.getBoundingClientRect().top) < 4 ? 'wide' : 'narrow'; break; }
  }
  const tables = [...c.querySelectorAll('table')].filter(e => e.offsetParent).map(t => Math.round(t.getBoundingClientRect().right - r.right));
  return { card: Math.round(r.width * 10) / 10, cw: document.documentElement.clientWidth, layout,
    pastCard: tables.length ? Math.max(...tables) : null };
})()`;
const OURS = `(() => {
  const c = document.querySelector('article.ordpar-card'); if (!c) return { err: 'no card' };
  const r = c.getBoundingClientRect();
  const shown = [...c.querySelectorAll('.ordpar-infl-wrap')].filter(w => w.getClientRects().length);
  const layout = shown.length ? [...new Set(shown.map(w => /--narrow/.test(w.className) ? 'narrow' : 'wide'))].join('+') : null;
  return { card: Math.round(r.width * 10) / 10, cw: document.documentElement.clientWidth, layout,
    pastCard: shown.length ? Math.round(Math.max(...shown.map(w => w.getBoundingClientRect().right)) - r.right) : null };
})()`;

run(async () => {
  const p = await open({ w: 1280, h: 1000 });
  const out = { cards: [], tables: [] };
  const obk = async (id, word, w, phone, clickInfl) => {
    await p.size(w, phone ? 860 : 1000, !!phone);
    await p.goto('about:blank', 50);
    await p.goto(args.obk + '/eng/bm/' + id, 1500);
    if (!await until(p, `!!(${OBK_HEAD(word)})`)) return { err: 'no heading in time' };
    if (clickInfl) {        // the article view shows its table; a click only if a closed button is there
      await p.eval(`(() => { const h = ${OBK_HEAD(word)}; let c = h; for (let i = 0; i < 6; i++) c = c.parentElement;
        if (c.querySelector('table')) return 'shown';
        const b = [...c.querySelectorAll('button')].find(x => x.innerText.trim() === 'Inflection'); if (b) b.click(); return !!b; })()`);
      await sleep(900);
    }
    const m = await p.eval(OBK(word));
    await sleep(600);                                   // a pause between their pages
    return m;
  };
  const ours = async (id, w, phone) => {
    await p.size(w, phone ? 860 : 1000, !!phone);
    await p.goto(base + '/bm-en/' + id + '/', 300);
    await until(p, `!!document.querySelector('article.ordpar-card')`);
    await until(p, `!!document.querySelector('article.ordpar-card .ordpar-inflection-tables table')`, 3000);
    await p.frames();
    return p.eval(OURS);
  };
  // the cards: ours with the table open, as ordbokene's article view shows it
  await p.goto(base + '/', 100);
  await p.eval(`localStorage.clear(); localStorage.setItem('infl', 'open'); true`);
  const C = args.cards;
  for (const w of C.widths) out.cards.push({ w, phone: false, obk: await obk(C.id, C.word, w, false), ours: await ours(C.id, w, false) });
  for (const w of (C.phone || [])) out.cards.push({ w, phone: true, obk: await obk(C.id, C.word, w, true), ours: await ours(C.id, w, true) });
  for (const t of args.tables) for (const w of args.tableWidths) {
    out.tables.push({ id: t.id, word: t.word, w, obk: await obk(t.id, t.word, w, false, true), ours: await ours(t.id, w, false) });
  }
  await done({ base, obk: args.obk, ...out });
});
