"""Site-review decisions 114, last paragraph (Robin, 2026-10-24): the deck's minis take their body at the card's own size.

Robin, to the session's view that the deck follows the site, the body to the card's size: "yes".
The deck card's text (`ordbok_gen._CARD_CSS` `.ordbok`, and its definitions) sets no size of its
own, so it is the page's 1rem; the mini's header is 1.1rem and its gloss 1rem (114's pick).
What it pins, in `mini.STYLE` (the deck's stylesheet, shared with the site's):

* the mini's body lines — `.mini-sline` (a numbered sense), `.mini-single` (an unnumbered line)
  and `.mini-nodef` (no definition) — are each `font-size:1rem`, the card's own size; none is
  left at the .92rem they had until this build;
* the card's text sets no size of its own: `.ordbok` carries no `font-size` (were it to gain one,
  "the card's own size" would no longer be 1rem and this test would say so);
* the header's rules are 114's: `.mini-head` 1.1rem, `.mini-gloss` 1rem semibold.

Fails on the build before (each of the three at .92rem). The look itself, measured in a card
rendered through `build_cards.build_card` (*hus*, its mini *bosted*), light and night, is in the
build's report.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ordbok_gen as g  # noqa: E402
import mini  # noqa: E402


def rule(css, selector):
    """The declarations of the one rule whose selector is exactly `selector`."""
    found = re.findall(r"(?m)^" + re.escape(selector) + r"\{([^}]*)\}", css)
    return found


class DeckMiniBody(unittest.TestCase):

    def test_the_body_lines_at_the_cards_size(self):
        for sel in (".mini-sline", ".mini-single", ".mini-nodef"):
            found = rule(mini.STYLE, sel)
            self.assertEqual(len(found), 1, "%s: one rule expected, found %r" % (sel, found))
            self.assertIn("font-size:1rem", found[0].split(";"), "%s{%s}" % (sel, found[0]))
            self.assertNotIn(".92rem", found[0], "%s{%s}" % (sel, found[0]))

    def test_the_card_text_sets_no_size(self):
        found = rule(g._CARD_CSS, ".ordbok")
        self.assertEqual(len(found), 1, found)
        self.assertNotIn("font-size", found[0])

    def test_the_header_as_ruled(self):
        self.assertIn("font-size:1.1rem", rule(mini.STYLE, ".mini-head")[0])
        gloss = rule(mini.STYLE, ".mini-gloss")[0]
        self.assertIn("font-size:1rem", gloss)
        self.assertIn("font-weight:600", gloss)


if __name__ == "__main__":
    unittest.main()
