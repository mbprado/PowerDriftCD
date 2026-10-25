# Phase 1B: Y-sprite source-to-screen lag probe — 2026-10-25

**Question / hypothesis:** did the callback-979 `$C` descriptor hide that partly changed screen 980 persist into screens 981–982, potentially supplying their otherwise unexplained road edges? **Baseline and acceptance:** the locally committed [lag plan](2026-10-25-y-sprite-source-lag-plan.md) (`a09a6f8`) required two isolated hides at callbacks 979 and 980, composed captures through screen 982, exact source-RAM override checks, unchanged prior screens and separate left/right edge counts. **Result — verified by execution in MAME:** the callback-979 hide affected screen 980 only; screens 981 and 982 were **byte-identical** to baseline. The callback-980 hide affected neither later screen. The source intervention therefore has no observed multi-screen lag in this window, and it still cannot establish a three-row two-sided road reference.

## Measured results

| Hide callback and page | Composed screen | Detected baseline rows Y=153–163 | Left edge changed | Right edge changed | Both changed | Whole screen differs? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 979, `$C000`–`$C7FF` | 980 | 3 | 3 | 1 | 1 | yes |
| 979, `$C000`–`$C7FF` | 981 | 7 | 0 | 0 | 0 | no |
| 979, `$C000`–`$C7FF` | 982 | 7 | 0 | 0 | 0 | no |
| 980, `$C000`–`$C7FF` | 981 | 7 | 0 | 0 | 0 | no |
| 980, `$C000`–`$C7FF` | 982 | 7 | 0 | 0 | 0 | no |

**Verified by execution:** `tools/phase1b_source_lag_audit.py` checked that exactly **116** descriptor hide bytes changed in each trial, all within `$C000`–`$C7FF`, and that the post-write source RAM equaled the prepared override. Screens 960 through the intervention callback remained pixel-identical to the fresh pulse-112 baseline. The callback-979 replay's screen-980 PNG matched the earlier screen-980 `$C` hide PNG byte-for-byte, independently confirming the previously observed partial response. The analyzer used baseline detected rows, not rows found in hidden images. Two analyzer runs produced identical ignored JSON SHA-256 `8ee56119006454acf6a5ccc6924af4810d42b48c2bd45708aa2dbb6eafbd545f`.

**Inference from verified execution:** the `$C` source hide's visible effect is confined to screen 980 in this observed two-screen window. This rules out *that exact intervention* simply appearing one or two composed screens later. It does **not** locate the right-edge source for Y=157–158 on screen 980 or the visible road source for screens 981–982. A different descriptor set, native bitmap timing, rotation clipping, or foreground composition remains a **hypothesis**. The screen-space sand boundary can include shoulders and overlays and is not decoded world-track geometry. No Sega CD packet was scored or changed.

## Reproduction and provenance

**Verified by execution:** source baseline `a09a6f8` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; system MAME `0.289 (unknown)` executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; owner-local ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 saved state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The baseline 960–990 capture and its checksums are in the [causal-gate report](2026-10-25-forward-road-causal-gate.md). No BIOS, BlastEm, second emulator or physical hardware was run; MAME wall-clock speed was not interpreted as arcade hardware speed.

**Verified by execution:** the two private replay logs under `build/private/phase1b-source-lag/phase1b-right-search-{979,980}-C000-00800/phase1b-input.log` have SHA-256 `9723c609f29cf8681e24d09763afafd5be16b3a603c15e92ccbccf05e3875d0d` and `dff2e167c59dc4d5cd607a3d86cb94a5770b745954dbbbdbf1668950e7bf82e2`. The audit tool SHA-256 is `bc512f9e25f7d802847567bba72cea2b82de1bbb1dbcebac2ec7c3706f45eb52`; the minimally extended source-hide runner SHA-256 is `1954a4fb8386cf089d6068cc25060804bf6915a3a50afcc4264e261f67835c18`. Both scripts contain original analysis logic, with no ROM bytes or proprietary image data. The runner's new optional `--capture-end` leaves the old default behavior intact and lets a single intervention be observed across subsequent screens.

```sh
mkdir -p build/private/phase1b-source-lag
ln -s ../phase1b-forward-baseline-112-990 build/private/phase1b-source-lag/phase1b-forward-baseline-112-990
python3 tools/phase1b_right_source_search.py build/private/phase1b-source-lag run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 979 --groups C000:0800 --capture-profile road-edge --baseline-name phase1b-forward-baseline-112-990 --capture-end 982
python3 tools/phase1b_right_source_search.py build/private/phase1b-source-lag run --mame /usr/local/bin/mame --rompath build/private/phase1b-roms --state build/private/phase1b-range-state-seed/callback950.sta --callback 980 --groups C000:0800 --capture-profile road-edge --baseline-name phase1b-forward-baseline-112-990 --capture-end 982
python3 tools/phase1b_source_lag_audit.py build/private/phase1b-source-lag build/private/phase1b-right-search-979-C000-00800/swap-screen-0980.png
```

The isolated private lag directory references the prior private baseline by a local symlink; it does not copy or track ROM/state/image content. All source RAM, screenshots and raw logs remain ignored under `build/private`.

**Next bounded test — hypothesis:** capture or reconstruct the *native* Y-sprite bitmap at the screen-980 render point and compare it with the composed screen under the callback-979 `$C` hide. The existing isolated MAME bitmap instrumentation previously covered earlier frames; extend it in a separate build if necessary, without changing upstream installation. If a right boundary pixel exists in the native bitmap but is unchanged after composition, trace rotation/foreground masking. If it does not, narrow the source descriptor or other layer supplying that boundary. Require a repeated causal replay before using new rows for a camera adapter.
