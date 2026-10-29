#!/usr/bin/env python3
"""Run or score a bounded private callback-991 Y-sprite hide."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from phase1b_swap_compare import png_rows


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "build/private"
BASELINE = PRIVATE / "phase1b-render989-baseline"
MAME = Path("/private/tmp/pd-mame0289-render989/mame")
ROMPATH = PRIVATE / "phase1b-roms"
STATE = PRIVATE / "phase1b-range-state-seed/callback950.sta"
LUA = ROOT / "tools/phase1b_mame_input.lua"
SAMPLES = ((220, 180), (240, 180), (260, 180))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paths(start, size, repeat):
    suffix = f"-r{repeat}" if repeat else ""
    stem = f"phase1b-render989-narrow-{start:04X}-{size:04X}{suffix}"
    return PRIVATE / stem, PRIVATE / f"{stem}-source.bin"


def checked_source(start, size):
    assert start % 16 == size % 16 == 0 and size > 0
    assert 0xE000 <= start and start + size <= 0xF000
    source = (BASELINE / "source-0991-ysprites.bin").read_bytes()
    assert len(source) == 0x10000
    slots = [slot for slot in range(start, start + size, 16)
             if not source[slot] & 0x10]
    assert slots
    return source, slots


def run(start, size, repeat):
    source, slots = checked_source(start, size)
    trial, override = paths(start, size, repeat)
    assert not trial.exists() and not override.exists(), "trial already frozen"
    changed = bytearray(source)
    for slot in slots:
        changed[slot] |= 0x10
    override.write_bytes(changed)
    trial.mkdir()
    env = os.environ.copy()
    env.update({"SDL_VIDEODRIVER": "dummy", "PDRIFT_SNAPSHOT_DIR": ".",
                "PDRIFT_SWAP_DIR": ".", "PDRIFT_SOURCE_DIR": ".",
                "PDRIFT_YBITMAP_DIR": ".", "PDRIFT_CAPTURE_PROFILE": "road-edge",
                "PDRIFT_SEQUENCE_END_FRAME": "1000",
                "PDRIFT_STATE_LOAD": str(STATE.resolve()),
                "PDRIFT_STEER_PULSE": "56",
                "PDRIFT_SOURCE_OVERRIDE_FRAME": "991",
                "PDRIFT_SOURCE_OVERRIDE_RANGE": f"{start:04X}:{size:04X}",
                "PDRIFT_SOURCE_OVERRIDE": str(override.resolve())})
    cmd = [str(MAME), "pdrift", "-rompath", str(ROMPATH),
           "-noreadconfig", "-video", "none", "-sound", "none",
           "-nothrottle", "-seconds_to_run", "18", "-debug",
           "-debugger", "none", "-debuglog", "-autoboot_script", str(LUA)]
    with (trial / "phase1b-input.log").open("w") as log:
        subprocess.run(cmd, cwd=trial, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    print("fresh MAME replay", f"{start:04X}:{size:04X}", "bytes", len(slots))


def score(start, size, repeat):
    source, slots = checked_source(start, size)
    trial, override = paths(start, size, repeat)
    changed = override.read_bytes()
    assert len(changed) == len(source)
    assert [i for i, (a, b) in enumerate(zip(source, changed)) if a != b] == slots
    assert (trial / "source-0991-ysprites.bin").read_bytes() == source
    assert (trial / "source-0991-ysprites-after.bin").read_bytes() == changed
    prior_equal = all(png_rows(BASELINE / f"swap-screen-{f:04d}.png") ==
                      png_rows(trial / f"swap-screen-{f:04d}.png")
                      for f in range(960, 992))
    assert prior_equal
    before = png_rows(BASELINE / "swap-screen-0992.png")
    after = png_rows(trial / "swap-screen-0992.png")
    samples = []
    for x, y in SAMPLES:
        old, new = before[y][3*x:3*x+3], after[y][3*x:3*x+3]
        samples.append({"x": x, "y": y, "before": list(old),
                        "after": list(new), "changed": old != new})
    native_before = (BASELINE / "ybitmap-0990.raw").read_bytes()
    native_after = (trial / "ybitmap-0990.raw").read_bytes()
    assert len(native_before) == len(native_after) == 512 * 512 * 2
    result = {"schema": 1, "pulse": 56, "callback": 991,
              "render_frame": 990, "screen": 992,
              "range": f"{start:04X}:{size:04X}", "repeat": repeat,
              "hide_bytes_changed": len(slots), "prior_screens_equal": prior_equal,
              "sample_pixels": samples,
              "screen_pixels_changed": sum(a[i:i+3] != b[i:i+3]
                                           for a, b in zip(before, after)
                                           for i in range(0, len(a), 3)),
              "native_words_changed": sum(native_before[i:i+2] != native_after[i:i+2]
                                          for i in range(0, len(native_before), 2)),
              "override_sha256": sha(override),
              "screen_sha256": sha(trial / "swap-screen-0992.png"),
              "native_sha256": sha(trial / "ybitmap-0990.raw")}
    output = PRIVATE / f"{trial.name}.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["range"], [p["changed"] for p in samples],
          "screen pixels", result["screen_pixels_changed"],
          "native words", result["native_words_changed"])
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
