#!/usr/bin/env python3
"""Run the known $8A->$86->$88->$7A state chain forward for pulse 80."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16


INIT = re.compile(r"CHAIN_INIT pc=0374D0 raw=([0-9A-F]{2}) "
                  r"old86=([0-9A-F]{4}) old88=([0-9A-F]{4}) "
                  r"old7a=([0-9A-F]{4})")
BRANCH = re.compile(r"CHAIN_BRANCH pc=034D44 word24=([0-9A-F]{4}) "
                    r"word80=([0-9A-F]{4}) flag91=([0-9A-F]{2})")
EXOGENOUS = re.compile(r"CHAIN_EXOGENOUS pc=034DDA word7c=([0-9A-F]{4})")
TARGET = re.compile(r"CHAIN_TARGET pc=034E0A word86=([0-9A-F]{4}) "
                    r"word88=([0-9A-F]{4}) word7a=([0-9A-F]{4})")


def clamp(value, limit):
    return max(-limit, min(limit, value))


def predict(root, pulse):
    input_path = root / f"state8a-chain-inputs-{pulse}/debug.log"
    init = events(input_path, INIT)
    branch = events(input_path, BRANCH)
    exogenous = events(input_path, EXOGENOUS)
    early_path = root / f"state8a-prediction-{pulse}.json"
    early = json.loads(early_path.read_text())
    assert early["pulse"] == pulse and len(early["predictions"]) == 20
    old86, old88, old7a = init[0][1][1:]
    rows = []
    for (frame, (raw, *_)), (f_branch, (word24, word80, flag91)), \
            (f_exo, (word7c,)), first in zip(init, branch, exogenous,
                                                early["predictions"]):
        assert frame == f_branch == f_exo == first["frame"]
        assert raw == first["raw_steering"]
        word8a = first["predicted_new8a"]
        if word24 != 0 and not (flag91 & 1):
            desired = signed16(-word8a)
            if -8 < desired < 8:
                desired = 0
            if word80:
                desired = signed16(desired) >> 1
            limit = max(1, abs(signed16(desired)) >> 1)
            old86 = (old86 + clamp(signed16(desired - old86), limit)) & 0xffff
        half = signed16(old86) >> 1
        quotient = abs(half) // 8
        quotient = -quotient if half < 0 else quotient
        limit = quotient if quotient > 0 else max(1, -quotient)
        old88 = (old88 + clamp(signed16(half - old88), limit)) & 0xffff
        half7c = signed16(word7c) >> 1
        if signed16(old88) < 0:
            half7c = signed16(-half7c)
        old7a = (old7a + clamp(signed16(half7c - old7a), 0x20)) & 0xffff
        rows.append({"frame": frame, "predicted_8a": word8a,
                     "exogenous_24": word24, "exogenous_80": word80,
                     "exogenous_91": flag91, "exogenous_7c": word7c,
                     "predicted_86": old86, "predicted_88": old88,
                     "predicted_7a": old7a})
    return {"schema": 1, "pulse": pulse,
            "chain_input_trace_sha256": sha(input_path),
            "early_prediction_sha256": sha(early_path),
            "initial_86": init[0][1][1], "initial_88": init[0][1][2],
            "initial_7a": init[0][1][3], "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=80)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state8a-chain-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen chain predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    target_path = root / f"state8a-chain-targets-{args.pulse}/debug.log"
    observed = events(target_path, TARGET)
    assert len(observed) == len(record["predictions"])
    differences = []
    exact = {"86": 0, "88": 0, "7a": 0}
    for row, (frame, values) in zip(record["predictions"], observed):
        assert frame == row["frame"], "callback misalignment"
        for field, value in zip(("86", "88", "7a"), values):
            predicted = row[f"predicted_{field}"]
            if value == predicted:
                exact[field] += 1
            else:
                differences.append({"frame": frame, "field": field,
                                    "predicted": predicted, "observed": value})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(target_path),
              "count": len(observed), "exact_by_field": exact,
              "differences": differences}
    out = root / f"state8a-chain-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out chain:", exact, "of", len(observed),
          "differences:", len(differences))


if __name__ == "__main__":
    main()
