// "Report a mistake" (site decisions 166: our own receiver; the name field
// optional): the rules for a report, pure functions with no Cloudflare in them, and the token check
// for Robin's two read endpoints. The endpoints themselves are worker.js's (`handleReport`,
// `handleReports`); what is kept and for how long: ordpar/docs/receiver.md § Reports.
//
// A report is the one message the reader writes and sends; the counting's rules (the stats
// setting, Global Privacy Control, Do Not Track, the bot layers) concern the counting and are not
// applied here. Nothing about the sender is read for a report: not the address (IP), not the
// browser name, not a code made from them (decisions 166: the per-sender
// limit dropped). Junk is kept out by the hidden trap field and a cap on the reports the receiver accepts
// per UTC hour IN TOTAL, from everyone together (REPORTS_PER_HOUR): one count per hour, nothing
// else, deleted when the hour is over.
//
// The name to credit (166, Robin 2026-11-05: a reader who wants it is credited by name on a page
// of its own): an optional `credit`, a name or nickname of at most MAX_CREDIT characters, no
// links; stored with the report and deleted with the reply address when Robin closes it.

/** Characters (UTF-16 units, as the form's `maxlength` counts) of a report's text. */
export const MAX_REPORT_TEXT = 2000;
/** An e-mail address's longest (RFC 5321). */
export const MAX_REPLY = 254;
/** Bytes: a larger body is refused unread (2,000 characters at up to 6 bytes each as JSON). */
export const MAX_REPORT_BODY = 16384;
/** The categories the form offers; none is allowed too. */
export const CATEGORIES = ['translation', 'audio', 'norwegian', 'other'];
/** Reports the receiver accepts in one UTC hour, from everyone together; past it, 429 for every
 *  sender until the next hour. 30: far above what one dictionary's readers send by hand (a
 *  report takes a minute to write, and Robin reads each), and low enough that a script that gets
 *  past the trap adds at most 720 reports a day to read and delete. */
export const REPORTS_PER_HOUR = 30;
/** Characters of the name to credit (a name or nickname). */
export const MAX_CREDIT = 60;
/** The open reports `GET /reports` lists at most, newest first. */
export const LIST_MAX = 500;

const BUILD = /^[0-9a-f]{6,40}$/;
const REPLY = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
/** A link in a name to credit: refused (the page's report.js has the same pattern, a test holds
 *  them equal). An address with a scheme, "www.", or a word ending in a common
 *  top-level domain ("example.com", "spam.ru/x"). */
export const LINK = /:\/\/|www\.|\.(com|net|org|info|biz|io|co|me|app|dev|xyz|top|site|online|shop|ru|cn|de|uk|no|se|dk)\b/i;

/** The name to credit as stored: trimmed, NFC, runs of white space (a line break too) one space,
 *  control characters dropped; '' when none. `null` when it is not allowed: too long, or a link. */
export function cleanCredit(value) {
  if (value == null) return '';
  if (typeof value !== 'string') return null;
  const s = value.normalize('NFC').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim();
  if (s.length > MAX_CREDIT || LINK.test(s)) return null;
  return s;
}

/** "2026-11-05T14": the hour a count belongs to (UTC). */
export function hourOf(date) {
  return date.toISOString().slice(0, 13);
}

/**
 * A report's body (the request's text) -> `{status, report}`:
 *   'ok'   — `report` is what is stored: {article, build, category, text, reply, credit};
 *   'drop' — the hidden trap field was filled: answered 204, nothing stored;
 *   'bad'  — not a report: answered 400.
 * The fields (the page's report.js sends exactly these): `id` (the article, a whole number from 1
 * to 9,999,999), `build` (hex or null), `category` (one of CATEGORIES, or null), `text` (required,
 * 1 … MAX_REPORT_TEXT once trimmed), `reply` (an e-mail address or null), `credit` (the name to
 * credit, `cleanCredit`, or null), and `hp`, the trap, only when filled. Any other field is
 * ignored, never stored.
 */
export function parseReport(text) {
  if (typeof text !== 'string' || !text) return { status: 'bad' };
  let o;
  try { o = JSON.parse(text); } catch (e) { return { status: 'bad' }; }
  if (!o || typeof o !== 'object' || Array.isArray(o)) return { status: 'bad' };
  if (o.hp != null && o.hp !== '') return { status: 'drop' };
  const article = o.id;
  if (!Number.isInteger(article) || article < 1 || article > 9999999) return { status: 'bad' };
  const build = o.build == null ? null : o.build;
  if (build !== null && (typeof build !== 'string' || !BUILD.test(build))) return { status: 'bad' };
  const category = o.category == null ? null : o.category;
  if (category !== null && !CATEGORIES.includes(category)) return { status: 'bad' };
  if (typeof o.text !== 'string') return { status: 'bad' };
  const body = o.text.normalize('NFC').trim();
  if (!body || body.length > MAX_REPORT_TEXT) return { status: 'bad' };
  let reply = o.reply == null ? '' : o.reply;
  if (typeof reply !== 'string') return { status: 'bad' };
  reply = reply.trim();
  if (reply && (reply.length > MAX_REPLY || !REPLY.test(reply))) return { status: 'bad' };
  const credit = cleanCredit(o.credit);
  if (credit === null) return { status: 'bad' };
  return { status: 'ok', report: { article, build, category, text: body, reply: reply || null,
    credit: credit || null } };
}

/** Is `header` (the request's Authorization) "Bearer <token>" for the Worker secret `token`?
 *  False whenever the secret is unset or short. Compared in time independent of where they differ. */
export function authorised(header, token) {
  if (typeof token !== 'string' || token.length < 16) return false;
  if (typeof header !== 'string' || !header.startsWith('Bearer ')) return false;
  const a = new TextEncoder().encode(header.slice(7));
  const b = new TextEncoder().encode(token);
  let diff = a.length ^ b.length;
  for (let i = 0; i < b.length; i++) diff |= (a[i % (a.length || 1)] || 0) ^ b[i];
  return diff === 0;
}
