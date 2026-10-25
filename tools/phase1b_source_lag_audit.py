#!/usr/bin/env python3
"""Audit two private Y-sprite hides across subsequent composed screens."""

import argparse
import json
from pathlib import Path

from phase1b_mild_steer_width import digest, scan
from phase1b_swap_compare import png_rows


CALLBACKS = (979, 980)
END_SCREEN = 982
GROUP = "C000-00800"


def same_pixel(before, after, y, x):
    at = 3 * x
    return before[y][at:at + 3] == after[y][at:at + 3]


def trial_record(root, baseline, callback, prior_screen980):
    trial = root / f"phase1b-right-search-{callback}-{GROUP}"
    source_name = f"source-{callback:04d}-ysprites.bin"
    before_source = (baseline / source_name).read_bytes()
    observed_source = (trial / source_name).read_bytes()
    after_source = (trial / f"source-{callback:04d}-ysprites-after.bin").read_bytes()
    override_path = root / f"phase1b-right-search-{callback}-{GROUP}-source.bin"
    assert len(before_source) == len(observed_source) == len(after_source) == 0x10000
    assert before_source == observed_source
    assert after_source == override_path.read_bytes()
    changed = [i for i, (a, b) in enumerate(zip(before_source, after_source)) if a != b]
    assert len(changed) == 116
    assert all(0xC000 <= i < 0xC800 and i % 16 == 0 and
               after_source[i] == before_source[i] | 0x10 for i in changed)

    for screen in range(960, callback + 1):
        name = f"swap-screen-{screen:04d}.png"
        assert png_rows(trial / name) == png_rows(baseline / name), (callback, screen)
    if callback == 979:
        assert digest(trial / "swap-screen-0980.png") == digest(prior_screen980)

    screens = []
    for screen in range(callback + 1, END_SCREEN + 1):
        name = f"swap-screen-{screen:04d}.png"
        before = png_rows(baseline / name)
        after = png_rows(trial / name)
        rows = []
        for item in scan(before, screen):
            if not 153 <= item["y"] <= 163:
                continue
            y, left, right = item["y"], item["left"], item["right"]
            rows.append({"y": y, "left": left, "right": right,
                         "left_changed": not same_pixel(before, after, y, left),
                         "right_changed": not same_pixel(before, after, y, right)})
        screens.append({"screen": screen, "baseline_sha256": digest(baseline / name),
                        "hidden_sha256": digest(trial / name),
                        "detected_rows": len(rows),
                        "both_changed": sum(r["left_changed"] and r["right_changed"]
                                            for r in rows),
                        "rows": rows})
    return {"callback": callback, "source_before_sha256": digest(baseline / source_name),
            "override_sha256": digest(override_path),
            "source_after_sha256": digest(trial / f"source-{callback:04d}-ysprites-after.bin"),
            "changed_hide_bytes": len(changed), "screens": screens,
            "input_log_sha256": digest(trial / "phase1b-input.log")}


def main(root, prior_screen980):
    baseline = root / "phase1b-forward-baseline-112-990"
    results = [trial_record(root, baseline, callback, prior_screen980)
               for callback in CALLBACKS]
    output = root / "result.json"
    output.write_text(json.dumps({"baseline_dir": baseline.name,
                                  "prior_screen980_sha256": digest(prior_screen980),
                                  "results": results}, indent=2) + "\n")
    print(json.dumps({"private_result": str(output), "sha256": digest(output),
                      "causal_counts": [{"callback": r["callback"],
                                         "screens": [(s["screen"], s["detected_rows"],
                                                      s["both_changed"])
                                                     for s in r["screens"]]}
                                        for r in results]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("prior_screen980", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve(), args.prior_screen980.resolve())
