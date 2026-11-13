"""Ordbokene's live layout beside ours (decisions 102) — a comparison script, NOT a test.

Run by the session before each deploy, never in the test run: it loads ordbokene.no's pages
(about forty, one at a time, with a pause between), so it is slow, it would fail whenever their
site is down, and it would load their servers on every build. It reports and never blocks: a
difference goes to Robin, and the numbers pinned in `test_ordpar_browser_cardwidth.py` change
only on his word (the session's call at his delegation, decisions 102).

What it measures, in headless Edge (rendered geometry only on ordbokene's side: boxes and the text
shown, never its code), each width a fresh load:

1. **The card** of *fange* III (`/eng/bm/13791` against our `/bm-en/13791/`) at a spread of window
   widths including each step's edges, on a computer and in phone emulation: ordbokene's card
   against the pinned table (has ordbokene changed?) and ours against ordbokene's.
2. **The table layout** of *fange* III, *trøtte* (62174) and *vitenskapsmann* (68839) at 800,
   1,024, 1,280 and 1,600 px: wide or narrow on each side, and how far a table runs past each
   card. Ours decides by fit, ordbokene by the window (wide from 1,024 px), so a difference at a
   narrower window is our deliberate divergence where our table fits (`divergences.md`) and is
   listed as such, not as a difference.

Usage (from the repository root):

    python ordpar/tests/browser/compare_ordbokene.py              # ours = https://ordpar.no
    python ordpar/tests/browser/compare_ordbokene.py --local      # ours = the build in ordpar/out/
    python ordpar/tests/browser/compare_ordbokene.py --ours URL   # ours = any other copy
    python ordpar/tests/browser/compare_ordbokene.py --json FILE  # also write the raw readings

Prints one line per reading and a summary; exit status 0 when nothing differs beyond the
tolerance (1 px), 1 when something does, 2 when it could not run (no Edge or bun).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import harness  # noqa: E402
from test_ordpar_browser_cardwidth import ORDBOKENE_CARD, TOLERANCE  # noqa: E402

OBK = "https://ordbokene.no"
CARD_WIDTHS = [360, 600, 782, 784, 800, 1000, 1022, 1024, 1040, 1100, 1278, 1280, 1296, 1400,
               1534, 1536, 1552, 1600, 1920]
PHONE_WIDTHS = [360, 390, 412]
TABLES = [{"id": 13791, "word": "fange"}, {"id": 62174, "word": "trøtte"}, {"id": 68839, "word": "vitenskapsmann"}]
TABLE_WIDTHS = [800, 1024, 1280, 1600]
#: ordbokene's switch, measured 2026-10-23: wide when the window is at least this wide, at load
OBK_WIDE_FROM = 1024


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ours", help="the copy of ours to measure (default https://ordpar.no)")
    ap.add_argument("--local", action="store_true", help="measure the build in ordpar/out/ instead")
    ap.add_argument("--json", help="write the raw readings to this file")
    a = ap.parse_args(argv)
    if a.local:
        os.environ.pop("ORDPAR_TEST_BASE", None)
    else:
        os.environ["ORDPAR_TEST_BASE"] = a.ours or "https://ordpar.no"
    why = harness.skip_reason()
    if why:
        print("compare_ordbokene: cannot run —", why)
        return 2
    site = harness.Site()
    try:
        res = site.check("compare.js", dict(
            obk=OBK, cards=dict(id=13791, word="fange", widths=CARD_WIDTHS, phone=PHONE_WIDTHS),
            tables=TABLES, tableWidths=TABLE_WIDTHS), timeout=1500)
    finally:
        site.close()
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)

    diffs, notes = [], []
    print("ours: %s   ordbokene: %s" % (res["base"], res["obk"]))
    print("\n1. The card of fange III (window -> ordbokene / ours, px)")
    for r in res["cards"]:
        o, u = r["obk"], r["ours"]
        tag = "%s %d" % ("phone" if r["phone"] else "window", r["w"])
        if o.get("err") or u.get("err"):
            diffs.append("%s: not measured (ordbokene %s, ours %s)" % (tag, o.get("err"), u.get("err")))
            print("  %-13s  %s" % (tag, diffs[-1]))
            continue
        line = "  %-13s  ordbokene %7.1f   ours %7.1f" % (tag, o["card"], u["card"])
        if abs(o["card"] - u["card"]) > TOLERANCE:
            diffs.append("%s: ours %.1f px, ordbokene %.1f px" % (tag, u["card"], o["card"]))
            line += "   DIFFERS"
        if o["cw"] != u["cw"]:
            notes.append("%s: the page widths differ (ordbokene %s, ours %s), so a fluid card may differ by as much"
                         % (tag, o["cw"], u["cw"]))
        pinned = ORDBOKENE_CARD.get(r["w"]) if not r["phone"] else None
        if pinned and abs(o["card"] - pinned[0]) > TOLERANCE:
            diffs.append("%s: ordbokene's card is now %.1f px, the pinned table says %d — ordbokene has changed"
                         % (tag, o["card"], pinned[0]))
            line += "   ORDBOKENE CHANGED (pinned %d)" % pinned[0]
        print(line)

    print("\n2. The inflection table (window -> layout, px past the card: ordbokene / ours)")
    for r in res["tables"]:
        o, u = r["obk"], r["ours"]
        tag = "%s %d" % (r["word"], r["w"])
        if o.get("err") or u.get("err") or not o.get("layout") or not u.get("layout"):
            diffs.append("%s: not measured (ordbokene %s, ours %s)" % (tag, o, u))
            print("  %-20s  %s" % (tag, diffs[-1]))
            continue
        line = "  %-20s  ordbokene %-6s %+5s   ours %-6s %+5s" % (
            tag, o["layout"], o["pastCard"], u["layout"], u["pastCard"])
        expected_obk = "wide" if r["w"] >= OBK_WIDE_FROM else "narrow"
        if o["layout"] != expected_obk:
            diffs.append("%s: ordbokene shows %s, its measured rule says %s — ordbokene has changed"
                         % (tag, o["layout"], expected_obk))
            line += "   ORDBOKENE CHANGED"
        if u["pastCard"] is not None and u["pastCard"] > TOLERANCE:
            diffs.append("%s: our table runs %d px past our card" % (tag, u["pastCard"]))
            line += "   OURS PAST THE CARD"
        if o["layout"] != u["layout"]:
            if r["w"] < OBK_WIDE_FROM and u["layout"] == "wide":
                notes.append("%s: ours wide where ordbokene is narrow — the table fits our card, "
                             "stacked if need be (the deliberate divergence, decisions 102, 108)" % tag)
                line += "   (divergence, by design)"
            else:
                diffs.append("%s: ours %s, ordbokene %s" % (tag, u["layout"], o["layout"]))
                line += "   DIFFERS"
        print(line)

    print("\nNotes:" if notes else "")
    for n in notes:
        print("  - " + n)
    if diffs:
        print("\n%d difference(s) beyond %g px:" % (len(diffs), TOLERANCE))
        for d in diffs:
            print("  - " + d)
        return 1
    print("\nNo difference beyond %g px." % TOLERANCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
