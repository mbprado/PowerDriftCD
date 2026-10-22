# Phase 1B: bounded shared-X projection intervention — 2026-10-22

**Question / hypothesis:** does one already traced shared transform input have a predictable, depth-dependent effect on arcade projection words? **Baseline:** centered steering in the owner-local callback-950 state, with unchanged ROM geometry and the validated projection arithmetic. **Method:** temporarily add `0`, `$10`, `$20`, or `$100` to `(A4+$1C)` only while the main CPU projects the three records at depths `$3600`, `$3800`, and `$3A00`; restore it at routine exit. **Expected evidence:** unchanged sham, debugger-confirmed restoration, differences limited to those records, exact independent arithmetic predictions, and a repeated run. **Result — verified by execution in MAME:** all controls passed. The `$100` intervention shifted projected X by −5, −3, and −2 at the three successive depths. This establishes a local transform sensitivity, not a calibrated camera axis or a fitted Sega CD control.

## Environment and reproduction

**Verified by execution:** source baseline `a3fa2d3` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing capture-only patch. The owner-local 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The optional Lua probe SHA-256 is `99f8696c43798720e3a4b4d20b059cb7390b763deb807c900e2bf0c800406a77`; analyzer SHA-256 `68f50a51c81f03c9478ee5fc83ad4d007aaa68ca7c40b1c3de12303a08f4c5ee`. All original ROMs, state, logs, and derived coordinate records remain ignored in `build/private/`.

**Verified by execution:** from a fresh ignored directory, the following reproduces one intervention; set the final environment variable to `0`, `10`, `20`, or `100` (hexadecimal) and use a distinct output directory for each run. Run `$20` twice as a repeat. The Lua probe arms at callback 960 and disarms at 967; the guarded `$0C9800` list pass projects the three selected records once each. The intervention affects the projection that appears in callback-964/965 samples.

```sh
mkdir -p build/private/phase1b-global-x-plus256
cd build/private/phase1b-global-x-plus256
env SDL_VIDEODRIVER=dummy PDRIFT_SNAPSHOT_DIR=. PDRIFT_GEOMETRY_SAMPLE_DIR=. PDRIFT_STATE_LOAD=/absolute/private/callback950.sta PDRIFT_DEBUG_WATCH=shared PDRIFT_SHARED_WATCH_ADDR=0C1C90 PDRIFT_PROJECTION_GLOBAL_X_DELTA=100 PDRIFT_SEQUENCE_END_FRAME=970 /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -debug -debugger none -debuglog -autoboot_script /absolute/repo/tools/phase1b_mame_input.lua
```

Analyze all five private runs from the repository root:

```sh
python3 tools/phase1b_global_x_intervention.py build/private
python3 -m py_compile tools/phase1b_global_x_intervention.py tools/phase1b_projection_replay.py
```

The resulting ignored `build/private/phase1b-global-x-results.json` has SHA-256 `724d877327cb656f0d5fbeb9632f56a604d99d012c70ce9c294c9ce48677c3ea`. It records each raw CSV/debug-log checksum and all observed/predicted pairs. The new probe only adds conditional debugger breakpoints to the project Lua runner; it does not edit upstream MAME or Sega CD renderer code.

## Controlled result

**Verified by execution:** the `0` sham CSV matched all 132 rows of the prior centered `phase1b-depth-sequence-center` capture over callbacks 960–970. Each of the five runs logged exactly three guarded entry writes and three matching restores. The `$20` repeat produced a byte-identical geometry CSV. Across all runs, differences from sham were confined to output X/Y words of the three target rows at callbacks 964/965. Source tuples, shared block at sampled callbacks, other object rows, and subsequent samples matched sham. The [fixed-point replay](../../tools/phase1b_projection_replay.py) predicted all 15 targeted X/Y pairs exactly using the baseline pre-projection row, the same post-projection horizontal offset, and only the controlled `$1C` change.

| Depth | Sham projected X/Y | `+$10` X/Y | `+$20` X/Y | `+$100` X/Y |
| --- | ---: | ---: | ---: | ---: |
| `$3600` | 12 / 26 | 11 / 25 | 11 / 26 | 7 / 25 |
| `$3800` | 9 / 23 | 9 / 24 | 9 / 24 | 6 / 24 |
| `$3A00` | 7 / 24 | 7 / 23 | 7 / 23 | 5 / 23 |

**Inference from verified execution:** this shared word contributes to the main CPU's depth-dependent projection, and its response is quantized by fixed-point arithmetic. `$100` raw units are an experimental register increment, **not** a known world distance or camera displacement. The different X/Y rounding at small increments is expected from the reconstructed signed shifts and division; it should not be smoothed into a continuous camera scale. The arithmetic was independently checked against ordinary MAME output in the [projection replay](2026-10-21-arcade-geometry-projection-sequence.md), and this intervention now checks it against a changed input.

**Unsupported:** the shared block's official field name, physical camera coordinates, road centerline identity, vertical/horizontal units, and any claim that the current Sega CD five-word controls reproduce these arcade samples. This experiment did not transfer the altered object through the sprite pipeline or measure frame timing. No second arcade emulator or physical hardware was run.

**Next bounded test — hypothesis:** compare the observed multi-depth arcade X/Y profiles at *matched lookup positions* against a parameterized offline adapter to the existing five-word Sega CD camera command. Fit on some epochs and assess held-out epochs, reporting each axis's residual separately. If a specific profile cannot be represented, document that mismatch before changing the interface. Keep synthetic Sega CD rendering and owner-local arcade captures separate.
