// Decisions 118 (Robin, 2026-10-24): a Norwegian-only article's compound lists linked, under a
// Norwegian label whatever the `formulas` setting.
//
// At 1280×900, in a fresh context, for each `formulas` choice (none stored: the default, `both` since site decisions 174, `en` before;
// `en`; `no`; `both`): every page of args.pages is opened and each compound list in its article
// (`.ordpar-comp`, outside any mini) read as the browser shows it — the label's visible text
// (`innerText`, so a hidden `ordpar-cl-*` half is left out), and each compound's word, its link's
// `href` (null for plain text) and whether it carries a peek. Then, for each of args.minis
// ([from, to]), the mini of `to` opened by a click on its link on `from`, and its compound lists
// read the same way.
//
// args: { pages: [id…], minis: [[from, to]…] }
// Result: { base, cases: { "<choice>": { pages: { <id>: [list…] }, minis: { "<from>-<to>": { opened,
//   lists: [list…] } } } } }, a list being { label, items: [{ word, href, peek }] }
import { open, base, args, run, done } from './cdp.js';

const LISTS = scope => `(() => {
  const root = ${scope};
  if (!root) return null;
  return [...root.querySelectorAll('.ordpar-comp')]
    .filter(c => ${scope === 'document' ? "!c.closest('.ordbok-xmini')" : 'true'})
    .map(c => {
      const def = c.querySelector(':scope > .ordbok-def');
      const label = def && def.firstElementChild && def.firstElementChild.tagName === 'EM'
        ? def.firstElementChild.innerText.trim() : null;
      const items = [];
      for (const k of [...def.children].slice(1)) {
        const a = k.matches('a') ? k : k.querySelector('a.ordbok-xword');
        items.push({ word: k.innerText.trim(), href: a ? a.getAttribute('href') : null,
                     peek: !!k.querySelector('.ordbok-xpeek') });
      }
      return { label, items };
    });
})()`;

const MINI = "[...document.querySelectorAll('.ordpar-mopen > .ordbok-xmini')].find(x => x.getClientRects().length)";

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const cases = {};
  await p.goto(base + '/bm-en/', 400);
  for (const choice of ['default', 'en', 'no', 'both']) {
    await p.eval(`localStorage.clear(); ${choice === 'default' ? '' : `localStorage.setItem('formulas', '${choice}');`} true`);
    const pages = {}, minis = {};
    for (const id of args.pages) {
      await p.goto(base + '/bm-en/' + id + '/', 600);
      pages[id] = await p.eval(LISTS('document'));
    }
    for (const [from, to] of args.minis) {
      await p.goto(base + '/bm-en/' + from + '/', 600);
      const opened = await p.eval(`(async () => {
        const a = [...document.querySelectorAll('a.ordbok-xword[href^="/bm-en/${to}/"]')].find(x => !x.closest('.ordbok-xmini'));
        if (!a) return false;
        a.scrollIntoView({ block: 'center' });
        a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
        for (let t = 0; t < 80; t++) { if (document.querySelector('.ordpar-mopen .ordpar-mbody .ordbok-def')) break;
          await new Promise(r => setTimeout(r, 100)); }
        await new Promise(r => setTimeout(r, 300));
        return !!(${MINI}); })()`);
      minis[from + '-' + to] = { opened, lists: opened ? await p.eval(LISTS(MINI)) : null };
    }
    cases[choice] = { pages, minis };
  }
  await done({ base, cases });
});
