# -*- coding: utf-8 -*-
"""Site-review decisions 113 (Robin, 2026-10-24): the search on a phone — the source side. Stdlib
unittest, pure Python.

* **The capital.** The site's one search field (`chrome.header`, on every page: the article,
  search, 404, settings, favourites and history pages) carries `autocapitalize="none"`, so a phone's
  keyboard starts in small letters, as ordbokene.no's field; the other attributes as before
  (`autocomplete="off"`, `spellcheck="false"`), no `autocorrect`. No page of `ordpar/site/` has a
  search field of its own.
* **The keyboard.** `shell.js` `submit` (a search by Enter, by a chosen suggestion or a Recent row)
  lets go of the field on a touch screen (`(pointer: coarse)`), so the keyboard closes; with a mouse
  the search page keeps the focus in the field, as before.

The browser side (the focus after each kind of search, the attribute on every page; fails on the
live site before the build): `test_ordpar_browser_search113.py`.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
SITE = os.path.join(ROOT, "ordpar", "site")

from ordpar.sitegen import chrome  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class TheField(unittest.TestCase):

    def test_small_letters(self):
        h = chrome.header(chrome.strings())
        inputs = re.findall(r"<input [^>]*>", h)
        self.assertEqual(len(inputs), 1)
        self.assertIn('autocapitalize="none"', inputs[0])
        self.assertIn('autocomplete="off"', inputs[0])
        self.assertIn('spellcheck="false"', inputs[0])
        self.assertNotIn("autocorrect", inputs[0])

    def test_no_other_search_field(self):
        for name in sorted(os.listdir(SITE)):
            if name.endswith(".html"):
                self.assertNotIn("<input", _read(SITE, name), name)


class TheKeyboard(unittest.TestCase):

    def test_submit_lets_go_on_a_touch_screen(self):
        js = _read(SITE, "shell.js")
        self.assertIn("global.matchMedia('(pointer: coarse)').matches", js)
        # `en`, the search's direction, since site decisions 148
        body = js.split("    function submit(value, en) {")[1].split("\n    }\n")[0]
        self.assertIn("if (touchFirst()) { input.blur(); }", body)
        self.assertIn("if (!touchFirst()) { input.focus(); }", body)
        self.assertLess(body.index("input.blur()"), body.index("searchHandler(query"))


if __name__ == "__main__":
    unittest.main()
