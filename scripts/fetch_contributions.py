#!/usr/bin/env python3
"""Scrape the public GitHub contribution calendar (no auth needed).

    GH_PROFILE_USER=<username> python scripts/fetch_contributions.py

Writes contributions.json: a date-sorted list of {date, count, level}.
"""
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

# ============================= CONFIG ======================================
GH_PROFILE_USER = os.environ.get("GH_PROFILE_USER", "Gmvz3090")
OUTPUT = "contributions.json"
# ===========================================================================

URL = f"https://github.com/users/{GH_PROFILE_USER}/contributions"


def main() -> None:
    print(f"[fetch] {URL}")
    resp = requests.get(
        URL, headers={"User-Agent": "profile-readme-heatmap"}, timeout=30
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Cell counts live in <tool-tip for="<cell id>"> elements.
    tips = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        m = re.match(r"(\d+)|No contributions", tip.get_text(strip=True))
        tips[target] = int(m.group(1)) if m and m.group(1) else 0

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        date = td.get("data-date")
        if not date:
            continue
        days.append(
            {
                "date": date,
                "count": tips.get(td.get("id"), 0),
                "level": int(td.get("data-level", 0)),
            }
        )

    if not days:
        sys.exit("[fetch] no calendar cells found -- GitHub markup may have changed")

    days.sort(key=lambda d: d["date"])
    with open(OUTPUT, "w") as f:
        json.dump(days, f, indent=1)
    total = sum(d["count"] for d in days)
    print(f"[fetch] wrote {OUTPUT}: {len(days)} days, {total} contributions")


if __name__ == "__main__":
    main()
