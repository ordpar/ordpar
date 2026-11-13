// The receiver's own tests, under bun with no network (site decisions 26, 62, 104): run by
// ordpar/tests/test_ordpar_receiver104.py, or here with `bun test`. D1 is stood in for by
// bun:sqlite running the migration and the same SQL strings; KV by a Map that keeps expirations.
import { describe, expect, test, beforeEach, setSystemTime } from 'bun:test';
import { Database } from 'bun:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import * as R from '../src/rules.js';
import { isCrawler, isDataCentre, LISTS } from '../src/bots.js';
import { dailyCode, importKey, newSecret } from '../src/code.js';
import { keyFor, rotate, expiry, forget, PREFIX } from '../src/secret.js';
import { handle, daily } from '../src/worker.js';

// The tests run the receiver at fixed dates around 2026-10-23, and the KV stand-in refuses an expiration
// under 60 s from Date.now(), as KV does; so the clock is fixed there too, or every test that writes a
// secret fails once the real date passes those days (it did on 2026-10-24).
setSystemTime(new Date('2026-10-23T00:00:00Z'));

const ROOT = join(import.meta.dir, '..');

/* ------------------------------------------------------------ stand-ins */

function d1() {
  const db = new Database(':memory:');
  // every migration, in order (site decisions 166 added 0002_reports.sql)
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
    put: async (k, v, o) => {
      if (o && o.expiration && o.expiration * 1000 < Date.now() + 60000) throw new Error('expiration < 60 s');
      m.set(k, { v, exp: o && o.expiration });
    },
    delete: async (k) => { m.delete(k); },
  };
}

const CHROME = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0';

function request(body, o = {}) {
  const headers = new Headers({
    Origin: o.origin === undefined ? 'https://ordpar.no' : o.origin,
    'User-Agent': o.ua === undefined ? CHROME : o.ua,
    'CF-Connecting-IP': o.ip || '192.0.2.1',
    'Content-Type': 'text/plain;charset=UTF-8',
  });
  if (o.origin === null) headers.delete('Origin');
  for (const [k, v] of Object.entries(o.headers || {})) headers.set(k, v);
  const r = new Request('https://ordpar-receiver.example.workers.dev' + (o.path || '/e'), {
    method: o.method || 'POST', headers,
    body: (o.method || 'POST') === 'POST' ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
  });
  Object.defineProperty(r, 'cf', { value: { asn: o.asn || 2119, asOrganization: 'Telenor Norge AS' } });
  return r;
}

let env, pending;
async function send(body, o) {
  pending = [];
  const res = await handle(request(body, o), env, (p) => pending.push(p), o && o.now);
  await Promise.all(pending);
  return res;
}
const rows = (sql) => env.DB.raw.query(sql).all();

// the counting ON here (COUNTING '1'): these are the counting's tests; with it off, as
// configured, /e is not served (site decisions 166: test/report.test.js)
beforeEach(() => { env = { DB: d1(), SECRETS: kv(), ALLOW_LOCAL: '0', COUNTING: '1' }; forget(); });

/* ------------------------------------------------------------ validation */

describe('parseEvent: what an event may carry', () => {
  test('the five types, each with exactly its fields; any other field dropped', () => {
    expect(R.parseEvent('{"type":"view","path":"/bm-en/12/","id":"x","ua":"y"}'))
      .toEqual({ status: 'ok', event: { type: 'view', path: '/bm-en/12/' } });
    expect(R.parseEvent('{"type":"install","path":"/x"}')).toEqual({ status: 'ok', event: { type: 'install' } });
    expect(R.parseEvent('{"type":"hit","query":"hus","session":"s"}'))
      .toEqual({ status: 'ok', event: { type: 'hit', query: 'hus', lang: 'nb' } });
    expect(R.parseEvent('{"type":"miss","query":"vus"}'))
      .toEqual({ status: 'ok', event: { type: 'miss', query: 'vus', word: null, position: null, lang: 'nb' } });
    expect(R.parseEvent('{"type":"miss","query":"vus","word":"hus","position":2}'))
      .toEqual({ status: 'ok', event: { type: 'miss', query: 'vus', word: 'hus', position: 2, lang: 'nb' } });
    expect(R.parseEvent('{"type":"pick","query":"hu","word":"hus","position":1,"code":"c"}'))
      .toEqual({ status: 'ok', event: { type: 'pick', query: 'hu', word: 'hus', position: 1, lang: 'nb' } });
  });

  test("148's follow-up: a search's language, 'en' or 'nb', kept with it; missing, 'nb'; anything else 400", () => {
    expect(R.parseEvent('{"type":"hit","query":"House","lang":"en"}'))
      .toEqual({ status: 'ok', event: { type: 'hit', query: 'house', lang: 'en' } });
    expect(R.parseEvent('{"type":"hit","query":"hus","lang":"nb"}').event.lang).toBe('nb');
    expect(R.parseEvent('{"type":"miss","query":"hoose","word":"choose","position":2,"lang":"en"}'))
      .toEqual({ status: 'ok', event: { type: 'miss', query: 'hoose', word: 'choose', position: 2, lang: 'en' } });
    expect(R.parseEvent('{"type":"miss","query":"hoose","word":null,"position":null,"lang":"en"}').event)
      .toEqual({ type: 'miss', query: 'hoose', word: null, position: null, lang: 'en' });
    expect(R.parseEvent('{"type":"pick","query":"hou","word":"house","position":1,"lang":"en"}').event)
      .toEqual({ type: 'pick', query: 'hou', word: 'house', position: 1, lang: 'en' });
    // the same rules as the Norwegian search: a digit or over 40 characters drops it
    expect(R.parseEvent('{"type":"hit","query":"house 2","lang":"en"}').status).toBe('drop');
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: 'a'.repeat(41), lang: 'en' })).status).toBe('drop');
    for (const l of ['"EN"', '"pl"', '""', '1', 'true', '["en"]']) {
      expect(R.parseEvent('{"type":"hit","query":"house","lang":' + l + '}').status).toBe('bad');
    }
    // a view and an install carry no language
    expect(R.parseEvent('{"type":"view","path":"/","lang":"en"}').event).toEqual({ type: 'view', path: '/' });
    expect(R.parseEvent('{"type":"install","lang":"en"}').event).toEqual({ type: 'install' });
  });

  test('62: a query with a digit, or over 40 characters, drops the event', () => {
    expect(R.parseEvent('{"type":"hit","query":"hus2"}').status).toBe('drop');
    expect(R.parseEvent('{"type":"miss","query":"ring 22 33 44 55"}').status).toBe('drop');
    expect(R.parseEvent('{"type":"hit","query":"٣"}').status).toBe('drop');          // any script's digits
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: 'a'.repeat(40) })).status).toBe('ok');
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: 'a'.repeat(41) })).status).toBe('drop');
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: 'æ'.repeat(40) })).status).toBe('ok');   // characters, not bytes
    expect(R.parseEvent(JSON.stringify({ type: 'pick', query: 'h', word: 'x'.repeat(61), position: 1 })).status).toBe('drop');
  });

  test('the query stored NFC, spaces collapsed', () => {
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: '  gå   hjem ' })).event.query).toBe('gå hjem');
  });

  test('104 (R11): the query and the word chosen stored lower-cased, so "Hus" and "hus" are one string', () => {
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: 'Hus' })).event.query).toBe('hus');
    expect(R.parseEvent(JSON.stringify({ type: 'hit', query: 'ÆRE Å' })).event.query).toBe('ære å');
    expect(R.parseEvent(JSON.stringify({ type: 'miss', query: 'Vus', word: 'Hus', position: 1 })).event)
      .toEqual({ type: 'miss', query: 'vus', word: 'hus', position: 1, lang: 'nb' });
    expect(R.parseEvent(JSON.stringify({ type: 'pick', query: 'OS', word: 'Oslo', position: 2 })).event)
      .toEqual({ type: 'pick', query: 'os', word: 'oslo', position: 2, lang: 'nb' });
    expect(R.cleanQuery('A'.repeat(40))).toBe('a'.repeat(40));
    expect(R.cleanQuery('A'.repeat(41))).toBe(null);
  });

  test('not an event: 400 material', () => {
    for (const t of ['', 'x', '[]', 'null', '{"type":"click"}', '{"type":"view"}', '{"type":"hit"}',
      '{"type":"hit","query":"   "}', '{"type":"pick","query":"hu","word":"hus"}',
      '{"type":"pick","query":"hu","word":"hus","position":0}',
      '{"type":"pick","query":"hu","word":"hus","position":1.5}',
      '{"type":"miss","query":"vus","word":"hus"}',
      JSON.stringify({ type: 'view', path: '/' + 'a'.repeat(600) })]) {
      expect(R.parseEvent(t).status).toBe('bad');
    }
  });

  test('a view stores a known path, anything else as /other (a mistyped address can hold a word)', () => {
    for (const p of ['/', '/bm-en/', '/bm-en/1/', '/bm-en/1234567/', '/about/', '/privacy/', '/settings/',
      '/favourites/', '/history/']) {
      expect(R.cleanPath(p)).toBe(p);
    }
    for (const p of ['/bm-en/hus', '/bm-en/?q=hus', '/bm-en/12', '/x/', '/bm-en/12345678/', 'about']) {
      expect(R.cleanPath(p)).toBe(R.OTHER_PATH);
    }
  });

  test('origins: ordpar.no; 127.0.0.1 only when ALLOW_LOCAL', () => {
    expect(R.allowedOrigin('https://ordpar.no', false)).toBe(true);
    expect(R.allowedOrigin('http://ordpar.no', false)).toBe(false);
    expect(R.allowedOrigin('https://ordpar.no.evil.example', false)).toBe(false);
    expect(R.allowedOrigin('http://127.0.0.1:8099', false)).toBe(false);
    expect(R.allowedOrigin('http://127.0.0.1:8099', true)).toBe(true);
    expect(R.allowedOrigin(null, true)).toBe(false);
  });

  test('day and minute in UTC', () => {
    const d = new Date('2026-10-23T23:59:30Z');
    expect(R.dayOf(d)).toBe('2026-10-23');
    expect(R.minuteOf(d)).toBe(1439);
    expect(R.daysBefore('2026-03-01', 1)).toBe('2026-02-28');
    expect(R.daysBefore('2026-10-23', 90)).toBe('2026-07-25');
  });
});

/* ------------------------------------------------------------ the bot lists */

describe('layers 2 and 5: the kept lists', () => {
  test('ordinary browsers pass; crawlers, headless browsers and no browser name do not', () => {
    for (const ua of [CHROME,
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
      'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1',
      'Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/28.0 Chrome/130.0.0.0 Mobile Safari/537.36',
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15',
      'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 OPR/120.0.0.0']) {
      expect(isCrawler(ua)).toBe(false);
    }
    for (const ua of ['Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
      'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm) Chrome/116.0.1938.76 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/141.0.0.0 Safari/537.36',
      'curl/8.9.1', 'python-requests/2.32.3', '', null, undefined]) {
      expect(isCrawler(ua)).toBe(true);
    }
  });

  test('the big clouds are on the data-centre list; home and mobile networks and the privacy relays are not', () => {
    for (const asn of [16509, 14618, 15169, 8075, 14061, 24940, 16276]) expect(isDataCentre(asn)).toBe(true);
    // Telenor, Telia, Ice (NO); Cloudflare, Akamai, Fastly (iCloud Private Relay egress); Apple
    for (const asn of [2119, 12929, 29695, 13335, 20940, 36183, 54113, 714, undefined, 'x']) {
      expect(isDataCentre(asn)).toBe(false);
    }
  });

  test('the lists name their source and commit', () => {
    expect(LISTS.crawlers.source).toContain('monperrus/crawler-user-agents');
    expect(LISTS.networks.source).toContain('brianhama/bad-asn-list');
    expect(LISTS.crawlers.commit).toMatch(/^[0-9a-f]{40}$/);
    expect(LISTS.networks.commit).toMatch(/^[0-9a-f]{40}$/);
    expect(LISTS.crawlers.count).toBeGreaterThan(1000);
  });

  test('the crawler check stays well inside 10 ms of CPU', () => {
    const t0 = performance.now();
    for (let i = 0; i < 200; i++) isCrawler(CHROME + i);
    expect((performance.now() - t0) / 200).toBeLessThan(2);
  });
});

/* ------------------------------------------------------------ the code */

describe('104: the daily scrambled code', () => {
  test('one address and browser give one code under one secret, another under the next day\'s', async () => {
    const k1 = await importKey(newSecret()), k2 = await importKey(newSecret());
    const a = await dailyCode(k1, '192.0.2.1', CHROME);
    expect(a).toMatch(/^[0-9a-f]{16}$/);
    expect(await dailyCode(k1, '192.0.2.1', CHROME)).toBe(a);
    expect(await dailyCode(k1, '192.0.2.2', CHROME)).not.toBe(a);
    expect(await dailyCode(k1, '192.0.2.1', CHROME + ' x')).not.toBe(a);
    expect(await dailyCode(k2, '192.0.2.1', CHROME)).not.toBe(a);
  });

  test('a known vector: HMAC-SHA-256, the first 8 bytes', async () => {
    // RFC 4231 test case 2 has a short key; ours are 32 bytes: checked against bun's own HMAC
    const secret = '00'.repeat(31) + '01';
    const want = new Bun.CryptoHasher('sha256', Buffer.from(secret, 'hex')).update('ip\nua').digest('hex').slice(0, 16);
    expect(await dailyCode(await importKey(secret), 'ip', 'ua')).toBe(want);
  });

  test('the secret: made once a day, expiring five minutes after its day, yesterday\'s deleted', async () => {
    const today = R.dayOf(new Date());
    const k = await keyFor(env.SECRETS, today);
    expect(env.SECRETS.m.get(PREFIX + today).v).toMatch(/^[0-9a-f]{64}$/);
    expect(env.SECRETS.m.get(PREFIX + today).exp).toBe(expiry(today));
    expect(expiry('2026-10-23')).toBe(Date.parse('2026-10-24T00:05:00Z') / 1000);
    forget();
    const k2 = await keyFor(env.SECRETS, today);              // read back, not made again
    expect(await dailyCode(k2, 'a', 'b')).toBe(await dailyCode(k, 'a', 'b'));
    const yesterday = R.daysBefore(today, 1);
    env.SECRETS.m.set(PREFIX + yesterday, { v: newSecret(), exp: 0 });
    await rotate(env.SECRETS, today);
    expect(env.SECRETS.m.has(PREFIX + yesterday)).toBe(false);
    const keys = [...env.SECRETS.m.keys()].sort();
    expect(keys.length).toBe(2);                               // today's and tomorrow's
    expect(keys[0]).toBe(PREFIX + today);
    expect(keys[1]).toBe(PREFIX + R.daysBefore(today, -1));          // tomorrow's, a day ahead
  });
});

/* ------------------------------------------------------------ the endpoint */

describe('the endpoint: POST /e', () => {
  test('a view: 204, no body, CORS for ordpar.no; stored as day, minute, path, code — nothing else', async () => {
    const res = await send({ type: 'view', path: '/bm-en/5/' }, { now: new Date('2026-10-23T10:15:00Z') });
    expect(res.status).toBe(204);
    expect(await res.text()).toBe('');
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe('https://ordpar.no');
    const v = rows('SELECT * FROM views');
    expect(v.length).toBe(1);
    expect(Object.keys(v[0]).sort()).toEqual(['code', 'day', 'minute', 'path']);
    expect(v[0]).toMatchObject({ day: '2026-10-23', minute: 615, path: '/bm-en/5/' });
    expect(v[0].code).toMatch(/^[0-9a-f]{16}$/);
    // the address and the browser name are nowhere in the database
    const dump = JSON.stringify(rows("SELECT * FROM views")) + JSON.stringify(rows('SELECT * FROM searches'));
    expect(dump).not.toContain('192.0.2.1');
    expect(dump).not.toContain('Chrome');
  });

  test('search events and installs carry no code', async () => {
    await send({ type: 'hit', query: 'hus' });
    await send({ type: 'miss', query: 'vus', word: 'hus', position: 1 });
    await send({ type: 'miss', query: 'kvs', word: null, position: null });
    await send({ type: 'pick', query: 'hu', word: 'hus', position: 3 });
    await send({ type: 'install' });
    await send({ type: 'install' });
    // 148's follow-up: the English search, marked
    await send({ type: 'hit', query: 'House', lang: 'en' });
    await send({ type: 'miss', query: 'hoose', word: 'choose', position: 2, lang: 'en' });
    await send({ type: 'pick', query: 'hou', word: 'house', position: 1, lang: 'en' });
    const s = rows('SELECT kind, lang, q, word, pos FROM searches ORDER BY kind, lang, q');
    expect(s).toEqual([
      { kind: 'hit', lang: 'en', q: 'house', word: null, pos: null },
      { kind: 'hit', lang: 'nb', q: 'hus', word: null, pos: null },
      { kind: 'miss', lang: 'en', q: 'hoose', word: 'choose', pos: 2 },
      { kind: 'miss', lang: 'nb', q: 'kvs', word: null, pos: null },
      { kind: 'miss', lang: 'nb', q: 'vus', word: 'hus', pos: 1 },
      { kind: 'pick', lang: 'en', q: 'hou', word: 'house', pos: 1 },
      { kind: 'pick', lang: 'nb', q: 'hu', word: 'hus', pos: 3 },
    ]);
    expect(rows('SELECT n FROM installs')[0].n).toBe(2);
    expect(rows('SELECT count(*) AS n FROM views')[0].n).toBe(0);
    expect(env.SECRETS.m.size).toBe(0);           // no secret even read for these
  });

  test('dropped by 62\'s rule: 204, nothing stored', async () => {
    expect((await send({ type: 'hit', query: 'ring 99 88 77' })).status).toBe(204);
    expect(rows('SELECT count(*) AS n FROM searches')[0].n).toBe(0);
  });

  test('bots (layers 2 and 5): 204, nothing stored', async () => {
    expect((await send({ type: 'view', path: '/' }, { ua: 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' })).status).toBe(204);
    expect((await send({ type: 'view', path: '/' }, { asn: 16509 })).status).toBe(204);
    expect((await send({ type: 'hit', query: 'hus' }, { ua: '' })).status).toBe(204);
    expect(rows('SELECT count(*) AS n FROM views')[0].n + rows('SELECT count(*) AS n FROM searches')[0].n).toBe(0);
  });

  test('104 (R12): Sec-GPC: 1 — answered 204, nothing stored, no secret made', async () => {
    const gpc = { headers: { 'Sec-GPC': '1' } };
    expect((await send({ type: 'view', path: '/' }, gpc)).status).toBe(204);
    expect((await send({ type: 'hit', query: 'hus' }, gpc)).status).toBe(204);
    expect((await send({ type: 'pick', query: 'hu', word: 'hus', position: 1 }, gpc)).status).toBe(204);
    expect((await send({ type: 'install' }, gpc)).status).toBe(204);
    expect(rows('SELECT count(*) AS n FROM views')[0].n + rows('SELECT count(*) AS n FROM searches')[0].n
      + rows('SELECT count(*) AS n FROM installs')[0].n).toBe(0);
    expect(env.SECRETS.m.size).toBe(0);
    // any other value is no signal
    await send({ type: 'hit', query: 'hus' }, { headers: { 'Sec-GPC': '0' } });
    expect(rows('SELECT count(*) AS n FROM searches')[0].n).toBe(1);
  });

  test('104 (R11): a search is stored lower-cased', async () => {
    await send({ type: 'hit', query: 'Hus' });
    await send({ type: 'miss', query: 'VUS', word: 'Hus', position: 1 });
    expect(rows('SELECT q, word FROM searches ORDER BY q')).toEqual([{ q: 'hus', word: null }, { q: 'vus', word: 'hus' }]);
  });

  test('104 (R4): search lines keep no order of arrival — no rowid, a random key, stored in its order', async () => {
    const letters = 'abcdefghijklmnopqrstuvwxyz';
    const sent = [];
    for (let i = 0; i < 40; i++) {
      const k = (i * 17) % 40;                                           // not in sorted order either
      const q = 'q' + letters[Math.floor(k / 26)] + letters[k % 26];
      sent.push(q);
      await send({ type: 'hit', query: q });
    }
    expect(() => rows('SELECT rowid FROM searches')).toThrow();          // WITHOUT ROWID
    const got = rows('SELECT * FROM searches');                          // the table's own order
    expect(got.length).toBe(40);
    expect(got.map((r) => r.q)).not.toEqual(sent);                       // not the order they came in
    expect(got.map((r) => r.q).sort()).toEqual(sent.slice().sort());
    for (const r of got) expect(r.id).toMatch(/^[0-9a-f]{32}$/);
    expect(new Set(got.map((r) => r.id)).size).toBe(40);
    expect(got.map((r) => r.id)).toEqual(got.map((r) => r.id).slice().sort());   // ordered by the key alone
    // the columns: nothing that could hold a time of day
    expect(Object.keys(got[0]).sort()).toEqual(['day', 'id', 'kind', 'lang', 'pos', 'q', 'word']);
  });

  test('anything else: 400 with no body and no echo', async () => {
    const cases = [
      [{ type: 'view', path: '/' }, { origin: 'https://example.com' }],
      [{ type: 'view', path: '/' }, { origin: null }],
      [{ type: 'view', path: '/' }, { origin: 'http://127.0.0.1:8099' }],
      [{ type: 'view', path: '/' }, { path: '/x' }],
      [null, { method: 'GET' }],
      ['<script>alert(1)</script>', {}],
      [{ type: 'view', path: '/', pad: 'x'.repeat(600) }, {}],
      [{ type: 'unknown' }, {}],
    ];
    for (const [body, o] of cases) {
      const res = await send(body, o);
      expect(res.status).toBe(400);
      expect(await res.text()).toBe('');
    }
    expect(rows('SELECT count(*) AS n FROM views')[0].n).toBe(0);
  });

  test('a preflight from ordpar.no is answered; local test origins only with ALLOW_LOCAL', async () => {
    const res = await send(null, { method: 'OPTIONS' });
    expect(res.status).toBe(204);
    expect(res.headers.get('Access-Control-Allow-Methods')).toBe('POST');
    env.ALLOW_LOCAL = '1';
    expect((await send({ type: 'view', path: '/' }, { origin: 'http://127.0.0.1:8099' })).status).toBe(204);
  });

  test('one day: one reader, one code; the next day, a new code', async () => {
    const d1 = new Date('2026-10-23T08:00:00Z'), d2 = new Date('2026-10-24T08:00:00Z');
    await send({ type: 'view', path: '/' }, { now: d1 });
    await send({ type: 'view', path: '/about/' }, { now: d1 });
    await send({ type: 'view', path: '/' }, { now: d1, ip: '198.51.100.7' });
    await send({ type: 'view', path: '/' }, { now: d2 });
    const c = rows('SELECT day, code FROM views ORDER BY rowid');
    expect(c[0].code).toBe(c[1].code);
    expect(c[2].code).not.toBe(c[0].code);
    expect(c[3].code).not.toBe(c[0].code);
  });

  test('a body over 512 bytes is refused when it comes without a Content-Length, counted in bytes', async () => {
    // Found in the local run under wrangler dev (2026-10-23): a chunked body has no Content-Length,
    // and the text check counted characters, so 625 bytes of "ø" (325 characters) got through.
    const streamed = (text) => {
      const bytes = new TextEncoder().encode(text);
      const r = new Request('https://ordpar-receiver.example.workers.dev/e', {
        method: 'POST', duplex: 'half',
        headers: { Origin: 'https://ordpar.no', 'User-Agent': CHROME, 'CF-Connecting-IP': '192.0.2.1' },
        body: new ReadableStream({ start(c) { c.enqueue(bytes.slice(0, 100)); c.enqueue(bytes.slice(100)); c.close(); } }),
      });
      Object.defineProperty(r, 'cf', { value: { asn: 2119 } });
      return r;
    };
    const big = JSON.stringify({ type: 'view', path: '/', pad: 'ø'.repeat(300) });
    expect(big.length).toBeLessThan(R.MAX_BODY);
    expect(new TextEncoder().encode(big).length).toBeGreaterThan(R.MAX_BODY);
    pending = [];
    const res = await handle(streamed(big), env, (p) => pending.push(p));
    await Promise.all(pending);
    expect(res.status).toBe(400);
    expect(await res.text()).toBe('');
    expect(rows('SELECT count(*) AS n FROM views')[0].n).toBe(0);
    // a small streamed body is read whole and stored
    pending = [];
    const ok = await handle(streamed(JSON.stringify({ type: 'hit', query: 'ø'.repeat(40) })), env, (p) => pending.push(p));
    await Promise.all(pending);
    expect(ok.status).toBe(204);
    expect(rows('SELECT q FROM searches')[0].q).toBe('ø'.repeat(40));
  });
});

/* ------------------------------------------------------------ the daily run */

function view(day, minute, code, path = '/bm-en/1/') {
  env.DB.raw.query(`INSERT INTO views VALUES (?1, ?2, ?3, ?4)`).run(day, minute, path, code);
}
let searchKey = 0;
function search(day, kind, q, word = null, pos = null) {
  env.DB.raw.query(`INSERT INTO searches (id, day, kind, q, word, pos) VALUES (?1, ?2, ?3, ?4, ?5, ?6)`)
    .run(String(++searchKey).padStart(32, '0'), day, kind, q, word, pos);
}

describe('the daily run: totals with layer 6, retention', () => {
  test('totals for every finished day not yet totalled; today left alone', async () => {
    view('2026-10-21', 600, 'a');
    view('2026-10-22', 600, 'a'); view('2026-10-22', 601, 'a', '/'); view('2026-10-22', 900, 'b');
    view('2026-10-23', 10, 'c');
    const out = await daily(env, new Date('2026-10-23T00:05:00Z'));
    expect(out.totalled).toEqual(['2026-10-21', '2026-10-22']);
    expect(rows('SELECT * FROM daily_views ORDER BY day')).toEqual([
      { day: '2026-10-21', views: 1, readers: 1, paced_codes: 0, paced_views: 0 },
      { day: '2026-10-22', views: 3, readers: 2, paced_codes: 0, paced_views: 0 },
    ]);
    expect(rows("SELECT path, views FROM daily_paths WHERE day='2026-10-22' ORDER BY path"))
      .toEqual([{ path: '/', views: 1 }, { path: '/bm-en/1/', views: 2 }]);
    // run again the same morning: nothing to do, nothing doubled
    expect((await daily(env, new Date('2026-10-23T03:00:00Z'))).totalled).toEqual([]);
    expect(rows('SELECT count(*) AS n FROM daily_views')[0].n).toBe(2);
  });

  test('layer 6: a code at an inhuman pace is left out of the totals, its lines kept', async () => {
    const day = '2026-10-22';
    for (let i = 0; i < R.PACE_MAX; i++) view(day, 300 + Math.floor(i / 20), 'bot');   // 100 in 5 minutes
    for (let i = 0; i < R.PACE_MAX - 1; i++) view(day, 400 + Math.floor(i / 10), 'keen'); // 99 in 10 minutes
    for (let i = 0; i < 150; i++) view(day, 600 + i, 'slow');                          // 150 over 150 minutes
    view(day, 700, 'human');
    await daily(env, new Date('2026-10-23T00:05:00Z'));
    expect(rows('SELECT * FROM daily_views')[0]).toEqual(
      { day, views: 99 + 150 + 1, readers: 3, paced_codes: 1, paced_views: 100 });
    expect(rows("SELECT count(*) AS n FROM views WHERE code='bot'")[0].n).toBe(100);
    expect(rows('SELECT sum(views) AS n FROM daily_paths')[0].n).toBe(250);
  });

  test('the window slides: 100 views across two fixed 10-minute blocks still count as one burst', async () => {
    const day = '2026-10-22';
    for (let i = 0; i < 100; i++) view(day, 305 + (i % 10), 'bot');    // minutes 305–314
    await daily(env, new Date('2026-10-23T00:05:00Z'));
    expect(rows('SELECT paced_codes FROM daily_views')[0].paced_codes).toBe(1);
  });

  test('104: view lines past 1 day deleted (their totals made first, and kept); yesterday kept; searches keep 30', async () => {
    expect(R.VIEW_DAYS).toBe(1);
    expect(R.RETAIN_DAYS).toBe(30);
    const today = '2026-10-23';
    const first = R.daysBefore(today, 1);                      // 2026-10-22: kept
    view(R.daysBefore(first, 1), 600, 'old');                 // 2026-10-21: never totalled, then deleted
    view(R.daysBefore(first, 20), 600, 'older');
    view(first, 600, 'kept');
    search(R.daysBefore(first, 20), 'hit', 'hus');             // a search line of the same day stays
    const out = await daily(env, new Date(today + 'T00:05:00Z'));
    expect(out.firstView).toBe(first);
    expect(rows('SELECT day FROM views').map((r) => r.day)).toEqual([first]);
    expect(rows('SELECT day FROM daily_views ORDER BY day').map((r) => r.day))
      .toEqual([R.daysBefore(first, 20), R.daysBefore(first, 1), first]);
    expect(rows('SELECT day FROM searches').map((r) => r.day)).toEqual([R.daysBefore(first, 20)]);
  });

  test('62: search lines past 30 days become counts, only for strings seen at least 3 times', async () => {
    const today = '2026-10-23', old = '2026-07-01', recent = '2026-10-01';
    // "vus": twice past the 30 days, once within them -> seen 3 times: its old lines kept as counts
    search(old, 'miss', 'vus', 'hus', 1); search(old, 'miss', 'vus', 'hus', 1); search(recent, 'miss', 'vus');
    // "ola nordmann": twice -> dropped
    search(old, 'hit', 'ola nordmann'); search(old, 'hit', 'ola nordmann');
    // "hus": three hits past the 30 days -> kept
    search(old, 'hit', 'hus'); search(old, 'hit', 'hus'); search(old, 'hit', 'hus');
    // "hu" typed, "hus" picked: once -> dropped
    search(old, 'pick', 'hu', 'hus', 1);
    await daily(env, new Date(today + 'T00:05:00Z'));
    expect(rows('SELECT kind, q, word, pos, n FROM search_kept ORDER BY q, kind')).toEqual([
      { kind: 'hit', q: 'hus', word: '', pos: 0, n: 3 },
      { kind: 'miss', q: 'vus', word: 'hus', pos: 1, n: 2 },
    ]);
    expect(rows('SELECT day, q FROM searches')).toEqual([{ day: recent, q: 'vus' }]);
    // the recent "vus" folds later and joins the kept string, which has been seen 3 times
    await daily(env, new Date('2027-01-15T00:05:00Z'));
    expect(rows("SELECT kind, word, pos, n FROM search_kept WHERE q='vus' ORDER BY word")).toEqual([
      { kind: 'miss', word: '', pos: 0, n: 1 },
      { kind: 'miss', word: 'hus', pos: 1, n: 2 },
    ]);
    expect(rows('SELECT count(*) AS n FROM searches')[0].n).toBe(0);
  });

  test("148's follow-up: the language is not carried into the counts (the privacy page lists what a count keeps)", async () => {
    const today = '2026-10-23', old = '2026-07-01';
    env.DB.raw.query(`INSERT INTO searches (id, day, kind, lang, q) VALUES ('e1', ?1, 'hit', 'en', 'house'),
      ('e2', ?1, 'hit', 'en', 'house'), ('n1', ?1, 'hit', 'nb', 'house')`).run(old);
    await daily(env, new Date(today + 'T00:05:00Z'));
    expect(rows('SELECT * FROM search_kept')).toEqual([{ kind: 'hit', q: 'house', word: '', pos: 0, n: 3 }]);
  });

  test('the run rotates the secret', async () => {
    env.SECRETS.m.set(PREFIX + '2026-10-22', { v: newSecret(), exp: 0 });
    const now = new Date();
    await daily(env, now);
    expect(env.SECRETS.m.has(PREFIX + R.daysBefore(R.dayOf(now), 1))).toBe(false);
    expect(env.SECRETS.m.has(PREFIX + R.dayOf(now))).toBe(true);
  });
});

/* ------------------------------------------------------------ the configuration */

describe('wrangler.jsonc', () => {
  const text = readFileSync(join(ROOT, 'wrangler.jsonc'), 'utf8');
  const cfg = JSON.parse(text.replace(/^\s*\/\/.*$/gm, ''));
  test('Workers Logs off (104\'s box, item 3), no Logpush, no traces', () => {
    expect(cfg.observability.enabled).toBe(false);
    expect(cfg.observability.logs.enabled).toBe(false);
    expect(cfg.observability.logs.invocation_logs).toBe(false);
    expect(cfg.observability.traces.enabled).toBe(false);
    expect(cfg.logpush).toBe(false);
  });
  test('one daily Cron Trigger, local origins off, D1 bound; KV (the daily secret) waiting in a comment while the counting is off (166)', () => {
    expect(cfg.triggers.crons).toEqual(['5 0 * * *']);
    expect(cfg.vars.ALLOW_LOCAL).toBe('0');
    expect(cfg.d1_databases[0].binding).toBe('DB');
    expect(cfg.kv_namespaces).toBe(undefined);           // put back before COUNTING "1" (README)
    expect(text).toMatch(/"binding": "SECRETS"/);
    expect(cfg.workers_dev).toBe(true);
  });
  test('the Worker never logs', () => {
    for (const f of ['worker.js', 'rules.js', 'bots.js', 'code.js', 'secret.js', 'sql.js']) {
      expect(readFileSync(join(ROOT, 'src', f), 'utf8')).not.toMatch(/console\./);
    }
  });
});
