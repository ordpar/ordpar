// Site decisions 173 (Robin, 2026-11-07): the readers' survey, "Ordpar — your first impressions", our
// own page `/survey/`, in a browser, sending to the receiver's own code run locally (args.receiver,
// the stand-in's `/survey`). The page's switch (`survey.js` `SURVEY_RECEIVER`) is set before the
// page's scripts run, as report166.js does for reports (a setter on `window.ordparSurvey`), so the
// check never sends anywhere but the stand-in, whatever the build wrote.
//
// Checked: the page (its title, the intro's Privacy link, every question with its label, hint and
// limit, radio buttons and check boxes, the trap out of sight and out of the tab order, Send, the
// names in the accessibility tree); the skipped question ("What is your first language?" hidden
// while "Norwegian is my first language" is chosen, shown again otherwise, never sent while hidden);
// Send with nothing answered (the status says so, nothing sent); answers sent (the thanks line, the
// form gone, focus on the line); a dead address (the failure said, the answers kept); offline (said,
// nothing sent, kept); the receiver's total cap reached from here (reports and answers together:
// the cap's words, the answers kept); every request a POST of exactly `answers` and `follow`, no
// Referer, no Cookie. The footer's "Tell us what you think →": as built (present exactly when the
// build wrote SURVEY_HREF), after the note while there is one, and with the note gone (launch), in a
// line of its own; the same tab. A phone's width: nothing wider than the screen.
//
// args: { receiver: 'http://127.0.0.1:<port>/survey', dead: 'http://127.0.0.1:<port>/survey', report: '<stand-in>/report' }
import { open, base, args, run, done, sleep } from './cdp.js';

const RECV = args.receiver, DEAD = args.dead;
const NATIVE = 'Norwegian is my first language';

const SWITCH = `(() => { let s; Object.defineProperty(window, 'ordparSurvey', { configurable: true,
  get() { return s; }, set(v) { if (v) v.SURVEY_RECEIVER = ${JSON.stringify(RECV)}; s = v; } }); })();`;
// launch: the "under development" note taken away as soon as it is parsed, before shell.js runs
const NO_NOTE = `new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes)
  if (n.classList && n.classList.contains('ordpar-devnote')) n.remove(); })
  .observe(document, { childList: true, subtree: true });`;

const PAGE = `(() => {
  const f = document.getElementById('ordpar-survey');
  if (!f) return null;
  const qs = [...f.querySelectorAll('[data-q]')].map((q) => {
    const kind = q.getAttribute('data-kind');
    const field = q.querySelector('textarea, input[type=text]');
    const label = kind === 'one' || kind === 'many' ? q.querySelector('legend').textContent
      : (field && field.labels[0] ? field.labels[0].textContent : null);
    const holder = q.querySelector('[aria-describedby]');
    const hint = holder ? (document.getElementById(holder.getAttribute('aria-describedby')) || {}).textContent : null;
    return { id: q.getAttribute('data-q'), kind, label, hint, max: field ? field.maxLength : null,
      tag: field ? field.tagName.toLowerCase() : null, shown: !q.hidden && q.getBoundingClientRect().height > 0,
      choices: [...q.querySelectorAll('input[type=radio], input[type=checkbox]')].map((i) => [i.type, i.value, i.labels[0].textContent.trim()]) };
  });
  const trap = f.querySelector('.ordpar-report-trap input'), r = trap.getBoundingClientRect();
  const intro = [...document.querySelectorAll('article.ordpar-about > p:not(.ordpar-survey-done):not(.ordpar-survey-note)')].map((p) => p.textContent);
  const noteEl = document.querySelector('article.ordpar-about > p.ordpar-survey-note');
  const note = noteEl ? { text: noteEl.textContent, bold: !!noteEl.querySelector('strong'), first: noteEl === document.querySelector('h1').nextElementSibling } : null;
  const priv = document.querySelector('article.ordpar-about > p a');
  return { title: document.querySelector('h1').textContent, note, intro, privacy: priv ? priv.getAttribute('href') : null,
    qs, trap: { tab: trap.tabIndex, hidden: trap.closest('[aria-hidden=true]') !== null, offscreen: r.right <= 0 || r.width <= 1 },
    buttons: [...f.querySelectorAll('button')].map((b) => b.textContent), formLabel: f.getAttribute('aria-label'),
    noscriptShown: [...f.querySelectorAll('noscript')].some((n) => n.getBoundingClientRect().height > 0) };
})()`;

const STATE = `(() => {
  const f = document.getElementById('ordpar-survey'), d = document.getElementById('ordpar-survey-done');
  const st = f.querySelector('.ordpar-survey-status');
  const a = document.activeElement;
  const fl = f.querySelector('[data-q=first_language]');
  return { formShown: !f.hidden && f.getBoundingClientRect().height > 0, status: st.textContent,
    statusRole: st.getAttribute('role'), failed: st.classList.contains('ordpar-report-status--failed'),
    done: d && !d.hidden ? d.textContent : null, doneRole: d ? d.getAttribute('role') : null,
    focus: a === d ? 'done' : a ? a.tagName.toLowerCase() : null,
    firstLanguageShown: !fl.hidden && fl.getBoundingClientRect().height > 0,
    kept: (f.querySelector('#ordpar-survey-anything-else') || {}).value };
})()`;

/** Fill the form: `a` maps question ids to a text, a choice, or a list of choices; then Send and
 *  wait for an answer (the status or the thanks line). */
async function fillAndSend(p, a, follow) {
  await p.eval(`(() => {
    const f = document.getElementById('ordpar-survey'), a = ${JSON.stringify(a)};
    for (const [k, v] of Object.entries(a)) {
      const q = f.querySelector('[data-q="' + k + '"]');
      if (Array.isArray(v) || q.getAttribute('data-kind') === 'one') {
        for (const i of q.querySelectorAll('input')) {
          const on = Array.isArray(v) ? v.includes(i.value) : i.value === v;
          if (i.checked !== on) i.click();
        }
      } else {
        const b = q.querySelector('textarea, input'); b.value = v;
        b.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
    f.querySelector('#ordpar-survey-follow').value = ${JSON.stringify(follow || '')};
    f.querySelector('.ordpar-survey-send').click(); return true; })()`);
  for (let i = 0; i < 50; i++) {
    await sleep(100);
    const s = await p.eval(STATE);
    if ((s.status && s.status !== 'Sending …') || s.done) return s;
  }
  return p.eval(STATE);
}

const FOOT = `(() => {
  const a = document.querySelector('.ordpar-footer .ordpar-feedback');
  if (!a) return { link: false };
  const r = a.getBoundingClientRect();
  return { link: true, text: a.textContent, href: a.getAttribute('href'), target: a.getAttribute('target'),
    inNote: !!a.closest('.ordpar-devnote'), inLine: !!a.closest('.ordpar-feedback-line'),
    noteThere: !!document.querySelector('.ordpar-devnote'), shown: r.height > 0,
    lineLast: !!a.closest('.ordpar-feedback-line') && a.closest('.ordpar-footer-inner').lastElementChild === a.closest('.ordpar-feedback-line') };
})()`;

run(async () => {
  const p = await open({ w: 1280, h: 900 });
  const out = { base, sent: [] };

  // 0. the footer link as built, on an article page
  await p.goto(base + '/bm-en/1000/', 800);
  out.builtFoot = await p.eval(FOOT);
  out.builtHref = await p.eval(`fetch('/site/shell.js', { cache: 'no-store' }).then((r) => r.text())
    .then((t) => { const m = t.match(/SURVEY_HREF\\s*=\\s*(["'])(.*?)\\1/); return m ? m[2] : null; })`);

  // 1. the page, the switch on
  await p.send('Network.enable');
  p.on((m) => {
    if (m.method === 'Network.requestWillBeSent' && (m.params.request.url.startsWith(RECV) || m.params.request.url.startsWith(DEAD))) {
      const r = m.params.request;
      out.sent.push({ url: r.url, method: r.method, headers: r.headers, body: r.postData || null, referrerPolicy: r.referrerPolicy });
    }
  });
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: SWITCH });
  await p.goto(base + '/survey/', 800);
  out.page = await p.eval(PAGE);
  if (!out.page) { await done(out); return; }      // no /survey/ where this runs (the live site with the survey off)
  out.foot = await p.eval(FOOT);
  out.ax = (await p.axNodes()).filter((n) => !n.ignored && n.role && ['textbox', 'radio', 'checkbox', 'button', 'group'].includes(n.role.value))
    .map((n) => [n.role.value, n.name ? n.name.value : '']);

  // 2. the skipped question
  out.skip = {};
  out.skip.before = (await p.eval(STATE)).firstLanguageShown;
  await p.eval(`(() => { const q = document.querySelector('[data-q=first_language] input'); q.value = 'NEVER SENT'; return true; })()`);
  await p.eval(`(() => { document.querySelector('[data-q=level] input[value="${NATIVE}"]').click(); return true; })()`);
  await p.frames();
  out.skip.native = (await p.eval(STATE)).firstLanguageShown;
  await p.eval(`(() => { document.querySelector('[data-q=level] input[value="Fluent"]').click(); return true; })()`);
  await p.frames();
  out.skip.fluent = (await p.eval(STATE)).firstLanguageShown;
  await p.reload(800);

  // 3. nothing answered
  let before = out.sent.length;
  out.empty = await fillAndSend(p, {}, '');
  out.emptySent = out.sent.length - before;

  // 4. answers sent
  out.answers = await fillAndSend(p, { level: 'I can read simple texts', first_language: 'Polish',
    looked_up: 'SENT: hus, and it helped.', ideas: ['Example sentences for the words and meanings that don\'t have any yet',
      'Use Ordpar as the dictionary on your e-reader (Kindle, Kobo) when reading Norwegian books'],
    devices: ['Phone'], anything_else: 'First answers.' }, 'reader@example.org');

  // 5. a native speaker: the first language typed, then skipped — never sent
  await p.reload(800);
  out.native = await fillAndSend(p, { first_language: 'NEVER SENT', level: NATIVE, anything_else: 'NATIVE: second answers.' }, '');

  // 6. a dead address: the failure said, the answers kept
  await p.reload(800);
  await p.eval(`(window.ordparSurvey.SURVEY_RECEIVER = ${JSON.stringify(DEAD)}, true)`);
  out.failed = await fillAndSend(p, { anything_else: 'FAILED: kept.' }, '');
  await p.eval(`(window.ordparSurvey.SURVEY_RECEIVER = ${JSON.stringify(RECV)}, true)`);

  // 7. offline: said, nothing sent, kept
  await p.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  before = out.sent.length;
  out.offline = await fillAndSend(p, { anything_else: 'OFFLINE: kept.' }, '');
  out.offlineSent = out.sent.length - before;
  await p.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });

  // 8. the total cap, reached from here with REPORTS (no browser): the page's answers refused too
  out.fill = 0;
  for (let i = 0; i < 200; i++) {
    const r = await fetch(args.report, { method: 'POST', body: JSON.stringify({ id: 5, text: 'FILL ' + i }),
      headers: { Origin: new URL(base).origin, 'Content-Type': 'text/plain;charset=UTF-8' } });
    if (r.status === 429) { out.fillRefused = true; break; }
    if (r.status === 204) out.fill++;
  }
  await p.reload(800);
  out.capped = await fillAndSend(p, { anything_else: 'CAP: refused, kept.' }, '');

  // 9. launch: the note gone, the link in a line of its own
  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: NO_NOTE });
  await p.goto(base + '/bm-en/1000/', 800);
  out.launchFoot = await p.eval(FOOT);

  // 10. a phone's width: nothing wider than the screen
  await p.size(360, 740, true);
  await p.goto(base + '/survey/', 800);
  out.phone = await p.eval(`(() => ({ scroll: document.documentElement.scrollWidth, width: innerWidth,
    wide: [...document.querySelectorAll('#ordpar-survey *')].filter((n) => n.getBoundingClientRect().right > innerWidth + 0.5
      && !n.closest('.ordpar-report-trap')).length }))()`);
  await done(out);
});
