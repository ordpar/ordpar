// Site decisions 166 (Robin, 2026-11-05, "Yes, as proposed"): the address that opens an article's
// "Suggest a correction" form on arrival, for the deck's link on every card — `/bm-en/<id>/#report`
// (`report.js` `ADDRESS_KEY`, `fromAddress`, called by the article page's script once its foot row
// is in the page).
//
// The switch (`report.js` `REPORT_RECEIVER`) is set before the page's scripts run, as
// `report166.js` does (a setter on `window.ordparReport`): to a dead local address, so whatever
// the build carries nothing can reach a real receiver — and nothing is sent here anyway. For the
// case without a button it is set empty.
//
//   off      — the switch empty, `/bm-en/<id>/#report`: no button, no form, the page as normal,
//              the address untouched;
//   opened   — the switch on, `/bm-en/<id>/#report`: the form open under the foot's row, the button
//              `aria-expanded`, focus in the text box (inside the window), the key off the address
//              (no fragment left), the history entry not added to;
//   reloaded — that page reloaded: the form not opened again;
//   back     — another page, then Back: the address still without the key;
//   settings — `/bm-en/<id>/#theme=<the other>&defs=en&report` (146's settings and the key; the
//              theme the one the system does not show): the form open, the settings applied (that
//              theme, the English definitions alone) and kept as the
//              tab's visit, the address with neither;
//   keyFirst — `/bm-en/<id>/#report&mini=en`: the same, the key first;
//   search   — `/bm-en/<id>/#q=<word>&report`: the form open, `#q=<word>` left in the address;
//   searchPage — the search page `/bm-en/#q=<word>&report`: the search still answers (the word's
//              page, its article), no form opened there;
//   wordPage — `/bm-en/<word>/#report`: no form opened (the article page only), the article shown.
//
// args: { id, word, dead }
import { open, base, args, run, done, sleep } from './cdp.js';

const SET = (addr) => `(() => { let r; Object.defineProperty(window, 'ordparReport', { configurable: true,
  get() { return r; }, set(v) { if (v) v.REPORT_RECEIVER = ${JSON.stringify(addr)}; r = v; } }); })();`;

const STATE = `(() => {
  const foot = document.querySelector('.ordpar-card-foot');
  const b = document.querySelector('.ordpar-report-btn');
  const f = b && document.getElementById(b.getAttribute('aria-controls') || '-');
  const ta = f && f.querySelector('textarea');
  const a = document.activeElement, r = ta ? ta.getBoundingClientRect() : null;
  const visit = (() => { try { return sessionStorage.getItem('ordpar-visit'); } catch (e) { return 'refused'; } })();
  return {
    path: location.pathname, hash: location.hash, search: location.search,
    history: history.length, state: history.state,
    footRow: !!(foot && foot.querySelector('.ordpar-result-controls')),
    button: !!b, buttons: document.querySelectorAll('.ordpar-report-btn').length,
    expanded: b ? b.getAttribute('aria-expanded') : null,
    forms: document.querySelectorAll('form.ordpar-report').length,
    open: !!f && !f.hidden && f.getBoundingClientRect().height > 0,
    afterRow: !!f && f.previousElementSibling === b.parentNode,
    focus: a === ta && !!ta ? 'text' : a === b && !!b ? 'button' : a ? a.tagName.toLowerCase() : null,
    textInView: !!r && r.top >= 0 && r.bottom <= innerHeight,
    night: document.documentElement.classList.contains('nightMode'),
    defsEn: document.documentElement.classList.contains('ordpar-defs-en'),
    miniEn: document.documentElement.classList.contains('ordpar-mini-en'),
    visit,
    articles: document.querySelectorAll('.ordpar-article').length,
  };
})()`;

async function until(p, expr, ms = 10000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

run(async () => {
  const p = await open({ w: 1280, h: 800 });
  const out = { base };
  const art = base + '/bm-en/' + args.id + '/';
  // each case from a fresh page in the same tab, the tab's visit and saved settings cleared first
  const fresh = async (url, settle = 800) => {
    await p.goto(base + '/about/', 200);
    await p.eval(`(() => { try { sessionStorage.clear(); localStorage.clear(); } catch (e) {} return true; })()`);
    await p.goto(url, settle);
  };

  // off: no button, nothing happens, the address untouched
  let s = await p.send('Page.addScriptToEvaluateOnNewDocument', { source: SET('') });
  await fresh(art + '#report');
  out.off = await p.eval(STATE);
  await p.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: s.identifier });

  // the switch on (a dead local address) from here
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: SET(args.dead) });

  // the plain address: the form open, the key gone, no entry added
  await fresh(art);
  const plainHistory = await p.eval('history.length');
  await fresh(art + '#report');
  out.opened = await p.eval(STATE);
  out.opened.historyBefore = plainHistory;

  // reloaded: not opened again
  await p.reload(800);
  out.reloaded = await p.eval(STATE);

  // another page, then Back: the address still without the key
  await p.goto(base + '/about/', 300);
  const backLoaded = p.waitEvent('Page.loadEventFired', 5000);
  await p.send('Runtime.evaluate', { expression: 'history.back()' });
  await backLoaded;
  await until(p, `location.pathname === ${JSON.stringify('/bm-en/' + args.id + '/')}`);
  await sleep(500);
  out.back = await p.eval(STATE);

  // 146's settings beside the key
  out.systemDark = await p.eval(`matchMedia('(prefers-color-scheme: dark)').matches`);
  out.theme = out.systemDark ? 'light' : 'dark';
  await fresh(art + '#theme=' + out.theme + '&defs=en&report');
  out.settings = await p.eval(STATE);
  await fresh(art + '#report&mini=en');
  out.keyFirst = await p.eval(STATE);

  // a search beside the key, on the article page
  await fresh(art + '#q=' + encodeURIComponent(args.word) + '&report');
  out.search = await p.eval(STATE);

  // the search page with the key: the search still answers, no form
  await fresh(base + '/bm-en/#q=' + encodeURIComponent(args.word) + '&report', 300);
  await until(p, `!!document.querySelector('.ordpar-article')`, 15000);
  await sleep(500);
  out.searchPage = await p.eval(STATE);

  // a word page with the key: the article page only, so no form
  await fresh(base + '/bm-en/' + encodeURIComponent(args.word) + '/#report', 300);
  await until(p, `!!document.querySelector('.ordpar-report-btn')`, 15000);
  await sleep(500);
  out.wordPage = await p.eval(STATE);

  await done(out);
});
