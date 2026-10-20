#!/usr/bin/env python3
"""Check private MAME road-image correspondences against captured affine parameters."""

import argparse
import struct
from pathlib import Path

from phase1b_swap_compare import png_rows, read_capture


FRAMES = (963, 965, 967, 969)
X_RANGE = range(320)
Y_RANGE = range(80, 170)
SCALE = 1 << 14


def parameters(directory, frame):
    return struct.unpack(">6i", read_capture(directory, "pre", frame - 1)[:24])


def alignment(center_dir, steered_dir, frame):
    center_params = parameters(center_dir, frame)
    steered_params = parameters(steered_dir, frame)
    cx, cy, cyy, cxx, cxy, cyx = center_params
    sx, sy, syy, sxx, sxy, syx = steered_params
    if (cyy, cxx, cxy, cyx) != (SCALE, SCALE, 0, 0):
        raise ValueError(f"centered transform is not identity at {frame}")
    if cx % SCALE or cy % SCALE:
        raise ValueError(f"centered origin is not pixel-aligned at {frame}")

    centered = png_rows(center_dir / f"swap-screen-{frame:04d}.png")
    steered = png_rows(steered_dir / f"swap-screen-{frame:04d}.png")
    exact = {"identity": 0, "predicted": 0, "reversed": 0}
    difference = {name: 0 for name in exact}
    compared = 0
    for y in Y_RANGE:
        for x in X_RANGE:
            # rotate_draw() samples source coordinates with an arithmetic >> 14.
            dx_fixed = sx - cx + (sxx - SCALE) * (x + 27) + sxy * y
            dy_fixed = sy - cy + syx * (x + 27) + (syy - SCALE) * y
            positions = {
                "identity": (x, y),
                "predicted": (x + dx_fixed // SCALE, y + dy_fixed // SCALE),
                "reversed": (x + (-dx_fixed) // SCALE, y + (-dy_fixed) // SCALE),
            }
            if any(not (0 <= px < 320 and 0 <= py < 224)
                   for px, py in positions.values()):
                continue
            target = steered[y][3 * x:3 * x + 3]
            compared += 1
            for name, (px, py) in positions.items():
                source = centered[py][3 * px:3 * px + 3]
                exact[name] += target == source
                difference[name] += sum(abs(a - b) for a, b in zip(target, source))
    return compared, exact, difference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print("frame,condition,pixels,identity_exact_pct,predicted_exact_pct,"
          "reversed_exact_pct,identity_rgb_mae,predicted_rgb_mae,reversed_rgb_mae")
    for frame in FRAMES:
        for condition in ("left", "right"):
            count, exact, difference = alignment(
                args.center, getattr(args, condition), frame)
            order = ("identity", "predicted", "reversed")
            fractions = [f"{100 * exact[name] / count:.2f}" for name in order]
            errors = [f"{difference[name] / (3 * count):.2f}" for name in order]
            print(",".join((str(frame), condition, str(count), *fractions, *errors)))


if __name__ == "__main__":
    main()
