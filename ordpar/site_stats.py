"""How much of Bokmålsordboka Ordpar has translated: the numbers for the About page's statistics
line (Robin, 2026-10-22: "the total number of articles, and how many have been translated so
far … the *proportion* of the lines in Bokmålsordboka that has been translated"). Read-only;
stdlib only.

    python ordpar/site_stats.py --mirror "…/bm-articles.jsonl"
    python ordpar/site_stats.py --mirror "…/bm-articles.jsonl" --json out.json

What it counts, over the articles ordbokene.no SHOWS: every article of the mirror except those
with no `status` or `status` 1, and those with no headword in the data (`lemmas` empty or blank)
and no library row to give one: ordbokene's page answers "500: Error" and ours is not built (site
decisions 163, 2026-11-04; *på tide* and two more have `lemmas: []` but a translated row, and pages). (Until 2026-10-22 only `status` 8 counted, an assumption from the
parent repo's `scripts/coverage.py`; the side chat and the session checked it that day against
ordbokene's search, `ord.uib.no/api/articles?w=…&dict=bm&scope=e`: samples of statuses 2–6 —
*både* and *enten* among the 5s, *feminist*, *tomahawk* — are found, while the no-status ones
(*girokonto*, one of the *de* articles) and the one status 1 (*kong alkohol*) are not. What the
codes mean is not documented; the rule rests on those samples.)

* **articles** — every shown article, fixed expressions included;
* **translated** — those whose id has a row in the library (`articles.jsonl`): the row is the
  English (the library's rows are authored whole); split into **complete** (the row has a
  summary gloss, `summary.gloss`) and **without a summary** — the backlog the new authoring
  workflow brings to zero (Robin, 2026-10-22: "every translated article is made complete").
  The About page may name the split while the backlog lasts (Robin, 2026-10-22: "It would
  just dissapear the day we get the library upto date");
* **lines** — the dictionary's own text in the units it is written in, the same units as
  `scripts/coverage.py` (its "slots"): one etymology segment, one explanation of a sense or a
  subsense, one example (its quote and its explanation together), one item of a compound list.
  A fixed expression's "Se: …" line is left out, as the library leaves it out;
* **words** — the running words of the same text: each whitespace-separated piece holding a
  letter, a digit or a `$` (the source's placeholder for a referenced word); a compound-list item
  is one word;
* **added** — Ordpar's own example sentences (`ex_added` on a library row's senses and
  subsenses), over the shown articles: the **sentences**, the **articles** holding them and the
  **senses** (sense and subsense units) holding them. A library row the snapshot lacks is not a
  shown article, so its sentences do not count (2026-10-22: one, on *ligge på det siste*, 101365:
  450 sentences in 271 articles, where the whole library holds 451 in 272).

A line or a word counts as translated when its article does. With `--build-json` (by default
`out/build.json`, when it exists) the build's own page counts are printed beside them: the site
has a page for every article of the mirror, the 44 unshown ones included, and for a few library
rows the snapshot lacks, so its totals are a little higher than the shown counts.

The walk restates `scripts/coverage.py`'s (`collect_senses`, `collect_subs`, `count_units`); the
test (`ordpar/tests/test_ordpar_site_stats.py`) holds the two to the same unit counts. The build calls
`measure()` on every run, over the rows it builds the pages from (the render gate's, so a held
added sentence is not counted), fills the About page's and the README's numbers from it
(`sitegen/about.py`, `ordpar/about.md`) and records it in `out/build.json` as `site_stats`
(wired 2026-10-22, on Robin's approval of the About page, site decisions 63).
"""
import argparse
import io
import json
import os
import re
import sys

ORDPAR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ORDPAR)
HIDDEN = (None, "None", "1")   # statuses ordbokene's search does not show (sampled, 2026-10-22)
_WORD = re.compile(r"[\w$]")


def words(text):
    """Running words: whitespace-separated pieces with a letter, digit or `$` in them."""
    return sum(1 for t in (text or "").split() if _WORD.search(t))


def _defs(node):
    return [e for e in node.get("elements", []) if e.get("type_") == "definition"]


def _is_gloss(node):
    els = node.get("elements", [])
    if any(e.get("type_") == "explanation" for e in els):
        return True
    return not _defs(node) and any(e.get("type_") == "example" for e in els)


def senses(article):
    out = []

    def walk(node):
        for child in _defs(node):
            out.append(child) if _is_gloss(child) else walk(child)
    for d in (article.get("body") or {}).get("definitions") or []:
        out.append(d) if _is_gloss(d) else walk(d)
    return out


def subs(sense):
    out = []

    def rec(node):
        for child in _defs(node):
            if _is_gloss(child):
                out.append(child)
            rec(child)
    rec(sense)
    return out


def _compound_items(node):
    """Items of the compound lists this unit owns (a nested subsense owns its own)."""
    n = 0

    def walk(x, root):
        nonlocal n
        if isinstance(x, dict):
            if x.get("type_") == "definition" and not root:
                return
            if x.get("type_") == "compound_list":
                n += sum(1 for el in x.get("elements", []) if el.get("type_") == "article_ref")
            for v in x.values():
                walk(v, False)
        elif isinstance(x, list):
            for v in x:
                walk(v, root)
    walk(node, True)
    return n


def is_expression(article):
    return any("EXPR" in (pi.get("tags") or [])
               for lem in article.get("lemmas") or [] for pi in lem.get("paradigm_info") or [])


def _see_line(content):
    c = (content or "").lstrip()
    return c.startswith("Se:") or c.startswith("Sjå:")


def text_of(article):
    """(lines, words) of one article's own text."""
    lines = n_words = 0
    for e in (article.get("body") or {}).get("etymology") or []:
        lines += 1
        n_words += words(e.get("content"))
    expr = is_expression(article)
    for s in senses(article):
        for u in [s] + subs(s):
            for e in u.get("elements", []):
                kind = e.get("type_")
                if kind == "explanation":
                    if expr and _see_line(e.get("content")):
                        continue
                    lines += 1
                    n_words += words(e.get("content"))
                elif kind == "example":
                    lines += 1
                    n_words += (words((e.get("quote") or {}).get("content"))
                                + words((e.get("explanation") or {}).get("content")))
            items = _compound_items(u)
            lines += items
            n_words += items
    return lines, n_words


def read_rows(path):
    with io.open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def added_examples(row):
    """(sentences, senses) of one row's `ex_added`: the sentences, and the sense and subsense
    units holding at least one."""
    n = units = 0
    for s in row.get("senses") or []:
        for u in [s] + (s.get("subs") or []):
            k = len(u.get("ex_added") or [])
            n += k
            units += k > 0
    return n, units


def library_ids(rows):
    """{id: (has a summary gloss, added sentences, senses holding them)} over the library's
    rows (a path to `articles.jsonl`, or the rows themselves)."""
    if isinstance(rows, str):
        rows = read_rows(rows)
    return {row["id"]: (bool((row.get("summary") or {}).get("gloss")),) + added_examples(row)
            for row in rows}


def measure(mirror, library=None, rows=None, overlay=None):
    """The counts as a dict: `articles`, `lines`, `words`, each `{"all", "translated", "share"}`
    (share a fraction, 0-1); `articles` also `complete` and `no_summary` (of the translated);
    `added` `{"sentences", "articles", "senses"}`. The library is a path (`library`) or the rows
    themselves (`rows`, as the build passes them). `overlay` (site decisions 182, the build's
    resolved `sitegen.overlay.Overlay`): the handover's corrections, applied to each article
    before its lines and words are counted, as its page shows it."""
    lib = library_ids(rows if rows is not None else library)
    added = {"sentences": 0, "articles": 0, "senses": 0}
    tot = {"articles": 0, "lines": 0, "words": 0}
    done = dict.fromkeys(tot, 0)
    complete = 0
    with io.open(mirror, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            d = rec.get("data") or {}
            if overlay is not None:
                d = overlay.apply(rec.get("id"), d) or {}
            if d.get("status") is None or str(d.get("status")) in HIDDEN:
                continue
            aid = rec.get("id", d.get("article_id"))
            if aid not in lib and not any(isinstance(l.get("lemma"), str) and l["lemma"].strip()
                                          for l in d.get("lemmas") or []):
                continue                    # site decisions 163: no headword anywhere, no page
            lines, n_words = text_of(d)
            aid = rec.get("id", d.get("article_id"))
            hit = aid in lib
            if hit:
                summary, n_added, n_units = lib[aid]
                complete += summary
                if n_added:
                    added["sentences"] += n_added
                    added["articles"] += 1
                    added["senses"] += n_units
            for k, v in (("articles", 1), ("lines", lines), ("words", n_words)):
                tot[k] += v
                if hit:
                    done[k] += v
    out = {k: {"all": tot[k], "translated": done[k],
               "share": (done[k] / tot[k]) if tot[k] else 0.0} for k in tot}
    out["articles"].update(complete=complete, no_summary=done["articles"] - complete)
    out["added"] = added
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 epilog=__doc__.split("\n\n", 1)[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mirror", required=True, help="the ordbokene mirror, bm-articles.jsonl")
    ap.add_argument("--articles", default=os.path.join(
                        os.path.abspath(os.environ.get("ORDBOK_DATA_DIR") or ROOT), "articles.jsonl"),
                    help="the library (default: the repository's articles.jsonl)")
    ap.add_argument("--build-json", default=os.path.join(ORDPAR, "out", "build.json"),
                    help="the build's report, for its page counts (skipped if absent)")
    ap.add_argument("--json", metavar="PATH", help="also write the counts as JSON")
    a = ap.parse_args(argv)
    stats = measure(a.mirror, a.articles)
    if a.build_json and os.path.exists(a.build_json):
        with io.open(a.build_json, encoding="utf-8") as f:
            b = json.load(f)
        stats["site_pages"] = {"all": b.get("pages"), "translated": b.get("translated"),
                               "built_at": b.get("built_at")}
    for k, label in (("articles", "shown articles"), ("lines", "lines of text"),
                     ("words", "running words")):
        s = stats[k]
        print("%-20s %9d translated of %9d  (%.1f %%)" % (label, s["translated"], s["all"],
                                                           100 * s["share"]))
    art = stats["articles"]
    print("%-20s %9d complete (with a summary gloss), %d without one"
          % ("  of the translated", art["complete"], art["no_summary"]))
    ad = stats["added"]
    print("%-20s %9d sentences in %d articles (%d senses)"
          % ("added examples", ad["sentences"], ad["articles"], ad["senses"]))
    if "site_pages" in stats:
        p = stats["site_pages"]
        print("%-20s %9s translated of %9s  (the build's report, %s)"
              % ("site pages", p["translated"], p["all"], p["built_at"]))
    if a.json:
        with io.open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump(stats, f, indent=1)
            f.write("\n")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
