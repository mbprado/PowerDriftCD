# Phase 1B: pulse-204 screen-968 Y-sprite page and exact source — 2026-10-28

## Question and frozen test

**Hypothesis:** the screen-968 edge pixels previously mapped to native bitmap 967 come from page C after a Y-sprite list update between Lua callbacks 967 and 968. **Baseline:** local `661334f` on `experiment/perspective-road`, the [native-source result](2026-10-27-screen968-native-source.md), and the [pretarget page-C plan](2026-10-27-screen968-page-c-plan.md). The ten native/screen pixels, pulse 204, callback 967, pre-966 transform and Y=159–163 rows stayed fixed. The plan specified one page-C intervention, followed by bounded descriptor splits only if that intervention passed. No camera packet was fitted.

**Documented from pinned MAME source:** `segaybd.cpp` maps the sub-X `$180000–$18FFFF` share as Y-sprite RAM and invokes `draw_async` before the rotation step. `sega16sp.cpp` traverses live `spriteram()` in `sega_yboard_sprite_device::draw`. **Verified by read-only inspection of owner-private MAME captures:** callback-967's reachable list used page E, callback-968's used page C, while all page-C bytes were identical in the two snapshots. Thus a page-C hide at callback 967 was a specific timing hypothesis. The exact instruction or sub-frame instant that changes the head has **not** been traced.

## Result

**Verified by execution in isolated MAME 0.289:** hiding the 212 active page-C descriptors at callback 967 changed all **10/10** frozen screen-968 RGB edge pixels and made all **10/10** corresponding native-967 words transparent under the pre-966 transform. Screens 960–967 remained identical to the baseline. The earlier page-E hide changed **0/10**. This supports page C, rather than the list reachable at the earlier Lua callback, as the page drawn for these sampled pixels.

**Verified by execution:** seven sequentially frozen interval splits localized the effect to a single 16-byte descriptor at `$C630`. Each split tested two disjoint ranges against the same ten-pixel vector. In the table, the pair is the changed RGB/native sample count; the two counts agreed for every interval.

| Split | First range | Result | Second range | Result |
| --- | --- | ---: | --- | ---: |
| 1 | `$C000:0380` | 0/10 | `$C380:0380` | 10/10 |
| 2 | `$C380:01C0` | 0/10 | `$C540:01C0` | 10/10 |
| 3 | `$C540:00E0` | 0/10 | `$C620:00E0` | 10/10 |
| 4 | `$C620:0070` | 10/10 | `$C690:0070` | 0/10 |
| 5 | `$C620:0040` | 10/10 | `$C660:0030` | 0/10 |
| 6 | `$C620:0020` | 10/10 | `$C640:0020` | 0/10 |
| 7 | `$C620:0010` | 0/10 | `$C630:0010` | 10/10 |

**Verified by execution:** the `$C630` override changed exactly one descriptor hide byte and no other source byte. All five rows had both edge RGB pixels changed, both mapped native words became `$FFFF`, and the captured 16B layer was clear. The exact-slot screen changed 14,513 decoded RGB bytes overall; this is an image-difference count, not a hardware timing measure. Two further **fresh MAME executions** of the same exact-slot intervention reproduced the 10/10 result. The three runs had identical source-override, screen-968 PNG and native-967 bitmap SHA-256 values, while their logs differed because each run used its own private paths. The aggregate [auditor](../../tools/phase1b_screen968_narrow_audit.py) verifies all 14 interval scores and three run hashes; it does not count cache reads as new MAME executions.

**Decision:** exact Y-sprite source attribution is **PASS for these ten sampled pixels**. The callback-967 page-E failure and page-C success strongly support an intervening list-head or scheduling change, but its exact trigger remains **hypothesis**. The `$C630` descriptor may draw more than the sampled road-boundary pixels; its full semantic role and the purity of the visual boundary remain **unsupported**. The arcade-to-Sega CD camera adapter is **INCONCLUSIVE**: no prospective numeric mapping from the predicted arcade state to the five-word command was tested. No host preview, BlastEm, second arcade emulator or physical hardware was run; MAME host time was not treated as hardware performance.

## Evidence and reproduction

**Verified by execution:** macOS Darwin 25.6.0 x86_64, Python 3.14.8, isolated MAME `0.289 (mame0289-dirty)` executable SHA-256 `6ec5bced7e0836da7a0f61aa0e27c99ec1f08e064703df58568ceb0524ecb7c4`, pinned source `f34f02505e32c1993c6a782b6814232cbfc74e36`; Lua capture/intervention script SHA-256 `a2c452d38f391d18386e43b6646ee7a0d041692529d66cbd969608ad441ac5c1`; owner-private 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The image was the existing locally held `pdrift` set, not a Sega CD disc. The [narrow runner](../../tools/phase1b_screen968_narrow.py) SHA-256 is `f6f36f99db26fad3fd0879dc57e5dd68c703d9ae0745b0cc8d12d26611044de4`; aggregate auditor SHA-256 `0cbc4cb9f9e46432ff25b2d613a40acabc6e5fb8c2066b3ea92fab7ddd8cd734`. Build details and the native bitmap capture patch are in the [previous report](2026-10-27-screen968-native-source.md).

**Verified by execution:** the ignored page-C override `build/private/phase1b-pulse204-screen968-pageC-source.bin` has SHA-256 `bae2e9dd0a467947d1344334438be5f213a152bd4999965dbc5d041fc6c0b4d7`. Its MAME replay was configured like the previous page-E trial, with `PDRIFT_SOURCE_OVERRIDE_RANGE=C000:1000` and `PDRIFT_SOURCE_OVERRIDE_FRAME=967`; the resulting screen-968 PNG SHA-256 was `70d203de12148d54f83c9eec45a41746e67a90bf6ae9d11a67fcb6c16c3529ec`, native-967 bitmap SHA-256 `043e238a765f7cfbc62596a50e53c8ffb6b188a99357b0ebede251725d67589f`.

The first split was run with the same explicit MAME command and private source overrides; subsequent splits used `python3 tools/phase1b_screen968_narrow.py run START SIZE`, then `score START SIZE`, with the hex ranges in the table. The exact-slot repeats used `run C630 0010 --repeat 1` and `--repeat 2`, followed by matching `score` calls. The runner refuses to overwrite existing trials. Finish with `python3 tools/phase1b_screen968_narrow_audit.py`; the ignored result `build/private/phase1b-screen968-narrow-audit.json` SHA-256 is `2952b0d9c3d318b8f2e555bcc2974f17bb8380f9d391ea07bb46dbd4c4a98d4e` and contains every interval's score, image, source and log hashes. For the three exact-slot runs, override SHA-256 was `369aaef13e00dcbab2bc7ecc7768a406eea2720247faa940287b10e0866f4334`, screen-968 PNG SHA-256 `43a2885e8050a33d8111235ae3e63bcf7708c7a8a16b109eb3c86a96d3049815`, and native-967 bitmap SHA-256 `f32245dad154c974094e09860c7ea810606957f98437eea5b5d866e3575f7faa`. Raw logs, ROMs, source dumps and native bitmaps remain private under ignored `build/private/`.

**Next bounded step — hypothesis:** use the now identified `$C630` source to verify whether the five sampled row pairs are stable road-boundary features across one adjacent pulse-204 update, then derive a camera-packet selection rule from earlier arcade state and original renderer controls **before** any new pixel score. Do not enlarge the Sega CD interface or fit the packet to screen-968 target pixels.

**Subsequent timing correction (2026-10-28; verified by execution):** the [shared-record projection trace](2026-10-28-pulse204-road-record-projection.md) found that Sub-CPU X writes both `$E630` and `$C630` from the same `$0C9A60` list record during sequence frame 965. Each page descriptor was already stable across callbacks 966 and 967. The page-C versus page-E visibility result above still stands, but the proposed *intervening list-head update* is not established; the exact page-selection mechanism and instant remain **unsupported**.
