#!/usr/bin/env python3
"""Wrap the original IP in a Genesis ROM for VDP preview, not CD boot proof."""

import pathlib
import struct
import sys


def build(ip):
    image = bytearray(0x200 + len(ip))
    struct.pack_into(">II", image, 0, 0x00FF0000, 0x00000200)
    image[0x100:0x110] = b"SEGA MEGA DRIVE "
    title = b"PHASE 0 TEXT PREVIEW".ljust(48, b" ")
    image[0x120:0x150] = title
    image[0x150:0x180] = title
    image[0x1F0:0x200] = b"E".ljust(16, b" ")
    image[0x200:] = ip
    return image


if __name__ == "__main__":
    source, destination = map(pathlib.Path, sys.argv[1:3])
    destination.write_bytes(build(source.read_bytes()))
