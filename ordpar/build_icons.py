"""The app icon (decisions 61): Robin's chosen design, variant G at 0.95 — "cow patches" on a
maroon ground: a white patch with a maroon "Ord" behind, a pink patch with a maroon "Par" in
front, three small stray patches, Segoe UI Semibold. Drawn from the sketch
`docs/sessions/2026-09-19-ordpar-site-review/evidence/offline-app-61-2026-10-19/icon_cow_g.py`
(`draw(0.95)`, without the guide ring); the drawing code below is that script's, unchanged.

The art sits inside the maskable safe zone (a centred circle of 80 % of the width) on a
full-bleed ground, so ONE drawing serves both `any` and `maskable`: a launcher that masks it
cuts only ground, and one that does not shows the square tile.

The font is Windows' own (`C:/Windows/Fonts/seguisb.ttf`), so the PNGs are generated once,
here, and committed under `ordpar/site/icons/` — the site build copies them with the rest of
`ordpar/site/` and never draws them. Re-run only when the design changes.

Usage: python ordpar/build_icons.py [--out ordpar/site/icons]
"""
import argparse
import math
import os

import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ordpar.sitegen import colours  # noqa: E402  -- decisions 63: the icon's ground is the default scheme's

#: The ground and the letters: the DEFAULT colour scheme's day accent (decisions 63 — the icon
#: follows the default only; since 2026-10-20 Wine, #6b0f2e). Re-run this script when the default
#: changes, and commit the two PNGs.
MAROON = tuple(int(colours.default()["day"][i:i + 2], 16) for i in (1, 3, 5))
PINK, WHITE = (227, 183, 201), (255, 255, 255)
S = 768
F = "C:/Windows/Fonts/seguisb.ttf"
P1 = [(2, .10, .3), (3, .07, 1.9), (5, .04, .7)]
P2 = [(2, .09, 2.2), (3, .08, .4), (4, .05, 2.8)]
#: the pick (decisions 61: variant G, bigger, at 0.95)
SCALE = 0.95
SIZES = (192, 512)


def blob(cx, cy, rx, ry, terms, rot=0.0, n=240):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + sum(amp * math.sin(f * a + ph) for f, amp, ph in terms)
        x, y = rx * k * math.cos(a), ry * k * math.sin(a)
        pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return pts


def put(d, text, size, fill, cx, cy):
    f = ImageFont.truetype(F, size)
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), text, font=f, fill=fill)


def draw(k):
    """k: the size of the patches and text against the frame (G as first sketched ~ 0.80)."""
    im = Image.new("RGBA", (S, S), MAROON + (255,))
    d = ImageDraw.Draw(im)
    c = S / 2

    def p(x, y):
        return c + (x - c) * k, c + (y - c) * k
    for (x, y), r, t, col in (((560, 200), 48, [(3, .12, .5)], PINK), ((190, 560), 40, [(2, .15, 1.0)], WHITE),
                              ((640, 330), 22, [(3, .1, 2.0)], PINK)):
        d.polygon(blob(*p(x, y), r * k, r * .8 * k, t), fill=col)
    c1, c2 = p(300, 300), p(468, 480)
    d.polygon(blob(*c1, 190 * k, 120 * k, P1, rot=-0.12), fill=WHITE)
    d.polygon(blob(*c2, 205 * k, 135 * k, P2, rot=0.10), fill=MAROON)
    d.polygon(blob(*c2, 190 * k, 120 * k, P2, rot=0.10), fill=PINK)
    put(d, "Ord", round(128 * k), MAROON, *c1)
    put(d, "Par", round(128 * k), MAROON, *c2)
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "site", "icons"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    big = draw(SCALE).convert("RGB")         # opaque: a full-bleed ground, no alpha needed
    for n in SIZES:
        path = os.path.join(a.out, "icon-%d.png" % n)
        big.resize((n, n), Image.LANCZOS).save(path, optimize=True)
        print("wrote", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
