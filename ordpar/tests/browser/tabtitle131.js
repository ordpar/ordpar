// Site-review decisions 131 (117's one style for the tab's title): a search answered in place whose
// address is its own word or form page shows that page's built title ("så — Norwegian–English
// dictionary"; one article: the article's own title), while a search with no page of its own keeps
// "q — Ordpar".
//
// For each start page in args.starts (the search page, a word page, the 404 shell), in a fresh
// context: the page opened, then each of args.queries searched in place (`ordparShell.search`, the
// header box's way), each read once its address is pushed (the history state names q) and its
// answer is drawn (the built word page's headline gone, a result, a form row or the miss shown)
// and the title has held for 1 s: the title and the address.
// Then args.sample ({q, title}: built word and form pages and their <title>s) searched in place on
// the search page, each title compared by the caller; and args.direct ({path}) opened directly, the
// title read once settled (a `#q=` search, a word page loaded).
//
// args: { starts: [path], queries: [q], sample: [{q, title}], direct: [path], listview?: 'on' }
// Result: { base, inplace: [{start, q, title, path}], sample: [{q, want, title, path}], direct: [{path, title}] }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 20000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// The address first: a search loads its shard (`lookup.address`), then pushes its address with
// the state {q} and only then draws (clearing the last answer). Until then the box already holds
// q while the last search's answer and title still stand, so without this the wait could pass on
// them (seen on ordpar.no, 2026-10-26: the previous search's title read).
const ANSWERED = (q) => `!!history.state && String(history.state.q || '').trim().toLowerCase() === ${JSON.stringify(q.toLowerCase())}
  && !document.querySelector('.ordpar-word-title')
  && (document.getElementById('ordpar-q') || {}).value === ${JSON.stringify(q)}
  && !!document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-inflected, [data-ordpar-results] .ordpar-miss')
  && !document.querySelector('.ordpar-result[aria-busy="true"]')`;

async function settled(p) {
  let last = null, same = 0;
  for (let t = 0; t < 120 && same < 10; t++) {
    const now = await p.eval('document.title');
    same = now === last ? same + 1 : 0;
    last = now;
    await sleep(100);
  }
  return last;
}

async function search(p, q) {
  // the box emptied first, so the wait sees this search's answer, not the last one's
  await p.eval(`(() => { const b = document.getElementById('ordpar-q'); if (b) b.value = ''; ordparShell.search(${JSON.stringify(q)}); return true; })()`);
  await until(p, ANSWERED(q));
  return { title: await settled(p), path: decodeURIComponent(await p.eval('location.pathname')) };
}

run(async () => {
  const inplace = [], sample = [], direct = [];
  for (const start of args.starts || []) {
    const p = await open({ w: 1280, h: 900 });
    await p.goto(base + '/', 200);
    await p.eval(`localStorage.clear(); ${args.listview ? `localStorage.setItem('listview', ${JSON.stringify(args.listview)});` : ''} true`);
    await p.goto(base + start, 600);
    await until(p, `!!window.ordparShell && !!ordparShell.ready && !document.querySelector('.ordpar-word-title')`);
    await sleep(500);
    for (const q of args.queries || []) {
      const r = await search(p, q);
      inplace.push({ start, q, title: r.title, path: r.path });
    }
    await p.close();
  }
  if ((args.sample || []).length) {
    const p = await open({ w: 1280, h: 900 });
    await p.goto(base + '/bm-en/', 600);
    await until(p, `!!window.ordparShell && !!ordparShell.ready`);
    for (const s of args.sample) {
      const r = await search(p, s.q);
      sample.push({ q: s.q, want: s.title, title: r.title, path: r.path });
    }
    await p.close();
  }
  for (const path of args.direct || []) {
    const p = await open({ w: 1280, h: 900 });
    await p.goto(base + path, 600);
    await until(p, `!document.querySelector('.ordpar-word-title') && !!document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-inflected, [data-ordpar-results] .ordpar-miss')`);
    direct.push({ path, title: await settled(p) });
    await p.close();
  }
  await done({ base, inplace, sample, direct });
});
