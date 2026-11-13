// Site decisions 144 (Robin, 2026-10-27): the similar headwords as rows after a search that finds
// nothing; the Norwegian homograph list in the suggestions and History.
//
// For one viewport (args.phone: 390×844, a phone; else 1280×900) and one theme (args.dark), in a
// fresh context:
// * the misses `args.misses` (husx, flyy, spisee and the inflected-form case) opened as searches
//   (`/bm-en/#q=`), and for each the "Similar headwords" section read once every row is filled:
//   the list's class, and per row its word, `href`, the word's `lang` and the row's, the word's
//   colour against the accent and the text colour, the word class, the side's text pieces (each
//   with its `lang`, the numerals apart), "+ N more", the dash before the side (`::before`), the
//   line above the row, and how far the side starts from the word (after the word, not at the
//   right edge); the page's width against the viewport (no sideways scroll);
// * the hit `args.hit` (katt) opened as its word page: the list's class and its links, each the
//   word alone, `lang="nb"`, with the pill's background;
// * the miss-choice listener: `window.ordparEvents` stubbed before a search typed into the box, a
//   click on the second row and a middle click (`auxclick`) on the first, the navigation held off;
// * the suggestions for `args.suggest` (husk): the exact row's side pieces;
// * History after searching it: its row's side pieces.
// With args.shots = {dir, tag} a PNG of each similar section, the suggestions and the History row.
//
// Result: { base, phone, dark, accent, text, misses: {q: {...}}, hit, listener, suggest, history, shots }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

async function shot(p, name, selector) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
    e.scrollIntoView({ block: 'start' }); const r = e.getBoundingClientRect();
    return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; })()`);
  if (!box) return null;
  await p.frames();
  const pad = 8;
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad), width: box.w + 2 * pad, height: box.h + 2 * pad, scale: 1 } });
  const file = args.shots.dir + '/' + name + '-' + args.shots.tag + '.png';
  await Bun.write(file, Buffer.from(data, 'base64'));
  return file;
}

// a colour as the browser computes it, for `value` (a var() or a colour)
const COLOUR = v => `(() => { const s = document.createElement('span'); s.style.color = ${JSON.stringify(v)};
  document.body.appendChild(s); const c = getComputedStyle(s).color; s.remove(); return c; })()`;

// the text pieces of a row's side: each text node's text, its lang, whether it is a numeral
const SIDE = `function side(s) {
  const out = [];
  if (!s) return out;
  const w = document.createTreeWalker(s, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const e = n.parentElement;
    if (!n.data.trim() || e.closest('.ordpar-visually-hidden')) continue;
    if (e.closest('[hidden]')) continue;
    const l = e.closest('[lang]');
    out.push({ t: n.data, lang: l ? l.getAttribute('lang') : '', hg: !!e.closest('.ordpar-hg'),
      more: !!e.closest('.ordpar-option-more'), sgloss: !!e.closest('.ordpar-sgloss'),
      tag: !!e.closest('.ordpar-tag'), w: getComputedStyle(e).fontWeight });
  }
  return out;
}`;

const SIMILAR = `(() => { ${SIDE}
  const sec = document.querySelector('[data-ordpar-results] .ordpar-similar');
  if (!sec) return null;
  const ul = sec.querySelector('.ordpar-similar-list');
  const rows = Array.from(ul.children).map((li, i) => {
    const a = li.querySelector('a'); const word = a.querySelector('.ordpar-option-word');
    const sd = a.querySelector('.ordpar-option-side'); const main = a.querySelector('.ordpar-option-main');
    const before = sd ? getComputedStyle(sd, '::before') : null;
    const lcs = getComputedStyle(li);
    return {
      word: word ? word.textContent : a.textContent, text: a.textContent, href: a.getAttribute('href'),
      aLang: a.getAttribute('lang') || '', wordLang: word ? word.getAttribute('lang') || '' : '',
      row: a.classList.contains('ordpar-option'), translated: a.classList.contains('is-translated'),
      form: a.classList.contains('ordpar-similar-form'),
      colour: getComputedStyle(word || a).color,
      pos: (a.querySelector('.ordpar-pos') || {}).textContent || '',
      side: side(sd), dash: before ? before.content : '', dashColour: before ? before.color : '',
      line: i > 0 ? lcs.borderTopStyle + ' ' + lcs.borderTopWidth : '',
      gap: sd && main ? Math.round(sd.getBoundingClientRect().left - main.getBoundingClientRect().right) : null,
      sideRight: sd ? Math.round(a.getBoundingClientRect().right - sd.getBoundingClientRect().right) : null,
      pending: !!a.querySelector('.is-pending'),
      bg: getComputedStyle(a).backgroundColor, radius: getComputedStyle(a).borderTopLeftRadius,
      rowWidth: Math.round(a.getBoundingClientRect().width) };
  });
  return { cls: ul.className, display: getComputedStyle(ul).display, rows,
    scroll: document.documentElement.scrollWidth, inner: innerWidth };
})()`;

const FILLED = `(() => { const ul = document.querySelector('[data-ordpar-results] .ordpar-similar-list');
  return !!ul && ul.children.length > 0 && !ul.querySelector('.is-pending'); })()`;

run(async () => {
  const phone = !!args.phone;
  const p = await open(phone ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  await p.goto(base + '/bm-en/', 500);
  const accent = await p.eval(COLOUR('var(--ordpar-accent)'));
  const text = await p.eval(COLOUR('var(--ordpar-text)'));
  const out = { base, phone, dark: !!args.dark, accent, text, misses: {}, shots: [] };

  for (const q of args.misses) {
    await p.goto('about:blank', 50);            // a new document each time, not a change of the fragment
    await p.goto(base + '/bm-en/#q=' + encodeURIComponent(q), 500);
    await until(p, FILLED);
    await sleep(500);                            // the last refits
    out.misses[q] = await p.eval(SIMILAR);
    out.shots.push(await shot(p, 'similar-' + q, '[data-ordpar-results] .ordpar-similar'));
  }

  // the hit: the word page, the bare list unchanged
  await p.goto(base + '/bm-en/' + encodeURIComponent(args.hit) + '/', 800);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-similar-list a').length > 0`);
  await sleep(300);
  out.hit = await p.eval(SIMILAR);
  out.shots.push(await shot(p, 'similar-' + args.hit, '[data-ordpar-results] .ordpar-similar'));

  // every place the list shows (step 6): the 404 shell's own search of a mistyped address, and a
  // miss typed into a word page's box (answered in place there)
  out.places = {};
  await p.goto('about:blank', 50);
  await p.goto(base + '/bm-en/' + encodeURIComponent(args.misses[0]), 600);
  await until(p, FILLED);
  out.places.notFound = await p.eval(`(() => { const ul = document.querySelector('[data-ordpar-results] .ordpar-similar-list');
    return { path: location.pathname, cls: ul ? ul.className : '', rows: ul ? ul.querySelectorAll('a.ordpar-option').length : 0 }; })()`);
  await p.goto('about:blank', 50);
  await p.goto(base + '/bm-en/' + encodeURIComponent(args.hit) + '/', 800);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-similar-list a').length > 0`);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(args.misses[1])};
    i.form.requestSubmit(); return true; })()`);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-similar-rows') && ${FILLED}`);
  out.places.wordPage = await p.eval(`(() => { const ul = document.querySelector('[data-ordpar-results] .ordpar-similar-list');
    return { path: location.pathname, cls: ul ? ul.className : '', rows: ul ? ul.querySelectorAll('a.ordpar-option').length : 0 }; })()`);

  // the miss-choice listener: the events stubbed, a search typed, a click and a middle click
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`(() => { window.__calls = [];
    window.ordparEvents = { hit(q) { __calls.push(['hit', q]); }, missStart(q) { __calls.push(['missStart', q]); },
      missChoose(q, w, n) { __calls.push(['missChoose', q, w, n]); } };
    document.addEventListener('click', e => { if (e.target.closest('.ordpar-similar-list a')) e.preventDefault(); });
    const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(args.misses[0])};
    i.form.requestSubmit(); return true; })()`);
  await until(p, FILLED);
  out.listener = await p.eval(`(() => {
    const links = document.querySelectorAll('[data-ordpar-results] .ordpar-similar-list a');
    const words = Array.from(links).map(a => (a.querySelector('.ordpar-option-word') || a).textContent);
    links[1].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    links[0].dispatchEvent(new MouseEvent('auxclick', { bubbles: true, cancelable: true, button: 1 }));
    return { words, calls: __calls, path: location.pathname, hash: location.hash }; })()`);

  // the suggestions for husk
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.focus(); i.value = ${JSON.stringify(args.suggest)};
    i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await until(p, `document.querySelectorAll('#ordpar-listbox > li.ordpar-option, #ordpar-listbox li.ordpar-option').length > 0
    && !document.querySelector('#ordpar-listbox .is-pending')`);
  await sleep(600);
  out.suggest = await p.eval(`(() => { ${SIDE}
    const li = Array.from(document.querySelectorAll('#ordpar-listbox li.ordpar-option'))
      .find(x => (x.querySelector('.ordpar-option-word') || {}).textContent === ${JSON.stringify(args.suggest)});
    return li ? { side: side(li.querySelector('.ordpar-option-side')), translated: li.classList.contains('is-translated') } : null; })()`);
  out.shots.push(await shot(p, 'suggest-' + args.suggest, '.ordpar-popup, #ordpar-listbox'));

  // History after a search for it
  await p.goto('about:blank', 50);
  await p.goto(base + '/bm-en/#q=' + encodeURIComponent(args.suggest), 600);
  await until(p, `JSON.parse(localStorage.getItem('history') || '[]').some(e => e.q === ${JSON.stringify(args.suggest)})`);
  await sleep(500);
  await p.goto(base + '/history/', 600);
  await until(p, `document.querySelectorAll('main .ordpar-option-side').length > 0 && !document.querySelector('main .is-pending')`);
  await sleep(600);
  out.history = await p.eval(`(() => { ${SIDE}
    const a = Array.from(document.querySelectorAll('main a.ordpar-history-link'))
      .find(x => (x.querySelector('.ordpar-option-word') || {}).textContent === ${JSON.stringify(args.suggest)});
    return a ? { side: side(a.querySelector('.ordpar-option-side')), translated: a.classList.contains('is-translated') } : null; })()`);
  out.shots.push(await shot(p, 'history-' + args.suggest, 'main .ordpar-history-row, main li'));
  await done(out);
});
