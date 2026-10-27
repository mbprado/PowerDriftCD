#!/usr/bin/env python3
"""Predict arcade $24 from the earlier desired word, step limit and accumulator."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16


INPUT = re.compile(r"STATE24_INPUT pc=034478 a5=0C0840 "
                   r"desired=([0-9A-F]{4}) limit=([0-9A-F]{4}) "
                   r"oldglobal=([0-9A-F]{4})")
DEV_WRITE = re.compile(r"STATE24_WRITE pc=0344A0 addr=0C0864 "
                       r"data=([0-9A-F]{8})")
TARGET = re.compile(r"STATE24_TARGET pc=0344A0 a5=0C0840 "
                    r"new24=([0-9A-F]{4})")


def predict(source):
    rows = []
    for frame, (desired, limit, oldglobal) in events(source, INPUT):
        assert 0 <= signed16(limit) <= 0x7fff, "unmodeled limit sign"
        delta = signed16(desired - oldglobal)
        delta = max(-limit, min(limit, delta))
        rows.append({"frame": frame, "desired": desired, "limit": limit,
                     "oldglobal": oldglobal, "delta": delta,
                     "predicted_new24": (oldglobal + delta) & 0xffff})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("development", "predict", "validate"))
    parser.add_argument("--pulse", type=int, default=188)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    if args.mode == "development":
        rows = predict(root / "state24-inputs-200/debug.log")
        observed = events(root / "state24-writes-200/debug.log", DEV_WRITE)
        assert len(observed) == len(rows)
        exact = sum(row["frame"] == frame and row["predicted_new24"] == value
                    for row, (frame, (value,)) in zip(rows, observed))
        print("development $24:", exact, "/", len(rows))
        return
    source = root / f"state24-inputs-{args.pulse}/debug.log"
    path = root / f"state24-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = {"schema": 1, "pulse": args.pulse,
                  "input_trace_sha256": sha(source),
                  "predictions": predict(source)}
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen $24 predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record["input_trace_sha256"] == sha(source)
    assert record["predictions"] == predict(source)
    target_path = root / f"state24-targets-{args.pulse}/debug.log"
    observed = events(target_path, TARGET)
    assert len(observed) == len(record["predictions"])
    differences = []
    for row, (frame, (value,)) in zip(record["predictions"], observed):
        assert row["frame"] == frame, "callback misalignment"
        if row["predicted_new24"] != value:
            differences.append({"frame": frame,
                                "predicted": row["predicted_new24"],
                                "observed": value})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(target_path),
              "count": len(observed), "exact": len(observed) - len(differences),
              "differences": differences}
    out = root / f"state24-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out $24:", result["exact"], "/", len(observed),
          "differences:", len(differences))


if __name__ == "__main__":
    main()
