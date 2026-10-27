#!/usr/bin/env python3
"""Predict arcade $8A copies from earlier steering bytes and initial state."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16


INPUT = re.compile(r"STATE8A_INPUT pc=0374D0 a5=0C0040 "
                   r"raw=([0-9A-F]{2}) old16=([0-9A-F]{4}) "
                   r"old18=([0-9A-F]{4}) oldglobal=([0-9A-F]{4})")
TARGET = re.compile(r"STATE8A_TARGET pc=033922 a0=0C0840 "
                    r"new8a=([0-9A-F]{4})")


def predict(root, pulse):
    source = root / f"state8a-inputs-{pulse}-corrected/debug.log"
    inputs = events(source, INPUT)
    previous, accumulator, global_word = inputs[0][1][1:]
    rows = []
    for frame, (raw, _old16, _old18, _oldglobal) in inputs:
        clamped = max(53, min(203, raw))
        change = signed16(clamped - previous)
        previous = clamped
        accumulator = signed16(accumulator + change)
        recalculated = abs(accumulator) > 2
        if recalculated:
            accumulator = 0
            dividend = signed16(clamped - 128) * 256
            quotient = abs(dividend) // 150
            quotient = -quotient if dividend < 0 else quotient
            global_word = max(-127, min(127, quotient)) & 0xffff
        rows.append({"frame": frame, "raw_steering": raw,
                     "recalculated": recalculated,
                     "predicted_new8a": global_word})
    return {"schema": 1, "pulse": pulse, "input_trace_sha256": sha(source),
            "initial_previous": inputs[0][1][1],
            "initial_accumulator": inputs[0][1][2],
            "initial_global": inputs[0][1][3], "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=176)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state8a-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen $8A predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    observed_path = root / f"state8a-targets-{args.pulse}/debug.log"
    observed = events(observed_path, TARGET)
    assert len(observed) == len(record["predictions"])
    differences = []
    for row, (frame, (value,)) in zip(record["predictions"], observed):
        assert frame == row["frame"], "callback misalignment"
        if value != row["predicted_new8a"]:
            differences.append({"frame": frame, "predicted": row["predicted_new8a"],
                                "observed": value})
    result = {"schema": 1, "pulse": args.pulse, "prediction_sha256": sha(path),
              "target_trace_sha256": sha(observed_path),
              "count": len(observed), "exact": len(observed) - len(differences),
              "differences": differences}
    out = root / f"state8a-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out $8A:", result["exact"], "/", result["count"],
          "exact; differences:", len(differences))


if __name__ == "__main__":
    main()
