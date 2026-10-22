#!/usr/bin/env python3
"""Predict private arcade strip screen changes from natural descriptor and rotation."""

import argparse
import json
import os
import struct
import sys
from pathlib import Path

from phase1b_depth_sequence import bounds, image_difference
from phase1b_fixed_graphic_strip import row_stats
from phase1b_near_depth_visibility import digest, run_trial, select
from phase1b_swap_compare import read_capture
from phase1b_ybitmap_map import map_pixel, signed32


SIDES = ("center", "left", "right")
FRAMES = (966, 970)
SAMPLE_SCREEN_ROW = {966: 143, 970: 150}


def native_mask(first, second):
    assert len(first) == len(second) == 512 * 512 * 2
    return {index for index in range(512 * 512)
            if first[2*index:2*index+2] != second[2*index:2*index+2]}


def affine(directory, kind, frame):
    words = struct.unpack(">16H", read_capture(directory, kind, frame))
    return tuple(signed32(words[i], words[i + 1]) for i in range(0, 12, 2))


def predict(mask, transform):
    predicted = set()
    for y in range(224):
        for x in range(320):
            sx, sy = map_pixel(transform, x, y)
            if sy * 512 + sx in mask:
                predicted.add((x, y))
    return predicted


def points(mask):
    return [(index % 512, index // 512) for index in mask]


def plan_item(root, side, frame):
    plan = json.loads((root / "phase1b-near-depth-inputs" / "plan.json").read_text())
    item, = [row for row in plan if row["side"] == side
             and row["descriptor_frame"] == frame and row["depth_index"] == 1]
    return item


def run(root, mame, rompath, state):
    os.environ["PDRIFT_YBITMAP_DIR"] = "."
    for frame in FRAMES:
        for side in SIDES:
            item = plan_item(root, side, frame)
            source = (root / f"phase1b-depth-sequence-{side}" /
                      f"source-{frame:04d}-ysprites.bin")
            hidden = (root / "phase1b-near-depth-inputs" /
                      f"{side}-{frame:04d}-depth1.bin")
            assert digest(source) == item["source_sha256"]
            assert digest(hidden) == item["override_sha256"]
            run_trial(root, item, mame, rompath, state, source,
                      "-native-baseline")
            run_trial(root, item, mame, rompath, state, hidden)


def analyze(root):
    results = []
    for frame in FRAMES:
        for side in SIDES:
            item = plan_item(root, side, frame)
            _, slot, source, graphic = select(root, side, frame - 2, 1)
            assert slot == int(item["slot"], 16)
            descriptor = struct.unpack_from(">8H", source.read_bytes(), slot)
            xpos = (descriptor[1] & 0x0fff) - 0x600
            ypos = (descriptor[2] & 0x0fff) - 0x600
            xdelta = 1 if descriptor[5] & 0x1000 else -1
            ydelta = 1 if descriptor[5] & 0x4000 else -1
            height = descriptor[4]
            baseline = root / f"phase1b-depth-sequence-{side}"
            visible = root / (f"phase1b-near-hidden-{side}-{frame}-"
                              "depth1-native-baseline")
            hidden = root / f"phase1b-near-hidden-{side}-{frame}-depth1"
            assert (visible / f"source-{frame:04d}-ysprites-after.bin").read_bytes() == (
                source.read_bytes())
            assert (visible / f"swap-screen-{frame+1:04d}.png").read_bytes() == (
                baseline / f"swap-screen-{frame+1:04d}.png").read_bytes()
            original = source.read_bytes()
            changed = (hidden / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
            assert [i for i, (a, b) in enumerate(zip(original, changed))
                    if a != b] == [slot]
            assert changed[slot] == original[slot] | 0x10
            for earlier in range(960, frame + 1):
                assert (visible / f"swap-screen-{earlier:04d}.png").read_bytes() == (
                    hidden / f"swap-screen-{earlier:04d}.png").read_bytes()
            a = (visible / f"ybitmap-{frame:04d}.raw").read_bytes()
            b = (hidden / f"ybitmap-{frame:04d}.raw").read_bytes()
            mask = native_mask(a, b)
            native = points(mask)
            assert mask and all((x - xpos) * xdelta >= 0 for x, _ in native)
            assert all((y - ypos) * ydelta >= 0 and
                       (y - ypos) * ydelta < height for _, y in native)
            screen = set(image_difference(
                visible / f"swap-screen-{frame+1:04d}.png",
                hidden / f"swap-screen-{frame+1:04d}.png"))
            predictions = {}
            for kind in ("pre", "post"):
                predicted = predict(mask, affine(visible, kind, frame))
                predictions[kind] = {
                    "predicted_pixels": len(predicted),
                    "true_positive": len(predicted & screen),
                    "false_positive": len(predicted - screen),
                    "false_negative": len(screen - predicted)}
            result = {"side": side, "descriptor_frame": frame,
                      "graphic": f"{graphic:04X}", "x_origin": xpos,
                      "y_origin": ypos, "x_direction": xdelta,
                      "y_direction": ydelta, "height": height,
                      "native_pixels": len(mask), "native_bbox": bounds(native),
                      "native_row": row_stats(native, ypos + 3 * ydelta),
                      "screen_pixels": len(screen),
                      "screen_bbox": bounds(screen),
                      "screen_row": row_stats(screen, SAMPLE_SCREEN_ROW[frame]),
                      "predictions": predictions,
                      "source_sha256": digest(source),
                      "native_sha256": digest(visible / f"ybitmap-{frame:04d}.raw"),
                      "screen_sha256": digest(
                          visible / f"swap-screen-{frame+1:04d}.png")}
            results.append(result)
            print(f"{side} {frame}: origin=({xpos},{ypos}), "
                  f"direction=({xdelta},{ydelta}), native={len(mask)}, "
                  f"screen={len(screen)}, pre={predictions['pre']}, "
                  f"post={predictions['post']}")
    output = root / "phase1b-strip-rotation-prediction"
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")


def main():
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


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, IndexError) as exc:
        sys.exit(str(exc))
