// Site decisions 150 (Robin, 2026-10-29): the Norwegian suggestions show the spelling typed.
//
// For one viewport (args.phone) and theme (args.dark), the box typed with each of args.typed
// ("selv", "sjøl"): the first rows' words as drawn (the numeral's hidden reading left out), each
// row's number of spellings drawn, and whether a row mixes the two spellings; then a search for
// args.searched ("sjølsagt") and its History and Recent rows' words. With args.shots = {dir, tag}
// a PNG of each dropdown.
//
// Result: { base, phone, dark, typed: {t: {rows: [{word, parts, cls}], wide}}, history, recent, shots }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

async function shot(p, name, selector) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
    const r = e.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; })()`);
  if (!box || !box.w || !box.h) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: Math.max(0, box.x - 8), y: Math.max(0, box.y - 8), width: box.w + 16, height: box.h + 16, scale: 1 } });
  const file = args.shots.dir + '/' + name + '-' + args.shots.tag + '.png';
  await Bun.write(file, Buffer.from(data, 'base64'));
  return file;
}

const WORD = `function word(li) {
  const w = li.querySelector('.ordpar-option-word'); if (!w) return '';
  const c = w.cloneNode(true); c.querySelectorAll('.ordpar-visually-hidden').forEach(x => x.remove());
  return c.textContent; }`;

run(async () => {
  const p = await open(args.phone ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  await p.goto(base + '/bm-en/', 600);
  const out = { base, phone: !!args.phone, dark: !!args.dark, typed: {}, shots: [] };
  for (const t of args.typed) {
    await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.focus(); i.value = ${JSON.stringify(t)};
      i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
    // wait for THIS word's rows: the previous word's stay in the box until the new index file is in,
    // which on the live site can take longer than the sleep (the deploy of 2026-10-31 read "selv"'s
    // rows for "sjøl"); on a faulty site the wait times out and the check below still fails
    await until(p, `(() => { const w = document.querySelector('#ordpar-listbox li.ordpar-option .ordpar-option-word');
      return document.querySelectorAll('#ordpar-listbox li.ordpar-option').length > 3 && !document.querySelector('#ordpar-listbox .is-pending')
        && !!w && w.textContent.toLowerCase().startsWith(${JSON.stringify(t)}); })()`);
    await sleep(500);
    out.typed[t] = await p.eval(`(() => { ${WORD}
      const rows = Array.from(document.querySelectorAll('#ordpar-listbox li.ordpar-option')).slice(0, 12).map(li => ({
        word: word(li), parts: li.querySelectorAll('.ordpar-option-word .ordpar-option-match, .ordpar-option-word .ordpar-option-alt').length }));
      return { rows, wide: document.documentElement.scrollWidth <= innerWidth + 1 }; })()`);
    out.shots.push(await shot(p, 'suggest150-' + t, '.ordpar-popup'));
  }
  // the box picked: the row's spelling is what is searched
  const pick = await p.eval(`(() => { ${WORD} const li = Array.from(document.querySelectorAll('#ordpar-listbox li.ordpar-option'))
    .find(x => word(x) === ${JSON.stringify(args.searched)}); if (!li) return null;
    const r = li.getBoundingClientRect(); return { x: r.left + 20, y: r.top + r.height / 2 }; })()`);
  if (pick) {
    await p.click(pick.x, pick.y);
    await until(p, `JSON.parse(localStorage.getItem('history') || '[]').some(e => e.q === ${JSON.stringify(args.searched)})`, 8000);
  }
  out.picked = await p.eval(`({ box: (document.getElementById('ordpar-q') || {}).value, path: location.pathname,
    history: JSON.parse(localStorage.getItem('history') || '[]').map(e => e.q) })`);
  await p.goto(base + '/history/', 700);
  await until(p, `document.querySelectorAll('main a.ordpar-history-link').length > 0 && !document.querySelector('main .is-pending')`);
  out.history = await p.eval(`(() => { ${WORD} return Array.from(document.querySelectorAll('main a.ordpar-history-link')).map(word); })()`);
  await p.goto(base + '/bm-en/', 600);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ''; i.focus(); i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await until(p, `document.querySelectorAll('#ordpar-listbox li.ordpar-option-recent').length > 0`);
  out.recent = await p.eval(`(() => { ${WORD} return Array.from(document.querySelectorAll('#ordpar-listbox li.ordpar-option-recent')).map(word); })()`);
  await done(out);
});
