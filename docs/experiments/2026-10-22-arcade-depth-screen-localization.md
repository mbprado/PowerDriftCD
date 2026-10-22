# Phase 1B: causal depth-to-screen localization — 2026-10-22

**Question / hypothesis:** where do four traced depth records actually contribute to the arcade screen, and can their steering response calibrate the previous Sega CD camera-shape comparison? **Baseline:** owner-local center/left/right callback-950 MAME captures and the previously verified one-byte descriptor-hide replays. **Acceptance:** pair the correct projected position with each later descriptor, verify every intervention, measure vertical screen support and at least two lateral displacements with a fixed graphic/direction control, and avoid treating a deformed visible mask as a camera coordinate. **Result — PASS for localization, INCONCLUSIVE for a screen-pixel calibration, verified by execution of private capture analysis:** all 36 projection/list/descriptor/hide cases were identified and their visible screen contributions measured. The depth order is stable, but changed-pixel medians and whole-mask translations disagree enough that a single arcade-projection-word-to-screen-pixel gain is not established.

## Timing correction and provenance

**Verified by execution:** the [previous offline camera-shape audit](2026-10-22-arcade-to-sega-camera-shape-audit.md) used projected X at `f+2` for projection callback `f`. The shared-list record displayed from descriptor callback `f+2` actually contains the projected X/Y sampled **at `f`**. The new analyzer checks that position against a unique Y-sprite-type shared-list record for all 36 cases. We corrected and reran the prior analyzer before comparing any screen pixels. Its corrected held-out inverse-fit RMSE is **9.92** or **8.67** arcade projected-X words under the two assumed row maps, versus **5.14** for a flat-shift control. The originally reported 7.14/10.55 values were one display epoch late and are superseded. The corrected private audit JSON SHA-256 is `de1c78b8d2653a17919ca92128efe1d15a1aa120f00208e9a52c39b075d651e0`; corrected analyzer SHA-256 `93938322d25cedb9e94b238b2ed89eb5b4c9350caddf2f903e2df6207f946554`.

**Verified by execution:** source baseline `4951f59` on `experiment/perspective-road`; macOS 26.6.2 x86_64; Python 3.14.8. The reused arcade captures were produced with isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, the owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`, and callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The MAME build includes only the previously documented bitmap-capture patch. No new emulator replay, Sega CD build, test image, second emulator, or physical hardware test was performed here.

**Verified by execution:** the new original analyzer `tools/phase1b_depth_screen_localization.py` SHA-256 `551a734ff52bbba3f5953a940417be01e459cf515dfd699fa9324f1d0bf09968` reads the prior [near-depth](2026-10-21-arcade-near-depth-visibility.md) and [matched far-depth](2026-10-21-arcade-matched-far-depth-visibility.md) hide replays. It verifies that each hide changes exactly one source-RAM byte and that the intervention-frame screen still equals baseline. Those earlier analyzers were rerun and again verified all **27/27 near** and **9/9 far** one-byte interventions, prior-screen controls, and repeat/sham controls. The exact upstream lookup-position marker is equal across steering runs at the three selected projection callbacks 964, 968, and 972. This does not hold all camera state equal.

The private result `build/private/phase1b-depth-screen-localization.json` has SHA-256 `cba4bf77e2412fb99008718819638f65fc1d388d3f9f868bd88865e2fea99126`. It records 36 per-descriptor screen supports, source-screen hashes, native descriptor origins, graphics/direction, and pairwise steering comparisons. No commercial source data or screenshot is tracked.

## Screen localization and lateral comparison

**Verified by execution:** the table shows callback-971/975 centered median **screen Y** from pixels that changed when only that descriptor was hidden. The projection shift is the left-minus-center main-CPU X word at callbacks 968/972, respectively. “Native origin” is the left-minus-center X-origin field in MAME's 512×512 Y-sprite plane. “Screen median” subtracts the median X of the two causal RGB-change masks. “Mask translation” shifts the centered mask to maximize pixel overlap with the left mask, allowing a small vertical shift; its F1 score records how much shape remains comparable. All shifts are signed pixel/word differences, not world-space distances. Center and left used the same graphic word and horizontal direction in all **12/12** depth/epoch comparisons; zoom, rotation and composition were not fixed.

| Arcade depth | Screen 971 center median Y | 971 projected / native / screen-median / mask-shift X | Screen 975 center median Y | 975 projected / native / screen-median / mask-shift X |
| --- | ---: | ---: | ---: | ---: |
| `$3400` | 148 | +20 / +16 / +21 / +11 (F1 .78) | 158 | +44 / +39 / +31 / +26 (F1 .74) |
| `$3600` | 140 | +14 / +11 / +13 / +9 (F1 .66) | 144 | +28 / +24 / +24 / +18 (F1 .60) |
| `$3800` | 137 | +11 / +9 / +15 / +16 (F1 .38) | 139 | +20 / +17 / +25 / +15 (F1 .36) |
| `$3A00` | 136 | +9 / +7 / +12 / +12 (F1 .48) | 136 | +15 / +13 / +9 / +20 (F1 .26) |

**Verified by execution:** at earlier screen 967 the centered median Y values were 144/139/136 for `$3400/$3600/$3800`; `$3A00` caused no changed composed-screen pixels for any steering side. This confirms that a valid projection/list/descriptor identity need not provide a visible screen landmark. At screen 971, the centered vertical supports were `$3400`: rows 143–154, `$3600`: 138–143, `$3800`: 137–138, and `$3A00`: 135–136. The near-to-far order persists at screen 975, while the near strip broadens to rows 147–169. These are descriptor contributions under final composition, not a unique road centerline row.

**Inference from verified execution:** `$3400` and `$3600` give useful, independently visible lateral checks at the same matched-position epochs; their native descriptor origins move roughly with the upstream projected X words. But a single screen-pixel gain is not yet defensible. For example, at screen 971 `$3400` moves +20 projected words, +21 changed-pixel median X, but only +11 pixels under best whole-mask translation (F1 .78). At screen 975 its changed mask reaches the right screen edge, and its +44 projected-word change corresponds to +31 median X or +26 best-mask shift. The farther strips are small and less stable. The differing measurements reflect changing occupancy, affine rotation, overlap and clipping; this experiment does not assign a fraction to each mechanism.

**Verified by execution:** right steering retained the same graphic and horizontal direction only at descriptor callback 966. At 970/974 it chose different graphic words and direction for the selected strips, so left/right mask displacement is not a controlled pure-camera comparison at those epochs. Those results remain in the private JSON as observations, excluded from the calibration table.

## Reproduction and decision

```sh
python3 tools/phase1b_camera_shape_audit.py build/private
python3 tools/phase1b_depth_screen_localization.py build/private
python3 tools/phase1b_near_depth_visibility.py build/private analyze
python3 tools/phase1b_matched_far_depth.py build/private analyze
python3 -m py_compile tools/phase1b_camera_shape_audit.py tools/phase1b_depth_screen_localization.py
```

**Unsupported:** a unique arcade road-edge/centerline pixel for these records, a fixed world-to-screen scale, a calibrated mapping into the Sega CD 128×64 viewport, predictive five-word camera commands, stock Sega CD timing, or physical hardware behavior. The previous audit's evenly spaced Sega output-row hypotheses `(56,40,24)` and `(48,32,16)` should remain hypotheses; observed arcade contribution rows are much more compressed and change over time. The Sega CD camera interface and renderer remain unchanged.

**Next bounded test — hypothesis:** use the already validated native-bitmap-to-screen affine map to predict a **specified landmark** (for example the `$3400` descriptor origin or a repeatable occupied edge) through callbacks 968 and 972. Check its prediction independently on the composed screen and across two depths before adopting a single pixel scale. If the landmark remains content-dependent, keep the projected words as the reference signal and test a revised offline curve lookup within the existing five-word packet, rather than expanding the interface.
