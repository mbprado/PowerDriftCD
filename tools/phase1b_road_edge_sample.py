#!/usr/bin/env python3
"""Sample the left sand-to-roadside boundary in private MAME screenshots."""

import argparse
import hashlib
from pathlib import Path

from phase1b_swap_compare import png_rows


SAND_RGB = (214, 214, 132)
FRAMES = range(960, 971)
SCANLINES = (162, 165, 168)


def boundary(row, scanline):
    pixels = [tuple(row[i:i + 3]) for i in range(0, len(row), 3)]
    if any(pixel != SAND_RGB for pixel in pixels[:16]):
        raise ValueError(f"scanline {scanline}: left border is not reference sand")
    for x in range(16, min(128, len(pixels) - 3)):
        if all(pixel != SAND_RGB for pixel in pixels[x:x + 4]):
            return x, pixels[x]
    raise ValueError(f"scanline {scanline}: no sustained boundary in first 128 pixels")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path,
                        help="directories containing swap-screen-NNNN.png")
    args = parser.parse_args()
    print("condition,callback,scanline,boundary_x,boundary_rgb,screenshot_sha256")
    for directory in args.captures:
        for frame in FRAMES:
            path = directory / f"swap-screen-{frame:04d}.png"
            image = path.read_bytes()
            rows = png_rows(path)
            for y in SCANLINES:
                x, rgb = boundary(rows[y], y)
                print(f"{directory.name},{frame},{y},{x},"
                      f"{'-'.join(map(str, rgb))},{hashlib.sha256(image).hexdigest()}")


if __name__ == "__main__":
    main()
