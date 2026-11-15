"""The editions of ordpar/docs/divergences.md for readers outside the project (site decisions
184). Moved here from the site review's walk-through folder on 2026-11-12, so that the public
export does not depend on a session folder.

    python ordpar/divergences_print.py <divergences.md> <out.md>            # the print edition
    python ordpar/divergences_print.py --public <divergences.md> <out.md>   # the repository's

Since the rewrite of 2026-11-11 the record keeps every decision reference in its last table
column (Decision) and in the closing section headed "## For the project's own record"; the text
above that heading names no decision. Both editions:

- cut everything from "## For the project's own record" on (the reference-link block included);
- keep the rest above that heading as written, the section "What ordbokene.no has that Ordpar
  lacks" included (a list after the tables, added 2026-11-12; of use to the editors, so in the
  print edition too; it names no decision, and a reference in it stops either edition);
- sort each table's rows by the verdict cell, "**Yes.**", then "**Maybe.**", then "**No…"
  (Robin, 2026-11-11: "put the "Of use to ordbokene?" → "yes", at the top of each table"; the
  record keeps its order), the record's order kept inside each group.

**The print edition** (the PDF for ordbokene's editors; Robin, 2026-11-11: "the "decision"
references are not useful for the ordbøkene editors") also cuts the Decision column, the sixth of
six, and the key's row that describes it.

**The public edition** (`--public`, the repository's `docs/divergences.md`; decisions 184)
keeps the Decision column, each number a link to the public decision log's entry,
`decisions.md#dN` beside it in the repository's `docs/`; the key's row names that log. A
reference to an entry the public log does not have (`<a id="dN"></a>` in ordpar/public/docs/
decisions.md, or docs/decisions.md in the public repository: an entry cut from it on purpose)
would be a dead link there, so it is left out of its cell, with the words before it and its
parenthesis of dates (`known_refs`), and named on stderr (`left out of the public edition: 122
(row "Addresses")`); a cell that would be left with no reference stops the script, naming the
row. The print edition does not read the log.

**The "How it works" column** (decisions 184, Robin 2026-11-13: "linking to the relevant sections
in the tecnical docs"): a seventh column after Decision, each cell a link (at most two, joined by
"; ") to the section of the site's technical docs, or of a README, that describes the feature as
built; empty where no doc does yet. Its links are relative to the record's own folder,
ordpar/docs/, whatever path the record is read from. The print edition cuts the column and the
key's row for it. The public edition puts it before the Decision column (… Of use to ordbokene? |
How it works | Decision), with its own key row (`PUBLIC_HOW_KEY`) before the Decision's, and each
link rewritten to resolve from the public repository's `docs/`: a file under ordpar/ keeps its
path (`../ordpar/docs/<file>.md`), a public text under ordpar/public/ goes to its exported path
(ordpar/public/data/README.md is `../data/README.md`). A table of six columns is read as before.

Every link in the column is checked, for both editions: the file must exist and the anchor must be
one a heading of that file makes, by GitHub's rule (`anchor`: the code spans' backticks and the
links' targets taken off, lower case, every character that is not a letter, a digit, a space, a
hyphen or an underscore dropped, each space a hyphen; a repeated heading `-1`, `-2` …;
`heading_anchors` reads a file's ATX headings outside fenced code). A link with no anchor is
refused too: the column names a section, not a file.

It stops with a message, rather than print something wrong, if the closing heading is missing,
if a verdict cell opens with none of the five verdicts, if a row points at a neighbour by its
place ("next row", "the row above": the sort may have moved the neighbour; the record names the
row instead), if a "How it works" link names a file that does not exist or an anchor no heading
of it makes, or if a decision reference is left anywhere in what it would print (the print
edition), or one that is not a link to the public log (the public edition).
"""
import io
import os
import posixpath
import re
import sys

PIPE = re.compile(r"(?<!\\)\|")
RECORD = "\n## For the project's own record\n"
VERDICTS = ("**Yes.**", "**Maybe.**", "**No: translation site.**", "**No: static site.**", "**No.**")
REFERENCES = [
    r"\[\d+[a-z]?\]\[d\d+[a-z]?\]",          # [59][d59]
    r"\[d\d+[a-z]?\]",                       # a bare [d59]
    r"dictionary-site-decisions",            # the decisions file by name
    r"#d\d+\b",                              # an anchor into it
    r"\bdecisions? \d+",                     # "decisions 126"
    r"\bsite decisions\b",
]
#: the public log, relative to the public edition (both in the repository's docs/)
PUBLIC_LOG = "decisions.md"
REF_LINK = re.compile(r"\[(\d+[a-z]?)\]\[d(\d+[a-z]?)\]")
#: the key's row for the Decision column, as the public edition words it
PUBLIC_KEY = ("| Decision | the project's record: the entry or entries in [the decision log](%s) behind "
              "the row, with their dates |" % PUBLIC_LOG)
#: the column of links to the technical docs, and the key's row for it in the public edition
HOW = "How it works"
PUBLIC_HOW_KEY = ("| How it works | the section of the technical docs that describes the feature as built; "
                  "empty where none does yet |")
#: the record's folder, which its links are relative to (the record is ordpar/docs/divergences.md)
HERE = os.path.dirname(os.path.abspath(__file__))
RECORD_DIR = os.path.join(HERE, "docs")
#: the repository root, and where the public texts sit in it (each exported without the prefix)
ROOT = os.path.dirname(HERE)
PUBLIC_TEXTS = "ordpar/public/"
#: the public edition's folder in the public repository
PUBLIC_DIR = "docs"
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def anchor(heading):
    """The anchor GitHub makes for a heading's text (before the -1, -2 of a repeat): the inline
    markup taken off (a code span's backticks, a link's target), lower case, every character that
    is not a letter, a digit, a space, a hyphen or an underscore dropped, each space a hyphen.
    ``"4. The query algorithms (`lookup.js`)"`` gives ``"4-the-query-algorithms-lookupjs"``."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading.strip())
    text = text.replace("`", "").lower()
    return "".join(ch for ch in text if ch.isalnum() or ch in " -_").replace(" ", "-")


def heading_anchors(markdown):
    """Every anchor the ATX headings of a Markdown text make (one to six ``#`` and a space, at most
    three spaces in; a closing run of ``#`` dropped), outside fenced code; a repeated anchor takes
    ``-1``, ``-2`` … in the order met. Setext headings are not read: the site's docs have none."""
    seen, out, fence = {}, set(), None
    for line in markdown.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        m = re.match(r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?[ \t]*$", line)
        if not m:
            continue
        text = re.sub(r"(?:^|[ \t]+)#+[ \t]*$", "", m.group(1) or "")
        base = anchor(text)
        n = seen.get(base, 0)
        out.add(base if n == 0 else "%s-%d" % (base, n))
        seen[base] = n + 1
    return out


_ANCHORS = {}


def check_link(target, base=None):
    """None where ``target`` (relative to ``base``, by default the record's folder) names a file
    there is and an anchor a heading of it makes; else what is wrong."""
    path, sep, frag = target.partition("#")
    full = os.path.normpath(os.path.join(base or RECORD_DIR, path))
    if not path or not os.path.isfile(full):
        return "no such file: %s" % target
    if not frag:
        return "no section named: %s" % target
    if full not in _ANCHORS:
        _ANCHORS[full] = heading_anchors(io.open(full, encoding="utf-8").read())
    if frag not in _ANCHORS[full]:
        return "no heading makes the anchor: %s" % target
    return None


def check_how(cell, base=None):
    """What is wrong with the links of one "How it works" cell."""
    return [f for f in (check_link(m.group(2), base) for m in MD_LINK.finditer(cell)) if f]


def public_target(target, base=None):
    """A record link as it resolves from the public edition, in the public repository's `docs/`: a
    file under ordpar/public/ at its exported path, any other file at its own path."""
    path, sep, frag = target.partition("#")
    full = os.path.normpath(os.path.join(base or RECORD_DIR, path))
    rel = os.path.relpath(full, ROOT).replace("\\", "/")
    if rel.startswith(PUBLIC_TEXTS):
        rel = rel[len(PUBLIC_TEXTS):]
    return posixpath.relpath(rel, PUBLIC_DIR) + sep + frag


def public_how(cell, base=None):
    """A "How it works" cell with each link rewritten by `public_target`."""
    return MD_LINK.sub(lambda m: "[%s](%s)" % (m.group(1), public_target(m.group(2), base)), cell)


def cells(line):
    return PIPE.split(line.strip()[1:-1])


def rank(verdict):
    """Where a row goes by its "Of use to ordbokene?" cell: yes, then maybe, then the no's."""
    v = verdict.strip()
    if not v.startswith(VERDICTS):
        sys.exit("divergences.md: a verdict cell opens with none of the five verdicts: %r" % v[:60])
    return 0 if v.startswith("**Yes.**") else 1 if v.startswith("**Maybe.**") else 2


def tables(text, public=False, base=None):
    """Each six- or seven-column table with its rows sorted yes, maybe, no; without its Decision
    and "How it works" columns unless ``public``, which puts "How it works" before Decision and
    rewrites its links. Every "How it works" link is checked first (`check_how`)."""
    lines = text.split("\n")
    out, i = [], 0
    ids = None
    if public:
        log = public_log(base)
        if log is None:
            sys.exit("divergences.md: the public log (ordpar/public/docs/%s, or docs/%s in the public "
                     "repository) was not found" % (PUBLIC_LOG, PUBLIC_LOG))
        ids = public_ids(log)
    while i < len(lines):
        line = lines[i]
        if line.startswith("|") and len(cells(line)) in (6, 7) and i + 1 < len(lines) \
                and set(lines[i + 1]) <= set("|-: "):
            head = cells(line)
            n = len(head)
            if head[5].strip() != "Decision" or (n == 7 and head[6].strip() != HOW):
                sys.exit("divergences.md: a %d-column table whose last columns are not Decision%s: %r"
                         % (n, ", " + HOW if n == 7 else "", line[:80]))
            order = [0, 1, 2, 3, 4] + (([6, 5] if n == 7 else [5]) if public else [])
            rule = cells(lines[i + 1])
            out += ["|" + "|".join(head[k] for k in order) + "|", "|" + "|".join(rule[k] for k in order) + "|"]
            j = i + 2
            rows, faults = [], []
            while j < len(lines) and lines[j].startswith("|"):
                r = cells(lines[j])
                if len(r) != n:
                    sys.exit("divergences.md: a table row without %d cells: %r" % (n, lines[j][:80]))
                if n == 7:
                    faults += ["%s: %s" % (r[0].strip(), f) for f in check_how(r[6], base)]
                    if public:
                        r[6] = public_how(r[6], base)
                if public:
                    r[5] = known_refs(r[5], ids, r[0].strip())
                rows.append([r[k] for k in order])
                j += 1
            if faults:
                sys.exit('divergences.md: a "How it works" link does not land on a heading:\n  '
                         + "\n  ".join(faults))
            rows.sort(key=lambda r: rank(r[4]))
            out += ["|" + "|".join(r) + "|" for r in rows]
            i = j
        elif line.startswith("| Decision |"):
            if public:
                if i + 1 < len(lines) and lines[i + 1].startswith("| %s |" % HOW):
                    out.append(PUBLIC_HOW_KEY)       # the new column comes before Decision
                    i += 1
                out.append(PUBLIC_KEY)
            i += 1          # the key's rows for the columns just cut, or reworded
        elif line.startswith("| %s |" % HOW):
            if public:
                out.append(PUBLIC_HOW_KEY)
            i += 1
        else:
            out.append(line)
            i += 1
    return "\n".join(out)


LOG_ANCHOR = re.compile(r'<a id="d(\d+[a-z]?)"></a>')


def public_log(base=None):
    """The public log's file in this checkout, found as the "How it works" files are, from the
    record's folder (``base``, by default ordpar/docs/): ordpar/public/docs/decisions.md in the
    private repository, else at its exported path, docs/decisions.md, as in the public one; None
    where neither is."""
    root = os.path.normpath(os.path.join(base or RECORD_DIR, os.pardir, os.pardir))
    for path in (os.path.join(root, PUBLIC_TEXTS, PUBLIC_DIR, PUBLIC_LOG),
                 os.path.join(root, PUBLIC_DIR, PUBLIC_LOG)):
        if os.path.isfile(path):
            return path
    return None


def public_ids(path):
    """The entry numbers of the public log, each as its ``<a id="dN"></a>`` writes it."""
    with io.open(path, encoding="utf-8") as fh:
        return set(LOG_ANCHOR.findall(fh.read()))


def _split_top(s, sep):
    """``s`` split at each ``sep`` outside parentheses."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(s):
        ch = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if depth == 0 and s.startswith(sep, i):
            parts.append("".join(cur))
            cur, i = [], i + len(sep)
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def known_refs(cell, ids, row):
    """A Decision cell with each reference to an entry not in ``ids`` left out, each one so left
    out printed to stderr. A cell lists its references joined by "; ", each with words before it
    ("the stacked step [108][d108]") and its parenthesis of dates after it, or several joined by
    ", " sharing one parenthesis ("[88][d88], [89][d89] (2026-10-22)"). A reference left out takes
    its words and its parenthesis with it; one of several sharing a parenthesis leaves the
    parenthesis to the others. Stops, naming the row, when no reference would be left."""
    lead = cell[:len(cell) - len(cell.lstrip())]
    trail = cell[len(cell.rstrip()):]
    kept = []
    for part in _split_top(cell.strip(), "; "):
        refs = REF_LINK.findall(part)
        gone = [n for _t, n in refs if n not in ids]
        for n in gone:
            sys.stderr.write('left out of the public edition: %s (row "%s")\n' % (n, row))
        if not gone:
            kept.append(part)
        elif len(gone) < len(refs):
            for n in gone:
                part = re.sub(r"\[\d+[a-z]?\]\[d%s\], |, \[\d+[a-z]?\]\[d%s\](?= \(|$)" % (n, n), "", part, count=1)
            kept.append(part)
    if not any(REF_LINK.search(p) for p in kept):
        sys.exit('divergences.md: row "%s" would be left with no decision the public log has '
                 '(%s)' % (row, cell.strip()))
    return lead + "; ".join(kept) + trail


def public_links(s):
    """Every ``[59][d59]`` as ``[59](decisions.md#d59)``."""
    return REF_LINK.sub(lambda m: "[%s](%s#d%s)" % (m.group(1), PUBLIC_LOG, m.group(2)), s)


def check_public(s):
    """What the public edition may not keep: a reference that is not a link into the public log
    (the links themselves are taken out first, then the print edition's patterns looked for)."""
    rest = re.sub(r"\]\(%s#d\d+[a-z]?\)" % re.escape(PUBLIC_LOG), "]", s)
    return list(dict.fromkeys(m for pat in REFERENCES for m in re.findall(r".{0,40}%s.{0,20}" % pat, rest)))


def edition(text, public=False, base=None):
    """The edition's text from the record's text; ``base`` is the folder its "How it works" links
    are relative to, by default the record's own (ordpar/docs/)."""
    s = text.replace("\r\n", "\n")
    head, sep, _tail = s.partition(RECORD)
    if not sep:
        sys.exit("divergences.md: the heading %r was not found" % RECORD.strip())
    s = tables(head.rstrip("\n") + "\n", public=public, base=base)
    left = re.findall(r".{0,50}(?:next row|previous row|row above|rows above|row below|rows below).{0,20}", s, re.I)
    if left:
        sys.exit("divergences.md: a row still points at a neighbour by its place:\n  " + "\n  ".join(left))
    if public:
        s = public_links(s)
        left = check_public(s)
        if left:
            sys.exit("divergences.md: a decision reference is not a link into the public log:\n  "
                     + "\n  ".join(left))
    else:
        left = list(dict.fromkeys(m for pat in REFERENCES for m in re.findall(r".{0,40}%s.{0,20}" % pat, s)))
        if left:
            sys.exit("divergences.md: a decision reference is left in the print edition:\n  " + "\n  ".join(left))
    return s


def main(src, dst, public=False):
    s = edition(io.open(src, encoding="utf-8").read(), public=public)
    io.open(dst, "w", encoding="utf-8", newline="\n").write(s)


if __name__ == "__main__":
    args = sys.argv[1:]
    public = "--public" in args
    args = [a for a in args if a != "--public"]
    if len(args) != 2 or any(a in ("-h", "--help") for a in args):
        print(__doc__)
        sys.exit(0 if any(a in ("-h", "--help") for a in sys.argv[1:]) else 2)
    main(args[0], args[1], public=public)
