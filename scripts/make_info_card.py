"""Render a neofetch-style info card as an animated SVG.

Usage: python scripts/make_info_card.py            -> info-card.svg (animated)
       STATIC=1 python scripts/make_info_card.py   -> frozen frame for local preview

Hand-built SVG: a terminal title bar and colored key/value rows.
Each line fades in and slides up with a short stagger (SMIL, plays once).
No JavaScript, no external CSS, no fonts to download.
"""
import os
from pathlib import Path

OUT = Path("info-card.svg")
USER = "KamiSama-97"
HOST = "github"

# --- Edit these ------------------------------------------------------------
# A string renders as one line; a list renders one line per item
# (keep each line under ~43 characters so it fits the 490px card).
ROWS = [
    ("Now",        ["Senior Genesys Cloud Engineer",
                    "@ Sabio Group · Santander Openbank"]),
    ("Prev",       ["Lead Full-Stack Developer @ GoConcept",
                    "Node.js · Go · Java · React · PostGIS"]),
    ("Stack",      ["Genesys Cloud · Architect · Data Actions",
                    "TypeScript · Node.js · Python · Go · Java",
                    "Terraform · CX as Code · Lambda · Docker",
                    "PostgreSQL · PostGIS · MongoDB · Redis"]),
    ("Highlights", ["- MCP server for Genesys Cloud: 400+ tools",
                    "- Platform audits: 2 weeks -> 10 minutes",
                    "- Full org migrations in ~2 hours",
                    "- 7 projects across 6 countries"]),
]
# ---------------------------------------------------------------------------

# Geometry (matches the ASCII portrait: same background, border and font).
WIDTH = 490
PAD_X = 24
TITLE_H = 36
LINE_H = 24
FONT_SIZE = 13
KEY_W = 104                       # column where values start (after the key)

BG = "#0d1117"
BORDER = "#30363d"
TITLE_BG = "#161b22"
FG = "#c9d1d9"
MUTED = "#8b949e"
KEY = "#58a6ff"                   # blue keys
PROMPT_USER = "#3fb950"           # green user@host
PROMPT_PATH = "#d2a8ff"           # purple path
DOTS = ("#ff5f56", "#ffbd2e", "#27c93f")

STAGGER = 0.12                    # seconds between lines
DUR = 0.45                        # fade+slide duration per line


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def animated_group(i: int, static: bool) -> str:
    """Opening tag for a line group with fade + slide-up animation."""
    if static:
        return "<g>"
    t0 = i * STAGGER
    return (
        f'<g opacity="0">'
        f'<animate attributeName="opacity" from="0" to="1" begin="{t0:.2f}s" dur="{DUR}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="0 8" to="0 0" '
        f'begin="{t0:.2f}s" dur="{DUR}s" fill="freeze"/>'
    )


def build() -> str:
    static = os.environ.get("STATIC") == "1"

    # Flatten rows into (key, value) lines; list values become extra lines.
    lines: list[tuple[str, str]] = []
    for key, val in ROWS:
        if isinstance(val, list):
            for j, item in enumerate(val):
                lines.append((key if j == 0 else "", item))
        else:
            lines.append((key, val))

    # +1 for prompt line, +1 for the separator, +1 for the trailing cursor line
    body_lines = 1 + 1 + len(lines) + 1
    height = TITLE_H + 16 + body_lines * LINE_H + 12

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, '
        f'Consolas, &quot;Liberation Mono&quot;, monospace" font-size="{FONT_SIZE}">',
        f'  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="8" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        # title bar
        f'  <path d="M0.5 8.5 a8 8 0 0 1 8 -8 h{WIDTH - 17} a8 8 0 0 1 8 8 v{TITLE_H - 8} h-{WIDTH - 1} z" '
        f'fill="{TITLE_BG}"/>',
        f'  <line x1="0.5" y1="{TITLE_H + 0.5}" x2="{WIDTH - 0.5}" y2="{TITLE_H + 0.5}" stroke="{BORDER}"/>',
    ]
    for k, c in enumerate(DOTS):
        svg.append(f'  <circle cx="{18 + k * 20}" cy="{TITLE_H / 2}" r="6" fill="{c}"/>')
    svg.append(
        f'  <text x="{WIDTH / 2}" y="{TITLE_H / 2 + 5}" text-anchor="middle" fill="{MUTED}" '
        f'font-size="12">{USER}@{HOST}: ~</text>'
    )

    y = TITLE_H + 16 + FONT_SIZE + 2
    i = 0

    # prompt line
    svg.append(f'  {animated_group(i, static)}')
    svg.append(
        f'    <text x="{PAD_X}" y="{y}"><tspan fill="{PROMPT_USER}">{USER}@{HOST}</tspan>'
        f'<tspan fill="{FG}">:</tspan><tspan fill="{PROMPT_PATH}">~</tspan>'
        f'<tspan fill="{FG}">$ neofetch</tspan></text>'
    )
    svg.append("  </g>")
    i += 1
    y += LINE_H

    # separator
    svg.append(f'  {animated_group(i, static)}')
    svg.append(f'    <text x="{PAD_X}" y="{y}" fill="{MUTED}">{"-" * 52}</text>')
    svg.append("  </g>")
    i += 1
    y += LINE_H

    # key/value lines
    for key, val in lines:
        svg.append(f'  {animated_group(i, static)}')
        if key:
            svg.append(
                f'    <text x="{PAD_X}" y="{y}" fill="{KEY}" font-weight="bold">{esc(key)}</text>'
            )
        svg.append(f'    <text x="{PAD_X + KEY_W}" y="{y}" fill="{FG}">{esc(val)}</text>')
        svg.append("  </g>")
        i += 1
        y += LINE_H

    # trailing prompt with blinking cursor (blink is the only loop; cheap)
    svg.append(f'  {animated_group(i, static)}')
    svg.append(
        f'    <text x="{PAD_X}" y="{y}"><tspan fill="{PROMPT_USER}">{USER}@{HOST}</tspan>'
        f'<tspan fill="{FG}">:</tspan><tspan fill="{PROMPT_PATH}">~</tspan>'
        f'<tspan fill="{FG}">$ </tspan></text>'
    )
    cursor_x = PAD_X + 8.4 * (len(f"{USER}@{HOST}:~$ "))
    blink = "" if static else (
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" '
        f'dur="1.1s" begin="{i * STAGGER + DUR:.2f}s" repeatCount="indefinite"/>'
    )
    svg.append(
        f'    <rect x="{cursor_x:.1f}" y="{y - FONT_SIZE + 1}" width="8" height="{FONT_SIZE + 2}" '
        f'fill="{FG}">{blink}</rect>'
    )
    svg.append("  </g>")

    svg.append("</svg>")
    return "\n".join(svg) + "\n"


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
