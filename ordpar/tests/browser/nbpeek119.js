// Decisions 119 (Robin, 2026-10-24): a Norwegian-only article's links carry their target's English.
//
// In a fresh context (the site's defaults), at args.w × 900 with a mouse, for each case in
// args.cases ({ page, href }): the article page is opened, the first link to `href` in the article
// (outside any mini) scrolled to the middle and hovered with the mouse, and its peek read as the
// reader sees it — shown or not, its text (`innerText`, so a `<br>` is a line break), its computed
// weight, its width, its line count (its height over its line height) and whether it stays inside
// the window. Then the link is clicked and the opened mini's header read (`.mini-head`'s text,
// without the headword's sound icon, decisions 159).
// For each of args.inMini ({ page, href, inner }): the mini of `href` opened on `page`, and inside
// it the link to `inner` read — its peek's text (not hovered: the mini's own links are read as
// cut from the target's page).
//
// args: { w, cases: [{ page, href }], inMini: [{ page, href, inner }] }
// Result: { base, w, cases: [{ page, href, found, peek: null | { shown, text, weight, width, lines,
//   left, right, vw, cls }, head }], inMini: [{ page, href, inner, opened, found, peek }] }
import { open, base, args, run, done, sleep } from './cdp.js';

const FIND = (href, root) => `[...${root}.querySelectorAll('a.ordbok-xword')].find(a => a.getAttribute('href') === ${JSON.stringify(href)} && ${root === 'document' ? "!a.closest('.ordbok-xmini')" : 'true'})`;
const MINI = "[...document.querySelectorAll('.ordpar-mopen > .ordbok-xmini')].find(x => x.getClientRects().length)";

async function openMini(p, href) {
  return p.eval(`(async () => {
    const a = ${FIND(href, 'document')};
    if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 80; t++) { if (document.querySelector('.ordpar-mopen .ordpar-mbody .ordbok-def')) break;
      await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 300));
    return !!(${MINI}); })()`);
}

run(async () => {
  const w = args.w || 1280;
  const p = await open({ w, h: 900 });
  await p.goto(base + '/bm-en/', 400);
  await p.eval('localStorage.clear(); true');
  const cases = [];
  for (const c of args.cases || []) {
    await p.goto(base + '/bm-en/' + c.page + '/', 600);
    const pos = await p.eval(`(() => {
      const a = ${FIND(c.href, 'document')};
      if (!a) return null;
      a.scrollIntoView({ block: 'center' });
      const r = a.getClientRects()[0];
      return { x: r.left + Math.min(8, r.width / 2), y: (r.top + r.bottom) / 2 };
    })()`);
    if (!pos) { cases.push({ ...c, found: false }); continue; }
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 1, y: 1 });
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pos.x, y: pos.y });
    await sleep(250);
    const peek = await p.eval(`(() => {
      const a = ${FIND(c.href, 'document')};
      const x = a.parentNode;
      const k = [...x.children].find(e => e.classList.contains('ordbok-xpeek'));
      if (!k) return null;
      const cs = getComputedStyle(k), r = k.getBoundingClientRect();
      const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
      const inner = r.height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      return { shown: cs.display !== 'none' && r.width > 0, text: k.innerText, weight: cs.fontWeight,
               width: r.width, lines: Math.round(inner / lh), left: r.left, right: r.right, vw: innerWidth,
               rem: parseFloat(getComputedStyle(document.documentElement).fontSize), cls: k.className };
    })()`);
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 1, y: 1 });
    const opened = await openMini(p, c.href);
    // the header's words as a reader sees them: the headword's sound icon (decisions 159) and its
    // hidden "Play" / "Spill av" left out
    const head = opened ? await p.eval(`(() => { const m = ${MINI}; const h = m && m.querySelector('.mini-head');
      if (!h) return null; const c = h.cloneNode(true); c.querySelectorAll('.ordpar-play').forEach(b => b.remove());
      return c.textContent.replace(/\\s+/g, ' ').trim(); })()`) : null;
    cases.push({ ...c, found: true, peek, opened, head });
  }
  const inMini = [];
  for (const c of args.inMini || []) {
    await p.goto(base + '/bm-en/' + c.page + '/', 600);
    const opened = await openMini(p, c.href);
    const got = opened ? await p.eval(`(() => {
      const m = ${MINI};
      const a = m && ${FIND(c.inner, 'm')};
      if (!a) return { found: false };
      const k = [...a.parentNode.children].find(e => e.classList.contains('ordbok-xpeek'));
      return { found: true, peek: k ? k.textContent : null };
    })()`) : {};
    inMini.push({ ...c, opened, ...got });
  }
  await done({ base, w, cases, inMini });
});
