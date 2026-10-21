#!/usr/bin/env python3
"""Compare private Y-Board sprite and palette RAM snapshots around a steering pulse."""

import argparse
from pathlib import Path


SIZES = {"ysprites": 0x10000, "bsprites": 0x1000, "palette": 0x4000}


def capture(directory, frame, name):
    path = directory / f"source-{frame:04d}-{name}.bin"
    content = path.read_bytes()
    if len(content) != SIZES[name]:
        raise ValueError(f"wrong capture size: {path}")
    return content


def changed_bytes(first, second):
    return sum(a != b for a, b in zip(first, second))


def verify_repeat(original, repeat):
    for frame in range(960, 971):
        for name in SIZES:
            if capture(original, frame, name) != capture(repeat, frame, name):
                raise ValueError(f"repeat mismatch: {original}, {repeat}, {frame}, {name}")


def verify_substitution(center, normal, substituted):
    if (substituted / "source-0966-ysprites-after.bin").read_bytes() != \
            capture(center, 966, "ysprites"):
        raise ValueError(f"substitution did not match centered source: {substituted}")
    for name in ("swap-pre-0966-006.bin", "swap-screen-0965.png",
                 "swap-screen-0966.png", "swap-screen-0969.png"):
        if (substituted / name).read_bytes() != (normal / name).read_bytes():
            raise ValueError(f"unexpected change outside immediate response: {name}")
    if (substituted / "swap-screen-0967.png").read_bytes() == \
            (normal / "swap-screen-0967.png").read_bytes():
        raise ValueError(f"no immediate display response: {substituted}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--center-repeat", type=Path)
    parser.add_argument("--left-repeat", type=Path)
    parser.add_argument("--sham-left", type=Path)
    parser.add_argument("--replace-left", type=Path)
    parser.add_argument("--replace-right", type=Path)
    args = parser.parse_args()
    if args.center_repeat:
        verify_repeat(args.center, args.center_repeat)
    if args.left_repeat:
        verify_repeat(args.left, args.left_repeat)
    if args.sham_left:
        for frame in range(960, 971):
            name = f"swap-screen-{frame:04d}.png"
            if (args.sham_left / name).read_bytes() != (args.left / name).read_bytes():
                raise ValueError(f"sham image changed at {frame}")
    if args.replace_left:
        verify_substitution(args.center, args.left, args.replace_left)
    if args.replace_right:
        verify_substitution(args.center, args.right, args.replace_right)
    print("callback,ysprites_left,ysprites_right,bsprites_left,bsprites_right,"
          "palette_left,palette_right")
    for frame in range(960, 971):
        values = []
        for name in SIZES:
            centered = capture(args.center, frame, name)
            values.extend(changed_bytes(centered, capture(run, frame, name))
                          for run in (args.left, args.right))
        print(f"{frame}," + ",".join(map(str, values)))


if __name__ == "__main__":
    main()
