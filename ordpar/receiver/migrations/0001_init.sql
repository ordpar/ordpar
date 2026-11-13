-- The receiver's tables (site decisions 26, 62, 104). Applied with
--   wrangler d1 migrations apply ordpar-events --remote      (on Robin's go; --local for tests)
-- What each holds and how long: ordpar/docs/receiver.md.

-- One line per page view: the UTC day, the minute of that day (for the pace rule, layer 6),
-- the page's path (26: the path only) and the day's scrambled code (104). Kept 7 days (104,
-- revised 2026-10-23 from 90), then only the totals below.
CREATE TABLE IF NOT EXISTS views (
  day TEXT NOT NULL,
  minute INTEGER NOT NULL,
  path TEXT NOT NULL,
  code TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS views_by_day ON views (day, code, minute);

-- One line per search event (62): kind 'hit' (query only), 'miss' (query, the similar word
-- chosen and its position, or none) or 'pick' (the text typed so far, the suggestion chosen,
-- its position); lang 'en' for the English search, 'nb' for the Norwegian one (site decisions
-- 148's follow-up, 2026-10-29); query and word lower-cased. No code, no time of day, and no order
-- of arrival (104, R4): keyed by 32 random hex digits (worker.js `randomKey`), WITHOUT ROWID, so
-- the rows sit in the key's order and there is no insertion-order rowid to match against the view
-- lines' minutes. Kept 90 days, then folded into search_kept (without lang). (Edited in place on
-- 2026-10-23, and again on 2026-10-29 for lang, before any database was created on Cloudflare,
-- rather than by a second migration.)
CREATE TABLE IF NOT EXISTS searches (
  id TEXT PRIMARY KEY,
  day TEXT NOT NULL,
  kind TEXT NOT NULL,
  lang TEXT NOT NULL DEFAULT 'nb',
  q TEXT NOT NULL,
  word TEXT,
  pos INTEGER
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS searches_by_day ON searches (day);
CREATE INDEX IF NOT EXISTS searches_by_q ON searches (q);

-- Installs of the offline app, a count per day (104: nothing identifying). Kept.
CREATE TABLE IF NOT EXISTS installs (
  day TEXT PRIMARY KEY,
  n INTEGER NOT NULL
);

-- The daily totals, made by the daily run from the raw lines, with the pace rule applied (layer
-- 6): views and readers (distinct codes) counted, and what the rule left out beside them. Kept.
CREATE TABLE IF NOT EXISTS daily_views (
  day TEXT PRIMARY KEY,
  views INTEGER NOT NULL,
  readers INTEGER NOT NULL,
  paced_codes INTEGER NOT NULL,
  paced_views INTEGER NOT NULL
);

-- Views per page per day, the same rule applied; no code. Kept.
CREATE TABLE IF NOT EXISTS daily_paths (
  day TEXT NOT NULL,
  path TEXT NOT NULL,
  views INTEGER NOT NULL,
  PRIMARY KEY (day, path)
);

-- Search lines past 90 days, as counts with no date, and only for query strings seen at least 3
-- times (62). word '' and pos 0 stand for "none".
CREATE TABLE IF NOT EXISTS search_kept (
  kind TEXT NOT NULL,
  q TEXT NOT NULL,
  word TEXT NOT NULL,
  pos INTEGER NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (kind, q, word, pos)
);
CREATE INDEX IF NOT EXISTS search_kept_by_q ON search_kept (q);
