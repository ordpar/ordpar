#!/usr/bin/env python3
"""Run every check in this folder over one input and write one TSV per check.

    python run_all.py ARTICLES OUTDIR [--nynorsk NN_ARTICLES]
                      [--bokmal-forms FILE] [--nynorsk-forms FILE]
                      [--include-unpublished] [--no-embedded]
    python run_all.py NN_ARTICLES OUTDIR --dictionary nn [--bokmal BM_ARTICLES]
                      [--nynorsk-forms FILE] [--bokmal-forms FILE] [...]

ARTICLES is a directory of <id>.json files or a JSONL file (see common.py), Bokmålsordboka
by default or Nynorskordboka with --dictionary nn, which every check is given (the links,
check 6's linking words, check 7's labels and form sets follow it). Each check's
summary line (articles read, skipped, findings, seconds) goes to OUTDIR/summary.txt as
well as to the screen.

Python 3 standard library only, no network.
"""

import argparse
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = ["dangling_sense_refs", "duplicate_definition_ids", "doubled_spaces_words",
          "unmatched_quotes", "empty_cited_articles", "sense_ref_cycles", "word_forms"]
#: the checks that also read embedded copies of fixed expressions (see common.py)
READS_EMBEDDED = {"dangling_sense_refs", "doubled_spaces_words", "unmatched_quotes",
                  "empty_cited_articles", "word_forms"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("outdir")
    ap.add_argument("--dictionary", choices=("bm", "nn"), default="bm",
                    help="which dictionary ARTICLES is (default bm)")
    ap.add_argument("--nynorsk", help="Nynorsk articles, for word_forms (Bokmål mode)")
    ap.add_argument("--bokmal", help="Bokmål articles, for word_forms (Nynorsk mode)")
    ap.add_argument("--bokmal-forms", help="a Bokmål full-form list, for word_forms")
    ap.add_argument("--nynorsk-forms", help="a Nynorsk full-form list, for word_forms")
    ap.add_argument("--include-unpublished", action="store_true")
    ap.add_argument("--no-embedded", action="store_true",
                    help="do not read the embedded copies of fixed expressions, in the "
                         "checks that read them")
    a = ap.parse_args(argv)
    os.makedirs(a.outdir, exist_ok=True)
    lines, status = [], 0
    for name in CHECKS:
        cmd = [sys.executable, os.path.join(HERE, name + ".py"), a.input,
               "-o", os.path.join(a.outdir, name + ".tsv"), "--dictionary", a.dictionary]
        if a.include_unpublished:
            cmd.append("--include-unpublished")
        if a.no_embedded and name in READS_EMBEDDED:
            cmd.append("--no-embedded")
        if name == "word_forms":
            for flag, val in (("--nynorsk", a.nynorsk), ("--bokmal", a.bokmal),
                              ("--bokmal-forms", a.bokmal_forms),
                              ("--nynorsk-forms", a.nynorsk_forms)):
                if val:
                    cmd += [flag, val]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run(cmd, stderr=subprocess.PIPE, env=env)
        err = p.stderr.decode("utf-8", "replace")
        sys.stderr.write(err)
        lines.append(err)
        status = max(status, p.returncode)
    with io.open(os.path.join(a.outdir, "summary.txt"), "w", encoding="utf-8",
                 newline="\n") as f:
        f.write("".join(lines))
    return status


if __name__ == "__main__":
    sys.exit(main())
