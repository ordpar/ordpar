// Site decisions 166 (Robin, 2026-11-05): "Report a mistake" at an article's foot, in a browser —
// since the follow-up of the same day "Suggest a correction", Robin's pick in the style lab, with a
// name to credit, the receiver's total cap per hour, and the phone row (Copy link not shown on a
// narrow screen where Share is).
//
// The switch is the report's own receiver address (`report.js` `REPORT_RECEIVER`), empty as
// built: read first as built (no button), then with the address set before the page's scripts
// run (CDP `Page.addScriptToEvaluateOnNewDocument`: a setter on `window.ordparReport` gives it the
// local stand-in's address, standing in for a build with the switch on). Then, on an article page
// (`args.id`): the button after Copy link, opened by the keyboard, the form's labels, focus and
// status line; an empty Send; Escape; a report sent (the confirmation, focus back on the button);
// a failed send (a dead address: the text kept); offline (the text kept, then sent once online).
// On a word page (`args.word`, an article shown whole by `lookup.js`): the same button in the
// result's row, a report sent; then the receiver filled to its cap for the hour straight from here
// (no browser), and one more from the page: the cap's answer. Every request the page makes to the
// receiver is recorded from the Network domain: its body, its headers. Last, the phone row at 320,
// 360 and 390 px, with Share (the browser's, or one put in for the check) and without; with Share,
// also with the form open (its line linking the privacy page inside the screen, the row unmoved).
// The privacy build (2026-11-05): the form's line linking `/privacy/#reporting-a-mistake`, and
// whether the site served has that page with that section (`privacyPage`; null without the page).
//
// args: { id, word, receiver: 'http://127.0.0.1:<port>/report', dead: 'http://127.0.0.1:<port>/report' }
import { open, base, args, run, done, sleep } from './cdp.js';

const RECV = args.receiver, DEAD = args.dead;

// the switch, set as report.js assigns window.ordparReport
const SWITCH = `(() => { let r; Object.defineProperty(window, 'ordparReport', { configurable: true,
  get() { return r; }, set(v) { if (v) v.REPORT_RECEIVER = ${JSON.stringify(RECV)}; r = v; } }); })();`;

// the foot row's buttons as shown, in order (the report's button and the others)
const ROW = (sel) => `(() => {
  const row = document.querySelector(${JSON.stringify(sel)});
  if (!row) return null;
  return [...row.querySelectorAll('button')].filter((b) => !b.hidden).map((b) => b.textContent.trim());
})()`;

const STATE = (scope) => `(() => {
  const s = document.querySelector(${JSON.stringify(scope)});
  const b = s && s.querySelector('.ordpar-report-btn');
  const f = b && document.getElementById(b.getAttribute('aria-controls') || '-');
  const q = (x) => f && f.querySelector(x);
  const a = document.activeElement;
  const ta = q('textarea'), em = q('input[type=email]'), trap = q('.ordpar-report-trap input');
  const r = trap ? trap.getBoundingClientRect() : null;
  return {
    button: !!b, expanded: b ? b.getAttribute('aria-expanded') : null,
    form: !!f, open: !!f && !f.hidden && f.getBoundingClientRect().height > 0,
    afterRow: !!f && f.previousElementSibling === b.parentNode,
    focus: a === b ? 'button' : a === ta ? 'text' : a === em ? 'reply' : a ? a.tagName.toLowerCase() + '.' + a.className : null,
    formLabel: f ? f.getAttribute('aria-label') : null,
    textLabel: ta && ta.labels[0] ? ta.labels[0].textContent : null,
    textMax: ta ? ta.maxLength : null, textRequired: ta ? ta.required : null,
    textHint: ta ? (document.getElementById(ta.getAttribute('aria-describedby')) || {}).textContent : null,
    whereLabel: q('select') && q('select').labels[0] ? q('select').labels[0].textContent : null,
    choices: f ? [...f.querySelectorAll('select option')].map((x) => [x.value, x.textContent.trim()]) : [],
    radios: f ? f.querySelectorAll('input[type=radio]').length : null,
    replyLabel: em && em.labels[0] ? em.labels[0].textContent : null,
    replyHint: em ? (document.getElementById(em.getAttribute('aria-describedby')) || {}).textContent : null,
    creditLabel: q('.ordpar-report-credit') && q('.ordpar-report-credit').labels[0] ? q('.ordpar-report-credit').labels[0].textContent : null,
    creditMax: q('.ordpar-report-credit') ? q('.ordpar-report-credit').maxLength : null,
    creditHint: q('.ordpar-report-credit') ? (document.getElementById(q('.ordpar-report-credit').getAttribute('aria-describedby')) || {}).textContent : null,
    textRows: ta ? ta.rows : null,
    trap: trap ? { tab: trap.tabIndex, hidden: trap.closest('[aria-hidden=true]') !== null,
      offscreen: r.right <= 0 || r.width <= 1 } : null,
    buttons: f ? [...f.querySelectorAll('button')].map((x) => x.textContent) : [],
    status: q('.ordpar-report-status') ? q('.ordpar-report-status').textContent : null,
    statusRole: q('.ordpar-report-status') ? q('.ordpar-report-status').getAttribute('role') : null,
    done: s && s.querySelector('.ordpar-report-done') ? s.querySelector('.ordpar-report-done').textContent : null,
    doneRole: s && s.querySelector('.ordpar-report-done') ? s.querySelector('.ordpar-report-done').getAttribute('role') : null,
    doneUnderRow: !!(s && s.querySelector('.ordpar-report-done') && f
      && s.querySelector('.ordpar-report-done').previousElementSibling === f
      && !b.parentNode.contains(s.querySelector('.ordpar-report-done'))),
    text: ta ? ta.value : null,
    lang: f ? f.closest('[lang]').getAttribute('lang') : null,
    privacy: (() => { const n = q('.ordpar-report-privacy'); if (!n) return null;
      const a = n.querySelector('a'), r = n.getBoundingClientRect(), send = q('.ordpar-report-send');
      return { text: n.textContent, link: a ? a.textContent : null, href: a ? a.getAttribute('href') : null,
        target: a ? a.target : null, rel: a ? a.rel : null, shown: r.height > 0,
        beforeSend: !!send && !!(n.compareDocumentPosition(send) & Node.DOCUMENT_POSITION_FOLLOWING),
        inside: r.left >= 0 && r.right <= innerWidth }; })(),
  };
})()`;

async function key(p, k, code) {
  const base = { key: k, code: k, windowsVirtualKeyCode: code, nativeVirtualKeyCode: code };
  await p.send('Input.dispatchKeyEvent', Object.assign({ type: 'keyDown' }, base, k === 'Enter' ? { text: '\r' } : {}));
  await p.send('Input.dispatchKeyEvent', Object.assign({ type: 'keyUp' }, base));
  await sleep(150);
}

/** Fill the open form under `scope` and press Send; wait for an answer (the status or the done line). */
async function fillAndSend(p, scope, text, cat, reply, credit) {
  await p.eval(`(() => {
    const b = document.querySelector(${JSON.stringify(scope)} + ' .ordpar-report-btn');
    const f = document.getElementById(b.getAttribute('aria-controls'));
    const ta = f.querySelector('textarea'); ta.value = ${JSON.stringify(text)};
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    f.querySelector('select').value = ${JSON.stringify(cat || '')};
    f.querySelector('input[type=email]').value = ${JSON.stringify(reply || '')};
    f.querySelector('.ordpar-report-credit').value = ${JSON.stringify(credit || '')};
    f.querySelector('.ordpar-report-send').click(); return true; })()`);
  for (let i = 0; i < 50; i++) {
    await sleep(100);
    const s = await p.eval(STATE(scope));
    if ((s.status && s.status !== 'Sending …') || s.done) return s;
  }
  return p.eval(STATE(scope));
}

async function openForm(p, scope) {
  await p.eval(`(() => { const b = document.querySelector(${JSON.stringify(scope)} + ' .ordpar-report-btn');
    b.click(); return true; })()`);
  await p.frames();
}

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const out = { base, sent: [] };
  const ART = '.ordpar-card-foot';

  // 1. as built: the switch off, no button
  await p.goto(base + '/bm-en/' + args.id + '/', 800);
  out.built = { row: await p.eval(ROW(ART + ' .ordpar-result-controls')), api: await p.eval(
    `window.ordparReport ? window.ordparReport.REPORT_RECEIVER : null`) };

  // 2. the switch on
  await p.send('Network.enable');
  p.on((m) => {
    if (m.method === 'Network.requestWillBeSent' && (m.params.request.url.startsWith(RECV) || m.params.request.url.startsWith(DEAD))) {
      const r = m.params.request;
      out.sent.push({ url: r.url, method: r.method, headers: r.headers, body: r.postData || null,
        referrerPolicy: r.referrerPolicy });
    }
  });
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: SWITCH });
  await p.reload(800);
  out.article = { row: await p.eval(ROW(ART + ' .ordpar-result-controls')), closed: await p.eval(STATE(ART)) };

  // opened by the keyboard: focus into the form
  await p.eval(`document.querySelector('${ART} .ordpar-report-btn').focus(); true`);
  await key(p, 'Enter', 13);
  await p.frames();
  out.article.opened = await p.eval(STATE(ART));
  // what a screen reader is given: the form's controls by their accessible names
  const ax = await p.axNodes();
  out.article.ax = ax.filter((n) => n.role && ['textbox', 'combobox', 'radio', 'group', 'form', 'button', 'status'].includes(n.role.value)
    && n.name && /wrong|mistake|correction|Where|Translation|Audio|Norwegian text|Other|email|credit|Send|Cancel/i.test(n.name.value || ''))
    .map((n) => [n.role.value, n.name.value]);

  // Send with nothing written: the status says so, focus to the text, nothing sent
  await p.eval(`document.querySelector('.ordpar-report-send').click(); true`);
  await sleep(200);
  out.article.empty = await p.eval(STATE(ART));
  out.article.emptySent = out.sent.length;

  // Escape closes, focus back on the button
  await key(p, 'Escape', 27);
  out.article.escaped = await p.eval(STATE(ART));

  // a link as the name to credit: the status says so, nothing sent, the form open
  await openForm(p, ART);
  const beforeLink = out.sent.length;
  out.article.badCredit = await fillAndSend(p, ART, 'LINK: never sent.', 'other', '', 'cheap-pills.com');
  out.article.badCreditSent = out.sent.length - beforeLink;
  await p.eval(`document.querySelector('${ART} .ordpar-report-credit').value = ''; document.querySelector('.ordpar-report-cancel').click(); true`);

  // a report sent, with a name to credit
  await openForm(p, ART);
  out.article.sent = await fillAndSend(p, ART, 'ARTICLE: the audio of the headword says the wrong word.', 'audio', 'reader@example.org', '  Kari  N. ');

  // a failed send: the address dead; the text kept, the form open
  await openForm(p, ART);
  await p.eval(`window.ordparReport.REPORT_RECEIVER = ${JSON.stringify(DEAD)}; true`);
  out.article.failed = await fillAndSend(p, ART, 'FAILED: kept after a failure.', null, '');
  await p.eval(`window.ordparReport.REPORT_RECEIVER = ${JSON.stringify(RECV)}; true`);

  // offline: the form says so, the text kept; online again, the same text sent
  await p.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  await sleep(200);
  out.article.offlineOnline = await p.eval('navigator.onLine');
  const before = out.sent.length;
  out.article.offline = await fillAndSend(p, ART, 'OFFLINE: sent once back online.', 'other', '');
  out.article.offlineSent = out.sent.length - before;
  await p.eval(`document.querySelector('.ordpar-report-cancel').click(); true`);
  await openForm(p, ART);
  out.article.offlineReopened = await p.eval(STATE(ART));
  await p.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  await sleep(200);
  await p.eval(`document.querySelector('.ordpar-report-send').click(); true`);
  for (let i = 0; i < 50 && !(await p.eval(STATE(ART))).done; i++) await sleep(100);
  out.article.online = await p.eval(STATE(ART));

  // 3. a word page: an article shown whole by lookup.js, the button in its row
  await p.goto(base + '/bm-en/' + encodeURIComponent(args.word) + '/', 600);
  const RES = '.ordpar-result-controls';
  for (let i = 0; i < 60 && !(await p.eval(`!!document.querySelector('${RES} .ordpar-report-btn')`)); i++) await sleep(100);
  out.word = { row: await p.eval(ROW(RES)) };
  const scope = await p.eval(`(() => { const r = document.querySelector('${RES}'); const h = r.parentNode;
    h.setAttribute('data-report-test', '1'); return true; })()`);
  const WS = '[data-report-test]';
  await openForm(p, WS);
  out.word.opened = await p.eval(STATE(WS));
  out.word.sent = await fillAndSend(p, WS, 'WORD: sense 1 is mistranslated.', 'translation', '');

  // 4. the total cap: the receiver filled to it for this hour from here (not the page, no browser:
  // any sender counts), then one more from the page
  out.fill = 0;
  for (let i = 0; i < 200; i++) {
    const r = await fetch(RECV, { method: 'POST', body: JSON.stringify({ id: 5, text: 'FILL ' + i }),
      headers: { Origin: new URL(base).origin, 'Content-Type': 'text/plain;charset=UTF-8' } });
    if (r.status === 429) { out.fillRefused = true; break; }
    if (r.status === 204) out.fill++;
  }
  await openForm(p, WS);
  const capped = await fillAndSend(p, WS, 'CAP: refused, kept.', null, '');
  out.rate = [capped.done ? 'sent' : capped.status];
  out.rateKept = capped.text;
  out.rateFailedClass = await p.eval(`!!document.querySelector('${WS} .ordpar-report-status--failed')`);
  // 5. under "Norwegian only" with the labels in Norwegian: the button and the form stay English (152)
  await p.eval(`localStorage.setItem('nbonly', 'on'); localStorage.setItem('labels', 'no'); true`);
  await p.goto(base + '/bm-en/' + args.id + '/', 800);
  await openForm(p, ART);
  out.nbonly = { layer: await p.eval(`document.documentElement.classList.contains('ordpar-nbo')`),
    row: await p.eval(ROW(ART + ' .ordpar-result-controls')), form: await p.eval(STATE(ART)) };

  // the privacy page the form links (the privacy build, 2026-11-05): served, with its section?
  out.privacyPage = await p.eval(`fetch('/privacy/', { cache: 'no-store' }).then((r) => r.ok ? r.text() : null)
    .then((t) => t === null ? null : t.includes('id="reporting-a-mistake"')).catch(() => null)`);

  // the build the site is on, as the page reads it
  out.build = await p.eval(`fetch('/offline/version.json', { cache: 'no-store' }).then((r) => r.ok ? r.json() : null)
    .then((v) => v ? v.build : null).catch(() => null)`);

  // 6. the phone row (Robin, 2026-11-05, as ordbokene: Copy link not shown on a narrow screen where
  // Share is), on the article page and on the word page's row; with Share (the browser's own, or
  // one put in for the check when it has none) and without
  await p.eval(`localStorage.removeItem('nbonly'); localStorage.removeItem('labels'); true`);
  out.nativeShare = await p.eval(`typeof navigator.share === 'function'`);
  const ROWM = (sel) => `(() => {
    const row = document.querySelector(${JSON.stringify(sel)});
    if (!row) return null;
    const shown = (n) => !!n && !n.hidden && getComputedStyle(n).display !== 'none' && n.getClientRects().length > 0;
    const pick = { copy: row.querySelector('#ordpar-copy, .ordpar-result-copy'), share: row.querySelector('#ordpar-share, .ordpar-result-share'),
      report: row.querySelector('.ordpar-report-btn'), heart: row.querySelector('.ordpar-heart'),
      page: row.querySelector('.ordpar-result-page') };                  // site decisions 168
    const o = { width: innerWidth, pagePresent: !!pick.page /* 168 re-ruled: not made at all */, shown: {}, mid: {}, h: {}, w: {}, row: Math.round(row.getBoundingClientRect().width),
      gap: getComputedStyle(row).columnGap, font: getComputedStyle(row).fontSize };
    for (const [k, n] of Object.entries(pick)) {
      o.shown[k] = shown(n);
      if (o.shown[k]) { const r = n.getBoundingClientRect(); o.mid[k] = r.top + r.height / 2; o.h[k] = r.height; o.w[k] = Math.round(r.width);
        o.inside = (o.inside !== false) && r.left >= 0 && r.right <= innerWidth; }
    }
    const three = ['share', 'report', 'heart'].filter((k) => o.shown[k]);
    o.oneLine = three.length === 3 && Math.max(...three.map((k) => o.mid[k])) - Math.min(...three.map((k) => o.mid[k]))
      < Math.min(...three.map((k) => o.h[k])) / 2;
    o.overflow = document.documentElement.scrollWidth > innerWidth;
    // 168: every item shown on the row's first line (no item wrapped to a second)
    const all = Object.keys(pick).filter((k) => o.shown[k]);
    o.allOneLine = all.length > 0 && Math.max(...all.map((k) => o.mid[k])) - Math.min(...all.map((k) => o.mid[k]))
      < Math.min(...all.map((k) => o.h[k])) / 2;
    o.others = [...row.children].filter((c) => shown(c) && !Object.values(pick).includes(c)).map((c) => [c.className, Math.round(c.getBoundingClientRect().width)]);
    return o; })()`;
  const SHARE_ON = `if (typeof navigator.share !== 'function') Object.defineProperty(Navigator.prototype, 'share',
    { configurable: true, value: function () { return Promise.resolve(); } });`;
  const SHARE_OFF = `delete Navigator.prototype.share; try { delete navigator.share; } catch (e) {}`;
  out.phone = {};
  for (const mode of ['share', 'noshare']) {
    const added = await p.send('Page.addScriptToEvaluateOnNewDocument', { source: mode === 'share' ? SHARE_ON : SHARE_OFF });
    for (const w of [320, 360, 390]) {
      await p.size(w, 800, true);
      await p.goto(base + '/bm-en/' + args.id + '/', 800);
      const art = await p.eval(ROWM(ART + ' .ordpar-result-controls'));
      let open = null;
      if (mode === 'share') {          // the form open under the row: its privacy line, the row unmoved
        await openForm(p, ART);
        open = { row: await p.eval(ROWM(ART + ' .ordpar-result-controls')), form: await p.eval(STATE(ART)) };
      }
      await p.goto(base + '/bm-en/' + encodeURIComponent(args.word) + '/', 600);
      for (let i = 0; i < 60 && !(await p.eval(`!!document.querySelector('${RES} .ordpar-report-btn')`)); i++) await sleep(100);
      const word = await p.eval(ROWM(RES));
      out.phone[mode + w] = { article: art, word, open };
    }
    await p.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: added.identifier });
  }
  // and on a computer's width, with Share: Copy link shown as before
  await p.size(1280, 900, false);
  const back = await p.send('Page.addScriptToEvaluateOnNewDocument', { source: SHARE_ON });
  await p.goto(base + '/bm-en/' + args.id + '/', 800);
  out.wide = await p.eval(ROWM(ART + ' .ordpar-result-controls'));
  // 168 (re-ruled 2026-11-06, everywhere): a word page's row on a computer has no "Article page" either
  await p.goto(base + '/bm-en/' + encodeURIComponent(args.word) + '/', 600);
  for (let i = 0; i < 60 && !(await p.eval(`!!document.querySelector('${RES} .ordpar-report-btn')`)); i++) await sleep(100);
  out.wideWord = await p.eval(ROWM(RES));
  await p.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: back.identifier });
  await done(out);
});
