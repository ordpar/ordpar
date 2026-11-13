# The receiver: counting, reports and the survey

Ordpar runs its own receiver rather than a third party's: a Cloudflare Worker on its free
`workers.dev` address ([26](../../docs/decisions.md#d26)). It does three things:

- **the counting**: page views, offline-app installs and search events, for daily reader numbers
  and the commonest searches and misses ([62](../../docs/decisions.md#d62),
  [104](../../docs/decisions.md#d104));
- **reports**: a reader's "Suggest a correction" on an article
  ([166](../../docs/decisions.md#d166));
- **the survey**: the readers' survey page's answers ([173](../../docs/decisions.md#d173)).

Where things are:

| Part | Where |
|---|---|
| the Worker: its files, tests and commands | `ordpar/receiver/` and its `ordpar/receiver/README.md` |
| the page's side of the counting | `ordpar/site/events.js` |
| the page's side of reports | `ordpar/site/report.js` |
| the page's side of the survey | `ordpar/site/survey.js`, `ordpar/sitegen/survey.py`, the questions in `ordpar/site/survey.json` |
| the words for readers | `ordpar/privacy.md`, published as `/privacy/` |
| how the build wires them in | `ordpar/docs/build-site.md` |

**What is on.** Reports and the survey are live. **The counting is off**, by two switches:

- on the site, `events.js`'s `RECEIVER` is empty, and while it is, the site sends nothing;
- on the Worker, `COUNTING` (`wrangler.jsonc` `vars`) is `"0"`. Then `/e` is not served (it answers
  400 and stores nothing) and the daily run makes no totals and makes or reads no secret.

So the Worker can serve reports and the survey while the counting stays off. Without the Worker's
switch, a Worker deployed for reports would store any well-formed event sent with the header
`Origin: https://ordpar.no`, which any program, not only a browser, can set.

## The counting

### What is collected

One endpoint, `POST /e`, one small JSON event per request, from `https://ordpar.no` only. The page
sends exactly these fields; the Worker drops any other before storage.

| Event | Sent when | Fields | Stored as |
|---|---|---|---|
| `view` | once per page, after 2 s visible or at the first scroll, tap or key | `path` (the path only) | `views`: day, minute of the day (UTC), path, the day's code |
| `install` | the offline app installed (`appinstalled`) | none | `installs`: a count per day |
| `hit` | a search the reader made found something (a Random word draw is not a search: no `hit` or `miss` for it) | `query`, `lang` | `searches`: day, `hit`, lang, query |
| `miss` | a search found nothing; sent when a similar word is chosen, or with none when the page is hidden, left, or a new search starts | `query`, `word`, `position` (or both null), `lang` | `searches`: day, `miss`, lang, query, word, position |
| `pick` | a suggestion chosen while typing (Enter or a press) | `query` (typed so far), `word`, `position`, `lang` | `searches`: day, `pick`, lang, query, word, position |

A chosen suggestion also runs a search, so it is counted as a `pick` and its search as a `hit` or
`miss`.

**The search's language.** The English search sends the same three events as the Norwegian one,
by the same rules, and every search event carries `lang`: `'en'` for the English search, `'nb'` for
the Norwegian one. The Worker stores it in `searches.lang`; a message without it is stored as
`'nb'` (a page from before the English search); any other value is refused (400). A view and an
install carry none (a `lang` sent with them is dropped). The language is **not carried into the
counts kept past 30 days** (`search_kept`): the privacy page lists what such a count keeps (the
kind, the words, the word chosen and its place), not the language, so English and Norwegian lines
of the same words fold into one count. Carrying it would need a column in `search_kept`, a line in
`FOLD_SEARCHES` and a sentence on the privacy page.

**Dropped** (answered 204, nothing stored):

- a query or word with a digit (in any script, `\p{N}`), a query over 40 characters, or a word
  over 60 (`MAX_QUERY`, `MAX_WORD`);
- anything from a crawler or a data-centre network (below);
- any request carrying `Sec-GPC: 1` (Global Privacy Control; the receiver checks it as well as the
  page).

A view's path that is not one of the site's own (`/`, `/bm-en/`, `/bm-en/<id>/`, `/about/`,
`/privacy/`, `/settings/`, `/favourites/`, `/history/`) is stored as `/other`, since a mistyped
address can hold a word. The page already sends it as `/other` (`events.js` `cleanPath`, the same
pattern as `rules.js` `PATH`). Queries and chosen words are stored NFC, spaces collapsed and
**lower-cased**, so *Hus* and *hus* are one string for the counts and the three-times rule.

**Refused** (400, no body, nothing echoed): another origin, another path or method, a body over
512 bytes, anything that is not one of the five events.

**Never sent, never stored:** an identifier of any kind, a cookie (`credentials: 'omit'`), the
page's full address (`referrerPolicy: 'no-referrer'`), the reader's IP address or the browser's
name. Search events carry no code and no time of day, and `searches` keeps **no order of
arrival**: each line is keyed by 32 random hex digits (`worker.js` `randomKey`) in a
`WITHOUT ROWID` table, so the rows sit in the key's order and no insertion-order `rowid` exists to
match against the view lines' minutes. No key links a search to page views. One way to date a line
remains: D1's Time Travel restores the database to any minute of the last 7 days, so comparing
restore points would show when a line arrived. Only the operator can do that, and it is not used.

**When the page sends nothing:** under `navigator.webdriver`, with no connection, with Global
Privacy Control or Do Not Track, while `RECEIVER` is empty, and when the reader has opted out. The
opt-out is one switch for everything: the setting "Send usage statistics" off (`stats` = `off` in
the browser's storage, `events.js` `optedOut`, read at every event) stops page views, searches,
suggestions chosen and installs alike; "Delete stored data" turns it back on. The setting shows in
Settings only while the counting is live (`chrome.counting()`, true exactly when `events.js`'s
`RECEIVER` is set); a stored Off is honoured either way. The receiver sees no difference: an
opted-out browser simply sends nothing. The installed app sends like the website while it has a
connection, and the privacy page says so.

### The daily code

For a `view` only: `HMAC-SHA-256(secret of the day, CF-Connecting-IP + "\n" + User-Agent)`, its
first 16 hex digits (`ordpar/receiver/src/code.js`). The IP address and the browser's name enter the hash and the
two bot checks and nothing else; the Worker has no `console` call, and Workers Logs are off.

**The secret** (`ordpar/receiver/src/secret.js`) is 32 random bytes in Workers KV under `secret:<YYYY-MM-DD>`. It is
in KV, not D1, because D1's Time Travel can restore a database's past state, and with it a deleted
secret. Each secret is written with an absolute `expiration` five minutes after its day ends (UTC),
and the daily run also deletes yesterday's explicitly. The daily run writes tomorrow's a day ahead,
so it has reached every location before it is used (KV can take 60 s or more to propagate a
change). Only if that failed does a request make today's itself; then two locations could each make
one, and a reader seen by both would count twice that day. Each isolate keeps the day's HMAC key in
memory, so KV is read about once per isolate per day.

**What the count means:** distinct codes in a day = readers that day. Two people behind one
address with the same browser count once; one person on two devices, or whose address changes
during the day, counts more than once. Codes cannot be linked across days, so there is **no weekly
or monthly unique-reader count**: only daily readers and their averages.

### Against bots: six layers

1. **Only the page's script sends**: a scraper without JavaScript sends nothing, and the Worker
   takes only `Origin: https://ordpar.no`.
2. **A kept crawler list**, matched against the User-Agent on the Worker:
   [monperrus/crawler-user-agents](https://github.com/monperrus/crawler-user-agents), under the MIT
   licence (`ordpar/receiver/data/crawlers.json`, 1,501 patterns, from upstream commit `9345a7ad`
   of 29 September 2026; its licence in `ordpar/receiver/data/crawlers.LICENSE.txt`). An empty
   User-Agent counts as a bot. The match costs about 0.2 ms per request.
3. **`navigator.webdriver`**: the page sends nothing, so automated browser tests send nothing either.
4. **Visible about 2 seconds**, or the first scroll, tap or key, before a view is sent; nothing while
   the page is hidden or prerendered.
5. **Data-centre networks skipped**, by `request.cf.asn` (which Workers get on every plan) against
   [brianhama/bad-asn-list](https://github.com/brianhama/bad-asn-list), under the MIT licence
   (`ordpar/receiver/data/datacentre-asns.json`, 723 networks, from upstream commit `b825d2e0` of
   12 April 2026; its licence in `ordpar/receiver/data/datacentre-asns.LICENSE.txt`). It holds the
   big clouds (AWS, Google, Microsoft, DigitalOcean, Hetzner, OVH …) and not Cloudflare, Akamai or
   Fastly, whose networks carry iCloud Private Relay. A reader on a VPN hosted in a data centre is
   skipped too.
6. **The pace rule at counting time**: a code with 100 or more views inside any 10 minutes (a window
   sliding by the minute) is left out of that day's totals. Its raw lines stay, and the totals
   record how many codes and views were left out. The constants are in `ordpar/receiver/src/rules.js` (`PACE_MAX`,
   `PACE_MINUTES`); a day can be totalled again while its lines are kept (below).

`ordpar/receiver/tools/refresh-lists.mjs` remakes both lists from their upstream files.

### Retention and the daily run

A Cron Trigger at **00:05 UTC** (`wrangler.jsonc`) runs `daily` (`ordpar/receiver/src/worker.js`). All its work is
SQL on D1's side, because a Cron Trigger has 10 ms of CPU on the Free plan and waiting on D1 does
not count. In order:

1. **the secret**: yesterday's deleted, today's and tomorrow's made if missing;
2. **totals** for every finished day not yet totalled (yesterday, or any day a failed run left):
   `daily_views` (views, readers, `paced_codes`, `paced_views`) and `daily_paths` (views per page),
   with the pace rule applied;
3. **retention**:
   - **view lines older than 1 day** before today are deleted (`VIEW_DAYS`). Their totals, made in
     step 2 first, stay. A day's view lines are each device's pages that day to the minute, a
     reading trail, so they are kept only through the next day, which leaves that day to total
     them again.
   - **search lines older than 30 days** (`RETAIN_DAYS`; a search can name something personal) are
     folded: a line is kept as a count in `search_kept` (kind, query, word, position, n; no date)
     only if its query string has been seen at least 3 times (`KEEP_MIN`) across all raw lines and
     what was kept before. The rest are deleted.
   - Installs are counts already, and kept.

Then, with the counting off or on, the total cap's counts of past hours are deleted (§ Reports).

| Table | Holds | Kept |
|---|---|---|
| `views` | day, minute, path, code | 1 day after its day |
| `searches` | random key, day, kind, language (`en` / `nb`), query, word, position | 30 days, then folded |
| `installs` | day, count | kept |
| `daily_views` | day, views, readers, paced codes and views | kept |
| `daily_paths` | day, path, views | kept |
| `search_kept` | kind, query, word, position, count (no language) | kept |

**Totalling a day again** (after changing the pace rule, while its lines are kept, that is through
the day after): delete its row from `daily_views` and its rows from `daily_paths`; the next run
totals it again.

### Reading the numbers

From `ordpar/receiver/`, with a Cloudflare API token in `CLOUDFLARE_API_TOKEN`. Every command below
only reads. The prefix is `npx wrangler d1 execute ordpar-events --remote --command` under Node
(see the README on Wrangler under bun). A number used outside the project, such as in a funding
application, should carry its method: daily distinct codes from a salted daily hash, the six
layers, and the known biases above.

| Number | `--command` |
|---|---|
| Readers and page views per day, last 30 days, with what the pace rule left out | `"SELECT day, readers, views, paced_codes, paced_views FROM daily_views ORDER BY day DESC LIMIT 30"` |
| Average daily readers and total views per month | `"SELECT substr(day,1,7) AS month, round(avg(readers)) AS daily_readers, sum(views) AS views FROM daily_views GROUP BY month ORDER BY month"` |
| Today so far (raw, before the pace rule) | `"SELECT count(*) AS views, count(DISTINCT code) AS readers FROM views WHERE day = date('now')"` |
| The most-viewed pages, last 30 days | `"SELECT path, sum(views) AS views FROM daily_paths WHERE day >= date('now','-30 days') GROUP BY path ORDER BY views DESC LIMIT 50"` |
| Installs per month | `"SELECT substr(day,1,7) AS month, sum(n) AS installs FROM installs GROUP BY month ORDER BY month"` |
| The commonest searches that found something, last 30 days | `"SELECT q, count(*) AS n FROM searches WHERE kind='hit' GROUP BY q ORDER BY n DESC LIMIT 50"` |
| The commonest misses, last 30 days | `"SELECT q, count(*) AS n FROM searches WHERE kind='miss' GROUP BY q ORDER BY n DESC LIMIT 50"` |
| The same for the English search only (`lang='nb'` for the Norwegian) | `"SELECT q, count(*) AS n FROM searches WHERE kind='miss' AND lang='en' GROUP BY q ORDER BY n DESC LIMIT 50"` |
| English and Norwegian searches per day | `"SELECT day, lang, count(*) AS n FROM searches WHERE kind IN ('hit','miss') GROUP BY day, lang ORDER BY day DESC, lang LIMIT 60"` |
| Misses and the similar word chosen, with its position | `"SELECT q, word, pos, count(*) AS n FROM searches WHERE kind='miss' AND word IS NOT NULL GROUP BY q, word, pos ORDER BY n DESC LIMIT 50"` |
| Misses where no similar word was chosen | `"SELECT q, count(*) AS n FROM searches WHERE kind='miss' AND word IS NULL GROUP BY q ORDER BY n DESC LIMIT 50"` |
| Suggestions chosen, by position | `"SELECT pos, count(*) AS n FROM searches WHERE kind='pick' GROUP BY pos ORDER BY pos"` |
| What was typed before a suggestion was chosen | `"SELECT q, word, pos, count(*) AS n FROM searches WHERE kind='pick' GROUP BY q, word, pos ORDER BY n DESC LIMIT 50"` |
| Searches past 30 days (counts, strings seen 3+ times) | `"SELECT kind, q, word, pos, n FROM search_kept ORDER BY n DESC LIMIT 50"` |

## Reports

A "Suggest a correction" button at the foot of each article opens a form where a reader can write
freely and point out a mistake in the translation, the audio or the Norwegian source, with an
optional reply address. The page's side is `ordpar/site/report.js`; the Worker's is
`ordpar/receiver/src/reports.js` and `ordpar/receiver/src/worker.js` `handleReport` and `handleReports`.

**`POST /report`**, from `https://ordpar.no` only (the same origin check as `/e`; `127.0.0.1` only
with `ALLOW_LOCAL`), a body of at most 16,384 bytes, one JSON message:

| Field | What | Refused (400) when |
|---|---|---|
| `id` | the article's id | not a whole number from 1 to 9,999,999 |
| `build` | the site's build id as the page read it (`/offline/version.json`), or null | not 6–40 hex digits |
| `category` | `translation`, `audio`, `norwegian`, `other`, or null | anything else |
| `text` | the reader's words, NFC, trimmed | empty, or over 2,000 characters (UTF-16 units, as the form's `maxlength`) |
| `reply` | an e-mail address, or null | over 254 characters, or not `x@y.z` in shape |
| `credit` | the name to credit, or null: trimmed, NFC, white space one space, control characters dropped | over 60 characters, or a link (`LINK`: `://`, `www.`, or a word ending in a common top-level domain) |
| `hp` | the hidden trap field, sent only when filled | (filled: answered 204, nothing stored) |

Any other field is ignored. Answers: **204** once stored (the answer waits for the write, so the
form's "sent" is true); **400** when it is not a report; **429** over the total cap; **503** when
D1 refused the write. None carries a body. The counting's rules do not apply: no `Sec-GPC` check,
no crawler or data-centre layer, and `COUNTING` is irrelevant, since a report is sent because the
reader pressed Send.

**The total cap**: at most **30 reports an hour (UTC) from everyone together**
(`REPORTS_PER_HOUR`), then 429 for every sender until the next hour. Nothing about the sender is
read for a report (not `CF-Connecting-IP`, not `User-Agent`, no code made from them), so reports
use no KV and no secret, and there is no per-sender limit. The count is one row per hour in
`report_hours` (hour, count), never joined with a report; the rows of earlier hours are deleted at
the next report and by the daily run (at the latest 00:05 UTC). Why 30: far above what a
dictionary's readers send by hand (a report takes a minute to write, and each is read by a
person), and low enough that a script past the trap adds at most 720 reports a day. The cost: a
flood fills the hour for everyone, and a real reader in that hour is asked to try again later
(their text is kept in the form).

**Stored** (`ordpar/receiver/migrations/0002_reports.sql`): `reports` holds id, the UTC day, article, build,
category, text, reply, credit and `done`. **No IP address, browser name or time of day.**

**The operator's two endpoints**, behind the Worker secret `REPORTS_TOKEN`
(`Authorization: Bearer <token>`; 401 without it, or when the secret is unset or under 16
characters; no CORS, so no web page can read them):

- `GET /reports`: the open reports, newest first, at most 500, as
  `{"reports": [{id, day, article, build, category, text, reply, credit}]}`;
- `POST /reports/<id>/done`: the report closed (`done` = the day), and its **reply address and name
  to credit deleted** (204; 404 when there is no open report of that id).

**After closing, the text is kept**, with the article, the category, the build and the days,
without the address: it is the record behind the dictionary's change list ("corrected thanks to a
reader's report") and a guard against fixing the same thing twice. Nothing deletes it
automatically; a reader's request to delete it is met by hand
(`DELETE FROM reports WHERE id = …`). D1's Time Travel can restore a deleted address for 7 days, as
any deletion there; the privacy page says so.

**Reading and closing reports.** The project reads them on a small local page in its private
repository, which calls the two endpoints with the token. Each report has two ways out: **Done**
(no fix) and **Fixed** (the report led to a fix). A fix is written to the committed list
`ordpar/reader-fixes.jsonl` (a new fix of the article, joined to an existing fix of it, or new fixes
of other articles too), with the reader's name only if the operator ticks Publish. Either way the
receiver then deletes the address and the name. A published name lives only in that list and is
taken off on its reader's request. While reports are on (`chrome.REPORT_RECEIVER`), the site build
makes the `/thanks/` page from the list (`ordpar/sitegen/thanks.py`).

| Reports | `--command` |
|---|---|
| Open reports, newest first | `"SELECT id, day, article, category, text FROM reports WHERE done IS NULL ORDER BY id DESC"` |
| Reports per month, by category | `"SELECT substr(day,1,7) AS month, category, count(*) AS n FROM reports GROUP BY month, category ORDER BY month"` |
| Articles reported more than once | `"SELECT article, count(*) AS n FROM reports GROUP BY article HAVING n > 1 ORDER BY n DESC"` |

## The survey

The readers' survey is Ordpar's own page, the one form besides "Suggest a correction". Its answers
come to this receiver as a second kind beside reports, under **the same total cap**, stored like
reports, with the same retention. The page's side is `ordpar/site/survey.js` and
`ordpar/sitegen/survey.py`; the Worker's, `ordpar/receiver/src/survey.js` and `ordpar/receiver/src/worker.js` `handleSurvey` and
`handleSurveys`.

**The receiver does not know the questions.** They, and the ideas listed, live in the site's data
file `ordpar/site/survey.json`, so they can be changed with a site build alone. The receiver takes
any question key of the agreed shape (`KEY`: a lower-case letter, then up to 39 lower-case letters,
digits or `_`) within its limits, and stores the answers as JSON text.

**`POST /survey`**, from `https://ordpar.no` only (the same origin check as `/report`), a body of at
most 131,072 bytes (`MAX_SURVEY_BODY`: every answer of the data file at its longest, six bytes a
character as JSON, stays well inside it, as `ordpar/receiver/test/survey.test.js` computes), one
JSON message:

| Field | What | Refused (400) when |
|---|---|---|
| `answers` | an object: question key → a text (NFC, trimmed, control characters but line breaks and tabs dropped) or a list of the choices ticked, as they read (each trimmed, white space one space, each once); an empty text or list is left out | not an object; over 40 keys (`MAX_QUESTIONS`); a key not of the shape; a text over 2,000 characters (`MAX_ANSWER`); over 20 choices (`MAX_CHOICES`) or a choice over 300 characters (`MAX_CHOICE`); any other value |
| `follow` | the follow-up e-mail address or name, or null: trimmed, NFC, white space one space, control characters dropped | not a string; over 254 characters (`MAX_FOLLOW`) |
| `hp` | the hidden trap field, sent only when filled | (filled: answered 204, nothing stored) |

Nothing answered and no follow-up is not a survey (400). Any other field is ignored. The answers
are as for `/report`: **204** once stored, **400**, **429** over the total cap, **503** when D1
refused the write. Nothing about the sender is read: the handler reads no header but `Origin` and
`Content-Length` (`takeMessage`, the one path for both kinds).

**The page's limits** (`survey.json`, each question's `max`): the one-line answers 100 or 200
characters, the text boxes 2,000, the follow-up 254; a choice is sent as it reads. The page cuts
nothing it shows: each field's `maxlength` is its `max`. `survey.check` in `ordpar/sitegen/survey.py` refuses a data file
beyond the receiver's limits, and the receiver's test holds the two together.

**The total cap is the reports' own**: `REPORTS_PER_HOUR` (30) an hour (UTC) **for reports and
survey answers together**, one count in `report_hours`, then 429 for every sender of either kind
until the next hour (`withinCap`, called by `takeMessage` for both).

**Stored** (`ordpar/receiver/migrations/0003_surveys.sql`): `surveys` holds id, the UTC day, `answers` (the JSON
text), `follow` and `done`. **No IP address, browser name, time of day, page address or build.**
The migration only adds a table and an index: nothing in `reports` or `report_hours` changes, and
a Worker deployed before it keeps working with it applied.

**The operator's two endpoints**, behind the same `REPORTS_TOKEN`:

- `GET /surveys`: the open answers, newest first, at most 500, as
  `{"surveys": [{id, day, answers, follow}]}` (`answers` the object);
- `POST /surveys/<id>/done`: the answers marked done (`done` = the day) and their **follow-up
  address or name deleted** (204; 404 when there are no open answers of that id).

**Retention, as for reports**: the answers are kept with no end date, as the record of what readers
asked for; the follow-up address or name is deleted once dealt with (marked Done after the
follow-up question was asked, or the decision made not to). D1's Time Travel can restore it for 7
days, as any deletion there; the privacy page says so. The reading page shows each set of answers
under its questions in the survey's order (a key the data file no longer has, under the key), with
Done and a Copy that copies the answers under their questions, never the follow-up address or name.

| Survey | `--command` |
|---|---|
| Open answers, newest first | `"SELECT id, day, answers FROM surveys WHERE done IS NULL ORDER BY id DESC"` |
| Answers per month | `"SELECT substr(day,1,7) AS month, count(*) AS n FROM surveys GROUP BY month ORDER BY month"` |
| How many chose each level | `"SELECT json_extract(answers, '$.level') AS level, count(*) AS n FROM surveys GROUP BY level ORDER BY n DESC"` |
