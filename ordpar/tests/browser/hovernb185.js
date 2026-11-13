// Site decisions 185 (Robin, 2026-11-12): the setting "When the pointer rests on a linked word" —
// its translation (the default), its first Norwegian definition (`peek` = nb) or nothing — and the
// Norwegian hover following the setting "When a linked article or page is loaded" (`minifetch`).
//
// On a computer, in a fresh context; every hover is the pointer parked off the links, then moved
// onto the word and rested (1.2 s), as a reader does. For each hover: the peeks shown in the link's
// own box (`.ordbok-xpeek` children with a box, `display` not none) as [class, lang, text], every
// peek shown anywhere, and the `snip/` files the page asked for (the resource timing).
//   fault      — `minifetch` click, Norwegian only on, `nbhover` nbdef: on hus (args.hus) a rest on a
//                Norwegian link with `data-s`, then a press (the small article opens): the `snip/`
//                requests before the press; then the file of a second link loaded as a search would
//                (`ordparLookup.loadSnippets`), and a rest on that link: its Norwegian peek.
//   faultpeek  — the same under `peek` nb with the layer off.
//   nb         — `peek` nb, the default loading: on hus a translated link; on elastisk (args.untr.page)
//                an untranslated link (args.untr.href) and a translated one (args.untr.tr); with
//                Definitions on English, hus's English partner word; a small article of elastisk
//                opened on args.mini.page, both links rested on inside it; the search page for
//                elastisk (`listview` off), both links in its article; the word page args.word.
//   nbo        — the Norwegian-only view's own hover (`nbhover` nbdef, the default loading) on hus.
//                Each Norwegian peek's computed look (`look`), to compare with this one.
//   off        — `peek` off: hus's link, no peek.
//   def        — nothing stored: hus's link, its English peek.
//   address    — `/bm-en/<hus>/#peek=nb`: the class, the visit, nothing saved, the Norwegian peek.
//   settings   — /settings/: the setting's title and its choices in order with their words; the
//                second chosen: `peek` stored nb, the class on <html>.
//
// args: { hus, untr: {page, href, tr}, mini: {page, id}, search, word }
import { open, base, args, run, done, sleep } from './cdp.js';

const HELP = `window.H185 = {
  vis: e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).display !== 'none' && getComputedStyle(e).visibility !== 'hidden',
  links(root, href) {
    return [...(root || document).querySelectorAll('.ordbok-xref > a.ordbok-xword')]
      .filter(a => (a.getAttribute('href') || '') === href && H185.vis(a));
  },
  newest() { const ms = [...document.querySelectorAll('.ordbok-xmini')].filter(m => m.getClientRects().length);
    return ms[ms.length - 1] || null; },
  snips() { return performance.getEntriesByType('resource').map(e => e.name).filter(n => n.indexOf('/snip/') >= 0)
    .map(n => n.replace(/^.*\\/snip\\//, '')); },
  peeks(x) { return [...x.children].filter(k => k.classList.contains('ordbok-xpeek') && H185.vis(k))
    .map(k => [k.className, k.getAttribute('lang') || '', k.textContent.trim().slice(0, 60)]); },
  shown() { return [...document.querySelectorAll('.ordbok-xpeek')].filter(H185.vis).length; },
  // the Norwegian peek's look, for one style everywhere
  look(x) { const k = [...x.children].filter(k => k.classList.contains('ordpar-nbpk') && H185.vis(k))[0];
    if (!k) return null; const s = getComputedStyle(k);
    return ['fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'lineHeight', 'whiteSpace', 'maxWidth', 'color',
      'backgroundColor', 'borderTopWidth', 'borderTopColor', 'borderRadius', 'paddingTop', 'paddingLeft', 'boxShadow']
      .map(p => p + ':' + s[p]).join(';'); },
};
true`;

const CLS = `document.documentElement.className`;

async function mouse(p, x, y) { await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y }); }

/** Rest on the link chosen by `pick` (an expression giving the <a>, or null). */
async function rest(p, pick) {
  await p.eval(HELP);
  const at = await p.eval(`(() => { const a = ${pick}; if (!a) return null; window.H185.a = a;
    const m = a.closest('.ordpar-fmini');
    if (m) { const r = a.getBoundingClientRect(), b = m.getBoundingClientRect();
      if (r.top < b.top || r.bottom > b.bottom) a.scrollIntoView({ block: 'nearest' }); }
    else a.scrollIntoView({ block: 'center' });
    const q = a.getClientRects()[0]; return { x: q.left + Math.min(q.width / 2, 10), y: q.top + q.height / 2,
      href: a.getAttribute('href'), key: a.getAttribute('data-s'), xen: a.parentNode.classList.contains('ordpar-xen') }; })()`);
  if (!at) return { found: false };
  await mouse(p, 2, 2); await sleep(150);
  await mouse(p, at.x, at.y); await sleep(1200);
  await mouse(p, at.x + 1, at.y); await sleep(300); await p.frames();
  const got = await p.eval(`({ peeks: H185.peeks(H185.a.parentNode), shown: H185.shown(), snips: H185.snips(),
    look: H185.look(H185.a.parentNode) })`);
  return Object.assign({ found: true, href: at.href, key: at.key, xen: at.xen, at }, got);
}

async function fresh(p, store) {
  await p.goto(base + '/bm-en/', 200);
  await p.eval(`localStorage.clear(); sessionStorage.clear(); localStorage.setItem('theme', 'light');
    ${Object.entries(store || {}).map(([k, v]) => `localStorage.setItem('${k}', '${v}');`).join(' ')} true`);
}

const NB_LINK = `[...document.querySelectorAll('main .ordpar-pair > span[lang=nb] .ordbok-xref > a.ordbok-xword[data-s]')]
  .filter(a => !a.closest('.ordbok-xmini') && H185.vis(a))`;

async function waitMini(p) {
  return p.eval(`(async () => { for (let t = 0; t < 80; t++) {
    const m = H185.newest(); if (m && m.querySelector('.ordpar-mbody') && !m.querySelector('[aria-busy=true]')) return true;
    await new Promise(r => setTimeout(r, 100)); } return false; })()`);
}

async function faultCase(p, store) {
  const out = {};
  await fresh(p, store);
  await p.goto(base + '/bm-en/' + args.hus + '/', 900);
  await p.eval(HELP);
  out.cls = await p.eval(CLS);
  out.atLoad = await p.eval(`H185.snips()`);
  out.rest = await rest(p, `${NB_LINK}[0] || null`);
  // the press: the small article opens (the page's own fetch); the snip files asked for until then
  if (out.rest.found) {
    await p.click(out.rest.at.x, out.rest.at.y); await p.eval(HELP); out.opened = await waitMini(p);
    out.afterPress = await p.eval(`H185.snips()`);
    await p.eval(`(() => { const b = document.querySelector('.ordbok-xback'); if (b) b.click(); return true; })()`);
    await sleep(300);
  }
  // a second link whose file the page already has (as a search would leave it): its peek
  const key = await p.eval(`(() => { const as = ${NB_LINK}; const first = H185.a && H185.a.getAttribute('data-s');
    const a = as.filter(x => x.getAttribute('data-s') !== first)[0] || null; window.B185 = a;
    return a ? a.getAttribute('data-s') : null; })()`);
  out.loadedKey = key;
  if (key) {
    await p.eval(`Promise.resolve(ordparLookup.loadSnippets(${JSON.stringify(key)})).then(() => true)`);
    out.loaded = await rest(p, `window.B185`);
  }
  return out;
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const R = {};

  R.fault = await faultCase(p, { minifetch: 'click', nbonly: 'on', nbhover: 'nbdef' });
  R.faultpeek = await faultCase(p, { minifetch: 'click', peek: 'nb' });

  // `peek` = nb, the default loading
  const nb = {};
  await fresh(p, { peek: 'nb' });
  await p.goto(base + '/bm-en/' + args.hus + '/', 900);
  nb.cls = await p.eval(CLS);
  nb.hus = await rest(p, `${NB_LINK}[0] || null`);
  await p.goto(base + '/bm-en/' + args.untr.page + '/', 900);
  nb.untr = await rest(p, `H185.links(document.querySelector('main'), ${JSON.stringify(args.untr.href)})[0] || null`);
  nb.untrHadPeek = await p.eval(`H185.a ? !!H185.a.parentNode.querySelector(':scope > .ordbok-xpeek:not(.ordpar-nbpk)') : null`);
  nb.tr = await rest(p, `H185.links(document.querySelector('main'), ${JSON.stringify(args.untr.tr)})[0] || null`);
  // the word page, its article drawn in place (`listview` multi: site decisions 158's default shows
  // the list there)
  await p.eval(`localStorage.setItem('listview', 'multi'); true`);
  await p.goto(base + '/bm-en/' + encodeURIComponent(args.word) + '/', 900);
  await p.eval(`(async () => { for (let t = 0; t < 100; t++) { if (document.querySelector('main .ordpar-pair .ordbok-xref')) return true;
    await new Promise(r => setTimeout(r, 100)); } return false; })()`);
  await sleep(500);
  nb.word = await rest(p, `${NB_LINK}[0] || null`);
  await p.eval(`localStorage.removeItem('listview'); true`);
  // the English partner word, with Definitions on English (the link lives on the English line)
  await p.eval(`localStorage.setItem('defs', 'en'); true`);
  await p.goto(base + '/bm-en/' + args.hus + '/', 900);
  nb.partner = await rest(p, `[...document.querySelectorAll('main .ordpar-xen > a.ordbok-xword')].filter(a => !a.closest('.ordbok-xmini') && H185.vis(a))[0] || null`);
  await p.eval(`localStorage.removeItem('defs'); true`);
  // a small article
  await p.goto(base + '/bm-en/' + args.mini.page + '/', 900);
  await p.eval(HELP);
  const mpt = await p.eval(`(() => { const a = H185.links(document.querySelector('main'), '/bm-en/${args.mini.id}/')[0];
    if (!a) return null; a.scrollIntoView({ block: 'center' }); const r = a.getClientRects()[0];
    return { x: r.left + Math.min(r.width / 2, 10), y: r.top + r.height / 2 }; })()`);
  nb.mini = { opened: false };
  if (mpt) {
    await mouse(p, mpt.x, mpt.y); await sleep(200); await p.click(mpt.x, mpt.y);
    nb.mini.opened = await waitMini(p);
    nb.mini.untr = await rest(p, `H185.links(H185.newest(), ${JSON.stringify(args.untr.href)})[0] || null`);
    nb.mini.tr = await rest(p, `H185.links(H185.newest(), ${JSON.stringify(args.untr.tr)})[0] || null`);
  }
  // the search page's article
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/#q=' + encodeURIComponent(args.search), 900);
  await p.eval(`(async () => { for (let t = 0; t < 60; t++) { if (document.querySelector('main .ordbok-xref')) return true;
    await new Promise(r => setTimeout(r, 100)); } return false; })()`);
  await sleep(500);
  nb.search = {
    untr: await rest(p, `H185.links(document.querySelector('main'), ${JSON.stringify(args.untr.href)})[0] || null`),
    tr: await rest(p, `H185.links(document.querySelector('main'), ${JSON.stringify(args.untr.tr)})[0] || null`),
  };
  R.nb = nb;

  // the Norwegian-only view's own hover, the default loading: the look the others must match
  await fresh(p, { nbonly: 'on', nbhover: 'nbdef' });
  await p.goto(base + '/bm-en/' + args.hus + '/', 900);
  R.nbo = await rest(p, `${NB_LINK}[0] || null`);

  // nothing; the default
  await fresh(p, { peek: 'off' });
  await p.goto(base + '/bm-en/' + args.hus + '/', 900);
  R.off = await rest(p, `${NB_LINK}[0] || null`);
  R.off.cls = await p.eval(CLS);
  await fresh(p, {});
  await p.goto(base + '/bm-en/' + args.hus + '/', 900);
  R.def = await rest(p, `${NB_LINK}[0] || null`);
  R.def.cls = await p.eval(CLS);

  // the address (146)
  await fresh(p, {});
  await p.goto(base + '/bm-en/' + args.hus + '/#peek=nb', 900);
  R.address = await rest(p, `${NB_LINK}[0] || null`);
  Object.assign(R.address, await p.eval(`({ cls: ${CLS}, saved: localStorage.getItem('peek'),
    visit: JSON.parse(sessionStorage.getItem('ordpar-visit') || 'null'), hash: location.hash })`));

  // the settings page
  await fresh(p, {});
  await p.goto(base + '/settings/', 900);
  const S = await p.eval(`(() => {
    const t = document.getElementById('ordpar-peek-legend');
    const rs = [...document.querySelectorAll('input[data-key="peek"]')];
    return { title: t ? t.textContent : null,
      choices: rs.map(r => [r.value, (document.querySelector('label[for="' + r.id + '"]') || {}).textContent || '', r.checked]),
      notes: rs.map(r => { const n = r.getAttribute('aria-describedby'); return n ? document.getElementById(n).textContent : ''; }) }; })()`);
  const at = await p.eval(`(() => { const r = document.querySelector('input[data-key="peek"][value="nb"]'); if (!r) return null;
    r.scrollIntoView({ block: 'center' }); const b = r.getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; })()`);
  if (at) { await p.click(at.x, at.y); await sleep(300); }
  S.stored = await p.eval(`localStorage.getItem('peek')`);
  S.cls = await p.eval(CLS);
  S.pressed = await p.eval(`[...document.querySelectorAll('button[data-preset]')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.getAttribute('data-preset'))`);
  R.settings = S;

  done({ base, R });
});
