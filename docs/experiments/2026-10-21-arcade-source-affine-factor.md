# Phase 1B: Y-sprite source and affine factor test — 2026-10-21

**Question / hypothesis:** does the steered road image at callback 967 depend on changes in the Y-sprite source list, the affine transform, or both? **Baseline:** the same callback-950 saved state and centered/left/right replays used in the [sprite-writer and road-edge report](2026-10-21-arcade-sprite-writer-and-road-edge.md). **Acceptance:** replace either input independently with its centered value, verify the replacement actually reached the renderer, and compare the next screenshot with the centered frame. **Result — PASS, verified by execution in MAME:** neither replacement alone reproduced the centered frame; replacing both did so byte-for-byte for left and right steering. This is a one-frame causal test of two MAME renderer inputs, not a decoded arcade camera or track.

## Method and evidence

**Verified by execution:** source commit `eac3dc310fc999c2945599067abd7faf1ff5a3ba` on `experiment/perspective-road`; macOS 26.6.2 x86_64; MAME 0.289 binary SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. The ignored callback-950 save state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The center donor Y-sprite RAM snapshot is 65,536 bytes, SHA-256 `4443c41565cd335e37825ffe0981f6a430a6376e6fe1810717b9e5396c4c06d2`; the center pre-swap affine block is 32 bytes, SHA-256 `36ca897160497c148598bc8feaf3ce14d0af47026c97078e8c5d5b0a290e9900`. Lua and comparator source SHA-256 values are `9fb493eb9bc9a8a0753764169e1b265fcf5ae4c551230e0de5eb508b43ef821a` and `1cf79fd9858d44b281ef1ab0b0a332123fad555563c81efa73685d7d6aeca35f` respectively.

**Documented only:** the [MAME 0.289 Y-Board driver](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) first draws Y sprites into a 512×512 bitmap, then calls the affine renderer before B-sprite overlay. The [affine implementation](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaic16.cpp) reads six 32-bit parameters from a swapped 16-word block and samples that source bitmap. [MAME's Lua memory API](https://docs.mamedev.org/luascript/ref-mem.html) documents returning replacement data from a write tap. The test changed only the local Lua script; no upstream emulator code was edited.

**Verified by execution:** `tools/phase1b_mame_input.lua` now accepts `PDRIFT_ROTATE_OVERRIDE`, a path to a private 32-byte block. At the 12 observed sub-CPU-Y writes during callback 966, its write tap substitutes the corresponding donor words. The existing `PDRIFT_SOURCE_OVERRIDE` replaces the 65,536-byte sub-CPU-X Y-sprite RAM snapshot after callback 966. Four fresh runs per steering direction were made: normal, source only, affine only, and both. Steering pulse was `64` for left and `192` for right. The same private save state and input schedule were used in all runs. A fresh ignored working directory was used for each condition. Representative command, run from that directory (set either, both or neither override variable):

```sh
PDRIFT_RAM_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_RAM_PROFILE=early PDRIFT_STEER_PULSE=64 PDRIFT_STATE_LOAD=/absolute/private/callback950.sta PDRIFT_SOURCE_OVERRIDE=/absolute/private/center/source-0966-ysprites.bin PDRIFT_ROTATE_OVERRIDE=/absolute/private/center/swap-pre-0966-006.bin /usr/local/Cellar/mame/0.289/bin/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

**Verified by execution:** every condition retained its own normal steered screenshot at callback 966 and returned to its normal steered screenshot by callback 969. Pre-intervention Y-sprite RAM matched its steered baseline. Source replacements matched the centered 65,536 bytes after injection; affine replacements matched the centered 32-byte pre-swap block. The tap logged 12 replaced writes in each affine run and its shadow matched mapped RAM. B-sprite and palette RAM snapshots at callbacks 966 and 967 matched each condition's steered baseline. A sham substitution of the left run's *own* affine block reproduced all its callback-960–970 screenshots byte-for-byte. A repeated left-both run reproduced the same callback-967 PNG SHA-256. An initial tap at callback 965 intercepted no relevant writes and was discarded; the measured test uses callback 966.

## Results

Pixel differences compare the 320×224 callback-967 PNG with the centered frame; the road rectangle is `x=0..319, y=80..169`. The boundary is the [previously defined visible color transition](2026-10-21-arcade-sprite-writer-and-road-edge.md) at `y=165`, not a geometric track edge.

| Steering | Centered inputs restored | Full-frame differing pixels | Road-rectangle differing pixels | Boundary x |
| --- | --- | ---: | ---: | ---: |
| Center | baseline | 0 | 0 | 60 |
| Left | none | 38,715 | 20,940 | 61 |
| Left | Y-sprite source | 37,336 | 20,431 | 58 |
| Left | affine | 22,983 | 10,694 | 63 |
| Left | both | **0** | **0** | **60** |
| Right | none | 39,603 | 21,756 | 58 |
| Right | Y-sprite source | 39,471 | 21,463 | 61 |
| Right | affine | 23,715 | 11,013 | 57 |
| Right | both | **0** | **0** | **60** |

**Verified by execution:** both-combined callback-967 screenshots have the centered PNG SHA-256 `eb636e035b9772db2a43d4c13bfd991c75feb86d0085a0b825c78395a03fb8fc`, for left, repeated left and right. The left sham equals the normal-left SHA-256 `b979ddfac77f46a7593b4d8ce3a3f56b98c411b9d0364471bf2c8ee623afb01f`. The raw eight-condition CSV is ignored at `build/private/phase1b-affine-factor.csv`, SHA-256 `a41b85ebd0c534febaa9dc26d66bf899828d0e5b696db25114b97d80647ab6c8`; both-combined input logs have SHA-256 `fe529babde768817213f8f5565f2db27ad578bf6daf2f698764ef08f2c4aa6a3` (left) and `e37a17a3afb330c8fb21f1a01a5511988ac78b143e79ec57da3f9614db40c592` (right). Reproduce the comparison with:

```sh
python3 tools/phase1b_affine_factor_compare.py build/private/phase1b-range-state-center build/private/phase1b-range-state-left build/private/phase1b-factor-left-source build/private/phase1b-affine-neutral-left2 build/private/phase1b-factor-left-both build/private/phase1b-range-state-right build/private/phase1b-factor-right-source build/private/phase1b-affine-neutral-right build/private/phase1b-factor-right-both > build/private/phase1b-affine-factor.csv
```

**Inference from verified execution:** both the source-list state and affine state contribute to the changed *composed* frame at this instant. The pixel counts are not additive: sampling, wrapping, transparency and sprite priority can make the factors interact. Their magnitudes do not establish which mechanism is more important for game-wide road motion. The 512×512 intermediate Y-sprite bitmap was not captured, so an actual source-space curb boundary remains **unsupported**. The experiment does not identify original camera variables, curvature, elevation, banking or a real track segment; compatibility with the Sega CD five-word camera interface remains **unsupported**. No physical hardware, Sega CD image, second emulator or timing test was used.

**Next bounded test — hypothesis:** capture a small region of MAME's internal 512×512 Y-sprite bitmap from an isolated, version-pinned build at this same render instant, then compare its boundary with the measured affine mapping and visible sample. Keep the captured commercial-derived pixels private. This should determine whether the source-list change moves the road edge itself or only changes its composition. The existing Sega CD renderer needs no change pending that evidence.
