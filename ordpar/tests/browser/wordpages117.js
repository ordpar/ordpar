// Site decisions 117 (Robin, 2026-10-24/25): the word pages and form pages in a browser.
//
// Each case in a fresh context (its own storage), read once the page's script has drawn the search:
//   direct      /bm-en/<word>/ opened as a link would: the search drawn under the default settings
//               (several entries: the list's rows; one article: the article whole), the page's own
//               title kept, the address unchanged, nothing recorded in History
//   form        /bm-en/tær/: the "is an inflected form of" rows with their labels
//   typed       on an article page, a word typed and Enter: the word's page, its address clean
//               (no #), the search recorded in History as the search page records one
//   suggestion  on an article page, a suggestion chosen: the word's page
//   inplace     on the search page, a form typed and Enter: the address becomes the form's page,
//               with no reload (the search answered in place); then a word with no page: `#q=`
//   back        on a word page, a search made there, then Back: the first word drawn again
//   redirect    /bm-en/#q=<word> loaded (a Recent row, an old link): sent to the word's page
//   similar     a word page's similar headwords: their links go to word pages where they exist
//   capital     /bm-en/Norge (the 404 shell): sent to /bm-en/norge/
//   label       a search for a regular form (husene) on the search page: its row's label
//   random      Random word on an article page: a word page, not recorded
//
// args: { id: an article page }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}
async function key(p, k, code, vk, text) {
  await p.send('Input.dispatchKeyEvent', text ? { type: 'keyDown', key: k, code, windowsVirtualKeyCode: vk, text }
    : { type: 'rawKeyDown', key: k, code, windowsVirtualKeyCode: vk });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk });
}
async function typeInBox(p, text) {
  await until(p, `!!document.getElementById('ordpar-q') && !!window.ordparShell && !!window.ordparShell.ready`);
  await p.eval(`(() => { const q = document.getElementById('ordpar-q'); q.focus(); q.select(); return true; })()`);
  await p.send('Input.insertText', { text });
  await sleep(600);
}
const DRAWN = `(() => !document.querySelector('[data-ordpar-results] .ordpar-word-title')
  && !!document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-inflected, [data-ordpar-results] .ordpar-miss')
  && !document.querySelector('[data-ordpar-results] [aria-busy="true"]'))()`;
const STATE = `(() => ({
  path: decodeURIComponent(location.pathname), hash: location.hash, title: document.title,
  rows: document.querySelectorAll('[data-ordpar-results] .ordpar-row').length,
  full: document.querySelectorAll('[data-ordpar-results] .ordpar-result').length,
  fullLoaded: document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok').length,
  inflected: Array.from(document.querySelectorAll('[data-ordpar-results] .ordpar-inflected .ordpar-hit')).map(li =>
    ({ word: li.querySelector('.ordpar-hit-link').textContent, pos: (li.querySelector('.ordpar-pos') || {}).textContent || '',
       label: (li.querySelector('.ordpar-form-label') || {}).textContent || '' })),
  similar: Array.from(document.querySelectorAll('.ordpar-similar-list a')).map(a => ({ word: (a.querySelector('.ordpar-option-word') || a).textContent, href: a.getAttribute('href') })),   // 144: rows after a miss
  history: (() => { try { return JSON.parse(localStorage.getItem('history') || '[]').map(e => e.q); } catch (e) { return ['?']; } })(),
  mark: window.__w117 || null
}))()`;

run(async () => {
  const out = { base };
  const fresh = async () => open({ w: 1280, h: 900 });

  async function opened(url, settle = 400) {
    const p = await fresh();
    await p.goto(url, settle);
    const drawn = await until(p, DRAWN);
    return { p, drawn };
  }

  // direct: several entries, one article, a form page
  for (const [name, path] of [['several', '/bm-en/s%C3%A5/'], ['one', '/bm-en/norge/'], ['form', '/bm-en/t%C3%A6r/']]) {
    const { p, drawn } = await opened(base + path);
    if (name === 'one') await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok').length > 0`);
    out[name] = Object.assign({ drawn }, await p.eval(STATE));
    await p.close();
  }

  // typed on an article page, Enter: the word's page
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/' + args.id + '/', 400);
    await typeInBox(p, 'så');
    await key(p, 'Escape', 'Escape', 27);
    await key(p, 'Enter', 'Enter', 13, '\r');
    await until(p, `decodeURIComponent(location.pathname) === '/bm-en/så/'`, 15000);
    await until(p, DRAWN);
    await sleep(500);
    out.typed = await p.eval(STATE);
    await p.close();
  }

  // a suggestion chosen on an article page
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/' + args.id + '/', 400);
    await typeInBox(p, 'bru');
    await until(p, `document.querySelectorAll('#ordpar-listbox .ordpar-option').length > 0`);
    const word = await p.eval(`(() => { const lis = Array.from(document.querySelectorAll('#ordpar-listbox .ordpar-option'));
      const li = lis.find(l => (l.textContent || '').trim().startsWith('bru')) || lis[0];
      li.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true })); return li.textContent; })()`);
    await until(p, `location.pathname !== '/bm-en/${args.id}/'`, 15000);
    await until(p, DRAWN);
    out.suggestion = Object.assign({ chose: word }, await p.eval(STATE));
    await p.close();
  }

  // in place on the search page: a form, then a word with no page
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/', 600);
    await p.eval(`window.__w117 = 'kept'`);
    await typeInBox(p, 'tær');
    await key(p, 'Escape', 'Escape', 27);
    await key(p, 'Enter', 'Enter', 13, '\r');
    await until(p, `decodeURIComponent(location.pathname) === '/bm-en/tær/'`);
    await until(p, DRAWN);
    out.inplace = await p.eval(STATE);
    await typeInBox(p, 'xyzzyqq');
    await key(p, 'Escape', 'Escape', 27);
    await key(p, 'Enter', 'Enter', 13, '\r');
    await until(p, `location.hash.indexOf('#q=xyzzyqq') === 0`);
    await sleep(500);
    out.nopage = await p.eval(STATE);
    await p.close();
  }

  // Back after a search made on a word page
  {
    const { p } = await opened(base + '/bm-en/da/');
    await p.eval(`window.__w117 = 'kept'`);
    await typeInBox(p, 'så');
    await key(p, 'Escape', 'Escape', 27);
    await key(p, 'Enter', 'Enter', 13, '\r');
    await until(p, `decodeURIComponent(location.pathname) === '/bm-en/så/'`);
    await until(p, DRAWN);
    const there = await p.eval(STATE);
    await p.eval('history.back(), true');
    await until(p, `decodeURIComponent(location.pathname) === '/bm-en/da/'`);
    await sleep(300);
    await until(p, DRAWN);
    out.back = { there, back: await p.eval(STATE) };
    await p.close();
  }

  // a search's address with a page: sent there
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/#q=da', 400);
    await until(p, `location.pathname === '/bm-en/da/'`);
    await until(p, DRAWN);
    await sleep(500);
    out.redirect = await p.eval(STATE);
    await p.close();
  }

  // the similar headwords on a word page
  {
    const { p } = await opened(base + '/bm-en/da/');
    await until(p, `document.querySelectorAll('.ordpar-similar-list a').length > 0`);
    out.similar = (await p.eval(STATE)).similar;
    await p.close();
  }

  // the 404 shell with capitals
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/Norge', 400);
    await until(p, `location.pathname === '/bm-en/norge/'`);
    await until(p, DRAWN);
    out.capital = await p.eval(STATE);
    await p.close();
  }

  // a regular form's row on the search page
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/#q=husene', 400);
    await until(p, DRAWN);
    await until(p, `!!document.querySelector('.ordpar-inflected .ordpar-hit')`);
    out.label = await p.eval(STATE);
    await p.close();
  }

  // Random word from an article page
  {
    const p = await fresh();
    await p.goto(base + '/bm-en/' + args.id + '/', 400);
    await until(p, `!!document.querySelector('[data-ordpar-random]') && !document.querySelector('[data-ordpar-random]').hidden`);
    await p.eval(`document.querySelector('[data-ordpar-random]').click(), true`);
    await until(p, `location.pathname !== '/bm-en/${args.id}/'`, 15000);
    await until(p, DRAWN);
    await sleep(500);
    out.random = await p.eval(STATE);
    await p.close();
  }

  done(out);
});
