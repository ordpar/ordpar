// Site decisions 165 (Robin, 2026-11-04: "Yes, open it above"): a nested small article is kept inside
// the window. A nested box is `position: fixed`, so the page cannot be scrolled to it; until 165 it
// always opened below its word, at least 160 px tall, and ran past the window's bottom when its word
// sat near it. Now it opens above its word when the room below is short and there is more above.
//
// For one viewport (args.w x args.h; args.mobile a phone with touch), in a fresh context, each case
// in args.cases ({ name, mode, at }): the page padded above and below so it can be scrolled anywhere,
// the setting `nestminis` = mode (null: nothing saved, the default `second`), the first box opened
// from the page's word (args.ids.skip on args.ids.bat) by a real click, its link to args.ids.two
// brought into view in the first box (the box's own scroll where it scrolls) and the page scrolled
// so that the link stands where `at` says — `low`: its bottom args.low px (default 70) above the
// window's bottom; `high`: its top 120 px from the window's top — then clicked (a real click). Read
// once the nested box has its content and has settled:
//   word    the link's first line box {top, bottom}
//   box     the nested `.mini` {top, bottom, left, right}; mini the `.ordbok-xmini` around it
//   above   the box ends above the word (box.bottom <= word.top); below: box.top >= word.bottom
//   inside  the box wholly inside the window (top >= 0, bottom <= innerHeight)
//   scrolls the box scrolls inside itself; kept: where it scrolls, its own scrollTop set to 30 and
//           a page-scroll event later still 30 (the placing never resets it)
//   later   the same read again after 600 ms (a late height change placed again)
//
// Result: { base, vh, cases: { <name>: {...} } }; args.shots (a folder) also writes PNGs.
import { open, base, args, run, done, sleep } from './cdp.js';

const I = args.ids;
const HELP = `window.H = {
  vis: a => !!a && a.getClientRects().length > 0 && getComputedStyle(a).pointerEvents !== 'none',
  link(root, id) { if (!root) return null;
    return [...root.querySelectorAll(':scope > .mini .ordbok-xref > a.ordbok-xword')]
      .filter(a => (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && H.vis(a))[0] || null; },
  page(id) { return [...document.querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => !a.closest('.ordbok-xmini') && (a.getAttribute('href') || '').indexOf('/bm-en/' + id + '/') === 0 && H.vis(a))[0] || null; },
  minis() { return [...document.querySelectorAll('.ordbok-xmini')].filter(m => m.getClientRects().length); },
  box(n) { return H.minis()[n] || null; },
  inner(m) { return m ? m.querySelector(':scope > .mini') : null; },
  busy() { return H.minis().some(m => !!m.querySelector(':scope > .mini[aria-busy=true]')); },
  rect(n) { const r = n.getBoundingClientRect();
    return { top: Math.round(r.top * 10) / 10, bottom: Math.round(r.bottom * 10) / 10,
      left: Math.round(r.left), right: Math.round(r.right) }; },
  read(a) {
    const m = H.box(1), b = H.inner(m), w = a.getClientRects()[0];
    const word = { top: Math.round(w.top * 10) / 10, bottom: Math.round(w.bottom * 10) / 10 };
    const box = H.rect(b), mini = H.rect(m);
    return { word, box, mini, vh: innerHeight, nest: m.classList.contains('ordpar-mnest'),
      hidden: m.style.visibility === 'hidden', head: (b.querySelector('.mini-head .mini-hw') || {}).textContent || null,
      above: box.bottom <= word.top + 0.5, below: box.top >= word.bottom - 0.5,
      inside: box.top >= -0.5 && box.bottom <= innerHeight + 0.5 && mini.top >= -0.5 && mini.bottom <= innerHeight + 0.5,
      scrolls: b.scrollHeight > b.clientHeight + 1, maxHeight: b.style.maxHeight };
  },
};
true`;

let p;
const E = s => p.eval(s);
async function mouse(x, y) {
  await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await p.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await p.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
}
async function settle(n) {
  for (let t = 0; t < 80; t++) {
    const k = await E(`H.minis().length`);
    if (k === n && !(await E(`H.busy()`))) break;
    await sleep(100);
  }
  await sleep(400);
}
async function shot(name) {
  if (!args.shots) return;
  await sleep(200);
  const { data } = await p.send('Page.captureScreenshot', { format: 'png' });
  await Bun.write(args.shots + '/' + name + '.png', Buffer.from(data, 'base64'));
}
async function clickAt(expr) {
  const pt = await E(`(() => { const a = ${expr}; if (!a) return null; const r = a.getClientRects()[0];
    return { x: r.left + Math.min(r.width / 2, 12), y: r.top + r.height / 2 }; })()`);
  if (!pt) throw new Error('nothing to click: ' + expr);
  await mouse(pt.x, pt.y);
}

async function one(c) {
  await E(`localStorage.clear(); localStorage.setItem('theme', 'light');
    ${c.mode ? `localStorage.setItem('nestminis', '${c.mode}');` : ''} true`);
  await p.goto(base + '/bm-en/' + I.bat + '/', 700);
  await E(HELP);
  const out = { mode: await E(`window.ordparMinis && window.ordparMinis.nestMode ? window.ordparMinis.nestMode() : null`) };
  // room to scroll the page anywhere: padding above and below the article
  await E(`document.body.style.paddingTop = '1500px'; document.body.style.paddingBottom = '1500px'; true`);
  await E(`(() => { const a = H.page(${I.skip}); const r = a.getClientRects()[0]; window.scrollBy(0, r.top - 200); return true; })()`);
  await sleep(250);
  await clickAt(`H.page(${I.skip})`); await settle(1);
  const LINK = `H.link(H.box(0), ${I.two})`;
  // the link shown in the first box (its own scroll, where it scrolls), then the page scrolled so it
  // stands where the case says
  await E(`(() => { const a = ${LINK}; if (!a) return false; const b = a.closest('.mini');
    if (b && b.scrollHeight > b.clientHeight + 1) {
      const r = a.getClientRects()[0], br = b.getBoundingClientRect();
      b.scrollTop += r.top - br.top - 40;
    } return true; })()`);
  await sleep(150);
  const low = args.low || 70;
  await E(`(() => { const a = ${LINK}; const r = a.getClientRects()[0];
    window.scrollBy(0, ${c.at === 'low' ? `r.bottom - (innerHeight - ${low})` : 'r.top - 120'}); return true; })()`);
  await sleep(300);
  out.before = await E(`(() => { const a = ${LINK}; const r = a.getClientRects()[0];
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), roomBelow: Math.round(innerHeight - r.bottom) }; })()`);
  await clickAt(LINK); await settle(2);
  out.n = await E(`H.minis().length`);
  if (out.n < 2) throw new Error(c.name + ': no nested box opened');
  out.first = await E(`H.read(${LINK})`);
  await shot((args.shotPrefix || '') + c.name);
  // the box's own scroll survives a placing (a page-scroll event places it again)
  if (out.first.scrolls) {
    await E(`H.inner(H.box(1)).scrollTop = 30; window.dispatchEvent(new Event('scroll')); true`);
    await sleep(200);
    out.kept = await E(`H.inner(H.box(1)).scrollTop`);
  }
  await sleep(600);
  out.later = await E(`H.read(${LINK})`);
  // Robin, 2026-11-04: "if they opened above to begin with, they stay above" — the page scrolled
  // until the word has more room below than above (where a fresh placing would turn it below)
  if (out.later.above) {
    await E(`(() => { const a = ${LINK}; const r = a.getClientRects()[0];
      window.scrollBy(0, r.top - Math.round(innerHeight * 0.35)); return true; })()`);
    await sleep(400);
    out.scrolled = await E(`(() => { const a = ${LINK}; const r = a.getClientRects()[0];
      return Object.assign(H.read(a), { roomAbove: Math.round(r.top), roomBelow: Math.round(innerHeight - r.bottom) }); })()`);
  }
  return out;
}

run(async () => {
  p = await open({ w: args.w || 1280, h: args.h || 900, mobile: !!args.mobile });
  await p.goto(base + '/bm-en/' + I.bat + '/', 300);       // a page of the site's own, for its localStorage
  const cases = {};
  for (const c of args.cases) cases[c.name] = await one(c);
  done({ base, vh: await E(`innerHeight`), cases });
});
