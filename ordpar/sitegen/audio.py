# -*- coding: utf-8 -*-
"""The audio's build side (site decisions 159, 2026-11-02): which texts of a page have a clip, the
mark the page carries for each, and the clip names apart from the pages.

**The names.** The build reads ONE names file by a path argument (`build_site.py --audio-names`,
as it takes `--mirror`), written by the private side before a build (`scripts/ordpar_audio_names.py`,
outside `ordpar/`): one line per name, `text TAB d|- TAB *|article id TAB 16 hex|-`. The text is
the page's text stripped and with runs of whitespace collapsed (`norm`); `d` a definition line's
name where it differs from the text's other name; an article id where an article-scoped fix names
the text otherwise in that article; `-` for the name: not uploaded, so no button (`Names.get` has
the order of the lookup). A text the file lacks has no clip: no mark, no button. Nothing here
knows how a clip is named, nor where the clips are.

**The mark** (how the page knows which texts have a clip before it draws a button): the build
writes `data-a` on each voiced element of the page whose text the names file holds — the
headword's main form and each other spelling (each `.ordbok-lemma` of the `h1` but the ", "
between them; site decisions 160, 2026-11-02), and of every later lemma group, a `p.ordpar-hw`
(160's follow-up, 2026-11-03), each set phrase's term
(`.ordbok-expr-term`), each Norwegian definition line (`.ordbok-def`; `data-a="101"` where only
some of its segments, the parts the page joins with ";" and a line break, have a clip: one digit
a segment), each example's quote (an example's first `<span>`). The page script
(`ordpar/site/audio.js`) turns every mark into a play button as the article, a small article
or a looked-up article is drawn — before the width fits, with no request — and finds the clip's
name in the names file of the article's range when a recording is wanted (a press, or a
pointer resting on an icon where the Loading setting allows it; site decisions 170). The marks are
attributes only: no text, so nothing a reader of the page's text sees changes (the description,
the snippets, the copy and share features, search engines).

**The tables' mark** (site decisions 170, Robin 2026-11-06): the inflection tables are drawn in
the browser, so their cells carry no mark; the paradigm island does instead, `data-a-cells` on its
`<script>`: one character a form of the island (`island_forms`, in its order), the bits of
`CELL_CODE.index(char)` saying after which of `FRAMES` (bit 0 bare, 1 "å ", 2 "har ", 3 "en ", 4
"ei ", 5 "et ") the form's text is a key of the article's entry, trailing "0"s dropped; no
attribute where no form has one (`table_code`, read back by `table_keys`). So it holds exactly the
keys the script matched a cell against when it read them from the names file (a cell's ruled text:
each form alone, "ei/en" voiced *ei*, the imperative without its "!"; never the participle table),
and the script draws the tables' icons with no request. Its own attribute, not `data-a`, which
the script turns into a button wherever it stands.

**The names files** (the measurement's (b2), keyed by text): `out/audio/<k>.json`, one per 500
consecutive article ids (`k = (id - 1) // 500`), `{"<id>": {"<text>": "<16 hex>"}}` with a
definition line's key led by a TAB (a page's text is stripped, so no text starts with one). An
article's entry holds the names of the texts its page marks and of every form its tables can draw
(each paradigm form bare and after each frame: å, har, en, ei, et). The offline copy holds none
of them (the clips are not offline either).

The page reading follows the measurement's reader (`evidence/audio-measure/sitetexts.py`, 159's
measurement, 2026-11-01), written again here for the build: the same elements, the hover's peek
and the screen readers' readings dropped from each text.
"""
import gzip
import html
import json
import os
import re

#: The names file's first line, as `scripts/ordpar_audio_names.py` writes it
HEADER = "# ordpar audio names v1"
#: Article ids to a names file
PER = 500
#: The names files' folder under `out/`, and the address the page script fetches
FOLDER = "audio"
#: A definition line's key in a names file: the text led by this (never the start of a text)
DEF = "\t"
#: The frames a table form can be drawn after (inflection.js: en, ei/en, et, å, har; ei/en is
#: voiced ei, the imperative's "!" dropped — the audio session's decisions 17)
FRAMES = ("", "å ", "har ", "en ", "ei ", "et ")
#: The tables' mark (module doc): the island's attribute, and its 64 characters, a form's frame bits
CELLS_ATTR = "data-a-cells"
CELL_CODE = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"

_WS = re.compile(r"\s+")
_WORD = re.compile(r"\w")


def norm(text):
    """The text as a browser shows it: stripped, every run of whitespace one space."""
    return _WS.sub(" ", text or "").strip()


def file_of(aid):
    """The names file an article's names are in: 1-500 -> 0, 501-1000 -> 1, ..."""
    return (int(aid) - 1) // PER


class Names(object):
    """The names file, read once: `get(text, aid, definition)` -> 16 hex or None."""

    def __init__(self, common=None, scoped=None, source=None, header=None):
        self.common = common or {}      # (flag, text) -> hex
        self.scoped = scoped or {}      # (flag, text, aid) -> hex or None
        self.source = source
        self.header = header

    @classmethod
    def read(cls, path):
        common, scoped, header = {}, {}, None
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.rstrip("\n")
                if not line:
                    continue
                if line.startswith("#"):
                    if header is None:
                        header = line
                    continue
                parts = line.split("\t")
                if len(parts) != 4 or parts[1] not in ("d", "-"):
                    raise ValueError("%s:%d: not a names line: %r" % (path, n, line[:80]))
                text, flag, where, name = parts
                if name != "-" and not re.fullmatch(r"[0-9a-f]{16}", name):
                    raise ValueError("%s:%d: not a clip name: %r" % (path, n, name))
                if where == "*":
                    common[(flag, text)] = name
                else:
                    scoped[(flag, text, int(where))] = None if name == "-" else name
        if not header or not header.startswith(HEADER):
            raise ValueError("%s: not an ordpar names file (its first line must start %r)"
                             % (path, HEADER))
        return cls(common, scoped, path, header)

    def __len__(self):
        return len(self.common) + len(self.scoped)

    def get(self, text, aid=None, definition=False):
        """A definition line in article A is looked up as `d A`, then `- A`, then `d *`, then
        `- *`; any other text as `- A`, then `- *` (the exporter writes a `d` line only where a
        definition line's name differs, and an article's line only where its name does). The
        first line found decides; `-` there means no clip."""
        key = norm(text)
        if not key:
            return None
        aid = None if aid is None else int(aid)
        order = ((("d", key, aid), ("-", key, aid)) if definition else (("-", key, aid),))
        for k in order:
            if aid is not None and k in self.scoped:
                return self.scoped[k]
        for k in ((("d", key), ("-", key)) if definition else (("-", key),)):
            if k in self.common:
                name = self.common[k]
                return None if name == "-" else name
        return None


# --- reading a built page (the measurement's reader, for the build) ---------------------------

_TAG = {}


def _tag_re(tag):
    if tag not in _TAG:
        _TAG[tag] = re.compile(r"<(/?)%s\b[^>]*>" % tag)
    return _TAG[tag]


def balanced_end(s, start, tag):
    """The index just past the element of `tag` whose start tag begins at `start`."""
    depth = 0
    for m in _tag_re(tag).finditer(s, start):
        if m.group(0).endswith("/>"):
            continue
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
    return len(s)


def drop_spans(s, cls_pat):
    """`s` with every <span> whose class matches `cls_pat` removed, contents and all."""
    pat = re.compile(r'<span class="[^"]*\b(?:%s)\b[^"]*"[^>]*>' % cls_pat)
    while True:
        m = pat.search(s)
        if not m:
            return s
        s = s[:m.start()] + s[balanced_end(s, m.start(), "span"):]


_ANY_TAG = re.compile(r"<[^>]+>")
_HIDDEN = r"ordbok-xpeek|sr-only|ordpar-visually-hidden"


def visible(fragment):
    """The words a reader sees in an HTML fragment (peeks and hidden readings out)."""
    return html.unescape(_ANY_TAG.sub("", drop_spans(fragment, _HIDDEN)))


def inner(s, m, tag):
    """The inner HTML of the element whose start tag is match `m`."""
    end = balanced_end(s, m.start(), tag)
    close = s.rfind("</%s" % tag, m.end(), end)
    return s[m.end():close if close >= 0 else end]


_ARTICLE = re.compile(r'<div class="ordbok ordpar-article"[^>]*>')
_HW = re.compile(r'<(h1|p) class="ordpar-hw"[^>]*>')
_LEMMA = re.compile(r'<span class="ordbok-lemma">')
_DEF = re.compile(r'<span class="ordbok-def"(?: lang="nb")?>')
_COMP = re.compile(r'<div class="ordbok-sub ordpar-comp">')
_UNTR = re.compile(r'<div class="ordpar-untr"')
_LI = re.compile(r'<li><span(?: lang="nb")?>')
_EXPR = re.compile(r'<div class="ordbok-expr">')
_EXPR_ID = re.compile(r'\bid="x(\d+)-')
_TERM = re.compile(r'<span class="ordbok-expr-term"(?: lang="nb")?>')
_ISLAND = re.compile(r'<script type="application/json" id="ordpar-paradigm">(.*?)</script>', re.S)
_BR = re.compile(r";<br>")


def island_forms(island_text):
    """Every word form of a compact paradigm island (`slim.compact_paradigm`), in order, once."""
    try:
        data = json.loads(island_text)
    except ValueError:
        return []
    seen, out = set(), []
    for lem in data if isinstance(data, list) else []:
        for par in (lem[1:] if isinstance(lem, list) else []):
            for f in (par[1:] if isinstance(par, list) else []):
                if isinstance(f, str) and f.strip() and f not in seen:
                    seen.add(f)
                    out.append(f)
    return out


def table_code(forms, keys):
    """The tables' mark (module doc) for the island's `forms` (`island_forms`) and the article's
    entry `keys`: one character a form, trailing "0"s dropped; "" where no form is a key."""
    out = []
    for f in forms:
        v = 0
        for i, frame in enumerate(FRAMES):
            if norm(frame + f) in keys:
                v |= 1 << i
        out.append(CELL_CODE[v])
    return "".join(out).rstrip("0")


def table_keys(forms, code):
    """The keys the tables' mark `code` names for the island's `forms` (as `audio.js` reads it)."""
    keys = set()
    for f, c in zip(forms, code or ""):
        v = CELL_CODE.find(c)
        for i, frame in enumerate(FRAMES):
            if v > 0 and v >> i & 1:
                keys.add(norm(frame + f))
    return keys


def mark(page, aid, names, expr_ids=None):
    """The page with a `data-a` mark on each voiced element whose text has a clip (module doc),
    and the article's names-file entry `{key: hex}`. `expr_ids`: `{term: id}` for the page's set
    phrases (a block's id is read from its own `x<id>-` anchors first), so a set phrase's texts are
    named as that article's — an article-scoped fix is the only difference it makes.
    -> (page, entry, counts)."""
    counts = {"head": 0, "spellings": 0, "groups": 0, "expr": 0, "def": 0, "def_lines": 0, "ex": 0, "cell_names": 0,
              "tables": 0, "table_forms": 0, "missing": 0, "collisions": 0}
    a = _ARTICLE.search(page)
    if not a or names is None:
        return page, {}, counts
    a0 = a.start()
    art = page[a0:balanced_end(page, a0, "div")]
    inserts = []                 # (offset in art of a start tag's ">", the attribute)
    entry = {}
    expr_ids = expr_ids or {}

    def put(key, name, definition):
        k = (DEF if definition else "") + norm(key)
        if k in entry and entry[k] != name:
            counts["collisions"] += 1
            return
        entry[k] = name

    # the set phrases' blocks, each named with its own id
    blocks = []
    for m in _EXPR.finditer(art):
        end = balanced_end(art, m.start(), "div")
        block = art[m.start():end]
        im = _EXPR_ID.search(block)
        eid = int(im.group(1)) if im else None
        if eid is None:
            tm = _TERM.search(block)
            eid = expr_ids.get(norm(visible(inner(block, tm, "span")))) if tm else None
        blocks.append((m.start(), end, eid or aid))

    def owner(pos):
        for s, e, eid in blocks:
            if s <= pos < e:
                return eid
        return aid

    # the headword: its main form and each other spelling (site decisions 160); the ", " between
    # them is a `.ordbok-lemma` of its own (`ordbok_gen._head_lemmas`), passed over. Every lemma
    # group of the head, not only the `h1`: a group with its own word class is a `p.ordpar-hw`
    # after it (`article.py` `head_html`; *forutanelse* / *forutaning* 17213), its spellings
    # counted as `groups` (160's follow-up, 2026-11-03)
    first = True
    for g, h in enumerate(_HW.finditer(art)):
        hs = h.end()
        he = balanced_end(art, h.start(), h.group(1))
        for lm in _LEMMA.finditer(art, hs, he):
            text = visible(inner(art, lm, "span"))
            if not _WORD.search(text):
                continue
            name = names.get(text, aid)
            if name:
                inserts.append((lm.end() - 1, " data-a"))
                put(text, name, False)
                counts["head" if first else "groups" if g else "spellings"] += 1
            elif norm(text):
                counts["missing"] += 1
            first = False
    # the set phrases' terms
    for m in _TERM.finditer(art):
        text = visible(inner(art, m, "span"))
        name = names.get(text, owner(m.start()))
        if name:
            inserts.append((m.end() - 1, " data-a"))
            put(text, name, False)
            counts["expr"] += 1
        elif norm(text):
            counts["missing"] += 1
    # the definition lines: not a compound list's; on a translated page (root lang="en") a line
    # with no lang of its own is English (`slim.drop_redundant_lang`), unless it sits in the
    # untranslated set phrases' `ordpar-untr` (lang="nb")
    comp = [(m.start(), balanced_end(art, m.start(), "div")) for m in _COMP.finditer(art)]
    untr = [(m.start(), balanced_end(art, m.start(), "div")) for m in _UNTR.finditer(art)]
    root_en = ' lang="en"' in art[:80]
    for m in _DEF.finditer(art):
        if any(s <= m.start() < e for s, e in comp):
            continue
        if root_en and 'lang="nb"' not in m.group(0) and not any(s <= m.start() < e for s, e in untr):
            continue
        segs = _BR.split(drop_spans(inner(art, m, "span"), _HIDDEN))
        who, bits = owner(m.start()), ""
        for seg in segs:
            text = visible(seg)
            name = names.get(text, who, definition=True)
            if name:
                put(text, name, True)
                counts["def"] += 1
            elif norm(text):
                counts["missing"] += 1
            bits += "1" if name else "0"
        if "1" in bits:
            inserts.append((m.end() - 1, " data-a" if "0" not in bits else ' data-a="%s"' % bits))
            counts["def_lines"] += 1
    # the examples: the quote alone, without its explanation
    for m in _LI.finditer(art):
        quote = drop_spans(inner(art, m, "span"), r"ordbok-exexpl")
        text = visible(quote)
        name = names.get(text, owner(m.start()))
        if name:
            inserts.append((m.end() - 1, " data-a"))
            put(text, name, False)
            counts["ex"] += 1
        elif norm(text):
            counts["missing"] += 1
    # the inflection tables' forms, drawn in the browser: every form bare and after each frame
    isl = _ISLAND.search(art)
    if isl:
        forms = island_forms(isl.group(1))
        for f in forms:
            for frame in FRAMES:
                text = frame + f
                name = names.get(text, aid)
                if name and norm(text) not in entry:
                    entry[norm(text)] = name
                    counts["cell_names"] += 1
        # the tables' mark (site decisions 170): which of those keys the entry holds, from any
        # source, as the script matched a cell against the whole entry
        code = table_code(forms, entry)
        if code:
            inserts.append((isl.start(1) - 1, ' %s="%s"' % (CELLS_ATTR, code)))
            counts["tables"] += 1
            counts["table_forms"] += sum(1 for c in code if c != "0")
    if not inserts:
        return page, entry, counts
    out, last = [], 0
    for pos, attr in sorted(inserts):
        out.append(art[last:pos])
        out.append(attr)
        last = pos
    out.append(art[last:])
    new_art = "".join(out)
    return page[:a0] + new_art + page[a0 + len(art):], entry, counts


# --- the names files ------------------------------------------------------------------------

def _dump(d):
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def write_files(out, entries, replace):
    """Write `out/audio/<k>.json` from `entries` (`{aid: {key: hex}}`; an empty entry removes the
    article). `replace` (a whole build): every file is written afresh and one no article fills
    is removed; otherwise (`--ids`, `--limit`) each file touched is read and only the built
    articles' entries change. -> {"files", "bytes", "gzip", "articles", "names"}."""
    folder = os.path.join(out, FOLDER)
    groups = {}
    for aid, e in entries.items():
        groups.setdefault(file_of(aid), {})[str(aid)] = e
    os.makedirs(folder, exist_ok=True)
    if replace:
        for n in os.listdir(folder):
            if re.fullmatch(r"\d+\.json", n) and int(n[:-5]) not in groups:
                os.remove(os.path.join(folder, n))
    for k, got in groups.items():
        path = os.path.join(folder, "%d.json" % k)
        have = {}
        if not replace and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    have = json.load(f)
            except ValueError:
                have = {}
        have.update(got)
        have = {i: e for i, e in have.items() if e}
        if have:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(_dump(have))
        elif os.path.exists(path):
            os.remove(path)
    return measure_files(out)


def measure_files(out):
    """The names files' count and size as they stand in `out/audio/`."""
    folder = os.path.join(out, FOLDER)
    files = raw = gz = arts = n = 0
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if not re.fullmatch(r"\d+\.json", name):
                continue
            with open(os.path.join(folder, name), "rb") as f:
                blob = f.read()
            files += 1
            raw += len(blob)
            gz += len(gzip.compress(blob, 9, mtime=0))
            d = json.loads(blob.decode("utf-8"))
            arts += len(d)
            n += sum(len(e) for e in d.values())
    return {"files": files, "bytes": raw, "gzip": gz, "articles": arts, "names": n}
