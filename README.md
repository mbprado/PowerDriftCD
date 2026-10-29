# Power Drift CD

**Mission:** develop the most arcade-faithful Power Drift conversion achievable on an **unmodified Sega Mega Drive/Genesis + Sega CD/Mega CD**, using modern engineering, rigorous measurement, and offline precomputation.

**Status:** [Phase 1 graphics characterization](docs/experiments/graphics-characterization.md) verified original graphics ASIC transforms, Genesis VDP display, and small deterministic 30/60 Hz pipelines in BlastEm after the [Phase 0 review](docs/experiments/2026-10-18-phase-0-review.md). An initial [64×64 perspective-road prototype](docs/experiments/2026-10-20-perspective-road-prototype.md) runs at 30 Hz in BlastEm with synthetic curvature, elevation and banking cues. [Runtime trace construction](docs/experiments/2026-10-20-runtime-road-traces.md), a [phase-indexed camera](docs/experiments/2026-10-20-phase-indexed-road-camera.md), [independently evolving camera controls](docs/experiments/2026-10-20-independent-road-camera-controls.md), and a [five-word live camera-command interface](docs/experiments/2026-10-20-live-road-camera-commands.md) each sustained 30 Hz in three U.S. Model 2 BlastEm runs. A [128×64 live-command stress test](docs/experiments/2026-10-20-wide-live-road-pipeline.md) also sustained 30 Hz after correcting a VBlank wait error; it is a synthetic scene with no scenery or game logic. The test packets are generated offline; a gameplay camera producer, original-only boot and physical-hardware compatibility remain open. U.S. Genesis/Sega CD (NTSC-U) is the development baseline; there is no running port or measured hardware-performance claim.

**Phase 1B research status — verified by execution in MAME 0.289:** the [code-led dependency map](docs/experiments/phase1b-camera-dependency-map.md) links a steering byte to `$8A` and models the exercised `$24 → $86/$88/$7A/$7C` chain. Frozen pulse-204 predictions matched all four downstream words at 20/20 updates each, including changing `$7A` and nonzero `$7C`. A [same-schedule native-bitmap test](docs/experiments/2026-10-28-screen968-page-c-source.md) traced ten sampled screen-968 edge pixels to Y-sprite descriptor `$C630`; an [adjacent update](docs/experiments/2026-10-28-screen967-adjacent-source.md) traced six sampled screen-967 pixels to corresponding `$E630`. Both exact-slot results were repeated in three fresh MAME runs. A [projection intervention](docs/experiments/2026-10-28-pulse204-road-record-projection.md) linked one main-CPU projected object through a shared list to both descriptors and the tested left-edge pixels. A [native-layer follow-up](docs/experiments/2026-10-28-roadslot-native-layer-and-translation.md) found the changed right-side samples covered by a 16B sprite and traced the selected translation back to an adjusted state word. A [held-out arithmetic test](docs/experiments/2026-10-28-position-multiplier-heldout.md) predicted 20/20 adjusted state words from captured base and multiplier operands; a [further chain test](docs/experiments/2026-10-28-position-operand-coefficient-chain.md) predicted operand, ROM coefficient and adjusted word on a distinct schedule from earlier pre-add state, table index and base. A [recurrent position test](docs/experiments/2026-10-29-position-carry-heldout-result.md) carried the operand through 20 updates and four negative clamps, while [controlled optional-addition](docs/experiments/2026-10-29-optional-position-add-result.md) and [low-`D3` correction](docs/experiments/2026-10-29-low-d3-correction-result.md) tests validated one event each. The active timer and natural sources of `$80/$7E` and nonzero low `D3` remain open. A separate [controlled `$7A` perturbation](docs/experiments/2026-10-28-state7a-foreground-sprite-chain.md) reached a delayed foreground-car sprite, so that particular response cannot calibrate the road camera. A prospective five-word Sega CD packet mapping remains unresolved. Several track and branch inputs still come from MAME; this is **not** a complete steering-to-camera model or a validated renderer handoff. Ghidra/REA and physical arcade hardware remain untested for this result.

**Verified by execution, earlier Phase 1B gate:** [two frozen scalar-to-road-record predictions](docs/experiments/2026-10-29-scalar-to-road-record-result.md) failed in three target runs each. The carried scalar reached the expected translation word, but a later projected object update was skipped when its signed divisor was nonpositive. The main-CPU shared-list record also held two distinct timed coordinate pairs in the tested window. A complete arcade-to-Sega CD camera handoff remains **unsupported**; the guard follow-up below tests the immediate projection decision.

**Verified by execution, projection and list follow-ups:** a [held-out pulse-56 test](docs/experiments/2026-10-29-projection-divisor-guard-result.md) matched 20/20 raw divisors and 20/20 accept/skip decisions in each of three MAME runs. It corrected the replay's guard order: the arcade checks the signed divisor before adding `$0080`. A separate [held-out pulse-72 test](docs/experiments/2026-10-29-stateful-projection-copy-result.md) matched 196/196 object-coordinate, copy-decision and current/prior shared-list-pair fields in each of three runs, including three skipped updates that retained the previous coordinates. A [held-out pulse-116 test](docs/experiments/2026-10-29-projection-slot-selection-result.md) then matched 84/84 local copy-slot/address fields in each of three runs from pre-copy count/base inputs. The earlier road-record failures still stand. Predicting the count and active buffer from earlier object/frame state, and completing an earlier-state-to-road-record model, remain open.

**Verified by execution, cross-CPU count boundary:** a [held-out pulse-124 test](docs/experiments/2026-10-29-shared-list-count-flow-result.md) predicted the target object's entry count `$0027` from the earlier reset and 39 main/Sub-Y writes in three fresh MAME runs. The count was `$0028` by the later pre-lock/copy stage, so entry count cannot be used directly as the list slot. Sub-Y interleaving and buffer selection still require a timed producer model.

**Verified by execution, same-run lock order:** a [three-run pulse-124 audit](docs/experiments/2026-10-29-same-run-list-lock-result.md) observed Sub-Y acquire the shared lock and insert the `$0028` record between the target object's entry and main-CPU lock acquisition. Main copied at `$0028`; a predictive rule for when this interleaving happens on other schedules remains open.

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
0. Toolchain + debugger + emulator evaluation (limited GO; original-only boot remains open)
1. **Parallel foundations:** **1A — Sega CD hardware characterization** (ASIC/VDP/Word RAM, synthetic benchmarking) and **1B — arcade reference feasibility** (MAME Y-Board runtime traces, REA/Ghidra analysis, sprite/palette decoding). Phase 1B starts early and must not interrupt ongoing hardware experiments.
2. Banking/elevation **road and camera renderer** — preserve the working synthetic 64×64 and 128×64/30 Hz prototypes; use a verified real arcade track/camera sample when Phase 1B provides one.
3. Sprite/object renderer — use arcade sprite/palette findings to inform scalable scenery and vehicle assets within VDP limits.
4. Combined renderer and profiling — integrate road, camera, objects and timing under load.
5. Arcade **mechanics and content integration** — handling, collisions, opponents, track progression and gameplay adaptation informed by the earlier arcade research (not the first reverse-engineering effort).
6. Playable racing demonstration.
7. Complete game, real-hardware validation and release.

**Phase 1B research order:** (1) confirm macOS/Linux REA/Ghidra and MAME tooling with locally held legal ROMs; (2) identify one reproducible arcade track section and record camera/track behavior through MAME; (3) correlate dynamic observations with code/data using REA/Ghidra; (4) catalog graphics/palette formats via suitable Y-Board viewers for Phase 3. A **single independently reproducible track/camera sample** is the first useful handoff to Phase 2, not a requirement to reverse-engineer the entire game. The current Phase 2 *synthetic* work can continue in parallel.

**Scope boundary:** Phase 1B outputs are evidence, annotations, original tools and independently authored descriptions; do not commit proprietary arcade ROMs or extracted commercial assets. Keep raw traces/derived assets private pending rights review. The original-only Sega CD disc boot and stock-hardware performance remain separate unresolved gates.

## Repository layout
- `docs/` — design decisions, experiments, hardware notes
- `src/` — eventual console engine (main CPU, sub CPU, graphics, shared)
- `tools/` — host-side generation and measurement tooling
- `tests/` — deterministic scenarios and regression tests
- `scripts/` — reproducible build/test entry points
- `assets/` — **original or newly generated** redistributable assets only

This project is independent homebrew research; it is not affiliated with Sega.
