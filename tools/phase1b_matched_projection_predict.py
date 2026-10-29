#!/usr/bin/env python3
"""Freeze and validate a one-update arcade projection prediction."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from phase1b_projection_replay import project, signed16


INPUT_CALLBACK = 988
TARGET_CALLBACK = 990
OBJECT = "0C1D00"
PULSE = 88


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(path, frame):
    rows = list(csv.DictReader(path.open()))
    if frame == INPUT_CALLBACK:
        assert len(rows) == (INPUT_CALLBACK - 960 + 1) * 12
        assert max(int(item["frame"]) for item in rows) == INPUT_CALLBACK
    matches = [item for item in rows
               if int(item["frame"]) == frame and item["object"] == OBJECT]
    assert len(matches) == 1
    return matches[0]


def calculate(input_dir):
    geometry = input_dir / "geometry-samples.csv"
    offset_file = input_dir / f"projection-input-{INPUT_CALLBACK:04d}.csv"
    source = row(geometry, INPUT_CALLBACK)
    offsets = list(csv.DictReader(offset_file.open()))
    assert len(offsets) == 1 and offsets[0]["callback"] == str(INPUT_CALLBACK)
    offset = int(offsets[0]["offset_source"], 16)
    predicted = project(source, offset)
    assert predicted is not None
    return {"schema": 1, "pulse": PULSE, "object": OBJECT,
            "input_callback": INPUT_CALLBACK, "target_callback": TARGET_CALLBACK,
            "input_geometry_sha256": digest(geometry),
            "input_offset_sha256": digest(offset_file),
            "offset_source": f"{offset:04X}",
            "prior_horizontal_offset": offsets[0]["prior_horizontal_offset"],
            "source_table": source["table"],
            "source16": source["source16"], "source18": source["source18"],
            "source1a": source["source1a"],
            "predicted_x": f"{predicted[0] & 0xffff:04X}",
            "predicted_y": f"{predicted[1] & 0xffff:04X}"}


def freeze(input_dir, output):
    assert not output.exists(), "prediction already frozen"
    result = calculate(input_dir)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("frozen", result["predicted_x"], result["predicted_y"], output)
    print("sha256", digest(output))


def validate(input_dir, prediction, target_dirs):
    frozen = json.loads(prediction.read_text())
    assert frozen == calculate(input_dir), "frozen input or model changed"
    expected = (int(frozen["predicted_x"], 16), int(frozen["predicted_y"], 16))
    results = []
    for directory in target_dirs:
        path = directory / "geometry-samples.csv"
        target = row(path, TARGET_CALLBACK)
        observed = (int(target["projected4"], 16),
                    int(target["projected6"], 16))
        difference = (signed16(observed[0] - expected[0]),
                      signed16(observed[1] - expected[1]))
        results.append({"directory": str(directory), "geometry_sha256": digest(path),
                        "observed_x": f"{observed[0]:04X}",
                        "observed_y": f"{observed[1]:04X}",
                        "difference_x": difference[0], "difference_y": difference[1]})
    assert len({(item["observed_x"], item["observed_y"])
                for item in results}) == 1, "target runs disagree"
    assert all(item["difference_x"] == item["difference_y"] == 0
               for item in results), "held-out prediction failed"
    print(json.dumps({"prediction_sha256": digest(prediction),
                      "target_runs": results}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "validate"))
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("prediction", type=Path)
    parser.add_argument("targets", nargs="*", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        assert not args.targets
        freeze(args.input_dir, args.prediction)
    else:
        assert len(args.targets) == 3
        validate(args.input_dir, args.prediction, args.targets)


if __name__ == "__main__":
    main()
