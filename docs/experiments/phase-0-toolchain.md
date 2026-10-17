# Phase 0 — Toolchain, emulators and automated data collection

**Status: IN PROGRESS (2026-10-18).** See [the initial smoke test](2026-10-16-phase-0-smoke.md), [BIOS-backed follow-up](2026-10-16-bios-backed-emulator-check.md), [second EU BIOS check](2026-10-16-eu-model2-bios-check.md), [reference boot control](2026-10-17-reference-boot-control.md), [simple-text boot check](2026-10-18-simple-text-boot.md), [Model 2 text-disc check](2026-10-18-model2-text-boot.md), [shared boot-prefix comparison](2026-10-18-shared-boot-prefix.md), [toolchain evaluation](toolchain-evaluation.md), [emulator comparison](emulator-comparison.md), and [automation feasibility](automation-feasibility.md). **Verified by execution:** two independent emulators reached an EU BIOS UI in earlier work, and BlastEm exposed both 68000 debuggers. A user-supplied working reference reached the main-CPU IP breakpoint under the EU Model 1 BIOS and MODE1/2048 sector format. The original `HELLO SEGA CD` IP displayed text in a BlastEm cartridge preview, while its Sega CD image still fell through to CD PLAYER after Start with both EU Model 1 and Model 2 BIOS files. The reference disc's first 1,390 IP bytes exactly match a sequence in both EU BIOS files; the smoke image has no comparable 16-byte match. An early Japanese BIOS and a header-only expanded layout did not reach IP in the observed tests. **Unsupported:** smoke-disc IP execution and hardware boot. The renderer gate remains closed.

**Owner decision (2026-10-18):** use BlastEm alone for future Phase 0 testing, debugging, and logs. Earlier Genesis Plus GX observations remain historical evidence; no further cross-emulator runs are planned. This supersedes the two-emulator task and exit criterion below for ongoing work. A BlastEm pass establishes an emulator-level result only; physical-hardware compatibility remains **unsupported** until separately tested.

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
3. Boot it in BlastEm with correctly sourced local BIOS firmware; record the owner-approved single-emulator limitation.
4. Validate breakpoints, step/run, memory inspection and sub-CPU debugging through actual operations.
5. Investigate graphics ASIC completion/busy timing, Word RAM ownership, VDP transfers and practical counters.
6. Define a headless Codex harness capturing stdout/stderr, screenshots, traces and JSON benchmark metadata.
7. Produce a comparison with evidence labels: verified / documented / hypothesis / unsupported.
8. Record BlastEm as the primary debugger and the next measurable graphics experiment once the boot gate is reviewed.

## Exit criteria
- Minimal CD image built from documented source
- Booted under BlastEm OR precise blockers recorded, with no cross-emulator compatibility claim
- Reproduction instructions for macOS and Linux
- Clear separation between measured and unavailable instrumentation
- No production road renderer until review

## Deliverables
`docs/experiments/toolchain-evaluation.md`, `emulator-comparison.md`, `automation-feasibility.md`, build/test entry points, evidence logs, and a go/no-go recommendation.
