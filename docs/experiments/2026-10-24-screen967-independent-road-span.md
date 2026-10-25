# Phase 1B: independent screen-967 road span — 2026-10-24

**Question / hypothesis:** does the original-art source-width change that improved screen 975 generalize to a different arcade update and a wider vertical span? **Baseline:** the [screen-975 local width bump](2026-10-23-road-vertical-profile-and-independent-update.md) and its three fitted camera packets. **Acceptance:** find a causal two-sided source intervention for another composed screen, fit one five-word host packet on only three rows, hold out the remaining causal rows, then run the [calibrated comparator](2026-10-24-phase1b-calibrated-geometry-comparison.md) and [regression checker](2026-10-24-phase1b-geometry-regression.md). **Result — verified by execution:** screen 967 yielded eleven two-sided causal rows, but both existing art profiles failed the eight-row independent shape check. The width bump helps slightly; it does not generalize sufficiently under this fixed-packet host test.

## Causal arcade sample

**Verified by execution:** the owner-local pulse-112 saved-state replay already contained screen-967 road-region boundaries at Y=153–163. The linked-list audit of its callback-966 captured source RAM found page `$8` reachable. Hiding all 119 page-`$8` descriptors at callback 966 changed neither measured edge on screen 967. Hiding all 119 page-`$E` descriptors at the same callback changed both edges on **11/11** sampled rows. This is consistent with the source-list/page timing observed earlier, but the exact sub-frame latch point remains **unsupported**. The no-effect page-`$8` run is retained as a control.

**Verified by execution:** successive independent range hides localized the screen-967 effect to `$E600`–`$E67F`. The `$E000`–`$E3FF`, `$E400`–`$E5FF`, `$E680`–`$E7FF` and page-`$8` controls changed neither sampled edge. Individual `$E630` hid the left contributor on all eleven rows and the right contributor at Y=158–163; `$E650` changed the right edge at Y=156–157; `$E660` changed it at Y=153–154. A joint `$E630/$E650/$E660` replay changed exactly three source bytes and both edge pixels at **every Y=153–163**. It kept composed screens 960–966 pixel-identical to baseline, and the captured post-write source RAM matched the prepared override. **Three** joint replays produced byte-identical screen and analysis hashes. The joint effect at Y=155 cannot be assigned to one of the three individual records from these tests alone; overlapping sprite composition is a **hypothesis**. No descriptor is identified as a decoded world-space track record.

**Verified by execution:** the baseline screen-967 PNG SHA-256 was `71cc0877c6853bae04360a370c6d12ef0edf5f64d7c3361f2864c5c82c7782d9`; the joint-hidden screen SHA-256 was `80ad0000f3d419dd1ef400d7795c4b038b7acf6a34a6d7ee3f39b37af9f2310b`. Baseline callback-966 Y-sprite source SHA-256 was `39b8af401719d5c41b7ce7d05036989254c59331909b496a630d3025d9307364`; the private three-byte override SHA-256 was `667d501cf8f7a1d7d4e58bd888fe7c6eee4f166c64831498d188d33672724a91`.

## Host geometry check

**Verified by execution of host software:** `tools/phase1b_screen967_holdout.py` used the project's explicit arcade-to-output calibration, tested 4,608 curve/texture candidates with ridge=bank=0 and horizon=4, and selected `[38,0,0,4,31]` using **only arcade Y=154–156**. This is an optimistic per-screen inverse fit, not a predictive camera adapter. The selected packet happens to match screen 975's earlier packet; its generated baseline and bump PNGs are therefore byte-identical to the corresponding screen-975 original-art previews. Both PNGs decoded exactly to the generated pixels. Arcade Y=153 and Y=157–163 were untouched by this packet fit and by the screen-975-specific width-bump selection, so they are an independent check of this host-art hypothesis.

| Arcade Y | Mapped target width | Baseline host width | Width-bump host width | Role |
| ---: | ---: | ---: | ---: | --- |
| 153 | 87 | 84 | 84 | check |
| 154 | 88 | 87 | 87 | fit |
| 155 | 89 | 87 | 87 | fit |
| 156 | 89 | 87 | 87 | fit |
| 157 | 90 | 87 | 89 | check |
| 158 | 91 | 87 | 89 | check |
| 159 | 91 | 86 | 90 | check |
| 160 | 93 | 86 | 86 | check |
| 161 | 94 | 86 | 86 | check |
| 162 | 95 | 86 | 86 | check |
| 163 | 96 | 93 | 93 | check |

**Verified by execution:** the three fit rows have mean absolute edge error **0.833** and width error **1.667 output pixels** for both original-art variants. Over the eight check rows, baseline mean edge/width errors are **3.125/5.250** pixels, while the local width bump yields **3.125/4.250**. It improves some upper check rows but leaves width shortfalls of **7–9 pixels** at Y=160–162. Under the deliberately retrospective regression criteria, both new cases are regression `PASS` at their recorded baselines and independent decision `FAIL` against the 2-pixel check-width limit. The earlier adaptation-only case remains decision `INCONCLUSIVE`; its new independent check here fails.

**Inference from verified execution:** a four-source-row width bump is too local for this wider vertical span under the tested 52/54/58 original-art strip and fixed ridge/bank/horizon. This does **not** show that the five-word interface, graphics ASIC or stock Sega CD cannot render the road. Other camera-word choices, trace construction, artwork profiles and visual-region definitions remain untested against this independent span. The arcade sand-to-non-sand edges may include shoulders; they are not decoded track-width samples.

## Provenance, reproduction and next decision

**Verified by execution:** source baseline `d028abe` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. Owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 saved-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Source-hide trials used the verified selective `road-edge` capture profile and normal MAME execution; no cache hit was counted as a replay. The original-art host generator SHA-256 is `e814601b6e2a3fcec10e3f61b1eae0e11f4e6266c3496fc1433438ff828924d6`.

```sh
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 966 --groups 8000:0800 --capture-profile road-edge
python3 tools/phase1b_right_source_search.py build/private analyze --callback 966 --groups 8000:0800
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 966 --groups E000:0800 --capture-profile road-edge
python3 tools/phase1b_right_source_search.py build/private analyze --callback 966 --groups E000:0800
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 966 --exact-slots E630 E650 E660 --capture-profile road-edge
python3 tools/phase1b_right_source_search.py build/private analyze --callback 966 --exact-slots E630 E650 E660
python3 tools/phase1b_screen967_holdout.py build/private docs/experiments/data/phase1b-road-calibration.json
python3 tools/phase1b_calibrated_geometry.py build/private docs/experiments/data/phase1b-road-calibration.json docs/experiments/data/phase1b-road-geometry-cases.json
python3 tools/phase1b_geometry_regression.py build/private docs/experiments/data/phase1b-road-regression-criteria.json
```

**Verified by execution:** range narrowing between the broad and joint replays used paired `run`/`analyze` calls with `--groups E000:0400 E400:0400`, `E400:0200 E600:0200`, `E600:0100 E700:0100`, `E600:0080 E680:0080`, and `E600:0040 E640:0040`, followed by independent 16-byte slot probes at `$E600` through `$E670`. Those ignored outputs and logs remain under `build/private/phase1b-right-search-966-*`.

**Verified by execution:** ignored private JSON SHA-256 values are `90dd36b83c107281d1b44db0fb7c2256f410c05b83f8ada41594803db794d052` for the page-`$8` control, `646bf5feafaaa708b2f64a8df559089b7273b7b3a80e2756fd86be7b920a3956` for the page-`$E` broad hide, `b68de3e28164b216ddb0bc6bd4fa04c3f1953f2f7887854af236da5a26cb526b` for the repeated three-slot joint replay, `a4bf51f850eb207ceb8877abc8dd583f3cf0b0a8a8d29f0edfcf5d13772216b1` for the original-art host manifest, `2ee2ed41111371a55a7e19d39a01795e3fa4f6e9cf07b081edffb9e0444b8822` for the six-case calibrated comparison and `746425ae4409445b41d7001ca7e521fa7d7d4d8fa8e020fcbac22bdef0931e30` for the six-case regression. Tracked case and criteria files have SHA-256 `486f5889931f4b6f1ee5fe06fb17a3aa44c4ec94624c18e06a2931c3b660c79e` and `a3558479c20fd7e53649b9d4a47607279a378f4c29d8e894abcd07a5dc23b817`. All ROMs, source RAM, screenshots, state and proprietary pixels remain ignored under `build/private`.

**Next bounded test — hypothesis:** hold this screen-967 source and calibration fixed while testing whether more of the existing five-word camera space or a smooth source-width profile can reduce the **eight independent-row errors**. Reserve other unmeasured arcade updates for validation, and report the added ASIC/VDP cost before changing the live renderer. No BlastEm build, additional emulator or physical hardware test was performed here.
