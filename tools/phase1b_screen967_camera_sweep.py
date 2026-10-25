#!/usr/bin/env python3
"""Bounded five-word camera diagnostic using fixed screen-967 arcade evidence."""

import argparse
import json
from pathlib import Path

from make_perspective_road import CURVE_SINE, RIDGE_SINE
from phase1b_calibrated_geometry import digest
from phase1b_road_vertical_profile import packet_bounds
from phase1b_road_width_profile import score
from phase1b_screen967_holdout import SOURCE, mapped


BASE = (38, 0, 0, 4, 31)
FIT_LIMITS = (1.0, 2.0)
CHECK_LIMITS = (2.0, 2.0)
SOURCE_SHA256 = "b68de3e28164b216ddb0bc6bd4fa04c3f1953f2f7887854af236da5a26cb526b"
CALIBRATION_SHA256 = "e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23"


def evaluate(packet, target, bumped):
    predicted = packet_bounds(packet, [row["row"] for row in target], bumped)
    return score(target, predicted) if predicted is not None else None


def choice(packet, fit_error, check_error, fit, check, bumped):
    return {"packet": packet, "fit_error": fit_error,
            "fit_bounds": packet_bounds(packet, [row["row"] for row in fit], bumped),
            "check_error": check_error,
            "check_bounds": packet_bounds(packet, [row["row"] for row in check], bumped),
            "check_pass": check_error is not None and
            all(a <= b for a, b in zip(check_error, CHECK_LIMITS))}


def sweep(name, packets, fit, check, bumped):
    eligible = []
    selected = None
    valid = 0
    for packet in packets:
        fit_error = evaluate(packet, fit, bumped)
        if fit_error is None:
            continue
        valid += 1
        if selected is None or (fit_error, packet) < (selected[0], selected[1]):
            selected = (fit_error, packet)
        if all(value <= limit for value, limit in zip(fit_error, FIT_LIMITS)):
            eligible.append((fit_error, packet))
    assert selected is not None
    # The oracle reads check rows. It is a diagnostic upper bound, not validation.
    oracle_candidates = []
    for fit_error, packet in eligible:
        check_error = evaluate(packet, check, bumped)
        if check_error is not None:
            oracle_candidates.append((check_error, fit_error, packet))
    oracle = min(oracle_candidates) if oracle_candidates else None
    chosen_fit, chosen_packet = selected
    chosen_check = evaluate(chosen_packet, check, bumped)
    return {"name": name, "candidate_count": len(packets), "valid_count": valid,
            "fit_eligible_count": len(eligible),
            "fit_only_choice": choice(chosen_packet, chosen_fit, chosen_check,
                                      fit, check, bumped),
            "check_oracle_among_fit_eligible": (
                choice(oracle[2], oracle[1], oracle[0], fit, check, bumped)
                if oracle else None)}


def main(root, calibration_path):
    calibration = json.loads(calibration_path.read_text())
    source_path = root / SOURCE
    assert digest(source_path) == SOURCE_SHA256
    assert digest(calibration_path) == CALIBRATION_SHA256
    evidence = json.loads(source_path.read_text())
    assert evidence["callback"] == 966 and evidence["pulse"] == 112
    record, = evidence["records"]
    assert record["group"] == "E630-00040-only-E630-E650-E660"
    assert record["slots_hidden"] == 3
    rows = record["rows"]
    assert [row["y"] for row in rows] == list(range(153, 164))
    assert all(row["left_changed"] and row["right_changed"] for row in rows)
    fit = mapped(rows[1:4], calibration)
    check = mapped(rows[:1] + rows[4:], calibration)
    assert [row["row"] for row in fit] == [22, 24, 25]
    assert [row["row"] for row in check] == [21, 26, 27, 28, 29, 30, 32, 33]

    curve_texture = [(curve, 0, 0, 4, texture)
                     for curve in range(len(CURVE_SINE)) for texture in range(48)]
    ridge_bank_horizon = [(38, ridge, bank, horizon, 31)
                          for ridge in range(len(RIDGE_SINE))
                          for bank in range(-2, 3) for horizon in range(1, 8)]
    result = {"source_sha256": digest(source_path),
              "calibration_sha256": digest(calibration_path),
              "generator": "wide_geometry_lines; original 52/54/58-width source art",
              "base_packet": BASE, "fit_arcade_y": [154, 155, 156],
              "check_arcade_y": [153, 157, 158, 159, 160, 161, 162, 163],
              "fit_limits": FIT_LIMITS, "check_limits": CHECK_LIMITS,
              "variants": []}
    for bumped, variant in ((False, "baseline"), (True, "width_bump")):
        record = {"variant": variant,
                  "base": {"fit_error": evaluate(BASE, fit, bumped),
                           "check_error": evaluate(BASE, check, bumped)},
                  "sweeps": [sweep("curve_texture_fixed_other_words", curve_texture,
                                   fit, check, bumped),
                             sweep("ridge_bank_horizon_fixed_curve_texture",
                                   ridge_bank_horizon, fit, check, bumped)]}
        result["variants"].append(record)
    destination = root / "phase1b-screen967-camera-sweep"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"private_result": str(path), "sha256": digest(path),
                      "variants": [{"variant": v["variant"],
                                    "sweeps": [{"name": s["name"],
                                                "fit_only": s["fit_only_choice"]["packet"],
                                                "fit_only_check": s["fit_only_choice"]["check_error"],
                                                "oracle": s["check_oracle_among_fit_eligible"]["packet"],
                                                "oracle_check": s["check_oracle_among_fit_eligible"]["check_error"]}
                                               for s in v["sweeps"]]}
                                   for v in result["variants"]]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("calibration", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.calibration)
