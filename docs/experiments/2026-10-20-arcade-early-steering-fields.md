# Phase 1B: early steering-response fields — 2026-10-20

**Question / hypothesis:** can a bounded, earlier RAM comparison find direction-sensitive values outside the stack-correlated `$1FFFxx` area, and can debugger writes and local code inspection explain how they update? **Baseline:** [mirrored steering and upper-RAM watchpoints](2026-10-20-arcade-mirrored-steering-watchpoints.md). **Acceptance:** centered/left/right repeats agree within condition, agree before the pulse, isolate a small early differential, identify the writing CPU and instruction sites, and preserve the replay under tracing. **Result — PASS, verified by execution:** four shared-RAM bytes differed persistently from callback 962 onward; three nearby words have repeatable, distinct update patterns, and MAME traced their writes to the main 68000. Their gameplay meanings are still **unsupported**.

## Environment, capture and reproduction

**Verified by execution:** baseline Git commit `ade2c23` on `experiment/perspective-road`; `tools/phase1b_mame_input.lua` was extended locally for this experiment and had SHA-256 `a62b1c436abc45b504254ff0ac058737d814e8bb09993447c94b95c2de46a71f` in the final trace/disassembly run. macOS 26.6.2 x86_64; MAME 0.289 (`unknown` revision string), executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; owner-local, ignored 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. No compiler, game build or Sega CD image was involved. All results are emulator observations; no physical arcade or Sega CD hardware was tested.

**Documented only:** the [MAME 0.289 Y-Board driver](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) maps `$0C0000–$0CFFFF` as RAM shared among the three 68000s and `$1F0000–$1FFFFF` as main-CPU RAM. [MAME's Lua debugger API](https://docs.mamedev.org/luascript/ref-debugger.html) exposes per-CPU watchpoints; its [disassembly command](https://docs.mamedev.org/debugger/memory.html) can save a bounded local code view. We used those documented facilities and did not modify MAME.

Six fresh, ignored runs live under `build/private/phase1b-early-{center1,center2,left1,left2,right1,right2}/`. The established input schedule is unchanged: coin at callbacks 60–64, start at 130–134, pedal 255 from 240, centered steering 128, with a left pulse of 64 or right pulse of 192 at callback 960. `PDRIFT_RAM_PROFILE=early` captures six 16 KiB pages at callbacks 960, 961, 962, 965, 970, 980, 1000 and 1020: main `$1F4000`, `$1F8000`, `$1FC000` and shared `$0C4000`, `$0C8000`, `$0CC000` as page bases. Each run saved 48 private binaries and reached the callback-1020 screenshot. Run from its fresh directory, setting `PDRIFT_STEER_PULSE` only for left/right:

```sh
PDRIFT_RAM_DIR=<DIR> PDRIFT_SNAPSHOT_DIR=<DIR> PDRIFT_RAM_PROFILE=early /usr/local/Cellar/mame/0.289/bin/mame pdrift -rompath /Users/murilo/repos/PowerDriftCD/build/private/phase1b-roms -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

Compare all six conditions without printing raw RAM contents:

```sh
python3 tools/phase1b_ram_diff.py build/private/phase1b-early-center1 build/private/phase1b-early-center2 build/private/phase1b-early-right1 build/private/phase1b-early-right2 --left build/private/phase1b-early-left1 build/private/phase1b-early-left2 --profile early
```

For the writer trace, three further fresh directories `build/private/phase1b-early-trace-{center,left,right}/` used the same command plus `PDRIFT_DEBUG_WATCH=shared -debug -debugger none -debuglog`; these options arm write watchpoints on `$0CE0CE–CF`, `$0CEA0E–0F` and `$0CFF26–27` for all three 68000s from callback 960 until 965. A final centered run in `build/private/phase1b-early-disasm-center/` also set `PDRIFT_DISASM_DIR` to that directory. MAME saved three short, private disassemblies near the observed writer PCs. No disassembly, raw RAM, screenshot or commercial asset is tracked.

Raw `phase1b-input.log` SHA-256 hashes for center1/center2, left1/left2 and right1/right2 were respectively `38f5e5db4295fb9a4bace7e8f91b4af9e6b52f4ea176f6c02e8348162ab32ab0` / `537501d4efa8d4d085b12c4042a7e1d3a381dfeec4eb83c975b1a7007cc11245`, `8e24ae59790e1e15e953b25c5b7ab6666b9b57a476961155c918cb7764dc2ee0` / `501cb3e1b0c59f16faf61cbc1b75912ced7244178fe1203913fdff300a28b970`, and `ad0f41aef455e78892589d5fb1718d4d728b32696f853c3835d6eb537eb90dde` / `0ee692dbfa38eee72a2b4264fb9a1274f87b0a5e9ea0a5a39084e69b596386e2`. A composite digest of each run's 48 files, formed by SHA-256 over sorted `filename + NUL + binary file SHA-256`, matched within each pair: center `e878be9ce02951720f6922bbd8bacfb79d85481ac5bb80b8ebc456a4133ba074`, left `bc625322d422e038c8c95b41a826f4a8959baef36abb7a11049f9333418d095c`, right `6af9b4b724af6bd5e0d0154d50c8035a0eb2d2835ff5418fe21263b49beed45b`.

## Findings

**Verified by execution:** every within-condition repeat matched byte-for-byte in all 48 captures. The conditions matched at callbacks 960 and 961. At 962, main middle pages and shared `$0C4000` page still matched; main-high showed transient differences, shared `$0C8000` had hundreds of changed bytes, and shared `$0CC000` had only five left-versus-right differing byte positions. Across all later checkpoints, four shared-high byte addresses differed persistently in both steering directions: `$0CE0CF`, `$0CEA0E–0F`, and `$0CFF27`. Callback-1020 screenshot hashes were center `55560dca0833f8fb44774882736933fc0f2edef4af1770ef776e9047b3e9bebb`, left `156534cb05687f8775b77ab01e7c087945c6708f6fb736e771a7904e5daa004b`, and right `4c450264012e1a338f394c469070fb1557e6e6e0e4c38c5ef3b5d377517dc7d0`; each matched its prior uninstrumented condition.

The three watched 16-bit words, read from the main CPU's shared-RAM view, had these values. Hex words are observations, not named game variables:

| Callback | `$0CFF26` left/center/right | `$0CE0CE` left/center/right | `$0CEA0E` left/center/right |
| ---: | --- | --- | --- |
| 961 | `FF80 / FF80 / FF80` | `0000 / 0000 / 0000` | `0000 / 0000 / 0000` |
| 962 | `FF40 / FF80 / FFC0` | `FF93 / 0000 / 006D` | `0001 / 0000 / FFFE` |
| 965 | `FF40 / FF80 / FFC0` | `FF93 / 0000 / 006D` | `0003 / 0000 / FFFC` |
| 970 | `FF40 / FF80 / FFC0` | `FF93 / 0000 / 006D` | `0009 / 0000 / FFF6` |
| 1020 | `FF40 / FF80 / FFC0` | `FF93 / 0000 / 006D` | `001C / 0000 / FFE3` |

**Verified by execution:** MAME logged 6/7/7 watch events in the centered/left/right traces over callbacks 960–965, all on `:maincpu` and none on `:subx` or `:suby` in that interval. The `$0CFF26–27` writes were observed with reported PC `$0374B4`, `$0CE0CE` with PC `$037550` when nonzero, and `$0CEA0E` with PC `$034F82`. All three traced callback-962 shared-high snapshots and callback-1020 screenshots matched their untraced counterparts. Debug-log SHA-256 hashes for center/left/right were `ead4673335ea1f61569e1e3d7088ebddd37a36184aa304d728527917022352c8`, `5d769b087fb9450f8da044fa01ada2617305e4ca1efcd206ba543a93cc4b0605`, and `5a2919273c17bb7384ec471998aeea138f3ca48ca0baee525d97f90a5f9b83f1`.

**Verified by local disassembly and trace correlation:** the write immediately before PC `$0374B4` stores one byte in a small indexed area near `$0CFF20`; the watched byte equals the scripted 64/128/192 steering setting. The write immediately before PC `$037550` stores a 16-bit value at `$0CE0CE` after bounding it to approximately ±127. The write immediately before PC `$034F82` adds a signed increment bounded to ±2 per update to `$0CEA0E`. These are independently authored descriptions of the locally inspected instructions, not copied disassembly. Private `input.asm`, `offset.asm` and `accum.asm` SHA-256 values were `b2d339f6117db4480971af40f41136d590e804f616d5c1ebbdd08af42cf12158`, `c43f8070d465b04a33bd3e35907154afa1038d1a298b64642bb65e9072777f6e`, and `0678b40a08b46f22fd9ca041a0e90e639e3b402102c1a2ca7af04c8f66ab191c`.

**Interpretation — hypothesis:** `$0CFF27` appears to be a sampled steering byte. `$0CE0CE` appears to be a bounded direction-dependent quantity, while `$0CEA0E` appears to be a gradual response or accumulator. Neither watchpoints nor the short disassembly establish whether either derived quantity is vehicle motion, camera state, or another control effect. They are not ready to feed the Sega CD five-word interface.

**Limits — verified by execution:** only six 16 KiB pages and eight callbacks around one Stage 1 pulse were sampled. The trace covers three word ranges and five callbacks. The three 68000s share the RAM, but absence of sub-CPU writes to these watched locations in that window does not establish their general workload. No complete track section, camera trajectory, Ghidra/REA correlation, original-hardware behavior or performance measurement was produced. Host run speed is not arcade timing.

**Regression check — verified by execution:** a fresh centered, default-profile 30-second replay under ignored `build/private/phase1b-regression-baseline/` matched the previous centered baseline's screenshots at callbacks 900, 1020, 1200 and 1800, and all 18 baseline RAM captures at callbacks 900–1200. The optional early profile and debugger hooks did not alter the established default replay in this test.

**Next experiment — hypothesis:** trace reads as well as writes to the two derived words, then inspect the consumers and the base registers feeding the bounded-value calculation. Compare a shorter and weaker steering pulse to separate direct input sampling from sustained vehicle/camera response. Only translate a field into the Sega CD camera commands after its meaning is supported by both dynamic behavior and code/data references.

**Follow-up — verified by execution:** [the rotation-consumer experiment](2026-10-20-arcade-rotation-consumer.md) traced `$0CEA0E` reads on the Y sub-CPU and found repeatable changes in its mapped rotation-parameter area after strong and weak steering pulses. Its exact gameplay meaning remains unsupported.
