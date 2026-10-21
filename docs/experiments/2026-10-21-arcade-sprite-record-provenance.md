# Phase 1B: provenance of one steering-sensitive sprite coordinate — 2026-10-21

**Question / hypothesis:** does the X-position write for the previously isolated Y-sprite entry at `$E630` derive from a main-CPU record, and does changing that upstream record reproduce the visible edge movement? **Baseline:** the callback-950 private save state, centered/left/right steering replays, and the [validated Y-sprite slot intervention](2026-10-21-arcade-ybitmap-sequence-and-writer.md). **Acceptance:** trace the record through CPU writes despite possible list reordering; alter one upstream word before the list copy; observe the descriptor, native bitmap, and composed screen; include a same-value control. **Result — PASS, verified by execution in MAME:** the main CPU's `$0C1C84` word reaches the shared sprite list, sub-CPU X transforms it into `$18E632`, and changing that one word shifts the same sampled screen boundary in both steering directions. The object's game-level identity remains **unsupported**.

## Environment and method

**Verified by execution:** starting project revision `8aa9eeae97ed53a4e6f450f3a69554642115faaa` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, built with the [capture-only patch](../../tools/phase1b_mame_ybitmap.patch), executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`. The owner-local 53-file ROM manifest SHA-256 was `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; the private callback-950 save-state SHA-256 was `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. All addresses below are MAME 68000 program-space addresses. No proprietary data is tracked.

**Verified by execution:** the original Lua replay gained optional conditional sub-CPU breakpoints (`PDRIFT_YSPRITE_INPUT_TRACE=1`), configurable all-CPU shared-memory watchpoints (`PDRIFT_SHARED_WATCH_ADDR`), and a main-CPU write tap at `$0C1C84` (`PDRIFT_RECORD_TAP=1`). The tap can substitute a 16-bit word at one selected callback, and asserts a complete `FFFF` write mask. These additions are inert unless their variables are enabled. The Lua SHA-256 is `f23de78d4fd8eef5e71d6b1fb13775a221656e3511da5fc2570a6b46e3665b02`.

Reproduce a targeted left replay in a fresh ignored working directory (change `64` to `192` for right steering). The state and ROM path are owner-local; the image data, traces and screenshots stay under `build/private/`:

```sh
SDL_VIDEODRIVER=dummy PDRIFT_YBITMAP_DIR=. PDRIFT_RAM_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_RAM_PROFILE=early PDRIFT_RECORD_TAP=1 PDRIFT_RECORD_OVERRIDE_FRAME=963 PDRIFT_RECORD_OVERRIDE_VALUE=0019 PDRIFT_STEER_PULSE=64 PDRIFT_STATE_LOAD=/absolute/private/callback950.sta /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

**Verified by execution:** the trace-only replays used `-debug -debugger none -debuglog` and `PDRIFT_DEBUG_WATCH=ysprite PDRIFT_YSPRITE_WATCH_OFFSET=E630 PDRIFT_YSPRITE_INPUT_TRACE=1 PDRIFT_YSPRITE_REGS=1 PDRIFT_DISASM_DIR=.`; separate replays used `PDRIFT_DEBUG_WATCH=shared PDRIFT_SHARED_WATCH_ADDR=0C9A30` for left and `0C9A60` for center/right, plus `PDRIFT_SHARED_REGS=1 PDRIFT_DISASM_DIR=.`. A watch at source record `$0C1C80` traced the main-CPU record writer. These were separate runs because a source-list address is not stable across steering conditions. The conditional breakpoints and list watchpoints captured the same final record values as the no-debug runs. [MAME's Lua debugger API](https://docs.mamedev.org/luascript/ref-debugger.html) **documents only** the breakpoint/watchpoint operations; the trace behavior and values here were **verified by execution**.

## Observed data path

**Verified by execution:** at callback 963, the main-CPU write tap saw a full-word write at `$0C1C84`: center `0019`, left `001E`, right `0013`. The main-CPU writer near PC `$033E58` writes this coordinate to `(4,A5)` with `A5=$0C1C80`; near `$033E84–$033E8E` it copies 16 bytes from that record into a shared sprite list based at `A0=$0C9800`. The watched list destination for the final `$E630` sprite differs: left uses offset `$0230` (`$0C9A30`), while center and right use `$0260` (`$0C9A60`). The identity word `8B3D0020` and matching non-coordinate fields link these records; equating a fixed list address between steering replays would be incorrect.

**Verified by execution:** in the sub-CPU-X trace, the final record load at PC `$00DD64–$00DD6A` uses that list offset while `A2=$18C630`. Its D1 upper word is respectively `001E`, `0019`, or `0013`. The transform/writer at PC near `$00E0BA` emits the sprite descriptor's second word at `$18E632`: left `0696`, center `0693`, right `0690`. The official [MAME 0.289 Y-sprite renderer source](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/sega16sp.cpp) **documents only** the descriptor's low 12 bits as its X-position field. This source interpretation is consistent with the observed position change, but is emulator-source evidence rather than independent physical-hardware validation.

```text
main CPU $0C1C84 (+4 in $0C1C80 source record)
  → main CPU copy at $033E84–$033E8E
  → shared list $0C9A30 (left) or $0C9A60 (center/right)
  → sub-CPU X load at $00DD64–$00DD6A
  → transformed Y-sprite descriptor $18E632
  → intermediate Y bitmap → affine pass → composed screen
```

## Controlled intervention

**Verified by execution:** replacing only the callback-963 main-CPU `$0C1C84` write with centered value `0019` changed the callback-966 final descriptor and the later displayed edge. The prior direct `$E630–$E63F` descriptor restoration provides an independent downstream comparator. `tools/phase1b_record_path_compare.py` (SHA-256 `1d5510eed53e42b00d3052f001b5c150616f859c2f26215ab688b18cc8757717`) checks private captures without exporting image data:

```sh
python3 tools/phase1b_record_path_compare.py build/private
```

| Steering / intervention | `$E632` low 12 bits | Callback-967 row-165 boundary x | Changed callback-967 screen pixels vs steering baseline |
| --- | ---: | ---: | ---: |
| Left baseline | `696` | 61 | — |
| Left, main record `001E→0019` | `693` | 58 | 2,735 |
| Left, same-value sham `001E→001E` | `696` | 61 | 0 |
| Right baseline | `690` | 58 | — |
| Right, main record `0013→0019` | `693` | 61 | 2,590 |

**Verified by execution:** each upstream intervention's 524,288-byte frame-966 native bitmap was byte-identical to the corresponding direct descriptor restoration, and its decoded callback-967 RGB screen pixels matched exactly. The left intervened bitmap SHA-256 is `33f5a4b752db74b663bb383f07840f849128bc2d191f6d2b8c171197f41f229b`; right is `d73cb2037090881b2538fcc1413df6e249a0965abf2bd974dfa89ea2b327021f`. Changed screen pixel counts relative to each steered baseline were left: callback 967 `2735`, 968 `3815`, 969 `4807`; right: 967 `2590`, 968 `3701`, 969 `5032`. All other captured callbacks 960–970 matched their respective baselines. The sham left record, bitmap and all callbacks 960–970 matched the baseline. A repeated left intervention reproduced the descriptor RAM, bitmap and callback-967 PNG byte-for-byte. These are pixel counts and emulated frame indices, not timing or performance measurements.

The ignored raw logs are `build/private/phase1b-record-override-{left,right,sham-left}/phase1b-input.log` (SHA-256 respectively `769f658d9f5ad2d76172b30917f5908530f25b5b19e838fb0dcd385256853a87`, `7ab4639b3cc3bb9d3e433b0164f2f42f521996bc3461864fe84f9d99dd2634ba`, `14267daddf526594d1f1468b650992e648f2c16fba06c7e20dc0bac391678605`). The repeated left log SHA-256 is `e0d96c2ff17bff9cb7492beb770b6b8646ab5c0668df7994a5d630fee26fdedf`. Representative ignored debug logs: `build/private/phase1b-e630-input-left/debug.log` SHA-256 `575d655cf05886cc7cb5924914a73e7f72f6a6f9c7850f6ab4ba605de5ea7919`, and `build/private/phase1b-input-record-9a60-center/debug.log` SHA-256 `12b2f727fe7ea2f932424d3421d93b40644b6a976908473d456263b0e1708d1c`.

## Interpretation and next bound

**Inference from verified execution:** the visible boundary depends causally on a main-CPU-generated sprite coordinate and a later sub-CPU-X projection. This is stronger than observing a steering correlation. **Unsupported:** that this record is a road segment, camera state, track curvature/elevation, or a suitable five-word Sega CD camera input. The screen region includes scenery and overlapping Y sprites, and the main CPU's inputs to its projection routine were not identified. The list's three-entry shift also warns against following raw addresses as object identities. This test did not measure arcade or Sega CD performance, run a second arcade emulator, or use physical hardware.

**Next bounded test — hypothesis:** identify the specific object represented by `$0C1C80` using its persistent identifier and sprite source fields, then trace only the main projection routine's inputs to see whether any independently observed track/camera variable feeds it. If identity or provenance remains ambiguous, retain this as a sprite-rendering finding and seek a separate track-state candidate; do not feed these coordinates into the Sega CD camera interface as though they were a verified road trajectory.
