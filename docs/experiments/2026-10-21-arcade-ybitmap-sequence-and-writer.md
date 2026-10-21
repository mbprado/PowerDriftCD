# Phase 1B: short Y-sprite edge sequence and writer — 2026-10-21

**Question / hypothesis:** does the [captured Y-sprite edge](2026-10-21-arcade-ybitmap-boundary.md) remain traceable over adjacent frames, and can one steering-dependent source-edge change be tied to a specific arcade sprite-list write? **Baseline:** the same callback-950 save state, nine MAME bitmap frames 960–968, centered/left/right steering and callback-961–969 screenshots. **Acceptance:** predict the visible boundary from each bitmap and its active affine block; identify a causally relevant, bounded RAM slot; trace its writer without changing the replay. **Result — PASS, verified by execution in MAME:** the first opaque Y-sprite pixel maps to the observed first non-sand pixel at rows 162, 165 and 168 in all 27 frame/steering combinations, 81 of 81 samples. At MAME frame 966, restoring one 16-byte Y-sprite slot at RAM offset `$E630` shifts the row-165 source-layer edge by three output pixels in either steering direction. Sub-CPU X writes its X-position word through the sprite-list writer near `$00E0B8`. This identifies one contributing sprite entry, not the track or camera representation.

## Reproducibility and sequence

**Verified by execution:** project starting commit `26b7c01` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source commit `f34f02505e32c1993c6a782b6814232cbfc74e36` with the previously documented capture patch; instrumented executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`; owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. Build and baseline launch commands are in the [capture report](2026-10-21-arcade-ybitmap-boundary.md). Neither the upstream MAME installation nor Sega CD source was changed. All ROMs, raw bitmaps, screenshots, save states, traces and disassembly remain ignored under `build/private/`.

**Verified by execution:** `tools/phase1b_ybitmap_sequence.py` uses bitmap frame `f`, callback `f+1` screenshot and the most recent pre-swap affine block. The swap log records an active update at even frames 960, 962, 964, 966 and 968; the intervening render uses the same block. On each row, the tool maps screen x through the six measured signed affine values into the captured 512×512 bitmap and finds four consecutive nontransparent source samples. An independent RGB sampler finds four consecutive non-sand screen pixels. For center/left/right at rows 162, 165 and 168, **81/81** predicted and observed x coordinates agree. This is an exact Y-sprite-layer alpha/color-boundary correspondence over this bounded window; it does not prove all 81 samples are the same physical road edge. The source bitmap can contain scenery and overlapping sprites.

At row 165, callback coordinates in output pixels were:

| Bitmap frame → screen callback | Center | Left | Right |
| ---: | ---: | ---: | ---: |
| 960 → 961 | 49 | 49 | 49 |
| 961 → 962 | 54 | 54 | 54 |
| 962 → 963 | 38 | 38 | 41 |
| 963 → 964 | 45 | 45 | 51 |
| 964 → 965 | 33 | 28 | 51 |
| 965 → 966 | 57 | 45 | 72 |
| 966 → 967 | 60 | 61 | 58 |
| 967 → 968 | 63 | 66 | 59 |
| 968 → 969 | 52 | 57 | 47 |

**Verified by execution:** the fixed source row `y=213` first-opaque x is identical among center/left/right through frame 965, then differs at frame 966: center 156, left 159, right 153. The source row is a *diagnostic slice*. It does not by itself explain earlier screen divergence because steered affine mapping samples other source rows. The `y=165` left/right sample at frame 966 maps to source rows 216/210, versus row 213 centered. Neither the screen x values nor the fixed source row form a smooth arcade camera trajectory; prominent jumps occur even with neutral steering.

Recreate the ignored 81-row CSV (SHA-256 `2d0e2f17f48baa86c3a7de0126c3a7b54356f6edf17d8aad2fe45de059315800`; sequence-tool SHA-256 `1bf1ef2d9879c7231114e725ec4c39188afb31b7a68faeaab0f206fbfc1fa750`) with:

```sh
python3 tools/phase1b_ybitmap_sequence.py build/private/phase1b-ybitmap-center build/private/phase1b-ybitmap-left build/private/phase1b-ybitmap-right > build/private/phase1b-ybitmap-sequence.csv
```

## One bounded source-entry intervention

**Verified by execution:** the existing Lua `PDRIFT_SOURCE_OVERRIDE_RANGE` mechanism restored center bytes to selected 16-byte-aligned ranges of left-steered Y-sprite RAM after callback 966. An isolated MAME replay captured the resulting bitmap and screenshot. For row 165, the left baseline boundary was x=61, restoring `$E400–$E5FF` left it at x=61, restoring `$E600–$E7FF` moved it to x=58, and bounded splits localized this effect to `$E630–$E63F`: restoring `$E620–$E62F` left x=61, restoring `$E630–$E63F` moved it to x=58. The same `$E630` restoration in the right replay moved its boundary from x=58 to x=61. The affine block stayed steered and unchanged. The callback-966 pre-intervention screenshot and callback-969 restored screenshot matched the corresponding unmodified steered run. The repeated left `$E630` intervention reproduced its raw 524,288-byte bitmap and callback-967 PNG byte-for-byte.

| Callback-967 condition | Screen boundary x | Mapped source pixel (x,y) |
| --- | ---: | ---: |
| Center baseline | 60 | (156,213) |
| Left baseline | 61 | (157,216) |
| Left, `$E620–$E62F` restored | 61 | (157,216) |
| Left, `$E630–$E63F` restored | 58 | (154,216) |
| Right baseline | 58 | (156,210) |
| Right, `$E630–$E63F` restored | 61 | (159,210) |

**Verified by execution:** the left `$E630` intervention changed 3,042 intermediate bitmap pixels in a private source-bitmap bounding box `x=153–405, y=195–217`, and 2,735 final screen pixels compared with left baseline. The centered donor and left/right snapshots differ in that slot only in the second 16-bit word at frame 966; its lower 12 bits differ by +3 for left and −3 for right from center. The right-side intervention confirms the sign-reversed effect. Other slots still differ and contribute to the full frame; restoring `$E630` alone does not reproduce the centered image. The ignored six-condition map CSV is `build/private/phase1b-ybitmap-e630-map.csv`, SHA-256 `20f1f3b5f812355b2bd8097ae1dd7178243bc08e2af0b5dbccec3012bff62af5`.

Reproduce a single range test in a fresh ignored directory with the capture-report command, left or right steering, and these extra variables:

```sh
PDRIFT_SOURCE_OVERRIDE=/absolute/private/center/source-0966-ysprites.bin PDRIFT_SOURCE_OVERRIDE_RANGE=e630:10
```

**Documented only:** [MAME 0.289's Y-sprite renderer](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/sega16sp.cpp) describes 16-byte linked entries and the second word's low 12 bits as the sprite X-position field. That source interpretation agrees with the measured three-pixel movement but is an emulator implementation description, not independent electrical hardware evidence. A descriptor may draw several visible features; the intervention establishes this slot's effect on the sampled edge, not that it is a unique track-boundary record.

## Writer trace and limits

**Verified by execution:** the Lua watchpoint now accepts `PDRIFT_YSPRITE_WATCH_OFFSET` (hex; default `E6E0`), allowing a bounded 16-byte sub-CPU-X write watch at `$18E630–$18E63F`. Center, left and right replays were run with `PDRIFT_DEBUG_WATCH=ysprite PDRIFT_YSPRITE_WATCH_OFFSET=E630`, plus `-debug -debugger none -debuglog` on the same isolated MAME binary. All callback-960–970 decoded screenshots and callback-966 Y-sprite RAM snapshots matched the corresponding untraced runs. Each trace saw two sets of seven word writes to the slot; in the later set, the second word differed by ±3 with steering while the other six written words matched. The debugger stop at PC near `$00E0BA` occurs just after the relevant write; [the earlier private disassembly](2026-10-21-arcade-sprite-writer-and-road-edge.md) places paired writes to destinations 8 KiB apart in the routine around `$00E0A4–$00E0E2`. The `$E630` slot is the upper destination. This ties the local source-edge motion to a specific write in the sprite-list writer. The origin of the writer's input value remains **unsupported**.

The three private debug-log SHA-256 values are center `68f3c4e4299feca6e88958b8ea2098675632c64c3679c0b174778ebf143f7bf2`, left `8998f8c97a6d2f1f92183d7baed880356bacb581e1a11d7f662735df333cdbbd`, and right `e5bb531517f7468f4fb140a3aaf6fde4e271035a1a64948fc61399d998aa5e54`. Final Lua source SHA-256 is `ea693800e04684464dfcf65a6b0aca609627b9fd4014c56f2186c7998495e0e6`.

**Inference from verified execution:** this arcade writer emits steering-responsive sprite X coordinates that affect the apparent roadside, and the affine layer adds a separate screen mapping. Which upstream game variable supplies the X coordinate, whether the entry represents a road segment or scenery, and how it relates to curvature, elevation or banking remain **unsupported**. No Sega CD build, physical-hardware test, second arcade emulator or performance measurement was performed.

**Next bounded test — hypothesis:** trace the input to the paired X-position write through the immediate caller and a short preceding state window, and use a targeted intervention to distinguish a track/camera-derived coordinate from a generic sprite or scenery coordinate. Only after that should an arcade-derived camera sequence be fed into the existing Sega CD interface; its adequacy is still **unsupported**.
