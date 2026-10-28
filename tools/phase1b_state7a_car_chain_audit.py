#!/usr/bin/env python3
"""Check the private pulse-204 $7A-to-foreground-sprite trace chain."""

import hashlib
import json
from pathlib import Path
import re
import struct

from phase1b_state7a_visual_gate import screen_diff


ROOT = Path(__file__).resolve().parents[1] / "build/private"
BASE_SCREEN = ROOT / "phase1b-pulse204-screen967-native-baseline"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(directory, pattern):
    return re.findall(pattern, (ROOT / directory / "debug.log").read_text(), re.M)


def images_equal(left, right, frames):
    for frame in frames:
        name = f"swap-screen-{frame:04d}.png"
        assert digest(left / name) == digest(right / name), (left, right, frame)


def main():
    path = {}
    for side in ("baseline", "plus16"):
        directory = f"phase1b-state7a-path-{side}"
        reads = events(directory, r"^STATE7A_PATH pc=034D44 .*?word7a=([0-9A-F]{4})")
        after = events(directory, r"^STATE7A_PATH pc=034AD8 .*?word84=([0-9A-F]{4}) word7a=([0-9A-F]{4})")
        indexes = events(directory, r"^FIELD_C pc=034B84 .*?d2=([0-9A-F]{8})")
        outputs = events(directory, r"^FIELD_C pc=034BA6 .*?fieldc=([0-9A-F]{4})")
        assert len(reads) == len(after) == len(indexes) == len(outputs) == 4
        path[side] = {"old7a": reads[-1], "updated84": after[-1][0],
                      "updated7a": after[-1][1],
                      "table_index": int(indexes[-1], 16),
                      "fieldc": outputs[-1], "debug_sha256": digest(ROOT / directory / "debug.log")}
    assert path["baseline"]["old7a"] == "FFFE"
    assert path["plus16"]["old7a"] == "000E"
    assert path["baseline"]["updated7a"] == path["plus16"]["updated7a"] == "FFFD"
    assert (path["baseline"]["updated84"], path["plus16"]["updated84"]) == ("FFE4", "FFD4")
    assert (path["baseline"]["table_index"], path["plus16"]["table_index"]) == (2, 4)
    assert (path["baseline"]["fieldc"], path["plus16"]["fieldc"]) == ("0FD8", "0FF6")

    records = {}
    for side, expected in (("baseline", "0FD8"), ("plus16", "0FF6")):
        writer_dir = f"phase1b-state7a-listwriter-{side}"
        log = (ROOT / writer_dir / "debug.log").read_text()
        assert f"addr=0C9F5C data=0000{expected} pc=037638" in log
        words = []
        for frame in range(968, 972):
            raw = (ROOT / writer_dir / f"shared-list-{frame:04d}.bin").read_bytes()
            assert len(raw) == 0x2000
            words.append(struct.unpack_from(">4I", raw, 0x750))
        assert len(set(words)) == 1 and words[0][3] == int(expected + "0080", 16)
        sprite_dir = f"phase1b-state7a-list-{side}"
        consumed = events(sprite_dir,
                          r"^YSPRITE_INPUT_AFTER pc=00DD6A .*?d3=([0-9A-F]{8}) a2=18C6B0$")
        assert len(consumed) == 3 and consumed[-1] == expected + "0080"
        writes = events(sprite_dir,
                        r"^YSPRITE_REGS addr=18C6B6 data=0000([0-9A-F]{4}) pc=00E0CE")
        assert len(writes) == 3
        records[side] = {"list_word": expected + "0080",
                         "sprite_word_c6b6": writes[-1],
                         "listwriter_debug_sha256": digest(ROOT / writer_dir / "debug.log"),
                         "subx_debug_sha256": digest(ROOT / sprite_dir / "debug.log")}
        prior = (BASE_SCREEN if side == "baseline" else
                 ROOT / "phase1b-pulse204-state7a-plus16-966")
        images_equal(prior, ROOT / sprite_dir, range(960, 983))
    assert records["baseline"]["sprite_word_c6b6"] == "CA5A"
    assert records["plus16"]["sprite_word_c6b6"] == "CBEF"

    hides = {}
    source = (BASE_SCREEN / "source-0970-ysprites.bin").read_bytes()
    for slot, screen, expected_pixels in (("E6B0", 971, 2521),
                                           ("E6C0", 971, 299),
                                           ("C6B0", 972, 2519)):
        offset = int(slot, 16)
        override = ROOT / f"phase1b-state7a-hide-{slot}-970.bin"
        changed = override.read_bytes()
        assert len(source) == len(changed) == 0x10000
        assert [i for i, (a, b) in enumerate(zip(source, changed)) if a != b] == [offset]
        assert changed[offset] == source[offset] | 0x10
        names = ([f"phase1b-state7a-hide-{slot}"] +
                 (["phase1b-state7a-hide-E6B0-r1", "phase1b-state7a-hide-E6B0-r2"]
                  if slot == "E6B0" else []))
        trial_hashes = []
        for name in names:
            trial = ROOT / name
            log = (trial / "phase1b-input.log").read_text(errors="replace")
            assert f"SOURCE_OVERRIDE,970,ysprites,{slot},0010," in log
            assert (trial / "source-0970-ysprites-after.bin").read_bytes() == changed
            images_equal(BASE_SCREEN, trial, range(960, 971))
            delta = screen_diff(BASE_SCREEN / f"swap-screen-{screen:04d}.png",
                                trial / f"swap-screen-{screen:04d}.png")
            assert delta and delta["pixels"] == expected_pixels
            trial_hashes.append({"directory": name, "changed_pixels": delta["pixels"],
                                 "screen_sha256": digest(trial / f"swap-screen-{screen:04d}.png"),
                                 "log_sha256": digest(trial / "phase1b-input.log")})
        assert len({x["screen_sha256"] for x in trial_hashes}) == 1
        if slot == "E6B0":
            assert len({x["log_sha256"] for x in trial_hashes}) == 3
        hides[slot] = {"screen": screen, "override_sha256": digest(override),
                       "trials": trial_hashes}
    paired = {}
    for side in ("baseline", "plus16"):
        original = (BASE_SCREEN if side == "baseline" else
                    ROOT / "phase1b-pulse204-state7a-plus16-966")
        trial = ROOT / f"phase1b-state7a-hide-pair-{side}"
        override = ROOT / f"phase1b-state7a-hide-E6B0-E6C0-{side}.bin"
        before = (original / "source-0970-ysprites.bin").read_bytes()
        after = override.read_bytes()
        assert len(before) == len(after) == 0x10000
        assert [i for i, (a, b) in enumerate(zip(before, after)) if a != b] == [
            0xe6b0, 0xe6c0]
        assert all(after[i] == before[i] | 0x10 for i in (0xe6b0, 0xe6c0))
        assert (trial / "source-0970-ysprites-after.bin").read_bytes() == after
        assert "SOURCE_OVERRIDE,970,ysprites,E6B0,0020," in (
            trial / "phase1b-input.log").read_text(errors="replace")
        images_equal(original, trial, range(960, 971))
        paired[side] = {"override_sha256": digest(override),
                        "screen971_sha256": digest(trial / "swap-screen-0971.png")}
    assert paired["baseline"]["screen971_sha256"] == paired["plus16"]["screen971_sha256"]
    result = {"schema": 1, "pulse": 204, "source_revision": "af972a2",
              "main_state_path": path, "shared_list_and_subx": records,
              "exact_slot_hides": hides, "paired_hide": paired,
              "road_camera_mapping_status": "INCONCLUSIVE"}
    output = ROOT / "phase1b-state7a-car-chain-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("$7A chain PASS, E6B0 fresh hides", len(hides["E6B0"]["trials"]),
          "road camera", result["road_camera_mapping_status"], output)


if __name__ == "__main__":
    main()
