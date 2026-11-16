# -*- coding: utf-8 -*-
"""The readers' survey (site decisions 173, Robin 2026-11-07): the page `/survey/`, "Ordpar — your
first impressions", our own in place of the Google form (decisions 72), kept after launch; the one
form readers fill in besides "Suggest a correction".

ONE data file holds its words, its questions and the ideas listed: `ordpar/site/survey.json`
(`read`, `check`), so Robin can change them as ideas get built without touching code. This module
renders the page's body from it (`body`), in the About page's frame (`page.survey_page`); the
page's script, `ordpar/site/survey.js`, sends the answers to the receiver (`POST /survey`) and hides
a question while the answer that skips it is chosen (`skip_if`). The receiver does not know the
questions: it takes any key of the agreed shape within its limits (`ordpar/receiver/src/survey.js`).

The page is built only while the survey's switch is on (`chrome.SURVEY`, `chrome.survey_receiver()`);
it is `noindex` and not in the sitemap or the offline copy (it needs a connection to send).

The markup, every question in one form (one page, so the part numbers of the Google form are
gone): each question a `<div data-q="<id>" data-kind="<kind>">` — a `one` question a `<fieldset>`
of radio buttons, a `many` question one of check boxes, a `short` question a one-line field, a
`long` one a text box, the `follow` question a one-line field sent apart from the answers — with its
label, its hint (`aria-describedby`) and its `maxlength` from the data file; a question with
`skip_if` carries `data-skip-q` / `data-skip-v`. Then the hidden trap field, the status line, Send,
the line shown after a send, and the words for the script as a JSON island.
"""
import html
import json
import os
import re

SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "survey.json")
#: The receiver's limits (ordpar/receiver/src/survey.js); `check` refuses a data file beyond them,
#: and the receiver's own test holds the two files together
MAX_ANSWER = 2000
MAX_CHOICE = 300
MAX_CHOICES = 20
MAX_QUESTIONS = 40
MAX_FOLLOW = 254
KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
KINDS = ("one", "many", "short", "long", "follow")
#: The words the page's script needs (`survey.js` `t`)
WORDS = ("form", "send", "sending", "sent", "empty", "offline", "failed", "tooMany", "noscript", "trap")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def read(path=None):
    """The data file, checked (`check`)."""
    with open(path or SOURCE, encoding="utf-8") as f:
        return check(json.load(f))


def check(data):
    """`data` if it is a survey the page and the receiver can both take, else ValueError naming the
    first fault: a title and intro; each question a known kind with a unique key of the receiver's
    shape, a label, choices for `one`/`many` (each within MAX_CHOICE, at most MAX_CHOICES), a `max`
    for the texts within MAX_ANSWER (the follow-up's exactly MAX_FOLLOW), exactly one follow-up
    question, last; a `skip_if` naming an earlier `one` question and one of its choices; every word
    the script needs."""
    def fail(msg):
        raise ValueError("survey.json: " + msg)
    if not isinstance(data, dict) or not data.get("title") or not data.get("intro"):
        fail("needs a title and an intro")
    if "note" in data and (not isinstance(data["note"], str) or not data["note"].strip()):
        fail("the note, when given, is a line of text")
    qs = data.get("questions")
    if not isinstance(qs, list) or not qs or len(qs) > MAX_QUESTIONS:
        fail("needs 1 to %d questions" % MAX_QUESTIONS)
    seen = {}
    for i, q in enumerate(qs):
        qid = q.get("id") if isinstance(q, dict) else None
        if not isinstance(qid, str) or not KEY.match(qid) or qid in seen:
            fail("question %d: the key %r is not a new key of the receiver's shape" % (i + 1, qid))
        kind = q.get("kind")
        if kind not in KINDS:
            fail("%s: unknown kind %r" % (qid, kind))
        if not q.get("label"):
            fail("%s: no label" % qid)
        if kind in ("one", "many"):
            ch = q.get("choices")
            if (not isinstance(ch, list) or not ch or len(ch) > MAX_CHOICES or len(set(ch)) != len(ch)
                    or any(not isinstance(c, str) or not c.strip() or len(c) > MAX_CHOICE for c in ch)):
                fail("%s: its choices must be 1 to %d different texts of at most %d characters"
                     % (qid, MAX_CHOICES, MAX_CHOICE))
        else:
            mx = q.get("max")
            limit = MAX_FOLLOW if kind == "follow" else MAX_ANSWER
            if not isinstance(mx, int) or isinstance(mx, bool) or mx < 1 or mx > limit or (kind == "follow" and mx != limit):
                fail("%s: max must be %s" % (qid, ("exactly %d" % limit) if kind == "follow"
                                                  else "1 to %d" % limit))
        skip = q.get("skip_if")
        if skip is not None:
            if not isinstance(skip, dict) or len(skip) != 1:
                fail("%s: skip_if names one question and one choice" % qid)
            (other, choice), = skip.items()
            if other not in seen or seen[other].get("kind") != "one" or choice not in seen[other]["choices"]:
                fail("%s: skip_if must name an earlier one-choice question and one of its choices" % qid)
        seen[qid] = q
    follows = [q for q in qs if q["kind"] == "follow"]
    if len(follows) != 1 or qs[-1]["kind"] != "follow":
        fail("exactly one follow-up question, the last")
    w = data.get("words") or {}
    missing = [k for k in WORDS if not w.get(k)]
    if missing:
        fail("words missing: %s" % ", ".join(missing))
    return data


def _e(text):
    return html.escape(text or "", quote=False)


def _a(text):
    return html.escape(text or "", quote=True)


def inline(text):
    """A paragraph's text: escaped, `[text](href)` a link."""
    out, at = [], 0
    for m in _LINK.finditer(text):
        out.append(_e(text[at:m.start()]))
        out.append('<a href="%s">%s</a>' % (_a(m.group(2)), _e(m.group(1))))
        at = m.end()
    out.append(_e(text[at:]))
    return "".join(out)


def _question(q):
    qid, kind = q["id"], q["kind"]
    pre = "ordpar-survey-" + qid.replace("_", "-")
    attrs = ' data-q="%s" data-kind="%s"' % (qid, kind)
    skip = q.get("skip_if")
    if skip:
        (other, choice), = skip.items()
        attrs += ' data-skip-q="%s" data-skip-v="%s"' % (_a(other), _a(choice))
    hint_id = pre + "-hint"
    hint = ('<p class="ordpar-report-hint" id="%s">%s</p>\n' % (hint_id, _e(q["hint"]))) if q.get("hint") else ""
    described = (' aria-describedby="%s"' % hint_id) if hint else ""
    if kind in ("one", "many"):
        typ = "radio" if kind == "one" else "checkbox"
        items = "".join(
            '<label class="ordpar-survey-choice"><input type="%s" name="%s" value="%s"> %s</label>\n'
            % (typ, qid, _a(c), _e(c)) for c in q["choices"])
        return ('<div class="ordpar-survey-q"%s>\n<fieldset%s>\n<legend class="ordpar-report-label">%s</legend>\n'
                '%s%s</fieldset>\n</div>\n' % (attrs, described, _e(q["label"]), hint, items))
    if kind == "long":
        field = ('<textarea class="ordpar-report-text" id="%s" name="%s" rows="4" maxlength="%d"%s></textarea>'
                 % (pre, qid, q["max"], described))
    else:
        auto = ' autocomplete="email"' if kind == "follow" else ""
        field = ('<input class="ordpar-report-reply" type="text" id="%s" name="%s" maxlength="%d"%s%s>'
                 % (pre, qid, q["max"], auto, described))
    return ('<div class="ordpar-survey-q"%s>\n<label class="ordpar-report-label" for="%s">%s</label>\n%s%s\n</div>\n'
            % (attrs, pre, _e(q["label"]), hint, field))


def body(data=None):
    """The page's parts, (title, body HTML), from the data file (`read`): the intro's paragraphs,
    then the form."""
    data = read() if data is None else check(data)
    w = data["words"]
    # the note (optional in the data file): first under the title, in bold (decisions 173:
    # a note at the top that each field is optional)
    note = data.get("note")
    intro = ('<p class="ordpar-survey-note"><strong>%s</strong></p>\n' % inline(note)) if note else ""
    intro += "".join("<p>%s</p>\n" % inline(p) for p in data["intro"])
    qs = "".join(_question(q) for q in data["questions"])
    island = json.dumps({k: w[k] for k in WORDS}, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    form = (
        '<form class="ordpar-survey" id="ordpar-survey" aria-label="%(form)s" novalidate data-nosnippet>\n'
        '<noscript><p class="ordpar-report-status ordpar-report-status--failed">%(noscript)s</p></noscript>\n'
        '%(qs)s'
        '<div class="ordpar-report-trap" aria-hidden="true"><label for="ordpar-survey-hp">%(trap)s</label>'
        '<input type="text" id="ordpar-survey-hp" name="website" tabindex="-1" autocomplete="off"></div>\n'
        '<p class="ordpar-report-status ordpar-survey-status" role="status"></p>\n'
        '<p class="ordpar-report-actions"><button type="submit" class="ordpar-result-btn ordpar-report-send '
        'ordpar-survey-send">%(send)s</button></p>\n'
        '</form>\n'
        '<p class="ordpar-survey-done" id="ordpar-survey-done" role="status" tabindex="-1" hidden></p>\n'
        '<script type="application/json" id="ordpar-survey-words">%(island)s</script>\n'
        % {"form": _a(w["form"]), "noscript": _e(w["noscript"]), "qs": qs, "trap": _e(w["trap"]),
           "send": _e(w["send"]), "island": island})
    return data["title"], intro + form
