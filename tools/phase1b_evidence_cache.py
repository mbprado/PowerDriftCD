"""Opt-in, content-keyed MAME replay manifest for private experiment outputs."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4


SCHEMA = 1
RUNTIME_ENV_NAMES = {"HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE"}
RUNTIME_ENV_PREFIXES = ("PDRIFT_", "SDL_", "MAME_", "DYLD_", "XDG_", "LC_")


def runtime_environment(env):
    """Pass only declared MAME/Lua inputs, excluding transient shell metadata."""
    return {name: value for name, value in env.items()
            if name in RUNTIME_ENV_NAMES or
            name.startswith(RUNTIME_ENV_PREFIXES)}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def private_rom_inputs(manifest, rompath):
    """Verify the owner-local loose ROM set and return labeled input paths."""
    directory = rompath.resolve() / "pdrift"
    entries = []
    for line in manifest.read_text().splitlines():
        name, size, expected = line.split()
        assert Path(name).name == name and len(expected) == 64
        path = directory / name
        assert path.is_file() and path.stat().st_size == int(size)
        assert file_hash(path) == expected, f"ROM manifest mismatch: {name}"
        entries.append((f"rom/{name}", path, expected))
    assert entries and len({label for label, _, _ in entries}) == len(entries)
    assert {path.name for path in directory.iterdir() if path.is_file()} == {
        path.name for _, path, _ in entries}
    return entries


def file_records(directory):
    records = {}
    for path in sorted(directory.rglob("*")):
        assert not path.is_symlink()
        if path.is_dir():
            continue
        assert path.is_file()
        name = path.relative_to(directory).as_posix()
        records[name] = {"size": path.stat().st_size,
                         "sha256": file_hash(path)}
    return records


def valid_outputs(directory, expected):
    if not directory.is_dir() or not expected:
        return False
    try:
        actual = file_records(directory)
    except (AssertionError, OSError):
        return False
    return actual == expected


def replay(cache_root, trial, cmd, env, inputs, required):
    """Return 'hit' or 'executed'; never count a hit as a fresh replay."""
    cache_root.mkdir(parents=True, exist_ok=True)
    descriptions = {}
    for label, path, known_hash in inputs:
        assert label not in descriptions and path.is_file()
        actual = file_hash(path)
        assert known_hash is None or actual == known_hash
        descriptions[label] = {"sha256": actual, "size": path.stat().st_size}
    run_env = runtime_environment(env)
    env_hash = hashlib.sha256(json.dumps(
        sorted(run_env.items()), separators=(",", ":")).encode()).hexdigest()
    request = {"schema": SCHEMA, "command": cmd, "cwd": str(trial.resolve()),
               "environment_names": sorted(run_env),
               "environment_sha256": env_hash, "inputs": descriptions}
    key = hashlib.sha256(json.dumps(request, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()
    manifest = cache_root / f"{key}.json"
    lock = cache_root / f"{key}.lock"
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    try:
        if manifest.is_file():
            try:
                old = json.loads(manifest.read_text())
                if (old.get("request") == request and
                        valid_outputs(trial, old.get("outputs")) and
                        all(name in old["outputs"] for name in required)):
                    return "hit", key
            except (ValueError, OSError, TypeError):
                pass
        if trial.exists():
            assert trial.is_dir() and not trial.is_symlink()
            if any(trial.iterdir()):
                trial.rename(trial.with_name(trial.name + ".invalid." + uuid4().hex))
        trial.mkdir(parents=True, exist_ok=True)
        with (trial / "phase1b-input.log").open("w") as log:
            subprocess.run(cmd, cwd=trial, env=run_env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        outputs = file_records(trial)
        assert all(name in outputs for name in required)
        record = {"request": request, "outputs": outputs}
        temporary = cache_root / f"{key}.{uuid4().hex}.tmp"
        temporary.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
        temporary.replace(manifest)
        return "executed", key
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
