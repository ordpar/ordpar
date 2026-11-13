// Site decisions 152 (Robin, 2026-10-30/31): NORWEGIAN ONLY, a layer over the reader's settings, its
// "English equivalents" sub-setting with the rows' and hovers' choices, the header icon (remembered,
// one state with Settings), the headword icon where Definer hides the header, and the labels setting.
//
// For one viewport (args.mobile: a phone, taps; else a computer, clicks), in a fresh context:
//   off        — hus (args.hus) with nothing stored but the eye on: no layer class, its English shown,
//                the eye shown, the header icon shown (the one for the width) and not pressed
//   on         — the icon pressed: the layer's classes, `nbonly` stored "on", the icon pressed; the
//                ENGLISH SCAN of `<main>` (below) finds no English from the dictionary's content; the
//                word class and, the table opened, the inflection words in Norwegian; the eye hidden;
//                the headings Norwegian too (152's follow-up: the layer turns every label)
//   reload     — the classes present when <body> is first made (before the first paint); still on
//   pages      — args.pages each opened (remembered across pages): the scan, empty
//   mini       — on hus a small article opened: the scan inside it, empty
//   search     — `#q=` args.search (rows): the scan, empty, the rows' right side the first Norwegian
//                definition (`lang="nb"`); the suggestions for args.suggest: no English on the right
//   personal   — hus favourited and searched; History and Favourites: the scan, empty, Norwegian lines
//   switch     — `direction` stored "en": the switch hidden, the box Norwegian, Random word draws a
//                Norwegian word, the stored direction still "en"; on a phone the icon still shown;
//                with the equivalents shown, the switch back and on
//   rows0      — the rows on "nothing": no row's right side shown
//   hover      — (computer) the hovers on "Norwegian definition": a link's Norwegian peek, no English;
//                on "nothing" (the default) no peek
//   iconoff    — `nbicon` off: no icon
//   definer    — `#nbonly=on&q=hus` with /more/'s CSS line: the header hidden, the headword's icon
//                shown and pressed; pressed again: the layer off for this pop-up, nothing saved
//   labels     — `labels` = no, the layer off: the headings and the word class Norwegian, the
//                definitions' English still shown
//   nbl        — (152's follow-up, Robin 2026-10-31) `labels` stored "en", the layer on: every label
//                shown Norwegian (no `.ordpar-l-en` shown) on hus, args.go, the word page args.word and
//                in a small article; the layer off by the icon: English again, `labels` still "en"
//   back       — the icon pressed again: no layer class, the English and the eye back
// The ENGLISH SCAN: every text node shown in `<main>` (or the box given) whose nearest `lang` is
// English, outside the site's own words (the view line, the result controls, the headings, labels and
// buttons, a screen reader's labels): `content` lists them, `site` the site's own words left.
//
// args: { mobile, hus, pages: [ids], search, suggest, css, go, word }
import { open, base, args, run, done, sleep } from './cdp.js';

const SITE_WORDS = ['.ordpar-viewline', '.ordpar-result-controls', '.ordpar-l-en', '.ordpar-section-title',
  '.ordpar-dict-title', '.ordpar-personal h1', '.ordpar-personal-nav', '.ordpar-personal-actions', 'button',
  '.ordpar-hint', '.ordpar-empty', '.ordpar-change', '.ordpar-popup-head',
  '.sr-only', '.ordpar-visually-hidden', '.ordpar-vh', '.ordbok-nodef', 'summary', '.ordpar-note',
  '.ordpar-option-count', '.ordpar-transfer'].join(',');
const SCAN = (root) => `(() => {
  const root = ${root || "document.querySelector('main')"};
  if (!root) return { content: ['(no root)'], site: [] };
  const content = [], site = [];
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const t = n.nodeValue.replace(/\\s+/g, ' ').trim();
    if (!t || !/[A-Za-zÆØÅæøå]{2}/.test(t)) continue;
    const el = n.parentElement;
    if (!el || !el.getClientRects().length) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const l = (el.closest('[lang]') || document.documentElement).getAttribute('lang') || '';
    if (!/^en/.test(l)) continue;
    (el.closest(${JSON.stringify(SITE_WORDS)}) ? site : content).push(t.slice(0, 80));
  }
  return { content, site: [...new Set(site)] };
})()`;

async function until(p, expr, ms = 12000) {
  for (let t = 0; t < ms; t += 100) { try { if (await p.eval(`!!(${expr})`)) return true; } catch (e) { /* again */ } await sleep(100); }
  return false;
}
async function press(p, selector) {
  const at = await p.eval(`(() => { const b = [...document.querySelectorAll(${JSON.stringify(selector)})]
    .find(x => x.getClientRects().length && getComputedStyle(x).visibility !== 'hidden');
    if (!b) return null; b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!at) return false;
  if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
  await sleep(400);
  return true;
}
const VISIBLE = sel => `[...document.querySelectorAll(${JSON.stringify(sel)})].filter(x => x.getClientRects().length && getComputedStyle(x).visibility !== 'hidden')`;
const TEXTS = sel => `${VISIBLE(sel)}.map(x => x.innerText.replace(/\\s+/g, ' ').trim())`;
const CLS = `document.documentElement.className`;
const ICON = '.ordpar-nbo-btn';
const STATE = `({ cls: ${CLS}, stored: localStorage.getItem('nbonly'),
  icon: ${VISIBLE(ICON)}.map(b => [b.parentNode.className, b.getAttribute('aria-pressed')]),
  gloss: ${TEXTS('.ordpar-gloss')}, enDefs: ${VISIBLE('.ordpar-pair > span.ordbok-def[lang=en], .ordpar-pair > span.ordbok-def:not([lang])')}.length,
  eye: ${VISIBLE('.ordpar-exeye')}.length, pos: ${TEXTS('.ordbok-pos')}, h3: ${TEXTS('main h3')} })`;
// the labels inside a box (152 follow-up): the headings, the inflection button, every label copy shown
// in either language, the stored `labels`, and the card foot's buttons (English whatever the labels
// say: the interface's, Robin 2026-11-03)
const LABELS = box => `(() => { const q = s => ${JSON.stringify(box)} + ' ' + s;
  const vis = s => [...document.querySelectorAll(q(s))].filter(x => x.getClientRects().length
    && getComputedStyle(x).visibility !== 'hidden').map(x => x.innerText.replace(/\\s+/g, ' ').trim());
  return { h3: vis('h3'), infl: vis('details.ordpar-infl-toggle > summary'), en: vis('.ordpar-l-en'),
    nb: vis('.ordpar-l-nb'), foot: vis('.ordpar-result-controls .ordpar-result-btn'),
    labels: localStorage.getItem('labels'), cls: document.documentElement.className };
})()`;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const R = {};
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: `
    new MutationObserver(function (ms, o) { if (document.body) { window.__firstBody = document.documentElement.className; o.disconnect(); } })
      .observe(document, { childList: true, subtree: true });` });
  // a new document each time (a search address after the search page is otherwise the same document)
  const go = async (url, settle) => { await p.goto('about:blank', 50); await p.goto(url, settle); };
  const hus = base + '/bm-en/' + args.hus + '/';
  await p.goto(hus, 300);
  await p.eval(`localStorage.clear(); sessionStorage.clear(); localStorage.setItem('exeye', 'on'); true`);
  await p.goto(hus, 900);

  R.off = await p.eval(STATE);
  R.off.scan = await p.eval(SCAN());

  // the icon pressed: Norwegian only for the whole site, remembered
  R.pressed = await press(p, ICON);
  await sleep(500);
  R.on = await p.eval(STATE);
  R.on.scan = await p.eval(SCAN());
  await press(p, 'details.ordpar-infl-toggle > summary');
  R.on.table = await p.eval(`${TEXTS('.ordpar-inflection th')}`);

  await p.reload(900);
  R.reload = await p.eval(`({ first: window.__firstBody || '', cls: ${CLS} })`);

  R.pages = {};
  for (const id of args.pages || []) {
    await p.goto(base + '/bm-en/' + id + '/', 900);
    R.pages[id] = { cls: await p.eval(CLS), scan: await p.eval(SCAN()) };
  }

  // a small article opened from hus, its own scan
  await p.goto(hus, 900);
  const opened = await press(p, 'main .ordpar-pair > span[lang=nb] a.ordbok-xword');
  await until(p, `document.querySelector('.ordbok-xmini .ordpar-mbody, .ordbok-xmini .mini-pair')`, 8000);
  await sleep(600);
  R.mini = { opened, scan: await p.eval(SCAN(`document.querySelector('.ordbok-xmini')`)) };

  // the heart, for Favourites
  await p.goto(hus, 900);
  R.faved = await press(p, '.ordpar-heart, .ordpar-result-heart');

  // the search (rows) and the suggestions
  await go(base + '/bm-en/#q=' + encodeURIComponent(args.search), 1500);
  await until(p, `document.querySelector('.ordpar-row-snippet:not(.is-pending)')`, 10000);
  await sleep(800);
  R.search = { url: await p.eval('location.href'), scan: await p.eval(SCAN()),
    labels: await p.eval(`${VISIBLE('.ordpar-form-label')}.map(x => x.innerText.trim())`),
    rows: await p.eval(`${VISIBLE('.ordpar-row-snippet')}.map(s => [s.lang, s.innerText.trim().slice(0, 60)])`) };
  await p.eval(`(() => { const b = document.getElementById('ordpar-q'); b.focus(); b.value = ${JSON.stringify(args.suggest)};
    b.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await until(p, `document.querySelector('.ordpar-option .ordpar-option-side :not(.is-pending)')`, 8000);
  await sleep(1200);
  R.suggest = { scan: await p.eval(SCAN(`document.querySelector('.ordpar-popup')`)),
    sides: await p.eval(`${VISIBLE('.ordpar-option:not(.ordpar-option-en) .ordpar-option-side > span')}.map(s => [s.lang, s.innerText.trim().slice(0, 50)])`) };

  // History and Favourites
  R.personal = {};
  for (const page of ['history', 'favourites']) {
    await p.goto(base + '/' + page + '/', 1500);
    await sleep(1200);
    R.personal[page] = { scan: await p.eval(SCAN()),
      sides: await p.eval(`${VISIBLE('.ordpar-option-side > span, .ordpar-row-snippet')}.map(s => [s.lang, s.innerText.trim().slice(0, 50)])`) };
  }

  // the English switch: hidden with the equivalents, the stored direction untouched
  await p.eval(`localStorage.setItem('direction', 'en'); true`);
  await p.goto(base + '/bm-en/', 900);
  R.sw = { switchShown: await p.eval(`${VISIBLE('.ordpar-switch')}.length`),
    boxLang: await p.eval(`document.getElementById('ordpar-q').lang`),
    icon: await p.eval(`${VISIBLE(ICON)}.map(b => b.parentNode.className)`) };
  await press(p, '.ordpar-random');
  await until(p, `location.hash.indexOf('#q=') === 0 || location.hash.indexOf('#en=') === 0 || /\\/bm-en\\/[^#]+\\/$/.test(location.pathname)`, 10000);
  await sleep(800);
  R.sw.random = await p.eval(`location.pathname + location.hash`);
  R.sw.stored = await p.eval(`localStorage.getItem('direction')`);
  await p.eval(`localStorage.setItem('nbequiv', 'shown'); true`);
  await p.goto(base + '/bm-en/', 900);
  R.sw.shown = { switchShown: await p.eval(`${VISIBLE('.ordpar-switch')}.length`),
    checked: await p.eval(`document.getElementById('ordpar-en-switch').checked`) };
  await p.eval(`localStorage.removeItem('nbequiv'); localStorage.removeItem('direction'); true`);

  // the rows' right side "nothing"
  await p.eval(`localStorage.setItem('nbrows', 'none'); true`);
  await go(base + '/bm-en/#q=' + encodeURIComponent(args.search), 1500);
  await sleep(1500);
  R.rows0 = { cls: await p.eval(CLS), snippets: await p.eval(`${VISIBLE('.ordpar-row-snippet, .ordpar-hit-snippet')}.length`),
    rows: await p.eval(`document.querySelectorAll('.ordpar-row').length`) };
  await p.eval(`localStorage.removeItem('nbrows'); true`);

  // the hovers (a pointer: a computer only)
  if (!args.mobile) {
    const hoverAt = async () => {
      const at = await p.eval(`(() => { const a = ${VISIBLE('main .ordpar-pair > span[lang=nb] a.ordbok-xword[data-s]')}[0];
        if (!a) return null; a.scrollIntoView({ block: 'center' }); const r = a.getBoundingClientRect();
        return { x: r.left + 3, y: r.top + r.height / 2 }; })()`);
      if (!at) return null;
      await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 5, y: 5 });
      await sleep(100);
      await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: at.x, y: at.y });
      await sleep(1200);
      await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: at.x + 1, y: at.y });
      await sleep(300);
      return p.eval(`${VISIBLE('.ordbok-xpeek')}.map(x => [x.className, x.lang, x.innerText.trim().slice(0, 60)])`);
    };
    await p.eval(`localStorage.setItem('nbhover', 'nbdef'); true`);
    await p.goto(hus, 900);
    R.hoverNb = await hoverAt();
    await p.eval(`localStorage.removeItem('nbhover'); true`);
    await p.goto(hus, 900);
    R.hoverNone = await hoverAt();
  }

  // the icon's own setting off
  await p.eval(`localStorage.setItem('nbicon', 'off'); true`);
  await p.goto(hus, 700);
  R.iconoff = { icons: await p.eval(`${VISIBLE(ICON)}.length`), cls: await p.eval(CLS) };
  await p.eval(`localStorage.removeItem('nbicon'); true`);

  // Definer: a fresh storage, the settings in the address, /more/'s CSS line; `listview=multi`
  // in the address too, so *hus* opens its article (site decisions 158: under the default it
  // shows the list, *hus* being also an inflected form of *huse*), whose headword holds the icon
  await p.eval(`localStorage.clear(); sessionStorage.clear(); true`);
  await go(base + '/bm-en/#nbonly=on&listview=multi&q=' + encodeURIComponent('hus'), 1500);
  await until(p, `document.querySelector('main .ordpar-article .ordbok-head')`, 10000);
  await p.eval(`(() => { const s = document.createElement('style'); s.textContent = ${JSON.stringify(args.css)};
    document.head.appendChild(s); return true; })()`);
  await sleep(600);
  const hw = '.ordpar-nbhw-btn';
  R.definer = { header: await p.eval(`${VISIBLE('.ordpar-header')}.length`), cls: await p.eval(CLS),
    hw: await p.eval(`${VISIBLE(hw)}.map(b => b.getAttribute('aria-pressed'))`),
    stored: await p.eval(`localStorage.getItem('nbonly')`) };
  await press(p, hw);
  await sleep(500);
  R.definer.after = { cls: await p.eval(CLS), hw: await p.eval(`${VISIBLE(hw)}.map(b => b.getAttribute('aria-pressed'))`),
    stored: await p.eval(`localStorage.getItem('nbonly')`),
    visit: await p.eval(`JSON.parse(sessionStorage.getItem('ordpar-visit') || 'null')`) };

  // the labels setting, the layer off
  await p.eval(`localStorage.clear(); sessionStorage.clear(); localStorage.setItem('labels', 'no'); true`);
  await p.goto(hus, 900);
  R.labels = await p.eval(STATE);
  R.labels.lab = await p.eval(LABELS('main'));
  await p.eval(`localStorage.setItem('nbonly', 'on'); localStorage.removeItem('labels'); true`);
  await p.goto(hus, 900);
  R.layerLabels = await p.eval(STATE);

  // site decisions 152, the follow-up (Robin, 2026-10-31): the layer turns EVERY label inside the
  // article, whatever `labels` says (stored "en" here), never writing it; `listview` = multi, so
  // the word page of *hus* opens its article (site decisions 158: the default shows the list)
  await p.eval(`localStorage.clear(); sessionStorage.clear(); localStorage.setItem('labels', 'en');
    localStorage.setItem('nbonly', 'on'); localStorage.setItem('listview', 'multi'); true`);
  R.nbl = {};
  for (const [name, url] of [['hus', hus], ['go', base + '/bm-en/' + args.go + '/'],
                             ['word', base + '/bm-en/' + encodeURIComponent(args.word) + '/']]) {
    await go(url, 900);
    await until(p, `document.querySelector('main h3')`, 10000);
    await sleep(500);
    R.nbl[name] = await p.eval(LABELS('main'));
  }
  // a small article opened from hus: no English label shown inside it (ordbokene's layout, whose
  // "Example" headings are labels the page script draws inside a small article too)
  await p.eval(`localStorage.setItem('layout', 'ordbokene'); true`);
  await go(hus, 900);
  const miniOpened = await press(p, 'main .ordpar-pair > span[lang=nb] a.ordbok-xword');
  await until(p, `document.querySelector('.ordbok-xmini .ordpar-mbody, .ordbok-xmini .mini-pair')`, 8000);
  await sleep(600);
  R.nbl.mini = Object.assign({ opened: miniOpened }, await p.eval(LABELS('.ordbok-xmini')));
  await p.eval(`localStorage.removeItem('layout'); true`);
  // the layer off by the icon: the reader's own English labels again, `labels` still "en"
  await go(hus, 900);
  await press(p, ICON);
  await sleep(500);
  R.nbl.off = await p.eval(LABELS('main'));
  await p.eval(`localStorage.setItem('nbonly', 'on'); localStorage.removeItem('labels'); true`);   // for "back"

  // back off by the icon: the reader's own settings again
  await p.eval(`localStorage.setItem('exeye', 'on'); true`);
  await p.goto(hus, 900);
  await press(p, ICON);
  await sleep(500);
  R.back = await p.eval(STATE);
  await done({ base, R });
});
