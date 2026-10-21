#!/usr/bin/env python3
"""Trace a private Y-Board bitmap edge through a deterministic MAME replay."""

import argparse
import struct
from pathlib import Path

from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import png_rows, read_capture
from phase1b_ybitmap_map import first_opaque_run, signed32, source_words


def active_affine(directory, source_frame):
    swap_frame = source_frame - source_frame % 2
    words = read_capture(directory, "pre", swap_frame)
    words = struct.unpack(">16H", words)
    return swap_frame, tuple(signed32(words[i], words[i + 1])
                             for i in range(0, 12, 2))


def fixed_source_edge(words, y):
    for x in range(120, 220):
        if all(words[y * 512 + xx] != 0xffff for xx in range(x, x + 4)):
            return x
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print("condition,source_frame,screen_callback,swap_frame,screen_y,"
          "visible_boundary_x,predicted_opaque_x,source_x,source_y,"
          "fixed_row213_edge_x,source_sha256")
    for name in ("center", "left", "right"):
        directory = getattr(args, name)
        for source_frame in range(960, 969):
            words, source_sha = source_words(directory, source_frame)
            swap_frame, params = active_affine(directory, source_frame)
            screen = png_rows(directory / f"swap-screen-{source_frame + 1:04d}.png")
            source_edge = fixed_source_edge(words, 213)
            for y in (162, 165, 168):
                try:
                    visible_x = boundary(screen[y], y)[0]
                except ValueError:
                    visible_x = None
                predicted_x, coords = first_opaque_run(words, params, y)
                sx, sy = coords if coords else (None, None)
                print(f"{name},{source_frame},{source_frame + 1},"
                      f"{swap_frame},{y},{visible_x},{predicted_x},"
                      f"{sx},{sy},{source_edge},{source_sha}")


if __name__ == "__main__":
    main()
