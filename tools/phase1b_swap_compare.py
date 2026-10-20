#!/usr/bin/env python3
"""Compare private Y-Board rotation-swap traces without publishing their contents."""

import argparse
import struct
import zlib
from pathlib import Path


def png_rows(path):
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not PNG: {path}")
    chunks = []
    offset = 8
    while offset < len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += length + 12
        if kind == b"IHDR":
            width, height, depth, color, *_ = struct.unpack(">IIBBBBB", payload)
            if (width, height, depth, color) != (320, 224, 8, 2):
                raise ValueError(f"unexpected PNG format: {path}")
        elif kind == b"IDAT":
            chunks.append(payload)
        elif kind == b"IEND":
            break
    pixels = zlib.decompress(b"".join(chunks))
    stride = width * 3
    previous = bytearray(stride)
    rows = []
    offset = 0
    for _ in range(height):
        filtering = pixels[offset]
        offset += 1
        row = bytearray(pixels[offset:offset + stride])
        offset += stride
        for index in range(stride):
            left = row[index - 3] if index >= 3 else 0
            above = previous[index]
            upper_left = previous[index - 3] if index >= 3 else 0
            if filtering == 1:
                predictor = left
            elif filtering == 2:
                predictor = above
            elif filtering == 3:
                predictor = (left + above) // 2
            elif filtering == 4:
                base = left + above - upper_left
                distances = (abs(base - left), abs(base - above), abs(base - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            elif filtering == 0:
                predictor = 0
            else:
                raise ValueError(f"unsupported PNG filter {filtering}: {path}")
            row[index] = (row[index] + predictor) & 0xFF
        rows.append(row)
        previous = row
    return rows


def different_bytes(first, second):
    if len(first) != len(second):
        raise ValueError("different capture lengths")
    return sum(a != b for a, b in zip(first, second))


def changed_pixels(first, second, x0=0, x1=320, y0=0, y1=224):
    return sum(
        first[y][3 * x:3 * x + 3] != second[y][3 * x:3 * x + 3]
        for y in range(y0, y1) for x in range(x0, x1)
    )


def read_capture(directory, kind, frame):
    matches = list(directory.glob(f"swap-{kind}-{frame:04d}-*.bin"))
    if len(matches) != 1:
        raise ValueError(f"expected one {kind} capture at {frame} in {directory}")
    content = matches[0].read_bytes()
    if len(content) != 32:
        raise ValueError(f"expected 32 bytes: {matches[0]}")
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("center", type=Path)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    for name in ("left", "right"):
        other = getattr(args, name)
        print(name)
        for frame in (960, 962, 964, 966, 970, 1020):
            center = read_capture(args.center, "pre", frame)
            changed = read_capture(other, "pre", frame)
            deltas = tuple(b - a for a, b in zip(
                struct.unpack(">6i", center[:24]), struct.unpack(">6i", changed[:24])
            ))
            print(f"  swap after callback {frame}: {different_bytes(center, changed)} bytes; "
                  f"six signed 32-bit deltas {deltas}")
        for frame in (960, 961, 962, 963, 965, 970):
            first = png_rows(args.center / f"swap-screen-{frame:04d}.png")
            second = png_rows(other / f"swap-screen-{frame:04d}.png")
            print(f"  screenshot {frame}: {changed_pixels(first, second)} pixels; "
                  f"road rectangle x=0..319,y=80..169: "
                  f"{changed_pixels(first, second, 0, 320, 80, 170)}")
    for name in ("center", "left", "right"):
        directory = getattr(args, name)
        frames = list(range(956, 1021, 2))
        lag_matches = sum(read_capture(directory, "post", later) ==
                          read_capture(directory, "pre", earlier)
                          for earlier, later in zip(frames, frames[1:]))
        print(f"{name}: post-swap block equals prior pre-swap block "
              f"at {lag_matches}/{len(frames) - 1} consecutive swaps")


if __name__ == "__main__":
    main()
