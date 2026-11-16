# -*- coding: utf-8 -*-
"""The card view: a library row (``articles.jsonl``) -> self-contained Anki-card HTML.

This module owns the card's CSS and section layout; ``scripts/mini.py`` owns the mini-
article's; ``scripts/markup.py`` owns marker expansion. Nothing else emits card markup, so
restyling anything is one edit here + a rebuild (``docs/rendering.md``).

A card is **English-facing**: the header shows the Norwegian lemma + POS, and every sense
shows its authored English (``en`` segments joined ``;<br>``); the derived Norwegian appears
only in examples (English behind a "Show translation" reveal) and inside Norwegian-visible
cross-reference links. ``render_card(row, library, …)`` returns a string — the card body plus
one inline ``<style>`` (the fuller sheet only when the card carries a two-tier control).
Expression sub-articles are inlined **in full from their own library rows**, in order.

``strict`` (a live build) makes ``markup`` raise on an untitled / row-less cross-reference;
the preview passes ``strict=False`` so those render visibly flagged instead
(``docs/rendering.md`` § link matrix, guardrails 2/6).
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import mini  # noqa: E402  -- mini-article renderer (its STYLE folds into the card CSS)

BASE = "https://ordbokene.no"


# --- cross-reference controls -----------------------------------------------

def xref(uid, visible, peek, mini_html):
    """A cross-reference as the full two-tier control: the inline `visible` word, a hover
    `peek` of its counterpart language, and a click-opened `mini_html`. Pure CSS — a checkbox
    first, so a ``~`` combinator uncovers the peek/backdrop/mini after it (no ``:has()``, so it
    works in any Anki client). `uid` is unique within the document (``markup.set_card`` salts
    it with the card freq). ``markup`` builds these from a titled link; never call it by hand."""
    cid = "xr%s" % uid
    return ('<span class="ordbok-xref">'
            '<input type="checkbox" class="ordbok-xtog" id="%s">'
            '<label class="ordbok-xword" for="%s">%s</label>'
            '<span class="ordbok-xpeek">%s</span>'
            '<label class="ordbok-xback" for="%s" aria-hidden="true"></label>'
            '<span class="ordbok-xmini">%s</span>'
            '</span>' % (cid, cid, visible, peek, cid, mini_html))


def xref_hover(visible, peek, url):
    """The hover-only control used **inside a mini**: the word + peek, minus the checkbox,
    backdrop and mini. A mini opens no further mini (the closure stops at depth one), but the
    word is a **direct link to ordbokene** (`url`) so a click still leads somewhere; the
    counterpart-language peek shows on hover (``docs/rendering.md`` § two-tier control)."""
    return ('<span class="ordbok-xref ordbok-xref-hover">'
            '<a class="ordbok-xword" href="%s" target="_blank" rel="noopener">%s</a>'
            '<span class="ordbok-xpeek">%s</span>'
            '</span>' % (html.escape(url, quote=True), visible, peek))


def idiom(text):
    """The authored English set phrase for a fixed expression, rendered as its own muted line
    after a sense's last segment: a small ``Eng. phrase`` tag + the phrase, no quotation marks
    (``docs/translation-conventions.md`` § Set phrases). Rendered on both views — the mini
    reuses this markup (``mini._idiom_line``).

    The tag reads **Eng. phrase**, not ``Eng. idiom`` (Robin, 2026-07-25): the slot holds the
    conventional English phrasing whether or not it is idiomatic — `ta bilde` → "to take a
    picture" belongs here and is no idiom. The data key stays ``idiom`` (``schemas.md``)."""
    return ('<span class="ordbok-idiom"><span class="ordbok-idiom-tag">Eng. phrase</span>'
            '<span class="ordbok-idiom-eng">%s</span></span>' % html.escape(text, quote=False))


# --- header -----------------------------------------------------------------

def article_url(article_id):
    """The ordbokene.no page for a row's own article."""
    return "%s/nob/bm/%s" % (BASE, article_id)


def _lemma_form(form, homograph=None, article_id=None):
    """One headword form. With the row's article id, the form links back to its ordbokene
    page; the homograph numeral stays outside the anchor — it marks the heading, not the word."""
    inner = html.escape(form, quote=False)
    if article_id is not None:
        inner = '<a href="%s">%s</a>' % (article_url(article_id), inner)
    s = '<span class="ordbok-lemma">%s</span>' % inner
    if homograph:
        s += ' <span class="ordbok-homograph">%s</span>' % html.escape(homograph, quote=False)
    return s


def _head_lemmas(row):
    """One or more alternative lemma forms, comma-separated like ordbokene (``en II, én``).
    Alternative forms are spellings of one article, so they all link to the same id."""
    forms = row.get("lemmas") or [{"form": row.get("lemma", ""), "homograph": None}]
    aid = row.get("id")
    parts = [_lemma_form(f.get("form", ""), f.get("homograph"), aid) for f in forms]
    return '<span class="ordbok-lemma">, </span>'.join(parts)


# --- shared field rendering (markers -> HTML via markup) ---------------------

# A segment that is WHOLLY a compare-collapse: the connective, then wrapped references and
# nothing else. `gloss — compare {X} and {Y}` does NOT match — it carries visible English of
# its own and belongs where the source put it.
_WHOLE_COLLAPSE = re.compile(
    r"^\s*compare\s+(?:\{[^{}]*\}(?:\s*(?:,|and)\s*)?)+[.;]?\s*$", re.IGNORECASE)


def is_collapse_segment(seg):
    """Is this `en` segment nothing but a compare-collapse?"""
    return bool(_WHOLE_COLLAPSE.match(seg or ""))


def collapse_order(en):
    """The order a unit's def-line segments RENDER in: a **leading** compare-collapse moves to
    the end, and nothing else moves (Robin, 2026-08-12).

    The collapse points back at English the sense has already printed, so opening with it
    gives the reader a pointer to something not yet said — `gjenstand` def 4 printed "compare
    *emne (I, 3)*" above "topic, subject matter". Six units are in that position, all of them
    arrivals of the 2026-08-12 A16 containment sweep, where the repeating reference is
    sometimes the sense's first line.

    **Only a leading one moves.** A collapse sitting mid-list is already after the prose it
    refers to, and the segments behind it are trailing tags the source puts last — a Latin
    taxon (`brunbjørn`: prose, collapse, `{Ursus arctos}`), an abbreviation note, an "as
    distinct from" gloss. Sorting every collapse to the end would push it past those and
    invent a worse order than the one ordbokene gives, in twelve units that read correctly
    today.

    **It applies to a source `jamfør` line too, and that is a deliberate Core Idea 6
    divergence** (four of the six: `han`/`hun`/`det` def 2/6/3 and `min` def 2, where
    ordbokene itself opens the sense with `jamfør` and puts the grammatical tag second). The
    rendered shape is identical either way — the reader cannot tell our collapse from the
    source's own cross-reference line — so keying the rule on provenance would give one
    visible shape two behaviours for a reason no reader can see.

    This is a **rendering** rule, not a data one: `no` and `en` stay index-paired in the row,
    the Norwegian keeps ordbokene's order on disk, and `_def_line` applies the same order to
    both sides so the preview's two columns stay aligned. Reordering the stored segments
    instead would break that pairing and be undone by the next derive."""
    idx = list(range(len(en or [])))
    if not idx or not is_collapse_segment(en[0]):
        return idx
    return sorted(idx, key=lambda i: 1 if is_collapse_segment(en[i]) else 0)


def _def_line(unit, side, mk, strict, drop_see_also=False):
    """A sense/sub def line, segments joined ``;<br>``: the authored **English** (``side='en'``;
    ``null`` renders a flag so a partially-authored live card is obvious) or the derived
    **Norwegian** source (``side='no'``, always present) for the preview's source column.

    ``drop_see_also`` (set only when inlining an expression into a parent's Fixed-expressions
    block) removes the ``Se: …`` see-also segment — keyed off the Norwegian face, so the parallel
    English segment drops with it (``docs/rendering.md`` § Fixed expressions)."""
    no = unit.get("no") or []
    en_all = unit.get("en")
    if side == "no":
        # The English decides the order (`collapse_order`), and the Norwegian follows it, so
        # the preview's source column stays opposite the segment it explains. Only where the
        # two sides are index-paired — an unauthored or mismatched unit keeps source order.
        order = (collapse_order(en_all)
                 if isinstance(en_all, list) and len(en_all) == len(no) else range(len(no)))
        segs = [no[i] for i in order if not (drop_see_also and mk.is_see_also(no[i]))]
        return ";<br>".join(mk.expand(s, norwegian=True, strict=strict) for s in segs)
    en = en_all
    if en is None:
        return '<span class="ordbok-flag">unauthored</span>'
    # en == [] is a stripped see-only unit (see-line deferral, 2026-07-14): empty by
    # construction, not unauthored
    pairs = list(zip(en, no)) if len(en) == len(no) else [(seg, "") for seg in en]
    pairs = [pairs[i] for i in collapse_order(en)]
    segs = [seg for seg, n in pairs if not (drop_see_also and mk.is_see_also(n))]
    if not segs:
        return ""
    return ";<br>".join(mk.expand(seg, norwegian=False, strict=strict) for seg in segs)


# The added-sentence marker (docs/proposals/example-sentences.md § Attribution rendering,
# adopted 2026-08-14): every `ex_added` sentence is visibly distinguishable from ordbokene's
# own — the deck presents itself as a translation of Bokmålsordboka, and an authored example
# falls outside that claim. A superscript `+` (addition, deliberately not `†`, which marks
# obsolete forms in lexicography), explained in its hover title; it becomes a link the day
# a credits surface exists to point at.
_ADDED_MARKER = ('<sup class="ordbok-added" title="Example added by this deck '
                 '(not from Bokmålsordboka)">+</sup>')


def _ex_no(no_html, expl_html=None):
    """The Norwegian face of one example: the QUOTE in italic, and where ordbokene
    attach an explanation, that upright after an en dash — their own site's
    treatment, which keeps the seam visible between what was said and the editors'
    gloss on it (Robin, 2026-08-16). The dash lives here, not in the row."""
    if not expl_html:
        return "<em>%s</em>" % no_html
    return '<em>%s</em> <span class="ordbok-exexpl">– %s</span>' % (no_html, expl_html)


def _ex_item(no_html, en_html, marker="", expl_html=None):
    """One example line: the derived Norwegian (italic), its English behind a reveal."""
    return ('<li>%s%s<label class="ordbok-reveal">'
            '<input type="checkbox" class="ordbok-toggle">'
            '<span class="ordbok-cue">Show translation</span>'
            '<span class="ordbok-tr">%s</span></label></li>'
            % (_ex_no(no_html, expl_html), marker, en_html))


def _ex_list(exs, mk, strict, side, added=None):
    """Examples. On the card (``side='en'``) each shows Norwegian with its English behind a
    reveal; in the source view (``side='no'``) the Norwegian shows plainly, no reveal.
    ``added`` carries the unit's ``ex_added`` sentences, rendered after the native run,
    each with the added-sentence marker."""
    if not exs and not added:
        return ""
    items = []
    for pair in (exs or []):
        no, en, expl = (list(pair) + [None, None, None])[:3]
        no_html = mk.expand(no or "", norwegian=True, strict=strict)
        expl_html = (mk.expand(expl, norwegian=True, strict=strict) if expl else None)
        if side == "no":
            items.append("<li>%s</li>" % _ex_no(no_html, expl_html))
        else:
            en_html = (mk.expand(en, norwegian=False, strict=strict) if en
                       else '<span class="ordbok-flag">unauthored</span>')
            items.append(_ex_item(no_html, en_html, expl_html=expl_html))
    for e in (added or []):
        no_html = mk.expand(e.get("no") or "", norwegian=True, strict=strict)
        if side == "no":
            items.append('<li><em>%s</em>%s</li>' % (no_html, _ADDED_MARKER))
        else:
            en = e.get("en")
            en_html = (mk.expand(en, norwegian=False, strict=strict) if en
                       else '<span class="ordbok-flag">unauthored</span>')
            items.append(_ex_item(no_html, en_html, marker=_ADDED_MARKER))
    return ('<ul class="ordbok-ex-list">\n          %s\n        </ul>'
            % "\n          ".join(items))


def _sub_inner(sub, mk, strict, side, drop_see_also=False):
    """The def line + optional set phrase + examples of one subsense, without a wrapper — so it can
    sit either in a bordered ``.ordbok-sub`` div or as a numbered ``<li>``."""
    out = ['          <span class="ordbok-def">%s</span>'
           % _def_line(sub, side, mk, strict, drop_see_also)]
    if side == "en" and sub.get("idiom"):
        out.append('          %s' % idiom(sub["idiom"]))
    el = _ex_list(sub.get("ex"), mk, strict, side, added=sub.get("ex_added"))
    if el:
        out.append('          ' + el)
    for blk in sub.get("comp") or []:
        out += [h for h in [_comp_html(blk, mk, strict, side)] if h]  # "" for an empty list (151)
    return out


def _sub_html(sub, mk, strict, side, drop_see_also=False):
    return "\n".join(['        <div class="ordbok-sub">']
                     + _sub_inner(sub, mk, strict, side, drop_see_also)
                     + ['        </div>'])


def _subs_html(subs, mk, strict, side, drop_see_also=False, numbered=False):
    """Render a sense's subsenses. **Numbered** (decimal, as ordbokene's pages number them) only
    when the parent is a *solo, unnumbered* top sense and the group has ≥2 members — the outermost
    definition group carries the numbers, so a lone top sense hands them to its subs
    (`docs/rendering.md`; verified against ordbokene seg/dette/vi). Otherwise the subs stay
    unnumbered bordered blocks (under a numbered top sense ordbokene uses disc bullets; a solo sub
    is never numbered)."""
    if not subs:
        return []
    if numbered and len(subs) >= 2:
        out = ['        <ol class="ordbok-senses ordbok-subsenses">']
        for sub in subs:
            out.append('          <li>')
            out += _sub_inner(sub, mk, strict, side, drop_see_also)
            out.append('          </li>')
        out.append('        </ol>')
        return out
    return [_sub_html(sub, mk, strict, side, drop_see_also) for sub in subs]


def _comp_html(comp, mk, strict, side):
    """A ``comp`` block: the label + its compound links. On the card (``side='en'``) each item
    is a Norwegian-visible two-tier link from its ``{word, href, en}`` (``en`` the hover gloss,
    ``null`` → flag / raise); in the source view (``side='no'``) the compounds show as plain
    italic Norwegian. A list with no intro in the source has ``label`` ``""`` (site decisions
    151): it is drawn without a label line, and a list with neither label nor compounds not
    at all (*bo* 6739's two empty lists)."""
    label = html.escape(comp.get("label") or "", quote=False)
    parts = []
    for it in comp["items"]:
        if side == "no":
            parts.append("<em>%s</em>" % html.escape(it["word"], quote=False))
        elif it.get("en"):
            parts.append(mk.expand('[%s](%s "%s")' % (it["word"], it["href"], it["en"]),
                                   norwegian=True, strict=strict))
        else:
            parts.append(mk.expand('[%s](%s)' % (it["word"], it["href"]),
                                   norwegian=True, strict=strict))  # untitled -> flag / raise
    if not label and not parts:
        return ""
    line = ("<em>%s</em> %s" % (label, ", ".join(parts))) if label else ", ".join(parts)
    return ('        <div class="ordbok-sub">\n'
            '          <span class="ordbok-def">%s</span>\n'
            '        </div>' % line)


def _sense_body(s, mk, strict, side, number_subs=False):
    """The inner HTML of one sense: def line, set phrase, examples, subs, then the sense's own
    compound lists (``comp`` is per-sense — ordbokene attaches each list to the sense it sits
    under; ``schemas.md`` § comp). ``number_subs`` is set only for a *solo* top sense, whose
    subs then carry the decimal numbering (``_subs_html``)."""
    out = ['        <span class="ordbok-def">%s</span>' % _def_line(s, side, mk, strict)]
    if side == "en" and s.get("idiom"):
        out.append('        %s' % idiom(s["idiom"]))
    el = _ex_list(s.get("ex"), mk, strict, side, added=s.get("ex_added"))
    if el:
        out.append('        ' + el)
    out += _subs_html(s.get("subs", []), mk, strict, side, numbered=number_subs)
    for blk in s.get("comp") or []:
        out += [h for h in [_comp_html(blk, mk, strict, side)] if h]  # "" for an empty list (151)
    return out


def _ety_join(parts):
    """Etymology segments joined **positionally, as ordbokene's articles show them**: ``, ``
    between items, ``; `` before the last (og: "norrønt ok, kanskje, beslektet med øke; uttale
    å"), as on the rendered og, være III and øke articles. The separators are presentation, so
    they are added here at render time and the stored segments stay separator-free (Fable
    review, 2026-07-13; replaces the uniform `; ` join that mis-rendered og)."""
    if not parts:
        return ""
    out = parts[0]
    for i, p in enumerate(parts[1:], 2):
        out += ("; " if i == len(parts) else ", ") + p
    return out


def _ety_html(ety, side, mk, strict):
    """Etymology segments (one per source node), inline prose, joined per ``_ety_join``.
    Authored English (``side='en'``) or derived Norwegian (``side='no'``)."""
    if side == "no":
        return _ety_join([mk.expand(s, norwegian=True, strict=strict) for s in (ety.get("no") or [])])
    en = ety.get("en")
    if not en:
        return '<span class="ordbok-flag">unauthored</span>'
    return _ety_join([mk.expand(seg, norwegian=False, strict=strict) for seg in en])


def _expr_html(erow, mk, strict, side):
    """One expression sub-article **inlined** from its own library row: the bold Norwegian term,
    then its senses, each with set phrase / examples / subsenses. This is the embedded view, so the
    ``Se: …`` see-also line is dropped (``drop_see_also=True``) — ordbokene shows it only on the
    expression's own article page, not when integrated into a parent (``docs/rendering.md``)."""
    term = html.escape((erow.get("lemmas") or [{}])[0].get("form", ""), quote=False)
    out = ['    <div class="ordbok-expr">',
           '      <span class="ordbok-expr-term">%s</span>' % term]
    senses = erow.get("senses") or []
    multi = len(senses) > 1
    if multi:
        out.append('      <ol class="ordbok-expr-senses">')
    for s in senses:
        if multi:
            out.append('        <li>')
        out.append('        <span class="ordbok-def">%s</span>'
                   % _def_line(s, side, mk, strict, drop_see_also=True))
        if side == "en" and s.get("idiom"):
            out.append('        %s' % idiom(s["idiom"]))
        el = _ex_list(s.get("ex"), mk, strict, side, added=s.get("ex_added"))
        if el:
            out.append('        ' + el)
        out += _subs_html(s.get("subs", []), mk, strict, side, drop_see_also=True,
                          numbered=not multi)
        for blk in s.get("comp") or []:
            out += [h for h in [_comp_html(blk, mk, strict, side)] if h]  # "" for an empty list (151)
        if multi:
            out.append('        </li>')
    if multi:
        out.append('      </ol>')
    out.append('    </div>')
    return "\n".join(out)


_NO_LAST = {"æ": "", "ø": "", "å": ""}  # sort after z, in Norwegian order
_ACCENT = {"é": "e", "è": "e", "ê": "e", "á": "a", "à": "a", "â": "a", "ó": "o", "ò": "o", "ô": "o"}


def expr_sort_key(form):
    """Norwegian collation key for the Fixed-expressions list: a–z then **æ ø å**, folding common
    accents (`é`→`e`) to their base — so embedded expressions list alphabetically as ordbokene
    shows them (`alt i ett`, `bli nummer én`, … `et og annet`, `ett å gjøre`, …), not in the
    stored `exprs` (source) order."""
    return "".join(_NO_LAST.get(c, _ACCENT.get(c, c)) for c in (form or "").lower())


def _expr_order(expr_ids, lib):
    """`exprs` ids sorted by their row's lemma form (alphabetical, ordbokene's ordering); a
    missing row keeps its id but sorts last so the flag still renders."""
    def key(eid):
        erow = lib.get(eid)
        form = (erow.get("lemmas") or [{}])[0].get("form", "") if erow else ""
        return (erow is None, expr_sort_key(form))
    return sorted(expr_ids, key=key)


# ordbokene registers words it has not yet defined: `alarmklokke`, `steinhelle` and a handful
# more give a headword and an inflection table, and where the article would be, this note.
# Our own wording, written blind (code provenance decisions 2 and 7, 2026-11-02: a fresh agent
# given only the note's purpose offered three lines; the third was picked, with "currently" added).
# Shared by the card, the mini and the A8 cited block, so all three say one thing.
NO_DEFINITION_NOTE = "This word is currently listed without a definition."


# --- the card ---------------------------------------------------------------

def render_card(row, library, salt=None, strict=True, side="en"):
    """A library ``row`` -> one self-contained card HTML string. ``library`` (id -> row, or a
    list) resolves cross-reference minis and inlined expression rows; ``salt`` (the card freq)
    salts reveal ids for byte-stable rebuilds; ``strict`` raises on a broken cross-reference (a
    live build) vs. flags it (the preview). ``side='en'`` is the card (authored English);
    ``side='no'`` renders the **derived-Norwegian source view** in the same layout — for the
    preview's source column (no reveals, no set-phrase lines)."""
    import markup as mk  # lazy: markup imports this module, so bind it at call time
    mk.set_library(library)
    mk.set_card(row["id"] if salt is None else salt)
    lib = library if isinstance(library, dict) else {r["id"]: r for r in library}
    row = mk.pair_view(row, side)  # complete every reference pair for this side (render-time)

    p = ['<div class="ordbok" lang="%s">' % ("no" if side == "no" else "en"),
         '  <div class="ordbok-head">',
         '    %s' % _head_lemmas(row),
         '    <span class="ordbok-pos">%s</span>' % html.escape(row.get("pos_en", ""), quote=False),
         '  </div>']

    ety = row.get("etymology") or {}
    if ety.get("no"):
        p += ['', '  <section class="ordbok-sec ordbok-inline">', '    <h3>Etymology</h3>',
              '    <span class="ordbok-body">%s</span>' % _ety_html(ety, side, mk, strict),
              '  </section>']

    # comp is per-sense now (rendered inside _sense_body / _sub_inner); every compound list in
    # the pinned universe sits under a gloss-bearing sense, so "Meaning and use" is gated on
    # senses alone.
    if row.get("senses"):
        p += ['', '  <section class="ordbok-sec">', '    <h3>Meaning and use</h3>']
        senses = row.get("senses")
        if len(senses) > 1:
            p.append('    <ol class="ordbok-senses">')
            for s in senses:
                p.append('      <li>')
                p += _sense_body(s, mk, strict, side)
                p.append('      </li>')
            p.append('    </ol>')
        else:
            # A solo top sense is rendered flush, unnumbered (ordbokene drops the number when a
            # sense stands alone); its own subs may become the numbered level (`_subs_html`).
            p += _sense_body(senses[0], mk, strict, side, number_subs=True)
        p.append('  </section>')
    elif not row.get("exprs"):
        # ordbokene registers words it has not yet defined — a headword, a paradigm, and in
        # place of the article a note. Rendering nothing left a card body that looked broken
        # (Robin, 2026-07-29), so the card says so too, in our own words (`NO_DEFINITION_NOTE`
        # above). A senseless article that heads expressions is NOT this case — its
        # content is the expression rows below.
        p += ['', '  <section class="ordbok-sec ordbok-inline">',
              '    <span class="ordbok-body ordbok-nodef">%s</span>' % NO_DEFINITION_NOTE,
              '  </section>']

    if row.get("exprs"):
        p += ['', '  <section class="ordbok-sec">', '    <h3>Fixed expressions</h3>']
        for eid in _expr_order(row["exprs"], lib):
            erow = lib.get(eid)
            if erow is None:
                if strict:
                    raise mk.MarkupError("expression row %s missing from the library" % eid)
                p.append('    <div class="ordbok-expr"><span class="ordbok-flag">'
                         'expression %s missing</span></div>' % eid)
            else:
                p.append(_expr_html(mk.pair_view(erow, side), mk, strict, side))
        p.append('  </section>')

    p.append('</div>')
    body = "\n".join(p)
    style = STYLE_FULL if 'class="ordbok-xref"' in body else STYLE
    return body + "\n" + style


# --- CSS --------------------------------------------------------------------

_CARD_CSS = r'''
.ordbok{font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;text-align:left;line-height:1.5;color:#222;max-width:40em;margin:0 auto}
.ordbok-head{margin-bottom:.7em}
.ordbok-lemma{font-size:1.9em;font-weight:700;color:#560027}
.ordbok-homograph{font-weight:600;color:#757070;vertical-align:.14em;font-size:.6em}
.ordbok-head .ordbok-homograph{font-size:calc(.6*1.9em)}
.ordbok-pos{display:block;font-size:.8em;font-variant:all-small-caps;letter-spacing:.08em;color:#757070}
.ordbok-sec{margin:.9em 0}
.ordbok-sec h3{display:block;font-size:1em;font-weight:700;font-variant:all-small-caps;letter-spacing:.06em;color:#560027;margin:0 0 .15em}
.ordbok-inline h3{display:inline;margin-right:.4em}
.ordbok-inline .ordbok-body{display:inline}
.ordbok em{font-style:italic}
.ordbok-exexpl{font-style:normal}
.ordbok-exexpl em{font-style:italic}
.ordbok a{color:#560027}
.ordbok-senses{margin:0;padding-left:1.5em;list-style:decimal}
.ordbok-senses>li{margin-bottom:.7em;padding-left:.2em}
.ordbok-senses>li::marker{font-weight:700;color:#560027}
.ordbok-subsenses{margin-top:.4em}
.ordbok-subsenses>li{margin-bottom:.4em}
.ordbok-def{margin:0}
.ordbok-sub{margin:.3em 0 .2em 1em;padding-left:.6em;border-left:2px solid #e0d8d9}
.ordbok-ex-label{font-size:1em;font-weight:700;color:#560027;margin:.35em 0 .1em 1.2em}
.ordbok-ex-list{list-style:none;margin:0 0 0 1.2em;padding-left:0}
.ordbok-ex-list>li{margin:.3em 0}
.ordbok-reveal{display:block;cursor:pointer}
.ordbok-toggle{position:absolute;opacity:0;width:0;height:0}
.ordbok-cue{display:inline-block;font-size:.8em;color:#757070;border:1px solid #c4bcbd;border-radius:.5em;padding:.05em .55em;margin-top:.15em;user-select:none}
.ordbok-tr{display:none;color:#757070;font-style:normal;font-size:.95em}
.ordbok-toggle:checked~.ordbok-cue{display:none}
.ordbok-toggle:checked~.ordbok-tr{display:block}
.ordbok-expr{margin:.6em 0}
.ordbok-expr-term{display:block;font-weight:700;color:#560027;margin-bottom:.1em}
.ordbok-expr .ordbok-def{margin-bottom:.15em}
.ordbok-expr-senses{margin:.2em 0 0;padding-left:1.4em;list-style:decimal}
.ordbok-expr-senses>li{margin-bottom:.4em}
.ordbok-expr-senses>li::marker{font-weight:700;color:#560027}
.ordbok-idiom{display:block;margin-top:.2em;font-size:.9em;color:#757070}
.ordbok-idiom-tag{display:inline-block;font-size:.72em;font-variant:all-small-caps;letter-spacing:.04em;background:#f3e9ed;color:#560027;border-radius:.5em;padding:.02em .5em;margin-right:.45em;vertical-align:.08em}
.ordbok-idiom-eng{font-style:normal;color:#560027}
.ordbok-added{vertical-align:super;font-size:.7em;color:#757070;font-style:normal;cursor:help;margin-left:.1em}
.ordbok-flag{color:#a30012;background:#fbe3e6;border-radius:.3em;padding:0 .3em;font-size:.85em;font-weight:600}
.ordbok-nodef{color:#757070;font-style:italic}
.nightMode .ordbok{color:#d9d6d6}
.nightMode .ordbok-lemma,.nightMode .ordbok-sec h3,.nightMode .ordbok-ex-label,.nightMode .ordbok-expr-term{color:#fdf4f5}
.nightMode .ordbok-pos,.nightMode .ordbok-tr,.nightMode .ordbok-nodef,.nightMode .ordbok-added{color:#b9b6b6}
.nightMode .ordbok-homograph{color:#b9b6b6}
.nightMode .ordbok-cue{color:#b9b6b6;border-color:#656161}
.nightMode .ordbok-senses>li::marker,.nightMode .ordbok-expr-senses>li::marker{color:#b9b6b6}
.nightMode .ordbok-sub{border-color:#656161}
.nightMode .ordbok a{color:#e3b7c9}
.nightMode .ordbok-idiom{color:#b9b6b6}
.nightMode .ordbok-idiom-tag{background:#4a2e37;color:#e3b7c9}
.nightMode .ordbok-idiom-eng{color:#e3b7c9}
.nightMode .ordbok-flag{color:#ffb4bd;background:#4a2226}
/* The headword links to its own ordbokene.no article. It keeps the heading's colour, not the
   cross-reference link colour — hence `inherit`, and hence these rules sit last: `.nightMode
   .ordbok a` has equal specificity and would otherwise repaint the lemma. Underline on hover
   only, so the heading still reads as a heading. */
.ordbok-lemma a,.nightMode .ordbok-lemma a{color:inherit;text-decoration:none}
.ordbok-lemma a:hover,.ordbok-lemma a:focus{text-decoration:underline}
'''

# Cross-reference two-tier control. The inline word is a <label>; hover shows a one-line peek
# of the counterpart language, a click opens the mini-article. Pure CSS: the checkbox is the
# first child of `.ordbok-xref`, so a `~` combinator uncovers the peek/backdrop/mini that
# follow it (no `:has()`, so it works in any Anki client). The hover peek uses the **child**
# combinator (`.ordbok-xref:hover > .ordbok-xpeek`) so an open mini's own hover-only peeks do
# not leak into the outer control. `@media (hover: none)` reprints the peek inline as a static
# `‘gloss’` so touch users lose nothing (the click tier is unchanged on touch).
_XREF_CSS = r'''
.ordbok-xref{position:relative;display:inline}
.ordbok-xtog{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.ordbok-xword{cursor:pointer;color:#560027;border-bottom:1px dotted #b98ba1;text-decoration:none}
.ordbok-xword:hover{background:rgba(86,0,39,.06);border-radius:.15em}
.ordbok-xtog:checked~.ordbok-xword{background:rgba(86,0,39,.1);border-radius:.15em}
.ordbok-xpeek{display:none;position:absolute;left:0;bottom:1.6em;z-index:60;font-style:normal;font-weight:600;
  white-space:nowrap;background:#560027;color:#fff;font-size:.8em;padding:.15em .5em;border-radius:.4em;
  box-shadow:0 4px 14px rgba(60,20,40,.3)}
.ordbok-xpeek::after{content:"";position:absolute;left:1em;top:100%;border:5px solid transparent;border-top-color:#560027}
.ordbok-xref:hover>.ordbok-xpeek{display:block}
.ordbok-xtog:checked~.ordbok-xpeek{display:none}
.ordbok-xback{display:none;position:fixed;inset:0;z-index:65;background:transparent;cursor:default}
.ordbok-xtog:checked~.ordbok-xback{display:block}
.ordbok-xmini{display:none;position:absolute;left:0;top:1.7em;z-index:70;font-style:normal;font-weight:400;white-space:normal}
.ordbok-xtog:checked~.ordbok-xmini{display:block}
.nightMode .ordbok-xword{color:#e3b7c9;border-bottom-color:#7a5566}
.nightMode .ordbok-xword:hover,.nightMode .ordbok-xtog:checked~.ordbok-xword{background:rgba(227,183,201,.14)}
.nightMode .ordbok-xpeek{background:#e3b7c9;color:#241318}
.nightMode .ordbok-xpeek::after{border-top-color:#e3b7c9}
@media (hover:none){
  /* Touch, on the article surface: no peek (Robin, 2026-09-29: the inline gloss looked "ugly";
     the tap's mini and the line's "Show Norwegian" reveal carry the counterpart). The :hover
     selector is listed too, since a tap leaves a sticky :hover on some phones. */
  .ordbok-xpeek,.ordbok-xref:hover>.ordbok-xpeek{display:none}
  /* Inside a mini the links are hover-only, with no reveal and no further mini, so there the
     peek stays, printed inline as a static gloss after the word. */
  .mini .ordbok-xpeek,.mini .ordbok-xref:hover>.ordbok-xpeek{display:inline;position:static;
    z-index:auto;white-space:normal;background:none;color:#757070;
    box-shadow:none;font-weight:400;font-size:.85em;padding:0 0 0 .3em}
  .mini .ordbok-xpeek::before{content:"\2018"}
  .mini .ordbok-xpeek::after{content:"\2019";position:static;border:none}
  .nightMode .mini .ordbok-xpeek{color:#b9b6b6}
}
'''

# Base card CSS, and the full sheet that also carries the cross-reference control + mini-
# article styles. A card needs the full sheet only when it contains a two-tier control, so
# `render_card` picks per card.
STYLE = "<style>" + _CARD_CSS + "</style>"
STYLE_FULL = "<style>" + _CARD_CSS + _XREF_CSS + mini.STYLE + "</style>"
