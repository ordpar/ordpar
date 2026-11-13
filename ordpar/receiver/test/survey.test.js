// The readers' survey (site decisions 173, 2026-11-07) on the receiver, under bun with no network:
// POST /survey, a second kind beside reports — the same origins, the trap, nothing about the sender
// read, and the SAME total cap (reports and answers counted together); Robin's GET /surveys and
// POST /surveys/<id>/done (the follow-up address or name deleted, the answers kept); and the page's
// limits held to the receiver's (ordpar/site/survey.js, ordpar/site/survey.json). Run by
// ordpar/tests/test_ordpar_receiver104.py, or here with `bun test`. D1 is stood in for by
// bun:sqlite running every migration and the same SQL strings.
import { describe, expect, test, beforeEach, setSystemTime } from 'bun:test';
import { Database } from 'bun:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import * as S from '../src/survey.js';
import { REPORTS_PER_HOUR } from '../src/reports.js';
import { handle, daily } from '../src/worker.js';

setSystemTime(new Date('2026-11-07T12:00:00Z'));

const ROOT = join(import.meta.dir, '..');
const SITE = join(ROOT, '..', 'site');
const TOKEN = 'a-test-token-of-some-length-0123456789';
const NOW = new Date('2026-11-07T12:10:00Z');

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
const count = (t) => rows('SELECT count(*) AS n FROM ' + t)[0].n;
const GOOD = {
  answers: {
    level: 'I can read simple texts', first_language: 'Polish',
    looked_up: 'I searched for hus and found it.', ideas: ['Example sentences for the words and meanings that don\'t have any yet', 'Use Ordpar as the dictionary on your e-reader (Kindle, Kobo) when reading Norwegian books'],
    devices: ['Phone'], anything_else: 'Thanks!',
  },
  follow: 'reader@example.org',
};
const REPORT = { id: 1234, build: null, category: null, text: 'A report.', reply: null };

beforeEach(() => { env = { DB: d1(), ALLOW_LOCAL: '0', REPORTS_TOKEN: TOKEN }; });

describe('parseSurvey: what a set of answers may carry', () => {
  test('the answers and the follow-up, exactly; any other field ignored', () => {
    const got = S.parseSurvey(JSON.stringify(Object.assign({ path: '/x', id: 5, ua: 'y', build: 'abc123' }, GOOD)));
    expect(got.status).toBe('ok');
    expect(Object.keys(got.survey)).toEqual(['answers', 'follow']);
    expect(JSON.parse(got.survey.answers)).toEqual(GOOD.answers);
    expect(got.survey.follow).toBe('reader@example.org');
  });
  test('cleaned: NFC, trimmed, empty answers left out, choices once each; a name as follow-up', () => {
    const got = S.parseSurvey(JSON.stringify({ answers: { a: '  Áse\u0007 ', b: '', c: [], d: [' x ', 'x', 'y  z'], e: null },
      follow: '  Kari \n Nordmann ' }));
    expect(JSON.parse(got.survey.answers)).toEqual({ a: 'Áse', d: ['x', 'y z'] });
    expect(got.survey.follow).toBe('Kari Nordmann');
    const lines = S.parseSurvey(JSON.stringify({ answers: { a: 'one\ntwo' } }));
    expect(JSON.parse(lines.survey.answers).a).toBe('one\ntwo');                   // line breaks kept
    expect(lines.survey.follow).toBe(null);
  });
  test('the follow-up alone, or answers alone, is a survey; neither is not', () => {
    expect(S.parseSurvey(JSON.stringify({ answers: {}, follow: 'x@example.org' })).status).toBe('ok');
    expect(S.parseSurvey(JSON.stringify({ answers: { a: 'x' }, follow: null })).status).toBe('ok');
    expect(S.parseSurvey(JSON.stringify({ answers: { a: '  ' }, follow: ' ' })).status).toBe('bad');
  });
  test('the limits', () => {
    expect([S.MAX_ANSWER, S.MAX_CHOICES, S.MAX_CHOICE, S.MAX_QUESTIONS, S.MAX_FOLLOW]).toEqual([2000, 20, 300, 40, 254]);
    const ok = (o) => S.parseSurvey(JSON.stringify(o)).status;
    expect(ok({ answers: { a: 'x'.repeat(2000) } })).toBe('ok');
    expect(ok({ answers: { a: 'x'.repeat(2001) } })).toBe('bad');
    expect(ok({ answers: { a: Array.from({ length: 20 }, (_, i) => 'c' + i) } })).toBe('ok');
    expect(ok({ answers: { a: Array.from({ length: 21 }, (_, i) => 'c' + i) } })).toBe('bad');
    expect(ok({ answers: { a: ['x'.repeat(300)] } })).toBe('ok');
    expect(ok({ answers: { a: ['x'.repeat(301)] } })).toBe('bad');
    const many = {};
    for (let i = 0; i < 41; i++) many['q' + i] = 'x';
    expect(ok({ answers: many })).toBe('bad');
    expect(ok({ answers: { a: 'x' }, follow: 'x'.repeat(254) })).toBe('ok');
    expect(ok({ answers: { a: 'x' }, follow: 'x'.repeat(255) })).toBe('bad');
  });
  test('not a survey: 400', () => {
    const bad = ['', 'not json', '[]', 'null', '{}', { answers: [] }, { answers: 'x' },
      { answers: { 'Bad Key': 'x' } }, { answers: { '1a': 'x' } }, { answers: { a: 5 } }, { answers: { a: { b: 'c' } } },
      { answers: { a: [5] } }, { answers: { a: 'x' }, follow: 5 }, { answers: { a: 'x' }, follow: ['x'] }];
    for (const b of bad) expect([b, S.parseSurvey(typeof b === 'string' ? b : JSON.stringify(b)).status]).toEqual([b, 'bad']);
  });
  test('the trap filled: dropped', () => {
    expect(S.parseSurvey(JSON.stringify(Object.assign({ hp: 'http://spam.example' }, GOOD))).status).toBe('drop');
    expect(S.parseSurvey(JSON.stringify(Object.assign({ hp: '' }, GOOD))).status).toBe('ok');
  });
});

describe('POST /survey', () => {
  test('204 with CORS for ordpar.no, stored as day, answers and follow-up', async () => {
    const res = await call('/survey', { body: GOOD });
    expect(res.status).toBe(204);
    expect(await res.text()).toBe('');
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe('https://ordpar.no');
    const got = rows('SELECT * FROM surveys');
    expect(got.length).toBe(1);
    expect(Object.keys(got[0])).toEqual(['id', 'day', 'answers', 'follow', 'done']);
    expect([got[0].day, got[0].follow, got[0].done]).toEqual(['2026-11-07', 'reader@example.org', null]);
    expect(JSON.parse(got[0].answers)).toEqual(GOOD.answers);
    expect(count('reports')).toBe(0);
  });
  test('nothing about the sender is read or stored: no address, no browser name, no KV', async () => {
    const asked = [];
    const r = request('/survey', { body: GOOD });
    const get = r.headers.get.bind(r.headers);
    r.headers.get = (name) => { asked.push(name.toLowerCase()); return get(name); };
    expect((await handle(r, env, (p) => p, NOW)).status).toBe(204);
    expect([...new Set(asked)].sort()).toEqual(['content-length', 'origin']);
    const tables = rows("SELECT name FROM sqlite_master WHERE type='table'").map((x) => x.name);
    const dump = JSON.stringify(tables.map((t) => rows('SELECT * FROM ' + t)));
    for (const s of [IP, CHROME, 'Edg/141', 'ordpar.no']) expect([s, dump.includes(s)]).toEqual([s, false]);
    const src = readFileSync(join(ROOT, 'src', 'survey.js'), 'utf8');
    expect(src).not.toMatch(/CF-Connecting-IP|User-Agent|crypto\.subtle|console\./);
    const w = readFileSync(join(ROOT, 'src', 'worker.js'), 'utf8');
    const part = w.slice(w.indexOf('export async function handleSurvey('), w.indexOf('/** Robin\'s two (site decisions 166)'));
    expect(part.length).toBeGreaterThan(50);
    for (const word of ['CF-Connecting-IP', 'User-Agent', 'SECRETS', 'request.cf']) expect([word, part.includes(word)]).toEqual([word, false]);
  });
  test('another origin, another method, a body too large: 400, nothing stored', async () => {
    for (const origin of ['https://evil.example', 'http://ordpar.no', null]) {
      expect((await call('/survey', { body: GOOD, origin })).status).toBe(400);
    }
    expect((await call('/survey', { method: 'GET' })).status).toBe(400);
    const big = JSON.stringify(Object.assign({}, GOOD, { pad: 'ø'.repeat(S.MAX_SURVEY_BODY) }));
    expect((await call('/survey', { body: big })).status).toBe(400);
    expect(count('surveys')).toBe(0);
    expect((await call('/survey', { method: 'OPTIONS' })).status).toBe(204);
  });
  test('the trap filled: 204, nothing stored, not counted toward the cap', async () => {
    expect((await call('/survey', { body: Object.assign({ hp: 'x' }, GOOD) })).status).toBe(204);
    expect(count('surveys')).toBe(0);
    expect(count('report_hours')).toBe(0);
  });
  test('the SAME total cap as reports: reports and answers counted together, then 429 for both', async () => {
    expect(REPORTS_PER_HOUR).toBe(30);
    for (let i = 0; i < 15; i++) {
      expect((await call('/report', { body: REPORT, ip: '203.0.113.' + i })).status).toBe(204);
      expect((await call('/survey', { body: GOOD, ip: '203.0.114.' + i })).status).toBe(204);
    }
    expect(rows('SELECT * FROM report_hours')).toEqual([{ hour: '2026-11-07T12', n: 30 }]);
    const a = await call('/survey', { body: GOOD, ip: '192.0.2.1' });
    expect(a.status).toBe(429);
    expect(a.headers.get('Access-Control-Allow-Origin')).toBe('https://ordpar.no');
    expect((await call('/report', { body: REPORT, ip: '192.0.2.2' })).status).toBe(429);
    expect([count('reports'), count('surveys')]).toEqual([15, 15]);
    expect((await call('/survey', { body: GOOD, now: new Date('2026-11-07T13:00:10Z') })).status).toBe(204);
    expect(rows('SELECT * FROM report_hours')).toEqual([{ hour: '2026-11-07T13', n: 1 }]);
  });
  test('a store that fails answers 503', async () => {
    env.DB.raw.exec('DROP TABLE surveys');
    expect((await call('/survey', { body: GOOD })).status).toBe(503);
  });
});

describe('GET /surveys and POST /surveys/<id>/done: Robin\'s, behind the token', () => {
  async function two() {
    await call('/survey', { body: GOOD });
    await call('/survey', { body: { answers: { level: 'Fluent' }, follow: null } });
  }
  test('without the token or with a wrong one: 401', async () => {
    await two();
    for (const o of [{}, { token: 'wrong-token-of-some-length-0000' }]) {
      expect((await call('/surveys', o)).status).toBe(401);
      expect((await call('/surveys/1/done', Object.assign({ method: 'POST' }, o))).status).toBe(401);
    }
    expect(rows('SELECT follow FROM surveys WHERE id = 1')[0].follow).toBe('reader@example.org');
  });
  test('with the token: the open answers, newest first, the answers as an object, no CORS', async () => {
    await two();
    const res = await call('/surveys', { token: TOKEN, origin: null });
    expect(res.status).toBe(200);
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe(null);
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    const got = (await res.json()).surveys;
    expect(got.map((s) => s.id)).toEqual([2, 1]);
    expect(got[1]).toEqual({ id: 1, day: '2026-11-07', answers: GOOD.answers, follow: 'reader@example.org' });
    expect(got[0].follow).toBe(null);
    // reports' own list is untouched by the survey
    expect((await (await call('/reports', { token: TOKEN })).json()).reports).toEqual([]);
  });
  test('done: the follow-up address or name deleted, the answers and the day kept; no longer listed', async () => {
    await two();
    expect((await call('/surveys/1/done', { method: 'POST', token: TOKEN })).status).toBe(204);
    const row = rows('SELECT * FROM surveys WHERE id = 1')[0];
    expect([row.follow, row.done, row.day]).toEqual([null, '2026-11-07', '2026-11-07']);
    expect(JSON.parse(row.answers)).toEqual(GOOD.answers);
    expect(JSON.stringify(rows('SELECT * FROM surveys'))).not.toContain('reader@example.org');
    expect((await (await call('/surveys', { token: TOKEN })).json()).surveys.map((s) => s.id)).toEqual([2]);
    expect((await call('/surveys/1/done', { method: 'POST', token: TOKEN })).status).toBe(404);
    expect((await call('/surveys/77/done', { method: 'POST', token: TOKEN })).status).toBe(404);
    expect((await call('/surveys/2/done', { token: TOKEN })).status).toBe(404);          // GET on done
    // a report's done does not touch the answers, nor the other way round
    expect((await call('/reports/2/done', { method: 'POST', token: TOKEN })).status).toBe(404);
    expect(count('surveys')).toBe(2);
  });
  test('the daily run leaves the answers alone', async () => {
    await two();
    await daily(env, new Date('2026-11-08T00:05:00Z'));
    expect(count('surveys')).toBe(2);
  });
});

describe('the page\'s limits are the receiver\'s (ordpar/site/survey.js and survey.json)', () => {
  const page = readFileSync(join(SITE, 'survey.js'), 'utf8');
  const data = JSON.parse(readFileSync(join(SITE, 'survey.json'), 'utf8'));
  test('survey.js: the same constants, the switch empty as committed', () => {
    expect(page).toContain('var MAX_ANSWER = ' + S.MAX_ANSWER + ';');
    expect(page).toContain('var MAX_CHOICE = ' + S.MAX_CHOICE + ';');
    expect(page).toContain('var MAX_FOLLOW = ' + S.MAX_FOLLOW + ';');
    expect(page).toContain("var SURVEY_RECEIVER = '';");
    expect(page).not.toMatch(/console\./);
  });
  test('survey.json: each question\'s key, limit and choices within the receiver\'s', () => {
    const qs = data.questions;
    expect(qs.length).toBeLessThanOrEqual(S.MAX_QUESTIONS);
    let worst = 0;
    for (const q of qs) {
      expect([q.id, S.KEY.test(q.id)]).toEqual([q.id, true]);
      if (q.kind === 'follow') { expect(q.max).toBe(S.MAX_FOLLOW); worst += q.max; continue; }
      if (q.choices) {
        expect(q.choices.length).toBeLessThanOrEqual(S.MAX_CHOICES);
        for (const c of q.choices) expect(c.length).toBeLessThanOrEqual(S.MAX_CHOICE);
        worst += q.choices.reduce((n, c) => n + c.length + 3, 0);
      } else {
        expect([q.id, q.max >= 1 && q.max <= S.MAX_ANSWER]).toEqual([q.id, true]);
        worst += q.max;
      }
    }
    // every answer at its longest, each character 6 bytes as JSON, and room for the keys
    expect(worst * 6 + 4096).toBeLessThan(S.MAX_SURVEY_BODY);
  });
});
