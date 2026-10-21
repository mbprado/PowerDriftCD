#!/usr/bin/env python3
"""Verify a farther private arcade geometry sample and visibility replays."""

import argparse
import csv
import struct
import sys
from pathlib import Path

from phase1b_depth_sequence import bounds, debug_events, image_difference
from phase1b_ybitmap_map import source_words


SIDES = ("center", "left", "right")
EPOCHS = range(960, 997, 4)
CENTER_HIDES = ((962, 0xE4B0, 0), (970, 0xE4B0, 70),
                (978, 0xE500, 44), (986, 0xE530, 330),
                (994, 0xE550, 1589), (998, 0xE570, 4248))


def selected_record(raw, position):
    matches = [(index, struct.unpack_from(">4I", raw, index * 16))
               for index in range(0x2000 // 16)
               if struct.unpack_from(">I", raw, index * 16 + 4)[0]
               == position and
               ((struct.unpack_from(">I", raw, index * 16)[0] >> 16)
                & 0xFF00) == 0x8B00]
    assert len(matches) == 1, matches
    return matches[0]


def hidden_test(root, side, frame, slot, expected):
    baseline = root / f"phase1b-depth-sequence-{side}"
    altered = root / (f"phase1b-far-hidden-{frame}" if side == "center"
                      else f"phase1b-far-hidden-{frame}-{side}")
    original = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
    after = (altered / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
    assert len(original) == len(after) == 0x10000
    assert [i for i, (a, b) in enumerate(zip(original, after)) if a != b] == [
        slot]
    assert after[slot] == original[slot] | 0x10
    for prior in range(960, frame + 1):
        assert (baseline / f"swap-screen-{prior:04d}.png").read_bytes() == (
            altered / f"swap-screen-{prior:04d}.png").read_bytes()
    points = image_difference(baseline / f"swap-screen-{frame+1:04d}.png",
                              altered / f"swap-screen-{frame+1:04d}.png")
    assert len(points) == expected, (side, frame, len(points), expected)
    if points:
        row150 = [x for x, y in points if y == 150]
        print(f"{side} hide at {frame}: {len(points)} screen pixels, "
              f"bbox={bounds(points)}, row150={len(row150)}")
    else:
        print(f"{side} hide at {frame}: no screen difference")
    return points


def main(root):
    matches = 0
    for side in SIDES:
        directory = root / f"phase1b-depth-sequence-{side}"
        rows = {(int(row["frame"]), int(row["index"])): row
                for row in csv.DictReader((directory /
                                           "geometry-samples.csv").open())}
        assert len(rows) == 41 * 12
        geometry = [rows[frame, 4] for frame in range(960, 1001)]
        assert len({tuple(row[key] for key in
                          ("depth", "table", "sample0", "sample1", "sample2"))
                    for row in geometry}) == 1
        assert all(row["depth"] == "3A00" for row in geometry)
        events = debug_events(root / f"phase1b-far-subx-{side}" / "debug.log")
        for frame in EPOCHS:
            row = rows[frame, 4]
            position = (int(row["projected4"], 16) << 16 |
                        int(row["projected6"], 16))
            raw = (directory / f"shared-list-{frame+2:04d}.bin").read_bytes()
            assert len(raw) == 0x2000
            index, fields = selected_record(raw, position)
            loads = [event for event_frame, event in events
                     if event_frame == frame + 1 and
                     event[:4] == fields and event[4] == 0x0C9800]
            assert len(loads) == 1, (side, frame, loads)
            slot = loads[0][5] - 0x180000 + 0x2000
            sprite = (directory / f"source-{frame+2:04d}-ysprites.bin").read_bytes()
            assert len(sprite) == 0x10000
            descriptor = struct.unpack_from(">8H", sprite, slot)
            assert descriptor[0] & 0xD000 == 0
            matches += 1
            print(f"{side} {frame}→{frame+2}: list +{index*16:04X}, "
                  f"descriptor +{slot:04X}, graphic={descriptor[3]:04X}")
        print(f"{side}: depth $3A00 ROM tuple unchanged over 41 callbacks")
    assert matches == 30
    print("geometry → list → sub-CPU X → descriptor: 30/30 epochs")

    points = {}
    for frame, slot, expected in CENTER_HIDES:
        points[frame] = hidden_test(root, "center", frame, slot, expected)
    assert not points[962]
    assert not [x for x, y in points[970] if y == 150]
    row150 = sorted(x for x, y in points[994] if y == 150)
    assert row150 == list(range(92, 260))
    for side, slot, expected in (("left", 0xE550, 1715),
                                 ("right", 0xE520, 1668)):
        hidden_test(root, side, 994, slot, expected)

    for frame in (962, 970):
        baseline = root / "phase1b-list-baseline-970"
        hidden = root / f"phase1b-far-hidden-{frame}"
        first, _ = source_words(baseline, frame)
        second, _ = source_words(hidden, frame)
        count = sum(a != b for a, b in zip(first, second))
        assert count == (0 if frame == 962 else 70)
        print(f"native Y bitmap at {frame}: {count} changed pixels")

    center = root / "phase1b-depth-sequence-center"
    sham = root / "phase1b-far-hidden-994-sham"
    changed = root / "phase1b-far-hidden-994"
    repeat = root / "phase1b-far-hidden-994-repeat"
    assert (center / "source-0994-ysprites.bin").read_bytes() == (
        sham / "source-0994-ysprites-after.bin").read_bytes()
    assert (center / "swap-screen-0995.png").read_bytes() == (
        sham / "swap-screen-0995.png").read_bytes()
    for name in ("source-0994-ysprites-after.bin", "swap-screen-0995.png"):
        assert (changed / name).read_bytes() == (repeat / name).read_bytes()
    print("callback 994 same-value sham unchanged; hidden repeat "
          "source RAM and screen byte-identical")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    try:
        main(args.private_root)
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
