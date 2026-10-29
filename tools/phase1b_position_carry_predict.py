#!/usr/bin/env python3
"""Carry the predicted $28 position word through the exercised operand path."""

import argparse
import json
import re
from pathlib import Path

from phase1b_forward_preadd_predict import ROM_SHA256, sha
from phase1b_state24_forward_predict import predict as forward_predict
from phase1b_state24_source_predict import predict as source24_predict
from phase1b_state8a_predict import predict as source8a_predict
from phase1b_state7c_predict import step as divide_step


FRAMES = list(range(961, 1000, 2))
TIMER = re.compile(r"POSITION_CARRY_TIMER pc=034EF4 timer=([0-9A-F]{4})")
GUARD = re.compile(r"POSITION_CARRY_GUARD pc=034FA4 d3=([0-9A-F]{8}) "
                   r"state80=([0-9A-F]{4}) state7e=([0-9A-F]{4})")
OPERAND = re.compile(r"POSITION_CHAIN_OPERAND pc=034FDA value=([0-9A-F]{4})")


def signed16(word):
    word &= 0xFFFF
    return word - 0x10000 if word & 0x8000 else word


def carry_inputs(trial, pulse):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control and "STATE_LOAD,950," in control
    assert "POSITION_CARRY_ARMED,input" in control
    assert "POSITION_CARRY_CLEARED,1000" in control and "LUA ERROR" not in control
    match = re.search(r"POSITION_CARRY_INIT,960,([0-9A-F]{4})", control)
    assert match
    initial = int(match[1], 16)
    path = trial / "debug.log"
    data = path.read_text()
    assert "POSITION_CHAIN_OPERAND" not in data
    assert "POSITION_PREADD_OUTPUT" not in data
    assert "POSITION_PREADD_BASE" not in data
    rows = {"timer": [], "guard": []}
    marker = None
    for line in data.splitlines():
        frame = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if frame:
            marker = int(frame[1])
        for name, pattern in (("timer", TIMER), ("guard", GUARD)):
            value = pattern.search(line)
            if value:
                rows[name].append((marker, tuple(int(x, 16) for x in value.groups())))
    assert all([frame for frame, _ in rows[name]] == FRAMES for name in rows)
    return initial, rows, sha(path), sha(trial / "phase1b-input.log")


def forward_inputs(root, pulse):
    source24_path = root / f"state24-source-inputs-{pulse}/debug.log"
    source8a_path = root / f"state8a-inputs-{pulse}-corrected/debug.log"
    state24_file = root / f"state24-source-prediction-{pulse}.json"
    state8a_file = root / f"state8a-prediction-{pulse}.json"
    forward_file = root / f"state24-forward-prediction-{pulse}.json"
    state24 = json.loads(state24_file.read_text())
    state8a = json.loads(state8a_file.read_text())
    assert state24["pulse"] == state8a["pulse"] == pulse
    assert state24["input_trace_sha256"] == sha(source24_path)
    assert state8a["input_trace_sha256"] == sha(source8a_path)
    assert {key: state24[key] for key in ("initial_global", "predictions")} == \
        source24_predict(source24_path)
    assert state8a == source8a_predict(root, pulse)
    forward = json.loads(forward_file.read_text())
    assert forward == forward_predict(root, pulse)
    assert [item["frame"] for item in forward["predictions"]] == FRAMES
    return forward, {"source24_prediction_sha256": sha(state24_file),
                     "source8a_prediction_sha256": sha(state8a_file),
                     "forward_prediction_sha256": sha(forward_file)}


def predict(root, trial, pulse):
    rom_path = root.parent / "phase1b-code-pilot/pdrift-maincpu.bin"
    assert sha(rom_path) == ROM_SHA256
    forward, source_hashes = forward_inputs(root, pulse)
    old28, guards, guard_sha, control_sha = carry_inputs(trial, pulse)
    initial28 = old28
    old7c = forward["initial"]["7c"]
    rom = rom_path.read_bytes()
    output = []
    for step_index, (row, (frame_t, (timer,)),
                     (frame_g, (d3, state80, state7e))) in enumerate(zip(
                         forward["predictions"], guards["timer"], guards["guard"])):
        frame = row["frame"]
        assert frame == frame_t == frame_g
        assert timer == 0, "timed multiplier branch requires a separate model"
        divided = divide_step(rom, row["predicted_86"], row["predicted_7a"],
                              row["predicted_24"], row["predicted_8a"],
                              old7c, row["flag69"])
        assert divided["predicted_new7c"] == row["predicted_7c"]
        old7c = row["predicted_7c"]
        value = signed16(old28 + divided["divide_quotient"] + signed16(d3))
        if signed16(state80) > 0:
            value = signed16(value + signed16(state7e))
        unclamped = value
        value = max(-0x5FF, min(0x5FF, value)) & 0xFFFF
        output.append({"marker": frame, "predicted_new28": f"{value:04X}",
                       "branch": "positive_clamp" if unclamped > 0x5FF else
                                 "negative_clamp" if unclamped < -0x5FF else "none",
                       "correction_d3": f"{d3:08X}",
                       "state80": f"{state80:04X}"})
        old28 = value
    assert len(output) == 20
    return {"schema": 1, "pulse": pulse, "private_rom_sha256": ROM_SHA256,
            "initial_old28": f"{initial28:04X}",
            "guard_debug_sha256": guard_sha, "guard_control_sha256": control_sha,
            **source_hashes, "predictions": output}


def observed(trial, pulse, phase):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control
    assert f"POSITION_CHAIN_ARMED,{phase}" in control
    assert "POSITION_CHAIN_CLEARED,1000" in control and "LUA ERROR" not in control
    data = (trial / "debug.log").read_text()
    if phase == "output":
        assert "POSITION_CHAIN_PRE" not in data and "POSITION_CHAIN_BASE" not in data
    marker = None
    rows = []
    for line in data.splitlines():
        frame = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if frame:
            marker = int(frame[1])
        word = OPERAND.search(line)
        if word:
            rows.append((marker, word[1]))
    assert [frame for frame, _ in rows] == FRAMES
    return rows, sha(trial / "debug.log")


def compare(predictions, targets):
    return [{"marker": frame, "predicted": item["predicted_new28"],
             "observed": word}
            for item, (frame, word) in zip(predictions, targets)
            if item["marker"] != frame or item["predicted_new28"] != word]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("development", "freeze", "validate"))
    parser.add_argument("upstream_root", type=Path)
    parser.add_argument("guard_trial", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--pulse", type=int, required=True)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    if args.action == "development":
        record = predict(args.upstream_root, args.guard_trial, args.pulse)
        targets, trace_sha = observed(args.result, args.pulse, "both")
        errors = compare(record["predictions"], targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "updates": len(targets), "errors": errors,
                          "target_debug_sha256": trace_sha}, indent=2))
        assert not errors
    elif args.action == "freeze":
        assert not args.result.exists(), "prediction already frozen"
        record = predict(args.upstream_root, args.guard_trial, args.pulse)
        args.result.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"status": "FROZEN", "updates": len(record["predictions"]),
                          "sha256": sha(args.result)}))
    else:
        assert args.target is not None
        frozen = json.loads(args.result.read_text())
        assert frozen == predict(args.upstream_root, args.guard_trial, args.pulse)
        targets, trace_sha = observed(args.target, args.pulse, "output")
        errors = compare(frozen["predictions"], targets)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "updates": len(targets), "matched": len(targets)-len(errors),
                          "errors": errors, "frozen_sha256": sha(args.result),
                          "target_debug_sha256": trace_sha}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
