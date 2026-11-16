<!-- The Anki deck's change list (decisions 177: a page for the Anki deck, the natural
extension of the change lists, and a change doc in the same style as theirs), beside the
site's (changes.md) and the dictionary's (library-changes.md); its public page is the site's to build
(asked of the site session 2026-11-07). One dated entry per release of the deck, newest first, in plain words
for readers, written by the deck session when the release is shared on AnkiWeb, from the build's own counts
(build.json), never typed from memory: what changed on the cards and in the word list, which deck it reached,
nothing internal, no decision numbers. Planned work is not listed here; the AnkiWeb pages' "Under development"
says what is coming. The entries up to 2026-10-25 are the AnkiWeb page's own "Updates", rewritten in this list's form with
nothing added.
Drafted 2026-11-07 by the deck-release session. -->

# Changes to the Ordpar Anki decks

What has changed in Ordpar's Anki decks, newest first. AnkiWeb doesn't tell you when a deck you downloaded is updated, so this list does. Each entry says which deck it reached:

- **Ordpar: Norwegian Core Vocabulary**, the words in one deck, sorted into levels ([on AnkiWeb](https://ankiweb.net/shared/info/1906319472)).
- **6000 Most Frequent Norwegian Words**, in two parts on AnkiWeb ([Part 1](https://ankiweb.net/shared/info/1989661164), [Part 2](https://ankiweb.net/shared/info/879167685)), with more of the audio in the download.

How to update is on each deck's AnkiWeb page. Changes to the dictionary itself have their own list: [Changes to the dictionary](https://ordpar.no/dictionary-changes/).

## 2026-11-11

**Both decks:**

- **A second hint.** When Hint has shown an example, a second button under it, "Show English", shows the
  sentence's translation with the word's English equivalent left blank, so you get the meaning of the sentence
  without the answer. On a reverse card the button is "Show Norwegian", and it shows the Norwegian sentence with
  the word itself left blank, for you to fill in. The idea came from a reader, Moomoo.
- **The front says when a spelling has more than one card.** *nå* is an adverb, a verb and an interjection, each
  with a card of its own; the verb's front now says "Also in this deck as: adverb, interjection", so you know
  which of them the card asks for. It is on 362 cards, for 178 spellings. A reader, Moomoo, told us these
  cards were hard to tell apart.
- **Three pairs of nouns share a card.** *følge*, *drikke* and *leie* each had two noun cards, one for each
  gender. Each pair is now one card showing both nouns, so the deck has 6,074 words, and three cards have left
  it. The cards that stay keep your progress. Each deck's AnkiWeb page says how to delete the three that left.
- **The hint's examples.** An example whose translation doesn't use one of the word's main English equivalents
  is now shown only for a word that has no other example, since it can't have a second hint.
- **Short formula lines in both languages.** Lines such as "used as an adverb:" now show in Norwegian and
  English, as on ordpar.no; a setting changes it back.
- **The read-me** says which version you have and links to this list, and "Suggestions on how to practise" has a
  new line: a word that keeps frustrating you can be suspended or deleted.
- **Corrections to the Norwegian** in 61 of the deck's articles, the same ones as in the dictionary.
- **The frequency index** of 1,080 words is one lower, since one of the cards that left had a rank of its own.

## 2026-11-07

**Ordpar: Norwegian Core Vocabulary**, new:

- **The two-part deck in one.** The same 6,077 words, sorted into a deck for each level: A1, A2, B1, B2, and C
  (C1 and C2 together, since C2 has only 19 words). The forward cards and the reverse cards have a branch each,
  Forward and Reverse, so you can study either direction level by level, or the whole of Forward in frequency
  order. It has everything listed below for the two parts. Of the audio, only each word's own recording comes in
  the download (about 50 MB in all); the rest plays online. If you study the two parts, you can switch to this
  deck and keep your progress: its AnkiWeb page says how.

**6000 Most Frequent Norwegian Words**, both parts:

- **Audio for every Norwegian line on the back:** the word, its definitions, its examples and its inflection
  tables, read by Ida, Amazon Polly's synthetic Norwegian voice. The word plays by itself when the back shows (a
  setting turns that off, and another slows the audio). Each word, its tables and an example for each meaning
  come with the download, so they play offline; Part 2 also carries the other examples, and the definitions of
  its first 1,133 words. The rest plays when you press it, with an internet connection; without one, the card
  says so.
- **A CEFR level on every word,** as a tag: 634 words at A1, 1,190 at A2, 2,057 at B1, 1,768 at B2, 409 at C1 and
  19 at C2. No graded word list exists for Norwegian in public (the Kelly project graded its Norwegian words, but
  never published the grades), so the levels were assigned by AI (Claude, by Anthropic). For every card, a
  judge read the whole article and placed each word at the level where a learner first needs it, judging it by
  its everyday meanings against the CEFR's descriptions of the levels; a card with several words takes the
  lowest level among them. Before the levels were used, they were checked against SVALex, a Swedish word list
  graded from CEFR-levelled coursebooks: 100 words the judges never saw, 20 from each level, each paired with
  its Norwegian equivalent. 87 of the 100 came within one level of the coursebooks' level. Take the levels as a
  guide, not an official grading.
- **The parts divided by level** for new downloads: Part 1 has A1–B1 (3,881 words), Part 2 B2–C2 (2,196). Before,
  they were divided by rank. If you update an older download, your cards stay in the part they were in.
- **Theme tags:** 3,863 words have a theme (`theme::food`, `theme::calendar::days` …) or an area of daily life
  (`life::shop`, `life::doctor` …), so you can study the words of one topic together. Many of the themes are the
  Kelly project's: the 24 everyday domains it drew from the CEFR's own themes (it published the domains, not
  which words went in each), combined with a few of our own. A second AI judge sorted each card into this list,
  which was settled after a trial run on a sample. Every card
  also has its word class as a tag (`word-class::noun` …), and set phrases are tagged `word-class::set-phrase`.
  The numbers, the days, the months and the seasons are in their natural order within
  their place in the deck.
- **A Hint button on the front:** a Norwegian example from the word's article, with the word marked, a different
  one each time, so you learn the word rather than the sentence. 5,642 forward cards and 5,544 reverse cards
  have one; the rest have none yet.
- **The words of the same spelling reordered, and fewer rare ones on the back.** 383 cards have two or more words
  of the same spelling on the back, such as *være* "to be" and *være* "to scent". For each of these cards, AI
  judges decided two things, without seeing our order: which word comes first, the most common one; and which
  words are not among the core vocabulary the deck is for (*være* "to scent" isn't), so they leave the back. I
  ruled on 78 of these cards myself, and left the other 305 to the judges. In all, 334 rarer words on 288 cards
  moved from the back to the foot of the card, "Also on ordpar.no", where they now come first; a press still
  opens them.
- **"Suggest a correction"** at the end of every card, one for each word on a card with several: it opens the
  article on ordpar.no with a short form. The fixes are listed on [ordpar.no/thanks](https://ordpar.no/thanks/).
- **The word list revised:** 323 words added and 281 retired. Every word added and every word
  retired was my own decision, word by word, made with AI help. Judges scored about 2,100 candidate words,
  the deck's weakest and the strongest words outside it, on how often an ordinary adult meets each one in
  everyday Norwegian, on a scale anchored by words I had graded myself. Both lists were ranked on that one
  scale, so I could see where a word outside the deck was commoner than one inside it.
- **Derived words and compounds moved to their base word's card.** About 200 of the retired words were derived
  forms or compounds of words that stay in the deck, such as *skaper* from *skape* and *samsvar* from
  *samsvare*: a learner who knows the base word can read them on sight. They aren't gone. Each is named in the
  foot of the card holding its base word, "Also on ordpar.no", and a press opens it. In all, the foot of a card
  now names 277 related words that aren't in the deck.
- **The order revised:** it blends the Kelly list's ranks with how often each word is used in film and TV
  subtitles, checked against the National Library of Norway's book counts.

## 2026-10-25

**6000 Most Frequent Norwegian Words**, both parts:

- **Every card rebuilt on Ordpar.** The back of each card is now the word's article from Ordpar, with every example
  in Norwegian and English, and a small article for each linked word.
- **A reverse card for every word,** English to Norwegian, after all the forward cards.
- **The AI-written explanations and sentences are gone,** and all the audio with them, and so are the fields that
  held them.
- **The word list corrected:** 205 words added, 109 retired, and the frequency ranks renumbered.

## 2026-07-25

**6000 Most Frequent Norwegian Words:**

- **Dictionary entries for the first 2,500 words.**

## 2026-06-20

**6000 Most Frequent Norwegian Words:**

- **Every dictionary entry updated.** The example sentences have a button that shows their English, so you can use
  them to practise.

## 2024-01-11

**6000 Most Frequent Norwegian Words:**

- **Dictionary entries for the first 1,500 words.**
