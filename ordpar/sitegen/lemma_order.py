# -*- coding: utf-8 -*-
"""Our lemma order in the article's headword line (site decisions 93 (2), Robin 2026-10-23).

The deck's library rows carry a few **lemma-order normalizations**: where Bokmålsordboka lists
the less common spelling first, Robin ruled the more common one first on usage counts — *tørre,
tore* (61543), *aksjemegler, aksjemekler* (554), *eiendomsmegler, eiendomsmekler* (11828),
*gæren, galen* (18893). Each ruling is one line of the deck's normalization log,
`review/source-normalizations.jsonl`: `kind: "lemma-order"`, `where` "top-level lemmas order
(the article header)", `before` and `after` the header's forms joined by ", ". The site reads
the MIRROR, which keeps ordbokene's order; this module puts the mirror's `lemmas` into the
logged order, so that every place the site shows an article's spellings — the headword line
(`article.lemma_groups`), the page `<title>`, the inflection table's order, the search index's
display text (`build_index.entry`) and through it the results, the list view, favourites,
history and the suggestions — shows ours.

**Why the log, not the library row's order.** The log is the ruling's own record: a new
ruling is a new line there, so it reaches the site with no code change; it names exactly which
order is ours (the library row's order could differ from the mirror's for other reasons —
a stale capture). The library row stays the deck's; the two agree today on all four.

**The rule.** A log line counts when its `kind` is `lemma-order` and its `where` starts with
"top-level lemmas" (a fifth `lemma-order` line, 37693, is about a compound list's faces and
is not the header's). The last such line for an article wins. It is applied only where some
order of the mirror row's distinct spellings, joined by ", ", reads exactly `after` — each
spelling keeps its own lemma (its homograph number, its paradigms); lemmas of one spelling keep
their relative order. A line whose `after` no order of the mirror's spellings matches (a
refresh changed the article) is not applied and is reported (`unmatched`), never guessed at.
"""
import itertools
import json
import os
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# `review/` under the repository root, or under `ORDBOK_DATA_DIR` when set: the one data override
# `scripts/fetch.py` reads (decisions 184; read here directly, so this module stays import-light)
LOG = os.path.join(os.path.abspath(os.environ.get("ORDBOK_DATA_DIR") or ROOT), "review",
                   "source-normalizations.jsonl")
WHERE = "top-level lemmas"
MAX_FORMS = 6          # permutations tried at most 720; no header has more than 4 spellings

_orders = None         # {article id: "after"}, read once per process
applied = set()        # ids reordered in this process (the build's report)
unmatched = set()      # ids whose log line matched no order of the mirror's spellings


def _nfc(s):
    return unicodedata.normalize("NFC", (s or "").strip())


def read_log(path=LOG):
    """``{article id: after}`` from the log's header lemma-order lines, the last one winning.
    A missing log is no rulings."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") != "lemma-order":
                continue
            if not str(e.get("where") or "").startswith(WHERE):
                continue
            if isinstance(e.get("article"), int) and isinstance(e.get("after"), str):
                out[e["article"]] = _nfc(e["after"])
    return out


def orders():
    global _orders
    if _orders is None:
        _orders = read_log()
    return _orders


def set_orders(mapping):
    """Replace the rulings (the tests; ``None`` reads the log again on next use)."""
    global _orders
    _orders = mapping


def reorder(aid, data, after=None):
    """``data`` with its ``lemmas`` in our order, or ``data`` itself where no ruling applies.
    Never changes ``data`` in place (the mirror reader caches its rows)."""
    if not data:
        return data
    if after is None:
        after = orders().get(aid)
    if after is None:
        return data
    lemmas = data.get("lemmas") or []
    forms = []
    for lem in lemmas:
        f = _nfc(lem.get("lemma"))
        if f and f not in forms:
            forms.append(f)
    if not forms or len(forms) > MAX_FORMS:
        unmatched.add(aid)
        return data
    want = None
    for perm in itertools.permutations(forms):
        if ", ".join(perm) == after:
            want = list(perm)
            break
    if want is None:
        unmatched.add(aid)
        return data
    applied.add(aid)
    if want == forms:
        return data
    rank = {f: i for i, f in enumerate(want)}
    keyed = sorted(enumerate(lemmas),
                   key=lambda p: (rank.get(_nfc(p[1].get("lemma")), len(want)), p[0]))
    out = dict(data)
    out["lemmas"] = [lem for _i, lem in keyed]
    return out
