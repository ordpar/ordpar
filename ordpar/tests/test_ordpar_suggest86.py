#!/usr/bin/env python3
"""Site decisions 86 (Robin, 2026-10-22: the style lab's frame D2-136L) and 22 reversed the same day.

Pins, in `lookup.js` `suggestSections` (run under bun or node): the rows keep their ranked order
and the run of one-word *Norwegian only* headwords is the section drawn under the "Norwegian
only" label; the exact match is first and never in it, whatever its status (decisions 59); set
phrases stay below the headwords, outside it — except after a trailing space, where they are
grouped as headwords are (exact match, translated, then the untranslated as the section); an
"N articles" row whose articles are all untranslated falls in the section. In `shell.js`, what
can be pinned outside a browser: the section is a `role="group"` named by its label, the label
and the rules are not options and the arrow keys walk the options only; a one-article row in the
section shows its Norwegian definition (the list view's snippet), outside it the tag; translated
words in the accent, the others in the text colour. In `shell.css`: the label's text is the
gloss's size through ONE value (`--ordpar-gloss-size`: "if we later change the gloss size, the
label follows"). And the setting `suggestrows` (standard | roomy, a 44 px row): the table, the
head script, the class, the export, the strings. The 20 rows and the keyboard cap:
`test_ordpar_suggest82.py` `SuggestHeight22`. The real layout is checked in a browser
(`docs/sessions/2026-09-19-ordpar-site-review/evidence/suggest-86-build-2026-10-22/`).

Stdlib unittest; the JavaScript runs under bun (or node), skipped when neither is on PATH.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)

from ordpar.sitegen import head  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _run(body):
    runner = shutil.which("bun") or shutil.which("node")
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run86.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(body)
        res = subprocess.run([runner, script], capture_output=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr.decode("utf-8", "replace"))
        return json.loads(res.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _row(word, translated, n=1):
    return {"word": word, "translated": translated, "ids": list(range(n))}


class Sections86(unittest.TestCase):
    """`suggestSections(items, typed)` -> {rows, start, end}, the section rows[start..end)."""

    def sections(self, items, typed):
        got = _run("""const L = require(%s).ordparLookup;
const items = %s, before = JSON.stringify(items);
const r = L.suggestSections(items, %s);
process.stdout.write(JSON.stringify({ rows: r.rows.map(x => x.word), start: r.start, end: r.end,
  same: JSON.stringify(items) === before }));""" % (
            json.dumps(os.path.join(SITE, "lookup.js")), json.dumps(items), json.dumps(typed)))
        self.assertTrue(got.pop("same"), "the rows given are not changed")
        return got

    # *dann* as the lab drew it: the exact match Norwegian only, then the translated headwords,
    # the Norwegian-only ones, then the set phrases
    DANN = [_row("dann", False), _row("danne", True), _row("dannelse", True), _row("dannet", True),
            _row("danner", False), _row("dannings", False), _row("dann og vann", False),
            _row("danne seg", True)]

    def test_exact_match_first_and_outside(self):
        got = self.sections(self.DANN, "dann")
        self.assertEqual(got["rows"], [r["word"] for r in self.DANN])   # no row moves
        self.assertEqual(got["rows"][0], "dann")
        self.assertEqual((got["start"], got["end"]), (4, 6))           # danner, dannings

    def test_set_phrases_stay_below(self):
        # a Norwegian-only set phrase is not in the section, and stays after the headwords
        got = self.sections(self.DANN, "dann")
        self.assertEqual(got["rows"][6:], ["dann og vann", "danne seg"])
        self.assertLessEqual(got["end"], 6)

    def test_trailing_space_groups_the_phrases(self):
        items = [_row("ha", True), _row("ha bo", False), _row("ha det", True), _row("ha imot", False),
                 _row("ha med", True), _row("hage", True), _row("hake", False)]
        got = self.sections(items, "ha ")
        self.assertEqual(got["rows"], ["ha", "ha det", "ha med", "hage", "ha bo", "ha imot", "hake"])
        self.assertEqual((got["start"], got["end"]), (4, 7))

    def test_trailing_space_exact_matches_first_whatever_their_status(self):
        # *ta*: ta (translated) and Ta (Norwegian only) both the exact match
        items = [_row("ta", True), _row("Ta", False), _row("ta fatt", False), _row("ta av", True)]
        got = self.sections(items, "ta ")
        self.assertEqual(got["rows"], ["ta", "Ta", "ta av", "ta fatt"])
        self.assertEqual((got["start"], got["end"]), (3, 4))

    def test_exact_match_folded(self):
        # *ø*: ø and Ø; *Ba* typed: ba, Ba, BA are all the exact match, never in the section
        got = self.sections([_row("ø", False), _row("Ø", False), _row("øye", True), _row("øl", True)], "ø")
        self.assertEqual((got["start"], got["end"]), (-1, -1))
        got = self.sections([_row("Ba", False), _row("BA", False), _row("bad", True), _row("bable", False)], "ba")
        self.assertEqual((got["start"], got["end"]), (3, 4))

    def test_all_untranslated_articles_row_in_the_section(self):
        items = [_row("stil", True), _row("stille", True, 3), _row("still", False, 2), _row("stilk", False)]
        got = self.sections(items, "stil")
        self.assertEqual((got["start"], got["end"]), (2, 4))
        self.assertEqual(got["rows"][2], "still")

    def test_no_section_and_bad_input(self):
        got = self.sections([_row("hus", True), _row("huske", True)], "hus")
        self.assertEqual((got["start"], got["end"]), (-1, -1))
        got = self.sections([], "")
        self.assertEqual(got, {"rows": [], "start": -1, "end": -1})


class Shell86(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = _read(SITE, "shell.js")
        cls.open = cls.js[cls.js.index("    function open(items) {"):cls.js.index("    function openRecent(")]

    def test_the_group_is_not_an_option(self):
        o = self.open
        self.assertIn("lookup.suggestSections(items, input.value)", o)
        self.assertIn("group.setAttribute('role', 'group');", o)
        self.assertIn("group.setAttribute('aria-labelledby', 'ordpar-option-nbhead');", o)
        self.assertIn("head.setAttribute('aria-hidden', 'true');", o)
        self.assertIn("host.setAttribute('role', 'none');", o)
        self.assertIn("after.setAttribute('role', 'none');", o)
        self.assertIn("above.setAttribute('aria-hidden', 'true');", o)
        self.assertIn("if (i > 0) {", o)                     # no rule above where it opens the list
        self.assertIn("t('tag.norwegianOnly')", o)           # the label's words: the tag's
        # the label is no `ordpar-option`, so the arrow keys and aria-activedescendant skip it
        self.assertIn("function optionRows() { return listbox.querySelectorAll('.ordpar-option'); }", self.js)
        choose = self.js[self.js.index("    function choose(i) {"):self.js.index("    var ranked = [];")]
        self.assertIn("var rows = optionRows();", choose)
        self.assertNotIn("listbox.children", choose)
        self.assertIn("scrollIntoView({ block: 'nearest' })", choose)

    def test_colours_and_the_definition(self):
        self.assertIn("var li = el('li', 'ordpar-option ' + (item.translated ? 'is-translated' : 'is-nb'));",
                      self.open)
        self.assertIn("optionSide(item, glosses, li, i >= sec.start && i < sec.end)", self.open)
        side = self.js[self.js.index("    function optionSide("):self.js.index("    function fillGlosses(")]
        self.assertIn("} else if (nbsec && ids.length === 1) {", side)
        self.assertIn("'ordpar-option-gloss ordpar-option-nb is-pending', '\\u00a0'", side)
        self.assertIn("def.lang = 'nb';", side)
        # outside the section an untranslated row keeps the tag
        self.assertIn("side.appendChild(el('span', 'ordpar-tag', t('tag.norwegianOnly')));", side)
        # the definition is the list view's snippet, whole; a gloss its first unit
        self.assertIn("var text = g.nb ? (snips[g.id] || '') : glossText(snips, g.id);", self.js)
        # the Recent rows: no section; since 88's second amendment (Robin, 2026-10-22: "the
        # history page still colours the headword of untranslated articles") the colour class
        # as a suggestion row's, set where a translated article is behind the row
        recent = self.js[self.js.index("    function openRecent("):self.js.index("    function emptyBox(")]
        self.assertNotIn("suggestSections", recent)
        self.assertIn("(e.n === 1 && e.translated ? ' is-translated' : '')", recent)
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-option.is-translated .ordpar-option-word { color: var(--ordpar-accent); }", css)
        self.assertNotRegex(css, r"\.is-nb[^{]*\{[^}]*color")      # the text colour, inherited

    def test_escapes_are_escapes(self):
        # the Write/Edit tools turn a typed escape into the character; the script keeps escapes
        self.assertNotIn(chr(0xa0), self.js)
        code = [ln for ln in self.js.splitlines() if not ln.strip().startswith(('*', '/*', '//'))]
        self.assertEqual([ln for ln in code if chr(0xb7) in ln.split('//')[0]], [])


class Label86(unittest.TestCase):
    """The label's text at the gloss's size, tied to it (Robin: "if we later change the gloss
    size, the label follows")."""

    def test_one_value(self):
        css = _read(SITE, "shell.css")
        root = css[css.index(":root {"):]
        root = root[:root.index("}")]
        self.assertIn("--ordpar-gloss-size: 0.85rem;", root)
        self.assertEqual(css.count("--ordpar-gloss-size:"), 1)
        rule = lambda sel: css[css.index(sel + " {"):].split("}")[0]
        self.assertIn("font-size: var(--ordpar-gloss-size);",
                      rule(".ordpar-option-gloss, .ordpar-option-count, .ordpar-option-glosses"))
        self.assertIn("font-size: var(--ordpar-gloss-size);", rule(".ordpar-option-label"))
        # the box inside takes the label's size, not the tag's own 0.72rem
        self.assertIn("font-size: inherit;", rule(".ordpar-option-label .ordpar-tag"))
        # the rules above and after the section
        self.assertIn("border-top: 1px solid var(--ordpar-border);", rule(".ordpar-option-sep"))


class Setting86(unittest.TestCase):
    """`suggestrows` = standard | roomy (default standard): Settings -> Search."""

    def test_the_table(self):
        js = _read(SITE, "shell.js")
        self.assertIn("{ key: 'suggestrows', values: ['standard', 'roomy'], def: 'standard', section: 'search' }", js)
        class_keys = js.split("var CLASS_KEYS = ")[1].split(";")[0]
        self.assertIn("'suggestrows'", class_keys)          # CLASS_KEYS (no longer its last: 87, 90)
        self.assertIn("cl.toggle('ordpar-suggestrows-roomy', getSetting('suggestrows') === 'roomy');", js)
        keys = _read(SITE, "personal.js").split("SETTING_KEYS = ")[1].split(";")[0]
        self.assertIn("'suggestrows'", keys)
        strings = json.loads(_read(SITE, "strings", "en.json"))
        for k in ("settings.suggestrows", "settings.suggestrows.standard", "settings.suggestrows.roomy"):
            self.assertIn(k, strings)

    def test_the_css(self):
        css = _read(SITE, "shell.css")
        self.assertIn("html.ordpar-suggestrows-roomy .ordpar-option { padding-top: 0.625rem; "
                      "padding-bottom: 0.625rem; }", css)
        # standard: today's row, untouched
        opt = css[css.index(".ordpar-option {"):].split("}")[0]
        self.assertIn("padding: 0.35rem 0.6rem;", opt)

    def test_the_head_script(self):
        self.assertIn("s.getItem('suggestrows')==='roomy'&&c.add('ordpar-suggestrows-roomy')", head.THEME_JS)
        got = _run("""const out = [];
for (const v of [null, 'standard', 'roomy', 'tight']) {
  const cls = new Set();
  globalThis.document = { documentElement: { classList: { add: c => cls.add(c) }, setAttribute() {} } };
  globalThis.localStorage = { getItem: k => k === 'suggestrows' ? v : null };
  globalThis.window = {};
  eval(%s);
  out.push(cls.has('ordpar-suggestrows-roomy'));
}
process.stdout.write(JSON.stringify(out));""" % json.dumps(head.THEME_JS))
        self.assertEqual(got, [False, False, True, False])


if __name__ == "__main__":
    unittest.main()
