# Phase 1B: bounded screen-967 camera-word sweep — 2026-10-25

**Question / hypothesis:** can the existing five-word camera packet explain the independent [screen-967 road span](2026-10-24-screen967-independent-road-span.md) without changing source art or the renderer? **Baseline:** packet `[38,0,0,4,31]` with original 52/54/58-pixel road bands. **Test:** retain the causal arcade source, calibration and three fit rows at Y=154–156; vary existing words in two bounded grids and assess Y=153,157–163 afterward. **Expected acceptance:** a packet selected without reading the eight check rows must meet the existing mean edge/width limits of 2/2 output pixels on those rows. **Result — verified by execution of host software:** fit-only choices fail that check. The unchanged source art *can* produce a passing shape when the check rows are used to select a different fit-eligible packet, but that is an oracle diagnostic, not independent validation.

## Method and controls

**Verified by execution:** `tools/phase1b_screen967_camera_sweep.py` reads the same ignored three-slot screen-967 intervention JSON as the preceding experiment and asserts its SHA-256, callback 966, pulse 112, three hidden slots, all eleven two-sided changed rows, and the tracked calibration SHA-256. It reuses the existing host `wide_geometry_lines` and original-art pixel generator. No arcade ROM data or extracted graphics are written to tracked files.

For each original-art variant, the first grid tests all **4,608** curve phases `0..95` × texture phases `0..47` with ridge/bank/horizon fixed at `0/0/4`. The second tests **6,720** ridge phases `0..191` × banks `-2..2` × horizons `1..7`, keeping curve/texture at `38/31`. The second grid had **5,988** candidates with contiguous road bounds over the three fit rows. Selection minimizes `(mean absolute fit-edge error, mean absolute fit-width error, packet)`; the check rows never participate in this selection. The *oracle* instead minimizes check error among packets meeting the retrospective fit limits of 1/2 pixels. This intentionally leaks the check rows and measures representational capacity only. The two grids do not cover every five-word combination.

| Art / sweep | Fit-only packet | Fit edge/width | Check edge/width | Check decision | Check-row oracle packet | Oracle check edge/width |
| --- | --- | ---: | ---: | --- | --- | ---: |
| Baseline, curve/texture | `[38,0,0,4,31]` | 0.833/1.667 | 3.125/5.250 | FAIL | `[58,0,0,4,39]` | 0.8125/1.625 |
| Width bump, curve/texture | `[61,0,0,4,34]` | 0.500/1.000 | 2.0625/3.375 | FAIL | `[58,0,0,4,39]` | 0.8125/1.625 |
| Baseline, ridge/bank/horizon | `[38,14,-2,7,31]` | 0.500/0.333 | no continuous road on all check rows | FAIL | `[38,182,-1,1,31]` | 2.250/3.250 |
| Width bump, ridge/bank/horizon | `[38,14,-2,7,31]` | 0.500/0.333 | no continuous road on all check rows | FAIL | `[38,178,-1,1,31]` | 2.5625/2.625 |

All errors are **output pixels**, never arcade pixels or emulated hardware timing. Check limits are edge ≤2 and width ≤2. In the first grid, 101 baseline and 123 width-bump packets meet both three-row fit limits. In the second grid, 706 and 690 do. A missing check error means the host renderer did not produce one contiguous road span at every check row; it is not a zero error. **Verified by execution:** the baseline curve/texture oracle produced widths 87,87,92,92,92,92,93,93 over output rows 21,26,27,28,29,30,32,33, versus target widths 87,90,91,91,93,94,95,96. The private JSON records all left/right bounds as well as aggregate errors. Two complete runs gave the identical JSON SHA-256 `464da7026605a74c49ed46f99485d3e0fbd102de6aab904e5e8b962cdab9e97c`.

## Interpretation and next test

**Inference from verified host execution:** the present original-art host renderer has enough representational range to draw a screen-967 span within the retrospective eight-row limits *when a packet is selected using those same rows*. Therefore this sample does not justify a wider source strip or a camera-interface change. The fit ambiguity is substantial: three arcade rows do not uniquely determine the camera packet. The fit-only result is `FAIL`, while predictive selection from arcade state is **unsupported**. The causal arcade edges are sand-to-non-sand screen-space boundaries and can include shoulders; they are not decoded world-space track dimensions.

**Next bounded test — hypothesis:** recover one independent arcade cue for curve phase and texture/vertical phase at screen 967, then select a packet *without reading the held-out road edges*. Freeze the rule before another arcade update. If those cues cannot be identified, report this as an adapter-identification blocker and consider a smooth art-width profile only with fresh validation rows. The live five-word interface and renderer remain unchanged; the oracle packet was not promoted to a runtime command. No new ASIC/VDP cost, BlastEm timing, MAME execution, second-emulator run or physical-hardware result was measured in this host-only diagnostic.

## Provenance and reproduction

**Verified by execution:** source baseline `de18e07657b96403168cb41accde98a0ad065ea4` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8. The locally held source intervention JSON SHA-256 is `b68de3e28164b216ddb0bc6bd4fa04c3f1953f2f7887854af236da5a26cb526b`; calibration SHA-256 is `e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23`. Host generator `tools/make_perspective_road.py` SHA-256 is `8965c5bd9d097bacdb3857e657228d9cd29e465ff1012e5bd49aa7490f7cbfe6`; original-art pixel adapter `tools/phase1b_road_vertical_profile.py` is `a76ab11b003876f8a057da3cfff2cc876d5ef47aad3b3ea3dd749e35db111320`; this sweep script is `9c7a764b7c2906f98d086412efb2828e31cda3a325ee133c96de3cdb3e912e9e`. The executable and private arcade evidence provenance are in the preceding report; this experiment did not rerun MAME. No disc image or BIOS was used.

```sh
python3 tools/phase1b_screen967_camera_sweep.py build/private docs/experiments/data/phase1b-road-calibration.json
```

The command writes ignored raw results to `build/private/phase1b-screen967-camera-sweep/result.json` and prints its SHA-256. It requires the owner-local private evidence already described in the preceding report. The complete source data and all protected ROM/state/screenshot material remain outside Git.
