# Phase 1B: bounded `$7A` visual-lag gate — 2026-10-28

## Question and baseline

**Hypothesis:** the independently predicted main-CPU state word `$0C0840+$7A` can affect a later arcade sprite update, providing one causal bridge between the scalar model and displayed geometry. **Baseline:** local `8e6c990`, the frozen [pulse-204 forward prediction](2026-10-27-state24-forward-chain.md), and the three-run [screen-967/968 exact-source attribution](2026-10-28-screen967-adjacent-source.md). The separate prediction has marker 965 `$7A=$FFFE` and marker 967 `$7A=$FFFD`; its `$7C` values are 7 and 10. The attributed screen-967/968 samples move, but their relation to these scalar values was **unsupported** before this test.

**Method — verified by execution:** add a narrowly bounded optional Lua perturbation of main-CPU shared word `$0C08BA`, only at callback 965 or 966 and only by a signed delta within ±16. It logs the old/new words and reads the value back after writing. Replay the same private callback-950 state and pulse-204 steering schedule in isolated MAME 0.289. Compare all composed screens and Y-sprite source snapshots from callbacks 960–982 with the existing unmodified baseline, then repeat any visible effect in fresh MAME processes. This is a causal sensitivity test. It does not fit a Sega CD packet.

## Result

| Intervention | Word read → written | First changed Y-sprite source | Changed composed screens | Interpretation |
| --- | --- | --- | --- | --- |
| `+2` at callback 965 | `$0000→$0002` | none through 982 | none through 982 | No observed effect at this timing and dose. |
| `+2` at callback 966 | `$FFFE→$0000` | none through 982 | none through 982 | No observed effect at this timing and dose. |
| `+16` at callback 966 | `$FFFE→$000E` | callback 970 | 971 and 972 only | Delayed sprite and screen effect; three fresh runs agree. |

**Verified by execution in MAME:** the callback-966 old word matches the frozen marker-965 prediction, while callback 965 reads `$0000`. This supports a marker-to-Lua-callback offset for this sampled word. It does **not** establish the full CPU-to-screen schedule or which version of the state each Y-sprite routine consumes. The `+2` callback-965 test was used to diagnose timing; the `+16` callback-966 test was an exploratory dose chosen after the `+2` runs showed no image difference. It is not held-out predictive validation.

**Verified by execution:** the `+16` trial left every screen through 970 byte identical to baseline. At callback 970, exactly 12 Y-sprite source bytes differed, confined to four 16-byte descriptors at `$C6B0/$C6C0/$E6B0/$E6C0`; the same 12 byte offsets differed in source snapshots 971–982. Screens 971 and 972 each changed **2,280 RGB pixels**. The changed bounding boxes were X=104–210,Y=154–210 and X=106–212,Y=154–210 respectively. Screens 973–982 were byte identical despite persistent source differences. Two additional **fresh MAME runs** reproduced the exact source-difference maps, image-difference maps and relevant image/source hashes. Their logs differed by run path.

**Interpretation — inference from verified execution:** `$7A` can influence a later Y-sprite descriptor and visible pixels on this pulse-204 schedule at a sufficiently large intervention. The first changed source appears four Lua callbacks after the write and the first changed screen five callbacks after it. These are observation offsets, not an established hardware pipeline latency. The changed descriptors are **different** from the `$E630/$C630` pair supplying the sampled screen-967/968 edges. The screen-971/972 changed area has no detector-eligible Y=153–163 two-sided road rows, so its semantic role and relation to road curvature remain **unsupported**. The zero `+2` image result cannot distinguish quantization, later overwrite, or an insensitive branch without an instruction-level trace.

**Camera-adapter gate — INCONCLUSIVE:** there is still no justified numerical mapping from `$7A/$7C` or the observed descriptor changes to curve phase, ridge phase, signed bank, horizon and texture offset. No packet was frozen or scored against the screen-967/968 edge samples. Reusing the old `[38,0,0,4,31]` inverse-fit packet would not make this a forward test. The validated synthetic Sega CD 128×64/30 Hz renderer remains unchanged.

## Reproduction and limits

**Verified by execution:** macOS Darwin 25.6.0 x86_64, Python 3.14.8, isolated MAME `0.289 (mame0289-dirty)` executable SHA-256 `712f0f9eaf931d6032b20d615f74583d7a418c81763f9b052c7f6c4727450ee9`, pinned MAME source `f34f02505e32c1993c6a782b6814232cbfc74e36`, owner-private ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`, callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`, and frozen pulse-204 scalar prediction SHA-256 `6a68c7fa35098f88e82def20d243eab199864d4daffc5db1c0f3660b0e1b74c1`. Source baseline revision `8e6c990`; this local experiment modifies only the capture Lua script and adds its auditor/report. The modified [Lua script](../../tools/phase1b_mame_input.lua) SHA-256 is `b598eb7b3629503cb2c470b2b5a76983aa23f0606fceb9248afc5a6c2a858ae6`; [auditor](../../tools/phase1b_state7a_visual_gate.py) SHA-256 is `7d1444fada69d21e74dc04f3fc822be710166a78cfd17929a7c27c3a054c97a6`.

For each trial, use its own ignored `build/private/phase1b-pulse204-state7a-<name>/` working directory. Set `SDL_VIDEODRIVER=dummy`, `PDRIFT_SNAPSHOT_DIR=.`, `PDRIFT_SWAP_DIR=.`, `PDRIFT_SOURCE_DIR=.`, `PDRIFT_YBITMAP_DIR=.`, `PDRIFT_LAYER_ROWS_DIR=.`, `PDRIFT_CAPTURE_PROFILE=full`, `PDRIFT_SEQUENCE_END_FRAME=982`, `PDRIFT_STATE_LOAD=<absolute callback950.sta>`, `PDRIFT_STEER_PULSE=204`, `PDRIFT_STATE7A_DELTA_FRAME=<965 or 966>`, and `PDRIFT_STATE7A_DELTA=<2 or 16>`. Execute:

```sh
/private/tmp/pd-mame0289-native966/mame pdrift -rompath /Users/murilo/repos/PowerDriftCD/build/private/phase1b-roms -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua
python3 tools/phase1b_state7a_visual_gate.py
```

Run the auditor from the repository root after saving each MAME run's stdout/stderr as `phase1b-input.log`. It checks the frozen prediction hash, the logged writes, all 23 screen/source pairs, the exact first changed source slots, and three-run reproducibility. The ignored audit JSON is `build/private/phase1b-state7a-visual-gate.json`, SHA-256 `a318fb07d0d97addfbc946d3e6b0e3acbc3c60ccc6b5c771a8feb39d13db45fb`. Raw ROMs, saved states, proprietary sprite RAM, screenshots and logs stay private. No Sega CD disc, BlastEm, second arcade emulator or physical hardware was run; MAME host speed is not arcade hardware performance.

**Next bounded test — hypothesis:** instrument the main-CPU `$7A` consumer and the writer of the changed `$C6B0/$C6C0` descriptors in one replay. Establish which intervening calculation carries the `+16` difference and whether that descriptor is a road surface, scenery, or another object. Only then derive a state-to-five-word rule from known quantities and reserve a fresh schedule or update for visual validation. Do not enlarge the camera interface from this result.

**Subsequent result — verified by execution:** the [bounded dependency trace](2026-10-28-state7a-foreground-sprite-chain.md) identified the surviving `$7A` step, shared-list transfer and foreground-car sprite. This intervention is not a road-camera calibration point.
