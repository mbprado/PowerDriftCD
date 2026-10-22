#!/usr/bin/env python3
"""Private affine landmark captures for two traced arcade depth strips."""

import argparse
import csv
import json
import os
import struct
from pathlib import Path

from phase1b_depth_sequence import image_difference
from phase1b_near_depth_visibility import digest, run_trial
from phase1b_projection_replay import hexfield, signed16
from phase1b_strip_rotation_prediction import affine, native_mask
from phase1b_ybitmap_map import map_pixel


SIDES = ("center", "left")
FRAMES = (970, 974)
DEPTHS = (1, 2)


def plan(root):
    rows = json.loads((root / "phase1b-near-depth-inputs/plan.json").read_text())
    return {(row["side"], row["descriptor_frame"], row["depth_index"]): row
            for row in rows}


def directory(root, side, frame, index, kind):
    return root / f"phase1b-near-hidden-{side}-{frame}-depth{index}-affine-{kind}"


def run(root, mame, rompath, state):
    items = plan(root)
    old = os.environ.get("PDRIFT_YBITMAP_DIR")
    os.environ["PDRIFT_YBITMAP_DIR"] = "."
    try:
        for side in SIDES:
            for frame in FRAMES:
                for index in DEPTHS:
                    item = items[side, frame, index]
                    baseline = (root / f"phase1b-depth-sequence-{side}" /
                                f"source-{frame:04d}-ysprites.bin")
                    hidden = (root / "phase1b-near-depth-inputs" /
                              f"{side}-{frame:04d}-depth{index}.bin")
                    assert digest(baseline) == item["source_sha256"]
                    assert digest(hidden) == item["override_sha256"]
                    for kind, source in (("baseline", baseline),
                                         ("hidden", hidden)):
                        trial = directory(root, side, frame, index, kind)
                        bitmap = trial / f"ybitmap-{frame:04d}.raw"
                        if bitmap.exists():
                            assert len(bitmap.read_bytes()) == 512 * 512 * 2
                            print(f"reuse {trial}", flush=True)
                        else:
                            run_trial(root, item, mame, rompath, state,
                                      source, f"-affine-{kind}")
                            assert len(bitmap.read_bytes()) == 512 * 512 * 2
    finally:
        if old is None:
            del os.environ["PDRIFT_YBITMAP_DIR"]
        else:
            os.environ["PDRIFT_YBITMAP_DIR"] = old


def mapped_pixels(mask, transform, landmark_row):
    full, landmark = set(), set()
    for y in range(224):
        for x in range(320):
            sx, sy = map_pixel(transform, x, y)
            if sy * 512 + sx in mask:
                full.add((x, y))
                if sy == landmark_row:
                    landmark.add((x, y))
    return full, landmark


def analyze(root):
    items = plan(root)
    matched = json.loads((root / "phase1b-projection-window/results.json").read_text())
    assert all(matched["exact_lookup_position"][str(frame - 2)]["left"]
               for frame in FRAMES)
    geometry = {}
    for side in SIDES:
        with (root / f"phase1b-depth-sequence-{side}/geometry-samples.csv").open() as file:
            geometry[side] = {(int(row["frame"]), int(row["index"])): row
                              for row in csv.DictReader(file)}
    results = []
    for side in SIDES:
        for frame in FRAMES:
            for index in DEPTHS:
                item = items[side, frame, index]
                baseline = directory(root, side, frame, index, "baseline")
                hidden = directory(root, side, frame, index, "hidden")
                previous = root / f"phase1b-near-hidden-{side}-{frame}-depth{index}"
                source = root / f"phase1b-depth-sequence-{side}"
                original = (source / f"source-{frame:04d}-ysprites.bin").read_bytes()
                a = (baseline / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
                b = (hidden / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
                slot = int(item["slot"], 16)
                assert a == original and len(a) == len(b) == 0x10000
                assert [i for i, (left, right) in enumerate(zip(a, b))
                        if left != right] == [slot]
                assert b[slot] == a[slot] | 0x10
                for replay in (baseline, hidden):
                    assert (replay / f"swap-screen-{frame:04d}.png").read_bytes() == (
                        source / f"swap-screen-{frame:04d}.png").read_bytes()
                visible_png = baseline / f"swap-screen-{frame+1:04d}.png"
                hidden_png = hidden / f"swap-screen-{frame+1:04d}.png"
                assert visible_png.read_bytes() == (
                    source / f"swap-screen-{frame+1:04d}.png").read_bytes()
                assert hidden_png.read_bytes() == (
                    previous / f"swap-screen-{frame+1:04d}.png").read_bytes()
                descriptor = struct.unpack_from(">8H", original, slot)
                assert f"{descriptor[3]:04X}" == item["graphic"]
                landmark_row = (descriptor[2] & 0xfff) - 0x600 + 3
                bitmap_a = baseline / f"ybitmap-{frame:04d}.raw"
                bitmap_b = hidden / f"ybitmap-{frame:04d}.raw"
                mask = native_mask(bitmap_a.read_bytes(), bitmap_b.read_bytes())
                native_edge = sorted(i % 512 for i in mask
                                     if i // 512 == landmark_row)
                assert native_edge
                actual = set(image_difference(visible_png, hidden_png))
                pre, landmark = mapped_pixels(
                    mask, affine(baseline, "pre", frame), landmark_row)
                post, _ = mapped_pixels(mask, affine(baseline, "post", frame),
                                        landmark_row)
                assert landmark and not (actual - pre)
                left_edge = min(x for x, _ in landmark)
                assert any(x == left_edge and (x, y) in actual
                           for x, y in landmark)
                row = geometry[side][frame - 2, index]
                result = {"side": side, "descriptor_frame": frame,
                          "projection_frame": frame - 2, "depth_index": index,
                          "depth": row["depth"],
                          "projected_x": signed16(hexfield(row, "projected4")),
                          "graphic": item["graphic"],
                          "direction_bits": descriptor[5] & 0x3000,
                          "native_landmark_y": landmark_row,
                          "native_landmark_span_x": [native_edge[0], native_edge[-1]],
                          "predicted_screen_left_x": left_edge,
                          "predicted_screen_span_x": [left_edge,
                                                      max(x for x, _ in landmark)],
                          "predicted_screen_span_y": [min(y for _, y in landmark),
                                                      max(y for _, y in landmark)],
                          "landmark_pixels": len(landmark),
                          "landmark_true_positive": len(landmark & actual),
                          "landmark_false_positive": len(landmark - actual),
                          "actual_changed_pixels": len(actual),
                          "pre_false_negative": len(actual - pre),
                          "pre_false_positive": len(pre - actual),
                          "post_false_negative": len(actual - post),
                          "baseline_screen_sha256": digest(visible_png),
                          "hidden_screen_sha256": digest(hidden_png),
                          "baseline_bitmap_sha256": digest(bitmap_a),
                          "hidden_bitmap_sha256": digest(bitmap_b),
                          "baseline_log_sha256": digest(
                              baseline / "phase1b-input.log"),
                          "hidden_log_sha256": digest(
                              hidden / "phase1b-input.log")}
                results.append(result)
                print(side, frame, index, "native row", landmark_row,
                      "screen edge", left_edge, "landmark TP/FP",
                      len(landmark & actual), len(landmark - actual),
                      "full misses pre/post", len(actual - pre),
                      len(actual - post))
    comparisons = []
    for frame in FRAMES:
        for index in DEPTHS:
            center = next(item for item in results if item["side"] == "center"
                          and item["descriptor_frame"] == frame
                          and item["depth_index"] == index)
            left = next(item for item in results if item["side"] == "left"
                        and item["descriptor_frame"] == frame
                        and item["depth_index"] == index)
            assert center["graphic"] == left["graphic"]
            assert center["direction_bits"] == left["direction_bits"]
            comparisons.append({"descriptor_frame": frame, "depth_index": index,
                                "depth": center["depth"],
                                "projected_x_delta": left["projected_x"]
                                - center["projected_x"],
                                "screen_left_edge_delta":
                                left["predicted_screen_left_x"]
                                - center["predicted_screen_left_x"]})
    training = [item for item in comparisons if item["descriptor_frame"] == 970]
    held = [item for item in comparisons if item["descriptor_frame"] == 974]
    gain = sum(item["projected_x_delta"] * item["screen_left_edge_delta"]
               for item in training) / sum(item["projected_x_delta"] ** 2
                                          for item in training)
    for item in held:
        item["screen_edge_prediction_from_training_gain"] = (
            gain * item["projected_x_delta"])
        item["prediction_error_pixels"] = (
            item["screen_left_edge_delta"]
            - item["screen_edge_prediction_from_training_gain"])
    output = root / "phase1b-affine-landmark-results.json"
    output.write_text(json.dumps({"cases": results, "comparisons": comparisons,
                                  "training_gain": gain}, indent=2) + "\n")
    print("four edge shifts:", comparisons)
    print("training gain", gain, "held-out errors",
          [item["prediction_error_pixels"] for item in held])
    print("private results:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("run", "analyze"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    if args.action == "run":
        assert args.mame and args.rompath and args.state
        run(args.private_root.resolve(), args.mame, args.rompath, args.state)
    else:
        analyze(args.private_root.resolve())
