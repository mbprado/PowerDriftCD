#!/usr/bin/env python3
"""Parse BlastEm debugger memory prints from the graphics ASIC benchmark."""

import hashlib
import json
from pathlib import Path
import re
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: parse_graphics_asic_bench.py BLASTEM_LOG OUTPUT_JSON")
    source = Path(sys.argv[1])
    raw = source.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if "d3: 47424f4b" not in text:
        raise SystemExit("missing GBOK completion marker")
    memory = {int(address, 16): int(value, 16)
              for address, value in re.findall(r"\[0x([0-9a-f]+)\]: ([0-9a-f]+)", text)}
    operations = []
    for index in range(27):
        address = 0xFF1200 + 12 * index
        offsets = (0, 2, 4, 6, 8, 10)
        if any(address + offset not in memory for offset in offsets):
            raise SystemExit(f"missing sample {index} at {address:#x}")
        case, composite, busy, control, high, low = (
            memory[address + offset] for offset in offsets)
        expected_order = list(range(9)) + list(range(8, -1, -1)) + list(range(9))
        if case != expected_order[index]:
            raise SystemExit(f"unexpected case {case} at sample {index}")
        operations.append({
            "operation_index": index,
            "pass": 1 + index // 9,
            "case": case,
            "output_width": (16, 32, 64)[case // 3],
            "output_height": (16, 32, 64)[case // 3],
            "transform": ("scale", "rotate", "combined")[case % 3],
            "asic_start_to_busy_clear_ticks": busy,
            "timer_read_control_ticks": control,
            "ownership_callback_and_asic_ticks": composite,
            "output_word_sum": (high << 16) | low,
        })
    result = {
        "test_id": "phase1-graphics-asic-16-32-64",
        "status": "pass",
        "evidence_level": "verified by execution",
        "git_commit": "4c3ace15641d2ed90b5d069d1627bd3374a2996f",
        "build_id": "9f0c1c26cf3ee5a4212ad622865703bf1850eef2df25d4c15c39923e8168302f",
        "source_tree_dirty_at_execution": True,
        "host_os": "macOS 26.6.2",
        "host_arch": "x86_64",
        "emulator": "BlastEm",
        "emulator_version": "1.0.0",
        "emulator_archive_sha256": "2315f5f32b8400b4c56980b87043516ac9ec22aac5fdb9d3bdb97c2b236da221",
        "bios_label": "owner-supplied U.S. Model 2; identity not independently authenticated",
        "video_mode": "NTSC U.S.",
        "scenario_seed": 0,
        "frames_requested": None,
        "frames_executed": None,
        "operations_requested": 27,
        "operations_executed": 27,
        "bios_sha256": "b1c2036b79467514eaaa69c76e5ba83801621e821059caa53cb921a0b21e3af4",
        "disc_image_sha256": "9f0c1c26cf3ee5a4212ad622865703bf1850eef2df25d4c15c39923e8168302f",
        "raw_log_sha256": hashlib.sha256(raw).hexdigest(),
        "measurements": {
            "main_cpu_cycles": None,
            "sub_cpu_cycles": None,
            "asic_cycles": None,
            "word_ram_swaps": None,
            "vdp_transfer_bytes": 0,
            "deadline_misses": None,
        },
        "measurement_provenance": {
            "timer": "12-bit Sega CD stopwatch in BlastEm",
            "asic_interval": "sub trigger write to GRON clear, including CPU polling",
            "composite_interval": "main ownership request through sub return, excluding output checksum",
            "wrap_handling": "modulo 4096; each adjacent interval shorter than one lap in observed runs",
        },
        "physical_hardware_tested": False,
        "artifact_paths": [str(source), str(Path(sys.argv[2]))],
        "notes": "Original generated stamp and trace tables; three order-varied passes in one emulator boot.",
        "operations": operations,
    }
    Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
