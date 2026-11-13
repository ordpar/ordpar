# -*- coding: utf-8 -*-
"""The About page and the published repository's README, from ONE source text, `ordpar/about.md`
(site decisions 63, Robin 2026-10-22: "making the README and the about page identical (since they
basically serve the same purpose)"; agreed: one source, so the two cannot drift). The approved text
is `docs/sessions/2026-09-19-ordpar-site-review/walk-through/about-page-final-2026-10-22.md`.

The source is Markdown, so the README is the source itself with its few build marks resolved, and
the page is a small renderer over the same lines. The subset:

* a leading `<!-- … -->` comment is the file's own note, dropped from both;
* `# Title` — the page's `<h1>` and `<title>`, the README's first line;
* `## Heading` — a section heading (`<h2>` on the page, with an id from its words since site
  decisions 131 — "Contact" -> `#contact`, which the deck's AnkiWeb page links — as the Help
  page's; on the privacy page with an index of them before the first — decisions 104,
  `privacy_page`);
* any other block, separated by a blank line, is a paragraph: `**bold**`, `*italic*` and
  `[text](url)` inside it (a link to the CC BY 4.0 deed gets `rel="license"` on the page; a
  `mailto:` address is a link like any other). `*italic*` since site decisions 131 (2026-10-26:
  the deck's name under "Thanks", the "*Waiting for:*" lines of `/coming/`);
* `{name}` — a number the build fills (`numbers`): `articles` (the shown article total, rounded to
  the nearest hundred), `translated`, `complete`, `no_summary`, `words_share` (the share of the
  text by running words, a whole percent), `added_sentences`, `added_articles`;
* `[if name]…[/if]` — kept only while the number `name` is not zero (the "…: N complete, … their
  summary still to come" clause, which goes by itself once every translated article has its
  summary; Robin 2026-10-22: "It would just dissapear the day we get the library upto date");
  two are switches, not counts: `privacy` (`chrome.PRIVACY`, decisions 104) and `reports` (the
  reports' switch, `chrome.REPORT_RECEIVER`, site decisions 166: the paragraph thanking the
  readers who report mistakes, true only while they can);
* `[readme]…[/readme]` — lines the README carries and the page does not (the note on the
  repository's own files, in the approved README's words).
* a block whose every line starts `- ` is a bulleted list (`<ul>` on the page), each line an item
  (decisions 106, Robin 2026-10-23: "What Ordpar has changed" as "a concise bulleted list of every
  type of change + the count"); since site decisions 175 (2026-11-07) an item may wrap onto lines
  indented by spaces, its own words joined into it (the change lists' entries are written so).

The changes' counts (decisions 106) are the change notice's own: `corrections.Checker` counts every
live correction of the normalization log the pages show, the build puts its About buckets in
`stats["corrections"]` and the mirror snapshot's date in `stats["snapshot"]`, and they are filled as
`corr_xref`, `corr_spelling`, `corr_headorder`, `corr_other` (corrections), `corr_*_articles`
("80 articles", "1 article" — the noun with its number), `corr_other_kinds` (the rest's kinds in
the notice's own phrases), `corr_articles` and `snapshot_date` ("25 September 2026"). A build
record without them (before decisions 106) fills zeros and an empty date, so their lines drop.

The numbers are `ordpar/site_stats.py` `measure()`'s, taken by `build_site.py` over the rows the
pages are built from and recorded in `out/build.json` (`site_stats`); `deploy.py` reads them back
from there, so the README names the numbers of the build it publishes.
"""
import html
import io
import os
import re

SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "about.md")
#: The privacy page's text (site decisions 104's box, item 5), in the same Markdown subset but with
#: no build numbers: `privacy_page`. A `[[…]]` is a placeholder still to be filled (a legal
#: sentence, the receiver's address); the build refuses the page while one is left.
PRIVACY_SOURCE = os.path.join(os.path.dirname(SOURCE), "privacy.md")
#: The Help page's text (site decisions 123 as amended, Robin 2026-10-24): `/help/`
HELP_SOURCE = os.path.join(os.path.dirname(SOURCE), "help.md")
#: The "Coming to Ordpar" page's text (site decisions 131, 2026-10-25/26): `/coming/`
COMING_SOURCE = os.path.join(os.path.dirname(SOURCE), "coming.md")
#: The page "More ways to use Ordpar" (site decisions 142, Robin 2026-10-26/27): `/more/`
MORE_SOURCE = os.path.join(os.path.dirname(SOURCE), "more.md")
#: The three change lists as public pages (site decisions 175, Robin 2026-11-07: "I want it
#: public", "Yes, both public"; 177: the decks' list, "Yes, both"): the site's (`/changes/`), the
#: dictionary's (`/dictionary-changes/`), the Anki decks' (`/deck-changes/`). Their words are written
#: elsewhere (the deploy's change-list step; the deck session for the decks') and never edited by
#: the build: what they hold, the renderer learns.
CHANGES_SOURCE = os.path.join(os.path.dirname(SOURCE), "changes.md")
LIBRARY_CHANGES_SOURCE = os.path.join(os.path.dirname(SOURCE), "library-changes.md")
DECK_CHANGES_SOURCE = os.path.join(os.path.dirname(SOURCE), "deck-changes.md")
#: A heading's fixed id, written after its words: `## Practise the words in Anki {#anki}` (site
#: decisions 142: the sections' addresses `#popup`, `#anki`, `#offline`, which the words alone
#: would not give)
_FIXED_ID = re.compile(r"\s*\{#([a-z0-9-]+)\}\s*$")
#: A numbered step, "1. " at the start of a line (site decisions 142)
_STEP = re.compile(r"^(\d+)\. ")
#: A line of code under a step: indented, wholly in backticks (the Definer URL and CSS)
_CODE_LINE = re.compile(r"^\s+`([^`]+)`\s*$")
_PLACEHOLDER = re.compile(r"\[\[.*?\]\]", re.S)
LICENCE = "https://creativecommons.org/licenses/by/4.0/"

_COMMENT = re.compile(r"\A\s*<!--.*?-->\s*", re.S)
_README = re.compile(r"\[readme\]\n?(.*?)\[/readme\]\n?", re.S)
_IF = re.compile(r"\[if (\w+)\](.*?)\[/if\]", re.S)
_FIELD = re.compile(r"\{(\w+)\}")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
#: `*italic*` (site decisions 131): one star at each end, hugging the words, never one of a `**`
#: pair (bold is resolved first on the page; `plain` drops both)
_ITALIC = re.compile(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])")

#: Example numbers for the tests and a quick preview — never what the build ships.
SAMPLE = {"articles": {"all": 94197, "translated": 21873, "complete": 10132,
                       "no_summary": 11741},
          "words": {"all": 1365856, "translated": 495400, "share": 495400 / 1365856},
          "added": {"sentences": 450, "articles": 271},
          "corrections": {"about": {"xref": {"corrections": 82, "articles": 80},
                                    "spelling": {"corrections": 99, "articles": 97},
                                    "headorder": {"corrections": 4, "articles": 4},
                                    "other": {"corrections": 5, "articles": 5}},
                          "other": [["form", 1], ["compounds", 1], ["misplaced", 1],
                                    ["setphrase", 1], ["anchor", 1]],
                          "articles": 185},
          "snapshot": "2026-09-25T01:15:52.933826663+00:00"}


def read_source(path=SOURCE):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def numbers(stats, reports=None):
    """`site_stats.measure()`'s counts as the text shows them: {name: (value, shown)}. The
    article total rounds to the nearest hundred ("94,200"), the rest are exact ("21,873"), the
    text share a whole percent ("36 %"). `reports`: are reports on (site decisions 166)? Default:
    the reports' switch, `chrome.REPORT_RECEIVER`; `deploy.py` passes the published build's own
    (`build.json` `reports_166`), so the README says what that build's pages say."""
    art, words, added = stats["articles"], stats["words"], stats["added"]
    whole = int(art["all"] + 50) // 100 * 100
    pct = int(100 * words["share"] + 0.5)
    raw = {"articles": whole, "translated": art["translated"], "complete": art["complete"],
           "no_summary": art["no_summary"], "added_sentences": added["sentences"],
           "added_articles": added["articles"]}
    out = {k: (v, "{:,}".format(v)) for k, v in raw.items()}
    out["words_share"] = (pct, "%d %%" % pct)
    # site decisions 104: the line on the privacy page, kept while its switch is on
    from . import chrome
    out["privacy"] = (1 if chrome.PRIVACY else 0, "")
    # site decisions 166: the paragraph thanking the readers who report mistakes, kept while the
    # reports' switch is on
    on = bool(chrome.REPORT_RECEIVER) if reports is None else bool(reports)
    out["reports"] = (1 if on else 0, "")
    out.update(_corrections(stats))
    return out


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")


def snapshot_date(stamp):
    """The mirror manifest's `created_at` ("2026-09-25T01:15:52…") as the page writes a date:
    "25 September 2026"; "" when it is missing or not a date."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", stamp or "")
    if not m or not 1 <= int(m.group(2)) <= 12:
        return ""
    return "%d %s %s" % (int(m.group(3)), _MONTHS[int(m.group(2)) - 1], m.group(1))


def _articles(n):
    return (n, "1 article" if n == 1 else "{:,} articles".format(n))


def _corrections(stats):
    """The change list's fields (decisions 106) from `stats["corrections"]` and
    `stats["snapshot"]`."""
    from . import chrome, corrections
    c = stats.get("corrections") or {}
    buckets = c.get("about") or {}
    out = {}
    for b in corrections.ABOUT_BUCKETS:
        got = buckets.get(b) or {}
        n, arts = int(got.get("corrections") or 0), int(got.get("articles") or 0)
        out["corr_" + b] = (n, "{:,}".format(n))
        out["corr_%s_articles" % b] = _articles(arts)
    # the headword's order is one correction per article: its line counts articles
    out["corr_headorder"] = _articles(out["corr_headorder_articles"][0])
    kinds = corrections.about_other(c.get("other") or [], chrome.strings("en"))
    out["corr_other_kinds"] = (kinds, kinds)
    out["corr_articles"] = _articles(int(c.get("articles") or 0))
    date = snapshot_date(stats.get("snapshot"))
    out["snapshot_date"] = (date, date)
    return out


def fill(text, stats, readme=False, reports=None):
    """The source with its marks resolved: the comment gone, `[readme]` kept or dropped, each
    `[if]` kept or dropped, each `{name}` filled. Raises on an unknown name. `reports`: `numbers`'."""
    nums = numbers(stats, reports)
    text = _COMMENT.sub("", text, count=1)
    text = _README.sub((lambda m: m.group(1)) if readme else "", text)

    def cond(m):
        if m.group(1) not in nums:
            raise KeyError("about.md: unknown number in [if %s]" % m.group(1))
        return m.group(2) if nums[m.group(1)][0] else ""
    text = _IF.sub(cond, text)

    def field(m):
        if m.group(1) not in nums:
            raise KeyError("about.md: unknown number {%s}" % m.group(1))
        return nums[m.group(1)][1]
    text = _FIELD.sub(field, text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n") + "\n"
    return text


def readme(stats, source=None, reports=None):
    """The README.md text: the source, its README lines kept, the numbers filled; `reports`:
    `numbers`'."""
    return fill(read_source() if source is None else source, stats, readme=True, reports=reports)


def _inline(text):
    """One paragraph's text as HTML: escaped, then links and bold."""
    def link(m):
        url = m.group(2)
        rel = ' rel="license"' if url == LICENCE else ""
        return '<a href="%s"%s>%s</a>' % (html.escape(url, quote=True), rel, m.group(1))
    out = html.escape(text, quote=False)
    out = _LINK.sub(link, out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    return _ITALIC.sub(r"<em>\1</em>", out)


def page(stats, source=None):
    """The page's parts: (title, body HTML) — the title as text, the body `<h2>`, `<p>` and
    `<ul>`; every `<h2>` with its id (`slug`, as the Help page's; site decisions 131: the
    section "Contact" is `#contact`, the address the deck's AnkiWeb page links)."""
    return render(fill(read_source() if source is None else source, stats, readme=False), ids=True)


#: The privacy page's `[if …]` names (site decisions 166, 2026-11-05): what the page says follows
#: the counting (`chrome.counting()`) and reports (`chrome.REPORT_RECEIVER`); `receiver` is either
#: (the receiver is used at all); each has its `no_` opposite. An `[if]` may sit inside another.
#: `survey` (site decisions 173): the readers' survey on (`chrome.SURVEY` with reports on — it goes
#: to the reports' receiver, so it is never on without them).
PRIVACY_CONDITIONS = ("counting", "reports", "receiver", "survey")
#: An `[if]` block holding no other `[if` — resolved innermost first, so blocks may nest
_IF_INNER = re.compile(r"\[if (\w+)\]((?:(?!\[if ).)*?)\[/if\]", re.S)


def privacy_conditions(counting=None, reports=None, survey=None):
    """{name: bool} for `privacy.md`'s `[if name]`: `counting` (default `chrome.counting()`),
    `reports` (default: `chrome.REPORT_RECEIVER` set), `receiver` (either), `survey` (default
    `chrome.SURVEY`; never without reports, site decisions 173), and each `no_<name>`."""
    from . import chrome
    c = chrome.counting() if counting is None else bool(counting)
    r = bool(chrome.REPORT_RECEIVER) if reports is None else bool(reports)
    s = r and (bool(chrome.SURVEY) if survey is None else bool(survey))
    out = {"counting": c, "reports": r, "receiver": c or r, "survey": s}
    out.update({"no_" + k: not v for k, v in list(out.items())})
    return out


def privacy_text(source=None, counting=None, reports=None, survey=None):
    """`privacy.md` with its leading comment dropped and every `[if …]…[/if]` kept or dropped
    (`privacy_conditions`), innermost first; blank lines left by a dropped block closed up.
    KeyError on an unknown name, ValueError on an `[if` or `[/if]` left over (unbalanced)."""
    text = _COMMENT.sub("", read_source(PRIVACY_SOURCE) if source is None else source, count=1)
    cond = privacy_conditions(counting, reports, survey)

    def keep(m):
        if m.group(1) not in cond:
            raise KeyError("privacy.md: unknown name in [if %s] (known: %s)"
                           % (m.group(1), ", ".join(sorted(cond))))
        return m.group(2) if cond[m.group(1)] else ""
    while True:
        text, n = _IF_INNER.subn(keep, text)
        if not n:
            break
    if "[if " in text or "[/if]" in text:
        raise ValueError("privacy.md: an [if] without its [/if], or the reverse")
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n") + "\n"


def privacy_page(source=None, draft=False, contents=None, counting=None, reports=None, survey=None):
    """The privacy page's parts, (title, body HTML), from `privacy.md` (its leading comment
    dropped; no numbers, no `[readme]`), its `[if counting]`, `[if reports]` and `[if receiver]`
    (and their `no_`) resolved by `privacy_text` — by default from the switches, the counting's
    (`chrome.counting()`) and the reports' (`chrome.REPORT_RECEIVER`), so the page states only
    what is true of the build (site decisions 166). Raises ValueError while a `[[…]]` placeholder
    is left, unless `draft` (a preview for Robin).

    The page opens with an index of its sections (decisions 104, Robin 2026-10-23: "an index on
    the top, where you can click on each header to bring you that section"): every `## ` heading
    gets an id from its words (`slug`), and a list of links to them goes under the title and the
    page's lead, before the first section, labelled `contents` (the interface's
    `privacy.contents`, "On this page", when not given). Only this page: the About page, which is also the README, has none."""
    text = privacy_text(source, counting, reports, survey)
    left = _PLACEHOLDER.findall(text)
    if left and not draft:
        raise ValueError("privacy.md: %d placeholder(s) still to fill, the first %r"
                         % (len(left), left[0][:80]))
    if contents is None:
        from . import chrome
        contents = chrome.strings("en")["privacy.contents"]
    return render(text, what="privacy.md", index=contents)


def help_page(source=None):
    """The Help page's parts, (title, body HTML), from `help.md` (its leading comment dropped): the
    About page's subset, every `## ` heading with its id (`slug`: "Pronunciation" ->
    `#pronunciation`, decisions 123 as amended, Robin 2026-10-24), and no index."""
    text = _COMMENT.sub("", read_source(HELP_SOURCE) if source is None else source, count=1)
    return render(text.strip("\n") + "\n", what="help.md", ids=True)


def coming_page(source=None):
    """The "Coming to Ordpar" page's parts, (title, body HTML), from `coming.md` (its leading
    comment dropped; site decisions 131, the session's call at Robin's delegation, its fifth item
    his ruling, 2026-10-25): the About page's subset, its headings with ids as Help's, no index, no
    build numbers. `/coming/`, linked from the end of About's "How far it has come"."""
    text = _COMMENT.sub("", read_source(COMING_SOURCE) if source is None else source, count=1)
    return render(text.strip("\n") + "\n", what="coming.md", ids=True)


def more_page(source=None):
    """The page "More ways to use Ordpar"'s parts, (title, body HTML), from `more.md` (its leading
    comment dropped; site decisions 142, Robin 2026-10-26/27): the About page's subset with each
    section's fixed id (`{#popup}`, `{#anki}`, `{#offline}`), numbered steps (`<ol>`), and a line of
    code under a step (`<div class="ordpar-code"><code>…</code></div>`, selectable with one click by
    `page.PAGE_CSS`); no index, no build numbers. `/more/`, linked from the home page's line under
    Random word and from every footer, after Help."""
    text = _COMMENT.sub("", read_source(MORE_SOURCE) if source is None else source, count=1)
    return render(text.strip("\n") + "\n", what="more.md", ids=True)


def _changes(path, what, source):
    text = _COMMENT.sub("", read_source(path) if source is None else source, count=1)
    return render(text.strip("\n") + "\n", what=what, ids=True)


def changes_page(source=None):
    """`/changes/`'s parts, (title, body HTML), from `changes.md` (site decisions 175): built as
    `coming_page` — the leading comment dropped, the About page's subset, every `## ` heading (a
    dated entry, "2026-11-07, second update") with its id from its words (`slug`:
    `#2026-11-07-second-update`), so an entry can be linked; no index, no build numbers."""
    return _changes(CHANGES_SOURCE, "changes.md", source)


def library_changes_page(source=None):
    """`/dictionary-changes/`'s parts, (title, body HTML), from `library-changes.md` (site decisions
    175): as `changes_page`."""
    return _changes(LIBRARY_CHANGES_SOURCE, "library-changes.md", source)


def deck_changes_page(source=None):
    """`/deck-changes/`'s parts, (title, body HTML), from `deck-changes.md` (site decisions 177, the
    deck session's file, never edited here): as `changes_page`."""
    return _changes(DECK_CHANGES_SOURCE, "deck-changes.md", source)


#: The address for a pop-up dictionary with every setting at its default (site decisions 146):
#: the line of code that is it gets `data-ordpar-popup`, and `shell.js` `wireCodeLines` fills it
#: with the address carrying the reader's saved settings (`popupAddress`, which gives exactly this
#: one with the defaults). Without script the page shows it as written.
POPUP_ADDRESS = "https://ordpar.no/bm-en/#q={{str}}"


def _steps(block):
    """A numbered list's block as `<ol>`: each "N. " line an item, an indented line in backticks
    under it the item's line of code (site decisions 142); the pop-up address's line marked
    `data-ordpar-popup` (site decisions 146)."""
    items = []
    for line in block.split("\n"):
        m = _STEP.match(line)
        if m:
            items.append([_inline(line[m.end():].strip()), []])
            continue
        c = _CODE_LINE.match(line)
        if c and items:
            mark = ' data-ordpar-popup' if c.group(1) == POPUP_ADDRESS else ''
            items[-1][1].append('<div class="ordpar-code"><code%s>%s</code></div>'
                                % (mark, html.escape(c.group(1), quote=False)))
        elif items:                            # a wrapped line of the item's own words
            items[-1][0] += " " + _inline(line.strip())
    return "<ol>\n%s\n</ol>" % "\n".join("<li>%s%s</li>" % (words, "".join(code))
                                         for words, code in items)


def slug(words, taken=()):
    """A heading's id from its words: lower case, letters and digits kept (æ, ø, å as ae, o, a),
    every other run one hyphen ("Who is responsible, and the legal basis" ->
    "who-is-responsible-and-the-legal-basis"); `-2`, `-3` … after one already in `taken`. Stable:
    the same words give the same id, so a link to a section keeps working while its heading
    does."""
    t = words.lower()
    for a, b in (("æ", "ae"), ("ø", "o"), ("å", "a")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "section"
    out, n = t, 1
    while out in taken:
        n += 1
        out = "%s-%d" % (t, n)
    return out


def render(text, what="about.md", index=None, ids=False):
    """Filled text -> (title, body HTML). With `index` (the privacy page's, decisions 104): each
    `## ` heading gets an id (`slug`), and a `<nav>` labelled `index` listing a link to each, in
    order, goes before the first of them (after the page's lead). With `ids` (the Help page's,
    decisions 123) the ids without the index. A heading's `{#id}` after its words is its id; a
    block opening "1. " is numbered steps (`_steps`) (site
    decisions 142)."""
    title, body, heads = None, [], []
    for block in text.split("\n\n"):
        block = block.strip("\n")
        if not block:
            continue
        if block.startswith("# "):
            title = block[2:].strip()
        elif block.startswith("## ") and (index is not None or ids):
            words = block[3:].strip()
            fixed = _FIXED_ID.search(words)
            if fixed:                          # `{#id}` after the words (site decisions 142)
                words = words[:fixed.start()]
                hid = fixed.group(1)
                if hid in [h for h, _w in heads]:
                    raise ValueError("%s: the id #%s twice" % (what, hid))
            else:
                hid = slug(_plain_words(words), [h for h, _w in heads])
            heads.append((hid, words))
            body.append('<h2 id="%s">%s</h2>' % (hid, _inline(words)))
        elif block.startswith("## "):
            body.append("<h2>%s</h2>" % _inline(block[3:].strip()))
        elif _STEP.match(block):
            body.append(_steps(block))
        elif _is_list(block):
            body.append("<ul>\n%s\n</ul>" % "\n".join(
                "<li>%s</li>" % _inline(item) for item in _items(block)))
        else:
            body.append("<p>%s</p>" % _inline(" ".join(block.split("\n"))))
    if title is None:
        raise ValueError("%s: no '# ' title" % what)
    if index is not None and heads:
        # before the first section, after the page's opening lines (its lead, which says what the
        # page covers)
        first = next(i for i, b in enumerate(body) if b.startswith("<h2 "))
        body.insert(first, '<nav class="ordpar-toc" aria-labelledby="ordpar-toc-title">\n'
                       '<p class="ordpar-toc-title" id="ordpar-toc-title">%s</p>\n<ul>\n%s\n</ul>\n</nav>'
                    % (html.escape(index, quote=False), "\n".join(
                        '<li><a href="#%s">%s</a></li>' % (hid, _inline(_plain_words(words)))
                        for hid, words in heads)))
    return title, "\n".join(body)


def _is_list(block):
    """Is `block` a bulleted list: its first line opening `- `, each other line either opening `- `
    or indented (an item's wrapped words, site decisions 175)?"""
    lines = block.split("\n")
    return lines[0].startswith("- ") and all(
        line.startswith("- ") or (line[:1] == " " and line.strip()) for line in lines[1:])


def _items(block):
    """A list block's items, each its words with its wrapped lines joined by one space."""
    items = []
    for line in block.split("\n"):
        if line.startswith("- "):
            items.append(line[2:].strip())
        else:
            items[-1] += " " + line.strip()
    return items


def _plain_words(markdown):
    """A heading's words with its Markdown marks dropped (a link's text kept, `**` gone)."""
    return _ITALIC.sub(r"\1", _LINK.sub(r"\1", markdown).replace("**", ""))


def plain(markup):
    """The visible words of either rendering, for comparing the page with the README: tags,
    Markdown marks and link targets dropped, whitespace collapsed."""
    t = re.sub(r"</?(?:a|strong|em)\b[^>]*>", "", markup)    # inline: no space
    t = re.sub(r"<[^>]+>", " ", t)
    t = _LINK.sub(r"\1", t)
    t = t.replace("**", "")
    t = _ITALIC.sub(r"\1", t)
    t = re.sub(r"(?m)^#+ ", "", t)
    t = re.sub(r"(?m)^- ", "", t)
    return " ".join(html.unescape(t).split())
