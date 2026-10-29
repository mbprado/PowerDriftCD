#!/usr/bin/env python3
"""Carry existing forward state models into the pre-add divider output."""

import argparse
import json
import re
from pathlib import Path

from phase1b_preadd_predict import FRAMES, ROM_SHA256, PATTERNS, sha
from phase1b_state24_forward_predict import predict as forward_predict
from phase1b_state24_source_predict import predict as source24_predict
from phase1b_state8a_predict import predict as source8a_predict
from phase1b_state7c_predict import step as divide_step


def prior_rows(trial, pulse, phase):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control and "STATE_LOAD,950," in control
    assert f"POSITION_PREADD_ARMED,{phase}" in control
    assert "POSITION_PREADD_CLEARED,1000" in control
    assert "LUA ERROR" not in control
    data = (trial / "debug.log").read_text()
    if phase == "prior":
        assert "POSITION_PREADD_STATE" not in data
        assert "POSITION_PREADD_OUTPUT" not in data
    marker = None
    rows = []
    for line in data.splitlines():
        frame = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if frame:
            marker = int(frame[1])
        match = PATTERNS["base"].search(line)
        if match:
            rows.append((marker, int(match[1], 16), int(match[2], 16)))
    assert [frame for frame, _, _ in rows] == FRAMES
    return rows, sha(trial / "debug.log")


def model(root, pulse, prior_trial, prior_phase="prior"):
    rom_path = root.parent / "phase1b-code-pilot/pdrift-maincpu.bin"
    assert sha(rom_path) == ROM_SHA256
    state24_input = root / f"state24-source-inputs-{pulse}/debug.log"
    state8a_input = root / f"state8a-inputs-{pulse}-corrected/debug.log"
    forward_input = root / f"state24-forward-inputs-{pulse}/debug.log"
    state24_file = root / f"state24-source-prediction-{pulse}.json"
    state8a_file = root / f"state8a-prediction-{pulse}.json"
    state24 = json.loads(state24_file.read_text())
    state8a = json.loads(state8a_file.read_text())
    assert state24["pulse"] == state8a["pulse"] == pulse
    assert state24["input_trace_sha256"] == sha(state24_input)
    assert state8a["input_trace_sha256"] == sha(state8a_input)
    assert {key: state24[key] for key in ("initial_global", "predictions")} == \
        source24_predict(state24_input)
    assert state8a == source8a_predict(root, pulse)
    forward_file = root / f"state24-forward-prediction-{pulse}.json"
    forward = json.loads(forward_file.read_text())
    assert forward == forward_predict(root, pulse)
    assert forward["input_trace_sha256"] == sha(forward_input)
    prior, prior_sha = prior_rows(prior_trial, pulse, prior_phase)
    rom = rom_path.read_bytes()
    old7c = forward["initial"]["7c"]
    rows = []
    for values, (frame, timer, old28) in zip(forward["predictions"], prior):
        assert values["frame"] == frame
        assert timer == 0, "active timed multiplier is not modeled"
        divided = divide_step(rom, values["predicted_86"], values["predicted_7a"],
                              values["predicted_24"], values["predicted_8a"],
                              old7c, values["flag69"])
        assert divided["predicted_new7c"] == values["predicted_7c"]
        old7c = values["predicted_7c"]
        quotient, remainder = divided["divide_quotient"], divided["divide_remainder"]
        d0 = ((remainder & 0xFFFF) << 16) | ((quotient + old28) & 0xFFFF)
        rows.append({"marker": frame, "predicted_d0": f"{d0:08X}",
                     "predicted_value82": f"{quotient & 0xFFFF:04X}",
                     "prior28": f"{old28:04X}"})
    assert len(rows) == len(FRAMES)
    return {"schema": 1, "pulse": pulse, "private_rom_sha256": ROM_SHA256,
            "source24_input_sha256": sha(state24_input),
            "source8a_input_sha256": sha(state8a_input),
            "forward_input_sha256": sha(forward_input),
            "prior_input_sha256": prior_sha,
            "source24_prediction_sha256": sha(state24_file),
            "source8a_prediction_sha256": sha(state8a_file),
            "forward_prediction_sha256": sha(forward_file),
            "predictions": rows}


def output_rows(trial, pulse, phase):
    control = (trial / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control and f"POSITION_PREADD_ARMED,{phase}" in control
    assert "POSITION_PREADD_CLEARED,1000" in control and "LUA ERROR" not in control
    data = (trial / "debug.log").read_text()
    if phase == "output":
        assert "POSITION_PREADD_STATE" not in data and "POSITION_PREADD_BASE" not in data
    marker = None
    rows = []
    for line in data.splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            marker = int(match[1])
        match = PATTERNS["output"].search(line)
        if match:
            rows.append((marker, match[1], match[2]))
    assert [frame for frame, _, _ in rows] == FRAMES
    return rows, sha(trial / "debug.log")


def compare(predictions, observed):
    return [{"marker": frame, "predicted_d0": row["predicted_d0"],
             "observed_d0": d0, "predicted_value82": row["predicted_value82"],
             "observed_value82": value82}
            for row, (frame, d0, value82) in zip(predictions, observed)
            if row["marker"] != frame or row["predicted_d0"] != d0
            or row["predicted_value82"] != value82]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("development", "freeze", "validate"))
    parser.add_argument("upstream_root", type=Path)
    parser.add_argument("prior_trial", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--pulse", type=int, required=True)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    if args.action == "development":
        # Development's existing combined capture includes the prior value.
        record = model(args.upstream_root, args.pulse, args.prior_trial, "both")
        observed, target_sha = output_rows(args.result, args.pulse, "both")
        errors = compare(record["predictions"], observed)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "updates": len(observed), "errors": errors,
                          "target_sha256": target_sha}, indent=2))
        assert not errors
    elif args.action == "freeze":
        assert not args.result.exists(), "prediction already frozen"
        record = model(args.upstream_root, args.pulse, args.prior_trial)
        args.result.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"status": "FROZEN", "updates": len(record["predictions"]),
                          "sha256": sha(args.result)}))
    else:
        frozen = json.loads(args.result.read_text())
        assert frozen == model(args.upstream_root, args.pulse, args.prior_trial)
        assert args.target is not None
        observed, target_sha = output_rows(args.target, args.pulse, "output")
        errors = compare(frozen["predictions"], observed)
        print(json.dumps({"status": "PASS" if not errors else "FAIL",
                          "updates": len(observed), "matched_fields": 40 - 2 * len(errors),
                          "errors": errors, "frozen_sha256": sha(args.result),
                          "target_debug_sha256": target_sha}, indent=2))
        assert not errors


if __name__ == "__main__":
    main()
