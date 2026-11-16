# -*- coding: utf-8 -*-
"""The page around the article fragment: head, the site's header and footer (`chrome.py`, one
source with the shell pages — decisions 63), the "Article view" line, the article's card,
captions, CSS and the page script (`PAGE_JS`; the head script is `head.THEME_JS`).

The inflection table is build B's: the page carries its paradigm island and mount point
(`article.paradigm_block`); its stylesheet and script are parts of the page's one stylesheet
and one script (below). A missing file costs nothing: the mount point stays empty.

**What the site serves from `/site/`** (2026-10-20, the size report's items 3 and 4): every
article page and the About page link ONE head script, `/site/theme.js` (parser-blocking, before
the sheet), ONE stylesheet, `/site/ordpar.css` (`ARTICLE_CSS_PARTS` concatenated in today's
order), and ONE deferred script, `/site/ordpar.js` (`ARTICLE_JS_PARTS`, likewise, each in its
own `try`, with the interface strings in front so the chrome `shell.js` inserts has its words
at once). The shell pages link their own pair, `/site/shell-pages.css` and
`/site/shell-pages.js` (`SHELL_CSS_PARTS`, `SHELL_JS_PARTS`; `build_index.copy_shell`). Every
script and stylesheet ships without comments (decisions 61: `slim.strip_js` / `strip_css`);
`shipped` is a file's text as served, `asset` its `?v=` link.

The fragment is language-neutral and identical under every interface language (decisions 24);
everything here is the chrome, and every visible word of it comes from `strings.py`. The page
works with JavaScript off: a cross-reference is a plain link to its page (decisions 80; the mini
script `ordpar/site/mini.js` makes it open a mini), the theme falls back to the
light palette, the header's box is a plain form that searches on Enter, and what needs script
(the copy/share buttons, the heart, the header's dropdown, Random word, Favourites, Settings)
is not in the page at all: the scripts insert it (since 2026-10-20; hidden until then).
"""
import functools
import hashlib
import html
import json
import os
from . import chrome, colours, deck, slim, face as site_face
from . import about as about_mod
from . import thanks as thanks_mod
from . import survey as survey_mod
from . import corrections
from . import describe
from .head import head_tags, SW_REGISTER, THEME_JS, THEME_JS_HREF  # noqa: F401  -- one copy, head.py
from .strings import EN

markup = deck.markup
g = deck.ordbok_gen
mini = deck.mini

#: The deck's own sheets, unchanged (decisions 12: the article keeps the deck's anatomy and
#: palette), plus the site's own small sheet below. They are written ONCE, to
#: `out/site/article.css`, and linked: 11 KB inlined into every one of 94,238 pages was more
#: than half the compressed site, and the offline dataset is the fragments, not the pages.
DECK_CSS = g._CARD_CSS + g._XREF_CSS + mini.STYLE

#: Night-mode partners for every colour, from `docs/visual-test-runs.md` § Night-mode palette
#: reference. The two values not in that table are the page background itself (the card has
#: none — Anki supplies it) and the button face.
#: The site's own rules for the ARTICLE FRAGMENT (`<div class="ordbok">` and the caption
#: above it) — they go into `article.css` with the deck's sheets, which the search page links
#: too (site decisions 59: full articles in the results). The article page's own chrome is
#: `PAGE_CSS`, a sheet of its own, so the search page never takes the article page's header
#: and footer rules on top of the shell's (split 2026-10-19).
SITE_CSS = r'''
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0,0,0,0);white-space:nowrap;border:0}
.ordpar-caption{margin:0 0 .2em;font-size:.78rem;font-variant:all-small-caps;
  letter-spacing:.07em;color:#757070}
.nightMode .ordpar-caption{color:#b9b6b6}
.ordpar-article{max-width:none}
.ordpar-hw{margin:0;font-size:1em;font-weight:400;line-height:1.2}
.ordbok-head .ordbok-pos{margin-bottom:.45em}
.ordbok-head .ordbok-pos:last-child{margin-bottom:0}
/* the POS line as ordbokene's (decisions 76): the class in the deck's small capitals, the
   gender or subclass (`article.pos_html`'s <i>) in italic lower case, no brackets */
.ordbok-pos i{font-style:italic;font-variant:normal;text-transform:lowercase;letter-spacing:normal}
/* its size (decisions 76, the style lab's variant 3, the word class at 1.0):
   the body text's own size, the class and its italic part alike, in the deck's muted grey kept
   (the deck's .8em, 12.8 px, overridden site-side; ordbokene's 20 / 16 px are in the text colour) */
.ordbok-pos{font-size:1em}
/* the summary gloss under the headword groups (decisions 42): the authored salience order;
   each item's sense mark (a superscript link to #def<N>) comes with the sense tags. Semibold
   and 1.1x the body, in the article's text colour, to stand out a little more (decisions 59);
   the full search results inherit it, the list view's one-line snippet does not */
.ordpar-gloss{margin:.4em 0 0;font-size:1.1em;font-weight:600;line-height:1.35}
.ordpar-gloss sup{font-weight:400}
.ordpar-gloss sup{font-size:.7em;line-height:0;margin-left:.1em}
.ordpar-en{display:block}
/* the definition line pair (decisions 53, 54): the Norwegian line first, the English beneath
   it. The rules here are the NORWEGIAN-EMPHASIZED look — the Norwegian in the main style, the
   English in the translation style, as the examples are; the default until decisions 87, now
   the setting `emph` = no (`ordpar-emph-no`) and the look under `defs = no`; the default again
   since site decisions 174 (2026-11-07), English emphasized (decisions 87, below: "the emphasized
   line") the default in between and the look with no class. The device setting `defs` (a
   class on <html>, from the head script): `ordpar-defs-en` shows the English alone, in the main
   style; `ordpar-defs-no` the Norwegian, with the English behind the "Show English" cue the
   page script adds (`.ordpar-open` once revealed) */
.ordpar-pair{display:flex;flex-direction:column}
.ordbok-inline .ordpar-pair{display:inline-flex}
.ordpar-pair>span[lang=en]{color:#757070;font-size:.95em;margin-top:.1em}
html.nightMode .ordpar-pair>span[lang=en]{color:#b9b6b6}
html.ordpar-defs-en .ordpar-pair>span[lang=nb]{display:none}
html.ordpar-defs-en .ordpar-pair>span[lang=en]{color:inherit;font-size:1em;margin-top:0}
html.ordpar-defs-no .ordpar-pair:not(.ordpar-open)>span[lang=en]{display:none}
/* a translated page's untranslated set phrases (decisions 58 as amended): whole in Norwegian
   after the translated ones, under a small label; "English only" hides them, and the whole
   section where none is translated */
.ordpar-untr-head{margin:.9em 0 .3em;font-size:.9em;font-style:italic;color:#757070}
html.nightMode .ordpar-untr-head{color:#b9b6b6}
html.ordpar-defs-en .ordpar-untr,html.ordpar-defs-en .ordpar-untr-only{display:none}
/* the mini of a translated target is the same line pair, with no reveal (Robin, 2026-10-18):
   both lines show unless the resolved setting `mini` is `en` (`ordpar-mini-en`, the English
   alone); its English line in the article's muted grey since decisions 70 (the deck's #8b7f84 /
   #a99ba1 until then). Since decisions 80 the mini is cut from the target's page by the mini
   script, which renames each `ordpar-pair` it keeps to `mini-pair`, so these rules — not the
   article's `defs` ones — decide what a mini shows, as before */
/* the mini header's gloss (" — place of residence" after the headword, `mini.js` `header`) in
   the text colour, not the deck's faded #8b7f84 / #a99ba1 (decisions 97: the
   header's glosses in the normal text colour, not faded), light and dark. Since decisions
   114 the deck's own rule takes the text colour too (and the gloss is 1rem, semibold there);
   this rule stays, so the site's look does not hang on the deck's sheet */
.mini-head .mini-gloss,html.nightMode .mini-head .mini-gloss{color:inherit}
.mini-pair,.mini-pair>span{display:block}
.mini-pair>span[lang=en]{color:#757070;font-size:.95em}
.nightMode .mini-pair>span[lang=en]{color:#b9b6b6}
html.ordpar-mini-en .mini-pair>span[lang=nb]{display:none}
html.ordpar-mini-en .mini-pair>span[lang=en]{color:inherit;font-size:1em}
/* the link lives on the line that leads, in the mini as in the article (rule 2): where the
   Norwegian leads (`emph = no`, or `defs = no`) and the mini does not show English alone, its
   English line's hover links are plain words */
html.ordpar-emph-no:not(.ordpar-mini-en) .mini-pair>span[lang=en] .ordbok-xword,
html.ordpar-defs-no:not(.ordpar-mini-en) .mini-pair>span[lang=en] .ordbok-xword{color:inherit;
  border-bottom:0;text-decoration-line:none;pointer-events:none}
html.ordpar-emph-no:not(.ordpar-mini-en) .mini-pair>span[lang=en] .ordbok-xpeek,
html.ordpar-defs-no:not(.ordpar-mini-en) .mini-pair>span[lang=en] .ordbok-xpeek{display:none}
.ordpar-fmini .mini-pair>span[lang=en]{margin-top:.1em}
html.ordpar-mini-en .ordpar-fmini .mini-pair>span[lang=en]{margin-top:0}
/* the article's partner words (decisions 54, as links since decisions 80): where the Norwegian
   leads — `emph = no` with both lines shown, or `defs = no` — a plain word, its peek hidden: the
   link lives on the line that leads. (`text-decoration-line`, not the shorthand, so a rule that
   makes one a link again keeps the accent underline). Every rule here that reaches a link or a peek
   INSIDE an article line pair ends in `:where(:not(.ordbok-xmini *))` (decisions 91): a mini opened
   from a line sits inside it, and its own links follow the mini's rules (`.mini-pair`, `mini`, `emph`),
   not the line's; `:where` adds no specificity, so the cascade is as before outside a mini */
html.ordpar-emph-no:not(.ordpar-defs-en) .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword:where(:not(.ordbok-xmini *)),
html.ordpar-defs-no .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword:where(:not(.ordbok-xmini *)){color:inherit;
  text-decoration-line:none;pointer-events:none;cursor:auto}
html.ordpar-emph-no:not(.ordpar-defs-en) .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xpeek:where(:not(.ordbok-xmini *)),
html.ordpar-defs-no .ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xpeek:where(:not(.ordbok-xmini *)){display:none}
/* THE EMPHASIZED LINE (decisions 87, Robin 2026-10-22: the pairtone style lab's variant 3, "with
   having this be the default"; the links "should go to the emphasized line"). The setting `emph`
   = en (no class: the look with JavaScript off too; the default until site decisions 174) | no
   (`ordpar-emph-no`, the look above; the default since 174, the head script's class unless en is
   stored).
   Under `en`, wherever both lines of a pair show and `defs` is not `no` (which keeps the Norwegian
   leading and the English behind its reveal, whatever `emph` says): the English line in the text
   colour at 1em, the Norwegian faded — the muted grey (`--ordpar-muted`: #757070, at night
   #b9b6b6) at .95em; the English line's partner words are the links, with their peek, and the
   Norwegian line's links plain words with none. Definition, subsense, set-phrase-sense, formula
   (`formulas = both`) and etymology (`ety = both`) lines, in a mini alike (`.mini-pair`); a line
   alone (a formula line under `formulas = no`, the etymology under `ety = no`) leads, so it is
   left in the main style with its links — hence three selectors: definitions (`.ordbok-def`, not
   a formula), formula lines, the etymology (`.ordbok-body`). The examples are not line pairs and
   never change (the Norwegian leads there), nor do an untranslated page's one-language lines */
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .ordpar-pair>span[lang=en],
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .mini-pair>span[lang=en]{color:inherit;font-size:1em}
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .ordpar-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb],
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no) .ordpar-fml.ordpar-pair>span[lang=nb],
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no) .ordpar-pair>span.ordbok-body[lang=nb],
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .mini-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb],
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no) .ordpar-fml.mini-pair>span[lang=nb],
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no) .mini-pair>span.ordbok-body[lang=nb]{
  color:var(--ordpar-muted,#757070);font-size:.95em}
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .ordpar-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb] .ordbok-xword:where(:not(.ordbok-xmini *)),
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no) .ordpar-fml.ordpar-pair>span[lang=nb] .ordbok-xword:where(:not(.ordbok-xmini *)),
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no) .ordpar-pair>span.ordbok-body[lang=nb] .ordbok-xword:where(:not(.ordbok-xmini *)),
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .mini-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb] .ordbok-xword,
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no) .ordpar-fml.mini-pair>span[lang=nb] .ordbok-xword,
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no) .mini-pair>span.ordbok-body[lang=nb] .ordbok-xword{
  color:inherit;border-bottom:0;text-decoration-line:none;pointer-events:none;cursor:auto}
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .ordpar-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb] .ordbok-xpeek:where(:not(.ordbok-xmini *)),
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no) .ordpar-fml.ordpar-pair>span[lang=nb] .ordbok-xpeek:where(:not(.ordbok-xmini *)),
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no) .ordpar-pair>span.ordbok-body[lang=nb] .ordbok-xpeek:where(:not(.ordbok-xmini *)),
html:not(.ordpar-emph-no):not(.ordpar-defs-no) .mini-pair:not(.ordpar-fml)>span.ordbok-def[lang=nb] .ordbok-xpeek,
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-formulas-no) .ordpar-fml.mini-pair>span[lang=nb] .ordbok-xpeek,
html:not(.ordpar-emph-no):not(.ordpar-defs-no):not(.ordpar-ety-no) .mini-pair>span.ordbok-body[lang=nb] .ordbok-xpeek{display:none}
/* formula lines (decisions 81, Robin 2026-10-21): a pair marked `ordpar-fml` ("brukt som adverb:")
   shows one language in every `defs` setting, the setting `formulas` saying which — `en` (no class;
   the default until site decisions 174) the English alone, in the main style and with no reveal;
   `no` (`ordpar-formulas-no`) the Norwegian alone; `both` (`ordpar-formulas-both`, the default since
   174, the head script's class unless en or no is stored) both lines, in every `defs` setting (below).
   In a mini alike */
html:not(.ordpar-formulas-no):not(.ordpar-formulas-both) .ordpar-fml.ordpar-pair>span[lang=nb],
html:not(.ordpar-formulas-no):not(.ordpar-formulas-both) .ordpar-fml.mini-pair>span[lang=nb]{display:none}
html:not(.ordpar-formulas-no):not(.ordpar-formulas-both) .ordpar-fml.ordpar-pair>span[lang=en],
html:not(.ordpar-formulas-no):not(.ordpar-formulas-both) .ordpar-fml.mini-pair>span[lang=en]{display:block;
  color:inherit;font-size:1em;margin-top:0}
html.ordpar-formulas-no .ordpar-fml.ordpar-pair>span[lang=en],
html.ordpar-formulas-no .ordpar-fml.mini-pair>span[lang=en]{display:none}
html.ordpar-formulas-no .ordpar-fml.ordpar-pair>span[lang=nb],
html.ordpar-formulas-no .ordpar-fml.mini-pair>span[lang=nb]{display:block}
html:not(.ordpar-formulas-both) .ordpar-fml.ordpar-pair>.ordpar-encue{display:none}
/* a compound list's label (decisions 81): English, or under `formulas = no` ordbokene's Norwegian
   intro ("som etterledd i ord som"); `both` keeps the English (Robin, 2026-10-21) */
.ordpar-cl-nb{display:none}
html.ordpar-formulas-no .ordpar-cl-en{display:none}
html.ordpar-formulas-no .ordpar-cl-nb{display:inline}
/* the words in a translated page's pronunciation field (decisions 123, `pronunciation.py`): "in the
   plural", "or" — English, or under `formulas = no` the field's own Norwegian ("i flertall",
   "eller"); `both` keeps the English, as the compound labels. On a Norwegian-only page the words
   are Norwegian alone, no pair. The section takes the etymology line's look (`ordbok-inline`); the
   note on the marks is Help's alone since decisions 123's amendment (the "?"
   beside the label took space and attention for nothing), on the site and the deck alike */
.ordpar-pg-nb{display:none}
html.ordpar-formulas-no .ordpar-pg-en{display:none}
html.ordpar-formulas-no .ordpar-pg-nb{display:inline}
/* the label upright, in both languages and every Formula lines setting, as ordbokene's (decisions
   81, from the style lab: upright for both languages, Norwegian and
   English): the label is the first <em> of the list's line, the deck's italic overridden; an
   untranslated page's one label alike. The compounds after it keep their own look */
.ordbok .ordpar-comp>.ordbok-def>em:first-child{font-style:normal}
/* a set phrase's "Se:" line on its own page (decisions 153, `article.see_html`): a line of its own
   after the definition, as ordbokene draws it; its label the compound label's two spans above */
.ordpar-see{display:block}
/* the etymology line (decisions 84, Robin 2026-10-21), modelled on the formula lines: the
   etymology section is the one inline section holding a line pair (`.ordbok-inline>.ordpar-pair`;
   in a mini, the senseless page's pair the mini script copies to the body's top level,
   `.ordpar-mbody>.mini-pair`). The setting `ety` says which line shows, in every `defs` and
   `mini` setting — `en` (the default) the English alone, in the main style and with no reveal;
   `no` (`ordpar-ety-no`) the Norwegian alone; `both` (`ordpar-ety-both`) both lines, in every
   `defs` setting (below) */
html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>span[lang=nb],
html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordpar-mbody>.mini-pair>span[lang=nb]{display:none}
html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>span[lang=en],
html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordpar-mbody>.mini-pair>span[lang=en]{display:block;
  color:inherit;font-size:1em;margin-top:0}
html.ordpar-ety-no .ordbok-inline>.ordpar-pair>span[lang=en],
html.ordpar-ety-no .ordpar-mbody>.mini-pair>span[lang=en]{display:none}
html.ordpar-ety-no .ordbok-inline>.ordpar-pair>span[lang=nb],
html.ordpar-ety-no .ordpar-mbody>.mini-pair>span[lang=nb]{display:block}
html.ordpar-defs-no:not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>.ordpar-encue{display:none}
/* the English line alone leads, so its partner words are links again (the link lives on the line
   that leads, as under `defs = en` / `mini = en`): underlined, clickable, their peek on hover; never
   in a mini opened from the line (decisions 91, above) */
html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword:where(:not(.ordbok-xmini *)),
html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordpar-mbody>.mini-pair>span[lang=en] .ordbok-xword{text-decoration-line:underline;
  pointer-events:auto;cursor:pointer}
@media (hover:hover){
  html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>span[lang=en] .ordpar-xen:hover>.ordbok-xpeek:where(:not(.ordbok-xmini *)),
  html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordpar-mbody>.mini-pair>span[lang=en] .ordbok-xref:hover>.ordbok-xpeek{display:block}
}
/* "both" is both lines in every `defs` setting (decisions 80's finding 2, Robin 2026-10-22;
   amends 84 and 81): under `defs = en` the etymology line with `ety = both`, and a formula line
   with `formulas = both`, stay the line pair they are under `defs = both` — the Norwegian line,
   the English beneath it — and since decisions 87 it follows the emphasis like any pair: under
   `emph = en` (the default) the rules of the emphasized line above (the English in the main
   style, its partner words the links, the Norwegian faded and plain); under `emph = no` the
   English in the muted grey, the link on the Norwegian line (54): the English line's partner
   words plain, their peek hidden. Under `defs = no` the English stays behind its reveal, as
   before. In a mini the same under `mini = en` (the session's reading), the Norwegian leading
   there under `emph = no` or `defs = no` */
html.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=nb],
html.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=nb],
html.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=nb],
html.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=nb]{display:block}
html.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en],
html.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=en],
html.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en],
html.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en]{margin-top:.1em}
html.ordpar-emph-no.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en],
html.ordpar-emph-no.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=en],
html.ordpar-emph-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en],
html.ordpar-emph-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en],
html.ordpar-defs-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en],
html.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en]{color:#757070;
  font-size:.95em}
html.nightMode.ordpar-emph-no.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en],
html.nightMode.ordpar-emph-no.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=en],
html.nightMode.ordpar-emph-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en],
html.nightMode.ordpar-emph-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en],
html.nightMode.ordpar-defs-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en],
html.nightMode.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en]{color:#b9b6b6}
html.ordpar-emph-no.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword:where(:not(.ordbok-xmini *)),
html.ordpar-emph-no.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xword:where(:not(.ordbok-xmini *)),
html.ordpar-emph-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en] .ordbok-xword,
html.ordpar-emph-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en] .ordbok-xword,
html.ordpar-defs-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en] .ordbok-xword,
html.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en] .ordbok-xword{color:inherit;
  border-bottom:0;text-decoration-line:none;pointer-events:none;cursor:auto}
html.ordpar-emph-no.ordpar-defs-en.ordpar-ety-both .ordbok-inline>.ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xpeek:where(:not(.ordbok-xmini *)),
html.ordpar-emph-no.ordpar-defs-en.ordpar-formulas-both .ordpar-fml.ordpar-pair>span[lang=en] .ordpar-xen>.ordbok-xpeek:where(:not(.ordbok-xmini *)),
html.ordpar-emph-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en] .ordbok-xpeek,
html.ordpar-emph-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en] .ordbok-xpeek,
html.ordpar-defs-no.ordpar-mini-en.ordpar-ety-both .ordpar-mbody>.mini-pair>span[lang=en] .ordbok-xpeek,
html.ordpar-defs-no.ordpar-mini-en.ordpar-formulas-both .ordpar-fml.mini-pair>span[lang=en] .ordbok-xpeek{display:none}
/* the "Show English" cue: the deck's reveal cue, as a button the page script inserts (the
   article's line pairs under `defs = no`; every example under `examples = no`, below). Its text in
   the muted grey since decisions 111 (the deck's `.ordbok-cue`, `DECK_MUTED`) */
.ordpar-encue{display:none;align-self:flex-start;font-family:inherit;background:none;
  cursor:pointer}
html.ordpar-defs-no .ordpar-pair:not(.ordpar-open)>.ordpar-encue{display:inline-block}
html.ordpar-defs-no:not(.ordpar-formulas-both) .ordpar-fml.ordpar-pair>.ordpar-encue{display:none}
html.ordpar-defs-no .ordpar-open>span[lang=en]{cursor:pointer}
/* the examples' English behind the same cue (decisions 111, Robin 2026-10-23): the setting
   `examples` = both (default) | no -> `ordpar-examples-no`. Every example with an English line
   (`li>.ordpar-en`: Bokmålsordboka's and our added ones, in an article, a search result, a set
   phrase and a mini) shows its Norwegian, then the cue the page script inserts before the English
   (`.ordpar-excue`), on a line of its own as the deck's; a click opens the example (`.ordpar-open`
   on its `li`), a click on the opened English closes it again, as a definition's. An example
   with no English gets no cue. Independent of `defs` */
html.ordpar-examples-no .ordbok-ex-list>li:not(.ordpar-open)>.ordpar-en{display:none}
html.ordpar-examples-no .ordbok-ex-list>li:not(.ordpar-open)>.ordpar-excue{display:block;width:fit-content}
html.ordpar-examples-no .ordbok-ex-list>li.ordpar-open>.ordpar-en{cursor:pointer}
/* the eye (decisions 131: the deck's eye as an optional setting a reader can turn on,
   off by default): `exeye` = off (default) | on -> `ordpar-exeye-on`. With it on,
   the page script puts a button beside the headword of every article shown whole that has an
   example with English (`eyes`: an article page, a word page, a search's full result, an article
   opened in a list row; never a mini). Its look is the deck's (style lab toggle.html, preset E: the
   eye at the headword, floated right, a round outline in the cue's grey, filled with the accent and
   the eye struck through while pressed), in the site's colours. Pressed = that article's examples'
   English hidden: under `examples = both` the article gets `ordpar-exhide`, which hides them as
   `ordpar-examples-no` does (each then opened by its "Show English" cue); under `examples = no`
   pressing it again opens every example of the article (`.ordpar-open`). Never reaches a mini. */
.ordpar-exeye{float:right;margin:.35rem 0 .2rem .6rem}
html:not(.ordpar-exeye-on) .ordpar-exeye{display:none}
.ordpar-exeye>button{display:inline-flex;align-items:center;vertical-align:middle;position:relative;
  font:inherit;font-size:1rem;line-height:1.3;color:var(--ordpar-muted,#757070);cursor:pointer;
  -webkit-user-select:none;user-select:none;padding:.36em;margin:0;border:1px solid #c4bcbd;
  border-radius:999px;background:none}
.nightMode .ordpar-exeye>button{border-color:#656161}
.ordpar-exeye>button svg{display:block;width:1.35em;height:1.35em}
.ordpar-exeye>button .ordpar-i-off,.ordpar-exeye>button[aria-pressed=true] .ordpar-i-on{display:none}
.ordpar-exeye>button[aria-pressed=true] .ordpar-i-off{display:block}
.ordpar-exeye>button[aria-pressed=true]{background:var(--ordpar-accent);border-color:var(--ordpar-accent);
  color:var(--ordpar-accent-text,#fff)}
/* an unseen tap area of at least 44 x 44 px, the deck's. The button is styled through its span
   (`.ordpar-exeye>button`), not its own class: the deck's cards share this sheet and the page
   script but never show the eye, and `deck/assets.py` refuses a class a button carries that the
   sheet styles outside its BUTTON_CLASSES */
.ordpar-exeye>button::before{content:"";position:absolute;top:min(0px,calc(50% - 22px));
  bottom:min(0px,calc(50% - 22px));left:min(0px,calc(50% - 22px));right:min(0px,calc(50% - 22px))}
.ordpar-exhide .ordbok-ex-list:not(.ordbok-xmini *)>li:not(.ordpar-open)>.ordpar-en{display:none}
.ordpar-exhide .ordbok-ex-list:not(.ordbok-xmini *)>li:not(.ordpar-open)>.ordpar-excue{display:block;width:fit-content}
.ordpar-exhide .ordbok-ex-list:not(.ordbok-xmini *)>li.ordpar-open>.ordpar-en{cursor:pointer}
/* what the eye hides (decisions 186): `exeyewhat` = examples (default) | all -> `ordpar-exeye-all`.
   Under all a press blanks its article (`ordpar-blanked`, the page script's `blank`): every English
   line but the etymology's hidden (`.ordpar-eyehid`), each behind the site's "Show English" cue as
   the examples' cue stands (its look, size and margin, nothing added; inline on a set phrase's
   "Eng. phrase" row), in the line's place; under a cue the make-up of the hidden line's height
   (`.ordpar-eyefill`). A line shown by its cue (`.ordpar-eyeshown`) hides again at a press. No hover
   peek in a blanked article (a small article's own kept), and in a list row its glosses go too. The
   cue is styled through its attribute, never a class of its own: the deck shares this sheet and the
   page script, and `deck/assets.py` refuses a styled button class outside its BUTTON_CLASSES */
.ordpar-eyehid{display:none!important}
.ordbok-cue[data-ordpar-eyecue]{display:block;width:fit-content;font-family:inherit;background:none;cursor:pointer}
.ordbok-idiom .ordbok-cue[data-ordpar-eyecue]{display:inline-block}
.ordpar-eyefill{display:block}
.ordpar-eyeshown{cursor:pointer}
.ordpar-blanked .ordbok-xpeek:not(.ordbok-xmini *){display:none!important}
.ordpar-row-blanked .ordpar-row-snippet{display:none}
/* the examples limit per sense (decisions 112, Robin 2026-10-23): `exlimit` = all (default) |
   1 … 10 -> `ordpar-exlimit-<n>` on <html>, set by the head script before the first paint. Every
   example list — a sense's or a subsense's, in an article, a search result, a list or favourites
   row's article and a set phrase; never a mini's, which keeps its own cap (`mini.js` EX_BUDGET) —
   shows its first n items in the page's order: Bokmålsordboka's, then our added ones ("+"), which
   count. A list opened by its "Show N more examples" line (`.ordpar-exopen`) shows them all. The
   line (`li.ordpar-exmore`, inserted by the page script under a cut list) is a button in the "Show
   English" cue's look (`.ordbok-cue`, one style); `exmore = off` -> `ordpar-exmore-off` hides it */
@EXLIMIT@
.ordbok-ex-list>li.ordpar-exmore{margin-top:.15em}
.ordpar-exbtn{font-family:inherit;background:none;cursor:pointer}
html.ordpar-exmore-off .ordbok-ex-list>li.ordpar-exmore,
html:not([class*="ordpar-exlimit-"]) .ordbok-ex-list>li.ordpar-exmore{display:none}
/* the hover peek as a setting (decisions 54): `peek = off` hides every one, minis too */
html.ordpar-peek-off .ordbok-xpeek{display:none!important}
/* SITE DECISIONS 152 (Robin, 2026-10-30/31): NORWEGIAN ONLY, a layer over the reader's settings
   (`ordpar-nbo`, from the head script; `shell.js` `layer`). The classes of the settings it answers
   for are drawn from its values (Definitions and Examples Norwegian, the formula lines and the
   etymology Norwegian, the small articles as the article); these rules hide what no setting
   reaches, so the articles show their Norwegian only, with nothing to reveal: the "Show English"
   cues and every English definition, formula, etymology and example line however opened (in a
   small article too), the eye, the "Eng. phrase" lines, the "not yet translated" sub-heading, the
   untranslated article's caption and note, the rows' "Norwegian only" tag. Ordpar's added
   examples stay, with their "+". The layout and the look stay the reader's */
html.ordpar-nbo .ordpar-encue,html.ordpar-nbo .ordpar-exeye,html.ordpar-nbo .ordbok-idiom,
html.ordpar-nbo .ordpar-pair>span[lang=en],html.ordpar-nbo .mini-pair>span[lang=en],
html.ordpar-nbo .ordbok-ex-list>li>.ordpar-en,html.ordpar-nbo .ordpar-untr-head,
html.ordpar-nbo .ordpar-caption,html.ordpar-nbo .ordpar-caption+.ordpar-note,
html.ordpar-nbo .ordpar-tag{display:none!important}
/* "English equivalents" hidden (`ordpar-nbo-noeq`, the default under the layer): the summary
   glosses under the headword, in an article and a small article, and every row's English (the
   rows' Norwegian definitions, or nothing, `ordpar-nbo-rows0`, are the scripts' and the next rules) */
html.ordpar-nbo-noeq .ordpar-gloss,html.ordpar-nbo-noeq .mini-gloss,
html.ordpar-nbo-noeq :not(.ordpar-option-en)>.ordpar-option-side>.ordpar-option-gloss:lang(en),
html.ordpar-nbo-noeq :not(.ordpar-option-en)>.ordpar-option-side>.ordpar-option-glosses:lang(en),
html.ordpar-nbo-noeq .ordpar-option-glosses:lang(en)~.ordpar-option-count,
html.ordpar-nbo-noeq .ordpar-row-snippet:lang(en),html.ordpar-nbo-noeq .ordpar-hit-snippet:lang(en){display:none!important}
/* a built row (a word or form page) ships its Norwegian definition beside the English one,
   hidden (`wordpages`, `ordpar-nbsnip`, `data-nosnippet`): shown in its place with the rows on
   "Norwegian definition" */
.ordpar-nbsnip{display:none}
html.ordpar-nbo-noeq:not(.ordpar-nbo-rows0) .ordpar-row-snippet.ordpar-nbsnip,
html.ordpar-nbo-noeq:not(.ordpar-nbo-rows0) .ordpar-hit-snippet.ordpar-nbsnip{display:block}
/* the rows' right side "nothing", as ordbokene's (`nbrows` = none) */
html.ordpar-nbo-rows0 :not(.ordpar-option-en)>.ordpar-option-side,
html.ordpar-nbo-rows0 .ordpar-row-snippet,html.ordpar-nbo-rows0 .ordpar-hit-snippet{display:none!important}
/* the hovers on "Norwegian definition" (`nbhover` = nbdef, or outside the layer `peek` = nb, site
   decisions 185; `ordpar-nbo-hovnb`): the English peeks
   hidden, each link's own Norwegian peek (`.ordpar-nbpk`, made by the mini script from the
   target's `snip/` file) shown on hover as any peek; never without that class */
html.ordpar-nbo-hovnb .ordbok-xpeek:not(.ordpar-nbpk){display:none!important}
html:not(.ordpar-nbo-hovnb) .ordbok-xpeek.ordpar-nbpk{display:none!important}
/* THE LABELS (site decisions 152, the setting `labels`): a label inside the article frame ships in
   both languages, `.ordpar-l-en` and `.ordpar-l-nb` (`data-nosnippet` on the Norwegian copy, the
   one the default hides, 154); `ordpar-labels-no` shows the Norwegian. The word class and the
   inflection tables' words (`.ordpar-w-en`, `.ordpar-w-nb`) follow the labels or the layer — and
   since 152's follow-up (the labels too become Norwegian with the Norwegian
   only setting turned on) so do the labels: `ordpar-nbo` shows every Norwegian copy whatever
   `labels` says, the stored value never written; the layer off, the reader's own choice again */
.ordpar-l-nb,.ordpar-w-nb{display:none}
html.ordpar-labels-no .ordpar-l-en,html.ordpar-labels-no .ordpar-w-en,html.ordpar-nbo .ordpar-l-en,html.ordpar-nbo .ordpar-w-en{display:none}
html.ordpar-labels-no .ordpar-l-nb,html.ordpar-labels-no .ordpar-w-nb,html.ordpar-nbo .ordpar-l-nb,html.ordpar-nbo .ordpar-w-nb{display:inline}
/* the headword's Norwegian-only icon (site decisions 152, Robin's pick (a)): for a page whose header
   is hidden (the Definer pop-up), made by the page script beside every article head shown whole
   (never a small article) and hidden here; only the extra rule in `/more/`'s CSS line for Definer
   shows it (`.ordpar-nbhw{display:inline-flex !important}`). Drawn as the eye; filled while on */
.ordpar-nbhw{display:none;float:right;margin:.35rem 0 .2rem .6rem}
.ordpar-nbhw>button{display:inline-flex;align-items:center;vertical-align:middle;position:relative;
  font:inherit;font-size:1rem;line-height:1.3;color:var(--ordpar-muted,#757070);cursor:pointer;
  -webkit-user-select:none;user-select:none;padding:.36em;margin:0;border:1px solid #c4bcbd;
  border-radius:999px;background:none}
.nightMode .ordpar-nbhw>button{border-color:#656161}
.ordpar-nbhw>button svg{display:block;width:1.35em;height:1.35em}
.ordpar-nbhw>button[aria-pressed=true]{background:var(--ordpar-accent);border-color:var(--ordpar-accent);
  color:var(--ordpar-accent-text,#fff)}
.ordpar-nbhw>button::before{content:"";position:absolute;top:min(0px,calc(50% - 22px));
  bottom:min(0px,calc(50% - 22px));left:min(0px,calc(50% - 22px));right:min(0px,calc(50% - 22px))}
/* the inflection table behind a pill toggle, closed by default, as ordbokene's results list
   (Robin, 2026-09-24); the device setting `infl = open` opens it (PAGE_JS) */
.ordpar-infl-toggle{margin:.5em 0 .9em}
.ordpar-infl-toggle>summary{display:inline-flex;align-items:center;gap:.55em;cursor:pointer;
  list-style:none;padding:.15em .8em .15em 1em;border:1px solid var(--ordpar-maroon,@DAY@);border-radius:2em;
  font-size:.95rem;line-height:1.5;user-select:none}
.ordpar-infl-toggle>summary::-webkit-details-marker{display:none}
.ordpar-infl-toggle>summary::after{content:"";width:.4em;height:.4em;margin-top:-.2em;
  border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;
  transform:rotate(45deg)}
.ordpar-infl-toggle[open]>summary::after{margin-top:.2em;transform:rotate(-135deg)}
.ordpar-infl-toggle>summary:hover{background:rgba(var(--ordpar-maroon-rgb,@DAY_RGB@),.06)}
.nightMode .ordpar-infl-toggle>summary{border-color:var(--ordpar-tint,#e3b7c9)}
.nightMode .ordpar-infl-toggle>summary:hover{background:rgba(var(--ordpar-tint-rgb,227,183,201),.1)}
/* the table keeps to its card's content box, everywhere (decisions 102;
   replacing 43's growth past the text column towards the window): the mount fills
   the box and never passes it, and inflection.js `fit` shows the wide table wherever its
   unwrapped width fits the box and the narrow one where it does not, at load and again when
   the box changes width; a narrow table still too wide scrolls inside its own strip */
.ordpar-inflection{margin:.2em 0 0;max-width:100%}
/* the text runs at the card's width, as ordbokene's (decisions 102 (3)): no cap inside the
   card — the deck's `.ordbok` caps its column at 40em, centred */
.ordpar-main .ordbok{max-width:none}
/* the cross-references in ordbokene's style (decisions 63, Robin 2026-10-19): upright, in the
   surrounding text's colour, with a solid underline in the accent — at night the scheme's
   night line (ordbokene's maroon: its #880e4f) or its tint. Overrides the deck's italic,
   coloured, dotted look site-side (later in this sheet, same specificity); the hover and the
   opened-mini backgrounds are the deck's, kept. The `em` rule needs `.ordbok` to beat
   `.ordbok em` */
.ordbok-xword{color:inherit;font-style:normal;border-bottom:0;text-decoration:underline;
  text-decoration-color:var(--ordpar-maroon,@DAY@);text-decoration-thickness:1.5px;
  text-underline-offset:3px}
.nightMode .ordbok-xword{color:inherit;
  text-decoration-color:var(--ordpar-night-line,var(--ordpar-tint,#e3b7c9))}
.ordbok .ordbok-xword em{font-style:normal}
/* the mini's headword reads as the link it is (decisions 78: the style lab's
   variant 5, the clearest sign that it is still a link): upright, in the text's
   colour, with the article body's link underline. The Style setting `minihw` = article
   (`ordpar-minihw-article` on <html>) gives it the article headword's look instead: semibold,
   coloured, upright, no underline (the deck's colour and hover underline, kept) */
.mini-hw{font-style:normal}
html:not(.ordpar-minihw-article) .mini-hw{color:inherit}
html:not(.ordpar-minihw-article) .mini-hw a{text-decoration:underline;
  text-decoration-color:var(--ordpar-maroon,@DAY@);text-decoration-thickness:1.5px;
  text-underline-offset:3px}
html.nightMode:not(.ordpar-minihw-article) .mini-hw a{
  text-decoration-color:var(--ordpar-night-line,var(--ordpar-tint,#e3b7c9))}
/* the headword at semibold (decisions 63: the deck's 700 slightly too
   thick; same size, font and colour) — the article page and the results' cards alike */
.ordbok-lemma{font-weight:600}
/* the mini's body formatted as the article's (decisions 70, Robin 2026-10-20). A link inside a
   mini is an <a class="ordbok-xword">, so the deck's `.ordbok a` colour outranked the rule above
   (0,1,1 against 0,1,0): the link takes the text's colour here too, by day and night, under
   every scheme. On a touch screen the article shows no peek; the deck printed a mini's peek
   inline after the word, in quotes — now hidden there too (the mini's hover links show their
   peek on hover, as the article's). Then the body's colours as the article's: the text, the
   muted grey of the English lines, the examples' translations, the etymology, the "added"
   mark and the no-definition note, the sense numbers' night grey, the set phrase's night
   colour, the subsense rule; and the article's proportions inside the mini's own, smaller
   scale (.92rem): an example as large as its definition, its translation .95 of it, the
   compound line as a definition. Kept, as the pop-up's own: its width, padding, ground,
   border and shadow, the .92rem scale and 1.45 line height, the heading (the italic headword
   and its gloss), the examples' left rule, and the etymology's italic (it has no label) */
.ordbok a.ordbok-xword,.nightMode .ordbok a.ordbok-xword{color:inherit}
@media (hover:none){
  .mini .ordbok-xpeek,.mini .ordbok-xref:hover>.ordbok-xpeek{display:none}
}
.mini{color:#222}
.nightMode .mini{color:#d9d6d6}
.mini-exen,.mini-ety,.mini-added,.mini-nodef{color:#757070}
.nightMode .mini-exen,.nightMode .mini-ety,.nightMode .mini-added,.nightMode .mini-nodef{color:#b9b6b6}
.mini-exno{font-size:.92rem}
.mini-exen{font-size:.874rem}
.mini-comp{font-size:.92rem;color:inherit}
.nightMode .mini-comp{color:inherit}
.mini-sub,.mini-ex2,.mini-comp{border-left-color:#e0d8d9}
.nightMode .mini-sub,.nightMode .mini-ex2,.nightMode .mini-comp{border-left-color:#656161}
.nightMode .mini-snum{color:#b9b6b6}
.nightMode .mini-expr-term{color:#fdf4f5}
/* the mini inside the window (decisions 69): never wider than the window, 0.5rem short of each
   edge; the page script (`place`) moves an opened mini left where it would pass the right edge */
.ordbok-xmini{max-width:calc(100vw - 1rem)}
/* the mini made from the target's own page (decisions 80, Robin 2026-10-21; `ordpar/site/mini.js`).
   The script puts `ordpar-mopen` on the link's `.ordbok-xref` and the mini and a backdrop in it
   (the deck's `.ordbok-xmini` / `.ordbok-xback`, placed as before): the mini box is the deck's
   `.mini` (border, shadow, width, padding, its heading), its body the article's own markup at
   the article's own size (1rem since decisions 114, Robin 2026-10-24; .92 until then, A5), so
   the article's sheet styles it — the examples as the
   article's list (a quote block since decisions 87), compound lists after the examples and
   subsenses */
.ordbok-xref.ordpar-mopen>.ordbok-xmini,.ordbok-xref.ordpar-mopen>.ordbok-xback{display:block}
/* an opened mini always hides its link's hover peek (decisions 80, finding 1, Robin 2026-10-22):
   `!important`, so no showing rule outranks it, however specific — the etymology line's (84)
   did, under its default, until then. It only ever hides, as `peek = off`'s does */
.ordbok-xref.ordpar-mopen>.ordbok-xpeek{display:none!important}
.ordbok-xref.ordpar-mopen>.ordbok-xword{background:rgba(var(--ordpar-maroon-rgb,@DAY_RGB@),.1);
  border-radius:.15em}
.nightMode .ordbok-xref.ordpar-mopen>.ordbok-xword{background:rgba(var(--ordpar-tint-rgb,227,183,201),.14)}
.ordpar-fmini{line-height:1.5}
.ordpar-mbody{margin-top:.55rem;font-size:1rem}
.ordpar-mbody>:last-child,.ordpar-mbody .ordbok-senses>li:last-child,
.ordpar-mbody .ordbok-sub:last-child{margin-bottom:0}
.ordpar-mbody>.ordbok-sub:first-child{margin-top:0}
.ordpar-mbody .ordbok-body{display:block;margin-bottom:.3em}
.ordpar-mbody .ordbok-nodef{display:block}
.ordpar-fmini[aria-busy=true] .ordpar-mbody::after{content:"\2026";color:#757070}
/* the setting `minispacing` (decisions 80; the default `article` since decisions 97, Robin
   2026-10-23): `article` the article's own spacing, with no class; `compact`
   (`ordpar-minispacing-compact`) the style lab's minifit variant 5 — the box at line height 1.3
   and less padding, the senses .3rem apart, .12rem inside a sense, the examples .05em, the
   subsenses and compound lists .35rem above and .2rem below. The examples are a flex column so
   their gap is not doubled by collapsing margins */
html.ordpar-minispacing-compact .ordpar-fmini{line-height:1.3;padding:.6rem .75rem}
html.ordpar-minispacing-compact .ordpar-mbody{margin-top:.35rem}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-senses>li{margin-bottom:.3rem}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-ex-list{display:flex;
  flex-direction:column;gap:.12rem;margin-top:.12rem}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-ex-list>li{margin:.05em 0}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-sub,
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-subsenses{margin-top:.35rem;margin-bottom:.2rem}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-subsenses>li{margin-bottom:.2rem}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-idiom{margin-top:.12rem}
html.ordpar-minispacing-compact .ordpar-mbody .ordbok-expr{margin:.3rem 0}
/* the setting `minitext` (decisions 114, Robin 2026-10-24): `article`, the default with no class,
   is the sizes he picked in the style lab — the header line 1.1rem and its gloss 1rem semibold
   (`scripts/mini.py` STYLE, shared with the deck), the body 1rem, the article's own size (above);
   `smaller` (`ordpar-minitext-smaller`) the sizes until then: the header 1.02rem, its gloss and
   the body .92rem. Sizes only: the gloss stays semibold and in the text colour in both, and the
   body's parts keep the article's proportions (each in em) */
html.ordpar-minitext-smaller .mini-head{font-size:1.02rem}
html.ordpar-minitext-smaller .mini-head .mini-gloss{font-size:.92rem}
html.ordpar-minitext-smaller .ordpar-mbody{font-size:.92rem}
/* the setting `miniscroll` (decisions 80): on a computer (a fine pointer that hovers) a tall mini
   scrolls inside its box, at most 70% of the window and 30rem, the page not scrolling with it;
   `off` (`ordpar-miniscroll-off`) shows it whole. Not on a phone, where a scrolling box inside a
   scrolling page fights the finger */
@media (hover:hover) and (pointer:fine){
  html:not(.ordpar-miniscroll-off) .ordpar-fmini{max-height:min(70vh,30rem);overflow-y:auto;
    overscroll-behavior:contain}
}
/* the mini's width on a computer (decisions 80: the style lab's row 7,
   "Fit-to-height <=36rem"; row 6's 32rem until the same day): the box shrinks to its content
   between a floor of 12rem (a one-word mini is no sliver) and a ceiling of 36rem, half the
   window but never below today's 19rem, and never past the window (69); `mini.js` `fit` then narrows it to the narrowest width with the same
   height. Site-side: the deck's 19rem (`scripts/mini.py` STYLE) stays, and so does a phone's */
@media (hover:hover) and (pointer:fine){
  .ordpar-fmini{width:max-content;min-width:12rem;max-width:min(36rem,max(19rem,50vw),calc(100vw - 1rem))}
}
/* the hover peek inside the window too (decisions 69, extended to the peek): the page
   script moves a peek left where it would pass the right edge, and its arrow back by as much, so it still points at the
   word (the arrow kept: Robin, 2026-10-21). The peek and its arrow never take the pointer, so a click
   where the arrow overlaps the word still opens the mini (decisions 77: the whole link stays clickable) */
.ordbok-xpeek{max-width:calc(100vw - 1rem);pointer-events:none}
.ordbok-xpeek::after{left:min(calc(1em + var(--ordpar-peek-dx,0px)),calc(100% - 1.5em))}
/* a Norwegian-only unit's link to one sense of a translated article: the peek is that sense's whole
   English definition line (decisions 119, the style lab's pick, breaking
   as the article), broken where the article breaks it (its `;<br>`), in regular weight (116: the
   definitions are normal text everywhere), a single long clause wrapping at 22rem */
.ordbok-xpeek.ordpar-nbdef{font-weight:400;white-space:normal;width:max-content;max-width:min(22rem,calc(100vw - 1rem))}
/* a peek inside a small article (decisions 141: the mini stays the same size, and the
   hover is still shown whole, past its edge): the mini's box scrolls, so a peek
   placed in it from its word was cut off at the box's edge; on hover `mini.js` `peekFix` draws it against
   the window (`ordpar-pfix`, its left and top set there), above its word as here, or below it where above
   would leave the window (`ordpar-pbelow`, the arrow turned to point up). Only its place: whether it shows
   is still the rules above and below (`peek`, `defs`, `emph`, `mini`) */
.ordbok-xmini .ordbok-xpeek.ordpar-pfix{position:fixed;bottom:auto;right:auto}
.ordbok-xmini .ordbok-xpeek.ordpar-pbelow::after{top:auto;bottom:100%;border-top-color:transparent;
  border-bottom-color:var(--ordpar-maroon,@DAY@)}
.nightMode .ordbok-xmini .ordbok-xpeek.ordpar-pbelow::after{border-top-color:transparent;
  border-bottom-color:var(--ordpar-tint,#e3b7c9)}
/* a small article inside a small article (decisions 139, Robin 2026-10-26; `mini.js`, the setting
   `nestminis`). Stacked: the nested box hangs in the box it opens from, on the page's own layer
   (fixed), placed by `placeNested` below its word, or above it where the room below is short (165),
   over the first; its height, capped by the script at the room on that side, scrolls inside it. Every other rule of the first box (its header,
   spacing, sizes, the Small articles settings) is its own, its shadow and colour too (157, below) */
.ordbok-xmini.ordpar-mnest{display:block;position:fixed;top:0;left:0;z-index:1}
.ordpar-mnest>.mini{overflow-y:auto;overscroll-behavior:contain}
/* THE SMALL ARTICLE'S SHADOW AND, AT NIGHT, ITS COLOUR (site decisions 157, Robin 2026-11-01, his pick
   in the lab `style-lab/mini-shadow.html`): a deeper shadow that darkens the page's text beside the
   box, with a tight edge shadow marking its rim, and at night the box lifted, a shade lighter than
   the card it lies on (it was darker, so it read as sunk). Over `mini.py`'s own `.mini` rules, by
   specificity; the nested box (`.ordpar-mnest`) takes the same. The deck's sheet carries these
   rules too (`deck/assets.py` ships `article.css`), from its next update */
.ordbok-xmini>.mini{box-shadow:0 1px 3px rgba(60,20,40,.12),0 8px 28px rgba(60,20,40,.2)}
.nightMode .ordbok-xmini>.mini{box-shadow:0 1px 3px rgba(0,0,0,.5),0 10px 36px 4px rgba(0,0,0,.8);
  background:#2c2629;border-color:#3e3439}
/* in place: the line back to the word stepped from, at the box's top ("← skip (II)", a button): the
   arrow in the muted grey, the word as the header draws its headword (`.mini-hw`: semibold, upright,
   in its colour under `minihw`), underlined as the header's link on hover and on keyboard focus */
.ordpar-mback{display:block;margin:0 0 .45rem;padding:0;border:0;background:none;font:inherit;
  font-size:.9rem;color:inherit;cursor:pointer;text-align:left}
.ordpar-mback-arrow{color:#757070}
.nightMode .ordpar-mback-arrow{color:#b9b6b6}
.ordpar-mback:hover .mini-hw,.ordpar-mback:focus-visible .mini-hw{text-decoration:underline;
  text-decoration-color:var(--ordpar-maroon,@DAY@);text-decoration-thickness:1.5px;text-underline-offset:3px}
.nightMode .ordpar-mback:hover .mini-hw,.nightMode .ordpar-mback:focus-visible .mini-hw{
  text-decoration-color:var(--ordpar-night-line,var(--ordpar-tint,#e3b7c9))}
/* THE EXAMPLES' LOOK (decisions 87, Robin 2026-10-22, his settings from the examples style lab,
   "This would be the default"; the bullets' indent 1.1em, his second paste). The default, with
   JavaScript off too: no "Example" heading; each example list a quote block with the left bar
   the subsenses had until then (the deck's `.ordbok-sub` bar: #e0d8d9, at night #656161); a real
   subsense (`div.ordbok-sub`, not a compound list's `.ordpar-comp`) a bullet point 1.1em in, the
   bullet in the sense numerals' colour (the deck's `.ordbok-senses>li::marker`: the scheme's
   accent by day, #b9b6b6 at night); a compound list a plain line at the end of its sense — no
   bar, no bullet, as ordbokene's. Articles and minis alike (a mini is cut from the article's
   markup), and a set phrase's example lists too. A numbered subsense (`ol.ordbok-subsenses`)
   keeps its number. The bullet is a list item, and every list item advances the enclosing
   `ol`'s implicit `list-item` counter, so each bulleted subsense took a sense number (*møte* II
   numbered 1, 3, …: decisions 98, a fault): `counter-increment: list-item 0` names the counter
   and so stops the automatic step (`none` does not — it is the computed value already), the
   bullet kept */
.ordbok-ex-list{margin:.3em 0 .2em 1em;padding-left:.6em;border-left:2px solid #e0d8d9}
.nightMode .ordbok-ex-list{border-left-color:#656161}
.ordbok-sub:not(.ordpar-comp){display:list-item;list-style:disc outside;border-left:0;
  padding-left:0;margin-left:1.1em;counter-increment:list-item 0}
.ordbok-sub:not(.ordpar-comp)::marker{color:var(--ordpar-maroon,@DAY@)}
.nightMode .ordbok-sub:not(.ordpar-comp)::marker{color:#b9b6b6}
.ordbok-sub.ordpar-comp{border-left:0;padding-left:0;margin-left:0}
/* THE LAYOUT CLOSER TO ORDBOKENE.NO (decisions 87: an optional style
   closer to ordbokene.no): the setting `layout` = ordbokene (`ordpar-layout-ordbokene`;
   the default `ordpar` is the look above). An "Example" heading before a sense's OWN examples —
   above its subsenses; none on a subsense, none on a set phrase, singular whatever the count, as
   ordbokene's (the examples lab report § Ordbokene's header) — in the accent, semibold, the body's
   size; the heading and those examples flush with the sense's text, no bar; a subsense's
   examples under its bullet's text, no heading, no bar; every other example list without its bar.
   The heading is a real element (`.ordpar-exhead`: an `h4` in an article, a `div` in a mini) with
   its words from the interface strings, inserted by the page script only under this setting
   (`PAGE_JS` `exheads`; in a mini by the mini script); hidden again if the setting goes back */
.ordpar-exhead{display:none}
html.ordpar-layout-ordbokene .ordpar-exhead{display:block;margin:.4em 0 .1em;font-size:1em;
  font-weight:600;font-style:normal;line-height:1.5;letter-spacing:normal;
  color:var(--ordpar-accent,var(--ordpar-maroon,@DAY@))}
html.ordpar-layout-ordbokene .ordbok-ex-list{border-left:0;padding-left:0}
html.ordpar-layout-ordbokene .ordbok-sec>.ordbok-senses>li>.ordbok-ex-list,
html.ordpar-layout-ordbokene .ordbok-sec>div[id]>.ordbok-ex-list,
html.ordpar-layout-ordbokene .ordpar-mbody>.ordbok-senses>li>.ordbok-ex-list,
html.ordpar-layout-ordbokene .ordpar-msense>.ordbok-ex-list,
html.ordpar-layout-ordbokene .ordbok-sub>.ordbok-ex-list{margin-left:0}
/* SUBSENSES IN ENGLISH ONLY (decisions 90, Robin 2026-10-22): the setting `subsenses` = defs (the
   default: as the definitions) | en (`ordpar-subsen-en`). Under `en`, where both lines would show
   (`defs = both`; in a mini, unless it shows English alone or `defs` is `no`), a real subsense's
   pair (`div.ordbok-sub`, not a compound list) shows its English line alone, in the main style,
   its partner words the links (the line that leads) — whichever line `emph` emphasizes. Under
   `defs = en` nothing changes; under `defs = no` it keeps its reveal (Robin's pick). A formula
   line keeps its own setting (81), which wins on it; a set phrase's numbered senses
   (`ol.ordbok-subsenses`) are not subsenses here and follow the definitions; a `div.ordbok-sub`
   under a set phrase follows this setting */
html.ordpar-subsen-en:not(.ordpar-defs-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.ordpar-pair:not(.ordpar-fml)>span[lang=nb],
html.ordpar-subsen-en:not(.ordpar-mini-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.mini-pair:not(.ordpar-fml)>span[lang=nb]{display:none}
html.ordpar-subsen-en:not(.ordpar-defs-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.ordpar-pair:not(.ordpar-fml)>span[lang=en],
html.ordpar-subsen-en:not(.ordpar-mini-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.mini-pair:not(.ordpar-fml)>span[lang=en]{
  color:inherit;font-size:1em;margin-top:0}
html.ordpar-subsen-en:not(.ordpar-defs-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.ordpar-pair:not(.ordpar-fml)>span[lang=en] .ordpar-xen>.ordbok-xword:where(:not(.ordbok-xmini *)),
html.ordpar-subsen-en:not(.ordpar-mini-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.mini-pair:not(.ordpar-fml)>span[lang=en] .ordbok-xword{
  text-decoration-line:underline;pointer-events:auto;cursor:pointer}
@media (hover:hover){
  html.ordpar-subsen-en:not(.ordpar-defs-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.ordpar-pair:not(.ordpar-fml)>span[lang=en] .ordpar-xen:hover>.ordbok-xpeek:where(:not(.ordbok-xmini *)),
  html.ordpar-subsen-en:not(.ordpar-mini-en):not(.ordpar-defs-no) .ordbok-sub:not(.ordpar-comp)>.mini-pair:not(.ordpar-fml)>span[lang=en] .ordbok-xref:hover>.ordbok-xpeek{display:block}
}
/* THE SOUND ICON (site decisions 159, Robin's pick from the style lab, 2026-11-02): a
   <button class="ordpar-play"> after each voiced text with a clip — the headword's main form (beside
   the word), a set phrase's term (inside it, at its end: the term is a block), each definition line,
   each example, each form of a voiced table — drawn by `audio.js` from the build's marks. The
   speaker with two waves, 1.00 rem everywhere; the muted grey faded 50 % toward the card, day
   #bab8b8, night #6f6b6c; on hover the text colour (darker by day, lighter at night); while its clip
   plays (`ordpar-playing`) the accent colour; an unseen tap area of 24 px. The night colour through
   `:where`, so it keeps the plain rule's weight and never outweighs hover and playing (the lab's
   fault, fixed there). Not selectable: a copied line never carries its hidden "Play" */
.ordpar-play{display:inline-flex;align-items:center;justify-content:center;position:relative;
  vertical-align:-.12em;margin:0 0 0 .3em;padding:0;border:0;border-radius:3px;background:none;
  font:inherit;line-height:1;color:#bab8b8;cursor:pointer;-webkit-tap-highlight-color:transparent;
  -webkit-user-select:none;user-select:none}
:where(html.nightMode) .ordpar-play{color:#6f6b6c}
.ordpar-play svg{display:block;width:1rem;height:1rem}
.ordpar-play:focus-visible{outline:2px solid var(--ordpar-focus);outline-offset:1px}
.ordpar-play::before{content:"";position:absolute;top:min(0px,calc(50% - 12px));bottom:min(0px,calc(50% - 12px));
  left:min(0px,calc(50% - 12px));right:min(0px,calc(50% - 12px))}
/* in a table, inside the cell's own padding: past the last column it would widen the table's strip */
.ordpar-infl .ordpar-play::before{top:-.3em;bottom:-.3em;left:-.25em;right:-.5em}
/* a narrow table's form: its last word and its icon never part (`audio.js` `bind`; the wide
   table's unbroken `ordpar-form` span holds them there) */
.ordpar-play-unit{white-space:nowrap}
@media (hover:hover){.ordpar-play:hover{color:var(--ordpar-text)}}
.ordpar-play.ordpar-playing{color:var(--ordpar-accent)}
/* a clip that could not play (offline, a failed names file, an error): faded for 1.5 s */
.ordpar-play-failed{opacity:.35}
/* THE CEFR LEVEL BOX (site decisions 187, the style lab's "Quiet box"):
   `<span class="ordpar-level">` (`levels.box_html`), the last thing in the headword's `h1` (after the
   last spelling's sound icon) and in each embedded set phrase's term (after its icon). A thin
   outline in the muted grey of the homograph numeral and the word-class line, the level as text,
   0.75 rem, weight 600; the lab's values. Shown only while the setting `levels` is on
   (`ordpar-levels-on` on <html>, from the head script before the first paint); with it off the box
   is not drawn and not read. Not selectable: a copied headword never carries it */
.ordpar-level{display:none;white-space:nowrap;line-height:1;font-style:normal;font-weight:600;
  font-variant:normal;font-size:.75rem;letter-spacing:.03em;padding:.2em .38em;
  border:1px solid currentColor;border-radius:3px;margin-left:.55em;vertical-align:.32em;
  color:var(--ordpar-muted,#757070);-webkit-user-select:none;user-select:none}
.nightMode .ordpar-level{color:var(--ordpar-muted,#b9b6b6)}
html.ordpar-levels-on .ordpar-level{display:inline-block}
/* on a set phrase's line, of body size, it sits lower than beside the headword */
.ordbok-expr-term .ordpar-level{vertical-align:.08em}
/* THE SET PHRASES BY CEFR LEVEL (site decisions 188): while the boxes are on and `phraseorder` is
   level (`ordpar-levels-on` and `ordpar-phraseorder-level` on <html>, both from the head script
   before the first paint), the set-phrase section (`ordpar-exprs`, written where any block has a
   level) and its untranslated group are flex columns, and each block (`data-level`, `article.py`
   `_expr_html`) takes its place by `order`: A1 to C 1 to 5, a block with no level 6, the
   untranslated group 7, so a level keeps the page's alphabetical order and the translated phrases
   stay first. Only a section's own blocks and its group's (child combinators): a small article
   opened inside a block keeps its own spacing and order. The order is drawn from the first paint,
   so nothing moves on screen; the page script (`ordparDefs` → `phord`) then puts the page's own
   blocks in the same order, so screen readers and the Tab key follow what is drawn. `:where`
   keeps these rules weaker than the sheet's hiding rules (`ordpar-defs-en` hides the untranslated
   group). In a flex column margins no longer collapse, so the gaps are rebuilt as the block layout draws them: .6em between blocks
   (`row-gap`), none from the heading's or a block's own margins; each block's last trailing margin
   (at most .4em) cancelled by an empty last box whose .6em and -.6em collapse with it to 0; .81em
   before the untranslated heading, as its own .9em margin at .9em type gives (.6 + .21), none where
   Norwegian only hides that heading */
:where(html.ordpar-levels-on.ordpar-phraseorder-level) .ordbok-sec.ordpar-exprs,:where(html.ordpar-levels-on.ordpar-phraseorder-level) .ordpar-exprs>.ordpar-untr{display:flex;flex-direction:column;row-gap:.6em}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) .ordpar-exprs.ordbok-sec>h3{margin-bottom:0}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr{margin:0;order:6}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr::after{content:"";display:block;margin:.6em 0 -.6em}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr[data-level="A1"]{order:1}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr[data-level="A2"]{order:2}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr[data-level="B1"]{order:3}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr[data-level="B2"]{order:4}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) :is(.ordpar-exprs,.ordpar-exprs>.ordpar-untr)>.ordbok-expr[data-level="C"]{order:5}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) .ordpar-exprs>.ordpar-untr{margin-top:.21em;order:7}
:where(html.ordpar-levels-on.ordpar-phraseorder-level) .ordpar-exprs>.ordpar-untr>.ordpar-untr-head{margin:0}
:where(html.ordpar-levels-on.ordpar-phraseorder-level.ordpar-nbo) .ordpar-exprs>.ordpar-untr{margin-top:0}
'''

#: The article page's own rules (decisions 63: the header, the footer and the card are the
#: shell's — `ordpar/site/shell.css`, which the page links before this sheet): the "Article view"
#: line, the untranslated note, the inflection table's room on the page, and the About page.
#: Written once to `out/site/page.css`.
PAGE_CSS = r'''
.ordpar-viewline{display:flex;flex-wrap:wrap;align-items:baseline;gap:.25rem 1.2rem;margin:0 0 .8rem}
.ordpar-viewline .ordpar-dict-title{margin:0;font-size:.8rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.09em}
.ordpar-viewline a{text-decoration:none}
.ordpar-viewline a:hover{text-decoration:underline}
.ordpar-entry .ordpar-note{margin:0 0 1em;font-style:italic}
.ordpar-about h1{font-size:1.6rem;margin:.3em 0 .5em;color:var(--ordpar-accent)}
.ordpar-about h2{font-size:1.05rem;margin:1.4em 0 .3em}
.ordpar-about p{margin:.5em 0;line-height:1.5}
/* the privacy page's index of its sections (decisions 104, Robin 2026-10-23): a short list of
   links under its lead, its label in the muted grey as a settings title */
.ordpar-toc{margin:.8em 0 1.2em;padding:.5em .9em;border-left:2px solid var(--ordpar-border,#e0d8d9)}
.ordpar-toc-title{margin:0 0 .2em;font-size:.9rem;font-weight:600;color:var(--ordpar-muted,#757070)}
.ordpar-toc ul{margin:0;padding-left:1.1em;line-height:1.6}
/* the page "More ways to use Ordpar" (site decisions 142, from the lab's more-page.css): numbered
   steps with the numbers in the accent colour, and a line of code under a step (the Definer URL
   and CSS) that one click selects whole; since site decisions 146 a Copy button beside each line
   (`shell.js` `wireCodeLines`, `has-copy` once it is there), the page's quiet button */
.ordpar-about ol{margin:.5em 0 .8em;padding-left:1.6em;line-height:1.5}
.ordpar-about ol>li{margin:.3em 0;padding-left:.2em}
.ordpar-about ol>li::marker{font-weight:700;color:var(--ordpar-accent)}
.ordpar-code{margin:.35em 0 .1em;max-width:100%}
.ordpar-code.has-copy{display:flex;align-items:flex-start;gap:.5em}
.ordpar-code.has-copy code{flex:1 1 auto;min-width:0}
.ordpar-code-copy{flex:none}
.ordpar-code code{display:block;padding:.35em .6em;white-space:pre-wrap;overflow-wrap:anywhere;
  font:.88rem/1.5 ui-monospace,Consolas,"Cascadia Mono",Menlo,monospace;color:var(--ordpar-text);
  background:var(--ordpar-pill);border:1px solid var(--ordpar-border);border-radius:var(--ordpar-radius);
  -webkit-user-select:all;user-select:all}
.ordpar-about h2[id]{scroll-margin-top:1rem}
/* the credit under a reader's idea on /thanks/ (site decisions 183; Robin's pick in the credit
   lab, 2026-11-11): a line of its own, italic, the body colour; the en dash drawn here, so the
   stored words stay "Suggested by …" */
.ordpar-thanks-credit{display:block;font-style:italic}
.ordpar-thanks-credit::before{content:"\2013\00a0"}
/* half a line between the ideas (decisions 183); the fixes' one-line
   rows keep their spacing */
.ordpar-thanks-ideas>li+li{margin-top:.5em}
'''

CSS_HREF = "/site/article.css"
PAGE_CSS_HREF = "/site/page.css"
#: The page script (`PAGE_JS`), written once to `out/site/article.js` and linked, deferred:
#: inlined, its 2.5 KB would cost every one of the 94k pages ~1 KB gzipped (decisions 54).
JS_HREF = "/site/article.js"
SITE_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")


#: The inflection table's script, and where the build writes the site's shape table into it
INFLECTION_JS_HREF = "/site/inflection.js"
SHAPES_SLOT = "var SHAPES = {};"
#: "Suggest a correction" (site decisions 166; its place in the bundles: below), and the line of it
#: the build writes the reports' switch into (`report_js`, `chrome.REPORT_RECEIVER`)
REPORT_JS_HREF = "/site/report.js"
REPORT_SLOT = "var REPORT_RECEIVER = '';"
#: The readers' survey (site decisions 173): its page's own script, linked by `/survey/` alone, and
#: the line the build writes the survey's receiver into (`survey_js`, `chrome.survey_receiver()`)
SURVEY_JS_HREF = "/site/survey.js"
SURVEY_SLOT = "var SURVEY_RECEIVER = '';"
#: ... and the line of `shell.js` the build writes the survey's address into, for the footer's
#: "Tell us what you think →" (`survey_link_js`; empty while the survey is off: no link)
SURVEY_LINK_SLOT = "var SURVEY_HREF = '';"

#: The mini script (decisions 80): `ordpar/site/mini.js`, verbatim — a cross-reference's mini cut
#: from the target's own page. Part of `/site/ordpar.js` after `article.js`, whose `place` it
#: uses; the search page and the 404 shell link it after their `article.js`.
MINI_JS_HREF = "/site/mini.js"


@functools.lru_cache(maxsize=None)
def source(url):
    """A `/site/` file's text before its comments are stripped: `article.css`, `page.css`,
    `article.js` and `theme.js` are generated here; `inflection.js` is `ordpar/site/`'s with the
    site's shape table written in (`article.SHAPES`, `set_shapes`); the rest are `ordpar/site/`
    verbatim."""
    if url == CSS_HREF:
        return article_css()
    if url == PAGE_CSS_HREF:
        return PAGE_CSS
    if url == JS_HREF:
        return PAGE_JS
    if url == THEME_JS_HREF:
        return THEME_JS + "\n"
    with open(os.path.join(SITE_SRC, url[len("/site/"):]), encoding="utf-8") as f:
        text = f.read()
    if url == INFLECTION_JS_HREF:
        from . import article
        if text.count(SHAPES_SLOT) != 1:
            raise ValueError("inflection.js: %r must occur exactly once" % SHAPES_SLOT)
        text = text.replace(SHAPES_SLOT, "var SHAPES = %s;" % slim.shapes_js(article.SHAPES))
    if url == REPORT_JS_HREF:
        text = report_js(text)
    if url == SURVEY_JS_HREF:
        text = survey_js(text)
    if url == "/site/shell.js":            # SHELL_JS_HREF, set further down
        text = survey_link_js(text)
    return text


def report_js(text):
    """`report.js` with the reports' switch written in (site decisions 166, `chrome.REPORT_RECEIVER`,
    the one place the address is set): its committed line `var REPORT_RECEIVER = '';` (REPORT_SLOT,
    exactly once, so an address typed into report.js itself fails the build rather than going
    unseen) becomes the address, or stays empty while reports are off."""
    if text.count(REPORT_SLOT) != 1:
        raise ValueError("report.js: %r must occur exactly once — the address is set in "
                         "sitegen/chrome.py REPORT_RECEIVER, never in report.js" % REPORT_SLOT)
    addr = chrome.check_report_receiver(chrome.REPORT_RECEIVER)
    return text.replace(REPORT_SLOT, "var REPORT_RECEIVER = %s;" % json.dumps(addr)) if addr else text


def _slot(text, slot, value, name, where):
    if text.count(slot) != 1:
        raise ValueError("%s: %r must occur exactly once — the value is set in sitegen/chrome.py "
                         "%s, never in %s" % (name, slot, where, name))
    return text.replace(slot, slot.replace("''", json.dumps(value))) if value else text


def survey_js(text):
    """`survey.js` with the survey's receiver written in (site decisions 173,
    `chrome.survey_receiver()`): its committed line `var SURVEY_RECEIVER = '';` (SURVEY_SLOT,
    exactly once) becomes the address, or stays empty while the survey is off."""
    return _slot(text, SURVEY_SLOT, chrome.survey_receiver(), "survey.js", "SURVEY / REPORT_RECEIVER")


def survey_link_js(text):
    """`shell.js` with the survey's address written in (site decisions 173): its committed line
    `var SURVEY_HREF = '';` (SURVEY_LINK_SLOT, exactly once) becomes `chrome.SURVEY_HREF` while the
    survey is on (`chrome.survey_receiver()` not empty), so the footer links the survey exactly when
    the build writes the page; empty, no link."""
    return _slot(text, SURVEY_LINK_SLOT, chrome.SURVEY_HREF if chrome.survey_receiver() else "",
                 "shell.js", "SURVEY_HREF / SURVEY")


def set_survey(on):
    """The survey's switch for this build (`chrome.SURVEY`; a test's or a look build's), every cached
    script dropped, since `shell.js` is part of both bundles and of their `?v=`."""
    chrome.SURVEY = bool(on)
    for f in (source, shipped, asset):
        f.cache_clear()


def set_report_receiver(address):
    """The reports' switch for this build (`build_site.py`, before the first page; site decisions
    166): `chrome.REPORT_RECEIVER` set and every cached script dropped, since `report.js` is part
    of both bundles and of their `?v=`."""
    chrome.REPORT_RECEIVER = chrome.check_report_receiver(address)
    for f in (source, shipped, asset):
        f.cache_clear()


@functools.lru_cache(maxsize=None)
def shipped(url):
    """A `/site/` script or stylesheet as the site serves it: without comments (decisions 61,
    `slim.strip_asset`), and for the combined files (`COMBINED`) their parts joined in order."""
    if url in COMBINED:
        parts = [shipped(p) if p.startswith("/site/") else p for p in COMBINED[url]]
        return slim.join_js(parts) if url.endswith(".js") else slim.join_css(parts)
    return slim.strip_asset(url, source(url)).lstrip("\n")


def set_shapes(shapes):
    """The site's paradigm shapes, before the first page is rendered (`build_site.py`): they are
    part of `inflection.js`, so of its `?v=` and of `/site/ordpar.js`'s."""
    from . import article
    article.SHAPES.clear()
    article.SHAPES.update(shapes)
    for f in (source, shipped, asset):
        f.cache_clear()


@functools.lru_cache(maxsize=None)
def asset(url):
    """`/site/<file>?v=<content hash>` — every page links its scripts and stylesheets through
    this, so a browser holding last build's copy fetches the new one the moment the page
    changes (2026-09-24: a cached `inflection.js` left the new page's Inflection toggle hidden).
    The hash is of the file as the build ships it (`shipped`; any other file under
    `ordpar/site/`, verbatim)."""
    if url.endswith((".js", ".css")):
        blob = shipped(url).encode("utf-8")
    else:
        with open(os.path.join(SITE_SRC, url[len("/site/"):]), "rb") as f:
            blob = f.read()
    return "%s?v=%s" % (url, hashlib.sha1(blob).hexdigest()[:10])


#: The deck's maroon and its night tint, as the deck's sheets write them, and the colour
#: variables they become on the site (decisions 63: every use of the accent goes through the
#: colour scheme, `colours.py`; `ordbok_gen.py` and `mini.py` are untouched — the rewrite is
#: the site's, at build time; each fallback — never used, since every page links the sheet that
#: defines the variables — is the default scheme's, so `#560027` appears only under its own
#: named scheme, ordbokene's, Robin 2026-10-20). `#7a5566` is the
#: night underline of a cross-reference, which ordbokene's scheme draws in its link colour.
_D = colours.default()
_D_RGB = "%d,%d,%d" % tuple(int(_D["day"][i:i + 2], 16) for i in (1, 3, 5))
DECK_ACCENT = (
    ("#560027", "var(--ordpar-maroon,%s)" % _D["day"]),
    ("rgba(86,0,39,", "rgba(var(--ordpar-maroon-rgb,%s)," % _D_RGB),
    ("#e3b7c9", "var(--ordpar-tint,#e3b7c9)"),
    ("rgba(227,183,201,", "rgba(var(--ordpar-tint-rgb,227,183,201),"),
    ("#7a5566", "var(--ordpar-night-line,#7a5566)"),
)


#: The examples limit's numbers (decisions 112): `shell.js` SETTINGS `exlimit`, All then 1 to 10.
EX_LIMITS = range(1, 11)
#: One rule per limit: a list's items past the first n hidden, the "Show N more" line excepted.
EXLIMIT_CSS = "\n".join(
    "html.ordpar-exlimit-%d .ordbok-ex-list:where(:not(.ordbok-xmini *)):not(.ordpar-exopen)>"
    "li:nth-child(n+%d):not(.ordpar-exmore){display:none}" % (n, n + 1) for n in EX_LIMITS)

#: `SITE_CSS` with its accent fallbacks filled in (the default scheme's day accent), and the
#: examples limit's rules
SITE_CSS = (SITE_CSS.replace("@DAY@", _D["day"]).replace("@DAY_RGB@", _D_RGB)
            .replace("@EXLIMIT@", EXLIMIT_CSS))


#: The deck's rules drawn in its muted grey that the site draws in `--ordpar-muted` instead (light
#: and night alike; `shell.css` sets the variable): the homograph numeral (decisions 105:
#: our faded text colour) and the "Show translation" / "Show English" cue
#: (decisions 111: faded grey, to make it less prominent). Each is an exact text of
#: `ordbok_gen._CARD_CSS`; a rule changed there and not here fails the build (`deck_css_site`)
#: rather than leaving the site a written-out grey. Only these rules: the deck's other uses of
#: #757070 stay as written.
DECK_MUTED = (
    (".ordbok-homograph{font-weight:600;color:#757070;",
     ".ordbok-homograph{font-weight:600;color:var(--ordpar-muted,#757070);"),
    (".nightMode .ordbok-homograph{color:#b9b6b6}",
     ".nightMode .ordbok-homograph{color:var(--ordpar-muted,#b9b6b6)}"),
    (".ordbok-cue{display:inline-block;font-size:.8em;color:#757070;",
     ".ordbok-cue{display:inline-block;font-size:.8em;color:var(--ordpar-muted,#757070);"),
    (".nightMode .ordbok-cue{color:#b9b6b6;",
     ".nightMode .ordbok-cue{color:var(--ordpar-muted,#b9b6b6);"),
)


def deck_css_site():
    """`DECK_CSS` with the accent through the colour variables (`DECK_ACCENT`), and the numeral's
    and the cue's grey through `--ordpar-muted` (`DECK_MUTED`)."""
    css = DECK_CSS
    for old, new in DECK_ACCENT:
        css = css.replace(old, new)
    for old, new in DECK_MUTED:
        if css.count(old) != 1:
            raise ValueError("deck_css_site: %r is not in the deck's sheet once (ordbok_gen._CARD_CSS "
                             "changed? update DECK_MUTED)" % old)
        css = css.replace(old, new)
    return css


def article_css():
    """The article fragment's sheet, for `out/site/article.css`: the deck's sheets (the accent
    through the colour variables), the site's fragment rules, and the colour schemes
    (`colours.css()`, decisions 63 — every page links this sheet, the shell pages too). The
    search page links it for its results (site decisions 59)."""
    return deck_css_site() + SITE_CSS + colours.css()


#: The page's scripts, deferred in this order: `inflection.js`, `/site/personal.js` (the history
#: and favourites, site decisions 60 — `ordpar/site/personal.js`, copied with the site folder),
#: and `/site/article.js` (`JS_HREF`, deferred, after
#: `inflection.js`), then `/site/mini.js` (`MINI_JS_HREF`: the cross-reference's mini, cut from
#: the target's own page — decisions 80; it reads `xref` = mini | page, default mini — decisions
#: 34 — itself, and uses this script's `place`, exported as `window.ordparPlace`). This one
#: carries the inflection setting (`infl` = button | open, default button —
#: ordbokene's "Always show inflection tables", Robin 2026-09-24), the two footer controls
#: (21e), the heart (decisions 60, through `personal.js` `mountPage`, when that script loaded;
#: the visit is not recorded — the history is a list of searches, brief 60b), and the definitions settings' two moving parts
#: (decisions 54):
#:
#: * `defs = en`: nothing to move since decisions 80 — a partner word is a link already
#:   (`face.SiteFace._partner`), which the sheet makes a plain word unless the English stands
#:   alone; until then this script moved the Norwegian control's checkbox and mini onto it.
#: * `defs = no`: a "Show English" cue (`strings.show_english`) is inserted before each
#:   article line pair's English line (never in a mini, which has no reveal); a click on it
#:   opens the pair (`.ordpar-open`), a click on the opened English line closes it again.
#: * `examples = no` (decisions 111, `ordpar-examples-no`): the same cue, `.ordpar-excue` besides,
#:   before each example's English line (`excues`; an example with no English gets none) — in
#:   the article, a search result and, through `window.ordparExCues(root)`, a mini the mini script
#:   cuts after the page has loaded; a click opens the example's `li` (`.ordpar-open`), a click on
#:   its opened English closes it again. Inserted only once the setting is on, as `defs = no`'s.
#: * `exlimit` = 1 … 10 (decisions 112, `ordpar-exlimit-<n>`; the sheet cuts each list to its first n
#:   items): under every example list the sheet cut, outside a mini, a "Show N more examples" line
#:   (`strings.examples_more`, `examples_more_one` for 1; `exmore`, a `li.ordpar-exmore` holding a
#:   button in the cue's look, `.ordpar-exbtn`); a click opens that list in place (`.ordpar-exopen`)
#:   and the line goes, the focus moving to the first example it showed when the line had it. Kept
#:   in step on every run: a line is added, renumbered or removed as the limit changes;
#:   `exmore = off` (`ordpar-exmore-off`) hides the lines by the sheet.
#: * `layout = ordbokene` (decisions 87, `ordpar-layout-ordbokene`): an "Example" heading
#:   (`strings.example_heading`, `.ordpar-exhead`) before each sense's own example list (`exheads`,
#:   the lists `XL` names: a top sense's, a solo sense's, and a mini's sense) — an `h4` in an
#:   article (one level under its section's `h3`, `aria-level` too in a search result), a `div` in
#:   a mini, whose header is no heading either. Inserted once, only while the setting is on (the
#:   sheet hides it again when it goes off), so no page ships it; `window.ordparExHeads(root)` is
#:   the mini script's, for a mini cut after the page has loaded.
#: * `exeye = on` (decisions 131, `ordpar-exeye-on`; off by default): the eye (`eyes`), a
#:   `<button>` named `strings.exeye_button` with `aria-pressed`, in a `span.ordpar-exeye` put
#:   first in the `.ordbok-head` of every `.ordpar-article` that has an example with English — an
#:   article page, a word page's or a search's article shown whole, an article opened in a list or
#:   favourites row; never in a mini or a row's button. Pressed means the article's examples'
#:   English hidden; a press (`eye`) switches that article only: under `examples = both` it adds
#:   `ordpar-exhide` to the article and its "Show English" cues (`excues(a, 1)`), under `examples =
#:   no` it opens every example (`.ordpar-open`, the article marked `ordpar-exshown`); either way
#:   any example opened one at a time closes first. A change of `examples`, or the eye turned
#:   off, puts every article back to the Examples setting; with it off nothing is inserted.
#: * `exeyewhat = all` (decisions 186, `ordpar-exeye-all`; `examples` the default, the eye above): the
#:   eye goes on every such article with an English line (`enOf`), none while definitions are in
#:   English only (`ordpar-defs-en`: a hidden definition would leave no Norwegian line above its
#:   cue); named `strings.exeye_all_hide`, pressed `strings.exeye_all_show`. A press (`blank`)
#:   blanks ITS article: the reader's hidden pairs and examples are marked open first (`defs = no`,
#:   `examples = no` set aside, their cues hidden by the sheet; never the etymology's), then every
#:   English line — the headword's gloss, each line of each definition (split at its `<br>`s into
#:   `span.ordpar-eyel`, its nodes moved), each example's, each set phrase's; never the etymology's,
#:   nor one in a peek, a mini or a row's button; one the reader's settings do not draw at all left
#:   alone — is hidden behind its own "Show English" cue (`.ordbok-cue[data-ordpar-eyecue]`), in its
#:   place; a line that is not an example is made up to its own height under the cue (`fitcue`: one
#:   row for a line of several), so a reveal moves nothing below a one-row line. A cue pressed shows
#:   its line (`ereveal`); a press on the shown line hides it again (`erehide`), taken before the
#:   pair's own close. The second press (`unblank`) gives the article back exactly, the reader's
#:   own openings and hidings included. Examples cut by the limit are blanked too, so "Show N more"
#:   opens them blanked. A change of a setting the article depends on (`eyesig`) gives every blanked
#:   article back first, so none is left half-blanked.
#:
#: It runs on load and again from `window.ordparDefs()`, which the shell calls when a
#: setting changes in place, and which the search page calls after it inserts an article
#: (site decisions 59) — so `ordparDefs` also applies `infl = open` to every Inflection toggle
#: it has not seen yet (once each: a toggle the reader closed stays closed), and tells the mini
#: script to look at the new links (`ordparMinis.scan`, for `minifetch = page`). It also puts each
#: set-phrase section's blocks in the page in the order the sheet draws them (`phord`, site
#: decisions 188): by level while the boxes and the level order are on, else as built, so screen
#: readers and the Tab key follow the drawn order and nothing moves on screen. With JavaScript
#: off the page is in the default and needs none of it: a cross-reference is a plain link, and
#: the buttons are not there.
#:
#: Since 2026-10-20 (the size report's items 5 and 10) it also MAKES the card's foot — Copy
#: link, its "Link copied" status and Share, in the empty `<footer class="ordpar-card-foot">`
#: the page ships, each still shown only where the browser has the API. Since decisions 106 the
#: foot may already hold the change notice (`corrections.notice_html`): the controls go before it,
#: and only a foot without controls of its own gets them. Since site decisions 166 (2026-11-05) a
#: third, "Report a mistake", after Share: `report.js` `mount` (`window.ordparReport`, before this
#: script in the bundle), which draws nothing while its own receiver address is empty. And the
#: address that opens its form on arrival (166, 2026-11-05, the deck's link on every card):
#: `/bm-en/<id>/#report` — once the row is in the page, `report.js` `fromAddress` opens the form as a
#: press would and takes the key off the address. The article page only: a word page or the search
#: may show several articles, and draws them later from a search (build-site.md § Report a mistake).
_PAGE_JS = """(function(){
var d=document,E=d.documentElement,C=E.classList,SHOW_EN=@SHOW_EN@,EXH=@EXH@,FOOT=@FOOT@,MORE=@MORE@,EYE=@EYE@,EYEA=@EYEA@,NB=@NB@;
function kid(n,c){for(var k=n.firstChild;k;k=k.nextSibling)
 if(k.classList&&k.classList.contains(c))return k;return null;}
/* site decisions 152: a label the page script draws, in both languages — `ordpar-l-en` and the
   Norwegian `ordpar-l-nb` (`data-nosnippet` from its making, 154), the sheet showing one (the
   labels setting); one copy where there is no Norwegian */
function lab(n,en,nb){n.textContent='';if(!nb||nb===en){n.textContent=en;return n;}
 var a=d.createElement('span');a.className='ordpar-l-en';a.textContent=en;
 var b=d.createElement('span');b.className='ordpar-l-nb';b.lang='nb';b.setAttribute('data-nosnippet','');b.textContent=nb;
 n.appendChild(a);n.appendChild(b);return n;}
function foot(){
 var f=d.querySelector('.ordpar-card-foot');
 if(!f||!E.hasAttribute('data-article-id')||f.querySelector('.ordpar-result-controls'))return;
 var p=d.createElement('p');p.className='ordpar-result-controls';
 function el(t,c,id,x,y){var n=d.createElement(t);n.className=c;n.id=id;n.hidden=true;lab(n,x,y);
  if(t==='button')n.type='button';p.appendChild(n);return n;}
 el('button','ordpar-result-btn','ordpar-copy',FOOT.copy);
 el('span','ordpar-result-copied','ordpar-copied',FOOT.done).setAttribute('role','status');
 el('button','ordpar-result-btn','ordpar-share',FOOT.share);
 var R=window.ordparReport,b=R&&R.mount?R.mount(p,E.getAttribute('data-article-id')):null;
 f.insertBefore(p,f.firstChild);
 if(b&&R.fromAddress)R.fromAddress(b);}
foot();
function cues(){
 if(!C.contains('ordpar-defs-no'))return;
 var ps=d.querySelectorAll('.ordpar-pair');
 for(var i=0;i<ps.length;i++){var p=ps[i];if(p._c)continue;p._c=1;
  var bt=d.createElement('button');bt.type='button';bt.className='ordbok-cue ordpar-encue';
  lab(bt,SHOW_EN,NB.showEn);p.insertBefore(bt,p.lastElementChild);}}
function excues(r,f){
 if(!f&&!C.contains('ordpar-examples-no'))return;
 var es=(r||d).querySelectorAll('.ordbok-ex-list>li>.ordpar-en');
 for(var i=0;i<es.length;i++){var e=es[i],li=e.parentNode;if(kid(li,'ordpar-excue')||f&&e.closest('.ordbok-xmini'))continue;
  var bt=d.createElement('button');bt.type='button';bt.className='ordbok-cue ordpar-encue ordpar-excue';
  lab(bt,SHOW_EN,NB.showEn);li.insertBefore(bt,e);}}
window.ordparExCues=excues;
/* decisions 131: the eye beside the headword (`exeye` = on, `ordpar-exeye-on`), on every article
   shown whole that has an example with English, never in a mini: pressed = the article's examples'
   English hidden. It starts from the Examples setting, which a change of either setting restores */
var EX0=null,EYEI='<svg class="ordpar-i-on" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '+
 'stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/>'+
 '<circle cx="12" cy="12" r="3"/></svg><svg class="ordpar-i-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" '+
 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/>'+
 '<circle cx="12" cy="12" r="3"/><path d="M3 3l18 18"/></svg>';
function exitems(a){var r=[],es=a.querySelectorAll('.ordbok-ex-list>li>.ordpar-en');
 for(var i=0;i<es.length;i++)if(!es[i].closest('.ordbok-xmini'))r.push(es[i].parentNode);return r;}
function exhidden(a){var c=a.classList;
 return c.contains('ordpar-exhide')||C.contains('ordpar-examples-no')&&!c.contains('ordpar-exshown');}
/* decisions 186: under `exeyewhat` = all (`ordpar-exeye-all`) the eye blanks every English line of
   ITS article but the etymology, each behind its own "Show English" cue; a second press gives the
   article back as it was. Never in a peek, a mini or a row's button */
var EN_SEL='.ordbok-head>.ordpar-gloss,.ordpar-pair>span.ordbok-def[lang="en"],.ordbok-ex-list>li>.ordpar-en,.ordbok-idiom-eng',
 EN_OFF='.ordbok-xpeek,.ordbok-xmini,template,.ordpar-row-button',EA0=null,SIG0=null;
function eyeall(){return C.contains('ordpar-exeye-all');}
function enOf(a){var r=[],xs=a.querySelectorAll(EN_SEL);
 for(var i=0;i<xs.length;i++)if(/\\S/.test(xs[i].textContent)&&!xs[i].closest(EN_OFF))r.push(xs[i]);return r;}
/* every English line its own element: a definition of several lines split at its <br>s (its nodes
   moved, never copied; the <br>s stay); a line the settings do not draw at all is left alone */
function enLines(a){var out=[],xs=enOf(a);
 for(var i=0;i<xs.length;i++){var x=xs[i];
  if(getComputedStyle(x).display==='none')continue;
  if(!x.classList.contains('ordbok-def')||!x.querySelector('br')){out.push(x);continue;}
  var ks=[].slice.call(x.childNodes),s=null;
  for(var k=0;k<ks.length;k++){if(ks[k].nodeName==='BR'){s=null;continue;}
   if(!s){s=d.createElement('span');s.className='ordpar-eyel';x.insertBefore(s,ks[k]);out.push(s);}
   s.appendChild(ks[k]);}
  x.setAttribute('data-ordpar-eyel','');}
 return out.filter(function(l){return /\\S/.test(l.textContent);});}
function ecue(l){var b=d.createElement('button');b.type='button';b.className='ordbok-cue';b.setAttribute('data-ordpar-eyecue','');
 lab(b,SHOW_EN,NB.showEn);b._l=l;return b;}
function ehide(l,a){var b=ecue(l);l.classList.add('ordpar-eyehid');l.parentNode.insertBefore(b,l);
 if(!l.closest('.ordbok-ex-list>li'))fitcue(b,l,a);return b;}
/* the cue made to take the hidden line's height: the article measured with the line and with the
   cue, the difference made up under the cue by an empty block, or by a negative margin where the
   cue is the taller; a line of several rows made up to one row; a line not laid out left as it is */
function fitcue(b,l,a){
 if(!a.getClientRects().length||!b.getClientRects().length)return;
 l.classList.remove('ordpar-eyehid');b.style.display='none';
 var cs=getComputedStyle(l),lh=parseFloat(cs.lineHeight)||parseFloat(cs.fontSize)*1.2;
 var rs=l.getClientRects(),tops=[],q,z;
 for(q=0;q<rs.length;q++){if(!rs[q].height)continue;
  for(z=0;z<tops.length&&Math.abs(tops[z]-rs[q].top)>=lh/2;z++){}
  if(z===tops.length)tops.push(rs[q].top);}
 var rows=Math.max(1,rs.length>1?tops.length:Math.round(l.getBoundingClientRect().height/lh)||1);
 var want=a.getBoundingClientRect().height-(rows-1)*lh;
 l.classList.add('ordpar-eyehid');b.style.display='';
 var f=null,h=0,m=0;
 for(var k=0;k<2;k++){var dh=want-a.getBoundingClientRect().height;
  if(Math.abs(dh)<=0.05)break;
  if(dh>0||h>0){
   if(!f){f=d.createElement('span');f.className='ordpar-eyefill';f.setAttribute('aria-hidden','true');
    b.parentNode.insertBefore(f,b.nextSibling);b._f=f;}
   var nh=Math.max(0,h+dh);if(nh===0&&dh<0)m+=dh+h;h=nh;f.style.height=h+'px';}
  else m+=dh;
  b.style.marginBottom=m?m+'px':'';}}
function ereveal(b){var l=b._l;if(!l||!b.parentNode)return;
 if(b._f&&b._f.parentNode)b._f.parentNode.removeChild(b._f);
 b.parentNode.removeChild(b);l.classList.remove('ordpar-eyehid');l.classList.add('ordpar-eyeshown');}
function erehide(l){var a=l.closest('.ordpar-blanked');if(!a)return;
 l.classList.remove('ordpar-eyeshown');var b=ehide(l,a);try{b.focus({preventScroll:true});}catch(e){}}
function off2(el,x,y){el.classList.remove(x,y);if(!el.classList.length)el.removeAttribute('class');}
function blank(a){a.classList.add('ordpar-blanked');
 var ps=a.querySelectorAll('.ordpar-pair,.ordbok-ex-list>li'),i;
 for(i=0;i<ps.length;i++)if(!ps[i].classList.contains('ordpar-open')&&!ps[i].closest('.ordbok-xmini,.ordbok-inline'))
  ps[i].classList.add('ordpar-open','ordpar-eyeopened');
 var ls=enLines(a);for(i=0;i<ls.length;i++)ehide(ls[i],a);
 var r=a.closest('.ordpar-row');if(r)r.classList.add('ordpar-row-blanked');}
function unblank(a){
 var x=a.querySelectorAll('[data-ordpar-eyecue],.ordpar-eyefill'),i;
 for(i=0;i<x.length;i++)x[i].parentNode.removeChild(x[i]);
 x=a.querySelectorAll('.ordpar-eyehid,.ordpar-eyeshown');
 for(i=0;i<x.length;i++)off2(x[i],'ordpar-eyehid','ordpar-eyeshown');
 x=a.querySelectorAll('[data-ordpar-eyel]');
 for(i=0;i<x.length;i++){var ss=x[i].querySelectorAll('.ordpar-eyel');
  for(var j=0;j<ss.length;j++){while(ss[j].firstChild)x[i].insertBefore(ss[j].firstChild,ss[j]);x[i].removeChild(ss[j]);}
  x[i].removeAttribute('data-ordpar-eyel');}
 x=a.querySelectorAll('.ordpar-eyeopened');
 for(i=0;i<x.length;i++)off2(x[i],'ordpar-open','ordpar-eyeopened');
 a.classList.remove('ordpar-blanked');
 var r=a.closest('.ordpar-row');if(r)r.classList.remove('ordpar-row-blanked');}
/* the settings a blanked article depends on: a change of any gives every blanked article back */
function eyesig(){var r=[];for(var i=0;i<C.length;i++)
 if(/^ordpar-(exeye|defs-|examples|nbo|formulas|ety|subsen|layout|exlimit|exmore|emph|labels)/.test(C[i]))r.push(C[i]);
 return r.sort().join(' ');}
function eyereset(){var s=eyesig();
 if(SIG0!==null&&s!==SIG0){var bs=d.querySelectorAll('.ordpar-blanked');for(var i=0;i<bs.length;i++)unblank(bs[i]);}
 SIG0=s;}
function elabel(b,a){var all=eyeall(),p=all?a.classList.contains('ordpar-blanked'):exhidden(a),
 w=all?(p?EYEA.show:EYEA.hide):EYE;
 b.setAttribute('aria-label',w);b.title=w;b.setAttribute('aria-pressed',p?'true':'false');}
/* site decisions 152 (Robin's pick (a)): NORWEGIAN ONLY'S ICON BESIDE THE HEADWORD, for a page whose
   header is hidden (the Definer pop-up, `/more/` step 7): on every article shown whole, never a small
   article or a row's button, hidden by the sheet (`.ordpar-nbhw`) unless the page's own CSS shows it
   (the extra rule in `/more/`'s line). A press switches the layer for this visit only (the pop-up):
   `ordparShell.visitSetting`, nothing saved, as every setting the address carries (146). None
   while the icon's setting is off (`ordpar-nbicon-off`), nor where the shell is not loaded (the deck) */
var NBI='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '+
 'stroke-linejoin="round"><path d="M4 5h11a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H9l-4 3.5V15H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/>'+
 '<path d="M17.5 9H20a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v3l-3.2-3H12" opacity=".55"/></svg>';
function nbhw(){
 var S=window.ordparShell,off=!S||!S.visitSetting||C.contains('ordpar-nbicon-off'),i;
 var as=d.querySelectorAll('.ordpar-article');
 for(i=0;i<as.length;i++){var a=as[i],h=kid(a,'ordbok-head');
  if(!h||a.closest('.ordbok-xmini,.ordpar-row-button'))continue;
  var w=kid(h,'ordpar-nbhw');
  if(off){if(w)h.removeChild(w);continue;}
  if(!w){w=d.createElement('span');w.className='ordpar-nbhw';var b=d.createElement('button');
   b.type='button';b.className='ordpar-nbhw-btn';b.innerHTML='<span aria-hidden="true">'+NBI+'</span>';
   w.appendChild(b);var e=kid(h,'ordpar-exeye');h.insertBefore(w,e?e.nextSibling:h.firstChild);}}
 if(S&&S.syncIcons)S.syncIcons();}
function eyes(){
 var on=C.contains('ordpar-exeye-on'),no=C.contains('ordpar-examples-no'),all=eyeall(),i;
 if(!on||EX0!==null&&EX0!==no||EA0!==null&&EA0!==all){var xs=d.querySelectorAll('.ordpar-exhide,.ordpar-exshown');
  for(i=0;i<xs.length;i++){var o=exitems(xs[i]);for(var j=0;j<o.length;j++)o[j].classList.remove('ordpar-open');
   xs[i].classList.remove('ordpar-exhide','ordpar-exshown');}}
 EX0=no;EA0=all;
 if(!on){var ws=d.querySelectorAll('.ordpar-exeye');for(i=0;i<ws.length;i++)ws[i].parentNode.removeChild(ws[i]);return;}
 var as=d.querySelectorAll('.ordpar-article');
 for(i=0;i<as.length;i++){var a=as[i],h=kid(a,'ordbok-head');
  if(!h||a.closest('.ordbok-xmini,.ordpar-row-button'))continue;
  var w=kid(h,'ordpar-exeye');
  if(all?C.contains('ordpar-defs-en')||!enOf(a).length:!exitems(a).length){if(w)h.removeChild(w);continue;}
  if(!w){w=d.createElement('span');w.className='ordpar-exeye';var b=d.createElement('button');
   b.type='button';b.className='ordpar-exeye-btn';b.setAttribute('aria-label',EYE);b.title=EYE;
   b.innerHTML='<span aria-hidden="true">'+EYEI+'</span>';w.appendChild(b);h.insertBefore(w,h.firstChild);}
  elabel(w.firstChild,a);}}
function eye(b){
 var a=b.closest('.ordpar-article');if(!a)return;
 if(eyeall()){if(a.classList.contains('ordpar-blanked'))unblank(a);else blank(a);elabel(b,a);return;}
 var hid=exhidden(a),no=C.contains('ordpar-examples-no'),li=exitems(a),i;
 for(i=0;i<li.length;i++)li[i].classList.remove('ordpar-open');
 a.classList.remove('ordpar-exhide','ordpar-exshown');
 if(hid&&no){a.classList.add('ordpar-exshown');for(i=0;i<li.length;i++)li[i].classList.add('ordpar-open');}
 else if(!hid&&!no){a.classList.add('ordpar-exhide');excues(a,1);}
 b.setAttribute('aria-pressed',exhidden(a)?'true':'false');}
var XL='.ordbok-sec>.ordbok-senses>li>ul.ordbok-ex-list,.ordbok-sec>div[id]>ul.ordbok-ex-list,'+
 '.ordpar-mbody>.ordbok-senses>li>ul.ordbok-ex-list,.ordpar-msense>ul.ordbok-ex-list';
function exheads(r){
 if(!C.contains('ordpar-layout-ordbokene'))return;
 var ls=(r||d).querySelectorAll(XL);
 for(var i=0;i<ls.length;i++){var u=ls[i],q=u.previousElementSibling;
  if(q&&q.classList.contains('ordpar-exhead'))continue;
  var m=u.closest('.ordbok-xmini'),h=d.createElement(m?'div':'h4');h.className='ordpar-exhead';
  lab(h,EXH,NB.exh);
  if(!m){var s=u.closest('.ordbok-sec'),t=s&&s.querySelector('h3[aria-level]');
   if(t)h.setAttribute('aria-level',(+t.getAttribute('aria-level')||3)+1);}
  u.parentNode.insertBefore(h,u);}}
window.ordparExHeads=exheads;
function exlim(){for(var i=1;i<11;i++)if(C.contains('ordpar-exlimit-'+i))return i;return 0;}
function exmore(r){
 var n=exlim(),ls=(r||d).querySelectorAll('ul.ordbok-ex-list');
 for(var i=0;i<ls.length;i++){var u=ls[i],b=null,k=0;if(u.closest('.ordbok-xmini'))continue;
  for(var c=u.firstElementChild;c;c=c.nextElementSibling){if(c.classList.contains('ordpar-exmore'))b=c;else k++;}
  var h=n&&!u.classList.contains('ordpar-exopen')?k-n:0;
  if(h<=0){if(b)u.removeChild(b);continue;}
  if(!b){b=d.createElement('li');b.className='ordpar-exmore';var bt=d.createElement('button');
   bt.type='button';bt.className='ordbok-cue ordpar-exbtn';b.appendChild(bt);u.appendChild(b);}
  lab(b.firstChild,(h===1?MORE.one:MORE.many).replace('{n}',h),(h===1?NB.moreOne:NB.more).replace('{n}',h));}}
window.ordparExMore=exmore;
function infl(){
 var o;try{o=(window.ordparRead?window.ordparRead('infl'):localStorage.getItem('infl'))==='open';}catch(e){}
 var ts=d.querySelectorAll('details.ordpar-infl-toggle');
 for(var i=0;i<ts.length;i++){if(ts[i]._i)continue;ts[i]._i=1;if(o)ts[i].open=true;}}
/* site decisions 188: THE SET PHRASES' PAGE ORDER FOLLOWS THE DRAWN ORDER. While <html> has both
   `ordpar-levels-on` and `ordpar-phraseorder-level` the sheet draws a set-phrase section's blocks
   by level (`order`, `SITE_CSS`); this puts the page's own blocks in that order too (A1, A2, B1,
   B2, C, no level last, a level in the order the page was built in), so screen readers and the Tab
   key follow what is drawn, and puts them back in the built order when either class goes. The
   sheet draws the same order before and after, so nothing moves on screen. Each block's place as
   built is recorded once (`_po`), so the way back never re-sorts text; a section's own blocks and
   its untranslated group's, each group apart (the translated phrases stay first); only the blocks
   out of place are moved, each with what it holds (an open small article, the eye's state, the
   examples shown), and the focus, if it was inside one, is given back without scrolling */
var LVO={A1:1,A2:2,B1:3,B2:4,C:5};
function phgrp(g,lv){var bs=[],c,i;
 for(c=g.firstElementChild;c;c=c.nextElementSibling)if(c.classList.contains('ordbok-expr'))bs.push(c);
 if(bs.length<2)return;
 if(bs[0]._po==null)for(i=0;i<bs.length;i++)bs[i]._po=i;
 var t=bs.slice().sort(function(a,b){
  return lv&&((LVO[a.getAttribute('data-level')]||6)-(LVO[b.getAttribute('data-level')]||6))||a._po-b._po;});
 var r=bs[0],f=d.activeElement,m=0;
 for(i=0;i<t.length;i++){
  if(t[i]===r){for(r=r.nextElementSibling;r&&!r.classList.contains('ordbok-expr');r=r.nextElementSibling){}continue;}
  if(f&&t[i].contains(f))m=1;g.insertBefore(t[i],r);}
 if(m&&f.isConnected&&d.activeElement!==f)try{f.focus({preventScroll:true});}catch(e){}}
function phord(){
 var lv=C.contains('ordpar-levels-on')&&C.contains('ordpar-phraseorder-level'),ss=d.querySelectorAll('.ordpar-exprs');
 for(var i=0;i<ss.length;i++){var s=ss[i];if(s.closest('.ordbok-xmini'))continue;
  phgrp(s,lv);var u=kid(s,'ordpar-untr');if(u)phgrp(u,lv);}}
window.ordparDefs=function(){
 eyereset();var M=window.ordparMinis;if(M&&M.scan)M.scan();var A=window.ordparAudio;if(A&&A.scan)A.scan();
 cues();excues();exheads();exmore();infl();eyes();nbhw();phord();};
try{window.ordparDefs();}catch(e){}
d.addEventListener('click',function(e){
 var t=e.target;if(!t||!t.closest)return;
 var y=t.closest('.ordpar-exeye-btn');if(y){eye(y);return;}
 var z=t.closest('.ordpar-nbhw-btn'),S=window.ordparShell;
 if(z&&S&&S.visitSetting){S.visitSetting('nbonly',S.getSetting('nbonly')==='on'?'off':'on');return;}
 var x=t.closest('.ordpar-exbtn');if(x){var li=x.parentNode,u=li.parentNode,f=d.activeElement===x;
  u.classList.add('ordpar-exopen');u.removeChild(li);var o=u.children[exlim()];
  if(f&&o){o.tabIndex=-1;o.focus({preventScroll:true});}return;}
 var q=t.closest('[data-ordpar-eyecue]');if(q){ereveal(q);return;}
 var c=t.closest('.ordpar-encue');if(c){c.parentNode.classList.add('ordpar-open');return;}
 if(t.closest('a,label,button'))return;
 var l=t.closest('.ordpar-eyeshown');if(l){erehide(l);return;}
 var o=t.closest('.ordpar-open>span[lang=en],.ordbok-ex-list>li.ordpar-open>.ordpar-en');
 if(o)o.parentNode.classList.remove('ordpar-open');});
var G=8;
/* measured parked a window-width to the LEFT, where an overhang scrolls nothing, never at its natural
   place (left cleared): a right overhang, even in one forced layout, widens a phone browser's layout
   viewport and clamps the scroll near the page's end (decisions 91). x = where the sheet's left:0
   puts the box; the same final left as before */
function place(m){
 var s=m.style;s.left='-100vw';
 var W=E.clientWidth,r=m.getBoundingClientRect();if(!r.width){s.left='';return;}
 var x=r.left-(parseFloat(getComputedStyle(m).left)||0);
 var dx=Math.min(0,W-G-(x+r.width));if(x+dx<G)dx=G-x;
 s.left=dx?dx+'px':'';}
window.ordparPlace=place;
d.addEventListener('mouseover',function(e){
 var t=e.target,x=t&&t.closest?t.closest('.ordbok-xref'):null;if(!x)return;
 var p=kid(x,'ordbok-xpeek');if(!p)return;
 p.style.removeProperty('--ordpar-peek-dx');place(p);
 var dx=parseFloat(p.style.left)||0;if(dx)p.style.setProperty('--ordpar-peek-dx',(-dx)+'px');});
window.addEventListener('resize',function(){
 var ms=d.querySelectorAll('.ordpar-mopen>.ordbok-xmini');
 for(var i=0;i<ms.length;i++)place(ms[i]);});
var c=d.getElementById('ordpar-copy');
if(c&&navigator.clipboard){c.hidden=false;c.addEventListener('click',function(){
 navigator.clipboard.writeText(location.href).then(function(){
  var s=d.getElementById('ordpar-copied');s.hidden=false;
  setTimeout(function(){s.hidden=true;},2500);});});}
var s=d.getElementById('ordpar-share');
if(s&&navigator.share){s.hidden=false;s.addEventListener('click',function(){
 navigator.share({title:d.title,url:location.href}).catch(function(){});});}
var P=window.ordparPersonal;if(P){try{P.mountPage(@FAV@);}catch(e){}}
if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(function(){});
/* decisions 94: with a copy in use (the manifest in use in Cache Storage; `caches.has` first, so
   no cache is ever created), load offline.js, whose update check then runs here too; without
   one, nothing is fetched. Not where offline.js is already loaded (the search page, 404) */
var K='ordpar-offline-1';
if(!window.ordparOffline&&window.caches)caches.has(K).then(function(h){
 return h&&caches.open(K).then(function(c){return c.match('/offline/__current.json');});
}).then(function(r){if(!r||window.ordparOffline)return;
 var o=d.createElement('script');o.src=@OFFLINE@;d.head.appendChild(o);}).catch(function(){});
})();"""


def page_js(strings):
    """`_PAGE_JS` with the interface's "Show English" and "Example" (decisions 87) filled in (the
    chrome strings the script itself draws; since decisions 112 the "Show N more examples" line's,
    `examples_more` and `examples_more_one`) and the heart's words (site decisions 60: `personal.js` `mountPage`
    draws the heart beside Copy link and Share at the card's foot, named "Favourite" in both
    states — brief 60b item 6; the header's "Favourites" link is the shared header's since
    decisions 63), and since 2026-10-20 the card foot's (`copy_link`, `copy_done`, `share`;
    English only, the interface's: site decisions 152, Robin 2026-11-03).
    `@OFFLINE@` is `offline.js` with its `?v=` (decisions 94: loaded only where a copy is in
    use)."""
    fav = {"label": strings["fav_label"], "saved": strings["fav_saved"]}
    foot = {"copy": strings["copy_link"], "done": strings["copy_done"], "share": strings["share"]}
    more = {"one": strings["examples_more_one"], "many": strings["examples_more"]}
    # decisions 186: the eye's words while it hides all of its article's English
    eye_all = {"hide": strings["exeye_all_hide"], "show": strings["exeye_all_show"]}
    # site decisions 152: the labels' Norwegian (`strings.NB`), drawn beside the English
    from .strings import NB
    # the card foot's words stay English (Robin, 2026-11-03: the interface language, at 1.0.0)
    nb = {"showEn": NB["show_english"], "exh": NB["example_heading"],
          "more": NB["examples_more"], "moreOne": NB["examples_more_one"]}
    return (_PAGE_JS
            .replace("@SHOW_EN@", json.dumps(strings["show_english"], ensure_ascii=False)
                     .replace("<", "\\u003c"))
            .replace("@EXH@", json.dumps(strings["example_heading"], ensure_ascii=False)
                     .replace("<", "\\u003c"))
            .replace("@FOOT@", json.dumps(foot, ensure_ascii=False).replace("<", "\\u003c"))
            .replace("@MORE@", json.dumps(more, ensure_ascii=False).replace("<", "\\u003c"))
            .replace("@FAV@", json.dumps(fav, ensure_ascii=False).replace("<", "\\u003c"))
            .replace("@EYE@", json.dumps(strings["exeye_button"], ensure_ascii=False)
                     .replace("<", "\\u003c"))
            .replace("@EYEA@", json.dumps(eye_all, ensure_ascii=False).replace("<", "\\u003c"))
            .replace("@NB@", json.dumps(nb, ensure_ascii=False).replace("<", "\\u003c"))
            .replace("@OFFLINE@", json.dumps(_offline_href())))


def _offline_href():
    """`asset("/site/offline.js")`, computed the same way (`shipped` of a file that is not
    combined) without `COMBINED`, which is set after `PAGE_JS`; `ordpar/tests/test_ordpar_offline94.py`
    holds the two equal."""
    url = "/site/offline.js"
    blob = slim.strip_asset(url, source(url)).lstrip("\n").encode("utf-8")
    return "%s?v=%s" % (url, hashlib.sha1(blob).hexdigest()[:10])


#: The script under the English strings: `out/site/article.js`. (A second interface language
#: would get its own file, `page_js(<its strings>)`, the one place the script differs.)
PAGE_JS = page_js(EN)

CANONICAL = "https://ordpar.no/bm-en/%d/"
LICENCE = chrome.LICENCE
ABOUT_HREF = chrome.ABOUT_HREF
#: The shell's sheet: the header, the footer, the card (decisions 63). `ordpar/site/shell.css`.
SHELL_CSS_HREF = "/site/shell.css"
#: The header's scripts on every article page (decisions 63: the same header as the search page,
#: so the same dropdown): `lookup.js` (the suggestions, Random word) and `shell.js` (the header's
#: enhancement, the settings' storage) — one cached request each, deferred.
LOOKUP_JS_HREF = "/site/lookup.js"
SHELL_JS_HREF = "/site/shell.js"
PERSONAL_JS_HREF = "/site/personal.js"
INFLECTION_CSS_HREF = "/site/inflection.css"
OFFLINE_JS_HREF = "/site/offline.js"
#: The install offer (site decisions 68): on every page, before `shell.js`, whose `addChrome`
#: asks it for the footer's phone hint and whose strings it uses
INSTALL_JS_HREF = "/site/install.js"
#: Loading ahead (site decisions 92): every page, in both bundles below
AHEAD_JS_HREF = "/site/ahead.js"
#: The sound icons (site decisions 159): every page, in both bundles below, before the page script
#: (`article.js`), whose `ordparDefs` calls its `scan`, and before `mini.js`, whose `fill` calls its
#: `mount` (`ordpar/site/audio.js`)
AUDIO_JS_HREF = "/site/audio.js"
#: The events for our receiver (site decisions 26, 62, 104): every page, in both bundles below,
#: before `install.js` and `shell.js`, which hand it their events; it sends nothing while its
#: receiver address is empty (`ordpar/site/events.js`, `ordpar/docs/receiver.md`)
EVENTS_JS_HREF = "/site/events.js"
#: "Report a mistake" at an article's foot (site decisions 166): every page, in both bundles below,
#: before `lookup.js` (whose `resultControls` calls it) and the page script (`article.js`, whose
#: `foot` calls it); it draws nothing while its own receiver address is empty (`ordpar/site/report.js`;
#: `REPORT_JS_HREF` itself is set above, beside `source`, which writes the switch into it)
#: The favourites and history pages' own script (site decisions 60), in the shell pages' bundle
#: since decisions 92, so a first opening of either page makes one trip, not two
PERSONAL_PAGE_JS_HREF = "/site/personal-page.js"

#: The ONE stylesheet and the ONE deferred script of every article page and the About page
#: (2026-10-20, the size report's item 4): the files they linked one by one until then,
#: concatenated in the same order. The separate files are still written and served (the
#: search page's results load `inflection.js` and `article.js` on their own).
CSS_ALL_HREF = "/site/ordpar.css"
JS_ALL_HREF = "/site/ordpar.js"
ARTICLE_CSS_PARTS = (CSS_HREF, INFLECTION_CSS_HREF, SHELL_CSS_HREF, PAGE_CSS_HREF)
ARTICLE_JS_PARTS = (INFLECTION_JS_HREF, PERSONAL_JS_HREF, REPORT_JS_HREF, LOOKUP_JS_HREF, AHEAD_JS_HREF,
                    AUDIO_JS_HREF, JS_HREF, MINI_JS_HREF, EVENTS_JS_HREF, INSTALL_JS_HREF,
                    SHELL_JS_HREF)
#: The shell pages' own pair (`build_index.copy_shell`): their sheets and their blocking
#: scripts, in the order they had (`/site/settings.js` and the search page's deferred
#: `inflection.js`, `article.js` and `mini.js` stay tags of their own); `ahead.js` and, last,
#: `personal-page.js` since decisions 92 (it does nothing on a page without
#: `data-ordpar-personal`)
SHELL_PAGES_CSS_HREF = "/site/shell-pages.css"
SHELL_PAGES_JS_HREF = "/site/shell-pages.js"
SHELL_CSS_PARTS = (CSS_HREF, INFLECTION_CSS_HREF, SHELL_CSS_HREF)
SHELL_JS_PARTS = (PERSONAL_JS_HREF, REPORT_JS_HREF, LOOKUP_JS_HREF, AHEAD_JS_HREF, AUDIO_JS_HREF, OFFLINE_JS_HREF,
                  EVENTS_JS_HREF, INSTALL_JS_HREF, SHELL_JS_HREF, PERSONAL_PAGE_JS_HREF)


def _strings_part():
    """`/site/ordpar.js`'s first part: the interface strings, the same table the page fetched
    from `/site/strings/en.json` until 2026-10-20 (the shell's strings with `strings.py`'s beside
    them, `chrome.strings`), so `shell.js` has the words of the chrome it inserts at once — as
    the shell pages have them inline (`ORDPAR_STRINGS`)."""
    return ("window.ORDPAR_STRINGS=window.ORDPAR_STRINGS||{};"
            "window.ORDPAR_STRINGS.en=window.ORDPAR_STRINGS.en||%s;"
            % json.dumps(chrome.strings("en"), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")))


COMBINED = {
    CSS_ALL_HREF: ARTICLE_CSS_PARTS,
    JS_ALL_HREF: (_strings_part(),) + ARTICLE_JS_PARTS,
    SHELL_PAGES_CSS_HREF: SHELL_CSS_PARTS,
    SHELL_PAGES_JS_HREF: SHELL_JS_PARTS,
}
#: Every script and stylesheet the article build writes to `out/site/` itself (the rest of the
#: folder is `ordpar/site/` copied, then stripped of its comments in place)
GENERATED = (CSS_HREF, PAGE_CSS_HREF, JS_HREF, THEME_JS_HREF) + tuple(COMBINED)


def _e(text):
    return html.escape(text or "", quote=False)


@functools.lru_cache(maxsize=None)
def _chrome_strings():
    return chrome.strings("en")


def chrome_strings(strings):
    """The header's and footer's strings: the shell's, with `strings` (the article build's,
    `strings.py`) over them."""
    merged = dict(_chrome_strings())
    merged.update(strings)
    return merged


def credit_line(strings):
    """The one-line credit (decisions 32 and 12, amended 2026-10-17), in the footer of every page
    since decisions 63 — `chrome.credit`: "Bokmålsordboka" links ordbokene.no in general (Robin,
    2026-10-19: no per-article source link), the licence, the About page."""
    return chrome.credit(chrome_strings(strings))


def _sheets(*hrefs):
    return "\n".join('<link rel="stylesheet" href="%s">' % asset(h) for h in hrefs)


def about_page(stamp, strings, stats):
    """`/about/`: the full attribution the credit points at — the rights holders, the
    licence, what Ordpar changed, not affiliated, no warranty (CC BY 4.0 § 3(a)(1)) — with the
    build's numbers (`stats`, `site_stats.measure()`'s). Its text is `ordpar/about.md`, the
    same source as the published README (`about.py`, decisions 63, 2026-10-22). The site's
    header and footer (decisions 63)."""
    title, body = about_mod.page(stats)
    return _prose_page(stamp, strings, title, body, chrome.ABOUT_HREF, indexed=True)


def privacy_page(stamp, strings, draft=False, counting=None, reports=None, survey=None):
    """`/privacy/` (site decisions 104's box, item 5): what the site sends and keeps, from
    `ordpar/privacy.md` (`about.privacy_page`, the About page's Markdown subset), in the About
    page's frame. Built while `chrome.PRIVACY` is on (and for a look build alone, site decisions
    166); refused while the text holds a `[[…]]` placeholder, unless `draft` (a preview). Its
    `[if counting]`, `[if reports]` and `[if survey]` follow the switches unless `counting` /
    `reports` / `survey` say."""
    title, body = about_mod.privacy_page(draft=draft, counting=counting, reports=reports, survey=survey)
    return _prose_page(stamp, strings, title, body, chrome.PRIVACY_HREF)


def help_page(stamp, strings):
    """`/help/` (site decisions 123 as amended, Robin 2026-10-24): what a reader needs to read only
    once, kept out of the articles — for now one section, Pronunciation (`#pronunciation`), the
    note on the field's marks. Its text is `ordpar/help.md` (`about.help_page`), in the About
    page's frame."""
    title, body = about_mod.help_page()
    return _prose_page(stamp, strings, title, body, chrome.HELP_HREF, indexed=True)


def coming_page(stamp, strings):
    """`/coming/` (site decisions 131, 2026-10-25): "Coming to Ordpar", the work decided and what
    each waits for. Its text is `ordpar/coming.md` (`about.coming_page`), in the About page's frame;
    indexed, as About and Help; linked from About's "How far it has come", not from the footer."""
    title, body = about_mod.coming_page()
    return _prose_page(stamp, strings, title, body, chrome.COMING_HREF, indexed=True)


def changes_page(stamp, strings):
    """`/changes/` (site decisions 175, made public): "Changes to the
    Ordpar site", one dated entry per deploy, from `ordpar/changes.md` (`about.changes_page`), in
    the About page's frame with the about pages' tabs (Changes pressed); indexed, as Coming;
    reached by the Changes tab and the update note's "What's new" (`offline.js`)."""
    title, body = about_mod.changes_page()
    return _prose_page(stamp, strings, title, body, chrome.CHANGES_HREF, indexed=True)


def library_changes_page(stamp, strings):
    """`/dictionary-changes/` (site decisions 175): "Changes to the Ordpar dictionary", from
    `ordpar/library-changes.md` (`about.library_changes_page`), as `changes_page`; linked from the
    site's and the decks' lists."""
    title, body = about_mod.library_changes_page()
    return _prose_page(stamp, strings, title, body, chrome.DICTIONARY_CHANGES_HREF, indexed=True)


def deck_changes_page(stamp, strings):
    """`/deck-changes/` (site decisions 177): "Changes to the Ordpar Anki decks", from
    `ordpar/deck-changes.md` (`about.deck_changes_page`; the deck session's file), as
    `changes_page`."""
    title, body = about_mod.deck_changes_page()
    return _prose_page(stamp, strings, title, body, chrome.DECK_CHANGES_HREF, indexed=True)


def more_page(stamp, strings):
    """`/more/` (site decisions 142, Robin 2026-10-26/27): "More ways to use Ordpar" — the Definer
    pop-up, the Anki deck, the offline copy, each section at its fixed id (`#popup`, `#anki`,
    `#offline`). Its text is `ordpar/more.md` (`about.more_page`), in the About page's frame;
    indexed, as Help; linked from the home page's line under Random word and from every footer,
    after Help (`chrome.MORE_HREF`)."""
    title, body = about_mod.more_page()
    return _prose_page(stamp, strings, title, body, chrome.MORE_HREF, indexed=True)


def thanks_page(stamp, strings, fixes, headword, ideas=()):
    """`/thanks/` (site decisions 166, Robin 2026-11-05): "Thanks to our readers", the fixes readers'
    reports led to — the two counts and the list, newest first, a name only where the reader gave
    it and Robin published it. Its words are `ordpar/thanks.md`, its list `fixes`
    (`thanks.read_fixes`, the committed `ordpar/reader-fixes.jsonl`), each fix's word
    `headword(article)` (`thanks.mirror_headword`); in the About page's frame, indexed as About;
    linked from About's "Thanks", not from the footer. Since site decisions 183 also readers' ideas,
    `ideas` (`thanks.read_ideas`, the committed `ordpar/reader-ideas.jsonl`, kept by hand)."""
    title, body = thanks_mod.page(fixes, headword, ideas=ideas)
    return _prose_page(stamp, strings, title, body, chrome.THANKS_HREF, indexed=True)


def survey_page(stamp, strings, data=None):
    """`/survey/` (site decisions 173, Robin 2026-11-07): "Ordpar — your first impressions", the
    readers' survey, from `ordpar/site/survey.json` (`survey.body`), in the About page's frame with
    its own script after the page's (`survey.js`, which sends the answers); `noindex`. Built while
    the survey is on (`chrome.survey_receiver()`), linked from every footer."""
    title, body = survey_mod.body(data)
    return _prose_page(stamp, strings, title, body, chrome.SURVEY_HREF, scripts=(SURVEY_JS_HREF,))


def _prose_page(stamp, strings, title, body, path, indexed=False, scripts=()):
    """A page of prose in the site's chrome: the About page, the privacy page, the Help page, the
    "Coming to Ordpar" page (decisions 131), "More ways to use Ordpar" (decisions 142), the three
    change lists (site decisions 175, 177), Thanks (166), the survey (173). `indexed`
    (site decisions 128): About, Help, Coming, More, Thanks and the change lists are indexed, the
    privacy page and the survey are not. None of
    them has a meta description, so its link preview carries none (`head.social_tags`). The about
    pages' tabs (site decisions 176, `chrome.about_tabs`) go directly under the `<h1>` of the pages
    that carry them — About, Coming, the change lists, Privacy, Thanks — and nowhere else."""
    cs = chrome_strings(strings)
    full_title = title + strings["title_suffix"]
    # the build stamp stays on this one page (the article pages lost theirs on 2026-10-20 —
    # `build.json` and the offline manifest carry it), so a served page still names its build;
    # the page's one sheet and one script are the article page's (the script registers the
    # service worker, which `SW_REGISTER` did here until then)
    return finish("""<!doctype html>
<!-- %(stamp)s -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s%(suffix)s</title>
<link rel="canonical" href="https://ordpar.no%(path)s">
%(head)s
%(theme)s
%(sheets)s
</head>
<body class="ordpar">
%(header)s<main id="ordpar-main" class="ordpar-main" tabindex="-1">
<article class="ordpar-about">
<h1>%(title)s</h1>
%(tabs)s%(body)s
</article>
</main>
%(footer)s<script src="%(js)s" defer></script>
%(more)s</body>
</html>
""" % {"stamp": stamp, "title": _e(title),
       "head": head_tags(indexed=indexed, social={"url": path, "title": full_title}),
       "suffix": _e(strings["title_suffix"]), "theme": theme_tag(),
       "sheets": _sheets(CSS_ALL_HREF),
       "header": chrome.header(cs), "footer": chrome.footer(cs),
       "js": asset(JS_ALL_HREF), "body": body, "path": path, "tabs": chrome.about_tabs(cs, path),
       "more": "".join('<script src="%s" defer></script>\n' % asset(u) for u in scripts)})


def theme_tag():
    """The head script's tag (`head.THEME_JS`, `/site/theme.js`): parser-blocking — never
    `defer` or `async` — and before the stylesheets, so it runs before the first paint."""
    return '<script src="%s"></script>' % asset(THEME_JS_HREF)


def finish(page):
    """The post-passes every page the site build writes goes through (2026-10-20, the size
    report's items 8 and 1): a `lang` equal to the inherited one dropped
    (`slim.drop_redundant_lang`; a page whose tags it cannot follow is left as it is), then the
    indentation of every line (`slim.strip_indent`)."""
    page, _n = slim.drop_redundant_lang(page)
    return slim.strip_indent(page)


def personal_attrs(personal, head_lemma, description=None):
    """The `<html>` attributes the device's favourites read (site decisions 60; since brief
    60b the history holds searches, not articles): what a favourites row needs to draw without
    a fetch, beside `data-article-id`,
    `data-lemma` and `data-translated` — `data-hg` (the homograph number, when there is one),
    `data-hgs` (one number per spelling, "1 2", where the spellings' numbers differ — site
    decisions 93; `data-hg` is then the first non-zero),
    `data-pos` (the index's word-class code, `NOUN`, `VERB`, `EXPR` …), `data-word` (the
    headword as the search index shows it, only where it differs from `data-lemma`),
    `data-snip` (the list view's snippet, cut as in `snip/`) and `data-drop` (the
    autocomplete's own text for a translated set phrase with no summary gloss — its first
    set-phrase box, or "" for nothing; `article.dropdown_text`). The search page reads the same
    attributes from the page it fetches for a result (`lookup.js` `extractArticle`), for the
    result's heart and for a one-article search's history row.

    `data-snip` is left out where it equals the page's meta `description` (2026-10-20, the
    size report's item 7: 77 % of the pages), and the readers (`personal.js` `fieldsFrom`,
    `lookup.js` `pageMeta`) fall back to the description; where the snippet is empty but the
    description is not, `data-snip=""` keeps the empty snippet. Since site decisions 128
    (2026-10-25) the description is the longer search-engine line (`describe.description`), so
    it rarely equals the snippet any more and `data-snip` is written on most pages: the rows
    show exactly what they showed before, from the snippet, never from the new description."""
    if not personal:
        return ""
    out = []
    if personal.get("hg"):
        out.append(' data-hg="%d"' % int(personal["hg"]))
    if personal.get("hgs"):
        out.append(' data-hgs="%s"' % " ".join(str(int(h)) for h in personal["hgs"]))
    if personal.get("pos"):
        out.append(' data-pos="%s"' % html.escape(personal["pos"], quote=True))
    if personal.get("word") and personal["word"] != head_lemma:
        out.append(' data-word="%s"' % html.escape(personal["word"], quote=True))
    snip, desc = personal.get("snip") or "", description or ""
    if snip != desc:
        out.append(' data-snip="%s"' % html.escape(snip, quote=True))
    if personal.get("drop") is not None:
        out.append(' data-drop="%s"' % html.escape(personal["drop"], quote=True))
    return "".join(out)


def render(*, aid, lemmas, article, translated, other_entries, strings, stamp,
           description, mk, extra_head="", inline_css=False, personal=None, change=None,
           pos_class=None, numerals=False):
    """One whole page. `lemmas` is the list of `{form, homograph}` dicts (the title and the
    headword link for the "other entries" line); `article` the rendered fragment; `personal`
    what the favourites rows need (`personal_attrs`).

    The frame (decisions 63): the site's header (`chrome.header`, the same as every page's);
    under it the "Article view" line with "← Home" and the "N more entries" link; the article
    in a card, as a full search result, with Copy link, Share and the heart at its foot
    (`<footer class="ordpar-card-foot">` — where the search page's `extractArticle` stops); the
    site's footer with the credit (`chrome.footer`).

    Since 2026-10-20 (the size report's stages 1 and 2): no build-stamp comment (it is
    `build.json`'s and the offline manifest's); `data-other-entries` only where there are
    others (nothing read the 0); the head script `/site/theme.js` and ONE sheet; ONE deferred
    script, `/site/ordpar.js`; the card's foot EMPTY — `PAGE_JS` makes Copy link and Share,
    `personal.js` the heart; `stamp` and `extra_head` are still taken, and `stamp` is unused.
    `finish` runs last.

    Site decisions 127 and 128 (2026-10-25): the `<title>` is "word (class) — <the pair's
    dictionary name>" (`describe.page_title`: `pos_class` the page's word class, None for none;
    `numerals` keeps the homograph numerals where another page shares a spelling and the class);
    `description` is the meta description the caller made (`describe.description`); a
    translated page is indexed, an untranslated one `noindex`; the link-preview tags on both.
    `data-snip` is written wherever the snippet differs from that description
    (`personal_attrs`), so the History rows and favourites show what they showed before."""
    head_lemma = (lemmas or [{}])[0].get("form", "")
    page_title = describe.page_title(lemmas, pos_class, numerals, strings, aid)
    other = ""
    if other_entries:
        key = "other_entries_one" if other_entries == 1 else "other_entries_many"
        # a newline before it, as between the line's other pieces (site decisions 154: the
        # "Article view" line is a flex row, where it draws nothing; a text extraction would
        # otherwise join "Home" and "2 more entries for …")
        # site decisions 152: in both languages (the labels setting; `strings.NB`, a draft)
        from .article import label_pair
        from .strings import NB
        other = ('\n<a href="%s">%s</a>'
                 % (site_face.lemma_url(head_lemma),
                    label_pair(strings[key].format(n=other_entries, lemma=head_lemma),
                               NB[key].format(n=other_entries, lemma=head_lemma))))

    caption = note = ""
    if not translated:
        # site decisions 152: in both languages (the labels setting; DRAFTS); Norwegian only
        # hides both (`SITE_CSS`)
        from .article import label_pair
        from .strings import NB
        caption = ('<p class="ordpar-caption">%s</p>\n'
                   % label_pair(strings["status_untranslated"], NB["status_untranslated"]))
        note = ('<p class="ordpar-note">%s</p>\n'
                % label_pair(strings["untranslated_note"], NB["untranslated_note"]))
    cs = chrome_strings(strings)

    return finish("""<!doctype html>
<html lang="en"%(others)s data-article-id="%(aid)d" \
data-lemma="%(lemma)s" data-translated="%(translated)s"%(personal)s>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<link rel="canonical" href="%(canonical)s">
<meta name="description" content="%(description)s">
%(head)s
%(theme)s
%(css)s
</head>
<body class="ordpar">
%(header)s<main id="ordpar-main" class="ordpar-main ordpar-main--cards" tabindex="-1">
<p class="ordpar-viewline"><span class="ordpar-section-title ordpar-dict-title">%(view)s</span>
<a href="/"><span aria-hidden="true">← </span>%(home)s</a>%(other)s</p>
<article class="ordpar-card ordpar-entry">
%(caption)s%(note)s%(article)s
<footer class="ordpar-card-foot">%(change)s</footer>
</article>
</main>
%(footer)s%(extra_head)s<script src="%(js)s" defer></script>
</body>
</html>
""" % {"others": (' data-other-entries="%d"' % other_entries) if other_entries else "",
       "aid": aid,
       "lemma": html.escape(head_lemma, quote=True),
       "translated": "1" if translated else "0",
       "title": _e(page_title), "canonical": CANONICAL % aid,
       "description": html.escape(description or "", quote=True),
       "theme": theme_tag(),
       "head": head_tags(indexed=translated,
                         social={"url": CANONICAL % aid, "title": page_title,
                                 "description": description or "", "strings": strings}),
       "css": ("<style>%s</style>" % shipped(CSS_ALL_HREF) if inline_css
               else _sheets(CSS_ALL_HREF)),
       "header": chrome.header(cs, "nav.skipArticle"), "footer": chrome.footer(cs),
       "view": _e(strings["article_view"]), "home": _e(strings["home_link"]),
       "other": other, "caption": caption, "note": note, "article": article,
       "change": corrections.notice_html(aid, change, cs),
       "extra_head": extra_head, "js": asset(JS_ALL_HREF),
       "personal": personal_attrs(personal, head_lemma, description)})


#: Marks the prototype front door below, so the index build replaces it with the search shell
#: (`build_index.copy_shell`) — the app's `start_url` is `/` (decisions 61).
PROTOTYPE_FRONT = "<!-- ordpar: prototype front page, written by build_site.py -->"


def index_page(pages, stamp, strings):
    """A minimal front door for the browser check — build C owns the real one. The index
    build replaces it (it carries `PROTOTYPE_FRONT`)."""
    items = "\n".join('  <li><a href="/%s/%d/">%s</a></li>' % (site_face.PAIR, aid, _e(t))
                      for aid, t in pages)
    return ("""<!doctype html>
<!-- %s -->
%s
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
<title>%s</title><link rel="stylesheet" href="%s"><link rel="stylesheet" href="%s"></head>
<body><div class="ordpar-shell"><h1 class="ordpar-brand">%s</h1>
<p>Prototype pages:</p>
<ul>
%s
</ul></div></body></html>
""" % (stamp, PROTOTYPE_FRONT, head_tags(indexed=False), _e(strings["site_name"]), asset(CSS_HREF), asset(PAGE_CSS_HREF),
       _e(strings["site_name"]), items))


def strings_json(strings):
    return json.dumps(strings, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
