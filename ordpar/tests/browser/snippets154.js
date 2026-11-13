// Site decisions 154 (Robin, 2026-10-31): what Google reads from a page. For each page in
// `args.pages` ({path, word}), on a computer (1,280 px) or a phone (390 px, args.mobile), the page
// as the browser draws it (its scripts run, the rows filled) and the page's markup as served:
//
//  (a) hidden labels: every word of every hover label (`.ordbok-xpeek`) and every
//      screen-reader-only label (`.ordpar-visually-hidden`, `.sr-only`, the inflection tables'
//      `.ordpar-vh`) sits inside an element carrying `data-nosnippet`, and that element is a
//      `span`, `div` or `section` (Google reads the attribute on those three only; a table's
//      `<caption>` holds such a span). The search box's own `<label>` in the header is the one exception (outside
//      the dictionary's content; a `<label>` cannot carry the attribute). Also every element
//      carrying `data-nosnippet` is one of the three. Read on the drawn page and on the markup as
//      served (`fetch` + DOMParser), since Google reads both.
//  (b) glued text: the text nodes of the drawn page outside `data-nosnippet` (and outside script,
//      style, template), in document order; wherever two consecutive drawn ones meet with no
//      whitespace at the join (and no `<br>` between them), while the page shows them apart — `innerText` puts a space or a
//      line break between them, or the second starts on another line or more than 2 px to the
//      right of the first — that is a fault: a text extraction would join their words.
//  (c) the description: `<meta name="description">` begins with the page's headword (`word`)
//      followed by ":" or " " (Robin approved "kanskje: perhaps · maybe …"), and
//      `og:description` is the same text. Skipped for a page with no `word`.
//
// Result: { base, pages: [{ path, url, hidden: [...], hiddenRaw: [...], badHolders: [...],
//   glued: [{a, b, where, why}], description, og, descOk, rows }] }
import { open, base, args, run, done, sleep } from './cdp.js';

const CHECK = `(async () => {
  const HID = '.ordbok-xpeek, .ordpar-visually-hidden, .sr-only, .ordpar-vh';
  const OK_HOLDER = /^(SPAN|DIV|SECTION)$/;
  const where = el => {
    const bits = [];
    for (let e = el; e && e.nodeType === 1 && bits.length < 4; e = e.parentElement) {
      bits.push(e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).join('.') : ''));
    }
    return bits.join(' < ');
  };
  const hiddenIn = doc => {
    const bad = [];
    for (const el of doc.querySelectorAll(HID)) {
      if (el.matches('label[for="ordpar-q"]')) continue;
      // its every word inside a data-nosnippet span, div or section (itself, an ancestor, or for
      // a <caption>, which cannot carry it, a span inside)
      const held = n => { const h = n.parentElement && n.parentElement.closest('[data-nosnippet]'); return !!h && OK_HOLDER.test(h.tagName); };
      const texts = []; const w = doc.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.data.trim()) texts.push(n); }
      if (texts.some(n => !held(n))) bad.push(where(el) + ' "' + (el.textContent || '').trim().slice(0, 40) + '"');
    }
    return bad;
  };
  const holdersIn = doc => Array.from(doc.querySelectorAll('[data-nosnippet]'))
    .filter(e => !OK_HOLDER.test(e.tagName)).map(where);
  const out = { url: location.href };
  out.hidden = hiddenIn(document);
  out.badHolders = holdersIn(document);
  try {
    const raw = await (await fetch(location.href.split('#')[0], { cache: 'no-store' })).text();
    const doc = new DOMParser().parseFromString(raw, 'text/html');
    out.hiddenRaw = hiddenIn(doc);
    out.badHolders = out.badHolders.concat(holdersIn(doc).map(x => 'served: ' + x));
  } catch (e) { out.hiddenRaw = ['fetch failed: ' + e]; }

  // (b) the text nodes in order, outside data-nosnippet / script / style / template / noscript
  const SKIP = 'script,style,template,noscript,[data-nosnippet]';
  const nodes = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: n =>
    n.parentElement && n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  for (let n = walk.nextNode(); n; n = walk.nextNode()) { if (n.data.length) nodes.push(n); }
  const rects = (n, a, b) => { const r = document.createRange(); r.setStart(n, a); r.setEnd(n, b); return r.getClientRects(); };
  const drawn = n => { const r = document.createRange(); r.selectNodeContents(n); return r.getClientRects().length > 0; };
  const WS = /\\s/;
  const cands = [];
  for (let i = 0; i + 1 < nodes.length; i++) {
    const A = nodes[i], B = nodes[i + 1];
    if (WS.test(A.data.charAt(A.data.length - 1)) || WS.test(B.data.charAt(0))) continue;
    if (!drawn(A) || !drawn(B)) continue;
    // a <br> between them is a line break a text extraction keeps (Google's snippet: "mulighet;
    // kan hende", across one)
    const between = document.createRange(); between.setStartAfter(A); between.setEndBefore(B);
    if (between.cloneContents().querySelector('br')) continue;
    const ra = rects(A, A.data.length - 1, A.data.length), rb = rects(B, 0, 1);
    if (!ra.length || !rb.length) continue;
    const a = ra[ra.length - 1], b = rb[0];
    const ma = (a.top + a.bottom) / 2, mb = (b.top + b.bottom) / 2;
    const otherLine = Math.abs(mb - ma) > Math.min(a.height, b.height) / 2;
    const gap = b.left - a.right;
    cands.push({ A, B, geo: otherLine ? 'another line' : (gap > 2 ? 'a gap of ' + Math.round(gap) + ' px' : '') });
  }
  // innerText between the two halves of each join, by markers put in after the measuring
  cands.forEach((c, i) => { c.a0 = c.A.data; c.b0 = c.B.data; });
  cands.forEach((c, i) => { c.A.data = c.A.data + '\\uE000' + i + '\\uE001'; c.B.data = '\\uE002' + i + '\\uE003' + c.B.data; });
  const text = document.body.innerText;
  cands.forEach((c, i) => { c.A.data = c.a0; c.B.data = c.b0; });
  const glued = [];
  cands.forEach((c, i) => {
    const s = text.indexOf('\\uE000' + i + '\\uE001'), e = text.indexOf('\\uE002' + i + '\\uE003');
    let it = '';
    if (s >= 0 && e > s) {
      const mid = text.slice(s + ('\\uE000' + i + '\\uE001').length, e).replace(/[\\uE000-\\uE003]\\d*[\\uE000-\\uE003]?/g, '');
      if (/\\s/.test(mid)) it = 'innerText ' + JSON.stringify(mid);
    }
    if (it || c.geo) glued.push({ a: c.a0.slice(-30), b: c.b0.slice(0, 30), where: where(c.A.parentElement) + ' | ' + where(c.B.parentElement),
      why: [it, c.geo].filter(Boolean).join('; ') });
  });
  out.glued = glued;
  const m = document.querySelector('meta[name="description"]'), og = document.querySelector('meta[property="og:description"]');
  out.description = m ? m.content : null;
  out.og = og ? og.content : null;
  out.rows = document.querySelectorAll('.ordpar-row, .ordpar-result, .ordpar-card, .ordpar-hit').length;
  return out;
})()`;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const pages = [];
  await p.goto(base + '/bm-en/', 500);
  await p.eval('localStorage.clear(); sessionStorage.clear(); true');
  for (const pg of args.pages) {
    await p.goto(base + pg.path, 800);
    // the page's own scripts: the rows drawn, their snippets filled, the article lifted
    for (let t = 0; t < 10000; t += 200) {
      const ready = await p.eval(`!!document.querySelector('main .ordpar-row, main .ordpar-result, main .ordpar-card, main .ordpar-hit, main article')
        && !document.querySelector('.is-pending') && !document.querySelector('.ordpar-searching')`);
      if (ready) break;
      await sleep(200);
    }
    await sleep(700);
    const r = await p.eval(CHECK);
    r.path = pg.path;
    r.word = pg.word || null;
    if (pg.word) {
      const d = r.description || '';
      r.descOk = d.startsWith(pg.word) && /^[: ]/.test(d.slice(pg.word.length)) && r.og === d;
    }
    pages.push(r);
  }
  await done({ base, pages });
});
