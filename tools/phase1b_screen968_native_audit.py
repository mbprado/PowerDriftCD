#!/usr/bin/env python3
"""Audit private pulse-204 screen-968 native bitmap/source timing tests."""

import hashlib
import json
from pathlib import Path

from phase1b_mild_steer_width import scan
from phase1b_road_only_contour import edge_stage, load_layer
from phase1b_strip_rotation_prediction import affine
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import map_pixel, source_words
from phase1b_ysprite_page_audit import traverse


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(root, baseline, trial_name, override_name, allowed):
    trial = root / trial_name
    original = (baseline / "source-0967-ysprites.bin").read_bytes()
    override = (root / override_name).read_bytes()
    assert (trial / "source-0967-ysprites.bin").read_bytes() == original
    assert (trial / "source-0967-ysprites-after.bin").read_bytes() == override
    changed = [i for i, (a, b) in enumerate(zip(original, override)) if a != b]
    assert changed and changed == allowed
    assert all(i % 16 == 0 and override[i] == original[i] | 0x10
               for i in changed)
    for frame in range(960, 968):
        name = f"swap-screen-{frame:04d}.png"
        assert png_rows(baseline / name) == png_rows(trial / name)
    return trial, {"trial": trial_name, "changed_descriptor_count": len(changed),
                   "prior_screens_equal": True,
                   "override_sha256": digest(root / override_name),
                   "screen_sha256": digest(trial / "swap-screen-0968.png"),
                   "native967_sha256": digest(trial / "ybitmap-0967.raw"),
                   "log_sha256": digest(trial / "phase1b-input.log")}


def main():
    root = Path(__file__).resolve().parents[1] / "build/private"
    old = root / "phase1b-pulse204-screen981-baseline"
    old_broad = root / "phase1b-pulse204-screen968-broad"
    baseline = root / "phase1b-pulse204-screen968-native-baseline"
    for frame in range(960, 983):
        name = f"swap-screen-{frame:04d}.png"
        assert png_rows(old / name) == png_rows(baseline / name)
    source = (baseline / "source-0967-ysprites.bin").read_bytes()
    chain, stop, _ = traverse(source)
    assert stop == "end_marker" and len(chain) - 1 == 111
    assert all(slot >> 12 == 0xe for slot in chain if slot)
    broad_slots = [i for i in range(0, 0x10000, 16) if not source[i] & 0x10]
    page_slots = [i for i in range(0xe000, 0xf000, 16) if not source[i] & 0x10]
    broad, broad_record = one(root, baseline,
        "phase1b-pulse204-screen968-native-broad",
        "phase1b-pulse204-screen968-broad-source.bin", broad_slots)
    page, page_record = one(root, baseline,
        "phase1b-pulse204-screen968-native-pageE",
        "phase1b-pulse204-screen968-pageE-source.bin", page_slots)
    for frame in range(960, 983):
        name = f"swap-screen-{frame:04d}.png"
        assert png_rows(old_broad / name) == png_rows(broad / name)

    original_screen = png_rows(baseline / "swap-screen-0968.png")
    edge_rows = [r for r in scan(original_screen, 968) if 159 <= r["y"] <= 163]
    assert [r["y"] for r in edge_rows] == list(range(159, 164))
    layer = load_layer(baseline / "layer-rows-0967.csv")
    transform = affine(baseline, "pre", 966)
    native, _ = source_words(baseline, 967)
    cases = []
    for trial, record in ((broad, broad_record), (page, page_record)):
        screen = png_rows(trial / "swap-screen-0968.png")
        words, _ = source_words(trial, 967)
        rows = []
        for row in edge_rows:
            sides = []
            for side in ("left", "right"):
                x, y = row[side], row["y"]
                sx, sy = map_pixel(transform, x, y)
                old_word, new_word = native[sy * 512 + sx], words[sy * 512 + sx]
                assert edge_stage(layer[y][x]) == "clear_rotation"
                assert old_word != 0xffff
                sides.append({"side": side, "screen_x": x,
                              "native": [sx, sy], "native_before": old_word,
                              "native_after": new_word,
                              "screen_changed": original_screen[y][3*x:3*x+3] !=
                                  screen[y][3*x:3*x+3],
                              "became_transparent": new_word == 0xffff})
            rows.append({"y": row["y"], "sides": sides})
        record["rows"] = rows
        record["screen_edges_changed"] = sum(s["screen_changed"] for r in rows
                                             for s in r["sides"])
        record["native_edges_transparent"] = sum(s["became_transparent"]
                                                 for r in rows for s in r["sides"])
        cases.append(record)
    assert (cases[0]["screen_edges_changed"], cases[0]["native_edges_transparent"]) == (10, 10)
    assert (cases[1]["screen_edges_changed"], cases[1]["native_edges_transparent"]) == (0, 0)
    mapping_controls = {}
    for native_frame in (967, 968):
        before_words, _ = source_words(baseline, native_frame)
        after_words, _ = source_words(broad, native_frame)
        for transform_frame in (966, 968):
            params = affine(baseline, "pre", transform_frame)
            count = 0
            for row in edge_rows:
                for side in ("left", "right"):
                    sx, sy = map_pixel(params, row[side], row["y"])
                    index = sy * 512 + sx
                    count += before_words[index] != 0xffff and after_words[index] == 0xffff
            mapping_controls[f"native{native_frame}_pre{transform_frame}"] = count
    assert mapping_controls == {"native967_pre966": 10,
                                "native967_pre968": 3,
                                "native968_pre966": 0,
                                "native968_pre968": 0}
    result = {"schema": 1, "pulse": 204, "callback": 967,
              "composed_screen": 968, "native_bitmap_frame": 967,
              "transform": "pre-0966", "reachable_page": "E",
              "reachable_descriptors": 111,
              "old_binary_screens_equal": True,
              "baseline_screen_sha256": digest(baseline / "swap-screen-0968.png"),
              "baseline_native967_sha256": digest(baseline / "ybitmap-0967.raw"),
              "baseline_source_sha256": digest(baseline / "source-0967-ysprites.bin"),
              "cases": cases, "mapping_controls": mapping_controls,
              "exact_descriptor_status": "INCONCLUSIVE",
              "reason": "reachable callback page E does not affect the ten mapped edge pixels"}
    output = root / "phase1b-screen968-native-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    for case in cases:
        print(case["trial"], case["changed_descriptor_count"],
              case["screen_edges_changed"], case["native_edges_transparent"])
    print("exact source", result["exact_descriptor_status"], output)


if __name__ == "__main__":
    main()
