# -*- coding: utf-8 -*-
"""Every visible chrome string, in one file (site decisions 24: a new interface language
costs one strings file, never a second copy of the 94k pages).

The article fragment itself is language-neutral and carries no string from here — its own
section labels ("Etymology", "Senses and Example Sentences", "Set phrases") live in
`article.py` — ordbokene's English labels since site decisions 22 was amended (Robin, 2026-10-19;
until then the deck's lineage labels).
That is the one visible-string exception to "every chrome string keyed", and it is deliberate:
the labels sit inside the fragment that must be identical under every interface language.

`{n}` and `{lemma}` are `str.format` placeholders. Keys are stable; the build writes this
dict to `out/site/strings/en.json` for the shell (build C) to read.
"""

EN = {
    # --- chrome ---------------------------------------------------------------
    "site_name": "Ordpar",
    "search_placeholder": "Search a word",
    "search_submit": "Search",
    "skip_to_article": "Skip to the article",
    "other_entries_one": "1 more entry for {lemma}",
    "other_entries_many": "{n} more entries for {lemma}",
    # decisions 63: the line under the header on an article page, after ordbokene's
    # "ARTICLE VIEW" and "← Home" (the arrow is drawn aria-hidden beside `home_link`)
    "article_view": "Article view",
    "home_link": "Home",

    # --- translation status (decisions 32, recommended (1) — verbatim) ---------
    "status_untranslated": "Norwegian only · not yet translated",
    "untranslated_note": ("This article has not been translated yet. It is shown as "
                          "Bokmålsordboka has it, in Norwegian."),

    # --- attribution (decisions 32 and 12, amended by Robin 2026-10-17) ------------
    # One short credit line, in the footer of every page since decisions 63; the full text is
    # the About page. CC BY 4.0 § 3(a)(2) allows the attribution "in any reasonable manner",
    # for example by a link to a resource that includes it. `{source}` and `{licence}` become
    # links: ordbokene.no (in general — no per-article source link, Robin 2026-10-19) and the
    # licence (`chrome.credit`). The About page's link, `about_link`, is the last of the
    # footer's links since 2026-10-22 (Robin: "on the same line as the other page-links";
    # `chrome.footer`), no longer the credit's last words.
    # Its words "About" since site decisions 176 (Robin, 2026-11-07), the about pages' first tab.
    "credit": "Based on {source} (UiB and Språkrådet) · {licence} · "
              "Ordpar is independent of both",
    "credit_source": "Bokmålsordboka",
    "credit_licence": "CC BY 4.0",
    "about_link": "About",
    # The "under development" note (decisions 63 item, Robin 2026-10-20: "makes sense"): in the
    # footer band of every page, shown exactly while `head.NOINDEX` (the launch switch) is on —
    # one switch turns both off at launch (`chrome.footer`). The session's wording; Robin may
    # change it. Reworded 2026-10-25 (decisions 132, Robin: "sounds good"): the site is public
    # since the deck's release, so no longer "not yet published"; the note stays for the
    # feedback link `shell.js` appends to it (Robin: "I would like to keep the form for now").
    "dev_note": "Under development: Ordpar is still being built, and its pages may change.",

    # --- the About page (/about/) -------------------------------------------------
    # Its text is not here: `ordpar/about.md`, one source with the published README
    # (`sitegen/about.py`, decisions 63, 2026-10-22); a second interface language would add
    # its own `about.<lang>.md`.

    # --- the article's own controls (decisions 37, 54) -------------------------
    # The interface words of the article page itself: the cue the page script adds under each
    # Norwegian definition line when `defs = no` (it reaches the page through PAGE_JS, never
    # the fragment), and the inflection toggle's label below. Everything else in the fragment
    # is the article or the deck's labels.
    "show_english": "Show English",
    # The heading the page script puts before a sense's own examples under the layout closer to
    # ordbokene.no (decisions 87, the setting `layout` = ordbokene): ordbokene's English word,
    # singular whatever the count (the examples lab report § Ordbokene's header).
    "example_heading": "Example",
    # The line the page script puts under an example list cut by the examples limit (decisions
    # 112, the setting `exlimit`): Robin's words, "Show N more examples"; singular for one. It
    # opens the rest of the list in place.
    "examples_more": "Show {n} more examples",
    "examples_more_one": "Show 1 more example",
    # The inflection table's toggle (Robin, 2026-09-24) — ordbokene's English label.
    "inflection": "Inflection",
    # decisions 131 (the setting `exeye`, off by default): the eye's accessible name and tooltip,
    # the deck's own words for hiding (`deck/templates/back.html` `data-hide`); one name in both
    # states, `aria-pressed` carrying the state, as the heart's (brief 60b item 6)
    "exeye_button": "Hide the examples' English",

    # --- footer controls (21e: copy-link and share only; no cite, no RIS) ------
    "copy_link": "Copy link",
    "copy_done": "Link copied",
    "share": "Share",
    # site decisions 60: the heart beside them, and the header's link to the favourites page
    # (both drawn by the page script, so a page with JavaScript off shows neither)
    # brief 60b item 6: one name in both states; `aria-pressed` carries the state
    "fav_label": "Favourite",
    "fav_saved": "In favourites",
    "fav_link": "Favourites",

    # --- accessibility --------------------------------------------------------
    # 33 (1): the Roman numeral is visible but hidden from assistive technology, and this
    # reads in its place — the word makes the digit mean something ("bru, homograph 2").
    "homograph": "homograph {n}",

    # --- page metadata --------------------------------------------------------
    # the prose pages' titles ("About Ordpar — Ordpar"); the article pages' since decisions 128
    # end in `dictionary_name` instead
    "title_suffix": " — Ordpar",
    # site decisions 128 (Robin, 2026-10-25): the language PAIR's own dictionary name — the
    # second half of every article page's <title> ("abstrakt (adjective) — Norwegian–English
    # dictionary", `describe.page_title`) and of the link picture's alt text (`head.social_tags`);
    # a second pair names its own here. (Until then an untranslated page's title ended
    # " (Norwegian only)", `title_untranslated`; the lab's title has no such ending.)
    "dictionary_name": "Norwegian–English dictionary",
    # the home page's description (Robin, 2026-10-25), its number the About page's figure of
    # translated articles, filled at every build (`describe.home_description`)
    "home_description": ("Ordpar: a Norwegian–English dictionary built on Bokmålsordboka. "
                         "{translated} of its articles are translated into English so far; "
                         "the rest are shown in Norwegian."),
    # site decisions 117 (Robin, 2026-10-25, "3 entries in the Norwegian–English dictionary: I
    # then · II when · III Norwegian only"): a word page with several entries opens its
    # description with this, then each entry (`wordpages.several_description`)
    "word_page_entries": "{n} entries in the {dictionary}: ",
    # site decisions 154 (Robin, 2026-10-31: the headword first in every description): a form
    # page's description opens with the form, then this and its rows (`wordpages.form_description`)
    "form_page_lead": "{q}: an inflected form of ",
}

#: Site decisions 152 (Robin, 2026-10-30/31): THE LABELS SETTING's Norwegian for the strings of
#: this file the article frame shows (its own section labels are `article.NB_LABELS`). Each label
#: ships in both languages and the sheet shows one (`ordpar-labels-no`, or Norwegian only's
#: `ordpar-nbo` since 152's follow-up, whatever `labels` says); the Norwegian copy, the one
#: the default hides, carries `data-nosnippet` (154). Ordbokene's word where its rendered pages
#: show one ("Eksempel": the lookup of 2026-10-30); the rest are DRAFTS for
#: Robin, marked here. The change notice's Norwegian drops the kind of correction (a draft). The
#: card foot's words (Copy link, Link copied, Share) have none: they are the interface's, English
#: until 1.0.0 (Robin, 2026-11-03; "Kopier lenke", "Lenke kopiert", "Del" until then).
NB = {
    "show_english": "Vis engelsk",                                   # draft
    "example_heading": "Eksempel",
    "examples_more": "Vis {n} eksempler til",                        # draft
    "examples_more_one": "Vis 1 eksempel til",                       # draft
    "other_entries_one": "1 artikkel til for {lemma}",               # draft
    "other_entries_many": "{n} artikler til for {lemma}",            # draft
    "status_untranslated": "Bare på norsk · ikke oversatt ennå",     # draft
    "untranslated_note": ("Denne artikkelen er ikke oversatt ennå. Den står slik "
                          "Bokmålsordboka har den, på norsk."),     # draft
    "change.sentence": "Vi har rettet feil i denne artikkelen.",     # draft
    "change.sentence.headorder": "Vi har satt den vanligste skrivemåten av oppslagsordet først.",  # draft
    "change.sentence.headorder_and": ("Vi har satt den vanligste skrivemåten av oppslagsordet "
                                      "først og rettet feil i denne artikkelen."),             # draft
    "change.link": "Bokmålsordbokas artikkel på ordbokene.no",       # draft
}
