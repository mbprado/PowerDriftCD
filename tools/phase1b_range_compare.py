#!/usr/bin/env python3
"""Compare private Y-sprite RAM interventions from one MAME save state."""

import argparse
from pathlib import Path

from phase1b_affine_verify import alignment
from phase1b_swap_compare import png_rows, read_capture


def changed_pixels(reference: Path, candidate: Path, frame: int):
    first = png_rows(reference / f"swap-screen-{frame:04d}.png")
    second = png_rows(candidate / f"swap-screen-{frame:04d}.png")
    if len(first) != len(second) or any(len(a) != len(b) for a, b in zip(first, second)):
        raise ValueError("screenshots have different dimensions")
    positions = [(x, y) for y, (a, b) in enumerate(zip(first, second))
                 for x in range(len(a) // 3)
                 if a[3 * x:3 * x + 3] != b[3 * x:3 * x + 3]]
    if not positions:
        return 0, ""
    return len(positions), ":".join(str(value) for value in (
        min(x for x, _ in positions), min(y for _, y in positions),
        max(x for x, _ in positions), max(y for _, y in positions)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    parser.add_argument("steered", type=Path)
    parser.add_argument("variants", nargs="+", type=Path)
    args = parser.parse_args()
    baseline_ram = (args.steered / "source-0966-ysprites.bin").read_bytes()
    center_ram = (args.center / "source-0966-ysprites.bin").read_bytes()
    baseline_screen = (args.steered / "swap-screen-0966.png").read_bytes()
    baseline_affine = read_capture(args.steered, "pre", 966)
    print("variant,pre_ram_equal,pre_screen_equal,affine_equal,"
          "changed_bytes_after,remaining_center_diff,pixels_changed,bbox,"
          "valid_pixels,predicted_exact_pct,predicted_rgb_mae")
    for variant in args.variants:
        before = (variant / "source-0966-ysprites.bin").read_bytes()
        after_path = variant / "source-0966-ysprites-after.bin"
        after = after_path.read_bytes() if after_path.exists() else before
        if len(before) != 0x10000 or len(after) != 0x10000:
            raise ValueError(f"invalid Y-sprite RAM size: {variant}")
        changed, bbox = changed_pixels(args.steered, variant, 967)
        count, exact, error = alignment(args.center, variant, 967)
        print(",".join(map(str, (
            variant.name,
            before == baseline_ram,
            (variant / "swap-screen-0966.png").read_bytes() == baseline_screen,
            read_capture(variant, "pre", 966) == baseline_affine,
            sum(a != b for a, b in zip(baseline_ram, after)),
            sum(a != b for a, b in zip(center_ram, after)),
            changed, bbox, count,
            f"{100 * exact['predicted'] / count:.2f}",
            f"{error['predicted'] / (3 * count):.2f}",
        ))))


if __name__ == "__main__":
    main()
