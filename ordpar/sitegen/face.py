# -*- coding: utf-8 -*-
"""The site face over the deck's control markup.

The deck's renderer builds every cross-reference through three module-level functions —
`ordbok_gen.xref` (the two-tier control), `ordbok_gen.xref_hover` (the hover-only control
inside a mini) and `ordbok_gen.article_url` (the headword's link) — and every mini through
`markup.mini.render`. The site needs the same references with our URLs — since decisions 80
a plain link and its peek, the mini made in the browser from the target's own page. All four
are **replaced at module level** from here;
neither `ordbok_gen.py` nor `markup.py` is edited (site decisions 30, recommended (1); the
one additive change in the deck's code is `mini.render(side=…)`).

Three things this face does that the deck's has no need for:

* **A plain link, no mini** (site decisions 80, Robin 2026-10-21; reverses 34's inlined
  minis). `xref` writes each cross-reference as `<a class="ordbok-xword" href="/bm-en/<id>/">`
  (`#def<N>` included) with its hover peek beside it — no checkbox, no backdrop, no mini in the
  page. Without JavaScript the link navigates; the site's mini script (`ordpar/site/mini.js`)
  upgrades it, fetching the target's own page and cutting the mini out of it on the reader's
  side. `MiniShim.render` therefore renders nothing: it only tells `xref` where the link goes,
  the URL the inlined mini's headword linked to until then (`markup._render_link` calls the
  two in that order).
* **Untitled cross-references.** A derived-Norwegian link has no title until its English is
  authored, and `markup` raises on one under `strict` (a live card must not ship half-built).
  An untranslated page is *made* of such links, so `MarkupShim.expand` gives them a sentinel
  title and the link drops the peek, and no page ever ships a `ordbok-flag`.
* **A target that does not exist.** A cross-reference to an id in neither the library nor
  the mirror would raise for the same reason. It is downgraded to plain text (a mention in
  Norwegian, the bare gloss in English) and counted.

**One link per reference, on the line that leads** (decisions 54, Robin 2026-10-18). A
translated line pair renders its Norwegian line first, under `MarkupShim.record_links()`:
every reference there is the link, recorded against its target URL. The English line follows
under `partner_links()`: each reference takes the first unused Norwegian link with the same
target (`#defN` included), in order, and becomes a PARTNER — the same link markup inside
`<span class="ordbok-xref ordpar-xen">`, with the word's own peek (the Norwegian face). The
sheet makes a partner a plain word, its peek hidden, unless the English stands alone
(`defs = en`; in a mini, `mini` = en): the link lives on the line that leads (`page.SITE_CSS`).
An English reference with no Norwegian partner is a plain word; a Norwegian one with no
English partner keeps its link.
"""
import contextlib
import html
import re
from urllib.parse import quote

from . import deck

ordbok_gen = deck.ordbok_gen
markup = deck.markup
mini = deck.mini

#: Stands in for a cross-reference title that does not exist. It never reaches the page:
#: the control drops the peek, and the mini drops its header gloss. NUL cannot occur in a
#: stored string (guardrail 6's validator would not be needed to know that).
SENTINEL = chr(0)

#: The marker grammar, as `scripts/markup.py` defines it (its docstring, lines 1-27):
#: `[label](href "title")`, optionally brace-wrapped for a Norwegian-visible link. Ours
#: matches only our own href shape, so nothing else in a string can be touched.
_LINK = re.compile(r"(\{)?\[(?P<label>[^\]]+)\]"
                   r"\((?P<href>/nob/bm/(?P<id>\d+)(?:#def\d+)?)"
                   r"(?:\s+\"(?P<title>[^\"]*)\")?\)(?(1)\})")

PAIR = "bm-en"   # the URL's first segment: the dictionary PAIR, never the interface language


def lemma_url(form, has_page=None):
    """Where a link to a headword goes (the "N more entries for …" line): its word page,
    `/bm-en/<fold>/` (site decisions 117, `wordpages.word_path`), where `has_page(fold)` says
    one is built, else its search, `/bm-en/#q=<form>` (decisions 104: the search after `#`).
    Never the unfolded `/bm-en/<form>`, which answered 404 on the case-sensitive host
    (`/bm-en/Norge`) until 117. The article build knows no word pages yet (`has_page` None):
    it writes the search, and the index build sends the link to the page where one exists
    (`wordpages.patch_article`)."""
    import unicodedata
    fq = unicodedata.normalize("NFC", form or "").lower()
    if has_page is not None and has_page(fq):
        from .wordpages import word_path
        return word_path(fq)
    return "/%s/#q=%s" % (PAIR, quote(form or "", safe=""))


def site_url(aid, defn=None):
    """A site article URL. The readable form `/bm-en/<id>/<lemma>` is accepted by the
    shell's 404 redirect (build C) but never generated — one address per article
    (decisions 24, refinement 1)."""
    return "/%s/%d/%s" % (PAIR, aid, "#def%d" % defn if defn is not None else "")


class SiteFace(object):
    """The installed face. One per build; holds the row store, the per-page library and the
    counters the report needs."""

    def __init__(self, store, omit_minis=False):
        self.store = store
        # no page carries a mini since decisions 80: kept so `build_site.py --measure`'s
        # "without the minis" variant still runs (it is now the same page)
        self.omit_minis = omit_minis
        self.lib = {}
        # set by the mini shim, read by `xref` — `markup._render_link` asks for the mini and
        # then immediately builds the link around it
        self.current_target_url = ""
        # counters: `minis` counts the links that open a mini (one per reference; the name is
        # the build report's); `mini_bytes` is 0 since decisions 80 — no page carries one
        self.minis = 0
        self.mini_bytes = 0
        self.downgraded = 0
        self.peekless = 0
        # the line-pair matching (decisions 54): None, "record" (the Norwegian line) or
        # "partner" (the English line); `recorded` maps a target URL to its control uids
        self.mode = None
        self.recorded = {}
        self.matched = 0
        self.no_unmatched = 0
        self.en_unmatched = 0
        # decisions 119: inside a Norwegian-only unit (`norwegian_only`) an untitled link takes
        # its TARGET's English as its peek; `nb_peeks` holds the page's peeks, the title carries
        # its index after the sentinel; `nb_counts` counts the links given one, by kind
        self.nb_only = 0
        self.nb_peeks = []
        self.nb_counts = {"bare": 0, "sense": 0}
        self._translated = {}
        # site decisions 152: `snip_key(id)` -> the `snip/` file key of an article's first
        # spelling (`build_index.snippet_key`), set by the site's build (`build_site.Builder`);
        # each leading link then carries it (`data-s`), so a hover can read the target's first
        # Norwegian definition from that file. None (the deck): no attribute
        self.snip_key = None

    # --- the per-page library ------------------------------------------------

    def set_library(self, lib):
        self.lib = lib
        markup.set_library(lib)

    def set_page(self, aid):
        """Begin a page: reset the reveal/control id counter, salted with the article id so
        a rebuild is byte-identical (`markup.set_card`)."""
        markup.set_card("a%d" % aid)
        self.minis = 0
        self.mini_bytes = 0
        self.nb_peeks = []

    def resolvable(self, aid, hover_only=False):
        """Can the page draw a cross-reference to `aid`?

        The click tier needs the target's ROW (the mini is rendered from it), so the test is
        the page library. A link INSIDE a mini is hover-only — it reads no row, it only
        needs somewhere to go — so there the test is merely that the article exists at all.

        An expression whose row was derived from its parent's embedded copy
        (`Store.embedded_expr`) is in the library only to be rendered in its parent's Fixed
        expressions block and in a mini's: it has no page to send a click to, so a
        reference to it stays plain text, as it did before it had a row.

        Likewise any target the build writes no page for (`has_page`, set by `build_site.py`
        main; None in a test or partial run: every target counts as having one): a library
        row is not a page. Found 2026-11-08: the deck batch translated *lufte ut* (122112), an
        expression ordbokene 404s and our mirror neither lists nor keeps (decisions 46), so
        *utluftet*'s reference to it became a link to no page (`test_ordpar_links`).
        """
        embedded_only = getattr(self.store, "is_embedded_only", None)  # a test's stub store
        if embedded_only is not None and embedded_only(aid):
            return False
        has_page = getattr(self, "has_page", None)
        if has_page is not None and not has_page(aid):
            return False
        if aid in self.lib:
            return True
        return hover_only and (aid in self.store.mirror or aid in self.store.library)

    # --- marker preprocessing ------------------------------------------------

    def preprocess(self, text, norwegian=False, hover_only=False):
        """`text` with every cross-reference the page cannot draw made drawable: an
        unresolvable target downgraded to plain text, an untitled link given the sentinel
        title. Everything else is untouched, so `markup.expand` does all the real work.
        (The counters count controls: the English line of a pair, whose references are
        partner words, is not counted a second time.)"""
        if not text or "](" not in text:
            return text
        count = int(hover_only or self.mode != "partner")

        def sub(m):
            aid = int(m.group("id"))
            label, title, wrapped = m.group("label"), m.group("title"), m.group(1)
            if not self.resolvable(aid, hover_only):
                self.downgraded += count
                return "{%s}" % label if (norwegian or wrapped) else label
            if not title:
                title = SENTINEL
                if (self.nb_only and not hover_only and self.mode is None
                        and (norwegian or wrapped)):
                    peek = self.target_english(m.group("href"))
                    if peek is not None:
                        self.nb_peeks.append(peek)
                        title = SENTINEL + str(len(self.nb_peeks) - 1)
                if title == SENTINEL:
                    self.peekless += count
            else:
                return m.group(0)
            core = '[%s](%s "%s")' % (label, m.group("href"), title)
            return "{%s}" % core if wrapped else core

        return _LINK.sub(sub, text)

    # --- the target's English on a Norwegian-only unit's links (decisions 119) ---

    @contextlib.contextmanager
    def norwegian_only(self):
        """A Norwegian-only unit — an untranslated page, a translated page's untranslated set
        phrases: inside it an untitled link's peek is its target's English (`target_english`)."""
        self.nb_only += 1
        try:
            yield
        finally:
            self.nb_only -= 1

    def translated_row(self, aid):
        """The target's library row when its page is translated (`coverage.complete_strict`, the
        build's own test in `Store.status`), else None."""
        if aid not in self._translated:
            row = self.store.library.get(aid)
            ok = row is not None and deck.coverage.complete_strict(row)
            self._translated[aid] = row if ok else None
        return self._translated[aid]

    def target_english(self, href):
        """The peek a Norwegian-only unit's untitled link to `href` (`/nob/bm/<id>[#def<N>]`)
        takes from its target's library row, read at build time — nothing stored twice (site
        decisions 119, Robin 2026-10-24: his pick of the style lab's "Robin's pick, breaking as
        the article"):

        * a **bare** reference to a translated target with summary glosses: the glosses joined by
          `markup.HEADLINE_SEP`, exactly as a translated page's Norwegian-line peek has them
          (`markup.headline_gloss`) — `("bare", html)`; the mini's header takes it, as there;
        * a reference to **one sense** of a translated target: that sense's whole English
          definition line as the target's page shows it — the segments in the page's order
          (`ordbok_gen.collapse_order`), each reduced to the words a reader sees (`plain_en`),
          broken where the page breaks it (`;<br>`) — `("sense", html)`; the sheet sets it in
          regular weight and wraps it at 22rem (`page.SITE_CSS`, `ordpar-nbdef`), and the mini's
          header leaves it out (`mini.js` `header`);
        * None where the target is untranslated, where a translated target has no summary glosses
          (bare), or where the targeted sense is not among its senses or has no English."""
        m = _NOB_HREF.match(href or "")
        if not m:
            return None
        row = self.translated_row(int(m.group(1)))
        if row is None:
            return None
        if m.group(2) is None:
            gl = (row.get("summary") or {}).get("gloss") or []
            if not gl:
                return None
            return ("bare", html.escape(markup.HEADLINE_SEP.join(gl), quote=False))
        en = (_unit(row, int(m.group(2))) or {}).get("en")
        if not en:
            return None
        segs = [plain_en(en[i]) for i in ordbok_gen.collapse_order(en)]
        segs = [html.escape(t, quote=False) for t in segs if t]
        return ("sense", ";<br>".join(segs)) if segs else None

    def _nb_peek(self, peek):
        """A title `preprocess` gave a Norwegian-only link: `(html, kind)`, counted; else None."""
        if peek and peek.startswith(SENTINEL) and len(peek) > 1:
            try:
                kind, text = self.nb_peeks[int(peek[1:])]
            except (ValueError, IndexError):
                return None
            self.nb_counts[kind] += 1
            return text, kind
        return None

    # --- the line pair (decisions 54) -----------------------------------------

    @contextlib.contextmanager
    def record_links(self):
        """The Norwegian line of a pair: full controls, each uid recorded by target URL."""
        self.mode, self.recorded = "record", {}
        try:
            yield
        finally:
            self.mode = None

    @contextlib.contextmanager
    def partner_links(self):
        """The English line of the same pair: partner words, matched by target in order.
        On leaving, whatever the Norwegian line recorded and nothing claimed is counted."""
        self.mode = "partner"
        try:
            yield
        finally:
            self.mode = None
            self.no_unmatched += sum(len(v) for v in self.recorded.values())
            self.recorded = {}

    def _partner(self, visible, peek):
        """One English reference of a pair: the partner of the first unclaimed Norwegian link
        with the same target — the same link markup, its own peek the other language (the
        Norwegian face, or for a mentioned Norwegian word its English gloss), inside
        `ordpar-xen` (the sheet keeps it a plain word unless the English stands alone) — or
        the plain word when there is none."""
        uids = self.recorded.get(self.current_target_url)
        if not uids:
            self.en_unmatched += 1
            return visible
        uids.pop(0)
        self.matched += 1
        # as `xref`: a Norwegian word MENTIONED on the English line (`<em>…</em>`, an etymology's
        # "developed from *hus*") is a Norwegian word with an English peek (2026-10-22)
        return _link(self.current_target_url, visible, peek,
                     "en" if visible.startswith("<em>") else "nb", partner=True)

    # --- the replaced control markup -----------------------------------------

    def xref(self, uid, visible, peek, mini_html):
        """`ordbok_gen.xref` as the site draws it since decisions 80: a plain link to the
        target's page (`/bm-en/<id>/`, `#def<N>` included) and its hover peek, each half
        language-tagged; a sentinel peek is simply not drawn. `mini_html` is always empty
        (`MiniShim.render`): the mini is cut from the target's page by the site's mini script.

        On the English line of a pair (`partner_links`) it is the partner word instead."""
        if self.mode == "partner":
            return self._partner(visible, peek)
        if self.mode == "record":
            self.recorded.setdefault(self.current_target_url, []).append(uid)
        self.minis += 1
        skey = self._skey(self.current_target_url)
        # decisions 119: a Norwegian-only unit's link, its peek its target's English
        nb = self._nb_peek(peek)
        if nb is not None:
            return _link(self.current_target_url, visible, nb[0], "en",
                         peek_cls=" ordpar-nbdef" if nb[1] == "sense" else "", skey=skey)
        # `markup._render_link` makes the visible word `<em>…</em>` exactly when the
        # NORWEGIAN side is visible; the peek is then the English gloss, and vice versa.
        return _link(self.current_target_url, visible, peek,
                     "en" if visible.startswith("<em>") else "nb", skey=skey)

    def _skey(self, url):
        """The `snip/` key of the article `url` goes to (site decisions 152), or None."""
        if not getattr(self, "snip_key", None):
            return None
        m = _SITE_HREF.match(url or "")
        return self.snip_key(int(m.group(1))) if m else None

    def xref_hover(self, visible, peek, url):
        """`ordbok_gen.xref_hover`: a link inside a mini. Same markup, but the word points at
        OUR page for the target, in the same tab — the deck sends it to ordbokene because it
        has nowhere else to go; the site has the article."""
        # the deck's second class, `ordbok-xref-hover`, is named by no sheet or script the site
        # serves, so the site leaves it out (2026-10-20, the size report's item 11)
        out = ['<span class="ordbok-xref">',
               '<a class="ordbok-xword" href="%s">%s</a>'
               % (html.escape(_ours(url), quote=True), visible)]
        if peek and peek != SENTINEL:
            out.append('<span class="ordbok-xpeek" lang="%s" data-nosnippet>%s</span>'
                       % ("en" if visible.startswith("<em>") else "nb", peek))
        out.append('</span>')
        return "".join(out)

    def article_url(self, article_id):
        """`ordbok_gen.article_url`: the site's own page. (On the article's own page the
        headword links nowhere — `article.py` renders the header from a row with the id
        removed — so this is the fallback for any other caller.)"""
        return site_url(article_id)


_NOB_HREF = re.compile(r"^/nob/bm/(\d+)(?:#def(\d+))?$")


def _unit(row, defn):
    """The sense or subsense of `row` whose `defn` is `defn`, the first in page order (a sense,
    then its subsenses: `article._unique_sense_ids` keeps the first anchor bare), or None."""
    for sense in row.get("senses") or []:
        if sense.get("defn") == defn:
            return sense
        for sub in sense.get("subs") or []:
            if sub.get("defn") == defn:
                return sub
    return None


def plain_en(text):
    """A stored English segment reduced to the words its page shows: each link its label,
    re-punctuated as the page does (`markup.prose_sep`); a mention's braces dropped."""
    text = markup._LINK_FIND.sub(lambda m: markup.prose_sep(m.group("l")), text or "")
    return text.replace("{", "").replace("}", "").strip()


_SITE_HREF = re.compile(r"^/%s/(\d+)/" % PAIR)


def _link(url, visible, peek, peek_lang, partner=False, peek_cls="", skey=None):
    """One cross-reference as the page carries it (decisions 80): `<span class="ordbok-xref">`
    holding the link and its peek. The visible word's language is the peek's other one (the
    `lang` an inherited one repeats is dropped by `slim.drop_redundant_lang`); a partner word
    (decisions 54) also carries `ordpar-xen`. The peek carries `data-nosnippet` (site decisions
    154, Robin 2026-10-31): a hover label is not page text, and Google glued it to its link in
    its snippets ("kan hendeperhaps, maybe"); the attribute is in the markup itself, since a page
    script may never add it (Google's rule) and the word pages and minis lift this markup whole.
    `skey` (site decisions 152): the target's `snip/` file key, as `data-s` on the link — where
    the hover's first Norwegian definition is read (`mini.js` `nbPeek`)."""
    word_lang = "nb" if peek_lang == "en" else "en"
    out = ['<span class="ordbok-xref%s">' % (" ordpar-xen" if partner else ""),
           '<a class="ordbok-xword" href="%s" lang="%s"%s>%s</a>'
           % (html.escape(url, quote=True), word_lang,
              ' data-s="%s"' % html.escape(skey, quote=True) if skey else "", visible)]
    if peek and not peek.startswith(SENTINEL):
        out.append('<span class="ordbok-xpeek%s" lang="%s" data-nosnippet>%s</span>' % (peek_cls, peek_lang, peek))
    out.append('</span>')
    return "".join(out)


_ORD_HREF = re.compile(r"^(?:https?://[^/]+)?/nob/bm/(\d+)(?:#def(\d+))?$")


def _ours(url):
    """An ordbokene article URL -> the same article on our site; anything else untouched."""
    m = _ORD_HREF.match(url or "")
    if not m:
        return url
    return site_url(int(m.group(1)), int(m.group(2)) if m.group(2) else None)


class MarkupShim(object):
    """Stands in for the `markup` module wherever the deck's renderer takes it as `mk`.

    Only `expand` (it preprocesses, § `SiteFace.preprocess`) and `pair_view` (its Norwegian
    side takes the headline set, § `headline_view`; since 2026-10-22) are our own; everything
    else — `is_see_also`, `MarkupError` — is the module's, untouched.

    `record_links()` and `partner_links()` scope the two lines of a translated line pair
    (`SiteFace.record_links`): the Norwegian line carries the controls and the English
    line's references become partner words matched to them, so each reference is a control
    exactly once (decisions 54).
    """

    def __init__(self, face):
        self._face = face

    def __getattr__(self, name):
        return getattr(markup, name)

    def record_links(self):
        return self._face.record_links()

    def partner_links(self):
        return self._face.partner_links()

    def norwegian_only(self):
        return self._face.norwegian_only()

    def pair_view(self, row, side="en"):
        """`markup.pair_view`, and for the Norwegian side the headline set on the Norwegian
        line's links (`headline_view`, decisions 80's finding 4). The English side is the
        module's, untouched."""
        r = markup.pair_view(row, side)
        return headline_view(r) if side == "no" else r

    def expand(self, text, norwegian=False, hover_only=False, strict=True):
        return markup.expand(self._face.preprocess(text, norwegian, hover_only),
                             norwegian=norwegian, hover_only=hover_only, strict=strict)


def headline_view(row, log=None):
    """`row` (a `pair_view(…, "no")` copy, changed in place and returned) with each derived-
    Norwegian definition, subsense and etymology link's hover title replaced by the target's
    headline set — the deck's rule of 2026-07-22 (`docs/rendering.md` § Norwegian-visible
    hovers: the headline set), extended to the site's Norwegian lines (decisions 80's finding 4,
    Robin 2026-10-22). Until then such a link hovered the citing article's own gloss (the
    parallel English's title, `pair_view` side `no`), while the English line's mention of the
    same target hovered the headline set: *hos* -> *hus* read "house" from one line and "a house
    · a building" from the other.

    The deck's own function does the work (`markup._inject_headlines`, bare links, which calls
    `markup.headline_gloss`), so the rule's exclusions are the deck's: a `#defN` link keeps its
    gloss, a target with no `summary` keeps it, and an untitled link (no English partner: the
    whole of an untranslated page) stays untitled, peekless. The examples' Norwegian is not
    touched (outside the ruling). The deck never calls this: its cards render `pair_view`'s
    English side.

    `log(kind, href, old, new)` is called for each title that changes (the build's count),
    `kind` one of definition / subsense / etymology."""
    def fix(unit, kind):
        segs = unit.get("no")
        if not segs:
            return
        new_segs = []
        for s in segs:
            t = markup._inject_headlines(s, bare=True)
            if log is not None and t != s:
                for (l0, h0, t0), (_l1, _h1, t1) in zip(markup.links(s), markup.links(t)):
                    if t0 != t1:
                        log(kind, h0, t0, t1)
            new_segs.append(t)
        unit["no"] = new_segs

    if row.get("etymology"):
        fix(row["etymology"], "etymology")
    for sense in row.get("senses") or []:
        fix(sense, "definition")
        for sub in sense.get("subs") or []:
            fix(sub, "subsense")
    return row


class MiniShim(object):
    """Installed as `markup.mini`. Since decisions 80 no page carries a mini — the site's mini
    script cuts it from the target's own page — so `render` draws nothing: it records the URL
    the link goes to (`/bm-en/<id>/`, `#def<N>` included), which `markup._render_link` then
    hands to `xref` with the link. Until 2026-10-21 it rendered the target's mini here (both
    languages as line pairs for a translated target, the Norwegian face otherwise) and the
    page inlined it.
    """

    def __init__(self, face):
        self._face = face

    def __getattr__(self, name):
        return getattr(mini, name)

    def render(self, row, gloss, defn=None, xexpand=None, expr_rows=None):
        self._face.current_target_url = site_url(row["id"], defn)
        return ""

    def placeholder(self, href, gloss):
        """Unreachable on a shipped page (an unresolvable target is downgraded to plain text
        before `markup` ever sees it); kept so a non-strict debug run still works."""
        self._face.current_target_url = _ours(href)
        return ""


def lowercase_comp(obj):
    """A copy of ``obj`` with every ``comp`` block's label starting lowercase — "as a suffix in
    words such as:", as every other line on the page and as ordbokene (decisions 47, Robin 2026-10-18:
    render-time, the site only). The stored row keeps the derive layer's capital, and the deck's
    renderers are untouched: the deck inherits this at the switch-over (decisions 49)."""
    if isinstance(obj, list):
        return [lowercase_comp(x) for x in obj]
    if not isinstance(obj, dict):
        return obj
    out = {k: lowercase_comp(v) for k, v in obj.items()}
    if isinstance(obj.get("comp"), list):
        out["comp"] = [lowercase_comp_block(b) for b in obj["comp"]]
    return out


def lowercase_comp_block(blk):
    """One ``comp`` block with its label's first letter lowercased. A list with no intro has no
    label (``""``, decisions 151) and keeps none: the renderers draw it without a label line."""
    if not isinstance(blk, dict):
        return blk
    label = blk.get("label") or ""
    return dict(blk, label=label[:1].lower() + label[1:])


def install(face):
    """Replace the four hooks. Returns the originals, for `restore`."""
    saved = (ordbok_gen.xref, ordbok_gen.xref_hover, ordbok_gen.article_url, markup.mini)
    ordbok_gen.xref = face.xref
    ordbok_gen.xref_hover = face.xref_hover
    ordbok_gen.article_url = face.article_url
    markup.mini = MiniShim(face)
    return saved


def restore(saved):
    ordbok_gen.xref, ordbok_gen.xref_hover, ordbok_gen.article_url, markup.mini = saved
