#!/usr/bin/env python3
"""Predict the arcade state word at $0C08BA from its pre-update inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import re


FRAME = re.compile(r"UPSTREAM_FRAME,(\d+)")
INPUT = re.compile(r"STATE_INPUT pc=034DDA a5=0C0840 old7a=([0-9A-F]{4}) "
                   r"source7c=([0-9A-F]{4}) sign88=([0-9A-F]{4})")
TARGET = re.compile(r"STATE_TARGET pc=034E0A a5=0C0840 new7a=([0-9A-F]{4})")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed16(value):
    value &= 0xffff
    return value - 0x10000 if value & 0x8000 else value


def events(path, pattern):
    frame = None
    result = []
    for line in path.read_text().splitlines():
        marker = FRAME.search(line)
        if marker:
            frame = int(marker.group(1))
        hit = pattern.search(line)
        if hit:
            assert frame is not None
            result.append((frame, tuple(int(item, 16) for item in hit.groups())))
    assert [frame for frame, _ in result] == list(range(961, 1000, 2))
    return result


def predict(root, pulse):
    log = root / f"state-inputs-{pulse}/debug.log"
    rows = []
    for frame, (old, source, sign) in events(log, INPUT):
        half = signed16(source) >> 1
        if signed16(sign) < 0:
            half = signed16(-half)
        delta = signed16(half - old)
        delta = max(-0x20, min(0x20, delta))
        result = (old + delta) & 0xffff
        rows.append({"frame": frame, "old7a": old, "source7c": source,
                     "sign88": sign, "delta": delta, "predicted_new7a": result})
    return {"schema": 1, "pulse": pulse, "input_trace_sha256": sha(log),
            "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=208)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen state predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    observed_path = root / f"state-targets-{args.pulse}/debug.log"
    observed = events(observed_path, TARGET)
    differences = []
    for row, (frame, (value,)) in zip(record["predictions"], observed):
        assert frame == row["frame"]
        if value != row["predicted_new7a"]:
            differences.append({"frame": frame, "predicted": row["predicted_new7a"],
                                "observed": value})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(observed_path),
              "count": len(observed), "exact": len(observed) - len(differences),
              "differences": differences}
    out = root / f"state-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out state:", result["exact"], "/", result["count"],
          "exact; differences:", len(differences))


if __name__ == "__main__":
    main()
