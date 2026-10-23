#!/usr/bin/env python3
"""Check two BlastEm road screenshots against host geometry without Pillow."""

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


VIEW_X, VIEW_Y, WIDTH, HEIGHT = 96, 89, 128, 64
ROAD_RGB = {(255, 255, 255), (255, 0, 0), (146, 146, 146),
            (255, 255, 0)}


def decode(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    at, palette, compressed = 8, [], bytearray()
    while at < len(data):
        size = struct.unpack_from(">I", data, at)[0]
        kind = data[at+4:at+8]
        payload = data[at+8:at+8+size]
        assert (zlib.crc32(kind + payload) & 0xffffffff
                == struct.unpack_from(">I", data, at+8+size)[0])
        if kind == b"IHDR":
            assert struct.unpack(">IIBBBBB", payload) == (256, 240, 8, 3,
                                                          0, 0, 0)
        elif kind == b"PLTE":
            palette = [tuple(payload[i:i+3])
                       for i in range(0, len(payload), 3)]
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        at += size + 12
    assert palette
    raw = zlib.decompress(compressed)
    assert len(raw) == 240 * 257
    assert all(raw[y*257] == 0 for y in range(240))
    rows = [raw[y*257+1:(y+1)*257] for y in range(240)]
    nonblack = [(x, y) for y, row in enumerate(rows)
                for x, value in enumerate(row) if palette[value] != (0, 0, 0)]
    assert (min(x for x, _ in nonblack), max(x for x, _ in nonblack),
            min(y for _, y in nonblack), max(y for _, y in nonblack)) == (
                VIEW_X, VIEW_X+WIDTH-1, VIEW_Y, VIEW_Y+HEIGHT-1)
    return rows, palette


def main(metrics_path, intermediate_path, final_path, output_path):
    metrics = json.loads(metrics_path.read_text())
    checks = []
    decoded = []
    for name, frames, path in (("intermediate", (15, 16), intermediate_path),
                               ("final", (59,), final_path)):
        rows, palette = decode(path)
        decoded.append(rows)
        screen_y = VIEW_Y + 28
        road = [x for x in range(WIDTH)
                if palette[rows[screen_y][VIEW_X+x]] in ROAD_RGB]
        expected = metrics["frames"][frames[0]]["anchor_rows"][3]
        assert all(metrics["frames"][frame]["anchor_rows"][3] == expected
                   for frame in frames)
        assert road == list(range(expected["left"], expected["right"] + 1))
        checks.append({"capture": name, "reference_packets": frames,
                       "output_row": 28, "left": road[0],
                       "right": road[-1], "width": len(road),
                       "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    changed = sum(decoded[0][y][x] != decoded[1][y][x]
                  for y in range(VIEW_Y, VIEW_Y+HEIGHT)
                  for x in range(VIEW_X, VIEW_X+WIDTH))
    assert changed > 0
    output_path.write_text(json.dumps({"checks": checks,
                                       "changed_viewport_pixels": changed},
                                      indent=2) + "\n")
    print(checks, "changed viewport pixels:", changed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("intermediate", type=Path)
    parser.add_argument("final", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.metrics, args.intermediate, args.final, args.output)
