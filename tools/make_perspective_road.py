#!/usr/bin/env python3
"""Generate original road stamps, full/compact traces, and frame checksums."""

import math
from pathlib import Path
import sys

from make_graphics_asic_fixture import tile_bytes

SIZE = 64
PERIOD = 24
FRAMES = 60

COMPARE_GLYPHS = {
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
}


def road_pixel(x, y):
    if x in (0, 15):
        return 15  # white edge
    if x in (1, 14):
        return 10  # red shoulder
    if x in (7, 8) and y < 8:
        return 14  # dashed center line
    return 7  # asphalt


def grass_pixel(x, y):
    return 2 + ((x // 4 + y // 4) & 1)


def lines(frame):
    phase = 2 * math.pi * (frame % PERIOD) / PERIOD
    bank = round(2 * math.sin(phase))  # eighth-pixels of Y per destination X
    horizon = 4 + round(3 * math.sin(phase + math.pi / 3))
    for y in range(SIZE):
        depth = max(0, y - horizon)
        scale_band = min(3, depth // 15)
        dx_eighth = (16, 12, 8, 4)[scale_band]
        curve = round(5 * math.sin(phase + y * math.pi / 48))
        bank_shift = bank * (y - SIZE // 2) // 8
        # The ridge term makes the road texture compress and expand along depth.
        ridge = round(6 * math.sin(phase + y * math.pi / 32))
        source_y = 20 + 3 * depth - depth * depth // 48 + ridge + 2 * (frame % PERIOD)
        x_start = (136 + curve + bank_shift) * 8 - 32 * dx_eighth
        y_start = source_y * 8 - 32 * bank
        yield (x_start, y_start, dx_eighth * 256, bank * 256)


def compact_state(frame):
    """Store camera constants and two signed curve/ridge samples per scanline."""
    phase = 2 * math.pi * (frame % PERIOD) / PERIOD
    bank = round(2 * math.sin(phase))
    horizon = 4 + round(3 * math.sin(phase + math.pi / 3))
    samples = [(round(5 * math.sin(phase + y * math.pi / 48)),
                round(6 * math.sin(phase + y * math.pi / 32)))
               for y in range(SIZE)]
    return bank, horizon, samples


def expand_compact_state(frame, state):
    """Integer reference for the sub-CPU trace builder."""
    bank, horizon, samples = state
    for y, (curve, ridge) in enumerate(samples):
        depth = max(0, y - horizon)
        dx_eighth = (16, 12, 8, 4)[min(3, depth // 15)]
        bank_shift = bank * (y - SIZE // 2) // 8
        source_y = 20 + 3 * depth - depth * depth // 48 + ridge + 2 * frame
        yield ((136 + curve + bank_shift) * 8 - 32 * dx_eighth,
               source_y * 8 - 32 * bank, dx_eighth * 256, bank * 256)


def source_pixel(sx, sy):
    if not (0 <= sx < 256 and 0 <= sy < 256):
        raise ValueError(f"source coordinate outside stamp map: {sx}, {sy}")
    pixel = road_pixel if sx // 16 == 8 else grass_pixel
    return pixel(sx % 16, sy % 16)


CURVE_SINE = [round(5 * math.sin(2 * math.pi * index / 96))
              for index in range(96)]
RIDGE_SINE = [round(6 * math.sin(2 * math.pi * index / 192))
              for index in range(192)]


def full_camera_lines(frame):
    """Derive scanline curve/ridge from phase plus small shared sine tables."""
    state = frame % PERIOD
    bank, horizon, _ = compact_state(state)
    for y in range(SIZE):
        depth = max(0, y - horizon)
        dx_eighth = (16, 12, 8, 4)[min(3, depth // 15)]
        curve = CURVE_SINE[(4 * state + y) % 96]
        ridge = RIDGE_SINE[(8 * state + 3 * y) % 192]
        bank_shift = bank * (y - SIZE // 2) // 8
        source_y = 20 + 3 * depth - depth * depth // 48 + ridge + 2 * state
        yield ((136 + curve + bank_shift) * 8 - 32 * dx_eighth,
               source_y * 8 - 32 * bank, dx_eighth * 256, bank * 256)


def output_words(frame, line_factory=lines):
    image = []
    trace_lines = list(line_factory(frame))
    for x_cell in range(SIZE // 8):
        for y_cell in range(SIZE // 8):
            for local_y in range(8):
                y = y_cell * 8 + local_y
                x_start, y_start, dx, dy = trace_lines[y]
                for pair in range(2):
                    x = x_cell * 8 + pair * 4
                    pixels = []
                    for pixel_x in range(x, x + 4):
                        sx = (x_start + pixel_x * (dx // 256)) // 8
                        sy = (y_start + pixel_x * (dy // 256)) // 8
                        pixels.append(source_pixel(sx, sy))
                    image.append(sum(value << (12 - 4 * index)
                                     for index, value in enumerate(pixels)))
    return image


def compare_font():
    """Eight original 5x7 glyphs, VDP tile IDs 65..72 after the road tiles."""
    tiles = bytearray()
    for letter in "PREUNTIM":
        for row in (*COMPARE_GLYPHS[letter], "00000"):
            pixels = "0" + row + "00"
            tiles.extend((int(pixels[i]) * 15 << 4) | int(pixels[i + 1]) * 15
                         for i in range(0, 8, 2))
    return bytes(tiles)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: make_perspective_road.py OUTDIR")
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    stamps = bytearray(128)  # stamp zero remains unused
    stamps.extend(tile_bytes(road_pixel))
    stamps.extend(tile_bytes(grass_pixel))
    (destination / "road-stamps.bin").write_bytes(stamps)
    trace = bytearray()
    compact = bytearray()
    for frame in range(PERIOD):
        state = compact_state(frame)
        if list(expand_compact_state(frame, state)) != list(lines(frame)):
            raise ValueError(f"compact trace mismatch at state {frame}")
        bank, horizon, samples = state
        compact.extend((bank & 0xFF, horizon, 2 * frame, 0))
        for curve, ridge in samples:
            compact.extend((curve & 0xFF, ridge & 0xFF))
        for line in lines(frame):
            for word in line:
                trace.extend((word & 0xFFFF).to_bytes(2, "big"))
    (destination / "road-traces.bin").write_bytes(trace)
    (destination / "road-compact.bin").write_bytes(compact)
    (destination / "road-compare-font.bin").write_bytes(compare_font())
    (destination / "road-camera-params.bin").write_bytes(bytes(
        value & 0xFF for frame in range(PERIOD)
        for value in compact_state(frame)[:2]
    ))
    (destination / "road-curve-sine.bin").write_bytes(bytes(
        value & 0xFF for value in CURVE_SINE
    ))
    (destination / "road-ridge-sine.bin").write_bytes(bytes(
        value & 0xFF for value in RIDGE_SINE
    ))
    checksums = []
    for frame in range(FRAMES):
        words = output_words(frame)
        checksums.append(sum(words))
    (destination / "road-sums.inc").write_text(
        "/* Expected 64x64 road output word sums, 60 deterministic frames. */\n"
        + "\n".join(f"    .long 0x{value:08x}" for value in checksums) + "\n"
    )
    full_sums = [sum(output_words(frame, full_camera_lines))
                 for frame in range(FRAMES)]
    (destination / "road-full-camera-sums.inc").write_text(
        "/* Expected 64x64 ASIC output from phase-indexed sine tables. */\n"
        + "\n".join(f"    .long 0x{value:08x}" for value in full_sums) + "\n"
    )


if __name__ == "__main__":
    main()
