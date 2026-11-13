<!-- The page "More ways to use Ordpar" (/more/), site decisions 142 (Robin, 2026-10-26/27): a page
of its own for using Ordpar outside the site, linked from the home page (a line under Random word)
and from every page's footer (after Help). The words are the approved draft's, word for word from
docs/sessions/2026-09-19-ordpar-site-review/walk-through/more-ways-page-draft-2026-10-26.md § The
draft, as it would read (with Robin's eight Definer steps and AnkiDroid's Shared Decks, 2026-10-27).
Rendered by ordpar/sitegen/about.py (more_page): the About page's Markdown subset, plus a heading's
fixed id written after it as {#id} (#popup, #anki, #offline), numbered steps ("1. "), and a line
of code under a step (indented, in backticks: the Definer URL and CSS, selectable with one click);
no index, no build numbers. Changed by site decisions 146 (2026-10-28): step 4's words, the new
sentence after step 8 and the theme sentence (Robin's approved words); the step-4 line is filled by
the page's script with the address carrying the reader's saved settings, and both code lines get a
Copy button (`shell.js` `wireCodeLines`). Site decisions 152 (2026-10-31): step 7's line gained a second
rule, `.ordpar-nbhw { display: inline-flex !important; }`, which shows the Norwegian-only button beside
the headword in the pop-up, whose header the first rule hides (Robin's pick (a)); the sentence after
step 8 on copying the line again is a DRAFT for Robin. Site decisions 178 (Robin, 2026-11-08): the
Anki section first, rewritten for the one-deck edition (Ordpar: Norwegian Core Vocabulary), the
two-part deck kept in its last paragraph; the opening's list reordered (the approved draft, A36). -->

# More ways to use Ordpar

Ordpar is a website, but you don't have to visit it to use it. Here are three other ways: as flashcards in Anki, as a pop-up on any web page, and on your own device without a connection.

## Practise the words in Anki {#anki}

Anki is a free flashcard program that shows you the cards you find hard more often than the ones you already know. Ordpar's Anki deck, [*Ordpar: Norwegian Core Vocabulary*](https://ankiweb.net/shared/info/1906319472), has about 6,000 core Norwegian words, sorted into levels from A1 to C2, the most frequent first. The back of each card is the word's Ordpar article, with the Norwegian read aloud and small articles for linked words that open with no network needed. If you're stuck, a Hint button on the front shows a Norwegian example. Every word also has a card from English to Norwegian. To start:

1. Install Anki on your computer from [apps.ankiweb.net](https://apps.ankiweb.net/). It is free for Windows, Mac and Linux.
2. Open the deck on AnkiWeb and press Download.
3. Double-click the downloaded file to add it to Anki, or use File → Import.

On a phone, AnkiDroid for Android is free, and AnkiMobile for iPhone and iPad is paid. In AnkiDroid you can add the deck directly: open its Shared Decks, search for "Ordpar", and choose *Ordpar: Norwegian Core Vocabulary*. On an iPhone or iPad, add the deck on your computer and sync both through a free AnkiWeb account. The deck's page on AnkiWeb says how to practise with it, and [Changes to the Ordpar Anki decks](https://ordpar.no/deck-changes/) lists what each update changed.

The same cards also come as *6000 Most Frequent Norwegian Words*, in two parts ([Part 1](https://ankiweb.net/shared/info/1989661164), [Part 2](https://ankiweb.net/shared/info/879167685)), which carry more of the audio in the download, for studying offline. If you already study the two parts, the new deck's page says how to switch and keep your progress.

## Look up words on any web page {#popup}

With Definer, a pop-up dictionary extension for Chrome, Edge and Firefox, you can select a Norwegian word on any web page and see its Ordpar article in a pop-up, with small articles for linked words, just as on ordpar.no. Definer is made by Lumetrium, not by Ordpar, and everything described here is free. To set it up:

1. Install Definer from the [Chrome Web Store](https://chromewebstore.google.com/detail/definer-word-translator-a/noagjioaihamoljcbelhdlldnmlgnkon), [Microsoft Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/definer-word-translator/bmjggedeimdncfelfdcphnmbknkmfffp) or [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/lumetrium-definer).
2. Right-click Definer's icon and choose Options.
3. Choose Sources, then + NEW SOURCE, then CONSTRUCTOR.
4. In the URL field, paste the address below. If you have changed any settings on ordpar.no, the address carries them, so the pop-up shows articles the way you see them here:
   `https://ordpar.no/bm-en/#q={{str}}`
5. Choose ADD SOURCE.
6. Find Custom in the list of sources and open its settings.
7. In the CSS field, paste:
   `.ordpar-header, .ordpar-footer, .ordpar-devnote { display: none !important; } .ordpar-nbhw { display: inline-flex !important; }`
8. Select a word on a page and press Definer's icon.

If you change your settings later, copy the address again, here or at the bottom of Settings, and paste it over the old one in Definer's URL field.

The CSS line also shows a button beside the headword in the pop-up that switches *Norwegian only* on or off, for that pop-up only. If your CSS field holds the line without its `.ordpar-nbhw` part, paste the line again to get the button.

A word with several articles shows them as a list, and an inflected form, such as *husene*, says which word it is a form of. The pop-up follows your browser's light or dark mode, unless you have chosen one in Settings. In a PDF, open the file in Definer's own PDF reader: the pop-up does not work in the browser's built-in PDF viewer.

## Use it without a connection {#offline}

Ordpar can keep the whole dictionary on your device, so you can look words up offline; pages also open faster. In [Settings](https://ordpar.no/settings/#data), under *Loading, offline and your data*, press *Keep the whole dictionary on this device*. On a phone, installing Ordpar as an app (your browser's menu, or the offer Ordpar shows) puts it on your home screen and helps the browser keep the copy.
