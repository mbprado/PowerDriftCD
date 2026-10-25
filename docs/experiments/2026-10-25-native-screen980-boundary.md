# Phase 1B: native Y-sprite versus composed screen-980 boundary — 2026-10-25

**Question / hypothesis:** does the callback-979 `$C` Y-sprite hide change a native bitmap pixel under the screen-980 road's right edge at Y=157–158, only to have that change hidden by later composition? **Baseline and acceptance:** the [locally frozen plan](2026-10-25-native-road-boundary-plan.md) (`73b0de9`) requires an isolated MAME bitmap capture, exact decoded-screen replay controls, a full changed-pixel affine comparison, and native/screen values at each measured edge. **Result — verified by execution in MAME:** the two unchanged right-edge pixels map to **transparent native Y-sprite pixels in both runs**. They are outside the changed `$C` native region. The Y=159 right edge maps to a changed native pixel and changes on the composed screen. This resolves the requested native-versus-composed distinction but does not yet identify whether the other two right-edge colors come from rotation scanline fill or foreground 16B sprites.

## Isolated capture and controls

**Verified by execution:** the official MAME `mame0289` tag resolves to source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`. A fresh source clone in `/private/tmp/pd-mame0289-native980` received the tracked [capture-only patch](../../tools/phase1b_mame_ybitmap.patch) and [frame-window patch](../../tools/phase1b_mame_ybitmap_980.patch). `git apply --check` passed before each patch. A one-driver macOS build used `make SOURCES=src/mame/sega/segaybd.cpp NOWERROR=1 REGENIE=1 -j8`; the resulting executable reported `0.289 (mame0289-dirty)` and SHA-256 `f9489f5e153de79bba9c9c0a48930bf933f3e98d27440e84eaf4d10549edbf66`. The installed `/usr/local/bin/mame` and upstream repository were not modified. The build log SHA-256 is `1cf38963b586776683167aaf2c03b9289177e21447c90717eee9bf734a11afb4`.

**Verified by execution:** both saved-state replays used pulse-112 steering, the same callback-950 state and source-hide bytes as the [source-lag experiment](2026-10-25-y-sprite-source-lag.md). The patched baseline and hide screen-980 PNGs have different *file* checksums from the system-MAME PNGs, but their **decoded RGB pixels match exactly** in each condition. All patched baseline/hidden screens 960–979 match one another. Exactly 116 `$C000`–`$C7FF` descriptor hide bytes changed in captured post-write source RAM, and it matched the prepared override. Two additional independent patched hide replays produced the **same native-frame-979 and composed-screen-980 SHA-256 values** as the first hide run; the system-MAME hide image separately matched in decoded RGB.

**Verified by execution:** native frame 979 differed at **61,112** of 512×512 pixels between baseline and hide. Native frame 980 was byte-identical between conditions. The native-frame-979 change mask, mapped through the captured affine values, covered **all 43,224 changed composed-screen pixels**: zero false negatives, 49,232 predicted pixels and 6,008 predictions that did not change the final RGB image. The `pre-978`, `post-978` and `post-980` blocks contained the same six affine values for this mapping, so those block labels cannot be distinguished by this comparison. The `pre-980` block left 414 observed screen changes unexplained. The 6,008 extra predictions can reflect composition or equal final colors; they are not individually classified as masked pixels.

| Screen Y | Left X | Left native `(X,Y)`, before→after | Left changed on screen? | Right X | Right native `(X,Y)`, before→after | Right changed on screen? |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 157 | 90 | `(185,207)`, `78→65535` | yes | 290 | `(385,202)`, `65535→65535` | no |
| 158 | 84 | `(179,208)`, `70→65535` | yes | 291 | `(386,203)`, `65535→65535` | no |
| 159 | 82 | `(177,209)`, `73→65535` | yes | 297 | `(392,204)`, `66→65535` | yes |

`65535` (`$FFFF`) denotes a transparent native Y-sprite source pixel in the tested MAME implementation. These are *arcade composed-screen* edge coordinates and raw emulated bitmap words, not world-track units. **Documented only in the pinned [MAME screen update](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/segaybd.cpp) and [rotation draw code](https://github.com/mamedev/mame/blob/mame0289/src/mame/sega/segaic16.cpp):** transparent Y-source pixels use a rotation scanline color, after which 16B sprites may overwrite eligible pixels by priority. **Inference from verified execution and that documented path:** the unchanged right boundaries at Y=157–158 are supplied outside the opaque Y-sprite contribution tested here. Which of those later/background stages supplies each pixel is **unsupported** until directly captured.

## Evidence and reproduction

**Verified by execution:** project baseline revision `73b0de9` on `experiment/perspective-road`; macOS Darwin 25.6.0 x86_64; Python 3.14.8; owner-local 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 saved-state SHA-256 `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The old/new patch SHA-256 values are `299fd78351679af86faa30198612ea593159abb8814ec3040f39d7df5fa93611` and `974249bf770fb1306aaa4c4d2e5d07c20e390954f7e543b8ae5dcc5f728e3aa8`; analyzer SHA-256 `32a5138828da8de75c7f8a2e1084f6ea5d5896773128eeb8ecacf85f98760080`. No Sega CD BIOS/image, BlastEm, second arcade emulator or physical hardware was run. MAME host speed is not Sega CD or arcade hardware performance.

**Verified by execution:** ignored `build/private/phase1b-native980/result.json` SHA-256 `b9fe558b01952826476401169ee1729ace62618027f87e53199c22aee1072a72` contains every candidate mapping, the three edge rows, source checks and raw-file references; two analyzer runs produced the same hash. Baseline/hidden native-frame-979 SHA-256 values are `07437b15e496d0c74f6e74779a101aeb4e3dfe6277d170c2c5088839e9b0ea87` and `043e238a765f7cfbc62596a50e53c8ffb6b188a99357b0ebede251725d67589f`. The patched baseline/hidden screen-980 PNG SHA-256 values are `fcde1003a0a42bd9d78f24a158272f14df2c36753005f21dc867d95f8560cf5c` and `51b71b1c2e65f09300aa16cc8617e6006feb1d7e40acddec0e9eb63a737811ee`. The initial patched replay logs have SHA-256 `5c1b10f2a2842edba2c5460de10609d376b31b573d01610423b242e460efffbe` and `68493c88962286bcc61ff133bb8b41855361d75a5205c07c5b3bd23047fbcbc1`.

The patch build is reproducible from the pinned official source; execute in the isolated clone only:

```sh
git clone --depth 1 --branch mame0289 https://github.com/mamedev/mame.git /private/tmp/pd-mame0289-native980
cd /private/tmp/pd-mame0289-native980
git apply /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_ybitmap.patch
git apply /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_ybitmap_980.patch
make SOURCES=src/mame/sega/segaybd.cpp NOWERROR=1 REGENIE=1 -j8
```

Set `PDRIFT_YBITMAP_DIR=.`, `PDRIFT_SWAP_DIR=.`, `PDRIFT_SOURCE_DIR=.`, `PDRIFT_SNAPSHOT_DIR=.`, `PDRIFT_SEQUENCE_END_FRAME=982`, `PDRIFT_STEER_PULSE=112` and `PDRIFT_STATE_LOAD` to the private callback-950 state for both MAME runs. For the hide run also set `PDRIFT_SOURCE_OVERRIDE_FRAME=979`, `PDRIFT_SOURCE_OVERRIDE_RANGE=C000:0800` and `PDRIFT_SOURCE_OVERRIDE` to the prior private `$C` override. Then run:

```sh
cd /Users/murilo/repos/PowerDriftCD
python3 tools/phase1b_native980_boundary.py build/private/phase1b-native980 build/private/phase1b-forward-baseline-112-990/swap-screen-0980.png build/private/phase1b-right-search-979-C000-00800/swap-screen-0980.png
```

The original ROMs, raw native bitmaps, source RAM, screenshots and logs remain ignored under `build/private`; only the two original diagnostic patches, analyzer and evidence report are tracked.

**Next bounded test — hypothesis:** capture the rotation scanline-color result and the 16B sprite bitmap/priority at `(290,157)` and `(291,158)` in the same isolated MAME build. A paired intervention or exact palette-index trace can then distinguish background fill from foreground sprite composition. Until then, do not call these two pixels Y-sprite road geometry or use them as validated camera-adapter targets. The live Sega CD renderer and five-word interface remain unchanged.
