"""Site-review decisions 126 (Robin, 2026-10-25): the settings' words, self-contained and saying
exactly what each setting does.

Robin approved the rewordings of `docs/sessions/2026-09-19-ordpar-site-review/walk-through/
proposal-settings-words-126-2026-10-25.md` ("I skimmed over the rest, and it seems ok"), with the line
under *Small articles* shortened. Pins:

* **The words** — every new or changed heading, choice, note and "?" text, exactly as the proposal's
  Proposed column (its `<span>` marks dropped), read from `site/strings/en.json`; the keys that are
  new exist (the line under the heading, three choice notes, five "?" texts).
* **The line under a subsection's heading** — `settings.js` `intro`, run under `bun` (or node) on a
  small DOM stand-in: a subsection whose strings have `settings.sub.<sub>.intro` gets a
  `p.ordpar-note.ordpar-settings-intro` right under its `h3`, and becomes a `role="group"` named by the
  heading and described by the line; a subsection without one is left alone. The sheet gives the line
  no rule above the first setting after it.
* **The accent colour's "?"** — drawn through the generic `settings.<key>.hint`, the button named
  "About this setting: Accent colour".

`ORDPAR_TEST_SITE` names another copy of `ordpar/site/` (to show the test failing on the version before
the change: `git archive <rev> ordpar/site`). The page in a browser:
`test_ordpar_browser_settingswords126.py`.
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
SITE = os.environ.get("ORDPAR_TEST_SITE") or os.path.join(ROOT, "ordpar", "site")

from ordpar.sitegen import colours  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


STRINGS = json.loads(_read(SITE, "strings", "en.json"))

#: Every new or changed text of 126, word for word from the proposal's Proposed column
WORDS = {
    # its last sentence, "A link inside the box opens that article's own page.", dropped with the
    # nested small articles (Robin, 2026-10-27, decisions 139)
    "settings.sub.mini.intro": "The box that opens on the page when you click a word linked to another article. It shows the word's senses only; click its headword for the whole article.",
    "settings.mini.article.note": "With Definitions set to \"Norwegian, with the English hidden\", a small article still shows its definitions in both languages, with nothing to click. Its examples, formula lines and etymology follow their own settings.",
    "settings.mini.en.note": "An article not yet translated is shown in Norwegian.",
    "settings.minicontent": "How much of the article it shows",
    "settings.minicontent.hint": "In both, each sense and subsense it shows that has examples gets its first one; more are then added one at a time, in turn, until there are 6 in all. With more than 6 senses and subsenses that have examples, each gets one.",
    "settings.minicontent.full": "In full: every subsense and compound list, and a few examples",
    "settings.minicontent.slim": "Shorter: some subsenses and compound lists left out",
    "settings.minicontent.slim.note": "Compound lists are left out wherever the sense or subsense has examples. And when the small article shows a whole word with several senses, a sense with its own definition is shown without its subsenses; a small article showing a single sense keeps them. To see everything, click the small article's headword: it opens the whole article.",
    "settings.miniscroll": "A long one, on a computer",
    "settings.miniscroll.off": "Shown at its full length",
    "settings.defs.en.note": "Shows only the English of each definition: the shortest articles, for when you only need the meaning. Set phrases not yet translated are left out. An article not yet translated still shows its Norwegian.",
    "settings.defs.no.note": "For when you mostly follow the Norwegian: each definition's English stays hidden until you click \"Show English\" under it; click the English again to hide it. The English glosses under the headword still show, and formula lines and the etymology follow their own settings.",
    "settings.examples.no.note": "For practising your Norwegian: read the example first, then click \"Show English\" under it to check yourself.",
    "settings.exlimit": "Examples under each sense and set phrase",
    "settings.exlimit.hint": "Fewer examples make a long article quicker to skim. Each sense, subsense and set phrase shows its first examples, in the article's order, including the examples Ordpar has added (marked +). Small articles keep their own limit. With a number chosen, the next setting decides whether the rest can still be opened.",
    "settings.exmore": "A line to show the examples left out",
    "settings.exmore.hint": "On: where the setting above leaves examples out, a line such as \"Show 12 more examples\" at the end of those examples opens them in place. Off: they are not shown.",
    "settings.emph.hint": "Which line of a definition is in the full text colour; the other is faded, and its links are plain words. Not used when Definitions is \"Norwegian, with the English hidden\": there the Norwegian always leads.",
    "settings.emph.en.note": "In the example sentences, the Norwegian stays emphasized.",
    "settings.subsenses.en.note": "The subsenses marked with a bullet show only their English, so a long article is quicker to scan. Only when Definitions is \"Norwegian and English\"; short formula lines such as \"used as an adverb:\" have their own setting, below.",
    "settings.formulas.hint": "On an article not yet translated, they are always in Norwegian.",
    "settings.infl": "Inflection tables",
    "settings.infl.open.note": "The tables of a word's forms (hus, huset, husene …) show without clicking the Inflection button. Handy when you are learning the forms; the articles get longer.",
    "settings.pframes.hint": "Grey helper words in a verb's inflection table that show how its perfect participle is used before a noun: \"+ noun\" after each form, and \"den/det\" before the definite form. Not shown in the narrower table used where the full one does not fit, as on a phone.",
    "settings.xref": "What a click on a linked word opens",
    # site decisions 185 (Robin, 2026-11-12) retitled it for its three choices
    "settings.peek": "When the pointer rests on a linked word",
    "settings.listview.hint": "The list view shows each article the search finds as one short row (its headword, word class, whether it is translated, and its English glosses, or its Norwegian definition if not yet translated), which opens in place when clicked. Off: the articles the search finds as headwords are shown whole, one under another. Words found as an inflected form (such as huset, a form of hus) are always listed as links.",
    "settings.listview.multi.note": "Counts the articles found as headwords; words found as an inflected form don't count.",
    "settings.suggestrows": "Spacing of the suggestions under the search box",
    "settings.minifetch.hint": "Loading an article, page or search before you open it makes it open faster, but uses data for the ones you never open. With the offline copy downloaded (Offline, below), articles come from the copy, so no data is used either way.",
    "settings.minifetch.point.note": "Articles, pages and searches open almost at once on a computer, Random word and the suggestions under the search box included. Uses a little extra data for the ones you rest on but don't click. On a touch screen, loading starts when you touch one.",
    "settings.minifetch.page.note": "The fastest on a phone, which has no pointer to rest on. Uses the most data: the articles behind the page's links that open a small article, and the articles in a list view, are loaded with the page, whether you open them or not. Everything else loads as under \"When the pointer rests on its link\". With the browser's data saver on, only when the link is clicked.",
    "settings.layout.ordbokene.note": "Familiar if you use ordbokene.no: each numbered sense's own examples get an \"Example\" heading and line up with the definition above them, and no example list has the grey bar at its left.",
    "settings.colour": "Accent colour",
    "settings.colour.hint": "The colour of links, headings, buttons and the sense numbers.",
}

#: The keys 126 adds (the proposal's rows marked "(new)")
NEW = ["settings.sub.mini.intro", "settings.mini.article.note", "settings.mini.en.note", "settings.minicontent.hint", "settings.emph.hint", "settings.formulas.hint", "settings.listview.hint", "settings.listview.multi.note", "settings.colour.hint"]


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


#: A DOM just big enough for `settings.js` `intro` and `field`, with the real strings, settings table
#: and colour schemes; prints one JSON line
HARNESS = r"""
function Node(tag) { this.tagName = tag; this.children = []; this.attrs = {}; this.style = {}; this.className = '';
  this.id = ''; this.hidden = false; this._text = ''; }
Node.prototype.appendChild = function (c) { this.children.push(c); c.parentNode = this; return c; };
Node.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
Node.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
Node.prototype.addEventListener = function () {};
Object.defineProperty(Node.prototype, 'textContent', {
  get: function () { return this._text + this.children.map(function (c) { return c.textContent; }).join(''); },
  set: function (v) { this._text = String(v); this.children = []; } });
function Text(t) { this.textContent = t; }
globalThis.document = { readyState: 'complete', createElement: function (t) { return new Node(t); },
  createTextNode: function (t) { return new Text(t); }, querySelector: function () { return null; },
  addEventListener: function () {} };
var STR = __STRINGS__;
var LANGS = ['en'];
var SETTINGS = __SETTINGS__;
globalThis.ordparShell = { SETTINGS: SETTINGS, t: function (k) { return k in STR ? STR[k] : k; },
  getSetting: function () { return null; }, colours: function () { return __COLOURS__; }, ready: null };
__SETTINGS_JS__
var S = globalThis.ordparSettings;
function sub(name) {
  var box = document.createElement('div'); box.className = 'ordpar-settings-sub';
  var h3 = document.createElement('h3'); h3.id = 'article-' + name + '-title'; box.appendChild(h3);
  var p = S.intro ? S.intro(box, h3, name) : null;
  return { n: box.children.length, second: box.children[1] ? { tag: box.children[1].tagName,
    cls: box.children[1].className, id: box.children[1].id, text: box.children[1].textContent } : null,
    role: box.getAttribute('role'), labelledby: box.getAttribute('aria-labelledby'),
    describedby: box.getAttribute('aria-describedby') };
}
var colour = SETTINGS.filter(function (sp) { return sp.key === 'colour'; })[0];
var f = S.field(colour, null);
var button = null;
(function walk(n) { if (n.tagName === 'button') { button = n; } (n.children || []).forEach(walk); })(f);
console.log(JSON.stringify({ mini: sub('mini'), language: sub('language'),
  colourHint: S.hintOf(colour), colourButton: button && button.getAttribute('aria-label') }));
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
    def test_a_every_text_as_approved(self):
        wrong = [k for k, v in WORDS.items() if STRINGS.get(k) != v]
        self.assertEqual(wrong, [], "texts not as the 126 proposal words them")

    def test_b_the_new_keys_exist(self):
        self.assertEqual([k for k in NEW if k not in STRINGS], [])
        self.assertEqual(len(NEW), 9)
        self.assertEqual(len(WORDS), 35)

    def test_c_the_quotes_as_the_settings_write_them(self):
        # straight quotes, as every other settings string; the one ellipsis spaced, as "Loading …"
        for k, v in WORDS.items():
            self.assertNotRegex(v, "[\u201c\u201d\u2018\u2019]", k)
        self.assertIn("husene \u2026)", WORDS["settings.infl.open.note"])


@unittest.skipUnless(_runner(), "neither bun nor node on PATH")
class TheLineUnderTheHeading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = _harness()

    def test_d_small_articles_gets_its_line(self):
        m = self.r["mini"]
        self.assertEqual(m["n"], 2)
        self.assertEqual(m["second"], {"tag": "p", "cls": "ordpar-note ordpar-settings-intro",
                                       "id": "article-mini-intro", "text": WORDS["settings.sub.mini.intro"]})
        self.assertEqual((m["role"], m["labelledby"], m["describedby"]),
                         ("group", "article-mini-title", "article-mini-intro"))

    def test_e_a_subsection_without_one_is_left_alone(self):
        self.assertEqual(self.r["language"], {"n": 1, "second": None, "role": None,
                                              "labelledby": None, "describedby": None})

    def test_f_the_accent_colours_question_mark(self):
        self.assertEqual(self.r["colourHint"]["hint"], WORDS["settings.colour.hint"])
        self.assertEqual(self.r["colourButton"], "About this setting: Accent colour")


class TheSheet(unittest.TestCase):
    def test_g_the_line_in_the_pages_note_style(self):
        css = _read(SITE, "shell.css")
        self.assertIn(".ordpar-settings-intro { margin: 0 0 0.5rem; }", css)
        self.assertIn(".ordpar-settings-intro + .ordpar-field { border-top: 0; padding-top: 0; }", css)
        js = _read(SITE, "settings.js")
        self.assertIn("intro(box, h3, sub);", js)


if __name__ == "__main__":
    unittest.main()
