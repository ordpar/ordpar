#!/usr/bin/env python3
"""Check 1: references that point at a sense the target article does not have.

A reference to another article (``type_: "article_ref"``) may carry a ``definition_id``
naming one sense of the target. This check reports every reference whose
``definition_id`` matches no definition node of the target article. Example: four
articles cite bryst I (7850) with definition_id 5; 7850 has no definition with id 5.

Finding types (column ``type``):
  missing_definition_id   the target article exists, but none of its own definition
                          nodes has this id (the main finding);
  anchor_without_text     a node with the id exists, but it carries no explanation and
                          no example of its own (it only holds sub-senses or fixed
                          expressions), so there is no sense to land on;
  target_not_published    the target article is in the input but not published;
  target_missing          the target article is not in the input at all (meaningful only
                          when the input is the whole dictionary).

Definition nodes inside an embedded fixed expression (sub_article) belong to that
expression's own article and are not counted as the host's. The references in an
embedded copy are read when the expression's own article lacks the element they stand
in, or when the expression has no article in the input (--no-embedded turns this off);
such a finding carries the parent's article_id and lemma, and its location begins
'artikkel <parent>, uttrykk "<expression>" (<expression id>)'.

It reads Nynorskordboka (--dictionary nn) exactly as it reads Bokmålsordboka, the
default: nothing in it depends on the language.

Python 3 standard library only, no network.
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "target_article_id", "target_lemma",
          "definition_id", "reference_text", "context"]


def index_article(art, embedded=None):
    """(own definition ids, ids whose node has no text of its own, refs). With an
    Embedded, the refs include those of the embedded copies' differing elements."""
    ids, textless = set(), set()
    for node in common.own_definition_nodes(art):
        if node.get("id") is None:
            continue
        ids.add(node["id"])
        if not common.has_own_text(node):
            textless.add(node["id"])
    # a node id that occurs twice, once with text and once without, has text
    textless -= {n.get("id") for n in common.own_definition_nodes(art) if common.has_own_text(n)}
    refs = []
    for loc, it, ctx in itertools.chain(common.iter_refs(art),
                                        common.iter_embedded_refs(art, embedded)):
        did = it.get("definition_id")
        if did is None:
            continue
        refs.append((loc, it.get("article_id"), did, common.ref_face(it), ctx))
    return ids, textless, refs


def main(argv=None):
    ap = common.parser(__doc__.split("\n")[0], epilog=__doc__)
    common.add_embedded_option(ap)
    a = ap.parse_args(argv)
    embedded = common.embedded_for(a)
    reader = common.Reader(a.input, a.include_unpublished)
    run = common.Run("dangling_sense_refs")
    targets = {}          # aid -> (ids, textless, lemma)
    citing = []           # (aid, lemma, refs)
    for art in reader:
        res = run.guard(art, index_article, art, embedded)
        if res is None:
            continue
        ids, textless, refs = res
        aid, lem = common.article_id(art), common.lemma_text(art)
        targets[aid] = (ids, textless, lem)
        if refs:
            citing.append((aid, lem, refs))
    unpublished = set(reader.skipped_ids)
    tsv = common.TSV(a.output, HEADER)
    for aid, lem, refs in citing:
        for loc, tid, did, face, ctx in refs:
            t = targets.get(tid)
            if t is None:
                kind = "target_not_published" if tid in unpublished else "target_missing"
                tsv.row([aid, lem, loc, kind, tid, "", did, face, ctx])
                continue
            ids, textless, tlem = t
            if did not in ids:
                tsv.row([aid, lem, loc, "missing_definition_id", tid, tlem, did, face, ctx])
            elif did in textless:
                tsv.row([aid, lem, loc, "anchor_without_text", tid, tlem, did, face, ctx])
    return run.finish(reader, tsv, extra=embedded.note() if embedded else "")


if __name__ == "__main__":
    sys.exit(main())
