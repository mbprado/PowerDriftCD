# Phase 1B: natural optional-position writer audit — 2026-10-29

**Result — INCONCLUSIVE for natural branch activation; bounded negative finding verified by execution.** The prior [controlled optional-addition test](2026-10-29-optional-position-add-result.md) proved the exercised `$0C08C0`/`$0C08BE` arithmetic after a private state intervention. This audit asked whether ordinary input schedules naturally write a nonzero value to either field. Across the watched windows, no such write occurred. This does not establish that the branch is unused later in the game or on other track states.

## Hypothesis, baseline and method

**Hypothesis:** an ordinary steering response or track update may write `$0C08C0` (state `+$80`) or `$0C08BE` (`+$7E`), enabling the optional addition without intervention. **Expected evidence:** a nonzero MAME write-watch event with CPU, program counter, address, data and frame context. A zero write would identify an initializer but not an active branch producer.

**Baseline:** `experiment/perspective-road` commit `5b1c279`; no renderer or projection-model change. The only source change adds `PDRIFT_DEBUG_WATCH=position_branch_writers` to `tools/phase1b_mame_input.lua`. It arms four-byte write watchpoints at `$0C08BE` in each of `maincpu`, `subx` and `suby`, records a debugger frame marker and clears the watches at callback 1000. Each CPU has a separate program space; the probe covers all three. The watch starts at callback 1 on fresh boot or callback 951 when loading the callback-950 state.

**Verified by execution:** both runs used isolated MAME 0.289 (source `f34f02505e32c1993c6a782b6814232cbfc74e36`; executable SHA-256 `8e4966a8a42e70cba398a8ec62bf3550bef84938bc17946579a69caac11876ba`) on macOS 26.6.2, Darwin x86_64. The Lua probe SHA-256 was `19de4c5fd583c6b19dd0893f0fab3cc5b9d084c06113e879ce2231397abb79bb`. The private ROM manifest SHA-256 was `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. All ROMs, assembled programs, states and raw logs remain under ignored `build/private/`.

For reproduction, run from an empty private directory with `SDL_VIDEODRIVER=dummy PDRIFT_SNAPSHOT_DIR=. PDRIFT_DEBUG_WATCH=position_branch_writers PDRIFT_SEQUENCE_END_FRAME=1000 PDRIFT_STEER_PULSE=<212 or 56>` and the existing deterministic input schedule (`coin60–64,start130–134,pedal240+,steer128`). Use:

```text
/private/tmp/pd-mame0289-render989/mame pdrift -rompath /Users/murilo/repos/PowerDriftCD/build/private/phase1b-roms -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -debug -debugger none -debuglog -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua
```

The fresh-boot run used pulse 212 and no saved state; the second used pulse 56 and `PDRIFT_STATE_LOAD=/Users/murilo/repos/PowerDriftCD/build/private/phase1b-range-state-seed/callback950.sta` (state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`). Capture each run's `debug.log` and stdout as `phase1b-input.log`. The `POSITION_BRANCH_WRITERS_ARMED` and `CLEARED` markers confirm watch coverage; neither run reported a Lua error. `-video none` produced no screenshots, so this is a write-provenance test, not visual evidence.

## Observations

| Run and watched callbacks | Write events | Observed writers and values |
| --- | ---: | --- |
| Fresh boot, pulse 212, callbacks 1–1000 | 10 | Main CPU only. Frame 2: `$039556 → $0C08BE`, `$039548 → $0C08C0`. Frames 3, 11, 14 and 389: `$0331DE` writes each word. Every reported data value is zero. |
| Callback-950 saved state, pulse 56, callbacks 951–1000 | 0 | No write by main CPU, Sub-X or Sub-Y in the watched range. |

**Verified by execution:** private main-CPU image SHA-256 `03143b6e3ba0045109e1745d06e04bda0db638f1cd7fadb1eab0b403fae40618` disassembles around `$039548/$039556` and `$0331DE` as zeroing loops; the watched data are all zero. These PCs identify observed initialization or clearing writes, not a natural positive-value producer. The watchpoint PC is a debugger-reported execution point, and the frame marker preceding an event is its callback context, not a cycle-accurate timestamp.

**Raw evidence:** fresh-boot `build/private/phase1b-position-branch-allcpu-natural212/debug.log` SHA-256 `a29a9a4a306f261fe0d6d599aa5f9582a078f3c013ef7f2bea3dad896146b4db`; stdout SHA-256 `c9b0d635c8e9ceba3dbc0a3fe732382b027b40d89a568fcb3f8d3a01660d000a`. Saved pulse-56 `build/private/phase1b-position-branch-allcpu-saved56/debug.log` SHA-256 `923a4b4aa31301b13ecb5ad16572a390f8d9d6aaa01f22de4c75d4a1264735ad`; stdout SHA-256 `dd5c0fbc387b81bcd853062790a738cf21d95b6e5a40df373e589d954b2761c1`.

## Limit and next test

The fresh watch starts at callback 1, so it does not cover writes before that point. The saved watch starts at 951, leaving the state-load transition to 951 outside that run's watch. Both stop at 1000. Neither schedule reaches all later game or track states. **Unsupported:** a claim that no natural writer exists, that Sub-X/Sub-Y never write these words, or that `$80/$7E` have a settled gameplay meaning. No emulated-cycle cost, original-hardware timing or physical-hardware behavior was measured; physical hardware and BlastEm were **NOT RUN** for this audit.

**Recommended bounded follow-up — hypothesis:** choose a later deterministic gameplay or track-position state where `$80` changes in a normal run, then watch the preceding interval on all CPUs and validate the value's downstream use. If no such state is available, trace the code's branch into `$80/$7E` statically to identify the enabling condition before scheduling another MAME capture. A separate guarded low-`D3` correction test can verify another arithmetic branch, but would not establish natural activation.
