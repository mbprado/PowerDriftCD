# Project rules — version 1.2

## Mission and constraints
Build a modern, maximal-fidelity Power Drift conversion for stock Mega Drive/Genesis + Sega CD/Mega CD. No enhancement cartridge or hardware modification. Original arcade visuals, especially steep curves, track banking, elevation and camera movement, are the reference. The development baseline is the U.S. Genesis/Sega CD (NTSC-U), matching the owner's console for a future physical test. Use the U.S. Model 2 BIOS in BlastEm for routine development tests. Run U.S. Model 1 compatibility checks at the checkpoints in [the BIOS test policy](experiments/2026-10-18-us-bios-test-policy.md); use the European BIOS as a regression check where useful. Investigate PAL later. Physical-hardware boot and performance tests are deferred by owner decision; emulator results do not establish hardware compatibility.

## Fidelity and tradeoffs
Arcade-faithful handling, track layout, opponent behavior and camera dynamics take precedence over mimicking a hypothetical 1992 conversion. Targets of 30 fps baseline, 60 fps stretch and 320×224 output are **unvalidated goals**, not guarantees. Any compromises must be justified by captured evidence. Smaller viewports and selective detail are legitimate experiments, not assumed solutions.

## Rendering research
Evaluate Sega CD ASIC transforms, offline projection/geometry tables, pre-scaled and pre-rotated assets, VDP sprite/tile composition and hybrid approaches. Benchmark main 68000, sub 68000, stamp engine, 1M versus 2M Word RAM handoffs, VDP DMA/VRAM, video timing and CPU coordination. Track transfer costs as well as compute. Interactive play must not be reduced to pre-rendered movie playback.

## Host environments
Prefer macOS for development; Linux is equally acceptable when it improves debugging, automation, or reproducibility. No Windows, Wine, or Windows-only toolchain without explicit permission.

## Codex / test policy
Codex may use local source, scripts, emulator debugging facilities, logs, screenshots and structured test records. Prefer deterministic input and camera sequences. Cross-emulator passes help but do not establish compatibility with physical hardware. Instrumentation must report whether values represent emulated hardware cycles, wall-clock measurements, estimates, or unresolved/unobservable quantities. Never make up data.

## Source and version discipline
Use Git, isolated branches for risky experiments, readable documentation, reproducible dependencies, and benchmark before/after comparisons. Do not push, merge, PR, release or modify upstream dependencies without explicit authorization for that action. Preserve stable working milestones.

## Copyright and ethics
Keep commercial ROMs, BIOSes, copyrighted art/audio and proprietary extracts outside tracked content. Keep scripts/tools for lawful locally held references separate from distributed assets. Early demos use independently produced graphics and data.

## Milestones and gates
0. Bootable toolchain + debugging/automation feasibility evaluated (original-only boot remains an open gate)
1. Parallel **1A** Sega CD CPU/ASIC/VDP/Word RAM characterization and **1B** early arcade reference feasibility (MAME observations, REA/Ghidra routine/data mapping, sprite format/palette study)
2. Curved/elevated/banked road and camera rendering prototype; adopt proven arcade reference samples when available
3. Cars, roadside objects and sprite scaling prototype, informed by arcade graphics research
4. Integrated renderer under measurable load
5. Arcade gameplay mechanics and content integration, using results from Phase 1B (not postponing initial reverse engineering until here)
6. Playable proof of concept
7. Full game and physical hardware qualification

Phase 1B may run alongside Phase 1A and ongoing Phase 2 synthetic prototypes: **do not block, reset or rewrite working rendering experiments** to wait for arcade disassembly. Its first practical handoff is one reproducible track section and camera trajectory, supported by both dynamic observation and binary/data analysis where feasible. Record tool limitations and distinguish measured observations from hypotheses. Commercial ROMs, BIOSes and extracted assets stay out of tracked files. Arcade research does not override the unresolved original-only disc boot or physical-hardware gates.

Do not promote a milestone without documenting evidence, platform versions, limitations and remaining risks.

## Decision rule
**Measure the hardware limits; do not assume the limits from historical ports.**
