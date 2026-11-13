"""Site-review decisions 111 (Robin, 2026-10-23): the examples' English behind a reveal, and the cue in grey.

1. **The setting.** `examples` = both (default, listed first, 107) | no, under Article -> Language,
   beside Definitions (`ordparShell.SETTINGS`); its words in `strings/en.json` in the `defs`
   pattern, the hint ("For practising your Norwegian …") one string, `settings.examples.no.note`;
   the class `ordpar-examples-no` set by the head script before the first paint (`head.THEME_JS`)
   and by `shell.js` on a change (`CLASS_KEYS`, `applyClassKeys`); carried by an export
   (`personal.js` `SETTING_KEYS`).
2. **The reveal.** The same cue as `defs = no`'s (`ordbok-cue ordpar-encue`, `.ordpar-excue`
   besides) inserted before each example's English by the page script (`excues`, run from
   `ordparDefs`, exported as `ordparExCues` for the mini script); the sheet hides the English of
   an unopened example and shows its cue; a click on an opened example's English closes it.
3. **The cue in the muted grey** (Robin, 2026-10-23: "faded grey, to make it less prominent"):
   the deck's `.ordbok-cue` text #757070 (night #b9b6b6), the site's through `--ordpar-muted`;
   the border as before.

The browser side (hidden, revealed, in every place): `test_ordpar_browser_examples111.py`.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import ordbok_gen  # noqa: E402  -- first: mini imports it back for STYLE
from ordpar.sitegen import head, page  # noqa: E402

SITE = os.path.join(ROOT, "ordpar", "site")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class TheSetting(unittest.TestCase):
    js = _read(SITE, "shell.js")
    strings = json.loads(_read(SITE, "strings", "en.json"))

    def test_the_entry_beside_definitions(self):
        self.assertIn("{ key: 'examples', values: ['both', 'no'], def: 'both', section: 'article', "
                      "sub: 'language' }", self.js)
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        self.assertEqual(order[order.index("defs") + 1], "examples")

    def test_the_words(self):
        s = self.strings
        self.assertEqual(s["settings.examples"], "Examples")
        self.assertEqual(s["settings.examples.both"], "Norwegian and English")
        self.assertEqual(s["settings.examples.no"], "Norwegian, with the English hidden until revealed")
        self.assertEqual(s["settings.examples.no.note"], "For practising your Norwegian: read the example "
                         "first, then click \"Show English\" under it to check yourself.")   # reworded by 126
        self.assertNotIn("settings.examples.both.note", s)
        # the same words as the Definitions setting's two
        self.assertEqual(s["settings.examples.both"], s["settings.defs.both"])
        self.assertEqual(s["settings.examples.no"], s["settings.defs.no"])

    def test_the_class_before_the_first_paint_and_on_a_change(self):
        # site decisions 152: Norwegian only (`L`) answers for the setting too
        self.assertIn("(L||s.getItem('examples')==='no')&&c.add('ordpar-examples-no')", head.THEME_JS)
        keys = re.search(r"var CLASS_KEYS = \[([^\]]*)\]", self.js).group(1)
        self.assertIn("'examples'", keys)
        self.assertIn("cl.toggle('ordpar-examples-no', eff('examples') === 'no');", self.js)

    def test_an_export_carries_it(self):
        keys = re.search(r"var SETTING_KEYS = \[([^\]]*)\]", _read(SITE, "personal.js")).group(1)
        self.assertIn("'examples'", keys)


class TheReveal(unittest.TestCase):
    css = page.article_css()
    js = page._PAGE_JS

    def test_the_sheet(self):
        for rule in ("html.ordpar-examples-no .ordbok-ex-list>li:not(.ordpar-open)>.ordpar-en{display:none}",
                     "html.ordpar-examples-no .ordbok-ex-list>li:not(.ordpar-open)>.ordpar-excue"
                     "{display:block;width:fit-content}"):
            self.assertIn(rule, self.css)

    def test_the_page_script(self):
        self.assertIn("bt.className='ordbok-cue ordpar-encue ordpar-excue'", self.js)
        self.assertIn("window.ordparExCues=excues;", self.js)
        self.assertIn("cues();excues();exheads();", self.js)
        self.assertIn("'.ordpar-open>span[lang=en],.ordbok-ex-list>li.ordpar-open>.ordpar-en'", self.js)

    def test_the_mini_script(self):
        mini = _read(SITE, "mini.js")
        self.assertIn("global.ordparExCues(box)", mini)
        self.assertIn("if (has(n, 'ordpar-open')) { n.classList.remove('ordpar-open'); }", mini)


class TheCueInGrey(unittest.TestCase):

    def test_the_deck(self):
        css = ordbok_gen._CARD_CSS
        cue = re.search(r"(^|\n)\.ordbok-cue\{([^}]*)\}", css).group(2)
        self.assertIn("color:#757070", cue)
        self.assertIn("border:1px solid #c4bcbd", cue)
        self.assertIn(".nightMode .ordbok-cue{color:#b9b6b6;border-color:#656161}", css)
        self.assertNotRegex(cue, "560027")

    def test_the_site(self):
        css = page.article_css()
        self.assertIn(".ordbok-cue{display:inline-block;font-size:.8em;color:var(--ordpar-muted,#757070);", css)
        self.assertIn(".nightMode .ordbok-cue{color:var(--ordpar-muted,#b9b6b6);", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
