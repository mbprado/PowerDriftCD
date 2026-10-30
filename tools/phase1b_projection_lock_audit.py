#!/usr/bin/env python3
"""Audit one same-run cross-CPU count/lock interval before a projected copy."""

import argparse
import hashlib
import json
import re
from pathlib import Path


STAGE = re.compile(r"PROJECTION_LOCK_STAGE name=(ENTRY|TAS|LOCKED|COPY|RELEASE) "
                   r"pc=([0-9A-F]{6}) count=([0-9A-F]{4}) lock=([0-9A-F]{2}) "
                   r"a5=0C1D00")
WRITE = re.compile(r"PROJECTION_LOCK_WRITE cpu=(maincpu|subx|suby) "
                   r"field=(COUNT|LOCK) pc=([0-9A-F]{6}) addr=([0-9A-F]{6}) "
                   r"data=([0-9A-F]{8}) count=([0-9A-F]{4}) lock=([0-9A-F]{2})")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory):
    control_path = directory / "phase1b-input.log"
    control = control_path.read_text(errors="replace")
    assert "STEER_PULSE=124" in control
    assert "PROJECTION_LOCK_ARMED,maincpu+subx+suby,960" in control
    assert "PROJECTION_LOCK_CLEARED,962" in control
    log_path = directory / "debug.log"
    log = log_path.read_text(errors="replace")
    assert "Error in expression" not in log
    first = log.split("PROJECTION_LOCK_FRAME,962", 1)[0]
    assert "PROJECTION_LOCK_FRAME,961" in first
    events = []
    for line in first.splitlines():
        found = STAGE.search(line)
        if found:
            name, pc, count, lock = found.groups()
            events.append({"kind": "stage", "name": name, "pc": pc,
                           "count": int(count, 16), "lock": int(lock, 16)})
            continue
        found = WRITE.search(line)
        if found:
            cpu, field, pc, address, data, count, lock = found.groups()
            events.append({"kind": "write", "cpu": cpu, "field": field,
                           "pc": pc, "address": address, "data": int(data, 16),
                           "count": int(count, 16), "lock": int(lock, 16)})
    def stage(name):
        rows = [(i, row) for i, row in enumerate(events)
                if row["kind"] == "stage" and row["name"] == name]
        assert len(rows) == 1, (name, len(rows))
        return rows[0]
    entry_i, entry = stage("ENTRY")
    tas_i, tas = stage("TAS")
    locked_i, locked = stage("LOCKED")
    copy_i, copy = stage("COPY")
    release_i, release = stage("RELEASE")
    assert entry_i < tas_i < locked_i < copy_i < release_i
    assert entry["count"] == 0x27 and entry["lock"] == 0
    assert tas["count"] == locked["count"] == copy["count"] == 0x28
    assert tas["lock"] == 0 and locked["lock"] == copy["lock"] == 0x80
    between = events[entry_i + 1:tas_i]
    assert len(between) == 3
    acquire, increment, unlock = between
    assert acquire["kind"] == increment["kind"] == unlock["kind"] == "write"
    assert [row["cpu"] for row in between] == ["suby"] * 3
    assert [(row["field"], row["data"]) for row in between] == \
           [("LOCK", 0x80), ("COUNT", 0x28), ("LOCK", 0)]
    assert acquire["lock"] == 0 and acquire["count"] == 0x27
    assert increment["lock"] == 0x80 and increment["count"] == 0x27
    assert unlock["lock"] == 0x80 and unlock["count"] == 0x28
    lock_writes = [row for row in events[tas_i + 1:locked_i]
                   if row["kind"] == "write"]
    assert len(lock_writes) == 1
    assert lock_writes[0]["cpu"] == "maincpu"
    assert lock_writes[0]["field"] == "LOCK"
    assert lock_writes[0]["data"] == 0x80 and lock_writes[0]["lock"] == 0
    assert not [row for row in events[locked_i + 1:copy_i]
                if row["kind"] == "write" and row["field"] == "COUNT"]
    result = {"status": "PASS", "entry_count": f"{entry['count']:04X}",
              "watch_action_visible_pc": increment["pc"],
              "suby_incremented_count": f"{increment['data']:04X}",
              "main_lock_count": f"{locked['count']:04X}",
              "copy_count": f"{copy['count']:04X}",
              "target_interval_events": release_i - entry_i + 1,
              "debug_sha256": digest(log_path),
              "control_sha256": digest(control_path)}
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    audit(args.directory)


if __name__ == "__main__":
    main()
