#!/usr/bin/env python3
"""Compare a private native Y-sprite hide with composed screen-980 road edges."""

import argparse
import json
from pathlib import Path

from phase1b_mild_steer_width import digest, scan
from phase1b_strip_rotation_prediction import affine, native_mask, predict
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import map_pixel, source_words


def screen_changes(before, after):
    return {(x, y) for y in range(224) for x in range(320)
            if before[y][3*x:3*x+3] != after[y][3*x:3*x+3]}


def main(root, previous_baseline, previous_hidden):
    baseline = root / "baseline"
    hidden = root / "hidden"
    name = "swap-screen-0980.png"
    assert png_rows(baseline / name) == png_rows(previous_baseline)
    assert png_rows(hidden / name) == png_rows(previous_hidden)
    for frame in range(960, 980):
        screen = f"swap-screen-{frame:04d}.png"
        assert digest(baseline / screen) == digest(hidden / screen)
    source = (baseline / "source-0979-ysprites.bin").read_bytes()
    after = (hidden / "source-0979-ysprites-after.bin").read_bytes()
    override = (root / "../phase1b-right-search-979-C000-00800-source.bin").resolve().read_bytes()
    assert source == (hidden / "source-0979-ysprites.bin").read_bytes()
    assert after == override
    changes = [i for i, (a, b) in enumerate(zip(source, after)) if a != b]
    assert len(changes) == 116
    assert all(0xC000 <= i < 0xC800 and i % 16 == 0 and
               after[i] == source[i] | 0x10 for i in changes)

    before_screen, after_screen = (png_rows(path / name)
                                   for path in (baseline, hidden))
    actual = screen_changes(before_screen, after_screen)
    native = {}
    candidates = []
    for frame in (979, 980):
        first, first_sha = source_words(baseline, frame)
        second, second_sha = source_words(hidden, frame)
        changed = native_mask((baseline / f"ybitmap-{frame:04d}.raw").read_bytes(),
                              (hidden / f"ybitmap-{frame:04d}.raw").read_bytes())
        native[frame] = (first, second, changed)
        for swap in (978, 980):
            for kind in ("pre", "post"):
                transform = affine(baseline, kind, swap)
                predicted = predict(changed, transform)
                candidates.append({"native_frame": frame, "swap_frame": swap,
                                   "swap_kind": kind, "transform": transform,
                                   "native_changed": len(changed),
                                   "predicted_changed": len(predicted),
                                   "observed_changed": len(actual),
                                   "true_positive": len(predicted & actual),
                                   "false_positive": len(predicted - actual),
                                   "false_negative": len(actual - predicted),
                                   "baseline_native_sha256": first_sha,
                                   "hidden_native_sha256": second_sha})
    selected = min(candidates, key=lambda row: (
        row["false_negative"], row["false_positive"], row["native_frame"],
        row["swap_frame"], row["swap_kind"]))
    equivalent = [{"native_frame": row["native_frame"],
                   "swap_frame": row["swap_frame"], "swap_kind": row["swap_kind"]}
                  for row in candidates
                  if (row["false_negative"], row["false_positive"],
                      row["transform"]) ==
                  (selected["false_negative"], selected["false_positive"],
                   selected["transform"])]
    frame = selected["native_frame"]
    first, second, changed = native[frame]
    transform = selected["transform"]
    edges = []
    for row in scan(before_screen, 980):
        y = row["y"]
        if not 153 <= y <= 163:
            continue
        item = {"y": y, "left": row["left"], "right": row["right"]}
        for side in ("left", "right"):
            x = row[side]
            sx, sy = map_pixel(transform, x, y)
            index = sy * 512 + sx
            item[side + "_native"] = {
                "coordinate": [sx, sy], "before_word": first[index],
                "after_word": second[index],
                "changed": index in changed,
                "screen_changed": (x, y) in actual}
        edges.append(item)

    result = {"baseline_screen_sha256": digest(baseline / name),
              "hidden_screen_sha256": digest(hidden / name),
              "source_before_sha256": digest(baseline / "source-0979-ysprites.bin"),
              "source_after_sha256": digest(hidden / "source-0979-ysprites-after.bin"),
              "changed_hide_bytes": len(changes), "candidate_mappings": candidates,
              "selected_mapping": {key: value for key, value in selected.items()
                                   if key not in ("transform",)},
              "equivalent_best_mappings": equivalent,
              "edges": edges,
              "logs_sha256": {kind: digest(root / kind / "phase1b-input.log")
                              for kind in ("baseline", "hidden")}}
    output = root / "result.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"private_result": str(output), "sha256": digest(output),
                      "selected_mapping": result["selected_mapping"],
                      "equivalent_best_mappings": equivalent,
                      "edge_summary": [{"y": row["y"],
                                        "left": [row["left_native"]["changed"],
                                                 row["left_native"]["screen_changed"]],
                                        "right": [row["right_native"]["changed"],
                                                  row["right_native"]["screen_changed"]]}
                                       for row in edges]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("previous_baseline_screen980", type=Path)
    parser.add_argument("previous_hidden_screen980", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.previous_baseline_screen980.resolve(),
         args.previous_hidden_screen980.resolve())
