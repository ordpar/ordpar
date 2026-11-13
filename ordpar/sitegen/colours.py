# -*- coding: utf-8 -*-
"""The site's colour schemes — the setting "Accent colour" ("Colour" until decisions 126) (site-review decisions 63, Robin 2026-10-19).

ONE TABLE. A scheme is one entry in `COLOURS`; everything else is generated from it:

* the CSS (`css()`, written into `out/site/article.css` by the article build, which every page
  links): `:root` carries the DEFAULT scheme's values, and `html[data-accent="<id>"]` each
  scheme's own — the head script (`head.THEME_JS`) puts the stored `colour` on `<html>` as
  `data-accent` before the first paint, so an unknown or absent value is the default;
* the choices on the settings page (`settings_json()`, inlined by the index build into
  `/settings/` as `window.ORDPAR_COLOURS`);
* the browser's theme colour, the app manifest's colours and the icon's ground follow the
  DEFAULT only (Chrome fixes the manifest's at install): `head.THEME_COLOR`,
  `build_site.py` (the manifest it copies), `build_icons.py`.

The variables every sheet uses (the deck's sheets are rewritten site-side, `page.article_css`;
`ordbok_gen.py` is untouched):

    --ordpar-maroon, --ordpar-maroon-rgb   the day accent, and its "r,g,b" for rgba()
    --ordpar-tint,   --ordpar-tint-rgb     the night accent (used only under .nightMode rules)
    --ordpar-night-line                    a link's underline in night mode (unset: as today)

`shell.css` maps them to `--ordpar-accent` / `--ordpar-focus` (day, and night under .nightMode).

**The default's night is today's** (Robin, 2026-10-20: "at least for the 'default' one,
whichever that becomes"): whichever scheme is `DEFAULT`, its night accent is `TINT_REF`
(`#e3b7c9`) with no night line — `effective()` applies the rule, so the CSS and the settings
page's swatch both show it. A scheme chosen while it is NOT the default keeps its own `night`
(Wine's and Burnt orange's computed tints, ordbokene's black and white).

**Changing the default** is the one value `DEFAULT` (its night becomes today's tint by the rule
above): then rebuild both builds and the offline
bundles (the frame changes, so every bundle once), and re-run `ordpar/build_icons.py` (it draws
with a Windows font, so on this machine) and commit its two PNGs.
"""
import colorsys
import json

#: Today's night tint — the night accent of the site's own schemes is their hue at its
#: lightness and saturation (`tint`, after
#: `evidence/accent-63-2026-10-19/accent_swatches_dark.py`).
TINT_REF = "#e3b7c9"


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def tint(day):
    """`day`'s hue at `TINT_REF`'s lightness and saturation."""
    _h, l0, s0 = colorsys.rgb_to_hls(*[v / 255 for v in _rgb(TINT_REF)])
    hue, _l, _s = colorsys.rgb_to_hls(*[v / 255 for v in _rgb(day)])
    return "#%02x%02x%02x" % tuple(round(v * 255) for v in colorsys.hls_to_rgb(hue, l0, s0))


#: The schemes, in the order the settings page lists them. `night` is the night accent;
#: `night_line` (optional) a link's underline in night mode; `note` (optional) a line under the
#: choice on the settings page.
#:
#: * `wine` (B) and `burnt-orange` — Ordpar's own; colour in night mode too (Robin: "for our own
#:   colour scheme I prefer to have colour for the dark theme as well"). Wine is THE DEFAULT
#:   (Robin, 2026-10-20: "I want to use 'wine' as the default colour for now"), so its night is
#:   today's tint `#e3b7c9` (the default's rule, `effective`); chosen while not the default, its
#:   own computed tint. Burnt orange (site decisions 167, Robin 2026-11-05: "Let's add burnt
#:   orange with ligtness changed to 37%") is the accent lab's preset `#c2410c` at HSL 17° 88%
#:   37%: 6.0:1 as text on the page, 5.1:1 on the idiom pill, white on it 6.0:1. It replaced
#:   Oxblood `#6e1a2a` (Robin, 2026-11-05: "I'd like to remove this option"), whose stored
#:   value now paints as the default, as any unknown one.
#: * `ordbokene` — ordbokene.no's own maroon, exactly (sampled from its header and footer,
#:   decisions 63). An optional scheme that shows where it comes from, never Ordpar's own (Robin,
#:   2026-10-19). Its night mode copies ordbokene's rendered dark mode, which is black and white
#:   with coloured link underlines: headings and labels white, links underlined in #880e4f
#:   (sampled from screenshots of the live pages in dark mode, 2026-10-19,
#:   `evidence/chrome-63-2026-10-19/ordbokene/`; the underline also from Robin's capture).
#:   `#560027` appears ONLY under this named scheme (Robin, 2026-10-20).
COLOURS = [
    {"id": "wine", "name": "Wine", "day": "#6b0f2e", "night": tint("#6b0f2e")},
    {"id": "burnt-orange", "name": "Burnt orange", "day": "#b13a0b", "night": tint("#b13a0b")},
    {"id": "ordbokene", "name": "ordbokene.no's maroon", "day": "#560027",
     "night": "#ffffff", "night_line": "#880e4f",
     "note": "The colour ordbokene.no uses. Ordpar is independent of ordbokene.no."},
]

#: THE DEFAULT — one value (Robin, 2026-10-20: Wine "for now").
DEFAULT = "wine"


def by_id(cid):
    for c in COLOURS:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def default():
    return by_id(DEFAULT)


def effective(c):
    """The scheme as the site paints it: the DEFAULT's night is always today's (`TINT_REF`,
    no night line); any other scheme as its entry says."""
    if c["id"] != DEFAULT:
        return c
    e = dict(c, night=TINT_REF)
    e.pop("night_line", None)
    return e


def _vars(c):
    c = effective(c)
    out = ["--ordpar-maroon:%s" % c["day"],
           "--ordpar-maroon-rgb:%d,%d,%d" % _rgb(c["day"]),
           "--ordpar-tint:%s" % c["night"],
           "--ordpar-tint-rgb:%d,%d,%d" % _rgb(c["night"])]
    if c.get("night_line"):
        out.append("--ordpar-night-line:%s" % c["night_line"])
    return ";".join(out)


def css():
    """The schemes as CSS: the default on `:root`, every scheme on `html[data-accent=…]`
    (a scheme without `night_line` resets it, so a switch never inherits the default's)."""
    lines = ["/* the colour schemes (decisions 63): sitegen/colours.py, one entry each */",
             ":root{%s}" % _vars(default())]
    for c in COLOURS:
        extra = "" if effective(c).get("night_line") else ";--ordpar-night-line:initial"
        lines.append('html[data-accent="%s"]{%s%s}' % (c["id"], _vars(c), extra))
    # a link's underline in night mode, where the scheme sets one (ordbokene's dark mode)
    lines.append("html.nightMode a{text-decoration-color:var(--ordpar-night-line,currentColor)}")
    return "\n".join(lines) + "\n"


def settings_json():
    """The choices for the settings page: `[{id, name, day, night, note?, default?}]`."""
    out = []
    for c in map(effective, COLOURS):
        e = {"id": c["id"], "name": c["name"], "day": c["day"], "night": c["night"]}
        if c.get("note"):
            e["note"] = c["note"]
        if c["id"] == DEFAULT:
            e["default"] = True
        out.append(e)
    return json.dumps(out, ensure_ascii=False).replace("<", "\\u003c")
