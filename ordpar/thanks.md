<!-- The thanks page (/thanks/, site decisions 166: a reader who wants it is
credited by name on a page of its own, with the number of reports and the number of fixes
they led to). Rendered by ordpar/sitegen/thanks.py from this text and the list of fixes,
ordpar/reader-fixes.jsonl, which only Robin's /reports page writes (scripts/reports_page.py). The
About page's Markdown subset; {reports} and {fixes} are counted by the build ("3 reports", "1 fix");
[if fixes]...[/if] is kept while there is a fix, [if no_fixes]...[/if] while there is none; {list},
a paragraph of its own, becomes the list of fixes, newest first. Readers' ideas (site decisions 183,
Robin 2026-11-11): ordpar/reader-ideas.jsonl, kept by hand by the session (ideas come from anywhere:
mail, Reddit, the deck's reviews); [if ideas]...[/if] is kept while it has an idea, so with none the
heading and its list are left out entirely; {ideas}, a paragraph of its own, becomes the list of
ideas, newest first; an idea's optional "credit": "reported" says "Reported by" for "Suggested by". The opening, the two headings and the ideas' entries are Robin's approved words
(2026-11-11, decisions 183). -->

# Thanks to our readers

Readers help us in two ways: by telling us about mistakes in the articles, and with ideas for making the dictionary or the Anki deck better. Here we list the mistakes we have corrected and the ideas we have taken up or plan to. We name a reader only if they asked us to.

## Corrections

[if fixes]Thanks to {reports} that led to {fixes}.[/if][if no_fixes]No report has led to a fix yet.[/if]

{list}

[if ideas]
## Ideas from our readers

{ideas}
[/if]
