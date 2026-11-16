"""Site-review decisions 107 (Robin, 2026-10-23): every setting lists its default first.

The ruling: each setting's default is the choice listed first (the mini spacing's default, "as
the article", had been listed second). The settings page
draws each setting's choices in the order of its `values` in `ordparShell.SETTINGS`
(`ordpar/site/shell.js`), so the rule is that each entry's `def` is its first value. The colour
choices come from the colour table (`sitegen/colours.py`), whose first scheme must be `DEFAULT`.

`ORDPAR_TEST_SHELL` names another copy of `shell.js` (to show the test failing on the version
before the fix: `git show <rev>:ordpar/site/shell.js`).
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo
ORDPAR = os.path.join(ROOT, "ordpar")
SHELL = os.environ.get("ORDPAR_TEST_SHELL") or os.path.join(ORDPAR, "site", "shell.js")

ENTRY = re.compile(r"\{\s*key:\s*'(\w+)'\s*,\s*values:\s*\[([^\]]*)\]\s*,\s*def:\s*'(\w+)'")


def settings_table(js):
    start = js.index("var SETTINGS = [")
    end = js.index("];", start)
    return [(m.group(1), [v.strip().strip("'\"") for v in m.group(2).split(",") if v.strip()], m.group(3))
            for m in ENTRY.finditer(js[start:end])]


class DefaultFirst(unittest.TestCase):

    def test_every_setting_lists_its_default_first(self):
        with open(SHELL, encoding="utf-8") as f:
            table = settings_table(f.read())
        self.assertGreaterEqual(len(table), 15, "the settings table was not read")
        wrong = ["%s: %s, default %s" % (key, values, default)
                 for key, values, default in table if values and values[0] != default]
        self.assertEqual(wrong, [], "settings whose default is not their first choice")

    def test_the_colour_table_starts_with_its_default(self):
        sys.path.insert(0, ORDPAR)
        from sitegen import colours
        self.assertEqual(colours.COLOURS[0]["id"], colours.DEFAULT)


if __name__ == "__main__":
    unittest.main()
