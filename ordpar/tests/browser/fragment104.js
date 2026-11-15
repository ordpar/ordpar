// Decisions 104 (2026-10-23): the search lives in the address's fragment (`/bm-en/#q=…`), which
// a browser never sends, so no request the page makes carries the reader's search in its query
// string (nor in a Referer).
//
// In one fresh context, with every request the page makes recorded (`Network.requestWillBeSent`:
// its URL and its Referer):
//   0. the same, with the article page's own script blocked, so the head script's guard must take
//      the form (args.early): to #q=, never the form's own GET to ?q=;
//   1. an article page (args.article); the header's search box gets args.typed and is submitted
//      (Enter, `requestSubmit`) — since site decisions 117 that word's own page answers it
//      (`/bm-en/<typed>/`, a word page);
//   2. a search that finds nothing (args.miss) made in that word page's own box, answered in
//      place (lookup.js `answerInPlace`, as the search page answers its own box); the first of
//      its similar words is clicked — answered in place too, and recorded in History; then Back
//      (the miss again) and Forward (the word again);
//   3. the History page; its first row is clicked — its word's page (or the search page) answers it.
// Then, apart from those: an old address with the search in its query (`/bm-en/?q=` + args.old)
// still answers, and the address is rewritten to `#q=` with no new history entry.
//
// Every read waits for the state it means to read, never a fixed pause (2026-10-26). A search
// answered in place first loads its query's index file and only then pushes its address and draws
// (`answerInPlace` `go`: `address` -> `pushState` -> `render`); until then the box already holds
// the new word while the previous answer — hits and similar words — still stands. So a step made
// in place is read once the history entry's state names its query (`answered`), which is pushed
// in the same moment the old answer is cleared; reading the box alone let the miss's step pass on
// *lys*'s answer, and the click on "the first similar word" then met either lys's list or none
// (the failures on ordpar.no after the deploys of 2026-10-26: "Cannot read properties of null").
//
// args: { article, early, typed, miss, old }
// Result: { requests: n, leaks: [{url, referer}], steps: {name: {href, search, hash, shown}}, ... }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// what the search page shows: the query in its box, and whether results (or a miss) are drawn
const SHOWN = `(() => { const b = document.getElementById('ordpar-q');
  return { box: b ? b.value : null,
    hits: document.querySelectorAll('.ordpar-result, .ordpar-row-button').length,
    miss: !!document.querySelector('.ordpar-miss'),
    similar: document.querySelectorAll('.ordpar-similar-list a').length }; })()`;
const WHERE = `({ href: location.href, path: location.pathname, search: location.search, hash: location.hash,
  length: history.length })`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const log = [];
  p.on(m => {
    if (m.method !== 'Network.requestWillBeSent') return;
    const r = m.params.request;
    log.push({ url: r.url, referer: (r.headers && (r.headers.Referer || r.headers.referer)) || '' });
  });
  await p.send('Network.enable');
  const steps = {};
  const results = (q) => until(p, `(() => { const b = document.getElementById('ordpar-q');
    return !!b && b.value === ${JSON.stringify(q)}
      && !!document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-miss'); })()`);
  // a search answered in place (step 2's): its own entry pushed — the state names q, set in the
  // same moment the previous answer is cleared — and its answer drawn; `more` an extra condition
  const answered = (q, more = 'true', ms = 10000) => until(p, `(() => { let st = null; try { st = history.state; } catch (e) {}
    const b = document.getElementById('ordpar-q');
    return !!st && st.q === ${JSON.stringify(q)} && !!b && b.value === ${JSON.stringify(q)}
      && !!document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-miss')
      && (${more}); })()`, ms);
  const step = async (name) => { steps[name] = Object.assign(await p.eval(WHERE), { shown: await p.eval(SHOWN) }); };

  // 0. the header's search submitted before the page's own script has taken the form (here: the
  //    article page's script blocked): the head script sends it to #q=, never the form's GET
  await p.send('Network.setBlockedURLs', { urls: ['*/site/ordpar.js*'] });
  await p.goto(base + '/bm-en/' + args.article + '/', 400);
  steps.earlyShell = await p.eval('!!window.ordparShell');
  let loaded = p.waitEvent('Page.loadEventFired', 10000);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(args.early)};
    i.form.requestSubmit(); return true; })()`);
  await loaded;
  await p.send('Network.setBlockedURLs', { urls: [] });
  steps.earlyFound = await results(args.early);
  await step('early');

  // 1. from an article page: the header's search box, submitted
  await p.goto(base + '/bm-en/' + args.article + '/', 600);
  await until(p, `!!window.ordparShell && document.getElementById('ordpar-q').getAttribute('role') === 'combobox'`);
  loaded = p.waitEvent('Page.loadEventFired', 10000);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(args.typed)};
    i.form.requestSubmit(); return true; })()`);
  await loaded;
  steps.typedFound = await results(args.typed);
  await step('typed');

  // 2. a miss made in the word page's own box (answered in place), then a similar word clicked:
  //    read once the miss's own entry is pushed and its own similar words are in — they come after
  //    the miss is drawn, over the network a file or four later (20 s: a cold index file on
  //    ordpar.no has taken 5 s)
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(args.miss)};
    i.form.requestSubmit(); return true; })()`);
  steps.missFound = await answered(args.miss,
    `!!document.querySelector('.ordpar-miss') && document.querySelectorAll('.ordpar-similar-list a').length > 0`, 20000);
  await step('miss');
  // site decisions 144: after a miss each similar word is a row; its word is the row's `.ordpar-option-word`
  const word = await p.eval(`(() => { const a = document.querySelector('.ordpar-similar-list a'); if (!a) return '';
    return (a.querySelector('.ordpar-option-word') || a).textContent; })()`);
  steps.word = word;
  await p.eval(`(() => { const a = document.querySelector('.ordpar-similar-list a'); if (a) { a.click(); } return !!a; })()`);
  steps.wordFound = !!word && await answered(word);
  await step('similar');
  // wait for the write itself (up to 15 s), never a fixed delay: until decisions 129 (2026-10-25) a
  // one-article search wrote its entry only once the article had been fetched, and the live run of
  // 2026-10-25 read History 400 ms after the heading, before the article had come over the network;
  // since 129 the entry is written at once and filled later, and the wait still holds
  steps.similarRecorded = await until(p, `JSON.parse(localStorage.getItem('history') || '[]')
    .some(e => e.q === ${JSON.stringify(word)})`, 15000);
  steps.historyAfterSimilar = await p.eval(`JSON.parse(localStorage.getItem('history') || '[]').map(e => e.q)`);
  await p.eval(`history.back(); true`);
  steps.backFound = await answered(args.miss);
  await step('back');
  await p.eval(`history.forward(); true`);
  steps.forwardFound = !!word && await answered(word);
  await step('forward');

  // 3. a History row
  await p.goto(base + '/history/', 600);
  await until(p, `!!document.querySelector('.ordpar-history-link')`);
  const row = await p.eval(`(() => { const a = document.querySelector('.ordpar-history-link');
    return { href: a.getAttribute('href'), text: a.textContent }; })()`);
  steps.historyRow = row;
  loaded = p.waitEvent('Page.loadEventFired', 10000);
  await p.eval(`(() => { document.querySelector('.ordpar-history-link').click(); return true; })()`);
  await loaded;
  // the row's search, from its own link (`/bm-en/#q=<word>`), not the box read after a pause: the
  // search page may still be passing the search on to the word's page (`location.replace`)
  let rowQ = '';
  try { rowQ = decodeURIComponent(((/#q=([^&]*)/.exec(row.href) || [])[1] || '').replace(/\+/g, ' ')).trim(); } catch (e) { rowQ = ''; }
  steps.historyFound = !!rowQ && await results(rowQ);
  await step('history');

  // every request so far: none carries a search in its query string or its Referer
  const queries = [args.early, args.typed, args.miss, word, rowQ].filter(Boolean);
  const enc = (s) => [s, encodeURIComponent(s)];
  const leaks = log.filter(r => {
    let u; try { u = new URL(r.url); } catch (e) { return false; }
    if (!/^https?:/.test(u.protocol)) return false;
    let ref = '';
    try { ref = r.referer ? new URL(r.referer).search : ''; } catch (e) { ref = ''; }
    const where = u.search + ' ' + ref;
    return /[?&]q=/.test(where) || queries.some(q => enc(q).some(s => where.indexOf(s) >= 0));
  });
  const requests = log.length;

  // an old address with the search in its query: still answered, then rewritten in place
  const lengthBefore = await p.eval('history.length');
  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.old), 600);
  steps.oldFound = await results(args.old);
  await step('old');
  steps.oldAddedEntries = steps.old.length - lengthBefore;

  await done({ base, requests, leaks: leaks.slice(0, 20), leakCount: leaks.length, steps,
    sample: log.slice(0, 5).map(r => r.url) });
});
