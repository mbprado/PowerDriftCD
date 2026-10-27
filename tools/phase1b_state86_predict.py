#!/usr/bin/env python3
"""Predict the arcade $0C08C6 word from the earlier prepared $8A state."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16


INPUT = re.compile(r"STATE86_INPUT pc=034D44 a5=0C0840 "
                   r"word8a=([0-9A-F]{4}) word24=([0-9A-F]{4}) "
                   r"word80=([0-9A-F]{4}) old86=([0-9A-F]{4}) "
                   r"flag91=([0-9A-F]{2})")
TARGET = re.compile(r"STATE86_TARGET pc=034DA4 a5=0C0840 "
                    r"new86=([0-9A-F]{4})")


def predict(root, pulse):
    source = root / f"state86-inputs-{pulse}-corrected/debug.log"
    rows = []
    for frame, (word8a, word24, word80, old86, flag91) in events(source, INPUT):
        retained = word24 == 0 or bool(flag91 & 1)
        desired = signed16(-word8a)
        if -8 < desired < 8:
            desired = 0
        if word80:
            desired = signed16(desired) >> 1
        limit = max(1, abs(signed16(desired)) >> 1)
        delta = signed16(desired - old86)
        delta = max(-limit, min(limit, delta))
        result = old86 if retained else (old86 + delta) & 0xffff
        rows.append({"frame": frame, "word8a": word8a, "word24": word24,
                     "word80": word80, "old86": old86, "flag91": flag91,
                     "retained": retained, "desired": desired,
                     "step_limit": limit, "delta": 0 if retained else delta,
                     "predicted_new86": result})
    return {"schema": 1, "pulse": pulse,
            "input_trace_sha256": sha(source), "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=216)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state86-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen $86 predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    target_path = root / f"state86-targets-{args.pulse}/debug.log"
    observed = events(target_path, TARGET)
    differences = []
    for row, (frame, (value,)) in zip(record["predictions"], observed):
        assert frame == row["frame"]
        if value != row["predicted_new86"]:
            differences.append({"frame": frame, "predicted": row["predicted_new86"],
                                "observed": value})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(target_path),
              "count": len(observed), "exact": len(observed) - len(differences),
              "differences": differences}
    out = root / f"state86-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out $86:", result["exact"], "/", result["count"],
          "exact; differences:", len(differences))


if __name__ == "__main__":
    main()
