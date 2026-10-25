# Phase 1B: nearest-depth packet transfer — 2026-10-25

**Question / hypothesis:** can an arcade state value select an existing five-word host camera packet without using screen-967 road edges? **Baseline:** the [screen-967 camera sweep](2026-10-25-screen967-camera-word-sweep.md) selected `[38,0,0,4,31]` using three local fit rows and failed the other eight rows. **Method:** transfer one of four independently fitted packets from neighboring arcade screens, selecting by nearest captured `road_depth` state. **Expected evidence:** a full eleven-row screen-967 score within the retrospective 2-pixel edge and width limits, plus leave-one-out checks on the four packet-source updates. **Result — verified by execution of host software:** the screen-969 packet scores 1.273/1.636 over all eleven screen-967 rows, but all four leave-one-out transfers fail the three-row fit-width limit. This is an exploratory offline cue, not a reliable predictive adapter.

## Inputs and alignment

**Verified by execution:** the existing center-steering upstream trace records the arcade state field named `road_depth` at markers 967/969/971/973/975 as hexadecimal `$303F/$30BE/$313D/$31BC/$323B`. At marker two frames earlier for each screen it records `$2FC0/$303F/$30BE/$313D/$31BC`. In both alignments, screen 969 is the nearest state to screen 967 by raw absolute difference, `$007F`. The existing producer trace verified that this state feeds the angle/lookup path; its physical distance units and precise relation to the composed screen are **unsupported**. Testing both marker alignments is a sensitivity control, not proof of a causal alignment.

**Verified by execution:** the four packet sources came from the prior original-art three-row inverse fits: screen 969 `[61,0,0,4,44]`, 971 `[63,0,0,4,42]`, 973 `[38,0,0,4,15]`, and 975 `[38,0,0,4,31]`. Each source packet was fitted using that source screen's road-edge rows, so the packet library is experimental training data. The selection rule reads only `road_depth`, source screen identifiers and these stored packets; it does not read target edges. The same tracked crop maps arcade Y=153–163 to eleven 128×64 host rows. The target is the previously verified three-slot causal screen-967 intervention, not an inferred world-track width.

| Diagnostic | Mean edge error | Mean width error | Limit result |
| --- | ---: | ---: | --- |
| Screen 967, transferred screen-969 packet, all 11 rows | 1.273 | 1.636 | PASS at retrospective 2/2 limits |
| Screen 967, same packet, old 3 fit rows | 1.167 | 2.333 | FAIL at old 1/2 fit limits |
| Screen 967, same packet, other 8 rows | 1.313 | 1.375 | PASS at 2/2 check limits |
| Leave out 969; choose nearest other training state | 1.833 | 3.667 | FAIL at 1/2 fit limits |
| Leave out 971; choose nearest other training state | 2.000 | 4.000 | FAIL at 1/2 fit limits |
| Leave out 973; choose nearest other training state | 2.500 | 5.000 | FAIL at 1/2 fit limits |
| Leave out 975; choose nearest other training state | 1.833 | 3.667 | FAIL at 1/2 fit limits |

All errors are host **output pixels**, not arcade pixels or emulated hardware timing. The script records every target and rendered left/right bound in ignored JSON. Both marker alignments select the same source and give the same errors. Two runs produced byte-identical JSON SHA-256 `b33d3fe0ca38f8e3aed2bce97dc2d2ddfb069c6327d2b0b9252e2c3651fad4b2`.

## Interpretation

**Inference from verified execution:** transferring an adjacent packet can represent this screen's full visible span with existing art and controls. The four leave-one-out failures show that raw nearest `road_depth` is too weak to select reliable packets across even this short sequence. The successful screen-967 transfer was noticed before the rule was formalized, so its 2/2 result is **exploratory** and must not be counted as clean independent validation. Moreover, source screen 969 occurs **after** target screen 967: this selection is possible offline but does not demonstrate a causal real-time producer. It does not identify arcade curve phase, texture phase, camera axes or track units.

**Next bounded test — hypothesis:** acquire a causally identified road span at an *earlier* update or a new later update, freeze a forward-only rule using only prior state and packets, and evaluate it on a fresh update without changing the rule. A stronger option is to correlate projection/descriptor geometry with the arcade state and derive packet phase directly. If neither can be established, mark adapter identification `INCONCLUSIVE` and continue hardware/renderer experiments independently. No new art profile, camera-interface change, BlastEm run, MAME replay or physical-hardware test was performed here.

## Provenance and reproduction

**Verified by execution:** baseline source revision `94f40d5` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8. The upstream trace SHA-256 is `d08c046ffa864fc3b938fbcdf6bd6ecee0056ad61a2d2cb0491ba266a5d90788`; prior training JSON `8d57ee07022b035c21f72c891e57276ad949024a7cae7ad7ba9adea9a6ddc3e3`; causal screen-967 JSON `b68de3e28164b216ddb0bc6bd4fa04c3f1953f2f7887854af236da5a26cb526b`; tracked calibration `e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23`. The script SHA-256 is `0ba07729fa31893bcebf0ca387d01ce11c338ba08ea71a9b4f0ce5c2108c6eb2`. MAME 0.289, ROM manifest and saved-state provenance for the pre-existing captures are in the [upstream state report](2026-10-21-arcade-upstream-state-and-matched-depth.md) and [screen-967 report](2026-10-24-screen967-independent-road-span.md). This command reuses them and does not execute MAME.

```sh
python3 tools/phase1b_nearest_depth_packet.py build/private docs/experiments/data/phase1b-road-calibration.json
```

Raw output is ignored at `build/private/phase1b-nearest-depth-packet/result.json`. The script checks hashes before using the private inputs; no ROM, source RAM, screenshot, BIOS or protected code is tracked.
