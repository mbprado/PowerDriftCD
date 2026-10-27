#!/usr/bin/env python3
"""Predict successive arcade $7A/$7C updates with one-stage $7C carry."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16
from phase1b_state7c_predict import step


A = re.compile(r"CARRY_A pc=034DDA sign88=([0-9A-F]{4}) "
               r"old7a=([0-9A-F]{4}) old7c=([0-9A-F]{4})")
B = re.compile(r"CARRY_B pc=034E24 word86=([0-9A-F]{4}) "
               r"word24=([0-9A-F]{4}) word8a=([0-9A-F]{4}) "
               r"flag69=([0-9A-F]{2})")
TARGET = re.compile(r"CARRY_TARGET pc=034EF4 new7a=([0-9A-F]{4}) "
                    r"new7c=([0-9A-F]{4})")


def predict(root, pulse):
    source = root / f"state7c-carry-inputs-{pulse}/debug.log"
    rom_path = root.parent / "phase1b-code-pilot/pdrift-maincpu.bin"
    rom = rom_path.read_bytes()
    assert len(rom) == 0x80000
    a_rows = events(source, A)
    b_rows = events(source, B)
    old7a, old7c = a_rows[0][1][1:]
    initial = {"old7a": old7a, "old7c": old7c}
    rows = []
    for (frame_a, (sign88, _observed_old7a, _observed_old7c)), \
            (frame_b, (word86, word24, word8a, flag69)) in zip(a_rows, b_rows):
        assert frame_a == frame_b
        source_half = signed16(old7c) >> 1
        if signed16(sign88) < 0:
            source_half = signed16(-source_half)
        delta = signed16(source_half - old7a)
        delta = max(-0x20, min(0x20, delta))
        old7a = (old7a + delta) & 0xffff
        result = step(rom, word86, old7a, word24, word8a, old7c, flag69)
        old7c = result["predicted_new7c"]
        rows.append({"frame": frame_a, "sign88": sign88,
                     "word86": word86, "word24": word24,
                     "word8a": word8a, "flag69": flag69,
                     "predicted_new7a": old7a,
                     "predicted_new7c": old7c,
                     "state7c_branch": result["branch"]})
    return {"schema": 1, "pulse": pulse,
            "input_trace_sha256": sha(source), "rom_sha256": sha(rom_path),
            "initial": initial, "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=200)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    path = root / f"state7c-carry-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = predict(root, args.pulse)
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen carry predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record == predict(root, args.pulse), "inputs or model changed after freeze"
    target_path = root / f"state7c-carry-targets-{args.pulse}/debug.log"
    targets = events(target_path, TARGET)
    assert len(targets) == len(record["predictions"])
    differences = []
    exact = {"7a": 0, "7c": 0}
    for row, (frame, (observed7a, observed7c)) in zip(record["predictions"], targets):
        assert row["frame"] == frame, "callback misalignment"
        for field, observed in (("7a", observed7a), ("7c", observed7c)):
            predicted = row[f"predicted_new{field}"]
            if observed == predicted:
                exact[field] += 1
            else:
                differences.append({"frame": frame, "field": field,
                                    "predicted": predicted, "observed": observed})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(target_path),
              "count": len(targets), "exact_by_field": exact,
              "differences": differences}
    out = root / f"state7c-carry-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out carry:", exact, "of", len(targets),
          "differences:", len(differences))


if __name__ == "__main__":
    main()
