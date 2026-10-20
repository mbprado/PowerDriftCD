# Phase 1B: bounded Stage 1 RAM differential — 2026-10-20

**Question / hypothesis:** can a controlled steering pulse produce repeatable RAM differences at the same arcade frame, suitable for later debugger tracing? **Baseline:** [centered versus pulse image replay](2026-10-20-arcade-steering-control.md). **Acceptance:** two independent runs per condition agree byte-for-byte, the conditions agree before the pulse, and any later changed addresses are reported as candidates only. **Result — PASS, verified by execution:** all within-condition RAM captures agreed; centered and pulse captures agreed at callbacks 900 and 960; later captures differed in upper main-CPU RAM and shared RAM. No camera, track or physics variable has been identified.

**Documented only:** the [MAME 0.289 Y-Board driver](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/segaybd.cpp) maps main work RAM at `$1F0000–$1FFFFF` and shared RAM at `$0C0000–$0CFFFF`. [MAME's Lua address-space API](https://docs.mamedev.org/luascript/ref-mem.html) exposes `read_u8`. The selected windows are map-based samples, not inferred game structures.

## Method and reproduction

**Verified by execution:** baseline source commit `13c5c9a` on `experiment/perspective-road`, with the RAM-capture changes to [`tools/phase1b_mame_input.lua`](../../tools/phase1b_mame_input.lua) uncommitted during execution; final tested script SHA-256 `07f25e66873c50ee6645b96a5407addde312c4d0b8be5093a01f8383554ec7b8`. macOS 26.6.2 x86_64; MAME 0.289 (`unknown` revision string), executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The owner-local, ignored 53-file `pdrift-2` ROM manifest had SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. No compiled game image was generated; MAME executed that private ROM set directly. No original ROM bytes or RAM dumps are tracked.

The original input sequence remains coin callbacks 60–64, start 130–134, pedal 255 from 240, steering 128 otherwise. Pulse runs set steering 192 at callback 960 and restore 128 at 1080. Lua saves screenshots and reads three 16,384-byte windows from the main CPU's program space at callbacks 900, 960, 1020, 1080, 1140 and 1200: `$1F0000–$1F3FFF` (`main_low`), `$1FC000–$1FFFFF` (`main_high`) and `$0C0000–$0C3FFF` (`shared`). These are read-only observations. Callback 960 is captured after setting the input field but before the following emulated frame processes it.

Each of four fresh working directories `build/private/phase1b-ram-extended-{center1,center2,pulse1,pulse2}/` was separate and ignored. From each directory, run the following with absolute paths as shown; set `PDRIFT_STEER_PULSE=192` only in the pulse runs, and replace `<DIR>` with that run's absolute directory:

```sh
PDRIFT_RAM_DIR=<DIR> PDRIFT_SNAPSHOT_DIR=<DIR> /usr/local/Cellar/mame/0.289/bin/mame pdrift -rompath /Users/murilo/repos/PowerDriftCD/build/private/phase1b-roms -noreadconfig -video none -sound none -nothrottle -seconds_to_run 30 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

Analyze the private binary captures without emitting ROM or RAM contents:

```sh
python3 tools/phase1b_ram_diff.py build/private/phase1b-ram-extended-center1 build/private/phase1b-ram-extended-center2 build/private/phase1b-ram-extended-pulse1 build/private/phase1b-ram-extended-pulse2
```

All four runs completed 1,800 callbacks. Raw logs and 18 binary RAM captures per run remain at the above ignored paths. Log SHA-256 values, in run order, are `eaaa3af274356cca6e6031bc7bfb198d41eb78601a97c82062e64840fe92cc95`, `d15651be9486f0556bfd9d02c4ad7b0228814eec86a3781eab223e71391c3ace`, `15d75a21dc41a1928fc849123f8ee144c56f17922ba638c524e9ee2c82df2896`, `12bb8b830b9dffe7295800536186cd28389b6dceee41f6a4813a73b0741da8a6`. At callback 900 every run's screenshot SHA-256 was `1ca21c0cebf2ea0b10ac249b60cfb949de860030fb1a790d22a54833dd7c8a25`; at 1020 the centered screenshot was `55560dca0833f8fb44774882736933fc0f2edef4af1770ef776e9047b3e9bebb` and the pulse screenshot was `4c450264012e1a338f394c469070fb1557e6e6e0e4c38c5ef3b5d377517dc7d0`. Each condition's two 1020 screenshots matched. Host run speed is irrelevant to arcade timing and is not reported as a performance result.

## Observations

**Verified by execution:** all 72 binary captures were exactly 16,384 bytes; within-condition repeats matched at every checkpoint. The table counts byte positions that differ between centered and pulse captures at the same callback, not distinct variables or writes.

| Callback | Main low | Main high | Shared |
| ---: | ---: | ---: | ---: |
| 900 | 0 | 0 | 0 |
| 960 | 0 | 0 | 0 |
| 1020 | 0 | 26 | 2,267 |
| 1080 | 0 | 30 | 2,914 |
| 1140 | 0 | 37 | 2,916 |
| 1200 | 0 | 30 | 2,821 |

**Verified by execution:** the sampled main-low page contained only zero bytes in all four runs at every checkpoint. The main-high page contained sparse differences: 23 byte addresses differed at all four post-pulse checkpoints, including the paired locations `$1FFF72–73`, `$1FFF7A–7B`, and clusters from `$1FFFC4` to `$1FFFE5`. The exact 23 addresses are emitted by the analysis script. Shared RAM had 1,930 byte addresses differing at all four later checkpoints, so this window is less selective for finding individual control variables. These bytes may include render or derived state; their meanings are **unsupported**.

**Limitations — verified by execution:** two 16 KiB portions of the 64 KiB main RAM and one 16 KiB portion of the 64 KiB shared RAM were sampled. No debugger write trace, disassembly correlation, opposite-steering control, or physical arcade board check was performed. A stable differential address is a candidate for tracing, not evidence of a specific game variable. The captures also do not establish whether a difference caused the changed image or followed from other changed state. No Sega CD rendering code or five-word camera interface was changed.

**Next experiment — hypothesis:** run a reversed steering pulse (e.g. 64) and inspect the small `$1FFFxx` differential cluster at additional early callbacks. Then use MAME debugger write watchpoints and 68000 code/data analysis to identify writers and distinguish input, vehicle, camera and derived state. Preserve all raw traces privately. Only after a candidate has independent dynamic and code evidence should it be translated into the Sega CD road camera commands.

**Follow-up — verified by execution:** [mirrored steering and debugger watchpoints](2026-10-20-arcade-mirrored-steering-watchpoints.md) reproduced the opposite-direction response and found that the sampled `$1FFFxx` addresses show stack-related write patterns. They must not be promoted to camera fields without independent code evidence.
