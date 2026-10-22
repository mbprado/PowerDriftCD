#!/usr/bin/env python3
"""Test a constant graphic-offset word for one private arcade road strip."""

import argparse
import json
import os
import struct
import sys
from pathlib import Path

from phase1b_depth_sequence import bounds, image_difference
from phase1b_near_depth_visibility import digest, run_trial, select


PROJECTIONS = (968, 972)
TARGET_GRAPHIC = 0x3888
ROWS = {967: 143, 971: 150, 975: 160}


def plan_path(root):
    return root / "phase1b-fixed-graphic-inputs" / "plan.json"


def prepare(root):
    output = plan_path(root).parent
    output.mkdir(parents=True, exist_ok=True)
    plan = []
    for projection in PROJECTIONS:
        frame, slot, source, graphic = select(root, "right", projection, 1)
        center_frame, _, center_source, center_graphic = select(
            root, "center", projection, 1)
        assert center_frame == frame and center_graphic == TARGET_GRAPHIC
        assert graphic == 0x3898
        original = source.read_bytes()
        native_direction = struct.unpack_from(">H", original, slot + 10)[0]
        _, center_slot, _, _ = select(root, "center", projection, 1)
        target_direction = struct.unpack_from(
            ">H", center_source.read_bytes(), center_slot + 10)[0]
        assert native_direction ^ target_direction == 0x3000
        for variant in ("fixed", "fixed-hidden", "paired", "paired-hidden"):
            raw = bytearray(original)
            struct.pack_into(">H", raw, slot + 6, TARGET_GRAPHIC)
            if variant.startswith("paired"):
                struct.pack_into(">H", raw, slot + 10, target_direction)
            if variant.endswith("hidden"):
                raw[slot] |= 0x10
            path = output / f"right-{frame:04d}-{variant}.bin"
            path.write_bytes(raw)
            plan.append({"side": "right", "descriptor_frame": frame,
                         "depth_index": 1, "slot": f"{slot:04X}",
                         "variant": variant,
                         "target_direction": f"{target_direction:04X}",
                         "source_sha256": digest(source),
                         "override_sha256": digest(path)})
            print(f"right {frame} {variant}: slot +{slot:04X}, "
                  f"graphic {graphic:04X} → {TARGET_GRAPHIC:04X}, "
                  f"direction {native_direction:04X} → {target_direction:04X}")
    plan_path(root).write_text(json.dumps(plan, indent=2) + "\n")


def run(root, mame, rompath, state):
    plan = json.loads(plan_path(root).read_text())
    for item in plan:
        frame, variant = item["descriptor_frame"], item["variant"]
        source = plan_path(root).parent / f"right-{frame:04d}-{variant}.bin"
        assert digest(source) == item["override_sha256"]
        run_trial(root, item, mame, rompath, state, source, f"-{variant}")
    item = next(row for row in plan if row["descriptor_frame"] == 970)
    source = root / "phase1b-depth-sequence-right" / "source-0970-ysprites.bin"
    assert digest(source) == item["source_sha256"]
    run_trial(root, item, mame, rompath, state, source, "-graphic-sham")
    item = next(row for row in plan if row["descriptor_frame"] == 974
                and row["variant"] == "fixed")
    source = plan_path(root).parent / "right-0974-fixed.bin"
    run_trial(root, item, mame, rompath, state, source, "-fixed-repeat")


def native_970(root, mame, rompath, state):
    previous = json.loads((root / "phase1b-near-depth-inputs" /
                           "plan.json").read_text())
    current = json.loads(plan_path(root).read_text())
    os.environ["PDRIFT_YBITMAP_DIR"] = "."
    for side in ("center", "left", "right"):
        item, = [row for row in previous if row["side"] == side
                 and row["descriptor_frame"] == 970
                 and row["depth_index"] == 1]
        source = (root / f"phase1b-depth-sequence-{side}" /
                  "source-0970-ysprites.bin")
        run_trial(root, item, mame, rompath, state, source,
                  "-native-baseline")
        hidden = (root / "phase1b-near-depth-inputs" /
                  f"{side}-0970-depth1.bin")
        run_trial(root, item, mame, rompath, state, hidden)
    for item in current:
        if item["descriptor_frame"] != 970:
            continue
        variant = item["variant"]
        source = plan_path(root).parent / f"right-0970-{variant}.bin"
        run_trial(root, item, mame, rompath, state, source, f"-{variant}")


def native_pixels(a, b):
    assert len(a) == len(b) == 512 * 512 * 2
    points = [(index % 512, index // 512)
              for index in range(512 * 512)
              if a[2*index:2*index+2] != b[2*index:2*index+2]]
    return {"pixels": len(points), "bbox": bounds(points) if points else None,
            "row194": row_stats(points, 194)}


def analyze_native(root):
    output = plan_path(root).parent
    results = {}
    for side in ("center", "left", "right"):
        base = root / f"phase1b-near-hidden-{side}-970-depth1-native-baseline"
        hidden = root / f"phase1b-near-hidden-{side}-970-depth1"
        original = root / f"phase1b-depth-sequence-{side}"
        assert (base / "source-0970-ysprites-after.bin").read_bytes() == (
            original / "source-0970-ysprites.bin").read_bytes()
        assert (base / "swap-screen-0971.png").read_bytes() == (
            original / "swap-screen-0971.png").read_bytes()
        a = (base / "ybitmap-0970.raw").read_bytes()
        b = (hidden / "ybitmap-0970.raw").read_bytes()
        results[f"{side}_hide"] = native_pixels(a, b)
        print(f"native {side} hide: {results[f'{side}_hide']}")
        if side == "right":
            for variant in ("fixed", "paired"):
                visible = root / f"phase1b-near-hidden-right-970-depth1-{variant}"
                concealed = root / (f"phase1b-near-hidden-right-970-"
                                    f"depth1-{variant}-hidden")
                v = (visible / "ybitmap-0970.raw").read_bytes()
                h = (concealed / "ybitmap-0970.raw").read_bytes()
                results[f"right_{variant}_vs_natural"] = native_pixels(a, v)
                results[f"right_{variant}_hide"] = native_pixels(v, h)
                print(f"native right {variant} vs natural: "
                      f"{results[f'right_{variant}_vs_natural']}; hide: "
                      f"{results[f'right_{variant}_hide']}")
    (output / "native-results.json").write_text(
        json.dumps(results, indent=2) + "\n")


def row_stats(points, y):
    xs = sorted(x for x, py in points if py == y)
    if not xs:
        return None
    groups = 1 + sum(b != a + 1 for a, b in zip(xs, xs[1:]))
    return {"min_x": xs[0], "max_x": xs[-1], "count": len(xs),
            "groups": groups, "mean_x": round(sum(xs) / len(xs), 3)}


def analyze(root):
    plan = json.loads(plan_path(root).read_text())
    output = plan_path(root).parent
    results = []
    for item in plan:
        side, frame, variant, slot = (item["side"], item["descriptor_frame"],
                                      item["variant"], int(item["slot"], 16))
        baseline = root / f"phase1b-depth-sequence-{side}"
        trial = root / f"phase1b-near-hidden-{side}-{frame}-depth1-{variant}"
        source = baseline / f"source-{frame:04d}-ysprites.bin"
        assert digest(source) == item["source_sha256"]
        input_path = output / f"right-{frame:04d}-{variant}.bin"
        assert digest(input_path) == item["override_sha256"]
        original = source.read_bytes()
        after = (trial / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
        assert len(original) == len(after) == 0x10000
        changes = [i for i, (a, b) in enumerate(zip(original, after)) if a != b]
        expected = [slot + 7]
        if variant.endswith("hidden"):
            expected.insert(0, slot)
        if variant.startswith("paired"):
            expected.append(slot + 10)
        assert changes == expected, (frame, variant, changes)
        assert struct.unpack_from(">H", after, slot + 6)[0] == TARGET_GRAPHIC
        if variant.startswith("paired"):
            assert struct.unpack_from(">H", after, slot + 10)[0] == int(
                item["target_direction"], 16)
        for prior in range(960, frame + 1):
            assert (baseline / f"swap-screen-{prior:04d}.png").read_bytes() == (
                trial / f"swap-screen-{prior:04d}.png").read_bytes()
        next_screen = frame + 1
        points = image_difference(
            baseline / f"swap-screen-{next_screen:04d}.png",
            trial / f"swap-screen-{next_screen:04d}.png")
        results.append({"side": side, "descriptor_frame": frame,
                        "variant": variant, "changed_pixels": len(points),
                        "bbox": bounds(points) if points else None,
                        "screen_sha256": digest(
                            trial / f"swap-screen-{next_screen:04d}.png")})
        print(f"right {frame} {variant} vs natural: {len(points)} pixels, "
              f"bbox={bounds(points) if points else None}")

    baseline = root / "phase1b-depth-sequence-right"
    sham = root / "phase1b-near-hidden-right-970-depth1-graphic-sham"
    assert (baseline / "source-0970-ysprites.bin").read_bytes() == (
        sham / "source-0970-ysprites-after.bin").read_bytes()
    assert (baseline / "swap-screen-0971.png").read_bytes() == (
        sham / "swap-screen-0971.png").read_bytes()
    fixed = root / "phase1b-near-hidden-right-974-depth1-fixed"
    repeat = root / "phase1b-near-hidden-right-974-depth1-fixed-repeat"
    for name in ("source-0974-ysprites-after.bin", "swap-screen-0975.png"):
        assert (fixed / name).read_bytes() == (repeat / name).read_bytes()
    print("same-value graphic sham unchanged; fixed-source repeat byte-identical")

    for frame in (966, 970, 974):
        screen = frame + 1
        masks = {}
        for side in ("center", "left", "right"):
            baseline = root / f"phase1b-depth-sequence-{side}"
            hidden = root / f"phase1b-near-hidden-{side}-{frame}-depth1"
            masks[side] = image_difference(
                baseline / f"swap-screen-{screen:04d}.png",
                hidden / f"swap-screen-{screen:04d}.png")
        if frame != 966:
            for variant in ("fixed", "paired"):
                visible = root / f"phase1b-near-hidden-right-{frame}-depth1-{variant}"
                hidden = root / f"phase1b-near-hidden-right-{frame}-depth1-{variant}-hidden"
                masks[f"right_{variant}"] = image_difference(
                    visible / f"swap-screen-{screen:04d}.png",
                    hidden / f"swap-screen-{screen:04d}.png")
        sample = {side: {"pixels": len(points),
                         "bbox": bounds(points) if points else None,
                         "row": row_stats(points, ROWS[screen])}
                  for side, points in masks.items()}
        print(f"screen {screen}, row {ROWS[screen]}: {sample}")
        results.append({"screen": screen, "sample_row": ROWS[screen],
                        "masks": sample})
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("action", choices=("prepare", "run", "native970",
                                           "analyze", "analyze-native"))
    parser.add_argument("--mame", type=Path)
    parser.add_argument("--rompath", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if args.action == "prepare":
        prepare(root)
    elif args.action in ("run", "native970"):
        assert args.mame and args.rompath and args.state
        if args.action == "run":
            run(root, args.mame, args.rompath, args.state)
        else:
            native_970(root, args.mame, args.rompath, args.state)
    elif args.action == "analyze-native":
        analyze_native(root)
    else:
        analyze(root)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, IndexError) as exc:
        sys.exit(str(exc))
