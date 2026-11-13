// Site decisions 136 (Robin, 2026-10-26): the presets on the settings page, and the Help page's
// Settings section.
//
// For one viewport (args.w; args.mobile: a phone, the buttons tapped; else clicked), in a fresh
// context, on /settings/: a reader with the defaults before site decisions 174 stored (`emph` en,
// `formulas` en) — which button is pressed; then, with a dark theme chosen first: each preset pressed
// in turn (Concise, Default, English emphasized, For learners, Concise) — the stored value of every Article setting, which buttons are
// pressed, the status line, the theme still dark, the radios in step; one Article setting changed
// after Concise (a real click on its radio) leaves none pressed; For learners pressed, then a
// reload keeps it pressed; a setting changed from another document of the site (a same-origin
// frame, as another tab) unpresses it; the pressed button's look. Then Concise and the article
// args.id: no Norwegian definition line shows, and no example list shows more than two.
// With args.shots = {dir, prefix}: the page's top with each preset pressed, light and dark, and
// /help/#settings.
//
// args: { w, mobile, keys: [the Article settings], id, shots? }
// Result: { base, steps: [{preset, stored, pressed, status, theme, night, radiosInStep}], ... }
import { writeFileSync } from 'fs';
import { open, base, args, run, done, sleep } from './cdp.js';

const KEYS = JSON.stringify(args.keys);

const STATE = `(() => {
  const keys = ${KEYS};
  const stored = {}; keys.forEach(k => { stored[k] = localStorage.getItem(k); });
  const pressed = [...document.querySelectorAll('button[data-preset]')]
    .filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.getAttribute('data-preset'));
  // every Article radio / drop-down showing what ordparShell reads
  const inStep = keys.every(k => {
    const v = ordparShell.getSetting(k);
    const sel = document.querySelector('select[data-key="' + k + '"]');
    if (sel) return sel.value === v;
    const r = document.querySelector('input[data-key="' + k + '"][value="' + v + '"]');
    return !!r && r.checked;
  });
  const st = document.querySelector('.ordpar-settings-status');
  return { stored, pressed, status: st ? st.textContent : null, theme: localStorage.getItem('theme'),
    night: document.documentElement.classList.contains('nightMode'), radiosInStep: inStep,
    effective: Object.fromEntries(keys.map(k => [k, ordparShell.getSetting(k)])) };
})()`;

async function press(p, sel) {
  const at = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(sel)});
    if (!b) return null; b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!at) throw new Error('nothing to press at ' + sel);
  if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
  await sleep(250);
  await p.frames();
}

async function shot(p, name, js) {
  if (!args.shots) return null;
  await p.eval('window.scrollTo(0, 0); true');
  await p.frames();
  const box = await p.eval(js);
  if (!box) return null;
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 } });
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

// the page's top: from the top of the page to under the presets' box, the window's width
const TOP = `(() => { const s = document.querySelector('#presets'); if (!s) return null;
  const r = s.getBoundingClientRect();
  return { x: 0, y: 0, w: document.documentElement.clientWidth, h: r.bottom + scrollY + 12 }; })()`;
// the Help page's Settings section: its heading to the next one
const HELP = `(() => { const a = document.getElementById('settings'), b = document.getElementById('pronunciation');
  if (!a || !b) return null; const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
  return { x: 0, y: Math.max(0, ra.top + scrollY - 12), w: document.documentElement.clientWidth,
    h: rb.top - ra.top + 4 }; })()`;

run(async () => {
  const p = await open(args.mobile ? { w: args.w, h: 844, mobile: true } : { w: args.w, h: 900 });
  const res = { base, w: args.w, steps: [], shots: {} };
  const page = base + '/settings/';
  await p.goto(page, 500);
  await p.eval('localStorage.clear(); true');
  await p.reload(800);
  res.fresh = await p.eval(STATE);
  // site decisions 174: a reader on the old defaults, stored, is on English emphasized
  await p.eval(`localStorage.setItem('emph', 'en'); localStorage.setItem('formulas', 'en'); true`);
  await p.reload(800);
  res.oldDefaults = await p.eval(STATE);
  await p.eval('localStorage.clear(); true');
  await p.reload(800);
  res.layout = await p.eval(`(() => {
    const s = document.querySelector('#presets'), first = document.querySelector('section#style');
    const bs = [...document.querySelectorAll('#presets button[data-preset]')];
    const intro = s && s.querySelector('p.ordpar-settings-intro');
    return { present: !!s, beforeSections: !!(s && first && (s.compareDocumentPosition(first) & 4)),
      heading: s && s.querySelector('#presets-title') ? s.querySelector('#presets-title').textContent : null,
      named: s ? s.getAttribute('aria-labelledby') : null,
      intro: intro ? intro.textContent : null, introCls: intro ? intro.className : null,
      labels: bs.map(b => b.textContent), cls: bs.map(b => b.className),
      hint: !!(s && s.querySelector('.ordpar-hint-button')),
      inside: bs.every(b => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }),
      docWidth: document.documentElement.scrollWidth, vw: innerWidth,
      resetNote: (() => { const n = document.querySelector('.ordpar-stored .ordpar-reset-note');
        return n ? { text: n.textContent, cls: n.className,
          afterButtons: !!(n.previousElementSibling && n.previousElementSibling.classList.contains('ordpar-settings-actions')) } : null; })() };
  })()`);

  // site decisions 161: the "?" after the heading opens a line per preset and a link to Help,
  // inside the window; a second press closes it
  await press(p, '#presets .ordpar-hint-button');
  await sleep(200);
  res.hint = await p.eval(`(() => {
    const b = document.querySelector('#presets .ordpar-hint-button'), box = document.querySelector('#presets .ordpar-hint-box');
    if (!box) return { open: false, expanded: b && b.getAttribute('aria-expanded'), label: b && b.getAttribute('aria-label') };
    const r = box.getBoundingClientRect(), a = box.querySelector('a');
    return { open: true, expanded: b.getAttribute('aria-expanded'), label: b.getAttribute('aria-label'),
      lines: [...box.querySelectorAll('.ordpar-hint-line')].filter(l => l.querySelector('strong'))
        .map(l => ({ name: l.querySelector('strong').textContent, text: l.textContent })),
      link: a ? { text: a.textContent, href: a.getAttribute('href') } : null,
      inside: r.left >= 0 && r.right <= innerWidth, docWidth: document.documentElement.scrollWidth };
  })()`);
  await press(p, '#presets .ordpar-hint-button');
  await sleep(200);
  res.hint.closed = await p.eval(`!document.querySelector('#presets .ordpar-hint-box')`);

  // a dark theme first, by its radio
  await press(p, '#ordpar-theme-dark');
  res.darkChosen = await p.eval(STATE);
  for (const id of ['concise', 'default', 'english', 'learners', 'concise']) {
    await press(p, `button[data-preset="${id}"]`);
    res.steps.push(Object.assign({ preset: id }, await p.eval(STATE)));
  }
  // the pressed look (in dark): filled with the accent; the others not
  res.look = await p.eval(`(() => {
    const cs = sel => { const e = document.querySelector(sel); const c = getComputedStyle(e);
      return { bg: c.backgroundColor, fg: c.color, border: c.borderTopColor }; };
    const probe = document.createElement('button'); probe.className = 'ordpar-button';
    document.body.appendChild(probe); const c = getComputedStyle(probe);
    const primary = { bg: c.backgroundColor, fg: c.color }; probe.remove();
    return { pressed: cs('button[data-preset="concise"]'), other: cs('button[data-preset="default"]'), primary };
  })()`);
  // one Article setting changed afterwards, by its radio: no preset pressed, the rest kept
  await press(p, '#ordpar-defs-both');
  res.changed = await p.eval(STATE);
  // For learners, then a reload
  await press(p, 'button[data-preset="learners"]');
  res.learners = await p.eval(STATE);
  await p.reload(800);
  res.reloaded = await p.eval(STATE);
  // another document of the site changes a setting (the storage event, as from another tab)
  await p.eval(`new Promise(r => { const f = document.createElement('iframe'); f.src = '/about/';
    f.style.display = 'none'; f.onload = () => { f.contentWindow.localStorage.setItem('emph', 'en'); setTimeout(() => r(true), 400); };
    document.body.appendChild(f); })`);
  res.otherTab = await p.eval(STATE);

  // the pictures: each preset pressed, light and dark
  if (args.shots) {
    for (const theme of ['light', 'dark']) {
      await p.eval(`ordparShell.setSetting('theme', '${theme}'); true`);
      for (const id of ['default', 'english', 'concise', 'learners']) {
        await press(p, `button[data-preset="${id}"]`);
        res.shots[theme + '-' + id] = await shot(p, 'settings-' + theme + '-' + id, TOP);
      }
    }
    await p.eval(`ordparShell.setSetting('theme', 'light'); true`);
  }

  // Concise, then an article
  await p.goto(page, 600);
  await press(p, 'button[data-preset="concise"]');
  res.beforeArticle = await p.eval(STATE);
  await p.goto(base + '/bm-en/' + args.id + '/', 900);
  res.article = await p.eval(`(() => {
    const vis = e => !!e && e.getClientRects().length > 0;
    const out = e => !e.closest('.ordbok-xmini, .ordpar-mini, .mini-pair');
    const main = document.querySelector('main') || document.body;
    const nb = [...main.querySelectorAll('.ordpar-pair > span[lang=nb]')].filter(out);
    const lists = [...main.querySelectorAll('ul.ordbok-ex-list')].filter(out).map(u =>
      [...u.children].filter(li => !li.classList.contains('ordpar-exmore')));
    return { pairs: nb.length, nbShown: nb.filter(vis).length,
      lists: lists.length, maxShown: Math.max(0, ...lists.map(l => l.filter(vis).length)),
      maxItems: Math.max(0, ...lists.map(l => l.length)),
      cls: [...document.documentElement.classList].filter(c => /^ordpar-(defs|ex)/.test(c)) };
  })()`);

  // the Help page's link to the Article settings, `/settings/#article`: the section drawn by the
  // script and scrolled to
  await p.goto(page + '#article', 900);
  res.articleLink = await p.eval(`(() => { const s = document.getElementById('article');
    return s ? { tag: s.tagName, top: Math.round(s.getBoundingClientRect().top), scrollY: Math.round(scrollY) } : null; })()`);

  // the Help page's section
  await p.goto(base + '/help/#settings', 600);
  res.help = await p.eval(`(() => { const h = document.getElementById('settings');
    return h ? { tag: h.tagName, text: h.textContent, top: Math.round(h.getBoundingClientRect().top),
      docWidth: document.documentElement.scrollWidth, vw: innerWidth } : null; })()`);
  if (args.shots) res.shots.help = await shot(p, 'help-settings', HELP);
  done(res);
});
