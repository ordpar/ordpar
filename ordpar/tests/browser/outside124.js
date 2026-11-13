// Decisions 124 (Robin, 2026-10-24): while a "?" box is open, a click or tap anywhere outside it
// closes the box and does nothing else; the next click acts as usual. Real input events through
// the DevTools protocol (`Input.dispatchMouseEvent` / `dispatchTouchEvent`), so the browser's own
// default actions (a label's click checking its radio, a link's navigation, a drop-down's focus)
// are what is measured, not a handler having run.
//
// At args.w × 844, with args.pointer 'mouse' (a computer) or 'touch' (a phone: touch emulation,
// a phone's user agent), each case in a fresh page of one context:
// * settings: the settings page with nothing stored; the "?" of `defs` (Definitions) pressed; then a
//   press on an unchecked choice of ANOTHER setting, outside the box (its label's middle, where
//   `elementFromPoint` is that label or its radio and the box is not): the box's state, the
//   setting as stored and as checked on screen; then a second press on the same choice.
// * select: the "?" pressed again, then a press on the examples drop-down (`exlimit`): the box's
//   state and whether the drop-down took the focus (its mousedown's default) or changed.
// * other: the "?" of `defs` pressed, then the "?" of another setting: both boxes' states.
// * scroll (touch only): the "?" pressed, then a finger scroll of 250 px starting outside the box
//   (touchStart, ten touchMoves, touchEnd): the box's state, how far the page moved,
//   the setting unchanged.
// (The pronunciation "?" on an article and in a list row had their cases here until decisions 123's
// amendment removed that "?", 2026-11-02; the settings' hints are the guard's only users now.)
//
// args: { w, pointer, article }
// Result: { base, w, pointer, settings: {...}, select: {...}, other: {...}, scroll: {...}|null }
import { open, base, args, run, done, sleep } from './cdp.js';

const W = args.w || 390, TOUCH = args.pointer === 'touch', ART = args.article || 98;

run(async () => {
  const p = await open({ w: W, h: 844, mobile: TOUCH });
  const press = async (pt, wait = 350) => {
    if (!pt) throw new Error('nothing to press');
    if (TOUCH) await p.tap(pt.x, pt.y); else await p.click(pt.x, pt.y);
    await sleep(wait);
  };
  // the middle of an element, scrolled into view first when asked
  const mid = (sel, scroll) => p.eval(`(() => { const e = ${sel}; if (!e) return null;
    ${scroll ? "e.scrollIntoView({ block: 'center' });" : ''}
    const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  const hintBtn = key => `document.querySelector('fieldset[data-setting="${key}"] .ordpar-hint-button')`;
  const state = key => p.eval(`(() => { const b = ${hintBtn(key)};
    return { expanded: b && b.getAttribute('aria-expanded'), box: !!(b && b.closest('.ordpar-hint').querySelector('.ordpar-hint-box')) }; })()`);
  // an unchecked choice of another setting, visible, outside the open box: its label's middle
  const TARGET = `(() => {
    const box = document.querySelector('.ordpar-hint-box'); const br = box && box.getBoundingClientRect();
    const inBox = (x, y) => br && x >= br.left - 2 && x <= br.right + 2 && y >= br.top - 2 && y <= br.bottom + 2;
    for (const row of document.querySelectorAll('fieldset:not([hidden]):not([data-setting="defs"]) .ordpar-radio')) {
      const input = row.querySelector('input[type=radio]'), label = row.querySelector('label');
      if (!input || !label || input.checked) continue;
      const r = label.getBoundingClientRect(), x = r.left + Math.min(r.width / 2, 40), y = r.top + r.height / 2;
      if (y < 60 || y > innerHeight - 20 || inBox(x, y)) continue;
      const hit = document.elementFromPoint(x, y);
      if (!hit || !(label.contains(hit) || hit === input)) continue;
      return { key: input.getAttribute('data-key') || input.name, value: input.value, x, y };
    }
    return null; })()`;
  const setting = (key, value) => p.eval(`(() => { const i = [...document.querySelectorAll('input[type=radio]')]
      .find(n => (n.getAttribute('data-key') || n.name) === '${key}' && n.value === '${value}');
    return { stored: localStorage.getItem('${key}'), checked: !!(i && i.checked) }; })()`);

  const fresh = async () => {
    await p.goto(base + '/bm-en/', 300);
    await p.eval('localStorage.clear(); true');
    await p.goto(base + '/settings/', 800);
  };

  // --- settings: a choice of another setting
  await fresh();
  const settings = {};
  await press(await mid(hintBtn('defs'), true));
  settings.opened = await state('defs');
  const target = await p.eval(TARGET);
  settings.target = target;
  if (target) {
    settings.before = await setting(target.key, target.value);
    await press(target);
    settings.afterFirst = { box: await state('defs'), ...(await setting(target.key, target.value)) };
    await press(target);
    settings.afterSecond = { box: await state('defs'), ...(await setting(target.key, target.value)) };
  }

  // --- select: the examples drop-down
  await fresh();
  const select = {};
  // the defs "?" near the top of the window, so the drop-down below it is on a phone's screen too
  // (since site decisions 131 the eye's setting sits between Examples and the drop-down)
  await p.eval(`(() => { const b = ${hintBtn('defs')}; b.scrollIntoView({ block: 'start' }); scrollBy(0, -100); return true; })()`);
  await press(await mid(hintBtn('defs'), false));
  select.opened = await state('defs');
  const sel = await mid(`document.querySelector('fieldset[data-setting="exlimit"] select')`, false);
  const selVisible = sel && sel.y > 60 && sel.y < 824;
  select.visible = !!selVisible;
  if (selVisible) {
    await press(sel);
    select.after = { box: await state('defs'), ...(await p.eval(`(() => { const s = document.querySelector('fieldset[data-setting="exlimit"] select');
      return { focused: document.activeElement === s, value: s.value, stored: localStorage.getItem('exlimit') }; })()`)) };
    // close a drop-down that did open (the live site), so the next case starts clean
    await p.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  }

  // --- other: another setting's "?"
  await fresh();
  const other = {};
  await press(await mid(hintBtn('defs'), true));
  other.opened = await state('defs');
  const second = await p.eval(`(() => { const box = document.querySelector('.ordpar-hint-box').getBoundingClientRect();
    for (const b of document.querySelectorAll('fieldset:not([hidden]) .ordpar-hint-button')) {
      const f = b.closest('fieldset'); if (f.getAttribute('data-setting') === 'defs') continue;
      const r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      if (y < 60 || y > innerHeight - 20) continue;
      if (x >= box.left && x <= box.right && y >= box.top && y <= box.bottom) continue;
      if (document.elementFromPoint(x, y) !== b) continue;
      return { key: f.getAttribute('data-setting'), x, y };
    } return null; })()`);
  other.second = second && second.key;
  if (second) {
    await press(second);
    other.after = { first: await state('defs'), second: await state(second.key) };
  }

  // --- scroll: a finger scroll while the box is open (touch only)
  let scroll = null;
  if (TOUCH) {
    await fresh();
    scroll = {};
    await press(await mid(hintBtn('defs'), true));
    scroll.opened = await state('defs');
    const y0 = await p.eval('scrollY');
    const start = await p.eval(`(() => { const r = document.querySelector('.ordpar-hint-box').getBoundingClientRect();
      return { x: Math.round(innerWidth / 2), y: Math.round(r.bottom + 40 < innerHeight - 100 ? innerHeight - 100 : Math.max(r.bottom + 20, innerHeight - 60)) }; })()`);
    // a finger drawn 250 px up in 10 moves (`synthesizeScrollGesture` scrolls nothing under touch emulation)
    await p.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: start.x, y: start.y }] });
    for (let i = 1; i <= 10; i++) {
      await p.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: start.x, y: start.y - i * 25 }] });
      await sleep(16);
    }
    await p.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await sleep(700);
    scroll.moved = Math.round((await p.eval('scrollY')) - y0);
    scroll.after = await state('defs');
    scroll.stored = await p.eval(`Object.keys(localStorage).length`);
  }

  await done({ base, w: W, pointer: TOUCH ? 'touch' : 'mouse', settings, select, other, scroll });
});
