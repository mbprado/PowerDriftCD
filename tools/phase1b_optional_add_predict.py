#!/usr/bin/env python3
"""Freeze and validate a controlled optional-addition branch in MAME."""

import argparse
import json
import re
from pathlib import Path

from phase1b_position_chain_predict import (
    ROM_SHA256, compare, compute, digest, trace,
)


PULSE = 212


def override(directory, phase, amount):
    control = directory / "phase1b-input.log"
    data = control.read_text(errors="replace")
    assert "LUA ERROR" not in data
    assert f"POSITION_CHAIN_ARMED,{phase}" in data
    events = re.findall(r"POSITION_OPTIONAL_ADD_OVERRIDE,960,([0-9A-F]{4}),"
                        r"([0-9A-F]{4}),0001,([0-9A-F]{4})", data)
    assert len(events) == 1 and events[0][2] == f"{amount:04X}"
    assert events[0][:2] == ("0000", "0000")
    return digest(control)


def model(input_dir, rom_path, amount):
    assert digest(rom_path) == ROM_SHA256
    control_sha = override(input_dir, "input", amount)
    events, debug_sha = trace(input_dir, "input", PULSE)
    positives = [frame for frame, (_, _, state80, state7e) in events["pre"]
        if 0 < state80 < 0x8000 and state7e == amount]
    assert positives == [961], positives
    rows = compute(events, rom_path.read_bytes())
    return {"schema": 1, "pulse": PULSE, "optional_add": f"{amount:04X}",
            "branch_markers": positives, "input_control_sha256": control_sha,
            "input_debug_sha256": debug_sha, "private_rom_sha256": ROM_SHA256,
            "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    dev = sub.add_parser("development")
    dev.add_argument("input", type=Path)
    dev.add_argument("target", type=Path)
    dev.add_argument("rom", type=Path)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("input", type=Path)
    freeze.add_argument("rom", type=Path)
    freeze.add_argument("frozen", type=Path)
    freeze.add_argument("control_input", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("input", type=Path)
    check.add_argument("rom", type=Path)
    check.add_argument("frozen", type=Path)
    check.add_argument("target", type=Path)
    check.add_argument("control_input", type=Path)
    args = parser.parse_args()
    if args.action == "development":
        expected = model(args.input, args.rom, 1)
        target_sha = override(args.target, "output", 1)
        targets, debug_sha = trace(args.target, "output", PULSE)
        errors = compare(expected["predictions"], targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "matched_fields": 60 - len(errors), "errors": errors,
                          "target_control_sha256": target_sha,
                          "target_debug_sha256": debug_sha}, indent=2))
        assert not errors
    elif args.action == "freeze":
        assert not args.frozen.exists(), "prediction already frozen"
        control, _ = trace(args.control_input, "input", PULSE)
        assert override(args.control_input, "input", 1)
        heldout, _ = trace(args.input, "input", PULSE)
        assert heldout["pre"][0][1][:3] == control["pre"][0][1][:3]
        assert control["pre"][0][1][3] == 1
        record = model(args.input, args.rom, 0x40)
        record["control_input_debug_sha256"] = digest(args.control_input / "debug.log")
        args.frozen.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"status": "FROZEN", "sha256": digest(args.frozen),
                          "first_operand": record["predictions"][0]["operand"],
                          "branch_markers": record["branch_markers"]}))
    else:
        frozen = json.loads(args.frozen.read_text())
        assert frozen["control_input_debug_sha256"] == digest(
            args.control_input / "debug.log")
        recomputed = model(args.input, args.rom, 0x40)
        assert {key: frozen[key] for key in recomputed} == recomputed
        control_sha = override(args.target, "output", 0x40)
        targets, debug_sha = trace(args.target, "output", PULSE)
        errors = compare(frozen["predictions"], targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "matched_fields": 60 - len(errors), "errors": errors,
                          "frozen_sha256": digest(args.frozen),
                          "target_control_sha256": control_sha,
                          "target_debug_sha256": debug_sha}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
