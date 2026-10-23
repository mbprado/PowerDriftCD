# Phase 1B: two-sided arcade road sample under mild steering — 2026-10-23

**Question / hypothesis:** can a controlled, milder arcade steering pulse retain both visible road-region boundaries at the established callback-974 landmark, and does the same `$3400` sprite strip cause both edges? **Baseline:** the [centered seven-row width landmark](2026-10-22-arcade-causal-right-extent.md) and its strong-left failure. **Acceptance:** replay the centered case pixel-identically, measure both independently visible sand boundaries under steering, hide one source descriptor byte, confirm prior screens unchanged and both boundary pixels affected. **Result — verified by execution: PASS for a six-row, one-frame two-sided mild-steering sample; INCONCLUSIVE for a longer steering trajectory.**

## Replay and controls

**Verified by execution:** source commit `30156a5` on `experiment/perspective-road`, with only the new analysis tool uncommitted during execution. macOS Darwin 25.6.0 x86_64, Python 3.14.8, system MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The owner-local 53-file ROM manifest SHA-256 was `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` as recorded in the earlier causal-edge report; the callback-950 saved state SHA-256 was rechecked as `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The replay Lua SHA-256 was `99f8696c43798720e3a4b4d20b059cb7390b763deb807c900e2bf0c800406a77`. No Sega CD image was built for this experiment.

**Verified by execution:** `tools/phase1b_mild_steer_width.py` replayed centered steering 128 and left pulses 112 and 96 from callback 960, using the same saved state, coin/start/pedal schedule, and locally held ROMs. Pulse 112 remained selected through callback 976. All **17/17** centered composed screens 960–976 matched the earlier centered capture pixel-for-pixel, and callback-974 source sprite RAM was byte-identical. The accepted boundary detector requires 16 sand pixels at each screen edge and four consecutive non-sand pixels inward. It scans the 320×224 MAME composed RGB image; all coordinates and widths below are arcade **screen pixels**, not world units or Sega CD pixels.

**Verified by execution:** at callback 974 / composed screen 975, the pulse-112 source descriptor at `$E610` retained graphic `$3888`. A private replay changed only the descriptor hide byte at `$E610` (bit `$10`). The captured source RAM differed from baseline at exactly that byte; screens 960–974 remained pixel-identical. At screen 975, both independently detected boundary pixels changed in **6/6** accepted rows Y=154–159. The apparent Y=153 left boundary X=26 did *not* change under this intervention, so that row is excluded. This is an intervention on a causal **visible strip**, not proof of a decoded world-space track edge.

| Screen Y | Center left/right/width | Pulse 112 left/right/width | Pulse 112 strip affects both edges? |
| ---: | ---: | ---: | :---: |
| 154 | unavailable | 82 / 296 / 215 | yes |
| 155 | unavailable | 81 / 296 / 216 | yes |
| 156 | 72 / 294 / 223 | 77 / 298 / 222 | yes |
| 157 | 70 / 296 / 227 | 76 / 300 / 225 | yes |
| 158 | 68 / 298 / 231 | 75 / 302 / 228 | yes |
| 159 | 67 / 299 / 233 | 74 / 303 / 230 | yes |

**Verified by execution:** on the four shared rows, both boundaries move right under pulse 112, while inclusive visible road-region width decreases by 1, 2, 3 and 3 pixels respectively. The width includes any shoulders between the sand transitions. Pulse 96 had **zero** independently two-sided rows at screen 975; it is a visibility limit of this detector, not evidence that the road disappears. Pulse 112 has other two-sided rows across screens 960–976, but only the six callback-974 rows above received the one-byte causal check. The center/reference and pulse-112 screen-975 PNG SHA-256 values were `035ebb74ba9e638c483047271a4b2a96fba44129273edcda168bf23e09336015` and `b4ac1d35d6be90614eccf40f7c126a57ad23aaa9050664473f55555a1ab0a4d2`; the hidden screen was `56c0c41379a638b7ae7c76bd72ab182cfb21ad03dfb15685c27c6352d4426da5`.

## Meaning for the Sega CD prototype

**Inference from verified execution:** scaling these arcade screen widths by 128/320 gives about 89–93 pixels on the four shared rows, within the current synthetic [wide road's](2026-10-23-coupled-wide-road-motion.md) 89–96-pixel row-28 range. That is an **envelope comparison only**. The arcade's screen Y=156–159 is not calibrated to Sega CD output row 28, the source road-region definition differs from the synthetic texture's road color, and no five-word camera packet has been derived from this arcade run. The measured lateral displacement is about 5–7 arcade pixels on the left edge and 4–5 on the right; it is small enough to motivate a host-only representability test, but does not demonstrate one. No sixth command word or renderer change is justified by this sample.

**Unsupported:** a complete arcade camera trajectory, world-space width or curvature, a calibrated 128×64 crop, a direct arcade-to-five-word adapter, 30 Hz behavior for an arcade-derived scene, and physical Sega CD performance. No BlastEm or second arcade emulator run was performed for this bounded Phase 1B test.

## Reproduction and next test

```sh
python3 tools/phase1b_mild_steer_width.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 tools/phase1b_mild_steer_width.py build/private analyze
python3 tools/phase1b_mild_steer_width.py build/private hide --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta
python3 -m py_compile tools/phase1b_mild_steer_width.py
```

**Verified by execution:** ignored raw logs, source RAM, screenshots, one-byte override and derived measurements reside under `build/private/phase1b-mild-steer-*`. The private analysis JSON SHA-256 values were `b1a3c902451564bb42905af9e40977c72a18a07444e047d78d773e17373fce1c` (width replay) and `b40990c092e218cec764ebf3ae78586b5aa52970dd75644a1b6da797bfa1f1f0` (hide intervention). These files and any commercial imagery remain ignored; the tracked tool contains no ROM bytes or extracted graphics.

**Next bounded test — hypothesis:** check several consecutive pulse-112 frames with one-byte interventions at their matching source descriptors, then compare the causally verified two-sided trajectory against the existing host-only 128×64 road fixture. First establish vertical row registration and an explicit screen-width mapping; only build a new Sega CD image if that host target reveals a meaningful new representability or timing question.
