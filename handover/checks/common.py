"""Shared reading and rendering for the ordbokene detection scripts.

Every check in this folder imports this module from its own directory; keep the folder
together. Python 3 standard library only, no network.

Input: article JSON as https://ord.uib.no/bm/article/<id>.json (Bokmålsordboka) or
https://ord.uib.no/nn/article/<id>.json (Nynorskordboka) publishes it, given as
  * a directory of <id>.json files, or
  * a JSONL file with one article per line. A line may also wrap the article as
    {"id": ..., "data": {<article>}}; the wrapper is unwrapped.

Articles whose ``status`` is not 8 (ordbokene's "published"; the API sends it with every
article), or that have no ``status`` at all, are skipped unless --include-unpublished is
given; the count is printed on stderr.

Which dictionary. Every check reads either dictionary; ``--dictionary`` (bm, the default,
or nn) says which one the input is, and so which ordbokene.no page a link points at
(``link``). Check 6 also takes its linking words from it, and check 7 its form sets and
labels; the other checks read both dictionaries the same way. The place vocabulary
("betydning", "eksempel", "uttrykk" ...) is the same in both modes.

Embedded copies of fixed expressions. A fixed expression exists twice: as an article of
its own, and as a copy (an element of ``type_: "sub_article"``) inside each parent
article that lists it. The copies do not always match the expression's own article. The
structural readers here (own_definition_nodes, sense_labels, iter_text, iter_refs) never
enter a copy. The checks that read text or references also visit the copies through
Embedded (below): from each copy they read only the text elements that do not occur in
the expression's own article, and every element of a copy whose expression has no
article in the input (or one that the run skips as unpublished). So a defect is still
reported once, against the article that owns it, and the copies that differ are read
too. Their --no-embedded option turns this off.
"""

import argparse
import io
import json
import os
import re
import sys
import time

PUBLISHED = "8"

#: Placeholder for an item that is not running text (an abbreviation concept, a language,
#: a fraction ...). It is neither a letter nor whitespace, so it splits words and can never
#: form part of a doubled word or a word form.
SEP = "\u2063"


# --- reading -------------------------------------------------------------------

class Reader(object):
    """Iterate articles from a directory or a JSONL file, counting what was skipped."""

    def __init__(self, path, include_unpublished=False):
        self.path = path
        self.include_unpublished = include_unpublished
        self.read = 0
        self.skipped_unpublished = 0
        self.skipped_ids = []
        self.unreadable = []          # (where, reason)

    def _raw(self):
        if os.path.isdir(self.path):
            names = [n for n in os.listdir(self.path) if n.endswith(".json")]

            def key(n):
                stem = n[:-5]
                return (0, int(stem)) if stem.isdigit() else (1, stem)
            for n in sorted(names, key=key):
                p = os.path.join(self.path, n)
                try:
                    with io.open(p, encoding="utf-8") as f:
                        yield n, json.load(f)
                except (ValueError, OSError) as e:
                    self.unreadable.append((n, str(e)))
        else:
            with io.open(self.path, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield "line %d" % i, json.loads(line)
                    except ValueError as e:
                        self.unreadable.append(("line %d" % i, str(e)))

    def __iter__(self):
        for where, obj in self._raw():
            if isinstance(obj, dict) and "body" not in obj and isinstance(obj.get("data"), dict):
                obj = obj["data"]
            if not isinstance(obj, dict) or "body" not in obj:
                self.unreadable.append((where, "not an article (no 'body')"))
                continue
            if not self.include_unpublished and str(obj.get("status")) != PUBLISHED:
                self.skipped_unpublished += 1
                self.skipped_ids.append(obj.get("article_id"))
                continue
            self.read += 1
            yield obj


def article_id(art):
    return art.get("article_id")


def lemma_text(art):
    out = []
    for lem in art.get("lemmas") or []:
        t = lem.get("lemma")
        if t and t not in out:
            out.append(t)
    return ", ".join(out)


DICTIONARIES = ("bm", "nn")

#: The article page on ordbokene.no, by dictionary: Bokmålsordboka with the Bokmål interface,
#: Nynorskordboka with the Nynorsk one (``/nno/nn/7435`` served "bokstavteikn" on 2026-11-13).
LINKS = {"bm": "https://ordbokene.no/nob/bm/%s", "nn": "https://ordbokene.no/nno/nn/%s"}


def link(aid, dictionary="bm"):
    return LINKS[dictionary] % aid


# --- structure -------------------------------------------------------------------

def def_children(node):
    return [e for e in node.get("elements") or [] if e.get("type_") == "definition"]


def has_own_text(node):
    """True when a definition node carries an explanation or an example of its own."""
    return any(e.get("type_") in ("explanation", "example") for e in node.get("elements") or [])


def own_definition_nodes(art):
    """Every definition node of this article, in document order, never entering an
    embedded sub_article."""
    out = []

    def walk(node):
        out.append(node)
        for c in def_children(node):
            walk(c)
    for d in (art.get("body") or {}).get("definitions") or []:
        if d.get("type_", "definition") == "definition":
            walk(d)
    return out


def _is_gloss(node):
    if any(e.get("type_") == "explanation" for e in node.get("elements") or []):
        return True
    return not def_children(node) and any(
        e.get("type_") == "example" for e in node.get("elements") or [])


#: The label sense_labels gives the one top-level sense of an article whose numbered
#: senses are that sense's sub-senses; node_place writes it "overordnet betydning".
TOP = "overordnet"


def _top_senses(nodes):
    """The senses among ``nodes`` and, under any node that is not a sense, its children:
    the senses that sit side by side at one level."""
    senses = []

    def walk(node):
        for c in def_children(node):
            if _is_gloss(c):
                senses.append(c)
            else:
                walk(c)
    for d in nodes:
        if _is_gloss(d):
            senses.append(d)
        else:
            walk(d)
    return senses


def _sub_senses(node):
    """Every sense below ``node``, at any depth, in document order."""
    subs = []

    def rec(n):
        for c in def_children(n):
            if _is_gloss(c):
                subs.append(c)
            rec(c)
    rec(node)
    return subs


def sense_labels(art):
    """Map id(node) -> the sense number as ordbokene numbers it: '2' for the second
    sense, '2.1' for the first sub-sense under it. A node that only holds other
    definitions or fixed expressions has no number of its own.

    When the article has ONE top-level sense and it has sub-senses, ordbokene numbers
    the sub-senses 1, 2, 3 (and theirs 1.1, 1.2 ...), whatever the top sense's own text
    ("Se: $", an empty explanation, or a definition); the top sense itself gets no number
    and is labelled TOP. This is the numbering ordbokene's own references carry
    (``article_ref.definition_order``)."""
    labels = {}
    senses = _top_senses((art.get("body") or {}).get("definitions") or [])
    if len(senses) == 1 and _sub_senses(senses[0]):
        labels[id(senses[0])] = TOP
        senses = _top_senses(def_children(senses[0]))
    for i, s in enumerate(senses, 1):
        labels[id(s)] = str(i)
        for j, sub in enumerate(_sub_senses(s), 1):
            labels.setdefault(id(sub), "%d.%d" % (i, j))
    return labels


def node_place(node, labels):
    """``betydning 1.2 (definisjon id 5)``; ``overordnet betydning (definisjon id 2)`` for
    the unnumbered top sense (TOP); ``definisjon id 3`` for a node with no number."""
    lab = labels.get(id(node))
    if lab == TOP:
        return "overordnet betydning (definisjon id %s)" % node.get("id")
    if lab:
        return "betydning %s (definisjon id %s)" % (lab, node.get("id"))
    return "definisjon id %s" % node.get("id")


# --- text elements ---------------------------------------------------------------

def iter_text(art, etymology=True, examples=True, definitions=True):
    """Yield (location, kind, content, items) for every text element the article owns.

    kind: 'definisjon' (an explanation), 'eksempel' (an example quote),
    'eksempelforklaring' (the explanation attached to an example), 'etymologi',
    'sammensetningsinnledning' (the intro line of a compound list, "som etterledd i ord
    som", at ``<sense>, sammensetninger, innledning``; numbered "sammensetninger 2" only
    in a sense with more than one list). The intro is read with the definitions: it is
    the editors' running text, not an example. Its items (a concept such as "f_eks")
    render as in any other element.
    """
    labels = sense_labels(art)
    for node in own_definition_nodes(art):
        place = node_place(node, labels)
        n_expl = n_ex = n_cl = 0
        many_cl = sum(1 for e in node.get("elements") or []
                      if e.get("type_") == "compound_list") > 1
        for e in node.get("elements") or []:
            t = e.get("type_")
            if t == "explanation":
                n_expl += 1
                if definitions:
                    yield ("%s, forklaring %d" % (place, n_expl), "definisjon",
                           e.get("content"), e.get("items"))
            elif t == "example":
                n_ex += 1
                if not examples:
                    continue
                q = e.get("quote") or {}
                yield ("%s, eksempel %d" % (place, n_ex), "eksempel",
                       q.get("content"), q.get("items"))
                x = e.get("explanation") or {}
                if (x.get("content") or "").strip() or x.get("items"):
                    yield ("%s, eksempel %d, forklaring" % (place, n_ex), "eksempelforklaring",
                           x.get("content"), x.get("items"))
            elif t == "compound_list":
                n_cl += 1
                intro = e.get("intro") or {}
                if definitions and ((intro.get("content") or "").strip() or intro.get("items")):
                    yield ("%s, sammensetninger%s, innledning"
                           % (place, " %d" % n_cl if many_cl else ""),
                           "sammensetningsinnledning", intro.get("content"), intro.get("items"))
    if etymology:
        for i, e in enumerate((art.get("body") or {}).get("etymology") or [], 1):
            yield ("etymologi, ledd %d" % i, "etymologi", e.get("content"), e.get("items"))


def iter_refs(art):
    """Yield (location, item, context) for every article_ref the article owns: in
    definition, example and etymology text, and in compound lists. ``context`` is the
    rendered text of the element the reference stands in."""
    for loc, kind, content, items in iter_text(art):
        ctx = None
        for it in _flat_items(items):
            if it.get("type_") == "article_ref":
                if ctx is None:
                    ctx = render(content, items)
                yield loc, it, ctx
    labels = sense_labels(art)
    for node in own_definition_nodes(art):
        for e in node.get("elements") or []:
            if e.get("type_") == "compound_list":
                for it in e.get("elements") or []:
                    if it.get("type_") == "article_ref":
                        yield ("%s, sammensetninger" % node_place(node, labels), it,
                               "(sammensetningsliste)")


def _flat_items(items):
    for it in items or []:
        if not isinstance(it, dict):
            continue
        yield it
        if it.get("type_") == "quote_inset":
            for sub in _flat_items(it.get("items")):
                yield sub


def ref_face(item):
    if item.get("word_form"):
        return item["word_form"]
    lems = item.get("lemmas") or []
    return (lems[0].get("lemma") if lems else "") or ""


def render_item(item, words):
    t = item.get("type_")
    if t == "article_ref":
        return ref_face(item)
    if t == "usage":
        return item.get("text") or ""
    if t == "quote_inset":
        return render(item.get("content"), item.get("items"), words)
    if t in ("superscript", "subscript"):
        return SEP if words else (item.get("text") or "")
    if t == "fraction":
        return SEP if words else "%s/%s" % (item.get("numerator"), item.get("denominator"))
    if words:
        return SEP
    if item.get("id") is not None:
        return str(item.get("id"))
    return item.get("text") or ""


def render(content, items, words=False):
    """Fill the ``$`` placeholders in ``content`` from ``items``, in order.

    words=False gives readable text (abbreviation concepts shown by their id, e.g. 'jf');
    words=True replaces every non-text item with SEP, for word-level checks. A count
    mismatch between ``$`` and items never raises: surplus placeholders render empty and
    surplus items are dropped (the mismatch itself is not something these checks report).
    """
    content = content or ""
    items = [i for i in (items or []) if isinstance(i, dict)]
    parts = content.split("$")
    out = [parts[0]]
    for k, part in enumerate(parts[1:]):
        out.append(render_item(items[k], words) if k < len(items) else "")
        out.append(part)
    return "".join(out)


# --- output and command line -------------------------------------------------------

def clean(field):
    s = "" if field is None else str(field)
    return s.replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


class TSV(object):
    def __init__(self, path, header):
        self.f = io.open(path, "w", encoding="utf-8", newline="\n") if path else None
        self.out = self.f or io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                              newline="\n", line_buffering=False)
        self.n = 0
        self.row(header, count=False)

    def row(self, fields, count=True):
        self.out.write("\t".join(clean(x) for x in fields) + "\n")
        if count:
            self.n += 1

    def close(self):
        self.out.flush()
        if self.f:
            self.f.close()


def parser(description, epilog=None):
    ap = argparse.ArgumentParser(description=description, epilog=epilog,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="a directory of <id>.json article files, or a JSONL file "
                                  "with one article per line")
    ap.add_argument("-o", "--output", help="write the TSV here (default: standard output)")
    ap.add_argument("--include-unpublished", action="store_true",
                    help="also read articles whose 'status' is not 8 (published)")
    ap.add_argument("--dictionary", choices=DICTIONARIES, default="bm",
                    help="which dictionary the input is: bm (Bokmålsordboka, the default) "
                         "or nn (Nynorskordboka); sets the ordbokene.no links")
    return ap


class Run(object):
    """Bookkeeping shared by every check: timing, per-article errors, the stderr summary."""

    def __init__(self, name):
        self.name = name
        self.t0 = time.time()
        self.errors = []              # (article_id, message)

    def guard(self, art, fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # a crash on one article is reported, never silent
            self.errors.append((article_id(art), "%s: %s" % (type(e).__name__, e)))
            return None

    def finish(self, reader, tsv, extra=""):
        tsv.close()
        sys.stderr.write(
            "%s: %d articles read, %d unpublished skipped, %d unreadable, %d errors, "
            "%d findings, %.1f s%s\n"
            % (self.name, reader.read, reader.skipped_unpublished, len(reader.unreadable),
               len(self.errors), tsv.n, time.time() - self.t0, extra))
        for where, why in reader.unreadable[:20]:
            sys.stderr.write("  unreadable %s: %s\n" % (where, why))
        for aid, msg in self.errors[:50]:
            sys.stderr.write("  ERROR article %s: %s\n" % (aid, msg))
        return 2 if self.errors else 0


def snippet(text, start, end, width=40):
    a = max(0, start - width)
    b = min(len(text), end + width)
    return ("…" if a > 0 else "") + text[a:b] + ("…" if b < len(text) else "")


WORD_RE = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*", re.UNICODE)


# --- embedded copies of fixed expressions -------------------------------------------

def _item_key(it):
    """What the checks read of one item, and nothing else: the target and sense of a
    reference with its face, the text of a usage, the id of a concept. Bookkeeping such
    as ``definition_order``, ``hgno`` or ``markdown_lemma`` is left out, because it
    differs between a copy and its article without changing anything a reader sees."""
    t = it.get("type_")
    if t == "article_ref":
        return (t, it.get("article_id"), it.get("definition_id"), ref_face(it))
    if t == "quote_inset":
        return (t, it.get("content") or "",
                tuple(_item_key(x) for x in it.get("items") or [] if isinstance(x, dict)))
    if t in ("usage", "superscript", "subscript", "fraction"):
        return (t, it.get("text"), it.get("numerator"), it.get("denominator"))
    # an abbreviation or other concept: shown by its id, whatever its type_ (a copy can
    # say "entity" where its article says "relation" for the same "el")
    return ("concept", it.get("id"), it.get("text"))


def element_key(content, items):
    """The identity of one text element for comparing a copy with its article: the exact
    ``content`` string and its items (_item_key). Whitespace is not normalised, so a
    doubled space found only in a copy still counts as a difference. The kind of element
    and its place are left out: a text that the article has anywhere, as an explanation
    or an example, is checked there."""
    return (content or "",
            tuple(_item_key(x) for x in items or [] if isinstance(x, dict)))


def text_keys(art):
    """The element_key of every text element the article owns (iter_text)."""
    return frozenset(element_key(c, i) for _, _, c, i in iter_text(art))


def embedded_copies(art):
    """Every embedded copy (``sub_article`` element) in the article's own definition
    nodes, in document order."""
    out = []
    for node in own_definition_nodes(art):
        for e in node.get("elements") or []:
            if e.get("type_") == "sub_article" and isinstance(e.get("article"), dict):
                out.append(e)
    return out


def copy_lemma(sub):
    """The expression's headword(s) as the copy gives them."""
    return lemma_text(sub["article"]) or ", ".join(
        x for x in sub.get("lemmas") or [] if isinstance(x, str))


def copy_place(art, sub):
    """``artikkel 48613, uttrykk "ringe inn" (133353)``: the start of every place in a
    copy. The sense numbers after it are the copy's own, as its parent shows it."""
    return 'artikkel %s, uttrykk "%s" (%s)' % (article_id(art), copy_lemma(sub),
                                              sub.get("article_id"))


class Embedded(object):
    """The copies' side of a run. Built by reading the input once before the check's own
    pass, with the same choice of statuses, it keeps the text keys of every expression
    article that the input embeds somewhere. ``keys(expr_id)`` is None when the
    expression has no article in this run: all of that copy is then read."""

    def __init__(self, path, include_unpublished=False):
        everything, embedded = {}, set()
        reader = Reader(path, include_unpublished)
        for art in reader:
            try:
                everything[article_id(art)] = text_keys(art)
                embedded.update(s.get("article_id") for s in embedded_copies(art))
            except Exception:        # the check's own pass reports a broken article
                continue
        self._keys = {k: v for k, v in everything.items() if k in embedded}
        self.copies = 0              # copies visited by the check
        self.without_article = 0     # of which the expression has no article in the run
        self.elements = 0            # elements read from copies
        self._words = {}

    def keys(self, expr_id):
        return self._keys.get(expr_id)

    def words(self, expr_id):
        """The lowercased words of the expression's own article (as render(words=True)
        gives them), or None when it has no article in the run. For word-level checks:
        a word that the article has is checked there, even when the copy's element as a
        whole differs."""
        keys = self._keys.get(expr_id)
        if keys is None:
            return None
        if expr_id not in self._words:
            self._words[expr_id] = {w.lower() for k in keys
                                    for w in WORD_RE.findall(_key_words(k))}
        return self._words[expr_id]

    def note(self):
        return ("; embedded copies: %d visited, %d without an article of their own, "
                "%d elements read" % (self.copies, self.without_article, self.elements))


def _key_words(key):
    """render(content, items, words=True), rebuilt from an element_key."""
    content, items = key
    parts = content.split("$")
    out = [parts[0]]
    for k, part in enumerate(parts[1:]):
        it = items[k] if k < len(items) else None
        if it is None:
            s = ""
        elif it[0] == "article_ref":
            s = it[3] or ""
        elif it[0] == "usage":
            s = it[1] or ""
        elif it[0] == "quote_inset":
            s = _key_words((it[1], it[2]))
        else:
            s = SEP
        out.append(s)
        out.append(part)
    return "".join(out)


def iter_embedded_text(art, embedded, etymology=True, examples=True, definitions=True,
                       expression=False):
    """Yield (location, kind, content, items) as iter_text does, for the text elements
    of the article's embedded copies that the expression's own article lacks, or for
    every element of a copy whose expression has no article in the run. The location
    starts with copy_place. ``embedded`` is an Embedded, or None to yield nothing. With
    expression=True each tuple ends with the expression's article id as well."""
    if embedded is None:
        return
    for sub in embedded_copies(art):
        keys = embedded.keys(sub.get("article_id"))
        embedded.copies += 1
        if keys is None:
            embedded.without_article += 1
        place = copy_place(art, sub)
        for loc, kind, content, items in iter_text(sub["article"], etymology, examples,
                                                   definitions):
            if keys is not None and element_key(content, items) in keys:
                continue
            embedded.elements += 1
            if expression:
                yield "%s, %s" % (place, loc), kind, content, items, sub.get("article_id")
            else:
                yield "%s, %s" % (place, loc), kind, content, items


def iter_embedded_refs(art, embedded):
    """Yield (location, item, context) as iter_refs does, for every article_ref in the
    text elements that iter_embedded_text yields. (No copy in the 2026-10-02 data holds a
    compound list.) Visits the copies on its own, so use it OR iter_embedded_text on an
    article, not both, if the counts in Embedded.note matter."""
    for loc, kind, content, items in iter_embedded_text(art, embedded):
        ctx = None
        for it in _flat_items(items):
            if it.get("type_") == "article_ref":
                if ctx is None:
                    ctx = render(content, items)
                yield loc, it, ctx


def add_embedded_option(ap):
    ap.add_argument("--no-embedded", action="store_true",
                    help="do not read the embedded copies of fixed expressions (by "
                         "default, the text in a copy that its expression's own article "
                         "lacks is read, and all of a copy with no such article)")
    return ap


def embedded_for(a):
    """An Embedded for the parsed arguments ``a``, or None under --no-embedded."""
    if getattr(a, "no_embedded", False):
        return None
    return Embedded(a.input, a.include_unpublished)
