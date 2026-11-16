# -*- coding: utf-8 -*-
"""The site's one header and one footer (site-review decisions 63: as on ordbokene.no,
the same header on the article pages and the search result pages; the credit at the bottom of
every page).

ONE SOURCE for both: `header()` and `footer()` are called by the article build (`page.py`: every
article page, the About page) and by the index build (`build_index.copy_shell`, through the
`<!--ORDPAR_HEADER-->` and `<!--ORDPAR_FOOTER-->` markers: the front page, the search page, 404,
`/favourites/`, `/history/`, `/settings/`). Nothing else writes header or footer markup;
`shell.js` only ENHANCES what is here (the combobox's ARIA, the × button, the dropdown).

**Without JavaScript** the header is a form that searches on Enter (a GET to `/bm-en/?q=`) and
the footer the credit and four links, Home, Help, More ways to use Ordpar (site decisions 142) and
About (its words since site decisions 176, Robin 2026-11-07). That is all the markup here
carries. What needs script — the header's Random word, Favourites and Settings, the
footer's Settings, Favourites and History (between Home and About) — is MADE by script since 2026-10-20 (the size report's
item 5: 71 MB of hidden markup over the site): `shell.js` `addChrome` inserts it, and `shell.css`
holds its room under `html.ordpar-js` (set by the head script, `head.THEME_JS`) until it is in,
so nothing moves. Until then it was here, `ordpar-needs-js`, hidden until the head script ran.

The words are the shell's strings (`ordpar/site/strings/en.json`); the credit sentence is
`strings.py`'s (`credit`), as before. `shell.js` relabels the chrome for another interface
language with no rebuild (decisions 24, 21a): it finds each static element here by a selector
(`STATIC_STRINGS` there; `RELABEL` below is the same map, and the tests hold the two together),
so no element carries its key any more (`data-ordpar-string`, 40 MB over the site, item 6).
"""
import html
import json
import os
import re

from . import head
from .strings import EN

SITE_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")
PAIR = "bm-en"
ORDBOKENE_HOME = "https://ordbokene.no/"
#: One article at ordbokene.no, by its id — the change notice's link (site decisions 106; the
#: form checked live 2026-10-23: https://ordbokene.no/nob/bm/111955 answers 200, "dele inn").
ORDBOKENE_ARTICLE = "https://ordbokene.no/nob/bm/%d"
LICENCE = "https://creativecommons.org/licenses/by/4.0/"
ABOUT_HREF = "/about/"
#: The Help page (site decisions 123 as amended, Robin 2026-10-24), linked from every footer
HELP_HREF = "/help/"
#: "More ways to use Ordpar" (site decisions 142, Robin 2026-10-26/27), linked from every footer,
#: after Help, and from the home page's line under Random word (`shell.js` `addMoreLine`)
MORE_HREF = "/more/"
#: "Coming to Ordpar" (site decisions 131, 2026-10-25): linked from the About page only, no footer link
COMING_HREF = "/coming/"
#: "Thanks to our readers" (site decisions 166, 2026-11-05): the fixes readers' reports led to,
#: linked from the About page's "Thanks" only, no footer link (`sitegen/thanks.py`)
THANKS_HREF = "/thanks/"
PRIVACY_HREF = "/privacy/"
#: The three change lists' pages (site decisions 175, 177; `about.changes_page` and its siblings):
#: the site's, the dictionary's, the Anki decks' — reached by the about pages' Changes tab
#: (`about_tabs`), the update note's "What's new" (`offline.js`) and each other's links
CHANGES_HREF = "/changes/"
DICTIONARY_CHANGES_HREF = "/dictionary-changes/"
DECK_CHANGES_HREF = "/deck-changes/"
#: THE TABS OVER THE ABOUT PAGES (site decisions 176: tabs in the about pages' header, one for
#: each about page, and those pages get the same header; Help and More ways left out): each
#: tab's address and its words' key (`site/strings/en.json`), in order
ABOUT_TABS = ((ABOUT_HREF, "about.tab.about"), (COMING_HREF, "about.tab.coming"),
              (CHANGES_HREF, "about.tab.changes"), (PRIVACY_HREF, "about.tab.privacy"),
              (THANKS_HREF, "about.tab.thanks"))
#: The pages that carry the tabs -> the tab shown pressed there: the change lists' three under
#: Changes. No other page has them (Help, More ways, Settings, the survey, the articles).
ABOUT_TAB_PAGES = {ABOUT_HREF: ABOUT_HREF, COMING_HREF: COMING_HREF, CHANGES_HREF: CHANGES_HREF,
                   DICTIONARY_CHANGES_HREF: CHANGES_HREF, DECK_CHANGES_HREF: CHANGES_HREF,
                   PRIVACY_HREF: PRIVACY_HREF, THANKS_HREF: THANKS_HREF}
#: The privacy page's section on reports — the anchor the report form links (site decisions 166,
#: 2026-11-05: the information at collection, GDPR Art. 13); `about.slug("Reporting a mistake")`,
#: the same in `report.js` `PRIVACY_HREF` (the tests hold the three together)
PRIVACY_REPORTS_HREF = PRIVACY_HREF + "#reporting-a-mistake"
#: THE PRIVACY PAGE'S SWITCH (site decisions 104's box, item 5: "its own page, `/privacy/`, linked
#: from every page's footer and from About"). It decides the page and nothing else (split from the
#: counting's on 2026-11-05, site decisions 166):
#:   * `/privacy/` written by the build (`build_site.py`; one an earlier build left is removed);
#:   * "Privacy" after About in every footer (`footer`);
#:   * the About page's and the README's line on it (`about.md` `[if privacy]`, `about.numbers`);
#:   * the offline copy takes the page where the build wrote it (`build_offline.OPTIONAL_PAGES`);
#:     the page is `noindex`, so it is never in the sitemap (`build_site.NOINDEX_OTHER`).
#: What the page SAYS follows the other two switches: `privacy.md`'s `[if counting]` and
#: `[if reports]` (`about.privacy_page`). The counting's "Send usage statistics" setting is NOT
#: this switch's: it follows `counting()`. Off until Robin has approved the page's words. With it
#: on, the build refuses a `privacy.md` that still holds a `[[…]]` placeholder. Reports need it:
#: the build refuses `REPORT_RECEIVER` set while it is off (the report form links the page;
#: `build_site.py`), except a look build, which gets the page for that build alone.
#: ON since 2026-11-05 (site decisions 166: the page's words approved).
PRIVACY = True
#: `events.js`, whose `var RECEIVER = '…';` decides whether anything is counted (`counting`)
EVENTS_JS = os.path.join(SITE_SRC, "events.js")
_EVENTS_RECEIVER = re.compile(r"^  var RECEIVER = (['\"])(.*?)\1;", re.M)


def counting(path=None):
    """Is THE COUNTING live (site decisions 104: page views, searches, suggestions chosen and installs
    sent to the receiver)? True exactly when `events.js`'s `var RECEIVER` is not empty — the line
    that decides whether anything is sent, so the site can never claim a counting that does not
    run, nor run one it does not describe (site decisions 166, 2026-11-05: no second flag to keep
    equal to it). It decides the settings page's "Send usage statistics" (`build_index.copy_shell`
    writes `window.ORDPAR_COUNTING`; `settings.js` gate `counting`) and the privacy page's
    `[if counting]` passages (`about.privacy_page`). ValueError if the line is gone."""
    with open(path or EVENTS_JS, encoding="utf-8") as f:
        m = _EVENTS_RECEIVER.search(f.read())
    if not m:
        raise ValueError("events.js: no `var RECEIVER = '…';` line, so the build cannot tell "
                         "whether the counting is on")
    return bool(m.group(2).strip())
#: THE REPORTS' SWITCH (site decisions 166, 2026-11-05): the receiver's `/report` address, the one
#: place it is set. Empty, as committed: reports are off. It decides everything readers see of
#: reports, so the site states only what is true:
#:   * the button "Suggest a correction" at an article's foot — the build writes this address into
#:     `report.js` (`page.REPORT_SLOT`, its `var REPORT_RECEIVER = '';`), so the shipped script and
#:     both bundles carry it; empty, no button anywhere and nothing is ever sent;
#:   * the page `/thanks/` (`build_site.write_thanks`): built only while on; one an earlier build
#:     left is removed;
#:   * `/thanks/` in the sitemap (`build_site.indexed_other`; the index build's
#:     `wordpages.indexed_other`, from the page's presence) and in the offline copy
#:     (`build_offline.OPTIONAL_PAGES`; its absence is no warning);
#:   * the About page's and the README's paragraph thanking the readers who report mistakes
#:     (`about.md` `[if reports]`, `about.numbers`).
#:   * the privacy page's "Reporting a mistake" and every sentence on reports (`privacy.md`
#:     `[if reports]`), and the form's line linking it (`PRIVACY_REPORTS_HREF`).
#: Apart from the counting's switch (`events.js` `RECEIVER`, `counting()`): reports can go live
#: while the counting stays off (decisions 166, our own receiver). NOT apart from `PRIVACY`:
#: the build refuses reports on while the privacy page is off.
#: For ONE build, `build_site.py` takes the address from the environment instead
#: (`ORDPAR_REPORT_RECEIVER`, `build_site.report_receiver_override`): Robin's look at the form on
#: :8098 against the receiver's local stand-in, with no committed file changed. `deploy.py prepare`
#: refuses a build whose address is not `https://` on a public name (`deploy.report_address_problem`),
#: so such a look build cannot be published.
#: ON since 2026-11-05 (site decisions 166): the receiver deployed that day, the privacy
#: page approved.
REPORT_RECEIVER = "https://ordpar-receiver.ordpar.workers.dev/report"

#: The readers' survey, "Ordpar — your first impressions" (site decisions 173, Robin 2026-11-07: our
#: own page in place of the Google form, kept after launch): its address on the site
SURVEY_HREF = "/survey/"
#: The privacy page's section on the survey, linked from the survey's second paragraph
#: (`ordpar/site/survey.json`): `about.slug("The survey")` (the tests hold the three together)
PRIVACY_SURVEY_HREF = PRIVACY_HREF + "#the-survey"
#: THE SURVEY'S SWITCH (site decisions 173). The survey's answers go to the reports' receiver, as a
#: second kind beside reports (`POST /survey`, under the same total cap), so the survey is ON only
#: while this is True AND reports are on (`survey_receiver()`: the reports' address with `/survey`
#: for `/report` — a look build's address too). It decides everything readers see of the survey:
#:   * the page `/survey/` (`build_site.write_survey`): built only while on; one an earlier build
#:     left is removed; `noindex`, not in the sitemap, not in the offline copy;
#:   * the address the build writes into `survey.js` (`page.SURVEY_SLOT`);
#:   * the footer's "Tell us what you think →" (`footer.feedback`), made by `shell.js` from the
#:     address the build writes into it (`page.SURVEY_LINK_SLOT`): after the "under development"
#:     note while the launch switch is on, in a line of its own after launch; none while off;
#:   * the privacy page's "The survey" and every clause on it (`privacy.md` `[if survey]`).
#: OFF as committed (the contractor's build, 2026-11-07): the receiver must take `/survey` first
#: (its migration `0003_surveys.sql` and a deploy), and two sentences of the privacy page that
#: predate the survey would be untrue with it on (the build's report). Google's form is gone either way.
#: ON since 2026-11-07: the receiver migrated and redeployed on Robin's go (version 7931eea5), the two
#: sentences approved and applied ("Approve all three"), site decisions 173.
SURVEY = True


def survey_receiver(report_receiver=None, on=None):
    """The survey's receiver address, or "" while the survey is off: `SURVEY` (or `on`) and the
    reports' address (`REPORT_RECEIVER`, or `report_receiver`) set — that address with its last
    "/report" made "/survey"."""
    addr = REPORT_RECEIVER if report_receiver is None else report_receiver
    if not (SURVEY if on is None else on) or not addr:
        return ""
    check_report_receiver(addr)
    return addr[:-len("/report")] + "/survey"


def check_report_receiver(address):
    """`address` if it can be the reports' switch — empty, or an http(s) address ending in
    "/report" — else ValueError. Whether it may be PUBLISHED is `deploy.py`'s question."""
    if address == "":
        return address
    if (not isinstance(address, str) or not re.match(r"^https?://[^/\s'\"\\<>]+/(?:[^\s'\"\\<>]*/)?report$", address)):
        raise ValueError("the reports' receiver address must be empty or an http(s) address ending "
                         "in /report, not %r" % (address,))
    return address


def strings(lang="en"):
    """The shell's strings for `lang` (`site/strings/<lang>.json`) with the article build's
    (`strings.py`) beside them — the keys do not overlap (dotted against underscored)."""
    with open(os.path.join(SITE_SRC, "strings", "%s.json" % lang), encoding="utf-8") as f:
        merged = json.load(f)
    for k, v in EN.items():
        merged.setdefault(k, v)
    return merged


def _e(text):
    return html.escape(text or "", quote=False)


def _a(text):
    return html.escape(text or "", quote=True)


#: How `shell.js` finds each static element of the chrome for a relabel — its `STATIC_STRINGS`,
#: the same pairs (`ordpar/tests/test_ordpar_slim.py` holds the two together): selector -> string key.
#: The skip link's key is `nav.skipArticle` where `<html>` carries `data-article-id` (an
#: article page), else `nav.skip`. The About link's key is the article build's (`strings.py`
#: `about_link`): the table inlined on the article pages and fetched on a switch of language
#: (`chrome.strings`) has it; the shell pages' inline table (the shell's `en.json` alone) does
#: not, and there the link keeps the words it was built with (`shell.js` relabels only a key the
#: strings have).
RELABEL = (
    (".ordpar-skip", ("nav.skip", "nav.skipArticle")),
    (".ordpar-brand-name", "site.name"),
    (".ordpar-brand-tagline", "site.tagline"),
    ('label[for="ordpar-q"]', "search.label"),
    (".ordpar-submit", "search.submit"),
    ('.ordpar-footer-nav a[href="/"]', "footer.home"),
    ('.ordpar-footer-nav a[href="/help/"]', "footer.help"),
    ('.ordpar-footer-nav a[href="/more/"]', "footer.more"),
    ('.ordpar-footer-nav a[href="/about/"]', "about_link"),
    ('.ordpar-footer-nav a[href="/privacy/"]', "footer.privacy"),
)


def about_tabs(s, path, privacy=None, thanks=None):
    """The row of tabs over the about pages (site decisions 176) for the page at `path`, or "" on a
    page that has none (`ABOUT_TAB_PAGES`). Links, not script-driven tabs — each is a page of its
    own — in a `<nav>` labelled `about.tabs` ("About Ordpar"), the current page's `aria-current=
    "page"`; Settings' section pills (`ordpar-jump` in `shell.css`, one style site-wide), wrapping
    onto a second line on a narrow screen, the pressed one filled in the accent. Placed by
    `page._prose_page` directly under the page's `<h1>`: the page's frame, never `about.md`'s words,
    so never in the README. A tab is drawn only while its page is built: Privacy while the privacy
    page's switch is on (`PRIVACY`, or `privacy`, as the footer's link; a look build that writes the
    page for itself alone gets no tab, as it gets no footer link), Thanks while reports are on
    (`REPORT_RECEIVER`, or `thanks`: `build_site.write_thanks`)."""
    current = ABOUT_TAB_PAGES.get(path)
    if current is None:
        return ""
    show = {PRIVACY_HREF: PRIVACY if privacy is None else privacy,
            THANKS_HREF: bool(REPORT_RECEIVER) if thanks is None else thanks}
    links = []
    for href, key in ABOUT_TABS:
        if not show.get(href, True):
            continue
        links.append('<li><a href="%s"%s>%s</a></li>' % (
            href, ' aria-current="page"' if href == current else "", _e(s[key])))
    return ('<nav class="ordpar-tabs" aria-label="%s">\n<ul class="ordpar-jump">\n%s\n</ul>\n</nav>\n'
            % (_a(s["about.tabs"]), "\n".join(links)))


def header(s, skip="nav.skip"):
    """The skip link and the header. `skip` is the skip link's string key (the article page:
    `nav.skipArticle`); it always targets `#ordpar-main`. Random word, Favourites and Settings
    are inserted by `shell.js` (`addChrome`). The search field is the site's only one (every
    page's, the search page's and 404's included): `autocapitalize="none"` (decisions 113, Robin
    2026-10-24) so a phone's keyboard starts in small letters, its shift key still working — as
    ordbokene.no's field, which sets it too. A newline between the name and the tagline (site
    decisions 154): two lines on the page (a flex column), one word to a text extraction without
    it ("OrdparNorwegian–English dictionary")."""
    return (
        '<a class="ordpar-skip" href="#ordpar-main">%(skip_text)s</a>\n'
        '<header class="ordpar-header">\n'
        '<div class="ordpar-header-inner">\n'
        '<a class="ordpar-brand" href="/"><span class="ordpar-brand-name">%(name)s</span>\n'
        '<span class="ordpar-brand-tagline">%(tagline)s</span></a>\n'
        '<form class="ordpar-search" role="search" action="/%(pair)s/" method="get">\n'
        '<label class="ordpar-visually-hidden" for="ordpar-q">%(label)s</label>\n'
        '<div class="ordpar-combobox"><input id="ordpar-q" type="text" lang="nb" '
        'autocomplete="off" autocapitalize="none" spellcheck="false" maxlength="200" '
        'placeholder="%(placeholder)s"></div>\n'
        '<button class="ordpar-submit" type="submit">%(submit)s</button>\n'
        '</form>\n'
        '</div>\n'
        '</header>\n'
        % {"skip_text": _e(s[skip]), "pair": PAIR,
           "name": _e(s["site.name"]), "tagline": _e(s["site.tagline"]),
           "label": _e(s["search.label"]), "placeholder": _a(s["search.placeholder"]),
           "submit": _e(s["search.submit"])})


def credit(s):
    """The one-line credit (decisions 32 and 12, amended 2026-10-17; decisions 63: in the footer
    of every page, "Bokmålsordboka" linking ordbokene.no in general — Robin, 2026-10-19, no
    per-article source link; the About page carries the full attribution, and its link is the
    footer's last since 2026-10-22, `footer`)."""
    out = _e(s["credit"])
    links = {
        "source": '<a href="%s" rel="noopener">%s</a>' % (ORDBOKENE_HOME, _e(s["credit_source"])),
        "licence": '<a href="%s" rel="license noopener">%s</a>' % (LICENCE, _e(s["credit_licence"])),
    }
    for name, markup in links.items():
        out = out.replace("{%s}" % name, markup)
    return out


def footer(s, noindex=None, privacy=None):
    """The footer band: the credit, then the site's links — Home and About here,
    and with script Settings, Favourites, History between them (`shell.js` `addChrome` inserts
    them before About): Home · Settings · Favourites · History · About (decisions
    63: on the same line as the other page links; until then About was the credit's
    last link). Once in the footer (decisions 63). While the launch switch is on
    (``head.NOINDEX``; ``noindex`` overrides it) the "under development" note closes the band —
    one switch turns both off. No logos (decisions 63: the credit says Ordpar is independent of
    both institutions). While the privacy switch is on (``PRIVACY``; ``privacy`` overrides it),
    "Privacy" follows About (site decisions 104's box, item 5). "Help" goes before About (site
    decisions 123 as amended, Robin 2026-10-24; ordbokene's header has "Help" before "About"),
    and the script's links before Help: Home · Settings · Favourites · History · Help · About.
    "More ways to use Ordpar" follows Help (site decisions 142, Robin 2026-10-27, the
    lab's default): Home · Settings · Favourites · History · Help · More ways to use Ordpar ·
    About. A newline between the links (site decisions 154): separate on the page (a
    flex row), and with nothing between them a text extraction ran them together. The About
    link's words are "About" since site decisions 176 (the footer's label
    just "About"): the licence stays in the credit's line,
    "CC BY 4.0" linked, and "About" matches the about pages' first tab and ordbokene's English
    footer."""
    on = head.NOINDEX if noindex is None else noindex
    note = ('<p class="ordpar-devnote">%s</p>\n' % _e(s["dev_note"])) if on else ""
    priv = ('<a href="%s">%s</a>' % (PRIVACY_HREF, _e(s["footer.privacy"]))
            if (PRIVACY if privacy is None else privacy) else "")
    return (
        '<footer class="ordpar-footer">\n'
        '<div class="ordpar-footer-inner">\n'
        '<p class="ordpar-credit">%s</p>\n'
        '<nav class="ordpar-footer-nav" aria-label="%s">%s</nav>\n'
        '%s'
        '</div>\n'
        '</footer>\n'
        % (credit(s), _a(s["footer.nav"]),
           '<a href="/">%s</a>\n<a href="%s">%s</a>\n<a href="%s">%s</a>\n<a href="%s">%s</a>%s'
           % (_e(s["footer.home"]), HELP_HREF, _e(s["footer.help"]), MORE_HREF,
              _e(s["footer.more"]), ABOUT_HREF, _e(s["about_link"]), ("\n" + priv) if priv else ""),
           note))
