#!/usr/bin/env python3
"""Audit private pulse-204 road-record projection trials without exporting ROM data."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from phase1b_mild_steer_width import scan
from phase1b_projection_replay import hexfield, project, signed16
from phase1b_swap_compare import changed_pixels, png_rows


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def samples(directory):
    rows = list(csv.DictReader((directory / "geometry-samples.csv").open()))
    return {(int(r["frame"]), int(r["index"])): r for r in rows}


def slot(directory, frame, address):
    data = (directory / f"source-{frame:04d}-ysprites.bin").read_bytes()
    assert len(data) >= address + 16
    return data[address:address + 16]


def rgb(rows, x, y):
    return bytes(rows[y][x * 3:x * 3 + 3])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    root = args.private_root
    sham = root / "phase1b-roadslot-project-sham-final"
    changed = root / "phase1b-roadslot-project-plus100-final"
    repeats = [root / f"phase1b-roadslot-project-plus100{suffix}"
               for suffix in ("", "-r1", "-r2", "-final")]
    baseline = root / "phase1b-pulse204-screen967-native-baseline"
    before, after = samples(sham), samples(changed)
    assert before.keys() == after.keys() and len(before) == 276
    differences = {(frame, index): [key for key in before[frame, index]
                                    if before[frame, index][key] != after[frame, index][key]]
                   for frame, index in before}
    differences = {key: value for key, value in differences.items() if value}
    assert differences == {(964, 0): ["projected4", "projected6"],
                           (965, 0): ["projected4", "projected6"]}, differences
    controls = []
    changes = []
    repeated = []
    for frame in range(960, 983):
        name = f"swap-screen-{frame:04d}.png"
        sham_rows, changed_rows = png_rows(sham / name), png_rows(changed / name)
        count = changed_pixels(sham_rows, changed_rows)
        if count:
            changes.append({"screen": frame, "rgb_pixels": count})
        assert all(digest(run / name) == digest(changed / name) for run in repeats)
        if (baseline / name).exists():
            controls.append((frame, sham_rows == png_rows(baseline / name)))
    assert [x["screen"] for x in changes] == [967, 968, 969], changes
    assert all(equal for _, equal in controls), controls
    for frame in range(960, 983):
        name = f"source-{frame:04d}-ysprites.bin"
        if (changed / name).exists():
            assert all(digest(run / name) == digest(changed / name) for run in repeats)
    assert all(digest(run / "geometry-samples.csv") ==
               digest(changed / "geometry-samples.csv") for run in repeats)
    for run in repeats:
        repeated.append({"directory": run.name,
                         "screen967_sha256": digest(run / "swap-screen-0967.png"),
                         "geometry_sha256": digest(run / "geometry-samples.csv")})
    for directory, expected in ((sham, (0x12, 0x24)),
                                (changed, (0x0A, 0x21))):
        log = (directory / "debug.log").read_text()
        assert "ROAD_X_RESTORED a5=0C1C80 value=E808" in log
        match = re.search(r"ROAD_X_OUTPUT[^\n]*slot=0260 record_x=([0-9A-F]+) "
                          r"record_y=([0-9A-F]+)", log)
        assert match and tuple(int(value, 16) for value in match.groups()) == expected
    predicted = {}
    for label, rows, delta, expected in (("sham", before, 0, (18, 36)),
                                         ("plus100", after, 0x100, (10, 33))):
        inputs = dict(before[962, 0])
        inputs["global1c"] = f"{(hexfield(inputs, 'global1c') + delta) & 0xFFFF:04X}"
        got = project(inputs, hexfield(rows[964, 0], "global18"))
        observed = (signed16(hexfield(rows[964, 0], "projected4")),
                    signed16(hexfield(rows[964, 0], "projected6")))
        assert got == observed == expected, (label, got, observed)
        predicted[label] = {"predicted": got, "observed": observed}
    for frame, address in ((966, 0xE630), (967, 0xC630)):
        assert slot(sham, frame, address) != slot(changed, frame, address)
        assert slot(changed, frame, address)[6:8] == bytes.fromhex("3888")
    edges = []
    for screen, address in ((967, 0xE630), (968, 0xC630)):
        hide = root / f"phase1b-roadslot-project-plus100-hide-{address:04X}"
        normal = png_rows(changed / f"swap-screen-{screen:04d}.png")
        hidden = png_rows(hide / f"swap-screen-{screen:04d}.png")
        original = png_rows(sham / f"swap-screen-{screen:04d}.png")
        selected = [row for row in scan(normal, screen) if 159 <= row["y"] <= 163]
        prior = [row for row in scan(original, screen) if 159 <= row["y"] <= 163]
        assert len(selected) == (3 if screen == 967 else 5), selected
        assert len(prior) == len(selected)
        left = sum(rgb(normal, row["left"], row["y"]) !=
                   rgb(hidden, row["left"], row["y"]) for row in selected)
        right = sum(rgb(normal, row["right"], row["y"]) !=
                    rgb(hidden, row["right"], row["y"]) for row in selected)
        assert (left, right) == (len(selected), 0)
        edges.append({"screen": screen, "baseline": prior, "changed": selected,
                      "hide_changed_left": left, "hide_changed_right": right})
    result = {"status": "PASS", "capture": "MAME 0.289, emulated frames",
              "baseline_screen_control": len(controls), "changed_pixels": changes,
              "geometry_differences": [list(key) for key in differences],
              "projection": predicted, "repeats": repeated, "edges": edges,
              "limitation": "Changed right-edge RGB pixels have no visible dependency on the tested slot hide."}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
