#!/usr/bin/env python3
"""Check 7: words in definitions and examples that are not a word form of the dictionary's language.

CANDIDATES FOR A HUMAN TO READ, NOT ERRORS. Most findings are correct words that
simply have no article of their own (compounds, rare derivations, foreign words in
examples); the defects are among them, mostly near the top of the ranking.

TWO MODES. By default the input is Bokmålsordboka and the other dictionary is Nynorsk;
with --dictionary nn the input is Nynorskordboka and the other dictionary is Bokmål.
Below, "the input's language" is Bokmål in the first mode and Nynorsk in the second.

The check collects every word form the input dictionary itself lists (the headwords
and ``lemmas[].paradigm_info[].inflection[].word_form`` of every article in the input)
and, given the other dictionary's articles (--nynorsk in Bokmål mode, --bokmal in
Nynorsk mode), every form in that dictionary the same way. Full-form lists can be added
on top with --bokmal-forms and --nynorsk-forms, each to its own language's set whatever
the mode: Norsk ordbank's ``fullformsliste.txt`` (Bokmål) and ``fullformer_2012.txt``
(Nynorsk), from Språkbanken at the National Library (CC BY), list inflected forms for
far more words than the dictionaries' headwords, compounds and derivations included,
and cut the false positives sharply. A plain UTF-8 file with one form per line also
works. It then reads every word of the input's definition text and example text (never
etymology, which quotes Old Norse and other languages):
  nynorsk_form   (Bokmål mode) the word is a Nynorsk form and not a Bokmål form
                 ("nøytronar");
  bokmal_form    (Nynorsk mode) the word is a Bokmål form and not a Nynorsk form
                 ("begrensa", "bedre");
  unknown_form   the word is neither ("laserstråle" misspelt "lasestråle").
Every rule below that speaks of "a Bokmål form" means a form of the input's language
in Nynorsk mode.

Embedded fixed expressions. An embedded copy of a fixed expression (sub_article) is
read only for the text elements that the expression's own article lacks, or in full
when the expression has no article in the input (--no-embedded turns this off); from a
differing element, a word that also occurs anywhere in the expression's own article is
left to that article. Such a row carries the parent's article_id and lemma, and its
location begins 'artikkel <parent>, uttrykk "<expression>" (<expression id>)'. The
words read there count towards the occurrences column too.

Words are lowercased, with punctuation stripped. Skipped: numbers; words with a
capital letter (mostly names); words of two letters or fewer; a word directly followed
by a full stop or directly preceded by one (an abbreviation such as "f.eks." or
"bl.a."); the epithets of a Latin name (below); a word directly followed or
preceded by a hyphen (half of a compound, as in "fugle- eller flyvinge") or by a
bracket inside a word ("(arbeids)oppgaver"); a hyphenated word whose parts are each a
known form; a genitive in -s of a known form ("båtens", "folks").

Latin names. Ordbokene marks a scientific name up as a ``usage`` item. Every word of a
usage item shaped like one (a capitalised genus, then one to three lowercase words,
with "x", "×", "subsp.", "var." and the like allowed between them) is skipped when the
item stands alone in its element ("$", "$ subsp. $") or none of its lowercase words is
a Bokmål form, so a genus that is also a Bokmål form ("Sylvia atricapilla", "Argentina
anserina") no longer lets its epithet through, while a Norwegian title of the same
shape ("Det kaspiske hav") is still read. A lowercase usage item after "subsp." or
"var." that follows such a name is its rank epithet ("$ var. $"). In running text
without that markup: the word directly after a capitalised word that is not itself a
Bokmål form ("Uria aalge"); a word after "x", "×" or a rank abbreviation inside such a
name ("Fragaria x ananassa", "acris subsp. acris"); and a third word directly after an
epithet that is not a Bokmål form either ("Fagus sylvatica atropunicea"). A capitalised
word that is a Bokmål form starts no Latin name in running text, so the second word of
an ordinary sentence is read.

Output is ranked by how few times the word occurs across all the definition and
example text read: a form that occurs once is likelier to be a slip than one that
occurs fifty times. One line per occurrence; the ``occurrences`` column is the word's
total count. The last column, ``mark``, is empty or ``compound``: the word splits into
two or three known Bokmål forms of at least three letters each, with an optional
linking -s- or -e- between parts ("saltvann-s-området"), and no known Bokmål form is
one edit (a letter deleted, added, changed, or two neighbours swapped) away from it.
The second condition keeps the mark off slips that happen to split ("lasestråle" is
"lase" + "stråle", but one edit from "laserstråle"). A marked row is probably a correct
compound with no article of its own; it is never dropped.

Python 3 standard library only, no network.
"""

import collections
import itertools
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEADER = ["article_id", "lemma", "location", "type", "word", "occurrences", "context", "mark"]

TOKEN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)
FORM_TOKEN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)


def forms_of(art):
    out = set()
    for lem in art.get("lemmas") or []:
        out.update(t.lower() for t in FORM_TOKEN.findall(lem.get("lemma") or ""))
        for pi in lem.get("paradigm_info") or []:
            for inf in pi.get("inflection") or []:
                out.update(t.lower() for t in FORM_TOKEN.findall(inf.get("word_form") or ""))
    return out


def read_form_list(path):
    """Forms from a full-form list: Norsk ordbank's tab-separated file (Latin-1, a header
    row naming the OPPSLAG column) or a plain list with one form per line."""
    raw = open(path, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    lines = text.splitlines()
    col = None
    if lines and "\t" in lines[0]:
        head = lines[0].split("\t")
        if "OPPSLAG" in head:
            col = head.index("OPPSLAG")
            lines = lines[1:]
    out = set()
    for ln in lines:
        form = ln.split("\t")[col] if col is not None and "\t" in ln else ln
        out.update(t.lower() for t in FORM_TOKEN.findall(form))
    return out


def collect_forms(path, include_unpublished, run):
    reader = common.Reader(path, include_unpublished)
    forms = set()
    for art in reader:
        f = run.guard(art, forms_of, art)
        if f:
            forms |= f
    return forms, reader


RANKS = {"subsp", "ssp", "var", "convar", "cv", "f"}   # followed by a full stop
HYBRID = {"x", "×"}
NAME_GENUS = re.compile(r"[^\W\d_][^\W\d_A-ZÆØÅ]*\Z", re.UNICODE)
NAME_EPITHET = re.compile(r"[^\W\d_A-ZÆØÅ]+(?:-[^\W\d_A-ZÆØÅ]+)*\Z", re.UNICODE)
NAME_FRAME = re.compile(r"(?:\$|\b(?:%s)\.|(?<!\w)[x×](?!\w)|[\s;,.:()])"
                        % "|".join(sorted(RANKS)), re.UNICODE)


def _is_link(tok):
    """A hybrid sign or a rank abbreviation, as it stands inside a Latin name."""
    return tok in HYBRID or (tok.endswith(".") and tok[:-1] in RANKS)


def _epithets(text, need_capital=True):
    """The epithets of ``text`` if it has the shape of a scientific name, else None:
    a capitalised word (the genus), then one to three lowercase words, with hybrid
    signs and rank abbreviations allowed between them ("Fragaria x ananassa",
    "Beta vulgaris subsp. vulgaris"). With need_capital=False the genus is left out
    and only lowercase words (and links) are allowed: the part after "subsp."."""
    toks = text.split()
    if need_capital:
        if len(toks) < 2 or not toks[0][:1].isupper() or not NAME_GENUS.match(toks[0]):
            return None
        toks = toks[1:]
    eps = [t for t in toks if not _is_link(t)]
    if not 1 <= len(eps) <= 3 or not all(NAME_EPITHET.match(t) for t in eps):
        return None
    if toks and _is_link(toks[-1]):
        return None
    return eps


def latin_spans(content, items, forms):
    """Render ``content`` as common.render(..., words=True) does, and return the text
    with the character spans of the ``usage`` items that hold a Latin name.

    A usage item holds a Latin name when its text has the shape of one (_epithets) and
    either it stands alone in its element (nothing else there but other usage items,
    rank abbreviations, hybrid signs and punctuation: "$", "$ subsp. $") or none of
    its lowercase words is a Bokmål form (so a Norwegian title such as "Det kaspiske
    hav", which has the same shape, is never one). A usage item of lowercase words
    only is the rest of a Latin name when the element text just before it is a rank
    abbreviation or a hybrid sign and the usage item before that is a Latin name or a
    single capitalised word ("$ var. $": "Brassica oleracea", "capitata")."""
    content = content or ""
    items = [i for i in (items or []) if isinstance(i, dict)]
    parts = content.split("$")
    alone = not NAME_FRAME.sub("", content)
    out, pos, spans = [parts[0]], len(parts[0]), []
    prev_latin = False
    for k, part in enumerate(parts[1:]):
        it = items[k] if k < len(items) else None
        s = common.render_item(it, True) if it is not None else ""
        is_latin = False
        if it is not None and it.get("type_") == "usage":
            t = it.get("text") or ""
            eps = _epithets(t)
            if eps is not None and (alone or not any(e in forms for e in eps)):
                is_latin = True
            elif (prev_latin and _is_link(parts[k].strip())
                  and _epithets(t, need_capital=False) is not None):
                is_latin = True
            if is_latin:
                spans.append((pos, pos + len(s)))
            toks = t.split()
            prev_latin = is_latin or (len(toks) == 1 and toks[0][:1].isupper()
                                      and bool(NAME_GENUS.match(toks[0])))
        else:
            prev_latin = False
        out.append(s)
        out.append(part)
        pos += len(s) + len(part)
    return "".join(out), spans


def tokens(text, forms, latin=()):
    """Yield the words of ``text`` worth checking, lowercased. ``latin`` holds the
    character spans of the Latin names found from the markup (latin_spans)."""
    prev = None
    name = 0            # in running text: 1 after a possible genus, +1 per epithet
    link = False        # the token before was "x" or a rank abbreviation in a name
    unknown = False     # the last epithet is not a Bokmål form
    for m in TOKEN.finditer(text):
        w, p = m.group(0), prev
        prev = m
        lw = w.lower()
        gap = text[p.end():m.start()].strip() if p is not None else None
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if any(s <= m.start() and m.end() <= e for s, e in latin):
            name, link = 0, False
            continue                    # a Latin name, marked up as a usage item
        if name and gap == "" and ((lw in RANKS and after == ".") or lw == "x"):
            link = True
            continue                    # "subsp." or "x" inside a Latin name
        epithet = False
        if name and w.islower():
            if link and gap in ("", "."):
                epithet = True          # "acris subsp. acris", "Fragaria x ananassa"
            elif gap == "×":
                epithet = True          # "Fragaria × ananassa"
            elif name == 1 and gap == "":
                epithet = True          # "Uria aalge": after a genus that is no Bokmål form
            elif name == 2 and gap == "" and unknown and lw not in forms:
                epithet = True          # "Fagus sylvatica atropunicea": the third word
        link = False
        if epithet:
            name += 1
            unknown = lw not in forms
            continue
        name = 1 if (w[:1].isupper() and lw not in forms) else 0
        if len(w) <= 2 or any(c.isupper() for c in w):
            continue
        if after == "." or before == ".":
            continue                    # an abbreviation: f.eks., bl.a.
        if after == "-" or before == "-":
            continue                    # half a compound: "fugle- eller flyvinge"
        after2 = text[m.end() + 1] if m.end() + 1 < len(text) else ""
        before2 = text[m.start() - 2] if m.start() > 1 else ""
        if (after == ")" and after2.isalpha()) or (before == "(" and before2.isalpha()):
            continue                    # a bracketed compound part: "(arbeids)oppgaver"
        yield lw


def known(w, forms):
    if w in forms:
        return True
    if len(w) > 3 and w.endswith("s") and w[:-1] in forms:
        return True                     # a genitive: folks, båtens, antikkens
    parts = [p for p in re.split(r"[-'’]", w) if p]
    return len(parts) > 1 and all(p in forms or len(p) <= 2 for p in parts)


LINKS = ("", "s", "e")      # the linking elements allowed between compound parts
MIN_PART = 3                # letters in each compound part


def alphabet(forms):
    """Every letter that occurs in the form set, for the edit-distance-1 variants."""
    return sorted({c for f in forms for c in f if c.isalpha()})


def edits1(w, letters):
    """Every string one deletion, substitution, insertion or swap of two neighbouring
    letters away from ``w``."""
    out = set()
    for i in range(len(w) + 1):
        a, b = w[:i], w[i:]
        if b:
            out.add(a + b[1:])
            out.update(a + c + b[1:] for c in letters)
        if len(b) > 1:
            out.add(a + b[1] + b[0] + b[2:])
        out.update(a + c + b for c in letters)
    out.discard(w)
    return out


def compound_split(w, forms, max_parts=3):
    """Split ``w`` into two or three known forms of at least MIN_PART letters each, with
    an optional linking -s- or -e- between parts. Fewest parts first; among those, the
    split whose shortest part is longest. Returns the parts (a link is written
    "+s"/"+e" on the part before it), or None."""
    def splits(rest, n):
        if n == 1:
            if len(rest) >= MIN_PART and rest in forms:
                yield [rest]
            return
        for i in range(MIN_PART, len(rest) - MIN_PART + 1):
            head = rest[:i]
            if head not in forms:
                continue
            for ln in LINKS:
                if rest.startswith(ln, i):
                    for tail in splits(rest[i + len(ln):], n - 1):
                        yield [head + ("+" + ln if ln else "")] + tail
    for n in range(2, max_parts + 1):
        found = list(splits(w, n))
        if found:
            return max(found, key=lambda p: (min(len(x.split("+")[0]) for x in p), len(p[-1])))
    return None


def mark(w, forms, letters):
    """'compound' when ``w`` splits into known forms (compound_split) and no known
    Bokmål form is one edit away from it; else ''. The second condition keeps the mark
    off slips that happen to split ("lasestråle" = "lase" + "stråle", one edit from
    "laserstråle"). A mark never removes a row."""
    if not w.isalpha() or compound_split(w, forms) is None:
        return ""
    if any(v in forms for v in edits1(w, letters)):
        return ""
    return "compound"


def article_words(art, forms, embedded=None):
    out = []
    own = ((loc, kind, content, items, None)
           for loc, kind, content, items in common.iter_text(art, etymology=False))
    for loc, kind, content, items, eid in itertools.chain(
            own, common.iter_embedded_text(art, embedded, etymology=False, expression=True)):
        text, latin = latin_spans(content, items, forms)
        ws = list(tokens(text, forms, latin))
        if eid is not None:
            had = embedded.words(eid)
            if had:                     # a word the expression's article has is read there
                ws = [w for w in ws if w not in had]
        if ws:
            out.append((loc, ws, common.render(content, items)))
    return out


#: by input dictionary: the other dictionary's language, and the label of its forms
OTHER = {"bm": ("Nynorsk", "nynorsk_form"), "nn": ("Bokmål", "bokmal_form")}
OWN = {"bm": "Bokmål", "nn": "Nynorsk"}


def main(argv=None):
    ap = common.parser(__doc__.splitlines()[0], epilog=__doc__)
    ap.add_argument("--nynorsk", metavar="NN_INPUT",
                    help="Bokmål mode: the Nynorsk dictionary's articles (directory or JSONL, "
                         "as for the input); without it or --nynorsk-forms only unknown_form "
                         "is reported")
    ap.add_argument("--bokmal", metavar="BM_INPUT",
                    help="Nynorsk mode (--dictionary nn): the Bokmål dictionary's articles; "
                         "without it or --bokmal-forms only unknown_form is reported")
    ap.add_argument("--bokmal-forms", metavar="FILE",
                    help="a Bokmål full-form list to add (Norsk ordbank fullformsliste.txt, "
                         "or one form per line)")
    ap.add_argument("--nynorsk-forms", metavar="FILE",
                    help="a Nynorsk full-form list to add (Norsk ordbank fullformer_2012.txt, "
                         "or one form per line)")
    common.add_embedded_option(ap)
    a = ap.parse_args(argv)
    if a.dictionary == "bm" and a.bokmal:
        ap.error("--bokmal is the other dictionary in Nynorsk mode; with a Bokmål input "
                 "give --nynorsk")
    if a.dictionary == "nn" and a.nynorsk:
        ap.error("--nynorsk is the other dictionary in Bokmål mode; with --dictionary nn "
                 "give --bokmal")
    run = common.Run("word_forms")
    embedded = common.embedded_for(a)
    # bm: the input language's forms; nn: the other language's (the names are the Bokmål
    # mode's, kept so its output stays byte for byte as it was)
    own_list, other_input, other_list = (
        (a.bokmal_forms, a.nynorsk, a.nynorsk_forms) if a.dictionary == "bm"
        else (a.nynorsk_forms, a.bokmal, a.bokmal_forms))
    other_lang, other_kind = OTHER[a.dictionary]
    bm, _ = collect_forms(a.input, a.include_unpublished, run)
    if own_list:
        bm |= read_form_list(own_list)
    nn = set()
    nn_note = ""
    if other_input:
        nn, nreader = collect_forms(other_input, a.include_unpublished, run)
        nn_note = "; %s: %d articles" % (other_lang, nreader.read)
    if other_list:
        nn |= read_form_list(other_list)
    if nn:
        nn_note += "; %s forms: %d" % (other_lang, len(nn))
    reader = common.Reader(a.input, a.include_unpublished)
    freq = collections.Counter()
    cand = []
    for art in reader:
        res = run.guard(art, article_words, art, bm, embedded)
        if not res:
            continue
        aid, lem = common.article_id(art), common.lemma_text(art)
        for loc, ws, shown in res:
            freq.update(ws)
            for w in ws:
                if not known(w, bm):
                    kind = other_kind if w in nn else "unknown_form"
                    cand.append((aid, lem, loc, kind, w, shown))
    cand.sort(key=lambda c: (freq[c[4]], c[4], c[0]))
    letters = alphabet(bm)
    marks = {w: mark(w, bm, letters) for w in {c[4] for c in cand}}
    tsv = common.TSV(a.output, HEADER)
    for aid, lem, loc, kind, w, shown in cand:
        tsv.row([aid, lem, loc, kind, w, freq[w], shown, marks[w]])
    return run.finish(reader, tsv, extra="; %s forms: %d%s; %d distinct words flagged; "
                      "%d rows marked compound"
                      % (OWN[a.dictionary], len(bm), nn_note, len({c[4] for c in cand}),
                         sum(1 for c in cand if marks[c[4]] == "compound"))
                      + (embedded.note() if embedded else ""))


if __name__ == "__main__":
    sys.exit(main())
