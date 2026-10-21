# Phase 1B: far-depth descriptor visibility at matched lookup positions — 2026-10-21

**Question / hypothesis:** can one ROM-backed far-depth sample from the [projection chain](2026-10-21-arcade-far-depth-visibility.md) be tied to a visible road descriptor while the [upstream state](2026-10-21-arcade-upstream-state-and-matched-depth.md) is at the *same exact lookup position* in center, left and right steering runs? **Baseline:** owner-local callback-950 MAME state, held pedal, steering 128 or a pulse to 64/192 from callback 960, and the existing private 960–1000 geometry/list/sub-CPU/screen captures. **Acceptance:** follow the `$3A00` sample through three consecutive selected projection epochs; identify its moving descriptor for each run; hide only that descriptor in private replays; verify prior screens, a same-value control and a repeat. **Result — partial PASS, verified by execution in MAME:** all nine projection → list → sub-CPU-X → descriptor identities and one-byte hide interventions checked. The descriptor changed no screen pixels at the first epoch, then produced small visible contributions in all three steering runs at each of the next two epochs. This is not yet a continuous road-edge reference or a camera adapter target.

## Environment and reproduction

**Verified by execution:** starting project revision `9d654100aa70ca32e86de3d500f2f7bf2605d105` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing [capture-only bitmap patch](../../tools/phase1b_mame_ybitmap.patch). Owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; private callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. No upstream emulator source, original commercial ROM or Sega CD renderer code was changed; proprietary-derived RAM copies and screenshots remain ignored.

**Verified by execution:** the new original analyzer `tools/phase1b_matched_far_depth.py` SHA-256 `2b83abde31a1d8ece4243f5495af2479aca6e0a65a31327e112732ab8db1ae86` uses the existing private geometry CSV, shared lists, sub-CPU-X debugger traces and source Y-sprite RAM to select the descriptor afresh at each epoch. It verifies that the state lookup-position word at markers **965, 969 and 973** is identical across center/left/right. Those markers correspond to projection callbacks **964, 968 and 972**, descriptors at **966, 970 and 974**, and next screens at **967, 971 and 975**. The owner-local override files and all screenshots remain ignored under `build/private/`.

Prepare the nine private, single-descriptor inputs from the existing baseline captures:

```sh
python3 tools/phase1b_matched_far_depth.py build/private prepare
```

The ignored `build/private/phase1b-matched-far-inputs/plan.json` lists the exact slot and source/override SHA-256 for each run (plan SHA-256 `87825b5dafb82b7e294639f9e039803c4fa6bea11f8624664663602cf42751e6`). Reproduce each run in a fresh ignored directory. For example, the center descriptor at callback 970 is:

```sh
SDL_VIDEODRIVER=dummy PDRIFT_SOURCE_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_SEQUENCE_END_FRAME=972 PDRIFT_STATE_LOAD=/absolute/private/callback950.sta PDRIFT_SOURCE_OVERRIDE_FRAME=970 PDRIFT_SOURCE_OVERRIDE_RANGE=E4B0:0010 PDRIFT_SOURCE_OVERRIDE=/absolute/private/phase1b-matched-far-inputs/center-0970.bin /private/tmp/pd-mame0289-source/mame pdrift -rompath /absolute/private/rompath -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
python3 tools/phase1b_matched_far_depth.py build/private analyze
```

Use the matching side/frame/slot from the plan, with `PDRIFT_STEER_PULSE=64` or `192` for left/right; set `PDRIFT_SEQUENCE_END_FRAME` to at least descriptor callback +2 (and at least 970). The nine replay directories are `build/private/phase1b-matched-far-hidden-{side}-{frame}/`. Private `results.json` SHA-256 is `9bda707c375414c0937e6e69d64a717b788ab66e10a2ad6afc2f85f1e318e1ae`. The SHA-256 manifest for all eleven intervention input logs, including controls, is `build/private/phase1b-matched-far-inputs/log-sha256.txt` (manifest SHA-256 `60cd7dc022e62a350ba475652739b0c4d10d2fd7f11ea2986faf7f316e9fc681`). These paths contain proprietary-derived RAM captures and stay ignored.

## Descriptor and screen evidence

**Verified by execution:** each selected `$3A00` projection position uniquely matched a Y-sprite-type shared-list record at the next selected epoch; the full record matched one frame-marked sub-CPU-X load, whose output pointer identified one non-hidden descriptor. Descriptor slots changed across epochs, so the intervention follows record identity rather than a fixed slot. The chosen descriptor's hide bit changed **one byte only** in each 64 KiB source-RAM copy, and every screen through the intervention callback matched baseline byte-for-byte.

| Descriptor callback → screen | Center slot / changed pixels / bounding box | Left slot / changed pixels / bounding box | Right slot / changed pixels / bounding box |
| --- | --- | --- | --- |
| 966 → 967 | `$E490` / 0 / none | `$E490` / 0 / none | `$E490` / 0 / none |
| 970 → 971 | `$E4B0` / 70 / x135–196, y135–136 | `$E4B0` / 83 / x142–207, y134–139 | `$E4C0` / 66 / x123–189, y134–139 |
| 974 → 975 | `$E4C0` / 138 / x127–204, y135–138 | `$E4C0` / 51 / x145–218, y136–141 | `$E4E0` / 145 / x110–186, y134–142 |

**Verified by execution:** the center and left selected descriptors used graphic-offset word `$3C84` at all three epochs. Right used `$3C84` at callback 966 but `$3C8C` at 970 and 974, despite equal *state lookup position* at the compared markers. Thus even the controlled state-position comparison does not hold graphic choice fixed. The rule selecting `$3C8C` is **unsupported**; screen bounding boxes cannot be interpreted as a camera-only translation.

**Verified by execution:** a callback-974 center same-value override left source RAM and callback-975 screen identical to baseline. Repeating the callback-974 center hide reproduced the altered source RAM and screen byte-for-byte. The focused test therefore establishes a visible contribution at two successive selected epochs and a genuinely invisible or fully occluded contribution at the first; whether the first case is clipping, overlap or transparent source pixels remains **unsupported**. The observed changed-pixel counts are composed 320×224 MAME screen pixels, not hardware timing, physical dimensions or a full object mask.

**Inference from verified execution:** the `$3A00` sample is useful as a short, steering-sensitive *visibility check*, but 51–145 changed pixels over narrow rows are too sparse and asset-dependent to certify a full arcade camera-to-Sega-CD mapping. **Unsupported:** a continuous road centerline/edge, calibrated camera pose, curvature/elevation units, sufficiency of the existing five-word Sega CD camera interface, or original-hardware performance. No second arcade emulator, Sega CD adapter implementation or physical hardware test was run.

**Next bounded test — hypothesis:** search the already captured nearby depth records for a wider, consistently visible descriptor within the same exact-position window, then evaluate a private offline mapping into the existing five-word Sega CD controls against that measurable visual target. Do not change the renderer or interface based on this small far-depth patch alone.
