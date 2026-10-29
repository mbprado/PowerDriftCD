#!/usr/bin/env python3
"""Predict the exercised pre-add D0 path from earlier divide inputs."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from phase1b_state7c_predict import step


ROM_SHA256 = "03143b6e3ba0045109e1745d06e04bda0db638f1cd7fadb1eab0b403fae40618"
FRAMES = list(range(961, 1000, 2))
PATTERNS = {
    "state": re.compile(r"POSITION_PREADD_STATE pc=034E24 "
                        r"word86=([0-9A-F]{4}) word7a=([0-9A-F]{4}) "
                        r"word24=([0-9A-F]{4}) word8a=([0-9A-F]{4}) "
                        r"old7c=([0-9A-F]{4}) flag69=([0-9A-F]{2})"),
    "base": re.compile(r"POSITION_PREADD_BASE pc=034EF4 "
                       r"timer=([0-9A-F]{4}) old28=([0-9A-F]{4})"),
    "output": re.compile(r"POSITION_PREADD_OUTPUT pc=034F1E "
                         r"d0=([0-9A-F]{8}) value82=([0-9A-F]{4})"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(directory, phase, pulse):
    control = (directory / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control and "STATE_LOAD,950," in control
    assert f"POSITION_PREADD_ARMED,{phase}" in control
    assert "POSITION_PREADD_CLEARED,1000" in control
    assert "LUA ERROR" not in control
    path = directory / "debug.log"
    data = path.read_text()
    needed = ("state", "base", "output") if phase == "both" else (
        ("state", "base") if phase == "input" else ("output",))
    forbidden = ("output",) if phase == "input" else (
        ("state", "base") if phase == "output" else ())
    assert all(PATTERNS[name].search(data) is None for name in forbidden)
    rows = {name: [] for name in needed}
    marker = None
    for line in data.splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            marker = int(match[1])
        for name in needed:
            match = PATTERNS[name].search(line)
            if match:
                assert marker is not None
                rows[name].append((marker, tuple(int(x, 16) for x in match.groups())))
    assert all([frame for frame, _ in rows[name]] == FRAMES for name in needed)
    return rows, sha(path)


def predict(rows, rom):
    result = []
    for (frame, state), (base_frame, (timer, old28)) in zip(
            rows["state"], rows["base"]):
        assert frame == base_frame
        assert timer == 0, "active timer branch needs a separate model"
        div = step(rom, *state)
        quotient, remainder = div["divide_quotient"], div["divide_remainder"]
        d0 = ((remainder & 0xFFFF) << 16) | ((quotient + old28) & 0xFFFF)
        result.append({"marker": frame, "predicted_d0": f"{d0:08X}",
                       "predicted_value82": f"{quotient & 0xFFFF:04X}",
                       "timer": f"{timer:04X}", "old28": f"{old28:04X}"})
    assert len(result) == len(FRAMES)
    return result


def differences(predicted, targets):
    errors = []
    for item, (frame, (d0, value82)) in zip(predicted, targets):
        assert item["marker"] == frame
        if item["predicted_d0"] != f"{d0:08X}" or item["predicted_value82"] != f"{value82:04X}":
            errors.append({"marker": frame, "predicted_d0": item["predicted_d0"],
                           "observed_d0": f"{d0:08X}",
                           "predicted_value82": item["predicted_value82"],
                           "observed_value82": f"{value82:04X}"})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    dev = sub.add_parser("development")
    dev.add_argument("trial", type=Path)
    dev.add_argument("rom", type=Path)
    dev.add_argument("--pulse", type=int, required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("trial", type=Path)
    freeze.add_argument("rom", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--pulse", type=int, required=True)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.action in ("development", "freeze"):
        assert sha(args.rom) == ROM_SHA256
        phase = "both" if args.action == "development" else "input"
        rows, trace_sha = trace(args.trial, phase, args.pulse)
        prediction = predict(rows, args.rom.read_bytes())
        if args.action == "development":
            errors = differences(prediction, rows["output"])
            print(json.dumps({"status": "PASS" if not errors else "FAIL",
                              "updates": len(prediction), "differences": errors,
                              "debug_sha256": trace_sha}))
            assert not errors
        else:
            assert not args.output.exists(), "prediction already frozen"
            result = {"schema": 1, "pulse": args.pulse,
                      "input_debug_sha256": trace_sha,
                      "private_rom_sha256": ROM_SHA256,
                      "predictions": prediction}
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps({"status": "FROZEN", "updates": len(prediction),
                              "sha256": sha(args.output)}))
    else:
        frozen = json.loads(args.frozen.read_text())
        assert frozen["private_rom_sha256"] == ROM_SHA256
        target, trace_sha = trace(args.target, "output", frozen["pulse"])
        assert len(frozen["predictions"]) == len(target["output"]) == len(FRAMES)
        errors = differences(frozen["predictions"], target["output"])
        result = {"status": "PASS" if not errors else "FAIL",
                  "updates": len(FRAMES), "matched_fields": 2 * len(FRAMES) - 2 * len(errors),
                  "differences": errors, "frozen_sha256": sha(args.frozen),
                  "target_debug_sha256": trace_sha}
        print(json.dumps(result, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
