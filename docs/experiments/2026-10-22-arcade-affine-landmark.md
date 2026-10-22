# Phase 1B: two-depth arcade affine landmark — 2026-10-22

**Question / hypothesis:** can one specified, causally visible landmark be propagated from the arcade's native Y-sprite bitmap to the composed screen at two matched-position epochs, and does its lateral shift agree with the traced projection words at two depths? **Baseline:** the [depth-screen localization](2026-10-22-arcade-depth-screen-localization.md) and [pre-swap affine validation](2026-10-22-arcade-strip-rotation-prediction.md). **Acceptance:** capture original and one-byte-hidden bitmaps for `$3400` and `$3600` under centered/left steering at descriptor callbacks 970 and 974; preselect the occupied native span at descriptor-origin Y+3; map it using the captured pre-swap affine block; verify its left edge against the independent RGB hide difference; fit a single lateral gain on callback 970 and check callback 974 without refitting. **Result — PASS for this bounded landmark, verified by execution in MAME and offline analysis:** all eight mapped left-edge pixels changed on the composed screen. Four center-to-left edge shifts differed from the corresponding projected-X shifts by at most one pixel/word numerically. A gain fitted at callback 970 predicted the two callback-974 shifts within 0.48 and 1.94 screen pixels. This is a local, content-defined landmark, not a decoded road centerline or general camera calibration.

## Environment, captures and controls

**Verified by execution:** source baseline `f91881e` on `experiment/perspective-road`; macOS 26.6.2 x86_64; Python 3.14.8. Original arcade capture baseline: isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`, and callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Centered steering was 128; left pulse 64 began at callback 960. Exact upstream lookup-position words match at projection callbacks 968 and 972. Those positions correspond to the selected descriptors at 970/974 and composed screens at 971/975.

**Verified by execution:** the existing isolated MAME capture build (SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`) only wrote raw native bitmaps through callback 970. A copy of that local, already patched tree was made at `/private/tmp/pd-mame0289-landmark`; the original tree and upstream installation were untouched. The original [capture-only patch](../../tools/phase1b_mame_ybitmap.patch) remained in effect. A second [capture-window patch](../../tools/phase1b_mame_capture_974.patch), SHA-256 `63af2163801faf4059d0d794f814d90272469c7053bf44ff63c16db93a6aac2c`, changed only the capture-window upper bound from 970 to 974. `git apply --check --unidiff-zero` passed against the earlier local source. Rebuilding with `make SOURCES=src/mame/sega/segaybd.cpp NOWERROR=1 REGENIE=1 -j8` produced MAME 0.289 (`mame0289-dirty`) SHA-256 `9e54fdc4b5da5e5f7ba2308b35be157803ebe1d5a54d41ae28301c675bd0456d`. This patch only writes diagnostic bitmaps when `PDRIFT_YBITMAP_DIR` is set; it does not alter emulated game logic.

**Verified by execution:** the first four callback-970 center captures were made before extending the window; the remaining captures used the extended isolated build. The analyzer verified each new baseline composed screen was byte-identical to its prior unmodified MAME screen and each hidden screen was byte-identical to the corresponding earlier one-descriptor hide replay, across **8/8** cases. Each hidden run changed exactly one descriptor hide-bit byte and left the intervention-frame screen unchanged. These controls check that extending the capture window did not create the measured RGB effects.

**Verified by execution:** representative unmodified screen SHA-256 values are `b647f0e1f7393b463f3502b7e229a77ba3120f0c2034b1523f7a2f088a271533` for centered screen 971 and `715195b80c239ec96c450a6dd55c611e28d39f203755429c1d3729d01df64f78` for centered screen 975. Every case's unmodified/hidden screen, native bitmap and raw input-log checksum is recorded in the private result below.

The original runner/analyzer [phase1b_affine_landmark.py](../../tools/phase1b_affine_landmark.py) SHA-256 `f33e1948a71f834060a5dc7969ffafa67d2738619b8bce2b3ec755998d65be0c` uses owner-local captures only. Ignored `build/private/phase1b-affine-landmark-results.json`, SHA-256 `08f76205c4d7bd7b2fee8b5329887766365f9a40afd1843d23e3d875dbe1c116`, records every bitmap, screen and input-log checksum plus the predicted/observed pixels. No ROM, native bitmap, RGB screenshot or extracted graphic is tracked.

## Specified landmark and screen result

**Verified by execution:** for each descriptor, the landmark is the occupied native-bitmap span on row `native descriptor Y origin + 3`, selected before examining the new screens. For example, `$3400` at callback 970 uses native row 194; `$3600` uses row 189. The analyzer compares baseline and hidden 512×512 bitmap words to find that descriptor's causal occupied pixels, then maps those pixels through the captured **pre-swap** six-word affine block. It compares predicted composed-screen pixels against the independent baseline/hidden 320×224 RGB difference. The leftmost mapped pixel of the landmark was visibly changed in every case.

| Descriptor callback / depth | Native landmark row | Center → left mapped screen left X | Screen edge shift | Projected-X shift at callback `f−2` |
| --- | ---: | ---: | ---: | ---: |
| 970 / `$3400` | 194 | 101 → 120 | +19 px | +20 words |
| 970 / `$3600` | 189 | 115 → 129 | +14 px | +14 words |
| 974 / `$3400` | 198 | 84 → 127 | +43 px | +44 words |
| 974 / `$3600` | 191 | 109 → 138 | +29 px | +28 words |

**Verified by execution:** across the eight cases, the mapped landmark included **1,028** actual changed RGB pixels and **25** additional mapped pixels unchanged in the final composition. The full pre-swap bitmap-to-screen mapping covered all **13,626** changed RGB pixels, with zero misses and 627 additional mapped pixels. Substituting the post-swap block missed 549 changed RGB pixels in total, all in left-steering cases. Thus the landmark's left-edge match is supported by the correct render-stage timing, while the extra mapped pixels caution against equating sampled source occupancy with final RGB visibility everywhere.

**Verified by execution:** the callback-970 pairs fit a zero-intercept gain of `0.96644` screen pixels per arcade projected-X word for this chosen edge. Holding that gain fixed, the projected changes `+44` and `+28` predict callback-974 shifts `+42.52` and `+27.06` pixels; the observed shifts were `+43` and `+29`. Absolute errors are `0.48` and `1.94` pixels. This is a two-sample train/two-sample check, too small to establish a universal transform. The landmark is defined by the descriptor's occupied graphic data; center/left kept the same graphic word and horizontal draw direction in all four pairs, but zoom, affine parameters, overlap and shape may still change.

## Reproduction and engineering limit

With the owner-local ROM/state and an isolated copy of the previously patched MAME source, apply the tracked capture-window patch and rebuild:

```sh
git apply --check --unidiff-zero /absolute/repo/tools/phase1b_mame_capture_974.patch
git apply --unidiff-zero /absolute/repo/tools/phase1b_mame_capture_974.patch
make SOURCES=src/mame/sega/segaybd.cpp NOWERROR=1 REGENIE=1 -j8
python3 tools/phase1b_affine_landmark.py build/private run --mame /private/tmp/pd-mame0289-landmark/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_affine_landmark.py build/private analyze
python3 -m py_compile tools/phase1b_affine_landmark.py
```

Run `git apply` and `make` inside the **isolated MAME copy**; run the Python commands from this repository root. The runner reuses already valid 512×512 captures and writes new data only under ignored `build/private/`. The analyzer also checks the earlier baseline/hide screen hashes rather than trusting the new instrumentation alone.

**Inference from verified execution:** in this short centered-to-left comparison, the selected occupied left edge behaves approximately like a screen-space proxy for projected X at two depths and two matched-position epochs. The numerical agreement is substantially stronger than the whole-mask medians from the previous localization, precisely because this test fixes a named native row and edge before comparing. It does **not** imply one projected word equals one pixel for other graphics, steering directions, depths, epochs, or Sega CD output resolutions.

**Unsupported:** formal road-edge identity, physical camera position/units, vertical camera calibration, right-steering applicability after its graphic/direction switch, a direct mapping to a Sega CD 128×64 scanline, a predictive five-word command producer, arcade-hardware behavior, or stock Sega CD timing. No Sega CD image, second arcade emulator, or physical hardware was run.

**Next bounded test — hypothesis:** repeat this predeclared landmark across more *matched-position* epochs while the graphic and direction remain stable, then test whether the `0.96644` gain from the first epoch predicts those later shifts without tuning. If it fails, separate affine change, zoom and source occupancy contributions before revising the Sega CD curve lookup. Keep the five-word interface unchanged until a calibrated mismatch demands otherwise.
