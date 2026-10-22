#!/usr/bin/env python3
"""Audit source-independent arcade projection samples through a longer window."""

import argparse
import csv
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

from phase1b_depth_sequence import debug_events
from phase1b_transform_producer import load_events, value


SIDES = ("center", "left", "right")
PROJECTIONS = tuple(range(960, 997, 4))
DEPTHS = tuple(range(5))


def signed16(word):
    return word - 0x10000 if word & 0x8000 else word


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def y_sprite_matches(raw, position):
    assert len(raw) == 0x2000
    matches = []
    for offset in range(0, len(raw), 16):
        fields = struct.unpack_from(">4I", raw, offset)
        if fields[1] == position and ((fields[0] >> 16) & 0xff00) == 0x8b00:
            matches.append((offset, fields))
    return matches


def input_data(root):
    runs = {}
    for side in SIDES:
        baseline = root / f"phase1b-depth-sequence-{side}"
        with (baseline / "geometry-samples.csv").open() as file:
            rows = {(int(row["frame"]), int(row["index"])): row
                    for row in csv.DictReader(file)}
        assert len(rows) == 41 * 12
        events = debug_events(root / f"phase1b-far-subx-{side}" / "debug.log")
        trace = load_events(root / f"phase1b-upstream-speed-{side}" / "debug.log")
        angle = {frame: next(fields for kind, fields in items
                             if kind == "ANGLE_SOURCE")
                 for frame, items in trace.items()}
        runs[side] = {"baseline": baseline, "rows": rows,
                      "events": events, "angle": angle}
    return runs


def analyze(root):
    runs = input_data(root)
    for index in DEPTHS:
        tuples = {tuple(runs[side]["rows"][frame, index][key]
                        for key in ("depth", "table", "sample0",
                                    "sample1", "sample2"))
                  for side in SIDES for frame in range(960, 1001)}
        assert len(tuples) == 1, (index, tuples)

    position_match = {}
    for projection in PROJECTIONS:
        marker = projection + 1
        positions = {side: value(runs[side]["angle"][marker], "road_depth")
                     for side in SIDES}
        position_match[projection] = {
            "left": positions["left"] == positions["center"],
            "right": positions["right"] == positions["center"]}
    records = []
    for side in SIDES:
        run = runs[side]
        for projection in PROJECTIONS:
            frame = projection + 2
            shared = (run["baseline"] /
                      f"shared-list-{frame:04d}.bin").read_bytes()
            sprite = (run["baseline"] /
                      f"source-{frame:04d}-ysprites.bin").read_bytes()
            assert len(sprite) == 0x10000
            for index in DEPTHS:
                geometry = run["rows"][projection, index]
                assert int(geometry["depth"], 16) == 0x3200 + 0x200 * index
                projected_x = signed16(int(geometry["projected4"], 16))
                projected_y = signed16(int(geometry["projected6"], 16))
                position = (int(geometry["projected4"], 16) << 16 |
                            int(geometry["projected6"], 16))
                matches = y_sprite_matches(shared, position)
                assert len(matches) <= 1, (side, projection, index, matches)
                record = {"side": side, "projection_frame": projection,
                          "depth_index": index, "depth": geometry["depth"],
                          "projected_x": projected_x,
                          "projected_y": projected_y,
                          "lookup_position": value(
                              run["angle"][projection + 1], "road_depth"),
                          "matched_position_vs_center": (
                              side == "center" or
                              position_match[projection][side]),
                          "record_status": "absent"}
                if matches:
                    list_offset, fields = matches[0]
                    loads = [event for marker, event in run["events"]
                             if marker == projection + 1 and
                             event[:4] == fields and event[4] == 0x0c9800]
                    assert len(loads) == 1, (side, projection, index, loads)
                    slot = loads[0][5] - 0x180000 + 0x2000
                    assert 0 <= slot <= len(sprite) - 16 and slot % 16 == 0
                    descriptor = struct.unpack_from(">8H", sprite, slot)
                    assert descriptor[0] & 0xd000 == 0
                    record.update({"record_status": "traced",
                                   "list_offset": list_offset,
                                   "descriptor_slot": slot,
                                   "descriptor_x": (descriptor[1] & 0x0fff) - 0x600,
                                   "descriptor_y": (descriptor[2] & 0x0fff) - 0x600,
                                   "descriptor_height": descriptor[4],
                                   "descriptor_x_direction": (
                                       1 if descriptor[5] & 0x1000 else -1),
                                   "descriptor_zoom": descriptor[5] & 0x07ff,
                                   "graphic_word": f"{descriptor[3]:04X}"})
                records.append(record)

    expected = len(SIDES) * len(PROJECTIONS) * len(DEPTHS)
    assert len(records) == expected
    counts = Counter((item["side"], item["depth_index"])
                     for item in records if item["record_status"] == "traced")
    assert all(counts[side, index] == 10 for side in SIDES for index in (3, 4))
    assert all(counts[side, 2] == 9 for side in SIDES)
    for side in SIDES:
        print(f"{side}: traceable epochs by depth 0–4: "
              + "/".join(str(counts[side, index]) for index in DEPTHS))
    all_matched = [projection for projection in PROJECTIONS
                   if all(position_match[projection].values())]
    assert all_matched == [960, 964, 968, 972]
    print(f"all-steering exact lookup position: {all_matched}; "
          "later trajectories are compared only within each run")
    for index in (2, 3, 4):
        for side in SIDES:
            subset = [item for item in records if item["side"] == side
                      and item["depth_index"] == index]
            xs = [item["projected_x"] for item in subset]
            ys = [item["projected_y"] for item in subset]
            print(f"depth {index} {side}: projected X {xs[0]}→{xs[-1]}, "
                  f"range {min(xs)}..{max(xs)}; Y {ys[0]}→{ys[-1]}, "
                  f"range {min(ys)}..{max(ys)}")
    output = root / "phase1b-projection-window"
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps({
        "baseline_sha256": {side: sha256(
            runs[side]["baseline"] / "geometry-samples.csv")
            for side in SIDES},
        "exact_lookup_position": position_match,
        "records": records}, indent=2) + "\n")
    print(f"{sum(counts.values())}/{expected} projection/list/sub-CPU/"
          "descriptor identities traced; private results recorded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    analyze(args.private_root.resolve())


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, IndexError,
            StopIteration) as exc:
        sys.exit(str(exc))
