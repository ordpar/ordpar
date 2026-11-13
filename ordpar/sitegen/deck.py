# -*- coding: utf-8 -*-
"""Import the deck's renderer and pipeline modules from the repo root.

Same two `sys.path` inserts `scripts/build_cards.py` uses (the root, then `scripts/`), so the
site build gets the *same* modules the deck build does — one renderer, no copy
(site decisions 30, recommended (1): import as-is at the prototype).

`ROOT` is the repo root; `ORDPAR` the site folder. Import order matters: `ordbok_gen` must be
imported before `mini` (it folds `mini.STYLE` into its full stylesheet at module level) and
`markup` imports both back, lazily inside `render_card`.
"""
import os
import sys

ORDPAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ORDPAR)
for _p in (os.path.join(ROOT, "scripts"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ordbok_gen  # noqa: E402  -- the card view: sections, sense bodies, the CSS
import markup      # noqa: E402  -- marker notation -> HTML, the cross-reference controls
import mini        # noqa: E402  -- the click-tier mini-article
import derive      # noqa: E402  -- derive_row / concepts_map / _roman
import coverage    # noqa: E402  -- complete_strict: the dictionary's completion bar
import fetch       # noqa: E402  -- prune_article
import postags     # noqa: E402  -- the paradigm-tag -> pos_en table (one source of truth)
import store       # noqa: E402  -- read_jsonl

__all__ = ["ROOT", "ORDPAR", "ordbok_gen", "markup", "mini", "derive", "coverage",
           "fetch", "postags", "store"]
