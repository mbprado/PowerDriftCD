#!/usr/bin/env python3
"""Carry the modeled arcade $24 source into the fractional phase accumulator."""

import argparse
import json
import re
from pathlib import Path

from phase1b_position_increment_predict import compare, sha256, signed16, trace
from phase1b_state24_source_predict import predict as predict_source
from phase1b_state7a_predict import events


INITIAL = re.compile(r"STATE24_SOURCE pc=0343C4 .* oldglobal=([0-9A-F]{4}) "
                     r"oldfraction=([0-9A-F]{8}) oldphase=([0-9A-F]{4})")


def compute(input_log):
    source = predict_source(input_log)
    initial = events(input_log, INITIAL)
    assert len(initial) == len(source["predictions"]) == 20
    assert initial[0][1][0] == source["initial_global"]
    fraction = initial[0][1][1]
    phase = initial[0][1][2]
    assert fraction < 0x10000
    rows = []
    for item in source["predictions"]:
        value = item["predicted_new24"]
        summed = (fraction + (signed16(value) << 10)) & 0xffffffff
        increment = summed >> 16
        phase = (phase + increment) & 0x7ff
        fraction = summed & 0xffff
        rows.append({"marker": item["frame"], "path": item["path"],
                     "source": f"{value:04X}", "sum": f"{summed:08X}",
                     "increment": f"{increment:04X}",
                     "phase": f"{phase:04X}", "offset": f"{2 * phase:04X}"})
    return rows


def input_log(trial, pulse):
    control = (trial / "phase1b-upstream.log").read_text(errors="replace")
    assert f"UPSTREAM_ARMED,state24_fraction_inputs,960,pulse={pulse}" in control
    assert "UPSTREAM_CLEARED,1000" in control
    return trial / "debug.log"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("development", "predict"):
        command = sub.add_parser(name)
        command.add_argument("trial", type=Path)
        if name == "development":
            command.add_argument("target", type=Path)
        if name == "predict":
            command.add_argument("output", type=Path)
        command.add_argument("--pulse", type=int, required=True)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("input_trial", type=Path)
    check.add_argument("target_trial", type=Path)
    args = parser.parse_args()
    if args.command in ("development", "predict"):
        path = input_log(args.trial, args.pulse)
        rows = compute(path)
        if args.command == "development":
            targets, _ = trace(args.target, "output", args.pulse)
            errors = compare(rows, targets)
            assert not errors, errors
            print("PASS development", len(rows), "updates, 5 fields each")
        else:
            assert not args.output.exists(), "predictions already frozen"
            record = {"schema": 1, "pulse": args.pulse,
                      "input_debug_sha256": sha256(path), "predictions": rows}
            args.output.write_text(json.dumps(record, indent=2) + "\n")
            print("FROZEN", len(rows), "predictions", sha256(args.output))
    else:
        record = json.loads(args.frozen.read_text())
        path = input_log(args.input_trial, record["pulse"])
        assert sha256(path) == record["input_debug_sha256"]
        assert compute(path) == record["predictions"]
        targets, target_sha = trace(args.target_trial, "output", record["pulse"])
        rows = record["predictions"]
        assert len(rows) == 20
        errors = compare(rows, targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "pulse": record["pulse"],
                          "matched_fields": 5 * len(rows) - len(errors),
                          "total_fields": 5 * len(rows), "errors": errors,
                          "frozen_sha256": sha256(args.frozen),
                          "target_debug_sha256": target_sha}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
