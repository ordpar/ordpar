#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the site's client-side lookup index, in shards, and copy the search shell.

    python ordpar/build_index.py --mirror "$(python ordpar/local_paths.py mirror)" --out ordpar/out
    python ordpar/build_index.py --mirror data/bokmalsordboka/bm-articles.jsonl   # public repository, ORDBOK_DATA_DIR=data
    python ordpar/build_index.py --out ordpar/out --verify            # query the built index, no rebuild
    python ordpar/build_index.py --mirror ... --out ... --limit 5000  # a fast partial build for a smoke test

Reads TWO sources and writes only under ``--out``:

* the **mirror** (`bm-articles.jsonl`, one raw ordbokene article per line) — every headword and
  every non-null inflected ``word_form`` becomes a *form* pointing at the article's id;
* the **library** (`articles.jsonl`) — an article counts as *translated* on the site iff
  ``coverage.complete_strict`` holds for its row (`scripts/coverage.py`).

Search covers ordbokene's LISTED articles (`bm-listed.jsonl`) plus the unlisted ones the site
KEEPS — translated library rows no translated listed article shares a headword with — and no
other unlisted article (decisions 46; ``search_scope``, ``sitegen.mirror.Listing``).

Output (format of record: `ordpar/docs/lookup-index.md`):

    out/index/<shard>.json     one shard per initial letter of the case-folded form; the five
                               big letters (b f k s t) split again by the second: s-k.json, ...
    out/index/<l>-top.json     a split letter's first 50 headwords (one-character autocomplete)
    out/index/headwords/<l>.json  every distinct headword form, sorted, one file per letter
                               (the similar-words pass), each with its frequency band
    out/index/tails/<k2>-<k3>.json  the same headwords filed by their 2nd and 3rd characters
                               (similar words past the first letter, decisions 55 / 56)
    out/index/snip/<k1>-<k2>-<k3>.json  the list view's one-line snippets, filed by a
                               headword's first three characters (site decisions 59), from build_site.py's
                               ordpar/.build/build-snippets.json — so build the articles first
    out/index/translated.json  the sorted ids that are translated today (the translated tags)
    out/index/random.json      the Random word's pool (decisions 115): the headwords whose
                               search shows FIRST an article that meets decisions 67's bar
                               (translated, not a set phrase, a summary gloss), sorted
    out/index/random-en.json   Random word's English pool (site decisions 155): how many words
                               each English file holds that the suggestions offer
                               (``english_random``); the words themselves are the files' own
    out/index/index.json       the manifest: counts, shard list, raw and gzip sizes
    out/bm-en/index.html       the search page (from site/search.html, strings inlined)
    out/404.html               the same shell as the 404 handler (from site/404.html)
    out/favourites/index.html  the favourites page, out/history/index.html the history page
                               (site decisions 60; from site/favourites.html, site/history.html)
    out/settings/index.html    the settings page (decisions 63; from site/settings.html)
    out/index.html             a front page — ONLY if the article build has not written one

The pages load `/site/lookup.js`, `/site/shell.js`, `/site/shell.css` — `ordpar/site/` as the
article build copies it to `out/site/`; this script copies none of them.

Forms are stored **as they are spelled** and folded at query time (decisions 25 (1)): the
distinction *PR* / *pr* is real and the saving from folding on disk is nil. The shard key is
the first character of ``bare(form)`` — ``form.lower()`` with accents folded, so *én* lives
with *e* (decisions 41 (a)); for b f k s t the second character too — ``lower()``, not
``casefold()``, so that Python and JavaScript agree on which file a query loads. Accents fold
one way at query time: *en* finds *én*, *én* does not find *en* (``bare``, ``accent_match``).

Headwords in ordbokene's alternation notation (``[få|sette] ræva i gir``) are stored as their
variants (``få ræva i gir``, ``sette ræva i gir``), each pointing at the same article — the
bracket notation is never a key (decisions 39; ``variants``).

``--freq`` (optional) names the National Library's "N-grams 2026" books list (Bokmål, 1990 on,
CC0) as a 1-gram file; only a frequency band per headword is written, never the list (decisions
55; ``article_freq``, ``headword_bands``, ``form_band``). ``--freq-overrides`` is the overrides
registry, ``ordpar/freq-overrides.tsv`` by default (``read_overrides``). With ``--freq``, each
inflected form's articles are stored most common first by E2 (site decisions 143: ``form_share``,
``form_order``); ``--form-overrides`` is the exceptions file, ``ordpar/form-order-overrides.tsv``
by default (``read_form_overrides``), applied after E2 with or without ``--freq``.

Read-only outside ``--out``. No network, no install; stdlib only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html as html_mod
import itertools
import json
import os
import random
import re
import shutil
import sys
import time
import unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import coverage  # noqa: E402  -- complete_strict: the translated gate (decisions 27)
from ordpar.sitegen import mirror as mirror_mod  # noqa: E402  -- decisions 46: Listing
from ordpar.sitegen import lemma_order  # noqa: E402  -- decisions 93 (2): our lemma order
from ordpar.sitegen import head as head_mod  # noqa: E402  -- decisions 61: noindex, app manifest
from ordpar.sitegen import chrome as chrome_mod  # noqa: E402  -- decisions 63: the header, the footer
from ordpar.sitegen import about as about_mod  # noqa: E402  -- decisions 128: the home page's count
from ordpar.sitegen import describe as describe_mod  # noqa: E402  -- decisions 128
from ordpar.sitegen import colours as colours_mod  # noqa: E402  -- decisions 63: the colour schemes
from ordpar.sitegen import wordpages as wordpages_mod  # noqa: E402  -- decisions 117: word pages
from ordpar.sitegen import slim as slim_mod  # noqa: E402  -- decisions 61: no comments published

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # pragma: no cover - a non-reconfigurable stream
        pass

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
MISC_SHARD = "misc"
SPECIAL_SHARDS = {"æ": "ae", "ø": "oe", "å": "aa"}
# the letters whose shard is split by the second folded character (decisions 39)
SPLIT_LETTERS = ("b", "f", "k", "s", "t")
# headwords in a split letter's `<letter>-top.json`, the one-character autocomplete file
TOP_HEADS = 50
GZ = 9

# Marks the stand-in front page this build writes while the article build has none.
PLACEHOLDER = "<!-- ordpar: placeholder front page, written by build_index.py -->"

# The standard smoke-test set (the build brief, 2026-09-20).
TEST_QUERIES = ["hus", "husene", "Be", "be", "rapp", "torde", "hause", "bru",
                "trøtte", "ferskvannsfisk"]


# --------------------------------------------------------------------------- #
# shared with lookup.js — keep the two in step
# --------------------------------------------------------------------------- #

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def fold(s: str) -> str:
    """Query-time folding. ``lower()`` on NFC text — what JS ``toLowerCase()`` does."""
    return nfc(s).lower()


# Accent folding (decisions 41 (a), 2026-10-18): what the reader types WITHOUT an accent
# matches a form WITH one (en -> én, a la carte -> à la carte), one way only, as ordbokene.
# A character folds to its base letter when it decomposes (NFD) into an ASCII letter followed
# only by combining marks U+0300-U+036F: à ä ç è é ê î ò ô ü in today's mirror. æ ø å are
# letters of Norwegian, never accented letters, and never fold (å decomposes, so it is
# listed); ø and æ do not decompose. The fold is one character for one character, so a
# folded string and its bare form have the same length and align position by position.
KEEP = frozenset("æøå")
_PLAIN = re.compile(r"[^\x00-\x7fæøå]")


def bare_char(c: str) -> str:
    """One FOLDED (lower-case) character without its accent: é -> e, ü -> u; æ ø å, ASCII
    and everything that is not a letter plus combining marks are returned unchanged."""
    if c < "\x80" or c in KEEP:
        return c
    d = unicodedata.normalize("NFD", c)
    if len(d) > 1 and "a" <= d[0] <= "z" and all(0x300 <= ord(m) <= 0x36F for m in d[1:]):
        return d[0]
    return c


def bare(s: str) -> str:
    """``fold(s)`` with every accent folded away (``bare_char``) — the key forms are matched,
    sharded and compared on. ``bare("À la carte") == "a la carte"``; ``bare("bør") == "bør"``."""
    f = fold(s)
    if not _PLAIN.search(f):
        return f
    return "".join(bare_char(c) for c in f)


def accent_match(q: str, w: str) -> bool:
    """Does folded query ``q`` match folded form ``w`` over ``q``'s length, one way? Each
    character of ``q`` must equal ``w``'s, or be that character's bare letter: *en* matches
    *én*, *én* does not match *en*. The caller has already checked the bare forms agree."""
    for a, b in zip(q, w):
        if a != b and a != bare_char(b):
            return False
    return len(w) >= len(q)


def letter_key(form: str) -> str:
    """The first-letter bucket of a form: its first BARE character (a-z, ae/oe/aa, misc), so
    *én* is filed with *e* (decisions 41 (a)). The headwords files are split by this key; so
    were all shards before 2026-10-18."""
    c = bare(form)[:1]
    if not c:
        return MISC_SHARD
    if "a" <= c <= "z":
        return c
    if c in SPECIAL_SHARDS:
        return SPECIAL_SHARDS[c]
    return MISC_SHARD


def shard_key(form: str) -> str:
    """Which shard file a form lives in: its letter key, and for the five big letters
    (``SPLIT_LETTERS``) the second bare character too — ``s-k``, ``s-oe``, ``s-misc``
    (no second character, or one outside a-z/æøå)."""
    key = letter_key(form)
    if key not in SPLIT_LETTERS:
        return key
    c = bare(form)[1:2]
    if c and "a" <= c <= "z":
        return key + "-" + c
    if c in SPECIAL_SHARDS:
        return key + "-" + SPECIAL_SHARDS[c]
    return key + "-" + MISC_SHARD


def suggest_key(prefix: str) -> str:
    """Which file an autocomplete prefix reads: its own shard, except a ONE-character prefix
    on a split letter, which reads ``<letter>-top`` (that letter's first TOP_HEADS headwords
    in suggestion order) instead of every sub-shard."""
    p = fold(prefix)
    if len(p) == 1 and letter_key(p) in SPLIT_LETTERS:
        return letter_key(p) + "-top"
    return shard_key(p)


def merge_articles(rows: list) -> list:
    """One suggestion per article (site decisions 82, Robin 2026-10-21 -- a deliberate
    divergence: ordbokene suggests per form). ``rows`` are the ranked per-form suggestions, each
    with its ``ids``; a row leading to ONE article takes in every later row leading to that same
    article, keeping its place and ``word`` (the best-ranked form) and listing the merged forms
    in ``forms``. A form several articles share keeps its own row and never merges into an
    article's, so the search showing them all stays on offer. lookup.js ``mergeArticles``."""
    out, by_id = [], {}
    for r in rows:
        if len(r["ids"]) != 1:
            out.append(r)
            continue
        i = r["ids"][0]
        if i in by_id:
            by_id[i]["forms"].append(r["word"])
            continue
        r["forms"] = [r["word"]]
        by_id[i] = r
        out.append(r)
    return out


def case_distance(q: str, w: str) -> int:
    """Capitalisation as a small distance (decisions 55, Robin 2026-10-19): the query AS TYPED
    against a form as written, position by position over the shorter of the two — each pair of
    cased characters whose case differs counts 1 (``us`` / ``UT`` 2, ``us`` / ``ut`` 0, ``US`` /
    ``UT`` 0, ``u`` / ``U`` 1). Only ever a tie-breaker, never an edit. lookup.js
    ``caseDistance``."""
    n = 0
    for a, b in zip(nfc(q), nfc(w)):
        if a.lower() != a.upper() and b.lower() != b.upper() and (a != a.lower()) != (b != b.lower()):
            n += 1
    return n


def suggest_order(w: str, prefix: str = ""):
    """The autocomplete order for ``prefix`` (what lookup.js does), as ordbokene's suggest
    API answers (2026-10-18, `ordpar-site-review/evidence/unlisted-46-2026-10-18/`): the
    continuations reached only through the accent fold — the form's own first letters differ
    from the typed ones — come after every other match; each group by length, then folded,
    then by capitalisation against the prefix as typed (``case_distance``), then folded, then as
    spelled. So *e* never reaches *én*, and *kafe* lists every *kafe-* word before
    *kaféliv*; but a form equal to the prefix keeps its place (*en* offers *en*, *én*, *ene*),
    and so does a continuation whose typed letters match as spelled (*kaf* offers *kafe*,
    *kafé*, *kaffe* … *kafkask*, *kaféliv*)."""
    p = fold(prefix)
    later = len(bare(w)) > len(p) and fold(w)[:len(p)] != p
    # within one length, the forms closest in capitalisation to the prefix AS TYPED first
    # (decisions 55, Robin 2026-10-19): u offers u before U, U offers U before u
    return (later, len(w), case_distance(prefix, w), fold(w), w)


# The similar-headwords limits (decisions 39 follow-up, Robin 2026-10-18): one edit per
# SIMILAR_PER characters, scaled to the length of what is compared — lookup-index.md § 4.
SIMILAR_PER = 3


def letter_limit(n: int) -> int:
    """Edits allowed between a whole query of ``n`` characters and a candidate: n // 3, at
    least 1 (``bro`` 1, ``skole`` 1, ``venskap`` 2, a 20-letter compound 6)."""
    return max(1, n // SIMILAR_PER)


def word_limit(n: int) -> int:
    """Edits allowed inside ONE word of an expression, for the word-by-word match: n // 3, with
    no floor — a word of one or two letters (``i``, ``en``, ``på``) must match exactly."""
    return n // SIMILAR_PER


def words_limit(m: int) -> int:
    """Words an ``m``-word query may differ from a candidate by: m // 3, at least 1."""
    return max(1, m // SIMILAR_PER)


def same_word(a: str, b: str) -> bool:
    """Do query word ``a`` and candidate word ``b`` count as the same word?"""
    if a == b:
        return True
    lim = word_limit(len(a))
    return lim > 0 and osa(a, b, lim) <= lim


def shared_words(qw: list, cw: list) -> int:
    """The most words ``qw`` and ``cw`` have in common IN ORDER (a longest common
    subsequence, with ``same_word`` as the equality)."""
    k = len(cw)
    prev = [0] * (k + 1)
    for a in qw:
        cur = [0] * (k + 1)
        for j in range(1, k + 1):
            cur[j] = prev[j - 1] + 1 if same_word(a, cw[j - 1]) else max(prev[j], cur[j - 1])
        prev = cur
    return prev[k]


# --------------------------------------------------------------------------- #
# decisions 55 (Robin, 2026-10-18/19): spelling suggestions past the first letter
# --------------------------------------------------------------------------- #

# (1) Norwegian spelling-variation rules, applied to the BARE query (on a miss and, since
# decisions 56, on a hit alike). Our own table
# of the orthography's variation (lookup-index.md § 4 (3), every rule with an example), not a
# word list. Each entry is ``(from, to, where, not_after)``: ``where`` is ``start`` (at the
# start of a word), ``end`` (at its end), ``inner`` (each occurrence not at a word's end, one
# rewrite per occurrence), ``any`` (each occurrence on its own, one rewrite per
# occurrence) or ``all`` (every occurrence at once, one rewrite — the keyboard rules: a reader
# without the letter writes all of them the same way); ``not_after`` is a character the match
# may not follow (``kj`` inside ``skj`` is the ``skj`` rule's). Kept in step with lookup.js
# ``RULES``.
RULES = (
    # hv ↔ k, hv ↔ v, word-initially: kordan → hvordan, kem → hvem, vem → hvem, hvalp → valp
    ("hv", "k", "start", ""), ("hv", "v", "start", ""),
    ("k", "hv", "start", ""), ("v", "hv", "start", ""),
    # kv ↔ hv word-initially, the Nynorsk and dialect spelling (added 2026-10-19): kvilken → hvilken
    ("kv", "hv", "start", ""), ("hv", "kv", "start", ""),
    # kj ↔ sj ↔ skj: sjære → skjære, kjorte → skjorte, forsjell → forskjell
    ("kj", "sj", "any", "s"), ("kj", "skj", "any", "s"), ("sj", "kj", "any", ""),
    ("sj", "skj", "any", ""), ("skj", "kj", "any", ""), ("skj", "sj", "any", ""),
    # tj ↔ kj word-initially: kjære → tjære, tjole → kjole
    ("tj", "kj", "start", ""), ("kj", "tj", "start", ""),
    # gj ↔ hj ↔ j word-initially: jerne → gjerne, jem → hjem, gjul → jul
    ("gj", "hj", "start", ""), ("gj", "j", "start", ""), ("hj", "gj", "start", ""),
    ("hj", "j", "start", ""), ("j", "gj", "start", ""), ("j", "hj", "start", ""),
    # the keyboard rules: aa ↔ å, ae ↔ æ, oe ↔ ø (paa → på, aere → ære, oel → øl)
    ("aa", "å", "all", ""), ("å", "aa", "all", ""), ("ae", "æ", "all", ""),
    ("æ", "ae", "all", ""), ("oe", "ø", "all", ""), ("ø", "oe", "all", ""),
    # the dialect æ (decisions 56, Robin 2026-10-19): word-final æ ↔ eg (dæ → deg, mæ → meg,
    # sæ → seg, jæ → jeg), and æ ↔ e anywhere in a word but its end (kæm → kem, and chained
    # with k → hv: kæm → kem → hvem)
    ("æ", "eg", "end", ""), ("eg", "æ", "end", ""),
    ("æ", "e", "inner", ""), ("e", "æ", "inner", ""),
    # loanword spellings Norwegian has respelt (added 2026-10-19, one way): cafe → kafe,
    # cigar → sigar, photograf → fotograf, thema → tema, taxi → taksi, quality → kvalitet
    ("c", "k", "any", ""), ("c", "s", "any", ""), ("ph", "f", "any", ""),
    ("th", "t", "any", ""), ("x", "ks", "any", ""), ("qu", "kv", "any", ""),
)
# single ↔ double consonants (venskap → vennskap, takk → tak): each run of one of these
# letters, of length one or two, is doubled or made single — one rewrite per run
DOUBLING = frozenset("bdfgklmnprstv")
# the most rewrites one query gets: the single rewrites in generation order, then the chained
# ones (decisions 56) — a long word has many consonants and many e's
MAX_REWRITES = 40
_WORD_EDGE = " -"


def _overlaps(i: int, j: int, spans) -> bool:
    return any(i < b and a < j for a, b in spans)


def _rewrite_once(q: str, avoid=()) -> list:
    """Every single-rule rewrite of ``q`` as ``(rewrite, spans)``, ``spans`` the ``[start, end)``
    stretches of the rewrite that the rule wrote. A match that touches a stretch of ``avoid``
    (the stretches an earlier rule wrote into ``q``) is skipped, so a chained second rule never
    rewrites what the first one wrote (*kordan* → *hvordan* → *vordan* would be a third rule,
    *k* → *v*, and an undo is no rewrite at all). lookup.js ``rewriteOnce``."""
    out = []
    n = len(q)
    for frm, to, where, not_after in RULES:
        L, T = len(frm), len(to)
        if where == "all":
            pos = []
            i = q.find(frm)
            while i != -1:
                pos.append(i)
                i = q.find(frm, i + L)
            if pos and not any(_overlaps(p, p + L, avoid) for p in pos):
                out.append((q.replace(frm, to),
                            [(p + k * (T - L), p + k * (T - L) + T) for k, p in enumerate(pos)]))
            continue
        i = q.find(frm)
        while i != -1:
            ok = not (not_after and i > 0 and q[i - 1] == not_after)
            if where == "start" and i > 0 and q[i - 1] not in _WORD_EDGE:
                ok = False
            if where == "end" and i + L < n and q[i + L] not in _WORD_EDGE:
                ok = False
            if where == "inner" and (i + L >= n or q[i + L] in _WORD_EDGE):
                ok = False
            if ok and avoid and _overlaps(i, i + L, avoid):
                ok = False
            if ok:
                out.append((q[:i] + to + q[i + L:], [(i, i + T)]))
            i = q.find(frm, i + 1)
    i = 0
    while i < n:
        c = q[i]
        j = i
        while j < n and q[j] == c:
            j += 1
        if c in DOUBLING and not (avoid and _overlaps(i, j, avoid)):
            if j - i == 1:
                out.append((q[:i] + c + q[i:], [(i, i + 2)]))
            elif j - i == 2:
                out.append((q[:i] + q[i + 1:], [(i, i + 1)]))
        i = j
    return out


def rewrites(q: str) -> list:
    """The spelling-variation rewrites of a BARE query (decisions 55 (1), 56): each rule of
    ``RULES`` applied once (``all``: every occurrence at once), then single ↔ double
    consonants; then, chained (decisions 56, capped at two), a second rule applied to each of
    those, never over what the first one wrote (``_rewrite_once``). Single rewrites before
    chained ones, deduplicated, never ``q`` itself, at most ``MAX_REWRITES``. lookup.js
    ``rewrites`` must give the same list in the same order."""
    seen, res, singles = {q}, [], []
    for r, spans in _rewrite_once(q):
        if r and r not in seen:
            seen.add(r)
            res.append(r)
            singles.append((r, spans))
    for r, spans in singles:
        if len(res) >= MAX_REWRITES:
            break
        for r2, _ in _rewrite_once(r, spans):
            if r2 and r2 not in seen:
                seen.add(r2)
                res.append(r2)
    return res[:MAX_REWRITES]


def char_key(c: str) -> str:
    """One BARE character's key: a-z, ae/oe/aa, misc (also for no character)."""
    if c and "a" <= c <= "z":
        return c
    if c in SPECIAL_SHARDS:
        return SPECIAL_SHARDS[c]
    return MISC_SHARD


def tail_key(form: str) -> str:
    """(2) The ``tails/`` file a headword lives in: the keys of its second and third BARE
    characters — the folded word without its first character, sharded by that remainder's
    first two letters (``hus`` -> ``u-s``, ``bus`` -> ``u-s``, ``ål`` -> ``l-misc``, ``i``
    -> ``misc-misc``). A search for *vus* reads ``tails/u-s`` (a wrong first letter) and
    ``tails/v-u`` (a missing one)."""
    b = bare(form)
    return char_key(b[1:2]) + "-" + char_key(b[2:3])


def remainder_key(s: str) -> str:
    """The ``tails/`` file whose headwords' remainder starts with ``s``'s first two
    characters: ``remainder_key("us") == tail_key("hus")``."""
    return char_key(s[0:1]) + "-" + char_key(s[1:2])


# (2) Frequency: the National Library of Norway's "N-grams 2026", books, Bokmål, 1990 on (CC0;
# decisions 55, switched from Språkbanken's sbr-12 on 2026-10-20; docs/licensing.md § Frequency
# lists). An article's frequency is the sum of the counts of its forms (headwords and paradigm
# forms), each distinct case-folded form once; by default a form other articles share counts
# only where it is the article's own headword (``article_freq``, with decisions 55's three fixes).
# A headword string's band follows ``form_band``'s rules. Shipped as a band, never as counts.
BAND_STEP = 1.75     # log2 units per band: one band ≈ a factor of 3.4
MAX_BAND = 15
HEX = "0123456789abcdef"

#: The list view's snippet (site decisions 59) is cut to this many characters, at a word
#: boundary, with "…": a row shows one line (CSS cuts it again to the row's width), and every
#: character is paid for in `snip/` (lookup-index.md § 3, § 5). 80 measured 2026-10-19.
SNIPPET_MAX = 80
#: What the article build leaves for this one: `{"<id>": [text, lang]}`, uncut
#: (`build_site.py` `write_snippets`) — outside `out/`, in the gitignored `ordpar/.build/`,
#: since it is a build by-product and `out/` is what gets published (2026-10-19). The same
#: path as `build_site.py` `SNIPPETS_PATH`; `--snippets` overrides it.
SNIPPETS_FILE = "build-snippets.json"
SNIPPETS_PATH = os.path.join(ROOT, "ordpar", ".build", SNIPPETS_FILE)


def homograph_order(a: dict):
    """The sort key of the articles under one form, as ordbokene's results (site decisions 59
    (1), measured 2026-10-19): verbs first, in homograph-number order, then every other
    article in number order whatever its word class (*fange* III verb, I, II; *stille* IV, V,
    I, II, III); an unnumbered article keeps its place before the numbered ones; the id breaks
    a tie. ``a`` has ``hg``, ``pos`` (the index's first paradigm tag, ``VERB`` for a verb) and
    ``id``. lookup.js ``homographOrder``."""
    rank = 0 if not a["hg"] else (1 if a.get("pos") == "VERB" else 2)
    return rank, a["hg"], a["id"]


def shard_bands(shard: dict) -> dict:
    """A shard's or ``-top`` file's ``n`` read back: ``{headword: band}`` — one hex digit per
    headword, aligned with the headwords sorted (by code point; lookup.js sorts the same keys
    by UTF-16 unit, the same order for every headword in the mirror, none of which is outside
    the BMP). lookup.js ``prepare``."""
    n = shard.get("n") or ""
    return {w: int(n[i], 16) for i, w in enumerate(sorted(shard["heads"])) if i < len(n)}


def suggest_rank(w: str, prefix: str, translated: bool, band_: int):
    """The autocomplete's sort key (brief 59b items 13 and 14, Robin 2026-10-19 — deliberate
    divergences from ordbokene's length-then-alphabet): rank 0 the exact match (the bare
    prefix), 1 the translated one-word headwords, 2 the Norwegian-only ones, 3 the set phrases
    (a headword with a space), 4 the continuations reached only through the accent fold (last
    as before, decisions 41/46); ranks 1 and 2 by frequency band, highest first (``band_``, from
    ``headword_bands``); then ``suggest_order``, the present order, for everything else and every
    tie. ``translated``: any article ``w`` heads is. lookup.js ``rankSuggestions``."""
    order = suggest_order(w, prefix)
    if bare(w) == bare(fold(prefix)):
        rank = 0
    elif order[0]:
        rank = 4
    elif " " in w:
        rank = 3
    else:
        rank = 1 if translated else 2
    return (rank, -band_ if rank in (1, 2) else 0) + order


def result_order(a: dict):
    """The results' order for one form (brief 59b item 12, Robin 2026-10-19): the translated
    articles first, then the untranslated, each group in ``homograph_order``. ``a`` also has
    ``translated``. lookup.js ``resultOrder``."""
    return (0 if a.get("translated") else 1,) + homograph_order(a)


def form_word(w: list) -> str:
    """The word an article belongs to, for ``form_order``'s groups: the first spelling its headword
    line shows (``words`` entry, " …" dropped), so every homograph of one spelling is one word
    (*vare* I, III and IV; *en, én* II and *en* III), the session's reading of 2026-10-27."""
    return ((w or [""])[0] or "").replace(" …", "").split(SEP)[0]


def form_order(ids, words: dict, translated, freq: dict | None = None, first=()) -> list:
    """The order of the articles under one INFLECTED form, as the index stores them in
    ``forms`` (site decisions 143, Robin 2026-10-26: "purely sort it based on frequency"; the
    measure E2, his choice of 2026-10-27; and, the same day, "if multiple headwords with the
    same lemma are showing, I think they should follow the same ordering as the normal list
    view"): the articles are grouped by their word (``form_word``); **the words** go most common
    first, a word's figure the sum of its articles' ``freq`` (the ``form_share`` figure: each
    spelling's count in NB's 2026 books shared out among every article that has it, by their
    example sentences + 1) — not ``article_freq``'s, never the band — a tie by the word's
    first article in ``result_order``; **within a word** the list view's order,
    ``result_order`` (translated first, then ``homograph_order``: verbs in number order, then the
    rest in number order). ``first``: the ids the exceptions file names for this form
    (``read_form_overrides``), in its order: each lifts its whole word ahead of the rest, the
    word keeping its own order inside (Robin, 2026-10-27: "within one word the list view's order
    wins"); an id not among ``ids`` is ignored. Without ``freq`` (or with no figure at all) the
    order is ``result_order``'s alone, as before 143, the exceptions still applied as above.
    Translated first therefore no longer leads across words; a query's own headword rows
    (``heads``) keep ``result_order``. Every reader keeps the stored order (``Index.lookup``,
    lookup.js ``group``)."""
    freq = freq or {}
    tr = translated if isinstance(translated, (set, frozenset)) else set(translated)

    def rkey(i):
        w = words.get(i) or ["", 0, ""]
        return result_order({"id": i, "hg": form_hg(w, ""), "pos": w[2] if len(w) > 2 else "",
                             "translated": i in tr})
    got = sorted(set(ids), key=rkey)
    groups = {}
    for i in got:                                        # each word's articles in result_order
        groups.setdefault(form_word(words.get(i)), []).append(i)
    if any(freq.get(i, 0) for i in got):
        order = sorted(groups.values(), key=lambda g: (-sum(freq.get(i, 0) for i in g), rkey(g[0])))
    else:
        order = None
    lead = []
    for i in first or ():
        if i in got and i not in lead:
            lead.extend(j for j in groups[form_word(words.get(i))] if j not in lead)
    if order is None:
        return lead + [i for i in got if i not in lead]
    return lead + [i for g in order for i in g if i not in lead]


def snippet_text(text: str, limit: int = SNIPPET_MAX) -> str:
    """``text`` on one line, cut to at most ``limit`` characters at a word boundary (the last
    space past half the limit, else mid-word), trailing punctuation dropped and "…" appended
    when cut. ``limit`` None or 0: uncut."""
    text = " ".join((text or "").split())
    if not limit or len(text) <= limit:
        return text
    cut = text[:limit - 1]
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:·") + "…"


def read_snippets(path: str) -> dict:
    """The article build's snippets, ``{id: (text, lang)}`` — or ``(text, lang, drop)`` where
    the autocomplete's text is not the snippet's first unit (a translated set phrase with no
    summary gloss: its set-phrase box, or "" for nothing; site decisions 60, brief item 7(b) as
    amended); empty when the file is absent (the list view then shows its rows without a
    snippet)."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {int(k): tuple(v[:5]) for k, v in json.load(fh).items()}


def snippet_key(form: str) -> str:
    """The ``snip/`` file a headword's snippets live in (site decisions 59): the keys of its
    first THREE bare characters — ``hus`` -> ``h-u-s``, ``en`` -> ``e-n-misc``, ``ta seg i
    akt`` -> ``t-a-misc``. Measured 2026-10-19 against one file per shard: 3,838 files instead
    of 135, and a list-view search reads 2–7 KB gzip instead of 14–95 KB. lookup.js
    ``snipKey``."""
    b = bare(form)
    return char_key(b[0:1]) + "-" + char_key(b[1:2]) + "-" + char_key(b[2:3])


def snippet_files(heads: dict, snippets: dict, translated, limit=SNIPPET_MAX, words=None):
    """``{snippet key: {"<id>": snippet}}`` over every headword form in ``heads`` (the shard
    tables): each file holds the articles whose headword falls under its key — what a list row
    shows — an English snippet cut by ``snippet_text``, a Norwegian one whole (site decisions
    185: the hover shows a Norwegian definition whole, and the rows cut a line to their width). A query and every form it can match share a
    key (the key is of the bare form, and an accent match needs equal bare forms). Every key
    with a headword has a file, ``{}`` where none of its articles has a snippet. Also
    returns ``(missing, mismatched)``: headword articles with no snippet, and snippets whose
    language is not the one the browser will mark — ``en`` for a translated article, ``nb``
    otherwise.

    A snippet with a third element (``drop``, the autocomplete's own text for a translated set
    phrase with no summary gloss) also lands in the file's ``"_d"`` map, ``{"<id>": drop}`` —
    its set-phrase box, which the dropdown reads in place of the snippet's first unit (shell.js
    ``glossText``), or ``""`` where it has none, which every reader takes as "no box" and so
    shows the snippet's first unit after all (site decisions 60, brief item 7(b) as amended,
    Robin 2026-10-19; its "else nothing" amended by site decisions 82, A13 point 3, Robin
    2026-10-21 — fixed in the readers, shell.js ``glossText``, lookup.js ``dropRule``,
    personal.js ``dropText``, so stored favourites and cached files follow too); the list view
    never looks at it.

    A snippet with a fourth element (site decisions 116: true where the snippet is the summary
    gloss, `article.snippet_is_gloss`) puts its id, an integer, in the file's ``"_g"`` list —
    what the rows set semibold (lookup.js ``isGloss``); an English definition line, a
    Norwegian one and a set-phrase box stay regular, and a file with no ``"_g"`` marks none.

    A snippet with a fifth element (site decisions 152: a TRANSLATED article's first Norwegian
    definition, uncut — `build_site.py` `write_snippets`, `article.snippet_nb`) lands in the file's
    ``"_n"`` map, uncut: ``{"<id>": text}`` for every translated article of the file,
    ``""`` where it has none — what the rows and the hovers show under Norwegian only with the
    English equivalents hidden (lookup.js ``nbDef``: an untranslated article's own line is its
    Norwegian definition). Every file that holds an article carries ``"_n"``, ``{}`` where none
    of its articles is translated, so a reader tells a file built before 152 (no ``"_n"``: no
    Norwegian definition for a translated article, never its English in its place).

    With ``words`` (the shards' ``words`` table; site decisions 144) each file also carries
    ``"_h"``: ``{form: ids}`` for every headword under its key with at least one snippet in the
    file — the ids of the articles the form heads in the results' order (``result_order``,
    translated first), a lone id as an integer, several as ``[[id, hg], …]``, ``hg`` the number
    of the spelling (``form_hg``) — so a similar headword's row after a miss finds its articles'
    snippets in this one file, with no shard (shell.js ``similarArticles``)."""
    tr = set(translated)
    out, seen = defaultdict(dict), set()
    missing = mismatched = 0
    for key in sorted(heads):
        for form, ids in heads[key].items():
            k = snippet_key(form)
            # every key a headword has gets its file, empty if none of its articles has a
            # snippet: the list view asks for the file only on a headword hit, and a hit then
            # never asks for a file that is not there (2026-10-19, site decisions 59)
            out[k]
            for i in ids:
                got = snippets.get(i, ("", ""))
                text, lang = got[0], got[1]
                if i not in seen:
                    seen.add(i)
                    missing += not text
                    mismatched += bool(text) and (lang == "en") != (i in tr)
                if text:
                    # site decisions 185: a Norwegian line is kept whole (the hover shows it
                    # whole; Robin: no definition is "so long that it makes sense to cut them
                    # off"); an English one is cut, since only the one-line rows read it
                    out[k][str(i)] = text if lang == "nb" else snippet_text(text, limit)
                    # site decisions 152: the translated articles' first Norwegian definitions
                    nmap = out[k].setdefault("_n", {})
                    if i in tr:
                        nb = got[4] if len(got) > 4 and got[4] else ""
                        nmap[str(i)] = nb
                if len(got) > 2 and got[2] is not None and i in tr:
                    out[k].setdefault("_d", {})[str(i)] = snippet_text(got[2], limit)
                # site decisions 116: the articles whose snippet is the summary gloss, which
                # the rows set semibold (lookup.js `isGloss`) — ids, in order, each once
                if text and len(got) > 3 and got[3] and i in tr:
                    g = out[k].setdefault("_g", [])
                    if i not in g:
                        g.append(i)
            if words is not None and any(str(i) in out[k] for i in ids):
                arts = sorted(
                    ({"id": i, "hg": form_hg(words.get(i) or ["", 0, ""], form),
                      "pos": (words.get(i) or ["", 0, ""])[2], "translated": i in tr}
                     for i in set(ids)), key=result_order)
                out[k].setdefault("_h", {})[form] = (
                    arts[0]["id"] if len(arts) == 1 else [[a["id"], a["hg"]] for a in arts])
    return dict(out), missing, mismatched


def band(n: int) -> int:
    """A count as a small integer: 0 = unseen, then 1 + log2(n) / 1.75, at most 15
    (1 → 1, 100 → 4, 10,000 → 8, 1,000,000 → 12, 42M — *i* — → 15)."""
    if n <= 0:
        return 0
    import math
    return min(MAX_BAND, 1 + int(math.log2(n) / BAND_STEP))


def read_freq(path: str, wanted: set) -> dict:
    """``{folded form: count}`` from a 1-gram file in Språkbanken's shape (ISO-8859-1, one
    ``count form`` per line, case-sensitive — NB's 2026 list as converted to it, whose forms
    are all lower case) — only the forms in ``wanted``, case variants summed."""
    counts = defaultdict(int)
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            line = line.strip()
            sp = line.find(" ")
            if sp <= 0:
                continue
            w = fold(line[sp + 1:].strip())
            if w in wanted:
                try:
                    counts[w] += int(line[:sp])
                except ValueError:
                    continue
    return counts


# The scale (decisions 55, round 2's "nb-scaled", built 2026-10-20): NB's books list counts
# 14.45 times the tokens of sbr-12, on which BAND_STEP and the bands were calibrated (*i* 15,
# *hus* 11). Dividing by the ratio of the two lists' token sums keeps a band meaning what it
# meant: NB's converted list sums 18,873,584,692 tokens, sbr-12 1,306,199,192 without its
# <s> and </s> (round 1, `ordpar-site-review/evidence/nb-ngram-55-2026-10-19/`). sbr-12 itself
# is no longer read; only its token sum survives, in this constant.
NB_TOKENS = 18_873_584_692
SBR12_TOKENS = 1_306_199_192
FREQ_SCALE = NB_TOKENS / SBR12_TOKENS     # ≈ 14.449


def scaled_band(count: int, scale: float = FREQ_SCALE) -> int:
    """``band`` of a count on NB's scale: ``band(max(1, round(count / scale)))`` above 0, so a
    form NB counts at all is band 1 or higher; 0 for unseen."""
    return band(max(1, round(count / scale))) if count > 0 else 0


# The rules for a headword STRING (decisions 55: round 3's "nb-scaled-own-list" and the fixes
# ruled beside it; ``form_band``). They take no input from any list but the one source.
#: (1) a single letter or digit — the alphabet's letters are headwords, and NB counts them as
#: page apparatus and initials; the lowest counted band, so a letter never outranks a counted
#: word at the same distance and case. The registry spares the two that are words (*å*, *i*).
SINGLE_BAND = 1
#: (2) an abbreviation: the whole string is letter groups, each closed by a full stop (*fl.*,
#: *dr.*, *bl.a.*, *f.eks.*); a digit, a space, a hyphen or "…" anywhere spares it (*17. mai*,
#: *ph.d.-kandidat*). It takes its scaled count held between ABBR_FLOOR and ABBR_CEILING; the
#: floor applies whether or not NB counts the string, since NB's tokeniser loses many (*Co.*).
#: The ceiling is 2, so the band is 2, round 3's: ceilings of 4, 5 and 6 were measured
#: (2026-10-20) and none brings *pr.* or *f.* back for *pr*, *f* — *f.*'s own scaled band is 7,
#: under *fe* and *fr* at 9; *pr.*'s is 10, level with *or* — so the brief's rule kept band 2
#: (`ordpar/docs/lookup-index.md` § 4 (3); Robin rules on it).
ABBR_RE = re.compile(r"^(?:[^\W\d_]+\.)+$")
ABBR_FLOOR = 2
ABBR_CEILING = 2
#: (3) the word classes of an article that is only a symbol or an abbreviation: one that shares
#: a form, case-folded, with an article of another class (*Og* oganesson / *og*, *Be* beryllium /
#: *be*) takes no count from that form and falls to the abbreviation band — NB's list has no
#: capital letters, so case cannot tell them apart (``symbol_shared``).
SYMBOL_CLASSES = frozenset({"SYM", "ABBR"})
#: The overrides registry (decisions 55: "word, band, why"; ours, CC BY; Robin rules on each
#: entry): a committed file a person reads, so not code (``read_overrides``).
OVERRIDES_PATH = os.path.join(ROOT, "ordpar", "freq-overrides.tsv")
#: ``article_freq``'s fixes to the ``own`` rule (decisions 55, 2026-10-20), all on in a build:
#: ``accent`` (a plain spelling beside its accented headword, ``accent_twins``), ``agent`` (the
#: verb counts the present form its agent noun shares, ``agent_forms``), ``symbol`` (above).
FREQ_FIXES = ("accent", "agent", "symbol")


def is_single(form: str) -> bool:
    return len(form) == 1 and form.isalnum()


def is_abbr(form: str) -> bool:
    return bool(ABBR_RE.match(form))


def read_overrides(path: str) -> dict:
    """The overrides registry: ``{form: band}``, ``band`` an int 0-15 or ``"nb"`` (keep NB's
    scaled count). A TSV: the header ``form<TAB>band<TAB>why``, then one line per form (the
    form as spelled, matched exactly); a line starting with ``#`` is a comment and a blank line
    is skipped. A malformed line, a band out of range, an empty reason or a form listed twice
    raises ``ValueError`` naming the file and the line number."""
    out = {}
    header = False
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.startswith("#"):
                continue
            cells = line.split("\t")
            where = "%s:%d" % (path, n)
            if not header:
                if cells != ["form", "band", "why"]:
                    raise ValueError("%s: the header must be 'form<TAB>band<TAB>why', got %r"
                                     % (where, line))
                header = True
                continue
            if len(cells) != 3:
                raise ValueError("%s: %d tab-separated fields, not 3: %r"
                                 % (where, len(cells), line))
            form, b, why = cells[0], cells[1].strip(), cells[2].strip()
            if not form or form != form.strip():
                raise ValueError("%s: the form is empty or padded: %r" % (where, form))
            if b == "nb":
                val = "nb"
            elif b.isdigit() and 0 <= int(b) <= MAX_BAND:
                val = int(b)
            else:
                raise ValueError("%s: band %r is neither 0-%d nor 'nb'" % (where, b, MAX_BAND))
            if not why:
                raise ValueError("%s: no reason given for %r" % (where, form))
            if form in out:
                raise ValueError("%s: %r is listed twice" % (where, form))
            out[form] = val
    if not header:
        raise ValueError("%s: no header line" % path)
    return out


def article_facts(data: dict) -> tuple:
    """What the fixes read of one article's paradigms: ``(classes, present, masc_plural)`` —
    the first tag of each paradigm (``NOUN``, ``VERB``, ``SYM`` …); the folded active present
    forms of its verb paradigms (a cell tagged ``Pres`` with no passive tag); the folded
    indefinite plurals of its masculine noun paradigms (``NOUN`` + ``Masc``, a cell tagged
    ``Plur`` and ``Ind``)."""
    classes, pres, mplur = set(), set(), set()
    for lemma in data.get("lemmas") or []:
        for para in lemma.get("paradigm_info") or []:
            tags = para.get("tags") or []
            if not tags:
                continue
            classes.add(str(tags[0]))
            verb = tags[0] == "VERB"
            masc = tags[0] == "NOUN" and "Masc" in tags
            if not (verb or masc):
                continue
            for cell in para.get("inflection") or []:
                wf, ct = cell.get("word_form"), cell.get("tags") or []
                if not (isinstance(wf, str) and wf.strip()):
                    continue
                if verb and "Pres" in ct and not any("Pass" in t for t in ct):
                    pres.add(fold(wf.strip()))
                elif masc and "Plur" in ct and "Ind" in ct:
                    mplur.add(fold(wf.strip()))
    return frozenset(classes), frozenset(pres), frozenset(mplur)


def read_facts(path: str) -> dict:
    """``{article id: article_facts}`` over the mirror. An article search keeps from a stored
    or embedded copy (``search_scope``) is not in it; it gets no fix that reads paradigms."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                out[row.get("id")] = article_facts(row.get("data") or {})
    return out


def _classes(e, facts) -> frozenset:
    got = facts.get(e[0]) if facts else None
    return got[0] if got else frozenset({e[3]} - {""})


def accent_twins(entries) -> dict:
    """``{article id: {folded spelling}}`` — an article's headword spelling that is the
    accent-folded form (``bare``) of another of its own headwords and is also a headword of
    another article: *for* beside *fôr* (the preposition's), *alle* beside *allé*, *og* beside
    *òg*. Under ``own`` such a spelling does not count for the article (decisions 55, the first
    mapping artefact). Homographs are untouched: those that share their only spelling (*fly* I,
    II), and those that share both (*fôring* I, II; *provencalsk* noun and adjective) — another
    article that lists the same accented twin does not count as the plain spelling's owner."""
    heads_of = {e[0]: {fold(w) for w in e[1]} for e in entries}
    head_owners = defaultdict(set)
    for aid, hs in heads_of.items():
        for h in hs:
            head_owners[h].add(aid)
    out = {}
    for aid, hs in heads_of.items():
        got = set()
        for h in hs:
            accented = {h2 for h2 in hs if h2 != h and bare(h2) == h}
            if accented and any(not (heads_of[o] & accented) for o in head_owners[h] - {aid}):
                got.add(h)
        if got:
            out[aid] = got
    return out


def agent_forms(entries, facts) -> dict:
    """``{verb article id: {folded form}}`` — a verb's present form that is also the headword
    of a masculine noun whose indefinite plural is that form + "e" (*skriver* → *skrivere*: the
    agent-noun paradigm). The verb counts the form as well; the noun keeps it (Robin,
    2026-10-20: for such forms the verb is what is meant, as ordbokene lists verbs first). The
    paradigm guard keeps it off *sukker* ← *sukke* (a neuter), *lager* ← *lage* (another
    plural): the *toe* ← *to* case the ``own`` rule exists for."""
    agent = defaultdict(set)      # folded noun headword -> the noun ids with that paradigm
    for e in entries:
        f = facts.get(e[0])
        if not f or not f[2]:
            continue
        for w in e[1]:
            h = fold(w)
            if h + "e" in f[2]:
                agent[h].add(e[0])
    out = {}
    for e in entries:
        f = facts.get(e[0])
        if not f or "VERB" not in f[0]:
            continue
        got = {p for p in f[1] if agent.get(p, set()) - {e[0]}}
        if got:
            out[e[0]] = got
    return out


def symbol_shared(entries, facts) -> dict:
    """``{article id: {folded form}}`` — an article whose every word class is a symbol or an
    abbreviation (``SYMBOL_CLASSES``), and the forms it shares, case-folded, with a form an
    article of another class spells in LOWER case: an ordinary word, whose count NB's
    capital-less list cannot tell from the symbol's (*Og* / *og*, *Be* / *be*, *NOK* / *nok*).
    A form an article of another class spells only with capitals is not a word's: *km* stays
    the unit's, though a noun *KM* exists. An article with no class at all is neither."""
    other, sym = set(), {}
    for e in entries:
        cls = _classes(e, facts)
        if cls and cls <= SYMBOL_CLASSES:
            sym[e[0]] = {fold(f) for f in list(e[1]) + list(e[4])}
        elif cls:
            other |= {f for f in list(e[1]) + list(e[4]) if f == fold(f)}
    return {aid: fs & other for aid, fs in sym.items() if fs & other}


FREQ_SHARED = ("own", "each")


def article_freq(entries, freq_path: str, stats: dict, shared: str = "own",
                 counts: dict | None = None, facts: dict | None = None,
                 fixes=FREQ_FIXES) -> dict:
    """``{article id: count}`` — the sum over the SET of the article's case-folded forms, each
    distinct form once (*hus* fills two cells in each of two paradigms and counts once).

    ``shared`` is the rule for a form several articles have (the orchestrator, 2026-10-19;
    Robin rules on the default):

    * ``own`` (the default, Robin 2026-10-19) — an article counts its own headword(s) as
      written, plus only the forms no other article has: *toe* does not inherit *to*'s count
      through its imperative *to*, nor *frukte* *frukt*'s;
    * ``each`` (the setting as first specified, kept behind ``--freq-shared each``) — a shared
      form counts for each of the articles that have it.

    ``fixes`` (decisions 55, 2026-10-20; ``FREQ_FIXES``): under ``own``, ``accent`` drops a
    plain spelling beside an accented headword (``accent_twins``) and ``agent`` adds to a verb
    the present form its agent noun shares (``agent_forms``); under either rule, ``symbol``
    drops the forms a symbol or abbreviation shares with a word (``symbol_shared``). ``agent``
    and ``symbol`` read ``facts`` (``read_facts``) and do nothing without it.

    ``counts`` (``{folded form: count}``) skips re-reading the list when both are measured."""
    forms_of = {e[0]: {fold(f) for f in list(e[1]) + list(e[4])} for e in entries}
    wanted = set().union(*forms_of.values()) if forms_of else set()
    if counts is None:
        counts = read_freq(freq_path, wanted)
    stats["freq_forms_wanted"] = len(wanted)
    stats["freq_forms_found"] = len(counts)
    fixes = set(fixes or ())
    if shared == "own":
        owners = defaultdict(int)
        for fs in forms_of.values():
            for f in fs:
                owners[f] += 1
        heads_of = {e[0]: {fold(w) for w in e[1]} for e in entries}
        if "accent" in fixes:
            twins = accent_twins(entries)
            for aid, fs in twins.items():
                heads_of[aid] -= fs
            stats["freq_fix_accent_articles"] = len(twins)
        forms_of = {aid: {f for f in fs if owners[f] == 1 or f in heads_of[aid]}
                    for aid, fs in forms_of.items()}
        if "agent" in fixes and facts:
            agent = agent_forms(entries, facts)
            for aid, fs in agent.items():
                forms_of[aid] |= fs
            stats["freq_fix_agent_verbs"] = len(agent)
            stats["freq_fix_agent_forms"] = len(set().union(*agent.values())) if agent else 0
    elif shared != "each":
        raise ValueError("shared must be one of %s" % (FREQ_SHARED,))
    if "symbol" in fixes and facts:
        sym = symbol_shared(entries, facts)
        for aid, fs in sym.items():
            forms_of[aid] -= fs
        stats["freq_fix_symbol_articles"] = len(sym)
    out = {aid: sum(counts.get(f, 0) for f in fs) for aid, fs in forms_of.items()}
    stats["freq_articles_seen"] = sum(1 for v in out.values() if v > 0)
    return out


def article_examples(data: dict) -> int:
    """The number of example sentences in one article's ``body.definitions``: every
    ``example`` element reached through ``elements``, an embedded ``sub_article`` (a fixed
    expression's own article) not entered — the measurement's D-examples (site decisions 143,
    ``form-order-measure-143-2026-10-26/collect.py`` ``size``, its second figure)."""
    n = 0

    def walk(el):
        nonlocal n
        if isinstance(el, list):
            for x in el:
                walk(x)
            return
        if not isinstance(el, dict):
            return
        t = el.get("type_")
        if t in ("sub_article", "explanation"):
            return
        if t == "example":
            n += 1
            return
        walk(el.get("elements") or [])
    walk((data.get("body") or {}).get("definitions") or [])
    return n


def read_examples(path: str, listing=None, ids=()) -> dict:
    """``{article id: article_examples}`` over the mirror; with ``listing`` (``search_scope``'s
    ``Listing``), each id of ``ids`` the mirror lacks is counted from its stored copy, as the
    measurement did. An article with neither counts 0 (``form_share`` weighs it 1)."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                out[row.get("id")] = article_examples(row.get("data") or {})
    if listing is not None:
        for aid in ids:
            if aid not in out:
                data = listing.stored_copy(aid)
                if data:
                    out[aid] = article_examples(data)
    return out


def form_share(entries, counts: dict, examples: dict) -> dict:
    """E2 (site decisions 143, Robin's choice 2026-10-27; defined and measured in
    ``form-order-measure-143-2026-10-26/collect.py``, ``split_by(1)``): ``{article id: figure}``
    — every case-folded spelling's NB count (``counts``, ``read_freq``) shared out among ALL the
    articles that have it, as a headword or an inflected form, in proportion to each one's
    number of example sentences + 1 (``examples``, ``read_examples``); an article's figure is
    the sum of its shares, rounded to a whole number as the measurement rounded it (so its
    ties are the measurement's). None of ``article_freq``'s fixes applies: an agent noun's
    plural is not lent to the verb, a symbol keeps its share. ``form_order`` sorts by it."""
    forms_of = {e[0]: {fold(f) for f in list(e[1]) + list(e[4])} for e in entries}
    owners = defaultdict(set)
    for aid, fs in forms_of.items():
        for f in fs:
            owners[f].add(aid)
    wt = {aid: examples.get(aid, 0) + 1 for aid in forms_of}
    out = defaultdict(float)
    # in a fixed order (spellings, then ids, sorted): a float sum taken in a set's order differs
    # in its last bits from run to run, and a figure near .5 then rounds either way
    for f in sorted(owners):
        os_ = sorted(owners[f])
        c = counts.get(f, 0)
        if not c:
            continue
        tot = sum(wt[a] for a in os_)
        for a in os_:
            out[a] += c * wt[a] / tot
    return {aid: round(out.get(aid, 0.0)) for aid in forms_of}


#: The exceptions to E2's order (site decisions 143, Robin 2026-10-27): a committed file a
#: person reads, beside ``freq-overrides.tsv`` and in its manner (``read_form_overrides``).
FORM_OVERRIDES_PATH = os.path.join(ROOT, "ordpar", "form-order-overrides.tsv")


def read_form_overrides(path: str) -> dict:
    """The exceptions file: ``{form: [article id, ...]}``, the ids ``form_order`` puts first
    under that inflected form, in that order. A TSV: the header ``form<TAB>first<TAB>why``, then
    one line per form (as spelled in the index's ``forms``, matched exactly), ``first`` one id
    or several separated by commas; a line starting with ``#`` is a comment and a blank line is
    skipped. A malformed line, an id that is not a number, an empty reason or a form listed
    twice raises ``ValueError`` naming the file and the line number. Whether each form and id is
    in the index is ``write_index``'s check (``form_overrides_unmatched``)."""
    out = {}
    header = False
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.startswith("#"):
                continue
            cells = line.split("\t")
            where = "%s:%d" % (path, n)
            if not header:
                if cells != ["form", "first", "why"]:
                    raise ValueError("%s: the header must be 'form<TAB>first<TAB>why', got %r"
                                     % (where, line))
                header = True
                continue
            if len(cells) != 3:
                raise ValueError("%s: %d tab-separated fields, not 3: %r"
                                 % (where, len(cells), line))
            form, first, why = cells[0], cells[1].strip(), cells[2].strip()
            if not form or form != form.strip():
                raise ValueError("%s: the form is empty or padded: %r" % (where, form))
            ids = [x.strip() for x in first.split(",")]
            if not all(x.isdigit() for x in ids):
                raise ValueError("%s: %r is not one article id or several, comma-separated"
                                 % (where, first))
            if not why:
                raise ValueError("%s: no reason given for %r" % (where, form))
            if form in out:
                raise ValueError("%s: %r is listed twice" % (where, form))
            out[form] = [int(x) for x in ids]
    if not header:
        raise ValueError("%s: no header line" % path)
    return out


def freq_rules(overrides: dict | None = None, symbol_ids=(), ceiling: int | None = None,
               scale: float = FREQ_SCALE) -> dict:
    """The rules ``headword_bands`` applies to a headword string (``form_band``): the
    registry, the articles ``symbol_shared`` sank, the abbreviation ceiling, the scale."""
    return {"overrides": dict(overrides or {}), "symbol_ids": frozenset(symbol_ids),
            "floor": ABBR_FLOOR, "ceiling": ABBR_CEILING if ceiling is None else ceiling,
            "scale": scale}


def freq_note(freq_path, shared, overrides_path=None, overrides=None, rules=None) -> dict:
    """The index manifest's ``freq``: the source file and its shared-form rule and, beside them
    (decisions 55, 2026-10-20), the scale, the single-character and abbreviation bands, the
    fixes, and the overrides registry by file name and entry count. Names, never paths."""
    if not freq_path:
        return {"freq": None, "freq_shared": None}
    note = {"freq": os.path.basename(freq_path), "freq_shared": shared}
    if rules is not None:
        note.update({"scale": round(rules["scale"], 4), "single_band": SINGLE_BAND,
                     "abbr_band": [rules["floor"], rules["ceiling"]], "fixes": list(FREQ_FIXES),
                     "overrides": {"file": os.path.basename(overrides_path or OVERRIDES_PATH),
                                   "entries": len(overrides or {})}})
    return note


def form_band(form: str, ids, count: int, rules: dict) -> int:
    """A headword string's band from its highest article's ``count`` (decisions 55, in order):
    the registry's entry where it has one (a band, or ``nb``: the scaled count) — a person's
    ruling, so ahead of every rule; a single letter or digit, ``SINGLE_BAND``; an abbreviation,
    or a string whose every article is a symbol ``symbol_shared`` sank, the scaled count held
    between the floor and the ceiling; anything else, the scaled count."""
    scale = rules["scale"]
    ov = rules["overrides"].get(form)
    if ov is not None:
        return scaled_band(count, scale) if ov == "nb" else ov
    if is_single(form):
        return SINGLE_BAND
    if is_abbr(form) or (ids and all(i in rules["symbol_ids"] for i in ids)):
        return min(rules["ceiling"], max(rules["floor"], scaled_band(count, scale)))
    return scaled_band(count, scale)


# --------------------------------------------------------------------------- #
# alternation in expression headwords — expanded for matching (decisions 39)
# --------------------------------------------------------------------------- #

_GROUP = re.compile(r"\[([^\[\]]*)\]")


def variants(form: str) -> list[str]:
    """The readable forms of a headword written in ordbokene's alternation notation.

    ``[få|sette] ræva i gir`` -> ``få ræva i gir``, ``sette ræva i gir``: each bracketed
    group is one of its ``|``-separated alternatives, every combination where there are
    several groups, in source order (so ``variants(w)[0]`` is the first variant). Two
    further spellings of the same notation occur once each and are read the same way: a
    group separated by ``/`` (``pipa får en annen [låt/lyd]``) and a ``|`` OUTSIDE the
    brackets between whole alternatives (``[i alt vesentlig] | [i det vesentlige]``).
    Whitespace is collapsed. A form with no bracket and no ``|`` is returned unchanged
    (a bare ``/`` — ``km/h``, ``ermet/bakhånd`` — is not alternation here), and so is a
    form whose brackets do not balance."""
    if "[" not in form and "|" not in form:
        return [form]
    depth, cuts = 0, []
    for i, c in enumerate(form):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth < 0:
                return [form]
        elif c == "|" and depth == 0:
            cuts.append(i)
    if depth != 0:
        return [form]
    parts = ([form[a + 1:b] for a, b in zip([-1] + cuts, cuts + [len(form)])]
             if cuts else [form])
    out = []
    for part in parts:
        pieces = _GROUP.split(part)
        options = [(piece.split("|") if "|" in piece else piece.split("/")) if i % 2
                   else [piece] for i, piece in enumerate(pieces)]
        for combo in itertools.product(*options):
            v = " ".join("".join(combo).split())
            if v:
                out.append(v)
    return list(dict.fromkeys(out)) or [form]


# --------------------------------------------------------------------------- #
# the mirror pass
# --------------------------------------------------------------------------- #

def read_mirror(path: str, limit: int | None = None):
    """Yield ``(id, headwords, hgnos, pos, inflected, cells)`` per mirror row (``entry``).

    ``headwords`` are the row's distinct ``lemmas[].lemma`` in source order, ``hgnos`` each
    one's own homograph number (site decisions 93); ``inflected``
    every distinct non-null ``word_form`` that is not one of them; ``pos`` the first
    paradigm tag (``NOUN`` / ``VERB`` / …) or ``""``.
    """
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            if limit is not None and n >= limit:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            yield entry(row.get("id"), row.get("data") or {})


class Entry(tuple):
    """``entry``'s answer: the 6-tuple ``(id, headwords, hgnos, pos, inflected, cells)`` every
    caller unpacks, and, as ``.tags``, each inflected form's cell keys — ``{form: {"Plur+Ind",
    …}}``, the mirror's ``paradigm_info[].inflection[].tags`` joined by "+" as ``inflection.js``
    keys ``TAGS`` — which the form labels are made from (site decisions 117)."""

    def __new__(cls, items, tags=None):
        obj = super().__new__(cls, items)
        obj.tags = tags or {}
        return obj


def entry(aid, data: dict, pos: str = ""):
    """One article's ``(id, headwords, hgnos, pos, inflected, cells)`` from its ``data`` —
    a mirror row's, or the copy a parent embeds (whose lemmas carry no paradigm, so the
    caller supplies ``pos``). ``hgnos`` is each headword's own homograph number, aligned with
    ``headwords`` (site decisions 93: *lysing* 1, *lysning* 2; a spelling listed twice keeps
    its first lemma's). Until 2026-10-22 one number, the first lemma's. The lemmas are read in
    OUR order where the normalization log rules one (site decisions 93 (2), `lemma_order`):
    *tørre / tore*, not the mirror's *tore / tørre* — so the display text, the numbers and every
    reader of them (results, list view, favourites, history, suggestions) follow it."""
    data = lemma_order.reorder(aid, data)
    heads, hgnos = [], []
    forms = []
    cell_keys = defaultdict(set)
    for lemma in data.get("lemmas") or []:
        w = lemma.get("lemma")
        if isinstance(w, str) and w.strip():
            w = nfc(w.strip())
            if w not in heads:
                heads.append(w)
                hgnos.append(int(lemma.get("hgno") or 0))
        for para in lemma.get("paradigm_info") or []:
            tags = para.get("tags") or []
            if tags and not pos:
                pos = str(tags[0])
            for cell in para.get("inflection") or []:
                wf = cell.get("word_form")
                if isinstance(wf, str) and wf.strip():
                    forms.append(nfc(wf.strip()))
                    ct = cell.get("tags") or []
                    cell_keys[forms[-1]].add("+".join(str(t) for t in ct))
    inflected = [f for f in dict.fromkeys(forms) if f not in heads]
    return Entry((aid, heads, hgnos, pos, inflected, len(forms)),
                 {f: frozenset(cell_keys[f]) for f in inflected})


#: The index's separator between an article's spellings in ``words[id][0]``. A DATA separator,
#: never shown: every reader draws the spellings with ", " between them, each with its own
#: numeral, as the article's headword line (site decisions 93, Robin 2026-10-22: "the lemmas
#: are seperated by `,` not `/`"; lookup.js ``headParts``). " / " stays in the data because 48
#: headwords contain ", " (*snipp, snapp, snute*) and none contains " / ", and because history
#: and favourites stored in readers' browsers carry it (personal.js ``wordQuery``).
SEP = " / "


def display(headwords: list[str], cap: int = 3) -> str:
    """The panel's text for an article: its lemma forms, at most three, joined by ``SEP``."""
    if not headwords:
        return ""
    if len(headwords) <= cap:
        return SEP.join(headwords)
    return SEP.join(headwords[:cap]) + " …"


def hg_field(hgnos: list[int], cap: int = 3):
    """``words[id][1]`` (site decisions 93): the homograph numbers of the spellings ``display``
    shows (the first ``cap``). One int where they are all the same — the number every spelling
    carries, 0 for none: *tore* 2, *tørre* 2 is ``2``, and a one-spelling article is its own
    number as before — else a list, one per shown spelling: *lysing* 1, *lysning* 2 is
    ``[1, 2]``. lookup.js ``article`` reads both shapes."""
    shown = [int(h or 0) for h in hgnos[:cap]] or [0]
    return shown[0] if len(set(shown)) == 1 else shown


def form_hg(word: list, form: str) -> int:
    """The homograph number of the spelling ``form`` in the article ``word`` (a ``words``
    entry): the number a results list, a suggestion's glosses and the results' order give the
    article when a search matched that spelling (site decisions 93, read off ordbokene's results
    for *lysning*: *lysning* I before *lysing* I, *lysning* II). A form the shown spellings do
    not include (a fourth spelling, an alternation variant, an inflected form) takes the first
    non-zero number shown. lookup.js ``formHg``."""
    hg = word[1] if len(word) > 1 else 0
    if not isinstance(hg, list):
        return int(hg or 0)
    forms = word[0].replace(" …", "").split(SEP)
    if form in forms and forms.index(form) < len(hg):
        return hg[forms.index(form)]
    return next((h for h in hg if h), 0)


def build_tables(mirror, limit: int | None, stats: dict, form_tags: dict | None = None):
    """One pass over the mirror -> per-shard head/form maps and the per-id word table.
    ``mirror`` is the jsonl's path, or the ``entry`` tuples already read (what ``main``
    passes once decisions 46 has chosen which articles search covers). ``form_tags``, when
    given, is filled with ``{(inflected form, id): frozenset of cell keys}`` (``Entry.tags``,
    site decisions 117's form labels)."""
    heads = defaultdict(lambda: defaultdict(list))   # shard -> form -> [id]
    forms = defaultdict(lambda: defaultdict(list))   # shard -> form -> [id]
    words = {}                                       # id -> [display, hg, pos(, 1)]
    rows = lemma_entries = cells = expanded = n_variants = 0
    source = read_mirror(mirror, limit) if isinstance(mirror, str) else mirror
    for e in source:
        aid, hws, hgnos, pos, inflected, n_cells = e
        rows += 1
        cells += n_cells
        lemma_entries += len(hws)
        if not hws and not inflected:
            continue
        # a headword in alternation notation is stored as its variants, never as written
        per_lemma = [variants(w) for w in hws]
        shown, shown_hg = [], []
        for vs, h in zip(per_lemma, hgnos):
            if vs[0] not in shown:
                shown.append(vs[0])
                shown_hg.append(h)
        words[aid] = [display(shown), hg_field(shown_hg), pos]
        if any(vs != [w] for w, vs in zip(hws, per_lemma)):
            words[aid].append(1)      # the panel shows the variant that matched
        own = set()
        for w, vs in zip(hws, per_lemma):
            if vs != [w]:
                expanded += 1
                n_variants += len(vs)
            for v in vs:
                own.add(v)
                heads[shard_key(v)][v].append(aid)
        tg = getattr(e, "tags", None) or {}
        for w in inflected:
            if w not in own:
                forms[shard_key(w)][w].append(aid)
                if form_tags is not None:
                    form_tags[(w, aid)] = tg.get(w, frozenset())
    stats["rows"] = rows
    stats["lemma_entries"] = lemma_entries
    stats["inflection_cells_with_form"] = cells
    stats["expanded_headwords"] = expanded
    stats["expanded_variants"] = n_variants
    return heads, forms, words


# --------------------------------------------------------------------------- #
# the library pass — which ids are translated
# --------------------------------------------------------------------------- #

def translated_ids(library: str) -> list[int]:
    out = []
    rows = 0
    with open(library, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows += 1
            row = json.loads(line)
            if coverage.complete_strict(row):
                out.append(row["id"])
    out.sort()
    return out, rows


def library_pass(library: str):
    """``translated_ids`` plus what decisions 46 needs of each row, and whether it carries a
    summary gloss (the Random word's pool, decisions 67): ``{id: {lemmas, pos_en, gloss}}``, and
    for a row with one its glosses (``en``: the English search's index, site decisions 148)."""
    out, lite = [], {}
    with open(library, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            summary = row.get("summary")
            gloss = (summary.get("gloss") or []) if isinstance(summary, dict) else []
            lite[row["id"]] = {"lemmas": row.get("lemmas") or [], "pos_en": row.get("pos_en"),
                               "gloss": bool(gloss)}
            if gloss:
                # site decisions 148: the summary gloss itself, the English search's index
                lite[row["id"]]["en"] = [g for g in gloss if isinstance(g, str)]
            if coverage.complete_strict(row):
                out.append(row["id"])
    out.sort()
    return out, lite


def random_pool(translated, words: dict, library: dict | None = None) -> list[int]:
    """The articles that meet the Random word's bar (decisions 67, Robin 2026-10-20; the pool
    itself is headwords since decisions 115, ``random_headwords``): the ``translated`` ids that are
    not a set phrase and, given the library pass's rows, carry a non-empty ``summary.gloss``.
    A set phrase is what search itself calls one: the entry's part of speech ``EXPR``
    (``words[id][2]``, the tag the lookup panel leaves unlabelled), or a library row whose
    ``pos_en`` is ``fixed expression`` (a kept article whose entry has no tag). Without
    ``library`` (the synthetic tests) only the set-phrase test applies. Sorted."""
    out = []
    for i in translated:
        w = words.get(i)
        if w is not None and len(w) > 2 and w[2] == "EXPR":
            continue
        if library is not None:
            row = library.get(i) or {}
            if row.get("pos_en") == "fixed expression" or not row.get("gloss"):
                continue
        out.append(i)
    return sorted(out)


def first_shown(res: dict):
    """The id of the article a search shows FIRST (lookup.js ``firstShown``, which ``render``
    draws from): every headword group's articles in turn (each already in ``result_order``),
    then the translated ones before the untranslated across the groups (brief 59b item 12) —
    the first of the full results and of the list view alike. The inflected-form rows are not
    articles shown in full and never count. ``res`` is ``Index.lookup``'s answer; None for a
    search with no headword hit."""
    arts = [a for g in res.get("heads", []) for a in g["articles"]]
    done = [a for a in arts if a.get("translated")]
    first = (done or arts or [None])[0]
    return None if first is None else first["id"]


def random_headwords(idx: "Index", heads: dict, pool) -> list[str]:
    """The Random word's pool since decisions 115 (Robin, 2026-10-24: "it opens to a random
    headword search … Just the first one is enough"): the headwords whose search shows first
    an article of ``pool`` (``random_pool``, decisions 67's bar). Each candidate — a headword
    form of an article in ``pool`` — is searched through ``idx`` (``Index``, the read-side twin
    of lookup.js, over the index just written: the same shards, ``translated.json``, the same
    ``result_order`` and accent dedupe) and kept when ``first_shown`` is in ``pool``; the other
    articles its search shows may be untranslated or partly authored (*fly*). Forms that fold
    to the same search (*Mars*, *mars*) are one search, written once: as the form whose group
    holds that first article. Sorted."""
    pool = set(pool)
    by_query = defaultdict(list)
    for key in sorted(heads):
        for form, ids in heads[key].items():
            if pool.intersection(ids):
                by_query[fold(form)].append(form)
    out = []
    for q, forms in sorted(by_query.items()):
        res = idx.lookup(q)
        first = first_shown(res)
        if first not in pool:
            continue
        holds = [g["form"] for g in res["heads"] if any(a["id"] == first for a in g["articles"])]
        out.append(next((f for f in sorted(forms) if f in holds), sorted(forms)[0]))
    return sorted(out)


def shown_articles(res: dict) -> list:
    """The articles a search shows, in its order, each once (lookup.js ``shownOrder``, deduped
    as ``render`` draws them): every headword group's articles in turn, then the translated
    before the untranslated. ``first_shown`` is its first."""
    arts = [a for g in res.get("heads", []) for a in g["articles"]]
    seen, out = set(), []
    for a in [a for a in arts if a.get("translated")] + [a for a in arts if not a.get("translated")]:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
    return out


def result_count(res: dict) -> int:
    """The number the results' heading shows (lookup.js ``lookup`` ``count``): every group's
    articles, headword and inflected-form groups alike."""
    return sum(len(g["articles"]) for k in ("heads", "forms") for g in res.get(k, []))


def form_rows(res: dict) -> list:
    """The "is an inflected form of" sections a search shows: ``[(form, [articles])]``, each
    article once (lookup.js ``render`` over ``res.forms``)."""
    return [(g["form"], list(g["articles"])) for g in res.get("forms", []) if g["articles"]]


def page_plan(idx, words, form_tags, labels, freq_path, stats) -> dict:
    """Site decisions 117: which searches get a page, and what each page's canonical is — the
    ONE rule the build writes pages from and the browser reads (``write_index`` writes it into
    the index; ``test_ordpar_wordpages117`` holds the two together). ``idx`` the read-side twin
    of lookup.js over the shards about to be written (``MemIndex``).

    * **A word page** for every distinct search (the search's own ``fold``: *Mars*/*mars* one
      search) that matches a headword and whose FIRST SHOWN article (``first_shown``: the
      translated before the untranslated) is translated — and that can be a folder name
      (``wordpages.unrepresentable``).
    * **A form page** for every search that matches no headword but is an inflected form, of
      which at least one word is translated (decisions 2's rule), is IRREGULAR against at least
      one of those translated words, tested against each word's own spellings (decisions 117 (3):
      it begins neither with the spelling nor with the spelling less a final -e — *tær* against
      *tå*, *bøker* against *bok*), is seen at least ``wordpages.MIN_FORM_COUNT`` times in NB's
      2026 books (``read_freq``, the list the search ranks by; without ``freq_path`` there are
      no form pages) and is not only a passive.
    * **The canonical**: a word page with several entries, and a form page, is its own; a word
      page with ONE article is the canonical page of that article (the article page's canonical
      points to it). Where one article is the only result of several word pages (a variant
      spelling, *bru* / *bro*), all of them and the article point to ONE: the page of the
      article's first spelling (the one its title leads with), else of its first spelling that
      has a page (the session's call, flagged to Robin).

    -> ``{"words": {fq: {...}}, "forms": {fq: {...}}, "canonical": {fq: fq},
    "article_canonical": {id: fq}, "counts": {...}}``; each page's ``form`` is the spelling it
    shows as its headline (the word's own capitals: the stored form whose group holds the first
    article), ``arts`` its headword articles in the order shown, ``rows`` its inflected-form
    sections (each article with its form ``label``)."""
    counts = defaultdict(int)
    unrep = defaultdict(int)
    unrep_examples = defaultdict(list)
    heads_by_q, forms_by_q = defaultdict(list), defaultdict(list)
    spellings = defaultdict(set)                 # id -> every headword form it is filed under
    for key, sh in idx._shards.items():
        for f, ids in sh["heads"].items():
            heads_by_q[fold(f)].append(f)
            for i in ids:
                spellings[i].add(f)
        for f in sh["forms"]:
            forms_by_q[fold(f)].append(f)

    def label_rows(res):
        rows = []
        for form, arts in form_rows(res):
            out = []
            for a in arts:
                a = dict(a)
                keys = (form_tags or {}).get((form, a["id"]), frozenset())
                a["keys"] = keys
                a["label"] = labels.label(keys) if labels is not None else ""
                # site decisions 152: its Norwegian, for the built row's hidden copy
                a["label_nb"] = labels.label_nb(keys) if labels is not None else ""
                out.append(a)
            rows.append((form, out))
        return rows

    def unrepresentable(fq):
        why = wordpages_mod.unrepresentable(fq)
        if why:
            unrep[why] += 1
            if len(unrep_examples[why]) < 12:
                unrep_examples[why].append(fq)
        return why

    taken = {}                                    # the folder name as Windows compares it
    word_pages = {}
    for fq in sorted(heads_by_q):
        counts["searches"] += 1
        res = idx.lookup(fq)
        arts = shown_articles(res)
        if not arts:
            continue
        if not arts[0].get("translated"):
            counts["searches_first_untranslated"] += 1
            continue
        counts["searches_first_translated"] += 1
        if unrepresentable(fq):
            continue
        if fq.upper() in taken:
            unrep["folder name taken"] += 1
            unrep_examples["folder name taken"].append(fq)
            continue
        taken[fq.upper()] = fq
        holds = [g["form"] for g in res["heads"] if any(a["id"] == arts[0]["id"] for a in g["articles"])]
        forms = sorted(heads_by_q[fq])
        word_pages[fq] = {"form": next((f for f in forms if f in holds), forms[0]),
                          "arts": arts, "count": result_count(res),
                          "rows": label_rows(res)}
    counts["word_pages"] = len(word_pages)
    counts["word_pages_several"] = sum(1 for w in word_pages.values() if len(w["arts"]) > 1)
    counts["word_pages_one"] = counts["word_pages"] - counts["word_pages_several"]
    counts["word_pages_with_inflected_rows"] = sum(1 for w in word_pages.values() if w["rows"])

    # the irregular forms (decisions 117 (3))
    candidates = {}
    for fq in sorted(forms_by_q):
        if fq in heads_by_q:
            continue
        counts["forms_not_headword_searches"] += 1
        res = idx.lookup(fq)
        if res["heads"]:
            counts["forms_with_accent_headword"] += 1
            continue
        rows = label_rows(res)
        arts = [a for _f, a_ in rows for a in a_]
        tr = [a for a in arts if a.get("translated")]
        if not tr:
            continue
        counts["forms_of_a_translated_word"] += 1
        if not any(wordpages_mod.irregular(fq, spellings[a["id"]], fold) for a in tr):
            continue
        counts["forms_irregular"] += 1
        candidates[fq] = (res, rows)
    freq = read_freq(freq_path, set(candidates)) if freq_path and candidates else {}
    form_pages = {}
    for fq, (res, rows) in sorted(candidates.items()):
        n = freq.get(fq, 0)
        if n < wordpages_mod.MIN_FORM_COUNT:
            continue
        counts["forms_irregular_common"] += 1
        if wordpages_mod.is_passive_only([a["keys"] for _f, arts in rows for a in arts]):
            counts["forms_passive_only"] += 1
            continue
        if unrepresentable(fq):
            continue
        if fq.upper() in taken:
            unrep["folder name taken"] += 1
            continue
        taken[fq.upper()] = fq
        form_pages[fq] = {"form": rows[0][0], "arts": [], "count": result_count(res),
                          "rows": rows, "freq": n}
    counts["form_pages"] = len(form_pages)

    # the canonical (decisions 117)
    canonical = {fq: fq for fq in word_pages}
    canonical.update({fq: fq for fq in form_pages})
    by_article = defaultdict(list)
    for fq, w in word_pages.items():
        if len(w["arts"]) == 1:
            by_article[w["arts"][0]["id"]].append(fq)
    article_canonical = {}
    variants = []
    for aid, fqs in sorted(by_article.items()):
        if len(fqs) == 1:
            article_canonical[aid] = fqs[0]
            continue
        shown = (words.get(aid) or [""])[0].replace(" …", "").split(SEP)
        order = [fold(x) for x in shown if x] + sorted(fold(x) for x in spellings[aid])
        lead = next((f for f in order if f in fqs), sorted(fqs)[0])
        for fq in fqs:
            canonical[fq] = lead
        article_canonical[aid] = lead
        variants.append((aid, lead, sorted(fqs)))
    counts["variant_spelling_articles"] = len(variants)
    counts["variant_spelling_pages_pointing_away"] = sum(len(v[2]) - 1 for v in variants)
    counts["articles_canonical_to_word_page"] = len(article_canonical)
    counts["unrepresentable"] = sum(unrep.values())
    stats["pages_117_unrepresentable"] = dict(unrep)
    return {"words": word_pages, "forms": form_pages, "canonical": canonical,
            "article_canonical": article_canonical, "counts": dict(counts),
            "unrepresentable": {k: {"count": v, "examples": unrep_examples[k]} for k, v in unrep.items()},
            "variants": variants}


class MemIndex:
    """``Index`` over shards held in memory (``write_index``'s, before they are written): the same
    ``lookup``, over the same tables, with ``translated`` given."""

    def __new__(cls, tables: dict, translated):
        idx = Index("")
        idx._translated = set(translated)
        for key, sh in tables.items():
            s2 = dict(sh)
            s2["fh"] = Index._folded(sh["heads"])
            s2["ff"] = Index._folded(sh["forms"])
            s2["bands"] = shard_bands(sh)
            idx._shards[key] = s2
        empty = {"heads": {}, "forms": {}, "words": {}, "fh": {}, "ff": {}, "bands": {}}
        idx.shard = lambda key: idx._shards.get(key, empty)
        return idx


_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}


def search_scope(mirror: str, entries: list, library: dict, translated: list, stats: dict):
    """Decisions 46 (Robin, 2026-10-18): search covers ordbokene's LISTED articles plus the
    KEPT unlisted ones (translated library rows with no translated listed namesake —
    ``sitegen.mirror.Listing``). Returns ``(entries, translated)`` filtered to that scope,
    with an entry added for each kept article the jsonl no longer carries (ordbokene 404s
    it): from its stored copy, else the copy its first parent embeds, else its library row."""
    listing = mirror_mod.Listing(mirror)
    by_form, lemmas_of = defaultdict(list), {}
    for e in entries:
        lemmas_of[e[0]] = e[1]
        for w in e[1]:
            by_form[w].append(e[0])
    embedded = mirror_mod.decide_kept(listing, mirror, library, set(translated), by_form,
                                      lambda a: lemmas_of.get(a, ()))
    kept = [e for e in entries if listing.in_search(e[0])]
    sources = defaultdict(int)
    for aid in listing.kept_404():
        data = listing.stored_copy(aid)
        art = (embedded.get(aid) or (None, None))[1] or {}
        row = library.get(aid) or {}
        # the embedded copy's lemmas carry no paradigm: the library row's part of speech,
        # else the copy's `word_class` when it is a tag (125117 carries the string "false")
        wc = str(art.get("word_class") or "")
        pos = "EXPR" if row.get("pos_en") == "fixed expression" else (
            wc if wc.isupper() else "")
        if data:
            kept.append(entry(aid, data))
            sources["stored_copy"] += 1
        elif art.get("lemmas"):
            kept.append(entry(aid, art, pos=pos))
            sources["parent_embedded_copy"] += 1
        else:
            lemmas = [{"lemma": l.get("form"), "hgno": _ROMAN.get(l.get("homograph") or "", 0)}
                      for l in row.get("lemmas") or []]
            kept.append(entry(aid, {"lemmas": lemmas}, pos=pos))
            sources["library_row"] += 1
    kept.sort(key=lambda e: e[0])
    for k, v in listing.counts().items():
        if isinstance(v, int):
            stats["unlisted46_" + k] = v
    for k, v in sources.items():
        stats["unlisted46_kept_404_index_from_" + k] = v
    stats["unlisted46_rows_left_out"] = len(entries) - sum(
        1 for e in entries if listing.in_search(e[0]))
    tr = [i for i in translated if listing.in_search(i)]
    stats["unlisted46_translated_left_out"] = len(translated) - len(tr)
    return kept, tr, listing


# --------------------------------------------------------------------------- #
# writing
# --------------------------------------------------------------------------- #

def dump(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True).encode("utf-8")


def write_bytes(path: str, blob: bytes) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


def gz_size(blob: bytes) -> int:
    return len(gzip.compress(blob, GZ, mtime=0))


def headword_bands(heads, freq, rules=None) -> dict:
    """``{headword form: band}`` — the highest band of the articles the form is a headword of
    (homographs share their forms' counts, so they mostly share a band anyway). With ``rules``
    (``freq_rules``, what a build passes) the band is ``form_band``'s, from the highest count;
    without, the raw count's ``band`` (the synthetic tests' bands)."""
    out = {}
    for key in heads:
        for f, ids in heads[key].items():
            n = max((freq.get(i, 0) for i in ids), default=0) if freq else 0
            b = form_band(f, ids, n, rules) if rules is not None else band(n)
            out[f] = max(out.get(f, 0), b)
    return out


#: The code characters of ``similar_file``'s ``k`` (site decisions 144): a word class's code is
#: its place in the file's own ``kc`` list; ``.`` none (several articles, or no tag).
ROW_CODES = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def row_fields(form_ids: dict, words: dict, translated) -> dict:
    """What a similar headword's row needs before its snippet file comes (site decisions 144):
    ``{form: (n, translated, pos)}`` — the number of articles the form heads (its own
    spelling, as a suggestion row counts them: ``heads[form]``), whether any of them is
    translated, and the word class of a one-article form ('' for several). lookup.js
    ``similarEntries`` reads them back from ``similar_file``'s ``a``, ``x`` and ``k``."""
    tr = translated if isinstance(translated, (set, frozenset)) else set(translated)
    out = {}
    for form, ids in form_ids.items():
        ids = sorted(set(ids))
        pos = ((words.get(ids[0]) or ["", 0, ""])[2] or "") if len(ids) == 1 else ""
        out[form] = (len(ids), any(i in tr for i in ids), pos)
    return out


def similar_file(forms: list, bands: dict, pages=None, rows=None) -> dict:
    """A similar-words file (``headwords/<l>.json``, ``tails/<k>.json``): the sorted forms and,
    aligned with them, one hex digit per form — its frequency band (decisions 55 (2)) — and,
    where any has one, ``p``: 1 where the form's search has a word page (site decisions 117,
    ``pages`` the folded searches that do; a similar headword links its page).

    With ``rows`` (``row_fields``; site decisions 144, so a similar headword's row after a miss
    needs no shard): ``a``, one hex digit per form, the number of articles it heads (at most
    ``f``); ``x``, one digit per form, 1 where any of them is translated; ``k``, one character
    per form, the word class of a one-article form as its place in ``kc`` (``ROW_CODES``), ``.``
    for none — ``kc`` the file's word classes, sorted."""
    lst = sorted(forms)
    out = {"w": lst, "f": "".join(HEX[bands.get(w, 0)] for w in lst)}
    if pages:
        p = "".join("1" if fold(w) in pages else "0" for w in lst)
        if p.strip("0"):
            out["p"] = p
    if rows is not None:
        got = [rows.get(w) or (0, False, "") for w in lst]
        kc = sorted({r[2] for r in got if r[2]})
        if len(kc) > len(ROW_CODES):
            raise ValueError("similar_file: more word classes than ROW_CODES")
        out["a"] = "".join(HEX[min(r[0], 15)] for r in got)
        out["x"] = "".join("1" if r[1] else "0" for r in got)
        out["k"] = "".join(ROW_CODES[kc.index(r[2])] if r[2] else "." for r in got)
        out["kc"] = kc
    return out


def write_index(out: str, heads, forms, words, translated, stats, freq=None, freq_note=None,
                snippets=None, snippet_max=SNIPPET_MAX, rules=None, library=None,
                form_tags=None, freq_path=None, order_freq=None, order_overrides=None,
                order_overrides_path=None, dict_articles=None):
    """Write ``out/index/`` (the format of record: ``lookup-index.md`` § 3) and return its
    manifest. Site decisions 143: each inflected form's articles are stored in ``form_order``'s
    order, by ``order_freq`` (``form_share``, E2) and then ``order_overrides``
    (``read_form_overrides``: the ids put first); an exception whose form is not an inflected
    form with two or more articles, or whose id is not among them, is counted in
    ``form_overrides_unmatched`` and named in the manifest's ``form_order``.
    Site decisions 117: the page plan (``page_plan``: which searches get a word page
    or a form page) is made first, over the shards in memory, and the browser's copy of it is
    written with them — ``p`` in each shard (one digit per headword, aligned with the headwords
    sorted, as ``n``: 1 where its search has a page), ``pf`` (the inflected forms with a form
    page) and ``p`` in ``headwords/`` and ``tails/`` (aligned with ``w``: the similar
    headwords' links); with ``form_tags`` (``build_tables``) each shard's ``t``, one form-label
    code per (form, article) aligned with ``forms``, and ``labels.json``, the codes' words. The
    plan rides back in the manifest under ``"_plan"`` (not written)."""
    index_dir = os.path.join(out, "index")
    if os.path.isdir(index_dir):
        shutil.rmtree(index_dir)
    os.makedirs(index_dir, exist_ok=True)

    # decisions 55's bands, which the autocomplete ranks by too (brief 59b item 14): each
    # shard and `-top` file carries `n`, one hex digit per headword aligned with its headwords
    # SORTED (`shard_bands`), as `headwords/` carries them — a {headword: band} map measured
    # 5.3x the gzip bytes; omitted when every band is 0, so a build without --freq writes the
    # files as before
    bands = headword_bands(heads, freq, rules)
    tr_set = set(translated)
    shard_keys = sorted(set(heads) | set(forms))
    shards = []
    tables = {}
    reordered = 0
    ovr = order_overrides or {}
    # an exception must name an inflected form with 2+ articles and only ids among them
    form_ids = {}
    for key in forms:
        for f in ovr:
            if f in forms[key]:
                form_ids[f] = set(forms[key][f])
    unmatched = sorted(f for f, first in ovr.items()
                       if len(form_ids.get(f, ())) < 2 or not set(first) <= form_ids[f])
    stats["form_overrides"] = len(ovr)
    stats["form_overrides_unmatched"] = len(unmatched)
    for key in shard_keys:
        h = {f: sorted(set(ids)) for f, ids in heads.get(key, {}).items()}
        # site decisions 143: each inflected form's articles stored most common first (E2),
        # then the exceptions file's ids first
        f_ = {f: form_order(ids, words, tr_set, order_freq, ovr.get(f))
              for f, ids in forms.get(key, {}).items()}
        if order_freq or ovr:
            reordered += sum(1 for f, ids in f_.items()
                             if len(ids) > 1 and ids != form_order(ids, words, tr_set))
        ids = {i for v in h.values() for i in v} | {i for v in f_.values() for i in v}
        shard = {"k": key,
                 "heads": h,
                 "forms": f_,
                 "words": {str(i): words[i] for i in sorted(ids) if i in words}}
        n = "".join(HEX[bands.get(f, 0)] for f in sorted(h))
        if n.strip("0"):
            shard["n"] = n
        tables[key] = shard
    stats["form_order_changed_143"] = reordered

    # site decisions 117: the form labels, then the page plan over the shards as they will be
    # written (the read-side twin of lookup.js, in memory), then the browser's copy of both
    labels = None
    if form_tags is not None:
        labels = wordpages_mod.FormLabels()
        labels.assign(form_tags.get((f, i), frozenset()) for key in shard_keys
                      for f, ids in tables[key]["forms"].items() for i in ids)
    plan = page_plan(MemIndex(tables, translated), words, form_tags, labels, freq_path, stats)
    for key in shard_keys:
        shard = tables[key]
        p = "".join("1" if fold(f) in plan["words"] else "0" for f in sorted(shard["heads"]))
        if p.strip("0"):
            shard["p"] = p
        pf = sorted(f for f in shard["forms"] if fold(f) in plan["forms"])
        if pf:
            shard["pf"] = pf
        if labels is not None and shard["forms"]:
            shard["t"] = "".join(labels.code(form_tags.get((f, i), frozenset()))
                                 for f in sorted(shard["forms"]) for i in shard["forms"][f])
    for key in shard_keys:
        shard = tables[key]
        blob = dump(shard)
        raw = write_bytes(os.path.join(index_dir, key + ".json"), blob)
        shards.append({"k": key, "file": key + ".json", "heads": len(shard["heads"]),
                       "forms": len(shard["forms"]),
                       "articles": len(shard["words"]), "raw": raw, "gzip": gz_size(blob)})

    # A split letter's one-character autocomplete file: its first TOP_HEADS headwords in
    # suggestion order, with their ids — the shard format with `forms` and `words` empty.
    tops = []
    for letter in SPLIT_LETTERS:
        pool = {f: ids for key in heads if key.startswith(letter + "-")
                for f, ids in heads[key].items()}
        if not pool:
            continue
        # the first TOP_HEADS for the prefix typed in lower case AND in capitals: the case
        # tie-break orders the two differently (decisions 55), and the file must answer both;
        # chosen in the autocomplete's own order (`suggest_rank`, brief 59b items 13, 14)
        def rank(w, typed):
            return suggest_rank(w, typed, any(i in tr_set for i in pool[w]), bands.get(w, 0))
        lower = sorted(pool, key=lambda w: rank(w, letter))[:TOP_HEADS]
        upper = sorted(pool, key=lambda w: rank(w, letter.upper()))[:TOP_HEADS]
        top = sorted(set(lower) | set(upper), key=lambda w: rank(w, letter))
        key = letter + "-top"
        top_file = {"k": key, "heads": {f: sorted(set(pool[f])) for f in top},
                    "forms": {}, "words": {}}
        n = "".join(HEX[bands.get(f, 0)] for f in sorted(top))
        if n.strip("0"):
            top_file["n"] = n
        blob = dump(top_file)
        raw = write_bytes(os.path.join(index_dir, key + ".json"), blob)
        tops.append({"k": key, "file": key + ".json", "heads": len(top), "raw": raw,
                     "gzip": gz_size(blob)})

    # The similar pass's candidates: every distinct headword form, one file per LETTER key
    # (the pass only reads the query's own first-letter bucket).
    by_letter = defaultdict(set)
    by_tail = defaultdict(set)
    # site decisions 144: each form's article count, translated flag and lone word class,
    # so a similar headword's row needs no shard
    rows = row_fields({f: ids for key in heads for f, ids in heads[key].items()}, words, tr_set)
    for key in heads:
        for f in heads[key]:
            by_letter[letter_key(f)].add(f)
            by_tail[tail_key(f)].add(f)
    hw_files = []
    for letter in sorted(by_letter):
        data = similar_file(by_letter[letter], bands, plan["words"], rows)
        blob = dump(data)
        raw = write_bytes(os.path.join(index_dir, "headwords", letter + ".json"), blob)
        hw_files.append({"k": letter, "file": "headwords/" + letter + ".json",
                         "count": len(data["w"]), "raw": raw, "gzip": gz_size(blob)})
    # (2) the same headwords keyed by the word WITHOUT its first character (decisions 55):
    # what a search reads to reach a wrong or missing first letter (vus -> hus, us -> hus)
    tail_files = []
    for k in sorted(by_tail):
        data = similar_file(by_tail[k], bands, plan["words"], rows)
        blob = dump(data)
        raw = write_bytes(os.path.join(index_dir, "tails", k + ".json"), blob)
        tail_files.append({"k": k, "count": len(data["w"]), "raw": raw, "gzip": gz_size(blob)})
    stats["headwords_with_band"] = sum(1 for v in bands.values() if v)

    # (3) the list view's snippets (site decisions 59): one file per first three bare
    # characters of a headword (`snippet_key`), for the articles that headword belongs to. Files
    # of their own, so the default view (full articles) never downloads one.
    snip, missing, mismatched = snippet_files(heads, snippets or {}, translated, snippet_max, words)
    snip_files = []
    for key in sorted(snip):
        blob = dump(snip[key])
        raw = write_bytes(os.path.join(index_dir, "snip", key + ".json"), blob)
        snip_files.append({"k": key, "count": len(snip[key]) - ("_d" in snip[key])
                           - ("_g" in snip[key]) - ("_h" in snip[key]) - ("_n" in snip[key]),
                           "rows": len(snip[key].get("_h", {})),
                           # site decisions 152: the translated articles' Norwegian definitions
                           "nb": sum(1 for v in snip[key].get("_n", {}).values() if v),
                           "drop": len(snip[key].get("_d", {})),
                           "gloss": len(snip[key].get("_g", [])), "raw": raw,
                           "gzip": gz_size(blob)})
    stats["snippets"] = sum(f["count"] for f in snip_files)
    stats["snippets_missing"] = missing
    stats["snippet_lang_mismatch"] = mismatched

    # site decisions 148: the English search's shards, `en/<letter>.json`
    english = write_english(index_dir, library or {}, words, bands, translated,
                            dict_articles or len(words))

    tr_blob = dump(translated)
    tr_raw = write_bytes(os.path.join(index_dir, "translated.json"), tr_blob)
    # decisions 115: the pool is HEADWORDS, each a search whose first article meets 67's bar,
    # found by searching the index just written (shards and translated.json are on disk)
    pool = random_pool(translated, words, library)
    hw_pool = random_headwords(Index(index_dir), heads, pool)
    rd_blob = dump(hw_pool)
    rd_raw = write_bytes(os.path.join(index_dir, "random.json"), rd_blob)
    stats["random_pool"] = len(pool)
    stats["random_headwords"] = len(hw_pool)
    lb_note = None
    if labels is not None:
        # site decisions 152: `"_nb"`, each code's words in Norwegian (`FormLabels.table_nb`)
        lb_blob = dump(dict(labels.table(), _nb=labels.table_nb()))
        lb_raw = write_bytes(os.path.join(index_dir, "labels.json"), lb_blob)
        t_raw = sum(len(tables[k].get("t", "").encode("utf-8")) for k in shard_keys)
        lb_note = {"file": "labels.json", "count": len(labels.table()), "raw": lb_raw,
                   "gzip": gz_size(lb_blob), "codes": t_raw,
                   "unknown_cell_keys": dict(sorted(labels.unknown.items()))}

    manifest = {
        "version": 3,
        "built": time.strftime("%Y-%m-%d"),
        "split_letters": list(SPLIT_LETTERS),
        "shards": shards,
        "tops": tops,
        "headwords": {"files": hw_files, "count": sum(h["count"] for h in hw_files),
                      "raw": sum(h["raw"] for h in hw_files),
                      "gzip": sum(h["gzip"] for h in hw_files)},
        "tails": {"files": tail_files, "count": sum(t["count"] for t in tail_files),
                  "raw": sum(t["raw"] for t in tail_files),
                  "gzip": sum(t["gzip"] for t in tail_files)},
        "snip": {"files": snip_files, "max": snippet_max,
                 "count": sum(f["count"] for f in snip_files),
                 "drop": sum(f["drop"] for f in snip_files),
                 "gloss": sum(f["gloss"] for f in snip_files),
                 "rows": sum(f["rows"] for f in snip_files),
                 "nb": sum(f["nb"] for f in snip_files),
                 "raw": sum(f["raw"] for f in snip_files),
                 "gzip": sum(f["gzip"] for f in snip_files)},
        # site decisions 148: the English search's shards (`write_english`)
        "english": english,
        "translated": {"file": "translated.json", "count": len(translated),
                       "raw": tr_raw, "gzip": gz_size(tr_blob)},
        "random": {"file": "random.json", "count": len(hw_pool), "articles": len(pool),
                   "raw": rd_raw, "gzip": gz_size(rd_blob)},
        # site decisions 155: Random word's English pool (`english_random`)
        "random_en": english.get("random"),
        # site decisions 117: the form labels' codes and the page plan's counts
        "labels": lb_note,
        "pages": plan["counts"],
        # the frequency source and its shared-form rule — the list itself is never written
        "freq": freq_note,
        # site decisions 143: how each inflected form's articles are ordered, and the exceptions
        "form_order": {"method": "E2" if order_freq else "result_order",
                       "overrides": {"file": os.path.basename(order_overrides_path
                                                              or FORM_OVERRIDES_PATH),
                                     "entries": len(ovr), "unmatched": unmatched}},
        "counts": {k: v for k, v in stats.items() if isinstance(v, int)},
    }
    mf_blob = dump(manifest)
    write_bytes(os.path.join(index_dir, "index.json"), mf_blob)
    manifest["_plan"] = plan
    manifest["_labels"] = labels
    return manifest


# --------------------------------------------------------------------------- #
# the English search (site decisions 148)
# --------------------------------------------------------------------------- #
#
# Robin, 2026-10-29: "a kind of "switch" underneath the search, where switching it on makes you
# search for the English equivalents instead of the Norwegian headword". The index is the summary
# glosses (decisions 17, amended 2026-10-19), ported from the style lab's `english_index.py`
# (`docs/sessions/2026-09-19-ordpar-site-review/evidence/style-lab/`), its rules unchanged but
# for the explanation units, which the lab indexed behind a toggle and the site does not index.
# The format of record: `ordpar/docs/lookup-index.md` § 3b.

#: The folder under `out/index/` of the English shards.
EN_DIR = "en"
_EN_OPEN, _EN_CLOSE = "([{", ")]}"
#: One leading word a key loses ("to go" -> "go", "a house" -> "house"), as the lab's `norm`.
EN_LEAD = ("to ", "a ", "an ", "the ")
#: The characters trimmed off a key's edges.
EN_EDGE = " \t.,;:!?'\"‘’“”-–—/"


def en_split_unit(unit: str) -> list:
    """``[(piece, sep)]``: a gloss unit cut at "," and ";" outside any bracket ( ), [ ], { };
    ``sep`` the separator as written after the piece (", ", "; " or "")."""
    out, depth, start, i = [], 0, 0, 0
    while i < len(unit):
        c = unit[i]
        if c in _EN_OPEN:
            depth += 1
        elif c in _EN_CLOSE:
            depth = max(0, depth - 1)
        elif c in ",;" and depth == 0:
            j = i + 1
            while j < len(unit) and unit[j] == " ":
                j += 1
            out.append((unit[start:i], unit[i:j]))
            start = i = j
            continue
        i += 1
    out.append((unit[start:], ""))
    return out


def en_strip_brackets(s: str) -> str:
    """``s`` without its ( ) and [ ] groups, and without its { } mentions AND their contents (a
    Norwegian mention is never an English key)."""
    out, depth = [], 0
    for c in s:
        if c in "([{":
            depth += 1
            continue
        if c in ")]}":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(c)
    return "".join(out)


def en_norm(s: str) -> str:
    """A key or a query as the index compares them: lower case, spaces collapsed, the edges
    trimmed, then one leading "to ", "a ", "an " or "the " dropped. lookup.js ``enNorm``."""
    s = " ".join(s.lower().split()).strip(EN_EDGE)
    for lead in EN_LEAD:
        if s.startswith(lead) and len(s) > len(lead):
            s = s[len(lead):].strip(EN_EDGE)
            break
    return s


def en_key_of(piece: str):
    """-> ``(key, kind)``: kind ``eq`` (an equivalent), ``x`` (an EXPLANATION: the piece is all
    brackets — not indexed, site decisions 148 item 1), ``m`` (only a Norwegian mention), ``""``
    (nothing left)."""
    k = en_norm(en_strip_brackets(piece.strip()))
    if k:
        return k, "eq"
    if "(" in piece or "[" in piece:
        return "", "x"
    if "{" in piece:
        return "", "m"
    return "", ""


def en_letter(key: str) -> str:
    """The English shard a key or a query lives in: the first character of ``bare(key)``, a to z,
    else ``misc``. lookup.js ``enLetter``."""
    c = bare(key)[:1]
    return c if "a" <= c <= "z" else MISC_SHARD


# British and American: the glosses are British (no American spelling in them, measured by the
# lab, 2026-10-29), so the map runs American -> British, applied to the query word by word.

#: Named pairs, American -> British (the lab's list).
EN_PAIRS = {"color": "colour", "gray": "grey", "center": "centre", "tire": "tyre",
            "theater": "theatre", "meter": "metre", "liter": "litre", "fiber": "fibre",
            "favor": "favour", "honor": "honour", "humor": "humour", "labor": "labour",
            "neighbor": "neighbour", "harbor": "harbour", "behavior": "behaviour", "odor": "odour",
            "rumor": "rumour", "vapor": "vapour", "flavor": "flavour", "armor": "armour",
            "plow": "plough", "mold": "mould", "jewelry": "jewellery", "aluminum": "aluminium",
            "defense": "defence", "offense": "offence", "pajamas": "pyjamas",
            "catalog": "catalogue", "traveler": "traveller", "skeptical": "sceptical",
            "cozy": "cosy", "mustache": "moustache"}
#: -ise words that are -ise in American too (never mapped).
EN_ISE_KEEP = frozenset("""advertise advise apprise arise chastise circumcise comprise compromise
demise despise devise disguise enterprise excise exercise expertise franchise improvise incise
merchandise premise promise revise rise supervise surmise surprise televise treatise wise otherwise
likewise clockwise raise praise noise poise precise concise paradise porpoise tortoise anise mortise
valise reprise cerise guise bruise cruise cheese mise vise sunrise moonrise uprise counterwise
lengthwise crosswise anticlockwise streetwise practise""".split())
#: The keep words matched only whole, never as a word's end: the lab matched every keep word as
#: an end, so *organise* (… *anise*), *memorise*, *categorise* (… *rise*), *summarise* (… *arise*)
#: and *economise* (… *mise*) were never mapped (found by this build's tests, 2026-10-29).
EN_ISE_WHOLE = frozenset(("rise", "arise", "anise", "mise"))
_EN_ISE = re.compile(r"^([a-z]{3,})is(e|es|ed|ing|er|ers|ation|ations|able)$")
_EN_OUR = re.compile(r"^([a-z]{2,})our(s|ed|ing|ful|less|ite|ites|able|er|ers)?$")
EN_OUR_KEEP = frozenset("""our ours four hour hours pour pours poured pouring sour soured tour tours
toured touring your yours flour flours scour scoured scouring devour devoured devouring dour contour
contours detour detours amour paramour troubadour velour glamour""".split())


def en_american_of(tok: str) -> list:
    """The American spellings of one British gloss word, by the lab's rules (or [])."""
    out = []
    m = _EN_ISE.match(tok)
    base = m.group(1) + "ise" if m else ""
    if m and not any(base == k or (k not in EN_ISE_WHOLE and base.endswith(k)) for k in EN_ISE_KEEP):
        out.append(m.group(1) + "iz" + m.group(2))
    m = _EN_OUR.match(tok)
    if m and tok not in EN_OUR_KEEP and (m.group(1) + "our") not in EN_OUR_KEEP:
        out.append(m.group(1) + "or" + (m.group(2) or ""))
    for am, br in EN_PAIRS.items():
        if br.endswith("re") and am.endswith("er"):          # centre: centres, centred, centring
            forms = {br: am, br + "s": am + "s", br + "d": am + "ed", br[:-1] + "ing": am + "ing"}
            if tok in forms:
                out.append(forms[tok])
            continue
        for suf in ("", "s", "ed", "ing", "ish", "y", "ful", "less", "ers", "er"):
            if tok == br + suf:
                out.append(am + suf)
    return out


def en_spelling_map(keys) -> dict:
    """``{american: british}`` for the words of ``keys`` (the -ise, -isation, -our words the
    glosses contain, with their inflections), then the named pairs."""
    sp = {}
    for k in sorted(keys):
        for tok in re.findall(r"[a-z]+", k):
            for am in en_american_of(tok):
                sp.setdefault(am, tok)
    for am, br in EN_PAIRS.items():
        sp.setdefault(am, br)
    return sp


#: Irregular English verb forms -> their base (site decisions 148 item 7: "a small table of
#: irregular English verb forms written by you"), for the similar words' stem rule: *swam*,
#: *swum* -> *swim*. A form that is just as often another word in the glosses (*ground*, *wound*,
#: *saw*, *left*, *bit*, *rose*, *fell*, *bound*, *bore*, *stole*, *shot*, *drunk*,
#: *broke*, *found*, *born*, *lay*, *spat*, *rung*) is left out, so it never pairs with a verb it
#: only looks like. Written for this build (2026-10-29), not taken from any list.
EN_IRREGULAR = {
    "arise": "arose arisen", "awake": "awoke awoken", "be": "was were been",
    "bear": "borne", "beat": "beaten", "become": "became", "begin": "began begun",
    "bend": "bent", "bite": "bitten", "bleed": "bled", "blow": "blew blown",
    "break": "broken", "breed": "bred", "bring": "brought", "build": "built", "burn": "burnt",
    "buy": "bought", "catch": "caught", "choose": "chose chosen", "cling": "clung",
    "come": "came", "creep": "crept", "deal": "dealt", "dig": "dug", "do": "did done does",
    "draw": "drew drawn", "dream": "dreamt", "drink": "drank", "drive": "drove driven",
    "eat": "ate eaten", "fall": "fallen", "feed": "fed", "feel": "felt", "fight": "fought",
    "find": "", "flee": "fled", "fling": "flung", "fly": "flew flown", "forbid": "forbade forbidden",
    "forget": "forgot forgotten", "forgive": "forgave forgiven", "freeze": "froze frozen",
    "get": "got gotten", "give": "gave given", "go": "went gone goes", "grow": "grew grown",
    "hang": "hung", "have": "had has", "hear": "heard", "hide": "hid hidden", "hold": "held",
    "keep": "kept", "kneel": "knelt", "know": "knew known", "lead": "led", "lean": "leant",
    "leap": "leapt", "learn": "learnt", "lend": "lent", "lie": "lain", "light": "lit",
    "lose": "lost", "make": "made", "mean": "meant", "meet": "met", "pay": "paid",
    "ride": "rode ridden", "ring": "rang", "rise": "risen", "run": "ran", "say": "said",
    "see": "seen", "seek": "sought", "sell": "sold", "send": "sent", "sew": "sewn",
    "shake": "shook shaken", "shine": "shone", "shoot": "", "show": "shown",
    "shrink": "shrank shrunk", "sing": "sang sung", "sink": "sank sunk", "sit": "sat",
    "sleep": "slept", "slide": "slid", "sling": "slung", "smell": "smelt", "speak": "spoke spoken",
    "speed": "sped", "spell": "spelt", "spend": "spent", "spill": "spilt", "spin": "spun",
    "spoil": "spoilt", "spring": "sprang sprung", "stand": "stood", "steal": "stolen",
    "stick": "stuck", "sting": "stung", "stink": "stank stunk", "stride": "strode stridden",
    "strike": "struck stricken", "string": "strung", "strive": "strove striven",
    "swear": "swore sworn", "sweep": "swept", "swell": "swollen", "swim": "swam swum",
    "swing": "swung", "take": "took taken", "teach": "taught", "tear": "tore torn",
    "tell": "told", "think": "thought", "throw": "threw thrown", "tread": "trod trodden",
    "understand": "understood", "wake": "woke woken", "wear": "wore worn",
    "weave": "wove woven", "weep": "wept", "win": "won", "withdraw": "withdrew withdrawn",
    "write": "wrote written",
}
#: form -> base, from ``EN_IRREGULAR``.
EN_FORM_BASE = {f: b for b, forms in EN_IRREGULAR.items() for f in forms.split()}


def en_stems(w: str) -> list:
    """A word's possible stems, for the similar English words (site decisions 148 item 7): the
    lab's rough English (``stems``: swimming -> swim, houses -> house, tries -> try) WITHOUT -er
    (it gave *runner* for *running*), then the base of an irregular form (``EN_FORM_BASE``: swam
    -> swim). Not a lemmatizer: two words are paired when their stems meet. lookup.js
    ``enStems`` (the irregular forms ride in each shard's ``ir``)."""
    out = [w]

    def add(s):
        if len(s) >= 3 and s not in out:
            out.append(s)

    def cut(suf):
        if len(w) < len(suf) + 3 or not w.endswith(suf):
            return
        b = w[:-len(suf)]
        add(b)
        add(b + "e")
        if len(b) > 3 and b[-1] == b[-2]:
            add(b[:-1])

    for suf in ("ing", "ed", "es", "s"):
        cut(suf)
    if len(w) > 4 and (w.endswith("ies") or w.endswith("ied")):
        add(w[:-3] + "y")
    base = EN_FORM_BASE.get(w)
    if base and base not in out:
        out.append(base)
    return out


def en_rank(w: list, aid: int):
    """The tie-break of one article inside one band (the lab's ``r``): the suggestions' own
    (lookup.js ``completions``: the first spelling's length, folded, as spelled), then the
    homograph order (``homograph_order``: an unnumbered article, the verbs by number, the rest
    by number), the id last."""
    hg = w[1] if len(w) > 1 else 0
    pos = w[2] if len(w) > 2 else ""
    first = str(w[0]).replace(" …", "").split(SEP)[0]
    h = hg[0] if isinstance(hg, list) else hg
    return (len(first), first.lower(), first) + homograph_order({"hg": h or 0, "pos": pos, "id": aid})


def english_index(library: dict, words: dict, bands: dict, translated) -> dict:
    """The English index in memory, from the library's summary glosses (``library_pass``'s
    ``en``): only the rows translated on the site (``translated``) and searchable (``words``).
    -> ``{"a": {id: [display, hg, pos, band, rank, units]}, "k": {key: [[id, unit, place,
    start, end], …]}, "d": {key: display}, "sp": {american: british}, "stats": {…}}`` — ``units``
    the gloss's units as the site draws them (``sitegen.article._plain``), ``start`` / ``end`` the
    equivalent's span in its unit's text (what the list view marks bold); ``band`` the highest
    band of the spellings the article shows (``bands``: decisions 55's, one per headword string);
    ``rank`` the place in ``en_rank``'s order over every indexed article."""
    from ordpar.sitegen.article import _plain    # a pure string function: markers to visible words
    tr = set(translated)
    arts, keys, display = {}, {}, {}
    st = {"glossed": 0, "glossed_not_on_site": 0, "units": 0, "equivalents": 0,
          "explanations_not_indexed": 0, "mention_only": 0}
    for aid in sorted(library):
        g = library[aid].get("en") or []
        if not g:
            continue
        st["glossed"] += 1
        w = words.get(aid)
        if aid not in tr or not w:
            st["glossed_not_on_site"] += 1
            continue
        units = []
        for ui, unit in enumerate(g, 1):
            st["units"] += 1
            text = ""
            for pi, (piece, sep) in enumerate(en_split_unit(unit), 1):
                shown = _plain(piece)
                start = len(text)
                text += shown
                end = len(text)
                text += sep
                k, kind = en_key_of(piece)
                if kind == "x":
                    st["explanations_not_indexed"] += 1
                if kind == "m":
                    st["mention_only"] += 1
                if kind != "eq":
                    continue
                st["equivalents"] += 1
                keys.setdefault(k, []).append([aid, ui, pi, start, end])
                shown_key = " ".join(en_strip_brackets(piece).split()).strip(EN_EDGE)
                for lead in ("to ", "a ", "an ", "the ", "To ", "A ", "An ", "The "):
                    if shown_key.startswith(lead) and len(shown_key) > len(lead):
                        shown_key = shown_key[len(lead):].strip(EN_EDGE)
                        break
                if shown_key != k:
                    display.setdefault(k, {}).setdefault(shown_key, 0)
                    display[k][shown_key] += 1
            units.append(text.strip())
        forms = str(w[0]).replace(" …", "").split(SEP)
        n = max([bands.get(f, 0) for f in forms] or [0])
        arts[aid] = [w[0], w[1] if len(w) > 1 else 0, w[2] if len(w) > 2 else "", n, 0, units]
    for r, aid in enumerate(sorted(arts, key=lambda i: en_rank(words[i], i))):
        arts[aid][4] = r
    # a key's display: its own (lower case) unless every occurrence is written otherwise (AIDS)
    disp = {}
    for k, forms in display.items():
        if len(keys[k]) - sum(forms.values()) <= 0:
            disp[k] = max(sorted(forms.items()), key=lambda kv: kv[1])[0]
    sp = en_spelling_map(keys)
    st.update({"articles": len(arts), "keys": len(keys),
               "one_word_keys": sum(1 for k in keys if " " not in k and "-" not in k),
               "spelling_map": len(sp), "irregular_forms": len(EN_FORM_BASE)})
    return {"a": arts, "k": keys, "d": disp, "sp": sp, "stats": st}


def en_tokens(key: str) -> list:
    """A key's words, as the similar words' phrase rule splits it (lookup.js: at spaces and
    hyphens)."""
    return [t for t in re.split(r"[\s\-]+", key) if t]


def english_files(idx: dict, dict_articles: int) -> dict:
    """``{letter: shard}`` — one file per first letter (``en_letter``), so a search, its
    suggestions and its similar words read ONE file (site decisions 148 item 1). A shard holds
    every key of its letter, and besides them: every key of two or more words with a word of its
    letter (the similar words' "go swimming" for *swimming*), the keys of an irregular pair or a
    spelling pair whose other half starts with another letter (*went* / *go*), each with its
    entries; each article any of them names once (``a``); the display of its keys (``d``); the
    spelling map's entries of its letter (``sp``); the irregular forms of its letter, or of a
    base of its letter (``ir``); and the miss line's numbers (``c`` the articles indexed, ``p``
    their share of the dictionary's ``dict_articles``, a whole percent)."""
    keys = idx["k"]
    by = defaultdict(set)
    for k in keys:
        by[en_letter(k)].add(k)
        toks = en_tokens(k)
        if len(toks) > 1:
            for t in toks:
                by[en_letter(t)].add(k)
    pairs = [(f, b) for f, b in EN_FORM_BASE.items()] + list(idx["sp"].items())
    for a_, b_ in pairs:
        la, lb = en_letter(a_), en_letter(b_)
        if la == lb:
            continue
        for k in (a_, b_):
            if k in keys:
                by[la].add(k)
                by[lb].add(k)
        # a spelling pair's phrases: "color film" is searched as "colour film"
        for k in keys:
            if k.split(" ", 1)[0] == b_:
                by[la].add(k)
    covered = len(idx["a"])
    pct = int(100 * covered / dict_articles + 0.5) if dict_articles else 0
    out = {}
    letters = set(by) | {en_letter(a_) for a_ in idx["sp"]}
    for L in sorted(letters):
        ks = sorted(by.get(L, ()))
        ids = sorted({e[0] for k in ks for e in keys[k]})
        out[L] = {"v": 1, "k": L,
                  "e": {k: keys[k] for k in ks},
                  "a": {str(i): idx["a"][i] for i in ids},
                  "d": {k: idx["d"][k] for k in ks if k in idx["d"]},
                  "sp": {a_: b_ for a_, b_ in idx["sp"].items() if en_letter(a_) == L},
                  "ir": {f: b for f, b in EN_FORM_BASE.items()
                         if en_letter(f) == L or en_letter(b) == L},
                  "c": covered, "p": pct}
    return out


#: The folder under `out/index/en/` of the English tails files (site decisions 148's follow-up).
EN_TAILS_DIR = "tails"


def en_one_word(key: str) -> bool:
    """A key the similar words compare letter by letter: one word, no space, no hyphen
    (lookup.js ``englishSimilar``'s spelled-alike branch)."""
    return " " not in key and "-" not in key


def en_tail_key(key: str) -> str:
    """The English tails file a one-word key lives in: the keys of its second and third BARE
    characters (``tail_key``, the Norwegian ``tails/`` rule): ``house`` -> ``o-u``,
    ``loose`` -> ``o-o``, ``choose`` -> ``h-o``. A search for *hoose* reads ``o-o`` (a wrong
    first letter: *loose*) and ``h-o`` (a missing one: *choose*), ``remainder_key`` of the
    query without its first character and of the query."""
    return tail_key(key)


def english_tails(idx: dict) -> dict:
    """``{tail key: file}`` — the English one-word keys again, filed by their second and third
    characters (site decisions 148's follow-up, Robin 2026-10-29: "the English similar words
    reach other first letters as the Norwegian ones do"), what the similar words read, after
    the results are painted, to reach a wrong or a missing first letter. Each file carries what a
    similar row needs and nothing more, so no letter file is fetched for a row: ``e`` {key:
    [[id, unit, place], …]} (the order (c) of the row's headwords, the ids for 149's rule),
    ``a`` {id: [first spelling, its numeral, pos, band, rank]} (the row draws the first spelling
    alone, Robin 2026-10-29: "enough to show the Norwegian main-lemma"), ``d`` the keys'
    display. No spans, no gloss units: a row draws neither."""
    keys = idx["k"]
    by = defaultdict(list)
    for k in keys:
        if en_one_word(k):
            by[en_tail_key(k)].append(k)
    out = {}
    for t in sorted(by):
        ks = sorted(by[t])
        ids = sorted({e[0] for k in ks for e in keys[k]})
        arts = {}
        for i in ids:
            x = idx["a"][i]
            first = str(x[0]).replace(" …", "").split(SEP)[0]
            hg = x[1][0] if isinstance(x[1], list) and x[1] else (x[1] if not isinstance(x[1], list) else 0)
            arts[str(i)] = [first, hg or 0, x[2], x[3], x[4]]
        out[t] = {"v": 1, "t": t,
                  "e": {k: [e[:3] for e in keys[k]] for k in ks},
                  "a": arts,
                  "d": {k: idx["d"][k] for k in ks if k in idx["d"]}}
    return out


def english_pool(idx: dict) -> dict:
    """Random word's English pool (site decisions 155, Robin 2026-10-31: with "Search English
    words" on, "it chooses a random English word"; the pool his pick, "every English word the
    English suggestions can offer, each equally likely"): ``{letter: [key, …]}`` — every key of
    the English index under its own file's letter (``en_letter``; a phrase a file also carries for
    another letter's sake counts in its own letter's only, so each word once), less the keys the
    suggestions can never offer: those whose display, typed, does not reach the key itself
    (``en_norm``), such as "the point" (from "to the point"), whose "the" the search drops.
    Sorted. lookup.js ``enPool`` takes the same keys from a loaded file."""
    out = defaultdict(list)
    for k in sorted(idx["k"]):
        if en_norm(idx["d"].get(k, k)) == k:
            out[en_letter(k)].append(k)
    return dict(out)


def english_random(idx: dict) -> dict:
    """``random-en.json`` (site decisions 155): ``{"v": 1, "n": {letter: count}}``, the number
    of pool words in each English file (``english_pool``) and nothing else. lookup.js
    ``randomEnglish`` draws ONE number below their sum, which picks the file (weighted by its
    count) and the place in its pool (uniform), so every word is equally likely, and loads only
    that file — the one the word's search then reads anyway. A list of the words themselves
    would be a second copy of the files' keys: 195 KB, 63 KB gzipped, on 2026-10-31, against
    this file's 0.2 KB (the brief's two ways, measured)."""
    return {"v": 1, "n": {L: len(ks) for L, ks in sorted(english_pool(idx).items())}}


def write_english(index_dir: str, library: dict, words: dict, bands: dict, translated,
                  dict_articles: int) -> dict:
    """Write ``out/index/en/<letter>.json`` (``english_files``) and return the manifest's
    ``english`` note: the index's counts, each file's size raw and gzipped, the totals and the
    largest."""
    idx = english_index(library or {}, words, bands, translated)
    files = english_files(idx, dict_articles)
    notes = []
    for L, shard in files.items():
        blob = dump(shard)
        raw = write_bytes(os.path.join(index_dir, EN_DIR, L + ".json"), blob)
        notes.append({"k": L, "file": EN_DIR + "/" + L + ".json", "keys": len(shard["e"]),
                      "articles": len(shard["a"]), "raw": raw, "gzip": gz_size(blob)})
    big = max(notes, key=lambda n: n["gzip"]) if notes else None
    # site decisions 148's follow-up: the tails files, `en/tails/<k2>-<k3>.json`
    tails = []
    for t, data in english_tails(idx).items():
        blob = dump(data)
        raw = write_bytes(os.path.join(index_dir, EN_DIR, EN_TAILS_DIR, t + ".json"), blob)
        tails.append({"k": t, "keys": len(data["e"]), "articles": len(data["a"]), "raw": raw,
                      "gzip": gz_size(blob)})
    tbig = max(tails, key=lambda n: n["gzip"]) if tails else None
    # site decisions 155: Random word's English pool, the count of each file's words
    rnd = english_random(idx)
    r_blob = dump(rnd)
    r_raw = write_bytes(os.path.join(index_dir, "random-en.json"), r_blob)
    return dict(idx["stats"], files=notes, raw=sum(n["raw"] for n in notes),
                random={"file": "random-en.json", "count": sum(rnd["n"].values()),
                        "left_out": len(idx["k"]) - sum(rnd["n"].values()),
                        "raw": r_raw, "gzip": gz_size(r_blob)},
                gzip=sum(n["gzip"] for n in notes), largest=big and big["k"],
                largest_gzip=big and big["gzip"], dict_articles=dict_articles,
                tails={"files": tails, "count": len(tails), "raw": sum(n["raw"] for n in tails),
                       "gzip": sum(n["gzip"] for n in tails), "largest": tbig and tbig["k"],
                       "largest_gzip": tbig and tbig["gzip"]})


class EnglishIndex:
    """The read side of ``out/index/en/``, the Python twin of lookup.js's English search, for
    the tests and the build's report: ``matches`` (the results in order (c)), ``suggest``,
    ``similar``. Reads the shard of the query's letter only, as the page does."""

    def __init__(self, index_dir: str):
        self.dir = os.path.join(index_dir, EN_DIR)
        self.cache = {}

    def shard(self, letter: str) -> dict:
        if letter not in self.cache:
            p = os.path.join(self.dir, letter + ".json")
            self.cache[letter] = None
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    self.cache[letter] = json.load(fh)
        return self.cache[letter]

    def tails(self, key: str) -> dict:
        """One English tails file (``en/tails/<key>.json``), or None."""
        name = EN_TAILS_DIR + "/" + key
        if name not in self.cache:
            p = os.path.join(self.dir, EN_TAILS_DIR, key + ".json")
            self.cache[name] = None
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    self.cache[name] = json.load(fh)
        return self.cache[name]

    @staticmethod
    def variants(q: str, shard: dict) -> list:
        out = [q]
        sp = (shard or {}).get("sp") or {}
        t = " ".join(sp.get(w, w) for w in q.split(" "))
        if t != q:
            out.append(t)
        return out

    @staticmethod
    def order(shard: dict):
        """Order (c), Robin 2026-10-29 ("C seems like a good compromise"): units 1 and 2 as one
        tier, then unit 3 on; inside a tier the band, highest first; then the unit, the place in
        the unit, the article's rank. lookup.js ``enOrder``."""
        def key(m):
            a = shard["a"][str(m["id"])]
            return (0 if m["unit"] <= 2 else 1, -a[3], m["unit"], m["pos"], a[4])
        return key

    def matches(self, q: str) -> list:
        """The articles an English search finds, exact equivalents only, in order (c):
        [{id, unit, pos, spans}] — ``spans`` every matched equivalent's [unit, start, end]."""
        p = en_norm(q)
        shard = self.shard(en_letter(p)) if p else None
        if not shard:
            return []
        by = {}
        for v in self.variants(p, shard):
            for e in shard["e"].get(v, []):
                m = by.get(e[0])
                if not m:
                    m = by[e[0]] = {"id": e[0], "unit": e[1], "pos": e[2], "spans": []}
                elif (e[1], e[2]) < (m["unit"], m["pos"]):
                    m["unit"], m["pos"] = e[1], e[2]
                m["spans"].append([e[1], e[3], e[4]])
        return sorted(by.values(), key=self.order(shard))

    def item(self, shard: dict, key: str) -> dict:
        seen, arts = set(), []
        for e in shard["e"].get(key, []):
            if e[0] not in seen:
                seen.add(e[0])
                arts.append({"id": e[0], "unit": e[1], "pos": e[2]})
        arts.sort(key=self.order(shard))
        return {"key": key, "word": shard["d"].get(key, key), "ids": [a["id"] for a in arts]}

    def suggest(self, typed: str, limit: int = 20) -> list:
        """One item per English word: the exact word, then one-word continuations by the top
        band of their Norwegian words, then phrases by length (the lab's ``sord: band``), up to
        ``limit``. lookup.js ``englishSuggest``."""
        p = en_norm(typed)
        shard = self.shard(en_letter(p)) if p else None
        if not shard:
            return []
        vs = self.variants(p, shard)
        items = []
        for k in shard["e"]:
            rank = -1
            for v in vs:
                if k == v:
                    rank = 0
                    break
                if k.startswith(v):
                    r = 1 if " " not in k else 2
                    rank = r if rank < 0 else min(rank, r)
            if rank < 0:
                continue
            top = max(shard["a"][str(e[0])][3] for e in shard["e"][k])
            items.append((rank, -top if rank == 1 else 0, len(k), k))
        items.sort()
        return [self.item(shard, it[3]) for it in items[:limit]]

    def similar(self, q: str, n: int = 5, shown=()) -> list:
        """The similar English words (site decisions 148 item 7): first the word matches — a
        longer equivalent holding the searched word as a whole word, a word sharing its stem
        (``en_stems``, the shard's ``ir``) — then the one-word keys spelled alike, within one edit
        per three letters (``letter_limit``); ranked word match first, then the distance, the top
        band, the length, the key. Site decisions 149: a word whose articles are all in
        ``shown`` (the ids on the page) is left out and the next takes its place. lookup.js
        ``englishSimilar``."""
        p = en_norm(q)
        if len(p) < 3:
            return []
        shard = self.shard(en_letter(p))
        if not shard:
            return []
        ir = shard.get("ir") or {}
        lim = letter_limit(len(p))

        def stems(w):
            out = en_stems(w)
            b = ir.get(w)
            if b and b not in out:
                out.append(b)
            return out

        mine = set(stems(p)) | set(self.variants(p, shard))
        shown = set(shown)
        out = []
        for k, es in shard["e"].items():
            if k in self.variants(p, shard):
                continue
            ids = {e[0] for e in es}
            if ids and ids <= shown:
                continue
            if " " in k or "-" in k:
                if p not in en_tokens(k):
                    continue
                w, d = 0, 0
            elif mine & set(stems(k)):
                w, d = 0, 0
            else:
                if en_letter(k) != en_letter(p):
                    continue
                d = osa(p, k, lim)
                if d > lim:
                    continue
                w = 1
            top = max(shard["a"][str(i)][3] for i in ids)
            out.append((w, d, -top, len(k), k, shard))
        # site decisions 148's follow-up (Robin, 2026-10-29: "the English similar words reach
        # other first letters as the Norwegian ones do"): a wrong first letter through the tails
        # file of the query without its first character (hoose -> loose), a missing one through
        # the query's own (hoose -> choose), an extra one through the second letter's file, its
        # keys starting with that letter (xhouse -> house); one-word keys, spelled alike only
        seen = {x[4] for x in out} | set(self.variants(p, shard))
        b = bare(p)
        pools = [self.tails(remainder_key(b[1:])), self.tails(remainder_key(b))]
        second = self.shard(en_letter(b[1:]))
        if second:
            pools.append({"e": {k: es for k, es in second["e"].items()
                                if en_one_word(k) and bare(k)[:1] == b[1:2]},
                          "a": second["a"], "d": second.get("d") or {}})
        for pool in pools:
            if not pool:
                continue
            for k, es in pool["e"].items():
                if k in seen:
                    continue
                seen.add(k)
                ids = {e[0] for e in es}
                if ids and ids <= shown:
                    continue
                d = osa(p, k, lim)
                if d > lim:
                    continue
                top = max(pool["a"][str(i)][3] for i in ids)
                out.append((1, d, -top, len(k), k, pool))
        out.sort(key=lambda x: x[:5])
        return [self.item(x[5], x[4]) for x in out[:n]]


# --------------------------------------------------------------------------- #
# the word pages and form pages (site decisions 117)
# --------------------------------------------------------------------------- #

#: Where the article build leaves the article pages its sitemap lists (`build_site.py`
#: `write_sitemap`), so that this build, which rewrites `sitemap.xml` with the word pages, reads
#: the same list on every run (outside `out/`, as the snippets)
SITEMAP_ARTICLES_PATH = os.path.join(ROOT, "ordpar", ".build", "sitemap-articles.json")


def write_word_pages(out: str, plan: dict, snippets: dict, snippet_max=SNIPPET_MAX,
                     headwords_of=None) -> dict:
    """Write every page of ``plan`` (``page_plan``) to ``out/bm-en/<fold>/index.html``, remove
    the word pages an earlier build left that the plan no longer has, send each article page's
    canonical (and link-preview address) to its word page where the plan says so and its "N
    more entries for …" link to the word's page where there is one (``wordpages.patch_article``),
    and rewrite ``out/sitemap.xml``: home, About, Help, Coming, every canonical word page, every form
    page, every translated article page still its own canonical (decisions 117, 128).
    Build the articles first: a one-article word page takes the article page's own title and
    description from the built page. ``headwords_of`` (``{id: [headwords]}``, every article
    the mirror carries, in search or not) widens the article pages looked at to every page
    whose headword has a word page: an article outside search (decisions 46) still links its
    word's other entries. -> the counts."""
    W = wordpages_mod
    s = chrome_mod.strings("en")
    assets = {h: "%s?v=%s" % (h, asset_hash(out, h[len("/site/"):]))
              for h in (head_mod.THEME_JS_HREF, "/site/ordpar.css", "/site/ordpar.js")}
    t0 = time.time()

    def snip(a):
        got = snippets.get(a["id"]) or ("", "")
        text = snippet_text(got[0], snippet_max) if got[0] else ""
        # site decisions 152: a translated article's first Norwegian definition, for the built
        # row's hidden Norwegian line (`wordpages._snip_span`)
        nb = (snippet_text(got[4], snippet_max) if len(got) > 4 and got[4] and a.get("translated")
              else "")
        return text, bool(text and len(got) > 3 and got[3] and a.get("translated")), nb

    def gloss_text(a):
        """shell.js `glossText`: the set-phrase box, else the snippet's first unit."""
        got = snippets.get(a["id"]) or ("", "")
        drop = (snippet_text(got[2], snippet_max) if len(got) > 2 and got[2] is not None
                and a.get("translated") else "")
        if drop:
            return drop
        text = snippet_text(got[0], snippet_max) if got[0] else ""
        return text.split(" · ")[0] if text else ""

    bm = os.path.join(out, wordpages_mod.PAIR)
    counts = defaultdict(int)
    written_bytes = 0
    descriptions = {}
    for kind in ("words", "forms"):
        for fq, pg in sorted(plan[kind].items()):
            word = pg["form"]
            if kind == "words" and len(pg["arts"]) == 1:
                meta = W.article_meta(out, pg["arts"][0]["id"])
                if meta is None:
                    counts["one_article_without_page"] += 1
                    meta = (W.several_title(word, s), W.several_description(pg["arts"], gloss_text, s, word))
                title, desc = meta
            elif kind == "words":
                title = W.several_title(word, s)
                desc = W.several_description(pg["arts"], gloss_text, s, word)   # 154: the word first
            else:
                title = W.several_title(word, s)
                desc = W.form_description(word, [a for _f, arts in pg["rows"] for a in arts],
                                          gloss_text, s, word=True)   # 154: the form first
            descriptions[fq] = (title, desc)
            html = W.render(fq=fq, word=word, title=title, description=desc,
                            canonical=W.word_path(plan["canonical"][fq]), s=s, assets=assets,
                            snip=snip, page={"count": pg["count"], "arts": pg["arts"],
                                             "forms": pg["rows"]})
            written_bytes += write_bytes(os.path.join(bm, fq, "index.html"), html.encode("utf-8"))
            counts[kind] += 1
    planned = set(plan["words"]) | set(plan["forms"])
    removed = 0
    for e in os.scandir(bm):
        if not e.is_dir() or e.name.isdigit() or unicodedata.normalize("NFC", e.name) in planned:
            continue
        idx_html = os.path.join(e.path, "index.html")
        if os.path.exists(idx_html):
            with open(idx_html, encoding="utf-8") as fh:
                mine = "data-ordpar-word=" in fh.read()
            if mine:
                shutil.rmtree(e.path)
                removed += 1
    t_pages = time.time() - t0

    # the article pages: their canonical, and their "N more entries" link
    has_page = plan["words"].__contains__
    candidates = set(plan["article_canonical"])
    for pg in plan["words"].values():
        candidates.update(a["id"] for a in pg["arts"])
    for aid, hws in (headwords_of or {}).items():
        if any(fold(h) in plan["words"] for h in hws):
            candidates.add(aid)
    patched = missing = 0
    for aid in sorted(candidates):
        path = os.path.join(bm, str(aid), "index.html")
        if not os.path.exists(path):
            missing += 1
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        canon = (W.word_path(plan["article_canonical"][aid]) if aid in plan["article_canonical"]
                 else "/%s/%d/" % (W.PAIR, aid))
        new = W.patch_article(text, aid, canon, has_page)
        if new is not None:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new)
            patched += 1

    # the sitemap
    arts = None
    if os.path.exists(SITEMAP_ARTICLES_PATH):
        with open(SITEMAP_ARTICLES_PATH, encoding="utf-8") as fh:
            arts = json.load(fh)
    if arts is None:
        arts = W.sitemap_articles(os.path.join(out, "sitemap.xml"))
    moved = set(plan["article_canonical"])
    paths = list(W.indexed_other(out))       # /thanks/ only where the article build wrote it (166)
    paths += [W.word_path(fq) for fq in sorted(plan["words"]) if plan["canonical"][fq] == fq]
    paths += [W.word_path(fq) for fq in sorted(plan["forms"])]
    kept = [a for a in arts if a not in moved]
    paths += ["/%s/%d/" % (W.PAIR, a) for a in sorted(kept)]
    sm = W.write_sitemap(os.path.join(out, "sitemap.xml"), paths)
    if sm["urls"] > SITEMAP_MAX:
        sys.exit("sitemap.xml holds %d addresses, over the %d one file may hold: split it into a "
                 "sitemap index" % (sm["urls"], SITEMAP_MAX))
    return {"word_pages_written": counts["words"], "form_pages_written": counts["forms"],
            "pages_bytes": written_bytes, "stale_pages_removed": removed,
            "one_article_without_page": counts["one_article_without_page"],
            "articles_patched": patched, "articles_missing": missing,
            "sitemap_urls": sm["urls"], "sitemap_bytes": sm["bytes"],
            "sitemap_word_pages": sum(1 for fq in plan["words"] if plan["canonical"][fq] == fq),
            "sitemap_form_pages": len(plan["forms"]), "sitemap_articles": len(kept),
            "sitemap_articles_dropped": len(arts) - len(kept),
            "seconds_pages": round(t_pages, 1), "seconds_total": round(time.time() - t0, 1),
            "_descriptions": descriptions}


#: One sitemap file holds at most 50,000 addresses (the sitemaps protocol)
SITEMAP_MAX = 50000


# --------------------------------------------------------------------------- #
# the shell: the two pages (the scripts themselves are copied by the ARTICLE build)
# --------------------------------------------------------------------------- #

def asset_hash(out: str, name: str) -> str:
    """The content hash of ``/site/<name>`` as the site serves it: the copy the article build
    wrote to ``out/site/`` (so build the articles first) — since 2026-10-20 every script and
    stylesheet there differs from ``ordpar/site/`` (no comments; the shell pages' pair and
    ``theme.js`` exist only there) — else ``ordpar/site/`` verbatim."""
    path = os.path.join(out, "site", name)
    if not os.path.exists(path):
        path = os.path.join(SITE, name)
    if not os.path.exists(path):
        print(f"  WARNING: /site/{name} is in neither ordpar/site/ nor out/site/ — "
              f"run build_site.py first; linked without a hash")
        return "missing"
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()[:10]


#: The shell pages by where they are written: (their address, indexed?) — site decisions 128: the
#: home page is indexed; the search page (the home page's twin at `/bm-en/`), the 404 page and
#: the device's own pages (History, Favourites, Settings) are `noindex`
SHELL_PAGES = {
    "index.html": ("/", True),
    os.path.join("bm-en", "index.html"): ("/bm-en/", False),
    "404.html": ("/404.html", False),
    os.path.join("favourites", "index.html"): ("/favourites/", False),
    os.path.join("history", "index.html"): ("/history/", False),
    os.path.join("settings", "index.html"): ("/settings/", False),
}
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_DESC_RE = re.compile(r'<meta name="description" content="([^"]*)">')
_ROBOTS_RE = re.compile(r'<meta name="robots" content="[^"]*">\n?')


def site_stats(out: str):
    """The About page's numbers as the article build recorded them (`build.json` `site_stats`,
    `site_stats.measure()`), or None when there is no build record."""
    path = os.path.join(out, "build.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("site_stats")


def copy_shell(out: str, stats=None) -> dict:
    """Render the two HTML pages. ``lookup.js`` / ``shell.js`` / ``shell.css`` /
    ``strings/en.json`` are NOT copied here: the article build copies ``ordpar/site/``
    wholesale to ``out/site/``, which is the one convention both builds reference
    (``/site/lookup.js``, as build B's ``/site/inflection.js``).

    The strings are **inlined** into every built page (a ``window.ORDPAR_STRINGS`` block
    replacing the ``<!--ORDPAR_STRINGS-->`` marker) so the chrome paints with no second
    request; ``site/strings/<lang>.json`` is what a switch to another language fetches.

    Decisions 63: every page's header and footer are ``sitegen/chrome.py``'s (the
    ``<!--ORDPAR_HEADER-->`` and ``<!--ORDPAR_FOOTER-->`` markers), its head script
    ``sitegen/head.py`` ``THEME_JS`` (``<!--ORDPAR_HEADJS-->``; the file ``/site/theme.js`` since
    2026-10-20) — one copy each, shared with the article build — and the settings page gets the
    colour schemes (``<!--ORDPAR_COLOURS-->``, ``sitegen/colours.py``) and, while the counting is
    live (``chrome.counting()``: ``events.js`` ``RECEIVER`` set; decisions 104, split from the
    privacy page's switch by site decisions 166), ``window.ORDPAR_COUNTING`` in place of
    ``<!--ORDPAR_COUNTING-->`` (nothing while it is off). Since 2026-10-20 the
    pages link the shell pages' one sheet and one blocking script, ``/site/shell-pages.css`` and
    ``/site/shell-pages.js``, which the article build writes (``page.COMBINED``).

    Site decisions 127, 128 (2026-10-25): each page's robots line is its own (``SHELL_PAGES``:
    the home page indexed, the rest ``noindex``; the sources' own robots lines are dropped), its
    link-preview tags are ``head.social_tags`` from its own ``<title>`` and description, and the
    home page's description (the search page's too, the same source) is
    ``describe.home_description`` — its number the About page's figure of translated articles,
    from ``stats`` (default: ``out/build.json``'s ``site_stats``; with no build record, the About
    page's SAMPLE, with a warning — ``main`` refuses to run without one).
    """
    written = {}
    if stats is None:
        stats = site_stats(out)
    if stats is None:
        print("  WARNING: no out/build.json: the home page's count is the About page's SAMPLE")
        stats = about_mod.SAMPLE
    home_desc = describe_mod.home_description(stats, chrome_mod.strings("en"))
    stale = os.path.join(out, "assets")          # the path this build used before 2026-09-20
    if os.path.isdir(stale):
        shutil.rmtree(stale)
    strings_blob = open(os.path.join(SITE, "strings", "en.json"), "rb").read()
    chrome_strings = chrome_mod.strings("en")
    counting = chrome_mod.counting()             # site decisions 166: the stats setting's gate

    # site decisions 131 (117's one style for tab titles): a search answered in place on a word or
    # form page titles the tab as the built page does ("så — Norwegian–English dictionary"), so the
    # inline strings carry the article build's `dictionary_name` (`strings.py`) beside the shell's
    # own, the one string of `strings.py` the shell pages' script reads; never a fixed copy
    extra = ",\n  %s: %s\n}" % (json.dumps("dictionary_name"), json.dumps(
        chrome_strings["dictionary_name"], ensure_ascii=False).replace("<", "\\u003c"))
    inline = ("<script>window.ORDPAR_STRINGS={\"en\":"
              + re.sub(r"\s*\}\s*$", extra, strings_blob.decode("utf-8").strip()) + "};</script>")

    def shell_html(src: str, dest: str, marker: str = "") -> str:
        html = open(os.path.join(SITE, src), encoding="utf-8").read()
        html = html.replace("<!--ORDPAR_STRINGS-->", marker + inline)
        # the head script, a file since 2026-10-20 (parser-blocking, before the sheets; its
        # `?v=` comes with the others below)
        html = html.replace("<!--ORDPAR_HEADJS-->", '<script src="%s"></script>' % head_mod.THEME_JS_HREF)
        html = html.replace("<!--ORDPAR_HEADER-->", chrome_mod.header(chrome_strings).rstrip())
        html = html.replace("<!--ORDPAR_FOOTER-->", chrome_mod.footer(chrome_strings).rstrip())
        html = html.replace("<!--ORDPAR_COLOURS-->", "<script>window.ORDPAR_COLOURS=%s;</script>"
                            % colours_mod.settings_json())
        # decisions 104: the settings page draws "Send usage statistics" only while the counting is
        # live (site decisions 166: `events.js` `RECEIVER`, not the privacy page's switch, so the
        # page can be published with the counting off); off, the page carries no trace
        html = html.replace("<!--ORDPAR_COUNTING-->", "<script>window.ORDPAR_COUNTING=true;</script>"
                            if counting else "")
        # decisions 128 (Robin, 2026-10-25): the home page's description from the build's count
        if src == "search.html":
            html = _DESC_RE.sub(lambda m: '<meta name="description" content="%s">'
                                % html_mod.escape(home_desc, quote=True), html, count=1)
        # decisions 61: the app manifest and theme colour; decisions 128: the page's own robots
        # line (the source's is dropped; `head_tags` writes `noindex` where it belongs);
        # decisions 127: the link-preview tags from the page's own title and description
        path, indexed = SHELL_PAGES[dest]
        html = _ROBOTS_RE.sub("", html)
        t = _TITLE_RE.search(html)
        d = _DESC_RE.search(html)
        social = {"url": path, "title": html_mod.unescape(t.group(1)) if t else "",
                  "description": html_mod.unescape(d.group(1)) if d else ""}
        html = html.replace("<!--ORDPAR_HEAD-->", head_mod.head_tags(indexed=indexed,
                                                                      social=social))
        # `/site/<file>?v=<content hash>`, as on the article pages (sitegen/page.py `asset`),
        # so a browser holding last build's shell.js fetches the new one
        return re.sub(r'"(/site/[\w./-]+\.(?:js|css))"', lambda m: '"%s?v=%s"' % (
            m.group(1), asset_hash(out, m.group(1)[len("/site/"):])), html)

    def render(src: str, dest: str) -> None:
        # decisions 61's leftover (built with 117): the published shell pages carry no comments
        blob = slim_mod.strip_html(shell_html(src, dest)).encode("utf-8")
        written[dest] = write_bytes(os.path.join(out, dest), blob)

    render("search.html", os.path.join("bm-en", "index.html"))
    render("404.html", "404.html")
    # site decisions 60: the favourites and history pages, static shells that render from the
    # device's storage (personal.js); nothing in them comes from the index
    render("favourites.html", os.path.join("favourites", "index.html"))
    render("history.html", os.path.join("history", "index.html"))
    # decisions 63: the settings, a page of their own in place of the header's dialog
    render("settings.html", os.path.join("settings", "index.html"))

    # The front page is build A's as soon as build A writes one; ours only while it has not.
    # Our placeholder carries a marker comment, so a rebuild refreshes our own file and never
    # touches a real front page.
    # The article build's prototype list (`page.PROTOTYPE_FRONT`) is replaced too: the app's
    # start_url is `/` (decisions 61), and that list is no front page. Since 61 the front page
    # gets the same `?v=` hashes and head lines as the other shell pages (it had neither).
    # Since 117 the front page carries no comment, so ours is known by what it is: the search
    # shell (its results container), as the search page is.
    front = os.path.join(out, "index.html")
    mine = (PLACEHOLDER, "<!-- ordpar: prototype front page, written by build_site.py -->",
            "data-ordpar-results")
    if os.path.exists(front) and not any(
            m in open(front, encoding="utf-8").read() for m in mine):
        written["index.html"] = -os.path.getsize(front)  # negative: left as the other build wrote it
    else:
        html = slim_mod.strip_html(shell_html("search.html", "index.html"))
        written["index.html"] = write_bytes(front, html.encode("utf-8"))
    return written


# --------------------------------------------------------------------------- #
# verification — the query algorithms of lookup.js, in Python, over the built index
# --------------------------------------------------------------------------- #

class Index:
    """Read-side twin of ``lookup.js``: same fold, same shard rule, same answers."""

    def __init__(self, index_dir: str):
        self.dir = index_dir
        self._shards = {}
        self._headwords = {}      # letter key -> sorted list
        self._translated = None
        self._buckets = {}        # letter key -> {first bare char: [(bare, folded, form, band)]}
        self._tails = {}          # tails key -> [(bare, folded, form, band)] (decisions 55)
        self._by_bare = {}        # (letter key, first char) -> {bare: entries} (decisions 56)

    def shard(self, key: str) -> dict:
        if key not in self._shards:
            path = os.path.join(self.dir, key + ".json")
            if not os.path.exists(path):
                self._shards[key] = {"heads": {}, "forms": {}, "words": {}, "fh": {}, "ff": {}, "bands": {}}
            else:
                with open(path, encoding="utf-8") as fh:
                    s = json.load(fh)
                s["fh"] = self._folded(s["heads"])
                s["bands"] = shard_bands(s)
                s["ff"] = self._folded(s["forms"])
                self._shards[key] = s
        return self._shards[key]

    @staticmethod
    def _folded(m):
        """bare form -> the stored forms with it (``lookup`` then keeps the accent matches)."""
        out = defaultdict(list)
        for form in m:
            out[bare(form)].append(form)
        return out

    def _similar_file(self, sub: str, key: str) -> list:
        """A similar-words file as ``[(bare, folded, form, band)]`` — ``{"w", "f"}`` since
        decisions 55, a plain list of forms before (every band 0)."""
        cache = self._headwords if sub == "headwords" else self._tails
        if key not in cache:
            path = os.path.join(self.dir, sub, key + ".json")
            data = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            if isinstance(data, list):
                data = {"w": data, "f": ""}
            fs = data.get("f") or ""
            cache[key] = [(bare(w), fold(w), w, int(fs[i], 16) if i < len(fs) else 0)
                          for i, w in enumerate(data.get("w") or [])]
        return cache[key]

    def headwords_of(self, letter: str) -> list:
        """One letter's headword forms (``headwords/<letter>.json``), or []."""
        return [e[2] for e in self._similar_file("headwords", letter)]

    @property
    def headwords(self):
        """Every headword form, all letters (for --time-similar)."""
        hw_dir = os.path.join(self.dir, "headwords")
        return [w for f in sorted(os.listdir(hw_dir))
                for w in self.headwords_of(f[:-len(".json")])]

    @property
    def translated(self):
        if self._translated is None:
            with open(os.path.join(self.dir, "translated.json"), encoding="utf-8") as fh:
                self._translated = set(json.load(fh))
        return self._translated

    def lookup(self, q: str) -> dict:
        q = fold(q.strip())
        bq = bare(q)
        s = self.shard(shard_key(q))

        def group(folded_map, source, matched):
            out = []
            for form in sorted(folded_map.get(bq, [])):
                if not accent_match(q, fold(form)):      # one way: én never finds en
                    continue
                arts = [{"id": i,
                         # an expanded expression shows the variant that matched
                         "word": (form if matched and len(s["words"].get(str(i), [])) > 3
                                  else s["words"].get(str(i), ["", 0, ""])[0]),
                         "hg": (form_hg(s["words"].get(str(i), ["", 0, ""]), form) if matched
                                else form_hg(s["words"].get(str(i), ["", 0, ""]), "")),
                         "pos": s["words"].get(str(i), ["", 0, ""])[2],
                         "translated": i in self.translated}
                        for i in source[form]]
                if matched:                             # what lookup.js renders
                    arts.sort(key=result_order)
                # an inflected form's articles keep their stored order: the build's
                # ``form_order``, most common first (site decisions 143)
                out.append({"form": form, "articles": arts})
            return out

        return dedupe_accent_groups(q, {"query": q,
                                        "heads": group(s["fh"], s["heads"], True),
                                        "forms": group(s["ff"], s["forms"], False)})

    def suggest(self, prefix: str, limit: int = 20):
        """lookup.js ``suggest``: leading spaces dropped and runs of spaces collapsed, a
        TRAILING space honoured (brief 59b item 10, Robin 2026-10-19) — the word itself first,
        then its set phrases ``"<word> …"``, then the ordinary completions."""
        trailing = prefix[-1:].isspace()
        typed = " ".join(prefix.split())
        p = fold(typed)
        if not p:
            return []

        def completions(shard, pre, as_typed):
            bp = bare(pre)
            hits = [w for w in shard["heads"] if bare(w).startswith(bp) and accent_match(pre, fold(w))]
            hits.sort(key=lambda w: suggest_order(w, as_typed))
            return [(w, shard) for w in hits]

        own = self.shard(suggest_key(p))
        hits = [(w, own) for w in sorted(
            (w for w, _ in completions(own, p, typed)),
            key=lambda w: suggest_rank(w, typed, any(i in self.translated for i in own["heads"][w]),
                                       own["bands"].get(w, 0)))]
        if trailing:
            seen, merged = set(), []
            phrases = completions(self.shard(shard_key(p + " ")), p + " ", typed + " ")
            for w, sh in ([h for h in hits if bare(h[0]) == bare(p)] + phrases + hits):
                if w not in seen:
                    seen.add(w)
                    merged.append((w, sh))
            hits = merged
        rows = merge_articles([{"word": w, "ids": list(sh["heads"][w]),
                                "translated": any(i in self.translated for i in sh["heads"][w])}
                               for w, sh in hits])
        return [{"word": r["word"], "translated": r["translated"], "forms": r.get("forms", [r["word"]])}
                for r in rows[:limit]]

    def buckets(self, letter: str):
        """one letter file's headwords bucketed by first folded character — what lookup.js
        builds when it loads that file (``misc`` holds several first characters). Each
        entry is ``(bare, folded, form, band)``, bucketed by the first BARE character."""
        if letter not in self._buckets:
            b = defaultdict(list)
            for e in self._similar_file("headwords", letter):
                b[e[0][:1]].append(e)
            self._buckets[letter] = b
        return self._buckets[letter]

    def tails_of(self, key: str) -> list:
        """One ``tails/<key>.json`` file as ``[(bare, folded, form, band)]`` (decisions 55)."""
        return self._similar_file("tails", key)

    def by_bare(self, letter: str, c: str) -> dict:
        """One bucket of ``buckets(letter)`` keyed by bare form — a rewrite's exact landings
        without a pass over the bucket (decisions 56: chaining multiplies the rewrites)."""
        key = (letter, c)
        if key not in self._by_bare:
            m = defaultdict(list)
            for e in self.buckets(letter).get(c, ()):
                m[e[0]].append(e)
            self._by_bare[key] = m
        return self._by_bare[key]

    def similar(self, q: str, n: int = 5, wide: bool = True):
        """The ``n`` nearest headwords — what lookup.js ``similar`` answers (lookup-index.md
        § 4 (3)). A candidate comes from the query's own first-character bucket and qualifies
        by LETTERS (OSA distance <= ``letter_limit(len(q))``) or, for a query of two words
        or more, by WORDS (at least two words in common in order, with a typo per word
        tolerated, and no more than ``words_limit(m)`` words differing).

        ``wide`` (decisions 55; on a hit and a miss alike since decisions 56, Robin 2026-10-19:
        "The search suggestions on a hit should be the same as for a non-hit"; ``wide=False``
        is kept only to measure against) widens the candidates: (2) the headwords whose
        remainder after the first letter starts like the query's (``tails/``: a wrong first
        letter, *vus* -> *hus*) or like the whole query (a missing one, *us* -> *hus*), and
        the bucket of the query's second letter (an extra letter in front, *ohus* -> *hus*);
        (1) each spelling-variation rewrite (``rewrites``) searched in its own first letter's
        bucket: a rewrite that lands on a headword costs nothing (*kordan* -> *hvordan* at 0),
        a candidate near a rewrite costs 1 + its distance from it, within the same limit; and a
        rewrite that is an inflected form in the query's own shard is offered itself, at 0.
        A chained rewrite (two rules, decisions 56: *kæm* -> *kem* -> *hvem*) costs the same.
        Under a limit of 1 only an exact landing can qualify, so the rewrite is looked up in
        its bucket by bare form (``by_bare``) instead of compared with every headword.

        Ranked (Robin, 2026-10-19): words differing (a word match first), letter distance,
        capitalisation against the query as typed (``case_distance``), the higher frequency band, the query's first letter before another, length difference,
        folded form, form. Another variant of the query's own article is listed like any other headword,
        as ordbokene lists it (*en vond sirkel* -> *en ond sirkel*).

        Accents are folded before comparing (decisions 41 (a)), so an accent is never an edit:
        the distances are between BARE forms. A form the lookup itself finds is never listed;
        the other direction is, at distance 0 — *à la carte* -> *a la carte*, *kafé* -> *kafe*,
        as ordbokene."""
        f = fold(q.strip())
        if not f:
            return []
        bf = bare(f)
        lim = letter_limit(len(bf))
        qw = bf.split()
        m = len(qw)
        wlim = words_limit(m) if m > 1 else -1
        typed = nfc(q.strip())
        cands = {}                      # form -> [wd, d, case, -band, first, gap, folded, form]

        def keep(entry, wd, d):
            bw, fw, w, bnd = entry
            c = cands.get(w)
            if c is None:
                cands[w] = [wd, d, case_distance(typed, w), -bnd, 0 if bw[:1] == bf[:1] else 1,
                            abs(len(bw) - len(bf)), fw, w]
            else:
                c[0] = min(c[0], wd)
                c[1] = min(c[1], d)

        pool = list(self.buckets(letter_key(bf)).get(bf[:1], ()))
        if wide and len(bf) > 1:
            pool += self.tails_of(remainder_key(bf[1:]))          # a wrong first letter
            pool += self.tails_of(remainder_key(bf))              # a missing first letter
            pool += self.buckets(letter_key(bf[1:])).get(bf[1:2], [])  # an extra one in front
        qc, qn = char_counts(bf), len(bf)
        bags = {}                       # bare candidate -> its bag distance from the query

        def bag_of(bw):
            b = bags.get(bw)
            if b is None:
                b = bags[bw] = bag_distance(qc, qn, bw)
            return b

        seen = set()
        for e in pool:
            bw, fw, w, _ = e
            if w in seen:
                continue
            seen.add(w)
            if bw == bf and accent_match(f, fw):    # the query itself, or one of its hits
                continue
            gap = abs(len(bw) - len(bf))
            # the bag distance is a lower bound of OSA: past the limit, no table is needed
            d = osa(bf, bw, lim) if gap <= lim and bag_of(bw) <= lim else lim + 1
            wd = wlim + 1
            if wlim > 0 and " " in bw:
                cw = bw.split()
                if abs(len(cw) - m) <= wlim:
                    c = shared_words(qw, cw)
                    if c >= 2 and max(m, len(cw)) - c <= wlim:
                        wd = max(m, len(cw)) - c
            if d > lim and wd > wlim:
                continue
            if d > lim:                         # a word match: rank it by its true distance
                d = osa(bf, bw, len(bf) + len(bw))
            keep(e, wd, d)
        if wide:
            own = shard_key(bf)
            near = lim - 1                      # 1 + a distance within the limit
            for r in rewrites(bf):
                if near < 1:                    # 1 + any distance > 1: exact landings only
                    bucket = self.by_bare(letter_key(r), r[:1]).get(r, ())
                else:
                    bucket = self.buckets(letter_key(r)).get(r[:1], ())
                rb = bag_distance(qc, qn, r)
                for e in bucket:
                    bw, fw, w, _ = e
                    if bw == bf and accent_match(f, fw):
                        continue
                    # bag(r, bw) >= bag(q, bw) - bag(q, r): a candidate that cannot come within
                    # `near` of the rewrite is skipped without its OSA table (decisions 56)
                    if abs(len(bw) - len(r)) <= near and bag_of(bw) - rb <= near:
                        # a rewrite costs nothing only where it lands exactly; a candidate near
                        # it costs 1 + its distance from it (Robin, 2026-10-19)
                        d = osa(r, bw, near)
                        if d <= near:
                            keep(e, wlim + 1, d + 1 if d else 0)
                if shard_key(r) == own:          # a rewrite that is an inflected form
                    s = self.shard(own)
                    hit = sorted(s["ff"].get(r, ()))
                    if hit and r not in s["fh"]:
                        keep((r, fold(hit[0]), hit[0], 0), wlim + 1, 0)
        best = sorted(cands.values())
        return [{"word": c[7], "dist": c[1]} for c in best[:n]]


def dedupe_accent_groups(q: str, res: dict) -> dict:
    """An article is listed once (what lookup.js does, decisions 41 (a)): a group reached only
    through accent folding (its form folds to something other than ``q`` — *én* for *en*)
    keeps only the articles no exact group (and no accent group before it) lists, and is
    dropped if none is left. *kafe*
    lists *kafé / kafe* once, under "kafe", as ordbokene lists the article once."""
    seen = {a["id"] for key in ("heads", "forms") for g in res[key]
            if fold(g["form"]) == q for a in g["articles"]}
    for key in ("heads", "forms"):
        kept = []
        for g in res[key]:
            if fold(g["form"]) != q:
                g = {"form": g["form"], "articles": [a for a in g["articles"]
                                                     if a["id"] not in seen]}
                if not g["articles"]:
                    continue
                seen.update(a["id"] for a in g["articles"])
            kept.append(g)
        res[key] = kept
    return res


def char_counts(s: str) -> dict:
    out = {}
    for ch in s:
        out[ch] = out.get(ch, 0) + 1
    return out


def bag_distance(counts: dict, n: int, w: str) -> int:
    """The bag distance between a string (its ``char_counts`` and length ``n``) and ``w``: the
    larger of the letters only one has and the letters only the other has, as multisets. A
    lower bound of ``osa`` (an edit changes the bag by at most one letter each way, a
    transposition not at all) and a metric, so ``bag(r, w) >= bag(q, w) - bag(q, r)``: the
    similar pass uses it to skip the OSA table for a candidate that cannot qualify
    (decisions 56). It never changes an answer. lookup.js ``bagDistance``."""
    seen = {}
    extra = 0
    for ch in w:
        k = seen.get(ch, 0) + 1
        seen[ch] = k
        if k > counts.get(ch, 0):
            extra += 1
    return max(extra, n - (len(w) - extra))


def osa(a: str, b: str, cutoff: int = 3) -> int:
    """Optimal string alignment (Damerau–Levenshtein with no repeated edits), with a cutoff."""
    la, lb = len(a), len(b)
    if abs(la - lb) > cutoff:
        return cutoff + 1
    prev2 = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        row_min = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            v = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, prev2[j - 2] + 1)
            cur[j] = v
            row_min = min(row_min, v)
        if row_min > cutoff:
            return cutoff + 1
        prev2, prev = prev, cur
    return prev[lb]


def describe(idx: Index, q: str) -> str:
    """One line per query: what the search page says for it."""
    r = idx.lookup(q)
    parts = []
    for g in r["heads"]:
        arts = ", ".join(_label(a) for a in g["articles"])
        parts.append(f"headword {g['form']} -> {len(g['articles'])} article(s): {arts}")
    for g in r["forms"]:
        arts = ", ".join(_label(a) for a in g["articles"])
        parts.append(f"inflected form {g['form']} of: {arts}")
    sim = idx.similar(q)              # a hit's list is built as a miss's (decisions 56)
    if not parts:
        parts.append("MISS; similar: " + ", ".join(f"{s['word']}({s['dist']})" for s in sim))
    else:
        parts.append("similar: " + ", ".join(f"{s['word']}({s['dist']})" for s in sim))
    return " | ".join(parts)


def _label(a) -> str:
    hg = f" ({a['hg']})" if a["hg"] else ""     # the matched spelling's number (form_hg)
    pos = f" {a['pos'].lower()}" if a["pos"] else ""
    mark = "*" if a["translated"] else ""
    return f"{a['word']}{hg}{pos} #{a['id']}{mark}"


# --------------------------------------------------------------------------- #

def human(n: int) -> str:
    return f"{n:,}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mirror", help="bm-articles.jsonl (omit to verify an existing index)")
    ap.add_argument("--library", default=os.path.join(
                        os.path.abspath(os.environ.get("ORDBOK_DATA_DIR") or ROOT), "articles.jsonl"),
                    help="articles.jsonl (default: the one in ORDBOK_DATA_DIR when that is set, "
                         "else at the repository root)")
    ap.add_argument("--out", default=os.path.join(ROOT, "ordpar", "out"),
                    help="site output root (default: ordpar/out)")
    ap.add_argument("--limit", type=int, help="read only the first N mirror rows")
    ap.add_argument("--verify", action="store_true",
                    help="after building (or on its own), answer the standard test queries")
    ap.add_argument("--query", action="append", default=[],
                    help="an extra query for --verify (repeatable)")
    ap.add_argument("--freq", help="the National Library's N-grams 2026 books list as a 1-gram file "
                    "(nb-2026-books-nob-1990_freq.frk, ISO-8859-1) — ranks common similar words "
                    "and suggestions first (decisions 55); without it every band is 0")
    ap.add_argument("--freq-overrides", default=OVERRIDES_PATH,
                    help="the overrides registry, form / band / why (default: "
                         "ordpar/freq-overrides.tsv); read only with --freq")
    ap.add_argument("--form-overrides", default=FORM_OVERRIDES_PATH,
                    help="the exceptions to the inflected-form order, form / first / why "
                         "(default: ordpar/form-order-overrides.tsv; site decisions 143)")
    ap.add_argument("--freq-shared", choices=FREQ_SHARED, default="own",
                    help="a form several articles share: an article counts its OWN headwords "
                         "plus only its unshared forms (the default, Robin 2026-10-19), or the "
                         "form counts for EACH of them")
    ap.add_argument("--snippets", help="the article build's snippets (default: "
                    "ordpar/.build/build-snippets.json, written by build_site.py) — the list view's "
                    "one-line rows (site decisions 59)")
    ap.add_argument("--snippet-max", type=int, default=SNIPPET_MAX,
                    help=f"cut each snippet to this many characters (default {SNIPPET_MAX}; "
                         f"0 = uncut)")
    ap.add_argument("--time-similar", type=int, default=0,
                    help="time the similar-headwords pass over N random headwords")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    t0 = time.time()

    if args.mirror:
        stats = {}
        print(f"reading library  {args.library}")
        translated, library = library_pass(args.library)
        t_lib = time.time()
        print(f"  {human(len(library))} rows, {human(len(translated))} translated "
              f"(complete_strict) — {t_lib - t0:.1f}s")

        print(f"reading mirror   {args.mirror}")
        entries = list(read_mirror(args.mirror, args.limit))
        stats["mirror_rows_read"] = len(entries)
        all_headwords = {e[0]: list(e[1]) for e in entries if e[1]}      # decisions 117
        # decisions 93 (2): the articles whose spellings the normalization log reorders
        stats["lemma_order_applied"] = sorted(lemma_order.applied)
        stats["lemma_order_unmatched"] = sorted(lemma_order.unmatched)
        print(f"  lemma order (decisions 93): {len(lemma_order.applied)} article(s) in our order "
              f"{sorted(lemma_order.applied)}; {len(lemma_order.unmatched)} log line(s) unmatched")
        entries, translated, listing = search_scope(args.mirror, entries, library,
                                                    translated, stats)
        c = listing.counts()
        print(f"  decisions 46: {c['listed']} listed; unlisted {c['unlisted_served']} served + "
              f"{c['unlisted_404']} 404; kept {c['kept']} ({c['kept_served']} served, "
              f"{c['kept_404']} 404); left out of search {c['left_out_of_search']} "
              f"({stats['unlisted46_rows_left_out']} rows of the jsonl); "
              f"{stats['unlisted46_translated_left_out']} translated id(s) out of translated.json")
        form_tags = {}
        heads, forms, words = build_tables(entries, None, stats, form_tags)
        freq = rules = overrides = order_freq = None
        form_overrides = read_form_overrides(args.form_overrides)   # refuses a malformed line
        if args.freq:
            t_f = time.time()
            overrides = read_overrides(args.freq_overrides)   # refuses a malformed line first
            facts = read_facts(args.mirror)
            counts = read_freq(args.freq, set().union(
                *({fold(f) for f in list(e[1]) + list(e[4])} for e in entries)))
            freq = article_freq(entries, args.freq, stats, args.freq_shared, counts=counts,
                                facts=facts)
            # site decisions 143 (E2): the inflected-form order's figure, from the same counts
            # and each article's example sentences, read from the mirror (a third pass)
            examples = read_examples(args.mirror, listing, [e[0] for e in entries])
            order_freq = form_share(entries, counts, examples)
            stats["form_share_articles_with_examples"] = sum(
                1 for e in entries if examples.get(e[0]))
            rules = freq_rules(overrides, symbol_shared(entries, facts))
            stats["freq_overrides"] = len(overrides)
            print(f"  frequency ({args.freq_shared}): {human(stats['freq_forms_found'])} of "
                  f"{human(stats['freq_forms_wanted'])} folded forms in the list; "
                  f"{human(stats['freq_articles_seen'])} articles seen; fixes: "
                  f"{stats.get('freq_fix_accent_articles', 0)} accent twins, "
                  f"{stats.get('freq_fix_agent_forms', 0)} agent-noun forms for "
                  f"{stats.get('freq_fix_agent_verbs', 0)} verbs, "
                  f"{stats.get('freq_fix_symbol_articles', 0)} symbols; "
                  f"{len(overrides)} overrides — {time.time() - t_f:.1f}s")
        t_mirror = time.time()
        stats["headword_form_keys"] = sum(len(v) for v in heads.values())
        stats["inflected_form_keys"] = sum(len(v) for v in forms.values())
        # a form can be BOTH a headword (article A) and an inflected form (article B), so the
        # distinct-form count is the union of the two key sets, not their sum
        stats["distinct_forms"] = sum(len(set(heads.get(k, {})) | set(forms.get(k, {})))
                                      for k in set(heads) | set(forms))
        stats["forms_that_are_both"] = (stats["headword_form_keys"]
                                        + stats["inflected_form_keys"]
                                        - stats["distinct_forms"])
        stats["form_id_pairs"] = (sum(len(set(ids)) for v in heads.values() for ids in v.values())
                                  + sum(len(set(ids)) for v in forms.values() for ids in v.values()))
        stats["articles"] = len(words)
        stats["translated"] = len(translated)
        multi = sum(1 for v in heads.values() for ids in v.values() if len(set(ids)) > 1) + \
            sum(1 for v in forms.values() for ids in v.values() if len(set(ids)) > 1)
        stats["form_keys_with_several_articles"] = multi
        print(f"  {human(stats['rows'])} rows, {human(stats['distinct_forms'])} distinct forms, "
              f"{human(stats['form_id_pairs'])} form->id pairs — {t_mirror - t_lib:.1f}s")

        print(f"writing index    {os.path.join(out, 'index')}")
        manifest_note = freq_note(args.freq, args.freq_shared, args.freq_overrides,
                                  overrides, rules)
        snippets = read_snippets(args.snippets or SNIPPETS_PATH)
        if not snippets:
            print("  WARNING: no snippets (run build_site.py first): the list view's rows "
                  "will show none")
        # site decisions 148: the English miss line's share is of the dictionary the About page
        # counts (`site_stats` "articles" "all"), read before the index is written
        early = site_stats(out)
        dict_all = ((early or {}).get("articles") or {}).get("all")
        manifest = write_index(out, heads, forms, words, translated, stats, freq,
                               manifest_note, snippets, args.snippet_max, rules, library,
                               form_tags=form_tags, freq_path=args.freq,
                               order_freq=order_freq, order_overrides=form_overrides,
                               order_overrides_path=args.form_overrides,
                               dict_articles=dict_all)
        en = manifest["english"]
        print(f"  English search (decisions 148): {human(en['articles'])} articles, "
              f"{human(en['equivalents'])} equivalents, {human(en['keys'])} keys; "
              f"{len(en['files'])} files under en/, {human(en['raw'])} raw / {human(en['gzip'])} gzip-9, "
              f"the largest {en['largest']} {human(en['largest_gzip'])} gzip; "
              f"{en['explanations_not_indexed']} explanation units not indexed")
        unmatched = manifest["form_order"]["overrides"]["unmatched"]
        if unmatched and args.limit is None:
            sys.exit("form-order-overrides: %d exception(s) name no inflected form with two or "
                     "more articles, or an id not among them: %s" % (len(unmatched), unmatched))
        plan = manifest.pop("_plan")
        manifest.pop("_labels", None)
        stats_about = site_stats(out)
        if stats_about is None:
            sys.exit("no out/build.json with site_stats: run build_site.py first (the home "
                     "page's description takes its count from it, decisions 128)")
        written = copy_shell(out, stats_about)
        # site decisions 117: the word pages and form pages, the article pages' canonical, the
        # sitemap — after the article build, whose pages and sitemap list it reads
        t_wp = time.time()
        wp = write_word_pages(out, plan, snippets, args.snippet_max, all_headwords)
        wp.pop("_descriptions", None)
        manifest["pages"].update(wp)
        manifest["pages"]["unrepresentable_examples"] = plan["unrepresentable"]
        manifest["pages"]["variant_examples"] = [[a, l, f] for a, l, f in plan["variants"][:30]]
        write_bytes(os.path.join(out, "index", "index.json"), dump(manifest))
        c = plan["counts"]
        print(f"  word pages (decisions 117): {human(c.get('word_pages', 0))} "
              f"({human(c.get('word_pages_one', 0))} one article, "
              f"{human(c.get('word_pages_several', 0))} several) of "
              f"{human(c.get('searches_first_translated', 0))} searches whose first article is "
              f"translated; {c.get('unrepresentable', 0)} unrepresentable "
              f"{dict(sorted(stats.get('pages_117_unrepresentable', {}).items()))}")
        print(f"  form pages: {human(c.get('form_pages', 0))} (irregular forms of a translated "
              f"word {human(c.get('forms_irregular', 0))}, seen >= "
              f"{wordpages_mod.MIN_FORM_COUNT} times {human(c.get('forms_irregular_common', 0))}, "
              f"passive only {c.get('forms_passive_only', 0)})")
        print(f"  canonical: {human(c.get('articles_canonical_to_word_page', 0))} article pages "
              f"point to their word page; {c.get('variant_spelling_articles', 0)} articles reached "
              f"by several one-article word pages ({c.get('variant_spelling_pages_pointing_away', 0)} "
              f"pages point to another); {wp['articles_patched']} article pages patched")
        print(f"  sitemap.xml {human(wp['sitemap_urls'])} addresses ({human(wp['sitemap_bytes'])} B): "
              f"{wp['sitemap_word_pages']} word pages, {wp['sitemap_form_pages']} form pages, "
              f"{wp['sitemap_articles']} articles ({wp['sitemap_articles_dropped']} dropped for "
              f"their word page); {human(wp['pages_bytes'])} B of pages, "
              f"{wp['stale_pages_removed']} stale removed — {time.time() - t_wp:.1f}s")
        if manifest.get("labels"):
            lb = manifest["labels"]
            print(f"  labels.json {lb['count']} labels, {lb['raw']} B; shard codes {human(lb['codes'])} "
                  f"chars; unknown cell keys {lb['unknown_cell_keys']}")
        print(f"  inflected-form rows by frequency (decisions 143, E2): "
              f"{human(stats.get('form_order_changed_143', 0))} forms' articles in a new order; "
              f"{stats.get('form_overrides', 0)} exceptions "
              f"({stats.get('form_overrides_unmatched', 0)} unmatched)")
        t_end = time.time()

        raw = sum(s["raw"] for s in manifest["shards"])
        gz = sum(s["gzip"] for s in manifest["shards"])
        print(f"  {len(manifest['shards'])} shards: {human(raw)} raw / {human(gz)} gzip-9")
        print(f"  {len(manifest['tops'])} one-letter autocomplete files (<letter>-top.json): "
              f"{human(sum(t['raw'] for t in manifest['tops']))} raw / "
              f"{human(sum(t['gzip'] for t in manifest['tops']))} gzip")
        print(f"  headwords/ {len(manifest['headwords']['files'])} files, "
              f"{human(manifest['headwords']['raw'])} raw / "
              f"{human(manifest['headwords']['gzip'])} gzip  ({human(manifest['headwords']['count'])} forms; "
              f"largest {max(h['gzip'] for h in manifest['headwords']['files']):,} gzip)")
        print(f"  tails/ {len(manifest['tails']['files'])} files, "
              f"{human(manifest['tails']['raw'])} raw / {human(manifest['tails']['gzip'])} gzip "
              f"(largest {max(t['gzip'] for t in manifest['tails']['files']):,} gzip); "
              f"frequency {manifest_note['freq']} ({manifest_note['freq_shared']}), "
              f"{human(stats.get('headwords_with_band', 0))} headwords with a band")
        print(f"  alternation: {human(stats['expanded_headwords'])} headwords expanded to "
              f"{human(stats['expanded_variants'])} variants")
        print(f"  snip/ {len(manifest['snip']['files'])} files, {human(manifest['snip']['raw'])} "
              f"raw / {human(manifest['snip']['gzip'])} gzip ({human(manifest['snip']['count'])} "
              f"snippets, cut at {manifest['snip']['max']}; {stats['snippets_missing']} headword "
              f"articles without one; {stats['snippet_lang_mismatch']} language mismatches; "
              f"largest {max(f['gzip'] for f in manifest['snip']['files']):,} gzip)")
        print(f"  translated.json {human(manifest['translated']['raw'])} raw / "
              f"{human(manifest['translated']['gzip'])} gzip  ({human(manifest['translated']['count'])} ids)")
        print(f"  random.json {human(manifest['random']['raw'])} raw / "
              f"{human(manifest['random']['gzip'])} gzip  ({human(manifest['random']['count'])} headwords "
              f"whose search shows first one of {human(manifest['random']['articles'])} articles: "
              f"translated, not a set phrase, with a summary gloss)")
        if manifest.get("random_en"):
            re_ = manifest["random_en"]
            print(f"  random-en.json {human(re_['raw'])} raw / {human(re_['gzip'])} gzip  "
                  f"({human(re_['count'])} English words the suggestions offer, "
                  f"{re_['left_out']} keys they never can left out; site decisions 155)")
        for path, n in sorted(written.items()):
            print(f"  {'left alone' if n < 0 else 'wrote'} {path} ({human(abs(n))} B)")
        print(f"\nshard table (raw / gzip-9 / heads / inflected forms / articles)")
        for s in manifest["shards"]:
            print(f"  {s['k']:<5} {human(s['raw']):>10} {human(s['gzip']):>9} "
                  f"{human(s['heads']):>8} {human(s['forms']):>9} {human(s['articles']):>8}")
        print(f"\ntotal wall time {t_end - t0:.1f}s")

    if args.verify or args.query or args.time_similar:
        idx = Index(os.path.join(out, "index"))
        print("\nqueries:")
        for q in (args.query or []) + (TEST_QUERIES if args.verify else []):
            print(f"  {q!r}: {describe(idx, q)}")
        if args.verify:
            print("\nautocomplete 'hus' (first 8 of 20):")
            for s in idx.suggest("hus")[:8]:
                print(f"  {s['word']}  [{'translated' if s['translated'] else 'Norwegian only'}]")
        if args.time_similar:
            everything = idx.headwords   # loads every letter file
            pool = random.Random(7).sample(everything, args.time_similar)
            t = time.time()
            for q in pool:
                idx.similar(q)
            dt = (time.time() - t) / args.time_similar * 1000
            print(f"\nsimilar-headwords: {dt:.1f} ms per query (Python, {args.time_similar} queries, "
                  f"{human(len(everything))} headwords)")

    if not args.mirror and not (args.verify or args.query or args.time_similar):
        ap.error("nothing to do: pass --mirror to build, or --verify to query an existing index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
