#!/usr/bin/env python3
"""Compare private MAME RAM captures from two centered and two steering replays."""

import argparse
from pathlib import Path

PROFILES = {
    "baseline": ((900, 960, 1020, 1080, 1140, 1200),
                 {"main_low": 0x1F0000, "main_high": 0x1FC000, "shared": 0x0C0000}, 960),
    "early": ((960, 961, 962, 965, 970, 980, 1000, 1020),
              {"main_mid1": 0x1F4000, "main_mid2": 0x1F8000,
               "main_high": 0x1FC000, "shared_mid1": 0x0C4000,
               "shared_mid2": 0x0C8000, "shared_high": 0x0CC000}, 961),
}
SIZE = 0x4000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center1", type=Path)
    parser.add_argument("center2", type=Path)
    parser.add_argument("pulse1", type=Path)
    parser.add_argument("pulse2", type=Path)
    parser.add_argument("--left", type=Path, nargs=2, metavar=("LEFT1", "LEFT2"))
    parser.add_argument("--profile", choices=PROFILES, default="baseline")
    args = parser.parse_args()
    frames, windows, pre_pulse_last = PROFILES[args.profile]
    runs = (args.center1, args.center2, args.pulse1, args.pulse2)
    changes = {name: [] for name in windows}
    left_changes = {name: [] for name in windows}

    for frame in frames:
        for name, base in windows.items():
            captures = tuple((run / f"ram-{frame:04d}-{name}.bin").read_bytes()
                             for run in runs)
            if any(len(data) != SIZE for data in captures):
                raise ValueError(f"bad capture size: frame={frame} window={name}")
            if captures[0] != captures[1] or captures[2] != captures[3]:
                raise ValueError(f"repeat mismatch: frame={frame} window={name}")
            offsets = {offset for offset, (a, b) in enumerate(zip(captures[0], captures[2]))
                       if a != b}
            if frame <= pre_pulse_last and offsets:
                raise ValueError(f"pre-pulse divergence: frame={frame} window={name}")
            if frame > pre_pulse_last:
                changes[name].append(offsets)
            if args.left:
                left = tuple((run / f"ram-{frame:04d}-{name}.bin").read_bytes()
                             for run in args.left)
                if any(len(data) != SIZE for data in left) or left[0] != left[1]:
                    raise ValueError(f"left repeat mismatch: frame={frame} window={name}")
                left_offsets = {offset for offset, (a, b) in enumerate(zip(captures[0], left[0]))
                                if a != b}
                if frame <= pre_pulse_last and left_offsets:
                    raise ValueError(f"left pre-pulse divergence: frame={frame} window={name}")
                if frame > pre_pulse_last:
                    left_changes[name].append(left_offsets)
                left_right = sum(a != b for a, b in zip(left[0], captures[2]))
                print(f"{frame},{name},{len(offsets)},{len(left_offsets)},{left_right}")
            else:
                print(f"{frame},{name},{len(offsets)}")

    for name, base in windows.items():
        common = set.intersection(*changes[name])
        addresses = (" ".join(f"{base + offset:06X}" for offset in sorted(common))
                     if len(common) <= 64 else "too_many_to_list")
        print(f"stable_post_pulse,{name},{len(common)},{addresses}")
        if args.left:
            print(f"stable_left_post_pulse,{name},{len(set.intersection(*left_changes[name]))}")


if __name__ == "__main__":
    main()
