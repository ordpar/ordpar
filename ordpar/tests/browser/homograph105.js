// Decisions 105 (Robin, 2026-10-23): the homograph numeral in his chosen style, in every place.
//
// For one theme (args.dark), at 1280×900, in a fresh context, the numerals of each place are
// measured against what they follow: in the article's headword line and a full search result the
// `.ordbok-lemma` beside them, in a row (inflected-form rows, the list view, favourites)
// the headword span they sit in, in a gloss list (the suggestions, Recent, History) the gloss text
// (`.ordpar-option-gl`). For each numeral: the size ratio, the colour, the weight, and its raise —
// its baseline's height above the baseline of what it follows, read off a zero-size inline-block
// probe put in each (an empty inline-block's bottom edge is the baseline it sits on).
//
// args: { dark: bool }
// Result: { base, places: { <place>: [{ text, fs, ref, ratio, color, weight, raise }] } }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

// measure every numeral `sel` finds (at most `max`)
const MEASURE = (sel, max = 4) => `(() => {
  function probe(el) {
    const s = document.createElement('span');
    s.style.cssText = 'display:inline-block;width:0;height:0;padding:0;margin:0;border:0';
    el.appendChild(s); const y = s.getBoundingClientRect().top; s.remove(); return y;
  }
  return [...document.querySelectorAll(${JSON.stringify(sel)})].filter(n => n.getClientRects().length)
    .slice(0, ${max}).map(n => {
      let ref = n.closest('.ordpar-option-gl'), kind = 'gloss';
      if (!ref) {
        let k = n.previousElementSibling;
        while (k && k.classList.contains('ordpar-visually-hidden')) k = k.previousElementSibling;
        if (k && k.classList.contains('ordbok-lemma')) { ref = k; kind = 'lemma'; }
        else { ref = n.parentElement; kind = 'parent'; }
      }
      const cs = getComputedStyle(n), rs = getComputedStyle(ref);
      const fs = parseFloat(cs.fontSize), rfs = parseFloat(rs.fontSize);
      return { text: n.textContent, kind, fs: Math.round(fs * 100) / 100, ref: Math.round(rfs * 100) / 100,
        ratio: Math.round(fs / rfs * 1000) / 1000, color: cs.color, weight: cs.fontWeight,
        raise: Math.round((probe(ref) - probe(n)) * 100) / 100 };
    });
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
    await until(p, `document.querySelectorAll('#ordpar-listbox .ordpar-option-gl .ordbok-homograph').length > 0
      && !document.querySelector('#ordpar-listbox .is-pending')`);
  }
  await sleep(700);
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const places = {};
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', ${JSON.stringify(args.dark ? 'dark' : 'light')}); true`);
  // the article's headword line
  await p.goto(base + '/bm-en/13791/', 800);
  places.article = await p.eval(MEASURE('.ordbok-head .ordbok-homograph'));
  // favourites: hearts clicked on two pages
  for (const id of [36349, 13791]) {
    await p.goto(base + '/bm-en/' + id + '/', 800);
    await until(p, `!!document.querySelector('.ordpar-heart')`, 4000);
    await p.eval(`(() => { const h = document.querySelector('.ordpar-heart'); if (h) h.click(); return !!h; })()`);
  }
  // a full result (the list view off), the inflected-form rows
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/?q=lysning', 500);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordbok-head .ordbok-homograph').length > 0`);
  await sleep(500);
  places.full = await p.eval(MEASURE('[data-ordpar-results] .ordbok-head .ordbok-homograph'));
  await p.goto(base + '/bm-en/?q=lysingen', 500);
  await until(p, `document.querySelectorAll('.ordpar-hit .ordbok-homograph').length > 0`);
  places.inflected = await p.eval(MEASURE('.ordpar-hit .ordbok-homograph'));
  // the list view's rows
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  await p.goto(base + '/bm-en/?q=lysning', 500);
  await until(p, `document.querySelectorAll('.ordpar-row-word .ordbok-homograph').length > 0`);
  places.list = await p.eval(MEASURE('.ordpar-row-word .ordbok-homograph'));
  await p.eval(`localStorage.removeItem('listview'); true`);
  // History: searches the site records (its rows show the query, so its numerals are in the gloss lists)
  for (const q of ['tore', 'lysning', 'fange']) {
    await p.goto(base + '/bm-en/?q=' + encodeURIComponent(q), 500);
    await until(p, `!!document.querySelector('.ordpar-row-button, .ordpar-entry, [data-ordpar-results] .ordbok-head')`);
    await sleep(300);
  }
  await p.goto(base + '/history/', 500);
  await until(p, `document.querySelectorAll('main .ordbok-homograph').length > 0`);
  await sleep(800);
  places.historyHead = await p.eval(`document.querySelectorAll('main .ordbok-homograph:not(.ordpar-option-gl .ordbok-homograph)').length`);
  places.historyGloss = await p.eval(MEASURE('main .ordpar-option-gl .ordbok-homograph'));
  await p.goto(base + '/favourites/', 500);
  await until(p, `document.querySelectorAll('main .ordbok-homograph').length > 0`);
  places.favourites = await p.eval(MEASURE('main .ordbok-homograph'));
  // the suggestions' gloss list, and Recent
  await suggest(p, 'fange');
  places.suggest = await p.eval(MEASURE('#ordpar-listbox .ordpar-option-gl .ordbok-homograph'));
  places.suggestHead = await p.eval(`document.querySelectorAll('#ordpar-listbox .ordbok-homograph:not(.ordpar-option-gl .ordbok-homograph)').length`);
  await suggest(p, '');
  places.recent = await p.eval(MEASURE('#ordpar-listbox .ordpar-option-gl .ordbok-homograph'));
  const dark = await p.eval(`document.documentElement.classList.contains('nightMode')`);
  await done({ base, dark, places });
});
