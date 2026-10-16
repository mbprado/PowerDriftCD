#!/usr/bin/env python3
"""Capture one emulator invocation with a PTY, deadline, and JSON metadata.

Raw output stays in build/ (gitignored).  A successful process exit is not a
Sega CD boot assertion; callers must inspect CPU state and video separately.
"""

import argparse
import hashlib
import json
import os
import pathlib
import platform
import pty
import select
import subprocess
import time


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--emulator-version", default="unknown")
    parser.add_argument("--frames", type=int)
    parser.add_argument("--input-seed", type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("emulator command is required after --")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.out_dir / "console.log"
    master, slave = pty.openpty()
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                               start_new_session=True)
    os.close(slave)
    timed_out = False
    terminated_at = None
    with log_path.open("wb") as log:
        while True:
            now = time.monotonic()
            if now - started >= args.timeout and process.poll() is None and terminated_at is None:
                timed_out = True
                process.terminate()
                terminated_at = now
            if terminated_at is not None and now - terminated_at >= 2 and process.poll() is None:
                process.kill()
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    chunk = b""
                if chunk:
                    log.write(chunk)
            if process.poll() is not None:
                break
        while True:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            log.write(chunk)
    os.close(master)
    result = {
        "result": "INCONCLUSIVE", "boot_verified": False,
        "timeout": timed_out, "exit_code": process.returncode,
        "command": command,
        "emulator_version": args.emulator_version,
        "host_os": platform.platform(), "host_arch": platform.machine(),
        "source_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_tree_dirty": bool(subprocess.check_output(
            ["git", "status", "--porcelain"], text=True).strip()),
        "image_sha256": sha256(args.image),
        "console_log_sha256": sha256(log_path),
        "requested_frames": args.frames, "input_seed": args.input_seed,
        "emulated_frames": None, "main_cpu_cycles": None,
        "sub_cpu_cycles": None, "asic_cycles": None,
        "wall_seconds": round(time.monotonic() - started, 3),
        "wall_seconds_provenance": "host monotonic clock; not emulated hardware speed",
    }
    (args.out_dir / "run.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
