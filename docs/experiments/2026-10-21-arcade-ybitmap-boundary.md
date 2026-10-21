# Phase 1B: capture and map the arcade Y-sprite bitmap — 2026-10-21

**Question / hypothesis:** does the visible left roadside transition in the controlled callback-967 frame correspond to an edge in MAME's pre-affine 512×512 Y-sprite bitmap, and do steering inputs move that edge in source space? **Baseline:** the [two-factor test](2026-10-21-arcade-source-affine-factor.md) at callback 966/967. **Acceptance:** capture the *actual* intermediate bitmap from an isolated, pinned MAME build; validate its visible output against the installed build; map captured source pixels through the measured affine block; repeat the centered and steered replays; test the existing source-only and affine-only controls. **Result — PASS, verified by execution in MAME:** the first opaque Y-sprite pixel along screen row 165 predicts the observed color transition in all eight conditions. At source row 213, the edge moves from x=156 (center) to x=159 (left) or x=153 (right). This is one arcade frame and one local boundary, not a decoded track or camera trajectory.

## Isolated tooling and provenance

**Verified by execution:** project starting commit `e44ac0f` on `experiment/perspective-road`; macOS 26.6.2 x86_64; Apple/Clang build identified itself as Clang 21.0.0; MAME source tag `mame0289`, resolved commit `f34f02505e32c1993c6a782b6814232cbfc74e36`; local instrumented one-driver executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`. The installed MAME 0.289 comparison binary SHA-256 is `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The owner-local 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; the private callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No ROM bytes, extracted pixels or private save states are tracked.

**Documented only:** the [MAME 0.289 Y-Board `screen_update`](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) draws Y sprites into a 512×512 bitmap before calling `rotate_draw`, and then mixes B sprites. The [MAME affine implementation](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaic16.cpp) samples the source at `((currx + dxx*(x+27) + dxy*y) >> 14) & 511` and the corresponding Y expression using `curry`, `dyx` and `dyy`. A source value of `$FFFF` is transparent; other values use a sprite palette/priority encoding. That is MAME's rendering model, not a direct readout from physical Y-Board hardware.

**Verified by execution:** an isolated `/private/tmp/pd-mame0289-source` clone was patched with [the small capture patch](../../tools/phase1b_mame_ybitmap.patch), SHA-256 `299fd78351679af86faa30198612ea593159abb8814ec3040f39d7df5fa93611`. It writes 512×512 native-endian 16-bit source pixels after the Y-sprite draw and before the affine pass for MAME frame numbers 960–970 only when `PDRIFT_YBITMAP_DIR` is set. The patch also explicitly enables the Musashi 68000 core in the one-driver build: `SOURCES=...segaybd.cpp` alone reached a missing-core link error. The upstream installation and repository were not edited. A clean pinned clone can reproduce the build with:

```sh
git clone --depth 1 --branch mame0289 --filter=blob:none https://github.com/mamedev/mame.git /private/tmp/pd-mame0289-source
cd /private/tmp/pd-mame0289-source
git apply /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_ybitmap.patch
make SOURCES=src/mame/sega/segaybd.cpp NOWERROR=1 REGENIE=1 -j8
```

The build command succeeded. In a fresh ignored `build/private/phase1b-ybitmap-<condition>/` directory, the representative centered replay was:

```sh
SDL_VIDEODRIVER=dummy PDRIFT_YBITMAP_DIR=. PDRIFT_RAM_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_RAM_PROFILE=early PDRIFT_STATE_LOAD=/absolute/private/callback950.sta /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

For left/right, set `PDRIFT_STEER_PULSE=64`/`192`. The source-only and affine-only controls set `PDRIFT_SOURCE_OVERRIDE` and `PDRIFT_ROTATE_OVERRIDE` to the private centered donor files as in the [previous report](2026-10-21-arcade-source-affine-factor.md). The combined control sets both. `SDL_VIDEODRIVER=dummy` is necessary for the isolated headless build in this sandbox. The raw bitmap named `ybitmap-0966.raw` supplies the source pixels corresponding to Lua callback-967 screenshot; the screen/frame labels are offset by one at this capture point. This alignment is independently checked by the exact boundary correspondence below.

**Verified by execution:** for centered, left and right replays, all 11 decoded screenshot pixel arrays at callbacks 960–970 matched the corresponding installed-MAME replays exactly. PNG file SHA-256 values differ because the builds encode PNGs differently. The callback-966 Y-sprite RAM and pre-swap affine bytes matched their installed-run captures exactly. A second centered and left run reproduced all 11 corresponding raw bitmap files byte-for-byte. The combined left control produced the centered 524,288-byte bitmap and centered decoded screenshot exactly. Private raw files remain under `build/private/phase1b-ybitmap-*`; representative input-log SHA-256 values are center `6ca2e2a6501d5521508d213bc642b860c5dec6d3fa357a4a659ff79819794705`, left `438a8c0ffe5350dfc6830a117fff06c2a1fcbbac0e781b7659f2535146abe6d4`, right `efee5b09f39adb16c2260ad3318fc6157db20e2ea585639c5795fc0d7637c1fc`.

## Source-space and screen-space correspondence

**Verified by execution:** [the mapping tool](../../tools/phase1b_ybitmap_map.py), SHA-256 `14703cad2e0d2662c8e5b345adaf670de47d3a7c1d77360a9c31190147a1bd36`, reads the captured 16-bit bitmap and six signed 32-bit affine values. It maps each screen x at row 165 to a source coordinate, then finds the first run of four non-`$FFFF` source pixels after screen x=16. The independent screen sampler finds the first sustained non-sand RGB transition. The two x coordinates agreed in all eight conditions:

| Condition | Source bitmap vs center | Affine block | Source-mapped first opaque screen x | Observed screen boundary x | Sampled source pixel (x,y) |
| --- | ---: | --- | ---: | ---: | ---: |
| Center | 0 changed words | center | 60 | 60 | (156,213) |
| Left | 37,054 changed words | left | 61 | 61 | (157,216) |
| Left, source restored | 0 changed words | left | 58 | 58 | (154,216) |
| Left, affine restored | 37,054 changed words | center | 63 | 63 | (159,213) |
| Left, both restored | 0 changed words | center | 60 | 60 | (156,213) |
| Right | 38,747 changed words | right | 58 | 58 | (156,210) |
| Right, source restored | 0 changed words | right | 61 | 61 | (159,210) |
| Right, affine restored | 38,747 changed words | center | 57 | 57 | (153,213) |

**Verified by execution:** at the fixed source row `y=213`, the first nontransparent pixel in the local x=120–219 search window is x=156 centered, x=159 left, and x=153 right. With the *center* affine block held fixed, these predict screen x=60, 63 and 57, matching the centered and affine-restored control screenshots. The source-only controls reproduce the centered bitmap byte-for-byte yet still place that bitmap differently on screen under their steered affine values. The center, left and right bitmap SHA-256 values at MAME frame 966 are respectively `cf21731c53ee04a1dc9f4b50ec056710ac6adf741558a8e61f5570781d991e33`, `3c03875da91fcd7c48416d8f71112a64f60488e5be10c3f53c77aefbe593f690` and `bfdb88a8b2aa81c53cf35d550e772a85d00ace9400f76f4f4255035645ee88b6`.

The same predicted/observed x agreement held at row 162 in all eight conditions. Row 168 is less reliable as a *roadside* sample: the left-steered case first becomes opaque at x=17, and the left source-restored screenshot fails the sampler's initial sand-color condition. It is therefore excluded from the roadside conclusion. The row-165 match establishes a local Y-sprite alpha-edge correspondence, not a semantic track-boundary variable. Changes in sprite overlap, palettes or B-sprite priority can invalidate the simple color-boundary heuristic in other frames.

Recreate the ignored 24-row CSV with:

```sh
python3 tools/phase1b_ybitmap_map.py build/private/phase1b-ybitmap-center build/private/phase1b-ybitmap-left build/private/phase1b-ybitmap-right build/private/phase1b-ybitmap-left-both --case left_source=build/private/phase1b-ybitmap-left-source --case left_affine=build/private/phase1b-ybitmap-left-affine --case right_source=build/private/phase1b-ybitmap-right-source --case right_affine=build/private/phase1b-ybitmap-right-affine > build/private/phase1b-ybitmap-map.csv
```

The private CSV SHA-256 is `0e35856c4623d20da17a6a116032b02272851009305a48ec0bcb2476b3560d4c`. No timing values were collected. **Inference from verified execution:** both source-space edge motion and affine mapping contribute to the visible response in this frame, and the five-word Sega CD camera interface cannot yet be judged against a real arcade sequence. Original track parameters, camera state and source sprite-list semantics remain **unsupported**. No second arcade emulator or physical hardware was tested.

**Next bounded test — hypothesis:** follow this specific source-space edge over a short deterministic sequence, using the captured bitmap and affine parameters, and identify where the source edge changes in the arcade sprite-list writer or upstream data. First prove a repeatable sequence; then investigate whether it is tied to track curvature/elevation rather than nearby scenery or transient sprites. Keep the Sega CD rendering interface unchanged until a real sequence exposes a measurable missing control.
