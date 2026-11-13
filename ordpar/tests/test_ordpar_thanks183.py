# -*- coding: utf-8 -*-
"""Site decisions 183 (Robin, 2026-11-11): readers' ideas as a second section of `/thanks/`. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-thanks-ideas-build-183-2026-11-11.md`.

* **The words** (`ordpar/thanks.md`, approved): the new opening paragraph, a `Corrections` heading
  over the counts and the fixes, an `Ideas from our readers` heading over the ideas — that heading
  and its list left out entirely while the ideas file has no entry.
* **An idea's entry**: a list item in the same `ordpar-thanks-list` class as the fixes; the title in
  bold with its colon, a space, the text; then, in a span `ordpar-thanks-credit` (no `<br>`), `Suggested by <names>` ("Kari", "Kari
  and Ola", "Kari, Ola and Per"), or `Suggested by a reader` with no names; `<` and `&` escaped in
  title, text and name. Newest first, by `(date, idea)` descending.
* **The file** (`ordpar/reader-ideas.jsonl`, kept by hand): committed, valid and holding the Moomoo
  entry; each kind of bad line refused with the file and line named; missing or empty, no ideas;
  `ORDPAR_IDEAS_FILE` names another.
* **The build**: `build_site.write_thanks` writes a page with the section.
* **The credit's look** (Robin's pick in the credit lab, 2026-11-11, `style-lab/credit.html`): the
  page sheet sets the span as a line of its own, italic, led by an en dash drawn by CSS. Failed on
  54378b082's code (6 failures: the `<br>` form, no rule in `page.PAGE_CSS`).

Stdlib unittest, no network; builds only into a temporary folder.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)
ROOT = os.path.dirname(ORDPAR)
sys.path.insert(0, ROOT)
from ordpar.sitegen import thanks, page, chrome  # noqa: E402
from ordpar import build_site  # noqa: E402

OPENING = ("Readers help us in two ways: by telling us about mistakes in the articles, and with ideas "
           "for making the dictionary or the Anki deck better. Here we list the mistakes we have "
           "corrected and the ideas we have taken up or plan to. We name a reader only if they asked "
           "us to.")
MOOMOO = {"idea": 1, "date": "2026-11-11", "title": "A second hint on the Anki cards",
          "text": "after the Hint shows an example sentence, a second button shows the whole sentence "
                  "in the other language, with the word you are practising left blank, so you can see "
                  "what the other words in the example mean. In the decks since their update of 11 "
                  "November.",
          "names": ["Moomoo"]}
#: Moomoo's report (Robin, 2026-11-11, relayed by the deck session; the entry approved: "looks good")
REPORT = {"idea": 2, "date": "2026-11-11", "title": "A note on words with more than one card",
          "text": "a card's front now says when its spelling also has a card as another word class, "
                  "such as “Also in this deck as: adverb, interjection”, after a reader found "
                  "such cards hard to tell apart. In the decks since their update of 11 November.",
          "names": ["Moomoo"], "credit": "reported"}
WORDS = {1000: "lek III"}
FIX = {"fix": 1, "date": "2026-11-05", "article": 1000, "reports": [4], "names": []}


def _idea(n, date, title="T", text="x", names=()):
    return {"idea": n, "date": date, "title": title, "text": text, "names": list(names)}


@contextlib.contextmanager
def ideas_file(lines):
    """`ORDPAR_IDEAS_FILE` pointed at a temporary file holding `lines` (objects or raw strings)."""
    d = tempfile.mkdtemp(prefix="ordpar-ideas183-")
    path = os.path.join(d, "reader-ideas.jsonl")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write((line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)) + "\n")
    before = os.environ.get("ORDPAR_IDEAS_FILE")
    os.environ["ORDPAR_IDEAS_FILE"] = path
    try:
        yield path
    finally:
        if before is None:
            os.environ.pop("ORDPAR_IDEAS_FILE", None)
        else:
            os.environ["ORDPAR_IDEAS_FILE"] = before
        shutil.rmtree(d)


class Words(unittest.TestCase):

    def test_opening_and_corrections_heading(self):
        _t, body = thanks.page([FIX], WORDS.get, ideas=[])
        self.assertIn("<p>%s</p>" % OPENING, body)
        self.assertNotIn("When a reader tells us about a mistake", body)
        self.assertIn("<h2>Corrections</h2>\n<p>Thanks to 1 report that led to 1 fix.</p>", body)
        self.assertLess(body.index("<p>Readers help us"), body.index("<h2>Corrections</h2>"))

    def test_no_ideas_no_section(self):
        _t, body = thanks.page([FIX], WORDS.get, ideas=[])
        self.assertNotIn("Ideas from our readers", body)
        self.assertNotIn("{ideas}", body)
        self.assertNotIn("[if", body)
        self.assertEqual(body.count('<ul class="ordpar-thanks-list">'), 1)

    def test_no_ideas_and_no_fixes(self):
        _t, body = thanks.page([], WORDS.get, ideas=[])
        self.assertIn("<h2>Corrections</h2>\n<p>No report has led to a fix yet.</p>", body)
        self.assertTrue(body.rstrip().endswith("<p>No report has led to a fix yet.</p>"), body)

    def test_ideas_section_after_corrections(self):
        _t, body = thanks.page([FIX], WORDS.get, ideas=[MOOMOO])
        self.assertIn("<h2>Ideas from our readers</h2>\n<ul class=\"ordpar-thanks-list ordpar-thanks-ideas\">", body)
        self.assertLess(body.index("<h2>Corrections</h2>"), body.index("<h2>Ideas from our readers</h2>"))
        self.assertEqual(body.count('<ul class="ordpar-thanks-list'), 2)

    def test_empty_ideas_file_no_section(self):
        with ideas_file([]):
            self.assertEqual(thanks.read_ideas(), [])
            _t, body = thanks.page([FIX], WORDS.get, ideas=thanks.read_ideas())
        self.assertNotIn("Ideas from our readers", body)

    def test_ideas_file_read(self):
        with ideas_file([MOOMOO]):
            _t, body = thanks.page([FIX], WORDS.get, ideas=thanks.read_ideas())
        self.assertIn("<h2>Ideas from our readers</h2>", body)
        self.assertIn("A second hint on the Anki cards", body)

    def test_no_ideas_given_none_shown(self):
        # as `fixes`, the ideas are the caller's: `page` reads no file (`write_thanks` does)
        _t, body = thanks.page([FIX], WORDS.get)
        self.assertNotIn("Ideas from our readers", body)

    def test_missing_file_no_ideas(self):
        with ideas_file([]) as path:
            os.remove(path)
            self.assertEqual(thanks.read_ideas(), [])


class Entry(unittest.TestCase):

    def test_moomoo(self):
        self.assertEqual(
            thanks.ideas_html([MOOMOO]),
            '<ul class="ordpar-thanks-list ordpar-thanks-ideas">\n'
            "<li><strong>A second hint on the Anki cards:</strong> after the Hint shows an example "
            "sentence, a second button shows the whole sentence in the other language, with the word "
            "you are practising left blank, so you can see what the other words in the example mean. "
            "In the decks since their update of 11 November. "
            "<span class=\"ordpar-thanks-credit\">Suggested by Moomoo</span></li>\n"
            "</ul>")

    def test_names_joined(self):
        def credit(names):
            return thanks.ideas_html([_idea(1, "2026-11-11", names=names)])
        self.assertIn("<span class=\"ordpar-thanks-credit\">Suggested by Kari</span></li>", credit(["Kari"]))
        self.assertIn("<span class=\"ordpar-thanks-credit\">Suggested by Kari and Ola</span></li>", credit(["Kari", "Ola"]))
        self.assertIn("<span class=\"ordpar-thanks-credit\">Suggested by Kari, Ola and Per</span></li>", credit(["Kari", "Ola", "Per"]))
        self.assertIn("<span class=\"ordpar-thanks-credit\">Suggested by a reader</span></li>", credit([]))

    def test_escaped(self):
        h = thanks.ideas_html([_idea(1, "2026-11-11", title="A <b> & B", text="x < y & z",
                                     names=["<i>Kari</i> & Co"])])
        self.assertIn("<strong>A &lt;b&gt; &amp; B:</strong> x &lt; y &amp; z", h)
        self.assertIn("Suggested by &lt;i&gt;Kari&lt;/i&gt; &amp; Co</span></li>", h)
        self.assertNotIn("<b>", h)
        self.assertNotIn("<i>", h)

    def test_newest_first(self):
        ideas = [_idea(1, "2026-11-01", "one"), _idea(2, "2026-11-11", "two"),
                 _idea(3, "2026-11-01", "three"), _idea(4, "2026-11-05", "four")]
        h = thanks.ideas_html(ideas)
        order = [h.index("<strong>%s:" % t) for t in ("two", "four", "three", "one")]
        self.assertEqual(order, sorted(order))

    def test_none_empty(self):
        self.assertEqual(thanks.ideas_html([]), "")


class File(unittest.TestCase):

    def test_committed_valid_with_moomoo(self):
        path = os.path.join(ORDPAR, "reader-ideas.jsonl")
        self.assertTrue(os.path.exists(path))
        self.assertEqual(thanks.IDEAS_PATH, path)
        ideas = thanks.read_ideas(path)
        self.assertIn(MOOMOO, ideas)
        with io.open(path, encoding="utf-8") as f:
            first = f.read().splitlines()[0]
        self.assertEqual(json.loads(first), MOOMOO)
        self.assertIn(REPORT, ideas)

    def test_good_file_read(self):
        with ideas_file([MOOMOO, "", _idea(2, "2026-11-12", names=[])]):
            self.assertEqual([i["idea"] for i in thanks.read_ideas()], [1, 2])

    def test_bad_lines_refused(self):
        good = dict(MOOMOO)
        bad = {
            "not JSON": "{not json",
            "not an object": "[1, 2]",
            "idea zero": dict(good, idea=0),
            "idea not a number": dict(good, idea="1"),
            "idea a bool": dict(good, idea=True),
            "no date": {k: v for k, v in good.items() if k != "date"},
            "bad date": dict(good, date="11.11.2026"),
            "impossible date": dict(good, date="2026-02-30"),
            "empty title": dict(good, title=""),
            "blank title": dict(good, title="   "),
            "title not a string": dict(good, title=5),
            "empty text": dict(good, text=""),
            "text not a string": dict(good, text=None),
            "names not a list": dict(good, names="Moomoo"),
            "a link as a name": dict(good, names=["www.example.com"]),
            "a name too long": dict(good, names=["x" * (thanks.MAX_NAME + 1)]),
            "an empty name": dict(good, names=[""]),
            "an other key": dict(good, url="x"),
        }
        for what, line in bad.items():
            with self.subTest(what), ideas_file([MOOMOO if what != "not JSON" else _idea(9, "2026-11-01"),
                                                 line]):
                with self.assertRaises(ValueError) as cm:
                    thanks.read_ideas()
                self.assertIn("reader-ideas.jsonl line 2", str(cm.exception))

    def test_idea_number_twice(self):
        with ideas_file([MOOMOO, _idea(1, "2026-11-12")]):
            with self.assertRaises(ValueError) as cm:
                thanks.read_ideas()
        self.assertIn("reader-ideas.jsonl line 2", str(cm.exception))
        self.assertIn("twice", str(cm.exception))

    def test_bad_file_fails_the_build(self):
        before = chrome.REPORT_RECEIVER
        out = tempfile.mkdtemp(prefix="ordpar-thanks183-")
        try:
            Build._switch(None, "http://192.168.0.100:8787/report")
            with ideas_file(["{nope"]):
                with self.assertRaises(ValueError) as cm:
                    build_site.write_thanks(out, "ordpar build: test", _Mirror(), [FIX])
            self.assertIn("reader-ideas.jsonl line 1", str(cm.exception))
        finally:
            Build._switch(None, before)
            shutil.rmtree(out)


class _Mirror:
    def data(self, aid):
        return {1000: {"lemmas": [{"lemma": "lek", "hgno": 3}]}}.get(aid)


class Build(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="ordpar-thanks183-")
        self.before = chrome.REPORT_RECEIVER

    def tearDown(self):
        shutil.rmtree(self.out)
        self._switch(self.before)

    def _switch(self, address):
        setter = getattr(page, "set_report_receiver", None)
        if setter:
            setter(address)
        else:
            chrome.REPORT_RECEIVER = address

    def _built(self):
        with io.open(os.path.join(self.out, "thanks", "index.html"), encoding="utf-8") as f:
            return f.read()

    def test_write_thanks_with_the_section(self):
        self._switch("http://192.168.0.100:8787/report")
        self.assertEqual(build_site.write_thanks(self.out, "ordpar build: test", _Mirror(), [FIX],
                                                 ideas=[MOOMOO]), "written")
        html = self._built()
        self.assertIn("<h2>Ideas from our readers</h2>", html)
        self.assertIn("<strong>A second hint on the Anki cards:</strong>", html)
        self.assertIn("<span class=\"ordpar-thanks-credit\">Suggested by Moomoo</span></li>", html)
        self.assertIn("<h2>Corrections</h2>", html)

    def test_write_thanks_reads_the_ideas_file(self):
        self._switch("http://192.168.0.100:8787/report")
        with ideas_file([_idea(1, "2026-11-11", "From the file")]):
            build_site.write_thanks(self.out, "ordpar build: test", _Mirror(), [FIX])
        self.assertIn("<strong>From the file:</strong>", self._built())

    def test_thanks_page_passes_ideas(self):
        h = page.thanks_page("ordpar build: test", page.EN, [FIX], WORDS.get, ideas=[])
        self.assertNotIn("Ideas from our readers", h)
        h = page.thanks_page("ordpar build: test", page.EN, [FIX], WORDS.get, ideas=[MOOMOO])
        self.assertIn("Ideas from our readers", h)


class CreditLook(unittest.TestCase):
    """Robin's pick in the credit lab (2026-11-11, `style-lab/credit.html`): the credit a line of
    its own, italic, the body colour, led by an en dash drawn by CSS, so the stored words stay
    "Suggested by …"; no `<br>` in the entry."""

    def test_the_sheet(self):
        from ordpar.sitegen import page
        self.assertIn(".ordpar-thanks-credit{display:block;font-style:italic}", page.PAGE_CSS)
        self.assertIn('.ordpar-thanks-credit::before{content:"\\2013\\00a0"}', page.PAGE_CSS)

    def test_space_between_ideas(self):
        """Robin, 2026-11-11, "Yes, add the space": half a line between ideas; the fixes' one-line
        rows unchanged."""
        from ordpar.sitegen import page
        self.assertIn(".ordpar-thanks-ideas>li+li{margin-top:.5em}", page.PAGE_CSS)
        self.assertIn('<ul class="ordpar-thanks-list ordpar-thanks-ideas">', thanks.ideas_html([MOOMOO]))

    def test_no_line_break_in_the_entry(self):
        self.assertNotIn("<br>", thanks.ideas_html([MOOMOO]))


class Credit(unittest.TestCase):
    """Moomoo's report credit (Robin, 2026-11-11): an idea's optional `credit`, "suggested" (the
    default, the key left out) or "reported", says "Suggested by" or "Reported by"."""

    def test_reported(self):
        self.assertIn('<span class="ordpar-thanks-credit">Reported by Moomoo</span></li>',
                      thanks.ideas_html([REPORT]))

    def test_default_and_explicit_suggested(self):
        self.assertIn(">Suggested by Moomoo</span>", thanks.ideas_html([MOOMOO]))
        self.assertIn(">Suggested by Moomoo</span>", thanks.ideas_html([dict(MOOMOO, credit="suggested")]))

    def test_reported_without_names(self):
        self.assertIn(">Reported by a reader</span>", thanks.ideas_html([dict(REPORT, names=[])]))

    def test_bad_credit_refused(self):
        for bad in ("Reported", "fixed", "", 1, None):
            with self.assertRaises(ValueError):
                thanks.check_idea(dict(REPORT, credit=bad))

    def test_report_above_the_idea(self):
        h = thanks.ideas_html([MOOMOO, REPORT])
        self.assertLess(h.index("A note on words"), h.index("A second hint"))


if __name__ == "__main__":
    unittest.main()
