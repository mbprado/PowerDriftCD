# Phase 1B: conditional arcade-to-Sega viewport audit — 2026-10-22

**Question / hypothesis:** can an independently visible arcade road boundary support the two-depth landmark's lateral signal, and does choosing an explicit arcade-to-128×64 screen registration resolve the earlier synthetic camera-shape mismatch? **Baseline:** the [three-epoch affine landmark](2026-10-22-arcade-affine-landmark-extension.md) and unchanged [128×64 Sega CD road prototype](2026-10-20-wide-live-road-pipeline.md). **Expected evidence:** screen-image checks independent of the traced projected-X words; fixed, disclosed crop/scale scenarios; an exact host-model control; separate inverse-fit and flat-shift results. **Result — PASS for an independent arcade boundary check, INCONCLUSIVE for a calibrated arcade-to-Sega adapter, verified by execution:** a visible sand-to-roadside edge moves with the near `$3400` landmark at three epochs. The current Sega synthetic model's apparent fit changes substantially with the vertical screen registration, so neither the old 16-row depth spacing nor a new unique mapping is justified.

## Inputs and controls

**Verified by execution:** source baseline `7143fe5` on `experiment/perspective-road`; macOS/Darwin 25.6.0 x86_64; Python 3.14.8. Arcade screenshots, affine data, local MAME 0.289 build, ROM/state checksums, and one-byte hide controls are documented in the [landmark extension](2026-10-22-arcade-affine-landmark-extension.md). This test reused those captures; it did **not** launch MAME, BlastEm, or physical hardware, build a disc, or modify any Sega CD source. The owner-local landmark result SHA-256 is `23d3b85f192fb3d0a07fef2f7b92927eb4d06ca923886804cd58c0aa759b543c`. The original analyzer `tools/phase1b_viewport_audit.py` is SHA-256 `83b02f176e4bc434d2e69b821f5623c725e703868629869979cb1970ae24fa8f`.

**Verified by execution:** the new analyzer checks each baseline composed-screen SHA-256 against the previous landmark result, then samples arcade screen row 162 with the existing exact-RGB sand-boundary detector. Its fixed criterion is 16 leading pixels of RGB `(214,214,132)`, followed by four consecutive non-sand pixels. It is a **sand-to-roadside image edge**, not a decoded road centerline or a unique 3D point. This row was selected from the earlier road-edge experiment; it was not chosen by minimizing the fit below. The 320×224 screenshots are owner-local and ignored.

| Descriptor callback / composed screen | Center → left sand edge at Y=162 | Sand-edge shift | `$3400` mapped landmark-edge shift | `$3600` landmark-edge shift |
| --- | ---: | ---: | ---: | ---: |
| 966 / 967 | 63 → 64 | +1 px | +2 px | +2 px |
| 970 / 971 | 46 → 65 | +19 px | +19 px | +14 px |
| 974 / 975 | 63 → 101 | +38 px | +42 px | +29 px |

**Inference from verified execution:** the independent visible boundary and the `$3400` descriptor edge have a similar lateral response over this short steering sequence, especially at callback 970. They are different image features at different Y rows; the 4-pixel difference at callback 974 and the smaller `$3600` shifts prevent treating them as one rigid camera coordinate. The repeated centered sand-edge value 63 at callbacks 966 and 974 while the landmark changes also shows that local road content and composition matter.

## Conditional Sega CD registration

**Hypothesis / design scenarios, not calibration:** the arcade 320-pixel screen is reduced to a 128-pixel target, fixing horizontal shift scale at `128/320 = 0.4`. Two vertical registrations are tested without tuning either to the lateral fit: `full_screen` maps arcade rows 0–223 to Sega rows 0–63; `road_crop` maps the visually selected arcade road band 133–169 to Sega rows 0–63. The latter crop is a plausible display-design choice, not a traced shared-depth correspondence. Each epoch uses the *centered* arcade landmark Y to select one fixed Sega row per depth for both steering conditions. The existing prototype does not contain the original arcade road geometry, so neither registration is independently established as equivalent scene content.

**Verified by execution of the host reference:** the analyzer enumerates the currently implemented curve phase 0–95, signed bank −2…2, and horizon 1–7 for each center and left packet. At each specified row it computes the leftmost synthetic road pixel from the original road stamp's source-X range 128–143. This reduced visible-road-edge model was checked against `live_camera_lines()` for all 60 existing five-word packets at four distinct rows in each registration: **240/240 exact checks per registration**. Ridge and texture control words affect appearance but not this road-membership edge in the current fixture. This is a host-model result, not a fresh ASIC or VDP measurement.

**Verified by execution:** the following residuals are in **Sega output pixels** after the stipulated 0.4 horizontal reduction. Each epoch independently chooses the best center and left curve/bank/horizon packets using *that epoch's target*; even the last epoch is inverse-fitted and is **not** a held-out prediction or a camera-command producer. The flat control uses the best constant lateral shift over the two depths. Two targets and freely chosen packets make low inverse-fit error an optimistic representation bound, not evidence of a robust adapter.

| Registration / callback | Sega rows `$3400/$3600` | Target shifts | Best model shifts | Model RMSE | Flat RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full screen / 966 | 40 / 39 | 0.8 / 0.8 | 1 / 1 | 0.20 | 0.00 |
| Full screen / 970 | 41 / 39 | 7.6 / 5.6 | 8 / 6 | 0.40 | 1.00 |
| Full screen / 974 | 42 / 40 | 16.8 / 11.6 | 16 / 12 | 0.63 | 2.60 |
| Road crop / 966 | 14 / 10 | 0.8 / 0.8 | 1 / 1 | 0.20 | 0.00 |
| Road crop / 970 | 19 / 10 | 7.6 / 5.6 | 8 / 6 | 0.40 | 1.00 |
| Road crop / 974 | 26 / 14 | 16.8 / 11.6 | 13 / 12 | 2.70 | 2.60 |

**Inference from verified execution:** full-screen registration compresses the two arcade depths to only one or two Sega rows apart, making a good fit relatively easy. The road-only crop separates them by 4–12 rows and exposes a structured mismatch at callback 974. The current five-word packet is therefore neither validated nor disproved by this screen-space exercise. The assumed crop changes the question being asked, and there is still no independently measured depth-to-Sega-row correspondence. The earlier audit's 16-row separation is also uncalibrated, not a result to average with these scenarios.

## Reproduction, limits, next decision

```sh
python3 tools/phase1b_viewport_audit.py build/private
python3 -m py_compile tools/phase1b_viewport_audit.py
```

**Verified by execution:** ignored `build/private/phase1b-viewport-audit.json` has SHA-256 `424b0c88fd3203dbd2065706735d190f4b98b2d68ca32528ecb850acd43a4c56`. It records source/screenshot checksums, all six boundary samples, arcade landmark and projection shifts, row registrations, fitted packets, distinct edge-profile counts, and residuals. No screenshot, commercial sprite, ROM, BIOS, or private startup code is tracked. The original Sega CD final screenshot remains SHA-256 `0ca25ab992e17f38e498a29b0624b7ca498efeddc545e447a553bf47fe4a442f`; it is an earlier BlastEm result, not a new image from this audit.

**Unsupported:** a physical viewport calibration, decoded original road-center or camera pose, shared 3D depth coordinates, a predictive arcade-to-five-word adapter, corresponding arcade/Sega texture or perspective, emulated-hardware performance for this fit, and physical Sega CD behavior. This experiment did not cross-check another emulator because it is an offline comparison of existing single-emulator captures and a host reference.

**Next bounded experiment — hypothesis:** recover a stable arcade road-edge or centerline sample at several Y rows with a defensible depth identity, and compare its vertical ordering and width progression with an original synthetic Sega fixture. Fix the target crop from an explicit visual design requirement before fitting any lateral camera controls. If a calibrated mismatch persists, try an offline curve lookup within the existing five-word interface first; preserve the running renderer until an actual visual or timing requirement calls for a change.
