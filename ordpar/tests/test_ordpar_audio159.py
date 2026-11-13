"""The audio on the site, the build side (site decisions 159, 2026-11-02; Robin's pick from the style
lab, the speed and the screen readers ruled the same day).

Pins:
* **the names** (`sitegen/audio.py` `Names`): the file's lines read back (an article's line first,
  `-` meaning no clip, a definition line looked up `d` then as any text), a header refused that is
  not the exporter's; the whitespace rule (a trailing or a double space finds the clip);
* **the marks** (`audio.mark`) on a synthetic page: the headword's main form and every other
  spelling, never the ", " between them (decisions 160), a set phrase's term,
  a definition line (`data-a`; `data-a="10"` where one segment of two has a clip; a hover's peek
  dropped from the text), an example's quote named without its explanation, a compound list's line
  and a translated page's English line never marked; a set phrase's texts named with its own id
  (an article-scoped name); the article's entry (a definition line's key TAB-led) with every table
  form the island can draw (bare and after å, har, en, ei, et); a page with nothing voiced unchanged;
  nothing but attributes added (no "Play" in the page);
* **the per-500 split** (`audio.write_files`): ids 1-500 in `0.json`, 501-1000 in `1.json`; a partial
  run keeps the other articles of a file it touches, an empty entry removes an article, a whole run
  removes a file no article fills; the offline copy never packs `out/audio/`;
* **the public code**: nothing under `ordpar/` imports `scripts/audio/` or names the clip store;
  `build_site.py` takes `--audio-names` and records `audio` in `build.json`;
* **the speed setting**: two choices, "As recorded" first and the default (107), then "90%", its own
  subsection "Audio" last under Article, its words, in the export (60) and the address table (146);
  `audio.js` plays at 0.9 with the pitch kept;
* **the sheet**: 1.00 rem, day #bab8b8, night #6f6b6c through `:where(html.nightMode)` (so hover's
  text colour and playing's accent outweigh it), not selectable, the 24 px tap area;
* **the script's wiring**: `audio.js` in both bundles before the page script and `mini.js`; the page
  script's `ordparDefs` scans; `mini.js` `fill` mounts the icons before `fit`; a set phrase's icon
  appended inside its term; the labels "Play" / "Spill av" by the label classes, the English one
  `lang="en"`, inside a `data-nosnippet` hidden span (154); the Worker's address; loading on rest
  after `REST_MS` (150, mini.js's) for a mouse only;
* **the readers of the markup**: on the built *hus* (24627, when `ordpar/out/` and the names file are
  there) the description and the snippets are what the page had before the marks, and the marks
  add no text.
* **the tables' mark** (site decisions 170, 2026-11-06: the list fetched only when a recording is
  wanted, so the tables' icons drawn from the page): the island's `data-a-cells` (`audio.table_code`,
  read back by `audio.table_keys`), on the synthetic page (*hus*, *tå*, *være*: exactly the entry's
  table keys, every frame), no attribute where no form has a clip, a page with no table unchanged;
  on the built pages re-marked with the names file (`ordpar/out/` and the names file, else
  skipped): *hus* 24627 all 4 forms named ("x111": bare, *et hus*), *bru, bro* 7663 all 10 ("ei"
  and "en" with the two lemmas' bare forms), *abbed* 13 only the bare form ("1"), *abortus
  provocatus* 62 (no table) no attribute and its page as built; each page otherwise byte for byte
  the built one, and the keys exactly the entry's keys the island can draw (what `audio.js`
  `cells` matched a cell against when it read them from the names file). The script: `tableKeys`
  reading the attribute with the same frames and characters, `cells` drawing from it, and no
  names fetched by `scan` or `mount`. Fails on the build deployed as 9b50a8b8d9c3375d (no
  attribute).
Fails before the build (no `sitegen/audio.py`, no `audio.js`, no setting).
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
sys.path.insert(0, ROOT)

from ordpar.sitegen import audio  # noqa: E402

SITE = os.path.join(ORDPAR, "site")
NAMES_FILE = os.environ.get("ORDPAR_TEST_AUDIO_NAMES") or os.path.join(ROOT, ".cache", "ordpar-audio-names.tsv")
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ORDPAR, "out")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


H = {"hus": "0f0ec0761c965550", "def1": "1111111111111111", "ex": "2222222222222222",
     "term": "3333333333333333", "termdef": "4444444444444444", "scoped": "5555555555555555",
     "et": "6666666666666666", "aa": "7777777777777777", "ei": "8888888888888888",
     "par": "9999999999999999"}

NAMES_TSV = "\n".join([
    audio.HEADER + " · test",
    "hus\t-\t*\t" + H["hus"],
    "bygning\t-\t*\t" + H["def1"],
    "bo i et hus\t-\t*\t" + H["ex"],
    "fullt hus\t-\t*\t" + H["term"],
    "mange folk\t-\t*\t" + H["termdef"],
    "mange folk\t-\t102921\t" + H["scoped"],
    "et hus\t-\t*\t" + H["et"],
    "å være\t-\t*\t" + H["aa"],
    "ei tå\t-\t*\t" + H["ei"],
    "huset\t-\t*\t" + H["et"],
    "som har to deler (i biologi)\t-\t*\t" + H["par"],
    "som har to deler (i biologi)\td\t*\t-",
    "ha al etter et dyr\t-\t*\t" + H["ex"],
    "fort\t-\t17077\t-",
    "fort\t-\t*\t" + H["def1"],
    "lavpris\t-\t*\t" + H["term"],
    "lågpris\t-\t*\t" + H["termdef"],
    ",\t-\t*\t" + H["par"],
]) + "\n"

PAGE = (
    '<!doctype html>\n<html lang="en" data-article-id="24627"><head><title>hus</title></head><body>\n'
    '<div class="ordbok ordpar-article" lang="en">\n'
    '<div class="ordbok-head"><h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma">hus</span></h1></div>\n'
    '<ol class="ordbok-senses"><li id="def1">\n'
    '<span class="ordpar-pair"><span class="ordbok-def" lang="nb"><span class="ordbok-xref">'
    '<a class="ordbok-xword" href="/bm-en/9/">bygning</a><span class="ordbok-xpeek" lang="en" data-nosnippet>'
    'a building;<br>x</span></span>;<br>ukjent tekst</span>\n'
    '<span class="ordbok-def">a building;<br>unknown</span></span>\n'
    '<ul class="ordbok-ex-list">\n<li><span lang="nb"><em>bo i et hus</em> <span class="ordbok-exexpl">– forklaring</span></span>\n'
    '<span class="ordbok-tr ordpar-en">live in a house</span></li>\n'
    '<li><span lang="nb"><em>ha al etter et dyr </em></span></li>\n'
    '<li><span lang="nb"><em>ingen lyd her</em></span></li></ul>\n'
    '<div class="ordbok-sub ordpar-comp"><span class="ordbok-def">hus</span></div>\n'
    '</li></ol>\n'
    '<div class="ordbok-expr">\n<span class="ordbok-expr-term" lang="nb">fullt  hus</span>\n'
    '<ol class="ordbok-senses ordbok-subsenses"><li id="x102921-def2">'
    '<span class="ordpar-pair"><span class="ordbok-def" lang="nb">mange folk</span>\n'
    '<span class="ordbok-def">many people</span></span></li></ol></div>\n'
    '<div class="ordpar-inflection-island"><script type="application/json" id="ordpar-paradigm">'
    '[["hus",["s1","hus","huset","hus","husa"]],["tå",["s2","tå","tåa"]],["være",["s3","være","vært"]]]'
    '</script></div>\n'
    '</div>\n<footer class="ordpar-card-foot"></footer></body></html>\n')


class Fixture(object):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "names.tsv")
        with open(cls.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(NAMES_TSV)
        cls.names = audio.Names.read(cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class Names(Fixture, unittest.TestCase):
    def test_lookup(self):
        n = self.names
        self.assertEqual(n.get("hus", 1), H["hus"])
        self.assertEqual(n.get("mange folk", 102921), H["scoped"])          # the article's line first
        self.assertEqual(n.get("mange folk", 5), H["termdef"])
        self.assertIsNone(n.get("fort", 17077))                             # `-`: no clip there
        self.assertEqual(n.get("fort", 3), H["def1"])
        # a definition line: `d` first (here `-`, not uploaded: no button), else as any text
        self.assertIsNone(n.get("som har to deler (i biologi)", 1, definition=True))
        self.assertEqual(n.get("som har to deler (i biologi)", 1), H["par"])
        self.assertEqual(n.get("bygning", 1, definition=True), H["def1"])
        self.assertIsNone(n.get("ingen lyd her", 1))
        self.assertIsNone(n.get("   ", 1))

    def test_whitespace(self):
        self.assertEqual(audio.norm("  ha al\tetter  et dyr \n"), "ha al etter et dyr")
        self.assertEqual(self.names.get("ha al etter et dyr ", 664), H["ex"])
        self.assertEqual(self.names.get("fullt  hus", 1), H["term"])

    def test_not_a_names_file(self):
        p = os.path.join(self.tmp, "bad.tsv")
        with open(p, "w", encoding="utf-8") as f:
            f.write("hus\t-\t*\t" + H["hus"] + "\n")
        with self.assertRaises(ValueError):
            audio.Names.read(p)


class Marks(Fixture, unittest.TestCase):
    def test_the_marks(self):
        page, entry, counts = audio.mark(PAGE, 24627, self.names)
        self.assertIn('<span class="ordbok-lemma" data-a>hus</span>', page)
        self.assertIn('<span class="ordbok-expr-term" lang="nb" data-a>fullt  hus</span>', page)
        # one segment of two: the peek's ";<br>" never splits the line
        self.assertIn('<span class="ordbok-def" lang="nb" data-a="10">', page)
        self.assertIn('<span class="ordbok-def" lang="nb" data-a>mange folk</span>', page)
        self.assertIn('<li><span lang="nb" data-a><em>bo i et hus</em>', page)
        self.assertIn('<li><span lang="nb" data-a><em>ha al etter et dyr </em>', page)   # the whitespace rule
        self.assertIn('<li><span lang="nb"><em>ingen lyd her</em>', page)                # no clip, no mark
        self.assertIn('<span class="ordbok-def">a building;', page)                      # English: never
        self.assertIn('<div class="ordbok-sub ordpar-comp"><span class="ordbok-def">hus</span>', page)
        self.assertEqual(counts["head"], 1)
        self.assertEqual(counts["def_lines"], 2)
        # only attributes: the page's text is unchanged, and no button words
        strip = lambda s: re.sub(r"<[^>]+>", "", s)
        self.assertEqual(strip(page), strip(PAGE))
        self.assertNotIn("Play", page)
        self.assertEqual(re.sub(r' data-a(?:="[01]+")?(?=>)', "", re.sub(r' data-a-cells="[^"]*"', "", page)), PAGE)

    def test_every_spelling(self):
        # site decisions 160: each spelling of the headword line is marked, the ", " between them
        # never (even were a "," in the names), a spelling without a clip left bare
        head = ('<h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma">lavpris</span>'
                ' <span class="ordbok-homograph">II</span><span class="ordbok-lemma">, </span>'
                '<span class="ordbok-lemma">lågpris</span><span class="ordbok-lemma">, </span>'
                '<span class="ordbok-lemma">lavpriz</span></h1>')
        src = re.sub(r'<h1 class="ordpar-hw".*?</h1>', head, PAGE)
        page, entry, counts = audio.mark(src, 24627, self.names)
        self.assertIn('<span class="ordbok-lemma" data-a>lavpris</span>', page)
        self.assertIn('<span class="ordbok-lemma" data-a>lågpris</span>', page)
        self.assertIn('<span class="ordbok-lemma">lavpriz</span>', page)
        self.assertEqual(page.count('<span class="ordbok-lemma">, </span>'), 2)
        base = audio.mark(PAGE, 24627, self.names)[2]["missing"]      # the page's other misses
        self.assertEqual((counts["head"], counts["spellings"], counts["missing"] - base), (1, 1, 1))
        self.assertEqual((entry["lavpris"], entry["lågpris"]), (H["term"], H["termdef"]))
        self.assertNotIn(",", entry)

    def test_every_lemma_group(self):
        # 160's follow-up (2026-11-03, the audio session's find, *forutanelse* / *forutaning* 17213):
        # a lemma group after the first, with its own word class, is a `p.ordpar-hw` after the `h1`
        # (`article.py`); its spellings are marked as the `h1`'s, a spelling without a clip bare
        head = ('<h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma">lavpris</span></h1>'
                '<span class="ordbok-pos">noun</span>'
                '<p class="ordpar-hw" lang="nb"><span class="ordbok-lemma">lågpris</span>'
                '<span class="ordbok-lemma">, </span><span class="ordbok-lemma">lavpriz</span></p>'
                '<span class="ordbok-pos">noun</span>')
        src = re.sub(r'<h1 class="ordpar-hw".*?</h1>', head, PAGE)
        page, entry, counts = audio.mark(src, 24627, self.names)
        self.assertIn('<h1 class="ordpar-hw" lang="nb"><span class="ordbok-lemma" data-a>lavpris</span>', page)
        self.assertIn('<p class="ordpar-hw" lang="nb"><span class="ordbok-lemma" data-a>lågpris</span>', page)
        self.assertIn('<span class="ordbok-lemma">lavpriz</span>', page)
        self.assertIn('<span class="ordbok-lemma">, </span>', page)
        base = audio.mark(PAGE, 24627, self.names)[2]["missing"]
        self.assertEqual((counts["head"], counts["spellings"], counts["groups"], counts["missing"] - base),
                         (1, 0, 1, 1))
        self.assertEqual(entry["lågpris"], H["termdef"])

    def test_the_entry(self):
        _page, entry, _c = audio.mark(PAGE, 24627, self.names)
        self.assertEqual(entry["hus"], H["hus"])
        self.assertEqual(entry["\tbygning"], H["def1"])                 # a definition line: TAB-led
        self.assertEqual(entry["\tmange folk"], H["scoped"])            # the set phrase's own id
        self.assertEqual(entry["bo i et hus"], H["ex"])
        self.assertEqual(entry["fullt hus"], H["term"])                 # the key collapsed
        # the table forms the island can draw: et hus, huset, ei tå, å være (bare forms too)
        for k in ("et hus", "huset", "ei tå", "å være"):
            self.assertIn(k, entry)
        self.assertNotIn("ingen lyd her", entry)
        self.assertFalse(any(k.startswith("\t") and k[1:] in ("bo i et hus",) for k in entry))

    def test_nothing_voiced(self):
        page = PAGE.replace("hus", "xyz").replace("bygning", "abc").replace("bo i et", "q").replace(
            "fullt", "w").replace("mange folk", "e").replace("ha al etter et dyr", "r")
        page = re.sub(r'(id="ordpar-paradigm">).*?(</script>)', r'[["q",["s1","q"]]]', page)
        got, entry, _c = audio.mark(page, 24627, self.names)
        self.assertEqual(got, page)
        self.assertEqual(entry, {})
        self.assertEqual(audio.mark(PAGE, 24627, None)[0], PAGE)


class Files(unittest.TestCase):
    def test_the_split(self):
        self.assertEqual([audio.file_of(i) for i in (1, 500, 501, 1000, 1001)], [0, 0, 1, 1, 2])
        with tempfile.TemporaryDirectory() as out:
            got = audio.write_files(out, {1: {"a": "1" * 16}, 500: {"b": "2" * 16}, 501: {"c": "3" * 16},
                                          1001: {"d": "4" * 16}}, replace=True)
            d = os.path.join(out, "audio")
            self.assertEqual(sorted(os.listdir(d)), ["0.json", "1.json", "2.json"])
            self.assertEqual(json.loads(read(d, "0.json")), {"1": {"a": "1" * 16}, "500": {"b": "2" * 16}})
            self.assertEqual(got["files"], 3)
            self.assertEqual(got["articles"], 4)
            # a partial run: the file's other articles kept, an emptied article removed
            audio.write_files(out, {2: {"e": "5" * 16}, 500: {}}, replace=False)
            self.assertEqual(json.loads(read(d, "0.json")), {"1": {"a": "1" * 16}, "2": {"e": "5" * 16}})
            self.assertTrue(os.path.exists(os.path.join(d, "2.json")))
            # a whole run: a file no article fills goes
            audio.write_files(out, {1: {"a": "1" * 16}}, replace=True)
            self.assertEqual(sorted(os.listdir(d)), ["0.json"])

    def test_not_offline(self):
        from ordpar import build_offline
        with tempfile.TemporaryDirectory() as out:
            for rel in ("audio/0.json", "site/audio.js"):
                os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
                with open(os.path.join(out, rel), "w") as f:
                    f.write("{}")
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):          # its warnings for the shell pages
                files = build_offline.other_files(out)
        self.assertIn("/site/audio.js", files)
        self.assertFalse(any(u.startswith("/audio/") for u in files))


class PublicCode(unittest.TestCase):
    def test_no_private_reads(self):
        skip = {"out", "tests", "__pycache__", "audio-worker", "receiver", ".build", "node_modules", "test"}
        for top, dirs, names in os.walk(ORDPAR):
            dirs[:] = [d for d in dirs if d not in skip]
            for n in names:
                if not n.endswith((".py", ".js")):
                    continue
                text = read(top, n)
                self.assertNotIn("scripts/audio", text.replace("\\", "/"), n)
                self.assertNotRegex(text, r"\bimport clips\b|\bimport upload_r2\b|ordpar-clips", n)

    def test_the_build_takes_the_names(self):
        src = read(ORDPAR, "build_site.py")
        self.assertIn('"--audio-names"', src)
        self.assertIn('"audio": audio_report(b, names, audio_files)', src)
        self.assertIn("audio_mod.mark(", src)


class Speed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = read(SITE, "shell.js")
        cls.strings = json.loads(read(SITE, "strings", "en.json"))

    def test_the_setting(self):
        self.assertIn("{ key: 'audiospeed', values: ['recorded', '90'], def: 'recorded', "
                      "section: 'article', sub: 'audio' }", self.shell)
        order = re.findall(r"\{ key: '(\w+)'", self.shell)
        # last under Article, before Search
        self.assertEqual(order[order.index("audiospeed") + 1], "listview")
        self.assertEqual(order[order.index("audiospeed") - 1], "minihw")

    def test_the_words(self):
        s = self.strings
        self.assertEqual(s["settings.sub.audio"], "Audio")
        self.assertEqual(s["settings.audiospeed"], "Speed of the spoken words")
        self.assertEqual(s["settings.audiospeed.recorded"], "As recorded")
        self.assertEqual(s["settings.audiospeed.90"], "90%")
        self.assertEqual(s["settings.audiospeed.hint"],
                         "How fast the voice reads when you press a sound icon. \"As recorded\" is the "
                         "recordings' own speed, which is already 10% slower than the voice's usual "
                         "pace. \"90%\" plays the same recordings more slowly, and the voice keeps its pitch.")

    def test_it_travels(self):
        self.assertIn("'audiospeed'", read(SITE, "personal.js"))           # the export (60)
        from ordpar.sitegen import head
        table = dict(head.settings_table())
        self.assertEqual(table["audiospeed"], ["recorded", "90"])            # the address (146)

    def test_the_rate(self):
        js = read(SITE, "audio.js")
        self.assertIn("var SPEEDS = { recorded: 1, '90': 0.9 };", js)
        self.assertIn("setting('audiospeed', 'recorded')", js)
        for s in ("a.playbackRate = r;", "a.defaultPlaybackRate = r;", "a.preservesPitch = true;",
                  "a.webkitPreservesPitch = true;"):
            self.assertIn(s, js)


class Sheet(unittest.TestCase):
    def test_the_css(self):
        from ordpar.sitegen import page
        css = page.SITE_CSS
        self.assertIn("color:#bab8b8;", css)
        self.assertIn(":where(html.nightMode) .ordpar-play{color:#6f6b6c}", css)
        self.assertNotIn("html.nightMode .ordpar-play{", css.replace(":where(html.nightMode) .ordpar-play{", ""))
        self.assertIn(".ordpar-play svg{display:block;width:1rem;height:1rem}", css)
        self.assertIn("@media (hover:hover){.ordpar-play:hover{color:var(--ordpar-text)}}", css)
        self.assertIn(".ordpar-play.ordpar-playing{color:var(--ordpar-accent)}", css)
        self.assertIn("user-select:none}", css[css.index(".ordpar-play{"):])
        self.assertIn("calc(50% - 12px)", css)                                # the 24 px tap area
        self.assertIn(".ordpar-play-failed{opacity:.35}", css)
        # shipped in the article's sheet, which the shell pages link too
        self.assertIn(".ordpar-play{", page.shipped(page.CSS_HREF))


class Script(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read(SITE, "audio.js")

    def test_the_bundles(self):
        from ordpar.sitegen import page
        a = page.ARTICLE_JS_PARTS
        self.assertLess(a.index(page.AUDIO_JS_HREF), a.index(page.JS_HREF))
        self.assertLess(a.index(page.AUDIO_JS_HREF), a.index(page.MINI_JS_HREF))
        self.assertIn(page.AUDIO_JS_HREF, page.SHELL_JS_PARTS)
        self.assertIn("var A=window.ordparAudio;if(A&&A.scan)A.scan();", page.PAGE_JS)
        self.assertIn("window.ordparAudio", page.shipped(page.JS_ALL_HREF))

    def test_the_small_article(self):
        mini = read(SITE, "mini.js")
        i = mini.index("function fill(")
        body = mini[i:mini.index("\n  }\n", i)]
        self.assertIn("global.ordparAudio.mount(box, t.id, art)", body)
        self.assertLess(body.index("ordparAudio.mount"), body.index("fit(m);"))

    def test_the_button(self):
        js = self.js
        self.assertIn("b.className = 'ordpar-play';", js)
        self.assertIn("b.type = 'button';", js)
        self.assertIn('<span class="ordpar-visually-hidden" data-nosnippet>', js)
        self.assertIn('<span class="ordpar-l-en" lang="en">', js)
        self.assertIn('<span class="ordpar-l-nb" lang="nb">', js)
        self.assertIn("var WORDS = { play: ['Play', 'Spill av'], stop: ['Stop', 'Stopp'] };", js)
        self.assertIn('aria-hidden="true" focusable="false"', js)
        # a set phrase's icon inside its block-level term, at its end
        i = js.index("cls.contains('ordbok-expr-term')")
        self.assertIn("el.appendChild(button(", js[i:i + 300])

    def test_loading_and_playing(self):
        js = self.js
        self.assertIn("var WORKER = 'https://ordpar-audio.ordpar.workers.dev/';", js)
        self.assertIn("var REST_MS = 150;", js)
        self.assertIn("if (e.pointerType !== 'mouse') { return; }", js)
        self.assertIn("l.rel = 'preconnect';", js)
        self.assertIn("var GAP = 300;", js)
        self.assertIn("var NAMES = '/audio/';", js)
        self.assertNotIn("fetch(WORKER", js)                  # the clips by <audio>, never fetch
        self.assertIn("ruled(t) { return norm(t).replace(/^ei\\/en /, 'ei ').replace(/!$/, ''); }", js)


def strip_marks(page):
    """A built page without its sound marks (`data-a`, `data-a="101"`, the tables' `data-a-cells`)."""
    return re.sub(r' data-a(?:="[01]+")?(?=>)', "", re.sub(r' data-a-cells="[^"]*"', "", page))


_ISL = re.compile(r'<script type="application/json" id="ordpar-paradigm"([^>]*)>(.*?)</script>', re.S)


def table_mark(page):
    """(the island's forms, its `data-a-cells` or None) of a page; (None, None) with no island."""
    m = _ISL.search(page)
    if not m:
        return None, None
    c = re.search(r' data-a-cells="([^"]*)"', m.group(1))
    return audio.island_forms(m.group(2)), (c.group(1) if c else None)


class TableMarks(Fixture, unittest.TestCase):
    """Site decisions 170's second part (Robin, 2026-11-06, "Yes, marks now")."""

    def test_the_synthetic_page(self):
        page, entry, counts = audio.mark(PAGE, 24627, self.names)
        forms, code = table_mark(page)
        self.assertEqual(forms, ["hus", "huset", "husa", "tå", "tåa", "være", "vært"])
        self.assertIn('<script type="application/json" id="ordpar-paradigm" data-a-cells="%s">' % code, page)
        keys = audio.table_keys(forms, code)
        # exactly the entry's keys a table form can be, bare or after a frame
        drawable = {audio.norm(f + x) for x in forms for f in audio.FRAMES}
        self.assertEqual(keys, {k for k in entry if k in drawable})
        self.assertEqual(keys, {"hus", "et hus", "huset", "ei tå", "å være"})
        self.assertEqual(code, "x10g02")   # hus: bare + et (33); huset: bare; husa none; tå: ei (16); tåa none; være: å (2)
        self.assertEqual((counts["tables"], counts["table_forms"]), (1, 4))
        self.assertEqual(audio.table_code(forms, entry), code)

    def test_the_code(self):
        self.assertEqual(len(audio.CELL_CODE), 64)
        self.assertEqual(len(set(audio.CELL_CODE)), 64)
        self.assertEqual(audio.FRAMES, ("", "å ", "har ", "en ", "ei ", "et "))
        every = {audio.norm(f + "x") for f in audio.FRAMES}
        self.assertEqual(audio.table_code(["x"], every), "_")
        self.assertEqual(audio.table_keys(["x"], "_"), every)
        self.assertEqual(audio.table_code(["a", "b", "c"], {"b"}), "01")      # trailing "0"s dropped
        self.assertEqual(audio.table_keys(["a", "b", "c"], "01"), {"b"})
        self.assertEqual(audio.table_code(["a"], set()), "")

    def test_no_form_voiced_no_mark(self):
        src = re.sub(r'(id="ordpar-paradigm">).*?(</script>)', r'\1[["q",["s1","q","qa"]]]\2', PAGE)
        page, _entry, counts = audio.mark(src, 24627, self.names)
        self.assertNotIn("data-a-cells", page)
        self.assertEqual(counts["tables"], 0)
        # the page's other marks as before: only the island's attribute is new
        self.assertEqual(page, re.sub(r'(id="ordpar-paradigm">).*?(</script>)',
                                      r'\1[["q",["s1","q","qa"]]]\2', audio.mark(PAGE, 24627, self.names)[0]
                                      .replace(' data-a-cells="x10g02"', "")))

    def test_no_table_no_mark(self):
        src = re.sub(r'<div class="ordpar-inflection-island">.*?</div>\n', "", PAGE, flags=re.S)
        self.assertNotIn("ordpar-paradigm", src)
        page, _entry, counts = audio.mark(src, 24627, self.names)
        self.assertNotIn("data-a-cells", page)
        self.assertEqual(counts["tables"], 0)

    def test_the_built_pages(self):
        if not (os.path.exists(os.path.join(OUT, "bm-en", "24627", "index.html")) and os.path.exists(NAMES_FILE)):
            self.skipTest("no built pages or no names file (%s)" % NAMES_FILE)
        names = audio.Names.read(NAMES_FILE)
        want = {
            24627: ("x111", ["hus", "huset", "husa", "husene"],
                    {"hus", "et hus", "huset", "husa", "husene"}),
            7663: ("p1111p1111", ["bru", "brua", "bruer", "bruene", "bruen", "bro", "broa", "broer", "broene", "broen"],
                   {"bru", "ei bru", "en bru", "brua", "bruer", "bruene", "bruen",
                    "bro", "ei bro", "en bro", "broa", "broer", "broene", "broen"}),
            13: ("1", ["abbed", "abbeden", "abbeder", "abbedene"], {"abbed"}),
            62: (None, None, set()),                     # abortus provocatus: no table
        }
        for aid, (code, forms, keys) in sorted(want.items()):
            with self.subTest(aid=aid):
                built = read(OUT, "bm-en", str(aid), "index.html")
                bare = strip_marks(built)
                got, entry, counts = audio.mark(bare, aid, names)
                gforms, gcode = table_mark(got)
                self.assertEqual((gcode, gforms), (code, forms))
                self.assertEqual(audio.table_keys(gforms or [], gcode), keys)
                drawable = {audio.norm(f + x) for x in (gforms or []) for f in audio.FRAMES}
                self.assertEqual(keys, {k for k in entry if k in drawable})
                # every other byte as built: the attribute is all that is added
                self.assertEqual(strip_marks(got), bare)
                self.assertEqual(re.sub(r' data-a-cells="[^"]*"', "", got),
                                 re.sub(r' data-a-cells="[^"]*"', "", built))
                self.assertEqual(len(got.encode("utf-8")) - len(re.sub(r' data-a-cells="[^"]*"', "", built).encode("utf-8")),
                                 len(' data-a-cells="%s"' % code) if code else 0)

    def test_the_script_reads_it(self):
        js = read(SITE, "audio.js")
        self.assertIn("var FRAMES = ['', '\\u00e5 ', 'har ', 'en ', 'ei ', 'et '];", js)
        self.assertIn("var CODE = '%s';" % audio.CELL_CODE, js)
        self.assertIn("root.querySelectorAll('script[data-a-cells]')", js)
        self.assertIn("if (!t || !keys[t]) { return; }", js)
        for fn in ("scan", "mount"):
            i = js.index("function %s(" % fn)
            body = js[i:js.index("\n  }\n", i)]
            with self.subTest(fn):
                self.assertNotIn("names(", body)           # no list fetched as an article opens
                self.assertNotIn("withNames", body)
                self.assertIn("ahead()", body)              # no preconnect under `click`
        i = js.index("function scan(")
        self.assertIn("tableKeys(art)", js[i:js.index("\n  }\n", i)])


class BuiltPage(unittest.TestCase):
    """The readers of the changed markup, on the built *hus* (skipped without a build or names)."""

    def test_readers(self):
        p = os.path.join(OUT, "bm-en", "24627", "index.html")
        if not (os.path.exists(p) and os.path.exists(NAMES_FILE)):
            self.skipTest("no built page or no names file (%s)" % NAMES_FILE)
        page = read(p)
        names = audio.Names.read(NAMES_FILE)
        bare = strip_marks(page)
        got, entry, counts = audio.mark(bare, 24627, names)
        self.assertGreater(counts["head"] + counts["def"] + counts["ex"], 10)
        self.assertNotIn("Play", got)
        self.assertNotIn("Spill av", got)
        # the description, the title and the personal fields are in <head>/<html>: unchanged
        head = lambda s: s[:s.index("<body")]
        self.assertEqual(head(got), head(bare))
        # the description reader over the marked fragment reads the same definitions
        from ordpar.sitegen import describe
        frag = lambda s: s[s.index('<div class="ordbok'):s.index('<footer class="ordpar-card-foot">')]
        self.assertEqual(describe.definitions(frag(got), True), describe.definitions(frag(bare), True))


if __name__ == "__main__":
    unittest.main()
