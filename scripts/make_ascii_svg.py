"""Turn the prepped portrait into an animated, monochrome ASCII SVG.

Usage: python scripts/make_ascii_svg.py [source-prepped.png] [out.svg]

- Downscales the grayscale image to a ~100x53 character grid.
- Maps luminance onto a density ramp (light/sparse -> dark/dense).
  The ramp starts with a space, so the white background becomes empty.
- Each row is wrapped in a horizontal clip that sweeps left -> right with a
  small "cursor" block riding the edge, staggered top -> bottom.
- Plays once and freezes (SMIL, no loop, no JavaScript).
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RAMP = " .`:-=+*cs#%@"          # light/sparse -> dark/dense
COLS = 100                      # characters per row
MAX_ROWS = 60                   # safety cap (target ~53 for a square photo)

# Font metrics (monospace, 12px). Width:height of one cell ~ 0.53,
# which is what turns a square picture into ~100x53 characters.
FONT_SIZE = 12
CHAR_W = 7.2
LINE_H = 13.6
PAD = 18

INK = "#c9d1d9"                 # single light-gray fill (monochrome)
BG = "#0d1117"
BORDER = "#30363d"
CURSOR = "#e6edf3"

ROW_DUR = 0.35                  # seconds for one row to sweep
ROW_STAGGER = 0.07              # delay between consecutive rows

WHITE_CUTOFF = 240              # luminance above this -> background (space)
BLUR = 2.0                      # pre-downscale blur (px): kills pixel-level noise
CONTRAST = 5.0                  # S-curve strength on the tone map (0 = linear)
INVERT = True                   # bright pixels -> dense glyphs (reads better on dark bg)
                                # override with env INVERT=0 / INVERT=1


def to_grid(img: Image.Image) -> list[str]:
    gray = img.convert("L")
    arr = np.array(gray)

    # Crop to the subject (anything that is not pure white) so the portrait
    # fills the grid instead of the white margins.
    mask = arr < WHITE_CUTOFF
    ys, xs = np.where(mask)
    if len(xs):
        gray = gray.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    w, h = gray.size
    rows = int(round(h / w * COLS * (CHAR_W / LINE_H)))
    rows = max(1, min(rows, MAX_ROWS))

    if BLUR:
        gray = gray.filter(ImageFilter.GaussianBlur(BLUR))
    small = np.array(gray.resize((COLS, rows), Image.BOX)).astype(np.float32)

    # High contrast: stretch the subject's own luminance range onto the ramp.
    subject = small[small < WHITE_CUTOFF]
    lo, hi = (np.percentile(subject, 2), np.percentile(subject, 98)) if subject.size else (0, 255)
    hi = max(hi, lo + 1)
    dark = np.clip((hi - small) / (hi - lo), 0.0, 1.0)   # 0 = light, 1 = dark
    if CONTRAST:
        # Sigmoid around mid-gray: pushes mid-tones toward sparse/dense so
        # faces stop looking like uniform noise at 100 columns.
        dark = 1.0 / (1.0 + np.exp(-CONTRAST * (dark - 0.5)))
        dark = (dark - dark.min()) / max(dark.max() - dark.min(), 1e-6)
    invert = INVERT if os.environ.get("INVERT") is None else os.environ["INVERT"] == "1"
    if invert:
        # On a dark background bright pixels read better as dense glyphs.
        dark = 1.0 - dark
    dark[small >= WHITE_CUTOFF] = 0.0                     # background -> space

    idx = np.rint(dark * (len(RAMP) - 1)).astype(int)
    return ["".join(RAMP[i] for i in row).rstrip() for row in idx]


def build_svg(lines: list[str]) -> str:
    rows = len(lines)
    width = int(PAD * 2 + COLS * CHAR_W)
    height = int(PAD * 2 + rows * LINE_H)
    static = os.environ.get("STATIC") == "1"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, '
        f'Consolas, &quot;Liberation Mono&quot;, monospace" font-size="{FONT_SIZE}">',
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        "  <defs>",
    ]

    # One clip rectangle per row; its width grows from 0 to the row width.
    for i, line in enumerate(lines):
        if not line:
            continue
        y = PAD + i * LINE_H
        row_w = len(line) * CHAR_W
        t0 = i * ROW_STAGGER
        if static:
            anim = ""
        else:
            anim = (f'<animate attributeName="width" from="0" to="{row_w:.1f}" '
                    f'begin="{t0:.2f}s" dur="{ROW_DUR}s" fill="freeze"/>')
        out.append(
            f'    <clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" '
            f'width="{row_w if static else 0:.1f}" height="{LINE_H}">{anim}</rect></clipPath>'
        )
    out.append("  </defs>")

    out.append(f'  <g fill="{INK}">')
    for i, line in enumerate(lines):
        if not line:
            continue
        y = PAD + i * LINE_H + FONT_SIZE      # baseline
        lead = len(line) - len(line.lstrip(" "))
        body = line.lstrip(" ").replace(" ", "&#160;")   # keep inner gaps intact
        x = PAD + lead * CHAR_W
        body_w = (len(line) - lead) * CHAR_W
        out.append(
            f'    <text x="{x:.1f}" y="{y:.1f}" textLength="{body_w:.1f}" '
            f'lengthAdjust="spacing" clip-path="url(#r{i})">{body}</text>'
        )
    out.append("  </g>")

    # Cursor blocks: one per row, visible only while that row is being typed.
    if not static:
        out.append(f'  <g fill="{CURSOR}">')
        for i, line in enumerate(lines):
            if not line:
                continue
            y = PAD + i * LINE_H
            row_w = len(line) * CHAR_W
            t0 = i * ROW_STAGGER
            t1 = t0 + ROW_DUR
            out.append(
                f'    <rect x="{PAD}" y="{y:.1f}" width="{CHAR_W}" height="{LINE_H}" opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{t0:.2f}s"/>'
                f'<animate attributeName="x" from="{PAD}" to="{PAD + row_w:.1f}" '
                f'begin="{t0:.2f}s" dur="{ROW_DUR}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0" begin="{t1:.2f}s"/></rect>'
            )
        out.append("  </g>")

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "KamiSama-97-ascii.svg")
    if not src.exists():
        sys.exit(f"not found: {src} (run scripts/prep_photo.py first)")

    lines = to_grid(Image.open(src))
    print("\n".join(lines))
    dst.write_text(build_svg(lines), encoding="utf-8")
    print(f"\nwrote {dst}: {COLS}x{len(lines)} chars, "
          f"animation ~{len(lines) * ROW_STAGGER + ROW_DUR:.1f}s")


if __name__ == "__main__":
    main()
