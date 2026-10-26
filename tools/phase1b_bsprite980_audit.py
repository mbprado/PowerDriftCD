#!/usr/bin/env python3
"""Audit the private single-record 16B sprite hide at screen 980."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct

from phase1b_swap_compare import png_rows


SLOT = 0x40
TARGETS = ((290, 157), (291, 158))
CONTROLS = ((297, 159), (90, 157), (84, 158), (82, 159))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path):
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    return {(int(row["x"]), int(row["y"])): {
        key: int(value) for key, value in row.items() if key not in ("x", "y")
    } for row in rows}


def rgb(rows, point):
    x, y = point
    return bytes(rows[y][3 * x:3 * x + 3]).hex()


def audit(baseline, trials):
    before = (baseline / "source-0979-bsprites.bin").read_bytes()
    assert len(before) == 0x1000
    words = struct.unpack_from(">8H", before, SLOT)
    assert words[0] & 0xff <= 157 < words[0] >> 8
    assert words[2] & 0xc000 == 0
    assert ((words[4] & 0xff) << 4) | (((words[1] >> 9) & 0xf) << 12) == 0x2e0
    baseline_probe = probe(baseline / "layer-0979.csv")
    baseline_screen = png_rows(baseline / "swap-screen-0980.png")
    for point in TARGETS:
        assert baseline_probe[point]["sprite"] == 0x2e2
        assert baseline_probe[point]["final"] == 0xae2

    results = []
    for trial in trials:
        captured = (trial / "source-0979-bsprites.bin").read_bytes()
        after = (trial / "source-0979-bsprites-after.bin").read_bytes()
        assert captured == before and len(after) == len(before)
        changed_bytes = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        assert changed_bytes == [SLOT + 4]
        assert after[SLOT + 4] == before[SLOT + 4] | 0x40
        for frame in range(960, 980):
            name = f"swap-screen-{frame:04d}.png"
            assert png_rows(trial / name) == png_rows(baseline / name), name
        trial_probe = probe(trial / "layer-0979.csv")
        screen = png_rows(trial / "swap-screen-0980.png")
        for point in TARGETS:
            assert trial_probe[point]["sprite"] == 0xffff
            assert trial_probe[point]["final"] == trial_probe[point]["rotated"]
            assert rgb(screen, point) != rgb(baseline_screen, point)
        for point in CONTROLS:
            assert trial_probe[point] == baseline_probe[point]
            assert rgb(screen, point) == rgb(baseline_screen, point)
        changed_pixels = sum(
            baseline_screen[y][3 * x:3 * x + 3] != screen[y][3 * x:3 * x + 3]
            for y in range(224) for x in range(320))
        results.append({
            "trial": str(trial), "changed_ram_offsets": [f"{i:04X}" for i in changed_bytes],
            "prior_screens_equal": True, "changed_screen980_pixels": changed_pixels,
            "targets": [{"xy": list(point), "baseline_rgb": rgb(baseline_screen, point),
                         "hidden_rgb": rgb(screen, point),
                         "baseline_sprite": baseline_probe[point]["sprite"],
                         "hidden_sprite": trial_probe[point]["sprite"]}
                        for point in TARGETS],
            "layer_sha256": sha(trial / "layer-0979.csv"),
            "screen980_sha256": sha(trial / "swap-screen-0980.png"),
            "after_ram_sha256": sha(trial / "source-0979-bsprites-after.bin"),
            "log_sha256": sha(trial / "phase1b-input.log"),
        })
    assert len({(r["changed_screen980_pixels"], r["layer_sha256"],
                 r["screen980_sha256"], r["after_ram_sha256"]) for r in results}) == 1
    return {"slot": "0040", "record_words": [f"{word:04X}" for word in words],
            "baseline_ram_sha256": sha(baseline / "source-0979-bsprites.bin"),
            "baseline_layer_sha256": sha(baseline / "layer-0979.csv"),
            "baseline_screen980_sha256": sha(baseline / "swap-screen-0980.png"),
            "replays": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("trials", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(audit(args.baseline, args.trials), indent=2))


if __name__ == "__main__":
    main()
