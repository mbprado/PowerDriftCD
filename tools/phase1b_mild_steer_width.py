#!/usr/bin/env python3
"""Replay mild arcade steering and audit two visible road-sand boundaries."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from phase1b_right_extent import right_sand_boundary
from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import png_rows


PULSES = (None, 112, 96)
FRAMES = range(960, 977)
HIDE_SLOT = 0xE610


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_dir(root, pulse):
    return root / f"phase1b-mild-steer-{pulse if pulse is not None else 'center'}"


def run(root, mame, rompath, state):
    script = Path(__file__).resolve().with_name("phase1b_mame_input.lua")
    for pulse in PULSES:
        trial = trial_dir(root, pulse)
        trial.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({"SDL_VIDEODRIVER": "dummy",
                    "PDRIFT_SNAPSHOT_DIR": ".", "PDRIFT_SWAP_DIR": ".",
                    "PDRIFT_SOURCE_DIR": ".",
                    "PDRIFT_GEOMETRY_SAMPLE_DIR": ".",
                    "PDRIFT_SEQUENCE_END_FRAME": "976",
                    "PDRIFT_STATE_LOAD": str(state.resolve())})
        env.pop("PDRIFT_STEER_PULSE", None)
        if pulse is not None:
            env["PDRIFT_STEER_PULSE"] = str(pulse)
        cmd = [str(mame.resolve()), "pdrift", "-rompath", str(rompath.resolve()),
               "-noreadconfig", "-video", "none", "-sound", "none",
               "-nothrottle", "-seconds_to_run", "18", "-autoboot_script",
               str(script)]
        with (trial / "phase1b-input.log").open("w") as log:
            subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        assert all((trial / f"swap-screen-{frame:04d}.png").exists()
                   for frame in FRAMES)
        print(pulse if pulse is not None else "center", "replay complete")


def scan(rows, screen_frame):
    detected = []
    for y in range(130, 191):
        try:
            left = boundary(rows[y], y)[0]
        except ValueError:
            continue
        right = right_sand_boundary(rows[y])
        if right is not None and right > left:
            detected.append({"screen_frame": screen_frame, "y": y,
                             "left": left, "right": right,
                             "width": right - left + 1})
    return detected


def analyze(root):
    previous = root / "phase1b-depth-sequence-center"
    center = trial_dir(root, None)
    controls = []
    for frame in FRAMES:
        name = f"swap-screen-{frame:04d}.png"
        current, prior = center / name, previous / name
        controls.append({"screen_frame": frame,
                         "same_rgb": png_rows(current) == png_rows(prior),
                         "current_sha256": digest(current),
                         "previous_sha256": digest(prior)})
    assert all(item["same_rgb"] for item in controls)
    assert ((center / "source-0974-ysprites.bin").read_bytes() ==
            (previous / "source-0974-ysprites.bin").read_bytes())
    cases = []
    for pulse in PULSES:
        trial = trial_dir(root, pulse)
        detected = []
        screenshots = {}
        for frame in FRAMES:
            path = trial / f"swap-screen-{frame:04d}.png"
            rows = png_rows(path)
            detected.extend(scan(rows, frame))
            screenshots[str(frame)] = digest(path)
        cases.append({"pulse": pulse if pulse is not None else 128,
                      "screen_sha256": screenshots,
                      "source_974_sha256": digest(trial / "source-0974-ysprites.bin"),
                      "two_sided_rows": detected})
        frame975 = [r for r in detected if r["screen_frame"] == 975]
        print("pulse", pulse if pulse is not None else 128,
              "frame975 rows", len(frame975),
              "all rows", len(detected))
    output = root / "phase1b-mild-steer-width.json"
    output.write_text(json.dumps({"center_controls": controls,
                                  "cases": cases}, indent=2) + "\n")
    print("private result:", output)


def hide_trial(root, mame, rompath, state):
    """Hide the candidate $3400 strip for pulse 112 at callback 974."""
    baseline = trial_dir(root, 112)
    source = baseline / "source-0974-ysprites.bin"
    raw = bytearray(source.read_bytes())
    assert len(raw) == 0x10000 and raw[HIDE_SLOT] & 0x10 == 0
    assert raw[HIDE_SLOT + 6:HIDE_SLOT + 8] == bytes.fromhex("3888")
    raw[HIDE_SLOT] |= 0x10
    override = root / "phase1b-mild-steer-112-hide-source.bin"
    override.write_bytes(raw)
    trial = root / "phase1b-mild-steer-112-hidden"
    trial.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"SDL_VIDEODRIVER": "dummy", "PDRIFT_SNAPSHOT_DIR": ".",
                "PDRIFT_SWAP_DIR": ".", "PDRIFT_SOURCE_DIR": ".",
                "PDRIFT_SEQUENCE_END_FRAME": "976",
                "PDRIFT_STATE_LOAD": str(state.resolve()),
                "PDRIFT_STEER_PULSE": "112",
                "PDRIFT_SOURCE_OVERRIDE_FRAME": "974",
                "PDRIFT_SOURCE_OVERRIDE_RANGE": "E610:0010",
                "PDRIFT_SOURCE_OVERRIDE": str(override.resolve())})
    cmd = [str(mame.resolve()), "pdrift", "-rompath", str(rompath.resolve()),
           "-noreadconfig", "-video", "none", "-sound", "none",
           "-nothrottle", "-seconds_to_run", "18", "-autoboot_script",
           str(Path(__file__).resolve().with_name("phase1b_mame_input.lua"))]
    with (trial / "phase1b-input.log").open("w") as log:
        subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    after = (trial / "source-0974-ysprites-after.bin").read_bytes()
    assert [i for i, (a, b) in enumerate(zip(source.read_bytes(), after))
            if a != b] == [HIDE_SLOT]
    for frame in range(960, 975):
        assert png_rows(trial / f"swap-screen-{frame:04d}.png") == png_rows(
            baseline / f"swap-screen-{frame:04d}.png")
    before_rows = png_rows(baseline / "swap-screen-0975.png")
    hidden_rows = png_rows(trial / "swap-screen-0975.png")
    measurements = []
    for y in range(153, 163):
        b = next((r for r in scan(before_rows, 975) if r["y"] == y), None)
        if b is None:
            continue
        changes = [x for x in range(320)
                   if before_rows[y][3 * x:3 * x + 3] !=
                   hidden_rows[y][3 * x:3 * x + 3]]
        measurements.append({"y": y, "left": b["left"], "right": b["right"],
                             "changed_pixels": len(changes),
                             "left_changed": b["left"] in changes,
                             "right_changed": b["right"] in changes,
                             "change_min": min(changes) if changes else None,
                             "change_max": max(changes) if changes else None})
    result = {"source_sha256": digest(source),
              "override_sha256": digest(override),
              "hidden_screen_975_sha256": digest(trial / "swap-screen-0975.png"),
              "measurements": measurements}
    accepted = [row for row in measurements if 154 <= row["y"] <= 159]
    assert len(accepted) == 6 and all(
        row["left_changed"] and row["right_changed"] for row in accepted)
    output = root / "phase1b-mild-steer-112-hide.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(measurements, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("run", "analyze", "hide"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if args.action in ("run", "hide"):
        assert args.mame and args.rompath and args.state
        if args.action == "run":
            run(root, args.mame, args.rompath, args.state)
        else:
            hide_trial(root, args.mame, args.rompath, args.state)
    else:
        analyze(root)
