"""Site decisions 139 (Robin, 2026-10-26) and 141: a small article inside a small article, as a
setting, and a peek inside a small article drawn against the window — the source and the build.

Pins:

* **The setting** (`site/shell.js` `SETTINGS`): `nestminis`, with 139's in place and stacked among
  its values, under Article -> Small articles (`sub: 'mini'`), right after `minicontent`. Since
  decisions 147 (2026-10-29) it has four values, the default `second`, and the limit `nestlimit`
  (139's drop-down 1 to 5, drawn only while stacked) is gone: the row, the words and the presets'
  values are pinned in `test_ordpar_nestminis147.py`; here only that no limit field is drawn.
* **The words** (`site/strings/en.json`) of 139 that still stand: the label, in place, off.
* **The presets** (decisions 136): Concise and For learners name `nestminis`; Default names none
  (it is the defaults).
* **The script** (`site/mini.js`): it reads the setting itself, with the default and values of the
  table; `target` no longer refuses every link inside a mini (depth one is now the setting's
  `off`); a stacked box goes beside the `.mini` of the box it opens from (`chain[d - 1].m`), not
  into its word's line; the back line is a `button.ordpar-mback` named "Back to <word>"; every
  level loads through `load` (so through `ordparSearch.fetchArticle` where the page has it); on
  the deck a link in a mini is upgraded only where the card carries its target's template; the
  peek fix (141) is `peekFix`, run from a `mouseover` listener on the window.
* **The sheet** (`sitegen/page.py` `SITE_CSS`): the nested box, its shadow by day and night, the
  back line and its night colour, the fixed peek and its turned arrow by day and night.
* **The build** (`ordpar/out/`, or `ORDPAR_TEST_OUT`): `site/ordpar.js` carries the script's
  settings and `site/article.css` the rules; `settings/index.html` the words. Skipped without a build.

The browser side: `test_ordpar_browser_nestminis139.py`, `test_ordpar_browser_peek141.py`.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo
sys.path.insert(0, ROOT)
SITE = os.path.join(ROOT, "ordpar", "site")
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ROOT, "ordpar", "out")

from ordpar.sitegen import page  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SHELL_JS = _read(SITE, "shell.js")
SETTINGS_JS = _read(SITE, "settings.js")
MINI_JS = _read(SITE, "mini.js")
STRINGS = json.loads(_read(SITE, "strings", "en.json"))

#: The words as drafted (the session's brief, 2026-10-27) that decisions 147 left as they were; the
#: stacked choice's new words, the new choice's and the hint are `test_ordpar_nestminis147.py`'s
WORDS = {
    "settings.nestminis": "A link inside a small article",
    "settings.nestminis.inplace": "Opens its small article in the same box",
    "settings.nestminis.off": "Opens its whole article",
}


def rows():
    """`SETTINGS` in shell.js: the rows' text, in order, by key."""
    body = re.search(r"var SETTINGS = \[(.*?)\n  \];", SHELL_JS, re.S).group(1)
    return [(m.group(1), m.group(0)) for m in re.finditer(r"\{ key: '(\w+)'[^\n]*\}", body)]


def presets():
    return json.loads(re.search(r"var PRESETS = (\[.*?\n  \]);", SETTINGS_JS, re.S).group(1))


class Settings(unittest.TestCase):

    def test_a_the_row_after_minicontent(self):
        keys = [k for k, _ in rows()]
        i = keys.index("minicontent")
        self.assertEqual(keys[i + 1], "nestminis")
        row = dict(rows())["nestminis"]
        for v in ("'inplace'", "'stacked'", "'off'"):                # 139's choices kept (147: four)
            self.assertIn(v, row)
        self.assertIn("section: 'article', sub: 'mini' }", row)

    def test_b_no_limit_drawn(self):
        # decisions 147: the limit went, and with it its drawing only while stacked
        self.assertNotIn("nestlimit", [k for k, _ in rows()])
        m = re.search(r"function shown\(sp\) \{(.*?)\n  \}", SETTINGS_JS, re.S)
        self.assertNotIn("nestlimit", m.group(1))
        # exmore's mechanism stays: `sync` re-asks `shown` for every field on each change
        self.assertIn("if (group) { group.hidden = !shown(sp); }", SETTINGS_JS)

    def test_c_the_words(self):
        for k, v in WORDS.items():
            self.assertEqual(STRINGS.get(k), v, k)
        # the limit and its words went (decisions 147)
        self.assertEqual([k for k in STRINGS if k.startswith("settings.nestlimit")], [])

    def test_d_the_presets(self):
        got = {p["id"]: p["values"] for p in presets()}
        self.assertEqual(got["default"], {})
        for pid in ("concise", "learners"):
            self.assertIn("nestminis", got[pid], pid)                  # its value: 147's test
            self.assertNotIn("nestlimit", got[pid], pid)

    def test_e_the_export_carries_every_setting(self):
        # personal.js `SETTING_KEYS` ("shell.js KEYS") lacked 139's two new keys after the build
        # (found 2026-10-27); every row of the settings table must travel in an export
        keys = re.findall(r"\{ key: '(\w+)'", SHELL_JS)
        m = re.search(r"SETTING_KEYS = \[(.*?)\];", _read(SITE, "personal.js"), re.S)
        self.assertEqual(sorted(re.findall(r"'(\w+)'", m.group(1))), sorted(keys))


class Script(unittest.TestCase):

    def test_a_reads_the_settings_itself(self):
        # decisions 147: four values, the default `second`, no limit
        self.assertIn("setting('nestminis', ['second', 'inplace', 'stacked', 'off'], 'second')", MINI_JS)
        self.assertNotIn("setting('nestlimit'", MINI_JS)

    def test_b_target_no_longer_depth_one(self):
        self.assertNotIn("if (a.closest('.ordbok-xmini')) { return null; }", MINI_JS)
        t = re.search(r"function target\(a\) \{(.*?)\n  \}", MINI_JS, re.S).group(1)
        self.assertIn("if (nestMode() === 'off') { return null; }", t)     # 147: no limit
        self.assertIn("if (global.ordparDeck && !doc.getElementById('ordpar-t-' + m[1])) { return null; }", t)

    def test_c_stacked_box_beside_the_mini_of_its_box(self):
        self.assertIn("if (d) { chain[d - 1].m.appendChild(m); } else { x.appendChild(m); }", MINI_JS)
        self.assertIn("m.classList.add('ordpar-mnest')", MINI_JS)

    def test_d_back_line(self):
        self.assertIn("b.className = 'ordpar-mback';", MINI_JS)
        self.assertIn("b.setAttribute('aria-label', 'Back to ' + word);", MINI_JS)

    def test_e_every_level_through_load(self):
        self.assertEqual(MINI_JS.count("load(t.id).then("), 2)     # a box (first or nested), a step
        self.assertIn("S.fetchArticle(id)", MINI_JS)               # the search page's shared fetch

    def test_f_the_peek_fix(self):
        self.assertIn("function peekFix(x) {", MINI_JS)
        self.assertIn("p.classList.add('ordpar-pfix');", MINI_JS)
        self.assertIn("global.addEventListener('mouseover', function (e) {", MINI_JS)

    def test_g_the_deck_seams_kept(self):
        # deck/assets.py `mini_js` refuses a mini.js without these
        self.assertEqual(MINI_JS.count("var HREF = /^\\/bm-en\\/(\\d+)\\/(?:#(def\\d+))?$/;"), 1)
        self.assertIn("global.ordparSearch", MINI_JS)
        self.assertIn("global.ordparPlace(m)", MINI_JS)


RULES = (
    ".ordbok-xmini.ordpar-mnest{display:block;position:fixed;top:0;left:0;z-index:1}",
    # site decisions 157 (Robin, 2026-11-01): the nested box's own deeper shadow gone, it takes the
    # first box's (`test_ordpar_minishadow157`)
    ".ordpar-mnest>.mini{overflow-y:auto;overscroll-behavior:contain}",
    ".ordpar-mback{display:block;",
    ".nightMode .ordpar-mback-arrow{color:#b9b6b6}",
    ".ordbok-xmini .ordbok-xpeek.ordpar-pfix{position:fixed;bottom:auto;right:auto}",
    ".ordbok-xmini .ordbok-xpeek.ordpar-pbelow::after{top:auto;bottom:100%;",
    ".nightMode .ordbok-xmini .ordbok-xpeek.ordpar-pbelow::after{",
)


class Sheet(unittest.TestCase):

    def test_the_rules(self):
        for r in RULES:
            self.assertIn(r, page.SITE_CSS, r)


def _built(*parts):
    path = os.path.join(OUT, *parts)
    return _read(path) if os.path.exists(path) else None


BUNDLE = _built("site", "ordpar.js")


@unittest.skipIf(BUNDLE is None, "no build in %s" % OUT)
class Built(unittest.TestCase):

    def test_a_the_bundle_and_the_sheet(self):
        self.assertIn("setting('nestminis', ['second', 'inplace', 'stacked', 'off'], 'second')", BUNDLE)
        self.assertIn("function peekFix(x)", BUNDLE)
        css = _built("site", "article.css")
        self.assertIsNotNone(css)
        flat = re.sub(r"\s+", "", css)
        for r in RULES:
            self.assertIn(re.sub(r"\s+", "", r), flat, r)

    def test_b_the_settings_page(self):
        pg = _built("settings", "index.html")
        self.assertIsNotNone(pg)
        for k, v in WORDS.items():
            self.assertIn(json.dumps(v, ensure_ascii=False)[1:-1], pg, k)


if __name__ == "__main__":
    unittest.main()
