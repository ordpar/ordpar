-- "Report a mistake" (site decisions 166, 2026-11-05): the reports readers send, and the total
-- cap's short-lived counts. Applied with
--   wrangler d1 migrations apply ordpar-events --remote      (on Robin's go; --local for tests)
-- What each holds and how long: ordpar/docs/receiver.md § Reports.
-- Amended in place by 166's follow-up (2026-11-05), before any deploy: the column `credit`, and
-- the per-sender table `report_rate` replaced by `report_hours` (the per-sender limit dropped,
-- Robin: "Yes, drop it"). The file has never been applied to a remote database.

-- One row per report: the UTC day it arrived, the article's id, the site's build (or none), the
-- category (or none), the text, the reply address (or none) and the name to credit (or none). No
-- address (IP), no browser name, no time of day. `done` is the day Robin closed it (Done or
-- Fixed, POST /reports/<id>/done), which deletes the reply address and the name; the rest is
-- kept, the record of what readers found (receiver.md § Reports).
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day TEXT NOT NULL,
  article INTEGER NOT NULL,
  build TEXT,
  category TEXT,
  text TEXT NOT NULL,
  reply TEXT,
  credit TEXT,
  done TEXT
);
CREATE INDEX IF NOT EXISTS reports_open ON reports (done, id);

-- The total cap (reports.js REPORTS_PER_HOUR): the number of reports accepted in each UTC hour,
-- from everyone together — the hour and a count, nothing about any sender. Rows of an earlier hour
-- are deleted at the next report and by the daily run, so the table holds at most the current
-- hour's. Never joined with `reports`.
CREATE TABLE IF NOT EXISTS report_hours (
  hour TEXT PRIMARY KEY,
  n INTEGER NOT NULL
) WITHOUT ROWID;
