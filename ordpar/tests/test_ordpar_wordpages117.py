"""Site decisions 117 (Robin, 2026-10-24/25): word pages, form pages and the form labels.

Pinned over the code and over the built site (`ordpar/out/`, or `ORDPAR_TEST_OUT`); the checks
marked [live] also run against a served site over HTTP with `ORDPAR_TEST_BASE=https://ordpar.no`
(the site before 117's deploy fails them), the full scans only on a built folder.

* **The address** (`wordpages.word_path`): `/bm-en/<the search's fold, percent-encoded>/`; the
  searches that cannot be folder names (a slash, a question mark, a trailing full stop …) get none.
* **The form label** (`wordpages.FormLabels`): the inflection table's own words read from
  `inflection.js` (group, then the narrow qualifier), "passive infinitive" / "passive present",
  "perfect participle" for a bare participle; several analyses in one label.
* **The irregular test** against each form's own word (*tær* against *tå*, *bøker* against *bok*).
* [live] **A word page** with several entries (*så*): its rows, "så — Norwegian–English
  dictionary", "6 entries in the Norwegian–English dictionary: …" in the suggestions' order, its
  own canonical, indexed; **with one article** (*hus*): the article page's own title and
  description, the canonical page (the article page's canonical points to it); **a variant
  spelling** (*bru*, *bro*: one article): both pages and the article point to *bru*'s page; **a
  form page** (*tær*): the rows with their labels, the proposed title and description, its own
  canonical; *bøker* has one, *husene* (regular) and the unrepresentable searches none.
* [live] **The sitemap**: the word pages, the form pages, the articles that kept their canonical;
  [built] exactly those, every address a page, under 50,000.
* [live] **The browser and the build agree** over every search: `lookup.js` `pageFor` over the
  served index (bun) names exactly the pages the build wrote — no search sent to a missing page,
  no word with a page left a `#q=` search — and the similar headwords' flags too.
* [built] **No internal link answers 404**: every `/bm-en/…` link in a word or form page, and
  every article page's "N more entries" link (`face.lemma_url`), names a page that exists or a
  `#q=` search.
* [live] **The shell pages carry no comments** (decisions 61's leftover), the sources keep theirs;
  **`/test-æøå/` is gone** (decisions 117's check page).
* [built] **The index carries the labels**: `labels.json`, and each shard's `t` aligned with its
  `forms`.

Skipped without a build (the [built] ones) or without bun (the agreement).
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ordpar.sitegen import wordpages as W  # noqa: E402
from ordpar.sitegen import face as F  # noqa: E402
from ordpar.sitegen import slim  # noqa: E402
from ordpar.sitegen import head as H  # noqa: E402
from ordpar import build_index as BI  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
BASE = (os.environ.get("ORDPAR_TEST_BASE") or "").rstrip("/")
DICT = " — Norwegian–English dictionary"
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)">')
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]*)">')
OGURL_RE = re.compile(r'<meta property="og:url" content="([^"]*)">')


def get(path):
    """(status, text) of a site path: over HTTP from `ORDPAR_TEST_BASE`, else from the built
    folder (a folder's `index.html`; 404 for a missing file)."""
    if BASE:
        try:
            with urllib.request.urlopen(BASE + quote(path, safe="/%#?=&"), timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
    rel = unquote(path).lstrip("/")
    p = os.path.join(OUT, rel)
    if path.endswith("/"):
        p = os.path.join(p, "index.html")
    if not os.path.isfile(p):
        return 404, ""
    with open(p, encoding="utf-8") as f:
        return 200, f.read()


def head(t):
    return t[:t.find("</head>")] if "</head>" in t else t


def title(t):
    m = TITLE_RE.search(t)
    return html.unescape(m.group(1)) if m else None


def desc(t):
    m = DESC_RE.search(head(t))
    return html.unescape(m.group(1)) if m else None


def canon(t):
    m = CANON_RE.search(head(t))
    return m.group(1) if m else None


BUILT = not BASE and os.path.isfile(os.path.join(OUT, "bm-en", "index.html"))
#: the page folders the build wrote (non-numeric under bm-en/), by folded word
def built_pages():
    bm = os.path.join(OUT, "bm-en")
    return {e.name for e in os.scandir(bm) if e.is_dir() and not e.name.isdigit()
            and os.path.isfile(os.path.join(e.path, "index.html"))}


# --- the code ------------------------------------------------------------------------

class Code(unittest.TestCase):

    def test_address(self):
        self.assertEqual(W.word_path("så"), "/bm-en/s%C3%A5/")
        self.assertEqual(W.word_path("på kryss og tvers"), "/bm-en/p%C3%A5%20kryss%20og%20tvers/")
        self.assertEqual(W.word_path("hors d'oeuvre"), "/bm-en/hors%20d%27oeuvre/")
        self.assertEqual(W.path_word("/bm-en/s%C3%A5/"), "så")
        self.assertIsNone(W.path_word("/bm-en/9055/"))
        self.assertIsNone(W.path_word("/bm-en/"))

    def test_unrepresentable(self):
        self.assertEqual(W.unrepresentable("km/h"), "slash")
        self.assertEqual(W.unrepresentable("hva behager?"), "question mark")
        self.assertEqual(W.unrepresentable("ca."), "trailing full stop")
        self.assertEqual(W.unrepresentable("...ingen"), "leading full stop")
        self.assertEqual(W.unrepresentable("1814"), "digits only")
        self.assertEqual(W.unrepresentable("con"), "reserved name")
        for ok in ("så", "-aktig", "på kryss og tvers", "hors d'oeuvre", "a4-format"):
            self.assertIsNone(W.unrepresentable(ok), ok)

    def test_labels_in_the_tables_words(self):
        L = W.FormLabels()
        self.assertEqual(L.label({"Plur+Ind"}), "plural indefinite")
        self.assertEqual(L.label({"Sing+Def"}), "singular definite")
        self.assertEqual(L.label({"Imp"}), "imperative")
        self.assertEqual(L.label({"Acc"}), "object form")
        self.assertEqual(L.label({"Pos+Def+Sing", "Pos+Plur"}), "singular definite, plural")
        # decisions 117's points: the passives, and a bare participle
        self.assertEqual(L.label({"Inf+Pass"}), "passive infinitive")
        self.assertEqual(L.label({"Pres+Pass"}), "passive present")
        self.assertEqual(L.label({"<PerfPart>"}), "perfect participle")
        self.assertEqual(L.label({"Past", "<PerfPart>", "Adj+<PerfPart>+Masc/Fem+Ind+Sing",
                                  "Adj+<PerfPart>+Neuter+Ind+Sing"}),
                         "past, perfect participle masculine / feminine and neuter")
        # the words are inflection.js's own: change one there and the label follows
        s = dict(W.table_strings(), plural="PLURAL", indefiniteNarrow="INDEF")
        self.assertEqual(W.FormLabels(s).label({"Plur+Ind"}), "PLURAL INDEF")
        self.assertEqual(W.table_strings()["indefiniteNarrow"], "indefinite")

    def test_codes(self):
        L = W.FormLabels()
        L.assign([{"Plur+Ind"}, {"Plur+Ind"}, {"Imp"}])
        self.assertEqual(L.code({"Plur+Ind"}), "A")
        self.assertEqual(L.code({"Imp"}), "B")
        self.assertEqual(L.code({"Nonsense"}), W.FormLabels.NONE)
        self.assertEqual(L.table(), {"A": "plural indefinite", "B": "imperative"})

    def test_irregular_against_its_own_word(self):
        fold = BI.fold
        self.assertTrue(W.irregular("tær", {"tå"}, fold))
        self.assertFalse(W.irregular("tær", {"tære"}, fold))       # its stem: regular
        self.assertTrue(W.irregular("bøker", {"bok"}, fold))
        self.assertFalse(W.irregular("bøker", {"bøk"}, fold))
        self.assertFalse(W.irregular("kastet", {"kaste"}, fold))
        self.assertFalse(W.irregular("gata", {"gate"}, fold))
        self.assertTrue(W.irregular("gikk", {"gå"}, fold))

    def test_passive_only(self):
        self.assertTrue(W.is_passive_only([frozenset({"Inf+Pass"}), frozenset({"Pres+Pass"})]))
        self.assertFalse(W.is_passive_only([frozenset({"Inf+Pass", "Imp"})]))
        self.assertFalse(W.is_passive_only([]))

    def test_lemma_url(self):
        # the article build writes the search; the index build, knowing the pages, the page
        self.assertEqual(F.lemma_url("Norge"), "/bm-en/#q=Norge")
        self.assertEqual(F.lemma_url("Norge", {"norge"}.__contains__), "/bm-en/norge/")
        self.assertEqual(F.lemma_url("ca.", set().__contains__), "/bm-en/#q=ca.")

    def test_patch_article(self):
        page = ('<head><link rel="canonical" href="https://ordpar.no/bm-en/7/">\n'
                '<meta property="og:url" content="https://ordpar.no/bm-en/7/"></head>'
                '<p class="ordpar-viewline"><a href="/">Home</a><a href="/bm-en/#q=Norge">2 more '
                'entries for Norge</a></p><a href="/bm-en/8/">x</a>')
        new = W.patch_article(page, 7, "/bm-en/norge/", {"norge"}.__contains__)
        self.assertIn('rel="canonical" href="https://ordpar.no/bm-en/norge/"', new)
        self.assertIn('og:url" content="https://ordpar.no/bm-en/norge/"', new)
        self.assertIn('<a href="/bm-en/norge/">2 more entries', new)
        self.assertIn('<a href="/bm-en/8/">x</a>', new)                      # a cross-reference
        back = W.patch_article(new, 7, "/bm-en/7/", set().__contains__)      # the page went away
        self.assertIn('<a href="/bm-en/#q=norge">2 more', back)
        self.assertIn('canonical" href="https://ordpar.no/bm-en/7/"', back)
        self.assertIsNone(W.patch_article(back, 7, "/bm-en/7/", set().__contains__))

    def test_strip_html(self):
        src = ('<!doctype html>\n<!-- a comment, Robin -->\n<p>x</p><!--MARK-->\n'
               '<script>/* one */ var a = "/* kept */"; // two\n</script>\n'
               '<script src="/x.js"></script>\n<style>/* s */ p{color:red}</style>\n')
        out = slim.strip_html(src)
        self.assertNotIn("<!--", out)
        self.assertNotIn("Robin", out)
        self.assertNotIn("one", out)
        self.assertNotIn("two", out)
        self.assertIn('"/* kept */"', out)
        self.assertIn('<script src="/x.js"></script>', out)
        self.assertIn("p{color:red}", out)
        self.assertNotIn("/* s */", out)

    def test_sources_keep_their_comments(self):
        for n in ("404.html", "search.html", "settings.html", "history.html", "favourites.html"):
            with open(os.path.join(ROOT, "ordpar", "site", n), encoding="utf-8") as f:
                self.assertIn("<!--", f.read(), n)

    def test_check_page_removed_from_the_sources(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "ordpar", "root", "test-æøå")))


# --- the site: what a reader or a crawler fetches [live] ------------------------------

def _need_site(test):
    return unittest.skipUnless(BASE or BUILT, "no built site in %s and no ORDPAR_TEST_BASE" % OUT)(test)


@_need_site
class Site(unittest.TestCase):

    def page(self, path):
        st, t = get(path)
        self.assertEqual(st, 200, "%s answered %s" % (path, st))
        return t

    def test_a_several_entries(self):
        t = self.page("/bm-en/s%C3%A5/")
        self.assertEqual(title(t), "så" + DICT)
        d = desc(t)
        # site decisions 154: the word first, 117's colon turned into a full stop
        self.assertTrue(d.startswith("så: 6 entries in the Norwegian–English dictionary. "), d)
        items = d.split("dictionary. ", 1)[1].split(" · ")
        self.assertEqual(len(items), 6, d)
        # the suggestions' order: the translated first (the verb first among them), each with its
        # numeral and first summary gloss; the untranslated "Norwegian only"
        self.assertTrue(items[0].startswith("VI "), items)
        self.assertEqual(items[-1], "II Norwegian only")
        self.assertEqual(canon(t), "https://ordpar.no/bm-en/s%C3%A5/")
        self.assertNotIn(H.ROBOTS_NOINDEX, head(t))
        self.assertIn('<meta property="og:title" content="så — Norwegian–English dictionary">', t)
        self.assertEqual(OGURL_RE.search(t).group(1), canon(t))
        self.assertEqual(t.count('class="ordpar-row"'), 6)
        self.assertIn('<h1 class="ordpar-word-title" lang="nb">så</h1>', t)
        self.assertIn('data-ordpar-word="så"', t)
        # each article keeps its own canonical: no page points to another
        for aid in re.findall(r'<div class="ordpar-row" data-id="(\d+)"', t):
            a = self.page("/bm-en/%s/" % aid)
            self.assertEqual(canon(a), "https://ordpar.no/bm-en/%s/" % aid)

    def test_b_one_article(self):
        t = self.page("/bm-en/hus/")
        aid = re.search(r'<div class="ordpar-row" data-id="(\d+)"', t).group(1)
        self.assertEqual(t.count('class="ordpar-row"'), 1)
        a = self.page("/bm-en/%s/" % aid)
        self.assertEqual(title(t), title(a))
        self.assertEqual(title(t), "hus (noun)" + DICT)
        self.assertEqual(desc(t), desc(a))
        self.assertEqual(canon(t), "https://ordpar.no/bm-en/hus/")
        self.assertEqual(canon(a), "https://ordpar.no/bm-en/hus/")       # the word page is canonical
        self.assertEqual(OGURL_RE.search(a).group(1), "https://ordpar.no/bm-en/hus/")
        # the word's own capitals in the headline
        n = self.page("/bm-en/norge/")
        self.assertIn('<h1 class="ordpar-word-title" lang="nb">Norge</h1>', n)
        self.assertTrue(title(n).startswith("Norge "), title(n))

    def test_c_variant_spelling(self):
        bru, bro = self.page("/bm-en/bru/"), self.page("/bm-en/bro/")
        aid = re.search(r'data-id="(\d+)"', bru).group(1)
        self.assertEqual(re.search(r'data-id="(\d+)"', bro).group(1), aid)
        self.assertEqual(canon(bru), "https://ordpar.no/bm-en/bru/")
        self.assertEqual(canon(bro), "https://ordpar.no/bm-en/bru/")    # the first spelling's page
        self.assertEqual(canon(self.page("/bm-en/%s/" % aid)), "https://ordpar.no/bm-en/bru/")
        sm = self.page("/sitemap.xml")
        self.assertIn("<loc>https://ordpar.no/bm-en/bru/</loc>", sm)
        self.assertNotIn("<loc>https://ordpar.no/bm-en/bro/</loc>", sm)
        self.assertNotIn("<loc>https://ordpar.no/bm-en/%s/</loc>" % aid, sm)

    def test_d_form_page(self):
        t = self.page("/bm-en/t%C3%A6r/")
        self.assertEqual(title(t), "tær" + DICT)
        # site decisions 154: the form first
        self.assertEqual(desc(t), "tær: an inflected form of tå, noun (plural indefinite): toe · "
                                  "tære, verb (imperative): Norwegian only.")
        self.assertEqual(canon(t), "https://ordpar.no/bm-en/t%C3%A6r/")
        self.assertNotIn(H.ROBOTS_NOINDEX, head(t))
        # \s*: site decisions 154 puts a newline between a row's pieces
        # site decisions 152: the word class and the form label in both languages, the Norwegian
        # copy hidden by default (`data-nosnippet`)
        self.assertRegex(t, r'<span class="ordpar-pos"><span class="ordpar-w-en">noun</span><span class="ordpar-w-nb" '
                            r'lang="nb" data-nosnippet>substantiv</span></span>\s*<span class="ordpar-form-label">'
                            r'<span class="ordpar-w-en">\(plural indefinite\)</span><span class="ordpar-w-nb" '
                            r'lang="nb" data-nosnippet>\(ubestemt form flertall\)</span></span>')   # 152 follow-up
        # site decisions 152: both languages, the Norwegian copy hidden ("verb" is Norwegian too)
        self.assertRegex(t, r'<span class="ordpar-pos"><span class="ordpar-w-en">verb</span><span class="ordpar-w-nb" '
                            r'lang="nb" data-nosnippet>verb</span></span>\s*<span class="ordpar-form-label">'
                            r'<span class="ordpar-w-en">\(imperative\)</span><span class="ordpar-w-nb" lang="nb" '
                            r'data-nosnippet>\(imperativ\)</span></span>')
        self.assertIn("“tær” is an inflected form of:", t)
        self.assertEqual(self.page("/bm-en/b%C3%B8ker/").count('class="ordpar-hit"'), 2)
        self.assertIn("<loc>https://ordpar.no/bm-en/t%C3%A6r/</loc>", self.page("/sitemap.xml"))

    def test_e_no_page(self):
        for path in ("/bm-en/husene/", "/bm-en/stirres/", "/bm-en/km%2Fh/", "/bm-en/ca./"):
            st, t = get(path)
            self.assertFalse(st == 200 and "data-ordpar-word" in t, path)

    def test_f_sitemap(self):
        sm = self.page("/sitemap.xml")
        locs = re.findall(r"<loc>([^<]+)</loc>", sm)
        self.assertEqual(len(locs), len(set(locs)))
        self.assertLess(len(locs), 50000)
        # since site decisions 131 (2026-10-26) "Coming to Ordpar" after Help
        self.assertEqual(locs[:4], ["https://ordpar.no/", "https://ordpar.no/about/",
                                    "https://ordpar.no/help/", "https://ordpar.no/coming/"])
        words = [u for u in locs if not re.search(r"/bm-en/\d+/$", u) and "/bm-en/" in u]
        self.assertGreater(len(words), 20000, "no word pages in the sitemap")
        for u in ("https://ordpar.no/bm-en/s%C3%A5/", "https://ordpar.no/bm-en/hus/",
                  "https://ordpar.no/bm-en/gikk/"):
            self.assertIn(u, locs)

    def test_g_shell_pages_without_comments(self):
        for path in ("/", "/404.html", "/bm-en/", "/favourites/", "/history/", "/settings/",
                     "/site/404.html", "/site/search.html", "/site/settings.html",
                     "/site/history.html", "/site/favourites.html"):
            t = self.page(path)
            self.assertNotIn("<!--", t, path)
            self.assertNotIn("Robin", t, path)
            for body in re.findall(r"<script>(.*?)</script>", t, re.S):
                self.assertNotIn("/*", body.replace("'/*'", ""), path)
        # the strings still parse, whole
        t = self.page("/bm-en/")
        m = re.search(r"window\.ORDPAR_STRINGS=\{\"en\":(.*?)\};</script>", t, re.S)
        with open(os.path.join(ROOT, "ordpar", "site", "strings", "en.json"), encoding="utf-8") as f:
            want = json.load(f)
        # since site decisions 131 (2026-10-26) with `strings.py`'s dictionary name beside them, for
        # the tab's title of a search answered in place (`build_index.copy_shell`)
        from ordpar.sitegen.strings import EN
        want["dictionary_name"] = EN["dictionary_name"]
        self.assertEqual(json.loads(m.group(1)), want)

    def test_i_more_entries_link_answers(self):
        """The "N more entries for …" link (`face.lemma_url`) answers 200: the word's page where it
        has one, else its search — never the unfolded `/bm-en/<lemma>` the host answers with 404
        (until 117: `/bm-en/t%C3%B8rre`, `/bm-en/da`)."""
        for aid, want in ((61543, "/bm-en/t%C3%B8rre/"), (9055, "/bm-en/da/")):
            t = self.page("/bm-en/%d/" % aid)
            line = re.search(r'<p class="ordpar-viewline">(.*?)</p>', t, re.S).group(1)
            href = re.findall(r'href="([^"]+)"', line)[-1]
            self.assertEqual(href, want, aid)
            st, _t = get(href.split("#")[0])
            self.assertEqual(st, 200, href)

    def test_h_check_page_gone(self):
        st, t = get("/test-%C3%A6%C3%B8%C3%A5/")
        self.assertNotEqual(st, 200, "/test-æøå/ is still served: %r" % t[:200])
        if not BASE:
            self.assertFalse(os.path.exists(os.path.join(OUT, "test-æøå")))


# --- the browser and the build agree [live] ----------------------------------------------

AGREE_JS = r"""
const fs = require('fs'), path = require('path');
const L = require(%(lookup)s).ordparLookup;
const dir = %(dir)s, base = %(base)s;
L.setLoader(base ? (n => fetch(base + '/index/' + n).then(r => r.ok ? r.json() : null).catch(() => null))
  : (n => { const p = path.join(dir, n); return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; }));
(async () => {
  const qs = JSON.parse(fs.readFileSync(%(qs)s, 'utf8'));
  const pages = {};
  for (const q of qs) { const u = await L.pageFor(q); if (u) { pages[q] = u; } }
  // the similar headwords' links: every headword a similar list can offer, by its own file's flag
  const similar = {};
  for (const letter of %(letters)s) {
    const data = await L.loadHeadwords(letter);
    for (const c in data.buckets) { for (const e of data.buckets[c]) { if (e.p) { similar[e.w] = L.pagePath(e.f); } } }
  }
  process.stdout.write(JSON.stringify({ pages, similar }));
})();
"""


@_need_site
class Agree(unittest.TestCase):
    """`lookup.js` `pageFor` over every search, against the pages the build wrote."""

    @classmethod
    def setUpClass(cls):
        cls.runner = shutil.which("bun") or shutil.which("node")
        if not cls.runner:
            raise unittest.SkipTest("no bun/node on PATH")
        cls.tmp = tempfile.mkdtemp(prefix="ordpar-117-")
        # every search: every headword's fold and every inflected form's, from the shards
        st, idx = get("/index/index.json")
        man = json.loads(idx)
        qs, letters = set(), set()
        for s in man["shards"]:
            st, t = get("/index/" + s["file"])
            sh = json.loads(t)
            qs.update(BI.fold(f) for f in sh["heads"])
            qs.update(BI.fold(f) for f in sh["forms"])
        for h in man["headwords"]["files"]:
            letters.add(h["k"])
        cls.searches = sorted(qs)
        qpath = os.path.join(cls.tmp, "qs.json")
        with open(qpath, "w", encoding="utf-8") as f:
            json.dump(cls.searches, f, ensure_ascii=False)
        script = os.path.join(cls.tmp, "agree.js")
        with open(script, "w", encoding="utf-8") as f:
            f.write(AGREE_JS % {"lookup": json.dumps(os.path.join(ROOT, "ordpar", "site", "lookup.js")),
                                "dir": json.dumps(os.path.join(OUT, "index")), "base": json.dumps(BASE),
                                "qs": json.dumps(qpath), "letters": json.dumps(sorted(letters))})
        res = subprocess.run([cls.runner, script], capture_output=True, timeout=900)
        if res.returncode:
            raise AssertionError(res.stderr.decode("utf-8", "replace")[-2000:])
        cls.got = json.loads(res.stdout.decode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, "tmp", ""), ignore_errors=True)

    def test_a_some_pages(self):
        for q in ("så", "hus", "tær", "gikk", "norge"):
            self.assertEqual(self.got["pages"].get(q), W.word_path(q), q)
        for q in ("husene", "kastet"):
            self.assertNotIn(q, self.got["pages"])

    def test_b_every_address_the_browser_names_is_the_page_it_means(self):
        bad = {q: u for q, u in self.got["pages"].items() if u != W.word_path(q)}
        self.assertFalse(bad, list(bad.items())[:10])

    @unittest.skipIf(BASE, "the built folders are read on a build only")
    def test_c_the_browser_and_the_folders_agree(self):
        built = built_pages()
        named = {unquote(u.split("/")[2]) for u in self.got["pages"].values()}
        self.assertFalse(named - built, "the browser sends these searches to a missing page: %r"
                         % sorted(named - built)[:20])
        self.assertFalse(built - named, "these pages are never reached by their search: %r"
                         % sorted(built - named)[:20])
        sim = {unquote(u.split("/")[2]) for u in self.got["similar"].values()}
        self.assertFalse(sim - built, sorted(sim - built)[:20])
        words = {f for f in built if "word" in self.kind(f)}
        self.assertFalse(words - sim, "word pages a similar headword would not link: %r"
                         % sorted(words - sim)[:20])

    def kind(self, name):
        with open(os.path.join(OUT, "bm-en", name, "index.html"), encoding="utf-8") as f:
            t = f.read()
        return "form" if 'class="ordpar-row"' not in t and "ordpar-inflected" in t else "word"


# --- the whole build [built] ------------------------------------------------------------

@unittest.skipUnless(BUILT, "no built site in %s (or ORDPAR_TEST_BASE set)" % OUT)
class Built(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pages = sorted(built_pages())
        bm = os.path.join(OUT, "bm-en")

        def read(name):
            with open(os.path.join(bm, name, "index.html"), encoding="utf-8") as f:
                return name, f.read()
        with ThreadPoolExecutor(8) as ex:
            cls.text = dict(ex.map(read, cls.pages, chunksize=256))
        with open(os.path.join(OUT, "index", "index.json"), encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_a_counts(self):
        p = self.manifest["pages"]
        self.assertEqual(len(self.pages), p["word_pages"] + p["form_pages"])
        self.assertGreater(p["word_pages"], 20000)
        self.assertGreater(p["form_pages"], 1500)

    def test_b_every_page_names_its_folder(self):
        bad = [n for n, t in self.text.items() if 'data-ordpar-word="%s"' % html.escape(n, quote=True) not in t]
        self.assertFalse(bad, bad[:10])

    def test_c_sitemap_exactly(self):
        with open(os.path.join(OUT, "sitemap.xml"), encoding="utf-8") as f:
            locs = re.findall(r"<loc>([^<]+)</loc>", f.read())
        self.assertLess(len(locs), 50000)
        self.assertEqual(len(locs), len(set(locs)))
        want = set()
        for n, t in self.text.items():
            if canon(t) == "https://ordpar.no" + W.word_path(n):
                want.add(canon(t))
            self.assertNotIn(H.ROBOTS_NOINDEX, head(t), n)
        got_words = {u for u in locs if "/bm-en/" in u and not re.search(r"/bm-en/\d+/$", u)}
        self.assertEqual(got_words, want)
        # every listed article is indexed and its own canonical
        arts = [re.search(r"/bm-en/(\d+)/$", u).group(1) for u in locs if re.search(r"/bm-en/\d+/$", u)]

        def one(aid):
            with open(os.path.join(OUT, "bm-en", aid, "index.html"), encoding="utf-8") as f:
                t = f.read(6000)
            return aid, canon(t), H.ROBOTS_NOINDEX in head(t)
        with ThreadPoolExecutor(8) as ex:
            rows = list(ex.map(one, arts, chunksize=128))
        bad = [r for r in rows if r[1] != "https://ordpar.no/bm-en/%s/" % r[0] or r[2]]
        self.assertFalse(bad, bad[:10])
        # and every article page pointing to a word page is out of it, its word page in it
        self.assertEqual(self.manifest["pages"]["sitemap_articles"], len(arts))

    def test_d_canonical_targets_exist(self):
        bad = []
        for n, t in self.text.items():
            c = canon(t)
            target = unquote(c[len("https://ordpar.no/bm-en/"):].rstrip("/"))
            if target not in self.text:
                bad.append((n, c))
            elif canon(self.text[target]) != c:
                bad.append((n, c, "the target points on"))
        self.assertFalse(bad, bad[:10])

    def test_e_no_internal_link_to_a_missing_page(self):
        bad = []
        ids = {e.name for e in os.scandir(os.path.join(OUT, "bm-en")) if e.name.isdigit()}
        link = re.compile(r'href="(/bm-en/[^"#]*)')
        for n, t in self.text.items():
            for h in link.findall(t):
                rest = unquote(h[len("/bm-en/"):]).rstrip("/")
                if rest and rest not in ids and rest not in self.text:
                    bad.append((n, h))
        self.assertFalse(bad, bad[:10])

        # every article page's "N more entries" link: a page, or a #q= search
        more = re.compile(r'<p class="ordpar-viewline">.*?</p>', re.S)

        def one(aid):
            with open(os.path.join(OUT, "bm-en", aid, "index.html"), encoding="utf-8") as f:
                t = f.read(12000)
            m = more.search(t)
            out = []
            for h in re.findall(r'href="(/bm-en/[^"]*)"', m.group(0) if m else ""):
                if h.startswith("/bm-en/#q="):
                    q = BI.fold(unquote(h[len("/bm-en/#q="):]))
                    if q in self.text:
                        out.append((aid, h, "a #q= link for a word with a page"))
                    continue
                rest = unquote(h[len("/bm-en/"):]).rstrip("/")
                if rest not in self.text and rest not in ids:
                    out.append((aid, h))
            return out
        with ThreadPoolExecutor(8) as ex:
            for r in ex.map(one, sorted(ids), chunksize=256):
                bad.extend(r)
        self.assertFalse(bad, "%d: %r" % (len(bad), bad[:10]))

    def test_f_labels_in_the_index(self):
        with open(os.path.join(OUT, "index", "labels.json"), encoding="utf-8") as f:
            table = json.load(f)
        # site decisions 152: "_nb", each code's words in Norwegian
        nb = table.pop("_nb")
        self.assertEqual(sorted(nb), sorted(table))
        self.assertIn("ubestemt form flertall", nb.values())   # site decisions 152, the follow-up: the Norwegian order
        self.assertIn("plural indefinite", table.values())
        self.assertIn("perfect participle", " ".join(table.values()))
        self.assertNotIn("present perfect", " ".join(table.values()))
        for s in self.manifest["shards"]:
            with open(os.path.join(OUT, "index", s["file"]), encoding="utf-8") as f:
                sh = json.load(f)
            pairs = sum(len(v) for v in sh["forms"].values())
            self.assertEqual(len(sh.get("t", "")), pairs, s["file"])
        with open(os.path.join(OUT, "index", BI.shard_key("tær") + ".json"), encoding="utf-8") as f:
            sh = json.load(f)
        t, k = sh["t"], 0
        for form in sorted(sh["forms"]):
            for aid in sh["forms"][form]:
                if form == "tær" and sh["words"][str(aid)][0] == "tå":
                    self.assertEqual(table[t[k]], "plural indefinite")
                k += 1

    def test_g_word_pages_use_the_article_frame(self):
        t = self.text["så"]
        for href in ("/site/theme.js?v=", "/site/ordpar.css?v=", "/site/ordpar.js?v="):
            self.assertIn(href, t)
        self.assertNotIn("ORDPAR_STRINGS", t)            # not the shell pages' 27 KB frame


if __name__ == "__main__":
    unittest.main()
