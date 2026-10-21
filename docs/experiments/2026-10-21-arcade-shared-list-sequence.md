# Phase 1B: shared sprite-list sequence and visible strips — 2026-10-21

**Question / hypothesis:** do selected ROM-backed projected records retain a traceable identity after main-CPU sorting, through sub-CPU X and into native Y-sprite output, across adjacent arcade updates? **Baseline:** the callback-950 owner-local state and the [five-step geometry/projection replay](2026-10-21-arcade-geometry-projection-sequence.md). **Acceptance:** match complete list records to execution-time sub-CPU X loads and final descriptors under center/left/right steering; perturb two additional selected descriptor positions and check native bitmap plus next composed screen. **Result — bounded PASS, verified by execution in MAME:** nine selected list records matched nine sub-CPU loads and descriptors. Two single-descriptor X shifts changed the expected native bitmap and next screen. The five previously measured main-CPU projection steps yielded only **three selected list epochs** here; one fixed descriptor slot does not retain the same object identity.

## Environment and reproducibility

**Verified by execution:** starting project revision `41b2baf` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing [capture-only patch](../../tools/phase1b_mame_ybitmap.patch). The owner-local 53-file ROM manifest SHA-256 was `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 save state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No upstream emulator code was edited in place. ROMs, derived sprite data, bitmaps, screenshots and raw traces remain ignored under `build/private/`.

**Verified by execution:** `tools/phase1b_mame_input.lua` optionally captures 8 KiB of the main CPU's `$0C9800` shared-list area at callbacks 960–970; SHA-256 `9be53d28a3175c32dd5de85bdf845e1b91dc658b1c788a9bfe63bd4d9496aa78`. An optional sub-CPU-X breakpoint at PC `$00DD6A` logs list loads whose first longword has low word `$0020`, including the source tuple and output pointer. The original fixed `$E630` watch remains available. `tools/phase1b_list_sequence.py`, SHA-256 `7a96f1a0ec228889f9f3b7e6afbad459200f784c444e70ce9e0e8bccb2359237`, verifies the matches against private captures.

Reproduce from a fresh ignored working directory. Use `PDRIFT_STEER_PULSE=64` for left, `192` for right, or omit for center:

```sh
SDL_VIDEODRIVER=dummy PDRIFT_SHARED_LIST_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_STATE_LOAD=/absolute/private/callback950.sta /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

For the independent execution trace, replace `PDRIFT_SHARED_LIST_DIR=.` with `PDRIFT_DEBUG_WATCH=ysprite PDRIFT_YSPRITE_SEQUENCE_TRACE=1 PDRIFT_YSPRITE_WATCH_OFFSET=E630` and add `-debug -debugger none -debuglog`. The input schedule is the established saved-state replay: pedal held, steering 128 except a 64/192 pulse beginning callback 960. The debugger uses the same state and ROM set. Run `python3 tools/phase1b_list_sequence.py build/private` after the three conditions and the two intervention captures described below.

## Sorting, sprite descriptors and screen interventions

**Verified by execution:** selected first-longword/source-word pairs were `8B310020/B2420032` at callback 962, `8B3D0020/B242003E` at 966, and `8B2F0020/B2420030` at 970. Each pair occurs once in its respective 8 KiB list capture, matches one sub-CPU-X `$00DD6A` load, and maps to one output descriptor by the observed A2 output pointer plus `$2000`. At callback 966, the same identity is at list offset `$0260` for center/right but `$0230` for left. Its descriptor is at `$E630` for all three. At callback 962 it is a different selected record at `$E600`; at callback 970, another at `$E5D0`. The `$E630` slot is occupied by a different sprite at 962 and 970. Thus a fixed RAM slot is not a persistent record identity.

| Callback | Shared-list selected identity | Sub-CPU output descriptor | X, center / left / right | Graphic-offset word, center / left / right |
| ---: | --- | --- | --- | --- |
| 962 | `8B310020` | `$E600` | `6A9 / 6A9 / 6A9` | `3888 / 3888 / 3888` |
| 966 | `8B3D0020` | `$E630` | `693 / 696 / 690` | `3888 / 3888 / 3888` |
| 970 | `8B2F0020` | `$E5D0` | `6AB / 6BB / 768` | `3888 / 3888 / 3898` |

**Verified by execution:** the selected first-longword/source-word pair persists uniquely over callbacks 960–963, 964–967, and 968–970 respectively. The full 8 KiB list can change for other reasons within an epoch. This selected-list cadence is an emulated callback observation, **not** an arcade-hardware frame-rate claim. The right-steered callback-970 descriptor uses a different graphic-offset word; source choice, clipping, and overlap have not been separately decoded.

**Verified by execution:** for center steering, a private copy of the existing source-RAM capture was changed only at the selected descriptor's X word by +3 (`$E602:06A9→06AC` at callback 962; `$E5D2:06AB→06AE` at 970). The optional source override applies the modified 16-byte descriptor after capturing the original RAM; all other source-RAM bytes remained equal. The callback-970 no-intervention replay reproduced the earlier center capture byte-for-byte for 33 files: 11 source-RAM captures, 11 native bitmaps and 11 screen PNGs. The following changes were measured from decoded emulated output:

| Descriptor change | Native bitmap changed pixels | Next screen changed pixels | Next-screen bounding box |
| --- | ---: | ---: | --- |
| `$E600` X +3 at 962 | 1,482 at bitmap 962 | 1,287 at callback 963 | x 83–269, y 143–155 |
| `$E5D0` X +3 at 970 | 1,236 at bitmap 970 | 1,099 at callback 971 | x 86–249, y 143–154 |

The screenshots before and including the intervention callback matched their corresponding baselines; the next callback differed. The previously documented [small main-CPU coordinate intervention](2026-10-21-arcade-rom-geometry-to-road-image.md) already showed the callback-966 `$E630` strip changing the visible road-height boundary with an identity-preserving sham and repeat. These two new direct-descriptor tests establish visible contribution for other selected epochs, but do **not** assign each changed pixel to one unique road edge or prove that `3888` is a full track texture.

For a direct descriptor test, take the baseline 64 KiB `source-0962-ysprites.bin` or `source-0970-ysprites.bin` in a private directory, change only the indicated big-endian X word by +3, and set `PDRIFT_SOURCE_OVERRIDE` to that private file, `PDRIFT_SOURCE_OVERRIDE_FRAME=962` or `970`, and `PDRIFT_SOURCE_OVERRIDE_RANGE=E600:0010` or `E5D0:0010`. Use the same MAME invocation as above with `PDRIFT_YBITMAP_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_EXTRA_SCREEN_FRAME=971` and no steering pulse. Capture an unmodified callback-970 baseline with those same flags. The private intervention input files live under `build/private/phase1b-list-interventions/`; the verifier compares the after-write RAM, bitmaps and screenshots.

Raw evidence: `build/private/phase1b-list-sequence-{center,left,right}/shared-list-*.bin`, `build/private/phase1b-subx-list-{center,left,right}/debug.log`, and `build/private/phase1b-list-{baseline-970,shift-962,shift-970}/`. The sub-CPU debug-log SHA-256 hashes (center/left/right) are `423e35deac057bea7a56068b16ef412032394ea6d23547c6f149e63155ca788c`, `9d029944df78289bfacda2c031c3e17a584b9e3add4c70aea05c5f2089386365`, and `8f51972048d5db1b452856bb5177c7b82e28b6779c8d`. Representative callback-966 shared-list SHA-256 hashes (center/left/right) are `096be85aa24972f62f91f1bc708a9bfe31508c9d57e88c5c0efdcf`, `0f85409f8011fa8ebc3a5761e3dd8da3a401af9a048b3c5a54f81fdab29c882d`, and `7d0ef124181d87bb38e9a524cde0332613dc6d6bde56588f13eb1372520a02e9`.

## Interpretation and next test

**Inference from verified execution:** the prior ROM geometry and exact main-CPU projection reconstruction can now be followed through a changing shared-list address, sub-CPU X load, selected Y-sprite descriptor, native bitmap and next composed screen in three adjacent display epochs. **Unsupported:** a single uninterrupted physical track-edge curve, formal arcade camera pose, meaning of the `8B...` or `B242...` fields beyond their observed matching behavior, or a demonstrated translation into the Sega CD five-word command. The current screen region contains overlapping strips; 30/60 Hz Sega CD suitability, arcade-hardware timing and physical-console compatibility were not tested. No second arcade emulator was run.

**Next bounded test — hypothesis:** isolate an unoccluded screen span in one of these epochs, use controlled per-record movement to determine which visible edge belongs to which record, and then compare its evolution with the independently reconstructed main-CPU coordinates. If overlap prevents unique attribution, retain the projection/list chain as a sprite-rendering reference and seek a clearer track section. Leave the Sega CD camera interface unchanged until a specific missing degree of freedom is demonstrated.
