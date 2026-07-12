#!/usr/bin/env python3
"""One-time local prep for the ASCII portrait source photo.

Removes the background with rembg, then boosts local contrast on the
subject with CLAHE so faces stay legible instead of turning into a dark
blob when quantized to ASCII.

Usage:
    python scripts/prep_photo.py <input-photo> <output.png>
"""
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

# ============================= CONFIG ======================================
CLAHE_CLIP_LIMIT = 3.0   # higher = stronger local contrast (2.0 - 5.0 sane)
CLAHE_GRID = 8           # tile grid size for CLAHE
OUTPUT_SIZE = 900        # longest edge of the prepped output, px
ALPHA_THRESHOLD = 40     # alpha below this is treated as background
# ===========================================================================


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: prep_photo.py <input-photo> <output.png>")
    src_path, out_path = sys.argv[1], sys.argv[2]

    print(f"[prep] loading {src_path}")
    img = Image.open(src_path).convert("RGBA")

    print("[prep] removing background (rembg, first run downloads the model)...")
    img = remove(img)

    rgba = np.array(img)
    alpha = rgba[:, :, 3]

    # CLAHE on the L channel of the subject only.
    print(f"[prep] applying CLAHE (clipLimit={CLAHE_CLIP_LIMIT})")
    lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=(CLAHE_GRID, CLAHE_GRID)
    )
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    rgba = np.dstack([rgb, alpha])

    # Crop to the subject's bounding box (with a small margin).
    ys, xs = np.where(alpha > ALPHA_THRESHOLD)
    if len(xs) == 0:
        sys.exit("[prep] rembg removed everything -- check the input photo")
    pad = max(rgba.shape[0], rgba.shape[1]) // 50
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, rgba.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, rgba.shape[1])
    rgba = rgba[y0:y1, x0:x1]

    out = Image.fromarray(rgba, "RGBA")
    out.thumbnail((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
    out.save(out_path)
    print(f"[prep] wrote {out_path} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
