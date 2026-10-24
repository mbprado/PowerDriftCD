# Phase 1B: calibrated arcade-to-host road comparison — 2026-10-24

**Question / hypothesis:** can the existing causal arcade edge reports and original-art 128×64 host previews be compared by one repeatable command with explicit coordinate calibration and fit/check labels? **Baseline:** the earlier [width-profile](2026-10-23-road-width-profile-fit.md) and [vertical-profile](2026-10-23-road-vertical-profile-and-independent-update.md) scripts each performed their own row mapping and scoring. **Acceptance:** reproduce their published per-role errors, require causal evidence for each selected row, prove that changing calibration changes the comparison, and produce a machine-readable result with input hashes. **Result — verified by execution: PASS** for the four specified host-image cases. No new MAME replay or Sega CD execution was needed.

## Explicit inputs and output

**Verified by source inspection and execution:** [the calibration file](data/phase1b-road-calibration.json) records the current **design-choice** crop arcade Y=134–190 to output rows 0–63, nearest-even row rounding, the rational pixel-center sample `arcade_x=(10*output_x+3)/4`, inclusive edge membership, image size and the original-art road RGB colors. This mapping is **not** a recovered arcade camera projection. [The case file](data/phase1b-road-geometry-cases.json) records only evidence filenames, original-art preview filenames, five-word camera packets and row roles; it contains no ROM or extracted graphics. Both files can be varied without changing the comparator code.

**Verified by execution:** `tools/phase1b_calibrated_geometry.py` reads private causal JSONs and already generated 128×64 original-art PNGs, checks that both observed boundary pixels changed under the source intervention, maps their inclusive arcade coordinates to discrete output pixels, and finds contiguous road-colored runs in the decoded PNG. It records signed left/right/width deltas, per-role mean absolute errors, the five-word packet and input SHA-256 values in ignored `build/private/phase1b-calibrated-geometry.json`. A source row lacking two-sided intervention evidence is rejected. The tool does **not** search or refit camera packets; packet selection remains a prior, separately documented optimistic inverse fit.

| Case and role | Rows | Mean edge error per edge | Mean width error |
| --- | ---: | ---: | ---: |
| Screen 971 baseline, fit | 3 | 0.833 output px | 1.667 output px |
| Screen 973 baseline, fit | 3 | 0.333 | 0.667 |
| Screen 975 baseline, fit | 3 | 0.500 | 1.000 |
| Screen 975 baseline, original check | 3 | 1.833 | 3.667 |
| Screen 975 local width bump, fit | 3 | 0.500 | 1.000 |
| Screen 975 local width bump, adaptation | 3 | 0.833 | 1.000 |

**Verified by execution:** the three baseline fit-row target and host bounds exactly matched the previous `phase1b-road-width-profile.json`, its screen-975 check width error was reproduced, and the changed-art adaptation width error matched `phase1b-road-vertical-profile/result.json`. The local width bump was chosen using Y=157–159, so its improved row group is labeled **adaptation**, not independent validation. A control calibration changing only the horizontal offset from 3 to 13 changed screen-971 Y=154 target bounds from `[35,116]` to `[34,115]`; this confirms the stored calibration actually controls the comparison. A deliberately added screen-975 Y=153 row, which lacks two-sided causal support, was rejected.

## Cost, provenance and limits

**Verified by execution:** five fresh Python-process runs of the same offline comparison took **0.212481, 0.296995, 0.283023, 0.275384 and 0.222672 host seconds** (median **0.275384**), and all five wrote byte-identical JSON with SHA-256 `9df0af32a37cdf22b67531d780b6f24e5d03b5570b4de83bba850f457176eef4`. This measures only rechecking existing artifacts, including process startup and PNG decoding. It does not replace the MAME executions or host rendering needed to create those artifacts, and it is not original hardware timing. Analyst time saved by avoiding repeated manual coordinate conversions was not measured.

**Verified by execution:** source baseline `e0289fa` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; no compiler, MAME or BlastEm launch in this experiment. The earlier arcade evidence came from MAME 0.289 executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`, owner-local ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and the callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`, as reported by their original experiments. The comparison tool SHA-256 is `639d704b66932657995c338268152ec9f7d26d72481fdc2e889375c63423b2f7`; calibration and case SHA-256 values are `e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23` and `1f02ea614ddda93a97f29de33c4f8cb3b153251b3b2bc7643d1654ea179d1b2e`.

```sh
python3 tools/phase1b_calibrated_geometry.py build/private docs/experiments/data/phase1b-road-calibration.json docs/experiments/data/phase1b-road-geometry-cases.json
python3 -m py_compile tools/phase1b_calibrated_geometry.py
shasum -a 256 build/private/phase1b-calibrated-geometry.json
```

**Verified by execution:** ignored raw five-run timing data are in `build/private/phase1b-calibrated-geometry-benchmark.json`, SHA-256 `e785ad890fb6111bfb32f5b536ea5fe22fe7af1aaae8980fb48cb29939740806`. The four original-art preview SHA-256 values are `07b7e355fb4a8ad517479a78bbca2a13384f7044da078ff180b45ac3a7fce56e`, `e02203ff530b6462278c282f7306d08128a152f9e74106bd06e87faf152f9752`, `163404b41aec7c812b33a8eea72eb7076d2c6350ba5f2ddef7cea4af423366b2` and `d3a4c4f55415096461d471fdfef443e3fa5827b418346abc367a311cb180575d` for screens 971/973/975 baseline and changed screen 975. All proprietary captures remain ignored under `build/private`.

**Limitations — inference from verified execution:** these PNGs are host-generated renderings of the Sega CD fixture's original art, not captured Genesis VDP output. Agreement in this comparison cannot establish ASIC/VDP correctness for these new packets, arcade camera recovery, or physical-hardware fidelity. The next framework step is machine-readable acceptance criteria that consume these role metrics and distinguish PASS, FAIL and INCONCLUSIVE without promoting adaptation rows to independent checks. A separate arcade update with a wider causally verified span is still needed to test generalization.
