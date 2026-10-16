# Reproducible testing and evidence

## Levels
- **L0 — static/documented:** read-only specifications or source inspection.
- **L1 — emulator executed:** deterministic test actually ran, raw output captured.
- **L2 — independent emulator:** same test executed independently, differences explained.
- **L3 — real console:** measured on stock Mega Drive + Sega CD; record model/region/firmware context where feasible.

## Required test record
Save each experiment as `docs/experiments/YYYY-MM-DD-<slug>.md` with:
- question/hypothesis and expected acceptance criteria
- Git commit and build configuration
- exact compiler, emulator revision, host OS and CPU architecture
- launch/build commands, input seed/script, frame count and image checksum
- raw log/trace paths; checksums where relevant
- units and provenance for every measurement
- observed output, differences, failure modes, and next action

Use a JSON file alongside traces where useful. A proposed starter record is `tests/schema/benchmark.example.json`; do not fill unknown counters with invented values.

## Counters to investigate
Main-CPU cycles, sub-CPU cycles, ASIC busy/latency, Word RAM ownership swaps, transfer bytes/time, VDP VRAM uploads, frame completion deadlines, and video correctness. Each field can remain `null` until measured by trustworthy instrumentation.

## Determinism
Use fixed camera paths, fixed car/traffic seeds, a fixed frame limit (e.g., 600 frames) and known output checksum(s). Keep emulator-host speed separate from emulated cycle timing. Screenshot comparisons are supplementary, not precise timing evidence.

## Result language
Use: `PASS`, `FAIL`, `INCONCLUSIVE`, or `NOT RUN`. If a tool or feature is documented but not executed, mark it **documented only**.
