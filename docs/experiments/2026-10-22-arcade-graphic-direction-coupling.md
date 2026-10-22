# Phase 1B: graphic and direction coupling in a visible arcade strip — 2026-10-22

**Question / hypothesis:** can the right-steering `$3400` strip be compared with center/left using a common graphic-offset word, then yield a repeatable contour for a future Sega CD camera adapter? **Baseline:** the [matched-position depth trial](2026-10-21-arcade-near-depth-visibility.md), with private callback-950 MAME state, held pedal, and the same center/left/right steering inputs. **Acceptance:** make bounded descriptor-only replays at callbacks 970 and 974, verify exact changed RAM bytes and prior screens, and inspect both composed screens and the native Y-sprite bitmap where captured. **Result — INCONCLUSIVE for a common-source camera contour, verified by execution in MAME:** the right descriptor's graphic offset, horizontal draw direction, and X origin are coupled. Forcing its graphic offset alone almost eliminates its visible contribution. Changing the offset and direction together moves the contribution to the far right. Natural, unmodified descriptor visibility still provides one contiguous native-bitmap span at callback 970 for each steering condition.

## Environment and reproduction

**Verified by execution:** baseline source revision `0ea5bf03f9c10689302ca44284950e12c9560593` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 (`mame0289-dirty`) built from revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing [capture-only bitmap patch](../../tools/phase1b_mame_ybitmap.patch). The owner-local 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. This is emulator evidence, not original-hardware performance or compatibility.

**Documented only:** [MAME 0.289's Y-Board sprite renderer](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/sega16sp.cpp#L1144-L1210) identifies descriptor word at byte offset `+6` as the sprite-bank graphic offset, byte offset `+2` as the X origin relative to `$600`, and bits `$2000` and `$1000` of the word at byte offset `+A` as horizontal flip and left/right draw direction. The renderer reads graphic words in opposite directions depending on the flip bit. This description is of MAME's implementation; the private interventions below tested its observable behavior for this game.

**Verified by execution:** original tool [phase1b_fixed_graphic_strip.py](../../tools/phase1b_fixed_graphic_strip.py) SHA-256 `50be25b7627150b45406a4ddd5cab2eb331dac1503a782e67eeaee48b1a22ec5` prepared private full-RAM copies and replayed just the selected descriptor slot. Reproduce from the repository root using the same owner-local state and ROM set:

```sh
python3 tools/phase1b_fixed_graphic_strip.py build/private prepare
python3 tools/phase1b_fixed_graphic_strip.py build/private run --mame /private/tmp/pd-mame0289-source/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_fixed_graphic_strip.py build/private analyze
python3 tools/phase1b_fixed_graphic_strip.py build/private native970 --mame /private/tmp/pd-mame0289-source/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_fixed_graphic_strip.py build/private analyze-native
```

The last two commands repeat only callback-970 trials with the existing native Y-sprite bitmap capture enabled. That isolated MAME patch captures bitmap frames 960–970, so callback 974 has composed-screen evidence but no native bitmap here. **Verified by execution:** private plan SHA-256 `6d244daee48e3dee43bdc29c05c08c3a3af9f5763e4f67ca12f7caefa6cb6a2c`; composed-screen results JSON SHA-256 `9d80f14ee916a6d7b3e4db16278aee4733ccc35f740786dff6dc19fb9f91e367`; native-bitmap results JSON SHA-256 `25e44ab2d82db9596a2029c77fbbf51183fb47a595482e705d6068b666f49280`. The ignored private `phase1b-fixed-graphic-inputs/log-sha256.txt` covers 16 relevant replay logs and has SHA-256 `03d3943ffd60cb58d3b09eb69cd569ae8a07835d7685a4248ee86f46767d6adc`. All RAM copies, bitmap captures, images and logs stay under ignored `build/private/`.

## What changed and what was observed

**Verified by execution:** at descriptor callback 970, center/left used graphic word `$3888` and direction word `$72AA`; right used `$3898` and `$42AA`. At callback 974 the corresponding direction words were `$7210` and `$4210`. Thus the right direction differs by `$3000`, changing both horizontal flip and draw direction. At callback 970 the descriptor's X-origin words were center `$06AB`, left `$06BB`, and right `$0768`; relative to MAME's `$600` origin these are 171, 187, and 360 native-bitmap pixels. Keeping the right X origin while making it draw to the right starts the transformed sprite near native X 360, explaining the far-right fragment without implying an arcade camera shift.

**Verified by execution:** each callback-970/974 fixed-offset replay changed only the low byte of the graphic word; each paired replay additionally changed only the high byte of the direction word. Their corresponding hidden replays additionally set one hide-bit byte. All composed screens through the intervention callback remained byte-identical to their natural baseline. A callback-970 same-value right override left source RAM and next screen unchanged; repeating the callback-974 fixed-offset trial reproduced its after-RAM and next screen byte-for-byte.

| Right descriptor intervention | Callback 970: descriptor contribution on screen 971 | Callback 974: contribution on screen 975 |
| --- | ---: | ---: |
| Natural `$3898` + leftward `$42xx` | 1,406 changed pixels when hidden | 4,191 changed pixels when hidden |
| Graphic `$3888` only, direction still leftward | 3 changed pixels when hidden | 46 changed pixels when hidden |
| Graphic `$3888` + rightward `$72xx`, right X origin retained | 634 changed pixels when hidden, x271–319 | 615 changed pixels when hidden, x278–319 |

These are composed 320×224 RGB-screen differences between each visible replay and its own hidden counterpart, not sprite areas or timings. **Verified by execution:** at callback 970 the corresponding native 512×512 bitmap differences were 1,404 pixels for natural right, 3 for graphic-only, and 1,026 for the paired change. The paired bitmap contribution was x371–433, whereas the natural right contribution was x167–348. The changed graphic did not create an equivalent centered strip at the same right X origin.

**Verified by execution:** hiding the *natural* `$3400` descriptor at callback 970 gave these native-bitmap contributions. Each has a single contiguous changed run on native row 194:

| Steering | Native changed pixels | Native bounding box | Row 194 changed span |
| --- | ---: | --- | --- |
| Center | 1,610 | x182–358, y191–202 | x197–341, 145 contiguous pixels |
| Left | 1,752 | x197–378, y191–203 | x213–365, 153 contiguous pixels |
| Right | 1,404 | x167–348, y191–202 | x182–303, 122 contiguous pixels |

**Inference from verified execution:** the natural row-194 span is a repeatable *visible descriptor contribution* in native Y-sprite coordinates. Its changed-pixel boundaries move with steering, but width and source content also change. The row endpoints are **not established** as physical road edges, calibrated camera positions, or a constant-source contour. Native Y-sprite coordinates still pass through rotation, clipping and composition before becoming screen pixels. Many composed-screen rows have gaps; even their extreme changed pixels cannot simply be called track boundaries.

## Decision

**Verified by execution:** simple graphic-word normalization failed, and pairing that word with horizontal direction produced a different visible fragment because the right descriptor retained its different X origin. The report preserves the measured natural spans without altering the Sega CD camera interface or renderer. The [previous depth analyzer](../../tools/phase1b_near_depth_visibility.py) still passed its center regression check; this tool passed Python compilation and the staged whitespace check.

**Hypothesis for the next bounded test:** use the natural descriptor's own X origin, direction, zoom, and the captured rotation transform to predict its visible span before trying to fit Sega CD camera controls. Validate predictions against several native rows and composed-screen observations under all three steering conditions. If different source content or overlap prevents a stable contour, seek another track section or use projection-coordinate traces as the adapter target. Do not force a common graphic source by manually relocating the sprite; that would prescribe the displacement the camera study is meant to measure.

**Not run / unsupported:** a complete road contour, a physical world-to-camera calibration, a Sega CD adapter, second arcade emulator, and physical hardware. No arcade ROM, extracted graphic, BIOS, or private RAM/bitmap/screenshot was added to Git.
