# -*- coding: utf-8 -*-
"""Decisions 184, the outsider test's finding 8: no control byte in a file the export ships.

`ordpar/site/inflection.js` held a literal NUL and a literal 0x01 inside two string literals, so git
took the file for binary: `git diff` and GitHub showed no diff for it, and `grep` printed "Binary
file matches" instead of the line. The characters are now written as the escapes `'\\x00'` and
`'\\x01'`, which give the same strings. `ordpar/tests/test_ordpar_audio159.py` held the same slip,
a literal 0x01 and 0x02 in a raw string where the back-references `\\1` and `\\2` were meant.

Pinned here: no file under `ordpar/` (the site's code, its tests and browser tests, the receiver
and the audio Worker, the docs and the public texts; not the build's output in `ordpar/out/` or
`ordpar/.build/`, nor `node_modules/` or `__pycache__/`), no pipeline module the export ships with
the site (`export_public.PIPELINE`), and nothing under `handover/checks/` where it is present,
holds a byte below 0x20 other than tab, LF and CR, or the byte 0x7F. Images, icons, fonts and
compressed files are not text and are passed over. Stdlib unittest.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ORDPAR)

import export_public  # noqa: E402  -- PIPELINE: the modules shipped with the site

#: folders walked whole, relative to the repository root
FOLDERS = ("ordpar", os.path.join("handover", "checks"))
#: folders never walked: the build's output, installed packages, caches
SKIP = {"__pycache__", "node_modules", "out", ".build", ".wrangler", ".git"}
#: files that are not text
BINARY = (".png", ".ico", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".ttf", ".otf",
          ".mp3", ".ogg", ".opus", ".wav", ".gz", ".br", ".zip", ".pyc")
CONTROL = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def files():
    out = []
    for folder in FOLDERS:
        for dp, dn, fn in os.walk(os.path.join(ROOT, folder)):
            dn[:] = sorted(d for d in dn if d not in SKIP)
            for f in sorted(fn):
                if not f.lower().endswith(BINARY):
                    out.append(os.path.join(dp, f))
    for rel in export_public.PIPELINE:
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            out.append(p)
    return out


class NoControlBytes(unittest.TestCase):
    def test_the_files_are_found(self):
        names = {os.path.relpath(p, ROOT).replace("\\", "/") for p in files()}
        for want in ("ordpar/site/inflection.js", "ordpar/site/lookup.js", "ordpar/sitegen/page.py",
                     "ordpar/root/sw.js", "ordpar/build_site.py", "ordpar/tests/test_ordpar_audio159.py",
                     "ordpar/tests/browser/fragment104.js", "ordpar/receiver/src/worker.js",
                     "ordpar/docs/tests.md", "scripts/derive.py", "ordbok_gen.py"):
            self.assertIn(want, names)
        self.assertFalse([n for n in names if n.startswith(("ordpar/out/", "ordpar/.build/"))])

    def test_no_control_byte(self):
        bad = []
        for p in files():
            with open(p, "rb") as fh:
                data = fh.read()
            for n, line in enumerate(data.split(b"\n"), 1):
                for m in CONTROL.finditer(line):
                    bad.append("%s:%d: byte 0x%02x" % (os.path.relpath(p, ROOT).replace("\\", "/"),
                                                       n, m.group()[0]))
        self.assertEqual(bad, [], "control bytes in a file the export ships (write them as escapes, "
                                  "such as '\\x00', or as the back-reference meant): " + "; ".join(bad))


if __name__ == "__main__":
    unittest.main()
