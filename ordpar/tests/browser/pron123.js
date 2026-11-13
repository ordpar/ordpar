// Decisions 123 (Robin, 2026-10-24): Bokmålsordboka's pronunciation field, as the browser shows it,
// and the Help page that holds the note on its marks (none in the article).
//
// At 1280×900, in a fresh context, for each `formulas` choice (none stored: the default, `both` since site decisions 174, `en` before; `en`;
// `no`; `both`): every page of args.pages opened and its article read — the pronunciation
// section's visible text (`innerText`, so the hidden language's half is left out), whether it comes
// after the inflection toggle and before the etymology section, and how many "?" buttons
// (`.ordpar-hint-button`) the article holds — none since decisions 123's amendment (2026-11-02).
// On each page of args.keyed (a field using a mark) the "?" is looked for, and would be read
// closed, clicked, read open and clicked again were it there. Then `/help/`: its `#pronunciation` heading and the paragraph
// after it; and the footer's links on an article page and on the home page, as shown once the
// page script has added its own.
//
// args: { pages: [id…], footer: [path…] }
// Result: { base, cases: { "<choice>": { <id>: { text, order, hints } } },
//   key: { <id>: { before, open, closed } }, help: { head, note },
//   footer: { "<path>": [link text…] } }
import { open, base, args, run, done } from './cdp.js';

const READ = `(() => {
  const art = document.querySelector('.ordpar-article');
  if (!art) return null;
  const sec = art.querySelector('section.ordpar-pron');
  const infl = art.querySelector('details.ordpar-infl-toggle');
  const ety = [...art.querySelectorAll('section')].find(s => (s.querySelector('h3') || {}).textContent === 'Etymology');
  const after = (a, b) => !!(a && b && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING));
  return { text: sec ? (sec.querySelector('h3').innerText + ' ' + sec.querySelector('.ordbok-body').innerText).replace(/\\s+/g, ' ').trim() : null,
           order: !!sec && (!infl || after(infl, sec)) && (!ety || after(sec, ety)),
           hints: document.querySelector('.ordpar-card').querySelectorAll('.ordpar-hint-button').length };
})()`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const cases = {};
  await p.goto(base + '/bm-en/', 400);
  for (const choice of ['default', 'en', 'no', 'both']) {
    await p.eval(`localStorage.clear(); ${choice === 'default' ? '' : `localStorage.setItem('formulas', '${choice}');`} true`);
    const pages = {};
    for (const id of args.pages) {
      await p.goto(base + '/bm-en/' + id + '/', 600);
      pages[id] = await p.eval(READ);
    }
    cases[choice] = pages;
  }
  await p.eval('localStorage.clear(); true');
  const STATE = `(() => { const b = document.querySelector('.ordpar-pron .ordpar-hint-button');
    if (!b) return null; const x = document.querySelector('.ordpar-pron .ordpar-hint-box');
    const c = document.querySelector('.ordpar-card').getBoundingClientRect();
    const r = x && x.getBoundingClientRect();
    return { expanded: b.getAttribute('aria-expanded'), box: x ? x.textContent : null,
             inside: !!r && r.left >= c.left - 1 && r.right <= c.right + 1 }; })()`;
  const CLICK = `(() => { const b = document.querySelector('.ordpar-pron .ordpar-hint-button');
    b.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })); return true; })()`;
  const key = {};
  for (const id of args.keyed) {
    await p.goto(base + '/bm-en/' + id + '/', 600);
    const before = await p.eval(STATE);
    if (!before) { key[id] = { before, open: {}, closed: null }; continue; }
    delete before.inside;
    await p.eval(CLICK); await new Promise(r => setTimeout(r, 150));
    const open = await p.eval(STATE);
    await p.eval(CLICK); await new Promise(r => setTimeout(r, 150));
    const closed = await p.eval(STATE); delete closed.inside;
    key[id] = { before, open, closed };
  }
  await p.goto(base + '/help/', 400);
  const help = await p.eval(`(() => { const h = document.getElementById('pronunciation');
    if (!h) return null; const n = h.nextElementSibling;
    return { head: h.textContent.trim(), note: n ? n.textContent.trim() : null }; })()`);
  const footer = {};
  for (const path of args.footer) {
    await p.goto(base + path, 800);
    footer[path] = await p.eval(`[...document.querySelectorAll('.ordpar-footer-nav a')].map(a => a.textContent.trim() + ' ' + a.getAttribute('href'))`);
  }
  await done({ base, cases, key, help, footer });
});
