# -*- coding: utf-8 -*-
"""The site's byte savings that change nothing a reader sees (the size report's stages 1 and 2,
`docs/sessions/2026-09-19-ordpar-site-review/evidence/reports/site-size-2026-10-20-contractor.md`;
built 2026-10-20). Pure string work, no I/O:

* `strip_js` / `strip_css` — the published scripts and stylesheets ship without comments
  (decisions 61, Robin 2026-10-20: "the published scripts and stylesheets ship without
  comments", by a small build step of our own, no third-party minifier). Comments only: names,
  line breaks and code stay as written; a `/*!` header goes too. Strings, template literals and
  regular-expression literals are read as such, so a `//` or `/*` inside one is kept.
* `strip_indent` — the indentation at the start of every line (`\\n[ \\t]+` -> `\\n`), the
  report's item 1 (render-checked there; its 1b, the newlines between tags, is not taken).
* `drop_redundant_lang` — a `lang` attribute equal to the one the element inherits is dropped
  (item 8), except on `<html>`, the article fragment's root (`<div class="ordbok …">`) and every
  mini span (`ordbok-xmini`): the page script moves minis, and the search page lifts the
  fragment out of the page.
* `compact_paradigm` — the paradigm island in the compact schema (item 9c): only what
  `inflection.js` reads, each paradigm as a shape id and its forms, the shapes (the paradigm's
  tags, its inflection group and its cells' tag sequence) in one site-wide table that the build
  writes into `inflection.js` (`SHAPES`).
"""
import hashlib
import json
import re

# --------------------------------------------------------------------------- comments

#: A word before a `/` that makes it the start of a regular expression, not a division
_REGEX_AFTER_WORD = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
                     "throw", "case", "do", "else", "yield", "await"}
_WORD = re.compile(r"[A-Za-z0-9_$\u0080-￿]+")

#: Stand-ins for a removed comment while the text is being cleaned up: two private-use
#: characters, refused in a source (`_check`; `inflection.js` holds NUL and U+0001 in strings)
_GONE = ""        # a comment with no line break in it
_GONE_NL = ""     # a block comment that spans lines: it stays a line break (ASI)


class StripError(ValueError):
    pass


def _skip_string(src, i):
    """`src[i]` is a quote: the index just past the closing one."""
    q, n = src[i], len(src)
    i += 1
    while i < n:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if c == q:
            return i + 1
        if c == "\n" and q != "`":
            raise StripError("line break inside a string at %d" % i)
        i += 1
    raise StripError("unterminated string")


def _skip_regex(src, i):
    """`src[i]` is the `/` that opens a regular expression: the index past its flags."""
    n, cls = len(src), False
    i += 1
    while i < n:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if c == "\n":
            raise StripError("line break inside a regular expression at %d" % i)
        if cls:
            if c == "]":
                cls = False
        elif c == "[":
            cls = True
        elif c == "/":
            i += 1
            while i < n and (src[i].isalnum() or src[i] in "_$"):
                i += 1
            return i
        i += 1
    raise StripError("unterminated regular expression")


def _template_part(src, i):
    """Inside a template literal at `i`: the index past its closing backtick (-> (j, False))
    or past a `${` (-> (j, True))."""
    n = len(src)
    while i < n:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if c == "`":
            return i + 1, False
        if c == "$" and src.startswith("${", i):
            return i + 2, True
        i += 1
    raise StripError("unterminated template literal")


def _js_marks(src):
    """`src` with every comment replaced by a stand-in."""
    out, i, n = [], 0, len(src)
    prev = None                 # the last significant token: ("w", word) | ("p", char) | ("v",)
    braces = []                 # "{" or "`" (a template's `${`), innermost last
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            out.append(c)
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(_GONE)
            i = j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                raise StripError("unterminated comment")
            out.append(_GONE_NL if "\n" in src[i:j] else _GONE)
            i = j + 2
            continue
        if c in "'\"":
            j = _skip_string(src, i)
            out.append(src[i:j])
            i, prev = j, ("v",)
            continue
        if c == "`" or (c == "}" and braces and braces[-1] == "`"):
            if c == "}":
                braces.pop()
            j, opened = _template_part(src, i + 1)
            out.append(src[i:j])
            i = j
            if opened:
                braces.append("`")
                prev = ("p", "{")
            else:
                prev = ("v",)
            continue
        if c == "/":
            regex = (prev is None or (prev[0] == "p" and prev[1] not in ")]}")
                     or (prev[0] == "w" and prev[1] in _REGEX_AFTER_WORD))
            if regex:
                j = _skip_regex(src, i)
                out.append(src[i:j])
                i, prev = j, ("v",)
                continue
        m = _WORD.match(src, i)
        if m:
            out.append(m.group(0))
            i, prev = m.end(), ("w", m.group(0))
            continue
        if c in "+-" and src.startswith(c + c, i):
            out.append(c + c)                     # `x++ / 2`: a division follows
            i, prev = i + 2, ("v",)
            continue
        if c == "{":
            braces.append("{")
        elif c == "}" and braces:
            braces.pop()
        out.append(c)
        i, prev = i + 1, ("p", c)
    return "".join(out)


def _css_marks(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                raise StripError("unterminated comment")
            out.append(_GONE_NL if "\n" in src[i:j] else _GONE)
            i = j + 2
            continue
        if c in "'\"":
            j = _skip_string(src, i)
            out.append(src[i:j])
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _check(src):
    if _GONE in src or _GONE_NL in src:
        raise StripError("the source holds U+E000 or U+E001, the stripper's own stand-ins")


def _tidy(marked):
    """Take the stand-ins out: a line left with nothing but a comment goes whole; a comment
    after code takes the spaces before it; one between two words becomes a space, so `a/**/b`
    never joins; one that spanned lines between code stays a line break."""
    lines, out = marked.split("\n"), []
    for line in lines:
        if _GONE not in line and _GONE_NL not in line:
            out.append(line)
            continue
        if not line.replace(_GONE, "").replace(_GONE_NL, "").strip():
            continue                                  # nothing but comment(s)
        parts = re.split("([%s%s])" % (_GONE, _GONE_NL), line)
        text = parts[0]
        for k in range(1, len(parts), 2):
            mark, after = parts[k], parts[k + 1]
            if mark == _GONE_NL and text.strip() and after.strip():
                text = text.rstrip() + "\n" + after.lstrip()
                continue
            if text and after and not text[-1].isspace() and not after[0].isspace():
                text += " "
            text += after
        out.append(text.rstrip())
    return "\n".join(out)


def strip_js(src):
    """A script with its comments removed (and nothing else)."""
    _check(src)
    return _tidy(_js_marks(src))


def strip_css(src):
    """A stylesheet with its comments removed (and nothing else)."""
    _check(src)
    return _tidy(_css_marks(src))


def strip_asset(name, text):
    """`strip_js` or `strip_css` by the file name; anything else as it is."""
    if name.endswith(".js"):
        return strip_js(text)
    if name.endswith(".css"):
        return strip_css(text)
    return text


_HTML_COMMENT = re.compile(r"[ \t]*<!--.*?-->(?:[ \t]*\n)?", re.S)
_SCRIPT_EL = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.S | re.I)
_STYLE_EL = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.S | re.I)


def strip_html(page):
    """A published HTML page without its comments (site decisions 61's leftover, built with 117:
    the shell pages carried their source comments, one naming Robin): every `<!-- … -->`
    outside a script or a style element removed (a line left with nothing but a comment goes
    whole), and the comments of every inline script (`strip_js`) and inline style
    (`strip_css`). A `<script src>` keeps its (empty) body; nothing else changes."""
    out, pos = [], 0
    spans = sorted([(m.start(), m.end(), m, strip_js) for m in _SCRIPT_EL.finditer(page)]
                   + [(m.start(), m.end(), m, strip_css) for m in _STYLE_EL.finditer(page)],
                   key=lambda s: s[0])
    for start, end, m, strip in spans:
        if start < pos:
            continue
        out.append(_HTML_COMMENT.sub("", page[pos:start]))
        body = m.group(2)
        if body.strip():
            body = strip(body)
        out.append(m.group(1) + body + m.group(3))
        pos = end
    out.append(_HTML_COMMENT.sub("", page[pos:]))
    return "".join(out)


def join_js(parts):
    """Several scripts as one, in order, each in its own `try` so that one that throws does not
    stop the rest (as separate `<script>` tags never did); the error is re-thrown on its own, so
    it still reaches the console. Every script here is one IIFE, so the block changes nothing
    else (no top-level declarations, its `'use strict'` inside its function)."""
    out = []
    for p in parts:
        out.append("try{\n%s\n}catch(e){setTimeout(function(){throw e;});}\n" % p.strip("\n"))
    return "".join(out)


def join_css(parts):
    return "\n".join(p.strip("\n") for p in parts) + "\n"


# --------------------------------------------------------------------------- the page

_INDENT = re.compile(r"\n[ \t]+")


def strip_indent(page):
    """Item 1: the indentation of every line. (No page has a `<pre>` or a `white-space: pre`
    rule; the JSON island is one line.)"""
    return _INDENT.sub("\n", page)


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
         "track", "wbr"}
#: An element whose start tag closes an open `<p>` in the HTML parser: the stack below would
#: no longer be the DOM's, so a page with one is left as it is
_CLOSES_P = {"address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset",
             "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
             "header", "hr", "main", "menu", "nav", "ol", "p", "pre", "section", "table", "ul"}
_TOKEN = re.compile(r"<!--.*?-->|<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>",
                    re.S)
_LANG = re.compile(r"""\slang=(?:"([^"]*)"|'([^']*)'|([^\s>]+))""")
_CLASS = re.compile(r"""\sclass="([^"]*)\"""")


#: A child of these keeps its `lang` whatever it inherits: the sheets and the page script select
#: the two lines of a pair BY THE ATTRIBUTE — `.ordpar-pair>span[lang=en]`, `.mini-pair>span[lang=nb]`
#: and their kin (`page.SITE_CSS`, `page.PAGE_JS`); without it the English line loses its smaller
#: muted style (found in the render check, 2026-10-20). `ordpar/tests/test_ordpar_slim.py` fails on any
#: other `[lang` selector the site serves, so a new one cannot slip past this list.
LANG_SELECTED_CHILDREN_OF = ("ordpar-pair", "mini-pair")


def _classes(attrs):
    m = _CLASS.search(attrs)
    return m.group(1).split() if m else []


def _keeps_lang(name, cls, parent_cls):
    if name == "html":
        return True
    if any(c in parent_cls for c in LANG_SELECTED_CHILDREN_OF):
        return True
    return "ordbok-xmini" in cls or (name == "div" and "ordbok" in cls)


def drop_redundant_lang(page):
    """Item 8: every `lang="X"` on an element whose parent's language is already X dropped —
    but never on `<html>`, the fragment's root, a mini span or a line of a pair (`_keeps_lang`).
    -> (page, dropped). A page whose tags do not nest as the parser would read them (an end tag
    that is not the open element's, a block start inside an open `<p>`, a `<li>` inside an open
    `<li>`) comes back unchanged, dropped -1."""
    stack = []                      # (name, lang in force, classes)
    cuts = []                       # (start, end) of the attribute text to remove
    raw = None                      # inside <script> / <style>: the end tag we wait for
    for m in _TOKEN.finditer(page):
        if m.group(0).startswith("<!--"):
            continue
        close, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if raw:
            if close and name == raw:
                raw = None
                if not stack or stack[-1][0] != name:
                    return page, -1
                stack.pop()
            continue
        if close:
            if not stack or stack[-1][0] != name:
                return page, -1
            stack.pop()
            continue
        names = [s[0] for s in stack]
        if (name in _CLOSES_P and "p" in names) or (name == "li" and names and names[-1] == "li"):
            return page, -1
        inherited = stack[-1][1] if stack else None
        cls = _classes(attrs)
        lm = _LANG.search(attrs)
        own = None
        if lm:
            own = next(g for g in lm.groups() if g is not None)
            if own == inherited and not _keeps_lang(name, cls, stack[-1][2] if stack else ()):
                start = m.start(3) + lm.start()
                cuts.append((start, m.start(3) + lm.end()))
        here = own if own is not None else inherited
        if name in _VOID or attrs.rstrip().endswith("/"):
            continue
        stack.append((name, here, cls))
        if name in ("script", "style"):
            raw = name
    if stack:
        return page, -1
    if not cuts:
        return page, 0
    out, last = [], 0
    for a, b in cuts:
        out.append(page[last:a])
        last = b
    out.append(page[last:])
    return "".join(out), len(cuts)


# --------------------------------------------------------------------------- the island

#: Characters of a shape id (base 36) and how many: 55 shapes in the whole dictionary
#: (2026-10-20), so a collision is about 1 in 1,000 per new shape; the build refuses one
SHAPE_ID_LEN = 4
_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def shape_id(shape):
    """A stable id for a shape: from its content alone, so it never depends on which other
    shapes exist (a page's bytes change only when its own paradigm does)."""
    blob = json.dumps(shape, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    n = int.from_bytes(hashlib.sha1(blob).digest()[:8], "big")
    out = ""
    for _ in range(SHAPE_ID_LEN):
        n, r = divmod(n, 36)
        out += _B36[r]
    return out


class ShapeClash(ValueError):
    pass


def compact_paradigm(data, shapes):
    """The mirror row's `data.lemmas` -> the compact island's JSON text, or None when no
    paradigm would render a table (no island then, and no toggle — item 9b). What it keeps is
    what `inflection.js` `readRows` reads (its doc, § 1): each lemma's `lemma`, and of each
    paradigm not withdrawn (`to` unset) its `tags`, `inflection_group` and the cells that have
    both tags and a form, in their order. A lemma with no such paradigm is left out (row order
    and grouping depend on the lemmas' relative order only).

        [[lemma, [shape id, form, form, …], …], …]

    `shapes` (shape id -> [paradigm tags, inflection group, [cell tags joined by "+", …]]) is
    the site-wide table: every shape used is added to it."""
    out = []
    for lem in (data or {}).get("lemmas") or []:
        lem = lem if isinstance(lem, dict) else {}
        pars = []
        for par in lem.get("paradigm_info") or []:
            if not isinstance(par, dict) or par.get("to"):
                continue
            cells = [c for c in par.get("inflection") or []
                     if isinstance(c, dict) and c.get("tags") and c.get("word_form") is not None]
            if not cells:
                continue
            for c in cells:
                if any("+" in t for t in c["tags"]):
                    raise ShapeClash("a cell tag with '+' in it: %r" % (c["tags"],))
            shape = [list(par.get("tags") or []), par.get("inflection_group"),
                     ["+".join(c["tags"]) for c in cells]]
            sid = shape_id(shape)
            if shapes.setdefault(sid, shape) != shape:
                raise ShapeClash("two shapes share the id %s: %r and %r"
                                 % (sid, shapes[sid], shape))
            pars.append([sid] + [c["word_form"] for c in cells])
        if pars:
            out.append([lem.get("lemma")] + pars)
    if not out:
        return None
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    # `</script>` cannot occur inside a JSON island; escaping `<` is the cheap guarantee
    return text.replace("<", "\\u003c")


def shapes_js(shapes):
    """The table as `inflection.js` carries it, sorted by id (so the file is the same for the
    same shapes)."""
    return json.dumps({k: shapes[k] for k in sorted(shapes)}, ensure_ascii=False,
                      separators=(",", ":")).replace("<", "\\u003c")
