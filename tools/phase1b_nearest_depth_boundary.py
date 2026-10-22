#!/usr/bin/env python3
"""Prepare and replay private one-byte hides for traced arcade depth $3200."""

import argparse
import json
from pathlib import Path

from phase1b_near_depth_visibility import digest, run_trial, select


SIDES = ("center", "left")
PROJECTIONS = (964, 968, 972)


def prepare(root):
    target = root / "phase1b-nearest-depth-inputs"
    target.mkdir(parents=True, exist_ok=True)
    plan = []
    for side in SIDES:
        for projection in PROJECTIONS:
            frame, slot, source, graphic = select(root, side, projection, 0)
            raw = bytearray(source.read_bytes())
            raw[slot] |= 0x10
            override = target / f"{side}-{frame:04d}-depth0.bin"
            override.write_bytes(raw)
            plan.append({"side": side, "projection_frame": projection,
                         "descriptor_frame": frame, "depth_index": 0,
                         "slot": f"{slot:04X}", "graphic": f"{graphic:04X}",
                         "source_sha256": digest(source),
                         "override_sha256": digest(override)})
            print(side, frame, "slot", f"{slot:04X}", "graphic", f"{graphic:04X}")
    (target / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")


def run(root, mame, rompath, state):
    plan = json.loads((root / "phase1b-nearest-depth-inputs/plan.json").read_text())
    assert len(plan) == len(SIDES) * len(PROJECTIONS)
    for item in plan:
        side, frame = item["side"], item["descriptor_frame"]
        override = root / "phase1b-nearest-depth-inputs" / \
            f"{side}-{frame:04d}-depth0.bin"
        assert digest(override) == item["override_sha256"]
        run_trial(root, item, mame, rompath, state, override)


def controls(root, mame, rompath, state):
    plan = json.loads((root / "phase1b-nearest-depth-inputs/plan.json").read_text())
    item, = [row for row in plan if (row["side"], row["descriptor_frame"]) ==
             ("center", 974)]
    baseline = root / "phase1b-depth-sequence-center/source-0974-ysprites.bin"
    override = root / "phase1b-nearest-depth-inputs/center-0974-depth0.bin"
    assert digest(baseline) == item["source_sha256"]
    assert digest(override) == item["override_sha256"]
    run_trial(root, item, mame, rompath, state, baseline, "-sham")
    run_trial(root, item, mame, rompath, state, override, "-repeat")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("prepare", "run", "controls"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if args.action == "prepare":
        prepare(root)
    elif args.action == "run":
        assert args.mame and args.rompath and args.state
        run(root, args.mame, args.rompath, args.state)
    else:
        assert args.mame and args.rompath and args.state
        controls(root, args.mame, args.rompath, args.state)
