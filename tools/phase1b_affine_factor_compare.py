#!/usr/bin/env python3
"""Compare private, same-state Y-sprite/affine interventions at callback 967."""

import argparse
import hashlib
from pathlib import Path

from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import changed_pixels, png_rows, read_capture


def capture(directory, frame, name):
    return (directory / f"source-{frame:04d}-{name}.bin").read_bytes()


def compare(center, baseline, directory, side, factor):
    center_screen = png_rows(center / "swap-screen-0967.png")
    screen_path = directory / "swap-screen-0967.png"
    screen = png_rows(screen_path)
    before_equal = ((directory / "swap-screen-0966.png").read_bytes()
                    == (baseline / "swap-screen-0966.png").read_bytes())
    restored_equal = ((directory / "swap-screen-0969.png").read_bytes()
                      == (baseline / "swap-screen-0969.png").read_bytes())
    source_before_equal = (capture(directory, 966, "ysprites")
                           == capture(baseline, 966, "ysprites"))
    source_after = directory / "source-0966-ysprites-after.bin"
    source_center_equal = (source_after.read_bytes()
                           == capture(center, 966, "ysprites")
                           if source_after.exists() else False)
    affine_center_equal = (read_capture(directory, "pre", 966)
                           == read_capture(center, "pre", 966))
    other_ram_equal = all(
        capture(directory, frame, name) == capture(baseline, frame, name)
        for frame in (966, 967) for name in ("bsprites", "palette"))
    image = screen_path.read_bytes()
    return (side, factor, before_equal, restored_equal, source_before_equal,
            source_center_equal, affine_center_equal, other_ram_equal,
            changed_pixels(center_screen, screen),
            changed_pixels(center_screen, screen, 0, 320, 80, 170),
            boundary(screen[165], 165)[0], hashlib.sha256(image).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    for side in ("left", "right"):
        for factor in ("normal", "source", "affine", "both"):
            parser.add_argument(f"{side}_{factor}", type=Path)
    args = parser.parse_args()
    print("side,factor,pre_screen_equal,screen969_restored,source_before_equal,"
          "source_after_center_equal,affine_center_equal,other_ram_equal,"
          "changed_pixels_full,changed_pixels_road_rect,left_boundary_y165,"
          "screen967_sha256")
    for side in ("left", "right"):
        baseline = getattr(args, f"{side}_normal")
        for factor in ("normal", "source", "affine", "both"):
            row = compare(args.center, baseline,
                          getattr(args, f"{side}_{factor}"), side, factor)
            print(",".join(map(str, row)))


if __name__ == "__main__":
    main()
