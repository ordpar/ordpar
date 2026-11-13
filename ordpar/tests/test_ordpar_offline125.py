"""Site-review decisions 125 (Robin, 2026-10-24; the sentence approved 2026-10-25): the offline setting's line says the copy also makes pages open faster.

* `site/strings/en.json` `offline.intro` is exactly the approved text: "Pages also open faster,
  since they come from this device." as its second sentence, after "…without a connection.";
* `site/offline.js` (Settings → Offline, the section drawn when no copy is kept) is the one script
  that reads the key, so the settings page is the one place the line shows;
* the built site (`ordpar/out/`, when built) carries the same text in the strings file and in every
  page that inlines the strings — the settings page, `/site/ordpar.js` — and no page the old line.

The claim rests on Robin's use of both on his devices (decisions 125) and one timing of an article
from the copy against the network, recorded in the build's report
(`docs/sessions/2026-09-19-ordpar-site-review/evidence/reports/outside-click-124-125-2026-10-25-contractor.md`).
"""
import json
import os
import re
import unittest

ORDPAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ORDPAR, "site")
OUT = os.environ.get("ORDPAR_TEST_OUT") or os.path.join(ORDPAR, "out")

LINE = ("Keep the whole dictionary on this device to look words up without a connection. "
        "Pages also open faster, since they come from this device. "
        "It is stored compressed; nothing is downloaded until you press the button.")
OLD = ("Keep the whole dictionary on this device to look words up without a connection. "
       "It is stored compressed;")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class OfflineLine(unittest.TestCase):

    def test_a_the_string(self):
        strings = json.loads(_read(os.path.join(SITE, "strings", "en.json")))
        self.assertEqual(strings["offline.intro"], LINE)

    def test_b_one_reader(self):
        readers = [n for n in sorted(os.listdir(SITE)) if n.endswith((".js", ".html"))
                   and "offline.intro" in _read(os.path.join(SITE, n))]
        self.assertEqual(readers, ["offline.js"])
        self.assertTrue(re.search(r"t\('offline\.intro'\)", _read(os.path.join(SITE, "offline.js"))))

    @unittest.skipUnless(os.path.isfile(os.path.join(OUT, "settings", "index.html")), "no build in " + OUT)
    def test_c_the_build(self):
        for rel in (("site", "strings", "en.json"), ("settings", "index.html"), ("site", "ordpar.js")):
            text = _read(os.path.join(OUT, *rel))
            self.assertIn(LINE, text.replace("\\u2019", "’"), "/".join(rel))
            self.assertNotIn(OLD, text, "/".join(rel))


if __name__ == "__main__":
    unittest.main()
