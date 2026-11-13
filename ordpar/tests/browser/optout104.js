// Decisions 104 (Robin, 2026-10-23/24): the opt-out "Send usage statistics" on the settings page.
//
// The setting shows only while the counting is live, which the build tells the page by
// `window.ORDPAR_COUNTING` (build_index.copy_shell, from `chrome.counting()`: events.js RECEIVER
// set). Until 2026-11-05 the privacy page's switch drew it (`window.ORDPAR_PRIVACY`); since site
// decisions 166's privacy build the page can be published with the counting off, so that flag
// must draw nothing. Read in a fresh context: as built (the counting off as shipped: no trace; over
// an overlay built with chrome.PRIVACY on, the page on and the counting off), then with the OLD
// flag set before the page's scripts run (what a privacy-on build wrote until 2026-11-05: still
// no field), then with the counting's flag (CDP `Page.addScriptToEvaluateOnNewDocument`, standing
// in for a build with the counting live): the field, its place (after the offline copy and the
// transfer, before the stored data), On first and chosen, Off stored, kept on reload, and "Delete
// stored data" turning it back on.
//
// Result: { base, built: STATE, pageOnly: STATE, on: STATE, off: STATE, reload: STATE, deleted: STATE }
import { open, base, args, run, done, sleep } from './cdp.js';

const STATE = `(() => {
  const f = document.querySelector('fieldset[data-setting="stats"]');
  const sec = document.getElementById('data');
  const kids = sec ? [...sec.children].map(c => c.getAttribute('data-setting') ||
    (c.classList.contains('ordpar-offline') ? 'offline' : c.classList.contains('ordpar-transfer') ? 'transfer'
      : c.classList.contains('ordpar-stored') ? 'stored' : c.classList.contains('ordpar-settings-sub') ? 'sub' : c.tagName.toLowerCase())) : null;
  const radios = f ? [...f.querySelectorAll('input[type=radio]')] : [];
  return { field: !!f, text: document.body.textContent.includes('Send usage statistics'),
    flag: window.ORDPAR_COUNTING === true, oldFlag: window.ORDPAR_PRIVACY === true, order: kids,
    privacyLink: !!document.querySelector('.ordpar-footer-nav a[href="/privacy/"]'),
    title: f ? f.querySelector('.ordpar-field-title').textContent : null,
    choices: radios.map(r => [r.value, r.labels[0] ? r.labels[0].textContent : null, r.checked]),
    hint: !!(f && f.querySelector('.ordpar-hint-button')),
    stored: localStorage.getItem('stats'),
    quiet: window.ordparEvents ? window.ordparEvents.quiet() : null };
})()`;

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const out = { base };
  await p.goto(base + '/settings/', 800);
  await p.eval(`localStorage.clear(); true`);
  await p.reload(600);
  out.built = await p.eval(STATE);

  // the privacy page's old flag alone: the page on, the counting off (site decisions 166)
  const old = await p.send('Page.addScriptToEvaluateOnNewDocument', { source: 'window.ORDPAR_PRIVACY = true;' });
  await p.reload(800);
  out.pageOnly = await p.eval(STATE);
  await p.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: old.identifier });

  await p.send('Page.addScriptToEvaluateOnNewDocument', { source: 'window.ORDPAR_COUNTING = true;' });
  await p.reload(800);
  out.on = await p.eval(STATE);
  await p.eval(`(() => { const r = document.querySelector('fieldset[data-setting="stats"] input[value="off"]');
    if (!r) return false; r.click(); return true; })()`);
  await sleep(200);
  out.off = await p.eval(STATE);
  await p.reload(800);
  out.reload = await p.eval(STATE);
  await p.eval(`(() => { const b = document.querySelector('.ordpar-settings-delete'); if (b) b.click(); return !!b; })()`);
  await sleep(300);
  out.deleted = await p.eval(STATE);
  await done(out);
});
