#!/usr/bin/env python3
"""Replay a private Y-Board projection window and verify branch execution."""

import argparse
import csv
import re
import sys
from pathlib import Path

from phase1b_projection_replay import project, signed16, signed32


SIDES = ("center", "left", "right")
FIELDS = ("global16", "global18", "global1a", "global1c", "global1e",
          "global20", "global24", "global26", "coef1sin", "coef1cos",
          "coef2sin", "coef2cos", "screen_y_offset")
GEOMETRY = ("depth", "table", "sample0", "sample1", "sample2",
            "source16", "source18", "source1a")
EVENT = re.compile(
    r"PROJECTION_(GATE|DEPTH|WRITE) pc=[0-9A-F]+ a5=([0-9A-F]+) "
    r"(?:d4|d2|d0)=([0-9A-F]+)")


def load_rows(path):
    rows = list(csv.DictReader(path.open()))
    indexed = {(int(row["frame"]), int(row["index"])): row for row in rows}
    assert len(rows) == len(indexed) == 41 * 12, path
    return indexed


def load_events(path):
    events = {}
    frame = None
    for line in path.read_text().splitlines():
        match = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if match:
            frame = int(match.group(1))
        match = EVENT.search(line)
        if not match or not 961 <= frame <= 999 or frame % 2 != 1:
            continue
        kind, address, value = match.groups()
        if kind == "GATE":
            flag = re.search(r" flag=([0-9A-F]+)", line)
            assert flag and int(flag.group(1), 16) == 0x80, (path, line)
        index = (int(address, 16) - 0xc1c80) // 0x40
        assert 0 <= index < 12 and int(address, 16) == 0xc1c80 + 0x40 * index
        key = (frame, index, kind)
        assert key not in events, (path, key)
        events[key] = int(value, 16)
    return events


def rotation_and_depth(row):
    h = lambda name: int(row[name], 16)
    x = signed16(h("source16") + h("global1c"))
    y = signed16(h("source18") + h("global1e"))
    z = signed16(h("source1a") + h("global20"))
    sine1, cosine1 = signed16(h("coef1sin")), signed16(h("coef1cos"))
    sine2, cosine2 = signed16(h("coef2sin")), signed16(h("coef2cos"))
    first_raw = signed32(sine1 * x + cosine1 * y)
    rotated_x = signed16(first_raw >> 9)
    depth_x = signed16(signed32(sine2 * rotated_x + cosine2 * z) >> 9)
    return first_raw, signed16(h("global16") + depth_x)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    root = parser.parse_args().private_root
    captures = {side: load_rows(root / f"phase1b-depth-sequence-{side}"
                                / "geometry-samples.csv") for side in SIDES}
    reference = captures["center"]
    totals = {"pairs": 0, "gates": 0, "skips": 0, "writes": 0}
    for side in SIDES:
        rows = captures[side]
        events = load_events(root / f"phase1b-projection-depth-{side}" / "debug.log")
        expected_events = set()
        packets = set()
        counters = {key: 0 for key in totals}
        for frame in range(960, 1001):
            packet = tuple(rows[frame, 0][name] for name in FIELDS)
            packets.add(packet)
            for index in range(12):
                row = rows[frame, index]
                assert tuple(row[name] for name in FIELDS) == packet
                assert tuple(row[name] for name in GEOMETRY) == tuple(
                    reference[frame, index][name] for name in GEOMETRY)
                assert (row["sample2"], row["sample0"], row["sample1"]) == (
                    row["source16"], row["source18"], row["source1a"])
        for frame in range(960, 1000, 2):
            for index in range(12):
                before, after = rows[frame, index], rows[frame + 2, index]
                first_raw, depth = rotation_and_depth(before)
                key = (frame + 1, index)
                expected_events.add((*key, "DEPTH"))
                assert signed16(events[*key, "DEPTH"]) == depth, (side, key)
                if first_raw <= -65536:
                    expected_events.add((*key, "GATE"))
                    assert signed32(events[*key, "GATE"]) == first_raw, (side, key)
                    counters["gates"] += 1
                if depth <= 0:
                    predicted = (signed16(int(before["projected4"], 16)),
                                 signed16(int(before["projected6"], 16)))
                    counters["skips"] += 1
                else:
                    expected_events.add((*key, "WRITE"))
                    assert (*key, "WRITE") in events, (side, key)
                    predicted = project(before, int(after["global18"], 16))
                    counters["writes"] += 1
                observed = (signed16(int(after["projected4"], 16)),
                            signed16(int(after["projected6"], 16)))
                assert predicted == observed, (side, key, predicted, observed)
                counters["pairs"] += 1
        assert set(events) == expected_events, (side, set(events) ^ expected_events)
        for key, count in counters.items():
            totals[key] += count
        print(f"{side}: {counters['pairs']}/240 pairs; "
              f"{counters['writes']} writes, {counters['skips']} depth skips, "
              f"{counters['gates']} first-rotation gate entries; "
              f"{len(packets)} distinct sampled parameter packets")
    print("total: {pairs}/720 pairs; {writes} writes, {skips} depth skips, "
          "{gates} first-rotation gate entries".format(**totals))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, TypeError) as exc:
        sys.exit(str(exc))
