#!/usr/bin/env python3
"""Check 6: reference-only senses that lead the reader back to the article they started in.

A sense is "reference-only" when its explanations contain nothing but references
(``article_ref``), abbreviation concepts (such as "jf"), punctuation and the linking
words "se", "og", "eller", "også" (with --dictionary nn, Nynorskordboka's "sjå", "og",
"eller", "òg", "også"). (Examples beside the explanation do not change this.)

Three finding types, one line per loop (never one per member):

  mutual               two reference-only senses in different articles, A and B, where
                       every reference in A leads to B and every reference in B leads to
                       A. Here a reference "leads to" a sense when it names it by
                       ``definition_id``, or names its article without one. Example:
                       allerede (868) is defined only as "alt", a reference to alt (1372),
                       and sense 3 of alt only as "allerede".
  returns-other-sense  a chain of reference-only senses through ONE other article that
                       comes back to the starting article on a different sense. Example:
                       blunke (6606) sense 2 is only "blinke" (6446, sense 2), which is
                       only "blunke" sense 1.
  longer-loop          the same through TWO OR MORE other articles, whether it comes back
                       on the starting sense (A -> B -> C -> A) or on another one.

How a chain is followed (returns-other-sense and longer-loop). Every sense on the chain
before the return is reference-only, and all of its references go to one article: a
sense that also refers elsewhere gives the reader somewhere else to go, and the chain
stops there. A reference to a definition goes to that sense; if that sense has text of
its own, the chain stops and there is no finding. A reference to a whole article
continues only when every sense of that article is reference-only; otherwise the reader
landing there finds a definition, and the chain stops. The chain is closed as soon as a
reference names the starting article, either a sense of it or the article as a whole;
the sense it comes back to may have text of its own (in the blunke case it does). No
other article is visited twice.

``--max-articles`` bounds the number of other articles on a chain (default 10). Over the
whole dictionary on 2026-10-03, no chain under these rules got beyond one other article,
and raising the bound to 50 changed nothing.

Each type is split by examples, the second column after type:
  bare          no reference-only sense on the loop has an example of its own;
  own-examples  at least one does (as blunke sense 2 does: "blunke med lyset"), so the
                reader finds some lexicographic information there, though no definition.
The sense the loop returns to is not counted: it is not reference-only by necessity.

Columns: the starting sense (article_id, lemma, location); type; examples (bare or
own-examples); other_articles (how many other articles the loop passes through); loop:
every step as "headword [article id] betydning N (definisjon id D) <ordbokene.no link>"
(the link to Nynorskordboka's page with --dictionary nn),
joined by " -> ", ending on the sense or article the reader is sent back to; texts: the
explanation of each reference-only step, in order, joined by " | "; senses_with_examples:
each reference-only sense on the loop that has examples of its own, with how many.

Output order: by type, then bare before own-examples, then by the starting sense.

A mutual pair is started from the lower article id, a longer loop that returns to its own
starting sense from its lowest (article id, definition id). Two senses of the same article
are never paired.

Python 3 standard library only, no network.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "examples", "other_articles", "loop",
          "texts", "senses_with_examples"]
GROUPS = ["bare", "own-examples"]
TYPES = ["mutual", "returns-other-sense", "longer-loop"]

#: the words allowed beside the references, by dictionary ("se" is "sjå" in Nynorskordboka,
#: which writes it before 9,129 references, 2026-11-13; Nynorsk has "òg" beside "også")
LINK_WORDS = {"se", "og", "eller", "også"}
LINK_WORDS_BY_DICT = {"bm": LINK_WORDS, "nn": {"sjå", "og", "eller", "òg", "også"}}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def senses(art, link_words=LINK_WORDS):
    """[(node, place, refs, text)] for every sense-bearing node (one with an
    explanation). refs is None unless the sense is reference-only."""
    labels = common.sense_labels(art)
    out = []
    for node in common.own_definition_nodes(art):
        expl = [e for e in node.get("elements") or [] if e.get("type_") == "explanation"]
        if not expl:
            continue
        refs, rest, shown = [], [], []
        for e in expl:
            items = [i for i in e.get("items") or [] if isinstance(i, dict)]
            for it in common._flat_items(items):
                if it.get("type_") == "article_ref":
                    refs.append((it.get("article_id"), it.get("definition_id")))
                elif it.get("type_") in ("usage", "quote_inset"):
                    rest.append(it.get("text") or it.get("content") or "")
            rest.append((e.get("content") or "").replace("$", " "))
            shown.append(common.render(e.get("content"), items))
        words = {w.lower() for w in WORD.findall(" ".join(rest))}
        pure = bool(refs) and words <= link_words
        out.append((node, common.node_place(node, labels), refs if pure else None,
                    " / ".join(shown)))
    return out


def headword(art):
    """The headword as ordbokene shows it: 'blinke II' for homograph 2."""
    lems = art.get("lemmas") or []
    hg = lems[0].get("hgno") if lems else 0
    word = common.lemma_text(art)
    if isinstance(hg, int) and 0 < hg < len(ROMAN):
        word = "%s %s" % (word, ROMAN[hg])
    return word


def read_article(art, link_words=LINK_WORDS):
    """What the check keeps of one article: its reference-only senses by definition id
    (place, references, text, number of examples of its own), whether every sense with text of its own is one of them,
    and the place of every definition node (for the sense a loop returns to)."""
    labels = common.sense_labels(art)
    res = senses(art, link_words)
    pure = {}
    for node, place, refs, text in res:
        if refs:
            n_ex = sum(1 for e in node.get("elements") or []
                       if e.get("type_") == "example")
            pure.setdefault(node.get("id"), (place, refs, text, n_ex))
    # every text-bearing node (an explanation or an example) is reference-only
    bearing = [n for n in common.own_definition_nodes(art) if common.has_own_text(n)]
    pure_ids = {node.get("id") for node, place, refs, text in res if refs}
    all_pure = bool(bearing) and all(n.get("id") in pure_ids for n in bearing)
    places = {}
    if pure:
        for node in common.own_definition_nodes(art):
            places.setdefault(node.get("id"), common.node_place(node, labels))
    return {"lemma": common.lemma_text(art), "head": headword(art), "pure": pure,
            "all_pure": all_pure, "places": places}


def leads_to(refs, aid, did):
    """Every reference in ``refs`` goes to article ``aid``: to its definition ``did``,
    or to the article as a whole."""
    return all(t == aid and (d is None or d == did) for t, d in refs)


def step_target(refs):
    """(article, definition id or None) when every reference names one article and at
    most one definition of it; None when the sense sends the reader to two places."""
    arts = {t for t, d in refs}
    if len(arts) != 1:
        return None
    dids = {d for t, d in refs if d is not None}
    if len(dids) > 1:
        return None
    return arts.pop(), (dids.pop() if dids else None)


def find_mutual(lib):
    """Today's two-sense cycles, unchanged: [(aid, did, other aid, other did)]."""
    out = []
    for aid in sorted(lib):
        for did, (place, refs, text, n_ex) in lib[aid]["pure"].items():
            targets = {t for t, d in refs}
            if len(targets) != 1:
                continue
            other = targets.pop()
            if other == aid or other < aid or other not in lib:
                continue
            for odid, (oplace, orefs, otext, on_ex) in lib[other]["pure"].items():
                if leads_to(refs, other, odid) and leads_to(orefs, aid, did):
                    out.append((aid, did, other, odid))
    return out


def id_order(did):
    """Sort key for definition ids: numbers first, in order, then anything else."""
    return (0, did, "") if isinstance(did, int) else (1, 0, str(did))


def find_chains(lib, max_articles=10):
    """Every closed chain from every reference-only sense:
    [(path, landing)] where path is [(aid, did), ...] starting at the start sense and
    landing is (start aid, did or None)."""
    out = []
    for sa in sorted(lib):
        for sd in sorted(lib[sa]["pure"], key=id_order):
            stack = [((sa, sd), [(sa, sd)], {sa})]
            while stack:
                (a, d), path, seen = stack.pop()
                tgt = step_target(lib[a]["pure"][d][1])
                if tgt is None:
                    continue
                t, td = tgt
                if t == sa:
                    if len(seen) > 1:
                        out.append((path, (t, td)))
                    continue
                if t in seen or t not in lib or len(seen) > max_articles:
                    continue
                if td is not None:
                    nxt = [td] if td in lib[t]["pure"] else []
                else:
                    nxt = sorted(lib[t]["pure"], key=id_order) if lib[t]["all_pure"] else []
                for n in nxt:
                    stack.append(((t, n), path + [(t, n)], seen | {t}))
    return out


def examples_on(lib, path):
    """[(aid, did, n)] for every reference-only sense on the loop that has n > 0
    examples of its own."""
    return [(a, d, lib[a]["pure"][d][3]) for a, d in path if lib[a]["pure"][d][3]]


def classify(mutual, chains, lib=None):
    """[(type, path, landing)], each loop once, grouped by type and then, when ``lib``
    is given, by examples (bare loops first).

    A loop is known by the set of senses on it: the path, plus the sense it returns to
    when that is not the starting sense and not the whole starting article. So a cycle
    (one that comes back where it began, or to the whole of an article it began in) is
    the same loop from every member, and is kept from the lowest starting sense; a chain
    of one other article that comes back on its own sense or the whole article is
    always a mutual pair, already reported."""
    found, keys = [], set()
    for aid, did, other, odid in mutual:
        keys.add(frozenset([(aid, did), (other, odid)]))
        found.append(("mutual", [(aid, did), (other, odid)], (aid, did)))
    for path, landing in chains:
        nodes = set(path)
        if landing[1] is not None:
            nodes.add(landing)
        key = frozenset(nodes)
        if key in keys:
            continue
        keys.add(key)
        others = len({a for a, d in path[1:]})
        found.append(("returns-other-sense" if others == 1 else "longer-loop", path,
                      landing))
    order = {t: i for i, t in enumerate(TYPES)}
    found.sort(key=lambda f: (order[f[0]], bool(lib and examples_on(lib, f[1])),
                              f[1][0]))
    return found


def render_step(lib, aid, did, dictionary="bm"):
    info = lib[aid]
    if did is None:
        place = "hele artikkelen"
    else:
        place = info["places"].get(did) or "definisjon id %s" % did
    return "%s [%s] %s %s" % (info["head"], aid, place, common.link(aid, dictionary))


def main(argv=None):
    ap = common.parser(__doc__.splitlines()[0], epilog=__doc__)
    ap.add_argument("--max-articles", type=int, default=10,
                    help="the most other articles a chain may pass through (default 10)")
    a = ap.parse_args(argv)
    reader = common.Reader(a.input, a.include_unpublished)
    run = common.Run("sense_ref_cycles")
    lib = {}
    for art in reader:
        res = run.guard(art, read_article, art, LINK_WORDS_BY_DICT[a.dictionary])
        if res is None:
            continue
        if res["pure"]:
            lib[common.article_id(art)] = res
    found = classify(find_mutual(lib), find_chains(lib, a.max_articles), lib)
    tsv = common.TSV(a.output, HEADER)
    counts = {(t, g): 0 for t in TYPES for g in GROUPS}
    for typ, path, landing in found:
        sa, sd = path[0]
        ex = examples_on(lib, path)
        group = GROUPS[bool(ex)]
        counts[typ, group] += 1
        steps = [render_step(lib, x, y, a.dictionary) for x, y in path + [landing]]
        tsv.row([sa, lib[sa]["lemma"], lib[sa]["places"].get(sd), typ, group,
                 len({x for x, y in path[1:]}), " -> ".join(steps),
                 " | ".join(lib[x]["pure"][y][2] for x, y in path),
                 "; ".join("%s [%s] %s: %d %s" % (
                     lib[x]["head"], x, lib[x]["places"][y], n,
                     "eksempel" if n == 1 else "eksempler") for x, y, n in ex)])
    return run.finish(reader, tsv, " (%s)" % ", ".join(
        "%s %d bare + %d own-examples" % (t, counts[t, "bare"], counts[t, "own-examples"])
        for t in TYPES))


if __name__ == "__main__":
    sys.exit(main())
