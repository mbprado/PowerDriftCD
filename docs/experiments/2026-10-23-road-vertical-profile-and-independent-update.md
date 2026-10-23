# Phase 1B: vertical road-width profile and independent update — 2026-10-23

**Question / hypothesis:** can a small change to original stamp art correct the [screen-975 vertical-width miss](2026-10-23-road-width-profile-fit.md) with the three selected five-word camera packets held fixed, and does the change help on a separate arcade update? **Baseline:** source widths 52/54/58 at X=139, packets `[63,0,0,4,42]`, `[38,0,0,4,15]`, `[38,0,0,4,31]` for screens 971/973/975. **Acceptance:** retain all nine previously fitted row bounds, improve screen-975 Y=157–159, then causally measure screen 969 and evaluate it without changing the artwork. **Result — verified by execution:** the bounded art change improves the three *adaptation* rows and preserves the nine old rows. On the independent update it leaves the clean Y=153 check unchanged and does not solve the upper Y=152 discrepancy. This profile is an experiment, not a promoted engine asset.

## Artwork and fixed-packet control

**Verified by execution of host software:** a broad +2-pixel ramp across the second 16-pixel source band spoiled screen-971 Y=154–155, so the tested alternative changes that band's local rows 6–9 only, from width 54 to 56. The art repeats every three stamp bands; those positions are source Y modulo 48 = 22–25, including source Y=118–121. It uses the same five road stamp columns plus grass and emits **2,176 bytes** of original art. The chosen row window was informed by the screen-975 Y=157–159 discrepancy, so those rows are now **adaptation data**, not independent validation.

**Verified by execution of the host reference:** `tools/phase1b_road_vertical_profile.py` regenerated all three 128×64 previews and decoded each PNG back to the generated pixel grid. Their original fitted arcade rows Y=154–156, mapped to output rows 22/24/25 by the established 134–190 crop and `arcade_x=2.5*output_x+0.75` sample, are **exactly unchanged** with fixed packets. Mean absolute edge errors remain 0.833, 0.333 and 0.500 output pixels per edge at screens 971, 973 and 975; mean absolute width errors remain 1.667, 0.667 and 1.000 pixels.

| Screen 975 arcade Y / output row | Target width | Baseline width | Changed width |
| ---: | ---: | ---: | ---: |
| 157 / 26 | 89 | 87 | 89 |
| 158 / 27 | 91 | 87 | 89 |
| 159 / 28 | 91 | 86 | 90 |

**Verified by execution of the host reference:** with the screen-975 packet fixed, adaptation-row mean absolute width error falls from **3.667 to 1.000 output pixels**, and mean absolute edge error from **1.833 to 0.833 pixels per edge**. Because the width window was selected after inspecting these rows, this improvement is a fit result rather than evidence of generalization. Equal stamp byte counts do not establish equal Sega CD ASIC or VDP cost.

## Independent screen-969 arcade observation

**Verified by execution in MAME:** the existing owner-local pulse-112 callback-950 saved-state replay was run with Y-sprite source hide bits set at callback 968. Hiding the `$A000`–`$A7FF` source range changed both detected edge pixels on screen 969 at Y=152–156. A narrower `$A600`–`$A6FF` group, comprising 14 changed descriptor bytes, changed both edges at Y=153–156 but only the right edge at Y=152. `$A500`–`$A5FF` changed neither edge on these rows. Each replay captured the intended source-byte changes and kept earlier composed screens 960–968 pixel-identical to baseline. A group intervention establishes collective source contribution; it does not identify one stable road descriptor or world-space road edge.

**Verified by execution:** a second narrow-group replay produced the same Y=152–156 change flags and the same report checksum. This is a deterministic emulator replay check, not an independent hardware observation.

| Screen 969 Y | Causal source group | Arcade left/right | Mapped output row/left/right/width |
| ---: | --- | --- | --- |
| 152 | broad `$A000`–`$A7FF` only | 54 / 294 | 20 / 22 / 117 / 96 |
| 153 | `$A600`–`$A6FF` | 75 / 294 | 21 / 30 / 117 / 88 |
| 154 | `$A600`–`$A6FF` | 74 / 298 | 22 / 30 / 118 / 89 |
| 155 | `$A600`–`$A6FF` | 70 / 299 | 24 / 28 / 119 / 92 |
| 156 | `$A600`–`$A6FF` | 67 / 303 | 25 / 27 / 120 / 94 |

**Verified by execution of host software:** the screen-969 camera packet `[61,0,0,4,44]` is the best of 4,608 curve/texture candidates selected using Y=154–156 with the **baseline** artwork, ridge=bank=0 and horizon=4. This is another optimistic inverse fit, not a camera prediction. Baseline and changed art both produce mean edge error **0.667** and width error **1.333** on those three fit rows. Their independent, narrower-hide Y=153 check is also identical: target width 88, host width 87, edge error **1.500** per edge. Thus the new update supplies no independent evidence in favor of the width change.

**Verified by execution of host software:** at Y=152, which required the broad hide for both boundaries, the target width is 96. The fixed screen-969 packet produces width 87 with baseline art and 89 with the local change. The changed art still has **7 pixels** of width error and **5.5 pixels per edge** mean edge error on that row. The 8-pixel target-width jump from Y=152 to Y=153 may reflect a different visible strip, overlap, or source composition; its cause is **unsupported**. This row is a warning against claiming a calibrated road shape from a few sand-boundary samples.

## Provenance, reproduction and decision

**Verified by execution:** source baseline `85437b0` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME 0.289 executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The owner-local ROM manifest and callback-950 state retain SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The prior private host baseline JSON SHA-256 is `ee9531424e7040e378d41726a7eedd0a0d55c33d2ad1e16e91e2fea5faa80d2f`.

```sh
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 968 --groups A000:0800
python3 tools/phase1b_right_source_search.py build/private analyze --callback 968 --groups A000:0800
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 968 --groups A500:0100 A600:0100
python3 tools/phase1b_right_source_search.py build/private analyze --callback 968 --groups A500:0100 A600:0100
python3 tools/phase1b_road_vertical_profile.py build/private
python3 -m py_compile tools/phase1b_road_vertical_profile.py
```

**Verified by execution:** ignored raw MAME group reports have SHA-256 `53a46fdf06155da4ff9f3ab7f2e442ed4ebc1ecf475c98deed6fe0d7ca3eb365` (broad) and `57b51d0d7a1cbf4528397a37eac0f63502548cc976bb29e85e00e17d0e4bdae9` (narrow). Ignored `build/private/phase1b-road-vertical-profile/result.json` has SHA-256 `8d57ee07022b035c21f72c891e57276ad949024a7cae7ad7ba9adea9a6ddc3e3`. The generated 2,176-byte stamp file SHA-256 is `5b69c8b3b84bb38b0d6f1687dc7177c9e226ad4f418e74d5b31a068208423a59`; three preview PNG hashes are in the private JSON. ROM bytes, source RAM and arcade screenshots remain ignored. No BlastEm disc, second emulator, Sega CD timing measurement or physical-hardware test was run.

**Decision — inference from verified execution:** retain the 52/54/58 baseline art as the current reference and keep this local bump as an experimental alternative. The next useful test is to resolve the Y=152 source composition or obtain another independently causal vertical span, then constrain artwork against several updates at once. A predictive mapping from arcade state to five camera words remains **unsupported**; changing the live camera interface or promoting a new Sega CD workload is premature on this evidence.
