#!/usr/bin/env python3
"""Assemble and check the private Power Drift main-CPU ROM from MAME's map."""

import argparse
import hashlib
import json
from pathlib import Path
import re


# pdrift, MAME 0.289 segaybd.cpp: ROM_LOAD16_BYTE, maincpu, 0x000000-0x07ffff.
CHIPS = (
    ("epr-12017.25", "18df4bd6078b1c76c7061c05a476a7cbf7d0b37b", 0),
    ("epr-12016.24", "506652bdb0f3d23a2cf7ff29732b8ec77c389b46", 1),
    ("epr-11748.27", "f8d3fe059e18896cd0e64711f1a3ee8b6372b4e0", 0x40000),
    ("epr-11747.26", "f84f5689c2edc0853ff173ce20f93f89758b2f31", 0x40001),
)
WINDOWS = (0x000000, 0x033B02, 0x033D1E, 0x034680, 0x03483C,
           0x034AD8, 0x034C30)


def assemble(rom_dir):
    image = bytearray(0x80000)
    chip_hashes = {}
    for name, expected, offset in CHIPS:
        raw = (rom_dir / name).read_bytes()
        actual = hashlib.sha1(raw).hexdigest()
        assert len(raw) == 0x20000 and actual == expected, (name, actual)
        image[offset:offset + 2 * len(raw):2] = raw
        chip_hashes[name] = actual
    return bytes(image), chip_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_rom_dir", type=Path)
    parser.add_argument("private_output_dir", type=Path)
    parser.add_argument("--live-log", type=Path)
    args = parser.parse_args()
    out = args.private_output_dir.resolve()
    assert out.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    out.mkdir(parents=True, exist_ok=True)
    image, chips = assemble(args.private_rom_dir)
    (out / "pdrift-maincpu.bin").write_bytes(image)
    record = {"schema": 1, "region": "maincpu", "size": len(image),
              "sha256": hashlib.sha256(image).hexdigest(), "chips_sha1": chips,
              "windows": {f"{address:06X}": image[address:address + 16].hex()
                          for address in WINDOWS}}
    if args.live_log:
        observed = {int(address, 16): bytes.fromhex(raw) for address, raw in
                    re.findall(r"MAIN_ROM_WINDOW,([0-9A-F]{6}),([0-9a-f]{32})",
                               args.live_log.read_text())}
        assert set(observed) == set(WINDOWS), sorted(observed)
        for address, raw in observed.items():
            assert image[address:address + 16] == raw, f"MAME mismatch at {address:06X}"
        record["live_mame_windows_match"] = len(observed)
    (out / "maincpu-map.json").write_text(json.dumps(record, indent=2) + "\n")
    print("private assembled maincpu:", record["sha256"])
    if args.live_log:
        print("live MAME windows:", record["live_mame_windows_match"], "of", len(WINDOWS), "match")
    print("private address windows:", out / "maincpu-map.json")


if __name__ == "__main__":
    main()
