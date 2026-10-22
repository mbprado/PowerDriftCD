# Phase 1B: causal arcade road-edge bands — 2026-10-22

**Question / hypothesis:** do two traced arcade depth records independently produce the visible sand-to-roadside edge on different screen rows, so that a depth-to-screen ordering can be measured before choosing Sega CD scanlines? **Baseline:** the [conditional viewport audit](2026-10-22-arcade-to-sega-viewport-audit.md) found a repeatable edge at Y=162 but could not assign it to a specific depth. **Acceptance:** use owner-local one-byte descriptor hides for `$3200`–`$3A00`, center/left steering, and callbacks 966/970/974; verify source-byte and prior-screen controls; record every row from 135–190 where the same sand-edge detector changes; separate visible strip support from the actual boundary response. **Result — PASS for two-depth causal ordering, INCONCLUSIVE for a Sega CD viewport mapping, verified by execution in isolated MAME 0.289 and offline analysis:** `$3400` and `$3200` control adjacent edge bands at callbacks 970 and 974. Farther selected descriptors remain visible but do not move this particular sand edge.

## Environment and intervention

**Verified by execution:** source baseline `4c2ab80` on `experiment/perspective-road`; macOS/Darwin 25.6.0 x86_64; Python 3.14.8. The six new `$3200` one-byte hides were replayed with the isolated MAME 0.289 (`mame0289-dirty`) capture build SHA-256 `9e54fdc4b5da5e5f7ba2308b35be157803ebe1d5a54d41ae28301c675bd0456d`, based on source revision `f34f02505e32c1993c6a782b6814232cbfc74e36` and the previously documented capture-only patches. The owner-local 53-file ROM manifest and callback-950 state remain SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Input used the same saved state, coin/start/pedal schedule, and center steering 128 or left pulse 64 from callback 960. No upstream MAME source, Sega CD renderer, ROM, or BIOS was changed.

**Verified by execution:** `tools/phase1b_nearest_depth_boundary.py` SHA-256 `209654c9fb9e825ee66501703b5bd3711a990f3f9eeb3ba8eb70e1f0e66e5fb1` uses the existing projection→shared-list→sub-CPU descriptor selection for depth `$3200`. It created six ignored 64 KiB source-RAM overrides, each setting exactly one hide bit, and ran six isolated MAME replays. The private plan SHA-256 is `ec5725bafa165f1b7d7d2ead8d2c5977fe954887326e4cd023df61f0c57d1357`. The existing 24 center/left hides for `$3400`–`$3A00` were reused.

**Verified by execution:** `tools/phase1b_causal_boundary_rows.py` SHA-256 `fa3f586cd1509bfeabaa125a14981c36dd4c6a4a280f4e22acbedf945966b9cc` verified all **30/30** center/left cases: the source RAM differs at only the selected byte; its hide bit is set; the intervention-frame screen matches baseline. A new center/974 `$3200` same-value replay left source RAM and screen 975 byte-identical to baseline; an independent hide repeat reproduced the original hidden source RAM and screen byte-for-byte. The earlier `$3400` one-byte and repeat controls remain documented separately. The screen-edge detector is unchanged: 16 leading sand RGB pixels `(214,214,132)`, then four consecutive non-sand pixels. An edge is reported only when the detector returns a position in both baseline and hidden screenshots on that row. Failure to report an edge does not imply no visible pixels changed.

## Causal row bands

**Verified by execution:** the following ranges are inclusive arcade **screen Y pixels**. “Changed support” means at least one RGB pixel changed after hiding the selected descriptor, anywhere across the 320-pixel row. “Edge rows” means the detected left sand boundary changed position. The scan for edge rows was fixed to Y=135–190. `$3200` is nearer in the traced ROM-depth ordering than `$3400`; that naming is an index ordering, not a decoded world-distance unit.

| Descriptor callback | Steering | `$3400` changed support / edge rows | `$3200` changed support / edge rows |
| --- | --- | --- | --- |
| 966 | Center | 140–147 / none | 147–169 / **153–169** (17 rows) |
| 966 | Left | 139–149 / none | 146–172 / **150–166** (17 rows) |
| 970 | Center | 143–154 / **154** (1 row) | 154–219 / **155–186** (32 rows) |
| 970 | Left | 142–160 / **149–152** (4 rows) | 152–223 / **153–190** (38 rows) |
| 974 | Center | 147–169 / **156–169** (14 rows) | 168–223 / **170–171** (2 rows) |
| 974 | Left | 147–181 / **150–167** (18 rows) | 167–223 / **168–190** (23 rows) |

**Verified by execution:** at callback 970, the two boundary bands meet at rows 154/155 centered and 152/153 left. At 974 they meet at 169/170 centered and 167/168 left. In the centered callback-974 image, hiding `$3400` moves the edge at row 162 from X=63 to X=90; hiding `$3200` does not move it there. This directly identifies the depth responsible for the earlier row-162 sand-boundary observation at that epoch. At callback 966, only `$3200` moves the measured edge, although `$3400` changes visible pixels above it.

**Verified by execution:** `$3600`, `$3800`, and `$3A00` each changed visible RGB pixels in the later cases but moved this *specific* sand edge on **0/18** tested side/epoch/depth combinations. `$3A00` changed no composed pixels at callback 966 under either steering condition despite a valid traced descriptor. Therefore “not an edge controller” is specific to this color/side detector and these frames; it does not mean those depths were not drawn or do not contribute to the road image.

**Inference from verified execution:** the visible sand edge is assembled from adjacent depth strips, and a given depth can cover many final screen rows. This yields a defensible local arcade depth-to-row **ordering and transition** for two depths. It is not a one-depth-to-one-row function. Clipping, car/HUD overlap, sprite composition and the edge detector's sand-color requirement limit the observed row bands. The `$3200` changed-pixel support extends below Y=190, while this experiment intentionally stops edge detection there; its lower endpoint is not measured.

**Verified by execution of the existing Sega CD host reference:** the original 128×64 synthetic road's stamp membership was checked at five output rows for all 60 existing five-word packets. Road widths in **Sega output pixels** were row 0: 10–11 (median 11), row 16: 10–16 (median 11), row 32: 16–22 (median 16), row 48: 21–32 (median 22), and row 63: 32 (median 32). This confirms a widening synthetic road in its own 64-row space. It is not a BlastEm timing result or an arcade width measurement. The arcade right sand border is not consistently exposed under left steering, so no like-for-like width progression or scale factor can be computed yet. The independently measured two-depth arcade row ordering can constrain a future visual crop, but cannot select a unique Sega output row per ROM depth by itself.

## Reproduction and next decision

From the repository root, with the owner-local ROM/state and isolated MAME build documented above:

```sh
python3 tools/phase1b_nearest_depth_boundary.py build/private prepare
python3 tools/phase1b_nearest_depth_boundary.py build/private run --mame /private/tmp/pd-mame0289-landmark/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_nearest_depth_boundary.py build/private controls --mame /private/tmp/pd-mame0289-landmark/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_causal_boundary_rows.py build/private
python3 -m py_compile tools/phase1b_nearest_depth_boundary.py tools/phase1b_causal_boundary_rows.py
```

**Verified by execution:** ignored `build/private/phase1b-causal-boundary-rows.json` SHA-256 `2b360eed5c6d50a613254b84ccb42348745df6ff7a55f0708d6cd8987802148d` records all 30 case-level screenshot/source checksums, changed-pixel counts by row, tested edge coordinates, sham/repeat controls, and synthetic host width statistics. No ROM, native bitmap, screenshot, commercial graphic or private startup code is tracked. This experiment did not run BlastEm, a second arcade emulator, or physical Sega CD hardware; it reports image pixels, not emulated hardware timing or host execution speed.

**Unsupported:** the physical camera's depth units, right-side road boundary across steering, road width progression at these rows, a unique crop into 128×64, and an arcade-to-five-word command producer. The right sand border is obscured or replaced in some left-steering frames, so the same exact-color detector cannot establish width across the whole interval. The existing synthetic Sega fixture has scale bands but no corresponding arcade geometry; matching a band boundary to these transition rows would be an unsupported assumption.

**Next bounded experiment — hypothesis:** use the now-causal `$3400`→`$3200` transition as a reference and inspect the right road edge or another width marker through native Y-sprite occupancy and pre-swap affine mapping, rather than relying on exact sand color. If both road sides can be attributed at the same rows, define a visual crop requirement (which road band must fit in 128×64) before revisiting an offline five-word adapter. Keep the Sega CD renderer unchanged until that comparison is measured.
