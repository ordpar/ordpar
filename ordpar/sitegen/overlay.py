# -*- coding: utf-8 -*-
"""The handover's corrections to articles with no library row, applied by the site build to the
mirror article in memory (site decisions 182).

The file is `review/mirror-corrections.jsonl`; its row format and the four verdicts are the
format file, `docs/sessions/2026-09-19-ordpar-site-review/evidence/mirror-corrections-format-182-
2026-11-10.md`, and its contract `docs/schemas.md` § `review/mirror-corrections.jsonl`. The mirror
file is never written: `Mirror.data` hands out a corrected deep copy of each article a row
touches (`mirror.Mirror.set_overlay`), and `Mirror.raw_data` the article as ordbokene serves it,
for the change notice's checker (`corrections.Checker`), which must compare the page with the raw
mirror or no correction would ever look shown.

**Where a row applies.** `article` names the corrected text's own article; for a fixed expression
that is the expression's id, and the text also sits in every parent that embeds the expression
(`sub_article` -> `article`, a copy with the same `{article_id, lemmas, body}` shape). The row's
`path` is read from the mirror row's `data`; in a copy it is read from the copy's own root (the
`sub_article` node's `article`). Measured on the mirror of 2026-11-10: of 10,501 embedded copies
whose expression has its own row, 10,263 carry every `content` string at the same path as the
expression's own article; the other 238 are older versions of it (no `attest`, an element fewer),
so the value check below decides each location on its own — a copy is changed only where its value
at `path` is exactly `before`, never anywhere else. 161 copies embed an expression with no row of
its own (404'd): those copies are the only place the text lives.

**The verdict per row**, decided at build time against the raw mirror, each location on its own:

* `applied` — the raw value at `path` (for an object — a reference or usage item, a definition —
  the keys `before` names, a key the object lacks reading as null) equals `before`; `after` is
  written in the build's copy (a key `after` gives as null, or drops, is removed);
* `upstream` — it equals `after`: ordbokene has made the fix itself;
* `stale` — anything else, no such path, or no such article: ordbokene changed it;
* `library_row` — the article has a row in `articles.jsonl` (its correction is a capture edit);
* `malformed` — the row cannot be read: no integer `article`, a `path` that is not a list starting
  at `body` (a row may change body text and references only, never the headwords or the paradigms
  the mirror's index and the search index read raw), `before`/`after` missing or of different
  types, or a `kind` the change notice has no group for;
* `duplicate` — an earlier row already corrects the same field of the same article.

A row's verdict is its own article's, where the mirror carries it; for an expression the mirror
carries only as copies, `applied` if any copy took it, else `upstream` if any copy has the fix,
else `stale`. Copies are corrected wherever their value is `before`, whatever the own article's
verdict, so a row can be `upstream` in its own article and applied in a copy (*på alle bauger og
kanter* 115367): `summary`'s `copies` lists every such row with each parent's copies' verdicts. No verdict fails the build; `summary` is `build.json`'s `mirror_corrections`.
"""
import collections
import copy
import json
import os

from . import deck

# `review/` is fetch.py's: the repository root's, or ORDBOK_DATA_DIR's (decisions 184)
PATH = os.path.join(deck.fetch.REVIEW, "mirror-corrections.jsonl")

APPLIED, UPSTREAM, STALE, LIBRARY_ROW, MALFORMED, DUPLICATE = (
    "applied", "upstream", "stale", "library_row", "malformed", "duplicate")
VERDICTS = [APPLIED, UPSTREAM, STALE, LIBRARY_ROW, MALFORMED, DUPLICATE]

_MISSING = object()


def read(path=PATH):
    """Every row of the file, in order; a missing file is none. An unreadable line is kept as a
    `malformed` row (`{"_line": n, "_error": …}`), so it is listed rather than lost."""
    out = []
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError as e:
                row = {"_line": n, "_error": "not JSON: %s" % e}
            if not isinstance(row, dict):
                row = {"_line": n, "_error": "not a JSON object"}
            out.append(row)
    return out


def _get(root, path):
    node = root
    for k in path:
        if isinstance(node, dict) and isinstance(k, str) and k in node:
            node = node[k]
        elif (isinstance(node, list) and isinstance(k, int) and not isinstance(k, bool)
              and 0 <= k < len(node)):
            node = node[k]
        else:
            return _MISSING
    return node


def _value(node, shape):
    """The part of `node` a row's `before`/`after` speaks of: for a dict, the keys it names, a
    key the object lacks reading as null (the writer writes an absent key as `null`); otherwise
    the node itself."""
    if isinstance(shape, dict):
        if not isinstance(node, dict):
            return _MISSING
        return {k: node.get(k) for k in shape}
    return node


def _set(root, path, before, after):
    parent = _get(root, path[:-1])
    key = path[-1]
    if isinstance(after, dict):
        # any object at `path` (a reference or usage item, a definition): its named keys set; a
        # key `before` names that `after` drops, or that `after` gives as null, is removed (an
        # absent key reads as null)
        node = parent[key]
        for k in before if isinstance(before, dict) else ():
            if k not in after:
                node.pop(k, None)
        for k, v in after.items():
            if v is None:
                node.pop(k, None)
            else:
                node[k] = copy.deepcopy(v)
    else:
        parent[key] = copy.deepcopy(after)


def judge(root, row):
    """`APPLIED`, `UPSTREAM` or `STALE` for one location (`root`: an article's `data`, or a copy's
    `article`), against its raw value."""
    if root is None:
        return STALE
    node = _get(root, row["path"])
    if node is _MISSING:
        return STALE
    got = _value(node, row["before"])
    if got == row["before"]:
        return APPLIED
    if _value(node, row["after"]) == row["after"]:
        return UPSTREAM
    return STALE


def _malformed(row, kinds):
    if "_error" in row:
        return row["_error"]
    a = row.get("article")
    if not isinstance(a, int) or isinstance(a, bool):
        return "no integer article"
    p = row.get("path")
    if not isinstance(p, list) or not p or p[0] != "body":
        return "path is not a list starting at body"
    if any(not isinstance(k, (str, int)) or isinstance(k, bool) for k in p):
        return "path holds something other than keys and indices"
    if "before" not in row or "after" not in row:
        return "no before or after"
    b, f = row["before"], row["after"]
    if isinstance(b, dict) != isinstance(f, dict) or (isinstance(b, dict) and not b):
        return "before and after are not the same shape"
    if b == f:
        return "before equals after"
    if kinds is not None and row.get("kind") not in kinds:
        return "kind %r has no change-notice group" % row.get("kind")
    return None


def _copies(data, eid):
    """Every embedded copy of `eid` in an article's `data` (the `sub_article` nodes' `article`)."""
    out, stack = [], [(data or {}).get("body")]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            if n.get("type_") == "sub_article" and n.get("article_id") == eid:
                art = n.get("article")
                if isinstance(art, dict):
                    out.append(art)
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
    return out


class Overlay(object):
    """The file's rows and, once `resolve`d against a mirror, each row's verdict and the edits to
    make. Empty (falsy) when the file is absent or holds no row: the build is then as before."""

    def __init__(self, rows=(), path=None, library_ids=(), kinds=None):
        """`kinds`: the kinds a row may carry (`corrections.KIND_GROUP`; None: any)."""
        self.path = path
        self.rows = list(rows)
        self.library_ids = set(library_ids)
        self.kinds = kinds
        self.verdicts = [None] * len(self.rows)     # per row
        self.details = [None] * len(self.rows)      # why a row was not applied
        self.copies = [dict() for _ in self.rows]   # per row: parent id -> [verdict per copy]
        self.edits = {}            # article id -> [row index] whose edit lands in its data
        self._fixed = {}           # article id -> its corrected data (deep copy), memoized

    @classmethod
    def load(cls, path=PATH, library_ids=(), kinds=None):
        return cls(read(path), path=path, library_ids=library_ids, kinds=kinds)

    def __bool__(self):
        return bool(self.rows)

    __nonzero__ = __bool__

    # --- deciding --------------------------------------------------------------------

    def resolve(self, raw_data, parents_of):
        """Decide every row against the raw mirror. `raw_data(aid)`: an article's raw `data` or
        None; `parents_of(ids)`: `{id: [parent ids]}` of the articles embedding each id (one
        pass, `mirror.embedding_parents`). Idempotent."""
        self.edits, self._fixed = {}, {}
        good = []
        for i, row in enumerate(self.rows):
            self.copies[i] = {}
            why = _malformed(row, self.kinds)
            if why:
                self.verdicts[i], self.details[i] = MALFORMED, why
            elif row["article"] in self.library_ids:
                self.verdicts[i] = LIBRARY_ROW
                self.details[i] = "the article has a library row: a capture edit"
            else:
                good.append(i)
        parents = parents_of(sorted({self.rows[i]["article"] for i in good})) if good else {}
        claimed = set()            # (article id, embedded id or None, path) already corrected

        def claim(where, row, i):
            key = (where[0], where[1], json.dumps(row["path"]))
            if key in claimed:
                return False
            claimed.add(key)
            self.edits.setdefault(where[0], []).append(i)
            return True

        for i in good:
            row = self.rows[i]
            aid = row["article"]
            own = raw_data(aid)
            own_v = judge(own, row) if own is not None else None
            dup = False
            if own_v == APPLIED and not claim((aid, None), row, i):
                dup = True
            copy_vs = []
            for parent in (parents.get(aid) or []):
                vs = []
                for art in _copies(raw_data(parent), aid):
                    v = judge(art, row)
                    if v == APPLIED and not claim((parent, aid), row, i):
                        v = DUPLICATE
                    vs.append(v)
                if vs:
                    self.copies[i][parent] = vs
                    copy_vs.extend(vs)
            if dup:
                v, why = DUPLICATE, "an earlier row corrects the same field"
            elif own_v is not None:
                v = own_v
                why = None if v == APPLIED else (
                    "ordbokene's article carries the fix" if v == UPSTREAM else
                    "the value at path is not before" if _get(own, row["path"]) is not _MISSING
                    else "no such path")
            elif APPLIED in copy_vs:
                v, why = APPLIED, None
            elif UPSTREAM in copy_vs:
                v, why = UPSTREAM, "every embedded copy carries the fix or differs"
            else:
                v = STALE
                why = ("not in the mirror" if not copy_vs
                       else "no embedded copy holds before at path")
            self.verdicts[i], self.details[i] = v, why
        return self

    # --- applying --------------------------------------------------------------------

    def touches(self, aid):
        """True when the article's data carries an edit (its own text or an embedded copy)."""
        return aid in self.edits

    def apply(self, aid, data):
        """`data` corrected: a deep copy with every resolved edit for `aid` made, or `data`
        itself when there is none. The edit is made only where the value is still `before`, so a
        different `data` than the one resolved against is never mis-corrected."""
        if aid not in self.edits or data is None:
            return data
        if aid in self._fixed and self._fixed[aid][0] is data:
            return self._fixed[aid][1]
        out = copy.deepcopy(data)
        for i in self.edits[aid]:
            row = self.rows[i]
            roots = [out] if row["article"] == aid else _copies(out, row["article"])
            for root in roots:
                if judge(root, row) == APPLIED:
                    _set(root, row["path"], row["before"], row["after"])
        self._fixed[aid] = (data, out)
        return out

    # --- reporting -------------------------------------------------------------------

    def applied_rows(self):
        """The applied rows, in file order — each a correction of its `article` for the change
        notice and the About page's counts (`corrections.Checker`)."""
        return [r for r, v in zip(self.rows, self.verdicts) if v == APPLIED]

    def summary(self):
        """`build.json`'s `mirror_corrections`: the file, the counts by verdict, the embedded
        copies corrected, and every row not applied with its verdict and why."""
        counts = collections.Counter(v for v in self.verdicts if v)
        listed = []
        for i, (row, v) in enumerate(zip(self.rows, self.verdicts)):
            if v == APPLIED:
                continue
            entry = {"article": row.get("article"), "lemma": row.get("lemma"),
                     "kind": row.get("kind"), "handover": row.get("handover"),
                     "line": row.get("_line"), "verdict": v, "why": self.details[i]}
            if self.copies[i]:
                entry["copies"] = {str(p): vs for p, vs in sorted(self.copies[i].items())}
            listed.append(entry)
        return {
            "file": (os.path.abspath(self.path).replace("\\", "/") if self.path else None),
            "present": bool(self.path and os.path.exists(self.path)),
            "rows": len(self.rows),
            "counts": {v: counts[v] for v in VERDICTS},
            "copies_applied": sum(vs.count(APPLIED) for c in self.copies for vs in c.values()),
            # every row that reaches embedded copies: the row's own verdict and each parent's
            # copies' verdicts, as a row may be upstream in its own article and applied in a copy
            "copies": [{"article": r.get("article"), "lemma": r.get("lemma"), "verdict": v,
                        "copies": {str(p): vs for p, vs in sorted(c.items())}}
                       for r, v, c in zip(self.rows, self.verdicts, self.copies) if c],
            "articles_touched": len(self.edits),
            "not_applied": listed,
        }
