#!/usr/bin/env python3
"""Predict one arcade position lookup chain from prior accumulator state."""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROM_SHA256 = "03143b6e3ba0045109e1745d06e04bda0db638f1cd7fadb1eab0b403fae40618"
TABLE_SHA256 = "58026dc7abea35d5336cdbd17dab0dc41714eafb9c8f64e2e9d49643b979f679"
FRAMES = list(range(961, 1000, 2))
PATTERNS = {
    "input": re.compile(r"POSITION_OFFSET_INPUT pc=03451C old=([0-9A-F]{4}) delta=([0-9A-F]{4})"),
    "output": re.compile(r"POSITION_OFFSET_OUTPUT pc=03454E offset=([0-9A-F]{4}) phase=([0-9A-F]{4})"),
    "index": re.compile(r"POSITION_OFFSET_INDEX pc=034B02 index=([0-9A-F]+)"),
    "coefficient": re.compile(r"POSITION_OFFSET_COEFFICIENT pc=034C1C coefficient=([0-9A-F]{4})"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(trial, phase, pulse):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert "STATE_LOAD,950," in control
    assert f"POSITION_OFFSET_ARMED,{phase}" in control
    assert "POSITION_OFFSET_CLEARED,1000" in control
    path = trial / "debug.log"
    data = path.read_text()
    needed = ("input", "output", "index", "coefficient") if phase == "both" else (
        ("input",) if phase == "input" else ("output", "index", "coefficient"))
    forbidden = ("output", "index", "coefficient") if phase == "input" else (
        ("input",) if phase == "output" else ())
    assert all("POSITION_OFFSET_" + name.upper() not in data for name in forbidden)
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


def predict(inputs, table, rom):
    assert len(table) == 4096 and len(rom) == 0x80000
    result = []
    for frame, (old, delta) in inputs["input"]:
        phase = (old + delta) & 0x7ff
        offset = phase * 2
        index = int.from_bytes(table[offset:offset + 2], "big")
        coefficient_address = 0xef6 + 2 * index
        assert coefficient_address + 2 <= len(rom)
        coefficient = int.from_bytes(rom[coefficient_address:coefficient_address + 2], "big")
        result.append({"marker": frame, "old": f"{old:04X}", "delta": f"{delta:04X}",
                       "phase": f"{phase:04X}", "offset": f"{offset:04X}",
                       "index": f"{index:04X}", "coefficient": f"{coefficient:04X}"})
    return result


def compare(predictions, targets):
    errors = []
    for step, row in enumerate(predictions):
        for kind, fields in (("output", ("offset", "phase")),
                             ("index", ("index",)),
                             ("coefficient", ("coefficient",))):
            marker, values = targets[kind][step]
            assert marker == row["marker"]
            for field, value in zip(fields, values):
                if int(row[field], 16) != (value & 0xffff):
                    errors.append({"marker": marker, "field": field,
                                   "predicted": row[field], "observed": f"{value & 0xffff:04X}"})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("development", "predict"):
        command = sub.add_parser(name)
        command.add_argument("trial", type=Path)
        command.add_argument("table", type=Path)
        command.add_argument("rom", type=Path)
        if name == "predict":
            command.add_argument("output", type=Path)
        command.add_argument("--pulse", type=int, required=True)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("trial", type=Path)
    args = parser.parse_args()
    if args.command in ("development", "predict"):
        assert sha256(args.table) == TABLE_SHA256
        assert sha256(args.rom) == ROM_SHA256
        phase = "both" if args.command == "development" else "input"
        events, trace_sha = trace(args.trial, phase, args.pulse)
        rows = predict(events, args.table.read_bytes(), args.rom.read_bytes())
        if args.command == "development":
            errors = compare(rows, events)
            assert not errors, errors
            print("PASS development", len(rows), "updates, 4 fields each")
        else:
            assert not args.output.exists(), "predictions already frozen"
            record = {"schema": 1, "pulse": args.pulse,
                      "input_debug_sha256": trace_sha,
                      "private_rom_sha256": ROM_SHA256, "private_table_sha256": TABLE_SHA256,
                      "predictions": rows}
            args.output.write_text(json.dumps(record, indent=2) + "\n")
            print("FROZEN", len(rows), "predictions", sha256(args.output))
    else:
        frozen = json.loads(args.frozen.read_text())
        assert frozen["private_rom_sha256"] == ROM_SHA256
        assert frozen["private_table_sha256"] == TABLE_SHA256
        targets, trace_sha = trace(args.trial, "output", frozen["pulse"])
        rows = frozen["predictions"]
        assert len(rows) == len(FRAMES)
        errors = compare(rows, targets)
        result = {"status": "PASS" if not errors else "FAIL", "pulse": frozen["pulse"],
                  "matched_fields": 4 * len(rows) - len(errors), "total_fields": 4 * len(rows),
                  "errors": errors, "frozen_sha256": sha256(args.frozen),
                  "target_debug_sha256": trace_sha}
        print(json.dumps(result, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
