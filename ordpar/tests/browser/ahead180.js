// Site decisions 180 (Robin, 2026-11-09): everything that opens an article, a page or a search of
// this site loads ahead under `minifetch` — Random word, the similar headwords, word pages, the
// suggestions — and inside an open small article a nested link's article is fetched once.
//
// Every request the page makes is recorded through CDP (`Network.requestWillBeSent`; the harness's
// server sends `no-store`, so a request repeated is a request made again, never a cache hit), each
// case in a fresh context with real mouse moves (`Input.dispatchMouseEvent`), the pointer then left
// still before any click: at least `args.rest` ms, and then until what the case expects has been
// requested and every request of the site's has been answered, `args.ceiling` ms at most (`rested`).
// A fixed rest failed the live check of 2026-11-11 on timing: under its parallel load Random word's
// article was not yet requested at 700 ms (site decisions 180). Where a case expects NOTHING
// (`click`), the rest stays the fixed one. `args.latency` slows every request, to show the wait works.
//
//   random      the search page (`/bm-en/`), `Math.random` set so the draw falls on args.word: the
//               pointer rests on Random word; the requests before the click, the pending draw
//               (`button.ordparDraw`); then the click: the word it opens and the requests after it
//   similar     the search for args.similarFrom answered on the search page: the pointer rests on a
//               similar headword whose link is its word page (`/bm-en/<w>/#q=<w>`): the searches
//               looked up during the rest (`ordparLookup.lookup` wrapped first; its index files may
//               already be in memory) and the requests (not the word page's HTML, which this page
//               will not navigate to)
//   more        an article page (args.moreFrom) and its "more entries" link to a word page
//               (`/bm-en/<w>/`): the requests during the rest (the word page itself)
//   suggestion  the History page (it navigates), args.word typed: the pointer rests on the first
//               suggestion row: the requests during the rest
//   click       the random case under `minifetch = click`: nothing requested before the click
//   nested      an article page (args.nest.from), its link to args.nest.mid clicked (a small
//               article opens), then the pointer rests on the box's link to args.nest.inner: how
//               often `/bm-en/<inner>/` is requested
//
// Result: { base, cases: { <name>: {...} } }
import { open, base, args, run, done, sleep } from './cdp.js';

const REST = args.rest || 700;
const CEILING = args.ceiling || 15000;

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) { try { if (await p.eval(expr)) return true; } catch (e) { /* navigating */ } await sleep(100); }
  return false;
}

async function fresh(settings = {}) {
  const p = await open({ w: 1280, h: 900 });
  const reqs = [];
  reqs.flying = new Set();   // the site's requests not yet answered
  p.on(m => {
    if (m.method === 'Network.requestWillBeSent') {
      const u = new URL(m.params.request.url);
      if (u.origin === new URL(base).origin) { reqs.push(decodeURIComponent(u.pathname)); reqs.flying.add(m.params.requestId); }
    } else if (m.method === 'Network.loadingFinished' || m.method === 'Network.loadingFailed') {
      reqs.flying.delete(m.params.requestId);
    }
  });
  await p.send('Network.enable', {});
  await p.goto(base + '/bm-en/', 400);
  await p.eval(`localStorage.clear(); sessionStorage.clear();
    ${Object.entries(settings).map(([k, v]) => `localStorage.setItem(${JSON.stringify(k)}, ${JSON.stringify(v)});`).join(' ')} true`);
  return { p, reqs };
}

/** The centre of the element `sel` (scrolled into view), or null. */
async function at(p, sel) {
  return p.eval(`(() => { const b = ${sel}; if (!b || !b.getClientRects().length) return null;
    b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect();
    return { x: Math.round(r.left + Math.min(r.width / 2, 20)), y: Math.round(r.top + r.height / 2) }; })()`);
}
async function moveTo(p, pt) {
  // `args.latency` (ms): every request from here on answered that much later, a slow connection
  // or a loaded machine made on purpose (the timing failure of 2026-11-11's live check)
  if (args.latency) await p.send('Network.emulateNetworkConditions', { offline: false, latency: args.latency, downloadThroughput: -1, uploadThroughput: -1 });
  await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 2, y: 2 });
  await sleep(50);
  await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pt.x, y: pt.y });
}
async function press(p, pt) {
  await p.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: pt.x, y: pt.y, button: 'left', clickCount: 1 });
  await p.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: pt.x, y: pt.y, button: 'left', clickCount: 1 });
}
/** The pointer left still: REST ms, then until `got()` holds (what the case expects to have been
    requested; may be async) and no request of the site's is unanswered, twice running, CEILING ms
    at most. The ms waited. With no `got`, the fixed rest alone (a case that expects nothing). */
async function rested(reqs, got) {
  await sleep(REST);
  if (!got) return REST;
  let t = REST, calm = 0;
  for (; t < CEILING && calm < 2; t += 100) {
    calm = (await got()) && !reqs.flying.size ? calm + 1 : 0;
    if (calm < 2) await sleep(100);
  }
  return t;
}
const index = l => l.filter(u => u.indexOf('/index/') === 0);
const pages = l => l.filter(u => /^\/bm-en\/[^/]+\/$/.test(u));

const SETTLED = `document.readyState === 'complete' && !!document.querySelector('[data-ordpar-results] .ordpar-hits')
  && !document.querySelector('.ordpar-result[aria-busy="true"]') && !document.querySelector('[data-ordpar-results] .is-pending')`;

async function randomCase(settings) {
  const { p, reqs } = await fresh(settings);
  await p.goto(base + '/bm-en/', 800);
  const i = await p.eval(`fetch('/index/random.json').then(r => r.json()).then(l => {
    const i = l.indexOf(${JSON.stringify(args.word)}); if (i < 0) return -1;
    Math.random = () => (i + 0.5) / l.length; return i; })`);
  if (i < 0) { await p.close(); return { error: args.word + ' is not in random.json' }; }
  await sleep(300);
  reqs.length = 0;
  const pt = await at(p, `document.querySelector('[data-ordpar-random]')`);
  if (!pt) { await p.close(); return { error: 'no Random word button' }; }
  await moveTo(p, pt);
  const waited = await rested(reqs, settings.minifetch === 'click' ? null
    : () => pages(reqs).length && index(reqs).some(u => u !== '/index/random.json'));
  const before = reqs.slice();
  const pending = await p.eval(`(() => { const b = document.querySelector('[data-ordpar-random]');
    return b.ordparDraw && b.ordparDraw.word ? Promise.resolve(b.ordparDraw.word) : null; })()`);
  reqs.length = 0;
  await press(p, pt);
  await until(p, `${SETTLED} && (document.getElementById('ordpar-q') || {}).value === ${JSON.stringify(args.word)}`);
  await sleep(600);
  const after = reqs.slice();
  const landed = await p.eval(`(document.getElementById('ordpar-q') || {}).value || null`);
  const full = await p.eval(`document.querySelectorAll('[data-ordpar-results] .ordpar-hits .ordpar-result').length`);
  await p.close();
  return { before, pending, after, landed, full, waited };
}

const CASES = {
  random: () => randomCase({}),
  click: () => randomCase({ minifetch: 'click' }),

  async similar() {
    const { p, reqs } = await fresh();
    await p.goto(base + '/bm-en/#q=' + encodeURIComponent(args.similarFrom), 800);
    await until(p, SETTLED);
    await until(p, `!!document.querySelector('.ordpar-similar a[href*="#q="]')`);
    await sleep(800);
    const link = await p.eval(`(() => { const a = [...document.querySelectorAll('.ordpar-similar a[href*="#q="]')]
      .filter(a => /^\\/bm-en\\/[^\\/0-9#][^\\/#]*\\/#q=/.test(a.getAttribute('href')))[0];
      if (!a) return null; a.setAttribute('data-test-similar', ''); return a.getAttribute('href'); })()`);
    if (!link) { await p.close(); return { error: 'no similar headword with a word page' }; }
    // the searches looked up from here on (its index files may already be in memory: a similar
    // headword often reads the shard the search itself read)
    await p.eval(`(() => { window.__looked = []; const L = window.ordparLookup, f = L.lookup;
      L.lookup = function (q) { window.__looked.push(q); return f.apply(this, arguments); }; return true; })()`);
    reqs.length = 0;
    const pt = await at(p, `document.querySelector('[data-test-similar]')`);
    await moveTo(p, pt);
    const word = decodeURIComponent(link).split('#q=')[1];
    const waited = await rested(reqs, () => p.eval(`window.__looked.indexOf(${JSON.stringify(word)}) >= 0`));
    const before = reqs.slice();
    const looked = await p.eval(`window.__looked.slice()`);
    await p.close();
    return { link: decodeURIComponent(link), before, looked, waited };
  },

  async more() {
    const { p, reqs } = await fresh();
    await p.goto(base + '/bm-en/' + args.moreFrom + '/', 800);
    const href = await p.eval(`(() => { const a = [...document.querySelectorAll('a[href]')]
      .filter(a => /^\\/bm-en\\/[^\\/0-9#][^\\/#]*\\/$/.test(a.getAttribute('href')))[0];
      if (!a) return null; a.setAttribute('data-test-more', ''); return a.getAttribute('href'); })()`);
    if (!href) { await p.close(); return { error: 'no word-page link on ' + args.moreFrom }; }
    reqs.length = 0;
    const pt = await at(p, `document.querySelector('[data-test-more]')`);
    await moveTo(p, pt);
    const waited = await rested(reqs, () => reqs.includes(decodeURIComponent(href)));
    const before = reqs.slice();
    await p.close();
    return { link: decodeURIComponent(href), before, waited };
  },

  async suggestion() {
    const { p, reqs } = await fresh();
    await p.goto(base + '/history/', 800);
    await p.eval(`(() => { const b = document.getElementById('ordpar-q'); b.focus(); b.value = ${JSON.stringify(args.word)};
      b.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
    if (!await until(p, `[...document.querySelectorAll('.ordpar-option')].some(o => o.getClientRects().length)`, 8000)) {
      await p.close(); return { error: 'no suggestions' };
    }
    await sleep(500);
    reqs.length = 0;
    const pt = await at(p, `document.querySelector('.ordpar-option')`);
    await moveTo(p, pt);
    const waited = await rested(reqs, () => reqs.includes('/bm-en/' + args.word + '/'));
    const before = reqs.slice();
    const row = await p.eval(`document.querySelector('.ordpar-option').textContent`);
    await p.close();
    return { row, before, waited };
  },

  async nested() {
    const n = args.nest;
    const { p, reqs } = await fresh();
    await p.goto(base + '/bm-en/' + n.from + '/', 800);
    const link = `[...document.querySelectorAll('.ordbok-xref > a.ordbok-xword')].filter(a => !a.closest('.ordbok-xmini')
      && (a.getAttribute('href') || '').indexOf('/bm-en/${n.mid}/') === 0 && a.getClientRects().length)[0]`;
    const pt = await at(p, link);
    if (!pt) { await p.close(); return { error: 'no link to ' + n.mid }; }
    await moveTo(p, pt); await sleep(100); await press(p, pt);
    if (!await until(p, `!!document.querySelector('.ordbok-xmini .ordpar-mbody')`, 8000)) { await p.close(); return { error: 'no small article opened' }; }
    await sleep(500);
    const inner = `[...document.querySelectorAll('.ordbok-xmini .ordbok-xref > a.ordbok-xword')].filter(a =>
      (a.getAttribute('href') || '').indexOf('/bm-en/${n.inner}/') === 0 && a.getClientRects().length)[0]`;
    const pt2 = await p.eval(`(() => { const a = ${inner}; if (!a) return null; const r = a.getClientRects()[0];
      return { x: Math.round(r.left + Math.min(r.width / 2, 12)), y: Math.round(r.top + r.height / 2) }; })()`);
    if (!pt2) { await p.close(); return { error: 'no link to ' + n.inner + ' in the small article' }; }
    reqs.length = 0;
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pt2.x, y: pt2.y });
    await rested(reqs, () => reqs.includes('/bm-en/' + n.inner + '/'));
    await sleep(REST + 500);   // a second request of it, if one is made, comes in this time
    const during = reqs.slice();
    await p.close();
    return { during, count: during.filter(u => u === '/bm-en/' + n.inner + '/').length };
  },
};

run(async () => {
  const cases = {};
  for (const name of args.cases || Object.keys(CASES)) {
    try { cases[name] = await CASES[name](); } catch (e) { cases[name] = { error: String(e && e.message || e) }; }
  }
  // the helpers' views, for the Python side's messages
  for (const c of Object.values(cases)) {
    if (c.before) { c.beforeIndex = index(c.before); c.beforePages = pages(c.before); }
    if (c.after) { c.afterIndex = index(c.after); c.afterPages = pages(c.after); }
  }
  await done({ base, cases });
});
