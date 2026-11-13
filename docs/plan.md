# The plan: what Ordpar is for and what it must do

Ordpar (<https://ordpar.no>) turns *Bokmålsordboka*, the Bokmål dictionary that the University of
Bergen and the Language Council of Norway publish at [ordbokene.no](https://ordbokene.no) under
CC BY 4.0, into a public Norwegian–English dictionary. This document is the site's plan: what the
site is for, what it must do, what it adds to ordbokene.no, what it costs, and the order of the
work. It says *what* and *why*; how each part is built is in the technical docs under
`ordpar/docs/`, and every ruling cited here by number is an entry in [the decision log](decisions.md).
Where Ordpar knowingly differs from ordbokene.no is listed in [the divergences record](divergences.md).
Rough ideas that are not yet plans are in [the ideas list](ideas.md).

Dates are given where a figure or a check belongs to a day. The site has been public since
25 October 2026 and is still being built, so parts of this plan describe work not yet done.

## 1. The mission

The site is meant to help people. Above all it is for learners who need Norwegian to live in
Norway (for work, for citizenship, for a life in the country) and who today have almost no
dictionary in a language they read. Hobbyists are welcome and are served by the same site, but
they are not the mission.

**English comes first** because it is the language most learners can read besides their own.
**The next languages follow the funding** ([14](decisions.md#d14)). The site is designed so that each further
target language costs only its translations (§ 4).

**Why the whole dictionary.** A dictionary of the 6,000 commonest words would add little: good
English dictionaries already cover them. A complete translation of Bokmålsordboka (94,136
articles in the snapshot of 2 September 2026, with senses, examples, etymology and set phrases)
would be the most comprehensive free Norwegian–English dictionary there is. Robin's estimate of
the field: the largest free online dictionaries offer perhaps 30,000 headwords, the paid ones
closer to 100,000. That is why the translation goes on past the commonest words.

## 2. The baseline: ordbokene.no, in English

**Every article's default face is ordbokene's**: its structure, senses, examples and inflection
tables, with English added wherever we have written it. Everything ordbokene.no does is a feature
we build unless we decide not to, and each such decision is recorded, with its reason, in the
divergences record.

**Why the definitions stay.** In September 2026 we compared five other bilingual dictionaries'
articles (the comparison is in [the ideas list](ideas.md#seen-elsewhere)). The translator's
dictionaries (Collins, PONS, and the licensed data behind Cambridge's Norwegian–English) define
no sense: the translation *is* the sense, and an English note at most tells senses apart. That
suits fast lookup of equivalents, but it is not an argument against definitions. Learner's
dictionaries are all definitions; the bilingual learner's dictionaries that grew from them carry
both a definition and a translation on every sense; and Lexin, the one site in the comparison
built for learners of Norwegian, keeps its definition in both languages. Ordpar is that kind of
dictionary, and its definitions cost nothing to write: they are ordbokene's, translated.
A translation alone fails exactly where a learner most needs help: words with several senses
(*bru*: four senses, one English word, *bridge*), words with no English equivalent, function
words, and writing (a translation says what a word can mean, never where the meaning stops). For
*koselig* the translations are *nice, pleasant*, which miss the word; the definition, "that
brings a sense of cosiness with it", is the word, and the examples then need three English words
for it (*a cosy home*, *a lovely party*, *a nice bloke*). What the comparison did show is that
most lookups want an English word first: hence the summary gloss in the article's head
([42](decisions.md#d42)).

**We imitate ordbokene.no; we never copy it.** Ordbokene's dictionary content is published under
CC BY 4.0; the code and design of its website carry no licence, so all rights in them are
reserved (checked 18 October 2026). Its features, layout and behaviour are ideas we may re-implement; its scripts,
stylesheets, components and markup are not ours to use. Our code is written only from what
ordbokene.no shows and does, never from its source ([12](decisions.md#d12)). If one of its
components would ever save real work, we would ask the University of Bergen for a licence rather
than assume one. *Norsk Ordbok* is not a possible source: its own citation page says its content
is protected by copyright and names no open licence (checked 19 September 2026).

**A recognisable family resemblance, never confusion** ([12](decisions.md#d12)). The articles
may look like what they descend from (ordbokene's maroon, its article anatomy), but a reader must
never be unsure which site they are on. So Ordpar has its own name, logo, header and front page;
a one-line credit on every article links to an About page with the full attribution and the
statement that Ordpar is not affiliated with the University of Bergen or the Language Council
([32](decisions.md#d32)); and it never uses ordbokene's name as its own, its marks or its files.
The resemblance is the article, not the site: our articles are translations of theirs, so the
article page keeps their anatomy and order, and the rest of the site owes them nothing in its
look. **Ordbokene's own English interface is the baseline for the article's grammatical terms**
(word classes, tenses and moods, genders, table headers): the same term unless our translation
conventions fix another, with each difference recorded ([22](decisions.md#d22)).

**Every article is on the site, translated or not** ([2](decisions.md#d2)). An article we have
not yet translated is shown whole in Norwegian, marked *Norwegian only*. You will always find the
word you look for, sometimes only in Norwegian. What is never shown is a half-translated article:
an article becomes *translated* only when its English is complete, and each site update publishes
only complete ones. Bokmålsordboka's text is CC BY 4.0, so showing it is not a licence question.

### 2.1 The feature inventory (19 September 2026)

This is the site's specification sheet. It was made on 19 September 2026 and checked against
the live ordbokene.no page by page, recording what each page shows and does. Where ordbokene's own help
pages describe a behaviour the live site did not show, the live site was followed.

**Verdicts.** *keep*: re-implemented as ordbokene does it. *adapt*: the feature stays, its shape
changes for a bilingual dictionary. *skip*: not built, for the reason given. *add*: ours, with no
ordbokene counterpart, listed so the sheet is complete. A number links to the ruling behind the
row. "Live" describes ordbokene.no on 19 September 2026.

**Pages and addresses**

| Feature | Live | Verdict | Why |
|---|---|---|---|
| Front page | Search box; a featured article and five recently updated headwords per dictionary; a photo background | adapt | Our own front door ([12](decisions.md#d12)): search first; a featured article and a "newly translated" list are honest equivalents; no photo |
| Search results page | One column per dictionary searched, each with its name, hit count and the full articles | adapt | One column: we serve one dictionary ([17](decisions.md#d17); § 3.1) |
| Single article page | One article on its own page, with a link home or back to the results | keep | The permanent page for an article |
| Article address = numeric id + optional headword | `/bm/24627` and `/bm/24627/hus` are the same page | keep | Our articles keep ordbokene's ids, so the ids even coincide; the headword makes links readable |
| Sense anchors `#defN` | A cross-reference to a sense scrolls to it and highlights it | keep | Our references already point to senses |
| Interface language, dictionary and query in the path | `/eng/bm,nn/hus` | adapt ([21a](decisions.md#d21)) | The address names the dictionary pair, then the article id or the query; the interface language is never in it (see *The addresses* below) |
| Interface language from storage or the browser | A stored choice wins; otherwise the browser's language | keep ([21a](decisions.md#d21)) | The stored choice decides; with nothing stored, the browser's language if we have it, English otherwise. A shared link opens in the recipient's own language |
| Alternate-language links and a canonical address per page | Declared for every interface language | adapt ([21a](decisions.md#d21)) | One canonical address per article and no alternates, since the article is the same in every interface language; alternates only on the help and about pages, which are written per language |
| Help, About and Contact pages | Pages of text, with a way back to the last search | adapt | Our own texts: licence and credit, why a word may be missing, installing the app, accessibility; Contact becomes the question box and `post@ordpar.no` |
| Missing-article page | "Could not fetch article N … 404", a link home | keep | Routine |

**Search**

| Feature | Live | Verdict | Why |
|---|---|---|---|
| Dictionary choice | A dropdown on the search bar: both dictionaries, Bokmål, Nynorsk, advanced search; switching keeps the word | adapt | The same control over our two directions, Bokmål–English (the default) and English–Bokmål, plus advanced search; no "both" ([17](decisions.md#d17); § 3.1) |
| Clear and submit buttons; 200-character limit | A standard search box | keep | Routine |
| Suggestions while typing | Up to 20 headwords that start with what is typed, shortest first, then alphabetical, each tagged with its dictionary | adapt | Ours mark, by colour, whether the article is translated yet: a reader needs that before clicking ([137](decisions.md#d137)) |
| Keyboard use of the suggestions (arrows, Home/End, Esc, Tab) | Standard behaviour | keep | Accessibility baseline |
| Query size limits (over 20 words, or a 40-character word, not sent) | Stops junk queries | keep | Routine |
| "X is an inflected form of: …" | Every headword the typed form belongs to, as links, beside the similar words | keep | Mechanical from our inflection tables; without it half of real lookups miss |
| Going straight to the headword when the form is unambiguous | Not seen live, though ordbokene's help page describes it | skip ([18](decisions.md#d18)) | We do what the live site does: the form's own search page with the "inflected form of" panel; each headword a link |
| Similar words | Five near spellings per dictionary, after a miss and under a hit | keep | Catches misspellings, the commonest failure of our readers |
| A suggested Bokmål ↔ Nynorsk translation (machine translation, labelled) | When a word is in one dictionary only | skip | Nothing like it here: our English is the translation, and we never show machine output as dictionary content |
| Full-text hint on a miss | When the typed string occurs inside articles, a link to full-text search; not seen on the live site on 19 September 2026 | keep | Cheap once full-text search exists; for us it also finds English words |
| No-hits text and "why is a word missing" page | Explains that compounds are unlimited | adapt | Ours adds that the article may exist in Norwegian only; misses are counted (§ 5) |
| Random word | A button on every search page | keep ([115](decisions.md#d115)) | Opens a headword search, as on ordbokene.no; drawn from every headword |
| A pattern (`hus*`) or more than two alternatives sends the search to advanced search | | keep | Routine |
| Two alternatives (`hus\|hytte`) in a simple search | Both words' articles on one page | keep | Routine |
| Advanced search: dictionary, scope (headwords / with inflected forms / full text), word class, hit count, 10–100 per page, paging; every search an address | | adapt | Kept whole; the dictionary choice becomes the direction; full text searches the English too; a "translated only" filter added |
| Wildcards `* % _ ?` and `\|`, explained on a help page | | keep | Our own help text |
| Matches highlighted in full-text results | | keep | Routine |
| List view: one compact line per article, opening in place | A setting, and a box on advanced search | keep | Each line's snippet is the summary gloss where we have one, made by the build, not in the browser |
| No paging in simple search | | keep | A simple search rarely has more than a few homographs |

**The article page** keeps ordbokene's anatomy and order ([12](decisions.md#d12)).

| Feature | Live | Verdict | Why |
|---|---|---|---|
| The dictionary's name above each article | "Bokmålsordboka" | adapt | Becomes the credit line ([12](decisions.md#d12)) and the translation status ([2](decisions.md#d2)) |
| Headword and its spelling variants; homograph number as a Roman numeral, read as a digit by screen readers | | keep ([21b](decisions.md#d21)) | The library already stores the numeral |
| Word class and gender line; nouns grouped by gender | | keep | In English, by our word-class table |
| Inflection table: behind a button in the results, always shown on the article page, a setting to always open; none for words that do not inflect | | keep | The data carries the tables; the table's design is ours, with English labels; ours opens from an Inflection button, closed by default, with an always-show setting ([43](decisions.md#d43)) |
| The printed dictionaries' inflection codes (a setting) | | skip ([21c](decisions.md#d21)) | The data carries no codes |
| Split infinitive and *a*-infinitive lines | Nynorsk only | skip | Bokmål only |
| Pronunciation | Only where the data has it | keep | Shown when present; recorded audio attaches here (§ 3.6) |
| Etymology, with cross-references | | keep | Translated like the rest |
| Senses and sub-senses; examples, some with a short explanation; compound lists; usage labels; set phrases in alphabetical order, *æøå* last, each a small article | | keep | All of it is in the library's structure already |
| Cross-references with homograph and sense number | | keep | Ours add a two-step control: a pointer over it shows a short translation, a click opens the small article |
| Abbreviations written out from a list of concepts | | keep | Expanded when the Norwegian is derived |
| Typographic detail (super- and subscripts, fractions), language marks, "do not translate" marks | | keep | Language marks matter more for us: Norwegian and English on one page |
| Empty-article line | | keep | Routine |
| Copy link, Cite (citation text, retrieval date, a RIS file), Share | | adapt ([21e](decisions.md#d21)) | Copy and Share stay; Cite goes: our translations are not checked by expert academics, so the dictionary should not be cited as an authority; the About page says what to cite instead |
| Two dictionaries side by side | Bokmål left, Nynorsk right | skip ([17](decisions.md#d17)) | One dictionary; English–Bokmål is a separate search (§ 3.1) |
| Learner mode, question box, audio, card for Anki, *Norwegian only* note, credit line | | add | § 3; [2](decisions.md#d2), [12](decisions.md#d12) |

**Settings** (no accounts; live, each setting is one key in the browser's local storage, as the
privacy page says)

| Setting | Live default | Verdict | Why |
|---|---|---|---|
| List view in simple search | off | keep | See List view |
| No automatic selection of the search word after a search | off | keep | Routine |
| Always show the inflection tables | off | keep | Routine |
| Show the printed dictionaries' inflection codes | off | skip | See above |
| Context for the participle forms in the tables | off | keep ([21d](decisions.md#d21)) | The frames ordbokene's English interface shows ("å spise", "har spist", "spis!", "spist + noun", "den/det spiste + noun") |
| Turn off the keyboard shortcut to search | off | keep | One documented key (ordbokene's own pages name two) |
| Suggest Bokmål ↔ Nynorsk translations | on | skip | The feature is skipped |
| Default scope of advanced search | headwords | keep | Routine |
| Colour mode: system, light, dark | system | keep | Routine |
| Results per page | 10 | keep | Routine |
| Interface language | the browser's | adapt | Our list: English first, then Norwegian and each target language as it ships (§ 4) |
| Learner mode (English hidden until revealed) | | add | § 3.2 |
| Reset settings, delete stored data | | keep | Routine |

**Languages**

| Feature | Verdict | Why |
|---|---|---|
| The whole interface translated; the dictionary content never translated by the interface | adapt | Our interface languages are our target languages; the content is translated by us, which is the product, and nothing on the site is machine-translated on the fly |
| Article headings follow the dictionary's language when the interface is Norwegian | adapt ([37](decisions.md#d37)) | The article body is the same whatever the interface language. Which language each line shows first is a setting, with the defaults of [174](decisions.md#d174). Section labels stay the English ones ([22](decisions.md#d22)) |
| Bokmål/Nynorsk default alternating by day | skip | No counterpart |
| English browsers not redirected | adapt | See interface language |
| Help and About pages per language | keep | Written per language as each ships |

**Offline and app**

| Feature | Live | Verdict | Why |
|---|---|---|---|
| A native app | Its contact page says the app is no longer updated | skip | § 3.4: an installable web app |
| A help page on adding the site to the home screen | Instructions per browser; no web app manifest, no offline support | add | Ours installs as a real web app and works offline with the whole dictionary (§ 3.4); the help page becomes an install button and instructions |
| A connection-error message | "Tilkoblingsfeil", reload | keep | Plus the offline copy |

**Feedback and measurement**

| Feature | Live | Verdict | Why |
|---|---|---|---|
| "Did you find the word you were looking for?" yes/no | Shown with suggestions | adapt | § 5: free text per article; a yes or no teaches nothing |
| Failed searches logged | | keep | The failed-search list is our signal of what is missing ([15](decisions.md#d15)); we log the query, never the reader |
| Analytics with no cookie banner; a privacy page | | adapt ([19](decisions.md#d19)) | No cookies and no third party: a small receiver of our own counts visits and records the few events § 5 needs ([26](decisions.md#d26)); the privacy page says what is sent |
| A contact page with questions and an address, no form | | adapt | The question box (§ 3.5) and `post@ordpar.no` |

**Accessibility and the keyboard** (all *keep*): skip links; the search box as a real combobox;
polite live announcements of hit counts and confirmations; alerts for errors; focus back on the
search box after navigation (unless turned off, or on touch screens); open/closed state on every
toggle; a language mark on every article and column; reduced motion honoured; external links and
the current page marked. Ordbokene's published accessibility statement is a duty of the public
sector; ours is an accessibility page of our own (*adapt*). Checking the built HTML with a
validator is a practice worth keeping.

**Everything else**

| Feature | Verdict | Why |
|---|---|---|
| A sitemap index with sitemaps in parts, one address per article (the headword search pages left out: an article's id is the only address stable from one snapshot to the next, [24](decisions.md#d24)); a title, description and link-preview tags per page | keep | How a public dictionary is found; a translated article's description is its summary gloss |
| A dismissible banner across the site | keep | Cheap; announces a new language or an outage |
| The institutions' logos in the footer | adapt | The credit line and the not-affiliated line ([12](decisions.md#d12)); never their marks |
| `robots.txt` naming a security contact | keep | `post@ordpar.no` |
| Search answered by an online service | adapt | Ordpar is a static site: built pages, a search index in parts read by the browser, a host and a receiver, and a build that only reads its data ([24](decisions.md#d24)–[27](decisions.md#d27)) |

**Nynorsk** is skipped for the Norwegian–English dictionary, which is built on Bokmålsordboka
([20](decisions.md#d20)). It would be revisited only if a Nynorsk community asked for it or funded
it, and then as a library of its own, never as a field in the Bokmål one.

**The addresses** ([21a](decisions.md#d21)). An address starts with the dictionary pair, never
the source language alone: `/bm-en/24627/hus` is an article (its id, then its headword for
readability), `/bm-en/hus` a headword search, and a later Bokmål–Polish dictionary would use
`/bm-pl/…`. The interface language is not in the address: it is stored on the device (the stored
choice, else the browser's language if we have it, else English), and the language switcher
changes the stored value and redraws the page's frame in place. A shared link, a search engine
result and the bare domain all open in the reader's own language. Putting the interface language
in the address would mainly let search engines index one copy of each article per language, which
is of little use when the article is the same in every language, and on a host with no rewrite
rules it would cost a full copy of every page per language ([26](decisions.md#d26)). Crawlers and
readers without JavaScript see each pair's default frame (English for Bokmål–English). The
editorial pages (help, about, privacy) are written per language, carry their language in the
address, and are the only pages with alternate-language links.

## 3. What we add

### 3.1 English–Bokmål search

**One dictionary, one column** ([17](decisions.md#d17)). Ordbokene.no shows two columns because
it serves two dictionaries; Ordpar serves one. Searching from English is therefore a separate
search, not a second column, so a Norwegian search is never crowded with English hits.

**What it searches.** The summary glosses' equivalents ("prisoner · captive · inmate"), not every
English line: the definitions are sentences, and a search for *person* or *thing* would match
them everywhere. The definitions may become a second tier later.

**As built** ([148](decisions.md#d148); the build is described in
[`ordpar/docs/build-site.md`](../ordpar/docs/build-site.md) and the index in
[`ordpar/docs/lookup-index.md`](../ordpar/docs/lookup-index.md)):

- a switch labelled "Search English words" under the search box on every page that has one,
  remembered on the device;
- switched on, the box searches the equivalents (on 29 October 2026, 23,213 equivalents in 10,134
  articles), exact equivalents only, with American spellings mapped onto the glosses' British
  ones (*color* finds *colour*);
- results in this order: the first and second equivalents of a gloss as one tier, then the third
  onwards, each tier ordered by how common the Norwegian word is ([55](decisions.md#d55));
  the order of the equivalents is the order of salience we wrote them in ([42](decisions.md#d42));
- suggestions one row per English word, the English on the left where the reader types, the
  Norwegian headwords on the right;
- results always in the list view, the whole summary gloss under each headword with the searched
  equivalent in bold; a single match opens in full;
- similar English words after every search; a miss says honestly that the word is not among our
  English equivalents *yet*, with the numbers, never that Norwegian has no word for it;
- the address `/bm-en/#en=<word>`; History and Recent keep English searches as English; the
  offline copy carries the English index.

Not built: matching inside longer equivalents, beyond the similar words; the definitions as a
second tier. Coverage grows as summary glosses are written for more articles.

### 3.2 The learner layer: there, never the default

The default stays very close to ordbokene.no. What the Anki deck gives a learner is offered on
the site only as settings.

- **The summary gloss is not a learner extra** ([42](decisions.md#d42)): it is in the article's
  head under the word class, visible by default, in the order of salience we wrote it in. Each
  item is to carry a superscript link to its sense once the glosses are tagged with senses.
- **The learner notes and traps are off the site** ([38](decisions.md#d38)), to be revised later;
  if they return, they are off by default, since they are not dictionary content as such.
- **Learner mode**, the English hidden until revealed (the self-test of a flashcard), is a
  setting, not the default: some readers like it, others do not, and visible is safer. The
  example sentences' English behind a reveal is a setting too ([111](decisions.md#d111)).
- **Settings live in the browser**, with no account: they last until the reader clears the
  site's data or changes device, which is acceptable for preferences. Every display option is
  meant for both the site and the deck ([30](decisions.md#d30)); the settings are listed in the
  ideas list.

### 3.3 The personal layer: a card for Anki, and your own lookups

The aim is a button that puts the article's card into the reader's Anki: not a download to open
and import, just a button. A personal deck of one's own lookups would build on the same thing.

**No accounts before this layer and the forum** ([4](decisions.md#d4)), and then sign-in with
Google or Apple only, no passwords of our own. An account brings a server and database that must
stay up, sign-in support, abuse handling and personal data under the GDPR. It also raises the
security floor: the domain's DNS must be signed (DNSSEC) and carry a CAA record before the first
sign-in exists, since whoever can forge the domain's DNS answers can have a valid certificate
issued and serve a convincing fake sign-in page. Both have been in place since 8 September 2026
([13](decisions.md#d13)).

**There is no AnkiWeb account to link to.** AnkiWeb offers no third-party sign-in, so no version
of the button may hold a reader's AnkiWeb password, and none will be built that way. A "linked"
button can only mean an account on Ordpar whose queue the reader pulls into Anki: by a file, by
AnkiConnect on the desktop, or by the phone apps' own hooks. None of these routes has been tested
yet.

### 3.4 The app: the dictionary in your pocket

The picture: on the bus, you overhear a word, look it up, keep it, and review it on the same
phone. The form is a **web app that installs to the home screen** ([5](decisions.md#d5)): the
same site, opened as an app with its own icon, full screen, and working offline with the
dictionary stored on the device. A native app comes only if the web app proves itself. A
flashcard reviewer inside the app would be a separate, large product and is not proposed
([16](decisions.md#d16)).

**Built early** ([61](decisions.md#d61)): the first need was the whole dictionary offline on an
Android phone and a computer, opened from a home-screen icon. A plain local file cannot keep a
home-screen icon on Android, so it was built as this web app. It runs as the site itself at
ordpar.no. The offline copy is the built pages packed into gzip bundles of 500, downloaded on
request and served by a service worker (about 34 MB to download on 31 October 2026);
[`ordpar/docs/offline-app.md`](../ordpar/docs/offline-app.md) describes it. Search engines index
the translated articles, the home page, About and Help; the untranslated pages carry `noindex`
until each is translated ([128](decisions.md#d128)).

### 3.5 The community layer: a question box first, a forum when there are people

Discussion attached to a dictionary entry exists for large languages, but we know of none for
Norwegian (not checked; it must be checked before anything calls the feature original). The risk
is an empty forum, not the building of one. So the start is **"ask a question about this word"**
under every article, the same box serving as the feedback channel (§ 5). Answered questions show
under the article; an AI answers, labelled as such, when a question has waited a set number of
days. It grows into a forum when there are people; live chat needs a crowd first. The box is to
be tried on a fraction of the articles first (§ 6).

It hangs off the article, not off a general forum, because two readers on the same article are
working on the same word: the article is the shared context a general learners' forum has to
create. A button for reporting a mistake in an article came first ([166](decisions.md#d166)).
Translated answers from the Language Council's language advice would come before any AI answers
(see the ideas list).

### 3.6 Audio: every headword, example, definition and etymology

Norwegian speech for every Norwegian line, made once and served per article (never bundled with
the offline copy: it runs to hundreds of hours). Made in advance, never generated on the spot,
so it is a one-time cost for Norwegian that every target language reuses. Two checks come
before a voice is used: the provider's terms for storing and reusing its output, and a listening
test on isolated headwords (tones, stress). Audio taken from the Anki deck's sources does not
come to the site, to keep the licensing clean.

The goal is higher-quality voices bought with separate funding. Until then the site uses
synthetic speech ([134](decisions.md#d134)). A free voice run on our own computer (Piper) was
tried first and failed the listening test (28 October 2026). Since 2 November 2026 the site
plays Ida, Amazon Polly's synthetic Norwegian voice, whose terms, as read on 26 October 2026,
set no limit on storing and reusing its output. Ida reads every headword, example sentence and
definition line, and the inflection tables of the core vocabulary, of every irregular word and
of every adjective, each with a small play button and a speed setting ([159](decisions.md#d159)). What is recorded
today, and its licence, is on the About page, `ordpar/about.md`.

## 4. One Norwegian, many target languages

One website, one name, one address, with many dictionaries inside it, as Lexin does. The
Norwegian half of every page is the same whichever pair the reader chose; only the translation
changes. The data is already shaped this way: a row is Norwegian plus an English part, and a
Polish part would sit beside it. **One truth about Norwegian**: a correction to the source, a
refreshed article or a recording is made once and reaches every dictionary. The site treats the
target language as a parameter from the start, which is cheap now and expensive to add later.

**Each pair is its own dictionary** ([65](decisions.md#d65)): one site, but Bokmål–Polish is a
different dictionary from Bokmål–English, with its own pages and addresses (`/bm-pl/<id>/` beside
`/bm-en/<id>/`), never one page per article showing every pair. A free GitHub Pages site holds
at most 1 GB, and the Bokmål–English pages alone, once every article is translated, were
projected at about 1.1 GB (early November 2026); savings that change nothing a reader sees would
bring them to about 919 MB, not yet built ([156](decisions.md#d156)). So a second pair needs
hosting beyond one GitHub Pages site; where several pairs will live is open.

## 5. Feedback over signals

A yes/no button teaches little: a reader who did not find a word may have misspelled it, or the
word may not exist. Ordpar takes **free text per article** (a correction, a question, a
complaint) and sorts it into the records the project already keeps; the public box is a new
source for the existing correction work, not a new process. The **one mechanical signal kept is
the failed search itself**: a ranked list of words people typed and did not find is the list of
missing words, needs no interpretation, and is the honest input to "when have we translated
enough". Showing spoken-frequency figures on the page was considered and declined.

**When is a language done enough to start the next?** ([15](decisions.md#d15)) The readers
decide it: if no one complains that a word they looked up is missing, it may not matter; if
readers say a very common word is missing, that is the signal to go back. So the rule has two
inputs, both in this section: the failed-search list and the complaints in the question box.
[14](decisions.md#d14) says *which* language comes next; this says *when*. The two are
independent, because funding may arrive before the first dictionary is near done.

**Measurement** ([19](decisions.md#d19), [26](decisions.md#d26), [62](decisions.md#d62),
[104](decisions.md#d104)). No cookies and no third party. A free host gives no count per page
without a script, so a small receiver of our own (a free serverless function) counts visits and
records the few events this plan needs: the English site's searches (a miss and what was chosen
instead, a suggestion chosen while typing, counts of searches that found something), so that
the spelling help learns from real readers; and, for the partial dictionaries to come
(Bokmål–Polish and the others), a lookup that lands on an article with no translation in the
reader's language, the signal of what that dictionary should add next. No identifier and no
stored IP address; search lines kept 30 days, then only strings seen at least three times, as
counts; nothing logged offline. The receiver is built and takes correction reports; its counting
was not yet switched on on 12 November 2026. The privacy page says exactly what is sent. The
receiver is described in [`ordpar/docs/receiver.md`](../ordpar/docs/receiver.md).

## 6. Try it on a tenth of the articles

Many choices can only be judged by whether readers like them. A site with tens of thousands of
article pages can show a feature (the question box, the placement of a control, a default) on a
fraction of them and compare use before changing it for everyone. This needs only a page
counter, no accounts.

## 7. What it costs

Ballpark figures, dated; each to be checked before any commitment.

| Item | Measured or estimated |
|---|---|
| The whole Bokmålsordboka snapshot | 94,238 articles (20 September 2026): 20.3 MB gzipped; without editorial metadata 13.9 MB gzipped (139 MB raw); one article 1.5 KB on average, 6.6 KB at the 99th percentile, 83 KB at most (*gå*); the inflected-form index 1.47 MB gzipped |
| The translated library | 20,934 articles on 5 September 2026: 17 MB raw, 4.5 MB gzipped |
| The whole dictionary translated | English is 9 % longer than the Norwegian it translates (measured 20 September 2026), and prose is a quarter of the compressed bytes, so the whole translated dictionary comes to about 18 MB compressed |
| Text to read aloud | 51.3 million characters of text in the snapshot, all fields: an upper bound on what would be spoken |
| Voice, made once | Mainstream neural voices at about $15–16 per million characters: about $800 for everything; standard voices a quarter of that; premium voices several thousand (2026 list prices, unchecked) |
| Audio storage | About 900 hours at 48 kbps, about 20 GB; storage costs pennies a month; bandwidth is the cost, near zero on object stores with free egress |
| The text site | A static site at about 10,000 visitors a month: free to a few dollars a month on the mainstream static hosts. The domain `ordpar.no` (registered 8 September 2026): NOK 209 a year from 2027 ([13](decisions.md#d13)) |
| Accounts, forum, question box | A small database and server: about $5–25 a month at this scale |

For a static site, the price is set by bandwidth and storage, both tiny for text; for anything
with accounts, by a server running all the time; for audio, by the bytes served. The text site
needs no funding. Voices of higher quality than today's synthetic tier (§ 3.6) do, and are to be
funded before they are bought. A funding application is
written about the mission (§ 1), not the hobbyists.

## 8. Order of work

**The site and the Anki deck are independent builds; neither waits for the other**
([23](decisions.md#d23)). The one shared piece is the article's design: a card and an article
page are two views of one library row, so the article's anatomy and labels are settled once, for
both. The site uses the deck's article renderer (`ordbok_gen.py`) as it is, and the finished
site rendering is to become the deck's too ([30](decisions.md#d30)); moving the renderer into
`ordpar/` is ruled but not yet done ([48](decisions.md#d48)).

1. **The ordbokene.no feature review** ([1](decisions.md#d1)): the inventory with verdicts in
   § 2.1. Done 19 September 2026.
2. **The site, baseline first**: every article in Norwegian, English where written, inflected
   and fuzzy lookup, settings on the device, the failed-search log, the dataset download (§ 9);
   installable and offline from the start (§ 3.4), which is a property of the same code, not a
   later feature. The technical foundation ([24](decisions.md#d24)–[27](decisions.md#d27)):
   pages built in advance per article id, with the inflection as data; a search index in parts,
   read by the browser; GitHub Pages as the host, with a Cloudflare Worker as the receiver; a
   build that only reads the library and the Bokmålsordboka data, with the complete-translation
   check deciding what counts as translated.
3. **The question box on a fraction of the articles** (§ 3.5, § 6), then accounts, then the
   card for Anki, then the forum if the box shows there are people.
4. **Voice as funded** (§ 3.6).

The deck's own track: the new deck's release first, then the translation of the rest of the
dictionary, every new article complete.

**At launch, a link from ordbokene.no** (an idea, not scheduled): to ask to be listed on
ordbokene's page of useful links, a reasonable request once the site is public.

## 9. The dataset and the repository

The translated library, under CC BY 4.0, is a product in itself, for other tool makers, for
researchers and for the dictionaries in other languages. It ships with the site, in this
repository's `data/` folder.

**The repository** starts as one commit with no history: the cleaned code and docs, without the
private repository's working records ([184](decisions.md#d184)). The
code's working comments are kept as they are, decision numbers included; addresses, private paths
and account ids are taken out; the README says what the decision numbers are
([184](decisions.md#d184)). It is to be updated weekly. The scripts and stylesheets the live site
serves go out without comments, stripped by a small build step of our own
(`ordpar/sitegen/slim.py`, [61](decisions.md#d61)).

**What the code is for.** We hope ordbokene.no, or other dictionary sites, can take any of our
solutions into their own builds. So the code carries no conditions: **our own code and docs are
under MIT-0** ([184](decisions.md#d184)), and nothing in the code should prevent reuse; ordbokene's
unlicensed code is kept out by writing ours blind (§ 2), and anything from a third party that
enters the code is noted as it comes. The data's licences are separate: Bokmålsordboka's
Norwegian stays CC BY 4.0, its publishers' condition, not ours to waive; Ordpar's English is
written with AI, and whatever rights exist in it are given under CC BY 4.0. Ordpar's added example sentences are offered under CC BY 4.0 too. The full terms are on the About page and in `data/README.md`.

## 10. Ideas that lost, and why

- **A half-translated article shown as such** (a stub with a link to ordbokene.no): replaced by
  § 2's rule, the whole article shown in Norwegian.
- **A reading companion** (paste a text, every word linked, tap the unknown ones, get a deck):
  dropped on 5 September 2026. Even with a tagger to choose each word's article, a word would
  often lead to three articles; a text is a different thing from a headword, and machine
  translation already does the sentence; the dictionary does its work as the place you go for the
  one word the translation could not explain. Not to be proposed again in this form.
- **Spoken-frequency rank on the page**: declined.
- **The learner notes and traps on the default face**: declined (§ 3.2).
- **Accounts for settings**: not needed; settings on the device suffice until the personal and
  community layers.
- **A flashcard reviewer inside the app**: an idea of Robin's, still open as
  [16](decisions.md#d16). The recommendation is that Anki stays the reviewer, reached through the
  card button (§ 3.3).
