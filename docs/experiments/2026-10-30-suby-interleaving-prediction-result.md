# Phase 1B: held-out Sub-Y entry-state interleaving

**PASS — verified by execution in MAME 0.289:** the frozen pulse-132 prediction matched **20/20 comparisons in each of three independent output-only runs**. Five comparisons checked that input-only entry counts reproduced; fifteen scored the predicted main locked count, copy count and 16-byte slot at markers 961–969. Each run executed MAME afresh from the same private callback-950 state. The frozen JSON SHA-256 `4bdbf62168795f6af2c610bb963b2332097ecd6ec9e5b233ad32fd8a1c5fe691` and the [pretarget method](2026-10-30-suby-interleaving-prediction-plan.md) were committed at `c2949a3` before target capture; the prediction was not changed afterward.

| Marker | Sub-Y PC at main entry | Predicted extra Sub-Y record | Entry count | Locked/copy count | Copy slot |
| --- | --- | --- | --- | --- | --- |
| 961 | `$012B3A` | 1 | `$0027` | `$0028` | `$0280` |
| 963 | `$012A06` | 1 | `$0028` | `$0029` | `$0290` |
| 965 | `$01293E` | 0 | `$0029` | `$0029` | `$0290` |
| 967 | `$0129BA` | 0 | `$0029` | `$0029` | `$0290` |
| 969 | `$012932` | 1 | `$0026` | `$0027` | `$0270` |

The first four PC outcomes came from the pulse-124 development schedule. `$012932` was new in the held-out input: the private Sub-Y instruction path tests a nonzero object field before entering the previously observed `$0129A8` projection path. Its `+1` **timing hypothesis** matched the target count and slot, but the code branch alone did not guarantee it would win the lock before main.

| Fresh private target directory | Debug log SHA-256 | Control log SHA-256 | Score |
| --- | --- | --- | --- |
| `build/private/phase1b-projection-interleave132-target-r1/` | `f27b4ca5e99ea4d3019fdd6b67096c7182e4fe1731a8e795952444896f1d8033` | `d5bc2d373190f85be203eb71da6dbf76201655a972c7be09aa3f2fefdaad0079` | 20/20 |
| `build/private/phase1b-projection-interleave132-target-r2/` | `f27b4ca5e99ea4d3019fdd6b67096c7182e4fe1731a8e795952444896f1d8033` | `e13e54015322ef1ef0bfa725dcab56342a619a3dc85ef8f5c66ce6c69ca2b4c7` | 20/20 |
| `build/private/phase1b-projection-interleave132-target-r3/` | `f27b4ca5e99ea4d3019fdd6b67096c7182e4fe1731a8e795952444896f1d8033` | `ddf89788cfa5176e0541cd8b55abaf6200dd80dfb92d4290d72178c1df9abd83` | 20/20 |

**Reproduction:** use the exact command, MAME/build/host/ROM/state hashes, and input-only capture SHA-256 values in the pretarget plan. Run `python3 tools/phase1b_projection_interleave_predict.py validate build/private/phase1b-projection-interleave132-frozen.json build/private/phase1b-projection-interleave132-target-rN` for `N=1,2,3`. The input phase logs Sub-Y's CPU-local `CURPC` only at main target entry; it logs no later main lock/copy values. The output phase logs main entry, lock-acquired and copy-stage count and slot, but no Sub-Y entry-state input. ROMs, saved state, raw logs and commercial disassembly stay ignored/private.

**Engineering interpretation — verified by execution for these windows:** Sub-Y's sampled execution state supported a short forward prediction of whether one record entered the shared list before main acquired the lock. The pulse-132 target output sequence was numerically identical to the pulse-124 development output for these five markers, even though one sampled Sub-Y PC differed. Thus this result gives limited evidence about changing steering conditions; it is a **local execution-state signature**, not a recovered scheduler algorithm or a track/steering-to-list-slot model. **Unsupported:** other Sub-Y PCs/branches, count behavior after marker 969, active-buffer selection, actual Y-Board scheduler timing, original arcade hardware and a complete Sega CD camera adapter. No physical hardware, Sega CD emulator or cycle benchmark was run. A useful next test would choose a later window whose count or interleaving sequence actually differs between input schedules, then validate a rule using earlier Sub-Y object/branch state rather than a fixed PC whitelist.
