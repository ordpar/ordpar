# -*- coding: utf-8 -*-
"""Bokmålsordboka's pronunciation field on the article page (site decisions 123, 2026-10-24).

The field is read from the mirror row (`data["body"]["pronunciation"]`): the library rows do not
carry it. Each entry is `{"type_": "pronunciation", "content": …, "items": […]}`; about 4,900 of
the 5,038 are a plain respelling ("abstrakˊt"), the rest `$` templates whose items are filled in
as the deriver fills every other field (`derive.fill`: a concept id through the concepts table,
a `usage` its text, a `pronunciation_guide` its own content and items).

**As ordbokene's rendered page shows it** (observed 2026-10-24 on ordbokene.no's English pages
*abrodd*, *alibi*, *doctor*, *kompaktor*, *lektor*, *monsieur*, *schizofren*, *schæferhund*,
*snackbar*, *stabilisator*, *akkumulator*, *administrator*, headless Edge, the DOM's text and
classes only): a section labelled "Pronunciation" ("Uttale" in its Norwegian interface) after
the inflection and before the etymology; the respellings verbatim, upright; a
`pronunciation_guide` item in italics (*i flertall*, and the respellings *kompakˊtor* … given
as items); a `grammar` or `entity` item upright ("ubestemt", "flertall", "eller", "tysk");
several entries joined by an italic *eller* — or by ", " where the next entry opens with a
template item (*akkumulator*: "akumulaˊtor, *i fleirtal* akumulaˊtorer *eller* akumulatoˊrer").
Ordbokene's English interface leaves the Norwegian words as they are.

**The words around the respellings** (decisions 123, Robin 2026-10-24): on a Norwegian-only
page always Norwegian; on a translated page in English by default, and in Norwegian under the
`formulas` setting's `no` (decisions 81) — one setting, not a new one, and under its `both` in
English, as the compound-list labels. A translated page carries both halves
(`ordpar-pg-en`, `ordpar-pg-nb` lang="nb"), the sheet picking one (`page.SITE_CSS`). The words
are matched as RUNS: the template items that are words (not respellings), the closed list of
literal words `LITERAL_WORDS` written into the content itself ("lekˊtorer eller lektoˊrer",
"møsjøˊ, flertall mesjøˊ"), and the connectors `CONNECTORS` ("i", "form") between or before
them — so *doctor*'s "i ubestemt form flertall" is one run, "in the indefinite plural". A run's
whole Norwegian text is looked up in `PHRASES`; an entry with a run the table does not hold is
shown in Norwegian everywhere, whole (`STATS["unmatched"]`) — *schæferhund*'s misfiled etymology
("av tysk ‘Schäferhund’ … av *Schaf* ‘sau’") is one, rendered as the data has it.

The note on what the marks mean is the Help page's § Pronunciation (`/help/#pronunciation`,
`ordpar/help.md`; Robin, 2026-10-24: "The notes belongs elsewhere, since it only needs to be read
once"). From 2026-10-24 an article whose field used a mark the note explains also had a "?" beside
the label opening it; removed 2026-11-02, on the site and the deck alike (decisions 123's amendment,
Robin: the "?" "taking unecessary space and attention" once the sound icons were in). The label stays
plain text, as ordbokene's.
"""
import html
import re

from . import deck

#: The section's label, ordbokene's English one (its Norwegian interface: "Uttale"); inside the
#: fragment, so hard-coded as the other section labels (`article.SENSES_LABEL`)
LABEL = "Pronunciation"

#: The concepts table the build uses (`library.mirror_concepts`, set by `build_site.Builder`);
#: None: the deck's own (`derive.concepts_map()`)
CONCEPTS = None

#: What the build counts (`build_site` writes it to `build.json` `pronunciation`)
STATS = {"pages": 0, "translated_pages": 0, "entries": 0, "runs_translated": 0,
         "unmatched": [], "bytes": 0}

#: The English of every run of words in the field (decisions 123), by its Norwegian, whitespace
#: collapsed. The site's own English where it has one: "plural", "indefinite plural" (the
#: inflection table, `inflection.js`), "German" (the authored etymologies' "fra tysk", 753 rows).
PHRASES = {
    "i flertall": "in the plural",
    "i fleirtal": "in the plural",          # Nynorsk, in *akkumulator* (475)
    "i flertal": "in the plural",           # as written in *tabulator* (59524)
    "flertall": "plural",                   # *monsieur* (39009): "møsjøˊ, flertall mesjøˊ"
    "i ubestemt form flertall": "in the indefinite plural",   # *doctor* (10501)
    "eller": "or",
    "el.": "or",                            # *snackbar* (55019) and two more
    "tysk": "German",
}

#: Words written into an entry's content itself (no `$`) that are the field's words, not a
#: respelling: whole words only
LITERAL_WORDS = {"eller", "el.", "flertall"}
#: Words that join a run, never one alone: "i flertall", "i ubestemt form flertall"
CONNECTORS = {"i", "form"}

#: A respelling's stress marks: ˊ ˋ (the modifier letters the data mostly uses), ´ and `
MARKS = "ˊˋ´`"

_TOKEN = re.compile(r"\s+|[^\s]+")
_TRAIL = re.compile(r"^(.*?)([,;:]+)$")


def _concepts():
    return CONCEPTS if CONCEPTS is not None else deck.derive.concepts_map()


def _fill_text(content, items):
    """A `pronunciation_guide`'s text: its content with its own items filled, plain."""
    parts = (content or "").split("$")
    out = [parts[0]]
    for i, part in enumerate(parts[1:]):
        it = items[i] if i < len(items) else {}
        out.append(_item_text(it))
        out.append(part)
    return "".join(out)


def _item_text(item):
    t = item.get("type_")
    if t == "pronunciation_guide":
        return _fill_text(item.get("content"), item.get("items") or [])
    if t == "usage":
        return (item.get("text") or "").strip()
    if isinstance(item.get("id"), str):
        return _concepts().get(item["id"], item["id"])
    return deck.derive.item_marker(item, _concepts(), True)


def _literal(text):
    """Literal content -> tokens: whitespace, and words — a word in `LITERAL_WORDS` (its
    trailing comma, semicolon or colon split off) a word token, the rest plain text."""
    toks = []
    for m in _TOKEN.finditer(text or ""):
        s = m.group(0)
        if s.isspace():
            toks.append(("sp", s, False))
            continue
        word, trail = s, ""
        if word not in LITERAL_WORDS and word not in CONNECTORS:
            tm = _TRAIL.match(word)
            if tm:
                word, trail = tm.group(1), tm.group(2)
        if word in LITERAL_WORDS:
            toks.append(("word", word, False))
        elif word in CONNECTORS:
            toks.append(("conn", word, False))
        else:
            toks.append(("lit", word, False))
        if trail:
            toks.append(("lit", trail, False))
    return toks


def entry_tokens(entry):
    """One entry -> `[(kind, text, italic)]`: kind "lit" (respelling and other text, verbatim),
    "resp" (a respelling given as an item), "word" (the field's words), "conn", "sp"."""
    content = entry.get("content") or ""
    items = entry.get("items") or []
    parts = content.split("$")
    toks = _literal(parts[0])
    for i, part in enumerate(parts[1:]):
        it = items[i] if i < len(items) else {}
        text = _item_text(it)
        italic = it.get("type_") == "pronunciation_guide"
        if italic and any(c in text for c in MARKS):
            toks.append(("resp", text, True))
        elif text.strip():
            toks.append(("word", text, italic))
        elif text:
            toks.append(("sp", text, False))
        toks += _literal(part)
    return toks


def _runs(toks):
    """Group the tokens: `[("run", [tok…]) | tok]`. A run is word tokens with the whitespace
    and connectors between them, a connector before the first included; trailing whitespace
    and connectors stay outside."""
    out, i, n = [], 0, len(toks)

    def next_word(j):
        while j < n and toks[j][0] in ("sp", "conn"):
            j += 1
        return j < n and toks[j][0] == "word"

    while i < n:
        k = toks[i][0]
        if k == "word" or (k == "conn" and next_word(i + 1)):
            run = []
            while i < n and (toks[i][0] == "word"
                             or (toks[i][0] in ("sp", "conn") and next_word(i + 1))):
                run.append(toks[i])
                i += 1
            out.append(("run", run))
        else:
            out.append(toks[i])
            i += 1
    return out


def _tok_html(tok):
    kind, text, italic = tok
    s = html.escape(text, quote=False)
    return "<em>%s</em>" % s if italic and s.strip() else s


def _run_nb(run):
    return " ".join("".join(t[1] for t in run).split())


def entry_html(entry, bilingual):
    """One entry's markup. On a translated page every run in `PHRASES` is a pair of spans; an
    entry with a run the table lacks is Norwegian whole."""
    return tokens_html(entry_tokens(entry), bilingual)


def tokens_html(toks, bilingual):
    """Tokens -> markup, their runs paired on a translated page (`entry_html`)."""
    grouped = _runs(toks)
    known = all(_run_nb(g[1]) in PHRASES for g in grouped if g[0] == "run")
    if bilingual and not known:
        STATS["unmatched"].append(" ".join(_run_nb(g[1]) for g in grouped if g[0] == "run"))
    out = []
    for g in grouped:
        if g[0] != "run":
            out.append(_tok_html(g))
            continue
        nb = "".join(_tok_html(t) for t in g[1])
        if not (bilingual and known):
            out.append(nb)
            continue
        en = html.escape(PHRASES[_run_nb(g[1])], quote=False)
        if any(t[2] for t in g[1]):
            en = "<em>%s</em>" % en
        STATS["runs_translated"] += 1
        out.append('<span class="ordpar-pg-en" lang="en">%s</span>'
                   '<span class="ordpar-pg-nb">%s</span>' % (en, nb))
    return "".join(out)


def entries(data):
    """The mirror row's pronunciation entries (`[]` when none)."""
    return [e for e in (((data or {}).get("body") or {}).get("pronunciation") or [])
            if isinstance(e, dict)]


def body_html(data, bilingual):
    """The field's inner markup: the entries in order, each after its joiner — ", " where the
    entry opens with a template item, else an italic "eller" (a run: "or" on a translated
    page) — as ordbokene's page joins them."""
    out = []
    for i, e in enumerate(entries(data)):
        if i:
            if (e.get("content") or "").lstrip().startswith("$"):
                out.append(", ")
            else:
                out.append(" %s " % tokens_html([("word", "eller", True)], bilingual))
        out.append(entry_html(e, bilingual))
    return "".join(out).strip()


def _all_text(content, items):
    out = [content or ""]
    for it in items or []:
        out.append(_all_text(it.get("content") or it.get("text") or "", it.get("items")))
    return " ".join(out)


def section_html(data, bilingual):
    """The whole section, or "" where the article has no pronunciation. `ordbok-inline` gives
    it the etymology line's look (the label inline before the text); `ordpar-pron` names it, and
    keeps it out of a mini (`mini.js` `senseless`), which shows the senses only."""
    es = entries(data)
    if not es:
        return ""
    body = body_html(data, bilingual)
    if not body:
        return ""
    STATS["pages"] += 1
    STATS["translated_pages"] += 1 if bilingual else 0
    STATS["entries"] += len(es)
    text = "\n".join(['', '  <section class="ordbok-sec ordbok-inline ordpar-pron">',
                      '    <h3 lang="en">%s</h3>' % LABEL,
                      '    <span class="ordbok-body" lang="nb">%s</span>' % body,
                      '  </section>'])
    STATS["bytes"] += len(text.encode("utf-8"))
    return text
