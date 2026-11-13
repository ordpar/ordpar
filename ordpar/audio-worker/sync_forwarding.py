r"""Copy the audio store's forwarding table into the Worker's bundle (site decisions 179).

The audio session's ``scripts/audio/forwarding.py`` writes ``<store>/forwarding.json``,
``{"written", "shipped", "current", "pairs": {"<old 16 hex>": "<new 16 hex>"}, "held"}``: the clip
names a shared deck still asks for, each with the clip that replaced it (audio decisions 26). This
script copies its pairs into ``src/forwarding.json``, which Wrangler bundles into the Worker, so a
deploy after it makes the Worker answer each old name with a redirect to its new one (README.md
§ Forwarding superseded names).

On the way it

* validates every name: 16 lower-case hex, the hex of the Worker's own ``NAME`` (``src/rules.js``);
* refuses a pair that forwards a name to itself (``a -> a``);
* **flattens chains**: ``a -> b`` and ``b -> c`` give ``a -> c`` and ``b -> c``, so the Worker
  follows the table once and a reader gets one redirect, never two;
* refuses a cycle (``a -> b -> a``), naming it;
* writes the file only when its text changes, and prints what it did.

    python -I ordpar/audio-worker/sync_forwarding.py              # the store's table
    python -I ordpar/audio-worker/sync_forwarding.py FILE         # another table
    python -I ordpar/audio-worker/sync_forwarding.py --out FILE   # write elsewhere (tests)

Exit status 0 when written or unchanged, 1 on a refusal (nothing written). Standard library only;
it reads the store and writes only the output file.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import local_paths  # noqa: E402  -- one machine's paths

# the store's table: this machine's, from ordpar/local-paths.json ("clip_store_forwarding")
STORE_TABLE = local_paths.get("clip_store_forwarding")
OUT = os.path.join(HERE, "src", "forwarding.json")
HEX16 = re.compile(r"^[0-9a-f]{16}$")


class Refused(Exception):
    """The table cannot be bundled; the message says why."""


def flatten(pairs):
    """``(flat, changed)``: every chain followed to its end, and how many targets that moved.

    Raises ``Refused`` on a bad name, a self-pair or a cycle."""
    if not isinstance(pairs, dict):
        raise Refused("'pairs' is not an object")
    for old, new in pairs.items():
        for which, name in (("old", old), ("new", new)):
            if not isinstance(name, str) or not HEX16.match(name):
                raise Refused("not a clip name (16 lower-case hex): %s %r in the pair %r -> %r"
                              % (which, name, old, new))
        if old == new:
            raise Refused("the name %s forwards to itself" % old)
    flat, changed = {}, 0
    for old in pairs:
        seen = [old]
        end = pairs[old]
        while end in pairs:
            if end in seen:
                raise Refused("a cycle: %s" % " -> ".join(seen[seen.index(end):] + [end]))
            seen.append(end)
            end = pairs[end]
        flat[old] = end
        if end != pairs[old]:
            changed += 1
    return dict(sorted(flat.items())), changed


def render(src, flat):
    """The bundled file's text: provenance first, then the pairs one to a line."""
    doc = {
        "about": "Superseded clip names and the clip each forwards to (site decisions 179); "
                 "written by sync_forwarding.py from the audio store's forwarding.json, never by hand.",
        "written": src.get("written"),
        "shipped": src.get("shipped"),
        "pairs": flat,
    }
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


def sync(path, out):
    """Read ``path``, write ``out`` if its text changes. Returns ``(read, flattened, written)``."""
    with open(path, encoding="utf-8") as f:
        try:
            src = json.load(f)
        except ValueError as e:
            raise Refused("%s is not JSON: %s" % (path, e))
    if not isinstance(src, dict) or "pairs" not in src:
        raise Refused("%s has no 'pairs'" % path)
    flat, changed = flatten(src["pairs"])
    text = render(src, flat)
    try:
        with open(out, encoding="utf-8", newline="") as f:
            old = f.read()
        if old == text:
            return len(src["pairs"]), changed, False
        # A re-run upstream stamps a new `written` with the same pairs: not a change worth a diff
        # (or a Worker deploy). Only the pairs and the shipped decks decide (the session, 2026-11-08).
        try:
            prev = json.loads(old)
        except ValueError:
            prev = None
        if (isinstance(prev, dict) and prev.get("pairs") == flat
                and prev.get("shipped") == src.get("shipped")):
            return len(src["pairs"]), changed, False
    except FileNotFoundError:
        pass
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, out)
    return len(src["pairs"]), changed, True


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", nargs="?", default=STORE_TABLE,
                    help="the store's table (default: %(default)s)")
    ap.add_argument("--out", default=OUT, help="default: src/forwarding.json beside this script")
    a = ap.parse_args(argv)
    if not a.path:
        local_paths.require("clip_store_forwarding", "the table's path as the argument")
    try:
        read, changed, written = sync(a.path, a.out)
    except Refused as e:
        print("refused, nothing written: %s" % e, file=sys.stderr)
        return 1
    print("read: %d pairs from %s" % (read, a.path))
    print("flattened: %d chained pairs pointed at their last clip" % changed)
    print(("written: %s" if written else "unchanged: %s (not written)") % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
