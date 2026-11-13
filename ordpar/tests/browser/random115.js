// Decisions 115 (Robin, 2026-10-24): Random word opens a random headword's SEARCH, as ordbokene's.
//
// For one viewport (args.mobile: a phone, the button tapped; else a computer, clicked), in a fresh
// context: Random word pressed `args.draws` times on the search page (answered in place) and
// `args.fromArticle` times from an article page (args.article; the page is left for the search).
// After each press: the address, the query it carries, the box, the search's first article (the
// first `[data-id]` of `.ordpar-hits`: a full result or a list row, never an inflected-form row)
// and how many articles it shows; then the same address opened afresh, as a typed search's would
// be, and its first article. Each first article is then read from the site's own files: in
// `/index/translated.json`, and its page's summary gloss (`p.ordpar-gloss`) and word class
// (`.ordbok-pos`, "fixed expression" for a set phrase).
//
// Result: { base, draws: [{ from, url, path, hash, q, box, first, n, fresh, gloss, pos, translated,
//   error }] }
import { open, base, args, run, done, sleep } from './cdp.js';

async function until(p, expr, ms = 10000) {
  // a press that navigates (an old build's article address) may destroy the context mid-call
  for (let t = 0; t < ms; t += 100) { try { if (await p.eval(expr)) return true; } catch (e) { /* again */ } await sleep(100); }
  return false;
}

const READ = `(() => {
  const hits = document.querySelector('.ordpar-hits');
  const first = hits && hits.querySelector('[data-id]');
  const ids = hits ? new Set([...hits.querySelectorAll('[data-id]')].map(e => e.getAttribute('data-id'))) : new Set();
  // the search: after #q= on the search page, or (site decisions 117) the word page's own word
  const m = /^#q=([^&]*)/.exec(location.hash) || /^\\/bm-en\\/([^\\/0-9][^\\/]*)\\/$/.exec(location.pathname);
  let q = null; if (m) { try { q = decodeURIComponent(m[1].replace(/\\+/g, ' ')); } catch (e) { q = m[1]; } }
  const box = document.getElementById('ordpar-q');
  return { url: location.href, path: location.pathname, hash: location.hash, q, box: box ? box.value : null,
    first: first ? +first.getAttribute('data-id') : null, n: ids.size };
})()`;

async function press(p) {
  const at = await p.eval(`(() => { const b = document.querySelector('.ordpar-random');
    if (!b || !b.getClientRects().length) return null; const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!at) return false;
  if (args.mobile) await p.tap(at.x, at.y); else await p.click(at.x, at.y);
  return true;
}

/** The first article's facts, from the site's own files. */
async function facts(p, id) {
  return p.eval(`(async () => {
    const tr = await (await fetch('/index/translated.json')).json();
    const r = await fetch('/bm-en/${id}/'); const html = r.ok ? await r.text() : '';
    const d = new DOMParser().parseFromString(html, 'text/html');
    const g = d.querySelector('.ordbok-head .ordpar-gloss'), pos = d.querySelector('.ordbok-head .ordbok-pos');
    return { translated: tr.includes(${id}), gloss: g ? g.textContent.trim() : '', pos: pos ? pos.textContent.trim() : '' };
  })()`);
}

run(async () => {
  const p = await open(args.mobile ? { w: 390, h: 844, mobile: true } : { w: 1280, h: 900 });
  const draws = [];
  await p.goto(base + '/bm-en/', 600);
  await p.eval(`localStorage.clear(); true`);

  const settle = async (from, before) => {
    const ok = await until(p, `(() => { const h = document.querySelector('.ordpar-hits [data-id]');
      const page = /^\\/bm-en\\/[^\\/0-9][^\\/]*\\/$/.test(location.pathname) && !location.hash
        && !document.querySelector('.ordpar-word-title');
      return (location.hash.indexOf('#q=') === 0 || page) && location.href !== ${JSON.stringify(before)} && !!h; })()`, 12000);
    await sleep(300);
    let read; try { read = await p.eval(READ); } catch (e) { await sleep(1500); read = await p.eval(READ); }
    const d = Object.assign({ from, landed: ok }, read);
    draws.push(d);
    return d;
  };

  // on the search page: answered in place
  await p.goto(base + '/bm-en/', 800);
  for (let i = 0; i < (args.draws || 4); i++) {
    const before = await p.eval('location.href');
    if (!await press(p)) { draws.push({ from: 'search', error: 'no Random word button' }); break; }
    await settle('search', before);
  }
  // from an article page: the page is left for the search
  for (let i = 0; i < (args.fromArticle || 2); i++) {
    await p.goto(base + '/bm-en/' + args.article + '/', 800);
    const before = await p.eval('location.href');
    const loaded = p.waitEvent('Page.loadEventFired', 12000);
    if (!await press(p)) { draws.push({ from: 'article', error: 'no Random word button' }); break; }
    await loaded;
    await settle('article', before);
  }
  // each landing: the same address afresh (a typed search's), and the first article's facts
  for (const d of draws) {
    if (d.error || d.first == null) continue;
    if (d.q) {
      await p.goto('about:blank', 50);             // a new document, not a fragment move
      // the word page opened afresh (site decisions 117), or the #q= search
      await p.goto(d.hash && d.hash.indexOf('#q=') === 0 ? base + '/bm-en/' + d.hash : d.url, 800);
      await until(p, `!!document.querySelector('.ordpar-hits [data-id]') && !document.querySelector('.ordpar-word-title')`, 10000);
      d.fresh = (await p.eval(READ)).first;
    }
    Object.assign(d, await facts(p, d.first));
  }
  await done({ base, draws });
});
