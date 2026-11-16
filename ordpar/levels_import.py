#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write `ordpar/levels.tsv`, the CEFR levels the site draws, from the merged levels file
(site decisions 187).

The levels are Ordpar's own: judged article by article with AI against the CEFR's descriptions of
the levels, in Ordpar's private repository, and merged there into one file of one row per article
id (columns `article`, `lemma`, `level`, `shown`, `kind`, `confidence`, `text`, `source`). This
tool keeps the two columns the site needs, `article` and `shown` (A1, A2, B1, B2, or C for C1 and
C2), and writes them where the build reads them:

    python ordpar/levels_import.py                  # from the default source
    python ordpar/levels_import.py SOURCE.tsv       # from another
    python ordpar/levels_import.py --out PATH       # somewhere else than ordpar/levels.tsv

The file it writes: a comment line naming its source and decisions 187, the header
`article<TAB>shown`, then one line per article id, sorted by id, LF line ends
(`sitegen/levels.py`). It refuses a `shown` outside the five values, a duplicate id and a source
without the two columns, and writes nothing then. The default source is in the private
repository; where it is missing (the public repository) the tool says so and stops, and the
committed `ordpar/levels.tsv` stays as it is. Standard library only.
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from ordpar.sitegen import levels  # noqa: E402

#: The merged levels file, in the private repository (repository-relative)
SOURCE = "docs/sessions/2026-10-24-deck-release/evidence/tags/cefr-levels.tsv"


class Refused(SystemExit):
    pass


def read_source(path):
    """`[(article id, shown)]` sorted by id; `Refused` on a bad level, a duplicate id or a missing
    column."""
    rows, seen = [], set()
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        if not reader.fieldnames or "article" not in reader.fieldnames or "shown" not in reader.fieldnames:
            raise Refused("REFUSED — %s has no columns `article` and `shown`" % path)
        for n, r in enumerate(reader, 2):
            aid, shown = (r.get("article") or "").strip(), (r.get("shown") or "").strip()
            if not aid.isdigit():
                raise Refused("REFUSED — %s:%d: not an article id: %r" % (path, n, aid))
            if shown not in levels.SHOWN:
                raise Refused("REFUSED — %s:%d: article %s has the level %r, not one of %s"
                              % (path, n, aid, shown, ", ".join(levels.SHOWN)))
            if int(aid) in seen:
                raise Refused("REFUSED — %s:%d: article %s twice" % (path, n, aid))
            seen.add(int(aid))
            rows.append((int(aid), shown))
    return sorted(rows)


def text(rows, source_name):
    """The levels file's text (module doc)."""
    out = ["# CEFR levels as the site draws them (C is C1 and C2), from %s; decisions 187; "
           "written by ordpar/levels_import.py" % source_name, levels.HEADER]
    out += ["%d\t%s" % r for r in rows]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", default=None,
                    help="the merged levels file (default: %s, in the private repository)" % SOURCE)
    ap.add_argument("--out", default=levels.PATH, help="where to write (default: ordpar/levels.tsv)")
    a = ap.parse_args(argv)
    path = a.source or os.path.join(ROOT, SOURCE)
    if not os.path.isfile(path):
        if a.source:
            raise Refused("no such file: %s" % a.source)
        raise Refused("The merged levels file is not here (%s). It is kept in Ordpar's private "
                      "repository, so in the public repository there is nothing to import: the "
                      "committed ordpar/levels.tsv is the levels as they stand. Nothing written."
                      % SOURCE)
    rows = read_source(path)
    name = SOURCE if not a.source else os.path.basename(path)
    data = text(rows, name)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    counts = {lv: 0 for lv in levels.SHOWN}
    for _aid, lv in rows:
        counts[lv] += 1
    print("wrote %s: %d articles (%s)" % (os.path.relpath(a.out, ROOT) if os.path.splitdrive(a.out)[0].lower()
                                          == os.path.splitdrive(ROOT)[0].lower() else a.out,
                                          len(rows), ", ".join("%s %d" % (k, v) for k, v in counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
