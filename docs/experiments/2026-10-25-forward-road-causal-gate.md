# Phase 1B: forward road-packet causal gate — 2026-10-25

**Question / hypothesis:** will the frozen earlier screen-975 packet `[38,0,0,4,31]` predict a later arcade road span without target-row fitting? **Baseline and acceptance:** the locally committed [screen-977 plan](2026-10-25-forward-screen977-plan.md) (`3c2aa14`), then its screen-980 and screen-981 amendments (`170290c`, `cd60a05`), require at least three screen Y=153–163 rows with **both** detected sand boundaries causally changed by a source hide before any geometry score is valid. **Result — INCONCLUSIVE, verified by execution in MAME:** screens 977, 980 and 981 did not pass that attribution gate. The packet was never scored on these targets; a visible edge alone was not treated as causal evidence.

## Baseline and source attribution

**Verified by execution:** a fresh pulse-112 baseline through screen 978 reproduced all 17 earlier screens 960–976 pixel-for-pixel against the saved baseline. A second isolated baseline through screen 990 reproduced screens 960–978 pixel-for-pixel against the first extension. The same callback-950 saved state and held-pedal/steering schedule were used. The road-boundary detector found one row at screen 977 (Y=155), three at 980 (Y=157–159), and seven at 981 (Y=157–163). Screen 979 had only two detectable rows; 980 was selected as the first later screen with three. These counts were inspected only to select a measurable target, not to select a camera packet.

**Verified by execution:** the callback-976 Y-sprite linked list reached 106 descriptors on page `$C`; a broad `$C000`–`$C7FF` hide changed neither edge on screen-977 Y=155. The screen-977 test is `INCONCLUSIVE` by its frozen minimum-row rule. At callback 979 the reachable list was page `$E`. Its broad hide changed neither side of the three screen-980 rows. Follow-up broad hides of `$8` and `$A` also changed neither side; `$C` changed the left edge on all three rows and the right edge only on Y=159. The screen-980 fallback has **one** two-sided causal row, below the frozen three-row minimum, so it is `INCONCLUSIVE`. The page controls are an attribution diagnostic after the fallback failed, not a new packet fit.

**Verified by execution:** screen 981 had seven detected rows, but a callback-980 broad `$C` hide changed neither boundary on any row. This separately frozen test is also `INCONCLUSIVE`. Every analyzed hide verified that post-write Y-sprite RAM matched the prepared override, only descriptor hide bytes changed, and all earlier composed screens remained pixel-identical to baseline. The tests used normal MAME execution with the selective `road-edge` capture profile; no evidence-cache hit was treated as a replay.

| Composed screen | Baseline detected rows | Frozen/source hide | Two-sided causal rows | Decision |
| ---: | ---: | --- | ---: | --- |
| 977 | 1 | callback 976, `$C000`–`$C7FF` | 0 | INCONCLUSIVE |
| 980 | 3 | callback 979, `$E000`–`$E7FF` | 0 | INCONCLUSIVE |
| 980 attribution controls | 3 | callback 979, pages `$8`, `$A`, `$C` separately | 0, 0, 1 | source timing remains partial |
| 981 | 7 | callback 980, `$C000`–`$C7FF` | 0 | INCONCLUSIVE |

**Inference from verified execution:** a Y-sprite page reachable at a Lua callback is not enough to identify which composed screen boundary it supplies. The `$C` control at callback 979 affecting screen 980 despite the reachable page being `$E` supports a buffering or page-timing explanation, but the exact source latch and the unaffected right edges are **unsupported**. The seven screen-981 detected boundaries are not validated road-reference rows. Therefore no PASS/FAIL claim about the five-word camera packet, original art or Sega CD hardware follows from these screens.

## Reproduction and provenance

**Verified by execution:** source baseline for first capture `3c2aa14`, fallback plan `170290c`, screen-981 plan `cd60a05`, branch `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The owner-local 53-file ROM manifest SHA-256 was `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 saved-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No Sega CD image/BIOS, BlastEm, second emulator or physical hardware was used. All frame counts are MAME callback/screen labels, not original-console performance measures.

**Verified by execution:** the two ignored baseline logs under `build/private/phase1b-forward-baseline-112{,-990}/phase1b-input.log` have SHA-256 `d46a907ed033c049785c926c1152326c96c17c720996065f3e015c458931a5ca` and `47baaf853df5c0e212648c00a52ca60ca9424d57363ad721cee9fac0796aa7f5`. Their screen-977/980/981 PNG SHA-256 values are `fddb719301c129928d37898d19797079e1c08def040f49b4cd8f58a01fe352f8`, `6646ffb786bb051848af7eaa16b6d273f326a91b0cb4cbcee342391f941284f6`, and `4725e491a3e9c93e2b2e53871e4dd87db22a10bbb73b67b946199175840b7eba`. The callback-976/979/980 private source-RAM SHA-256 values are `bb1dbed2950e20e2c0e8c1dbc29b145f6c16868b74f96f34f9c1a7708bff83cf`, `cf9cea5f47098eddcc7e11d69c3f060d28fdd84723aaee99acef397a93a1805d`, and `4a13a55cdd598bde300f2f1faedaf5a5d2cd200a64b2a72e117e0075b0b8d82a`.

**Verified by execution:** ignored analysis JSON SHA-256 values are `cbb71765beca7dd4ed8ef569dd7f25f5347485e62d13af8e345542ae26e198ae` (976 `$C`), `17e6fb9e52a741517b6fe9fbe1418b291b2190df1f182f856216dc2b9e7b3152` (979 `$E`), `ec75a59cb71a8bb0c599b9c4ceba21785e1b3e5bba822b867691a66524b3cfdd` (979 `$8/$A/$C`), and `49b5d5c686e5ae752b2b900bd85712baaac934f102c9a333759e6bae35000699` (980 `$C`). `tools/phase1b_right_source_search.py` was extended with an optional private baseline directory and later callback range while retaining its earlier defaults; its SHA-256 is `ac1090cae6b6901ec627720986a5ef12f1d836aeff35a2686a6916dc15940b1b`. Screenshots, source RAM, state and ROMs remain ignored under `build/private`.

Reproduction uses `tools/phase1b_mame_input.lua` with `PDRIFT_STATE_LOAD` set to the private callback-950 state, `PDRIFT_STEER_PULSE=112`, `PDRIFT_SWAP_DIR=.`, `PDRIFT_SOURCE_DIR=.`, and `PDRIFT_SEQUENCE_END_FRAME=978` or `990` for the separate baselines. With the latter baseline present, run/analyze each broad group using:

```sh
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 980 --groups C000:0800 --capture-profile road-edge --baseline-name phase1b-forward-baseline-112-990
python3 tools/phase1b_right_source_search.py build/private analyze --callback 980 --groups C000:0800 --baseline-name phase1b-forward-baseline-112-990
```

Replace callback/group with `976 C000:0800`, `979 E000:0800`, or `979 8000:0800 A000:0800 C000:0800` for the other trials. The owner-local state, ROM directory and source captures are required; no protected data is in the tracked tools or report.

**Next bounded experiment — hypothesis:** identify the composed-screen Y-sprite source latch or rotation-buffer dependency directly for one later road update, starting with callback 979 where a page-`$C` hide changed the left edge. Require two-sided causal attribution on at least three rows before returning to forward packet scoring. A screen-only boundary series would risk measuring the wrong layer.
