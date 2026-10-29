#!/usr/bin/env python3
"""Freeze matched-PC Y-Board projection divisor and guard predictions."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from phase1b_projection_replay import signed16, signed32


FRAMES = list(range(961, 1000, 2))
FIELDS = ("source16", "source18", "source1a", "global16", "global1c",
          "global1e", "global20", "coef1sin", "coef1cos", "coef2sin",
          "coef2cos")
INPUT = re.compile(r"PROJECTION_DIV_INPUT pc=033D98 " + " ".join(
    rf"{field}=([0-9A-F]{{4}})" for field in FIELDS))
OUTPUT = re.compile(r"PROJECTION_DIV_OUTPUT pc=033E00 d2=([0-9A-F]{4})")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(directory, phase, pulse):
    control_path = directory / "phase1b-input.log"
    control = control_path.read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert f"PROJECTION_DIV_ARMED,{phase},960" in control
    assert "PROJECTION_DIV_CLEARED,1000" in control
    assert "LUA ERROR" not in control
    path = directory / "debug.log"
    data = path.read_text(errors="replace")
    if phase == "input":
        assert "PROJECTION_DIV_OUTPUT" not in data
    else:
        assert "PROJECTION_DIV_INPUT" not in data
    rows = []
    accepted = []
    marker = None
    for line in data.splitlines():
        frame = re.search(r"PROJECTION_DIV_FRAME,(\d+)", line)
        if frame:
            marker = int(frame[1])
        match = (INPUT if phase == "input" else OUTPUT).search(line)
        if match:
            assert marker is not None
            rows.append((marker, tuple(int(x, 16) for x in match.groups())))
        if phase == "output" and "PROJECTION_DIV_ACCEPT pc=033E04" in line:
            assert marker is not None
            accepted.append(marker)
    assert [marker for marker, _ in rows] == FRAMES
    return rows, accepted, digest(path), digest(control_path)


def divisor(values):
    fields = dict(zip(FIELDS, values))
    get = lambda key: signed16(fields[key])
    x = signed16(get("source16") + get("global1c"))
    y = signed16(get("source18") + get("global1e"))
    z = signed16(get("source1a") + get("global20"))
    rotated_x = signed16(signed32(get("coef1sin") * x
                                  + get("coef1cos") * y) >> 9)
    depth_x = signed16(signed32(get("coef2sin") * rotated_x
                                + get("coef2cos") * z) >> 9)
    return signed16(get("global16") + depth_x)


def freeze(input_dir, frozen, pulse):
    assert not frozen.exists(), "prediction already frozen"
    inputs, _, debug_sha, control_sha = trace(input_dir, "input", pulse)
    predictions = []
    for frame, values in inputs:
        d2 = divisor(values)
        predictions.append({"marker": frame, "raw_divisor": f"{d2 & 0xFFFF:04X}",
                            "accept": d2 > 0})
    record = {"schema": 1, "pulse": pulse, "object": "0C1D00",
              "source_commit": "3bfa8c4", "input_debug_sha256": debug_sha,
              "input_control_sha256": control_sha, "predictions": predictions}
    frozen.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "FROZEN", "sha256": digest(frozen),
                      "accepted": sum(item["accept"] for item in predictions),
                      "rejected": sum(not item["accept"] for item in predictions)},
                     indent=2))


def validate(frozen, target):
    record = json.loads(frozen.read_text())
    assert record["schema"] == 1 and record["object"] == "0C1D00"
    outputs, accepted, debug_sha, control_sha = trace(
        target, "output", record["pulse"])
    errors = []
    for item, (marker, (observed,)) in zip(record["predictions"], outputs):
        if marker != item["marker"] or observed != int(item["raw_divisor"], 16):
            errors.append({"marker": marker, "field": "raw_divisor",
                           "predicted": item["raw_divisor"],
                           "observed": f"{observed:04X}"})
        if (marker in accepted) != item["accept"]:
            errors.append({"marker": marker, "field": "accept",
                           "predicted": item["accept"],
                           "observed": marker in accepted})
    result = {"status": "PASS" if not errors else "FAIL",
              "matched_fields": len(outputs) * 2 - len(errors),
              "total_fields": len(outputs) * 2, "errors": errors,
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
