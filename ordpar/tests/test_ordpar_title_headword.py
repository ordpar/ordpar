"""Site decisions 93 (2), 100 (1), 128: every article page's `<title>` is its headword line.

Since the follow-up build (93) the page's `<title>`, `data-lemma` and the "N more entries" link
follow the headword line (the mirror's spellings and numerals, in our order: `build_site.py`,
`head_lemmas`), "so the title and the line never disagree". Since 128 (Robin, 2026-10-25) the
title is "word (class) — Norwegian–English dictionary" (`sitegen/describe.py` `page_title`): the
headword line WITHOUT its homograph numerals — or with them, where another page shares a spelling
and the class — then the page's word class in brackets (none for a set phrase), then the pair's
dictionary name. This holds that over every built page, `ordpar/out/bm-en/*/index.html`, pure
Python over the files:

* the headword line is the text of the article head's `.ordpar-hw` lines (the `h1` and, for an
  article with several paradigm groups, its `p` siblings — decisions 36), the homograph numeral
  included as drawn ("dyp II") and its visually hidden reading ("homograph 2") left out, as a
  sighted reader sees it; several lines join with ", ", as the title joins every spelling; the
  same line without the numerals is the bare line;
* the class is the head's first `.ordbok-pos` label without its `<i>` (the gender or subclass);
* the title must be the bare line or the line, then " (class)" where the head has a class, then
  the dictionary name.

Until 128 the title was the line then " — Ordpar" (an untranslated page's " — Ordpar (Norwegian
only)"); this test was rewritten for the new form on 2026-10-25.

Expected: 0 mismatches. The three articles with no lemma at all (`NO_LEMMA`) were the known
exception until site decisions 163 (Robin, 2026-11-04) gave them no page; since then their pages
must be absent (`test_no_page_without_a_headword` — fails on a build from before 163). Skipped when
`ordpar/out/` holds no build. About 10–20 s over all pages (threaded reads).
"""
import html
import os
import re
import unittest
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo
PAGES = os.path.join(ROOT, "ordpar", "out", "bm-en")

TITLE = re.compile(r"<title>(.*?)</title>", re.S)
HW = re.compile(r'<(h1|p) class="ordpar-hw"[^>]*>(.*?)</\1>', re.S)
SR = re.compile(r'<span class="sr-only"[^>]*>.*?</span>', re.S)   # [^>]*: data-nosnippet (site decisions 154)
#: the CEFR level box (site decisions 187), last in the `h1` and off by default: not part of the headword
LEVEL = re.compile(r'<span class="ordpar-level".*?</span></span>', re.S)
NUM = re.compile(r'<span class="ordbok-homograph"[^>]*>.*?</span>', re.S)
POS = re.compile(r'<span class="ordbok-pos"[^>]*>(.*?)</span>', re.S)
TAG = re.compile(r"<[^>]+>")
DICT = " — Norwegian–English dictionary"

# Three articles the mirror gives NO lemma (`"lemmas": []` in bm-articles.jsonl, 2026-10-23 and
# 2026-11-03). Until site decisions 163 each had a page with an empty head line and the id as its
# title, excused here; since 163 they have no page at all (`build_site.py`, `Mirror.has_headword`).
NO_LEMMA = {"134445", "136424", "136509"}


def text(fragment):
    return " ".join(html.unescape(TAG.sub("", fragment)).split())


def title_and_lines(page):
    """(title, the titles the head allows) of one page's HTML; None where absent."""
    m = TITLE.search(page)
    title = " ".join(html.unescape(m.group(1)).split()) if m else None
    head = page.find('class="ordbok-head"')                 # the article head: no div inside it
    end = page.find("</div>", head) if head >= 0 else -1
    if head < 0:
        return title, None
    found = list(HW.finditer(page, head, end))
    if not found:
        return title, None
    line = ", ".join(text(SR.sub("", LEVEL.sub("", x.group(2)))) for x in found)
    bare = ", ".join(re.sub(r" ,", ",", text(NUM.sub("", SR.sub("", LEVEL.sub("", x.group(2)))))) for x in found)
    pos = POS.search(page, head, end)
    cls = text(re.sub(r"<i>.*?</i>", "", pos.group(1))) if pos else ""
    tail = (" (%s)" % cls if cls else "") + DICT
    return title, {bare + tail, line + tail}


def _check(aid):
    try:
        with open(os.path.join(PAGES, aid, "index.html"), encoding="utf-8") as f:
            page = f.read()
    except FileNotFoundError:
        return None
    title, allowed = title_and_lines(page)
    if title is None or not allowed or title not in allowed:
        return (aid, title, sorted(allowed or []))
    return None


@unittest.skipUnless(os.path.isdir(PAGES), "no built site in ordpar/out/bm-en/")
class TitleIsHeadwordLine(unittest.TestCase):

    def test_reader(self):
        page = ('<title>dyp (adjective)' + DICT + '</title><div class="ordbok-head">'
                '<h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma">dyp</span> <span class="ordbok-homograph" '
                'aria-hidden="true">II</span><span class="sr-only"> homograph 2</span><span class="ordbok-lemma">, </span>'
                '<span class="ordbok-lemma">djup</span> <span class="ordbok-homograph" aria-hidden="true">II</span>'
                '<span class="sr-only"> homograph 2</span></h1><span class="ordbok-pos">adjective</span></div>')
        self.assertEqual(title_and_lines(page)[1], {"dyp, djup (adjective)" + DICT,
                                                     "dyp II, djup II (adjective)" + DICT})
        two = ('<title>a, b (noun)' + DICT + '</title><div class="ordbok-head"><h1 class="ordpar-hw" lang="nb">a</h1>'
               '<span class="ordbok-pos">noun <i>neuter</i></span><p class="ordpar-hw" lang="nb">b</p></div>')
        t, allowed = title_and_lines(two)
        self.assertIn(t, allowed)
        phrase = ('<title>holde på' + DICT + '</title><div class="ordbok-head"><h1 class="ordpar-hw">holde på</h1></div>')
        t, allowed = title_and_lines(phrase)
        self.assertIn(t, allowed)

    def test_every_page_title_is_its_headword_line(self):
        # the article pages only: since site decisions 117 `bm-en/` also holds the word pages and
        # form pages (`bm-en/<word>/`), whose titles are 117's (`test_ordpar_wordpages117.py`)
        ids = [e.name for e in os.scandir(PAGES) if e.is_dir() and e.name.isdigit()]
        with ThreadPoolExecutor(8) as ex:
            bad = [r for r in ex.map(_check, ids, chunksize=256) if r]
        self.assertGreater(len(ids), 1000, "too few pages in %s" % PAGES)
        if bad:
            self.fail("%d of %d pages: <title> differs from the headword line (decisions 93, 128):\n%s"
                      % (len(bad), len(ids), "\n".join("%s: title %r, allowed %r" % b for b in sorted(bad)[:50])))

    def test_no_page_without_a_headword(self):
        # site decisions 163: an article with no headword has no page (until then, an empty head)
        left = sorted(a for a in NO_LEMMA if os.path.exists(os.path.join(PAGES, a)))
        self.assertEqual(left, [], "pages for articles with no headword (site decisions 163)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
