#!/usr/bin/env python3
"""Freeze and validate the main CPU projection-list slot from pre-copy state."""

import argparse
import hashlib
import json
import re
from pathlib import Path


MARKERS = list(range(961, 1000, 2))
FRAME = re.compile(r"PROJECTION_SLOT_FRAME,(\d+)")
INPUT = re.compile(r"PROJECTION_SLOT_INPUT pc=033E68 count=([0-9A-F]{4}) base=([0-9A-F]{8})")
OUTPUT = re.compile(r"PROJECTION_SLOT_OUTPUT pc=033E8E slot=([0-9A-F]{4}) "
                    r"base=([0-9A-F]{8}) count=([0-9A-F]{4}) addr=([0-9A-F]{8})")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(directory, phase, pulse):
    control = directory / "phase1b-input.log"
    control_text = control.read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control_text
    assert f"PROJECTION_SLOT_ARMED,{phase},960" in control_text
    assert "PROJECTION_SLOT_CLEARED,1000" in control_text
    log = directory / "debug.log"
    text = log.read_text(errors="replace")
    assert "Error in expression" not in text
    assert ("PROJECTION_SLOT_OUTPUT" if phase == "input" else "PROJECTION_SLOT_INPUT") not in text
    rows = {}
    marker = None
    for line in text.splitlines():
        found = FRAME.search(line)
        if found:
            marker = int(found[1])
        found = (INPUT if phase == "input" else OUTPUT).search(line)
        if found:
            assert marker in MARKERS and marker not in rows
            rows[marker] = found.groups()
    assert all(marker in text for marker in ("PROJECTION_SLOT_FRAME,960", "PROJECTION_SLOT_FRAME,1000"))
    return rows, digest(log), digest(control)


def freeze(source, target, pulse):
    assert not target.exists(), "prediction already frozen"
    rows, debug_sha, control_sha = capture(source, "input", pulse)
    predictions = []
    for marker in MARKERS:
        entry = {"marker": marker, "copy": marker in rows}
        if marker in rows:
            count_hex, base_hex = rows[marker]
            count = int(count_hex, 16)
            base = int(base_hex, 16)
            assert count < 0x17F and base in (0x0C8000, 0x0C9800)
            slot = (count << 4) & 0xFFFF
            entry.update(count=count_hex, base=base_hex, slot=f"{slot:04X}",
                         addr=f"{base + slot:08X}")
        predictions.append(entry)
    record = {"schema": 1, "source_commit": "9eeb140", "pulse": pulse,
              "input_debug_sha256": debug_sha,
              "input_control_sha256": control_sha,
              "predictions": predictions}
    target.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "FROZEN", "sha256": digest(target),
                      "copies": len(rows), "skips": len(MARKERS) - len(rows)}, indent=2))


def validate(frozen, directory):
    record = json.loads(frozen.read_text())
    assert record["schema"] == 1
    rows, debug_sha, control_sha = capture(directory, "output", record["pulse"])
    errors = []
    total = 0
    for prediction in record["predictions"]:
        marker = prediction["marker"]
        row = rows.get(marker)
        total += 1
        if bool(row) != prediction["copy"]:
            errors.append({"marker": marker, "field": "copy", "expected": prediction["copy"],
                           "observed": bool(row)})
        if row:
            for field, observed in zip(("slot", "base", "count", "addr"), row):
                total += 1
                if observed != prediction[field]:
                    errors.append({"marker": marker, "field": field,
                                   "expected": prediction[field], "observed": observed})
    result = {"status": "PASS" if not errors else "FAIL", "matched": total - len(errors),
              "total": total, "errors": errors, "frozen_sha256": digest(frozen),
              "target_debug_sha256": debug_sha, "target_control_sha256": control_sha}
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    freeze_command = sub.add_parser("freeze")
    freeze_command.add_argument("source", type=Path)
    freeze_command.add_argument("target", type=Path)
    freeze_command.add_argument("--pulse", type=int, required=True)
    validate_command = sub.add_parser("validate")
    validate_command.add_argument("frozen", type=Path)
    validate_command.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.source, args.target, args.pulse)
    else:
        validate(args.frozen, args.directory)


if __name__ == "__main__":
    main()
