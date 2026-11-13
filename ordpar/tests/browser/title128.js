// Decisions 128 (2026-10-25): one style for every page title. A search that lifts ONE article in
// full sets the search page's title to that article page's own <title> ("abstrakt (adjective) —
// Norwegian–English dictionary"); a search showing several articles keeps the query's title.
//
// For each query in args.cases ({q}): the search page opened at `/bm-en/#q=<q>` in a fresh
// context, waited for until its articles have arrived (no `.ordpar-result[aria-busy]` left) and
// the title has settled; then the page's title, the number of lifted articles, and the first
// lifted article's id and its page's own <title>, fetched as the search page fetches it.
// Every wait is for a condition, never a fixed delay (the title is read once it stops changing).
//
// args: { cases: [{q}] }
// Result: { base, rows: [{q, title, articles, rows, id, pageTitle}] } (`rows`: list-view rows,
// the default view of a search with several hits)
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 20000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

run(async () => {
  const out = [];
  for (const c of args.cases) {
    const p = await open({ w: 1280, h: 900 });
    await p.send('Page.navigate', { url: base + '/bm-en/#q=' + encodeURIComponent(c.q) });
    await until(p, `document.readyState === 'complete'
      && document.querySelectorAll('[data-ordpar-results] .ordpar-result, [data-ordpar-results] .ordpar-row').length > 0
      && !document.querySelector('.ordpar-result[aria-busy="true"]')`, 30000);
    // the title is set once every lifted article has come: wait until it holds for 1 s
    let last = null, same = 0;
    for (let t = 0; t < 100 && same < 10; t++) {
      const now = await p.eval('document.title');
      same = now === last ? same + 1 : 0;
      last = now;
      await sleep(100);
    }
    const articles = await p.eval(`document.querySelectorAll('[data-ordpar-results] .ordpar-result').length`);
    const rows = await p.eval(`document.querySelectorAll('[data-ordpar-results] .ordpar-row').length`);
    // the first lifted article's own page, fetched as the search page fetches it
    const id = await p.eval(`(document.querySelector('[data-ordpar-results] .ordpar-result') || {}).getAttribute
      ? document.querySelector('[data-ordpar-results] .ordpar-result').getAttribute('data-id') : null`);
    let pageTitle = null;
    if (id) {
      pageTitle = await p.eval(`fetch('/bm-en/${id}/').then(r => r.text()).then(t => {
        const d = document.createElement('textarea');
        d.innerHTML = (/<title>([\\s\\S]*?)<\\/title>/.exec(t) || [, ''])[1];
        return d.value; })`);
    }
    out.push({ q: c.q, title: last, articles, rows, id, pageTitle });
    await p.close();
  }
  await done({ base, rows: out });
});
