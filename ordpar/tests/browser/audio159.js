// Site decisions 159 (Robin's pick from the style lab, 2026-11-02): the sound icons, played from the
// live Worker (https://ordpar-audio.ordpar.workers.dev/), with the speed setting.
//
// For one viewport (args.mobile: a phone, pressed by touch; else a computer, by the mouse) and one
// theme (args.night), in a fresh context:
//   hus       (24627) the icons on its headword (beside the word), its definition lines, its
//             examples and, the Inflection toggle opened, its table forms; every icon a real
//             <button> named "Play" in the accessibility tree; every icon's text in the article's
//             names file (`/audio/<k>.json`); the colour at rest (day #bab8b8, night #6f6b6c)
//   press     the headword's icon pressed: the clip asked of the Worker (its address), loaded
//             (`readyState`, `duration`) and playing, the icon `ordpar-playing` in the accent colour;
//             a second press stops it
//   rest      (computer) the pointer crossing four icons asks for nothing; resting on one asks for
//             its clip once; the press then plays it with no second request
//   hover     (computer) the text colour (day darker, night lighter)
//   speed     `audiospeed` = 90: the clip plays at 0.9 with the pitch kept
//   mini      a small article opened on hus (hjem, 23742) carries icons, and one plays inside the
//             box, which stays open
//   phrase    (være, 69211) a set phrase's icon inside its term, on the term's line
//   run6      (smuldre, 54865) a run-6 table: only the forms whose text has a clip get an icon
//   spellings (bru, bro, 7663; 160) each spelling its icon, beside it, in order; on the word page
//             /bm-en/bru/ the same, the headword no link, and no "Article page" under it (168 re-ruled)
//   labels    `labels` = no: the icons named "Spill av"
//
// args: { mobile, night }   Result: { base, cases: {...} }
import { open, base, args, run, done, sleep } from './cdp.js';

const WORKER = 'https://ordpar-audio.ordpar.workers.dev/';

async function until(p, expr, ms = 15000) {
  for (let t = 0; t < ms; t += 100) {
    try { if (await p.eval(expr)) return true; } catch (e) { /* a navigation in between */ }
    await sleep(100);
  }
  return false;
}

// the i-th match that is drawn (an English line's copy of a link, hidden by the settings, is not)
const NTH = (sel, i) => `[...document.querySelectorAll(${JSON.stringify(sel)})].filter(e => e.getClientRects().length)[${i}]`;
async function centre(p, sel, i = 0) {
  const c = await p.eval(`(() => { const b = ${NTH(sel, i)};
    if (!b) return null; b.scrollIntoView({ block: 'center' }); return true; })()`);
  if (!c) return null;
  await p.frames();
  return p.eval(`(() => { const r = ${NTH(sel, i)}.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
}

async function press(p, sel, i = 0) {
  const c = await centre(p, sel, i);
  if (!c) return false;
  if (args.mobile) await p.tap(c.x, c.y); else await p.click(c.x, c.y);
  return true;
}

const LAST = `(window.ordparAudio && ordparAudio.last()) || null`;
const PLAYING = `(() => { const l = ${LAST}; return !!l && l.readyState >= 2 && (!l.paused || l.currentTime > 0); })()`;

// the icons of the article on the page, by kind (never a small article's)
const KINDS = `(() => {
  const a = document.querySelector('.ordpar-article');
  const bs = [...a.querySelectorAll('button.ordpar-play')].filter(b => !b.closest('.ordbok-xmini'));
  const kind = b => b.closest('.ordpar-hw') ? 'head' : b.closest('.ordbok-expr-term') ? 'expr'
    : b.closest('.ordbok-def') ? 'def' : b.closest('.ordpar-inflection') ? 'cell'
    : b.closest('.ordbok-ex-list') ? 'ex' : 'other';
  const out = { head: 0, expr: 0, def: 0, ex: 0, cell: 0, other: 0 };
  bs.forEach(b => out[kind(b)]++);
  const b0 = a.querySelector('.ordpar-hw button.ordpar-play'), lem = a.querySelector('.ordpar-hw .ordbok-lemma');
  if (b0) {
    const r = b0.getBoundingClientRect(), l = lem.getBoundingClientRect();
    out.headBeside = r.left >= l.right - 1 && r.left - l.right < 30 && r.top < l.bottom && r.bottom > l.top;
    out.colour = getComputedStyle(b0).color;
    out.type = b0.type;
    out.size = [Math.round(r.width), Math.round(r.height)];
    out.fontPx = parseFloat(getComputedStyle(document.documentElement).fontSize);
  }
  return out;
})()`;

// every icon's text found in the article's names (the build's key and the script's agree)
const KEYS = `(async () => {
  const id = +document.documentElement.getAttribute('data-article-id');
  if (!window.ordparAudio) return { n: 0, miss: ['no audio.js'], file: null };
  const e = await ordparAudio.names(id);
  const bs = [...document.querySelectorAll('.ordpar-article button.ordpar-play')].filter(b => !b.closest('.ordbok-xmini'));
  const miss = bs.filter(b => !(b._keys || []).every(k => e && e[k])).map(b => (b._keys || []).join('|'));
  return { n: bs.length, miss, file: Math.floor((id - 1) / 500) };
})()`;

const AX = async (p, name) => (await p.axNodes()).filter(n => n.role && n.role.value === 'button'
  && n.name && n.name.value === name && !n.ignored).length;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const requests = [];
  await p.send('Network.enable');
  p.on(m => { if (m.method === 'Network.requestWillBeSent' && m.params.request.url.startsWith(WORKER)) requests.push(m.params.request.url); });
  const cases = {};
  const theme = async () => {
    await p.eval(`localStorage.setItem('theme', ${JSON.stringify(args.night ? 'dark' : 'light')}); true`);
  };

  // ---------------------------------------------------------------- hus
  await p.goto(base + '/bm-en/24627/', 400);
  await theme();
  await p.reload(600);
  await until(p, `!!document.querySelector('.ordpar-article button.ordpar-play')`);
  // the Inflection toggle opened: its forms get their icons once the names are in
  await p.eval(`(() => { const t = document.querySelector('details.ordpar-infl-toggle'); if (t) t.open = true; return true; })()`);
  await until(p, `!!document.querySelector('.ordpar-inflection button.ordpar-play')`, 8000);
  cases.hus = await p.eval(KINDS);
  cases.hus.night = await p.eval(`document.documentElement.classList.contains('nightMode')`);
  cases.keys = await p.eval(KEYS);
  cases.ax = { play: await AX(p, 'Play'), spill: await AX(p, 'Spill av') };
  cases.focusable = await p.eval(`(() => { const b = document.querySelector('.ordpar-hw button.ordpar-play'); if (!b) return false; b.focus(); return document.activeElement === b; })()`);
  cases.cellText = await p.eval(`[...document.querySelectorAll('.ordpar-infl-wrap--wide td button.ordpar-play')].map(b => b._keys[0]).slice(0, 12)`);
  cases.accent = await p.eval(`getComputedStyle(document.documentElement).getPropertyValue('--ordpar-accent').trim()`);
  cases.text = await p.eval(`getComputedStyle(document.documentElement).getPropertyValue('--ordpar-text').trim()`);

  // ---------------------------------------------------------------- rest (computer)
  const restSel = '.ordpar-article .ordbok-ex-list button.ordpar-play';
  if (!args.mobile && !(await p.eval(`document.querySelectorAll(${JSON.stringify(restSel)}).length >= 4`))) {
    cases.rest = { crossed: null, rested: null, restedUrl: null, afterPress: null, playing: false, last: null, hover: null };
  } else if (!args.mobile) {
    const sel = restSel;
    // crossing: each icon touched for less than REST_MS (150), then off them all. How long the
    // pointer really stayed is measured in the page: under a loaded machine (the gate runs eight
    // files at once) a 40 ms touch can reach the page as 150 ms or more, which is a rest, and a
    // clip then rightly loads. Such a pass proves nothing, so the page is reloaded (nothing
    // loaded) and the pass made again, three times at most; a pass that stayed under 150 ms on
    // every icon must ask for nothing.
    let crossed = null, dwell = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      if (attempt) {
        await p.reload(600);
        await until(p, `document.querySelectorAll(${JSON.stringify(sel)}).length >= 4`);
      }
      await p.eval(`(() => { window.__dwell = []; let t0 = 0;
        const on = e => e.target.matches && e.target.matches('button.ordpar-play');
        document.addEventListener('pointerenter', e => { if (on(e)) t0 = performance.now(); }, true);
        document.addEventListener('pointerleave', e => { if (on(e) && t0) { window.__dwell.push(performance.now() - t0); t0 = 0; } }, true);
        return true; })()`);
      const pts = [];
      for (let i = 0; i < 4; i++) pts.push(await centre(p, sel, i));
      requests.length = 0;
      for (const c of pts) { await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x, y: c.y }); await sleep(40); await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x + 300, y: c.y }); await sleep(30); }
      await sleep(500);
      crossed = requests.length;
      dwell = await p.eval(`Math.round(Math.max(0, ...(window.__dwell || [])))`);
      if (dwell < 150) break;
    }
    // resting on the third
    const c = await centre(p, sel, 2);
    await p.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x, y: c.y });
    await sleep(1200);
    const rested = requests.slice();
    // hover's colour, while the pointer is on it
    const hover = await p.eval(`getComputedStyle(document.querySelectorAll(${JSON.stringify(sel)})[2]).color`);
    await p.click(c.x, c.y);
    await until(p, PLAYING, 8000);
    await sleep(300);
    cases.rest = { crossed, dwell, rested: rested.length, restedUrl: rested[0] || null, afterPress: requests.length,
      playing: await p.eval(PLAYING), last: await p.eval(LAST), hover };
    await p.eval(`window.ordparAudio && ordparAudio.stop(), true`);
  }

  // ---------------------------------------------------------------- press, playing, second press
  requests.length = 0;
  await press(p, '.ordpar-hw button.ordpar-play');
  const played = await until(p, PLAYING, 8000);
  const during = await p.eval(`(() => { const b = document.querySelector('.ordpar-hw button.ordpar-play');
    if (!b) return null;
    return { cls: b.classList.contains('ordpar-playing'), colour: getComputedStyle(b).color,
      label: b.querySelector('.ordpar-l-en').textContent }; })()`);
  cases.press = { played, last: await p.eval(LAST), during, requests: requests.slice() };
  // The second press, on a LONG clip (2026-11-06): *hus*'s headword is 0.7 s, and against the live
  // site it twice ran to its end before the second press landed (verify, 2026-11-05 and -06), so
  // the stop is checked on the article's first example sentence, several seconds long; the clip's
  // length is returned, and the test requires it long enough for the check to mean something.
  await p.eval(`window.ordparAudio && ordparAudio.stop(), true`);
  const STOPSEL = '.ordpar-article .ordbok-ex-list button.ordpar-play';
  // the example with the longest text, so the longest clip (the first, *bygge hus*, is 1.1 s)
  const STOPI = await p.eval(`(() => { const bs = [...document.querySelectorAll(${JSON.stringify(STOPSEL)})];
    let best = 0, len = -1;
    bs.forEach((b, i) => { const n = (b.parentElement && b.parentElement.textContent || '').trim().length;
      if (b.getClientRects().length && n > len) { len = n; best = i; } });
    return best; })()`);
  await press(p, STOPSEL, STOPI);
  await until(p, PLAYING, 8000);
  await press(p, STOPSEL, STOPI);
  // the stop awaited, not a fixed 200 ms: under the gate's load a tap can land later (2026-11-04,
  // phone-night once at `prepare`); `cut` below tells the press's stop from the clip's own end
  await until(p, `!(window.ordparAudio && ordparAudio.playing())`, 3000);
  await sleep(100);
  cases.stop = await p.eval(`(() => { const b = document.querySelectorAll(${JSON.stringify(STOPSEL)})[${STOPI}]; const l = window.ordparAudio && ordparAudio.last();
    if (!b || !l) return { paused: null, cls: null, playing: null, label: null, cut: null };
    return { paused: l.paused, cls: b.classList.contains('ordpar-playing'), playing: !!ordparAudio.playing(),
      label: b.querySelector('.ordpar-l-en').textContent,
      // stopped by the press, not run to its end: stop() pauses where the clip is
      cut: l.currentTime < l.duration - 0.02, at: l.currentTime, duration: l.duration }; })()`);

  // ---------------------------------------------------------------- speed 90 %
  await p.eval(`localStorage.setItem('audiospeed', '90'); true`);
  await p.reload(600);
  await until(p, `!!document.querySelector('.ordpar-article .ordbok-ex-list button.ordpar-play')`);
  await press(p, '.ordpar-article .ordbok-ex-list button.ordpar-play', 0);
  await until(p, PLAYING, 8000);
  cases.speed = { last: await p.eval(LAST), rate: await p.eval(`window.ordparAudio ? ordparAudio.rate() : null`) };
  await p.eval(`window.ordparAudio && ordparAudio.stop(), localStorage.removeItem('audiospeed'), true`);

  // ---------------------------------------------------------------- a small article
  await p.reload(600);
  // opened as eye131.js opens it (a click dispatched on the link): the press inside it is real
  const LINK = 'main .ordpar-article a.ordbok-xword[href^="/bm-en/23742/"]';
  await until(p, `!!document.querySelector(${JSON.stringify(LINK)})`);
  await p.eval(`(() => { const a = document.querySelector(${JSON.stringify(LINK)}); a.scrollIntoView({ block: 'center' });
    a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })); return true; })()`);
  const opened = await until(p, `!!document.querySelector('.ordbok-xmini .ordpar-fmini:not([aria-busy]) button.ordpar-play')`, 10000);
  const mini = { opened, icons: await p.eval(`document.querySelectorAll('.ordbok-xmini button.ordpar-play').length`),
    href: await p.eval('location.href'),
    // what there is, when it did not open: the box, its busy state, the marks it carries
    seen: await p.eval(`(() => { const m = document.querySelector('.ordbok-xmini'); const b = m && m.querySelector('.ordpar-fmini');
      return m ? { busy: b && b.getAttribute('aria-busy'), marks: m.querySelectorAll('[data-a]').length,
        text: (b ? b.textContent : '').slice(0, 80), audio: !!window.ordparAudio } : null; })()`) };
  requests.length = 0;
  if (opened) {
    await press(p, '.ordbok-xmini button.ordpar-play', 0);
    mini.played = await until(p, PLAYING, 8000);
    mini.last = await p.eval(LAST);
    mini.still = await p.eval(`!!document.querySelector('.ordbok-xmini')`);
    mini.inBox = await p.eval(`!!(window.ordparAudio && ordparAudio.playing() && ordparAudio.playing().closest('.ordbok-xmini'))`);
    mini.requests = requests.slice();
    await p.eval(`window.ordparAudio && ordparAudio.stop(), true`);
  }
  cases.mini = mini;

  // ---------------------------------------------------------------- a set phrase (være)
  await p.goto(base + '/bm-en/69211/', 600);
  await until(p, `!!document.querySelector('.ordbok-expr-term button.ordpar-play')`);
  cases.phrase = await p.eval(`(() => {
    const t = [...document.querySelectorAll('.ordbok-expr-term')].find(x => x.textContent.indexOf('være eller ikke være') === 0);
    if (!t) return null;
    const b = t.querySelector('button.ordpar-play');
    if (!b) return { inside: false };
    const r = b.getBoundingClientRect(), tr = t.getBoundingClientRect();
    const range = document.createRange(); range.selectNodeContents(t.firstChild); const wr = range.getBoundingClientRect();
    // last in the term, or followed only by the term's CEFR level box (site decisions 187)
    const lv = b.nextSibling;
    const last = t.lastChild === b || (!!lv && lv.nodeType === 1 && lv.classList.contains('ordpar-level') && t.lastChild === lv);
    return { inside: true, last, sameLine: r.top < wr.bottom && r.bottom > wr.top,
      afterWords: r.left >= wr.right - 1, termLines: Math.round(tr.height / parseFloat(getComputedStyle(t).lineHeight || 20)) };
  })()`);

  // ---------------------------------------------------------------- run 6 (smuldre)
  await p.goto(base + '/bm-en/54865/', 600);
  await p.eval(`(() => { const t = document.querySelector('details.ordpar-infl-toggle'); if (t) t.open = true; return true; })()`);
  await until(p, `!!document.querySelector('.ordpar-inflection td')`, 5000);
  await sleep(1500);   // the names file in, the forms with a clip given their icons
  cases.run6 = await p.eval(`(() => {
    const tds = [...document.querySelectorAll('.ordpar-infl-wrap--wide td')].filter(td => td.textContent.trim());
    return { forms: tds.length, icons: [...document.querySelectorAll('.ordpar-infl-wrap--wide td button.ordpar-play')].map(b => b._keys[0]) };
  })()`);

  // ---------------------------------------------------------------- every spelling (bru, bro; 160)
  await p.goto(base + '/bm-en/7663/', 600);
  await until(p, `document.querySelectorAll('.ordpar-hw button.ordpar-play').length >= 2`, 8000);
  const SPELL = `(() => {
    const h = document.querySelector('.ordpar-hw');
    const lems = [...h.querySelectorAll('.ordbok-lemma')].filter(l => /\\w/.test(l.textContent));
    return { words: lems.map(l => l.textContent.trim()),
      icons: [...h.querySelectorAll('button.ordpar-play')].map(b => b._keys[0]),
      beside: lems.map(l => { const b = l.nextElementSibling; if (!b || !b.matches('button.ordpar-play')) return false;
        const r = b.getBoundingClientRect(), lr = l.getBoundingClientRect(); return r.left >= lr.right - 1 && r.left - lr.right < 30; }),
      inLink: !!h.querySelector('a button.ordpar-play') };
  })()`;
  cases.spellings = { page: await p.eval(SPELL) };
  // a looked-up article (the word page): the headword no link (as ordbokene's results), an icon
  // beside each spelling as on the article page; no "Article page" under the article since site
  // decisions 168 was re-ruled (2026-11-06, everywhere)
  await p.goto(base + '/bm-en/bru/', 600);
  await until(p, `!!document.querySelector('.ordpar-hw button.ordpar-play')`, 10000);
  await sleep(500);
  cases.spellings.lookedUp = await p.eval(`(() => {
    // the spellings' own text: the icon's hidden "Play" follows each word in the heading's text
    const words = h => [...h.querySelectorAll('.ordbok-lemma')].filter(l => /\\w/.test(l.textContent));
    const h = [...document.querySelectorAll('.ordpar-hw')].find(x => words(x).some(l => l.textContent.trim() === 'bru'));
    if (!h) return null;
    const ls = words(h), res = h.closest('.ordpar-result') || h.parentNode;
    return { words: ls.map(l => l.textContent.trim()), links: h.querySelectorAll('a').length,
      icons: [...h.querySelectorAll('button.ordpar-play')].map(b => b._keys[0]),
      beside: ls.map(l => { const b = l.nextElementSibling; if (!b || !b.matches('button.ordpar-play')) return false;
        const r = b.getBoundingClientRect(), lr = l.getBoundingClientRect(); return r.left >= lr.right - 1 && r.left - lr.right < 30; }),
      articlePage: !!(res && [...res.querySelectorAll('a.ordpar-result-page')].some(a => a.getAttribute('href') === '/bm-en/7663/')) }; })()`);

  // ---------------------------------------------------------------- labels in Norwegian
  await p.eval(`localStorage.setItem('labels', 'no'); true`);
  await p.goto(base + '/bm-en/24627/', 600);
  await until(p, `!!document.querySelector('.ordpar-article button.ordpar-play')`);
  cases.labels = { play: await AX(p, 'Play'), spill: await AX(p, 'Spill av') };
  await p.eval(`localStorage.removeItem('labels'); true`);

  done({ base, cases });
});
