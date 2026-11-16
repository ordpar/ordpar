"""Site decisions 100 (2): no broken link inside the built site, pure Python over `ordpar/out/`.

**What the build already does, and why this is not a duplicate.** `sitegen/face.py`
`preprocess` downgrades a cross-reference whose target the LIBRARY or mirror cannot resolve to
plain text (`build.json` `cross_references.downgraded_unresolvable`, 73 on 2026-10-23), and the
deck's `dangling-def` advisory counts definition ids its derive cannot find. Neither looks at
the OUTPUT: whether every link a published page carries reaches a file the build actually
wrote, or an anchor on that page. This does.

Every `href` and `src` in every published HTML page (`out/` less `deploy.py` `EXCLUDE`, the
prototypes and `build.json`) that points inside the site — a path from `/`, a relative path,
`https://ordpar.no/…`, or a bare `#anchor` — must resolve:

* the `?v=` stamp and any query are dropped (`/bm-en/?q=hus` is the search page);
* `/dir/` is `out/dir/index.html`; a path is a file in `out/`, or a folder holding `index.html`;
* `/bm-en/<id>/<slug>` bounces to `/bm-en/<id>/` (`docs/lookup-index.md` § `404.html` is the
  shell too) and must have its page; `/bm-en/<word>` with no page answers 404 on the host and is
  broken (site decisions 117: "No internal link may answer 404" — until 117 the 404 shell's search
  made it allowed, and the "N more entries" link used it);
* a fragment `#q=…` is a search (decisions 104), not an anchor: the page must exist (the search
  page `/bm-en/`, or since 117 a word page `/bm-en/<word>/#q=<word>`, a similar headword's link);
* a `#anchor` must be an `id` (or `<a name>`) on its target page — the same page for a bare one;
  14 known exceptions, ordbokene's own dangling definition ids, are listed in `KNOWN_DANGLING`.
  The settings page is drawn by its script, so its sections' ids are not in its HTML: an anchor
  on `/settings/` must be one `settings.js` draws (`SCRIPT_ANCHORS`: its `SECTIONS` and the presets'
  box, read from the script; site decisions 136, the Help page's link to `/settings/#article`).

About 25–40 s over the 94,000-odd pages (threaded reads; most of it is the disk). Skipped when
`ordpar/out/` holds no build.
"""
import ast
import os
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo
OUT = os.path.join(ROOT, "ordpar", "out")
SITE_HOSTS = {"ordpar.no", "www.ordpar.no"}

ATTR = re.compile(r'\s(?:href|src)="([^"]*)"')
IDS = re.compile(r'\s(?:id|name)="([^"]+)"')
SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.S)
NOT_HTTP = ("mailto:", "tel:", "data:", "javascript:", "blob:")
# Known, reported 2026-10-23 and left for the session to rule on: links from UNTRANSLATED pages
# (the mirror path) to a definition id the target article does not have — ordbokene's own
# dangling definition ids. The deck's deriver drops such an anchor and keeps the bare link
# (`review/dangling-def-assessed.jsonl`, "the standard dangling-def handling"); the site's
# mirror path keeps it, so the link opens the right page at its top. A new one fails the test,
# and so does one that no longer occurs (remove it here).
KNOWN_DANGLING = {
    ("bm-en/107519/index.html", "/bm-en/879/#def3"), ("bm-en/118360/index.html", "/bm-en/27521/#def4"),
    ("bm-en/124735/index.html", "/bm-en/41276/#def2"),
    ("bm-en/27277/index.html", "/bm-en/27240/#def4"), ("bm-en/28737/index.html", "/bm-en/28738/#def4"),
    ("bm-en/42507/index.html", "/bm-en/42532/#def4"), ("bm-en/43849/index.html", "/bm-en/43877/#def4"),
    ("bm-en/46064/index.html", "/bm-en/46063/#def4"), ("bm-en/46451/index.html", "/bm-en/46456/#def4"),
    ("bm-en/47303/index.html", "/bm-en/14216/#def9"), ("bm-en/47305/index.html", "/bm-en/14216/#def9"),
    ("bm-en/62225/index.html", "/bm-en/62046/#def4"), ("bm-en/62452/index.html", "/bm-en/62451/#def3"),
    ("bm-en/65809/index.html", "/bm-en/65804/#def4"),
}
ID_SLUG = re.compile(r"^(bm-en/\d+)/.+$")


def script_anchors():
    """{page: ids} a page's script draws (decisions 136): `/settings/`'s sections, from
    `settings.js` `SECTIONS`, and the presets' box (`presets`)."""
    with open(os.path.join(ROOT, "ordpar", "site", "settings.js"), encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"var SECTIONS = \[([^\]]*)\];", js)
    ids = set(re.findall(r"'([\w-]+)'", m.group(1))) if m else set()
    if "sec.id = 'presets';" in js:
        ids.add("presets")
    return {"settings/index.html": ids}


SCRIPT_ANCHORS = script_anchors()


def excluded():
    """`deploy.py` `EXCLUDE`, read without importing the module."""
    with open(os.path.join(ROOT, "ordpar", "deploy.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(getattr(t, "id", None) == "EXCLUDE" for t in targets):
                return set(ast.literal_eval(node.value))
    raise AssertionError("deploy.py has no EXCLUDE")


def pages():
    """Every published HTML page, as a path relative to out/ with forward slashes."""
    skip = excluded()
    out = []
    for name in os.listdir(OUT):
        if name in skip:
            continue
        p = os.path.join(OUT, name)
        if name.endswith(".html"):
            out.append(name)
        elif os.path.isdir(p) and name not in ("offline", "index"):
            if name == "bm-en":
                out.append("bm-en/index.html")
                out.extend("bm-en/%s/index.html" % e.name for e in os.scandir(p) if e.is_dir())
            else:
                for d, _, fs in os.walk(p):
                    rel = os.path.relpath(d, OUT).replace(os.sep, "/")
                    out.extend("%s/%s" % (rel, f) for f in fs if f.endswith(".html"))
    return out


def read(rel):
    """(links, ids) of one page: every href/src value outside inline scripts, and its anchors."""
    with open(os.path.join(OUT, rel), encoding="utf-8") as f:
        text = f.read()
    body = SCRIPT.sub("", text)
    return rel, set(ATTR.findall(body)), set(IDS.findall(text))


def target(rel, url):
    """(target page relative to out/ or None for a search route, fragment) of an internal link;
    None for a link outside the site."""
    if url.startswith(NOT_HTTP):
        return None
    s = urlsplit(url)
    if s.scheme or s.netloc:
        if s.scheme not in ("http", "https", "") or s.netloc not in SITE_HOSTS:
            return None
    path = unquote(s.path)
    frag = "" if s.fragment.startswith("q=") else s.fragment     # a search, not an anchor (104)
    if not path:
        return rel, frag                                # "#anchor" or "?q=…": this page
    if not path.startswith("/"):
        path = "/" + os.path.normpath(os.path.join(os.path.dirname(rel), path)).replace(os.sep, "/")
    path = path.lstrip("/")
    if path == "" or path.endswith("/"):
        return path + "index.html", frag
    m = ID_SLUG.match(path)
    if m and not os.path.isfile(os.path.join(OUT, path)):
        return m.group(1) + "/index.html", frag
    if os.path.isdir(os.path.join(OUT, path)):
        return path + "/index.html", frag
    return path, frag


class NoPageNoLink(unittest.TestCase):
    """The renderer's side (always runs): a cross-reference to an article the build writes no page
    for stays plain text, even when the library has its row (`face.SiteFace.resolvable`,
    `has_page`). Found 2026-11-08: *utluftet*'s reference to *lufte ut* (122112, a library row
    ordbokene 404s and the mirror never lists) became a link to no page once the row had English;
    the whole-site check below failed on that build."""

    def test_a_row_without_a_page_stays_plain(self):
        import sys
        sys.path.insert(0, ROOT)
        sys.path.insert(0, os.path.join(ROOT, "ordpar"))
        from ordpar.sitegen import face

        class Store:
            library = {1: {"id": 1}, 2: {"id": 2}}
            mirror = {1: {}}

            def is_embedded_only(self, aid):
                return False

        f = face.SiteFace(Store())
        f.set_library(Store.library)
        text = "som er [luftet ut](/nob/bm/2#def3)"
        self.assertIn("](/nob/bm/2#def3", f.preprocess(text, norwegian=True))   # no `has_page`: a link
        f.has_page = lambda aid: aid == 1
        self.assertEqual(f.preprocess(text, norwegian=True), "som er {luftet ut}")
        self.assertTrue(f.resolvable(1))
        self.assertFalse(f.resolvable(2))
        self.assertFalse(f.resolvable(2, hover_only=True))


@unittest.skipUnless(os.path.isfile(os.path.join(OUT, "index.html")), "no built site in ordpar/out/")
class NoBrokenLinks(unittest.TestCase):

    def test_target_rules(self):
        self.assertEqual(target("bm-en/1/index.html", "/site/ordpar.css?v=abc"), ("site/ordpar.css", ""))
        self.assertEqual(target("bm-en/1/index.html", "/bm-en/39910/#def2"), ("bm-en/39910/index.html", "def2"))
        self.assertEqual(target("bm-en/1/index.html", "#def3"), ("bm-en/1/index.html", "def3"))
        self.assertEqual(target("index.html", "https://ordpar.no/bm-en/39910/"), ("bm-en/39910/index.html", ""))
        self.assertEqual(target("index.html", "https://ordbokene.no/"), None)
        self.assertEqual(target("index.html", "/bm-en/?q=hus"), ("bm-en/index.html", ""))
        self.assertEqual(target("index.html", "mailto:a@b.c"), None)
        # site decisions 117: a search after `#` is no anchor; a word page is a folder
        self.assertEqual(target("bm-en/1/index.html", "/bm-en/#q=Norge"), ("bm-en/index.html", ""))
        self.assertEqual(target("bm-en/1/index.html", "/bm-en/s%C3%A5/#q=s%C3%A5"), ("bm-en/så/index.html", ""))
        self.assertEqual(target("bm-en/1/index.html", "/bm-en/Nowhere")[0], "bm-en/Nowhere")
        # decisions 136: the settings page's script-drawn sections
        self.assertLessEqual({"style", "article", "search", "data", "presets"}, SCRIPT_ANCHORS["settings/index.html"])

    def test_every_internal_link_resolves(self):
        rels = pages()
        self.assertGreater(len(rels), 1000, "too few pages in %s" % OUT)
        with ThreadPoolExecutor(8) as ex:
            found = list(ex.map(read, rels, chunksize=256))
        anchors = {rel: ids for rel, _, ids in found}
        exists = {}
        bad = []
        seen_known = set()
        n = 0
        for rel, links, _ in found:
            for url in links:
                t = target(rel, url)
                if t is None:
                    continue
                n += 1
                page, frag = t
                if page == "":
                    continue
                if page not in exists:
                    exists[page] = page in anchors or os.path.isfile(os.path.join(OUT, page))
                if not exists[page]:
                    bad.append("%s: %s — no file %s" % (rel, url, page))
                elif frag and page.endswith(".html"):
                    ids = anchors.get(page)
                    if ids is None:
                        ids = anchors[page] = read(page)[2]
                    if unquote(frag) not in ids and unquote(frag) not in SCRIPT_ANCHORS.get(page, ()):
                        if (rel, url) in KNOWN_DANGLING:
                            seen_known.add((rel, url))
                        else:
                            bad.append("%s: %s — no #%s on %s" % (rel, url, frag, page))
        self.assertGreater(n, 100000, "suspiciously few internal links (%d)" % n)
        bad += ["%s: %s — listed in KNOWN_DANGLING but no longer broken: remove it" % k
                for k in sorted(KNOWN_DANGLING - seen_known)]
        if bad:
            self.fail("%d broken internal link(s) in %d pages (%d links checked):\n%s"
                      % (len(bad), len(rels), n, "\n".join(sorted(bad)[:60])))


if __name__ == "__main__":
    unittest.main(verbosity=2)
