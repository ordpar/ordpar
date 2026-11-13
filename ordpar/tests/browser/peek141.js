// Decisions 141 (Robin, 2026-10-26): a hover peek inside a small article is shown in full — not cut
// off by the mini's scrolling box — and kept inside the window; the mini keeps its size.
//
// For one viewport (args.w x args.h; args.mobile a phone with touch), in a fresh context, for each
// case of args.cases {name, page, path: [id, ...], hover, nest, theme, settings, toTop}: the page `page` is opened,
// the link to path[0] outside any mini clicked with the mouse (a real click: the sheet's
// pointer-events count), then each further id of `path` clicked inside the newest box (`nest`:
// the setting `nestminis`), then the pointer moved onto the link to `hover` inside the newest box
// and rested. Measured: the peek's box (its `display`, its rect), the window, every ancestor of
// the peek that clips (an `overflow` other than visible), the mini box's rect before and after the
// hover (its size must not change), whether the peek's rect lies inside the window, and whether
// nine points of it are painted as the peek (`document.elementFromPoint`, the peek made
// hit-testable for the moment): a point a scrolling ancestor clips does not hit it.
//
// Result: { base, cases: { <name>: { opened, boxes, shown, peek, win, clips: [{cls, rect, inside}],
//   inWindow, hits, fullyVisible, boxBefore, boxAfter, text } } }
import { open, base, args, run, done, sleep } from './cdp.js';

const HELP = `window.P141 = {
  vis: a => a && a.getClientRects().length && getComputedStyle(a).pointerEvents !== 'none',
  link(root, id) {
    return [...root.querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && P141.vis(a))[0] || null;
  },
  page(id) { return [...document.querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => !a.closest('.ordbok-xmini') && (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && P141.vis(a))[0] || null; },
  newest() { const ms = [...document.querySelectorAll('.ordbok-xmini')].filter(m => m.getClientRects().length);
    return ms[ms.length - 1] || null; },
  r(e) { const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height }; },
  point(a) { a.scrollIntoView({ block: 'center' }); const r = a.getClientRects()[0]; return { x: r.left + Math.min(r.width / 2, 12), y: r.top + r.height / 2 }; },
};
true`;

async function mouse(p, x, y, click = true) {
  await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  if (!click) return;
  await p.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await p.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
}

async function waitBody(p, n) {
  return p.eval(`(async () => { for (let t = 0; t < 80; t++) {
    const ms = [...document.querySelectorAll('.ordbok-xmini')].filter(m => m.getClientRects().length);
    const m = ms[ms.length - 1];
    if (ms.length >= ${n} && m && m.querySelector('.ordpar-mbody') && !m.querySelector('[aria-busy=true]')) break;
    await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 250)); return true; })()`);
}

run(async () => {
  const p = await open({ w: args.w || 1280, h: args.h || 900, mobile: !!args.mobile });
  const cases = {};
  await p.goto(base + '/bm-en/', 300);
  for (const c of args.cases) {
    await p.eval(`localStorage.clear(); localStorage.setItem('theme', '${c.theme || 'light'}');
      ${c.nest ? `localStorage.setItem('nestminis', '${c.nest}');` : ''}
      ${Object.entries(c.settings || {}).map(([k, v]) => `localStorage.setItem('${k}', '${v}');`).join(' ')} true`);
    await p.goto(base + '/bm-en/' + c.page + '/', 700);
    await p.eval(HELP);
    const out = { opened: false };
    cases[c.name] = out;
    let pt = await p.eval(`(() => { const a = P141.page(${c.path[0]}); return a ? P141.point(a) : null; })()`);
    if (!pt) { out.error = 'no link to ' + c.path[0] + ' on ' + c.page; continue; }
    await sleep(150); await mouse(p, pt.x, pt.y); await waitBody(p, 1);
    let ok = true;
    for (let i = 1; i < c.path.length; i++) {
      pt = await p.eval(`(() => { const a = P141.link(P141.newest(), ${c.path[i]}); return a ? P141.point(a) : null; })()`);
      if (!pt) { out.error = 'no link to ' + c.path[i] + ' in the box'; ok = false; break; }
      await sleep(150); await mouse(p, pt.x, pt.y); await sleep(300);
      // a link the page's mini.js does not open in a box navigates (nesting off, or a build before 139)
      if (!(await p.eval(`typeof window.P141 !== 'undefined'`))) { out.error = 'the click on ' + c.path[i] + ' left the page'; ok = false; break; }
      // boxes open: stacked one per link; `second` (decisions 147) a second box, then steps in it
      await waitBody(p, Math.min(i + 1, c.nest === 'stacked' ? 99 : c.nest === 'second' ? 2 : 1));
    }
    if (!ok) continue;
    out.boxes = await p.eval(`document.querySelectorAll('.ordbok-xmini').length`);
    out.opened = true;
    // `toTop`: the page scrolled so the box's top is 4 px below the window's (room above the word
    // too small: the peek goes below it)
    if (c.toTop) {
      await p.eval(`(() => { const m = P141.newest().querySelector('.ordpar-fmini');
        document.body.style.paddingBottom = '150vh';           // a short page: room to scroll
        window.scrollBy(0, m.getBoundingClientRect().top - 4); return true; })()`);
      await sleep(200);
    }
    // the link to hover, in the newest box; the pointer first parked off every link
    pt = await p.eval(`(() => { const a = P141.link(P141.newest(), ${c.hover}); if (!a) return null;
      const m = P141.newest().querySelector('.ordpar-fmini'); const r = a.getClientRects()[0];
      // into view inside its own box, not by scrolling the page past the box
      if (r.top < m.getBoundingClientRect().top || r.bottom > m.getBoundingClientRect().bottom) a.scrollIntoView({ block: 'nearest' });
      const q = a.getClientRects()[0]; window.P141.box = P141.r(m); return { x: q.left + Math.min(q.width / 2, 12), y: q.top + q.height / 2 }; })()`);
    if (!pt) { out.error = 'no link to ' + c.hover + ' in the newest box'; continue; }
    await mouse(p, 2, 2, false); await sleep(100);
    await mouse(p, pt.x, pt.y, false); await sleep(400); await p.frames();
    Object.assign(out, await p.eval(`(() => {
      const a = P141.link(P141.newest(), ${c.hover}), x = a.parentNode, pk = x.querySelector(':scope > .ordbok-xpeek');
      if (!pk) return { shown: false, why: 'no peek' };
      const cs = getComputedStyle(pk), shown = cs.display !== 'none' && pk.getClientRects().length > 0;
      const pr = P141.r(pk), W = document.documentElement.clientWidth, H = document.documentElement.clientHeight;
      const clips = [];
      for (let e = pk.parentElement; e && e !== document.documentElement; e = e.parentElement) {
        const s = getComputedStyle(e);
        if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
          const er = P141.r(e);
          clips.push({ cls: e.className, rect: er, inside: pr.l >= er.l - 0.5 && pr.r <= er.r + 0.5 && pr.t >= er.t - 0.5 && pr.b <= er.b + 0.5 });
        }
        if (s.position === 'fixed') break;     // a fixed ancestor: nothing above it clips what it holds
      }
      const inWindow = pr.l >= -0.5 && pr.t >= -0.5 && pr.r <= W + 0.5 && pr.b <= H + 0.5;
      // what is painted: the peek made hit-testable for a moment, then nine points of it asked
      // (2 px inside each corner, each edge's middle, the centre) — a point a scrolling ancestor
      // clips, or another box covers, does not hit the peek
      const old = pk.style.pointerEvents; pk.style.pointerEvents = 'auto';
      const xs = [pr.l + 2, (pr.l + pr.r) / 2, pr.r - 2], ys = [pr.t + 2, (pr.t + pr.b) / 2, pr.b - 2];
      const hits = [];
      for (const y of ys) for (const xx of xs) { const e = document.elementFromPoint(xx, y); hits.push(!!e && (e === pk || pk.contains(e))); }
      pk.style.pointerEvents = old;
      const m = P141.newest().querySelector('.ordpar-fmini');
      return { shown, display: cs.display, below: pk.classList.contains('ordpar-pbelow'), word: P141.r(x), position: cs.position, peek: pr, win: { w: W, h: H }, clips, inWindow,
        hits, fullyVisible: shown && inWindow && hits.every(Boolean), boxBefore: P141.box, boxAfter: P141.r(m),
        text: pk.textContent.slice(0, 80), pointer: [${pt.x}, ${pt.y}] };
    })()`));
    if (args.shots && c.shot) {
      const { data } = await p.send('Page.captureScreenshot', { format: 'png' });
      out.shot = data.length;
      await Bun.write(args.shots + '/' + c.shot + '.png', Buffer.from(data, 'base64'));
    }
  }
  done({ base, cases });
});
