<!-- The About page (/about/) and the published repository's README.md, one text (site
decisions 63, Robin 2026-10-22). Rendered by ordpar/sitegen/about.py: read its docstring before
editing. In short: "# " the title, "## " a heading, **bold**, *italic*, a link, [text] directly followed by (url); {name} a number the
build fills; [if name]...[/if] kept only while that number is not zero; a block of "- " lines
a bulleted list; [readme]...[/readme] in the README only. Approved text: docs/sessions/2026-09-19-ordpar-site-review/walk-through/
about-page-final-2026-10-22.md; the aim paragraph and the section order, site-review decisions 121 (2026-10-24); the deck's
paragraph under "Thanks", the link to /coming/ and the "Contact" section (its id #contact, which
the deck's AnkiWeb page links), decisions 131 (2026-10-25/26); the last paragraph under "Thanks",
its link to /thanks/, decisions 166 (2026-11-05, a draft for Robin), in [if reports] since: shown only
while the reports' switch is on (sitegen/chrome.py REPORT_RECEIVER), since until then no reader can
tell us about a mistake. The recordings' licence sentence under "Hear the words" and the data
sentence under "Contact", decisions 172 (Robin, 2026-11-07). The deck's paragraph under "Thanks" names both decks
and the blended order, decisions 178 (Robin, 2026-11-08). Every "## " heading gets an id from its words. -->

# About Ordpar

Ordpar is a Norwegian–English dictionary on the web. It is built on Bokmålsordboka, the Bokmål dictionary from Språkrådet and the University of Bergen, and adds an English translation to each article: the definitions, the examples and the set phrases. Every article has a page; those we have not translated yet are shown in Norwegian.

Ordpar's aim is to help people learn Norwegian. Translating Bokmålsordboka into English, and later into other languages, is how we work towards that: a learner can read a Norwegian word's whole dictionary entry in a language they already know. Ordpar is free to use, with no advertisements and no account, and its English is free to reuse (see The English, below).

[readme]
## This repository

This is the built site that GitHub Pages serves at ordpar.no: generated pages, styles, scripts and search files. It is replaced in full each time the site is updated and keeps no history, so changes made here would be lost. The code that builds the site will be published in a repository of its own, with its own licence; until then, no licence is given for the scripts and styles here.
[/readme]

## How far it has come

Bokmålsordboka has about {articles} articles, and {translated} of them have been translated so far[if no_summary]: {complete} complete, with the short summary at the top, and the rest with every definition and example in English, their summary still to come[/if]. The translated articles are mostly the common, longer ones, so they hold a larger share of the dictionary's text: about {words_share} of it, counted in running words across all its definitions, examples and etymologies. We intend to translate the whole of Bokmålsordboka into English, and then to add other languages. What we have decided to build next: [Coming to Ordpar](https://ordpar.no/coming/).

## Where the dictionary comes from

The Norwegian text is Bokmålsordboka, © Språkrådet (the Language Council of Norway) and the University of Bergen, published at [ordbokene.no](https://ordbokene.no/) under the [Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The inflection tables are built from Norsk ordbank, under the same licence. Thank you to Språkrådet and the University of Bergen for making the dictionary freely available: Ordpar could not exist without it.

## The English

The English is written with AI (Claude, by Anthropic) under Robin Fauskanger's direction and review. Whatever rights exist in it are given on the same terms as the Norwegian, CC BY 4.0: credit the English to Ordpar (ordpar.no), and the Norwegian to Bokmålsordboka.

## Our changes to the Norwegian

We show Bokmålsordboka's articles in a layout close to ordbokene.no's, with these changes of ours[if snapshot_date], as of its data of {snapshot_date}[/if]:

[if corr_xref]- Cross-references that pointed to the wrong sense, homograph or article, corrected: {corr_xref} in {corr_xref_articles}
[/if][if corr_spelling]- Typos, punctuation and formatting corrected: {corr_spelling} in {corr_spelling_articles}
[/if][if corr_headorder]- The more common spelling of the headword put first, where Bokmålsordboka lists it second: {corr_headorder}
[/if][if corr_other]- Other corrections ({corr_other_kinds}): {corr_other} in {corr_other_articles}
[/if]- Example sentences of our own, added where a sense had no example: {added_sentences} in {added_articles} articles. Each is marked with a small raised "+", so it is never taken for Bokmålsordboka's.

Each corrected article says so at its foot, with a link to Bokmålsordboka's article on ordbokene.no. Any mistakes our changes introduce are ours. Every page credits Bokmålsordboka in its footer, with a link to ordbokene.no.

## Hear the words

About 200 hours of Norwegian audio: every headword, every example sentence and every definition line, and the inflection tables of the core vocabulary, of every irregular word and of every adjective, read by Ida, [Amazon Polly's](https://aws.amazon.com/polly/) synthetic Norwegian voice. You may reuse the recordings on the same terms as the text, CC BY 4.0: credit the recordings to Ordpar (ordpar.no), and the words they read as you would the text itself.

## Search

Word frequencies for search suggestions: N-grams from the National Library of Norway 2026, [Språkbanken](https://www.nb.no/sprakbanken/), National Library of Norway ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)). The site ships only a coarse frequency band per headword, never the list.

## Thanks

The articles we translated first were chosen from [The original Norwegian Kelly list](https://www.hf.uio.no/iln/english/about/organisation/text-laboratory/services/kelly.html), a list of the core words for language learners from the Text Laboratory at the University of Oslo (CC BY-SA 4.0). Thank you to the Text Laboratory for the list, and for agreeing that a dictionary built on its selection is not an adaptation of it.

The same list, blended with how often each word is used in film and TV subtitles ([Hermit Dave's FrequencyWords](https://github.com/hermitdave/FrequencyWords), CC BY-SA 4.0), sets the order of Ordpar's Anki decks, [*Ordpar: Norwegian Core Vocabulary*](https://ankiweb.net/shared/info/1906319472) and *6000 Most Frequent Norwegian Words* ([Part 1](https://ankiweb.net/shared/info/1989661164), [Part 2](https://ankiweb.net/shared/info/879167685)), whose cards show each word's Ordpar article. Because their word order comes from these two lists, the decks are licensed CC BY-SA 4.0, as the lists are; the dictionary itself stays under CC BY 4.0.

[if reports]Thank you to the readers who tell us about mistakes in the articles or send us ideas: [Thanks to our readers](https://ordpar.no/thanks/) lists the fixes their reports have led to and the ideas we have taken up or plan to.

[/if][if privacy]## Privacy

What the site sends, what it keeps and for how long, and what stays on your device: [Privacy](https://ordpar.no/privacy/).

[/if]## Not affiliated

Ordpar is an independent project. It is not made, endorsed or checked by Språkrådet, the University of Bergen or ordbokene.no.

## No warranty

The dictionary is offered as it is, without warranties of any kind; see the licence's [disclaimer of warranties (section 5)](https://creativecommons.org/licenses/by/4.0/legalcode.en#s5).

## Contact

Write to us at [post@ordpar.no](mailto:post@ordpar.no) about a mistake in an article, the Anki deck, or anything else about Ordpar. If you would like the dictionary's data as files, the articles or the recordings, write to us there too.
