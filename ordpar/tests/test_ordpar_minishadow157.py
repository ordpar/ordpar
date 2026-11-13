"""Site decisions 157 (Robin, 2026-11-01, his pick in the lab `style-lab/mini-shadow.html`): the small
article's shadow drawn deep enough to darken the page's text beside the box, the box lifted at night, and
the night page and surfaces a shade darker.

* **The box** (`page.SITE_CSS`): `.ordbok-xmini>.mini` (day) and `.nightMode .ordbok-xmini>.mini` (night,
  with the box #2c2629 and its border #3e3439) carry his shadows, over `mini.py`'s own `.mini` rules by
  specificity; the nested box (`.ordpar-mnest`) has no shadow of its own left, so it takes the same.
* **The night colours** (`shell.css`): `--ordpar-bg` #1b1819 and `--ordpar-surface` #242021 (the card,
  the header and every surface that shares the variable: one style); the day colours unchanged.

Stdlib unittest.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)

from sitegen import page  # noqa: E402


def _rules(css):
    """`{selector: declarations without spaces}` over every plain rule (comments dropped)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        for sel in m.group(1).split(","):
            sel = re.sub(r"\s+", " ", sel.strip())
            out.setdefault(sel, []).append(re.sub(r"\s+", "", m.group(2)))
    return out


def _block(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else ""


class TheBox(unittest.TestCase):

    def setUp(self):
        self.r = _rules(page.SITE_CSS)

    def test_a_day_shadow(self):
        self.assertIn("box-shadow:01px3pxrgba(60,20,40,.12),08px28pxrgba(60,20,40,.2)",
                      self.r.get(".ordbok-xmini>.mini", []))

    def test_b_night_shadow_and_colour(self):
        decl = "".join(self.r.get(".nightMode .ordbok-xmini>.mini", []))
        self.assertIn("box-shadow:01px3pxrgba(0,0,0,.5),010px36px4pxrgba(0,0,0,.8)", decl)
        self.assertIn("background:#2c2629", decl)
        self.assertIn("border-color:#3e3439", decl)

    def test_c_the_nested_box_takes_the_same(self):
        for sel in (".ordpar-mnest>.mini", ".nightMode .ordpar-mnest>.mini"):
            self.assertFalse(any("box-shadow" in d for d in self.r.get(sel, [])), sel)
        self.assertIn("overflow-y:auto;overscroll-behavior:contain", self.r.get(".ordpar-mnest>.mini", []))


class TheNightColours(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(ORDPAR, "site", "shell.css"), encoding="utf-8") as f:
            self.css = re.sub(r"/\*.*?\*/", "", f.read(), flags=re.S)

    def test_a_night(self):
        night = _block(self.css, "html.nightMode")
        self.assertRegex(night, r"--ordpar-bg:\s*#1b1819;")
        self.assertRegex(night, r"--ordpar-surface:\s*#242021;")

    def test_b_day_unchanged(self):
        day = _block(self.css, ":root")
        self.assertRegex(day, r"--ordpar-bg:\s*#fffdfd;")
        self.assertRegex(day, r"--ordpar-surface:\s*#ffffff;")


if __name__ == "__main__":
    unittest.main()
