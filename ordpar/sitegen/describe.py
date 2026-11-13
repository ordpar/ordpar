# -*- coding: utf-8 -*-
"""An article page's `<title>` and `<meta name="description">` for search engines and link
previews (site decisions 128, Robin's picks of 2026-10-25 from the preview lab).

**The title** (`page_title`): "word (class) — Norwegian–English dictionary".

* *word* is the headword line as the page's headline shows it (`build_site.head_lemmas`: every
  spelling, ", " between), WITHOUT the homograph numerals — except where another article with a
  page shares one of the spellings AND the word class: then the numerals stay ("fange I (noun)"),
  so two pages never carry one title (decisions 128, the session's reading). `shared_class`
  decides it.
* *(class)* is the page's own word-class label, the class only (`pos_class`: "noun", not
  "noun (neuter)"); a page with no class (a set phrase as its own page) gets no brackets.
* the second half is the language pair's dictionary name, `strings["dictionary_name"]` — never a
  fixed string here, so a second pair names its own dictionary (Robin, decisions 128).

**The description** (`description`): the lab's template H (`describeF(a, lim, 'bare')` in
`docs/sessions/2026-09-19-ordpar-site-review/evidence/style-lab/preview.html`), capped at
`CAP` characters:

* translated: the summary glosses joined " · ", ". Definition: ", then the page's definition
  lines (`definitions`), numbered "1. …; 2. …" when more than one. The glosses are NEVER cut
  (Robin, decisions 128): whole definitions are dropped from the end (with " …"), then the first
  is cut at a ", " and then at a word (with " …"); with fewer than `MIN_ROOM` characters left for
  it, no definition and no "Definition:" — the glosses alone, with a full stop;
* untranslated: "Not yet in English: " and the Norwegian definition lines the same way;
* a page with no definition lines read: today's description (`fallback`, the glosses or the
  first Norwegian line, `article.meta_description`), unchanged;
* a translated page with no summary gloss (11,810 pages on 2026-10-25; the lab had none):
  "Definition: " and its English definition lines — the template without its glosses, the
  build's call, flagged to the session.

The definition lines are read from the page's own rendered fragment as the lab's harvest read
them from the built page (`preview_harvest.py`): each top-level sense's definition line in the
page's language (English on a translated page, Norwegian on an untranslated one), the hover
peeks left out, the line's `<br>` a space.

**The headword first** (site decisions 154, Robin 2026-10-31, approving "kanskje: perhaps · maybe
…"): given the page's `word` (the headword's first spelling, with its numeral where the title
keeps it: `headword` over the first lemma, `build_site.Builder.page`; the whole list of spellings
left a nine-spelling page no room for its definition), the description opens with it —
Google built its own snippets from the page text instead of our descriptions, and none of them
named the word. The shapes, `CAP` still the whole length (the headword counts):

* translated: "kanskje: perhaps · maybe. Definition: 1. …; 2. …";
* translated, no summary gloss: "hus: 1. …; 2. …" (the headword in place of "Definition: ");
* untranslated: "absurdisme (not yet in English): retning innenfor …";
* no definition lines read: "word: " and today's fallback (none where the fallback is empty).

Without `word` every shape is as before.
"""
import re
from html.parser import HTMLParser

#: The description's length cap (the lab's default, which Robin kept; decisions 128)
CAP = 155
#: Under this many characters left for the first definition's text, none is shown (the lab's rule)
MIN_ROOM = 25
GLOSS_SEP = " · "
UNTRANSLATED_LEAD = "Not yet in English: "
DEF_LEAD = "Definition: "
#: Site decisions 154: after the headword — ": ", or on an untranslated page " (not yet in
#: English): " in place of `UNTRANSLATED_LEAD`
WORD_SEP = ": "
UNTRANSLATED_AFTER = " (not yet in English): "

_BRACKET = re.compile(r"^(.+?) \((.+)\)$")
_NO_CLASS = {"", "fixed expression"}


def pos_class(pos):
    """The word class alone from a site POS label (`article.site_pos`): "noun (neuter)" ->
    "noun", "determiner (quantifier)" -> "determiner", "verb" -> "verb"; a set phrase
    ("fixed expression") or no label -> None."""
    pos = (pos or "").strip()
    if pos in _NO_CLASS:
        return None
    m = _BRACKET.match(pos)
    if m:
        return m.group(1)
    if ", " in pos:
        return pos.split(", ", 1)[0]
    return pos


def headword(lemmas, numerals):
    """The headline's spellings, ", " between, each with its numeral only when `numerals`."""
    return ", ".join(" ".join(x for x in (l.get("form"), l.get("homograph") if numerals else None) if x)
                     for l in lemmas)


def page_title(lemmas, cls, numerals, strings, aid=None):
    """"word (class) — <dictionary name>" (module doc). `lemmas` the headline's `{form,
    homograph}` dicts; `cls` `pos_class`'s answer; `numerals` `shared_class`'s."""
    word = headword(lemmas, numerals) or (str(aid) if aid is not None else "")
    if cls:
        word = "%s (%s)" % (word, cls)
    return "%s — %s" % (word, strings["dictionary_name"])


def shared_class(aid, forms, cls, others_of, class_of):
    """Does another article (with a page) share one of `forms` and the word class `cls`?
    `others_of(form)` -> the ids carrying that spelling; `class_of(id)` -> its `pos_class`
    (None for a set phrase: two set phrases of one spelling share "no class", so they keep their
    numerals too)."""
    for form in forms:
        for other in others_of(form):
            if other != aid and class_of(other) == cls:
                return True
    return False


# --- the definition lines ----------------------------------------------------

# site decisions 152: on a site page the heading is a label pair (`article.label_pair`): the English
# copy, then the Norwegian; without this the harvest found no definitions (the gate on the full build,
# 2026-10-31: *abstrakt* 98 lost its "Definition: …", and pages with no glosses fell back to today's
# text, uncapped)
_SEC = re.compile(r'<h3[^>]*>(?:Senses and Example Sentences|<span class="ordpar-l-en">Senses and Example '
                  r'Sentences</span><span class="ordpar-l-nb"[^>]*>[^<]*</span>)</h3>(.*?)</section>', re.S)


class _Defs(HTMLParser):
    """The definition line of each top-level sense in the first senses list (`ol.ordbok-senses`,
    its `li` with an id `def…`), or a solo sense's first line; in `lang`; peeks left out, `<br>`
    a space. A port of the lab harvest's reader (`preview_harvest.py` `_Defs`)."""

    def __init__(self, lang, solo):
        super().__init__(convert_charrefs=True)
        self.lang, self.solo, self.defs = lang, solo, []
        self.ol, self.done, self.li_open = 0, False, False
        self.cap, self.skip, self.buf = 0, 0, []

    def handle_starttag(self, tag, a):
        a = dict(a)
        cls = a.get("class") or ""
        if self.done:
            return
        if tag == "ol" and "ordbok-senses" in cls and self.ol == 0:
            self.ol = 1
            return
        if tag == "ol" and self.ol:
            self.ol += 1
            return
        if tag == "li" and self.ol == 1 and (a.get("id") or "").startswith("def"):
            self.li_open = True
            return
        if self.cap:
            if tag == "br" and not self.skip:
                self.buf.append(" ")
            if tag == "span":
                self.cap += 1
                if "ordbok-xpeek" in cls or self.skip:
                    self.skip += 1
            return
        if (tag == "span" and "ordbok-def" in cls and a.get("lang", self.lang) == self.lang
                and (self.li_open or (self.solo and not self.defs))):
            self.cap, self.buf = 1, []

    def handle_startendtag(self, tag, a):
        self.handle_starttag(tag, a)      # `<br/>` as `<br>`; no other void tag matters here

    def handle_endtag(self, tag):
        if self.done:
            return
        if self.cap and tag == "span":
            if self.skip:
                self.skip -= 1
            self.cap -= 1
            if self.cap == 0:
                self.defs.append(re.sub(r"\s+", " ", "".join(self.buf)).strip())
                self.li_open = False
            return
        if tag == "ol" and self.ol:
            self.ol -= 1
            if self.ol == 0:
                self.done = True

    def handle_data(self, d):
        if self.cap and not self.skip:
            self.buf.append(d)


def definitions(fragment, translated):
    """The page's definition lines (module doc) from its article fragment or whole page."""
    m = _SEC.search(fragment or "")
    if not m:
        return []
    sec = m.group(1)
    p = _Defs("en" if translated else "nb", 'class="ordbok-senses"' not in sec)
    p.feed(sec)
    p.close()
    return [d for d in p.defs if d]


# --- the description ---------------------------------------------------------

def _finish(s):
    return s.replace("….", "…")


def _cut_item(it, room):
    """One definition cut to `room` characters with " …": at a ", " boundary, then at a word
    (the lab's `cutItem`)."""
    parts, out = it.split(", "), ""
    for p in parts:
        t = out + ", " + p if out else p
        if len(t + " …") > room:
            break
        out = t
    if out and out != it:
        return out + " …"
    out = ""
    for w in it.split(" "):
        t = out + " " + w if out else w
        if len(t + " …") > room:
            break
        out = t
    return (out or it[:max(1, room - 2)]) + " …"


def _stop(text):
    """`text` ending in a full stop, never a second one (no "…." and no ".."), as the lab's
    `finish` keeps one stop."""
    return text if text.endswith((".", "!", "?", "…")) else text + "."


def description(glosses, defs, translated, fallback="", cap=CAP, word=""):
    """The meta description (module doc). `glosses` the summary gloss items, plain; `defs`
    `definitions`'s lines; `fallback` today's description, for a page with no lines read; `word`
    the headword it opens with (site decisions 154), none when empty."""
    n = len(defs)
    if not n:
        return (word + WORD_SEP + fallback) if (word and fallback) else fallback

    def body(k):
        return "; ".join(("%d. " % (i + 1) if n > 1 else "") + x
                         for i, x in enumerate(defs[:k])) + (" …" if k < n else "")

    g = GLOSS_SEP.join(glosses) if translated else ""

    def make(b):
        if not translated:
            return _finish((word + UNTRANSLATED_AFTER if word else UNTRANSLATED_LEAD) + b)
        if not g:
            return _finish((word + WORD_SEP if word else DEF_LEAD) + b)
        return _finish(lead + _stop(g) + " " + DEF_LEAD + b)

    lead = word + WORD_SEP if word else ""

    for k in range(n, 0, -1):
        t = make(body(k))
        if len(t) <= cap:
            return t
    head = make("1. " if n > 1 else "")
    room = cap - len(head)
    if room >= MIN_ROOM:
        return _finish(head + _cut_item(defs[0], room))
    if g:
        return _finish(lead + _stop(g))
    # without glosses the head is at most 23 characters plus the headword (site decisions 154),
    # so this is reached only with a very long headword or a small cap: the first definition cut
    # to what is left, as the lab's untranslated branch
    return _finish(head + _cut_item(defs[0], max(room, 3)))


def plain_glosses(meta_description, has_gloss):
    """The summary gloss items from today's description (`article.meta_description`, the items
    joined " · "), as the lab split it; [] when the page has no summary gloss."""
    return meta_description.split(GLOSS_SEP) if has_gloss and meta_description else []


def home_description(stats, strings):
    """The home page's description (Robin, 2026-10-25), its number written by the build: the
    count of translated articles exactly as the About page states it (`about.numbers`, over
    `site_stats.measure()`'s counts recorded in `build.json`), with its thousands comma."""
    from . import about
    return strings["home_description"].format(translated=about.numbers(stats)["translated"][1])
