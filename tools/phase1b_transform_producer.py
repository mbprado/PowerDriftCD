#!/usr/bin/env python3
"""Check private main-CPU transform writes against projection snapshots."""

import argparse
import csv
import re
import sys
from pathlib import Path

from phase1b_projection_replay import signed16


SIDES = ("center", "left", "right")
WRITE_FIELDS = {0xc0098: "global18", 0xc00a6: "global26",
                0xc00a4: "global24", 0xc009e: "global1e",
                0xc009c: "global1c", 0xc00a0: "global20"}
ORDER = ("OFFSET_SOURCE", "WRITE:0C0098", "PROJECT", "ANGLE_SOURCE",
         "WRITE:0C00A6", "WRITE:0C00A4", "POSITION_SOURCE",
         "WRITE:0C009E", "WRITE:0C009C", "WRITE:0C00A0")


def load_rows(path):
    rows = [row for row in csv.DictReader(path.open()) if row["index"] == "0"]
    assert len(rows) == 41
    return {int(row["frame"]): row for row in rows}


def load_events(path):
    events = {}
    frame = None
    for line in path.read_text().splitlines():
        marker = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if marker:
            frame = int(marker.group(1))
        match = re.search(r"TRANSFORM_(OFFSET_SOURCE|WRITE|PROJECT|"
                          r"ANGLE_SOURCE|POSITION_SOURCE)\b(.*)", line)
        if not match or frame is None or frame < 961 or frame > 999:
            continue
        kind, details = match.groups()
        fields = dict(re.findall(r"([a-z][a-z0-9_]*)=([0-9A-F]+)", details))
        if kind == "WRITE":
            assert "cpu=maincpu" in details, (path, line)
            kind += ":" + fields["addr"]
        events.setdefault(frame, []).append((kind, fields))
    return events


def value(fields, name):
    return int(fields[name], 16) & 0xffff


def first_divergence(reference, other, field):
    for frame in range(961, 1000, 2):
        if reference[frame][field] != other[frame][field]:
            return frame
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    root = parser.parse_args().private_root
    sources = {}
    checked = 0
    extra_total = 0
    for side in SIDES:
        rows = load_rows(root / f"phase1b-depth-sequence-{side}"
                         / "geometry-samples.csv")
        events = load_events(root / f"phase1b-transform-source-{side}"
                             / "debug.log")
        assert sorted(events) == list(range(961, 1000, 2)), (side, sorted(events))
        sources[side] = {}
        extra = 0
        for frame in sorted(events):
            before, after = rows[frame - 1], rows[frame + 1]
            sequence = events[frame]
            assert tuple(kind for kind, _ in sequence[:10]) == ORDER, (side, frame)
            assert tuple(kind for kind, _ in sequence[10:]) in (
                (), ("WRITE:0C00A0",)), (side, frame)
            data = {kind: fields for kind, fields in sequence[:10]}
            offset = value(data["OFFSET_SOURCE"], "source")
            assert offset == value(data["WRITE:0C0098"], "data")
            project = data["PROJECT"]
            assert value(project, "off") == offset
            for name, field in (("angle1", "global26"),
                                ("angle2", "global24"),
                                ("x", "global1c"), ("y", "global1e"),
                                ("z", "global20")):
                assert value(project, name) == int(before[field], 16), (
                    side, frame, name)
            angle = data["ANGLE_SOURCE"]
            position = data["POSITION_SOURCE"]
            expected_angle1 = (value(angle, "road_angle")
                               + (signed16(value(angle, "tilt")) >> 1)) & 0x3ff
            expected_angle2 = ((signed16(value(angle, "smooth")) >> 1)
                               + signed16(value(angle, "adjustment"))) & 0x3ff
            assert value(angle, "d2") & 0x3ff == expected_angle1
            assert value(data["WRITE:0C00A6"], "data") == expected_angle1
            assert value(data["WRITE:0C00A4"], "data") == expected_angle2
            for address, field in WRITE_FIELDS.items():
                actual = value(data[f"WRITE:{address:06X}"], "data")
                if field != "global20" or len(sequence) == 10:
                    assert actual == int(after[field], 16), (side, frame, field)
            for axis, field in (("x", "global1c"), ("y", "global1e"),
                                ("z", "global20")):
                base_value = value(data[f"WRITE:{next(k for k, v in WRITE_FIELDS.items() if v == field):06X}"], "data")
                assert base_value == (-value(position, axis)) & 0xffff
            if len(sequence) == 11:
                assert sequence[10][1]["pc"] == "0348D0"
                assert value(sequence[10][1], "data") == int(after["global20"], 16)
                extra += 1
            sources[side][frame] = {key: value(angle, key) for key in (
                "road_depth", "road_angle", "tilt", "d2")}
            sources[side][frame].update({
                "offset": offset, "source_x": value(position, "x"),
                "source_y": value(position, "y"),
                "final_z": int(after["global20"], 16)})
            checked += 1
        extra_total += extra
        print(f"{side}: 20/20 ordered producer passes; "
              f"120 base writes, {extra} later Z writes; "
              "120/120 final fields match next snapshot")
    for side in ("left", "right"):
        print(f"{side} first difference vs center: "
              + ", ".join(f"{name}={first_divergence(sources['center'], sources[side], name)}"
                          for name in ("tilt", "d2", "offset", "source_x",
                                       "source_y", "final_z", "road_depth",
                                       "road_angle")))
    print(f"total: {checked}/60 producer passes, {360 + extra_total} "
          "accounted write events, 360/360 final fields")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, TypeError) as exc:
        sys.exit(str(exc))
