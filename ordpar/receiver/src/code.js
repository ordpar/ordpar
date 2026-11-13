// The daily scrambled code (site decisions 104): for a page view only,
//   code = HMAC-SHA-256(today's secret, CF-Connecting-IP + "\n" + User-Agent), first 16 hex digits.
// The address and the browser name go into the hash and nowhere else: never stored, never logged.
// The secret is replaced every day and the old one deleted (secret.js), so a code made today
// cannot be matched with one made yesterday, and nobody — us included — can recompute a code
// from an address once its day's secret is gone.

const enc = new TextEncoder();

/** 32 random bytes as 64 hex digits: one day's secret. */
export function newSecret() {
  const b = new Uint8Array(32);
  crypto.getRandomValues(b);
  return hex(b);
}

function hex(bytes) {
  let s = '';
  for (const x of bytes) s += x.toString(16).padStart(2, '0');
  return s;
}

/** A secret's hex -> the HMAC key (made once per isolate per day by secret.js). */
export function importKey(secretHex) {
  const raw = new Uint8Array(secretHex.match(/../g).map((h) => parseInt(h, 16)));
  return crypto.subtle.importKey('raw', raw, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
}

/** The code for one address and browser name under `key`: 16 hex digits (64 bits). */
export async function dailyCode(key, ip, ua) {
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(String(ip) + '\n' + String(ua)));
  return hex(new Uint8Array(sig).slice(0, 8));
}
