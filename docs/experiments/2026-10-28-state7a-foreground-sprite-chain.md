# Phase 1B: `$7A` to foreground sprite, not road — 2026-10-28

## Question and bounded test

**Hypothesis:** the delayed pulse-204 `$7A` perturbation identified in the [visual-lag gate](2026-10-28-state7a-visual-lag-gate.md) reaches the changed Y-sprite descriptors through a specific main-CPU field, shared-list copy and Sub-CPU X writer. **Baseline:** local `af972a2`; same owner-private callback-950 state, pulse 204, isolated MAME 0.289 and `+16` at Lua callback 966. **Expected evidence:** locate the first differing arithmetic input and writer, match the transferred word at each stage, then isolate the changed visible object with a one-slot source hide. A road-camera conclusion requires the changed object to be a road feature.

**Method — verified by execution:** reuse the existing targeted MAME watch modes. Compare unmodified and `+16` replays at the main `$0C0840` field producer, the 16-byte shared-list slot `$0C9F50`, Sub-CPU X's list load at `$00DD64/$00DD6A`, and Y-sprite descriptor `$C6B0`. Private local disassembly was checked against the watched PCs; it was not committed. Exact-slot hides at callback 970 then tested the active page on screens 971 and 972. All ROMs, states, screenshots, list dumps and raw disassembly stayed ignored under `build/private/`.

## Ordered arithmetic and transfer

**Verified by execution and the private 68000 instruction sequence:** at the affected update, old `$7A` is `$FFFE` (−2) in baseline and `$000E` (+14) after intervention. The frozen baseline prediction gives carried `$7C=7` and negative `$88`; the paired trace confirms the same `$7C` and subsequent state path. At main PC `$034DDA–$034E20`, the signed half of `$7C` is negated for the `$88` sign; subtracting old `$7A` yields a step of −1 versus −17. Neither reaches the ±32 clamp. Adding that step to old `$7A` produces the **same** new `$7A=$FFFD` (−3) in both runs, but the step also contributes to field `$0C0840+$84`, giving `$FFE4` (−28) versus `$FFD4` (−44). A watch observed that field's differing write at `$034E20` (watch log PC `$034E24`). This explains why comparing only subsequent `$7A` words would miss the intervention's effect. The exercised branch is verified; other signs, clamps and branches remain **documented only** from instructions.

**Verified by execution:** at `$034B2A–$034BA0`, all other watched lookup inputs match. Subtracting `$84`, masking with `$03F0` and shifting right three selects table index 2 in baseline versus 4 in the intervention. The main-CPU table read writes `$0C084C=$0FD8` versus `$0FF6` at `$034BA0` (watch log PC `$034BA6`). The table's physical meaning is **unsupported**; this is a discrete-index change, not a measured camera-angle unit.

**Verified by execution:** main CPU `$037630–$037636` copies the 16-byte `$0C0840` record into shared-list slot `$0C9F50`. The only changed byte positions in this captured slot at callbacks 968–971 are in its final longword: `$0FD80080→$0FF60080`. The targeted writer watch attributes this record copy to the main CPU. Sub-CPU X `$00DD6A` then reads that exact longword for output slot `$18C6B0`; its sprite writer at `$00E0A6–$00E0E0` changes descriptor word `$C6B6` from `$CA5A` to `$CBEF`, among the twelve changed source bytes already reported. The corresponding page-E slot also changes. This is a measured state → list → descriptor chain. The earlier producer-to-display callback offsets remain observational, not original-hardware timing measurements.

| Stage | Baseline | `+16` intervention |
| --- | ---: | ---: |
| Old `$7A` at affected update | `$FFFE` | `$000E` |
| New `$7A` | `$FFFD` | `$FFFD` |
| Intermediate `$84` | `$FFE4` | `$FFD4` |
| `$034BA0` lookup index | 2 | 4 |
| `$0C084C` and list final-word high half | `$0FD8` | `$0FF6` |
| Sub-CPU X list final longword | `$0FD80080` | `$0FF60080` |
| `$C6B6` descriptor word | `$CA5A` | `$CBEF` |

## Visible object gate

**Verified by execution in MAME:** hiding just `$E6B0` at callback 970 changed **2,521** pixels on screen 971 and removed the blue foreground car body in the private screenshot. The same intervention produced byte-identical screen-971 images in **three fresh runs**. Hiding `$C6B0` instead changed **2,519** pixels on screen 972 and none on 971, establishing the alternating page for this sampled object. Hiding `$E6C0` changed another **299** pixels on screen 971. All hides changed exactly their declared descriptor hide byte(s), and prior screens through 970 remained identical.

**Verified by execution:** a paired hide of `$E6B0/$E6C0` in *both* the baseline and `+16` source snapshots made their screen-971 images byte identical, SHA-256 `9100ff5b5795b8d4cd424bad4fbfcd88487a46838a469da7566b1e27d73ecd71`. The unhidden state intervention had changed 2,280 pixels on that screen. This neutralization supports attribution of the screen-971 difference to those two foreground-car descriptors. It does not identify every individual changed pixel or the entire car composition. The screen-972 page-C update was not neutralized by the page-E pair, as expected; its exact one-slot `$C6B0` hide visibly affects the corresponding car update.

**Decision — FAIL for this road-camera cue:** the tested `$7A → $84 → lookup → list → Y-sprite` path is real, but the changed visible feature is the **foreground car**, not a causally attributed road edge. It cannot calibrate the Sega CD curve, ridge, bank, horizon or texture words. The screen-967/968 `$E630/$C630` road-like edge samples remain separate and their scalar relationship remains `INCONCLUSIVE`. No renderer or five-word interface change follows. The previous 128×64/30 Hz synthetic Sega CD milestone remains the BlastEm baseline.

## Provenance and reproduction

**Verified by execution:** macOS Darwin 25.6.0 x86_64; Python 3.14.8; isolated MAME `0.289 (mame0289-dirty)` executable SHA-256 `712f0f9eaf931d6032b20d615f74583d7a418c81763f9b052c7f6c4727450ee9`, pinned source `f34f02505e32c1993c6a782b6814232cbfc74e36`; owner-private ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Modified [Lua probe](../../tools/phase1b_mame_input.lua) SHA-256 `55ef9866757bacd10fa37ec5e6a02c8b0559f2a9cf1201d715d67c9ff03455b1`; [auditor](../../tools/phase1b_state7a_car_chain_audit.py) SHA-256 `9eff11bee080ce64c0ca2751260e148c04beae10356cd0f817e82e6f5125d257`; ignored audit JSON SHA-256 `4a9c497894c527fd731182036522acc66a81f37c44b83a95685127423aad0078`. The baseline screen-971 PNG SHA-256 is `ede22cd5e80aa0d48da591b00701b53be25b42976c8e59c1c4d031b6dddef98a`; the single `$E6B0` hide screen-971 PNG SHA-256 is `75a1447099aa256eda018c1c1bfe829b16605c758284547a38771cc8e4b1fd34`.

The paired baseline/intervention debug logs are in ignored `build/private/phase1b-state7a-{path,listwriter,list,fieldc,word84}-{baseline,plus16}/`. The main path logs have SHA-256 `aa785573fcc5128d7d7fe2f03dd4af9717e9685ba232cd6a17eaf148ad2a1d4d` and `31ecd0c5cd2b2ea9b7d6a50d93b52bfdc1c73142a4401a795eeaf62e402d79d4`; the list-writer logs `035871858ddfc7802d6b2f8178583fb9db41651a2adc13db49f33dc29a5905e7` and `ff237f2984ba030e7f8dc3c7aedd5d01fe36ae448e445cac1d4c37714a940eb2`; the Sub-CPU X input logs `1a1e0c3bc0a1032d79a77615e18cfacd86aec2138333294f9df4310f67162cd1` and `a7e8d93f4f33308d7d6f6870a386288a3064408bbb2050909fc9d0c3e06b0a0e`. The private disassembly is under `build/private/phase1b-state7a-{list,field,prelude}-disasm/` and is not tracked.

Use separate ignored working directories and the existing saved-state command from the [visual-lag gate](2026-10-28-state7a-visual-lag-gate.md). For main-field watches, add `-debug -debugger none -debuglog` and `PDRIFT_DEBUG_WATCH=shared PDRIFT_SHARED_WATCH_ADDR=0C084C PDRIFT_SHARED_WATCH_UNTIL=969 PDRIFT_STATE7A_FIELD_TRACE=1 PDRIFT_STATE7A_PATH_TRACE=1`. For list-copy watches and 8 KiB list captures, use `PDRIFT_SHARED_WATCH_ADDR=0C9F50 PDRIFT_SHARED_LIST_DIR=. PDRIFT_SHARED_REGS=1 PDRIFT_SHARED_WATCH_UNTIL=971`. For Sub-CPU X, use `PDRIFT_DEBUG_WATCH=ysprite PDRIFT_YSPRITE_WATCH_OFFSET=C6B0 PDRIFT_YSPRITE_REGS=1 PDRIFT_YSPRITE_INPUT_TRACE=1 PDRIFT_YSPRITE_INPUT_SLOT=C6B0 PDRIFT_YSPRITE_SEQUENCE_TRACE=1 PDRIFT_YSPRITE_SEQUENCE_END_FRAME=971`. Add `PDRIFT_STATE7A_DELTA_FRAME=966 PDRIFT_STATE7A_DELTA=16` only for intervention runs. Save `debug.log` and `phase1b-input.log` privately.

For the one-slot visual controls, make private 64 KiB copies of the baseline callback-970 source, set only hide bit `$10` at byte offset `$E6B0`, `$E6C0` or `$C6B0`, and set `PDRIFT_SOURCE_OVERRIDE_FRAME=970`, `PDRIFT_SOURCE_OVERRIDE_RANGE=<slot>:0010`, `PDRIFT_SOURCE_OVERRIDE=<absolute private copy>`, `PDRIFT_CAPTURE_PROFILE=road-edge`, `PDRIFT_SOURCE_DIR=.`, and `PDRIFT_SWAP_DIR=.`. The paired control sets both `$E6B0/$E6C0` in matching baseline and intervention source copies with range `E6B0:0020`. Finish with:

```sh
python3 tools/phase1b_state7a_car_chain_audit.py
```

The auditor checks the stage values, list-copy identity, screen provenance, exact hide bytes, prior-screen equality and three-run `$E6B0` repeat. **Not run:** BlastEm, another arcade emulator or physical hardware. MAME host duration was not treated as arcade hardware performance. **Next hypothesis:** trace a record that actually supplies the verified `$E630/$C630` road-like edge pixels backward through the main-CPU list and projection path; do not use the player-car chain as a road-camera calibration point.
