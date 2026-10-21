#!/usr/bin/env python3
"""Verify a private five-epoch arcade geometry/list/descriptor/visibility trace."""

import argparse
import csv
import struct
import sys
from pathlib import Path

from phase1b_list_sequence import TRACE
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import source_words


SIDES = ("center", "left", "right")
PROJECTION_FRAMES = (960, 964, 968, 972, 976)
HIDDEN = ((962, 0xE600), (966, 0xE630), (970, 0xE660),
          (974, 0xE660), (978, 0xE640))


def debug_events(path):
    frame = None
    events = []
    for line in path.read_text().splitlines():
        if line.startswith("SEQUENCE_FRAME,"):
            frame = int(line.split(",", 1)[1])
        match = TRACE.fullmatch(line)
        if match:
            assert frame is not None
            events.append((frame, tuple(int(field, 16)
                                        for field in match.groups())))
    return events


def image_difference(first, second):
    a = png_rows(first)
    b = png_rows(second)
    return [(x, y) for y in range(224) for x in range(320)
            if a[y][3*x:3*x+3] != b[y][3*x:3*x+3]]


def bounds(points):
    return (min(x for x, _ in points), max(x for x, _ in points),
            min(y for _, y in points), max(y for _, y in points))


def main(root):
    matches = 0
    for side in SIDES:
        directory = root / f"phase1b-depth-sequence-{side}"
        rows = list(csv.DictReader((directory / "geometry-samples.csv").open()))
        indexed = {(int(row["frame"]), int(row["index"])): row
                   for row in rows}
        assert len(rows) == len(indexed) == 41 * 12
        previous = root / f"phase1b-geometry-sequence-{side}"
        old_rows = list(csv.DictReader((root /
                       f"phase1b-geometry-coeff-{side}" /
                       "geometry-samples.csv").open()))
        assert rows[:len(old_rows)] == old_rows
        for prior_frame in range(960, 971):
            for name in (f"source-{prior_frame:04d}-ysprites.bin",
                         f"swap-screen-{prior_frame:04d}.png"):
                assert (directory / name).read_bytes() == (
                    previous / name).read_bytes()
        samples = [indexed[frame, 0] for frame in range(960, 1001)]
        assert len({tuple(row[key] for key in
                          ("depth", "table", "sample0", "sample1", "sample2"))
                    for row in samples}) == 1
        assert all(row["depth"] == "3200" for row in samples)
        events = debug_events(root / f"phase1b-depth-subx-{side}" / "debug.log")
        for frame in PROJECTION_FRAMES:
            row = indexed[frame, 0]
            position = (int(row["projected4"], 16) << 16 |
                        int(row["projected6"], 16))
            raw = (directory / f"shared-list-{frame+2:04d}.bin").read_bytes()
            assert len(raw) == 0x2000
            candidates = [(slot, struct.unpack_from(">4I", raw, 16 * slot))
                          for slot in range(0x2000 // 16)
                          if struct.unpack_from(">I", raw, 16 * slot + 4)[0]
                          == position and
                          struct.unpack_from(">I", raw, 16 * slot)[0]
                          & 0xFFFF == 0x20]
            assert len(candidates) == 1, (side, frame, candidates)
            slot, fields = candidates[0]
            loads = [entry for event_frame, entry in events
                     if event_frame == frame + 1 and
                     entry[:4] == fields and entry[4] == 0x0C9800]
            assert len(loads) == 1, (side, frame, loads)
            descriptor_offset = loads[0][5] - 0x180000 + 0x2000
            sprite_ram = (directory /
                          f"source-{frame+2:04d}-ysprites.bin").read_bytes()
            assert len(sprite_ram) == 0x10000
            descriptor = struct.unpack_from(">8H", sprite_ram,
                                            descriptor_offset)
            assert not (descriptor[0] & 0xD000), (side, frame, descriptor)
            matches += 1
            print(f"{side} {frame}→{frame+2}: list +{slot*16:04X}, "
                  f"descriptor +{descriptor_offset:04X}, "
                  f"X={descriptor[1]&0xFFF:03X}, "
                  f"graphic={descriptor[3]:04X}")
        print(f"{side}: same ROM depth/table/sample over 41 callbacks")
    print(f"geometry → list → sub-CPU X → descriptor: {matches}/{matches} "
          "selected epochs")
    print("overlap with prior 960–970 captures: 396/396 geometry rows and "
          "66/66 source-RAM/screen files byte-identical")

    baseline = root / "phase1b-depth-sequence-center"
    visibility = []
    for frame, slot in HIDDEN:
        altered = root / (f"phase1b-list-hidden-{frame}" if frame < 970
                          else f"phase1b-depth-hidden-{frame}")
        original = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
        after = (altered / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
        assert len(original) == len(after) == 0x10000
        assert [i for i, (a, b) in enumerate(zip(original, after))
                if a != b] == [slot]
        assert after[slot] == original[slot] | 0x10
        for earlier in range(960, frame + 1):
            assert (baseline / f"swap-screen-{earlier:04d}.png").read_bytes() == (
                altered / f"swap-screen-{earlier:04d}.png").read_bytes()
        changed = image_difference(
            baseline / f"swap-screen-{frame+1:04d}.png",
            altered / f"swap-screen-{frame+1:04d}.png")
        assert changed
        row150 = [x for x, y in changed if y == 150]
        box = bounds(changed)
        if frame in (962, 966):
            assert row150 == list(range(min(row150), max(row150) + 1))
        else:
            assert not row150
        visibility.append((frame, len(changed), box))
        print(f"hide +{slot:04X} at {frame}: {len(changed)} screen pixels "
              f"at {frame+1}, bbox={box}, row150={len(row150)}")
    assert [item[2][2] for item in visibility] == [143, 147, 154, 168, 220]
    for frame in (962, 966, 970):
        original = root / ("phase1b-list-baseline-970" if frame == 970
                           else "phase1b-geometry-sequence-center")
        altered = root / (f"phase1b-list-hidden-{frame}" if frame < 970
                          else "phase1b-depth-hidden-970")
        native_a, _ = source_words(original, frame)
        native_b, _ = source_words(altered, frame)
        print(f"native bitmap {frame}: "
              f"{sum(a != b for a, b in zip(native_a, native_b))} "
              "changed pixels")
    sham = root / "phase1b-depth-hidden-974-sham"
    repeat = root / "phase1b-depth-hidden-974-repeat"
    changed = root / "phase1b-depth-hidden-974"
    assert (baseline / "source-0974-ysprites.bin").read_bytes() == (
        sham / "source-0974-ysprites-after.bin").read_bytes()
    assert image_difference(baseline / "swap-screen-0975.png",
                            sham / "swap-screen-0975.png") == []
    for name in ("source-0974-ysprites-after.bin", "swap-screen-0975.png"):
        assert (changed / name).read_bytes() == (repeat / name).read_bytes()
    print("callback 974 same-value sham unchanged; hidden repeat "
          "source RAM and next screen byte-identical")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    try:
        main(args.private_root)
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
