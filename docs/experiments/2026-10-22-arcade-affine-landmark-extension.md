# Phase 1B: earlier-epoch affine landmark check — 2026-10-22

**Question / hypothesis:** does the arcade projected-X-to-visible-edge relation measured at descriptor callbacks 970/974 also hold at the earlier matched-position callback 966, and do the landmarks locate those depths well enough to choose Sega CD scanlines? **Baseline:** the [two-depth affine landmark](2026-10-22-arcade-affine-landmark.md) and unchanged 128×64 [Sega CD road prototype](2026-10-20-wide-live-road-pipeline.md). **Expected evidence:** the same one-byte hide and pre-swap affine checks at 966, with two depths and center/left steering; a gain fitted only at 970; independently visible held-out edges. **Result — PASS for this local edge check, INCONCLUSIVE for Sega CD viewport calibration, verified by execution:** the 970 gain predicted four other depth/epoch shifts within 1.94 arcade screen pixels. The two centered landmark rows are only 2–7 arcade screen pixels apart, and no independent arcade-to-Sega viewport correspondence exists.

## Source, capture, and controls

**Verified by execution:** source baseline `2b83f94` on `experiment/perspective-road`; macOS/Darwin 25.6.0 x86_64; Python 3.14.8. The original source data come from the same owner-local Power Drift ROM manifest and callback-950 state as the [prior landmark report](2026-10-22-arcade-affine-landmark.md): SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The isolated MAME 0.289 capture build is SHA-256 `9e54fdc4b5da5e5f7ba2308b35be157803ebe1d5a54d41ae28301c675bd0456d`; upstream MAME was not edited. The extended analyzer `tools/phase1b_affine_landmark.py` is SHA-256 `2d81eb28d639ccd4d51f55667b6511a60ed58421e4b06a5302c5d8ead1dcf0c4`.

**Verified by execution:** eight new MAME replays supplied centered/left baseline and single-descriptor-hidden native bitmaps for `$3400/$3600` at callback 966. The eight 970/974 baseline/hidden pairs were reused. Each hidden replay changed exactly its selected descriptor hide-bit byte, left the intervention-frame screen identical to baseline, and reproduced the prior composed baseline/hidden screens byte-for-byte. The exact upstream lookup-position words match across center/left at projection callbacks 964, 968, and 972; each projected X at callback `f` is linked to the descriptor at `f+2` and screen at `f+3`. The input is centered steering 128, with left steering 64 beginning at callback 960, from the same saved arcade state. No Sega CD image or hardware test was run.

**Verified by execution:** the earlier native-row `descriptor Y + 3` definition has no occupied pixels for `$3600` at callback 966: this callback uses graphic `$3C84`, while later `$3600` callbacks use `$3888`. This was found from native mask occupancy before extending the screen-edge analysis. The extension therefore specifies **descriptor Y + 1 for every case**, including the 970 calibration cases. This is an exploratory revised landmark, not a blind replication of the earlier Y+3 definition. Center and left have the same graphic and horizontal draw direction within each matched depth/epoch pair. The original Y+3 analysis was rerun with the extended script; all original cases, comparisons, and gain matched its previous private JSON exactly after removing the new row-offset metadata.

## Measured arcade-screen landmark

**Verified by execution:** the specified native row was mapped through each capture's pre-swap affine block to the 320×224 composed screen. The mapped leftmost pixel changed in the independent one-descriptor hide screen difference in all **12/12** cases. Across all cases, the specified landmark covered 1,227 changed RGB pixels and 19 mapped pixels that remained unchanged in final composition. The full pre-swap mapping missed none of the changed RGB pixels; using the later post-swap block missed 673. This validates the render-stage timing for the bounded sample, while final composition can still mask some mapped source pixels.

| Descriptor callback / depth | Center landmark Y | Center → left edge X | Edge shift | Projected-X shift | Error from 970 gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| 966 / `$3400` | 141 | 118 → 120 | +2 px | +3 words | −0.90 px |
| 966 / `$3600` | 139 | 126 → 128 | +2 px | +2 words | +0.07 px |
| 970 / `$3400` | 144 | 109 → 128 | +19 px | +20 words | fit |
| 970 / `$3600` | 139 | 124 → 138 | +14 px | +14 words | fit |
| 974 / `$3400` | 148 | 94 → 136 | +42 px | +44 words | −0.52 px |
| 974 / `$3600` | 141 | 117 → 146 | +29 px | +28 words | +1.94 px |

**Verified by execution:** a zero-intercept least-squares gain fitted to only the two callback-970 pairs is `0.966442953` arcade screen pixels per projected-X word. The four held-out signed errors are `−0.8993`, `+0.0671`, `−0.5235`, and `+1.9396` pixels. Callback 966 shifts are only two pixels, so quantization makes those two checks weak; callback 974 provides the larger displacement test. This gain is local to this content-defined edge and steering interval. It does not determine the arcade's world-to-screen projection or a universal pixel/word conversion.

**Verified by execution:** the centered landmark Y is `(141,139)` at callback 966, `(144,139)` at 970, and `(148,141)` at 974 for `$3400/$3600`. Thus their same-epoch row separation is 2, 5, and 7 arcade pixels and is changing. The prior camera-shape audit placed these depths 16 Sega output rows apart under both uncalibrated maps; these arcade observations give no basis for that 16-row assumption. The landmark is a strip of graphic content, not a decoded road centerline, so even its arcade Y is only a bounded visibility coordinate.

## Reproduction and decision

Run from the repository root with the owner-local ROM, state, and isolated MAME build described above. The replay command writes only beneath ignored `build/private/` and reuses already present 970/974 captures:

```sh
python3 tools/phase1b_affine_landmark.py build/private run --frames 966 970 974 --mame /private/tmp/pd-mame0289-landmark/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_affine_landmark.py build/private analyze --frames 966 970 974 --row-offset 1 --output-name phase1b-affine-landmark-extension.json
python3 tools/phase1b_affine_landmark.py build/private analyze --output-name phase1b-affine-landmark-regression.json
python3 -m py_compile tools/phase1b_affine_landmark.py
```

**Verified by execution:** ignored `build/private/phase1b-affine-landmark-extension.json` has SHA-256 `23d3b85f192fb3d0a07fef2f7b92927eb4d06ca923886804cd58c0aa759b543c`; the separate original-result regression JSON has SHA-256 `b28ee677dab1c4555587b0a1885c0554963b9428a31c65f85213393da01a3471` and matches the original parsed result after excluding its added offset field. Case-level checksums of every raw bitmap, screen, and MAME log are in the ignored extension JSON. No ROM, native bitmap, screenshot, or extracted commercial graphic is tracked.

**Inference from verified execution:** arcade projected X is a useful lateral reference for these two strip edges over this short interval. This strengthens the case for an offline adapter experiment using projection words as the reference signal. It does **not** calibrate the current Sega CD source-X units, viewport crop/scale, depth-to-scanline mapping, or five-word command producer. The previous synthetic sine-table inverse fit should not be revised using arbitrary row placement.

**Next bounded test — hypothesis:** identify a stable road-center or edge coordinate in both the arcade reference and the Sega CD synthetic viewport, then specify a viewport crop/scale and depth-to-row correspondence independently of the fit target. Only then repeat the offline camera-shape audit. If the calibrated five-word waveform still leaves a structured depth residual, test an offline replacement curve lookup without changing the packet interface. The current Sega CD renderer and all private boot files remain unchanged; physical hardware remains untested.
