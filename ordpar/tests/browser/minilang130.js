// Site decisions 130 (2026-10-25): the mini's header carries its own language tags.
//
// In one fresh context (the site's defaults), with every request delayed by args.latency ms (CDP
// `Network.emulateNetworkConditions`), for each case in args.cases ({ name, page, find, unpeek }):
// the article page is opened, the link `find` selects (a JS expression over `document`, outside
// any mini) scrolled to the middle and clicked; in the same task as the click (so before the
// target's article can have arrived) the header is read once — `busy` — and again once the mini's
// body is in (`aria-busy` gone) — `loaded`. `unpeek` first removes the link's peek, for the one
// branch the built pages do not carry (an English link with no peek). Each reading gives the
// header's text, `.mini-hw`'s nearest `[lang]`, every text node under `.mini-gloss` with its
// nearest `[lang]`, its computed weight and colour, the box's `aria-busy` and the mini's `lang`.
// The header's text leaves out the headword's sound icon (decisions 159, its hidden "Play" /
// "Spill av"); `play` gives each icon in the header: inside `.mini-hw` or not, and the nearest
// `[lang]` of its English and its Norwegian label.
// With args.shot (a path prefix) the first case is also shot in both states.
//
// args: { latency, cases: [{ name, page, find, unpeek }], shot }
// Result: { base, latency, cases: [{ name, page, found, busy: Reading, loaded: Reading }] }
//   Reading: { busy, mlang, text, hw: { text, lang, weight }, gloss: [{ t, lang, weight, color }] }
import { open, base, args, run, done, sleep } from './cdp.js';

const READ = `(() => {
  const x = document.querySelector('.ordpar-mopen'); if (!x) return null;
  const m = x.querySelector('.ordbok-xmini'), box = x.querySelector('.ordpar-fmini');
  const head = x.querySelector('.mini-head'); if (!head) return { head: false };
  const lang = e => { const l = e && e.closest('[lang]'); return l ? l.getAttribute('lang') : ''; };
  const hw = head.querySelector('.mini-hw');
  // the header's words as a reader sees them: the sound icon's hidden "Play" (decisions 159) out
  const seen = e => { const c = e.cloneNode(true); c.querySelectorAll('.ordpar-play').forEach(b => b.remove());
    return c.textContent.replace(/\\s+/g, ' ').trim(); };
  const gloss = [];
  for (const g of head.querySelectorAll('.mini-gloss')) {
    const w = document.createTreeWalker(g, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (!n.data.trim()) continue;
      const e = n.parentElement, cs = getComputedStyle(e);
      gloss.push({ t: n.data, lang: lang(e), weight: cs.fontWeight, color: cs.color });
    }
  }
  return { head: true, busy: !!box && box.getAttribute('aria-busy') === 'true',
    mlang: m && m.getAttribute('lang'), text: seen(head),
    play: [...head.querySelectorAll('.ordpar-play')].map(b => ({ inHw: !!(hw && hw.contains(b)),
      en: lang(b.querySelector('.ordpar-l-en')), nb: lang(b.querySelector('.ordpar-l-nb')) })),
    hw: hw ? { text: hw.textContent.trim(), lang: lang(hw), weight: getComputedStyle(hw).fontWeight } : null,
    gloss };
})()`;

async function shoot(p, path) {
  const r = await p.send('Page.captureScreenshot', { format: 'png' });
  await Bun.write(path, Buffer.from(r.data, 'base64'));
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  await p.send('Network.enable');
  await p.send('Network.emulateNetworkConditions', { offline: false, latency: args.latency,
    downloadThroughput: -1, uploadThroughput: -1 });
  const cases = [];
  for (const [i, c] of (args.cases || []).entries()) {
    await p.goto(base + '/bm-en/' + c.page + '/', 800);
    const busy = await p.eval(`(() => {
      const a = ${c.find};
      if (!a) return null;
      if (${!!c.unpeek}) { const k = a.parentNode.querySelector(':scope > .ordbok-xpeek'); if (k) k.remove(); }
      a.scrollIntoView({ block: 'center' });
      a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
      return ${READ};
    })()`);
    if (!busy) { cases.push({ name: c.name, page: c.page, found: false }); continue; }
    if (args.shot && i === 0) await shoot(p, args.shot + '-busy.png');
    let loaded = null;
    for (let t = 0; t < 20000; t += 100) {
      const r = await p.eval(READ);
      if (r && r.head && !r.busy && r.mlang) { loaded = r; break; }
      await sleep(100);
    }
    if (args.shot && i === 0) await shoot(p, args.shot + '-loaded.png');
    cases.push({ name: c.name, page: c.page, found: true, busy, loaded });
  }
  await done({ base, latency: args.latency, cases });
});
