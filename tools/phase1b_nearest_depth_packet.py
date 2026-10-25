#!/usr/bin/env python3
"""Probe whether adjacent arcade road-depth states transfer prior host packets."""

import argparse
import json
from pathlib import Path

from phase1b_calibrated_geometry import digest
from phase1b_road_vertical_profile import packet_bounds
from phase1b_road_width_profile import score
from phase1b_screen967_holdout import SOURCE, mapped
from phase1b_upstream_state import angle_sources


TRACE_SHA256 = "d08c046ffa864fc3b938fbcdf6bd6ecee0056ad61a2d2cb0491ba266a5d90788"
TRAIN_SHA256 = "8d57ee07022b035c21f72c891e57276ad949024a7cae7ad7ba9adea9a6ddc3e3"
SOURCE_SHA256 = "b68de3e28164b216ddb0bc6bd4fa04c3f1953f2f7887854af236da5a26cb526b"
CALIBRATION_SHA256 = "e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23"
EXPECTED = {969: (61, 0, 0, 4, 44), 971: (63, 0, 0, 4, 42),
            973: (38, 0, 0, 4, 15), 975: (38, 0, 0, 4, 31)}


def depth(sources, screen, lag):
    fields = sources[screen - lag]
    return int(fields["road_depth"], 16)


def nearest(sources, screen, choices, lag):
    return min(choices, key=lambda other: (
        abs(depth(sources, screen, lag) - depth(sources, other, lag)), other))


def measure(packet, target):
    host = packet_bounds(packet, [row["row"] for row in target], False)
    assert host is not None
    return {"score": score(target, host), "bounds": host}


def main(root, calibration_path):
    trace_path = root / "phase1b-upstream-speed-center" / "debug.log"
    train_path = root / "phase1b-road-vertical-profile" / "result.json"
    source_path = root / SOURCE
    assert digest(trace_path) == TRACE_SHA256
    assert digest(train_path) == TRAIN_SHA256
    assert digest(source_path) == SOURCE_SHA256
    assert digest(calibration_path) == CALIBRATION_SHA256
    sources = angle_sources(trace_path)
    training = json.loads(train_path.read_text())
    packets = {item["screen_frame"]: tuple(item["packet"])
               for item in training["fixed_packets"]}
    targets = {item["screen_frame"]: item["anchor_target"]
               for item in training["fixed_packets"]}
    independent = training["independent_screen_969"]
    packets[969] = tuple(independent["optimistic_fit_packet"])
    targets[969] = independent["fit_rows"]
    assert packets == EXPECTED
    assert set(targets) == set(EXPECTED)

    calibration = json.loads(calibration_path.read_text())
    evidence = json.loads(source_path.read_text())
    assert evidence["callback"] == 966 and evidence["pulse"] == 112
    record, = evidence["records"]
    assert record["slots_hidden"] == 3
    rows = record["rows"]
    assert [r["y"] for r in rows] == list(range(153, 164))
    assert all(r["left_changed"] and r["right_changed"] for r in rows)
    target = mapped(rows, calibration)

    result = {"inputs_sha256": {"trace": TRACE_SHA256, "training": TRAIN_SHA256,
                                 "screen967": SOURCE_SHA256,
                                 "calibration": CALIBRATION_SHA256},
              "rule": "nearest absolute hexadecimal road_depth; earlier screen breaks ties",
              "training_packets": {str(k): list(v) for k, v in sorted(packets.items())},
              "lag_sensitivity": [], "leave_one_out": []}
    for lag in (0, 2):
        chosen = nearest(sources, 967, packets, lag)
        assert chosen == 969
        packet = packets[chosen]
        result["lag_sensitivity"].append({
            "source_marker_lag": lag,
            "arcade_depth_hex": {str(screen): f"{depth(sources, screen, lag):04X}"
                                 for screen in (967, *sorted(packets))},
            "screen967": {"selected_training_screen": chosen,
                          "packet": packet,
                          "all_11_rows": measure(packet, target),
                          "prior_fit_rows": measure(packet, target[1:4]),
                          "other_8_rows": measure(packet, target[:1] + target[4:])}})
        for screen in sorted(packets):
            other = nearest(sources, screen, [k for k in packets if k != screen], lag)
            result["leave_one_out"].append({
                "source_marker_lag": lag, "target_screen": screen,
                "selected_training_screen": other, "packet": packets[other],
                "fit_rows": measure(packets[other], targets[screen]),
                "own_packet_fit": measure(packets[screen], targets[screen])})

    destination = root / "phase1b-nearest-depth-packet"
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "result.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"private_result": str(output), "sha256": digest(output),
                      "screen967_all_rows": result["lag_sensitivity"][0]["screen967"]["all_11_rows"]["score"],
                      "training_leave_one_out": [item["fit_rows"]["score"]
                                                 for item in result["leave_one_out"][:4]]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("calibration", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.calibration)
