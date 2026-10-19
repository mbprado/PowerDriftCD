#!/usr/bin/env python3
"""Generate original trace tables and checksum expectations for ASIC timing."""

from pathlib import Path
import sys


def stamp_pixel(x, y):
    return 1 + (((x % 16) // 4 + 4 * ((y % 16) // 4)) % 15)


def source(kind, n, x, y):
    if kind == "scale":
        return x // 2, y // 2
    if kind == "rotate":
        return y, n - 1 - x
    return y // 2, n - 1 - x // 2


def trace(kind, n):
    result = bytearray()
    for y in range(n):
        if kind == "scale":
            words = (0, (y // 2) * 8, 0x400, 0)
        elif kind == "rotate":
            words = (y * 8, (n - 1) * 8, 0, -0x800)
        else:
            words = ((y // 2) * 8, (n - 1) * 8 + 4, 0, -0x400)
        for value in words:
            result.extend((value & 0xFFFF).to_bytes(2, "big"))
    return bytes(result)


def expected_words(kind, n, x_offset=0):
    words = []
    for cell_x in range(n // 8):
        for cell_y in range(n // 8):
            for local_y in range(8):
                y = cell_y * 8 + local_y
                for local_x in (0, 4):
                    x = cell_x * 8 + local_x
                    colors = [stamp_pixel(source(kind, n, x + dx, y)[0] + x_offset,
                                          source(kind, n, x + dx, y)[1])
                              for dx in range(4)]
                    words.append((colors[0] << 12) | (colors[1] << 8)
                                 | (colors[2] << 4) | colors[3])
    return words


def expected_sum(kind, n):
    total = 0
    for word in expected_words(kind, n):
        total += word
    return total


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: make_graphics_asic_bench.py OUTDIR")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    sums = []
    for n in (16, 32, 64):
        for kind in ("scale", "rotate", "combined"):
            (out / f"trace-{n}-{kind}.bin").write_bytes(trace(kind, n))
            sums.append(expected_sum(kind, n))
    (out / "expected-sums.inc").write_text(
        "/* Independent sums of all output words, in benchmark case order. */\n"
        + "\n".join(f"    .long 0x{value:08x}" for value in sums) + "\n")
    animation = bytearray()
    animation_sums = []
    kinds = ("scale", "rotate", "combined")
    for frame in range(120):
        words = expected_words(kinds[frame % 3], 32, frame % 16)
        animation_sums.append(sum(words))
        if frame < 48:  # LCM(3, 16): unique precomputed images.
            for word in words:
                animation.extend(word.to_bytes(2, "big"))
    (out / "animation-32-48frames.bin").write_bytes(animation)
    (out / "animation-32-sums.inc").write_text(
        "/* Exact original 32x32 output sums for 120 deterministic frames. */\n"
        + "\n".join(f"    .long 0x{value:08x}" for value in animation_sums) + "\n")


if __name__ == "__main__":
    main()
