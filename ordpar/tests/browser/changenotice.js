// Decisions 106: the change notice at the card's foot, as the browser draws it.
//
// For one viewport (args.w × args.h, args.mobile; args.dark for the dark theme), in a fresh
// context: the article page of a corrected article (args.article) — the foot's children in order
// (the page script's controls, then the notice), the heart among the controls, the notice's text,
// link and colour against the muted colour, and whether it stays inside the card; an article
// without a notice (args.plain); a full search result (args.single, a query finding one article,
// args.single_id) and an opened list-view row (args.list, its row args.list_id) — the notice
// after the result's controls. With args.shots = {dir, prefix} it saves a screenshot of each
// card's foot (the review's pictures; `Page.captureScreenshot`).
//
// Result: { article: {...}, plain: {...}, single: {...}, list: {...} }
import { open, base, args, run, done, sleep } from './cdp.js';
import { writeFileSync } from 'fs';

async function until(p, expr, ms = 8000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

// what a host (the article card, a result, an opened row) shows at its foot
const READ = host => `(() => {
  const host = ${host};
  if (!host) return { missing: true };
  const n = host.querySelector('.ordpar-change');
  const ctl = host.querySelector('.ordpar-result-controls');
  const card = host.closest('.ordpar-card, .ordpar-entry, .ordpar-row-panel, article') || host;
  const muted = getComputedStyle(document.documentElement).getPropertyValue('--ordpar-muted').trim();
  const probe = document.createElement('span'); probe.style.color = muted; document.body.appendChild(probe);
  const mutedRgb = getComputedStyle(probe).color; probe.remove();
  const out = { notices: host.querySelectorAll('.ordpar-change').length, controls: !!ctl,
    heart: !!(ctl && ctl.querySelector('.ordpar-heart, .ordpar-result-heart')) };
  if (n) {
    const r = n.getBoundingClientRect(), c = card.getBoundingClientRect();
    const a = n.querySelector('a');
    // site decisions 152: the words as drawn (the Norwegian copies ship hidden beside them)
    out.text = n.innerText.replace(/\\s+/g, ' ').trim();
    out.href = a && a.getAttribute('href');
    out.colour = getComputedStyle(n).color; out.muted = mutedRgb;
    out.linkColour = a && getComputedStyle(a).color;
    out.inside = r.left >= c.left - 0.5 && r.right <= c.right + 0.5;
    out.overflow = n.scrollWidth > n.clientWidth + 1;
    out.afterControls = !!(ctl && (ctl.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING));
    out.lines = Math.round(r.height / parseFloat(getComputedStyle(n).lineHeight));
    out.scrollX = document.documentElement.scrollWidth > document.documentElement.clientWidth;
  }
  return out;
})()`;

async function shot(p, name, selector) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)});
    if (!e) return null; e.scrollIntoView({ block: 'center' }); const r = e.getBoundingClientRect();
    return { x: Math.max(0, r.left - 12), y: Math.max(0, r.top + scrollY - 12), w: r.width + 24, h: r.height + 24 }; })()`);
  if (!box) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 } });
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

run(async () => {
  const p = await open({ w: args.w, h: args.h, mobile: !!args.mobile });
  const res = {};
  await p.goto(base + '/', 300);
  await p.eval(`localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);

  await p.goto(base + '/bm-en/' + args.article + '/', 400);
  await until(p, `!!document.querySelector('.ordpar-card-foot .ordpar-result-controls')`);
  await sleep(300);
  res.article = await p.eval(READ(`document.querySelector('.ordpar-card-foot')`));
  res.article.order = await p.eval(`[...document.querySelector('.ordpar-card-foot').children].map(e => e.className)`);
  res.article.night = await p.eval(`document.documentElement.classList.contains('nightMode')`);
  res.article.shot = await shot(p, 'article', '.ordpar-card');

  if (args.several) {
    await p.goto(base + '/bm-en/' + args.several + '/', 400);
    await until(p, `!!document.querySelector('.ordpar-card-foot .ordpar-result-controls')`);
    res.several = await p.eval(READ(`document.querySelector('.ordpar-card-foot')`));
    res.several.shot = await shot(p, 'several', '.ordpar-card-foot');
  }

  await p.goto(base + '/bm-en/' + args.plain + '/', 400);
  await until(p, `!!document.querySelector('.ordpar-card-foot .ordpar-result-controls')`);
  res.plain = await p.eval(READ(`document.querySelector('.ordpar-card-foot')`));

  await p.eval(`localStorage.setItem('listview', 'multi'); true`);
  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.single), 400);
  await until(p, `!!document.querySelector('.ordpar-hits .ordpar-result-controls')`);
  await sleep(400);
  res.single = await p.eval(READ(`document.querySelector('.ordpar-hits [data-id="${args.single_id}"], .ordpar-hits')`));
  res.single.shot = await shot(p, 'search', '.ordpar-hits [data-id="' + args.single_id + '"]');

  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.list), 400);
  await until(p, `!!document.getElementById('r${args.list_id}-row')`);
  await p.eval(`document.getElementById('r${args.list_id}-row').click(); true`);
  await until(p, `!!document.querySelector('#r${args.list_id}-panel .ordpar-result-controls')`);
  await sleep(400);
  res.list = await p.eval(READ(`document.getElementById('r${args.list_id}-panel')`));
  res.list.shot = await shot(p, 'listrow', '#r' + args.list_id + '-panel');
  await done({ base, ...res });
});
