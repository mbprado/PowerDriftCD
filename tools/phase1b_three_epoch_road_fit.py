#!/usr/bin/env python3
"""Compare three causally verified arcade edge samples with original-art host geometry."""

import argparse
import json
from pathlib import Path

from make_perspective_road import CURVE_SINE
from phase1b_steer_width_trajectory import host_bounds


SAMPLES = (
    (971, "phase1b-right-search-E630-00040-only-E630-E660.json"),
    (973, "phase1b-right-search-972-A600-00040-only-A600-A630.json"),
    (975, "phase1b-mild-steer-112-hide.json"),
)
ARCADE_ROWS = (154, 155, 156)
OUTPUT_ROWS = tuple(y - 128 for y in ARCADE_ROWS)


def load_samples(root):
    samples = []
    for screen, filename in SAMPLES:
        data = json.loads((root / filename).read_text())
        source_rows = data["measurements"] if screen == 975 else data["records"][0]["rows"]
        by_y = {row["y"]: row for row in source_rows}
        assert all(by_y[y]["left_changed"] and by_y[y]["right_changed"]
                   for y in ARCADE_ROWS), screen
        rows = [{"y": y, "left": by_y[y]["left"],
                 "right": by_y[y]["right"],
                 "width": by_y[y]["right"] - by_y[y]["left"] + 1}
                for y in ARCADE_ROWS]
        samples.append({"screen_frame": screen, "rows": rows})
    return samples


def score(arcade, host, offset):
    edge = sum(abs(h["left"] - (0.4 * a["left"] + offset)) +
               abs(h["right"] - (0.4 * a["right"] + offset))
               for a, h in zip(arcade, host)) / 6
    width = sum(abs(h["width"] - 0.4 * a["width"])
                for a, h in zip(arcade, host)) / 3
    return round(edge, 6), round(width, 6)


def main(root, metrics_path):
    samples = load_samples(root)
    metrics = json.loads(metrics_path.read_text())
    assert len(metrics["frames"]) == 60
    for frame in metrics["frames"]:
        reference = [row for row in frame["anchor_rows"]
                     if row["row"] in OUTPUT_ROWS]
        assert host_bounds(frame["camera_packet"], OUTPUT_ROWS) == reference

    candidates = []
    for curve in range(len(CURVE_SINE)):
        for texture in range(48):
            packet = (curve, 0, 0, 4, texture)
            rows = host_bounds(packet, OUTPUT_ROWS)
            if rows is not None:
                candidates.append((packet, rows))
    assert candidates
    results = []
    for offset in (0, -4):
        fits = []
        for sample in samples:
            ranked = ((score(sample["rows"], rows, offset), packet, rows)
                      for packet, rows in candidates)
            error, packet, host = min(ranked, key=lambda item: item[0][0])
            fits.append({"screen_frame": sample["screen_frame"],
                         "packet": packet, "host_rows": host,
                         "mean_absolute_edge_error": error[0],
                         "mean_absolute_width_error": error[1]})
        results.append({"horizontal_offset": offset, "fits": fits})
    output = root / "phase1b-three-epoch-road-fit.json"
    output.write_text(json.dumps({"mapping": "x_sega=0.4*x_arcade+offset; y_sega=y_arcade-128",
                                  "samples": samples,
                                  "candidate_count": len(candidates),
                                  "fixed_words": {"ridge": 0, "bank": 0, "horizon": 4},
                                  "results": results}, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    print("private result:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("host_metrics", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.host_metrics)
