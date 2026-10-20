# Phase 1B: steering-derived rotation consumer — 2026-10-20

**Question / hypothesis:** does the direction-sensitive shared word `$0CEA0E` reach the Y-Board rotation path, and does a brief, weak steering pulse separate immediate input from slower transformation state? **Baseline:** [early steering-response fields](2026-10-20-arcade-early-steering-fields.md). **Acceptance:** locate actual reader CPUs and instruction sites, find a repeatable change in the rotation parameter area after the pulse, and keep the established replay unchanged. **Result — PASS, verified by execution:** the Y sub-CPU reads `$0CEA0E` and writes the rotation parameter area; the captured 32-byte area changes after steering, reproducibly in both directions. The physical meaning of that word and its individual camera axes remains **unsupported**.

## Environment and method

**Verified by execution:** starting source revision `7918a51` on `experiment/perspective-road`; final local `tools/phase1b_mame_input.lua` SHA-256 `ad0c9cb8bad67117d88188d09623de882ea041a549b593a96510ce8cd059936f`. macOS 26.6.2 x86_64; MAME 0.289 (revision string `unknown`), executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; private 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. The script evolved during this bounded experiment; the final replay regression used the stated final SHA. No compiler, Sega CD image, host-speed measurement, or physical hardware was involved.

**Documented only:** the [MAME 0.289 Y-Board driver](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) maps `$0C0000–$0CFFFF` as shared RAM and sub-CPU Y `$180000–$1807FF` as rotation RAM. The [MAME Sega video implementation](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaic16.cpp) interprets words `0x3F0–0x3FB` of a rotation buffer as six 32-bit transform parameters. Its rotation-control read swaps RAM and buffer, so a snapshot of the mapped RAM does not by itself identify which buffer the video renderer used at that instant. [Lua debugger watchpoints](https://docs.mamedev.org/luascript/ref-debugger.html) and [read-watchpoint syntax](https://docs.mamedev.org/debugger/watchpoint.html) supplied the tracing mechanism. Upstream MAME was not modified.

**Verified by execution:** each run started in a fresh ignored `build/private/phase1b-*` directory, reached callback 1020, and exited zero. The established replay inserts coin at callbacks 60–64, start at 130–134, pedal 255 from 240, and steering 128 otherwise. The strong-pulse runs set steering to 64 (left) or 192 (right) at 960 and restore 128 at 1080. The weak-pulse runs use 112 or 144 at 960 and restore 128 at 976. `PDRIFT_RAM_PROFILE=early` saves the six prior 16 KiB pages at callbacks 960, 961, 962, 965, 970, 980, 1000, 1020. `PDRIFT_ROTATE_DIR` saves 32 bytes at sub-CPU Y `$1807E0–$1807FF` at the last seven of those callbacks. The capture is a MAME program-space read, not a direct video-buffer probe.

Reproduce from a fresh ignored directory `<DIR>`; omit pulse variables for the centered control:

```sh
PDRIFT_RAM_DIR=<DIR> PDRIFT_ROTATE_DIR=<DIR> PDRIFT_SNAPSHOT_DIR=<DIR> PDRIFT_RAM_PROFILE=early PDRIFT_STEER_PULSE=112 PDRIFT_STEER_RETURN=976 /usr/local/Cellar/mame/0.289/bin/mame pdrift -rompath /Users/murilo/repos/PowerDriftCD/build/private/phase1b-roms -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

For a focused read trace, set `PDRIFT_DEBUG_WATCH=reads PDRIFT_READ_CPU=suby`, omit rotation capture if unnecessary, and add `-debug -debugger none -debuglog`. The script arms two-byte read watchpoints at `$0CE0CE` and `$0CEA0E` from callback 960 through 965. Optional `PDRIFT_DISASM_DIR=<DIR>` saves small, private disassemblies for inspection. The raw logs, RAM, screenshots, rotation captures and disassembly remain ignored; none are in Git.

## Consumer trace

**Verified by execution:** mixed-CPU read traces for centered, strong left and strong right each recorded 24 events over callbacks 960–965. Main-CPU reads included `$0CE0CE` at reported PC `$033920` and `$0CEA0E` at `$034F66` and `$034F82`; repeated `$037488` reads belong to the input polling path. Six events per run were `$0CEA0E` reads by `:suby`. The centered mixed trace `debug.log` SHA-256 is `412a948aed78660af3379fc407db33bb58fc60c3a56834d212c06c57e9456ddd`; left and right are `f5e534e6015c8e463ff02c1114ea34082e38905c66bb2d855e75819c66440b64` and `d18e3a9c8228a7e3230bee77409dd7a2fee75837cf2cea5f31f4af6ecdbbdfe7`.

**Verified by execution, instrumentation correction:** the action's `pc` expression in a `:suby` watchpoint printed a **main-CPU** PC while the debugger focused `:maincpu`. Those mixed-trace `:suby` PC values are invalid as sub-CPU locations. With `visible_cpu=:suby` and watchpoints restricted to that CPU, fresh centered and left runs both recorded three reads at actual sub-CPU PC `$013414` and three at `$01346E`. Their private `debug.log` SHA-256 was the same, `4da01ec003568831f48f832474f8d2c9f5c1363c2b76904975b11fbaae25cd08`. Each run reproduced all 48 prior condition-specific RAM captures and its callback-1020 screenshot. The earlier [writer report](2026-10-20-arcade-early-steering-fields.md) reported main-CPU PCs while main CPU was focused; this focus issue does not change those observations.

**Verified by local disassembly and trace correlation:** the instruction immediately before each actual sub-CPU read PC loads `$0CEA0E`. Nearby instructions combine that word with another shared word, use the result to select from local tables, and write six longwords to mapped rotation RAM `$1807E0–$1807F4`; a related block is also written at `$180010`. The private disassembly files `suby-13400.asm` and `suby-13450.asm` have SHA-256 `c6a89511a02b3812d6ec93a219645b34c8ffb7f44c9af56d9253a8ab5ed91cf9` and `f383697057fa4600c46bdce825bd489175786cb9d1a27d259d3ced62c35cd5ae`. Main PC `$033920` copies `$0CE0CE` to another structure; its later use is **unsupported**. No original code or table bytes are reproduced here.

## Rotation-RAM and short-pulse observations

**Verified by execution:** two fresh runs per strong condition under `build/private/phase1b-rotate-{center,left,right}{1,2}/` matched byte-for-byte within each pair, for all 48 early RAM captures, seven 32-byte rotation captures, and the callback-1020 screenshot. SHA-256 over sorted `filename + NUL + binary file SHA-256` for the seven rotation files was center `48a3a8c70d8bd13458cb0538630a23c62d8141d81c963fca757b560b624c3b3d`, left `5772a624c6b49fa3417fde82c96c6a0c974e32c75f1827644585415983d2faf0`, right `818058015e869f03255669e5aee965c89b84c87b7dfac6a1a0c6673f97680ab4`. Each condition's 48-page composite digest and screenshot hash also matched the previous uninstrumented runs.

The table counts bytes, among the 32 captured at `$1807E0`, differing from the centered capture at the same callback. It is **not** a count of pixels or a timing measurement.

| Callback | Strong left 64 | Strong right 192 | Weak left 112 | Weak right 144 |
| ---: | ---: | ---: | ---: | ---: |
| 961 | 0 | 0 | 0 | 0 |
| 962 | 0 | 0 | 0 | 0 |
| 965 | 7 | 12 | 0 | 8 |
| 970 | 14 | 14 | 7 | 12 |
| 980 | 14 | 14 | 13 | 13 |
| 1000 | 13 | 13 | 13 | 13 |
| 1020 | 13 | 13 | 7 | 12 |

**Verified by execution:** weak left/right runs under `build/private/phase1b-weak-{left,right}{1,2}/` also matched their partner's 48 RAM files, seven rotation captures and callback-1020 screenshot. Their rotation composite digests were left `67fdad6a1c79fa7c518140bffd33cb29adb5e0001ddf570935a1731d8fc755c2`, right `99eb5639815a958f45109e1523c5f9422256e54d03d52b6893ab1b7f297e6d08`. Screenshot SHA-256: left `37d68d41c4766ee9335d4662cdcabe8532780f91208fde2e3495659df42f6ead`; right `3b81ad21e55d0dedb669fbd5e21ea27c6e7c4163609225f336e9de36cade3962`. Visual inspection showed a smaller left/right displacement than the strong pulse, but exact screen geometry was not measured.

Weak-pulse word observations (left / center / right, hexadecimal) show the separation between the immediate input and later response:

| Callback | `$0CFF26` | `$0CE0CE` | `$0CEA0E` |
| ---: | --- | --- | --- |
| 961 | `FF80 / FF80 / FF80` | `0000 / 0000 / 0000` | `0000 / 0000 / 0000` |
| 962 | `FF70 / FF80 / FF90` | `FFE5 / 0000 / 001B` | `0000 / 0000 / FFFF` |
| 965 | `FF70 / FF80 / FF90` | `FFE5 / 0000 / 001B` | `0001 / 0000 / FFFF` |
| 970 | `FF70 / FF80 / FF90` | `FFE5 / 0000 / 001B` | `0002 / 0000 / FFFD` |
| 980 | `FF80 / FF80 / FF80` | `0000 / 0000 / 0000` | `0005 / 0000 / FFFB` |
| 1000 | `FF80 / FF80 / FF80` | `0000 / 0000 / 0000` | `0003 / 0000 / FFFC` |
| 1020 | `FF80 / FF80 / FF80` | `0000 / 0000 / 0000` | `0001 / 0000 / FFFE` |

**Hypothesis:** `$0CEA0E` is a smoothed phase or orientation input to the Y-Board transform calculation. The chronology is consistent with input sampling, a bounded direction-dependent value, accumulated response, then rotation-parameter changes. The reads and code path make the consumer relationship stronger than screenshot correlation alone. **Unsupported:** identifying it as camera yaw, camera bank, car heading, or track coordinate; equating captured rotation RAM with the active display buffer at each sampling instant; deriving real-arcade timing from callback intervals; or mapping it directly to a Sega CD camera command.

**Regression — verified by execution:** a final-script centered run in `build/private/phase1b-read-regression-default/` matched the prior centered early run's 48-file RAM composite digest `e878be9ce02951720f6922bbd8bacfb79d85481ac5bb80b8ebc456a4133ba074` and callback-1020 screenshot SHA-256 `55560dca0833f8fb44774882736933fc0f2edef4af1770ef776e9047b3e9bebb`. No rendering source was changed.

**Next experiment — hypothesis:** trace the rotation-control swap and one active-buffer consumption point for a short fixed interval, then relate selected transform parameters to screen-space road displacement. Only after that should we attempt to recover a deterministic arcade camera/track sample or an adapter to the Sega CD five-word interface. Ghidra/REA correlation, full track data, a second emulator, and physical hardware are **not run** in this experiment.
