# -*- coding: utf-8 -*-
"""Word pages and form pages (site decisions 117, Robin 2026-10-24/25): a real page at
`/bm-en/<word>/` for every headword search whose first shown article is translated, and for
every common irregular inflected form of a translated word — what the index build writes after
the index (`build_index.py` `page_plan` decides WHICH; this module says how a page is
addressed, labelled, drawn, described, listed and linked). The doc of record is
`ordpar/docs/lookup-index.md` § 9.

* **The address** (`word_path`): `/bm-en/<the search's fold, percent-encoded>/` — lower case,
  the folder named in NFC UTF-8, every byte outside `A-Z a-z 0-9 _ . - ~` percent-encoded
  (`urllib.parse.quote(…, safe="")`; `lookup.js` `pagePath` writes the same string). A search
  that cannot be a folder name (`unrepresentable`: a slash, a question mark, a full stop at
  either end, …) gets no page and stays a `#q=` search.
* **The form label** (`FormLabels`): which form of its word an inflected form is, in the
  inflection table's own English (`inflection.js` `DEFAULT_STRINGS`, read from that file: the
  group, then the narrow layout's qualifier — "plural indefinite"), "passive infinitive" /
  "passive present" for the two passives the table does not show, and "perfect participle" for
  a bare participle that fills the table's "present perfect" column (decisions 117, the four
  points as the session proposed them). Several analyses within one word are one label, joined
  by commas. The index carries one code per (form, article), the codes' words once
  (`labels.json`).
* **The page** (`render`): the article page's frame (`page.py`: the head lines, `theme.js`,
  `/site/ordpar.css`, the header and footer, `/site/ordpar.js`), and in `<main>` what a search
  for the word shows in the list view — the headword rows, then the "is an inflected form of"
  rows with their labels — drawn as `lookup.js` draws them. In a browser `lookup.js`
  (`ordparSearch.wordPage`) replaces it at once by the search itself, under the reader's
  settings; the built rows are what a crawler without script, or a reader without JavaScript,
  reads.
* **Title, description, canonical** (decisions 117, "The word pages' title, description and
  canonical settled"): one article — the article page's own title and description, read from its
  built page, and the word page is canonical (the article page's canonical points to it,
  `patch_article`); several — "word — <dictionary name>" and "N entries in the <dictionary
  name>: I … · II … · III Norwegian only", every page its own canonical; a form page — the
  several-entry title and "“tær” is an inflected form of: tå, noun (plural indefinite): toe ·
  tære, verb (imperative): Norwegian only." (the session's proposal, Robin's to change).
* **The sitemap** (`write_sitemap`): the home page, About, Help, Coming (decisions 131), More (142),
  the three change lists (175, 177), every canonical word page,
  every form page, and every translated article page whose canonical is still itself.
"""
import html
import os
import re
from urllib.parse import quote, unquote

from . import chrome, head as head_mod, page as page_mod

PAIR = "bm-en"
SITE_URL = head_mod.SITE_URL
#: Decisions 117 (3): a form page for an irregular form seen at least this often in NB's 2026
#: books (`build_index.read_freq`, the list the search ranks by)
MIN_FORM_COUNT = 100
#: The pages besides the articles and the word pages that search engines may list (decisions 128);
#: `/thanks/` (166) only where the article build wrote it: `indexed_other(out)`
INDEXED_OTHER = ("/", "/about/", "/help/", "/coming/", "/more/",   # /coming/ 131, /more/ 142
                 "/changes/", "/dictionary-changes/", "/deck-changes/")   # 175, 177
#: Indexed pages the article build writes only while the reports' switch is on (site decisions 166,
#: `chrome.REPORT_RECEIVER`, `build_site.REPORTS_INDEXED`): listed only where the page is there
REPORTS_INDEXED = ("/thanks/",)


def indexed_other(out):
    """INDEXED_OTHER, and each of REPORTS_INDEXED whose page the article build wrote under `out`
    (site decisions 166: `/thanks/` exists only while reports are on, `build_site.write_thanks`) —
    so the index build, a process of its own, lists exactly what the article build made."""
    return INDEXED_OTHER + tuple(p for p in REPORTS_INDEXED
                                 if os.path.isfile(os.path.join(out, p.strip("/"), "index.html")))

_e = html.escape


def _a(text):
    return html.escape(text or "", quote=True)


# --------------------------------------------------------------------------- the address

def word_path(fq):
    """The site path of the page for the folded search `fq`: `/bm-en/s%C3%A5/`, `/bm-en/p%C3%A5%20kryss%20og%20tvers/`."""
    return "/%s/%s/" % (PAIR, quote(fq, safe=""))


def word_url(fq):
    return SITE_URL + word_path(fq)


#: Windows' reserved device names: no folder may be called so, with or without an extension
_RESERVED = frozenset(["con", "prn", "aux", "nul"] + ["com%d" % i for i in range(1, 10)]
                      + ["lpt%d" % i for i in range(1, 10)])
#: Characters no folder name may hold on Windows (where the build runs), and two more a page
#: address would carry only percent-encoded with nothing on the live site to show GitHub Pages
#: answers them (`#`, `%`): kept out, as a slash is
_FORBIDDEN = set('<>:"\\|*#%')


def unrepresentable(fq):
    """Why the folded search `fq` cannot be a folder name, or None when it can (decisions 117:
    "The 254 searches that cannot be folder names (a slash, a `?`, a trailing full stop) get no
    page and stay `#q=` searches"). The first three are the brief's; the rest no headword has
    today (2026-10-25) and are here so that a new one fails safe: a full stop at the start (a
    hidden name), digits only (an article's own folder, `/bm-en/<id>/`), a character Windows
    forbids, `#` or `%`, a space at either end, a reserved device name, over 200 bytes."""
    if not fq:
        return "empty"
    if "/" in fq:
        return "slash"
    if "?" in fq:
        return "question mark"
    if fq.endswith("."):
        return "trailing full stop"
    if fq.startswith("."):
        return "leading full stop"
    if fq.isdigit():
        return "digits only"
    if any(c in _FORBIDDEN or ord(c) < 32 for c in fq):
        return "forbidden character"
    if fq != fq.strip():
        return "space at an end"
    if fq.split(".")[0] in _RESERVED:
        return "reserved name"
    if len(fq.encode("utf-8")) > 200:
        return "too long"
    return None


def path_word(path):
    """The folded search a page path names (`/bm-en/s%C3%A5/` -> `så`), or None for any other
    path (an article's `/bm-en/<id>/`, `/bm-en/`, a deeper path)."""
    m = re.match(r"^/%s/([^/]+)/(?:index\.html)?$" % PAIR, path or "")
    if not m:
        return None
    w = unquote(m.group(1))
    return None if w.isdigit() else w


# --------------------------------------------------------------------------- the form labels

INFLECTION_JS = os.path.join(chrome.SITE_SRC, "inflection.js")

#: A cell's key (its mirror tags joined by "+", as `inflection.js` keys `TAGS`) -> (order, the
#: group's string key, the qualifier's string key or None). The words are the table's own
#: (`DEFAULT_STRINGS`): the group, then the NARROW layout's qualifier ("indefinite", not the wide
#: "indefinite form"; `NARROW_STRINGS`), as the form report § 3 built them — but
#: "masculine / feminine" (the wide header's string, its no-break space before the slash
#: included: the narrow one, "masculine/ feminine", breaks after the slash).
#: The order is the table's, so several analyses read in table order.
CELLS = {
    "Sing+Ind": (10, "singular", "indefiniteNarrow"), "Sing+Def": (11, "singular", "definiteNarrow"),
    "Plur+Ind": (12, "plural", "indefiniteNarrow"), "Plur+Def": (13, "plural", "definiteNarrow"),
    "Inf": (20, "infinitive", None), "Pres": (21, "present", None), "Past": (22, "past", None),
    # decisions 117: a bare participle that fills the "present perfect" column is labelled
    # "perfect participle" (*tatt* alone is not the present perfect; *har tatt* is)
    "<PerfPart>": (23, "perfectParticiple", None), "Imp": (24, "imperative", None),
    "Inf+<SPass>": (20, "infinitive", None), "Pres+<SPass>": (21, "present", None),
    "Past+<SPass>": (22, "past", None), "<PerfPart>+<SPass>": (23, "perfectParticiple", None),
    "Imp+<SPass>": (24, "imperative", None),
    "Adj+<PerfPart>+Masc/Fem+Ind+Sing": (30, "perfectParticiple", "mascFem"),
    "Adj+<PerfPart>+Neuter+Ind+Sing": (31, "perfectParticiple", "neuter"),
    "Adj+<PerfPart>+Def+Sing": (32, "perfectParticiple", "definiteNarrow"),
    "Adj+<PerfPart>+Plur": (33, "perfectParticiple", "plural"),
    "Adj+<PresPart>": (34, "presentParticiple", None),
    "Pos+Masc/Fem+Ind+Sing": (40, "singular", "mascFem"), "Pos+Fem+Ind+Sing": (41, "singular", "feminine"),
    "Pos+Neuter+Ind+Sing": (42, "singular", "neuter"), "Pos+Def+Sing": (43, "singular", "definiteNarrow"),
    "Pos+Plur": (44, "plural", None), "Cmp": (45, "comparative", None),
    "Sup+Ind": (46, "superlative", "indefiniteNarrow"), "Sup+Def": (47, "superlative", "definiteNarrow"),
    "Pos": (50, "positive", None), "Sup": (52, "superlative", None),
    "Masc+Ind+Sing": (60, "singular", "masculine"), "Fem+Ind+Sing": (61, "singular", "feminine"),
    "Neuter+Ind+Sing": (62, "singular", "neuter"), "Def+Sing": (63, "singular", "definiteNarrow"),
    "Plur": (64, "plural", None),
    "Masc+Sing": (60, "singular", "masculine"), "Fem+Sing": (61, "singular", "feminine"),
    "Neuter+Sing": (62, "singular", "neuter"),
    "Nom": (70, "subjectForm", None), "Acc": (71, "objectForm", None),
}
#: The two periphrastic passives the table drops (`inflection.js` `TAGS`: "ordbokene shows no
#: passive column"): "passive" and the table's own word (decisions 117: "passive infinitive" /
#: "passive present", the session's words)
PASSIVES = {"Inf+Pass": (25, "infinitive"), "Pres+Pass": (26, "present")}
PASSIVE_WORD = "passive"


def table_strings(path=INFLECTION_JS, name="DEFAULT_STRINGS"):
    """`inflection.js`'s `DEFAULT_STRINGS` as a dict — the words the table's headers use, read
    from the file itself so that the labels and the table never differ. `name` "NB_STRINGS": the
    tables' Norwegian words (site decisions 152), for the labels' Norwegian (`FormLabels.nb`)."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    start = src.index("var %s = {" % name)
    end = src.index("};", start)
    body = re.sub(r"/\*.*?\*/", "", src[start:end], flags=re.S)
    return dict(re.findall(r"(\w+): '([^']*)'", body))


class FormLabels:
    """The form labels and their codes. `label(keys)` -> the words for a set of cell keys;
    `code(keys)` -> its one-character code, the codes handed out most frequent label first
    (`assign`); `table()` -> `{code: words}`, the index's `labels.json`."""

    #: The code characters: A-Z a-z 0-9, then on into Latin-1 letters (never a JSON escape)
    ALPHABET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
                + "".join(chr(c) for c in range(0xC0, 0x250) if chr(c).isalpha()))
    #: The code of an analysis with no label (a cell key outside `CELLS` and `PASSIVES`)
    NONE = "-"

    def __init__(self, strings=None, words=("passive", "and"), form=None):
        self.s = strings if strings is not None else table_strings()
        self.passive, self.and_ = words
        #: the word "form" where a number's definiteness leads (the Norwegian: `nb`), else None
        self.form = form
        self.unknown = {}            # an unknown cell key -> how often
        self._codes = {}
        self._keys = {}              # a label's words -> a set of cell keys it was made from
        self._nb = None

    def nb(self):
        """The same labels in NORWEGIAN (site decisions 152: the inflection tables' words, under
        Norwegian only or the labels setting): the tables' Norwegian words (`NB_STRINGS`, with the
        English for a key it lacks), "passiv", "og"; a number's definiteness in the Norwegian order,
        definiteness, "form", then number (152's follow-up: "ubestemt form
        flertall", as Bokmålsordboka's own definitions write "i bestemt form entall"; `label`).
        Ordbokene's rows show no composed label: the composition is ours."""
        if self._nb is None:
            nb = dict(self.s)
            nb.update(table_strings(name="NB_STRINGS"))
            self._nb = FormLabels(nb, ("passiv", "og"), form="form")
        return self._nb

    def label_nb(self, keys):
        """`label`'s words in Norwegian ("ubestemt form flertall")."""
        return self.nb().label(keys)

    def table_nb(self):
        """`{code: Norwegian words}` for every code `table` has: `labels.json`'s `"_nb"`."""
        return {c: self.label_nb(self._keys.get(w, ())) for w, c in self._codes.items()}

    def _part(self, key):
        if key in PASSIVES:
            o, w = PASSIVES[key]
            return o, "%s %s" % (self.passive, self.s[w]), None
        if key in CELLS:
            o, g, q = CELLS[key]
            qual = self.s.get(q) if q else None
            return o, self.s[g], qual
        self.unknown[key] = self.unknown.get(key, 0) + 1
        return None

    def label(self, keys):
        """"plural indefinite"; "past, perfect participle masculine / feminine and neuter"; ""
        for none: each group once, in table order, its qualifiers run together ("and" before
        the last). With `form` (the Norwegian), a NUMBER whose qualifiers are all definiteness
        reads definiteness, "form", number (`_definite_first`): "ubestemt form flertall",
        "ubestemt og bestemt form flertall"; the degrees, the participles and a number led by a
        gender ("entall intetkjønn") keep the table's order (Robin, 2026-11-01)."""
        groups = {}                  # group words -> [first order, [qualifiers]]
        for key in keys:
            p = self._part(key)
            if p is None:
                continue
            o, g, q = p
            if g not in groups:
                groups[g] = [o, []]
            groups[g][0] = min(groups[g][0], o)
            if q and q not in groups[g][1]:
                groups[g][1].append((o, q))
        out = []
        for g, (o, quals) in sorted(groups.items(), key=lambda kv: kv[1][0]):
            qs = [q for _o, q in sorted(quals)]
            if self.form and self._is_number(g, qs):
                out.append((g, qs))             # composed by `_definite_first` below
            elif not qs:
                out.append(g)
            elif len(qs) <= 2:
                out.append("%s %s" % (g, (" %s " % self.and_).join(qs)))
            else:
                out.append("%s %s %s %s" % (g, ", ".join(qs[:-1]), self.and_, qs[-1]))
        if self.form:
            out = self._definite_first(out)
        return ", ".join(out)

    def _is_number(self, g, qs):
        """`g` the singular or the plural, its qualifiers (if any) all definiteness."""
        defs = (self.s.get("indefiniteNarrow"), self.s.get("definiteNarrow"))
        return g in (self.s.get("singular"), self.s.get("plural")) and all(q in defs for q in qs)

    def _definite_first(self, items):
        """The numbers among `items` (`(number, [definiteness])`; the rest already words) in
        the Norwegian order: "bestemt form entall"; the singular and the plural side by side as
        one where the plural has the same definiteness or none ("bestemt form entall og
        flertall", 152's follow-up, for "singular definite, plural"), else each on
        its own ("bestemt form entall, ubestemt og bestemt form flertall"); a bare number as it
        is ("flertall")."""
        def one(g, qs):
            return "%s %s %s" % ((" %s " % self.and_).join(qs), self.form, g) if qs else g
        out, i = [], 0
        while i < len(items):
            it = items[i]
            if isinstance(it, str):
                out.append(it)
                i += 1
                continue
            g, qs = it
            nxt = items[i + 1] if i + 1 < len(items) and not isinstance(items[i + 1], str) else None
            if qs and nxt and nxt[0] != g and (not nxt[1] or nxt[1] == qs):
                out.append("%s %s %s" % (one(g, qs), self.and_, nxt[0]))
                i += 2
                continue
            out.append(one(g, qs))
            i += 1
        return out

    def assign(self, keysets):
        """Hand out the codes: `keysets` every analysis (a set of cell keys) the index carries,
        repeats included; the most frequent label gets the first character."""
        count = {}
        for ks in keysets:
            w = self.label(ks)
            if w:
                count[w] = count.get(w, 0) + 1
                self._keys.setdefault(w, ks)
        words = sorted(count, key=lambda w: (-count[w], w))
        if len(words) > len(self.ALPHABET):
            raise ValueError("%d form labels, more than the %d codes" % (len(words), len(self.ALPHABET)))
        self._codes = {w: self.ALPHABET[i] for i, w in enumerate(words)}
        return self._codes

    def code(self, keys):
        return self._codes.get(self.label(keys), self.NONE)

    def table(self):
        return {c: w for w, c in self._codes.items()}


def is_passive_only(keysets):
    """Every analysis of a form only a passive (decisions 117: "No page for a form that is only
    a passive")."""
    keys = set().union(*keysets) if keysets else set()
    return bool(keys) and keys <= set(PASSIVES)


def irregular(fq, spellings, fold):
    """Decisions 117 (3), the form report's (b) class: the folded form `fq` begins neither with
    one of its word's spellings nor with one less a final -e (the stem at least two letters)."""
    for s in spellings:
        f = fold(s)
        if fq.startswith(f):
            return False
        if f.endswith("e") and len(f) >= 3 and fq.startswith(f[:-1]):
            return False
    return True


# --------------------------------------------------------------------------- the page

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def roman(n):
    return ROMAN[n] if 0 <= n < len(ROMAN) else str(n)


SEP = " / "


def head_parts(a):
    """`lookup.js` `headParts`: [(spelling, numeral)] and whether the text was cut."""
    text = a.get("word") or ""
    cut = text.endswith(" …")
    forms = text[:-2].split(SEP) if cut else text.split(SEP)
    hgs = a.get("hgs")
    return [(f, (hgs[i] if hgs and i < len(hgs) else 0) if hgs else (a.get("hg") or 0))
            for i, f in enumerate(forms)], cut


def head_text(a):
    """`lookup.js` `headText`: "lysing I, lysning II"."""
    parts, cut = head_parts(a)
    return ", ".join(w + (" " + roman(h) if h else "") for w, h in parts) + (" …" if cut else "")


def _headword_html(a, s):
    """`lookup.js` `headwordInto`: each spelling, its numeral hidden from assistive technology
    with a visually hidden reading beside it — `data-nosnippet`, so a search engine's snippet
    leaves it out (site decisions 154: Google showed "være III homograph 3")."""
    if not a.get("word"):
        return "#%d" % a["id"]
    parts, cut = head_parts(a)
    out = []
    for i, (w, h) in enumerate(parts):
        bit = _e(w)
        if h:
            bit += (' <span class="ordbok-homograph ordpar-hg" aria-hidden="true">%s</span>'
                    '<span class="ordpar-visually-hidden" data-nosnippet> %s</span>'
                    % (roman(h), _e(s["results.homograph"].replace("{n}", str(h)))))
        out.append(bit)
    return ", ".join(out) + (" …" if cut else "")


def pos_label(pos, s):
    """`lookup.js` `posLabel`: the word class's words, none for a set phrase."""
    return s.get("pos." + pos, "") if pos else ""


def pos_html(pos, s):
    """A built row's word class (`lookup.js` `posSpan`), newline-led (`_sep`): its words, and
    where the Norwegian differs (site decisions 152, `pos.nb.<code>`) both copies — the
    Norwegian, which the default hides, with `lang="nb"` and `data-nosnippet` (154) — the sheet
    showing the Norwegian under Norwegian only or the labels setting (`ordpar-w-*`); "" for none."""
    en = pos_label(pos, s)
    if not en:
        return ""
    nb = s.get("pos.nb." + pos, "")
    if not nb:
        return _sep('<span class="ordpar-pos">%s</span>' % _e(en))
    return _sep('<span class="ordpar-pos"><span class="ordpar-w-en">%s</span>'
                '<span class="ordpar-w-nb" lang="nb" data-nosnippet>%s</span></span>' % (_e(en), _e(nb)))


def _gloss_html(text, gloss):
    """`lookup.js` `writeGloss`: a summary gloss marked semibold, its " · " faded."""
    if not gloss:
        return _e(text)
    return '<span class="ordpar-gsep"> · </span>'.join(_e(p) for p in text.split(" · "))


def _snip_span(cls, a, snip):
    """The row's one-line snippet; for a translated article with a first Norwegian definition
    (site decisions 152, `snip`'s third value) a second line beside it, `ordpar-nbsnip`, hidden
    but under Norwegian only's rows on "Norwegian definition" (`page.SITE_CSS`), with
    `data-nosnippet` (the copy the default hides, 154)."""
    got = snip(a) if snip else ("", False)
    text, gloss = got[0], got[1]
    nb = got[2] if len(got) > 2 else ""
    if not text:
        return ""
    out = '<span class="%s%s" lang="%s">%s</span>' % (
        cls, " ordpar-sgloss" if gloss else "", "en" if a.get("translated") else "nb",
        _gloss_html(text, gloss))
    if nb and a.get("translated"):
        out += '\n<span class="%s ordpar-nbsnip" lang="nb" data-nosnippet>%s</span>' % (cls, _e(nb))
    return out


def _sep(markup):
    """`markup` with a newline before it, or "" (site decisions 154): the pieces of a row — the
    word, its word class, its tag, its snippet line — are separate on the page (a flex row, a grid
    line), and with nothing between them in the markup a text extraction joined them ("verbto
    scent"). In a flex or grid layout a newline between the children draws nothing."""
    return ("\n" + markup) if markup else ""


def _tag(a, s):
    # site decisions 137 (Robin, 2026-10-26): only an untranslated article is tagged, "Norwegian only"
    return "" if a.get("translated") else '<span class="ordpar-tag">%s</span>' % _e(s["tag.norwegianOnly"])


def list_rows(arts, s, snip):
    """`lookup.js` `listRows` as built HTML: one row per article — headword, word class, the
    translated tag, the one-line snippet — each a disclosure button, its panel holding the
    article page's link (the script opens the article in place)."""
    out = []
    for a in arts:
        out.append(
            '<div class="ordpar-row" data-id="%(id)d"><h3 class="ordpar-row-head">'
            '<button class="ordpar-row-button" type="button" id="r%(id)d-row" aria-expanded="false" '
            'aria-controls="r%(id)d-panel"><span class="ordpar-row-chevron" aria-hidden="true"></span>\n'
            '<span class="ordpar-row-line"><span class="ordpar-row-word" lang="nb">%(word)s</span>'
            '%(pos)s%(tag)s</span>%(snip)s</button></h3>\n'
            '<div class="ordpar-row-panel" id="r%(id)d-panel" role="region" aria-labelledby="r%(id)d-row" hidden>'
            '<a href="/%(pair)s/%(id)d/">%(page)s</a></div></div>'
            % {"id": a["id"], "word": _headword_html(a, s), "pair": PAIR,
               "pos": pos_html(a.get("pos"), s),
               "tag": _sep(_tag(a, s)), "snip": _sep(_snip_span("ordpar-row-snippet", a, snip)),
               "page": _e(s["results.articlePage"])})
    return '<div class="ordpar-rows">%s</div>' % "\n".join(out)


def form_label_html(label, label_nb=""):
    """The form label after the word class (decisions 117, Robin's shape: *tå* *noun* (plural
    indefinite)) — `lookup.js` `articleItem` draws the same. Site decisions 152: with its
    Norwegian (`FormLabels.label_nb`) both copies, the Norwegian hidden by default, with
    `data-nosnippet` (154); the sheet shows it under Norwegian only or the labels setting."""
    if not label:
        return ""
    if not label_nb:
        return '<span class="ordpar-form-label">(%s)</span>' % _e(label)
    return ('<span class="ordpar-form-label"><span class="ordpar-w-en">(%s)</span>'
            '<span class="ordpar-w-nb" lang="nb" data-nosnippet>(%s)</span></span>' % (_e(label), _e(label_nb)))


def form_rows(arts, s, snip):
    """`lookup.js` `articleList` as built HTML: the "is an inflected form of" rows, each its
    headword's link, word class, form label, translated tag and snippet — in the order given,
    which is the index's stored order (the most common headword first, site decisions 143:
    `build_index.form_order`, kept by `Index.lookup`); never re-sorted here."""
    out = []
    for a in arts:
        out.append('<li class="ordpar-hit"><a class="ordpar-hit-link" href="/%s/%d/" lang="nb">%s</a>%s%s%s%s</li>'
                   % (PAIR, a["id"], _headword_html(a, s),
                      pos_html(a.get("pos"), s),
                      _sep(form_label_html(a.get("label"), a.get("label_nb"))), _sep(_tag(a, s)),
                      _sep(_snip_span("ordpar-hit-snippet", a, snip))))
    return '<ul class="ordpar-hits-list">%s</ul>' % "\n".join(out)


def results_heading(count, s):
    """`lookup.js` `resultsHeading`."""
    return ('<h2 class="ordpar-section-title ordpar-dict-title"><span class="ordpar-dict-name">%s</span>\n'
            '<span class="ordpar-count"><span aria-hidden="true">%d</span><span class="ordpar-visually-hidden" data-nosnippet> %s</span></span></h2>'
            % (_e(s["results.dictionary"]), count,
               _e((s["results.countOne"] if count == 1 else s["results.count"]).replace("{n}", str(count)))))


def main_html(word, page, s, snip):
    """What `<main>`'s results hold as built: the word as the headline (its own capitals), the
    results' heading, the headword rows (the list view's), then each "is an inflected form of"
    section."""
    out = ['<h1 class="ordpar-word-title" lang="nb">%s</h1>' % _e(word)]
    if page["count"]:
        hits = results_heading(page["count"], s)
        if page["arts"]:
            hits += "\n" + list_rows(page["arts"], s, snip)
        out.append('<section class="ordpar-hits">%s</section>' % hits)
    for form, arts in page["forms"]:
        out.append('<section class="ordpar-inflected"><h2 class="ordpar-section-title">%s</h2>\n%s</section>'
                   % (_e(s["results.inflected"].replace("{q}", form)), form_rows(arts, s, snip)))
    return "\n".join(out)


def render(*, fq, word, page, title, description, canonical, s, assets, snip):
    """One word or form page: the article page's frame around the built results. `fq` the
    search (`data-ordpar-word`, which `lookup.js` `wordPage` answers); `word` its headline;
    `page` `{count, arts, forms}`; `canonical` a site path; `assets` `{href: href?v=…}`."""
    cs = page_mod.chrome_strings(s)
    return page_mod.finish("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<link rel="canonical" href="%(canonical)s">
<meta name="description" content="%(description)s">
%(head)s
<script src="%(theme)s"></script>
<link rel="stylesheet" href="%(css)s">
</head>
<body class="ordpar">
%(header)s<main id="ordpar-main" class="ordpar-main ordpar-main--cards" tabindex="-1" data-ordpar-word="%(fq)s">
<div class="ordpar-visually-hidden" data-ordpar-live data-nosnippet role="status" aria-live="polite"></div>
<div data-ordpar-results>%(results)s</div>
</main>
%(footer)s<script src="%(js)s" defer></script>
</body>
</html>
""" % {"title": _e(title), "canonical": SITE_URL + canonical, "description": _a(description),
       "head": head_mod.head_tags(indexed=True, social={"url": canonical, "title": title,
                                                         "description": description}),
       "theme": assets[head_mod.THEME_JS_HREF], "css": assets[page_mod.CSS_ALL_HREF],
       "header": chrome.header(cs), "footer": chrome.footer(cs), "fq": _a(fq),
       "results": main_html(word, page, s, snip), "js": assets[page_mod.JS_ALL_HREF]})


# --------------------------------------------------------------------------- the words

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_DESC_RE = re.compile(r'<meta name="description" content="([^"]*)">')


def article_meta(out, aid):
    """An article page's own `<title>` and meta description, as built (`sitegen/describe.py`),
    or None when the page is not there."""
    p = os.path.join(out, PAIR, str(aid), "index.html")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        head = f.read(6000)
    t, d = _TITLE_RE.search(head), _DESC_RE.search(head)
    return (html.unescape(t.group(1)) if t else "", html.unescape(d.group(1)) if d else "")


def several_title(word, s):
    """A word page with several entries, and a form page: "så — Norwegian–English dictionary"."""
    return "%s — %s" % (word, s["dictionary_name"])


def entry_text(a, gloss_text, s):
    """One entry of a several-entry description: its numeral, then its first summary gloss — or
    what the suggestions show for it (a set-phrase box, the snippet's first unit) — or "Norwegian
    only"."""
    text = gloss_text(a) if a.get("translated") else ""
    text = text or (s["tag.norwegianOnly"] if not a.get("translated") else "")
    hg = a.get("hg") or 0
    return ("%s %s" % (roman(hg), text) if hg else text).strip()


def several_description(arts, gloss_text, s, word=""):
    """"så: 3 entries in the Norwegian–English dictionary. II when · III then · I Norwegian only".
    Site decisions 154 (Robin, 2026-10-31): the word first, then 117's words (Robin, 2026-10-25),
    their colon a full stop after the word's own. Without `word`, as before 154: "3 entries in
    the Norwegian–English dictionary: II when · …"."""
    entries = s["word_page_entries"].replace("{n}", str(len(arts))).replace(
        "{dictionary}", s["dictionary_name"])
    if word:
        entries = "%s: %s. " % (word, entries.rstrip().rstrip(":"))
    return "%s%s" % (entries, " · ".join(entry_text(a, gloss_text, s) for a in arts))


def form_description(form, arts, gloss_text, s, word=False):
    """"“tær” is an inflected form of: tå, noun (plural indefinite): toe · tære, verb
    (imperative): Norwegian only." — the page's own rows in one line. With `word` (site
    decisions 154, Robin 2026-10-31: the word first) "tær: an inflected form of tå, noun (plural
    indefinite): toe · tære, verb (imperative): Norwegian only." (`form_page_lead`)."""
    items = []
    for a in arts:
        bits = head_text(a)
        pos = pos_label(a.get("pos"), s)
        if pos:
            bits += ", " + pos
        if a.get("label"):
            bits += " (%s)" % a["label"]
        text = gloss_text(a) if a.get("translated") else ""
        bits += ": " + (text or s["tag.norwegianOnly"])
        items.append(bits)
    if word:
        return "%s%s." % (s["form_page_lead"].replace("{q}", form), " · ".join(items))
    return "%s %s." % (s["results.inflected"].replace("{q}", form), " · ".join(items))


# --------------------------------------------------------------------------- sitemap and links

def write_sitemap(path, paths):
    """`/sitemap.xml` (decisions 128, 117): the site paths given, absolute, in order, each once;
    no `<lastmod>`. -> {"urls", "bytes"}."""
    seen, urls = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            urls.append(SITE_URL + p)
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join("<url><loc>%s</loc></url>\n" % _e(u) for u in urls) + "</urlset>\n")
    blob = body.encode("utf-8")
    with open(path, "wb") as f:
        f.write(blob)
    return {"urls": len(urls), "bytes": len(blob)}


def sitemap_articles(path):
    """The article pages the article build's sitemap lists (`build_site.write_sitemap`: the
    translated ones), as ids — the index build rewrites the file with the word pages."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [int(m) for m in re.findall(r"<loc>%s/%s/(\d+)/</loc>" % (re.escape(SITE_URL), PAIR), f.read())]


_CANON_RE = re.compile(r'(<link rel="canonical" href=")([^"]*)(">)')
_OGURL_RE = re.compile(r'(<meta property="og:url" content=")([^"]*)(">)')
_VIEWLINE_RE = re.compile(r'<p class="ordpar-viewline">.*?</p>', re.S)
#: The "N more entries for …" link in the "Article view" line: a search (`#q=<form>`) as the
#: article build writes it, or a word page as this one patched it
_MORE_RE = re.compile(r'(<a href=")/%s/(?:#q=([^"]*)|([^"/#]+)/)(">)' % PAIR)


def patch_article(text, aid, canonical, has_page):
    """An article page's canonical and link-preview address set to `canonical` (a site path;
    its own `/bm-en/<id>/` or a word page), and its "N more entries for …" link sent to the
    word's page where it has one (`has_page(fq)`), else to the word's search (`face.lemma_url`,
    the one place that address is made). -> the new text, or None when nothing changes."""
    from . import face as site_face
    url = SITE_URL + canonical
    new = _CANON_RE.sub(lambda m: m.group(1) + url + m.group(3), text, count=1)
    new = _OGURL_RE.sub(lambda m: m.group(1) + url + m.group(3), new, count=1)

    def more(m):
        form = unquote(m.group(2) if m.group(2) is not None else m.group(3))
        return m.group(1) + site_face.lemma_url(form, has_page) + m.group(4)

    def viewline(m):
        return _MORE_RE.sub(more, m.group(0), count=1)
    new = _VIEWLINE_RE.sub(viewline, new, count=1)
    return None if new == text else new
