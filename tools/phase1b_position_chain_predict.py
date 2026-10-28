#!/usr/bin/env python3
"""Predict a bounded Y-Board position chain from pre-write state and private ROM."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from phase1b_position_math_predict import signed16


ROM_SHA256 = "03143b6e3ba0045109e1745d06e04bda0db638f1cd7fadb1eab0b403fae40618"
PATTERNS = {
    "pre": re.compile(r"POSITION_CHAIN_PRE pc=034FA4 d0=([0-9A-F]{8}) "
                      r"d3=([0-9A-F]{8}) state80=([0-9A-F]{4}) state7e=([0-9A-F]{4})"),
    "index": re.compile(r"POSITION_CHAIN_INDEX pc=034B02 d1=([0-9A-F]{8})"),
    "base": re.compile(r"POSITION_CHAIN_BASE pc=034C1C base=([0-9A-F]{4})"),
    "operand": re.compile(r"POSITION_CHAIN_OPERAND pc=034FDA value=([0-9A-F]{4})"),
    "coefficient": re.compile(r"POSITION_CHAIN_COEFFICIENT pc=034C1C value=([0-9A-F]{4})"),
    "adjusted": re.compile(r"POSITION_CHAIN_ADJUSTED pc=034C38 value=([0-9A-F]{4})"),
}
INPUT = ("pre", "index", "base")
OUTPUT = ("operand", "coefficient", "adjusted")
FRAMES = list(range(961, 1000, 2))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(trial, phase, pulse):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert "STATE_LOAD,950," in control
    assert f"POSITION_CHAIN_ARMED,{phase}" in control
    assert "POSITION_CHAIN_CLEARED,1000" in control
    path = trial / "debug.log"
    data = path.read_text()
    needed = INPUT + OUTPUT if phase == "both" else INPUT if phase == "input" else OUTPUT
    forbidden = OUTPUT if phase == "input" else INPUT if phase == "output" else ()
    assert all("POSITION_CHAIN_" + name.upper() not in data for name in forbidden)
    found = {name: [] for name in needed}
    marker = None
    for line in data.splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            marker = int(match[1])
        for name in needed:
            match = PATTERNS[name].search(line)
            if match:
                assert marker is not None
                found[name].append((marker, tuple(int(v, 16) for v in match.groups())))
    assert all([frame for frame, _ in found[name]] == FRAMES for name in needed)
    return found, digest(path)


def compute(inputs, rom):
    assert len(rom) == 0x80000
    result = []
    for step, frame in enumerate(FRAMES):
        d0, d3, state80, state7e = inputs["pre"][step][1]
        (index_raw,) = inputs["index"][step][1]
        (base,) = inputs["base"][step][1]
        operand = signed16((d0 + d3) & 0xffff)
        if signed16(state80) > 0:
            operand = signed16((operand + signed16(state7e)) & 0xffff)
        operand = min(0x5ff, max(-0x5ff, operand)) & 0xffff
        index = index_raw & 0xffff
        address = 0x0ef6 + 2 * index
        assert address + 2 <= len(rom)
        coefficient = int.from_bytes(rom[address:address + 2], "big")
        delta = signed16(operand) * signed16(coefficient) >> 9
        adjusted = (base + delta) & 0xffff
        result.append({"marker": frame, "pre_d0": f"{d0:08X}",
                       "pre_d3": f"{d3:08X}", "state80": f"{state80:04X}",
                       "state7e": f"{state7e:04X}", "index": f"{index:04X}",
                       "base": f"{base:04X}", "operand": f"{operand:04X}",
                       "coefficient": f"{coefficient:04X}",
                       "adjusted": f"{adjusted:04X}"})
    return result


def compare(predictions, targets):
    errors = []
    for step, item in enumerate(predictions):
        for name in OUTPUT:
            frame, (value,) = targets[name][step]
            if frame != item["marker"] or f"{value:04X}" != item[name]:
                errors.append({"marker": item["marker"], "field": name,
                               "predicted": item[name], "observed": f"{value:04X}"})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dev = sub.add_parser("development")
    dev.add_argument("trial", type=Path)
    dev.add_argument("rom", type=Path)
    dev.add_argument("--pulse", type=int, required=True)
    freeze = sub.add_parser("predict")
    freeze.add_argument("trial", type=Path)
    freeze.add_argument("rom", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--pulse", type=int, required=True)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("trial", type=Path)
    args = parser.parse_args()
    if args.command in ("development", "predict"):
        assert digest(args.rom) == ROM_SHA256
        phase = "both" if args.command == "development" else "input"
        events, trace_sha = trace(args.trial, phase, args.pulse)
        predictions = compute(events, args.rom.read_bytes())
        if args.command == "development":
            errors = compare(predictions, events)
            assert not errors, errors
            print("PASS development", len(predictions), "updates, 3 fields each")
        else:
            assert not args.output.exists(), "predictions already frozen"
            result = {"schema": 1, "pulse": args.pulse,
                      "input_debug_sha256": trace_sha,
                      "private_rom_sha256": ROM_SHA256,
                      "predictions": predictions}
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            print("FROZEN", len(predictions), "predictions", digest(args.output))
    else:
        frozen = json.loads(args.frozen.read_text())
        assert frozen["private_rom_sha256"] == ROM_SHA256
        targets, trace_sha = trace(args.trial, "output", frozen["pulse"])
        predictions = frozen["predictions"]
        assert len(predictions) == 20
        errors = compare(predictions, targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "pulse": frozen["pulse"], "matched_fields": 60 - len(errors),
                          "total_fields": 60, "errors": errors,
                          "frozen_sha256": digest(args.frozen),
                          "target_debug_sha256": trace_sha}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
