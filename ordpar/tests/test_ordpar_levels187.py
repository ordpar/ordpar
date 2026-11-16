"""Site decisions 187 (2026-11-15): the CEFR level box, the static half and the rendered pages.

* **The levels file** (`ordpar/levels.tsv`, `sitegen/levels.py` `read`): a comment line naming its
  source and decisions 187, the header `article<TAB>shown`, one line per article id, sorted by id,
  LF line ends, every level one of A1, A2, B1, B2, C; `read` refuses a level outside them, an id
  twice, a line not of two columns and a file without the header. Where the merged source is here
  (the private repository), the committed file is exactly what the import tool writes from it.
* **The import tool** (`ordpar/levels_import.py`): from a source of the merged file's columns it
  writes the two columns, sorted, LF; it refuses a level outside the five and an id twice, and writes
  nothing then; with its default source missing (the public repository) it says so plainly, names
  the committed file, and writes nothing.
* **The box** (`levels.box_html`): the lab's markup with the site's classes, the visible letters
  `aria-hidden` with the tooltip on them, ", level B1" in an `sr-only` span, `lang="en"`,
  `data-nosnippet`; the five tooltips in the strings; none for no level.
* **The renderer**: `head_html` puts the box last in the `h1` (after the last spelling, its
  numeral and its reading), on the first headword line only; `fragment` puts each embedded set
  phrase's box last in its term, each looked up by its own id, an untranslated one's too; with no
  levels (the deck's call) the markup carries no box and is the same as without the parameter.
* **The setting** `levels` = off | on, default off, in the Article section's Language subsection
  right after the eye's two settings; its words; stored, exported, read from the address and reset
  like the rest (`CLASS_KEYS`, `personal.js`, `head.settings_table`); the head script's and the
  shell's class `ordpar-levels-on`; its "?" with a link to Help's section `#cefr-levels`.
* **The presets**: For learners names `levels` on; no other preset names it, so each gives the
  default, off; For learners' "?" line names the box.
* **The sheet**: the box hidden unless `html.ordpar-levels-on`; the Quiet box's values (0.75 rem,
  weight 600, padding .2em .38em, a 1 px outline in `currentColor`, radius 3 px, .55em before it,
  the muted grey); lower on a set phrase's line.
* **The sound icons**: the build's reading of a set phrase's term leaves the box out (`audio.py`
  `visible`), so a term with a box still gets its mark; the page script's (`audio.js` `HIDE`) too, and
  puts the term's icon before the box.
* **Small articles**: `mini.js` `finish` removes every box.
* **Help**: a section "CEFR levels" (id `cefr-levels`), a line for each of A1, A2, B1, B2 and C.
* **Rendered pages** (through `build_site.Builder` on the real mirror; skipped without it): *hus*
  (24627) with its level after the headword and every set phrase's own on its line; *bein, ben*
  (5026) the box after the second spelling; *uteområde* (128786, no definition) and *omkjøring*
  (42134, Norwegian only) with theirs; each as `ordpar/levels.tsv` says; the build's counts; the
  same pages built without levels carry no box.

`ORDPAR_TEST_ROOT` names another copy of the repository (`git archive HEAD ordpar` unpacked over a
checkout) to show it failing on the version before the change. Stdlib unittest.
"""
import io
import json
import os
import re
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("ORDPAR_TEST_ROOT") or REPO
sys.path.insert(0, ROOT)

from ordpar.sitegen import article, face as face_mod, head, page  # noqa: E402
from ordpar.sitegen.strings import EN  # noqa: E402

try:
    from ordpar.sitegen import levels  # noqa: E402
except ImportError:          # the version before decisions 187
    levels = None

ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
SOURCE = os.path.join(REPO, "docs", "sessions", "2026-10-24-deck-release", "evidence", "tags",
                      "cefr-levels.tsv")

TIPS = {"A1": "A1 · beginner", "A2": "A2 · elementary", "B1": "B1 · intermediate",
        "B2": "B2 · upper intermediate", "C": "C · advanced (C1 and C2)"}
WORDS = {"settings.levels": "CEFR level after the headword", "settings.levels.off": "Off",
         "settings.levels.on": "On", "settings.levels.helpLink": "More about the levels in Help"}


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def _strings():
    return json.loads(_read(SITE, "strings", "en.json"))


def box(level):
    return ('<span class="ordpar-level" data-level="%s" lang="en" data-nosnippet>'
            '<span class="ordpar-level-txt" aria-hidden="true" title="%s">%s</span>'
            '<span class="sr-only" data-nosnippet>, level %s</span></span>' % (level, TIPS[level], level, level))


class TheFile(unittest.TestCase):

    def setUp(self):
        self.assertIsNotNone(levels, "no ordpar/sitegen/levels.py")

    def test_a_its_shape(self):
        raw = open(os.path.join(ORDPAR, "levels.tsv"), "rb").read()
        self.assertNotIn(b"\r", raw)
        lines = raw.decode("utf-8").split("\n")
        self.assertEqual(lines[-1], "")
        self.assertTrue(lines[0].startswith("# ") and "decisions 187" in lines[0], lines[0])
        self.assertEqual(lines[1], "article\tshown")
        ids = [int(l.split("\t")[0]) for l in lines[2:-1]]
        self.assertEqual(ids, sorted(set(ids)))
        self.assertEqual({l.split("\t")[1] for l in lines[2:-1]}, {"A1", "A2", "B1", "B2", "C"})
        got = levels.read(os.path.join(ORDPAR, "levels.tsv"))
        self.assertEqual(len(got), len(ids))
        self.assertGreater(len(got), 90000)

    def test_b_read_refuses(self):
        d = tempfile.mkdtemp(prefix="ordpar-levels187-")
        for name, body in (("bad", "article\tshown\n1\tC1\n"), ("twice", "article\tshown\n1\tA1\n1\tB1\n"),
                           ("cols", "article\tshown\n1\tA1\tx\n"), ("nohead", "1\tA1\n")):
            p = os.path.join(d, name + ".tsv")
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
            with self.assertRaises(levels.Refused, msg=name):
                levels.read(p)

    @unittest.skipUnless(os.path.exists(SOURCE), "the merged levels file is not in this checkout")
    def test_c_the_committed_file_is_the_import(self):
        import importlib
        imp = importlib.import_module("ordpar.levels_import")
        rows = imp.read_source(SOURCE)
        self.assertEqual(imp.text(rows, imp.SOURCE), _read(ORDPAR, "levels.tsv"))


class TheImportTool(unittest.TestCase):

    def setUp(self):
        import importlib
        try:
            self.imp = importlib.import_module("ordpar.levels_import")
        except ImportError:
            self.fail("no ordpar/levels_import.py")
        self.d = tempfile.mkdtemp(prefix="ordpar-levels187-")

    def src(self, rows):
        p = os.path.join(self.d, "src.tsv")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("article\tlemma\tlevel\tshown\tkind\tconfidence\ttext\tsource\n")
            for r in rows:
                f.write("\t".join(r) + "\n")
        return p

    def test_a_writes_two_columns_sorted(self):
        p = self.src([("30", "c", "C2", "C", "article", "low", "none", "x.tsv"),
                      ("4", "a", "A1", "A1", "article", "high", "", "x.tsv"),
                      ("12", "b", "B2", "B2", "phrase", "medium", "", "x.tsv")])
        out = os.path.join(self.d, "levels.tsv")
        with io.StringIO() as buf:
            sys.stdout, old = buf, sys.stdout
            try:
                self.imp.main([p, "--out", out])
            finally:
                sys.stdout = old
        raw = open(out, "rb").read()
        self.assertNotIn(b"\r", raw)
        lines = raw.decode("utf-8").split("\n")
        self.assertIn("decisions 187", lines[0])
        self.assertEqual(lines[1:], ["article\tshown", "4\tA1", "12\tB2", "30\tC", ""])

    def test_b_refuses_and_writes_nothing(self):
        out = os.path.join(self.d, "levels.tsv")
        for rows in ([("1", "a", "C1", "C1", "article", "high", "", "x")],
                     [("1", "a", "A1", "A1", "article", "high", "", "x"),
                      ("1", "a", "B1", "B1", "article", "high", "", "x")]):
            with self.assertRaises(SystemExit) as cm:
                self.imp.main([self.src(rows), "--out", out])
            self.assertIn("REFUSED", str(cm.exception.code))
            self.assertFalse(os.path.exists(out))

    def test_c_no_source_in_the_public_repository(self):
        out = os.path.join(self.d, "levels.tsv")
        saved = self.imp.SOURCE
        self.imp.SOURCE = "docs/no/such/cefr-levels.tsv"
        try:
            with self.assertRaises(SystemExit) as cm:
                self.imp.main(["--out", out])
        finally:
            self.imp.SOURCE = saved
        msg = str(cm.exception.code)
        self.assertIn("private repository", msg)
        self.assertIn("ordpar/levels.tsv", msg)
        self.assertIn("Nothing written", msg)
        self.assertFalse(os.path.exists(out))


class TheBox(unittest.TestCase):

    def setUp(self):
        self.assertIsNotNone(levels, "no ordpar/sitegen/levels.py")

    def test_a_the_markup(self):
        for lv in TIPS:
            self.assertEqual(levels.box_html(lv, EN), box(lv))
        self.assertEqual(levels.box_html(None, EN), "")

    def test_b_the_tooltips_are_the_strings(self):
        for lv, tip in TIPS.items():
            self.assertEqual(EN["level_tip_" + lv.lower()], tip)
        self.assertEqual(EN["level"], "level {level}")


ROW = {"id": 7, "lemmas": [{"form": "bein", "homograph": None}, {"form": "ben", "homograph": "II"}],
       "pos_en": "noun"}
DATA = {"lemmas": [{"lemma": "bein", "hgno": 0, "paradigm_info": [{"tags": ["NOUN", "Neuter"]}]},
                   {"lemma": "ben", "hgno": 2, "paradigm_info": [{"tags": ["NOUN", "Neuter"]}]},
                   {"lemma": "beinet", "hgno": 0, "paradigm_info": [{"tags": ["VERB"]}]}]}


class TheHeadword(unittest.TestCase):

    def test_a_last_in_the_heading(self):
        out = article.head_html(ROW, EN, DATA, level="B1")
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", out).group(1)
        self.assertTrue(h1.endswith(box("B1")), h1)
        self.assertLess(h1.index("homograph 2"), h1.index("ordpar-level"))
        self.assertEqual(out.count("ordpar-level\""), 1)              # the first line only
        self.assertNotIn("ordpar-level", re.search(r"<p class=\"ordpar-hw\"[^>]*>(.*?)</p>", out).group(1))

    def test_b_none_no_box(self):
        self.assertEqual(article.head_html(ROW, EN, DATA, level=None), article.head_html(ROW, EN, DATA))
        self.assertNotIn("ordpar-level", article.head_html(ROW, EN, DATA))


EX = {1: {"id": 1, "lemmas": [{"form": "ha det"}], "pos_en": "fixed expression",
          "senses": [{"defn": 3, "no": ["farvel"], "en": ["bye"]}]},
      2: {"id": 2, "lemmas": [{"form": "ha seg"}], "pos_en": "fixed expression",
          "senses": [{"defn": 4, "no": ["vel"], "en": ["well"]}]},
      9: {"id": 9, "lemmas": [{"form": "ha"}], "pos_en": "verb", "exprs": [1, 2],
          "senses": [{"defn": 1, "no": ["eie"], "en": ["to have"]}]}}


class StubStore:
    library = EX
    mirror = {}

    def is_embedded_only(self, aid):
        return False


class TheSetPhrases(unittest.TestCase):

    def setUp(self):
        self.face = face_mod.SiteFace(StubStore())
        self.mk = face_mod.MarkupShim(self.face)
        self.saved = face_mod.install(self.face)
        self.face.set_library(EX)
        self.face.set_page(9)

    def tearDown(self):
        face_mod.restore(self.saved)

    def frag(self, row_en=True, **kw):
        no = self.mk.pair_view(EX[9], "no")
        en = self.mk.pair_view(EX[9], "en") if row_en else None
        return article.fragment(no, en, EX, self.mk, EN, paradigm=False, site=True, **kw)

    def test_a_each_its_own_last_in_its_term(self):
        out = self.frag(levels={9: "A1", 1: "A2", 2: "C"})
        terms = re.findall(r'<span class="ordbok-expr-term" lang="nb">(.*?)</span>\n', out)
        self.assertEqual(terms, ["ha det" + box("A2"), "ha seg" + box("C")])
        self.assertIn(box("A1") + "</h1>", out)

    def test_b_an_untranslated_set_phrase_and_a_norwegian_page(self):
        out = self.frag(levels={1: "B2"}, untranslated_exprs={1})
        self.assertIn("ha det" + box("B2"), out)
        self.assertEqual(out.count('class="ordpar-level"'), 1)     # 9 and 2 have none
        self.assertIn("ha det" + box("B2"), self.frag(row_en=False, levels={1: "B2"}))

    def test_c_no_levels_no_box_the_deck_unchanged(self):
        self.assertNotIn("ordpar-level", self.frag())
        self.assertEqual(self.frag(levels=None), self.frag())
        self.assertNotIn("ordpar-level", self.frag(levels={}))


class TheSetting(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_a_after_the_eye_off_first(self):
        self.assertIn("{ key: 'levels', values: ['off', 'on'], def: 'off', section: 'article', sub: 'language' }",
                      self.js)
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        self.assertEqual(order[order.index("exeyewhat") + 1], "levels")

    def test_b_the_words(self):
        s = _strings()
        for k, v in WORDS.items():
            self.assertEqual(s.get(k), v, k)
        hint = s.get("settings.levels.hint") or ""
        self.assertTrue(hint.startswith("On: "), hint)
        for w in ("CEFR", "A1", "C covers both C1 and C2", "Help page"):
            self.assertIn(w, hint)

    def test_c_stored_exported_reset_and_in_the_address(self):
        self.assertIn("'levels'", re.search(r"var CLASS_KEYS = \[([^\]]*)\]", self.js).group(1))
        self.assertIn("cl.toggle('ordpar-levels-on', getSetting('levels') === 'on');", self.js)
        self.assertIn("'levels'", re.search(r"var SETTING_KEYS = \[([^\]]*)\]",
                                            _read(SITE, "personal.js")).group(1))
        self.assertIn(("levels", ["off", "on"]), head.settings_table())
        self.assertIn("s.getItem('levels')==='on'&&c.add('ordpar-levels-on');", head.THEME_JS)

    def test_d_its_hint_links_to_help(self):
        js = _read(SITE, "settings.js")
        self.assertIn("var HELP_LINKS = { levels: '/help/#cefr-levels' };", js)
        self.assertIn("out.link = { href: HELP_LINKS[sp.key], text: t('settings.' + sp.key + '.helpLink') };", js)


def _presets():
    js = _read(SITE, "settings.js")
    return json.loads(re.search(r"var PRESETS = (\[.*?\n  \]);", js, re.S).group(1))


class ThePresets(unittest.TestCase):

    def test_a_for_learners_turns_it_on(self):
        p = {x["id"]: x["values"] for x in _presets()}
        self.assertEqual(p["learners"].get("levels"), "on")
        for pid in ("default", "english", "concise"):
            self.assertNotIn("levels", p[pid], pid)     # each gives the default, off

    def test_b_its_line_names_the_box(self):
        self.assertIn("CEFR level", _strings()["settings.presets.learners.note"])


class TheSheet(unittest.TestCase):
    css = page.SITE_CSS

    def test_a_hidden_unless_on(self):
        self.assertIn("html.ordpar-levels-on .ordpar-level{display:inline-block}", self.css)
        rule = re.search(r"\n\.ordpar-level\{([^}]*)\}", self.css).group(1)
        self.assertIn("display:none", rule)

    def test_b_the_quiet_box(self):
        rule = re.search(r"\n\.ordpar-level\{([^}]*)\}", self.css).group(1).replace("\n", "").replace(" ", "")
        for decl in ("font-size:.75rem", "font-weight:600", "padding:.2em.38em", "border:1pxsolidcurrentColor",
                     "border-radius:3px", "margin-left:.55em", "vertical-align:.32em",
                     "color:var(--ordpar-muted,#757070)", "user-select:none", "white-space:nowrap"):
            self.assertIn(decl, rule)
        self.assertIn(".ordbok-expr-term .ordpar-level{vertical-align:.08em}", self.css)


class TheSoundIcons(unittest.TestCase):

    def test_a_the_build_reads_the_term_without_the_box(self):
        from ordpar.sitegen import audio
        self.assertEqual(audio.visible("ha det" + box("A2")), "ha det")
        names = audio.Names(common={("-", "ha det"): "0123456789abcdef"}, source="x", header=audio.HEADER)
        pg = ('<div class="ordbok ordpar-article" lang="nb"><div class="ordbok-expr">'
              '<span class="ordbok-expr-term" lang="nb">ha det%s</span></div></div>' % box("A2"))
        out, entry, counts = audio.mark(pg, 9, names)
        self.assertIn('<span class="ordbok-expr-term" lang="nb" data-a>', out)
        self.assertEqual(counts["expr"], 1)

    def test_b_the_page_script(self):
        js = _read(SITE, "audio.js")
        self.assertIn("var HIDE = '.ordbok-xpeek, .sr-only, .ordpar-visually-hidden, .ordpar-play, .ordpar-level';", js)
        i = js.index("cls.contains('ordbok-expr-term')")
        self.assertIn("el.insertBefore(button([textOf([el])], id), box);", js[i:i + 600])


class SmallArticles(unittest.TestCase):

    def test_no_box(self):
        js = _read(SITE, "mini.js")
        body = re.search(r"function finish\(root\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("root.querySelectorAll('.ordpar-level')", body)


class Help(unittest.TestCase):

    def test_the_section(self):
        from ordpar.sitegen import about
        _t, body = about.help_page()
        m = re.search(r'<h2 id="cefr-levels">CEFR levels</h2>(.*?)(?:<h2|$)', body, re.S)
        self.assertIsNotNone(m, "no CEFR levels section")
        for lv in ("A1 · beginner", "A2 · elementary", "B1 · intermediate", "B2 · upper intermediate",
                   "C · advanced"):
            self.assertIn("<li><strong>%s</strong>" % lv, m.group(1))
        self.assertIn("C1 and C2", m.group(1))


# ---- rendered pages --------------------------------------------------------------------------

def mirror_path():
    sys.path.insert(0, ORDPAR)
    try:
        from ordpar import local_paths
        p = local_paths.get("mirror")
    except Exception:
        p = None
    return p if p and os.path.exists(p) else None


_BUILT = {}


def builder(with_levels=True):
    """A `build_site.Builder` over the real mirror and library, as `main` makes it (the example
    gate applied), with the committed levels or none; cached per kind."""
    if with_levels in _BUILT:
        return _BUILT[with_levels]
    from ordpar import build_site
    from ordpar.sitegen import mirror as mirror_mod, library, gate, deck
    if "store" not in _BUILT:
        rows = deck.store.read_jsonl(deck.fetch.LIBRARY_PATH)
        rows, _held, _by = gate.apply(rows, deck.fetch.LIBRARY_PATH)
        m = mirror_mod.Mirror(mirror_path())
        m.index()
        page.set_shapes(dict(m.shapes))
        _BUILT["store"] = (library.Store(m, rows), m)
    store, m = _BUILT["store"]
    b = build_site.Builder(store, m, "levels187 test")
    if with_levels:
        b.levels = levels.read()
    _BUILT[with_levels] = b
    return b


@unittest.skipUnless(mirror_path(), "no mirror (ordpar/local-paths.json `mirror`)")
class RenderedPages(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if levels is None:
            raise AssertionError("no ordpar/sitegen/levels.py")
        cls.lv = levels.read()
        b = builder(True)
        cls.pages = {aid: b.page(aid)["html"] for aid in (24627, 5026, 128786, 42134)}
        cls.counts = dict(b.level_counts)
        bare = builder(False)
        cls.bare = {aid: bare.page(aid)["html"] for aid in (24627, 5026)}

    def h1(self, aid):
        return re.search(r'<h1 class="ordpar-hw"[^>]*>(.*?)</h1>', self.pages[aid], re.S).group(1)

    def test_a_hus_headword_and_set_phrases(self):
        self.assertTrue(self.h1(24627).endswith(box(self.lv[24627])), self.h1(24627)[-300:])
        exprs = re.findall(r'id="x(\d+)-', self.pages[24627])
        terms = re.findall(r'<span class="ordbok-expr-term"[^>]*>(.*?)</span>\s*<', self.pages[24627], re.S)
        self.assertGreater(len(terms), 5)
        got = re.findall(r'<span class="ordbok-expr-term"[^>]*>[^<]*(<span class="ordpar-level".*?</span></span>)',
                         self.pages[24627])
        self.assertEqual(len(got), len(terms))
        self.assertTrue(exprs)

    def test_b_each_set_phrase_its_own_level(self):
        # each term's box is its own article's level: the expressions in the page's order
        b = builder(True)
        root, lib = b.store.page_library(24627)
        order = [e for e in article.g._expr_order(root["exprs"], lib) if lib.get(e) is not None]
        shown = re.findall(r'<span class="ordbok-expr-term"[^>]*>[^<]*<span class="ordpar-level" data-level="(\w+)"',
                           self.pages[24627])
        untr = set(b.untranslated_on_translated.get(24627) or [])
        want = [self.lv[e] for e in order if e not in untr] + [self.lv[e] for e in order if e in untr]
        self.assertEqual(shown, want)

    def test_c_two_spellings_no_definition_norwegian_only(self):
        h = self.h1(5026)
        self.assertTrue(h.endswith(box(self.lv[5026])))
        self.assertLess(h.rindex("ordbok-lemma"), h.index("ordpar-level"))
        for aid in (128786, 42134):
            self.assertTrue(self.h1(aid).endswith(box(self.lv[aid])), aid)
        self.assertIn("ordbok-nodef", self.pages[128786])               # no definition
        self.assertIn('lang="nb"', self.pages[42134][:200000])

    def test_d_the_counts(self):
        self.assertEqual((self.counts["articles"], self.counts["articles_without"]), (4, 0))
        self.assertGreater(self.counts["phrases"], 10)

    def test_d2_what_has_no_level_is_counted(self):
        # an article and a set phrase missing from the levels (newer data, say) are counted as
        # without a box, in the build's line and in `build.json` `levels`
        from ordpar import build_site
        store, m = _BUILT["store"]
        b = build_site.Builder(store, m, "levels187 missing")
        b.levels = dict(self.lv)
        root, lib = b.store.page_library(24627)
        phrase = next(e for e in root["exprs"] if e in lib)
        del b.levels[24627], b.levels[phrase]
        b.page(24627)
        self.assertEqual((b.level_counts["articles"], b.level_counts["articles_without"]), (0, 1))
        self.assertEqual(b.level_counts["phrases_without"], 1)
        line = build_site.levels_line(b)
        self.assertIn("0 articles with a box, 1 without", line)
        self.assertRegex(line, r"\d+ distinct embedded set phrases with a box, 1 without$")
        rep = build_site.levels_report(b, levels.PATH)
        self.assertEqual((rep["articles_without_box"], rep["distinct_embedded_phrases_without_box"]), (1, 1))

    def test_e_without_levels_no_box(self):
        for aid, html in self.bare.items():
            self.assertNotIn("ordpar-level", html, aid)
            bare = re.sub(r'<span class="ordpar-level".*?</span></span>', "", self.pages[aid])
            # site decisions 188: the level on each set phrase's block and the section's class
            bare = re.sub(r' data-level="\w+"(?=>)', "", bare.replace(' ordpar-exprs"', '"'))
            self.assertEqual(bare, html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
