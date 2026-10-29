#!/usr/bin/env python3
"""Freeze stateful object X/Y and copy-stage shared-list pair predictions."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from phase1b_projection_replay import project


FRAMES = list(range(961, 1000, 2))
FIELDS = ("source16", "source18", "source1a", "global16", "global18",
          "global1a", "global1c", "global1e", "global20", "coef1sin",
          "coef1cos", "coef2sin", "coef2cos", "screen_y_offset")
INPUT = re.compile(r"PROJECTION_STATEFUL_INPUT pc=033D98 " + " ".join(
    rf"{field}=([0-9A-F]{{4}})" for field in FIELDS))
OUTPUT = re.compile(r"PROJECTION_STATEFUL_OUTPUT pc=033E9A "
                    r"x=([0-9A-F]{4}) y=([0-9A-F]{4})")
COPY = re.compile(r"PROJECTION_STATEFUL_COPY pc=033E8E "
                  r"slot=([0-9A-F]{8}) x=([0-9A-F]{4}) y=([0-9A-F]{4}) "
                  r"oldx=([0-9A-F]{4}) oldy=([0-9A-F]{4}) "
                  r"listx=([0-9A-F]{4}) listy=([0-9A-F]{4}) "
                  r"listoldx=([0-9A-F]{4}) listoldy=([0-9A-F]{4})")
INITIAL = re.compile(r"PROJECTION_STATEFUL_INITIAL,960,([0-9A-F]{4}),"
                     r"([0-9A-F]{4})")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def control(directory, phase, pulse):
    path = directory / "phase1b-input.log"
    data = path.read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in data
    assert f"PROJECTION_STATEFUL_ARMED,{phase},960" in data
    assert "PROJECTION_STATEFUL_CLEARED,1000" in data
    assert "LUA ERROR" not in data
    return data, digest(path)


def events(path, phase):
    data = path.read_text(errors="replace")
    if phase == "input":
        assert "PROJECTION_STATEFUL_OUTPUT" not in data
        assert "PROJECTION_STATEFUL_COPY" not in data
    else:
        assert "PROJECTION_STATEFUL_INPUT" not in data
    rows = []
    copies = []
    frame = None
    for line in data.splitlines():
        found = re.search(r"PROJECTION_STATEFUL_FRAME,(\d+)", line)
        if found:
            frame = int(found[1])
        found = (INPUT if phase == "input" else OUTPUT).search(line)
        if found:
            assert frame is not None
            rows.append((frame, found.groups()))
        if phase == "output":
            found = COPY.search(line)
            if found:
                assert frame is not None
                copies.append((frame, found.groups()))
    assert [frame for frame, _ in rows] == FRAMES
    assert len(copies) == len({frame for frame, _ in copies})
    return rows, dict(copies), digest(path)


def freeze(input_dir, frozen, pulse):
    assert not frozen.exists(), "prediction already frozen"
    controls, control_sha = control(input_dir, "input", pulse)
    initial = INITIAL.findall(controls)
    assert len(initial) == 1
    old_x, old_y = (int(value, 16) for value in initial[0])
    rows, _, debug_sha = events(input_dir / "debug.log", "input")
    predictions = []
    for frame, values in rows:
        fields = dict(zip(FIELDS, values))
        prior_x, prior_y = old_x, old_y
        projected = project(fields, int(fields["global18"], 16))
        accepted = projected is not None
        if accepted:
            old_x, old_y = (value & 0xFFFF for value in projected)
        predictions.append({
            "marker": frame, "accepted": accepted,
            "x": f"{old_x:04X}", "y": f"{old_y:04X}",
            "copy_old_x": f"{prior_x:04X}" if accepted else None,
            "copy_old_y": f"{prior_y:04X}" if accepted else None,
        })
    record = {"schema": 1, "pulse": pulse, "object": "0C1D00",
              "source_commit": "2755692", "initial_x": initial[0][0],
              "initial_y": initial[0][1],
              "input_control_sha256": control_sha,
              "input_debug_sha256": debug_sha,
              "predictions": predictions}
    frozen.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "FROZEN", "sha256": digest(frozen),
                      "accepted": sum(row["accepted"] for row in predictions),
                      "rejected": sum(not row["accepted"] for row in predictions)},
                     indent=2))


def validate(frozen, target):
    record = json.loads(frozen.read_text())
    assert record["schema"] == 1 and record["object"] == "0C1D00"
    _, control_sha = control(target, "output", record["pulse"])
    rows, copies, debug_sha = events(target / "debug.log", "output")
    errors = []
    fields_compared = 0
    for prediction, (frame, (observed_x, observed_y)) in zip(
            record["predictions"], rows):
        assert frame == prediction["marker"]
        for name, observed in (("x", observed_x), ("y", observed_y)):
            fields_compared += 1
            if observed != prediction[name]:
                errors.append({"marker": frame, "field": name,
                               "predicted": prediction[name], "observed": observed})
        copy = copies.get(frame)
        fields_compared += 1
        if bool(copy) != prediction["accepted"]:
            errors.append({"marker": frame, "field": "copy_event",
                           "predicted": prediction["accepted"],
                           "observed": bool(copy)})
        if copy:
            slot, x, y, oldx, oldy, listx, listy, listoldx, listoldy = copy
            expected = (prediction["x"], prediction["y"],
                        prediction["copy_old_x"], prediction["copy_old_y"])
            for name, observed, wanted in zip(
                    ("copy_x", "copy_y", "copy_old_x", "copy_old_y",
                     "list_x", "list_y", "list_old_x", "list_old_y"),
                    (x, y, oldx, oldy, listx, listy, listoldx, listoldy),
                    expected + expected):
                fields_compared += 1
                if observed != wanted:
                    errors.append({"marker": frame, "field": name,
                                   "predicted": wanted, "observed": observed,
                                   "observed_slot": slot})
    result = {"status": "PASS" if not errors else "FAIL",
              "matched_fields": fields_compared - len(errors),
              "total_fields": fields_compared, "errors": errors,
              "observed_slots": sorted({row[0] for row in copies.values()}),
              "frozen_sha256": digest(frozen),
              "target_debug_sha256": debug_sha,
              "target_control_sha256": control_sha}
    print(json.dumps(result, indent=2))
    assert not errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    freeze_cmd = sub.add_parser("freeze")
    freeze_cmd.add_argument("input", type=Path)
    freeze_cmd.add_argument("frozen", type=Path)
    freeze_cmd.add_argument("--pulse", type=int, required=True)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.input, args.frozen, args.pulse)
    else:
        validate(args.frozen, args.target)


if __name__ == "__main__":
    main()
