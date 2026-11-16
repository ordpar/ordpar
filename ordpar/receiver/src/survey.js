// The readers' survey (site decisions 173, "Ordpar — your first impressions", our
// own page in place of the Google form, kept after launch): the rules for a set of answers, pure
// functions with no Cloudflare in them. The endpoints are worker.js's (`handleSurvey`,
// `handleSurveys`); what is kept and for how long: ordpar/docs/receiver.md § The survey.
//
// A second kind beside reports, under the same rules: sent once, when the reader presses Send;
// nothing about the sender read (no address, no browser name, no code made from them); the hidden
// trap field; and the SAME total cap as reports (reports.js REPORTS_PER_HOUR, one count per UTC hour
// for reports and answers together, `report_hours`). Stored in D1 (`surveys`), the answers kept with
// no end date, the follow-up address or name (`follow`) deleted when Robin marks the answers done.
//
// The receiver does not know the questions: they live in the site's data file
// (ordpar/site/survey.json), so Robin can change them, and the ideas listed, with a site build alone.
// It takes any question key of the agreed shape, each answer a text (at most MAX_ANSWER characters)
// or a list of the choices ticked (at most MAX_CHOICES, each at most MAX_CHOICE characters); the
// page's own limits per question are within these (ordpar/tests/test_ordpar_survey173.py holds the
// data file's limits to them).

/** Characters (UTF-16 units, as a form's `maxlength` counts) of one written answer. */
export const MAX_ANSWER = 2000;
/** The choices ticked in one question. */
export const MAX_CHOICES = 20;
/** Characters of one choice's words (the page sends the choice as it reads). */
export const MAX_CHOICE = 300;
/** Questions answered in one message. */
export const MAX_QUESTIONS = 40;
/** Characters of the follow-up address or name (an e-mail address's longest, RFC 5321). */
export const MAX_FOLLOW = 254;
/** Bytes: a larger body is refused unread. Every answer at its longest in characters of up to 6
 *  bytes each as JSON stays well inside it (the test computes the data file's worst case). */
export const MAX_SURVEY_BODY = 131072;

/** A question's key, as the data file names it. */
export const KEY = /^[a-z][a-z0-9_]{0,39}$/;

function clean(s) {
  return s.normalize('NFC').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '').trim();
}

/** The follow-up address or name as stored: trimmed, NFC, white space one space, control characters
 *  dropped; '' when none; null when not allowed (not a string, or over MAX_FOLLOW). */
export function cleanFollow(value) {
  if (value == null) return '';
  if (typeof value !== 'string') return null;
  const s = value.normalize('NFC').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim();
  return s.length > MAX_FOLLOW ? null : s;
}

/**
 * A survey's body (the request's text) -> `{status, survey}`:
 *   'ok'   — `survey` is what is stored: {answers (JSON text of {key: text | [choices]}), follow};
 *   'drop' — the hidden trap field was filled: answered 204, nothing stored;
 *   'bad'  — not a survey: answered 400.
 * The fields (the page's survey.js sends exactly these): `answers`, an object of question key ->
 * a text or a list of choices (an empty one left out), and `follow`, the address or name, or null;
 * `hp`, the trap, only when filled. Any other field is ignored, never stored. Nothing answered and
 * no follow-up: not a survey.
 */
export function parseSurvey(text) {
  if (typeof text !== 'string' || !text) return { status: 'bad' };
  let o;
  try { o = JSON.parse(text); } catch (e) { return { status: 'bad' }; }
  if (!o || typeof o !== 'object' || Array.isArray(o)) return { status: 'bad' };
  if (o.hp != null && o.hp !== '') return { status: 'drop' };
  const a = o.answers;
  if (!a || typeof a !== 'object' || Array.isArray(a)) return { status: 'bad' };
  const keys = Object.keys(a);
  if (keys.length > MAX_QUESTIONS) return { status: 'bad' };
  const answers = {};
  for (const k of keys) {
    if (!KEY.test(k)) return { status: 'bad' };
    const v = a[k];
    if (typeof v === 'string') {
      const s = clean(v);
      if (s.length > MAX_ANSWER) return { status: 'bad' };
      if (s) answers[k] = s;
    } else if (Array.isArray(v)) {
      if (v.length > MAX_CHOICES) return { status: 'bad' };
      const out = [];
      for (const c of v) {
        if (typeof c !== 'string') return { status: 'bad' };
        const s = clean(c).replace(/\s+/g, ' ');
        if (s.length > MAX_CHOICE) return { status: 'bad' };
        if (s && !out.includes(s)) out.push(s);
      }
      if (out.length) answers[k] = out;
    } else if (v != null) {
      return { status: 'bad' };
    }
  }
  const follow = cleanFollow(o.follow);
  if (follow === null) return { status: 'bad' };
  if (!Object.keys(answers).length && !follow) return { status: 'bad' };
  return { status: 'ok', survey: { answers: JSON.stringify(answers), follow: follow || null } };
}
