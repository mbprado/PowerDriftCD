# Phase 1B: fractional position increment — 2026-10-28

## Question and acceptance

**Hypothesis:** the earlier `$0CEA12` source state and long `$0CEA14` remainder predict the changing increment that advances `$0CEA00`, then the `$0CEA02/$0CEA04` phase and generated-RAM lookup offset. **Baseline:** `7a90073`, the [prior offset model](2026-10-28-position-table-offset-heldout.md), callback-950 private state and isolated MAME 0.289. **Acceptance:** match 20 development updates on pulse 204; freeze five fields from a fresh pulse-192 input-only run; compare a later output-only run. The input-only trace must contain no resulting source, increment, sum, phase or offset.

## Executed path and arithmetic

**Verified by execution and read-only local disassembly:** the main CPU adds `D0` to `$0CEA12` at PC `$034490`, then sign-extends that resulting word at `$0344FE`, shifts it left ten bits at `$034502`, and adds it to the long `$0CEA14` at `$034504`. It reads the **high word** as `D7` at `$03450A` and clears that high word at `$034510`, retaining the low 16-bit remainder for the next update. The earlier [offset model](2026-10-28-position-table-offset-heldout.md) then advances `$0CEA00` by `D7` and doubles the masked phase into `$0CEA04`. The [new predictor](../../tools/phase1b_position_increment_predict.py) uses 16/32-bit wrapping:

```text
source    = (old_CEA12 + source_delta_D0) & 0xFFFF
sum32     = (old_CEA14 + (signed16(source) << 10)) & 0xFFFFFFFF
increment = sum32 >> 16
phase     = (old_CEA00 + increment) & 0x07FF
offset    = 2 * phase
```

The `old_CEA14` input in this tested path had a zero high word because the previous update cleared it. `sum32` is captured **before** that clear. At the first pulse-204 marker, source `$00FE`, old remainder `$0000F800`, and old phase `$0176` predict sum `$0004F000`, increment `$0004`, phase `$017A` and offset `$02F4`; the output trace agrees.

## Results and boundaries

**Verified by execution — PASS:** 20/20 development updates matched all five fields. The pulse-204 increment was `$0003` at markers 989, 995 and 999, and `$0004` otherwise. The pulse-192 input-only run then froze 20 predictions, SHA-256 `4324221954191cb7af1a8144db47bc84d50e78f24d183f33fe9feb02eed2429f`, before the output-only run. All **100/100** frozen fields matched: source, preclear sum, increment, phase, offset. Pulse 192 exercised nine source values `$00E6–$00FE`, source deltas `$0000/$FFFD`, 18 increments `$0004` and two `$0003`. Ten of its 20 input rows differed from pulse 204. Input-only and output-only callback-1020 images were byte-identical, SHA-256 `a10afa71a289ed3c8695019726b4286e278a0e593205fa0451afd3562b3ca7ee`.

**Verified by execution, bounded meaning:** this validates the exercised fixed-point carry, update order and 11-bit phase mask over the observed values. The source delta `D0` at `$034490`, old `$0CEA12`, old `$0CEA14`, and old `$0CEA00` are captured **before** their targets; they are not predicted from steering here. The earlier [`$24` source study](2026-10-27-state24-source.md) models part of the preceding smoother, but this experiment does not merge the two models or claim a complete camera trajectory. Negative source values, 32-bit overflow and 11-bit phase wrap were not exercised. The physical meaning of this phase and its relationship to the Sega CD five-word command remain **unsupported**.

**Hypothesis for the next bounded test:** link the already modeled `$24/$0CEA12` source calculation to this fractional accumulator using one held-out continuous state sequence, then test whether that stronger chain predicts an unoccluded road boundary under explicit coordinate calibration. Preserve the existing renderer interface until a mismatch is demonstrated.

## Reproduction and private evidence

**Verified by execution:** macOS 26.6.2 / Darwin 25.6.0 x86_64; Python 3.14.8; isolated MAME 0.289 executable SHA-256 `712f0f9eaf931d6032b20d615f74583d7a418c81763f9b052c7f6c4727450ee9`, pinned source `f34f02505e32c1993c6a782b6814232cbfc74e36`; owner-private 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Lua tracer SHA-256 `1cfa5eb9b7cf4d05bd8854a2f8883b970404d284d2d25db6a6ee7ca77504bd31`; predictor SHA-256 `08935fdfdfbd38383144acc415b6a7f9d1cf4c67092e4d2899b768b4ac10ee52`.

From each empty ignored trial directory, run the isolated MAME executable with `pdrift -rompath <absolute private ROM directory> -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -debug -debugger none -debuglog -autoboot_script <absolute tools/phase1b_mame_input.lua>`. Set `SDL_VIDEODRIVER=dummy`, `PDRIFT_SNAPSHOT_DIR=.`, `PDRIFT_STATE_LOAD=<absolute callback950.sta>`, `PDRIFT_SEQUENCE_END_FRAME=1000`, and `PDRIFT_DEBUG_WATCH=position_increment`; capture stdout/stderr in `phase1b-input.log`. Use pulse 204 and `PDRIFT_POSITION_INCREMENT_PHASE=both` for development. Use pulse 192 and `input` followed by `output` in distinct directories for held-out validation.

```sh
python3 tools/phase1b_position_increment_predict.py development build/private/phase1b-fraction-dev204-final --pulse 204
python3 tools/phase1b_position_increment_predict.py predict build/private/phase1b-fraction-heldout192-input-final build/private/phase1b-fraction-heldout192-frozen-final.json --pulse 192
# Execute the output-only MAME run after freezing predictions.
python3 tools/phase1b_position_increment_predict.py validate build/private/phase1b-fraction-heldout192-frozen-final.json build/private/phase1b-fraction-heldout192-output-final
```

**Verified by execution:** ignored raw `debug.log` SHA-256: development `bfd489114413ddea6bd1b4b756c9e1c47a8a28c1dcdaa9550151c4b12ad47aa9`, held-out input `a8e6ce06cf2b4784b67086a87d3475ac30505e136083d0fbc093de785af8be87`, held-out output `ce3f70148f63eeb29b8d008ef4d92ee311e70b4468b8940e20116fcc8fe956de`. The read-only program disassembly remains private at `build/private/phase1b-position-increment-dev204/main-cea14-input.asm`. The ignored JSON and all private ROM/state data remain outside Git. This is L1 MAME evidence; BlastEm, another arcade emulator and physical hardware were **NOT RUN**. No MAME host wall-clock speed is treated as original hardware timing.
