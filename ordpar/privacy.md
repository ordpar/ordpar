<!-- The privacy page (/privacy/), site decisions 19, 26, 62 and 104. A DRAFT for Robin: nothing
here is published until he has approved the words and the switch is turned on (sitegen/chrome.py
PRIVACY). Rendered by ordpar/sitegen/about.py (privacy_page): the About page's Markdown subset —
"# " the title, "## " a heading, **bold**, a link, [text] directly followed by (url), a block of "- " lines a list — with no
build numbers. A [[...]] is a placeholder: the build refuses the page while one is left; none is
left since 2026-11-05 (the receiver's address filled with the Worker's workers.dev name).
Redrafted 2026-10-23 against the independent review (decisions 104; the review's
R1–R12 and M1–M16) and the legal check: every statement about Cloudflare or GitHub is what their
own documents say (the legal check, fetched 2026-10-23), and where they are silent the page says
so. It claims nothing about whether consent is needed (decisions 104, Robin 2026-10-23). Every
number here is the receiver's (ordpar/receiver/src/rules.js, secret.js) and the page script's
(ordpar/site/events.js, offline.js); ordpar/tests/test_ordpar_privacy104.py holds them together.
"Reporting a mistake" drafted 2026-11-05 (site decisions 166), its numbers the receiver's
(ordpar/receiver/src/reports.js) and the page's (ordpar/site/report.js), held together by
ordpar/tests/test_ordpar_report166.py; its legal-basis sentence is the drafter's, to be checked
against the lookup of 2026-11-05 before the page is published. Redrafted by 166's follow-up the
same day: the total cap in place of the per-sender limit (no scrambled code any more), and the name
to credit (consent, 6(1)(a)).
What Cloudflare itself keeps (site decisions 169 (a), Robin's approval 2026-11-06): the full statement
moved to "Audio", which every build shows, the receiver's section pointing to it; the 32 days are the
account's `httpRequestsAdaptive` lookback (`notOlderThan` 2,764,800 s, read 2026-11-06), whose records carry
the client IP, the time and the path (the recording) for both Workers.
The readers' survey (site decisions 173, Robin's approval 2026-11-07, "Approve all"): Google and its form gone
from the opening and from "Questions"; the opening names Anthropic for "a report or survey answers"; and "The
survey", after "Reporting a mistake", inside [if survey] (chrome.SURVEY, on only with reports on). Its claims
are held to the code by ordpar/tests/test_ordpar_survey173.py (the page ordpar/site/survey.js, the receiver
ordpar/receiver/src/survey.js). The opening's "and" before Anthropic, and before Cloudflare with reports off,
is the build's, for the list's grammar with each switch off.
THE SWITCHES IN THE TEXT (site decisions 166, 2026-11-05): the page says only what is true of the
build. [if counting]…[/if] is kept only while the counting is live (events.js RECEIVER set,
chrome.counting()), [if reports]…[/if] only while reports are on (chrome.REPORT_RECEIVER),
[if receiver]…[/if] while either is (the receiver is used at all), [if survey]…[/if] while the survey
is (chrome.SURVEY with reports on, site decisions 173); [if no_counting], [if no_reports],
[if no_receiver] and [if no_survey] the reverse. A block may sit inside another. The counting's text inside its
blocks is the text reviewed under decisions 104, unchanged; test_ordpar_privacy166.py holds it so
(the page with every switch on is HEAD's text, the address and the companies' sentence apart). -->

# Privacy

Ordpar sets no cookies, has no accounts, and has no advertising or scripts from other companies on its pages. This page says what your browser keeps, what it sends to us,[if receiver] what we keep and for how long,[/if] and which companies handle it. They are GitHub, which serves the site's pages;[if no_reports] and[/if] Cloudflare, which runs our[if receiver] receiver and our[/if] audio server[if reports]; and Anthropic, whose AI assistant may help us read a report[if survey] or survey answers[/if] you send[/if].

[if no_counting]**To look words up without anyone seeing which:** download the offline copy, in Settings under "Loading, offline and your data". Your searches and the articles you open are then answered from your device, so neither GitHub nor anyone else sees which words you look up; only a recording you play, and the list of recordings it is found in, is still fetched (see "Audio"). Setting "When a linked article or page is loaded" to "When its link is clicked" also stops the site fetching anything before you open it.[/if]

## What stays on your device

Your browser keeps these in its storage for this site: your settings, when you change one; whether you search in English or in Norwegian, once you have switched; your favourites, when you mark one; your search history (a list of words you have looked up); a note about the offer to install Ordpar as an app (whether it was shown, your answer and when, and, until you close the tab, that it was shown in this visit); and, if you download the whole dictionary for use offline, that copy and two records about it (its date and size, and the result of the last check for a newer version). None of this is sent anywhere. Only your browser reads it, and it leaves your device only if you export it to a file yourself.

The site also installs a small background script in your browser (a service worker) when you open any of its pages, whether or not you keep the offline copy. Without the copy it changes nothing, except that a page that cannot load shows a short notice; with the copy, it answers from the copy. It keeps nothing of its own.

To delete what is stored, go to Settings: "Delete stored data" removes everything listed above except the offline copy itself and the note for the open tab, which goes when you close it; "Remove the offline copy" removes the copy and its records. Clearing this site's data in your browser's own settings removes all of it, the service worker included.

## What your browser sends us

[if no_counting]Ordpar does not count its readers or record what they look up. Apart from a request for a recording when you play one (see "Audio" below)[if reports][if no_survey] and[/if][if survey],[/if] a report of a mistake if you send one (see "Reporting a mistake" below)[/if][if survey] and your answers to the survey if you send them (see "The survey" below)[/if], your browser sends us nothing: not the pages you view, not what you search for, and not whether you install Ordpar as an app.[/if][if counting]While you use the site with a connection, your browser sends our receiver (see below) these short messages, and nothing else[if reports] apart from a report of a mistake, if you send one (see "Reporting a mistake" below)[/if][if survey], or your answers to the survey, if you send them (see "The survey" below)[/if]:

- **A page view:** the page's address within the site, such as /bm-en/12345/, and nothing more. One per page, sent after the page has been on screen for two seconds, or at your first scroll, tap or key press. The search page is sent as /bm-en/, without your search, and an address the site does not have is sent as /other.
- **A search:** for a search that found something, what you searched for. For a search that found nothing, what you searched for and which of the similar words you then chose and its place in the list, or that you chose none (which is also sent if you leave the page or switch away from it first).
- **A suggestion chosen:** what you had typed so far, the suggestion you chose and its place in the list. One message per choice, never one per key you press. Choosing a suggestion also runs a search for it, which is sent as a search.
- **An install:** that Ordpar was installed as an app, and nothing else.

Each search and each suggestion chosen also says whether it was made in English or in Norwegian.

A search that contains a digit, or is longer than 40 characters, is never sent.

The messages carry no identifier and no cookie, and your browser is told not to send the address of the page you are on with them. Like every request on the internet, they reach the receiver with your IP address and your browser's name and version. The receiver uses these only to make the daily code described below and to recognise robots, and does not store them.

## How we count readers

To count how many people use the site each day, the receiver makes a scrambled code from your IP address and your browser's name, together with a secret that is replaced every day. Only the code is stored with the page view; your IP address and your browser's name are not stored. Each day's secret is deleted five minutes after its day ends (midnight UTC), so one day's code cannot be matched with another day's, and once a day's secret is deleted we cannot work out that day's code from an IP address. Nothing is stored on your device for this.

The number of different codes in a day is our count of readers that day. It is not exact: people who share an IP address and the same browser count once, and one person counts twice when using two devices, or when their IP address changes during the day or their browser is updated.

While page views are kept (below), the lines with the same code are the pages one browser viewed from one IP address that day, in order and to the minute. We use them only to make the daily totals and to apply the rule against robots below.

Searches are kept apart from page views, with no code, no time of day and in a random order, so we have no key that links a search to the pages you viewed, and we do not try to find one.

## Counting people, not robots

Your browser sends nothing when it reports that it is being driven by automation software, as our own automatic tests are. The receiver keeps nothing from a browser whose name is on a public list of web crawlers or that gives no name, nor from a network on a public list of data centres and hosting companies (a VPN run from a data centre included). When the daily totals are made, a code that viewed 100 pages or more within 10 minutes is left out of them, and the number of codes and page views left out is kept beside the totals. A robot that presents itself as an ordinary browser can get past these checks.[/if]

[if receiver]## Where it is kept, and for how long

The receiver is a small program of ours that Cloudflare runs for us (a Cloudflare Worker), at https://ordpar-receiver.ordpar.workers.dev. It runs at whichever of Cloudflare's locations your request reaches, which may be outside the EU. What it keeps is stored in Cloudflare's database service[if counting], and the daily secret in a separate Cloudflare store. Both were created in Cloudflare's EU jurisdiction, so their data is stored in the EU, though the secret can be cached at other Cloudflare locations when it is used[/if][if no_counting], in a database created in Cloudflare's EU jurisdiction, so its data is stored in the EU[/if].

[if counting]- **Page views** are kept as they arrived (the page's address, the day and minute, the day's code) for one day after the day they arrived, and are then deleted. They are totalled shortly after midnight (UTC) at the end of their day, and the totals are kept with no end date: page views per day, readers per day, page views per page per day, and how many the rule against robots left out.
- **Searches and suggestions chosen** are kept as they arrived (the day, the kind of message, whether it was English or Norwegian, its words in small letters, and any place in a list) for 30 days after the day they arrived. After that, a search is kept only if the same words were searched for at least three times, and then only as a count with no date, together with the kind of search and, where there was one, the word chosen and its place in the list; the rest are deleted. These counts are kept with no end date.
- **Installs** are kept as a count per day, with no end date.

[/if]We have turned off the request log that Cloudflare offers us for the receiver. Cloudflare itself keeps log data about the traffic on its network, as described under "Audio" below.

Cloudflare keeps our database restorable to any minute of the last 7 days (its "Time Travel", which is always on), so a line we delete can still be restored by us for 7 days. Cloudflare does not say how long its own backups last.[if counting] We have found nothing in Cloudflare's documentation about backups of the store that holds the daily secrets.[/if]

Cloudflare, Inc. is an American company. It handles this data for us as our processor, under the data processing addendum that is part of its terms. Cloudflare states that it is certified under the EU–US Data Privacy Framework, which covers transfers to the United States, and its addendum includes the EU's standard contractual clauses.[/if]

## What GitHub sees

The site's pages and files are served by GitHub Pages (GitHub, Inc., an American company), so GitHub receives your IP address and the address of each page and file your browser asks for. GitHub says that when a site it serves this way is visited, the visitor's IP address is logged and stored for security purposes. It does not say for how long, nor whether it does this for us or for itself. Its privacy statement says that for transfers out of the EU it generally relies on the EU's standard contractual clauses.

To answer a search, your browser fetches from GitHub the parts of the dictionary's index named by its first few letters, the pages of the articles it shows, and often the word's own page (such as /bm-en/hus/). So unless you keep the offline copy, GitHub can tell which words and articles you look up. If you keep the offline copy, your searches and the articles you open are answered from your device instead, so GitHub does not see them; a recording you play is still fetched from our audio server, and the list of recordings it is found in from GitHub (see "Audio" below). By default the site also fetches an article, page or search when your pointer rests on its link, on a suggestion under the search box or on Random word, before you open it, and a recording when it rests on a sound icon; under Settings, "When a linked article or page is loaded" set to "When its link is clicked" fetches nothing before you click. If you have chosen to see a linked word's first Norwegian definition when the pointer rests on it, the site fetches the part of the index that holds it as soon as your pointer reaches the link, unless you have chosen "When its link is clicked". With JavaScript turned off, the search does not work, and your search is not sent anywhere. If you keep the offline copy, your browser asks GitHub whether there is a newer version while you use the site, at most once every 15 minutes.

## Audio

When you press a sound icon, or rest the pointer on one (unless you have chosen to load nothing before you click, see "What GitHub sees" above), your browser fetches the recording from Ordpar's audio server, a small program on Cloudflare's network. The request reaches Cloudflare like any request on the web, with your IP address; our program sets no cookie and keeps no logs of it, and we have turned off the request log that Cloudflare offers us for it. Cloudflare itself keeps log data about the traffic on its network, which can include IP addresses, in its data centres in the US and Europe "for a limited period of time"; it does not say how long. Cloudflare also keeps records of requests to our audio server, which we can see in our Cloudflare account for 32 days: each with the IP address, its country, the time, and which recording was asked for, and so which word. We do not copy or keep them.

[if reports]## Reporting a mistake

Under every article there is a button, "Suggest a correction". If you use it, your browser sends our receiver one message when you press Send, and only then: what you wrote, where you said the mistake is (if you chose), your email address (if you gave one), a name to credit (if you gave one), the article's number, and which version of the site is current when you send it. Nothing else goes with it: no cookie, no identifier, and not the address of the page you were on.[if counting] Since you send it yourself, it is sent even if you have turned off "Send usage statistics" or your browser sends Global Privacy Control or Do Not Track.[/if]

The receiver stores the report with the day it arrived. It does not use or store your IP address or your browser's name for a report, though Cloudflare keeps records of requests to the receiver too, with their IP address and time, which we can see for 32 days, as for the audio server (see "Audio" above). To stop a flood of reports, it accepts at most 30 reports an hour from everyone together: for this it keeps only the number of reports that have arrived in the current hour, nothing about who sent them, and deletes that number once the hour is over. When the hour's number is reached, everyone who sends a report is asked to try again later.

Robin reads the reports, to correct the dictionary. He may read a report with the help of an AI assistant (Claude, by Anthropic). The report's text then goes to Anthropic, which keeps the conversation for 30 days and does not use it to improve its AI models, except that it may use a conversation its safety systems flag for its safety work. Your email address and the name to credit are never shared with it. The reports are kept in [if counting]the same Cloudflare database as the rest[/if][if no_counting]Cloudflare's database service[/if], in the EU (see "Where it is kept" above). We use your email address only to answer your report, and delete it once we have dealt with the report; like any deletion in that database, it can still be restored by us for 7 days after that. The rest of the report (the text, where the mistake is, the article, the day and the site's version) is kept after that, as our record of what readers have helped us correct, with no end date. Please do not write anything in a report that you would not want us to keep.

The name to credit is optional, and only for our page [Thanks to our readers](https://ordpar.no/thanks/), which lists the fixes readers' reports have led to. If your report leads to a fix, or to an idea we take up, we may publish the name there with it, as you gave it or shortened; we never publish it otherwise, and we name nobody who did not give a name. When we have dealt with the report, the name is deleted from the receiver as your email address is, whether or not we published it; a published name is kept only in the lists behind that page. If you want your name taken off the page, write to post@ordpar.no, and we will take it off. If you send us an idea some other way, such as by mail or in a comment, and ask to be credited, we publish the name you give with the idea on the same page, and take it off whenever you ask.

The legal basis is our legitimate interest in correcting the dictionary (GDPR Article 6(1)(f)); for your email address, your choice to give it so that we can answer you (GDPR Article 6(1)(a)); and for a name to credit, your consent, which you give by writing it in the field and can withdraw at any time (GDPR Article 6(1)(a)). You can ask us to see, correct or delete a report you sent, to delete your email address before we answer, or to take your name off the Thanks page, by writing to post@ordpar.no. Since we do not know who sent a report, tell us roughly when you sent it and what it said.[/if]

[if survey]## The survey

The page "Ordpar — your first impressions", linked at the foot of every page, asks what you think of Ordpar. Every question is optional. If you fill it in, your browser sends our receiver one message when you press Send, and only then: your answers, and an email address or name if you gave one so that we can ask you a follow-up question. Nothing else goes with it: no cookie, no identifier, and not the address of the page you were on. As for a report, the receiver does not use or store your IP address or your browser's name, though Cloudflare keeps records of requests to it (see "Audio" above), and the limit of 30 an hour counts reports and answers together. The answers are kept in Cloudflare's database service, in the EU, as reports are (see "Where it is kept" above).

Robin reads the answers, to improve Ordpar, and may go through them with the help of an AI assistant, as for reports (see "Reporting a mistake"); your email address or name is never shared with it. We use them only to ask you a follow-up question, and delete them once we have, or once we have decided not to; like any deletion in that database, they can still be restored by us for 7 days after that. The rest of your answers is kept with no end date, as our record of what readers have asked for. Please do not write anything you would not want us to keep.

The legal basis is our legitimate interest in improving the dictionary (GDPR Article 6(1)(f)); for your email address or name, your choice to give it so that we can ask you a follow-up question (GDPR Article 6(1)(a)). You can ask us to see, correct or delete your answers, or to delete your email address or name before we use it, by writing to post@ordpar.no; tell us roughly when you sent them and what they said.[/if]

[if counting]## Offline and the installed app

Nothing is sent while your device has no connection: searches in the offline copy are then never sent, and go only into your history on the device. The installed app sends the same messages as the website whenever it has a connection.

## Who is responsible, and the legal basis[/if][if no_counting]## Who is responsible[/if]

Robin Fauskanger is responsible for this data (the controller), and can be reached at post@ordpar.no.

[if counting]The legal basis for what the receiver does with these messages, the daily code included, is our legitimate interest (GDPR Article 6(1)(f)) in counting the readers of a free dictionary and learning what they look for, for the dictionary's development and for applications for funding.

[/if][if receiver]Nothing here is required of you: the site works the same if your browser sends nothing. No decision about you is made from this data.

[/if][if counting]## Your right to object

You can object to this at any time. The simplest way is to turn off "Send usage statistics" in Settings: the site then sends none of these messages. "Delete stored data" turns it back on, since it resets every setting. Turning on Global Privacy Control or Do Not Track in your browser does the same, and the receiver keeps nothing from a browser that sends Global Privacy Control. With JavaScript turned off, the site sends none either. You can also object by writing to us (below).

## Your other rights[/if][if no_counting]## Your rights[/if]

You can ask us what we hold about you, and have it corrected, deleted or its use restricted[if no_counting][if reports], or object to our use of it[/if][/if].[if counting] Until a day's secret is deleted, that day's page views can be found by their code from your IP address and your browser's name, if you give them to us. Once the secret is deleted, we cannot tell which code was yours, so we cannot find your page views to show them to you or delete them (GDPR Article 11). For a search, tell us the words and the day, and we can delete the lines with those words from that day (or, after 30 days, the count kept for them).[/if]

You can complain to the Norwegian Data Protection Authority, Datatilsynet, or to the data protection authority where you live or work.

## Questions

To ask about this page or to use any of these rights, write to post@ordpar.no.

If what we collect changes, this page will say so, with the date of the change.
