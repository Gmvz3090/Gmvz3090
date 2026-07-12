#!/usr/bin/env python3
"""Render contributions.json as a GitHub-style monochrome heatmap SVG.

Cells reveal column by column on load; includes a Less->More legend and
real streak stats. Run fetch_contributions.py first.

    python scripts/render_heatmap_svg.py
"""
import datetime as dt
import json
import os
import sys

# ============================= CONFIG ======================================
INPUT = "contributions.json"
OUTPUT_BASE = "contrib-heatmap"   # writes {OUTPUT_BASE}-light.svg and -dark.svg

CELL = 11        # cell size, px
GAP = 3          # gap between cells, px
RADIUS = 2       # cell corner radius
COL_STAGGER = 0.018   # seconds between successive week-columns appearing
DAY_STAGGER = 0.004   # extra delay per weekday inside a column

# Color ramps, level 0..4 (GitHub's data-level). Classic GitHub greens.
LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

FG_LIGHT, DIM_LIGHT = "#24292f", "#57606a"
FG_DARK, DIM_DARK = "#c9d1d9", "#8b949e"
# ===========================================================================

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def streaks(days):
    current = longest = run = 0
    prev = None
    for d in days:
        date = dt.date.fromisoformat(d["date"])
        if d["count"] > 0:
            run = run + 1 if prev and (date - prev).days == 1 else 1
            longest = max(longest, run)
            prev = date
        else:
            if prev and (date - prev).days > 1:
                run = 0
    today = dt.date.fromisoformat(days[-1]["date"])
    # Current streak: walk backwards; today may still be 0 without breaking it.
    by_date = {d["date"]: d["count"] for d in days}
    cursor = today
    if by_date.get(cursor.isoformat(), 0) == 0:
        cursor -= dt.timedelta(days=1)
    while by_date.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= dt.timedelta(days=1)
    return current, longest


def render(days, palette, fg, dim, static: bool) -> str:
    total = sum(d["count"] for d in days)
    current, longest = streaks(days)

    # Bucket into week columns (calendar weeks starting Sunday, like GitHub).
    weeks: list[list[dict | None]] = []
    col: list[dict | None] = []
    first_dow = (dt.date.fromisoformat(days[0]["date"]).weekday() + 1) % 7
    col = [None] * first_dow
    for d in days:
        col.append(d)
        if len(col) == 7:
            weeks.append(col)
            col = []
    if col:
        weeks.append(col + [None] * (7 - len(col)))

    left, top = 32, 30
    grid_w = len(weeks) * (CELL + GAP)
    width = left + grid_w + 10
    height = top + 7 * (CELL + GAP) + 46

    css = f"""
    text {{ font: 10px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {dim}; }}
    .stat {{ font-size: 11px; fill: {fg}; }}
    {"".join(f".l{i}{{fill:{c}}}" for i, c in enumerate(palette))}
    """
    if not static:
        css += """
    .c { opacity: 0; animation: pop 0.3s ease-out forwards; }
    @keyframes pop { from { opacity: 0; } to { opacity: 1; } }
    """

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="contribution heatmap">',
        f"<style>{css}</style>",
    ]

    # Month labels: first week-column whose top cell enters a new month.
    seen = None
    for wi, week in enumerate(weeks):
        first = next((d for d in week if d), None)
        if not first:
            continue
        month = dt.date.fromisoformat(first["date"]).month
        if month != seen:
            seen = month
            parts.append(
                f'<text x="{left + wi * (CELL + GAP)}" y="{top - 10}">{MONTHS[month - 1]}</text>'
            )

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(
            f'<text x="0" y="{top + row * (CELL + GAP) + CELL - 2}">{label}</text>'
        )

    for wi, week in enumerate(weeks):
        for di, d in enumerate(week):
            if d is None:
                continue
            x = left + wi * (CELL + GAP)
            y = top + di * (CELL + GAP)
            cls = f"l{d['level']}" if static else f"c l{d['level']}"
            delay = (
                ""
                if static
                else f' style="animation-delay:{wi * COL_STAGGER + di * DAY_STAGGER:.3f}s"'
            )
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RADIUS}" '
                f'class="{cls}"{delay}/>'
            )

    # Footer: stats on the left, Less->More legend on the right.
    fy = top + 7 * (CELL + GAP) + 26
    parts.append(
        f'<text x="{left}" y="{fy}" class="stat">{total} contributions in the last year'
        f'&#160;&#160;&#183;&#160;&#160;current streak {current}d'
        f'&#160;&#160;&#183;&#160;&#160;longest {longest}d</text>'
    )
    lx = width - 10 - 5 * (CELL + GAP) - 66
    parts.append(f'<text x="{lx - 34}" y="{fy}">Less</text>')
    for i in range(5):
        parts.append(
            f'<rect x="{lx + i * (CELL + GAP)}" y="{fy - CELL + 1}" width="{CELL}" '
            f'height="{CELL}" rx="{RADIUS}" class="l{i}"/>'
        )
    parts.append(f'<text x="{lx + 5 * (CELL + GAP) + 4}" y="{fy}">More</text>')
    parts.append("</svg>")
    return "\n".join(parts), total, current, longest


def main() -> None:
    static = os.environ.get("STATIC") == "1"
    if not os.path.exists(INPUT):
        sys.exit(f"[heatmap] missing {INPUT} -- run fetch_contributions.py first")
    with open(INPUT) as f:
        days = json.load(f)

    themes = (
        ("light", LIGHT, FG_LIGHT, DIM_LIGHT),
        ("dark", DARK, FG_DARK, DIM_DARK),
    )
    for theme, palette, fg, dim in themes:
        svg, total, current, longest = render(days, palette, fg, dim, static)
        path = f"{OUTPUT_BASE}-{theme}.svg"
        with open(path, "w") as f:
            f.write(svg)
        print(
            f"[heatmap] wrote {path}: {total} contributions, "
            f"streak {current}d (longest {longest}d)"
        )


if __name__ == "__main__":
    main()
