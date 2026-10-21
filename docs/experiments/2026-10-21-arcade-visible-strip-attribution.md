# Phase 1B: one visible arcade road-strip span — 2026-10-21

**Question / hypothesis:** can an unoccluded part of the original arcade road image be attributed to selected ROM-backed projected records across more than one display epoch? **Baseline:** the [exact fixed-point geometry replay](2026-10-21-arcade-geometry-projection-sequence.md) and [shared-list/sub-CPU/descriptor trace](2026-10-21-arcade-shared-list-sequence.md). **Acceptance:** align projected coordinates with the later shared-list record under three steering inputs; hide only that record's Y-sprite descriptor in a private MAME replay; verify its native-bitmap and composed-screen contribution, with a same-value control and repeat. **Result — bounded PASS, verified by execution in MAME:** all 9/9 selected projected X/Y pairs reappear in the list two callbacks later. At screen row 150, hiding the selected descriptor removes one contiguous 169-pixel visible contribution at callback 963 and another at 967. These are two display epochs of a road-like strip, not a decoded continuous track edge or camera pose.

## Reproduction and evidence

**Verified by execution:** starting source revision `1fe6cdb` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing [capture-only patch](../../tools/phase1b_mame_ybitmap.patch). Owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 save-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No new emulator or dependency was introduced. All ROMs, private intervention files, bitmaps and screenshots remain ignored under `build/private/`.

**Documented only:** the pinned [MAME 0.289 Y-Board sprite renderer](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/sega16sp.cpp) treats bits `$5000` of descriptor word 0 as a hide condition while retaining the linked-list index in word 7. **Verified by execution:** setting only bit `$1000` of word 0 at the selected descriptor (`$E600`, `$E630` or `$E5D0`) changed one byte of the 64 KiB captured sprite RAM and changed the next native Y bitmap and composed screen. All screenshots through the intervention callback were identical to baseline. The test modified the private runtime copy of RAM, not the commercial ROM or tracked assets.

From a fresh ignored directory, use the same saved state and input schedule as the prior report. For callback 962, use a private copy of baseline `source-0962-ysprites.bin` with descriptor word 0 changed from `$0005` to `$1005` at offset `$E600`; corresponding callback/offset pairs are 966/`$E630` and 970/`$E5D0`. Run:

```sh
SDL_VIDEODRIVER=dummy PDRIFT_YBITMAP_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_EXTRA_SCREEN_FRAME=971 PDRIFT_STATE_LOAD=/absolute/private/callback950.sta PDRIFT_SOURCE_OVERRIDE_FRAME=962 PDRIFT_SOURCE_OVERRIDE_RANGE=E600:0010 PDRIFT_SOURCE_OVERRIDE=/absolute/private/source-0962-hidden.bin /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

Change the frame, range and private input file together for 966 or 970. The callback-970 baseline replay was captured without an override using the same flags. For a same-value control, supply the unmodified callback-962 source file at `E600:0010`; for a repeat, rerun the hidden descriptor case. Compare all private captures with:

```sh
python3 tools/phase1b_strip_attribution.py build/private
```

The analysis tool SHA-256 is `7c454bbef3667c505d042da8a263a14c59df9a7171dc912fdefed60cc49ae07e`. The ignored raw input logs are `build/private/phase1b-list-hidden-{962,966,970}/phase1b-input.log`; SHA-256 respectively `9a41f6a5de4840ee36db041c7afa40db12dec8a260619866f9a66cfa009310f9`, `64be8217ef1e4b7799277c122cfcf3e6e0dd0bd05009f2849cc435efa6bd816e`, `7a2c30073e61a80a0e6835ad6a81a04f56963a208bc59ba5eaa1f4c1ee9df66c`. The same-value and repeat logs are in `build/private/phase1b-list-hidden-962-{sham,repeat}/`. The three hidden native-bitmap SHA-256 values are `caf4b6166cd53c10a2de57c35bf1ab9263ce7b1ff9b2fd719c965afe00734377`, `fd750bb532961b38d6b120b906fae7ab2a85f78af179f23b6e251a28031dc35d`, and `ce2598cc747a3a1ec39910ee47c23ba7e5c1bb98c710c2544d36b279c09417e4`.

## Timing and visible contribution

**Verified by execution:** the selected list record's complete `pos` longword equals the earlier geometry CSV's projected X/Y words for 3/3 epochs in each of center, left and right steering. Callback 962 uses object index 0 projected at callback 960; callback 966 uses index 0 projected at 964; callback 970 uses index 1 projected at 968. The later record is selected by first/source words rather than by fixed list address. The third epoch switching to index 1 is a concrete sorting/selection change; it must not be joined to the earlier two as though it were one persistent object.

| Hidden descriptor at callback | Changed native bitmap pixels | Changed pixels on next screen | Screen row 150 changed span |
| --- | ---: | ---: | --- |
| `$E600` at 962 | 1,932 | 1,902 at 963 | x 91–259, all 169 pixels contiguous |
| `$E630` at 966 | 4,111 | 3,986 at 967 | x 84–252, all 169 pixels contiguous |
| `$E5D0` at 970 | 1,610 | 1,609 at 971 | 156 changed pixels within x 91–251; gaps remain |

**Verified by execution:** the callback-962 same-value override produced source RAM, native bitmap and callback-963 screen identical to baseline. Repeating the hidden-descriptor callback-962 run produced byte-identical after-write source RAM, native bitmap and callback-963 PNG. The 169-pixel contiguous changed span shows that the selected sprite contributes visibly across that complete screen scanline span in the first two epochs. The callback-970 gaps show that a whole selected strip need not remain visible without overlap or other intervening pixels. Pixel counts and callback indices are emulator observations, not hardware timings.

**Inference from verified execution:** in this short window, the chain is now ROM-backed coordinates → main-CPU fixed-point projection → shared list after a two-callback lag → sub-CPU X descriptor → native road-like strip → composed screen. At row 150 the first two selected strips have a clear visible contribution. **Unsupported:** that x 91 or x 84 is the game's formal left track edge, that these two records encode a single uninterrupted track segment, the unit scale of their geometry, a decoded camera pose, or compatibility of those controls with the Sega CD five-word interface. Different affine parameters, depth, sorting and sprite image content also change between the epochs, so screen displacement must not be inferred from the projected X difference alone. No Sega CD render, physical hardware, arcade hardware, performance timing or second arcade emulator was tested here.

**Next bounded test — hypothesis:** extend the source-to-list-to-screen association for the same ROM depth/object across a longer, controlled section. Identify whether its visible left/right boundary remains unoccluded through several successive display epochs. If record identity changes or overlap prevents that, seek a clearer track section before constructing an arcade-derived camera sequence. Keep the Sega CD camera command unchanged pending a demonstrated missing input.
