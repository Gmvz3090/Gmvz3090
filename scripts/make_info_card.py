#!/usr/bin/env python3
"""Render a terminal-styled monochrome info card as info-card.svg.

Edit ROWS and HOST below, then run:
    python scripts/make_info_card.py            # animated
    STATIC=1 python scripts/make_info_card.py   # final frame (for previews)
"""
import html
import os

# ============================= CONFIG ======================================
HOST = "franek@soppo"

# Each entry is (label, value) -- or None for a blank separator line.
ROWS = [
    ("name", "Franciszek Malko"),
    ("role", "SWE intern @ soppo"),
    ("location", "Poland"),
    None,
    ("languages", "Node.js / C++ / Python"),
    ("stack", "React / Node / NumPy / OpenCV"),
    ("interests", "ML from first principles, telemetry"),
    None,
    ("building", "PureNN -- neural net in raw C++"),
    ("shipped", "GetAnomaly -- satellite telemetry app"),
    None,
    ("linkedin", "in/franciszek-malko-a8120231b"),
    ("instagram", "@franek.malko"),
]

W = 560          # viewBox width; rendered at width=490 in the README
H = 400          # viewBox height; bump this if rows overflow
FONT_SIZE = 15
ROW_H = 24       # vertical distance between rows
LABEL_W = 118    # px reserved for the label column
TYPE_STAGGER = 0.18   # seconds between each row appearing

FG_LIGHT, DIM_LIGHT, BORDER_LIGHT = "#24292f", "#57606a", "#d0d7de"
FG_DARK, DIM_DARK, BORDER_DARK = "#f0f6fc", "#adbac7", "#444c56"

OUTPUT_BASE = "info-card"   # writes {OUTPUT_BASE}-light.svg and -dark.svg
# ===========================================================================


def render(fg: str, dim: str, border: str, bar_opacity: float, static: bool) -> str:
    css = f"""
    text {{ font: {FONT_SIZE}px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; }}
    .fg {{ fill: {fg}; }} .dim {{ fill: {dim}; }}
    .frame {{ stroke: {border}; fill: none; }}
    .bar {{ fill: {border}; fill-opacity: {bar_opacity}; }}
    """
    if not static:
        css += """
    .line { opacity: 0; animation: reveal 0.4s ease-out forwards; }
    @keyframes reveal { from { opacity: 0; transform: translateX(-6px); }
                        to { opacity: 1; transform: none; } }
    """
    body = []
    y = 78
    visible = 0
    for row in ROWS:
        if row is None:
            y += ROW_H // 2
            continue
        label, value = row
        delay = 0.3 + visible * TYPE_STAGGER
        body.append(
            f'<g class="line" style="animation-delay:{delay:.2f}s">'
            f'<text x="28" y="{y}" class="dim">{html.escape(label)}</text>'
            f'<text x="{28 + LABEL_W}" y="{y}" class="dim">::</text>'
            f'<text x="{28 + LABEL_W + 26}" y="{y}" class="fg">{html.escape(value)}</text>'
            f"</g>"
        )
        visible += 1
        y += ROW_H

    prompt_delay = 0.3 + visible * TYPE_STAGGER
    body.append(
        f'<g class="line" style="animation-delay:{prompt_delay:.2f}s">'
        f'<text x="28" y="{y + ROW_H // 2}"><tspan class="dim">$</tspan>'
        f'<tspan class="fg" dx="8">&#9608;</tspan></text></g>'
    )

    needed = y + ROW_H * 2
    height = max(H, needed)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="info card">
<style>{css}</style>
<rect x="1.5" y="1.5" width="{W - 3}" height="{height - 3}" rx="10" class="frame" stroke-width="1.5"/>
<rect x="1.5" y="1.5" width="{W - 3}" height="34" rx="10" class="bar"/>
<rect x="1.5" y="20" width="{W - 3}" height="16" class="bar"/>
<circle cx="22" cy="18.5" r="5.5" class="frame" stroke-width="1.2"/>
<circle cx="42" cy="18.5" r="5.5" class="frame" stroke-width="1.2"/>
<circle cx="62" cy="18.5" r="5.5" class="frame" stroke-width="1.2"/>
<text x="{W // 2}" y="23" text-anchor="middle" class="dim">{html.escape(HOST)}: ~/about</text>
{chr(10).join(body)}
</svg>"""
    return svg, height, visible


def main() -> None:
    static = os.environ.get("STATIC") == "1"
    themes = (
        ("light", FG_LIGHT, DIM_LIGHT, BORDER_LIGHT, 0.35),
        ("dark", FG_DARK, DIM_DARK, BORDER_DARK, 0.5),
    )
    for theme, fg, dim, border, bar_opacity in themes:
        svg, height, visible = render(fg, dim, border, bar_opacity, static)
        path = f"{OUTPUT_BASE}-{theme}.svg"
        with open(path, "w") as f:
            f.write(svg)
        print(f"[card] wrote {path} ({W}x{height}, {visible} rows)")


if __name__ == "__main__":
    main()
