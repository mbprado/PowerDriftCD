#!/usr/bin/env python3
"""Bounded, conditional arcade-X versus Sega CD camera-shape audit."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from make_perspective_road import (CURVE_SINE, live_camera_lines,
                                   live_camera_packet)
from phase1b_projection_replay import hexfield, signed16


SIDES = ("center", "left", "right")
EPOCHS = (960, 964, 968, 972)
DEPTH_INDEXES = (2, 3, 4)
ROW_MAPS = ((56, 40, 24), (48, 32, 16))
GAINS = tuple(index / 8 for index in range(1, 257))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_geometry(root):
    rows = {}
    hashes = {}
    for side in SIDES:
        path = root / f"phase1b-depth-sequence-{side}" / "geometry-samples.csv"
        with path.open() as file:
            rows[side] = {(int(row["frame"]), int(row["index"])): row
                          for row in csv.DictReader(file)}
        assert len(rows[side]) == 41 * 12
        hashes[side] = sha256(path)
    return rows, hashes


def projection_deltas(rows):
    outputs = {}
    for epoch in EPOCHS:
        for index in DEPTH_INDEXES:
            source = {tuple(rows[side][epoch, index][field] for field in
                            ("depth", "table", "sample0", "sample1", "sample2"))
                      for side in SIDES}
            assert len(source) == 1
        center = tuple(signed16(hexfield(rows["center"][epoch, index],
                                         "projected4")) for index in DEPTH_INDEXES)
        for side in SIDES[1:]:
            other = tuple(signed16(hexfield(rows[side][epoch, index],
                                            "projected4")) for index in DEPTH_INDEXES)
            outputs[epoch, side] = tuple(a - b for a, b in zip(other, center))
    assert all(outputs[960, side] == (0, 0, 0) for side in SIDES[1:])
    return outputs


def packet_profiles(scanlines):
    """Center source-X term from the current 128x64 five-word trace builder."""
    profiles = {}
    for phase in range(96):
        for bank in range(-2, 3):
            shape = tuple(CURVE_SINE[(phase + y) % 96]
                          + bank * (y - 32) // 8 for y in scanlines)
            profiles.setdefault(shape, (phase, bank))
    return profiles


def verify_host_trace_center(scanlines):
    """Check the reduced lateral term against the existing host trace model."""
    checks = 0
    for frame in range(60):
        phase, _, bank, _, _ = live_camera_packet(frame)
        lines = list(live_camera_lines(frame, width=128))
        for y in scanlines:
            x_start, _, x_step, _ = lines[y]
            center_source_x = (x_start + 64 * (x_step // 256)) // 8
            expected = 136 + CURVE_SINE[(phase + y) % 96] \
                + bank * (y - 32) // 8
            assert center_source_x == expected, (frame, y)
            checks += 1
    return checks


def squared_error(target, prediction):
    return sum((a - b) ** 2 for a, b in zip(target, prediction))


def best_epoch(epoch, gain, targets, profiles, contrasts):
    """Use one center packet for both steering sides; refit side packets."""
    best = None
    for center, candidates in contrasts.items():
        sides = {}
        total = 0.0
        for side in SIDES[1:]:
            target = targets[epoch, side]
            side_best = None
            for shape, d0, d1, d2 in candidates:
                p0, p1, p2 = gain * d0, gain * d1, gain * d2
                error = ((p0 - target[0]) ** 2 + (p1 - target[1]) ** 2
                         + (p2 - target[2]) ** 2)
                if side_best is None or error < side_best[0]:
                    side_best = (error, shape, (p0, p1, p2))
            error, shape, prediction = side_best
            total += error
            sides[side] = {"packet": profiles[shape], "predicted": prediction,
                           "squared_error": error}
        if best is None or total < best[0]:
            best = (total, center, sides)
    error, center, sides = best
    return {"squared_error": error, "center_packet": profiles[center],
            "side_fits": sides}


def run(root):
    rows, hashes = read_geometry(root)
    matched = json.loads((root / "phase1b-projection-window" /
                          "results.json").read_text())["exact_lookup_position"]
    assert all(all(matched[str(epoch)].values()) for epoch in EPOCHS)
    targets = projection_deltas(rows)
    result = {"geometry_csv_sha256": hashes,
              "source_result_sha256": sha256(root / "phase1b-projection-window" /
                                              "results.json"),
              "training_epochs": (964, 968), "held_out_epoch": 972,
              "model": "128x64 center source-X term; curve phase and bank only",
              "maps": []}
    for scanlines in ROW_MAPS:
        host_checks = verify_host_trace_center(scanlines)
        profiles = packet_profiles(scanlines)
        contrasts = {center: [(shape, shape[0] - center[0],
                               shape[1] - center[1], shape[2] - center[2])
                              for shape in profiles] for center in profiles}
        best = None
        for gain in GAINS:
            train = {epoch: best_epoch(epoch, gain, targets, profiles, contrasts)
                     for epoch in (964, 968)}
            error = sum(item["squared_error"] for item in train.values())
            if best is None or error < best[0]:
                best = (error, gain, train)
        train_error, gain, train = best
        held = best_epoch(972, gain, targets, profiles, contrasts)
        flat_error = {}
        for epoch in (964, 968, 972):
            flat_error[epoch] = sum(squared_error(
                targets[epoch, side],
                (sum(targets[epoch, side]) / 3,) * 3)
                for side in SIDES[1:])
        entry = {
            "scanlines_near_to_far": scanlines,
            "host_trace_center_checks": host_checks,
            "distinct_control_profiles": len(profiles),
            "gain_arcade_words_per_sega_source_pixel": gain,
            "training_rmse_arcade_words": (train_error / 12) ** 0.5,
            "held_out_inverse_fit_rmse_arcade_words":
                (held["squared_error"] / 6) ** 0.5,
            "flat_shift_control_rmse_arcade_words": {
                str(epoch): (flat_error[epoch] / 6) ** 0.5
                for epoch in (964, 968, 972)},
            "epochs": {},
        }
        for epoch, fit in {**train, 972: held}.items():
            entry["epochs"][str(epoch)] = {
                "center_packet": fit["center_packet"],
                "squared_error": fit["squared_error"],
                "sides": {side: {"target": targets[epoch, side],
                                 **fit["side_fits"][side]}
                          for side in SIDES[1:]}}
        result["maps"].append(entry)
        print(f"rows {scanlines}: {len(profiles)} profiles, gain {gain:g}, "
              f"train RMSE {entry['training_rmse_arcade_words']:.3f}, "
              "held-out inverse-fit RMSE "
              f"{entry['held_out_inverse_fit_rmse_arcade_words']:.3f}")
    output = root / "phase1b-camera-shape-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"private detail: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    run(parser.parse_args().private_root)
