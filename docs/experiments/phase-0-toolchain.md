# Phase 0 — Toolchain, emulators and automated data collection

**Status: IN PROGRESS (2026-10-18).** See [the initial smoke test](2026-10-16-phase-0-smoke.md), [BIOS-backed follow-up](2026-10-16-bios-backed-emulator-check.md), [second EU BIOS check](2026-10-16-eu-model2-bios-check.md), [reference boot control](2026-10-17-reference-boot-control.md), [simple-text boot check](2026-10-18-simple-text-boot.md), [Model 2 text-disc check](2026-10-18-model2-text-boot.md), [shared boot-prefix comparison](2026-10-18-shared-boot-prefix.md), [private text-disc boot](2026-10-18-private-text-disc-boot.md), [toolchain evaluation](toolchain-evaluation.md), [emulator comparison](emulator-comparison.md), and [automation feasibility](automation-feasibility.md). **Verified by execution:** BlastEm reached the original `HELLO SEGA CD` IP and displayed its text from a private two-track disc under both owner-supplied EU Model 1 and Model 2 BIOS files. The private disc used an owner-authorized, ignored local Sonic-derived startup prefix and a generated silent audio track; neither proprietary bytes nor the derived disc are tracked. The original-only distributable ISO still falls through to CD PLAYER. **Unsupported:** original-only smoke-disc boot, stock-hardware boot, and hardware-speed claims. The renderer gate remains closed pending Phase 0 review.

**Owner decision (2026-10-18):** use BlastEm alone for future Phase 0 testing, debugging, and logs. Earlier Genesis Plus GX observations remain historical evidence; no further cross-emulator runs are planned. This supersedes the two-emulator task and exit criterion below for ongoing work. A BlastEm pass establishes an emulator-level result only; physical-hardware compatibility remains **unsupported** until separately tested.

**2026-10-18 follow-up — verified by execution:** the [five-second-track EU/US test](2026-10-18-eu-us-five-second-text-boot.md) displayed `HELLO SEGA CD` under EU and U.S. Model 1 and Model 2 BIOSes in BlastEm. The U.S. disc required a longer, locally held U.S. startup sequence; one U.S. Model 1-derived image passed under both U.S. models. Hardware and original-only boot remain **unsupported**.

**Owner decision (2026-10-18):** future development targets the owner's U.S. Genesis/Sega CD (NTSC-U). Use U.S. region images and BIOSes as the primary BlastEm test configuration; EU checks are regressions. Physical-hardware boot and performance testing are deferred until the owner chooses to do them. **Verified by execution:** the private U.S. text image passed in BlastEm, and the [routine smoke build now defaults to U.S.](2026-10-18-us-development-baseline.md). The original-only U.S. build is still a boot candidate, not a verified bootable disc. Do not infer hardware compatibility from emulator output.

**2026-10-18 sub-CPU follow-up — verified by execution:** the [U.S. handshake experiment](2026-10-18-us-subcpu-handshake.md) reached the original `MAIN` system-program callback and exchanged one command/reply word between the CPUs in BlastEm under both U.S. BIOS models. Requesting the sub-CPU level-2 interrupt after writing the command was necessary in this test. No physical-hardware or timing claim follows from this result.

**2026-10-18 level-2 follow-up — verified by execution:** the [dedicated callback experiment](2026-10-18-us-level2-callback.md) stopped in the sub-CPU level-2 callback and received its distinct `I2` reply under both U.S. BIOS models in BlastEm. Interrupt timing and hardware behavior remain **unsupported**.

**2026-10-18 Word RAM follow-up — verified by execution:** the [2M round-trip experiment](2026-10-18-us-wordram-2m-roundtrip.md) switched from the BIOS's observed 1M mode, yielded Word RAM to the sub-CPU, and read back its two written words after RET under both U.S. BIOS models in BlastEm. The Model 2 debugger trace captured `$2A02` during sub ownership and `$2A01` after return. Timing and hardware compatibility remain **unsupported**.

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
