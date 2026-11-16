# -*- coding: utf-8 -*-
"""The CEFR level box (site decisions 187): the levels file, read once, and the box's markup.

**The file** (`ordpar/levels.tsv`, written by `ordpar/levels_import.py`, read by `build_site.py`
`--levels`): a first line naming its source, then the header `article<TAB>shown`, then one line
per article id, sorted by id, LF line ends. `shown` is the level the site draws: A1, A2, B1, B2,
or C for C1 and C2 together (decisions 187). A set phrase embedded in an article is looked up by
its own article id. An article the file lacks gets no box.

**The box** (`box_html`): the style lab's "Quiet box", the same after the headword and on each
embedded set phrase's line:

    <span class="ordpar-level" data-level="B1" lang="en" data-nosnippet><span class="ordpar-level-txt"
    aria-hidden="true" title="B1 · intermediate">B1</span><span class="sr-only" data-nosnippet>, level B1</span></span>

The visible letters are real text, hidden from screen readers with their tooltip; a screen reader
hears ", level B1" once, from the visually hidden span (`sr-only`, the class the homograph's
reading uses in the same heading). `lang="en"`: the words are English inside a Norwegian heading.
`data-nosnippet`: search engines leave the box out of their snippets, as the homograph's reading
(decisions 154); on the hidden reading too, as on every hidden label the build writes. The sheet
hides the box unless `<html>` carries `ordpar-levels-on`, which the head script sets before the
first paint while the setting `levels` is on (`head.py` `THEME_JS`), so a page carries the box
always and nothing moves on load.
"""
import html
import os

#: The levels the site draws, in order
SHOWN = ("A1", "A2", "B1", "B2", "C")
#: The file's header line (after its comment line)
HEADER = "article\tshown"
#: The file the build reads by default
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "levels.tsv")


class Refused(ValueError):
    pass


def read(path=PATH):
    """`{article id: shown}` from a levels file; refuses a level outside `SHOWN`, a duplicate id,
    a line that is not two columns, or a file without the header."""
    out, header = {}, False
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            if not header:
                if line != HEADER:
                    raise Refused("%s:%d: not a levels file (its header must be %r)" % (path, n, HEADER))
                header = True
                continue
            parts = line.split("\t")
            if len(parts) != 2 or not parts[0].isdigit():
                raise Refused("%s:%d: not a levels line: %r" % (path, n, line[:80]))
            aid, shown = int(parts[0]), parts[1]
            if shown not in SHOWN:
                raise Refused("%s:%d: level %r is not one of %s" % (path, n, shown, ", ".join(SHOWN)))
            if aid in out:
                raise Refused("%s:%d: article %d twice" % (path, n, aid))
            out[aid] = shown
    if not header:
        raise Refused("%s: not a levels file (no header %r)" % (path, HEADER))
    return out


def box_html(shown, strings):
    """The box for one level (module doc); "" for none. Its words are the strings'
    (`level_tip_<level>`, `level`)."""
    if not shown:
        return ""
    lv = html.escape(shown, quote=True)
    tip = html.escape(strings["level_tip_" + shown.lower()], quote=True)
    said = html.escape(strings["level"].format(level=shown), quote=False)
    return ('<span class="ordpar-level" data-level="%s" lang="en" data-nosnippet>'
            '<span class="ordpar-level-txt" aria-hidden="true" title="%s">%s</span>'
            '<span class="sr-only" data-nosnippet>, %s</span></span>' % (lv, tip, lv, said))
