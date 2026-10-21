#!/usr/bin/env python3
"""Validate a private Y-Board state-to-projection trace at matching lookup positions."""

import argparse
import re
import sys
from pathlib import Path

from phase1b_projection_replay import signed16
from phase1b_transform_producer import load_events, value


SIDES = ("center", "left", "right")
BASE_PCS = ("034E0A", "034AE8", "034AEC", "034AF0", "034C34",
            "034C38", "034C48", "0347C8", "034912")
BASE_POSITION = ("034AE8", "034AEC", "034AF0")


def parse_trace(path):
    writes, speeds = {}, {}
    frame = None
    for line in path.read_text().splitlines():
        marker = re.search(r"SEQUENCE_FRAME,(\d+)", line)
        if marker:
            frame = int(marker.group(1))
        if frame is None or frame < 961 or frame > 999:
            continue
        if "UPSTREAM_WRITE " in line or "UPSTREAM_SPEED " in line:
            fields = dict(re.findall(r"([a-z][a-z0-9_]*)=([0-9A-F]+)", line))
            if "UPSTREAM_WRITE " in line:
                assert "cpu=maincpu" in line, (path, line)
                pc = fields["pc"]
                bucket = writes.setdefault(frame, {})
                assert pc not in bucket, (path, frame, pc)
                bucket[pc] = fields
            else:
                assert frame not in speeds, (path, frame)
                speeds[frame] = fields
    return writes, speeds


def angle_sources(path):
    return {frame: next(fields for kind, fields in events
                        if kind == "ANGLE_SOURCE")
            for frame, events in load_events(path).items()}


def position_sources(path):
    return {frame: next(fields for kind, fields in events
                        if kind == "POSITION_SOURCE")
            for frame, events in load_events(path).items()}


def offset_sources(path):
    return {frame: next(fields for kind, fields in events
                        if kind == "OFFSET_SOURCE")
            for frame, events in load_events(path).items()}


def first_difference(reference, other, field):
    return next((frame for frame in range(961, 1000, 2)
                 if reference[frame][field] != other[frame][field]), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    root = parser.parse_args().private_root
    runs = {}
    for side in SIDES:
        path = root / f"phase1b-upstream-speed-{side}" / "debug.log"
        writes, speeds = parse_trace(path)
        angles = angle_sources(path)
        positions = position_sources(path)
        offsets = offset_sources(path)
        expected_frames = list(range(961, 1000, 2))
        assert sorted(writes) == sorted(speeds) == sorted(angles) == expected_frames
        extra = 0
        for frame in expected_frames:
            row, speed = writes[frame], speeds[frame]
            assert set(BASE_PCS) <= set(row), (side, frame, set(row))
            assert set(row) <= set(BASE_PCS) | {"034894", "0348A0"}
            extra += len(set(row) - set(BASE_PCS))
            assert value(row["034E0A"], "data") == value(angles[frame], "tilt")
            assert value(speed, "old_depth") == value(angles[frame], "road_depth")
            assert signed16(value(speed, "speed")) >> 1 == signed16(
                value(speed, "half"))
            assert value(row["034912"], "data") == (
                value(speed, "old_depth") + value(speed, "half")) & 0xffff
            for pc, field in (("034C38", "x"), ("034C34", "y"),
                              ("0347C8", "z")):
                assert value(row[pc], "data") == value(positions[frame], field)
            if frame < 999:
                following = frame + 2
                assert value(row["034912"], "data") == value(
                    angles[following], "road_depth")
                assert value(row["034C48"], "data") == value(
                    offsets[following], "source")
        runs[side] = {"writes": writes, "speeds": speeds, "angles": angles}
        print(f"{side}: 20/20 speed/depth steps and state chains; "
              f"{extra} late-adjustment state writes")
    for side in ("left", "right"):
        ref, current = runs["center"], runs[side]
        exact = [frame for frame in range(961, 1000, 2)
                 if value(ref["angles"][frame], "road_depth") == value(
                     current["angles"][frame], "road_depth")]
        bucket = [frame for frame in range(961, 1000, 2)
                  if (value(ref["angles"][frame], "road_depth") & 0xffe0)
                  == (value(current["angles"][frame], "road_depth") & 0xffe0)]
        for frame in exact:
            left, right = ref["writes"][frame], current["writes"][frame]
            assert all(value(left[pc], "data") == value(right[pc], "data")
                       for pc in BASE_POSITION), (side, frame, "base")
            assert all(value(left[pc], "data") != value(right[pc], "data")
                       for pc in ("034C34", "034C38")), (side, frame, "final")
        first_speed = next((frame for frame in range(961, 1000, 2)
                            if value(ref["speeds"][frame], "half") != value(
                                current["speeds"][frame], "half")), None)
        print(f"{side}: {len(exact)} exact-position comparisons: "
              f"{len(exact)}/{len(exact)} same base triples, "
              f"{len(exact)}/{len(exact)} changed adjusted X/Y pairs; "
              f"{len(bucket)} same lookup buckets; first half-speed difference "
              f"at marker {first_speed}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, TypeError,
            StopIteration) as exc:
        sys.exit(str(exc))
