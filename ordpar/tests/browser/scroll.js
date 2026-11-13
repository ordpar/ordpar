// Decisions 91 / 100 (3): opening a mini by a tap on a phone does not move the page.
//
// A phone (390×844, DPR 3, touch, a phone's user agent); each case loads an article, scrolls
// (to the page's end, or the link to mid-screen), taps a cross-reference link with a touch, and
// records scrollY on every frame for 1.5 s. Before 91's fix `place()` measured a mini near the
// right edge where it overhung, the page widened for a frame and the browser scrolled; the
// reproduction is `../../../docs/sessions/2026-09-19-ordpar-site-review/evidence/fixes-91-2026-10-22/scripts/tap.js`.
//
// args: { cases: [{ label, id, text, at: 'end' | 'mid', emph?: 'no' | 'en' }] }
//   `text` the link's text; the first visible, live `.ordbok-xref > a.ordbok-xword` with it is tapped.
//   `emph` sets that setting first: 'no' the Norwegian line's links live, as 91's diagnosis ran; 'en'
//   the English line's (the default until site decisions 174, so named since).
// Result: { W, cases: [{ label, maxY, before, after, frames: [distinct scrollY], linkX, mini: [l, r, t, b] | null }] }
import { open, base, args, run, done, sleep } from './cdp.js';

run(async () => {
  const W = 390, H = 844;
  const p = await open({ w: W, h: H, mobile: true });
  const out = [];
  for (const c of args.cases) {
    const url = base + '/bm-en/' + c.id + '/';
    await p.goto(url, 200);
    await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light');
      ${c.emph ? `localStorage.setItem('emph', ${JSON.stringify(c.emph)});` : ''} true`);
    await p.goto(url, 800);
    const s0 = await p.eval(`(() => { document.documentElement.style.scrollBehavior = 'auto';
      const E = document.documentElement, maxY = E.scrollHeight - innerHeight;
      const a = [...document.querySelectorAll('.ordbok-xref > a.ordbok-xword')].find(a => a.textContent === ${JSON.stringify(c.text)}
        && a.getClientRects().length && getComputedStyle(a).pointerEvents !== 'none');
      if (!a) return null;
      window.__a = a;
      const top = a.getBoundingClientRect().top + scrollY;
      scrollTo(0, ${c.at === 'end' ? 'maxY' : 'Math.max(0, Math.min(maxY, top - innerHeight / 2))'});
      return { maxY }; })()`);
    if (!s0) { out.push({ label: c.label, missing: true }); continue; }
    await sleep(400);
    const pt = await p.eval(`(() => { const r = window.__a.getClientRects()[0];
      return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2, sy: scrollY }; })()`);
    await p.eval(`(() => { window.__sy = []; const t0 = performance.now();
      const f = () => { window.__sy.push(Math.round(scrollY * 100) / 100); if (performance.now() - t0 < 1500) requestAnimationFrame(f); };
      requestAnimationFrame(f); return true; })()`);
    await p.tap(pt.x, pt.y);
    await sleep(1700);
    const s1 = await p.eval(`(() => { const m = [...document.querySelectorAll('.ordpar-mopen > .ordbok-xmini')].find(m => m.getClientRects().length);
      const q = m && m.getBoundingClientRect();
      return { sy: scrollY, mini: q ? [Math.round(q.left), Math.round(q.right), Math.round(q.top), Math.round(q.bottom)] : null,
               frames: [...new Set(window.__sy)] }; })()`);
    out.push({ label: c.label, maxY: s0.maxY, before: pt.sy, after: s1.sy, frames: s1.frames, linkX: Math.round(pt.x), mini: s1.mini });
  }
  await done({ base, W, cases: out });
});
