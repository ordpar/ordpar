// The site's browser tests (decisions 100): a small Chrome DevTools Protocol client for bun.
//
// The browser is started by the Python side (`ordpar/tests/browser/harness.py`), once per test
// file, headless Edge with a throwaway profile; a check script connects to it here, gets a FRESH
// browser context (its own storage: no localStorage, cache or service worker carried over from
// another check) and one page in it, and closes both when done. Grown out of the build agents'
// helper copied from one evidence folder to the next (`.../homograph-93-2026-10-22/scripts/cdp.js`).
//
//   import { open, base, args, done } from './cdp.js';
//   const p = await open();                 // reads ORDPAR_CDP_PORT
//   await p.goto(base + '/bm-en/39910/');   // base = ORDPAR_BASE, no trailing slash
//   const v = await p.eval('document.title');
//   done({ ok: true, ... });                // ONE JSON line on stdout, then closes the page
//
// A check prints exactly one JSON object as its LAST stdout line (`done`); the harness parses it.
// `args` is the JSON the harness passed in ORDPAR_ARGS (an object; {} if none).

export const base = (process.env.ORDPAR_BASE || '').replace(/\/+$/, '');
export const args = JSON.parse(process.env.ORDPAR_ARGS || '{}');
const PORT = +process.env.ORDPAR_CDP_PORT;
const sleep = ms => new Promise(r => setTimeout(r, ms));
export { sleep };

let opened = null;

/** Connect to the browser, make a fresh context and a page in it. `w`×`h` the viewport;
 *  `mobile` true for a phone (touch, mobile viewport, DPR 3, a phone's user agent). */
export async function open({ w = 1280, h = 800, mobile = false } = {}) {
  if (!PORT) throw new Error('ORDPAR_CDP_PORT is not set (run through harness.py)');
  const ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((ok, bad) => { ws.onopen = ok; ws.onerror = bad; });
  let id = 0; const waits = {}; const listeners = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && waits[m.id]) { waits[m.id](m); delete waits[m.id]; } else listeners.forEach(f => f(m));
  };
  const raw = (method, params = {}, sessionId) => new Promise((ok, bad) => {
    const i = ++id;
    waits[i] = m => m.error ? bad(new Error(method + ': ' + JSON.stringify(m.error))) : ok(m.result);
    ws.send(JSON.stringify(sessionId ? { id: i, method, params, sessionId } : { id: i, method, params }));
  });
  const { browserContextId } = await raw('Target.createBrowserContext', {});
  const { targetId } = await raw('Target.createTarget', { url: 'about:blank', browserContextId });
  const { sessionId: sid } = await raw('Target.attachToTarget', { targetId, flatten: true });
  const send = (m, p) => raw(m, p, sid);
  await send('Page.enable'); await send('Runtime.enable'); await send('DOM.enable');
  const waitEvent = (name, ms = 20000) => new Promise(r => {
    const f = m => { if (m.sessionId === sid && m.method === name) { listeners.splice(listeners.indexOf(f), 1); r(m.params); } };
    listeners.push(f); setTimeout(() => { const i = listeners.indexOf(f); if (i >= 0) { listeners.splice(i, 1); r(null); } }, ms);
  });

  const page = {
    send, raw, on(f) { listeners.push(f); }, waitEvent,
    /** Load `url`, wait for its load event, then `settle` ms more (the page's own scripts). */
    async goto(url, settle = 300) {
      const loaded = waitEvent('Page.loadEventFired');
      const r = await send('Page.navigate', { url });
      if (r.errorText) throw new Error('navigate ' + url + ': ' + r.errorText);
      await loaded; await sleep(settle);
    },
    async reload(settle = 300) {
      const loaded = waitEvent('Page.loadEventFired');
      await send('Page.reload', {}); await loaded; await sleep(settle);
    },
    /** Evaluate an expression in the page (awaiting a promise); returns its value by value. */
    async eval(expr) {
      const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(expr.slice(0, 100) + ' :: ' + JSON.stringify(r.exceptionDetails).slice(0, 500));
      return r.result.value;
    },
    /** Two animation frames: style and layout caught up after a change. */
    frames() { return page.eval('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(true))))'); },
    async size(w, h, mobile = false) {
      await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: mobile ? 3 : 1, mobile });
      await send('Emulation.setTouchEmulationEnabled', mobile ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
      await send('Emulation.setUserAgentOverride', { userAgent: mobile
        ? 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36'
        : ver['User-Agent'].replace('HeadlessChrome', 'Chrome') });
    },
    /** A touch tap at viewport (x, y). */
    async tap(x, y) {
      await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
      await sleep(60);
      await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    },
    /** A mouse click at viewport (x, y). */
    async click(x, y) {
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    },
    /** The accessibility tree's nodes, as Chrome builds it for screen readers. */
    async axNodes() { return (await send('Accessibility.getFullAXTree', {})).nodes; },
    /** The attributes of a DOM node by its backend id, as {name: value}. */
    async attrs(backendNodeId) {
      const { node } = await send('DOM.describeNode', { backendNodeId });
      const a = {}; const l = node.attributes || [];
      for (let i = 0; i < l.length; i += 2) a[l[i]] = l[i + 1];
      return a;
    },
    /** Close the page and its context (each step given 3 s at most); safe to call twice. */
    async close() {
      if (page.closed) return; page.closed = true;
      const t = pr => Promise.race([pr.catch(() => {}), sleep(3000)]);
      await t(raw('Target.closeTarget', { targetId }));
      await t(raw('Target.disposeBrowserContext', { browserContextId }));
      ws.close();
    },
  };
  await page.size(w, h, mobile);
  opened = page;
  return page;
}

/** Print the check's result as one JSON line and close the page. */
export async function done(result) { await finish(result, 0); }

async function finish(result, code) {
  if (opened) await opened.close();
  // written and flushed before exiting: a large result through a pipe is otherwise cut short
  await new Promise(r => process.stdout.write(JSON.stringify(result) + String.fromCharCode(10), r));
  process.exit(code);
}

/** Run `main`, reporting an exception as {error} so the harness shows it rather than a bare exit code. */
export async function run(main) {
  try { await main(); }
  catch (e) {
    await finish({ error: e && e.message ? e.message + ' | ' + e.stack : String(e) }, 1);
  }
}
