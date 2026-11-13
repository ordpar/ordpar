// Site decisions 158 (Robin, 2026-11-01): the list view also when a search finds an inflected form,
// the new default — "only if there are just 1 search match, and no inflected forms hits, does the
// search open straight to the article". Every place a search opens follows the setting (one style).
//
// For one viewport (args.mobile: a phone, tapped; else a computer, clicked), each step in a fresh
// context (storage empty) unless it says otherwise; `listview` stored first where a step names it:
//   address      — a shared search address, `/bm-en/#q=<q>` (sent on to the word page, 117)
//   page         — the word page opened directly, `/bm-en/<q>/`
//   typed        — typed in the search page's box and submitted (answered in place)
//   random       — Random word on the search page, the draw made to fall on <q> (`Math.random`
//                  set from `random.json`, so the button's own code draws it)
//   history      — after `typed`, the History page's row for <q> clicked
//   recent       — after `typed`, the search page's box focused empty and its Recent row clicked
//   form         — a form page (args.form: a word found only as an inflected form)
// for each case of args.cases ({q, listview?}). After each: the path, the list rows and full
// articles shown, the inflected-form section and where it starts against the window's height.
//
// args: { mobile, cases: [{name, q, listview?, steps: [...]}], form }
// Result: { base, got: { <case>: { <step>: {path, rows, full, inflected, inflTop, height} } } }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 20000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// the results drawn for `q`: rows or articles there, none still loading, no "Searching…" line
const SETTLED = q => `document.readyState === 'complete'
  && !!document.querySelector('[data-ordpar-results] .ordpar-hits, [data-ordpar-results] .ordpar-inflected')
  && !document.querySelector('[data-ordpar-results] > .ordpar-empty')
  && !document.querySelector('.ordpar-result[aria-busy="true"]')
  && (document.getElementById('ordpar-q') || {}).value === ${JSON.stringify(q)}`;

const READ = `(() => {
  const R = document.querySelector('[data-ordpar-results]') || document;
  const sec = R.querySelector('.ordpar-inflected');
  return { path: decodeURIComponent(location.pathname), hash: location.hash,
    rows: R.querySelectorAll('.ordpar-hits .ordpar-row').length,
    full: R.querySelectorAll('.ordpar-hits .ordpar-result').length,
    inflected: sec ? sec.querySelectorAll('a').length : 0,
    inflTop: sec ? Math.round(sec.getBoundingClientRect().top + scrollY) : null,
    height: innerHeight };
})()`;

async function press(p, selector) {
  const at = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(selector)});
    if (!b || !b.getClientRects().length) return null; b.scrollIntoView({ block: 'center' });
    const r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!at) return false;
  if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
  return true;
}

async function fresh(c) {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  await p.goto(base + '/bm-en/', 500);
  await p.eval(`localStorage.clear(); sessionStorage.clear();
    ${c.listview ? `localStorage.setItem('listview', ${JSON.stringify(c.listview)});` : ''} true`);
  return p;
}

async function settle(p, q) {
  const ok = await until(p, SETTLED(q));
  await sleep(400);                     // a re-render on a late setting would show here
  const r = await p.eval(READ);
  r.settled = ok;
  return r;
}

async function typed(p, q) {
  await p.goto(base + '/bm-en/', 600);
  await p.eval(`(() => { const b = document.getElementById('ordpar-q'); b.value = ${JSON.stringify(q)};
    b.form.requestSubmit(); return true; })()`);
  return settle(p, q);
}

const STEPS = {
  async address(p, q) {
    await p.goto(base + '/bm-en/#q=' + encodeURIComponent(q), 600);
    return settle(p, q);
  },
  async page(p, q) {
    await p.goto(base + '/bm-en/' + encodeURIComponent(q) + '/', 600);
    return settle(p, q);
  },
  typed,
  async random(p, q) {
    await p.goto(base + '/bm-en/', 600);
    const i = await p.eval(`fetch('/index/random.json').then(r => r.json()).then(l => {
      const i = l.indexOf(${JSON.stringify(q)}); if (i < 0) return -1;
      Math.random = () => (i + 0.5) / l.length; return i; })`);
    if (i < 0) return { error: q + ' is not in random.json' };
    if (!await press(p, '.ordpar-random')) return { error: 'no Random word button' };
    return settle(p, q);
  },
  async history(p, q) {
    await typed(p, q);
    await sleep(500);
    await p.goto(base + '/history/', 600);
    await until(p, `!!document.querySelector('a.ordpar-history-link')`);
    const sel = `a.ordpar-history-link`;
    const loaded = p.waitEvent('Page.loadEventFired', 12000);
    if (!await press(p, sel)) return { error: 'no History row' };
    await loaded;
    return settle(p, q);
  },
  async recent(p, q) {
    await typed(p, q);
    await sleep(500);
    await p.goto(base + '/bm-en/', 600);
    await p.eval(`(() => { const b = document.getElementById('ordpar-q'); b.value = ''; b.focus();
      b.dispatchEvent(new Event('focus')); b.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
    if (!await until(p, `[...document.querySelectorAll('[role="option"]')].some(o => o.getClientRects().length)`, 6000)) {
      return { error: 'no Recent row' };
    }
    if (!await press(p, '[role="option"]')) return { error: 'no Recent row to press' };
    return settle(p, q);
  },
};

run(async () => {
  const got = {};
  for (const c of args.cases) {
    got[c.name] = {};
    for (const step of c.steps) {
      const p = await fresh(c);
      try {
        got[c.name][step] = await STEPS[step](p, c.q);
      } catch (e) {
        got[c.name][step] = { error: String(e && e.message || e) };
      }
      await p.close();
    }
  }
  if (args.form) {
    const p = await fresh({});
    got.form = { page: await STEPS.page(p, args.form) };
    await p.close();
  }
  await done({ base, got });
});
