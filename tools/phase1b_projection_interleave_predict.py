#!/usr/bin/env python3
"""Freeze a bounded Sub-Y entry-state prediction of main list-copy counts."""

import argparse
import hashlib
import json
import re
from pathlib import Path


MARKERS = (961, 963, 965, 967, 969)
INPUT = re.compile(r"PROJECTION_INTERLEAVE_INPUT,(\d+),([0-9A-F]{6}),"
                   r"([0-9A-F]{8}),([0-9A-F]{4}),([0-9A-F]{2}),"
                   r"([0-9A-F]{4}),([0-9A-F]{4})")
FRAME = re.compile(r"PROJECTION_INTERLEAVE_FRAME,(\d+)")
OUTPUT = re.compile(r"PROJECTION_INTERLEAVE_OUTPUT name=(ENTRY|LOCKED|COPY) "
                    r"pc=([0-9A-F]{6}) count=([0-9A-F]{4}) "
                    r"lock=([0-9A-F]{2})(?: slot=([0-9A-F]{4}))?")

# Development pulse 124: local Sub-Y PC signatures and observed count deltas.
DEVELOPMENT_RULE = {
    0x012B3A: 1, 0x012A06: 1, 0x01293E: 0,
    0x0129BA: 0, 0x0129A8: 1,
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def control(directory, phase, pulse):
    path = directory / "phase1b-input.log"
    text = path.read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in text
    assert f"PROJECTION_INTERLEAVE_ARMED,{phase},960" in text
    assert "PROJECTION_INTERLEAVE_CLEARED,970" in text
    assert "LUA ERROR" not in text
    return text, digest(path)


def freeze(source, frozen, pulse):
    assert not frozen.exists(), "prediction already frozen"
    text, control_sha = control(source, "input", pulse)
    debug_path = source / "debug.log"
    debug = debug_path.read_text(errors="replace")
    assert "PROJECTION_INTERLEAVE_OUTPUT" not in debug
    rows = INPUT.findall(text)
    assert tuple(int(row[0]) for row in rows) == MARKERS
    predictions = []
    for marker_text, pc_text, object_text, count_text, lock_text, fieldc, field30 in rows:
        pc = int(pc_text, 16)
        if pc == 0x012932:
            # New held-out PC: nonzero ($c,A0) enters the $129A8 path.
            assert int(fieldc, 16) != 0 and int(object_text, 16) == 0xFFFF2240
            delta, basis = 1, "code-path extrapolation"
        else:
            assert pc in DEVELOPMENT_RULE, f"unclassified Sub-Y PC {pc_text}"
            delta, basis = DEVELOPMENT_RULE[pc], "development signature"
        assert lock_text == "00"
        count = int(count_text, 16)
        assert count + delta < 0x17F
        predictions.append({"marker": int(marker_text), "suby_pc": pc_text,
                            "suby_object": object_text, "suby_field_c": fieldc,
                            "suby_field_30": field30, "basis": basis,
                            "entry_count": count_text, "delta": delta,
                            "lock_count": f"{count + delta:04X}",
                            "copy_slot": f"{(count + delta) * 16:04X}"})
    record = {"schema": 1, "source_commit": "3c4e904", "pulse": pulse,
              "input_control_sha256": control_sha,
              "input_debug_sha256": digest(debug_path),
              "predictions": predictions}
    frozen.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "FROZEN", "sha256": digest(frozen),
                      "predicted_deltas": [row["delta"] for row in predictions]}, indent=2))


def output_events(path):
    data = path.read_text(errors="replace")
    assert "Error in expression" not in data
    events = {marker: {} for marker in MARKERS}
    marker = None
    for line in data.splitlines():
        found = FRAME.search(line)
        if found:
            marker = int(found[1])
        found = OUTPUT.search(line)
        if found and marker in events:
            name, pc, count, lock, slot = found.groups()
            assert name not in events[marker]
            events[marker][name] = (pc, count, lock, slot)
    assert all(set(rows) == {"ENTRY", "LOCKED", "COPY"} for rows in events.values())
    return events


def validate(frozen, target):
    record = json.loads(frozen.read_text())
    assert record["schema"] == 1
    _, control_sha = control(target, "output", record["pulse"])
    debug_path = target / "debug.log"
    events = output_events(debug_path)
    errors = []
    scored = 0
    for row in record["predictions"]:
        marker = row["marker"]
        entry, locked, copy = (events[marker][name]
                               for name in ("ENTRY", "LOCKED", "COPY"))
        expected = (("entry_count", entry[1], row["entry_count"]),
                    ("lock_count", locked[1], row["lock_count"]),
                    ("copy_count", copy[1], row["lock_count"]),
                    ("copy_slot", copy[3], row["copy_slot"]))
        assert entry[0] == "033D1E" and locked[0] == "033E70" and copy[0] == "033E8E"
        assert entry[2] == "00" and locked[2] == copy[2] == "80"
        for field, observed, wanted in expected:
            scored += 1
            if observed != wanted:
                errors.append({"marker": marker, "field": field,
                               "predicted": wanted, "observed": observed})
    result = {"status": "PASS" if not errors else "FAIL",
              "matched": scored - len(errors), "total": scored, "errors": errors,
              "frozen_sha256": digest(frozen),
              "target_debug_sha256": digest(debug_path),
              "target_control_sha256": control_sha}
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    freeze_command = commands.add_parser("freeze")
    freeze_command.add_argument("source", type=Path)
    freeze_command.add_argument("frozen", type=Path)
    freeze_command.add_argument("--pulse", type=int, required=True)
    check = commands.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.source, args.frozen, args.pulse)
    else:
        validate(args.frozen, args.target)


if __name__ == "__main__":
    main()
