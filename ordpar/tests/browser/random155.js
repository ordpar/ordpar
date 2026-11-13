// Site decisions 155 (Robin, 2026-10-31): with "Search English words" on, Random word draws an
// English word — every English word the English suggestions can offer, each equally likely — and
// opens it exactly as if it had been typed and picked (148: its English search, the list, or the
// article itself where it has one match); a draw is not a search (115): not in History. With the
// switch off, Random word is as before: a Norwegian headword's search.
//
// For one viewport (args.mobile: a phone, the button tapped; else a computer, clicked), in a fresh
// context, storage cleared:
//   onSearch     — on the search page, the switch turned on by a real click or tap, then Random word
//   reload       — that address reloaded (still a draw: nothing recorded)
//   onArticle    — the switch left on (stored), Random word pressed on an article page
//                  (args.article, which shows no results of its own): the page is left for the search
//   off          — the switch turned off on the search page, then Random word: Norwegian as before
// After each: the address, the box (its value and `lang`), the switch, the search shown (English
// rows / an article in full), whether the drawn word is in the English pool (lookup.js `enPool`
// over the word's own English file, the pool `random-en.json` counts), and the stored History.
//
// Result: { base, steps: { <name>: { url, hash, path, box, boxLang, switchOn, word, inPool,
//   english, shown, history: [...] } } }
import { open, base, args, run, done, sleep } from './cdp.js';

const READ = `(async () => {
  const L = window.ordparLookup;
  const m = /^#en=([^&]*)/.exec(location.hash);
  let word = null; if (m) { try { word = decodeURIComponent(m[1].replace(/\\+/g, ' ')); } catch (e) { word = m[1]; } }
  let inPool = null;
  if (word && L && L.enPool && L.enLetter && L.enNorm && L.loadEnglish) {
    const key = L.enNorm(word), letter = L.enLetter(key);
    const shard = await L.loadEnglish(letter);
    inPool = L.enPool(shard, letter).indexOf(key) !== -1;
  }
  let hist = []; try { hist = JSON.parse(localStorage.getItem('history') || '[]'); } catch (e) {}
  const box = document.getElementById('ordpar-q'), sw = document.getElementById('ordpar-en-switch');
  return { url: location.href, hash: location.hash, path: location.pathname,
    box: box ? box.value : null, boxLang: box ? box.lang : null, switchOn: sw ? sw.checked : null,
    word, inPool, english: !!document.querySelector('.ordpar-hits-en'),
    shown: document.querySelectorAll('.ordpar-hits .ordpar-row, .ordpar-hits .ordpar-result').length,
    history: (Array.isArray(hist) ? hist : []).map(e => e && e.q) };
})()`;

async function until(p, expr, ms = 12000) {
  for (let t = 0; t < ms; t += 100) { try { if (await p.eval(expr)) return true; } catch (e) { /* again */ } await sleep(100); }
  return false;
}

async function press(p, selector) {
  const at = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(selector)});
    if (!b || !b.getClientRects().length) return null; const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!at) return false;
  if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
  return true;
}

// an English search drawn and shown: `#en=<word>`, its results (rows or the one article) in
const ENGLISH = `location.hash.indexOf('#en=') === 0 && location.hash.indexOf('random') === -1
  && !!document.querySelector('.ordpar-hits-en .ordpar-row, .ordpar-hits-en .ordpar-result')`;
const SETTLE = 1500;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const steps = {};
  const read = async name => { await sleep(SETTLE); steps[name] = await p.eval(READ); return steps[name]; };

  await p.goto(base + '/bm-en/', 600);
  await p.eval(`localStorage.clear(); sessionStorage.clear(); true`);
  await p.goto(base + '/bm-en/', 800);

  // the switch on, by a real click or tap on it, then Random word
  if (!await press(p, '.ordpar-switch')) { await done({ base, error: 'no switch on the search page' }); return; }
  await until(p, `document.getElementById('ordpar-en-switch').checked`, 4000);
  if (!await press(p, '.ordpar-random')) { await done({ base, error: 'no Random word button' }); return; }
  steps.onSearchLanded = await until(p, ENGLISH);
  await read('onSearch');

  await p.reload(800);
  await until(p, ENGLISH);
  await read('reload');

  // from an article page, the switch as stored
  await p.goto(base + '/bm-en/' + args.article + '/', 800);
  const loaded = p.waitEvent('Page.loadEventFired', 12000);
  if (!await press(p, '.ordpar-random')) { await done({ base, error: 'no Random word on the article page', steps }); return; }
  await loaded;
  steps.onArticleLanded = await until(p, ENGLISH);
  await read('onArticle');

  // the switch off: Norwegian, as before
  await p.goto(base + '/bm-en/', 800);
  if (!await press(p, '.ordpar-switch')) { await done({ base, error: 'no switch the second time', steps }); return; }
  await until(p, `!document.getElementById('ordpar-en-switch').checked`, 4000);
  const before = await p.eval('location.href');
  if (!await press(p, '.ordpar-random')) { await done({ base, error: 'no Random word the second time', steps }); return; }
  steps.offLanded = await until(p, `location.href !== ${JSON.stringify(before)} && location.hash.indexOf('#en=') === -1
    && !!document.querySelector('.ordpar-hits [data-id]')`);
  await read('off');

  await done({ base, steps });
});
