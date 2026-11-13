"""Site-review decisions 99 (Robin, 2026-10-23): the settings page's hints behind one "?" per
setting.

Pins:

* **The words** — the setting-level hints (`settings.<key>.hint`: Loading's trade-off and what
  "Context for participle forms" shows, under 25 words), the choice notes as Robin passed them
  ("They seem fine"), the button's name, and the old notes that keep their words.
* **One "?" per setting with something to say** — `settings.js` `hintOf`, run under `bun` (or
  node) over the real settings table (`shell.js` SETTINGS), the strings and the colour schemes:
  exactly the twelve settings that have a hint or a choice note, and none for the rest.
* **The button** — `field()` on a small DOM stand-in: a real `<button type="button">` "?" in the
  legend with `aria-label` "About this setting: <subsection>, <title>", `aria-expanded="false"`,
  `aria-controls` naming the always-present `role="status"` region that holds the box once open;
  the fieldset named by the title's own span (not the legend, which holds the "?"); each radio
  with a note described by a HIDDEN copy of its line; no grey line under a choice any more.
* **The sheet** — the overlay's rules (`shell.css`): the fieldset the containing block, the box
  absolute and never wider than the fieldset.

The behaviour in a browser (hover, click, tap, Esc, keyboard, the 360 px window) was checked in
headless Edge: `docs/sessions/2026-09-19-ordpar-site-review/evidence/settings-hints-99-2026-10-23/`.

`settings.minifetch.click.note` since site decisions 170 (Robin, 2026-11-06, "Approve all four"):
"…nothing is loaded before you click, a recording included. …" (the sound icon follows the setting).
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
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")

from ordpar.sitegen import colours  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


STRINGS = json.loads(_read(SITE, "strings", "en.json"))

#: The words Robin passed (decisions 99, "They seem fine"), exactly; reworded by decisions 126 (2026-10-25,
#: `test_ordpar_settingswords126.py` pins every 126 text), so the values here are 126's
HINTS = {
    "settings.minifetch.hint": "Loading an article, page or search before you open it makes it open faster, but uses data for the ones you never open. With the offline copy downloaded (Offline, below), articles come from the copy, so no data is used either way.",
    "settings.minifetch.point.note": "Articles, pages and searches open almost at once on a computer, Random word and the suggestions under the search box included. Uses a little extra data for the ones you rest on but don't click. On a touch screen, loading starts when you touch one.",
    "settings.minifetch.click.note": "Uses the least data: nothing is loaded before you click, a recording included. An article can take a moment to open the first time.",  # site decisions 170, Robin 2026-11-06 ("Approve all four")
    "settings.minifetch.page.note": "The fastest on a phone, which has no pointer to rest on. Uses the most data: the articles behind the page's links that open a small article, and the articles in a list view, are loaded with the page, whether you open them or not. Everything else loads as under \"When the pointer rests on its link\". With the browser's data saver on, only when the link is clicked.",
    "settings.defs.en.note": "Shows only the English of each definition: the shortest articles, for when you only need the meaning. Set phrases not yet translated are left out. An article not yet translated still shows its Norwegian.",
    "settings.defs.no.note": "For when you mostly follow the Norwegian: each definition's English stays hidden until you click \"Show English\" under it; click the English again to hide it. The English glosses under the headword still show, and formula lines and the etymology follow their own settings.",
    "settings.subsenses.en.note": "The subsenses marked with a bullet show only their English, so a long article is quicker to scan. Only when Definitions is \"Norwegian and English\"; short formula lines such as \"used as an adverb:\" have their own setting, below.",
    "settings.layout.ordbokene.note": "Familiar if you use ordbokene.no: each numbered sense's own examples get an \"Example\" heading and line up with the definition above them, and no example list has the grey bar at its left.",
    "settings.infl.open.note": "The tables of a word's forms (hus, huset, husene …) show without clicking the Inflection button. Handy when you are learning the forms; the articles get longer.",
    "settings.peek.off.note": "Fewer pop-ups while you read. A click still opens the link.",
    "settings.minicontent.slim.note": "Compound lists are left out wherever the sense or subsense has examples. And when the small article shows a whole word with several senses, a sense with its own definition is shown without its subsenses; a small article showing a single sense keeps them. To see everything, click the small article's headword: it opens the whole article.",
}
#: The notes that keep their words and move into their setting's box (emph.en's reworded by 126)
KEPT = {
    "settings.emph.en.note": "In the example sentences, the Norwegian stays emphasized.",
    "settings.formulas.no.note": "The labels of compound lists and the words in a pronunciation, such as \"in the plural\", are in Norwegian too.",
    "settings.formulas.both.note": "The labels of compound lists and the words in a pronunciation stay in English.",
    "settings.minihw.article.note": "It is still a link: click it to open the whole article.",
}
#: The settings with something to say (the colour's from ordbokene's maroon, `colours.py`)
WITH_HINT = ["colour", "layout", "defs", "examples", "exeye", "exlimit", "exmore", "emph", "subsenses", "formulas", "infl", "pframes", "peek",
             "mini", "minicontent", "nestminis", "minitext", "minihw", "listview", "minifetch", "stats",
             "labels", "nbonly", "nbequiv", "nbrows", "nbicon",   # site decisions 152
             "audiospeed"]   # site decisions 159   # minitext: decisions 114; mini, listview: 126; exeye: 131; nestminis: 139 (nestlimit, 139, went in 147)


def _runner():
    return shutil.which("bun") or shutil.which("node")


def _run(js):
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "t.js")
        with open(script, "w", encoding="utf-8") as f:
            f.write(js)
        res = subprocess.run([_runner(), script], capture_output=True, timeout=60)
    out = res.stdout.decode("utf-8", "replace")
    if res.returncode != 0:
        raise AssertionError("JS failed: %s\n%s" % (res.stderr.decode("utf-8", "replace"), out))
    return json.loads(out.strip().splitlines()[-1])


#: A DOM just big enough for `settings.js` `field()`, the real settings table (`shell.js`), the
#: strings and the colour schemes; prints what the tests ask for as one JSON line
HARNESS = r"""
function Node(tag) { this.tagName = tag; this.children = []; this.attrs = {}; this.style = {};
  this.className = ''; this.id = ''; this.hidden = false; this._text = ''; this.listeners = {}; }
Node.prototype.appendChild = function (c) { this.children.push(c); c.parentNode = this; return c; };
Node.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
Node.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
Node.prototype.addEventListener = function (k, f) { (this.listeners[k] = this.listeners[k] || []).push(f); };
Object.defineProperty(Node.prototype, 'textContent', {
  get: function () { return this._text + this.children.map(function (c) { return c.textContent; }).join(''); },
  set: function (v) { this._text = String(v); this.children = []; } });
function Text(t) { this.textContent = t; }
var all = function (n, f, out) { out = out || []; if (f(n)) out.push(n); (n.children || []).forEach(function (c) { all(c, f, out); }); return out; };
globalThis.document = { readyState: 'complete', createElement: function (t) { return new Node(t); },
  createTextNode: function (t) { return new Text(t); }, querySelector: function () { return null; },
  addEventListener: function () {} };
var STR = __STRINGS__;
var LANGS = ['en'];
var SETTINGS = __SETTINGS__;
globalThis.ordparShell = { SETTINGS: SETTINGS, t: function (k) { return k in STR ? STR[k] : k; },
  getSetting: function (k) { return null; }, colours: function () { return __COLOURS__; }, ready: null };
__SETTINGS_JS__
var S = globalThis.ordparSettings;
var res = { hints: {}, fields: {} };
SETTINGS.forEach(function (sp) {
  var h = S.hintOf(sp);
  if (h) { res.hints[sp.key] = h; }
  var sub = sp.sub ? sp.section + '-' + sp.sub + '-title' : null;
  var f = S.field(sp, sub);
  var legend = f.children[0];
  var buttons = all(f, function (n) { return n.tagName === 'button'; });
  var notes = all(f, function (n) { return n.className === 'ordpar-choice-note'; });
  var radios = all(f, function (n) { return n.tagName === 'input'; });
  var live = all(f, function (n) { return n.className === 'ordpar-hint-live'; });
  res.fields[sp.key] = {
    labelledby: f.getAttribute('aria-labelledby'),
    title: { tag: legend.children[0].tagName, id: legend.children[0].id, text: legend.children[0].textContent },
    buttons: buttons.map(function (b) { return { type: b.type, text: b.textContent, inLegend: all(legend, function (n) { return n === b; }).length === 1,
      label: b.getAttribute('aria-label'), expanded: b.getAttribute('aria-expanded'), controls: b.getAttribute('aria-controls'),
      title: b.getAttribute('title') }; }),
    live: live.map(function (l) { return { id: l.id, role: l.getAttribute('role'), text: l.textContent }; }),
    notes: notes.map(function (n) { return { id: n.id, hidden: n.hidden, text: n.textContent }; }),
    described: radios.filter(function (r) { return r.getAttribute('aria-describedby'); }).map(function (r) { return [r.id, r.getAttribute('aria-describedby')]; })
  };
});
console.log(JSON.stringify(res));
"""


def _harness():
    shell = _read(SITE, "shell.js")
    table = re.search(r"var SETTINGS = (\[.*?\n  \]);", shell, re.S).group(1)
    js = (HARNESS.replace("__STRINGS__", json.dumps(STRINGS, ensure_ascii=False))
          .replace("__SETTINGS__", table)
          .replace("__COLOURS__", colours.settings_json())
          .replace("__SETTINGS_JS__", _read(SITE, "settings.js")))
    return _run(js)


class TheWords(unittest.TestCase):
    def test_a_the_hints_as_passed(self):
        for k, v in HINTS.items():
            self.assertEqual(STRINGS[k], v, k)

    def test_b_the_old_notes_keep_their_words(self):
        for k, v in KEPT.items():
            self.assertEqual(STRINGS[k], v, k)
        maroon = [c for c in json.loads(colours.settings_json()) if c.get("note")]
        self.assertEqual(len(maroon), 1)
        self.assertEqual(maroon[0]["note"], "The colour ordbokene.no uses. Ordpar is independent of ordbokene.no.")

    def test_c_the_participle_line(self):
        line = STRINGS["settings.pframes.hint"]
        # reworded by decisions 126 (2026-10-25): what the words are and where they are not shown
        self.assertEqual(line, "Grey helper words in a verb's inflection table that show how its perfect participle "
                               "is used before a noun: \"+ noun\" after each form, and \"den/det\" before the "
                               "definite form. Not shown in the narrower table used where the full one does not "
                               "fit, as on a phone.")
        # the narrow tables carry no frames (decisions 44), so the setting changes nothing there

    def test_d_the_button_name(self):
        self.assertEqual(STRINGS["settings.hintButton"], "About this setting: {title}")

    def test_e_hints_only_where_ruled(self):
        # a setting-level hint for Loading and the participle context; since 2026-10-24 the examples
        # limit and its line (decisions 112) and the opt-out (decisions 104); since 2026-10-25 the
        # accent colour, emphasis, formula lines, list view and the small article's content (126);
        # since 2026-10-26 the eye's line (decisions 131)
        self.assertEqual(sorted(k for k in STRINGS if re.match(r"settings\.\w+\.hint$", k)),
                         ["settings.audiospeed.hint",   # site decisions 159
                          "settings.colour.hint", "settings.emph.hint", "settings.exeye.hint",
                          "settings.exlimit.hint",
                          "settings.exmore.hint", "settings.formulas.hint",
                          "settings.labels.hint",        # site decisions 152
                          "settings.listview.hint",
                          "settings.minicontent.hint", "settings.minifetch.hint",
                          "settings.nbicon.hint", "settings.nbonly.hint",   # site decisions 152
                          "settings.nestminis.hint",     # decisions 139, 147 (nestlimit's hint went)
                          "settings.pframes.hint", "settings.stats.hint"])


@unittest.skipUnless(_runner(), "neither bun nor node on PATH")
class TheQuestionMark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = _harness()

    def test_f_one_per_setting_with_something_to_say(self):
        self.assertEqual(sorted(self.r["hints"]), sorted(WITH_HINT))
        for key, f in self.r["fields"].items():
            self.assertEqual(len(f["buttons"]), 1 if key in WITH_HINT else 0, key)
            self.assertEqual(len(f["live"]), 1 if key in WITH_HINT else 0, key)

    def test_g_the_box_holds_the_hint_then_the_choices_lines(self):
        h = self.r["hints"]["minifetch"]
        self.assertEqual(h["hint"], HINTS["settings.minifetch.hint"])
        self.assertEqual([(x["label"], x["text"]) for x in h["lines"]], [
            ("When the pointer rests on its link", HINTS["settings.minifetch.point.note"]),
            ("When its link is clicked", HINTS["settings.minifetch.click.note"]),
            ("With the page", HINTS["settings.minifetch.page.note"])])
        self.assertEqual(self.r["hints"]["pframes"], {"hint": STRINGS["settings.pframes.hint"], "lines": []})
        self.assertEqual(self.r["hints"]["colour"]["lines"][0]["label"], "ordbokene.no's maroon")

    def test_h_the_button(self):
        f = self.r["fields"]["minifetch"]
        b = f["buttons"][0]
        self.assertEqual(b["type"], "button")
        self.assertEqual(b["text"], "?")
        self.assertTrue(b["inLegend"])
        self.assertIsNone(b["title"])                       # not a title attribute
        self.assertEqual(b["label"], "About this setting: Loading, When a linked article or page is loaded")
        self.assertEqual(b["expanded"], "false")
        self.assertEqual(b["controls"], "ordpar-minifetch-hint")
        self.assertEqual(f["live"], [{"id": "ordpar-minifetch-hint", "role": "status", "text": ""}])  # empty until opened
        # a setting under no subsection: its title alone
        self.assertEqual(self.r["fields"]["layout"]["buttons"][0]["label"], "About this setting: Article layout")

    def test_i_the_fieldset_named_by_its_title_not_the_legend(self):
        f = self.r["fields"]["minifetch"]
        self.assertEqual(f["title"], {"tag": "span", "id": "ordpar-minifetch-legend",
                                      "text": "When a linked article or page is loaded"})
        self.assertEqual(f["labelledby"], "data-loading-title ordpar-minifetch-legend")
        self.assertEqual(self.r["fields"]["theme"]["labelledby"], "ordpar-theme-legend")

    def test_j_each_radio_keeps_its_line_as_its_description(self):
        f = self.r["fields"]["minifetch"]
        self.assertEqual(f["described"], [["ordpar-minifetch-point", "ordpar-minifetch-point-note"],
                                          ["ordpar-minifetch-click", "ordpar-minifetch-click-note"],
                                          ["ordpar-minifetch-page", "ordpar-minifetch-page-note"]])
        for n in f["notes"]:
            self.assertTrue(n["hidden"], n)                  # no grey line under a choice any more
        n = sum(len(f["notes"]) for f in self.r["fields"].values())
        self.assertEqual(n, 24)                              # 152: nbequiv's two, nbrows.none's; the nine old lines, six new ones, examples.no's (111), minitext.smaller's (114), mini.article's, mini.en's, listview.multi's (126); listview.forms's (site decisions 158)
        self.assertEqual(self.r["fields"]["pframes"]["notes"], [])


class TheSheet(unittest.TestCase):
    def test_k_an_overlay_inside_the_fieldset(self):
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-field { position: relative; }", css)
        box = re.search(r"\.ordpar-hint-box \{(.*?)\}", css, re.S).group(1)
        self.assertIn("position: absolute;", box)
        self.assertIn("max-width: min(26rem, 100%);", box)
        self.assertNotIn(".ordpar-choice-note {", css)       # the grey line's rule is gone
        js = _read(SITE, "settings.js")
        self.assertIn("doc.addEventListener('pointerdown', function (e) {", js)
        self.assertIn("if (e.pointerType !== 'mouse') { return; }", js)
        self.assertIn("e.key === 'Escape'", js)


if __name__ == "__main__":
    unittest.main()
