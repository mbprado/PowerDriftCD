# Phase 1B: upstream position-table offset — 2026-10-28

## Question and acceptance

**Hypothesis:** the main CPU's earlier accumulator state predicts the later `$0CEA04` table offset, its selected generated-RAM index, and the ROM coefficient used in the `$0C0856` position adjustment. **Baseline:** `b96594f`, the [previous position chain](2026-10-28-position-operand-coefficient-chain.md), callback-950 private state and MAME 0.289. **Acceptance:** fit the arithmetic on pulse 204; freeze predictions from an input-only, unused pulse 142; compare a subsequent output-only MAME run. No resulting offset, index or coefficient is permitted in the held-out input log.

## Routine and model

**Verified by execution and read-only local disassembly:** the main CPU writes `$0CEA04` at `$034548` (post-write PC `$03454E`). At `$03451C`, it adds `D7` to the old `$0CEA00` word. The following instructions mask the sum to 11 bits, write `$0CEA02`, then double it into `$0CEA04`. `$034AF8–$034B02` uses this byte offset into the generated `$1FB000` RAM table. `$034C02` doubles that table word to index the private main-CPU ROM coefficient table at `$000EF6`. The independently written [predictor](../../tools/phase1b_position_offset_predict.py) implements:

```text
phase       = (old_CEA00 + D7) & 0x07FF
offset      = 2 * phase
index       = big_endian_word(generated_RAM_table + offset)
coefficient = big_endian_word(main_CPU_ROM + 0x0EF6 + 2 * index)
```

**Verified by execution, development pulse 204:** 20/20 updates matched all four fields. The first observed input was old `$0176`, `D7=$0004`; the predicted phase `$017A`, offset `$02F4`, table index `$0025`, and coefficient `$0073` matched the trace. The model uses the private, previously captured 4096-byte generated table SHA-256 `58026dc7abea35d5336cdbd17dab0dc41714eafb9c8f64e2e9d49643b979f679` and assembled main-CPU image SHA-256 `03143b6e3ba0045109e1745d06e04bda0db638f1cd7fadb1eab0b403fae40618`. Neither file is tracked.

## Held-out result and limits

**Verified by execution — PASS:** pulse 142 input-only and output-only runs were separate. The ignored prediction file was frozen first, SHA-256 `f91ff81152028fe0774514ca8c40b62beb0df8b7a94cad5ba46c93fcca49f414`. All **80/80** field predictions matched the later output-only trace: 20 each of phase, offset, index, and coefficient. Six of 20 input rows differed from development pulse 204. The index selected either `$0025` or `$0026`, and the corresponding coefficient was `$0073` or `$0076`. Both callback-1020 images were byte-identical, SHA-256 `55629a5d89c91a0e0a79bfef7764c91c2aebe5e4248a40222c82f420d3123f98`.

**Verified by execution, exercised-path limit:** `D7` was `$0004` for all 20 held-out updates. This validates the update order and table lookups over two coefficient values, but not other increments or the 11-bit wrap. The source of `D7` is the preceding `$034500–$03450A` shift/long accumulator operation; its earlier game-state producer was not modeled here. The old `$0CEA00` word is captured before this update. The generated `$1FB000` table was captured from this private MAME boot and independently checksum-guarded, but its generation from original arcade inputs remains a separate dependency. This result predicts one upstream transformation dependency; it does **not** predict a complete camera trajectory from steering or validate a Sega CD command packet.

**Hypothesis for the next bounded test:** trace the source of the shift input at `$034500` and reproduce `D7` from a still-earlier accumulator/speed state, then test a window with nonconstant increments or wrap. The separate pre-add `D0` producer at `$034EF4–$034F60` also remains open. Do not change the five-word Sega CD interface on this evidence alone.

## Reproduction and private evidence

**Verified by execution:** macOS 26.6.2 / Darwin 25.6.0 x86_64; Python 3.14.8; isolated MAME 0.289 executable SHA-256 `712f0f9eaf931d6032b20d615f74583d7a418c81763f9b052c7f6c4727450ee9`, pinned source `f34f02505e32c1993c6a782b6814232cbfc74e36`; owner-private 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Tracer SHA-256 `23838086e842874490db3bab03f58c1862a83957cbcb2c51c4158a7adff51c0d`; predictor SHA-256 `1a396b0742f8af318fe193ee939d64bee0e069befda9f61c90328e49a61d093f`. These are emulator observations, not original hardware timing or physical arcade-hardware validation.

Run the isolated MAME executable from each empty ignored trial directory with `pdrift -rompath <absolute private ROM directory> -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -debug -debugger none -debuglog -autoboot_script <absolute tools/phase1b_mame_input.lua>`. Set `SDL_VIDEODRIVER=dummy`, `PDRIFT_SNAPSHOT_DIR=.`, `PDRIFT_STATE_LOAD=<absolute callback950.sta>`, `PDRIFT_SEQUENCE_END_FRAME=1000`, and `PDRIFT_DEBUG_WATCH=position_offset`. Capture standard output in `phase1b-input.log`. Use `PDRIFT_STEER_PULSE=204 PDRIFT_POSITION_OFFSET_PHASE=both` for development, then `PDRIFT_STEER_PULSE=142` with `input` and subsequently `output` phases in distinct directories. Run:

```sh
python3 tools/phase1b_position_offset_predict.py development build/private/phase1b-position-offset-dev204 build/private/phase1b-upstream-inputs/table-boot/table-0950-1FB000.bin build/private/phase1b-code-pilot/pdrift-maincpu.bin --pulse 204
python3 tools/phase1b_position_offset_predict.py predict build/private/phase1b-position-offset-heldout142-input build/private/phase1b-upstream-inputs/table-boot/table-0950-1FB000.bin build/private/phase1b-code-pilot/pdrift-maincpu.bin build/private/phase1b-position-offset-heldout142-frozen.json --pulse 142
# Run the output-only MAME trial after freezing predictions.
python3 tools/phase1b_position_offset_predict.py validate build/private/phase1b-position-offset-heldout142-frozen.json build/private/phase1b-position-offset-heldout142-output
```

**Verified by execution:** ignored raw logs: `build/private/phase1b-position-offset-dev204/debug.log` SHA-256 `3940037a148ca804ac2230f71e27e8d2d7659489841b89c1ab9e720f1a3edda6`, held-out input `c88f786b92993623b3ad967c9ba60402120d39baf150fbcf87a7ce46a604eeaa`, held-out output `1e11c8fe67d0925d7eee8db403693fd029f53cb0b35303920998efb7f5f30ee4`. The ignored private disassembly is `build/private/phase1b-cea04-disasm204/main-cea04-writer.asm`; it contains commercial program disassembly and must remain untracked. BlastEm, a second arcade emulator and physical hardware were **NOT RUN** for this investigation.
