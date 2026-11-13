# The data's licences

The files in this folder are not under the code's licence. What is under which licence, and the
credit each asks for:

- **Bokmålsordboka** (`bokmalsordboka/`, `sources/articles/`, and the Norwegian in
  `articles.jsonl`): © Språkrådet (the Language Council of Norway) and the University of Bergen,
  published at [ordbokene.no](https://ordbokene.no/) under the
  [Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
  The inflection tables are built from Norsk ordbank, under the same licence. Credit
  Bokmålsordboka as that licence asks. The corrected copy (`bokmalsordboka/corrected/`) is
  Bokmålsordboka with our fixes in it, under the same licence: credit Bokmålsordboka, and Ordpar
  (ordpar.no) for the corrections.
- **Ordpar's English** (the English in `articles.jsonl`): written with AI (Claude, by Anthropic)
  under Robin Fauskanger's direction and review. Whatever rights exist in it are given on the same
  terms as the Norwegian, CC BY 4.0: credit the English to Ordpar (ordpar.no), and the Norwegian to
  Bokmålsordboka.
- **Ordpar's added example sentences and corrections** (the `ex_added` sentences in
  `articles.jsonl`, the files in `review/`, and our fixes in `sources/articles/` and
  `bokmalsordboka/corrected/`): CC BY 4.0, like the rest of what Ordpar adds, credited to Ordpar
  (ordpar.no).
- **The word counts** in `frequency/`: N-grams from the National Library of Norway 2026,
  [Språkbanken](https://www.nb.no/sprakbanken/), National Library of Norway
  ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)).

The code and the docs in this repository are under MIT-0, in [`LICENSE`](../LICENSE) at the
repository's root.
