// A LOCAL STAND-IN for the receiver (site decisions 166): the Worker's own code (`src/worker.js`
// `handle`) served by bun on 127.0.0.1, with D1 stood in for by bun:sqlite (every migration, the
// same SQL strings, as the tests) and KV by a Map — since `wrangler dev` cannot answer under bun
// (README § Wrangler under bun). Not Cloudflare: no workerd, no request.cf, no CF-Connecting-IP.
// For the browser tests of "Report a mistake" and of the survey (site decisions 173: POST /survey,
// GET /surveys), and for trying Robin's /reports page before the Worker is deployed.
//
//   bun tools/local.mjs [--port 8787] [--db <file.sqlite>] [--counting] [--lan [--host <addr>]] [--stay]
//
// ALLOW_LOCAL is on (pages on http://127.0.0.1:<port> may send); COUNTING off unless --counting;
// the token for GET /reports is the environment's REPORTS_TOKEN, or "local-reports-token-0000"
// when unset. Prints "listening http://<host>:<port>" as its first line, once it answers. Stops on
// Ctrl-C or when its standard input closes (so a test that starts it never leaves it running);
// with --stay, only on Ctrl-C or when killed (a run in the background, whose standard input is
// closed from the start).
//
// --lan, THE LOCAL NETWORK (site decisions 166: a look at the form on :8098 from this
// computer and from a phone on the same network; README § A look build): it answers on every interface (0.0.0.0, or
// --host), and a report is taken from LAN_ORIGINS only — the look build served on :8098 as this
// computer opens it and as the phone does — never from any other origin, 127.0.0.1's other ports
// included. The Worker's own origin rule is untouched: such a request reaches `handle` as from
// http://127.0.0.1:8098, and its answer goes back with the page's own origin. GET /reports and
// /reports/<id>/done, and the survey's GET /surveys and /surveys/<id>/done (173), answer this
// computer only (as serve.py's /reports page), whatever the token; survey answers are taken from
// LAN_ORIGINS only, as reports.
// Without --lan nothing changes: 127.0.0.1 only.
import { Database } from 'bun:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { handle } from '../src/worker.js';

const ROOT = join(import.meta.dir, '..');
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const LAN = args.includes('--lan');
/** --lan: the pages that may send a report — the look build on :8098, as this computer and as the
 *  phone open it (on the local network, this computer's address is 192.168.0.100). */
const LAN_ORIGINS = ['http://127.0.0.1:8098', 'http://192.168.0.100:8098'];
/** What a LAN origin is passed to the Worker's `handle` as (ALLOW_LOCAL accepts it). */
const AS_LOCAL = 'http://127.0.0.1:8098';
const LOOPBACK = /^(127\.\d+\.\d+\.\d+|::1|::ffff:127\.\d+\.\d+\.\d+)$/;

const db = new Database(opt('--db', ':memory:'));
for (const f of readdirSync(join(ROOT, 'migrations')).filter((n) => n.endsWith('.sql')).sort()) {
  db.exec(readFileSync(join(ROOT, 'migrations', f), 'utf8'));
}
const prepare = (sql) => {
  const st = { sql, args: [] };
  st.bind = (...a) => { st.args = a; return st; };
  st.run = async () => { db.query(sql).run(...st.args); return { success: true }; };
  st.all = async () => ({ results: db.query(sql).all(...st.args) });
  st.first = async () => db.query(sql).get(...st.args);
  return st;
};
const DB = {
  prepare,
  batch: async (stmts) => { db.transaction(() => stmts.forEach((s) => db.query(s.sql).run(...s.args)))(); },
};
const kvMap = new Map();
const SECRETS = {
  get: async (k) => (kvMap.has(k) ? kvMap.get(k) : null),
  put: async (k, v) => { kvMap.set(k, v); },
  delete: async (k) => { kvMap.delete(k); },
};
const env = {
  DB, SECRETS, ALLOW_LOCAL: '1', COUNTING: args.includes('--counting') ? '1' : '0',
  REPORTS_TOKEN: process.env.REPORTS_TOKEN || 'local-reports-token-0000',
};

async function run(request) {
  const pending = [];
  const res = await handle(request, env, (p) => pending.push(p));
  await Promise.all(pending);
  return res;
}

/** Robin's read paths: the reports' and the survey's (site decisions 173). */
const ROBINS = /^\/(reports|surveys)(\/|$)/;

/** --lan: the origin rule above, and Robin's read paths for this computer only. */
async function lan(request, server) {
  const url = new URL(request.url);
  if (ROBINS.test(url.pathname)) {
    const ip = (server.requestIP(request) || {}).address || '';
    if (!LOOPBACK.test(ip)) return new Response(null, { status: 403 });
    return run(request);
  }
  const origin = request.headers.get('Origin');
  if (origin === null) return run(request);                   // the Worker refuses a report without one
  if (!LAN_ORIGINS.includes(origin)) return new Response(null, { status: 400, headers: { Vary: 'Origin' } });
  const headers = new Headers(request.headers);
  headers.set('Origin', AS_LOCAL);
  const body = request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer();
  const res = await run(new Request(request.url, { method: request.method, headers, body }));
  const out = new Headers(res.headers);
  if (out.has('Access-Control-Allow-Origin')) out.set('Access-Control-Allow-Origin', origin);
  return new Response(res.body, { status: res.status, headers: out });
}

const server = Bun.serve({
  hostname: LAN ? opt('--host', '0.0.0.0') : '127.0.0.1',
  port: Number(opt('--port', 8787)),
  fetch(request, srv) {
    return LAN ? lan(request, srv) : run(request);
  },
});
process.stdout.write('listening http://' + server.hostname + ':' + server.port + '\n');
if (LAN) {
  process.stdout.write('home network: reports and survey answers from ' + LAN_ORIGINS.join(' and ') +
                       ' only; /reports and /surveys from this computer only\n');
}

// stop when the parent closes our standard input (a test's subprocess pipe), or on Ctrl-C
// (--stay: not on standard input's end)
if (!args.includes('--stay')) {
  process.stdin.on('end', () => { server.stop(true); process.exit(0); });
  process.stdin.on('error', () => {});
  process.stdin.resume();
}
process.on('SIGINT', () => { server.stop(true); process.exit(0); });
