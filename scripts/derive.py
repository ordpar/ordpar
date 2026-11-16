#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derive the Norwegian side of ``articles.jsonl`` from ``sources/`` — never English.

The deriver is **mechanical and idempotent**: it projects the committed API captures into
library rows and re-runs to byte-identical output. Its whole contract is **merge, never
overwrite** on anything authored — `en` segment lists, `idiom` slots, comp `en`, and the
English *title* slot inside a Norwegian link marker are preserved from the existing row and
re-aligned; the mechanical Norwegian around them is regenerated (``docs/pipeline.md`` §
Deriver).

Hard stops (invalid states must not pass silently):
- ``$``-placeholder / item-count mismatch in any filled string (the old ``_fill`` bug that
  substituted empty strings) → ``DeriveError``.
- Unknown POS tag set (``postags.UnknownPOS``) → the header cannot be guessed.

Advisories (surfaced, never fatal): a sub flattened up from depth-3 (the flat ``subs``
schema can't nest — Robin, 2026-07-12); an underivable link display form; embedded-vs-
standalone expression divergence — emitted here, summarized by ``check_library.py``.
"""
import os
import re as _re
import sys
import json
import argparse
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # noqa: E402
import store  # noqa: E402
import postags  # noqa: E402
import markup  # noqa: E402  -- is_see_also (shared see-also identification)
import headwords  # noqa: E402  -- the headword groups (site ruling 49)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(ROOT, "articles.jsonl")


class DeriveError(Exception):
    """A source structure the deriver refuses to guess at — halts for triage."""


# --- concept + item filling -------------------------------------------------

_CONCEPTS_MEMO = (None, None)  # ((mtime, size) of the snapshot, the map)


def concepts_map():
    """The ``concept → expansion`` table, memoized on the snapshot file's (mtime, size).

    Every transient derivation asked for it afresh — 2,305 reads of ``concepts.json`` in one
    scoped gate, 1.7 s (context-cost decisions 9, 2026-09-05). The stat guard keeps a
    re-snapshot (``fetch.ensure_concepts(force=True)``) visible to the same process."""
    global _CONCEPTS_MEMO
    try:
        st = os.stat(fetch.CONCEPTS_PATH)
        stamp = (st.st_mtime_ns, st.st_size)
    except OSError:
        stamp = None
    if stamp is not None and _CONCEPTS_MEMO[0] == stamp:
        return _CONCEPTS_MEMO[1]
    raw = fetch.ensure_concepts()
    table = {k: (v.get("expansion") or k) for k, v in (raw.get("concepts") or {}).items()}
    if stamp is not None:
        _CONCEPTS_MEMO = (stamp, table)
    return table


_HGNO_CACHE = {}
_DEFIDS_CACHE = {}
_DEFORD_CACHE = {}

# Dangling `definition_id`s discovered while filling a row's markers — a ref whose target
# article exists but has no definition with the cited id (ordbokene's own data is internally
# inconsistent; slumpe 54577 has one def but `komme til å` cites `#def4`). link_marker drops
# the unresolvable anchor and the dangling sense-number suffix (bare-href to the real article,
# whose mini renders its actual senses — Robin, 2026-07-16), and records the case here;
# derive_row drains it into its advisory channel as advisory 11.
_DEF_DANGLERS = []


def _source_def_ids(aid):
    """The set of ``definition`` node ids that **derive to a unit of the target's row**
    (``None`` if the source is not on disk — an unfetched target we cannot confirm dangling
    against). Cached; build_closure fetches every depth-one ref before deriving, so a card
    ref's target is always present.

    The oracle is the deriver's own sense/sub walk, not the raw node set, because an anchor
    is resolvable exactly when the row it lands on has that ``defn`` — which is what
    guardrail 5 checks. Two node classes exist in a capture but derive nothing, and an
    anchor at either is as unusable as one at an id the article never had:

    * an **expression-host** node, whose only element is a ``sub_article`` — no explanation
      and no example of its own, so ``_is_gloss`` rejects it and it vanishes from the row.
      ``felt I`` (14219) def 7 hosts *ut/ute i felten* and nothing else, yet ``feltarbeid``
      (14222) cites ``#def7``; ``dess`` (9889) def 5 and ``desto`` (9909) are the same pair.
      Counted as present, the anchor survived into the derived Norwegian and left a row
      **no English could merge** — guardrail 5 rejected it on the ``no`` side too, so no
      authoring could fix it (found by the slot-3 authoring agent, 2026-08-08; 2 refs
      affected across the pinned universe, both this shape).
    * a pure **container/wrapper** node, which holds only child definitions.

    This subsumes the older ``sub_article`` stop-condition rather than restating it: the
    walk reaches a nested article's ids by no path at all, since ``_def_children`` reads
    ``elements`` for ``type_ == "definition"`` only. That condition existed because ``ne``
    (40430) owns only def 4 while its embedded ``i ny og ne`` carries def 2, so the dangling
    ``#def2`` that ``fallende måne`` cites read as resolvable — the same symptom, and now
    impossible by construction instead of by a special case (card-426 agent, 2026-07-26)."""
    if aid not in _DEFIDS_CACHE:
        src = fetch.load_source(aid)
        if src is None:
            _DEFIDS_CACHE[aid] = None
        else:
            ids = set()
            for sense in _collect_senses(src):
                if sense.get("id") is not None:
                    ids.add(sense["id"])
                # a throwaway advisory sink: deriving the target itself emits its own
                # flattened-subsense lines, and the oracle must not duplicate them
                for sub in _collect_subs(sense, aid, []):
                    if sub.get("id") is not None:
                        ids.add(sub["id"])
            _DEFIDS_CACHE[aid] = ids
    return _DEFIDS_CACHE[aid]


def _target_def_ordinal(aid, did):
    """The **displayed** sense number a ``#defN`` anchor resolves to, read off the TARGET's own
    source: a top sense's 1-based position among the target's senses, or a subsense's 1-based
    position among its parent's subs. ``None`` when the target is not on disk (an unfetched
    depth-two peek) or the id resolves to nothing.

    **This replaces the citer's ``definition_order``** (Robin, 2026-08-09). A citation carried
    two fields for one fact — ``definition_id`` chose the anchor, ``definition_order`` printed
    the suffix — and nothing made them agree. ``gymnastikkøvelse`` (21687) anchored ``øvelse``
    id 5, displayed 3, while printing ``(2)``, which names id 7, *"det å beherske en kunst"*:
    the face told the reader one sense and the link went to another. Deriving the number from
    the target makes that class unrepresentable rather than merely detectable, and it is the
    same mapping ``mini._display_num`` already uses on the rendered side, so the two cannot
    drift either. The stored ``definition_order`` survives only as the fallback below."""
    if aid not in _DEFORD_CACHE:
        src = fetch.load_source(aid)
        if src is None:
            _DEFORD_CACHE[aid] = None
        else:
            out = {}
            for i, sense in enumerate(_collect_senses(src), 1):
                if sense.get("id") is not None:
                    out[sense["id"]] = i
                # a throwaway advisory sink, as in `_source_def_ids`
                for j, sub in enumerate(_collect_subs(sense, aid, []), 1):
                    if sub.get("id") is not None:
                        out.setdefault(sub["id"], j)
            _DEFORD_CACHE[aid] = out
    table = _DEFORD_CACHE[aid]
    return None if table is None else table.get(did)


def _target_hgno(aid, item_lem):
    """The homograph a citing ``article_ref`` shows for the spelling it cites. A normal ref
    carries its own ``hgno`` field (``0`` or a number); use the target's source to confirm it —
    **the target lemma whose form is the one the ref names** — falling back to the item's own
    value for a form the target does not list, and to the target's first numbered lemma only
    when the ref has no usable value of its own. An unfetched (dangling) target has no source to
    read, so the item's value stands. A ``Se:`` see-also ref carries **no ``hgno`` field at
    all** — and ordbokene renders those lines with the **bare lemma, no homograph** (`Se: la,
    være`), so it gets none. Keying the bare case off the missing field (not the target source)
    also keeps a see-also line's derivation independent of that target's source, so it stays
    deterministic when the target is not a committed row (`docs/rendering.md` § Fixed expressions).

    **The homograph belongs to a SPELLING, not to an article** (2026-09-08; batch-notes entry 6
    of `docs/sessions/2026-09-08-continuation-batch-2/…/notes.md`, route (1), and the Fable
    review of it). Until this the scan took *the target's first lemma with a truthy hgno* and
    cached it per target id, ignoring which of the target's spellings the ref named. `opprustning`
    (42635) lists `opprustning` hgno **0** and the variant `opprusting` hgno **2** — the variant
    collides with another headword, the main spelling does not — so every ref to *opprustning*
    printed `opprustning (II)` while our own derived header for 42635 said `homograph: null`.
    Measured over every committed capture: **138 refs, 130 captures, 51 targets**, every one
    spurious (a numeral where the cited spelling has none) and none the other way; 108 of the
    138 between library rows, 80 rendered, 26 inside authored English link labels. Invisible to
    every guardrail — the link resolves and parity holds; only the face was wrong. The ref itself
    carries the answer: it lists the target's lemmas with THEIR hgno, and over the pinned
    universe the ref's own value equals the target's for that spelling in 37,054 of 37,161
    fetchable cases. Raw string compare of the two forms is enough — ``_display_lemma``
    normalisation of the ``[a|b]`` alternation was measured to add **zero** further matches
    (both sides come from ordbokene in the same syntax), and only 3 refs name a form the target
    does not list at all (`avstemming` → 3873 *avstemning* ×2, `støtt` → 58077 *støte/støyte*).
    The cache is keyed by ``(aid, form)``: per target id, the two spellings of one article would
    go on sharing a single numeral."""
    if "hgno" not in item_lem:
        return 0
    form = item_lem.get("lemma")
    key = (aid, form)
    if key not in _HGNO_CACHE:
        src = fetch.load_source(aid)
        hg = None
        if src:
            for lem in src.get("lemmas", []):
                if lem.get("lemma") == form:
                    hg = lem.get("hgno") or 0
                    break
            if hg is None and item_lem.get("hgno") is not None:
                # a form the target does not list — an inflected `word_form` ref, or a spelling
                # the article dropped. The ref's own value is the best evidence left.
                hg = item_lem["hgno"] or 0
            if hg is None:
                for lem in src.get("lemmas", []):
                    if lem.get("hgno"):
                        hg = lem["hgno"]
                        break
            if hg is None:
                hg = 0
        _HGNO_CACHE[key] = hg
    hg = _HGNO_CACHE[key]
    return hg if hg is not None else (item_lem.get("hgno") or 0)


def link_marker(item):
    """An ``article_ref`` → `[display](/nob/bm/{id}[#def{N}])`, no title (titles are
    authored and merged in later). Display = the ref's ``word_form`` (inflected) else the ref's
    cited lemma, then ordbokene's ``(homograph, sense)`` suffix — Roman homograph from the
    **target article's entry for the cited spelling** (``_target_hgno``; a target's variant
    spelling may be a homograph where its main one is not) and the cited sense's displayed
    ordinal — omitting
    absent parts (`konjunktiv (1)`, `ha (II, 13)`, `kopula`, `være (II)`). Settled with Robin
    2026-07-12; homograph-from-target amendment 2026-07-13. A **dangling `definition_id`** —
    an anchor to a definition the target article does not have (`komme til å` → `slumpe #def4`,
    slumpe having one def) — drops the anchor and its sense-number suffix and keeps a bare-href
    link, recording advisory 11 (Robin, 2026-07-16; the dangling-*article* case above renders
    plain text instead — there the whole article is gone)."""
    aid = item["article_id"]
    lemmas = item.get("lemmas") or [{}]
    lem0 = lemmas[0] if isinstance(lemmas[0], dict) else {"lemma": lemmas[0]}
    text = _display_lemma(item.get("word_form") or lem0.get("lemma") or "")
    if int(aid) in fetch.load_dangling():
        # A confirmed-dangling target (404 in ordbokene) has no article to open and would fail
        # the strict build as a link — render its display form as plain definitional Norwegian
        # instead (Robin, 2026-07-13). The registry keeps this deterministic for guardrail 4; the
        # `(homograph, sense)` suffix is dropped since a plain mention makes no citation.
        return text
    href = "/nob/bm/%d" % aid
    did = item.get("definition_id")
    # A dangling `definition_id` in ordbokene's own data: the target article exists but has
    # no definition with this id (slumpe 54577 has only def 2; `komme til å` cites `#def4`).
    # Confirmed against the target source only — an unfetched target (ids == None) keeps its
    # anchor, since we cannot prove it dangling. Drop the unresolvable anchor and the dangling
    # sense-number suffix; the link stays (bare-href to the real article, whose mini renders
    # its actual senses), a valid homograph is kept, and the case rides out as advisory 11
    # (Robin, 2026-07-16). Guardrail 4 stays deterministic — the id set is read from disk.
    ids = _source_def_ids(aid) if did else None
    dangling_def = ids is not None and did not in ids
    if did and not dangling_def:
        href += "#def%d" % did
    parts = []
    hg = _target_hgno(aid, lem0)
    if hg > 0:
        parts.append(_roman(hg))
    if item.get("definition_order") and not dangling_def:
        # The number comes from the TARGET, not from the citer's `definition_order` — see
        # `_target_def_ordinal`. The stored field is kept only as the gate (ordbokene prints a
        # suffix exactly when it sets one) and as the fallback for a target we cannot read.
        shown = _target_def_ordinal(aid, did) if did else None
        parts.append(str(shown if shown is not None else item["definition_order"]))
    if parts:
        text += " (%s)" % ", ".join(parts)
    if dangling_def:
        _DEF_DANGLERS.append((aid, did))
    return "[%s](%s)" % (text, href)


# ordbokene writes an alternating particle in a lemma as `[a|b]` and *displays* it as `a/b`
# (`valse [over|ned]` is titled "valse over/ned", `[enkelt|enstavelses] tonelag` likewise).
# Normalising at derive time keeps the marker grammar free of nested brackets: a link label
# containing `]` matches no link at all, so the stint validator called a mirrored English link
# invented and the renderer dropped the whole cross-reference to plain text (card 311).
_ALT_RE = _re.compile(r"\[([^\[\]]*)\]")


def _display_lemma(text):
    """ordbokene's display form of a lemma: `[a|b]` → `a/b` (Robin's Core Idea 6 — the live
    site is the baseline; verified against articles 106178 and 113215, 2026-07-26)."""
    return _ALT_RE.sub(lambda m: m.group(1).replace("|", "/"), text or "")


# Unicode super-/subscript, the plain-text equivalent of ordbokene's `<sup>`/`<sub>` and of
# the real fraction it typesets (`gon` shows ¹⁄₄₀₀). No raw HTML may enter stored data
# (guardrail 6), and these characters need none: `km²`, `2³ = 8`, `¹⁄₄₀₀` render as themselves.
_SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷",
        "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾", "n": "ⁿ",
        "i": "ⁱ",
        # site decisions 57 (2026-10-19): the minus as ordbokene's data writes it — an en
        # dash in `piko-` 44916 (10⁻¹²), or the true minus sign — and the `x` of eˣ in
        # `eksponentialfunksjon` 112137. The whole mirror's other scripts all map already.
        "–": "⁻", "−": "⁻", "x": "ˣ"}
_SUB = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇",
        "8": "₈", "9": "₉", "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎", "n": "ₙ",
        "a": "ₐ", "e": "ₑ", "o": "ₒ", "x": "ₓ"}


def _script(text, table, kind):
    """Map ``text`` through a super-/subscript table. An unmappable character raises rather
    than degrading silently: a flattened `2³` reads as the number 23, which is wrong and
    invisible (found on `potens` and `grad I`, card 323)."""
    out = []
    for ch in str(text or ""):
        if ch not in table:
            raise DeriveError("no %s form for %r in %r" % (kind, ch, text))
        out.append(table[ch])
    return "".join(out)


def item_marker(item, concepts, in_example):
    """A filled item. A ``usage`` item is a headword form: **used** (plain) inside an
    example quote, **mentioned** (`{…}`) inside a definition/etymology segment — the
    extracts never brace an example, always brace an etymon."""
    t = item.get("type_")
    if t == "article_ref":
        return link_marker(item)
    if t == "quote_inset":
        return fill(item.get("content"), item.get("items", []), concepts, in_example)
    if t == "usage":
        text = (item.get("text", "") or "").strip()
        return text if in_example else "{%s}" % text
    if t == "fraction":
        # ordbokene typesets a real fraction; U+2044 FRACTION SLASH between a superscript
        # numerator and a subscript denominator reproduces it exactly (`¹⁄₄₀₀`).
        return "%s⁄%s" % (_script(item.get("numerator"), _SUP, "superscript"),
                               _script(item.get("denominator"), _SUB, "subscript"))
    if t == "superscript":
        return _script(item.get("text"), _SUP, "superscript")
    if t == "subscript":
        return _script(item.get("text"), _SUB, "subscript")
    cid = item.get("id")
    if cid is not None:
        return concepts.get(cid, cid)
    return item.get("text", "") or ""


def fill(content, items, concepts, in_example=False):
    """Fill ``$`` placeholders in ``content`` from ``items`` in order. A count mismatch
    raises (the deriver never silently drops an item).

    **A space before a comma is closed up** (Robin, 2026-08-13). ordbokene's own templates
    write ``"fra $ , opprinnelig ‘se på’"`` — language item, then a space, then the comma —
    for the ~122 etymologies whose foreign form is the same string as the Norwegian headword
    and is therefore not printed. Mirrored byte-for-byte that renders as *"fra tysk ,"* on
    every such card, which reads as our defect rather than theirs.

    This is a deliberate, minimal departure from guardrail 4's byte-fidelity, taken here
    rather than in 122 capture edits: the class is *consistent* in the source, so the
    normalization licence (correct ordbokene to its own convention) does not reach it, and a
    capture edit would re-appear on the next re-pin anyway. It is recorded for the ordbokene
    handover in ``review/source-normalizations.jsonl`` as a single class row.

    Scope is exactly what the symptom is: whitespace immediately before ``,`` or ``;``, in
    the assembled segment. Nothing else about the source's text is touched, and no authored
    English carries the stray space, so the re-derive moves Norwegian only."""
    content = content or ""
    items = items or []
    n = content.count("$")
    if n != len(items):
        raise DeriveError("$/item mismatch: %d placeholders vs %d items in %r"
                          % (n, len(items), content))
    parts = content.split("$")
    out = [parts[0]]
    for part, item in zip(parts[1:], items):
        out.append(item_marker(item, concepts, in_example))
        out.append(part)
    return _SPACE_BEFORE_PUNCT.sub(r"\1", "".join(out))


#: ordbokene prints an empty ``$`` slot as a bare space, leaving " ," / " ;" in the assembled
#: text. See :func:`fill`.
_SPACE_BEFORE_PUNCT = _re.compile(r"[ \t]+([,;])")


# --- structure helpers -------------------------------------------------------

def _def_children(node):
    return [e for e in node.get("elements", []) if e.get("type_") == "definition"]


def _is_gloss(node):
    """A unit ordbokene shows: one that carries an explanation of its own, **or** one whose
    only content is an example (Robin, 2026-07-29).

    ordbokene does define a word by example alone: `aldersforskjell` has no explanation, just
    *til tross for aldersforskjellen har vi fin kontakt*, and the site shows exactly that.
    Requiring an explanation dropped the node whole, taking its example with it, so the row
    derived empty and the card, the mini and the A8 cited block all rendered nothing — the
    compound looked contentless when its one piece of evidence was right there.

    Nine nodes deck-wide over 24,611 captures (`aldersforskjell`, `alkoholinnhold`, `agn II`
    and six more), so this is a rare shape, not a class the rest of the pipeline is built
    around: the unit derives with an empty ``no`` (nothing to say) and its ``ex`` intact,
    which is the same shape the see-line deferral already produces.

    A node with definition children is still a container, not a unit — its examples belong to
    the children (`_collect_senses` recurses); only a childless example-only node is one."""
    if any(e.get("type_") == "explanation" for e in node.get("elements", [])):
        return True
    return (not _def_children(node)
            and any(e.get("type_") == "example" for e in node.get("elements", [])))


_JF_HEAD = _re.compile(r"^(jamfør|jf\.?|sml\.?|se)\b", _re.IGNORECASE)
_JF_REST = _re.compile(r"[\s,;.:]*(?:\b(?:og|eller)\b[\s,;.:]*)*")


def _jf_all_dangling(e, concepts):
    """True for an explanation that is nothing but a jamfør-type pointer (``jamfør X``,
    ``jf X og Y``) whose **every** ref target is confirmed dangling — such a segment is
    dropped whole (Robin, 2026-07-14): a "compare X" with nowhere to go teaches nothing
    and is not essential to the lemma. Tested on the **filled** segment (the connector is
    usually a concept item, not content text). A segment with any live ref, or any prose
    beyond connector + refs + separators, is kept (its dangling refs render as plain
    text as before)."""
    refs = [it for it in e.get("items", []) if isinstance(it, dict)
            and it.get("type_") == "article_ref"]
    if not refs or not all(int(it.get("article_id", -1)) in fetch.load_dangling()
                           for it in refs):
        return False
    seg = fill(e.get("content"), e.get("items", []), concepts).strip().rstrip(";").strip()
    m = _JF_HEAD.match(seg)
    if not m:
        return False
    rest = seg[m.end():]
    for it in refs:
        lems = it.get("lemmas") or [{}]
        disp = _display_lemma(it.get("word_form") or (lems[0].get("lemma")
                                                      if isinstance(lems[0], dict) else lems[0]) or "")
        if disp:
            rest = rest.replace(disp, "", 1)
    return _JF_REST.fullmatch(rest) is not None


def _strip_join_commas(segs):
    """Drop the comma ordbokene used to JOIN one element to the next — their source holds
    ``…mellom ulike prosenttall,`` as one element and the synonym ref as the following one;
    our element-per-segment split otherwise leaves that comma hanging at the end of a
    rendered line while the text that completed it starts the next (Robin, 2026-08-23;
    7 rows deck-wide — 5 definitions like prosentpoeng def 2, 2 etymologies like gull's).
    Only a comma on a segment FOLLOWED by another segment goes: a comma inside a segment,
    and one on the LAST segment (beskjed's etymology), are the source's own and stay."""
    out = list(segs)
    for i in range(len(out) - 1):
        s = out[i].rstrip()
        if s.endswith(","):
            out[i] = s[:-1].rstrip()
    return out


def _segments(node, concepts):
    """Filled explanation segments. Per ``docs/schemas.md`` a stored segment carries no
    trailing ``;`` (the renderer joins with ``;<br>``); ordbokene puts one at the end of a
    label like ``brukt som adverb;`` — strip it (a domain-tag ``:`` stays), likewise a
    comma that joined the element to the next (``_strip_join_commas``). A jamfør-only
    segment whose every target is dangling is dropped (``_jf_all_dangling``)."""
    out = []
    for e in node.get("elements", []):
        if e.get("type_") != "explanation":
            continue
        if _jf_all_dangling(e, concepts):
            continue
        seg = fill(e.get("content"), e.get("items", []), concepts).rstrip()
        if seg.endswith(";"):
            seg = seg[:-1].rstrip()
        out.append(seg)
    return _strip_join_commas(out)


def _examples(node, concepts):
    """``[quote, en]`` — or ``[quote, en, explanation]`` where ordbokene attach one.

    Their capture keeps the two apart (`quote` and `explanation` are separate typed
    nodes) and their site renders the quote italic with the explanation upright
    after an en dash. This deriver used to glue them into one string, which threw
    the distinction away one line into the pipeline and left the renderer no way
    to draw the seam (Robin, 2026-08-16). The dash is now the renderer's, not the
    row's. Only the ~116 examples that HAVE an explanation change shape; the rest
    stay pairs."""
    out = []
    for e in node.get("elements", []):
        if e.get("type_") != "example":
            continue
        q = e.get("quote", {})
        no = fill(q.get("content"), q.get("items", []), concepts, in_example=True)
        x = e.get("explanation") or {}
        expl = (fill(x.get("content"), x.get("items", []), concepts, in_example=True)
                if x.get("content") else None)
        out.append([no, None, expl] if expl else [no, None])
    return out


EX_JOIN = " – "        # how the two halves used to be stored, and still display


def ex_no(pair):
    """Every NORWEGIAN string of one ``ex`` entry — the quote, and the explanation
    where ordbokene attached one. **Use this wherever the Norwegian face of an
    example is walked** (markers, closure, notation, repeat checks): reading
    ``pair[0]`` alone silently drops the explanation, which carries links of its
    own, and a dropped link is a row that falls out of the closure."""
    out = [pair[0]]
    if len(pair) > 2 and pair[2]:
        out.append(pair[2])
    return out


def ex_display(pair):
    """The example's Norwegian as one line, the way it renders and the way a human
    reads it in a packet or a log. The renderer styles the halves differently
    (`ordbok_gen._ex_no`); this is for text surfaces that cannot."""
    return EX_JOIN.join(ex_no(pair))


# --- senses + subs (with depth-3 flattening) --------------------------------

def _collect_senses(article):
    """Top senses in document order: gloss-bearing definition nodes, recursing through
    non-gloss containers. A gloss-bearing node's own children are its subs, not senses."""
    senses = []

    def walk(node):
        for child in _def_children(node):
            if _is_gloss(child):
                senses.append(child)
            else:
                walk(child)
    for d in (article.get("body", {}).get("definitions") or []):
        if _is_gloss(d):
            senses.append(d)
        else:
            walk(d)
    return senses


def _collect_subs(sense_node, aid, advisories):
    """A sense's subs, flattened to a single list in document order. A sub with its own
    definition children (depth-3) is flattened up — its gloss-bearing descendants become
    further subs — and each such promotion is flagged (advisory)."""
    subs = []

    def rec(node, depth):
        for child in _def_children(node):
            if _is_gloss(child):
                subs.append(child)
                if depth >= 1:
                    advisories.append(("flattened-subsense",
                                       "%s def %s: subsense flattened up from depth %d"
                                       % (aid, child.get("id"), depth + 2)))
                rec(child, depth + 1)
            else:
                rec(child, depth)
    rec(sense_node, 0)
    return subs


def _blank_en(no):
    """A unit's starting ``en``: ``None`` (unauthored — an obligation the frontier will reach)
    unless there is no Norwegian to translate, where the parallel list is empty by construction
    and there is nothing to author. This is the shape the see-line deferral already produces
    post-hoc; an example-only unit (`_is_gloss`) arrives at it from the other direction, and
    without this it would raise guardrail 2 forever with no slot anyone could fill."""
    return [] if not no else None


def _sub_row(node, concepts):
    no = _segments(node, concepts)
    return {"defn": node.get("id"), "no": no, "en": _blank_en(no),
            "idiom": None, "ex": _examples(node, concepts), "comp": _comp(node, concepts)}


def _sense_row(node, ordinal, aid, concepts, advisories):
    no = _segments(node, concepts)
    return {"defn": node.get("id"), "ordinal": ordinal,
            "no": no, "en": _blank_en(no), "idiom": None,
            "subs": [_sub_row(s, concepts) for s in _collect_subs(node, aid, advisories)],
            "ex": _examples(node, concepts), "comp": _comp(node, concepts)}


# --- etymology, comp, exprs, header -----------------------------------------

def _etymology(article, concepts):
    ety = article.get("body", {}).get("etymology")
    if not ety:
        return {"no": [], "en": None}
    return {"no": _strip_join_commas(
                [fill(n.get("content"), n.get("items", []), concepts) for n in ety
                 if not _jf_all_dangling(n, concepts)]),  # jf-only-dangling dropped (liten → lite)
            "en": None}


#: A compound list's English label, by its Norwegian intro (site decisions 151: the
#: wordings that stay closer to ordbokene's own; the table as drafted). The key is the intro as `comp_intro_key` sees it: its plain text
#: (`fill`ed, so an `f_eks` entity reads "for eksempel" and `sms_er` "sammensetninger"),
#: whitespace collapsed, lower case, any final colon dropped. Matched WHOLE, never by
#: substring: a misspelt intro is corrected in the capture (`pipeline.md` § Source
#: normalization), not matched around. Stored lowercase-initial, as the Norwegian intro is
#: (decisions 151: the English not capitalized, since the Norwegian is not).
#: An intro this table does not know gets `COMP_UNKNOWN_LABEL` and an advisory (`comp-intro-unknown`); no intro at all, no label.
COMP_INTRO_LABELS = {
    "som etterledd i ord som": "as a suffix in words such as:",
    "som etterledd i": "as a suffix in:",
    "brukt som etterledd i ord som": "used as a suffix in words such as:",
    "også som etterledd i": "also as a suffix in:",
    "etterledd i fuglenavn som": "as a suffix in bird names such as:",
    "som forledd i ord som": "as a prefix in words such as:",
    "som førsteledd i ord som": "as a prefix in words such as:",
    # the two "også som førsteledd …" intros, "with the rest of its intro" (151)
    "også som førsteledd i ord som uttrykker tilknytning til nato, i ord som":
        "also as a prefix in words expressing a connection with Nato, in words such as:",
    "også som førsteledd i ord som uttrykker tilknytning til nrk":
        "also as a prefix in words expressing a connection with NRK:",
    "i ord som": "in words such as:",
    "for eksempel": "for example:",
    "for eksempel i ord som": "for example in words such as:",
    "for eksempel i": "for example in:",
    # "også i $ som" with `sms_er` fills to this one (151's "også i {word} som")
    "også i sammensetninger som": "also in compounds such as:",
    "også i sammensetninger": "also in compounds:",
    # two intros 151's table did not list (the contractor's report, 2026-10-30; neither
    # article in the library): drafted on the table's own pattern, for Robin's word
    "i sammensetninger": "in compounds:",
    "som etterledd i for eksempel": "as a suffix in, for example:",
}

#: The label of an intro `COMP_INTRO_LABELS` does not know (151: "in words such as:")
COMP_UNKNOWN_LABEL = "in words such as:"


def comp_intro_key(intro):
    """A compound-list intro as the label table matches it: whitespace collapsed and trimmed,
    lower case, a final colon dropped. Nothing looser."""
    key = _re.sub(r"\s+", " ", intro or "").strip().lower()
    if key.endswith(":"):
        key = key[:-1].rstrip()
    return key


def comp_label(intro):
    """``(label, known)`` for a compound list's plain-text intro: ``("", True)`` for no intro
    (the list is drawn without a label line), the table's label, or ``(COMP_UNKNOWN_LABEL,
    False)``."""
    key = comp_intro_key(intro)
    if not key:
        return "", True
    if key in COMP_INTRO_LABELS:
        return COMP_INTRO_LABELS[key], True
    return COMP_UNKNOWN_LABEL, False


#: Compound-list intros the label table did not know, met while deriving a row
#: (`_comp_block`); derive_row drains them into its advisory channel (`comp-intro-unknown`)
_COMP_UNKNOWN = []


def _find_nodes(article, type_):
    out = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type_") == type_:
                out.append(n)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(article.get("body"))
    return out


def _own_compound_lists(node):
    """The ``compound_list`` nodes a definition unit owns **directly** — excluding any inside a
    nested child definition, which belong to that subsense. ordbokene attaches each compound
    list to the (sub)sense it sits under (sak: ``gladsak, nyhetssak`` under sense 4;
    ``avholdssak, kvinnesak, målsak`` under sense 6), so ``comp`` is a per-unit field, not
    article-level — rendering only the first node article-wide orphaned the rest (Robin, as of
    card 82, 2026-07-18)."""
    out = []

    def walk(n, root):
        if isinstance(n, dict):
            if n.get("type_") == "definition" and not root:
                return  # a nested subsense owns its own compound lists
            if n.get("type_") == "compound_list":
                out.append(n)
            for v in n.values():
                walk(v, False)
        elif isinstance(n, list):
            for v in n:
                walk(v, root)
    walk(node, True)
    return out


def _comp_block(node, concepts=None):
    """One ``compound_list`` node → ``{label, intro, items}`` (each item's ``en`` authored
    later). ``intro`` is the capture's intro as plain text (``fill``ed; ``""`` where it has
    none), derived Norwegian like the items; ``label`` its English (``comp_label``, decisions
    151), ``""`` with no intro. A dangling compound is dropped from the enumeration (Robin,
    2026-07-14) — the list loses nothing, and ``link_marker``'s plain-text demotion would
    otherwise crash the ``[word](href)`` parse below."""
    node_intro = node.get("intro") or {}
    intro = fill(node_intro.get("content", "") or "", node_intro.get("items") or [],
                 concepts if concepts is not None else concepts_map())
    label, known = comp_label(intro)
    if not known:
        _COMP_UNKNOWN.append(intro)
    items = []
    for el in node.get("elements", []):
        if el.get("type_") == "article_ref":
            if int(el.get("article_id", -1)) in fetch.load_dangling():
                continue
            m = link_marker(el)  # "[word](href)"; word may carry a "(homograph, sense)"
            sep = m.rindex("](")  # split on the last "](" — the display can contain "(" (målmann (II))
            word = m[1:sep]
            href = m[sep + 2:-1]
            items.append({"word": word, "href": href, "en": None})
    return {"label": label, "intro": intro, "items": items}


def _comp(node, concepts=None):
    """A definition unit's comp: a list of blocks, one per ``compound_list`` it directly owns
    (mann's sense 1 owns both an *etterledd* and an *i ord som* list, different labels).
    Empty list when the unit owns none."""
    return [_comp_block(n, concepts) for n in _own_compound_lists(node)]


def iter_comp_items(row):
    """Every comp item ``{word, href, en}`` across a row's senses and subsenses, in document
    order — comp is per-unit now (``schemas.md`` § comp). The shared walk for merge, closure,
    the guardrails, and the authoring kit."""
    for s in row.get("senses") or []:
        for blk in s.get("comp") or []:
            for it in blk["items"]:
                yield it
        for sub in s.get("subs") or []:
            for blk in sub.get("comp") or []:
                for it in blk["items"]:
                    yield it


def _exprs(article):
    return [n.get("article_id") for n in _find_nodes(article, "sub_article")
            if n.get("article_id") is not None]


def _raw_ref_ids(article):
    """Every ``article_ref`` target id in a raw source (before derivation) — the R half of the
    closure, needed *up front* so each target's homograph is available when its links derive.

    **Does not descend into embedded ``sub_article`` bodies** (Robin, 2026-07-13): an embedded
    expression is derived from its own *standalone* source, and the two captures can diverge
    (advisory 11) — om II embeds ``om hverandre`` with a link to ``hulter til bulter`` that the
    standalone capture renders as plain text, so scanning the embedded copy pulled an id into
    the closure that no derived row ever links, an unfixable G3 orphan. Each sub_article is a
    C member in its own right (``_exprs``) and its refs enter R via ``_content_ref_ids`` on its
    standalone source, so stopping here loses nothing."""
    out = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get("type_") == "sub_article":
                return  # its refs come from the standalone source, not this embedded copy
            if n.get("type_") == "article_ref" and n.get("article_id") is not None:
                out.add(n["article_id"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(article.get("body"))
    return out


def _content_ref_ids(article):
    """Every ``article_ref`` target id in a raw source **outside** ``Se: …`` see-also
    explanations. Used for a **non-seed** closure member (an inlined expression), whose
    see-also line the parent's Fixed-expressions block does not render
    (``docs/rendering.md`` § Fixed expressions). Per-node, not a set subtraction: an id cited
    both in a ``Se:`` line and in real content stays referenced — the same semantics as
    ``referenced_ids(see_also=False)``'s per-segment skip, so ``check_library``'s G3
    recomputation always matches the derived closure."""
    out = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get("type_") == "explanation" and markup.is_see_also(n.get("content")):
                return  # markup.is_see_also matches both Se: and ordbokene's nynorsk Sjå:
            if n.get("type_") == "article_ref" and n.get("article_id") is not None:
                out.add(n["article_id"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(article.get("body"))
    return out


def ref_targets_with_lemmas(article, is_expr):
    """``{target_id: set(expected lemma strings)}`` for every ``article_ref`` in a raw
    source — the fetch-boundary view that feeds the renumber guard
    (``fetch.fetch_article_checked``). Skips embedded ``sub_article`` bodies (each is
    scanned via its own standalone source) and, for a fixed expression, its ``Se:``
    see-also explanations (see-line deferral, 2026-07-14)."""
    out = {}

    def walk(n):
        if isinstance(n, dict):
            if n.get("type_") == "sub_article":
                return
            if is_expr and n.get("type_") == "explanation" and markup.is_see_also(n.get("content")):
                return
            if n.get("type_") == "article_ref" and n.get("article_id") is not None:
                lems = set()
                for lem in n.get("lemmas") or []:
                    v = lem.get("lemma") if isinstance(lem, dict) else lem
                    if v:
                        lems.add(v)
                out.setdefault(int(n["article_id"]), set()).update(lems)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(article.get("body"))
    return out


def article_is_expr(article):
    """Whether a raw source is a fixed expression (POS-tag view; UnknownPOS → not)."""
    try:
        return postags.article_pos(article) == "fixed expression"
    except postags.UnknownPOS:
        return False


def ensure_expr_sources(article):
    """Materialize each of an article's expression sub-articles into ``sources/`` from its
    embedded copy when no standalone source exists — every expression is a first-class row
    and needs its own source file (Robin, 2026-07-12; ``docs/pipeline.md`` § Deriver §8)."""
    for node in _find_nodes(article, "sub_article"):
        emb = node.get("article")
        if isinstance(emb, dict) and emb.get("article_id") is not None:
            if fetch.load_source(emb["article_id"]) is None:
                # Prefer the standalone article (real EXPR tag + any of its own body);
                # fall back to the embedded copy when the id 404s (embedded-only exprs).
                fetch.fetch_article_or_embedded(int(emb["article_id"]), emb)


_ALT = _re.compile(r"\[([^\]]*\|[^\]]*)\]")


def _norm_lemma(form):
    """Expression lemmas carry ordbokene's ``[a|b]`` alternation syntax; ordbokene displays
    it as ``a/b`` (``[få|ha] fram`` → ``få/ha fram``)."""
    return _ALT.sub(lambda m: m.group(1).replace("|", "/"), form)


def _header(article):
    lemmas = []
    for lem in article.get("lemmas", []):
        form = lem.get("lemma")
        if not form:
            continue
        hg = lem.get("hgno") or 0
        lemmas.append({"form": _norm_lemma(form), "homograph": _roman(hg)})
    return lemmas


def _roman(hg):
    return {0: None, 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}.get(hg, str(hg))


# --- the row ----------------------------------------------------------------

def derive_row(aid, concepts, advisories, art=None):
    """The Norwegian side of one article's row (English slots all ``None``). ``art``
    overrides the committed-source lookup — author_kit's briefing passes its transient
    fetch so a read-only lookup never needs a ``sources/`` write."""
    if art is None:
        art = fetch.load_source(aid)
    if art is None:
        raise DeriveError("no source for article %s" % aid)
    try:
        pos = postags.article_pos(art)
    except postags.UnknownPOS as e:
        raise DeriveError("article %s: %s" % (aid, e))
    del _DEF_DANGLERS[:]  # link_marker records dangling `#def` anchors dropped in this row
    del _COMP_UNKNOWN[:]  # _comp_block records compound-list intros the label table lacks
    senses = _collect_senses(art)
    row = {"id": int(aid),
           "lemmas": _header(art),
           "pos_en": pos,
           # the head's lines, one per paradigm group, genders in the data's order (site
           # ruling 49: the library carries the order);
           # mechanical Norwegian like `lemmas`, regenerated on every derive
           "headwords": headwords.groups(art, pos, _norm_lemma),
           "etymology": _etymology(art, concepts),
           "senses": [_sense_row(s, i + 1, aid, concepts, advisories)
                      for i, s in enumerate(senses)],
           "exprs": _exprs(art)}
    if pos == "fixed expression":
        # The see line (site decisions 153, Robin 2026-10-30; the deferral of 2026-07-14
        # amended): a fixed expression's ``Se: …`` component line is kept OUT of ``no`` — so it
        # is never served to an author, never needs English, and never renders on a card
        # (embedded expressions drop it) — and kept instead in a mechanical field of its own,
        # ``see`` (Norwegian segments with their link markers, no English slot, present only
        # where the unit has one), which the site draws on the expression's standalone page.
        # Its targets never enter the library: `referenced_ids` does not read ``see``, and the
        # closure scans skip ``Se:`` explanations (``_content_ref_ids``), as before
        # (``docs/library.md`` § The closure). ``no``, ``en`` and parity are as under the
        # deferral: units are kept (defn numbering and subs untouched); a see-only unit is an
        # empty-parity pair (``no: []``, ``en: []`` — mechanical, not authored).
        for s in row["senses"]:
            for u in [s] + s["subs"]:
                see = [seg for seg in u["no"] if markup.is_see_also(seg)]
                u["no"] = [seg for seg in u["no"] if not markup.is_see_also(seg)]
                if not u["no"]:
                    u["en"] = []
                if see:
                    u["see"] = see
    assessed_def = fetch.load_dangling_def_assessed()
    for tgt, did in dict.fromkeys(_DEF_DANGLERS):  # dedup, order-preserving
        if (aid, tgt, did) in assessed_def:  # human-reviewed no-issue — stay silent (mirrors dangling-ref)
            continue
        advisories.append(("dangling-def", "%s cites %s#def%d, but %s has no such definition "
                           "(dangling definition_id in ordbokene's data; anchor + sense suffix "
                           "dropped, bare-href kept) — assess: python scripts/a8.py dangling-def "
                           "%s %s#def%d --note '…'" % (aid, tgt, did, tgt, aid, tgt, did)))
    del _DEF_DANGLERS[:]
    lemma = ((row["lemmas"] or [{}])[0] or {}).get("form", "")
    for intro in dict.fromkeys(_COMP_UNKNOWN):
        advisories.append(("comp-intro-unknown", "%s %s: compound-list intro %r is not in "
                           "derive.COMP_INTRO_LABELS — labelled %r; give it a label there "
                           "(site decisions 151), or correct a misspelling in the capture "
                           "(pipeline.md § Source normalization)"
                           % (aid, lemma, intro, COMP_UNKNOWN_LABEL)))
    del _COMP_UNKNOWN[:]
    return row


# --- closure (C ∪ R, depth one) ---------------------------------------------

_HREF = _re.compile(r"\]\(/nob/bm/(\d+)")


def referenced_ids(row, see_also=True):
    """Article ids the row's **derived Norwegian** cites — definition/etymology/example/comp
    links plus the row's own expression refs. This is the R half of the closure.

    ``see_also=False`` drops the targets of ``Se: …`` see-also segments — used when the row is
    reached as an *inlined* expression, whose see-also line the parent's Fixed-expressions block
    does not render (mirrors ``build_closure``'s seed/non-seed split so ``check_library``'s G3
    recomputation matches the derived closure)."""
    ids = set(row.get("exprs", []))

    def scan(s):
        for m in _HREF.finditer(s or ""):
            ids.add(int(m.group(1)))
    for seg in row["etymology"]["no"]:
        scan(seg)
    def scan_comp(unit):
        for blk in unit.get("comp") or []:
            for it in blk["items"]:
                scan("](%s)" % it["href"])
    for s in row["senses"]:
        for seg in s["no"]:
            if not see_also and markup.is_see_also(seg):
                continue
            scan(seg)
        for pair in s["ex"]:
            for x in ex_no(pair):       # the explanation cites too (`se [med (II)](…)`)
                scan(x)
        for e in s.get("ex_added") or []:
            scan(e["no"])
        scan_comp(s)
        for sub in s["subs"]:
            for seg in sub["no"]:
                if not see_also and markup.is_see_also(seg):
                    continue
                scan(seg)
            for pair in sub["ex"]:
                for x in ex_no(pair):
                    scan(x)
            for e in sub.get("ex_added") or []:
                scan(e["no"])
            scan_comp(sub)
    return ids


_FLAT_RE = _re.compile(r"^(\d+) def (\d+):")


def flattened_key(msg):
    """The ack key for a ``flattened-subsense`` advisory message (``article|defn``) — a source
    restructure that renumbers the defn refires it (`docs/guardrails.md` § Acknowledging a
    standing advisory). Shared by the deriver's own print filter and ``check_library``'s gate
    so both mute against the same registry entry."""
    m = _FLAT_RE.match(msg or "")
    return "%s|%s" % (m.group(1), m.group(2)) if m else None


def _unacked(advisories):
    """``advisories`` (``(tag, msg)`` tuples) minus those a human has acked as a reviewed
    standing no-issue (``fetch.load_advisory_acks``). Only classes with a defined key are
    ackable; everything else passes through, always shown."""
    keyers = {"flattened-subsense": flattened_key}
    out = []
    for a in advisories:
        tag = a[0] if isinstance(a, (tuple, list)) else None
        keyer = keyers.get(tag)
        key = keyer(a[1]) if (keyer and len(a) > 1) else None
        if key is not None and fetch.is_advisory_acked(tag, key):
            continue
        out.append(a)
    return out


def build_closure(seed_ids, concepts, advisories):
    """Derive the library for ``seed_ids`` (card articles): C = seeds + their inlined
    expressions, R = ids referenced from C's Norwegian, depth one (a mini's links never
    traverse — ``library.md`` § The closure). Returns ``{id: row}`` for C ∪ R."""
    rows = {}
    C = set()
    for aid in seed_ids:
        src = fetch.load_source(aid) or fetch.fetch_article(aid)
        ensure_expr_sources(src)
        C.add(int(aid))
        C |= set(_exprs(src))
    # R from a raw scan of C's sources — fetched *before* any derivation so that every link's
    # target article (and thus its homograph) is on disk when the link derives (deterministic
    # `_target_hgno`; otherwise re-derivation would depend on fetch order — guardrail 4).
    seed_set = {int(a) for a in seed_ids}
    R = set()
    for aid in C:
        src = fetch.load_source(aid)
        # A fixed expression's `Se:` see-also refs are never counted — its see-line is not
        # projected into `no` (see-line deferral, Robin 2026-07-14; previously a seed
        # expression kept them for its standalone-card view). Since site decisions 153
        # (2026-10-30) the line is kept in the unit's own `see` field for the site, whose
        # page resolves its links at build time; its targets still do not enter the library.
        # A non-expression seed keeps the full raw scan.
        R |= _raw_ref_ids(src) if (aid in seed_set and not article_is_expr(src)) \
            else _content_ref_ids(src)
    R -= C
    dangling = set()
    known_dangling = fetch.load_dangling()
    assessed_dangling = fetch.load_dangling_assessed()
    for aid in R:
        if aid in known_dangling:
            # Already recorded as a 404 in ordbokene's data — no network re-fetch (a dangling
            # target never lands on disk, so re-fetching it just re-404s every derive: churn +
            # noise). The advisory fires only until a human assesses it as a no-issue
            # (`a8.py dangling`), then stays silent — mirrors the A8 confirm registry.
            dangling.add(aid)
            if aid not in assessed_dangling:
                advisories.append(("dangling-ref", "referenced article %s: registered 404, "
                                   "unassessed — assess: python scripts/a8.py dangling %s "
                                   "--note '…'" % (aid, aid)))
            continue
        src = fetch.load_source(aid)
        if src is None:
            try:
                fetch.fetch_article(aid)
            except urllib.error.HTTPError as e:
                advisories.append(("dangling-ref", "NEW referenced article %s: HTTP %s — "
                                   "assess: python scripts/a8.py dangling %s --note '…'"
                                   % (aid, e.code, aid)))
                dangling.add(aid)
                fetch.mark_dangling(aid, "referenced from a card article but HTTP %s" % e.code)
                continue
        # No ensure_expr_sources here: an R member with senses is a *mini* that renders them
        # and never its own expressions — those sources have no consumer and were advisory
        # 14's one mechanical stray-producer (Fable review, 2026-07-13). A seed's exprs (the
        # rows that actually render) are materialized above. The senseless case is below.
    # A **senseless** R member's mini renders its expression rows instead of senses
    # (`mini._expr_block`, e.g. a DEF-less article like `si II`) — so those expressions
    # join the closure as rows (Robin, 2026-07-13). Their own references do NOT extend R:
    # the mini's links are hover-only, so the closure stays bounded.
    E2 = set()
    for aid in R - dangling:
        src = fetch.load_source(aid)
        if src is not None and not _collect_senses(src):
            ensure_expr_sources(src)
            E2 |= set(_exprs(src))
    E2 -= C | R
    for aid in C | (R - dangling) | E2:
        rows[aid] = derive_row(aid, concepts, advisories)
    return rows


# --- merge (refresh semantics: never overwrite authored English) ------------

DROPPED_EN = os.path.join(ROOT, "review", "dropped-english.jsonl")


def _archive_en(lost, aid, unit, why, old_no, old_en, new_no=None):
    """Record authored English the merge is about to lose.

    The deriver is the only tool besides ``promote.py --demote`` that destroys authored
    English, and until 2026-08-05 it was the only one that did so **without a copy** — a
    re-fetch that split one sense segment into two dropped the `en` to null and left the
    words nowhere but the terminal (Robin's ruling: keep the drop, archive first, as
    ``--demote`` already does). The drop itself is right: parity is a hard guardrail and a
    stale English segment aligned against the wrong Norwegian is worse than an empty slot.
    What was wrong was that re-authoring meant reconstructing from nothing.
    """
    if lost is None or not old_en:
        return
    lost.append({"id": aid, "unit": unit, "why": why,
                 "en": list(old_en), "no": list(old_no or []),
                 "new_no": None if new_no is None else list(new_no)})


def _archive_ex_added(lost, aid, unit, why, objs):
    """Record added example sentences (``ex_added``) the merge is about to lose — the
    ``_archive_en`` contract extended to the second authored class. Objects are archived
    verbatim: the authored Norwegian, its provenance and any authored English travel as
    one record, so re-landing after a capture repair is a copy, not a reconstruction."""
    if lost is None or not objs:
        return
    lost.append({"id": aid, "unit": unit, "why": why, "ex_added": list(objs)})


def _write_dropped(lost):
    """Persist the archive, de-duplicating an identical re-drop.

    Keyed by ``(id, unit, en)``, not by ``(id, unit)``: a unit whose English is dropped,
    re-authored, and dropped again must keep **both** records, while a re-run of the same
    derive over the same captures must not accumulate copies of one loss. ``ex_added``
    records carry no ``en`` list; their payload joins the key the same way.
    """
    if not lost:
        return 0
    def key(r):
        return (r["id"], r["unit"], " ".join(r.get("en") or []),
                json.dumps(r["ex_added"], ensure_ascii=False, sort_keys=True)
                if r.get("ex_added") else "")
    added, _replaced, _skipped = store.upsert_jsonl(DROPPED_EN, lost, key=key)
    return added


def _merge_segments(new_no, old_no, old_en, defn, aid, drift, lost=None):
    """Keep authored ``en`` when it still parity-matches the (possibly reworded) Norwegian;
    report a same-count content change (advisory 13); drop ``en`` on a count change —
    archiving it to ``review/dropped-english.jsonl`` first (``_archive_en``)."""
    if not new_no and defn != "ety":
        # a stripped see-only sense unit (see-line deferral, 2026-07-14): the empty-parity
        # pair is mechanical, not authored — always [], regardless of history, no drift
        # (an absent etymology stays en: null, its long-standing shape)
        return []
    if old_en is None:
        return None
    if len(old_en) != len(new_no):
        _archive_en(lost, aid, str(defn), "segment-count", old_no, old_en, new_no)
        drift.append(("segment-count", "%s def %s: en dropped (%d→%d segments) — archived to %s"
                      % (aid, defn, len(old_en), len(new_no),
                         os.path.relpath(DROPPED_EN, ROOT))))
        return None
    if old_no is not None and old_no != new_no:
        drift.append(("reworded", "%s def %s: Norwegian changed under authored en" % (aid, defn)))
        _report_stale_hrefs(new_no, old_en, defn, aid, drift)
    return old_en


_HREF_RE = _re.compile(r"\]\((/nob/bm/\d+(?:#def\d+)?)")


def _report_stale_hrefs(new_no, old_en, defn, aid, drift):
    """Name the authored-English links this rewording just stranded.

    A **ref-anchor source normalization is a two-part edit** and only the first part is
    mechanical: re-pointing a capture's `#defN` moves the derived Norwegian, but authored
    English is merge-only, so every citing segment keeps the pre-normalization href. The build
    then dies on link parity — one segment per rebuild cycle, because the error names the first
    it meets, so the four-reference normalization of 2026-08-09 cost four full rebuilds to
    discover four hrefs the deriver could see all at once.

    So say it here, where both sides are in hand: which href the English still carries and which
    the Norwegian now uses. Reporting only — **merge-only semantics do not change.** Guessing
    the re-point would be a tool rewriting authored English, which nothing in this pipeline does;
    the fix goes through `author_kit` like any other authored change."""
    if not old_en:
        return
    fresh = [_HREF_RE.findall(s or "") for s in new_no]
    for i, en in enumerate(old_en):
        if en is None or i >= len(fresh):
            continue
        for href in _HREF_RE.findall(en):
            if href in fresh[i]:
                continue
            # Prefer the same article's new anchor — a re-anchoring is the common case and its
            # replacement is unambiguous. A repoint to a different article (a homograph fix:
            # `moro`'s etymon `ro (I)` → `ro (II)`, 2026-08-09) has no such match, so fall back
            # to every link the segment now carries and let the author pick.
            same = [h for h in fresh[i] if h.split("#")[0] == href.split("#")[0]]
            drift.append(("stale-href",
                          "%s def %s segment %d: authored en still points at %s; the Norwegian "
                          "now links %s — re-point the en (author_kit) or the build will fail on "
                          "link parity"
                          % (aid, defn, i + 1, href,
                             ", ".join(same or fresh[i]) or "nothing")))


_TITLE_RE = _re.compile(r'(\[[^\]]*\]\(/nob/bm/\d+(?:#def\d+)?)\s+"[^"]*"(\))')


def strip_titles(s):
    """`[text](href "title")` → `[text](href)` — titles are authored, merge-owned."""
    return _TITLE_RE.sub(r"\1\2", s or "")


def _split_legacy(old_no, quote, expl):
    """Cut a legacy flattened `quote – explanation` string back in two, keeping each
    half's AUTHORED link titles with the half they belong to. Split by testing every
    join position against the title-stripped halves rather than by index, because
    titles make the two strings different lengths."""
    q_key, x_key = strip_titles(quote), strip_titles(expl)
    start = 0
    while True:
        i = old_no.find(EX_JOIN, start)
        if i < 0:
            return old_no, None
        head, tail = old_no[:i], old_no[i + len(EX_JOIN):]
        if strip_titles(head) == q_key and strip_titles(tail) == x_key:
            return head, tail
        start = i + 1


def _merge_examples(new_ex, old_ex, aid, drift, lost=None, unit=None):
    """Re-attach authored example English **and link titles** by **title-stripped verbatim
    Norwegian match** — an example's stored `no` may carry authored titles, which must not
    defeat the match against the freshly derived (untitled) text. Orphaned English or titles
    are **archived** (`_archive_en`) and reported, never dropped silently — the two orphan
    branches were the last drop paths without a copy, exposed when the `spilletid`
    normalization reworded an example's Norwegian (batch 4386-4663, entry 4)."""
    old_by_no = {}
    for old in (old_ex or []):
        no, en = old[0], old[1]
        # The old EXPLANATION rides along (2026-08-17): the migration's first
        # derive preserved explanation titles through the legacy branch, but a
        # non-legacy match only re-merged the QUOTE's titles — the stored
        # explanation was never indexed, so its authored titles dropped
        # silently on the SECOND full derive after the migration (caught by
        # the år-normalization trial diff: 10 rows, e.g. din's 'se stå'
        # see-tail).
        old_x = old[2] if len(old) > 2 else None
        if (en is not None or strip_titles(no) != no
                or (old_x is not None and strip_titles(old_x) != old_x)):
            old_by_no.setdefault(strip_titles(no), []).append((no, en, old_x))
    for pair in new_ex:
        expl = pair[2] if len(pair) > 2 else None
        bucket = old_by_no.get(strip_titles(pair[0]))
        legacy = False
        if not bucket and expl:
            # pre-2026-08-16 rows stored `quote – explanation` in ONE string, so the
            # quote alone will not match; without this the English of all ~116 such
            # examples would archive as orphaned on the first re-derive
            bucket = old_by_no.get(strip_titles(pair[0]) + EX_JOIN + strip_titles(expl))
            legacy = bool(bucket)
        if bucket:
            old_no, en, old_x = bucket.pop(0)
            if legacy:
                old_q, old_x = _split_legacy(old_no, pair[0], expl)
                pair[0] = _merge_titles([pair[0]], [old_q], aid, "ex", drift)[0]
                if old_x is not None:
                    pair[2] = _merge_titles([expl], [old_x], aid, "ex-expl", drift)[0]
            else:
                pair[0] = _merge_titles([pair[0]], [old_no], aid, "ex", drift)[0]
                if expl is not None and old_x is not None:
                    pair[2] = _merge_titles([expl], [old_x], aid, "ex-expl", drift)[0]
            if en is not None:
                pair[1] = en
    for _key, leftovers in old_by_no.items():
        for old_no, en, old_x in leftovers:
            if en is not None:
                _archive_en(lost, aid, unit, "orphan-example",
                            [x for x in (old_no, old_x) if x is not None], [en])
                drift.append(("orphan-example", "%s: example English orphaned by changed no: %r"
                              " — archived to %s"
                              % (aid, old_no, os.path.relpath(DROPPED_EN, ROOT))))
            elif (strip_titles(old_no) != old_no
                  or (old_x is not None and strip_titles(old_x) != old_x)):
                # the authored English here is the TITLES riding inside the Norwegian; the
                # titled strings are archived whole, under `en`, so nothing needs re-parsing
                _archive_en(lost, aid, unit, "orphan-title",
                            [x for x in (old_no, old_x) if x is not None],
                            [x for x in (old_no, old_x)
                             if x is not None and strip_titles(x) != x])
                drift.append(("orphan-title", "%s: example link titles orphaned by changed no: %r"
                              " — archived to %s"
                              % (aid, old_no, os.path.relpath(DROPPED_EN, ROOT))))


def _merge_titles(new_no_list, old_no_list, aid=None, where=None, drift=None):
    """Re-attach authored English title slots onto derived-Norwegian links by href, in
    positional order among duplicates of one href within a string. A title whose href no
    longer exists in the fresh derivation is **reported as drift, never dropped silently** —
    a title is authored English (advisory 13's "titles orphaned by a vanished link")."""
    if not old_no_list:
        return new_no_list
    old_titles = {}  # href -> [titles in order]
    tre = _re.compile(r"\[[^\]]*\]\((/nob/bm/\d+(?:#def\d+)?)\s+\"([^\"]*)\"\)")
    for s in old_no_list:
        for m in tre.finditer(s or ""):
            old_titles.setdefault(m.group(1), []).append(m.group(2))
    if not old_titles:
        return new_no_list
    link = _re.compile(r"(\[[^\]]*\]\()(/nob/bm/\d+(?:#def\d+)?)(\))")
    out = []
    for s in new_no_list:
        def repl(m):
            href = m.group(2)
            bucket = old_titles.get(href)
            if bucket:
                return "%s%s \"%s\"%s" % (m.group(1), href, bucket.pop(0), m.group(3))
            return m.group(0)
        out.append(link.sub(repl, s))
    if drift is not None:
        for href, leftovers in old_titles.items():
            for title in leftovers:
                drift.append(("orphan-title", "%s %s: authored title %r orphaned — link %s "
                              "gone from the fresh derivation" % (aid, where, title, href)))
    return out


def _archive_removed_unit(lost, drift, aid, unit):
    """Archive everything authored on a unit the fresh derivation no longer has: its
    ``en`` (the long-standing behaviour) and its ``ex_added`` objects verbatim. Also
    applied to removed *subs*, which previously lost their English with no copy — a gap
    against the never-destroy-without-a-copy rule, found while wiring ``ex_added``
    archival (2026-08-15)."""
    defn = str(unit["defn"])
    if unit.get("en"):
        _archive_en(lost, aid, defn, "removed-sense", unit.get("no"), unit["en"])
        drift.append(("removed-sense", "%s def %s removed; authored en was: %r — archived to %s"
                      % (aid, defn, unit["en"], os.path.relpath(DROPPED_EN, ROOT))))
    if unit.get("ex_added"):
        _archive_ex_added(lost, aid, defn, "removed-sense", unit["ex_added"])
        drift.append(("removed-sense", "%s def %s removed; %d added example(s) archived to %s"
                      % (aid, defn, len(unit["ex_added"]),
                         os.path.relpath(DROPPED_EN, ROOT))))


def merge_row(new_row, old_row, drift, lost=None):
    """Merge authored English from ``old_row`` into a freshly derived ``new_row`` — never
    overwriting authored slots, re-aligning by ``defn`` / href / verbatim example match.

    ``lost`` collects the English this merge could not re-attach, for the caller to archive
    (``_write_dropped``). Four things reach it: a segment-count change, a sense the fresh
    derivation no longer has, and an example whose changed Norwegian orphans its English or
    its authored link titles."""
    if old_row is None:
        return new_row
    # etymology
    o_ety = old_row.get("etymology", {})
    new_row["etymology"]["no"] = _merge_titles(new_row["etymology"]["no"], o_ety.get("no"),
                                               new_row["id"], "ety", drift)
    new_row["etymology"]["en"] = _merge_segments(new_row["etymology"]["no"], o_ety.get("no"),
                                                 o_ety.get("en"), "ety", new_row["id"], drift,
                                                 lost)
    # senses by defn
    old_senses = {s["defn"]: s for s in old_row.get("senses", [])}
    seen = set()
    for s in new_row["senses"]:
        os_ = old_senses.get(s["defn"])
        seen.add(s["defn"])
        if os_ is None:
            continue
        s["no"] = _merge_titles(s["no"], os_.get("no"), new_row["id"], "def %s" % s["defn"], drift)
        s["en"] = _merge_segments(s["no"], os_.get("no"), os_.get("en"), s["defn"],
                                  new_row["id"], drift, lost)
        s["idiom"] = os_.get("idiom")
        if os_.get("ex_added"):
            # ex_added is authored Norwegian with no capture behind it: never re-derived,
            # carried whole like `summary` — the deriver never writes or deletes it
            s["ex_added"] = os_["ex_added"]
        _merge_examples(s["ex"], os_.get("ex"), new_row["id"], drift,
                        lost, str(s["defn"]))
        old_subs = {sub["defn"]: sub for sub in os_.get("subs", [])}
        for sub in s["subs"]:
            osub = old_subs.get(sub["defn"])
            if osub is None:
                continue
            sub["no"] = _merge_titles(sub["no"], osub.get("no"),
                                      new_row["id"], "sub %s" % sub["defn"], drift)
            sub["en"] = _merge_segments(sub["no"], osub.get("no"), osub.get("en"),
                                        sub["defn"], new_row["id"], drift, lost)
            sub["idiom"] = osub.get("idiom")
            if osub.get("ex_added"):
                sub["ex_added"] = osub["ex_added"]
            _merge_examples(sub["ex"], osub.get("ex"), new_row["id"], drift,
                            lost, str(sub["defn"]))
        for sdefn in set(old_subs) - {sub["defn"] for sub in s["subs"]}:
            _archive_removed_unit(lost, drift, new_row["id"], old_subs[sdefn])
    for defn in set(old_senses) - seen:
        _archive_removed_unit(lost, drift, new_row["id"], old_senses[defn])
        for osub in old_senses[defn].get("subs", []):
            _archive_removed_unit(lost, drift, new_row["id"], osub)
    # comp English by href (comp is per sense/sub now; a compound's href is unique in an
    # article, so a global href map re-attaches authored glosses even if a re-fetch moves a
    # compound list to another sense)
    old_comp_en = {it["href"]: it["en"] for it in iter_comp_items(old_row) if it.get("en") is not None}
    legacy = old_row.get("comp")  # transition: rows authored under the row-level comp schema
    if isinstance(legacy, dict):   # (harmless once every row is re-derived per-sense)
        for it in legacy.get("items", []):
            if it.get("en") is not None:
                old_comp_en.setdefault(it["href"], it["en"])
    for it in iter_comp_items(new_row):
        it["en"] = old_comp_en.get(it["href"])
    # summary block (authored by the separate phase-4 batch agent, `summary.py`) — carried
    # whole; a re-fetch that rewords a pointed-at example surfaces via guardrail 18's
    # self-validating `ex` keys, and the article move itself via `summary.py stale`
    if old_row.get("summary") is not None:
        new_row["summary"] = old_row["summary"]
    return new_row


POSVAR = os.path.join(ROOT, "review", "pos-variants.jsonl")


def sync_pos_variants(lib_ids):
    """Keep ``review/pos-variants.jsonl``'s ``in_library`` snapshot mechanically true
    (Robin, as of card 70, 2026-07-17). The flag is pure derived state — "does this
    set-aside variant currently have a library row?" — and it changes exactly when the
    deriver moves the library (a variant enters as a mini the moment a live card's text
    reaches it: det III / herre II on card 64). Hand-flipping it per stint was a recurring
    chore advisory 12 kept flagging (cards 26/34/42/45/60/64), so the deriver now syncs it
    in the same pass, both directions. **Advisory 12 stays the independent from-disk
    verifier** — after this, a firing flag-staleness line means the sync itself broke,
    never routine drift. Runs only on the full-seed path — a scoped ``--ids`` run is a
    surgical tool and stays surgical, touching nothing it was not asked about. (Before
    2026-07-24 the reason was stronger: a scoped run *replaced* the library with its partial
    closure, so the flags would have been synced against a fraction of it. Scoped runs now
    merge, so this gate is deliberate conservatism rather than a correctness requirement.)
    The ``no_sense1``/``example`` snapshot is synced in the same pass (Robin, 2026-08-23):
    like ``in_library`` it is pure derived state — the seeder's own light projection of the
    capture — and after the `akutt` capture edit it was re-baselined by a hand-written script
    against a private helper, which produced exactly the silent mistake this sync removes
    (raw ``concepts.json`` passed where ``seed._concepts_map()`` belonged; the domain
    dropped without a sound). The captures are pinned, so a snapshot moves only when our own
    hand moved the source — but the old→new diff is PRINTED below, so the signal advisory 12
    used to carry survives as a visible line in the derive output rather than a chore.
    Preserves file order; no write when nothing changed."""
    rows = store.read_jsonl(POSVAR, missing_ok=True)
    if not rows:
        return
    import seed  # deferred: only this full-seed-path sync needs the seeder
    concepts = seed._concepts_map()
    flipped, rebased = [], []
    for r in rows:
        truth = r.get("id") in lib_ids
        if bool(r.get("in_library")) != truth:
            r["in_library"] = truth
            flipped.append("%s (%s) -> %s" % (r.get("id"), r.get("base_lemma"), truth))
        src = fetch.load_source(r.get("id"))
        if src is None:
            continue
        segs, ex = seed._project_sense1(src, concepts)
        if segs != (r.get("no_sense1") or []) or ex != r.get("example"):
            rebased.append("%s (%s): no_sense1 %r -> %r; example %r -> %r"
                           % (r.get("id"), r.get("base_lemma"),
                              r.get("no_sense1"), segs, r.get("example"), ex))
            r["no_sense1"], r["example"] = segs, ex
    if flipped or rebased:
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        store._atomic_write(POSVAR, text)
        if flipped:
            print("pos-variants in_library synced: " + "; ".join(flipped))
        for line in rebased:
            print("pos-variants snapshot re-baselined: " + line)


def merge_into_library(computed, existing, scoped):
    """The row set a derive writes.

    A **full** derive writes exactly the closure it computed: a row for a card that is no
    longer live is *meant* to disappear (that is how `prepare` releases over-budget
    candidates). A **scoped** derive (``--ids``) writes its computed rows **merged into** the
    existing library — it is a smaller *view* of the library, never a smaller library.

    Robin, 2026-07-24. Before this, both paths wrote only the computed rows, so
    ``derive.py --ids <one id>`` *replaced* `articles.jsonl` with that id's partial closure —
    a one-row fix silently deleted ~3000 rows. The second half of the damage is what makes it
    worth a named function: `merge_row` merges authored English out of the file it is
    rewriting, so the next **full** derive over the gutted file had nothing to merge from and
    the English went with the rows (5199 authored `en` -> 42). Recovery was only possible
    because `sources/` and `review/` are never touched by a derive.
    """
    if not scoped:
        return list(computed)
    computed_ids = {r["id"] for r in computed}
    return list(computed) + [r for i, r in existing.items() if i not in computed_ids]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", type=int, metavar="ID", help="derive one article id, print it")
    ap.add_argument("--ids", help="comma-separated card article ids to seed the closure — a "
                                  "SCOPED derive: the computed rows are merged into the "
                                  "existing library, every other row is left untouched")
    ap.add_argument("--out", default=ARTICLES, help="library file to merge into")
    args = ap.parse_args()
    # The closure loads a cited target's capture once per citer, not once per run —
    # the same repeat-read cost check_library carried (2026-08-10). derive reads
    # captures and never edits them, and the cache stores no misses, so a capture
    # fetched mid-run is still seen; process-lifetime cache is safe here.
    fetch.cache_sources()
    concepts = concepts_map()

    if args.only:
        import json
        adv = []
        try:
            row = derive_row(args.only, concepts, adv)
        except DeriveError as exc:
            # `--only` takes an ARTICLE id; a card key is the natural mis-read (the
            # full-suite audit, 2026-09-05, tried `--only 1` and got a traceback).
            raise SystemExit("derive: %s — `--only` takes an ARTICLE id, not a card key "
                             "(a card's ids are its `articles` list in cards.jsonl)" % exc)
        print(json.dumps(row, ensure_ascii=False, indent=1))
        for a in _unacked(adv):
            print("ADVISORY", a[0], a[1] if len(a) > 1 else "", file=sys.stderr)
        return

    if args.ids:
        seed = [int(x) for x in args.ids.split(",") if x.strip()]
    else:
        cards = store.read_jsonl(os.path.join(ROOT, "cards.jsonl"))
        seed = [a for c in cards if c.get("live") for a in c.get("articles", [])]

    adv, drift, lost = [], [], []
    rows = build_closure(seed, concepts, adv) if seed else {}
    if args.ids:
        # A scoped derive RE-DERIVES rows; it never EXTENDS the closure (Robin, 2026-08-24 —
        # ruled via Fable's review of the 3344-3884 batch notes § 1, observed twice with a
        # G3 consequence). `build_closure` treats every id as a seed, so an id naming a row
        # that is deck-wide only CITED pulled its own citations in as depth-two rows — G3
        # orphans on the next gate — and fetched out-of-universe captures on the way (the
        # A14 strays). Keep exactly the named ids plus rows the library already holds; a
        # dropped id has no live reader, and the deck-wide closure is the FULL derive's job.
        keep = set(seed) | {r["id"] for r in store.read_jsonl(args.out)} \
            if os.path.exists(args.out) else set(seed)
        dropped = sorted(set(rows) - keep)
        if dropped:
            print("scoped derive: dropped %d closure extension(s) with no library row: %s"
                  % (len(dropped), ", ".join(str(i) for i in dropped)))
        rows = {i: r for i, r in rows.items() if i in keep}
    # Under the library lock: this is a read-modify-write like every other merge here, and it
    # is the SLOWEST one — `build_closure` runs first, but the read + merge + write still spans
    # thousands of rows. `author_kit.author` has been locked since parallel stints landed
    # (2026-07-26); derive was not, because it historically ran BETWEEN stints. It no longer
    # does: a source repoint mid-batch (`gal II` → `feil II`, 2026-07-28) needs a re-derive
    # while four agents are merging, and an agent's write landing between this read and this
    # write would be discarded in silence — one card's English simply absent, with the file
    # still well-formed. `build_closure` stays OUTSIDE: it reads captures, not the library, and
    # holding the lock across it would stall every agent for the length of a full derive.
    with store.lock(args.out):
        existing = {r["id"]: r for r in store.read_jsonl(args.out)}
        merged = merge_into_library([merge_row(rows[i], existing.get(i), drift, lost)
                                     for i in rows],
                                    existing, scoped=bool(args.ids))
        # Archive INSIDE the lock and BEFORE the library write: if the process dies between
        # the two, the copy exists and the original still does too. The other order can lose
        # both.
        n_lost = _write_dropped(lost) if args.out == ARTICLES else 0
        store.write_jsonl(args.out, merged, key=lambda r: r["id"])
    if not args.ids and args.out == ARTICLES:
        sync_pos_variants({r["id"] for r in merged})
    # depth-two evidence net (Robin, 2026-07-14): every library row's link targets get a
    # committed source — pinned gloss evidence, offline stints, verifiable G5 anchors.
    # After the bulk prefetch (scripts/prefetch.py) this is normally a no-op; it exists so
    # a frontier advance can never reopen a network dependency mid-stint. Sources only —
    # never rows; the closure (G3) is untouched.
    dangling = fetch.load_dangling()
    fetched2 = 0
    for aid in sorted(rows):
        src = fetch.load_source(aid)
        if src is None:
            continue
        for tid, lemmas in ref_targets_with_lemmas(src, article_is_expr(src)).items():
            if tid in rows or tid in dangling or fetch.load_source(tid) is not None:
                continue
            try:
                fetch.fetch_article_checked(tid, lemmas)
                fetched2 += 1
            except urllib.error.HTTPError as e:
                adv.append(("dangling-ref", "depth-two target %s: HTTP %s" % (tid, e.code)))
                fetch.mark_dangling(tid, "depth-two evidence target but HTTP %s" % e.code)
            except fetch.LemmaMismatch as e:
                adv.append(("renumber-suspect", str(e)))
    if fetched2:
        print("fetched %d depth-two evidence source(s)" % fetched2)
    if args.ids:
        # Say what was WRITTEN, not just what was computed. The old line printed the computed
        # count alone ("derived 14 rows"), which read like ordinary progress output at the
        # exact moment the library was being replaced by those 14 rows.
        print("derived %d row(s) scoped by --ids (C∪R over %d seed(s)) and merged into %s — "
              "%d row(s) total, %d left untouched"
              % (len(rows), len(seed), args.out, len(merged), len(merged) - len(rows)))
    else:
        print("derived %d rows (C∪R over %d seeds) -> %s" % (len(merged), len(seed), args.out))
    for a in _unacked(adv):
        print("ADVISORY", a[0], a[1] if len(a) > 1 else "", file=sys.stderr)
    for d in drift:
        print("DRIFT", d[0], d[1], file=sys.stderr)
    if n_lost:
        print("ARCHIVED %d authored-English unit(s) the merge could not re-attach -> %s"
              % (n_lost, os.path.relpath(DROPPED_EN, ROOT)), file=sys.stderr)


if __name__ == "__main__":
    main()
