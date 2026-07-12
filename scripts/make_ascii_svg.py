#!/usr/bin/env python3
"""Render source-prepped.png as a monochrome ASCII-art SVG that "types"
itself in like a terminal, one row at a time.

Usage:
    python scripts/make_ascii_svg.py            # animated (blank at t=0)
    STATIC=1 python scripts/make_ascii_svg.py   # final frame, no animation

Output: avi-ascii-light.svg + avi-ascii-dark.svg. Two files because
Safari ignores prefers-color-scheme media queries inside SVGs rendered
via <img>; the README picks the right one with a <picture> element.
"""
import html
import os
import sys

import numpy as np
from PIL import Image

# ============================= CONFIG ======================================
INPUT = "source-prepped.png"
OUTPUT_BASE = "avi-ascii"   # writes {OUTPUT_BASE}-light.svg and -dark.svg

COLS = 78            # characters per row (resolution of the portrait)
CHAR_ASPECT = 0.52   # width/height of a monospace glyph cell

CONTRAST = 1.35      # >1 pushes mids apart; tune until the face reads well
GAMMA = 0.85         # <1 brightens mids, >1 darkens them
WHITE_FLOOR = 0.06   # luminance below this renders as blank space

CHARSET = " .:-=+*#%@"   # dark -> bright ramp (index 0 must be a space)

FG_LIGHT = "#24292f"     # ink color on light backgrounds
FG_DARK = "#c9d1d9"      # ink color on dark backgrounds

FONT_SIZE = 10           # px; cell height derives from this
ROW_TYPE_SECONDS = 0.05  # how long each row takes to "type" in
CURSOR = True            # blinking block cursor at the end
# ===========================================================================


def to_grid(path: str) -> list[str]:
    img = Image.open(path).convert("LA")
    w, h = img.size
    rows = max(1, round(COLS * (h / w) * CHAR_ASPECT))
    img = img.resize((COLS, rows), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float64) / 255.0
    lum, alpha = arr[:, :, 0], arr[:, :, 1]

    lum = np.clip((lum - 0.5) * CONTRAST + 0.5, 0.0, 1.0)
    lum = np.power(lum, GAMMA)
    lum[alpha < 0.35] = 0.0          # transparent background -> blank
    lum[lum < WHITE_FLOOR] = 0.0     # floor -> blank

    idx = np.clip((lum * (len(CHARSET) - 1)).round().astype(int), 0, len(CHARSET) - 1)
    return ["".join(CHARSET[i] for i in row) for row in idx]


def render(grid: list[str], fg: str, static: bool) -> str:
    cell_h = FONT_SIZE + 1
    cell_w = FONT_SIZE * CHAR_ASPECT / 0.52 * 0.6
    width = round(COLS * cell_w + 20)
    height = len(grid) * cell_h + 20

    css = f"""
    text {{
      font: {FONT_SIZE}px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      fill: {fg};
      white-space: pre;
    }}
    """
    if not static:
        css += f"""
    .row {{
      clip-path: inset(0 100% 0 0);
      animation: type {ROW_TYPE_SECONDS}s steps({COLS}) forwards;
    }}
    @keyframes type {{ to {{ clip-path: inset(0 -2% 0 0); }} }}
    .cursor {{ animation: blink 1s steps(1) infinite; animation-delay: {len(grid) * ROW_TYPE_SECONDS:.2f}s; opacity: 0; }}
    @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
    """
        for i in range(len(grid)):
            css += f".row:nth-of-type({i + 1}) {{ animation-delay: {i * ROW_TYPE_SECONDS:.2f}s; }}\n"

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="ASCII portrait">',
        f"<style>{css}</style>",
    ]
    for i, row in enumerate(grid):
        y = 10 + (i + 1) * cell_h
        cls = "" if static else ' class="row"'
        lines.append(
            f'<text x="10" y="{y}"{cls} xml:space="preserve" textLength="{COLS * cell_w:.0f}" '
            f'lengthAdjust="spacingAndGlyphs">{html.escape(row)}</text>'
        )
    if CURSOR and not static:
        lines.append(
            f'<text x="10" y="{10 + (len(grid) + 1) * cell_h}" class="cursor">&#9608;</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    static = os.environ.get("STATIC") == "1"
    if not os.path.exists(INPUT):
        sys.exit(f"[ascii] missing {INPUT} -- run prep_photo.py first")

    grid = to_grid(INPUT)
    for theme, fg in (("light", FG_LIGHT), ("dark", FG_DARK)):
        path = f"{OUTPUT_BASE}-{theme}.svg"
        with open(path, "w") as f:
            f.write(render(grid, fg, static))
        print(f"[ascii] wrote {path} ({COLS}x{len(grid)} chars, static={static})")


if __name__ == "__main__":
    main()
