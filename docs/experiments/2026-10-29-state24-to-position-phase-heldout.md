# Phase 1B: modeled `$24` source to position phase — 2026-10-29

## Question and acceptance

**Hypothesis:** the previously validated `$0CEA12/$24` smoother can feed the [fractional phase accumulator](2026-10-28-position-fractional-increment-heldout.md) without observing the intermediate source delta or any subsequent target word. **Baseline:** local `b751a00`, callback-950 private state, isolated MAME 0.289. **Acceptance:** development pulse 204 matches 20 updates; a separate held-out schedule freezes five outputs from PC `$0343C4` inputs and the initial accumulator/phase only, before a target-only MAME run; exact callback markers and values must match.

## Model and temporal boundary

**Verified by execution:** the existing [source model](../../tools/phase1b_state24_source_predict.py) reconstructs the exercised `$8C/$5E` desired-value path and bounded `$0CEA12` updates. The [combined predictor](../../tools/phase1b_state24_fraction_predict.py) uses its predicted source word for each marker, then adds `signed16(source) << 10` to a carried 16-bit `$0CEA14` remainder, reads the high word as the increment, retains the low word, and advances/masks `$0CEA00` before deriving `$0CEA04`. It starts with the **first** old `$0CEA12`, `$0CEA14`, and `$0CEA00` values at PC `$0343C4`; later logged old values are not fed back. The input-only trace still supplies per-update flags, `$8C`, `$8E`, and related branch inputs to the source model. Those earlier game-state inputs remain a boundary of this result.

**Verified by execution, development pulse 204 — PASS:** fresh source-input and target-output runs matched **100/100** fields across 20 odd callback markers 961–999: new source, preclear accumulator sum, increment, phase, and offset. The target run uses the previously checked `$0344A0/$034510/$03454E` breakpoints. No target fields are present in the source-input trace.

## Held-out validation

**Verified by execution:** pulse 172 was inspected as an input-only schedule; its predicted increment stayed `$0004`, and no pulse-172 target run was made. Pulse 196 was then selected and its 20 five-field predictions frozen under SHA-256 `d973ac6789b295f56f0738ee21cb73fe1d47f89909a842e3e5b474c93b9b0aea` **before** target execution. It exercised ten distinct source words `$00E3–$00FE`, with `$0003` increments at markers 991 and 997 and `$0004` at the other 18 markers. Ten of its 20 predicted rows differed from development pulse 204.

**Verified by execution — PASS:** the later pulse-196 output-only run matched **100/100** frozen fields with zero differences. The validator rechecks the frozen input-log checksum and recomputes the prediction before comparing targets. The callback-1020 target screenshot SHA-256 was `b495eddb4a4ebddea93cbe569cf64ccd1a9ed1e4e6c822fb5b5ee3f079fa4f8b`. This is an independent *target observation* for the chosen input schedule; the schedule itself was selected after inspecting input-only predictions, which is recorded above.

**Limits:** the exercised source-model branch is `word8c` at every held-out marker. ROM-table and multiplier branches, negative source values, accumulator overflow and 11-bit phase wrap remain **unsupported**. The meaning of `$0CEA00` as a physical road or camera quantity is **unsupported**. This is a stronger upstream numerical dependency, not a steering-to-camera model: `$8C/$8E` and flags still come from MAME, and no screen pixel or Sega CD five-word camera packet was predicted here. The renderer was unchanged.

**Next hypothesis:** correlate a forward numerical phase sequence with an unoccluded road descriptor/edge using fixed coordinate calibration. First test whether intervening on this phase changes the road path rather than foreground sprites; only then seek a Sega CD packet mapping.

## Reproduction and evidence

**Verified by execution:** macOS 26.6.2 / Darwin 25.6.0 x86_64; Python 3.14.8; isolated MAME 0.289 executable SHA-256 `712f0f9eaf931d6032b20d615f74583d7a418c81763f9b052c7f6c4727450ee9`, pinned source `f34f02505e32c1993c6a782b6814232cbfc74e36`; owner-private 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Upstream tracer SHA-256 `117d831a875043e554e6fe5abfb20cf432f9c8616a728ac189fdddb628cbdc90`; combined predictor SHA-256 `7f85a081fce3a5ee11a0a96e44ce9355375c19317bcaa8e6530d363b7aca1386`. The target tracer is the unchanged [position increment probe](../../tools/phase1b_mame_input.lua) from `b751a00`.

Run the isolated MAME executable from separate empty ignored trial directories with `pdrift -rompath <absolute private ROM directory> -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -debug -debugger none -debuglog -autoboot_script <script>`. For source-input runs, use `SDL_VIDEODRIVER=dummy PDRIFT_UPSTREAM_DIR=. PDRIFT_STATE_LOAD=<callback950.sta> PDRIFT_UPSTREAM_MODE=state24_fraction_inputs PDRIFT_STEER_PULSE=<pulse>` and `tools/phase1b_mame_upstream_probe.lua`; save stdout/stderr to `phase1b-upstream.log`. For target-output runs, use `SDL_VIDEODRIVER=dummy PDRIFT_SNAPSHOT_DIR=. PDRIFT_STATE_LOAD=<callback950.sta> PDRIFT_SEQUENCE_END_FRAME=1000 PDRIFT_DEBUG_WATCH=position_increment PDRIFT_POSITION_INCREMENT_PHASE=output PDRIFT_STEER_PULSE=<pulse>` and `tools/phase1b_mame_input.lua`; save stdout/stderr to `phase1b-input.log`.

```sh
python3 tools/phase1b_state24_fraction_predict.py development build/private/phase1b-combined-dev204-input build/private/phase1b-combined-dev204-output --pulse 204
python3 tools/phase1b_state24_fraction_predict.py predict build/private/phase1b-combined-heldout196-input build/private/phase1b-combined-heldout196-frozen.json --pulse 196
# Execute the pulse-196 target-only MAME run after freezing predictions.
python3 tools/phase1b_state24_fraction_predict.py validate build/private/phase1b-combined-heldout196-frozen.json build/private/phase1b-combined-heldout196-input build/private/phase1b-combined-heldout196-output
```

**Verified by execution:** ignored raw `debug.log` SHA-256: development input `a46a325d41cf3ab1eeecb6f55831eafcab87d0d263d09f696d8ae70c653b095a`, development target `52071d0e28c4aea7959dbcee4ccea0b61d85812b355b7e2e00bbfb56bd101be3`, exploratory pulse-172 input `6f027c5f10d316cc25e30b918ccde00c283eb10841be2955461636cbe4bf7c25`, pulse-196 input `ea23f16705cfdc02d1c3f41884fa3f638155f3a4a0b9e8f9a16de9f76a2acdd2`, pulse-196 target `5602e969dc32c28c6029a87f330949a736105196d00e651462506f2c9f4b411e`. The frozen JSON, logs, saved state and owner ROMs remain ignored/private. This is L1 MAME evidence; a second emulator, BlastEm and physical hardware were **NOT RUN**. No host-speed figure is interpreted as original hardware timing.
