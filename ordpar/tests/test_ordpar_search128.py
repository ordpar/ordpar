"""Site decisions 127 and 128 (2026-10-25): search engines and link previews.

What Robin picked from the preview lab, held over the page code and over the built site:

* **noindex on untranslated pages only** (128): `<meta name="robots" content="noindex">` on every
  untranslated article page and on the search page `/bm-en/`, History, Favourites, Settings and
  404; none on a translated article page, the home page, About or Help. Over EVERY built article
  page: `noindex` exactly when `data-translated="0"` — the build lifts it when an article is
  translated, with no list kept by hand.
* **the link-preview tags** (127) on each kind of page: `og:type`, `og:site_name`, `og:url` (the
  canonical address), `og:title` = the `<title>`, `og:description` = the meta description, the
  picture `https://ordpar.no/site/og/ordpar.png` at 1200 x 630 with its alt text, and
  `twitter:card` `summary_large_image`; the picture shipped as is (Robin's PNG, byte for byte).
* **the titles** (128): "word (class) — Norwegian–English dictionary" — *abstrakt* III, *hus*,
  *holde på* (no class), *vei, veg*, and the shared-class pair *fange* I / II (both nouns: the
  numerals stay); the dictionary name read from the strings table, not written into the code.
* **the descriptions** (128, template H at 155 characters): *abstrakt* III and *gå* as the lab
  wrote them, the untranslated *abstrakt* I ("Not yet in English: …"), a page with no senses
  (today's text, unchanged); over every built page, at most 155 characters and never "….".
  The lab's nine samples are checked against its own outputs (`descriptions.json`) where the lab
  files are there.
* **the home page's description** (Robin, 2026-10-25): its sentence, word for word, with the
  build's count of translated articles — the About page's figure, with its thousands comma.
* **the sitemap and robots.txt**: `/sitemap.xml` lists home, About and Help and the indexed
  article pages, no `noindex` page — since site decisions 117 (2026-10-25) less the articles whose
  canonical is now their word page (sampled: each of those points to a word page), which the
  word pages stand for (until 117 its count equalled `build.json`'s and the translated pages'
  plus three); `/robots.txt` allows all and names the sitemap; Google Search Console's ownership
  file ships at the root as Google gave it.
* **History rows unchanged** (§ 4 of the brief): the text a History row, a favourite or a
  one-article search takes from a page (`data-snip`, else the meta description — `lookup.js`
  `pageMeta`, `personal.js` `fieldsFrom`) is pinned for nine pages as the build before 128 gave
  it, and over every page it equals the list view's snippet (`build-snippets.json`, cut as
  `snip/`), so the new description never shows on the site itself.

`ORDPAR_TEST_OUT=<folder>` runs the built-site checks against another build (a copy of the pages
from before 128 fails them: every page `noindex`, the old titles and descriptions, no tags, no
sitemap). The built-site checks are skipped when the folder holds no build.
"""
import html
import json
import os
import re
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ordpar.sitegen import describe as D  # noqa: E402
from ordpar.sitegen import head as H  # noqa: E402
from ordpar.sitegen import about as A  # noqa: E402
from ordpar.sitegen.strings import EN  # noqa: E402
from ordpar import build_index as BI  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
LAB = os.path.join(ROOT, "docs", "sessions", "2026-09-19-ordpar-site-review", "evidence")
DICT = " — Norwegian–English dictionary"

# the lab's template H at 155 (descriptions.json, 2026-10-25), since site decisions 154 (Robin,
# 2026-10-31) with the headword first, the 155 characters including it (`describe.description`'s
# `word`): *gå*'s first definition is cut one comma earlier for it. Before 154: "abstract.
# Definition: …", "to walk · … to travel on foot …", "Not yet in English: 1. …"
ABSTRAKT_III = ("abstrakt: abstract. Definition: 1. which can only be grasped by thought; detached from the "
                "world of the senses; opposite of concrete …")
GAA = ("gå: to walk · to go · to run, to work (of a machine) · to turn out. Definition: 1. with a "
       "person or being as subject: to move step by step …")
ABSTRAKT_I = ("abstrakt I (not yet in English): 1. uhåndgripelig eller tenkt fenomen; 2. i språkvitenskap: "
              "substantiv med abstrakt (III, 1) betydning")

# what a History row showed for these pages in the build before 128 (2026-10-25T11:49)
HISTORY_BEFORE = {
    98: "abstract",
    97: "uhåndgripelig eller tenkt fenomen",
    102828: "to be in the middle of, to be busy doing · to keep at it, to carry on · to…",
    13787: "as much as one can hold in one's arms",
    21740: "to walk · to go · to run, to work (of a machine) · to turn out",
    24627: "a house · a building",
    67204: "road · way · route · distance",
    124369: "playing time (that a player gets on the pitch) · playing time, normal time…",
    100502: "",
}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)">')
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]*)">')
HTML_TAG = re.compile(r"<html\b[^>]*>")


def _read(*parts):
    p = os.path.join(*parts)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return f.read()


def page(path):
    """The built page at a site path ("/bm-en/98/", "/", "/404.html")."""
    rel = path.strip("/")
    if not rel.endswith(".html"):
        rel = os.path.join(rel, "index.html") if rel else "index.html"
    return _read(OUT, rel)


def head(text):
    return text[:text.index("</head>")]


def meta(text, prop):
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)">' % re.escape(prop), head(text))
    return html.unescape(m.group(1)) if m else None


def title(text):
    return html.unescape(TITLE_RE.search(text).group(1))


def description(text):
    m = DESC_RE.search(head(text))
    return html.unescape(m.group(1)) if m else None


def history_text(text):
    """What a History row / favourite takes from a page: `data-snip`, else the description."""
    tag = HTML_TAG.search(text).group(0)
    m = re.search(r'\sdata-snip="([^"]*)"', tag)
    if m:
        return html.unescape(m.group(1))
    return description(text) or ""


BUILT = os.path.isdir(os.path.join(OUT, "bm-en")) and page("/bm-en/98/") is not None


# --- the code, no build needed ------------------------------------------------

class Code(unittest.TestCase):

    def test_pos_class(self):
        self.assertEqual(D.pos_class("noun (neuter)"), "noun")
        self.assertEqual(D.pos_class("noun (masculine, feminine or neuter)"), "noun")
        self.assertEqual(D.pos_class("determiner (quantifier)"), "determiner")
        self.assertEqual(D.pos_class("verb"), "verb")
        self.assertIsNone(D.pos_class("fixed expression"))
        self.assertIsNone(D.pos_class(""))

    def test_titles(self):
        s = dict(EN)
        abst = [{"form": "abstrakt", "homograph": "III"}]
        self.assertEqual(D.page_title(abst, "adjective", False, s), "abstrakt (adjective)" + DICT)
        self.assertEqual(D.page_title([{"form": "fange", "homograph": "I"}], "noun", True, s),
                         "fange I (noun)" + DICT)
        self.assertEqual(D.page_title([{"form": "holde på", "homograph": None}], None, False, s),
                         "holde på" + DICT)
        two = [{"form": "vei", "homograph": None}, {"form": "veg", "homograph": None}]
        self.assertEqual(D.page_title(two, "noun", False, s), "vei, veg (noun)" + DICT)
        # the second half is the pair's name from the strings table, not a fixed string
        s["dictionary_name"] = "Norwegian–Polish dictionary"
        self.assertEqual(D.page_title(abst, "adjective", False, s),
                         "abstrakt (adjective) — Norwegian–Polish dictionary")

    def test_shared_class(self):
        forms = {"fange": [1, 2, 3]}
        cls = {1: "noun", 2: "noun", 3: "verb"}
        f = lambda aid, c: D.shared_class(aid, ["fange"], c, lambda w: forms.get(w, []), cls.get)
        self.assertTrue(f(1, "noun"))
        self.assertFalse(f(3, "verb"))

    def test_description_rules(self):
        g = ["abstract"]
        defs = ["which can only be grasped by thought; detached from the world of the senses; "
                "opposite of concrete",
                "about a noun: denoting an idea, a quality or a state, not a concrete thing"]
        self.assertEqual(D.description(g, defs, True, word="abstrakt"), ABSTRAKT_III)   # 154
        self.assertEqual(D.description(g, defs, True), ABSTRAKT_III[len("abstrakt: "):])  # no word: as 128
        self.assertLessEqual(len(ABSTRAKT_III), D.CAP)
        # a lone definition is unnumbered; no definitions: today's text
        self.assertEqual(D.description(["a"], ["b"], True), "a. Definition: b")
        self.assertEqual(D.description(["a"], [], True, "a"), "a")
        self.assertEqual(D.description([], [], False, "nb text"), "nb text")
        # the glosses are never cut: too little room left, the glosses alone with one stop
        long_g = ["x" * 70, "y" * 60]
        out = D.description(long_g, ["z " * 40], True)
        self.assertEqual(out, " · ".join(long_g) + ".")
        self.assertNotIn("Definition", out)
        # never "…."
        self.assertNotIn("….", D.description(["a …"], [], True, "a …"))
        self.assertNotIn("….", D.description(["a …"], ["w " * 100], True))

    def test_lab_samples(self):
        """The lab's nine samples, from its harvest, give its own H outputs."""
        samples = _read(LAB, "style-lab", "preview-samples.json")
        outs = _read(LAB, "preview-lab-127-128-2026-10-25", "descriptions.json")
        if not (samples and outs):
            self.skipTest("the lab's files are not here")
        outs = json.loads(outs)
        for a in json.loads(samples)["samples"]:
            glosses = a["description_today"].split(" · ") if a["translated"] and a["gloss_line"] else []
            got = D.description(glosses, a["definitions"], a["translated"], a["description_today"])
            self.assertEqual(got, outs[str(a["id"])]["H"]["text"], a["id"])

    def test_home_description(self):
        stats = A.SAMPLE
        text = D.home_description(stats, EN)
        self.assertEqual(text, "Ordpar: a Norwegian–English dictionary built on Bokmålsordboka. "
                               "21,873 of its articles are translated into English so far; the "
                               "rest are shown in Norwegian.")
        self.assertIn(A.numbers(stats)["translated"][1], text)

    def test_social_tags(self):
        t = H.social_tags("/bm-en/98/", "abstrakt (adjective)" + DICT, 'a "b"')
        for line in ('<meta property="og:type" content="website">',
                     '<meta property="og:site_name" content="Ordpar">',
                     '<meta property="og:url" content="https://ordpar.no/bm-en/98/">',
                     '<meta property="og:description" content="a &quot;b&quot;">',
                     '<meta property="og:image" content="https://ordpar.no/site/og/ordpar.png">',
                     '<meta property="og:image:width" content="1200">',
                     '<meta property="og:image:height" content="630">',
                     '<meta property="og:image:alt" content="Ordpar: Norwegian–English dictionary">',
                     '<meta name="twitter:card" content="summary_large_image">'):
            self.assertIn(line, t)
        self.assertNotIn("og:description", H.social_tags("/", "t", ""))

    def test_picture_and_robots_source(self):
        src = os.path.join(ROOT, "ordpar", "site", "og", "ordpar.png")
        lab = os.path.join(LAB, "preview-lab-127-128-2026-10-25", "picked-ordpar-preview-1200x630.png")
        with open(src, "rb") as f:
            png = f.read()
        self.assertEqual(png[16:24], (1200).to_bytes(4, "big") + (630).to_bytes(4, "big"))
        if os.path.exists(lab):
            with open(lab, "rb") as f:
                self.assertEqual(png, f.read(), "the picture is Robin's file, as is")
        robots = _read(ROOT, "ordpar", "root", "robots.txt")
        self.assertEqual(robots, "User-agent: *\nAllow: /\n\nSitemap: https://ordpar.no/sitemap.xml\n")
        # Google Search Console's ownership file (Robin, 2026-10-25): Google re-checks it, so it
        # stays at the root for good, byte for byte as Google gave it.
        self.assertEqual(_read(ROOT, "ordpar", "root", GOOGLE), GOOGLE_BODY)


GOOGLE = "google1a7a4e06bc7a50c5.html"
GOOGLE_BODY = "google-site-verification: " + GOOGLE   # no newline at the end, as given


# --- the built site -------------------------------------------------------------

INDEXED = ("/bm-en/98/", "/", "/about/", "/help/", "/coming/")   # /coming/: decisions 131
NOINDEX = ("/bm-en/97/", "/bm-en/", "/history/", "/favourites/", "/settings/", "/404.html")
URLS = {"/": "https://ordpar.no/", "/bm-en/": "https://ordpar.no/bm-en/",
        "/about/": "https://ordpar.no/about/", "/help/": "https://ordpar.no/help/",
        "/coming/": "https://ordpar.no/coming/",
        "/history/": "https://ordpar.no/history/", "/favourites/": "https://ordpar.no/favourites/",
        "/settings/": "https://ordpar.no/settings/", "/404.html": "https://ordpar.no/404.html"}


@unittest.skipUnless(BUILT, "no built site in %s" % OUT)
class Built(unittest.TestCase):

    def test_a_noindex_by_kind(self):
        for p in INDEXED:
            self.assertNotIn(H.ROBOTS_NOINDEX, head(page(p)), p)
        for p in NOINDEX:
            self.assertIn(H.ROBOTS_NOINDEX, head(page(p)), p)

    def test_b_noindex_exactly_on_the_untranslated_pages(self):
        ids = [e.name for e in os.scandir(os.path.join(OUT, "bm-en")) if e.name.isdigit()]

        def one(aid):
            t = _read(OUT, "bm-en", aid, "index.html")
            if t is None:
                return None
            h = head(t)
            tr = 'data-translated="1"' in t[:2000]
            d = description(t) or ""
            return (aid, tr, H.ROBOTS_NOINDEX in h, len(d), "…." in d)
        with ThreadPoolExecutor(8) as ex:
            rows = [r for r in ex.map(one, ids, chunksize=256) if r]
        bad = [r for r in rows if r[1] == r[2]]
        self.assertFalse(bad, "%d pages whose noindex does not follow data-translated: %r"
                         % (len(bad), bad[:10]))
        long = [r for r in rows if r[3] > D.CAP or r[4]]
        self.assertFalse(long, "%d descriptions over %d or with '….': %r" % (len(long), D.CAP, long[:10]))
        Built.translated = sorted(int(r[0]) for r in rows if r[1])

    def test_c_tags_on_each_kind_of_page(self):
        for p in ("/bm-en/98/", "/bm-en/97/", "/bm-en/102828/") + tuple(URLS):
            t = page(p)
            self.assertIsNotNone(t, p)
            self.assertEqual(meta(t, "og:title"), title(t), p)
            self.assertEqual(meta(t, "og:description"), description(t) or None, p)
            canon = CANON_RE.search(head(t))
            self.assertEqual(meta(t, "og:url"), canon.group(1) if canon else URLS[p], p)
            self.assertEqual(meta(t, "og:type"), "website", p)
            self.assertEqual(meta(t, "og:site_name"), "Ordpar", p)
            self.assertEqual(meta(t, "og:image"), "https://ordpar.no/site/og/ordpar.png", p)
            self.assertEqual(meta(t, "og:image:width"), "1200", p)
            self.assertEqual(meta(t, "og:image:height"), "630", p)
            self.assertEqual(meta(t, "og:image:alt"), "Ordpar: Norwegian–English dictionary", p)
            self.assertEqual(meta(t, "twitter:card"), "summary_large_image", p)
        self.assertTrue(os.path.exists(os.path.join(OUT, "site", "og", "ordpar.png")))

    def test_d_titles(self):
        want = {98: "abstrakt (adjective)", 24627: "hus (noun)", 102828: "holde på",
                67204: "vei, veg (noun)", 13789: "fange I (noun)", 13787: "fange II (noun)",
                21740: "gå (verb)"}
        for aid, w in want.items():
            self.assertEqual(title(page("/bm-en/%d/" % aid)), w + DICT, aid)

    def test_e_descriptions(self):
        self.assertEqual(description(page("/bm-en/98/")), ABSTRAKT_III)
        self.assertEqual(description(page("/bm-en/21740/")), GAA)
        self.assertEqual(description(page("/bm-en/97/")), ABSTRAKT_I)
        # a page with no senses (pikk III: set phrases only): its description as before, empty
        t = page("/bm-en/100502/")
        self.assertNotIn("Senses and Example Sentences", t)
        self.assertEqual(description(t), "")

    def test_f_home_description_is_the_about_figure(self):
        b = json.loads(_read(OUT, "build.json"))
        n = A.numbers(b["site_stats"])["translated"][1]
        want = D.home_description(b["site_stats"], EN)
        self.assertRegex(want, r"^Ordpar: a Norwegian–English dictionary built on Bokmålsordboka\. "
                               r"\d{1,3}(,\d{3})* of its articles are translated into English so "
                               r"far; the rest are shown in Norwegian\.$")
        for p in ("/", "/bm-en/"):
            self.assertEqual(description(page(p)), want, p)
        self.assertIn(n + " of them have been translated",
                      re.sub(r"<[^>]+>", "", page("/about/")).replace("\n", " "))

    def test_g_sitemap(self):
        sm = _read(OUT, "sitemap.xml")
        self.assertIsNotNone(sm, "no sitemap.xml")
        locs = re.findall(r"<loc>([^<]+)</loc>", sm)
        self.assertEqual(len(locs), len(set(locs)))
        self.assertNotIn("<lastmod>", sm)
        # since site decisions 131 (2026-10-26) "Coming to Ordpar" after Help, and since 142
        # (2026-10-27) "More ways to use Ordpar" after it
        self.assertEqual(locs[:5], ["https://ordpar.no/", "https://ordpar.no/about/",
                                    "https://ordpar.no/help/", "https://ordpar.no/coming/",
                                    "https://ordpar.no/more/"])
        ids = sorted(int(m) for m in re.findall(r"/bm-en/(\d+)/", sm))
        if not hasattr(Built, "translated"):
            self.test_b_noindex_exactly_on_the_untranslated_pages()
        # every indexed article, no noindex page — but, since site decisions 117 (2026-10-25), the
        # articles whose canonical page is now their word page are listed by that page instead
        # (the sitemap lists canonical pages only); the word and form pages are
        # `test_ordpar_wordpages117.py`'s. Moved with 117: until then exactly the translated
        # articles plus the three, `build.json`'s `indexed_pages`.
        moved = [a for a in Built.translated if a not in set(ids)]
        self.assertTrue(set(ids) <= set(Built.translated))
        for aid in moved[:200] + moved[-200:]:
            canon = CANON_RE.search(head(page("/bm-en/%d/" % aid))).group(1)
            self.assertRegex(canon, r"^https://ordpar\.no/bm-en/[^/0-9][^/]*/$", aid)
        words = [u for u in locs if re.search(r"/bm-en/[^/0-9][^/]*/$", u)]
        # site decisions 166 (2026-11-05): "Thanks to our readers" is listed while reports are on,
        # exactly when the build wrote the page
        thanks = [u for u in locs if u == "https://ordpar.no/thanks/"]
        self.assertEqual(bool(thanks), os.path.exists(os.path.join(OUT, "thanks", "index.html")))
        # site decisions 175, 177 (2026-11-07): the three change lists after More
        self.assertEqual(locs[5:8], ["https://ordpar.no/changes/", "https://ordpar.no/dictionary-changes/",
                                     "https://ordpar.no/deck-changes/"])
        self.assertEqual(len(locs), 8 + len(ids) + len(words) + len(thanks))
        robots = _read(OUT, "robots.txt")
        self.assertIn("Sitemap: https://ordpar.no/sitemap.xml", robots or "")
        self.assertEqual(_read(OUT, GOOGLE), GOOGLE_BODY)   # served at the root

    def test_h_history_rows_unchanged(self):
        for aid, before in HISTORY_BEFORE.items():
            self.assertEqual(history_text(page("/bm-en/%d/" % aid)), before, aid)

    def test_i_history_text_is_the_snippet_everywhere(self):
        path = os.path.join(ROOT, "ordpar", ".build", "build-snippets.json")
        if not os.path.exists(path) or os.environ.get("ORDPAR_TEST_OUT"):
            self.skipTest("no build-snippets.json for this build")
        with open(path, encoding="utf-8") as f:
            snips = json.load(f)

        def one(aid):
            t = _read(OUT, "bm-en", aid, "index.html")
            if t is None or aid not in snips:
                return None
            want = BI.snippet_text(snips[aid][0])
            got = history_text(t)
            return None if got == want else (aid, got, want)
        with ThreadPoolExecutor(8) as ex:
            bad = [r for r in ex.map(one, list(snips), chunksize=256) if r]
        self.assertFalse(bad, "%d pages whose History text is not their snippet: %r" % (len(bad), bad[:5]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
