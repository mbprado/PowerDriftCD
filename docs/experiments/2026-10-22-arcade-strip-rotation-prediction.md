# Phase 1B: natural strip rotation prediction — 2026-10-22

**Question / hypothesis:** can the natural `$3400` descriptor and the captured Y-Board rotation state predict where that strip's visible contribution reaches the composed screen, without forcing a common graphic source? **Baseline:** the [graphic/direction coupling experiment](2026-10-22-arcade-graphic-direction-coupling.md), the owner-local callback-950 state, held pedal, and the existing center/left/right steering inputs. **Acceptance:** at two descriptor epochs, verify each descriptor's geometric envelope, map the measured native Y-sprite contribution through the captured affine block, and compare every predicted screen pixel with the one-descriptor hide replay. **Result — PASS for the native-to-screen mapping, verified by execution in MAME:** the pre-swap rotation block predicted all 7,083 observed changed screen pixels across six cases, with 60 additional mapped pixels that did not change in the composed RGB image. This is a rendering-stage validation; it is not a descriptor-only texture generator, track-edge decoder, or Sega CD camera adapter.

## Source, environment and method

**Verified by execution:** baseline source revision `9fffc1303aa7b16f7ff31dc9a16d55d43115c602` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 (`mame0289-dirty`) from source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, using the existing [capture-only Y bitmap patch](../../tools/phase1b_mame_ybitmap.patch). The owner-local 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No physical hardware or second arcade emulator was used.

**Documented only:** [MAME's Y-Board sprite renderer](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/sega16sp.cpp#L1144-L1210) gives descriptor X/Y origins, height and draw direction. [MAME's rotation renderer](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/segaic16.cpp#L1394-L1442) samples the 512×512 Y-sprite bitmap using six signed fixed-point values from the buffered rotation RAM, with a `+27` screen-X adjustment. The original tool [phase1b_strip_rotation_prediction.py](../../tools/phase1b_strip_rotation_prediction.py), SHA-256 `84ba8d87382cc8bd5ff1edda2fc7ffe915674c3a533198343101c54c7583d767`, applies that source-coordinate equation to the captured pre-swap block and to a native contribution mask measured by hiding only the selected descriptor.

**Verified by execution:** each frame/side replay selected the `$3400` descriptor by projection → shared list → sub-CPU-X load identity. It saved a same-value baseline and a hide-bit variant at descriptor callbacks **966 and 970**, then compared native Y-sprite bitmap frames 966/970 with composed screen frames **967 and 971**. A single source-RAM byte changed in every hide replay; all preceding composed screens were byte-identical. The tool also checks that every changed native-bitmap pixel lies in the half-plane and vertical extent prescribed by the natural descriptor origin, direction and height. The private bitmap, RAM, screenshot and log data remain ignored under `build/private/`.

Reproduce with the existing owner-local state/ROM set and MAME build:

```sh
python3 tools/phase1b_strip_rotation_prediction.py build/private run --mame /private/tmp/pd-mame0289-source/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_strip_rotation_prediction.py build/private analyze
```

**Verified by execution:** private `phase1b-strip-rotation-prediction/results.json` SHA-256 `dfd04faf4047677fa39358971eaef0f5f96384b734987d1a765ac9699fa84e4e`; private manifest `phase1b-strip-rotation-prediction/log-sha256.txt` covers the 12 replay logs and has SHA-256 `540d9600e7dd3e5d1bf93aab9d6137d798ecd3bb36342c8023ed2996e5726248`. The JSON also records baseline source-RAM, native-bitmap and composed-screen SHA-256 per case. These private artifacts contain or derive from owner-local commercial data and are not tracked.

## Prediction versus observed screen contribution

The “predicted” set comprises screen pixels whose affine-mapped source coordinate lands on a *changed* pixel of the captured native Y-sprite bitmap. It does not decode the sprite ROM graphic stream itself. “Observed” is a changed RGB pixel in the composed-screen hide comparison. Counts are MAME pixels, not hardware timings.

| Descriptor frame / steering | Natural native bitmap pixels | Predicted screen pixels with pre-swap block | Observed screen pixels | False positives / false negatives |
| --- | ---: | ---: | ---: | ---: |
| 966 center | 796 | 796 | 796 | 0 / 0 |
| 966 left | 798 | 798 | 798 | 0 / 0 |
| 966 right | 784 | 785 | 785 | 0 / 0 |
| 970 center | 1,610 | 1,610 | 1,609 | 1 / 0 |
| 970 left | 1,752 | 1,748 | 1,689 | 59 / 0 |
| 970 right | 1,404 | 1,406 | 1,406 | 0 / 0 |
| **Total** | **7,144** | **7,143** | **7,083** | **60 / 0** |

**Verified by execution:** using the *post*-swap block instead missed 385 observed pixels across the six cases, including 92/74 misses for left/right at frame 966 and 137/82 at frame 970. The pre-swap block's complete recall therefore also checks the timing choice. The 60 pre-swap false positives are source pixels sampled by rotation but unchanged in the final RGB composition; **hypotheses** include later sprite overlap, priority and equal final colors. This test did not isolate which cause applies to each pixel.

**Verified by execution:** descriptor geometry agrees with the changed native bitmap. At frame 966 the native origins were center `(186,188)`, left `(187,188)`, right `(184,188)`; each drew rightward and down with height 38 and graphic word `$3888`. At frame 970 the origins were center `(171,191)`, left `(187,191)`, right `(360,191)`; center/left drew rightward with `$3888`, while right drew leftward with `$3898`; each had height 46. These are native 512×512 Y-sprite coordinates after subtracting MAME's `$600` origin, not world-space track coordinates or Sega CD display positions.

**Verified by execution:** on native row 194 at frame 970, the hide contribution was contiguous at x197–341 (center), x213–365 (left), and x182–303 (right). On composed-screen row 150, changed pixels occupied x91–251 (156 changed, two groups) for center, x105–259 (155 contiguous) for left, and x85–204 (120 contiguous) for right. The affine map accounts for their placement without treating these extremes as formal road edges.

## Interpretation and next action

**Inference from verified execution:** for this short section, captured rotation and natural native strip occupancy are sufficient to predict where the selected descriptor *can* affect the screen. The mismatch is limited to final composition, not an unexplained steering-dependent screen displacement. The descriptor envelope alone cannot predict the exact occupied native pixels: source graphic data, indirection, scanline clipping and overlap still matter. The natural strip changes graphic offset and horizontal direction in the right run, as established in the preceding report.

**Hypothesis for the next bounded experiment:** trace the natural rotation block and descriptor geometry across a longer, fixed track window at several depths, then seek a source-independent projected road/camera quantity that the existing five-word Sega CD command can represent. Validate against the measured screen spans; if the spans remain content- or overlap-dependent, use the upstream projection-coordinate trace rather than pixel extrema as the adapter target. Do not alter the current Sega CD camera interface until an unmet degree of freedom is demonstrated.

**Unsupported:** a complete track contour, physical road-width calibration, the original arcade camera pose, a Sega CD camera fit, and stock Sega CD frame-rate/compatibility conclusions. The previous depth analyzer passed its right-steering regression check, this tool passed Python compilation, and the staged diff passed whitespace validation.
