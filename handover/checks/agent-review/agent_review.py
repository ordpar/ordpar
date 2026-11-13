#!/usr/bin/env python3
"""Sort check 7's candidates with reader agents: packets, batches, verdicts, the merge.

    python agent_review.py [--state DIR] packets WORD_FORMS_TSV [--articles ARTICLES]
                           [--bokmal-forms FILE] [--include-unpublished]
    python agent_review.py [--state DIR] queue --pass 1 [--batch 25] [--seed N] [--sample N]
    python agent_review.py [--state DIR] queue --pass 2 [--batch 25] [--seed N]
                           [--include-unsure] [--dry-run]
    python agent_review.py [--state DIR] take --as TAG [--pass N]   # a reader claims a batch
    python agent_review.py [--state DIR] submit BATCH FILE [--override]
    python agent_review.py [--state DIR] release BATCH              # un-claim a failed batch
    python agent_review.py [--state DIR] status
    python agent_review.py [--state DIR] forms WORD [WORD ...]      # the readers' lookup
    python agent_review.py [--state DIR] disputed
    python agent_review.py [--state DIR] merge -o FILE [--format csv|md] [--all]

All working files live in the state folder (default ./review-state):
  packets.jsonl     one packet per distinct (article, word) of word_forms.py's output;
  lexicon.json      the Bokmal forms with their counts and owners (only with --articles);
  passN/queue.json  the batches of pass N; passN/claim_<B> a reader's claim (created
                    exclusively, so two readers never hold one batch); passN/out/<B>.jsonl
                    where the reader writes; passN/done/<B>.jsonl the verdicts as recorded.
A batch id is p<pass>-<NNN>, for example p1-007.

packets   Cuts word_forms.py's TSV into packets: every row of one word in one article
          becomes one packet, with every place it stands. Without --articles a packet
          carries the text element of each place (``texts``). With --articles (the same
          article input word_forms.py read; this needs common.py and word_forms.py in the
          folder above this one) it carries instead the whole sense the word stands in
          (every explanation and example), the article's other senses in one line each,
          and the known Bokmal forms one edit away (``nearest``), each with its count in
          the dictionary's own definition and example text and the articles whose
          inflection table holds it. It then also writes lexicon.json, which ``forms``
          and ``submit`` use. --bokmal-forms adds a full-form list (Norsk ordbank's
          fullformsliste.txt, or one form per line), as word_forms.py does.
queue     Pass 1: every packet without a mark, plus every packet marked ``compound``
          or, with --sample N, a seeded random N of them; shuffled with the same seed
          so each batch mixes them. Refuses if pass 1 is queued already. Pass 2: every
          packet that a done pass-1 batch called ``slip`` (and ``unsure`` too, with
          --include-unsure) that pass 2 does not hold yet; run it again after more
          pass-1 batches are done and it adds their packets, numbering on. --dry-run
          lists the keys without queuing.
take      Claims the next open batch of the pass (default: the highest pass queued) and
          prints its id, the file to write, the submit command and one JSON packet per
          line. The ``mark`` is left out, and pass 2 shows the same packet as pass 1,
          with nothing of pass 1's verdict. Prints a line starting "nothing left" when
          no batch is open.
submit    Checks the reader's file against the batch and records it, or refuses it and
          lists every problem; nothing is recorded until the file is clean. One JSON
          object per line, one per packet, each key once and no other key. Fields:
            key, verdict (slip | valid | unsure),
            kind (misspelling | nynorsk_form | missing_space | extra_space | inflection |
              other; required for a slip; null for valid; null, one of these or
              joint_variant for unsure),
            confidence (high | reasonable | low),
            correction (a non-empty string for a slip and a joint_variant; null for
              valid; null or a string for unsure),
            reason (non-empty), and optionally
            also (a non-empty list of {"text", "correction", "reason"}: other slips the
              reader saw in the same text) and override_reason (below).
          When lexicon.json exists, every word of a slip's correction that is not
          already in the packet must be a known Bokmal form; if one is not, the file is
          refused with an advisory. With --override, each such row must carry an
          ``override_reason``, and it is recorded with ``flagged: true``.
release   Un-claims a batch whose reader failed, so another can take it.
status    Per pass: batches open, claimed and done; verdict counts; flagged rows.
forms     For each word: the articles whose inflection table holds it and its count; or,
          if it is not a known form, its nearest known forms (needs lexicon.json).
disputed  The packets a person must read: the two passes disagree, or pass 1 said
          unsure. One line each.
merge     One row per packet read, both passes side by side, with an ``outcome``:
          slip (both passes), disputed, unsure, slip (one pass only: pass 2 has not read
          it), valid; --all adds the packets nobody read, as "not read". CSV, or a
          Markdown table with --format md. It decides nothing: an editor does.

Python 3 standard library only, no network.
"""

import argparse
import collections
import csv
import datetime
import io
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)  # as word_forms.py
DEF_ID = re.compile(r"definisjon id (\d+)")
COPY_PLACE = re.compile(r'^artikkel \S+, uttrykk "(.*)" \((\d+)\), ')
BATCH = re.compile(r"p(\d+)-(\d{3,})\Z")
COLUMNS = ("article_id", "lemma", "location", "type", "word", "occurrences", "context")

VERDICTS = ("slip", "valid", "unsure")
KINDS = ("misspelling", "nynorsk_form", "missing_space", "extra_space", "inflection", "other")
JOINT = "joint_variant"
CONFIDENCES = ("high", "reasonable", "low")
REQUIRED = ("key", "verdict", "kind", "confidence", "correction", "reason")
FIELDS = REQUIRED + ("also", "override_reason")
HIDDEN = ("mark",)          # what a packet is expected to be: never shown to a reader
OUTCOMES = ("slip", "disputed", "unsure", "slip (one pass)", "valid", "not read")


class Refused(Exception):
    """A command that changed nothing; the message says why."""


def nonempty(v):
    return isinstance(v, str) and v.strip() != ""


def words_of(text):
    return [t.lower() for t in TOKEN.findall(text or "")]


def checks_modules():
    """common.py and word_forms.py from the folder above (handover/checks/)."""
    up = os.path.dirname(HERE)
    if not (os.path.exists(os.path.join(up, "common.py"))
            and os.path.exists(os.path.join(up, "word_forms.py"))):
        raise Refused("--articles needs common.py and word_forms.py in %s" % up)
    if up not in sys.path:
        sys.path.insert(0, up)
    import common
    import word_forms
    return common, word_forms


def write_json(path, obj, indent=1):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")
    os.replace(tmp, path)


def read_jsonl(path):
    out = []
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line, object_pairs_hook=collections.OrderedDict))
    return out


# --- the lexicon: known forms, their counts and the articles that hold them ---------------

class Lexicon(object):
    def __init__(self, counts, owners, heads):
        self.counts = counts          # form -> count in the dictionary's own text
        self.owners = owners          # form -> [article id] whose table holds it
        self.heads = heads            # article id (str) -> [headwords]
        self.letters = sorted({c for f in counts for c in f if c.isalpha()})

    @classmethod
    def load(cls, path):
        with io.open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls(d["counts"], d["owners"], d["heads"])

    def save(self, path):
        write_json(path, {"counts": self.counts, "owners": self.owners, "heads": self.heads},
                   indent=None)

    def known(self, w):
        """As word_forms.known: a form, a genitive in -s of one, or a hyphenated word whose
        parts are forms (or two letters or fewer)."""
        if w in self.counts:
            return True
        if len(w) > 3 and w.endswith("s") and w[:-1] in self.counts:
            return True
        parts = [p for p in re.split(r"[-'’]", w) if p]
        return len(parts) > 1 and all(p in self.counts or len(p) <= 2 for p in parts)

    def lemmas(self, form):
        return [collections.OrderedDict([("article_id", a), ("headwords", self.heads.get(a, []))])
                for a in self.owners.get(form, [])]

    def entry(self, form):
        e = collections.OrderedDict([("form", form), ("count", self.counts.get(form, 0))])
        lem = self.lemmas(form)
        if lem:
            e["lemmas"] = lem
        return e

    def nearest(self, w, n=5):
        """Up to n known forms one edit away (a letter deleted, added or changed, or two
        neighbours swapped), commoner first."""
        cand = set()
        for i in range(len(w) + 1):
            a, b = w[:i], w[i:]
            if b:
                cand.add(a + b[1:])
                cand.update(a + c + b[1:] for c in self.letters)
            if len(b) > 1:
                cand.add(a + b[1] + b[0] + b[2:])
            cand.update(a + c + b for c in self.letters)
        cand.discard(w)
        found = sorted((f for f in cand if f in self.counts),
                       key=lambda f: (-self.counts[f], f))[:n]
        return [self.entry(f) for f in found]

    def lookup(self, w):
        w = w.lower()
        if self.known(w):
            out = self.entry(w)
            out["known"] = True
            return out
        return collections.OrderedDict([("form", w), ("known", False),
                                        ("nearest", self.nearest(w))])


def build_lexicon(articles, common, wf, bokmal_forms=None):
    """One pass over every article: its forms, its own text's word counts."""
    counts, owners, heads = collections.Counter(), {}, {}
    for art in articles:
        aid = str(common.article_id(art))
        heads[aid] = [l.get("lemma") for l in art.get("lemmas") or [] if l.get("lemma")]
        for f in wf.forms_of(art):
            owners.setdefault(f, [])
            if aid not in owners[f]:
                owners[f].append(aid)
        for _loc, _kind, content, items in common.iter_text(art, etymology=False):
            counts.update(words_of(common.render(content, items, words=True)))
    known = set(owners)
    if bokmal_forms:
        known |= wf.read_form_list(bokmal_forms)
    return Lexicon({f: counts.get(f, 0) for f in known}, owners, heads)


# --- packets -------------------------------------------------------------------------------

def read_findings(path):
    with io.open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines:
        raise Refused("%s is empty" % path)
    head = lines[0].split("\t")
    miss = [c for c in COLUMNS if c not in head]
    if miss:
        raise Refused("%s lacks the column(s) %s; is it word_forms.py's output?"
                      % (path, ", ".join(miss)))
    rows = []
    for n, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) < len(head):
            cells += [""] * (len(head) - len(cells))
        r = dict(zip(head, cells))
        r["context"] = r["context"].replace("\\n", "\n").replace("\\t", "\t")
        rows.append(r)
    return rows


def group_findings(rows):
    """(article_id, word) -> its rows, in the TSV's order (rarest words first)."""
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault((r["article_id"], r["word"]), []).append(r)
    return groups


def base_packet(rows):
    r0 = rows[0]
    aid = r0["article_id"]
    p = collections.OrderedDict()
    p["key"] = "%s-%s" % (aid, r0["word"])
    p["article_id"] = int(aid) if aid.isdigit() else aid
    p["link"] = "https://ordbokene.no/nob/bm/%s" % aid
    p["headwords"] = [h for h in r0["lemma"].split(", ") if h]
    p["word"] = r0["word"]
    p["type"] = r0["type"]
    p["occurrences"] = int(r0["occurrences"]) if r0["occurrences"].isdigit() else r0["occurrences"]
    p["mark"] = r0.get("mark", "")
    p["places"] = [r["location"] for r in rows]
    return p


def explanations(common, node):
    return [common.render(e.get("content"), e.get("items"))
            for e in node.get("elements") or [] if e.get("type_") == "explanation"]


def examples(common, node):
    out = []
    for e in node.get("elements") or []:
        if e.get("type_") != "example":
            continue
        q, x = e.get("quote") or {}, e.get("explanation") or {}
        ex = collections.OrderedDict([("quote", common.render(q.get("content"), q.get("items")))])
        if (x.get("content") or "").strip() or x.get("items"):
            ex["explanation"] = common.render(x.get("content"), x.get("items"))
        out.append(ex)
    return out


def short(text, n=100):
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def add_context(p, art, common, lex):
    """The whole sense, the other senses and the nearest forms, from the article itself.
    A finding in an embedded copy of a fixed expression reads the copy's senses."""
    sense_art = art
    m = COPY_PLACE.match(p["places"][0])
    if m:
        for sub in common.embedded_copies(art):
            if str(sub.get("article_id")) == m.group(2):
                sense_art = sub["article"]
                p["expression"] = collections.OrderedDict(
                    [("article_id", int(m.group(2))), ("headword", m.group(1))])
                break
    labels = common.sense_labels(sense_art)
    nodes = common.own_definition_nodes(sense_art)
    by_id = {}
    for nd in nodes:
        by_id.setdefault(str(nd.get("id")), nd)
    ids = []
    for place in p["places"]:
        d = DEF_ID.search(place)
        if d and d.group(1) not in ids:
            ids.append(d.group(1))
    senses, seen = [], set()
    for did in ids:
        nd = by_id.get(did)
        if nd is None:
            continue
        seen.add(id(nd))
        senses.append(collections.OrderedDict([
            ("sense", labels.get(id(nd), "")), ("definition_id", nd.get("id")),
            ("definitions", explanations(common, nd)), ("examples", examples(common, nd))]))
    p["senses"] = senses
    p["other_senses"] = [short("%s: %s" % (labels[id(nd)], " / ".join(explanations(common, nd))
                                           or "(no explanation)"))
                         for nd in nodes if id(nd) not in seen and id(nd) in labels]
    p["nearest"] = lex.nearest(p["word"])


def build_packets(tsv, articles=None, bokmal_forms=None, include_unpublished=False):
    """(packets, lexicon or None). Without ``articles`` each packet carries the text
    element of each place (``texts``); with it, the senses and the nearest forms."""
    groups = group_findings(read_findings(tsv))
    if not articles:
        out = []
        for rows in groups.values():
            p = base_packet(rows)
            p["texts"] = list(collections.OrderedDict.fromkeys(r["context"] for r in rows))
            out.append(p)
        return out, None
    common, wf = checks_modules()
    want = {aid for aid, _w in groups}
    kept = {}

    def stream():
        for art in common.Reader(articles, include_unpublished):
            aid = str(common.article_id(art))
            if aid in want:
                kept[aid] = art
            yield art
    lex = build_lexicon(stream(), common, wf, bokmal_forms)
    out = []
    for (aid, _w), rows in groups.items():
        p = base_packet(rows)
        if aid in kept:
            add_context(p, kept[aid], common, lex)
        else:
            p["texts"] = list(collections.OrderedDict.fromkeys(r["context"] for r in rows))
        out.append(p)
    return out, lex


# --- the state folder ----------------------------------------------------------------------

def pass_of(b):
    m = BATCH.match(b or "")
    if not m:
        raise Refused("%r is not a batch id (they look like p1-007)" % b)
    return int(m.group(1))


class State(object):
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self._packets = self._lex = None

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    def queue_path(self, n):
        return self.p("pass%d" % n, "queue.json")

    def queue(self, n):
        path = self.queue_path(n)
        if not os.path.exists(path):
            return None
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)

    def passes(self):
        return [n for n in (1, 2) if os.path.exists(self.queue_path(n))]

    def claim(self, b):
        return self.p("pass%d" % pass_of(b), "claim_%s" % b)

    def out(self, b):
        return self.p("pass%d" % pass_of(b), "out", "%s.jsonl" % b)

    def done(self, b):
        return self.p("pass%d" % pass_of(b), "done", "%s.jsonl" % b)

    def packets(self):
        if self._packets is None:
            path = self.p("packets.jsonl")
            if not os.path.exists(path):
                raise Refused("no packets in %s; run 'packets' first" % self.root)
            self._packets = collections.OrderedDict((pk["key"], pk) for pk in read_jsonl(path))
        return self._packets

    def lexicon(self):
        if self._lex is None and os.path.exists(self.p("lexicon.json")):
            self._lex = Lexicon.load(self.p("lexicon.json"))
        return self._lex

    def batches(self, n):
        return [b["id"] for b in (self.queue(n) or {}).get("batches", [])]

    def batch_keys(self, b):
        for x in (self.queue(pass_of(b)) or {}).get("batches", []):
            if x["id"] == b:
                return x["keys"]
        return None

    def state_of(self, b):
        if os.path.exists(self.done(b)):
            return "done"
        return "claimed" if os.path.exists(self.claim(b)) else "open"

    def verdicts(self, n):
        out = collections.OrderedDict()
        for b in self.batches(n):
            if os.path.exists(self.done(b)):
                for r in read_jsonl(self.done(b)):
                    out[r["key"]] = r
        return out


def reader_view(pk):
    return collections.OrderedDict((k, v) for k, v in pk.items() if k not in HIDDEN)


def save_packets(st, packets, lex):
    if os.path.exists(st.p("packets.jsonl")) and st.passes():
        raise Refused("a pass is queued in %s; packets are not rebuilt under it" % st.root)
    os.makedirs(st.root, exist_ok=True)
    with io.open(st.p("packets.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for p in packets:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    if lex is not None:
        lex.save(st.p("lexicon.json"))
    st._packets = None


# --- queue / take / release ----------------------------------------------------------------

def cut(keys, size, n, start=0):
    return [{"id": "p%d-%03d" % (n, start + i + 1), "keys": keys[j:j + size]}
            for i, j in enumerate(range(0, len(keys), size))]


def queue(st, n, batch=25, seed=1, sample=None, include_unsure=False, dry_run=False):
    """Queue pass n; returns (the new batches, a line saying what was queued)."""
    pk = st.packets()
    rng = random.Random(seed)
    if n == 1:
        if st.queue(1) is not None:
            raise Refused("pass 1 is already queued; nothing changed")
        unmarked = [k for k, p in pk.items() if not p.get("mark")]
        marked = sorted(k for k, p in pk.items() if p.get("mark"))
        chosen = marked if sample is None else sorted(rng.sample(marked, min(sample, len(marked))))
        keys = unmarked + chosen
        rng.shuffle(keys)
        new = cut(keys, batch, 1)
        q = {"pass": 1, "seed": seed, "batch_size": batch, "unmarked": len(unmarked),
             "marked": len(marked), "marked_read": chosen, "batches": new}
        what = "%d unmarked + %d of %d marked" % (len(unmarked), len(chosen), len(marked))
    elif n == 2:
        if st.queue(1) is None:
            raise Refused("pass 1 is not queued; pass 2 reads pass 1's results")
        want = ("slip", "unsure") if include_unsure else ("slip",)
        q = st.queue(2) or {"pass": 2, "seed": seed, "batch_size": batch, "batches": []}
        have = {k for b in q["batches"] for k in b["keys"]}
        keys = sorted(k for k, r in st.verdicts(1).items()
                      if r["verdict"] in want and k not in have)
        if dry_run:
            return [{"id": None, "keys": keys}], "%d packets would go to pass 2" % len(keys)
        if not keys:
            raise Refused("no packet from a done pass-1 batch waits for pass 2; nothing changed")
        rng.shuffle(keys)
        new = cut(keys, batch, 2, start=len(q["batches"]))
        q["batches"].extend(new)
        left = sum(1 for b in st.batches(1) if st.state_of(b) != "done")
        what = "%d packets pass 1 called %s" % (len(keys), " or ".join(want))
        if left:
            what += " (%d pass-1 batches not done yet: queue pass 2 again after them)" % left
    else:
        raise Refused("there are two passes, 1 and 2")
    write_json(st.queue_path(n), q)
    for d in ("out", "done"):
        os.makedirs(st.p("pass%d" % n, d), exist_ok=True)
    return new, ("pass %d queued: %s -> %d packets in %d batches"
                 % (n, what, sum(len(b["keys"]) for b in new), len(new)))


def take(st, tag, n=None):
    """Claim the next open batch: {"batch", "pass", "out", "packets"}, or None."""
    if not nonempty(tag) or not re.match(r"[\w.-]+\Z", tag):
        raise Refused("--as needs a tag of letters, digits, '.', '-' or '_'")
    n = n or (st.passes() or [None])[-1]
    if n is None or st.queue(n) is None:
        return None
    pk = st.packets()
    for b in st.batches(n):
        if st.state_of(b) != "open":
            continue
        try:
            fd = os.open(st.claim(b), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue                    # another reader got there first
        os.write(fd, tag.encode("utf-8"))
        os.close(fd)
        return {"batch": b, "pass": n, "out": st.out(b),
                "packets": [reader_view(pk[k]) for k in st.batch_keys(b)]}
    return None


def release(st, b):
    if st.batch_keys(b) is None:
        raise Refused("no batch %s in the queue" % b)
    if os.path.exists(st.done(b)):
        raise Refused("batch %s is already submitted; nothing to release" % b)
    if not os.path.exists(st.claim(b)):
        return "%s was not claimed; nothing changed" % b
    os.remove(st.claim(b))
    return "released %s" % b


# --- submit --------------------------------------------------------------------------------

def packet_words(view):
    out = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            out.update(words_of(x))
    walk(view)
    return out


def check_row(r, who):
    probs = []
    extra = [x for x in r if x not in FIELDS]
    if extra:
        probs.append("%s: unknown field(s) %s; the fields are %s"
                     % (who, ", ".join(extra), ", ".join(FIELDS)))
    miss = [x for x in REQUIRED if x not in r]
    if miss:
        probs.append("%s: missing field(s) %s (write null where null is meant)"
                     % (who, ", ".join(miss)))
    v, kind, corr = r.get("verdict"), r.get("kind"), r.get("correction")
    if v not in VERDICTS:
        probs.append("%s: verdict %r must be one of %s" % (who, v, "/".join(VERDICTS)))
    if v == "slip":
        if kind not in KINDS:
            probs.append("%s: a slip's kind %r must be one of %s" % (who, kind, "/".join(KINDS)))
        if not nonempty(corr):
            probs.append("%s: a slip needs a correction, a non-empty string" % who)
    if v == "valid":
        if kind is not None:
            probs.append("%s: kind must be null for valid (got %r)" % (who, kind))
        if corr is not None:
            probs.append("%s: correction must be null for valid (got %r)" % (who, corr))
    if v == "unsure":
        if kind is not None and kind not in KINDS + (JOINT,):
            probs.append("%s: an unsure row's kind is null or one of %s (got %r)"
                         % (who, "/".join(KINDS + (JOINT,)), kind))
        if kind == JOINT and not nonempty(corr):
            probs.append("%s: a %s row needs the headword's form as its correction" % (who, JOINT))
        elif corr is not None and not nonempty(corr):
            probs.append("%s: an unsure row's correction is null or a non-empty string" % who)
    if r.get("confidence") not in CONFIDENCES:
        probs.append("%s: confidence %r must be one of %s"
                     % (who, r.get("confidence"), "/".join(CONFIDENCES)))
    if not nonempty(r.get("reason")):
        probs.append("%s: reason must be a non-empty string" % who)
    ov = r.get("override_reason")
    if ov is not None and not nonempty(ov):
        probs.append("%s: override_reason, when given, must be a non-empty string" % who)
    also = r.get("also")
    if also is not None and not (isinstance(also, list) and also and all(
            isinstance(x, dict) and set(x) == {"text", "correction", "reason"}
            and all(nonempty(x[f]) for f in x) for x in also)):
        probs.append('%s: also, when given, is a non-empty list of {"text", "correction", '
                     '"reason"}, each a non-empty string' % who)
    return probs


def validate(st, b, path, override=False):
    """(rows by key, problems, advisory) for the reader's file against batch b."""
    keys = st.batch_keys(b)
    try:
        with io.open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return {}, ["cannot read %s: %s" % (path, e)], []
    rows, probs, advisory = collections.OrderedDict(), [], []
    want = set(keys)
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError as e:
            probs.append("line %d: not valid JSON (%s)" % (i, e))
            continue
        if not isinstance(r, dict):
            probs.append("line %d: not a JSON object" % i)
            continue
        k = r.get("key")
        who = "line %d (%s)" % (i, k)
        if k not in want:
            probs.append("%s: the key is not in batch %s" % (who, b))
            continue
        if k in rows:
            probs.append("%s: the key appears more than once" % who)
            continue
        rows[k] = r
        probs.extend(check_row(r, who))
    for k in keys:
        if k not in rows:
            probs.append("%s: no line for this packet (every packet of the batch needs one)" % k)
    lex = st.lexicon()
    if lex is not None:
        pk = st.packets()
        for k, r in rows.items():
            if r.get("verdict") != "slip" or not nonempty(r.get("correction")):
                continue
            seen = packet_words(reader_view(pk[k]))
            bad = [w for w in dict.fromkeys(words_of(r["correction"]))
                   if w not in seen and not lex.known(w)]
            if not bad:
                continue
            r["_unknown"] = bad
            if not override:
                advisory.append("%s: %s" % (k, ", ".join(bad)))
            elif not nonempty(r.get("override_reason")):
                probs.append("%s: the correction uses %s, in neither the packet nor the known "
                             "Bokmal forms; --override needs this row's override_reason"
                             % (k, ", ".join(bad)))
    return rows, probs, advisory


def submit(st, b, path, override=False):
    keys = st.batch_keys(b)
    if keys is None:
        raise Refused("no batch %s in the queue" % b)
    if os.path.exists(st.done(b)):
        raise Refused("batch %s is already submitted; nothing changed" % b)
    if not os.path.exists(st.claim(b)):
        raise Refused("batch %s is not claimed; take it first (or it was released)" % b)
    rows, probs, advisory = validate(st, b, path, override)
    if probs or advisory:
        msg = ["REFUSED %s - nothing recorded. Fix these and submit the same file again:" % b]
        msg += ["  " + p for p in probs]
        if advisory:
            msg.append("  ADVISORY - a slip's correction must be real Bokmal. These rows use "
                       "words that are neither in the packet nor known Bokmal forms:")
            msg += ["    " + x for x in advisory]
            msg.append("  Check each word. If the correction is right as written, submit again "
                       "with --override, giving each of these rows an \"override_reason\".")
        raise Refused("\n".join(msg))
    with io.open(st.claim(b), encoding="utf-8") as f:
        tag = f.read().strip()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    flagged = 0
    tmp = st.done(b) + ".tmp"
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for k in keys:
            r = rows[k]
            rec = collections.OrderedDict((x, r.get(x)) for x in REQUIRED)
            for x in ("also", "override_reason"):
                if r.get(x) is not None:
                    rec[x] = r[x]
            rec["flagged"] = bool(r.get("_unknown"))
            if rec["flagged"]:
                rec["unknown_words"] = r["_unknown"]
                flagged += 1
            rec.update([("batch", b), ("tag", tag), ("submitted", now)])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    os.replace(tmp, st.done(b))
    os.remove(st.claim(b))
    c = collections.Counter(rows[k]["verdict"] for k in keys)
    return "ACCEPTED %s: %d verdicts (%s); %d flagged" % (
        b, len(keys), ", ".join("%s %d" % (v, c[v]) for v in VERDICTS), flagged)


# --- status / outcomes / merge -------------------------------------------------------------

def status(st):
    if not st.passes():
        return "nothing queued in %s" % st.root
    out = []
    for n in st.passes():
        c = collections.Counter(st.state_of(b) for b in st.batches(n))
        v = st.verdicts(n)
        vc = collections.Counter(r["verdict"] for r in v.values())
        out.append("pass %d: %d batches (%d open, %d claimed, %d done); %d verdicts: %s; "
                   "%d flagged" % (n, len(st.batches(n)), c["open"], c["claimed"], c["done"],
                                   len(v), ", ".join("%s %d" % (x, vc[x]) for x in VERDICTS),
                                   sum(1 for r in v.values() if r.get("flagged"))))
    return "\n".join(out)


def outcome(r1, r2):
    if r1 is None:
        return "not read"
    v1, v2 = r1["verdict"], (r2 or {}).get("verdict")
    if v1 == "slip":
        if v2 is None:
            return "slip (one pass)"
        return "slip" if v2 == "slip" else "disputed"
    if v1 == "unsure":
        return "disputed" if v2 == "slip" else "unsure"
    return "valid"


def outcomes(st, everything=False):
    """One OrderedDict per packet read (or every packet), sorted by outcome, then by the
    packets' own order."""
    v1, v2 = st.verdicts(1), st.verdicts(2)
    rows = []
    for i, (k, p) in enumerate(st.packets().items()):
        r1, r2 = v1.get(k), v2.get(k)
        oc = outcome(r1, r2)
        if oc == "not read" and not everything:
            continue
        row = collections.OrderedDict()
        row["outcome"] = oc
        row["article_id"] = p["article_id"]
        row["headwords"] = ", ".join(p.get("headwords") or [])
        row["link"] = p.get("link", "")
        row["word"] = p["word"]
        row["places"] = " | ".join(p.get("places") or [])
        for tag, r in (("pass1", r1), ("pass2", r2)):
            for f in ("verdict", "kind", "confidence", "correction", "reason"):
                row["%s_%s" % (tag, f)] = (r or {}).get(f) or ""
        also = []
        for r in (r1, r2):
            for x in (r or {}).get("also") or []:
                also.append("%s -> %s (%s)" % (x["text"], x["correction"], x["reason"]))
        row["also"] = " | ".join(also)
        row["flagged"] = "yes" if any((r or {}).get("flagged") for r in (r1, r2)) else ""
        row["_order"] = (OUTCOMES.index(oc), i)
        rows.append(row)
    rows.sort(key=lambda r: r["_order"])
    for r in rows:
        del r["_order"]
    return rows


def disputed(st):
    return [r for r in outcomes(st) if r["outcome"] in ("disputed", "unsure")]


def md_cell(x):
    return str(x).replace("|", "\\|").replace("\n", " ")


def merge(st, path, fmt="csv", everything=False):
    rows = outcomes(st, everything)
    cols = list(rows[0].keys()) if rows else ["outcome"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if fmt == "csv":
        with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c] for c in cols])
    else:
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("| " + " | ".join(cols) + " |\n")
            f.write("|" + "---|" * len(cols) + "\n")
            for r in rows:
                f.write("| " + " | ".join(md_cell(r[c]) for c in cols) + " |\n")
    c = collections.Counter(r["outcome"] for r in rows)
    return "wrote %d rows to %s: %s" % (len(rows), path,
                                        ", ".join("%s %d" % (o, c[o]) for o in OUTCOMES if c[o]))


# --- the command line ----------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default="review-state",
                    help="the folder that holds every working file (default ./review-state)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("packets", help="cut word_forms.py's output into packets")
    s.add_argument("tsv", help="word_forms.py's output (TSV)")
    s.add_argument("--articles", help="the article input word_forms.py read (directory or JSONL)")
    s.add_argument("--bokmal-forms", help="a Bokmal full-form list to add, as for word_forms.py")
    s.add_argument("--include-unpublished", action="store_true",
                   help="read unpublished articles too (use it if word_forms.py did)")
    s = sub.add_parser("queue", help="cut the packets of a pass into batches")
    s.add_argument("--pass", dest="pass_", type=int, required=True, choices=(1, 2))
    s.add_argument("--batch", type=int, default=25, help="packets per batch (default 25)")
    s.add_argument("--seed", type=int, default=1, help="the shuffle's seed (default 1)")
    s.add_argument("--sample", type=int, help="pass 1: read only N of the marked packets")
    s.add_argument("--include-unsure", action="store_true",
                   help="pass 2: re-read pass 1's unsure packets as well as its slips")
    s.add_argument("--dry-run", action="store_true", help="pass 2: list the keys only")
    s = sub.add_parser("take", help="claim the next open batch and print it")
    s.add_argument("--as", dest="tag", required=True, help="the reader's own tag, e.g. r01")
    s.add_argument("--pass", dest="pass_", type=int, choices=(1, 2))
    s = sub.add_parser("submit", help="check a verdict file and record it")
    s.add_argument("batch")
    s.add_argument("file")
    s.add_argument("--override", action="store_true",
                   help="accept corrections outside the known forms, each with override_reason")
    s = sub.add_parser("release", help="un-claim a batch whose reader failed")
    s.add_argument("batch")
    sub.add_parser("status", help="batches and verdicts per pass")
    s = sub.add_parser("forms", help="look words up among the known Bokmal forms")
    s.add_argument("words", nargs="+")
    sub.add_parser("disputed", help="the packets a person must read")
    s = sub.add_parser("merge", help="both passes in one file for the editors")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--format", choices=("csv", "md"), default="csv")
    s.add_argument("--all", action="store_true", help="include the packets nobody read")
    a = ap.parse_args(argv)
    st = State(a.state)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    out = sys.stdout
    try:
        if a.cmd == "packets":
            pks, lex = build_packets(a.tsv, a.articles, a.bokmal_forms, a.include_unpublished)
            save_packets(st, pks, lex)
            out.write("%d packets from %s in %s%s\n" % (
                len(pks), a.tsv, st.root, "; lexicon.json written" if lex else ""))
        elif a.cmd == "queue":
            new, line = queue(st, a.pass_, a.batch, a.seed, a.sample, a.include_unsure, a.dry_run)
            out.write(line + "\n")
            if a.dry_run:
                out.write("".join(k + "\n" for k in new[0]["keys"]))
        elif a.cmd == "take":
            got = take(st, a.tag, a.pass_)
            if got is None:
                out.write("nothing left: no open batch\n")
            else:
                me = os.path.abspath(__file__)
                out.write("batch %s (pass %d, %d packets)\n" % (got["batch"], got["pass"],
                                                                len(got["packets"])))
                out.write("write your verdicts to: %s\n" % got["out"])
                out.write('then run: python "%s" --state "%s" submit %s "%s"\n'
                          % (me, st.root, got["batch"], got["out"]))
                out.write("packets, one JSON object per line:\n")
                for p in got["packets"]:
                    out.write(json.dumps(p, ensure_ascii=False) + "\n")
        elif a.cmd == "submit":
            out.write(submit(st, a.batch, a.file, a.override) + "\n")
        elif a.cmd == "release":
            out.write(release(st, a.batch) + "\n")
        elif a.cmd == "status":
            out.write(status(st) + "\n")
        elif a.cmd == "forms":
            lex = st.lexicon()
            if lex is None:
                raise Refused("no lexicon.json in %s; build the packets with --articles" % st.root)
            for w in a.words:
                out.write(json.dumps(lex.lookup(w), ensure_ascii=False) + "\n")
        elif a.cmd == "disputed":
            rows = disputed(st)
            for r in rows:
                out.write("%s\t%s\t%s\t%s: %s %s\t%s: %s %s\n" % (
                    r["outcome"], r["article_id"], r["word"],
                    "pass 1", r["pass1_verdict"], r["pass1_correction"],
                    "pass 2", r["pass2_verdict"] or "-", r["pass2_correction"]))
            out.write("%d packets to read\n" % len(rows))
        elif a.cmd == "merge":
            out.write(merge(st, a.output, a.format, a.all) + "\n")
    except Refused as e:
        out.write(str(e) + "\n")
        out.flush()
        return 1
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
