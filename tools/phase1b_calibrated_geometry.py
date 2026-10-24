#!/usr/bin/env python3
"""Compare causally verified arcade edges with existing host-rendered road PNGs."""

import argparse
import hashlib
import json
from pathlib import Path

from phase1b_wide_host_fixture import read_png_rows


ROLES = ("fit", "adaptation", "check")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_file(root, name):
    assert isinstance(name, str) and not Path(name).is_absolute()
    path = (root / name).resolve()
    assert path.is_relative_to(root) and path.is_file(), name
    return path


def nearest_even(numerator, denominator):
    quotient, remainder = divmod(numerator, denominator)
    if 2 * remainder > denominator or (2 * remainder == denominator and quotient % 2):
        return quotient + 1
    return quotient


def output_row(y, calibration):
    top, bottom = calibration["arcade_y_crop_inclusive"]
    height = calibration["output_image"][1]
    assert top <= y <= bottom and bottom > top
    return nearest_even((y - top) * (height - 1), bottom - top)


def target_bounds(left, right, calibration):
    width = calibration["output_image"][0]
    mapping = calibration["arcade_x_at_output_pixel_center"]
    scale = mapping["denominator"]
    multiplier = mapping["x_multiplier"]
    offset = mapping["offset"]
    assert 0 <= left <= right < calibration["arcade_screen"][0]
    xs = [x for x in range(width)
          if scale * left <= multiplier * x + offset <= scale * right]
    assert xs, (left, right)
    return xs[0], xs[-1]


def image_bounds(pixels, row, road_rgb):
    xs = [x for x, rgb in enumerate(pixels[row]) if rgb in road_rgb]
    assert xs and xs == list(range(xs[0], xs[-1] + 1)), row
    return xs[0], xs[-1]


def metrics(rows):
    return {"count": len(rows),
            "mean_absolute_edge_error": round(sum(
                abs(r["delta_left"]) + abs(r["delta_right"]) for r in rows
            ) / (2 * len(rows)), 6),
            "mean_absolute_width_error": round(sum(
                abs(r["delta_width"]) for r in rows
            ) / len(rows), 6)}


def compare(root, calibration_path, cases_path):
    calibration = json.loads(calibration_path.read_text())
    cases = json.loads(cases_path.read_text())
    assert calibration["schema"] == cases["schema"] == 1
    assert calibration["status"] == "project_design_choice_not_recovered_arcade_projection"
    assert calibration["output_row_rounding"] == "nearest_even"
    assert calibration["edge_membership"] == "inclusive_arcade_left_and_right"
    assert all(value > 0 for value in calibration["arcade_screen"])
    assert all(value > 0 for value in calibration["output_image"])
    top, bottom = calibration["arcade_y_crop_inclusive"]
    assert 0 <= top < bottom < calibration["arcade_screen"][1]
    mapping = calibration["arcade_x_at_output_pixel_center"]
    assert mapping["x_multiplier"] > 0 and mapping["denominator"] > 0
    road_rgb = {tuple(color) for color in calibration["host_road_rgb"]}
    assert road_rgb and all(len(rgb) == 3 and all(0 <= c <= 255 for c in rgb)
                            for rgb in road_rgb)
    results = []
    for case in cases["cases"]:
        evidence_path = private_file(root, case["evidence"])
        image_path = private_file(root, case["host_image"])
        evidence = json.loads(evidence_path.read_text())
        selector = case["evidence_rows"]
        assert selector in ("measurements", "records[0].rows")
        source_rows = (evidence["measurements"] if selector == "measurements"
                       else evidence["records"][0]["rows"])
        if "callback" in evidence:
            assert evidence["callback"] + 1 == case["screen_frame"]
        by_y = {row["y"]: row for row in source_rows}
        assert len(by_y) == len(source_rows)
        pixels = read_png_rows(image_path, *calibration["output_image"])
        assert len(case["camera_packet"]) == 5
        assert set(case["rows"]).issubset(ROLES)
        used = set()
        rows = []
        for role in ROLES:
            for y in case["rows"].get(role, []):
                assert y not in used and y in by_y
                used.add(y)
                source = by_y[y]
                assert source["left_changed"] and source["right_changed"]
                row = output_row(y, calibration)
                target_left, target_right = target_bounds(
                    source["left"], source["right"], calibration)
                host_left, host_right = image_bounds(pixels, row, road_rgb)
                rows.append({"role": role, "arcade_y": y, "output_row": row,
                             "arcade_edges": [source["left"], source["right"]],
                             "target_edges": [target_left, target_right],
                             "host_edges": [host_left, host_right],
                             "delta_left": host_left - target_left,
                             "delta_right": host_right - target_right,
                             "delta_width": ((host_right - host_left) -
                                             (target_right - target_left))})
        assert len({r["output_row"] for r in rows}) == len(rows)
        grouped = {role: metrics([row for row in rows if row["role"] == role])
                   for role in ROLES if any(row["role"] == role for row in rows)}
        results.append({"id": case["id"], "screen_frame": case["screen_frame"],
                        "camera_packet": case["camera_packet"],
                        "evidence": case["evidence"],
                        "evidence_sha256": digest(evidence_path),
                        "host_image": case["host_image"],
                        "host_image_sha256": digest(image_path),
                        "rows": rows, "role_metrics": grouped})
    return {"schema": 1,
            "calibration_sha256": digest(calibration_path),
            "cases_sha256": digest(cases_path),
            "calibration_status": calibration["status"],
            "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("cases", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    output = root / "phase1b-calibrated-geometry.json"
    result = compare(root, args.calibration, args.cases)
    output.write_text(json.dumps(result, indent=2) + "\n")
    for case in result["cases"]:
        print(case["id"], case["role_metrics"])
    print("private result:", output)
