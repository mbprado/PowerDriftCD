#!/usr/bin/env python3
"""Aggregate frozen pulse-204 screen-968 interval and repeat results."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "build/private"
EXPECTED = (
    ("C000", "0380", 0), ("C380", "0380", 10),
    ("C380", "01C0", 0), ("C540", "01C0", 10),
    ("C540", "00E0", 0), ("C620", "00E0", 10),
    ("C620", "0070", 10), ("C690", "0070", 0),
    ("C620", "0040", 10), ("C660", "0030", 0),
    ("C620", "0020", 10), ("C640", "0020", 0),
    ("C620", "0010", 0), ("C630", "0010", 10),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(start, size, repeat=0):
    suffix = f"-r{repeat}" if repeat else ""
    path = ROOT / f"phase1b-pulse204-screen968-{start}-{size}{suffix}.json"
    record = json.loads(path.read_text())
    assert (record["pulse"], record["callback"], record["screen"],
            record["start"], record["size"], record["repeat"]) == (
                204, 967, 968, start, size, repeat)
    assert record["prior_screens_equal"]
    assert record["screen_changed"] == record["native_transparent"]
    assert len(record["vector"]) == 10
    assert all(a == b for a, b in record["vector"])
    trial = ROOT / f"phase1b-pulse204-screen968-native-{start}-{size}{suffix}"
    override = ROOT / f"phase1b-pulse204-screen968-{start}-{size}{suffix}-source.bin"
    assert record["override_sha256"] == digest(override)
    assert record["log_sha256"] == digest(trial / "phase1b-input.log")
    assert record["screen_sha256"] == digest(trial / "swap-screen-0968.png")
    assert record["native967_sha256"] == digest(trial / "ybitmap-0967.raw")
    log = (trial / "phase1b-input.log").read_text(errors="replace")
    assert "STEER_PULSE=204" in log and "INPUT,960,steer-204" in log
    assert "STATE_LOAD,950," in log
    assert f"SOURCE_OVERRIDE,967,ysprites,{start},{size}," in log
    return {"start": start, "size": size, "repeat": repeat,
            "slots_hidden": record["slots_hidden"],
            "screen_changed": record["screen_changed"],
            "native_transparent": record["native_transparent"],
            "score_sha256": digest(path),
            "override_sha256": record["override_sha256"],
            "screen_sha256": record["screen_sha256"],
            "native967_sha256": record["native967_sha256"],
            "log_sha256": record["log_sha256"]}


def main():
    intervals = []
    for start, size, expected in EXPECTED:
        record = load(start, size)
        assert record["screen_changed"] == record["native_transparent"] == expected
        intervals.append(record)
    repeats = [intervals[-1], load("C630", "0010", 1),
               load("C630", "0010", 2)]
    for key in ("override_sha256", "screen_sha256", "native967_sha256"):
        assert len({item[key] for item in repeats}) == 1, key
    assert len({item["log_sha256"] for item in repeats}) == 3
    assert all(item["slots_hidden"] == 1 and item["screen_changed"] == 10 and
               item["native_transparent"] == 10 for item in repeats)
    result = {"schema": 1, "pulse": 204, "screen": 968,
              "exact_descriptor_offset": "C630",
              "intervals": intervals, "fresh_exact_slot_runs": repeats,
              "source_attribution_status": "PASS",
              "adapter_status": "INCONCLUSIVE"}
    output = ROOT / "phase1b-screen968-narrow-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("intervals", len(intervals), "exact-slot fresh runs", len(repeats),
          "source", result["source_attribution_status"], output)


if __name__ == "__main__":
    main()
