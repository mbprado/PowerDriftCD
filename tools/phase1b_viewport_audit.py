#!/usr/bin/env python3
"""Conditional arcade-screen to synthetic Sega viewport audit; private inputs."""

import argparse
import hashlib
import json
from pathlib import Path

from make_perspective_road import CURVE_SINE, live_camera_lines, live_camera_packet
from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import png_rows


FRAMES = (966, 970, 974)
SIDES = ("center", "left")
DEPTHS = ("3400", "3600")
SCREEN_Y = 162
VIEWPORTS = {
    "full_screen": (0, 223),
    "road_crop": (133, 169),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sega_row(arcade_y, crop):
    top, bottom = crop
    assert top <= arcade_y <= bottom
    return round((arcade_y - top) * 63 / (bottom - top))


def road_left_edge(phase, bank, horizon, row):
    depth = max(0, row - horizon)
    step = (12, 8, 6, 4)[min(3, depth // 15)]
    curve = CURVE_SINE[(phase + row) % 96]
    bank_shift = bank * (row - 32) // 8
    x_start = (136 + curve + bank_shift) * 8 - 64 * step
    pixels = [x for x in range(128)
              if 128 <= (x_start + x * step) // 8 < 144]
    assert pixels
    return pixels[0]


def verify_host_model(rows):
    checks = 0
    for frame in range(60):
        phase, _, bank, horizon, _ = live_camera_packet(frame)
        traces = list(live_camera_lines(frame, width=128))
        for row in rows:
            x_start, _, dx, _ = traces[row]
            expected = [x for x in range(128)
                        if 128 <= (x_start + x * (dx // 256)) // 8 < 144]
            assert expected and road_left_edge(phase, bank, horizon, row) == expected[0]
            checks += 1
    return checks


def fit_pair(rows, target):
    profiles = {}
    for phase in range(96):
        for bank in range(-2, 3):
            for horizon in range(1, 8):
                edge = tuple(road_left_edge(phase, bank, horizon, row)
                             for row in rows)
                profiles.setdefault(edge, (phase, bank, horizon))
    best = None
    for center in profiles:
        for left in profiles:
            delta = tuple(a - b for a, b in zip(left, center))
            error = sum((a - b) ** 2 for a, b in zip(delta, target))
            if best is None or error < best[0]:
                best = (error, center, left, delta)
    error, center, left, delta = best
    flat = sum(target) / len(target)
    return {
        "distinct_edge_profiles": len(profiles),
        "center_packet_curve_bank_horizon": profiles[center],
        "left_packet_curve_bank_horizon": profiles[left],
        "predicted_delta_sega_pixels": delta,
        "inverse_fit_rmse_sega_pixels": (error / len(rows)) ** 0.5,
        "flat_shift_rmse_sega_pixels":
            (sum((x - flat) ** 2 for x in target) / len(rows)) ** 0.5,
    }


def run(root):
    source = root / "phase1b-affine-landmark-extension.json"
    landmark = json.loads(source.read_text())
    assert landmark["native_row_offset"] == 1
    cases = {(item["side"], item["descriptor_frame"], item["depth"]): item
             for item in landmark["cases"]}
    assert len(cases) == len(FRAMES) * len(SIDES) * len(DEPTHS)
    output = {"source_landmark_sha256": digest(source),
              "arcade_boundary_row": SCREEN_Y,
              "boundaries": [], "landmark_pairs": [], "registrations": {}}
    for frame in FRAMES:
        edges = {}
        for side in SIDES:
            screen = root / f"phase1b-depth-sequence-{side}" / \
                f"swap-screen-{frame+1:04d}.png"
            assert digest(screen) == cases[side, frame, DEPTHS[0]][
                "baseline_screen_sha256"]
            assert digest(screen) == cases[side, frame, DEPTHS[1]][
                "baseline_screen_sha256"]
            edges[side] = boundary(png_rows(screen)[SCREEN_Y], SCREEN_Y)[0]
            output["boundaries"].append({"descriptor_frame": frame,
                                         "side": side, "screen_sha256": digest(screen),
                                         "screen_row": SCREEN_Y,
                                         "sand_boundary_x": edges[side]})
        for depth in DEPTHS:
            center = cases["center", frame, depth]
            left = cases["left", frame, depth]
            output["landmark_pairs"].append({
                "descriptor_frame": frame, "depth": depth,
                "center_screen_y": center["predicted_screen_span_y"][0],
                "arcade_projected_x_delta": left["projected_x"]
                - center["projected_x"],
                "arcade_landmark_edge_delta": left["predicted_screen_left_x"]
                - center["predicted_screen_left_x"],
                "arcade_sand_boundary_delta": edges["left"] - edges["center"]})
    for name, crop in VIEWPORTS.items():
        entries = []
        rows_used = set()
        for frame in FRAMES:
            pairs = [item for item in output["landmark_pairs"]
                     if item["descriptor_frame"] == frame]
            rows = tuple(sega_row(item["center_screen_y"], crop) for item in pairs)
            assert len(set(rows)) == 2
            rows_used.update(rows)
            # A 320-pixel arcade screen reduced to 128 pixels has a fixed 0.4 X scale.
            target = tuple(item["arcade_landmark_edge_delta"] * 128 / 320
                           for item in pairs)
            fit = fit_pair(rows, target)
            entries.append({"descriptor_frame": frame, "arcade_y":
                            [item["center_screen_y"] for item in pairs],
                            "sega_rows": rows,
                            "target_delta_sega_pixels": target, **fit})
        output["registrations"][name] = {
            "arcade_y_crop_inclusive": crop,
            "horizontal_scale": 128 / 320,
            "host_edge_checks": verify_host_model(rows_used),
            "epochs": entries}
    path = root / "phase1b-viewport-audit.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    for item in output["landmark_pairs"]:
        print("landmark", item)
    for name, entry in output["registrations"].items():
        for case in entry["epochs"]:
            print(name, case["descriptor_frame"], "rows", case["sega_rows"],
                  "target", case["target_delta_sega_pixels"],
                  "inverse RMSE", case["inverse_fit_rmse_sega_pixels"],
                  "flat RMSE", case["flat_shift_rmse_sega_pixels"])
    print("private result:", path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    run(parser.parse_args().private_root.resolve())
