#!/usr/bin/env python3
"""Check 2: two definition nodes in one article that share an id.

A reference addresses a sense by its ``definition_id``, so the id must be unique within
the article. This check reports every id that two or more of an article's own
definition nodes carry; one line per node, so each copy can be located. Example:
gå (21740) has two definition nodes with id 5.

Definition nodes inside an embedded fixed expression (sub_article) belong to that
expression's own article and are not counted.

It reads Nynorskordboka (--dictionary nn) exactly as it reads Bokmålsordboka, the
default: nothing in it depends on the language.

Python 3 standard library only, no network.
"""

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "definition_id", "occurrences",
          "first_text"]


def first_text(node):
    for e in node.get("elements") or []:
        if e.get("type_") == "explanation":
            return common.render(e.get("content"), e.get("items"))
        if e.get("type_") == "example":
            q = e.get("quote") or {}
            return "(eksempel) " + common.render(q.get("content"), q.get("items"))
    kids = common.def_children(node)
    if kids:
        return "(inneholder %d underdefinisjoner)" % len(kids)
    if any(e.get("type_") == "sub_article" for e in node.get("elements") or []):
        return "(inneholder faste uttrykk)"
    return "(tom)"


def check(art):
    nodes = [n for n in common.own_definition_nodes(art) if n.get("id") is not None]
    count = collections.Counter(n["id"] for n in nodes)
    labels = common.sense_labels(art)
    out = []
    for n in nodes:
        if count[n["id"]] > 1:
            out.append((common.node_place(n, labels), n["id"], count[n["id"]], first_text(n)))
    return out


def main(argv=None):
    ap = common.parser(__doc__.split("\n")[0], epilog=__doc__)
    a = ap.parse_args(argv)
    reader = common.Reader(a.input, a.include_unpublished)
    run = common.Run("duplicate_definition_ids")
    tsv = common.TSV(a.output, HEADER)
    for art in reader:
        for loc, did, n, text in run.guard(art, check, art) or []:
            tsv.row([common.article_id(art), common.lemma_text(art), loc,
                     "duplicate_definition_id", did, n, text])
    return run.finish(reader, tsv)


if __name__ == "__main__":
    sys.exit(main())
