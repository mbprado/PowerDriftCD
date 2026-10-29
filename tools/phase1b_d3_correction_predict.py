#!/usr/bin/env python3
"""Freeze and validate one controlled low-D3 correction at the position add."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(path, pattern):
    return re.findall(pattern, path.read_text(errors="replace"))


def control(directory, phase, amount):
    path = directory / "phase1b-input.log"
    data = path.read_text(errors="replace")
    assert "LUA ERROR" not in data
    assert f"POSITION_D3_ARMED,{phase},{amount:04X},960" in data
    assert "POSITION_D3_CLEARED,962" in data
    return sha256(path)


def output(directory):
    log = directory / "debug.log"
    rows = events(log, r"POSITION_D3_OUTPUT pc=034FDA d0=([0-9A-F]{8}) "
                   r"value=([0-9A-F]{4})")
    assert len(rows) == 1, rows
    frames = events(log, r"POSITION_D3_FRAME,(\d+)")
    assert frames == ["960", "961", "962"], frames
    return tuple(int(value, 16) for value in rows[0]), sha256(log)


def freeze(development, frozen, target_low):
    assert not frozen.exists(), "prediction is already frozen"
    assert target_low == 0x40
    control_sha = control(development, "both", 1)
    log = development / "debug.log"
    pre = events(log, r"POSITION_D3_PRE pc=034FA4 d0=([0-9A-F]{8}) "
                 r"d3=([0-9A-F]{8}) timer=([0-9A-F]{4}) "
                 r"state80=([0-9A-F]{4}) state7e=([0-9A-F]{4})")
    post = events(log, r"POSITION_D3_POST pc=034FA4 d3=([0-9A-F]{8})")
    assert len(pre) == len(post) == 1
    d0, d3, timer, state80, state7e = (int(value, 16) for value in pre[0])
    assert (d3 & 0xFFFF, state80, state7e) == (0, 0, 0)
    assert int(post[0], 16) == ((d3 & 0xFFFF0000) | 1)
    (observed_d0, observed_word), debug_sha = output(development)
    assert observed_d0 == ((d0 & 0xFFFF0000) | ((d0 + 1) & 0xFFFF))
    assert observed_word == ((d0 + 1) & 0xFFFF)
    expected_word = (d0 + target_low) & 0xFFFF
    signed = expected_word if expected_word < 0x8000 else expected_word - 0x10000
    assert -1535 <= signed <= 1535, "test would hit clamp"
    record = {
        "schema": 1, "source": "controlled first marker-961 position branch",
        "source_commit": "fe64179", "target_low_d3": f"{target_low:04X}",
        "pre_d0": f"{d0:08X}", "pre_d3": f"{d3:08X}",
        "pre_timer": f"{timer:04X}", "pre_state80": f"{state80:04X}",
        "pre_state7e": f"{state7e:04X}",
        "predicted_d0": f"{((d0 & 0xFFFF0000) | expected_word):08X}",
        "predicted_word": f"{expected_word:04X}",
        "development_control_sha256": control_sha,
        "development_debug_sha256": debug_sha,
    }
    frozen.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "FROZEN", "sha256": sha256(frozen),
                      "predicted_word": record["predicted_word"]}, indent=2))


def validate(frozen, target):
    record = json.loads(frozen.read_text())
    assert record["schema"] == 1
    amount = int(record["target_low_d3"], 16)
    control_sha = control(target, "output", amount)
    (observed_d0, observed_word), debug_sha = output(target)
    debug_text = (target / "debug.log").read_text(errors="replace")
    assert "POSITION_D3_PRE" not in debug_text
    assert "POSITION_D3_POST" not in debug_text
    errors = []
    if observed_d0 != int(record["predicted_d0"], 16):
        errors.append("d0 mismatch")
    if observed_word != int(record["predicted_word"], 16):
        errors.append("position word mismatch")
    print(json.dumps({"status": "PASS" if not errors else "FAIL",
                      "matched_fields": 2 - len(errors), "errors": errors,
                      "frozen_sha256": sha256(frozen),
                      "target_control_sha256": control_sha,
                      "target_debug_sha256": debug_sha}, indent=2))
    assert not errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze_cmd = commands.add_parser("freeze")
    freeze_cmd.add_argument("development", type=Path)
    freeze_cmd.add_argument("frozen", type=Path)
    validate_cmd = commands.add_parser("validate")
    validate_cmd.add_argument("frozen", type=Path)
    validate_cmd.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.development, args.frozen, 0x40)
    else:
        validate(args.frozen, args.target)


if __name__ == "__main__":
    main()
