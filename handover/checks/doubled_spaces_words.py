#!/usr/bin/env python3
"""Check 3: doubled spaces and doubled words.

Reports, in definition text, example text (the quote and its explanation) and
etymology text:
  double_space   two or more consecutive spaces inside a text string (the ``content``
                 template, a usage text or a reference's word form) — also in the
                 article's own headword (lemma) strings;
  doubled_word   the same word twice in a row with only whitespace between, after the
                 ``$`` placeholders are filled ("del av av byggverk").

A pair whose first word is capitalised and second is not is skipped: that is the shape
of a Latin binomial such as "Crex crex" or "Gorilla gorilla".

A doubled word can be correct Norwegian ("det det gjelder"); every finding is a
candidate for a human to read, not a correction. The word itself is in the ``word``
column, so the output can be counted by word.

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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "word", "context"]

SPACES = re.compile(r"[  ]{2,}")
DOUBLED = re.compile(r"(?<![^\W\d_])([^\W\d_]+)\s+(\1)(?![^\W\d_])", re.IGNORECASE | re.UNICODE)


def _strings(content, items):
    """The stored strings of one text element that the article itself owns."""
    yield content or ""
    for it in common._flat_items(items):
        t = it.get("type_")
        if t == "usage" and it.get("text"):
            yield it["text"]
        elif t == "article_ref" and it.get("word_form"):
            yield it["word_form"]
        elif t == "quote_inset" and it.get("content"):
            yield it["content"]


def check(art, embedded=None):
    out = []
    for i, lem in enumerate(art.get("lemmas") or [], 1):
        t = lem.get("lemma") or ""
        for m in SPACES.finditer(t):
            out.append(("oppslagsord %d" % i, "double_space", "", t))
    for loc, kind, content, items in itertools.chain(
            common.iter_text(art), common.iter_embedded_text(art, embedded)):
        for s in _strings(content, items):
            for m in SPACES.finditer(s):
                out.append((loc, "double_space", "", common.snippet(s, m.start(), m.end())))
        words = common.render(content, items, words=True)
        shown = common.render(content, items)
        for m in DOUBLED.finditer(words):
            if m.group(1)[:1].isupper() and m.group(2)[:1].islower():
                continue            # a Latin tautonym such as "Crex crex"
            out.append((loc, "doubled_word", m.group(1).lower(), shown))
    return out


def main(argv=None):
    ap = common.parser(__doc__.split("\n")[0], epilog=__doc__)
    common.add_embedded_option(ap)
    a = ap.parse_args(argv)
    embedded = common.embedded_for(a)
    reader = common.Reader(a.input, a.include_unpublished)
    run = common.Run("doubled_spaces_words")
    tsv = common.TSV(a.output, HEADER)
    for art in reader:
        for loc, kind, word, ctx in run.guard(art, check, art, embedded) or []:
            tsv.row([common.article_id(art), common.lemma_text(art), loc, kind, word, ctx])
    return run.finish(reader, tsv, extra=embedded.note() if embedded else "")


if __name__ == "__main__":
    sys.exit(main())
