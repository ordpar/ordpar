# -*- coding: utf-8 -*-
"""A library row's headword groups — the lines an article's head prints (site ruling 49).

ordbokene prints one headword line per **paradigm group**, each with its own word-class line:
*anskaffelse* "noun (masculine)" over *anskaffing* "noun (masculine or feminine)"; *bru, bro*
one line, "noun (feminine or masculine)", the genders in the data's order. Robin ruled
(2026-10-17, site decisions 49) that the library carries that order: "I'd say we make the
library carry the order". `derive.py` writes it into each row as ``headwords``
(`docs/schemas.md` § articles.jsonl):

    "headwords": [{"forms": [{"form": "bru", "homograph": null},
                             {"form": "bro", "homograph": null}],
                   "pos_en": "noun (feminine or masculine)"}]

This module is the one definition of the grouping and the wording, and the one reader:

* ``groups(article, fallback_pos)`` — the field from a capture's ``lemmas`` (`derive.py` calls
  it; ``article`` is a `sources/` capture or a mirror row's ``data``, the same shape);
* ``lines(row)`` — the head's lines from a library row alone, in the shape the site's
  `ordpar/sitegen/article.py` `lemma_groups` returns, ``[([(form, homograph), …], pos), …]``,
  so the deck builder and, later, the site can read the row instead of the mirror.

**The rule, as the site states it** (`lemma_groups`, `site_pos`; the parity test
`tests/test_headwords.py` pins the two equal over every live card article): the group key is a
lemma's paradigm-tag set (the union over its ``paradigm_info[].tags``) plus the order its
genders first appear in; groups come in the lemmas' order, and forms inside one keep it. The
label is `postags.pos_en` of the group's tags, with a noun's genders named in the data's order
("masculine, feminine or neuter" for all three), a genderless noun "noun (uninflectable)" when
tagged ``Uninfl`` and "noun" otherwise, ordbokene's "subjunction" for the subordinating
conjunction, and "compound prefix" for a ``COMPPFX`` group (*kjempe-*), which `pos_en` folds into
"prefix" (site decisions 152's follow-up, Robin 2026-11-01: one word everywhere). A tag set
`pos_en` cannot name takes the article's own label.

**The spelling order** (the four lemma-order rulings in `review/source-normalizations.jsonl`,
e.g. *tørre, tore*) is in the committed captures already — each ruling edited its capture — so
the field derived from `sources/` is in our order, and the site's `lemma_order.reorder` is a
no-op on it (measured by the parity test).

Standard library only; imports nothing but `postags`, so `derive.py` can import it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postags  # noqa: E402

KEY = "headwords"

GENDERS = {"Masc": "masculine", "Fem": "feminine", "Neuter": "neuter"}

#: Whole labels in ordbokene's words where `postags.pos_en` (the deck's table) differs
#: (site decisions 76) — the site's `article._SITE_WORDS`, restated.
SITE_WORDS = {"subordinating conjunction": "subjunction",
              "noun (uninflected)": "noun (uninflectable)"}

_ROMAN = {0: None, 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}


def roman(hg):
    """``hgno`` as the row writes it (`derive._roman`)."""
    return _ROMAN.get(hg, str(hg))


def site_label(pos):
    """A whole `pos_en` label in ordbokene's words."""
    return SITE_WORDS.get(pos, pos)


def label(tags, genders):
    """One group's word-class line. Raises `postags.UnknownPOS` as `pos_en` does."""
    pos = postags.pos_en(tags)
    if pos == "prefix" and "COMPPFX" in set(tags) and "PFX" not in set(tags):
        return "compound prefix"     # the site's `article.site_pos`, restated
    if pos == "noun" or pos.startswith("noun ("):
        words = [GENDERS[g] for g in genders]
        if len(words) == 3:
            return "noun (masculine, feminine or neuter)"
        if words:
            return "noun (%s)" % " or ".join(words)
        return "noun (uninflectable)" if "Uninfl" in set(tags) else "noun"
    return site_label(pos)


def groups(article, fallback_pos, norm=lambda s: s):
    """The ``headwords`` field from a capture. ``fallback_pos`` is the article's own
    `pos_en`, used (in ordbokene's words) for a group whose tags `pos_en` cannot name;
    ``norm`` is the deriver's form normalizer (`derive._norm_lemma`). Lemmas with no form are
    skipped, as `derive._header` skips them."""
    order, by_key = [], {}
    for lem in (article or {}).get("lemmas") or []:
        form = lem.get("lemma")
        if not form:
            continue
        tags, genders = set(), []
        for par in lem.get("paradigm_info") or []:
            for t in par.get("tags") or []:
                tags.add(t)
                if t in GENDERS and t not in genders:
                    genders.append(t)
        key = (frozenset(tags), tuple(genders))
        if key not in by_key:
            by_key[key] = []
            order.append(key)
        by_key[key].append({"form": norm(form), "homograph": roman(lem.get("hgno") or 0)})
    out = []
    for key in order:
        try:
            pos = label(key[0], key[1])
        except postags.UnknownPOS:
            pos = site_label(fallback_pos or "")
        out.append({"forms": by_key[key], "pos_en": pos})
    return out


def lines(row):
    """The head's lines from the row alone: ``[([(form, homograph|None), …], pos), …]``.
    A row derived before the field existed gives its ``lemmas`` as one line under its own
    ``pos_en`` in ordbokene's words — what the site prints with no mirror row."""
    hw = row.get(KEY)
    if hw is None:
        forms = [(l.get("form", ""), l.get("homograph") or None) for l in row.get("lemmas") or []]
        return [(forms, site_label(row.get("pos_en", "")))]
    return [([(f["form"], f.get("homograph") or None) for f in g["forms"]], g["pos_en"])
            for g in hw]
