#!/usr/bin/env python3
"""Check 4: quotation marks without their partner in the same text element.

Within one text element (a definition's explanation, an example quote or its
explanation, one etymology element), after the ``$`` placeholders are filled:
  unclosed_opening   an opening ‘ “ or « with no closing mark after it ("grjót ‘stein");
  unopened_closing   a closing ’ ” or » with no opening mark before it, where it cannot
                     be an apostrophe ("kinesisk ’rund ting, dollar’");
  straight_close     an opening curly mark closed by a straight one: ‘stein' or “ord" —
                     a pair, but a mismatched one, reported as its own type;
  straight_open      the reverse: a straight opening closed by a curly one ('sol’).

A ’ directly after a letter, with no ‘ open, is read as an apostrophe (the genitive in
"Johannes’ åpenbaring", or "Sant’ Elmo") and is not reported; nor is a ’ between two
letters ("sommer’n"). Straight quotes used as a pair on their own ('i går') are not
reported.

An embedded fixed expression (sub_article) is checked in its own article. From the
embedded copy, only the text elements that its own article lacks are read, or all of
them when the expression has no article in the input (--no-embedded turns this off);
such a finding carries the parent's article_id and lemma, and its location begins
'artikkel <parent>, uttrykk "<expression>" (<expression id>)'.

It reads Nynorskordboka (--dictionary nn) exactly as it reads Bokmålsordboka, the
default: nothing in it depends on the language.

Python 3 standard library only, no network.
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "mark", "near", "context"]

OPEN = {"‘": "’", "“": "”", "«": "»"}
CLOSE = {v: k for k, v in OPEN.items()}
STRAIGHT = {"'": "‘", '"': "“"}          # straight mark -> the curly opening it stands for


def _letter(s, i):
    return 0 <= i < len(s) and s[i].isalpha()


def scan(text):
    """Return [(type, mark, position)] for one string, in text order."""
    found = []
    stack = []                                  # (opening mark, position)
    for i, ch in enumerate(text):
        if ch in OPEN:
            stack.append((ch, i))
        elif ch in CLOSE:
            want = CLOSE[ch]
            if ch == "’" and _letter(text, i - 1) and _letter(text, i + 1):
                continue                        # apostrophe inside a word
            if any(m == want for m, _ in stack):
                while stack:                    # close the nearest matching opening;
                    m, p = stack.pop()          # a curly one opened after it is unclosed
                    if m == want:
                        break
                    if m in OPEN:
                        found.append(("unclosed_opening", m, p))
            elif stack and stack[-1][0] in STRAIGHT and STRAIGHT[stack[-1][0]] == want:
                m, p = stack.pop()
                found.append(("straight_open", m + "…" + ch, p))
            elif ch == "’" and _letter(text, i - 1):
                continue                        # apostrophe after a word: Johannes’
            else:
                found.append(("unopened_closing", ch, i))
        elif ch in STRAIGHT:
            if _letter(text, i - 1) and _letter(text, i + 1):
                continue                        # apostrophe inside a word
            curly = STRAIGHT[ch]
            if stack and stack[-1][0] == curly:
                m, p = stack.pop()
                found.append(("straight_close", m + "…" + ch, p))
            elif stack and stack[-1][0] == ch:
                stack.pop()                     # a straight pair: not reported
            elif not _letter(text, i - 1) and _letter(text, i + 1):
                stack.append((ch, i))           # a straight opening
    for m, p in stack:
        if m in OPEN:
            found.append(("unclosed_opening", m, p))
    return sorted(found, key=lambda x: x[2])


def check(art, embedded=None):
    out = []
    for loc, kind, content, items in itertools.chain(
            common.iter_text(art), common.iter_embedded_text(art, embedded)):
        text = common.render(content, items)
        if not any(c in text for c in "‘’“”«»"):
            continue
        for typ, mark, pos in scan(text):
            out.append((loc, typ, mark, common.snippet(text, pos, pos + 1, 25), text))
    return out


def main(argv=None):
    ap = common.parser(__doc__.splitlines()[0], epilog=__doc__)
    common.add_embedded_option(ap)
    a = ap.parse_args(argv)
    embedded = common.embedded_for(a)
    reader = common.Reader(a.input, a.include_unpublished)
    run = common.Run("unmatched_quotes")
    tsv = common.TSV(a.output, HEADER)
    for art in reader:
        for loc, typ, mark, near, ctx in run.guard(art, check, art, embedded) or []:
            tsv.row([common.article_id(art), common.lemma_text(art), loc, typ, mark, near, ctx])
    return run.finish(reader, tsv, extra=embedded.note() if embedded else "")


if __name__ == "__main__":
    sys.exit(main())
