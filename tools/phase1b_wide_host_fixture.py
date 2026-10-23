#!/usr/bin/env python3
"""Build a private, original-asset 128x64 width reference from bounded arcade metrics."""

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


WIDTH, HEIGHT = 128, 64
CROP_TOP, CROP_BOTTOM = 134, 190
GRASS = ((28, 92, 42), (35, 105, 47))
ROAD = ((88, 89, 91), (96, 97, 99))
SHOULDER = ((188, 42, 35), (232, 221, 201))
CENTER = (239, 220, 92)
ROAD_COLORS = set(ROAD + SHOULDER + (CENTER,))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk(kind, payload):
    body = kind + payload
    return (struct.pack(">I", len(payload)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xffffffff))


def write_png(path, rows, scale=1):
    width, height = WIDTH * scale, HEIGHT * scale
    raw = bytearray()
    for row in rows:
        expanded = b"".join(bytes(pixel) * scale for pixel in row)
        for _ in range(scale):
            raw.extend(b"\x00" + expanded)
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2,
                                         0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))
    path.write_bytes(data)


def read_png_rows(path, width, height):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    at, compressed = 8, bytearray()
    while at < len(data):
        length = struct.unpack_from(">I", data, at)[0]
        kind = data[at+4:at+8]
        payload = data[at+8:at+8+length]
        assert zlib.crc32(kind + payload) & 0xffffffff == struct.unpack_from(
            ">I", data, at+8+length)[0]
        if kind == b"IHDR":
            assert struct.unpack(">IIBBBBB", payload) == (width, height, 8, 2,
                                                          0, 0, 0)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        at += length + 12
    raw = zlib.decompress(compressed)
    stride = width * 3 + 1
    assert len(raw) == height * stride
    assert all(raw[y*stride] == 0 for y in range(height))
    return [[tuple(raw[y*stride+1+3*x:y*stride+1+3*x+3])
             for x in range(width)] for y in range(height)]


def arcade_to_output_row(arcade_y):
    assert CROP_TOP <= arcade_y <= CROP_BOTTOM
    return round((arcade_y - CROP_TOP) * (HEIGHT - 1)
                 / (CROP_BOTTOM - CROP_TOP))


def arcade_edge_to_output(left_arcade, right_arcade):
    # Output pixel center x samples arcade coordinate 2.5*x + 0.75.
    included = [x for x in range(WIDTH)
                if 4*left_arcade <= 10*x + 3 <= 4*right_arcade]
    assert included
    return included[0], included[-1]


def interpolate(first, second, row):
    y0, left0, right0 = first
    y1, left1, right1 = second
    assert y0 <= row <= y1 and y0 != y1
    fraction = (row - y0) / (y1 - y0)
    return (round(left0 + fraction * (left1 - left0)),
            round(right0 + fraction * (right1 - right0)))


def build(root):
    source = root / "phase1b-right-extent.json"
    data = json.loads(source.read_text())
    band_source = root / "phase1b-causal-boundary-rows.json"
    bands = json.loads(band_source.read_text())
    mapped_bands = []
    for item in bands["records"]:
        if item["descriptor_frame"] != 974 or item["depth_index"] not in (0, 1):
            continue
        rows = [entry["y"] for entry in item["boundary_changes"]]
        assert rows and all(CROP_TOP <= y <= CROP_BOTTOM for y in rows)
        mapped_bands.append({"side": item["side"],
                             "depth_index": item["depth_index"],
                             "arcade_edge_rows": [min(rows), max(rows)],
                             "output_edge_rows": [arcade_to_output_row(min(rows)),
                                                  arcade_to_output_row(max(rows))]})
    strip_edges = {}
    for item in bands["records"]:
        if item["descriptor_frame"] == 974 and item["depth_index"] == 1:
            strip_edges[item["side"]] = {
                entry["y"]: entry["baseline_x"]
                for entry in item["boundary_changes"]}
    assert set(strip_edges) == {"center", "left"}
    case, = [case for case in data["cases"]
             if (case["side"], case["descriptor_frame"], case["depth_index"])
             == ("center", 974, 1)]
    accepted = [entry for entry in case["edge_rows"]
                if entry["right_extent_is_sand_boundary"]]
    assert [entry["y"] for entry in accepted] == list(range(156, 163))
    anchors = [(0, 58, 69, "synthetic top")]
    for entry in accepted:
        arcade_y = entry["y"]
        right = entry["right_sand_x"]
        left = right - entry["sand_to_sand_width"] + 1
        output_y = arcade_to_output_row(arcade_y)
        output_left, output_right = arcade_edge_to_output(left, right)
        anchors.append((output_y, output_left, output_right, f"measured arcade Y={arcade_y}"))
    anchors.append((HEIGHT-1, 0, WIDTH-1, "synthetic bottom"))
    assert len(set(entry[0] for entry in anchors)) == len(anchors)
    rows, geometry = [], []
    for y in range(HEIGHT):
        matching = [entry for entry in anchors if entry[0] == y]
        if matching:
            left, right = matching[0][1:3]
            provenance = matching[0][3]
        else:
            below = max((entry for entry in anchors if entry[0] < y),
                        key=lambda entry: entry[0])
            above = min((entry for entry in anchors if entry[0] > y),
                        key=lambda entry: entry[0])
            left, right = interpolate(below[:3], above[:3], y)
            provenance = "interpolated"
        assert 0 <= left <= right < WIDTH
        geometry.append({"row": y, "left": left, "right": right,
                         "width": right - left + 1, "provenance": provenance})
        center = (left + right) // 2
        pixels = []
        for x in range(WIDTH):
            if not left <= x <= right:
                color = GRASS[(x//8 + y//8) & 1]
            elif x - left < 2 or right - x < 2:
                color = SHOULDER[(y//4) & 1]
            elif x == center and (y//6) % 2 == 0:
                color = CENTER
            else:
                color = ROAD[(x//8 + y//8) & 1]
            pixels.append(color)
        rows.append(pixels)
    destination = root / "phase1b-wide-host-fixture"
    destination.mkdir(parents=True, exist_ok=True)
    image = destination / "road-128x64.png"
    preview = destination / "road-preview-512x256.png"
    write_png(image, rows)
    write_png(preview, rows, scale=4)
    decoded = read_png_rows(image, WIDTH, HEIGHT)
    assert decoded == rows
    for item, decoded_row in zip(geometry, decoded):
        road = [x for x, color in enumerate(decoded_row) if color in ROAD_COLORS]
        assert road == list(range(item["left"], item["right"] + 1))
    for output_y, left, right, provenance in anchors:
        assert geometry[output_y]["left"] == left
        assert geometry[output_y]["right"] == right
    steering_reference = []
    for entry in accepted:
        arcade_y = entry["y"]
        output_y = arcade_to_output_row(arcade_y)
        center_arcade_left = strip_edges["center"][arcade_y]
        left_arcade_left = strip_edges["left"][arcade_y]
        center_output_left = arcade_edge_to_output(center_arcade_left, 319)[0]
        left_output_left = arcade_edge_to_output(left_arcade_left, 319)[0]
        assert center_output_left == geometry[output_y]["left"]
        width = geometry[output_y]["width"]
        steering_reference.append({
            "arcade_y": arcade_y, "output_row": output_y,
            "arcade_left_delta": left_arcade_left - center_arcade_left,
            "output_left_delta": left_output_left - center_output_left,
            "center_output_left": center_output_left,
            "left_output_left": left_output_left,
            "right_if_center_width_held": left_output_left + width - 1,
            "would_clip_right": left_output_left + width - 1 >= WIDTH})
    assert read_png_rows(preview, WIDTH*4, HEIGHT*4)[0][0] == rows[0][0]
    metadata = {"source_result_sha256": digest(source),
                "source_band_result_sha256": digest(band_source),
                "source_case": "center descriptor 974 depth $3400, screen 975",
                "arcade_y_crop_inclusive": [CROP_TOP, CROP_BOTTOM],
                "mapped_callback_974_bands": mapped_bands,
                "output_dimensions": [WIDTH, HEIGHT],
                "horizontal_sample_arcade_x": "2.5 * output_x + 0.75",
                "anchors": [{"output_row": y, "left": left, "right": right,
                             "provenance": provenance}
                            for y, left, right, provenance in anchors],
                "left_steering_reference": steering_reference,
                "rows": geometry, "image_sha256": digest(image),
                "preview_sha256": digest(preview)}
    result = destination / "result.json"
    result.write_text(json.dumps(metadata, indent=2) + "\n")
    for anchor in metadata["anchors"]:
        print(anchor)
    print("private image:", image)
    print("private result:", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    build(parser.parse_args().private_root.resolve())
