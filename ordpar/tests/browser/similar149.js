// Site decisions 149 (Robin, 2026-10-29): a similar headword is listed only if its own search would
// show an article not already on the page.
//
// For one viewport (args.phone) and theme (args.dark), each of args.searches opened as a search
// (`/bm-en/#q=`, which goes on to the word's own page): once the results and the similar headwords
// have come, the similar words listed, the articles on the page (their ids, the results' and the
// inflected-form rows') and the page's width. With args.shots = {dir, tag} a PNG of the page's
// results.
//
// Result: { base, phone, dark, searches: {q: {similar: [...], ids: [...], forms: [...], wide}}, shots }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

async function shot(p, name, selector) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
    const r = e.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: Math.min(r.height, 1600) }; })()`);
  if (!box || !box.w || !box.h) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: Math.max(0, box.x - 8), y: Math.max(0, box.y - 8), width: box.w + 16, height: box.h + 16, scale: 1 } });
  const file = args.shots.dir + '/' + name + '-' + args.shots.tag + '.png';
  await Bun.write(file, Buffer.from(data, 'base64'));
  return file;
}

run(async () => {
  const p = await open(args.phone ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  const out = { base, phone: !!args.phone, dark: !!args.dark, searches: {}, shots: [] };
  for (const q of args.searches) {
    await p.goto('about:blank', 50);
    await p.goto(base + '/bm-en/#q=' + encodeURIComponent(q), 900);
    await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-hits') && !document.querySelector('[data-ordpar-results] [aria-busy="true"]')`);
    // the similar words come after the results; give them their time
    await until(p, `!!document.querySelector('[data-ordpar-results] .ordpar-similar-list a')`, 6000);
    await sleep(800);
    out.searches[q] = await p.eval(`(() => {
      const R = document.querySelector('[data-ordpar-results]');
      const sim = Array.from(R.querySelectorAll('.ordpar-similar-list a')).map(a => (a.querySelector('.ordpar-option-word') || a).textContent);
      const ids = Array.from(R.querySelectorAll('.ordpar-hits [data-id]')).map(x => x.getAttribute('data-id'));
      const forms = Array.from(R.querySelectorAll('.ordpar-inflected a')).map(a => a.textContent);
      return { similar: sim, ids, forms, path: location.pathname, wide: document.documentElement.scrollWidth <= innerWidth + 1 }; })()`);
    out.shots.push(await shot(p, 'similar149-' + q, '[data-ordpar-results]'));
  }
  await done(out);
});
