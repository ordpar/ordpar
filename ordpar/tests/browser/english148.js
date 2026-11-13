// Site decisions 148 (Robin, 2026-10-29): the English search, in a browser.
//
// For one viewport (args.phone: 390×844, a phone; else 1280×900) and one theme (args.dark), in a
// fresh context, on the search page:
// * the switch: drawn under the box (a computer: below it; a phone: on Random word's row), its
//   label, off at first; clicked, the box's placeholder, label and `lang`, and the stored direction;
//   a reload keeps it on (remembered);
// * the suggestions typed with it on, for each of args.suggest (hou, run, phone): each row's English
//   word, its colour and weight, its side's Norwegian headwords (each one spelling, no ", "), their
//   colour and weight, the word classes shown, "+ N more", the row's `data-cut`;
// * the address `/bm-en/#en=<q>` for args.results (go, house, candle, swimming, hoose, smartphone):
//   the switch on, the heading, the view (rows, or one article in full), each row's headword line
//   and its snippet line — its text, the bold pieces and their weight, the rest's weight, wrapping
//   — the miss's heading and line, the similar English words (rows or the bare list), the title;
// * switched off with a word in the box: the same word searched in Norwegian;
// * Random word with the switch on: since site decisions 155 an English word's search, the switch
//   still on (until then the switch went off: 148 item 11, amended);
// * History and Recent after English searches: the rows' English word, side and link;
// * the page never wider than the viewport.
// With args.shots = {dir, tag} PNGs of the switch, the suggestions, the results and the rest.
//
// Result: { base, phone, dark, accent, text, switch, stored, remembered, suggest: {q: …},
//           results: {q: …}, off, random, history, recent, shots }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

async function shot(p, name, selector) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
    const r = e.getBoundingClientRect();
    return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: Math.min(r.height, 1400) }; })()`);
  if (!box || !box.w || !box.h) return null;
  await p.frames();
  const pad = 8;
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad), width: box.w + 2 * pad, height: box.h + 2 * pad, scale: 1 } });
  const file = args.shots.dir + '/' + name + '-' + args.shots.tag + '.png';
  await Bun.write(file, Buffer.from(data, 'base64'));
  return file;
}

const COLOUR = v => `(() => { const s = document.createElement('span'); s.style.color = ${JSON.stringify(v)};
  document.body.appendChild(s); const c = getComputedStyle(s).color; s.remove(); return c; })()`;

const WIDE = `(document.documentElement.scrollWidth <= innerWidth + 1)`;

// one English row (a suggestion, a Recent row, a History link, a similar row)
const ROW = `function row(li) {
  const word = li.querySelector('.ordpar-option-word');
  const nbs = Array.from(li.querySelectorAll('.ordpar-option-side .ordpar-en-nb'));
  const more = li.querySelector('.ordpar-option-more');
  const cs = word ? getComputedStyle(word) : null;
  return { word: word ? word.textContent : '', wordLang: word ? word.getAttribute('lang') : '',
    wordColour: cs ? cs.color : '', wordWeight: cs ? cs.fontWeight : '',
    en: li.classList.contains('ordpar-option-en'),
    nb: nbs.map(n => n.textContent.replace(/\\s*homograph \\d+$/, '')),
    nbColour: nbs.length ? getComputedStyle(nbs[0]).color : '', nbWeight: nbs.length ? getComputedStyle(nbs[0]).fontWeight : '',
    nbLang: nbs.length ? (nbs[0].closest('[lang]') || {}).getAttribute('lang') : '',
    pos: Array.from(li.querySelectorAll('.ordpar-option-side .ordpar-pos')).filter(x => !x.closest('[hidden]')).map(x => x.textContent),
    more: more && !more.hidden ? more.textContent : '', cut: (li.querySelector('[data-cut]') || { getAttribute: () => null }).getAttribute('data-cut'),
    count: (li.querySelector('.ordpar-option-side > .ordpar-option-count:not(.ordpar-option-more)') || {}).textContent || '',
    pending: !!li.querySelector('.is-pending'), href: li.getAttribute('href') || '',
    overflow: li.scrollWidth > li.clientWidth + 1 };
}`;

const RESULTS = `(() => { ${ROW}
  const R = document.querySelector('[data-ordpar-results]');
  const heading = R.querySelector('.ordpar-dict-name');
  const rows = Array.from(R.querySelectorAll('.ordpar-rows-en .ordpar-row')).map(r => {
    const w = r.querySelector('.ordpar-row-word'); const s = r.querySelector('.ordpar-row-snippet');
    const hits = s ? Array.from(s.querySelectorAll('.ordpar-en-hit')) : [];
    return { id: r.getAttribute('data-id'), word: w ? w.textContent.replace(/\\s*homograph \\d+/g, '') : '',
      pos: (r.querySelector('.ordpar-row-line .ordpar-pos') || {}).textContent || '',
      snippet: s ? s.textContent : '', lang: s ? s.getAttribute('lang') : '',
      hits: hits.map(h => h.textContent), hitWeight: hits.length ? getComputedStyle(hits[0]).fontWeight : '',
      weight: s ? getComputedStyle(s).fontWeight : '', white: s ? getComputedStyle(s).whiteSpace : '',
      sgloss: !!(s && s.querySelector('.ordpar-sgloss')), pending: !!(s && s.classList.contains('is-pending')) };
  });
  const sim = R.querySelector('.ordpar-similar');
  const list = sim ? sim.querySelector('.ordpar-similar-list') : null;
  const miss = R.querySelector('.ordpar-miss');
  return { heading: heading ? heading.textContent : '', count: (R.querySelector('.ordpar-count span') || {}).textContent || '',
    rows, full: R.querySelectorAll('.ordpar-result').length,
    fullWord: (R.querySelector('.ordpar-result h3, .ordpar-result .ordpar-hw') || {}).textContent || '',
    miss: miss ? (miss.querySelector('h2') || {}).textContent : '', missLine: miss ? (miss.querySelector('.ordpar-note') || {}).textContent : '',
    similarHead: sim ? sim.querySelector('h2').textContent : '', similarRows: !!(list && list.classList.contains('ordpar-similar-rows')),
    similar: list ? Array.from(list.querySelectorAll(':scope > li > a')).map(a => a.classList.contains('ordpar-option') ? row(a) : { word: a.textContent, href: a.getAttribute('href'), lang: a.getAttribute('lang') }) : [],
    title: document.title, hash: location.hash, path: location.pathname,
    // the English index files the page asked for (from the network or a cache alike), in order
    enFiles: performance.getEntriesByType('resource').map(e => e.name).filter(n => n.indexOf('/index/en/') !== -1)
      .map(n => n.split('/index/en/')[1].split('?')[0]),
    switchOn: !!(document.getElementById('ordpar-en-switch') || {}).checked, wide: ${WIDE} };
})()`;

const SETTLED = `(() => { const R = document.querySelector('[data-ordpar-results]');
  if (!R || R.querySelector('.ordpar-empty') || R.querySelector('[aria-busy="true"]')) return false;
  if (!(R.querySelector('.ordpar-hits') || R.querySelector('.ordpar-miss'))) return false;
  if (R.querySelector('.ordpar-miss') && !(R.querySelector('.ordpar-miss .ordpar-note') || {}).textContent) return false;
  return !R.querySelector('.is-pending'); })()`;

run(async () => {
  const phone = !!args.phone;
  const p = await open(phone ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  await p.goto(base + '/bm-en/', 600);
  const accent = await p.eval(COLOUR('var(--ordpar-accent)'));
  const text = await p.eval(COLOUR('var(--ordpar-text)'));
  const out = { base, phone, dark: !!args.dark, accent, text, suggest: {}, results: {}, shots: [] };

  // 1. the switch, where it is drawn
  await until(p, `!!document.getElementById('ordpar-en-switch')`, 5000);
  const geo = `(() => { const sw = document.querySelector('.ordpar-direction'); if (!sw) return null;
    const box = document.querySelector('.ordpar-search').getBoundingClientRect(), r = sw.getBoundingClientRect();
    const rnd = document.querySelector('.ordpar-random').getBoundingClientRect();
    const cb = document.getElementById('ordpar-en-switch'), i = document.getElementById('ordpar-q');
    const tr = sw.querySelector('.ordpar-switch-track').getBoundingClientRect();
    return { text: sw.textContent, role: cb.getAttribute('role'), checked: cb.checked,
      belowBox: Math.round(r.top - box.bottom), left: Math.round(r.left - box.left),
      sameRowAsRandom: Math.abs((r.top + r.bottom) / 2 - (rnd.top + rnd.bottom) / 2) < 12,
      placeholder: i.placeholder, lang: i.getAttribute('lang'),
      label: document.querySelector('label[for="ordpar-q"]').textContent,
      track: { x: tr.left + tr.width / 2, y: tr.top + tr.height / 2 }, wide: ${WIDE} }; })()`;
  out.switch = { before: await p.eval(geo) };
  out.shots.push(await shot(p, 'switch-off', 'header.ordpar-header'));
  const t0 = out.switch.before.track;
  if (phone) await p.tap(t0.x, t0.y); else await p.click(t0.x, t0.y);
  await sleep(300);
  out.switch.after = await p.eval(geo);
  out.stored = await p.eval(`localStorage.getItem('direction')`);
  out.shots.push(await shot(p, 'switch-on', 'header.ordpar-header'));
  await p.reload(600);
  await until(p, `!!document.getElementById('ordpar-en-switch')`, 5000);
  out.remembered = await p.eval(geo);

  // 2. the suggestions, typed with the switch on
  for (const q of args.suggest) {
    await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.focus(); i.value = ${JSON.stringify(q)};
      i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
    // wait for THIS word's rows: the previous word's stay in the box until the new index file is in,
    // which on the live site can take longer than the sleep (the deploy of 2026-10-31 read "run"'s
    // rows for "phone")
    await until(p, `(() => { const w = document.querySelector('#ordpar-listbox li.ordpar-option .ordpar-option-word');
      return !!w && w.textContent.toLowerCase().startsWith(${JSON.stringify(q)}); })()`);
    await sleep(500);
    out.suggest[q] = await p.eval(`(() => { ${ROW}
      return { rows: Array.from(document.querySelectorAll('#ordpar-listbox li.ordpar-option')).slice(0, 8).map(row),
        n: document.querySelectorAll('#ordpar-listbox li.ordpar-option').length, wide: ${WIDE} }; })()`);
    out.shots.push(await shot(p, 'suggest-' + q, '.ordpar-popup'));
  }
  // picking a row runs the English search for it (the first row of the last list)
  const first = await p.eval(`(() => { const li = document.querySelector('#ordpar-listbox li.ordpar-option');
    const r = li.getBoundingClientRect(); return { x: r.left + 20, y: r.top + r.height / 2, word: li.querySelector('.ordpar-option-word').textContent }; })()`);
  await p.click(first.x, first.y);
  await until(p, SETTLED);
  out.picked = { word: first.word, hash: await p.eval('location.hash'), title: await p.eval('document.title') };
  await p.eval(`document.getElementById('ordpar-q').blur(); true`);

  // 3. the searches, opened from their address
  for (const q of args.results) {
    await p.goto('about:blank', 50);
    await p.goto(base + '/bm-en/#en=' + encodeURIComponent(q), 700);
    await until(p, SETTLED);
    // the similar English words come last, a hit's as a miss's: after the rows' glosses (a hit) or
    // the note's numbers (a miss), once their index file is in — so SETTLED can hold before they are
    // drawn (the deploys of 2026-11-07 read house's list empty, once on a phone, once on a
    // computer). For a search that should have them (args.similar), wait until the list has its
    // first word; if it never comes, the result says so and the test fails, as before.
    if ((args.similar || []).includes(q)) {
      await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-similar .ordpar-similar-list > li > a')`, 15000);
    } else if (await p.eval(`!!document.querySelector('[data-ordpar-results] .ordpar-miss')`)) {
      // a miss draws its similar words after its note, once their index file is in (slower live)
      await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-similar')`, 8000);
    }
    await sleep(600);
    out.results[q] = await p.eval(RESULTS);
    out.shots.push(await shot(p, 'results-' + q, '[data-ordpar-results]'));
  }

  // 4. switched off with a word in the box: the same word in Norwegian
  await p.goto('about:blank', 50);
  await p.goto(base + '/bm-en/#en=house', 700);
  await until(p, SETTLED);
  const tr = await p.eval(`(() => { const r = document.querySelector('.ordpar-switch-track').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (phone) await p.tap(tr.x, tr.y); else await p.click(tr.x, tr.y);
  await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-hits:not(.ordpar-hits-en)')`);
  await sleep(500);
  out.off = await p.eval(`({ switchOn: document.getElementById('ordpar-en-switch').checked, box: document.getElementById('ordpar-q').value,
    path: location.pathname, hash: location.hash, english: !!document.querySelector('.ordpar-hits-en'),
    placeholder: document.getElementById('ordpar-q').placeholder, stored: localStorage.getItem('direction') })`);

  // 5. Random word with the switch on: an English word's search, the switch still on (site
  // decisions 155, amending 148 item 11's "back to Norwegian")
  await p.goto(base + '/bm-en/#en=house', 700);
  await until(p, SETTLED);
  await p.eval(`document.querySelector('[data-ordpar-random]').click(); true`);
  await until(p, `document.getElementById('ordpar-en-switch').checked && location.hash.indexOf('#en=') === 0
    && location.hash !== '#en=house'`, 8000);
  await sleep(500);
  out.random = await p.eval(`({ switchOn: document.getElementById('ordpar-en-switch').checked, hash: location.hash, path: location.pathname })`);

  // 6. History and Recent: English searches made, then a Norwegian one
  await p.goto('about:blank', 50);
  await p.eval(`true`);
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.removeItem('history'); true`);
  for (const q of ['house', 'smartphone', 'swim']) {
    await p.goto('about:blank', 50);
    await p.goto(base + '/bm-en/#en=' + q, 700);
    await until(p, SETTLED);
  }
  await p.goto('about:blank', 50);
  await p.goto(base + '/bm-en/#q=hus', 900);
  await until(p, `JSON.parse(localStorage.getItem('history') || '[]').some(e => e.q === 'hus')`);
  out.stored_history = await p.eval(`JSON.parse(localStorage.getItem('history') || '[]').map(e => ({ q: e.q, n: e.n, en: !!e.en }))`);
  await p.goto(base + '/history/', 700);
  await until(p, `document.querySelectorAll('main a.ordpar-history-link').length >= 3 && !document.querySelector('main .is-pending')`);
  await sleep(600);
  out.history = await p.eval(`(() => { ${ROW} return { rows: Array.from(document.querySelectorAll('main a.ordpar-history-link')).map(row), wide: ${WIDE} }; })()`);
  out.shots.push(await shot(p, 'history', 'main'));
  // Recent: the box emptied and focused, the switch on
  await p.goto(base + '/bm-en/', 600);
  await p.eval(`(() => { if (!document.getElementById('ordpar-en-switch').checked) document.getElementById('ordpar-en-switch').click();
    const i = document.getElementById('ordpar-q'); i.value = ''; i.focus(); i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await until(p, `document.querySelectorAll('#ordpar-listbox li.ordpar-option-recent').length >= 3 && !document.querySelector('#ordpar-listbox .is-pending')`);
  await sleep(500);
  out.recent = await p.eval(`(() => { ${ROW} return { rows: Array.from(document.querySelectorAll('#ordpar-listbox li.ordpar-option-recent')).map(row), wide: ${WIDE} }; })()`);
  out.shots.push(await shot(p, 'recent', '.ordpar-popup'));
  await done(out);
});
