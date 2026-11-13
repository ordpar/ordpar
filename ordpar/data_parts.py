#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bokmålsordboka's articles file in parts, and back (decisions 184).

The build reads the mirror's `bm-articles.jsonl`, one article per line in id order, about 205 MB.
The public repository stores it in parts under 50 MB each, uncompressed, so that git can store a
week's changes as differences rather than a new copy: `bm-articles.<first id>.jsonl`, each part
holding the articles whose ids fall in its range of `PART_IDS` ids. A part's range never moves,
so an article stays in the same part from one week to the next.

Before a build, put the file back together once (the one join step):

    python ordpar/data_parts.py join data/bokmalsordboka        # writes data/bokmalsordboka/bm-articles.jsonl

The joined file is byte for byte the file the parts were cut from. `split` is the export's side:

    python ordpar/data_parts.py split <bm-articles.jsonl> <folder>

Both check that every line is an article whose id belongs to its part, in ascending order.
Standard library only.
"""
import json
import os
import re
import sys

NAME = "bm-articles.jsonl"
PART = re.compile(r"^bm-articles\.(\d{6})\.jsonl$")
PART_IDS = 20000            # ids per part: the largest part was 41.6 MB on 2026-11-12
LIMIT = 50 * 1000 * 1000    # bytes: a part at or above this is refused (GitHub warns at 50 MB)
_ID = re.compile(rb'^\{"id": (\d+),')


class Refused(Exception):
    pass


def line_id(line):
    m = _ID.match(line)
    if m:
        return int(m.group(1))
    return int(json.loads(line)["id"])


def part_name(first):
    return "bm-articles.%06d.jsonl" % first


def split(src, folder, part_ids=PART_IDS, limit=LIMIT):
    """Cut ``src`` into parts in ``folder``; returns ``[(path, bytes)]``. Refuses a line out of
    id order or a part that would reach ``limit`` (lower ``part_ids`` then)."""
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        if PART.match(name):
            os.remove(os.path.join(folder, name))
    out, fh, current, size, prev = [], None, None, 0, -1
    try:
        with open(src, "rb") as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                aid = line_id(line)
                if aid <= prev:
                    raise Refused("%s line %d: id %d after %d, not in id order" % (src, n, aid, prev))
                prev = aid
                first = aid - aid % part_ids
                if first != current:
                    if fh:
                        fh.close()
                        out.append((path, size))
                    current, size = first, 0
                    path = os.path.join(folder, part_name(first))
                    fh = open(path, "wb")
                size += len(line)
                if size >= limit:
                    raise Refused("part %s reaches %d bytes: lower PART_IDS" % (part_name(first), size))
                fh.write(line)
    finally:
        if fh:
            fh.close()
    if current is not None:
        out.append((path, size))
    return out


def parts(folder):
    return sorted(n for n in os.listdir(folder) if PART.match(n))


def join(folder, out=None, part_ids=PART_IDS):
    """Write the parts of ``folder`` as one file (default ``folder/bm-articles.jsonl``), checking
    each line's id against its part. Returns ``(path, lines)``."""
    names = parts(folder)
    if not names:
        raise Refused("no bm-articles.<id>.jsonl parts in %s" % folder)
    out = out or os.path.join(folder, NAME)
    tmp = out + ".tmp"
    n, prev = 0, -1
    with open(tmp, "wb") as dst:
        for name in names:
            first = int(PART.match(name).group(1))
            with open(os.path.join(folder, name), "rb") as f:
                for line in f:
                    aid = line_id(line)
                    if not first <= aid < first + part_ids or aid <= prev:
                        dst.close()
                        os.remove(tmp)
                        raise Refused("%s: id %d does not belong there" % (name, aid))
                    prev = aid
                    dst.write(line)
                    n += 1
    os.replace(tmp, out)
    return out, n


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:] if argv is None else argv
    try:
        if len(argv) == 2 and argv[0] == "join":
            path, n = join(argv[1])
            print("joined %d articles into %s" % (n, path))
            return 0
        if len(argv) == 3 and argv[0] == "split":
            for path, size in split(argv[1], argv[2]):
                print("%s %d bytes" % (path, size))
            return 0
    except Refused as e:
        print("refused: %s" % e, file=sys.stderr)
        return 1
    print(__doc__)
    return 0 if argv and argv[0] in ("-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main())
