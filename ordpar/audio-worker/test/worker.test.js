// The audio Worker's own tests, under bun with no network (site 159): run by
// ordpar/tests/test_ordpar_audioworker159.py, or here with `bun test`. R2 is stood in for by a small
// in-memory bucket with the binding's interface: `get(key, { range, onlyIf })` and `head(key)`, each
// call counted, so a test can say the bucket was never touched.
import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import * as MAIN from '../src/worker.js';
import { keyOf, parseRange, NAME, TYPE, CACHE, SITE } from '../src/rules.js';

const { handle } = MAIN;

const ROOT = join(import.meta.dir, '..');
const SRC = ['worker.js', 'rules.js'];

/* ------------------------------------------------------------ the stand-in */

function md5ish(bytes) {
  // any stable hex string will do for an etag here
  let h = 0;
  for (const b of bytes) h = (h * 31 + b) >>> 0;
  return h.toString(16).padStart(8, '0') + 'cafebabecafebabecafebabe';
}

function bucket(objects) {
  const calls = [];
  const store = new Map();
  for (const [key, o] of Object.entries(objects)) {
    const etag = md5ish(o.bytes);
    store.set(key, { bytes: o.bytes, etag, httpMetadata: o.httpMetadata === undefined ? { contentType: TYPE, cacheControl: CACHE } : o.httpMetadata });
  }
  const meta = (key, s) => ({
    key,
    size: s.bytes.length,
    etag: s.etag,
    httpEtag: `"${s.etag}"`,
    httpMetadata: s.httpMetadata,
  });
  return {
    calls,
    async head(key) {
      calls.push(['head', key]);
      const s = store.get(key);
      return s ? meta(key, s) : null;
    },
    async get(key, opts = {}) {
      calls.push(['get', key, opts]);
      const s = store.get(key);
      if (!s) return null;
      const m = meta(key, s);
      const c = opts.onlyIf;
      if (c && ((c.etagDoesNotMatch && c.etagDoesNotMatch === s.etag) || (c.etagMatches && c.etagMatches !== s.etag))) {
        return m; // a failed precondition: the object without a body, as R2 does
      }
      let part = s.bytes;
      const r = opts.range;
      if (r) {
        if ('suffix' in r) part = s.bytes.slice(Math.max(0, s.bytes.length - r.suffix));
        else {
          const off = r.offset || 0;
          if (off >= s.bytes.length) throw new Error('InvalidRange');
          part = s.bytes.slice(off, r.length === undefined ? undefined : off + r.length);
        }
      }
      return Object.assign(m, { body: new Blob([part]).stream(), range: r });
    },
  };
}

const A = 'ordpar-0123456789abcdef.mp3';
const B = 'ordpar-fedcba9876543210.mp3'; // uploaded with no headers at all
const MISSING = 'ordpar-00000000000000aa.mp3';
const BYTES = Uint8Array.from({ length: 5000 }, (_, i) => (i * 7 + 3) % 256);

function env() {
  return { AUDIO: bucket({ [A]: { bytes: BYTES }, [B]: { bytes: BYTES.slice(0, 100), httpMetadata: {} } }) };
}

function req(path, o = {}) {
  return new Request('https://ordpar-audio.example.workers.dev' + path, { method: o.method || 'GET', headers: o.headers || {} });
}

async function bytesOf(res) {
  return new Uint8Array(await res.arrayBuffer());
}

/* ------------------------------------------------------------ the name */

describe('the name: ordpar- + 16 lower-case hex + .mp3, nothing else reaches R2', () => {
  test('good names pass', () => {
    expect(keyOf('https://x/' + A)).toBe(A);
    expect(NAME.test('ordpar-ac06dc7ae33bbab9.mp3')).toBe(true);
  });
  const bad = [
    '/ordpar-0123456789ABCDEF.mp3', // upper-case hex
    '/ordpar-0123456789abcde.mp3', // 15 digits
    '/ordpar-0123456789abcdef0.mp3', // 17 digits
    '/ordpar-0123456789abcdeg.mp3', // not hex
    '/ordpar-0123456789abcdef.wav',
    '/ordpar-0123456789abcdef.mp3.txt',
    '/ordpar-0123456789abcdef.MP3',
    '/0123456789abcdef.mp3',
    '/clips/' + A,
    '/' + A + '/',
    '/x%2F' + A,
    '/%2F' + A,
    '/' + A.replace('.mp3', '%2Emp3'),
    '/..%2F' + A,
    '/',
    '/?list-type=2',
    '//' + A,
  ];
  for (const p of bad) {
    test(`refused without a bucket call: ${p}`, async () => {
      const e = env();
      const res = await handle(req(p), e);
      expect(res.status).toBe(404);
      expect((await bytesOf(res)).length).toBe(0);
      expect(e.AUDIO.calls).toEqual([]);
    });
  }
  test('a path with .. is normalized by the URL parser and still fails the pattern', async () => {
    const e = env();
    const res = await handle(req('/a/../b/' + A), e);
    expect(res.status).toBe(404);
    expect(e.AUDIO.calls).toEqual([]);
  });
  test('a query string does not change the key', async () => {
    const e = env();
    const res = await handle(req('/' + A + '?x=1'), e);
    expect(res.status).toBe(200);
  });
});

/* ------------------------------------------------------------ methods */

describe('methods: GET and HEAD only', () => {
  for (const m of ['POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']) {
    test(`${m} is a 405 with Allow, and no bucket call`, async () => {
      const e = env();
      const res = await handle(req('/' + A, { method: m }), e);
      expect(res.status).toBe(405);
      expect(res.headers.get('Allow')).toBe('GET, HEAD');
      expect((await bytesOf(res)).length).toBe(0);
      expect(e.AUDIO.calls).toEqual([]);
    });
  }
});

/* ------------------------------------------------------------ whole file */

describe('the whole file', () => {
  test('GET with no Range: 200, every byte, the headers, one bucket read', async () => {
    const e = env();
    const res = await handle(req('/' + A), e);
    expect(res.status).toBe(200);
    expect(await bytesOf(res)).toEqual(BYTES);
    expect(res.headers.get('Content-Type')).toBe('audio/mpeg');
    expect(res.headers.get('Cache-Control')).toBe('public, max-age=31536000, immutable');
    expect(res.headers.get('Content-Length')).toBe('5000');
    expect(res.headers.get('Accept-Ranges')).toBe('bytes');
    expect(res.headers.get('ETag')).toMatch(/^"[0-9a-f]+"$/);
    expect(res.headers.get('Content-Range')).toBeNull();
    expect(e.AUDIO.calls.length).toBe(1);
    expect(e.AUDIO.calls[0][0]).toBe('get');
  });
  test('an object with no stored headers gets the two fallbacks', async () => {
    const res = await handle(req('/' + B), env());
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe(TYPE);
    expect(res.headers.get('Cache-Control')).toBe(CACHE);
    expect((await bytesOf(res)).length).toBe(100);
  });
  test('the object\'s own headers are passed on as stored', async () => {
    const e = { AUDIO: bucket({ [A]: { bytes: BYTES, httpMetadata: { contentType: 'audio/x-test', cacheControl: 'max-age=5' } } }) };
    const res = await handle(req('/' + A), e);
    expect(res.headers.get('Content-Type')).toBe('audio/x-test');
    expect(res.headers.get('Cache-Control')).toBe('max-age=5');
  });
  test('HEAD: the headers and the full length, no body', async () => {
    const e = env();
    const res = await handle(req('/' + A, { method: 'HEAD' }), e);
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Length')).toBe('5000');
    expect(res.headers.get('Content-Type')).toBe('audio/mpeg');
    expect(res.headers.get('Accept-Ranges')).toBe('bytes');
    expect((await bytesOf(res)).length).toBe(0);
    expect(e.AUDIO.calls.map((c) => c[0])).toEqual(['head']);
  });
});

/* ------------------------------------------------------------ ranges */

describe('ranges (Safari asks for media in ranges)', () => {
  const cases = [
    ['bytes=0-99', 0, 100],
    ['bytes=1000-', 1000, 4000],
    ['bytes=-500', 4500, 500],
    ['bytes=0-0', 0, 1],
    ['bytes=0-1', 0, 2], // Safari's first probe
    ['bytes=4999-', 4999, 1],
    ['bytes=4000-99999', 4000, 1000], // last byte past the end: clamped
    ['bytes=-99999', 0, 5000], // suffix longer than the file: all of it
    ['bytes=0-', 0, 5000], // Chrome's and Edge's usual ask
    ['BYTES = 10 - 19', 10, 10], // case and spaces tolerated
  ];
  for (const [h, off, len] of cases) {
    test(`${h}: 206, Content-Range, Content-Length and exactly those bytes`, async () => {
      const e = env();
      const res = await handle(req('/' + A, { headers: { Range: h } }), e);
      expect(res.status).toBe(206);
      expect(res.headers.get('Content-Range')).toBe(`bytes ${off}-${off + len - 1}/5000`);
      expect(res.headers.get('Content-Length')).toBe(String(len));
      expect(res.headers.get('Accept-Ranges')).toBe('bytes');
      expect(res.headers.get('Content-Type')).toBe('audio/mpeg');
      expect(res.headers.get('Cache-Control')).toBe(CACHE);
      expect(await bytesOf(res)).toEqual(BYTES.slice(off, off + len));
      // a head, then one read of exactly the part
      expect(e.AUDIO.calls.map((c) => c[0])).toEqual(['head', 'get']);
      expect(e.AUDIO.calls[1][2]).toEqual({ range: { offset: off, length: len } });
    });
  }
  for (const h of ['bytes=5000-', 'bytes=5000-6000', 'bytes=99999-', 'bytes=-0']) {
    test(`${h}: 416 with Content-Range bytes */5000, no body, no read`, async () => {
      const e = env();
      const res = await handle(req('/' + A, { headers: { Range: h } }), e);
      expect(res.status).toBe(416);
      expect(res.headers.get('Content-Range')).toBe('bytes */5000');
      expect((await bytesOf(res)).length).toBe(0);
      expect(e.AUDIO.calls.map((c) => c[0])).toEqual(['head']);
    });
  }
  for (const h of ['bytes=0-99,200-299', 'bytes=10-5', 'items=0-99', 'bytes=', 'bytes=-', 'garbage', 'bytes=a-b']) {
    test(`${h}: ignored, 200 and the whole file`, async () => {
      const res = await handle(req('/' + A, { headers: { Range: h } }), env());
      expect(res.status).toBe(200);
      expect(res.headers.get('Content-Range')).toBeNull();
      expect(await bytesOf(res)).toEqual(BYTES);
    });
  }
  test('HEAD with a range: 206 headers, no body, no read', async () => {
    const e = env();
    const res = await handle(req('/' + A, { method: 'HEAD', headers: { Range: 'bytes=0-99' } }), e);
    expect(res.status).toBe(206);
    expect(res.headers.get('Content-Range')).toBe('bytes 0-99/5000');
    expect(res.headers.get('Content-Length')).toBe('100');
    expect((await bytesOf(res)).length).toBe(0);
    expect(e.AUDIO.calls.map((c) => c[0])).toEqual(['head']);
  });
  test('If-Range with the clip\'s etag keeps the range; anything else gives the whole file', async () => {
    const e = env();
    const etag = (await e.AUDIO.head(A)).httpEtag;
    let res = await handle(req('/' + A, { headers: { Range: 'bytes=0-99', 'If-Range': etag } }), e);
    expect(res.status).toBe(206);
    res = await handle(req('/' + A, { headers: { Range: 'bytes=0-99', 'If-Range': '"other"' } }), e);
    expect(res.status).toBe(200);
    expect(await bytesOf(res)).toEqual(BYTES);
    res = await handle(req('/' + A, { headers: { Range: 'bytes=0-99', 'If-Range': 'Sat, 01 Nov 2026 00:00:00 GMT' } }), e);
    expect(res.status).toBe(200);
  });
  test('parseRange directly', () => {
    expect(parseRange(null, 10)).toBeNull();
    expect(parseRange('bytes=2-4', 10)).toEqual({ offset: 2, length: 3 });
    expect(parseRange('bytes=-3', 10)).toEqual({ offset: 7, length: 3 });
    expect(parseRange('bytes=10-', 10)).toEqual({ unsatisfiable: true });
    expect(parseRange('bytes=0-', 0)).toEqual({ unsatisfiable: true });
    expect(parseRange('bytes=1-2, 4-5', 10)).toBeNull();
  });
});

/* ------------------------------------------------------------ 304 */

describe('If-None-Match: 304', () => {
  test('the clip\'s etag (strong, weak, in a list, or *) gives a 304 with no body and no read', async () => {
    const e = env();
    const etag = (await e.AUDIO.head(A)).httpEtag;
    for (const v of [etag, 'W/' + etag, `"x", ${etag}`, '*']) {
      e.AUDIO.calls.length = 0;
      const res = await handle(req('/' + A, { headers: { 'If-None-Match': v } }), e);
      expect(res.status).toBe(304);
      expect(res.headers.get('ETag')).toBe(etag);
      expect(res.headers.get('Cache-Control')).toBe(CACHE);
      expect((await bytesOf(res)).length).toBe(0);
      expect(e.AUDIO.calls.map((c) => c[0])).toEqual(['head']);
    }
  });
  test('another etag: 200 and the file; with a Range, 206', async () => {
    let res = await handle(req('/' + A, { headers: { 'If-None-Match': '"nope"' } }), env());
    expect(res.status).toBe(200);
    expect(await bytesOf(res)).toEqual(BYTES);
    res = await handle(req('/' + A, { headers: { 'If-None-Match': '"nope"', Range: 'bytes=0-9' } }), env());
    expect(res.status).toBe(206);
  });
  test('a matching etag wins over a Range (RFC 9110 § 13.2.2)', async () => {
    const e = env();
    const etag = (await e.AUDIO.head(A)).httpEtag;
    const res = await handle(req('/' + A, { headers: { 'If-None-Match': etag, Range: 'bytes=0-9' } }), e);
    expect(res.status).toBe(304);
  });
});

/* ------------------------------------------------------------ missing, CORS, cookies */

describe('a missing clip, CORS, nothing kept', () => {
  test('a well-formed name not in the bucket: 404, cached a minute, no body', async () => {
    for (const o of [{}, { method: 'HEAD' }, { headers: { Range: 'bytes=0-9' } }, { headers: { 'If-None-Match': '"x"' } }]) {
      const res = await handle(req('/' + MISSING, o), env());
      expect(res.status).toBe(404);
      expect(res.headers.get('Cache-Control')).toBe('public, max-age=60');
      expect((await bytesOf(res)).length).toBe(0);
    }
  });
  test('every answer names ordpar.no as the one origin that may read it, never *', async () => {
    for (const r of [req('/' + A), req('/' + MISSING), req('/x'), req('/' + A, { method: 'POST' })]) {
      const res = await handle(r, env());
      expect(res.headers.get('Access-Control-Allow-Origin')).toBe(SITE);
    }
    expect(SITE).toBe('https://ordpar.no');
  });
  test('no Set-Cookie, and a cookie sent changes nothing', async () => {
    const res = await handle(req('/' + A, { headers: { Cookie: 'a=b' } }), env());
    expect(res.status).toBe(200);
    expect(res.headers.get('Set-Cookie')).toBeNull();
    for (const f of SRC) expect(readFileSync(join(ROOT, 'src', f), 'utf8')).not.toMatch(/['"](set-)?cookie['"]/i);
  });
});

/* ------------------------------------------------------------ the configuration */

describe('wrangler.jsonc', () => {
  const text = readFileSync(join(ROOT, 'wrangler.jsonc'), 'utf8');
  const cfg = JSON.parse(text.replace(/^\s*\/\/.*$/gm, ''));
  test('Workers Logs off (site decisions 104), no Logpush, no traces', () => {
    expect(cfg.observability.enabled).toBe(false);
    expect(cfg.observability.logs.enabled).toBe(false);
    expect(cfg.observability.logs.invocation_logs).toBe(false);
    expect(cfg.observability.traces.enabled).toBe(false);
    expect(cfg.logpush).toBe(false);
  });
  test('the name, workers.dev without preview addresses, the one R2 binding', () => {
    expect(cfg.name).toBe('ordpar-audio');
    expect(cfg.workers_dev).toBe(true);
    expect(cfg.preview_urls).toBe(false);
    expect(cfg.r2_buckets).toEqual([{ binding: 'AUDIO', bucket_name: 'ordpar-audio' }]);
    expect(cfg.d1_databases).toBeUndefined();
    expect(cfg.kv_namespaces).toBeUndefined();
  });
  test('the Worker never logs, and never lists or writes the bucket', () => {
    for (const f of SRC) {
      const src = readFileSync(join(ROOT, 'src', f), 'utf8');
      expect(src).not.toMatch(/console\./);
      expect(src).not.toMatch(/\.list\(/);
      expect(src).not.toMatch(/\.(put|delete)\(/);
    }
  });
  test('the main module exports only functions and its default handler (workerd refuses any other export)', () => {
    for (const [k, v] of Object.entries(MAIN)) {
      if (k !== 'default') expect(typeof v).toBe('function');
    }
    expect(typeof MAIN.default.fetch).toBe('function');
  });
});

/* ------------------------------------------------------------ forwarding (site decisions 179) */

describe('forwarding: a superseded name is sent to the clip that replaced it (site decisions 179)', () => {
  const OLD = 'ordpar-1111111111111111.mp3';
  const OLD_HEX = '1111111111111111';
  const A_HEX = A.slice(7, 23);
  const TABLE = { [OLD_HEX]: A_HEX };
  const FWD_CACHE = 'public, max-age=86400';

  for (const method of ['GET', 'HEAD']) {
    test(`${method} of an old name: 302 to the new name, cached a day, CORS, no bucket call`, async () => {
      const e = env();
      const res = await handle(req('/' + OLD, { method }), e, TABLE);
      expect(res.status).toBe(302);
      expect(res.headers.get('Location')).toBe('/' + A);
      expect(res.headers.get('Cache-Control')).toBe(FWD_CACHE);
      expect(res.headers.get('Cache-Control')).not.toMatch(/immutable/);
      expect(res.headers.get('Access-Control-Allow-Origin')).toBe(SITE);
      expect(res.headers.get('X-Content-Type-Options')).toBe('nosniff');
      expect(res.headers.get('Set-Cookie')).toBeNull();
      expect((await bytesOf(res)).length).toBe(0);
      expect(e.AUDIO.calls).toEqual([]);
    });
  }
  test('a Range request (and an If-None-Match) for an old name is redirected too, no bucket call', async () => {
    for (const headers of [{ Range: 'bytes=0-1' }, { Range: 'bytes=0-' }, { 'If-None-Match': '"x"' }]) {
      const e = env();
      const res = await handle(req('/' + OLD, { headers }), e, TABLE);
      expect(res.status).toBe(302);
      expect(res.headers.get('Location')).toBe('/' + A);
      expect(res.headers.get('Content-Range')).toBeNull();
      expect(e.AUDIO.calls).toEqual([]);
    }
  });
  test('the redirect, followed, is served as the new clip always was', async () => {
    const e = env();
    const first = await handle(req('/' + OLD), e, TABLE);
    const res = await handle(req(first.headers.get('Location')), e, TABLE);
    expect(res.status).toBe(200);
    expect(res.headers.get('Cache-Control')).toBe(CACHE);
    expect(await bytesOf(res)).toEqual(BYTES);
  });
  test('a current name is served exactly as before, with the table, an empty one or the bundled one', async () => {
    for (const t of [TABLE, {}, undefined]) {
      const e = env();
      const res = await handle(req('/' + A), e, t);
      expect(res.status).toBe(200);
      expect(res.headers.get('Location')).toBeNull();
      expect(await bytesOf(res)).toEqual(BYTES);
      expect(e.AUDIO.calls.map((c) => c[0])).toEqual(['get']);
    }
  });
  test('a bad name is still refused before the table: an upper-case old name is a 404', async () => {
    const e = env();
    const res = await handle(req('/' + OLD.replace('1111', 'AAAA')), e, { AAAA111111111111: A_HEX });
    expect(res.status).toBe(404);
    expect(e.AUDIO.calls).toEqual([]);
  });
  test('the table is followed once: a target that is itself an old name is not forwarded, so nothing loops', async () => {
    const X = '2222222222222222';
    const Y = '3333333333333333';
    for (const t of [{ [OLD_HEX]: OLD_HEX }, { [OLD_HEX]: X, [X]: OLD_HEX }, { [OLD_HEX]: X, [X]: Y }]) {
      const e = { AUDIO: bucket({ [OLD]: { bytes: BYTES } }) };
      const res = await handle(req('/' + OLD), e, t);
      expect(res.status).toBe(200); // served from R2 as today
      expect(res.headers.get('Location')).toBeNull();
    }
  });
  test('a malformed target in the table is ignored: the name is served as today', async () => {
    for (const bad of ['ABCDEF0123456789', '123', 'ordpar-0123456789abcdef.mp3', null, 7]) {
      const e = { AUDIO: bucket({ [OLD]: { bytes: BYTES } }) };
      const res = await handle(req('/' + OLD), e, { [OLD_HEX]: bad });
      expect(res.status).toBe(200);
    }
  });
  test('the lookup reads only the table\'s own keys, never its prototype', async () => {
    const e = env();
    const res = await handle(req('/' + A), e, Object.create({ [A_HEX]: OLD_HEX }));
    expect(res.status).toBe(200);
  });
  test('the bundled src/forwarding.json parses, and every key and value is a clip name', () => {
    const doc = JSON.parse(readFileSync(join(ROOT, 'src', 'forwarding.json'), 'utf8'));
    expect(typeof doc.pairs).toBe('object');
    expect(Array.isArray(doc.pairs)).toBe(false);
    for (const [k, v] of Object.entries(doc.pairs)) {
      expect(NAME.test(`ordpar-${k}.mp3`)).toBe(true);
      expect(NAME.test(`ordpar-${v}.mp3`)).toBe(true);
      expect(v).not.toBe(k);
      expect(Object.hasOwn(doc.pairs, v)).toBe(false); // flattened: one redirect, never a chain
    }
  });
});
