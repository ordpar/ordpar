"""Site decisions 137 (Robin, 2026-10-26): "We can drop the "translated" tag from the list views. The
"Norwegian only" tag alone is enough."

Every row that tags an article — a search's list rows and inflected-form rows (`lookup.js`), the
rows of Favourites and History (the same code), a word page's built rows (`sitegen/wordpages.py`
`_tag`) — tags only an untranslated article, "Norwegian only"; a translated one has no tag. (The
suggestions and History's links mark a translated word by colour, not a tag: unchanged.)

The source side always runs; the built side reads `ordpar/out/bm-en/fly/` (five entries, two
translated, three Norwegian-only, as on 2026-10-26) and is skipped without a build. Before this
build: fails on both (the source's `tag.translated`; the built page's two "translated" tags).
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
sys.path.insert(0, ORDPAR)
from sitegen import wordpages  # noqa: E402

OUT = os.path.join(ORDPAR, "out")


def read(*parts):
    with open(os.path.join(ORDPAR, *parts), encoding="utf-8") as f:
        return f.read()


class Source(unittest.TestCase):

    def test_a_lookup_js_tags_only_norwegian_only(self):
        js = read("site", "lookup.js")
        self.assertNotIn("tag.translated", js)
        self.assertNotIn("ordpar-tag is-translated", js)
        self.assertEqual(js.count("t('tag.norwegianOnly')"), 2, "the two row kinds")

    def test_b_strings_and_sheet(self):
        strings = json.loads(read("site", "strings", "en.json"))
        self.assertNotIn("tag.translated", strings)
        self.assertEqual(strings["tag.norwegianOnly"], "Norwegian only")
        self.assertNotIn(".ordpar-tag.is-translated", read("site", "shell.css"))

    def test_c_word_page_rows(self):
        s = {"tag.norwegianOnly": "Norwegian only"}
        self.assertEqual(wordpages._tag({"translated": True}, s), "")
        self.assertEqual(wordpages._tag({"translated": False}, s),
                         '<span class="ordpar-tag">Norwegian only</span>')


@unittest.skipUnless(os.path.exists(os.path.join(OUT, "bm-en", "fly", "index.html")), "no build")
class Built(unittest.TestCase):

    def test_d_fly_word_page(self):
        with open(os.path.join(OUT, "bm-en", "fly", "index.html"), encoding="utf-8") as f:
            page = f.read()
        tags = re.findall(r'<span class="ordpar-tag[^"]*">([^<]*)</span>', page)
        self.assertNotIn("translated", tags)
        self.assertEqual(tags.count("Norwegian only"), 3, tags)


if __name__ == "__main__":
    unittest.main(verbosity=2)
