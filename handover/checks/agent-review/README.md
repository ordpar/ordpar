# Sorting check 7's candidates with AI agents

This folder shows how we had language-model agents read the candidates that check 7
(`word_forms.py`, in the folder above) finds in Bokmålsordboka, and how you can set up the
same kind of review for your own dictionary. It holds:

- `README.md`: this text;
- `check7-reader.md`: the reader agent's definition, its prompt, ready to copy;
- `agent_review.py`: a small script that runs the loop (Python 3, standard library only;
  `python agent_review.py --help`);
- `test_agent_review.py`: its tests (`python test_agent_review.py`).

**Please note.** The script here was written for this repository, after the fact. The
findings we sent to ordbokene's editors on 10 November 2026 came from our original tools,
which were tied to our own files and folders. The script follows their design. It **has not
been run with real agents**. Its tests run the whole loop with a stand-in: a function that
returns fixed verdicts.

## What check 7 finds, and why its candidates need sorting

Check 7 reads every word in the dictionary's definitions and examples. It reports the words
it cannot find among the dictionary's own word forms or in Norsk ordbank's Bokmål full-form
list. Most of these are correct: compounds and derivations without an article of their own,
foreign words, names, quotations, rare or older forms. Some are slips: a misspelling, a
Nynorsk form in Bokmål text, a missing space, a wrong inflection.

Over every article the API serves (94,241), the check found 5,814 candidates. 4,438 of them
are marked `compound`: the word splits into known forms, so it is probably a correct
compound. Telling a slip from a correct word needs a reader who knows Bokmål and reads the
whole sense. That is too many words for a person to read in a reasonable time, so we had
agents read them, and people read what the agents could not settle.

## How the loop is set up

1. **Packets.** The check's output has one line per place a word stands. The script joins
   the lines of one word in one article into a **packet**: the word, the article, every
   place it stands, and the text around it. With the articles file, a packet carries the
   whole sense the word stands in (every definition and example), the article's other
   senses in one line each, and the known Bokmål forms one edit away from the word, with
   how often the dictionary uses each.
2. **Batches.** The packets are shuffled and cut into batches of 25. A batch is the unit an
   agent takes.
3. **Readers.** Each reader is an agent of the same type, `check7-reader`. It loops: it
   takes the next open batch, judges each packet, writes one verdict per packet, and
   submits the file. The script checks the file. If anything is wrong (a packet missing, a
   field out of place, a slip without a correction), it refuses the whole file and lists
   every problem, and the reader fixes it. Nothing malformed is ever recorded. Two readers
   can never take the same batch.
4. **A second pass.** Every packet the first pass calls a slip goes to a second, independent
   reader. It sees the same packet and nothing of the first verdict. A fresh agent gives the
   independence.
5. **The merge.** Both passes go into one table, with an outcome per packet. People read
   the packets where the two passes disagree, and those the first pass was unsure of.

Readers can run side by side, so the work goes in waves: a few readers first, a look at
their verdicts and their cost, then more. The second pass can run after each wave.

## The verdicts, and what each means for an editor

A reader gives each packet one verdict, a confidence (high, reasonable or low) and a
one-line reason:

- **slip**: an error in the dictionary's text. The reader names the kind (misspelling,
  Nynorsk form, missing space, extra space, inflection, other) and gives the words as they
  should stand. A correction follows the dictionary's own usage: the main headword's form,
  and the form the dictionary itself writes most often.
- **valid**: a correct word; the reason says what it is ("compound: mark + sti",
  "English, in a quoted title").
- **unsure**: the reader cannot tell. It may give a candidate kind and correction. One kind
  is for unsure only: **joint_variant**, a compound written with a joint (*-s-*, *-e-*)
  that the dictionary's own article for that compound does not have, or the other way round
  (*låsemekanismen* where the article is *låsmekanisme*). That is the editors' choice, not
  a slip.

A reader can also note **other slips** it sees in the same text (a doubled word, a wrong
preposition) in a field called `also`.

After the merge, each packet has one **outcome**:

| Outcome | Meaning | For the editor |
|---|---|---|
| `slip` | both passes call it a slip | a correction to consider |
| `disputed` | the passes disagree | a person reads it |
| `unsure` | the first pass could not tell | a person reads it |
| `slip (one pass)` | the second pass has not read it yet | wait, or read it |
| `valid` | a correct word | nothing to do |

**The loop does not correct the dictionary.** It sorts candidates. An editor decides every
change. The `also` notes were seen by one reader only and are not checked by the script.

## What the agents were

The readers were Claude models from Anthropic (Claude Opus), run as **subagents in Claude
Code**, Anthropic's coding assistant. A subagent is a separate assistant with its own
instructions, which the main session starts and which reports back when it is done. The
instructions live in a file, `check7-reader.md`, in the project's `.claude/agents/` folder.
Every reader starts from the same instructions, so they judge alike, and none of them sees
the others' work. The readers had three tools: running a command, reading a file and writing
a file. They worked offline.

The main session (also Claude, directed by a person) queued the passes, started the
readers, and read the disagreements. A person ruled on what went to the editors.

## How to run it, step by step, with Claude Code

1. Run check 7 over the dictionary, with Norsk ordbank's list (see the README in the
   folder above):
   `python word_forms.py ARTICLES --bokmal-forms fullformsliste.txt -o word_forms.tsv`
2. Make the packets. With `--articles` the packets carry the whole sense and the near
   forms, and the readers get the `forms` lookup; this needs `common.py` and `word_forms.py`
   in the folder above, as in this repository:
   `python agent_review.py packets word_forms.tsv --articles ARTICLES --bokmal-forms fullformsliste.txt`
   Everything goes into a state folder, `review-state` unless you name another with
   `--state DIR` (before the subcommand).
3. Queue the first pass: `python agent_review.py queue --pass 1`. To read only a sample of
   the packets marked `compound`, add `--sample N`.
4. Copy `check7-reader.md` into your project's `.claude/agents/` folder, and start a new
   Claude Code session, so that it finds the new agent type. Change `model` and `effort` in
   its first lines if you want. `omitClaudeMd: true` keeps your project's own `CLAUDE.md`
   out of the readers' context, so they start from the reader's instructions alone.
5. Ask the session to start some readers of type `check7-reader`, each with a one-line
   prompt. For example:
   `Run your loop with: python C:/work/agent_review.py --state C:/work/review-state; tag r01; pass 1; up to 2 batches. Articles: C:/work/articles.jsonl. Norsk ordbank: C:/work/fullformsliste.txt.`
   Give every reader its own tag. Start with a few, look at their verdicts, then start more.
6. Follow the work with `python agent_review.py status`. If a reader fails, free its batch
   with `python agent_review.py release p1-007`.
7. When a wave is done, queue the second pass: `python agent_review.py queue --pass 2`
   (`--dry-run` first shows which packets it takes; `--include-unsure` adds the unsure
   ones). Start readers with `pass 2` in their prompt. Run it again after each later wave:
   it adds only the new packets.
8. List what a person must read: `python agent_review.py disputed`.
9. Write the table for the editors: `python agent_review.py merge -o review.csv`, or
   `--format md` for Markdown; `--all` adds the packets nobody read.

## What it cost us

These figures are from our own run in October and November 2026 and are rough.

- **What was read.** Of 5,777 packets, the first pass read 1,659: all 1,359 without a
  `compound` mark, and a random 300 of the marked ones. In those 300, 3 were slips (1 %).
  We read ten more of the marked words and judged that reading the other 4,118 was not
  worth the cost.
- **Result.** Both passes agreed on 555 slips. They disagreed on 11, which a person read.
  Some of the slips were known to us already.
- **Readers.** The first wave was small: 3 readers with 2 batches each (150 packets). We
  then changed the tool and the instructions, and ran the rest in two larger waves (the
  last with 16 readers of 2 batches each) on one day.
- **Tokens.** About 100,000 to 120,000 tokens per batch of 25 packets, on Claude Opus at
  medium effort, measured in two waves. Most of it is the reader re-reading its own
  growing context on every step, not the packets themselves. The second pass cost about the
  same per batch.

## What changed from our original tools

- **The reader's prompt** (`check7-reader.md`) is the one our readers ran with, with these
  changes: our folder paths and the name of our session are gone; the script is called
  `agent_review.py`, and the spawn prompt gives its command and the data files; the
  `nearest` field is simpler (see below); a packet built without the articles (`texts`)
  is described; the line on scratch files is new (it was in our pass-2 prompts). The rules
  for judging, the measured figures on the dictionary's own usage, and the examples are as
  they were.
- **The script** replaces four tools of ours. It keeps their design: one packet per word
  per article; batches claimed with a lock file, so no two readers share one; a verdict
  file refused whole, with every problem listed; a slip's correction checked against the
  known Bokmål forms, with an override that flags the row; a blind second pass on the
  slips, queued wave by wave.
- **Left out:** the comparison with our own translation logs, which we used to measure how
  many known slips the readers found; the sampling of the marked packets by group; the
  forms index in a database (the script keeps a JSON file); the near forms one edit away
  only (ours went to two edits when one found nothing); and in `nearest` each article's
  whole inflection table (the script gives each form's count and the articles that hold
  it, and `forms` looks up any other form). Also left out is our import into the list we
  sent: there, a joint difference counted as a slip if it stood in the compound's own
  article, and went to a list of joint variants for the editors otherwise.

## Licence and contact

The code and text in this folder are ours, under MIT-0, like the rest of our code. The
dictionary's data is Bokmålsordboka's, under CC BY 4.0. Questions: post@ordpar.no.
