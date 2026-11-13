// Decisions 120 (Robin, 2026-10-24): on a phone, a setting's choice too long for the line wraps
// INSIDE its label, its first line beside the radio button, instead of dropping whole below it.
//
// At args.w × 844 (390: a phone's width; a mouse, so the page is the one a narrow window shows
// too), in a fresh context, the settings page is opened and every choice on it (`.ordpar-radio`)
// measured, its fieldset shown first if a setting hides it (the measuring is about the layout,
// not the setting's visibility): the radio's box, the label's box, and the label's first line —
// the first line box of its text (`Range.getClientRects` over the label's contents, the rects on
// the first line merged). A long label is one whose text takes more than one line.
//
// args: { w }
// Result: { base, w, rows: [{ key, value, text, radio: {l, t, r, b}, label: {l, t, r, b},
//   first: {t, b}, lines, swatch, note }], select: { found, height, top, labelTop } }
import { open, base, args, run, done } from './cdp.js';

run(async () => {
  const w = args.w || 390;
  const p = await open({ w, h: 844 });
  await p.goto(base + '/bm-en/', 400);
  await p.eval('localStorage.clear(); true');
  await p.goto(base + '/settings/', 800);
  const got = await p.eval(`(() => {
    const box = r => ({ l: r.left, t: r.top, r: r.right, b: r.bottom });
    document.querySelectorAll('fieldset[hidden]').forEach(f => { f.hidden = false; });
    const rows = [...document.querySelectorAll('.ordpar-radio')].map(row => {
      const input = row.querySelector(':scope > input[type=radio]');
      const label = row.querySelector(':scope > label');
      const range = document.createRange();
      range.selectNodeContents(label);
      const rects = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
      // the line boxes: rects grouped by their vertical middle
      const lines = [];
      for (const r of rects) {
        const mid = (r.top + r.bottom) / 2;
        const line = lines.find(l => mid > l.t && mid < l.b);
        if (line) { line.t = Math.min(line.t, r.top); line.b = Math.max(line.b, r.bottom); }
        else lines.push({ t: r.top, b: r.bottom });
      }
      lines.sort((a, b) => a.t - b.t);
      const note = row.querySelector('.ordpar-choice-note');
      return { key: input && input.getAttribute('data-key'), value: input && input.value,
               text: label.textContent.trim(), radio: box(input.getBoundingClientRect()),
               label: box(label.getBoundingClientRect()), first: lines[0] || null, lines: lines.length,
               swatch: !!label.querySelector('.ordpar-swatch'),
               note: note ? { hidden: note.hidden, shown: note.getClientRects().length > 0 } : null };
    });
    const sel = document.querySelector('.ordpar-select select');
    const selBox = sel && sel.getBoundingClientRect();
    const fs = sel && sel.closest('fieldset');
    const leg = fs && fs.querySelector('legend');
    return { rows, select: sel ? { found: true, height: selBox.height, top: selBox.top,
      legendBottom: leg ? leg.getBoundingClientRect().bottom : null,
      width: selBox.width, right: selBox.right } : { found: false },
      docWidth: document.documentElement.scrollWidth, vw: innerWidth };
  })()`);
  await done({ base, w, ...got });
});
