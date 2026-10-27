#!/usr/bin/env python3
"""Predict the arcade $7C producer from earlier state and a private ROM table."""

import argparse
import json
from pathlib import Path
import re

from phase1b_state7a_predict import events, sha, signed16


INPUT = re.compile(r"STATE7C_INPUT pc=034E24 a5=0C0840 "
                   r"word86=([0-9A-F]{4}) word7a=([0-9A-F]{4}) "
                   r"word24=([0-9A-F]{4}) word8a=([0-9A-F]{4}) "
                   r"old7c=([0-9A-F]{4}) flag69=([0-9A-F]{2})")
INTERMEDIATE = re.compile(r"STATE7C_INTERMEDIATE pc=034E5A d0=([0-9A-F]{8})")
DEV_TARGET = re.compile(r"STATE7C_DEV_TARGET pc=034EF4 new7c=([0-9A-F]{4})")
TARGET = re.compile(r"STATE7C_TARGET pc=034EF4 new7c=([0-9A-F]{4})")


def divs(dividend, divisor):
    quotient = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        quotient = -quotient
    assert -32768 <= quotient <= 32767, "unmodeled DIVS overflow"
    remainder = dividend - quotient * divisor
    return quotient, remainder


def step(rom, word86, word7a, word24, word8a, old7c, flag69):
    index = signed16(word86 + word7a)
    address = 0x0ef6 + signed16(index * 2)
    assert 0 <= address < len(rom) - 1 and address % 2 == 0
    table = int.from_bytes(rom[address:address + 2], "big", signed=True)
    # The assembly doubles the table-plus-half value, then adds that same word.
    doubled = signed16((table + (table >> 1)) * 2)
    value = signed16(doubled + doubled)
    q1, _ = divs(value * signed16(480 - word24), 480)
    q2, rem2 = divs(signed16(q1) * signed16(word24), 2560)
    d0 = signed16(q2)
    threshold_base = signed16(word24 - 160)
    branch = "decay"
    result = old7c
    if threshold_base > 0:
        extra = signed16(abs(signed16(word8a)) - 64)
        if extra > 0:
            threshold = signed16(threshold_base + extra)
            threshold = signed16(-threshold + 224)
            threshold = signed16((threshold >> 1) + 20)
            if d0 > threshold or d0 < -threshold:
                branch = "grow"
                magnitude = abs(signed16(word86))
                if signed16(word24) > 280 and (flag69 & 0x20):
                    magnitude = signed16(magnitude + (magnitude >> 1))
                    increment = magnitude >> 2
                else:
                    increment = magnitude >> 5
                result = min(signed16(old7c + increment), magnitude) & 0xffff
    if branch == "decay":
        result = max(0, signed16(old7c - 32)) & 0xffff
    return {"table_address": address, "table_word": table,
            "divide_quotient": d0, "divide_remainder": rem2,
            "branch": branch, "predicted_new7c": result}


def predictions(source, rom):
    rows = []
    for frame, words in events(source, INPUT):
        row = {"frame": frame, "input_words": list(words)}
        row.update(step(rom, *words))
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("development", "predict", "validate"))
    parser.add_argument("--pulse", type=int, default=224)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    rom_path = root.parent / "phase1b-code-pilot/pdrift-maincpu.bin"
    rom = rom_path.read_bytes()
    assert len(rom) == 0x80000
    if args.mode == "development":
        source = root / "state7c-dev-208/debug.log"
        rows = predictions(source, rom)
        intermediate = events(source, INTERMEDIATE)
        targets = events(source, DEV_TARGET)
        exact_div = exact_target = 0
        for row, (frame_d, (full_d0,)), (frame_t, (observed,)) in zip(
                rows, intermediate, targets):
            assert row["frame"] == frame_d == frame_t
            modeled_d0 = ((row["divide_remainder"] & 0xffff) << 16) | \
                         (row["divide_quotient"] & 0xffff)
            exact_div += modeled_d0 == full_d0
            exact_target += row["predicted_new7c"] == observed
        print("development divider:", exact_div, "/", len(rows),
              "target:", exact_target, "/", len(rows))
        return
    source = root / f"state7c-inputs-{args.pulse}/debug.log"
    path = root / f"state7c-prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not path.exists(), "prediction already frozen; do not overwrite"
        record = {"schema": 1, "pulse": args.pulse,
                  "input_trace_sha256": sha(source), "rom_sha256": sha(rom_path),
                  "predictions": predictions(source, rom)}
        path.write_text(json.dumps(record, indent=2) + "\n")
        print("frozen $7C predictions:", len(record["predictions"]), sha(path))
        return
    record = json.loads(path.read_text())
    assert record["input_trace_sha256"] == sha(source)
    assert record["rom_sha256"] == sha(rom_path)
    assert record["predictions"] == predictions(source, rom)
    target_path = root / f"state7c-targets-{args.pulse}/debug.log"
    targets = events(target_path, TARGET)
    assert len(targets) == len(record["predictions"])
    differences = []
    for row, (frame, (observed,)) in zip(record["predictions"], targets):
        assert row["frame"] == frame, "callback misalignment"
        if row["predicted_new7c"] != observed:
            differences.append({"frame": frame,
                                "predicted": row["predicted_new7c"],
                                "observed": observed})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(path),
              "target_trace_sha256": sha(target_path),
              "count": len(targets), "exact": len(targets) - len(differences),
              "differences": differences}
    out = root / f"state7c-validation-{args.pulse}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out $7C:", result["exact"], "/", len(targets),
          "differences:", len(differences))


if __name__ == "__main__":
    main()
