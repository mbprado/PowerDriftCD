#!/usr/bin/env python3
"""Audit private changed-projection road-edge layers and position provenance."""

import hashlib
import json
from pathlib import Path

from phase1b_mild_steer_width import scan
from phase1b_road_only_contour import edge_stage, load_layer
from phase1b_strip_rotation_prediction import affine
from phase1b_swap_compare import changed_pixels, png_rows
from phase1b_ybitmap_map import map_pixel, source_words


ROOT = Path(__file__).resolve().parents[1] / "build/private"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(image, x, y):
    return bytes(image[y][3 * x:3 * x + 3])


def main():
    baseline = ROOT / "phase1b-roadslot-plus100-native-baseline"
    previous = ROOT / "phase1b-roadslot-project-plus100-final"
    source = ROOT / "phase1b-roadslot-upstream-position-204"
    for frame in range(960, 983):
        name = f"swap-screen-{frame:04d}.png"
        assert png_rows(baseline / name) == png_rows(previous / name)
    rows = []
    for screen in (967, 968):
        source_frame = screen - 1
        slot = "E630" if screen == 967 else "C630"
        yhide = ROOT / f"phase1b-roadslot-plus100-native-hide-{slot}"
        old = png_rows(baseline / f"swap-screen-{screen:04d}.png")
        assert old == png_rows(previous / f"swap-screen-{screen:04d}.png")
        yhidden = png_rows(yhide / f"swap-screen-{screen:04d}.png")
        before_y = (baseline / f"source-{source_frame:04d}-ysprites.bin").read_bytes()
        after_y = (yhide / f"source-{source_frame:04d}-ysprites-after.bin").read_bytes()
        slot_address = int(slot, 16)
        assert [i for i, (a, b) in enumerate(zip(before_y, after_y)) if a != b] == [slot_address]
        assert after_y[slot_address] == before_y[slot_address] | 0x10
        transform = affine(baseline, "pre", 966)
        native, _ = source_words(baseline, source_frame)
        hidden_native, _ = source_words(yhide, source_frame)
        layer = load_layer(baseline / f"layer-rows-{source_frame:04d}.csv")
        selected = [r for r in scan(old, screen) if 159 <= r["y"] <= 163]
        assert len(selected) == (3 if screen == 967 else 5)
        for r in selected:
            y = r["y"]
            for side in ("left", "right"):
                x = r[side]
                sx, sy = map_pixel(transform, x, y)
                before, after = native[sy * 512 + sx], hidden_native[sy * 512 + sx]
                stage = edge_stage(layer[y][x])
                changed = rgb(old, x, y) != rgb(yhidden, x, y)
                if side == "left":
                    assert stage == "clear_rotation" and before != 0xffff
                    assert after == 0xffff and changed
                else:
                    assert stage == "16b_occluded" and before == after == 0xffff
                    assert layer[y][x][0] == 0x02e1 and not changed
                rows.append({"screen": screen, "y": y, "side": side,
                             "screen_x": x, "native_xy": [sx, sy],
                             "native_before": f"{before:04X}",
                             "native_after_y_hide": f"{after:04X}",
                             "layer": stage, "rgb_changed_by_y_hide": changed})
    b_before = (baseline / "source-0967-bsprites.bin").read_bytes()
    bhide = ROOT / "phase1b-roadslot-plus100-native-hide-B40-967"
    assert (bhide / "source-0967-bsprites.bin").read_bytes() == b_before
    b_after = (bhide /
               "source-0967-bsprites-after.bin").read_bytes()
    assert [i for i, (a, b) in enumerate(zip(b_before, b_after)) if a != b] == [0x44]
    assert b_after[0x44] == b_before[0x44] | 0x40
    original = png_rows(baseline / "swap-screen-0968.png")
    hidden = png_rows(bhide / "swap-screen-0968.png")
    before_layer = load_layer(baseline / "layer-rows-0967.csv")
    after_layer = load_layer(bhide / "layer-rows-0967.csv")
    right = [r for r in rows if r["screen"] == 968 and r["side"] == "right"]
    assert all(before_layer[r["y"]][r["screen_x"]][0] == 0x2e1
               and after_layer[r["y"]][r["screen_x"]][0] == 0xffff
               and rgb(original, r["screen_x"], r["y"]) !=
               rgb(hidden, r["screen_x"], r["y"]) for r in right)
    assert all(png_rows(baseline / f"swap-screen-{f:04d}.png") ==
               png_rows(bhide / f"swap-screen-{f:04d}.png")
               for f in range(960, 968))
    # The screen-967 B-sprite dependency remains unresolved under the tested
    # callback-965/966 hides, despite the captured layer classification.
    for callback in (965, 966):
        trial = ROOT / f"phase1b-roadslot-plus100-native-hide-B40-{callback}"
        assert changed_pixels(png_rows(baseline / "swap-screen-0967.png"),
                              png_rows(trial / "swap-screen-0967.png")) == 0
    log = (source / "debug.log").read_text()
    events = (
        "UPSTREAM_WRITE cpu=maincpu field=position pc=034AF0 addr=0C0856 data=000017D3",
        "UPSTREAM_WRITE cpu=maincpu field=position pc=034C38 addr=0C0856 data=000017F8",
        "TRANSFORM_POSITION_SOURCE pc=03483C x=17F8",
        "TRANSFORM_WRITE cpu=maincpu pc=034850 addr=0C009C data=0000E808",
        "TRANSFORM_PROJECT pc=033D1E off=FFF5 angle1=0025 angle2=03A0 x=E808",
    )
    offsets = [log.index(item) for item in events]
    assert offsets == sorted(offsets)
    assert (0x17d3 + 0x25) & 0xffff == 0x17f8
    assert (-0x17f8) & 0xffff == 0xe808
    assert sha(source / "phase1b-trial-1020.png") == sha(
        ROOT / "phase1b-roadslot-translation-source-204" / "phase1b-trial-1020.png")
    result = {"status": "PASS", "source_revision": "408b6f1",
              "native_baseline_screen967_sha256": sha(baseline / "swap-screen-0967.png"),
              "native_baseline_966_sha256": sha(baseline / "ybitmap-0966.raw"),
              "native_baseline_967_sha256": sha(baseline / "ybitmap-0967.raw"),
              "b_slot40_override_sha256": sha(ROOT / "phase1b-roadslot-plus100-hide-bsprite0040.bin"),
              "b_slot40_screen968_changed_pixels": changed_pixels(original, hidden),
              "upstream_debug_sha256": sha(source / "debug.log"),
              "upstream_events": list(events), "samples": rows,
              "limits": ["screen967 exact B descriptor timing not verified",
                         "source of adjusted position arithmetic not fully modeled"]}
    output = ROOT / "phase1b-roadslot-native-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS", len(rows), "samples; screen968 B-slot40 hide changed",
          result["b_slot40_screen968_changed_pixels"], "pixels;")
    print(output, sha(output))


if __name__ == "__main__":
    main()
