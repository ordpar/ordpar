# -*- coding: utf-8 -*-
"""Decisions 91 (Robin, 2026-10-22), as built on the site. Stdlib unittest; the page script's
`place` runs under bun (or node) against a small stand-in DOM, skipped when neither is on PATH
(the browser checks are the build's evidence,
`docs/sessions/2026-09-19-ordpar-site-review/evidence/fixes-91-2026-10-22/`).

* **A — the phone scroll jump.** `page.PAGE_JS` `place` (the mini's, through
  `window.ordparPlace`, the peek's on `mouseover`, every open mini's on `resize`) never measures
  the box with its `left` cleared — at its natural place a right overhang widens a phone
  browser's layout viewport for that one forced layout and clamps the scroll near the page's end.
  It measures the box parked a window-width to the left (`left:-100vw`) and sets the same final
  `left` the old `place` set, the peek's `--ordpar-peek-dx` too. The stand-in resolves `vw`
  against a viewport wider than `clientWidth` (a scrollbar), so the arithmetic cannot lean on
  `100vw` and the client width being one number.
* **B — the etymology mini's links.** Every rule of `page.SITE_CSS` that reaches a link or a peek
  INSIDE an article line pair (`.ordpar-pair>span…  …ordbok-xword|xpeek`) ends in
  `:where(:not(.ordbok-xmini *))`, so a mini opened from that line (it sits inside the line's
  span) follows its own rules; decisions 84's relinking rules were the leak (under `emph = no` the
  mini's English partner words were live). `:where` adds no specificity.
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
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import ordbok_gen  # noqa: E402,F401  -- first: mini imports it back for STYLE
from ordpar.sitegen import page  # noqa: E402

NM = ":where(:not(.ordbok-xmini *))"


def _runner():
    return shutil.which("bun") or shutil.which("node")


#: The `place` before decisions 91, verbatim from the page script (git 572f14874), to compare
#: the final positions against.
OLD_PLACE = r"""
function oldPlace(m){
 var s=m.style;s.left='';
 var W=E.clientWidth,r=m.getBoundingClientRect();if(!r.width)return;
 var dx=Math.min(0,W-G0-r.right);if(r.left+dx<G0)dx=G0-r.left;
 if(dx)s.left=((parseFloat(getComputedStyle(m).left)||0)+dx)+'px';}
"""

#: A stand-in DOM: a box drawn at `x0` (where the sheet's `left:0` puts it) with width `w`, shifted
#: by its inline `left` in px or vw (vw = the viewport, 15 px wider than `clientWidth`); every
#: `getBoundingClientRect` logs the inline `left` it was measured at.
HARNESS = r"""
const handlers = {doc: {}, win: {}};
globalThis.localStorage = {getItem: () => null, setItem() {}, removeItem() {}};
globalThis.navigator = {};
const E = {clientWidth: 390, classList: {contains: () => false}, hasAttribute: () => false};
const VW = () => E.clientWidth + 15;
const px = v => !v ? 0 : /vw$/.test(v) ? parseFloat(v) * VW() / 100 : parseFloat(v);
const measured = [];
function box(x0, w, cls) {
  const props = {};
  return {style: {left: '', setProperty(k, v) { props[k] = v; }, removeProperty(k) { delete props[k]; },
                  getPropertyValue(k) { return props[k] || ''; }},
    nextSibling: null, classList: {contains: c => c === cls},
    getBoundingClientRect() { measured.push(this.style.left); const l = x0 + px(this.style.left);
      return {left: l, right: l + w, width: w}; }};
}
let open = [];
globalThis.getComputedStyle = n => ({left: px(n.style.left) + 'px'});
globalThis.document = {documentElement: E,
  addEventListener(t, f) { (handlers.doc[t] = handlers.doc[t] || []).push(f); },
  getElementById: () => null, querySelector: () => null,
  querySelectorAll: sel => sel === '.ordpar-mopen>.ordbok-xmini' ? open : []};
globalThis.window = globalThis;
globalThis.addEventListener = (t, f) => { (handlers.win[t] = handlers.win[t] || []).push(f); };
eval(PAGE_JS);
const G0 = 8;
const oldPlace = eval('(' + OLD_PLACE + ')');   // a module's eval keeps its declarations
const out = {cases: [], measured: null};
// [window width, x0, width]: a right overhang, one that fits, one that would pass the left edge,
// a box wider than the window less the gaps, a computer width
const CASES = [[390, 200, 306], [390, 20, 306], [300, 100, 290], [300, 150, 284], [1280, 900, 306],
               [1280, 1100, 306], [390, 382, 304], [390, -20, 120], [600, 350, 230]];
for (const [W, x0, w] of CASES) {
  E.clientWidth = W;
  const a = box(x0, w, 'ordbok-xmini'), b = box(x0, w, 'ordbok-xmini');
  a.style.left = '-37px'; b.style.left = '-37px';         // a stale left from an earlier placing
  measured.length = 0; window.ordparPlace(a); const at = measured.slice();
  oldPlace(b);
  out.cases.push({W, x0, w, now: a.style.left, old: b.style.left, measuredAt: at});
}
// the peek: the page's own mouseover handler
E.clientWidth = 390;
const p = box(300, 120, 'ordbok-xpeek'), x = {firstChild: p};
measured.length = 0;
handlers.doc.mouseover.forEach(h => h({target: {closest: s => s === '.ordbok-xref' ? x : null}}));
out.peek = {left: p.style.left, dx: p.style.getPropertyValue('--ordpar-peek-dx'), measuredAt: measured.slice()};
// resize: every open mini placed again
const m1 = box(200, 306, 'ordbok-xmini'); open = [m1]; window.ordparPlace(m1);
E.clientWidth = 1280; measured.length = 0; handlers.win.resize.forEach(h => h());
out.resize = {left: m1.style.left, measuredAt: measured.slice()};
// a hidden box (no width) keeps no parking left behind
const hid = box(0, 0, 'ordbok-xmini'); window.ordparPlace(hid); out.hidden = hid.style.left;
process.stdout.write(JSON.stringify(out));
"""


class PlaceNeverAtTheNaturalPlace(unittest.TestCase):
    """A: `place` measures the box parked to the left, and lands it where the old one did."""

    @classmethod
    def setUpClass(cls):
        runner = _runner()
        if not runner:
            raise unittest.SkipTest("no bun/node on PATH")
        tmp = tempfile.mkdtemp()
        try:
            script = os.path.join(tmp, "place91.js")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("const PAGE_JS = %s;\nconst OLD_PLACE = %s;\n%s"
                         % (json.dumps(page.PAGE_JS), json.dumps(OLD_PLACE), HARNESS))
            res = subprocess.run([runner, script], capture_output=True, timeout=60)
            if res.returncode:
                raise AssertionError(res.stderr.decode("utf-8", "replace"))
            cls.out = json.loads(res.stdout.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_never_measured_with_left_cleared(self):
        for c in self.out["cases"]:
            self.assertEqual(c["measuredAt"], ["-100vw"], c)
        self.assertEqual(self.out["peek"]["measuredAt"], ["-100vw"])
        self.assertEqual(self.out["resize"]["measuredAt"], ["-100vw"])

    def test_the_same_final_left_as_before(self):
        for c in self.out["cases"]:
            self.assertEqual(c["now"], c["old"], c)
        self.assertEqual([c["now"] for c in self.out["cases"]][:3], ["-124px", "", "-92px"])

    def test_the_peek_and_its_arrow(self):
        # 300 + 120 = 420 > 382: left by 38, the arrow back by as much
        self.assertEqual(self.out["peek"]["left"], "-38px")
        self.assertEqual(self.out["peek"]["dx"], "38px")

    def test_resize_and_a_hidden_box(self):
        self.assertEqual(self.out["resize"]["left"], "")      # fits again at 1280
        self.assertEqual(self.out["hidden"], "")             # the parking left is undone

    def test_the_source(self):
        body = page.PAGE_JS.split("function place(m){")[1].split("window.ordparPlace=place;")[0]
        self.assertNotIn("s.left='';\n", body.split("getBoundingClientRect")[0])
        self.assertIn("s.left='-100vw';", body)
        # the assumption: the sheet's base `left` of both boxes is 0
        css = page.article_css()
        self.assertIn(".ordbok-xmini{display:none;position:absolute;left:0;", css)
        self.assertIn(".ordbok-xpeek{display:none;position:absolute;left:0;", css)


def _selectors(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@media[^{]*\{", "", css)
    for sel, _body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for one in sel.split(","):
            yield one.strip()


class ArticleLineRulesStopAtAMini(unittest.TestCase):
    """B: an article line pair's link and peek rules never reach a mini opened from the line."""

    css = page.article_css()
    REACH = re.compile(r"\.ordpar-pair[^ ]*>span[^ ]* .*\.ordbok-x(word|peek)")

    def test_every_reaching_rule_is_scoped(self):
        reaching = [s for s in _selectors(self.css) if self.REACH.search(s)]
        self.assertGreaterEqual(len(reaching), 18)
        for s in reaching:
            self.assertTrue(s.endswith(NM), s)

    def test_the_84_rules(self):
        E = "html:not(.ordpar-ety-no):not(.ordpar-ety-both) .ordbok-inline>.ordpar-pair>span[lang=en]"
        self.assertIn(E + " .ordpar-xen>.ordbok-xword" + NM + ",", self.css)
        self.assertIn(E + " .ordpar-xen:hover>.ordbok-xpeek" + NM + ",", self.css)

    def test_the_mini_rules_unscoped(self):
        # a mini's own rules are the ones meant to decide inside it
        for s in _selectors(self.css):
            if ".mini-pair" in s and ".ordpar-pair" not in s:
                self.assertNotIn("ordbok-xmini *", s, s)

    def test_shipped(self):
        self.assertIn(NM, page.shipped(page.CSS_ALL_HREF))


if __name__ == "__main__":
    unittest.main()
