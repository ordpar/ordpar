// The Ordpar event receiver: a Cloudflare Worker on its workers.dev address (site decisions 26),
// taking page views with the daily scrambled code (104), offline-app installs (104) and the
// search events (62). One endpoint, POST /e, one small JSON event per request. A request that
// carries `Sec-GPC: 1` is answered and nothing kept (104, R12).
//
// THE COUNTING'S SWITCH (site decisions 166, 2026-11-05): the Worker variable COUNTING
// (wrangler.jsonc `vars`). Not "1", as configured: `/e` is not served (400, as any unknown path,
// nothing stored) and the daily run makes no totals, so the Worker can be deployed for the
// reports while the counting stays off (104, 166). "1" turns it on.
//
// "Report a mistake" (site decisions 166): POST /report, from the page's report.js, stored in D1
// (`reports`), with a hidden trap field and a cap on the reports accepted per hour in total
// (nothing about the sender read: Robin, 2026-11-05, "Yes, drop it"); GET /reports and
// POST /reports/<id>/done, for Robin, behind the Worker secret REPORTS_TOKEN. Rules: reports.js.
// Reports use D1 only: no KV, so the Worker can go live for them without the counting's secret.
//
// The readers' survey (site decisions 173, 2026-11-07): POST /survey, from the page /survey/
// (`ordpar/site/survey.js`), a second kind beside reports under the same rules — the same origins,
// the trap, nothing about the sender read, and the SAME total cap (one count per hour for reports
// and answers together); GET /surveys and POST /surveys/<id>/done for Robin, behind the same token.
// Rules: survey.js.
//
// It never logs: no console call anywhere, and Workers Logs are off in wrangler.jsonc. Nothing
// here stores or logs the address or the browser name; for the counting (`/e`) they enter the
// daily code's hash and the two bot checks, and nothing else; for a report, nothing at all.
// What is stored and for how long: ordpar/docs/receiver.md.
import { allowedOrigin, dayOf, minuteOf, daysBefore, parseEvent, MAX_BODY, RETAIN_DAYS, VIEW_DAYS } from './rules.js';
import { isCrawler, isDataCentre } from './bots.js';
import { dailyCode } from './code.js';
import { keyFor, rotate, PREFIX } from './secret.js';
import { parseReport, authorised, hourOf, MAX_REPORT_BODY, REPORTS_PER_HOUR, LIST_MAX } from './reports.js';
import { parseSurvey, MAX_SURVEY_BODY } from './survey.js';
import * as SQL from './sql.js';

function cors(origin) {
  return origin ? { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } : { Vary: 'Origin' };
}

/** 400, no body: never an echo of what was sent. */
function bad(origin) {
  return new Response(null, { status: 400, headers: cors(origin) });
}

function done(origin) {
  return new Response(null, { status: 204, headers: cors(origin) });
}

function answer(status, origin) {
  return new Response(null, { status, headers: cors(origin) });
}

function preflight(origin) {
  return new Response(null, {
    status: 204,
    headers: Object.assign(cors(origin), {
      'Access-Control-Allow-Methods': 'POST',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
    }),
  });
}

/** Layers 2 and 5 (104): a crawler's browser name (or none), or a data-centre network. */
export function fromBot(request) {
  return isCrawler(request.headers.get('User-Agent')) || isDataCentre(request.cf && request.cf.asn);
}

/** The reader asked not to be counted (Global Privacy Control, `Sec-GPC: 1`): the page's
 *  events.js sends nothing then already; this is the receiver's own check (104, R12). */
export function optedOut(request) {
  return request.headers.get('Sec-GPC') === '1';
}

/** 32 random hex digits: a search line's key, so `searches` keeps no order of arrival (104, R4). */
export function randomKey() {
  const b = crypto.getRandomValues(new Uint8Array(16));
  let s = '';
  for (const x of b) s += (x < 16 ? '0' : '') + x.toString(16);
  return s;
}

/** Store one event received at `now`. */
export async function store(env, event, request, now) {
  const day = dayOf(now);
  if (event.type === 'view') {
    const key = await keyFor(env.SECRETS, day);
    const code = await dailyCode(key, request.headers.get('CF-Connecting-IP') || '',
      request.headers.get('User-Agent') || '');
    await env.DB.prepare(SQL.INSERT_VIEW).bind(day, minuteOf(now), event.path, code).run();
  } else if (event.type === 'install') {
    await env.DB.prepare(SQL.INSERT_INSTALL).bind(day).run();
  } else {
    await env.DB.prepare(SQL.INSERT_SEARCH)
      .bind(randomKey(), day, event.type, event.lang || 'nb', event.query, event.word ?? null,
        event.position ?? null).run();
  }
}

/** The body as text, or null when it is over `max` bytes: read no further than that. Bytes, not
 *  characters, and whether or not a Content-Length came with it (a chunked body has none). */
export async function readBody(request, max = MAX_BODY) {
  if (!request.body) return '';
  const reader = request.body.getReader();
  const parts = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > max) {
      reader.cancel().catch(() => {});
      return null;
    }
    parts.push(value);
  }
  const all = new Uint8Array(size);
  let at = 0;
  for (const p of parts) { all.set(p, at); at += p.byteLength; }
  return new TextDecoder().decode(all);
}

/** Is the counting on? Only with the Worker variable COUNTING = "1" (site decisions 166). */
export function counting(env) {
  return !!env && env.COUNTING === '1';
}

/** One more report or set of survey answers this hour, from anyone: is it within REPORTS_PER_HOUR?
 *  One count per UTC hour (`report_hours`) for both kinds together (site decisions 173), nothing
 *  about the sender; the counts of earlier hours are deleted first. */
async function withinCap(env, now) {
  const hour = hourOf(now);
  await env.DB.prepare(SQL.CLEAR_HOURS).bind(hour).run();
  const row = await env.DB.prepare(SQL.COUNT_HOUR).bind(hour).first();
  return !!row && row.n <= REPORTS_PER_HOUR;
}

/** A message the reader sends (a report, or the survey's answers): from https://ordpar.no only, as
 *  /e. 204 once stored (or when the trap was filled: dropped, nothing stored); 400 when it is not
 *  one; 429 over the total cap for the hour (reports and answers counted together); 503 when it could
 *  not be stored. The answer waits for the write, so the reader's "sent" is true. Reads no header
 *  but Origin and Content-Length. `parse` gives {status, row}; `insert` stores the row. */
async function takeMessage(request, env, now, maxBody, parse, insert) {
  const origin = request.headers.get('Origin');
  if (!allowedOrigin(origin, env.ALLOW_LOCAL === '1')) return bad(null);
  if (request.method === 'OPTIONS') return preflight(origin);
  if (request.method !== 'POST') return bad(origin);
  const length = Number(request.headers.get('Content-Length') || 0);
  if (length > maxBody) return bad(origin);
  const text = await readBody(request, maxBody);
  if (text === null) return bad(origin);
  const got = parse(text);
  if (got.status === 'bad') return bad(origin);
  if (got.status === 'drop') return done(origin);
  try {
    if (!(await withinCap(env, now))) return answer(429, origin);
    await insert(got.row);
  } catch (e) {
    return answer(503, origin);
  }
  return done(origin);
}

/** POST /report (site decisions 166): a report, `parseReport`'s rules. */
export async function handleReport(request, env, now) {
  return takeMessage(request, env, now, MAX_REPORT_BODY, (text) => {
    const got = parseReport(text);
    return { status: got.status, row: got.report };
  }, (r) => env.DB.prepare(SQL.INSERT_REPORT)
    .bind(dayOf(now), r.article, r.build, r.category, r.text, r.reply, r.credit).run());
}

/** POST /survey (site decisions 173): the survey's answers, `parseSurvey`'s rules, under the same
 *  cap as reports. */
export async function handleSurvey(request, env, now) {
  return takeMessage(request, env, now, MAX_SURVEY_BODY, (text) => {
    const got = parseSurvey(text);
    return { status: got.status, row: got.survey };
  }, (r) => env.DB.prepare(SQL.INSERT_SURVEY).bind(dayOf(now), r.answers, r.follow).run());
}

/** Robin's two (site decisions 166), behind the Worker secret REPORTS_TOKEN ("Authorization:
 *  Bearer <token>"): GET /reports, the open reports newest first as JSON; POST
 *  /reports/<id>/done, the report closed (Done or Fixed on Robin's page) and its reply address and
 *  name to credit deleted (204; 404 when there is no open report of that id). 401 without the
 *  token. No CORS: a browser page cannot read them. */
export async function handleReports(request, env, now) {
  if (!authorised(request.headers.get('Authorization'), env.REPORTS_TOKEN)) {
    return new Response(null, { status: 401 });
  }
  const path = new URL(request.url).pathname;
  if (path === '/reports' && request.method === 'GET') {
    const rows = (await env.DB.prepare(SQL.OPEN_REPORTS).bind(LIST_MAX).all()).results || [];
    return new Response(JSON.stringify({ reports: rows }), {
      status: 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }
  const m = /^\/reports\/(\d{1,12})\/done$/.exec(path);
  if (m && request.method === 'POST') {
    const row = await env.DB.prepare(SQL.REPORT_DONE).bind(Number(m[1]), dayOf(now)).first();
    return new Response(null, { status: row ? 204 : 404 });
  }
  return new Response(null, { status: 404 });
}

/** Robin's two for the survey (site decisions 173), behind the same token as reports: GET /surveys,
 *  the open answers newest first as JSON (each `answers` the object the reader's page sent, cleaned);
 *  POST /surveys/<id>/done, the answers marked done and their follow-up address or name deleted
 *  (204; 404 when there are no open answers of that id). 401 without the token. No CORS. */
export async function handleSurveys(request, env, now) {
  if (!authorised(request.headers.get('Authorization'), env.REPORTS_TOKEN)) {
    return new Response(null, { status: 401 });
  }
  const path = new URL(request.url).pathname;
  if (path === '/surveys' && request.method === 'GET') {
    const rows = (await env.DB.prepare(SQL.OPEN_SURVEYS).bind(LIST_MAX).all()).results || [];
    const surveys = rows.map((r) => {
      let answers;
      try { answers = JSON.parse(r.answers); } catch (e) { answers = {}; }
      return { id: r.id, day: r.day, answers, follow: r.follow };
    });
    return new Response(JSON.stringify({ surveys }), {
      status: 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }
  const m = /^\/surveys\/(\d{1,12})\/done$/.exec(path);
  if (m && request.method === 'POST') {
    const row = await env.DB.prepare(SQL.SURVEY_DONE).bind(Number(m[1]), dayOf(now)).first();
    return new Response(null, { status: row ? 204 : 404 });
  }
  return new Response(null, { status: 404 });
}

/** The answer to one request; `waitUntil` takes the write, so the answer does not wait for it. */
export async function handle(request, env, waitUntil, now) {
  const origin = request.headers.get('Origin');
  const url = new URL(request.url);
  if (url.pathname === '/report') return handleReport(request, env, now || new Date());
  if (url.pathname === '/survey') return handleSurvey(request, env, now || new Date());
  if (url.pathname === '/surveys' || url.pathname.startsWith('/surveys/')) {
    return handleSurveys(request, env, now || new Date());
  }
  if (url.pathname === '/reports' || url.pathname.startsWith('/reports/')) {
    return handleReports(request, env, now || new Date());
  }
  if (url.pathname !== '/e' || !counting(env) || !allowedOrigin(origin, env.ALLOW_LOCAL === '1')) return bad(null);
  if (request.method === 'OPTIONS') return preflight(origin);
  if (request.method !== 'POST') return bad(origin);
  const length = Number(request.headers.get('Content-Length') || 0);
  if (length > MAX_BODY) return bad(origin);
  const text = await readBody(request);
  if (text === null) return bad(origin);
  const got = parseEvent(text);
  if (got.status === 'bad') return bad(origin);
  if (got.status === 'ok' && !fromBot(request) && !optedOut(request)) {
    waitUntil(store(env, got.event, request, now || new Date()).catch(() => {}));
  }
  return done(origin);
}

/** The daily run (Cron Trigger, 00:05 UTC): the reports' counts of past hours deleted; with the
 *  counting on (COUNTING = "1"), also: rotate the secret; total every finished day not yet
 *  totalled, the pace rule applied; then delete the view lines past VIEW_DAYS, and fold and
 *  delete the search lines past RETAIN_DAYS. */
export async function daily(env, now) {
  const today = dayOf(now);
  // the total cap's counts of past hours (site decisions 166), whether or not the counting is on
  await env.DB.prepare(SQL.CLEAR_HOURS).bind(hourOf(now)).run();
  if (!counting(env)) {
    // the counting off: no totals, no secret made or read (reports use none; KV may not even be
    // bound, wrangler.jsonc). A secret left from a time the counting was on expires by itself
    // (secret.js), and is deleted here too when KV is bound.
    if (env.SECRETS) await env.SECRETS.delete(PREFIX + daysBefore(today, 1));
    return { today, counting: false, totalled: [] };
  }
  await rotate(env.SECRETS, today);
  const rows = (await env.DB.prepare(SQL.DAYS_TO_TOTAL).bind(today).all()).results || [];
  const days = rows.map((r) => r.day);
  for (const day of days) {
    await env.DB.batch([
      env.DB.prepare(SQL.TOTAL_DAY).bind(day),
      env.DB.prepare(SQL.CLEAR_PATHS).bind(day),
      env.DB.prepare(SQL.TOTAL_PATHS).bind(day),
    ]);
  }
  const first = daysBefore(today, RETAIN_DAYS);        // the first day whose search lines are kept
  const firstView = daysBefore(today, VIEW_DAYS);      // ... and whose view lines are
  await env.DB.batch([
    env.DB.prepare(SQL.FOLD_SEARCHES).bind(first),
    env.DB.prepare(SQL.DELETE_SEARCHES).bind(first),
    env.DB.prepare(SQL.DELETE_VIEWS).bind(firstView),
  ]);
  return { today, totalled: days, first, firstView };
}

export default {
  fetch(request, env, ctx) {
    return handle(request, env, (p) => ctx.waitUntil(p));
  },
  scheduled(controller, env, ctx) {
    ctx.waitUntil(daily(env, new Date(controller.scheduledTime)));
  },
};
