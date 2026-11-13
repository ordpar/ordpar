#!/usr/bin/env python3
"""Check 5: empty articles that other articles cite.

An article is "empty" here when none of its own definition nodes carries any definition
text or any example, and it embeds no fixed expression either: a reader who follows a
reference to it finds a headword (perhaps with inflection and etymology) and nothing
else. Such an article is reported only when at least one OTHER published article
refers to it (an ``article_ref`` in definition, example or etymology text, or in a
compound list), with the number of distinct citing articles and up to five of them.

An empty article that nothing cites is not reported. An article whose only content is
its fixed expressions is not reported: the reader lands on those expressions.

Citations are counted from each article's own text and, by default, from the
references in its embedded copies of fixed expressions that the expression's own
article lacks (or all of a copy whose expression has no article in the input),
credited to the parent article (--no-embedded turns this off). Whether an article is
empty is decided from its own body only.

It reads Nynorskordboka (--dictionary nn) exactly as it reads Bokmålsordboka, the
default: nothing in it depends on the language.

Python 3 standard library only, no network.
"""

import collections
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "citing_articles", "has_etymology",
          "citing_examples"]


def is_empty(art):
    for loc, kind, content, items in common.iter_text(art, etymology=False):
        if common.render(content, items).strip():
            return False
    for node in common.own_definition_nodes(art):
        for e in node.get("elements") or []:
            if e.get("type_") in ("sub_article", "compound_list"):
                return False
    return True


def scan(art, embedded=None):
    aid = common.article_id(art)
    cited = {it.get("article_id") for loc, it, ctx in itertools.chain(
        common.iter_refs(art), common.iter_embedded_refs(art, embedded))}
    cited.discard(aid)
    return is_empty(art), cited


def main(argv=None):
    ap = common.parser(__doc__.split("\n")[0], epilog=__doc__)
    common.add_embedded_option(ap)
    a = ap.parse_args(argv)
    embedded = common.embedded_for(a)
    reader = common.Reader(a.input, a.include_unpublished)
    run = common.Run("empty_cited_articles")
    empty = {}                                   # aid -> (lemma, has etymology)
    citers = collections.defaultdict(list)       # target -> [(citing aid, citing lemma)]
    for art in reader:
        res = run.guard(art, scan, art, embedded)
        if res is None:
            continue
        is_e, cited = res
        aid, lem = common.article_id(art), common.lemma_text(art)
        if is_e:
            empty[aid] = (lem, bool((art.get("body") or {}).get("etymology")))
        for t in cited:
            citers[t].append((aid, lem))
    tsv = common.TSV(a.output, HEADER)
    rows = [(aid, v) for aid, v in empty.items() if citers.get(aid)]
    rows.sort(key=lambda x: (-len(citers[x[0]]), x[0]))
    for aid, (lem, ety) in rows:
        cs = sorted(citers[aid])
        tsv.row([aid, lem, "hele artikkelen", "empty_article_cited", len(cs),
                 "ja" if ety else "nei",
                 "; ".join("%s %s" % (c, l) for c, l in cs[:5])])
    return run.finish(reader, tsv, extra=" (%d empty articles in all)%s" % (
        len(empty), embedded.note() if embedded else ""))


if __name__ == "__main__":
    sys.exit(main())
