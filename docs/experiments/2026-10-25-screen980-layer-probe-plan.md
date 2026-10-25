# Phase 1B: screen-980 right-edge layer probe — 2026-10-25

**Question / hypothesis:** the right road-boundary pixels at screen-980 `(290,157)` and `(291,158)` are native-Y-transparent and therefore come from the rotation scanline fill or later 16B sprite composition. **Baseline:** the [native bitmap experiment](2026-10-25-native-screen980-boundary.md) showed `$FFFF` native Y-sprite words at those coordinates under the matching affine transform. The `(297,159)` right edge is an opaque Y-sprite control changed by the callback-979 `$C` hide.

## Frozen test

- Keep the isolated MAME 0.289 clone, callback-950 saved state, pulse-112 input, callback-979 `$C000`–`$C7FF` hide and native bitmap capture used in the previous experiment. Add a capture-only patch to that clone; do not edit installed/upstream MAME.
- At native frame 979, record the palette-index value **after rotation and before 16B composition**, the 16B sprite bitmap word, the rotation priority byte, and the **final** palette-index value at each of the three right-edge pixels and its immediate horizontal neighbors. Also record the previously verified left-edge pixels `(90,157)`, `(84,158)`, `(82,159)` as controls.
- Compare baseline and hide captures with the exact MAME 0.289 priority condition. If final equals the rotated value and the 16B sprite does not pass priority, classify the pixel as rotation output. If a passing 16B sprite changes the final value, classify it as 16B composition. If both operations produce the same value or the evidence is ambiguous, classify `INCONCLUSIVE`.
- Require exact decoded-RGB agreement with the prior baseline/hide screen-980 captures, identical screens before callback 979, exact post-write source override, and correct native Y-sprite transparency at the two questioned right-edge pixels. No Sega CD packet score or physical-hardware inference is permitted.

Record build and patch hashes, raw private capture paths, repeated-run checks and layer decisions in a report. All ROMs, state, screenshots and raw pixel captures stay ignored under `build/private`.
