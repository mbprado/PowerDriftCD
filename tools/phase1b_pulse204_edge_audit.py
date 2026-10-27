#!/usr/bin/env python3
"""Audit two private pulse-204 Y-sprite interventions without fitting a camera."""

import hashlib
import json
from pathlib import Path

from phase1b_calibrated_geometry import output_row, target_bounds
from phase1b_mild_steer_width import scan
from phase1b_road_only_contour import edge_stage, load_layer
from phase1b_swap_compare import png_rows


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(root, baseline, name, callback, expected_slots, calibration):
    trial = root / name
    source = baseline / f"source-{callback:04d}-ysprites.bin"
    before_source = source.read_bytes()
    override = root / f"{name}-source.bin"
    after_source = (trial / f"source-{callback:04d}-ysprites-after.bin").read_bytes()
    assert len(before_source) == len(after_source) == 0x10000
    assert after_source == override.read_bytes()
    changed_slots = [i for i, (a, b) in enumerate(zip(before_source, after_source))
                     if a != b]
    assert changed_slots == expected_slots
    assert all(slot % 16 == 0 and after_source[slot] == before_source[slot] | 0x10
               for slot in changed_slots)
    assert (trial / f"source-{callback:04d}-ysprites.bin").read_bytes() == before_source
    assert all(png_rows(baseline / f"swap-screen-{frame:04d}.png") ==
               png_rows(trial / f"swap-screen-{frame:04d}.png")
               for frame in range(960, callback + 1))

    screen = callback + 1
    original = png_rows(baseline / f"swap-screen-{screen:04d}.png")
    altered = png_rows(trial / f"swap-screen-{screen:04d}.png")
    layer = load_layer(baseline / f"layer-rows-{callback:04d}.csv")
    rows = []
    for item in scan(original, screen):
        y = item["y"]
        if not 153 <= y <= 163:
            continue
        sides = {}
        for side in ("left", "right"):
            x = item[side]
            sides[side] = {
                "changed": original[y][3*x:3*x+3] != altered[y][3*x:3*x+3],
                "layer": edge_stage(layer[y][x]),
            }
        rows.append({"y": y, "left": item["left"], "right": item["right"],
                     "output_row": output_row(y, calibration),
                     "calibrated_target": list(target_bounds(
                         item["left"], item["right"], calibration)),
                     "sides": sides})
    changed_rgb_bytes = sum(a != b for old, new in zip(original, altered)
                            for a, b in zip(old, new))
    accepted = [row for row in rows if all(
        row["sides"][side]["changed"] and
        row["sides"][side]["layer"] == "clear_rotation"
        for side in ("left", "right"))]
    native = baseline / f"ybitmap-{callback:04d}.raw"
    return {"callback": callback, "screen": screen, "trial": name,
            "changed_descriptor_count": len(changed_slots),
            "prior_screens_equal": True, "changed_rgb_bytes": changed_rgb_bytes,
            "detected_rows_153_163": rows, "clear_two_sided_rows": len(accepted),
            "native_bitmap_status": "CAPTURED" if native.is_file() else "NOT_CAPTURED",
            "baseline_source_sha256": digest(source),
            "override_sha256": digest(override),
            "baseline_screen_sha256": digest(baseline / f"swap-screen-{screen:04d}.png"),
            "trial_screen_sha256": digest(trial / f"swap-screen-{screen:04d}.png"),
            "baseline_log_sha256": digest(baseline / "phase1b-input.log"),
            "trial_log_sha256": digest(trial / "phase1b-input.log")}


def main():
    root = Path(__file__).resolve().parents[1] / "build/private"
    baseline = root / "phase1b-pulse204-screen981-baseline"
    calibration_path = Path(__file__).resolve().parents[1] / (
        "docs/experiments/data/phase1b-road-calibration.json")
    calibration = json.loads(calibration_path.read_text())
    early_source = (baseline / "source-0967-ysprites.bin").read_bytes()
    early_slots = [i for i in range(0, 0x10000, 16) if not early_source[i] & 0x10]
    results = [one(root, baseline, "phase1b-pulse204-screen981-three-slot", 980,
                   [0xA4A0, 0xA5D0, 0xA620], calibration),
               one(root, baseline, "phase1b-pulse204-screen968-broad", 967,
                   early_slots, calibration)]
    result = {"schema": 1, "pulse": 204,
              "calibration_sha256": digest(calibration_path),
              "cases": results,
              "visual_adapter_status": "INCONCLUSIVE",
              "reason": "no supported state-to-five-word mapping or native screen-968 bitmap"}
    path = root / "phase1b-pulse204-edge-audit.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    for case in results:
        print(case["screen"], "rows", len(case["detected_rows_153_163"]),
              "clear two-sided", case["clear_two_sided_rows"],
              "native", case["native_bitmap_status"])
    print("visual adapter", result["visual_adapter_status"], path)


if __name__ == "__main__":
    main()
