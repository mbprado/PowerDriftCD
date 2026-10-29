#!/usr/bin/env python3
"""Predict one offset-source write from earlier position-chain inputs."""

import argparse
import csv
import json
import re
from pathlib import Path

from phase1b_position_chain_predict import PATTERNS, ROM_SHA256, compute, digest
from phase1b_position_math_predict import signed16
from phase1b_projection_replay import project


MARKER = 987
INPUT_CALLBACK = 988
TARGET_CALLBACK = 990
OBJECT = "0C1D00"
SOURCE = re.compile(r"UPSTREAM_WRITE cpu=maincpu field=offset_source pc=034C48 "
                    r"addr=0C00AE data=([0-9A-F]{8})")


def position_inputs(directory, pulse, end):
    control = (directory / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={pulse}" in control and "STATE_LOAD,950," in control
    assert "POSITION_CHAIN_ARMED,input" in control
    assert f"POSITION_CHAIN_CLEARED,{end}" in control
    data = (directory / "debug.log").read_text()
    assert "POSITION_CHAIN_OPERAND" not in data
    assert "POSITION_CHAIN_COEFFICIENT" not in data
    assert "POSITION_CHAIN_ADJUSTED" not in data
    found = {name: [] for name in ("pre", "index", "base")}
    marker = None
    for line in data.splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            marker = int(match[1])
        for name in found:
            match = PATTERNS[name].search(line)
            if match:
                found[name].append((marker, tuple(int(v, 16) for v in match.groups())))
    frames = list(range(961, end, 2))
    assert all([frame for frame, _ in found[name]] == frames for name in found)
    return found


def source_word(item, rom):
    index = int(item["index"], 16)
    address = 0x0CF6 + 2 * index
    assert address + 2 <= len(rom)
    coefficient = int.from_bytes(rom[address:address + 2], "big")
    operand = signed16(int(item["operand"], 16))
    # The hardware result is shifted as a long, then its low word is shifted.
    shifted_long = (operand * signed16(coefficient)) >> 9
    shifted_word = signed16(shifted_long & 0xFFFF)
    return coefficient, (shifted_word >> 4) & 0xFFFF


def geometry_row(path, callback):
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == (callback - 960 + 1) * 12
    assert max(int(row["frame"]) for row in rows) == callback
    selected = [row for row in rows if int(row["frame"]) == callback
                and row["object"] == OBJECT]
    assert len(selected) == 1
    return selected[0]


def predict(directory, rom_path, pulse):
    assert digest(rom_path) == ROM_SHA256
    inputs = position_inputs(directory, pulse, INPUT_CALLBACK)
    # Reuse the already validated operand model for this bounded path.
    items = compute(inputs, rom_path.read_bytes(),
                    frames=list(range(961, INPUT_CALLBACK, 2)))
    assert items[-1]["marker"] == MARKER
    coefficient, offset = source_word(items[-1], rom_path.read_bytes())
    geometry = directory / "geometry-samples.csv"
    row = geometry_row(geometry, INPUT_CALLBACK)
    projected = project(row, offset)
    assert projected is not None
    return {"schema": 1, "pulse": pulse, "input_marker": MARKER,
            "input_callback": INPUT_CALLBACK, "target_callback": TARGET_CALLBACK,
            "object": OBJECT, "input_debug_sha256": digest(directory / "debug.log"),
            "input_geometry_sha256": digest(geometry), "private_rom_sha256": ROM_SHA256,
            "operand": items[-1]["operand"], "index": items[-1]["index"],
            "offset_coefficient": f"{coefficient:04X}",
            "predicted_offset_source": f"{offset:04X}",
            "predicted_x": f"{projected[0] & 0xFFFF:04X}",
            "predicted_y": f"{projected[1] & 0xFFFF:04X}"}


def observed_source(path):
    marker = None
    values = []
    for line in path.read_text().splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            marker = int(match[1])
        match = SOURCE.search(line)
        if match:
            values.append((marker, int(match[1], 16) & 0xFFFF))
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    dev = sub.add_parser("development")
    dev.add_argument("input", type=Path)
    dev.add_argument("source_log", type=Path)
    dev.add_argument("rom", type=Path)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("input", type=Path)
    freeze.add_argument("rom", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--pulse", type=int, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("frozen", type=Path)
    validate.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.action == "development":
        from phase1b_position_chain_predict import trace
        inputs, _ = trace(args.input, "both", 204)
        rom = args.rom.read_bytes()
        predictions = compute(inputs, rom)
        observed = dict(observed_source(args.source_log))
        checked = [(item["marker"], source_word(item, rom)[1], observed[item["marker"]])
                   for item in predictions if item["marker"] in observed]
        assert len(checked) >= 5 and all(a == b for _, a, b in checked), checked
        print(json.dumps({"status": "PASS", "source_writes": len(checked),
                          "source_log_sha256": digest(args.source_log)}))
    elif args.action == "freeze":
        assert not args.output.exists()
        result = predict(args.input, args.rom, args.pulse)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": "FROZEN", "sha256": digest(args.output),
                          "offset": result["predicted_offset_source"],
                          "x": result["predicted_x"], "y": result["predicted_y"]}))
    else:
        frozen = json.loads(args.frozen.read_text())
        source = dict(observed_source(args.target / "debug.log"))
        assert MARKER in source
        geometry = geometry_row(args.target / "geometry-samples.csv", TARGET_CALLBACK)
        expected = [frozen["predicted_offset_source"], frozen["predicted_x"],
                    frozen["predicted_y"]]
        actual = [f"{source[MARKER]:04X}", geometry["projected4"],
                  geometry["projected6"]]
        result = {"status": "PASS" if expected == actual else "FAIL",
                  "expected": expected, "observed": actual,
                  "frozen_sha256": digest(args.frozen),
                  "target_debug_sha256": digest(args.target / "debug.log"),
                  "target_geometry_sha256": digest(args.target / "geometry-samples.csv")}
        print(json.dumps(result, indent=2))
        assert expected == actual


if __name__ == "__main__":
    main()
