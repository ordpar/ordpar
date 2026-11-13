// "Report a mistake" (site decisions 166, 2026-11-05) on the receiver, under bun with no network:
// POST /report, Robin's GET /reports and POST /reports/<id>/done, and the counting's own switch
// (COUNTING) that lets the Worker go live for reports with the counting off. Since 166's
// follow-up (the same day): no per-sender limit — a total cap per hour, nothing about the sender
// read, no KV — and the name to credit (`credit`), deleted with the reply address at closing. Run
// by ordpar/tests/test_ordpar_receiver104.py, or here with `bun test`. D1 is stood in for by
// bun:sqlite running every migration and the same SQL strings; KV by a Map.
import { describe, expect, test, beforeEach, setSystemTime } from 'bun:test';
import { Database } from 'bun:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import * as P from '../src/reports.js';
import { handle, daily } from '../src/worker.js';
import { dailyCode } from '../src/code.js';
import { keyFor, forget, PREFIX } from '../src/secret.js';

setSystemTime(new Date('2026-11-05T12:00:00Z'));

const ROOT = join(import.meta.dir, '..');
const TOKEN = 'a-test-token-of-some-length-0123456789';
const NOW = new Date('2026-11-05T12:10:00Z');

function d1() {
  const db = new Database(':memory:');
  for (const f of readdirSync(join(ROOT, 'migrations')).filter((n) => n.endsWith('.sql')).sort()) {
    db.exec(readFileSync(join(ROOT, 'migrations', f), 'utf8'));
  }
  const prep = (sql) => {
    const st = { sql, args: [] };
    st.bind = (...a) => { st.args = a; return st; };
    st.run = async () => { db.query(sql).run(...st.args); return { success: true }; };
    st.all = async () => ({ results: db.query(sql).all(...st.args) });
    st.first = async () => db.query(sql).get(...st.args);
    return st;
  };
  return {
    raw: db,
    prepare: prep,
    batch: async (stmts) => { db.transaction(() => stmts.forEach((s) => db.query(s.sql).run(...s.args)))(); },
  };
}

function kv() {
  const m = new Map();
  return {
    m,
    get: async (k) => (m.has(k) ? m.get(k).v : null),
    put: async (k, v, o) => { m.set(k, { v, exp: o && o.expiration }); },
    delete: async (k) => { m.delete(k); },
  };
}

const CHROME = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0';
const IP = '198.51.100.23';

function request(path, o = {}) {
  const method = o.method || (o.body !== undefined ? 'POST' : 'GET');
  const headers = new Headers({ 'User-Agent': o.ua || CHROME, 'CF-Connecting-IP': o.ip || IP });
  if (o.origin !== null) headers.set('Origin', o.origin || 'https://ordpar.no');
  if (o.body !== undefined) headers.set('Content-Type', 'text/plain;charset=UTF-8');
  if (o.token) headers.set('Authorization', 'Bearer ' + o.token);
  for (const [k, v] of Object.entries(o.headers || {})) headers.set(k, v);
  const body = o.body === undefined ? undefined : (typeof o.body === 'string' ? o.body : JSON.stringify(o.body));
  return new Request('https://ordpar-receiver.example.workers.dev' + path, { method, headers, body });
}

let env;
const call = (path, o = {}) => handle(request(path, o), env, (p) => p, o.now || NOW);
const rows = (sql) => env.DB.raw.query(sql).all();
const GOOD = { id: 1234, build: '3be273e42565c3a6', category: 'translation', text: 'The English of sense 2 is wrong.', reply: 'reader@example.org', credit: 'Kari N.' };

beforeEach(() => { env = { DB: d1(), SECRETS: kv(), ALLOW_LOCAL: '0', REPORTS_TOKEN: TOKEN }; forget(); });

describe('parseReport: what a report may carry', () => {
  test('a whole report, exactly its fields; any other field ignored', () => {
    expect(P.parseReport(JSON.stringify(Object.assign({ path: '/x', lang: 'en', ua: 'y' }, GOOD)))).toEqual({
      status: 'ok', report: { article: 1234, build: '3be273e42565c3a6', category: 'translation',
        text: 'The English of sense 2 is wrong.', reply: 'reader@example.org', credit: 'Kari N.' } });
  });
  test('the optional fields may be null or missing; the text trimmed and NFC', () => {
    const got = P.parseReport(JSON.stringify({ id: 7, text: '  Å er feil  ', build: null, category: null, reply: null, credit: null }));
    expect(got).toEqual({ status: 'ok', report: { article: 7, build: null, category: null, text: 'Å er feil', reply: null, credit: null } });
    expect(P.parseReport(JSON.stringify({ id: 7, text: 'x', reply: '' })).report.reply).toBe(null);
    expect(P.parseReport(JSON.stringify({ id: 7, text: 'x', credit: '  ' })).report.credit).toBe(null);
    expect(P.parseReport(JSON.stringify({ id: 7, text: 'x' })).report.credit).toBe(null);
  });
  test('the name to credit: cleaned; at most MAX_CREDIT characters; no links', () => {
    expect(P.MAX_CREDIT).toBe(60);
    const name = (c) => P.parseReport(JSON.stringify({ id: 7, text: 'x', credit: c }));
    expect(name('  Kari \n\t Nordmann ').report.credit).toBe('Kari Nordmann');
    expect(name('A\u0301se').report.credit).toBe('\u00c1se');                 // NFC
    expect(name('Ola\u0007 N.').report.credit).toBe('Ola N.');               // a control character dropped
    expect(name('@kari_n').report.credit).toBe('@kari_n');                   // a handle is a name, not a link
    expect(name('x'.repeat(60)).status).toBe('ok');
    for (const bad of ['x'.repeat(61), 'https://spam.example', 'see www.example', 'spam.com', 'cheap.ru/pills',
      'Kari (kari.no)', 'mailto://x', 12, ['Kari'], { n: 'Kari' }]) {
      expect([bad, name(bad).status]).toEqual([bad, 'bad']);
    }
  });
  test('the page refuses what the receiver refuses: the same link pattern and the same longest name', () => {
    const page = readFileSync(join(ROOT, '..', 'site', 'report.js'), 'utf8');
    expect(page).toContain('var LINK = ' + P.LINK.toString() + ';');
    expect(page).toContain('var MAX_CREDIT = ' + P.MAX_CREDIT + ';');
  });
  test('every category the form offers, and none other', () => {
    for (const c of ['translation', 'audio', 'norwegian', 'other']) {
      expect(P.parseReport(JSON.stringify({ id: 1, text: 'x', category: c })).status).toBe('ok');
    }
    expect(P.CATEGORIES).toEqual(['translation', 'audio', 'norwegian', 'other']);
    expect(P.parseReport(JSON.stringify({ id: 1, text: 'x', category: 'spelling' })).status).toBe('bad');
  });
  test('not a report: 400', () => {
    const bad = [
      '', 'not json', '[]', 'null', '{}',
      { text: 'x' }, { id: 0, text: 'x' }, { id: 1.5, text: 'x' }, { id: '12', text: 'x' }, { id: 10000000, text: 'x' },
      { id: 1 }, { id: 1, text: '   ' }, { id: 1, text: 5 }, { id: 1, text: 'x'.repeat(P.MAX_REPORT_TEXT + 1) },
      { id: 1, text: 'x', build: 'not-hex!' }, { id: 1, text: 'x', build: 12 },
      { id: 1, text: 'x', reply: 'nobody' }, { id: 1, text: 'x', reply: 'a b@example.org' }, { id: 1, text: 'x', reply: 5 },
      { id: 1, text: 'x', reply: 'a@' + 'b'.repeat(P.MAX_REPLY) + '.no' },
    ];
    for (const b of bad) expect([b, P.parseReport(typeof b === 'string' ? b : JSON.stringify(b)).status]).toEqual([b, 'bad']);
    expect(P.parseReport(JSON.stringify({ id: 1, text: 'x'.repeat(P.MAX_REPORT_TEXT) })).status).toBe('ok');
  });
  test('the trap filled: dropped', () => {
    expect(P.parseReport(JSON.stringify(Object.assign({ hp: 'http://spam.example' }, GOOD))).status).toBe('drop');
    expect(P.parseReport(JSON.stringify(Object.assign({ hp: '' }, GOOD))).status).toBe('ok');
  });
});

describe('POST /report: accepted', () => {
  test('204 with CORS for ordpar.no, stored as day, article, build, category, text, reply, credit', async () => {
    const res = await call('/report', { body: GOOD });
    expect(res.status).toBe(204);
    expect(await res.text()).toBe('');
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe('https://ordpar.no');
    expect(rows('SELECT * FROM reports')).toEqual([{ id: 1, day: '2026-11-05', article: 1234,
      build: '3be273e42565c3a6', category: 'translation', text: 'The English of sense 2 is wrong.',
      reply: 'reader@example.org', credit: 'Kari N.', done: null }]);
  });
  test('nothing about the sender is read: no address, no browser name, no KV', async () => {
    const asked = [];
    const r = request('/report', { body: GOOD });
    const get = r.headers.get.bind(r.headers);
    r.headers.get = (name) => { asked.push(name.toLowerCase()); return get(name); };
    delete env.SECRETS;                                   // reports need no KV at all
    expect((await handle(r, env, (p) => p, NOW)).status).toBe(204);
    expect([...new Set(asked)].sort()).toEqual(['content-length', 'origin']);
    expect(rows('SELECT count(*) AS n FROM reports')[0].n).toBe(1);
    // and the source has no read of them on the report's path
    const src = readFileSync(join(ROOT, 'src', 'worker.js'), 'utf8');
    const rep = src.slice(src.indexOf('async function withinCap'), src.indexOf('export async function handleReports'));
    for (const word of ['CF-Connecting-IP', 'User-Agent', 'SECRETS', 'keyFor', 'request.cf']) expect([word, rep.includes(word)]).toEqual([word, false]);
    expect(readFileSync(join(ROOT, 'src', 'reports.js'), 'utf8')).not.toMatch(/rateCode|CF-Connecting-IP|User-Agent|crypto\.subtle/);
  });
  test('no address (IP) and no browser name anywhere in the database, nor the day\'s view code', async () => {
    await call('/report', { body: GOOD });
    const key = await keyFor(env.SECRETS, '2026-11-05');
    const view = await dailyCode(key, IP, CHROME);
    const tables = rows("SELECT name FROM sqlite_master WHERE type='table'").map((r) => r.name);
    const dump = JSON.stringify(tables.map((t) => rows('SELECT * FROM ' + t)));
    for (const s of [IP, CHROME, 'Edg/141', view]) expect(dump.includes(s)).toBe(false);
    // the reports table has no column for them, and no table keeps a sender's code
    const cols = rows('PRAGMA table_info(reports)').map((r) => r.name);
    expect(cols).toEqual(['id', 'day', 'article', 'build', 'category', 'text', 'reply', 'credit', 'done']);
    expect(tables).not.toContain('report_rate');
    expect(rows('PRAGMA table_info(report_hours)').map((r) => r.name)).toEqual(['hour', 'n']);
  });
  test('the preflight answers for POST from ordpar.no', async () => {
    const res = await call('/report', { method: 'OPTIONS' });
    expect(res.status).toBe(204);
    expect(res.headers.get('Access-Control-Allow-Methods')).toBe('POST');
  });
  test('the counting off does not stop reports (COUNTING unset or "0")', async () => {
    env.COUNTING = '0';
    expect((await call('/report', { body: GOOD })).status).toBe(204);
    delete env.COUNTING;
    expect((await call('/report', { body: GOOD })).status).toBe(204);
    expect(rows('SELECT count(*) AS n FROM reports')[0].n).toBe(2);
  });
  test('Global Privacy Control does not stop a report the reader sent', async () => {
    expect((await call('/report', { body: GOOD, headers: { 'Sec-GPC': '1' } })).status).toBe(204);
    expect(rows('SELECT count(*) AS n FROM reports')[0].n).toBe(1);
  });
});

describe('POST /report: refused, dropped, limited', () => {
  const none = () => rows('SELECT count(*) AS n FROM reports')[0].n;
  test('another origin, or none: 400, nothing stored', async () => {
    for (const origin of ['https://evil.example', 'http://ordpar.no', 'http://127.0.0.1:8000', null]) {
      const res = await call('/report', { body: GOOD, origin });
      expect([origin, res.status, res.headers.get('Access-Control-Allow-Origin')]).toEqual([origin, 400, null]);
    }
    expect(none()).toBe(0);
  });
  test('127.0.0.1 only with ALLOW_LOCAL (the local tests)', async () => {
    env.ALLOW_LOCAL = '1';
    expect((await call('/report', { body: GOOD, origin: 'http://127.0.0.1:8123' })).status).toBe(204);
  });
  test('another method: 400', async () => {
    expect((await call('/report', { method: 'GET' })).status).toBe(400);
    expect((await call('/report', { method: 'PUT', body: GOOD })).status).toBe(400);
    expect(none()).toBe(0);
  });
  test('size: a body over MAX_REPORT_BODY bytes refused, with or without its length', async () => {
    const big = JSON.stringify(Object.assign({}, GOOD, { pad: 'ø'.repeat(P.MAX_REPORT_BODY) }));
    expect((await call('/report', { body: big })).status).toBe(400);
    const stream = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode(big)); c.close(); } });
    const r = new Request('https://ordpar-receiver.example.workers.dev/report', {
      method: 'POST', body: stream, duplex: 'half',
      headers: { Origin: 'https://ordpar.no', 'User-Agent': CHROME } });
    expect(r.headers.get('Content-Length')).toBe(null);
    expect((await handle(r, env, (p) => p, NOW)).status).toBe(400);
    // the longest text the form allows, in a letter of two bytes, goes through
    expect((await call('/report', { body: Object.assign({}, GOOD, { text: 'ø'.repeat(P.MAX_REPORT_TEXT) }) })).status).toBe(204);
    expect(none()).toBe(1);
  });
  test('the trap filled: 204, nothing stored, and it does not count toward the cap', async () => {
    for (let i = 0; i < P.REPORTS_PER_HOUR + 2; i++) {
      expect((await call('/report', { body: Object.assign({ hp: 'x' }, GOOD) })).status).toBe(204);
    }
    expect(none()).toBe(0);
    expect(rows('SELECT count(*) AS n FROM report_hours')[0].n).toBe(0);
    expect((await call('/report', { body: GOOD })).status).toBe(204);
  });
  test('the total cap: REPORTS_PER_HOUR an hour from everyone together, then 429 for every sender', async () => {
    expect(P.REPORTS_PER_HOUR).toBe(30);
    expect(P.rateCode).toBe(undefined);
    // 30 reports from 30 different senders (addresses and browsers): all taken
    for (let i = 0; i < 30; i++) {
      expect((await call('/report', { body: GOOD, ip: '203.0.113.' + i, ua: CHROME.replace('141', String(100 + i)) })).status).toBe(204);
    }
    expect(none()).toBe(30);
    expect(rows('SELECT * FROM report_hours')).toEqual([{ hour: '2026-11-05T12', n: 30 }]);
    // the 31st, from a sender never seen, and from one already seen: both 429
    for (const o of [{ ip: '192.0.2.77', ua: 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0' }, {}]) {
      const res = await call('/report', Object.assign({ body: GOOD }, o));
      expect(res.status).toBe(429);
      expect(res.headers.get('Access-Control-Allow-Origin')).toBe('https://ordpar.no');   // the page can read it
    }
    expect(none()).toBe(30);
    // the next hour: taken again, and the last hour's count gone
    expect((await call('/report', { body: GOOD, now: new Date('2026-11-05T13:00:30Z') })).status).toBe(204);
    expect(rows('SELECT * FROM report_hours')).toEqual([{ hour: '2026-11-05T13', n: 1 }]);
    expect(none()).toBe(31);
  });
  test('a store that fails answers 503, so the page says it failed', async () => {
    env.DB.raw.exec('DROP TABLE reports');
    expect((await call('/report', { body: GOOD })).status).toBe(503);
  });
});

describe('GET /reports and POST /reports/<id>/done: Robin\'s, behind the token', () => {
  async function three() {
    await call('/report', { body: Object.assign({}, GOOD, { text: 'first' }) });
    await call('/report', { body: Object.assign({}, GOOD, { text: 'second', reply: null, category: null, credit: null }), ip: '203.0.113.1' });
    await call('/report', { body: Object.assign({}, GOOD, { text: 'third', id: 99 }), ip: '203.0.113.2' });
  }
  test('without the token, with a wrong one, or with the secret unset: 401, nothing listed', async () => {
    await three();
    for (const o of [{}, { token: 'wrong-token-of-some-length-0000' }, { token: TOKEN.slice(0, -1) }, { token: TOKEN + 'x' }]) {
      const res = await call('/reports', o);
      expect(res.status).toBe(401);
      expect(await res.text()).toBe('');
    }
    expect((await call('/reports', { headers: { Authorization: TOKEN } })).status).toBe(401);   // no "Bearer "
    delete env.REPORTS_TOKEN;
    expect((await call('/reports', { token: TOKEN })).status).toBe(401);
    env.REPORTS_TOKEN = 'short';
    expect((await call('/reports', { token: 'short' })).status).toBe(401);
  });
  test('with the token: the open reports, newest first, as JSON, no CORS', async () => {
    await three();
    const res = await call('/reports', { token: TOKEN, origin: null });
    expect(res.status).toBe(200);
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe(null);
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    const got = await res.json();
    expect(got.reports.map((r) => r.text)).toEqual(['third', 'second', 'first']);
    expect(got.reports[0]).toEqual({ id: 3, day: '2026-11-05', article: 99, build: '3be273e42565c3a6',
      category: 'translation', text: 'third', reply: 'reader@example.org', credit: 'Kari N.' });
    expect(got.reports[1].reply).toBe(null);
    expect(got.reports[1].credit).toBe(null);
  });
  test('done (closed, Done or Fixed): the reply address and the name deleted, the day and the text kept; no longer listed', async () => {
    await three();
    const res = await call('/reports/1/done', { method: 'POST', token: TOKEN, origin: null });
    expect(res.status).toBe(204);
    expect(rows('SELECT * FROM reports WHERE id = 1')).toEqual([{ id: 1, day: '2026-11-05', article: 1234,
      build: '3be273e42565c3a6', category: 'translation', text: 'first', reply: null, credit: null, done: '2026-11-05' }]);
    expect(JSON.stringify(rows('SELECT * FROM reports WHERE id = 1'))).not.toContain('reader@example.org');
    expect(JSON.stringify(rows('SELECT * FROM reports WHERE id = 1'))).not.toContain('Kari');
    expect(rows('SELECT credit FROM reports WHERE id = 3')[0].credit).toBe('Kari N.');   // the open one keeps it
    const list = await (await call('/reports', { token: TOKEN })).json();
    expect(list.reports.map((r) => r.id)).toEqual([3, 2]);
    // twice, or a report that does not exist: 404
    expect((await call('/reports/1/done', { method: 'POST', token: TOKEN })).status).toBe(404);
    expect((await call('/reports/77/done', { method: 'POST', token: TOKEN })).status).toBe(404);
  });
  test('done without the token: 401, nothing changed; GET on done, or another path: 404', async () => {
    await three();
    expect((await call('/reports/1/done', { method: 'POST' })).status).toBe(401);
    expect(rows('SELECT reply FROM reports WHERE id = 1')[0].reply).toBe('reader@example.org');
    expect((await call('/reports/1/done', { token: TOKEN })).status).toBe(404);
    expect((await call('/reports/x/done', { method: 'POST', token: TOKEN })).status).toBe(404);
    expect((await call('/reports', { method: 'POST', token: TOKEN })).status).toBe(404);
  });
});

describe('the counting off (COUNTING not "1", as configured): reports deployable alone', () => {
  const VIEW = { type: 'view', path: '/bm-en/1/' };
  test('/e is not served: 400 for a valid view or search, nothing stored', async () => {
    for (const c of [undefined, '0', 'yes', 'true']) {
      if (c === undefined) delete env.COUNTING; else env.COUNTING = c;
      expect((await call('/e', { body: VIEW })).status).toBe(400);
      expect((await call('/e', { body: { type: 'hit', query: 'hus' } })).status).toBe(400);
      expect((await call('/e', { method: 'OPTIONS' })).status).toBe(400);
    }
    expect(rows('SELECT count(*) AS n FROM views')[0].n + rows('SELECT count(*) AS n FROM searches')[0].n).toBe(0);
    env.COUNTING = '1';
    expect((await call('/e', { body: VIEW })).status).toBe(204);
  });
  test('the daily run makes no totals and nothing ahead; a left secret and past hours\' counts deleted', async () => {
    env.DB.raw.query("INSERT INTO views VALUES ('2026-11-04', 600, '/', 'abc')").run();
    env.DB.raw.query("INSERT INTO report_hours VALUES ('2026-11-04T23', 2), ('2026-11-05T00', 1)").run();
    env.SECRETS.m.set(PREFIX + '2026-11-04', { v: 'x', exp: 0 });
    const out = await daily(env, new Date('2026-11-05T00:05:00Z'));
    expect(out.counting).toBe(false);
    expect(rows('SELECT count(*) AS n FROM daily_views')[0].n).toBe(0);
    expect(env.SECRETS.m.has(PREFIX + '2026-11-04')).toBe(false);
    expect(env.SECRETS.m.has(PREFIX + '2026-11-06')).toBe(false);
    expect(rows('SELECT hour FROM report_hours')).toEqual([{ hour: '2026-11-05T00' }]);
  });
  test('the counting off and no KV bound (as configured): the daily run still runs', async () => {
    delete env.SECRETS;
    env.DB.raw.query("INSERT INTO report_hours VALUES ('2026-11-04T23', 2)").run();
    expect((await daily(env, new Date('2026-11-05T00:05:00Z'))).counting).toBe(false);
    expect(rows('SELECT count(*) AS n FROM report_hours')[0].n).toBe(0);
  });
  test('with the counting on, the daily run deletes past hours\' counts too', async () => {
    env.COUNTING = '1';
    env.DB.raw.query("INSERT INTO report_hours VALUES ('2026-11-04T23', 2)").run();
    await daily(env, new Date('2026-11-05T00:05:00Z'));
    expect(rows('SELECT count(*) AS n FROM report_hours')[0].n).toBe(0);
  });
});

describe('wrangler.jsonc and the code: reports on, counting off', () => {
  const text = readFileSync(join(ROOT, 'wrangler.jsonc'), 'utf8');
  const cfg = JSON.parse(text.replace(/^\s*\/\/.*$/gm, ''));
  test('COUNTING "0" as configured; the token never in the configuration', () => {
    expect(cfg.vars.COUNTING).toBe('0');
    expect(Object.keys(cfg.vars).sort()).toEqual(['ALLOW_LOCAL', 'COUNTING']);
    expect(text).not.toMatch(/REPORTS_TOKEN"\s*:/);
  });
  test('no KV binding while the counting is off: reports use D1 alone; the binding waits in a comment', () => {
    expect(cfg.kv_namespaces).toBe(undefined);
    expect(cfg.d1_databases[0].binding).toBe('DB');
    expect(text).toMatch(/^\s*\/\/\s*,"kv_namespaces": \[ \{ "binding": "SECRETS"/m);
  });
  test('the report code never logs', () => {
    expect(readFileSync(join(ROOT, 'src', 'reports.js'), 'utf8')).not.toMatch(/console\./);
    expect(readFileSync(join(ROOT, 'src', 'worker.js'), 'utf8')).not.toMatch(/console\./);
  });
  test('the page\'s limits are the receiver\'s (ordpar/site/report.js)', () => {
    const page = readFileSync(join(ROOT, '..', 'site', 'report.js'), 'utf8');
    expect(page).toContain('var MAX_TEXT = ' + P.MAX_REPORT_TEXT + ';');
    expect(page).toContain('var MAX_REPLY = ' + P.MAX_REPLY + ';');
    expect(page).toContain("var CATEGORIES = ['translation', 'audio', 'norwegian', 'other'];");
    expect(page).toContain("var REPORT_RECEIVER = '';");
  });
});
