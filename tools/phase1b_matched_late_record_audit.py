#!/usr/bin/env python3
"""Audit a matched arcade geometry record through two Y-sprite slots."""

import csv
import json
from pathlib import Path
import struct

from phase1b_dual_roadslot_audit import digest, native_changes, screen_changes


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "build/private"
EXPECTED = {
    204: {"first": 0x8B7C0020, "position": 0xFF070039,
          "size": 0xFF510032, "source": 0xB242007D,
          "slot": 0xE5D0, "baseline": "phase1b-render989-pulse204-baseline",
          "trial": "phase1b-render989-pulse204-E5D0",
          "main_log": "phase1b-E5D0-mainlist-pulse204"},
    56: {"first": 0x8B740020, "position": 0x013E0038,
         "size": 0x00E7002E, "source": 0xB2420075,
         "slot": 0xE5F0, "baseline": "phase1b-render989-baseline",
         "trial": "phase1b-render989-narrow-E5F0-0010",
         "main_log": "phase1b-E5F0-mainlist-pulse56"},
}


def interval_lines(path, marker):
    frame = None
    for line in path.read_text().splitlines():
        if line.startswith("SEQUENCE_FRAME,"):
            frame = int(line.split(",")[1])
        if frame == marker:
            yield line


def verify(pulse, spec):
    origin = PRIVATE / f"phase1b-E5D0-origin-pulse{pulse}"
    geometry = PRIVATE / f"phase1b-natural-screen{pulse}" / "geometry-samples.csv"
    rows = [row for row in csv.DictReader(geometry.open())
            if row["frame"] == "989" and row["object"] == "0C1D00"]
    assert len(rows) == 1
    row = rows[0]
    assert (row["table"], row["source16"], row["source18"]) == (
        "01D3E8", "20BF", "0790")
    expected_position = (int(row["projected4"], 16) << 16) | int(row["projected6"], 16)
    assert expected_position == spec["position"]

    tuple4 = (spec["first"], spec["position"], spec["size"], spec["source"])
    captures = []
    for callback in range(988, 992):
        path = origin / f"shared-list-{callback:04d}.bin"
        data = path.read_bytes()
        assert len(data) == 8192
        assert struct.unpack_from(">4I", data, 0x240) == tuple4
        matches = [offset for offset in range(0, len(data) - 15, 2)
                   if struct.unpack_from(">4I", data, offset) == tuple4]
        assert matches == [0x240]
        captures.append({"callback": callback, "sha256": digest(path)})

    main_log = PRIVATE / spec["main_log"] / "debug.log"
    write_lines = [line for line in main_log.read_text().splitlines()
                   if line.startswith("RECORD_WRITE ")]
    expected_words = struct.unpack(">8H", struct.pack(">4I", *tuple4))
    expected_lines = [
        f"RECORD_WRITE cpu=maincpu addr={0x0C9A40 + 2*i:06X} "
        f"data=0000{word:04X} pc=033E8E a0=0C9800 a5=0C1D00"
        for i, word in enumerate(expected_words)]
    assert sum(all(expected in actual for expected, actual in
                   zip(expected_lines, write_lines[start:start + 8]))
               for start in range(len(write_lines) - 7)) == 1
    sub_log = origin / "debug.log"
    sub_lines = list(interval_lines(sub_log, 989))
    slot = spec["slot"] - 0x2000
    if pulse == 204:
        match = (f"YSPRITE_INPUT_AFTER pc=00DD6A a0=0C9800 "
                 f"d0={spec['first']:08X} d1={spec['position']:08X} "
                 f"d2={spec['size']:08X} d3={spec['source']:08X} "
                 f"a2=18{slot:04X}")
    else:
        match = (f"SUBX_LIST pc=00DD6A first={spec['first']:08X} "
                 f"pos={spec['position']:08X} size={spec['size']:08X} "
                 f"source={spec['source']:08X} a0=0C9800 a2=18{slot:04X}")
    assert sum(match in line for line in sub_lines) == 1

    baseline = PRIVATE / spec["baseline"]
    trial = PRIVATE / spec["trial"]
    repeats = [trial, PRIVATE / (spec["trial"] + "-r1"),
               PRIVATE / (spec["trial"] + "-r2")]
    source = (baseline / "source-0991-ysprites.bin").read_bytes()
    assert len(source) == 65536 and not source[spec["slot"]] & 0x10
    artifacts = ("source-0991-ysprites-after.bin", "ybitmap-0990.raw",
                 "swap-screen-0992.png")
    for candidate in repeats:
        assert (candidate / "source-0991-ysprites.bin").read_bytes() == source
        hidden = (candidate / artifacts[0]).read_bytes()
        assert [i for i, (a, b) in enumerate(zip(source, hidden)) if a != b] == [spec["slot"]]
        assert hidden[spec["slot"]] == source[spec["slot"]] | 0x10
    assert all(len({digest(candidate / name) for candidate in repeats}) == 1
               for name in artifacts)
    pixels = screen_changes(baseline, trial)
    words = native_changes(baseline, trial)
    xs, ys = zip(*pixels)
    return {"pulse": pulse, "geometry_object": "0C1D00",
            "geometry_table": row["table"], "source16": row["source16"],
            "source18": row["source18"], "projected4": row["projected4"],
            "projected6": row["projected6"], "shared_offset": "0240",
            "shared_first": f"{spec['first']:08X}", "shared_captures": captures,
            "main_copy_source": "0C1D00", "main_copy_pc": "033E8E",
            "subx_load_pc": "00DD6A", "subx_output_slot": f"{slot:04X}",
            "visible_slot": f"{spec['slot']:04X}", "callback": 991,
            "native_frame": 990, "screen": 992, "fresh_runs": 3,
            "native_words_changed": words, "screen_pixels_changed": len(pixels),
            "screen_bbox": [min(xs), min(ys), max(xs), max(ys)],
            "main_log_sha256": digest(main_log), "subx_log_sha256": digest(sub_log),
            "screen_sha256": digest(trial / artifacts[2])}


def main():
    records = [verify(pulse, spec) for pulse, spec in EXPECTED.items()]
    assert len({record["geometry_table"] for record in records}) == 1
    assert len({record["source16"] for record in records}) == 1
    assert len({record["source18"] for record in records}) == 1
    output = PRIVATE / "phase1b-matched-late-record-audit.json"
    output.write_text(json.dumps({"schema": 1, "evidence": "MAME execution",
                                  "records": records}, indent=2) + "\n")
    for record in records:
        print(record["pulse"], record["geometry_object"],
              record["visible_slot"], record["screen_bbox"])
    print("private result", output)


if __name__ == "__main__":
    main()
