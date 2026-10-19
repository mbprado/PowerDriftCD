# Power Drift CD

**Mission:** develop the most arcade-faithful Power Drift conversion achievable on an **unmodified Sega Mega Drive/Genesis + Sega CD/Mega CD**, using modern engineering, rigorous measurement, and offline precomputation.

**Status:** [Phase 1 graphics characterization](docs/experiments/graphics-characterization.md) verified original graphics ASIC transforms, Genesis VDP display, and small deterministic 30/60 Hz pipelines in BlastEm after the [Phase 0 review](docs/experiments/2026-10-18-phase-0-review.md). An initial [64×64 perspective-road prototype](docs/experiments/2026-10-20-perspective-road-prototype.md) now runs at 30 Hz in BlastEm with synthetic curvature, elevation and banking cues. U.S. Genesis/Sega CD (NTSC-U) is the development baseline. Original-only boot and physical-hardware compatibility remain open; there is no running port or measured hardware-performance claim.

## Principles
- Original console hardware is the target; no expansion CPU/RAM or emulator-only shortcuts.
- Arcade-feel first: banked tracks, elevation, camera motion, controls, opponents.
- Benchmark hardware-relative timing, Word RAM handoff, graphics ASIC, VDP transfers, and frame pacing before choosing an engine architecture.
- macOS first, Linux welcome for debug/automation; Windows requires explicit approval.
- Codex may build, instrument, execute deterministic tests, and report data; **never invent results**.
- All game ROMs, BIOS images, and extracted copyrighted assets stay outside this repository.

## Getting started
1. Read [project rules](docs/project-rules.md) and [Codex agent rules](AGENTS.md).
2. Follow [Phase 0 plan](docs/experiments/phase-0-toolchain.md).
3. Record findings in [test evidence format](docs/testing.md).
4. Review the initial GitHub issue before writing game engine code.

## Roadmap
0. Toolchain + debugger + emulator evaluation
1. Sega CD hardware characterization
2. Banking/elevation road renderer
3. Sprite/object renderer
4. Combined renderer and profiling
5. Arcade-reference data adaptation
6. Playable racing demonstration
7. Complete game, hardware validation, release

## Repository layout
- `docs/` — design decisions, experiments, hardware notes
- `src/` — eventual console engine (main CPU, sub CPU, graphics, shared)
- `tools/` — host-side generation and measurement tooling
- `tests/` — deterministic scenarios and regression tests
- `scripts/` — reproducible build/test entry points
- `assets/` — **original or newly generated** redistributable assets only

This project is independent homebrew research; it is not affiliated with Sega.
