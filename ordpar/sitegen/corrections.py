# -*- coding: utf-8 -*-
"""The change notice on the articles whose Norwegian we corrected (site decisions 106, Robin
2026-10-23), and the About page's counts of the same corrections — the build's one reader of the
deck's normalization log, `review/source-normalizations.jsonl`, for them (`lemma_order.py` reads
the same log for the headword order only).

**Which log rows are live** (`live_rows`; the log's contract is `docs/schemas.md`
§ `review/source-normalizations.jsonl` and `docs/pipeline.md` § Source normalization):

* a row names one article by an integer `article`. A row with `article: null` is either a backfill
  whose case was logged again with its id (all six such rows today have that twin) or not an
  article's correction at all (`whitespace-class` and the three `registry-pointer:*` rows record
  defects deliberately NOT corrected in any capture). A class row with an `ids` list (`refresh`, a
  content refresh, and the doubled-space class, whose before and after a browser shows alike) is
  not an article correction either;
* `resolved_upstream` set: ordbokene's own article carries the fix, so the row no longer differs
  from the source and is dropped;
* `revert` is the recipe for undoing the edit, not a record that it was undone — the row stands;
  `supersedes` points at the declined decision the row replaced — the row stands;
* `reapplied_from` marks a correction a content refresh undid and the session re-applied: the row
  stands, and the earlier row it names (same article and kind, `date` = `reapplied_from`) is its
  predecessor and is dropped, so the one correction is counted once;
* the same correction logged twice for one article (same kind, the one row's `before` and
  `after` contained in the other's) counts once.

**A notice must be true** (the brief; Robin's rider of 2026-10-23: a correction ordbokene makes
itself drops off before the log learns of it). Each live row is checked at build time against
two renderings of its article: the page's own Norwegian (the library row the page is built from,
with its expressions as the page shows them) and the same article derived from the mirror —
ordbokene's text as of the snapshot (`Checker`). Per kind:

* a cross-reference (`ref-anchor`, `ref-retarget`, `ref-unlink`): the page's link targets
  differ from the mirror's; where they agree, the mirror already points where ours does;
* the headword's order (`lemma-order` on the header): the mirror's spellings, in ordbokene's own
  order, are not already the logged order and can be put in it (as `lemma_order.reorder` does);
* a typo (`typo`, `wording`, `wrong-form`): the words and punctuation the row removed are fewer
  on the page than in the mirror, or those it added more (word counts over the whole article,
  NFKC, tags dropped); where they agree, the row's `before` text still in the mirror means the
  page carries the defect too, and its `after` text there (with `before` gone) means ordbokene
  has fixed it;
* every other kind: the page's Norwegian (text, link targets, senses, word class) differs from
  the mirror's anywhere;
* any kind whose `before` and `after` differ only in a run of spaces (or that the row calls a
  "double space"): a browser shows the two alike, so there is nothing to see.

The verdicts: `SHOWN` — the only one that makes a notice or a count; `UPSTREAM` — ordbokene's
text as of the snapshot already carries the fix (for the library side to mark
`resolved_upstream`); `NOT_SHOWN` — the page does not show the correction (it is built from the
mirror, with no library row, or the page carries the defect as the mirror does); `INVISIBLE`;
`UNCONFIRMED` — no difference found on the page, and the row's text cannot settle why. All but
`SHOWN` are listed in `build.json` (`change_notice`).

**The handover's corrections to articles with no library row** (site decisions 182,
`review/mirror-corrections.jsonl`, `overlay.py`): the build applies each to the mirror article
before the page derives it. A row the overlay APPLIED is a live correction of its `article`, like a
capture edit; it is checked the same way (`check_row`, its `before_text` and `after_text` standing
for the log's `before` and `after`), the page — derived from the corrected article — against the
RAW mirror (`Store.raw_derived`), with the page counting as ours (`page_has_row`). The capture-edit
rows' mirror side is the raw mirror too, so their verdicts are as before. A row the overlay did not
apply makes no notice and is listed in `build.json`'s `mirror_corrections`, not here.

**The words** are the shell's strings (`ordpar/site/strings/en.json`, `change.*`): a phrase per
group, singular and plural, joined with commas and "and", the groups most important first
(`GROUPS`). The link goes to the article on ordbokene.no (`chrome.ORDBOKENE_ARTICLE`).
"""
import collections
import html
import json
import os
import re
import unicodedata

from . import chrome
from . import lemma_order

LOG = lemma_order.LOG

#: kind -> notice group. Every kind the log carries that names a correction of an article.
KIND_GROUP = {
    "ref-anchor": "xref", "ref-retarget": "xref", "ref-unlink": "xref",
    "lemma-order": "headorder",
    "typo": "typo", "wording": "typo",
    "wrong-form": "form",
    "notation": "punct", "alternation-notation": "punct", "inflectional-collapse": "punct",
    "marker": "punct",
    "comp-membership": "compounds",
    "segment-drop": "fragment",
    "misplaced-element": "misplaced",
    "duplicate-expression-article": "setphrase",
    "pos-tag": "wordclass",
    "duplicate-def-id": "anchor",
    "capture-repair": "damage",
}
#: The groups in the notice's order: cross-references, the headword's order, spelling, the rest
#: (the session's call, decisions 106).
GROUPS = ["xref", "headorder", "typo", "form", "punct", "compounds", "fragment", "misplaced",
          "setphrase", "wordclass", "anchor", "damage"]
#: The About page's buckets (decisions 106: a concise bulleted list of every type of change
#: with its count): cross-references; typos, punctuation and formatting; the headword's order;
#: the rest, which the page names by these groups' own phrases (`about_other`).
ABOUT_BUCKET = {"xref": "xref", "headorder": "headorder", "typo": "spelling", "punct": "spelling"}
ABOUT_BUCKETS = ["xref", "spelling", "headorder", "other"]

SHOWN, UPSTREAM, NOT_SHOWN, INVISIBLE, UNCONFIRMED = (
    "shown", "upstream", "not_shown", "invisible", "unconfirmed")

_REF = {"xref"}
_TYPO = {"typo", "form"}


def _nfc(s):
    return unicodedata.normalize("NFC", s or "")


def read_log(path=LOG):
    """Every row of the log, in order (a missing log is none)."""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def _squash(s):
    return " ".join(_nfc(s).split())


def _same_case(a, b):
    """Two rows for one article and kind that record the same edit: each `before` and `after`
    contained in the other's (after collapsing whitespace)."""
    def within(x, y):
        x, y = _squash(x).strip("'\""), _squash(y).strip("'\"")
        return bool(x) and bool(y) and (x in y or y in x)
    return within(a.get("before"), b.get("before")) and within(a.get("after"), b.get("after"))


def live_rows(rows):
    """The rows that are live corrections of one article (the module's rule), in log order."""
    cand = [r for r in rows
            if isinstance(r.get("article"), int) and not isinstance(r.get("article"), bool)
            and r.get("kind") in KIND_GROUP and not r.get("ids")
            and not r.get("resolved_upstream")]
    # a re-applied row replaces the row it names
    gone = set()
    for r in cand:
        src = r.get("reapplied_from")
        if src:
            for i, o in enumerate(cand):
                if (o is not r and o.get("article") == r["article"] and o.get("kind") == r["kind"]
                        and o.get("date") == src and not o.get("reapplied_from")):
                    gone.add(i)
    out = []
    for i, r in enumerate(cand):
        if i in gone:
            continue
        if any(o["article"] == r["article"] and o["kind"] == r["kind"] and _same_case(o, r)
               for o in out):
            continue
        out.append(r)
    return out


# --- what a page shows, as text ------------------------------------------------

_LINK = re.compile(r"\]\(([^)]*)\)")


def _segments(row):
    """Every Norwegian string of a row: etymology, senses and sub-senses, examples, and the
    compound lists, their intro (stored since site decisions 151) and their compounds written
    as links."""
    if not row:
        return []
    out = list((row.get("etymology") or {}).get("no") or [])
    for s in row.get("senses") or []:
        for u in [s] + (s.get("subs") or []):
            out.extend(u.get("no") or [])
            for ex in u.get("ex") or []:
                if ex and isinstance(ex[0], str):
                    out.append(ex[0])
            for b in u.get("comp") or []:
                out.append(b.get("intro") or "")
                for it in b.get("items") or []:
                    out.append("[%s](%s)" % (it.get("face") or it.get("form") or "",
                                             it.get("href") or ""))
    return [_nfc(x) for x in out if isinstance(x, str)]


class View(object):
    """One article's Norwegian as a page shows it: the root row plus its expression rows."""

    def __init__(self, root, exprs=()):
        rows = [root] + [e for e in exprs if e]
        segs = [s for r in rows for s in _segments(r)]
        # whitespace collapsed, as a browser shows it
        self.text = _squash(" ".join(_LINK.sub("]", s) for s in segs))
        self.hrefs = collections.Counter(h for s in segs for h in _LINK.findall(s))
        self.rest = json.dumps([[(x.get("defn"), len(x.get("subs") or []))
                                 for x in (r.get("senses") or [])] for r in rows]
                               + [root.get("pos_en"), len(root.get("exprs") or [])])

    def tokens(self):
        return collections.Counter(_tokens(self.text))


def _tokens(s):
    # NFKC and the tags dropped: a page's superscript "m³" is the "m<sup>3</sup>" a log row writes
    s = re.sub(r"</?\w+>", "", s or "")
    return re.findall(r"\w+|[^\w\s$]", unicodedata.normalize("NFKC", s).lower())


def _piece(s):
    """The longest stretch of a log row's `before` or `after` with no `$` slot, without the
    quotes the row wraps it in, or None when it is too short to look for."""
    p = max(_squash(s).strip("'\"").split("$"), key=len).strip().strip("'\"")
    return p if len(p) > 3 else None


def _spaces_only(before, after):
    b, a = _nfc(before), _nfc(after)
    return b != a and b.split() == a.split()


def check_row(row, page, mirror, page_has_row, mirror_lemmas=None):
    """The verdict on one live row (`SHOWN`, `UPSTREAM`, `NOT_SHOWN`, `INVISIBLE`, `UNCONFIRMED`).

    `page` and `mirror` are `View`s of the article as the page shows it and as the mirror's
    data derives (None where there is none); `page_has_row` whether the page is built from a
    library row (so from the capture carrying the edit); `mirror_lemmas` the mirror's header
    spellings in its order, for a `lemma-order` row."""
    group = KIND_GROUP[row["kind"]]
    if row["kind"] == "lemma-order" and str(row.get("where") or "").startswith(lemma_order.WHERE):
        after = _squash(row.get("after"))
        forms = []
        for f in mirror_lemmas or []:
            f = _squash(f)
            if f and f not in forms:
                forms.append(f)
        if ", ".join(forms) == after:
            return UPSTREAM
        if forms and sorted(forms) == sorted(after.split(", ")):
            return SHOWN              # `lemma_order.reorder` puts the line in the logged order
        return NOT_SHOWN
    if (_spaces_only(row.get("before"), row.get("after")) or group in _TYPO
            and "double space" in (str(row.get("before")) + " "
                                   + str(row.get("after"))).lower()):
        return INVISIBLE
    if mirror is None:
        return SHOWN if page_has_row else NOT_SHOWN   # no mirror text: the page is ours alone
    mtext = _squash(mirror.text)
    bp, ap = _piece(row.get("before")), _piece(row.get("after"))
    fixed_upstream = bool(group in _TYPO and ap and ap in mtext and not (bp and bp in mtext))
    if not page_has_row:
        return UPSTREAM if fixed_upstream else NOT_SHOWN
    if group in _REF:
        if page.hrefs != mirror.hrefs:
            return SHOWN
        return UPSTREAM               # the mirror's references already point where ours do
    if group in _TYPO:
        b = collections.Counter(_tokens(row.get("before")))
        a = collections.Counter(_tokens(row.get("after")))
        removed, added = b - a, a - b
        if removed or added:
            tp, tm = page.tokens(), mirror.tokens()
            differs = (any(tp[w] > tm[w] for w in added)
                       or any(tm[w] > tp[w] for w in removed))
        else:
            differs = page.text != mirror.text
        if differs:
            return SHOWN
        if bp and bp in mtext:
            return NOT_SHOWN          # the page carries the defect as the mirror does
        return UPSTREAM if fixed_upstream else UNCONFIRMED
    if (page.text != mirror.text or page.hrefs != mirror.hrefs or page.rest != mirror.rest):
        return SHOWN
    return UNCONFIRMED


class Checker(object):
    """The verdicts for every live row, over the build's `library.Store` (the page's rows and
    the mirror's derivation) — computed once for the whole log, whatever pages a run builds."""

    def __init__(self, store, rows=None, has_page=None, overlay_rows=()):
        """`has_page(aid)`: whether the site builds the article a page (decisions 46,
        `mirror.Listing.has_page`); a row on an article with none is `NOT_SHOWN`.
        `overlay_rows`: the rows of `review/mirror-corrections.jsonl` the overlay applied
        (`overlay.Overlay.applied_rows`, site decisions 182)."""
        self.store = store
        self.rows = live_rows(read_log() if rows is None else rows)
        self.overlay_rows = list(overlay_rows)
        self._overlay_ids = {id(r) for r in self.overlay_rows}
        self.verdicts = []            # (row, verdict)
        by_article = collections.OrderedDict()
        for r in self.rows:
            by_article.setdefault(r["article"], []).append(r)
        for aid, rs in by_article.items():
            if has_page is not None and not has_page(aid):
                self.verdicts.extend((r, NOT_SHOWN) for r in rs)
                continue
            page, mirror, has_row, lemmas = self._views(aid)
            for r in rs:
                self.verdicts.append((r, check_row(r, page, mirror, has_row, lemmas)))
        for r in self.overlay_rows:
            self.verdicts.append((r, self._check_overlay(r, has_page)))
        self.notice = {}              # article id -> [(group, n)] in GROUPS order
        counts = collections.defaultdict(collections.Counter)
        for r, v in self.verdicts:
            if v == SHOWN:
                counts[r["article"]][KIND_GROUP[r["kind"]]] += 1
        for aid, c in counts.items():
            self.notice[aid] = [(g, c[g]) for g in GROUPS if c[g]]

    def _check_overlay(self, r, has_page):
        """An applied overlay row's verdict: the page (derived from the corrected article)
        against the raw mirror, the page counting as ours."""
        aid = r["article"]
        if has_page is not None and not has_page(aid):
            return NOT_SHOWN
        st = self.store
        derived = st.derived(aid)
        raw = getattr(st, "raw_derived", st.derived)(aid)
        if derived is None or raw is None:
            return NOT_SHOWN
        raw_ex = getattr(st, "raw_embedded_expr", st.embedded_expr)
        page = View(derived, [st.expr_row(aid, e) for e in derived.get("exprs") or []])
        mirror = View(raw, [getattr(st, "raw_derived", st.derived)(e) or raw_ex(aid, e)
                            for e in raw.get("exprs") or []])
        shim = dict(r, before=r.get("before_text") or "", after=r.get("after_text") or "")
        return check_row(shim, page, mirror, True)

    def _views(self, aid):
        st = self.store
        lib = st.library.get(aid)
        # site decisions 182: the mirror's side is the RAW mirror, without the overlay's
        # corrections (a stand-in store without `raw_derived` has no overlay)
        raw_derived = getattr(st, "raw_derived", st.derived)
        raw_embedded = getattr(st, "raw_embedded_expr", st.embedded_expr)
        derived = raw_derived(aid)
        # the mirror's own order, before `lemma_order` (which `Mirror.data` applies)
        raw = st.mirror.row(aid)
        data = raw.get("data") if raw else st.mirror.stored.get(aid)
        lemmas = [l.get("lemma") for l in (data or {}).get("lemmas") or []]
        mirror_view = None
        if derived is not None:
            mx = [raw_derived(e) or raw_embedded(aid, e) for e in derived.get("exprs") or []]
            mirror_view = View(derived, mx)
        if lib is None:
            return mirror_view, mirror_view, False, lemmas
        px = [st.expr_row(aid, e) for e in lib.get("exprs") or []]
        return View(lib, px), mirror_view, True, lemmas

    def summary(self):
        """What `build.json` records and the About page counts: the notice's articles, the
        counts by group and by the About page's bucket (corrections and articles), and every
        row that makes no notice, by verdict."""
        groups = collections.Counter()
        g_articles = collections.defaultdict(set)
        buckets = collections.Counter()
        b_articles = collections.defaultdict(set)
        for r, v in self.verdicts:
            if v != SHOWN:
                continue
            g = KIND_GROUP[r["kind"]]
            b = ABOUT_BUCKET.get(g, "other")
            groups[g] += 1
            g_articles[g].add(r["article"])
            buckets[b] += 1
            b_articles[b].add(r["article"])
        other_groups = [[g, groups[g]] for g in GROUPS
                        if groups[g] and ABOUT_BUCKET.get(g, "other") == "other"]
        out = {
            "live_rows": len(self.rows),
            "shown": sum(groups.values()),
            "articles": len(self.notice),
            "groups": {g: {"corrections": groups[g], "articles": len(g_articles[g])}
                       for g in GROUPS if groups[g]},
            "about": {b: {"corrections": buckets[b], "articles": len(b_articles[b])}
                      for b in ABOUT_BUCKETS},
            "other_groups": other_groups,
            "notice": {str(a): [[g, n] for g, n in v] for a, v in sorted(self.notice.items())},
        }
        if self.overlay_rows:
            # site decisions 182: the applied rows of `review/mirror-corrections.jsonl`, checked
            # as above (each also in its verdict's list below, marked `"overlay": true`); absent
            # with none, so a build without the file records what it did before (`deploy.py`'s
            # library fingerprint hashes these keys)
            out["overlay_rows"] = [{"article": r["article"], "kind": r["kind"],
                                    "handover": r.get("handover")} for r in self.overlay_rows]
            out["overlay_shown"] = sum(1 for r, v in self.verdicts
                                       if v == SHOWN and id(r) in self._overlay_ids)
        for verdict in (UPSTREAM, NOT_SHOWN, INVISIBLE, UNCONFIRMED):
            out[verdict] = [dict({"article": r["article"], "kind": r["kind"],
                                  "date": r.get("date"), "lemma": r.get("lemma"),
                                  "defect": r.get("defect")},
                                 **({"overlay": True} if id(r) in self._overlay_ids else {}))
                            for r, v in self.verdicts if v == verdict]
        return out


# --- the words ------------------------------------------------------------------

def phrases(groups, strings):
    """`[(group, n)]` -> the phrases, each singular or plural by `n`."""
    return [strings["change.%s.%s" % (g, "one" if n == 1 else "many")] for g, n in groups]


def join(items, strings):
    """"a", "a and b", "a, b and c" (the list's "and" is `change.and`)."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " " + strings["change.and"] + " " + items[-1]


def sentence(groups, strings):
    """The notice's sentence. The headword's order is not a correction but a usage ruling, so it
    has a sentence of its own, "We put the more common spelling of the headword first." (Robin,
    2026-10-23, decisions 106), joined to any other kinds: "… first and corrected a typo in this
    article." """
    rest = [(g, n) for g, n in groups if g != "headorder"]
    if len(rest) < len(groups):
        if not rest:
            return strings["change.sentence.headorder"]
        return strings["change.sentence.headorder_and"].format(changes=join(phrases(rest, strings), strings))
    return strings["change.sentence"].format(changes=join(phrases(groups, strings), strings))


def notice_html(aid, groups, strings):
    """The notice's markup, inside the card's foot (`page.render`): one paragraph, the sentence
    and the link to the article on ordbokene.no. `groups` is `Checker.notice[aid]`; "" for
    none. `strings` must carry the shell's `change.*` (`page.chrome_strings`)."""
    if not groups:
        return ""
    # site decisions 152: the sentence and the link's words in both languages, the labels
    # setting showing one (`article.label_pair`; the Norwegian, `strings.NB`, DRAFTS that drop
    # the kind of correction)
    from .article import label_pair
    from .strings import NB
    rest = [g for g, _n in groups if g != "headorder"]
    nb = NB["change.sentence" if len(rest) == len(groups) else
            "change.sentence.headorder_and" if rest else "change.sentence.headorder"]
    # the link itself in both languages: the English link as it was (a copy inside the link moved
    # three pixels of its underline in the screenshots), the Norwegian one beside it in a span that
    # carries `data-nosnippet` (an `<a>` cannot)
    href = chrome.ORDBOKENE_ARTICLE % aid
    arrow = '<span aria-hidden="true"> ↗</span>'
    link = ('<a class="ordpar-l-en" href="%s" rel="noopener">%s%s</a><span class="ordpar-l-nb" lang="nb" '
            'data-nosnippet><a href="%s" rel="noopener">%s%s</a></span>'
            % (href, html.escape(strings["change.link"], quote=False), arrow,
               href, html.escape(NB["change.link"], quote=False), arrow))
    return ('<p class="ordpar-change">%s %s</p>'
            % (label_pair(sentence(groups, strings), nb), link))


def about_other(other_groups, strings):
    """The About page's "Other corrections (…)": the rest's groups by their notice phrases,
    singular or plural by count, joined — "a word form, a list of compounds and a misplaced
    passage"."""
    return join(phrases(other_groups, strings), strings)
