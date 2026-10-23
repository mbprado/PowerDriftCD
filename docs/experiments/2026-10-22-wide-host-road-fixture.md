# Phase 1B: wider host-only road fixture — 2026-10-22

**Hypothesis:** the seven centered arcade width samples can define a useful, wider 128×64 visual reference without changing the working Sega CD renderer. **Baseline:** the [causal road-edge bands](2026-10-22-arcade-causal-road-edge-bands.md) and [bounded right extent](2026-10-22-arcade-causal-right-extent.md); the current synthetic Sega CD host fixture reaches at most 32/128 pixels across its 60 packets. **Method:** fix an explicit arcade vertical crop, map the seven independently verified two-sided edge samples to output pixels, fill unmeasured rows with labeled synthetic anchors and interpolation, then decode and check the generated original-asset image. **Result — verified by execution:** a static 128×64 PNG has road-region widths of 89–96 output pixels at the seven measured anchor rows. This is a host-software visual target, not an ASIC rendering, Sega CD timing result, or calibrated arcade camera adapter.

## Crop and provenance

**Verified by execution:** `tools/phase1b_wide_host_fixture.py` read only the ignored analysis results `build/private/phase1b-right-extent.json` (SHA-256 `8fa498e5df91b75330890050bf3b46f1b8973af12bcfd482f1cfbe365b5a67d0`) and `build/private/phase1b-causal-boundary-rows.json` (SHA-256 `2b360eed5c6d50a613254b84ccb42348745df6ff7a55f0708d6cd8987802148d`). Their underlying arcade observations were made with the owner-local ROM set and isolated MAME 0.289 (`mame0289-dirty`) capture build documented in those reports; this experiment did not launch MAME. The report's source baseline is `f559d5a` on `experiment/perspective-road`, on macOS/Darwin 25.6.0 x86_64 with Python 3.14.8. No BIOS or disc image is involved.

**Design choice / hypothesis:** the inclusive arcade screen-Y crop **134–190** maps linearly to output rows **0–63**, with nearest-integer row selection. It includes far changed-pixel support reaching Y=134, the seven centered `$3400` two-sided samples at Y=156–162, and the callback-974 `$3400`/`$3200` causal left-edge bands. It cuts off `$3200` support below Y=190. This is a visible-region choice, not a recovered projection or calibrated depth mapping. For horizontal geometry, output pixel center `x` samples arcade X=`2.5x+0.75`, representing the full 320-pixel screen in 128 samples. An output pixel belongs to the road region when its sample falls between the measured inclusive sand edges. The measured width includes shoulders and is not asphalt or world-track width.

| Arcade Y | Output row | Output left | Output right | Inclusive output width |
| ---: | ---: | ---: | ---: | ---: |
| 156 | 25 | 29 | 117 | 89 |
| 157 | 26 | 28 | 118 | 91 |
| 158 | 27 | 27 | 118 | 92 |
| 159 | 28 | 27 | 119 | 93 |
| 160 | 29 | 27 | 119 | 93 |
| 161 | 30 | 26 | 120 | 95 |
| 162 | 32 | 25 | 120 | 96 |

**Verified by execution:** the source two-sided edges at these rows are causally associated with the centered callback-974 `$3400` strip and independently identifiable as visible sand boundaries in the prior MAME analysis. The mapped left/right output pixels above were checked against the generated PNG after decoding its pixels and CRCs. All other output rows are **hypothesis/design data**: row 0 is a synthetic 12-pixel road at X=58–69, row 63 is a synthetic full-width road at X=0–127, and gaps are linearly interpolated between anchors. The road colors, shoulder stripes, grass, and center dash are original generated artwork. They do not reconstruct arcade pixels.

**Verified by execution of the source analysis and row mapping:** the centered callback-974 `$3400` causal left edge at arcade Y=156–169 maps to output rows 25–39; the nearer `$3200` edge at Y=170–171 maps to 40–42. Under left steering, `$3400` Y=150–167 maps to 18–37 and `$3200` Y=168–190 maps to 38–63. These are mapped **left-edge response bands**, not claims that one depth owns every pixel in those rows.

**Hypothesis tested conditionally:** on the seven anchor rows, the measured left-steering left edge moves right by 37–39 arcade pixels, corresponding to 14–16 output pixels. If road width remained equal to each centered sample, its predicted right output edge would be X=132–136 and clip beyond X=127 in **7/7** rows. The arcade right boundary under left steering was not established, so this is a clipping risk under a stated constant-width assumption, not a measured steering-dependent width or a rendered left-steering frame.

## Reproduction, checks and limits

```sh
python3 tools/phase1b_wide_host_fixture.py build/private
python3 -m py_compile tools/phase1b_wide_host_fixture.py
shasum -a 256 tools/phase1b_wide_host_fixture.py build/private/phase1b-wide-host-fixture/*
```

**Verified by execution:** the script SHA-256 is `6eca47f2b920ec7145d84bee013cd00054d8587ba2d56b3adfc1021e6dba32a5`. The ignored private outputs are `road-128x64.png` SHA-256 `57d37c18aea511f8c95e528c6a4693c2c9c951d57401722fb62a0e07a92a8c39`, `road-preview-512x256.png` SHA-256 `5e94a712e7f626fffd8ac98bfc88da4caa66c95fc3cab2dfed06c4481b228f77`, and `result.json` SHA-256 `3bdf049dd120cbc3475679f1cff4d87fc355575aabdf2ae3208c94b9111527c8`. The JSON records every output row, its source label, mapped bands, conditional steering comparison, and input/output checksums. The script checks decoded PNG pixel runs against all 64 geometry rows and all anchor edges. Private derived images and prior captures are not tracked in Git.

**Measured comparison:** the seven source-backed rows use 89–96 of 128 output pixels, versus at most 32/128 in the earlier synthetic Sega CD host fixture. Their vertical coordinates and road definitions are not like-for-like; this comparison motivates a wider target but does not establish a required hardware resolution or throughput. **Unsupported:** correctness of interpolated rows as an arcade road, right-edge behavior under steering, equivalence to the existing five-word camera controls, ASIC/VDP cost, 30 Hz frame pacing for this geometry, and physical Sega CD behavior. BlastEm, a second arcade emulator, a Sega CD disc and physical hardware were not run for this host-only fixture.

**Next bounded test — hypothesis:** assess whether the existing ASIC stamp/trace approach can produce a similarly wide original-asset road region and upload it at 30 Hz in BlastEm, retaining the validated 128×64 pipeline as a control. Measure end-to-end output and timing before changing the production camera interface; the host fixture alone cannot justify that change.
