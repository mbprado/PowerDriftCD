#!/usr/bin/env python3
"""Search private callback-970 Y-sprite source ranges for the visible right edge."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from phase1b_mild_steer_width import digest, scan
from phase1b_swap_compare import png_rows


DEFAULT_CALLBACK = 970
PULSE = 112
DEFAULT_GROUPS = ((0xE000, 0x0800), (0x0000, 0x10000))


def group_name(start, size):
    return f"{start:04X}-{size:05X}"


def trial_name(callback, name):
    prefix = "phase1b-right-search-"
    return prefix + (f"{callback}-" if callback != DEFAULT_CALLBACK else "") + name


def case_name(start, size, exact_slots):
    name = group_name(start, size)
    if exact_slots:
        name += "-only-" + "-".join(f"{slot:04X}" for slot in exact_slots)
    return name


def run(root, mame, rompath, state, groups, callback, exact_slots):
    baseline = root / "phase1b-mild-steer-112"
    original = (baseline / f"source-{callback:04d}-ysprites.bin").read_bytes()
    assert len(original) == 0x10000
    script = Path(__file__).resolve().with_name("phase1b_mame_input.lua")
    for start, size in groups:
        name = case_name(start, size, exact_slots)
        raw = bytearray(original)
        slots = []
        for slot in range(start, start + size, 16):
            if exact_slots and slot not in exact_slots:
                continue
            if raw[slot] & 0x10 == 0:
                raw[slot] |= 0x10
                slots.append(slot)
        assert slots
        override = root / f"{trial_name(callback, name)}-source.bin"
        override.write_bytes(raw)
        trial = root / trial_name(callback, name)
        trial.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({"SDL_VIDEODRIVER": "dummy", "PDRIFT_SNAPSHOT_DIR": ".",
                    "PDRIFT_SWAP_DIR": ".", "PDRIFT_SOURCE_DIR": ".",
                    "PDRIFT_SEQUENCE_END_FRAME": "976",
                    "PDRIFT_STATE_LOAD": str(state.resolve()),
                    "PDRIFT_STEER_PULSE": str(PULSE),
                    "PDRIFT_SOURCE_OVERRIDE_FRAME": str(callback),
                    "PDRIFT_SOURCE_OVERRIDE_RANGE": f"{start:04X}:{size:05X}",
                    "PDRIFT_SOURCE_OVERRIDE": str(override.resolve())})
        cmd = [str(mame.resolve()), "pdrift", "-rompath", str(rompath.resolve()),
               "-noreadconfig", "-video", "none", "-sound", "none",
               "-nothrottle", "-seconds_to_run", "18", "-autoboot_script",
               str(script)]
        with (trial / "phase1b-input.log").open("w") as log:
            subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        print(name, "hidden slots", len(slots), "replay complete", flush=True)


def analyze(root, groups, callback, exact_slots):
    baseline = root / "phase1b-mild-steer-112"
    source = (baseline / f"source-{callback:04d}-ysprites.bin").read_bytes()
    screen = callback + 1
    before = png_rows(baseline / f"swap-screen-{screen:04d}.png")
    boundaries = scan(before, screen)
    records = []
    for start, size in groups:
        name = case_name(start, size, exact_slots)
        trial = root / trial_name(callback, name)
        override = root / f"{trial_name(callback, name)}-source.bin"
        after = (trial / f"source-{callback:04d}-ysprites-after.bin").read_bytes()
        assert after == override.read_bytes()
        changed = [i for i, (a, b) in enumerate(zip(source, after)) if a != b]
        assert changed and all(i % 16 == 0 and start <= i < start + size
                               and after[i] == source[i] | 0x10 for i in changed)
        if exact_slots:
            assert changed == list(exact_slots)
        for frame in range(960, screen):
            path = f"swap-screen-{frame:04d}.png"
            assert png_rows(trial / path) == png_rows(baseline / path)
        hidden = png_rows(trial / f"swap-screen-{screen:04d}.png")
        rows = []
        for b in boundaries:
            y = b["y"]
            changes = [x for x in range(320)
                       if before[y][3*x:3*x+3] != hidden[y][3*x:3*x+3]]
            rows.append({**b, "left_changed": b["left"] in changes,
                         "right_changed": b["right"] in changes,
                         "change_min": min(changes) if changes else None,
                         "change_max": max(changes) if changes else None})
        records.append({"group": name, "slots_hidden": len(changed),
                        "source_override_sha256": digest(override),
                        "screen_sha256": digest(trial / f"swap-screen-{screen:04d}.png"),
                        "rows": rows})
        print(name, [(r["y"], r["left_changed"], r["right_changed"])
                     for r in rows])
    output = root / f"{trial_name(callback, case_name(*groups[0], exact_slots))}.json"
    output.write_text(json.dumps({"callback": callback, "pulse": PULSE,
                                  "baseline_source_sha256": digest(baseline / f"source-{callback:04d}-ysprites.bin"),
                                  "baseline_screen_sha256": digest(baseline / f"swap-screen-{screen:04d}.png"),
                                  "records": records}, indent=2) + "\n")
    print("private result:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("run", "analyze"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--groups", nargs="+", help="hex START:SIZE pairs")
    parser.add_argument("--callback", type=int, default=DEFAULT_CALLBACK)
    parser.add_argument("--exact-slots", nargs="+", help="hide only these hex slots")
    args = parser.parse_args()
    root = args.private_root.resolve()
    exact_slots = tuple(sorted(int(item, 16) for item in args.exact_slots)) if args.exact_slots else ()
    if exact_slots:
        assert not args.groups and len(set(exact_slots)) == len(exact_slots)
        groups = ((exact_slots[0], exact_slots[-1] - exact_slots[0] + 16),)
    else:
        groups = tuple(tuple(int(part, 16) for part in item.split(":"))
                       for item in args.groups) if args.groups else DEFAULT_GROUPS
    assert all(start % 16 == 0 and size % 16 == 0 and size > 0
               and start + size <= 0x10000 for start, size in groups)
    assert 960 <= args.callback <= 975
    if args.action == "run":
        assert args.mame and args.rompath and args.state
        run(root, args.mame, args.rompath, args.state, groups, args.callback,
            exact_slots)
    else:
        analyze(root, groups, args.callback, exact_slots)
