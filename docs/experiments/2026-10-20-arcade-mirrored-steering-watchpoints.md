# Phase 1B: mirrored steering and upper-RAM watchpoints — 2026-10-20

**Question / hypothesis:** does a left steering pulse produce a repeatable response distinct from both centered and right-pulse replays, and do writes to the previously flagged `$1FFFxx` addresses support treating them as game-state fields? **Baseline:** the [bounded RAM differential](2026-10-20-arcade-ram-differential.md) found 23 upper-main-RAM byte positions that differed at all four later right-pulse checkpoints. **Acceptance:** two matching left runs, identical conditions before the pulse, debugger writes with PC and stack-pointer context, and unchanged output when instrumentation is enabled. **Result — partial PASS, verified by execution:** mirrored steering is deterministic and distinct; debugger watchpoints execute without changing the replay. **Hypothesis:** the most promising upper-RAM differences are stack-related rather than stable camera variables. No arcade camera field was established.

## Environment and method

**Verified by execution:** baseline Git commit `27abd17` on `experiment/perspective-road`; current `tools/phase1b_mame_input.lua` was modified locally during this experiment and had SHA-256 `6605bce12314e274f4c000f195eccc7ece23b1d7486bd79cb5384f6cb3b3bee0` in the final watchpoint runs. macOS 26.6.2 x86_64; MAME 0.289 (`unknown` revision string), executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; the same owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. No build or game image was produced. These are emulator observations, not physical arcade or Sega CD measurements.

**Documented only:** [MAME's Lua debugger interface](https://docs.mamedev.org/luascript/ref-debugger.html) provides write watchpoints, and [the debugger command reference](https://docs.mamedev.org/debugger/watchpoint.html) documents `wpaddr`, `wpdata`, and resume actions. The script uses these facilities with `-debug -debugger none -debuglog`, so no upstream MAME code was changed.

For the left control, run two fresh ignored directories `build/private/phase1b-ram-left{1,2}/`, with `PDRIFT_STEER_PULSE=64` and the same command, script, coin/start/pedal schedule and RAM capture windows as the [prior report](2026-10-20-arcade-ram-differential.md). Compare the six conditions with:

```sh
python3 tools/phase1b_ram_diff.py build/private/phase1b-ram-extended-center1 build/private/phase1b-ram-extended-center2 build/private/phase1b-ram-extended-pulse1 build/private/phase1b-ram-extended-pulse2 --left build/private/phase1b-ram-left1 build/private/phase1b-ram-left2
```

For the bounded debugger replay, use two further fresh ignored directories `build/private/phase1b-debug-sp-{left,right}/`. In each directory use the same MAME command as the prior report, adding `PDRIFT_DEBUG_WATCH=1`, `-debug -debugger none -debuglog`, and `PDRIFT_STEER_PULSE=64` or `192`. The Lua script arms two main-CPU program-space write watchpoints at callback 960, on `$1FFF72–73` and `$1FFFC4–C5`, then clears them at 1020. It logs the debugger's write address/data, PC and A7 stack pointer to private `debug.log`; the common `$3D00` write at `$1FFF72` is filtered to bound the log. The watchpoint command resumes execution after each hit. Each run reached callback 1800. This traces only two locations during 60 callbacks; it does not establish their complete write histories.

Raw `phase1b-input.log`, `debug.log`, RAM binaries and screenshots remain in the ignored directories. The left-replay log SHA-256 values were `dc506b3be4f9cfc5eb1fea915276b5fce5504faae04a5f14198af035b6c9ae8d` and `5a1e1e5da750f20989ced98242215e45d91b42d4a3554d23199622be0918329`. The left/right debugger `debug.log` hashes were `636e02b4f5bf2d7134d1f540cb49e7e09de66743ac4e014deee4485a18c73cca` and `f93c0a08c69397ea60c0c5ece9875bd9264467e9fc089438599c785ecad005d7`. Their corresponding input-log hashes were `c429cbd47fea000fb7f64aa46e8c6d61aaeed372d3f2eb06e67617c7443380bf` and `533796a7784ccabd768baa355172bfb7bce9d31bde1852e1cbeb890c3c125959`.

## Observations

**Verified by execution:** both left runs matched byte-for-byte across all sampled RAM windows and their corresponding screenshots matched. All six centered, left and right captures agreed at callbacks 900 and 960. At callback 1020 the left/center/right screenshots each differed; their SHA-256 values were `156534cb05687f8775b77ab01e7c087945c6708f6fb736e771a7904e5daa004b`, `55560dca0833f8fb44774882736933fc0f2edef4af1770ef776e9047b3e9bebb`, and `4c450264012e1a338f394c469070fb1557e6e6e0e4c38c5ef3b5d377517dc7d0`, respectively. Visual inspection shows the car on opposite sides of the roadway in the two pulse screenshots, with different surrounding scenery and race state. That is a visible control response, not a recovered steering angle or camera transform.

| Callback | Upper main: left vs center | Upper main: right vs center | Shared: left vs center | Shared: right vs center |
| ---: | ---: | ---: | ---: | ---: |
| 900 | 0 | 0 | 0 | 0 |
| 960 | 0 | 0 | 0 | 0 |
| 1020 | 17 | 26 | 1,468 | 2,267 |
| 1080 | 24 | 30 | 1,880 | 2,914 |
| 1140 | 41 | 37 | 2,246 | 2,916 |
| 1200 | 26 | 30 | 2,937 | 2,821 |

Counts are differing byte positions at a common callback, not variables, cycles or performance values. The sampled lower main-RAM page had zero differences throughout. **Verified by execution:** at callback 1020, the left and right upper-main captures differed at 29 byte positions; the shared captures differed at 2,306.

**Verified by execution:** a preliminary unfiltered right watchpoint run in private `build/private/phase1b-debug-watch-test/` logged 4,398 events; 4,230 were repeated `$3D00` writes to `$1FFF72`. It used MAME's debugger and still produced screenshots and sampled RAM identical to the untraced right replay. The final filtered left and right runs logged 180 and 168 events respectively. Both traced runs again reproduced their untraced condition's screenshots at callbacks 900, 1020, 1200 and 1800 and upper-RAM captures at 900, 960, 1020 and 1200.

**Verified by execution:** in the filtered left run, `$1FFF72` was written repeatedly with `$4AC2` or `$4AD2` while the debugger reported PC `$034AC2` or `$034AD2` and A7 `$FFFF70` (30 events of each). The right run showed the same two PC/data/A7 combinations 24 times each. The [MAME Y-Board main map](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) applies a `$1FFFFF` global address mask, placing that A7 value at mapped `$1FFF70`; the watched word sits two bytes above it. For `$1FFFC4`, writes came mostly from PC `$033234` and `$03327E` while A7 was `$FFFFFA`, which maps near the top of the same RAM area. The repeated near-stack locations and PC-related data make a stack explanation **hypothesis with supporting execution evidence**; the exact instruction, calling convention and ownership of these words remain **unsupported** until code inspection.

## Limits and next action

**Verified by execution:** the watchpoint trace did not include a disassembly or prove which code path uses the data. Nothing here identifies an original track segment, camera coordinates, curvature, or a sufficient mapping to the Sega CD five-word camera interface. No physical hardware was used and no renderer code was modified.

**Next experiment — hypothesis:** exclude stack-correlated addresses and search other bounded main/shared RAM pages for fields that respond promptly and directionally to short left/right pulses. Add earlier post-pulse checkpoints, then use watchpoints plus local 68000 code inspection on a small candidate set. Do not change the Sega CD camera interface until a genuine arcade quantity has been identified and shown to exceed its current controls.
