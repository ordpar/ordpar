// The Ordpar audio Worker: serves the pronunciation clips from the private R2 bucket
// `ordpar-audio` on its workers.dev address (audio decisions 12, 15; the site's 159). It answers
// GET and HEAD of /ordpar-<16 lower-case hex>.mp3 and nothing else: the name is checked before R2
// is touched, so a bad path, a listing or a key with a slash costs no bucket operation, and the
// bucket is never listed. Range requests (Safari asks for media in ranges) get a 206; the clip's
// own headers (audio/mpeg, a year's immutable cache) are passed on.
//
// A superseded name (a clip since fixed, its name still in a shared deck) is answered with a 302 to
// the clip that replaced it, from the bundled table src/forwarding.json, before R2 is touched
// (site decisions 179; audio decisions 26).
//
// It never logs (no console call; Workers Logs, traces and Logpush off in wrangler.jsonc), stores
// nothing and reads no cookie. Why each rule: ../README.md.

import { keyOf, parseRange, noneMatch, objectHeaders, refuse, forwardOf, forward } from './rules.js';
import FORWARDING from './forwarding.json';

const PAIRS = FORWARDING.pairs;

export async function handle(request, env, pairs = PAIRS) {
  const method = request.method;
  if (method !== 'GET' && method !== 'HEAD') {
    return refuse(405, { Allow: 'GET, HEAD' });
  }
  const key = keyOf(request.url);
  if (!key) return refuse(404);

  // A superseded name: the redirect, from the bundled table, with no bucket call.
  const next = forwardOf(key, pairs);
  if (next) return forward(next);

  const rangeHeader = request.headers.get('Range');
  const inm = request.headers.get('If-None-Match');
  const bucket = env.AUDIO;

  // The common case, a GET of the whole clip with nothing to compare: one bucket read.
  if (method === 'GET' && rangeHeader == null && inm == null) {
    const obj = await bucket.get(key);
    if (!obj) return refuse(404);
    const headers = objectHeaders(obj);
    headers['Content-Length'] = String(obj.size);
    return new Response(obj.body, { status: 200, headers });
  }

  // Otherwise the size and etag come first (a head, no body), then at most one ranged read.
  const meta = await bucket.head(key);
  if (!meta) return refuse(404);
  const headers = objectHeaders(meta);

  if (noneMatch(inm, meta.etag)) {
    return new Response(null, { status: 304, headers });
  }

  // If-Range: the range only if the validator is this clip's strong etag; a date or another etag
  // means "send the whole file" (RFC 9110 § 13.1.5). Clips never change, so this is a formality.
  let range = parseRange(rangeHeader, meta.size);
  const ifRange = request.headers.get('If-Range');
  if (range && ifRange != null && ifRange.trim() !== meta.httpEtag) range = null;

  if (range && range.unsatisfiable) {
    headers['Content-Range'] = `bytes */${meta.size}`;
    return new Response(null, { status: 416, headers });
  }

  let status = 200;
  let length = meta.size;
  if (range) {
    status = 206;
    length = range.length;
    headers['Content-Range'] = `bytes ${range.offset}-${range.offset + range.length - 1}/${meta.size}`;
  }
  headers['Content-Length'] = String(length);
  if (method === 'HEAD') return new Response(null, { status, headers });

  const obj = await bucket.get(key, range ? { range: { offset: range.offset, length: range.length } } : {});
  if (!obj) return refuse(404); // deleted between the two reads
  return new Response(obj.body, { status, headers });
}

export default {
  fetch: (request, env) => handle(request, env),
};
