# Phase 1B: exact-replay evidence cache — 2026-10-24

**Question / hypothesis:** can an exact-repeat source-hide request reuse verified private MAME evidence without being mistaken for a new experiment? **Baseline:** the existing `phase1b_right_source_search.py run` action always launches MAME; the optional `road-edge` capture profile from the [prior benchmark](2026-10-23-phase1b-selective-capture-benchmark.md) retains the analyzer's required evidence. **Acceptance:** an exact repeat is identified as a hit and launches no MAME process; a normal run still executes; changed input receives a different key; altered output forces a fresh run while preserving prior files; the existing analyzer returns the same result. **Result — verified by execution: PASS** for one callback-968 source-hide workflow. This does not reduce the number of independent experiments we should run.

## Opt-in runner behavior

**Verified by source inspection and execution:** `tools/phase1b_evidence_cache.py` is a small standard-library runner used by the source-hide tool only when `--reuse-cache` is present. The cache key covers the MAME executable, Lua probe, saved state, source-search and cache tool code, baseline Y-sprite RAM, generated override, owner-local ROM manifest and all 53 ROM file hashes, plus the exact MAME command, working directory and a hash of the **environment actually passed to MAME**. That environment retains the declared `PDRIFT_`, `SDL_`, `MAME_`, `DYLD_`, `XDG_`, and locale variables plus `HOME`, `PATH` and `TMPDIR`; transient shell and tool-call metadata are excluded from execution and from the key. The ROM files are checked against the manifest before reuse. A JSON manifest under ignored `build/private/.../phase1b-evidence-cache/<key>.json` records every file produced in the trial directory with size and SHA-256. A hit requires the same request, every recorded file unchanged, no extra files, and the screenshots and before/after source dumps needed by this analyzer. Manifest writes are atomic; a process lock prevents simultaneous writes to the same key.

**Verified by source inspection and execution:** a missing or changed manifest/output makes the runner execute MAME. If a trial directory already contains files, it is renamed to an `.invalid.<id>` sibling before the fresh run, preserving the old material for inspection. The cache currently reuses evidence **in place** under one experiment root; it does not copy captures across roots or deduplicate their storage. `--reuse-cache` is opt-in. An ordinary run with the same arguments continues to launch MAME, so deliberate independent repetitions are available. A hit is labeled `hit`, never counted as emulator execution.

## Measured trial and correctness checks

**Verified by execution:** from the same callback-950 state and pulse 112, the `$A600`–`$A6FF` hide at callback 968 produced these host wall times. Only the `run` action was timed; emulator time was unthrottled. The first miss includes full input hashing and manifest creation.

| Request in order | MAME launched? | Host seconds | Observation |
| --- | :---: | ---: | --- |
| First `--reuse-cache` | yes | 5.638 | New content key `55fff180…721df` |
| Exact repeat 1 | no | 1.206 | Verified hit |
| Exact repeat 2 | no | 1.106 | Verified hit |
| Exact repeat 3 | no | 1.056 | Verified hit |
| Ordinary run without cache | yes | 4.903 | Independent MAME replay |
| Reuse after appending a probe line to the trial log | yes | 5.328 | Output validation failed; prior directory quarantined |

**Verified by execution:** median hit time was **1.106 host seconds** across three repeats, compared with **4.903 seconds** for the single ordinary replay in this sequence. The first cached miss was **0.735 seconds slower** than that ordinary replay, so the cache is useful for exact repeats, not as a blanket default for one-off experiments. Host scheduling and file cache can move these figures; they are not arcade or Sega CD hardware measurements.

**Verified by execution:** a different hide input (`$A610` only) executed MAME and produced a different key, `25b1b5af…e4f52`. After the invalidation rerun, the unchanged source-hide analyzer returned the same Y=152–156 edge flags as the earlier uncached `$A600` trial, and its entire analyzed record matched the prior record exactly. Screen-969 PNG SHA-256 was `ec9a0f7a2a8b163d5e83ca0c1d4237e363c1e4b8243289f260c191c063c3cf83`; callback-968 post-write Y-sprite SHA-256 was `6a660fa33812646f14f90179516d7d5eec98f1fa73357eca77e32a462e41a6d1`. One altered directory was preserved under `.invalid.<id>`. A separate pair of shell tool calls also produced the **same** content key and a hit after the initial execution. These checks show cache behavior and result identity for this trial, not independent arcade semantics.

**Verified by execution:** the default `full` capture profile also executed once, hit on an exact repeat and passed the unchanged analyzer with its 52 source dumps present. A test manifest with one deliberately wrong ROM hash was rejected before MAME execution. These controls support the fail-closed input check and preservation of the previous full-capture path.

## Provenance, reproduction and limits

**Verified by execution:** source baseline `6183dec` on `experiment/perspective-road`, with these tool edits uncommitted during measurement; macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. Final cache tool SHA-256 `4d777b054f30993d745e57c2c8d8a24c66b819f82221110622b944d466ac974d`; source-search tool SHA-256 `674e60ac7448aa14f052a6445b4ed11daa157a08c16b9514f038d92d2c14f9f9`; Lua probe SHA-256 `a526584dc0cf8574b5244c74230ae749b08c5e5f95e3bba5cb1b5443a24d7e8e`. Owner-local ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 saved-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`.

**Verified by execution:** ignored raw `build/private/phase1b-cache-final24/benchmark.json` has SHA-256 `574602bd9eb3064bd66b1adf127c51ae5903ec6fd7775d243377007ef467ffc7`; the content-keyed private manifest has SHA-256 `519d2d0a9b5acd4258ce840ce9f9595771cb5642aa5e81ff7f0bd00cdd0af461`. Source RAM, ROMs, screenshots, logs, state and cache records remain ignored. For the same trial, create an ignored root with a `phase1b-mild-steer-112` symlink to the existing private baseline, then run the command twice; omit `--reuse-cache` for a deliberately independent replay:

```sh
python3 tools/phase1b_right_source_search.py build/private/phase1b-cache-final24 run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 968 --groups A600:0100 --capture-profile road-edge --reuse-cache
python3 tools/phase1b_right_source_search.py build/private/phase1b-cache-final24 analyze --callback 968 --groups A600:0100
```

**Limitations — verified by source inspection:** the cache validates only the local loose `pdrift` ROM layout and the source-hide runner's declared artifacts. Hashing the 380 MB MAME binary on every request contributes to hit overhead; a faster metadata shortcut would weaken strict content validation unless independently checked. The runner deliberately passes only declared MAME/Lua environment categories; an undeclared variable needed by a future experiment must be added to that set and the key. The first draft hashed the entire inherited shell environment; a changing tool-call ID caused an unwanted miss across calls. That draft was corrected and excluded from the final benchmark. The cache does not yet serve other Phase 1B scripts, automate coordinate calibration or encode acceptance thresholds. No upstream emulator, Sega CD renderer, BlastEm image or physical hardware was changed or tested.
