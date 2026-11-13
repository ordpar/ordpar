# -*- coding: utf-8 -*-
"""The site face over the deck's renderer — the article-page prototype's own code.

`build_site.py` is the entry point; the modules here are, in dependency order:

    deck.py     imports the deck's renderer (`ordbok_gen`, `markup`, `mini`, `derive`,
                `coverage`) from the repo root, the way `scripts/build_cards.py` does
    strings.py  every visible chrome string, one dict (written to `out/site/strings/en.json`)
    mirror.py   the read-only mirror: id -> byte offset, lemma form -> ids
    library.py  `articles.jsonl` + the derive-on-demand store, and the translated/untranslated
                status of any article id (`coverage.complete_strict`)
    face.py     the site face: a cross-reference as a plain link to our page with its peek (the
                mini is cut from the target's page by `site/mini.js`, decisions 80), and the
                marker shim that keeps a shipped page free of flags
    article.py  the article fragment (bilingual on a translated page, Norwegian on the rest)
    page.py     the page around it: head, chrome, captions, attribution, footer, CSS, scripts

Nothing here writes anything outside the build's own output folder.
"""
