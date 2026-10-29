#!/usr/bin/env python3
"""Freeze the first object-entry list count from prior all-CPU count writes."""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


WRITE = re.compile(r"PROJECTION_COUNT_WRITE cpu=(maincpu|subx|suby) "
                   r"pc=([0-9A-F]{6}) data=([0-9A-F]{4})")
ENTRY = re.compile(r"PROJECTION_COUNT_ENTRY pc=033D1E count=([0-9A-F]{4})")
PRELOCK = re.compile(r"PROJECTION_COUNT_PRELOCK pc=033E68 count=([0-9A-F]{4})")
COPY = re.compile(r"PROJECTION_COUNT_COPY pc=033E8E count=([0-9A-F]{4}) "
                  r"slot=([0-9A-F]{4})")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(source, frozen, pulse):
    assert not frozen.exists(), "prediction already frozen"
    control_path = source / "phase1b-input.log"
    control = control_path.read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert "PROJECTION_COUNT_ARMED,input,960" in control
    assert "Exited via the debugger" in control
    log_path = source / "debug.log"
    log = log_path.read_text(errors="replace")
    assert log.count("PROJECTION_COUNT_TARGET pc=033D1E") == 1
    prefix = log.split("PROJECTION_COUNT_TARGET pc=033D1E", 1)[0]
    assert "PROJECTION_COUNT_ENTRY" not in prefix
    assert "PROJECTION_COUNT_PRELOCK" not in prefix
    assert "PROJECTION_COUNT_COPY" not in prefix
    writes = [(cpu, pc, int(word, 16)) for cpu, pc, word in WRITE.findall(prefix)]
    resets = [i for i, (cpu, pc, word) in enumerate(writes)
              if cpu == "maincpu" and pc == "033264" and word == 0]
    assert len(resets) == 1
    positive = writes[resets[0] + 1:]
    assert positive and [word for _, _, word in positive] == list(range(1, len(positive) + 1))
    counts = collections.Counter(cpu for cpu, _, _ in positive)
    prediction = {"schema": 1, "source_commit": "57a738b", "pulse": pulse,
                  "marker": 961, "entry_count": f"{len(positive):04X}",
                  "prior_writes_by_cpu": dict(counts),
                  "input_debug_sha256": digest(log_path),
                  "input_control_sha256": digest(control_path)}
    frozen.write_text(json.dumps(prediction, indent=2) + "\n")
    print(json.dumps({"status": "FROZEN", "sha256": digest(frozen),
                      "entry_count": prediction["entry_count"],
                      "prior_writes_by_cpu": prediction["prior_writes_by_cpu"]}, indent=2))


def validate(frozen, target):
    prediction = json.loads(frozen.read_text())
    assert prediction["schema"] == 1
    control_path = target / "phase1b-input.log"
    control = control_path.read_text(errors="replace")
    assert f"STEER_PULSE={prediction['pulse']}" in control
    assert "PROJECTION_COUNT_ARMED,output,960" in control
    assert "PROJECTION_COUNT_CLEARED,970" in control
    log_path = target / "debug.log"
    log = log_path.read_text(errors="replace")
    assert "Error in expression" not in log
    first = log.split("PROJECTION_COUNT_FRAME,962", 1)[0]
    entry = ENTRY.findall(first)
    prelock = PRELOCK.findall(first)
    copy = COPY.findall(first)
    assert len(entry) == len(prelock) == len(copy) == 1
    assert int(copy[0][1], 16) == int(copy[0][0], 16) * 16
    result = {"status": "PASS" if entry[0] == prediction["entry_count"] else "FAIL",
              "predicted_entry_count": prediction["entry_count"],
              "observed_entry_count": entry[0],
              "observed_prelock_count": prelock[0],
              "observed_copy_count": copy[0][0],
              "observed_copy_slot": copy[0][1],
              "frozen_sha256": digest(frozen),
              "target_debug_sha256": digest(log_path),
              "target_control_sha256": digest(control_path)}
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
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
