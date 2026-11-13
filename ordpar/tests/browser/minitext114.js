// Decisions 114 (Robin, 2026-10-24): the mini's text sizes, and the setting `minitext`.
//
// For one viewport (args.mobile: a phone; else a computer), in a fresh context, for each theme
// (light, dark) and each choice of `minitext` (none stored: the default; `article`; `smaller`): a
// real mini opened on args.from (*hus*) from its link to args.to (*bosted*), measured with the
// computed styles: the header line (`.mini-head`), its gloss (`.mini-gloss`: size, weight, style,
// colour), the mini's text colour, and the English line of its first definition beside the
// English line of the article's own first definition (outside any mini). Then the settings page:
// the field's place under Small articles, its choices and their order.
//
// Result: { base, cases: { "<theme>-<choice>": { opened, head, gloss, weight, italic, colour,
//   miniColour, articleColour, def, articleDef, cls } }, settings: {...} }
import { open, base, args, run, done, sleep } from './cdp.js';

const px = 'v => parseFloat(v)';

const MEASURE = `(() => {
  const cs = e => e ? getComputedStyle(e) : null;
  const px = ${px};
  const m = [...document.querySelectorAll('.ordpar-mopen > .ordbok-xmini')].find(x => x.getClientRects().length);
  if (!m) return { opened: false };
  const head = m.querySelector('.mini-head'), gloss = m.querySelector('.mini-head .mini-gloss');
  const box = m.querySelector('.ordpar-fmini') || m.querySelector('.mini') || m;
  const def = m.querySelector('.ordpar-mbody .ordbok-def[lang=en]');
  const art = [...document.querySelectorAll('.ordpar-article .ordbok-senses .ordbok-def[lang=en]')]
    .find(e => !e.closest('.ordbok-xmini'));
  const article = document.querySelector('.ordpar-article');
  return { opened: true,
    head: px(cs(head).fontSize), gloss: gloss ? px(cs(gloss).fontSize) : null,
    weight: gloss ? cs(gloss).fontWeight : null, italic: gloss ? cs(gloss).fontStyle : null,
    colour: gloss ? cs(gloss).color : null, headColour: cs(head).color, miniColour: cs(box).color,
    articleColour: cs(article).color,
    def: def ? px(cs(def).fontSize) : null, articleDef: art ? px(cs(art).fontSize) : null,
    bodyColour: def ? cs(def).color : null, articleDefColour: art ? cs(art).color : null,
    cls: [...document.documentElement.classList].filter(c => c.startsWith('ordpar-minitext') || c === 'nightMode') };
})()`;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  await p.goto(base + '/bm-en/', 400);
  for (const theme of ['light', 'dark']) {
    for (const choice of ['default', 'article', 'smaller']) {
      await p.eval(`localStorage.clear(); localStorage.setItem('theme', '${theme}');
        ${choice === 'default' ? '' : `localStorage.setItem('minitext', '${choice}');`} true`);
      await p.goto(base + '/bm-en/' + args.from + '/', 800);
      await p.eval(`(async () => {
        const a = document.querySelector('a.ordbok-xword[href^="/bm-en/${args.to}/"]'); if (!a) return false;
        a.scrollIntoView({ block: 'center' });
        a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
        for (let t = 0; t < 80; t++) { if (document.querySelector('.ordpar-mopen .ordpar-mbody .ordbok-def')) break;
          await new Promise(r => setTimeout(r, 100)); }
        await new Promise(r => setTimeout(r, 300));
        return true; })()`);
      cases[theme + '-' + choice] = await p.eval(MEASURE);
    }
  }
  // a change made in place applies at once (no reload): smaller, then back
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);
  await p.goto(base + '/bm-en/' + args.from + '/', 800);
  await p.eval(`(async () => {
    const a = document.querySelector('a.ordbok-xword[href^="/bm-en/${args.to}/"]'); if (!a) return false;
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 80; t++) { if (document.querySelector('.ordpar-mopen .ordpar-mbody .ordbok-def')) break;
      await new Promise(r => setTimeout(r, 100)); }
    return true; })()`);
  await p.eval(`(window.ordparShell && ordparShell.setSetting('minitext', 'smaller'), true)`);
  await p.frames();
  cases.inPlace = await p.eval(MEASURE);

  // the settings page
  await p.eval(`localStorage.clear(); true`);
  await p.goto(base + '/settings/', 800);
  const settings = await p.eval(`(() => {
    const f = document.querySelector('fieldset[data-setting="minitext"]');
    const order = [...document.querySelectorAll('fieldset[data-setting]')].map(x => x.getAttribute('data-setting'));
    const sub = f && f.closest('.ordpar-settings-sub');
    return { field: !!f, title: f ? f.querySelector('.ordpar-field-title').textContent : null,
      sub: sub ? sub.querySelector('h3').textContent : null,
      choices: f ? [...f.querySelectorAll('input[type=radio]')].map(r => [r.value, r.checked,
        (r.closest('label') || f.querySelector('label[for="' + r.id + '"]') || {}).textContent]) : null,
      hint: !!(f && f.querySelector('.ordpar-hint-button')),
      after: order.slice(order.indexOf('minispacing'), order.indexOf('minispacing') + 3) };
  })()`);
  await done({ base, cases, settings });
});
