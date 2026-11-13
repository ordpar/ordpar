// Decisions 115, last paragraph (Robin, 2026-10-24): "A random word is not a search, and it does
// not go into history". Random word still opens the drawn headword's search page, but the draw is
// neither recorded in History nor sent as a search event.
//
// For one viewport (args.mobile: a phone, the button tapped; else a computer, clicked), in a fresh
// context. Before any page script runs (CDP `Page.addScriptToEvaluateOnNewDocument`), a stand-in
// receiver, as test_ordpar_events104.py's stand-in page: `navigator.webdriver` reads false, the
// events module (`window.ordparEvents`, caught as it is assigned) is given a test receiver address,
// and `fetch` to that address is answered here and its message kept in sessionStorage (which
// survives a reload and a page change within the tab). The built files are not touched.
//
// Steps, reading after each the stored History (`localStorage.history`) and the search events
// sent (every message but a page view):
//   drawSearch   — Random word pressed on the search page (answered in place)
//   reload       — that address reloaded
//   backForward  — Back, then Forward
//   typed        — a search typed in the box and submitted (`args.typed`): recorded and sent as usual
//   drawArticle  — Random word pressed on an article page (args.article): the page is left
//   reload2      — that address reloaded
//
// Result: { base, steps: { <name>: { url, hash, q, box, history: [q...], sent: [msg...], n } } }
import { open, base, args, run, done, sleep } from './cdp.js';

const RECEIVER = 'https://receiver.test/e';

const STUB = `(() => {
  try { Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => false, configurable: true }); } catch (e) {}
  const KEY = '__ordpar_test_sent';
  const real = window.fetch;
  window.fetch = function (url, opts) {
    if (url === ${JSON.stringify(RECEIVER)}) {
      let a = []; try { a = JSON.parse(sessionStorage.getItem(KEY) || '[]'); } catch (e) {}
      try { a.push(JSON.parse(opts && opts.body)); } catch (e) { a.push({ raw: String(opts && opts.body) }); }
      sessionStorage.setItem(KEY, JSON.stringify(a));
      return Promise.resolve(new Response('', { status: 204 }));
    }
    return real.apply(this, arguments);
  };
  let ev;
  Object.defineProperty(window, 'ordparEvents', { configurable: true,
    get() { return ev; },
    set(v) { ev = v; if (v) { v.RECEIVER = ${JSON.stringify(RECEIVER)}; } } });
})();`;

const READ = `(() => {
  let sent = []; try { sent = JSON.parse(sessionStorage.getItem('__ordpar_test_sent') || '[]'); } catch (e) {}
  let hist = []; try { hist = JSON.parse(localStorage.getItem('history') || '[]'); } catch (e) {}
  // the search: after #q=, or (site decisions 117) the word page's own word
  const m = /^#q=([^&]*)/.exec(location.hash) || /^\\/bm-en\\/([^\\/0-9][^\\/]*)\\/$/.exec(location.pathname);
  let q = null; if (m) { try { q = decodeURIComponent(m[1].replace(/\\+/g, ' ')); } catch (e) { q = m[1]; } }
  const box = document.getElementById('ordpar-q');
  const hits = document.querySelector('.ordpar-hits');
  return { url: location.href, hash: location.hash, q, box: box ? box.value : null,
    n: hits ? hits.querySelectorAll('[data-id]').length : 0,
    history: (Array.isArray(hist) ? hist : []).map(e => e && e.q),
    sent: sent.filter(s => s && s.type !== 'view'),
    quiet: window.ordparEvents && window.ordparEvents.quiet ? window.ordparEvents.quiet() : null };
})()`;

async function until(p, expr, ms = 12000) {
  for (let t = 0; t < ms; t += 100) { try { if (await p.eval(expr)) return true; } catch (e) { /* again */ } await sleep(100); }
  return false;
}

async function press(p) {
  const at = await p.eval(`(() => { const b = document.querySelector('.ordpar-random');
    if (!b || !b.getClientRects().length) return null; const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!at) return false;
  if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
  return true;
}

// a search's address: `#q=`, or (site decisions 117) the word's own page, its built rows replaced
const SEARCHED = `(location.hash.indexOf('#q=') === 0 || (/^\\/bm-en\\/[^\\/0-9][^\\/]*\\/$/.test(location.pathname)
  && !location.hash)) && !document.querySelector('.ordpar-word-title')`;
const LANDED = before => `(() => ${SEARCHED} && location.href !== ${JSON.stringify(before)}
  && !!document.querySelector('.ordpar-hits [data-id]'))()`;

// the History entry of a one-article search is written once its text is on hand: time for it
const SETTLE = 2500;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: STUB });
  const steps = {};
  const read = async name => { await sleep(SETTLE); steps[name] = await p.eval(READ); return steps[name]; };

  await p.goto(base + '/bm-en/', 600);
  await p.eval(`localStorage.clear(); sessionStorage.clear(); true`);
  await p.goto(base + '/bm-en/', 800);
  steps.start = await p.eval(READ);

  // Random word on the search page
  let before = await p.eval('location.href');
  if (!await press(p)) { await done({ base, error: 'no Random word button on the search page', steps }); return; }
  steps.drawSearchLanded = await until(p, LANDED(before));
  await read('drawSearch');

  // a reload of that address
  await p.reload(800);
  await until(p, `!!document.querySelector('.ordpar-hits [data-id]')`);
  await read('reload');

  // Back to the empty search page, then Forward to the draw again
  await p.eval('history.back(); true');
  await sleep(800);
  await p.eval('history.forward(); true');
  await until(p, `${SEARCHED} && !!document.querySelector('.ordpar-hits [data-id]')`);
  await read('backForward');

  // a search typed afterwards, on that page: an ordinary search
  await p.eval(`(() => { const b = document.getElementById('ordpar-q'); b.value = ${JSON.stringify(args.typed)};
    b.closest('form').requestSubmit(); return true; })()`);
  await until(p, `(location.hash === '#q=' + encodeURIComponent(${JSON.stringify(args.typed)})
      || location.pathname === '/bm-en/' + encodeURIComponent(${JSON.stringify(args.typed)}) + '/')
    && !!document.querySelector('.ordpar-hits [data-id]')`);
  await read('typed');

  // Random word from an article page: the page is left for the search
  await p.goto(base + '/bm-en/' + args.article + '/', 800);
  before = await p.eval('location.href');
  const loaded = p.waitEvent('Page.loadEventFired', 12000);
  if (!await press(p)) { await done({ base, error: 'no Random word button on the article page', steps }); return; }
  await loaded;
  steps.drawArticleLanded = await until(p, LANDED(before));
  await read('drawArticle');

  await p.reload(800);
  await until(p, `!!document.querySelector('.ordpar-hits [data-id]')`);
  await read('reload2');

  await done({ base, steps });
});
