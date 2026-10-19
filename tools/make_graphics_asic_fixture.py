#!/usr/bin/env python3
"""Generate original 16x16 stamp and independently calculated ASIC expectations."""

from pathlib import Path
import sys


def be16(values):
    return b"".join(value.to_bytes(2, "big", signed=False) for value in values)


def pixel(x, y):
    return 1 + ((x // 4 + 4 * (y // 4)) % 15)


def tile_bytes(sample):
    result = bytearray()
    for cell_x in range(2):
        for cell_y in range(2):
            for row in range(8):
                y = 8 * cell_y + row
                for pair in range(2):
                    x = 8 * cell_x + 4 * pair
                    colors = [sample(x + offset, y) for offset in range(4)]
                    result.extend(((colors[0] << 4) | colors[1],
                                   (colors[2] << 4) | colors[3]))
    return bytes(result)


def source(case, x, y):
    if case == "identity":
        return x, y
    if case == "scale":
        return x // 2, y // 2
    if case == "rotate":
        return y, 15 - x
    if case == "combined":
        return y // 2, 15 - x // 2
    raise ValueError(case)


def trace(case):
    words = []
    for y in range(16):
        if case == "identity":
            x_start, y_start, dx, dy = 0, y * 8, 0x800, 0
        elif case == "scale":
            x_start, y_start, dx, dy = 0, (y // 2) * 8, 0x400, 0
        elif case == "rotate":
            x_start, y_start, dx, dy = y * 8, 15 * 8, 0, -0x800
        else:
            # Start at 15.5 so floor(15.5 - x/2) repeats each source row.
            x_start, y_start, dx, dy = (y // 2) * 8, 15 * 8 + 4, 0, -0x400
        words.extend((x_start, y_start, dx & 0xFFFF, dy & 0xFFFF))
    return be16(words)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: make_graphics_asic_fixture.py OUTDIR")
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=True)
    (target / "stamp.bin").write_bytes(tile_bytes(pixel))
    for case in ("identity", "scale", "rotate", "combined"):
        (target / f"trace-{case}.bin").write_bytes(trace(case))
        (target / f"expected-{case}.bin").write_bytes(
            tile_bytes(lambda x, y: pixel(*source(case, x, y))))


if __name__ == "__main__":
    main()
