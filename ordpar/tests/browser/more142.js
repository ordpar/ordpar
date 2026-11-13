// Site-review decisions 142 (Robin, 2026-10-26/27): "More ways to use Ordpar" in a browser.
//
// For one viewport (args.w × args.h, args.mobile; args.dark for the dark theme), in a fresh context:
//   home     — `/`: the line under Random word (the main's first thing shown, below the header), its
//              words, the link on "more ways to use Ordpar" to /more/; no "Type a Norwegian word…"
//              anywhere and the results area empty (no box, no height); the search box and Random
//              word where they are without the line (the line only in the main, not the header);
//   search   — a search made from the box (Search pressed): the line hidden;
//   random   — Random word pressed on `/`: the line hidden;
//   follow   — the line's link clicked (tapped on a phone): /more/ opens;
//   more     — /more/: its footer's links in order, "More ways to use Ordpar" right after Help and
//              marked the current page (aria-current); the footer's rows (the phone's wrap);
//   anki     — /more/#anki opened: the section's heading scrolled into view;
//   code     — a click on each code line: the selection is the whole line;
//   empty    — `/bm-en/` with no search, and a missing page (404): no "Type a Norwegian word…".
// With args.shots = {dir, prefix}: the home page's top, /more/'s top, its Anki section and the
// footer, as PNGs.
//
// args: { w, h, mobile, dark, shots }   Result: { base, home, search, random, follow, more, anki, code, empty }
import { writeFileSync } from 'node:fs';
import { open, base, args, run, done, sleep } from './cdp.js';

const DROPPED = 'Type a Norwegian word to search the dictionary.';

async function until(p, expr, ms = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await p.eval(`!!(${expr})`)) return true;
    await sleep(100);
  }
  return false;
}

async function shot(p, name, full) {
  if (!args.shots) return null;
  await p.frames();
  const opts = { format: 'png' };
  if (full) {
    const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(full)});
      if (!e) return null; const r = e.getBoundingClientRect();
      return { x: 0, y: Math.max(0, r.top + scrollY), w: innerWidth, h: r.height }; })()`);
    if (box) { opts.captureBeyondViewport = true; opts.clip = { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 }; }
  }
  const { data } = await p.send('Page.captureScreenshot', opts);
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

async function press(p, selector) {
  const r = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)});
    if (!e) return null; e.scrollIntoView({ block: 'center' }); const b = e.getBoundingClientRect();
    return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; })()`);
  if (!r) return false;
  await p.frames();
  if (args.mobile) await p.tap(r.x, r.y); else await p.click(r.x, r.y);
  return true;
}

const SHOWN = `(() => { const l = document.querySelector('.ordpar-more-line');
  return !!l && getComputedStyle(l).display !== 'none' && l.getBoundingClientRect().height > 0; })()`;

run(async () => {
  const p = await open({ w: args.w, h: args.h, mobile: !!args.mobile });
  const res = {};
  await p.goto(base + '/', 300);
  await p.eval(`localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  await p.goto(base + '/', 500);
  await until(p, SHOWN);

  res.home = await p.eval(`(() => {
    const l = document.querySelector('.ordpar-more-line'), a = l && l.querySelector('a');
    const main = document.getElementById('ordpar-main'), res = main.querySelector('[data-ordpar-results]');
    const hdr = document.querySelector('.ordpar-header').getBoundingClientRect();
    const rnd = document.querySelector('.ordpar-random'), box = document.getElementById('ordpar-q');
    const visible = [...main.children].filter(e => !e.classList.contains('ordpar-visually-hidden') && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0);
    const rect = e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
    const lr = l ? l.getBoundingClientRect() : null;
    return { night: document.documentElement.classList.contains('nightMode'),
      shown: ${SHOWN}, text: l ? l.textContent : null,
      link: a ? { text: a.textContent, href: a.getAttribute('href'), underline: getComputedStyle(a).textDecorationLine,
                  color: getComputedStyle(a).color } : null,
      linkOnly: a ? l.textContent.slice(0, l.textContent.length - a.textContent.length) : null,
      color: l ? getComputedStyle(l).color : null, muted: getComputedStyle(document.documentElement).getPropertyValue('--ordpar-muted').trim(),
      firstShown: visible.length ? visible[0].className : null,
      inHeader: !!(l && l.closest('header')),
      belowHeader: lr ? lr.top >= hdr.bottom - 1 : null,
      belowRandom: lr && rnd ? lr.top >= rnd.getBoundingClientRect().bottom - 1 : null,
      // lined up with the header's column (Robin, 2026-10-27): the brand's left edge
      lineLeft: lr ? Math.round(lr.left) : null, columnLeft: Math.round(document.querySelector('.ordpar-brand').getBoundingClientRect().left),
      resultsEmpty: res.children.length === 0, resultsHeight: res.getBoundingClientRect().height,
      dropped: document.body.innerText.includes(${JSON.stringify(DROPPED)}),
      boxRect: rect(box), randomRect: rnd ? rect(rnd) : null, lineRect: lr ? rect(l) : null };
  })()`);
  res.home.shot = await shot(p, 'home');
  // the header without the line: the search box and Random word stay where they are
  res.home.without = await p.eval(`(() => {
    const main = document.getElementById('ordpar-main'); main.classList.remove('ordpar-idle');
    const rect = e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
    const out = { boxRect: rect(document.getElementById('ordpar-q')),
      randomRect: document.querySelector('.ordpar-random') ? rect(document.querySelector('.ordpar-random')) : null };
    main.classList.add('ordpar-idle'); return out; })()`);

  // a search from the box hides it
  await p.eval(`(() => { const b = document.getElementById('ordpar-q'); b.value = 'hus';
    b.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await press(p, '.ordpar-submit');
  const answered = await until(p, `document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-result')`);
  await sleep(200);
  res.search = { answered, shown: await p.eval(SHOWN), path: await p.eval('location.pathname') };

  // Random word on the home page hides it
  await p.goto(base + '/', 500);
  await until(p, SHOWN);
  const before = await p.eval(SHOWN);
  await press(p, '.ordpar-random');
  const drawn = await until(p, `document.querySelector('[data-ordpar-results]') && document.querySelector('[data-ordpar-results]').children.length && !document.querySelector('[data-ordpar-results] > .ordpar-empty')`);
  await sleep(200);
  res.random = { before, drawn, shown: await p.eval(SHOWN) };

  // the link opens /more/
  await p.goto(base + '/', 500);
  await until(p, SHOWN);
  const loaded = p.waitEvent('Page.loadEventFired');
  await press(p, '.ordpar-more-line a');
  await loaded; await sleep(400);
  res.follow = { path: await p.eval('location.pathname'), title: await p.eval('document.title') };

  // /more/: the footer
  res.more = await p.eval(`(() => {
    const nav = document.querySelector('.ordpar-footer-nav');
    const links = [...nav.querySelectorAll('a')].filter(a => getComputedStyle(a).display !== 'none');
    const tops = [...new Set(links.map(a => Math.round(a.getBoundingClientRect().top)))];
    const m = nav.querySelector('a[href="/more/"]');
    return { links: links.map(a => a.textContent), current: m ? m.getAttribute('aria-current') : null,
      currentAll: [...nav.querySelectorAll('a[aria-current]')].map(a => a.textContent), rows: tops.length,
      rowOf: Object.fromEntries(links.map(a => [a.textContent, tops.indexOf(Math.round(a.getBoundingClientRect().top))])),
      ids: [...document.querySelectorAll('.ordpar-about h2[id]')].map(h => h.id),
      steps: [...document.querySelectorAll('.ordpar-about ol')].map(o => o.children.length) };
  })()`);
  res.more.shotTop = await shot(p, 'more-top');
  await p.eval(`document.querySelector('footer').scrollIntoView({ block: 'end' }); true`);
  res.more.shotFooter = await shot(p, 'footer', 'footer');

  // /more/#anki
  await p.goto(base + '/more/#anki', 600);
  res.anki = await p.eval(`(() => { const h = document.getElementById('anki'), r = h.getBoundingClientRect();
    return { top: r.top, vh: innerHeight, y: scrollY, ymax: document.documentElement.scrollHeight - innerHeight, text: h.textContent }; })()`);
  res.anki.shot = await shot(p, 'more-anki');

  // a click on a code line selects it whole
  res.code = [];
  const n = await p.eval(`document.querySelectorAll('.ordpar-code code').length`);
  for (let i = 0; i < n; i++) {
    await p.eval(`getSelection().removeAllRanges(); true`);
    await press(p, '.ordpar-code code:not([data-done])');
    await sleep(150);
    res.code.push(await p.eval(`(() => { const c = document.querySelectorAll('.ordpar-code code')[${i}];
      const s = getSelection().toString(); c.setAttribute('data-done', ''); return { text: c.textContent, selected: s,
      userSelect: getComputedStyle(c).userSelect || getComputedStyle(c).webkitUserSelect }; })()`));
  }

  // the dropped line nowhere: the search page with no search, a missing page
  res.empty = {};
  for (const [name, path] of [['search', '/bm-en/'], ['notfound', '/no-such-page/']]) {
    await p.goto(base + path, 700);
    res.empty[name] = await p.eval(`({ dropped: document.body.innerText.includes(${JSON.stringify(DROPPED)}),
      empties: document.querySelectorAll('.ordpar-empty').length,
      line: !!document.querySelector('.ordpar-more-line') })`);
  }
  await done({ base, ...res });
});
