#!/usr/bin/env python3
"""Render original-art host previews for the independent screen-967 road span."""

import argparse
import json
from pathlib import Path

from make_perspective_road import CURVE_SINE
from phase1b_calibrated_geometry import digest, output_row, target_bounds
from phase1b_road_vertical_profile import COLORS, image, packet_bounds
from phase1b_road_width_profile import score
from phase1b_wide_host_fixture import read_png_rows, write_png


SOURCE = "phase1b-right-search-966-E630-00040-only-E630-E650-E660.json"


def mapped(rows, calibration):
    output = []
    for row in rows:
        left, right = target_bounds(row["left"], row["right"], calibration)
        output.append({"row": output_row(row["y"], calibration),
                       "left": left, "right": right,
                       "width": right - left + 1})
    return output


def main(root, calibration_path):
    calibration = json.loads(calibration_path.read_text())
    path = root / SOURCE
    evidence = json.loads(path.read_text())
    assert evidence["callback"] == 966 and evidence["pulse"] == 112
    record, = evidence["records"]
    assert record["group"] == "E630-00040-only-E630-E650-E660"
    assert record["slots_hidden"] == 3
    rows = record["rows"]
    assert [row["y"] for row in rows] == list(range(153, 164))
    assert all(row["left_changed"] and row["right_changed"] for row in rows)
    fit = mapped([row for row in rows if 154 <= row["y"] <= 156], calibration)
    check = mapped([row for row in rows if row["y"] == 153 or row["y"] >= 157],
                   calibration)
    candidates = []
    for curve in range(len(CURVE_SINE)):
        for texture in range(48):
            packet = (curve, 0, 0, 4, texture)
            predicted = packet_bounds(packet, [row["row"] for row in fit], False)
            if predicted is not None:
                candidates.append((score(fit, predicted), packet))
    _, packet = min(candidates, key=lambda item: (item[0], item[1]))
    assert packet == (38, 0, 0, 4, 31)
    destination = root / "phase1b-screen967-holdout"
    destination.mkdir(parents=True, exist_ok=True)
    results = []
    for bumped, name in ((False, "baseline"), (True, "width-bump")):
        pixels = image(packet, bumped)
        rgb = [[COLORS[value] for value in row] for row in pixels]
        output = destination / f"{name}.png"
        write_png(output, rgb)
        assert read_png_rows(output, 128, 64) == rgb
        fit_host = packet_bounds(packet, [row["row"] for row in fit], bumped)
        check_host = packet_bounds(packet, [row["row"] for row in check], bumped)
        results.append({"variant": name, "image_sha256": digest(output),
                        "fit_error": score(fit, fit_host),
                        "check_error": score(check, check_host)})
    result = {"source_sha256": digest(path),
              "calibration_sha256": digest(calibration_path),
              "candidate_count": len(candidates), "packet": packet,
              "fit_arcade_y": [154, 155, 156],
              "check_arcade_y": [153, 157, 158, 159, 160, 161, 162, 163],
              "results": results}
    (destination / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("calibration", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.calibration)
