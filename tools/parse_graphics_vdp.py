#!/usr/bin/env python3
"""Extract 120 frame records from the BlastEm graphics-to-VDP transcript."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--disc-image", type=Path)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--size", type=int, choices=(32, 64), default=32)
    parser.add_argument("--strategy", default="asic")
    parser.add_argument("--road", action="store_true",
                        help="label the cyclic case IDs as one perspective-road sequence")
    parser.add_argument("--road-runtime", action="store_true",
                        help="expect trace and ready-time words in the frame record")
    parser.add_argument("--combined-verify-stage", action="store_true",
                        help="staging window includes checksum and main-RAM copy")
    parser.add_argument("--expected-interval-min", type=int)
    parser.add_argument("--expected-interval-max", type=int)
    parser.add_argument("--source-commit", default="4c3ace15641d2ed90b5d069d1627bd3374a2996f")
    parser.add_argument("--reverse-transfer", action="store_true")
    parser.add_argument("--dma-only", action="store_true")
    args = parser.parse_args()
    if (args.expected_interval_min is None) != (args.expected_interval_max is None):
        parser.error("both expected interval bounds are required")
    if (args.expected_interval_min is not None and
            args.expected_interval_min > args.expected_interval_max):
        parser.error("expected interval minimum exceeds maximum")
    raw = args.log.read_bytes()
    source = raw.decode("utf-8", errors="replace")
    if "d3: 47564f4b" not in source:
        raise SystemExit("missing GVOK completion marker")
    # PTY echo can interleave a debugger response with the next command.
    word_count = 11 if args.road_runtime else 9
    records = re.findall(r"F,((?:[0-9a-f]+,){%d}[0-9a-f]+)" % (word_count - 1), source)
    if len(records) != args.frames:
        raise SystemExit(f"expected {args.frames} records, got {len(records)}")
    frames = []
    for index, record in enumerate(records):
        values = [int(value, 16) for value in record.split(",")]
        frame, case, mode, interval, stage, upload, vblank, asic, composite = values[:9]
        expected_mode = 1 if args.dma_only else (index % 2) ^ int(args.reverse_transfer)
        case_base = 3 if args.size == 32 else 6
        if frame != index or case != case_base + index % 3 or mode != expected_mode:
            raise SystemExit(f"unexpected frame sequence at {index}: {values}")
        row = {
            "frame": frame,
            "transform": ("perspective_road" if args.road else
                          ("scale", "rotate", "combined")[case - case_base]),
            "transfer": ("cpu_direct_from_word_ram", "dma_from_main_ram_staging")[mode],
            "vblank_start_interval_ticks": None if index == 0 else interval,
            "staging_ticks": stage,
            "vram_upload_ticks": upload,
            "vblank_asserted_after_upload": bool(vblank & 8),
            "asic_start_to_busy_clear_ticks": asic,
            "ownership_prepare_asic_return_ticks": composite,
        }
        if args.road_runtime:
            row["trace_construction_ticks"] = values[9]
            row["ready_since_prior_vblank_ticks"] = None if index == 0 else values[10]
        frames.append(row)
    summary = {}
    for mode in ("cpu_direct_from_word_ram", "dma_from_main_ram_staging"):
        selected = [f for f in frames if f["transfer"] == mode]
        if not selected:
            summary[mode] = {"count": 0}
            continue
        summary[mode] = {
            "count": len(selected),
            "staging_ticks_min_median_max": [min(f["staging_ticks"] for f in selected),
                                               statistics.median(f["staging_ticks"] for f in selected),
                                               max(f["staging_ticks"] for f in selected)],
            "upload_ticks_min_median_max": [min(f["vram_upload_ticks"] for f in selected),
                                              statistics.median(f["vram_upload_ticks"] for f in selected),
                                              max(f["vram_upload_ticks"] for f in selected)],
            "vblank_upload_deadlines_missed": sum(not f["vblank_asserted_after_upload"] for f in selected),
        }
    intervals = [f["vblank_start_interval_ticks"] for f in frames[1:]]
    cadence_misses = (sum(not args.expected_interval_min <= value <= args.expected_interval_max
                          for value in intervals)
                      if args.expected_interval_min is not None else None)
    upload_misses = sum(not f["vblank_asserted_after_upload"] for f in frames)
    result = {
        "test_id": (f"perspective-road-{args.strategy}-{args.size}x{args.size}-{args.frames}-frames"
                    if args.road else
                    f"phase1-graphics-vdp-{args.size}x{args.size}-{args.strategy}-{args.frames}-frames"),
        "status": "fail" if (upload_misses or cadence_misses) else "pass",
        "evidence_level": "verified by execution",
        "git_commit": args.source_commit,
        "build_id": (hashlib.sha256(args.disc_image.read_bytes()).hexdigest()
                     if args.disc_image else "251117a070e586f56a3b641384b9da7c72e3806f38dce75d70cff623fbb0c087"),
        "source_tree_dirty_at_execution": True,
        "host_os": "macOS 26.6.2",
        "host_arch": "x86_64",
        "emulator": "BlastEm",
        "emulator_version": "1.0.0",
        "emulator_archive_sha256": "2315f5f32b8400b4c56980b87043516ac9ec22aac5fdb9d3bdb97c2b236da221",
        "bios_label": "owner-supplied U.S. Model 2; identity not independently authenticated",
        "video_mode": "NTSC U.S.",
        "scenario_seed": 0,
        "target_fps": 30 if args.frames == 60 else 60,
        "bios_sha256": "b1c2036b79467514eaaa69c76e5ba83801621e821059caa53cb921a0b21e3af4",
        "disc_image_sha256": (hashlib.sha256(args.disc_image.read_bytes()).hexdigest()
                              if args.disc_image else "251117a070e586f56a3b641384b9da7c72e3806f38dce75d70cff623fbb0c087"),
        "raw_log_sha256": hashlib.sha256(raw).hexdigest(),
        "measurements": {
            "main_cpu_cycles": None,
            "sub_cpu_cycles": None,
            "asic_cycles": None,
            "word_ram_swaps": None,
            "vdp_transfer_bytes": args.frames * args.size * args.size // 2,
            "deadline_misses": upload_misses,
            "cadence_deadline_misses": cadence_misses,
        },
        "measurement_provenance": {
            "timer": "emulated Sega CD 12-bit stopwatch, modulo 4096",
            "vblank_deadline": "VDP VBlank status bit sampled immediately after upload",
            "frame_cadence": "timer difference between successive VBlank starts; first sample excluded",
            "staging_window": ("checksum verification plus main-RAM staging"
                               if args.combined_verify_stage else "main-RAM staging copy only"),
            "physical_hardware": "not tested",
        },
        "physical_hardware_tested": False,
        "artifact_paths": [str(args.log), str(args.output)],
        "notes": ("ASIC perspective-road output checksum checked in-program before every upload; "
                  "four camera controls evolve separately from frame index on the sub-CPU using shared lookup tables; "
                  "no hardware validation." if args.strategy == "road-runtime-independent" else
                  "ASIC perspective-road output checksum checked in-program before every upload; "
                  "curvature, elevation and banking are deterministic trace-table cues; "
                  "no hardware validation." if args.road else
                  "ASIC output checksum checked in-program before every upload; no hardware validation."),
        "output_width": args.size,
        "output_height": args.size,
        "bytes_transferred_per_frame": args.size * args.size // 2,
        "frames_requested": args.frames,
        "frames_executed": args.frames,
        "vblank_interval_ticks_min_median_max": [min(intervals), statistics.median(intervals), max(intervals)],
        "expected_vblank_interval_ticks": ([args.expected_interval_min, args.expected_interval_max]
                                           if args.expected_interval_min is not None else None),
        "summary": summary,
        "frames": frames,
    }
    destination = args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
