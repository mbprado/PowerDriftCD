#!/usr/bin/env python3
"""Verify private projected-record timing and one visible arcade strip span."""

import argparse
import csv
import struct
import sys
from pathlib import Path

from phase1b_swap_compare import changed_pixels, png_rows
from phase1b_ybitmap_map import source_words


CASES = ((960, 962, 0, 0x8B310020, 0xB2420032, 0xE600),
         (964, 966, 0, 0x8B3D0020, 0xB242003E, 0xE630),
         (968, 970, 1, 0x8B2F0020, 0xB2420030, 0xE5D0))


def rows(path):
    return {(int(row["frame"]), int(row["index"])): row
            for row in csv.DictReader(path.open())}


def list_record(raw, identity, source):
    matches = [(index, struct.unpack_from(">4I", raw, 16 * index))
               for index in range(len(raw) // 16)
               if struct.unpack_from(">I", raw, 16 * index)[0] == identity
               and struct.unpack_from(">I", raw, 16 * index + 12)[0] == source]
    assert len(matches) == 1, matches
    return matches[0]


def bbox(coords):
    return (min(x for x, _ in coords), max(x for x, _ in coords),
            min(y for _, y in coords), max(y for _, y in coords))


def main(root):
    aligned = 0
    for side in ("center", "left", "right"):
        geometry = rows(root / f"phase1b-geometry-coeff-{side}" /
                        "geometry-samples.csv")
        captures = root / f"phase1b-list-sequence-{side}"
        for projected_frame, list_frame, index, identity, source, _ in CASES:
            raw = (captures / f"shared-list-{list_frame:04d}.bin").read_bytes()
            assert len(raw) == 0x2000
            slot, fields = list_record(raw, identity, source)
            row = geometry[projected_frame, index]
            projected = (int(row["projected4"], 16) << 16) | int(
                row["projected6"], 16)
            assert fields[1] == projected, (side, projected_frame, slot,
                                            fields[1], projected)
            aligned += 1
        print(f"{side}: 3/3 projected position → selected list position "
              "after two callbacks")
    print(f"projection/list position alignment: {aligned}/{aligned}")

    for _, frame, _, _, _, slot in CASES:
        baseline = root / ("phase1b-list-baseline-970" if frame == 970
                           else "phase1b-geometry-sequence-center")
        hidden = root / f"phase1b-list-hidden-{frame}"
        before = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
        after = (hidden / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
        assert len(before) == len(after) == 0x10000
        assert [i for i, (a, b) in enumerate(zip(before, after)) if a != b] == [
            slot]
        assert after[slot] == before[slot] | 0x10
        native_a, _ = source_words(baseline, frame)
        native_b, _ = source_words(hidden, frame)
        native_diff = [(i % 512, i // 512) for i, (a, b) in
                       enumerate(zip(native_a, native_b)) if a != b]
        visible_frame = frame + 1
        screen_a = png_rows(baseline / f"swap-screen-{visible_frame:04d}.png")
        screen_b = png_rows(hidden / f"swap-screen-{visible_frame:04d}.png")
        screen_diff = [(x, y) for y in range(224) for x in range(320)
                       if screen_a[y][3*x:3*x+3] != screen_b[y][3*x:3*x+3]]
        assert native_diff and screen_diff
        for prior in range(960, frame + 1):
            a = png_rows(baseline / f"swap-screen-{prior:04d}.png")
            b = png_rows(hidden / f"swap-screen-{prior:04d}.png")
            assert changed_pixels(a, b) == 0, (frame, prior)
        row150 = sorted(x for x, y in screen_diff if y == 150)
        contiguous = row150 == list(range(row150[0], row150[-1] + 1))
        assert contiguous if frame in (962, 966) else not contiguous
        print(f"hide descriptor +{slot:04X} at {frame}: "
              f"native={len(native_diff)}, screen={len(screen_diff)} "
              f"at {visible_frame}, screen bbox={bbox(screen_diff)}, "
              f"row150={row150[0]}..{row150[-1]} "
              f"({len(row150)} changed, contiguous={contiguous})")

    baseline = root / "phase1b-geometry-sequence-center"
    hidden = root / "phase1b-list-hidden-962"
    repeat = root / "phase1b-list-hidden-962-repeat"
    sham = root / "phase1b-list-hidden-962-sham"
    for filename in ("source-0962-ysprites-after.bin", "ybitmap-0962.raw",
                     "swap-screen-0963.png"):
        assert (hidden / filename).read_bytes() == (repeat / filename).read_bytes()
    assert (baseline / "source-0962-ysprites.bin").read_bytes() == (
        sham / "source-0962-ysprites-after.bin").read_bytes()
    for filename in ("ybitmap-0962.raw", "swap-screen-0963.png"):
        assert (baseline / filename).read_bytes() == (sham / filename).read_bytes()
    print("callback 962 same-value sham matches baseline; hidden repeat "
          "matches source RAM, bitmap and next screen byte-for-byte")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    try:
        main(args.private_root)
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
