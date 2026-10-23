# Phase 1B: three verified steered road updates — 2026-10-23

**Question / hypothesis:** why did hides at callback 972 fail to affect screen 973, and can the correct active source yield a second two-sided arcade road sample? **Baseline:** the verified screen-971 `$E630`/`$E660` intervention and screen-975 `$E610` intervention. **Acceptance:** identify the active Y-sprite source list for screen 973, hide individual left/right contributors, verify captured RAM and unchanged earlier screens, then compare all three update points with the original-art host road. **Result — verified by execution: PASS for a three-update, three-row screen-space sample; INCONCLUSIVE for a calibrated five-word camera adapter.**

## Source-list timing

**Documented only:** pinned [MAME 0.289 Y-Board sprite code](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/sega16sp.cpp) starts Y-sprite drawing at list entry zero, follows each descriptor's low 12-bit next index, and stops at an end marker or repeated entry. Its renderer also consults the rotation buffer for native scanline clipping. The pinned [Y-Board screen update](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) draws Y sprites, applies the rotation transform and composes the foreground sprites. These are facts about the tested emulator implementation, not a hardware timing claim.

**Verified by execution:** `tools/phase1b_ysprite_page_audit.py` followed that linked-list format in the private pulse-112 source-RAM captures at callbacks 968–976. It found exactly one non-head descriptor page per capture, cycling **C, A, 8, E, C, A, 8, E, C**, with 106–110 reachable descriptors. `$E630` and `$E660` were reached in the capture labelled 971, but not 973; `$A600` and `$A630` were reached in the capture labelled 973. The callback-970 joint `$E630`/`$E660` hide remained in captured RAM through callback 973, then disappeared at 974. Thus the earlier failed callback-972 `$E`-page hide was **not** evidence that source writes were ignored. The list traversal explains its lack of a visible effect in the tested screen-973 update. The exact sub-frame latch time between a Lua callback label and MAME's screen update was not directly measured.

## Causal two-sided sample

**Verified by execution:** the existing saved-state replay was run with source hides at callback 972. Independent one-byte hides at `$A600` (captured graphic word `$3888`) changed the visible **left** boundary at screen-973 Y=154–157; `$A630` (graphic word `$3F45`) changed the **right** boundary at Y=154–156. An `$A5B0` `$3888` control changed neither measured boundary on those rows. A joint replay changed exactly the two source bytes `$A600` and `$A630`, kept screens 960–972 pixel-identical, and changed both boundary pixels at Y=154–156. Screen-973 baseline and joint-hidden PNG SHA-256 values were `b57f71a20eaf437e58fa70501ce5942c6f7d3d274f085d80b833835d67c0526a` and `3356719085df1d7b4cf3ca3057f3fb4ae2f7935727d77f5ee700e0fb5f172d0b`.

**Verified by execution:** the following are inclusive sand-to-non-sand road-region widths in 320-pixel MAME composed screens. Each row in each column passed a two-sided causal hide: `$E630`/`$E660` for screen 971, `$A600`/`$A630` for screen 973, and `$E610` for screen 975. These are screen-space landmarks; the visible region can include shoulders and is not decoded world-space track width.

| Screen Y | Screen 971: left/right/width | Screen 973: left/right/width | Screen 975: left/right/width |
| ---: | ---: | ---: | ---: |
| 154 | 86 / 292 / 207 | 86 / 293 / 208 | 82 / 296 / 215 |
| 155 | 78 / 292 / 215 | 84 / 293 / 210 | 81 / 296 / 216 |
| 156 | 69 / 298 / 230 | 83 / 293 / 211 | 77 / 298 / 222 |

**Inference from verified execution:** the same visible width can be composed from different descriptors at adjacent update points. A fixed RAM slot or graphic word cannot be treated as a persistent road record. This is a short, reproducible **screen-space edge trajectory** under one input pulse; it does not identify arcade camera units, curvature, elevation, or a track-segment data structure.

## Original-art host comparison

**Verified by execution of the host reference:** `tools/phase1b_three_epoch_road_fit.py` mapped arcade X by `x_sega = 0.4 × x_arcade + offset` and arcade Y by `y_sega = y_arcade − 128`, so rows 154–156 became output rows 26–28. It reproduced the relevant row bounds of **all 60/60** tracked wide-road packets exactly before fitting. It then searched the **96 curve × 48 texture** settings of the current 128×64 fixture independently at each update, holding ridge=0, bank=0 and horizon=4. This is an optimistic host-only inverse fit: the target was used to select each packet, there is no temporal-smoothness or CPU-cost constraint, and no BlastEm image was built.

| Provisional horizontal offset | Screen 971 best edge error | Screen 973 best edge error | Screen 975 best edge error |
| ---: | ---: | ---: | ---: |
| 0 output px | 2.333 px | 3.467 px | 3.333 px |
| −4 output px | 1.700 px | 2.267 px | 0.900 px |

**Verified by execution of the host reference:** with the post-hoc −4-pixel alignment, the selected packets were `[52,0,0,4,22]`, `[40,0,0,4,9]` and `[51,0,0,4,9]` for screens 971, 973 and 975. Their mean absolute width errors over the three rows were **3.733**, **5.133** and **2.267** output pixels. The middle arcade widths map to **83.2–84.4** output pixels under the chosen scale, while this fixture's tested source geometry yields at least **89** pixels at those rows. The width shortfall is therefore a property of the current **synthetic geometry under this mapping**, not proof that the five-word interface or Sega CD ASIC cannot represent the arcade road. The −4-pixel offset was chosen after inspecting the first sample to explore crop sensitivity, so it cannot serve as validation.

## Provenance, reproduction and decision

**Verified by execution:** source revision `e8f91ed` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The owner-local ROM manifest and callback-950 state remain SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The tracked host metrics SHA-256 is `60187a57c8c8f768de32ebf4a365dc4d55e5f9b6aa59a14c8adf0ad58451721a`. No Sega CD disc image, BIOS, or physical hardware was used.

```sh
python3 tools/phase1b_ysprite_page_audit.py build/private
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 972 --groups A5B0:0010 A600:0010 A630:0010
python3 tools/phase1b_right_source_search.py build/private analyze --callback 972 --groups A5B0:0010 A600:0010 A630:0010
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 972 --exact-slots A600 A630
python3 tools/phase1b_right_source_search.py build/private analyze --callback 972 --exact-slots A600 A630
python3 tools/phase1b_three_epoch_road_fit.py build/private docs/experiments/data/wide-road-motion-host-metrics.json
python3 -m py_compile tools/phase1b_ysprite_page_audit.py tools/phase1b_three_epoch_road_fit.py
```

**Verified by execution:** ignored raw captures and derived JSON remain under `build/private`. SHA-256 values are `748307bab58c088cc367d88c16147ae065b7374547ac8f83a327d332de128556` for the page audit, `8503501d9ff715de42e77d3d304d8796a965b62bf502548e8cf79c1098149944` for the screen-973 joint intervention, and `e4c3a9345cd0f74bd1d0689be87564b5ca99d2023794c41322494d1ff8246f2d` for the host comparison. ROM data, source RAM, screenshots and commercial graphics remain ignored and private. No second arcade emulator, BlastEm timing test, or physical-hardware test was run.

**Next bounded step — hypothesis:** calibrate a viewport and road-region definition against the original-art fixture, then try a modest, original source-width profile that covers the measured middle update. Only after a host target matches the three updates should a new ASIC/VDP timing disc be considered. A real camera-command producer and original track data still require separate binary/data analysis; this fit alone does not justify changing the five-word interface.
