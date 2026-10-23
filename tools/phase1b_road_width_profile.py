#!/usr/bin/env python3
"""Fit one original-art source-width variant to three private arcade edge samples."""

import argparse
import json
from pathlib import Path

from make_graphics_asic_fixture import tile_bytes
from make_perspective_road import CURVE_SINE, grass_pixel, wide_geometry_lines
from make_wide_road_motion import ROAD_WIDTHS, road_pixel, source_pixel
from phase1b_three_epoch_road_fit import load_samples
from phase1b_steer_width_trajectory import host_bounds
from phase1b_wide_host_fixture import (
    arcade_edge_to_output, arcade_to_output_row, digest, read_png_rows,
    write_png,
)


PROFILES = (("baseline", ROAD_WIDTHS, 136),
            ("narrow", (52, 54, 58), 136),
            ("narrow_shifted_art", (52, 54, 58), 139))
COLORS = {2: (28, 92, 42), 3: (35, 105, 47), 7: (96, 97, 99),
          10: (188, 42, 35), 14: (239, 220, 92), 15: (232, 221, 201)}


def variant_road_pixel(sx, sy, width, road_center):
    if road_center == 136:
        return road_pixel(sx, sy, width)
    left = road_center - width // 2
    right = left + width - 1
    if sx in (left, right):
        return 15
    if sx in (left + 1, right - 1):
        return 10
    if sx in (road_center - 1, road_center) and sy < 8:
        return 14
    if left <= sx <= right:
        return 7
    return grass_pixel(sx, sy)


def variant_pixel(sx, sy, widths, road_center):
    if not (0 <= sx < 256 and 0 <= sy < 256):
        raise ValueError((sx, sy))
    if 96 <= sx < 176:
        width = widths[(sy // 16) % 3]
        return variant_road_pixel(sx, sy % 16, width, road_center)
    return grass_pixel(sx % 16, sy % 16)


def bounds(packet, rows, widths, road_center):
    traces = list(wide_geometry_lines(0, packet_fn=lambda _: packet))
    result = []
    for y in rows:
        start_x, start_y, dx, dy = traces[y]
        road = []
        for x in range(128):
            sx = (start_x + x * (dx // 256)) // 8
            sy = (start_y + x * (dy // 256)) // 8
            value = (source_pixel(sx, sy) if widths == ROAD_WIDTHS and road_center == 136
                     else variant_pixel(sx, sy, widths, road_center))
            if value in (7, 10, 14, 15):
                road.append(x)
        if not road or road != list(range(road[0], road[-1] + 1)):
            return None
        result.append({"row": y, "left": road[0], "right": road[-1],
                       "width": len(road)})
    return result


def score(target, predicted):
    edge = sum(abs(a["left"] - b["left"]) +
               abs(a["right"] - b["right"])
               for a, b in zip(target, predicted)) / (2 * len(target))
    width = sum(abs(a["width"] - b["width"])
                for a, b in zip(target, predicted)) / len(target)
    return round(edge, 6), round(width, 6)


def render_selected(root, result):
    """Render reviewable original-art previews for the best no-offset variant."""
    assert (result["profile"], result["horizontal_offset"]) == (
        "narrow_shifted_art", 0)
    widths = tuple(result["source_widths"])
    center = result["source_center"]
    destination = root / "phase1b-road-width-profile-preview"
    destination.mkdir(parents=True, exist_ok=True)
    stamps = bytearray(128)  # stamp zero unused, as in the live-road fixture
    for width in widths:
        for column in range(6, 11):
            stamps.extend(tile_bytes(
                lambda x, y, width=width, column=column:
                variant_road_pixel(column * 16 + x, y, width, center)))
    stamps.extend(tile_bytes(grass_pixel))
    assert len(stamps) == 17 * 128
    stamp_path = destination / "original-road-stamps.bin"
    stamp_path.write_bytes(stamps)
    packet_bytes = bytearray()
    images = []
    for fit in result["fits"]:
        packet = tuple(fit["packet"])
        for value in packet:
            packet_bytes.extend(value.to_bytes(2, "big"))
        traces = list(wide_geometry_lines(0, packet_fn=lambda _: packet))
        pixels = []
        for y in range(64):
            start_x, start_y, dx, dy = traces[y]
            row = []
            for x in range(128):
                sx = (start_x + x * (dx // 256)) // 8
                sy = (start_y + x * (dy // 256)) // 8
                row.append(COLORS[variant_pixel(sx, sy, widths, center)])
            pixels.append(row)
        path = destination / f"original-road-{fit['screen_frame']}.png"
        write_png(path, pixels)
        decoded = read_png_rows(path, 128, 64)
        assert decoded == pixels
        for expected in fit["host_rows"]:
            y = expected["row"]
            road = [x for x, rgb in enumerate(decoded[y])
                    if rgb in (COLORS[7], COLORS[10], COLORS[14], COLORS[15])]
            assert road == list(range(expected["left"], expected["right"] + 1))
        images.append({"screen_frame": fit["screen_frame"],
                       "png_sha256": digest(path)})
    packet_path = destination / "fitted-camera-packets.bin"
    packet_path.write_bytes(packet_bytes)
    metadata = {"source_widths": widths, "source_center": center,
                "stamp_bytes": len(stamps), "stamps_sha256": digest(stamp_path),
                "packet_bytes": len(packet_bytes),
                "packets_sha256": digest(packet_path), "images": images}
    (destination / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def held_out_check(root, result):
    """Check extra screen-975 causal rows that were excluded from fitting."""
    raw = json.loads((root / "phase1b-mild-steer-112-hide.json").read_text())
    source = [row for row in raw["measurements"]
              if 157 <= row["y"] <= 159]
    assert [row["y"] for row in source] == [157, 158, 159]
    assert all(row["left_changed"] and row["right_changed"] for row in source)
    target = []
    for row in source:
        left, right = arcade_edge_to_output(row["left"], row["right"])
        target.append({"row": arcade_to_output_row(row["y"]),
                       "left": left, "right": right,
                       "width": right - left + 1})
    selected, = [fit for fit in result["fits"] if fit["screen_frame"] == 975]
    predicted = bounds(tuple(selected["packet"]),
                       tuple(row["row"] for row in target),
                       tuple(result["source_widths"]), result["source_center"])
    edge_error, width_error = score(target, predicted)
    return {"screen_frame": 975, "arcade_rows": [157, 158, 159],
            "target": target, "host_rows": predicted,
            "mean_absolute_edge_error": edge_error,
            "mean_absolute_width_error": width_error}


def main(root):
    samples = load_samples(root)
    rows = tuple(arcade_to_output_row(y) for y in (154, 155, 156))
    assert rows == (22, 24, 25)
    metrics_path = (Path(__file__).resolve().parents[1] / "docs/experiments/data/"
                    "wide-road-motion-host-metrics.json")
    metrics = json.loads(metrics_path.read_text())
    assert len(metrics["frames"]) == 60
    for frame in range(60):
        packet = (frame * 3 % 96, 0, 0, 4, frame * 2 % 48)
        original = bounds(packet, rows, ROAD_WIDTHS, 136)
        assert original == host_bounds(packet, rows)
        assert original[2] == metrics["frames"][frame]["anchor_rows"][0]
    results = []
    for name, widths, road_center in PROFILES:
        candidates = []
        for curve in range(len(CURVE_SINE)):
            for texture in range(48):
                packet = (curve, 0, 0, 4, texture)
                geometry = bounds(packet, rows, widths, road_center)
                if geometry is not None:
                    candidates.append((packet, geometry))
        for offset in (0, -4):
            fits = []
            for sample in samples:
                target = []
                for row in sample["rows"]:
                    left, right = arcade_edge_to_output(row["left"], row["right"])
                    left += offset
                    right += offset
                    target.append({"row": arcade_to_output_row(row["y"]),
                                   "left": left, "right": right,
                                   "width": right - left + 1})
                options = ((score(target, geometry), packet, geometry)
                           for packet, geometry in candidates)
                error, packet, predicted = min(options,
                                               key=lambda item: (item[0], item[1]))
                fits.append({"screen_frame": sample["screen_frame"],
                             "target": target, "packet": packet,
                             "host_rows": predicted,
                             "mean_absolute_edge_error": error[0],
                             "mean_absolute_width_error": error[1]})
            results.append({"profile": name, "source_widths": widths,
                            "source_center": road_center,
                            "horizontal_offset": offset,
                            "candidate_count": len(candidates), "fits": fits})
    output = root / "phase1b-road-width-profile.json"
    selected, = [item for item in results
                 if item["profile"] == "narrow_shifted_art"
                 and item["horizontal_offset"] == 0]
    held_out = held_out_check(root, selected)
    output.write_text(json.dumps({"arcade_crop": [134, 190],
                                  "horizontal_sample": "arcade_x=2.5*output_x+0.75",
                                  "output_rows": rows,
                                  "fixed_camera_words": {"ridge": 0, "bank": 0,
                                                         "horizon": 4},
                                  "results": results,
                                  "held_out": held_out}, indent=2) + "\n")
    print("private preview:", render_selected(root, selected))
    print("held-out screen 975:", held_out)
    for result in results:
        print(result["profile"], result["horizontal_offset"],
              [(f["screen_frame"], f["packet"],
                f["mean_absolute_edge_error"],
                f["mean_absolute_width_error"])
               for f in result["fits"]])
    print("private result:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve())
