#!/usr/bin/env python3
"""Audit private screen-981 Y-sprite source and fixed-packet host comparison."""

import argparse
import hashlib
import json
from pathlib import Path

from phase1b_calibrated_geometry import compare
from phase1b_mild_steer_width import scan
from phase1b_road_only_contour import edge_stage, load_layer
from phase1b_strip_rotation_prediction import affine
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import map_pixel, source_words


SLOTS = (0xA4A0, 0xA5D0, 0xA620)
ROWS = tuple(range(157, 164))
TRIAL_NAMES = tuple(f"phase1b-screen981-three-slot-native-r{i}"
                    for i in (1, 2, 3))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(rows, x, y):
    return bytes(rows[y][3*x:3*x+3]).hex()


def audit(root, calibration, case_file):
    baseline = root / "phase1b-screen981-native-baseline"
    old = root / "phase1b-layer980/baseline"
    trials = [root / name for name in TRIAL_NAMES]
    override = root / ("phase1b-right-search-980-A4A0-00190-only-"
                       "A4A0-A5D0-A620-source.bin")
    original = (baseline / "source-0980-ysprites.bin").read_bytes()
    hidden = override.read_bytes()
    assert len(original) == len(hidden) == 0x10000
    assert [i for i, (a, b) in enumerate(zip(original, hidden)) if a != b] == list(SLOTS)
    assert all(hidden[slot] == original[slot] | 0x10 for slot in SLOTS)
    assert original == (old / "source-0980-ysprites.bin").read_bytes()
    assert (baseline / "ybitmap-0980.raw").read_bytes() == (
        old / "ybitmap-0980.raw").read_bytes()
    for screen in range(960, 983):
        name = f"swap-screen-{screen:04d}.png"
        assert png_rows(baseline / name) == png_rows(old / name), screen

    screen = png_rows(baseline / "swap-screen-0981.png")
    detected = [row for row in scan(screen, 981) if row["y"] in ROWS]
    assert [row["y"] for row in detected] == list(ROWS)
    layer = load_layer(baseline / "layer-rows-0980.csv")
    transform = affine(baseline, "pre", 980)
    native, native_sha = source_words(baseline, 980)
    edges = []
    for row in detected:
        for side in ("left", "right"):
            x, y = row[side], row["y"]
            assert edge_stage(layer[y][x]) == "clear_rotation"
            sx, sy = map_pixel(transform, x, y)
            before = native[sy * 512 + sx]
            assert before != 0xffff
            edges.append({"y": y, "side": side, "x": x,
                          "native": [sx, sy], "native_before": before,
                          "rgb_before": rgb(screen, x, y)})
    assert len(edges) == 14

    replay_hashes = []
    for trial in trials:
        assert (trial / "source-0980-ysprites.bin").read_bytes() == original
        assert (trial / "source-0980-ysprites-after.bin").read_bytes() == hidden
        for frame in range(960, 981):
            name = f"swap-screen-{frame:04d}.png"
            assert png_rows(trial / name) == png_rows(baseline / name), (trial, frame)
        altered_screen = png_rows(trial / "swap-screen-0981.png")
        altered_native, _ = source_words(trial, 980)
        for edge in edges:
            sx, sy = edge["native"]
            assert altered_native[sy * 512 + sx] == 0xffff
            assert rgb(altered_screen, edge["x"], edge["y"]) != edge["rgb_before"]
        replay_hashes.append({"trial": str(trial),
                              "native980_sha256": digest(trial / "ybitmap-0980.raw"),
                              "screen981_sha256": digest(trial / "swap-screen-0981.png"),
                              "post_source_sha256": digest(trial / "source-0980-ysprites-after.bin"),
                              "log_sha256": digest(trial / "phase1b-input.log")})
    assert len({(item["native980_sha256"], item["screen981_sha256"],
                 item["post_source_sha256"]) for item in replay_hashes}) == 1

    result = compare(root, calibration, case_file)
    case, = result["cases"]
    assert case["screen_frame"] == 981
    assert case["camera_packet"] == [38, 0, 0, 4, 31]
    assert [row["arcade_y"] for row in case["rows"]] == list(ROWS)
    metric = case["role_metrics"]["check"]
    limits_met = (metric["mean_absolute_edge_error"] <= 2.0 and
                  metric["mean_absolute_width_error"] <= 2.0)
    return {"schema": 1, "source_attribution_status": "PASS",
            "retrospective_packet_limit_status": "PASS" if limits_met else "FAIL",
            "forward_adapter_status": "INCONCLUSIVE",
            "callback": 980, "composed_screen": 981,
            "changed_source_offsets": [f"{slot:04X}" for slot in SLOTS],
            "baseline_native_sha256": native_sha,
            "baseline_screen_sha256": digest(baseline / "swap-screen-0981.png"),
            "override_sha256": digest(override), "edges": edges,
            "replays": replay_hashes, "calibration_sha256": digest(calibration),
            "case_sha256": digest(case_file), "host_image_sha256": case["host_image_sha256"],
            "camera_packet": case["camera_packet"],
            "check_metrics": metric, "comparison_rows": case["rows"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("case_file", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    result = audit(root, args.calibration, args.case_file)
    output = root / "phase1b-screen981-source-score.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("source", result["source_attribution_status"],
          "fixed-packet limits", result["retrospective_packet_limit_status"],
          "forward adapter", result["forward_adapter_status"])
    print("metrics", result["check_metrics"])
    print("private result:", output)


if __name__ == "__main__":
    main()
