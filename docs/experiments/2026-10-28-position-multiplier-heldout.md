# Phase 1B: held-out position adjustment from multiplier inputs — 2026-10-28

## Hypothesis and frozen gate

**Hypothesis:** the `$034C34` main-CPU adjustment that feeds the road-like record's later `$0C009C` translation equals the prior `$0C0856` base plus a signed 16×16 hardware-multiplier product shifted arithmetically right nine, wrapped to 16 bits. **Baseline:** source revision `f70107a`, the [native-layer and translation trace](2026-10-28-roadslot-native-layer-and-translation.md), callback-950 owner-private saved state, and pulse 204 at callback 960. **Acceptance:** reproduce 20 development writes, then freeze 20 predictions from a previously unused input-only steering schedule *before* collecting its output-only MAME trace. A held-out schedule must change the arithmetic inputs and outputs; an equivalent schedule is only a control.

## Algorithm and result

**Documented only by the pinned MAME 315-5248 implementation:** the mapped `$080000` multiplier treats its two 16-bit registers as signed operands and exposes their 32-bit product at offsets `$4/$6`. **Verified by read-only local disassembly and execution:** the arcade routine writes a state operand and a coefficient to those registers, reads the product at PC `$034C1C`, applies `ASR.L #9` at `$034C2C`, and adds its low word to `$0C0856` at `$034C34`. A focused debugger breakpoint at PC `$034C1C` captured the *pre-result* base and multiplier registers; a separate breakpoint at `$034C38` captured the adjusted word after the add. The independently written [predictor](../../tools/phase1b_position_math_predict.py) calculates:

`adjusted = (base + ((signed16(operand) * signed16(coefficient)) >> 9)) & 0xFFFF`

**Verified by execution, development pulse 204:** 20/20 ordered updates matched, including 18 negative operands. The first input was base `$17D3`, operand `$00A7`, coefficient `$0073`; its product shift is `$0025`, yielding `$17F8`, consistent with the prior translation trace. The focused instrumentation left the callback-1020 screenshot byte-identical to that prior pulse-204 trace.

**Verified by execution, rejected holdout control:** pulse 206 was run input-only, its 20 predictions were frozen, and a fresh output-only MAME run matched 20/20. However, all 20 input rows were identical to pulse 204 and the callback-1020 image was identical. Thus pulse 206 provides a deterministic control, **not** an independent arithmetic validation.

**Verified by execution, meaningful held-out pulse 160 — PASS:** its input-only run differed from pulse 204 on **20/20 input rows**. The output trial directory was empty when the 20 predictions were frozen under SHA-256 `b84362c7d89c15e0368db87ab62274e184d95b5094c0a8d295378c639ecace93`. Only then was a fresh output-only MAME run executed. Its 20/20 adjusted `$0C0856` writes matched the frozen values exactly, with **20/20 outputs distinct** from pulse 204. The held-out inputs include 15 negative operands and two observed positive coefficients, `$0073/$0076`. The input-only and output-only callback-1020 screenshots were byte-identical, SHA-256 `7ef858d27d5d1c6825c55f5d70a736a2fb60fb1bf9e226f4e973097e8e6356b6`. The private result JSON records zero errors and SHA-256 `7d6fde5909b52c0c6b51f376ede8a4d197068d911123479f7b7e5bcabf00819d`.

**Scope:** this predicts one upstream transformation field from its earlier base and multiplier operands without reading the resulting field first. It does **not** predict the multiplier operand, coefficient index, or base table selection from steering alone. It does not establish physical camera units or road curvature, nor a calibrated Sega CD five-word packet. The previous synthetic 128×64/30 Hz BlastEm renderer remains unchanged.

## Reproduction and evidence

**Verified by execution:** macOS 26.6.2 / Darwin 25.6.0 x86_64, Python 3.14.8, isolated MAME 0.289 executable SHA-256 `712f0f9eaf931d6032b20d615f74583d7a418c81763f9b052c7f6c4727450ee9`, pinned source `f34f02505e32c1993c6a782b6814232cbfc74e36`; owner-private 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The capture script SHA-256 was `8f6682baa52da0cff70f2bec6ce19ca6f8f1195dc91834497b302092b037e86c`; predictor SHA-256 was `63b575c9213d556547ac7aa6ddc3a94ecb765b160c6b6515e9aa229142f2c6b1`. There was no Sega CD image or original-hardware test.

Run the isolated MAME binary from each new empty ignored trial directory with `pdrift -rompath <absolute private ROM directory> -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -debug -debugger none -debuglog -autoboot_script <absolute tools/phase1b_mame_input.lua>`. Set `SDL_VIDEODRIVER=dummy`, `PDRIFT_SNAPSHOT_DIR=.`, `PDRIFT_STATE_LOAD=<absolute callback950.sta>`, `PDRIFT_SEQUENCE_END_FRAME=1000`, `PDRIFT_DEBUG_WATCH=position_math`, `PDRIFT_STEER_PULSE=204` for development or `160` for holdout, and `PDRIFT_POSITION_MATH_PHASE=both` for development, `input` for the first holdout run, `output` for the later target run. The script prints callback markers into `debug.log` and refuses to mix target outputs into the input-only trace. Then run:

```sh
python3 tools/phase1b_position_math_predict.py development build/private/phase1b-position-math-dev204 --pulse 204
python3 tools/phase1b_position_math_predict.py predict build/private/phase1b-position-math-heldout160-input build/private/phase1b-position-math-heldout160-frozen.json --pulse 160
# Execute the output-only MAME run only after the frozen file is written.
python3 tools/phase1b_position_math_predict.py validate build/private/phase1b-position-math-heldout160-frozen.json build/private/phase1b-position-math-heldout160-output
```

The private directories are `build/private/phase1b-position-math-dev204`, `phase1b-position-math-heldout206-{input,output}`, and `phase1b-position-math-heldout160-{input,output}`. The pulse-204 development `debug.log` SHA-256 is `28fb505b0f137026d848c94cf1c95a5c91ef8d618c7e62fdd74ecdd6f9c89a51`; pulse-160 input-only log is `4c0dc9cb2f08dfba1ec07d84f18d455d33a58ea3c6bf0c5c624c44b070516b4d`, and output-only log is `7e50a7269d936376beadd33ee8d978fe659e63499b8513dc96f9b4ee4f15c154`. Raw logs, saved states and ROMs remain private under ignored `build/private/`.

**Next hypothesis:** trace the earlier producer of the multiplier operand and coefficient/table index, then freeze a short prediction from steering and prior state through adjusted `$0C0856` and `$0C009C`. Validate on a distinct input schedule before trying an unoccluded road-pixel calibration. This result does not justify changing the Sega CD camera interface. No second arcade emulator, BlastEm or physical hardware run was needed for this bounded MAME arithmetic test.

**Subsequent result (2026-10-28; verified by execution):** the [bounded operand/coefficient chain](2026-10-28-position-operand-coefficient-chain.md) linked the operand writer at `$034FD6`, a RAM-table index through `$0CEA04`, and the ROM coefficient lookup to the adjusted position. A distinct held-out pulse matched 60/60 fields, while the optional operand branches remained unexercised.
