# Phase 0 — Toolchain, emulators and automated data collection

**Current status (2026-10-20): conditionally reviewed; Phase 1 graphics characterization and an initial perspective-road prototype completed in BlastEm.** The owner accepted the [Phase 0 review](2026-10-18-phase-0-review.md) and the private-disc boot limitation for synthetic BlastEm experiments. This does not close the original-only boot, Linux/headless automation, or physical-hardware questions. **Verified by execution:** the private two-track disc ran the original text IP under EU and U.S. Model 1 and Model 2 BIOS files in BlastEm; main/sub-CPU and Word RAM experiments followed. The [graphics characterization](graphics-characterization.md) and [64×64 road prototype](2026-10-20-perspective-road-prototype.md) subsequently exercised the ASIC-to-VDP path and measured emulator frame pacing. Those results are emulator observations, not hardware-speed measurements. The original-only image still falls through to CD PLAYER; no production game renderer has begun.

| Review item | Current disposition |
| --- | --- |
| macOS build, private Sega CD boot, main/sub-CPU debugger, 2M Word RAM exchange | `PASS` — **verified by execution** in the linked experiment records and [Phase 0 review](2026-10-18-phase-0-review.md). |
| Original-only distributable disc boot | `FAIL` in the observed BlastEm runs; a working original-only boot remains **unsupported**. Private startup bytes and derived images stay ignored. |
| Linux execution, headless graphics, unattended input replay | `NOT RUN`; availability for this project remains **unsupported**. |
| Independent-emulator IP execution | `NOT RUN`; the owner chose BlastEm alone, superseding this original Phase 0 requirement. No cross-emulator compatibility claim is made. |
| ASIC busy/latency, VDP transfer timing, and frame pacing | `PASS` for bounded synthetic cases — **verified by execution** in [Phase 1](graphics-characterization.md) and the [road prototype](2026-10-20-perspective-road-prototype.md) under BlastEm. Larger scenes, runtime trace calculation, and physical-hardware timing remain **unsupported**. |
| Physical-hardware boot or performance | `NOT RUN`; expressly deferred until the owner requests it. |

Earlier evidence remains in the [initial smoke test](2026-10-16-phase-0-smoke.md), [BIOS-backed follow-up](2026-10-16-bios-backed-emulator-check.md), [second EU BIOS check](2026-10-16-eu-model2-bios-check.md), [reference boot control](2026-10-17-reference-boot-control.md), [simple-text boot check](2026-10-18-simple-text-boot.md), [Model 2 text-disc check](2026-10-18-model2-text-boot.md), [shared boot-prefix comparison](2026-10-18-shared-boot-prefix.md), [private text-disc boot](2026-10-18-private-text-disc-boot.md), [toolchain evaluation](toolchain-evaluation.md), [emulator comparison](emulator-comparison.md), and [automation feasibility](automation-feasibility.md).
Those dated records describe the status at the time of each experiment; the disposition above is current.

**Owner decision (2026-10-18):** use BlastEm alone for future Phase 0 testing, debugging, and logs. Earlier Genesis Plus GX observations remain historical evidence; no further cross-emulator runs are planned. This supersedes the two-emulator task and exit criterion below for ongoing work. A BlastEm pass establishes an emulator-level result only; physical-hardware compatibility remains **unsupported** until separately tested.

**2026-10-18 follow-up — verified by execution:** the [five-second-track EU/US test](2026-10-18-eu-us-five-second-text-boot.md) displayed `HELLO SEGA CD` under EU and U.S. Model 1 and Model 2 BIOSes in BlastEm. The U.S. disc required a longer, locally held U.S. startup sequence; one U.S. Model 1-derived image passed under both U.S. models. Hardware and original-only boot remain **unsupported**.

**Owner decision (2026-10-18):** future development targets the owner's U.S. Genesis/Sega CD (NTSC-U). Use U.S. region images and BIOSes as the primary BlastEm test configuration; EU checks are regressions. Physical-hardware boot and performance testing are deferred until the owner chooses to do them. **Verified by execution:** the private U.S. text image passed in BlastEm, and the [routine smoke build now defaults to U.S.](2026-10-18-us-development-baseline.md). The original-only U.S. build is still a boot candidate, not a verified bootable disc. Do not infer hardware compatibility from emulator output.

**2026-10-18 sub-CPU follow-up — verified by execution:** the [U.S. handshake experiment](2026-10-18-us-subcpu-handshake.md) reached the original `MAIN` system-program callback and exchanged one command/reply word between the CPUs in BlastEm under both U.S. BIOS models. Requesting the sub-CPU level-2 interrupt after writing the command was necessary in this test. No physical-hardware or timing claim follows from this result.

**2026-10-18 level-2 follow-up — verified by execution:** the [dedicated callback experiment](2026-10-18-us-level2-callback.md) stopped in the sub-CPU level-2 callback and received its distinct `I2` reply under both U.S. BIOS models in BlastEm. Interrupt timing and hardware behavior remain **unsupported**.

**2026-10-18 Word RAM follow-up — verified by execution:** the [2M round-trip experiment](2026-10-18-us-wordram-2m-roundtrip.md) switched from the BIOS's observed 1M mode, yielded Word RAM to the sub-CPU, and read back its two written words after RET under both U.S. BIOS models in BlastEm. The Model 2 debugger trace captured `$2A02` during sub ownership and `$2A01` after return. Timing and hardware compatibility remain **unsupported**.

**2026-10-18 repeatability follow-up — verified by execution:** the [sixteen-handoff test](2026-10-18-us-wordram-repeat.md) completed numbered, bidirectional data checks across sixteen consecutive 2M ownership switches under both U.S. BIOS models in BlastEm. Latency and stock-hardware repeatability remain **unsupported**.

**2026-10-18 timer follow-up — verified by execution:** the [stopwatch feasibility experiment](2026-10-18-us-wordram-stopwatch.md) recorded sixteen per-transaction tick values and a whole-batch modulo stopwatch delta for the same handoffs. Two boots per U.S. BIOS reproduced 51 ticks for Model 1 and 52 for Model 2 at 30.72 µs nominal resolution. These are BlastEm timer observations, not hardware-speed measurements. Physical-hardware work remains deferred until the owner explicitly requests it.

**Owner decision (2026-10-18):** the [U.S. BIOS test policy](2026-10-18-us-bios-test-policy.md) makes Model 2 the routine BlastEm BIOS and reserves Model 1 for compatibility checkpoints. Both BIOSes passed the functional tests above; the one-tick stopwatch difference does not justify duplicating every development run. No physical-hardware testing is authorized.

## Original Phase 0 plan and goals
Establish a reproducible Sega CD native boot/demo pipeline and assess whether Codex can run tests and collect meaningful data without Windows.

## Emulator candidates (verify rather than assume)
- BlastEm — check Sega CD boot accuracy and debugger coverage on current macOS/Linux builds.
- Genesis Plus GX — independent compatibility check.
- MAME — arcade Power Drift reference and possible debugger/instrumentation.
- ares — independent console emulation.
- ares-for-ai — experimental headless integration; verify provenance, license, maturity and actual Sega CD instrumentation.

For each, record binary version, source commit, host system, image format, firmware requirement, debug interface, both-CPU register visibility, Word RAM/ASIC/VDP trace support, scripting/headless options, deterministic frames, and known inaccuracies.

## Original tasks (review disposition above)
1. Identify and pin a working cross-compiler/assembler/linker and CD image builder for macOS and Linux.
2. Assemble/build a minimal **original-code, original-assets** Sega CD demo; do not commit BIOS data.
3. Boot it in BlastEm with correctly sourced local BIOS firmware; record the owner-approved single-emulator limitation.
4. Validate breakpoints, step/run, memory inspection and sub-CPU debugging through actual operations.
5. Investigate graphics ASIC completion/busy timing, Word RAM ownership, VDP transfers and practical counters.
6. Define a headless Codex harness capturing stdout/stderr, screenshots, traces and JSON benchmark metadata.
7. Produce a comparison with evidence labels: verified / documented / hypothesis / unsupported.
8. Record BlastEm as the primary debugger and the next measurable graphics experiment once the boot gate is reviewed.

## Original exit criteria (review disposition above)
- Minimal CD image built from documented source
- Booted under BlastEm OR precise blockers recorded, with no cross-emulator compatibility claim
- Reproduction instructions for macOS and Linux
- Clear separation between measured and unavailable instrumentation
- No production road renderer until review

## Deliverables
`docs/experiments/toolchain-evaluation.md`, `emulator-comparison.md`, `automation-feasibility.md`, build/test entry points, evidence logs, and a go/no-go recommendation.
