#!/usr/bin/env python3
"""Predict the arcade $0C08C8 state word from pre-update $86 and old $88."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16


INPUT = re.compile(r"STATE88_INPUT pc=034DA4 a5=0C0840 "
                   r"source86=([0-9A-F]{4}) old88=([0-9A-F]{4})")
TARGET = re.compile(r"STATE88_TARGET pc=034DDA a5=0C0840 "
                    r"new88=([0-9A-F]{4})")


def predict(root, pulse):
    source = root / f"state88-inputs-{pulse}/debug.log"
    rows = []
    for frame, (word86, old88) in events(source, INPUT):
        half = signed16(word86) >> 1
        quotient = (abs(half) // 8) * (1 if half >= 0 else -1)
        limit = quotient if quotient > 0 else max(1, -quotient)
        delta = signed16(half - old88)
        delta = max(-limit, min(limit, delta))
        rows.append({"frame": frame, "source86": word86, "old88": old88,
                     "half": half, "signed_quotient": quotient,
                     "limit": limit, "delta": delta,
                     "predicted_new88": (old88 + delta) & 0xffff})
    return {"schema": 1, "pulse": pulse,
            "input_trace_sha256": sha(source), "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=40)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state88-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen $88 predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    target_path = root / f"state88-targets-{args.pulse}/debug.log"
    observed = events(target_path, TARGET)
    differences = []
    for row, (frame, (value,)) in zip(record["predictions"], observed):
        assert frame == row["frame"]
        if value != row["predicted_new88"]:
            differences.append({"frame": frame, "predicted": row["predicted_new88"],
                                "observed": value})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(target_path),
              "count": len(observed), "exact": len(observed) - len(differences),
              "differences": differences}
    out = root / f"state88-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out $88:", result["exact"], "/", result["count"],
          "exact; differences:", len(differences))


if __name__ == "__main__":
    main()
