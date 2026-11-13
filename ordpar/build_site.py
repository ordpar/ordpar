#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the public dictionary's static article pages — READ-ONLY (site decisions 27 (1)).

The build joins two sources and writes neither: the **library** (`articles.jsonl`, Norwegian
derived and English authored) and a **mirror snapshot** of every Bokmål article, passed with
`--mirror` and opened read-only. An article is TRANSLATED on the site only when its library
row passes `coverage.complete_strict`; every other article — no row, or a row whose English
is unfinished — is the Norwegian page, derived from the mirror by `derive.derive_row`, with
the not-yet-translated note. Nothing is ever half-English (decisions 2).

Which articles get a page (decisions 46, Robin 2026-10-18): every article the mirror's jsonl
carries — ordbokene's listed articles and the unlisted ones it still serves — plus the KEPT
unlisted articles ordbokene now answers 404 for (translated library rows with no translated
listed namesake, `sitegen.mirror.Listing`), built from the mirror's stored copy or, when that
is empty, from the library row alone. Any other 404'd article gets no page, by `--ids` or
`--all`. An article whose data gives no headword (`lemmas: []`; three in the mirror of
2026-11-03) gets no page either, as ordbokene has none (site decisions 163); a page an earlier
build wrote for one is removed. (Until decisions 63 the credit line linked each article at ordbokene.no, a 404'd kept
one its parent; since then the credit sits in every page's footer and links ordbokene.no.)

A fixed expression the jsonl does not carry and the library has no row for (404'd, or never
mirrored) still shows in its parent's Set phrases block, as on ordbokene: its row is
derived from the whole copy the parent's own data embeds (`library.Store.embedded_expr`,
decisions 57). It gets no page and no search entry, and nothing links to it.

One page per article at its id URL, `out/bm-en/<id>/index.html` (decisions 24). The article
fragment is language-neutral; the chrome around it is English from one strings file. The
paradigm ships as a JSON island for the device to render (`site/inflection.js`); the
cross-references are plain links to the target's page with their hover peek, which the page's
`mini.js` turns into the mini, cut from the fetched target page (site decisions 80, replacing 34's
minis inlined at build time). The build is stamped with the mirror snapshot's date and the library
commit — in `build.json` and on the About page (on every article page too until 2026-10-20).
The About page's numbers are `site_stats.measure()`'s, taken on every build over the rows the
pages are built from and recorded in `build.json` as `site_stats`; its text is `ordpar/about.md`,
the source too of the README in the repository GitHub Pages serves the site from (`sitegen/about.py`,
decisions 63, 2026-10-22).

The size savings of 2026-10-20 (the size report's stages 1 and 2, `sitegen/slim.py`): the
pages' indentation and redundant `lang` attributes go at write time (`page.finish`), the
paradigm island is compact (its shape table, from the mirror, goes into `inflection.js`), and
every script and stylesheet under `out/site/` ships without comments (`write_assets`), with
`/site/theme.js`, `/site/ordpar.css` and `/site/ordpar.js` the article page's three links.

Usage:
    python ordpar/build_site.py --mirror "…/bm-articles.jsonl" --ids 7663 62174   # bru, trøtte
    python ordpar/build_site.py --mirror "…" --all --limit 2000     # a timed pass
    python ordpar/build_site.py --mirror "…" --all                  # the whole dictionary
    python ordpar/build_site.py --mirror "…" --all --audio-names PATH   # with the sound icons

The audio (site decisions 159): `--audio-names` names the list of the recordings' clip names. It is
not in the public repository: Ordpar's own is written before each build by a script outside
`ordpar/`, in its private repository. With it, the build marks each voiced text with a clip
(`data-a`) and writes the names apart, one file per 500 ids (`out/audio/<k>.json`,
`sitegen/audio.py`). This code never reads the audio's own records.

Our corrections to articles with no library row (site decisions 182): the build reads
`review/mirror-corrections.jsonl` in the data folder (`ORDBOK_DATA_DIR`, else the repository root;
`--mirror-corrections` names another file) and applies each row
to the mirror article in memory before anything derives or reads it (`sitegen/overlay.py`); the
mirror file is never written. With no file, or an empty one, the build is as before.

The build writes only under `--out` (default `ordpar/out/`, gitignored).
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ordpar.sitegen import deck, article, face as face_mod, library, mirror as mirror_mod
from ordpar.sitegen import page as page_mod
from ordpar.sitegen import pronunciation
from ordpar.sitegen import colours as colours_mod
from ordpar.sitegen import chrome as chrome_mod
from ordpar.sitegen import slim as slim_mod
from ordpar.sitegen import lemma_order
from ordpar.sitegen import corrections
from ordpar.sitegen import gate as gate_mod
from ordpar.sitegen import overlay as overlay_mod
from ordpar.sitegen import describe
from ordpar.sitegen import head as head_mod
from ordpar.sitegen import audio as audio_mod
from ordpar.sitegen import thanks as thanks_mod
from ordpar.sitegen.strings import EN
from ordpar import build_index as index_mod
from ordpar import site_stats

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = deck.ROOT
ORDPAR = deck.ORDPAR
markup = deck.markup

_CONCEPTLESS = {"article_ref", "quote_inset", "usage", "fraction", "superscript", "subscript"}


# --- small helpers -----------------------------------------------------------

def library_commit(path=None):
    """What the stamp names as the library: this checkout's commit when the build reads the
    committed `articles.jsonl` unchanged; otherwise the file's own git blob id, `file <blob>`,
    which names its content wherever it lives (`--articles` elsewhere, or edited and
    uncommitted; site decisions 64)."""
    def git(*args):
        return subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True)
    try:
        default = os.path.join(ROOT, "articles.jsonl")
        here = path is None or os.path.normcase(os.path.abspath(path)) == os.path.normcase(default)
        if here and git("diff", "--quiet", "HEAD", "--", "articles.jsonl").returncode == 0:
            return git("rev-parse", "--short", "HEAD").stdout.decode().strip() or "unknown"
        blob = git("hash-object", os.path.abspath(path or default)).stdout.decode().strip()
        return ("file " + blob[:9]) if blob else "unknown"
    except OSError:
        return "unknown"


def _shown(path):
    """A path for the build report: relative to the repo where it can be, else absolute
    (`relpath` raises across drives — a `--snippets` on E: crashed the report, 2026-10-20)."""
    try:
        return os.path.relpath(path, ROOT).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path).replace(os.sep, "/")


def gz(text):
    return len(gzip.compress(text.encode("utf-8"), 9, mtime=0))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return len(text.encode("utf-8"))


def walk_concept_ids(node, out):
    """Every concept id in a raw article (`{"id": "norr.", "type_": "entity"}` and kin —
    `derive.item_marker` resolves these against `concepts_map()`, falling back to the id
    itself, so an id the table lacks shows on the page as an unexpanded abbreviation)."""
    if isinstance(node, dict):
        if node.get("type_") not in _CONCEPTLESS and isinstance(node.get("id"), str):
            out.add(node["id"])
        for v in node.values():
            walk_concept_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_concept_ids(v, out)


# --- one page ----------------------------------------------------------------

class Builder(object):
    def __init__(self, store, mirror, stamp, strings=EN):
        self.store = store
        self.mirror = mirror
        self.stamp = stamp
        self.strings = strings
        # decisions 123: the pronunciation field's concept ids through the build's own table
        pronunciation.CONCEPTS = store.concepts
        self.face = face_mod.SiteFace(store)
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        # site decisions 152: every leading link carries its target's `snip/` key (`data-s`)
        self._snip_keys = {}
        self.face.snip_key = self.snip_key
        self.missing_exprs = 0
        self.missing_expr_ids = set()
        self.embedded_expr_ids = set()     # rendered from the parent's copy (decisions 57)
        self.embedded_on_translated = set()   # ... on a translated parent (58)
        self.untranslated_on_translated = {}       # translated page -> its untranslated expressions (58)
        self.changes = {}                  # decisions 106: id -> the notice's [(group, n)]
        # decisions 128: which ids have a page (`Listing.has_page`; main sets it), for the
        # titles' shared-class test, and each id's word class, read once
        self.has_page = lambda _aid: True
        self._classes = {}
        self.shared_class_titles = []      # (id, title): the pages that keep their numerals
        self.descriptions_cut = 0          # descriptions that left a definition out or cut one
        # site decisions 159: the clip names (`audio_mod.Names`, `--audio-names`; None: no audio),
        # each built page's names-file entry, and what the marks did on it
        self.audio = None
        self.audio_entries = {}
        self.audio_counts = {}

    def snip_key(self, aid):
        """The `snip/` file the article `aid` is read from by its first spelling (site decisions
        152): `build_index.snippet_key` of the first headword the index files it under
        (`build_index.entry`, our lemma order), the file a row of it reads (lookup.js
        `snipKey(fold(word))`); else the library row's first lemma; None with neither."""
        if aid not in self._snip_keys:
            heads = index_mod.entry(aid, self.mirror.data(aid) or {})[1]
            if not heads:
                row = self.store.library.get(aid) or {}
                heads = [l.get("form") for l in row.get("lemmas") or [] if l.get("form")]
            self._snip_keys[aid] = index_mod.snippet_key(heads[0]) if heads else None
        return self._snip_keys[aid]

    def word_class(self, aid, root=None, data=None):
        """The page's word class as its headline prints it (`article.lemma_groups`' first
        group's label, `describe.pos_class`): None for a set phrase (decisions 128)."""
        if aid not in self._classes:
            if data is None:
                data = self.mirror.data(aid)
            if root is None:
                root = self.store.library.get(aid) or {}
            groups = article.lemma_groups(root, data)
            self._classes[aid] = describe.pos_class(groups[0][1] if groups else "")
        return self._classes[aid]

    def keeps_numerals(self, aid, data, head, cls):
        """Decisions 128: another page shares a spelling of this one and its word class."""
        if not any(l.get("homograph") for l in head):
            return False
        forms = ([lem.get("lemma") for lem in (data or {}).get("lemmas") or []]
                 or [l.get("form") for l in head])
        return describe.shared_class(
            aid, forms, cls,
            lambda f: [o for o in self.mirror.forms.get(f, ()) if self.has_page(o)],
            self.word_class)

    def close(self):
        face_mod.restore(self.saved)

    def page(self, aid, omit_minis=False, omit_paradigm=False, inline_css=False):
        """The page HTML for one article, plus what the build wants to know about it."""
        root, lib = self.store.page_library(aid)
        if root is None:
            return None
        side, _row = self.store.status(aid)
        self.face.set_library(lib)
        self.face.omit_minis = omit_minis
        self.face.set_page(aid)
        # the Norwegian side through the face: the headline set on its links (decisions 80's
        # finding 4, `face.headline_view`)
        row_no = self.mk.pair_view(root, "no")
        row_en = markup.pair_view(root, "en") if side == "en" else None
        data = self.mirror.data(aid)       # the headword groups come from it either way
        missing = [e for e in (root.get("exprs") or []) if e not in lib]
        self.missing_exprs += len(missing)
        self.missing_expr_ids.update(missing)
        embedded = {e for e in (root.get("exprs") or []) if self.store.is_embedded_only(e)}
        self.embedded_expr_ids |= embedded
        # decisions 58 as amended: an expression with no complete English of its own is shown
        # whole in Norwegian on a translated page (a listed one also keeps its own page)
        untranslated = {e for e in (root.get("exprs") or []) if e in lib and not (
            e in self.store.library
            and library.coverage.complete_strict(self.store.library[e]))}
        if side == "en":
            self.embedded_on_translated |= embedded
            self.untranslated_on_translated[aid] = sorted(untranslated)
        # site decisions 60: what a history / favourites row needs, on the page itself
        snip_text, _snip_lang = article.snippet(row_no, row_en)
        drop = article.dropdown_text(row_no, row_en)
        personal = personal_fields(aid, data, root, snip_text, drop)
        frag = article.fragment(row_no, row_en, lib, self.mk, self.strings, data=data,
                                paradigm=not omit_paradigm, untranslated_exprs=untranslated,
                                see_lines=True,   # decisions 153: a set phrase's own page
                                site=True)        # site decisions 152: the labels' two copies
        # decisions 93 (2): the page's <title>, `data-lemma` and the "N more entries for …" link
        # follow the headword line (the mirror's spellings and numbers, in our order), not the
        # library row, so the title and the line never disagree
        head = head_lemmas(root, data)
        # decisions 127, 128: the title's word class and numerals, and the description
        cls = self.word_class(aid, root, data)
        numerals = self.keeps_numerals(aid, data, head, cls)
        today = article.meta_description(row_no, row_en, self.mk)
        defs = describe.definitions(frag, side == "en")
        glosses = describe.plain_glosses(today, side == "en" and article.snippet_is_gloss(row_no, row_en))
        description = describe.description(
            glosses, defs, side == "en", today,
            # site decisions 154: the headword first — its first spelling only, with its numeral
            # where the title keeps it (a page listing nine spellings left no room for the
            # definition: *strafforfølging*, the first full build)
            word=describe.headword(head[:1], numerals))
        # cut: a definition dropped or shortened, or the glosses alone where definitions were read
        # (since 154 a page with no glosses has no "Definition:" either, so the glosses decide)
        if defs and (" …" in description or glosses and describe.DEF_LEAD not in description):
            self.descriptions_cut += 1
        html_text = page_mod.render(
            aid=aid, lemmas=head, article=frag,
            translated=(side == "en"),
            other_entries=self.mirror.other_entries(aid, [l["form"] for l in head]),
            strings=self.strings,
            stamp=self.stamp, description=description,
            mk=self.mk, inline_css=inline_css, personal=personal,
            change=self.changes.get(aid), pos_class=cls, numerals=numerals)
        if numerals:
            self.shared_class_titles.append((aid, describe.page_title(head, cls, True, self.strings)))
        if self.audio is not None:
            # site decisions 159: a `data-a` mark on each voiced element with a clip, and the
            # article's entry for its names file (`sitegen/audio.py`); after the description and
            # the snippets, which read the rows, so neither can see a mark
            before = len(html_text.encode("utf-8"))
            html_text, entry, counts = audio_mod.mark(
                html_text, aid, self.audio, expr_terms(root, lib))
            counts["bytes"] = len(html_text.encode("utf-8")) - before
            self.audio_entries[aid] = entry
            self.audio_counts[aid] = counts
        return {"html": html_text, "translated": side == "en", "lib": len(lib),
                "minis": self.face.minis, "mini_bytes": self.face.mini_bytes,
                "lemmas": head,
                # site decisions 59: the list view's snippet, for the index build
                "snippet": (snip_text, _snip_lang), "drop": drop,
                # site decisions 116: the snippet is the summary gloss (semibold in the rows)
                "gloss": article.snippet_is_gloss(row_no, row_en),
                # site decisions 152: a translated article's first Norwegian definition
                "nbsnip": article.snippet_nb(row_no) if side == "en" else ""}


#: Entries `ordpar/root/` once held, removed from `out/` by every build (the copy of
#: `ordpar/root/` adds and overwrites, never deletes): the æ ø å check's page (decisions 117,
#: shipped with 130's deploy, removed with the word pages' build)
RETIRED_ROOT = ("test-æøå",)

#: One sitemap file holds at most 50,000 addresses (the sitemaps protocol); past that the build
#: fails and asks for a sitemap index
SITEMAP_MAX = 50000
#: The pages besides the articles that search engines may list (decisions 128); `/thanks/` (166)
#: only while reports are on: `indexed_other()`
INDEXED_OTHER = ("/", "/about/", "/help/", "/coming/", "/more/",   # /coming/ 131, /more/ 142
                 "/changes/", "/dictionary-changes/", "/deck-changes/")   # 175, 177
#: Indexed pages that exist only while the reports' switch is on (site decisions 166,
#: `chrome.REPORT_RECEIVER`): the thanks page
REPORTS_INDEXED = ("/thanks/",)
#: The environment variable that sets the reports' receiver for ONE build (site decisions 166):
#: Robin's look at the form against the receiver's local stand-in, with no committed file changed
#: (`report_receiver_override`; `ordpar/receiver/README.md` § A look build). `deploy.py prepare`
#: refuses a build whose address is not https on a public name.
REPORT_RECEIVER_ENV = "ORDPAR_REPORT_RECEIVER"
#: The environment variable that sets the survey's switch for ONE build (site decisions 173): "1" on,
#: "0" off, unset or empty the committed `chrome.SURVEY` (`survey_override`). The survey goes to the
#: reports' receiver, so with reports off it stays off whatever this says.
SURVEY_ENV = "ORDPAR_SURVEY"


def indexed_other():
    """The pages besides the articles in the sitemap: INDEXED_OTHER, and `/thanks/` while the
    reports' switch is on (site decisions 166)."""
    return INDEXED_OTHER + (REPORTS_INDEXED if chrome_mod.REPORT_RECEIVER else ())


def report_receiver_override(environ=None):
    """The address `ORDPAR_REPORT_RECEIVER` gives for this build, checked
    (`chrome.check_report_receiver`: an http(s) address ending in /report), or None when it is
    unset or empty (the committed switch, `chrome.REPORT_RECEIVER`, then decides). ValueError on a
    malformed one."""
    value = (os.environ if environ is None else environ).get(REPORT_RECEIVER_ENV, "").strip()
    if not value:
        return None
    return chrome_mod.check_report_receiver(value)


def survey_override(environ=None):
    """`ORDPAR_SURVEY` for this build: True ("1"), False ("0"), or None when unset or empty (the
    committed `chrome.SURVEY` decides). ValueError on any other value."""
    value = (os.environ if environ is None else environ).get(SURVEY_ENV, "").strip()
    if not value:
        return None
    if value not in ("0", "1"):
        raise ValueError("%s must be 1 or 0, not %r" % (SURVEY_ENV, value))
    return value == "1"


def write_survey(out, stamp):
    """`/survey/` (site decisions 173): written while the survey is on (`chrome.survey_receiver()`:
    `chrome.SURVEY` and the reports' receiver) — "Ordpar — your first impressions", from
    `ordpar/site/survey.json`; while off, not built, and one an earlier build left is removed.
    -> "written", "removed" or "absent"."""
    path = os.path.join(out, "survey", "index.html")
    if chrome_mod.survey_receiver():
        write(path, page_mod.survey_page(stamp, EN))
        return "written"
    if os.path.exists(path):
        os.remove(path)
        return "removed"
    return "absent"


def privacy_for_build(privacy, receiver, look):
    """Does this build write `/privacy/`? (site decisions 166, 2026-11-05: the report form links the
    page's section on reports, so reports never go out without it) -> (write, note):

    * the privacy page's switch on (`chrome.PRIVACY`): written, whatever else;
    * off, reports off: not written (one an earlier build left is removed);
    * off, reports on from the committed switch (`chrome.REPORT_RECEIVER`): REFUSED (ValueError,
      saying why) — the form would link a page that does not exist;
    * off, reports on for a LOOK build alone (`ORDPAR_REPORT_RECEIVER`, `look`): written for this
      build alone, so Robin can follow the form's link and read the page as it would be published,
      with `note` to print; no footer or About link (those follow the switch), and the next build
      without the override removes it. `deploy.py prepare` refuses such a build anyway (its address)."""
    if privacy:
        return True, None
    if not receiver:
        return False, None
    if look:
        return True, ("privacy: chrome.PRIVACY is off, but this look build has reports on, so "
                      "/privacy/ is written for this build alone (the report form links it); no "
                      "footer or About link, and the next build without %s removes it"
                      % REPORT_RECEIVER_ENV)
    raise ValueError("reports are on (chrome.REPORT_RECEIVER %r) while the privacy page is off "
                     "(chrome.PRIVACY False): the report form links %s, which this build would not "
                     "have. Turn chrome.PRIVACY on once Robin has approved ordpar/privacy.md, or "
                     "empty chrome.REPORT_RECEIVER (site decisions 166)"
                     % (receiver, chrome_mod.PRIVACY_REPORTS_HREF))


def write_thanks(out, stamp, mirror, fixes=None, ideas=None):
    """`/thanks/` (site decisions 166): written while the reports' switch is on — "Thanks to our
    readers", the fixes readers' reports led to, counted now from the committed list
    (`ordpar/reader-fixes.jsonl`, written only by the /reports page), each fix's word from the
    mirror; while off, not built, and one an earlier build left is removed (as 104's privacy page
    and 163's headword-less pages). Since site decisions 183 also readers' ideas, from the committed
    `ordpar/reader-ideas.jsonl` (kept by hand) when `ideas` is None. -> "written", "removed" or
    "absent"."""
    path = os.path.join(out, "thanks", "index.html")
    if chrome_mod.REPORT_RECEIVER:
        write(path, page_mod.thanks_page(stamp, EN, thanks_mod.read_fixes() if fixes is None else fixes,
                                         thanks_mod.mirror_headword(mirror),
                                         ideas=thanks_mod.read_ideas() if ideas is None else ideas))
        return "written"
    if os.path.exists(path):
        os.remove(path)
        return "removed"
    return "absent"
#: The pages besides the untranslated articles that carry `noindex` (decisions 128): the index
#: build's shell pages and, while its switch is on, the privacy page
NOINDEX_OTHER = ("/bm-en/", "/history/", "/favourites/", "/settings/", "/404.html")


def write_sitemap(path, translated_ids, articles_path=None):
    """`/sitemap.xml` (site decisions 128): every INDEXED page's canonical address — the home
    page, About, Help, Coming to Ordpar (decisions 131), More (142), the three change lists (175,
    177), then every translated article page in id order; no `noindex` page, and
    no `<lastmod>` (the build knows no true date per page). `robots.txt` (`ordpar/root/`) names
    it. Since site decisions 117 the index build rewrites it with the word pages and form pages,
    leaving out the article pages whose canonical is now their word page
    (`build_index.write_word_pages`); it reads the article pages listed here from
    `articles_path` (`build_index.SITEMAP_ARTICLES_PATH`, outside `out/`), so a second run of
    the index build lists the same articles. -> {"urls", "bytes"}."""
    if articles_path:
        os.makedirs(os.path.dirname(articles_path), exist_ok=True)
        with open(articles_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(sorted(translated_ids), f)
    urls = [head_mod.SITE_URL + p for p in indexed_other()]
    urls += [page_mod.CANONICAL % aid for aid in sorted(translated_ids)]
    nl = "\n"
    body = ('<?xml version="1.0" encoding="UTF-8"?>' + nl
            + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + nl
            + "".join("<url><loc>%s</loc></url>%s" % (u, nl) for u in urls)
            + "</urlset>" + nl)
    return {"urls": len(urls), "bytes": write(path, body)}


def robots_counts(pages, privacy, sitemap, builder):
    """`build.json`'s `search_128`: the indexed and `noindex` pages counted (decisions 128), the
    sitemap's size, the titles that keep their numerals (a shared spelling and class) and the
    descriptions that left out or cut a definition."""
    tr = sum(1 for _i, g_, _n in pages if g_["translated"])
    untr = len(pages) - tr
    noindex_other = (list(NOINDEX_OTHER) + (["/privacy/"] if privacy else [])
                     + ([chrome_mod.SURVEY_HREF] if chrome_mod.survey_receiver() else []))
    indexed = indexed_other()
    return {"indexed_pages": tr + len(indexed), "indexed_articles": tr,
            "indexed_other": list(indexed),
            "noindex_pages": untr + len(noindex_other), "noindex_articles": untr,
            "noindex_other": noindex_other,
            "sitemap_urls": sitemap["urls"] if sitemap else None,
            "sitemap_bytes": sitemap["bytes"] if sitemap else None,
            "shared_class_titles": len(builder.shared_class_titles),
            "shared_class_title_examples": [t for _a, t in sorted(builder.shared_class_titles)[:40]],
            "descriptions_cut": builder.descriptions_cut}


def remove_page(out, aid):
    """Delete `out/bm-en/<aid>/index.html` (and its folder, once empty) if an earlier build wrote
    it: an article that no longer gets a page (site decisions 163). True if a page was removed."""
    folder = os.path.join(out, face_mod.PAIR, str(aid))
    path = os.path.join(folder, "index.html")
    if not os.path.isfile(path):
        return False
    os.remove(path)
    try:
        os.rmdir(folder)
    except OSError:
        pass
    return True


def head_lemmas(root, data):
    """The headword line's spellings as `{form, homograph}` dicts, in the line's order: every
    paradigm group's forms in turn (`article.lemma_groups` — the mirror's spellings and their
    own numerals, our order where the normalization log rules one; the library row's lemmas
    where the mirror has no data). The page's title, `data-lemma` and the "N more entries"
    link read these (site decisions 93 (2), Robin 2026-10-23: the title follows the line). A
    run of spaces inside a form is one, as the line shows it (13 mirror set phrases carry a
    double space, *sprenge  grenser*; the library rows carry one)."""
    return [{"form": " ".join(f.split()), "homograph": hg}
            for forms, _pos in article.lemma_groups(root, data) for f, hg in forms]


def expr_terms(root, lib):
    """`{term: id}` for the set phrases a page embeds (site decisions 159: a set phrase's texts
    are named as its own article's), from their rows' first lemma; `sitegen/audio.py` `mark`
    reads a block's id from its own anchors first and uses this where a block has none."""
    out = {}
    for e in root.get("exprs") or []:
        row = lib.get(e) if hasattr(lib, "get") else None
        lem = (row or {}).get("lemmas") or []
        form = lem[0].get("form") if lem and isinstance(lem[0], dict) else None
        if form:
            out.setdefault(audio_mod.norm(form), e)
    return out


def audio_report(builder, names, files):
    """`build.json`'s `audio` (site decisions 159): the names file read, what the marks did over
    the pages built, and the names files as they stand in `out/audio/`."""
    if names is None:
        return {"names_file": None, "note": "built without --audio-names: no marks, no names files"}
    tot = {}
    for c in builder.audio_counts.values():
        for k, v in c.items():
            tot[k] = tot.get(k, 0) + v
    return {"names_file": _shown(names.source), "names_header": names.header,
            "names_lines": len(names), "pages": len(builder.audio_counts),
            "pages_marked": sum(1 for c in builder.audio_counts.values() if c.get("bytes")),
            "marks": tot, "files": files}


def personal_fields(aid, data, root, snip_text, drop):
    """The fields `page.personal_attrs` writes (site decisions 60): the homograph number (and
    since decisions 93 the per-spelling numbers where they differ), the word-class code and the headword as the search index computes them (`build_index.entry`,
    `display` — so a history row drawn from the page matches a search row), and the snippet and
    the dropdown text cut as `snip/` cuts them (`build_index.snippet_text`)."""
    _aid, heads, hgnos, pos, _infl, _cells = index_mod.entry(aid, data or {})
    if not pos and root.get("pos_en") == "fixed expression":
        pos = "EXPR"                       # an embedded-only expression, as the index files it
    word = index_mod.display(heads) or ", ".join(
        l.get("form", "") for l in root.get("lemmas") or [])
    # decisions 93: one number every spelling carries, or one per spelling where they differ
    # (`hgs`, the shown spellings'), `hg` then the first non-zero — as the index's `hg_field`
    hg = index_mod.hg_field(hgnos)
    hgs = hg if isinstance(hg, list) else None
    if hgs:
        hg = next((h for h in hgs if h), 0)
    return {"hg": hg, "hgs": hgs,
            "pos": pos, "word": word, "snip": index_mod.snippet_text(snip_text),
            "drop": None if drop is None else index_mod.snippet_text(drop)}


# --- the build ---------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mirror", required=True,
                    help="path to the mirror's bm-articles.jsonl, read only (in the public "
                         "repository: data/bokmalsordboka/bm-articles.jsonl, once joined)")
    ap.add_argument("--ids", type=int, nargs="+", metavar="ID",
                    help="build these article ids")
    ap.add_argument("--all", action="store_true",
                    help="build every article in the mirror, one pass")
    ap.add_argument("--limit", type=int, help="with --all: stop after N articles")
    ap.add_argument("--out", default=os.path.join(ORDPAR, "out"), help="output folder")
    ap.add_argument("--snippets", metavar="PATH",
                    help="where the list view's snippets go for build_index.py (default: "
                         "ordpar/.build/build-snippets.json — outside out/, never published)")
    ap.add_argument("--articles", default=deck.fetch.LIBRARY_PATH,
                    help="the library (default: articles.jsonl at the repository root, or in "
                         "ORDBOK_DATA_DIR when that is set)")
    ap.add_argument("--audio-names", metavar="PATH",
                    help="the list of the recordings' clip names (site decisions 159), read only; "
                         "not in the public repository (Ordpar's own is written by a script of its "
                         "private repository). Without it the pages carry no play buttons, and a "
                         "whole build removes out/audio/")
    ap.add_argument("--mirror-corrections", metavar="PATH", default=overlay_mod.PATH,
                    help="our corrections to articles with no library row (site decisions 182), "
                         "applied to the mirror article in memory; default "
                         "review/mirror-corrections.jsonl in the data folder (ORDBOK_DATA_DIR, else "
                         "the repository root), and a missing file changes nothing")
    ap.add_argument("--measure", action="store_true",
                    help="also report each page's size with the minis and/or the paradigm "
                         "island left out (decisions 24 and 34 asked for these numbers)")
    a = ap.parse_args()
    if not a.ids and not a.all:
        ap.error("give --ids or --all")
    # site decisions 166: the reports' switch — the committed one (`chrome.REPORT_RECEIVER`), or for
    # this build alone the environment's (a look build), set before anything is rendered
    try:
        override = report_receiver_override()
        page_mod.set_report_receiver(override if override is not None else chrome_mod.REPORT_RECEIVER)
    except ValueError as e:
        ap.error(str(e))
    report_source = REPORT_RECEIVER_ENV if override is not None else "chrome.REPORT_RECEIVER"
    # site decisions 173: the survey's switch — the committed one (`chrome.SURVEY`), or this build's
    # (`ORDPAR_SURVEY`); on only with reports on (it goes to the same receiver)
    try:
        survey_env = survey_override()
    except ValueError as e:
        ap.error(str(e))
    if survey_env is not None:
        page_mod.set_survey(survey_env)
    survey_source = SURVEY_ENV if survey_env is not None else "chrome.SURVEY"
    print("survey: %s" % (("ON, receiver %s (%s)" % (chrome_mod.survey_receiver(), survey_source))
                          if chrome_mod.survey_receiver() else
                          "off (%s%s)" % (survey_source, "" if chrome_mod.SURVEY else " False")))
    if override is not None:
        print("reports: ON for this build only, receiver %s (from %s) — a look build: deploy.py "
              "prepare refuses it unless the address is https on a public name"
              % (override, REPORT_RECEIVER_ENV))
    else:
        print("reports: %s" % (("ON, receiver " + chrome_mod.REPORT_RECEIVER)
                               if chrome_mod.REPORT_RECEIVER else "off (chrome.REPORT_RECEIVER empty)"))
    # site decisions 166 (2026-11-05): reports need the privacy page (the form links it); a look
    # build gets the page for itself alone (`privacy_for_build`)
    try:
        privacy_build, privacy_note = privacy_for_build(chrome_mod.PRIVACY, chrome_mod.REPORT_RECEIVER,
                                                        override is not None)
    except ValueError as e:
        ap.error(str(e))
    counting = chrome_mod.counting()
    print("privacy page: %s; counting: %s" % (
        "ON (chrome.PRIVACY)" if chrome_mod.PRIVACY else
        ("for this look build only" if privacy_build else "off (chrome.PRIVACY)"),
        "ON (events.js RECEIVER set)" if counting else "off (events.js RECEIVER empty)"))
    if privacy_note:
        print(privacy_note)

    t0 = time.perf_counter()
    rows = deck.store.read_jsonl(a.articles)
    # the render gate (entry 38), as the deck build: `triage.publishable` where the private
    # pipeline is here, else the export's marker beside the library (decisions 184, `sitegen/gate.py`)
    try:
        rows, held, gated_by = gate_mod.apply(rows, a.articles)
    except gate_mod.Refused as e:
        ap.error(str(e))
    if held:
        print("holding %d unverified added sentence(s) off the pages" % held)
    if gated_by != "triage.publishable":
        print("example gate: %s" % gated_by)
    t_lib = time.perf_counter() - t0

    t0 = time.perf_counter()
    mirror = mirror_mod.Mirror(a.mirror)
    n_mirror = mirror.index()
    t_index = time.perf_counter() - t0
    print("mirror: %d articles indexed in %.1f s; library: %d rows"
          % (n_mirror, t_index, len(rows)))

    store = library.Store(mirror, rows)

    # site decisions 182: the handover's corrections to articles with no library row, decided
    # against the raw mirror and applied by `mirror.data` from here on (nothing reads an article
    # before this line but the index pass, which reads only headwords and paradigms)
    t0 = time.perf_counter()
    overlay = mirror.set_overlay(overlay_mod.Overlay.load(
        a.mirror_corrections, library_ids=store.library, kinds=set(corrections.KIND_GROUP)))
    if overlay:
        oc = overlay.summary()["counts"]
        print("decisions 182: %d mirror correction(s) in %s: %s; %.1f s"
              % (len(overlay.rows), _shown(a.mirror_corrections),
                 ", ".join("%d %s" % (n, v) for v, n in oc.items() if n),
                 time.perf_counter() - t0))
    else:
        overlay = overlay_mod.Overlay(path=a.mirror_corrections)

    # decisions 46: which unlisted articles the site keeps, and the 404'd ones' sources
    listing = mirror_mod.Listing(a.mirror)
    translated = {i for i, r in store.library.items() if library.coverage.complete_strict(r)}
    embedded = mirror_mod.decide_kept(
        listing, a.mirror, store.library, translated, mirror.forms,
        lambda i: ([l.get("lemma") for l in (mirror.data(i) or {}).get("lemmas") or []]
                   if i in mirror else []))
    # how each 404'd kept page is sourced (decisions 46; the per-article credit links that
    # used `embedded` went with decisions 63)
    sourced = {"stored_copy": 0, "library_row_only": 0}
    for aid in listing.kept_404():
        mirror.stored[aid] = listing.stored_copy(aid)
        sourced["stored_copy" if mirror.stored[aid] else "library_row_only"] += 1
    # the compact islands' site-wide shape table (the size report's item 9c): every paradigm the
    # mirror and the stored copies hold — the same table for any run on the same snapshot, a
    # `--ids` run included — fixed before the first page, since it is part of `inflection.js`
    # and so of every page's `?v=` for `/site/ordpar.js`
    shapes = dict(mirror.shapes)
    for aid in listing.kept_404():
        slim_mod.compact_paradigm(mirror.stored.get(aid), shapes)
    page_mod.set_shapes(shapes)
    c46 = listing.counts()
    print("decisions 46: %s listed; unlisted %d served + %d 404; kept %d (%d served, %d 404: "
          "%d from a stored copy, %d from the library row alone); %d left out of search"
          % (c46["listed"], c46["unlisted_served"], c46["unlisted_404"], c46["kept"],
             c46["kept_served"], c46["kept_404"], sourced["stored_copy"],
             sourced["library_row_only"], c46["left_out_of_search"]))
    stamp_date = mirror_mod.snapshot_stamp(a.mirror) or "unknown"
    commit = library_commit(a.articles)
    stamp = ("ordpar build: mirror snapshot %s · library %s" % (stamp_date, commit))

    ids = a.ids
    if a.all:
        ids = sorted(set(mirror.ids()) | set(listing.kept_404()))
        if a.limit:
            ids = ids[:a.limit]

    # decisions 106: every live correction in the normalization log checked against the page's
    # Norwegian and the mirror's — over the whole log, whatever this run builds
    # site decisions 163 (Robin, 2026-11-04): an article with no headword gets no page either —
    # none in the mirror's data and none in a library row (*på tide* 131994, *til topps*, *til
    # vanns*: `lemmas: []` in the jsonl, their translated rows give the line; they keep pages)
    def has_headword(aid):
        if mirror.has_headword(aid):
            return True
        return any(isinstance(l, dict) and isinstance(l.get("form"), str) and l["form"].strip()
                   for l in (store.library.get(aid) or {}).get("lemmas") or [])

    # A page is one `--all` writes: an article the mirror carries, or a kept 404 (decisions 46).
    # `listing.has_page` alone says yes to any id it never heard of — a library row ordbokene
    # neither lists nor unlists (*lufte ut* 122112, the deck batch of 2026-11-06) — and the
    # renderer then linked a page nobody writes (2026-11-08, `test_ordpar_links`).
    def has_page(aid):
        return ((aid in mirror or aid in listing.kept)
                and listing.has_page(aid) and has_headword(aid))

    checker = corrections.Checker(store, has_page=has_page, overlay_rows=overlay.applied_rows())
    changes = checker.summary()
    print("decisions 106: %d live corrections; %d shown on %d pages; %d fixed upstream, %d not "
          "on the page, %d invisible, %d unconfirmed"
          % (changes["live_rows"], changes["shown"], changes["articles"],
             len(changes["upstream"]), len(changes["not_shown"]), len(changes["invisible"]),
             len(changes["unconfirmed"])))

    b = Builder(store, mirror, stamp)
    b.has_page = has_page
    b.face.has_page = has_page   # a cross-reference to an article with no page stays plain text
    b.changes = checker.notice
    # site decisions 159: the clip names, read once (a missing key means no button)
    names = None
    if a.audio_names:
        t0 = time.perf_counter()
        names = audio_mod.Names.read(a.audio_names)
        b.audio = names
        print("audio names: %d lines read from %s in %.1f s"
              % (len(names), _shown(a.audio_names), time.perf_counter() - t0))
    else:
        print("note: no --audio-names: the pages get no play buttons (site decisions 159)")
    pages, failures, sizes, refused = [], [], {}, []
    headless, headless_removed = [], []
    concepts_seen, t_render = set(), time.perf_counter()
    for aid in ids:
        if not listing.has_page(aid):
            # decisions 46: ordbokene 404s it and the site does not keep it — no page
            refused.append(aid)
            failures.append((aid, "unlisted and 404 at ordbokene, not kept (decisions 46): "
                                  "no page"))
            continue
        if not has_headword(aid):
            # site decisions 163: no headword in the data, no page (ordbokene's own answers
            # "500: Error"); a page an earlier build wrote is removed, so neither the offline
            # copy (which packs every page in out/) nor a deploy carries it
            headless.append(aid)
            if remove_page(a.out, aid):
                headless_removed.append(aid)
            continue
        try:
            got = b.page(aid)
        except Exception as e:                      # never lose the whole run to one article
            failures.append((aid, "%s: %s" % (type(e).__name__, e)))
            continue
        if got is None:
            failures.append((aid, "no row (mirror miss or DeriveError)"))
            continue
        path = os.path.join(a.out, face_mod.PAIR, str(aid), "index.html")
        n = write(path, got["html"])
        pages.append((aid, got, n))
        data = mirror.data(aid)
        if data is not None:
            walk_concept_ids(data, concepts_seen)
        if a.measure:
            sizes[aid] = measure(b, aid, got["html"])
    t_render = time.perf_counter() - t_render
    new_shapes = sorted(set(article.SHAPES) - set(shapes))
    if new_shapes:
        # cannot happen while every page's data is the mirror's or a stored copy; were it to,
        # those pages' tables would not render (the shipped inflection.js lacks the shapes)
        failures.append((0, "paradigm shape(s) %s met after inflection.js was hashed"
                            % ", ".join(new_shapes)))

    # --- the site folder, the strings, the front door, the stamp -------------
    site_src = os.path.join(ORDPAR, "site")
    if os.path.isdir(site_src):
        shutil.copytree(site_src, os.path.join(a.out, "site"), dirs_exist_ok=True)
        print("copied ordpar/site/ -> out/site/")
    # decisions 61: the files that must sit at the site's root — the service worker (scope `/`)
    # and the app manifest; the icons ride with ordpar/site/ (`site/icons/`)
    root_src = os.path.join(ORDPAR, "root")
    if os.path.isdir(root_src):
        shutil.copytree(root_src, a.out, dirs_exist_ok=True)
        print("copied ordpar/root/ -> out/")
    # what `ordpar/root/` once held and no longer does: the copy above never deletes, and
    # `deploy.py` publishes every entry of `out/` but its EXCLUDE, so a retired entry goes here
    for name in RETIRED_ROOT:
        stale = os.path.join(a.out, name)
        if os.path.isdir(stale):
            shutil.rmtree(stale)
            print("removed out/%s (retired from ordpar/root/)" % name)
        elif os.path.exists(stale):
            os.remove(stale)
            print("removed out/%s (retired from ordpar/root/)" % name)
        write_manifest_colours(os.path.join(a.out, "manifest.webmanifest"))
    assets = write_assets(a.out)
    print("scripts and stylesheets without comments: %d files, %d -> %d bytes; "
          "/site/ordpar.css %d, /site/ordpar.js %d bytes"
          % (assets["files"], assets["source_bytes"], assets["shipped_bytes"],
             assets["ordpar.css"], assets["ordpar.js"]))
    write_strings(os.path.join(a.out, "site", "strings", "en.json"))
    # the About page the credit in every page's footer points at (decisions 32, 12, 63), its
    # numbers measured now, over the rows the pages were built from (decisions 63, 2026-10-22)
    t0 = time.perf_counter()
    stats = site_stats.measure(a.mirror, rows=rows, overlay=mirror.overlay)
    # decisions 106 (Robin 2026-10-23): the About page's list of changes, counted by the same
    # checker as the notices and dated by the snapshot they were checked against
    stats["corrections"] = {"about": changes["about"], "other": changes["other_groups"],
                            "articles": changes["articles"]}
    stats["snapshot"] = stamp_date
    print("site_stats: %d shown articles, %d translated (%d complete); %d added sentences in "
          "%d articles; %.1f s" % (stats["articles"]["all"], stats["articles"]["translated"],
                                   stats["articles"]["complete"], stats["added"]["sentences"],
                                   stats["added"]["articles"], time.perf_counter() - t0))
    write(os.path.join(a.out, "about", "index.html"), page_mod.about_page(stamp, EN, stats))
    # decisions 123 as amended (Robin, 2026-10-24): the Help page, where the note on the
    # pronunciation marks lives instead of the articles
    write(os.path.join(a.out, "help", "index.html"), page_mod.help_page(stamp, EN))
    # site decisions 131 (2026-10-25): "Coming to Ordpar", what is decided and what each waits for
    write(os.path.join(a.out, "coming", "index.html"), page_mod.coming_page(stamp, EN))
    # site decisions 142 (Robin, 2026-10-26/27): "More ways to use Ordpar", the Definer pop-up, the
    # Anki deck and the offline copy
    write(os.path.join(a.out, "more", "index.html"), page_mod.more_page(stamp, EN))
    # site decisions 175 and 177 (Robin, 2026-11-07): the three change lists as public pages, built
    # from their files as /coming/ is from coming.md — the site's, the dictionary's, the Anki decks'
    write(os.path.join(a.out, "changes", "index.html"), page_mod.changes_page(stamp, EN))
    write(os.path.join(a.out, "dictionary-changes", "index.html"), page_mod.library_changes_page(stamp, EN))
    write(os.path.join(a.out, "deck-changes", "index.html"), page_mod.deck_changes_page(stamp, EN))
    # site decisions 166 (Robin, 2026-11-05): "Thanks to our readers", only while reports are on
    # (`write_thanks`; the list `thanks_mod.read_fixes()`, each fix's word from the mirror)
    thanks_state = write_thanks(a.out, stamp, mirror)
    # site decisions 173 (Robin, 2026-11-07): the readers' survey, only while it is on (`write_survey`)
    survey_state = write_survey(a.out, stamp)
    if survey_state == "removed":
        print("survey off: removed out/survey/ (an earlier build's)")
    if thanks_state == "removed":
        print("reports off: removed out/thanks/ (an earlier build's)")
    # site decisions 104: the privacy page, only while its switch is on (`chrome.PRIVACY`; the
    # build stops on a placeholder left in `privacy.md`) or for a look build with reports on (166,
    # `privacy_for_build`); one an earlier build left is removed. Its `[if counting]` and
    # `[if reports]` follow the switches (`about.privacy_page`)
    privacy_out = os.path.join(a.out, "privacy", "index.html")
    privacy_state = "absent"
    if privacy_build:
        write(privacy_out, page_mod.privacy_page(stamp, EN))
        privacy_state = "written"
    elif os.path.exists(privacy_out):
        os.remove(privacy_out)
        privacy_state = "removed"
    if pages:
        # the real front door is build C's; ours is only for a browser check, and it is
        # written only when nothing is there
        front = os.path.join(a.out, "index.html")
        if os.path.exists(front):
            print("note: out/index.html exists already — left alone")
        else:
            write(front, page_mod.index_page(
                [(aid, ", ".join(l.get("form", "") for l in got["lemmas"]))
                 for aid, got, _n in pages], stamp, EN))

    snippets_written = write_snippets(a.snippets or SNIPPETS_PATH, pages,
                                      replace=a.all and not a.limit)
    # site decisions 159: the names files, one per 500 ids (`out/audio/<k>.json`); a whole build
    # without names leaves none, so no stale file names clips for pages that carry no marks
    audio_files = None
    if names is not None:
        audio_files = audio_mod.write_files(
            a.out, {aid: b.audio_entries.get(aid, {}) for aid, _g, _n in pages},
            replace=a.all and not a.limit)
        print("audio: %d names files, %d bytes (%d gzipped), %d articles"
              % (audio_files["files"], audio_files["bytes"], audio_files["gzip"],
                 audio_files["articles"]))
    elif a.all and not a.limit and os.path.isdir(os.path.join(a.out, audio_mod.FOLDER)):
        shutil.rmtree(os.path.join(a.out, audio_mod.FOLDER))
        print("removed out/%s/ (built without --audio-names)" % audio_mod.FOLDER)
    # decisions 128: the sitemap of the indexed pages — written only by a whole build, which
    # knows every translated page (a `--ids` or `--limit` run leaves the last one alone)
    sitemap = None
    if a.all and not a.limit:
        sitemap = write_sitemap(os.path.join(a.out, "sitemap.xml"),
                                [aid for aid, g_, _n in pages if g_["translated"]],
                                index_mod.SITEMAP_ARTICLES_PATH)
        if sitemap["urls"] > SITEMAP_MAX:
            failures.append((0, "sitemap.xml holds %d addresses, over the %d one file may hold: "
                                "split it into a sitemap index" % (sitemap["urls"], SITEMAP_MAX)))

    unknown = sorted(c for c in concepts_seen if c not in store.concepts)
    adv = {}
    for tag, _msg in store.advisories:
        adv[tag] = adv.get(tag, 0) + 1
    report = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mirror": os.path.abspath(a.mirror).replace("\\", "/"),
        "mirror_snapshot": stamp_date,
        "library_commit": commit,
        # the build stamp: on the About page and here since 2026-10-20 (no longer on every
        # article page — the size report's item 2); `build_offline.py` puts it in its manifest
        "stamp": stamp,
        "paradigm_shapes": len(shapes),
        "assets": assets,
        "library_rows": len(rows), "mirror_articles": n_mirror,
        "pages": len(pages),
        "translated": sum(1 for _i, g_, _n in pages if g_["translated"]),
        "untranslated": sum(1 for _i, g_, _n in pages if not g_["translated"]),
        "held_added_examples": held,
        # decisions 63: the About page's and the README's numbers (`site_stats.measure()`);
        # `deploy.py` reads them back for the README
        "site_stats": stats,
        # decisions 46: listed / unlisted / kept, and how the 404'd kept pages were sourced
        "unlisted_46": dict(c46, kept_404_source=sourced,
                            displaced=dict((str(k), v) for k, v in
                                           sorted(listing.displaced.items())),
                            kept_ids=sorted(listing.kept),
                            refused_ids=refused,
                            kept_pages_built=sum(1 for i, _g, _n in pages
                                                 if i in listing.kept)),
        # site decisions 163: the articles with no headword, given no page, and those of them
        # whose page an earlier build had written, removed now
        "no_headword_163": {"ids": headless, "pages_removed": headless_removed},
        # decisions 127, 128: what search engines may list and what a link preview shows
        "search_128": robots_counts(pages, privacy_build, sitemap, b),
        # site decisions 166: the reports' switch this build was made with — the address written
        # into report.js and both bundles ("" off), where it came from, and /thanks/;
        # `deploy.py prepare` refuses an address that is not https on a public name
        "reports_166": {"receiver": chrome_mod.REPORT_RECEIVER, "source": report_source,
                        "thanks": thanks_state},
        # site decisions 173: the survey's switch this build was made with — the address written
        # into survey.js ("" off), where the switch came from, and /survey/
        "survey_173": {"receiver": chrome_mod.survey_receiver(), "source": survey_source,
                       "page": survey_state},
        # site decisions 166 (2026-11-05): the privacy page's switch, the page as this build left it
        # ("written", "removed", "absent"), and the counting (`events.js` RECEIVER), which decides
        # its `[if counting]` and the stats setting; `deploy.py prepare` refuses reports on with no
        # /privacy/
        "privacy_166": {"switch": bool(chrome_mod.PRIVACY), "page": privacy_state,
                        "counting": counting},
        "failures": failures[:50], "failure_count": len(failures),
        "derive": {"rows_derived": store.derived_count,
                   "seconds": round(store.derive_seconds, 2),
                   "errors": dict(store.errors), "error_count": sum(store.errors.values()),
                   "error_ids": store.error_ids[:50]},
        "advisories": adv,
        "concepts_source": os.path.abspath(store.concepts_source).replace("\\", "/"),
        "concepts_codes": len(store.concepts),
        "concept_ids_seen": len(concepts_seen),
        "concept_ids_missing": unknown,
        # decisions 123: the pronunciation field — pages showing it, entries, the runs of words
        # put into English on translated pages, the ones left Norwegian (`PHRASES` lacks them)
        # and the section's bytes over all pages
        "pronunciation": dict(pronunciation.STATS,
                              unmatched=sorted(set(pronunciation.STATS["unmatched"]))),
        # decisions 93 (2): the pages whose headword line the normalization log reorders
        "lemma_order": {"applied": sorted(lemma_order.applied),
                        "unmatched": sorted(lemma_order.unmatched)},
        # decisions 106: the change notice — its articles, its counts, and every live correction
        # that makes none (fixed upstream, not on the page, invisible, unconfirmed)
        "change_notice": dict(changes, pages_built=sum(1 for i, _g, _n in pages
                                                       if i in checker.notice)),
        # site decisions 182: the handover's corrections to articles with no library row — the
        # file, the counts by verdict, and every row not applied with its verdict and why
        "mirror_corrections": overlay.summary(),
        "cross_references": {"minis": sum(g_["minis"] for _i, g_, _n in pages),
                             "mini_bytes": sum(g_["mini_bytes"] for _i, g_, _n in pages),
                             "downgraded_unresolvable": b.face.downgraded,
                             "peekless": b.face.peekless,
                             # decisions 119: a Norwegian-only unit's links given their
                             # target's English, by kind (bare: the summary glosses; sense:
                             # the targeted sense's definition line)
                             "nb_target_english": dict(b.face.nb_counts),
                             # decisions 54: the line pairs' references, Norwegian control
                             # to English partner word, matched by target in order
                             "pair_matched": b.face.matched,
                             "pair_unmatched_norwegian": b.face.no_unmatched,
                             "pair_unmatched_english": b.face.en_unmatched,
                             "missing_expression_rows": b.missing_exprs,
                             "missing_expression_ids": sorted(b.missing_expr_ids)[:50],
                             # decisions 57: no row of their own, built from the parent's copy
                             "expressions_from_parent_copy": len(b.embedded_expr_ids),
                             "expressions_from_parent_copy_ids":
                                 sorted(b.embedded_expr_ids),
                             "expressions_from_parent_copy_on_translated_ids":
                                 sorted(b.embedded_on_translated),
                             # decisions 58 as amended: untranslated expressions
                             # shown in Norwegian on translated pages
                             "untranslated_expressions_in_norwegian": sum(
                                 len(v) for v in b.untranslated_on_translated.values()),
                             "translated_pages_with_untranslated_expressions": sum(
                                 1 for v in b.untranslated_on_translated.values() if v)},
        "timings": {"library_load": round(t_lib, 2), "mirror_index": round(t_index, 2),
                    "build": round(t_render, 2),
                    "pages_per_second": round(len(pages) / t_render, 1) if t_render else None},
        "bytes": {"html_total": sum(n for _i, _g, n in pages)},
        # site decisions 59: the list view's snippets, read by build_index.py
        "snippets": snippets_written,
        # site decisions 159: the clip names, the marks and the names files
        "audio": audio_report(b, names, audio_files),
    }
    if sizes:
        report["sizes"] = sizes
    write(os.path.join(a.out, "build.json"),
          json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    b.close()
    mirror.close()

    print("\nbuilt %d page(s) in %.2f s (%.1f/s); %d failure(s), %d derive error(s)"
          % (len(pages), t_render, len(pages) / t_render if t_render else 0,
             len(failures), sum(store.errors.values())))
    if headless:
        print("site decisions 163: %d article(s) with no headword given no page (%s)%s"
              % (len(headless), ", ".join(str(i) for i in headless[:20]),
                 "; removed the page an earlier build wrote for %s"
                 % ", ".join(str(i) for i in headless_removed) if headless_removed else ""))
    if b.missing_expr_ids:
        print("WARNING: %d expression row(s) cited by a parent are absent from the mirror "
              "and were left out of its Fixed expressions block: %s"
              % (b.missing_exprs, ", ".join(str(i) for i in sorted(b.missing_expr_ids)[:20])))
    if b.embedded_expr_ids:
        print("%d expression(s) with no row of their own rendered from the copy their parent "
              "embeds (no page, no search entry)" % len(b.embedded_expr_ids))
    print("derived %d row(s) in %.2f s; advisories %s; concept ids missing from the table: %d"
          % (store.derived_count, store.derive_seconds, adv or "none", len(unknown)))
    print("line-pair references: %d matched, %d Norwegian and %d English unmatched"
          % (b.face.matched, b.face.no_unmatched, b.face.en_unmatched))
    for aid, got, n in pages[:8]:
        print("  %-7d %-22s %s  %6d B (%5d gz)  %d mini(s)"
              % (aid, ", ".join(l.get("form", "") for l in got["lemmas"]),
                 "en" if got["translated"] else "no", n, gz(got["html"]), got["minis"]))
    print("out: %s" % os.path.abspath(a.out))


#: The list view's snippets (site decisions 59), one per page built: `{"<id>": [text, lang]}`,
#: `[text, lang, drop]` with a set phrase's box (60), `[text, lang, drop|null, 1]` where the
#: snippet is the summary gloss (116), uncut. Not served — `build_index.py` reads it, cuts each to one line and ships it in the
#: index (`lookup-index.md` § 3). A build by-product, so it lives OUTSIDE `out/` (the folder
#: that gets published), in the gitignored `ordpar/.build/` (2026-10-19, site decisions 59);
#: `build_index.py` `SNIPPETS_PATH` is the same path, and `--snippets` overrides it in both.
SNIPPETS = "build-snippets.json"
SNIPPETS_PATH = os.path.join(ORDPAR, ".build", SNIPPETS)


def write_snippets(path, pages, replace):
    """Write the snippets of `pages`. A full `--all` run replaces the file; a partial run
    (`--ids`, or `--all --limit`) updates the entries it built and keeps the rest."""
    snippets = {}
    if not replace and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                snippets = json.load(f)
        except ValueError:
            snippets = {}
    for aid, got, _n in pages:
        text, lang = got["snippet"]
        # site decisions 60, item 7(b) as amended: a third element where the autocomplete's
        # text is not the snippet's first unit (a translated set phrase with no gloss)
        snippets[str(aid)] = [text, lang] if got.get("drop") is None else [text, lang, got["drop"]]
        # site decisions 116: a fourth element, 1, where the snippet is the summary gloss (a
        # set phrase's box, the third, is only ever there where it is not)
        if got.get("gloss"):
            snippets[str(aid)] = [text, lang, got.get("drop"), 1]
        # site decisions 152: a fifth element, a translated article's first Norwegian definition
        # (uncut; `build_index.snippet_files` cuts it into the `snip/` files' "_n")
        if got.get("nbsnip"):
            v = snippets[str(aid)]
            v += [None, 0][len(v) - 2:] if len(v) < 4 else []
            snippets[str(aid)] = v[:4] + [got["nbsnip"]]
    write(path, json.dumps(snippets, ensure_ascii=False, separators=(",", ":"),
                           sort_keys=True) + "\n")
    return {"file": _shown(path) if os.path.isabs(path)
            else path, "entries": len(snippets),
            "empty": sum(1 for v in snippets.values() if not v[0]),
            "english": sum(1 for v in snippets.values() if v[1] == "en")}


def write_assets(out):
    """Every script and stylesheet under `out/site/` as the site serves it (`page.shipped`):
    the copied `ordpar/site/` files stripped of their comments in place (decisions 61, Robin
    2026-10-20: "the published scripts and stylesheets ship without comments"), the generated
    ones (`page.GENERATED`: `article.css`, `page.css`, `article.js`, `theme.js` and the combined
    `ordpar.css` / `ordpar.js` / `shell-pages.css` / `shell-pages.js`) written, and the service
    worker at the root stripped too. The pages' `?v=` hashes are of exactly these bytes."""
    site = os.path.join(out, "site")
    urls = set(page_mod.GENERATED)
    for root, _dirs, names in os.walk(site):
        for n in names:
            if n.endswith((".js", ".css")):
                rel = os.path.relpath(os.path.join(root, n), site).replace(os.sep, "/")
                urls.add("/site/" + rel)
    src_bytes = shipped_bytes = 0
    for url in sorted(urls):
        text = page_mod.shipped(url)
        if url not in page_mod.COMBINED:
            src_bytes += len(page_mod.source(url).encode("utf-8"))
            shipped_bytes += len(text.encode("utf-8"))
        write(os.path.join(site, url[len("/site/"):]), text)
    # decisions 61's leftover (built with 117): the shell pages' sources, copied to `out/site/`
    # with the rest of `ordpar/site/` and published there, without their comments too
    for n in sorted(os.listdir(site)):
        if n.endswith(".html"):
            src = os.path.join(ORDPAR, "site", n)
            if os.path.exists(src):
                with open(src, encoding="utf-8") as f:
                    write(os.path.join(site, n), slim_mod.strip_html(f.read()))
    sw_src = os.path.join(ORDPAR, "root", "sw.js")
    if os.path.exists(sw_src):
        with open(sw_src, encoding="utf-8") as f:
            sw = f.read()
        src_bytes += len(sw.encode("utf-8"))
        shipped_bytes += write(os.path.join(out, "sw.js"), slim_mod.strip_js(sw).lstrip("\n"))
    return {"files": len(urls) - len(page_mod.COMBINED) + 1, "source_bytes": src_bytes,
            "shipped_bytes": shipped_bytes,
            "ordpar.css": len(page_mod.shipped(page_mod.CSS_ALL_HREF).encode("utf-8")),
            "ordpar.js": len(page_mod.shipped(page_mod.JS_ALL_HREF).encode("utf-8"))}


def write_manifest_colours(path):
    """The app manifest's `theme_color` and `background_color` follow the DEFAULT colour scheme
    (decisions 63, `sitegen/colours.py` `DEFAULT`; Chrome fixes them at install). Rewritten in
    place after `ordpar/root/` is copied, so with the default unchanged the file is the
    committed one byte for byte."""
    import re
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    day = colours_mod.default()["day"]
    new = re.sub(r'("(?:theme|background)_color": ")#[0-9a-fA-F]{6}(")',
                 lambda m: m.group(1) + day + m.group(2), text)
    if new != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)


def write_strings(path):
    """`sitegen/strings.py` -> `out/site/strings/en.json`. Where `ordpar/site/` brought its
    own `strings/en.json` along (the shell's keys, build C), the two are merged and the
    file's own value wins any collision — this build never silently rewrites another's
    string."""
    existing = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
        except ValueError:
            existing = {}
        clash = [k for k in existing if k in EN and existing[k] != EN[k]]
        if clash:
            print("note: out/site/strings/en.json already had %s with other value(s); "
                  "keeping the file's" % ", ".join(sorted(clash)))
    merged = dict(EN)
    merged.update(existing)
    write(path, page_mod.strings_json(merged))


def measure(builder, aid, full_html):
    """The sizes decisions 24 and 34 asked for: the page as shipped (the stylesheet linked),
    the same page with the sheet inlined, and with the minis and/or the paradigm island left
    out."""
    def one(text):
        return {"bytes": len(text.encode("utf-8")), "gzip": gz(text)}
    # the variants are re-renders of the same page: they must not count twice
    f = builder.face
    keep = (builder.missing_exprs, f.downgraded, f.peekless, f.matched, f.no_unmatched,
            f.en_unmatched, dict(f.nb_counts))
    inlined = builder.page(aid, inline_css=True)["html"]
    no_minis = builder.page(aid, omit_minis=True)["html"]
    no_par = builder.page(aid, omit_paradigm=True)["html"]
    neither = builder.page(aid, omit_minis=True, omit_paradigm=True)["html"]
    builder.face.omit_minis = False
    (builder.missing_exprs, f.downgraded, f.peekless, f.matched, f.no_unmatched,
     f.en_unmatched, f.nb_counts) = keep
    return {"full": one(full_html), "css_inlined": one(inlined), "no_minis": one(no_minis),
            "no_paradigm": one(no_par), "neither": one(neither)}


if __name__ == "__main__":
    main()
