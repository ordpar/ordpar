"""Site-review decisions 131 (2026-10-26): one style for the tab's title (117's open point (a); the
session's proposal, in 131's build). Headless Edge, `browser/tabtitle131.js`.

The rule: a search answered in place whose address is its own word page or form page shows that
page's built `<title>` — several entries and forms "*word* — Norwegian–English dictionary", one
article the article's own title (as before, 128); a search with no page of its own (`#q=`) keeps
"*q* — Ordpar". Until this build a search answered in place said "så — Ordpar" where loading
`/bm-en/så/` showed "så — Norwegian–English dictionary".

* **In place, from three pages** — the search page (`/bm-en/`), a word page (`/bm-en/hus/`) and the
  404 shell (`/bm-en/ingenslikside`): *så* (several entries) "så — Norwegian–English dictionary",
  *tær* (a form page) "tær — …", *vindu* (one article) its article's title, each equal to the built
  page's own `<title>` and at its address; the miss *husx* "husx — Ordpar" at `/bm-en/#q=husx`.
* **The list view on** (`listview` = on): *vindu* in one row still takes its article's title.
* **A sample of the built pages**: about forty word and form pages with a several-entry title (every
  capitalised one among them), each searched in place on the search page — the tab's title equals
  the page's built `<title>` (the page's word as the build picks it, `pageTitle`).
* **Loaded directly**: `/bm-en/#q=husx` keeps "husx — Ordpar"; `/bm-en/så/` its built title.

`ORDPAR_TEST_BASE=https://ordpar.no` runs it against the live site (before 131's deploy: fails —
"så — Ordpar" in place). The sample comes from `ordpar/out/` either way. Skipped without Edge, bun or
a build.
"""
import html
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "ordpar", "out")
DICT = " — Norwegian–English dictionary"
STARTS = ["/bm-en/", "/bm-en/hus/", "/bm-en/ingenslikside"]
QUERIES = ["så", "tær", "vindu", "husx"]
SITE = None
R = {}
SKIP = harness.skip_reason()
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


def built_title(word):
    p = os.path.join(OUT, "bm-en", word, "index.html")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        m = TITLE_RE.search(f.read(6000))
    return html.unescape(m.group(1)) if m else None


def sample(n=40):
    """Word and form pages whose title is the several-entry one, spread over the alphabet, every
    page whose title's word is capitalised first (at most 12)."""
    words = sorted(e.name for e in os.scandir(os.path.join(OUT, "bm-en"))
                   if e.is_dir() and not e.name.isdigit())
    several = []
    for w in words:
        t = built_title(w)
        if t and t.endswith(DICT) and "(" not in t and " " not in w:
            several.append((w, t))
    caps = [s for s in several if s[1][:1].isupper()][:12]
    step = max(1, len(several) // max(1, n - len(caps)))
    rest = [s for s in several[::step] if s not in caps][:n - len(caps)]
    return [{"q": w, "title": t} for w, t in caps + rest]


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_tabtitle131: skipped —", SKIP)
        return
    SITE = harness.Site()
    R["main"] = SITE.check("tabtitle131.js", dict(starts=STARTS, queries=QUERIES, sample=sample(),
                                                  direct=["/bm-en/#q=husx", "/bm-en/s%C3%A5/"]),
                           timeout=900)
    R["list"] = SITE.check("tabtitle131.js", dict(starts=["/bm-en/"], queries=["vindu"], listview="on"))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class TabTitle(unittest.TestCase):

    def test_a_in_place_from_every_start(self):
        want = {"så": built_title("så"), "tær": built_title("tær"), "vindu": built_title("vindu"),
                "husx": "husx — Ordpar"}
        self.assertEqual(want["så"], "så" + DICT)
        self.assertEqual(want["tær"], "tær" + DICT)
        self.assertEqual(want["vindu"], "vindu (noun)" + DICT)
        paths = {"så": "/bm-en/så/", "tær": "/bm-en/tær/", "vindu": "/bm-en/vindu/", "husx": "/bm-en/"}
        got = R["main"]["inplace"]
        self.assertEqual(len(got), len(STARTS) * len(QUERIES))
        for r in got:
            with self.subTest(start=r["start"], q=r["q"]):
                self.assertEqual(r["title"], want[r["q"]], r)
                self.assertEqual(r["path"], paths[r["q"]], r)

    def test_b_list_view_one_article(self):
        r = R["list"]["inplace"][0]
        self.assertEqual(r["title"], "vindu (noun)" + DICT, r)

    def test_c_the_built_pages_sample(self):
        got = R["main"]["sample"]
        self.assertGreaterEqual(len(got), 30)
        self.assertTrue(any(s["want"][:1].isupper() for s in got), "no capitalised page in the sample")
        bad = [s for s in got if s["title"] != s["want"]]
        self.assertEqual(bad, [], "%d of %d differ" % (len(bad), len(got)))

    def test_d_loaded_directly(self):
        d = {r["path"]: r["title"] for r in R["main"]["direct"]}
        self.assertEqual(d["/bm-en/#q=husx"], "husx — Ordpar")
        self.assertEqual(d["/bm-en/s%C3%A5/"], "så" + DICT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
