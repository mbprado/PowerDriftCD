#!/usr/bin/env python3
"""Emit original 5x7 monochrome letter tiles for the Phase 0 text IP."""

import pathlib

GLYPHS = {
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
}


def build():
    tiles = bytearray()
    # Tile numbers 1..9 must match src/smoke/ip.S's message table.
    for letter in "HELOSGACD":
        rows = GLYPHS[letter]
        for row in (*rows, "00000"):
            pixels = "0" + row + "00"
            tiles.extend((int(pixels[i]) << 4) | int(pixels[i + 1])
                         for i in range(0, 8, 2))
    return bytes(tiles)


if __name__ == "__main__":
    path = pathlib.Path("build/smoke/font.bin")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build())
