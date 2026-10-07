"""Prepare a portrait for ASCII conversion.

Usage: python scripts/prep_photo.py source-photo.jpg

Steps:
  1. Remove the background with rembg (subject becomes RGBA with alpha mask).
  2. Boost local contrast with OpenCV CLAHE so facial features survive
     the heavy downscale to a character grid.
  3. Composite over pure white: the background turns into spaces later.

Output: source-prepped.png (8-bit grayscale).
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

OUT = Path("source-prepped.png")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/prep_photo.py <photo>")
    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"not found: {src}")

    print(f"[1/3] removing background from {src} ...")
    rgba = remove(Image.open(src).convert("RGBA"))

    print("[2/3] boosting local contrast (CLAHE) ...")
    rgb = np.array(rgba.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4))
    gray = clahe.apply(gray)

    print("[3/3] compositing over white ...")
    alpha = np.array(rgba.getchannel("A")).astype(np.float32) / 255.0
    white = np.full_like(gray, 255, dtype=np.uint8)
    out = (gray.astype(np.float32) * alpha + white.astype(np.float32) * (1 - alpha))
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out, mode="L").save(OUT)
    print(f"wrote {OUT} ({out.shape[1]}x{out.shape[0]})")


if __name__ == "__main__":
    main()
