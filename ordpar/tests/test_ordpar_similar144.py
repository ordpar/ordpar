"""Site decisions 144 (Robin, 2026-10-27): the similar headwords as rows after a miss, the Norwegian
homograph list, and no reference numbers in one-line Norwegian definitions.

The parts that need no browser (the browser side: `test_ordpar_browser_similar144.py`):

* **The source**: `lookup.js` `render` draws the rows only when the search finds nothing
  (`!res.count`), a hit keeping the bare list; the miss-choice listener is kept on every link;
  the rows are drawn by the shell's row code (`searchRowMain`, `searchRowSide`, `fillSearchRow`),
  their articles from `similarArticles`. The three surfaces' side rule is one function: the
  suggestions (`glossList` -> `listedGlosses`), History and Recent (`fillSearchRow`) and the
  similar rows (`fillSearchRow` with `similarArticles`) all go through `sideGlosses`.
  `shell.css`: the pill rules scoped off the rows (`:not(.ordpar-similar-rows)`, no override),
  the dash and the line between rows.
* **The rule** (`sideGlosses`, under bun): translated glosses with their numerals where any
  article is translated, never a Norwegian line beside them; with none translated, each
  homograph's Norwegian definition; nothing to list, nothing.
* **The rows over the built index** (`ordpar/out/index`, under bun, the real `lookup.js` and
  `shell.js` in a stand-in page): *husx*, *flyy*, *spisee* and *kjøppte* draw rows with the
  expected words, word classes, colours and sides; *katt* (a hit) the bare list; and each miss
  loads no shard but its own — the rows cost the `snip/` files, not the shards (step 4).
* **The snippets** (`sitegen/article.py` `snippet`, `drop_ref_numbers`): a cross-reference's
  homograph numeral and sense number dropped from a one-line Norwegian definition where the
  markers are reduced, a parenthesis of the definition's own words kept; and over the built
  `snip/` files no Norwegian snippet ends a word with such a number (`ref_numbers`). On the index
  as deployed before 144 that check fails (thousands of snippets; the report has the count).
* **The headword lists** (`headwords/`, `tails/`): `a`, `x`, `k`/`kc` right for *hus*, *husk*,
  *fly*, and for every form against the shards' `heads` and `translated.json`; `snip/`'s `"_h"`
  for *husk* lists its two articles with their numbers.

Skips the parts that need a build without one (`ordpar/out/index/index.json`), and the bun parts
without bun.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
SITE = os.path.join(ORDPAR, "site")
INDEX = os.path.join(ORDPAR, "out", "index")
sys.path.insert(0, ROOT)
sys.path.insert(0, ORDPAR)
sys.path.insert(0, os.path.join(ORDPAR, "tests"))

from ordpar import build_index as B  # noqa: E402

BUILT = os.path.exists(os.path.join(INDEX, "index.json"))
RUNNER = shutil.which("bun") or shutil.which("node")

#: A cross-reference's numbers as a reduced snippet shows them: a word, then " (II)", " (1)" or
#: " (II, 2)" — what the link label carried before 144.
REF_NUMBER = re.compile(r"\w \((?:[IVXL]+(?:, \d+)?|\d+)\)")

#: The articles whose Norwegian line has a parenthesised number of its OWN words, outside any
#: link (read off their snippets on the build of 2026-10-27): kept, as the ruling says. A new
#: entry here is a judgement — check the definition's markers first.
OWN_NUMBERS = {
    1974: "dag nummer to (2) i en høytid",
    18739: "som er fra eller gjelder tiden før Kristoffer Columbus reiste til Amerika (1492)",
    31744: "sett som består av (52) spillkort",
}


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def ref_numbers(index_dir):
    """The Norwegian snippets (an untranslated article's line) in ``index_dir``'s ``snip/`` files
    that still show a reference number, ``OWN_NUMBERS`` aside: ``{id: text}``."""
    tr = set(_json(os.path.join(index_dir, "translated.json")))
    out = {}
    for p in glob.glob(os.path.join(index_dir, "snip", "*.json")):
        for k, v in _json(p).items():
            if k.startswith("_") or int(k) in tr or OWN_NUMBERS.get(int(k)) == v:
                continue
            if REF_NUMBER.search(v):
                out[int(k)] = v
    return out


class TheSource(unittest.TestCase):

    def test_rows_only_on_a_miss_the_listener_kept(self):
        look = _read(SITE, "lookup.js")
        self.assertIn("var rows = !res.count && canDrawRows();", look)
        self.assertIn("var a = rows ? similarRow(s) : el('a', null, s.word);", look)
        self.assertIn("if (!rows) { a.lang = 'nb'; }", look)
        # the listener, on rows and pills alike, unchanged (decisions 62 (1))
        self.assertIn("E.missChoose(g.query, s.word, i + 1)", look)
        self.assertIn("a.addEventListener('auxclick', function (ev) { if (ev.button === 1) { choose(); } });", look)
        row = look.split("function similarRow(s) {")[1].split("\n  }\n")[0]
        self.assertIn("S.searchRowMain(e)", row)
        self.assertIn("S.fillSearchRow(a.appendChild(S.searchRowSide(e)), e, null, S.similarArticles);", row)

    def test_one_side_rule_for_the_three(self):
        shell = _read(SITE, "shell.js")
        listed = shell.split("function listedGlosses(articles, snips) {")[1].split("\n  }\n")[0]
        self.assertIn("return sideGlosses(", listed)
        gl = shell.split("function glossList(g, snips) {")[1].split("\n    }\n")[0]
        self.assertIn("listedGlosses(g.articles, snips)", gl)
        fill = shell.split("function fillSearchRow(side, e, refit, source) {")[1].split("\n  }\n")[0]
        self.assertIn("sideGlosses(got.list)", fill)
        self.assertIn("(source || historyArticles)(e.q)", fill)
        self.assertNotIn("a.translated && a.text; })", fill)          # the old private filter gone
        self.assertIn("sideGlosses: sideGlosses, similarArticles: similarArticles", shell)

    def test_the_stylesheet(self):
        css = _read(SITE, "shell.css")
        self.assertNotRegex(css, r"(?m)^\.ordpar-similar-list a \{")
        self.assertIn(".ordpar-similar-list:not(.ordpar-similar-rows) a {", css)
        self.assertIn(".ordpar-similar-rows > li + li { border-top: 1px solid var(--ordpar-border); }", css)
        dash = css.split(".ordpar-similar-rows .ordpar-option-side::before {")[1].split("}")[0]
        self.assertIn('content: "\\2014";', dash)
        self.assertIn("color: var(--ordpar-muted);", dash)

    def test_the_string(self):
        self.assertEqual(json.loads(_read(SITE, "strings", "en.json"))["similar.formOf"], "inflected form of")


class TheSnippets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from ordpar.sitegen import article
        except Exception as e:                      # the deck's renderer not importable
            raise unittest.SkipTest("sitegen.article not importable: %s" % e)
        cls.article = article

    def test_drop_ref_numbers(self):
        d = self.article.drop_ref_numbers
        self.assertEqual(d("I [evne](/nob/bm/1) til å [huske (III)](/nob/bm/2)"),
                         "I [evne](/nob/bm/1) til å [huske](/nob/bm/2)")
        self.assertEqual(d("[hake (II, 2)](/nob/bm/21880#def4), [men (II)](/nob/bm/37856)"),
                         "[hake](/nob/bm/21880#def4), [men](/nob/bm/37856)")
        self.assertEqual(d("som gjelder [dialektikk (1)](/nob/bm/10005)"),
                         "som gjelder [dialektikk](/nob/bm/10005)")
        # the definition's own parentheses stay, inside a label too where they are words
        own = "retning innenfor filosofi og litteratur (særlig drama) som (1) [ord (særlig)](/nob/bm/5)"
        self.assertEqual(d(own), own)

    def test_the_snippet_drops_them_the_article_keeps_them(self):
        a = self.article
        row = {"id": 1, "pos_en": "noun", "lemmas": [{"form": "husk"}],
               "senses": [{"defn": 1, "no": ["evne til å [huske (III)](/nob/bm/24700) (særlig godt)"],
                           "en": [None], "subs": [], "ex": [], "comp": []}]}
        self.assertEqual(a.snippet(row, None), ("evne til å huske (særlig godt)", "nb"))
        self.assertIn("(III)", row["senses"][0]["no"][0])            # the row itself untouched

    @unittest.skipUnless(BUILT, "no build (ordpar/out/index)")
    def test_no_reference_numbers_in_the_built_snippets(self):
        got = ref_numbers(INDEX)
        self.assertEqual(got, {}, "Norwegian snippets still showing a reference number: %d, e.g. %r"
                         % (len(got), sorted(got.items())[:5]))


@unittest.skipUnless(BUILT, "no build (ordpar/out/index)")
class TheHeadwordLists(unittest.TestCase):

    @staticmethod
    def entry(sub, key, form):
        d = _json(os.path.join(INDEX, sub, key + ".json"))
        i = d["w"].index(form)
        k = d["k"][i]
        return {"a": int(d["a"][i], 16), "x": d["x"][i] == "1",
                "pos": "" if k == "." else d["kc"][B.ROW_CODES.index(k)]}

    def test_known_words(self):
        self.assertEqual(self.entry("headwords", "h", "hus"), {"a": 1, "x": True, "pos": "NOUN"})
        self.assertEqual(self.entry("headwords", "h", "husk"), {"a": 2, "x": False, "pos": ""})
        fly = self.entry("headwords", "f", "fly")
        self.assertEqual((fly["x"], fly["pos"]), (True, ""))
        self.assertGreaterEqual(fly["a"], 4)
        self.assertEqual(self.entry("tails", B.tail_key("hus"), "hus"), {"a": 1, "x": True, "pos": "NOUN"})

    def test_every_form_against_the_shards(self):
        heads, words = {}, {}
        for p in glob.glob(os.path.join(INDEX, "*.json")):
            s = _json(p)
            if isinstance(s, dict) and "heads" in s and not p.endswith("-top.json"):
                heads.update(s["heads"])
                words.update(s["words"])
        tr = set(_json(os.path.join(INDEX, "translated.json")))
        bad, n = [], 0
        for sub in ("headwords", "tails"):
            for p in glob.glob(os.path.join(INDEX, sub, "*.json")):
                d = _json(p)
                for i, w in enumerate(d["w"]):
                    ids = sorted(set(heads[w]))
                    k = d["k"][i]
                    pos = "" if k == "." else d["kc"][B.ROW_CODES.index(k)]
                    want_pos = (words[str(ids[0])][2] or "") if len(ids) == 1 else ""
                    got = (int(d["a"][i], 16), d["x"][i] == "1", pos)
                    want = (min(len(ids), 15), any(j in tr for j in ids), want_pos)
                    n += 1
                    if got != want:
                        bad.append((sub, w, got, want))
        self.assertGreater(n, 100000)
        self.assertEqual(bad[:10], [])

    def test_snip_rows_for_husk(self):
        snips = json.loads(_read(INDEX, "snip", B.snippet_key("husk") + ".json"))
        h = snips["_h"]["husk"]
        self.assertEqual([hg for _i, hg in h], [1, 2])
        for i, _hg in h:
            self.assertIn(str(i), snips)
        self.assertIsInstance(snips["_h"]["hus"], int)


#: shell.js + lookup.js in the stand-in page of test_ordpar_events104, over the built index
ROWS = r"""
const INDEX = %(index)s;
Object.defineProperty(N.prototype, 'ownerDocument', { get() { return document; } });
globalThis.ORDPAR_STRINGS = { en: JSON.parse(fs.readFileSync(%(strings)s, 'utf8')) };
function load(file) { (0, eval)(fs.readFileSync(file, 'utf8')); }
// favMark: a list row's heart, drawn since site decisions 158 made the list the default view of a
// one-article search that also finds an inflected form (*katt* below)
globalThis.ordparPersonal = { history: () => [], RECENT: 8, recordSearch() {}, setLabels() {},
  favMark: () => document.createElement('span') };
const LOADED = [];
load(%(lookup)s);
ordparLookup.setLoader(name => { LOADED.push(name); const p = path.join(INDEX, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; });
load(%(shell)s);
const main = document.createElement('main'); document.body.appendChild(main);
const results = document.createElement('div'); results.setAttribute('data-ordpar-results', ''); main.appendChild(results);
const wait = (ms) => new Promise(r => realSetTimeout(r, ms));
(async () => {
  await ordparShell.ready; await wait(30);
  const out = { searches: {} };
  const S = ordparShell.sideGlosses;
  out.rule = {
    someTranslated: S([{ hg: 1, translated: true, text: 'to fly', gloss: true },
                       { hg: 2, translated: false, text: 'flygende insekt' },
                       { hg: 3, translated: true, text: 'a plane', gloss: false }]),
    noneTranslated: S([{ hg: 1, translated: false, text: 'evne til å huske' },
                       { hg: 2, translated: false, text: 'huskende bevegelse' }]),
    translatedNoText: S([{ hg: 1, translated: true, text: '' }, { hg: 2, translated: false, text: 'norsk' }]),
    nothing: S([{ hg: 1, translated: false, text: '' }, { hg: 2, translated: false, text: '' }]),
  };
  for (const q of %(queries)s) {
    LOADED.length = 0;
    await ordparSearch.render(main, q, { record: false });
    await wait(150);
    const ul = main.querySelector('.ordpar-similar-list');
    out.searches[q] = {
      cls: ul ? ul.className : null,
      loaded: LOADED.slice(),
      own: ordparLookup.shardKey(ordparLookup.fold(q)) + '.json',
      rows: ul ? ul.querySelectorAll('a').map(a => ({
        word: (a.querySelector('.ordpar-option-word') || a).textContent, text: a.textContent,
        cls: a.className, lang: a.lang, href: a.href,
        pos: (a.querySelector('.ordpar-pos') || { textContent: '' }).textContent,
        side: (a.querySelector('.ordpar-option-side') || { textContent: '' }).textContent,
        nbList: !!a.querySelector('.ordpar-option-nblist'),
        pending: !!a.querySelector('.is-pending') })) : [],
    };
  }
  process.stdout.write('\n' + JSON.stringify(out));
  process.exit(0);
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
"""


@unittest.skipUnless(BUILT and RUNNER, "no build, or neither bun nor node")
class TheRowsOverTheBuiltIndex(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from test_ordpar_events104 import FAKE_DOM
        script = (FAKE_DOM + ROWS) % {
            "receiver": json.dumps("https://receiver.test/e"), "index": json.dumps(INDEX), "strings": json.dumps(os.path.join(SITE, "strings", "en.json")),
            "lookup": json.dumps(os.path.join(SITE, "lookup.js")),
            "shell": json.dumps(os.path.join(SITE, "shell.js")),
            "queries": json.dumps(["husx", "flyy", "spisee", "kjøppte", "katt"], ensure_ascii=False)}
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "t.js")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(script)
            res = subprocess.run([RUNNER, path], capture_output=True, timeout=180)
            out = res.stdout.decode("utf-8", "replace")
            if res.returncode != 0:
                raise AssertionError("JS failed:\n" + out + res.stderr.decode("utf-8", "replace"))
            cls.out = json.loads(out.strip().splitlines()[-1])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def rows(self, q):
        return {r["word"]: r for r in self.out["searches"][q]["rows"]}

    def test_the_rule(self):
        r = self.out["rule"]
        self.assertEqual([(x["hg"], x["text"], x["lang"]) for x in r["someTranslated"]],
                         [(1, "to fly", "en"), (3, "a plane", "en")])
        self.assertEqual([(x["hg"], x["text"], x["lang"]) for x in r["noneTranslated"]],
                         [(1, "evne til å huske", "nb"), (2, "huskende bevegelse", "nb")])
        self.assertEqual(r["translatedNoText"], [])            # never Norwegian beside English
        self.assertEqual(r["nothing"], [])

    def test_rows_on_a_miss(self):
        for q in ("husx", "flyy", "spisee", "kjøppte"):
            s = self.out["searches"][q]
            self.assertIn("ordpar-similar-rows", s["cls"].split(), q)
            for r in s["rows"]:
                self.assertIn("ordpar-option", r["cls"].split(), (q, r))
                self.assertEqual(r["lang"], "", (q, r))
                self.assertFalse(r["pending"], (q, r))
                self.assertTrue(r["href"].startswith("/bm-en/"), (q, r))

    def test_husx(self):
        rows = self.rows("husx")
        self.assertEqual(list(rows)[:4], ["hus", "husk", "huse", "husj"])
        self.assertEqual(rows["hus"]["pos"], "noun")
        self.assertIn("is-translated", rows["hus"]["cls"].split())
        self.assertTrue(rows["husk"]["nbList"])
        self.assertTrue(rows["husk"]["side"].startswith("I"), rows["husk"])
        self.assertIn("II", rows["husk"]["side"])
        self.assertNotIn("articles", rows["husk"]["side"])
        self.assertNotIn("is-translated", rows["husk"]["cls"].split())
        self.assertEqual(rows["huse"]["pos"], "verb")

    def test_flyy(self):
        fly = self.rows("flyy")["fly"]
        self.assertEqual(fly["pos"], "")
        self.assertIn("is-translated", fly["cls"].split())
        self.assertFalse(fly["nbList"])
        self.assertIn("more", fly["side"])

    def test_the_inflected_form(self):
        row = self.rows("kjøppte")["kjøpte"]
        self.assertIn("ordpar-similar-form", row["cls"].split())
        self.assertIn("inflected form of", row["side"])
        self.assertIn("kjøpe", row["side"])

    def test_a_hit_keeps_the_bare_list(self):
        s = self.out["searches"]["katt"]
        self.assertEqual(s["cls"], "ordpar-similar-list")
        self.assertTrue(s["rows"])
        for r in s["rows"]:
            self.assertEqual(r["text"], r["word"])
            self.assertEqual(r["lang"], "nb")
            self.assertNotIn("ordpar-option", r["cls"].split())

    def test_a_miss_loads_no_shard_but_its_own(self):
        for q in ("husx", "flyy", "spisee", "kjøppte"):
            s = self.out["searches"][q]
            shards = {f for f in s["loaded"] if "/" not in f
                      and f not in ("translated.json", "labels.json", "random.json", "index.json")}
            self.assertLessEqual(shards, {s["own"]}, (q, s["loaded"]))
            self.assertTrue(any(f.startswith("snip/") for f in s["loaded"]), q)


if __name__ == "__main__":
    unittest.main()
