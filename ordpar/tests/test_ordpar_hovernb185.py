"""Site decisions 185 (Robin, 2026-11-12): the linked word's first Norwegian definition as a hover
choice everywhere — the static half (the browser half: `test_ordpar_browser_hovernb185.py`).

* **The settings' table** (`shell.js` `SETTINGS`): `peek` = on | nb | off, `on` the default and
  first, `off` kept, so a stored value or an address reads as before; under Article › Cross-references,
  not a layer setting; in the Definer address's table (`head.settings_table`, 146) with all three.
* **The words** (Robin's, 2026-11-12): the title "When the pointer rests on a linked word"; "Its
  translation", "Its first Norwegian definition", "Nothing", "Nothing" keeping its note.
* **The head script's classes and the shell's** (run under bun or node): `peek` = nb ->
  `ordpar-nbo-hovnb` and no `ordpar-peek-off`; on and nothing stored -> neither; off ->
  `ordpar-peek-off`; under the Norwegian-only view with the English equivalents hidden its own
  `nbhover` decides, whatever `peek` says; with them shown, `peek` does. The shell draws the same
  classes, and on a change of `peek` alone. `#peek=nb` starts a visit with it, nothing saved; the
  pop-up address carries it.
* **The presets** (136, 161, 174): none names `peek`, so each sets today's value, `on`.
* **The Loading setting** (`mini.js` `nbPeek`): under `click` the peek is made only from a `snip/`
  file the page has (`lookup.js` `loadedSnippets`, which never fetches); an English partner word
  finds its key through the Norwegian link to the same target in its pair.

Stdlib unittest; the JS parts under bun or node (skipped without either).
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
sys.path.insert(0, ORDPAR)
sys.path.insert(0, HERE)

from sitegen import head  # noqa: E402
import test_ordpar_settingsaddr146 as T146  # noqa: E402  (its stand-in page and runner)


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SHELL_JS = _read(SITE, "shell.js")
STRINGS = json.loads(_read(SITE, "strings", "en.json"))


def _js(body):
    return T146._run(T146._prelude() + body)


class TheSetting(unittest.TestCase):

    def test_a_the_row(self):
        body = SHELL_JS[SHELL_JS.index("var SETTINGS = ["):SHELL_JS.index("var SPEC = {}")]
        row = re.search(r"\{ key: 'peek'[^}]*\}", body).group(0)
        self.assertIn("values: ['on', 'nb', 'off'], def: 'on', section: 'article', sub: 'xref'", row)
        self.assertNotIn("layer", row)
        self.assertEqual(dict(head.settings_table())["peek"], ["on", "nb", "off"])

    def test_b_the_words(self):
        self.assertEqual(STRINGS["settings.peek"], "When the pointer rests on a linked word")
        self.assertEqual(STRINGS["settings.peek.on"], "Its translation")
        self.assertEqual(STRINGS["settings.peek.nb"], "Its first Norwegian definition")
        self.assertEqual(STRINGS["settings.peek.off"], "Nothing")
        self.assertEqual(STRINGS["settings.peek.off.note"],
                         "Fewer pop-ups while you read. A click still opens the link.")

    def test_c_the_presets(self):
        js = _read(SITE, "settings.js")
        presets = json.loads(re.search(r"var PRESETS = (\[.*?\n  \]);", js, re.S).group(1))
        self.assertTrue(presets)
        for pr in presets:
            self.assertNotIn("peek", pr["values"], pr["id"])     # each sets the default, `on`

    def test_d_the_hover_follows_the_loading_setting(self):
        mini = _read(SITE, "mini.js")
        body = mini[mini.index("function nbPeek(x)"):mini.index("/** `minifetch = page`")]
        self.assertIn("if (fetchMode() === 'click') {", body)
        self.assertIn("have = L.loadedSnippets ? L.loadedSnippets(key) : null;", body)
        self.assertIn("if (!have) { return; }", body)
        self.assertLess(body.index("if (!have) { return; }"), body.index("x._nbpk = 1;"))
        lookup = _read(SITE, "lookup.js")
        self.assertIn("function loadedSnippets(key) { return snippets[key] || null; }", lookup)
        self.assertIn("loadedSnippets: loadedSnippets,", lookup)


class TheClasses(unittest.TestCase):
    CASES = {
        "none": {},
        "on": {"peek": "on"},
        "nb": {"peek": "nb"},
        "off": {"peek": "off"},
        "bad": {"peek": "maybe"},
        # the Norwegian-only view, the equivalents hidden: its own `nbhover` lies over `peek`
        "layer_none": {"nbonly": "on", "peek": "nb"},
        "layer_nbdef": {"nbonly": "on", "nbhover": "nbdef", "peek": "off"},
        # the equivalents shown: the reader's own `peek`
        "shown_nb": {"nbonly": "on", "nbequiv": "shown", "peek": "nb"},
        "layer_off": {"nbonly": "off", "nbhover": "nbdef", "peek": "on"},
    }
    WANT = {   # name -> (hovnb, peek-off)
        "none": (False, False), "on": (False, False), "nb": (True, False), "off": (False, True),
        "bad": (False, False), "layer_none": (False, True), "layer_nbdef": (True, False),
        "shown_nb": (True, False), "layer_off": (False, False),
    }

    @classmethod
    def setUpClass(cls):
        cls.r = _js("""
const cases = %s;
for (const name in cases) {
  const h = head('', '/bm-en/24627/', cases[name]);
  out[name] = { head: h.classes, writes: h.writes };
}
for (const name in cases) {
  const p = page('', '/bm-en/24627/', cases[name]);
  const sh = shell();
  sh.applyAll();
  out[name].shell = [...p.cls].filter(c => ['ordpar-js', 'nightMode', 'ordpar-chrome'].indexOf(c) < 0).sort();
  out[name].hoverNb = sh.hoverNb();
}
// a change of `peek` alone, on a page (setSetting: stored, the classes redrawn)
{
  const p = page('', '/bm-en/24627/', {});
  const sh = shell();
  sh.applyAll();
  out.change = {};
  for (const v of ['nb', 'off', 'on']) {
    sh.setSetting('peek', v);
    out.change[v] = { hovnb: p.cls.has('ordpar-nbo-hovnb'), off: p.cls.has('ordpar-peek-off'),
                      stored: localStorage.getItem('peek') };
  }
}
// the address starts a visit with it, nothing saved (146); the pop-up address carries it
const v = head('#peek=nb&q=hus', '/bm-en/', {});
out.visit = { classes: v.classes, visit: v.visit, writes: v.writes };
page('', '/settings/', { peek: 'nb' });
out.addr = shell().popupAddress();
console.log(JSON.stringify(out));""" % json.dumps(cls.CASES))

    def test_a_the_head_script(self):
        for name, (hovnb, off) in self.WANT.items():
            with self.subTest(name):
                c = set(self.r[name]["head"])
                self.assertEqual("ordpar-nbo-hovnb" in c, hovnb, c)
                self.assertEqual("ordpar-peek-off" in c, off, c)
                self.assertEqual(self.r[name]["writes"], [])

    def test_b_the_shell_draws_the_same(self):
        for name in self.CASES:
            with self.subTest(name):
                head_set = {c for c in self.r[name]["head"] if c not in ("ordpar-js", "nightMode")}
                self.assertEqual(set(self.r[name]["shell"]), head_set, self.r[name])
                self.assertEqual(self.r[name]["hoverNb"], self.WANT[name][0])

    def test_c_a_change_of_peek_alone(self):
        ch = self.r["change"]
        self.assertEqual(ch["nb"], {"hovnb": True, "off": False, "stored": "nb"})
        self.assertEqual(ch["off"], {"hovnb": False, "off": True, "stored": "off"})
        self.assertEqual(ch["on"], {"hovnb": False, "off": False, "stored": "on"})

    def test_d_the_address(self):
        self.assertIn("ordpar-nbo-hovnb", self.r["visit"]["classes"])
        self.assertEqual(self.r["visit"]["visit"], {"peek": "nb"})
        self.assertEqual(self.r["visit"]["writes"], [])
        self.assertEqual(self.r["addr"], "https://ordpar.no/bm-en/#peek=nb&q={{str}}")


if __name__ == "__main__":
    unittest.main()
