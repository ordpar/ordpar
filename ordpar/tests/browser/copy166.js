// Site decisions 166, Copy (Robin, 2026-11-05): the Copy button on Robin's /reports page, in a
// browser. The page is served by scripts/serve.py's own handler (the Python side), with the
// receiver's answer stood in for, so `args.copy` is the text the server made for the one report.
//
// The clipboard is stood in for before the page's script runs (CDP
// `Page.addScriptToEvaluateOnNewDocument`): `navigator.clipboard.writeText` records what it is
// given and resolves, or (`?refuse`) rejects, as a browser that refuses the clipboard does.
//   1. The report's row: Done, Fixed …, Copy, in that order; Copy's tooltip and the note under
//      the row say the reply address and the name are not copied.
//   2. Copy pressed: exactly `args.copy` written, once; the status says so; no text box.
//   3. The clipboard refused: a read-only text box with exactly that text, selected whole and
//      focused; the status says to press Ctrl+C.
//   4. No clipboard at all (`navigator.clipboard` undefined): the same text box.
//
// args: { copy, reply, credit }
import { open, base, args, run, done } from './cdp.js';

const STUB = `(() => {
  const mode = location.search.slice(1);
  window.__copied = [];
  if (mode === 'none') { Object.defineProperty(navigator, 'clipboard', { configurable: true, get() { return undefined; } }); return; }
  const cb = { writeText(t) { window.__copied.push(t); return mode === 'refuse' ? Promise.reject(new Error('denied')) : Promise.resolve(); } };
  Object.defineProperty(navigator, 'clipboard', { configurable: true, get() { return cb; } });
})();`;

const STATE = `(() => {
  const li = document.querySelector('li.report');
  if (!li) return null;
  const box = li.querySelector('textarea.copybox');
  const b = li.querySelector('button.copy');
  return {
    buttons: [...li.querySelectorAll(':scope > p > button')].map(x => x.textContent),
    title: b ? b.title : null,
    note: (li.querySelector('.copynote') || {}).textContent || null,
    status: li.querySelector('.status').textContent,
    copied: window.__copied,
    box: box && !box.hidden ? { value: box.value, readOnly: box.readOnly, focused: document.activeElement === box,
      selected: box.selectionStart === 0 && box.selectionEnd === box.value.length } : null,
    rowText: li.textContent,
  };
})()`;

run(async () => {
  const p = await open();
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: STUB });
  const out = {};
  for (const mode of ['ok', 'refuse', 'none']) {
    await p.goto(base + '/reports?' + mode, 300);
    for (let i = 0; i < 50 && !(await p.eval("!!document.querySelector('li.report')")); i++) await p.frames();
    const before = await p.eval(STATE);
    await p.eval("document.querySelector('li.report button.copy').click()");
    for (let i = 0; i < 10; i++) await p.frames();
    out[mode] = { before, after: await p.eval(STATE) };
  }
  done({ ok: true, out });
});
