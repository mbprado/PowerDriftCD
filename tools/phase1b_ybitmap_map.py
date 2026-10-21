#!/usr/bin/env python3
"""Map private MAME Y-sprite bitmap pixels through the captured affine block."""

import argparse
import hashlib
import struct
from pathlib import Path

from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import png_rows, read_capture


def signed32(high, low):
    value = (high << 16) | low
    return value - 0x100000000 if value & 0x80000000 else value


def affine(directory):
    words = struct.unpack(">16H", read_capture(directory, "pre", 966))
    return tuple(signed32(words[i], words[i + 1]) for i in range(0, 12, 2))


def map_pixel(params, x, y):
    currx, curry, dyy, dxx, dxy, dyx = params
    sx = ((currx + dxx * (x + 27) + dxy * y) >> 14) & 0x1ff
    sy = ((curry + dyx * (x + 27) + dyy * y) >> 14) & 0x1ff
    return sx, sy


def source_words(directory, frame):
    path = directory / f"ybitmap-{frame:04d}.raw"
    data = path.read_bytes()
    if len(data) != 512 * 512 * 2:
        raise ValueError(f"Expected 512x512x16-bit bitmap: {path}")
    return struct.unpack("<262144H", data), hashlib.sha256(data).hexdigest()


def first_opaque_run(words, params, y):
    for x in range(16, 128):
        coords = [map_pixel(params, xx, y) for xx in range(x, x + 4)]
        if all(words[sy * 512 + sx] != 0xffff for sx, sy in coords):
            return x, coords[0]
    return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("left_both", type=Path)
    parser.add_argument("--case", action="append", default=[], metavar="NAME=DIR",
                        help="Additional private replay directory")
    args = parser.parse_args()
    center_words, _ = source_words(args.center, 966)
    cases = [(name, getattr(args, name)) for name in
             ("center", "left", "right", "left_both")]
    for item in args.case:
        name, separator, path = item.partition("=")
        if not separator or not name or not path:
            parser.error("--case requires NAME=DIR")
        cases.append((name, Path(path)))
    print("condition,screen_y,visible_boundary_x,first_source_opaque_screen_x,"
          "source_x,source_y,source_words_changed_from_center,source_sha256")
    for name, directory in cases:
        words, sha = source_words(directory, 966)
        params = affine(directory)
        changed = sum(a != b for a, b in zip(center_words, words))
        screen = png_rows(directory / "swap-screen-0967.png")
        for y in (162, 165, 168):
            try:
                visible_x = boundary(screen[y], y)[0]
            except ValueError:
                visible_x = None
            source_x, coords = first_opaque_run(words, params, y)
            sx, sy = coords if coords else (None, None)
            print(f"{name},{y},{visible_x},{source_x},{sx},{sy},"
                  f"{changed},{sha}")


if __name__ == "__main__":
    main()
