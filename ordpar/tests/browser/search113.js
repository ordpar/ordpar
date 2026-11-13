// Decisions 113 (Robin, 2026-10-24): the search on a phone.
//
// (1) After a search made by Enter or by choosing a suggestion (a tap or click on it, or Enter on a
// highlighted one), the search field lets go of the focus on a touch screen, so a phone's keyboard
// closes and the result shows; with a mouse it keeps it (as ordbokene.no's). Read on the search page
// (the search answered in place) and on an article page (the search goes to the search page).
// (2) Every search field the site has carries autocapitalize="none" (a phone keyboard starts in
// small letters): the article, search, 404, settings and favourites pages.
//
// args: { mobile: bool, word: a word with suggestions, id: an article }
// Result: { base, coarse, cases: { <name>: { active, results, value } }, fields: { <page>: [...] } }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  for (let t = 0; t < ms; t += 100) { if (await p.eval(expr)) return true; await sleep(100); }
  return false;
}
async function key(p, k, code, vk, text) {
  await p.send('Input.dispatchKeyEvent', text ? { type: 'keyDown', key: k, code, windowsVirtualKeyCode: vk, text }
    : { type: 'rawKeyDown', key: k, code, windowsVirtualKeyCode: vk });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk });
}
const STATE = `(() => { const a = document.activeElement, q = document.getElementById('ordpar-q');
  return { active: a === q ? 'search' : (a ? a.tagName.toLowerCase() + (a.id ? '#' + a.id : '') : null),
    results: !!document.querySelector('[data-ordpar-results] .ordbok-ex-list, [data-ordpar-results] .ordpar-row-button, [data-ordpar-results] article, .ordpar-article'),
    value: q ? q.value : null, path: location.pathname + location.hash }; })()`;

/** Put the focus in the search field as the reader would: a tap on a phone, a click otherwise. */
async function into(p) {
  const r = await p.eval(`(() => { const q = document.getElementById('ordpar-q'); q.scrollIntoView({ block: 'center' });
    const b = q.getBoundingClientRect(); return { x: b.left + 20, y: b.top + b.height / 2 }; })()`);
  if (args.mobile) await p.tap(r.x, r.y); else await p.click(r.x, r.y);
  await sleep(200);
  await p.eval(`(() => { const q = document.getElementById('ordpar-q'); q.focus(); q.select(); return true; })()`);
}
async function type(p, text) {
  await p.send('Input.insertText', { text });
  await until(p, `document.querySelectorAll('#ordpar-listbox .ordpar-option').length > 0`, 8000);
  await sleep(300);
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  const coarse = await p.eval(`matchMedia('(pointer: coarse)').matches`);
  const search = base + '/bm-en/';

  // the search page: Enter
  await p.goto(search, 800);
  await into(p); await type(p, args.word);
  await key(p, 'Enter', 'Enter', 13, '\r');
  await sleep(1200);
  cases.enter = await p.eval(STATE);

  // the search page: a suggestion pressed
  await p.goto(base + '/bm-en/' + args.id + '/', 300);
  await p.goto(search, 800);
  await into(p); await type(p, args.prefix);
  const o = await p.eval(`(() => { const li = document.querySelectorAll('#ordpar-listbox .ordpar-option')[1]
      || document.querySelector('#ordpar-listbox .ordpar-option'); const r = li.getBoundingClientRect();
    return { x: r.left + Math.min(40, r.width / 2), y: r.top + r.height / 2 }; })()`);
  if (args.mobile) await p.tap(o.x, o.y); else await p.click(o.x, o.y);
  await sleep(1200);
  cases.pick = await p.eval(STATE);

  // the search page: Enter on a highlighted suggestion
  await p.goto(base + '/bm-en/' + args.id + '/', 300);
  await p.goto(search, 800);
  await into(p); await type(p, args.prefix);
  await key(p, 'ArrowDown', 'ArrowDown', 40);
  await sleep(150);
  await key(p, 'Enter', 'Enter', 13, '\r');
  await sleep(1200);
  cases.pickKey = await p.eval(STATE);

  // an article page: Enter goes to the search page
  await p.goto(base + '/bm-en/' + args.id + '/', 800);
  await into(p); await type(p, args.word);
  const loaded = p.waitEvent('Page.loadEventFired', 8000);
  await key(p, 'Enter', 'Enter', 13, '\r');
  await loaded; await sleep(1200);
  cases.fromArticle = await p.eval(STATE);

  // every search field: the pages
  const fields = {};
  for (const [name, path] of [['article', '/bm-en/' + args.id + '/'], ['search', '/bm-en/'], ['404', '/404.html'],
                              ['settings', '/settings/'], ['favourites', '/favourites/']]) {
    await p.goto(base + path, 500);
    fields[name] = await p.eval(`[...document.querySelectorAll('input')].filter(i =>
        i.type === 'search' || i.getAttribute('role') === 'combobox' || !!i.closest('form[role=search]'))
      .map(i => ({ id: i.id, autocapitalize: i.getAttribute('autocapitalize'), autocomplete: i.getAttribute('autocomplete'),
                   spellcheck: i.getAttribute('spellcheck'), autocorrect: i.getAttribute('autocorrect') }))`);
  }
  await done({ base, coarse, cases, fields });
});
