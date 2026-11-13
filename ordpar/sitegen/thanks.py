# -*- coding: utf-8 -*-
"""The thanks page, `/thanks/` (site decisions 166, Robin 2026-11-05): "a reader who wants it is
credited by name on a page of its own", and "thanks to X number of reports that lead to Y number
of fixes"; since site decisions 183 (Robin, 2026-11-11) also readers' ideas. Built by
`build_site.py` from three files:

* **the list of fixes**, `ordpar/reader-fixes.jsonl` (`FIXES_PATH`), committed, one JSON line per
  fix, written ONLY by Robin's `/reports` page (`scripts/reports_page.py` `mark_fixed`,
  `unname` and `remove_fix`, through `scripts/serve.py`), as `order.rule` is the one writer of the deck's order:

      {"fix": 1, "date": "2026-11-05", "article": 1000, "reports": [4, 7], "names": ["Kari"]}

  `fix` the fix's own number (1, 2, …; one past the highest in the list, so a fix removed as a
  mistake, `remove_fix`, frees its number only when it was the last), `date` the day Robin closed the report as
  Fixed, `article` the article fixed, `reports` the receiver's ids of the reports behind it
  (several reports can lead to one fix, and one report to several fixes), `names` the names Robin
  published with it, each given by its reader for that (none: `[]`);
* **the list of ideas** (183), `ordpar/reader-ideas.jsonl` (`IDEAS_PATH`), committed, one JSON
  line per idea from a reader for making the dictionary or the Anki deck better that we have taken
  up or plan to, KEPT BY HAND by the session (ideas come from anywhere: mail, Reddit, the deck's
  reviews), never written by a tool:

      {"idea": 1, "date": "2026-11-11", "title": "…", "text": "…", "names": ["Moomoo"]}

  `idea` its own number (1, 2, …, distinct), `date` the day it went on the list, `title` and
  `text` plain text (escaped on output, no markup), `names` the readers to credit, each checked as
  a fix's (`clean_name`; none: `[]`), `credit` optional, "suggested" (the default) or "reported"
  (Robin, 2026-11-11: Moomoo credited for a report behind a change; `CREDITS`), no other keys. A bad line fails the build;
* **the words**, `ordpar/thanks.md`, in the About page's Markdown subset (`about.render`), with
  `{reports}` and `{fixes}` ("3 reports", "1 fix"), `[if fixes]…[/if]` and `[if no_fixes]…[/if]`,
  and `{list}`, a paragraph of its own that becomes the list of fixes; `[if ideas]…[/if]`, kept
  while there is an idea (around the heading "Ideas from our readers" and its list), and
  `{ideas}`, a paragraph of its own that becomes the list of ideas.

Both numbers are counted here, at build time, from the file: X the distinct report ids, Y the
lines — so they are always true (standing.md, "state only true things"). The list: newest first,
each fix's word (the article's headword, linked to its page), its date, and the names, or "a
reader" (one report) / "readers" (several) when none was published. The ideas: newest first, by
(date, idea), in the same list class; each the title in bold with a colon, the text, and on a line
of its own "Suggested by" the names, or "a reader" when none.
"""
import datetime
import html
import io
import json
import os
import re
import unicodedata

from . import about

ORDPAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The committed list of fixes; `ORDPAR_FIXES_FILE` names another (the tests)
FIXES_PATH = os.path.join(ORDPAR, "reader-fixes.jsonl")
SOURCE = os.path.join(ORDPAR, "thanks.md")
#: The page's address (`chrome.THANKS_HREF` is the same)
HREF = "/thanks/"
#: The longest name to credit, as the receiver's `MAX_CREDIT` (`ordpar/receiver/src/reports.js`)
MAX_NAME = 60
#: A link in a name: the receiver's `LINK` (`reports.js`), the same pattern
LINK = re.compile(r"://|www\.|\.(com|net|org|info|biz|io|co|me|app|dev|xyz|top|site|online|shop"
                  r"|ru|cn|de|uk|no|se|dk)\b", re.I)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LIST = "<p>{list}</p>"
_IDEAS = "<p>{ideas}</p>"
#: The committed list of readers' ideas, kept by hand (site decisions 183); `ORDPAR_IDEAS_FILE`
#: names another (the tests)
IDEAS_PATH = os.path.join(ORDPAR, "reader-ideas.jsonl")
_IDEA_KEYS = ("idea", "date", "title", "text", "names", "credit")
#: An idea's optional `credit` (Robin, 2026-11-11: Moomoo credited for a report, not an idea):
#: the words before the names; "suggested" when the key is left out
CREDITS = {"suggested": "Suggested by", "reported": "Reported by"}
#: When no name was published: one report, several (drafts for Robin)
A_READER, READERS = "a reader", "readers"


def fixes_path():
    return os.environ.get("ORDPAR_FIXES_FILE") or FIXES_PATH


def ideas_path():
    return os.environ.get("ORDPAR_IDEAS_FILE") or IDEAS_PATH


def clean_name(value):
    """A name as published: the receiver's `cleanCredit` (white space one space, control characters
    dropped, trimmed); None when empty, too long or a link."""
    if not isinstance(value, str):
        return None
    s = unicodedata.normalize("NFC", value)
    s = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", s)).strip()
    if not s or len(s) > MAX_NAME or LINK.search(s):
        return None
    return s


def _check_date(date, where):
    if not (isinstance(date, str) and _DATE.match(date)):
        raise ValueError("%s: date must be YYYY-MM-DD" % where)
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise ValueError("%s: date %s is not a day" % (where, date))


def _check_names(names, where):
    if not (isinstance(names, list) and all(clean_name(n) == n for n in names)):
        raise ValueError("%s: names must be a list of names (no links, at most %d characters)"
                         % (where, MAX_NAME))


def check_line(o, where="reader-fixes.jsonl"):
    """One fix as read, or ValueError saying what is wrong with it."""
    if not isinstance(o, dict):
        raise ValueError("%s: not an object" % where)
    fix, date, art = o.get("fix"), o.get("date"), o.get("article")
    reports, names = o.get("reports"), o.get("names")
    if not (isinstance(fix, int) and fix >= 1):
        raise ValueError("%s: fix must be a whole number from 1" % where)
    _check_date(date, where)
    if not (isinstance(art, int) and art >= 1):
        raise ValueError("%s: article must be a whole number from 1" % where)
    if not (isinstance(reports, list) and reports
            and all(isinstance(r, int) and r >= 1 for r in reports)
            and len(set(reports)) == len(reports)):
        raise ValueError("%s: reports must be a list of distinct report ids" % where)
    _check_names(names, where)
    return {"fix": fix, "date": date, "article": art, "reports": list(reports), "names": list(names)}


def check_idea(o, where="reader-ideas.jsonl"):
    """One idea as read (site decisions 183), or ValueError saying what is wrong with it."""
    if not isinstance(o, dict):
        raise ValueError("%s: not an object" % where)
    other = sorted(set(o) - set(_IDEA_KEYS))
    if other:
        raise ValueError("%s: unknown key %s (only %s)"
                         % (where, ", ".join(other), ", ".join(_IDEA_KEYS)))
    idea = o.get("idea")
    if not (isinstance(idea, int) and not isinstance(idea, bool) and idea >= 1):
        raise ValueError("%s: idea must be a whole number from 1" % where)
    _check_date(o.get("date"), where)
    for key in ("title", "text"):
        if not (isinstance(o.get(key), str) and o[key].strip()):
            raise ValueError("%s: %s must be a non-empty string" % (where, key))
    _check_names(o.get("names"), where)
    out = {"idea": idea, "date": o["date"], "title": o["title"], "text": o["text"],
           "names": list(o["names"])}
    if "credit" in o:
        if not (isinstance(o["credit"], str) and o["credit"] in CREDITS):
            raise ValueError("%s: credit must be one of %s" % (where, ", ".join(CREDITS)))
        out["credit"] = o["credit"]
    return out


def read_fixes(path=None):
    """Every fix in the file, in its order; [] when the file is missing or empty. ValueError on a
    line that is not a fix, or a fix number used twice."""
    return _read_lines(path or fixes_path(), check_line, "fix")


def read_ideas(path=None):
    """Every idea in the file (site decisions 183), in its order; [] when the file is missing or
    empty. ValueError on a line that is not an idea, or an idea number used twice."""
    return _read_lines(path or ideas_path(), check_idea, "idea")


def _read_lines(path, check, key):
    """The file's lines, each through `check(o, where)`, its number `key` distinct."""
    try:
        with io.open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return []
    out, seen = [], set()
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = "%s line %d" % (os.path.basename(path), i)
        try:
            o = json.loads(line)
        except ValueError as exc:
            raise ValueError("%s: not JSON (%s)" % (where, exc))
        item = check(o, where)
        if item[key] in seen:
            raise ValueError("%s: %s %d twice" % (where, key, item[key]))
        seen.add(item[key])
        out.append(item)
    return out


def line_text(fix):
    """One fix as its line in the file: the keys in a fixed order, UTF-8 as it is."""
    return json.dumps({"fix": fix["fix"], "date": fix["date"], "article": fix["article"],
                       "reports": fix["reports"], "names": fix["names"]}, ensure_ascii=False)


def counts(fixes):
    """(X, Y): the distinct reports that led to a fix, and the fixes."""
    return len({r for f in fixes for r in f["reports"]}), len(fixes)


def _noun(n, one, many):
    return "1 %s" % one if n == 1 else "{:,} {}".format(n, many)


def who(fix):
    """The names, "Kari", "Kari and Ola", "Kari, Ola and Per"; or "a reader" / "readers"."""
    if not fix["names"]:
        return A_READER if len(fix["reports"]) == 1 else READERS
    return join_names(fix["names"])


def join_names(names):
    """"Kari", "Kari and Ola", "Kari, Ola and Per"; '' for none."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def newest_first(fixes):
    return sorted(fixes, key=lambda f: (f["date"], f["fix"]), reverse=True)


def list_html(fixes, headword):
    """The fixes as `<ul class="ordpar-thanks-list">`, newest first; '' when there is none.
    `headword(article)` gives the article's headword as text ("lek III"), or None ("#1234")."""
    if not fixes:
        return ""
    items = []
    for f in newest_first(fixes):
        word = headword(f["article"]) or "#%d" % f["article"]
        items.append('<li><a href="/bm-en/%d/" lang="nb">%s</a>, %s, from %s</li>'
                     % (f["article"], html.escape(word, quote=False),
                        about.snapshot_date(f["date"]), html.escape(who(f), quote=False)))
    return '<ul class="ordpar-thanks-list">\n%s\n</ul>' % "\n".join(items)


def ideas_html(ideas):
    """The ideas (site decisions 183) as `<ul class="ordpar-thanks-list ordpar-thanks-ideas">` (the
    second class for half a line between ideas, Robin 2026-11-11), newest first by
    (date, idea); '' when there is none. Each: the title in bold with its colon, the text, and on a
    line of its own "Suggested by" the names (`join_names`), or "a reader": a span
    `ordpar-thanks-credit` that the page's sheet sets as a block, italic, led by an en dash
    (Robin's pick in the credit lab, 2026-11-11; `page.PAGE_CSS`). The space before it keeps the
    words apart where no sheet applies."""
    if not ideas:
        return ""
    items = []
    for i in sorted(ideas, key=lambda i: (i["date"], i["idea"]), reverse=True):
        items.append('<li><strong>%s:</strong> %s <span class="ordpar-thanks-credit">%s %s</span></li>'
                     % (html.escape(i["title"], quote=False), html.escape(i["text"], quote=False),
                        CREDITS[i.get("credit", "suggested")],
                        html.escape(join_names(i["names"]) or A_READER, quote=False)))
    return '<ul class="ordpar-thanks-list ordpar-thanks-ideas">\n%s\n</ul>' % "\n".join(items)


def fill(text, fixes, ideas=()):
    """`thanks.md` with its marks resolved (the comment, `[if]`, `{reports}`, `{fixes}`); `{list}`
    and `{ideas}` are left for `page`. `[if ideas]` is kept while there is an idea (183)."""
    x, y = counts(fixes)
    nums = {"fixes": (y, _noun(y, "fix", "fixes")), "no_fixes": (0 if y else 1, ""),
            "reports": (x, _noun(x, "report", "reports")), "ideas": (len(ideas), "")}
    text = about._COMMENT.sub("", text, count=1)

    def cond(m):
        if m.group(1) not in nums:
            raise KeyError("thanks.md: unknown number in [if %s]" % m.group(1))
        return m.group(2) if nums[m.group(1)][0] else ""
    text = about._IF.sub(cond, text)

    def field(m):
        if m.group(1) in ("list", "ideas"):
            return m.group(0)
        if m.group(1) not in nums:
            raise KeyError("thanks.md: unknown number {%s}" % m.group(1))
        return nums[m.group(1)][1]
    text = about._FIELD.sub(field, text)
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n") + "\n"


def page(fixes, headword, source=None, ideas=()):
    """The page's parts, (title, body HTML): `thanks.md` filled and rendered, `{list}` the list of
    fixes, `{ideas}` the list of ideas (183; as `fixes`, given by the caller: `build_site.write_thanks`
    reads the committed file, `read_ideas`)."""
    text = fill(about.read_source(SOURCE) if source is None else source, fixes, ideas)
    title, body = about.render(text, what="thanks.md")
    if _LIST not in body:
        raise ValueError("thanks.md: no {list} paragraph")
    if ideas and _IDEAS not in body:
        raise ValueError("thanks.md: no {ideas} paragraph")
    for mark, lst in ((_LIST, list_html(fixes, headword)), (_IDEAS, ideas_html(ideas))):
        if lst:
            body = body.replace(mark, lst)
        else:
            body = body.replace(mark + "\n", "").replace("\n" + mark, "").replace(mark, "")
    return title, body


def mirror_headword(mirror):
    """`headword(article)` over the mirror (`mirror.Mirror`): the article's spellings with their
    homograph numerals, as the page's title gives them ("lysing I, lysning II"); None when the
    mirror has no such article."""
    from . import deck

    def headword(aid):
        data = mirror.data(aid)
        lemmas = (data or {}).get("lemmas") or []
        parts = []
        for lem in lemmas:
            w = deck.derive._norm_lemma(lem.get("lemma") or "")
            if not w:
                continue
            n = lem.get("hgno") or 0
            parts.append(w + (" " + deck.derive._roman(n) if n else ""))
        return ", ".join(parts) or None
    return headword
