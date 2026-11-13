// The audio Worker's pure rules (site 159): the key's shape, the range parser, the etag check,
// the headers and the constants. Kept apart from worker.js because workerd treats every export
// of the main module as an entry point and refuses a string there (found in the local run).

/** The one key shape the bucket holds: `clip_name` / `name_for_sent` in scripts/audio/clips.py. */
export const NAME = /^ordpar-[0-9a-f]{16}\.mp3$/;

/** The values set at upload (for-the-site.md § 4); used when an object lacks them. */
export const TYPE = 'audio/mpeg';
export const CACHE = 'public, max-age=31536000, immutable';

/** A missing clip may be uploaded later under that name: its 404 is cached a minute at most. */
export const MISSING_CACHE = 'public, max-age=60';

/** The site may read a clip with fetch (a fetch ahead of play, Web Audio): its origin only. */
export const SITE = 'https://ordpar.no';

export const COMMON = {
  'Access-Control-Allow-Origin': SITE,
  'Access-Control-Expose-Headers': 'Content-Range, Accept-Ranges, ETag',
  'X-Content-Type-Options': 'nosniff',
};

export function refuse(status, extra) {
  return new Response(null, {
    status,
    headers: Object.assign({ 'Cache-Control': MISSING_CACHE }, COMMON, extra || {}),
  });
}

/** The key a request path asks for, or null. The raw path is checked, so `%2F`, `..` and any
 *  other escape fail the pattern as they stand and are never decoded into a key. */
export function keyOf(url) {
  const path = new URL(url).pathname;
  if (path.charAt(0) !== '/') return null;
  const name = path.slice(1);
  return NAME.test(name) ? name : null;
}

/**
 * The byte range a `Range` header asks for, against an object of `size` bytes (RFC 9110 § 14):
 *   null                       no Range, or one to ignore (a garbled header, another unit, an
 *                              inverted a-b, or several ranges): the whole file, 200
 *   { unsatisfiable: true }    416 with `Content-Range: bytes * /size`
 *   { offset, length }         206 with that part
 */
export function parseRange(header, size) {
  if (header == null) return null;
  const m = /^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$/i.exec(header);
  if (!m) return null; // several ranges (a comma), another unit, garbage: ignored, 200 whole
  const [, a, b] = m;
  if (a === '' && b === '') return null;
  if (a === '') {
    // the suffix form, bytes=-n: the last n bytes (all of them if n >= size)
    const n = Number(b);
    if (n === 0 || size === 0) return { unsatisfiable: true };
    const length = Math.min(n, size);
    return { offset: size - length, length };
  }
  const first = Number(a);
  if (b !== '' && Number(b) < first) return null; // inverted: invalid, so ignored
  if (first >= size) return { unsatisfiable: true };
  const last = b === '' ? size - 1 : Math.min(Number(b), size - 1);
  return { offset: first, length: last - first + 1 };
}

/** If-None-Match against the object's etag (weak comparison, RFC 9110 § 13.1.2). */
export function noneMatch(header, etag) {
  if (header == null) return false;
  if (header.trim() === '*') return true;
  return header.split(',').some((t) => t.trim().replace(/^W\//, '').replace(/^"|"$/g, '') === etag);
}

/** The headers every answer for a found clip carries, from the object's own metadata. */
export function objectHeaders(obj) {
  const meta = obj.httpMetadata || {};
  return Object.assign({
    'Content-Type': meta.contentType || TYPE,
    'Cache-Control': meta.cacheControl || CACHE,
    ETag: obj.httpEtag,
    'Accept-Ranges': 'bytes',
  }, COMMON);
}

/* ------------------------------------------------------------ forwarding (site decisions 179) */

/** A superseded name's redirect is cached a day, never immutable: a later fix can move it on. */
export const FORWARD_CACHE = 'public, max-age=86400';

/** 302, not 301 or 308 (browsers keep those for good): README.md § Forwarding superseded names. */
export const FORWARD_STATUS = 302;

const HEX16 = /^[0-9a-f]{16}$/;

/** The key a superseded `key` forwards to, or null. `pairs` maps old 16-hex names to new ones
 *  (src/forwarding.json, flattened by sync_forwarding.py). Followed once: a target that is not a
 *  clip name, is the name itself, or is itself forwarded is ignored, so no redirect can loop. */
export function forwardOf(key, pairs) {
  if (!pairs) return null;
  const old = key.slice(7, 23); // ordpar-<16 hex>.mp3, already checked against NAME
  if (!Object.hasOwn(pairs, old)) return null;
  const next = pairs[old];
  if (typeof next !== 'string' || !HEX16.test(next) || next === old || Object.hasOwn(pairs, next)) return null;
  return `ordpar-${next}.mp3`;
}

/** The redirect to `key`, with the headers every answer carries. */
export function forward(key) {
  return new Response(null, {
    status: FORWARD_STATUS,
    headers: Object.assign({ Location: '/' + key, 'Cache-Control': FORWARD_CACHE }, COMMON),
  });
}
