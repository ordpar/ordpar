// Every statement the receiver runs against D1 (SQLite). The daily work is done in SQL, on D1's
// side: a Cron Trigger has 10 ms of CPU on the Free plan, and time spent waiting on D1 does not
// count (Cloudflare, Workers limits § CPU time). The same strings run under bun:sqlite in the tests.
import { KEEP_MIN, PACE_MAX, PACE_MINUTES } from './rules.js';

export const INSERT_VIEW = 'INSERT INTO views (day, minute, path, code) VALUES (?1, ?2, ?3, ?4)';
/** ?1 a random key (worker.js `randomKey`): `searches` is ordered by it, so its rows keep no
 *  order of arrival (decisions 104; migrations/0001_init.sql). */
export const INSERT_SEARCH =
  'INSERT INTO searches (id, day, kind, lang, q, word, pos) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)';
export const INSERT_INSTALL =
  'INSERT INTO installs (day, n) VALUES (?1, 1) ON CONFLICT (day) DO UPDATE SET n = n + 1';

/** The days before ?1 (today) that have view lines but no totals yet: yesterday, normally, and
 *  any day a failed run left behind. */
export const DAYS_TO_TOTAL =
  'SELECT DISTINCT day FROM views WHERE day < ?1 AND day NOT IN (SELECT day FROM daily_views) ORDER BY day';

// Layer 6 (104): the codes of day ?1 with PACE_MAX or more views inside any PACE_MINUTES minutes
// (a sliding window over the minute of the day). Our constants, written into the text: SQLite
// wants the window's bound a constant.
const FAST = `fast AS (
  SELECT DISTINCT code FROM (
    SELECT code, count(*) OVER (PARTITION BY code ORDER BY minute
      RANGE BETWEEN ${PACE_MINUTES - 1} PRECEDING AND CURRENT ROW) AS c
    FROM views WHERE day = ?1)
  WHERE c >= ${PACE_MAX})`;

/** Day ?1's totals, the pace rule applied; what it left out stands beside them. */
export const TOTAL_DAY = `WITH ${FAST}
INSERT OR REPLACE INTO daily_views (day, views, readers, paced_codes, paced_views)
SELECT ?1,
  (SELECT count(*) FROM views WHERE day = ?1 AND code NOT IN (SELECT code FROM fast)),
  (SELECT count(DISTINCT code) FROM views WHERE day = ?1 AND code NOT IN (SELECT code FROM fast)),
  (SELECT count(*) FROM fast),
  (SELECT count(*) FROM views WHERE day = ?1 AND code IN (SELECT code FROM fast))`;

export const CLEAR_PATHS = 'DELETE FROM daily_paths WHERE day = ?1';
/** Day ?1's views per page, the same rule applied. */
export const TOTAL_PATHS = `WITH ${FAST}
INSERT INTO daily_paths (day, path, views)
SELECT ?1, path, count(*) FROM views
WHERE day = ?1 AND code NOT IN (SELECT code FROM fast)
GROUP BY path`;

/** Search lines older than ?1 (the first day kept) folded into counts: a line is kept only if
 *  its query string has been seen at least KEEP_MIN times — in all raw lines (the expiring ones
 *  and the RETAIN_DAYS after them) and in what was kept before (62). The language (`lang`, 148's
 *  follow-up) is not carried into the counts: the privacy page lists what a count keeps (the kind,
 *  the word chosen and its place), and it does not name the language. */
export const FOLD_SEARCHES = `INSERT INTO search_kept (kind, q, word, pos, n)
SELECT s.kind, s.q, IFNULL(s.word, ''), IFNULL(s.pos, 0), count(*) FROM searches s
WHERE s.day < ?1 AND
  (SELECT count(*) FROM searches t WHERE t.q = s.q)
  + IFNULL((SELECT sum(k.n) FROM search_kept k WHERE k.q = s.q), 0) >= ${KEEP_MIN}
GROUP BY s.kind, s.q, IFNULL(s.word, ''), IFNULL(s.pos, 0)
ON CONFLICT (kind, q, word, pos) DO UPDATE SET n = n + excluded.n`;
export const DELETE_SEARCHES = 'DELETE FROM searches WHERE day < ?1';
/** View lines older than ?1 (the first day kept by VIEW_DAYS, not RETAIN_DAYS), once totalled. */
export const DELETE_VIEWS = 'DELETE FROM views WHERE day < ?1';

// "Report a mistake" (site decisions 166): migrations/0002_reports.sql.
/** ?1 day, ?2 article, ?3 build, ?4 category, ?5 text, ?6 reply, ?7 credit (the name to credit). */
export const INSERT_REPORT =
  'INSERT INTO reports (day, article, build, category, text, reply, credit) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)';
/** The open reports, newest first, at most ?1. */
export const OPEN_REPORTS =
  'SELECT id, day, article, build, category, text, reply, credit FROM reports WHERE done IS NULL ORDER BY id DESC LIMIT ?1';
/** Report ?1 closed on day ?2 (Done or Fixed, scripts/reports_page.py): its reply address and the
 *  name to credit deleted, the rest kept. */
export const REPORT_DONE =
  'UPDATE reports SET done = ?2, reply = NULL, credit = NULL WHERE id = ?1 AND done IS NULL RETURNING id';
/** The total cap's counts of an hour before ?1 deleted. */
export const CLEAR_HOURS = 'DELETE FROM report_hours WHERE hour < ?1';
/** One more report in hour ?1, from anyone; the hour's count so far. */
export const COUNT_HOUR = `INSERT INTO report_hours (hour, n) VALUES (?1, 1)
ON CONFLICT (hour) DO UPDATE SET n = n + 1 RETURNING n`;

// The readers' survey (site decisions 173): migrations/0003_surveys.sql. Its cap is the reports'
// (COUNT_HOUR above): one count per hour for reports and answers together.
/** ?1 day, ?2 the answers (JSON text), ?3 the follow-up address or name. */
export const INSERT_SURVEY = 'INSERT INTO surveys (day, answers, follow) VALUES (?1, ?2, ?3)';
/** The open sets of answers, newest first, at most ?1. */
export const OPEN_SURVEYS =
  'SELECT id, day, answers, follow FROM surveys WHERE done IS NULL ORDER BY id DESC LIMIT ?1';
/** Answers ?1 marked done on day ?2 (Robin's page): the follow-up address or name deleted, the
 *  answers kept. */
export const SURVEY_DONE =
  'UPDATE surveys SET done = ?2, follow = NULL WHERE id = ?1 AND done IS NULL RETURNING id';
