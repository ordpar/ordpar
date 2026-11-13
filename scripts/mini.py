#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a library row into its cross-reference *mini-article* HTML.

A cross-reference's **click / tap** tier shows the referenced article's mini-article: the
canonical, lemma-headed row — never the citation's inflected form (that lives on the hover
tier). It is one of the two views over a row (``docs/rendering.md`` § The two views):

    header   lemma (homograph, sense№) — gloss     (sense№ only for a #defN citation;
                                                     gloss = the citing link's English;
                                                     the lemma is the ordbokene link)
    body     the row's senses, **en only** (the mini never shows the Norwegian sense text),
             segments joined ``;<br>``; each rendered unit shows at least its first
             example, with extras allocated within ``EX_BUDGET`` for **authored** English
             (``_allocate_examples``); a sense's subs render **iff authored** (opt-in).

A ``#defN`` citation shows **only** the anchored sense (plus its opt-in subs); a bare href
shows all senses — with a sense's authored subs only when the article is **single-sense**
or the sense is an **empty container** (the card-80 scope rule, mirroring
``stint._role_units``; other multi-sense bare minis keep their senses bare even when the
target's subs are authored as another card's seed). A row
with **no senses of its own** (a DEF-less article like ``si II``) renders its expression rows
— with their subsenses and examples — instead of an empty box; with no expressions either it
is a word ordbokene has **not defined**, and renders a note saying so
(``ordbok_gen.NO_DEFINITION_NOTE``, our own wording) rather than a header over nothing. A ``comp`` line renders under a unit that would
otherwise be **bare** — no example of any kind (Robin, 2026-08-16: armed where the gloss exists, plain where not, see
``_comp_line``; comp was omitted entirely until then), while **etymology is omitted
except on a senseless row** (Robin, 2026-07-29), where there
are no senses for it to compete with and it is often the closest thing to an explanation the
article carries; an authored ``idiom`` line renders after its unit's English, exactly as on the
card (Robin, 2026-07-13 — restoring the two-views table in ``docs/revamp.md`` § 4, which
omits only etymology and ``comp``; the "idiom omitted" line was doc-split drift). Links inside a mini are **hover-only** (the caller passes an
``xexpand`` bound to ``hover_only=True``); a mini never opens a further mini, which is what
keeps the closure finite (``docs/library.md`` § The closure).

``render(…, side='no')`` is the same mini with its **Norwegian** face — the derived ``no``
lines instead of the authored English, for the public dictionary site's cross-references to
articles it has no translation for (`ordpar/`, site decisions 34); ``side='both'`` carries
both faces as line pairs, for the site's translated targets (decisions 54). Additive: the deck
never passes either and every default is what it was.

This is the one place mini-article markup lives, so the authoring preview and the card build
render byte-identical minis. The reveal is a pure-CSS checkbox (no JavaScript), so it renders
identically in the preview and inside every Anki client.
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ordbok_gen  # noqa: E402  -- expr_sort_key (shared Norwegian collation for the expr list)

BASE = "https://ordbokene.no"


def _display_num(row, defn):
    """The displayed sense number a ``#defN`` anchor resolves to: a top sense's stored
    ``ordinal``, or — since subs carry no ordinal — a subsense's **1-based position among its
    parent's subs** (subs are held in document order, so position == the number ordbokene shows,
    matching the citing marker's ``definition_order``; ``holde på`` sub 4 sits at position 2, so
    ``holde på (2)``)."""
    for s in row.get("senses", []):
        if s.get("defn") == defn:
            return s.get("ordinal")
        for i, u in enumerate(s.get("subs", []), 1):
            if u.get("defn") == defn:
                return i
    return None


def _anchored_defn(row, defn):
    """Resolve a ``#defN`` to ``('sense', s)`` or ``('sub', parent, sub)`` or ``None``."""
    for s in row.get("senses", []):
        if s.get("defn") == defn:
            return ("sense", s)
        for u in s.get("subs", []):
            if u.get("defn") == defn:
                return ("sub", s, u)
    return None


def _suffix(row, defn):
    """`(homograph, sense№)` for the header, absent parts omitted — the same face the citing
    marker shows (``ha (II, 13)``, ``holde på (2)``)."""
    lem = (row.get("lemmas") or [{}])[0]
    parts = []
    if lem.get("homograph"):
        parts.append(lem["homograph"])
    if defn is not None:
        num = _display_num(row, defn)
        if num is not None:
            parts.append(str(num))
    return " (%s)" % ", ".join(parts) if parts else ""


def _en_line(en, xexpand, no=None, side="en"):
    """A sense's authored English, segments joined ``;<br>``. ``null`` (unauthored) shows a
    flag so a partially-authored target is obvious in the preview; ``[]`` is a stripped
    see-only unit (see-line deferral, 2026-07-14) — empty by construction, renders nothing.

    ``side='no'`` renders the unit's **derived Norwegian** (``no``) instead — the Norwegian
    face of a mini, for a target the public site has no translation for (the dictionary
    site's build, `ordpar/`); the deck never passes it and its output is unchanged.

    ``side='both'`` renders the two as one **line pair** — the Norwegian line, then the
    English, each language-tagged (``_pair``) — for the site's mini of a translated target,
    whose stylesheet picks what shows (site decisions 54). A unit with no English renders
    nothing, as on the English face; one with no Norwegian line renders its English alone."""
    if side == "both":
        en_html = _en_line(en, xexpand, no, "en")
        return _pair(_en_line(en, xexpand, no, "no") if no else "", en_html) if en_html else ""
    if side == "no":
        segs = no or []
        # the English still decides the order where the two sides are index-paired, exactly
        # as `ordbok_gen._def_line(side='no')` does, so both views read alike
        order = (ordbok_gen.collapse_order(en)
                 if isinstance(en, list) and len(en) == len(segs) else range(len(segs)))
        return ";<br>".join(xexpand(segs[i], norwegian=True) for i in order)
    if en is None:
        return '<span class="ordbok-flag">unauthored</span>'
    # Same segment order as the card (`ordbok_gen.collapse_order`): a compare-collapse reads
    # as a trailing pointer, and a mini is a view over the same row.
    order = ordbok_gen.collapse_order(en)
    return ";<br>".join(xexpand(en[i], norwegian=False) for i in order)


def _pair(no_html, en_html):
    """``side='both'``: a Norwegian line over its English, in one wrapper the site's sheet
    styles (``.mini-pair``); either half alone is returned as it is."""
    if not (no_html and en_html):
        return en_html or no_html
    return ('<span class="mini-pair"><span lang="nb">%s</span><span lang="en">%s</span></span>'
            % (no_html, en_html))


def _idiom_line(unit, side="en"):
    """An authored ``idiom`` slot, rendered with the card's own markup (one owner,
    ``ordbok_gen.idiom``) right after the unit's English line; empty when null — and on a
    Norwegian-faced mini (``side='no'``), where the slot's English has no place."""
    return ordbok_gen.idiom(unit["idiom"]) if unit.get("idiom") and side != "no" else ""


def _comp_line(unit, xexpand):
    """The unit's compound lists — but **only when the unit would otherwise render bare**
    (Robin, 2026-08-16: the spec said `comp` omitted until then, *gang* 4 rendered as the
    bare gloss "a narrow passage or path" with nothing behind it, and his own refinement
    minutes later was that a comp block on every sense of an article like *gang* is
    clutter). Bare means **no example of any kind** — native or added — since the mini's
    floor renders one for any unit that has one. That is **358 senses**, where the comp
    block is the only usage display the sense has.

    **Armed where the gloss exists, plain where it does not** (Robin, 2026-08-16 — his
    amendment the same day: "for the comp-blocks that have received authored glosses, the
    mini should render them likewise"). An item with an authored `en` renders as the
    card's two-tier link, the gloss in its hover title; an item without one renders as a
    plain word. **This creates no authoring obligation**, which is the whole point of the
    split: rendering a gloss that exists is free, while arming the unauthored ones would
    open 235 slots across 85 articles at a stroke (reachable ⟹ authored, guardrail 2).
    Of those 235, work already queued covers all but **78 across 32 articles** — 118
    arrive armed when their article is carded, and 56 sit on units that chain tiers 1–3
    will hand a sentence, after which the unit is no longer bare and this line stops
    rendering at all. The plain form is the source view's own treatment
    (`ordbok_gen._comp_html(side='no')`) and carries the attestation, which is the point."""
    if _unit_examples(unit):
        return ""
    out = []
    for b in unit.get("comp") or []:
        parts = []
        for i in b.get("items") or []:
            if i.get("en") and i.get("href"):
                parts.append(xexpand('[%s](%s "%s")' % (i["word"], i["href"], i["en"]),
                                     norwegian=True))
            else:
                parts.append(html.escape(i["word"], quote=False))
        if not parts:
            continue
        label = b.get("label") or ""   # no intro in the source: no label line (decisions 151)
        out.append('<div class="mini-comp">%s%s</div>'
                   % (("<em>%s</em> " % html.escape(label, quote=False)) if label else "",
                      ", ".join(parts)))
    return "".join(out)


EX_BUDGET = 6

# The added-sentence marker, mini variant — same convention as the card's
# (`ordbok_gen._ADDED_MARKER`): an `ex_added` sentence is visibly not ordbokene's own.
_ADDED_MARKER = ('<sup class="mini-added" title="Example added by this deck '
                 '(not from Bokmålsordboka)">+</sup>')


def _unit_examples(u):
    """The unit's rendered example sequence, as ``(no, en, added)`` triples: native ``ex``
    pairs first, then ``ex_added`` sentences — which count toward the ≥1 floor and the
    ``EX_BUDGET`` like native ones (decision 5, `docs/proposals/example-sentences.md`)."""
    out = [(p[0], p[1], False, p[2] if len(p) > 2 else None)
           for p in (u.get("ex") or [])]
    out += [(e.get("no"), e.get("en"), True, None) for e in (u.get("ex_added") or [])]
    return out


def _allocate_examples(units):
    """How many examples each rendered unit shows (Robin, 2026-07-13). The **floor** is one
    example per unit (always rendered, exactly the old rule — never starved by the budget:
    every unit that carries any example gets at least one, even when the floor sum exceeds
    ``EX_BUDGET``, so a >6-example-sense article shows one per sense uncapped). **Extras**
    are granted round-robin (everyone's 2nd, then everyone's 3rd, …) while the mini's total
    stays within ``EX_BUDGET`` — and only for examples whose English is **authored** (opt-in
    by authoring, like the anchored-sub context rule: legacy cards show nothing new until
    backfilled; stint-authored cards are richer automatically). So: one anchored sub → up to
    6 examples; three units → two each; seven+ units → floor only. Returns a list of per-unit
    counts aligned with ``units``. Counts run over the combined native+added sequence
    (``_unit_examples``)."""
    counts = [1 if _unit_examples(u) else 0 for u in units]
    total = sum(counts)
    rank = 1
    while total < EX_BUDGET:
        granted = False
        for i, u in enumerate(units):
            ex = _unit_examples(u)
            if len(ex) > rank and counts[i] == rank and ex[rank][1] is not None and total < EX_BUDGET:
                counts[i] += 1
                total += 1
                granted = True
        if not granted:
            break
        rank += 1
    return counts


def _example_html(ex, xexpand, side="en"):
    """One example: derived Norwegian (italic) over its authored English (muted). ``ex`` is
    a ``(no, en)`` pair or a ``(no, en, added[, explanation])`` tuple — an added sentence
    carries the added-sentence marker after its Norwegian, and ordbokene's own explanation
    renders UPRIGHT after an en dash, as on their site (Robin, 2026-08-16).

    ``side='no'`` (the site's Norwegian-faced mini) shows the Norwegian alone."""
    no, en, added, expl = (list(ex) + [None, None, False, None])[:4]
    if side == "no":
        en = None
    body = xexpand(no or "", norwegian=True)
    if expl:
        # `.mini-exno` is italic by CSS, so the explanation opts back out
        body += ('<span class="mini-exexpl">– %s</span>'
                 % xexpand(expl, norwegian=True))
    rows = ['<div class="mini-exno">%s%s</div>'
            % (body, _ADDED_MARKER if added else "")]
    if en:
        rows.append('<div class="mini-exen">%s</div>' % xexpand(en, norwegian=False))
    return '<div class="mini-ex2">%s</div>' % "".join(rows)


def _shown_subs(sense, side="en"):
    """The subs a mini renders under a sense: **only those whose `en` is authored** — context
    is opt-in by authoring (Robin, 2026-07-13). The stint work model authors a `#defN`-cited
    sense's subs, so new cards show them; legacy cards change nothing until backfilled.

    On a Norwegian-faced mini (``side='no'``, the site's untranslated target) there is no
    authored English to opt in with, so the same test reads the face that IS the content:
    a sub renders when its ``no`` carries text. Without that a container sense — whose
    meaning lives entirely in its subs — would render as a blank line."""
    if side == "no":
        return [u for u in sense.get("subs", []) if u.get("no")]
    return [u for u in sense.get("subs", []) if u.get("en")]


def _ex_run(unit, n, xexpand, side="en"):
    return "".join(_example_html(e, xexpand, side) for e in _unit_examples(unit)[:n])


def _sense_blocks(senses, xexpand, bare=False, side="en"):
    """The senses, each with its opt-in authored subs, examples allocated per
    ``_allocate_examples`` (floor of one per unit, extras within ``EX_BUDGET``).
    ``bare=True`` is the bare-href path, where the card-80 scope rule applies: a sense
    carries its subs only when the article is single-sense or the sense is an empty
    container (no own ``no``) — a multi-sense bare mini stays compact even when the
    target's subs happen to be authored (e.g. as another card's seed). An anchored
    ``#defN`` sense (``bare=False``) always carries its authored subs."""
    single = len(senses) == 1

    def subs(s):
        return _shown_subs(s, side) if (not bare or single or not s.get("no")) else []

    order = []
    for s in senses:
        order.append(s)
        order.extend(subs(s))
    counts = dict(zip((id(u) for u in order), _allocate_examples(order)))
    numbered = len(senses) > 1
    parts = []
    for i, s in enumerate(senses, 1):
        ex_html = _ex_run(s, counts[id(s)], xexpand, side)
        gloss = _en_line(s.get("en"), xexpand, s.get("no"), side)
        subs_html = "".join(_sub_html(u, counts[id(u)], xexpand, side) for u in subs(s))
        if numbered:
            head = ('<div class="mini-sline"><span class="mini-snum">%d</span>'
                    '<span>%s</span></div>' % (i, gloss))
            parts.append('<div class="mini-sense2">%s%s%s%s</div>'
                         % (head, _idiom_line(s, side) + _comp_line(s, xexpand), ex_html, subs_html))
        else:
            # A unit ordbokene defines by example alone has no definition line at all
            # (`aldersforskjell`); an empty `mini-single` would open the popup with a blank
            # row above the example.
            line = '<div class="mini-single">%s</div>' % gloss if gloss else ""
            parts.append('<div class="mini-sense2 mini-solo">%s%s%s%s</div>'
                         % (line, _idiom_line(s, side) + _comp_line(s, xexpand), ex_html, subs_html))
    return "".join(parts)


def _sub_html(sub, n, xexpand, side="en"):
    """One subsense: its authored English over its example run, indented under a sense."""
    return ('<div class="mini-sub"><div class="mini-single">%s</div>%s%s</div>'
            % (_en_line(sub.get("en"), xexpand, sub.get("no"), side),
               _idiom_line(sub, side) + _comp_line(sub, xexpand),
               _ex_run(sub, n, xexpand, side)))


def _anchored_sub_block(parent, defn, xexpand, side="en"):
    """A ``#defN`` that targets a **subsense**: the anchored sub is always shown; the parent
    sense's own line and any sibling subs appear **only when their `en` is authored** — context
    is opt-in by authoring (Robin, 2026-07-13), so a self-contained sub (``holde på (2)``) shows
    alone, while a sub that needs its parent gets it the moment the parent is authored. When the
    anchored sub is the *only* content it renders **flush**, like a solo sense drops its number —
    the indent (`.mini-sub`) only reads as nesting when there is a parent/sibling to nest under.
    Examples follow the same budget allocation as everywhere else."""
    key = "no" if side == "no" else "en"   # the face that carries the content (see `_shown_subs`)
    subs = [s for s in parent.get("subs", []) if s.get("defn") == defn or s.get(key)]
    show_parent = bool(parent.get(key))
    order = ([parent] if show_parent else []) + subs
    counts = dict(zip((id(u) for u in order), _allocate_examples(order)))
    if not show_parent and len(subs) == 1:
        sub = subs[0]
        return ('<div class="mini-sense2 mini-solo"><div class="mini-single">%s</div>%s%s</div>'
                % (_en_line(sub.get("en"), xexpand, sub.get("no"), side),
                   _idiom_line(sub, side) + _comp_line(sub, xexpand),
                   _ex_run(sub, counts[id(sub)], xexpand, side)))
    parts = []
    if show_parent:
        parts.append('<div class="mini-single">%s</div>'
                     % _en_line(parent["en"], xexpand, parent.get("no"), side))
        parts.append(_idiom_line(parent, side))
        parts.append(_ex_run(parent, counts[id(parent)], xexpand, side))
    for sub in subs:
        parts.append(_sub_html(sub, counts[id(sub)], xexpand, side))
    return '<div class="mini-sense2 mini-solo">%s</div>' % "".join(parts)


def _ety_block(row, xexpand, side="en"):
    """A senseless row's etymology, English only — the mini's one etymology, and empty markup
    when the row has none or it is unauthored (guardrail 2 owns the obligation). ``side='no'``
    renders the derived Norwegian instead, the one face that page has; ``side='both'`` the
    two as a line pair (``_pair``)."""
    ety = row.get("etymology") or {}
    if side == "both":
        def join(key, norwegian):
            return ";<br>".join(xexpand(seg, norwegian=norwegian)
                                for seg in (ety.get(key) or []) if seg)
        en_html = join("en", False)
        return ('  <div class="mini-ety">%s</div>' % _pair(join("no", True), en_html)
                if en_html else "")
    segs = [seg for seg in (ety.get("no" if side == "no" else "en") or []) if seg]
    if not segs:
        return ""
    return ('  <div class="mini-ety">%s</div>'
            % ";<br>".join(xexpand(seg, norwegian=(side == "no")) for seg in segs))


def _expr_block(row, xexpand, side="en"):
    """A senseless row's mini shows its expression rows in full — term, senses, subsenses,
    examples — since that is all the content the article carries."""
    term = html.escape((row.get("lemmas") or [{}])[0].get("form", ""), quote=False)
    p = ['<div class="mini-expr"><span class="mini-expr-term">%s</span>' % term]
    for s in row.get("senses", []):
        # A hollow wrapper says nothing of its own (`til pass`) — its content is the subs
        # below, so it must not open the block with a blank line.
        line = _en_line(s.get("en"), xexpand, s.get("no"), side)
        if line:
            p.append('<div class="mini-single">%s</div>' % line)
        p.append(_idiom_line(s, side) + _comp_line(s, xexpand))
        for ex in _unit_examples(s)[:1]:
            p.append(_example_html(ex, xexpand, side))
        for sub in s.get("subs", []):
            p.append('<div class="mini-sub"><div class="mini-single">%s</div>%s%s</div>'
                     % (_en_line(sub.get("en"), xexpand, sub.get("no"), side),
                        _idiom_line(sub, side) + _comp_line(sub, xexpand),
                        "".join(_example_html(ex, xexpand, side)
                                for ex in _unit_examples(sub)[:1])))
    p.append('</div>')
    return "".join(p)


def render(row, gloss, defn=None, xexpand=None, expr_rows=None, side="en"):
    """A library row -> mini-article HTML. ``gloss`` is the citing link's English; ``defn``
    anchors a ``#defN`` citation to one sense; ``xexpand`` expands the row's own markers
    hover-only; ``expr_rows`` are the row's expression rows (used only when it has no senses).

    ``side='no'`` renders the **Norwegian face** of the same mini — the unit lines, examples
    and etymology from the row's derived ``no``, no English line, no set-phrase box: what the
    public site shows for a cross-reference whose target is not translated yet
    (`ordpar/`, site decisions 34). ``side='both'`` is the English mini with each unit line
    and the etymology as a Norwegian-over-English line pair (`_pair`): the site's mini of a
    translated target, whose stylesheet picks what shows (site decisions 54). Nothing else
    changes, and the deck's default is untouched.
    A falsy ``gloss`` drops the header's ``— gloss`` span altogether: a Norwegian-faced mini
    is cited from a page that has no English gloss to put there. The deck always passes one
    (``markup._render_link`` refuses an untitled link), so its output is byte-identical."""
    if xexpand is None:
        xexpand = lambda t, norwegian=False: html.escape(t or "", quote=False)
    # The ordbokene link targets the *cited* subsense for a #defN citation
    # (`…/21804#def23`), else the article top — matching the mini's own scope.
    href = "/nob/bm/%d" % row["id"] + ("#def%d" % defn if defn is not None else "")
    lem = (row.get("lemmas") or [{}])[0]
    # The headword itself carries the ordbokene link (Robin, 2026-07-13 — tidier, and
    # consistent with the card header, `ordbok_gen._lemma_form`): colour-inherit anchor,
    # underline on hover only. The `(homograph, sense)` suffix stays outside the anchor —
    # it marks the heading, not the word.
    head_word = ('<a href="%s%s">%s</a>%s'
                 % (BASE, html.escape(href, quote=True),
                    html.escape(lem.get("form", ""), quote=False), _suffix(row, defn)))

    p = ['<div class="mini">',
         '  <div class="mini-head"><span class="mini-hw">%s</span>%s</div>'
         % (head_word, '<span class="mini-gloss"> — %s</span>' % _gsep(gloss) if gloss else "")]

    senses = row.get("senses") or []
    if not senses:
        # **A senseless row shows its etymology** (Robin, 2026-07-29) — the one place a mini
        # does. Minis omit etymology because a defined word's senses say what it means and the
        # etymology is background; with no senses there is no such competition, and for a word
        # that exists only inside its expressions the etymology is often the closest thing to
        # an explanation the article carries. `fyllest` heads two expressions and its origin —
        # Low German {vulleisten}, "to accomplish in full" — states the sense both share more
        # plainly than either expression does. 12 rows deck-wide, 10 with an etymology.
        ety = _ety_block(row, xexpand, side)
        if ety:
            p.append(ety)

    anchored = _anchored_defn(row, defn) if defn is not None else None
    if anchored and anchored[0] == "sub":
        p.append('  <div class="mini-senses">%s</div>'
                 % _anchored_sub_block(anchored[1], defn, xexpand, side))
    elif anchored and anchored[0] == "sense":
        p.append('  <div class="mini-senses">%s</div>'
                 % _sense_blocks([anchored[1]], xexpand, side=side))
    elif senses:
        # a bare href (no #defN), or a #defN that resolved to nothing (g5 flags that separately)
        p.append('  <div class="mini-senses">%s</div>'
                 % _sense_blocks(senses, xexpand, bare=True, side=side))
    elif expr_rows:
        ordered = sorted(expr_rows, key=lambda e: ordbok_gen.expr_sort_key(
            (e.get("lemmas") or [{}])[0].get("form", "")))
        p.append('  <div class="mini-senses">%s</div>'
                 % "".join(_expr_block(e, xexpand, side) for e in ordered))
    else:
        # A row ordbokene has not defined: the header alone left the popup looking like a
        # rendering failure (`alarmklokke`, clicked from `klokke`'s compound list — Robin,
        # 2026-07-29). Say so, as the site does, in our own words (`ordbok_gen.NO_DEFINITION_NOTE`).
        p.append('  <div class="mini-senses"><div class="mini-nodef">%s</div></div>'
                 % html.escape(ordbok_gen.NO_DEFINITION_NOTE, quote=False))

    p.append('</div>')
    return "\n".join(p)


def _gsep(gloss):
    """The header's gloss with each " · " between glosses in a span of its own, faded (ordpar
    site decisions 116, Robin 2026-10-24; the deck follows the site, 105): `.mini-gsep`."""
    return gloss.replace(" · ", '<span class="mini-gsep"> · </span>')


def placeholder(href, gloss):
    """A stand-in mini for a titled link whose target row is missing — preview only; a live
    build raises instead (``markup._render_link``)."""
    return ('<div class="mini"><div class="mini-head"><span class="mini-hw"><a href="%s%s">%s</a></span>'
            '<span class="mini-gloss"> — %s</span></div>'
            '<div class="mini-single"><span class="ordbok-flag">no library row</span></div></div>'
            % (BASE, html.escape(href, quote=True), html.escape(href, quote=False), gloss))


# Mini-article CSS. Scoped under `.mini`; same maroon palette as the cards, with a
# night-mode block mirroring ordbok_gen's `.nightMode` overrides.
STYLE = r'''
.mini{display:inline-block;text-align:left;background:#fffdfd;color:#2a2126;border:1px solid #e8dee2;
  border-radius:.6rem;padding:.85rem .95rem;width:19rem;max-width:100%;
  font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.45;
  box-shadow:0 6px 20px rgba(60,20,40,.14)}
.mini-head{display:block;font-size:1.1rem}
.mini-hw{font-style:italic;font-weight:600;color:#560027}
.mini-gloss{font-size:1rem;font-weight:600}
.mini-gsep{color:#757070}
.mini-senses{margin-top:.55rem;display:flex;flex-direction:column;gap:.55rem}
.mini-sense2{display:flex;flex-direction:column;gap:.3rem}
.mini-sline{display:grid;grid-template-columns:1.1rem 1fr;gap:.45rem;font-size:1rem}
.mini-snum{color:#560027;font-weight:700;font-variant-numeric:tabular-nums}
.mini-single{font-size:1rem}
.mini-nodef{font-size:1rem;font-style:italic;color:#8b7f84}
.mini-ety{margin-top:.45rem;font-size:.86rem;font-style:italic;color:#8b7f84}
.mini-sub{margin:.25rem 0 0 .8rem;padding-left:.55rem;border-left:2px solid #e8dee2}
.mini-ex2{margin-left:1.55rem;padding-left:.6rem;border-left:2px solid #e8dee2}
.mini-solo .mini-ex2{margin-left:0}
.mini-exno{font-style:italic;font-size:.85rem}
.mini-comp{margin-left:1.55rem;padding-left:.6rem;border-left:2px solid #e8dee2;font-size:.85rem;color:#6b6065}
.mini-solo .mini-comp{margin-left:0}
.mini-comp em{font-style:italic}
.mini-exexpl{font-style:normal}
.mini-exexpl em{font-style:italic}
.mini-added{vertical-align:super;font-size:.7em;color:#8b7f84;font-style:normal;cursor:help;margin-left:.1em}
.mini-exen{font-size:.82rem;color:#8b7f84}
.mini-expr{margin-top:.4rem}
.mini-expr-term{display:block;font-weight:700;color:#560027;margin-bottom:.15rem}
/* The mini headword links to its ordbokene page, like the card's own headword. Colour-inherit
   so it keeps the heading colour (mini.STYLE folds in last, so the paired .nightMode selector
   outranks the generic `.nightMode .ordbok a` repaint by order at equal specificity); underline
   on hover only, so the heading still reads as a heading. */
.mini-hw a,.nightMode .mini-hw a{color:inherit;text-decoration:none}
.mini-hw a:hover,.mini-hw a:focus{text-decoration:underline}
.nightMode .mini{background:#201a1e;color:#e9e3e6;border-color:#362b31;box-shadow:0 6px 20px rgba(0,0,0,.4)}
.nightMode .mini-hw{color:#e3b7c9}
.nightMode .mini-gsep{color:#b9b6b6}
.nightMode .mini-exen,.nightMode .mini-nodef,.nightMode .mini-ety,.nightMode .mini-added,.nightMode .mini-comp{color:#a99ba1}
.nightMode .mini-snum,.nightMode .mini-expr-term{color:#e3b7c9}
.nightMode .mini-sub,.nightMode .mini-ex2,.nightMode .mini-comp{border-left-color:#362b31}
'''
