#!/usr/bin/env python3
"""Build a deterministic, original-code Sega CD Phase 0 boot *candidate*.

This emits a 2048-byte-sector ISO and CUE. It does not supply Sega's
region-dependent security program. Actual boot requires emulator execution.
"""

import argparse
import pathlib
import struct

SECTOR = 2048
SECTORS = 300
ROOT_SECTOR = 20


def both16(value):
    return struct.pack("<H", value) + struct.pack(">H", value)


def both32(value):
    return struct.pack("<I", value) + struct.pack(">I", value)


def directory_record(extent, size, name, flags):
    record = bytearray(34 if len(name) == 1 else 33 + len(name) + (len(name) % 2 == 0))
    record[0] = len(record)
    record[2:10] = both32(extent)
    record[10:18] = both32(size)
    record[18:25] = bytes((126, 10, 16, 0, 0, 0, 0))
    record[25] = flags
    record[28:32] = both16(1)
    record[32] = len(name)
    record[33:33 + len(name)] = name
    return record


def put_text(data, start, size, value):
    encoded = value.encode("ascii")
    if len(encoded) > size:
        raise ValueError(value)
    data[start:start + size] = encoded.ljust(size, b" ")


def build(ip):
    if len(ip) > 0x600:
        raise ValueError("IP exceeds first-sector 0x600-byte space")
    image = bytearray(SECTOR * SECTORS)
    put_text(image, 0, 16, "SEGADISCSYSTEM")
    put_text(image, 0x10, 11, "POWERDRIFT0")
    image[0x1b:0x1d] = b"\x00\x01"
    image[0x1d] = 1
    put_text(image, 0x20, 12, "PHASE0SMOKE")
    struct.pack_into(">4I", image, 0x30, 0x200, 0x600, 0, 0)
    struct.pack_into(">4I", image, 0x40, 0x800, 0x7800, 0, 0)
    image[0x100:0x200] = b" " * 0x100
    put_text(image, 0x100, 16, "SEGA MEGA DRIVE")
    put_text(image, 0x110, 16, "(C) PDCD 2026")
    put_text(image, 0x120, 48, "PHASE ZERO SMOKE")
    put_text(image, 0x150, 48, "PHASE ZERO SMOKE")
    put_text(image, 0x180, 14, "GM PD00001 -00")
    image[0x190:0x193] = b"J  "
    put_text(image, 0x1f0, 16, "E")
    image[0x200:0x200 + len(ip)] = ip

    pvd = memoryview(image)[16 * SECTOR:17 * SECTOR]
    pvd[0:7] = b"\x01CD001\x01"
    pvd[8:40] = b"POWER DRIFT CD".ljust(32, b" ")
    pvd[40:72] = b"PHASE0_SMOKE".ljust(32, b" ")
    pvd[80:88] = both32(SECTORS)
    pvd[120:124] = both16(1)
    pvd[124:128] = both16(1)
    pvd[128:132] = both16(SECTOR)
    pvd[132:140] = both32(10)
    struct.pack_into("<I", pvd, 140, 18)
    struct.pack_into(">I", pvd, 148, 19)
    root = directory_record(ROOT_SECTOR, SECTOR, b"\x00", 2)
    pvd[156:156 + len(root)] = root
    for offset in (813, 830, 847, 864):
        pvd[offset:offset + 17] = b"2026101600000000\x00"
    pvd[881] = 1
    image[17 * SECTOR:17 * SECTOR + 7] = b"\xffCD001\x01"

    image[18 * SECTOR:18 * SECTOR + 10] = bytes((1, 0)) + struct.pack("<I", ROOT_SECTOR) + struct.pack("<H", 1) + b"\x00\x00"
    image[19 * SECTOR:19 * SECTOR + 10] = bytes((1, 0)) + struct.pack(">I", ROOT_SECTOR) + struct.pack(">H", 1) + b"\x00\x00"
    root_sector = ROOT_SECTOR * SECTOR
    parent = directory_record(ROOT_SECTOR, SECTOR, b"\x01", 2)
    image[root_sector:root_sector + len(root)] = root
    image[root_sector + len(root):root_sector + len(root) + len(parent)] = parent
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", type=pathlib.Path)
    parser.add_argument("iso", type=pathlib.Path)
    parser.add_argument("cue", type=pathlib.Path)
    args = parser.parse_args()
    args.iso.write_bytes(build(args.ip.read_bytes()))
    args.cue.write_text(f'FILE "{args.iso.name}" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n', encoding="ascii")


if __name__ == "__main__":
    main()
