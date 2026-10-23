# Phase 1B: selective source capture benchmark — 2026-10-23

**Question / hypothesis:** can source-hide trials avoid repeated source RAM and palette dumps while retaining the exact causal edge evidence used by `phase1b_right_source_search.py`? **Baseline:** the existing full `phase1b_mame_input.lua` capture from a callback-950 saved state. **Acceptance:** six matched trials in varied order, three per profile; identical 17 composed-screen PNG hashes, callback-968 Y-sprite before/after hashes and analyzed edge records; fewer files/bytes; report host elapsed time separately from emulated performance. **Result — verified by execution: PASS** for this callback-968 source-hide workflow.

## Small opt-in change

**Verified by source inspection and execution:** `PDRIFT_CAPTURE_PROFILE=road-edge` makes the existing Lua probe dump Y-sprite RAM at the selected override callback and again immediately after applying the override. It still writes every screen 960–976 and all existing swap evidence, so the analyzer's previous-screen checks remain intact. It omits Y-sprite dumps from other callbacks and all B-sprite/palette dumps. The `phase1b_right_source_search.py` `--capture-profile road-edge` option passes this setting through; its default `full` preserves old behavior. The profile requires a source override and is not intended for general arcade discovery or analyses that consume the omitted data. No old evidence was deleted.

**Verified by execution:** the same pulse-112 `$A600`–`$A6FF` hide at callback 968 was replayed in order **full, road-edge, road-edge, full, full, road-edge**. Every trial used the existing callback-950 state and source baseline. The current `analyze` action ran successfully on all six. All six analyzer records exactly matched the earlier independently saved `$A600` group record; screens 960–976 were byte-identical across the six trials, as were callback-968 Y-sprite before/after dumps and Y=152–156 causal flags. The selective profile therefore retains the evidence required for *this* analyzer. It does not preserve all information needed by other Phase 1B scripts.

| Profile | Host run seconds, in execution order | Median host seconds | Files per trial | Bytes per trial |
| --- | --- | ---: | ---: | ---: |
| Full | 5.284, 6.085, 5.370 | 5.370 | 138 | 2,080,979 |
| Road-edge | 4.639, 4.851, 4.791 | 4.791 | 88 | 681,304 |

**Verified by execution:** the selective trial produced **50 fewer files** and **1,399,675 fewer bytes** (67.3% of the full trial's file bytes). The median host-time difference was **0.579 seconds** (10.8% of the full median). These runs were serial and unthrottled on one host; the elapsed-time difference is a local workflow observation, sensitive to host load and filesystem cache. It is **not** an arcade or Sega CD hardware-performance measurement. The analysis pass was not included in the timed interval; its output was checked for equality.

## Provenance and reproduction

**Verified by execution:** source baseline `e8f4770` on `experiment/perspective-road`, with the Lua and runner edits uncommitted during measurement; macOS Darwin 25.6.0 x86_64; Python 3.14.8; installed MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. Lua probe SHA-256 `a526584dc0cf8574b5244c74230ae749b08c5e5f95e3bba5cb1b5443a24d7e8e`; modified source-search tool SHA-256 `b58fabd602904d56c783ebf3f2d04d8d79351d1668f5fac909b4d645ca360ee4`. The owner-local 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`.

**Verified by execution:** raw timings, trial order, file counts/bytes, screen hashes, Y-sprite hashes and causal flags are in ignored `build/private/phase1b-throughput-benchmark/measurements.json`, SHA-256 `cbe51f13ac662539cc9617b0ce467cec6cbd6e541c1f6d209c02f648e076361c`. The six ignored trial directories contain the raw MAME logs, captures and analyzer JSON. They are not tracked because they include arcade images and source RAM. An initial local benchmark driver invocation used an invalid duplicated `analyze` action and stopped after one untimed full replay; the corrected six-trial series above is the reported comparison.

For one matched pair, create two ignored roots containing a `phase1b-mild-steer-112` symlink to the same private baseline, then run:

```sh
python3 tools/phase1b_right_source_search.py build/private/phase1b-throughput-benchmark/01-full run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 968 --groups A600:0100 --capture-profile full
python3 tools/phase1b_right_source_search.py build/private/phase1b-throughput-benchmark/01-full analyze --callback 968 --groups A600:0100
python3 tools/phase1b_right_source_search.py build/private/phase1b-throughput-benchmark/02-road-edge run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 968 --groups A600:0100 --capture-profile road-edge
python3 tools/phase1b_right_source_search.py build/private/phase1b-throughput-benchmark/02-road-edge analyze --callback 968 --groups A600:0100
```

**Limitations — verified by inspection:** the trial directories are currently named by candidate group, not a complete input digest, and rerunning an action can overwrite its previous files. This is exactly why the proposed content-addressed runner must verify input and output manifests before reuse. A cache hit must be labeled reused evidence, not counted as a new MAME execution. The selective profile should be adopted only by analyzers whose required artifacts are declared and checked. No BlastEm, second arcade emulator or physical Sega CD hardware test was run, and no rendering code was changed.
