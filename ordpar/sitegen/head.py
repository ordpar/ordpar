# -*- coding: utf-8 -*-
"""What every page's `<head>` carries for the installable web app (decisions 61), search engines
(128) and link previews (127), shared by both builds: the article build (`page.py`: article
pages, About, Help, the privacy page, the prototype front door) and the index build
(`build_index.copy_shell`: the search page, the front page, 404, the favourites, history and
settings pages). `ordpar/docs/offline-app.md` is the spec of the app's part.

* the app manifest link and the browser's theme colour (the accent, `shell.css`'s maroon);
* `<meta name="robots" content="noindex">` on the pages search engines are to leave out (site
  decisions 128, Robin 2026-10-25, reopening 61 (2) and 110's row): every UNTRANSLATED article
  page, the search page `/bm-en/`, History, Favourites, Settings, the 404 page and the privacy
  page; a translated article page, the home page, About and Help carry none. The caller says
  which (`head_tags(indexed=…)`), so a page loses its `noindex` by the build when its article
  becomes translated, with no list kept by hand. `robots.txt` (`ordpar/root/`) blocks nothing —
  a crawler that may not fetch a page never sees its `noindex` (Google's block-indexing doc) —
  and names the sitemap the article build writes (`build_site.write_sitemap`);
* the link-preview tags (site decisions 127, `social_tags`): Open Graph and `twitter:card`, with
  one picture for the whole site (`OG_IMAGE_HREF`, Robin's PNG as he made it in the lab);
* the site's icon (`ICON_HREF`, found missing 2026-10-26 when Robin saw Google list ordpar.no with
  its generic globe): Google Search reads it from the HOME page's `<link rel="icon">` — square,
  PNG among its formats, at a stable address (the site review's
  `evidence/reports/google-favicon-2026-10-26-lookup-web.md`); every page carries it, so a
  browser tab shows it too. The app's own 192 px icon, the one the manifest names.

The service worker is registered by the pages' scripts, not here: `page.PAGE_JS`, in
`/site/ordpar.js`, on the article and About pages, and `site/offline.js` on the shell pages.
`SW_REGISTER` below, a one-line registration, is used by no page: `page.py` imports it without
using it, and `test_ordpar_offline61.py` checks that the About page does not carry it (the page
used it until it loaded `/site/ordpar.js`, 2026-10-20).

`THEME_JS` is the head script every page runs before its first paint (decisions 63: one copy).
Since 2026-10-20 it is a FILE, `/site/theme.js` (`THEME_JS_HREF`, written by the article build,
linked through `page.asset` with its `?v=`), loaded by a parser-blocking `<script src>` in the
head before the stylesheets — never `defer` or `async`, so it still runs before the first paint
(the size report's item 3: 650 bytes inline on every page, 61 MB over the site). The article
pages and About link it through `page.py`, the shell pages through the index build's
`<!--ORDPAR_HEADJS-->` marker. If the file cannot be had (a 404, or offline with neither the
copy nor the HTTP cache), the page paints in the default settings and without `ordpar-js`, as
with JavaScript off.
"""
import html
import json
import os
import re

from . import colours

#: THE LAUNCH SWITCH. On (True) until launch (1.0.0, decisions 110): the "under development"
#: note closes every page's footer (`chrome.footer`). Until site decisions 128 (2026-10-25) it
#: also put `noindex` on every page; the robots line is now each page's own (`head_tags`
#: `indexed`), and this switch no longer touches it. **Remove at launch**: set it to False and
#: rebuild both builds (the article build, then the index build, then the offline bundles);
#: removing it changes every page's frame, so every offline bundle changes once.
NOINDEX = True

MANIFEST_HREF = "/manifest.webmanifest"
#: The browser's theme colour follows the DEFAULT colour scheme only (decisions 63:
#: `colours.DEFAULT`; the stored setting does not change it).
THEME_COLOR = colours.default()["day"]
ROBOTS_NOINDEX = '<meta name="robots" content="noindex">'

#: The site's address, for the absolute URLs a link preview needs (`og:url`, `og:image`)
SITE_URL = "https://ordpar.no"
#: The link-preview picture (site decisions 127): Robin's PNG, shipped as is from
#: `ordpar/site/og/ordpar.png` (copied with the rest of `ordpar/site/`), 1200 x 630
OG_IMAGE_HREF = "/site/og/ordpar.png"
OG_IMAGE_SIZE = (1200, 630)
#: The site's icon for browsers and Google Search: the app icon (`ordpar/site/icons/`, the
#: manifest's), square. Keep the address stable — Google asks for that.
ICON_HREF = "/site/icons/icon-192.png"
ICON_SIZES = "192x192"

#: The one line that registers the service worker (scope `/`), for a page with no script of
#: its own that does it.
SW_REGISTER = ("<script>if('serviceWorker'in navigator)"
               "navigator.serviceWorker.register('/sw.js').catch(function(){});</script>")


def head_tags(indexed=False, social=None):
    """The lines for `<head>`: `noindex` unless the page is `indexed` (site decisions 128; the
    default leaves a page out, so a new kind of page stays out until it is named), the icon, the
    manifest, the colour, then the link-preview tags when `social` is given (`social_tags`'s arguments)."""
    lines = [] if indexed else [ROBOTS_NOINDEX]
    lines.append('<link rel="icon" type="image/png" sizes="%s" href="%s">' % (ICON_SIZES, ICON_HREF))
    lines.append('<link rel="manifest" href="%s">' % MANIFEST_HREF)
    lines.append('<meta name="theme-color" content="%s">' % THEME_COLOR)
    if social:
        lines.append(social_tags(**social))
    return "\n".join(lines)


def _attr(v):
    return html.escape(v or "", quote=True)


def social_tags(url, title, description="", strings=None):
    """The link-preview tags (site decisions 127, Robin 2026-10-25), on every page the builds
    write: `og:type` website, `og:site_name` the site's name, `og:url` the page's address,
    `og:title` the page's `<title>`, `og:description` its meta description (left out where the
    page has none, or an empty one), the picture with its size and a short alt text ("Ordpar:
    Norwegian–English dictionary": the site's name and the pair's dictionary name), and
    `twitter:card` `summary_large_image`. `url` absolute, or a path on the site."""
    s = strings or _strings()
    if url.startswith("/"):
        url = SITE_URL + url
    alt = "%s: %s" % (s["site_name"], s["dictionary_name"])
    lines = ['<meta property="og:type" content="website">',
             '<meta property="og:site_name" content="%s">' % _attr(s["site_name"]),
             '<meta property="og:url" content="%s">' % _attr(url),
             '<meta property="og:title" content="%s">' % _attr(title)]
    if description:
        lines.append('<meta property="og:description" content="%s">' % _attr(description))
    lines += ['<meta property="og:image" content="%s%s">' % (SITE_URL, OG_IMAGE_HREF),
              '<meta property="og:image:width" content="%d">' % OG_IMAGE_SIZE[0],
              '<meta property="og:image:height" content="%d">' % OG_IMAGE_SIZE[1],
              '<meta property="og:image:alt" content="%s">' % _attr(alt),
              '<meta name="twitter:card" content="summary_large_image">']
    return "\n".join(lines)


def _strings():
    from .strings import EN
    return EN


#: Where the head script is served: `out/site/theme.js`, `THEME_JS` below (the build writes it)
THEME_JS_HREF = "/site/theme.js"

#: The head script, run before the first paint, on EVERY page (the article build's pages and,
#: through `<!--ORDPAR_HEADJS-->`, the shell pages — one copy since decisions 63; a file,
#: `THEME_JS_HREF`, since 2026-10-20):
#: * `ordpar-js` on `<html>`: script runs, so `shell.css` holds the room of the chrome that
#:   `shell.js` will insert (the header's Random word, Favourites and Settings, the footer's
#:   Settings, Favourites and History; until 2026-10-20 it showed them, `ordpar-needs-js`);
#: * `theme` = system | light | dark (default system) -> `nightMode` (decisions 19);
#: * `colour` -> `data-accent="<id>"` (decisions 63; `colours.css()` styles each scheme, so a
#:   value no scheme has is the default);
#: * `defs` = en | both | no (default both) -> `ordpar-defs-en` / `ordpar-defs-no`; `mini` =
#:   article | en | both (default article: `en` when `defs` is en, else both — a mini has no
#:   reveal, Robin 2026-10-18) -> `ordpar-mini-en` when it resolves to en; `peek` = on | nb | off ->
#:   `ordpar-peek-off` for off, `ordpar-nbo-hovnb` for nb (site decisions 185: the linked word's
#:   first Norwegian definition as the hover, the English peeks hidden by the sheet); `pframes` = on | off -> `ordpar-pframes-off` (decisions 31, 54);
#:   `minihw` = link | article -> `ordpar-minihw-article` (decisions 78: the mini's headword);
#: * the mini made from the target's page (decisions 80): `minicontent` = full | slim ->
#:   `ordpar-minicontent-slim`; `minispacing` = article | compact (default article since
#:   decisions 97) -> `ordpar-minispacing-compact`; `minitext` = article | smaller (decisions
#:   114: the mini's text sizes, default article) -> `ordpar-minitext-smaller`;
#:   `miniscroll` = on | off -> `ordpar-miniscroll-off`; `minifetch` = point | click | page ->
#:   `ordpar-minifetch-click` / `-page` (the mini script reads the stored values itself; the
#:   classes are for the sheet and for a look at the page);
#: * `formulas` = both | en | no (decisions 81: the formula lines' language; default both since site
#:   decisions 174, en before) -> `ordpar-formulas-no` / `-both`, the latter for any value but en or
#:   no (the default, so a reader with nothing stored gets it); `ety` = en | no | both (decisions 84: the etymology line's
#:   language, modelled on it) -> `ordpar-ety-no` / `-both`;
#: * `suggestrows` = standard | roomy (decisions 86: the search dropdown's row spacing) ->
#:   `ordpar-suggestrows-roomy`;
#: * `emph` = no | en (decisions 87: the emphasized line of a pair; default no since site decisions
#:   174, en before) -> `ordpar-emph-no` for any value but en (the default's class);
#:   `subsenses` = defs | en (decisions 90: subsenses in English only, default defs) ->
#:   `ordpar-subsen-en`; `layout` = ordpar | ordbokene (decisions 87: the layout closer to
#:   ordbokene.no) -> `ordpar-layout-ordbokene`; `examples` = both | no (decisions 111: the
#:   examples' English behind a reveal, default both) -> `ordpar-examples-no`; `exeye` = off | on
#:   (decisions 131: the eye beside the headword, default off) -> `ordpar-exeye-on`; `exlimit` = all |
#:   1 … 10 (decisions 112: the examples shown under each sense, default all) ->
#:   `ordpar-exlimit-<n>`, so the sheet cuts the lists before the first paint; `exmore` = on | off
#:   (the "Show N more examples" line, default on) -> `ordpar-exmore-off`. Each default is the
#:   state with no class, but for `emph` and `formulas` since site decisions 174 (Robin, 2026-11-07):
#:   their new defaults keep the classes they had as choices, so the state with no class — what a
#:   page shows with JavaScript off — is still English emphasized, formula lines in English.
#: * site decisions 152, NORWEGIAN ONLY (`nbonly` = off | on, default off) -> `ordpar-nbo`: a
#:   layer over the reader's settings — while on, `defs`, `mini`, `examples`, `formulas`, `ety` and
#:   `subsenses` draw the layer's classes (`ordpar-defs-no`, both lines in a mini, `ordpar-examples-no`,
#:   `ordpar-formulas-no`, `ordpar-ety-no`, no `ordpar-subsen-en`) whatever is stored, the stored
#:   values untouched (`shell.js` `LAYER_VALUES`, `eff`, the same table); `nbequiv` = hidden | shown
#:   (default hidden, only under the layer) -> `ordpar-nbo-noeq`, and then the hover from `nbhover`
#:   = none | nbdef (default none: `ordpar-peek-off`; nbdef: `ordpar-nbo-hovnb`, the English peeks
#:   hidden by the sheet; it lies over `peek` there) and the rows from `nbrows` = nbdef | none (none: `ordpar-nbo-rows0`);
#:   `nbicon` = on | off (default on) -> `ordpar-nbicon-off`; `labels` = en | no (the labels inside
#:   the article frame, default en) -> `ordpar-labels-no` (the reader's own choice: under the layer
#:   the sheet shows the Norwegian labels from `ordpar-nbo`, 152's follow-up).
#: Any other stored value is the default. `shell.js` toggles the same classes on a change.
#: * the header's search form submitted before `shell.js` has taken it (decisions 104): sent to
#:   `/bm-en/#q=<query>`, never as the form's own GET (`/bm-en/?q=`), which would hand the search
#:   to the host; only with JavaScript off does the form's GET run.
#
#: Site decisions 146 (Robin, 2026-10-27/28): **the settings in the address**, for a pop-up
#: dictionary such as Definer (its frame never sees the reader's saved settings). Before the rest,
#: the script reads the fragment's `key=value` pairs whose key is in the settings table
#: (`settings_table`: shell.js `SETTINGS`, read from that file — the one source; `colour` against
#: the colour table, `lang` against shell.js `LANGS`); a value the key does not accept, and any key
#: not in the table, is ignored. An address that names any setting of the table starts the VISIT:
#: its valid settings, kept in `sessionStorage` (`VISIT_KEY`) for every page that tab or pop-up
#: opens until it is closed, never in `localStorage`; the table's pairs are then taken off the
#: address (`history.replaceState`, the entry's state kept), so the page sees the plain search
#: (`#q=hus`). A page opened without settings in its address takes the tab's visit, if any.
#: Never on `/settings/` (the session's call, 2026-10-28): that page shows, changes and copies the
#: saved settings. `window.ordparRead(key)` is the one reader of a stored setting — the visit's
#: value where it has one, else `localStorage` — for this script and every script that reads a
#: setting itself (`shell.js` `read`, `mini.js`, `ahead.js`, `events.js`, `page.PAGE_JS`);
#: `window.ordparVisit` = {table, colour (the default scheme's id), settings (the visit, or null)}.
#: Every other read below goes through it (`s`).

#: Where the visit is kept (site decisions 146): `sessionStorage`, this tab or pop-up only
VISIT_KEY = "ordpar-visit"
_SHELL_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "shell.js")
_SETTING_ROW = re.compile(r"^\s*\{ key: '([a-z]+)', values: (\[[^\]]*\]|null|LANGS),", re.M)


def settings_table(source=None):
    """The settings table as the address may carry it (site decisions 146): [(key, [values])] in
    `shell.js` `SETTINGS`'s order, read from that file (the one source, no second list); `colour`'s
    values the colour table's ids (`colours.COLOURS`), `lang`'s shell.js `LANGS`."""
    if source is None:
        with open(_SHELL_JS, encoding="utf-8") as f:
            source = f.read()
    js = source
    body = js[js.index("var SETTINGS = ["):js.index("var SPEC = {}")]
    langs = json.loads(re.search(r"var LANGS = (\[[^\]]*\])", js).group(1).replace("'", '"'))
    out = []
    for key, values in _SETTING_ROW.findall(body):
        if values == "LANGS":
            vals = list(langs)
        elif values == "null":
            if key != "colour":
                raise ValueError("shell.js SETTINGS: %r has no values and is not colour" % key)
            vals = [c["id"] for c in colours.COLOURS]
        else:
            vals = json.loads(values.replace("'", '"'))
        out.append((key, vals))
    if not out or len(out) != body.count("{ key: '"):
        raise ValueError("shell.js SETTINGS: %d rows read of %d" % (len(out), body.count("{ key: '")))
    return out


def _visit_js():
    """The head script's first part (site decisions 146): the address's settings, the visit and
    `ordparRead` (see the comment above `THEME_JS`)."""
    table = json.dumps(dict(settings_table()), separators=(",", ":"))
    return (
        "var W=window,T=%s,K=%s,V=null,O=Object.prototype.hasOwnProperty;"
        # the fragment's pairs: a table key starts the visit with its valid values; the rest stay
        "try{var H=location.hash.slice(1).split('&'),o={},n=0,k=[],i,p;"
        "for(i=0;i<H.length;i++){p=H[i].split('=');"
        "if(O.call(T,p[0])){n=1;if(T[p[0]].indexOf(p[1])>=0)o[p[0]]=p[1]}else if(H[i])k.push(H[i])}"
        "if(n){V=o;try{sessionStorage.setItem(K,JSON.stringify(o))}catch(x){}"
        "try{history.replaceState(history.state,'',location.pathname+location.search+(k.length?'#'+k.join('&'):''))}catch(x){}}"
        "}catch(x){}"
        # else the tab's visit; either checked against the table again
        "if(!V)try{V=JSON.parse(sessionStorage.getItem(K))}catch(x){}"
        "if(V&&typeof V==='object'){p={};for(i in V)if(O.call(V,i)&&O.call(T,i)&&T[i].indexOf(V[i])>=0)p[i]=V[i];V=p}else V=null;"
        # never on the settings page (the session's call, 2026-10-28)
        "try{if(/\\/settings\\/(?:index\\.html)?$/.test(location.pathname))V=null}catch(x){}"
        "W.ordparVisit={table:T,colour:%s,settings:V};"
        # site decisions 152: the visit read where it is now, so a setting written into it later
        # (the headword's Norwegian-only icon in a pop-up, shell.js `visitSetting`) is read too
        "W.ordparRead=function(y){var v=W.ordparVisit.settings;if(v&&O.call(v,y))return v[y];try{return localStorage.getItem(y)}catch(x){return null}};"
        % (table, json.dumps(VISIT_KEY), json.dumps(colours.DEFAULT)))


THEME_JS = ("(function(){var E=document.documentElement,c=E.classList;c.add('ordpar-js');"
            "try{" + _visit_js() + "var s={getItem:W.ordparRead},"
            "t=s.getItem('theme')||'system';"
            "if(t==='dark'||(t==='system'&&window.matchMedia&&"
            "window.matchMedia('(prefers-color-scheme: dark)').matches))c.add('nightMode');"
            "var a=s.getItem('colour');if(a&&/^[a-z][a-z0-9-]*$/.test(a))E.setAttribute('data-accent',a);"
            # `defs`: '' for the default; `mini`: its own value if valid, else as the article
            # site decisions 152: Norwegian only (`nbonly`), a layer over the reader's settings —
            # while on, the classes of defs, mini, examples, formulas, ety and subsenses are the
            # layer's, the hover's too with the English equivalents hidden (`L`, `H`)
            "var L=s.getItem('nbonly')==='on',H=L&&s.getItem('nbequiv')!=='shown',"
            "v=L?'no':s.getItem('defs'),m=L?'no':s.getItem('mini');v=v==='en'||v==='no'?v:'';"
            "m=m==='en'||m==='both'?m:v;"
            "v&&c.add('ordpar-defs-'+v);m==='en'&&c.add('ordpar-mini-en');"
            "(H?s.getItem('nbhover')!=='nbdef':s.getItem('peek')==='off')&&c.add('ordpar-peek-off');"
            "L&&c.add('ordpar-nbo');H&&c.add('ordpar-nbo-noeq');"
            "H&&s.getItem('nbrows')==='none'&&c.add('ordpar-nbo-rows0');"
            # site decisions 185: the Norwegian definition as the hover, from `nbhover` under
            # the layer with the equivalents hidden, else from `peek` = nb
            "(H?s.getItem('nbhover')==='nbdef':s.getItem('peek')==='nb')&&c.add('ordpar-nbo-hovnb');"
            "s.getItem('nbicon')==='off'&&c.add('ordpar-nbicon-off');"
            "s.getItem('labels')==='no'&&c.add('ordpar-labels-no');"
            "s.getItem('pframes')==='off'&&c.add('ordpar-pframes-off');"
            "s.getItem('minihw')==='article'&&c.add('ordpar-minihw-article');"
            "s.getItem('minicontent')==='slim'&&c.add('ordpar-minicontent-slim');"
            "s.getItem('minispacing')==='compact'&&c.add('ordpar-minispacing-compact');"
            "s.getItem('minitext')==='smaller'&&c.add('ordpar-minitext-smaller');"
            "s.getItem('miniscroll')==='off'&&c.add('ordpar-miniscroll-off');"
            "var f=s.getItem('minifetch');(f==='click'||f==='page')&&c.add('ordpar-minifetch-'+f);"
            # site decisions 174: `both` the default, so its class unless en or no is stored
            "f=L?'no':s.getItem('formulas');f!=='en'&&c.add('ordpar-formulas-'+(f==='no'?'no':'both'));"
            "f=L?'no':s.getItem('ety');(f==='no'||f==='both')&&c.add('ordpar-ety-'+f);"
            "s.getItem('suggestrows')==='roomy'&&c.add('ordpar-suggestrows-roomy');"
            # site decisions 174: `no` the default, so its class unless en is stored
            "s.getItem('emph')!=='en'&&c.add('ordpar-emph-no');"
            "!L&&s.getItem('subsenses')==='en'&&c.add('ordpar-subsen-en');"
            "s.getItem('layout')==='ordbokene'&&c.add('ordpar-layout-ordbokene');"
            "(L||s.getItem('examples')==='no')&&c.add('ordpar-examples-no');"
            "s.getItem('exeye')==='on'&&c.add('ordpar-exeye-on');"
            "f=s.getItem('exlimit');/^(?:[1-9]|10)$/.test(f)&&c.add('ordpar-exlimit-'+f);"
            "s.getItem('exmore')==='off'&&c.add('ordpar-exmore-off')"
            "}catch(x){}"
            # the header's search submitted before shell.js has taken the form (a slow
            # connection): to `#q=`, never the form's own GET to `?q=` (decisions 104)
            "var D=document;D.addEventListener&&D.addEventListener('submit',function(e){var f=e.target,i;"
            "if(e.defaultPrevented||!f.classList||!f.classList.contains('ordpar-search'))return;"
            "e.preventDefault();i=D.getElementById('ordpar-q');i=i?i.value.trim():'';"
            "if(i)location.href=f.action.split(/[?#]/)[0]+'#q='+encodeURIComponent(i)})"
            "})();")
