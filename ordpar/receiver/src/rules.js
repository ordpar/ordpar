// The receiver's rules, pure functions with no Cloudflare in them (site decisions 26, 62, 104):
// what an event may carry, what is dropped, the day and the minute, the allowed origins.
// Tested under bun with no network: ordpar/tests/test_ordpar_receiver104.py.

/** Raw search lines are kept this many days, then folded (62; 104, revised 2026-11-08 from 90,
 *  Robin: a search can name something personal, so its line is kept no longer than needed). */
export const RETAIN_DAYS = 30;
/** Raw view lines are kept this many days, then only their totals (104, revised 2026-10-23 from
 *  90: a day's view lines are each device's pages that day, to the minute; the totals are made
 *  the next morning, and a week lets a day be totalled again, layer 6; revised 2026-11-08 from
 *  7, Robin: a day's lines are a device's reading trail, so they go once the day is totalled,
 *  with the next day left to total it again). */
export const VIEW_DAYS = 1;
/** After RETAIN_DAYS, a search string is kept as counts only if seen at least this often (62). */
export const KEEP_MIN = 3;
/** A query longer than this, in characters, drops its event (62: "over about 40"). */
export const MAX_QUERY = 40;
/** The chosen word: a headword the page offered; longer than this drops the event. */
export const MAX_WORD = 60;
/** A position in a list of suggestions or similar words: 1 … MAX_POSITION. */
export const MAX_POSITION = 100;
/** Bytes: a larger body is refused unread. */
export const MAX_BODY = 512;
/** Layer 6 (104): a daily code with at least PACE_MAX views inside any PACE_MINUTES minutes is
 *  left out of that day's totals; its raw lines stay, so the rule can change. */
export const PACE_MINUTES = 10;
export const PACE_MAX = 100;

export const ORIGIN = 'https://ordpar.no';
const LOCAL_ORIGIN = /^http:\/\/127\.0\.0\.1(:\d{1,5})?$/;

/** The page paths a view may name; anything else is stored as OTHER_PATH, so a mistyped address
 *  (which can hold a word the reader typed) is never stored. The page's events.js sends by the
 *  same pattern (104, R12; test_ordpar_events104.py holds the two together). */
const PATH = /^\/(?:bm-en\/(?:\d{1,7}\/)?|about\/|privacy\/|settings\/|favourites\/|history\/)?$/;
export const OTHER_PATH = '/other';

const DIGIT = /\p{N}/u;
const TYPES = { view: 1, install: 1, hit: 1, miss: 1, pick: 1 };
/** A search's language (site decisions 148's follow-up, Robin 2026-10-29: "Yes, count them"):
 *  'en' the English search, 'nb' the Norwegian one; a message without it is Norwegian (a page from
 *  before the English search). */
const LANGS = { en: 1, nb: 1 };

/** Is `origin` allowed to send events? `allowLocal` adds http://127.0.0.1:<port> (local tests). */
export function allowedOrigin(origin, allowLocal) {
  if (origin === ORIGIN) return true;
  return !!allowLocal && typeof origin === 'string' && LOCAL_ORIGIN.test(origin);
}

/** "2026-10-23" for a Date, in UTC (Cron Triggers run on UTC too). */
export function dayOf(date) {
  return date.toISOString().slice(0, 10);
}

/** Minutes since midnight UTC: the only time of day a view line keeps (for layer 6). */
export function minuteOf(date) {
  return date.getUTCHours() * 60 + date.getUTCMinutes();
}

/** The day `n` days before `day` ("YYYY-MM-DD"). */
export function daysBefore(day, n) {
  const d = new Date(day + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() - n);
  return dayOf(d);
}

/** A query as stored: NFC, spaces collapsed and trimmed, lower-cased (104, R11: "Hus" and "hus"
 *  one string, for the counts and 62's three-times rule). -> the string, '' when empty, or null
 *  when it must be dropped (a digit, or longer than MAX_QUERY characters as sent). */
export function cleanQuery(q) {
  if (typeof q !== 'string') return '';
  const s = q.normalize('NFC').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  if (DIGIT.test(s) || [...s].length > MAX_QUERY) return null;
  return s.toLowerCase();
}

/** The word chosen, as stored: by the query's rule, lower-cased too. */
function cleanWord(w) {
  if (typeof w !== 'string') return '';
  const s = w.normalize('NFC').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  if (DIGIT.test(s) || [...s].length > MAX_WORD) return null;
  return s.toLowerCase();
}

function position(i) {
  return Number.isInteger(i) && i >= 1 && i <= MAX_POSITION ? i : 0;
}

/** A view's path as stored. */
export function cleanPath(p) {
  return typeof p === 'string' && p.length <= 200 && PATH.test(p) ? p : OTHER_PATH;
}

/**
 * One event's body (the request's text) -> `{status, event}`:
 *   status 'ok'   — `event` is what is stored, every other field gone;
 *   status 'drop' — well formed, but 62's rule drops it (a digit, or too long): answered 204,
 *                   nothing stored;
 *   status 'bad'  — not an event: answered 400.
 * The fields (the page's `events.js` sends exactly these):
 *   {type: 'view', path}           the path only (26)
 *   {type: 'install'}              nothing else (104)
 *   {type: 'hit', query}           a search that found something: counts per query (62 (3))
 *   {type: 'miss', query, word, position}   a search that found nothing, the similar word
 *                                  chosen and its position, or word null / position null (62 (1))
 *   {type: 'pick', query, word, position}   a suggestion chosen while typing: the text typed so
 *                                  far, the word, its position (62 (2))
 * and on each of the three search events `lang`, 'en' or 'nb' (148's follow-up): stored with it;
 * missing, 'nb'; any other value is not an event.
 */
export function parseEvent(text) {
  if (typeof text !== 'string' || !text || text.length > MAX_BODY) return { status: 'bad' };
  let o;
  try { o = JSON.parse(text); } catch (e) { return { status: 'bad' }; }
  if (!o || typeof o !== 'object' || Array.isArray(o) || !TYPES[o.type]) return { status: 'bad' };
  const type = o.type;
  if (type === 'install') return { status: 'ok', event: { type } };
  if (type === 'view') {
    if (typeof o.path !== 'string' || !o.path) return { status: 'bad' };
    return { status: 'ok', event: { type, path: cleanPath(o.path) } };
  }
  const lang = o.lang == null ? 'nb' : o.lang;
  if (typeof lang !== 'string' || !LANGS[lang]) return { status: 'bad' };
  const query = cleanQuery(o.query);
  if (query === '') return { status: 'bad' };
  if (query === null) return { status: 'drop' };
  if (type === 'hit') return { status: 'ok', event: { type, query, lang } };
  const none = o.word == null && o.position == null;
  if (type === 'miss' && none) return { status: 'ok', event: { type, query, word: null, position: null, lang } };
  const word = cleanWord(o.word);
  const pos = position(o.position);
  if (word === '' || !pos) return { status: 'bad' };
  if (word === null) return { status: 'drop' };
  return { status: 'ok', event: { type, query, word, position: pos, lang } };
}
