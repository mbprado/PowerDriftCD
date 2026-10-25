#!/usr/bin/env python3
"""Verify screen-980 Y rotation and 16B composition at measured road edges."""

import argparse
import csv
import json
from pathlib import Path

from phase1b_mild_steer_width import digest
from phase1b_strip_rotation_prediction import affine
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import map_pixel, source_words


RIGHT = ((290, 157), (291, 158), (297, 159))
LEFT = ((90, 157), (84, 158), (82, 159))
NEIGHBORS = ((289, 157), (291, 157), (290, 158), (292, 158),
             (296, 159), (298, 159))
COORDINATES = set(RIGHT + LEFT + NEIGHBORS)


def read_probe(path):
    with path.open() as file:
        rows = [{key: int(value) for key, value in row.items()}
                for row in csv.DictReader(file)]
    assert len(rows) == len(COORDINATES)
    indexed = {(row["x"], row["y"]): row for row in rows}
    assert set(indexed) == COORDINATES
    return indexed


def interpret(row):
    sprite, priority = row["sprite"], row["priority"]
    passes = sprite != 0xffff and ((sprite >> 11) & 0x1e) < (priority & 0x1f)
    if passes:
        assert sprite & 0xf != 0xe, "shadow case requires palette-size context"
        expected = 0x800 | (sprite & 0x7ff)
        stage = "16b" if expected != row["rotated"] else "ambiguous_same_pen"
    else:
        expected = row["rotated"]
        stage = "rotation"
    assert row["final"] == expected, (row, expected)
    return {"sprite_passes": passes, "expected_final": expected,
            "stage": stage}


def main(root, old_baseline, old_hidden):
    baseline = root / "baseline"
    hidden = root / "hidden"
    assert png_rows(baseline / "swap-screen-0980.png") == png_rows(old_baseline)
    assert png_rows(hidden / "swap-screen-0980.png") == png_rows(old_hidden)
    for frame in range(960, 980):
        image = f"swap-screen-{frame:04d}.png"
        assert png_rows(baseline / image) == png_rows(hidden / image)
    source = (baseline / "source-0979-ysprites.bin").read_bytes()
    after = (hidden / "source-0979-ysprites-after.bin").read_bytes()
    override = (root / "../phase1b-right-search-979-C000-00800-source.bin").resolve().read_bytes()
    assert source == (hidden / "source-0979-ysprites.bin").read_bytes()
    assert after == override
    changed = [i for i, (a, b) in enumerate(zip(source, after)) if a != b]
    assert len(changed) == 116
    assert all(0xC000 <= i < 0xC800 and i % 16 == 0 and
               after[i] == source[i] | 0x10 for i in changed)

    probes = {kind: read_probe(root / kind / "layer-0979.csv")
              for kind in ("baseline", "hidden")}
    native = {kind: source_words(root / kind, 979)
              for kind in ("baseline", "hidden")}
    transform = affine(baseline, "post", 978)
    rows = []
    for x, y in sorted(COORDINATES, key=lambda pair: (pair[1], pair[0])):
        sx, sy = map_pixel(transform, x, y)
        record = {"x": x, "y": y, "native": [sx, sy]}
        for kind in ("baseline", "hidden"):
            row = probes[kind][x, y]
            native_word = native[kind][0][sy * 512 + sx]
            record[kind] = {**row, **interpret(row), "native_word": native_word}
            if native_word == 0xffff:
                assert row["priority"] == 0xff
        rows.append(record)

    index = {(row["x"], row["y"]): row for row in rows}
    for xy in RIGHT[:2]:
        row = index[xy]
        assert all(row[kind]["native_word"] == 0xffff and
                   row[kind]["stage"] == "16b" for kind in probes)
    last = index[RIGHT[2]]
    assert last["baseline"]["native_word"] != 0xffff
    assert last["hidden"]["native_word"] == 0xffff
    assert all(last[kind]["stage"] == "rotation" for kind in probes)
    assert all(index[xy][kind]["stage"] == "rotation"
               for xy in LEFT for kind in probes)

    result = {"mame_frame": 979, "composed_screen": 980,
              "changed_source_hide_bytes": len(changed),
              "probe_sha256": {kind: digest(root / kind / "layer-0979.csv")
                               for kind in probes},
              "native_sha256": {kind: native[kind][1] for kind in probes},
              "screen_sha256": {kind: digest(root / kind / "swap-screen-0980.png")
                                for kind in probes},
              "logs_sha256": {kind: digest(root / kind / "phase1b-input.log")
                              for kind in probes},
              "rows": rows}
    output = root / "result.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"private_result": str(output), "sha256": digest(output),
                      "right_edges": [{"screen": list(xy),
                                       "baseline": index[xy]["baseline"]["stage"],
                                       "hidden": index[xy]["hidden"]["stage"]}
                                      for xy in RIGHT]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("previous_baseline_screen980", type=Path)
    parser.add_argument("previous_hidden_screen980", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.previous_baseline_screen980.resolve(),
         args.previous_hidden_screen980.resolve())
