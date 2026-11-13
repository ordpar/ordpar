"""Site decisions 69 and 70 (Robin, 2026-10-20): the mini inside the window, and the mini's body
formatted as the article's. Stdlib unittest; the page script's placement runs under bun (or
node) against a small stand-in DOM, skipped when neither is on PATH.

What it pins:

* **69 — placement** (`page.PAGE_JS` `place`): an opened mini that would pass the window's right
  edge is moved left to sit 8 px short of it; one that fits is left alone; it never goes past the
  left edge; a resize re-places every open mini; a closed one is not touched. Its width is capped
  at the window less 1rem (`SITE_CSS`), so a window narrower than the mini keeps it on screen.
* **70 — the body's look** (`page.article_css`): a link inside a mini (`a.ordbok-xword`) takes the
  text's colour, by day and by night, in rules that come after and outrank the deck's
  `.ordbok a` / `.nightMode .ordbok a`; on a touch screen a mini's peek is hidden as the article's
  is, after the deck's rule that printed it inline; the body's greys are the article's.
* **No page markup is involved**: the deck's renderers are untouched, and both changes live in the
  shipped sheet and script only.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
sys.path.insert(0, ROOT)

from ordpar.sitegen import page  # noqa: E402


def _runner():
    return shutil.which("bun") or shutil.which("node")


#: A stand-in DOM for the page script: one control whose mini box is drawn at `x0` with width `w`
#: plus whatever `style.left` says; the window `W` wide. Since decisions 80 the mini script opens a
#: mini (`ordpar-mopen` on its `.ordbok-xref`) and places it through the page script's `place`,
#: exported as `window.ordparPlace`; a resize re-places every `.ordpar-mopen>.ordbok-xmini`.
HARNESS = r"""
const handlers = {doc: {}, win: {}};
const store = {};
globalThis.localStorage = {getItem: k => (k in store ? store[k] : null), setItem() {}, removeItem() {}};
globalThis.navigator = {};
const E = {clientWidth: 390, classList: {contains: () => false}, hasAttribute: () => false};
function makeMini(x0, w) {
  const m = {style: {left: ''}, nextSibling: null,
    classList: {contains: c => c === 'ordbok-xmini'},
    getBoundingClientRect() { const l = x0 + (parseFloat(this.style.left) || 0); return {left: l, right: l + w, width: w}; }};
  return {m, open: false};
}
let controls = [];
globalThis.getComputedStyle = n => ({left: n.style.left || '0px'});
globalThis.document = {documentElement: E,
  addEventListener(t, f) { (handlers.doc[t] = handlers.doc[t] || []).push(f); },
  getElementById: () => null, querySelector: () => null,
  querySelectorAll: sel => sel === '.ordpar-mopen>.ordbok-xmini' ? controls.filter(c => c.open).map(c => c.m) : []};
globalThis.window = globalThis;
globalThis.addEventListener = (t, f) => { (handlers.win[t] = handlers.win[t] || []).push(f); };
eval(PAGE_JS);
function open(c) { c.open = true; window.ordparPlace(c.m); return c.m.style.left; }
const out = {};
E.clientWidth = 390;
let a = makeMini(200, 306); controls = [a]; out.right = open(a);          // 506 > 382: left by 124
let b = makeMini(20, 306); controls = [b]; out.fits = open(b);            // fits: untouched
E.clientWidth = 300;
let c = makeMini(100, 290); controls = [c]; out.leftEdge = open(c);       // would pass the left edge
let d = makeMini(150, 284); controls = [d]; out.narrow = open(d);         // capped width, flush right
E.clientWidth = 1280;
let e = makeMini(900, 306); let f = makeMini(900, 306); controls = [e, f]; open(e);
out.wide = e.m.style.left;
E.clientWidth = 390; handlers.win.resize.forEach(h => h());              // a rotation: re-placed
out.resized = e.m.style.left; out.closedUntouched = f.m.style.left;
E.clientWidth = 1280; handlers.win.resize.forEach(h => h());
out.back = e.m.style.left;
process.stdout.write(JSON.stringify(out));
"""


class Placement(unittest.TestCase):
    """Decisions 69: the page script's `place`."""

    @classmethod
    def setUpClass(cls):
        runner = _runner()
        if not runner:
            raise unittest.SkipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "place.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("const PAGE_JS = %s;\n%s" % (json.dumps(page.PAGE_JS), HARNESS))
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            cls.out = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_moved_left_to_the_right_edge(self):
        self.assertEqual(self.out["right"], "-124px")       # 390 - 8 - 506

    def test_a_mini_that_fits_is_left_alone(self):
        self.assertEqual(self.out["fits"], "")
        self.assertEqual(self.out["wide"], "")

    def test_never_past_the_left_edge(self):
        self.assertEqual(self.out["leftEdge"], "-92px")     # lands at 8, not at 300 - 8 - 290
        self.assertEqual(self.out["narrow"], "-142px")      # 284 wide in 300: 8 .. 292

    def test_resize_replaces_open_minis_only(self):
        self.assertEqual(self.out["resized"], "-824px")     # 900 + 306 → right at 382
        self.assertEqual(self.out["closedUntouched"], "")
        self.assertEqual(self.out["back"], "")

    def test_width_capped_at_the_window(self):
        self.assertIn(".ordbok-xmini{max-width:calc(100vw - 1rem)}", page.article_css())

    def test_vertical_position_is_the_decks(self):
        # the script sets `left` only; the mini still opens below the word (the deck's `top`)
        self.assertNotIn("style.top", page.PAGE_JS)
        self.assertIn(".ordbok-xmini{display:none;position:absolute;left:0;top:1.7em", page.article_css())


class BodyLook(unittest.TestCase):
    """Decisions 70: the mini's body as the article's, in the shipped sheet."""

    css = page.article_css()

    def after(self, earlier, later):
        i, j = self.css.find(earlier), self.css.find(later)
        self.assertGreater(i, -1, earlier)
        self.assertGreater(j, i, later)

    def test_links_in_the_texts_colour(self):
        self.after(".nightMode .ordbok a{color:",
                   ".ordbok a.ordbok-xword,.nightMode .ordbok a.ordbok-xword{color:inherit}")

    def test_no_inline_peek_on_touch(self):
        self.after(".mini .ordbok-xpeek,.mini .ordbok-xref:hover>.ordbok-xpeek{display:inline",
                   ".mini .ordbok-xpeek,.mini .ordbok-xref:hover>.ordbok-xpeek{display:none}")

    def test_greys_are_the_articles(self):
        self.assertIn(".mini-pair>span[lang=en]{color:#757070;font-size:.95em}", self.css)
        self.assertIn(".nightMode .mini-pair>span[lang=en]{color:#b9b6b6}", self.css)
        self.after(".nightMode .mini-exen,.nightMode .mini-nodef,.nightMode .mini-ety",   # the deck's (gloss out since 114)
                   ".nightMode .mini-exen,.nightMode .mini-ety,.nightMode .mini-added,"
                   ".nightMode .mini-nodef{color:#b9b6b6}")
        self.after(".nightMode .mini-snum,.nightMode .mini-expr-term{color:",
                   ".nightMode .mini-snum{color:#b9b6b6}")

    def test_shipped_sheet_carries_it(self):
        shipped = page.shipped(page.CSS_ALL_HREF)
        self.assertIn("a.ordbok-xword", shipped)
        self.assertNotIn("decisions 70", shipped)          # comments stripped (decisions 61)
        self.assertIn("function place(m)", page.shipped(page.JS_ALL_HREF))


if __name__ == "__main__":
    unittest.main()
