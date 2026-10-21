# Phase 1B: nearby road-depth visibility at matched lookup positions — 2026-10-21

**Question / hypothesis:** does a depth record nearer than the sparse `$3A00` record give a wider, repeatedly visible reference within the same exact state-lookup-position window? **Baseline:** the [matched far-depth trial](2026-10-21-arcade-matched-far-depth-visibility.md), the owner-local callback-950 state, held pedal, and center/left/right steering pulses. **Method:** follow depth indexes 1–3 (`$3400`, `$3600`, `$3800`) from projection through a unique shared-list record and sub-CPU-X load to a live Y-sprite descriptor; hide only that descriptor in independent private MAME replays; compare the next composed screen with the unmodified baseline. **Result — PASS for visibility, verified by execution in MAME:** `$3400` produced a broad visible strip at all three selected epochs and all three steering conditions. It is a useful *visual target*, but the right run changed graphic-offset words despite matched lookup position, so the current comparison does not isolate camera motion.

## Environment and reproduction

**Verified by execution:** source baseline `1fe10b409f28d52537dd691e4a0a21157b0670de` on `experiment/perspective-road`; macOS 26.6.2 x86_64; isolated MAME 0.289 (`mame0289-dirty`) from source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, using the existing [capture-only bitmap patch](../../tools/phase1b_mame_ybitmap.patch). The owner-local 53-file ROM manifest SHA-256 was `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; the private callback-950 state SHA-256 was `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. These are identifiers for local evidence, not distributed ROMs or assets.

**Verified by execution:** original analyzer/runner [phase1b_near_depth_visibility.py](../../tools/phase1b_near_depth_visibility.py) SHA-256 `1e976c2493f6883adb9ec496375c27a00d3c04efdc3ba3a8f1781c8c57e0f544` used existing private `phase1b-depth-sequence-{center,left,right}` baselines and `phase1b-far-subx-{center,left,right}` debugger logs. Projection callbacks **964, 968, 972** map to lookup-state markers **965, 969, 973**, descriptors **966, 970, 974**, and composed screens **967, 971, 975**. At all three selected markers, the exact lookup-position word was equal across the steering runs. The full transform state was not equal.

From the repository root, with the same locally held state and ROM set, reproduce the original tool's private inputs and runs:

```sh
python3 tools/phase1b_near_depth_visibility.py build/private prepare
python3 tools/phase1b_near_depth_visibility.py build/private run --mame /private/tmp/pd-mame0289-source/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_near_depth_visibility.py build/private controls --mame /private/tmp/pd-mame0289-source/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_near_depth_visibility.py build/private analyze
```

**Verified by execution:** the runner launches MAME with the fixed state, `-noreadconfig -video none -sound none -nothrottle -seconds_to_run 18`, the existing `phase1b_mame_input.lua` script, and left/right pulse values 64/192. It selects the descriptor by record identity for each trial and overrides only that 16-byte source-RAM slot. The private plan, changed 64-KiB RAM copies, logs, screenshots and results remain ignored under `build/private/phase1b-near-depth-*`. Plan SHA-256 `f5c1b10b0db1f2e4572d298fae2174c94eb265e83f282ebef38b0a447c440aa6`; results JSON SHA-256 `aadd7b84e66a9ed4da0c571b79fe7d737baacc3fa263081b1e0a4c1ef5b04cbe`. The private manifest `phase1b-near-depth-inputs/log-sha256.txt` covers **29** replay logs, including two controls, and has SHA-256 `19a242a0e9352c3e918d5101cc9de8974429f0036e7a88de1d682b30e167b1f7`.

## Observations

**Verified by execution:** all **27/27** geometry → shared-list → sub-CPU-X → descriptor matches were unique, and all 27 hide replays changed exactly one source-RAM byte. Every composed screen through the intervention callback matched its unmodified baseline byte-for-byte. The following counts are changed RGB pixels on the *next* 320×224 MAME composed screen; they are not object area, emulated timing, or hardware performance.

| Depth / index | Screen 967 center / left / right | Screen 971 center / left / right | Screen 975 center / left / right |
| --- | ---: | ---: | ---: |
| `$3400` / 1 | 796 / 798 / 785 | 1,609 / 1,689 / 1,406 | 4,058 / 3,807 / 4,191 |
| `$3600` / 2 | 124 / 124 / 124 | 427 / 437 / 415 | 797 / 802 / 662 |
| `$3800` / 3 | 125 / 128 / 122 | 43 / 52 / 40 | 126 / 218 / 126 |

**Verified by execution:** the `$3400` strip's changed-pixel bounding boxes were:

| Next screen | Center x / y | Left x / y | Right x / y |
| --- | --- | --- | --- |
| 967 | 101–246 / 140–147 | 103–248 / 139–149 | 96–238 / 137–149 |
| 971 | 86–251 / 143–154 | 103–284 / 142–160 | 67–248 / 140–160 |
| 975 | 57–306 / 147–169 | 97–319 / 147–181 | 18–259 / 143–180 |

**Verified by execution:** center/left selected `$3400` descriptor graphic-offset word was `$3888` at all three epochs. Right used `$3888` at descriptor 966 and `$3898` at 970/974. Thus the selected depth record remains identifiable and visible, but the later steering comparison also changes graphic source. Its screen-pixel deltas include occlusion, transparency, palette and composition effects; the table does not measure a pure camera transform. The graphic-selection rule is **unsupported** by this trial.

**Verified by execution:** a same-value callback-974 center override left source RAM and screen 975 identical to baseline. A repeat of the changed callback-974 center override reproduced both changed source RAM and screen 975 byte-for-byte. The prior-screen and control results support causal attribution of the changed pixels to the selected descriptor, within this MAME configuration. The earlier `$3A00` matched-depth analyzer also passed again as a regression check; `python3 -m py_compile` and `git diff --check` passed.

## Interpretation and next test

**Inference from verified execution:** `$3400` is a materially better visual reference than `$3A00` in this three-epoch window because it contributes hundreds to thousands of visible pixels in every steering run. The visible shape grows toward the near field, making it useful for an offline camera/geometry comparison. Its exact physical road height, world-space units, curvature, and screen-edge semantics remain **unsupported**. A broad bounding box alone is not a calibrated road contour.

**Hypothesis:** the next bounded test should hold graphic selection constant in a *private comparison* where possible, then extract a repeatable visible strip outline or centerline from the `$3400` descriptor under the three steering inputs. Only after that should an offline adapter attempt to fit the arcade observation to the existing five-word Sega CD camera controls. Do not change that interface or the renderer until a specific representational failure is measured.

**Not run / unsupported:** second arcade emulator, actual Sega CD adapter, stock Sega CD timing, and physical hardware. No proprietary RAM, screenshot, graphic, BIOS or ROM data was committed. This experiment does not establish that the complete arcade camera or road can be represented by the current Sega CD prototype.
