"""Site decisions 131 (the deck's request, promised by the site session, 2026-10-25): a pin on
`inflection.js` `mountAll`'s `script.textContent || script.innerHTML`.

The deck carries its paradigm islands in `<template>` elements (`deck/render.py` `editor_safe`,
decisions 34: Anki's editor deletes a field's scripts), and a template's `textContent` is empty —
its content is a separate document fragment — so the deck's inflection tables are drawn only
through the `innerHTML` fallback. In headless Edge (`browser/inflection131.js`): a real article's
island (*hus*, 24627) put into a `<template>`, a mount point naming it, the site's shipped
`inflection.js` evaluated in the page, `mountAll` called: the template's `textContent` is empty
and the table is drawn, with *hus*'s forms.

`ORDPAR_TEST_INFLECTION=<path>` tests another copy of the file (a copy without the fallback
fails: no table); `ORDPAR_TEST_BASE` serves another site (the page is fetched there; the file is
then that site's `/site/inflection.js`). Skipped without Edge, bun or a build.
"""
import os
import sys
import tempfile
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser"))
import harness  # noqa: E402

SITE = None
R = {}
SKIP = harness.skip_reason()


def _script_path():
    path = os.environ.get("ORDPAR_TEST_INFLECTION")
    if path:
        return path
    base = harness.base_override()
    if base:
        fd, path = tempfile.mkstemp(suffix=".js", prefix="ordpar-131-")
        with os.fdopen(fd, "wb") as f, urllib.request.urlopen(base.rstrip("/") + "/site/inflection.js") as r:
            f.write(r.read())
        return path
    return os.path.join(harness.OUT, "site", "inflection.js")


def setUpModule():
    global SITE
    if SKIP:
        print("test_ordpar_browser_inflection131: skipped —", SKIP)
        return
    SITE = harness.Site()
    R.update(SITE.check("inflection131.js", {"id": 24627, "path": _script_path()}))


def tearDownModule():
    if SITE:
        SITE.close()


@unittest.skipIf(SKIP, SKIP or "")
class TemplateIsland(unittest.TestCase):

    def test_a_the_template_has_no_text(self):
        self.assertEqual(R["textContent"], "")
        self.assertGreater(R["innerHTML"], 20)

    def test_b_the_table_is_drawn_from_it(self):
        self.assertEqual(R["mounted"], "1", R)
        self.assertGreaterEqual(R["tables"], 1, R)
        cells = " ".join(R["forms"])
        self.assertIn("huset", cells)
        self.assertIn("husene", cells)


if __name__ == "__main__":
    unittest.main()
