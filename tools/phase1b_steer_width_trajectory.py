#!/usr/bin/env python3
"""Causally audit mild-steering road-width swap epochs in private MAME captures."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from phase1b_mild_steer_width import digest, scan
from phase1b_swap_compare import png_rows
from make_perspective_road import CURVE_SINE, wide_geometry_lines
from make_wide_road_motion import source_pixel


PULSE = 112
TRIALS = ((966, 0xE5D0), (970, 0xE5D0), (970, 0xE5B0),
          (972, 0xE5D0), (972, 0xE5B0), (974, 0xE610))


def trial_dir(root, callback, slot):
    return root / f"phase1b-trajectory-hidden-{callback}-{slot:04X}"


def run(root, mame, rompath, state):
    baseline = root / f"phase1b-mild-steer-{PULSE}"
    script = Path(__file__).resolve().with_name("phase1b_mame_input.lua")
    for callback, slot in TRIALS:
        source = baseline / f"source-{callback:04d}-ysprites.bin"
        raw = bytearray(source.read_bytes())
        assert len(raw) == 0x10000 and raw[slot] & 0x10 == 0
        assert raw[slot + 6:slot + 8] == bytes.fromhex("3888")
        raw[slot] |= 0x10
        override = root / f"phase1b-trajectory-hide-{callback}-{slot:04X}.bin"
        override.write_bytes(raw)
        trial = trial_dir(root, callback, slot)
        trial.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({"SDL_VIDEODRIVER": "dummy", "PDRIFT_SNAPSHOT_DIR": ".",
                    "PDRIFT_SWAP_DIR": ".", "PDRIFT_SOURCE_DIR": ".",
                    "PDRIFT_SEQUENCE_END_FRAME": "976",
                    "PDRIFT_STATE_LOAD": str(state.resolve()),
                    "PDRIFT_STEER_PULSE": str(PULSE),
                    "PDRIFT_SOURCE_OVERRIDE_FRAME": str(callback),
                    "PDRIFT_SOURCE_OVERRIDE_RANGE": f"{slot:04X}:0010",
                    "PDRIFT_SOURCE_OVERRIDE": str(override.resolve())})
        cmd = [str(mame.resolve()), "pdrift", "-rompath", str(rompath.resolve()),
               "-noreadconfig", "-video", "none", "-sound", "none",
               "-nothrottle", "-seconds_to_run", "18", "-autoboot_script",
               str(script)]
        with (trial / "phase1b-input.log").open("w") as log:
            subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        print(callback, f"{slot:04X}", "replay complete", flush=True)


def analyze(root):
    baseline = root / f"phase1b-mild-steer-{PULSE}"
    center = root / "phase1b-mild-steer-center"
    records = []
    for callback, slot in TRIALS:
        screen_frame = callback + 1
        trial = trial_dir(root, callback, slot)
        source = (baseline / f"source-{callback:04d}-ysprites.bin").read_bytes()
        override_path = root / f"phase1b-trajectory-hide-{callback}-{slot:04X}.bin"
        override = override_path.read_bytes()
        after = (trial / f"source-{callback:04d}-ysprites-after.bin").read_bytes()
        assert len(source) == len(override) == len(after) == 0x10000
        assert override == after
        assert [i for i, (a, b) in enumerate(zip(source, after))
                if a != b] == [slot]
        assert after[slot] == source[slot] | 0x10
        for frame in range(960, screen_frame):
            name = f"swap-screen-{frame:04d}.png"
            assert png_rows(trial / name) == png_rows(baseline / name)
        name = f"swap-screen-{screen_frame:04d}.png"
        baseline_rows = png_rows(baseline / name)
        hidden_rows = png_rows(trial / name)
        center_by_y = {r["y"]: r for r in scan(png_rows(center / name), screen_frame)}
        candidate = scan(baseline_rows, screen_frame)
        rows = []
        for b in candidate:
            y = b["y"]
            changes = [x for x in range(320)
                       if baseline_rows[y][3*x:3*x+3] != hidden_rows[y][3*x:3*x+3]]
            row = {**b, "left_changed": b["left"] in changes,
                   "right_changed": b["right"] in changes,
                   "change_min": min(changes) if changes else None,
                   "change_max": max(changes) if changes else None}
            if y in center_by_y:
                row["center_left"] = center_by_y[y]["left"]
                row["center_right"] = center_by_y[y]["right"]
                row["center_width"] = center_by_y[y]["width"]
            rows.append(row)
        accepted = [r for r in rows if r["left_changed"] and r["right_changed"]]
        records.append({"callback": callback, "screen_frame": screen_frame,
                        "slot": f"{slot:04X}",
                        "baseline_source_sha256": digest(baseline / f"source-{callback:04d}-ysprites.bin"),
                        "override_sha256": digest(override_path),
                        "baseline_screen_sha256": digest(baseline / name),
                        "hidden_screen_sha256": digest(trial / name),
                        "rows": rows})
        print(callback, f"{slot:04X}", "two-sided candidates", len(rows),
              "both edges causal", len(accepted),
              "shared with center", sum("center_width" in r for r in accepted))
        print([(r["y"], r["left"], r["right"], r["width"])
               for r in accepted])
    output = root / "phase1b-steer-width-trajectory.json"
    output.write_text(json.dumps({"pulse": PULSE, "records": records}, indent=2) + "\n")
    print("private result:", output)


def host_bounds(packet, rows):
    """Sample the same original source texture and trace math as the host fixture."""
    traces = list(wide_geometry_lines(0, packet_fn=lambda _: packet))
    result = []
    for y in rows:
        start_x, start_y, dx, dy = traces[y]
        road = []
        for x in range(128):
            sx = (start_x + x * (dx // 256)) // 8
            sy = (start_y + x * (dy // 256)) // 8
            if source_pixel(sx, sy) in (7, 10, 14, 15):
                road.append(x)
        if not road or road != list(range(road[0], road[-1] + 1)):
            return None
        result.append({"row": y, "left": road[0], "right": road[-1],
                       "width": len(road)})
    return result


def compare(root, metrics_path):
    trajectory = json.loads((root / "phase1b-steer-width-trajectory.json").read_text())
    record, = [item for item in trajectory["records"]
               if (item["callback"], item["slot"]) == (974, "E610")]
    arcade = [item for item in record["rows"]
              if item["left_changed"] and item["right_changed"]]
    assert [item["y"] for item in arcade] == list(range(154, 160))
    rows = [item["y"] - 128 for item in arcade]  # Explicit, provisional crop.
    metrics = json.loads(metrics_path.read_text())
    assert len(metrics["frames"]) == 60
    for frame in metrics["frames"]:
        generated = host_bounds(frame["camera_packet"], rows)
        recorded = [item for item in frame["anchor_rows"] if item["row"] in rows]
        assert generated == recorded, frame["frame"]

    def score(packet):
        host = host_bounds(packet, rows)
        if host is None:
            return None
        edge_error = sum(abs(h["left"] - a["left"] * 0.4) +
                         abs(h["right"] - a["right"] * 0.4)
                         for a, h in zip(arcade, host)) / (2 * len(rows))
        width_error = sum(abs(h["width"] - a["width"] * 0.4)
                          for a, h in zip(arcade, host)) / len(rows)
        return {"packet": list(packet), "host_rows": host,
                "mean_absolute_edge_error": round(edge_error, 6),
                "mean_absolute_width_error": round(width_error, 6)}

    existing = [score(frame["camera_packet"]) for frame in metrics["frames"]]
    best_existing = min(existing, key=lambda item: item["mean_absolute_edge_error"])
    best_existing_width = min(existing, key=lambda item: item["mean_absolute_width_error"])
    candidates = (score((curve, 0, 0, 4, texture))
                  for curve in range(len(CURVE_SINE)) for texture in range(48))
    best = min((item for item in candidates if item is not None),
               key=lambda item: item["mean_absolute_edge_error"])
    result = {"mapping": "x_sega=0.4*x_arcade; y_sega=y_arcade-128",
              "arcade_rows": [{"screen_y": item["y"], "left": item["left"],
                               "right": item["right"], "width": item["width"]}
                              for item in arcade],
              "existing_60_best_edges": best_existing,
              "existing_60_best_width": best_existing_width,
              "independent_curve_texture_best_edges": best,
              "curve_count": len(CURVE_SINE), "texture_count": 48}
    output = root / "phase1b-steer-host-comparison.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("run", "analyze", "compare"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--host-metrics", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if args.action == "run":
        assert args.mame and args.rompath and args.state
        run(root, args.mame, args.rompath, args.state)
    elif args.action == "analyze":
        analyze(root)
    else:
        assert args.host_metrics
        compare(root, args.host_metrics)
