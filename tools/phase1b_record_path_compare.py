#!/usr/bin/env python3
"""Compare private sprite-record intervention captures without exporting assets."""

import argparse
import hashlib
import sys
from pathlib import Path

from phase1b_swap_compare import changed_pixels, png_rows


def descriptor_x(directory):
    data = (directory / "source-0966-ysprites.bin").read_bytes()
    assert len(data) == 65536
    return int.from_bytes(data[0xE632:0xE634], "big") & 0xFFF


def bitmap(directory):
    data = (directory / "ybitmap-0966.raw").read_bytes()
    assert len(data) == 512 * 512 * 2
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compare(label, baseline, override, direct):
    source = bitmap(override)
    direct_source = bitmap(direct)
    assert source == direct_source, f"{label}: bitmap differs from direct descriptor restore"
    print(f"{label}: descriptor X baseline={descriptor_x(baseline):03X} "
          f"override={descriptor_x(override):03X}")
    print(f"{label}: override bitmap SHA-256={digest(source)}; "
          "equals direct descriptor restore")
    changed = []
    for frame in range(960, 971):
        original = png_rows(baseline / f"swap-screen-{frame:04d}.png")
        altered = png_rows(override / f"swap-screen-{frame:04d}.png")
        delta = changed_pixels(original, altered)
        if delta:
            changed.append((frame, delta))
        if frame == 967:
            direct_pixels = png_rows(direct / "swap-screen-0967.png")
            assert changed_pixels(altered, direct_pixels) == 0, (
                f"{label}: screen differs from direct descriptor restore")
    print(f"{label}: changed screen pixels by callback={changed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    root = args.private_root
    for side in ("left", "right"):
        compare(side, root / f"phase1b-ybitmap-{side}",
                root / f"phase1b-record-override-{side}",
                root / f"phase1b-ybitmap-{side}-e630-10")
    baseline = root / "phase1b-ybitmap-left"
    sham = root / "phase1b-record-override-sham-left"
    assert descriptor_x(baseline) == descriptor_x(sham)
    assert bitmap(baseline) == bitmap(sham)
    assert all(changed_pixels(
        png_rows(baseline / f"swap-screen-{frame:04d}.png"),
        png_rows(sham / f"swap-screen-{frame:04d}.png")) == 0
        for frame in range(960, 971))
    print("left sham: descriptor, bitmap, and callbacks 960–970 unchanged")
    repeat = root / "phase1b-record-override-left-repeat"
    assert all((root / "phase1b-record-override-left" / name).read_bytes()
               == (repeat / name).read_bytes()
               for name in ("source-0966-ysprites.bin", "ybitmap-0966.raw",
                            "swap-screen-0967.png"))
    print("left repeat: descriptor, bitmap, and callback-967 PNG byte-identical")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
