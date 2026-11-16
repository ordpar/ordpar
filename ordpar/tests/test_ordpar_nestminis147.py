"""Site decisions 147 (Robin, 2026-10-29): nested small articles get four choices, a second box then
the same box the new default, no limit; and nothing done inside a box scrolls the page — the source.

Pins:

* **The row** (`site/shell.js` `SETTINGS`): `nestminis` = second | inplace | stacked | off, the default first (decisions 107; Robin's
  order, default `second`, right after `minicontent` under Article -> Small articles; **`nestlimit`
  gone** from the table, from the export list (`personal.js` `SETTING_KEYS`), from the presets, from
  the strings, from `settings.js` (`shown`) and from `mini.js`.
* **The words** (`site/strings/en.json`), exactly as approved (decisions 147).
* **The presets** (decisions 136): Concise and For learners name `nestminis` at the new default
  (as recommended); Default names nothing.
* **The script** (`site/mini.js`): it reads the four values with the default `second`, a saved
  `stacked` kept; `inPlaceAt` (from which depth a link is a step in the box it is in: in place 1,
  second 2, stacked never); one `step`/`stepBack` for every box, its steps the box's own
  (`c.steps`); `target` refuses only under `off` (no limit).
* **Rule 3** at source level (nothing done inside the small article boxes ever scrolls the main
  window): no `scrollTo`, `scrollBy` or `scrollIntoView` in `mini.js`; every
  `focus(` is `preventScroll` (the old fallback to a plain `focus()` gone); the boxes out of scroll
  anchoring; `hold` before each change that can shorten the page.
* **The address** (decisions 146, the head script `sitegen/head.py` `THEME_JS`, run under bun or
  node): `#nestminis=second` is taken for the visit, `#nestlimit=2` is an unknown key, ignored and
  left in the address; `mini.js` then reads `second`.

The browser side: `test_ordpar_browser_nestminis147.py`. Stdlib unittest; the JS parts under bun or
node (skipped without either).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo
sys.path.insert(0, ROOT)
SITE = os.path.join(ROOT, "ordpar", "site")

from ordpar.sitegen import head  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SHELL_JS = _read(SITE, "shell.js")
SETTINGS_JS = _read(SITE, "settings.js")
PERSONAL_JS = _read(SITE, "personal.js")
MINI_JS = _read(SITE, "mini.js")
STRINGS = json.loads(_read(SITE, "strings", "en.json"))

#: The words Robin approved (decisions 147, 2026-10-29), the default first (107)
WORDS = {
    "settings.nestminis": "A link inside a small article",
    "settings.nestminis.second": "Opens its small article in a second box; a link there changes that box",
    "settings.nestminis.inplace": "Opens its small article in the same box",
    "settings.nestminis.stacked": "Opens each small article in a box of its own",
    "settings.nestminis.off": "Opens its whole article",
    "settings.nestminis.hint": "In the same box: the box changes to the new word, and a line at its top, "
                               "such as \"← skip\", goes back one word at a time. In a second box: the new "
                               "small article opens below its word, over the first; a link inside the "
                               "second box changes that box, with the same line back. In a box of its own: "
                               "every link opens one more box, over the one before. There is no limit. A "
                               "click outside every box closes them all.",
}


def rows():
    body = re.search(r"var SETTINGS = \[(.*?)\n  \];", SHELL_JS, re.S).group(1)
    return [(m.group(1), m.group(0)) for m in re.finditer(r"\{ key: '(\w+)'[^\n]*\}", body)]


def presets():
    return json.loads(re.search(r"var PRESETS = (\[.*?\n  \]);", SETTINGS_JS, re.S).group(1))


def _run(body):
    runner = shutil.which("bun") or shutil.which("node")
    if not runner:
        raise unittest.SkipTest("no bun/node on PATH")
    tmp = tempfile.mkdtemp()
    try:
        script = os.path.join(tmp, "run147.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(body)
        res = subprocess.run([runner, script], capture_output=True, timeout=120)
        out = res.stdout.decode("utf-8", "replace")
        if res.returncode != 0:
            raise AssertionError("JS failed:\n" + out + res.stderr.decode("utf-8", "replace"))
        return json.loads(out.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class TheRow(unittest.TestCase):

    def test_a_four_values_second_the_default(self):
        keys = [k for k, _ in rows()]
        i = keys.index("minicontent")
        self.assertEqual(keys[i + 1], "nestminis")
        self.assertEqual(dict(rows())["nestminis"],
                         "{ key: 'nestminis', values: ['second', 'inplace', 'stacked', 'off'], def: 'second', "
                         "section: 'article', sub: 'mini' }")

    def test_b_nestlimit_gone_everywhere(self):
        self.assertNotIn("nestlimit", [k for k, _ in rows()])
        self.assertNotIn("nestlimit", SHELL_JS)
        keys = re.search(r"SETTING_KEYS = \[(.*?)\];", PERSONAL_JS, re.S).group(1)
        self.assertNotIn("'nestlimit'", keys)
        self.assertIn("'nestminis'", keys)
        self.assertNotIn("nestlimit", SETTINGS_JS)                 # `shown` and the presets
        self.assertNotIn("nestlimit", MINI_JS)
        self.assertNotIn("nestLimit", MINI_JS)
        self.assertEqual([k for k in STRINGS if k.startswith("settings.nestlimit")], [])

    def test_c_the_words_exactly(self):
        for k, v in WORDS.items():
            self.assertEqual(STRINGS.get(k), v, k)
        # the default first in the file, as the settings page draws them (107)
        ks = [k for k in STRINGS if k.startswith("settings.nestminis.") and not k.endswith(".hint")]
        self.assertEqual(ks, ["settings.nestminis." + v for v in ("second", "inplace", "stacked", "off")])

    def test_d_the_presets(self):
        got = {p["id"]: p["values"] for p in presets()}
        self.assertEqual(got["default"], {})
        for pid in ("concise", "learners"):
            self.assertEqual(got[pid].get("nestminis"), "second", pid)
            self.assertNotIn("nestlimit", got[pid], pid)


class TheScript(unittest.TestCase):

    def test_a_reads_four_values(self):
        self.assertIn("setting('nestminis', ['second', 'inplace', 'stacked', 'off'], 'second')", MINI_JS)
        self.assertIn("function inPlaceAt(mode) { return mode === 'inplace' ? 1 : mode === 'second' ? 2 : 0; }",
                      MINI_JS)

    def test_b_one_step_path_for_every_box(self):
        self.assertIn("function step(c, a, t) {", MINI_JS)
        self.assertIn("function stepBack(c, focus) {", MINI_JS)
        self.assertIn("if (d && from && d >= from && chain[d - 1]) { step(chain[d - 1], a, t); return; }", MINI_JS)
        self.assertIn("c.steps.push(", MINI_JS)
        self.assertNotIn("stepTok", MINI_JS)                       # the one global list of steps went
        t = re.search(r"function target\(a\) \{(.*?)\n  \}", MINI_JS, re.S).group(1)
        self.assertIn("if (nestMode() === 'off') { return null; }", t)

    def test_c_the_setting_read_live(self):
        got = _run(r"""
globalThis.window = globalThis;
const src = require('fs').readFileSync(%s, 'utf8');
let V = {};
globalThis.ordparRead = k => (k in V ? V[k] : null);
(0, eval)(src);
const M = globalThis.ordparMinis, out = {};
for (const v of [null, 'inplace', 'second', 'stacked', 'off', 'bogus', '2']) { V = v == null ? {} : { nestminis: v }; out[String(v)] = M.nestMode(); }
out.at = ['inplace', 'second', 'stacked', 'off'].map(M.inPlaceAt);
out.hasLimit = 'nestLimit' in M;
process.stdout.write(JSON.stringify(out));""" % json.dumps(os.path.join(SITE, "mini.js")))
        self.assertEqual(got["null"], "second")                    # nothing saved: the new default
        for v in ("inplace", "second", "stacked", "off"):
            self.assertEqual(got[v], v)                            # a saved `stacked` kept
        self.assertEqual(got["bogus"], "second")
        self.assertEqual(got["2"], "second")
        self.assertEqual(got["at"], [1, 2, 0, 0])
        self.assertFalse(got["hasLimit"])


class RuleThree(unittest.TestCase):
    """Nothing in a box scrolls the page (decisions 147)."""

    def test_a_no_page_scrolling_calls(self):
        code = re.sub(r"/\*.*?\*/", "", MINI_JS, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        for call in (r"\bscrollTo\(", r"\bscrollBy\(", r"\bscrollIntoView\(", r"\bpx:", r"\bpy:"):
            self.assertIsNone(re.search(call, code), call)        # (not the whole file in the message)

    def test_b_every_focus_keeps_the_page(self):
        code = re.sub(r"/\*.*?\*/", "", MINI_JS, flags=re.S)
        calls = re.findall(r"\.focus\(([^)]*)\)", code)
        self.assertTrue(calls)
        for c in calls:
            self.assertEqual(c, "{ preventScroll: true }", c)

    def test_c_anchoring_and_the_hold(self):
        self.assertIn("m.style.overflowAnchor = 'none';", MINI_JS)
        self.assertIn("function hold() {", MINI_JS)
        self.assertIn("e.style.minHeight = held + 'px';", MINI_JS)
        for f in ("function closeFrom(i) {", "function step(c, a, t) {", "function stepBack(c, focus) {"):
            body = MINI_JS[MINI_JS.index(f):]
            body = body[:body.index("\n  }\n")]
            self.assertIn("hold()", body, f)
        self.assertIn("unhold();", MINI_JS)                        # lowered as the reader scrolls up


class TheAddress(unittest.TestCase):
    """Decisions 146: the head script reads its table from `SETTINGS` at build time."""

    def test_second_accepted_nestlimit_ignored(self):
        table = dict(head.settings_table())
        self.assertEqual(table["nestminis"], ["second", "inplace", "stacked", "off"])
        self.assertNotIn("nestlimit", table)
        got = _run(r"""
globalThis.window = globalThis;
// bun's global is an event target, Node.js's is not: mini.js listens for 'scroll' on the window
if (!globalThis.addEventListener) { globalThis.addEventListener = function () {}; }
const m = {};
globalThis.document = { documentElement: { classList: { add() {}, remove() {}, contains() { return false; } },
  setAttribute() {}, removeAttribute() {} }, querySelector: () => null, querySelectorAll: () => [],
  getElementById: () => null, readyState: 'complete', addEventListener() {} };
globalThis.localStorage = { getItem: k => (k in m ? m[k] : null), setItem(k, v) { m[k] = String(v); } };
const ss = {};
globalThis.sessionStorage = { getItem: k => (k in ss ? ss[k] : null), setItem(k, v) { ss[k] = String(v); } };
globalThis.location = { hash: '#nestminis=second&nestlimit=2&q=hus', pathname: '/bm-en/', search: '' };
const replaced = [];
globalThis.history = { state: null, replaceState(s, t, u) { replaced.push(u); } };
(0, eval)(%s);
const out = { visit: window.ordparVisit.settings, nest: window.ordparRead('nestminis'),
  limit: window.ordparRead('nestlimit'), replaced };
// mini.js reads the visit's value through ordparRead
(0, eval)(require('fs').readFileSync(%s, 'utf8'));
out.mode = window.ordparMinis.nestMode();
// an address with a value the key does not accept: ignored, the default stands
location.hash = '#nestminis=nested'; delete window.ordparVisit; delete window.ordparRead;
for (const k in ss) delete ss[k];
(0, eval)(%s);
out.badVisit = window.ordparVisit.settings;
out.badMode = window.ordparMinis.nestMode();
process.stdout.write(JSON.stringify(out));""" % (json.dumps(head.THEME_JS), json.dumps(os.path.join(SITE, "mini.js")),
                                                 json.dumps(head.THEME_JS)))
        self.assertEqual(got["visit"], {"nestminis": "second"})
        self.assertEqual(got["nest"], "second")
        self.assertIsNone(got["limit"])                            # an unknown key: never read
        self.assertEqual(got["replaced"][0], "/bm-en/#nestlimit=2&q=hus")   # and left in the address
        self.assertEqual(got["mode"], "second")
        self.assertEqual(got["badVisit"], {})
        self.assertEqual(got["badMode"], "second")


if __name__ == "__main__":
    unittest.main()
