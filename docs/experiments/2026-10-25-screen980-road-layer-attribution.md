# Phase 1B: screen-980 road-boundary layer attribution — 2026-10-25

**Question / hypothesis:** are the two screen-980 right-edge pixels that remained unchanged under the callback-979 `$C` Y-sprite hide supplied by rotation scanline fill or by later 16B sprite composition? **Baseline:** the [native bitmap experiment](2026-10-25-native-screen980-boundary.md) found transparent native Y-sprite words at `(290,157)` and `(291,158)`, while `(297,159)` came from the changed Y-sprite region. **Acceptance:** the [frozen plan](2026-10-25-screen980-layer-probe-plan.md) (`968dc8d`) requires before/after-composition palette indices, 16B sprite words and priority, replay controls and native transparency checks. **Result — verified by execution in isolated MAME 0.289:** the right-edge pixels on Y=157–158 come from **16B sprites**. The Y=159 right edge comes from the rotated **Y-sprite** bitmap. Thus the three-row visible boundary changes rendering layers within one short vertical span.

## Pixel-level evidence

**Verified by execution:** the capture-only [layer probe patch](../../tools/phase1b_mame_layer_980.patch) records twelve predetermined pixels at native frame 979, corresponding to composed screen 980. For each pixel, it saves the palette-index value after `rotate_draw`, the 16B bitmap word, the rotation priority byte and the final palette-index value after 16B composition. The analyzer independently evaluates the exact MAME comparison `((sprite >> 11) & 0x1e) < (priority & 0x1f)` and asserts the expected final index. None of the twelve samples uses the shadow-color branch.

| Screen pixel | Native Y word, baseline→hide | After rotation, baseline→hide | 16B word / priority | Final index, baseline→hide | Provenance |
| --- | --- | --- | --- | --- | --- |
| `(290,157)` | `$FFFF→$FFFF` | `202→202` | `738 / 255` | `2786→2786` | 16B sprite |
| `(291,158)` | `$FFFF→$FFFF` | `203→203` | `738 / 255` | `2786→2786` | 16B sprite |
| `(297,159)` | `66→$FFFF` | `4162→204` | `$FFFF / 1→255` | `4162→204` | rotated Y sprite |

**Verified by execution:** at the first two right-edge pixels, the 16B priority value is `0`, less than `255 & 31 = 31`, so the sprite passes. Its final index is `0x800 | 738 = 2786`, different from the rotation fill `202/203`. The immediate next pixel to the right has no 16B sprite (`$FFFF`) and retains rotation fill `202/203`. At Y=159 the 16B bitmap is transparent; the final value equals the rotated Y-sprite value before and after the hide. The three left-edge controls `(90,157)`, `(84,158)` and `(82,159)` likewise follow rotation and have transparent 16B pixels. **Inference from this execution:** the sand boundary detector is measuring a composited outline, not one continuous Y-sprite contour.

**Documented only in the pinned [MAME screen update](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/segaybd.cpp) and [rotation routine](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/segaic16.cpp):** Y sprites feed `rotate_draw`, transparent native pixels receive scanline color, and 16B sprites can replace the result by priority. The capture probes that precise emulated code path. This is evidence about MAME's modeled arcade rendering, **not** a measured stock Sega CD pipeline or physical Y-Board timing.

## Controls, limitations and decision

**Verified by execution:** the isolated MAME build preserved the same decoded RGB screen-980 baseline/hide images as the prior system-MAME replays. Screens 960–979 matched between patched baseline and hide; captured source RAM differed at exactly 116 `$C` descriptor hide bytes and matched the prepared override. The native Y-bitmap SHA-256 values also matched the previous isolated native experiment. Three independent hidden replays produced identical `layer-0979.csv`, native-frame-979 bitmap and composed-screen-980 PNG hashes. Two analyzer runs produced identical private result JSON SHA-256 `842ec3421580788af7328ad229d4d2e960ebcd11cf3a2c311b1d2af5f91a3065`.

**Verified by execution:** the initial layer-probe build failed at compilation because the probe used `pix(y)[x]` while MAME's bitmap API returns one pixel from `pix(y)`. The isolated clone and tracked patch were corrected to `pix(y,x)` before any layer-probe replay. The successful incremental build log is retained. No gameplay result relies on the failed build.

**Decision — inference from verified execution:** these Y=157–158 right-edge points should be labeled **16B-composited** in future arcade geometry comparisons, while Y=159's right edge is Y-sprite-derived in this intervention. Do not drop or relabel the rows to improve a fit; record mixed provenance and keep the [forward packet test](2026-10-25-forward-road-causal-gate.md) `INCONCLUSIVE` because it required three two-sided `$C`-Y-sprite causal rows. The identity of the 16B sprite descriptor supplying those two pixels, a world-space road-width variable and a predictive five-word camera adapter remain **unsupported**. No renderer/art/interface change or new Sega CD timing claim follows.

## Reproduction and private evidence

**Verified by execution:** project baseline `968dc8d` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, built as `0.289 (mame0289-dirty)` with `make SOURCES=src/mame/sega/segaybd.cpp NOWERROR=1 REGENIE=1 -j8`. The successful executable SHA-256 is `690c57de086c2cdf069e0290564c241cceb8ff53101832cf760ac909d4270766`; successful incremental build log SHA-256 `55dbc731b1c52131e2415be022b5a2a8f5027e02c5c54f16d95c2492dbce2012`. The tracked layer patch SHA-256 is `d6b38a2d47d6d79ab2d544693eb3d8bb12b06054dcf9f9c6294cf1e736b7d890`; analyzer SHA-256 `d87eec1b13a11896ff5ec8de9b5813b9875aaa0ecb14c0e7dcbdd49953def2f4`. The preceding [native report](2026-10-25-native-screen980-boundary.md) gives the base and frame-window patch hashes.

**Verified by execution:** owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 saved-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Ignored baseline/hidden probe CSV SHA-256 values are `b5265da1bb35494a4c3a78d80d45f5795df4374e4af3a9bb19d01c16cf908a6d` and `cbfc1185d9095f3ab3cd3f1b3dbb385e4ba9ea195682cc9f8aa19fbf2bce5a28`. The hidden CSV, native bitmap and screen PNG hashes matched across all three hidden runs; the native bitmap hashes are `07437b15e496d0c74f6e74779a101aeb4e3dfe6277d170c2c5088839e9b0ea87` (baseline) and `043e238a765f7cfbc62596a50e53c8ffb6b188a99357b0ebede251725d67589f` (hidden). Initial patched replay logs SHA-256: `8f34857ec3de522d60f94f028805d4be13f4406c1587a3659320514e220e5b83` and `9c7873a396d97892bcb4057921ec5412cf1885e61940954a1e70c8b1fa42f12a`. Raw bitmaps, CSVs, screenshots, ROMs and state remain ignored under `build/private/phase1b-layer980/`.

Apply the three tracked MAME patches in order to a fresh isolated `mame0289` clone: `tools/phase1b_mame_ybitmap.patch`, `tools/phase1b_mame_ybitmap_980.patch`, then `tools/phase1b_mame_layer_980.patch`; build with the command above. Run baseline and callback-979 `$C000`–`$C7FF` hide replays with the preceding experiment's fixed input/state settings, additionally setting `PDRIFT_LAYER_PROBE_DIR=.` in each private working directory. Analyze with:

```sh
python3 tools/phase1b_screen980_layer_audit.py build/private/phase1b-layer980 build/private/phase1b-forward-baseline-112-990/swap-screen-0980.png build/private/phase1b-right-search-979-C000-00800/swap-screen-0980.png
```

No BIOS, BlastEm, second arcade emulator or physical hardware was run. Host wall-clock time was not used as hardware performance data.

**Next bounded test — hypothesis:** identify the specific 16B descriptor or source input that produces the Y=157–158 right outline. Use a causal, single-descriptor hide or write trace and preserve the 16B-versus-Y layer labels in machine-readable geometry evidence. Only then decide whether the current five-word Sega CD camera packet should be compared with the *composited* arcade outline or with a selected projection layer.
