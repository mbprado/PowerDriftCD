#!/usr/bin/env python3
"""Audit private pulse-56/204 exact-slot Y-sprite interventions."""

import hashlib
import json
from pathlib import Path

from phase1b_swap_compare import png_rows


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "build/private"
SLOT = 0xE5D0
NATIVE_FRAMES = range(988, 996)
SCREEN_FRAMES = range(960, 1001)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_paths(pulse):
    if pulse == 56:
        baseline = PRIVATE / "phase1b-render989-baseline"
        stem = "phase1b-render989-narrow-E5D0-0010"
    else:
        baseline = PRIVATE / "phase1b-render989-pulse204-baseline"
        stem = "phase1b-render989-pulse204-E5D0"
    return baseline, [PRIVATE / stem, PRIVATE / (stem + "-r1"),
                      PRIVATE / (stem + "-r2")]


def screen_changes(baseline, trial):
    changed = []
    target_pixels = []
    for frame in SCREEN_FRAMES:
        a = png_rows(baseline / f"swap-screen-{frame:04d}.png")
        b = png_rows(trial / f"swap-screen-{frame:04d}.png")
        pixels = [(x, y) for y, (old, new) in enumerate(zip(a, b))
                  for x in range(320)
                  if old[3*x:3*x+3] != new[3*x:3*x+3]]
        if pixels:
            changed.append(frame)
            if frame == 992:
                target_pixels = pixels
    assert changed == [992]
    return target_pixels


def native_changes(baseline, trial):
    changed = []
    target_words = 0
    for frame in NATIVE_FRAMES:
        a = (baseline / f"ybitmap-{frame:04d}.raw").read_bytes()
        b = (trial / f"ybitmap-{frame:04d}.raw").read_bytes()
        assert len(a) == len(b) == 512 * 512 * 2
        words = sum(a[i:i+2] != b[i:i+2] for i in range(0, len(a), 2))
        if words:
            changed.append(frame)
            if frame == 990:
                target_words = words
    assert changed == [990]
    return target_words


def writer(pulse):
    log = (PRIVATE / f"phase1b-render989-pulse{pulse}-E5D0-writer"
           / "debug.log")
    frame = None
    found = []
    for line in log.read_text().splitlines():
        if line.startswith("SEQUENCE_FRAME,"):
            frame = int(line.split(",")[1])
        if frame == 989 and line.startswith("YSPRITE_REGS addr=18E5D0 "):
            found.append(line)
    assert len(found) == 1
    assert "pc=00E0A8" in found[0] and "a2=18C5D2" in found[0]
    return {"callback_interval": 989, "pc": "00E0A8",
            "source_pointer_after_read": "18C5D2", "log_sha256": digest(log)}


def audit(pulse):
    baseline, trials = trial_paths(pulse)
    source = (baseline / "source-0991-ysprites.bin").read_bytes()
    assert len(source) == 0x10000 and not source[SLOT] & 0x10
    artifacts = ["source-0991-ysprites-after.bin", "ybitmap-0990.raw",
                 "swap-screen-0992.png"]
    for trial in trials:
        assert (trial / "source-0991-ysprites.bin").read_bytes() == source
        changed = (trial / artifacts[0]).read_bytes()
        assert [i for i, (a, b) in enumerate(zip(source, changed))
                if a != b] == [SLOT]
        assert changed[SLOT] == source[SLOT] | 0x10
    for artifact in artifacts:
        assert len({digest(trial / artifact) for trial in trials}) == 1
    pixels = screen_changes(baseline, trials[0])
    words = native_changes(baseline, trials[0])
    xs, ys = zip(*pixels)
    return {"pulse": pulse, "slot": f"{SLOT:04X}", "callback": 991,
            "native_frame": 990, "screen": 992, "repeats": len(trials),
            "native_words_changed": words, "screen_pixels_changed": len(pixels),
            "screen_bbox": [min(xs), min(ys), max(xs), max(ys)],
            "screen_row180_changed_range": [min(x for x, y in pixels if y == 180),
                                            max(x for x, y in pixels if y == 180)],
            "baseline_screen_sha256": digest(baseline / artifacts[2]),
            "trial_screen_sha256": digest(trials[0] / artifacts[2]),
            "trial_native_sha256": digest(trials[0] / artifacts[1]),
            "trial_source_after_sha256": digest(trials[0] / artifacts[0]),
            "writer": writer(pulse)}


def main():
    records = [audit(pulse) for pulse in (56, 204)]
    result = {"schema": 1, "evidence": "MAME execution, not hardware",
              "records": records}
    output = PRIVATE / "phase1b-dual-roadslot-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    for record in records:
        print(record["pulse"], record["screen_pixels_changed"],
              record["native_words_changed"], record["screen_bbox"])
    print("private result", output)


if __name__ == "__main__":
    main()
