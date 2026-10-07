"""Render data/contributions.json as an animated SVG heatmap.

Usage: python scripts/render_heatmap_svg.py   -> contrib-heatmap.svg

- 53 weeks x 7 days of rounded boxes, GitHub-style, dark palette.
- Levels 0-4 come from GitHub; the best day(s) get level 5 (neon).
- One-shot reveal: each week column slides down and fades in, staggered
  left -> right, so the reveal sweeps diagonally. CSS keyframes inside the
  SVG, plays on load, then freezes (no loop, no JavaScript).
- Less -> More legend and a stats footer.
"""
import json
from datetime import date
from pathlib import Path

SRC = Path("data/contributions.json")
OUT = Path("contrib-heatmap.svg")

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

CELL = 12          # box size
GAP = 3            # gap between boxes
STEP = CELL + GAP
RADIUS = 2.5
LEFT = 36          # room for weekday labels
TOP = 46           # room for title + month labels
WEEKS = 53

BG = "#0d1117"
BORDER = "#30363d"
FG = "#c9d1d9"
MUTED = "#8b949e"
ACCENT = "#58a6ff"

COL_DELAY = 0.035  # seconds between consecutive week columns
COL_DUR = 0.5      # slide/fade duration of one column

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt(n: int) -> str:
    return f"{n:,}"


def build(data: dict) -> str:
    days = data["days"]
    stats = data["stats"]
    best = stats.get("best_day")
    best_count = best["count"] if best else 0

    # Layout: GitHub's calendar starts on a Sunday; column = week index.
    start = date.fromisoformat(days[0]["date"])
    cols: dict[int, list[dict]] = {}
    for d in days:
        dt = date.fromisoformat(d["date"])
        col, row = divmod((dt - start).days, 7)
        cols.setdefault(col, []).append({**d, "row": row, "dt": dt})
    ncols = min(max(cols) + 1, WEEKS + 1)

    width = LEFT + ncols * STEP + 24
    height = TOP + 7 * STEP + 70

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, '
        f'Consolas, &quot;Liberation Mono&quot;, monospace" font-size="11">',
        "  <style>",
        "    .wk { opacity: 0; animation: drop 0.5s ease-out forwards; }",
        "    @keyframes drop {",
        "      from { opacity: 0; transform: translateY(-14px); }",
        "      to   { opacity: 1; transform: translateY(0); }",
        "    }",
        "    .fade { opacity: 0; animation: fadein 0.6s ease-out forwards; }",
        "    @keyframes fadein { to { opacity: 1; } }",
        "  </style>",
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        f'  <text x="{LEFT}" y="22" fill="{FG}" font-size="13" font-weight="bold">'
        f'{fmt(stats["total"])} contributions in the last year</text>',
    ]

    # weekday labels
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = TOP + row * STEP + CELL - 2
        out.append(f'  <text x="{LEFT - 8}" y="{y}" text-anchor="end" fill="{MUTED}">{label}</text>')

    # month labels: first column whose first day falls within the first week of a month
    seen: set[int] = set()
    for col in range(ncols):
        cells = cols.get(col, [])
        if not cells:
            continue
        m = cells[0]["dt"].month
        if m not in seen and cells[0]["dt"].day <= 7:
            seen.add(m)
            x = LEFT + col * STEP
            out.append(f'  <text x="{x}" y="{TOP - 8}" fill="{MUTED}">{MONTHS[m - 1]}</text>')

    # the boxes: one <g> per week column, each with its own animation delay
    for col in range(ncols):
        delay = col * COL_DELAY
        out.append(f'  <g class="wk" style="animation-delay:{delay:.3f}s">')
        for c in cols.get(col, []):
            level = c["level"]
            if best_count and c["count"] == best_count:
                level = 5
            x = LEFT + col * STEP
            y = TOP + c["row"] * STEP
            out.append(
                f'    <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RADIUS}" '
                f'fill="{PALETTE[level]}"><title>{c["count"]} on {c["date"]}</title></rect>'
            )
        out.append("  </g>")

    # footer appears once the sweep has finished
    total_delay = ncols * COL_DELAY + COL_DUR
    fy = TOP + 7 * STEP + 28
    out.append(f'  <g class="fade" style="animation-delay:{total_delay:.2f}s">')

    # legend Less -> More (right aligned)
    lx = width - 24 - len(PALETTE) * STEP - 44
    out.append(f'    <text x="{lx - 6}" y="{fy + CELL - 2}" text-anchor="end" fill="{MUTED}">Less</text>')
    for i, color in enumerate(PALETTE):
        out.append(f'    <rect x="{lx + i * STEP}" y="{fy}" width="{CELL}" height="{CELL}" '
                   f'rx="{RADIUS}" fill="{color}"/>')
    out.append(f'    <text x="{lx + len(PALETTE) * STEP + 4}" y="{fy + CELL - 2}" fill="{MUTED}">More</text>')

    # stats line (left)
    best_txt = f'{fmt(best["count"])} on {best["date"]}' if best else "n/a"
    parts = [
        f'<tspan fill="{MUTED}">streak </tspan><tspan fill="{ACCENT}">{stats["current_streak"]}d</tspan>',
        f'<tspan fill="{MUTED}">  longest </tspan><tspan fill="{ACCENT}">{stats["longest_streak"]}d</tspan>',
        f'<tspan fill="{MUTED}">  best day </tspan><tspan fill="{ACCENT}">{best_txt}</tspan>',
    ]
    out.append(f'    <text x="{LEFT}" y="{fy + CELL - 2}">{"".join(parts)}</text>')

    # updated-at (small, bottom-left)
    out.append(f'    <text x="{LEFT}" y="{fy + 30}" fill="{MUTED}" font-size="10">'
               f'updated {data["fetched_at"]} · github.com/{data["user"]}</text>')
    out.append("  </g>")

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}: run scripts/fetch_contributions.py first")
    data = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.write_text(build(data), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
