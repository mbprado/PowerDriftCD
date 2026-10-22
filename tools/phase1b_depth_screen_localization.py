#!/usr/bin/env python3
"""Localize private arcade depth descriptors through one-byte hide replays."""

import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path

from phase1b_projection_replay import hexfield, signed16
from phase1b_swap_compare import png_rows


SIDES = ("center", "left", "right")
DESCRIPTOR_FRAMES = (966, 970, 974)
DEPTH_INDEXES = (1, 2, 3, 4)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def mask(baseline, hidden):
    before, after = png_rows(baseline), png_rows(hidden)
    return {(x, y) for y in range(224) for x in range(320)
            if before[y][3*x:3*x+3] != after[y][3*x:3*x+3]}


def best_translation(center, other):
    """F1-optimal translation of the causal RGB-change mask, not a camera pose."""
    if not center or not other:
        return None
    guess_x = median(x for x, _ in other) - median(x for x, _ in center)
    guess_y = median(y for _, y in other) - median(y for _, y in center)
    best = None
    for dy in range(guess_y - 8, guess_y + 9):
        for dx in range(guess_x - 20, guess_x + 21):
            common = sum((x + dx, y + dy) in other for x, y in center)
            if best is None or common > best[0]:
                best = (common, dx, dy)
    common, dx, dy = best
    return {"dx": dx, "dy": dy, "f1": 2 * common / (len(center) + len(other)),
            "intersection_pixels": common,
            "search_edge": abs(dx - guess_x) == 20 or abs(dy - guess_y) == 8}


def plans(root):
    near = json.loads((root / "phase1b-near-depth-inputs/plan.json").read_text())
    far = json.loads((root / "phase1b-matched-far-inputs/plan.json").read_text())
    indexed = {(item["side"], item["descriptor_frame"],
                item.get("depth_index", 4)): item for item in near + far}
    assert len(indexed) == 36
    return indexed


def geometry(root):
    output = {}
    for side in SIDES:
        with (root / f"phase1b-depth-sequence-{side}" /
              "geometry-samples.csv").open() as file:
            output[side] = {(int(row["frame"]), int(row["index"])): row
                            for row in csv.DictReader(file)}
        assert len(output[side]) == 41 * 12
    return output


def summarize(root):
    plan, rows = plans(root), geometry(root)
    records, masks = [], {}
    for side in SIDES:
        baseline = root / f"phase1b-depth-sequence-{side}"
        for frame in DESCRIPTOR_FRAMES:
            screen = baseline / f"swap-screen-{frame+1:04d}.png"
            for index in DEPTH_INDEXES:
                item = plan[side, frame, index]
                trial = root / (f"phase1b-near-hidden-{side}-{frame}-depth{index}"
                                if index != 4 else
                                f"phase1b-matched-far-hidden-{side}-{frame}")
                source = baseline / f"source-{frame:04d}-ysprites.bin"
                original = source.read_bytes()
                changed = (trial / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
                slot = int(item["slot"], 16)
                assert len(original) == len(changed) == 0x10000
                assert [at for at, (a, b) in enumerate(zip(original, changed))
                        if a != b] == [slot]
                assert changed[slot] == original[slot] | 0x10
                assert (baseline / f"swap-screen-{frame:04d}.png").read_bytes() == (
                    trial / f"swap-screen-{frame:04d}.png").read_bytes()
                descriptor = struct.unpack_from(">8H", original, slot)
                assert f"{descriptor[3]:04X}" == item["graphic"]
                points = mask(screen, trial / f"swap-screen-{frame+1:04d}.png")
                masks[side, frame, index] = points
                row = rows[side][frame - 2, index]
                position = (hexfield(row, "projected4") << 16 |
                            hexfield(row, "projected6"))
                shared = (baseline / f"shared-list-{frame:04d}.bin").read_bytes()
                assert len(shared) == 0x2000
                matches = [offset for offset in range(0, len(shared), 16)
                           if struct.unpack_from(">I", shared, offset + 4)[0]
                           == position and
                           ((struct.unpack_from(">I", shared, offset)[0] >> 16)
                            & 0xff00) == 0x8b00]
                assert len(matches) == 1, (side, frame, index, matches)
                record = {
                    "side": side, "projection_frame": frame - 2,
                    "descriptor_frame": frame, "screen_frame": frame + 1,
                    "depth_index": index, "depth": row["depth"],
                    "projected_x": signed16(hexfield(row, "projected4")),
                    "graphic": item["graphic"],
                    "native_origin_x": (descriptor[1] & 0xfff) - 0x600,
                    "native_origin_y": (descriptor[2] & 0xfff) - 0x600,
                    "direction_word": f"{descriptor[5]:04X}",
                    "changed_pixels": len(points),
                    "screen_sha256": sha256(screen),
                    "hidden_screen_sha256": sha256(
                        trial / f"swap-screen-{frame+1:04d}.png"),
                }
                if points:
                    record["visible_x"] = [min(x for x, _ in points),
                                           median(x for x, _ in points),
                                           max(x for x, _ in points)]
                    record["visible_y"] = [min(y for _, y in points),
                                           median(y for _, y in points),
                                           max(y for _, y in points)]
                records.append(record)
    comparisons = []
    by_key = {(r["side"], r["descriptor_frame"], r["depth_index"]): r
              for r in records}
    for frame in DESCRIPTOR_FRAMES:
        for index in DEPTH_INDEXES:
            center = by_key["center", frame, index]
            for side in SIDES[1:]:
                other = by_key[side, frame, index]
                same_graphic = (center["graphic"] == other["graphic"]
                                and (int(center["direction_word"], 16) & 0x3000)
                                == (int(other["direction_word"], 16) & 0x3000))
                comparison = {
                    "side": side, "descriptor_frame": frame,
                    "depth_index": index,
                    "same_graphic_and_direction": same_graphic,
                    "projected_x_delta": other["projected_x"] - center["projected_x"],
                    "median_screen_x_delta": (
                        other["visible_x"][1] - center["visible_x"][1]
                        if "visible_x" in center and "visible_x" in other else None),
                    "best_mask_translation": best_translation(
                        masks["center", frame, index], masks[side, frame, index]),
                }
                comparisons.append(comparison)
    output = root / "phase1b-depth-screen-localization.json"
    output.write_text(json.dumps({"records": records,
                                  "comparisons": comparisons}, indent=2) + "\n")
    for frame in DESCRIPTOR_FRAMES:
        print(f"screen {frame+1}:")
        for index in DEPTH_INDEXES:
            center = by_key["center", frame, index]
            left = next(r for r in comparisons if r["side"] == "left"
                        and r["descriptor_frame"] == frame
                        and r["depth_index"] == index)
            print(f"  depth {center['depth']}: y {center.get('visible_y')}, "
                  f"left projected dx {left['projected_x_delta']}, "
                  f"visible median dx {left['median_screen_x_delta']}, "
                  f"mask shift {left['best_mask_translation']}")
    print(f"{len(records)} one-byte interventions localized; private {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    summarize(parser.parse_args().private_root)
