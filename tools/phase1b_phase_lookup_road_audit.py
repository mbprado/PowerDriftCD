#!/usr/bin/env python3
"""Audit a private arcade phase-lookup intervention and road-edge attribution."""

import csv
import hashlib
import json
from pathlib import Path

from phase1b_mild_steer_width import scan
from phase1b_swap_compare import changed_pixels, png_rows


ROOT = Path(__file__).resolve().parents[1] / "build/private"
CONTROL = ROOT / "phase1b-phase-road-control-frame961-204"
SMALL = ROOT / "phase1b-phase-road-plus20-204"
LATE = ROOT / "phase1b-phase-road-plus1c0-204"
CHANGED = ROOT / "phase1b-phase-road-plus1c0-frame961-204"
REPEATS = (CHANGED, ROOT / "phase1b-phase-road-plus1c0-frame961-r1",
           ROOT / "phase1b-phase-road-plus1c0-frame961-r2")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(image, x, y):
    return bytes(image[y][3 * x:3 * x + 3])


def slot(trial, frame, offset):
    return (trial / f"source-{frame:04d}-ysprites.bin").read_bytes()[offset:offset + 16]


def geometry(trial):
    return {(int(row["frame"]), int(row["index"])): row
            for row in csv.DictReader((trial / "geometry-samples.csv").open())}


def main():
    control_log = (CONTROL / "debug.log").read_text()
    changed_log = (CHANGED / "debug.log").read_text()
    assert "PHASE_LOOKUP_ENTRY pc=03454E old=02F4" in changed_log
    assert "PHASE_LOOKUP_CHANGED value=04B4" in changed_log
    assert "PHASE_LOOKUP_INDEX pc=034B02 index=001B changed=04B4" in changed_log
    assert "PHASE_LOOKUP_RESTORED value=02F4" in changed_log
    assert "PHASE_LOOKUP_INDEX pc=034B02 index=0025 changed=02F4" in control_log
    assert (changed_log.index("PHASE_LOOKUP_CHANGED") <
            changed_log.index("PHASE_LOOKUP_INDEX") <
            changed_log.index("PHASE_LOOKUP_RESTORED"))
    before = geometry(CONTROL)
    after = geometry(CHANGED)
    assert before.keys() == after.keys()
    assert (before[962, 0]["global1c"], after[962, 0]["global1c"]) == ("E808", "E812")
    assert (before[962, 0]["global1e"], after[962, 0]["global1e"]) == ("FB23", "FB25")
    projected = [(frame, index) for (frame, index), row in before.items()
                 if row["projected4"] != after[frame, index]["projected4"]
                 or row["projected6"] != after[frame, index]["projected6"]]
    assert projected and min(frame for frame, _ in projected) == 964
    assert (CONTROL / "shared-list-0963.bin").read_bytes() == \
           (CHANGED / "shared-list-0963.bin").read_bytes()
    assert (CONTROL / "shared-list-0964.bin").read_bytes() != \
           (CHANGED / "shared-list-0964.bin").read_bytes()
    screen_changes = {}
    for frame in range(960, 983):
        name = f"swap-screen-{frame:04d}.png"
        baseline = png_rows(CONTROL / name)
        different = changed_pixels(baseline, png_rows(CHANGED / name))
        screen_changes[frame] = different
        assert changed_pixels(baseline, png_rows(SMALL / name)) == 0
        for repeat in REPEATS[1:]:
            assert sha(repeat / name) == sha(CHANGED / name)
    assert all(screen_changes[frame] == 0 for frame in range(960, 965))
    assert all(screen_changes[frame] > 0 for frame in range(965, 970))
    assert slot(CONTROL, 966, 0xe630) == slot(LATE, 966, 0xe630)
    assert slot(CONTROL, 967, 0xc630) == slot(LATE, 967, 0xc630)
    assert sha(CONTROL / "geometry-samples.csv") == sha(SMALL / "geometry-samples.csv")
    for repeat in REPEATS[1:]:
        assert sha(repeat / "geometry-samples.csv") == sha(CHANGED / "geometry-samples.csv")
        for frame in (966, 967):
            assert sha(repeat / f"source-{frame:04d}-ysprites.bin") == \
                   sha(CHANGED / f"source-{frame:04d}-ysprites.bin")
    edges = []
    for screen, source_frame, address in ((967, 966, 0xe630), (968, 967, 0xc630)):
        assert slot(CONTROL, source_frame, address) != slot(CHANGED, source_frame, address)
        assert slot(CHANGED, source_frame, address)[6:8] == bytes.fromhex("3888")
        hide = ROOT / f"phase1b-phase-road-plus1c0-hide-{address:04X}"
        raw = (CHANGED / f"source-{source_frame:04d}-ysprites.bin").read_bytes()
        edited = (ROOT / f"phase1b-phase-road-plus1c0-hide-{address:04X}.bin").read_bytes()
        assert len(raw) == len(edited) == 0x10000
        assert [i for i, (a, b) in enumerate(zip(raw, edited)) if a != b] == [address]
        assert edited[address] == raw[address] | 0x10
        log = (hide / "phase1b-input.log").read_text()
        assert f"SOURCE_OVERRIDE,{source_frame},ysprites,{address:04X},0010," in log
        normal = png_rows(CHANGED / f"swap-screen-{screen:04d}.png")
        hidden = png_rows(hide / f"swap-screen-{screen:04d}.png")
        baseline = png_rows(CONTROL / f"swap-screen-{screen:04d}.png")
        rows = [row for row in scan(normal, screen) if 159 <= row["y"] <= 163]
        old = [row for row in scan(baseline, screen) if 159 <= row["y"] <= 163]
        assert len(rows) == len(old) == (3 if screen == 967 else 5)
        assert all(row["left"] > prior["left"] for row, prior in zip(rows, old))
        assert all(rgb(normal, row["left"], row["y"]) !=
                   rgb(hidden, row["left"], row["y"]) for row in rows)
        assert all(sha(hide / f"swap-screen-{frame:04d}.png") ==
                   sha(CHANGED / f"swap-screen-{frame:04d}.png")
                   for frame in range(960, screen))
        edges.append({"screen": screen, "slot": f"{address:04X}",
                      "control_left": [row["left"] for row in old],
                      "changed_left": [row["left"] for row in rows],
                      "hide_changed_left": len(rows)})
    result = {"status": "PASS", "source_revision": "4dd7cec",
              "control_debug_sha256": sha(CONTROL / "debug.log"),
              "changed_debug_sha256": sha(CHANGED / "debug.log"),
              "screen_changed_pixels": {str(k): v for k, v in screen_changes.items() if v},
              "projected_rows_changed": len(projected), "edges": edges,
              "repeated_screen967_sha256": [sha(run / "swap-screen-0967.png")
                                                 for run in REPEATS],
              "limitation": "The intervention changes a derived lookup offset, not a naturally varying camera phase; this does not calibrate the Sega CD packet."}
    output = ROOT / "phase1b-phase-lookup-road-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS", len(projected), "projected rows;", sum(x["hide_changed_left"]
          for x in edges), "sampled left pixels", sha(output))


if __name__ == "__main__":
    main()
