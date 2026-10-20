# 2026-10-20 live road camera command interface

**Question / hypothesis:** can the main CPU send independently chosen curvature, ridge, bank, horizon and texture-phase controls to the sub-CPU every road update, while preserving the 64×64 ASIC road's 30 Hz cadence? **Baseline — verified by execution:** the [frame-derived independent-control run](2026-10-20-independent-road-camera-controls.md) passed three 60-update Model 2 boots with worst image-ready time 511 emulated stopwatch ticks after the previous VBlank. **Acceptance evidence:** 60 checked ASIC outputs, 59 two-VBlank intervals within 1,085–1,088 ticks, no missed uploads, three reproducible cold boots, and a Model 1 communication checkpoint.

**Result — verified by execution:** three U.S. Model 2 BlastEm runs completed all 60 checked outputs with identical frame records and no cadence or VBlank upload misses. The unchanged private disc also reached `GVOK` at update 60 under the owner-labelled U.S. Model 1 BIOS. This is L1 emulator evidence; physical hardware was not tested.

## Interface and test sequence

**Documented only:** Sega's [Mega-CD Hardware Manual](https://segaretro.org/images/5/51/Mega-CD_Hardware_Manual.pdf) specifies eight main-to-sub communication command words at main-CPU `$A12010–$A1201E`, mirrored for sub-CPU reads at `$FF8010–$FF801E`. The existing experiment used word 7 (`$A1201E`) to trigger work. This test uses words 0–4 for a five-word camera packet, writes them before word 7, and retains the existing Word RAM ownership handoff and reply path. No undocumented ASIC or VDP register behavior was added.

| Command word | Main address | Sub address | Value in this test |
| --- | --- | --- | --- |
| Curve-table phase | `$A12010` | `$FF8010` | 0–95 |
| Ridge-table phase | `$A12012` | `$FF8012` | 0–191 |
| Signed bank | `$A12014` | `$FF8014` | −2…2 |
| Horizon | `$A12016` | `$FF8016` | 1–7 |
| Texture offset | `$A12018` | `$FF8018` | 0–47 |

**Verified by execution:** the main CPU copies five words from a generated 600-byte test-packet sequence into the command registers for each update. The sub-CPU reads those words and builds 64 trace rows from the existing 96-byte curve and 192-byte ridge tables; the ASIC still performs the pixel transformation. The main CPU then checks the 1,024-word additive output sum, stages 2,048 bytes in main RAM and uploads through VDP DMA. A packet is written before the trigger/ownership request, so the sub-CPU sees a complete packet when its interrupt handler runs.

**Test coverage — verified by execution:** the 60 packets form ten six-update groups. Each group has one base camera, then five variants that change only curve, ridge, bank, horizon or texture phase respectively. The host reference found that every variant changes output words and that all six expected additive sums are distinct within each group. All 60 expected sums matched actual ASIC outputs in each Model 2 run. The Model 1 debugger also showed final packet `($000C,$004E,$0000,$0004,$0014)`, equal to generated update 59. **Unsupported:** additive sums cannot rule out compensating pixel errors, and this test does not measure arbitrary player-controlled input. The packet producer is an offline-generated test fixture; the interface permits new values each update, but a gameplay camera producer has not been implemented.

| U.S. Model 2 run | Result | VBlank interval ticks, min/median/max | Trace build ticks | Image-ready ticks after previous VBlank | Ownership/setup/ASIC/return ticks | Checksum + staging ticks | VDP DMA/setup ticks | Cadence / upload misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Run 1](data/live-camera-model2-run1.json) | `PASS` | 1086/1086/1087 | 111/112/125 | 495/502/510 | 297/304/312 | 167/168/168 | 26/26/27 | 0/0 |
| [Run 2](data/live-camera-model2-run2.json) | `PASS` | 1086/1086/1087 | 111/112/125 | 495/502/510 | 297/304/312 | 167/168/168 | 26/26/27 | 0/0 |
| [Run 3](data/live-camera-model2-run3.json) | `PASS` | 1086/1086/1087 | 111/112/125 | 495/502/510 | 297/304/312 | 167/168/168 | 26/26/27 | 0/0 |

**Timing interpretation — verified by execution:** these are 12-bit Sega CD stopwatch readings as emulated by BlastEm, with each measured window shorter than the 4,096-tick wrap. Worst image-ready time 510 ticks leaves about 33 ticks before the next approximately 543-tick VBlank boundary in this fixture. The packet copy is included in image-ready timing but is not isolated: the separate ownership window starts after packet preparation, and the trace window begins on the sub-CPU before it reads the packet. ASIC trigger-to-busy-clear remained 96/97/97 ticks. Checksum and staging are a composite 167–168-tick window. The earlier frame-derived scene differs, so its 511-tick worst ready time is context, not a controlled measurement of communication cost. CPU cycle counts and stock-hardware duration are **unsupported**.

## Provenance and reproduction

**Environment — verified by execution:** parent source commit `e28582f847cd9c8a152ee2ccc3361cf048d960a3`; working tree dirty during execution on `experiment/perspective-road`. macOS 26.6.2 (25G83), x86_64; GNU m68k binutils 2.47.20260726; Python 3.14.8; BlastEm 1.0.0 official macOS archive SHA-256 `2315f5f32b8400b4c56980b87043516ac9ec22aac5fdb9d3bdb97c2b236da221`. Owner-labelled U.S. Model 2 BIOS SHA-256 `b1c2036b79467514eaaa69c76e5ba83801621e821059caa53cb921a0b21e3af4`; Model 1 BIOS SHA-256 `807384678ef259494d943eddb6954dfc7069693d0dde0c424e2028488d88e81a`. BIOS identities are not independently authenticated. Local startup-prefix SHA-256 `6ddf49d3e9edffe66b98776507aae447b3b0a90d96d3dae4572618d258d1259d`.

**Build — verified by execution:** `sh scripts/build-perspective-road.sh build/private/us-m1-startup-prefix.bin runtime-live` produced private ISO SHA-256 `687856e5b872b76bd28a61d918d7325195dff8c023592fdffd436cd9a79181ce`, IP SHA-256 `f6b9fe93a1b9eddd1a0f7cab8db50b69e09bf2c2409531aecd620f5120d73d8c`, and SP SHA-256 `96ed65ce9c3e5730a52d1e21be7368ef58a938f28a5291989cfa56a1b2c3ef30`. The 600-byte generated packet fixture SHA-256 is `fb6b1e85ec29a360b335679cb67e2dc29000729124ae3164a930cdcc1fde2952`. BIOS, prefix, private image and raw transcripts remain ignored locally; the source and parsed frame records are tracked.

**Execution — verified by execution:** run `script -q LOG /private/tmp/pd-blastem-us-m2-5s/blastem -r U -d build/private/perspective-road-runtime-live-us.cue`. In the debugger, set `breakpoint 0xff0584`; advance `frames 600`, press Start with `binddown "gamepads.1.start"`, advance `frames 5`, release with `bindup "gamepads.1.start"`, then advance `frames 1200` and `frames 300`. Completion is `d3=$47564F4B` (`GVOK`) and `d6=$3C` (60). Capture eleven words per frame from `$FF3000 + 22×frame` as in the [runtime-trace report](2026-10-20-runtime-road-traces.md). Parse with `python3 tools/parse_graphics_vdp.py LOG JSON --disc-image build/private/perspective-road-runtime-live-us.iso --frames 60 --size 64 --strategy road-runtime-live --road --road-runtime --combined-verify-stage --dma-only --expected-interval-min 1085 --expected-interval-max 1088 --source-commit e28582f847cd9c8a152ee2ccc3361cf048d960a3`. The linked JSON files retain all 60 frame records each.

**Raw logs — verified by execution:** ignored Model 2 transcripts `build/evidence-perspective-road-runtime-live-model2-run{1,2,3}.log` have SHA-256 `18fad7210e7187abf18cd40b88ef49337ebb745f3858a8aa492e2ec96caf96ab`, `fd6685d5fb157cd6c259f7538a1dd223237ff677a5011e6a0e3575ccc4527211`, and `af3c3b34b52a42fedf90ee76891d42a8d83760231aa8fa800a9ed45c09482150`. The Model 1 checkpoint transcript SHA-256 is `ae1e20337e62bd5bd4a4471f64875e6d89b4f98f7cd5db7e6c99e60fbc797162`. That checkpoint confirms completion and last-packet values, not timing equivalence.

**Next test — hypothesis:** increase output area while keeping this packet interface and its correctness checks, then identify which stage first misses the 30 Hz deadline. The current 64×64 margin is small and the 60-update fixture has no scenery, sprites, game logic or independent hardware validation. A larger scene's performance cannot be inferred from this pass.
