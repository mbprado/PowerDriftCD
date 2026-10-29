#!/usr/bin/env python3
"""Audit frozen natural arcade phase predictions and the fixed road-edge check."""

import json
from pathlib import Path

from phase1b_calibrated_geometry import output_row
from phase1b_mild_steer_width import scan
from phase1b_position_increment_predict import compare, sha256, trace
from phase1b_state24_fraction_predict import compute
from phase1b_swap_compare import changed_pixels, png_rows


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "build/private"
CALIBRATION = ROOT / "docs/experiments/data/phase1b-road-calibration.json"
CALIBRATION_SHA256 = "e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23"
FROZEN_SHA256 = "8a03f91de7de3c9d0fe6649d5a19e0e6ffb18270847a172805c7c4ad03ff2c20"
SCREENS = (989, 990)
ROWS = range(153, 164)


def main():
    assert sha256(CALIBRATION) == CALIBRATION_SHA256
    calibration = json.loads(CALIBRATION.read_text())
    assert calibration["arcade_screen"] == [320, 224]
    assert calibration["output_image"] == [128, 64]
    frozen_path = PRIVATE / "phase1b-natural-phase56-frozen.json"
    assert sha256(frozen_path) == FROZEN_SHA256
    frozen = json.loads(frozen_path.read_text())
    assert frozen["pulse"] == 56
    source_log = PRIVATE / "phase1b-natural-phase56-input/debug.log"
    assert sha256(source_log) == frozen["input_debug_sha256"]
    assert compute(source_log) == frozen["predictions"]
    targets, target_sha = trace(PRIVATE / "phase1b-natural-phase56-output", "output", 56)
    errors = compare(frozen["predictions"], targets)
    assert not errors
    control = compute(PRIVATE / "phase1b-combined-dev204-input/debug.log")
    divergences = [(old["marker"], old["phase"], new["phase"])
                   for old, new in zip(control, frozen["predictions"])
                   if old["phase"] != new["phase"]]
    assert divergences[0] == (983, "01A6", "01A5")
    assert SCREENS[0] == divergences[0][0] + 6
    baseline = PRIVATE / "phase1b-natural-screen204"
    heldout = PRIVATE / "phase1b-natural-screen56"
    differences = {}
    for frame in range(960, 1001):
        name = f"swap-screen-{frame:04d}.png"
        differences[frame] = changed_pixels(png_rows(baseline / name),
                                            png_rows(heldout / name))
    first_visual_difference = next(frame for frame, count in differences.items() if count)
    assert first_visual_difference == 964 < divergences[0][0]
    checks = []
    for frame in SCREENS:
        name = f"swap-screen-{frame:04d}.png"
        before = [row for row in scan(png_rows(baseline / name), frame)
                  if row["y"] in ROWS]
        after = [row for row in scan(png_rows(heldout / name), frame)
                 if row["y"] in ROWS]
        assert not before and not after
        checks.append({"screen": frame, "control_edge_rows": len(before),
                       "heldout_edge_rows": len(after),
                       "changed_rgb_pixels": differences[frame],
                       "control_png_sha256": sha256(baseline / name),
                       "heldout_png_sha256": sha256(heldout / name)})
    result = {"source_revision": "c598682", "scalar_status": "PASS",
              "scalar_matched_fields": 100, "scalar_total_fields": 100,
              "visual_status": "INCONCLUSIVE",
              "visual_reason": "No fixed-rule road-edge rows at either nominated screen; visual divergence preceded phase divergence.",
              "first_phase_divergence": {"marker": divergences[0][0],
                                         "control": divergences[0][1],
                                         "heldout": divergences[0][2]},
              "first_visual_difference_screen": first_visual_difference,
              "fixed_arcade_y_rows": list(ROWS),
              "calibrated_output_rows": [output_row(y, calibration) for y in ROWS],
              "calibration_sha256": CALIBRATION_SHA256,
              "frozen_sha256": FROZEN_SHA256,
              "input_debug_sha256": sha256(source_log),
              "target_debug_sha256": target_sha,
              "screens": checks}
    output = PRIVATE / "phase1b-natural-phase-edge-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("scalar PASS 100/100; visual INCONCLUSIVE;", sha256(output))


if __name__ == "__main__":
    main()
