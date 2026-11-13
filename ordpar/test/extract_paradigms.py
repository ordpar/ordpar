#!/usr/bin/env python3
"""Extract the inflection test set from the Bokmål mirror.

Writes ``ordpar/test/paradigms.json``: one entry per article, holding the
article's ``data.lemmas`` **verbatim** plus the heading and the capture file
name the test page prints under each table.

The mirror lives in another worktree and is read-only:

    python ordpar/test/extract_paradigms.py --mirror "$(python ordpar/local_paths.py mirror)"

The ids are the paradigm shapes of the captures note
(docs/sessions/2026-09-19-ordpar-site-review/evidence/
ordbokene-inflection-captures-2026-09-20.md), in the note's own order, then
the shapes the brief named but Robin did not capture, then the shapes found by
surveying the whole mirror that no capture covers.
"""

import argparse
import json
import sys
from pathlib import Path

# Captures of ordbokene's narrow-screen (transposed) tables, by article id.
NARROW_CAPTURES = {
    61543: "ordbokene-tore-toerre-inflection-narrow-en-2026-09-20.png",
}

# Live-site DOM reads of the narrow layout that have no PNG beside them.
NARROW_NOTES = {
    27603: "narrow layout read from the live site at 500 px, 2026-09-20",
    50675: "narrow layout read from the live site at ~670 px, 2026-09-20",
}

# (id, capture file name or None, what the article is there to test)
WANTED = [
    # 1-10: the ten captures, in the captures note's order
    (27603, "ordbokene-jente-inflection-en-2026-09-20.png",
     "two-gender noun, one lemma - gender row axis, plural spanned"),
    (24627, "ordbokene-hus-inflection-en-2026-09-20.png",
     "neuter noun, no gender axis - two paradigms comma-joined (husa, husene)"),
    (7217, "ordbokene-bra-inflection-en-2026-09-20.png",
     "adjective - two tables, degrees of comparison"),
    (69211, "ordbokene-vaere-inflection-en-2026-09-20.png",
     "defective verb - participle columns dropped, not left empty"),
    (12570, "ordbokene-en-inflection-en-2026-09-20.png",
     "determiner, two lemma forms - one unlabelled row each"),
    (11072, "ordbokene-du-inflection-en-2026-09-20.png",
     "pronoun - subject form / object form"),
    (40926, "ordbokene-noen-inflection-en-2026-09-20.png",
     "determiner with a plural column"),
    (61543, "ordbokene-tore-toerre-inflection-en-2026-09-20.png",
     "verb, two lemma forms x two paradigms - rowspans, no imperative column"),
    (7663, "ordbokene-bru-bro-inflection-en-2026-09-20.png",
     "two genders x two lemma forms - plural repeated per row"),
    (56144, "ordbokene-spise-inflection-en-2026-09-19.png",
     "regular verb, all 16 slots - both verb tables"),
    # 11-14: named by the brief, no capture
    (62174, None, "verb, two lemma forms x three paradigms (trotte/trette)"),
    (55343, None, "three-gender noun with two neuter paradigms (snorr)"),
    (21740, None, "the largest article (ga)"),
    (50675, None, "ten spelling variants in one row (selvfordypelse)"),
    # 15-22: shapes from the mirror survey that no capture covers
    (14771, None, "s-passive-only verb (VERB_sPass: finnes)"),
    (35408, None, "adjective with its own feminine column, 8 paradigms (liten)"),
    (11725, None, "adjectival determiner (DET_adj: egen)"),
    (41859, None, "comparable adverb (ADV_adj: ofte) - no capture, headers reconstructed"),
    (42925, None, "adjective with no positive forms (ovre) - table (i) dropped"),
    (36844, None, "adjective with a plural positive only (mange)"),
    (124935, None, "ordbokene mis-tag: lemma tagged NOUN with adjective cells"),
    (66495, None, "plurale tantum noun (vannkopper) - singular columns dropped"),
    (130705, None, "uninflected fixed expression - renders no table at all"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mirror", required=True,
                    help="path to bm-articles.jsonl (read-only, another worktree)")
    ap.add_argument("--out", default=str(here / "paradigms.json"),
                    help="output path (default: ordpar/test/paradigms.json)")
    args = ap.parse_args()

    wanted = {i: (cap, note) for i, cap, note in WANTED}
    found = {}
    with open(args.mirror, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id") in wanted:
                found[row["id"]] = row
                if len(found) == len(wanted):
                    break

    missing = [i for i in wanted if i not in found]
    if missing:
        print("MISSING ids (not in the mirror): %s" % missing)

    roman = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}
    out = []
    for article_id, capture, note in WANTED:
        row = found.get(article_id)
        if row is None:
            continue
        lemmas = (row.get("data") or {}).get("lemmas") or []
        heading = ", ".join(
            (lem.get("lemma") or "") + (" " + roman.get(lem.get("hgno") or 0, str(lem.get("hgno"))) if lem.get("hgno") else "")
            for lem in lemmas
        )
        out.append({
            "id": article_id,
            "heading": heading,
            "capture": capture,
            "capture_narrow": NARROW_CAPTURES.get(article_id),
            "narrow_note": NARROW_NOTES.get(article_id),
            "note": note,
            "lemmas": lemmas,          # verbatim
        })

    payload = {
        "source": "bm-articles.jsonl (ordbokene Bokmål mirror), read-only",
        "extracted": "by ordpar/test/extract_paradigms.py",
        "articles": out,
    }
    dest = Path(args.out)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote %s: %d articles (%d bytes)" % (dest, len(out), dest.stat().st_size))
    for entry in out:
        print("  %-7d %-42s %s" % (entry["id"], entry["heading"], entry["capture"] or "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
