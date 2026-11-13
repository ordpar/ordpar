-- The readers' survey (site decisions 173, 2026-11-07): the answers readers send from the page
-- "Ordpar — your first impressions" (/survey/), a second kind beside reports. Applied with
--   wrangler d1 migrations apply ordpar-events --remote      (on Robin's go; --local for tests)
-- which applies this file alone on a database that has 0001 and 0002 (D1 records the files it has
-- applied in its own table, d1_migrations). It only adds a table: nothing in `reports` or
-- `report_hours` changes. What it holds and how long: ordpar/docs/receiver.md § The survey.
--
-- One row per set of answers: the UTC day it arrived, the answers (JSON text: question key -> the
-- text written, or the list of choices ticked; survey.js `parseSurvey`), and the follow-up address
-- or name (or none). No address (IP), no browser name, no time of day, no page address. `done` is
-- the day Robin marked the answers done (POST /surveys/<id>/done), which deletes `follow`; the
-- answers are kept, the record of what readers asked for. The total cap is reports' own
-- (`report_hours`): one count per hour for reports and answers together.
CREATE TABLE IF NOT EXISTS surveys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day TEXT NOT NULL,
  answers TEXT NOT NULL,
  follow TEXT,
  done TEXT
);
CREATE INDEX IF NOT EXISTS surveys_open ON surveys (done, id);
