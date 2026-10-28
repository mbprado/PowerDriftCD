#!/usr/bin/env python3
"""Predict the arcade phase increment from earlier source and fraction state."""

import argparse
import hashlib
import json
import re
from pathlib import Path


FRAMES = list(range(961, 1000, 2))
PATTERNS = {
    "input": re.compile(r"POSITION_INCREMENT_INPUT pc=034490 old_source=([0-9A-F]{4}) source_delta=([0-9A-F]{4}) old_fraction=([0-9A-F]{8}) old_phase=([0-9A-F]{4})"),
    "source": re.compile(r"POSITION_INCREMENT_SOURCE pc=0344A0 source=([0-9A-F]{4})"),
    "output": re.compile(r"POSITION_INCREMENT_OUTPUT pc=034510 increment=([0-9A-F]{4}) preclear_sum=([0-9A-F]{8})"),
    "offset": re.compile(r"POSITION_INCREMENT_OFFSET pc=03454E phase=([0-9A-F]{4}) offset=([0-9A-F]{4})"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed16(value):
    return value - 0x10000 if value & 0x8000 else value


def trace(trial, phase, pulse):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert "STATE_LOAD,950," in control
    assert f"POSITION_INCREMENT_ARMED,{phase}" in control
    assert "POSITION_INCREMENT_CLEARED,1000" in control
    path = trial / "debug.log"
    data = path.read_text()
    needed = ("input", "source", "output", "offset") if phase == "both" else (
        ("input",) if phase == "input" else ("source", "output", "offset"))
    forbidden = ("source", "output", "offset") if phase == "input" else (
        ("input",) if phase == "output" else ())
    assert all("POSITION_INCREMENT_" + name.upper() not in data for name in forbidden)
    events = {name: [] for name in needed}
    marker = None
    for line in data.splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            marker = int(match[1])
        for name in needed:
            match = PATTERNS[name].search(line)
            if match:
                assert marker is not None
                events[name].append((marker, tuple(int(value, 16) for value in match.groups())))
    assert all([frame for frame, _ in events[name]] == FRAMES for name in needed)
    return events, sha256(path)


def predict(inputs):
    result = []
    for frame, (old_source, source_delta, old_fraction, old_phase) in inputs["input"]:
        source = (old_source + source_delta) & 0xffff
        # Main CPU sign-extends the word, shifts the long value left ten bits,
        # and adds it to the long accumulator. The following word read takes
        # the *high* half; clearing that half retains the fractional low half.
        summed = (old_fraction + (signed16(source) << 10)) & 0xffffffff
        increment = summed >> 16
        phase = (old_phase + increment) & 0x7ff
        result.append({"marker": frame, "old_source": f"{old_source:04X}",
                       "source_delta": f"{source_delta:04X}",
                       "old_fraction": f"{old_fraction:08X}",
                       "old_phase": f"{old_phase:04X}",
                       "source": f"{source:04X}", "sum": f"{summed:08X}",
                       "increment": f"{increment:04X}",
                       "phase": f"{phase:04X}", "offset": f"{2 * phase:04X}"})
    return result


def compare(rows, targets):
    errors = []
    for step, row in enumerate(rows):
        for kind, fields, order in (("source", ("source",), (0,)),
                                    ("output", ("increment", "sum"), (0, 1)),
                                    ("offset", ("phase", "offset"), (0, 1))):
            marker, values = targets[kind][step]
            assert marker == row["marker"]
            for field, index in zip(fields, order):
                value = values[index]
                if int(row[field], 16) != value:
                    errors.append({"marker": marker, "field": field,
                                   "predicted": row[field], "observed": f"{value:0{len(row[field])}X}"})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("development", "predict"):
        command = sub.add_parser(name)
        command.add_argument("trial", type=Path)
        if name == "predict":
            command.add_argument("output", type=Path)
        command.add_argument("--pulse", type=int, required=True)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("trial", type=Path)
    args = parser.parse_args()
    if args.command in ("development", "predict"):
        phase = "both" if args.command == "development" else "input"
        events, trace_sha = trace(args.trial, phase, args.pulse)
        rows = predict(events)
        if args.command == "development":
            errors = compare(rows, events)
            assert not errors, errors
            print("PASS development", len(rows), "updates, 5 fields each")
        else:
            assert not args.output.exists(), "predictions already frozen"
            record = {"schema": 1, "pulse": args.pulse,
                      "input_debug_sha256": trace_sha, "predictions": rows}
            args.output.write_text(json.dumps(record, indent=2) + "\n")
            print("FROZEN", len(rows), "predictions", sha256(args.output))
    else:
        frozen = json.loads(args.frozen.read_text())
        targets, trace_sha = trace(args.trial, "output", frozen["pulse"])
        rows = frozen["predictions"]
        assert len(rows) == len(FRAMES)
        errors = compare(rows, targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "pulse": frozen["pulse"],
                          "matched_fields": 5 * len(rows) - len(errors),
                          "total_fields": 5 * len(rows), "errors": errors,
                          "frozen_sha256": sha256(args.frozen),
                          "target_debug_sha256": trace_sha}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
