// Site decisions 186 (2026-11-14/15): what the eye at the headword hides. The setting `exeyewhat`
// (The examples' English | All the English ...), shown while the eye (`exeye`, decisions 131) is on.
//
// For one viewport (args.mobile: a phone, pressed by touch; else a computer, by the mouse), in a
// fresh context with the storage cleared:
//   settings   the setting right after the eye's, hidden while the eye is off and shown once it is
//              on, its choices in order, the first checked, its "?"; "For learners" leaves it at
//              the examples (and puts it back there from all);
//   examples   under the default the eye is the eye of 131: a press hides the examples' English
//              only (the gloss and the definitions stay), its name unchanged;
//   all        on hus: the eye named "Hide the English"; a press blanks every English line of the
//              article (each line of a split definition its own), each behind its own "Show
//              English" cue, the etymology untouched, no hover peek, the example lists where they
//              were, a reveal moving nothing below a one-row line, nothing of a hidden line in a
//              select-all; named "Show the English", pressed; the second press gives the article
//              back exactly (markup and text); Enter presses it;
//              slett (100500): a definition of three lines, three cues, one a line;
//   readers    under `defs` no, `examples` no and `ety` both, one example opened by its cue first:
//              the press overrides the hiding, the second gives it back exactly; a line's cue shows
//              it, a press on the line hides it again (its cue back and focused), the pair still
//              open after a second reveal;
//   more       under a limit of one example a sense: the examples shown stay as many at the press,
//              and "Show N more" opens them blanked;
//   where      no eye under `defs` en (one under the examples' value, as today), none under
//              Norwegian only; one on kid (100084: English but no example), none there under the
//              examples' value; none on an untranslated article (10); a word page, a search answered
//              in place, each full result of fange (a press blanks only its own), an article opened
//              in a list row (its row's glosses hidden while blanked);
//   mini       a small article opened in a blanked article: no cue, nothing hidden, no eye in it;
//   change     the setting changed while blanked gives the article back first; so does a change of
//              the Examples setting.
//
// args: { mobile }   Result: { base, cases: {...} }
import { open, base, args, run, done, sleep } from './cdp.js';

const HUS = 24627, SLETT = 100500, KID = 100084, UNTR = 10;
const SHOWN = `(e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden')`;

async function until(p, expr, ms = 15000) {
  expr = `!document.querySelector('.ordpar-word-title') && (${expr})`;
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

async function press(p, sel) {
  const c = await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(sel)});
    if (!b) return null; b.scrollIntoView({ block: 'center' }); return true; })()`);
  if (!c) return false;
  await p.frames();
  const c2 = await p.eval(`(() => { const r = document.querySelector(${JSON.stringify(sel)}).getBoundingClientRect();
    return { x: r.left + Math.min(r.width / 2, 20), y: r.top + r.height / 2 }; })()`);
  if (args.mobile) await p.tap(c2.x, c2.y); else await p.click(c2.x, c2.y);
  await sleep(200);
  return true;
}

// the page's helpers, put in after each load: an article's English lines (each line of a split
// definition its own), what of them shows, the cues, the etymology, the example lists' layout;
// `keep` / `same` its markup and text before a press and after the second
const HELP = `window.__T = window.__T || (() => {
  const SH = ${SHOWN};
  const SEL = '.ordbok-head>.ordpar-gloss,span.ordbok-def[lang="en"],.ordbok-ex-list>li>.ordpar-en,.ordbok-idiom-eng';
  const OFF = '.ordbok-xpeek,.ordbok-xmini,template,.ordpar-row-button';
  const units = a => [...a.querySelectorAll(SEL)].filter(x => /\\S/.test(x.textContent) && !x.closest(OFF))
    .flatMap(x => { const s = x.querySelectorAll(':scope > .ordpar-eyel'); return s.length ? [...s] : [x]; })
    .filter(x => /\\S/.test(x.textContent));
  const norm = t => t.replace(/\\s+/g, ' ').trim();
  const ety = a => [...a.querySelectorAll('.ordbok-inline > .ordpar-pair')].map(p => ({
    en: SH(p.querySelector('span[lang=en]')), nb: SH(p.querySelector('span[lang=nb]')),
    cue: SH(p.querySelector('.ordpar-encue')), eyeCue: !!p.querySelector('[data-ordpar-eyecue]'), open: p.classList.contains('ordpar-open') }));
  const lists = a => { const L = a.getBoundingClientRect().left;
    return [...a.querySelectorAll('ul.ordbok-ex-list')].filter(SH).map(u => { const cs = getComputedStyle(u), r = u.getBoundingClientRect();
      return [(r.left - L).toFixed(2), r.width.toFixed(2), cs.paddingLeft, cs.marginLeft, cs.marginTop, cs.marginBottom, cs.listStyleType].join('|'); }); };
  const snap = a => a.innerHTML.replace(/ (aria-pressed|aria-label|title|data-test-[a-z]+)="[^"]*"/g, '');
  const eyeOf = a => a.querySelector(':scope > .ordbok-head > .ordpar-exeye > button');
  const state = a => { if (!a) return null; const us = units(a), cues = [...a.querySelectorAll('[data-ordpar-eyecue]')];
    const lines = new Set(cues.map(c => c._l)), b = eyeOf(a);
    return { units: us.length, shown: us.filter(SH).length, hid: a.querySelectorAll('.ordpar-eyehid').length,
      cues: cues.length, cuesShown: cues.filter(SH).length, uncovered: us.filter(u => !SH(u) && !lines.has(u)).length,
      coveredHidden: us.filter(u => lines.has(u) && u.classList.contains('ordpar-eyehid')).length,
      siteCues: [...a.querySelectorAll('.ordpar-encue')].filter(c => SH(c) && !c.closest('.ordbok-inline')).length,
      blanked: a.classList.contains('ordpar-blanked'), ety: ety(a), lists: lists(a),
      peeks: a.querySelectorAll('.ordbok-xpeek').length,
      peeksShown: [...a.querySelectorAll('.ordbok-xpeek')].filter(x => !x.closest('.ordbok-xmini')).filter(SH).length,
      gloss: SH(a.querySelector('.ordbok-head > .ordpar-gloss')),
      defsShown: [...a.querySelectorAll('span.ordbok-def[lang=en]')].filter(x => !x.closest(OFF)).filter(SH).length,
      exEn: [...a.querySelectorAll('.ordbok-ex-list > li > .ordpar-en')].filter(x => !x.closest(OFF)).length,
      exEnShown: [...a.querySelectorAll('.ordbok-ex-list > li > .ordpar-en')].filter(x => !x.closest(OFF)).filter(SH).length,
      exInView: [...a.querySelectorAll('.ordbok-ex-list > li')].filter(x => !x.closest(OFF) && !x.classList.contains('ordpar-exmore')).filter(SH).length,
      eyes: a.querySelectorAll(':scope > .ordbok-head > .ordpar-exeye').length,
      eye: b ? { shown: SH(b), label: b.getAttribute('aria-label'), title: b.title, pressed: b.getAttribute('aria-pressed') } : null }; };
  const kept = {};
  const keep = (k, a) => { kept[k] = [snap(a), norm(a.innerText)]; return true; };
  const same = (k, a) => ({ html: snap(a) === kept[k][0], text: norm(a.innerText) === kept[k][1] });
  return { SH, units, state, norm, keep, same, eyeOf };
})(), true`;

const look = async (p, sel) => { await p.eval(HELP); return p.eval(`window.__T.state(document.querySelector(${JSON.stringify(sel)}))`); };
const MAIN = 'main .ordpar-article';
const EYE = (sel) => sel + ' > .ordbok-head > .ordpar-exeye > button';

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const cases = {};
  const set = async (k, v) => { await p.eval(`ordparShell.setSetting(${JSON.stringify(k)}, ${JSON.stringify(v)}); true`); await p.frames(); await sleep(100); };
  await p.goto(base + '/bm-en/', 400);
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); true`);

  // --- the settings page
  await p.goto(base + '/settings/', 400);
  await until(p, `document.querySelectorAll('fieldset[data-setting]').length > 5`);
  const SET = `(() => { const fs = [...document.querySelectorAll('fieldset[data-setting]')];
    const keys = fs.map(f => f.getAttribute('data-setting')), i = keys.indexOf('exeye');
    const f = fs.find(x => x.getAttribute('data-setting') === 'exeyewhat');
    const radios = f ? [...f.querySelectorAll('input[type=radio]')] : [];
    return { after: keys[i + 1], sameSub: !!f && f.parentNode === fs[i].parentNode,
      title: f ? f.querySelector('.ordpar-field-title').textContent : null,
      shown: !!f && f.getClientRects().length > 0, hint: !!f && !!f.querySelector('.ordpar-hint-button'),
      choices: radios.map(r => document.querySelector('label[for="' + r.id + '"]').textContent.trim()),
      values: radios.map(r => r.value), checked: radios.filter(r => r.checked).map(r => r.value) }; })()`;
  const s = { off: await p.eval(SET) };
  await p.eval(`document.querySelector('fieldset[data-setting="exeye"] input[value="on"]').click(); true`);
  await sleep(200);
  s.on = await p.eval(SET);
  s.learnersValues = await p.eval(`(() => { const S = ordparSettings, pr = S.PRESETS.find(x => x.id === 'learners');
    const v = S.presetValues(pr); return { exeye: v.exeye, exeyewhat: v.exeyewhat }; })()`);
  await p.eval(`document.querySelector('fieldset[data-setting="exeyewhat"] input[value="all"]').click(); true`);
  await sleep(200);
  s.storedAll = await p.eval(`localStorage.getItem('exeyewhat')`);
  await press(p, 'button[data-preset="learners"]');
  s.afterLearners = await p.eval(`({ exeye: ordparShell.getSetting('exeye'), exeyewhat: ordparShell.getSetting('exeyewhat'),
    pressed: document.querySelector('button[data-preset="learners"]').getAttribute('aria-pressed') })`);
  cases.settings = s;

  // --- the examples' value: the eye of 131
  await p.eval(`localStorage.clear(); localStorage.setItem('theme', 'light'); localStorage.setItem('exeye', 'on'); true`);
  await p.goto(base + '/bm-en/' + HUS + '/', 600);
  const e0 = await look(p, MAIN);
  e0.cls = await p.eval(`document.documentElement.classList.contains('ordpar-exeye-all')`);
  await press(p, EYE(MAIN));
  const e1 = await look(p, MAIN);
  await press(p, EYE(MAIN));
  const e2 = await look(p, MAIN);
  cases.examples = { before: e0, pressed: e1, again: e2 };

  // --- all, on hus
  await p.eval(`localStorage.setItem('exeyewhat', 'all'); true`);
  await p.reload(600);
  const a0 = await look(p, MAIN);
  a0.cls = await p.eval(`document.documentElement.classList.contains('ordpar-exeye-all')`);
  await p.eval(`window.__T.keep('hus', document.querySelector(${JSON.stringify(MAIN)}))`);
  await press(p, EYE(MAIN));
  const a1 = await look(p, MAIN);
  a1.selected = await p.eval(`(() => { const s = getSelection(); s.removeAllRanges(); s.selectAllChildren(document.body);
    const all = window.__T.norm(s.toString()); s.removeAllRanges();
    const hid = [...document.querySelectorAll('.ordpar-eyehid')].map(l => window.__T.norm(l.textContent)).filter(t => t.length > 3);
    return { hidden: hid.length, found: hid.filter(t => all.includes(t)).slice(0, 10) }; })()`);
  // an example's cue against the cue the examples' value draws (measured below, `exCue`)
  const EXCUE = `(() => { const a = document.querySelector(${JSON.stringify(MAIN)});
    const isCue = c => c.matches('[data-ordpar-eyecue], .ordpar-excue') && (${SHOWN})(c);
    const li = [...a.querySelectorAll('.ordbok-ex-list > li')].find(l => [...l.children].some(isCue));
    if (!li) return null; const c = [...li.children].find(isCue);
    const nb = li.querySelector('span[lang=nb]').getBoundingClientRect(), r = c.getBoundingClientRect(), l = li.getBoundingClientRect();
    return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), dx: +(r.left - l.left).toFixed(1), gap: +(r.top - nb.bottom).toFixed(1),
      below: +(l.bottom - r.bottom).toFixed(1), font: getComputedStyle(c).fontSize, text: c.innerText.trim() }; })()`;
  a1.exCue = await p.eval(EXCUE);
  // each reveal of a one-row line that is not an example keeps the article's height
  a1.reveals = await p.eval(`(() => { const a = document.querySelector(${JSON.stringify(MAIN)}), out = [];
    const cs = [...a.querySelectorAll('[data-ordpar-eyecue]')].filter(c => (${SHOWN})(c) && !c.closest('.ordbok-ex-list'));
    for (const c of cs.slice(0, 40)) { const l = c._l, h0 = a.getBoundingClientRect().height; c.click();
      const lh = parseFloat(getComputedStyle(l).lineHeight) || 24;
      out.push({ kind: l.matches('.ordpar-gloss') ? 'gloss' : l.matches('.ordbok-idiom-eng') ? 'phrase' : 'def',
        rows: Math.max(1, Math.round(l.getBoundingClientRect().height / lh)), dy: +(a.getBoundingClientRect().height - h0).toFixed(2) }); }
    return out; })()`);
  await press(p, EYE(MAIN));
  const a2 = await look(p, MAIN);
  a2.same = await p.eval(`window.__T.same('hus', document.querySelector(${JSON.stringify(MAIN)}))`);
  // the keyboard
  await p.eval(`document.querySelector(${JSON.stringify(EYE(MAIN))}).focus(); true`);
  await p.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
  await p.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await sleep(200);
  const a3 = await look(p, MAIN);
  // the setting changed while blanked: the article given back first
  await set('exeyewhat', 'examples');
  const c1 = await look(p, MAIN);
  c1.same = await p.eval(`window.__T.same('hus', document.querySelector(${JSON.stringify(MAIN)}))`);
  await set('exeyewhat', 'all');
  const c2 = await look(p, MAIN);
  await press(p, EYE(MAIN));
  // a small article opened, blanked again first, in the blanked article (hjem I, 23742)
  const miniOpened = await p.eval(`(async () => {
    const a = document.querySelector('main .ordpar-article a.ordbok-xword[href^="/bm-en/23742/"]'); if (!a) return false;
    a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
    for (let t = 0; t < 60; t++) { if (document.querySelector('.ordbok-xmini .ordbok-ex-list > li')) break;
      await new Promise(r => setTimeout(r, 100)); }
    await new Promise(r => setTimeout(r, 300));
    return !!document.querySelector('.ordbok-xmini .ordbok-ex-list > li'); })()`);
  const mini = await p.eval(`(() => { const m = document.querySelector('.ordbok-xmini'); if (!m) return null;
    const vis = ${SHOWN}; const en = [...m.querySelectorAll('.ordbok-ex-list > li > .ordpar-en, .mini-pair > span[lang=en]')];
    return { cues: m.querySelectorAll('[data-ordpar-eyecue]').length, hid: m.querySelectorAll('.ordpar-eyehid').length,
      eyes: m.querySelectorAll('.ordpar-exeye').length, en: en.length, enShown: en.filter(vis).length }; })()`);
  await p.eval('window.ordparMinis && window.ordparMinis.close && window.ordparMinis.close(), true');
  await set('examples', 'no');
  const c3 = await look(p, MAIN);
  c3.blankedAny = await p.eval(`document.querySelectorAll('.ordpar-blanked, [data-ordpar-eyecue], .ordpar-eyehid, .ordpar-eyeopened').length`);
  await set('examples', 'both');
  cases.all = { before: a0, hidden: a1, shownAgain: a2, enter: a3, miniOpened, mini,
    changedWhat: c1, backToAll: c2, changedExamples: c3 };

  // --- slett: a definition of three lines
  await p.goto(base + '/bm-en/' + SLETT + '/', 600);
  await press(p, EYE(MAIN));
  await p.eval(HELP);
  cases.threeLine = await p.eval(`(() => { const x = [...document.querySelectorAll('main .ordpar-article span.ordbok-def[lang=en][data-ordpar-eyel]')]
    .find(x => x.querySelectorAll(':scope > br').length === 2); if (!x) return null;
    const cs = [...x.querySelectorAll(':scope > [data-ordpar-eyecue]')];
    return { lines: x.querySelectorAll(':scope > .ordpar-eyel').length, cues: cs.length, shown: cs.filter(${SHOWN}).length,
      own: new Set(cs.map(c => c._l)).size }; })()`);
  cases.slett = await look(p, MAIN);

  // --- the reader's own hiding, and a line revealed and hidden again
  await p.eval(`localStorage.setItem('defs', 'no'); localStorage.setItem('examples', 'no'); localStorage.setItem('ety', 'both'); true`);
  await p.goto(base + '/bm-en/' + HUS + '/', 600);
  const r0 = await look(p, MAIN);
  r0.exCue = await p.eval(EXCUE);
  await press(p, MAIN + ' .ordbok-ex-list > li > .ordpar-excue');
  const r0b = await look(p, MAIN);
  await p.eval(`window.__T.keep('readers', document.querySelector(${JSON.stringify(MAIN)}))`);
  await press(p, EYE(MAIN));
  const r1 = await look(p, MAIN);
  r1.exCue = await p.eval(EXCUE);
  // one definition line: its cue shows it, a press on it hides it, its cue shows it again
  await p.eval(`(() => { const c = [...document.querySelectorAll('main .ordpar-article [data-ordpar-eyecue]')]
    .find(c => (${SHOWN})(c) && c._l.matches('span.ordbok-def, .ordpar-eyel'));
    if (!c) return false; c._l.setAttribute('data-test-l', ''); c.setAttribute('data-test-c', ''); return true; })()`);
  const LINE = `(() => { const l = document.querySelector('[data-test-l]'); if (!l) return null;
    const cs = [...document.querySelectorAll('[data-ordpar-eyecue]')].filter(c => c._l === l);
    document.querySelectorAll('[data-test-c]').forEach(x => x.removeAttribute('data-test-c')); if (cs[0]) cs[0].setAttribute('data-test-c', '');
    return { shown: (${SHOWN})(l), cues: cs.length, cueShown: cs.some(${SHOWN}),
      focused: !!document.activeElement && document.activeElement._l === l,
      pairOpen: !!l.closest('.ordpar-pair') && l.closest('.ordpar-pair').classList.contains('ordpar-open') }; })()`;
  const line = { before: await p.eval(LINE) };
  await press(p, '[data-test-c]');
  line.revealed = await p.eval(LINE);
  await press(p, '[data-test-l]');
  line.hiddenAgain = await p.eval(LINE);
  await press(p, '[data-test-c]');
  line.again = await p.eval(LINE);
  await p.eval(`document.querySelectorAll('[data-test-l], [data-test-c]').forEach(x => { x.removeAttribute('data-test-l'); x.removeAttribute('data-test-c'); }), true`);
  await press(p, EYE(MAIN));
  const r2 = await look(p, MAIN);
  r2.same = await p.eval(`window.__T.same('readers', document.querySelector(${JSON.stringify(MAIN)}))`);
  cases.readers = { before: r0, opened: r0b, hidden: r1, line, shownAgain: r2 };
  await p.eval(`localStorage.removeItem('defs'); localStorage.removeItem('examples'); localStorage.removeItem('ety'); true`);

  // --- a limit of one example a sense: as many shown at the press; "Show N more" opens them blanked
  await p.eval(`localStorage.setItem('exlimit', '1'); true`);
  await p.goto(base + '/bm-en/' + HUS + '/', 600);
  const m0 = await look(p, MAIN);
  await press(p, EYE(MAIN));
  const m1 = await look(p, MAIN);
  await p.eval(`(() => { const b = document.querySelector('main .ordpar-article .ordpar-exbtn'); if (b) b.setAttribute('data-test-more', ''); return !!b; })()`);
  const more = { before: m0.exInView, pressed: m1.exInView };
  const IN = `[...document.querySelector('main .ordpar-article').querySelectorAll('.ordbok-ex-list > li > .ordpar-en')].filter(e => (${SHOWN})(e.parentElement))`;
  more.listBefore = await p.eval(`${IN}.length`);
  await press(p, '[data-test-more]');
  more.after = await p.eval(`(() => { const v = ${IN};
    return { inView: v.length, enShown: v.filter(${SHOWN}).length,
      withCue: v.filter(e => [...e.parentElement.children].some(c => c.hasAttribute('data-ordpar-eyecue') && (${SHOWN})(c))).length }; })()`);
  cases.more = more;
  await p.eval(`localStorage.removeItem('exlimit'); true`);

  // --- where the eye goes
  const where = {};
  await p.eval(`localStorage.setItem('defs', 'en'); true`);
  await p.goto(base + '/bm-en/' + HUS + '/', 600);
  where.defsEnAll = await look(p, MAIN);
  await p.eval(`localStorage.setItem('exeyewhat', 'examples'); true`);
  await p.reload(600);
  where.defsEnExamples = await look(p, MAIN);
  await p.eval(`localStorage.removeItem('defs'); localStorage.setItem('nbonly', 'on'); true`);
  await p.reload(600);
  where.nbExamples = await look(p, MAIN);
  await p.eval(`localStorage.setItem('exeyewhat', 'all'); true`);
  await p.reload(600);
  where.nbAll = await look(p, MAIN);
  await p.eval(`localStorage.removeItem('nbonly'); true`);
  await p.goto(base + '/bm-en/' + KID + '/', 600);
  where.kidAll = await look(p, MAIN);
  await press(p, EYE(MAIN));
  where.kidPressed = await look(p, MAIN);
  await p.eval(`localStorage.setItem('exeyewhat', 'examples'); true`);
  await p.reload(600);
  where.kidExamples = await look(p, MAIN);
  await p.eval(`localStorage.setItem('exeyewhat', 'all'); true`);
  await p.goto(base + '/bm-en/' + UNTR + '/', 600);
  where.untranslated = await look(p, MAIN);
  // a word page of one article
  await p.goto(base + '/bm-en/vindu/', 400);
  const WR = '[data-ordpar-results] .ordpar-result .ordpar-article';
  await until(p, `!!document.querySelector('${WR} > .ordbok-head .ordpar-exeye')`);
  where.word = await look(p, WR);
  await press(p, EYE(WR));
  where.wordPressed = await look(p, WR);
  // a one-article search answered in place
  await p.goto(base + '/bm-en/', 600);
  await p.eval(`ordparShell.search('vindu'); true`);
  await until(p, `!!document.querySelector('${WR} > .ordbok-head .ordpar-exeye')`);
  where.search = await look(p, WR);
  await press(p, EYE(WR));
  where.searchPressed = await look(p, WR);
  // every full result its own eye; a press blanks only its own article
  await p.eval(`localStorage.setItem('listview', 'off'); true`);
  await p.goto(base + '/bm-en/fange/', 400);
  await until(p, `document.querySelectorAll('[data-ordpar-results] .ordpar-result .ordbok-head').length > 1
    && !document.querySelector('.ordpar-result[aria-busy]')`);
  await sleep(300);
  await p.eval(`document.querySelectorAll('[data-ordpar-results] .ordpar-result').forEach((r, i) => r.setAttribute('data-t186', i)); true`);
  const n = await p.eval(`document.querySelectorAll('[data-ordpar-results] .ordpar-result').length`);
  where.full = [];
  for (let i = 0; i < n; i++) where.full.push(await look(p, `[data-t186="${i}"] .ordpar-article`));
  const first = where.full.findIndex(r => r && r.eyes), other = where.full.findIndex((r, i) => i > first && r && r.eyes);
  await press(p, EYE(`[data-t186="${first}"] .ordpar-article`));
  where.fullFirst = await look(p, `[data-t186="${first}"] .ordpar-article`);
  where.fullOther = other >= 0 ? await look(p, `[data-t186="${other}"] .ordpar-article`) : null;
  // an article opened in a list row
  await p.eval(`localStorage.setItem('listview', 'on'); true`);
  await p.goto(base + '/bm-en/fange/', 400);
  await until(p, `document.querySelectorAll('.ordpar-row-button').length > 1`);
  where.rowButtons = await p.eval(`document.querySelectorAll('.ordpar-row-button .ordpar-exeye').length`);
  await p.eval(`document.querySelector('.ordpar-row-button').click(); true`);
  const RP = '.ordpar-row-panel:not([hidden]) .ordpar-article';
  await until(p, `!!document.querySelector('${RP} > .ordbok-head .ordpar-exeye')`);
  const SNIP = `(() => { const r = document.querySelector('${RP}').closest('.ordpar-row'); const s = r && r.querySelector('.ordpar-row-snippet');
    return s ? (${SHOWN})(s) : null; })()`;
  where.row = await look(p, RP);
  where.row.snippet = await p.eval(SNIP);
  await press(p, EYE(RP));
  where.rowPressed = await look(p, RP);
  where.rowPressed.snippet = await p.eval(SNIP);
  await p.eval(`localStorage.removeItem('listview'); true`);
  cases.where = where;
  await done({ base, cases });
});
