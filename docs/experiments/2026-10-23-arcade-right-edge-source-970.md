# Phase 1B: callback-970 right-edge source — 2026-10-23

**Question / hypothesis:** which locally captured Y-sprite source descriptor supplies the visible right road-region boundary under mild left steering at callback 970? **Baseline:** the [steered trajectory audit](2026-10-23-steered-road-trajectory-audit.md), where the previously selected `$E5D0` strip moved one left boundary but no right boundary. **Acceptance:** locate a source range with a right-edge effect, narrow it to a single descriptor, verify exactly one changed source byte and unchanged earlier screens, and confirm a joint left/right intervention. **Result — verified by execution: PASS for the screen-971 boundary at Y=154–156; the source relationship at screen 973 remains unresolved.**

## Setup and narrowing

**Verified by execution:** source commit `4def1fb` on `experiment/perspective-road`, with only this search tool uncommitted during execution. macOS Darwin 25.6.0 x86_64; Python 3.14.8; locally installed MAME `0.289 (unknown)`, executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`. The same owner-local 53-file ROM manifest and callback-950 saved state used in the prior report have SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f` and `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The saved-state replay sets steering to 112 at callback 960 and uses the prior coin/start/pedal schedule. All coordinates below are 320×224 arcade composed-screen pixels, not world or Sega CD coordinates.

**Verified by execution:** `tools/phase1b_right_source_search.py` copied the captured 64 KiB source sprite RAM at callback 970, set the descriptor hide bit `$10` used in the earlier causal experiments at aligned candidate starts, and replayed that source at callback 970. The captured post-override RAM matched each prepared private file exactly; all composed screens 960–970 remained pixel-identical to baseline. The table records whether hiding a range changed the independently detected left/right boundary pixels on screen 971:

| Hidden source range | Y=154–155 left changed? | Y=154–155 right changed? |
| --- | :---: | :---: |
| `$E000–E7FF` | yes | yes |
| `$E000–E3FF` | no | no |
| `$E400–E7FF` | yes | yes |
| `$E400–E5FF` | no | no |
| `$E600–E7FF` | yes | yes |
| `$E600–E6FF` | yes | yes |
| `$E700–E7FF` | no | no |
| `$E600–E63F` | no | yes |
| `$E640–E67F` | yes | no |

**Verified by execution:** the broad hides are localization probes; their combined effects alone cannot assign a pixel to one descriptor. Independent one-byte trials resolved the relevant records:

| Hidden descriptor | Captured graphic word | Screen-971 Y=154–155 left | Screen-971 Y=154–155 right | Y=156 |
| --- | ---: | :---: | :---: | --- |
| `$E630` | `$3F45` | unchanged | changed | neither edge changed |
| `$E660` | `$2898` | changed | unchanged | both edges changed |

**Verified by execution:** individual hides at `$E600`, `$E610`, `$E620`, `$E640`, `$E650` and `$E670` did not change either boundary at Y=154–155, although some alter other screen pixels or rows. A joint replay changed **exactly two** source bytes, `$E630` and `$E660`, and changed *both* boundary pixels in **3/3** visible rows Y=154–156. Baseline `(left,right,width)` for those rows was `(86,292,207)`, `(78,292,215)`, `(69,298,230)`; width is inclusive and may include shoulders. The screen-971 baseline and joint-hidden PNG SHA-256 values were `52867e796f83b40a0cb390cc4325478385a489b23b202fca21d8b627a7fd69c0` and `123fa87d184d24f62957b780c1ed24000cdd8a0a050aaa5f669546b07402379a`.

**Inference from verified execution:** the right boundary at Y=154–155 is causally dependent on the source record at `$E630`, while the same visible width spans contributions from at least two descriptor records. Graphic IDs identify captured descriptor fields; their asset meaning and original track semantics are **unsupported**. This explains why hiding only the earlier `$E5D0` road candidate could not validate both sides.

## Adjacent-frame timing limit

**Verified by execution:** the same independent `$E630`/`$E660` one-byte hides at callback 971 left the entire next composed screen 972 byte-identical to baseline; repeated at callback 972, they left screen 973 byte-identical. Their source RAM overrides were captured and verified, and prior screens matched. Source records at those callbacks retain the same graphic words, but source presence plus a successful RAM write does not prove that a given rotation/composition update consumes them.

**Hypothesis:** callback timing, Y-sprite buffering, or another active descriptor accounts for the screen-973 boundary. This experiment did not isolate the mechanism. **Unsupported:** a continuously causal two-sided arcade width trajectory, a decoded world-space track edge, and any new requirement on the Sega CD five-word camera interface. No BlastEm, second arcade emulator, or physical-hardware test was performed.

## Reproduction and next step

```sh
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --groups E000:0800 0000:10000
python3 tools/phase1b_right_source_search.py build/private analyze --groups E000:0800 0000:10000
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --groups E600:0010 E610:0010 E620:0010 E630:0010
python3 tools/phase1b_right_source_search.py build/private analyze --groups E600:0010 E610:0010 E620:0010 E630:0010
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --groups E640:0010 E650:0010 E660:0010 E670:0010
python3 tools/phase1b_right_source_search.py build/private analyze --groups E640:0010 E650:0010 E660:0010 E670:0010
python3 tools/phase1b_right_source_search.py build/private run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --exact-slots E630 E660
python3 tools/phase1b_right_source_search.py build/private analyze --exact-slots E630 E660
python3 -m py_compile tools/phase1b_right_source_search.py
```

**Verified by execution:** the intermediate half-range probes used the same `run`/`analyze` commands with groups `E000:0400 E400:0400`, `E400:0200 E600:0200`, `E600:0100 E700:0100`, `E600:0080 E680:0080`, and `E600:0040 E640:0040`. Ignored private logs, source RAM, overrides, screenshots and analysis JSON are under `build/private/phase1b-right-search-*`. The private one-byte `$E600–E63F`, one-byte `$E640–E67F`, and joint JSON SHA-256 values are `96af143b67cb530fce7f8f20b87d68478f44640bd3040ddc2a4bd54dbec6899b`, `30457656cfa4d74ec06ae10cbf245fcc38d5ef501f745aaa0d92f9b47aa5f78c`, and `5a3c30c7f4cef6f705c610835dc5146049ae69c09b08af5bf911beb56c5b3db1`. Commercial imagery and source RAM remain private and ignored.

**Next bounded test — hypothesis:** capture or instrument the Y-sprite-to-rotation-buffer consumption stage around callbacks 970–974, then identify the descriptor(s) responsible for screen 973. Once a second update has causally verified left and right boundaries under the same crop, compare their motion against the original-art host fixture; do not redesign the camera interface from this one resolved update.
