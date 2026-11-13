// Decisions 98 / 100: the sense numbers the browser DRAWS run 1, 2, 3, … in every `ol.ordbok-senses`.
//
// Read from the accessibility tree (CDP `Accessibility.getFullAXTree`): each list item's marker is a
// node of role `ListMarker` whose name is the text drawn — what a screen reader announces, and what
// the eye sees, exact, with no OCR. Each marker is mapped to its list item (the marker's parent node)
// and through it to its list; a visible `ol.ordbok-senses` with n `li` children must read
// "1. " … "n. ". The second finding names the cause where it fails: any other element inside the
// list that advances its `list-item` counter (computed `display` a list item, nearest `ol`/`ul` that
// list, `counter-increment` not setting `list-item` to 0).
//
// args: { cases: [{ label, url, settings: {layout, subsenses, defs}, open?: {mini|row: ...} }] }
//   `settings` are applied as the classes on <html> the settings page sets (`shell.js` `applyDefs`,
//   `applyClassKeys`), then the page's `ordparDefs()` is asked to catch up, as the shell does.
//   `open`: {mini: <href>} clicks the first visible link to <href> and reads the mini it opens;
//           {row: <article id>} clicks the list view's row for that article and reads its panel.
// Result: { cases: [{ label, lists: [{ where, senses, subs, selector, drawn: [...] }], offenders: [{ where, selector }] }] }
import { open, base, args, run, done, sleep } from './cdp.js';

// The <html> classes per setting value (shell.js applyDefs / applyClassKeys; mini = article resolved).
function classScript(s) {
  const defs = s.defs || 'both', mini = defs === 'en' ? 'en' : 'both';
  return `(() => { const cl = document.documentElement.classList;
    cl.toggle('ordpar-defs-en', ${JSON.stringify(defs)} === 'en');
    cl.toggle('ordpar-defs-no', ${JSON.stringify(defs)} === 'no');
    cl.toggle('ordpar-mini-en', ${JSON.stringify(mini)} === 'en');
    cl.toggle('ordpar-subsen-en', ${JSON.stringify(s.subsenses || 'defs')} === 'en');
    cl.toggle('ordpar-layout-ordbokene', ${JSON.stringify(s.layout || 'ordpar')} === 'ordbokene');
    if (typeof window.ordparDefs === 'function') window.ordparDefs();
    return document.documentElement.className; })()`;
}

// Tag every visible ol.ordbok-senses and its li children, so the AX tree's nodes can be mapped back;
// and find the elements that wrongly advance a list's counter (the cause).
const TAG = `(() => {
  const vis = e => e.getClientRects().length > 0;
  // a readable selector, up to an id (lists) or from the sense list down (offenders: stop = the list)
  const path = (e, stop) => { const p = []; for (; e && e.nodeType === 1 && e !== document.body; e = e.parentElement) {
      let s = e.tagName.toLowerCase();
      if (e.classList.length) s += '.' + [...e.classList].join('.');
      if (e === stop) { p.unshift(s); break; }
      if (e.id) { p.unshift(s + '#' + e.id); if (!stop) break; else continue; }
      const sib = e.parentElement ? [...e.parentElement.children].filter(c => c.tagName === e.tagName) : [];
      if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(e) + 1) + ')';
      p.unshift(s); } return p.join(' > '); };
  const where = ol => { const m = ol.closest('.ordbok-xmini'); if (m) return 'mini'; const r = ol.closest('.ordpar-row-panel'); if (r) return 'row'; return 'page'; };
  const lists = [], offenders = [];
  document.querySelectorAll('[data-tst-ol]').forEach(e => e.removeAttribute('data-tst-ol'));
  document.querySelectorAll('[data-tst-li]').forEach(e => e.removeAttribute('data-tst-li'));
  [...document.querySelectorAll('ol.ordbok-senses')].filter(vis).forEach((ol, i) => {
    ol.setAttribute('data-tst-ol', i);
    const lis = [...ol.children].filter(c => c.tagName === 'LI');
    lis.forEach((li, j) => li.setAttribute('data-tst-li', i + ':' + j));
    const subs = [...ol.querySelectorAll('div.ordbok-sub:not(.ordpar-comp)')].filter(d => vis(d) && d.parentElement.closest('ol, ul') === ol).length;
    lists.push({ i, where: where(ol), senses: lis.length, subs, selector: path(ol) });
    for (const e of ol.querySelectorAll('*')) {
      if (e.parentElement === ol && e.tagName === 'LI') continue;
      const cs = getComputedStyle(e);
      if (!/list-item/.test(cs.display)) continue;
      if (e.parentElement.closest('ol, ul') !== ol) continue;
      const ci = cs.counterIncrement || 'none';
      const m = /(?:^|\\s)list-item(?:\\s+(-?\\d+))?/.exec(ci);
      if (m && m[1] === '0') continue;
      offenders.push({ list: i, where: where(ol), selector: path(e, ol), counterIncrement: ci });
    }
  });
  return { lists, offenders };
})()`;

async function readMarkers(p, lists) {
  const nodes = await p.axNodes();
  const byId = new Map(nodes.map(n => [n.nodeId, n]));
  const drawn = lists.map(() => []);
  for (const n of nodes) {
    if (!n.role || n.role.value !== 'ListMarker' || n.ignored) continue;
    const item = byId.get(n.parentId);
    if (!item || !item.backendDOMNodeId) continue;
    const a = await p.attrs(item.backendDOMNodeId);
    if (a['data-tst-li'] === undefined) continue;          // a marker of another list
    const [i] = a['data-tst-li'].split(':').map(Number);
    drawn[i].push((n.name && n.name.value) || '');
  }
  return drawn;
}

async function openThing(p, o) {
  if (o.mini) {
    const pt = await p.eval(`(() => { const a = [...document.querySelectorAll('a.ordbok-xword')].find(a =>
        a.getAttribute('href') === ${JSON.stringify(o.mini)} && a.getClientRects().length && getComputedStyle(a).pointerEvents !== 'none');
      if (!a) return null; document.documentElement.style.scrollBehavior = 'auto'; a.scrollIntoView({ block: 'center' });
      return new Promise(ok => requestAnimationFrame(() => requestAnimationFrame(() => { const r = a.getClientRects()[0];
        ok({ x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 }); }))); })()`);
    if (!pt) throw new Error('no live link to ' + o.mini);
    await p.click(pt.x, pt.y);
    for (let i = 0; i < 50; i++) {
      await sleep(100);
      if (await p.eval(`!!document.querySelector('.ordbok-xmini ol.ordbok-senses') && [...document.querySelectorAll('.ordbok-xmini ol.ordbok-senses')].some(e => e.getClientRects().length)`)) return;
    }
    throw new Error('the mini for ' + o.mini + ' did not open with its senses');
  }
  if (o.row) {
    const sel = JSON.stringify('.ordpar-row[data-id="' + o.row + '"] .ordpar-row-button');
    let ok = false;
    // the search's own rows, not a word page's built ones (decisions 117: `?q=møte` goes on to
    // /bm-en/møte/, whose built rows carry the same classes until the script redraws them and
    // closes a row opened meanwhile; the built headline goes when the script has drawn), as the
    // eight scripts hardened on 2026-10-26 wait; this one, reaching the search by `?q=`, was missed
    for (let i = 0; i < 100 && !ok; i++) { ok = await p.eval(`!document.querySelector('.ordpar-word-title') && !!document.querySelector(${sel})`); if (!ok) await sleep(100); }
    if (!ok) throw new Error('no list-view row for ' + o.row);
    await p.eval(`document.querySelector(${sel}).click()`);
    for (let i = 0; i < 80; i++) {
      await sleep(100);
      if (await p.eval(`[...document.querySelectorAll('.ordpar-row-panel ol.ordbok-senses')].some(e => e.getClientRects().length)`)) return;
    }
    throw new Error('the row for ' + o.row + ' did not open with its senses');
  }
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const out = [];
  let loaded = null;
  for (const c of args.cases) {
    if (c.open || loaded !== c.url) { await p.goto(base + c.url, 400); loaded = c.open ? null : c.url; }
    const cls = await p.eval(classScript(c.settings || {}));
    if (c.open) await openThing(p, c.open);
    await p.frames();
    const t = await p.eval(TAG);
    const drawn = await readMarkers(p, t.lists);
    out.push({ label: c.label, html: cls, lists: t.lists.map((l, i) => ({ where: l.where, senses: l.senses, subs: l.subs, selector: l.selector, drawn: drawn[i] })), offenders: t.offenders });
  }
  await done({ base, cases: out });
});
