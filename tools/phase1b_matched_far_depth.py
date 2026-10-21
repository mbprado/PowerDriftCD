#!/usr/bin/env python3
"""Prepare and verify private far-depth descriptor visibility at matched positions."""

import argparse
import csv
import hashlib
import json
import struct
import sys
from pathlib import Path

from phase1b_depth_sequence import bounds, debug_events, image_difference
from phase1b_far_depth import selected_record
from phase1b_transform_producer import load_events, value


SIDES = ("center", "left", "right")
PROJECTION_FRAMES = (964, 968, 972)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(root, side, projection_frame):
    baseline = root / f"phase1b-depth-sequence-{side}"
    with (baseline / "geometry-samples.csv").open() as file:
        rows = {(int(row["frame"]), int(row["index"])): row
                for row in csv.DictReader(file)}
    row = rows[projection_frame, 4]
    assert row["depth"] == "3A00"
    position = (int(row["projected4"], 16) << 16) | int(
        row["projected6"], 16)
    frame = projection_frame + 2
    raw = (baseline / f"shared-list-{frame:04d}.bin").read_bytes()
    _, fields = selected_record(raw, position)
    events = debug_events(root / f"phase1b-far-subx-{side}" / "debug.log")
    loads = [event for marker, event in events
             if marker == projection_frame + 1 and
             event[:4] == fields and event[4] == 0x0c9800]
    assert len(loads) == 1, (side, projection_frame, loads)
    slot = loads[0][5] - 0x180000 + 0x2000
    source = baseline / f"source-{frame:04d}-ysprites.bin"
    original = source.read_bytes()
    assert len(original) == 0x10000 and slot % 16 == 0
    descriptor = struct.unpack_from(">8H", original, slot)
    assert descriptor[0] & 0x1000 == 0, (side, frame, slot)
    return frame, slot, source, descriptor[3]


def assert_matched_positions(root):
    runs = {}
    for side in SIDES:
        path = root / f"phase1b-upstream-speed-{side}" / "debug.log"
        runs[side] = {marker: next(fields for kind, fields in events
                                   if kind == "ANGLE_SOURCE")
                      for marker, events in load_events(path).items()}
    for projection_frame in PROJECTION_FRAMES:
        marker = projection_frame + 1
        depths = [value(runs[side][marker], "road_depth") for side in SIDES]
        assert len(set(depths)) == 1, (marker, depths)
    print("3/3 selected epochs have identical exact lookup positions "
          "across center/left/right")


def prepare(root):
    output = root / "phase1b-matched-far-inputs"
    output.mkdir(parents=True, exist_ok=True)
    plan = []
    for side in SIDES:
        for projection_frame in PROJECTION_FRAMES:
            frame, slot, source, graphic = selected(root, side,
                                                    projection_frame)
            raw = bytearray(source.read_bytes())
            raw[slot] |= 0x10
            path = output / f"{side}-{frame:04d}.bin"
            path.write_bytes(raw)
            plan.append({"side": side, "projection_frame": projection_frame,
                         "descriptor_frame": frame, "slot": f"{slot:04X}",
                         "graphic": f"{graphic:04X}",
                         "source_sha256": sha256(source),
                         "override_sha256": sha256(path)})
            print(f"{side} projection {projection_frame} → descriptor {frame} "
                  f"slot {slot:04X}, graphic {graphic:04X}")
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(f"private override plan: {output / 'plan.json'}")


def analyze(root):
    plan = json.loads((root / "phase1b-matched-far-inputs" / "plan.json").read_text())
    assert len(plan) == 9
    results = []
    for item in plan:
        side, frame, slot = item["side"], item["descriptor_frame"], int(
            item["slot"], 16)
        baseline = root / f"phase1b-depth-sequence-{side}"
        changed = root / f"phase1b-matched-far-hidden-{side}-{frame}"
        input_path = root / "phase1b-matched-far-inputs" / f"{side}-{frame:04d}.bin"
        assert sha256(input_path) == item["override_sha256"]
        original = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
        after = (changed / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
        assert len(original) == len(after) == 0x10000
        assert [index for index, (a, b) in enumerate(zip(original, after))
                if a != b] == [slot], (side, frame)
        assert after[slot] == original[slot] | 0x10
        for earlier in range(960, frame + 1):
            assert (baseline / f"swap-screen-{earlier:04d}.png").read_bytes() == (
                changed / f"swap-screen-{earlier:04d}.png").read_bytes()
        points = image_difference(
            baseline / f"swap-screen-{frame+1:04d}.png",
            changed / f"swap-screen-{frame+1:04d}.png")
        result = {"side": side, "descriptor_frame": frame, "slot": f"{slot:04X}",
                  "changed_pixels": len(points), "bbox": bounds(points) if points else None,
                  "screen_sha256": sha256(changed / f"swap-screen-{frame+1:04d}.png")}
        results.append(result)
        print(f"{side} hide {frame}: {len(points)} screen pixels, "
              f"bbox={result['bbox']}")
    (root / "phase1b-matched-far-inputs" / "results.json").write_text(
        json.dumps(results, indent=2) + "\n")
    print("9/9 one-byte interventions and prior-screen controls verified")
    baseline = root / "phase1b-depth-sequence-center"
    hidden = root / "phase1b-matched-far-hidden-center-974"
    sham = root / "phase1b-matched-far-hidden-center-974-sham"
    repeat = root / "phase1b-matched-far-hidden-center-974-repeat"
    assert (baseline / "source-0974-ysprites.bin").read_bytes() == (
        sham / "source-0974-ysprites-after.bin").read_bytes()
    assert (baseline / "swap-screen-0975.png").read_bytes() == (
        sham / "swap-screen-0975.png").read_bytes()
    for name in ("source-0974-ysprites-after.bin", "swap-screen-0975.png"):
        assert (hidden / name).read_bytes() == (repeat / name).read_bytes()
    print("center 974 same-value control unchanged; hidden repeat byte-identical")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("prepare", "analyze"))
    args = parser.parse_args()
    assert_matched_positions(args.private_root)
    if args.action == "prepare":
        prepare(args.private_root)
    else:
        analyze(args.private_root)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, IndexError) as exc:
        sys.exit(str(exc))
