#!/usr/bin/env python3
"""Report exact boot-region matches without outputting firmware/disc bytes."""

import argparse
import hashlib
import json
import pathlib


WINDOW = 16
DISC_START = 0x200
DISC_END = 0x800


def longest_match(disc_sector, firmware):
    index = {}
    for offset in range(len(firmware) - WINDOW + 1):
        key = firmware[offset:offset + WINDOW]
        if len(set(key)) > 4:  # Ignore trivial padding and repeated fill patterns.
            index.setdefault(key, []).append(offset)

    best = (0, None, None)
    for disc_offset in range(DISC_START, DISC_END - WINDOW + 1):
        key = disc_sector[disc_offset:disc_offset + WINDOW]
        for bios_offset in index.get(key, ()):
            length = WINDOW
            while (disc_offset + length < DISC_END
                   and bios_offset + length < len(firmware)
                   and disc_sector[disc_offset + length] == firmware[bios_offset + length]):
                length += 1
            if length > best[0]:
                best = (length, disc_offset, bios_offset)
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=pathlib.Path, help="MODE1/2048 reference data track")
    parser.add_argument("bios", type=pathlib.Path, nargs="+", help="local firmware file(s)")
    args = parser.parse_args()
    with args.iso.open("rb") as source:
        sector = source.read(DISC_END)
    if len(sector) != DISC_END:
        parser.error("ISO is shorter than one 2048-byte sector")

    results = []
    for bios_path in args.bios:
        firmware = bios_path.read_bytes()
        length, disc_offset, bios_offset = longest_match(sector, firmware)
        results.append({
            "bios": str(bios_path),
            "bios_sha256": hashlib.sha256(firmware).hexdigest(),
            "match_bytes": length,
            "disc_offset": disc_offset,
            "bios_offset": bios_offset,
            "matched_region_sha256": (hashlib.sha256(
                sector[disc_offset:disc_offset + length]).hexdigest() if length else None),
        })
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
