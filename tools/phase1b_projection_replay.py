#!/usr/bin/env python3
"""Check a bounded Y-Board fixed-point projection against private MAME traces."""

import argparse
import csv
import re
import sys
from pathlib import Path


SIDES = ("center", "left", "right")
GEOMETRY = ("depth", "table", "sample0", "sample1", "sample2",
            "source16", "source18", "source1a")


def signed16(value):
    return ((value + 0x8000) & 0xFFFF) - 0x8000


def signed32(value):
    return ((value + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def hexfield(row, name):
    return int(row[name], 16)


def project(row, horizontal_offset_at_projection):
    """Reproduce the observed main-CPU sequence and signed 315-5248/5249 math."""
    h = lambda name: hexfield(row, name)
    x = signed16(h("source16") + h("global1c"))
    y = signed16(h("source18") + h("global1e"))
    z = signed16(h("source1a") + h("global20"))
    sine1, cosine1 = signed16(h("coef1sin")), signed16(h("coef1cos"))
    sine2, cosine2 = signed16(h("coef2sin")), signed16(h("coef2cos"))
    rotated_x = signed16(signed32(sine1 * x + cosine1 * y) >> 9)
    rotated_y = signed16(signed32(sine1 * y - cosine1 * x) >> 9)
    depth_x = signed16(signed32(sine2 * rotated_x + cosine2 * z) >> 9)
    depth_y = signed16(signed32(sine2 * z - cosine2 * rotated_x) >> 9)
    horizontal = signed16(horizontal_offset_at_projection + rotated_y)
    vertical = signed16(h("global1a") + depth_y)
    divisor = signed16(h("global16") + depth_x + 0x80)
    if divisor <= 0:
        return None
    quotient = min(32767, 0x20000 // divisor)
    projected_x = signed16(signed32(horizontal * quotient) >> 10)
    projected_y = signed16(- (signed32(vertical * quotient) >> 10)
                           + h("screen_y_offset"))
    return projected_x, projected_y


def load_samples(directory):
    rows = list(csv.DictReader((directory / "geometry-samples.csv").open()))
    indexed = {(int(row["frame"]), int(row["index"])): row for row in rows}
    assert len(rows) == len(indexed) == 11 * 12
    return indexed


def trace_pairs(path):
    text = path.read_text()
    offsets = [int(x, 16) for x in re.findall(
        r"MAIN_FIELDS pc=033D1E[^\n]*cam18=([0-9A-F]+)", text)]
    outputs = [signed16(int(x, 16)) for x in re.findall(
        r"MAIN_RECORD pc=033E58[^\n]*d0=([0-9A-F]+)", text)]
    assert len(offsets) >= 5 and len(outputs) >= 5
    return list(zip(offsets[:5], outputs[:5]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    root = args.private_root
    runs = {side: load_samples(root / f"phase1b-geometry-coeff-{side}")
            for side in SIDES}
    reference = runs["center"]
    source_matches = 0
    geometry_matches = 0
    predictions = 0
    for side, rows in runs.items():
        for key, row in rows.items():
            assert (row["sample2"], row["sample0"], row["sample1"]) == (
                row["source16"], row["source18"], row["source1a"])
            source_matches += 1
            if side != "center":
                assert all(row[field] == reference[key][field] for field in GEOMETRY)
                geometry_matches += 1
        trace = trace_pairs(root / f"phase1b-projection-timing-{side}" / "debug.log")
        for step, frame in enumerate(range(960, 970, 2)):
            destination = rows[frame + 2, 0]
            assert trace[step] == (
                hexfield(destination, "global18"),
                signed16(hexfield(destination, "projected4")))
            for index in range(12):
                before = rows[frame, index]
                after = rows[frame + 2, index]
                predicted = project(before, hexfield(after, "global18"))
                observed = (signed16(hexfield(after, "projected4")),
                            signed16(hexfield(after, "projected6")))
                assert predicted == observed, (
                    f"{side} frame {frame} index {index}: "
                    f"predicted {predicted}, observed {observed}")
                predictions += 1
        print(f"{side}: 5 projection steps × 12 records = 60/60 exact "
              "X/Y coordinate pairs; target timing trace agrees")
    print(f"ROM sample → object fields: {source_matches}/{source_matches} exact")
    print(f"geometry tuple shared across steering: "
          f"{geometry_matches}/{geometry_matches} exact")
    print(f"fixed-point projection: {predictions}/{predictions} exact "
          "coordinate pairs")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as exc:
        sys.exit(str(exc))
