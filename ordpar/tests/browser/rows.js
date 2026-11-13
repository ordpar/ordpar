// Decisions 100 (4): the rows of the search dropdown, its Recent list and the list view keep their height.
//
// For one viewport (args.w × args.h, args.mobile), in a fresh context: a few searches are made
// (`/bm-en/?q=…`, which records them in History), then on the home page the empty search box is
// focused (the Recent rows) and "hu" is typed (the suggestion rows); the same again with the
// setting `suggestrows` = roomy; and the list view of a search whose rows have and lack a
// homograph numeral. Every row's height is returned, by group.
//
// args: { w, h, mobile, history: [q, …], typed: 'hu', list: 'la' }
// Result: { groups: { suggest, 'suggest-roomy', recent, 'recent-roomy', list: [{ text, h, numeral? }] } }
import { open, base, args, run, done, sleep } from './cdp.js';

const ROWS = `[...document.querySelectorAll('#ordpar-listbox > li')].filter(li => li.getClientRects().length)
  .map(li => ({ text: li.textContent.replace(/\\s+/g, ' ').trim().slice(0, 50), h: Math.round(li.getBoundingClientRect().height * 100) / 100 }))`;

async function until(p, expr, ms = 8000) {
  // site decisions 117: a search for a word with a page lands on that page, whose built rows the
  // script replaces; wait for the script's (the built headline gone) before reading anything
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}

async function dropdown(p, typed) {
  await p.goto(base + '/', 500);
  await until(p, `!!document.getElementById('ordpar-q') && document.getElementById('ordpar-q').getAttribute('role') === 'combobox'`);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.focus(); i.click(); return true; })()`);
  await until(p, `document.querySelectorAll('#ordpar-listbox > li.ordpar-option-recent').length > 0`);
  await sleep(600);                                     // the rows' glosses fill in, then fit
  const recent = await p.eval(ROWS);
  await p.eval(`(() => { const i = document.getElementById('ordpar-q'); i.value = ${JSON.stringify(typed)};
    i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await until(p, `document.querySelectorAll('#ordpar-listbox > li:not(.ordpar-option-recent)').length > 3
    && !document.querySelector('#ordpar-listbox .is-pending')`);
  await sleep(600);
  return { recent, suggest: await p.eval(ROWS) };
}

run(async () => {
  const p = await open({ w: args.w, h: args.h, mobile: !!args.mobile });
  const groups = {};
  for (const q of args.history) {
    await p.goto(base + '/bm-en/?q=' + encodeURIComponent(q), 300);
    await until(p, `!!document.querySelector('.ordpar-row-button, .ordpar-entry')`);
    await sleep(300);
  }
  const hist = await p.eval(`(JSON.parse(localStorage.getItem('history') || '[]')).length`);
  let r = await dropdown(p, args.typed);
  groups.recent = r.recent; groups.suggest = r.suggest;
  await p.eval(`localStorage.setItem('suggestrows', 'roomy'); true`);
  r = await dropdown(p, args.typed);
  groups['recent-roomy'] = r.recent; groups['suggest-roomy'] = r.suggest;
  await p.eval(`localStorage.removeItem('suggestrows'); true`);
  await p.goto(base + '/bm-en/?q=' + encodeURIComponent(args.list), 300);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 1`);
  await sleep(800);                                     // the snippets arrive after the rows
  groups.list = await p.eval(`[...document.querySelectorAll('.ordpar-row-button')].map(b => ({
    text: b.querySelector('.ordpar-row-word').textContent.replace(/\\s+/g, ' ').trim(),
    h: Math.round(b.getBoundingClientRect().height * 100) / 100, numeral: !!b.querySelector('.ordbok-homograph') }))`);
  await done({ base, history: hist, groups });
});
