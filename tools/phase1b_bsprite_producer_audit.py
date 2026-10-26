#!/usr/bin/env python3
"""Audit private sub-CPU-Y staging and sprite-RAM writes for record 4."""

import argparse
import hashlib
import json
from pathlib import Path
import re


STAGE = 0x1F8630
DISPLAY = 0x188040


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(path, tag):
    pattern = re.compile(rf"^{tag},(\d+),([0-9A-F]+),([0-9A-F]+),([0-9A-F]+)$")
    result = []
    for line in path.read_text().splitlines():
        match = pattern.match(line)
        if match:
            result.append((int(match[1]), *(int(match[i], 16) for i in (2, 3, 4))))
    return result


def watches(path, tag):
    pattern = re.compile(rf"^{tag} pc=([0-9A-F]+) addr=([0-9A-F]+) data=([0-9A-F]+)")
    result = []
    for line in path.read_text().splitlines():
        match = pattern.match(line)
        if match:
            result.append(tuple(int(match[i], 16) for i in (1, 2, 3)))
    return result


def audit(trials, baseline_ram):
    final = baseline_ram.read_bytes()[0x40:0x4c]
    assert len(final) == 12
    results = []
    sequences = []
    for trial in trials:
        log = trial / "phase1b-input.log"
        stage = events(log, "BSTAGE_TAP")
        display = events(log, "BSPRITE_TAP")
        stage_watch = watches(trial / "debug.log", "BSTAGE_WRITE")
        display_watch = watches(trial / "debug.log", "BSPRITE_WRITE")
        assert len(stage) == len(stage_watch) == 576
        assert len(display) == len(display_watch) == 1418
        for (frame, addr, data, mask), (pc, watched_addr, watched_data) in zip(stage, stage_watch):
            assert 0 <= frame < 480
            assert watched_addr == addr + (1 if mask == 0x00ff else 0)
            assert watched_data == (data & (0xff if mask != 0xffff else 0xffff))
            assert pc < 0x40000
        for (frame, addr, data, mask), (pc, watched_addr, watched_data) in zip(display, display_watch):
            assert mask == 0xffff and (addr, data) == (watched_addr, watched_data)
            assert pc < 0x40000
        stage_final = [(addr, data, mask, pc) for (frame, addr, data, mask), (pc, _, _)
                       in zip(stage, stage_watch) if frame == 411]
        display_final = [(addr, data, pc) for (frame, addr, data, _), (pc, _, _)
                         in zip(display, display_watch) if frame == 412]
        assert [(a, mask) for a, _, mask, _ in stage_final] == [
            (STAGE, 0xff00), (STAGE, 0x00ff),
            (STAGE + 2, 0xffff), (STAGE + 4, 0xffff),
            (STAGE + 6, 0xffff), (STAGE + 8, 0xff00),
            (STAGE + 8, 0x00ff), (STAGE + 10, 0xffff)]
        assert [(a, d) for a, d, _ in display_final] == [
            (DISPLAY + i * 2, int.from_bytes(final[2*i:2*i+2], "big"))
            for i in range(6)]
        assert [pc for _, _, _, pc in stage_final] == [
            0x13172, 0x13174, 0x13176, 0x13178,
            0x1317a, 0x1317c, 0x1317e, 0x13182]
        assert [pc for _, _, pc in display_final] == [
            0x131ca, 0x131ca, 0x131cc, 0x131cc, 0x131ce, 0x131ce]
        before = (trial / "source-0411-bsource.bin").read_bytes()
        after = (trial / "source-0412-bsource.bin").read_bytes()
        next_frame = (trial / "source-0413-bsource.bin").read_bytes()
        assembled = bytearray(before[0x30:0x3c])
        for addr, data, mask, _ in stage_final:
            offset = addr - STAGE
            if mask & 0xff00:
                assembled[offset] = (data >> 8) & 0xff
            if mask & 0x00ff:
                assembled[offset + 1] = data & 0xff
        assert before[0x30:0x3c] != final
        assert bytes(assembled) == after[0x30:0x3c] == next_frame[0x30:0x3c] == final
        results.append({"trial": str(trial), "stage_writes": len(stage),
                        "display_writes": len(display),
                        "stage_source_frame": 411, "display_copy_frame": 412,
                        "stage_pcs": [f"{pc:06X}" for _, _, _, pc in stage_final],
                        "copy_pcs": [f"{pc:06X}" for _, _, pc in display_final],
                        "log_sha256": digest(log),
                        "debug_log_sha256": digest(trial / "debug.log")})
        sequences.append((stage, display, digest(trial / "phase1b-trial-0300.png")))
    assert all(item == sequences[0] for item in sequences[1:])
    return {"result": "PASS", "record": 4, "staging_address": "1F8630",
            "display_address": "188040", "replays": results,
            "common_frame300_sha256": sequences[0][2],
            "baseline_record_sha256": hashlib.sha256(final).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_ram", type=Path)
    parser.add_argument("trials", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(audit(args.trials, args.baseline_ram), indent=2))


if __name__ == "__main__":
    main()
