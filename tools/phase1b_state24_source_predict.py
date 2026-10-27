#!/usr/bin/env python3
"""Predict the exercised $24 desired/limit branch from earlier state."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16
from phase1b_state24_predict import INPUT as SMOOTHER_INPUT, TARGET as STATE24_TARGET


SOURCE = re.compile(r"STATE24_SOURCE pc=0343C4 "
                    r"flag26=([0-9A-F]{2}) flag54=([0-9A-F]{2}) "
                    r"flag55=([0-9A-F]{2}) flag47=([0-9A-F]{2}) "
                    r"word80=([0-9A-F]{4}) word8c=([0-9A-F]{4}) "
                    r"flag69=([0-9A-F]{2}) flag5e=([0-9A-F]{2}) "
                    r"word8e=([0-9A-F]{4}) oldglobal=([0-9A-F]{4})")
SOURCE_TARGET = re.compile(r"STATE24_SOURCE_TARGET pc=034478 "
                           r"desired=([0-9A-F]{4}) limit=([0-9A-F]{4})")


def predict(source):
    inputs = events(source, SOURCE)
    global_word = inputs[0][1][-1]
    rows = []
    for frame, (flag26, flag54, flag55, flag47, word80, word8c,
                flag69, flag5e, word8e, _observed_global) in inputs:
        if flag26 & 1 or not (flag54 or flag55 or flag47 or word80):
            desired = signed16(word8c)
            if not flag69 & 0x20:
                desired = signed16(desired + (desired >> 1))
            if flag5e:
                desired = signed16(desired >> 1)
                desired = signed16(desired + (desired >> 2))
            path = "word8c"
        else:
            desired = 20
            path = "constant20"
        assert desired <= signed16(global_word), "ROM-table branch not modeled"
        assert signed16(word8e) < 20, "multiplier branch not modeled"
        limit = 3
        delta = signed16(desired - global_word)
        delta = max(-limit, min(limit, delta))
        global_word = (global_word + delta) & 0xffff
        rows.append({"frame": frame, "path": path, "flag5e": flag5e,
                     "predicted_desired": desired & 0xffff,
                     "predicted_limit": limit,
                     "predicted_new24": global_word})
    return {"initial_global": inputs[0][1][-1], "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("development", "predict", "validate"))
    parser.add_argument("--pulse", type=int, default=180)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    if args.mode == "development":
        result = predict(root / "state24-source-dev-188/debug.log")
        earlier = events(root / "state24-inputs-188/debug.log", SMOOTHER_INPUT)
        target = events(root / "state24-targets-188/debug.log", STATE24_TARGET)
        exact_operands = exact_output = 0
        for row, (frame_i, (desired, limit, oldglobal)), \
                (frame_t, (new24,)) in zip(result["predictions"], earlier, target):
            assert row["frame"] == frame_i == frame_t
            exact_operands += (row["predicted_desired"], row["predicted_limit"]) == \
                              (desired, limit)
            exact_output += row["predicted_new24"] == new24
        print("development D0/D1:", exact_operands, "/", len(earlier),
              "$24:", exact_output, "/", len(target))
        return
    source = root / f"state24-source-inputs-{args.pulse}/debug.log"
    path = root / f"state24-source-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = {"schema": 1, "pulse": args.pulse,
                  "input_trace_sha256": sha(source)}
        record.update(predict(source))
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen source predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record["input_trace_sha256"] == sha(source)
    assert {key: record[key] for key in ("initial_global", "predictions")} == predict(source)
    operands_path = root / f"state24-source-targets-{args.pulse}/debug.log"
    state_path = root / f"state24-targets-{args.pulse}/debug.log"
    operands = events(operands_path, SOURCE_TARGET)
    states = events(state_path, STATE24_TARGET)
    assert len(operands) == len(states) == len(record["predictions"])
    differences = []
    for row, (frame_o, (desired, limit)), (frame_s, (new24,)) in zip(
            record["predictions"], operands, states):
        assert row["frame"] == frame_o == frame_s, "callback misalignment"
        for field, actual in (("desired", desired), ("limit", limit),
                              ("new24", new24)):
            expected = row[f"predicted_{field}"]
            if expected != actual:
                differences.append({"frame": row["frame"], "field": field,
                                    "predicted": expected, "observed": actual})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "operands_trace_sha256": sha(operands_path),
              "state_trace_sha256": sha(state_path),
              "count": len(states), "differences": differences}
    out = root / f"state24-source-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out source:", len(states) * 3 - len(differences), "/",
          len(states) * 3, "field values; differences:", len(differences))


if __name__ == "__main__":
    main()
