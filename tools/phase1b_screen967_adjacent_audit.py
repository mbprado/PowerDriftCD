#!/usr/bin/env python3
"""Audit private pulse-204 screen-967 E630 and adjacent screen-968 C630 sources."""

import hashlib
import json
from pathlib import Path
import struct

from phase1b_mild_steer_width import scan
from phase1b_road_only_contour import edge_stage, load_layer
from phase1b_strip_rotation_prediction import affine
from phase1b_swap_compare import png_rows
from phase1b_ybitmap_map import map_pixel, source_words


ROOT = Path(__file__).resolve().parents[1] / "build/private"
BASELINE = ROOT / "phase1b-pulse204-screen967-native-baseline"
TRIALS = tuple(ROOT / ("phase1b-pulse204-screen967-native-E630" + suffix)
               for suffix in ("", "-r1", "-r2"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(image, x, y):
    return image[y][3*x:3*x+3]


def audit():
    old = ROOT / "phase1b-pulse204-screen968-native-baseline"
    for frame in range(960, 983):
        name = f"swap-screen-{frame:04d}.png"
        assert png_rows(old / name) == png_rows(BASELINE / name)
    source = (BASELINE / "source-0966-ysprites.bin").read_bytes()
    next_source = (BASELINE / "source-0967-ysprites.bin").read_bytes()
    e_words = struct.unpack_from(">8H", source, 0xe630)
    c_words = struct.unpack_from(">8H", next_source, 0xc630)
    assert [e_words[i] == c_words[i] for i in (0, 3, 4, 5, 6)] == [True] * 5
    assert (c_words[1] - e_words[1], c_words[2] - e_words[2]) == (-2, 1)
    assert e_words[3] == c_words[3]
    before_screen = png_rows(BASELINE / "swap-screen-0967.png")
    rows = [row for row in scan(before_screen, 967) if 159 <= row["y"] <= 161]
    assert [(row["y"], row["left"], row["right"]) for row in rows] == [
        (159, 66, 300), (160, 64, 301), (161, 62, 301)]
    layer = load_layer(BASELINE / "layer-rows-0966.csv")
    transform = affine(BASELINE, "pre", 966)
    before_native, _ = source_words(BASELINE, 966)
    replays = []
    for index, trial in enumerate(TRIALS):
        suffix = f"-r{index}" if index else ""
        override = ROOT / f"phase1b-pulse204-screen967-E630{suffix}-source.bin"
        hidden_source = override.read_bytes()
        assert (trial / "source-0966-ysprites.bin").read_bytes() == source
        assert (trial / "source-0966-ysprites-after.bin").read_bytes() == hidden_source
        assert [i for i, (a, b) in enumerate(zip(source, hidden_source))
                if a != b] == [0xe630]
        assert hidden_source[0xe630] == source[0xe630] | 0x10
        for frame in range(960, 967):
            name = f"swap-screen-{frame:04d}.png"
            assert png_rows(trial / name) == png_rows(BASELINE / name)
        log = (trial / "phase1b-input.log").read_text(errors="replace")
        assert "STEER_PULSE=204" in log and "INPUT,960,steer-204" in log
        assert "STATE_LOAD,950," in log
        assert "SOURCE_OVERRIDE,966,ysprites,E630,0010," in log
        after_screen = png_rows(trial / "swap-screen-0967.png")
        after_native, _ = source_words(trial, 966)
        samples = []
        for row in rows:
            for side in ("left", "right"):
                x, y = row[side], row["y"]
                assert edge_stage(layer[y][x]) == "clear_rotation"
                sx, sy = map_pixel(transform, x, y)
                old_word = before_native[sy * 512 + sx]
                new_word = after_native[sy * 512 + sx]
                assert old_word != 0xffff and new_word == 0xffff
                assert rgb(before_screen, x, y) != rgb(after_screen, x, y)
                samples.append({"y": y, "side": side, "screen_x": x,
                                "native": [sx, sy], "native_before": old_word,
                                "native_after": new_word})
        assert len(samples) == 6
        replays.append({"trial": trial.name, "sample_count": len(samples),
                        "prior_screens_equal": True,
                        "override_sha256": digest(override),
                        "screen967_sha256": digest(trial / "swap-screen-0967.png"),
                        "native966_sha256": digest(trial / "ybitmap-0966.raw"),
                        "log_sha256": digest(trial / "phase1b-input.log"),
                        "samples": samples})
    for field in ("override_sha256", "screen967_sha256", "native966_sha256"):
        assert len({item[field] for item in replays}) == 1
    assert len({item["log_sha256"] for item in replays}) == 3
    return {"schema": 1, "pulse": 204,
            "screen967_source_offset": "E630",
            "screen968_source_offset": "C630",
            "equal_descriptor_fields": [0, 3, 4, 5, 6],
            "raw_position_word_delta": [-2, 1],
            "baseline_screen967_sha256": digest(BASELINE / "swap-screen-0967.png"),
            "baseline_native966_sha256": digest(BASELINE / "ybitmap-0966.raw"),
            "baseline_source966_sha256": digest(BASELINE / "source-0966-ysprites.bin"),
            "replays": replays, "adjacent_source_status": "PASS",
            "camera_adapter_status": "INCONCLUSIVE"}


if __name__ == "__main__":
    result = audit()
    output = ROOT / "phase1b-screen967-adjacent-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("adjacent source", result["adjacent_source_status"],
          "fresh runs", len(result["replays"]), output)
