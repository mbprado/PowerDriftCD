#!/usr/bin/env python3
"""Predict the exercised $24/$8A -> $86/$88/$7A/$7C chain."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16
from phase1b_state7c_predict import step as state7c_step


INIT = re.compile(r"FORWARD_INIT pc=0374D0 old86=([0-9A-F]{4}) "
                  r"old88=([0-9A-F]{4}) old7a=([0-9A-F]{4}) "
                  r"old7c=([0-9A-F]{4})")
BRANCH = re.compile(r"FORWARD_BRANCH pc=034D44 word80=([0-9A-F]{4}) "
                    r"flag91=([0-9A-F]{2})")
FLAG = re.compile(r"FORWARD_FLAG pc=034E24 flag69=([0-9A-F]{2})")
TARGET = re.compile(r"FORWARD_TARGET pc=034EF4 word86=([0-9A-F]{4}) "
                    r"word88=([0-9A-F]{4}) word7a=([0-9A-F]{4}) "
                    r"word7c=([0-9A-F]{4})")


def bounded(value, limit):
    return max(-limit, min(limit, value))


def predict(root, pulse):
    source = root / f"state24-forward-inputs-{pulse}/debug.log"
    rom_path = root.parent / "phase1b-code-pilot/pdrift-maincpu.bin"
    rom = rom_path.read_bytes()
    assert len(rom) == 0x80000
    state24_path = root / f"state24-source-prediction-{pulse}.json"
    state8a_path = root / f"state8a-prediction-{pulse}.json"
    state24 = json.loads(state24_path.read_text())
    state8a = json.loads(state8a_path.read_text())
    assert state24["pulse"] == state8a["pulse"] == pulse
    init = events(source, INIT)
    branch = events(source, BRANCH)
    flags = events(source, FLAG)
    assert len(state24["predictions"]) == len(state8a["predictions"]) == 20
    old86, old88, old7a, old7c = init[0][1]
    initial = {"86": old86, "88": old88, "7a": old7a, "7c": old7c}
    rows = []
    for (frame, _), (f_b, (word80, flag91)), (f_f, (flag69,)), \
            upstream24, upstream8a in zip(init, branch, flags,
                                          state24["predictions"],
                                          state8a["predictions"]):
        assert frame == f_b == f_f == upstream24["frame"] == upstream8a["frame"]
        word24 = upstream24["predicted_new24"]
        word8a = upstream8a["predicted_new8a"]
        if word24 and not flag91 & 1:
            desired = signed16(-word8a)
            if -8 < desired < 8:
                desired = 0
            if word80:
                desired = signed16(desired) >> 1
            limit = max(1, abs(signed16(desired)) >> 1)
            old86 = (old86 + bounded(signed16(desired - old86), limit)) & 0xffff
        half = signed16(old86) >> 1
        quotient = abs(half) // 8
        quotient = -quotient if half < 0 else quotient
        limit = quotient if quotient > 0 else max(1, -quotient)
        old88 = (old88 + bounded(signed16(half - old88), limit)) & 0xffff
        half7c = signed16(old7c) >> 1
        if signed16(old88) < 0:
            half7c = signed16(-half7c)
        old7a = (old7a + bounded(signed16(half7c - old7a), 0x20)) & 0xffff
        state7c = state7c_step(rom, old86, old7a, word24, word8a,
                               old7c, flag69)
        old7c = state7c["predicted_new7c"]
        rows.append({"frame": frame, "predicted_24": word24,
                     "predicted_8a": word8a, "word80": word80,
                     "flag91": flag91, "flag69": flag69,
                     "predicted_86": old86, "predicted_88": old88,
                     "predicted_7a": old7a, "predicted_7c": old7c,
                     "state7c_branch": state7c["branch"]})
    return {"schema": 1, "pulse": pulse,
            "input_trace_sha256": sha(source), "rom_sha256": sha(rom_path),
            "source24_prediction_sha256": sha(state24_path),
            "source8a_prediction_sha256": sha(state8a_path),
            "initial": initial, "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=180)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state24-forward-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen forward predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    target_path = root / f"state24-forward-targets-{args.pulse}/debug.log"
    targets = events(target_path, TARGET)
    assert len(targets) == len(record["predictions"])
    differences = []
    exact = {field: 0 for field in ("86", "88", "7a", "7c")}
    for row, (frame, values) in zip(record["predictions"], targets):
        assert row["frame"] == frame, "callback misalignment"
        for field, actual in zip(exact, values):
            expected = row[f"predicted_{field}"]
            if expected == actual:
                exact[field] += 1
            else:
                differences.append({"frame": frame, "field": field,
                                    "predicted": expected, "observed": actual})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path), "target_trace_sha256": sha(target_path),
              "count": len(targets), "exact_by_field": exact,
              "differences": differences}
    out = root / f"state24-forward-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out forward:", exact, "of", len(targets),
          "differences:", len(differences))


if __name__ == "__main__":
    main()
