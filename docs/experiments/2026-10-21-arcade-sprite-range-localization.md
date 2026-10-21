# Phase 1B: localized Y-sprite RAM intervention — 2026-10-21

**Question / hypothesis:** which of the callback-966 Y-sprite RAM differences from the [source-divergence experiment](2026-10-21-arcade-sprite-source-divergence.md) change the composed callback-967 image? **Baseline:** the same center/left/right steering schedule and affine-pixel comparison. **Test:** restore small portions of the centered 64 KiB snapshot into a steered run after callback 966, while leaving the other steered RAM, inputs and rotation parameters intact. **Expected evidence:** equal pre-intervention RAM/screenshots, unchanged affine parameters, and a reproducible next-frame pixel change. No arcade sprite/track field meanings were assumed.

## Reproducibility

**Verified by execution:** source revision `b2b547ad91dfddac87750404947433dbf0bcafdd` before these edits; host macOS 26.6.2 x86_64; MAME 0.289 executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. Final Lua script SHA-256 `129d71c62c78e5a57462a0b5f0c90ec8060b8eb0bb535a5b471f76d0e0f4effd`; comparison tool SHA-256 `77b2f038ef99b79185530e5e2b4df383e3dd08537c9f33bf9150d94ffe2e1779`. This is an emulated image-behavior experiment, with no hardware timing measurement and no physical hardware test.

**Verified by execution:** a first standalone left-range replay diverged from the old baseline *before* callback 966: its screenshot at 300 matched, 600 differed slightly, and 900 showed a different race position. Its measurements were discarded. [MAME's Lua API](https://docs.mamedev.org/luascript/ref-core.html) documents `machine:save()` and `machine:load()`; the [MAME 0.289 driver](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) marks `pdrift` as supporting save states. We saved a private callback-950 state (SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`) and loaded it for every reported center/steered/intervention replay. Center and left Y-sprite RAM matched at 960 and 963, then differed by 139 bytes at 965 and 537 at 966. The center/left callback-967 affine agreement reproduced the earlier **60.44%** baseline exactly. Thus the reported comparisons share an emulated starting state; the reason for the earlier standalone replay's drift is **unsupported**.

The Lua script now accepts `PDRIFT_SOURCE_OVERRIDE_RANGE=start:size` in hexadecimal, requiring 16-byte alignment, to replace only the selected sub-CPU-X `$180000` Y-sprite RAM range after callback 966. It also accepts `PDRIFT_STATE_SAVE` and `PDRIFT_STATE_LOAD`. The local save state, owner ROMs, RAM snapshots, screenshots, logs and CSV files are ignored; no commercial data is in the source changes.

To reproduce privately, first create a fresh ignored working directory and run this command there to save the state:

```sh
PDRIFT_SNAPSHOT_DIR=. PDRIFT_STATE_SAVE=/absolute/private/callback950.sta /usr/local/Cellar/mame/0.289/bin/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

For each new center, left or right directory, use the same saved state with `PDRIFT_STATE_LOAD=/absolute/private/callback950.sta`, `PDRIFT_SNAPSHOT_DIR=.`, `PDRIFT_SOURCE_DIR=.`, `PDRIFT_SWAP_DIR=.`, `PDRIFT_ROTATE_DIR=.`, `PDRIFT_RAM_DIR=.`, and `PDRIFT_RAM_PROFILE=early`. Set `PDRIFT_STEER_PULSE=64` for left or `192` for right; omit it for center. For an intervention, also set `PDRIFT_SOURCE_OVERRIDE=/absolute/private/center/source-0966-ysprites.bin` and a range such as `PDRIFT_SOURCE_OVERRIDE_RANGE=e6e0:10`. Use the same MAME command line and a fresh directory for every condition. `tools/phase1b_range_compare.py CENTER STEERED VARIANTS...` checks pre-intervention RAM, screenshot and affine-block equality, then computes next-frame pixel changes and affine agreement.

The private comparison CSVs are `build/private/phase1b-range-compare-{left,right}.csv`, SHA-256 `815b4a939eaec6f70c686a0d84a11ad4e94a96d3938708d8fce7074001591c81` and `17bd7697be1aac7f5123cbe84d0bee33c4ae4b57616a10039f230ea11208185f`. Center, left and right callback-966 Y-sprite snapshot SHA-256 values are `4443c41565cd335e37825ffe0981f6a430a6376e6fe1810717b9e5396c4c06d2`, `1d72f65f68c2ccf58583eefb850c2bd2fa916686daeb1ac8bb33627cc3931d11` and `169c9b6d4eb5a302adcd686e39a068883dbe0edbbbf5eed90634c2`. The private range directories are `build/private/phase1b-range-state-*`.

**Verified by execution:** raw `phase1b-input.log` SHA-256 values for center, left, right, first left `$E000` intervention, repeated left `$E000` intervention and right `$E000` intervention are respectively `2f91c67f6cdf6255bb624ae0025627c759b7bbfae17aa74dd6ac28c15fbfd776`, `4fe92b90cb83a1dddb10bdff2103fc8798500488f912b646efe215a0e6bb2187`, `fc273dc5f6f7ad6c9534e55ae42caaae514135659a95d48385a68e04b753cb6f`, `a09c488404a926cc6332bb26c06957025f87eb6a1acf229895dde32fa950dba8`, `b2aa2641d98b5087ab59521ddb1003746d759c3a2a82c476a997efd88ec4c3df` and `b3ffa2ca8a3e245beed5ae84814fde3dfad7a509703b8c0f020f3567014fbb4c`.

## Result

**Verified by execution in MAME:** all reported intervention runs had byte-identical callback-966 *pre-write* Y-sprite RAM, screenshot and pre-swap affine block relative to their corresponding steered baseline. The table gives the **callback-967** exact RGB agreement with the affine prediction from the centered screenshot, for the same valid-pixel rectangle as the earlier report. A higher percentage means the selected replacement removed more of the image difference beyond the whole-screen affine transform. The percentages are image correspondence, not processing speed.

| Centered bytes restored at callback 966 | Left changed bytes | Left agreement | Right agreement | Visible pixel change, left |
| --- | ---: | ---: | ---: | ---: |
| None | 0 | 60.44% | 57.04% | 0 |
| `$8000–$9FFF` | 69 | 60.44% | — | 0 |
| `$A000–$BFFF` | 70 | 60.44% | — | 0 |
| `$C000–$DFFF` | 215 | 60.44% | — | 0 |
| `$E000–$FFFF` | 183 | **96.63%** | **94.86%** | 22,973 |
| `$E000–$E3FF` | 130 | 61.46% | — | 311 |
| `$E400–$E7FF` | 53 | **95.57%** | — | 22,687 |
| `$E400–$E5FF` | 21 | 81.83% | — | 8,913 |
| `$E600–$E7FF` | 32 | 74.16% | — | 13,801 |
| `$E6E0–$E6EF` | 11 | 60.70% | — | 302 |

**Verified by execution:** the `$E000–$FFFF` left intervention was repeated from the same state and produced a byte-identical callback-967 screenshot and the same 96.63% agreement. It also produced the same 96.63% result as the prior full-64-KiB replacement. The right `$E000–$FFFF` result reproduced the prior full-replacement 94.86% agreement. In the left runs, restoring only `$E400–$E7FF` accounted for almost all of the image-wide improvement, despite changing only 53 RAM bytes. Its screenshot differed from the steered baseline at 22,687 pixels. Narrower `$E400–$E4FF`, `$E500–$E5FF` and `$E600–$E6FF` interventions each had a visible effect (2,932, 6,038 and 13,801 pixels), so the dominant difference is distributed across multiple slots. Effects need not add linearly because sprites overlap and use priority.

**Verified by execution:** restoring the 16-byte aligned `$E6E0–$E6EF` slot changed 302 pixels, all inside screenshot coordinates `x=103–210, y=149–160`. Its callback-967 screenshot was byte-identical to the one from restoring the full 32-byte `$E6E0–$E6FF` interval. The affected band contains visible road and moving objects; the particular object or road feature controlled by the slot is **unsupported**. The 16-byte intervention screenshot SHA-256 is `3e53a69a66b7a6afbf1e77dca03ebfe0f78302053e3a2a0837a423022c2ef31d`; the full `$E000–$FFFF` left screenshot SHA-256 is `59fd6c3b9d65eebb16f49fd344357d4917e8cdf741376fa26ac90fe19b8f77e0`.

**Documented only:** [MAME 0.289's Y-Board sprite renderer](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/sega16sp.cpp) describes 16-byte sprite descriptors, linked indices and indirection data, with scanline extents from rotation RAM. The intervention addresses are mapped Y-sprite RAM offsets, but the current observations do **not** establish whether `$E6E0` is a descriptor, an indirection entry, or data copied/consumed elsewhere between callbacks. Calling it a track or camera field would be **unsupported**. The [driver](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) draws Y sprites into a 512×512 source bitmap, applies rotation, then composites B sprites; that ordering supports the observed distinction between source-image and affine changes.

**Limitations / next bounded test — hypothesis:** trace the `$E400–$E7FF` bytes to their consumer at the actual render instant, or capture a direct 512×512 Y-sprite bitmap from an isolated MAME patch, to assign a specific visible road-edge feature to a specific record. Then collect several adjacent unsteered and steered frames of that feature as a deterministic Stage 1 reference. The present experiment did not decode arcade track storage, measure original hardware timing, or test the five-word Sega CD camera interface against real arcade data.
