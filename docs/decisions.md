# Decisions

This is the decision log of Ordpar, a Norwegian–English dictionary built on Bokmålsordboka. It records the
project's decisions, each with its reason, numbered in the order they were raised. The comments in the code cite
them by these numbers ("site decisions 126", "decisions 93 (2)"); where a citation names a part of an entry, such
as **(2)**, **item 9** or **21a**, that label marks the part in the entry.

Ordpar is Robin Fauskanger's project; the entries call him Robin. The project keeps a longer working record of its
decisions, with the discussion behind them. The entries here were retold from that record for outside readers and
checked against it, then cut to what someone working on the code needs: each decision as built, and its reason.
Decisions about the project rather than its code are left out, so the numbers have gaps: 6, 7, 8, 10, 11, 28, 35,
50, 51, 66, 73, 79, 96, 122, 135, 140 and 181 are not here.

Each entry opens with its number, a plain title and the date the question was opened. The **Status** line beneath
says where the decision stands: open, ruled, built, live since a date, or dropped, and, where a later entry changed
it, which entry amended, replaced or reversed it, with a link. An entry is best read with the later entries its
status links.

If you find an error, please report it as an issue on this repository, or write to `post@ordpar.no`.

<a id="d1"></a>
### 1. The review of ordbokene.no's features, and what it delivers (2026-09-05)

**Status:** done, 19 September 2026.

ordbokene.no was walked function by function and every feature was given a verdict: keep, adapt or skip. This inventory is the site's specification sheet, since ordbokene.no is the project's baseline for presentation. The review records what each feature does, never how it is built: only the dictionary's content is openly licensed (CC BY). It was finished as a table of about 95 behaviours, each with a verdict and a live address; the rows it left open were ruled in [17](#d17) to [22](#d22).

<a id="d2"></a>
### 2. Untranslated articles are shown in full, in Norwegian (2026-09-05)

**Status:** ruled; built.

The site carries every article of Bokmålsordboka. An article is shown translated only when its English is complete; every other article shows ordbokene's Norwegian text in full, with a note that it has not been translated yet. So there are no holes: a reader always finds the word, sometimes only in Norwegian. Small articles at the edge of the translated part follow the same rule. Each site update switches the newly completed articles to English, and nothing is ever shown half in English. Ordbokene's text is CC BY, which allows this. The rule is applied per unit: a set phrase inside a translated article is likewise shown either fully translated or in Norwegian ([58](#d58)).

<a id="d3"></a>
### 3. The reverse direction: English to Norwegian (2026-09-05)

**Status:** ruled; the site's form amended by [17](#d17); the English search live since 30 October 2026 ([148](#d148)).

For the site: a second direction beside the Norwegian–English one, Norwegian the default. How it appears on the site was changed by [17](#d17): not a second panel, but a search of its own.

<a id="d4"></a>
### 4. No accounts until there is something that needs one (2026-09-05)

**Status:** ruled.

The site has no user accounts for now. Settings and preferences are kept in the browser on the reader's device; they last until the reader clears the site's data or changes browser or device, which is acceptable for preferences of this kind. Accounts would come only with features that need them, such as sending a card to Anki in one step or a question box or forum, and then only as sign-in with Google or Apple, with no passwords of Ordpar's own. History and favourites later followed the same rule ([60](#d60)).

<a id="d5"></a>
### 5. The app's first form: an installable web app, native later (2026-09-05)

**Status:** ruled 20 October 2026; built early for [61](#d61), live since 20 October 2026.

A web app is the same website opened as an app: its own icon on the home screen, its own window, the dictionary available offline, on iPhone and Android alike, with no app store needed. Ruled: the web app first, one codebase for the site and the phone. A native app stays a later question.

<a id="d9"></a>
### 9. The default page looks like ordbokene.no; learner extras behind one control (2026-09-05)

**Status:** ruled; the learner notes are not yet shown on the site.

The project writes extra notes for learners, such as a usage note and a warning about a common mistake ("trap"). Ruled: these are not shown by default, but a reader can reveal them through a control on the page; the default face of an article stays as ordbokene.no's. How often a word is used in speech is not shown on the page.

<a id="d12"></a>
### 12. A recognisable family resemblance, never confusion (2026-09-05)

**Status:** ruled; refined 19 September 2026 (the article, not the site); amended 17 October 2026 by [32](#d32) (the credit line), 18 October 2026 (code written blind) and 19 October 2026 by [63](#d63) (the colour).

The same features and the same layout of an article, built in Ordpar's own code, are imitation and acceptable; ordbokene's files, name and logo are off limits. Ruled: a family resemblance is welcome, mistaken identity is not. So Ordpar has its own name, logo, header and front page, while ordbokene's colour scheme and the layout of an article may stay, with a line on every article saying where the text comes from and that Ordpar is not affiliated. The resemblance is the article's, since Ordpar's articles are translations of ordbokene's; search, the front page, settings and every other part of the site are designed on their own terms. The `ordpar.no` domain was registered under a declaration that the name does not give the impression of involving a public authority, so the not-affiliated line and a front page of its own also keep the domain.

**Amended by [32](#d32):** the full attribution on every article became a one-line credit linking to an About page with the full text. CC BY 4.0 allows attribution by a link to a page that carries it. The credit keeps the source, the licence and "Ordpar is independent of both" on every article, so a reader who arrives from a search engine still sees which site they are on.

**Amended:** Ordpar mirrors what ordbokene.no shows, never its code. Ordbokene's code may be read to learn how something works, but Ordpar's own code is written blind: the behaviour to match is written down in Ordpar's own words, from what ordbokene.no shows, and the code is written from that description by someone who has not seen ordbokene's. The reason: the Norwegian database is CC BY 4.0, and that licence covers the dictionary's content only.

**Amended by [63](#d63):** ordbokene's colour scheme did not stay as the default. Ordpar has a colour of its own, Wine; ordbokene.no's maroon is one of the optional schemes in the settings, named for its source.

<a id="d13"></a>
### 13. The site's name: Ordpar (2026-09-05)

**Status:** ruled 20 October 2026; `ordpar.no` registered 8 September 2026, live since 20 October 2026.

One name was wanted for the whole site and every language pair in it. *Ordpar* ("word pair") was chosen. *Ordpar* says what the dictionary is, fits every language pair, and every sound in it exists in Slavic and Baltic languages.

Ruled with it: only the `.no` domain, a Norwegian name on a Norwegian domain being the neutral choice for readers from anywhere; the name `ordpar` on GitHub, no social media accounts. The domain was registered on 8 September 2026 with a registrar that signs it with DNSSEC; the domain's name servers stay with that registrar. The domain's contact address is kept outside `ordpar.no`, so that warnings still arrive if the domain itself fails. Written form: *Ordpar* in running text, `ordpar.no` as the address.

<a id="d14"></a>
### 14. The next language follows the funding (2026-09-05)

**Status:** ruled.

The work needs outside funding. When to move to a next language is a separate question ([15](#d15)).

<a id="d15"></a>
### 15. When a language is "done enough" to start the next one

**Status:** open.

[14](#d14) settles which language comes next, not when. Readers' complaints and failed searches were suggested as the measure. **(1)**, recommended: no fixed fraction; publish failed searches and unanswered complaints as a monthly figure, and start the next language when the misses stop being common words.

<a id="d16"></a>
### 16. The app as a full package: does it review cards itself, or hand them to Anki?

**Status:** open.

The idea: the app could hold both the dictionary and the flashcards, removing the step of downloading a card, opening Anki and importing it. **(1)**, recommended: hand cards to Anki rather than rebuild it, since Anki has a long-developed scheduler, sync, and the reader's existing decks; the effort goes into making the handover one tap. **(3)**: the full package; not recommended until the site and the deck are both established, since it is a larger build than the dictionary itself.

<a id="d17"></a>
### 17. Search results in one column; English to Norwegian as a search of its own (2026-09-19)

**Status:** ruled; amended 19 October 2026; the English search live since 30 October 2026 ([148](#d148)).

ordbokene.no shows both its dictionaries, Bokmål and Nynorsk, for every query, in two columns side by side. Ruled: no two columns. Ordpar has only one dictionary, so a query shows Bokmål articles in one column. This settles the site's form of [3](#d3)'s reverse direction: searching by an English word is a separate way into the dictionary, whose result is the Bokmål articles whose English matches.

**Amended:** the English search was refined: a switch for the direction, as ordbokene.no lets the reader choose between its two dictionaries; the summary glosses as the index; its own suggestions while typing; British and American spellings matched; results ranked by the place of the English word in the gloss, then by how common the Norwegian word is.

<a id="d18"></a>
### 18. An inflected form stays on its own search page (2026-09-19)

**Status:** ruled; built.

When a reader searches an inflected form such as *husene*, should the site jump to the headword *hus*, or stay on the form? ordbokene.no's help page described a redirect, but the live site stays on the form's page and shows a panel naming the headword it belongs to. Ruled: no redirect; follow ordbokene.no's live behaviour. Every form has its own search page, and the panel lists each headword the form belongs to as a link that runs a new search for that headword. A form shared by two headwords (*torde*: *tore*, *tørre*) is simply the same panel with two rows, so no question of a single canonical address arises.

<a id="d19"></a>
### 19. No cookies and no third party; what is counted (2026-09-19)

**Status:** ruled; the visit counts corrected by [26](#d26); the English site's search logging amended by [62](#d62); the receiver built, its counting not yet switched on ([104](#d104)).

ordbokene.no's privacy page said it counts visits without cookies and uses only the browser's local storage. Ordpar needs a count per page to test features such as the question box on a fraction of articles. Ruled: no cookies, as ordbokene.no; no paid third-party counter for now, so that no third party sees the readers. A small receiver of Ordpar's own records the few events the plan needs. The privacy page says what is sent. Settings stay in local storage. The English dictionary logs no failed searches, since every word will be translated anyway; for partial dictionaries in other languages, a lookup that lands on a Bokmål article not yet translated into the reader's language is logged, to show which articles to translate next. [26](#d26) found that a free host gives no per-page count without a script, so visits are counted by Ordpar's own receiver. [62](#d62) reopened logging for the English site, so that the spelling help can learn from real searches.

<a id="d20"></a>
### 20. Nynorsk: skipped, with a path left open (2026-09-19)

**Status:** ruled.

Ruled: skip, with nothing added to the data model; Nynorsk is revisited only if a Nynorsk community asks for it or funds it. If a second source ever comes, for example a Nynorsk–English dictionary, it gets its own library file rather than a source field in each row: the row's shape stays the same, ordbokene's article numbers in the two dictionaries never collide, and the address's pair segment (`bm-en`, `nn-en`) names the file. Reusing the English of identical Bokmål and Nynorsk articles is left for a later measurement.

<a id="d21"></a>
### 21. Five small calls from the review (2026-09-19)

**Status:** ruled; **21a** reversed and amended (see below).

**21a** The interface language and the address. ordbokene.no's live behaviour: there the interface language is both stored and in the address, and the stored choice wins, so a shared link opens in the receiver's own interface language. Ordpar does the same: the interface language is stored on the device and wins; with nothing stored, the browser's language if Ordpar has it, otherwise English. **Amended:** with the stored language winning, an interface prefix in the address does nothing for a reader and, on a host without rewrite rules, would cost a full copy of every page per interface language. So the address carries the dictionary pair and then the article (`/bm-en/24627/hus`, `/bm-en/hus`), and switching the language changes the page's text in place. A search engine or a reader without JavaScript sees each pair's default language. The help, about and privacy pages are written per language and keep the language in their address; every article has one canonical address.

**21b** Homograph numerals follow ordbokene.no's rendering (a Roman numeral); the library already stores them that way.

**21c** The printed dictionary's inflection codes are skipped: they belong to the printed editions' apparatus. The data carries them (`inflection_class`), so a setting for them may be added later.

**21d** The inflection table keeps ordbokene.no's frames for verbs and participles ("å spise", "har spist", "spis!", "spist + noun", "den/det spiste + noun"); whether they are always on or a setting is settled in [31](#d31).

**21e** No "Cite" control at all, neither the citation line nor the download: the translations are not reviewed by academic experts, so the dictionary should not be cited as a source of truth. Copying the link and sharing stay. The About page says what to cite instead: Bokmålsordboka for the Norwegian; the English is Ordpar's own.

<a id="d22"></a>
### 22. ordbokene.no's English interface as the baseline for labels (2026-09-19)

**Status:** ruled; amended 19 October 2026; built and live.

ordbokene.no has an English interface, with labels such as "Etymology", "Senses and Example Sentences", "present perfect" and "definite form". Ruled: its English is the baseline for grammatical terms (word classes, tenses, genders, table headers) unless the project's translation conventions already fixed another term; the terms are taken from its English pages as shown.

**Amended:** the section labels follow ordbokene.no's English too ("Etymology", "Senses and Example Sentences", "Set phrases"), since the deck now follows the site rather than the other way round. A set phrase's own page and its search results show no word class, as on ordbokene.no.

**The divergence table.** Every deliberate difference from ordbokene.no is recorded in `docs/divergences.md`, with a column saying whether it could be of use to ordbokene. A decision that creates or ends a difference updates its row in the same change. Each entry of this log got a stable anchor (`#dN`) so the table can link to it.

**The number of suggestions.** ordbokene.no's suggestion list showed 20 rows in a list that scrolls. Ordpar switched to as many rows as fit the screen, without scrolling. Reversed: ordbokene's roomy list with a scroll bar may have been chosen for a reason such as accessibility, so Ordpar went back to 20 rows in a scrolling list, as ordbokene.no. One part was kept: on a phone the list's height stops above the on-screen keyboard and scrolls inside.

<a id="d23"></a>
### 23. The order of work: the site does not wait for the deck (2026-09-20)

**Status:** ruled.

Ruled: apart from the design of an article, the website and the deck are independent builds, and neither waits for the other. The one shared piece is the article itself: a flashcard and an article page are two views of the same data, so a change to an article's layout or labels is made once, for both.

<a id="d24"></a>
### 24. Foundation (a): a static page for every article (2026-09-20)

**Status:** ruled; built. The offline copy was built in [61](#d61) as whole pages in bundles; the headword's page amended by [117](#d117) (real word pages for translated words).

**(1)**, chosen: every article is written as a static HTML page when the site is built, by one renderer in Python, the same one as the deck's. Every article then has a real address that any search engine can index, and the page works with JavaScript switched off.

Refined within (1): one static page per article, at its id address only (the one address stable across updates of the source data); the headword's page (`/bm-en/rå`, listing all its articles) is drawn by the browser from the search index and left out of the sitemap. A line such as "3 more entries for *rå*" is added around the article, not inside it. The inflection table is shipped as data and drawn on the device, since prerendered tables would repeat a lot of markup on every page. The interface language is applied in the browser ([21](#d21)), so a new interface language costs one strings file, not another copy of every page.

<a id="d25"></a>
### 25. Foundation (b): searching with no server, from an index in the browser (2026-09-20)

**Status:** ruled; built; its size estimate revised by [39](#d39).

Ordpar has no server, so its lookups (the inflected-form panel, suggestions while typing, and the English index) had to run in the browser or in a function. **(1)**, chosen: an index in the browser, split by first letter into small files fetched when needed and cached, mapping each form to a list of article ids only. A line such as "definite plural of *hus*" is read from the article's own inflection data. Suggestions while typing and similar spellings are worked out on the device, so a misspelling is caught offline too. Letter case is kept in the index and ignored at search time (*PR* and *pr* differ). The English index is built the same way. One file for the whole index ((2)) would make a phone download all of it before its first answer. A server function ((3)) would mean a request per keystroke against a free tier's daily cap, and nothing offline.

<a id="d26"></a>
### 26. Foundation (c): the host, and a receiver of Ordpar's own (2026-09-20)

**Status:** ruled; the site on GitHub Pages since 20 October 2026 ([61](#d61)); the receiver built in [104](#d104), receiving correction reports since 5 November 2026 ([166](#d166)), its counting not yet switched on; hosting beyond GitHub Pages' size limit raised again in [156](#d156).

Two standing rules framed it: the domain's name servers stay with its registrar ([13](#d13)), and no cookies and no third party on the pages ([19](#d19)). The free hosts compared, from their own documentation (20 September 2026): Cloudflare Pages allowed at most 20,000 files per site and needed the name servers moved; GitHub Pages allowed 1 GB, had no documented file limit, but no functions or logs; Netlify's free plan stopped hard at its monthly allowance. No free host gave a count of visits per page without a script on the page, so [19](#d19)'s plan to count visits from the host's request log could not work.

Ruled, **(1)**: GitHub Pages for the site, with `ordpar.no` pointed at it from the registrar; a Cloudflare Worker on its free `workers.dev` address as the receiver, storing to Cloudflare's free database; and visits counted by a page-view event sent to that receiver, carrying the page's path and nothing else: no identifier, no cookie, no third party. The privacy page says so. The cost is nothing beyond the domain: the free tiers have no card on file, and their limits are far above the expected traffic. Cloudflare for everything would have meant moving the name servers.

<a id="d27"></a>
### 27. Foundation (d): the build from the translation library to the site (2026-09-20)

**Status:** ruled; built; **(1)**'s plain links amended by [34](#d34).

The project's translations live in a library of rows; the rest exist only in a local copy (a mirror) of the full Bokmålsordboka data. The build had to turn both into the site without ever overwriting translated English, and show an article as translated only when it is complete ([2](#d2)). **(1)**, chosen: a read-only build script under `ordpar/`, run against a named snapshot of the source data and a named version of the library, which never writes the library or the source files. For each article: if the library has the row and its English is complete, the translated page; otherwise the Norwegian page, derived from the source data. An incomplete row ships in Norwegian, and its English waits in the library. Cross-references are plain links to the target's page, since every article has one. The renderer is the deck's, with a site face ([23](#d23)). Both the site and the downloadable dataset are stamped with the snapshot date and the library version. Growing the library to all 94,000 rows ((2)) was rejected: the library's set of rows defines the translation work, and its checks assume that. A second, template-based renderer for Norwegian pages ((3)) was rejected as duplicate work. **Amended by [34](#d34):** a click on a cross-reference opens a small article on the page, with a setting to go to the target's page instead.

<a id="d29"></a>
### 29. Prototype (b): the abbreviation table comes with the source data (2026-09-20)

**Status:** ruled 25 September 2026; built.

Deriving an article's Norwegian needs a table that expands ordbokene's abbreviation codes. The library used a committed copy of that table, fetched at its own date, not the date of the source snapshot, so the two could drift apart. **(3)**, chosen: the table is snapshotted with the source data each time it is fetched, so it is dated with the articles. The site build reads that copy, falls back to the committed table only if it is absent, counts any code it cannot expand, and records which table it used. Warnings raised while deriving are counted in the build's report and never written into the project's review records. A reworded expansion is a change the missing-code count cannot see; the project's source-data tool lists those separately.

<a id="d30"></a>
### 30. Prototype (c): the deck's renderer used as it is; the site's rendering becomes the deck's (2026-09-20)

**Status:** ruled 25 September 2026; the site's half built; the deck's switch to the site's rendering scheduled in [49](#d49).

The site reuses the Anki deck's article renderer (`ordbok_gen.py`). **(1)**, chosen: the site imports the renderer as it is. Ruled with it: there is no split in the site's first version; the finished site rendering becomes the deck's article rendering too, and a separate deck version would be a new decision, made only if one is ever wanted. The reason is that each reader is in the best position to know how they want articles shown, so every display option is meant to be a setting, on the site and in the deck alike, rather than a fixed default for everyone. Copying the functions into `ordpar/` ((3)) was rejected as two renderers for one article design ([23](#d23)). When the deck changes over is [49](#d49).

<a id="d31"></a>
### 31. Prototype (d): the participle frames on by default, as a setting (2026-09-20)

**Status:** ruled 25 September 2026; built.

21d ([21](#d21)) kept ordbokene.no's frames in the inflection table, the small grey words beside a form (*å* spise, *har* spist, spis*!*, spist *+ noun*, *den/det* spiste *+ noun*). On ordbokene.no the setting for participle frames appeared unchecked but had no effect; on v1.ordbokene.no it was checked by default and worked. Ruled: **(2)**, follow ordbokene: on by default, with a setting to turn them off. Turning them off hides only the participle frames (*+ noun*, *den/det*); the others always show, as on ordbokene.no.

<a id="d32"></a>
### 32. Prototype (e): the translation status above the article, and the credit line (2026-09-20)

**Status:** ruled 17 October 2026; built; the change notice amended 20 October 2026; the credit line amended by [63](#d63).

ordbokene.no captions each article with its dictionary's name. Ordpar needs two things there: the translation status ([2](#d2)) and the attribution ([12](#d12)). CC BY 4.0 requires naming the licensor and the licence, so the attribution names the University of Bergen and the Language Council of Norway.

**The caption.** Ruled, **(1)**: a status only where it is news. An untranslated article carries "Norwegian only · not yet translated" above the headword and, where it belongs, a note that the article is shown as Bokmålsordboka has it, in Norwegian. A translated article carries no status, since a "translated" label on nine articles in ten would be noise.

**The attribution.** CC BY 4.0 allows attribution "in any reasonable manner", including a link to a page that carries it. Ruled: a one-line credit under every article, "Based on Bokmålsordboka (UiB and Språkrådet) · CC BY 4.0 · Ordpar is independent of both · About and licence", with the full text on the About page: the rights holders, the licence, what Ordpar changed, the not-affiliated statement and the no-warranty notice. A reader who arrives at an article from a search engine still sees the source and that Ordpar is independent. This amended [12](#d12). [63](#d63) later moved the credit into the footer of every page, linking to ordbokene.no in general rather than to the same article there.

**The change notice.** CC BY 4.0 asks a reuser to say that the material was modified; a general statement is enough. The About page's "What Ordpar has changed" now also says that Ordpar corrects some clear errors in the Norwegian: spelling and typography, and cross-references that point to the wrong sense or homograph.

<a id="d33"></a>
### 33. Prototype (f): the homograph numeral read out as "homograph 2" (2026-09-20)

**Status:** ruled 17 October 2026; built.

ordbokene.no shows a Roman numeral beside a homograph's headword, with the plain digit for screen readers (21b, [21](#d21)). A bare "2" read out after a headword says little. **(1)**, chosen: the numeral stays visible but is hidden from screen readers, and a visually hidden "homograph 2" is read instead ("bru, homograph 2"). This is a deliberate difference from ordbokene.no's bare digit. The Anki deck's card markup is unchanged.

<a id="d34"></a>
### 34. Prototype (g): a cross-reference opens a small article on the page (2026-09-20)

**Status:** ruled 17 October 2026; built; the small articles' inlining reversed by [80](#d80); the link's place amended by [54](#d54).

[27](#d27) made every cross-reference a plain link to the target's page. A click should open a small article on the page, as in the deck, with a setting to go to the target's page; an untranslated target gets a small article too, in Norwegian. A target can have several small articles (one per cited sense), and the header of each carries the English the citing link uses, so a small article depends on the citing article, not only on the target. **(1)**, chosen: every small article rendered at build time by the deck's renderer and placed in the page, in English where the target is translated and in Norwegian otherwise. This needed no JavaScript for the click and came offline for free; the cost was page size. The setting: "Cross-references: open as a small article on the page / open the full article page", the small article the default. [80](#d80) later changed this: small articles are made from the target's own page and fetched when needed.

<a id="d36"></a>
### 36. The headword line grouped by gender, as ordbokene.no does (2026-09-20)

**Status:** ruled 17 October 2026; built on the site; the deck follows when it switches to the site's rendering ([49](#d49)).

On ordbokene.no, a word with spelling variants of different genders shows several headword lines, each with its own word class and gender (*selvfordypelse*: three lines). The deck put every form on one line with one combined label, so *anskaffelse, anskaffing* read "noun (masculine or feminine)" though *anskaffelse* is masculine only: a lexicographic error, not just a layout difference. **(1)**, chosen: group the headword line by each form's tags, each group with its own word-class line, on the site now; the deck follows. The data often lists the feminine first, and ordbokene.no follows the data. Ruled: the genders in the data's order, as ordbokene.no. Checked against ordbokene.no's English pages: *bru, bro* "noun (feminine or masculine)", *adresse* "feminine or masculine", *anskaffelse* two lines, *selvfordypelse* three; Ordpar's pages match on all four.

<a id="d37"></a>
### 37. Both languages on a translated page, and where a cross-reference's control lives (2026-09-20)

**Status:** built; the default amended by [52](#d52), the order of the two lines by [53](#d53), and where the link lives by [54](#d54).

The first prototype showed a translated article in both languages: every sense, subsense, set phrase sense, etymology and example in Norwegian with the English beneath. A cross-reference then appeared in both halves, and each occurrence carried its own small article, so the small article was included twice. The definition lines (senses, subsenses, set phrase senses and the etymology) show the English by default; the Norwegian definition is revealed per line by a click, or everywhere by a device setting (`nodef`, default hidden). The English line carries the two-tier control (hover peek, click for the small article); the Norwegian line is plain text, its references plain words, so each small article is included once. Examples were unchanged: Norwegian, with the English visible beneath.

<a id="d38"></a>
### 38. The labels of the learner block (2026-09-20)

**Status:** dropped (the learner block removed from the site, 17 October 2026).

The prototype put the summary's `note` and `trap` behind a closed control after the article, labelled "For learners", with "Watch out" for the trap. The learner block is dropped from the site. The reasons: the notes and traps were to be revised first, and they are not dictionary content as such. If they return after that revision, they are off by default; whether they return at all is decided then. The summary gloss in the article head stays. The block's code and its two strings were removed.

<a id="d39"></a>
### 39. The first search's download, and how the index was cut (2026-09-20)

**Status:** built (18 October 2026), with the similar-words ranking that followed.

The search index was planned at about 50 KB before the first lookup ([25](#d25)). As built it was far larger: a first search fetched its letter's shard, the list of translated articles and the full similar-headwords list. The similar-headwords list is split by first letter, and the five big letters (*s*, *k*, *f*, *t*, *b*) by their first two characters. The list is still needed after a successful search, since similar words show under a hit too, as on ordbokene.no; but the results render first and the list is fetched after, so the cost is data, not delay. Set phrases stay in the list. 325 set phrases carried the source's alternation brackets (`[få|sette] ræva i gir`), which neither a search nor a suggestion could reach; each bracketed alternative now expands into its variants, and the variant is what is shown. This closes [41](#d41) (b).

A follow-up changed the similar-words ranking, which had used fixed limits (edit distance up to 3, length within 2) that were strict on long phrases and loose on short words. Now one edit is allowed per three characters (at least one); a query of two or more words may also match word by word, at least two words shared in order. Word matches rank first, then distance, length and alphabet; up to five are shown, and nothing that qualifies neither way. Ordbokene.no's own ranking could not be seen, so ours is designed, not copied. Phrase suggestions that share only common words (*ta … på*) were kept as built.

<a id="d40"></a>
### 40. The inflection table's smaller questions (2026-09-20)

**Status:** built (18–19 October 2026).

Before the ruling, ordbokene.no's tables were compared with ours on 17 words, and what they showed was written down in our own words; our renderer is written from that description and tested against the output. Ruled:

- **(a)** The passive forms (*spises*) are left out, as on ordbokene.no.
- **(b)** A comparable adverb (*ofte*) keeps "positive" as a column header, as ordbokene.no prints it, and has no "degrees of comparison" header over it.
- **(c)** S-passive verbs (*finnes*, *aldres*) show no imperative, as on ordbokene.no; elsewhere an absent form still counts as a difference between paradigms.
- **(d)** Variants inside one cell are sorted alphabetically in Norwegian collation (*lita, liten*), as on ordbokene.no, not in the data's order.
- **(e)** Abbreviations tagged with a gender, and ordbokene's two mis-tagged entries, render by their cells: the cells are the truth.
- **(f)** The header colour: answered by [43](#d43).
- **(g)** Two paradigms are joined into one cell only when they differ within one of 14 kinds of cell, as ordbokene.no does; otherwise they stay two rows, the shared cells spanning both.

Two further differences found in the build followed ordbokene.no too: **question 9**, every variant of a joined cell carries its own frame (*avvæpn! avvæpne!*); **question 10**, the narrow layout is one table per lemma, its sections stacked under a shared label column. Of the narrow headers, "indefinite" and "definite" without "form" and the break in "masculine/ feminine" follow ordbokene.no; the visually hidden name in a lone section's row header is kept, for screen readers.

<a id="d41"></a>
### 41. The search's smaller questions (2026-09-20)

**Status:** built (18 October 2026).

- **(a)** Accent folding: what is typed without accents matches headwords with them (*en* finds *én*, *a la carte* finds *à la carte*), one way only, as ordbokene.no; the display keeps the accents, and *é*-initial words are filed with *e*.
- **(b)** The similar-headwords list by letter: closed by [39](#d39).
- **(c)** A string that is both a headword and an inflected form (*hus*): the headword first, then "is an inflected form of".
- **(d)** A homograph on the results page is named by its numeral and word class; the summary gloss to be added later (it came with the list view's rows, [59](#d59)).
- **(e)** A link's text names all the headword's spellings (*bru / bro*, at most three).
- **(f)** Set phrases among the suggestions: ordbokene.no ranks them like any headword, as ours already did.
- **(g)** No "translated only" filter; each suggestion's tag answers that.
- **(h)** No failed-search log is kept until a receiver exists.
- **(i)** Which build owns the landing page: the article build in the end, the search build's placeholder until then.

<a id="d42"></a>
### 42. The summary gloss in the article head (2026-09-20)

**Status:** built (20 September 2026); the sense marks wait on a sense tag for each gloss item.

Ruled: the gloss goes in the article head, under the word-class line, visible by default. It keeps the authors' order, by salience, not by sense, since ordbokene's sense 1 is often the older meaning (*bli* 1 is *to remain*; *to become* is far commoner). Each item is to carry its sense number as a small superscript linking to that sense (*to become ² · to stay, to remain ¹ · to be (forming the passive) ³*), so the head is also a table of contents. Those marks need a sense tag per gloss item, which the data does not yet hold; until then the items show unmarked. An item covering every sense, or none, carries no mark.

<a id="d43"></a>
### 43. The inflection table behind an "Inflection" button, in neutral grey (2026-09-24)

**Status:** built (24 September 2026).

Ruled and built: **(1)** the header cells take ordbokene's neutral grey (`#f1f1f1`) and the page's text colour, with neutral borders and a light wash at night, answering [40](#d40) (f); **(2)** the table sits behind an "Inflection" pill with a chevron, closed by default, and the pill appears only when a table was rendered, so a word without inflection, or a reader without JavaScript, sees no empty button; **(3)** a device setting, "Inflection tables", opens it always. Amended: the table may grow wider than the text column, up to the window's edge, so a cell wraps only where the window has no room.

<a id="d44"></a>
### 44. The narrow inflection table: no participle frames, a lone section as a heading row (2026-09-24)

**Status:** built (24 September 2026).

At phone width ordbokene.no prints the participle cells as bare forms, while its verb rows keep *å*, *har* and *!*; at full width the frames are all there. It also puts a lone section such as *present participle* above its row rather than to its left. In the narrow layout the participle table fills its cells without frames, and every lone section (*present participle*; the adjective and determiner *plural*) is a heading row, its row header empty to the eye but named for a screen reader. Narrow row headers may wrap at a space, with *masculine /* kept together over *feminine*. The wide layout is unchanged. A verb with six participle variants still overflows a phone in both dictionaries and scrolls sideways.

<a id="d45"></a>
### 45. The order of rows inside one lemma of the inflection table (2026-09-24)

**Status:** built; amended 2 November 2026.

On *trøtte, trette* III ordbokene.no ordered the paradigms *tretta, trettet, trøtta, trøttet*. Ruled: "Ours should follow the same ordering as theirs." The rows were sorted by gender, then lemma, then their forms column by column, in Norwegian collation.

Amended, with the same aim: a fresh comparison of the rendered tables found that most remaining differences from ordbokene.no were row order. Ordbokene.no orders a lemma's rows, and the lemmas, by each cell's first form, in a collation where æ, ø and å sort as *ae*, *o* and *a*, the accent only breaking ties. Ours now does the same (`orderCollate` in `ordpar/site/inflection.js`); the forms inside one joined cell keep Norwegian collation, as on ordbokene.no. After the change every row-order difference was gone.

<a id="d46"></a>
### 46. Articles ordbokene no longer lists: pages and search (2026-09-25)

**Status:** built (18 October 2026); whether 23 set phrases that our copy of the source never held should have pages is open.

An article that leaves ordbokene's word list may still be served at its address. Ordbokene.no then leaves it out of search but still serves it: *krone* 32274 was served but not found by a search for *krone*. An article we have already translated should stay, or its English would vanish from the dictionary. Ruled: search (the index, suggestions, similar words, the random word) covers the listed articles plus every unlisted article we have translated, except where a listed article with the same headword is translated too, since that one carries the English. Those kept articles keep their pages, even when ordbokene no longer serves them; their link to the source then points at the parent article that includes them. Every other unlisted article has a page only while ordbokene serves it, and is never in search. When a later update moves our English to a new article, the old one leaves search by itself. The same-headword match is a heuristic: an article merged under another headword is not caught.

<a id="d47"></a>
### 47. The compound line's label in lower case (2026-09-25)

**Status:** built; amended by [151](#d151).

Every line of an article starts with a small letter, as on ordbokene.no, which prints *som etterledd i ord som …*; but the compound line began "Used as a suffix in:". The label is stored in the data, written by the deriver. The label is lowercased by the site's own code when the page is rendered (`ordpar/sitegen/article.py` and `ordpar/sitegen/face.py`), not in the renderer the deck shares, so the deck's output is untouched and it takes the change at its switch-over ([49](#d49)). [151](#d151) later had the deriver store the labels in lower case, so this step now only guards data derived before.

<a id="d48"></a>
### 48. The article renderer moves into `ordpar/` (2026-09-25)

**Status:** ruled, not built; the renderer is still at the repository's root.

Since the finished site's rendering is to become the deck's ([30](#d30)), the article renderer (`ordbok_gen.py`, with `scripts/mini.py` and the parts of `scripts/markup.py` it uses) moves under `ordpar/`, the folder that becomes the public repository, and the deck's scripts import it from there. The move is a multi-file port with its tests.

<a id="d49"></a>
### 49. When the deck switches to the site's rendering (2026-09-25)

**Status:** done: the deck switched to the site's rendering with its release of 25 October 2026 ([131](#d131)); amended by [111](#d111) and [131](#d131); the renderer's move ([48](#d48)) not yet made.

The finished site is the deck's baseline. Until the switch-over, decisions are made for the site only, and the deck inherits them then. One gap: some of what the site shows comes from the data its build reads, not from the renderer (the grouping of a headword's spellings and genders, [36](#d36)). Ruled: the library carries that order itself, so a row says what the page shows and the library, published as a dataset, needs no other source to give *bru*'s genders right (each row's headword groups, `scripts/headwords.py`). The one exception first set, a reveal on the examples' English in the deck, became a site setting too ([111](#d111)); the released deck shows the examples in both languages by default, as the site does ([131](#d131)). Needed at the switch-over: the renderer moved ([48](#d48)), the small articles written into the card, and the library carrying the order.

<a id="d52"></a>
### 52. The Norwegian definitions shown by default (2026-10-17)

**Status:** built (17 October 2026); amended by [54](#d54).

Under [37](#d37) the Norwegian definition sat behind a per-line "Show Norwegian" control. Ruled: "the Norwegian definitions should be shown by default." It is built so that the default needs no script: every Norwegian line shows unless the page carries a class set from the stored choice. Amended during [54](#d54): the setting becomes three-way, *English*, *Norwegian and English* (the default) and *Norwegian, the English behind a reveal*; hiding the Norwegian goes. Built with [54](#d54).

<a id="d53"></a>
### 53. Norwegian first in a definition's pair of lines (2026-10-17)

**Status:** built (18 October 2026); amended by [54](#d54) and [87](#d87).

With the Norwegian shown by default ([52](#d52)), each definition read English first and Norwegian beneath, while each example read the other way. One order for every pair on the page, the source then its translation, so the page reads as Bokmålsordboka's article with our English under each line; the summary gloss in the head already gives the quick English. Norwegian first in the main style, the English beneath it in the translation style, for definitions, set phrase definitions and the etymology. When the Norwegian is hidden, the English leads alone, as before. This changed the order set in [37](#d37). [87](#d87) later made the English line the emphasized one.

<a id="d54"></a>
### 54. A cross-reference's link on the leading line, and three settings (2026-10-18)

**Status:** built (18 October 2026); amended by [87](#d87).

With the Norwegian line now first ([53](#d53)), the link still sat on the English line beneath. Each reference is one control, and each control includes its own small article, so two controls would double their share of the page. The small article's layout is a setting of its own and by default mirrors the article's; the hover peek stays, as a setting, on by default, since it also tells the reader which word a link belongs to; and the definitions setting becomes three-way, with the Norwegian no longer hideable ([52](#d52)). Ruled: the link lives on the line that leads. While both lines show it is on the Norwegian word, and the English words are not links; when the English stands alone, the page script moves the control to the English word, which keeps its own peek. The small article opens directly below the word that carries the link and has no reveal button. Settings: definitions `en` | `both` (default) | `no`; small article `article` (default, same as the article) | `en` | `both`; peek `on` (default) | `off`. Under the reveal setting, the headword's summary gloss stays visible. This moved the link from where [34](#d34) and [37](#d37) had put it. [87](#d87) later moved the links to whichever line is emphasized.

<a id="d55"></a>
### 55. Spelling suggestions past the first letter (2026-10-18)

**Status:** built ((1) and (2) on 19 October 2026; the National Library's book counts since 20 October 2026); (3) and (4) noted for later; a check on register-inflated counts ruled, not built.

Similar words were sought only among headwords sharing the query's first letter, so a first-letter typo (*vus* for *hus*) or a dialect spelling (*kordan*) found nothing.

- **(1)** Ruled: our own table of Norwegian spelling-variation rules applied to the query (*hv/k/v* at the start, *kj/sj/skj*, *gj/hj/j*, *aa/å*, single and double consonants and more), each rewrite looked up like a query.
- **(2)** Ruled: a second similar-words index without the first letter, limited in number, preferring words that share the first letter and commoner words, so that *vus* offers *hus* first.
- **(3)** Learning corrections from real searches: noted for later.
- **(4)** Using the Nynorsk dictionary (*kva* → *hva*): the two dictionaries do not link these pairs in the data, so noted for later.

The frequency signal needed an openly licensed source; share-alike and non-commercial lists were ruled out. Språkbanken's CC0 newspaper n-gram list was used first; the National Library's 2026 book n-grams (CC0, Bokmål books since 1990) agreed better with independent lists of common words, and the book counts alone were ruled: scaled to bands, single characters and abbreviations given low bands, a short list of fixes. Newspapers over-count words such as *representant*. Each distinct form counts once per article, a form shared with another article counts only as an article's own headword, and a suggestion takes its best article's band. A verb's present tense that is also an agent noun (*skriver*) counts for the verb too. Our own corrections live in `ordpar/freq-overrides.tsv`. Also ruled, not built: a hand-judged check on the commonest 3,000 words for counts inflated by the source's register (for books, books against newspapers, from the National Library's two 2026 files).

Two ranking refinements were ruled: the frequency band comes before "same first letter" (*vus* → hus, vis, jus, mus, rus), and a difference in capital letters from the query as typed is a tie-breaker smaller than any edit (*us* → ut first; *US* → UT first). Ordbokene.no showed its similar words alphabetically (*ike* gives *alsike, anrike, avvike …*); ours by distance, then frequency (*ike* gives *ikke, uke, like …*).

<a id="d56"></a>
### 56. Dialect spellings in search: *kæm*, *dæ*, *mæ*, *kor* (2026-10-19)

**Status:** built, 19 October 2026; the *-a ↔ -en* spelling rule dropped the same day.

The spelling rules of [55](#d55) already led *kem*, *koffor*, *ka* and *ikkje* to *hvem*, *hvorfor*, *hva* and *ikke*. Three gaps remained: the dialect *æ* for *eg*, the *æ* for *e* inside a word, and a dialect form that is itself a headword (*kor*, choir), where no rule ran because the search was a hit.

**(1)** Two spelling rules were added: a word-final *æ ↔ eg* (*dæ → deg*, *mæ → meg*, *sæ → seg*, *jæ → jeg*) and *æ ↔ e* inside a word (*æple → eple*). Two rules may now chain (*kæm → kem → hvem*), capped at two so the candidates stay few; the second rule never rewrites what the first wrote.

**(2)** Widened: the similar words under a hit are built exactly as on a miss, with the same sources, limits and ranking; a query still never lists itself. So *kor* now offers *hvor*. ordbokene.no's lists behaved the same on hits and misses, ordered alphabetically, so this is not a separate divergence; the difference is our ranking (distance, how common a word is, case, spelling rules) where ordbokene.no orders alphabetically. The cost: a hit downloads what a miss does, after its results have shown.

The existing *-a ↔ -en* rule gave odd lists on short hits (*en* → *a*, *à*, *A*). It was dropped: headwords are base forms, so the rule's one use was offering an inflected form, and plain edit distance already reaches the base form (*hesta* → *hest*). Tested by `ordpar/tests/test_ordpar_dialect56.py`.

<a id="d57"></a>
### 57. The full build's failures: where the fixes for seven defective articles live (2026-10-19)

**Status:** built, 19 October 2026.

The full build still failed on seven articles, each stopped by the shared deriver (`scripts/derive.py`, `scripts/postags.py`), which the flashcard deck uses too. Two were gaps in our deriver: a superscript minus (*piko-*, 10⁻¹²) and a superscript *x* (*eksponentialfunksjon*, eˣ). Five were mis-tags in the source data: *jern- og metallindustri* had a gender but no noun tag, and four fixed expressions carried the word class `false` (ordbokene.no printed it as such).

Ruled: fix the shared deriver rather than patch the articles on the site's side. These are crash fixes, not new conventions, and the deck would fail on the same articles if it ever reached them. The deriver gains the two superscripts; a lone `false` tag on an expression reads as a fixed expression, and a lone gender tag as a noun of that gender. Every other unknown tag set is still an error.

The same build found two faults fixed in the site's own code, both following ordbokene.no. **78 fixed expressions** were missing from their parents' pages because their own articles were absent from the source list: 4 now derive on their own, and the other 74 are built from the copy the parent article embeds (shown on the parent's page only, with no page or search entry of their own). And **duplicate ids** on 486 pages are gone: an embedded expression's sense anchors are now `x<id>-defN`, the parent's stay as they were.

<a id="d58"></a>
### 58. Untranslated fixed expressions on translated pages (2026-10-19)

**Status:** built, 19 October 2026, as amended the same day; translating the phrases waits for their articles' own frequency rank (ruled 21 October 2026).

Once [57](#d57) built the missing fixed expressions, ten of them sat on translated pages with no English. Looking further found 623 more: set phrases cited by translated articles that had no translation of their own, until then shown with an "unauthored" marker. They hang off articles translated as small articles, whose own set phrases were never in scope. The rule of [2](#d2) is that nothing is shown half-translated.

Amended: the unit is the article, embedded or not, so a set phrase is shown either fully translated or in Norwegian alone. On a translated page:

- the translated set phrases come first in their usual order, then the untranslated ones in Norwegian, under a small heading "Not yet translated" (a deliberate divergence from ordbokene.no's order);
- where none is translated, a short note at the top of the block replaces the heading;
- under the setting "English only" the untranslated set phrases are hidden, heading and note with them.

A page in Norwegian is unchanged.

<a id="d59"></a>
### 59. The search results: full articles by default, the list view a setting (2026-10-19)

**Status:** built, 19 October 2026; the default view changed by [71](#d71) and [158](#d158); the suggestions (item 11) amended by [82](#d82) and [86](#d86); the "translated" tag (5) dropped by [137](#d137); the "Article page" link (2) dropped by [168](#d168).

Ruled, as ordbokene.no: every hit's article is shown in full in the results, one after another, behaving as on its own page. A setting, "List view in search", shows one row per hit instead (headword, homograph, word class, the translated or *Norwegian only* tag, a one-line snippet); a row opens the full article in place and closes again, several at once. The article's own page stays its canonical address.

Five follow-ups, measured against ordbokene.no:

- **(1)** Homographs in ordbokene.no's results order: the verbs first, in homograph-number order, then every other homograph in number order.
- **(2)** Copy link, Share and an "Article page" link under each full result and each opened row; no Cite (21e, [21](#d21)).
- **(3)** An opened list row shows its inflection table open, as ordbokene.no's does.
- **(4)** The snippet is our summary gloss (else the first English sense; for an untranslated article, the first Norwegian definition), a deliberate divergence.
- **(5)** The translated / *Norwegian only* tag on each row is kept, also a divergence.

Further items:

- **item 6** A gloss's units are joined by " · ", in the snippet and the page description.
- **item 7** The summary gloss on an article stands out (semibold, slightly larger); the list-view snippet stays at normal weight.
- **item 8** The line "'fly' is a headword" goes; the heading is the dictionary's name, "Bokmål–English dictionary", and the number of entries.
- **item 9** The "inflected form of" rows carry the snippet too, a divergence (ordbokene.no lists bare headwords).
- **item 10** A trailing space asks for set phrases: "fy " suggests *fy*, then *fy faen*, *fy flate* … ordbokene.no's site dropped the space; a deliberate divergence.
- **item 11** A suggestion for one article shows its word class in faded italic after the word, and on the right the first unit of its summary gloss, or "Norwegian only"; a form with several articles shows "N articles". A set phrase shows its gloss's first unit, else its first English set-phrase box, else nothing.
- **item 12** In the results, translated articles come before untranslated ones, each group in item (1)'s order; in the full view, a "Not yet translated" heading over the second group.
- **item 13** In the suggestions, the exact match first, then translated headwords, then *Norwegian only* headwords, then set phrases.
- **item 14** Within those groups, the commoner headwords first, by the frequency bands of [55](#d55); ties keep the earlier order.
- **item 15** In a small article, the headword link covers its suffix, `gå (6)` rather than `gå`; a site rule the deck takes over at the switch ([49](#d49)).
- **item 16** A third list-view value: the list only when the search has several articles.

In a result, a wide inflection table that does not fit the card switches to the narrow layout, measured, rather than scrolling sideways. Tested by `ordpar/tests/test_ordpar_results59.py`.

<a id="d60"></a>
### 60. History and favourites, kept on the device (2026-10-19)

**Status:** built, 19 October 2026; history changed to searches only and rebuilt the same day; export as `.txt` ruled and built 20 October 2026.

ordbokene.no has neither, so both are a deliberate divergence. Ruled:

1. **Kept on the device, no account**: in the browser's storage, as the settings are ([4](#d4)); nothing is sent anywhere.
2. **History records searches only**: the search box submitted, a suggestion chosen, a similar word chosen, a recent search re-run, recorded as typed and only when it found something. Articles opened by a link are not recorded (the browser's own history keeps them). A repeat moves to the top; about 100 are kept. (First built to record every article a search showed; changed the same day, since one search for *fly* added five entries.)
3. **item 3** With the search box empty and focused, the recent searches show under it; a History page lists them all with a "Clear" button. Each row looks like a suggestion and runs the search again.
4. **item 4** A heart button on each article (its page, each full result, an opened row) saves it to favourites; it is labelled "Favourite" and shows its state as pressed or not.
5. A Favourites page, linked from the header, with one removable row per saved article.
6. **item 6** Export: one small file with the settings, history and favourites, saved as `ordpar-<date>.txt` holding JSON, to share more easily across apps. Where the browser can share a file, a share button sends it.
7. **item 7** Import merges: favourites added, history combined by time, settings from the file; a file with one bad entry is refused whole. It reads `.txt` and `.json` alike.

Tested by `ordpar/tests/test_ordpar_history60.py`.

<a id="d61"></a>
### 61. An offline copy: the installable web app, early (2026-10-19)

**Status:** built; live at `https://ordpar.no` since 20 October 2026; the `noindex` of (2) lifted on the translated pages by [128](#d128).

The request: a copy of the dictionary that works offline on a phone and a computer, and opens from an Android home-screen button. A single HTML file was tried first. A test file holding the whole dictionary (about 25 MB) opened and stored settings, but on Android a home-screen shortcut to a local file stopped working after a restart. **(1)** Ruled: the installable web app planned for the site, built early, since `ordpar.no` would serve it at launch anyway.

**(2)** Ruled: the copy is the real site at `ordpar.no` on GitHub Pages ([26](#d26)), unlisted until launch (every page `noindex`, nothing linking to it), published from a public repository holding only the built site. **(3)** Ruled: offline, the built pages are stored whole, 2,000 to a compressed bundle, served by a service worker after an explicit download in Settings. The whole dictionary goes offline, untranslated articles included. The pages' version stamps are blanked inside the bundles and restored when served, so a change to a script does not force a new download; only a change to an article or the page frame does. An update fetches only the changed bundles.

**step 2** The deployment: `ordpar/deploy.py` pushes the built site as one snapshot commit to the public repository ordpar/ordpar.github.io on GitHub, so it never grows a history.

The icon is the project's own, kept distinct from ordbokene.no's white "O" on maroon: a white patch with a maroon "Ord" and a pink patch with "Par", like patches on a cow, on a maroon ground.

The published scripts and stylesheets ship without comments, stripped by a small build step of our own, no third-party minifier (`ordpar/sitegen/slim.py`). The download comes in checked packs and resumes where it stopped. Tested by `ordpar/tests/test_ordpar_offline61.py`.

<a id="d62"></a>
### 62. Search logging on the English site, reopening 19 for the spelling help (2026-10-19)

**Status:** ruled 20 October 2026; built with the receiver of [104](#d104) on 23 October 2026, not yet switched on.

[19](#d19) had ruled that the English site logs no searches, since every word will be translated anyway. But on the English site a miss is mostly a spelling or a form the search did not understand, which [55](#d55) and [56](#d56) tuned by hand from guessed cases. Logging is the only way the spelling help and the suggestions can learn from real readers. Ruled: log, through our own receiver ([26](#d26)), one event per search sent or choice made, never per keystroke:

- **(1)** a miss, with the similar word chosen and its position, or none;
- **(2)** a suggestion chosen while typing: the text typed so far, the word chosen, its position;
- **(3)** for searches that found something, counts per query only.

No session, cookie or identifier; no IP address stored. A query with digits or over about 40 characters is dropped. Raw lines are kept about 90 days; after that only queries seen at least three times are kept, as counts, since a free-text query can itself identify someone. Searches made offline are not logged, and the privacy page says that logging happens only online. This amends [19](#d19).

<a id="d63"></a>
### 63. One header and one footer on every page, and the article in a card (2026-10-19)

**Status:** built, live since 20 October 2026 (the site's first deploy); partly reopened by [106](#d106); the optional ordbokene typography carried into [75](#d75).

The article page had a plain search form without suggestions and a different header from the search page. ordbokene.no uses one header for both, so every page now has the search page's header, an "Article view" line with "← Home", and the article in a card with its controls at the foot. One footer on every page carries the credit and the links Home · Settings · Favourites · History · About and licence, with no logos of the University of Bergen or the Language Council, since Ordpar is independent of both. The credit links ordbokene.no in general and the About page carries the full attribution, which CC BY 4.0 allows "in any reasonable manner"; a per-article source link was dropped as bloat that leads to no further content. Settings moved to their own page, `/settings/`, in sections.

**Identity.** Following ordbokene's layout closely is fine, but the default colour, the name and icon, the independence statement, the English and the typography stay ours. Our accent had been ordbokene's exact maroon, so the default became Wine (`#6b0f2e`); Oxblood and "ordbokene.no's maroon" are optional schemes, the latter named for its source, with ordbokene's black-and-white night mode. Cross-reference links follow ordbokene's style (upright, the text's colour, a solid underline in the accent), replacing an italic, coloured style inherited from the Anki deck and never ruled for the site: an inherited convention is a divergence until ruled. The headword is sans at weight 600. An optional ordbokene typography was agreed in principle, off by default and named for its source.

An "under development" note sits in the footer, tied to the same pre-launch switch as `noindex` ([61](#d61)), so launch removes both in one rebuild.

**The About page** is one source text, `ordpar/about.md`, rendered as the About page and as the README of the repository that hosts the site, so the two cannot drift; the README carries no feedback link, since the form is for the site's readers. Its figures are measured by the build (`ordpar/site_stats.py`), never typed. Ruled:

- **(a)** The translated share is given by running words, the easiest for a reader to grasp.
- **(b)** The page counts the example sentences Ordpar added where a sense had none, and the articles they are in, and names their mark (a small raised "+", whose hover text on the site reads "Example added by Ordpar (not from Bokmålsordboka)").
- **(c)** No claim on the design, which is closely modelled on ordbokene's; only the English is licensed.
- **(d)** No "©": the English is written with AI (Claude, by Anthropic) under Robin's direction and review, and whatever rights exist in it are given under CC BY 4.0, as the Norwegian (the notice's wording since 13 November 2026: whether text written by AI carries any right is an open question). Attribution was kept over CC0 because credit may help the project reach more readers.
- **(e)** The credit for the English goes to Ordpar (ordpar.no), the Norwegian to Bokmålsordboka.
- **(f)** The warranty sentence links section 5 of the licence.
- **(g)** The aim: the whole of Bokmålsordboka in English, then other languages.
- **(h)** The article count covers every article ordbokene.no's search shows (statuses 2–6, not status 1 or none).
- **(i)** A thanks to the KELLY list, from which the first selection of articles came.

The page also splits translated articles into complete ones and those still without a summary gloss, a clause the build drops when none remain. Tested by `ordpar/tests/test_ordpar_chrome63.py` and `ordpar/tests/test_ordpar_about63.py`.

<a id="d64"></a>
### 64. The site's library: a committed copy, updated only on purpose (2026-10-20)

**Status:** ruled; updated since only by recorded merges.

The site read its own branch's copy of the library file, while the most up-to-date library was in a separate working branch, unmerged. Ruled: that file is copied over the site's own, byte for byte, and committed with a message naming its source branch and commit. The site builds from that file only, and any later update of the library is a deliberate copy or merge, recorded in this log, so the published dictionary changes only on purpose. Because the content is identical, git stores it once, and a later merge of either branch meets the same text rather than a conflict.

<a id="d65"></a>
### 65. Each language pair is a dictionary of its own (2026-10-20)

**Status:** ruled; where several pairs will be hosted is open.

The English site was about 871 MB against GitHub Pages' 1 GB limit, and a second pair (Polish, for instance) as its own pages would add about as much again. One way round that was a single page per article carrying every translation. Ruled against it: the Bokmål–Polish dictionary will be a different dictionary from the Bokmål–English one, and is treated as such, with its own pages and addresses (`/bm-en/<id>/`, `/bm-pl/<id>/`), as the address scheme already allows. The site stays one site with one Norwegian source, holding several dictionaries.

Where the pairs are hosted is left until a second pair starts; a move of host keeps the addresses.

<a id="d67"></a>
### 67. Random word: words only, and only fully authored articles (2026-10-20)

**Status:** built, live since 20 October 2026; amended by [115](#d115), which keeps its pool rule.

Random word drew from every translated article, set phrases included, and could land on an article whose senses were translated but which had no summary gloss. Ruled: its pool is the translated articles that are not set phrases **and** have a summary gloss ([42](#d42)); *båtdekk*, translated but without a summary gloss, is out. Random word should show actual words, as ordbokene's does (Robin's observation, not re-checked), and only articles that are complete. The pool is a file of its own written by `ordpar/build_index.py`, also in the offline index. [115](#d115) later made Random word open a headword search instead of an article, drawing a headword when the first article its search shows meets this rule.

<a id="d68"></a>
### 68. The app's install offer: once per device, then a button in Settings (2026-10-20)

**Status:** built 20 October 2026; live since 21 October 2026.

Chrome offers to install the site as an app. Ruled: the site shows its own small install offer once per device, then an **Install app** button in Settings → Offline, beside the offline download, for any time after. A one-time offer is useful because readers may never discover the feature otherwise. "Install" or "No thanks" ends the offer for good; an offer left unanswered (the page closed or left) shows once more on a later visit, then never again. It is remembered on the device, so clearing the site's data shows it again.

A one-line "Install Ordpar as an app" hint in the footer, on phones only and never inside the installed app, leads to the same Settings line, and it stays after the offer has been seen. The proposal's four questions were answered:

- **(1)** The offer appears wherever Chrome allows it, computers included.
- **(2)** On iPhones there is no bar, only the footer hint and the Settings line.
- **(3)** The manifest lists the site's own web app under `related_applications`, so a browser tab can tell the app is installed.
- **(4)** The wording as proposed.

Everything is written by script, so no page changes. Built in `ordpar/site/install.js`; specified in `ordpar/docs/offline-app.md`; tested by `ordpar/tests/test_ordpar_install68.py`.

<a id="d69"></a>
### 69. The small article stays inside the window (2026-10-20)

**Status:** built 20 October 2026; live since 21 October 2026.

A small article opened from a cross-reference near the right edge of the screen could run off it. Ruled: it never extends past the window's right edge, nor its left; where it would, it moves left to sit flush with the right side, ending 8 px short so its border and shadow stay whole. Vertically it still opens just below the cross-reference clicked. It is placed again after a resize or rotation, and its width is capped at the window less 1rem. On a computer the hover peek is fixed the same way: moved left where it would pass the right edge, its arrow shifted back so it still points at the word. Tested by `ordpar/tests/test_ordpar_mini69_70.py`.

<a id="d70"></a>
### 70. The small article's body formatted as the main article's (2026-10-20)

**Status:** built 20 October 2026; live since 21 October 2026.

The small article still had the Anki deck's look: coloured, italic links, and on phones each link's hover text printed after it. Ruled: its body takes the main article's formatting, with the same link style ([63](#d63)) and the same handling of hover text on a touch screen. Done in the site's stylesheet only, so no page changes. The small article keeps a few things of its own as a pop-up: its smaller text, width, padding and heading. Tested by `ordpar/tests/test_ordpar_mini69_70.py`.

<a id="d71"></a>
### 71. List view by default when there are several articles (2026-10-20)

**Status:** built 20 October 2026; live since 21 October 2026; the default changed again by [158](#d158).

The setting *List view in search* defaulted to off, as on ordbokene.no ([59](#d59)). Ruled: the default becomes "only when there are several articles". A search finding one article shows it whole; a search finding several shows the list, whose entries open in place. A reader who has chosen a value keeps it. The reason: when a search finds many articles, or some are very long, it is hard to find the one wanted, while the list shows each article's summary gloss (or its Norwegian definition, if untranslated), so the right one can be found and opened. A divergence from ordbokene's default.

<a id="d72"></a>
### 72. A link to the feedback form, until launch (2026-10-20)

**Status:** built, live from 21 October 2026; replaced by [173](#d173), Ordpar's own survey kept after launch, live since 7 November 2026.

Robin had shared a feedback form (a Google form) and asked to link it from the site until launch. Ruled: the footer's "under development" note ([63](#d63)) ends with "Tell us what you think →", opening the form in a new tab. The link is written by script, so adding or removing it changes no page and no offline copy; it loads nothing from Google, so the site still loads nothing from third parties ([19](#d19), [26](#d26)). The address was one line in `ordpar/site/shell.js`; emptying it removed the link. The note, and the link with it, was to go at launch.

<a id="d74"></a>
### 74. A search icon instead of the "Search" button (2026-10-21)

**Status:** built, live since 21 October 2026.

Ruled, following ordbokene.no: the "Search" button becomes a magnifier icon at the right end of the search box, which gains the width; on a phone that leaves more room for the suggestions' glosses and definitions. The word "Search" stays as the button's accessible name. Done in the stylesheet only (`ordpar/site/shell.css`), so no page changes: the label is hidden visually and the icon drawn in the colour scheme's accent, with the clear button beside it. Without script the form still submits. Tested by `ordpar/tests/test_ordpar_pos_search74_76.py`.

<a id="d75"></a>
### 75. Making the whole site beautiful, after the basics (2026-10-21)

**Status:** open; for after the basic features. Two of its calls built since: the optional layout with an "Example" label ([87](#d87)) and the per-article correction form ([166](#d166)).

The intention: after the basic features, a pass over the look of the whole site, not only the home page. It covers the header, footer, search box, labels, the pages around the article, and perhaps the article card's own box (a shadow, as ordbokene's has), but not the article's body. Following ordbokene's layout is fine, while our colour, name, icon and typography stay ours and no publishers' logos appear. Joined to it since: the header and footer's width and the card's padding ([102](#d102)), a box in ordbokene's manner for the home page's line to "More ways to use Ordpar" ([142](#d142)), accessibility options, and whether to keep the header's tagline ([164](#d164)).

Ruled on ordbokene's content conventions: the card gets a slight shadow; no "Example" label over the examples, since the indentation does the same job more compactly; no Cite button, because Ordpar's English cannot claim academic authority on what a Norwegian word means; a per-article feedback box, if any, asks in free text about errors in the article, not whether the word was found, since adding new words is ordbokene's work, not ours. The "Example" label stays off by default; [87](#d87) later offered it in an optional layout closer to ordbokene.no's. The feedback box became the "Suggest a correction" form on every article ([166](#d166)).

The optional ordbokene typography ([63](#d63)) belongs here. ordbokene.no's pages use Noto Sans for the body and Inria Serif for headwords and headings. Both are published under the SIL Open Font License 1.1; the option would fetch them from their publishers, never from ordbokene.no.

<a id="d76"></a>
### 76. The part-of-speech line as ordbokene's: "NOUN *feminine or masculine*" (2026-10-21)

**Status:** built, live since 21 October 2026.

The general rule is no divergence from ordbokene.no without a good reason. Ordpar wrote "NOUN (FEMININE OR MASCULINE)"; ordbokene.no wrote "NOUN *feminine or masculine*". Ruled: the word class in small capitals, then the gender or subclass in lower-case italics without brackets, as ordbokene renders each class, done site-side. The wording matches theirs too: "subjunction" for a subordinating conjunction. Reading ordbokene's pages showed a wider rule, which the site follows: a noun names every gender it has (two in the data's order, all three as "masculine, feminine or neuter"), a noun marked uninflected still shows its gender, and "uninflectable" is used only for a noun with no gender. This also fixed a real error, where a neuter beside a masculine had been dropped.

The label stays in a muted grey, so it stands out from the summary gloss below it, at the body text's size: a divergence from ordbokene's sizes and colour. Built in `ordpar/sitegen/article.py`; tested by `ordpar/tests/test_ordpar_pos_search74_76.py`.

<a id="d77"></a>
### 77. The hover peek never blocks the link (2026-10-21)

**Status:** built, live since 21 October 2026.

On a computer, the small arrow under a cross-reference's hover peek hung over the top of the word, so a click there hit the peek and did not open the small article. Ruled: the whole word stays clickable. The peek, arrow included, now ignores the pointer (`pointer-events:none`); it holds nothing to click, so a click anywhere on the word reaches the link. Hovering is unchanged, and the stylesheet alone changed, so no pages did. Tested by `ordpar/tests/test_ordpar_minihw78.py`.

<a id="d78"></a>
### 78. The small article's headword looks like the link it is (2026-10-21)

**Status:** built, live since 21 October 2026.

The headword at the top of a small article links to the full article, but it was italic, bold and coloured, with an underline only on hover, so on a phone nothing showed it led anywhere. Ruled: by default the headword is upright, in the text's colour, with the article body's link underline, the clearest sign that it is a link. A Style setting offers instead the main article's headword style (semibold, coloured, upright, no underline), with the note "It is still a link: click it to open the whole article.", so a reader who picks the prettier style knows. Stylesheet and scripts only, so no page changes. Tested by `ordpar/tests/test_ordpar_minihw78.py`.

<a id="d80"></a>
### 80. Small articles cut from the target's own page, fetched when needed (2026-10-21)

**Status:** built, live since 21 October 2026; reopens [34](#d34); its finding 2 amends [81](#d81) and [84](#d84).

Each page carried its small articles inlined, a second copy of text that already exists on the target's own page. Ruled: a click fetches the target's article page (online from the site, offline from the downloaded bundles) and the small article is cut from it. Pages on GitHub Pages fell from about 481 MB to 358 MB, and the offline download from about 40 MB to 26 MB. What it costs: without script a click goes to the article's page, and online the first opening waits for one request. It reverses [34](#d34) (1), which inlined small articles so that a click needed no script and offline came free; offline still works, since the bundles hold every page.

A setting decides when the target is fetched: *on request*, *when pointed at* (the default: the pointer must rest on the link about 150 ms, so a pointer crossing the page fetches nothing; on a phone, from the touch), or *with the page*.

The small article takes the main article's look in every respect. Its defaults: **full** (every sense whole, all subsenses and compound lists, up to six examples, at least one a sense; no sense limit), **compact** spacing, and on computers **scrolling** inside a tall one. On computers its width is the narrowest that gives the same height as the widest allowed, so extra width is used only where it saves lines; the ceiling is 36rem or half the window, whichever is smaller, but never below 19rem; small content may shrink to 12rem. Phones keep 19rem.

Ruled on four findings from the checks:

- **finding 1** An opened small article always hides its link's hover peek.
- **finding 2** "Both" for the etymology and formula lines shows both lines in every *Definitions* setting (amends [81](#d81) and [84](#d84)).
- **finding 3** A link lives on the line that leads ([54](#d54)): no change.
- **finding 4** A link to a whole article (not to one sense) on a Norwegian definition or etymology line shows the target's summary gloss in its peek, as the English line's link to it already did; before, it showed the citing article's own gloss.

Tested by `ordpar/tests/test_ordpar_minifetch80.py`.

<a id="d81"></a>
### 81. Formula lines in English only, such as "used as an adverb:" (2026-10-21)

**Status:** built, live since 21 October 2026; amended by [80](#d80) (finding 2); its default changed by [174](#d174), live since 7 November 2026.

Many subsenses have a definition that is a set formula, "brukt som adverb:" ("used as an adverb:"); five such formulas cover 42 % of the library's subsenses. Showing both languages is repetitive. Ruled: a closed list of formula lines ("(brukt) som" + a word class, "brukt i nøytrum", "brukt i ikke-tellelig betydning", with or without the colon, nothing else on the line) shows its English alone, as compound-list labels already did, in articles and small articles and in every *Definitions* setting, with nothing to reveal: a formula holds nothing to test oneself on. Untranslated pages are unchanged. A divergence from ordbokene.no.

A setting, *Formula lines*: **English** (the default then), **Norwegian** (readers quickly learn the formulas), or **both**; the compound-list labels follow English or Norwegian, and stay English under *both*. The compound label is upright in every setting, as ordbokene's. Under *both*, both lines show in every *Definitions* setting ([80](#d80), finding 2). [174](#d174) later made *both* the default.

<a id="d82"></a>
### 82. One suggestion per article, not per headword form (2026-10-21)

**Status:** built, live since 21 October 2026.

The search suggestions showed one row per headword form, so an article with two spellings (*dannet, danna*) appeared twice, with the same gloss. Ruled: rows that lead to one and the same article merge into one, showing the article's headword line with the forms matching the typed text in bold, ranked by its best-matching form. A form shared by several articles keeps its own "N articles" row, never merged, since its search shows all of them. That row lists the translated articles' glosses with their homograph numerals ("I it · II that · III the"), as many as fit, then "+ N more", which also counts the untranslated ones. A divergence from ordbokene.no, which suggests per form: one meaning, one row, no duplicate glosses.

**A13** Ruled: **point 1** a row too long for its width is shortened in order: the forms that do not match go, then all but the best form, then the word class, then an ellipsis, the "Norwegian only" tag always kept whole; **point 2** the tag keeps its wording; **point 3** a translated set phrase with neither a summary gloss nor an English phrase shows its English definition line instead of nothing (amends [59](#d59) item 11). Tested by `ordpar/tests/test_ordpar_suggest82.py`.

<a id="d83"></a>
### 83. An article opened in the list view follows the inflection setting (2026-10-21)

**Status:** built, live since 21 October 2026.

An article opened from the list view always showed its inflection table, ignoring the setting whose default keeps the table behind the Inflection button. Ruled: an article opened there follows the inflection setting like any article page. ordbokene.no's list view shows the inflections with no option to turn them off (Robin's observation), so this is a divergence, one ordbokene could adopt, since its own setting exists. Fixed in `ordpar/site/lookup.js`.

<a id="d84"></a>
### 84. The etymology line in one language, English by default (2026-10-21)

**Status:** built, live since 21 October 2026; amended by [80](#d80) (finding 2); a fault fixed in [91](#d91).

The etymology was a pair of lines, Norwegian and English, above the first sense, where it takes room before what most readers came for. Ruled: a setting for the etymology line, like *Formula lines* ([81](#d81)): **English** (the default), Norwegian, or both, the English shown directly with nothing to reveal. The Norwegian line is mostly fixed wording ("av latin", "fra norrønt") around source words the English line also carries, so English alone loses almost nothing. A divergence that exists because Ordpar is a translation site. Under *both*, both lines show in every *Definitions* setting ([80](#d80), finding 2).

<a id="d85"></a>
### 85. The settings page in subsections (2026-10-21)

**Status:** built, live since 21 October 2026.

The Article section of the settings page now has four: *Language* (definitions, formula lines, etymology), *Inflection* (inflection tables, context for participle forms), *Cross-references* (cross-references, translation when hovering) and *Small articles* (their language, how much one shows, spacing, a tall one on a computer, when it is loaded, and its headword's look, moved there from Style). The small article's language goes under *Small articles* rather than *Language*. Each group's accessible name starts with its subsection, and saved values survive the move.

<a id="d86"></a>
### 86. The Norwegian definition in an untranslated suggestion, and the row spacing (2026-10-22)

**Status:** built, live since 22 October 2026; the Recent rows' cap added 23 October 2026.

An untranslated article's row in the search suggestions showed only the tag "Norwegian only" ([82](#d82)), while the list view showed its short Norwegian definition ([59](#d59)). The one labelled **D2** (with a 13.6 px label and a line above it):

- translated headwords in the accent colour, as the history rows already had them; Norwegian-only headwords in the text colour, so colour means "has English";
- the untranslated rows under a grey label box "Norwegian only", with a thin rule above the label and after the section, each row showing its first Norwegian definition;
- the label's text the same size as the glosses and tied to it, so it follows any later change of gloss size;
- the exact match still first ([59](#d59)), and set phrases left where the ranking puts them, except after a trailing space, when they are grouped the same way.

With the exact match first, the grouping moves no rows for an ordinary search, because the ranking already puts translated headwords first. The label only marks where the Norwegian-only rows begin.

On spacing, ordbokene.no's suggestions on a computer were as airy and scrolled through 20 rows, perhaps for accessibility. So the spacing stays as it was on every device, the list scrolls through 20 rows ([22](#d22)), and a setting offers roomier rows ("Roomy, for easier tapping", about 44 px, towards the touch-target guidance). The label and rules form a group in the list box, and the arrow keys walk the options only. The Recent rows under the empty search box are capped above a phone's keyboard as the suggestions are, scrolling inside. Tested by `ordpar/tests/test_ordpar_suggest86.py`. ordbokene.no's dropdown showed no definitions, so this is a divergence, recorded in `docs/divergences.md`.

<a id="d87"></a>
### 87. Under "both", the English line emphasized and the Norwegian faded (2026-10-22)

**Status:** built, live since 22 October 2026; the default amended by [174](#d174) (Norwegian emphasized again, live since 7 November 2026).

When both languages showed, each definition's Norwegian line was in the text colour and the English line under it was faded and smaller. The reverse, as a setting, applies to **definition lines only**: senses, subsenses, set phrases' senses, formula lines and the etymology line, in articles and small articles alike. Example sentences keep the Norwegian emphasized, because there the Norwegian is the point. Colour and size swap together (the emphasized line at full size, the other faded at 0.95). The default became English emphasized; the setting "Emphasis, when both languages show" restores the old look. Links live on the emphasized line ([54](#d54)'s "the link lives on the line that leads").

The new default made Norwegian examples read like the English definitions, so their look changed too. Examples became quote blocks with a left bar. Subsenses became bullet points, and compound lists a plain line at the end, both as ordbokene.no showed them. A second setting, "Article layout", offers "Closer to ordbokene.no". That layout gives a real "Example" heading before a sense's own examples, flush with the sense's text, with no heading on subsenses' examples. Ordpar's own layout keeps [75](#d75)'s rule of no "Example" label. Tested by `ordpar/tests/test_ordpar_emphasis87.py`.

<a id="d88"></a>
### 88. History rows show the suggestions' glosses (2026-10-22)

**Status:** built, live since 22 October 2026; amended twice the same day.

History rows draw as the suggestion row for the same word does ([82](#d82), [86](#d86)): the translated articles listed by their numbered glosses ("I it · II that · III the"), the untranslated ones counted under "+ N more", "N articles" only when all are untranslated, and one untranslated article shown by its Norwegian definition. There is no section label. The headword is in the accent colour only when a translated article is behind it, as in [86](#d86). Rows are drawn when shown, not stored: each re-runs its search, so older entries are fixed too and the stored format is unchanged.

**First amendment:** a history row lists only the articles whose own headword the search matched. Opening an article reached through an inflected form adds that article to the history as its own entry. A search that found only inflected forms (*gikk* → *gå*) records nothing until one is opened.

**Second amendment**, under the rule of one style wherever the same thing shows: the first version listed untranslated articles by their Norwegian definitions among the glosses, mixing the two languages. That part was reversed in favour of the "+ N more" count above. Tested by `ordpar/tests/test_ordpar_history88.py` and `ordpar/tests/test_ordpar_history88b.py`.

<a id="d89"></a>
### 89. The favourites page as list-view rows that open in place (2026-10-22)

**Status:** built, live since 22 October 2026.

The favourites page reuses the list view's rows: a click opens the article on the page, following the settings as an article opened in the list view does (the inflection tables included). An opened favourite keeps Copy link, Share, the heart and a link to the article page, and the heart inside it removes the row. The row's tag stays, as list-view rows carry it. Offline it works with the downloaded copy, and without it a row is a plain link. The history page is unchanged, since its rows are searches. Tested by `ordpar/tests/test_ordpar_favourites89.py`.

<a id="d90"></a>
### 90. Subsenses in English only, as a setting (2026-10-22)

**Status:** built, live since 22 October 2026.

A setting under Article → Language, "Subsenses", shows bulleted subsenses in English only: "As the definitions" (the default) or "In English only". It acts where both languages show. A subsense then shows its English alone, in the main style, with its links live. When the definitions are English only, nothing changes. When they are Norwegian with the English behind a reveal, a subsense keeps its reveal, because unlike a formula line it has something to test oneself on. A formula line keeps its own setting ([81](#d81)). Small articles follow the same rule.

Numbered senses are left out and follow the definitions setting: a set phrase's numbered senses, and the numbered subsenses an article shows when it has only one sense. In the data these are subsenses, but they read as the article's senses. The setting therefore acts on the bulleted subsenses only. It is a divergence from ordbokene.no that exists only because Ordpar adds English.

<a id="d91"></a>
### 91. The page jumps when a small article opens near the right edge on a phone; and a link leak into an etymology small article (2026-10-22)

**Status:** built, live since 22 October 2026.

On a phone, opening a small article near a page's end and towards the right edge made the page jump. To measure the box, the code briefly placed it where it overhung the right edge. Phone Chrome then widened its layout viewport, the page's maximum scroll dropped and the scroll position was clamped, and it was never restored. The box is now measured parked a window's width to the left, then placed as before. It lands in the same place, and the jump is gone. Tested in phone emulation by `ordpar/tests/test_ordpar_browser_scroll.py`.

A small article opened from the etymology line sits inside that line, and [84](#d84)'s rules for the English etymology line reached into it, making its English words live under "Norwegian emphasized". Every rule reaching a link inside an article's line pairs is now scoped away from small articles. The same leak from [54](#d54)'s, [87](#d87)'s and [90](#d90)'s rules was closed with it. Tested by `ordpar/tests/test_ordpar_fixes91.py`.

<a id="d92"></a>
### 92. Load ahead on a resting pointer beyond the small articles (2026-10-22)

**Status:** built, live since 22 October 2026; the sound icon brought under the same setting by [170](#d170); extended to every control that opens something by [180](#d180), live since 11 November 2026.

Only a small article's target was fetched ahead, when the pointer rested on its link ([80](#d80)). Most of a row's first-open lag (150–550 ms) was the network fetch of the article's page. Loading ahead on a resting pointer removes about 95 % of it on a computer, and nothing on a phone, which has no resting pointer. Built:

- **(A)** loading ahead for list rows, history and favourites rows, and the History and Favourites links, sharing one queue with the small articles; a touch also starts the fetch.
- **(B)** the setting moved from Small articles to a widened section, "Loading, offline and your data", under *Loading*, with its values and saved choice unchanged.
- **(C)** a suspected extra connection per session was not confirmed, so nothing was changed.
- **(D)** the history page's script sent with the other shell scripts, so a first History opening makes one request, not two.
- **(E)** the offline copy's bundles cut from 2,000 articles to 500. Unpacking one article fell from 25 to 7 ms on a computer, for 1.3 % more download.
- **(F)** loading everything with the page was not made the default for readers with an offline copy. On a link-heavy article it would unpack many bundles at once on a phone, while the smaller bundles already give most of the gain. A reader may still choose it.
- **(G)** an error in a suggestion row's article count, seen when typing "hu" in the header search, fixed; and the install offer's bar hidden while the suggestions are open.

Tested by `ordpar/tests/test_ordpar_loadahead92.py`.

<a id="d93"></a>
### 93. A homograph numeral per spelling, as ordbokene (2026-10-22)

**Status:** built, live since 22 October 2026 (the follow-up 23 October 2026); the tag point amended by [137](#d137) (the tag dropped, live since 26 October 2026); the About sentence replaced by [106](#d106).

An article with two spellings carrying different homograph numbers showed one numeral for the whole headword line: "lysing, lysning I" where ordbokene.no printed "lysing I, lysning II". In 395 articles the spellings' numbers differ. ordbokene.no showed each spelling with its own lemma's number, none for a 0, and both numerals where they match ("tore II, tørre II"). This was a fault against ordbokene's rendering, which is Ordpar's baseline. Each spelling now carries its own numeral in the article's headword line and wherever the site shows a numeral for a matched form: results, list view, the suggestions' numbered glosses, history and favourites. Results and suggestions are ordered and numbered by the matched spelling. The list view separates spellings with ", " as the headword line does, not " / ". The stored separator in readers' history and favourites stays readable.

A follow-up:

- **(1)** one numeral look, the article's (raised, maroon, bold), in the list view, favourites, inflected-form rows and gloss lists; the look was revisited in [105](#d105).
- **(2)** four articles whose spellings Ordpar deliberately reorders (the more common form first, on usage counts) show that order in the headword line, and the page title follows the headword line, so the two never disagree.
- **(3)** a sentence on the About page: "In a few articles we have also put the more common form of the headword first, where Bokmålsordboka lists it second."
- **(4)** the Recent rows capped above a phone's keyboard ([86](#d86)).

The "translated" tag was kept for the time being; [137](#d137) later dropped it. Tested by `ordpar/tests/test_ordpar_homograph93.py`, `ordpar/tests/test_ordpar_followup93.py` and `ordpar/tests/test_ordpar_title_headword.py`.

<a id="d94"></a>
### 94. The offline copy did not take an update by itself (2026-10-22)

**Status:** built, live since 22 October 2026; confirmed on a real phone at the next deploy.

An installed copy of the site on Android did not pick up a new build until Chrome itself was closed. The update check ran once per opening, marked with a session flag. On Android, closing the installed app's window does not end Chrome's session, so the flag from an earlier check survived every reopening. Now the copy checks when the app opens and whenever it comes back to the screen, at most once every 15 minutes, timed from the last check that reached the site. Article pages check too, where a copy is in use. Once the copy has switched to the new build, a small bar says "Ordpar has been updated — reload to see it", with a Reload button and a close button, in the install offer's look. Tested by `ordpar/tests/test_ordpar_offline94.py`.

<a id="d95"></a>
### 95. A list of changes for readers (2026-10-22)

**Status:** built: the site list kept since 22 October 2026, the content list since 23 October 2026; amended by [175](#d175) (both lists public as pages, and the content list's entries shortened, live since 7 November 2026).

A change list is kept, so readers can see what was updated. There are two lists: `ordpar/changes.md` for the site, and `ordpar/library-changes.md` for the dictionary's content. Every deploy adds a dated entry to the site list in readers' words, and one to the content list whenever the content changed. The content list says what changed in the content, corrections of Bokmålsordboka's own data included. As first ruled, a content refresh against a newer Bokmålsordboka was one short line credited to its makers, the Language Council and the University of Bergen, with Ordpar's follow-up work beside it; [175](#d175) shortened the entries to what changed.

Versions are the site's only: the dictionary's content is listed by date, not numbered. Launch would be one entry, **1.0.0**, "the first public version"; [175](#d175) made the lists public before launch, with dated entries until 1.0.0. After 1.0.0, the second number marks a new feature (headword audio would be 1.1.0) and the third marks fixes. The version is to be shown on the About page and in the offline settings from launch.

<a id="d97"></a>
### 97. The small article: the article's spacing by default, and the header's gloss in the text colour (2026-10-23)

**Status:** built, live since 23 October 2026; the small article's text sizes later set by [114](#d114).

A small article's spacing ([80](#d80)) now defaults to the article's own, with *compact* kept as a choice. A reader's saved choice stays as saved, and only readers who never chose get the new default. The gloss in a small article's header (" — place of residence") is drawn in the text colour, no longer faded.

<a id="d98"></a>
### 98. Sense numbers skip a number for each bulleted subsense (2026-10-23)

**Status:** fixed, live since 23 October 2026.

After subsenses became bullet points ([87](#d87)), an article's senses were numbered 1, 3, … where sense 1 held a bulleted subsense (*møte* II). The markup was right. Each bullet was drawn as a list item, and every list item advanced the enclosing list's counter. ordbokene.no numbered its senses 1, 2, 3, so this was a fault: the bullet is kept and the counter no longer advances. Tested in a real browser by `ordpar/tests/test_ordpar_browser_senses.py` ([100](#d100)).

<a id="d99"></a>
### 99. Hints in the settings: why a reader might pick a choice (2026-10-23)

**Status:** built, live since 23 October 2026; two hints reworded.

To keep the long settings page from growing, the hints sit behind a "?" on a setting's title line. It opens a small box with the setting's trade-off and a line per choice that has one. On a computer the box shows on hover and stays open on a click. On a phone a tap opens and closes it, and a tap elsewhere or Esc closes it. The "?" is a real button for keyboards and screen readers. The nine earlier grey notes under choices moved into the same boxes, so explanations have one place. Twelve settings have a "?".

Two hints were reworded afterwards. Definitions in Norwegian with the English behind a reveal: "For when you mostly follow the Norwegian: the English stays hidden until you need it." A small article's short summary: "Leaves out most subsenses and lists of compounds. Open the whole article for them." Tested by `ordpar/tests/test_ordpar_hints99.py`.

<a id="d100"></a>
### 100. Browser tests for the site (2026-10-23)

**Status:** built, in use since 23 October 2026; test 5 not yet built.

No site test opened the site in a real browser, so a fault in how correct markup is drawn, such as [98](#d98)'s numbering, passed every test. The rendered numbers are read from the browser's accessibility tree, which is exact and is what a screen reader hears. Five more checks, all pass-or-fail; the first four were built:

- **(1)** every page's title matches its headword line;
- **(2)** no broken links inside the site;
- **(3)** a small article near the right edge does not move the page in phone emulation ([91](#d91));
- **(4)** suggestion, Recent and list rows keep their height;
- **(5)** dark-mode contrast by the WCAG formula, left for later, since it needs a choice of views first.

`ordpar/docs/tests.md` indexes every site test file: what it checks, the decision it pins, and how it runs. Every later build that adds a test adds its row. A later fix made the test harness always close its browser and remove its throwaway profile, even when a test fails, times out or is killed (`ordpar/tests/browser/harness.py`, tested by `ordpar/tests/test_ordpar_browser_cleanup100.py`).

<a id="d101"></a>
### 101. The site's tests move into `ordpar/tests/` (2026-10-23)

**Status:** done 23 October 2026.

The site's test files moved from the repository's shared tests folder to `ordpar/tests/`, with the browser harness at `ordpar/tests/browser/`. `ordpar/` is the folder that becomes the public repository, and tests belong with the code they test. The names were kept, and references in the site's docs and code followed. Most of the moved tests also read the flashcard deck's code or library files, so in a split-out repository they run only once the renderer moves ([48](#d48)), as for the site's code itself.

<a id="d102"></a>
### 102. The article card too narrow for the inflection table (2026-10-23)

**Status:** built, live since 23 October 2026.

Ordpar's article card was a fixed 704 px. On an article page an inflection table could run past the card's edge, and in the list view the table always went narrow. Both came from earlier rulings made before the card had a visible edge ([43](#d43), [59](#d59)). ordbokene.no's card, measured, was fluid below a 784 px window, then stepped through 736, 992, 1,248 and 1,504 px. Its wide table showed when the window was at least 1,024 px at load. Ruled:

- **(1)** the card in ordbokene.no's steps, results the same width;
- **(2)** the table's switch decided by Ordpar's own measured fit everywhere, a deliberate divergence: never a table past the card, the wide one wherever it fits, re-decided on resize;
- **(3)** the text at the card's width, as ordbokene.no's;
- **(4)** tests: ordbokene.no's measured widths pinned in a browser test holding Ordpar's build to them (`ordpar/tests/test_ordpar_browser_cardwidth.py`), and a live side-by-side comparison script (`ordpar/tests/browser/compare_ordbokene.py`), kept out of the test run and run before each deploy, reporting differences without blocking. Geometry only, never a screenshot comparison, since fonts and colours differ on purpose.

The header and footer stay at their width for now, to be decided with the header's whole design ([75](#d75)).

<a id="d103"></a>
### 103. A guarded deploy: a test gate, a check after the push, a rollback (2026-10-23)

**Status:** built, in use since 23 October 2026.

As the site gains readers, a bug should not reach thousands of them before it is fixed. Three steps were chosen. A deploy refuses a build unless every test passes against it, browser tests included; an override needs a written reason, which is logged. After the push, the browser tests run against `https://ordpar.no` once GitHub serves the new build. A rollback re-publishes the previous build **as a new version**, so that installed offline copies ([94](#d94)) update back instead of keeping the bad one. Faults no test describes yet are not covered; each is closed by a new test as it is found. Built in `ordpar/deploy.py`, tested by `ordpar/tests/test_ordpar_deploy103.py`.

<a id="d104"></a>
### 104. Counting daily users without cookies (2026-10-23)

**Status:** the receiver live since 5 November 2026, taking correction reports ([166](#d166)), with the counting off; the counting is set to start on 1 December 2026 unless Nkom objects first.

The frame: no cookies and no third party ([19](#d19)), counts from our own receiver, a Cloudflare Worker ([26](#d26), [62](#d62)).

**The method.** A daily code made on the receiver from the IP address and browser name with a secret replaced every day (Plausible's published method). Distinct codes give the day's users; nothing is stored on the reader's device. The secret is kept where no history can restore it, so yesterday's codes cannot be matched once it is deleted. App installs are counted too, with nothing identifying. A statistic is added only when it answers a question we actually have, and each is described on the privacy page. Searches carry no daily code, no time of day and no arrival order, so they are not tied to a reader's page views.

**People, not bots,** in six layers, the method stated beside any number: only the page's script sends; known crawler names are dropped (a public list kept locally); nothing is sent from an automated browser, or before the page has been visible a moment or used; data-centre networks are skipped; a daily code reading at an inhuman pace is dropped when counting.

**What is kept.** Page-view lines for one day after the day they arrive, then daily totals only; search lines for 30 days, then only strings seen at least three times, as counts, lower-cased and in random order. Search terms can touch on very personal matters, and a day's page views are one device's reading trail. The database can restore a deleted line for 7 days, which the privacy page says. At the go-live the databases are to be created in Cloudflare's EU jurisdiction, its request logs off. Nothing is sent under Global Privacy Control or Do Not Track, or when the reader turns off "Send usage statistics" in Settings (one switch for everything; "Delete stored data" turns it back on).

**The search left the address.** Searches reached the host's servers in the page address. The search now travels after `#` (`/bm-en/#q=`), never sent to a server; old `?q=` links still work.

**Going live.** Whether such a page script needs the reader's consent under Norway's electronic communications act (§ 3-15) is not settled by any source, so Ordpar asked Nkom, the regulator. Set aside: counting on the server with Cloudflare in front of ordpar.no (it hands Cloudflare every page request) and Plausible itself (a third party, counting by the same kind of script). The privacy page (`ordpar/privacy.md`, with a list of its sections at the top) is live ([166](#d166)); its passages on the counting, and the switch, stay hidden until the counting starts. See `ordpar/docs/receiver.md`.

<a id="d105"></a>
### 105. The homograph numeral closer to ordbokene's look (2026-10-23)

**Status:** built, live since 23 October 2026; the Anki deck follows.

The homograph numeral (the "III" in *fange* III) was raised, maroon, bold and small everywhere ([93](#d93)). Ordbokene.no showed it on the line, smaller, grey and not bold. Ruled: 0.60 of the headword beside it, in the muted text colour (light #757070, dark #b9b6b6), weight 600, raised 0.14 em, with no gap beyond a space. In the gloss lists of the suggestions, History and Recent it has its own size, 0.80 em of the gloss text, and is not coloured. The small article's header keeps "lysing (I)", and the suggestions still show no numeral after a headword. One style everywhere at once: the headword line, full results, inflected-form rows, list view and favourites.

The rule is shared with the Anki deck (`.ordbok-homograph` in `ordbok_gen.py`), and the deck follows the website in all respects, so its cards take the new look too. Tested by `ordpar/tests/test_ordpar_browser_homograph105.py` and `ordpar/tests/test_ordpar_followup93.py`.

<a id="d106"></a>
### 106. A change notice and a link to ordbokene.no on the articles whose Norwegian we changed (2026-10-23)

**Status:** built, live since 23 October 2026.

Ordpar corrects some of Bokmålsordboka's text (typos, cross-references that point to the wrong place, notation). CC BY 4.0 asks a reuser to indicate changes, and the About page already described them in general. Ruled: every article with a live correction carries one line at its foot, beside Copy link, Share and Favourite, naming only the kinds of change (no before and after), with a link, "Bokmålsordboka's article on ordbokene.no". It replaces the About page's sentence of [93](#d93) (3). This partly reopens [63](#d63), which ruled out a source link on every article: on a changed article, the original *is* different content. Fixed cross-references count, and come first, since they change what a reference means; a reordered headword reads "We put the more common spelling of the headword first."

To keep it true, each correction is checked at build time against Ordpar's latest copy of ordbokene's data: one ordbokene has since fixed itself gets no notice, and neither does one the reader cannot see on the page. The About page's "What Ordpar has changed" became a list of each kind of change with its count, filled in by the build from the same check and dated by the data's date. Code: `ordpar/sitegen/corrections.py`; tested by `ordpar/tests/test_ordpar_changenotice106.py`. See also [151](#d151).

<a id="d107"></a>
### 107. Every setting lists its default first (2026-10-23)

**Status:** built, live since 23 October 2026.

Two of the 21 settings broke it: the small article's spacing (now As the article, Compact) and the list view (now Only when there are several articles, On, Off; On before Off, as in every other on/off setting). Stored choices are kept by name, so no reader's setting changed. A test, `ordpar/tests/test_ordpar_settings_default107.py`, fails whenever a setting's default is not its first choice; it caught a later slip ([147](#d147)).

<a id="d108"></a>
### 108. The wide table stacks its cells before going narrow (2026-10-23)

**Status:** built, live since 23 October 2026 (stacking by space saved).

The inflection table had two layouts: the wide one where its full width fits, else the narrow one ([102](#d102)). So a table that only just missed went straight to the narrow layout, and one that only just fitted was squeezed, its cells wrapping unevenly while columns kept spare room. Ordbokene.no's tables stack their cells first. Ruled: **(1)** the wide table wherever it fits with its cells stacked, broken between a form and its frame words ("møtt +" / "noun"), never inside a form, as ordbokene's breaks fall; the narrow layout only below that; **(2)** the table at its natural width, stacking only as far as its box requires, no column wider than it needs; **(3)** the same in the article, full results, list and favourites rows; **(4)** a browser test on *møte* II.

To meet (2), the table stacks one column at a time until it fits, rather than all at once. At each step the column whose stacking frees the most width goes first: this reaches a fit with the fewest columns stacked, where widest-first could stack a column that frees little. Ordbokene's own squeezed table keeps spare width in its columns, so our tighter table is a deliberate difference. The choice still depends on fit, not on window width ([102](#d102)). Code: `ordpar/site/inflection.js`; tested by `ordpar/tests/test_ordpar_browser_tablestack.py` and `ordpar/tests/test_ordpar_browser_cardwidth.py`.

<a id="d109"></a>
### 109. A written procedure for every deploy (2026-10-23)

**Status:** built, in use since 23 October 2026.

Ruled: every deploy step in order is written down in one place (a project skill for Claude Code): the owner's go-ahead, the full build, the comparison with ordbokene.no (reported, never blocking), the change-list entries, publishing and the check after it, the records, and the rollback. Since a written procedure helps only when it is read, `ordpar/deploy.py` also refuses to prepare a deploy without an `ordpar/changes.md` entry newer than the last published version, and without a newer `ordpar/library-changes.md` entry when the content has changed; `--skip-changes "<reason>"` overrides it, logged. Tested by `ordpar/tests/test_ordpar_deploy109.py`.

<a id="d110"></a>
### 110. Going public: what is left first (2026-10-23)

**Status:** ruled; the public release (the deck on AnkiWeb) happened on 25 October 2026 ([131](#d131)); 1.0.0 not yet. The `noindex` row amended by [128](#d128).

Ruled: the deck's release, with its link, comes first and is in effect the site's public release; it does not wait for the receiver ([104](#d104)). Version 1.0.0 of the site comes later, after its main steps, the look ([75](#d75)) among them.

Where the items once ruled "at launch" fall: `noindex` lifted with the word pages ([117](#d117)), not at 1.0.0 (later lifted at once on the translated pages, [128](#d128)); the "under development" note until 1.0.0; the feedback link past 1.0.0 as long as it brings useful answers; the published scripts without their comments ([61](#d61)) before the public release; the change list's entries hidden until 1.0.0 ([95](#d95)).

<a id="d111"></a>
### 111. The example sentences' English behind a reveal, as a setting on the site (2026-10-23)

**Status:** built, live since 23 October 2026.

Until now only the Anki deck hid an example's English ([49](#d49)). Ruled: the site offers it too, so deck and site no longer diverge. A setting "Examples" in Settings → Article → Language: *Norwegian and English* (the default, first, [107](#d107)) or *Norwegian, with the English hidden until revealed*, with the hint "For practising your Norwegian: read the example first, then reveal the English to check yourself." It uses the same "Show English" cue as the Definitions setting ([37](#d37), [99](#d99)), on every example the site shows, Bokmålsordboka's and our added ones, in articles, results, list rows, set phrases and small articles.

The "Show English" cue's text also became the muted grey, to make it less prominent; the rule is shared with the deck (`ordbok_gen.py`), which follows. Tested by `ordpar/tests/test_ordpar_examples111.py` and `ordpar/tests/test_ordpar_browser_examples111.py`.

<a id="d112"></a>
### 112. A setting for how many examples show under each sense (2026-10-23)

**Status:** built, live since 24 October 2026.

Some senses have many examples (*gå* has 15 under its first), which makes skimming the senses hard. Ruled: a setting "Examples under each sense", a drop-down with All (the default, first) and 1 to 10; a drop-down rather than a number box, since on a phone it opens the phone's own picker with nothing to type. With a limit set, a second setting, "The line to show the rest" (On by default), decides whether a "Show N more examples" line opens the rest in place or the rest is simply not shown. Each sense and subsense has its own limit, the first examples in Bokmålsordboka's order; our added examples come last and count toward it. It applies in articles, full results, list and favourites rows and set phrases; small articles keep their own cap of 6. Ordbokene.no had no such limit (`docs/divergences.md`). Tested by `ordpar/tests/test_ordpar_exlimit112.py` and `ordpar/tests/test_ordpar_browser_exlimit112.py`.

<a id="d113"></a>
### 113. The phone's keyboard after a search, and no capital letter (2026-10-24)

**Status:** built, live since 24 October 2026.

On a phone, the keyboard stayed open after a search and covered the result, and the search field started with a
capital letter. Now, after a search by Enter or by choosing a suggestion, the field lets go of focus on a touch
screen, so the keyboard closes; on a computer it keeps focus, as ordbokene.no's does. The field no longer starts
with a capital (`autocapitalize="none"`); the phone's own shift key still gives one. The site has one search field,
on every page, so the change reaches them all. Tested by `ordpar/tests/test_ordpar_search113.py` and
`ordpar/tests/test_ordpar_browser_search113.py`; the keyboard itself was checked by hand on a phone, since a test
cannot see it.

<a id="d114"></a>
### 114. The text sizes in the small article, and its header gloss (2026-10-24)

**Status:** built, live since 24 October 2026.

The body already mirrors the article's style
([70](#d70), [80](#d80), [97](#d97)), so it got one size control for the whole of it.

Chosen: the header line 1.1rem (was 1.02rem), the number in brackets after the headword at the
headword's size; the header's gloss 1rem (was .92rem), semibold (600), upright, in the text colour; the body 1rem,
the article's own size (was .92rem), its proportions unchanged. A new setting under Small articles, "Text size",
offers "As the article" (the default, listed first) and "Smaller" (the old sizes); the gloss stays semibold in
both. The hover peek's gloss and the glosses in list rows and suggestions were left as they were; [116](#d116)
took up the rows and suggestions.

The Anki deck shares the header's rules (`scripts/mini.py`) and follows the site, as [105](#d105) rules; its small
articles' body was also set to the card's own size, so the header is not larger than the text under it. Tested by
`ordpar/tests/test_ordpar_browser_minitext114.py` and `ordpar/tests/test_ordpar_deckmini114.py`.

<a id="d115"></a>
### 115. Random word opens a headword search, as on ordbokene.no (2026-10-24)

**Status:** built, live since 24 October 2026; with the English search switched on, Random word draws an English word ([155](#d155), live since 31 October 2026).

Ordbokene.no's "Tilfeldig ord" opens its search page for a random headword, not an article. Ordpar now does the same: Random word opens `/bm-en/#q=<headword>`, showing
every article for the word, as any search does. This reverses [67](#d67)'s "opens an article" but keeps its bar.

A headword is drawn if the **first** article its search shows meets [67](#d67)'s bar (translated, not a fixed
expression, with a summary gloss); later articles may be untranslated. A stricter rule, every article meeting the
bar, was considered and dropped: it would have left out words such as *fly*. The pool is found through the site's
own search, so the first article is the one the search shows first.

A drawn word is not a search.
It is neither recorded in History nor sent as a search to the site's reader count ([104](#d104)), also after a reload or Back and Forward. Opening an
inflected-form row from a drawn search is the reader's own act and is recorded ([88](#d88)). Since
[117](#d117), a drawn word opens its word page where it has one. Tested by `ordpar/tests/test_ordpar_random115.py`,
`ordpar/tests/test_ordpar_browser_random115.py` and `ordpar/tests/test_ordpar_browser_randomdraw115.py`.

<a id="d116"></a>
### 116. Summary glosses semibold in list rows and suggestions, the separator faded (2026-10-24)

**Status:** built, live since 24 October 2026.

Ruled, as a general rule: **summary glosses are semibold (600) wherever they show; definitions, Norwegian or
English, are regular wherever they show.** An English definition line, shown where an article has no summary
gloss, stays regular. Sizes are unchanged. The "·" between glosses is in the muted grey but keeps the glosses'
weight, wherever it separates glosses: the rows, the article's head and the small article's header (the deck's
small-article header follows, [105](#d105)).

A row cannot tell a summary gloss from an English definition by its text, so the build marks which snippets are
summary glosses, and only those are made semibold. Four points were ruled to stay as built:
**(1)** in a gloss list, a separator before a definition takes the definition's weight; **(2)** History, Recent and
favourites rows drawn from stored text read the index once to know whether a line is a summary gloss; **(3)** a set
phrase's box stays regular; **(4)** the hover peek's gloss is already bold and its separator is not faded. Tested by
`ordpar/tests/test_ordpar_rowgloss116.py` and `ordpar/tests/test_ordpar_browser_rowgloss116.py`.

<a id="d117"></a>
### 117. Word pages search engines can index, as ordbokene.no's search pages (2026-10-24)

**Status:** built, live since 26 October 2026.

A search on ordbokene.no has its own address, and Google lists those search pages. Ordpar's searches lived after `#q=` ([104](#d104)), which
no search engine sees. Putting the typed search in the address was not taken up: every search would reach the host
again, which [104](#d104) had avoided, and each such address would be answered by the "not found" page. Instead the
build makes real pages ahead: `/bm-en/da/`. A word page shows what the search shows, in the list view's form (rows,
then the "is an inflected form of" rows and the similar headwords, which an article page lacks and a searcher may
want), so no article is copied; in a browser the reader's list-view setting applies, so browsing is unchanged. A
search for a word with a page now opens that page, as do Random word and the similar-headword links; any other
search stays after `#q=`.

**(1)** Word pages are built. **(2)** For headwords whose first article is translated; a word gains a page when
its first article is translated. **(3)** A page also for each irregular inflected form of a translated word (one
that does not begin with the word's spelling, such as *tær* for *tå*) seen at least 100 times in the National
Library's 2026 book counts; regular forms are left to Google's own matching for now, no pages for passive-only
forms. Every "is an inflected form of" row gains its form label after the word class: *tå* *noun* (plural
indefinite).

A word with several entries is titled "så — Norwegian–English dictionary" and described as "N entries in the
Norwegian–English dictionary:" then each homograph's numeral and first summary gloss, an untranslated one "Norwegian
only"; the word page and each article are their own canonical pages, since "så" and "så verb" are different
searches. A word with one article takes the article's title and description, and its word page is canonical.
GitHub Pages was checked first to serve folder names with æ, ø and å. Tested by
`ordpar/tests/test_ordpar_wordpages117.py` and `ordpar/tests/test_ordpar_browser_wordpages117.py`.

<a id="d118"></a>
### 118. Norwegian-only articles: linked compounds, and their labels in Norwegian (2026-10-24)

**Status:** built, live since 24 October 2026.

On an untranslated article, the compound lists showed each compound as plain text with no link, under an English
label ("used as a suffix in:"), while ordbokene.no links every compound. Of such an
article's formula lines, only the compound-list labels were still in English.

Ruled: on a Norwegian-only article, **every compound in a compound list is a link**, as on ordbokene.no (plain only
where the target has no page), and **every formula line and compound-list label is Norwegian**, whatever the
`formulas` setting ([81](#d81)): the dictionary's own wording where it has one. The links were a fault; English lines look odd in an otherwise Norwegian article. This
covers an untranslated page and a translated page's untranslated set phrases; the small articles follow, being cut
from the page. Translated pages are unchanged; the deck has no Norwegian-only articles. Tested by
`ordpar/tests/test_ordpar_nbcomp118.py` and `ordpar/tests/test_ordpar_browser_nbcomp118.py`.

<a id="d119"></a>
### 119. English on the links of a Norwegian-only article: the target's own glosses (2026-10-24)

**Status:** built, live since 24 October 2026.

On a Norwegian-only article a cross-reference had no hover peek and no gloss in the small article's header, even
when the target was translated. Where no reference gloss was written, the target's own English is the best the
site has; it is borrowed at build time from the target, not stored twice.

Chosen: on a Norwegian-only article, **a link to a whole translated word with summary glosses**
shows those glosses ("·"-joined) in the hover peek and in the small article's header; **a link to one sense of a
translated word** shows that sense's whole English definition in the peek, breaking where the article breaks it
(after each ";"), in regular weight ([116](#d116)), wrapping at 22rem. The small article's header then stays the
headword alone, since the line is in its body. A target with no summary glosses, or untranslated, shows nothing.
The compounds linked by [118](#d118) follow the same rule. A Norwegian-only page now changes when one of its targets
is translated. Tested by `ordpar/tests/test_ordpar_nbpeek119.py` and
`ordpar/tests/test_ordpar_browser_nbpeek119.py`.

<a id="d120"></a>
### 120. On a narrow screen, a setting's choice starts beside its button (2026-10-24)

**Status:** built, live since 24 October 2026.

On a phone, a long choice in Settings wrapped as a whole onto the line below its radio button. Each choice now
keeps the button at its own size and lets the label take the rest of the line, wrapping inside it, so the first
line sits beside the button. This applies to every radio on the settings page. Tested at a phone's width by
`ordpar/tests/test_ordpar_browser_radiowrap120.py`.

<a id="d121"></a>
### 121. The About page: the site's aim, and free to use (2026-10-24)

**Status:** live since 24 October 2026; the deck link, added at the deck's release, live since 26 October 2026.

The About page gained a statement of aim after its opening paragraph: "Ordpar's aim is to help people learn
Norwegian. Translating Bokmålsordboka into English, and later into other languages, is how we work towards that: a
learner can read a Norwegian word's whole dictionary entry in a language they already know. Ordpar is free to use,
with no advertisements and no account, and its English is free to reuse (see The English, below)." It states what is true today rather than
a promise: "no tracking"
was left out because a daily-reader count was planned ([104](#d104)). The About page and the published README are
one text (`ordpar/about.md`).

At the deck's release, "Thanks", where it names the Kelly list, gains a link to the Anki deck and a sentence that
the deck is CC BY-SA, as the Kelly list is, being a derived work; the dictionary stays CC BY. The sections were
reordered: "The English" right after "Where the dictionary comes from", then "Our changes to the Norwegian".

<a id="d123"></a>
### 123. Bokmålsordboka's pronunciation field on Ordpar's pages (2026-10-24)

**Status:** built, live since 24 October 2026; the "?" beside it removed, live since 2 November 2026.

The dictionary's data has a pronunciation field on about 4,400 of 94,000 articles, which Ordpar did not show. Most
entries are respellings in Norwegian spelling with stress marks ("abstrakˊt"), with nothing to translate; a few use
a small fixed set of words ("i flertall", "eller", "tysk").

Ruled: the respellings are shown verbatim, under "Pronunciation", after the inflection and before the etymology,
as ordbokene.no's rendered page places it. The field's words are English on a translated
article, unless the existing `formulas` setting ([81](#d81)) asks for Norwegian, and always Norwegian on a
Norwegian-only one.

The marks need explaining, but the article body stays lean. A new **Help** page (`/help/`, linked in every
footer beside "About and licence", as ordbokene.no has "Hjelp" beside "Om ordbøkene") carries the
note: a mark after the stressed syllable shows the stress and, ´ or `, which of Norwegian's two word tones it has;
the tones can tell words apart, such as *bønder* and *bønner*; a hyphen means only part of the word is spelt out. The marks' meaning is taken from the Language Council's pronunciation advice, the tones' description from
Store norske leksikon; ordbokene.no had no key online.

At first a closed "?" beside the label opened the note in place, only on entries that use the marks. It was removed from the site:
once the line also carried the sound icons ([159](#d159), [160](#d160)), the "?" took space and attention for a
note read once. The note stays on Help. Tested by
`ordpar/tests/test_ordpar_pron123.py` and `ordpar/tests/test_ordpar_browser_pron123.py`.

<a id="d124"></a>
### 124. A click outside an open "?" box only closes it (2026-10-24)

**Status:** built, live since 25 October 2026.

On a phone, tapping outside an open "?" box in Settings to close it could also change a setting. Ruled: while a
"?" box is open, a click or tap anywhere outside it closes the box and does nothing else; it neither picks a
setting nor follows a link. The next click acts as usual. One mechanism (`ordpar/site/shell.js`), the same for
every "?" box drawn that way: the settings' hints ([99](#d99)) and, at the time, the pronunciation "?"
([123](#d123)). A finger that scrolls leaves the box open; a press on another "?" only closes the first. A box shown
only because the mouse rests on the "?" stays outside the rule, so a quick click just after the pointer crosses a
"?" is not lost. Tested by `ordpar/tests/test_ordpar_browser_outside124.py`.

<a id="d125"></a>
### 125. The offline setting's line: the copy also makes pages load faster (2026-10-24)

**Status:** built, live since 25 October 2026.

The Offline setting's line said only that the copy lets a reader look words up without a connection. Robin asked
that it also say pages load faster, from his own use of both. The line was to state only what is true, so the
claim was timed once: from the copy, an article opened four to seven times faster than from the network, on a
computer and at phone speed; against an article the browser fetched a few minutes earlier, the gain is small. The
line now adds: "Pages also open faster, since they come from this device." Tested by
`ordpar/tests/test_ordpar_offline125.py`.

<a id="d126"></a>
### 126. The settings' words, self-contained and exact (2026-10-25)

**Status:** built, live since 25 October 2026.

Some setting hints were unclear without context: the small article's hint said "Open the whole article" without
saying how (click its headword). Ruled: every text on the Settings page, the "?" texts ([99](#d99)), the choices'
notes, the choices and the headings, is written so a reader with no context understands it: it says how to do what
it mentions and explains the site's own terms ("small article", the "+" on added examples, "subsense"). It says
exactly what the setting does, no more: "a shorter summary", not "a short summary"; "long", not "tall". New
settings are held to the same test.

"Small articles" gained a line under its heading: "The box that opens on the page when you click a word
linked to another article. It shows the word's senses only; click its headword for the whole article. A link
inside the box opens that article's own page." Tested by `ordpar/tests/test_ordpar_settingswords126.py` and
`ordpar/tests/test_ordpar_browser_settingswords126.py`.

<a id="d127"></a>
### 127. A link preview when an Ordpar page is shared (2026-10-25)

**Status:** built, live since 25 October 2026, with [128](#d128).

A link to ordpar.no shared on Facebook and the like showed as a plain link. Ruled: Open Graph tags on every page
(`og:title`, `og:description`, `og:url`, `og:image`, `og:type`, `og:site_name`), with `twitter:card` for X, built
in [128](#d128)'s build (`ordpar/sitegen/head.py`). One picture for the whole site, 1200 × 630, not one per article:
94,000 pictures would not fit beside the site. A search link (`#q=`) shows the home page's card, since the part
after `#` never reaches the sharing site.

Its variants included one with the name written "ordpar.no" and a
centred, stacked one (the icon, "ordpar.no", then "Norwegian–English dictionary"); Messenger was seen to show a
1200 × 630 picture cropped to about a square, and a stacked layout keeps everything in that crop. [156](#d156) weighed dropping some
of the tags to save space and kept them.

<a id="d128"></a>
### 128. Search engines: `noindex` lifted on the translated pages, fuller descriptions, a sitemap (2026-10-25)

**Status:** built, live since 25 October 2026; this reopened the `noindex` row of [110](#d110); the description
amended by [154](#d154).

About 72,000 of the 94,000 pages were untranslated, word for word the
articles ordbokene.no already shows, and a site mostly of copied text may be judged lower as a whole (an
understanding of how Google ranks, not checked against its documentation). Ruled: `noindex` lifted on the translated
pages and kept on the untranslated ones, lifted from a page by the build when it is translated. A translated page's
untranslated set phrases do not keep it out. The home page, About and Help are indexed; History, Favourites,
Settings, the 404 page and the privacy page are not. The build writes a sitemap of the indexable pages and a
`robots.txt`.

A page's title names the dictionary rather than the site, "abstrakt (adjective) — Norwegian–English dictionary",
since the site's name already shows beside it in a search result or a link card; the second half is read from the
language pair, so a second pair ([65](#d65)) needs no new rule. The homograph numeral stays only where two homographs
share a word class; a set phrase has no class.

The description: the page's summary glosses, always whole ("The glosses should never be cut to make space for the
definition"), then "Definition:" and the definitions, numbered when more than one, cut by whole definitions and
then at a word with "…", to 155 characters; where under 25 characters would be left, the glosses alone. An
untranslated page reads "Not yet in English: 1. …". The home page's line carries the count of translated articles,
written by the build; "free" and "no ads" were left out, since readers see that on arrival. The link-preview picture
of [127](#d127) is a 1200 × 630 PNG Robin made.

The site was registered with Google Search Console, proved by Google's ownership file in `ordpar/root/` (kept for
good, since Google re-checks it), and with Bing Webmaster Tools; both were given the sitemap. Built in
`ordpar/sitegen/describe.py` and `ordpar/sitegen/head.py`; tested by `ordpar/tests/test_ordpar_search128.py` and
`ordpar/tests/test_ordpar_browser_title128.py`.

<a id="d129"></a>
### 129. A History entry lost when a one-article search is left before its article arrives (2026-10-25)

**Status:** built, live since 25 October 2026.

A search that finds one translated article wrote its History entry only once the article's text had been fetched
(`recordSearch` in `ordpar/site/lookup.js`). A reader who left the page before then, on a slow connection, lost the
entry; it was reproduced at 300 ms of added delay.

Fixed as `recordOpened` already worked: the entry is written at once, and the text, when it comes, rewrites the same
entry. The list view had the same gap and was closed too. A row stored without its text still shows its gloss on the
History page and in the Recent rows, read from the index ([116](#d116)). Left as it was: a late fill can bring back an
entry the reader removed in the moment before the article arrived. Tested by
`ordpar/tests/test_ordpar_browser_history129.py` (under 400 ms of delay) and `ordpar/tests/test_ordpar_history88b.py`.

<a id="d130"></a>
### 130. The small article's header has no language tags of its own (2026-10-25)

**Status:** built, live since 25 October 2026; in the Anki deck, which runs the site's `ordpar/site/mini.js`, since
its update of 7 November 2026.

The small article's header (`header()` in `ordpar/site/mini.js`) is drawn at the click, before the article is
fetched, and carried no `lang` of its own. While the article loaded, the header inherited Norwegian from the line
around the link, so its English gloss was tagged Norwegian; once loaded it inherited English, so the Norwegian
headword was tagged English. Nothing a reader sees changed, but a screen reader read those words in the wrong
language.

The fix: the headword is tagged `nb` when it is the Norwegian word (`en` only for an English word with no gloss) and
every gloss `en`, so the header no longer depends on where it is drawn. Every other place that sets a Norwegian word
beside its English already tagged both halves. Tested by `ordpar/tests/test_ordpar_browser_minilang130.py`, which reads
the header while loading and once loaded. A real screen reader was not tried.

<a id="d131"></a>
### 131. The deck is released: what it asks of the site (2026-10-25)

**Status:** built, live since 26 October 2026; the `/coming/` page's later lines live the same day.

The Anki deck went live on AnkiWeb, so the site's public release ([110](#d110)) had happened. The
deck's code and the library changes it carried (among them a `headwords` key on every row) were merged into the
site's line of work, and the deck's list of requests for the site was taken up:

- **(1) The merge**, done before the next site build, which was the first on the merged library.
- **(2)** The About page's "Thanks" gained a paragraph naming the deck, *6000 Most Frequent Norwegian Words*, with its
  AnkiWeb links and its CC BY-SA 4.0 licence; the dictionary stays CC BY 4.0.
- **(3)** A "Contact" section at the foot of About (id `contact`) with Ordpar's post address, which the deck's support
  link points to. No footer link.
- **(4)** The deck's eye as a site setting under Examples, off by default: it hides the examples' English, on every
  article shown whole and in list rows, not in small articles; its name is the deck's own, "Hide the examples'
  English".
- **(5)** A page `/coming/`, "Coming to Ordpar", indexed and linked from About's "How far it has come": only work
  decided and waiting on something named, with what it waits on and no dates. Its items: search from English to
  Norwegian; audio; Ordpar in Norwegian (waiting for the site's first full version, 1.0); more
  languages; more example sentences, each checked by hand; and better English equivalents, every one reviewed and
  linked to its sense, which waits for the revision of the lexicographical principles the work builds on.
- **(6)** The one-line change the deck patches into its copy of `ordpar/site/mini.js` (so that a card's absolute
  links open small articles) was not made in the site; the deck still patches its own copy.

The deck relies on `ordpar/site/inflection.js` reading its paradigms from `<template>`s, since Anki's editor strips
scripts; the line stays, and a test pins it. The deck shows examples in both languages by default, superseding the
reveal of [49](#d49) and [111](#d111) for the deck. A search answered in place now shows its page's built title
([117](#d117)). Tested by `ordpar/tests/test_ordpar_site131.py` and the browser tests `eye131`,
`pages131`, `inflection131` and `tabtitle131`.

<a id="d132"></a>
### 132. The footer's note no longer says "not yet published" (2026-10-25)

**Status:** live since 25 October 2026.

The footer of every page read "Under development: Ordpar is not yet published, and its pages may change." Since the
deck's release ([131](#d131)) the site is public, so that was false. The note and the feedback form's link that follows
it stay, as [110](#d110) set them (the note until 1.0.0); only the sentence changed, to "Under development: Ordpar is
still being built, and its pages may change." It is `dev_note` in `ordpar/sitegen/strings.py`, pinned by
`ordpar/tests/test_ordpar_chrome63.py`.

<a id="d133"></a>
### 133. The site has no icon in search results (2026-10-26)

**Status:** built, live since 26 October 2026.

No page declared one, and
`/favicon.ico` answered 404; the app's icons were linked only from the web-app manifest. Google's documentation
asks for a `<link rel="icon">` in the home page's head, square, larger than 48 px
recommended, at a stable address. Now every page links `/site/icons/icon-192.png` as its icon: the home page for
Google, every page for the browser tab. Google promises no icon even so, and takes days or weeks to read the home page
again. Built in `ordpar/sitegen/head.py`; tested by `ordpar/tests/test_ordpar_favicon.py`.

<a id="d134"></a>
### 134. Audio before funding: a cheaper first tier (2026-10-26)

**Status:** taken up into a plan of its own, with its own decision log; its two voices replaced there by one, Amazon
Polly's Ida, for the whole dictionary, after Piper failed the listening test. Audio live on the site
since 2 November 2026.

Ruled in this entry:

- The headwords get audio from the start, with the example sentences: a public learners' dictionary uses synthetic
  speech for its headwords, and most Norwegian tone pairs are inflected forms rather than base forms.
- The audio goes in the deck and on the site.
- Two voices: Piper, a free voice model run on our own computer, for full coverage; and
  Amazon Polly, whose terms state no restriction on storing and reusing the output,
  for selected articles. Each clip
  records which voice made it. Cloudflare R2 was welcomed
  as the store for the files.
- Each deck article gets its headword and two or three sentences: going down the article in page order, an example is
  voiced when it is the first on the page to use a form of the word not yet voiced, so the voiced sentences sit as
  high on the page as they can and each shows another form (*er*, then *var* on *være*).

<a id="d136"></a>
### 136. A Help section on the settings, and presets on the settings page (2026-10-26)

**Status:** built, live since 26 October 2026; amended by [174](#d174) (new defaults for emphasis and the formula
lines, and a fourth preset, English emphasized).

Ruled:

- Three preset buttons at the top of Settings, **Default**, **Concise** and **For learners**. **(1)** A preset sets
  only the article settings; theme, accent colour, offline and the data settings stay as they are. **(2)** It locks
  nothing: a setting changed afterwards is simply the reader's own. The button whose settings match is shown pressed,
  none when none matches. **(3)** Default resets the article settings to their defaults. Each preset sets every
  article setting, its own choices plus the defaults for the rest.
- **Concise:** definitions in English only; two examples under each sense; the line for examples left out on; small
  articles shorter, at the article's spacing.
- **For learners:** the eye on ([131](#d131)); Norwegian emphasized; examples in both languages, the eye doing the
  hiding; subsenses and the short formula lines in both languages. Etymology, pronunciation and compound lists stay in
  English.
- The Help page's Settings section comes first, before Pronunciation (id `settings`), describing the presets and three
  more settings: inflection tables always shown, what a click opens, and the ordbokene layout.
- The existing "Reset settings" button resets every setting, the theme and colour too, so it stays beside Default with
  a line saying the difference.

The table of presets is `PRESETS` in `ordpar/site/settings.js`. Tested by `ordpar/tests/test_ordpar_presets136.py` and
`ordpar/tests/test_ordpar_browser_presets136.py`.

<a id="d137"></a>
### 137. The "translated" tag dropped from list rows (2026-10-26)

**Status:** built, live since 26 October 2026; amends [59](#d59) (5) and [93](#d93), which had kept the tag.

Ruled: "The 'Norwegian only' tag alone is enough." A row for an untranslated article keeps its *Norwegian only* tag; a
translated one has no tag. This applies everywhere a row is tagged, one style: a search's list rows and inflected-form
rows, the rows of Favourites and History (`ordpar/site/lookup.js`), and a word page's built rows
(`ordpar/sitegen/wordpages.py`). The colour that marks translated words in the suggestions and History's links stays,
since it is not a tag. Tested by `ordpar/tests/test_ordpar_tag137.py` and `ordpar/tests/test_ordpar_favourites89.py`.

<a id="d138"></a>
### 138. A second search made before the first is answered loses to the first (2026-10-26)

**Status:** built, live since 26 October 2026.

A search answered in place, on a word page (`answerInPlace` in `ordpar/site/lookup.js`) or the search page
(`ordpar/site/search.html`), first loads its query's index file and only then moves the address and draws, and nothing
checked whether a newer search had come in meanwhile. So a reader who searched again, or clicked a similar word or a
link, before the first search was answered ended on the earlier one: box, address, title and answer jumped back. The
wait on ordpar.no was 0.1 to 5 seconds for an index file not yet cached.

Fixed with a counter, as the drawing code already kept for its own answers: each search remembers its number and
drops its answer if a newer search, or Back or Forward, has started since. And the "Searching…" line is now shown, and
the old results cleared, at the moment a search is made, on a word page, the search page and the 404 page, instead of
the old answer staying on screen. Tested by `ordpar/tests/test_ordpar_browser_race138.py`.

<a id="d139"></a>
### 139. A small article inside a small article (2026-10-26)

**Status:** built, live since 27 October 2026; the setting's choices and default amended by [147](#d147).

Until now a link inside a small article kept its hover peek but a click opened the whole page; only one small article
was open at a time. Two ways: *stacked*
(a second box below the word, inside the first) and *in place* (the first box's content swaps to the new word, with a
"← word" line back). The site has a page for every article, so a nested small article always has something to show.

As a setting under Small articles, "A link inside a small article": *in place*, the default,
with no limit on nesting, each step back by the "← word" line or Escape; *stacked*, with its own limit, 1 to 5,
default 1; and *off*, the old behaviour. Each step keeps the box's and the page's scroll, restored on the way back.
The nested box hangs from the first box (`position: fixed`), since inside the word's line the page's rules would reach
its links. The Concise and For learners presets ([136](#d136)) set both keys. The Small articles intro lost its last
sentence ("A link inside the box opens that article's own page."), no longer true under the default.

The Anki deck runs the site's `mini.js`, so it could nest too, wherever a card carries the second-level target.
Nesting on the deck's cards is not built yet. Built in
`ordpar/site/mini.js` and `ordpar/site/settings.js`; tested by `ordpar/tests/test_ordpar_nestminis139.py` and
`ordpar/tests/test_ordpar_browser_nestminis139.py`.

<a id="d141"></a>
### 141. A hover peek inside a small article is cut off at the box's edge (2026-10-26)

**Status:** built, live since 27 October 2026, with [139](#d139).

A long hover peek inside a small article was clipped at the box's edge, because the box scrolls and the peek was
drawn inside it. Ruled: the small article keeps its size, and a peek inside it shows in full, extending beyond the
box. The peek is now drawn against the window, as the small article itself is ([69](#d69)), for first-level and
nested small articles alike; near the window's top it goes below its word. Built in `ordpar/site/mini.js`; tested by `ordpar/tests/test_ordpar_browser_peek141.py`.

<a id="d142"></a>
### 142. A page for using Ordpar elsewhere: More ways to use Ordpar (2026-10-26)

**Status:** built, live since 27 October 2026; its Definer step extended by [146](#d146); its Anki section moved
first by [178](#d178), live since 9 November 2026.

Help explains how to read the
dictionary; this page is about Ordpar elsewhere and will grow.

The page is "More ways to use Ordpar", at `/more/`, written in `ordpar/more.md` and drawn as Help is, indexed and in
the sitemap. It has three sections: the Definer pop-up (Definer's custom source, step by step, with links to the
browsers' add-on stores); the Anki deck (what Anki is, how to install it, the deck's links on AnkiWeb, AnkiDroid's
own list of shared decks); and the offline copy. Everything it describes is free, except AnkiMobile, which is noted
as paid. Its code lines are selected with one click (Copy buttons came with [146](#d146)).

Two links lead to it: a plain line on the home page, under Random word at the top of the area below the header,
shown only while nothing is searched and held to the header's column; and a footer link after Help on every page.
The home page's line "Type a Norwegian word to search the dictionary." was dropped everywhere it showed, as
superfluous. `/more/` is also among the offline copy's pages. Tested by
`ordpar/tests/test_ordpar_more142.py`, which pins the page's text to the approved draft, and
`ordpar/tests/test_ordpar_browser_more142.py`.

<a id="d143"></a>
### 143. The rows under "is an inflected form of", ordered by how common each word is (2026-10-26)

**Status:** built, live since 27 October 2026.

A search for an inflected form lists the headwords it belongs to, ordered purely by how common each word is, since similarity plays no part here. A headword's own
homographs, at the top of the search, keep their order.

The plain count of a headword's spelling misled where that spelling is also a common other word (*helt* put *hele*
before *hel*). Chosen: **(E2)**: each spelling's count in the National Library's book
n-grams ([55](#d55)) is shared out among the articles that have it, as headword or inflected form, in proportion to
their example sentences.

The articles are grouped by word (one spelling is one word), the words ordered by
their summed E2 figure, and within one word the list view's order holds (translated first, then verbs, then the
homograph number). *varer* gives *vare* III, IV and I, then *var* I. A short list of ruled exceptions,
`ordpar/form-order-overrides.tsv`, lifts a word where the figure gets it wrong (*løpet*, *ansatte*, *været*,
*giftet*, *les*, *varen*). So *et* and *ei*
list the numeral *en, én* II before the article *en* III, which was ruled to stay. The build writes each form's
order and every place that draws the rows keeps it. Tested by `ordpar/tests/test_ordpar_formorder143.py`.

<a id="d144"></a>
### 144. The similar headwords after a miss, with their word class and English (2026-10-27)

**Status:** built, live since 27 October 2026; extended to the English search by [148](#d148); headwords that
would repeat the page left out by [149](#d149).

After a search, Ordpar lists similar headwords. After a typo the list answers "which of these did I mean?", which a bare word cannot.

The new rows appear only after a search that finds nothing; a hit, by headword or inflected form,
keeps the bare list, where the rows were too much. Each similar word is one row, drawn by the suggestions' own row
code: the headword (in colour if translated), its word class, the English after a muted em dash, and
a thin line between rows. A word with several articles lists its homographs with their English and "+ N more" for
the rest. A row never mixes English and Norwegian: only where none of the word's articles is translated does it list
each homograph with its first Norwegian definition (*husk*: I evne til å huske · II huskende, gyngende bevegelse).
That rule also reaches the suggestions and History, in place of "N articles". A word that is only an inflected form
reads "*kjøpte*: inflected form of *kjøpe*".

In every one-line Norwegian definition (the similar rows, the list view, the suggestions, History, a word page's
built rows), a cross-reference's homograph or sense number in brackets is
dropped (*huske (III)* becomes *huske*): such numbers serve the links and add little in running text. They are
dropped where the line is made from the definition's markup (`ordpar/sitegen/article.py`), so a bracket that is the
definition's own words stays; the article keeps them. English one-line definitions keep theirs, since a "compare"
line points at one homograph and sense. So that a row costs little to load, the headword lists now carry each word's
article count, translated flag and word class. Tested by `ordpar/tests/test_ordpar_similar144.py` and
`ordpar/tests/test_ordpar_browser_similar144.py`.

<a id="d145"></a>
### 145. The test suite's run time (2026-10-27)

**Status:** steps 1 and 2 in force since 27 October 2026; step 3 not yet done.

Most of the suite's time went to the browser tests, run one file at
a time behind a lock, while the other files already ran eight at once. Three steps were approved:

**(1)** A build's full run of the suite goes through the deploy tool's runner, eight files at once, not file after
file.
A new command, `python ordpar/deploy.py test`, runs the suite alone against the built site, copying nothing.

**(2)** Browser test files run three at a time (`BROWSER_JOBS` in `ordpar/deploy.py`); each already has its own port
and browser profile.

**(3)** Later: the few slow browser files whose time is spent waiting, each still shown to fail on its fault.

Not chosen: one browser shared by every file, since a crash or leftover state would reach them all. Running three at
once exposed two tests that depended on timing; both were fixed in the tests, not the site. A width test read the
page before it could scroll and now waits for it (`ordpar/tests/browser/cardwidth.js`). A tab-title test failed at
random because the test server kept a queue of only 5 waiting connections and refused requests under load; the
queue was raised to 128 (`ordpar/tests/browser/harness.py`). The site's own fetch of the title, which has no retry,
was not changed.

<a id="d146"></a>
### 146. Settings in the address, for a pop-up dictionary such as Definer (2026-10-27)

**Status:** built, live since 28 October 2026.

Definer shows ordpar.no in a frame on another site, and browsers keep a frame's storage apart from the site's own,
so the pop-up never saw the reader's saved settings and always showed the defaults.

The site reads settings from the address, after `#` as the search is (so never sent to a server, [104](#d104)),
checks each against the settings table and ignores what it does not know. They hold for that tab's or pop-up's
visit, pages it opens included, and are never saved to the reader's own settings. A setting the reader changes on
that tab ends the visit's value for it, and Reset settings ends the whole visit. Every setting can travel, only those
that differ from the defaults, the theme and the usage-statistics opt-out included, with the search last:
`https://ordpar.no/bm-en/#theme=dark&defs=en&exlimit=3&q={{str}}`.

The address is copied in two places by one code: in the Definer step on `/more/` ([142](#d142)), shown filled from
the saved settings with a Copy button (both of that page's code lines got one), and at the bottom of Settings, "Copy
the address for a pop-up dictionary". On a phone the address may break mid-word; left as it is, since the Copy button
serves. Tested by `ordpar/tests/test_ordpar_settingsaddr146.py` and
`ordpar/tests/test_ordpar_browser_settingsaddr146.py`.

<a id="d147"></a>
### 147. Nested small articles: a second box, then the same box, as the default (2026-10-29)

**Status:** built, live since 29 October 2026; amends [139](#d139).

The setting "A link inside a small article" has four choices, the default listed first ([107](#d107)): "Opens its
small article in a second box; a link there changes that box" (new, the default); "Opens its small article in the
same box"; "Opens each small article in a box of its own"; "Opens its whole article". Under the default, a link in
the small article opened from the page opens a second box, and a link inside that second box changes it in place,
with a line such as "← skip" at its top to go back. The limit on second boxes, and its setting, went: no choice has a
limit, and a click outside every box closes them all. Escape steps back in the deepest box, then closes it; a click
inside the first box closes the second. A reader who had chosen a box per link keeps it, now without a limit. The
presets Concise and For learners ([136](#d136)) follow the new default.

Robin added a rule for every choice: "interacting inside the small article boxes should never scroll the main
window". Nothing done in a box (a link, the back line, Escape, closing) moves the page; a step back restores only the
box's own scroll. The Anki deck runs the site's `ordpar/site/mini.js`. A box cut off at the window's bottom was fixed later, in [165](#d165). Tested by
`ordpar/tests/test_ordpar_nestminis147.py` and `ordpar/tests/test_ordpar_browser_nestminis147.py`.

<a id="d148"></a>
### 148. The English–Norwegian search (2026-10-29)

**Status:** built, live since 30 October 2026; builds on [17](#d17); item 11's Random word amended by
[155](#d155).

The English search ruled in [17](#d17) was built: a switch under the search box; switched on, a query is matched
against the English equivalents in the summary glosses, not the Norwegian headwords. As 17 ruled, the index is the
glosses, not the definitions, and a miss says the word is not yet among our equivalents, not that Norwegian lacks
one. As built:

**item 1** The index: the translated articles with a summary gloss, each unit split into its equivalents; only exact
equivalents are found, and units that are explanations (all in brackets) are not indexed. British and American
spellings are mapped onto each other. One file per first letter, so a search costs one request.

**item 2** The switch, "Search English words", is drawn by script, not written into the pages, which would rebuild
every page and make every offline copy download again. It stays on after an English search and is remembered on the
device, since the switch is prominent.

**item 3** The address: `/bm-en/#en=house`.

**item 4** The suggestions: one row per English word, on the left where the reader types, semibold in the text
colour; its Norwegian headwords on the right, semibold in the accent red, the top-ranked first, each with its word
class while all fit (the classes go first when the list is cut to "+ N more"). Each headword shows its first spelling
([150](#d150)), with a numeral only where the row shows two words of the same form (*light*: *lys* I · *lys* II).
Ordered as the Norwegian suggestions are. The row-spacing setting applies; no new setting.

**item 5** The results: always the list view, the site's own rows with the Norwegian on the left; the whole summary
gloss on the line below in normal text, the searched equivalent in bold, a deliberate exception to [116](#d116). An
English word matching one article opens that article.

**item 6** The order: equivalents in a gloss's first two units as one tier, by the Norwegian word's frequency band,
then the later units by band. Unit first put *gå* third for *go*; frequency first put a machine's *gå* first for
*run*. This compromise gives *gå* for *go* and *løpe* for *run*.

**item 7** Similar English words after every search, as in [144](#d144): rows after a miss, a bare list after a hit.
First longer equivalents holding the word ("go swimming": *bade*) and words sharing its stem (*swim*: *svømme*), then
words spelled alike, also from other first letters. The stem rule drops -er (it gave *runner* for *running*) and has
a small table of irregular verbs. [149](#d149) applies.

**item 8** A miss: "The English search looks through the English equivalents of the {n} articles that have them so
far, {p} % of the dictionary. A word missing here may still have a Norwegian equivalent." ({n} counts the glossed
articles, fewer than the translated ones.)

**item 9** History and Recent store an English search marked as English and draw it unmarked, in the English manner,
linking to `#en=`; the tab reads "house — Ordpar". English searches and chosen suggestions are sent for the usage
counts as Norwegian ones are, marked English, and the privacy page says so.

**item 10** It shows wherever the search box does, the offline copy included. `/coming/` gained a "Built" section,
newest first, where items move as they land.

**item 11** Not touched: Random word, which stays Norwegian and switches the box back (amended by [155](#d155):
with the switch on, it now picks an English word); the Anki deck.

Tested by `ordpar/tests/test_ordpar_english148.py` and `ordpar/tests/test_ordpar_browser_english148.py`.

<a id="d149"></a>
### 149. Similar headwords that would only repeat the page (2026-10-29)

**Status:** built, live since 30 October 2026.

The similar headwords after a search sometimes repeated what the page already showed: *selvlaget*, one article with
six spellings, listed its own spellings *selvlaga* and *selvlagd*; *rett*, whose page shows "is an inflected form
of" *rette* II, listed *rette*. Ruled: a similar headword is listed only if its own search would show an article not
already on the page, either among the results (full or list view) or among the "is an inflected form of" rows.
*selvlagd* and *selvlaga* go; *rette* stays, since its search also shows the noun *rette* I. The places freed go to
the next similar words, so the list keeps five where there are five.

It costs no extra request: the headword lists give each form the number of articles it heads, and the page knows
the spellings of every article it shows, so a candidate is dropped when the articles on the page that carry it are
as many as it heads. The English search's similar words follow the same rule ([148](#d148)). Tested by
`ordpar/tests/test_ordpar_browser_similar149.py`.

<a id="d150"></a>
### 150. The Norwegian suggestions show the spelling typed (2026-10-29)

**Status:** built, live since 30 October 2026.

A suggestion row showed every spelling of a word: "selv" suggested *selvsagt, sjølsagt*. Ordbokene.no's suggestions
listed each spelling as an entry of its own and showed only those matching what was typed.

Ruled, as one rule for both search directions: a compact row shows one spelling of a word, while the article and the
list view keep the full headword line. In the Norwegian suggestions that is the spelling matching what was typed
("selv" gives *selvsagt*, "sjøl" gives *sjølsagt*); where the typing matches more than one spelling, the first in our
lemma order ([93](#d93)). In the English search it is the first spelling ([148](#d148)). Ordpar keeps one row per
word rather than one per spelling, so the word class and the English show once. Tested by
`ordpar/tests/test_ordpar_browser_suggest150.py`.

<a id="d151"></a>
### 151. The compound lists' labels, closer to ordbokene's own words (2026-10-29)

**Status:** built, live since 30 October 2026.

Ordbokene's compound lists open with a Norwegian intro, such as "som etterledd i ord som". Ordpar's English label was
derived from it by a substring test, giving one of three labels: "Used as a suffix in:", "Used as a prefix in:" or
"Also found in compounds:". Measured over Bokmålsordboka's data, that lost meaning: three
misspelt intros fell to the third label, "førsteledd" was not caught as a prefix, the third label stood for nine
different intros, and "etterledd i fuglenavn som" lost its "bird names".

Ruled: each Norwegian intro gets an English label that says what ordbokene's says. "som etterledd i ord som" (94 %
of the lists) reads "as a suffix in words such as:", "i ord som" "in words such as:", "for eksempel" "for example:",
"også i sammensetninger som" "also in compounds such as:", and so on for every intro found; a list with no intro gets
no label. "Suffix" and "prefix" are kept for *etterledd* and *forledd*, as the terms readers know, though strictly
they are a compound's last and first element. The labels start with a small letter, as the Norwegian intros do. Proper names keep their
capitals (*Nato*, *NRK*). The site already lowered them when drawing the page ([47](#d47)); now they are stored so.

Each compound block now stores the intro itself, so the Norwegian label shows the text as corrected. The table is in
`scripts/derive.py` (`COMP_INTRO_LABELS`); an intro it does not know gets "in words such as:" and an advisory, and a
test fails on any intro in the data that has no label, so a new intro from ordbokene stops a deploy until it has one.
Nine misspelt intros (*klinikk*, *reim*, *skriv*, then six more) were corrected as source normalizations, each checked
against the live dictionary first and logged for ordbokene; the corrected pages carry the correction note
([106](#d106)). Tested by
`ordpar/tests/test_ordpar_complabels151.py` and `ordpar/tests/test_ordpar_changenotice106.py`.

<a id="d152"></a>
### 152. Norwegian only: the articles in Norwegian, with Ordpar's features (2026-10-30)

**Status:** built, live since 31 October 2026.

Because a publicly funded service may report its
reach, and readers who stay on Ordpar do not count there, the credit and links to ordbokene stay prominent. The text is
the copy Ordpar translated, with its corrections, and some articles have changed at ordbokene since; the setting's
words say so. The English behind a tap was declined: the point is a plain article.

**The layer.** *Norwegian only* is off by default. It is a layer over the reader's own settings, not a preset: off,
the reader's settings are as they were, and the stored values are never written. It changes the language only, not
the layout or the look. It shows the word class and the inflection tables' words in Norwegian, hides the "Eng.
phrase" lines, and keeps Ordpar's added examples.

**The icon.** An icon in the header switches the layer for the whole site and is remembered on the device, as a
light/dark switch is; it and the setting in Settings are one state. A setting can hide it; shown is the default. In
the Definer pop-up, where the header is hidden (`ordpar/more.md`), the icon shows beside the headword and holds for
that pop-up only. While the layer is on, the examples' eye is hidden: there is no English to reveal.

**English equivalents.** Inside the layer, one setting shows or hides the English equivalents everywhere at once:
summary glosses, search suggestions, hover peeks, History and Favourites. Hidden is the default; it also removes the
"Search English words" switch, and Random word draws in Norwegian ([155](#d155)). With them hidden, the rows' right
side shows the first Norwegian definition (the default) or nothing, and the hover peeks show nothing (the default, as
ordbokene) or the Norwegian definition.

**The labels.** A separate setting, "Labels inside an article", in Article's Language settings and set by no preset,
gives the headings, buttons, word class and table words in English (the default) or Norwegian, in ordbokene's words
where its pages show them ("Vis bøyning"). While *Norwegian only* is on, every label inside
the article is Norwegian. The buttons at an article's foot ("Copy link", "Share") stay English: they belong to the
site's interface language. The Norwegian form labels follow the order of Bokmålsordboka's own text,
definiteness, "form", then number ("ubestemt form flertall"), and use ordbokene's "gradbøying", "forkorting" and "i
sammensetning"; a compound prefix is "compound prefix" / "i sammensetning" everywhere.

Every copy the default settings hide carries `data-nosnippet`, the existing "Se:" and compound-label pairs too
([154](#d154)). Tested by
`ordpar/tests/test_ordpar_nbonly152.py`, `ordpar/tests/test_ordpar_nblabels152.py` and
`ordpar/tests/test_ordpar_browser_nbonly152.py`.

<a id="d153"></a>
### 153. The "Se:" lines back on set phrases' own articles (2026-10-30)

**Status:** built, live on the site since 31 October 2026.

On ordbokene.no, a set phrase's own article has a "Se:" line naming the words it is built from. Ordpar had dropped
these lines because they were being given to translators though nothing in them
needs translating: their links get English as the summary glosses of the words they point to are written.

Ruled: the line comes back, derived mechanically with nothing written by hand, and only on the set phrase's own
article, never on a set phrase printed inside its headword's article, as on ordbokene. It is stored as a field of its
own (`see`), Norwegian with no English slot, so no article gains an untranslated part. It is drawn as a formula line
after the definition and before the examples: "see:", or ordbokene's "Se:" under Norwegian formula lines. Its links
peek as on a *Norwegian only* article ([119](#d119)): a target with summary glosses shows them, an untranslated one
shows none. The line is not shown in a small article (a switch in `ordpar/site/mini.js`, off by default). Ordbokene
puts ";" before the line; Ordpar draws it on a line of its own after the English, where a ";" would end the English,
so none is added.

Tested by `ordpar/tests/test_ordpar_selines153.py`.

<a id="d154"></a>
### 154. Google's snippets: the hidden labels kept out, spaces between lines, the headword in the description (2026-10-31)

**Status:** built, live since 31 October 2026.

Google's results showed some Ordpar pages with snippets that ran words together ("kan hendeperhaps, maybe"), put
the Norwegian before the English, or read "homograph 3" beside the numeral "III". The pages' own descriptions were
right; Google had built its snippets from the page text instead, which it does when it judges that text a better
fit. The faults were in the markup as Google reads it: a link followed by its hidden hover label, a screen reader's
label beside a numeral hidden from screen readers, and elements with no space between them.

**(1)** every hover label and screen-reader label the site writes carries
`data-nosnippet`, so Google leaves it out of snippets; only the header's search label is left without it, since a
`label` cannot carry it. Google's documentation says the attribute is honoured only on
`span`, `div` and `section`, and only when the element carries it from the start, not when a script adds it later;
so it is in the markup, or set when a script first makes the element. **(2)** Whitespace between separate lines in
the markup, with no visible change. **(3)** Every description begins with the headword (its first spelling, with
its numeral where the title has one), so that Google may take ours more often: our descriptions had never contained
the headword, which may be one reason it passed them over. None of this governs what Google shows; it changes only after Google crawls the pages again.
Tested by `ordpar/tests/test_ordpar_snippets154.py` and `ordpar/tests/test_ordpar_browser_snippets154.py`.

<a id="d155"></a>
### 155. Random word in English when "Search English words" is on (2026-10-31)

**Status:** built, live since 31 October 2026.

With
the switch on, Random word draws an English word and opens its English search, exactly as if the word had been typed
and picked from the suggestions (the English results list, or the article itself where the word has one match);
with it off, it works as before ([115](#d115)). The pool is every English word the English suggestions can offer,
each equally likely.

Two keys that cannot be searched since [148](#d148) were left out.
Rather than ship a word list, a small index file holds only the number of words in each letter's file; one draw
below the total picks the file and the word, so every word is equally likely. A drawn word is kept out of History,
as in [115](#d115), and the search box stays in English. Tested by `ordpar/tests/test_ordpar_random155.py` and
`ordpar/tests/test_ordpar_browser_random155.py`.

<a id="d156"></a>
### 156. Hosting beyond GitHub Pages' 1 GB (2026-10-31)

**Status:** ruled, not built; the build is left for later.

GitHub Pages publishes a site of at most 1 GB.
A measurement projected the whole dictionary, translated, at about 1,097 MB: over the limit. The article pages barely
grow as they are translated; the growth is in the word pages.

A second measurement, with the audio added, put the projection at about 1,124 MB and sized the savings that change
nothing a reader, a search engine or a link preview sees: shorter class names, attribute quotes left out where HTML
needs none, optional end tags and line breaks dropped, the audio's names stored more compactly. Together about
205 MB, to about 919 MB. Ruled: **no saving a reader can see**. Drawing the header and footer, or the Norwegian label
copies, by script is out, and so is any change to what a link preview shows. Dropping the duplicated preview tags
(`og:title`, `og:description`, `og:url`) was to be taken only if every platform fell back without them; Signal takes a preview's description only from `og:description`, and several platforms document
no fallback, so the three tags stay. Signal also needs the quotes on those tags, so the head's tags stay quoted. The savings are
to be built later, as one change to the page frame.

<a id="d157"></a>
### 157. The small article's shadow over the page's text, in dark mode (2026-11-01)

**Status:** built, live since 1 November 2026.

In dark mode the shadow under an open small article hardly showed on the page's text, which lost some of the
three-dimensional effect. The shadow was already drawn over the text, but faint: it dimmed the text 15 % next to
the box and nothing past about 20 px. At night the box was also darker than the card beneath it, so it looked sunk
rather than raised.

**At night**, a deeper shadow (`0 1px 3px rgba(0,0,0,.5), 0 10px 36px 4px rgba(0,0,0,.8)`) and
a lighter box, #2c2629 with border #3e3439; **by day**, a slightly stronger shadow
(`0 1px 3px rgba(60,20,40,.12), 0 8px 28px rgba(60,20,40,.2)`), the box's colour unchanged; a nested small article
gets the same shadow as the first; the page is not dimmed under an open box. The night page background became
#1b1819 and the article card and header #242021. The card and the header share one colour with the result cards,
settings panels, menus and dialogs (`--ordpar-surface`), so all of them follow. The Anki deck's stylesheet is built
from the site's and follows too; the
deck's own night fallback was changed to match. Tested by `ordpar/tests/test_ordpar_minishadow157.py`.

<a id="d158"></a>
### 158. List view when a search also finds inflected forms, as the new default (2026-11-01)

**Status:** built, live since 1 November 2026.

Under the list view setting ([71](#d71)), the default opened the article whenever a search found one article as a
headword; any "is an inflected form of" rows sat at the foot of the page, below the article.

A fourth value, "When there are several articles, or inflected forms", the default and listed
first. It shows the list for several headword hits, or for one with any inflected-form hit; the article opens only
for one headword hit and no inflected-form hit. The other three values are unchanged. Measured before the change:
of 21,291 words whose search finds one article, 1,321 (6 %) also find inflected forms and now open as the list,
among them *hus*, *alle* and *andre*. The cost is one more click on those words, against finding the inflected
forms at once. The rule applies wherever a search opens: the search page, a shared address, word pages, Random word
and History. Search engines see no change. The Definer address on "More ways to use Ordpar" keeps carrying the reader's own
settings ([146](#d146)). Tested by `ordpar/tests/test_ordpar_listview158.py` and
`ordpar/tests/test_ordpar_browser_listview158.py`.

<a id="d159"></a>
### 159. The audio on the site: Ida's clips from R2, play controls and a speed setting (2026-11-01)

**Status:** built, live since 2 November 2026; when the names are fetched, amended by [170](#d170).

The project's audio work recorded about 400,000 MP3 clips in Ida, Amazon Polly's synthetic Norwegian voice (every
headword, example and definition line, and the inflection tables of the core vocabulary and every irregular word),
kept in a private Cloudflare R2 bucket. This entry brings them to the site.

**Serving.** A small Cloudflare Worker (`ordpar/audio-worker/`) at `ordpar-audio.ordpar.workers.dev` serves the
clips read-only: only `GET` and `HEAD` of a clip's name reach the bucket, which is never listed; byte ranges and a
year-long cache are supported, cross-origin access is granted to ordpar.no only, and its logs are switched off.

**Which texts play.** A clip's name is derived from the text the page shows; the build marks each voiced text whose
clip exists (`ordpar/sitegen/audio.py`), and a missing clip means no button. The names reach the
browser in 225 files keyed by the text itself, not in every page and not in the offline copy: about 2 % of the 1 GB
target of [156](#d156), and no reliance on the order of elements on the page. The public build takes the names file
as an argument and does not depend on the audio tooling.

**The controls.** A small sound icon after every voiced text: the headword, each example, each definition line, and
each form in a table. An icon was preferred over a clickable text because it is obvious and works the same on a
phone. A table cell plays its own form alone, since a form is practised in isolation. A
speaker with two waves, 1 rem, after the text, with an unseen 24 px tap area; the muted grey faded halfway toward
the card; on hover the text colour, by day and by night; while playing, the accent colour; a second press stops it.
By day the faded colour is under the usual 3:1 contrast for a control; it was kept as chosen.

**Speed.** A setting with two choices, "As recorded" (the default) and "90%"; slower steps were dropped because the
voice distorts at 80 % and below.

**Screen readers.** Every icon is a real button, "Play" / "Spill av", reachable by keyboard. Hiding the icons from
screen readers was rejected: it would take the audio from the readers who may need it most, and a control hidden
from them must also leave the tab order.

**Loading early.** A clip loads when the pointer rests on its icon for 150 ms, as links do. As built, opening an
article also fetched the names file; since [170](#d170) it is fetched only when a clip is wanted, and nothing loads
early when the reader's Loading setting waits for a click.

Help, the About page and the privacy page gained short texts on the synthetic voice and on Cloudflare. Tested by
`ordpar/tests/test_ordpar_audio159.py`, `ordpar/tests/test_ordpar_browser_audio159.py` and the Worker's own tests.

<a id="d160"></a>
### 160. Sound on the headword's other spellings (2026-11-02)

**Status:** built, live since 2 November 2026; the later lemma groups since 4 November 2026.

Only the first spelling of a headword line had a sound icon (*hjem* in "hjem, heim"). The audio had voiced every
spelling from the start. Ruled: every spelling of the headword line gets its
icon.

In a looked-up article (word and form pages, search results, the list's opened rows, History, Favourites) the
headword line was one link, and an icon cannot sit inside a link. The link added little and made it easy to miss the icon and leave the page: every
looked-up article already ends with an "Article page" link. Ruled: **in a looked-up article the headword line is no
link**, and each spelling's icon follows it, as on the article page. Ordbokene.no's results do not link their
headwords either; they have only an "Article page" link. The Anki deck keeps its headword
link to ordpar.no, since on a card it is the way to the article. The "Article page" link was itself removed later
([168](#d168)); Copy link and Share give the article's address.

A headword's second lemma group, with its own gender line (*forutanelse* /
*forutaning*), had no icon, because only the first heading line was scanned. Every lemma group is now marked. Tested by `ordpar/tests/test_ordpar_audio159.py` and `ordpar/tests/test_ordpar_browser_audio159.py`.

<a id="d161"></a>
### 161. What each preset does, on the settings page (2026-11-02)

**Status:** built, live since 2 November 2026; amended by [174](#d174) (a fourth preset, new defaults).

The settings page's Presets box said only that each preset sets all the article settings at once. One "?" after the heading "Presets", using the settings page's own hint
([99](#d99)), rather than a "?" on each of the three buttons, which would crowd the row on a phone. It opens one
line per preset and a link to Help's Settings section:

- **Default:** Ordpar as it starts: each definition in English and Norwegian, the English in full colour; every
  example with its English; small articles in full.
- **Concise:** for when you only need the meaning: each definition in English only; the first two examples under
  each sense and set phrase, with a line to show the rest; small articles a little shorter. An article not yet
  translated still shows its Norwegian.
- **For learners:** for reading the Norwegian first: an eye beside the headword hides the examples' English; in
  each definition the Norwegian in full colour and the English faded; short formula lines in both languages.

The button is named "About the presets". Since [174](#d174) the defaults put
the Norwegian first, a fourth preset, "English emphasized", keeps the old ones, and the Default line was reworded
and a line added for the new preset. Tested by `ordpar/tests/test_ordpar_presets136.py` and
`ordpar/tests/test_ordpar_browser_presets136.py`.

<a id="d162"></a>
### 162. Two inflection-table drawings unlike ordbokene's (2026-11-02)

**Status:** ruled 4 November 2026; (1) built, live since 4 November 2026; (2) ours kept, a recorded divergence.

A comparison of Ordpar's wide inflection tables with the tables ordbokene.no renders found two ways
of drawing that differ.

**(1) An empty comparison row.** For an adjective with two paradigms, one with comparison forms and one without,
ordbokene.no's comparison table has only the row with forms; Ordpar drew an empty row for the other (15 articles,
among them *ettertrykkelig* and *uredd*). Ruled: the empty row is not drawn, as on ordbokene.no; an empty row tells
the reader nothing, and ordbokene.no is the baseline.

**(2) The first column in a later gender group.** Where a noun has two gender groups and two rows of a group share
the indefinite singular, ordbokene.no joins the shared cell in the first group ("en ku" over two rows) but repeats it
on each row of a later group ("ei/en ku", "ei/en ku"), while it still joins that group's other shared cells ("kua").
This affects 49 articles. Ordpar joins it in every group. Ruled: ours is kept. The
drawing on ordbokene.no is not consistent with itself, so it reads as a side effect rather than a choice, and
ordbokene.no is a tiebreaker, not something to copy blindly. The difference is recorded in `docs/divergences.md`.

The change was written from ordbokene.no's rendered tables only. The Anki deck ships the same `ordpar/site/inflection.js`
and follows at its next update. Tested by `ordpar/tests/test_ordpar_inflection40.py`.

<a id="d163"></a>
### 163. Three articles with no headword (2026-11-04)

**Status:** built, live since 4 November 2026.

Three articles in Bokmålsordboka's data have no headword at all (134445, 136424, 136509). Ordpar built a page for
each, with an empty heading. On ordbokene.no all three gave an error page. On Ordpar
none was translated, in the sitemap or findable by search, and no page linked to them. Ruled: **no page for an article without
a headword**, as ordbokene.no has none. Writing a headword of our own (*v/*, *u.å.*) was rejected as a guess at a form
the data does not give.

As built, an article gets no page only when neither the data nor the project's own translated row gives a headword:
three set phrases (*på tide*, *til topps*, *til vanns*) also have none in the data but have it in their translated
rows, and keep their pages. About's article count leaves out the three without one. Tested by
`ordpar/tests/test_ordpar_noheadword163.py`.

<a id="d164"></a>
### 164. The search heading and the header's tagline (2026-11-04)

**Status:** (1) built, live since 4 November 2026; (2) kept as it is, to be raised again in the look work ([75](#d75)).

On a search, the header read "Ordpar" over its tagline "Norwegian–English dictionary", and the results opened with
"Bokmål–English dictionary".

**(1) The heading.** Ruled: the results heading reads "Norwegian–English dictionary", in the Norwegian and the
English search alike. It had followed ordbokene.no's results heading, which names "Bokmål"
because that site shows two dictionaries side by side; everywhere else Ordpar already calls itself "Norwegian–English dictionary". Bokmål is
named on About and in the footer. Should a second Norwegian source come, the heading would name each again.

**(2) The tagline.** On a search page the same words now stand twice, but on the home page the tagline is the only
line telling a first visitor what the site is. Ruled: the
tagline stays as it is, on every page, for now, and is to be taken up again in the look work. Tested by
`ordpar/tests/test_ordpar_results59.py`.

<a id="d165"></a>
### 165. A nested small article cut off at the window's bottom (2026-11-04)

**Status:** built, live since 4 November 2026.

A small article opened inside another, from a word near the bottom of the window, ran past the window's edge, and the
page could not be scrolled to it. The nested box is fixed to the window below its word, and its height had a floor
of 160 px, so with less room it ran off-screen.

**A nested box opens above its word when the room below is short and there is more room above**,
never taller than the room it has (scrolling inside itself), and the 160 px floor is gone. This mends both nested
styles; going back to *in place* as the default would have left them with the fault and undone [147](#d147)'s
default. *In place* stays an option.

Robin added a rule: "the minis should not change position when you scroll the main window". So a
nested box's side, above or below, is chosen when it opens (or when its content arrives, a step is taken in it, or
the window is resized) and kept while the page or a box scrolls. Tested by
`ordpar/tests/test_ordpar_browser_nestabove165.py`.

<a id="d166"></a>
### 166. A "Suggest a correction" button on every article (2026-11-05)

**Status:** built, live since 5 November 2026; the question of a per-address limit settled 6 November 2026.

A button at the foot of each article where a reader can write, in free text, about a mistake in the
translation, the audio or the Norwegian text. A report is sent only when the reader writes it and presses Send,
unlike the page-view counting, which stays off. Ruled: the reports go to Ordpar's own receiver, a `POST /report` on
the Cloudflare Worker of [104](#d104) (`ordpar/receiver/`), with no third party and no captcha.

A pill "Suggest a correction" after Share, opening a
plain form under the row (free text, an optional category, an optional reply address, an optional "Name to credit"),
drawn by script. The reply address is deleted when the report is dealt with. Nothing from the reader's IP address
or browser name is used: junk is kept out by a hidden trap field and a cap of 30 reports an hour from everyone
together.

On a phone, Copy link is hidden where Share is shown (the share sheet has its own copy), so the row keeps one line;
ordbokene.no drops its "copy link" button on narrow screens.
`/bm-en/<id>/#report` opens an article's form on arrival, so the Anki deck can link each card to it; no mark of
where a report came from is sent.

Robin reads the reports on a local page that is not part of the site, marks them done or fixed, and can copy one, without the address or the name, to discuss with an AI assistant, as the privacy page says. A report may be used directly to make a fix: Ordpar takes the sending of a report as leave to use it for that, which is what the form is for. A reader who wants credit for it gives a name to credit, and one who does not stays anonymous, so there is no separate permission line under the form. The page `/thanks/` counts the reports and the fixes they led to and names only readers who asked to
be named (`ordpar/thanks.md`). The build refuses to turn reports on without the privacy page, and the deploy refuses
them without its section on reporting a mistake (`ordpar/privacy.md`).

<a id="d167"></a>
### 167. Accent colour: Oxblood out, Burnt orange in (2026-11-05)

**Status:** built, live since 5 November 2026.

Oxblood was barely
distinguishable from Wine, the default (contrast on white 11.4:1 against 12.1:1, the hues a few degrees apart). The
accent paints text and the Send button, so a new colour must read as text on white at 4.5:1 or more (WCAG AA);
bright oranges fail, burnt oranges pass.

Chosen: **Burnt orange `#b13a0b`**, the lab's `#c2410c` with its lightness lowered to 37%, in place of Oxblood,
between Wine and ordbokene's maroon (`ordpar/sitegen/colours.py`). It gives 5.96:1 as text on the page and 5.08:1 on
the idiom tag's pink pill. At night it takes the computed tint `#e3c3b7`,
a greyish peach close to Wine's night pink; a hand-set night colour was left open. A reader who had stored Oxblood
gets the default, Wine.

<a id="d168"></a>
### 168. No "Article page" link under a result (2026-11-05)

**Status:** built, live since 6 November 2026 (first on phones only, then everywhere).

After [166](#d166)'s button, the row under an article on a word page, in search results, History and Favourites
still wrapped on a phone because of its "Article page" link. Copy link and Share already use the article page's
address, so the link is not needed for sharing. Removed everywhere;
on a computer, Copy link gives the address. This is a divergence from ordbokene.no's results, with its row in
`docs/divergences.md`.

Kept: the hidden link in the word pages' static list rows (`ordpar/sitegen/wordpages.py`), the fallback without
JavaScript and the link search engines follow to the article pages. Tested by
`ordpar/tests/test_ordpar_browser_report166.py` (no link at 320, 360 and 390 px or on a computer).

<a id="d169"></a>
### 169. Two follow-ups to the report button: what Cloudflare keeps, and undoing a fix (2026-11-06)

**Status:** built; (a) live since 6 November 2026, (b) on the local reading page, which is not part of the site.

**(a)** Ordpar's Workers keep no logs and have Cloudflare's request log turned off, but Cloudflare itself keeps records of
requests, with the IP address, country, time and the recording asked for, and so the word; the account can see
these records for 32 days, and Cloudflare documents no way to shorten that. The full statement of what Cloudflare keeps moves to the privacy page's Audio section,
which every build shows; it says the records can be seen for 32 days and "We do not copy or keep them". The section
on where data is kept points to it, and the section on reporting a mistake says the receiver's requests are recorded
the same way (`ordpar/privacy.md`).

**(b)** On the local reading page for reports, a fix marked by mistake could not be taken off. A "Remove" beside
each fix, after a confirm, now deletes the whole fix and its names; the reports behind it stay closed, and nothing
is sent to the receiver. Tested by `ordpar/tests/test_ordpar_thanks166.py`.

<a id="d170"></a>
### 170. What a reader looks up, and who can see it (2026-11-06)

**Status:** built, live since 6 November 2026.

The words a reader looks up, linked to an IP address, can be sensitive. Without the offline copy, GitHub can tell which words and articles a reader looks
up: a search fetches the index by its first letters, the articles shown, and often the word's own page
(`/bm-en/hus/`). Changing the address scheme would not hide that, and would cost the clean word address of
[117](#d117), so it was dropped. The privacy page now says so plainly.

(1) **the offline copy is named as the way to look words up unseen**, in a paragraph near the top
of the privacy page, so a privacy-minded reader finds it; only a recording played, and the list
of recordings it is found in, is still fetched. The paragraph is shown only while the counting is off. (2) **The
sound icon follows the Loading setting** ([92](#d92)): under "When its link is clicked" nothing is fetched before a press, a
recording included, and the early connection to the audio server is skipped. (3) **Word pages from the copy**: with
the copy kept, a word page such as `/bm-en/hus/` is answered from the device (`ordpar/root/sw.js`).

Opening an article fetched its block's list of recordings from GitHub ([159](#d159)), which named
the block of 500 articles it was in. The list is now fetched only when a recording is wanted; the inflection tables,
which needed it to draw their icons, get their sound marks at build time instead (`ordpar/sitegen/audio.py`), adding
0.3% to the pages. Changing how recordings are named, so that no list is needed, was left for later. Tested by
`ordpar/tests/test_ordpar_browser_soundrest170.py`, `ordpar/tests/test_ordpar_audio159.py` and the privacy tests.

<a id="d171"></a>
### 171. The "Could not find" line: NAOB and Norsk Ordbok (2026-11-06)

**Status:** built, live since 6 November 2026.

Under "Could not find …", the search page gave as one possible reason "an article whose translation we have not
reached yet", which was untrue: every Bokmål article is on Ordpar, in Norwegian where it is not yet translated.
Ruled: NAOB first, since Ordpar is Bokmål only, and each name a link that opens that
dictionary's search for the reader's word, in a new tab, with nothing sent unless the reader clicks. "It may be a misspelling or a compound. Try the larger dictionaries NAOB (for Bokmål) and
Norsk Ordbok (for dialect words and Nynorsk), both in Norwegian." The links are drawn in `ordpar/site/lookup.js`
(`https://naob.no/søk/<word>`, `https://norsk-ordbok.no/nno/no/<word>`); a Norsk Ordbok link for a word with
æ, ø or å was checked by hand on the live site. Tested by `ordpar/tests/test_ordpar_missline171.py`.

<a id="d172"></a>
### 172. The About page: the recordings under CC BY 4.0, and the data on request (2026-11-07)

**Status:** built, live since 7 November 2026.

Neither the site nor the licence notes said under what terms the recordings (Amazon Polly's synthetic voice) could
be reused. Amazon's service terms say that the output of its AI services, Polly among them,
is the customer's own. Ruled,
in the words added under "Hear the words" on the About page: "You may reuse the recordings on the same terms as the
text, CC BY 4.0: credit the recordings to Ordpar (ordpar.no), and the words they read as you would the text itself."
The second clause is there because the recordings also read Ordpar's own added examples, not only Bokmålsordboka's
text. About's "Contact" also says: "If you would like the dictionary's data as files, the
articles or the recordings, write to us there too." (`ordpar/about.md`; the project's licence notes say the same.) Tested
by `ordpar/tests/test_ordpar_about63.py`.

<a id="d173"></a>
### 173. Our own survey in place of Google's form, kept after launch (2026-11-07)

**Status:** built, live since 7 November 2026.

Until then the footer's development note linked a Google form for first readers ([72](#d72)), and the privacy page
named Google for it. The Google form was a survey, not a
feedback box (the reader's Norwegian, first language, what they looked up and whether they found it, what confused
them, ideas to tick, devices, whether they would come back, an optional address for a follow-up). Ruled: the survey ported as Ordpar's one form, at `/survey/`,
every question optional, the first-language part skipped for a reader whose first language is Norwegian, with one
free-form question added last, "Anything else you'd like to tell us?". A note at the top says "Every question is
optional.".

The answers go to the same receiver as the reports of [166](#d166) (`ordpar/receiver/`), under the same total cap of
30 an hour, and are read on the same local page. Retention as for reports: the answers are kept with no end date;
the address or name is never given to an AI assistant and is deleted once dealt with. The questions live in one data file
(`ordpar/site/survey.json`), so they can change as ideas are built. The footer links the survey for good; Google's
link and every mention of Google on the privacy page are gone, and the page gained a section "The survey" (`ordpar/privacy.md`). Tested by `ordpar/tests/test_ordpar_survey173.py`, its browser test
and the receiver's tests.

<a id="d174"></a>
### 174. Norwegian emphasized and formula lines in both languages by default; a preset "English emphasized" (2026-11-07)

**Status:** built, live since 7 November 2026.

Two article settings changed their defaults: *Emphasis, when both languages show* became
"Norwegian emphasized" (was English, [87](#d87)), and *Short formula lines* (such as "used as an adverb:") became
"In Norwegian and English" (was English, [81](#d81)). A new preset, **English emphasized**, sets the old values. Of
the presets of [136](#d136): Default takes the new values; For learners already had them; Concise keeps the old
values, since a later change of a default does not silently change a preset. The new button is second: Default,
English emphasized, Concise, For learners. The settings page's account of the presets ([161](#d161)) follows. Each setting lists its default first ([107](#d107)). A reader who chose a
value keeps it; one who never did sees the new defaults.

With JavaScript off, the page still shows the old look, since the classes were kept rather than renamed across the
stylesheet. A settings address copied before the change, which names only values that differ from the default, now
opens with the new defaults. The Anki deck keeps the old values as its own defaults. Tested by
`ordpar/tests/test_ordpar_defaults174.py` and the presets tests.

<a id="d175"></a>
### 175. The change lists public before launch (2026-11-07)

**Status:** built, live since 7 November 2026; amends [95](#d95).

[95](#d95) had kept the site's change list (`ordpar/changes.md`) internal until launch. Ruled: the site's list goes public now, at `/changes/`; the
entries stay dated, with no version number until 1.0.0, the first numbered entry. The dictionary's list
(`ordpar/library-changes.md`) goes public with it, at `/dictionary-changes/`, made concise:
"Totals unchanged." when nothing moved, otherwise only what moved, with its change ("94,197 articles (+1)"); the
starting point keeps the full totals, and each newer copy of Bokmålsordboka's data gets one credited line. This
amends 95's "each entry gives the new totals". The update note gains "What's new", linking `/changes/`; an About
link to the lists was dropped in favour of [176](#d176)'s Changes tab. Tested by
`ordpar/tests/test_ordpar_changes175.py`.

<a id="d176"></a>
### 176. Tabs over the About pages (2026-11-07)

**Status:** built, live since 7 November 2026.

The tabs About · Coming to Ordpar · Changes · Privacy · Thanks, in that order, under each page's title, the
current one pressed, in the style of the Settings page's section buttons, wrapping onto a second line on a phone
rather than scrolling sideways. One Changes tab serves the site's and the dictionary's lists of [175](#d175), and later the Anki deck's list
([177](#d177)). Help
and More ways to use Ordpar stay out; they may get tabs of their own if those sections grow. ordbokene.no has no tab
row: a header menu "Om ordbøkene" lists its sub-pages, each links back to it, and the footer repeats them; so the tabs are a deliberate divergence, with a row in `docs/divergences.md`. The footer's
"About and licence" became "About", matching the tab; the licence stays in the footer's first line. Tested by
`ordpar/tests/test_ordpar_browser_tabs176.py`.

<a id="d177"></a>
### 177. A changes page for the Anki deck (2026-11-07)

**Status:** built, live since 7 November 2026.

AnkiWeb never tells a reader that a shared deck has been updated, so the deck's own changes needed one place to be
read. Ruled: a page `/deck-changes/`, "Changes to the Ordpar Anki decks", built from `ordpar/deck-changes.md` in the
same short dated form as the site's own list ([175](#d175)). It sits under the Changes tab with the site's and the
dictionary's lists ([176](#d176)); the three link each other. The file is written only by the deck's side of the
project and brought over as it stands, never edited on the site's side, so no second copy can drift; a deck
release's entry reaches the page with the site's next deploy. Tested by
`ordpar/tests/test_ordpar_changes175.py`, which also keeps a list of the deck list's outside links.

<a id="d178"></a>
### 178. The More page: Anki first, and the one-deck edition (2026-11-08)

**Status:** built, live since 9 November 2026.

On `/more/` ([142](#d142), [146](#d146), [152](#d152)) the Anki section should come first and link the new
one-deck edition, *Ordpar: Norwegian Core Vocabulary*, with its description brought up to date. The page's
opening lists the three ways in the new order, and the Anki section was rewritten from the facts of the deck's
AnkiWeb description (about 6,000 words, levels A1–C2, the most frequent first, the article on the back, the
Norwegian read aloud, the Hint, the reverse cards), with one download in place of two, a link to the deck's change
list ([177](#d177)), and a closing paragraph keeping the two-part deck for audio offline. For AnkiDroid the page says
to search for "Ordpar", since a new deck would rank low under "Norwegian". The section keeps its id `#anki`. With it, the About page's thanks name both decks and their order:
since the November release it blends the Kelly list with a subtitle frequency list (FrequencyWords, CC BY-SA 4.0)
rather than the Kelly list alone. The words are pinned by `ordpar/tests/test_ordpar_more142.py` and
`ordpar/tests/test_ordpar_site131.py`.

<a id="d179"></a>
### 179. The audio Worker forwards replaced clip names (2026-11-08)

**Status:** built 8 November 2026; not deployed, since the table still held no pairs on 12 November 2026.

A pronunciation clip is named by its content. When a clip is fixed it gets a new name, and the old one stays in
storage, so older versions of the deck keep playing sound. But the November deck names its
clips and cannot be rebuilt, so it would never get the fixed sound. Ruled: the audio Worker (`ordpar/audio-worker/`)
forwards an old name to its replacement. The table of old and new names is bundled into the Worker at deploy
(`ordpar/audio-worker/src/forwarding.json`), so it needs no extra storage and costs nothing per request; a few thousand pairs at most,
far within Cloudflare's limits on script size and start-up. A requested name is looked up before storage; an old
name is answered with a 302 redirect to the new one, cached for a day, while the new name keeps its year-long
cache. `ordpar/audio-worker/sync_forwarding.py` copies the audio side's table into the Worker, flattens chains of renames and refuses cycles. The deck's player is a
plain audio element, which follows a redirect; clips packaged inside a deck never ask the Worker, so forwarding does
not reach them. The table held no pairs at first; the Worker is to be deployed with the first table that holds
some. Tested by `ordpar/audio-worker/test/worker.test.js` and `ordpar/tests/test_ordpar_forwarding179.py`.

<a id="d180"></a>
### 180. Loading ahead for every control that opens something, Random word included (2026-11-09)

**Status:** built, live since 11 November 2026 (the site's change list dates it 10 November).

Until then only links were loaded ahead ([92](#d92), under the
setting for loading ahead), and the list of pages in `ordpar/site/ahead.js` predated the word pages and left out the
about pages. An inventory of 46 kinds of control found many that opened something of the site but loaded nothing
ahead: the word pages, the English searches, the front page, the about pages and their tabs, the suggestions and
recent rows, Random word.

Ruled: every control that opens an article, a page or a search of the site loads it ahead under the same setting.
For Random word, a rest of 150 ms (or a touch) draws the word then and loads what its click will open; the click
opens that same word. Kept out, with reasons: links to other sites (they would learn the reader's interest before a
click), actions (reporting, answering the survey, clearing, the offline download, installing), links that open a
new tab or a download, links to a place on the same page, and the English/Norwegian switch. Keyboard selection in
the suggestions loads ahead only after a 150 ms pause on one row. Under the *click* setting nothing is loaded before
a click, as before. A link inside an open small article had been fetched twice; now once. The privacy page and the
setting's notes were reworded to cover buttons and suggestion rows. Tested by `ordpar/tests/test_ordpar_ahead180.py`
and the browser test `ordpar/tests/browser/ahead180.js`, which waits for the expected fetch, up to a ceiling, rather
than a fixed time, so the live check cannot fail on timing.

<a id="d182"></a>
### 182. Our corrections shown on articles we have not translated (2026-11-10)

**Status:** built, live since 11 November 2026 (the site's change list dates it 10 November).

The corrections to Bokmålsordboka sent to ordbokene's editors were to be applied on ordpar.no as well.
The fixes that fell
in articles of our library went the usual way, as edits to the stored capture. The rest fell in articles with
no library row, which the build derives from the mirror of Bokmålsordboka's data, and no correction could reach
those. Ruled: the overlay. The build applies each logged correction to the mirror's article before deriving its
page, and only where the text at that place is still the logged *before*; a correction whose text ordbokene has
since changed is skipped and listed. The corrections live in a file of their own, apart from the log of edits to the library's captures. The change notice and the About page's
counts read both files. The deck is unchanged, since it reads only the library. A corrected text loses its play
button until a clip is recorded for the new text. The dictionary change list's opening was amended to say that our
corrections are kept wherever the text they correct is unchanged. Built
in `ordpar/sitegen/overlay.py`; tested by `ordpar/tests/test_ordpar_overlay182.py`.

<a id="d183"></a>
### 183. Readers' ideas on "Thanks to our readers" (2026-11-11)

**Status:** built, live since 11 November 2026.

The Thanks page should also list readers' suggestions for making the dictionary or the deck better, a
different kind of feedback from "Suggest a correction". Ruled: a section of `/thanks/` for now; each list may get a
page or tab of its own if it grows long. Only ideas taken up or planned are listed. They are kept by hand in
`ordpar/reader-ideas.jsonl`, since they come from anywhere. The page's naming rule ("We name a reader only if they
asked us to") covers them as it stands. The page has two headings, "Corrections" and "Ideas from our readers",
newest first, the second left out while it is empty. A reader's credit stands on its own line below the entry
("Suggested by …", or "Reported by …" for a report behind a change; "Suggested by a reader" when no name is given),
in italic with an en dash before it, and half a line of space between ideas. The corrections keep their name in the
row; this is to be looked at again once a report leads to a fix. An entry credits only what the reader contributed:
for the deck's second hint, the idea of seeing what the other words in an example mean, not the design built from
it. The About page and the privacy page were reworded to cover ideas as well as fixes. Built in
`ordpar/sitegen/thanks.py`; tested by `ordpar/tests/test_ordpar_thanks183.py`.

<a id="d184"></a>
### 184. Ordbokene's reply: the divergences record, the licences and the public repository (2026-11-11)

**Status:** ruled; the public repository in preparation, not yet published on
12 November 2026.

**The licences.** Our own code is under MIT-0: its readers are developers,
not the learners Ordpar is for, and no attribution should be needed, by ordbokene or anyone. For Ordpar the only point of asking for attribution is to reach more learners; in code it would live in comments and documentation that learners never see, so it would not help, and leaving it out makes the code easier for anyone to use, ordbokene included. The documentation is
under MIT-0 too. The added example sentences stay CC BY 4.0 for everyone, but Bokmålsordboka's publishers, the
University of Bergen and the Language Council, may use them without attribution and take them into Bokmålsordboka
under its own licence: a condition would otherwise follow each sentence into their dictionary and on to everyone who
reuses it. The same holds for the recordings, offered to them on request.

**The public repository**, `github.com/ordpar/ordpar`, updated weekly, is to let an outsider rebuild the site and adapt the work to projects of their own. It holds the code with its comments unchanged; the working docs, this log
among them, rewritten for an outside reader; the check scripts, with an account of how agents sorted one check's
findings; and the data a build needs: the library, a frequency extract, and Bokmålsordboka's data in two forms,
exactly as its API serves it (editors' names included), so a build reproduces ordpar.no, and a corrected copy with
our fixes applied, remade with each update. The list of recordings stays out; the deck's work, when published, gets
a folder of its own. The documentation stays in English.

<a id="d185"></a>

### 185. The linked word's first Norwegian definition as a hover choice everywhere (2026-11-12)

**Status:** built (12 November 2026).

The setting for what shows when the pointer rests on a linked word has three choices: its translation (the default), its first Norwegian definition, or nothing. The Norwegian definition was a choice only inside *Norwegian only* ([152](#d152)); it now works wherever a hover peek shows on a computer, and a link to a word not yet translated, which has no English peek, gets one. Inside *Norwegian only* with the English equivalents hidden, that view's own hover setting decides instead. The hover follows the Loading setting: under "When its link is clicked" a Norwegian definition shows only from a part of the index the page already has, so nothing is fetched before a press. The index keeps each Norwegian first definition whole, not cut to the length of a list row: 99 % are 123 characters or fewer and the longest is 273. No preset chooses the Norwegian definition.
