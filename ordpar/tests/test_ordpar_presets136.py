"""Site decisions 136 (Robin, 2026-10-26): the presets on the settings page, the line under "Reset
settings", and the Help page's Settings section — the source and the built pages.

Pins:

* **The presets' table** — `site/settings.js` `PRESETS` (strict JSON between its brackets): exactly
  Default, English emphasized, Concise and For learners, in that order (English emphasized since site
  decisions 174, 2026-11-07), with exactly the values Robin ruled (English emphasized: `emph` en,
  `formulas` en, the defaults before 174; Concise: `defs` en, `exlimit` 2, `exmore` on, `minicontent`
  slim, `minispacing` article, and since 174 `emph` en and `formulas` en, so the change of default
  leaves it as it was; For learners: `exeye` on, `emph` no, `examples` both, `subsenses` defs,
  `formulas` both; Default: none named). Every value
  named is one the setting takes, every key named is an Article setting (`section: 'article'` in
  `site/shell.js` `SETTINGS`), and the full set a preset applies covers every Article setting and no
  other — Default's being every default.
* **The words** — the section's heading, its line, the four names, the spoken confirmation and the
  Reset line, exactly as decided, in `site/strings/en.json`.
* **`resetSettings`** drops every key of `KEYS` (so the Reset line's "every setting on this page …
  your theme and colour too" is true).
* **The built pages** (`ordpar/out/`, or `ORDPAR_TEST_OUT`): `/help/` has `h2#settings` before
  `h2#pronunciation`, its five paragraphs rendered from `help.md` itself (not a copy here) and
  matching `sitegen/about.py` `help_page`; `/settings/` carries the Reset line and the presets'
  strings, and its `settings.js` the table. Skipped without a build.

The browser side: `test_ordpar_browser_presets136.py`.
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

from ordpar.sitegen import about  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SETTINGS_JS = _read(SITE, "settings.js")
SHELL_JS = _read(SITE, "shell.js")
STRINGS = json.loads(_read(SITE, "strings", "en.json"))

#: Robin's rulings, 2026-10-26 (site decisions 136); decisions 139's `nestminis` named in Concise and
#: For learners, since decisions 147 (2026-10-29) at its new default, `second` (Robin: "agree on recommendation");
#: named even at the default, so a later change of the default leaves them
RULED = [
    ("default", {}),
    # site decisions 174 (Robin, 2026-11-07): the old defaults as a preset, second; Concise names them
    # too, so the new defaults (`emph` no, `formulas` both) leave it as it was
    ("english", {"emph": "en", "formulas": "en"}),
    ("concise", {"defs": "en", "exlimit": "2", "exmore": "on", "minicontent": "slim",
                 "minispacing": "article", "nestminis": "second",   # 147: the new default; nestlimit went
                 "emph": "en", "formulas": "en"}),                  # 174
    ("learners", {"exeye": "on", "emph": "no", "examples": "both", "subsenses": "defs",
                  "formulas": "both", "nestminis": "second"}),   # 147
]
WORDS = {
    "settings.presets.title": "Presets",
    "settings.presets.intro": "Each one sets all the article settings at once. Change any setting "
                              "afterwards and your change stays. Your style, search and offline "
                              "settings are not changed.",
    "settings.presets.default": "Default",
    "settings.presets.english": "English emphasized",                # 174
    "settings.presets.concise": "Concise",
    "settings.presets.learners": "For learners",
    "settings.presets.done": "Article settings set to {name}.",
    "settings.resetNote": "Puts every setting on this page back as Ordpar starts, your theme and "
                          "colour too. To reset only the article settings, use Default at the top.",
}


def presets_table(src=SETTINGS_JS):
    m = re.search(r"var PRESETS = (\[.*?\n  \]);", src, re.S)
    if not m:
        raise AssertionError("no `var PRESETS = [...]` in settings.js")
    return json.loads(m.group(1))


def settings_table():
    """`SETTINGS` in shell.js: [(key, values or None, def, section)] in order."""
    body = re.search(r"var SETTINGS = \[(.*?)\n  \];", SHELL_JS, re.S).group(1)
    rows = []
    for m in re.finditer(r"\{ key: '(\w+)', values: (\[[^\]]*\]|\w+), def: ('?\w*'?|null), "
                         r"section: '(\w+)'([^}]*)\}", body):
        vals = m.group(2)
        vals = re.findall(r"'([^']*)'", vals) if vals.startswith("[") else None
        # site decisions 152: Norwegian only's settings (`layer: true`) sit in Article but are a
        # layer, never a preset's (settings.js `articleSettings`): read as a section of their own
        sec = "layer" if "layer: true" in m.group(5) else m.group(4)
        rows.append((m.group(1), vals, m.group(3).strip("'"), sec))
    return rows


def full(values):
    return {k: values.get(k, d) for k, _v, d, sec in settings_table() if sec == "article"}


class Presets(unittest.TestCase):

    def test_a_the_table_is_the_ruling(self):
        got = [(p["id"], p["values"]) for p in presets_table()]
        self.assertEqual(got, RULED)

    def test_b_named_keys_are_article_settings_with_valid_values(self):
        table = {k: (v, d, sec) for k, v, d, sec in settings_table()}
        self.assertGreaterEqual(len(table), 25)          # the parse found the whole table
        for p in presets_table():
            for k, v in p["values"].items():
                self.assertIn(k, table, (p["id"], k))
                self.assertEqual(table[k][2], "article", (p["id"], k))
                self.assertIn(v, table[k][0], (p["id"], k, v))

    def test_c_each_covers_every_article_setting_and_no_other(self):
        rows = settings_table()
        article = [k for k, _v, _d, sec in rows if sec == "article"]
        self.assertEqual(len(article), 21)               # today's Article section (139: +2; 147: -1; 159: +1)
        for p in presets_table():
            self.assertEqual(sorted(full(p["values"])), sorted(article), p["id"])
        others = [k for k, _v, _d, sec in rows if sec != "article"]
        for k in ("theme", "colour", "lang", "layout", "listview", "suggestrows", "minifetch", "stats"):
            self.assertIn(k, others)

    def test_d_default_is_the_defaults(self):
        rows = settings_table()
        self.assertEqual(full({}), {k: d for k, _v, d, sec in rows if sec == "article"})
        # the four differ from each other, so at most one shows pressed (174: four)
        sets = [json.dumps(full(p["values"]), sort_keys=True) for p in presets_table()]
        self.assertEqual(len(set(sets)), 4)

    def test_e_the_words(self):
        for k, v in WORDS.items():
            self.assertEqual(STRINGS.get(k), v, k)
        for p in presets_table():
            self.assertIn("settings.presets." + p["id"], STRINGS)

    def test_f_reset_drops_every_key(self):
        m = re.search(r"function resetSettings\(\) \{(.*?)\n  \}", SHELL_JS, re.S)
        self.assertIn("KEYS.forEach(drop);", m.group(1))
        self.assertIn("var KEYS = SETTINGS.map(function (sp) { return sp.key; });", SHELL_JS)

    def test_g_the_page_script_draws_and_follows_them(self):
        s = SETTINGS_JS
        self.assertIn("wrap.appendChild(presets());", s)
        self.assertLess(s.index("wrap.appendChild(presets());"), s.index("SECTIONS.forEach(function (id) {\n      var sec"))
        self.assertIn("'aria-pressed'", s)
        self.assertIn("t('settings.resetNote')", s)
        self.assertIn("addEventListener('storage'", s)

    def test_h_what_each_does_behind_a_hint(self):
        # site decisions 161 (Robin, 2026-11-02, "Yes, as drafted"): one "?" after the heading,
        # a line per preset in the ruled words, then a link to Help's Settings section
        ruled = {
            # site decisions 174 (Robin, 2026-11-07): Default's note for the new defaults; English emphasized's
            "default": "Ordpar as it starts: each definition in Norwegian and English, the Norwegian in full colour and the English faded; short formula lines in both languages; every example with its English; small articles in full.",
            "english": "for when you read mostly for the English: in each definition the English in full colour and the Norwegian faded; short formula lines in English only.",
            "concise": "for when you only need the meaning: each definition in English only; the first two examples under each sense and set phrase, with a line to show the rest; small articles a little shorter. An article not yet translated still shows its Norwegian.",
            "learners": "for reading the Norwegian first: an eye beside the headword hides the examples' English; in each definition the Norwegian in full colour and the English faded; short formula lines in both languages.",
        }
        for p in presets_table():
            self.assertEqual(STRINGS.get("settings.presets." + p["id"] + ".note"), ruled[p["id"]], p["id"])
        self.assertEqual(STRINGS.get("settings.presets.hintButton"), "About the presets")
        self.assertIn("settings.presets.helpLink", STRINGS)
        body = re.search(r"function presets\(\) \{(.*?)\n  \}", SETTINGS_JS, re.S).group(1)
        self.assertIn("hintControl({ key: 'presets' }, data, sec, h2", body)
        self.assertIn("href: '/help/#settings'", body)
        self.assertIn("if (h.data.link) {", SETTINGS_JS)
        self.assertIn(".ordpar-presets { position: relative; }", _read(SITE, "shell.css"))


def _built(*parts):
    path = os.path.join(OUT, *parts)
    return _read(path) if os.path.exists(path) else None


HELP = _built("help", "index.html")


@unittest.skipIf(HELP is None, "no build in %s" % OUT)
class Built(unittest.TestCase):

    def test_a_help_has_the_section_before_pronunciation(self):
        self.assertIn('<h2 id="settings">Settings</h2>', HELP)
        self.assertLess(HELP.index('<h2 id="settings">'), HELP.index('<h2 id="pronunciation">'))

    def test_b_help_words_are_help_md(self):
        # the section's blocks, read from help.md itself
        src = _read(ROOT, "ordpar", "help.md")
        blocks = [b.strip() for b in src.split("\n\n")]
        i, j = blocks.index("## Settings"), blocks.index("## Pronunciation")
        paras = blocks[i + 1:j]
        self.assertEqual(len(paras), 10)                  # 152: Norwegian only, Labels in Norwegian; 159: Spoken words and the voice (Robin, 2026-11-02); 174: English emphasized
        self.assertTrue(paras[1].startswith("**Presets.** At the top of Settings"))
        sec = re.search(r'<h2 id="settings">Settings</h2>(.*?)<h2 id="pronunciation">', HELP, re.S).group(1)
        self.assertEqual(about.plain(sec), about.plain("\n\n".join(paras)))
        # the markup as help_page renders it: bold lead-ins, italic names, the two links
        _t, body = about.help_page()
        want = re.search(r'<h2 id="settings">Settings</h2>(.*?)<h2 id="pronunciation">', body, re.S).group(1)
        self.assertEqual(" ".join(sec.split()), " ".join(want.split()))
        self.assertEqual(sec.count("<strong>"), 8)            # 152: two more lead-ins; 159: one more; 174: one more
        self.assertIn('<a href="https://ordpar.no/settings/">settings</a>', sec)
        self.assertIn('<a href="https://ordpar.no/settings/#article">Article</a>', sec)
        self.assertIn("<em>Default</em>, <em>English emphasized</em>, <em>Concise</em> and <em>For learners</em>", sec)   # 174

    def test_c_settings_page_carries_the_words(self):
        page = _built("settings", "index.html")
        self.assertIsNotNone(page)
        for k, v in WORDS.items():
            self.assertIn(json.dumps(v, ensure_ascii=False)[1:-1], page, k)
        js = _built("site", "settings.js")
        self.assertIsNotNone(js)
        self.assertEqual([(p["id"], p["values"]) for p in presets_table(js)], RULED)


if __name__ == "__main__":
    unittest.main()
