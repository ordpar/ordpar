// Site decisions 170 (Robin, 2026-11-06): the sound icon's early load follows the setting "When a
// linked article or page is loaded" (`minifetch`). On a computer, for each value in turn, on *hus*
// (24627): the article opened, the pointer rested on an example's icon well past `REST_MS`, then the
// icon pressed, then another icon of the same block pressed.
//
// The second part (2026-11-06, "Yes, marks now"): the sound list `/audio/<k>.json` (our own host) is
// fetched only when a recording is wanted, never as an article or a small article opens, and the
// table's icons are drawn from the page's mark (`data-a-cells`) with no list; no `preconnect` to the
// Worker under `click`.
//
// The audio Worker is never reached: every request to it is intercepted (the DevTools `Fetch`
// domain) and answered by a stand-in of a few bytes, and counted. So the counts are the requests
// the page made, and the live Worker's daily allowance is not touched (a press "plays" the
// stand-in, which fails to decode; only the request is counted). The sound lists on our own host
// are intercepted too (`/audio/*`), counted and let through; each count is checked against the
// page's own resource timing, which a list served from the browser's cache still enters.
//
// Result: { base, cases: { click|point|page: {...}, mini: {...} } }, per value:
//   mode         `ordparAhead.mode()` as the page reads the setting
//   icons        the example icons drawn
//   cells        the table's icons drawn at open: each its form's text (`_keys[0]`), sorted
//   listsOpen    sound lists asked for by the time the article has opened (intercepted, timing)
//   preconnect   a `preconnect` to the Worker after the open, before any rest or press
//   rested       requests to the Worker after the rest (before any press)
//   listsRest    sound lists after the rest (cumulative)
//   pressed      requests to the Worker after the press too (cumulative)
//   listsPress   sound lists after the press (cumulative)
//   listsSecond  sound lists after a second icon of the same block pressed (cumulative)
// mini (`point`): a small article (hjem, 23742) opened on hus: its icons, the lists asked for.
import { open, base, run, done, sleep } from './cdp.js';

const WORKER = 'https://ordpar-audio.ordpar.workers.dev/';
const SEL = '.ordpar-article .ordbok-ex-list button.ordpar-play';
const LIST = /\/audio\/\d+\.json(\?|$)/;

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

async function centre(p, i) {
  const ok = await p.eval(`(() => { const b = [...document.querySelectorAll(${JSON.stringify(SEL)})]
    .filter(e => e.getClientRects().length)[${i}]; if (!b) return false; b.scrollIntoView({ block: 'center' }); return true; })()`);
  if (!ok) return null;
  await p.frames();
  return p.eval(`(() => { const r = [...document.querySelectorAll(${JSON.stringify(SEL)})]
    .filter(e => e.getClientRects().length)[${i}].getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
}

// the sound lists in the page's resource timing (a fetch the browser's cache answers is there too)
const TIMED = `performance.getEntriesByType('resource').filter(e => ${LIST}.test(e.name)).length`;
const CELLS = `[...document.querySelectorAll('.ordpar-article .ordpar-inflection td button.ordpar-play')]
  .filter(b => !b.closest('.ordbok-xmini')).map(b => b._keys && b._keys[0]).sort()`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const requests = [];
  const lists = [];
  // an ID3 header and nothing more: a stand-in for a clip
  const BODY = Buffer.from('ID3\x03\x00\x00\x00\x00\x00\x00').toString('base64');
  p.on(m => {
    if (m.method !== 'Fetch.requestPaused') return;
    const url = m.params.request.url;
    if (url.indexOf(WORKER) === 0) {
      requests.push(url);
      p.send('Fetch.fulfillRequest', { requestId: m.params.requestId, responseCode: 200, body: BODY,
        responseHeaders: [{ name: 'Content-Type', value: 'audio/mpeg' },
          { name: 'Access-Control-Allow-Origin', value: '*' }] }).catch(() => {});
      return;
    }
    if (LIST.test(url)) lists.push(url);
    p.send('Fetch.continueRequest', { requestId: m.params.requestId }).catch(() => {});
  });
  await p.send('Fetch.enable', { patterns: [{ urlPattern: WORKER + '*' }, { urlPattern: base + '/audio/*' }] });
  const count = async () => Math.max(lists.length, (await p.eval(TIMED)) || 0);

  const cases = {};
  await p.goto(base + '/bm-en/24627/', 400);
  for (const value of ['click', 'point', 'page']) {
    await p.eval(`localStorage.setItem('minifetch', ${JSON.stringify(value)}); true`);
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 2, y: 2 });
    lists.length = 0;
    await p.reload(600);
    await until(p, `document.querySelectorAll(${JSON.stringify(SEL)}).length >= 3`);
    await sleep(1200);                        // as long as the old page took to fetch its list
    const mode = await p.eval(`window.ordparAhead ? ordparAhead.mode() : null`);
    const icons = await p.eval(`document.querySelectorAll(${JSON.stringify(SEL)}).length`);
    const cells = await p.eval(CELLS);
    const listsOpen = await count();
    const preconnect = await p.eval(`!!document.querySelector('link[rel="preconnect"][href^="https://ordpar-audio."]')`);
    requests.length = 0;
    const c = await centre(p, 2);
    if (!c) { cases[value] = { mode, icons, cells, listsOpen, preconnect, rested: null }; continue; }
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x, y: c.y });
    await sleep(1200);                        // well past REST_MS (150)
    const rested = requests.slice();
    const listsRest = await count();
    await p.click(c.x, c.y);
    await sleep(1200);
    const pressed = requests.length;
    const listsPress = await count();
    await p.eval(`window.ordparAudio && ordparAudio.stop(), true`);
    const c2 = await centre(p, 3);
    if (c2) { await p.click(c2.x, c2.y); await sleep(1000); }
    const listsSecond = await count();
    await p.eval(`window.ordparAudio && ordparAudio.stop(), true`);
    cases[value] = { mode, icons, cells, listsOpen, preconnect, rested: rested.length, restedUrl: rested[0] || null,
      listsRest, pressed, listsPress, listsSecond };
  }

  // a small article opened on hus (`mount`): its icons drawn, no list asked for
  await p.eval(`localStorage.setItem('minifetch', 'point'); true`);
  lists.length = 0;
  await p.reload(600);
  const LINK = 'main .ordpar-article a.ordbok-xword[href^="/bm-en/23742/"]';
  await until(p, `!!document.querySelector(${JSON.stringify(LINK)})`);
  await sleep(800);
  const before = await count();
  await p.eval(`(() => { const a = document.querySelector(${JSON.stringify(LINK)}); a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })); return true; })()`);
  const opened = await until(p, `!!document.querySelector('.ordbok-xmini .ordpar-fmini:not([aria-busy]) button.ordpar-play')`, 10000);
  await sleep(1200);
  cases.mini = { opened, icons: await p.eval(`document.querySelectorAll('.ordbok-xmini button.ordpar-play').length`),
    listsBefore: before, listsAfter: await count() };
  await p.eval(`localStorage.removeItem('minifetch'); true`);
  await done({ base, cases });
});
