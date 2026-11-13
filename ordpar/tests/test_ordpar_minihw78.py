# -*- coding: utf-8 -*-
"""Pins site-review decisions 77 and 78 (Robin, 2026-10-21). The style lab's variants are
`docs/sessions/2026-09-19-ordpar-site-review/evidence/style-lab/minihead.html`.

* 77: the hover peek, arrow included, never takes the pointer, so a click where the arrow
  overlaps the word reaches the word's label.
* 78: the mini's headword is upright, in the text's colour, with the article body's link
  underline by default (the lab's variant 5); the Style setting `minihw` = article puts
  `ordpar-minihw-article` on <html> (head script and shell alike) and keeps the headword's own
  colour without the underline; the settings page notes under that choice that it is still a
  link; the export carries the setting.

Stdlib unittest."""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
SITE = os.path.join(ROOT, "ordpar", "site")
sys.path.insert(0, ROOT)

from ordpar.sitegen import head, page  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class Peek77(unittest.TestCase):

    def test_peek_takes_no_pointer(self):
        self.assertIn(".ordbok-xpeek{max-width:calc(100vw - 1rem);pointer-events:none}", page.article_css())


class MiniHeadword78(unittest.TestCase):

    def test_css(self):
        css = page.article_css()
        self.assertIn(".mini-hw{font-style:normal}", css)
        self.assertIn("html:not(.ordpar-minihw-article) .mini-hw{color:inherit}", css)
        self.assertIn("html:not(.ordpar-minihw-article) .mini-hw a{text-decoration:underline;", css)
        self.assertIn("html.nightMode:not(.ordpar-minihw-article) .mini-hw a{", css)
        self.assertNotIn("@DAY@", css)
        # after the deck's own mini rules, which it overrides
        self.assertGreater(css.index("html:not(.ordpar-minihw-article) .mini-hw a"),
                           css.index(".mini-hw a,.nightMode .mini-hw a{color:inherit;text-decoration:none}"))

    def test_setting(self):
        self.assertIn("s.getItem('minihw')==='article'&&c.add('ordpar-minihw-article')", head.THEME_JS)
        js = _read(SITE, "shell.js")
        # under Article → Small articles since decisions 85 (Style until then); key and values kept
        self.assertIn("{ key: 'minihw', values: ['link', 'article'], def: 'link', section: 'article', sub: 'mini' }",
                      js)
        self.assertIn("cl.toggle('ordpar-minihw-article', getSetting('minihw') === 'article');", js)
        self.assertIn("'minihw'", _read(SITE, "personal.js").split("SETTING_KEYS = ")[1].split(";")[0])
        strings = json.loads(_read(SITE, "strings", "en.json"))
        for k in ("settings.minihw", "settings.minihw.link", "settings.minihw.article",
                  "settings.minihw.article.note"):
            self.assertIn(k, strings)
        self.assertIn("still a link", strings["settings.minihw.article.note"])
        self.assertIn("'settings.' + sp.key + '.' + ch.value + '.note'", _read(SITE, "settings.js"))


if __name__ == "__main__":
    unittest.main()
