# -*- coding: utf-8 -*-
"""The article fragment — the deck's card anatomy, wearing the site face.

Two shapes, one anatomy (header, Pronunciation, Etymology, Senses and Example Sentences, Set
phrases — ordbokene's English section labels, decisions 22; Pronunciation since decisions 123,
from the mirror row, `pronunciation.py`):

* **Translated** (a library row that passes `complete_strict`): every definition line — sense,
  subsense, expression sense, etymology — is a LINE PAIR (`line_pair`): the derived
  Norwegian first, carrying the cross-reference links (a plain link and its peek since
  decisions 80: the mini is cut from the target's page by the site's mini script), then the
  authored English, whose references are PARTNER words matched to those links
  (`face.SiteFace.record_links`), so each reference leads from one line only (decisions 54,
  Robin 2026-10-18). The device setting `defs` picks what shows: `both` (default — the
  Norwegian in the main style, the English beneath in the translation style, decisions 53),
  `en` (the English alone; the sheet makes each partner word the link) or
  `no` (the Norwegian, with the English behind a "Show English" cue the page script adds).
  A **formula line** (decisions 81: "brukt som adverb:", `FORMULA_RE`) is a pair marked
  `ordpar-fml`, and the setting `formulas` picks its language whatever `defs` says (the
  sheet); a compound list's label carries both languages (`comp_html`), the Norwegian one
  ordbokene's own wording, shown under `formulas = no`.
  **Examples are always bilingual and always visible**: the Norwegian quote with its
  translation beneath.
* **Untranslated**: the derived Norwegian alone — the same walk with the English left out,
  and there the Norwegian line carries the controls. Both pages get the same `#def` anchors
  and the same example markup. A compound list there (and in a translated page's untranslated
  set phrases) is `comp_html_nb`'s: every compound linked, under its one Norwegian label
  whatever the `formulas` setting (decisions 118). Every link in such a Norwegian-only unit
  takes its target's English as its peek where the target is translated (decisions 119,
  `norwegian_only`, `face.SiteFace.target_english`).

What is reused and what is not (the evidence for site decisions 30):

    unchanged   `_head_lemmas` (over a synthetic row with no id, so the headword links
                nowhere — it IS the page), `_ety_html`, `_def_line`, `idiom`, `_ex_no`,
                `_comp_html` (translated units only, since decisions 118), `_expr_order`,
                `expr_sort_key`, `NO_DEFINITION_NOTE`,
                `collapse_order`, and `postags.pos_en` for the headword groups; the
                added-example mark is the deck's `_ADDED_MARKER` with the site's own hover
                text (`ADDED_MARKER`, 2026-10-22)
    reimplemented here: the sense / subsense / example / expression walk (`_sense_body`,
                `_subs_html`, `_sub_html`, `_ex_list`, `_ex_item`, `_expr_html`) and
                `render_card` itself — because each of those renders ONE side of a unit and
                a translated page interleaves two (the Norwegian line with the controls,
                then the English with the partner words), and because the page needs a `#def`
                anchor, an inflection mount and grouped headwords that the card has nowhere
                to put. The leaves above do all the marker and section work; the walk is the
                only thing the two products do differently.
"""
import contextlib
import html
import re

from . import deck
from . import face as face_mod
from . import pronunciation
from . import slim

#: The site-wide table of paradigm shapes the compact islands name (`slim.compact_paradigm`):
#: shape id -> [paradigm tags, inflection group, [cell tags]]. `build_site.py` fills it from
#: every paradigm in the mirror before the first page, and writes it into `inflection.js`;
#: `paradigm_block` adds any shape it meets that is not there yet.
SHAPES = {}

g = deck.ordbok_gen

#: The mark after an added example sentence (`ex_added`): the deck's (`ordbok_gen._ADDED_MARKER`,
#: same element and class) with the site's hover text — "added by Ordpar", where the deck says
#: "added by this deck" (site decisions 63 (b), 2026-10-22; the About page names the mark). The
#: deck's own string is left as it is.
ADDED_MARKER = ('<sup class="ordbok-added" title="Example added by Ordpar '
                '(not from Bokmålsordboka)">+</sup>')

#: An example's translation line: the deck's own translation style (`.ordbok-tr`, muted,
#: and its night-mode colour) with our sheet turning `display:none` back on — on the site
#: the example translation is always visible.
EN_CLASS = "ordbok-tr ordpar-en"

#: The article head's separator between summary glosses (site decisions 116): the stored
#: `markup.HEADLINE_SEP` in a span the stylesheet fades (`shell.css` `.ordpar-gsep`).
GLOSS_SEP_HTML = '<span class="ordpar-gsep">%s</span>' % deck.markup.HEADLINE_SEP

_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
_HOMOGRAPH_RE = re.compile(r'<span class="ordbok-homograph">([^<]+)</span>')


# --- the header --------------------------------------------------------------

def lemma_groups(row, data=None):
    """The headword lines: `[([(form, homograph|None), …], pos_en), …]` (decisions 36, 93).

    ordbokene prints one headword line per **paradigm group** with its own part-of-speech
    line — *anskaffelse* "noun (masculine)" over *anskaffing* "noun (masculine or feminine)"
    (the capture: `…/evidence/ordbokene-selvfordypelse-header-groups-en-2026-09-20.png`). The
    group key is the mirror lemma's **paradigm-tag set** (the union over its
    `paradigm_info[].tags`) **plus the order its genders first appear in**; groups come in the
    mirror's lemma order and the forms inside one keep it too. The label is `site_pos`:
    `postags.pos_en` — the same table the deriver uses — in ordbokene's words (decisions 76),
    with the genders read in the data's order, as ordbokene prints them (decisions 36, Robin
    2026-10-17): *selvfordyping* "masculine or feminine" and *selvfordjuping* "feminine or
    masculine" are two lines, not one.

    The homograph numeral belongs to each SPELLING (site decisions 93, Robin 2026-10-22, read
    off ordbokene's rendered pages): every form carries its own lemma's `hgno` after it, a form
    numbered 0 none — *lysing* I, *lysning* II; *avrustning*, *avrusting* II; and where the
    numbers match, the numeral on each form, *tore* II, *tørre* II. So a group is a list of
    `(form, homograph|None)` pairs. Until 2026-10-22 the article's first non-zero number was
    printed once, after the first group's last form ("lysing, lysning I").
    With no mirror row to group by, the library row's own lemmas (each with its own
    `homograph`, as the deriver writes them) are the one group.
    """
    lemmas = (data or {}).get("lemmas") or []
    if not lemmas:
        forms = [(l.get("form", ""), l.get("homograph") or None) for l in row.get("lemmas") or []]
        return [(forms, site_pos_label(row.get("pos_en", "")))]
    order, groups = [], {}
    for lem in lemmas:
        tags, genders = set(), []
        for par in lem.get("paradigm_info") or []:
            for t in par.get("tags") or []:
                tags.add(t)
                if t in _GENDERS and t not in genders:
                    genders.append(t)
        key = (frozenset(tags), tuple(genders))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((deck.derive._norm_lemma(lem.get("lemma") or ""),
                            deck.derive._roman(lem.get("hgno") or 0)))
    out = []
    for key in order:
        try:
            pos = site_pos(key[0], key[1])
        except deck.postags.UnknownPOS:
            pos = site_pos_label(row.get("pos_en", ""))   # the deriver's label for the article
        out.append((groups[key], pos))
    return out


_GENDERS = {"Masc": "masculine", "Fem": "feminine", "Neuter": "neuter"}


def site_pos(tags, genders):
    """The POS label the site prints for one paradigm group, in ordbokene's words (site
    decisions 76 and its wording match, Robin 2026-10-21): `postags.pos_en`, then two
    rewordings `pos_en` (the deck's and the library's table) does not make.

    * A NOUN names every gender its paradigms carry, read off the tags as ordbokene's rendered
      pages show them (`…/evidence/pos-wording-76-2026-10-21/`): one gender alone; two in the
      data's order, "neuter or masculine" (decisions 36); all three as "masculine, feminine or
      neuter", whatever the data's order. An `Uninfl` tag does not hide the gender: *råd*
      reads "feminine or masculine", *afrikaans* "masculine or neuter". A noun with no gender
      is "uninflectable" when it is tagged `Uninfl` (*ert*), plain "noun" otherwise. `pos_en`
      says "noun (uninflected)" for every `Uninfl` noun and drops a neuter beside a masculine.
    * The subordinating conjunction is ordbokene's "subjunction" (`site_pos_label`).
    * A COMPOUND PREFIX (`COMPPFX`, *kjempe-*) is "compound prefix" / "i sammensetning", as the
      rows draw it (`pos.COMPPFX`) and ordbokene shows it; `pos_en` folds it into "prefix"
      (152's follow-up, Robin 2026-11-01: "yes, it should be one word").

    Every other label is `pos_en`'s. Raises `postags.UnknownPOS` as `pos_en` does."""
    pos = deck.postags.pos_en(tags)
    if pos == "prefix" and "COMPPFX" in set(tags) and "PFX" not in set(tags):
        return "compound prefix"
    if pos == "noun" or pos.startswith("noun ("):
        words = [_GENDERS[g] for g in genders]
        if len(words) == 3:
            return "noun (masculine, feminine or neuter)"
        if words:
            return "noun (%s)" % " or ".join(words)
        return "noun (uninflectable)" if "Uninfl" in set(tags) else "noun"
    return site_pos_label(pos)


_SITE_WORDS = {"subordinating conjunction": "subjunction",
               "noun (uninflected)": "noun (uninflectable)"}


def site_pos_label(pos):
    """A whole `pos_en` label in ordbokene's words where the two differ (site decisions 76):
    for a page with no mirror tags to read, where only the row's own label is known."""
    return _SITE_WORDS.get(pos, pos)


_POS_BRACKET = re.compile(r"^(.+?) \((.+)\)$")


# --- site decisions 152: the labels in both languages -------------------------
#: True while `fragment(site=True)` renders a page of the SITE (`build_site.Builder.page`): the
#: labels, the word class and the compound lists' Norwegian copies are drawn as the site needs
#: them. The deck's cards (`deck/render.py`) call `fragment` without it and are unchanged.
_SITE = [False]

#: The labels inside the article frame and their Norwegian (site decisions 152, Robin 2026-10-31:
#: the "labels" setting; English the default): ordbokene's own word where its rendered Bokmål
#: pages show one (the lookup of 2026-10-30, `ordbokene-interface-words-2026-10-30-lookup-web.md`:
#: Uttale, Opphav, Betydning og bruk, Faste uttrykk, Vis bøyning), else a DRAFT for Robin.
NB_LABELS = {
    "Pronunciation": "Uttale",
    "Etymology": "Opphav",
    "Senses and Example Sentences": "Betydning og bruk",
    "Set phrases": "Faste uttrykk",
    "Inflection": "Vis bøyning",
    "Not yet translated": "Ikke oversatt ennå",                       # draft
    ("These set phrases have not been translated yet. They are shown as "
     "Bokmålsordboka has them, in Norwegian."):
        "Disse faste uttrykkene er ikke oversatt ennå. De står slik Bokmålsordboka har dem.",  # draft
}


def label_pair(en, nb, attrs=""):
    """A label in both languages (site decisions 152): `<span class="ordpar-l-en">` and the
    Norwegian `<span class="ordpar-l-nb" lang="nb" data-nosnippet>` — the copy the default
    settings hide carries `data-nosnippet` (154), so a search engine reads the page as the
    default shows it — nothing between (a space there showed in an inline heading; the hidden
    copy is never read with the shown one). The sheet shows one
    (`page.SITE_CSS`, `ordpar-labels-no`; and under Norwegian only, `ordpar-nbo`, whatever the
    labels setting says: 152's follow-up). `en` and `nb` plain text."""
    return ('<span class="ordpar-l-en"%s>%s</span><span class="ordpar-l-nb" lang="nb" '
            'data-nosnippet>%s</span>'
            % (attrs, html.escape(en, quote=False), html.escape(nb, quote=False)))


def site_label(en):
    """`en` as a label inside the article: in both languages on a site page with a Norwegian word
    for it (`NB_LABELS`), else the English alone, escaped."""
    nb = NB_LABELS.get(en)
    if not _SITE[0] or not nb:
        return html.escape(en, quote=False)
    return label_pair(en, nb)


#: The word class's words in Norwegian (site decisions 152): ordbokene's where its rendered pages
#: show them (substantiv, adjektiv, verb, hankjønn, hunkjønn, intetkjønn; the lookup of 2026-11-01
#: found every other here on ordbokene too, and its "forkorting" for the abbreviation, 152's
#: follow-up), "suffiks" and "fast uttrykk" drafts.
#: Word by word over `site_pos`'s labels; a label with a word not here stays English alone.
NB_POS_WORDS = {
    "noun": "substantiv", "verb": "verb", "adjective": "adjektiv", "adverb": "adverb",
    "preposition": "preposisjon", "pronoun": "pronomen", "determiner": "determinativ",
    "quantifier": "kvantor", "demonstrative": "demonstrativ", "possessive": "possessiv",
    "subjunction": "subjunksjon", "conjunction": "konjunksjon", "interjection": "interjeksjon",
    "symbol": "symbol", "abbreviation": "forkorting", "prefix": "prefiks", "suffix": "suffiks",
    "masculine": "hankjønn", "feminine": "hunkjønn", "neuter": "intetkjønn",
    "uninflectable": "ubøyelig", "or": "eller",
}
#: Whole labels first (two English words, one Norwegian)
NB_POS_PHRASES = {"proper noun": "egennavn", "fixed expression": "fast uttrykk",
                  "compound prefix": "i sammensetning"}


def nb_pos(text):
    """A `site_pos` label (or a part of one) in Norwegian, or None where a word is not known."""
    if text in NB_POS_PHRASES:
        return NB_POS_PHRASES[text]
    out = []
    for tok in re.split(r"(, | )", text or ""):
        if tok in (", ", " ", ""):
            out.append(tok)
        elif tok in NB_POS_WORDS:
            out.append(NB_POS_WORDS[tok])
        else:
            return None
    return "".join(out) or None


def pos_html(pos):
    """A POS line's inner markup as ordbokene renders it (site decisions 76, Robin 2026-10-21):
    the word class, then the gender or subclass in an `<i>` — "noun <i>feminine or
    masculine</i>", "determiner <i>quantifier</i>" — with no brackets and no comma. The class
    keeps the deck's small capitals (`.ordbok-pos`); the `<i>` is italic lower case
    (`page.SITE_CSS`). The words are `site_pos`'s; only the brackets and the comma go (a
    comma inside the brackets, "masculine, feminine or neuter", stays), so a screen reader
    hears "noun feminine or masculine". A label with neither ("verb", "proper noun") is the
    class alone. `ordbok_gen.py` (the deck) still prints the bracketed label."""
    pos = pos or ""
    m = _POS_BRACKET.match(pos)
    if not m and ", " in pos:
        m = re.match(r"^([^,]+), (.+)$", pos)
    if not m:
        en = html.escape(pos, quote=False)
        nb = html.escape(nb_pos(pos) or "", quote=False) if _SITE[0] and pos else None
    else:
        en = "%s <i>%s</i>" % (html.escape(m.group(1), quote=False),
                               html.escape(m.group(2), quote=False))
        a, b = (nb_pos(m.group(1)), nb_pos(m.group(2))) if _SITE[0] else (None, None)
        nb = ("%s <i>%s</i>" % (html.escape(a, quote=False), html.escape(b, quote=False))
              if a and b else None)
    if not nb:              # 152: "verb" is Norwegian too, and marked so under the layer
        return en
    # site decisions 152: the word class in both languages (`ordpar-w-*`), the Norwegian shown
    # under Norwegian only or the labels setting; `data-nosnippet` on the copy the default hides
    return ('<span class="ordpar-w-en">%s</span><span class="ordpar-w-nb" lang="nb" '
            'data-nosnippet>%s</span>' % (en, nb))


def head_html(row, strings, data=None, gloss=None):
    """The headword block: one line per paradigm group (`lemma_groups`), each over its own
    POS line, then the summary gloss under them (decisions 42: the authored salience order;
    the per-item sense marks wait for the sense tags). `gloss` is the list of expanded HTML
    strings, or nothing on an untranslated page. Each line is the deck's own `_head_lemmas` markup, built from a synthetic row
    with no `id` — so no form links anywhere: on its own page the headword is not a link.

    Each spelling's Roman homograph numeral (decisions 93) is hidden from assistive technology
    and given a visually hidden reading beside it (decisions 33 (1)): "lysing, homograph 1,
    lysning, homograph 2". The reading carries `data-nosnippet` (site decisions 154): Google put
    "være III homograph 3" in its snippet."""
    def a11y(m):
        num = _ROMAN.get(m.group(1).strip(), m.group(1).strip())
        return ('<span class="ordbok-homograph" aria-hidden="true">%s</span>'
                '<span class="sr-only" data-nosnippet> %s</span>'
                % (m.group(1), html.escape(strings["homograph"].format(n=num), quote=False)))

    out = ['  <div class="ordbok-head">']
    for i, (forms, pos) in enumerate(lemma_groups(row, data)):
        synthetic = {"lemmas": [{"form": f, "homograph": hg} for f, hg in forms]}
        line = _HOMOGRAPH_RE.sub(a11y, g._head_lemmas(synthetic))
        tag = "h1" if i == 0 else "p"     # one heading per article; the rest are its siblings
        out.append('    <%s class="ordpar-hw" lang="nb">%s</%s>' % (tag, line, tag))
        if pos == "fixed expression":
            continue      # site decisions 22 as amended: ordbokene prints no word class for one
        out.append('    <span class="ordbok-pos" lang="en">%s</span>' % pos_html(pos))
    if gloss:
        # the " · " between the glosses faded, in the gloss's weight (site decisions 116,
        # Robin 2026-10-24): the same separator, `markup.HEADLINE_SEP`, in a span of its own
        out.append('    <p class="ordpar-gloss" lang="en">%s</p>'
                   % GLOSS_SEP_HTML.join(gloss))
    out.append('  </div>')
    return "\n".join(out)


def paradigm_block(data, strings):
    """The paradigm as DATA plus the mount point build B renders into (decisions 24,
    refinement 3). Since 2026-10-20 the island is in the compact schema (the size report's item
    9c, `slim.compact_paradigm`): only what `inflection.js` reads, each paradigm a shape id
    (the site-wide table `SHAPES`, which the build writes into `inflection.js`) and its forms,
    `<` escaped. Until then the mirror row's lemmas went in verbatim, holes included.

    The mount sits behind an "Inflection" toggle, closed, as in ordbokene's results list
    (Robin, 2026-09-24); the device setting `infl = open` opens it (`page.PAGE_JS`). The toggle
    ships `hidden` and `inflection.js` reveals it only when a table was rendered, so an
    uninflected word — or a reader without JavaScript — never sees an empty button. Where no
    paradigm has a tagged form there is nothing to render, so neither the island nor the toggle
    is written (item 9b): "" comes back."""
    payload = slim.compact_paradigm(data, SHAPES)
    if payload is None:
        return ""
    return ('  <script type="application/json" id="ordpar-paradigm">%s</script>\n'
            '  <details class="ordpar-infl-toggle" hidden><summary>%s</summary>\n'
            '  <div class="ordpar-inflection" data-paradigm="ordpar-paradigm"></div>\n'
            '  </details>'
            % (payload, label_pair(strings["inflection"], NB_LABELS["Inflection"]) if _SITE[0]
               else html.escape(strings["inflection"], quote=False)))


# --- bilingual units ---------------------------------------------------------

def _en_span(inner, cls=EN_CLASS):
    return '<span class="%s" lang="en">%s</span>' % (cls, inner)


def _ex_item(no_html, en_html, marker="", expl_html=None):
    """One example line, both languages visible: the deck's Norwegian face (`_ex_no` —
    italic quote, upright explanation after an en dash) and the translation beneath it. The
    card's "Show translation" reveal is a self-test device and has no place on the site.

    A newline before the translation (site decisions 154): it is a line of its own on the page
    (`.ordpar-en`, a block), and Google's snippet ran the two together ("de kommer kanskje i
    morgenperhaps they'll come tomorrow"). Before a block, a newline ends the line above, where
    it draws nothing."""
    en = ("\n" + _en_span(en_html)) if en_html else ""
    return ('<li><span lang="nb">%s</span>%s%s</li>'
            % (g._ex_no(no_html, expl_html), marker, en))


def _en(mk, text, strict):
    """An English string, expanded as the deck expands it (its cross-references are the
    site's links, `face.SiteFace.xref`)."""
    return mk.expand(text, norwegian=False, strict=strict) if text else ""


def line_pair(no_html, en_html, cls="ordbok-def", formula=False):
    """A Norwegian line and its English line in one wrapper, Norwegian FIRST, as the examples
    are (decisions 53). The sheet picks what shows from the `defs` setting (decisions 54):
    both (default, with JavaScript off too), the English alone, or the Norwegian with the
    English behind a "Show English" cue — which the page script adds only in that setting,
    since only a script can have set it, so no page ships the cue. Either half alone is
    returned on its own, outside a pair, and shows in every setting.

    `formula` marks a formula line (decisions 81, `is_formula`): the pair gets `ordpar-fml`,
    and the setting `formulas` decides its language in the sheet (`page.SITE_CSS`).

    A newline between the two lines (site decisions 154, Robin 2026-10-31): they are two lines on
    the page, and with nothing between them in the markup a text extraction joined the last word
    of one to the first of the other (Google's snippet: "maybeused to express a possibility"). The
    pair is a flex column (`page.SITE_CSS`; a mini's `mini-pair` is two blocks), where a newline
    between the children draws nothing."""
    no = '<span class="%s" lang="nb">%s</span>' % (cls, no_html) if no_html else ""
    en = '<span class="%s" lang="en">%s</span>' % (cls, en_html) if en_html else ""
    if not (no and en):
        return no or en
    return '<span class="ordpar-pair%s">%s\n%s</span>' % (" ordpar-fml" if formula else "", no, en)


#: The word classes a formula line may name (decisions 81): the closed list, measured over the
#: library and the mirror on 2026-10-21 (`ordpar/docs/build-site.md` § Definition lines and their settings)
FORMULA_CLASSES = ("adverb", "adjektiv", "substantiv", "preposisjon", "pronomen", "verb",
                   "interjeksjon", "konjunksjon", "subjunksjon", "determinativ", "artikkel")

#: A formula line (decisions 81, Robin 2026-10-21): the WHOLE Norwegian definition is
#: "(brukt) som (forsterkende) <word class>", "brukt i nøytrum" or "brukt i ikke-tellelig
#: betydning", with or without the final colon — nothing else on the line, no link
FORMULA_RE = re.compile(r"^(?:(?:brukt )?som (?:forsterkende )?(?:%s)|brukt i nøytrum"
                        r"|brukt i ikke-tellelig betydning):?$" % "|".join(FORMULA_CLASSES))


def is_formula(u_no):
    """Is this unit's definition a formula line? Its stored Norwegian is one segment that
    `FORMULA_RE` matches whole (a link would carry `](`, which the pattern cannot match)."""
    segs = [s for s in (u_no or {}).get("no") or [] if s]
    return len(segs) == 1 and bool(FORMULA_RE.match(segs[0].strip()))


#: The Norwegian label of a compound list (decisions 81, `formulas = no`) for a block derived
#: before decisions 151, which has no `intro`, by its old English label: ordbokene's own
#: commonest intros, as its pages print them (lower case, no colon; checked on ordbokene.no
#: 2026-10-21: *hus* 24627 "som etterledd i ord som", *aften* 320 "i ord som"). A transition
#: fallback only: once the library is re-derived every block carries its `intro`, and a row
#: derived from the mirror at build time always does (`library.Store.derived`).
COMP_NB = {"used as a suffix in:": "som etterledd i ord som",
           "used as a prefix in:": "som forledd i ord som",
           "also found in compounds:": "i ord som"}


def comp_nb_label(u_no, i, blk):
    """The Norwegian label of a compound list: the block's own `intro`, the capture's words as the
    deriver read them (decisions 151; `""` where the source has none, and the list then has no
    label line); for a block derived before 151 (no `intro` key), `COMP_NB` by its old English
    label. `u_no` and `i` (the unit and the list's place in it) are kept for the callers."""
    if "intro" in blk:
        return (blk.get("intro") or "").strip()
    label = (blk.get("label") or "").lower()
    return COMP_NB.get(label, COMP_NB["also found in compounds:"])


def comp_html(blk, mk, strict, side, nb_label=None):
    """`ordbok_gen._comp_html` with the site's two changes: the block carries `ordpar-comp` (the
    mini script tells a compound list from a subsense by it), and on a translated page
    (`side='en'`) the label is both languages — `ordpar-cl-en` (decisions 47's lowercase
    English) and `ordpar-cl-nb` (`comp_nb_label`), the sheet showing the Norwegian only under
    `formulas = no` (decisions 81). A Norwegian-only unit (`side='no'`) is `comp_html_nb`'s. A
    list with no intro has no label in either language (decisions 151): no label line."""
    if side == "no":
        return comp_html_nb(blk, mk, strict, nb_label)
    blk = face_mod.lowercase_comp_block(blk)
    out = g._comp_html(blk, mk, strict, side)
    out = out.replace('<div class="ordbok-sub">', '<div class="ordbok-sub ordpar-comp">', 1)
    if side == "en" and nb_label and blk["label"]:
        old = '<span class="ordbok-def"><em>%s</em>' % html.escape(blk["label"], quote=False)
        # site decisions 152 (Robin, 2026-10-31): the copy the default hides (the Norwegian, shown
        # only under `formulas` = no; the default `both` keeps the labels English, site decisions
        # 174) carries `data-nosnippet` on the site (154's rule for paired copies)
        new = ('<span class="ordbok-def"><em><span class="ordpar-cl-en">%s</span>'
               '<span class="ordpar-cl-nb" lang="nb"%s>%s</span></em>'
               % (html.escape(blk["label"], quote=False), " data-nosnippet" if _SITE[0] else "",
                  html.escape(nb_label, quote=False)))
        out = out.replace(old, new, 1)
    return out


def comp_html_nb(blk, mk, strict, nb_label=None):
    """A compound list on a Norwegian-only unit — an untranslated page, and a translated page's
    untranslated set phrases (decisions 118, Robin 2026-10-24). Until then the deck's source view
    (`ordbok_gen._comp_html`, `side='no'`): plain italics under the deriver's English label.
    Now, as ordbokene's page: **every compound a link** to its article, drawn as the page's other
    Norwegian-only references (`markup.expand` of a bare `[word](href)` — untitled, so its peek
    is its target's English, or none, as those: decisions 119, `face.SiteFace.target_english`), a compound with no target plain
    italics; and **the label Norwegian** whatever the `formulas` setting — `nb_label`
    (`comp_nb_label`: the block's own `intro`, decisions 151), one label, no `ordpar-cl-*` pair;
    none where the source has no intro. The block's markup is otherwise the translated page's
    (`ordpar-comp`, the upright label)."""
    label = nb_label if nb_label is not None else comp_nb_label(None, 0, blk)
    parts = []
    for it in blk.get("items") or []:
        word, href = it.get("word") or "", it.get("href")
        if href:
            parts.append(mk.expand("[%s](%s)" % (word, href), norwegian=True, strict=strict))
        else:
            parts.append("<em>%s</em>" % html.escape(word, quote=False))
    if not label and not parts:
        return ""
    line = (("<em>%s</em> %s" % (html.escape(label, quote=False), ", ".join(parts))) if label
            else ", ".join(parts))
    return ('        <div class="ordbok-sub ordpar-comp">\n'
            '          <span class="ordbok-def">%s</span>\n'
            '        </div>' % line)


def paired_lines(mk, render_no, render_en):
    """Render one line pair's two halves in the order the matching needs: the Norwegian line
    under `record_links` (full controls, recorded by target), then the English under
    `partner_links` (decisions 54). A unit with no Norwegian line renders its English with
    the controls, as before — there is nothing to lead it."""
    with mk.record_links():
        no_line = render_no()
    if not no_line:
        return "", render_en()
    with mk.partner_links():
        return no_line, render_en()


def _ex_list(u_no, u_en, mk, strict):
    """The unit's examples, native then added, each Norwegian over English."""
    exs = u_no.get("ex") or []
    en_exs = (u_en.get("ex") or []) if u_en else []
    items = []
    for i, pair in enumerate(exs):
        no, _e, expl = (list(pair) + [None, None, None])[:3]
        no_html = mk.expand(no or "", norwegian=True, strict=strict)
        expl_html = mk.expand(expl, norwegian=True, strict=strict) if expl else None
        en = en_exs[i][1] if i < len(en_exs) else None
        items.append(_ex_item(no_html, _en(mk, en, strict), expl_html=expl_html))
    added_en = (u_en.get("ex_added") or []) if u_en else []
    for i, e in enumerate(u_no.get("ex_added") or []):
        no_html = mk.expand(e.get("no") or "", norwegian=True, strict=strict)
        en = added_en[i].get("en") if i < len(added_en) else None
        items.append(_ex_item(no_html, _en(mk, en, strict), marker=ADDED_MARKER))
    if not items:
        return ""
    return ('<ul class="ordbok-ex-list">\n          %s\n        </ul>'
            % "\n          ".join(items))


#: The English label of a fixed expression's "Se:" line (decisions 153; `Se:` → "see:",
#: `docs/translation-conventions.md`'s table of link roles)
SEE_LABEL_EN = "see:"

_SEE_HEAD_RE = re.compile(r"^\s*(Se|Sjå):\s*")


def see_html(u_no, mk, strict, bilingual):
    """A fixed expression's "Se:" line(s) on its standalone page (site decisions 153, Robin
    2026-10-30): the unit's `see` field (the deriver's, mechanical Norwegian, no English slot),
    one line per segment, after the unit's definition line and before its examples, where
    ordbokene draws it (its rendered *holde i age* 100606, *aksle seg* 100615). The label is a
    formula line's, as a compound list's (decisions 81): on a translated page "see:"
    (`ordpar-cl-en`) and ordbokene's own word (`ordpar-cl-nb`, "Se:" or "Sjå:"), the sheet
    showing the Norwegian under `formulas = no`; on an untranslated page the Norwegian alone
    (decisions 118). Upright, as the compound label. The links are Norwegian-visible, italic and
    untitled, drawn inside `norwegian_only`, so each takes its target's English as its peek
    (decisions 119, `face.SiteFace.target_english`), or none. Not `ordbok-def`: the line is not a
    definition (the meta description's harvest, `describe.definitions`, and the mini script's
    `isDefLine` read that class). "" where the unit has no `see`."""
    out = []
    with norwegian_only(mk):
        for seg in u_no.get("see") or []:
            m = _SEE_HEAD_RE.match(seg or "")
            nb_label = (m.group(1) + ":") if m else ""
            rest = seg[m.end():] if m else (seg or "")
            links = mk.expand(rest, norwegian=True, strict=strict)
            if bilingual:
                # site decisions 152: `data-nosnippet` on the copy the default hides (154)
                label = ('<span class="ordpar-cl-en" lang="en">%s</span>'
                         '<span class="ordpar-cl-nb" lang="nb" data-nosnippet>%s</span>'
                         % (html.escape(SEE_LABEL_EN, quote=False),
                            html.escape(nb_label, quote=False)))
                out.append('          <span class="ordpar-see">%s %s</span>' % (label, links))
            else:
                out.append('          <span class="ordpar-see" lang="nb">%s %s</span>'
                           % (html.escape(nb_label, quote=False), links))
    return out


def _unit_inner(u_no, u_en, mk, strict, strings, drop_see_also=False, see_lines=False):
    """One sense or subsense.

    On a **translated** page the definition line is a line pair (`line_pair`): the derived
    Norwegian carrying the controls, then the authored English with partner words
    (`paired_lines`, decisions 54). With `u_en` None it is the Norwegian face alone, and
    that line carries the controls — the same walk either way, so both pages get the same
    anchors and example markup.

    `see_lines`: draw the unit's "Se:" line after its definition line (`see_html`, decisions
    153) — set for an expression's standalone page only; an embedded expression
    (`drop_see_also`) never has it."""
    out = []
    if u_en:
        no_line, en_line = paired_lines(
            mk, lambda: g._def_line(u_no, "no", mk, strict, drop_see_also),
            lambda: g._def_line(u_en, "en", mk, strict, drop_see_also))
        pair = line_pair(no_line, en_line, formula=is_formula(u_no))
        if pair:
            out.append('          ' + pair)
    else:
        no_line = g._def_line(u_no, "no", mk, strict, drop_see_also)
        if no_line:
            out.append('          <span class="ordbok-def" lang="nb">%s</span>' % no_line)
    if see_lines and not drop_see_also:
        out += see_html(u_no, mk, strict, bilingual=bool(u_en))
    if u_en and u_en.get("idiom"):
        out.append('          %s' % g.idiom(u_en["idiom"]))
    el = _ex_list(u_no, u_en, mk, strict)
    if el:
        out.append('          ' + el)
    # The compound list is already bilingual on the card — Norwegian words, the authored
    # gloss in the hover — so it renders once, in the deck's armed form; its label in both
    # languages on a translated page (decisions 81, `comp_html`); a Norwegian-only unit's linked,
    # under its Norwegian label alone (decisions 118, `comp_html_nb`)
    for i, blk in enumerate((u_en or u_no).get("comp") or []):
        h = comp_html(blk, mk, strict, "en" if u_en else "no",
                      comp_nb_label(u_no, i, blk))   # decisions 47, 151
        if h:                                        # "" for an empty list (*bo* 6739)
            out.append(h)
    return out


def _subs_html(subs_no, subs_en, mk, strict, strings, drop_see_also=False, numbered=False,
               id_prefix="", see_lines=False):
    """The subsenses of one sense — numbered only where the deck numbers them (a solo,
    unnumbered top sense with ≥2 subs; `ordbok_gen._subs_html`). Each carries the anchor
    `id="<id_prefix>def<N>"`: the bare `defN` on the article's own senses, which the site's
    cross-references link to; an embedded expression's are prefixed (`expr_anchor_prefix`)."""
    if not subs_no:
        return []
    pairs = list(zip(subs_no, subs_en or [None] * len(subs_no)))
    if numbered and len(subs_no) >= 2:
        out = ['        <ol class="ordbok-senses ordbok-subsenses">']
        for u_no, u_en in pairs:
            out.append('          <li id="%sdef%s">' % (id_prefix, u_no.get("defn")))
            out += _unit_inner(u_no, u_en, mk, strict, strings, drop_see_also, see_lines)
            out.append('          </li>')
        out.append('        </ol>')
        return out
    return ['\n'.join(['        <div class="ordbok-sub" id="%sdef%s">'
                       % (id_prefix, u_no.get("defn"))]
                      + _unit_inner(u_no, u_en, mk, strict, strings, drop_see_also, see_lines)
                      + ['        </div>'])
            for u_no, u_en in pairs]


def _sense_body(s_no, s_en, mk, strict, strings, number_subs=False, see_lines=False):
    return (_unit_inner(s_no, s_en, mk, strict, strings, see_lines=see_lines)
            + _subs_html(s_no.get("subs") or [], (s_en or {}).get("subs") or [],
                         mk, strict, strings, numbered=number_subs, see_lines=see_lines))


def expr_anchor_prefix(eid):
    """The prefix of an embedded expression's sense anchors on its parent's page:
    `x<expression id>-`, so *ikke* (25712)'s own `#def2` and the `def2` of an expression it
    embeds are two ids (`x<id>-def2`), and two expressions never share one either. The
    parent's own `#defN` stay bare — every cross-reference on the site links to those
    (`face.site_url`); nothing links to an embedded expression's sense, since a reference to
    an expression goes to the expression's own page, where its senses are the bare ones
    (site decisions 57, 2026-10-19). ordbokene's own page repeats the id (25712 carries
    `def2` twice, its DOM read 2026-10-19); this is where we diverge, on purpose."""
    return "x%s-" % eid


def _expr_html(e_no, e_en, mk, strict, strings):
    """One expression sub-article inlined in full, both faces (`ordbok_gen._expr_html`'s
    shape: the bold term, then its senses; the `Se: …` line dropped, as the embedded view
    always does). Its sense anchors are prefixed (`expr_anchor_prefix`)."""
    prefix = expr_anchor_prefix(e_no.get("id"))
    term = html.escape((e_no.get("lemmas") or [{}])[0].get("form", ""), quote=False)
    out = ['    <div class="ordbok-expr">',
           '      <span class="ordbok-expr-term" lang="nb">%s</span>' % term]
    senses = e_no.get("senses") or []
    en_senses = (e_en or {}).get("senses") or []
    multi = len(senses) > 1
    if multi:
        out.append('      <ol class="ordbok-expr-senses">')
    for i, s in enumerate(senses):
        s_en = en_senses[i] if i < len(en_senses) else None
        if multi:
            out.append('        <li>')
        out += _unit_inner(s, s_en, mk, strict, strings, drop_see_also=True)
        out += _subs_html(s.get("subs") or [], (s_en or {}).get("subs") or [],
                          mk, strict, strings, drop_see_also=True, numbered=not multi,
                          id_prefix=prefix)
        if multi:
            out.append('        </li>')
    if multi:
        out.append('      </ol>')
    out.append('    </div>')
    return "\n".join(out)


# --- the fragment ------------------------------------------------------------

def norwegian_only(mk):
    """The scope of a Norwegian-only unit (decisions 119): the face's `norwegian_only`, inside
    which an untitled link's peek is its target's English (`face.SiteFace.target_english`); a
    stand-in `mk` without one (a test's) gets a scope that does nothing."""
    scope = getattr(mk, "norwegian_only", None)
    return scope() if scope is not None else contextlib.nullcontext()


def fragment(row_no, row_en, lib, mk, strings, data=None, paradigm=True, strict=True,
             untranslated_exprs=(), see_lines=False, site=False):
    """`_fragment`, an untranslated page (`row_en` None) rendered inside `norwegian_only`: every
    link on it a Norwegian-only unit's (decisions 119); a translated page's untranslated set
    phrases are scoped in `_fragment` itself.

    `see_lines` (decisions 153): draw a fixed expression's "Se:" lines (`see_html`) on the
    article's own senses. The site's page build sets it (`build_site.Builder.page`), so the
    expression's own page has them, and whatever lifts that page's fragment whole (the search
    page, the offline copy) with it; the default leaves them out, so the Anki deck's cards
    (`deck/render.py`) stay as they are. An embedded expression never has them.

    `site` (site decisions 152): a page of the site — the labels inside it (`site_label`), the
    word class (`pos_html`) and the inflection toggle in both languages, and `data-nosnippet` on
    the compound lists' Norwegian label copy (`_SITE`). The deck leaves it off."""
    was = _SITE[0]
    _SITE[0] = bool(site)
    try:
        if row_en is None:
            with norwegian_only(mk):
                return _fragment(row_no, row_en, lib, mk, strings, data, paradigm, strict,
                                 untranslated_exprs, see_lines)
        return _fragment(row_no, row_en, lib, mk, strings, data, paradigm, strict,
                         untranslated_exprs, see_lines)
    finally:
        _SITE[0] = was


def _fragment(row_no, row_en, lib, mk, strings, data=None, paradigm=True, strict=True,
              untranslated_exprs=(), see_lines=False):
    """The whole article, `<div class="ordbok">` and all.

    `row_en` is the same row with its reference pairs completed for English (`None` on an
    untranslated page, which renders the Norwegian face alone). `lib` holds every row the
    expressions and cross-references resolve against; `data` is the mirror row's `data` — the
    headword groups come from it always, the paradigm island only when `paradigm`.
    `untranslated_exprs` names the expressions with no complete English of their own — a
    listed expression with no library row (its own Norwegian page and search entry stay), or
    one derived from the parent's embedded copy (decisions 57). On a translated page each
    is shown whole in Norwegian, never half-English and never with an `unauthored` flag
    (decisions 58 as amended, Robin 2026-10-19: the unit is the article, embedded or not):
    after the translated ones, under the sub-heading `UNTRANSLATED_HEAD`, or — when none of
    the article's expressions is translated — with `UNTRANSLATED_NOTE` at the top of the
    block. The setting "English only" hides them (`page.py`, `ordpar-untr`). On a Norwegian
    page every expression renders alike, as on ordbokene.
    """
    bilingual = row_en is not None
    gloss = ((row_en.get("summary") or {}).get("gloss") or []) if bilingual else []
    # the root carries the fragment's language either way (the size report's caveat to item 8,
    # 2026-10-20): the search page lifts the fragment out of the page, and a future interface
    # language puts its own code on <html>
    p = ['<div class="ordbok ordpar-article" lang="%s">' % ("en" if bilingual else "nb"),
         head_html(row_no, strings, data,
                   gloss=[mk.expand(x, norwegian=False, strict=strict) for x in gloss])]
    if paradigm and data is not None:
        block = paradigm_block(data, strings)
        if block:
            p.append(block)

    # decisions 123: Bokmålsordboka's pronunciation, from the mirror row, where ordbokene's
    # page has it — after the inflection, before the etymology (`pronunciation.section_html`)
    pron = pronunciation.section_html(data, bilingual)
    if pron:
        if _SITE[0]:         # site decisions 152: its heading in both languages
            head = '<h3 lang="en">%s</h3>' % pronunciation.LABEL
            pron = pron.replace(head, '<h3 lang="en">%s</h3>' % site_label(pronunciation.LABEL), 1)
        p.append(pron)

    ety_no = row_no.get("etymology") or {}
    if ety_no.get("no"):
        # a line pair like a sense's: the Norwegian leads with the controls
        ety_en = (row_en.get("etymology") or {}) if bilingual else {}
        if ety_en.get("en"):
            no_ety, en_ety = paired_lines(mk, lambda: g._ety_html(ety_no, "no", mk, strict),
                                          lambda: g._ety_html(ety_en, "en", mk, strict))
            body = ['    ' + line_pair(no_ety, en_ety, cls="ordbok-body")]
        else:
            body = ['    <span class="ordbok-body" lang="nb">%s</span>'
                    % g._ety_html(ety_no, "no", mk, strict)]
        p += ['', '  <section class="ordbok-sec ordbok-inline">',
              '    <h3 lang="en">%s</h3>' % site_label("Etymology")] + body + ['  </section>']

    senses = row_no.get("senses") or []
    en_senses = (row_en or {}).get("senses") or []

    def en_of(i):
        return en_senses[i] if bilingual and i < len(en_senses) else None

    if senses:
        p += ['', '  <section class="ordbok-sec">',
              '    <h3 lang="en">%s</h3>' % site_label(SENSES_LABEL)]
        if len(senses) > 1:
            p.append('    <ol class="ordbok-senses">')
            for i, s in enumerate(senses):
                p.append('      <li id="def%s">' % s.get("defn"))
                p += _sense_body(s, en_of(i), mk, strict, strings, see_lines=see_lines)
                p.append('      </li>')
            p.append('    </ol>')
        else:
            # a solo top sense renders flush, unnumbered; its subs may take the numbering
            p.append('    <div id="def%s">' % senses[0].get("defn"))
            p += _sense_body(senses[0], en_of(0), mk, strict, strings, number_subs=True,
                             see_lines=see_lines)
            p.append('    </div>')
        p.append('  </section>')
    elif not row_no.get("exprs"):
        # a word ordbokene has registered but not defined — a note saying so (our wording), both views
        p += ['', '  <section class="ordbok-sec ordbok-inline">',
              '    <span class="ordbok-body ordbok-nodef" lang="en">%s</span>'
              % g.NO_DEFINITION_NOTE, '  </section>']

    if row_no.get("exprs"):
        blocks, untr = [], []
        for eid in g._expr_order(row_no["exprs"], lib):
            erow = lib.get(eid)
            if erow is None:
                continue          # counted by the build; never a flag on a shipped page
            if bilingual and eid in untranslated_exprs:
                # decisions 58 as amended: whole in Norwegian, after the translated ones; a
                # Norwegian-only unit, so its links take their targets' English (decisions 119)
                with norwegian_only(mk):
                    untr.append(_expr_html(mk.pair_view(erow, "no"), None, mk, strict, strings))
                continue
            blocks.append(_expr_html(mk.pair_view(erow, "no"),
                                     mk.pair_view(erow, "en") if bilingual else None,
                                     mk, strict, strings))
        if untr:
            label = ('    <p class="ordpar-untr-head" lang="en">%s</p>'
                     % site_label(UNTRANSLATED_HEAD if blocks else UNTRANSLATED_NOTE))
            blocks.append('\n'.join(['    <div class="ordpar-untr" lang="nb">', label] + untr
                                    + ['    </div>']))
        if blocks:                # no heading over an empty block
            # all untranslated: "English only" hides the whole section, heading and all
            cls = "ordbok-sec ordpar-untr-only" if untr and len(blocks) == 1 else "ordbok-sec"
            p += ['', '  <section class="%s">' % cls,
                  '    <h3 lang="en">%s</h3>' % site_label(EXPRS_LABEL)] + blocks + ['  </section>']

    p.append('</div>')
    # on an untranslated page every word inside is Norwegian (the root's lang="nb"); the class
    # `ordpar-mono` the root also carried until 2026-10-20 was named by no sheet or script
    return _unique_sense_ids("\n".join(p))


# The section labels as ordbokene's English article page has them (site decisions 22 as amended,
# Robin 2026-10-19; read on its live pages: "Senses and Example Sentences", "Set phrases"; until
# then the deck's "Meaning and use", "Fixed expressions").
SENSES_LABEL = "Senses and Example Sentences"
EXPRS_LABEL = "Set phrases"

# decisions 58 as amended (Robin, 2026-10-19): the labels over a translated page's untranslated
# set phrases. Inside the fragment, so hard-coded like the section labels (`strings.py`'s note
# on that exception).
UNTRANSLATED_HEAD = "Not yet translated"
UNTRANSLATED_NOTE = ("These set phrases have not been translated yet. They are shown as "
                     "Bokmålsordboka has them, in Norwegian.")


_SENSE_ID_RE = re.compile(r' id="(def\d+)"')


def _unique_sense_ids(text):
    """The article's own `def<N>` anchors with any REPEAT suffixed `-2`, `-3`…: ordbokene's
    data can give two definitions of one article the same id (*uhørt* 63992 has def 4
    twice, mirror of 2026-09-25). The first keeps the bare id, so a `#def4` link lands where
    it always did (a browser takes the first of two); only the repeat, which no link can
    reach, is renamed (decisions 57, 2026-10-19). An expression's prefixed anchors
    (`expr_anchor_prefix`) never match."""
    seen = {}

    def sub(m):
        n = seen[m.group(1)] = seen.get(m.group(1), 0) + 1
        return m.group(0) if n == 1 else ' id="%s-%d"' % (m.group(1), n)

    return _SENSE_ID_RE.sub(sub, text)


def meta_description(row_no, row_en, mk):
    """The `<meta name="description">`: the summary gloss where one exists (its items joined by
    " · ", `markup.HEADLINE_SEP`, as the article head — 2026-10-19), else the first
    sense's Norwegian, plain (markers reduced to their visible words)."""
    gloss = ((row_en or row_no).get("summary") or {}).get("gloss") or []
    if gloss:
        text = deck.markup.HEADLINE_SEP.join(gloss)     # " · ", as the article head joins it
    else:
        first = (row_no.get("senses") or [{}])[0]
        text = ((first.get("no") or [""])[0]) or ""
        if not text:
            for u in first.get("subs") or []:
                if u.get("no"):
                    text = u["no"][0]
                    break
    return _plain(text)


def snippet(row_no, row_en):
    """The list view's snippet (site decisions 59; plan § 1.1 "our snippet is the summary gloss
    where authored"): on a translated article the summary gloss, its items joined by " · "
    (`markup.HEADLINE_SEP`, as the article head and everywhere else — Robin, 2026-10-19),
    else the first sense's English; on an untranslated one the first sense's Norwegian, as
    ordbokene's rows show its definitions. Plain text, uncut: the index build cuts it
    (`build_index.snippet_text`). The Norwegian line drops its cross-references' homograph and
    sense numbers (`drop_ref_numbers`, site decisions 144).
    Returns `(text, lang)` with `lang` "en" or "nb"."""
    if row_en is not None:
        gloss = (row_en.get("summary") or {}).get("gloss") or []
        if gloss:
            return _plain(deck.markup.HEADLINE_SEP.join(gloss)), "en"
        text = _first_line(row_en, "en")
        if text:
            return _plain(text), "en"
    return _plain(drop_ref_numbers(_first_line(row_no, "no"))), "nb"


def snippet_nb(row_no):
    """A translated article's first Norwegian definition (site decisions 152): what `snippet`
    gives an UNTRANSLATED article — the first sense's (else first subsense's) Norwegian line,
    plain, its cross-references' numbers dropped (`drop_ref_numbers`) — uncut; "" where none. The
    rows and the hovers show it under Norwegian only with the English equivalents hidden; the
    index build cuts it into the `snip/` files' `"_n"` (`build_index.snippet_files`)."""
    return _plain(drop_ref_numbers(_first_line(row_no, "no")))


#: A cross-reference's numbers at the end of its link's LABEL: a homograph numeral, a sense
#: number, or both — `[huske (III)](…)`, `[dialektikk (1)](…)`, `[hake (II, 2)](…)` — the only
#: three shapes the derived Norwegian has (2026-10-27: 6,928 / 5,567 / 2,654 labels in
#: articles.jsonl). Matched inside a link marker only, so a parenthesis of the definition's own
#: words ("(særlig drama)") is never touched.
_REF_NUMBER_RE = re.compile(r"\[([^\]]+?) \((?:[IVXL]+(?:, \d+)?|\d+)\)\]\(")


def drop_ref_numbers(text):
    """`text` (a stored Norwegian line, with its link markers) with each link label's trailing
    homograph numeral and sense number dropped — *huske (III)* → *huske* — for a one-line
    Norwegian definition in a row (site decisions 144, Robin 2026-10-27: "I would drop any
    Homographs or sense numbering inside the paranthesis, since these are more relevant for
    pointing the links themselves, but provide little inside the running texts"). The article
    keeps them; only `snippet` calls this."""
    return _REF_NUMBER_RE.sub(r"[\1](", text or "")


def snippet_is_gloss(row_no, row_en):
    """Whether `snippet` is the article's SUMMARY GLOSS (decisions 42) rather than its first
    English sense or its Norwegian: site decisions 116 (Robin, 2026-10-24) sets only the summary
    glosses semibold in the rows, so `snip/` names them (`build_index.snippet_files` "_g")."""
    return row_en is not None and bool((row_en.get("summary") or {}).get("gloss"))


def dropdown_text(row_no, row_en):
    """The autocomplete's right-hand text where it is NOT the snippet's first unit (Robin,
    2026-10-19, decisions 59 as ruled with brief 60 item 7(b) and its amendment): a translated
    SET PHRASE (`pos_en` "fixed expression") with no summary gloss shows its first authored
    set-phrase box (`idiom`, the card's "Eng. phrase": the first non-null in sense order, each
    sense before its subsenses), plain — else nothing (""). Every other article returns None:
    the dropdown takes the snippet's first unit, as before. The list view's snippet is not
    touched (`snippet`)."""
    if row_en is None:
        return None
    if (row_en.get("pos_en") or row_no.get("pos_en")) != "fixed expression":
        return None
    if (row_en.get("summary") or {}).get("gloss"):
        return None
    return _plain(first_idiom(row_en))


def first_idiom(row):
    """The row's first non-null `idiom` (the set-phrase box), senses in order, each sense's
    own before its subsenses'; "" when none."""
    for sense in row.get("senses") or []:
        if sense.get("idiom"):
            return sense["idiom"]
        for u in sense.get("subs") or []:
            if u.get("idiom"):
                return u["idiom"]
    return ""


def _first_line(row, key):
    """The first sense's first `key` line, else its first subsense's."""
    for sense in row.get("senses") or []:
        if (sense.get(key) or [""])[0]:
            return sense[key][0]
        for u in sense.get("subs") or []:
            if (u.get(key) or [""])[0]:
                return u[key][0]
    return ""


def _plain(text):
    """A stored string with its markers reduced to the words a reader sees
    (`markup.visible_faces` keeps each link's label; `{…}` mentions lose their braces)."""
    return deck.markup.visible_faces(text or "").replace("{", "").replace("}", "").strip()
