# Phase 1B: steered road trajectory and host fixture audit — 2026-10-23

**Question / hypothesis:** can adjacent mild-steering arcade frames produce a causally verified two-sided road-width trajectory, and can the existing 128×64 original-art host fixture represent the verified sample under an explicit screen mapping? **Baseline:** the [single-frame, six-row mild-steering landmark](2026-10-23-mild-steering-two-sided-road.md) and the [60-packet wide road fixture](2026-10-23-coupled-wide-road-motion.md). **Acceptance:** confirm exact one-byte source overrides and unchanged preceding screens; count rows where *both* independently detected sand boundaries respond; compare only accepted rows with reproduced host metrics. **Result — verified by execution: INCONCLUSIVE for a consecutive causal arcade trajectory; PASS for a bounded host comparison of the one verified window.** No production renderer or camera interface was changed.

## Arcade intervention

**Verified by execution:** source commit `7cf127b` on `experiment/perspective-road`, with the new audit tool uncommitted during execution. macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME `0.289 (unknown)`, executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The locally held 53-file ROM manifest and callback-950 state checksums remain `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No commercial image or extracted asset is tracked.

**Verified by execution:** `tools/phase1b_steer_width_trajectory.py` replayed the existing pulse-112 saved-state sequence six times. For each trial it hid one candidate `$3888` source descriptor, confirmed the captured source RAM differed from baseline by **exactly one byte**, and confirmed all prior composed screens were pixel-identical. Candidate slots came from the earlier centered depth tracing and matching pulse-112 source records; this is a focused set, not an exhaustive scan of all Y-sprite descriptors. The screen number is callback + 1. A row counts as causal only if both the left and right boundary pixels change under the hide.

| Callback / screen | Source slot | Two-sided visible candidate rows | Left boundary changed | Right boundary changed | Both changed |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 966 / 967 | `$E5D0` | 11 | 0 | 0 | 0 |
| 970 / 971 | `$E5D0` | 5 | 1 | 0 | 0 |
| 970 / 971 | `$E5B0` | 5 | 0 | 0 | 0 |
| 972 / 973 | `$E5D0` | 9 | 0 | 0 | 0 |
| 972 / 973 | `$E5B0` | 9 | 0 | 0 | 0 |
| 974 / 975 | `$E610` | 7 | 6 | 6 | 6 |

**Verified by execution:** both callback-972 hides left the entire screen-973 PNG byte-identical to baseline despite changing source RAM. At callback 970, the `$E5D0` hide changed one left boundary but no right boundary. At callback 974, the earlier six rows Y=154–159 were reproduced exactly; screen-975 baseline and hidden SHA-256 values were `b4ac1d35d6be90614eccf40f7c126a57ad23aaa9050664473f55555a1ab0a4d2` and `56c0c41379a638b7ae7c76bd72ab182cfb21ad03dfb15685c27c6352d4426da5`.

**Inference from verified execution:** a visible pair of sand transitions at nearby frames does not establish that the *tested* sprite strip causes both transitions. The failed callback-972 interventions may reflect rotation-buffer cadence or a different active strip; this experiment did not isolate which. **Unsupported:** a continuous, causally identified arcade width or camera trajectory, and the assertion that no such trajectory can be recovered. The next arcade step requires tracing the specific source contribution to each boundary at callbacks 966–972, possibly across the rotation buffer, before exporting any sequence as a real track/camera reference.

## Explicit host-only comparison

**Verified by execution of the original-art host reference:** the only accepted arcade window is screen 975, Y=154–159, with `(left,right,width)` values `(82,296,215)`, `(81,296,216)`, `(77,298,222)`, `(76,300,225)`, `(75,302,228)`, `(74,303,230)` in 320-pixel arcade screen coordinates. For a deliberately provisional crop, map `x_sega = 0.4 × x_arcade` and `y_sega = y_arcade − 128`, so these rows become output Y=26–31. This stretches the full 320-pixel arcade width into 128 pixels and takes arcade Y=128–191 as the 64-row viewport. It is a comparison convention, **not** a calibrated arcade-to-Sega camera transform; inclusive widths have subpixel rounding differences.

**Verified by execution of the host reference:** the audit recomputed the original wide-road texture and trace lines for all **60/60** recorded packets and matched their six relevant row bounds exactly to the tracked host metrics (SHA-256 `60187a57c8c8f768de32ebf4a365dc4d55e5f9b6aa59a14c8adf0ad58451721a`). It then measured mean absolute left/right edge error over the six rows. Of those 60 existing synthetic packets, `[42,0,0,4,28]` was best by edge position at **3.333 output pixels per edge**; `[3,0,0,4,18]` was best by width at **1.333 output pixels per row**, but its edges were displaced by **18.333 pixels per edge**. Searching all **96 curve × 48 texture** combinations with ridge=0, bank=0 and horizon=4 found `[40,0,0,4,9]` at the same best **3.333-pixel mean edge error** and **2.000-pixel mean width error**. These are deterministic host geometry errors, not Sega CD cycle timings or BlastEm results.

**Inference from verified execution:** the existing fixture can approximate the single-window width slope, but its current curve/texture settings do not match both edge positions under the chosen uncalibrated full-width mapping. The target center at arcade Y=156 maps to X=75.0, beyond the recorded row-28 host-center range of X=55.5–72.0. Horizontal crop alignment alone can change this result, so the 3.333-pixel residual does **not** prove a five-word camera limitation. Width also describes different pixel classes: arcade sand-to-non-sand road region versus the synthetic stamped road colors.

## Reproduction and decision

```sh
python3 tools/phase1b_steer_width_trajectory.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_steer_width_trajectory.py build/private analyze
python3 tools/phase1b_steer_width_trajectory.py build/private compare --host-metrics docs/experiments/data/wide-road-motion-host-metrics.json
python3 -m py_compile tools/phase1b_steer_width_trajectory.py
```

**Verified by execution:** ignored raw MAME logs, source overrides, captured RAM and screenshots remain under `build/private/phase1b-trajectory-*`. Private derived JSON SHA-256 values are `b0e35c73352b52deed523b1d64d57adbcb94260b15b1fe7302ffd2df1e664767` for the intervention table and `cbfd576df4796dd88cdfbdb57daf97c47c049b709212548e4e9a143191699319` for the host comparison. This experiment did not run BlastEm, a second arcade emulator, or physical hardware. Original-only disc boot and stock-hardware performance remain unresolved.

**Next bounded test — hypothesis:** identify which source descriptor or rotation-buffer state supplies the right boundary at callback 970, then repeat on one adjacent epoch. If two or more epochs yield causal two-sided rows under the same crop, test whether a single sequence of independently chosen five-word packets can approximate their edge motion. Preserve the current 30 Hz synthetic milestone until that requirement is measured.
