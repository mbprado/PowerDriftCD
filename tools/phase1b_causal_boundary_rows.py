#!/usr/bin/env python3
"""Check which private arcade depth-strip hides move a visible sand edge."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median

from make_perspective_road import live_camera_lines
from phase1b_depth_screen_localization import plans
from phase1b_road_edge_sample import boundary
from phase1b_swap_compare import png_rows


SIDES = ("center", "left")
FRAMES = (966, 970, 974)
DEPTHS = (0, 1, 2, 3, 4)
ROWS = range(135, 191)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_path(root, side, frame, depth):
    if depth == 4:
        return root / f"phase1b-matched-far-hidden-{side}-{frame}"
    return root / f"phase1b-near-hidden-{side}-{frame}-depth{depth}"


def edge(row, y):
    try:
        return boundary(row, y)[0]
    except ValueError:
        return None


def synthetic_width_reference():
    rows = (0, 16, 32, 48, 63)
    widths = {row: [] for row in rows}
    for frame in range(60):
        traces = list(live_camera_lines(frame, width=128))
        for row in rows:
            x_start, _, step, _ = traces[row]
            road = [x for x in range(128)
                    if 128 <= (x_start + x * (step // 256)) // 8 < 144]
            assert road and road == list(range(road[0], road[-1] + 1))
            widths[row].append(len(road))
    return {str(row): {"min": min(samples), "median": median(samples),
                       "max": max(samples)}
            for row, samples in widths.items()}


def run(root):
    plan = plans(root)
    nearest = json.loads((root / "phase1b-nearest-depth-inputs/plan.json").read_text())
    assert len(nearest) == len(SIDES) * len(FRAMES)
    for item in nearest:
        key = (item["side"], item["descriptor_frame"], 0)
        assert key not in plan
        plan[key] = item
    records = []
    for side in SIDES:
        baseline = root / f"phase1b-depth-sequence-{side}"
        for frame in FRAMES:
            screen = baseline / f"swap-screen-{frame+1:04d}.png"
            before = png_rows(screen)
            baseline_edges = {y: edge(before[y], y) for y in ROWS}
            for depth in DEPTHS:
                item = plan[side, frame, depth]
                trial = trial_path(root, side, frame, depth)
                hidden_screen = trial / f"swap-screen-{frame+1:04d}.png"
                after = png_rows(hidden_screen)
                source = baseline / f"source-{frame:04d}-ysprites.bin"
                original = source.read_bytes()
                modified = (trial / f"source-{frame:04d}-ysprites-after.bin").read_bytes()
                slot = int(item["slot"], 16)
                assert digest(source) == item["source_sha256"]
                assert len(original) == len(modified) == 0x10000
                assert [index for index, (a, b) in enumerate(zip(original, modified))
                        if a != b] == [slot]
                assert modified[slot] == original[slot] | 0x10
                assert (baseline / f"swap-screen-{frame:04d}.png").read_bytes() == (
                    trial / f"swap-screen-{frame:04d}.png").read_bytes()
                row_counts = Counter()
                for y in range(224):
                    a, b = before[y], after[y]
                    row_counts[y] = sum(a[3*x:3*x+3] != b[3*x:3*x+3]
                                        for x in range(320))
                visible = [y for y, count in row_counts.items() if count]
                boundary_rows = []
                for y in ROWS:
                    a = baseline_edges[y]
                    b = edge(after[y], y)
                    if a is not None and b is not None and a != b:
                        boundary_rows.append({"y": y, "baseline_x": a,
                                              "hidden_x": b, "delta_x": b - a,
                                              "changed_pixels_on_row": row_counts[y]})
                records.append({
                    "side": side, "descriptor_frame": frame,
                    "screen_frame": frame + 1, "depth_index": depth,
                    "depth": f"{0x3200 + 0x200*depth:04X}",
                    "graphic": item["graphic"],
                    "source_sha256": digest(source),
                    "baseline_screen_sha256": digest(screen),
                    "hidden_screen_sha256": digest(hidden_screen),
                    "changed_pixels": sum(row_counts.values()),
                    "changed_row_span": [visible[0], visible[-1]] if visible else None,
                    "changed_row_counts": {str(y): row_counts[y] for y in visible},
                    "baseline_valid_boundary_rows": [y for y in ROWS
                                                     if baseline_edges[y] is not None],
                    "hidden_valid_boundary_rows": [y for y in ROWS
                                                   if edge(after[y], y) is not None],
                    "boundary_changes": boundary_rows})
                print(side, frame, depth, "visible Y",
                      (visible[0], visible[-1]) if visible else None,
                      "changed edge rows", len(boundary_rows),
                      "edge span", (boundary_rows[0]["y"], boundary_rows[-1]["y"])
                      if boundary_rows else None)
    assert len(records) == len(SIDES) * len(FRAMES) * len(DEPTHS)
    control_baseline = root / "phase1b-depth-sequence-center"
    control_hidden = trial_path(root, "center", 974, 0)
    sham = root / "phase1b-near-hidden-center-974-depth0-sham"
    repeat = root / "phase1b-near-hidden-center-974-depth0-repeat"
    assert (control_baseline / "source-0974-ysprites.bin").read_bytes() == (
        sham / "source-0974-ysprites-after.bin").read_bytes()
    assert (control_baseline / "swap-screen-0975.png").read_bytes() == (
        sham / "swap-screen-0975.png").read_bytes()
    for name in ("source-0974-ysprites-after.bin", "swap-screen-0975.png"):
        assert (control_hidden / name).read_bytes() == (repeat / name).read_bytes()
    result = {"tested_rows": [ROWS.start, ROWS.stop - 1],
              "records": records,
              "sega_host_road_width_reference": synthetic_width_reference(),
              "controls": {
                  "same_value_screen_sha256": digest(sham / "swap-screen-0975.png"),
                  "repeat_hidden_screen_sha256": digest(repeat / "swap-screen-0975.png"),
                  "same_value_unchanged": True,
                  "repeat_byte_identical": True}}
    path = root / "phase1b-causal-boundary-rows.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print("private result:", path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    run(parser.parse_args().private_root.resolve())
