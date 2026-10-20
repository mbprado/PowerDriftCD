#!/usr/bin/env python3
"""Compare private MAME RAM captures from two centered and two steering replays."""

import argparse
from pathlib import Path

FRAMES = (900, 960, 1020, 1080, 1140, 1200)
WINDOWS = {"main_low": 0x1F0000, "main_high": 0x1FC000, "shared": 0x0C0000}
SIZE = 0x4000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center1", type=Path)
    parser.add_argument("center2", type=Path)
    parser.add_argument("pulse1", type=Path)
    parser.add_argument("pulse2", type=Path)
    args = parser.parse_args()
    runs = (args.center1, args.center2, args.pulse1, args.pulse2)
    changes = {name: [] for name in WINDOWS}

    for frame in FRAMES:
        for name, base in WINDOWS.items():
            captures = tuple((run / f"ram-{frame:04d}-{name}.bin").read_bytes()
                             for run in runs)
            if any(len(data) != SIZE for data in captures):
                raise ValueError(f"bad capture size: frame={frame} window={name}")
            if captures[0] != captures[1] or captures[2] != captures[3]:
                raise ValueError(f"repeat mismatch: frame={frame} window={name}")
            offsets = {offset for offset, (a, b) in enumerate(zip(captures[0], captures[2]))
                       if a != b}
            if frame <= 960 and offsets:
                raise ValueError(f"pre-pulse divergence: frame={frame} window={name}")
            if frame > 960:
                changes[name].append(offsets)
            print(f"{frame},{name},{len(offsets)}")

    for name, base in WINDOWS.items():
        common = set.intersection(*changes[name])
        addresses = (" ".join(f"{base + offset:06X}" for offset in sorted(common))
                     if len(common) <= 64 else "too_many_to_list")
        print(f"stable_post_pulse,{name},{len(common)},{addresses}")


if __name__ == "__main__":
    main()
