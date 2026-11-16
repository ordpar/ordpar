# -*- coding: utf-8 -*-
"""Site decisions 171 (Robin, 2026-11-06): the line under "Could not find …" when a search finds nothing.

The old line's "it may be ... an article whose translation we have not reached yet" was not true: every
article is on Ordpar, translated or not. So, as ordbokene's own page for a missing word
(ordbokene.no/nob/about/missing-word), the line points onward to NAOB and Norsk Ordbok, in wording A (2026-11-06).

* **The words** (`site/strings/en.json` `results.noneWhy`): exactly as approved, with `{naob}` and `{norskOrdbok}`
  where the two names go, the names themselves `results.naob` and `results.norskOrdbok`; the untrue reason gone.
* **The links** (`site/lookup.js` `missWhy`): each placeholder becomes a link to that dictionary's search for the
  reader's word — NAOB `https://naob.no/s%C3%B8k/<word>` (the lookup of 2026-11-06), Norsk Ordbok
  `https://norsk-ordbok.no/nno/no/<word>` (Robin's look) — the word through `encodeURIComponent`, in a new tab,
  `noopener nofollow`; the line drawn by `missWhy`, never as plain `t('results.noneWhy')` (which would show the
  braces).

Fails on 2322bf680's strings and `lookup.js` (the old line; no `missWhy`): 2 failures, 1 error.
"""
import io
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDPAR = os.path.dirname(HERE)

APPROVED = ("It may be a misspelling or a compound. Try the larger dictionaries {naob} (for Bokmål) and "
            "{norskOrdbok} (for dialect words and Nynorsk), both in Norwegian.")


def _read(*p):
    with io.open(os.path.join(ORDPAR, *p), encoding="utf-8") as f:
        return f.read()


class TheWords(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads(_read("site", "strings", "en.json"))

    def test_the_line_as_approved(self):
        self.assertEqual(self.s["results.noneWhy"], APPROVED)
        self.assertEqual(self.s["results.naob"], "NAOB")
        self.assertEqual(self.s["results.norskOrdbok"], "Norsk Ordbok")

    def test_the_untrue_reason_gone(self):
        self.assertNotIn("not reached yet", json.dumps(self.s, ensure_ascii=False))


class TheLinks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = _read("site", "lookup.js")
        start = cls.js.index("function missWhy(")
        cls.fn = cls.js[cls.js.index("var MISS_LINKS"):cls.js.index("\n  }\n", start)]

    def test_drawn_by_misswhy_only(self):
        self.assertIn("miss.appendChild(missWhy(g.query));", self.js)
        self.assertNotIn("t('results.noneWhy'))", self.js.replace("t('results.noneWhy').split", ""))

    def test_every_placeholder_is_a_link(self):
        names = set(re.findall(r"\{(\w+)\}", APPROVED))
        self.assertEqual(names, {"naob", "norskOrdbok"})
        for n in names:
            self.assertRegex(self.fn, r"\b%s: \['results\.%s', 'https://" % (n, n))

    def test_the_addresses(self):
        self.assertIn("'https://naob.no/s%C3%B8k/'", self.fn)
        self.assertIn("'https://norsk-ordbok.no/nno/no/'", self.fn)
        self.assertIn("encodeURIComponent(String(q || '').trim())", self.fn)
        self.assertIn("a.target = '_blank';", self.fn)
        self.assertIn("a.rel = 'noopener nofollow';", self.fn)
        self.assertNotIn("innerHTML", self.fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
