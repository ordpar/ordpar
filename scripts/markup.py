#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marker notation -> card HTML: the one place a marker becomes markup.

Stored strings (derived Norwegian, authored English) carry *semantic markers*, never
presentational HTML (``docs/schemas.md`` § Marker notation). This module expands them per
the link-rendering matrix in ``docs/rendering.md``:

    {word}                     ->  <em>word</em>              a mention, static italic
    [english](href "norsk")    ->  two-tier control, English visible (roman)
    {[norsk](href "english")}  ->  two-tier control, Norwegian visible (italic)
    [norsk](href "english")    ->  in a Norwegian string: Norwegian visible (italic)

The visible language depends on **where the string sits**: a link in authored English shows
English unless ``{…}``-wrapped; a link in derived Norwegian (``norwegian=True``) shows the
Norwegian face. Both tiers come from the marker itself — the visible word, a hover *peek* of
the counterpart language (the link's title), and, on a card, a click-opened *mini-article*
of the target's library row (``mini.render``). A mini arms the hover tier only
(``docs/library.md`` § The closure), so a link expanded inside a mini (``hover_only=True``)
never opens a further mini and never reads the target row — the peek is self-contained.

An **untitled** cross-reference, or a titled link whose target has **no library row**, is a
build error on a live card (``strict=True``); the preview renders it visibly flagged
(``strict=False``) rather than silently plain (guardrails 2/6). ``validate`` is the static
half: it rejects *all* raw tags — including ``<br>`` — plus bad hrefs, empty titles,
unbalanced or mislocated braces.
"""
import re
import html
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ordbok_gen as g  # noqa: E402  -- card control markup (g.xref / g.xref_hover)
import mini  # noqa: E402            -- the click-tier mini-article renderer


class MarkupError(Exception):
    """A marker the renderer refuses to draw silently wrong (untitled / row-less link)."""


def is_see_also(no_segment):
    """True for a derived-Norwegian ``Se: …`` **see-also** def segment — the component
    cross-references ordbokene lists on an expression's *own* article. It is rendered when the
    expression is the main article (a standalone card, or its mini) but **dropped when the
    expression is inlined** into another article's Fixed-expressions block, where pointing back
    is circular (``docs/rendering.md`` § Fixed expressions). Keyed off the Norwegian face so the
    parallel authored English segment is dropped with it. Matches ``Sjå:`` too — ordbokene's
    own data occasionally carries the nynorsk label inside a bokmål article (med mer 103903,
    caught on card 12; Robin, 2026-07-13: embedded expressions never show see-lines)."""
    seg = (no_segment or "").lstrip()
    return seg.startswith("Se:") or seg.startswith("Sjå:")


# --- marker grammar ---------------------------------------------------------
# Expansion escapes first (html.escape(text, quote=False)); markers survive because
# [ ] ( ) { } and " are not escaped. A link is [label](href) with an optional "title".

def _link_pat(label, href, title):
    return (r"\[(?P<%s>[^\]]+)\]\((?P<%s>[^)\s\"]+)(?:\s+\"(?P<%s>[^\"]*)\")?\)"
            % (label, href, title))


_WRAPPED = r"\{" + _link_pat("wl", "wh", "wt") + r"\}"   # {[norsk](h "e")} — Norwegian visible
_BARE = _link_pat("bl", "bh", "bt")                      # [text](h "t")
_MENTION = r"\{(?P<mw>[^{}]*)\}"                          # {word} — a mention
# Ordered alternation: a brace-wrapped link must win over the bare-link and mention branches.
_TOKEN_RE = re.compile("|".join("(?:%s)" % p for p in (_WRAPPED, _BARE, _MENTION)))

_HREF_RE = re.compile(r"^/nob/bm/(?P<id>\d+)(?:#def(?P<defn>\d+))?$")
_LINK_FIND = re.compile(_link_pat("l", "h", "t"))
_RAW_TAG_RE = re.compile(r"<[^>]+>")   # ANY tag is illegal — including <br> (guardrail 6)
_GLUED_BRACE_RE = re.compile(r"[^\W\d_]\{", re.UNICODE)   # letter glued to `{` — see validate()
# UTF-8 bytes read back as cp1252 — the Windows-shell transport defect (2026-09-05, the
# completion round 1: seven authored strings landed as `{hirÃ°}`, `NordmÃ¸re`, `1â€“1` and
# the whole gate accepted them; only A22 noticed, and only where a mention was involved).
# A two-byte UTF-8 sequence shows as Ã/Â + one Latin-1 char, a three-byte one (curly
# quotes, dashes, `·`) as â€ + one char. Measured over the whole library after the repair:
# zero occurrences in either language, so nothing legitimate is in the way.
_MOJIBAKE_RE = re.compile("[ÃÂ][-¿€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]|â€")


# --- library + per-card state -----------------------------------------------
# The builder hands us the library so a click-tier mini renders from the target's row.
# Reveal ids are salted per card with the card freq (set_card) so a rebuild is byte-
# identical and ids stay unique when preview.py concatenates every card onto one page.

_LIBRARY = {}
_SALT = "x"
_N = 0


def set_library(rows):
    """Register the library the click tier resolves against (a list of rows or an id->row map)."""
    global _LIBRARY
    _LIBRARY = rows if isinstance(rows, dict) else {r["id"]: r for r in rows}


def set_card(salt):
    """Begin a card: reset the reveal-id counter and salt ids with whatever `salt` the caller
    hands over. Callers pass `{card label}-{article index}` (`build_cards.combine`,
    `preview.py`, which prefixes per column on top); `ordbok_gen.render_card` falls back to the
    row id. Not the card freq — that was true before multi-article cards (`rendering.md`)."""
    global _SALT, _N
    _SALT, _N = str(salt), 0


def _next_uid():
    global _N
    _N += 1
    return "%s-%d" % (_SALT, _N)


# --- expansion --------------------------------------------------------------

def expand(text, norwegian=False, hover_only=False, strict=True):
    """Expand marker notation in one string into card HTML.

    ``norwegian`` — the string is derived Norwegian, so a bare link is Norwegian-visible
    (italic). ``hover_only`` — we are inside a mini, so links arm the hover tier only (no
    click, no nested mini). ``strict`` — raise on an untitled / row-less link (a live build);
    when false, render it visibly flagged (the preview).
    """
    if not text:
        return text or ""
    esc = html.escape(text, quote=False)

    def sub(m):
        if m.group("wl") is not None:
            return _render_link(m.group("wl"), m.group("wh"), m.group("wt"),
                                norwegian_visible=True, hover_only=hover_only, strict=strict)
        if m.group("bl") is not None:
            return _render_link(m.group("bl"), m.group("bh"), m.group("bt"),
                                norwegian_visible=norwegian, hover_only=hover_only, strict=strict)
        return "<em>%s</em>" % m.group("mw")

    return _TOKEN_RE.sub(sub, esc)


def _render_link(label, href, title, norwegian_visible, hover_only, strict):
    """One cross-reference. The English side is always the visible word when English is
    visible, the title otherwise — that is the mini-article's gloss."""
    hm = _HREF_RE.match(href)
    if hm is None:
        return _fail("bad cross-reference href %r" % href, label, strict)
    if not title:
        return _fail("untitled cross-reference [%s](%s)" % (label, href), label, strict)
    if norwegian_visible:
        visible_html, peek, gloss = "<em>%s</em>" % label, title, title
    else:
        visible_html, peek, gloss = prose_sep(label), title, label
    if hover_only:
        # Depth-two: no nested mini (the closure stops here), but the word links straight to
        # ordbokene — to the cited subsense when the href carries a #defN.
        return g.xref_hover(visible_html, peek, g.BASE + href)
    row = _LIBRARY.get(int(hm.group("id")))
    if row is None:
        if strict:
            raise MarkupError("cross-reference to %s has no library row" % href)
        return g.xref(_next_uid(), visible_html, peek, mini.placeholder(href, gloss))
    defn = int(hm.group("defn")) if hm.group("defn") else None
    # The mini's own strings expand hover-only (depth one); strict flows in so a live build
    # still refuses an untitled link buried in a mini. The target row's reference pairs are
    # completed first (minis render authored English — same injection as the card body).
    xe = lambda t, norwegian=False: expand(t, norwegian=norwegian, hover_only=True, strict=strict)
    mini_html = mini.render(pair_view(row, "en"), gloss=gloss, defn=defn, xexpand=xe,
                            expr_rows=[pair_view(_LIBRARY[i], "en")
                                       for i in row.get("exprs", []) if i in _LIBRARY])
    return g.xref(_next_uid(), visible_html, peek, mini_html)


def _fail(msg, label, strict):
    if strict:
        raise MarkupError(msg)
    return '<span class="ordbok-flag" title="%s">%s</span>' % (html.escape(msg, quote=True), label)


# --- reference pairs (render-time title completion) --------------------------
# Every cross-reference is one pair: a mechanical Norwegian face + one authored English
# gloss (docs/proposals/reference-pairs.md, Robin 2026-07-18). Whichever member a string
# stores visibly, the *other* is injected as the link's title at render time, so nothing
# is stored twice: an authored-English bare link gets the same-unit derived-Norwegian
# face as its hover; a derived-Norwegian definition/etymology link gets the citer's
# gloss (the preview's source column). Stored titles always win — they are the fallback
# tier (an ``ex-en`` link whose href has no face in its own example) and the authored
# gloss on wrapped links.

def inject_pair_titles(text, titles):
    """``text`` with each **untitled bare** link's pair counterpart injected as its title
    (``titles``: href → counterpart). Wrapped links and titled links pass through — a
    wrapped link's title is its authored gloss, and an untitled wrapped link is a
    notation error the validator owns, never silently papered over."""
    if not text or not titles:
        return text

    def sub(m):
        if m.group("bl") is not None and m.group("bt") is None:
            t = titles.get(m.group("bh"))
            if t:
                return '[%s](%s "%s")' % (m.group("bl"), m.group("bh"), t)
        return m.group(0)

    return _TOKEN_RE.sub(sub, text)


def _pair_faces(segs):
    """href → Norwegian face: each bare link's display text in derived-Norwegian ``segs``
    (first occurrence wins; the library has no unit citing one href under two faces)."""
    m = {}
    for seg in segs or []:
        for mo in _TOKEN_RE.finditer(seg or ""):
            if mo.group("bl") is not None:
                m.setdefault(mo.group("bh"), mo.group("bl"))
    return m


def _pair_glosses(segs):
    """href → citer's English gloss in authored-English ``segs``: a bare link's visible
    label, a wrapped link's title — the visible-language rule, same extraction as
    ``citations``."""
    m = {}
    for seg in segs or []:
        for mo in _TOKEN_RE.finditer(seg or ""):
            if mo.group("wl") is not None and mo.group("wt"):
                m.setdefault(mo.group("wh"), mo.group("wt"))
            elif mo.group("bl") is not None:
                m.setdefault(mo.group("bh"), mo.group("bl"))
    return m


HEADLINE_SEP = " · "   # separates whole headline glosses; commas separate within one
PROSE_SEP = "; "       # the same boundary, rendered where English is the VISIBLE side


def prose_sep(gloss):
    """A stored gloss re-punctuated for **running English prose** (Robin, 2026-07-28).

    One boundary, two idiomatic renderings. `·` reads well as a compact list — in a hover
    popup, in the summary browser, in a joined headline set — and badly inside a definition
    line, which is running lexicographic prose where `;` is the norm. The stored form is `·`
    (it must match what `headline_gloss` joins, so a stored gloss and an injected headline set
    are one shape); this is the one-way swap applied at render time, and only where English is
    the visible side. A hover title keeps `·`.

    Scoped to a link's visible **label**, never to the surrounding prose: `;` is ordinary
    punctuation in an example translation or a summary note ("the ship left Rio on 15 Oct.;
    since then no one has seen her") and must survive untouched.
    """
    return gloss.replace(HEADLINE_SEP, PROSE_SEP) if gloss else gloss


def headline_gloss(href):
    """The target's **curated summary headline set**, joined for a Norwegian-visible hover —
    or ``None`` when the rule doesn't apply (Robin, 2026-07-22).

    A **bare** href cites the whole word, so the honest hover is the whole curated set
    (``a · b``), not one gloss picked out of it — the same reasoning guardrail 8 already
    applies when it judges a bare citation against the headline. A **``#defN``** href is
    sense-governed and gets nothing here: its gloss is the citing sense's own nuance
    (``finne (IV, 1)`` → "to come across"), which a whole-word headline would drown.
    Targets with no ``summary`` (every mini — guardrail 19 requires a block only on articles
    composed onto a live card) also return ``None``, keeping the authored gloss as the
    fallback. Two-level separation: ``·`` between headline glosses, commas inside one
    (``who, which, that · as · like``)."""
    hm = _HREF_RE.match(href or "")
    if not hm or hm.group("defn"):
        return None
    gl = ((_LIBRARY.get(int(hm.group("id"))) or {}).get("summary") or {}).get("gloss") or []
    return HEADLINE_SEP.join(gl) if gl else None


def _inject_headlines(text, wrapped=False, bare=False):
    """``text`` with the **Norwegian-visible** links' hover titles replaced by the target's
    headline set (``headline_gloss``). ``wrapped``: ``{[face](h "gloss")}`` in authored
    English (see-also, etymon, mention). ``bare``: a titled bare link in derived-Norwegian
    example text. A target with no headline keeps its authored title."""
    if not text:
        return text

    def sub(m):
        if wrapped and m.group("wl") is not None:
            hl = headline_gloss(m.group("wh"))
            if hl:
                return '{[%s](%s "%s")}' % (m.group("wl"), m.group("wh"), hl)
        elif bare and m.group("bl") is not None and m.group("bt") is not None:
            hl = headline_gloss(m.group("bh"))
            if hl:
                return '[%s](%s "%s")' % (m.group("bl"), m.group("bh"), hl)
        return m.group(0)

    return _TOKEN_RE.sub(sub, text)


def pair_view(row, side="en"):
    """A render-ready **copy** of ``row`` with every reference pair completed for ``side``.

    ``side='en'`` (card, mini): authored-English bare links get the same-unit derived-
    Norwegian face as hover title; an example's English gets faces from its own example
    Norwegian (self-contained — examples are parity-excluded, so a stored title is the
    fallback when no face exists there). ``side='no'`` (the preview's source column):
    derived-Norwegian definition/etymology links get the citer's gloss from the parallel
    authored English (Robin, 2026-07-18 — the hover then shows what the deck actually
    renders); example-Norwegian links keep their stored authored titles. The input row is
    never mutated — library rows are shared across a build."""
    import copy
    r = copy.deepcopy(row)

    def fix_unit(unit):
        no, en = unit.get("no") or [], unit.get("en")
        if side == "en":
            if en:
                fm = _pair_faces(no)
                unit["en"] = [_inject_headlines(inject_pair_titles(s, fm), wrapped=True)
                              for s in en]
            # example Norwegian is deck-visible on the card: its authored titles are
            # Norwegian-visible hovers, so they take the headline treatment too.
            for pair in unit.get("ex") or []:
                pair[0] = _inject_headlines(pair[0], bare=True)
            for blk in unit.get("comp") or []:
                for it in blk.get("items") or []:
                    hl = headline_gloss(it.get("href"))
                    if hl:
                        it["en"] = hl
        else:
            gm = _pair_glosses(en) if en else {}
            unit["no"] = [inject_pair_titles(s, gm) for s in no]
        for pair in unit.get("ex") or []:
            if side == "en" and pair[1]:
                pair[1] = inject_pair_titles(pair[1], _pair_faces([pair[0]]))

    ety = r.get("etymology")
    if ety:
        fix_unit(ety)  # same no/en shape as a sense; carries no ex
    for s in r.get("senses") or []:
        fix_unit(s)
        for u in s.get("subs") or []:
            fix_unit(u)
    return r


# --- introspection (for guardrails + reach analysis) ------------------------

def links(text):
    """Every ``[label](href "title")`` marker as ``(label, href, title|None)`` triples."""
    return [(m.group("l"), m.group("h"), m.group("t")) for m in _LINK_FIND.finditer(text or "")]


def hrefs(text):
    """Just the hrefs cited in a string."""
    return [h for _l, h, _t in links(text)]


def visible_prose(text):
    """The string minus every link marker, whole — the prose standing OUTSIDE any link face.

    The A16 unlock's single-ref containment test used this until 2026-08-27 and now uses
    `visible_faces`: deleting labels made the unlock search a surface the DETECTOR does not
    see, so a gloss contained in a sibling link's label ("river" inside "a river bed",
    `elvedrag` def 2) fired A16 on a gloss the unlock could not open, and the collapse's
    cold re-author was served the collapse back as settled (batch 4639-4927 entry 4)."""
    return _LINK_FIND.sub(" ", text or "")


def visible_faces(text, skip_href=None):
    """The string with each link marker reduced to its shown LABEL — the whole visible
    surface, links included; only hrefs and titles drop (contrast `visible_prose`, which
    deletes faces entirely). ``skip_href`` blanks that target's links instead, so a caller
    testing whether a link's own gloss stands elsewhere on the surface never matches the
    link against itself.

    This is the surface the A16 detector quantifies over (its `_visible` reduces links to
    their shown word), and since 2026-08-27 the surface the unlock's containment test
    searches too — the invariant being that A16 never fires on a surface the unlock cannot
    open (Robin, via the Fable review of batch 4639-4927 entry 4)."""
    def _face(m):
        return " " if (skip_href is not None and m.group("h") == skip_href) else m.group("l")
    return _LINK_FIND.sub(_face, text or "")


def citations(text, norwegian=False):
    """``(id, defn, english_gloss)`` per cross-reference, the English side chosen by the
    visible-language rule (so attestation/divergence compare the *English* gloss): a bare link
    in English prose is English-visible → gloss = label; a ``{…}``-wrapped link, or any link in
    a Norwegian string (``norwegian=True``), is Norwegian-visible → gloss = title."""
    out = []
    for m in _TOKEN_RE.finditer(text or ""):
        if m.group("wl") is not None:
            href, gloss = m.group("wh"), m.group("wt")
        elif m.group("bl") is not None:
            href = m.group("bh")
            gloss = m.group("bt") if norwegian else m.group("bl")
        else:
            continue
        hm = _HREF_RE.match(href)
        if hm:
            out.append((int(hm.group("id")),
                        int(hm.group("defn")) if hm.group("defn") else None, gloss))
    return out


def citations_faced(text, norwegian=False):
    """``citations`` plus the pair's **facing**: ``(id, defn, gloss, norwegian_visible)``.

    ``norwegian_visible`` is True when the reader sees the Norwegian and the *gloss* lives in
    the hover — a ``{…}``-wrapped link, or any link inside a Norwegian string. Advisory 8 uses
    it to skip the class whose hover is now derived from the target's headline at render time
    (``headline_gloss``), where the stored gloss is no longer what the deck shows."""
    for m in _TOKEN_RE.finditer(text or ""):
        if m.group("wl") is not None:
            href, gloss, no_vis = m.group("wh"), m.group("wt"), True
        elif m.group("bl") is not None:
            href = m.group("bh")
            gloss = m.group("bt") if norwegian else m.group("bl")
            no_vis = norwegian
        else:
            continue
        hm = _HREF_RE.match(href)
        if hm:
            yield (int(hm.group("id")),
                   int(hm.group("defn")) if hm.group("defn") else None, gloss, no_vis)


def validate(text, where="", require_titles=False):
    """Static notation problems in a stored string (guardrail 6). Empty list == clean.

    ``require_titles`` (pass for **authored-English** strings): every **wrapped**
    (Norwegian-visible) cross-reference must carry a title — its title *is* the authored
    English gloss, the pair's only home. A **bare** link's title is no longer required
    (reference pairs, Robin 2026-07-18): its gloss is the visible label, and the Norwegian
    face is injected at render time (``pair_view``); a *stored* bare-link title is either
    the fallback tier (an ``ex-en`` link with no derivable face) or a leftover the
    unit-level pair check in ``check_library`` flags. Off by default because a
    *derived-Norwegian* link's title (example text) is authored lazily (absent until the
    row is reached — guardrail 2 owns that, reachability-scoped)."""
    problems = []
    if not text:
        return problems
    for tag in _RAW_TAG_RE.findall(text):
        problems.append("%s: raw HTML %r — markers only, no tags (not even <br>)" % (where, tag))
    if text.count("{") != text.count("}"):
        problems.append("%s: unbalanced {} (%d open, %d close)"
                        % (where, text.count("{"), text.count("}")))
    # A letter glued to `{` is a missing word space, not notation (Robin, 2026-08-24 — the
    # `OldNorse{ǿrr}` incident: a hand repair whose one-liner stripped every space landed a
    # well-formed marker the whole gate accepted, and only the hand-author auto-flag caught
    # it). Measured over the entire library — every field, both languages — the shape occurs
    # ZERO times, so there are no false positives to weigh; anything this fires on is a
    # defect at write time instead of a spawn pair later.
    for m in _GLUED_BRACE_RE.finditer(text):
        problems.append("%s: %r — a letter glued to '{' (missing word space?)"
                        % (where, text[max(0, m.start() - 20):m.end() + 10]))
    for m in _MOJIBAKE_RE.finditer(text):
        problems.append("%s: %r — mojibake (UTF-8 read as cp1252); re-enter the text as "
                        "UTF-8" % (where, text[max(0, m.start() - 20):m.end() + 10]))
    for m in _TOKEN_RE.finditer(text):
        if m.group("mw") is not None:
            continue
        wrapped = m.group("wl") is not None
        label = m.group("wl") if wrapped else m.group("bl")
        href = m.group("wh") if wrapped else m.group("bh")
        title = m.group("wt") if wrapped else m.group("bt")
        if not _HREF_RE.match(href):
            problems.append("%s: href %r not /nob/bm/{id}[#def{N}]" % (where, href))
        if title == "":
            problems.append("%s: empty title on [%s](%s)" % (where, label, href))
        elif title is None and require_titles and wrapped:
            problems.append("%s: untitled wrapped link {[%s](%s)} — the English gloss "
                            "title is mandatory on a Norwegian-visible link" % (where, label, href))
        if "{" in label or "}" in label:
            problems.append("%s: brace inside link label [%s] — braces go outside" % (where, label))
        # `·` is the reserved sense separator in a stored GLOSS (Robin, 2026-07-28), so a `;`
        # there is either an unmigrated row or a misuse. Scoped to the two gloss surfaces — a
        # link's title, and its visible label when the string is authored English — and NOT to
        # the surrounding prose, where `;` is ordinary punctuation: 224 summary note/trap
        # strings and 8 example translations rely on it ("the ship left Rio on 15 Oct.; since
        # then no one has seen her").
        if title and ";" in title:
            problems.append("%s: ';' in the gloss title %r — the stored sense separator is "
                            "'%s' (rendered as ';' only where English is visible)"
                            % (where, title, HEADLINE_SEP.strip()))
        if require_titles and not wrapped and ";" in label:
            problems.append("%s: ';' in the gloss [%s] — the stored sense separator is '%s' "
                            "(rendered as ';' only where English is visible)"
                            % (where, label, HEADLINE_SEP.strip()))
    return problems
