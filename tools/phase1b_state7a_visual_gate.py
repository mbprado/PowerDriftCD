#!/usr/bin/env python3
"""Audit private pulse-204 state-$7A callback perturbations and visual lag."""

import hashlib
import json
from pathlib import Path

from phase1b_swap_compare import png_rows


ROOT = Path(__file__).resolve().parents[1] / "build/private"
BASE = ROOT / "phase1b-pulse204-screen967-native-baseline"
PREFIX = "phase1b-pulse204-state7a-"
TRIALS = (("plus2-965", 965, "0000", "0002"),
          ("plus2-966", 966, "FFFE", "0000"),
          ("plus16-966", 966, "FFFE", "000E"),
          ("plus16-966-r1", 966, "FFFE", "000E"),
          ("plus16-966-r2", 966, "FFFE", "000E"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def screen_diff(left, right):
    a, b = png_rows(left), png_rows(right)
    assert len(a) == len(b) == 224
    changed = [(x, y) for y, (arow, brow) in enumerate(zip(a, b))
               for x in range(320)
               if arow[3*x:3*x+3] != brow[3*x:3*x+3]]
    if not changed:
        return None
    return {"pixels": len(changed),
            "bbox": [min(x for x, _ in changed), max(x for x, _ in changed),
                     min(y for _, y in changed), max(y for _, y in changed)]}


def source_diff(left, right):
    a, b = left.read_bytes(), right.read_bytes()
    assert len(a) == len(b) == 0x10000
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if not changed:
        return None
    return {"bytes": len(changed),
            "descriptor_offsets": [f"{offset:04X}"
                                   for offset in sorted({i & ~15 for i in changed})],
            "byte_offsets": [f"{i:04X}" for i in changed]}


def audit_trial(name, frame, before, after):
    trial = ROOT / (PREFIX + name)
    log = (trial / "phase1b-input.log").read_text(errors="replace")
    assert "STATE_LOAD,950," in log and "INPUT,960,steer-204" in log
    assert f"STATE7A_DELTA,{frame},0C08BA,{before},{after}," in log
    screens, sources = {}, {}
    for n in range(960, 983):
        image = f"swap-screen-{n:04d}.png"
        source = f"source-{n:04d}-ysprites.bin"
        screen = screen_diff(BASE / image, trial / image)
        sprite = source_diff(BASE / source, trial / source)
        if screen:
            screens[str(n)] = screen
        if sprite:
            sources[str(n)] = sprite
    return {"trial": name, "write_callback": frame,
            "old_word": before, "new_word": after,
            "changed_screens": screens, "changed_source_snapshots": sources,
            "screen971_sha256": digest(trial / "swap-screen-0971.png"),
            "screen972_sha256": digest(trial / "swap-screen-0972.png"),
            "source970_sha256": digest(trial / "source-0970-ysprites.bin"),
            "log_sha256": digest(trial / "phase1b-input.log")}


def main():
    prediction = ROOT / "phase1b-upstream-inputs/state24-forward-prediction-204.json"
    assert digest(prediction) == (
        "6a68c7fa35098f88e82def20d243eab199864d4daffc5db1c0f3660b0e1b74c1")
    predicted = json.loads(prediction.read_text())
    marker965, = (p for p in predicted["predictions"] if p["frame"] == 965)
    assert marker965["predicted_7a"] == 0xfffe
    records = [audit_trial(*trial) for trial in TRIALS]
    assert not records[0]["changed_screens"] and not records[0]["changed_source_snapshots"]
    assert not records[1]["changed_screens"] and not records[1]["changed_source_snapshots"]
    repeats = records[2:]
    for record in repeats:
        assert set(record["changed_screens"]) == {"971", "972"}
        assert set(record["changed_source_snapshots"]) == {
            str(n) for n in range(970, 983)}
        assert record["changed_source_snapshots"]["970"]["descriptor_offsets"] == [
            "C6B0", "C6C0", "E6B0", "E6C0"]
        assert record["changed_screens"]["971"]["pixels"] == 2280
        assert record["changed_screens"]["972"]["pixels"] == 2280
    for key in ("changed_screens", "changed_source_snapshots",
                "screen971_sha256", "screen972_sha256", "source970_sha256"):
        assert len({json.dumps(record[key], sort_keys=True) for record in repeats}) == 1
    assert len({record["log_sha256"] for record in repeats}) == 3
    result = {"schema": 1, "pulse": 204, "source_revision": "8e6c990",
              "prediction_sha256": digest(prediction),
              "baseline_screen967_sha256": digest(BASE / "swap-screen-0967.png"),
              "baseline_source966_sha256": digest(BASE / "source-0966-ysprites.bin"),
              "trials": records, "state_to_screen_packet_status": "INCONCLUSIVE"}
    output = ROOT / "phase1b-state7a-visual-gate.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("state7a callbacks", len(records), "repeat runs", len(repeats),
          "visual packet", result["state_to_screen_packet_status"], output)


if __name__ == "__main__":
    main()
