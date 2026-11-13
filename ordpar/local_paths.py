#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The paths that belong to one machine, read from one git-ignored file.

Some of the site's tools need a path outside the repository: the mirror's `bm-articles.jsonl`,
the National Library's 1-gram file, the deploy clone, the audio clip store's forwarding table,
the folder the public export is written to. None of these is the same on two machines, so none
is written in the code. They live in `ordpar/local-paths.json`, which git ignores; its shape is
`ordpar/local-paths.example.json`, which is committed:

    {"mirror": "/data/ordbokene/bm-articles.jsonl", "freq": "...", ...}

A key may be missing, or the file may not exist at all: `get(key)` then returns None, and a tool
that cannot go on without the path calls `require(key, flag)`, which stops with a message naming
the key, the file and the command-line flag that gives the path instead. A flag on the command
line always wins over the file.

The keys:

    mirror                 the mirror's bm-articles.jsonl (build_site.py, build_index.py --mirror;
                           tests that read the real mirror skip without it)
    freq                   the National Library's N-gram 2026 1-gram file (build_index.py --freq)
    deploy_clone           the clone deploy.py publishes from (deploy.py --clone)
    clip_store_forwarding  the audio clip store's forwarding.json (audio-worker/sync_forwarding.py)
    public_export          the folder export_public.py writes the public repository into (--target)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "local-paths.json")
EXAMPLE = os.path.join(HERE, "local-paths.example.json")
KEYS = ("mirror", "freq", "deploy_clone", "clip_store_forwarding", "public_export")

_cache = {}


class Missing(SystemExit):
    """A tool needed a path that neither its flag nor the local file gave."""


def load(path=None):
    """The local file as a dict ({} when it does not exist). A file that is not a JSON object,
    or that names a key this module does not know, is refused: a misspelt key would otherwise
    read as unset."""
    path = path or PATH
    if path in _cache:
        return _cache[path]
    if not os.path.exists(path):
        data = {}
    else:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("%s: expected a JSON object" % path)
        unknown = sorted(set(data) - set(KEYS))
        if unknown:
            raise ValueError("%s: unknown key(s) %s; the keys are %s"
                             % (path, ", ".join(unknown), ", ".join(KEYS)))
    _cache[path] = data
    return data


def get(key, path=None):
    """The path stored under ``key``, or None."""
    if key not in KEYS:
        raise KeyError(key)
    value = load(path).get(key)
    return value or None


def require(key, flag=None, path=None):
    """The path under ``key``; stops with a clear message when it is unset."""
    value = get(key, path)
    if value:
        return value
    how = ("pass %s, or " % flag) if flag else ""
    raise Missing("no path for %r: %sset it in %s (a JSON object; see %s for its shape)"
                  % (key, how, _shown(path or PATH), _shown(EXAMPLE)))


def _shown(p):
    try:
        return os.path.relpath(p)
    except ValueError:              # another drive (Windows)
        return p


def main(argv=None):
    """``python ordpar/local_paths.py KEY`` prints the path, for a shell command:
    ``--mirror "$(python ordpar/local_paths.py mirror)"``. Exit 1, with the message, when unset."""
    import sys
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("usage: python ordpar/local_paths.py KEY    (KEY: %s)" % ", ".join(KEYS))
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    if argv[0] not in KEYS:
        print("unknown key %r; the keys are %s" % (argv[0], ", ".join(KEYS)), file=sys.stderr)
        return 2
    try:
        print(require(argv[0]))
    except Missing as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
