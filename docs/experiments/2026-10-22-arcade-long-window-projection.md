# Phase 1B: longer-window arcade projection signal — 2026-10-22

**Question / hypothesis:** can fixed-depth arcade geometry samples provide a graphics-source-independent signal over more than the two display epochs previously validated? **Baseline:** the owner-local callback-950 MAME state, held pedal, center steering 128 or left/right pulses 64/192 at callback 960, and the existing callback-960–1000 captures. **Acceptance:** verify the same source tuple for several depths; follow each projected X/Y pair through shared list, sub-CPU-X load and live descriptor across ten selected epochs; separate equal lookup-position steering comparisons from later diverging trajectories. **Result — PASS for a bounded projection signal, verified by execution of analysis on MAME captures:** depths `$3800` and `$3A00` trace at all ten epochs in each steering run, while `$3600` traces at nine. Signed projection words vary smoothly with steering even when graphic words and sprite draw direction change. These words are a candidate offline reference, **not** decoded physical camera coordinates or formal road edges.

## Environment and reproduction

**Verified by execution:** analysis baseline commit `7df05dcac05c58840ca08a33d8fbfa68e7fdd2f1` on `experiment/perspective-road`; macOS 26.6.2 x86_64. The reused private captures were produced by isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, executable SHA-256 `86cedb4f1a0f85ace895fa533a33c5e6eedb3fbd4f272ad85aa85410174d1d3d`, with the existing [capture-only bitmap patch](../../tools/phase1b_mame_ybitmap.patch). The owner-local 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. This experiment reran analyzers on previously recorded MAME state, geometry, shared-list, sub-CPU debugger and sprite-RAM captures; it did not launch a new emulator replay or test hardware.

**Verified by execution:** original analyzer [phase1b_projection_window.py](../../tools/phase1b_projection_window.py), SHA-256 `b3402001d3887b2be4fa6768e4313cbbf57f68a1610ed83b9b92a877a5179f7e`, reads the three private `phase1b-depth-sequence-{center,left,right}` geometry/list/source sets, three `phase1b-far-subx-*` debugger logs, and three `phase1b-upstream-speed-*` state logs. It uses the exact projected X/Y longword to select a unique Y-sprite-type list record, then matches the complete record to one sub-CPU-X load and that load's output pointer to one non-hidden descriptor. It checks the fixed ROM source tuple at every one of 41 callback snapshots for depth indexes 0–4 in all runs. Reproduce with:

```sh
python3 tools/phase1b_projection_window.py build/private
python3 tools/phase1b_upstream_state.py build/private
python3 tools/phase1b_far_depth.py build/private
```

**Verified by execution:** private result file `build/private/phase1b-projection-window/results.json` SHA-256 `6b02d6c9b60c6cde348c38d7be86b36e1e896af929367e35f657d` records all 150 attempted depth/epoch/steering associations, absence status, signed projection words, lookup positions, and descriptor fields when found. It also records the three baseline geometry CSV hashes. The private input-log and ROM/state checksums are cited in the [depth-sequence](2026-10-21-arcade-depth-sequence-limit.md) and [upstream-state](2026-10-21-arcade-upstream-state-and-matched-depth.md) reports. Derived per-sample records remain ignored alongside the proprietary captures rather than becoming a distributed arcade track-data extract.

## What remained traceable

**Verified by execution:** the five selected ROM depth/sample tuples were unchanged across all **41 callbacks × 3 steering conditions** for each depth index. This means the same fixed source sample was projected under changing global state; it does **not** identify a named track segment or a world-space coordinate system. Ten projection callbacks were selected at 960, 964, …, 996, with descriptor callbacks two later.

| Depth | Center traced epochs | Left traced epochs | Right traced epochs |
| --- | ---: | ---: | ---: |
| `$3200` | 7/10 | 5/10 | 5/10 |
| `$3400` | 8/10 | 7/10 | 7/10 |
| `$3600` | 9/10 | 9/10 | 9/10 |
| `$3800` | 10/10 | 10/10 | 10/10 |
| `$3A00` | 10/10 | 10/10 | 10/10 |

**Verified by execution:** **126/150** candidate associations reached a unique list record, sub-CPU-X load, and live descriptor. The other 24 projected positions had no matching Y-sprite-type list record in that callback's captured list. Calling them clipped, rejected, or replaced would require an additional trace; their exact omission mechanism is **unsupported**. The farther `$3800`/`$3A00` samples make a continuous ten-epoch *data* reference even though their screen visibility is intermittent, as shown by the [earlier far-depth hide tests](2026-10-21-arcade-far-depth-visibility.md).

## Steering comparisons and interface relevance

**Verified by execution:** the exact upstream lookup-position word matched center, left and right at projection callbacks **960, 964, 968 and 972** (state markers 961, 965, 969, 973). Left first diverged at projection 976; right first diverged at 988. Later numbers describe each run's own progression and are not same-track-position steering controls.

Within the exact-position window, the signed projected X response is opposite under left/right steering and grows at nearer tested depths. The table gives **steered X minus center X** in the arcade projection words, not screen pixels or camera units:

| Projection callback | `$3600` left / right | `$3800` left / right | `$3A00` left / right |
| --- | ---: | ---: | ---: |
| 960 | 0 / 0 | 0 / 0 | 0 / 0 |
| 968 | +14 / −13 | +11 / −10 | +9 / −8 |
| 972 | +28 / −28 | +20 / −21 | +15 / −16 |

**Verified by execution:** the corresponding projected Y differences at callback 972 were 0/0 for `$3600`, −1/0 for `$3800`, and +2/0 for `$3A00`; their physical meaning is **unsupported**. Over each run's ten-epoch sequence, `$3800` X moved from 8 to 56 (center), 8 to 268 (left), and 8 to −274 (right); `$3A00` moved from 7 to 25, 7 to 138, and 7 to −133 respectively. Those longer changes include unequal lookup-position progression after the matched window. The earlier [graphic/direction experiment](2026-10-22-arcade-graphic-direction-coupling.md) explains why a sprite descriptor's X origin is not a stable substitute for these pre-graphic projection words.

**Inference from verified execution:** the signed projected X/Y pairs at fixed depths are the cleanest reference currently available for an offline arcade-to-Sega-CD mapping because they precede graphic-offset choice, sprite direction and visibility. Their depth-ordered steering response is consistent with a perspective-sensitive lateral transform, but whether it corresponds to road center, camera displacement, track curvature or a combination is **unsupported**. The existing [five-word Sega CD interface](2026-10-20-live-road-camera-commands.md) carries curve phase, ridge phase, bank, horizon and texture phase into a synthetic renderer; it has no direct per-depth X/Y fields. That does **not** establish an interface failure: suitable tables or an offline adapter might produce the observed profile from those controls. No fit, Sega CD replay or representational-failure test was performed here.

**Hypothesis for the next bounded test:** establish the scale and role of the upstream projected X/Y words by perturbing one already traced state input at a time in private replay, or by replaying the documented projection arithmetic offline, then test whether one set of camera controls can reproduce the **multi-depth shape** at held-out matched-position epochs. Keep raw arcade sequence data private and leave the renderer/interface unchanged until a specific mismatch is measured.

**Not run / unsupported:** physical arcade or Sega CD hardware, a new MAME run in this experiment, a complete track section, calibrated camera pose, actual Sega CD adapter, and stock-hardware timing. The prior upstream-state and far-depth analyzers passed as regression checks; Python compilation and the staged whitespace check passed.
