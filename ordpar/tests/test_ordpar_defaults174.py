"""Site decisions 174 (Robin, 2026-11-07): Norwegian emphasized and formula lines in both languages
as the defaults; a fourth preset, "English emphasized", with the old ones.

The ruling: the "Norwegian emphasized" option the default, and Short formula lines such as "used
as an adverb:" defaulting to "In Norwegian and English"; with it, a new preset, "English
emphasized", holding the old defaults; the defaults, the preset, Concise kept, the words and Help
as drafted.

Pins:

* **The defaults** (`site/shell.js` `SETTINGS`): `emph` `no`, its values `no`, `en`; `formulas`
  `both`, its values `both`, `en`, `no` — the default first (decisions 107: the page draws the
  choices in `values` order), each choice's note keyed by its value, so it travels with it.
* **The presets** (`site/settings.js` `PRESETS`): Default, English emphasized, Concise, For learners,
  in that order; English emphasized names exactly `emph` en and `formulas` en; Concise names both
  old values, so it is what it was; For learners and Default unchanged.
* **The words** (`site/strings/en.json`): Default's new note, the new preset's name and note, byte
  for byte; For learners' and Concise's notes unchanged.
* **Help** (`ordpar/help.md`): "four buttons … *Default*, *English emphasized*, *Concise* and *For
  learners*", and the new paragraph straight after "Presets", before "Shorter articles: Concise".
* **The page, run under bun or node** (the stand-in of `test_ordpar_settingsaddr146.py`, with
  `settings.js` loaded): the head script draws `ordpar-emph-no` and `ordpar-formulas-both` for a
  reader with nothing stored (or a value the setting does not take), none of them for one on the old
  defaults, and `shell.js` draws the same; `ordparSettings.matching()` is Default for nothing stored
  or the new defaults stored, English emphasized for a reader with the old defaults stored; the
  pop-up address (146) names `emph=en&formulas=en` for the old defaults and nothing for the new.

Stdlib unittest; the JS parts skipped without bun or node.
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import test_ordpar_settingsaddr146 as T146  # noqa: E402  (its stand-in page and runner)


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SHELL_JS = _read(SITE, "shell.js")
SETTINGS_JS = _read(SITE, "settings.js")
STRINGS = json.loads(_read(SITE, "strings", "en.json"))
HELP_MD = _read(ORDPAR, "help.md")

#: Robin's words, 2026-11-07 (site decisions 174), approved "Yes, as drafted"
DEFAULT_NOTE = ("Ordpar as it starts: each definition in Norwegian and English, the Norwegian in full "
                "colour and the English faded; short formula lines in both languages; every example "
                "with its English; small articles in full.")
ENGLISH_NAME = "English emphasized"
ENGLISH_NOTE = ("for when you read mostly for the English: in each definition the English in full "
                "colour and the Norwegian faded; short formula lines in English only.")
CONCISE_NOTE = ("for when you only need the meaning: each definition in English only; the first two "
                "examples under each sense and set phrase, with a line to show the rest; small "
                "articles a little shorter. An article not yet translated still shows its Norwegian.")
LEARNERS_NOTE = ("for reading the Norwegian first: an eye beside the headword hides the examples' "
                 "English; in each definition the Norwegian in full colour and the English faded; "
                 "short formula lines in both languages; each word's CEFR level in a small box "
                 "after the headword, with the set phrases ordered by level, A1 first.")
# site decisions 187: the level box's clause; 188: the set phrases' order, a draft for Robin
HELP_PRESETS = ("four buttons set all the article settings at once: *Default*, *English emphasized*, "
                "*Concise* and *For learners*.")
HELP_ENGLISH = ("**The English first: English emphasized.** For when you read mostly for the English. "
                "In each definition the English is in the full text colour and the Norwegian is faded, "
                "and short formula lines, such as \"used as an adverb:\", show in English only. The "
                "settings behind it: *Emphasis, when both languages show*, and *Short formula lines*.")

RULED = [
    ("default", {}),
    ("english", {"emph": "en", "formulas": "en"}),
    ("concise", {"defs": "en", "exlimit": "2", "exmore": "on", "minicontent": "slim",
                 "minispacing": "article", "nestminis": "second", "emph": "en", "formulas": "en"}),
    ("learners", {"exeye": "on", "emph": "no", "examples": "both", "subsenses": "defs",
                  "formulas": "both", "nestminis": "second",
                  "levels": "on",   # site decisions 187
                  "phraseorder": "level"}),   # site decisions 188
]


def _row(key):
    body = SHELL_JS[SHELL_JS.index("var SETTINGS = ["):SHELL_JS.index("var SPEC = {}")]
    return re.search(r"\{ key: '%s', values: \[([^\]]*)\], def: '(\w+)'" % key, body)


def _presets():
    return json.loads(re.search(r"var PRESETS = (\[.*?\n  \]);", SETTINGS_JS, re.S).group(1))


class TheDefaults(unittest.TestCase):

    def test_a_emph_norwegian_first(self):
        m = _row("emph")
        self.assertEqual((m.group(1), m.group(2)), ("'no', 'en'", "no"))

    def test_b_formulas_both_first(self):
        m = _row("formulas")
        self.assertEqual((m.group(1), m.group(2)), ("'both', 'en', 'no'", "both"))

    def test_c_the_notes_travel_with_their_choice(self):
        # the page reads a choice's note by its value (`settings.<key>.<value>.note`), so the
        # reordering moves them with it; the words themselves unchanged
        self.assertEqual(STRINGS["settings.emph.en.note"], "In the example sentences, the Norwegian stays emphasized.")
        self.assertNotIn("settings.emph.no.note", STRINGS)
        self.assertIn("settings.formulas.both.note", STRINGS)
        self.assertIn("settings.formulas.no.note", STRINGS)
        self.assertIn("var key = 'settings.' + sp.key + '.' + v;", SETTINGS_JS)
        self.assertIn("return sp.values.map(function (v) {", SETTINGS_JS)


class ThePresets(unittest.TestCase):

    def test_a_four_in_order(self):
        self.assertEqual([(p["id"], p["values"]) for p in _presets()], RULED)

    def test_b_the_words(self):
        self.assertEqual(STRINGS.get("settings.presets.default.note"), DEFAULT_NOTE)
        self.assertEqual(STRINGS.get("settings.presets.english"), ENGLISH_NAME)
        self.assertEqual(STRINGS.get("settings.presets.english.note"), ENGLISH_NOTE)
        self.assertEqual(STRINGS.get("settings.presets.concise.note"), CONCISE_NOTE)
        self.assertEqual(STRINGS.get("settings.presets.learners.note"), LEARNERS_NOTE)

    def test_c_help(self):
        self.assertIn("At the top of Settings, " + HELP_PRESETS, HELP_MD)
        self.assertNotIn("three buttons", HELP_MD)
        blocks = [b.strip() for b in HELP_MD.split("\n\n")]
        i = [n for n, b in enumerate(blocks) if b.startswith("**Presets.**")][0]
        self.assertEqual(blocks[i + 1], HELP_ENGLISH)
        self.assertTrue(blocks[i + 2].startswith("**Shorter articles: Concise.**"), blocks[i + 2][:60])


class ThePage(unittest.TestCase):
    """The head script, the shell and the settings page's `matching`, under bun or node."""

    @classmethod
    def setUpClass(cls):
        cls.r = T146._run(T146._prelude() + r"""
const SETTINGS_SRC = fs.readFileSync(%s, 'utf8');
const CASES = {
  none: {},
  oldDefaults: { emph: 'en', formulas: 'en' },
  newDefaults: { emph: 'no', formulas: 'both' },
  formulasNo: { formulas: 'no' },
  bogus: { emph: 'x', formulas: 'y' },
};
const want = ['ordpar-emph-no', 'ordpar-formulas-both', 'ordpar-formulas-no'];
for (const name in CASES) {
  const h = head('', '/bm-en/24627/', CASES[name]);
  const p = page('', '/bm-en/24627/', CASES[name]);
  const sh = shell();
  sh.applyAll();
  delete globalThis.ordparSettings;
  (0, eval)(SETTINGS_SRC);
  out[name] = { head: h.classes.filter(c => want.indexOf(c) >= 0),
                shell: [...p.cls].filter(c => want.indexOf(c) >= 0).sort(),
                matching: globalThis.ordparSettings.matching(),
                emph: sh.getSetting('emph'), formulas: sh.getSetting('formulas'),
                address: sh.popupAddress() };
}
console.log(JSON.stringify(out));""" % json.dumps(os.path.join(SITE, "settings.js")))

    def test_a_nothing_stored_is_the_new_look(self):
        r = self.r["none"]
        self.assertEqual(r["head"], ["ordpar-emph-no", "ordpar-formulas-both"])
        self.assertEqual((r["emph"], r["formulas"]), ("no", "both"))
        self.assertEqual(self.r["bogus"]["head"], ["ordpar-emph-no", "ordpar-formulas-both"])

    def test_b_the_old_defaults_no_class(self):
        self.assertEqual(self.r["oldDefaults"]["head"], [])
        self.assertEqual(self.r["formulasNo"]["head"], ["ordpar-emph-no", "ordpar-formulas-no"])

    def test_c_the_shell_draws_the_same(self):
        for name, r in self.r.items():
            self.assertEqual(r["shell"], r["head"], name)

    def test_d_which_preset_matches(self):
        self.assertEqual(self.r["none"]["matching"], "default")
        self.assertEqual(self.r["newDefaults"]["matching"], "default")
        self.assertEqual(self.r["oldDefaults"]["matching"], "english")
        self.assertIsNone(self.r["formulasNo"]["matching"])

    def test_e_the_popup_address(self):
        self.assertEqual(self.r["oldDefaults"]["address"], "https://ordpar.no/bm-en/#emph=en&formulas=en&q={{str}}")
        self.assertEqual(self.r["newDefaults"]["address"], T146.PLAIN)
        self.assertEqual(self.r["none"]["address"], T146.PLAIN)


if __name__ == "__main__":
    unittest.main()
