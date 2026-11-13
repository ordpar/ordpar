// Decisions 126 (Robin, 2026-10-25): the settings' words. On the settings page at args.w × 844, in a
// fresh context with the defaults (storage cleared):
//
// * the line under the "Small articles" heading: the element right after `#article-mini-title`, its
//   text, class, box (on screen, inside the window), its font size and colour against the page's other
//   explanatory line (`settings.applied`, the first `p.ordpar-note`), and the subsection's ARIA group
//   (role, the heading naming it, the line describing it) — read from Chrome's accessibility tree too;
// * for each setting in args.keys: whether its legend has a "?", then a real mouse click on it — the
//   box's text and whether the box sits inside the window — and a second click to close it;
// * with args.shots = {dir, prefix}: a picture of the Small articles subsection and one with
//   minicontent's "?" open.
//
// args: { w, keys: [..], shots? }
// Result: { base, w, vw, docWidth, intro: {...}, applied: {...}, ax: {...}, hints: {key: {...}}, shots }
import { writeFileSync } from 'fs';
import { open, base, args, run, done, sleep } from './cdp.js';

async function shot(p, name, selector) {
  if (!args.shots) return null;
  const box = await p.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)});
    if (!e) return null; const r0 = e.getBoundingClientRect();
    // an open "?" box overhangs its fieldset: the picture takes in both
    const o = e.querySelector('.ordpar-hint-box'); const r1 = o ? o.getBoundingClientRect() : r0;
    const r = { left: Math.min(r0.left, r1.left), top: Math.min(r0.top, r1.top),
      width: Math.max(r0.right, r1.right) - Math.min(r0.left, r1.left),
      height: Math.max(r0.bottom, r1.bottom) - Math.min(r0.top, r1.top) };
    return { x: Math.max(0, r.left - 8), y: Math.max(0, r.top + scrollY - 8), w: r.width + 16, h: r.height + 16 }; })()`);
  if (!box) return null;
  await p.frames();
  const { data } = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 } });
  const file = args.shots.dir + '/' + args.shots.prefix + '-' + name + '.png';
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
}

async function buttonAt(p, key) {
  return p.eval(`(() => {
    const b = document.querySelector('fieldset[data-setting="${key}"] legend .ordpar-hint-button');
    if (!b) return null;
    b.scrollIntoView({ block: 'center', behavior: 'instant' });
    const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, label: b.getAttribute('aria-label') };
  })()`);
}

run(async () => {
  const w = args.w || 390;
  const p = await open({ w, h: 844 });
  await p.goto(base + '/bm-en/', 300);
  await p.eval('localStorage.clear(); true');
  await p.goto(base + '/settings/', 800);
  const res = await p.eval(`(() => {
    const h3 = document.getElementById('article-mini-title');
    const line = h3 && h3.nextElementSibling;
    const box = h3 && h3.parentElement;
    const applied = document.querySelector('.ordpar-settings-page > p.ordpar-note');
    const style = e => { const s = getComputedStyle(e); return { size: s.fontSize, colour: s.color }; };
    const rect = e => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, h: r.height }; };
    return { vw: innerWidth, docWidth: document.documentElement.scrollWidth,
      heading: h3 ? h3.textContent : null,
      intro: line && line.tagName === 'P' ? { text: line.textContent, cls: line.className, id: line.id,
        ...style(line), ...rect(line),
        role: box.getAttribute('role'), labelledby: box.getAttribute('aria-labelledby'),
        describedby: box.getAttribute('aria-describedby') } : null,
      applied: applied ? style(applied) : null };
  })()`);
  // the accessibility tree: a group named "Small articles" whose description is the line
  const nodes = await p.axNodes();
  const val = v => (v && v.value != null ? String(v.value) : '');
  const group = nodes.find(n => val(n.role) === 'group' && val(n.name) === 'Small articles');
  res.ax = group ? { role: 'group', name: val(group.name), description: val(group.description) } : null;
  res.hints = {};
  for (const key of args.keys || []) {
    const b = await buttonAt(p, key);
    if (!b) { res.hints[key] = { button: false }; continue; }
    await sleep(100);
    await p.click(b.x, b.y);
    await sleep(150);
    await p.frames();
    const got = await p.eval(`(() => {
      const f = document.querySelector('fieldset[data-setting="${key}"]');
      const box = f.querySelector('.ordpar-hint-box');
      const r = box && box.getBoundingClientRect();
      return { open: !!box, text: box ? box.textContent : '',
        inside: !!r && r.left >= -0.5 && r.right <= innerWidth + 0.5,
        expanded: f.querySelector('.ordpar-hint-button').getAttribute('aria-expanded') };
    })()`);
    await p.click(b.x, b.y);           // closed again: a click on its own "?"
    await sleep(100);
    res.hints[key] = { button: true, label: b.label, ...got };
  }
  // the choices' notes, kept as each radio's (hidden) description
  res.notes = await p.eval(`(() => {
    const o = {};
    for (const id of ['ordpar-mini-article-note', 'ordpar-mini-en-note', 'ordpar-listview-multi-note']) {
      const e = document.getElementById(id);
      o[id] = e ? e.textContent : null;
    }
    return o;
  })()`);
  // the pictures last: a full-page capture changes the page's metrics, so nothing is clicked after one
  // without the size set again
  res.shots = {};
  if (args.shots) {
    await p.eval(`document.getElementById('article-mini-title').scrollIntoView({ block: 'start', behavior: 'instant' }); true`);
    res.shots.sub = await shot(p, 'small-articles', '.ordpar-settings-sub:has(#article-mini-title)');
    await p.size(w, 844);
    const b = await buttonAt(p, 'minicontent');
    await sleep(100);
    await p.click(b.x, b.y);
    await sleep(150);
    res.shots.hint = await shot(p, 'minicontent-hint', 'fieldset[data-setting="minicontent"]');
  }
  await done({ base, w, ...res });
});
