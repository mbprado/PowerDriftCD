#!/usr/bin/env python3
"""Classify measured arcade road edges by 16B occlusion and compare host previews."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from phase1b_calibrated_geometry import compare
from phase1b_mild_steer_width import scan
from phase1b_swap_compare import png_rows


FIRST_SCREEN = 967
LAST_SCREEN = 981
FIRST_ROW = 153
LAST_ROW = 163
TRIAL_NAMES = ("phase1b-road-only-layer-window",
               "phase1b-road-only-layer-window-r2",
               "phase1b-road-only-layer-window-r3")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_layer(path):
    rows = {y: [None] * 320 for y in range(FIRST_ROW, LAST_ROW + 1)}
    with path.open(newline="") as file:
        for item in csv.DictReader(file):
            x, y = int(item["x"]), int(item["y"])
            assert 0 <= x < 320 and FIRST_ROW <= y <= LAST_ROW
            assert rows[y][x] is None
            rows[y][x] = tuple(int(item[key]) for key in
                               ("sprite", "priority", "final"))
    assert all(all(pixel is not None for pixel in row) for row in rows.values())
    return rows


def edge_stage(pixel):
    sprite, priority, _ = pixel
    if sprite != 0xffff and ((sprite >> 11) & 0x1e) < (priority & 0x1f):
        return "16b_occluded"
    if priority == 0xff:
        return "rotation_fill"
    return "clear_rotation"


def classify(screen, trial):
    rows = scan(png_rows(trial / f"swap-screen-{screen:04d}.png"), screen)
    layer = load_layer(trial / f"layer-rows-{screen-1:04d}.csv")
    result = []
    for item in rows:
        y = item["y"]
        if not FIRST_ROW <= y <= LAST_ROW:
            continue
        left = edge_stage(layer[y][item["left"]])
        right = edge_stage(layer[y][item["right"]])
        status = ("16b_occluded" if "16b_occluded" in (left, right)
                  else "rotation_fill" if "rotation_fill" in (left, right)
                  else "clear_visual_candidate")
        result.append({"y": y, "left": item["left"], "right": item["right"],
                       "left_stage": left, "right_stage": right,
                       "status": status})
    return result


def validate_replays(root):
    trials = [root / name for name in TRIAL_NAMES]
    old = root / "phase1b-forward-baseline-112-990"
    for trial in trials:
        for screen in range(960, 983):
            name = f"swap-screen-{screen:04d}.png"
            assert png_rows(trial / name) == png_rows(old / name), (trial, screen)
    for screen in range(FIRST_SCREEN, LAST_SCREEN + 1):
        name = f"layer-rows-{screen-1:04d}.csv"
        hashes = {digest(trial / name) for trial in trials}
        assert len(hashes) == 1, (screen, hashes)
    point = root / "phase1b-layer980/baseline/layer-0979.csv"
    assert (trials[0] / "layer-0979.csv").read_bytes() == point.read_bytes()
    layer = load_layer(trials[0] / "layer-rows-0979.csv")
    with point.open(newline="") as file:
        for item in csv.DictReader(file):
            x, y = int(item["x"]), int(item["y"])
            assert layer[y][x] == tuple(int(item[key]) for key in
                                         ("sprite", "priority", "final"))
    return trials


def audit(root, calibration_path, cases_path):
    trials = validate_replays(root)
    trajectory = {str(screen): classify(screen, trials[0])
                  for screen in range(FIRST_SCREEN, LAST_SCREEN + 1)}
    by_frame_y = {(int(screen), row["y"]): row
                  for screen, rows in trajectory.items() for row in rows}
    comparison = compare(root, calibration_path, cases_path)
    selected = []
    for case in comparison["cases"]:
        for row in case["rows"]:
            key = case["screen_frame"], row["arcade_y"]
            classified = by_frame_y[key]
            assert classified["left"] == row["arcade_edges"][0]
            assert classified["right"] == row["arcade_edges"][1]
            assert classified["status"] == "clear_visual_candidate", (case["id"], key)
            selected.append({"case": case["id"], "role": row["role"],
                             "screen": key[0], "y": key[1],
                             "status": "clear_and_prior_causally_verified",
                             "target_edges": row["target_edges"],
                             "host_edges": row["host_edges"],
                             "delta_left": row["delta_left"],
                             "delta_right": row["delta_right"]})
    assert len(selected) == sum(len(case["rows"]) for case in comparison["cases"])
    assert [(row["y"], row["status"]) for row in trajectory["980"]] == [
        (157, "16b_occluded"), (158, "16b_occluded"),
        (159, "clear_visual_candidate")]
    counts = {"clear_visual_candidate": 0, "16b_occluded": 0,
              "rotation_fill": 0}
    for rows in trajectory.values():
        for row in rows:
            counts[row["status"]] += 1
    return {"schema": 1, "layer_capture_status": "PASS",
            "selected_edge_attribution_status": "PASS",
            "forward_camera_status": "INCONCLUSIVE",
            "interpretation":
            "layer_mask_validated_retrospective_host_comparison_not_forward_camera_validation",
            "arcade_screen_window": [FIRST_SCREEN, LAST_SCREEN],
            "arcade_y_window": [FIRST_ROW, LAST_ROW], "counts": counts,
            "trajectory": trajectory, "selected_causal_rows": selected,
            "unique_selected_arcade_rows": len({(row["screen"], row["y"])
                                                 for row in selected}),
            "comparison_role_metrics": {case["id"]: case["role_metrics"]
                                        for case in comparison["cases"]},
            "calibration_sha256": digest(calibration_path),
            "cases_sha256": digest(cases_path),
            "layer_sha256": {str(screen): digest(
                trials[0] / f"layer-rows-{screen-1:04d}.csv")
                for screen in range(FIRST_SCREEN, LAST_SCREEN + 1)},
            "screen980_sha256": digest(trials[0] / "swap-screen-0980.png"),
            "replay_log_sha256": [digest(trial / "phase1b-input.log")
                                  for trial in trials]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("cases", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    result = audit(root, args.calibration, args.cases)
    output = root / "phase1b-road-only-contour.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("layer", result["layer_capture_status"],
          "forward camera", result["forward_camera_status"], result["counts"],
          "unique selected rows", result["unique_selected_arcade_rows"])
    print("private result:", output)


if __name__ == "__main__":
    main()
