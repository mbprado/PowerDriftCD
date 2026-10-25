# Phase 1B: native Y-sprite versus screen-980 road boundary — 2026-10-25

**Hypothesis:** the callback-979 `$C` hide changes a native Y-sprite region that maps to screen 980's left road edge, while the unchanged right-edge pixels either lie outside that changed native region or are covered by later composition. **Baseline:** the [source-lag probe](2026-10-25-y-sprite-source-lag.md) reproducibly changed the left edge on Y=157–159 and only the right edge on Y=159. Its screen-980 response did not carry into screens 981–982.

## Frozen test and expected evidence

- Use an isolated MAME 0.289 source clone at `f34f02505e32c1993c6a782b6814232cbfc74e36`. Apply the tracked capture-only Y-bitmap patch and a second tracked patch limiting native bitmap dumps to frames 979–982. The installed MAME executable and upstream repository stay untouched.
- Replay the same callback-950 state and pulse-112 input twice: original source RAM, then the already prepared callback-979 `$C000`–`$C7FF` hide. Capture native 512×512 Y-sprite bitmaps, the pre/post rotation blocks and composed screens. Verify both composed screen-980 PNGs against the prior system-MAME baseline/hide and verify exact post-write source RAM.
- Compare native bitmap frames 979 and 980 between runs. Map changed native pixels through captured pre/post affine blocks surrounding swaps 978 and 980, and compare predicted changed screen pixels with the observed screen-980 difference. Report all tested frame/block combinations; do not assume the timing association from callback labels alone.
- At baseline screen-980 sand boundaries Y=157–159, record each edge pixel's native mapped coordinate, native value before/after the hide, and composed-screen change. Classify an unchanged right edge as **outside the changed native region**, **changed natively but masked in composition**, or **unresolved** only when the transform association is supported by the full changed-pixel mask.
- No Sega CD packet, geometry score, rendering architecture or physical hardware test is involved. Missing/ambiguous native mapping must be reported `INCONCLUSIVE`, without substituting a software bitmap or guessing the source layer.

Private ROMs, state, screenshots and raw bitmap dumps remain ignored under `build/private`. Record source/patch/binary hashes, commands and both result paths in the experiment report.
