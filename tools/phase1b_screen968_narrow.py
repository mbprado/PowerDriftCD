#!/usr/bin/env python3
"""Run or score a bounded private pulse-204 screen-968 descriptor hide."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from phase1b_mild_steer_width import scan
from phase1b_road_only_contour import edge_stage, load_layer
from phase1b_strip_rotation_prediction import affine
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import map_pixel, source_words


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "build/private"
BASELINE = PRIVATE / "phase1b-pulse204-screen968-native-baseline"
MAME = Path("/private/tmp/pd-mame0289-native968/mame")
ROMPATH = PRIVATE / "phase1b-roms"
STATE = PRIVATE / "phase1b-range-state-seed/callback950.sta"
LUA = ROOT / "tools/phase1b_mame_input.lua"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paths(start, size, repeat=0):
    name = f"{start:04X}-{size:04X}" + (f"-r{repeat}" if repeat else "")
    return (PRIVATE / f"phase1b-pulse204-screen968-native-{name}",
            PRIVATE / f"phase1b-pulse204-screen968-{name}-source.bin")


def checked_slots(start, size):
    assert start % 16 == size % 16 == 0 and size > 0
    assert 0xc000 <= start and start + size <= 0xd000
    source = (BASELINE / "source-0967-ysprites.bin").read_bytes()
    assert len(source) == 0x10000
    return source, [slot for slot in range(start, start + size, 16)
                    if not source[slot] & 0x10]


def run(start, size, repeat=0):
    source, slots = checked_slots(start, size)
    assert slots
    trial, override = paths(start, size, repeat)
    assert not trial.exists() and not override.exists(), "trial already frozen"
    hidden = bytearray(source)
    for slot in slots:
        hidden[slot] |= 0x10
    override.write_bytes(hidden)
    trial.mkdir()
    env = os.environ.copy()
    env.update({"SDL_VIDEODRIVER": "dummy", "PDRIFT_SNAPSHOT_DIR": ".",
                "PDRIFT_SWAP_DIR": ".", "PDRIFT_SOURCE_DIR": ".",
                "PDRIFT_YBITMAP_DIR": ".", "PDRIFT_LAYER_ROWS_DIR": ".",
                "PDRIFT_CAPTURE_PROFILE": "road-edge",
                "PDRIFT_SEQUENCE_END_FRAME": "982",
                "PDRIFT_STATE_LOAD": str(STATE.resolve()),
                "PDRIFT_STEER_PULSE": "204",
                "PDRIFT_SOURCE_OVERRIDE_FRAME": "967",
                "PDRIFT_SOURCE_OVERRIDE_RANGE": f"{start:04X}:{size:04X}",
                "PDRIFT_SOURCE_OVERRIDE": str(override.resolve())})
    cmd = [str(MAME), "pdrift", "-rompath", str(ROMPATH),
           "-noreadconfig", "-video", "none", "-sound", "none",
           "-nothrottle", "-seconds_to_run", "18", "-autoboot_script",
           str(LUA)]
    with (trial / "phase1b-input.log").open("w") as log:
        subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    print("fresh MAME replay", f"{start:04X}:{size:04X}", "slots", len(slots))


def score(start, size, repeat=0):
    source, slots = checked_slots(start, size)
    trial, override = paths(start, size, repeat)
    hidden = override.read_bytes()
    assert len(hidden) == len(source)
    assert [i for i, (a, b) in enumerate(zip(source, hidden)) if a != b] == slots
    assert all(hidden[slot] == source[slot] | 0x10 for slot in slots)
    assert (trial / "source-0967-ysprites.bin").read_bytes() == source
    assert (trial / "source-0967-ysprites-after.bin").read_bytes() == hidden
    for frame in range(960, 968):
        name = f"swap-screen-{frame:04d}.png"
        assert png_rows(BASELINE / name) == png_rows(trial / name), frame
    baseline_screen = png_rows(BASELINE / "swap-screen-0968.png")
    trial_screen = png_rows(trial / "swap-screen-0968.png")
    rows = [row for row in scan(baseline_screen, 968) if 159 <= row["y"] <= 163]
    assert [row["y"] for row in rows] == list(range(159, 164))
    layer = load_layer(BASELINE / "layer-rows-0967.csv")
    transform = affine(BASELINE, "pre", 966)
    before, _ = source_words(BASELINE, 967)
    after, _ = source_words(trial, 967)
    observations = []
    for row in rows:
        sides = []
        for side in ("left", "right"):
            x, y = row[side], row["y"]
            assert edge_stage(layer[y][x]) == "clear_rotation"
            sx, sy = map_pixel(transform, x, y)
            index = sy * 512 + sx
            assert before[index] != 0xffff
            sides.append({"side": side, "screen_x": x,
                          "screen_changed": baseline_screen[y][3*x:3*x+3] !=
                              trial_screen[y][3*x:3*x+3],
                          "native_transparent": after[index] == 0xffff})
        observations.append({"y": row["y"], "sides": sides})
    vector = [(s["screen_changed"], s["native_transparent"])
              for row in observations for s in row["sides"]]
    result = {"schema": 1, "pulse": 204, "callback": 967,
              "screen": 968, "start": f"{start:04X}", "size": f"{size:04X}",
              "repeat": repeat,
              "slots_hidden": len(slots), "prior_screens_equal": True,
              "screen_changed": sum(v[0] for v in vector),
              "native_transparent": sum(v[1] for v in vector),
              "vector": vector, "rows": observations,
              "override_sha256": sha(override),
              "log_sha256": sha(trial / "phase1b-input.log"),
              "screen_sha256": sha(trial / "swap-screen-0968.png"),
              "native967_sha256": sha(trial / "ybitmap-0967.raw")}
    suffix = f"-r{repeat}" if repeat else ""
    output = PRIVATE / f"phase1b-pulse204-screen968-{start:04X}-{size:04X}{suffix}.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{start:04X}:{size:04X}", "RGB", result["screen_changed"],
          "native", result["native_transparent"], "vector", vector)
    print("private result", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "score"))
    parser.add_argument("start", type=lambda x: int(x, 16))
    parser.add_argument("size", type=lambda x: int(x, 16))
    parser.add_argument("--repeat", type=int, default=0)
    args = parser.parse_args()
    assert 0 <= args.repeat <= 3
    if args.action == "run":
        run(args.start, args.size, args.repeat)
    else:
        score(args.start, args.size, args.repeat)


if __name__ == "__main__":
    main()
