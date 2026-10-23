#!/usr/bin/env python3
"""Generate original stamp-map geometry and packets for coupled road motion."""

import json
from pathlib import Path
import sys

from make_graphics_asic_fixture import tile_bytes
from make_perspective_road import (
    FRAMES, grass_pixel, output_words, wide_geometry_anchor_rows,
    wide_geometry_lines,
)


ROAD_WIDTHS = (56, 58, 60)


def motion_packet(frame):
    """Existing five words: lateral phase and forward texture position vary."""
    return (frame * 3 % 96, 0, 0, 4, frame * 2 % 48)


def road_pixel(x, y, width):
    left = 136 - width // 2
    right = left + width - 1
    if x in (left, right):
        return 15
    if x in (left + 1, right - 1):
        return 10
    if x in (135, 136) and y < 8:
        return 14
    if left <= x <= right:
        return 7
    return grass_pixel(x, y)


def source_pixel(sx, sy):
    if not (0 <= sx < 256 and 0 <= sy < 256):
        raise ValueError(f"source coordinate outside stamp map: {sx}, {sy}")
    if 96 <= sx < 176:
        return road_pixel(sx, sy % 16, ROAD_WIDTHS[(sy // 16) % 3])
    return grass_pixel(sx % 16, sy % 16)


def trace_lines(frame):
    return wide_geometry_lines(frame, packet_fn=motion_packet)


def main(destination):
    destination.mkdir(parents=True, exist_ok=True)
    stamps = bytearray(128)  # stamp 0 remains unused
    for width in ROAD_WIDTHS:
        for column in range(6, 11):
            stamps.extend(tile_bytes(
                lambda x, y, width=width, column=column:
                road_pixel(column * 16 + x, y, width)))
    stamps.extend(tile_bytes(grass_pixel))  # stamp 16
    assert len(stamps) == 17 * 128
    (destination / "road-wide-motion-stamps.bin").write_bytes(stamps)

    packets = bytearray()
    metrics = []
    for frame in range(FRAMES):
        packet = motion_packet(frame)
        for value in packet:
            packets.extend((value & 0xffff).to_bytes(2, "big"))
        words = output_words(frame, trace_lines, width=128,
                             pixel_factory=source_pixel)
        metrics.append({"frame": frame, "camera_packet": packet,
                        "word_sum": sum(words),
                        "anchor_rows": wide_geometry_anchor_rows(words)})

    row28 = [entry["anchor_rows"][3] for entry in metrics]
    widths = [row["width"] for row in row28]
    centers = [(row["left"] + row["right"]) / 2 for row in row28]
    simultaneous = sum(widths[index] != widths[index-1]
                       and centers[index] != centers[index-1]
                       for index in range(1, FRAMES))
    all_rows = [row for entry in metrics for row in entry["anchor_rows"]]
    assert min(row["width"] for row in all_rows) >= 89
    assert max(row["width"] for row in all_rows) <= 96
    assert all(0 < row["left"] <= row["right"] < 127 for row in all_rows)
    assert simultaneous >= 10
    (destination / "road-wide-motion-packets.bin").write_bytes(packets)
    (destination / "road-wide-motion-sums.inc").write_text(
        "/* Expected 128x64 ASIC output for coupled road-motion packets. */\n"
        + "\n".join(f"    .long 0x{entry['word_sum']:08x}"
                    for entry in metrics) + "\n")
    (destination / "road-wide-motion-metrics.json").write_text(
        json.dumps({"source_road_widths": ROAD_WIDTHS,
                    "row28_width_values": sorted(set(widths)),
                    "row28_center_range": [min(centers), max(centers)],
                    "simultaneous_adjacent_updates": simultaneous,
                    "frames": metrics}, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: make_wide_road_motion.py OUTDIR")
    main(Path(sys.argv[1]))
