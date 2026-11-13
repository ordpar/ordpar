# -*- coding: utf-8 -*-
"""Decisions 184, the outsider test's finding 8: no control byte in the site's code.

`ordpar/site/inflection.js` held a literal NUL and a literal 0x01 inside two string literals, so git
took the file for binary: `git diff` and GitHub showed no diff for it, and `grep` printed "Binary
file matches" instead of the line. The characters are now written as the escapes `'\\x00'` and
`'\\x01'`, which give the same strings.

Pinned here: no file under `ordpar/site/`, `ordpar/sitegen/` or `ordpar/root/`, and no
`ordpar/*.py`, holds a byte below 0x20 other than tab, LF and CR, or the byte 0x7F. Images,
icons and fonts are not text and are passed over. Stdlib unittest.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
FOLDERS = ("site", "sitegen", "root")
#: files that are not text
BINARY = (".png", ".ico", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".ttf", ".otf",
          ".mp3", ".ogg", ".opus", ".wav", ".gz", ".br", ".zip", ".pyc")
CONTROL = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def files():
    out = []
    for name in sorted(os.listdir(ORDPAR)):
        p = os.path.join(ORDPAR, name)
        if name.endswith(".py") and os.path.isfile(p):
            out.append(p)
    for folder in FOLDERS:
        for dp, dn, fn in os.walk(os.path.join(ORDPAR, folder)):
            dn[:] = sorted(d for d in dn if d != "__pycache__" and d != "node_modules")
            for f in sorted(fn):
                if not f.lower().endswith(BINARY):
                    out.append(os.path.join(dp, f))
    return out


class NoControlBytes(unittest.TestCase):
    def test_the_files_are_found(self):
        names = {os.path.relpath(p, ORDPAR).replace("\\", "/") for p in files()}
        for want in ("site/inflection.js", "site/lookup.js", "sitegen/page.py", "root/sw.js",
                     "build_site.py"):
            self.assertIn(want, names)

    def test_no_control_byte(self):
        bad = []
        for p in files():
            with open(p, "rb") as fh:
                data = fh.read()
            for n, line in enumerate(data.split(b"\n"), 1):
                for m in CONTROL.finditer(line):
                    bad.append("%s:%d: byte 0x%02x" % (os.path.relpath(p, ROOT).replace("\\", "/"),
                                                       n, m.group()[0]))
        self.assertEqual(bad, [], "control bytes in the site's code (write them as escapes, "
                                  "such as '\\x00'): " + "; ".join(bad))


if __name__ == "__main__":
    unittest.main()
