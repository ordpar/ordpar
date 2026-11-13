// Decisions 116 (Robin, 2026-10-24): only the summary glosses semibold, the "·" between glosses faded.
//
// For one theme (args.dark), at 1280×900, in a fresh context, every place a row shows a gloss is
// opened and its text read piece by piece: each text node (not a homograph numeral, not a
// visually hidden reading) with the computed weight and colour of the element it sits in, its
// `lang`, and whether it is a separator (" · "). The places: the suggestions for *fange*, *fly* and
// *båtdekk*; Recent and History after searching *fange*, *fly*, *båtdekk*, *hus*; the list view for
// *fly* and *båtdekk*; the inflected-form rows under *fanger* (list view); favourites (*fly* V, *fly*
// I — Norwegian only — and *båtdekk*); the article head of *hus*; the mini's header for *bosted*
// opened on *hus*. Which texts are summary glosses the Python side knows (the data); this script
// only reads.
//
// args: { dark: bool }
// Result: { base, dark, muted, text, places: { <place>: [{ t, w, c, lang, sep }] } }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

// the pieces of every element `sel` finds that is shown
const PIECES = sel => `(() => {
  const out = [];
  for (const box of document.querySelectorAll(${JSON.stringify(sel)})) {
    if (!box.getClientRects().length) continue;
    const w = document.createTreeWalker(box, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const e = n.parentElement;
      if (!n.data.trim() || e.closest('.ordbok-homograph, .ordpar-visually-hidden, .sr-only, .ordpar-option-more, .ordpar-tag')) continue;
      const cs = getComputedStyle(e), l = e.closest('[lang]');
      out.push({ t: n.data, w: cs.fontWeight, c: cs.color, lang: l ? l.getAttribute('lang') : '',
        sep: n.data.trim() === '\\u00b7' });
    }
  }
  return out;
})()`;

async function suggest(p, typed) {
  await p.goto(base + '/', 800);
  await until(p, `!!document.getElementById('ordpar-q') && document.getElementById('ordpar-q').getAttribute('role') === 'combobox'`);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.focus(); i.click(); return true; })()`);
  if (typed === '') {
    await until(p, `document.querySelectorAll('#ordpar-listbox > li.ordpar-option-recent').length > 0`);
  } else {
    await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(typed)};
      i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
    await until(p, `document.querySelectorAll('#ordpar-listbox > li:not(.ordpar-option-recent)').length > 0
      && !document.querySelector('#ordpar-listbox .is-pending')`);
  }
  await sleep(900);
  return p.eval(PIECES('#ordpar-listbox .ordpar-option-side'));
}

async function results(p, q, sel) {
  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(q), 500);
  await until(p, `document.querySelectorAll(${JSON.stringify(sel)}).length > 0
    && !document.querySelector(${JSON.stringify(sel.split(',').map(s => s.trim() + '.is-pending').join(', '))})`);
  await sleep(600);
  return p.eval(PIECES(sel));
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const places = {};
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  // the article head, and the mini's header (bosted on hus)
  await p.goto(base + '/bm-en/24627/', 800);
  places.articleHead = await p.eval(PIECES('.ordbok-head .ordpar-gloss'));
  await p.eval(`(() => {
    const a = document.querySelector('a.ordbok-xword[href^="/bm-en/7136/"]'); if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    return true; })()`);
  // read the header once the mini is whole: its body in (`aria-busy` gone) and the mini tagged with
  // the article's language (`mini.js` `open`). The header is drawn at the click, before the fetch,
  // and until the body arrives it inherits the Norwegian line's `lang` — a fixed 300 ms read it
  // there on a slow answer (the flake of 2026-10-25, evidence/rowgloss116-flake-2026-10-25/)
  await until(p, `!!document.querySelector('.ordpar-mopen .ordpar-fmini:not([aria-busy]) .mini-head .mini-gloss')
    && !!document.querySelector('.ordpar-mopen > .ordbok-xmini[lang]')`, 20000);
  places.miniHead = await p.eval(PIECES('.ordpar-mopen .mini-head .mini-gloss'));
  // favourites: hearts on three pages
  for (const id of [15544, 15540, 8611]) {
    await p.goto(base + '/bm-en/' + id + '/', 800);
    await until(p, `!!document.querySelector('.ordpar-heart')`, 4000);
    await p.eval(`(() => { const h = document.querySelector('.ordpar-heart'); if (h) h.click(); return !!h; })()`);
  }
  // the list view's rows, the inflected-form rows (they record History too)
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  places.listFly = await results(p, 'fly', '.ordpar-row-snippet');
  places.listBatdekk = await results(p, 'båtdekk', '.ordpar-row-snippet');
  places.inflected = await results(p, 'fanger', '.ordpar-hit-snippet');
  await p.eval(`localStorage.removeItem('listview'); true`);
  for (const q of ['hus', 'fange']) {
    await p.goto(base + '/bm-en/?q=' + encodeURIComponent(q), 500);
    await until(p, `!!document.querySelector('[data-ordpar-results] .ordbok-head')`);
    await sleep(300);
  }
  await p.goto(base + '/history/', 500);
  await until(p, `document.querySelectorAll('main .ordpar-option-side').length > 0 && !document.querySelector('main .is-pending')`);
  await sleep(1200);
  places.history = await p.eval(PIECES('main .ordpar-option-side'));
  await p.goto(base + '/favourites/', 500);
  await until(p, `document.querySelectorAll('main .ordpar-row-snippet').length > 2`);
  await sleep(1200);
  places.favourites = await p.eval(PIECES('main .ordpar-row-snippet'));
  places.suggestFange = await suggest(p, 'fange');
  places.suggestFly = await suggest(p, 'fly');
  places.suggestBatdekk = await suggest(p, 'båtdekk');
  places.recent = await suggest(p, '');
  const colours = await p.eval(`(() => { const s = getComputedStyle(document.documentElement);
    return { muted: s.getPropertyValue('--ordpar-muted').trim(), text: s.getPropertyValue('--ordpar-text').trim(),
      night: document.documentElement.classList.contains('nightMode') }; })()`);
  await done({ base, dark: colours.night, muted: colours.muted, text: colours.text, places });
});
