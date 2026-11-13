# -*- coding: utf-8 -*-
"""Site-review decisions 112 (Robin, 2026-10-23): how many examples show under each sense — the
settings' table, the words, the head script, the sheet and the page script. Brief:
`docs/sessions/2026-09-19-ordpar-site-review/evidence/brief-examples-limit-optout-phone-112-104-113-2026-10-24.md` § 1.
Stdlib unittest, pure Python.

What it pins:

* **The settings.** `exlimit` (All, then 1 to 10; All the default and first, 107), a drop-down
  (`control: 'select'`), in Settings -> Article -> Language right after Examples (111); `exmore`
  (On, the default and first / Off) after it. Both kept by the shell as classes on <html>
  (`ordpar-exlimit-<n>`, `ordpar-exmore-off`), set by the head script before the first paint,
  carried by an export, reset with every setting.
* **The words.** Each label, choice and hint one string in `site/strings/en.json` (99's "?" box);
  the line's own words, Robin's "Show N more examples", singular for one, in `strings.py` beside
  the page script's other words ("Show English", "Example").
* **The sheet.** One rule per limit, cutting a list past its first n items outside a mini (the minis
  keep `mini.js` EX_BUDGET), never the line itself, never an opened list; the line hidden by
  `exmore = off` and with no limit; the line's button in the "Show English" cue's look.
* **The page script.** `exmore` puts the line under every cut list from `ordparDefs` (so a search
  result, a list or favourites row and a setting changed in place get it), and a click on it opens
  the list in place.

The browser side (every place, the line opened, the reveal of 111 on the opened ones, the settings
page): `test_ordpar_browser_exlimit112.py`.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
SITE = os.path.join(ROOT, "ordpar", "site")

from ordpar.sitegen import head, page, strings as strings_mod  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class TheSettings(unittest.TestCase):
    js = _read(SITE, "shell.js")

    def test_the_entries(self):
        self.assertIn("{ key: 'exlimit', values: ['all', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], "
                      "def: 'all', section: 'article', sub: 'language', control: 'select' }", self.js)
        self.assertIn("{ key: 'exmore', values: ['on', 'off'], def: 'on', section: 'article', sub: 'language' }",
                      self.js)

    def test_after_examples(self):
        order = re.findall(r"\{ key: '(\w+)'", self.js)
        i = order.index("examples")
        # since site decisions 131 (2026-10-26) the eye's setting, `exeye`, sits right under
        # Examples, before the limit
        self.assertEqual(order[i:i + 4], ["examples", "exeye", "exlimit", "exmore"])

    def test_classes_on_html(self):
        keys = self.js.split("var CLASS_KEYS = [")[1].split("];")[0]
        self.assertIn("'exlimit', 'exmore'", keys)
        self.assertIn("SPEC.exlimit.values.forEach(function (v) { if (v !== 'all') { "
                      "cl.toggle('ordpar-exlimit-' + v, v === lim); } });", self.js)
        self.assertIn("cl.toggle('ordpar-exmore-off', getSetting('exmore') === 'off');", self.js)

    def test_the_head_script_before_the_first_paint(self):
        self.assertIn("f=s.getItem('exlimit');/^(?:[1-9]|10)$/.test(f)&&c.add('ordpar-exlimit-'+f);", head.THEME_JS)
        self.assertIn("s.getItem('exmore')==='off'&&c.add('ordpar-exmore-off')", head.THEME_JS)

    def test_the_export_carries_them(self):
        keys = re.search(r"var SETTING_KEYS = \[([^\]]*)\]", _read(SITE, "personal.js")).group(1)
        for k in ("exlimit", "exmore", "stats"):
            self.assertIn("'%s'" % k, keys)

    def test_the_settings_page_draws_a_drop_down(self):
        js = _read(SITE, "settings.js")
        self.assertIn("if (sp.control === 'select') {", js)
        self.assertIn("select.setAttribute('data-key', sp.key);", js)
        self.assertIn("select.addEventListener('change', function () { shell().setSetting(sp.key, select.value); });", js)
        # a number is its own label; the line's setting hidden while the limit is All
        self.assertIn("/^\\d+$/.test(v) && t(key) === key ? v : t(key)", js)
        self.assertIn("if (sp.key === 'exmore') { return sh.getSetting('exlimit') !== 'all'; }", js)
        self.assertIn("select.value = sh.getSetting(select.getAttribute('data-key'));", js)


class TheWords(unittest.TestCase):
    s = json.loads(_read(SITE, "strings", "en.json"))

    def test_labels_choices_and_hints(self):
        s = self.s
        self.assertEqual(s["settings.exlimit"], "Examples under each sense and set phrase")   # 126
        self.assertEqual(s["settings.exlimit.all"], "All")
        self.assertTrue(s["settings.exlimit.hint"])
        self.assertEqual((s["settings.exmore"], s["settings.exmore.on"], s["settings.exmore.off"]),
                         ("A line to show the examples left out", "On", "Off"))   # 126
        self.assertIn('"Show 12 more examples"', s["settings.exmore.hint"])
        for n in range(1, 11):          # the numbers are their own labels
            self.assertNotIn("settings.exlimit.%d" % n, s)

    def test_the_line_robins_words(self):
        self.assertEqual(strings_mod.EN["examples_more"], "Show {n} more examples")
        self.assertEqual(strings_mod.EN["examples_more_one"], "Show 1 more example")
        self.assertIn('MORE={"one": "Show 1 more example", "many": "Show {n} more examples"}', page.PAGE_JS)


class TheSheet(unittest.TestCase):
    css = page.SITE_CSS

    def test_one_rule_per_limit(self):
        for n in range(1, 11):
            self.assertIn("html.ordpar-exlimit-%d .ordbok-ex-list:where(:not(.ordbok-xmini *)):not(.ordpar-exopen)>"
                          "li:nth-child(n+%d):not(.ordpar-exmore){display:none}" % (n, n + 1), self.css)
        self.assertNotIn("ordpar-exlimit-11", self.css)
        self.assertNotIn("@EXLIMIT@", self.css)

    def test_the_line(self):
        self.assertIn("html.ordpar-exmore-off .ordbok-ex-list>li.ordpar-exmore,\n"
                      "html:not([class*=\"ordpar-exlimit-\"]) .ordbok-ex-list>li.ordpar-exmore{display:none}", self.css)
        self.assertIn(".ordpar-exbtn{font-family:inherit;background:none;cursor:pointer}", self.css)

    def test_in_the_shipped_sheet(self):
        self.assertIn("ordpar-exlimit-10", page.article_css())


class ThePageScript(unittest.TestCase):
    js = page.PAGE_JS

    def test_the_line_under_each_cut_list(self):
        self.assertIn("function exmore(r){", self.js)
        self.assertIn("if(u.closest('.ordbok-xmini'))continue;", self.js)          # never in a mini
        self.assertIn("bt.type='button';bt.className='ordbok-cue ordpar-exbtn';", self.js)
        # site decisions 152: in both languages (`lab`, the labels setting)
        self.assertIn("lab(b.firstChild,(h===1?MORE.one:MORE.many).replace('{n}',h),"
                      "(h===1?NB.moreOne:NB.more).replace('{n}',h));", self.js)
        self.assertIn("cues();excues();exheads();exmore();infl();", self.js)

    def test_a_click_opens_the_list_in_place(self):
        self.assertIn("var x=t.closest('.ordpar-exbtn');if(x){", self.js)
        self.assertIn("u.classList.add('ordpar-exopen');u.removeChild(li);", self.js)

    def test_the_mini_is_untouched(self):
        mini = _read(SITE, "mini.js")
        self.assertIn("var EX_BUDGET = 6;", mini)
        self.assertNotIn("exlimit", mini)


if __name__ == "__main__":
    unittest.main()
