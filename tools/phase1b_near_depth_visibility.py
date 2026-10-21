#!/usr/bin/env python3
"""Select and check private, one-descriptor arcade depth visibility trials."""

import argparse
import csv
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

from phase1b_depth_sequence import bounds, debug_events, image_difference
from phase1b_far_depth import selected_record
from phase1b_matched_far_depth import assert_matched_positions


SIDES = ("center", "left", "right")
PROJECTIONS = (964, 968, 972)
INDICES = (1, 2, 3)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(root, side, projection, index):
    baseline = root / f"phase1b-depth-sequence-{side}"
    with (baseline / "geometry-samples.csv").open() as file:
        rows = {(int(row["frame"]), int(row["index"])): row
                for row in csv.DictReader(file)}
    row = rows[projection, index]
    assert row["depth"] == f"{0x3200 + index * 0x200:04X}"
    position = int(row["projected4"] + row["projected6"], 16)
    frame = projection + 2
    _, fields = selected_record(
        (baseline / f"shared-list-{frame:04d}.bin").read_bytes(), position)
    events = debug_events(root / f"phase1b-far-subx-{side}" / "debug.log")
    loads = [event for marker, event in events
             if marker == projection + 1 and event[:4] == fields
             and event[4] == 0x0C9800]
    assert len(loads) == 1, (side, projection, index, loads)
    slot = loads[0][5] - 0x180000 + 0x2000
    source = baseline / f"source-{frame:04d}-ysprites.bin"
    data = source.read_bytes()
    assert len(data) == 0x10000 and slot % 16 == 0
    descriptor = struct.unpack_from(">8H", data, slot)
    assert descriptor[0] & 0xD000 == 0 and data[slot] & 0x10 == 0
    return frame, slot, source, descriptor[3]


def prepare(root, sides):
    output = root / "phase1b-near-depth-inputs"
    output.mkdir(parents=True, exist_ok=True)
    plan = []
    for side in sides:
        for projection in PROJECTIONS:
            for index in INDICES:
                frame, slot, source, graphic = select(
                    root, side, projection, index)
                raw = bytearray(source.read_bytes())
                raw[slot] |= 0x10
                path = output / f"{side}-{frame:04d}-depth{index}.bin"
                path.write_bytes(raw)
                plan.append({"side": side, "projection_frame": projection,
                             "descriptor_frame": frame, "depth_index": index,
                             "slot": f"{slot:04X}", "graphic": f"{graphic:04X}",
                             "source_sha256": digest(source),
                             "override_sha256": digest(path)})
                print(f"{side} {projection} index {index}: descriptor "
                      f"{frame} +{slot:04X}, graphic {graphic:04X}")
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(f"private plan: {output / 'plan.json'}")


def analyze(root, sides):
    output = root / "phase1b-near-depth-inputs"
    plan = json.loads((output / "plan.json").read_text())
    results = []
    for item in plan:
        side, frame, index = (item["side"], item["descriptor_frame"],
                              item["depth_index"])
        if side not in sides:
            continue
        slot = int(item["slot"], 16)
        baseline = root / f"phase1b-depth-sequence-{side}"
        changed = root / f"phase1b-near-hidden-{side}-{frame}-depth{index}"
        input_path = output / f"{side}-{frame:04d}-depth{index}.bin"
        assert digest(input_path) == item["override_sha256"]
        original = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
        assert hashlib.sha256(original).hexdigest() == item["source_sha256"]
        after = (changed / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
        assert len(original) == len(after) == 0x10000
        assert [i for i, (a, b) in enumerate(zip(original, after)) if a != b] == [slot]
        assert after[slot] == original[slot] | 0x10
        for earlier in range(960, frame + 1):
            assert (baseline / f"swap-screen-{earlier:04d}.png").read_bytes() == (
                changed / f"swap-screen-{earlier:04d}.png").read_bytes()
        points = image_difference(
            baseline / f"swap-screen-{frame+1:04d}.png",
            changed / f"swap-screen-{frame+1:04d}.png")
        result = {"side": side, "descriptor_frame": frame,
                  "depth_index": index, "slot": item["slot"],
                  "graphic": item["graphic"], "changed_pixels": len(points),
                  "bbox": bounds(points) if points else None,
                  "screen_sha256": digest(changed / f"swap-screen-{frame+1:04d}.png")}
        results.append(result)
        print(f"{side} {frame} index {index}: {len(points)} pixels, "
              f"bbox={result['bbox']}")
    assert len(results) == len(sides) * len(PROJECTIONS) * len(INDICES)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"{len(results)} one-byte interventions and prior-screen controls verified")


def run_trial(root, item, mame, rompath, state, source, suffix=""):
    side, frame, index = (item["side"], item["descriptor_frame"],
                          item["depth_index"])
    trial = root / f"phase1b-near-hidden-{side}-{frame}-depth{index}{suffix}"
    trial.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().with_name("phase1b_mame_input.lua")
    env = os.environ.copy()
    env.update({"SDL_VIDEODRIVER": "dummy", "PDRIFT_SOURCE_DIR": ".",
                "PDRIFT_ROTATE_DIR": ".", "PDRIFT_SWAP_DIR": ".",
                "PDRIFT_SNAPSHOT_DIR": ".",
                "PDRIFT_SEQUENCE_END_FRAME": str(max(970, frame + 2)),
                "PDRIFT_STATE_LOAD": str(state.resolve()),
                "PDRIFT_SOURCE_OVERRIDE_FRAME": str(frame),
                "PDRIFT_SOURCE_OVERRIDE_RANGE": f"{item['slot']}:0010",
                "PDRIFT_SOURCE_OVERRIDE": str(source.resolve())})
    if side != "center":
        env["PDRIFT_STEER_PULSE"] = "64" if side == "left" else "192"
    cmd = [str(mame.resolve()), "pdrift", "-rompath", str(rompath.resolve()),
           "-noreadconfig", "-video", "none", "-sound", "none",
           "-nothrottle", "-seconds_to_run", "18", "-autoboot_script",
           str(script)]
    with (trial / "phase1b-input.log").open("w") as log:
        subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    print(f"{side} {frame} index {index}{suffix}: replay complete", flush=True)


def run(root, sides, mame, rompath, state):
    output = root / "phase1b-near-depth-inputs"
    plan = json.loads((output / "plan.json").read_text())
    for item in plan:
        side, frame, index = (item["side"], item["descriptor_frame"],
                              item["depth_index"])
        if side not in sides:
            continue
        source = (output / f"{side}-{frame:04d}-depth{index}.bin").resolve()
        assert digest(source) == item["override_sha256"]
        run_trial(root, item, mame, rompath, state, source)


def controls(root, mame, rompath, state):
    output = root / "phase1b-near-depth-inputs"
    plan = json.loads((output / "plan.json").read_text())
    item, = [row for row in plan if (row["side"], row["descriptor_frame"],
                                     row["depth_index"]) == ("center", 974, 1)]
    baseline = root / "phase1b-depth-sequence-center"
    source = baseline / "source-0974-ysprites.bin"
    assert digest(source) == item["source_sha256"]
    run_trial(root, item, mame, rompath, state, source, "-sham")
    source = output / "center-0974-depth1.bin"
    assert digest(source) == item["override_sha256"]
    run_trial(root, item, mame, rompath, state, source, "-repeat")


def analyze_controls(root):
    baseline = root / "phase1b-depth-sequence-center"
    hidden = root / "phase1b-near-hidden-center-974-depth1"
    sham = root / "phase1b-near-hidden-center-974-depth1-sham"
    repeat = root / "phase1b-near-hidden-center-974-depth1-repeat"
    assert (baseline / "source-0974-ysprites.bin").read_bytes() == (
        sham / "source-0974-ysprites-after.bin").read_bytes()
    assert (baseline / "swap-screen-0975.png").read_bytes() == (
        sham / "swap-screen-0975.png").read_bytes()
    for name in ("source-0974-ysprites-after.bin", "swap-screen-0975.png"):
        assert (hidden / name).read_bytes() == (repeat / name).read_bytes()
    print("center 974 depth 1 same-value control unchanged; hidden repeat "
          "source RAM and screen byte-identical")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("prepare", "run", "controls",
                                           "analyze"))
    parser.add_argument("--sides", nargs="+", choices=SIDES, default=SIDES)
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    assert_matched_positions(args.private_root)
    if args.action == "prepare":
        prepare(args.private_root, args.sides)
    elif args.action in ("run", "controls"):
        assert args.mame and args.rompath and args.state
        if args.action == "run":
            run(args.private_root.resolve(), args.sides, args.mame,
                args.rompath, args.state)
        else:
            controls(args.private_root.resolve(), args.mame, args.rompath,
                     args.state)
    else:
        analyze(args.private_root, args.sides)
        if tuple(args.sides) == SIDES:
            analyze_controls(args.private_root)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, IndexError,
            subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
