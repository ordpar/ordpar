"""Site decisions 186 (2026-11-14/15): what the eye at the headword hides, the source side. The
setting `exeyewhat` = examples (the default) | all, beside the eye's own setting (`exeye`, decisions
131); under `all` the eye blanks every English line of its article but the etymology, each behind
its own "Show English" cue. In a browser: `test_ordpar_browser_eyeall186.py`.

* **The setting**: right after `exeye` in the table, under Article's Language, `examples` first and
  the default; its words in `strings/en.json` exactly; shown on the Settings page only while the eye
  is on (`settings.js` `shown`); the export carries it; no preset names it, so each preset gives the
  default ("For learners": the eye on, hiding the examples).
* **The class**: the head script's `ordpar-exeye-all`, `shell.js` toggling it as a class setting.
* **The page script**: the eye's words under `all` from `strings.py`; the English lines' selector and
  the parts it never reaches (a peek, a small article, a row's button); the cue a `.ordbok-cue`
  button marked `data-ordpar-eyecue`; a press on a shown line taken before the page script closes
  its pair.
* **The sheet**: the hidden line, the cue in the line's place (block, fit-content; inline-block on a
  set phrase's line), the make-up block, no hover peek in a blanked article (a small article's own
  kept), a list row's glosses hidden while its article is blanked. The cue is styled through its
  attribute, never a class of its own: the deck shares this sheet and the page script, and its asset
  build refuses a styled button class outside its list.

`ORDPAR_TEST_ROOT` names another copy of the repository (`git archive HEAD ordpar` unpacked) to show
it failing on the version before the change. Stdlib unittest.
"""
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("ORDPAR_TEST_ROOT") or REPO
sys.path.insert(0, ROOT)

from ordpar.sitegen import head, page  # noqa: E402
from ordpar.sitegen import strings as strings_mod  # noqa: E402

SITE = os.path.join(ROOT, "ordpar", "site")

WORDS = {
    "settings.exeyewhat": "What the eye at the headword hides",
    "settings.exeyewhat.examples": "The examples' English",
    "settings.exeyewhat.all": "All the English of its article but the etymology, each line behind its own \"Show English\"",
}


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _presets():
    js = _read(SITE, "settings.js")
    return json.loads(re.search(r"var PRESETS = (\[.*?\n  \]);", js, re.S).group(1))


class TheSetting(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_right_after_the_eye_examples_first(self):
        self.assertIn("{ key: 'exeyewhat', values: ['examples', 'all'], def: 'examples', section: 'article', "
                      "sub: 'language' }", self.js)
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        self.assertEqual(order[order.index("exeye") + 1], "exeyewhat")

    def test_the_words(self):
        s = json.loads(_read(SITE, "strings", "en.json"))
        for k, v in WORDS.items():
            self.assertEqual(s.get(k), v, k)
        hint = s.get("settings.exeyewhat.hint") or ""
        self.assertIn("etymology", hint)
        self.assertIn("Show English", hint)

    def test_shown_only_while_the_eye_is_on(self):
        self.assertIn("if (sp.key === 'exeyewhat') { return sh.getSetting('exeye') === 'on'; }",
                      _read(SITE, "settings.js"))

    def test_the_export_carries_it(self):
        exp = re.search(r"var SETTING_KEYS = \[([^\]]*)\]", _read(SITE, "personal.js")).group(1)
        self.assertIn("'exeyewhat'", exp)

    def test_no_preset_names_it(self):
        ps = _presets()
        self.assertTrue(ps)
        for p in ps:
            self.assertNotIn("exeyewhat", p["values"], p["id"])
        learners = [p for p in ps if p["id"] == "learners"][0]
        self.assertEqual(learners["values"].get("exeye"), "on")


class TheClass(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_head_script_and_shell(self):
        self.assertIn("s.getItem('exeyewhat')==='all'&&c.add('ordpar-exeye-all');", head.THEME_JS)
        self.assertIn("cl.toggle('ordpar-exeye-all', getSetting('exeyewhat') === 'all');", self.js)
        keys = self.js.split("var CLASS_KEYS = [")[1].split("];")[0]
        self.assertIn("'exeyewhat'", keys)

    def test_the_address_reads_it(self):
        # the settings in the address (decisions 146) take every row of the table
        self.assertIn("exeyewhat", dict(head.settings_table()))


class ThePageScript(unittest.TestCase):
    js = page.PAGE_JS

    def test_the_words(self):
        self.assertEqual(strings_mod.EN["exeye_all_hide"], "Hide the English")
        self.assertEqual(strings_mod.EN["exeye_all_show"], "Show the English")
        self.assertIn(json.dumps({"hide": "Hide the English", "show": "Show the English"}), self.js)
        # the examples' words unchanged
        self.assertIn("EYE=" + json.dumps("Hide the examples' English"), self.js)

    def test_the_lines_and_where_never(self):
        self.assertIn("'.ordbok-head>.ordpar-gloss,.ordpar-pair>span.ordbok-def[lang=\"en\"],"
                      ".ordbok-ex-list>li>.ordpar-en,.ordbok-idiom-eng'", self.js)
        self.assertIn("'.ordbok-xpeek,.ordbok-xmini,template,.ordpar-row-button'", self.js)
        self.assertIn("C.contains('ordpar-exeye-all')", self.js)
        self.assertIn("C.contains('ordpar-defs-en')", self.js)

    def test_the_cue(self):
        self.assertIn("b.className='ordbok-cue';b.setAttribute('data-ordpar-eyecue','')", self.js)

    def test_a_shown_line_before_the_pair_closes(self):
        js = self.js
        i = js.index("t.closest('.ordpar-eyeshown')")
        j = js.index("var o=t.closest('.ordpar-open>span[lang=en]")
        self.assertLess(i, j)


class TheSheet(unittest.TestCase):
    css = page.article_css()

    def test_rules(self):
        for rule in (".ordpar-eyehid{display:none!important}",
                     ".ordbok-cue[data-ordpar-eyecue]{display:block;width:fit-content;font-family:inherit;"
                     "background:none;cursor:pointer}",
                     ".ordbok-idiom .ordbok-cue[data-ordpar-eyecue]{display:inline-block}",
                     ".ordpar-eyefill{display:block}",
                     ".ordpar-blanked .ordbok-xpeek:not(.ordbok-xmini *){display:none!important}",
                     ".ordpar-row-blanked .ordpar-row-snippet{display:none}"):
            self.assertIn(rule, self.css)

    def test_no_class_of_its_own_on_the_cue(self):
        self.assertNotIn(".ordpar-eyecue", self.css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
