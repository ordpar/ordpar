// Decisions 129 (2026-10-25): a search that finds one translated article keeps its History entry
// when the page is left before the article arrives (a slow connection).
//
// In one fresh context, with every request delayed by args.latency ms (CDP
// `Network.emulateNetworkConditions`): the search page opened at `/bm-en/#q=<args.word>` (a first
// load from #q= is a search the reader made, so it is recorded; since site decisions 117 it is
// sent on to the word's own page, `/bm-en/<word>/#q=<word>`, which records it as the search page
// did, and the page is left from there). A script put into every page
// before its own (`Page.addScriptToEvaluateOnNewDocument`) watches the search page and, the moment
// the results heading (`.ordpar-hits`) is drawn, notes what it sees (how many articles, whether
// they are still loading, what History holds) in sessionStorage and leaves by a full navigation to
// `/history/` — in the page itself, with no round trip to this script between the two. Then, on
// the History page (still throttled): what History holds, and the row's right-hand text once it
// has filled (a row stored without its gloss is drawn from the index, shell.js `needsFill`).
// Every wait is for a condition, never a fixed delay.
//
// args: { word, latency }
// Result: { base, atLeave: {path, articles, busy, history}, landed, history: [{q, n, text, t}],
//           row: {text, pending} | null }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 20000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// runs in every document before the page's own scripts; acts on the search page only, once
const LEAVE = `(() => {
  // the search page, or (site decisions 117) the word's own page the search is sent to
  if (!/^\\/bm-en\\/(?:[^\\/0-9][^\\/]*\\/)?$/.test(location.pathname) || sessionStorage.getItem('h129')) return;
  const look = () => {
    // a word page's built rows (its headline still there) are not the search's results
    if (!document.querySelector('[data-ordpar-results] .ordpar-hits')
        || document.querySelector('[data-ordpar-results] .ordpar-word-title')) return false;
    let hist = [];
    try { hist = JSON.parse(localStorage.getItem('history') || '[]').map(e => e.q); } catch (e) { hist = ['?']; }
    sessionStorage.setItem('h129', JSON.stringify({ path: location.pathname,
      articles: document.querySelectorAll('.ordpar-result, .ordpar-row-button').length,
      busy: document.querySelectorAll('.ordpar-result[aria-busy="true"]').length,
      history: hist }));
    location.href = '/history/';
    return true;
  };
  const watch = new MutationObserver(() => { if (look()) watch.disconnect(); });
  watch.observe(document, { childList: true, subtree: true });
})();`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  await p.send('Network.enable');
  await p.send('Network.emulateNetworkConditions', { offline: false, latency: args.latency,
    downloadThroughput: -1, uploadThroughput: -1 });
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: LEAVE });

  await p.send('Page.navigate', { url: base + '/bm-en/#q=' + encodeURIComponent(args.word) });
  // the History page reached (by the script's navigation), its rows drawn
  const landed = await until(p, `location.pathname === '/history/' && !!sessionStorage.getItem('h129')
    && document.readyState === 'complete'`, 60000);
  const atLeave = JSON.parse(await p.eval(`sessionStorage.getItem('h129') || 'null'`));
  const history = await p.eval(`JSON.parse(localStorage.getItem('history') || '[]')
    .map(e => ({ q: e.q, n: e.n, text: e.text, t: e.t }))`);
  let row = null;
  if (history.some(e => e.q === args.word)) {
    const sel = `[...document.querySelectorAll('.ordpar-history-link')]
      .find(a => (a.getAttribute('href') || '').indexOf(${JSON.stringify(encodeURIComponent(args.word))}) >= 0)`;
    await until(p, `(() => { const a = ${sel}; const g = a && a.querySelector('.ordpar-option-gloss');
      return !!g && !g.classList.contains('is-pending') && g.textContent.trim().length > 0; })()`, 30000);
    row = await p.eval(`(() => { const a = ${sel}; if (!a) return null;
      const g = a.querySelector('.ordpar-option-gloss');
      return { text: g ? g.textContent.trim() : '', pending: !!g && g.classList.contains('is-pending') }; })()`);
  }
  await done({ base, atLeave, landed, history, row });
});
