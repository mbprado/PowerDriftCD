# Phase 1B: one geometry depth through five display epochs — 2026-10-21

**Question / hypothesis:** can the same ROM-backed geometry depth be followed beyond the two previously verified visible strip epochs, and does it continue to supply a stable screen-edge reference? **Baseline:** [the short visible-strip attribution](2026-10-21-arcade-visible-strip-attribution.md), callback-950 owner-local state, center/left/right steering schedules. **Acceptance:** preserve the old 960–970 captures, follow depth `$3200` through five consecutive main-CPU projection/list/sub-CPU-X/descriptor updates, then hide only that descriptor in center-steering replays to determine where its visible contribution appears. **Result — PASS for the bounded data path, FAIL for a fixed-row edge reference, verified by execution in MAME:** 15/15 selected records matched across five epochs and three steering conditions. The sample's source geometry stayed unchanged through 41 callback snapshots. Its visible contribution moved down and was nearly clipped by the fifth epoch; screen row 150 contained it only in the first two.

## Environment and method

**Verified by execution:** starting Git revision `a295048` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing [capture-only patch](../../tools/phase1b_mame_ybitmap.patch). Owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 save-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The Lua probe gained an optional bounded capture ending at callback 1000 and frame markers in the existing sub-CPU debugger trace; SHA-256 `fc26b181f4709fa1d16be5a2ceb7dacb6d648ef8d97d1396eb6cc5b776e6ce32`. The new analysis tool `tools/phase1b_depth_sequence.py` SHA-256 is `32e6c5e18066651556480f10ea2f2cb0e38d1351477b905282bfea9b038e26fb`. No upstream emulator source was changed or new dependency introduced.

**Verified by execution:** each saved-state replay used the established held-pedal input and center steering 128, or a left/right pulse to 64/192 beginning callback 960. The 960–970 overlap matched previous captures: 396/396 geometry rows and 66/66 source-RAM/screen files across the three conditions were byte-identical. The fixed index-0 source fields had one depth, ROM table and ROM sample tuple across all 41 callbacks 960–1000 in each condition. This identifies a persistent *sample at depth `$3200`* in the current run, not the arcade's formal object name or track coordinate system.

Reproduce center steering from a fresh ignored directory, changing `PDRIFT_STEER_PULSE` to `64` or `192` for the other conditions:

```sh
SDL_VIDEODRIVER=dummy PDRIFT_GEOMETRY_SAMPLE_DIR=. PDRIFT_SHARED_LIST_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_SEQUENCE_END_FRAME=1000 PDRIFT_STATE_LOAD=/absolute/private/callback950.sta /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

For the independent sub-CPU execution trace, replace the geometry/list/source/rotation/swap output settings with `PDRIFT_DEBUG_WATCH=ysprite PDRIFT_YSPRITE_SEQUENCE_TRACE=1 PDRIFT_YSPRITE_SEQUENCE_END_FRAME=1000 PDRIFT_YSPRITE_WATCH_OFFSET=E630`, add `-debug -debugger none -debuglog`, and keep the same state and steering. The debugger log's `SEQUENCE_FRAME` markers assign sub-CPU loads to the callback interval in which they executed. Analyze the private files with `python3 tools/phase1b_depth_sequence.py build/private`. The script also checks the prior short-window captures and the visibility interventions below.

## Five matching epochs

**Verified by execution:** for main-CPU callbacks 960, 964, 968, 972 and 976, the index-0 projected X/Y words reappeared as one selected shared-list `pos` longword at callbacks 962, 966, 970, 974 and 978 respectively. Each complete list record matched one sub-CPU-X load in the preceding callback interval, and that load's output pointer matched a non-hidden Y-sprite descriptor in the captured sprite RAM. This held for 5/5 epochs in each of center, left and right steering, **15/15 total**. It extends the previous ROM-sample → projection → list → descriptor chain while preserving record identity through list reordering.

| Projected → list callback | Center list offset / descriptor offset | Center descriptor X | Center graphic-offset word | Right graphic-offset word |
| --- | --- | ---: | --- | --- |
| 960 → 962 | `$0260 / $E600` | `$6A9` | `$3888` | `$3888` |
| 964 → 966 | `$0260 / $E630` | `$693` | `$3888` | `$3888` |
| 968 → 970 | `$0260 / $E660` | `$668` | `$2898` | `$28B9` |
| 972 → 974 | `$0240 / $E660` | `$60A` | `$2898` | `$28B9` |
| 976 → 978 | `$0240 / $E640` | `$47A` | `$2898` | `$28B9` |

**Verified by execution:** the descriptor's graphic-offset word changes between the second and third epochs, despite the same index-0 ROM geometry tuple. The reason for the asset choice is **unsupported**; scale/bank/segment selection are possible hypotheses, not decoded behavior. Left and right descriptor positions also diverge under steering, and the right graphic-offset word differs from center/left after the transition. The list and descriptor offsets can change independently, so neither is a permanent identity.

## Visibility intervention and limit

**Documented only:** MAME's pinned [Y-Board sprite renderer](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/sega16sp.cpp) treats descriptor word-0 bit `$1000` as a hide condition while keeping the linked-list word intact. **Verified by execution:** a private source-RAM override changed that one bit, and only one byte of the captured 64 KiB source RAM, for the center descriptor at each of five display epochs. Earlier screenshots matched baseline. The next screen changed as follows:

| Hidden descriptor callback | Changed next-screen pixels | Changed screen bounding box | Row-150 contribution |
| --- | ---: | --- | --- |
| 962 / `$E600` | 1,902 at 963 | x 83–269, y 143–155 | 169 contiguous pixels |
| 966 / `$E630` | 3,986 at 967 | x 57–306, y 147–169 | 169 contiguous pixels |
| 970 / `$E660` | 11,589 at 971 | x 10–319, y 154–219 | none |
| 974 / `$E660` | 10,216 at 975 | x 0–319, y 168–223 | none |
| 978 / `$E640` | 1,158 at 979 | x 0–319, y 220–223 | none |

**Verified by execution:** native Y-bitmap differences were 1,932, 4,111 and 14,186 pixels at callbacks 962, 966 and 970 respectively. The existing isolated MAME capture patch records native bitmaps only through callback 970, so native-bitmap measurements at 974/978 were **not run**; the later screen and descriptor evidence remains direct. A callback-974 same-value override reproduced the baseline after-write source RAM and callback-975 screen. Repeating its hidden-descriptor run reproduced after-write source RAM and callback-975 PNG byte-for-byte. The 978 effect is confined to four bottom screen rows in this 320×224 MAME capture. Calling the sample *nearly clipped* is an inference from that measured screen extent; the game's own clipping rule and physical arcade timing were not independently established.

For later private interventions, copy `source-0970-ysprites.bin`, `source-0974-ysprites.bin` or `source-0978-ysprites.bin` from the center baseline and change descriptor word 0 from `$0005` to `$1005` at `$E660`, `$E660` or `$E640`. Reuse the baseline command with `PDRIFT_SOURCE_OVERRIDE_FRAME=970/974/978`, `PDRIFT_SOURCE_OVERRIDE_RANGE=E660:0010` or `E640:0010`, and `PDRIFT_SOURCE_OVERRIDE` pointing to that private 64 KiB file. Keep `PDRIFT_SOURCE_DIR=.` and `PDRIFT_SWAP_DIR=.`. The same-value and repeat controls used the callback-974 file and range.

Raw evidence remains ignored in `build/private/phase1b-depth-sequence-{center,left,right}/`, `phase1b-depth-subx-{center,left,right}/`, and `phase1b-depth-hidden-{970,974,978,974-sham,974-repeat}/`. Geometry CSV SHA-256 (center/left/right): `a5214e912dfdd84e9ed97feb54b74002f3de012c00f2fd2e3f77440e70e55c25`, `41d0a7d5ee3e801ce1021180c15d1cd4717587da329decf0c833758777e297b6`, `8b13e35fb598ade2b258a9ca395d39bcabd7ba79762495c18a1818ad1ce268ef`. Sub-CPU debug-log SHA-256: `0d49720ad3c1322be4003fae2e70d916075d9338ca32d0ad530142019914501c`, `176430030961ddb9c83f63647056eda09e79d500a9c3ec7206a763f6032c9fc8`, `bee5eb2922e26d122dc2fedb87895d4c6de02000ee881474ad51f70f5d6920df`. Hidden-run input-log SHA-256 for 970/974/978: `39fb964522a17d58b5cba87148ec25d04e052dd41339bc263ac9c3239816c3c3`, `52203f290927cc14922afdca2bcef141f12f9a1b393714396e040c8fb8609a38`, `e609354bec3929da78d6e42f07b26a5df74ed7b3e93778d389d6eb28d0c5ce16`.

**Inference from verified execution:** the `$3200` geometry sample is a useful short-lived rendering reference across five epochs, but its fixed screen-row boundary is unsuitable for a longer camera sequence because perspective motion, asset switching, overlap and clipping intervene. **Unsupported:** a decoded world-space road edge, camera pose, geometry units, or a demonstrated mapping into the Sega CD five-word camera interface. No Sega CD renderer change, second arcade emulator, physical hardware test or performance measurement occurred.

**Next bounded test — hypothesis:** choose a farther depth that stays in view longer, then repeat the identity/visibility check before proposing an arcade camera handoff. If far-depth records remain overlapped or asset-switched, identify the camera/global transform sequence independently and use the visible strips only as validation targets. Do not modify the Sega CD camera interface without a measured missing degree of freedom.
