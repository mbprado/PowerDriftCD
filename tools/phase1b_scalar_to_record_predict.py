#!/usr/bin/env python3
"""Predict one road-like projected record using a carried position operand."""

import argparse
import csv
import hashlib
import json
import re
import struct
from pathlib import Path

from phase1b_position_chain_predict import ROM_SHA256, signed16
from phase1b_projection_replay import project


PULSE = 212
SOURCE_MARKER = 987
INPUT_CALLBACK = 988
TARGET_CALLBACK = 990
OBJECT = "0C1D00"
LIST_OFFSET = 0x240


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(path, frame):
    rows = list(csv.DictReader(path.open()))
    matches = [item for item in rows if item["frame"] == str(frame)
               and item["object"] == OBJECT]
    assert len(matches) == 1
    return matches[0], rows


def marker_inputs(path):
    data = path.read_text()
    assert "POSITION_CHAIN_OPERAND" not in data
    assert "POSITION_CHAIN_ADJUSTED" not in data
    marker = None
    index = []
    base = []
    for line in data.splitlines():
        found = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if found:
            marker = int(found[1])
        found = re.search(r"POSITION_CHAIN_INDEX pc=034B02 d1=([0-9A-F]{8})", line)
        if found and marker == SOURCE_MARKER:
            index.append(int(found[1], 16) & 0xFFFF)
        found = re.search(r"POSITION_CHAIN_BASE pc=034C1C base=([0-9A-F]{4})", line)
        if found and marker == SOURCE_MARKER:
            base.append(int(found[1], 16))
    assert len(index) == len(base) == 1
    return index[0], base[0]


def calculate(input_dir, carry_file, rom_path):
    assert digest(rom_path) == ROM_SHA256
    control = input_dir / "phase1b-input.log"
    control_text = control.read_text(errors="replace")
    assert f"STEER_PULSE={PULSE}" in control_text
    assert "POSITION_CHAIN_ARMED,input" in control_text
    assert "POSITION_CHAIN_CLEARED,988" in control_text
    assert "BRIDGE_INPUT_MASKED,988,global1c+projected4+projected6" in control_text
    assert "LUA ERROR" not in control_text
    geometry = input_dir / "geometry-samples.csv"
    source, rows = row(geometry, INPUT_CALLBACK)
    assert max(int(item["frame"]) for item in rows) == INPUT_CALLBACK
    assert (source["global1c"], source["projected4"],
            source["projected6"]) == ("0000", "0000", "0000")
    carry = json.loads(carry_file.read_text())
    assert carry["pulse"] == PULSE and carry["private_rom_sha256"] == ROM_SHA256
    operands = [item for item in carry["predictions"]
                if item["marker"] == SOURCE_MARKER]
    assert len(operands) == 1
    operand = int(operands[0]["predicted_new28"], 16)
    index, base = marker_inputs(input_dir / "debug.log")
    rom = rom_path.read_bytes()
    coefficient = int.from_bytes(rom[0x0EF6 + index * 2:
                                     0x0EF8 + index * 2], "big")
    adjusted = (base + ((signed16(operand) * signed16(coefficient)) >> 9)) & 0xFFFF
    translation = (-adjusted) & 0xFFFF
    projection_input = input_dir / "projection-input-0988.csv"
    offsets = list(csv.DictReader(projection_input.open()))
    assert len(offsets) == 1 and offsets[0]["callback"] == "988"
    offset_source = int(offsets[0]["offset_source"], 16)
    prepared = dict(source, global1c=f"{translation:04X}")
    coordinates = project(prepared, offset_source)
    assert coordinates is not None
    return {
        "schema": 1, "pulse": PULSE, "object": OBJECT,
        "source_marker": SOURCE_MARKER, "input_callback": INPUT_CALLBACK,
        "target_callback": TARGET_CALLBACK, "shared_list_offset": f"{LIST_OFFSET:04X}",
        "carried_operand": f"{operand:04X}", "index": f"{index:04X}",
        "base": f"{base:04X}", "coefficient": f"{coefficient:04X}",
        "predicted_adjusted": f"{adjusted:04X}",
        "predicted_translation": f"{translation:04X}",
        "offset_source": f"{offset_source:04X}",
        "predicted_x": f"{coordinates[0] & 0xFFFF:04X}",
        "predicted_y": f"{coordinates[1] & 0xFFFF:04X}",
        "carry_sha256": digest(carry_file), "input_control_sha256": digest(control),
        "input_debug_sha256": digest(input_dir / "debug.log"),
        "input_geometry_sha256": digest(geometry),
        "input_projection_sha256": digest(projection_input),
        "private_rom_sha256": ROM_SHA256,
    }


def validate(frozen, target_dir):
    record = json.loads(frozen.read_text())
    assert record["schema"] == 1 and record["object"] == OBJECT
    control = (target_dir / "phase1b-input.log").read_text(errors="replace")
    assert f"STEER_PULSE={PULSE}" in control and "LUA ERROR" not in control
    assert "BRIDGE_INPUT_MASKED" not in control
    geometry = target_dir / "geometry-samples.csv"
    observed, rows = row(geometry, TARGET_CALLBACK)
    assert max(int(item["frame"]) for item in rows) >= TARGET_CALLBACK
    list_path = target_dir / f"shared-list-{TARGET_CALLBACK:04d}.bin"
    shared = list_path.read_bytes()
    assert len(shared) == 8192
    list_x, list_y = struct.unpack_from(">HH", shared, LIST_OFFSET + 4)
    expected = (record["predicted_x"], record["predicted_y"])
    fields = {"projected_x": observed["projected4"],
              "projected_y": observed["projected6"],
              "shared_x": f"{list_x:04X}", "shared_y": f"{list_y:04X}"}
    errors = {key: value for key, value in fields.items()
              if value != expected[0 if key.endswith("_x") else 1]}
    result = {"status": "PASS" if not errors else "FAIL",
              "matched_fields": 4 - len(errors), "errors": errors,
              "observed": fields, "frozen_sha256": digest(frozen),
              "target_geometry_sha256": digest(geometry),
              "target_shared_sha256": digest(list_path)}
    print(json.dumps(result, indent=2))
    assert not errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("input", type=Path)
    freeze.add_argument("carry", type=Path)
    freeze.add_argument("rom", type=Path)
    freeze.add_argument("frozen", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("frozen", type=Path)
    check.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        assert not args.frozen.exists(), "prediction already frozen"
        result = calculate(args.input, args.carry, args.rom)
        args.frozen.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": "FROZEN", "sha256": digest(args.frozen),
                          "predicted": (result["predicted_x"],
                                        result["predicted_y"])}, indent=2))
    else:
        validate(args.frozen, args.target)


if __name__ == "__main__":
    main()
