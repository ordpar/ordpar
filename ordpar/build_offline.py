"""The offline copy's files (decisions 61): `out/offline/` — the built site packed into gzip
bundles for the installable web app's "Keep the whole dictionary on this device", and the
manifest the service worker (`ordpar/root/sw.js`) and the download (`ordpar/site/offline.js`)
read. The spec is `ordpar/docs/offline-app.md`.

Run it AFTER both builds (it reads what they wrote and nothing else):

    python ordpar/build_site.py --mirror "…/bm-articles.jsonl" --all
    python ordpar/build_index.py --mirror "…/bm-articles.jsonl" --freq "…"
    python ordpar/build_offline.py            # writes out/offline/
    python ordpar/build_offline.py --verify   # reads every bundle back against out/

What it writes (all under `out/offline/`, which is published with the site):

    bm-en-<first>.<hash>.bin    the article pages, whole, 500 to a bundle in numeric id order
    index-<key>.<hash>.bin      the search index (`out/index/`), one pack per letter key
    tails-<key>.<hash>.bin      `out/index/tails/`, one pack per first key
    en-<letter>.<hash>.bin      `out/index/en/`, the English search's shards, one pack per letter
                                (site decisions 148)
    en-tails-<key>.<hash>.bin   `out/index/en/tails/`, the English tails files, one pack per first
                                key (site decisions 148's follow-up)
    index-meta.<hash>.bin       `index.json`, `translated.json`, `random.json`, `labels.json`
                                (the form labels' words, site decisions 117), `random-en.json`
                                (Random word's English pool, site decisions 155)
    shell.<hash>.bin            the shell pages (`SHELL_PAGES`, and those of `OPTIONAL_PAGES`
                                the build wrote; listed at the end of --help) and `out/site/`
    manifest.json               the build id, every bundle and pack, every file
    version.json                the build id alone — what the app polls on opening

A pack is gzip data (named `.bin`, so no server labels it `Content-Encoding: gzip`): `OPK1`, a
little-endian uint32 header length, a JSON header `{"keys": [...], "offsets": [...]}` (n keys,
n + 1 offsets into the body), then the bodies. One page is found from the header — no scan.

**The frame tokens.** An article page is stored with its build-wide stamps BLANKED, so that
editing a script or stylesheet, or committing anything, leaves every bundle unchanged:
every `/site/<file>?v=<hash>` whose hash is the shipped file's current one becomes
`/site/<file>?v=*`, and the build stamp comment `<!-- ordpar build: … -->` (it carries the
repository's commit) becomes `<!-- ordpar build: * -->` when it is the build's majority stamp.
The pages the build writes today carry no stamp comment, so only their `?v=` tokens are blanked
and the manifest's `stamp` is `out/build.json`'s; a page that still has the comment is blanked as
above.
The service worker puts both back from the manifest (`files[path].hash[:10]`, `stamp`), so a
page served offline is byte for byte the page the host serves. A token that does not match is
left as it is, so the restore is always exact.

A bundle's name carries its hash, so an unchanged bundle keeps its name from build to build.
Its boundaries are kept from the previous manifest when there is one (`--rechunk` to start
afresh), so an article added or removed shifts only its own bundle; a bundle that grows past
1.5 × `--per` is split.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import struct
import sys
import time
from collections import Counter

ORDPAR = os.path.dirname(os.path.abspath(__file__))
FORMAT = "ordpar-offline"
VERSION = 1
MAGIC = b"OPK1"
#: pages to a bundle: 500 since decisions 92 (2,000 until then; offline-app.md § 2 has the measurement)
PER = 500
LEVEL = 9
#: A file's hash in the manifest: the first 16 hex digits of its SHA-1 — the same digest as
#: the pages' `?v=` (its first 10), long enough to tell a changed file
HASH_HEX = 16
PAIR = "bm-en"

STAMP_RE = re.compile(rb"\A(<!doctype html>\n<!-- )(ordpar build: [^\n]*?)( -->\n)", re.I)
STAMP_TOKEN = b"ordpar build: *"
ASSET_RE = re.compile(rb"(/site/[\w./-]+\.(?:js|css))\?v=([0-9a-f]{10})")
ASSET_TOKEN = b"*"

#: The shell pages: URL path -> file under out/
SHELL_PAGES = {"/": "index.html", "/bm-en/": "bm-en/index.html", "/about/": "about/index.html",
               "/help/": "help/index.html",                # decisions 123 as amended
               "/coming/": "coming/index.html",            # decisions 131
               "/more/": "more/index.html",                # decisions 142
               "/changes/": "changes/index.html",          # site decisions 175
               "/dictionary-changes/": "dictionary-changes/index.html",   # 175
               "/deck-changes/": "deck-changes/index.html",                # 177
               "/favourites/": "favourites/index.html", "/history/": "history/index.html",
               "/settings/": "settings/index.html",       # decisions 63
               "/404.html": "404.html", "/manifest.webmanifest": "manifest.webmanifest"}
#: Shell pages taken only where the build wrote them, so their absence is no warning: `/privacy/`
#: exists only while its switch is on (`sitegen/chrome.py` `PRIVACY`, site decisions 104; or in a
#: look build with reports on, 166's `build_site.privacy_for_build`), and
#: `/thanks/` only while reports are on (`chrome.REPORT_RECEIVER`, site decisions 166)
OPTIONAL_PAGES = {"/privacy/": "privacy/index.html",
                  "/thanks/": "thanks/index.html"}


# --- the pack format ---------------------------------------------------------

def pack_raw(items):
    """`items`: [(key, bytes)] -> the uncompressed pack."""
    keys, offsets, pos = [], [0], 0
    for k, b in items:
        keys.append(k)
        pos += len(b)
        offsets.append(pos)
    head = json.dumps({"keys": keys, "offsets": offsets}, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    return MAGIC + struct.pack("<I", len(head)) + head + b"".join(b for _k, b in items)


def gz(raw):
    return gzip.compress(raw, LEVEL, mtime=0)


def read_pack(blob):
    """A pack file's bytes (gzip, or already unpacked) -> {key: bytes}, in order."""
    raw = gzip.decompress(blob) if blob[:2] == b"\x1f\x8b" else blob
    if raw[:4] != MAGIC:
        raise ValueError("not an Ordpar pack")
    (n,) = struct.unpack("<I", raw[4:8])
    head = json.loads(raw[8:8 + n].decode("utf-8"))
    body = 8 + n
    offs = head["offsets"]
    return {k: raw[body + offs[i]:body + offs[i + 1]] for i, k in enumerate(head["keys"])}


# --- the frame tokens --------------------------------------------------------

def blank(page, assets, stamp):
    """An article page as the bundle stores it: every `?v=<hash>` that is the shipped file's
    current hash (`assets`: path -> 10-hex hash) and the build stamp when it is `stamp`, each
    replaced by its token. Anything that does not match stays, so `restore` is exact."""
    def one(m):
        return m.group(1) + b"?v=" + ASSET_TOKEN if assets.get(m.group(1)) == m.group(2) \
            else m.group(0)
    page = ASSET_RE.sub(one, page)
    m = STAMP_RE.match(page)
    if m and stamp is not None and m.group(2) == stamp:
        page = m.group(1) + STAMP_TOKEN + m.group(3) + page[m.end():]
    return page


def restore(page, assets, stamp):
    """The inverse of `blank` — what the service worker does (`sw.js` `restore`)."""
    page = re.sub(rb"(/site/[\w./-]+\.(?:js|css))\?v=\*",
                  lambda m: m.group(1) + b"?v=" + assets[m.group(1)]
                  if m.group(1) in assets else m.group(0), page)
    m = STAMP_RE.match(page)
    if m and m.group(2) == STAMP_TOKEN and stamp is not None:
        page = m.group(1) + stamp + m.group(3) + page[m.end():]
    return page


# --- the inputs --------------------------------------------------------------

def sha1(b):
    return hashlib.sha1(b).hexdigest()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read(path):
    with open(path, "rb") as f:
        return f.read()


def article_ids(out):
    d = os.path.join(out, PAIR)
    return sorted(int(x) for x in os.listdir(d)
                  if x.isdigit() and os.path.isfile(os.path.join(d, x, "index.html")))


def page_path(out, aid):
    return os.path.join(out, PAIR, str(aid), "index.html")


def majority_stamp(out, ids):
    """The build stamp most pages carry (a partial `--ids` rebuild leaves a few with another).
    Since 2026-10-20 the pages carry none (the size report's item 2): then it is the article
    build's own, `out/build.json` `stamp` — the manifest keeps naming the build either way."""
    c = Counter()
    for aid in ids:
        with open(page_path(out, aid), "rb") as f:
            m = STAMP_RE.match(f.read(400))
        if m:
            c[m.group(2)] += 1
    if c:
        return c.most_common(1)[0][0]
    try:
        with open(os.path.join(out, "build.json"), encoding="utf-8") as f:
            stamp = json.load(f).get("stamp")
    except (OSError, ValueError):
        stamp = None
    return stamp.encode("utf-8") if stamp else None


def other_files(out):
    """Every file the app needs offline besides the article pages: URL path -> file path.
    The shell pages, `out/site/` and `out/index/`."""
    files = {}
    for url, rel in SHELL_PAGES.items():
        p = os.path.join(out, rel)
        if os.path.isfile(p):
            files[url] = p
        else:
            print("  WARNING: %s (%s) is missing — not in the offline copy" % (url, rel))
    for url, rel in OPTIONAL_PAGES.items():
        p = os.path.join(out, rel)
        if os.path.isfile(p):
            files[url] = p
    for sub in ("site", "index"):
        top = os.path.join(out, sub)
        for root, dirs, names in os.walk(top):
            # the link-preview picture (`/site/og/`, site decisions 127) is for the sites that
            # draw a shared link's card, never shown by a page: not in the offline copy
            dirs[:] = sorted(d for d in dirs if os.path.join(root, d) != os.path.join(out, "site", "og"))
            for n in sorted(names):
                p = os.path.join(root, n)
                files["/" + os.path.relpath(p, out).replace(os.sep, "/")] = p
    return files


def file_group(url):
    """Which pack a file goes in — stable, so a change touches only its own pack: the search
    index by the letter key a query reads together (the shard, its `-top`, its `snip/` files,
    its headwords file), `tails/` by its first key, the rest in `shell`."""
    if not url.startswith("/index/"):
        return "shell"
    rest = url[len("/index/"):]
    name = rest.rsplit("/", 1)[-1][:-len(".json")] if rest.endswith(".json") else rest
    if rest in ("index.json", "translated.json", "random.json", "labels.json", "random-en.json"):
        return "index-meta"
    if rest.startswith("tails/"):
        return "tails-" + name.split("-")[0]
    # site decisions 148's follow-up: the English tails files, one pack per first key, as the
    # Norwegian `tails/` (never in a letter's `en-` pack, nor one pack per file)
    if rest.startswith("en/tails/"):
        return "en-tails-" + name.split("-")[0]
    # site decisions 148: the English search's shards, one pack per letter of their own, so a
    # change to the English glosses never touches a Norwegian pack (nor the reverse)
    if rest.startswith("en/"):
        return "en-" + name
    return "index-" + name.split("-")[0]


# --- the chunking ------------------------------------------------------------

def chunk(ids, per=PER, starts=None):
    """`ids` (sorted) -> [(first, [ids])]. With `starts` (the previous manifest's bundle
    boundaries) every id goes to the last boundary at or below it, so an id added or removed
    changes only its own bundle; a group past 1.5 × per is split into `per`-sized parts,
    an empty one dropped. Without, `per` to a bundle from the lowest id."""
    if not starts:
        return [(ids[k], ids[k:k + per]) for k in range(0, len(ids), per)]
    starts = sorted(starts)
    groups, si = {s: [] for s in starts}, 0
    for aid in ids:
        while si + 1 < len(starts) and starts[si + 1] <= aid:
            si += 1
        groups[starts[si]].append(aid)
    out = []
    for s in starts:
        g = groups[s]
        if not g:
            continue
        if len(g) > per * 1.5:
            parts = [g[k:k + per] for k in range(0, len(g), per)]
            out.append((min(s, g[0]), parts[0]))
            out.extend((p[0], p) for p in parts[1:])
        else:
            out.append((min(s, g[0]), g))
    return out


# --- the build ---------------------------------------------------------------

def build(out, per=PER, rechunk=False, quiet=False):
    t0 = time.perf_counter()
    dest = os.path.join(out, "offline")
    os.makedirs(dest, exist_ok=True)
    prev_path = os.path.join(dest, "manifest.json")
    prev = None
    if os.path.exists(prev_path):
        try:
            with open(prev_path, encoding="utf-8") as f:
                prev = json.load(f)
            if prev.get("format") != FORMAT or prev.get("version") != VERSION:
                prev = None
        except ValueError:
            prev = None
    # a pack whose uncompressed content is unchanged keeps its file: no recompression
    reuse = {}
    if prev:
        for p in prev.get("bundles", []) + prev.get("packs", []):
            if os.path.exists(os.path.join(dest, p["name"])):
                reuse[p["raw"]] = p

    log = (lambda *a: None) if quiet else print
    files = other_files(out)
    file_meta, file_bytes = {}, {}
    for url, p in files.items():
        b = read(p)
        file_bytes[url] = b
        file_meta[url] = {"size": len(b), "hash": sha1(b)[:HASH_HEX]}
    assets = {url.encode(): m["hash"][:10].encode() for url, m in file_meta.items()
              if url.startswith("/site/") and re.search(r"\.(?:js|css)$", url)}

    ids = article_ids(out)
    t_stamp = time.perf_counter()
    stamp = majority_stamp(out, ids)
    t_stamp = time.perf_counter() - t_stamp
    starts = None if rechunk or not prev else [b["first"] for b in prev.get("bundles", [])]
    groups = chunk(ids, per, starts)

    stats = Counter()
    written, reused = [], []

    def emit(prefix, items, extra):
        raw = pack_raw(items)
        rh = sha256(raw)
        old = reuse.get(rh)
        if old and old["name"].startswith(prefix + "."):
            reused.append(old["name"])
            rec = dict(old)
        else:
            z = gz(raw)
            h = sha256(z)
            name = "%s.%s.bin" % (prefix, h[:16])
            with open(os.path.join(dest, name), "wb") as f:
                f.write(z)
            written.append(name)
            rec = {"name": name, "size": len(z), "sha256": h, "raw": rh}
        rec.update(extra)
        rec["raw_size"] = len(raw)
        rec["count"] = len(items)
        return rec

    bundles = []
    t_b = time.perf_counter()
    for first, g in groups:
        items = []
        for aid in g:
            page = read(page_path(out, aid))
            b = blank(page, assets, stamp)
            stats["pages"] += 1
            stats["raw"] += len(page)
            if b == page:
                stats["unblanked"] += 1          # nothing matched: kept verbatim
            elif STAMP_TOKEN not in b[:200] and STAMP_RE.match(page):
                stats["stamp_kept"] += 1         # a stamp, not the build's: kept as it is
            items.append((aid, b))
        rec = emit("%s-%d" % (PAIR, first), items, {"first": first, "last": g[-1]})
        bundles.append({k: rec[k] for k in ("name", "first", "last", "count", "size", "sha256",
                                            "raw", "raw_size")})
    t_b = time.perf_counter() - t_b

    by_group = {}
    for url in files:
        by_group.setdefault(file_group(url), []).append(url)
    packs = []
    for grp in sorted(by_group):
        urls = by_group[grp]
        rec = emit(grp, [(u, file_bytes[u]) for u in urls], {"group": grp})
        packs.append({k: rec[k] for k in ("name", "group", "count", "size", "sha256", "raw",
                                          "raw_size")})
        for u in urls:
            file_meta[u]["pack"] = grp

    body = {"format": FORMAT, "version": VERSION, "per": per,
            "stamp": stamp.decode("utf-8") if stamp else None,
            "tokens": {"asset": "?v=*", "stamp": STAMP_TOKEN.decode()},
            "pages": stats["pages"],
            "bundles": bundles, "packs": packs, "files": file_meta}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    build_id = sha256(canon.encode("utf-8"))[:16]
    manifest = {"format": FORMAT, "version": VERSION, "build": build_id,
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "total": sum(b["size"] for b in bundles) + sum(p["size"] for p in packs)}
    manifest.update(body)
    blob = (json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    tmp = prev_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, prev_path)
    with open(os.path.join(dest, "version.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"format": FORMAT, "version": VERSION, "build": build_id,
                            "total": manifest["total"]}) + "\n")

    keep = {b["name"] for b in bundles} | {p["name"] for p in packs} | {"manifest.json",
                                                                        "version.json"}
    removed = [n for n in os.listdir(dest) if n not in keep]
    for n in removed:
        os.remove(os.path.join(dest, n))

    secs = time.perf_counter() - t0
    res = {"build": build_id, "pages": stats["pages"], "pages_raw": stats["raw"],
           "pages_unblanked": stats["unblanked"], "pages_stamp_kept": stats["stamp_kept"],
           "bundles": len(bundles), "bundles_total": sum(b["size"] for b in bundles),
           "bundle_largest": max((b["size"] for b in bundles), default=0),
           "bundle_largest_raw": max((b["raw_size"] for b in bundles), default=0),
           "packs": len(packs), "packs_total": sum(p["size"] for p in packs),
           "files": len(file_meta), "files_raw": sum(m["size"] for m in file_meta.values()),
           "manifest_bytes": len(blob), "manifest_gzip": len(gz(blob)),
           "download_total": manifest["total"] + len(blob),
           "written": len(written), "reused": len(reused), "removed": len(removed),
           "secs": round(secs, 1), "secs_stamp_pass": round(t_stamp, 1),
           "secs_bundles": round(t_b, 1), "stamp": body["stamp"]}
    log("offline: %(pages)d pages -> %(bundles)d bundles, %(bundles_total)d bytes "
        "(largest %(bundle_largest)d); %(files)d other files -> %(packs)d packs, "
        "%(packs_total)d bytes; download %(download_total)d bytes; build %(build)s; "
        "%(written)d written, %(reused)d reused, %(removed)d removed; %(secs)s s" % res)
    if stats["unblanked"]:
        log("  note: %d page(s) carried no current ?v= hash or stamp (kept verbatim)"
            % stats["unblanked"])
    return res


def verify(out, quiet=False):
    """Read every bundle and pack back: each page equals its built file with the tokens
    blanked, byte for byte, and restores to the file itself; each other file equals its
    file and its hash; every built page is in exactly one bundle."""
    log = (lambda *a: None) if quiet else print
    dest = os.path.join(out, "offline")
    with open(os.path.join(dest, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    assets = {u.encode(): m["hash"][:10].encode() for u, m in man["files"].items()
              if u.startswith("/site/") and re.search(r"\.(?:js|css)$", u)}
    stamp = man["stamp"].encode() if man["stamp"] else None
    seen, bad, restored_bad = set(), [], []
    t0 = time.perf_counter()
    for b in man["bundles"]:
        blob = read(os.path.join(dest, b["name"]))
        if sha256(blob) != b["sha256"] or len(blob) != b["size"]:
            bad.append((b["name"], "hash or size"))
            continue
        got = read_pack(blob)
        if len(got) != b["count"]:
            bad.append((b["name"], "count"))
        for aid, body in got.items():
            aid = int(aid)
            if aid in seen:
                bad.append((aid, "twice"))
            seen.add(aid)
            page = read(page_path(out, aid))
            if body != blank(page, assets, stamp):
                bad.append((aid, "differs"))
            if restore(body, assets, stamp) != page:
                restored_bad.append(aid)
    missing = [a for a in article_ids(out) if a not in seen]
    fbad = []
    for p in man["packs"]:
        blob = read(os.path.join(dest, p["name"]))
        if sha256(blob) != p["sha256"]:
            fbad.append((p["name"], "hash"))
            continue
        for url, body in read_pack(blob).items():
            m = man["files"].get(url)
            if m is None or m.get("pack") != p["group"]:
                fbad.append((url, "not in the manifest under this pack"))
                continue
            rel = dict(SHELL_PAGES, **OPTIONAL_PAGES).get(url, url.lstrip("/"))
            disk = read(os.path.join(out, rel))
            if body != disk or sha1(body)[:HASH_HEX] != m["hash"] or len(body) != m["size"]:
                fbad.append((url, "differs"))
    res = {"pages_checked": len(seen), "pages_bad": len(bad), "pages_restore_bad":
           len(restored_bad), "pages_missing": len(missing), "files_checked":
           len(man["files"]), "files_bad": len(fbad), "secs": round(time.perf_counter() - t0, 1),
           "examples": (bad + [(a, "restore") for a in restored_bad] + fbad
                        + [(a, "missing") for a in missing])[:10]}
    log("verify: %(pages_checked)d pages (%(pages_bad)d differ, %(pages_restore_bad)d restore "
        "wrong, %(pages_missing)d missing), %(files_checked)d files (%(files_bad)d bad); "
        "%(secs)s s" % res)
    return res


def shell_pages_help():
    """The shell pages as --help lists them, read from `SHELL_PAGES` and `OPTIONAL_PAGES`."""
    return ("the shell pages (SHELL_PAGES):\n  " + "  ".join(SHELL_PAGES)
            + "\nand, where the build wrote them (OPTIONAL_PAGES):\n  " + "  ".join(OPTIONAL_PAGES))


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=shell_pages_help(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ORDPAR, "out"), help="the built site")
    ap.add_argument("--per", type=int, default=PER, help="pages to a bundle (default %d)" % PER)
    ap.add_argument("--rechunk", action="store_true",
                    help="ignore the previous manifest's bundle boundaries")
    ap.add_argument("--verify", action="store_true",
                    help="only read every bundle back against out/ (writes nothing)")
    ap.add_argument("--json", help="also write the counts to this file")
    a = ap.parse_args()
    res = verify(a.out) if a.verify else build(a.out, a.per, a.rechunk)
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    if a.verify and (res["pages_bad"] or res["pages_restore_bad"] or res["pages_missing"]
                     or res["files_bad"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
