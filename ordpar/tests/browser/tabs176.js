// Site decisions 176 (Robin, 2026-11-07): the tabs over the about pages, and 175's change pages, in
// a browser.
//
// For one viewport (args.w × args.h, args.mobile) and theme (args.dark), each of args.pages opened:
// its tab row (`nav.ordpar-tabs`) — its label, its place (the `<h1>` right before it, a paragraph
// right after), each tab's words, address, `aria-current`, background and text colour, and box;
// the rows the tabs fall into (by their tops); whether anything is wider than the window (the
// page, the row); the footer's About link's words. Then args.none opened: no tab row there. Then,
// from the About page, the Changes tab clicked (tapped on a phone): where it lands. With
// args.shots = {dir, tag} a PNG of each page's top.
//
// Result: { base, accent, accentText, pages: {path: …}, none: {path: bool}, clicked, shots }
import { open, base, args, run, done, sleep } from './cdp.js';

const COLOUR = v => `(() => { const s = document.createElement('span'); s.style.color = ${JSON.stringify(v)};
  document.body.appendChild(s); const c = getComputedStyle(s).color; s.remove(); return c; })()`;

const READ = `(() => {
  const nav = document.querySelector('nav.ordpar-tabs');
  const foot = document.querySelector('.ordpar-footer-nav a[href="/about/"]');
  const out = { status: 0, title: document.title, footAbout: foot ? foot.textContent : null,
    pageWide: document.documentElement.scrollWidth > innerWidth + 1, vw: innerWidth };
  if (!nav) { out.nav = null; return out; }
  const prev = nav.previousElementSibling, next = nav.nextElementSibling;
  const links = [...nav.querySelectorAll('a')];
  const tops = [...new Set(links.map(a => Math.round(a.getBoundingClientRect().top)))];
  const ul = nav.querySelector('ul');
  out.nav = { label: nav.getAttribute('aria-label'), cls: ul ? ul.className : '',
    after: prev ? prev.tagName : null, h1: prev && prev.tagName === 'H1' ? prev.textContent : null,
    before: next ? next.tagName : null, rows: tops.length,
    rowWide: nav.scrollWidth > nav.clientWidth + 1,
    tabs: links.map(a => { const r = a.getBoundingClientRect(), cs = getComputedStyle(a);
      return { text: a.textContent, href: a.getAttribute('href'), current: a.getAttribute('aria-current'),
        bg: cs.backgroundColor, color: cs.color, radius: cs.borderTopLeftRadius,
        left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), h: Math.round(r.height) }; }) };
  return out;
})()`;

async function shot(p, name) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const a = document.querySelector('.ordpar-about'); if (!a) return null;
    const r = a.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, w: r.width }; })()`);
  if (!box) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: Math.max(0, box.x - 8), y: Math.max(0, box.y - 8), width: box.w + 16, height: 260, scale: 1 } });
  const file = args.shots.dir + '/' + name + '-' + args.shots.tag + '.png';
  await Bun.write(file, Buffer.from(data, 'base64'));
  return file;
}

run(async () => {
  const p = await open({ w: args.w || 360, h: args.h || 740, mobile: !!args.mobile });
  await p.goto(base + '/about/', 300);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  const out = { base, pages: {}, none: {}, shots: [] };
  for (const path of args.pages) {
    const st = await p.eval(`fetch(${JSON.stringify(path)}).then(r => r.status)`);
    await p.goto(base + path, 400);
    const r = await p.eval(READ);
    r.status = st;
    out.pages[path] = r;
    out.shots.push(await shot(p, 'tabs' + path.replace(/\//g, '_')));
  }
  out.accent = await p.eval(COLOUR('var(--ordpar-accent)'));
  out.accentText = await p.eval(COLOUR('var(--ordpar-accent-text)'));
  for (const path of args.none) {
    await p.goto(base + path, 600);
    out.none[path] = await p.eval(`!!document.querySelector('nav.ordpar-tabs, .ordpar-tabs')`);
  }
  // a tab is a link: the Changes tab from About lands on /changes/, its own tab pressed there
  await p.goto(base + '/about/', 400);
  const at = await p.eval(`(() => { const a = document.querySelector('nav.ordpar-tabs a[href="/changes/"]'); if (!a) return null;
    a.scrollIntoView({ block: 'center' }); const r = a.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (at) {
    if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
    for (let t = 0; t < 50; t++) { await sleep(100); if ((await p.eval('location.pathname')) === '/changes/') break; }
    await sleep(300);
    out.clicked = await p.eval(`({ path: location.pathname,
      current: (document.querySelector('nav.ordpar-tabs a[aria-current="page"]') || {}).textContent || null })`);
  } else {
    out.clicked = null;
  }
  await done(out);
});
