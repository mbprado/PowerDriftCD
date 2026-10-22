#!/usr/bin/env python3
"""Private causal right-extent check for adjacent arcade road strips."""

import argparse
import json
import os
from pathlib import Path

from phase1b_depth_sequence import image_difference
from phase1b_near_depth_visibility import digest, run_trial
from phase1b_road_edge_sample import SAND_RGB, boundary
from phase1b_strip_rotation_prediction import affine, native_mask, predict
from phase1b_swap_compare import png_rows


SIDES = ("center", "left")
FRAMES = (970, 974)
DEPTHS = (0, 1)


def plans(root):
    nearest = json.loads((root / "phase1b-nearest-depth-inputs/plan.json").read_text())
    other = json.loads((root / "phase1b-near-depth-inputs/plan.json").read_text())
    return {(item["side"], item["descriptor_frame"], item["depth_index"]): item
            for item in nearest + other}


def directory(root, side, frame, depth, kind):
    suffix = ("-right-" if depth == 0 else "-affine-") + kind
    return root / f"phase1b-near-hidden-{side}-{frame}-depth{depth}{suffix}"


def right_sand_boundary(row):
    pixels = [tuple(row[i:i + 3]) for i in range(0, len(row), 3)]
    if any(pixel != SAND_RGB for pixel in pixels[-16:]):
        return None
    for x in range(303, 127, -1):
        if all(pixels[x - offset] != SAND_RGB for offset in range(4)):
            return x
    return None


def run(root, mame, rompath, state):
    plan = plans(root)
    previous = os.environ.get("PDRIFT_YBITMAP_DIR")
    os.environ["PDRIFT_YBITMAP_DIR"] = "."
    try:
        for side in SIDES:
            for frame in FRAMES:
                item = plan[side, frame, 0]
                baseline = root / f"phase1b-depth-sequence-{side}" / \
                    f"source-{frame:04d}-ysprites.bin"
                hidden = root / "phase1b-nearest-depth-inputs" / \
                    f"{side}-{frame:04d}-depth0.bin"
                assert digest(baseline) == item["source_sha256"]
                assert digest(hidden) == item["override_sha256"]
                for kind, source in (("baseline", baseline), ("hidden", hidden)):
                    trial = directory(root, side, frame, 0, kind)
                    bitmap = trial / f"ybitmap-{frame:04d}.raw"
                    if bitmap.exists():
                        assert len(bitmap.read_bytes()) == 512 * 512 * 2
                        print("reuse", trial, flush=True)
                    else:
                        run_trial(root, item, mame, rompath, state,
                                  source, f"-right-{kind}")
                        assert len(bitmap.read_bytes()) == 512 * 512 * 2
    finally:
        if previous is None:
            del os.environ["PDRIFT_YBITMAP_DIR"]
        else:
            os.environ["PDRIFT_YBITMAP_DIR"] = previous


def analyze(root):
    plan = plans(root)
    bands = json.loads((root / "phase1b-causal-boundary-rows.json").read_text())
    band_by_key = {(item["side"], item["descriptor_frame"], item["depth_index"]): item
                   for item in bands["records"]}
    results = []
    for side in SIDES:
        for frame in FRAMES:
            source = root / f"phase1b-depth-sequence-{side}"
            for depth in DEPTHS:
                item = plan[side, frame, depth]
                baseline = directory(root, side, frame, depth, "baseline")
                hidden = directory(root, side, frame, depth, "hidden")
                original = source / f"source-{frame:04d}-ysprites.bin"
                override = (root / ("phase1b-nearest-depth-inputs" if depth == 0
                                    else "phase1b-near-depth-inputs") /
                            f"{side}-{frame:04d}-depth{depth}.bin")
                assert digest(original) == item["source_sha256"]
                assert digest(override) == item["override_sha256"]
                assert (baseline / f"source-{frame:04d}-ysprites-after.bin").read_bytes() == (
                    original.read_bytes())
                assert (hidden / f"source-{frame:04d}-ysprites-after.bin").read_bytes() == (
                    override.read_bytes())
                prior = f"swap-screen-{frame:04d}.png"
                current = f"swap-screen-{frame+1:04d}.png"
                for trial in (baseline, hidden):
                    assert (trial / prior).read_bytes() == (source / prior).read_bytes()
                assert (baseline / current).read_bytes() == (source / current).read_bytes()
                original_hidden = root / f"phase1b-near-hidden-{side}-{frame}-depth{depth}"
                assert (hidden / current).read_bytes() == (
                    original_hidden / current).read_bytes()
                bitmap_a = baseline / f"ybitmap-{frame:04d}.raw"
                bitmap_b = hidden / f"ybitmap-{frame:04d}.raw"
                mask = native_mask(bitmap_a.read_bytes(), bitmap_b.read_bytes())
                predicted = predict(mask, affine(baseline, "pre", frame))
                actual = set(image_difference(baseline / current, hidden / current))
                assert actual and not (actual - predicted)
                screen_rows = png_rows(baseline / current)
                edge_rows = {entry["y"] for entry in
                             band_by_key[side, frame, depth]["boundary_changes"]}
                row_results = []
                for y in sorted(edge_rows):
                    native_x = [x for x, yy in predicted if yy == y]
                    visible_x = [x for x, yy in actual if yy == y]
                    assert native_x and visible_x
                    right_sand_x = right_sand_boundary(screen_rows[y])
                    left_sand_x = boundary(screen_rows[y], y)[0]
                    row_results.append({"y": y,
                                        "mapped_right_x": max(native_x),
                                        "visible_right_x": max(visible_x),
                                        "mapped_left_x": min(native_x),
                                        "visible_left_x": min(visible_x),
                                        "mapped_pixels": len(native_x),
                                        "visible_pixels": len(visible_x),
                                        "right_clipped": max(native_x) == 319,
                                        "right_sand_x": right_sand_x,
                                        "right_extent_is_sand_boundary":
                                            right_sand_x == max(visible_x)
                                            if right_sand_x is not None else False,
                                        "sand_to_sand_width":
                                            right_sand_x - left_sand_x + 1
                                            if right_sand_x is not None else None})
                result = {"side": side, "descriptor_frame": frame,
                          "depth_index": depth, "graphic": item["graphic"],
                          "baseline_bitmap_sha256": digest(bitmap_a),
                          "hidden_bitmap_sha256": digest(bitmap_b),
                          "baseline_screen_sha256": digest(baseline / current),
                          "hidden_screen_sha256": digest(hidden / current),
                          "mapped_pixels": len(predicted),
                          "visible_pixels": len(actual),
                          "mapped_false_positive": len(predicted - actual),
                          "mapped_false_negative": len(actual - predicted),
                          "edge_rows": row_results}
                results.append(result)
                print(side, frame, depth, "mapped/visible", len(predicted),
                      len(actual), "edge rows", len(row_results),
                      "clipped", sum(r["right_clipped"] for r in row_results))
    output = root / "phase1b-right-extent.json"
    output.write_text(json.dumps({"cases": results}, indent=2) + "\n")
    print("private result:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("run", "analyze"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if args.action == "run":
        assert args.mame and args.rompath and args.state
        run(root, args.mame, args.rompath, args.state)
    else:
        analyze(root)
