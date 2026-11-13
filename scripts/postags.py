#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parts of speech: the paradigm-tag → ``pos_en`` mapping, one source of truth.

``pos_en`` derives from the **union** of every ``lemmas[].paradigm_info[].tags`` on an
article — never the top-level ``word_class`` (often absent), and never a single lemma
(alternate spellings like ``en / én`` each carry their own paradigm). The table is
``docs/translation-conventions.md`` § Parts of speech; an **unknown tag set is a hard
error**, never a guessed label (``UnknownPOS``) — the deriver turns that into a crash, the
seeder into a reported per-note failure. Two named exceptions read ordbokene's own mis-tags
(Core Idea 6, site decisions 57, 2026-10-19): a set of gender tags alone is a noun of that
gender (124989), and the lone tag ``false`` is a fixed expression (104373 and three more).

Lives in its own module because the seeder needs it (POS-scoped card composition) a step
before the deriver, which reuses it for the row header.
"""


class UnknownPOS(Exception):
    """Raised when a paradigm-tag set matches no row of the pos_en table."""

    def __init__(self, tags):
        self.tags = sorted(tags)
        super().__init__("unrecognized POS tag set: %s" % self.tags)


_GENDER_TAGS = frozenset({"Masc", "Fem", "Neuter"})


def pos_en(tags):
    """Map a set of paradigm tags to the ``pos_en`` label. Raises ``UnknownPOS`` on a
    non-empty unrecognized set; an **empty** set is a fixed expression (only multiword
    expressions carry no inflection paradigm — every real word has at least one tag)."""
    t = set(tags)
    if not t:
        return "fixed expression"
    # ordbokene's mis-tags, corrected (Core Idea 6; site decisions 57, 2026-10-19). Both are
    # narrow on purpose — any other unknown set still raises:
    # * the string "false" as the ONLY tag: four EXPR articles (104373 piggene [ut|ute],
    #   125146, 125183, 125458) whose live page prints `tags.false` as the word class — its
    #   own bug; read as the empty set, which is what every other expression carries.
    if t == {"false"}:
        return "fixed expression"
    # * gender tags with no NOUN: 124989 jern- og metallindustri is tagged ['Masc'] alone;
    #   its paradigm is NOUN_regular and ordbokene shows "masculine" and a noun table.
    if t <= _GENDER_TAGS:
        t = t | {"NOUN"}
    if "PROPN" in t:
        return "proper noun"
    if "NOUN" in t:
        if "Uninfl" in t:
            return "noun (uninflected)"
        masc, fem, neu = "Masc" in t, "Fem" in t, "Neuter" in t
        if masc and fem:
            return "noun (masculine or feminine)"
        if masc:
            return "noun (masculine)"
        if fem:
            return "noun (feminine)"
        if neu:
            return "noun (neuter)"
        return "noun"
    if "VERB" in t:
        return "verb"
    if "ADJ" in t:
        return "adjective"
    if "ADV" in t:
        return "adverb"
    if "ADP" in t or "PREP" in t:
        return "preposition"
    if "PRON" in t:
        return "pronoun"
    if "DET" in t:
        if "Quant" in t:
            return "determiner, quantifier"
        if "Dem" in t:
            return "determiner, demonstrative"
        if "Poss" in t:
            return "determiner, possessive"
        return "determiner"
    if "SCONJ" in t:
        return "subordinating conjunction"
    if "CCONJ" in t or "CONJ" in t:
        return "conjunction"
    if "INTJ" in t:
        return "interjection"
    if "EXPR" in t:
        return "fixed expression"
    if "SYM" in t:
        return "symbol"
    if "ABBR" in t:
        return "abbreviation"
    if "PFX" in t or "COMPPFX" in t:
        return "prefix"  # eks- (PFX), kjempe- (COMPPFX) — seed-failure triage 2026-07-13
    raise UnknownPOS(t)


def article_tags(article):
    """Union of every paradigm tag across all of an article's lemmas."""
    tags = set()
    for lem in article.get("lemmas", []):
        for p in lem.get("paradigm_info", []):
            tags.update(p.get("tags") or [])
    return tags


def article_pos(article):
    """``pos_en`` for a whole article (union of all its lemmas' tags)."""
    return pos_en(article_tags(article))


# The UPOS bridge (2026-08-15, example-sentences build step 2): ordbokene's paradigm
# tags are already UPOS-shaped strings plus a few house extras; SpaCy tags lines with
# real UPOS. One mapping, here, so the evidence filter and the paradigm collision
# table can never disagree with pos_en about what class an article claims.
UPOS = {"NOUN", "VERB", "ADJ", "ADV", "ADP", "PRON", "DET",
        "SCONJ", "CCONJ", "INTJ", "PROPN", "SYM"}
_UPOS_ALIAS = {"PREP": "ADP", "CONJ": "CCONJ"}


def upos(tags):
    """The UPOS classes a tag set claims — empty for EXPR/ABBR/PFX-only articles."""
    out = set()
    for t in tags:
        if t in UPOS:
            out.add(t)
        elif t in _UPOS_ALIAS:
            out.add(_UPOS_ALIAS[t])
    return out


def article_upos(article):
    """UPOS classes for a whole article (union over its lemmas' paradigm tags)."""
    return upos(article_tags(article))


def article_hgno(article):
    """The article's homograph number (0 = none). Roman numeral rendering is elsewhere."""
    lemmas = article.get("lemmas", [])
    return max((lem.get("hgno") or 0) for lem in lemmas) if lemmas else 0


def article_lemma_forms(article):
    """All headword spellings the article lists (``en``, ``én`` for one article)."""
    return [lem.get("lemma") for lem in article.get("lemmas", []) if lem.get("lemma")]


def article_main_lemma(article):
    """The article's **main** headword — the first spelling it lists, which is the one
    ordbokene displays the entry under (``blive, bli`` is headed *blive*).

    The distinction matters when a word owns an article of its own *and* appears as a
    secondary spelling on another word's: card *bli* (18) resolved to both 6390 (*bli*) and
    6460 (*blive, bli*), and only the first is the *bli* entry (Robin, 2026-07-23).
    """
    forms = article_lemma_forms(article)
    return forms[0] if forms else None


def is_main_lemma(article, lemma):
    """Does ``article`` list ``lemma`` as its main headword? Case-insensitive, matching the
    seeder's existing lemma filter (a wordlist capital like *Sovjet* against ordbokene's
    lowercase *sovjet* is the same headword, tracked separately as a case mismatch)."""
    main = article_main_lemma(article)
    return main is not None and main.casefold() == (lemma or "").casefold()
