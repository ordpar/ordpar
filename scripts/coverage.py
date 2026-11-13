#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""How much of Bokmålsordboka we have authored — the line-count coverage figure.

    python scripts/coverage.py                # the report
    python scripts/coverage.py --obligation   # + guardrail 2's own bar for minis
    python scripts/coverage.py --include-expr # count fixed-expression articles too
    python scripts/coverage.py --validate     # check the counter against our own rows
    python scripts/coverage.py --json         # machine-readable

Two questions, one tool.

**Coverage** (report § 1) — of every authorable-English slot the dictionary holds, how many
carry authored English? The denominator is the FULL local mirror (``.mirror/bm-articles.jsonl``,
built by ``mirror.py fetch`` + ``extract``); the numerator is ``articles.jsonl``. A *slot* is
one place a row carries an ``en``, one per parallel Norwegian line — ``ety`` (etymology
segment), ``sense_seg`` / ``sub_seg`` (explanation segment), ``ex`` (one English string per
example, quote and explanation together), ``comp`` (one compound item's hover gloss).
``idiom``, ``ex_added`` and ``summary`` are excluded from both sides on purpose: no Norwegian
line in the source stands behind them, so they cannot be coverage OF the source. They are
reported separately.

**Completeness** (report § 2) — how many articles are *finished*: every sense and every
example authored. Split by how the article is reached: **seed** (composed onto a live card)
versus **mini-only** (in the library only because a live card's derived Norwegian cites it —
the R half of the closure). This bar is stricter than what guardrail 2 obliges for a mini: a
``#defN`` citation obliges only the anchored sense, and a bare href only every sense plus the
first example per unit, so an unfinished mini is normally not debt. ``--obligation`` reports
the guardrail's own bar beside it.

**Fixed expressions are excluded by default** (Robin, 2026-09-04): an expression article is
not a lemma article, and counting the ~8.9k of them alongside ~82k lemma articles distorts
every ratio. ``--include-expr`` puts them back. Excluding them also takes the see-line
question out of the denominator: the deferral (``derive.derive_row``, Robin 2026-07-14) that
keeps an expression's ``Se: …`` component line out of its row applies to EXPR articles alone.

Why not run the deriver over the mirror: ``derive_row``'s ``link_marker`` resolves every link
target through ``fetch``, so 94k articles would mean tens of thousands of requests outside the
pinned evidence universe. The counter below is instead a **structural** restatement of the
deriver's unit rules — the same ``_def_children`` / ``_is_gloss`` / ``_collect_senses`` /
``_collect_subs`` walk, counting element types rather than filling them. ``--validate``
measures that restatement against the library's own rows: it agreed to 18 units out of
105,158 on 2026-09-04, the whole remaining gap being the EXPR see-lines.
"""

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(ROOT, ".mirror", "bm-articles.jsonl")
ARTICLES = os.path.join(ROOT, "articles.jsonl")
CARDS = os.path.join(ROOT, "cards.jsonl")
PUBLISHED = "8"          # ordbokene's own `status` for a published article

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

KEYS = ("ety", "sense_seg", "sub_seg", "ex", "comp")
LABEL = {"ety": "etymology segments", "sense_seg": "sense segments",
         "sub_seg": "subsense segments", "ex": "examples", "comp": "compound glosses"}


# --- the structural counter (mirrors derive.py, without the filling) --------

def _def_children(node):
    return [e for e in node.get("elements", []) if e.get("type_") == "definition"]


def _is_gloss(node):
    if any(e.get("type_") == "explanation" for e in node.get("elements", [])):
        return True
    return (not _def_children(node)
            and any(e.get("type_") == "example" for e in node.get("elements", [])))


def collect_senses(article):
    senses = []

    def walk(node):
        for child in _def_children(node):
            senses.append(child) if _is_gloss(child) else walk(child)
    for d in (article.get("body", {}) or {}).get("definitions") or []:
        senses.append(d) if _is_gloss(d) else walk(d)
    return senses


def collect_subs(sense_node):
    subs = []

    def rec(node):
        for child in _def_children(node):
            if _is_gloss(child):
                subs.append(child)
            rec(child)
    rec(sense_node)
    return subs


def _n(node, type_):
    return sum(1 for e in node.get("elements", []) if e.get("type_") == type_)


def _own_compound_lists(node):
    out = []

    def walk(n, root):
        if isinstance(n, dict):
            if n.get("type_") == "definition" and not root:
                return                       # a nested subsense owns its own lists
            if n.get("type_") == "compound_list":
                out.append(n)
            for v in n.values():
                walk(v, False)
        elif isinstance(n, list):
            for v in n:
                walk(v, root)
    walk(node, True)
    return out


def _n_comp(node):
    return sum(sum(1 for el in cl.get("elements", []) if el.get("type_") == "article_ref")
               for cl in _own_compound_lists(node))


def count_units(article):
    """The authorable-English slots one raw article JSON yields."""
    c = dict.fromkeys(KEYS, 0)
    c["ety"] = len((article.get("body", {}) or {}).get("etymology") or [])
    for s in collect_senses(article):
        c["sense_seg"] += _n(s, "explanation")
        c["ex"] += _n(s, "example")
        c["comp"] += _n_comp(s)
        for sub in collect_subs(s):
            c["sub_seg"] += _n(sub, "explanation")
            c["ex"] += _n(sub, "example")
            c["comp"] += _n_comp(sub)
    return c


def is_expr_source(article):
    for lem in article.get("lemmas") or []:
        for pi in lem.get("paradigm_info") or []:
            if "EXPR" in (pi.get("tags") or []):
                return True
    return False


def _is_see_also(content):
    c = (content or "").lstrip()
    return c.startswith("Se:") or c.startswith("Sjå:")


def _see_lines(article):
    """An EXPR article's see-also component lines — deferred, so never in a row."""
    n = 0
    for s in collect_senses(article):
        for u in [s] + collect_subs(s):
            n += sum(1 for e in u.get("elements", [])
                     if e.get("type_") == "explanation" and _is_see_also(e.get("content")))
    return n


# --- the two sides ----------------------------------------------------------

def read_mirror(include_expr):
    if not os.path.exists(MIRROR):
        sys.exit("no %s — run: python scripts/mirror.py fetch && python scripts/mirror.py extract"
                 % os.path.relpath(MIRROR, ROOT))
    agg = dict.fromkeys(KEYS, 0)
    arts = drafts = expr_arts = see = 0
    with io.open(MIRROR, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line).get("data") or {}
            if str(d.get("status")) != PUBLISHED:
                drafts += 1
                continue
            if is_expr_source(d):
                expr_arts += 1
                see += _see_lines(d)
                if not include_expr:
                    continue
            arts += 1
            c = count_units(d)
            for k in KEYS:
                agg[k] += c[k]
    if include_expr:
        agg["sense_seg"] -= see          # the deferral our rows mirror
    return {"articles": arts, "drafts": drafts, "expr_articles": expr_arts,
            "see_lines": see, "units": agg}


def read_library(include_expr):
    rows = {}
    with io.open(ARTICLES, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rows[r["id"]] = r
    keep = {i: r for i, r in rows.items()
            if include_expr or r.get("pos_en") != "fixed expression"}
    tot, auth = dict.fromkeys(KEYS, 0), dict.fromkeys(KEYS, 0)
    extra = {"idiom": 0, "ex_added": 0, "ex_added_en": 0, "summary": 0}
    for r in keep.values():
        ety = r.get("etymology") or {}
        tot["ety"] += len(ety.get("no") or [])
        if ety.get("en") is not None:
            auth["ety"] += len(ety.get("no") or [])
        if r.get("summary"):
            extra["summary"] += 1
        for s in r["senses"]:
            for u, key in [(s, "sense_seg")] + [(x, "sub_seg") for x in s.get("subs", [])]:
                no = u.get("no") or []
                tot[key] += len(no)
                if u.get("en") is not None:
                    auth[key] += len(no)
                if u.get("idiom"):
                    extra["idiom"] += 1
                for e in u.get("ex") or []:
                    tot["ex"] += 1
                    auth["ex"] += e[1] is not None
                for b in u.get("comp") or []:
                    for it in b.get("items", []):
                        tot["comp"] += 1
                        auth["comp"] += it.get("en") is not None
                for o in u.get("ex_added") or []:
                    extra["ex_added"] += 1
                    extra["ex_added_en"] += o.get("en") is not None
    return rows, keep, tot, auth, extra


# --- completeness by how the article is reached -----------------------------

def partition(rows, keep):
    """(live cards, seed, mini, inlined) over the kept ids.

    **seed** = rendered in full on a live card: composed onto one, or inlined into one as a
    sub-article. Inlining is almost always a fixed expression (dropped by default), but not
    always — ordbokene attach two multiword *lemma* articles that way (`spansk pepper`,
    `i morgen`), and those are card content like any other. **mini** = everything else the
    library holds: rows present only because a live card's derived Norwegian cites them."""
    composed, live = set(), 0
    with io.open(CARDS, encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if c.get("live"):
                live += 1
                composed.update(c["articles"])
    inlined = set()
    for a in composed:
        if a in rows:
            inlined.update(rows[a].get("exprs") or [])
    inlined -= composed
    seed_k = {i for i in composed | inlined if i in keep}
    mini_k = {i for i in keep if i not in seed_k}
    return live, seed_k, mini_k, len(inlined & set(keep))


def _iter_units(r):
    for s in r["senses"]:
        yield s
        for sub in s.get("subs", []):
            yield sub


def complete(r):
    """Finished: every sense and subsense translated, every example translated."""
    for u in _iter_units(r):
        if (u.get("no") or []) and u.get("en") is None:
            return False
        if any(e[1] is None for e in u.get("ex") or []):
            return False
    return True


def summary_due(r):
    """Does the dictionary's SECOND bar (A35) oblige this row to carry a summary block?
    Complete at the seed bar (`complete_strict`) AND a lemma article — **a fixed expression
    is excluded** (Robin, 2026-09-10, the summary-block review's Fable sitting): a summary
    gloss does not fit a phrase built from several glosses, and the expression's authored
    set-phrase box already serves as its headline wherever it is cited (the citing agent is
    told to weigh it as the link's gloss, `authoring-agent.md`); and an expression features
    almost only as an embedded article on its headword's card. The few expressions that ARE
    the seed of a live card keep guardrail 19's obligation unchanged — that is the deck's bar,
    not this one. Measured at the ruling: 5,890 of A35's 14,534 rows were expressions."""
    return r.get("pos_en") != "fixed expression" and complete_strict(r)


def complete_strict(r):
    """…and etymology and every compound gloss — what a live card actually renders."""
    if not complete(r):
        return False
    ety = r.get("etymology") or {}
    if (ety.get("no") or []) and ety.get("en") is None:
        return False
    for u in _iter_units(r):
        for b in u.get("comp") or []:
            if any(it.get("en") is None for it in b.get("items", [])):
                return False
    return True


def meets_mini_obligation(r):
    """Guardrail 2's bar for a bare href: every sense's ``en``, first example per unit."""
    for u in _iter_units(r):
        if (u.get("no") or []) and u.get("en") is None:
            return False
        ex = u.get("ex") or []
        if ex and ex[0][1] is None:
            return False
    return True


# --- report -----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Authored-English coverage of Bokmalsordboka, and per-article completeness.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--include-expr", action="store_true",
                    help="count fixed-expression articles too (default: lemma articles only)")
    ap.add_argument("--obligation", action="store_true",
                    help="also report guardrail 2's own bar for minis, not just completeness")
    ap.add_argument("--validate", action="store_true",
                    help="check the structural counter against the library's own rows")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    a = ap.parse_args()

    m = read_mirror(a.include_expr)
    rows, keep, tot, auth, extra = read_library(a.include_expr)
    live, seed, mini, n_inlined = partition(rows, keep)
    M = sum(m["units"].values())
    T, A = sum(tot.values()), sum(auth.values())
    scope = "all articles" if a.include_expr else "lemma articles only"

    def done(ids, fn):
        return sum(1 for i in ids if fn(rows[i]))

    sc, mc = done(seed, complete), done(mini, complete)

    if a.json:
        print(json.dumps(
            {"scope": scope, "mirror": m, "library_units": tot, "authored_units": auth,
             "extra": extra, "live_cards": live,
             "articles": {"dictionary": m["articles"], "library": len(keep),
                          "seed": len(seed), "mini": len(mini),
                          "seed_complete": sc, "mini_complete": mc,
                          "seed_complete_strict": done(seed, complete_strict),
                          "mini_meets_obligation": done(mini, meets_mini_obligation),
                          "inlined_expressions_excluded": n_inlined}},
            ensure_ascii=False, indent=1))
        return

    print("Coverage of Bokmalsordboka - %s" % scope)
    print("  dictionary: %d published articles (%d drafts skipped, %d fixed expressions %s)"
          % (m["articles"], m["drafts"], m["expr_articles"],
             "included" if a.include_expr else "excluded"))
    print("  library:    %d rows over %d live cards" % (len(keep), live))
    print()
    print("1. LINES")
    print("   %-22s %11s %11s %11s %8s" % ("", "dictionary", "in library", "authored", "of dict"))
    for k in KEYS:
        print("   %-22s %11d %11d %11d %7.1f%%"
              % (LABEL[k], m["units"][k], tot[k], auth[k],
                 100.0 * auth[k] / max(m["units"][k], 1)))
    print("   %-22s %11d %11d %11d %7.1f%%" % ("TOTAL", M, T, A, 100.0 * A / max(M, 1)))
    print("   beyond the source: %d set-phrase lines, %d added sentences (%d translated), "
          "%d summary blocks" % (extra["idiom"], extra["ex_added"], extra["ex_added_en"],
                                 extra["summary"]))
    print()
    print("2. ARTICLES fully authored (every sense and every example)")
    print("   %-22s %11s %11s %8s" % ("", "in library", "complete", "pct"))
    for name, ids, n in (("seed (on a live card)", seed, sc), ("mini-only (cited)", mini, mc)):
        print("   %-22s %11d %11d %7.1f%%" % (name, len(ids), n, 100.0 * n / max(len(ids), 1)))
    both = len(seed) + len(mini)
    print("   %-22s %11d %11d %7.1f%%" % ("TOTAL", both, sc + mc, 100.0 * (sc + mc) / max(both, 1)))
    print("   of the dictionary's %d articles: %.1f%%"
          % (m["articles"], 100.0 * (sc + mc) / max(m["articles"], 1)))
    print("   seed includes %d row(s) inlined into a card as a sub-article%s"
          % (n_inlined, "" if a.include_expr else
             "; the ~5.9k inlined fixed expressions are excluded - not lemma articles"))
    if a.obligation:
        ok = done(mini, meets_mini_obligation)
        print("   guardrail 2's bar for a bare href (all senses + first example): "
              "%d/%d minis (%.1f%%)" % (ok, len(mini), 100.0 * ok / max(len(mini), 1)))
        print("   seed articles complete incl. etymology and comp: %d/%d"
              % (done(seed, complete_strict), len(seed)))

    if a.validate:
        print()
        print("3. VALIDATION - structural counter vs the rows those captures derived to")
        import fetch  # noqa: E402  (only needed here)
        src, row = dict.fromkeys(KEYS, 0), dict.fromkeys(KEYS, 0)
        for i, r in keep.items():
            art = fetch.load_source(i)
            if art is None:
                continue
            c = count_units(art)
            for k in KEYS:
                src[k] += c[k]
            row["ety"] += len((r.get("etymology") or {}).get("no") or [])
            for s in r["senses"]:
                for u, key in [(s, "sense_seg")] + [(x, "sub_seg") for x in s.get("subs", [])]:
                    row[key] += len(u.get("no") or [])
                    row["ex"] += len(u.get("ex") or [])
                    row["comp"] += sum(len(b.get("items", [])) for b in u.get("comp") or [])
        print("   %-22s %11s %11s %8s" % ("", "counter", "rows", "delta"))
        for k in KEYS:
            print("   %-22s %11d %11d %8d" % (LABEL[k], src[k], row[k], src[k] - row[k]))


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
