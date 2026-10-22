# Phase 1B: bounded arcade road-width landmark — 2026-10-22

**Question / hypothesis:** can the `$3400`/`$3200` causal left-edge bands be paired with a reproducible right-side road landmark, using native Y-sprite occupancy and the validated pre-swap affine map rather than assuming the exact sand color survives every steering case? **Baseline:** the [two-depth causal edge bands](2026-10-22-arcade-causal-road-edge-bands.md). **Acceptance:** capture native bitmap baseline/hidden pairs for the new `$3200` hides at callbacks 970/974; reuse prior `$3400` captures; verify source/screens against the original one-byte replays; map changed native pixels into screen space; distinguish a mapped strip extent from a visible outer sand boundary; measure width only where both sides are independently detectable. **Result — PASS for a centered seven-row width landmark, INCONCLUSIVE for a steering-wide width sequence, verified by execution:** at centered callback 974, `$3400` provides both causal left and right sand edges on rows 156–162, and the visible road region widens from 223 to 241 arcade pixels. Most nearer-strip right extents clip at X=319, and the right sand border is not consistently available under left steering.

## Environment, controls and mapping

**Verified by execution:** source baseline `9cb7610` on `experiment/perspective-road`; macOS/Darwin 25.6.0 x86_64; Python 3.14.8. Eight new centered/left, baseline/hidden native-bitmap replays for `$3200` at callbacks 970/974 used the isolated MAME 0.289 (`mame0289-dirty`) executable SHA-256 `9e54fdc4b5da5e5f7ba2308b35be157803ebe1d5a54d41ae28301c675bd0456d`, based on source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`. `$3400` native bitmap pairs were reused from the [affine landmark experiment](2026-10-22-arcade-affine-landmark.md). The owner-local ROM manifest/state checksums and input schedule remain those in the [causal edge report](2026-10-22-arcade-causal-road-edge-bands.md). No upstream MAME source or Sega CD renderer was modified, and no physical hardware was tested.

**Verified by execution:** `tools/phase1b_right_extent.py` SHA-256 `274c2e2383c32b04253b2aae027c57c419ded7587221516f2f3d5aa45d6bf268` checks all **8/8** depth/steering/epoch cases. Each new native capture reproduced the earlier unmodified/hidden composed screens byte-for-byte; the baseline replay retained the original source RAM, and the hidden replay retained exactly the prepared one-byte override. The script differences the 512×512 native bitmaps, maps each changed native pixel through the **pre-swap** affine block to the 320×224 screen, and compares the prediction with the independent composed RGB difference. Across all eight cases, **zero** changed screen pixels were missed by the mapping. Extra mapped pixels remained unchanged after final composition, so mapped occupancy is not always visible.

**Verified by execution:** an outer right sand boundary is accepted only when the last 16 screen pixels equal RGB `(214,214,132)` and a scan inward finds four consecutive non-sand pixels. The earlier left detector imposes the mirrored leading-sand condition. A measured width additionally requires the native-mapped `$3400` strip's *visible rightmost changed pixel* to coincide with that independently detected right boundary on the same row. These conditions avoid calling any arbitrary rightmost changed pixel a road edge. The accepted window was found during this exploratory audit; it is not a pre-registered prediction.

## Measured width and failure modes

**Verified by execution:** centered callback 974, composed screen 975, `$3400` descriptor graphic `$3888`:

| Arcade screen Y | Causal left sand edge X | Causal right sand edge X | Inclusive road-region width |
| ---: | ---: | ---: | ---: |
| 156 | 72 | 294 | 223 px |
| 157 | 70 | 296 | 227 px |
| 158 | 68 | 298 | 231 px |
| 159 | 67 | 299 | 233 px |
| 160 | 66 | 300 | 235 px |
| 161 | 65 | 301 | 237 px |
| 162 | 63 | 303 | 241 px |

**Verified by execution:** the rightmost native-mapped pixel and independently changed RGB pixel equal the right sand boundary in all **7/7** listed rows. The left sand edge is also causally moved by the same `$3400` hide on those rows, as recorded in the previous report. The width is the distance between visible sand-to-non-sand boundaries, inclusive, and may include shoulders; it is not decoded asphalt width or world-space track width. It grows by 18 arcade screen pixels across six vertical row steps. At this epoch, the measured region occupies approximately 70–75% of the 320-pixel arcade screen; this fraction is contextual, not a prescribed Sega CD scale.

**Verified by execution:** the `$3200` mapped right extent reaches X=319 in **30/32** centered callback-970 edge rows and **2/2** centered callback-974 edge rows. Under left steering it clips in **27/38** callback-970 and **9/23** callback-974 rows. A clipped extent cannot locate the underlying outer edge. For the four left-steering/epoch/depth cases, **0** tested causal edge rows passed the strict right-sand-boundary coincidence check. Some visible rightmost pixels are genuine mapped strip pixels, but adjacent scenery, palette changes and final composition prevent classifying them as the outer road edge. At callback 974 the `$3400` right extent remains inside the screen in all 14 centered and 18 left edge rows, yet only the seven centered rows above have an independent outer-sand confirmation. This is a bounded width sample, not a full steering-dependent width trajectory.

**Inference from verified execution:** the road's visible width in this centered arcade section is much larger, as a fraction of image width, than the current synthetic Sega CD stamp fixture (at most 32/128 output pixels in its 60 host-reference packets, as measured in the [causal edge report](2026-10-22-arcade-causal-road-edge-bands.md)). The two width definitions are visually related but not identical, and no arcade-to-Sega vertical row registration is calibrated. Thus this contrast identifies a **geometry target to investigate**, not a demonstrated inadequacy of the five-word packet or a hardware-performance limit. A faithful adapter cannot be judged from lateral center shifts alone while the fixture road remains so narrow.

## Reproduction and decision

```sh
python3 tools/phase1b_right_extent.py build/private run --mame /private/tmp/pd-mame0289-landmark/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_right_extent.py build/private analyze
python3 -m py_compile tools/phase1b_right_extent.py
```

**Verified by execution:** ignored `build/private/phase1b-right-extent.json` SHA-256 `8fa498e5df91b75330890050bf3b46f1b8973af12bcfd482f1cfbe365b5a67d0` stores case-level native bitmap/screen checksums, mapped/visible counts, right clipping, right-sand checks and row-by-row widths. The original-only Sega CD boot issue and physical-hardware timing are unchanged. No ROM, native bitmap, screenshot, extracted commercial asset, BIOS or private startup prefix is tracked. This experiment did not run BlastEm or a second arcade emulator; all new values are image pixels from isolated MAME and offline mapping, not wall-clock or emulated-hardware timing.

**Unsupported:** a usable arcade right edge under the full steering sequence, a full width trajectory, a uniquely justified 128×64 crop, direct matching of arcade and Sega road-width definitions, original camera units, a predictive five-word command producer, and stock Sega CD hardware behavior.

**Next bounded experiment — hypothesis:** use the seven-row centered width reference and the two-depth left-edge transition to define a visual target for an **original-asset, host-only** 128×64 road fixture with a substantially wider near road. Fix a crop explicitly (which arcade rows must remain visible) and compare its row-by-row width and edge motion before building a new Sega CD disc. Only if that host target is representable and valuable should ASIC/VDP timing be remeasured in BlastEm; keep the current verified 30 Hz milestone intact.
