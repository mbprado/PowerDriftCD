#!/usr/bin/env python3
"""Predict one Y-Board position adjustment from pre-result multiplier inputs."""

import argparse
import hashlib
import json
import re
from pathlib import Path


INPUT = re.compile(r"POSITION_MATH_INPUT pc=034C1C a5=0C0840 a6=080000 "
                   r"base=([0-9A-F]{4}) operand=([0-9A-F]{4}) "
                   r"coefficient=([0-9A-F]{4})")
OUTPUT = re.compile(r"POSITION_MATH_OUTPUT pc=034C38 a5=0C0840 "
                    r"adjusted=([0-9A-F]{4})")
MARKER = re.compile(r"SEQUENCE_FRAME,(\d+)")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed16(word):
    return word - 0x10000 if word & 0x8000 else word


def entries(trial, kind, pulse):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert "STATE_LOAD,950," in control
    assert f"POSITION_MATH_ARMED,{kind}" in control
    assert "POSITION_MATH_CLEARED,1000" in control
    debug_path = trial / "debug.log"
    debug = debug_path.read_text()
    assert ("POSITION_MATH_OUTPUT" not in debug if kind == "input" else True)
    assert ("POSITION_MATH_INPUT" not in debug if kind == "output" else True)
    marker = None
    collected = []
    for line in debug.splitlines():
        frame = MARKER.search(line)
        if frame:
            marker = int(frame[1])
        event = INPUT.search(line) if kind == "input" else OUTPUT.search(line)
        if event:
            assert marker is not None
            collected.append((marker, tuple(int(x, 16) for x in event.groups())))
    assert [frame for frame, _ in collected] == list(range(961, 1000, 2))
    return collected, digest(debug_path)


def predicted(inputs):
    result = []
    for frame, (base, operand, coefficient) in inputs:
        product = signed16(operand) * signed16(coefficient)
        delta = product >> 9
        result.append({"marker": frame, "base": f"{base:04X}",
                       "operand": f"{operand:04X}",
                       "coefficient": f"{coefficient:04X}",
                       "delta": f"{delta & 0xffff:04X}",
                       "predicted": f"{(base + delta) & 0xffff:04X}"})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    dev = sub.add_parser("development", help="check a paired trace")
    dev.add_argument("trial", type=Path)
    dev.add_argument("--pulse", type=int, required=True)
    freeze = sub.add_parser("predict", help="freeze input-only predictions")
    freeze.add_argument("trial", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--pulse", type=int, required=True)
    validate = sub.add_parser("validate", help="compare frozen values to output-only trace")
    validate.add_argument("prediction", type=Path)
    validate.add_argument("trial", type=Path)
    args = parser.parse_args()
    if args.action == "development":
        control = (args.trial / "phase1b-input.log").read_text(errors="replace")
        assert f"STEER_PULSE={args.pulse}" in control
        assert "POSITION_MATH_ARMED,both" in control
        debug = (args.trial / "debug.log").read_text()
        marker = None
        inputs, outputs = [], []
        for line in debug.splitlines():
            frame = MARKER.search(line)
            if frame:
                marker = int(frame[1])
            entry, result = INPUT.search(line), OUTPUT.search(line)
            if entry:
                inputs.append((marker, tuple(int(x, 16) for x in entry.groups())))
            if result:
                outputs.append((marker, int(result[1], 16)))
        predictions = predicted(inputs)
        assert len(predictions) == len(outputs) == 20
        assert all(item["marker"] == frame and item["predicted"] == f"{value:04X}"
                   for item, (frame, value) in zip(predictions, outputs))
        print("PASS development", len(predictions), "updates",
              "negative operands", sum(signed16(values[1]) < 0 for _, values in inputs))
    elif args.action == "predict":
        assert not args.output.exists(), "predictions already frozen"
        inputs, input_hash = entries(args.trial, "input", args.pulse)
        result = {"schema": 1, "pulse": args.pulse,
                  "input_debug_sha256": input_hash,
                  "predictions": predicted(inputs)}
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print("FROZEN", len(inputs), "predictions", digest(args.output))
    else:
        frozen = json.loads(args.prediction.read_text())
        actual, output_hash = entries(args.trial, "output", frozen["pulse"])
        assert len(frozen["predictions"]) == len(actual) == 20
        errors = [{"marker": item["marker"], "expected": item["predicted"],
                   "actual": f"{value[0]:04X}"}
                  for item, (frame, value) in zip(frozen["predictions"], actual)
                  if item["marker"] != frame or item["predicted"] != f"{value[0]:04X}"]
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "pulse": frozen["pulse"], "matched": 20 - len(errors),
                          "total": 20, "errors": errors,
                          "frozen_prediction_sha256": digest(args.prediction),
                          "target_debug_sha256": output_hash}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
