// Site decisions 138 (2026-10-26): a later search always wins, and "Searching…" is shown at once.
//
// A search answered in place (a word page, `lookup.js` `answerInPlace` `go`; the search page,
// `search.html` `run`) first loads its query's index file and only then pushes its address and
// draws. Two searches made 50 ms apart, the first's index file not yet loaded and the second's
// already in, with every request delayed by args.latency ms (CDP `Network.emulateNetworkConditions`):
// the page must end on the SECOND. And from the first submit until the second is drawn, the results
// area shows the search page's "Searching…" line (`results.searching`, a `p.ordpar-empty`) and
// nothing of the previous answer.
//
// The second search is typed into the box (`how: 'box'`) or is a click on the start page's first
// similar headword (`how: 'similar'`). Since 138 that list is cleared at the first submit, so the
// link is read before it and, when it is gone by the click, an identical link is put into the page
// outside the results and clicked: the same document handler (`wireFragmentLinks`) answers it, so
// the second search goes the same way a click in time would have gone (`clicked`: 'live' or 'copy').
//
// args: { start (path), first, second (for 'box'), gap (ms), latency (ms), how, late (ms) }
// Result: { base, second, clicked, during: {n, bad: [...]}, drawnAfter (ms), end: {...}, text }
import { open, base, args, run, done, sleep } from './cdp.js';

const STATE = `(() => {
  const b = document.getElementById('ordpar-q'); let st = null; try { st = history.state; } catch (e) {}
  const r = document.querySelector('[data-ordpar-results]');
  const words = r ? Array.from(r.querySelectorAll('.ordpar-row-word')).map(w => {
    const c = w.cloneNode(true); c.querySelectorAll('.ordpar-visually-hidden, .ordbok-homograph').forEach(x => x.remove());
    return c.textContent.replace(/\\s+/g, ' ').trim(); }) : [];
  const kids = r ? Array.from(r.children) : [];
  const line = window.ordparShell && ordparShell.t ? ordparShell.t('results.searching') : 'Searching';
  return { box: b ? b.value : null, path: decodeURIComponent(location.pathname), hash: decodeURIComponent(location.hash),
    stq: st && st.q || null, title: document.title,
    miss: !!(r && r.querySelector('.ordpar-miss')), hits: r ? r.querySelectorAll('.ordpar-hits').length : 0,
    rows: r ? r.querySelectorAll('.ordpar-row, .ordpar-similar-list a, article').length : 0,
    words: words,
    onlySearching: kids.length === 1 && kids[0].matches('p.ordpar-empty') && kids[0].textContent.trim() === line,
    text: r ? (r.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 80) : '' }; })()`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  await p.send('Network.enable');
  await p.goto(base + args.start, 600);
  // the start page drawn — its own search answered, its similar words in — unthrottled
  let ready = false;
  for (let i = 0; i < 200 && !ready; i++) {
    ready = await p.eval(`!!window.ordparShell && !!document.querySelector('[data-ordpar-results] .ordpar-similar-list a')`);
    if (!ready) await sleep(100);
  }
  if (!ready) throw new Error('the start page ' + args.start + ' never drew its similar headwords');
  const link = await p.eval(`(() => { const a = document.querySelector('.ordpar-similar-list a');
    return { href: a.getAttribute('href'), text: (a.querySelector('.ordpar-option-word') || a).textContent.trim() }; })()`);   // 144: a row after a miss
  await p.send('Network.emulateNetworkConditions', { offline: false, latency: args.latency,
    downloadThroughput: -1, uploadThroughput: -1 });
  const submit = (q) => p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(q)};
    i.form.requestSubmit(); return true; })()`);

  const during = [];
  const t0 = Date.now();
  await submit(args.first);
  during.push(Object.assign({ t: Date.now() - t0 }, await p.eval(STATE)));   // at once after the submit
  await sleep(Math.max(0, (args.gap || 50) - (Date.now() - t0)));
  let second = args.second, clicked = null;
  if (args.how === 'similar') {
    second = link.text;
    clicked = await p.eval(`(() => {
      let a = Array.from(document.querySelectorAll('.ordpar-similar-list a')).find(x => x.getAttribute('href') === ${JSON.stringify(link.href)});
      let how = 'live';
      if (!a) { a = document.createElement('a'); a.setAttribute('href', ${JSON.stringify(link.href)});
        a.textContent = ${JSON.stringify(link.text)}; document.body.appendChild(a); how = 'copy'; }
      a.click(); return how; })()`);
  } else {
    await submit(second);
  }
  // until the second search is drawn: its entry pushed and its answer in
  let drawnAfter = null;
  while (Date.now() - t0 < 20000) {
    const s = await p.eval(STATE);
    if (s.stq === second && (s.hits || s.miss) && s.box === second) { drawnAfter = Date.now() - t0; break; }
    during.push(Object.assign({ t: Date.now() - t0 }, s));
    await sleep(15);
  }
  await sleep(args.late || 1500);            // time for a late answer of the first search
  const end = await p.eval(STATE);
  const bad = during.filter(s => !s.onlySearching || s.rows > 0);
  await done({ base, args, second, clicked, link, drawnAfter,
    during: { n: during.length, bad: bad.slice(0, 5), badCount: bad.length }, end });
});
