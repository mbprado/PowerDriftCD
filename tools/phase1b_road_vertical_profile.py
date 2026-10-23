#!/usr/bin/env python3
"""Test a bounded original-art road-width bump against fixed camera packets."""

import argparse
import json
from pathlib import Path

from make_graphics_asic_fixture import tile_bytes
from make_perspective_road import CURVE_SINE, grass_pixel, wide_geometry_lines
from phase1b_road_width_profile import COLORS, score, variant_road_pixel
from phase1b_wide_host_fixture import (
    arcade_edge_to_output, arcade_to_output_row, digest, read_png_rows, write_png,
)


WIDTHS = (52, 54, 58)
CENTER = 139
PACKETS = {971: (63, 0, 0, 4, 42),
           973: (38, 0, 0, 4, 15),
           975: (38, 0, 0, 4, 31)}


def pixel(sx, sy, bumped):
    if not (0 <= sx < 256 and 0 <= sy < 256):
        raise ValueError((sx, sy))
    if 96 <= sx < 176:
        band = (sy // 16) % 3
        width = WIDTHS[band]
        if bumped and band == 1 and 6 <= sy % 16 <= 9:
            width = 56
        return variant_road_pixel(sx, sy % 16, width, CENTER)
    return grass_pixel(sx % 16, sy % 16)


def image(packet, bumped):
    output = []
    for start_x, start_y, dx, dy in wide_geometry_lines(
            0, packet_fn=lambda _: packet):
        output.append([pixel((start_x + x * (dx // 256)) // 8,
                             (start_y + x * (dy // 256)) // 8, bumped)
                       for x in range(128)])
    assert len(output) == 64
    return output


def packet_bounds(packet, rows, bumped):
    traces = list(wide_geometry_lines(0, packet_fn=lambda _: packet))
    pixels = []
    for row in rows:
        start_x, start_y, dx, dy = traces[row]
        pixels.append([pixel((start_x + x * (dx // 256)) // 8,
                             (start_y + x * (dy // 256)) // 8, bumped)
                       for x in range(128)])
    return bounds({row: pixels[i] for i, row in enumerate(rows)}, rows)


def bounds(pixels, rows):
    result = []
    for row in rows:
        xs = [x for x, value in enumerate(pixels[row])
              if value in (7, 10, 14, 15)]
        if not xs or xs != list(range(xs[0], xs[-1] + 1)):
            return None
        result.append({"row": row, "left": xs[0], "right": xs[-1],
                       "width": len(xs)})
    return result


def target(rows):
    result = []
    for item in rows:
        left, right = arcade_edge_to_output(item["left"], item["right"])
        result.append({"row": arcade_to_output_row(item["y"]),
                       "left": left, "right": right,
                       "width": right - left + 1})
    return result


def stamps(destination):
    data = bytearray(128)
    for band, base_width in enumerate(WIDTHS):
        for column in range(6, 11):
            data.extend(tile_bytes(
                lambda x, y, band=band, base_width=base_width,
                       column=column: variant_road_pixel(
                           column * 16 + x, y,
                           56 if band == 1 and 6 <= y <= 9 else base_width,
                           CENTER)))
    data.extend(tile_bytes(grass_pixel))
    assert len(data) == 2176
    path = destination / "original-road-stamps.bin"
    path.write_bytes(data)
    return {"bytes": len(data), "sha256": digest(path)}


def main(root):
    prior = json.loads((root / "phase1b-road-width-profile.json").read_text())
    selected, = [result for result in prior["results"]
                 if result["profile"] == "narrow_shifted_art"
                 and result["horizontal_offset"] == 0]
    assert {fit["screen_frame"]: tuple(fit["packet"])
            for fit in selected["fits"]} == PACKETS
    destination = root / "phase1b-road-vertical-profile"
    destination.mkdir(parents=True, exist_ok=True)
    stamp_record = stamps(destination)
    fixed = []
    for fit in selected["fits"]:
        frame = fit["screen_frame"]
        baseline, changed = (image(PACKETS[frame], bump)
                             for bump in (False, True))
        baseline_rows = bounds(baseline, [22, 24, 25])
        assert baseline_rows == fit["host_rows"]
        anchor = bounds(changed, [22, 24, 25])
        source = fit["target"]
        record = {"screen_frame": frame, "packet": PACKETS[frame],
                  "anchor_target": source, "baseline_anchor": baseline_rows,
                  "changed_anchor": anchor,
                  "baseline_anchor_error": score(source, baseline_rows),
                  "changed_anchor_error": score(source, anchor)}
        if frame == 975:
            held = prior["held_out"]
            before = bounds(baseline, [26, 27, 28])
            after = bounds(changed, [26, 27, 28])
            assert before == held["host_rows"]
            record["adapted_rows"] = {
                "target": held["target"], "baseline": before,
                "changed": after, "baseline_error": score(held["target"], before),
                "changed_error": score(held["target"], after)}
        path = destination / f"changed-{frame}.png"
        rgb = [[COLORS[value] for value in row] for row in changed]
        write_png(path, rgb)
        assert read_png_rows(path, 128, 64) == rgb
        record["preview_sha256"] = digest(path)
        fixed.append(record)

    independent = json.loads((root / "phase1b-right-search-968-A500-00100.json").read_text())
    assert independent["callback"] == 968 and independent["pulse"] == 112
    source, = [record for record in independent["records"]
               if record["group"] == "A600-00100"]
    rows = source["rows"]
    assert [r["y"] for r in rows] == [152, 153, 154, 155, 156]
    assert not rows[0]["left_changed"] and rows[0]["right_changed"]
    assert all(r["left_changed"] and r["right_changed"] for r in rows[1:])
    anchor_target = target(rows[2:])
    check_target = target(rows[1:2])
    candidates = []
    fit_output_rows = [r["row"] for r in anchor_target]
    for curve in range(len(CURVE_SINE)):
        for texture in range(48):
            packet = (curve, 0, 0, 4, texture)
            geometry = packet_bounds(packet, fit_output_rows, False)
            if geometry is not None:
                candidates.append((score(anchor_target, geometry), packet))
    _, packet = min(candidates, key=lambda item: (item[0], item[1]))
    independent_results = []
    broad = json.loads((root / "phase1b-right-search-968-A000-00800.json").read_text())
    assert broad["callback"] == 968 and broad["pulse"] == 112
    outer_source, = [row for row in broad["records"][0]["rows"]
                     if row["y"] == 152]
    assert outer_source["left_changed"] and outer_source["right_changed"]
    outer_target = target([outer_source])
    for bump in (False, True):
        anchor = packet_bounds(packet, fit_output_rows, bump)
        check = packet_bounds(packet, [r["row"] for r in check_target], bump)
        outer = packet_bounds(packet, [r["row"] for r in outer_target], bump)
        independent_results.append({"variant": "local_bump" if bump else "baseline",
                                    "anchor": anchor,
                                    "anchor_error": score(anchor_target, anchor),
                                    "check": check,
                                    "check_error": score(check_target, check),
                                    "broad_hide_outer": outer,
                                    "broad_hide_outer_error": score(outer_target, outer)})
    result = {"source_widths": WIDTHS, "source_center": CENTER,
              "changed_source_y_modulo_48": [22, 23, 24, 25],
              "changed_width": 56, "stamp_art": stamp_record,
              "fixed_packets": fixed,
              "independent_screen_969": {
                  "screen_frame": 969, "fit_rows": anchor_target,
                  "check_rows": check_target,
                  "broad_hide_outer_target": outer_target,
                  "causal_source_group": source["group"],
                  "fit_candidate_count": len(candidates),
                  "optimistic_fit_packet": packet,
                  "results": independent_results}}
    path = destination / "result.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"fixed": [(r["screen_frame"], r["baseline_anchor_error"],
                                  r["changed_anchor_error"])
                                 for r in fixed],
                      "adapted": fixed[-1]["adapted_rows"],
                      "independent": result["independent_screen_969"],
                      "private_result": str(path)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve())
