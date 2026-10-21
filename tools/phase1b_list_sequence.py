#!/usr/bin/env python3
"""Check private arcade shared-list records against sub-CPU X and Y-sprite RAM."""

import argparse
import re
import struct
import sys
from pathlib import Path

from phase1b_swap_compare import changed_pixels, png_rows
from phase1b_ybitmap_map import source_words


STAGES = ((962, 0x8B310020, 0xB2420032),
          (966, 0x8B3D0020, 0xB242003E),
          (970, 0x8B2F0020, 0xB2420030))
SIDES = ("center", "left", "right")
TRACE = re.compile(
    r"^SUBX_LIST pc=00DD6A first=([0-9A-F]{8}) pos=([0-9A-F]{8}) "
    r"size=([0-9A-F]{8}) source=([0-9A-F]{8}) "
    r"a0=([0-9A-F]{6}) a2=([0-9A-F]{6})$", re.M)


def words(path):
    raw = path.read_bytes()
    assert len(raw) == 0x2000, path
    return raw


def main(root):
    matches = 0
    for side in SIDES:
        directory = root / f"phase1b-list-sequence-{side}"
        trace_path = root / f"phase1b-subx-list-{side}" / "debug.log"
        events = [tuple(int(value, 16) for value in match)
                  for match in TRACE.findall(trace_path.read_text())]
        assert len(events) == 12, (side, len(events))
        print(f"{side}: {len(events)} matching sub-CPU X list loads")
        seen = set()
        for frame, identity, source in STAGES:
            shared = words(directory / f"shared-list-{frame:04d}.bin")
            records = [(index, struct.unpack_from(">4I", shared, index * 16))
                       for index in range(0x2000 // 16)]
            candidates = [(index, fields) for index, fields in records
                          if fields[0] == identity and fields[3] == source]
            assert len(candidates) == 1, (side, frame, candidates)
            index, fields = candidates[0]
            candidates = [event for event in events if event[:4] == fields
                          and event[4] == 0x0C9800]
            assert len(candidates) == 1, (side, frame, candidates)
            event = candidates[0]
            slot = event[5] - 0x180000 + 0x2000
            assert 0 <= slot <= 0xFFF0 and slot % 16 == 0
            sprite = (root / f"phase1b-geometry-sequence-{side}" /
                      f"source-{frame:04d}-ysprites.bin").read_bytes()
            assert len(sprite) == 0x10000
            descriptor = struct.unpack_from(">8H", sprite, slot)
            assert descriptor[0] != 0xFFFF
            seen.add(event)
            matches += 1
            print(f"  callback {frame}: list +{index*16:04X}, "
                  f"identity={identity:08X}, subX A2={event[5]:06X}, "
                  f"descriptor +{slot:04X}, X={descriptor[1]&0xFFF:03X}, "
                  f"graphic={descriptor[3]:04X}")
        assert len(seen) == 3
        for start, end, identity, source in ((960, 963, *STAGES[0][1:]),
                                              (964, 967, *STAGES[1][1:]),
                                              (968, 970, *STAGES[2][1:])):
            for frame in range(start, end + 1):
                shared = words(directory / f"shared-list-{frame:04d}.bin")
                hits = sum(struct.unpack_from(">II", shared, index * 16)[0]
                           == identity and
                           struct.unpack_from(">I", shared, index * 16 + 12)[0]
                           == source for index in range(0x2000 // 16))
                assert hits == 1, (side, frame, hits)
    print(f"selected list → sub-CPU load → descriptor: {matches}/{matches} "
          "matched stages; selected identity is stable within each epoch")
    for frame, slot, base_name in ((962, 0xE600,
                                    "phase1b-geometry-sequence-center"),
                                   (970, 0xE5D0, "phase1b-list-baseline-970")):
        baseline = root / base_name
        changed = root / f"phase1b-list-shift-{frame}"
        before = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
        after = (changed / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
        assert len(before) == len(after) == 0x10000
        different = [i for i, (a, b) in enumerate(zip(before, after))
                     if a != b]
        assert different and all(slot + 2 <= i <= slot + 3
                                 for i in different)
        assert int.from_bytes(after[slot+2:slot+4], "big") == (
            int.from_bytes(before[slot+2:slot+4], "big") + 3)
        base_bitmap, _ = source_words(baseline, frame)
        shifted_bitmap, _ = source_words(changed, frame)
        bitmap_diffs = [(i % 512, i // 512) for i, (a, b) in
                        enumerate(zip(base_bitmap, shifted_bitmap)) if a != b]
        screen_frame = frame + 1
        base_screen = png_rows(baseline / f"swap-screen-{screen_frame:04d}.png")
        shifted_screen = png_rows(changed / f"swap-screen-{screen_frame:04d}.png")
        screen_diffs = [(x, y) for y in range(224) for x in range(320)
                        if base_screen[y][x*3:x*3+3] !=
                        shifted_screen[y][x*3:x*3+3]]
        assert bitmap_diffs and screen_diffs
        for earlier in range(960, frame + 1):
            base = png_rows(baseline / f"swap-screen-{earlier:04d}.png")
            shifted = png_rows(changed / f"swap-screen-{earlier:04d}.png")
            assert changed_pixels(base, shifted) == 0, (frame, earlier)
        print(f"descriptor +{slot:04X} X+3 at callback {frame}: "
              f"{len(bitmap_diffs)} native bitmap pixels, "
              f"{len(screen_diffs)} screen pixels at callback {screen_frame}; "
              f"screen bbox x={min(x for x, _ in screen_diffs)}–"
              f"{max(x for x, _ in screen_diffs)}, "
              f"y={min(y for _, y in screen_diffs)}–"
              f"{max(y for _, y in screen_diffs)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    try:
        main(args.private_root)
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
