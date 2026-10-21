#!/usr/bin/env python3
"""Summarize private arcade geometry traces and one controlled projection change."""

import argparse
import re
import sys
from pathlib import Path

from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import changed_pixels, png_rows
from phase1b_ybitmap_map import source_words


FIELDS = ("a5", "p16", "p18", "p1a", "depth")
FIELD_PATTERN = re.compile(r"(a5|p16|p18|p1a|depth)=([0-9A-F]+)")


def entries(directory):
    lines = (directory / "debug.log").read_text().splitlines()
    return [dict(FIELD_PATTERN.findall(line)) for line in lines
            if line.startswith("OBJECT_ENTRY")]


def bbox(coords):
    return (min(x for x, _ in coords), max(x for x, _ in coords),
            min(y for _, y in coords), max(y for _, y in coords))


def descriptor_x(directory):
    raw = (directory / "source-0966-ysprites.bin").read_bytes()
    assert len(raw) == 65536
    return int.from_bytes(raw[0xE632:0xE634], "big") & 0xFFF


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    root = args.private_root
    conditions = {name: entries(root / f"phase1b-object-list-{name}")
                  for name in ("center", "left", "right")}
    center = conditions["center"]
    assert len(center) == 116
    assert all(len(value) == len(center) and
               all(tuple(a[key] for key in FIELDS) ==
                   tuple(b[key] for key in FIELDS)
                   for a, b in zip(center, value))
               for value in conditions.values())
    assert center[0]["a5"] == "0C1C80"
    print(f"object list: {len(center)} entries; selected address "
          f"{center[0]['a5']}; geometry fields identical in all 3 replays")
    print(f"selected fields: p16={center[0]['p16']} "
          f"p18={center[0]['p18']} depth={center[0]['depth']}")

    baseline = root / "phase1b-ybitmap-center"
    changed = root / "phase1b-geometry-small-center"
    sham = root / "phase1b-geometry-sham-center"
    repeat = root / "phase1b-geometry-small-center-repeat"
    for name in ("source-0966-ysprites.bin", "ybitmap-0966.raw"):
        assert (baseline / name).read_bytes() == (sham / name).read_bytes()
        assert (changed / name).read_bytes() == (repeat / name).read_bytes()
    print(f"descriptor X: baseline={descriptor_x(baseline):03X} "
          f"sham={descriptor_x(sham):03X} "
          f"changed={descriptor_x(changed):03X}")
    normal_ram = (baseline / "source-0966-ysprites.bin").read_bytes()
    changed_ram = (changed / "source-0966-ysprites.bin").read_bytes()
    assert sum(a != b for a, b in zip(normal_ram, changed_ram)) == 6
    assert normal_ram[0xE636:0xE638] == changed_ram[0xE636:0xE638]
    print("same E630 sprite ROM offset; six changed descriptor-RAM bytes")
    first, _ = source_words(baseline, 966)
    second, digest = source_words(changed, 966)
    coords = [(index % 512, index // 512)
              for index, (a, b) in enumerate(zip(first, second)) if a != b]
    print(f"bitmap frame 966: {len(coords)} changed pixels, "
          f"bbox={bbox(coords)}, SHA-256={digest}")
    for frame in range(960, 971):
        base_rows = png_rows(baseline / f"swap-screen-{frame:04d}.png")
        changed_rows = png_rows(changed / f"swap-screen-{frame:04d}.png")
        sham_rows = png_rows(sham / f"swap-screen-{frame:04d}.png")
        assert changed_pixels(base_rows, sham_rows) == 0
        count = changed_pixels(base_rows, changed_rows)
        if count:
            coords = [(x, y) for y in range(224) for x in range(320)
                      if base_rows[y][x * 3:x * 3 + 3] !=
                      changed_rows[y][x * 3:x * 3 + 3]]
            print(f"screen callback {frame}: {count} changed pixels, "
                  f"bbox={bbox(coords)}")
        if frame == 967:
            assert (changed / "swap-screen-0967.png").read_bytes() == (
                repeat / "swap-screen-0967.png").read_bytes()
            print("callback 967 boundaries: " + ", ".join(
                f"y={y} {boundary(base_rows[y], y)[0]}→"
                f"{boundary(changed_rows[y], y)[0]}"
                for y in (162, 165, 168)))
    print("sham: callbacks 960–970 unchanged; repeat: frame-966 RAM/bitmap "
          "and callback-967 PNG byte-identical")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
