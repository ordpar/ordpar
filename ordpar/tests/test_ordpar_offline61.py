# -*- coding: utf-8 -*-
"""Pins the offline web app's build side and the service worker's routing (site-review decisions
61, Robin 2026-10-19; brief `docs/sessions/2026-09-19-ordpar-site-review/evidence/
brief-offline-61-2026-10-19.md`; spec `ordpar/docs/offline-app.md`). What can be pinned outside
a browser:

* **The pack format** (`ordpar/build_offline.py` `pack_raw` / `read_pack`): `OPK1`, a uint32
  header length, a JSON header of keys and n + 1 offsets, the bodies; gzip-compressed, read back
  to the identical bytes — in Python, and in `ordpar/root/sw.js` `parsePack` under bun with
  `DecompressionStream('gzip')`, as the worker reads it.
* **The frame tokens**: an article page is stored with its `?v=<hash>` (when it is the shipped
  file's current hash) and its build stamp (when it is the build's) blanked; `restore` — in
  Python and in `sw.js` — gives back the built file byte for byte; a token that does not match
  is kept.
* **The manifest**: the build id; each bundle's name, id range, count, size and SHA-256 equal
  to its file; every other file (the shell pages, `site/`, `index/`) with its size, hash and
  pack; `version.json` with the build id and the total.
* **Stability**: a script edited and the pages rebuilt with its new hash (and a new stamp)
  leaves every bundle's name and bytes unchanged — only the shell pack changes; one page edited
  changes only its own bundle; a page removed from the first bundle changes only that bundle
  (the boundaries are kept); an unchanged rebuild gives the same build id.
* **The worker's routes** (`sw.js` `route`): the article page from its bundle, a held file from
  its pack (a `?v=` that is not the held hash goes to the network first), `/bm-en/<id>` and
  `/bm-en/<id>/<slug>` to the held 404 shell when the network fails, everything else to the
  network, a failed navigation to the offline notice; without the copy, nothing but the notice.
  **A word page from the copy** (site decisions 170, Robin 2026-11-06, `test_word_page_from_copy`):
  with the copy kept, a navigation to `/bm-en/<word>/` (or `/bm-en/<word>`, `/bm-en/s%C3%A5/`) is
  the held 404 shell at once, online too, so the host never sees the word; `/bm-en/<id>/` stays
  the article, `/bm-en/7` and `/bm-en/7/hus` the network; not a navigation, no copy, or a copy
  without its 404 shell: the network. Fails on the `sw.js` before 170 (the word page went to the
  network first).
* **The robots line** (site decisions 128, 2026-10-25; until then the `NOINDEX` switch put
  `noindex` on every page): each page's own, whatever the switch (which now governs only the
  "under development" note) — the home page indexed, the search page, 404, favourites, history
  and settings `noindex`; a translated article page and the About page indexed, an untranslated
  article page `noindex`; every page links the app manifest and a theme colour; the shell build
  writes no `robots.txt` (it ships from `ordpar/root/`).
* **The app's files**: `ordpar/root/manifest.webmanifest` (name, short name, start_url, scope,
  standalone, the accent, icons 192 and 512 for `any` and `maskable`), the icons at their sizes,
  the shell pages loading `offline.js` before `shell.js`.

Synthetic data only (a temp `out/`); no mirror, library or built site is read. The JavaScript
tests run under `bun` and are skipped when it is not on PATH.
"""

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo (ordpar/tests/ since decisions 101)
ORDPAR = os.path.join(ROOT, "ordpar")
sys.path.insert(0, ORDPAR)
sys.path.insert(0, ROOT)

import build_offline as O  # noqa: E402
import build_index as B  # noqa: E402
from ordpar.sitegen import head as H  # noqa: E402

SW = os.path.join(ORDPAR, "root", "sw.js")


def _sha1(b):
    return hashlib.sha1(b).hexdigest()


def _rb(*parts):
    with open(os.path.join(*parts), "rb") as f:
        return f.read()


def _rt(*parts):
    with open(os.path.join(*parts), encoding="utf-8", newline="") as f:
        return f.read()


def _json(*parts):
    return json.loads(_rt(*parts))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


SCRIPTS = ("article.css", "page.css", "inflection.css", "inflection.js", "personal.js",
           "article.js")


def make_out(tmp, ids, stamp="ordpar build: mirror snapshot X · library aaaa", script=b"/*1*/",
             body=lambda aid: "body of %d — æøå" % aid):
    """A small built site: pages linking the six scripts and sheets with their hashes."""
    for name in SCRIPTS:
        _write(os.path.join(tmp, "site", name), script + name.encode())
    _write(os.path.join(tmp, "site", "strings", "en.json"), '{"a": "b"}')
    for url, rel in O.SHELL_PAGES.items():
        _write(os.path.join(tmp, rel), "<!doctype html><title>%s</title>" % url)
    for name in ("a.json", "a-top.json", "translated.json", "random.json", "index.json", "headwords/a.json",
                 "tails/a-b.json", "tails/c-d.json", "snip/a-b-c.json", "b-a.json"):
        _write(os.path.join(tmp, "index", name), '{"%s": 1}' % name)
    for aid in ids:
        write_page(tmp, aid, stamp, body(aid))


def write_page(tmp, aid, stamp, text):
    links = "".join('<link href="/site/%s?v=%s">' % (
        n, _sha1(_rb(tmp, "site", n))[:10]) for n in SCRIPTS)
    _write(os.path.join(tmp, "bm-en", str(aid), "index.html"),
           "<!doctype html>\n<!-- %s -->\n<html>%s<p>%s</p></html>\n" % (stamp, links, text))


class PackFormat(unittest.TestCase):
    def test_round_trip(self):
        items = [(1, b"one"), (22, "tjue-to — å".encode()), (333, b""), (4444, bytes(range(256)))]
        raw = O.pack_raw(items)
        self.assertEqual(raw[:4], b"OPK1")
        back = O.read_pack(O.gz(raw))
        self.assertEqual(list(back.items()), items)
        self.assertEqual(O.read_pack(raw), dict(items))          # unpacked input too
        self.assertEqual(O.gz(raw), O.gz(raw))                    # deterministic (mtime 0)

    def test_string_keys(self):
        items = [("/index/a.json", b"{}"), ("/site/x.js", b"x")]
        self.assertEqual(list(O.read_pack(O.gz(O.pack_raw(items))).items()), items)


class Tokens(unittest.TestCase):
    assets = {b"/site/a.js": b"0123456789"}
    stamp = b"ordpar build: mirror snapshot X \xc2\xb7 library abc"

    def page(self, h=b"0123456789", stamp=None):
        return (b"<!doctype html>\n<!-- " + (stamp or self.stamp) + b" -->\n<html>"
                b'<script src="/site/a.js?v=' + h + b'"></script>'
                b'<link href="/site/b.css?v=9999999999"></html>\n')

    def test_blank_and_restore(self):
        p = self.page()
        b = O.blank(p, self.assets, self.stamp)
        self.assertIn(b"/site/a.js?v=*", b)
        self.assertIn(b"<!-- ordpar build: * -->", b)
        self.assertIn(b"/site/b.css?v=9999999999", b)             # not a held file: kept
        self.assertEqual(O.restore(b, self.assets, self.stamp), p)

    def test_mismatch_kept(self):
        p = self.page(h=b"aaaaaaaaaa", stamp=b"ordpar build: other")
        self.assertEqual(O.blank(p, self.assets, self.stamp), p)


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ids = list(range(1, 26)) + [100, 101, 205]
        make_out(self.tmp, self.ids)
        self.res = O.build(self.tmp, per=10, quiet=True)
        self.man = _json(self.tmp, "offline", "manifest.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_manifest(self):
        m, dest = self.man, os.path.join(self.tmp, "offline")
        self.assertEqual((m["format"], m["version"]), ("ordpar-offline", 1))
        self.assertEqual(len(m["build"]), 16)
        self.assertEqual([(b["first"], b["last"], b["count"]) for b in m["bundles"]],
                         [(1, 10, 10), (11, 20, 10), (21, 205, 8)])
        for rec in m["bundles"] + m["packs"]:
            blob = _rb(dest, rec["name"])
            self.assertEqual(rec["size"], len(blob))
            self.assertEqual(rec["sha256"], hashlib.sha256(blob).hexdigest())
            self.assertIn("." + rec["sha256"][:16] + ".bin", rec["name"])
        self.assertTrue(m["bundles"][0]["name"].startswith("bm-en-1."))
        for url in ("/", "/bm-en/", "/about/", "/favourites/", "/history/", "/404.html",
                    "/manifest.webmanifest", "/site/article.js",
                    "/site/strings/en.json", "/index/a.json", "/index/tails/a-b.json",
                    "/index/snip/a-b-c.json"):
            self.assertIn(url, m["files"])
        f = m["files"]["/site/article.js"]
        data = _rb(self.tmp, "site", "article.js")
        self.assertEqual((f["size"], f["hash"]), (len(data), _sha1(data)[:16]))
        groups = {p["group"] for p in m["packs"]}
        self.assertEqual(groups, {"shell", "index-a", "index-b", "index-meta", "tails-a",
                                  "tails-c"})
        self.assertEqual(m["files"]["/index/snip/a-b-c.json"]["pack"], "index-a")
        self.assertEqual(m["files"]["/index/headwords/a.json"]["pack"], "index-a")
        self.assertEqual(m["files"]["/index/random.json"]["pack"], "index-meta")   # decisions 67
        self.assertEqual(m["total"], sum(r["size"] for r in m["bundles"] + m["packs"]))
        v = _json(dest, "version.json")
        self.assertEqual((v["build"], v["total"]), (m["build"], m["total"]))
        self.assertEqual(m["stamp"], "ordpar build: mirror snapshot X · library aaaa")

    def test_pages_equal_blanked_files(self):
        res = O.verify(self.tmp, quiet=True)
        self.assertEqual((res["pages_checked"], res["pages_bad"], res["pages_restore_bad"],
                          res["pages_missing"], res["files_bad"]), (len(self.ids), 0, 0, 0, 0))
        blob = _rb(self.tmp, "offline", self.man["bundles"][0]["name"])
        page = O.read_pack(blob)[3]
        self.assertIn(b"?v=*", page)
        self.assertNotIn(b"library aaaa", page)

    def names(self):
        m = _json(self.tmp, "offline", "manifest.json")
        return m, [b["name"] for b in m["bundles"]], {p["group"]: p["name"] for p in m["packs"]}

    def test_unchanged_rebuild_same_build(self):
        res = O.build(self.tmp, per=10, quiet=True)
        self.assertEqual(res["build"], self.man["build"])
        self.assertEqual((res["written"], res["removed"]), (0, 0))

    def test_script_edit_keeps_every_bundle(self):
        _m0, b0, p0 = self.names()
        bytes0 = {n: _rb(self.tmp, "offline", n) for n in b0}
        # a script edited, every page rebuilt with its new ?v= — and a new commit in the stamp
        _write(os.path.join(self.tmp, "site", "inflection.js"), b"/*2*/ changed")
        for aid in self.ids:
            write_page(self.tmp, aid, "ordpar build: mirror snapshot X · library bbbb",
                       "body of %d — æøå" % aid)
        O.build(self.tmp, per=10, quiet=True)
        m1, b1, p1 = self.names()
        self.assertEqual(b1, b0)
        for n in b1:
            self.assertEqual(_rb(self.tmp, "offline", n), bytes0[n])
        self.assertNotEqual(p1["shell"], p0["shell"])
        self.assertEqual({g: n for g, n in p1.items() if g != "shell"},
                         {g: n for g, n in p0.items() if g != "shell"})
        self.assertNotEqual(m1["build"], self.man["build"])
        self.assertEqual(O.verify(self.tmp, quiet=True)["pages_restore_bad"], 0)

    def test_one_page_changes_one_bundle(self):
        _m0, b0, _p0 = self.names()
        write_page(self.tmp, 15, "ordpar build: mirror snapshot X · library aaaa", "edited")
        O.build(self.tmp, per=10, quiet=True)
        _m1, b1, _p1 = self.names()
        self.assertEqual([a == b for a, b in zip(b0, b1)], [True, False, True])

    def test_boundaries_kept(self):
        _m0, b0, _p0 = self.names()
        shutil.rmtree(os.path.join(self.tmp, "bm-en", "3"))
        O.build(self.tmp, per=10, quiet=True)
        m1, b1, _p1 = self.names()
        self.assertEqual([a == b for a, b in zip(b0, b1)], [False, True, True])
        self.assertEqual([(b["first"], b["count"]) for b in m1["bundles"]],
                         [(1, 9), (11, 10), (21, 8)])
        # --rechunk starts afresh: 2,000 (here 10) to a bundle from the lowest id
        O.build(self.tmp, per=10, rechunk=True, quiet=True)
        m2, _b2, _p2 = self.names()
        self.assertEqual([(b["first"], b["count"]) for b in m2["bundles"]],
                         [(1, 10), (12, 10), (22, 7)])

    def test_chunk_split(self):
        ids = list(range(1, 40))
        got = O.chunk(ids, per=10, starts=[1, 11])
        self.assertEqual([(f, len(g)) for f, g in got], [(1, 10), (11, 10), (21, 10), (31, 9)])


def _bun():
    return shutil.which("bun")


class Worker(unittest.TestCase):
    """`sw.js`'s pure parts under bun, over a pack and a manifest this build wrote."""

    @classmethod
    def setUpClass(cls):
        if not _bun():
            raise unittest.SkipTest("no bun on PATH")
        cls.tmp = tempfile.mkdtemp()
        make_out(cls.tmp, list(range(1, 26)))
        O.build(cls.tmp, per=10, quiet=True)
        script = os.path.join(cls.tmp, "t.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(r"""
const S = require(%(sw)s);
const fs = require('fs'), path = require('path');
const out = %(out)s;
const man = JSON.parse(fs.readFileSync(path.join(out, 'offline', 'manifest.json'), 'utf8'));
const st = S.prepare(man);
async function unpack(file) {
  const z = fs.readFileSync(path.join(out, 'offline', file));
  const ds = new Blob([z]).stream().pipeThrough(new DecompressionStream('gzip'));
  return S.parsePack(new Uint8Array(await new Response(ds).arrayBuffer()));
}
(async () => {
  const res = {pages: {}, files: {}, routes: {}, routesNoCopy: {}};
  for (const b of man.bundles) {
    const p = await unpack(b.name);
    for (const [id, span] of p.index) {
      const text = new TextDecoder().decode(p.body.subarray(span[0], span[1]));
      res.pages[id] = S.restore(text, man);
    }
  }
  const shell = await unpack(st.byGroup.shell.name);
  res.files['/site/article.js'] = new TextDecoder().decode(
    shell.body.subarray(...shell.index.get('/site/article.js')));
  const h = man.files['/site/article.js'].hash.slice(0, 10);
  const cases = [['/bm-en/7/', 1], ['/bm-en/7/index.html', 1], ['/bm-en/7', 1],
    ['/bm-en/hus', 1], ['/bm-en/7/hus', 1], ['/bm-en/', 1], ['/bm-en/?q=fly', 1], ['/', 1],
    ['/about/', 1], ['/about/index.html', 1], ['/site/article.js?v=' + h, 0],
    ['/site/article.js?v=0000000000', 0], ['/site/strings/en.json', 0], ['/index/a.json', 0],
    ['/index/zz.json', 0], ['/elsewhere/', 1], ['/bm-en/999999/', 1], ['/favourites/', 1],
    ['/bm-en/hus/', 1], ['/bm-en/s%%C3%%A5/', 1], ['/bm-en/b%%C3%%B8ker/', 1], ['/bm-en/7/', 1],
    ['/bm-en/index.html', 1]];
  // a copy whose manifest lacks the 404 shell (decisions 170: then the network, as before)
  const noShell = Object.assign({}, st, { files: Object.assign({}, st.files) });
  delete noShell.files['/404.html'];
  res.routesNoShell = {};
  for (const [u, nav] of cases) {
    res.routes[u] = S.route(st, new URL('http://x' + u), !!nav);
    res.routesNoCopy[u] = S.route(null, new URL('http://x' + u), !!nav);
    res.routesNoShell[u] = S.route(noShell, new URL('http://x' + u), !!nav);
  }
  res.wordNotNavigate = S.route(st, new URL('http://x/bm-en/hus/'), false);
  res.bundleFor = [0, 1, 10, 11, 25, 99999].map(i => (S.bundleFor(st, i) || {}).first || null);
  res.types = ['/', '/a.js', '/a.css', '/i.json', '/manifest.webmanifest', '/x.png', '/404.html']
    .map(S.typeOf);
  res.hash = h;
  res.notice = [S.noticeHtml('/x/<b>', true), S.noticeHtml('/x/', false)];
  console.log(JSON.stringify(res));
})().catch(e => { console.error(e); process.exit(1); });
""" % {"sw": json.dumps(SW), "out": json.dumps(cls.tmp)})
        run = subprocess.run([_bun(), script], capture_output=True, timeout=60)
        if run.returncode != 0:
            raise AssertionError(run.stderr.decode("utf-8", "replace"))
        cls.res = json.loads(run.stdout.decode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pages_restored_exactly(self):
        self.assertEqual(len(self.res["pages"]), 25)
        for aid, text in self.res["pages"].items():
            with open(os.path.join(self.tmp, "bm-en", aid, "index.html"), encoding="utf-8",
                      newline="") as f:
                self.assertEqual(text, f.read(), aid)

    def test_file_from_pack(self):
        with open(os.path.join(self.tmp, "site", "article.js"), encoding="utf-8") as f:
            self.assertEqual(self.res["files"]["/site/article.js"], f.read())

    def test_routes(self):
        r = self.res["routes"]
        k = lambda u: (r[u]["kind"], r[u].get("fallback"))
        self.assertEqual((r["/bm-en/7/"]["kind"], r["/bm-en/7/"]["id"],
                          r["/bm-en/7/"]["bundle"]["first"]), ("article", 7, 1))
        self.assertEqual(k("/bm-en/7/"), ("article", "notice"))
        self.assertEqual(r["/bm-en/7/index.html"]["kind"], "article")
        self.assertEqual(k("/bm-en/7"), ("network", "shell404"))      # the 404 shell redirects
        self.assertEqual(k("/bm-en/hus"), ("shell404", "shell404"))   # the shell searches (170)
        self.assertEqual(k("/bm-en/7/hus"), ("network", "shell404"))
        self.assertEqual((r["/bm-en/"]["kind"], r["/bm-en/"]["path"]), ("file", "/bm-en/"))
        self.assertEqual(r["/bm-en/?q=fly"]["path"], "/bm-en/")
        self.assertEqual(r["/"]["path"], "/")
        self.assertEqual(r["/about/index.html"]["path"], "/about/")
        self.assertEqual(k("/elsewhere/"), ("network", "notice"))
        self.assertEqual(r["/bm-en/999999/"]["kind"], "article")      # in range; not in the pack
        self.assertFalse(r["/site/article.js?v=" + self.res["hash"]]["stale"])
        self.assertTrue(r["/site/article.js?v=0000000000"]["stale"])
        self.assertEqual(k("/site/strings/en.json"), ("file", None))  # not a navigation
        self.assertEqual(k("/index/a.json"), ("file", None))
        self.assertEqual(k("/index/zz.json"), ("network", None))
        for u, got in self.res["routesNoCopy"].items():
            self.assertEqual(got["kind"], "network", u)
            self.assertIn(got["fallback"], ("notice", None), u)

    def test_word_page_from_copy(self):
        """Site decisions 170: with the copy kept, a word's own page is the held 404 shell at
        once, online too (it runs the word's search from the copy), so the host never sees the
        word; every other route as before."""
        r = self.res["routes"]
        k = lambda u: (r[u]["kind"], r[u].get("fallback"))
        for u in ("/bm-en/hus/", "/bm-en/hus", "/bm-en/s%C3%A5/", "/bm-en/b%C3%B8ker/"):
            self.assertEqual(k(u), ("shell404", "shell404"), u)
        self.assertEqual(r["/bm-en/7/"]["kind"], "article")
        self.assertEqual(k("/bm-en/7"), ("network", "shell404"))
        self.assertEqual(k("/bm-en/7/hus"), ("network", "shell404"))
        self.assertEqual(r["/bm-en/index.html"]["kind"], "file")      # the search page, held
        self.assertEqual(r["/bm-en/?q=fly"]["kind"], "file")
        self.assertEqual(k("/elsewhere/"), ("network", "notice"))
        self.assertEqual(self.res["wordNotNavigate"]["kind"], "network")
        for u in ("/bm-en/hus/", "/bm-en/s%C3%A5/"):
            self.assertEqual(self.res["routesNoCopy"][u]["kind"], "network", u)
            self.assertEqual(self.res["routesNoShell"][u]["kind"], "network", u)
        # without the shell held, every other route is unchanged
        for u, got in self.res["routesNoShell"].items():
            if u not in ("/bm-en/hus/", "/bm-en/hus", "/bm-en/s%C3%A5/", "/bm-en/b%C3%B8ker/"):
                self.assertEqual(got["kind"], r[u]["kind"], u)

    def test_bundle_for(self):
        self.assertEqual(self.res["bundleFor"], [None, 1, 1, 11, 21, 21])

    def test_types_and_notice(self):
        self.assertEqual(self.res["types"], [
            "text/html; charset=utf-8", "text/javascript; charset=utf-8",
            "text/css; charset=utf-8", "application/json; charset=utf-8",
            "application/manifest+json", "image/png", "text/html; charset=utf-8"])
        held, none = self.res["notice"]
        self.assertIn("You are offline", held)
        self.assertIn("not in the offline copy", held)
        self.assertIn("Keep the whole dictionary on this device", none)
        self.assertIn("/x/&lt;b&gt;", held)                           # the path escaped


class NoIndex(unittest.TestCase):
    def setUp(self):
        self.saved = H.NOINDEX
        self.tmp = tempfile.mkdtemp()
        for name in ("article.css", "article.js"):     # the article build's, which the shell links
            _write(os.path.join(self.tmp, "site", name), "/* %s */" % name)

    def tearDown(self):
        H.NOINDEX = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_switch_is_on(self):
        self.assertIs(self.saved, True)
        self.assertIn("remove at launch", _rt(H.__file__).lower())

    def shells(self):
        B.copy_shell(self.tmp)
        return {rel: _rt(self.tmp, rel)
                for rel in ("index.html", "bm-en/index.html", "404.html",
                            "favourites/index.html", "history/index.html",
                            "settings/index.html")}

    def test_shell_pages(self):
        for on in (True, False):          # the switch no longer moves the robots line (128)
            H.NOINDEX = on
            for f in ("index.html",):
                p = os.path.join(self.tmp, f)
                if os.path.exists(p):
                    os.remove(p)
            for rel, html in self.shells().items():
                self.assertIn('<link rel="manifest" href="/manifest.webmanifest">', html, rel)
                # decisions 63: the default colour scheme's day accent (Wine since 2026-10-20)
                self.assertIn('<meta name="theme-color" content="#6b0f2e">', html, rel)
                self.assertNotIn("<!--ORDPAR_HEAD-->", html, rel)
                home = rel == "index.html"
                self.assertEqual(H.ROBOTS_NOINDEX in html, not home, (on, rel))
                self.assertEqual(html.count('<meta name="robots"'), 0 if home else 1, (on, rel))
                # one blocking script since 2026-10-20: offline.js still before shell.js in it
                self.assertIn('<script src="/site/shell-pages.js', html, rel)
        from ordpar.sitegen import page as P
        self.assertLess(P.SHELL_JS_PARTS.index("/site/offline.js"),
                        P.SHELL_JS_PARTS.index("/site/shell.js"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "robots.txt")))

    def test_front_page_replaced(self):
        _write(os.path.join(self.tmp, "index.html"),
               "<!doctype html>\n<!-- s -->\n<!-- ordpar: prototype front page, written by "
               "build_site.py -->\n<p>Prototype pages:</p>")
        self.assertIn("data-ordpar-results", self.shells()["index.html"])
        _write(os.path.join(self.tmp, "index.html"), "<p>someone else's</p>")
        self.assertEqual(self.shells()["index.html"], "<p>someone else's</p>")

    def test_article_and_about_pages(self):
        from ordpar.sitegen import page as P
        from ordpar.sitegen.strings import EN
        for on in (True, False):          # the switch no longer moves the robots line (128)
            H.NOINDEX = on
            art = {tr: P.render(aid=7, lemmas=[{"form": "x"}], article='<div class="ordbok"></div>',
                                translated=tr, other_entries=0, strings=EN, stamp="s",
                                description="d", mk=None) for tr in (True, False)}
            about = P.about_page("s", EN, P.about_mod.SAMPLE)
            for html, out in ((art[True], False), (art[False], True), (about, False)):
                self.assertEqual(H.ROBOTS_NOINDEX in html, out)
                self.assertIn('<link rel="manifest" href="/manifest.webmanifest">', html)
            # the About page's one script is the article page's (since 2026-10-20), which
            # registers the worker as `SW_REGISTER` did there until then
            self.assertIn('<script src="/site/ordpar.js?v=', about)
            self.assertNotIn(H.SW_REGISTER, about)
        self.assertIn("navigator.serviceWorker.register('/sw.js')", P.PAGE_JS)
        self.assertIn(P.JS_HREF, P.ARTICLE_JS_PARTS)


class AppFiles(unittest.TestCase):
    def test_manifest(self):
        m = _json(ORDPAR, "root", "manifest.webmanifest")
        self.assertEqual((m["name"], m["short_name"], m["start_url"], m["scope"], m["display"]),
                         ("Ordpar", "Ordpar", "/", "/", "standalone"))
        self.assertEqual(m["theme_color"], "#6b0f2e")       # decisions 63: the default scheme, Wine
        got = {(i["sizes"], i["purpose"]) for i in m["icons"]}
        self.assertEqual(got, {("192x192", "any"), ("512x512", "any"), ("192x192", "maskable"),
                               ("512x512", "maskable")})
        for i in m["icons"]:
            path = os.path.join(ORDPAR, i["src"].lstrip("/").replace("site/", "site" + os.sep, 1))
            with open(path, "rb") as f:
                png = f.read(24)
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            w = int.from_bytes(png[16:20], "big")
            self.assertEqual("%dx%d" % (w, int.from_bytes(png[20:24], "big")), i["sizes"])

    def test_worker_at_root(self):
        self.assertTrue(os.path.isfile(SW))
        self.assertFalse(os.path.exists(os.path.join(ORDPAR, "site", "sw.js")))


if __name__ == "__main__":
    unittest.main()
