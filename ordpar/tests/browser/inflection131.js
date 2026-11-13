// Site decisions 131 (the deck's request, promised by the site session): `inflection.js`
// `mountAll` reads a paradigm island by `script.textContent || script.innerHTML`. The deck carries
// its islands in `<template>`s (`deck/render.py` `editor_safe`: Anki's editor deletes a field's
// scripts), whose `textContent` is empty — the content of a template is a separate fragment — so
// the deck's tables depend on the `innerHTML` fallback.
//
// On a page of the served site: the island of a real article page (args.id) put into a
// `<template>`, a mount point naming it, the given `inflection.js` (args.path: the shipped file, or
// a copy) evaluated in the page, then `ordparInflection.mountAll`. Read: the template's
// `textContent` (empty), whether a table was drawn, and its forms.
//
// args: { id, path }
// Result: { textContent, innerHTML, mounted, tables, forms: [...] }
import { open, base, args, run, done } from './cdp.js';
import { readFileSync } from 'fs';

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  await p.goto(base + '/about/', 300);
  const src = readFileSync(args.path, 'utf8');
  const res = await p.eval(`(async () => {
    const page = await (await fetch('/bm-en/${args.id}/')).text();
    const m = /<script type="application\\/json" id="ordpar-paradigm"[^>]*>([\\s\\S]*?)<\\/script>/.exec(page);
    const box = document.createElement('div');
    box.innerHTML = '<template id="t131-island">' + m[1] + '</template>'
      + '<div class="ordpar-inflection" data-paradigm="t131-island"></div>';
    document.body.appendChild(box);
    (0, eval)(${JSON.stringify(src)});
    window.ordparInflection.mountAll(box);
    const t = document.getElementById('t131-island');
    return { textContent: t.textContent, innerHTML: t.innerHTML.length,
      mounted: box.querySelector('.ordpar-inflection').getAttribute('data-ordpar-mounted'),
      tables: box.querySelectorAll('table').length,
      forms: Array.from(box.querySelectorAll('td')).map(td => td.textContent.trim()).filter(Boolean).slice(0, 12) };
  })()`);
  done(res);
});
