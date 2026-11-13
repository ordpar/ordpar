// The daily secret (site decisions 104), in Workers KV: KV documents no restore of a deleted or
// expired key, where D1 (Time Travel) and Durable Objects can restore their past state, which
// would let a "deleted" secret come back and yesterday's codes be matched.
//
//   secret:<YYYY-MM-DD>   64 hex digits, random; expires by KV's own expiry five minutes after
//                         its day ends (an absolute `expiration`), and is deleted by the daily
//                         run the morning after as well, whichever comes first.
//
// The daily run (worker.js `scheduled`, 00:05 UTC) writes tomorrow's secret a day ahead, so it
// has reached every Cloudflare location long before it is used (KV takes up to 60 seconds or
// more to show a change elsewhere). Only if that failed does a request make today's itself.
import { newSecret, importKey } from './code.js';
import { dayOf, daysBefore } from './rules.js';

export const PREFIX = 'secret:';
/** Seconds after its day's end that a secret expires. */
export const GRACE = 300;

let cached = { day: '', key: null };

/** The seconds-since-epoch at which `day`'s secret expires. */
export function expiry(day) {
  return Date.parse(day + 'T00:00:00Z') / 1000 + 86400 + GRACE;
}

function dayAfter(day) {
  const d = new Date(day + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + 1);
  return dayOf(d);
}

/** The HMAC key for `day`, from this isolate's memory or from KV (made there if missing). */
export async function keyFor(kv, day) {
  if (cached.day === day && cached.key) return cached.key;
  let hex = await kv.get(PREFIX + day);
  if (!hex) {
    hex = newSecret();
    await kv.put(PREFIX + day, hex, { expiration: expiry(day) });
  }
  const key = await importKey(hex);
  cached = { day, key };
  return key;
}

/** The daily rotation, on `today`: yesterday's secret deleted, today's and tomorrow's present. */
export async function rotate(kv, today) {
  await kv.delete(PREFIX + daysBefore(today, 1));
  for (const day of [today, dayAfter(today)]) {
    if (!(await kv.get(PREFIX + day))) {
      await kv.put(PREFIX + day, newSecret(), { expiration: expiry(day) });
    }
  }
}

/** For the tests: forget the key held in memory. */
export function forget() {
  cached = { day: '', key: null };
}
