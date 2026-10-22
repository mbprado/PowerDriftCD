#!/usr/bin/env python3
"""Audit a bounded shared-X intervention against arcade projection arithmetic."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from phase1b_projection_replay import hexfield, project, signed16


RUNS = {"sham": 0, "plus16": 0x10, "plus32": 0x20,
        "plus32-repeat": 0x20, "plus256": 0x100}
TARGETS = (2, 3, 4)
OUTPUTS = ("projected4", "projected6")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(directory):
    path = directory / "geometry-samples.csv"
    with path.open() as file:
        rows = {(int(row["frame"]), int(row["index"])): row
                for row in csv.DictReader(file)}
    assert len(rows) == 11 * 12
    return rows


def signed_output(row):
    return tuple(signed16(hexfield(row, field)) for field in OUTPUTS)


def check_debug(path, delta):
    lines = path.read_text()
    pattern = (r"GLOBAL_X_ENTRY pc=033D1E a5=([0-9A-F]+) old=([0-9A-F]+)"
               r"\n+GLOBAL_X_CHANGED a5=\1 value=([0-9A-F]+)"
               r"\n+GLOBAL_X_OUTPUT a5=\1 x=([0-9A-F]+) y=([0-9A-F]+)"
               r" changed=([0-9A-F]+)"
               r"\n+GLOBAL_X_RESTORED a5=\1 value=([0-9A-F]+)")
    events = re.findall(pattern, lines)
    assert len(events) == 3, (path, len(events))
    assert {int(event[0], 16) for event in events} == {
        0x0c1c80 + 0x40 * index for index in TARGETS}
    for address, old, changed, _, _, held, restored in events:
        assert int(changed, 16) == (int(old, 16) + delta) & 0xffff, address
        assert held == changed and restored == old, address
    assert lines.count("GLOBAL_X_ENTRY") == 3
    assert lines.count("GLOBAL_X_RESTORED") == 3
    return events


def analyze(root):
    runs = {name: load(root / f"phase1b-global-x-{name}") for name in RUNS}
    baseline = runs["sham"]
    assert runs["plus32"] == runs["plus32-repeat"]
    results = {"runs": {}, "samples": []}
    for name, delta in RUNS.items():
        directory = root / f"phase1b-global-x-{name}"
        events = check_debug(directory / "debug.log", delta)
        rows = runs[name]
        differences = []
        for key, current in rows.items():
            previous = baseline[key]
            changed = [field for field in current if current[field] != previous[field]]
            if changed:
                assert key[0] in (964, 965) and key[1] in TARGETS, (name, key)
                assert set(changed) <= set(OUTPUTS), (name, key, changed)
                differences.append((key, changed))
        results["runs"][name] = {
            "delta_raw": delta,
            "geometry_csv_sha256": sha256(directory / "geometry-samples.csv"),
            "debug_log_sha256": sha256(directory / "debug.log"),
            "intervention_count": len(events),
            "changed_rows": len(differences),
        }
        for index in TARGETS:
            before = baseline[962, index]
            after = baseline[964, index]
            modified = dict(before, global1c=f"{(hexfield(before, 'global1c') + delta) & 0xffff:04X}")
            predicted = project(modified, hexfield(after, "global18"))
            observed = signed_output(rows[964, index])
            assert predicted == observed, (name, index, predicted, observed)
            if name != "plus32-repeat":
                results["samples"].append({
                    "run": name, "depth": before["depth"],
                    "baseline_xy": signed_output(after),
                    "observed_xy": observed, "predicted_xy": predicted})
    output = root / "phase1b-global-x-results.json"
    output.write_text(json.dumps(results, indent=2) + "\n")
    for sample in results["samples"]:
        print(sample["run"], sample["depth"], sample["baseline_xy"],
              sample["observed_xy"])
    print("15/15 transient writes restored; 15/15 projection pairs predicted")
    print("plus32 replay byte-identical; only selected projection words changed")
    print(f"private results: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    analyze(parser.parse_args().private_root)
