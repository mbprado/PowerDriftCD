# Phase 1B: arcade rotation parameters versus visible road geometry — 2026-10-20

**Question / hypothesis:** can the six captured Y-Board rotation parameters predict where the visible road image moves under a controlled steering pulse? **Baseline:** [rotation-buffer swap and first displayed response](2026-10-20-arcade-rotation-swap.md). **Acceptance:** compare the same callback in centered, left and right replays; apply the documented source-coordinate transform to a fixed road-containing rectangle; outperform an unshifted comparison and a reversed-transform control; reproduce the result from independent captures. **Result — PASS for the first two affected frames, verified by execution in MAME:** the predicted mapping matched 94–98% of RGB pixels exactly at callbacks 963 and 965, compared with 27–48% at the same screen positions. **Result — INCONCLUSIVE for a sustained single-layer model:** exact matches fell to 41–60% by callbacks 967–969, though the predicted mapping remained better than both controls. No arcade camera variable or track coordinate has been identified.

## Environment and method

**Verified by execution:** analysis source revision `974f60d` on `experiment/perspective-road`; `tools/phase1b_affine_verify.py` SHA-256 `04a27f24fad70cec3668630edbdbfc53b9eb5324b3f8252a172b877e4ca3fd29`; its imported PNG/capture reader `tools/phase1b_swap_compare.py` SHA-256 `54dcec8a4ed0597b661b35b18090977e09c1ce1ece0e78f0c5e1131069039a07`. The input captures were made by the earlier Lua script with SHA-256 `09086417b9fcc623e8953ffae3512b829ecb3351f1d65abcc74553d3f52cd798`. Host: macOS 26.6.2 x86_64. Input emulator: MAME 0.289 (revision string `unknown`), executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; owner-local, ignored 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. This experiment reanalyzed the five previously captured runs; it did not execute new emulator sessions, compile a game, or test physical hardware.

**Documented only:** [MAME 0.289's `rotate_draw()`](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaic16.cpp) reads the active buffer's `currx`, `curry`, `dyy`, `dxx`, `dxy`, and `dyx` values and advances source X/Y across screen X/Y. Source pixels are selected by arithmetic right-shift of each fixed-point coordinate by 14 bits. The previous experiment verified the pre-swap block becomes MAME's active buffer for the next displayed response; this analysis uses that block for the following odd-numbered screenshot callback.

**Verified by execution:** for each steered output pixel `(x,y)`, the tool computes MAME's corresponding source coordinate from that condition's six captured parameters, then locates the same integer source pixel in the centered image. The centered transform was verified to have `dxx=dyy=16384`, `dxy=dyx=0`, and pixel-aligned origins at all four analyzed swaps. The tool follows the emulator's arithmetic `>>14` source-pixel rule. The fixed comparison rectangle is `x=0..319, y=80..169` in the 320×224 screenshot, containing road, scenery and some objects. Pixels whose predicted or reversed-control source position lay outside the screenshot were excluded from **all three** comparisons at that callback, so their denominators are identical.

Three comparisons were made over the same valid pixels: same screen position (`identity`), position predicted by the captured transform (`predicted`), and the opposite displacement (`reversed`). The metric is the fraction of pixels with all three RGB bytes identical; RGB mean absolute error is also written to the raw CSV. This is a dense correspondence test across visible pixels, not a manually selected landmark or a claim that every pixel belongs to the road layer. The center and left inputs were each captured twice; the right input once. The two center/left combinations produced byte-identical CSV output.

Reproduce from the repository root using the ignored captures described in the [swap report](2026-10-20-arcade-rotation-swap.md):

```sh
python3 tools/phase1b_affine_verify.py build/private/phase1b-swap-precise-center1 build/private/phase1b-swap-precise-left1 build/private/phase1b-swap-precise-right1 > build/private/phase1b-affine-verify/measurements-1.csv
python3 tools/phase1b_affine_verify.py build/private/phase1b-swap-precise-center2 build/private/phase1b-swap-precise-left2 build/private/phase1b-swap-precise-right1 > build/private/phase1b-affine-verify/measurements-2.csv
```

**Verified by execution:** both nine-line private CSV files had identical SHA-256 `b77c1ce08ed9bf076149123d30dfa497571e2b498d1be8979bed5ae642b10cf3`. The callback-963 input screenshot SHA-256 values were center `0a1f2b8c79ce6bc095b89284bef4137aa972326e7b275d5d096515b0fe5bfd90`, left `b6071c8a863c47589b4ce45e68adccd6f31bd822e22ea5f4e97ae12802e45a4a`, and right `ebf842c4406cc1dd5e8f19dc1d6c7527aeb03e854ee5ee94eefcba9f725b6bec`. Raw PNGs, rotation blocks, logs and CSVs remain ignored and untracked; only the independently written analysis tool and this summary are intended for Git.

## Results

**Verified by execution:** percentages below are exact RGB matches over the same valid pixels within each row. The parameters used for screenshot 963 came from the swap after callback 962, and likewise for later odd callbacks. These are image correspondences in MAME, not emulated cycle or stock arcade timing measurements.

| Screenshot callback | Direction | Pixels compared | Same position | Predicted | Reversed |
| ---: | --- | ---: | ---: | ---: | ---: |
| 963 | left | 28,710 | 47.68% | **97.83%** | 35.76% |
| 963 | right | 28,363 | 34.40% | **96.70%** | 22.56% |
| 965 | left | 28,701 | 42.59% | **96.72%** | 26.59% |
| 965 | right | 28,105 | 26.92% | **94.33%** | 18.09% |
| 967 | left | 28,560 | 27.31% | **60.44%** | 19.32% |
| 967 | right | 28,031 | 24.46% | **57.04%** | 15.79% |
| 969 | left | 28,465 | 23.31% | **43.70%** | 16.71% |
| 969 | right | 27,782 | 20.92% | **40.77%** | 12.70% |

**Verified by execution:** RGB mean absolute error at callback 963 fell from 34.95 to 2.79 (left) and from 46.75 to 4.15 (right) with the predicted mapping. At callback 965 it fell from 42.29 to 4.05 (left) and 55.83 to 7.19 (right). These values use 8-bit RGB intensity units, not timing units. The reversed control increased the error in every row. Repeating centered and left captures gave the same result exactly, consistent with the prior byte-for-byte run comparisons.

**Interpretation — verified by execution plus documented MAME behavior:** the six-value affine block predicts the first visible geometric movement extremely well under either steering direction. The exact-match drop after callback 965 shows that the compared rectangle of the composed screenshot is no longer explained by applying one transform to the centered screenshot. **Hypothesis:** later source-layer content, object positions, palette/priority effects, or other game state differs between steering conditions. The present test did not isolate the rotation source bitmap from the composed screen, so it cannot assign the residual pixels to any one cause. **Unsupported:** that the arcade game stores a complete camera in this six-value block, that these values alone encode track curvature/elevation, or that the Sega CD's five-word camera interface already represents the full arcade scene.

**Next bounded experiment — hypothesis:** inspect the rotation source bitmap or the Y-Board sprite RAM at the same four callbacks to determine whether source content diverges when the whole-screen affine match falls. Separately identify one stable road-edge or scenery landmark across several unsteered frames, then compare its movement against the affine prediction. Only after a reproducible track/camera segment is supported by both image observations and code/data references should an adapter to the Sega CD renderer be proposed. No Sega CD rendering architecture changed here.

**Follow-up — verified by execution in MAME:** [the source-sprite divergence experiment](2026-10-21-arcade-sprite-source-divergence.md) found Y-sprite RAM changes before the image match declines. Substituting the centered RAM snapshot into both steered replays restored the callback-967 affine match to about 95–97%; a same-state writeback control did not change the replay. Which Y-sprite records encode the road remains unsupported.
