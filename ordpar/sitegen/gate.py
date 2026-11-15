# -*- coding: utf-8 -*-
"""The example gate, one code path for the private build and the public one (decisions 184).

An added example sentence reaches a reader only once a native speaker has written or ratified it.
The rule lives in the private pipeline, `scripts/triage.py`
(`publishable`), which reads the triage log; neither is published. So:

* **where `triage` can be imported** (the private repository), the build applies
  `triage.publishable` to the library exactly as before;
* **where it cannot** (the public repository), the library must already be gated: the export
  (`ordpar/export_public.py`) applies the same function, writes the gated library, and beside it
  a marker, `<library>.gate.json`, naming the gate and the library's SHA-256. The build accepts
  such a library as it is, and refuses an unmarked one, or one whose bytes no longer match its
  marker, with a message saying why.

The marker holds no date, so the same library gives the same marker (the export is byte-stable).
"""
import hashlib
import importlib
import importlib.util
import json
import os

GATE = "triage.publishable"
SUFFIX = ".gate.json"


class Refused(Exception):
    """The library cannot be built from: not gated, and no `triage` to gate it."""


def marker_path(library):
    return library + SUFFIX


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def marker(library, rows, held):
    """The marker's content for a gated library file (the export writes it)."""
    return {"gate": GATE, "held": held, "rows": rows, "sha256": sha256(library)}


def write_marker(library, rows, held):
    text = json.dumps(marker(library, rows, held), indent=1, sort_keys=True) + "\n"
    with open(marker_path(library), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return marker_path(library)


def triage_module():
    """`triage` when this checkout has it (the private repository), else None."""
    if importlib.util.find_spec("triage") is None:
        return None
    return importlib.import_module("triage")


def apply(rows, library):
    """``(rows, held, how)``: the rows a build may show. ``how`` says which side applied the gate."""
    triage = triage_module()
    if triage is not None:
        rows, held = triage.publishable(rows)
        return rows, held, "triage.publishable"
    path = marker_path(library)
    if not os.path.exists(path):
        raise Refused(
            "the library %s carries no gate marker (%s), and this checkout has no scripts/triage.py "
            "to apply the example gate. The marker, a small JSON file beside the library, records "
            "that its added example sentences have passed the gate, and the library's SHA-256; "
            "gate.write_marker (ordpar/sitegen/gate.py) writes it. How, for a library you have "
            "changed: data/README.md, \"Added example sentences and the example gate\""
            % (os.path.basename(library), os.path.basename(path)))
    with open(path, encoding="utf-8") as fh:
        mark = json.load(fh)
    if mark.get("gate") != GATE:
        raise Refused("%s names the gate %r, not %r" % (os.path.basename(path), mark.get("gate"), GATE))
    if mark.get("sha256") != sha256(library):
        raise Refused("the library %s has changed since it was gated (its SHA-256 no longer matches "
                      "%s). If the change is yours, write a new marker with gate.write_marker "
                      "(ordpar/sitegen/gate.py); how: data/README.md, \"Added example sentences "
                      "and the example gate\"" % (os.path.basename(library), os.path.basename(path)))
    return rows, 0, "gated at export (%s, %d held then)" % (os.path.basename(path), mark.get("held", 0))
