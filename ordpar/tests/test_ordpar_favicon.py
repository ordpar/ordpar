"""The site's icon in every page's head, for browsers and for Google Search (found 2026-10-26: Robin
saw Google list ordpar.no with its generic globe; no page declared an icon and `/favicon.ico`
answered 404).

Google reads the icon from a `<link rel="icon">` in the HOME page's head; the image must be square,
in a format it lists (PNG is one), at a stable address, crawlable
(`evidence/reports/google-favicon-2026-10-26-lookup-web.md` in the site review's session folder,
quoting developers.google.com/search/docs/appearance/favicon-in-search). One style: every page
carries the same line, so a browser tab shows the icon wherever a reader is.

Pinned over the code (`head.head_tags`) and the built site (`ordpar/out/`, or `ORDPAR_TEST_OUT`);
the [live] checks also run against a served site with `ORDPAR_TEST_BASE=https://ordpar.no` (they
fail there before the fix: no icon link on the home page).
"""
import os
import re
import struct
import sys
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ordpar.sitegen import head as H  # noqa: E402

OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")
BASE = (os.environ.get("ORDPAR_TEST_BASE") or "").rstrip("/")
ICON_RE = re.compile(r'<link rel="icon" type="image/png" sizes="(\d+)x(\d+)" href="([^"]+)">')
#: built pages of every kind: the home page, an article, a word page, About, Help, Coming, the
#: search page, the 404 shell, Settings
PAGES = ["index.html", "bm-en/98/index.html", "bm-en/da/index.html", "about/index.html",
         "help/index.html", "coming/index.html", "bm-en/index.html", "404.html",
         "settings/index.html"]


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


class Source(unittest.TestCase):
    def test_head_tags_carry_the_icon(self):
        for indexed in (True, False):
            m = ICON_RE.search(H.head_tags(indexed=indexed))
            self.assertTrue(m, "head_tags(indexed=%s) has no icon link" % indexed)
            self.assertEqual(m.group(3), H.ICON_HREF)
            self.assertEqual(m.group(1), m.group(2))

    def test_the_icon_file_is_a_square_png_of_its_stated_size(self):
        path = os.path.join(ROOT, "ordpar", H.ICON_HREF.lstrip("/").replace("/", os.sep))
        with open(path, "rb") as f:
            w, h = png_size(f.read(32))
        self.assertEqual(w, h)
        self.assertEqual("%dx%d" % (w, h), H.ICON_SIZES)


@unittest.skipUnless(os.path.isdir(OUT), "no built site at %s" % OUT)
class Built(unittest.TestCase):
    def test_every_kind_of_page_links_the_icon(self):
        for rel in PAGES:
            with open(os.path.join(OUT, rel.replace("/", os.sep)), encoding="utf-8") as f:
                head = f.read().split("</head>")[0]
            m = ICON_RE.search(head)
            self.assertTrue(m, "%s: no icon link in <head>" % rel)
            self.assertEqual(m.group(3), H.ICON_HREF, rel)

    def test_the_linked_file_is_built(self):
        self.assertTrue(os.path.isfile(os.path.join(OUT, H.ICON_HREF.lstrip("/").replace("/", os.sep))))


@unittest.skipUnless(BASE, "set ORDPAR_TEST_BASE to check a served site")
class Live(unittest.TestCase):
    def fetch(self, path):
        req = urllib.request.Request(BASE + path, headers={"User-Agent": "ordpar-test"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()

    def test_live_home_page_links_a_square_png(self):
        head = self.fetch("/").decode("utf-8").split("</head>")[0]
        m = ICON_RE.search(head)
        self.assertTrue(m, "the home page's head has no icon link")
        w, h = png_size(self.fetch(m.group(3))[:32])
        self.assertEqual((w, h), (int(m.group(1)), int(m.group(2))))
        self.assertEqual(w, h)


if __name__ == "__main__":
    unittest.main()
