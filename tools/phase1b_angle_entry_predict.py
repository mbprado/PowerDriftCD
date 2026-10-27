#!/usr/bin/env python3
"""Predict one Power Drift main-CPU index from pre-producer state."""

import argparse
import hashlib
import json
from pathlib import Path
import re


FIELDS = ("a0", "a1", "a4", "a5", "depth", "smooth", "state2a",
          "state7a", "flag1", "flag2")
INPUT = re.compile(r"PILOT_INPUT pc=034680 " +
                   " ".join(fr"{name}=([0-9A-F]+)" for name in FIELDS))
TARGET = re.compile(r"PILOT_TARGET pc=0346F0 a4=([0-9A-F]+) "
                    r"a5=([0-9A-F]+) index=([0-9A-F]+)")
FRAME = re.compile(r"PILOT_FRAME,(\d+)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed16(value):
    value &= 0xffff
    return value - 0x10000 if value & 0x8000 else value


def events(path, pattern):
    frame = None
    output = []
    for line in path.read_text().splitlines():
        marker = FRAME.search(line)
        if marker:
            frame = int(marker.group(1))
        hit = pattern.search(line)
        if hit:
            assert frame is not None
            output.append((frame, tuple(int(item, 16) for item in hit.groups())))
    assert [frame for frame, _ in output] == list(range(961, 1000, 2))
    return output


def word(table, offset):
    assert offset >= 0 and offset + 2 <= len(table) and offset % 2 == 0
    return int.from_bytes(table[offset:offset + 2], "big")


def prediction(root, trial):
    table_dir = root / f"inputs-{trial}"
    tables = {}
    hashes = {}
    for address in (0x1fa000, 0x1fb000):
        before = table_dir / f"table-0960-{address:06X}.bin"
        after = table_dir / f"table-1000-{address:06X}.bin"
        assert before.read_bytes() == after.read_bytes()
        assert len(before.read_bytes()) == 0x1000
        tables[address] = before.read_bytes()
        hashes[f"{address:06X}"] = sha(before)
    rom = (root / "pdrift-maincpu.bin").read_bytes()
    assert len(rom) == 0x80000
    rows = []
    for frame, values in events(table_dir / "debug.log", INPUT):
        data = dict(zip(FIELDS, values))
        assert data["a4"] == 0xc0080 and data["a5"] == 0xc0840
        a0, a1 = data["a0"] & 0x1fffff, data["a1"] & 0x1fffff
        assert (a0, a1) == (0x1fb000, 0x1fa000)
        offset = ((data["depth"] & 0xffe0) >> 4)
        base = word(tables[a0], offset)
        smoothing_input = word(tables[a1], offset)
        smooth = (signed16((smoothing_input + data["smooth"]) & 0xffff) >> 1) & 0xffff
        index = base
        if data["state2a"]:
            correction_offset = (0x2894 - 2 * signed16(data["state2a"])) & 0xffffffff
            index = (index + word(rom, correction_offset)) & 0xffff
        if (data["flag1"] >> 8) & 8 and (data["flag2"] >> 8) & 8:
            index = (index + 0x200) & 0xffff
        index = (index + (signed16(data["state7a"]) >> 1)) & 0x3ff
        rows.append({"frame": frame, "entry_state": data,
                     "table_byte_offset": offset,
                     "predicted_base": base, "predicted_smooth": smooth,
                     "predicted_index": index})
    return {"schema": 1, "trial_pulse": trial,
            "input_trace_sha256": sha(table_dir / "debug.log"),
            "rom_sha256": hashlib.sha256(rom).hexdigest(),
            "table_sha256": hashes, "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("mode", choices=("predict", "validate"))
    parser.add_argument("--pulse", type=int, default=48)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    output = root / f"prediction-{args.pulse}.json"
    if args.mode == "predict":
        assert not output.exists(), "prediction already frozen; do not overwrite"
        record = prediction(root, args.pulse)
        output.write_text(json.dumps(record, indent=2) + "\n")
        print("predictions frozen:", len(record["predictions"]), sha(output))
        return
    record = json.loads(output.read_text())
    assert record == prediction(root, args.pulse), "inputs or model changed after freeze"
    target = root / f"targets-{args.pulse}/debug.log"
    observed = events(target, TARGET)
    assert len(observed) == len(record["predictions"])
    differences = []
    for row, (frame, (a4, a5, value)) in zip(record["predictions"], observed):
        assert (frame, a4, a5) == (row["frame"], 0xc0080, 0xc0840)
        if row["predicted_index"] != value:
            differences.append({"frame": frame, "predicted": row["predicted_index"],
                                "observed": value})
    result = {"schema": 1, "pulse": args.pulse,
              "prediction_sha256": sha(output), "target_trace_sha256": sha(target),
              "count": len(observed), "exact": len(observed) - len(differences),
              "differences": differences}
    result_path = root / f"validation-{args.pulse}.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print("held-out:", result["exact"], "/", result["count"],
          "exact; differences:", len(differences))


if __name__ == "__main__":
    main()
