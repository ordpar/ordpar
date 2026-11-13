# Ideas for Ordpar: suggestions, not yet decisions

This is a list of ideas for the Ordpar site that are neither planned nor ruled: thoughts worth
keeping so they are not lost and not worked out twice. When an idea is taken up it becomes an
entry in [the decision log](decisions.md), and the line here points to the entry. What the site is
for and what it must do is in [the plan](plan.md).

Each idea says who had it and when, what it would take, and what is still unchecked. One standing
preference shapes the whole list: when it comes to options for the reader, the more the better.

## Settings, for the site and the deck alike

The finished site rendering is to become the Anki deck's rendering too ([30](decisions.md#d30)),
and the reader is the person best placed to know how they want an article shown. So every option
below is meant for **both** surfaces, as a setting.

- **Which language each line shows first**, Norwegian with the English revealable, English with
  the Norwegian revealable, or both, chosen per kind of line: definitions, examples, etymology and
  any other line. For definitions this is built as a three-way setting
  ([37](decisions.md#d37), [52](decisions.md#d52)); the defaults now put the Norwegian first
  ([174](decisions.md#d174)). For examples, the English behind a reveal for self-testing is
  built as a setting on the site ([111](decisions.md#d111)); the deck shows both languages by
  default ([131](decisions.md#d131)).
- **The interface language inside the article**: the section headings ("Senses and Example
  Sentences" / "Betydning og bruk") and the compound lines ("used as a suffix in" / "som etterledd
  i ord som") in Norwegian or English. Built on the site as the setting "Labels inside an
  article", English by default ([152](decisions.md#d152)).
- **The inflection table closed or open** by default: built ([43](decisions.md#d43)). **The
  participle frames on or off**: built ([31](decisions.md#d31)). **A third choice for the table**:
  behind its button, but open on a word with irregular forms, as the deck does; perhaps the choice
  of the "For learners" preset.
- **The printed dictionaries' inflection codes** (*hus* "n1"), as a setting on ordbokene.no shows
  them after the word class in search results: skipped ([21](decisions.md#d21), 21c), a possible
  later addition. The data carries them (`inflection_class`).
- **Sense order**: ordbokene's, or by how much each sense is used (under *Article page* below).
- **Summary glosses only in the article's head, or also beside their senses** (under *Article
  page*; needs sense tags).
- **A colour theme**: maroon by default; blue, green or others on request.
- **The small article's layout** as its own setting, by default following the article's; **the
  short translation shown when pointing at a cross-reference** a setting, on by default: built
  ([52](decisions.md#d52), [54](decisions.md#d54)).

Open: what a deck setting needs that a site setting does not. An Anki card has no reliable
storage on the device across Anki's apps, and a choice made at build time (sense order) is fixed
in the card's HTML.

## Favourites, history and settings on every device (for later)

Today a reader's favourites, history and settings live only in the browser. Settings can be
exported and imported as a file, and settings can travel in an address
([146](decisions.md#d146)), but moving everything to another device is manual. Robin noticed
(7 November 2026) that another site for learners of Norwegian syncs a reader's word list across
devices through an account. Three possible ways, none ruled:

- **accounts**: a store per reader, sign-in, password reset, and personal data the privacy page
  must cover;
- **a sync code**: the data stored under a random code beside our Cloudflare Workers (for example
  in Workers KV), with no email or password; whoever has the code has the data, and a lost code
  means lost data;
- **a link** carrying the data, opened on the other device, with nothing stored by us.

Other sites may be looked at and asked for advice, but their code is never read to be copied:
ours is written only from what a site shows ([12](decisions.md#d12)).

## Pictures on noun articles, from Wikimedia (for later)

Robin, 7 November 2026: pictures are a different kind of content from the article text, set
beside it rather than mixed into it, so they may suit the site even where share-alike text would
not. **The licence question is to be checked against the licence texts before anything is
built.** What it would bring: a credit per picture (author, licence, link); a line on the About
page and with the data download saying that pictures carry their own licences; unchanged pictures
only (a crop may count as a change); pictures served from our own host, never from Wikimedia's,
since a reader's IP address must not go to a third party ([19](decisions.md#d19)), which costs
space against GitHub Pages' 1 GB ([156](decisions.md#d156)); and a recorded divergence, since
ordbokene.no shows no pictures.

**A setting, off by default**, turned on by the "For learners" preset
([136](decisions.md#d136)). When it is off, a picture is never downloaded, not only hidden.

## The "For learners" preset, closer to the deck (a later, larger build)

Robin, 7 November 2026: the preset ([136](decisions.md#d136)) could turn on more of what the
deck gives a learner: first the word's **CEFR level** where one exists, then the pictures above.
To settle when it is taken up: the deck's levels are assigned by AI and not yet checked against
an outside source; how many articles have one; where the level shows (the headword line, the
list rows); what else in the deck a learner would want on the site.

**Random word by level** (the same day): a choice of level for *Random word*, which would draw
only among words at that level; C-level words are of little use to most learners. Random word
today draws from every headword ([115](decisions.md#d115); in English, [155](decisions.md#d155)).
It needs the levels first.

## Article page

- **The headword marked inside its examples** (seen on PONS: *might I **suggest** a white
  wine*). Our examples are in italics with nothing marked. It needs no new writing: the inflection
  data lists every form, so the build can find and mark the headword's form in each example
  (*foreslår*, *foreslått*, *slitne*), the form and not just the dictionary form, as Lexin does. A
  setting if anyone finds it noisy. To check on a sample: multi-word expressions, and forms that
  are also another word.
- **The seam drawn in compound lists** (seen on Lexin: *bro|hode*). Our "Used as a suffix in" and
  "Used as a prefix in" lists know the headword, so the seam is known: *gang|bru*, *henge|bru*. A
  hairline or a thin space, not a bar.
- **A gloss beside the sense, only where the senses translate differently** (Robin, 20 September
  2026). The library holds one summary gloss per article, its items in order of salience, and
  none per sense. Often an inline gloss would only repeat: *bru*'s four senses all translate as
  *bridge*, and *bli*'s definitions are already lists of equivalents. The sense that needs one
  has a descriptive definition in an article whose glosses differ by sense. The light way is a
  sense tag on each summary item (*bli*: *to become* → 2, *to stay, to remain* → 1, *to be
  (forming the passive)* → 3): the head still shows the items in salience order, and the page
  sets an item beside its sense only where the items map to different senses. Writers check a
  tag; they write no new glosses. The same tag gives the head's superscript sense links
  ([42](decisions.md#d42)). The tags must allow a sense with no item (*pålegg* 1), an item that
  leads although its sense is third, and an item that is itself a cultural note (*dugnad*:
  *communal voluntary work, a working bee*). Two partial sources exist: a citation into a sense
  carries the citing article's gloss, and compounds carry an English word each.
- **A gloss lights up its senses** (Robin, 26 October 2026, once the tags exist): pointing at a
  gloss in the head highlights the sense or senses it is tagged to; a click or tap pins the
  highlight while the reader scrolls. On a phone the tap is the whole feature. To settle: what
  clears a pin, one highlight style shared with a sense reached by a `#def` link, perhaps the
  reverse (a sense lighting its glosses). Whether the gloss itself, its superscript number, a
  double-click or a setting should also jump to the sense is left to a test page where Robin
  tries each, once tags exist.
- **Senses ordered by use, as a setting or the default** (Robin, 20 September 2026). Ordbokene
  orders senses literal before derived (*bli* 1 *to remain*, 2 *to become*); learner's
  dictionaries usually order by use. Addresses do not break: citations point to a sense's id,
  and the numbers are derived, so numbers, `#def<N>` anchors, link labels and small articles'
  sense marks all change together, provided the site and the deck take their numbers from one
  shared ordering function. Needs the sense tags and a fallback for untagged or shared senses
  (ordbokene's order). Cost: our "*bli* 2" is no longer ordbokene's, so the page should say which
  order it shows. One built page serves both: each sense block carries `data-defn` and
  `data-rank`, the setting sorts the blocks, the numbers are CSS counters, anchors are by id; a
  small article's sense number must follow the page's current order. Without JavaScript the
  reader gets the built order.
- **A short paradigm on one line under the headword** (PONS: *tired <-er, -est>*; Cambridge:
  *~slår – ~slo – ~slått*): comparison or principal parts on one line, the full table kept for
  the full paradigm or opened from the line ([40](decisions.md#d40)).
- **Pronunciation in IPA** (Cambridge gives it per headword, with variants). Ordbokene has none
  and we have no source; Wiktionary's Norwegian IPA (CC BY-SA) is the one to assess.
- **Labels and slot markers with a tooltip** (PONS: *sth*, *sb*, *inf*, *pej* underlined with
  dots, the full form on hover). Our labels and the *sb/sth* slots in glosses could do the same,
  one interface string per abbreviation.
- **The sense heading repeats the headword** (PONS: "1. suggest *(propose)*:"), so a sense read
  alone, from a `#def` link or in a small article, stands on its own.
- **Example pairs side by side on wide screens** (PONS's two columns; Collins's pairs on one
  line). Ours put the Norwegian above the English; a responsive or optional layout.
- **The passive verb forms** as a sixth column or a line under the table: ordbokene omits
  *spises*, but the data has it ([40](decisions.md#d40)).
- **Settled since**: a cross-reference control on the Norwegian line (the link now sits on
  whichever line leads, [54](decisions.md#d54)), and the "Show Norwegian" cue as an interface word
  inside the article (the Norwegian is no longer hidden, and the remaining "Show English" cue is
  added by the page script).
- **Audio for the target language too** (Robin, 4 November 2026): speaker icons on the English
  glosses, definitions and examples, behind a setting, beside the Norwegian audio
  ([159](decisions.md#d159)), for Norwegian speakers learning English. Not a priority: the main
  audience is people learning Norwegian.

## Search

- **A "translated only" filter** on the suggestions and results: each suggestion already marks
  whether its article is translated; a control does not exist yet.
- **Taken up**: the summary gloss beside each hit, and suggestions ranked by how common the word
  is ([59](decisions.md#d59)).
- **Spelling corrections learnt from real searches** ([55](decisions.md#d55)): a failed search
  followed shortly by a successful one gives a misspelling and its correction, an automatic form
  of a hand-made "did you mean" list that finds what readers really type. It needs the search
  log ([26](decisions.md#d26), [62](decisions.md#d62)); since the site counts without cookies
  ([19](decisions.md#d19)), two searches can be linked only within one browser tab.
- **A Nynorsk word typed into the Bokmål search** ([55](decisions.md#d55); *kva* → *hva*).
  Ordbokene.no shows a "Possible translation" box when a word is in one dictionary only, based
  mainly on the Apertium translation program, by its own account. The links Bokmålsordboka's data
  itself has to Nynorsk articles (5,585) include none of the common pairs (*hva/kva*,
  *ikke/ikkje*, *jeg/eg*; checked 18 October 2026). Our way in would be to run Apertium's
  Nynorsk–Bokmål pair (GPL-2.0) over the Nynorsk headwords to build our own list; whether such a
  list may ship in a CC BY index is unchecked.
- **Set phrases ranked by their own frequency** (Robin, 21 October 2026; low urgency). The
  National Library's 2026 n-gram release has two- and three-word files beside the single words the
  site uses ([55](decisions.md#d55)). Counting each set phrase there (inflected variants summed,
  slot words such as *noen*, *seg*, *sin* matched loosely) would rank set phrases among themselves.
  It matters where many compete: 3,858 of the library's 6,171 set phrases share their first word
  with more than five others, and 555 their first two (*gå i* 34, *ta seg* 21), so typing *ta seg*
  has 21 phrases for five places. Set phrases stay after the headwords in the suggestions
  ([59](decisions.md#d59)); a very common one might rarely go above them. Limits: three words at
  most (longer phrases by their rarest part); a literal use counts as the idiom; the files' sizes
  are unchecked. First step: that measurement, with a check of a few groups' top phrases.
- **Name the form in the results** (Robin, 21 October 2026): not only "“kjørte” is an inflected
  form of:", but "“kjørte” is the past tense of: *kjøre*". The data tags every inflected form with
  its table cell, and the inflection tables already name the cells in English, so the index would
  carry a short cell code per form (its growth to be measured). A form in several cells names them
  all (*kastet*: past tense and past participle of *kaste*). First step: see what ordbokene.no's
  own results say.
- **An advanced search page** (Robin, 29 October 2026; a separate build). Already in the plan's
  inventory ([plan § 2.1](plan.md)). Ordbokene.no's form has a scope (headwords, with inflected
  forms, full text), a word-class filter, patterns (`hus*`), paging and a list view; a full-text
  search for *båt* there finds 308 articles (checked 29 October 2026). For us: full text over the
  Norwegian and the English, the direction switch ([148](decisions.md#d148)), a "translated only"
  filter. The cost to measure first: full text needs a word index over every article, far larger
  than the headword and gloss indexes, and the offline copy would have to carry it or go without.
  Ordbokene's own offline app goes without advanced search, a baseline for offering it online only.

## Accessibility, after the look ([75](decisions.md#d75))

Robin, 23 October 2026: options such as larger text for readers with poor sight, taken up after
the work on the site's look, so their effect on the layouts can be seen.

**Where the site stands** (checked in the code, 23 October 2026): the viewport allows zooming,
and every font size in `ordpar/site/shell.css`, `ordpar/site/inflection.css` and
`ordpar/sitegen/page.py` is in `em` or `rem`, so a browser's or phone's text size already scales
the text. Not checked: how the pages look at 200 % (the suggestion rows and the small articles are
placed by measurement).

1. **A WCAG check**: text at 200 % with nothing cut off or overlapping (1.4.4), the page usable at
   320 CSS pixels wide (1.4.10), contrast in both themes (1.4.3; the dark-mode contrast test was
   put off in [100](decisions.md#d100)), each a browser test like those in `ordpar/tests/browser/`.
2. **A text-size setting** under Settings → Style, for readers who want Ordpar larger than other
   sites: since every size is relative, nearly one value (the root size, say 100 / 115 / 130 %).
3. **If readers ask**: more line spacing; links underlined, for readers who cannot tell the link
   colour from the text.

## Speed, after function and look

The order of work: first make the dictionary work well, then make it look good, and last make it
fast. Ideas here wait for that last phase unless one is cheap enough to take earlier.

- **Prepare the likely next article, offline above all** (Robin, 21 October 2026). When results,
  the "inflected form of" choices or the suggestions appear, prepare those pages so the next click
  opens at once. Two levels: (1) the page tells the service worker which articles are likely and
  it unpacks them into storage ahead of the click (cheap; offline only; survives Android stopping
  the worker); (2) the browser's speculation rules draw the likely page in the background, online
  and offline, though whether that works with our worker offline is unchecked. First step: time
  the worker's wake-up, the unpacking and the drawing of a page on a phone (on a desktop, 19
  October 2026: 41–59 ms to unpack a page from a bundle against 11 ms already unpacked). If
  unpacking dominates, (1) is enough; if drawing does, (2), or swapping the article inside the
  page ([24](decisions.md#d24)).
- **Offline bundles without the page frame (parked).** The offline copy stores each article page
  whole, 500 to a bundle, and a bundle whose bytes change is downloaded again. The idea: store
  only each page's own part (`<main>`, the per-page data on the `<html>` tag such as `data-snip`
  and `data-drop`, the head's per-page lines) and let the worker put the shared frame (head,
  header, footer) back, so a change to the frame touches no bundle. Measured on 28 October 2026:
  the download would shrink from 30.8 to about 28.5 MB (the frame is half the pages' raw bytes,
  but compresses well); of 20 site updates between 23 and 28 October, 10 rewrote every bundle, 2
  through the frame alone and 1 nearly, the other 7 through the articles themselves; about 63 of
  the roughly 233 MB downloaded would have been spared, and a copy updated once a day would have
  saved nothing. Parked because the re-downloads came from feature work that changes the articles;
  once the site settles, frame changes may be most of what is left, and the count is worth taking
  again then. A build would touch `ordpar/build_offline.py` (`blank`, `restore`), the worker
  `ordpar/root/sw.js` (`restore`) and a template per kind of page, with
  `python ordpar/build_offline.py --verify` proving each reassembled page byte for byte.

## Beyond the site: looking up from anywhere

Robin, 21 October 2026, for when the dictionary is in good shape: select Norwegian text anywhere
(a web page, a PDF, a document) and open it in Ordpar in a pop-up: in a browser extension first,
ideally anywhere on the computer, and on e-readers for Norwegian books.

The cheapest route has two parts: (1) **exports in standard dictionary formats** (the library
already holds every inflected form), so that existing readers do the looking up: GoldenDict on
the desktop, Kindle and Kobo, KOReader, the Mac's Dictionary; (2) **a browser extension** for the
web. Unchecked: whether a Kindle offers a side-loaded dictionary for Norwegian books, whether an
extension's menu reaches Chrome's PDF viewer, each format's packaging. Every export carries the CC
BY 4.0 credit for Bokmålsordboka's Norwegian.

What existed on 21 October 2026: ordbokene's own app and an offline web app for exams, but no
extension, e-reader dictionary or desktop pop-up of theirs; one third-party Chrome extension that
opens a word on UiB's site (last updated 2017); Bokmålsordboka and Nynorskordboka converted by a
third party in 2026 for Kobo and KOReader, Norwegian only; nothing for Kindle. A Norwegian–English
version in these forms would be new.

**A pop-up with no extension of our own: Definer** (26 October 2026). Definer, a general pop-up
dictionary extension for Chrome and Firefox, accepts any website as a custom source: an address
with `{{str}}` where the selected word goes, plus optional CSS to fit the page into the pop-up.
It works with Ordpar today, with no build: Robin tried it in Chrome and Firefox, and it showed
Ordpar as on the site, small articles included; in a PDF it works in Definer's own PDF reader, not
in Chrome's. It relies on ordpar.no sending no header that forbids showing it inside another
page (`X-Frame-Options`, or a `frame-ancestors` rule; none sent on 26 October 2026). The setup:

```
https://ordpar.no/bm-en/#q={{str}}
.ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; }
```

The pop-up shows the site's own search, including the "inflected form of" step, which tells the
reader what the form is (a first wish to jump straight to the article was dropped after the try).
Ordpar has a page explaining this setup ([142](decisions.md#d142)). **No extension of our own for
now**: only if readers find the setup a barrier or ask for one. What an extension of our own would
add is no setup and a listing in the browsers' stores, against building it twice, store reviews
and upkeep.

Two limits found in the try: the pop-up uses the default settings, not the reader's, and it does
not work offline even when Ordpar is installed. Both seem to have one cause (unchecked for
Definer itself): the pop-up shows ordpar.no inside a frame on another site, and browsers keep such
a frame's storage apart from the site's own. **Settings in the address** solves the first: built,
a Copy button gives the address with the reader's own settings, applied to that visit only and
stored nowhere ([146](decisions.md#d146)). **Offline in the pop-up** stays an idea: the frame cannot
reach the copy on the device, and only an extension of our own could hold the data, which is the
real argument for one.

## Readers as quality control

**Taken up** into the translation-quality work of the private repository; this is the idea as it
was first put.

A reward for readers who find a real mistake in our translations, mainly for the languages after
English, where we have no human quality control yet. The report box comes first in any case: it
is the channel a reward would need, and it needs our own receiver ([19](decisions.md#d19),
[166](decisions.md#d166)). The cheapest reward is credit, "corrected thanks to a reader's
report" in the library's list of changes ([95](decisions.md#d95)). Money brings more reports to
judge, and anyone can run a model over the dictionary to produce them, so a money reward would
wait for a funded reviewer, native in the target language and fluent in Norwegian.

**A line-by-line comparison with Lexin** (Robin, 22 October 2026; after the revision of our
lexicographical principles). Lexin's Bokmål–English dictionary (OsloMet), made by people with
native speakers, as the reference: a large sample of its entries converted to our format and
translated by our usual workflow from Lexin's own Norwegian, then each pair of lines (ours and
Lexin's English for the same Norwegian) judged blind by AI judges (ours better, Lexin's better,
equal), and Robin checking every case where they found a clear difference. It measures our
workflow against a professional human reference. **Only with Lexin's permission**: the data used
privately, never in our dictionary, and the improved sentences offered back to them. Design
points: the judges blind to which line is ours (random order, house style removed, since model
judges may prefer model-written text); each verdict saying whether it is about meaning or style;
the sample sized by lines (about 3,000 a side to detect a doubling of a meaning-error rate near
1 %).

## Readers together: questions answered by fellow learners

An idea discussed on 23 October 2026; nothing ruled or planned. Can readers ask questions and
answer each other with no cookies and no accounts? Yes: posts through a receiver of our own
([26](decisions.md#d26)), readers posting under a chosen name, and a secret code per post kept in
the browser so that its writer can edit or delete it. The hard parts: moderation, responsibility
for what is posted, the authority of the answers, and keeping bots out.

- **Moderation by AI** fits how the project works: a model screens each post before it shows (or
  after, with flagging), and Robin rules on appeals. It costs computing per post, and a person
  stays responsible for what stays up.
- **AI answers, if offered, are checked** like the dictionary's own text, and marked as the AI's;
  readers' answers are marked as readers'.
- **Keeping bots out without a third party**, in our own receiver: a hidden field only bots
  fill; a limit per address, the address used in the moment and never stored; a small
  proof-of-work puzzle the browser solves before posting; and the AI screening behind them.
  Cloudflare's own bot check is another option, to weigh against [19](decisions.md#d19). The
  limit can be counted under the daily code of the visit counter ([104](decisions.md#d104)),
  counting posts and holding no text; but the counts must live in storage that expires within the
  window, apart from the visit records, since a post's time could otherwise link it to its
  writer's reading. Limits generous: a school or library shares one address.
- **Learning by answering** is the idea's real strength: answering a question is a way of
  learning too, and learning with other learners is more fun than with an AI. A fit for after
  launch, once there are readers to talk to each other.

## The Language Council's language advice, translated and linked (not for now)

**Taken up** into a plan of its own in the private repository.

Robin, 23 October 2026: translate the Language Council's published answers to language
questions (sprakradet.no, *Språkspørsmål og svar*) into a searchable collection, linked from the
words they discuss: from *da*, *siden* and *fordi*, the answer on when to use which. Because the
answers are authoritative, this would come before any AI question-and-answer feature.

What is known (23 October 2026): sprakradet.no states no licence for the answers, only how to
cite them. Linking to the Norwegian originals needs no permission; translating and republishing
them would need the Language Council's permission, which had not been asked. There are about 1,122 answers, tagged by category,
not by word, so mapping them to headwords means matching titles or the words in italics.

Points agreed so far:

1. **A cheap first step**: link articles to the Norwegian answers, untranslated, which shows
   whether readers use the links.
2. **Translations marked as Ordpar's unofficial translation**, with a link to the original, so the
   Language Council's name is never on our wording.
3. **The Norwegian examples stay Norwegian**, as quoted words; only the explanation is
   translated, with care for grammar terms and hedges.
4. **Context for the translator**: every word in the text with two or more senses has its library
   row passed to the translating model. Counted over 21,871 rows with senses: 14,894 have one
   sense, 3,500 two, 2,692 three or four, 698 five to nine, 87 ten or more; 1,616 have sub-senses.
   Useful for any longer translation, not only these answers.

## Seen elsewhere

Other bilingual dictionaries' articles, read on 20 September 2026 for what they do about the
questions still open on our pages. Test words on every site: *suggest*, *bridge*, *run*, *tired*
(and *foreslå*, *bru*, *løpe*, *trøtt* where the site starts from Norwegian).

### Collins English–German (collinsdictionary.com)

A translator's dictionary: dense, no inflection, no small articles, each example on one line.

- **Most senses have no definition: the translation is the sense.** *bridge* 2–5 are `(NAUT)
  (Kommando)brücke f`, `(of nose) Sattel m`, `(DENTISTRY) Brücke f`, `(BILLIARDS) Steg m`. An
  English note such as `(= fatigued)` or `(= propose) candidate, place, idea etc` is a synonym or
  the typical objects, there only to steer the reader to the right translation; it never
  defines. Ours is a translated monolingual dictionary: a full definition per sense, the gloss
  beside it. The lever this suggests is one step beyond the definition-language setting: whether
  the *gloss* or the *definition* is the visible line, with the other revealable.
- **Every translation links** to the other direction's article, gender beside it (*Brücke f*).
  Our nearest equivalent is the English search over the summary glosses
  ([148](decisions.md#d148)).
- **Example pairs on one line**, source regular, translation bold, grouped under the sense: a
  denser article; a possible display setting.
- **A sense with no translation** (*tired* 2): only patterns, `to be tired of sb/sth …`. Some
  senses are usage, not a word; our renderer should not assume a gloss line exists.
- **The frequency band as five dots** in the head: a possible form for labels of how common a word
  is.
- **One page for all word classes** of a headword, with no homograph numbers. Ours follows
  ordbokene's split into articles ([33](decisions.md#d33)); a joined view of a headword's articles
  is a design not yet considered.
- **Labels as tiny parentheticals in the line**: `(fig)`, `(inf)`, `(+acc)`, slot markers
  *sb/sth*; *or* in italics between alternatives.
- A copyright line under every article: a precedent for our credit line ([32](decisions.md#d32)).

### PONS English–German (pons.com)

The same logic as Collins, laid out as a table of pairs, source left, translation right.

- **Everything is a pair row**: the headword with its slots (*to suggest sth [to sb]* ↔ *[jdm]
  etw vorschlagen*), patterns (*to suggest that …*) and full examples, told apart by style.
  Patterns are a unit between gloss and example that our data does not have. PONS has some twenty
  rows for *suggest*, ordbokene three for *foreslå*. Measured the same day in our library: a third
  of the translated articles have no example at all, and 29 % of senses none; among the commonest
  words, 9.4 % of articles and 12.6 % of senses (about 2,100) have none. Robin counts this the
  biggest gap in our dictionary, and in ordbokene's; the added example sentences address it.
- **The headword bold in every example**, **inflection in the headline**, **every label an
  abbreviation with a tooltip**, **the headword repeated in each sense heading**: each listed
  under *Article page* above.
- **Audio on both sides of every row**, a copy button per row, and readers' entries kept in a
  separate block with its own heading: a model for the community layer, kept visibly apart from
  the edited article.
- **Senses belong to the source word, so counts do not compare.** PONS gives *suggest* five
  senses; ordbokene gives *foreslå* one. That is not a gap but the two words' own range: *indicate*,
  *evoke*, *come to mind* are English senses, rendered in Norwegian by *tyde på*, *antyde*, *falle
  inn*; *foreslå* means "to put forward", and every use of it is that. Our three summary items
  (*to suggest · to propose · to nominate*) are three renderings of one sense.

### Cambridge Norwegian–English (dictionary.cambridge.org)

Licensed-in data (K Dictionaries' GLOBAL Norwegian–English), not Cambridge's own work. Sparse:
*bro* has two senses (ordbokene four), one example each, no etymology, set phrases or compounds.
By that comparison our articles add a great deal for the pair.

- **Norwegian definition, English gloss, one example pair** per sense: the reverse of our default
  layout. It reads well at that size; ours carries far more per sense.
- **Principal parts in the line** and **IPA with variants**: listed under *Article page*.
- **"Add to word list"** per sense: the personal layer of the plan.
- A credit line naming the licensed source: another precedent for our credit line.

### Jisho (jisho.org, Japanese–English)

Its article design is built around the Japanese script and has no counterpart for us. On the
search side:

- **The results page is the articles**: an English query returns the entries themselves, not a
  list of links.
- **Tags as small labels under the headword** (*common word*, *jlpt n1*): another form for labels
  of how common a word is; and an English query finding 110 Japanese words through their
  translations, which is the English search working as ordinary search.

### Lexin (lexin.oslomet.no, Bokmål–English)

The learner's dictionary for immigrants to Norway, the closest to us in kind. Every row is a
Bokmål/English pair with a field label beside it (*oppslagsord*, *ordklasse*, *forklaring*,
*eksempel*, *uttrykk*, *sammensetning*).

- **Definitions in both languages, both visible**: the only site in the comparison that does
  this; it is the "both" option of our definition-language setting, as a default.
- **The gloss under the headword** (*propose, suggest*): as our summary gloss
  ([42](decisions.md#d42)).
- **The headword highlighted in every example, inflected forms included, and the seam drawn in
  compounds** (*bro|hode*): under *Article page* above.
- **Inflection behind "Vis bøyning"**, closed by default: as ours ([43](decisions.md#d43)).
- **One meaning per entry**: *bro* the structure and *bro* in teeth are separate entries, so Lexin
  never numbers senses. A simplification for learners, not for us.
- Audio on every Norwegian item; IPA with stress marked; labelled rows for readers new to
  dictionaries.
