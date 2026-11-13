# -*- coding: utf-8 -*-
"""Site decisions 166 (Robin, 2026-11-05, "Yes, as proposed"): the address that opens an article's
"Suggest a correction" form on arrival, `/bm-en/<id>/#report`, for the deck's link on every card —
the parts a browser is not needed for. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-report-address-166-2026-11-05.md`. The
browser's side: `test_ordpar_browser_reportaddr166.py`.

* **The key lives with the fragment's other uses**: `report.js` `ADDRESS_KEY` is `report`, a bare
  word; it is not a key of the settings table (`head.settings_table`, decisions 146), so the head
  script neither stores it as a setting nor takes it off the address — it keeps every part that is
  not the table's — and it is no part of a search (`#q=`).
* **`takeAddress`** (under bun, a stand-in location and history): the key found among the fragment's
  `&`-separated parts is taken off with `history.replaceState` — the entry's state and the other
  parts kept (`#q=hus&report` -> `#q=hus`, `#theme=dark&report&q=hus` -> `#theme=dark&q=hus`,
  `#report` -> no fragment) — and only the exact word: `#reporting`, `#report=1`, `#q=report` are
  left alone. **`fromAddress`** presses the button only then, and does nothing without a button
  or with the form already open.
* **The wiring**: the article page's script (`page.PAGE_JS` `foot`) calls `fromAddress` with the
  button `mount` returned, after the row is in the page (the form is put after the row, so the row
  must have a parent); the rows `lookup.js` draws under articles shown whole (word pages, the
  search) do not (the article page only).
* **Nothing new is sent**: the message is the same six fields; the address is never read into it.
* **The address documented** in `build-site.md` § Report a mistake, as the one form for the deck.

Fails on f2c7cc366's code (no `ADDRESS_KEY`, no `fromAddress`). Stdlib unittest; the bun part
skipped without bun.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
SITE = os.path.join(ORDPAR, "site")
sys.path.insert(0, ROOT)

from ordpar.sitegen import head, page  # noqa: E402

BUN = shutil.which("bun")


def _read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Key(unittest.TestCase):

    def test_the_key(self):
        src = _read(SITE, "report.js")
        self.assertEqual(re.findall(r"var ADDRESS_KEY = '([^']*)';", src), ["report"])

    def test_not_a_setting(self):
        keys = [k for k, _v in head.settings_table()]
        self.assertTrue(keys)
        self.assertNotIn("report", keys)

    def test_the_head_script_keeps_other_parts(self):
        # the head script's fragment loop (146): a table key starts the visit, every other part is
        # kept (`k.push`) and written back — so `report` reaches report.js
        js = head.THEME_JS
        self.assertIn("if(O.call(T,p[0])){", js)
        self.assertIn("else if(H[i])k.push(H[i])", js)
        self.assertIn("(k.length?'#'+k.join('&'):'')", js)

    def test_nothing_new_sent(self):
        src = _read(SITE, "report.js")
        body = src[src.index("function message("):src.index("function creditOk(")]
        self.assertNotIn("location", body)
        self.assertNotIn("ADDRESS_KEY", body)


class Wiring(unittest.TestCase):

    def test_the_article_page_calls_it_after_the_row_is_placed(self):
        js = page._PAGE_JS
        foot = js[js.index("function foot(){"):js.index("foot();")]
        self.assertIn("R.mount(p,", foot)
        placed = foot.index("f.insertBefore(p,f.firstChild);")
        self.assertGreater(foot.index("R.fromAddress(b)"), placed)

    def test_not_from_the_rows_lookup_draws(self):
        self.assertNotIn("fromAddress", _read(SITE, "lookup.js"))

    def test_documented(self):
        doc = _read(ORDPAR, "docs", "build-site.md")
        sec = doc[doc.index("## Report a mistake"):doc.index("## The deploy")]
        self.assertIn("/bm-en/<id>/#report", sec)


@unittest.skipUnless(BUN, "bun is not on PATH")
class Script(unittest.TestCase):
    """report.js under bun, with a stand-in location and history."""

    PROG = r"""
const src = require('fs').readFileSync(%s, 'utf8');
function load(hash) {
  const calls = [];
  const g = {
    location: { pathname: '/bm-en/1000/', search: '', hash },
    history: { state: { kept: 1 }, replaceState(s, t, u) { calls.push([s, u]); } },
  };
  new Function('globalThis', src.replace(/typeof globalThis !== 'undefined' \? globalThis : this/, 'globalThis'))(g);
  return { R: g.ordparReport, calls };
}
const out = {};
for (const h of ['#report', '#q=hus&report', '#report&q=hus', '#theme=dark&report&q=hus', '#reporting',
                 '#report=1', '#q=report', '', '#q=hus']) {
  const { R, calls } = load(h);
  out[h] = { took: R.takeAddress(), calls };
}
// fromAddress: presses the button only when the address asks, never without one or when open
const button = (exp) => ({ parentNode: {}, pressed: 0, getAttribute() { return exp; }, click() { this.pressed++; } });
let t = load('#report'), b = button('false');
out.press = { opened: t.R.fromAddress(b), pressed: b.pressed, calls: t.calls.length };
t = load('#q=hus'); b = button('false');
out.noKey = { opened: t.R.fromAddress(b), pressed: b.pressed, calls: t.calls.length };
t = load('#report');
out.noButton = { opened: t.R.fromAddress(null), calls: t.calls.length };
t = load('#report'); b = button('true');
out.alreadyOpen = { opened: t.R.fromAddress(b), pressed: b.pressed, calls: t.calls.length };
t = load('#report'); b = button('false'); b.parentNode = null;
out.notPlaced = { opened: t.R.fromAddress(b), pressed: b.pressed, calls: t.calls.length };
out.key = t.R.ADDRESS_KEY;
console.log(JSON.stringify(out));
"""

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            prog = os.path.join(d, "t.js")
            with open(prog, "w", encoding="utf-8") as f:
                f.write(cls.PROG % json.dumps(os.path.join(SITE, "report.js")))
            res = subprocess.run([BUN, prog], capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        cls.out = json.loads(res.stdout.decode("utf-8").strip().splitlines()[-1])

    def test_taken_off_the_other_parts_kept(self):
        o = self.out
        self.assertEqual(o["key"], "report")
        for h, left in (("#report", "/bm-en/1000/"), ("#q=hus&report", "/bm-en/1000/#q=hus"),
                        ("#report&q=hus", "/bm-en/1000/#q=hus"),
                        ("#theme=dark&report&q=hus", "/bm-en/1000/#theme=dark&q=hus")):
            with self.subTest(h=h):
                self.assertIs(o[h]["took"], True)
                self.assertEqual(o[h]["calls"], [[{"kept": 1}, left]])   # the entry's state kept

    def test_only_the_exact_word(self):
        for h in ("#reporting", "#report=1", "#q=report", "", "#q=hus"):
            with self.subTest(h=h):
                self.assertIs(self.out[h]["took"], False)
                self.assertEqual(self.out[h]["calls"], [])

    def test_from_address(self):
        o = self.out
        self.assertEqual(o["press"], {"opened": True, "pressed": 1, "calls": 1})
        self.assertEqual(o["noKey"], {"opened": False, "pressed": 0, "calls": 0})
        self.assertEqual(o["noButton"], {"opened": False, "calls": 0})          # the key stays
        self.assertEqual(o["alreadyOpen"], {"opened": False, "pressed": 0, "calls": 0})
        self.assertEqual(o["notPlaced"], {"opened": False, "pressed": 0, "calls": 0})


if __name__ == "__main__":
    unittest.main()
