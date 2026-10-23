#!/usr/bin/env python3
"""Audit the reachable Y-sprite descriptor page in private MAME captures."""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from phase1b_mild_steer_width import digest


FRAMES = range(968, 977)
SLOTS = (0xA600, 0xA630, 0xA660, 0xE610, 0xE630, 0xE660)


def traverse(raw):
    assert len(raw) == 0x10000
    seen = set()
    chain = []
    offset = 0
    while offset not in seen:
        assert 0 <= offset < len(raw) and offset % 16 == 0
        first = struct.unpack_from(">H", raw, offset)[0]
        if first & 0x8000:
            return chain, "end_marker", offset
        seen.add(offset)
        chain.append(offset)
        offset = (struct.unpack_from(">H", raw, offset + 14)[0] & 0xfff) * 16
    return chain, "repeat", offset


def main(root):
    baseline = root / "phase1b-mild-steer-112"
    records = []
    for frame in FRAMES:
        path = baseline / f"source-{frame:04d}-ysprites.bin"
        chain, stop, stop_offset = traverse(path.read_bytes())
        pages = Counter(f"{offset >> 12:X}" for offset in chain if offset)
        assert len(pages) == 1 and stop == "end_marker"
        records.append({"callback": frame, "source_sha256": digest(path),
                        "reachable_count": len(chain) - 1,
                        "active_page": next(iter(pages)),
                        "stop_offset": f"{stop_offset:04X}",
                        "selected_slots": {f"{slot:04X}": slot in chain
                                           for slot in SLOTS}})
    assert [r["active_page"] for r in records] == list("CA8ECA8EC")
    # A hide in source RAM can persist while the draw list points to another page.
    old = root / "phase1b-right-search-E630-00040-only-E630-E660"
    persistent = []
    for frame in (971, 972, 973, 974):
        b = (baseline / f"source-{frame:04d}-ysprites.bin").read_bytes()
        h = (old / f"source-{frame:04d}-ysprites.bin").read_bytes()
        diffs = [i for i, (a, c) in enumerate(zip(b, h)) if a != c]
        persistent.append({"callback": frame, "changed_offsets":
                           [f"{i:04X}" for i in diffs]})
    assert [p["changed_offsets"] for p in persistent] == [
        ["E630", "E660"], ["E630", "E660"],
        ["E630", "E660"], []]
    output = root / "phase1b-ysprite-page-audit.json"
    output.write_text(json.dumps({"records": records,
                                  "persistent_hide": persistent}, indent=2) + "\n")
    for record in records:
        print(record["callback"], record["active_page"],
              record["reachable_count"], record["selected_slots"])
    print("private result:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    main(args.private_root.resolve())
