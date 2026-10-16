# Phase 0 — Toolchain, emulators and automated data collection

**Status: NOT STARTED.** This is an assignment brief, not a report of completed tests.

## Goals
Establish a reproducible Sega CD native boot/demo pipeline and assess whether Codex can run tests and collect meaningful data without Windows.

## Emulator candidates (verify rather than assume)
- BlastEm — check Sega CD boot accuracy and debugger coverage on current macOS/Linux builds.
- Genesis Plus GX — independent compatibility check.
- MAME — arcade Power Drift reference and possible debugger/instrumentation.
- ares — independent console emulation.
- ares-for-ai — experimental headless integration; verify provenance, license, maturity and actual Sega CD instrumentation.

For each, record binary version, source commit, host system, image format, firmware requirement, debug interface, both-CPU register visibility, Word RAM/ASIC/VDP trace support, scripting/headless options, deterministic frames, and known inaccuracies.

## Tasks
1. Identify and pin a working cross-compiler/assembler/linker and CD image builder for macOS and Linux.
2. Assemble/build a minimal **original-code, original-assets** Sega CD demo; do not commit BIOS data.
3. Boot it in two independent emulators with correctly sourced local BIOS firmware.
4. Validate breakpoints, step/run, memory inspection and sub-CPU debugging through actual operations.
5. Investigate graphics ASIC completion/busy timing, Word RAM ownership, VDP transfers and practical counters.
6. Define a headless Codex harness capturing stdout/stderr, screenshots, traces and JSON benchmark metadata.
7. Produce a comparison with evidence labels: verified / documented / hypothesis / unsupported.
8. Recommend the primary debugger, secondary emulator and next measurable graphics experiment.

## Exit criteria
- Minimal CD image built from documented source
- Booted under two independent emulators OR precise blockers recorded
- Reproduction instructions for macOS and Linux
- Clear separation between measured and unavailable instrumentation
- No production road renderer until review

## Deliverables
`docs/experiments/toolchain-evaluation.md`, `emulator-comparison.md`, `automation-feasibility.md`, build/test entry points, evidence logs, and a go/no-go recommendation.
