"""Fetch the public GitHub contribution calendar and derive stats.

Usage: python scripts/fetch_contributions.py [username]

- Downloads https://github.com/users/<user>/contributions (public HTML, no token).
- Parses the day cells with BeautifulSoup (date, level 0-4, count from tooltip).
- Writes data/contributions.json with the raw days plus derived stats:
  total, current streak, longest streak, best day and monthly totals.
"""
import json
import re
import sys
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER = sys.argv[1] if len(sys.argv) > 1 else "KamiSama-97"
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path("data/contributions.json")

COUNT_RE = re.compile(r"^(\d[\d,]*)\s+contribution")


def fetch_html() -> str:
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (profile-readme)"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # Tooltips carry the count: "No contributions on ..." / "3 contributions on ..."
    tips = {t["for"]: t.get_text(" ", strip=True) for t in soup.find_all("tool-tip") if t.get("for")}

    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        text = tips.get(td.get("id", ""), "")
        m = COUNT_RE.match(text)
        count = int(m.group(1).replace(",", "")) if m else 0
        days.append({
            "date": td["data-date"],
            "level": int(td.get("data-level", 0)),
            "count": count,
        })
    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days: list[dict]) -> dict:
    by_date = {date.fromisoformat(d["date"]): d["count"] for d in days}
    if not by_date:
        return {"total": 0, "current_streak": 0, "longest_streak": 0,
                "best_day": None, "monthly": {}}

    total = sum(by_date.values())

    # longest streak of consecutive active days
    longest = run = 0
    prev = None
    for d in sorted(by_date):
        if by_date[d] > 0:
            run = run + 1 if (prev is not None and d - prev == timedelta(days=1) and by_date[prev] > 0) else 1
        else:
            run = 0
        longest = max(longest, run)
        prev = d

    # current streak: count back from the last day in the calendar
    # (today may still be empty, so an empty last day does not break it)
    last = max(by_date)
    cur = 0
    d = last if by_date[last] > 0 else last - timedelta(days=1)
    while d in by_date and by_date[d] > 0:
        cur += 1
        d -= timedelta(days=1)

    best_date = max(by_date, key=lambda k: by_date[k])
    best = {"date": best_date.isoformat(), "count": by_date[best_date]} if by_date[best_date] > 0 else None

    monthly: "OrderedDict[str, int]" = OrderedDict()
    for d in sorted(by_date):
        key = d.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + by_date[d]

    return {
        "total": total,
        "current_streak": cur,
        "longest_streak": longest,
        "best_day": best,
        "monthly": monthly,
    }


def main() -> None:
    print(f"fetching {URL} ...")
    html = fetch_html()
    days = parse_days(html)
    if not days:
        sys.exit("no day cells found: GitHub markup may have changed")

    stats = derive_stats(days)
    payload = {
        "user": USER,
        "fetched_at": date.today().isoformat(),
        "from": days[0]["date"],
        "to": days[-1]["date"],
        "stats": stats,
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT}: {len(days)} days, {stats['total']} contributions, "
          f"streak {stats['current_streak']} (longest {stats['longest_streak']})")


if __name__ == "__main__":
    main()
