# -*- coding: utf-8 -*-
"""Decisions 184: no comment in the exported files that only the private papers explain.

The public repository carries the site's code and tests (decisions 184). A reader of it has the
public decision log `docs/decisions.md` and its glossary, which explain "decisions N", "Robin,
<date>", "brief N" and "build B"; they do not have the private log with the rulings' words, nor the
privacy review's finding numbers, nor the review that numbered its points. So, pinned here over
every text file the export takes (`export_public.ordpar_files()` and `export_public.PIPELINE`, the
same list the export reads; outside a git checkout, every file under `ordpar/` it would keep):

* no quotation of a ruling: Robin's name, within a few words (and across a comment's line break),
  followed by quoted words, the shape "Robin, <date>: <quoted words>" or "(Robin: <quoted
  words>)". The decision number says where the ruling is; the comment says in plain words what it
  means for the code;
* no privacy-review finding label: "104" and "R" with the finding's number, as "(104, R4)" or
  "104 (R11)", or the label alone in brackets or before a colon;
* no "A13 point N", the numbered points of a private review.

This file, which spells the labels out, is passed over. A legitimate text that trips the pattern goes in `ALLOWED` with its reason. Stdlib unittest.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ORDPAR)

import export_public  # noqa: E402  -- the export's own list of files

#: the name, built in two parts so this file does not match its own pattern
NAME = "Rob" + "in"
#: between the name and the quote: up to 40 characters with no full stop, semicolon or closing
#: bracket (a sentence or a bracket that ends first means the quote is not his), a line break
#: followed by a comment's leader counting as a space
GAP = r'(?:[^"“\n.;)]|\n[ \t]*(?:\*|#:?|//|--)?)'
QUOTATION = re.compile(r"\b" + NAME + r"\b" + GAP + r'{0,40}?["“]')
#: the privacy review's findings R1-R12 as the code cited them: "(104, R4)", "104 (R11)", "104 R4",
#: a bare "(R12)" or "R5:" (not "R2" alone, which is also Cloudflare's storage)
REVIEW_LABEL = re.compile(r"\b104,? \(?" + r"R\d{1,2}\b|\((?:" + r"R\d{1,2}(?:, )?)+\)|\b" + r"R\d{1,2}:")
POINT_LABEL = re.compile(r"\bA13 " + r"point\b")

#: this file, which names the labels it looks for, is passed over
SELF = "ordpar/tests/test_ordpar_labels184.py"
#: (path, the text of the line) let through, each with its reason
ALLOWED = {
    ('ordbok_gen.py', '/* Touch, on the article surface: no peek (' + NAME + ', 2026-09-29: the inline gloss looked "ugly";'):
        "inside the deck's card CSS, which every built card carries: a change rebuilds every card's bytes",
    ('ordpar/coming.md', 'items the session\'s call at ' + NAME + '\'s delegation, the fifth ("More example sentences") his ruling;'):
        "the quoted words are the item's title, not a ruling",
    ('ordpar/tests/test_ordpar_about63.py', 'ENGLISH_184 = ("The English is written with AI (Claude, by Anthropic) under ' + NAME + ' Fauskanger\'s direction and "'):
        "the About page's own sentence, which the test pins",
    ('ordpar/tests/test_ordpar_browser_survey173.py', 'self.assertTrue(pg["intro"][1].startswith("Your answers are stored by Ordpar (see Privacy) and read by ' + NAME + '"))'):
        "the survey page's own words, which the test pins",
    ('ordpar/tests/test_ordpar_defaults174.py', "# site decisions 187: the level box's clause; 188: the set phrases' order, a draft for " + NAME):
        "a comment naming no words of his; the quote is the next line's string",
    ('ordpar/tests/test_ordpar_presets136.py', "# site decisions 187: the level box's clause; 188: the set phrases' order, a draft for " + NAME):
        "a comment naming no words of his; the quote is the next line's string",
    ('ordpar/tests/test_ordpar_privacy104.py', 'self.assertIn("' + NAME + ' Fauskanger is responsible for this data", body)'):
        "the privacy page's own words, which the test pins",
    ('ordpar/tests/test_ordpar_search128.py', 'self.assertEqual(png, f.read(), "the picture is ' + NAME + '\'s file, as is")'):
        "an assertion's message",
    ('ordpar/tests/test_ordpar_spelling55.py', 'self.assertIn("' + NAME + '", open(B.OVERRIDES_PATH, encoding="utf-8").read().split("form\\tband")[0])'):
        "an assertion on the overrides file's header",
    ('ordpar/tests/test_ordpar_wordpages117.py', 'self.assertNotIn("' + NAME + '", out)'):
        'an assertion that the name is NOT in the output',
    ('ordpar/tests/test_ordpar_wordpages117.py', 'self.assertNotIn("' + NAME + '", t, path)'):
        'an assertion that the name is NOT in the output',
    ('scripts/derive.py', "# article in the library): drafted on the table's own pattern, for " + NAME + "'s word"):
        "a comment naming no words of his; the quote is the next line's dict key",
}


def exported():
    """The text files the export takes from this tree, as repository paths."""
    try:
        tracked, untracked = export_public.ordpar_files()
        paths = tracked + untracked
    except SystemExit:                  # no git here: walk ordpar/ as the export would keep it
        paths = []
        for base, dirs, names in os.walk(ORDPAR):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".wrangler")]
            for n in names:
                rel = os.path.relpath(os.path.join(base, n), ROOT).replace("\\", "/")
                if (rel not in export_public.WORKING_DOCS and not export_public.is_rationale(rel)
                        and not rel.startswith(export_public.NEVER)):
                    paths.append(rel)
    paths += [p for p in export_public.PIPELINE if os.path.exists(os.path.join(ROOT, p))]
    return sorted(p for p in set(paths) if export_public.is_text(p) and p != SELF)


def hits(pattern):
    out = []
    for rel in exported():
        try:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        for m in pattern.finditer(text):
            n = text.count("\n", 0, m.start()) + 1
            line = lines[n - 1].strip() if n <= len(lines) else ""
            if (rel, line) not in ALLOWED:
                out.append("%s:%d: %s" % (rel, n, line[:160]))
    return out


class Labels(unittest.TestCase):
    def test_the_list_is_the_exports(self):
        files = exported()
        self.assertIn("ordpar/export_public.py", files)
        self.assertIn("ordbok_gen.py", files)
        self.assertFalse([p for p in files if p in export_public.WORKING_DOCS])

    def test_no_quotation_of_a_ruling(self):
        found = hits(QUOTATION)
        self.assertEqual(found, [], "%d quotation(s) of a ruling; cite the decision number and say "
                         "it in plain words:\n%s" % (len(found), "\n".join(found)))

    def test_no_review_finding_label(self):
        found = hits(REVIEW_LABEL)
        self.assertEqual(found, [], "%d privacy-review label(s); write decisions 104:\n%s"
                         % (len(found), "\n".join(found)))

    def test_no_point_label(self):
        found = hits(POINT_LABEL)
        self.assertEqual(found, [], "%d private review point label(s):\n%s"
                         % (len(found), "\n".join(found)))

    def test_the_patterns(self):
        q = lambda s: bool(QUOTATION.search(s))
        self.assertTrue(q("(site decisions 166, " + NAME + ' 2026-11-05: "Our own receiver")'))
        self.assertTrue(q("(" + NAME + ': "Yes, drop it")'))
        self.assertTrue(q("// (" + NAME + ', 2026-10-29:\n// "the switch is remembered")'))
        self.assertFalse(q("(decisions 178, " + NAME + ', 2026-11-08). Every "## " heading'))
        self.assertFalse(q("(site decisions 175, " + NAME + ', 2026-11-07): "What\'s new", the page'))
        for s in ("(104, " + "R7)", "104 (" + "R11)", "104 " + "R4", "(" + "R2)", "# " + "R5: true"):
            self.assertTrue(REVIEW_LABEL.search(s), s)
        self.assertFalse(REVIEW_LABEL.search("from the private R2 bucket"))
        self.assertTrue(POINT_LABEL.search("A13 " + "point 3"))


if __name__ == "__main__":
    unittest.main()
